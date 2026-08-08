#!/usr/bin/env python3
"""Entry 66, stage S1 — the drift probe: closure-pair evidence for Entry 65's
baro-drift attribution, with no DTM anywhere.

THE IDENTIFICATION. Barometric drift is a function of TIME at a fixed place;
terrain is a function of PLACE. Any ride that revisits a location therefore
measures its own drift internally: two passes over the same spot separated by
dt should read the same elevation, and the discrepancy IS the drift
accumulated in between (the surveyor's levelling-loop closure, per ride). No
external elevation source is involved — Danilo's objection to the DTM design
("DTMs introduce other kinds of noise and sources of errors") is what this
probe answers: FABDEM building/canopy bias, georeferencing and GPS-slope
leakage are all place-shaped and cancel out of a same-place difference.

S1 IS CORRELATIONAL (the cheap gate before the S2 intervention). Per ride,
closure pairs give drift statistics; Entry 65's attribution then predicts:

  P1a  drift amplitude correlates with the EXTRA deadband removal between
       tau = 2 and tau = 6 — computable exactly from the e52 cache as
       (f3t5_climb - f3t12_climb) / beta, in metres;
  P1b  drift amplitude correlates with the per-ride loss improvement of
       F3(tau = 6) over F3(tau = 2), eps refit per arm on the train half;
  P1c  rider-level: median drift orders with the per-rider fitted tau* of
       Entry 64 (e63_taupred).

If none of these correlations exist, the attribution is refuted before any
correction machinery is built. (P3, the virtual-ride control, is vacuous
in-population: iter_brazil already drops manufacturer 260, so the chain
corpora contain no synthetic-elevation rides — stated, not tested.)

PAIR FILTERS, against the named confounds: same 10 m grid cell (worst-case
separation ~14 m), dt >= 10 min (a slow same-pass crossing is not a revisit),
per-cell downsampling to one sample per 60 s (a long stop must not flood the
statistics), |dh| > 20 m dropped and counted (grade-separated crossings — a
viaduct over its own street is terrain, not drift), per-cell pair cap 30.
Medians everywhere; GPS matching noise on slopes stays (bounded by ~15 m x
grade) and argues for rank correlations, which is what is reported.

LABEL PARITY: the walk reproduces corpus_rides()' iteration order and per-
group counters exactly (D6 pre-pass filters included), so every drift row
joins the e52 cache by ride label by construction.

Output: data/results/e66_drift.csv (scalar drift stats only — no geometry
leaves the walk, the repo is public). Run:
python3 src/harness/e66_driftprobe.py            (E66_SMOKE=1 for 15/group)
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

SMOKE = bool(os.environ.get("E66_SMOKE"))

from bicycling_energy_model import load_pts, parse_fit  # noqa: E402
from bicycling_energy_model.engines import G  # noqa: E402

from e52_build import C_PUB, TAU_GRID  # noqa: E402
from e52_split import cv_loss, load, split  # noqa: E402
from perride_invert import KEFF, RESULTS  # noqa: E402
from skc_compare import med_of, ride_files  # noqa: E402
from skc_invert import DATA, ZWIFT  # noqa: E402

# --- raw records with geo. Deliberately COPIED from param_fit.py (its
# raw_records/parse_gpx_records) rather than imported: param_fit is a
# module-level script — importing it runs the whole Entry-15 analysis and
# rewrites param_fit.csv as a side effect (it did, once, in this entry's
# smoke; the file is deterministic so the rewrite was benign, but an import
# that runs a harness is not a dependency, it is an accident).

import gzip  # noqa: E402
import re  # noqa: E402
from datetime import datetime  # noqa: E402

_TRKPT = re.compile(r'<trkpt\b([^>]*)>([\s\S]*?)</trkpt>')
_LAT = re.compile(r'lat="([-\d.]+)"')
_LON = re.compile(r'lon="([-\d.]+)"')
_ELE = re.compile(r'<ele>\s*([-\d.]+)')
_TIME = re.compile(r'<time>\s*([^<]+)')


def _date_parse(s: str) -> float:
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float("nan")


def _parse_gpx_records(text: str) -> list[dict]:
    out = []
    for m in _TRKPT.finditer(text):
        la, lo = _LAT.search(m.group(1)), _LON.search(m.group(1))
        if not la or not lo:
            continue
        ele, tm = _ELE.search(m.group(2)), _TIME.search(m.group(2))
        out.append({"lat": float(la.group(1)), "lon": float(lo.group(1)),
                    "alt": float(ele.group(1)) if ele else None,
                    "time": _date_parse(tm.group(1)) if tm else None})
    return out


def raw_records(path: str) -> list[dict]:
    with open(path, "rb") as fh:
        buf = fh.read()
    if path.endswith(".gz") and not path.endswith(".gpx.gz"):
        buf = gzip.decompress(buf)
    if path.endswith(".gpx"):
        return _parse_gpx_records(buf.decode("utf-8"))
    return parse_fit(buf)

TI_2, TI_6 = TAU_GRID.index(2.0), TAU_GRID.index(6.0)
CELL = 10.0          # m, revisit grid cell
MIN_DT = 600.0       # s, minimum revisit separation
BIG_DH = 20.0        # m, grade-separation drop threshold
PAIR_CAP = 30        # per-cell pair budget
DRIFT_CSV = os.path.join(RESULTS, "e66_drift" + (".SMOKE" if SMOKE else "") + ".csv")


# --------------------------------------------------------------- the walk

def corpus_paths():
    """(group, path) in corpus_rides()' exact order, D3-D6 only. The D6
    pre-pass filters are replicated verbatim so the per-group counters land on
    the same rides as the e52 cache."""
    for rider, path in ride_files():
        try:
            pts = load_pts(path)
        except Exception:
            continue
        if len(pts) < 10:
            continue
        npow = sum(1 for q in pts if q.get("power") is not None)
        nalt = sum(1 for q in pts if q.get("alt") is not None)
        if npow / len(pts) <= 0.5 or nalt / len(pts) < 0.99 or pts[-1]["x"] / 1000 < 20:
            continue
        yield "D6-" + rider, path
    for corpus, lab in (("ppaz", "D3"), ("jaam", "D4"), ("danlessa", "D5")):
        man = json.load(open(os.path.join(DATA, f"strava_{corpus}_manifest.json")))
        cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
                and a["km"] >= 20 and a["altCov"] >= 0.99]
        for a in cand:
            meta: dict = {}
            try:
                load_pts(os.path.join(DATA, a["file"]), meta)
            except Exception:
                continue
            if meta.get("manufacturer") == ZWIFT:
                continue
            yield lab, os.path.join(DATA, a["file"])


def closure_stats(path: str) -> dict | None:
    """Per-ride drift statistics from same-place, different-time pairs."""
    try:
        recs = raw_records(path)
    except Exception:
        return None
    g = [(r["time"], r["lat"], r["lon"], r["alt"]) for r in recs
         if r.get("time") is not None and r.get("lat") is not None
         and r.get("lon") is not None and r.get("alt") is not None]
    if len(g) < 100:
        return None
    lat0, lon0 = g[0][1], g[0][2]
    kx = 111320.0 * math.cos(math.radians(lat0))
    cells: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for t, la, lo, al in g:
        key = (int((lo - lon0) * kx // CELL), int((la - lat0) * 110540.0 // CELL))
        lst = cells.setdefault(key, [])
        if lst and t - lst[-1][0] < 60.0:
            continue
        lst.append((t, al))
    deltas: list[tuple[float, float]] = []
    n_big = 0
    for lst in cells.values():
        if len(lst) < 2:
            continue
        n_here = 0
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                dt = lst[j][0] - lst[i][0]
                if dt < MIN_DT:
                    continue
                dh = lst[j][1] - lst[i][1]
                if abs(dh) > BIG_DH:
                    n_big += 1
                    continue
                deltas.append((abs(dh), dt))
                n_here += 1
                if n_here >= PAIR_CAP:
                    break
            if n_here >= PAIR_CAP:
                break
    if len(deltas) < 10:
        return {"n_pairs": len(deltas), "n_big": n_big, "n_sites": 0,
                "drift_med_m": "", "drift_p90_m": "", "rate_mh": "",
                "max_dt_min": ""}
    mags = sorted(d for d, _ in deltas)
    rates = sorted(d / (dt / 3600.0) for d, dt in deltas)
    n_sites = sum(1 for lst in cells.values() if len(lst) >= 2)
    return {"n_pairs": len(deltas), "n_big": n_big, "n_sites": n_sites,
            "drift_med_m": mags[len(mags) // 2],
            "drift_p90_m": mags[min(len(mags) - 1, int(0.9 * len(mags)))],
            "rate_mh": rates[len(rates) // 2],
            "max_dt_min": max(dt for _, dt in deltas) / 60.0}


# ------------------------------------------------------------ correlations

def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    rk = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rk[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return rk


def spearman(xs, ys) -> float:
    ra, rb = ranks(xs), ranks(ys)
    n = len(xs)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((a - ma) * (b - mb) for a, b in zip(ra, rb))
    den = math.sqrt(sum((a - ma) ** 2 for a in ra)
                    * sum((b - mb) ** 2 for b in rb))
    return num / den if den else float("nan")


def eps_opt_f3(rows, ti) -> float:
    lo, hi = (-0.20, 1.00)
    best = 0.2
    for _ in range(5):
        step = (hi - lo) / 200
        best = min([lo + i * step for i in range(201)],
                   key=lambda e: cv_loss(rows, "F3", e, C_PUB, ti))
        lo, hi = best - step, best + step
    return best


def main() -> None:
    print("Entry 66 S1 — the drift probe (closure pairs, no DTM)"
          + ("   [SMOKE]" if SMOKE else ""))
    cache = {r["ride"]: r for r in load()}
    if os.path.exists(DRIFT_CSV) and not os.environ.get("E66_REBUILD"):
        print(f"  reusing {os.path.basename(DRIFT_CSV)} (E66_REBUILD=1 to rewalk)")
        with open(DRIFT_CSV, encoding="utf-8") as fh:
            drift_rows = list(csv.DictReader(fh))
    else:
        drift_rows = []
        seen: dict[str, int] = {}
        for group, path in corpus_paths():
            i = seen.get(group, 0)
            seen[group] = i + 1
            if SMOKE and i >= 15:
                continue
            label = f"{group}#{i}"
            if label not in cache:
                continue
            st = closure_stats(path)
            if st is None:
                st = {"n_pairs": 0, "n_big": 0, "n_sites": 0, "drift_med_m": "",
                      "drift_p90_m": "", "rate_mh": "", "max_dt_min": ""}
            drift_rows.append({"group": group, "ride": label, **st})
        cols = ["group", "ride", "n_pairs", "n_big", "n_sites", "drift_med_m",
                "drift_p90_m", "rate_mh", "max_dt_min"]
        with open(DRIFT_CSV, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in drift_rows:
                w.writerow(r)
        print(f"  wrote {os.path.basename(DRIFT_CSV)} ({len(drift_rows)} rides)")

    usable = [r for r in drift_rows if r["drift_med_m"] != ""]
    print(f"  closure coverage: {len(usable)}/{len(drift_rows)} rides with "
          f">=10 pairs; median pairs "
          f"{med_of([float(r['n_pairs']) for r in usable]):.0f}, median drift "
          f"{med_of([float(r['drift_med_m']) for r in usable]):.2f} m, median "
          f"rate {med_of([float(r['rate_mh']) for r in usable]):.2f} m/h")
    print("  (P3 note: the chain corpora contain no virtual rides — "
          "iter_brazil drops manufacturer 260 — so that control is vacuous)")

    # join the cache; removal in metres is parameter-free arithmetic
    joined = []
    for r in usable:
        c = cache.get(r["ride"])
        if not c:
            continue
        beta = c["m_hat"] * G / KEFF
        joined.append({
            "group": r["group"], "ride": r["ride"],
            "drift": float(r["drift_med_m"]), "rate": float(r["rate_mh"]),
            "removal_m": (c["f3t%d_climb" % TI_2] - c["f3t%d_climb" % TI_6]) / beta,
            "c": c})

    train, _test = split([j["c"] for j in joined])
    train_ids = {r["ride"] for r in train}
    jt = [j for j in joined if j["ride"] in train_ids]
    e2 = eps_opt_f3(train, TI_2)
    e6 = eps_opt_f3(train, TI_6)
    from e52_build import e_form
    for j in jt:
        l2 = abs(math.log(e_form(j["c"], "F3", e2, C_PUB, TI_2) / j["c"]["emp"]))
        l6 = abs(math.log(e_form(j["c"], "F3", e6, C_PUB, TI_6) / j["c"]["emp"]))
        j["benefit"] = l2 - l6          # >0: the 6 m deadband helped this ride

    print(f"\n  P1 correlations (train half, n = {len(jt)}; eps refit per arm: "
          f"eps(tau2) = {e2:.4f}, eps(tau6) = {e6:.4f})")
    for tag, xs, ys in (
            ("P1a drift vs extra removal (tau2->tau6, m)",
             [j["drift"] for j in jt], [j["removal_m"] for j in jt]),
            ("P1b drift vs per-ride tau6 benefit",
             [j["drift"] for j in jt], [j["benefit"] for j in jt]),
            ("     rate  vs per-ride tau6 benefit",
             [j["rate"] for j in jt], [j["benefit"] for j in jt])):
        print(f"    {tag:<44} Spearman rho = {spearman(xs, ys):+.3f}")

    # rider level: median drift vs Entry 64's fitted tau*
    taupred = os.path.join(RESULTS, "e63_taupred.E63_TAUN2p0.csv")
    if os.path.exists(taupred):
        tau_star = {}
        with open(taupred, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                tau_star[r["group"]] = float(r["tau_star"])
        groups = sorted({j["group"] for j in joined} & set(tau_star))
        gd, gt = [], []
        print(f"\n  P1c rider level ({len(groups)} groups)")
        print(f"    {'group':<12} {'n':>5} {'med drift m':>12} {'med rate':>9} "
              f"{'tau*':>5}")
        for g in groups:
            sub = [j for j in joined if j["group"] == g]
            dmed = med_of([j["drift"] for j in sub])
            rmed = med_of([j["rate"] for j in sub])
            print(f"    {g:<12} {len(sub):>5} {dmed:>12.2f} {rmed:>9.2f} "
                  f"{tau_star[g]:>5.1f}")
            gd.append(dmed)
            gt.append(tau_star[g])
        print(f"    Spearman rho(med drift, tau*) = {spearman(gd, gt):+.3f}")


if __name__ == "__main__":
    main()
