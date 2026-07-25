#!/usr/bin/env python3
"""e26_detour.py — Entry 26 / Experiment 1 SECONDARY endpoint: the detour ratio.

Pre-registration: "the detour ratio E_opt(8) / E_trackwalk per ride (connecting
the discretized optimum to Entry 19's fixed-route numbers)".

  E_opt(n)      free-terrain optimal energy A→B on the n-direction grid, from
                data/results/e26_grid.csv (produced in the sibling simujaules repo by
                the REAL energy-worker.js).
  E_trackwalk   the v2Edge cost of the route the rider ACTUALLY took, walked over
                that ride's igc5 profile.

WHY THIS HARNESS EXISTS RATHER THAN A CSV JOIN.  Entry 19's per-ride v2_igc5
numbers are computed with each corpus's own FROZEN RIDER PHYSICS, while the grid
optimum uses the app's UI-DEFAULT bundle.  Dividing one by the other would
conflate "the terrain-optimal path is cheaper" (what we want) with "the two runs
assumed different riders" (a confound).  So the trackwalk is recomputed here
under the SAME bundle the grid harness uses, including the same gravity constant:

  * bundle = grid-e26.mjs deriveCost()'s UI defaults (m 75, Crr 0.008, CdA 0.45,
    ρ 1.1, k_eff 0.97, P_flat 80 W, k_s 1, climbThr 0.02, epsOffset 0.13);
  * g = 9.81 — the constant the JS engine folds into its cost bundle.  This is
    DELIBERATELY not bicycling_energy_model's G (São Paulo's 9.7864): a cross-engine ratio
    must hold the constant fixed, so v2Edge and flatEqSpeed are mirrored locally
    (~30 lines, same formulas as the JS) instead of imported.  The mirrors are
    hand-kept-in-sync, the house rule for every engine copy in this repo.

Everything else is imported from igc_resolution_test (profile sampling) and
e26_pairs (the pair → member-ride map), so the profiles are the Entry-19 ones.

Reads:  data/results/e26_grid.csv, data/results/e26_pair_rides.json (+ the gitignored FITs)
Writes: data/results/e26_detour.csv     (gitignored — carries ride labels)
stdout: aggregates only, no coordinates and no ride names.

  E26_GRID=<csv>  score a different grid CSV (e.g. e26_grid_cal.csv)
  /Users/danlessa/conda/bin/python src/harness/e26_detour.py
"""

import csv
import gzip
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import igc_resolution_test as igc          # noqa: E402  (profile machinery)
import e26_pairs as pairsmod               # noqa: E402  (label → FIT map)

RESULTS = igc.RESULTS
GRID_CSV = os.path.join(RESULTS, os.environ.get("E26_GRID", "e26_grid.csv"))
RIDES_MAP = os.path.join(RESULTS, "e26_pair_rides.json")
OUT = os.path.join(RESULTS, "e26_detour.csv")

# ---- UI-default cost bundle, mirrored from grid-e26.mjs deriveCost() ---------
G_JS = 9.81
UI = dict(m=75.0, crr=0.008, cda=0.45, rho=1.1, keff=0.97, pflat=80.0, ks=1.0)
CLIMB_THR = 0.02
EPS_OFFSET = 0.13


def flat_eq_speed_js(P, b):
    """Bisection mirror of grid-e26.mjs flatEqSpeed (60 halvings, [0, 40])."""
    a = b["crr"] * b["m"] * G_JS
    c = 0.5 * b["rho"] * b["cda"]
    lo, hi = 0.0, 40.0
    for _ in range(60):
        v = (lo + hi) / 2
        if (a + c * v * v) * v < b["keff"] * P:
            lo = v
        else:
            hi = v
    return (lo + hi) / 2


def derive_cost(b):
    vf = flat_eq_speed_js(b["pflat"], b)
    mg = b["m"] * G_JS
    aero = 0.5 * b["rho"] * b["cda"] * vf * vf
    return {"aRoll": mg * b["crr"] / b["keff"] / 1000,
            "aAero": aero / b["keff"] / 1000,
            "beta": mg * b["ks"] / b["keff"] / 1000,
            "abRatio": b["crr"] + aero / mg,
            "vf": vf}


def walk_v2edge(prof, c):
    """kJ for a profile under the deployed per-edge cost (v2Edge, verbatim)."""
    xs, hs = prof["x"], prof["h"]
    tot = 0.0
    for i in range(1, len(xs)):
        dist = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        if not dist > 0:
            continue
        if dh >= 0:
            aero = c["aAero"] * dist if dh < CLIMB_THR * dist else 0.0
            tot += c["aRoll"] * dist + aero + c["beta"] * dh
        else:
            ndh = -dh
            eps = c["abRatio"] * dist / ndh
            if eps > 1:
                eps = 1
            eps -= EPS_OFFSET
            if eps < 0:
                eps = 0
            e = c["aRoll"] * dist + c["aAero"] * dist - eps * c["beta"] * ndh
            tot += e if e > 0 else 0.0
    return tot


def igc5_profile(path):
    """The Entry-19 igc5 profile for one ride (5 m steps, bilinear, gap-filled).

    Mirrors process_ride's reader exactly: the rider corpora are Strava exports
    of `.fit.gz`, so decompress by extension first.  Returns (None, 0.0) for a
    .gpx track, which the Entry-19 driver also skips ('gpx-unsupported')."""
    if path.endswith(".gpx") or path.endswith(".gpx.gz"):
        return None, 0.0
    with open(path, "rb") as fh:
        buf0 = fh.read()
    buf = gzip.decompress(buf0) if path.endswith(".gz") else buf0
    try:
        geo = igc.geo_track_from_fit(buf)
    except ValueError:
        return None, 0.0
    if len(geo) < 2:
        return None, 0.0
    total = geo[len(geo) - 1]["x"]
    if not total > 0:
        return None, 0.0
    d5 = igc.grid_positions(total, 5)
    g5 = igc.lon_lat_at(geo, d5)
    s5 = igc.build_dem_profile(d5, igc.sample_raster(igc.DEM5, g5["lons"], g5["lats"], 'igc5'), 0.5)
    return s5["prof"], total


def main():
    if not os.path.exists(GRID_CSV):
        sys.exit(f"missing {GRID_CSV} — run the grid harness first")
    igc.ensure_rasters()
    grid = {}
    with open(GRID_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                grid[r["pair_id"]] = {"corpus": r["corpus"],
                                      "straight_m": float(r["straight_m"]),
                                      "e8": float(r["e8"]),
                                      "e128": float(r["e128"]) if r.get("e128") else float("nan")}
            except (TypeError, ValueError):
                continue
    ride_map = json.load(open(RIDES_MAP, encoding="utf-8"))
    fmap = pairsmod.label_to_file()
    cost = derive_cost(UI)

    print("ENTRY 26 / Experiment 1 secondary — detour ratio E_opt / E_trackwalk")
    print(f"grid CSV: {os.path.basename(GRID_CSV)} ({len(grid)} pairs)")
    print(f"bundle (mirrored from grid-e26.mjs, g={G_JS}): aRoll={cost['aRoll']:.4e} "
          f"aAero={cost['aAero']:.4e} beta={cost['beta']:.4e} v_f={cost['vf'] * 3.6:.2f} km/h")
    print(f"NOTE: g={G_JS} (the JS constant), deliberately NOT bicycling_energy_model's G={igc.G} — "
          f"a cross-engine ratio holds the constant fixed.\n")

    rows, miss = [], 0
    for pid, meta in grid.items():
        for corpus, ride in ride_map.get(pid, []):
            rel = fmap.get((corpus, ride))
            if not rel or not os.path.exists(os.path.join(igc.DATA, rel)):
                miss += 1
                continue
            prof, total = igc5_profile(os.path.join(igc.DATA, rel))
            if prof is None:
                miss += 1
                continue
            etrack = walk_v2edge(prof, cost)
            if not etrack > 0:
                miss += 1
                continue
            rows.append({"pair_id": pid, "corpus": corpus, "ride": ride,
                         "straight_km": meta["straight_m"] / 1000,
                         "track_km": total / 1000,
                         "e_opt8": meta["e8"], "e_opt128": meta["e128"],
                         "e_track_ui": etrack,
                         "ratio8": meta["e8"] / etrack,
                         "ratio128": meta["e128"] / etrack,
                         "detour": total / max(1.0, meta["straight_m"])})
        if len(rows) and len(rows) % 50 == 0:
            print(f"  …{len(rows)} rides walked")

    if not rows:
        sys.exit("no rides scored")
    os.makedirs(RESULTS, exist_ok=True)
    cols = ["pair_id", "corpus", "ride", "straight_km", "track_km",
            "e_opt8", "e_opt128", "e_track_ui", "ratio8", "ratio128", "detour"]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    def block(name, sub):
        if not sub:
            return
        r8 = sorted(x["ratio8"] for x in sub)
        r128 = sorted(x["ratio128"] for x in sub if x["ratio128"] == x["ratio128"])
        det = sorted(x["detour"] for x in sub)
        print(f"── {name} ── n={len(sub)} rides over {len({x['pair_id'] for x in sub})} pairs")
        print(f"   E_opt(8)/E_track   med={st.median(r8):.3f}  p10={r8[len(r8) // 10]:.3f} "
              f"p90={r8[min(len(r8) - 1, 9 * len(r8) // 10)]:.3f}  "
              f"share < 1 (optimum cheaper): {100 * sum(1 for v in r8 if v < 1) / len(r8):.0f}%")
        if r128:
            print(f"   E_opt(128)/E_track med={st.median(r128):.3f}")
        print(f"   route detour (track km / straight km) med={st.median(det):.2f}")

    print()
    for c in ("censo", "ppaz", "jaam", "danlessa"):
        block(c, [r for r in rows if r["corpus"] == c])
    block("ALL", rows)
    # The endpoint presumes the ride was a JOURNEY from A to B.  After Entry 26's
    # 800 m floor, most surviving rider pairs are NEAR-LOOPS (start and end a few
    # km apart, ride 60–100 km), so their ratio measures "this was not a journey"
    # rather than anything about routing.  Stratify on that explicitly instead of
    # reporting one swamped number.
    print()
    jr = [r for r in rows if r["detour"] <= 2.0]
    block("JOURNEYS ONLY (track ≤ 2× straight line)", jr)
    print(f"   [{len(rows) - len(jr)} of {len(rows)} member rides excluded as near-loops; "
          f"median detour among them {st.median([r['detour'] for r in rows if r['detour'] > 2.0]):.1f}×]"
          if len(jr) < len(rows) else "")
    print(f"\nunscored member rides (unlocatable / unprofilable): {miss}")
    print(f"wrote {os.path.basename(OUT)} ({len(rows)} rides) — gitignored")
    print("\nREADING: the ratio is NOT an accuracy statistic. E_opt is a free-terrain "
          "point-to-point optimum; E_track is the street route actually ridden. A ratio "
          "below 1 measures how much of a ride's energy is street-constraint + detour "
          "rather than terrain necessity — the bridge between Q1's discretized optimum "
          "and Entry 19's fixed-route numbers.")


if __name__ == "__main__":
    main()
