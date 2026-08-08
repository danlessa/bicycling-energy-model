#!/usr/bin/env python3
"""Entry 72 — paper 3's core results: the edge cost at ride grain.

Three questions, one walk over paper 1's population (D3–D6, the A-chain
cache's per-ride physics):

  R1  FIDELITY (H1; claim a3.discretisation.fidelity). The deployed per-edge
      cost — `r1d_v2_edge`, the Python reference of the router's v2Edge —
      summed over each ride's own profile, against (a) the measured energy
      and (b) its route-level twin: F2-with-ε_geom on the same 5 m profile
      (v2Edge has no deadband and lumps no ε, so its ride-level integral is
      the ungated closed form at the geometric recovery estimator).
  R2  SCALE (H2). The same edge-sum at grid pitches 5/10/30/60/90 m — the
      divergence-with-resolution curve the paper's §2.4 promises at edge
      grain, on the recording chain so no DEM error mixes in.
  R3  THE VALLEY PATCH (H5 teaser). At the 30 m pitch — the deployed scale,
      where jitter is gone and no deadband exists to double-book — the
      Entry-63 KE toll applied as a per-valley (graph-node) term on the
      closed form: E = roll + aero + β(h₊−T) − ε_geom·β(h₋−T), T from the
      profile's own descent→climb valleys at floor τ_n = 0, v_b = ∞.
      Route-grain evidence (Entry 71) says this should beat the scalar k_s
      stand-in; this is the edge-grain first look, NOT the pre-registered
      arm H5 still requires.

Output: data/results/e72_edgegrain.csv (per ride × arms), console tables,
and the paper-3 figure `research/article/figs/fig-p3-scale.svg` (hand-emitted
SVG, the e62 convention). Run: python3 src/harness/e72_edgegrain.py
(`E72_SMOKE=1` for 15 rides/group).
"""

from __future__ import annotations

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

SMOKE = bool(os.environ.get("E72_SMOKE"))
if SMOKE:
    os.environ["E52_SMOKE"] = "1"

from bicycling_energy_model import (approximate, build_profile,  # noqa: E402
                                    empirical_kj, extract_regime_powers,
                                    is_finite, overall_mean_power,
                                    resample_profile)
from bicycling_energy_model.engines import G, eps_geom, flat_eq_speed  # noqa: E402
from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

from e44_scurve import corpus_rides  # noqa: E402
from e52_split import GROUPS, load  # noqa: E402
from perride_invert import CLIMB_THR, DESC_THR, KEFF, RESULTS, RHO  # noqa: E402
from regime_compare import r1d_v2_edge  # noqa: E402
from skc_compare import boot_ci_strat, med_of, sign_p  # noqa: E402

DXS = (5, 10, 30, 60, 90)
SUFF = ".SMOKE" if SMOKE else ""
FIGS = os.path.join(REPO, "research", "article", "figs")
_E63 = None


def toll30(prof, p, vf, p_climb) -> float:
    """Entry-63 valley toll on the 30 m profile, floor 0, v_b = ∞ (metres)."""
    global _E63
    if _E63 is None:
        import e63_f5_kebuffer as _m
        _E63 = _m
    _E63.TAU_N = 0.0
    t = _E63.ride_tolls(prof, p["m"], p["Crr"], p["CdA"], vf, p_climb)
    return t[f"toll_vb{_E63.VB_INF_I}"]


def f4_published() -> tuple[float, float]:
    """Paper 1's published F4 (eps, c) — read from the producing CSV, never a
    literal (the Entry-63 invariant)."""
    path = os.path.join(RESULTS, "e52_split" + SUFF + ".csv")
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["form"] == "F4":
                return float(r["eps"]), float(r["c"])
    raise SystemExit("F4 row not found in e52_split.csv")


def c_measured() -> float:
    """Article 2's measured barometric noise rate (re-based, Entry 71) — read
    from e71_dem_pop.csv's CRATE row, never a literal. Smoke falls back to
    3.0 with a warning (non-authoritative anyway)."""
    path = os.path.join(RESULTS, "e71_dem_pop.csv")
    try:
        with open(path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("table") == "CRATE" and r.get("pool") == "D3+D4+D5"
                        and r.get("arm") == "own"):
                    return float(r["c_med"])
    except FileNotFoundError:
        pass
    if SMOKE:
        print("  (e71 CRATE row unavailable — smoke fallback c = 3.0)")
        return 3.0
    raise SystemExit("run e71_dem_pop.py first: F4's measured c comes from it")


def main() -> None:
    eps_pub, c_pub = f4_published()
    c_meas = c_measured()
    cache = {r["ride"]: r for r in load()}
    rows = []
    seen: dict[str, int] = {}
    print(f"Entry 72 — the edge cost at ride grain ({len(cache)} cached rides)"
          + ("   [SMOKE]" if SMOKE else ""))
    for group, pts, _mass in corpus_rides():
        if group not in GROUPS:
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if SMOKE and i >= 15:
            continue
        c = cache.get(f"{group}#{i}")
        if c is None:
            continue
        emp = empirical_kj(pts)
        if not (is_finite(emp) and emp > 0):
            continue
        p = {"m": c["m_hat"], "Crr": c["crr_hat"], "CdA": c["cda_hat"],
             "rho": RHO, "keff": KEFF, "wind": 0.0}
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        flat = (rp["flat"]["mean"] if rp["flat"]["mean"] is not None
                else overall_mean_power(pts))
        if not (is_finite(flat) and flat > 0):
            continue
        p_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat
        pw = {"climb": p_climb, "flat": flat,
              "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
        vf = flat_eq_speed(flat, p)
        row = {"group": group, "ride": f"{group}#{i}", "emp": emp}
        opt = {"climbAeroMode": "zero", "climbThr": CLIMB_THR,
               "descThr": DESC_THR, "climbPower": p_climb}
        prof30 = None
        for dx in DXS:
            prof = resample_profile(phys, dx)
            if prof["x"][-1] - prof["x"][0] < 3000:
                row = None
                break
            row[f"v2_d{dx}"] = 100 * (r1d_v2_edge(prof, p, pw, CLIMB_THR)
                                      - emp) / emp     # r1d returns kJ
            if dx == 5:
                eg = eps_geom(prof, p, vf)
                eg = eg if is_finite(eg) else 0.2
                row["eps_geom"] = eg
                row["route5"] = 100 * (approximate(prof, p, vf, eg, opt)["E"]
                                       / 1000 - emp) / emp
            if dx == 30:
                prof30 = prof
        if row is None:
            continue
        eg30 = eps_geom(prof30, p, vf)
        eg30 = eg30 if is_finite(eg30) else row["eps_geom"]
        a30 = approximate(prof30, p, vf, eg30, opt)
        T = toll30(prof30, p, vf, p_climb)
        beta = p["m"] * G / p["keff"]
        e_patch = (a30["roll"] + a30["aero"] + beta * (a30["hplus"] - T)
                   - eg30 * beta * (a30["hminus"] - T)) / 1000
        row["patch30"] = 100 * (e_patch - emp) / emp
        row["toll30_m"] = T

        # the edge-expressible route-level comparators (Danilo: F4, with the
        # flat-eps recommendation of paper 1 and the measured c of paper 2) —
        # pure arithmetic on the A-chain cache's F2 components
        def f4(eps_, cr_):
            x_km = c["x_m"] / 1000.0
            k = (max(0.0, 1 - cr_ * x_km / c["hplus"]) if c["hplus"] > 0 else 1.0)
            return (c["f2_roll"] + c["f2_aero"]
                    + k * (c["f2_climb"] + eps_ * c["f2_recov1"])) / 1000.0
        row["f4_pub"] = 100 * (f4(eps_pub, c_pub) - emp) / emp
        row["f4_meas"] = 100 * (f4(row["eps_geom"], c_meas) - emp) / emp
        rows.append(row)

    print(f"  {len(rows)} rides scored")

    def line(tag, vals):
        vals = [v for v in vals if is_finite(v)]
        a = [abs(v) for v in vals]
        by_g = lambda f: [x for x in
                          (f([r for r in rows if r["group"] == g]) for g in GROUPS)
                          if x]
        key = tag
        ci_a = boot_ci_strat(by_g(lambda s: [abs(r[key]) for r in s
                                             if is_finite(r.get(key, float("nan")))]), 42)
        ci_s = boot_ci_strat(by_g(lambda s: [r[key] for r in s
                                             if is_finite(r.get(key, float("nan")))]), 43)
        print(f"    {tag:<10} med|Δ%| {med_of(a):5.2f} [{ci_a[0]:.2f}, {ci_a[1]:.2f}]"
              f"   signed {med_of(vals):+5.2f} [{ci_s[0]:+.2f}, {ci_s[1]:+.2f}]")
        return med_of(a), med_of(vals)

    print("\n  R1/R2 — vs measured energy (med|Δ%| [95% CI] · signed [95% CI])")
    curve = {}
    for dx in DXS:
        curve[dx] = line(f"v2_d{dx}", [r[f"v2_d{dx}"] for r in rows])
    print("    ---")
    line("route5", [r["route5"] for r in rows])
    print(f"    [F4 comparators: published (eps {eps_pub:g}, c {c_pub:g}) · "
          f"all-measured (eps_geom, c {c_meas:g} from article 2)]")
    line("f4_pub", [r["f4_pub"] for r in rows])
    line("f4_meas", [r["f4_meas"] for r in rows])
    pa, ps = line("patch30", [r["patch30"] for r in rows])

    # agreement with the route-level integral (the fidelity bound)
    gaps = [r["v2_d5"] - r["route5"] for r in rows]
    print(f"\n  R1 — edge-sum vs route-level integral at 5 m: "
          f"med|gap| {med_of([abs(g) for g in gaps]):.2f} pp, "
          f"med {med_of(gaps):+.2f} pp")
    pair = [(abs(r["patch30"]), abs(r[f"v2_d30"])) for r in rows]
    w = sum(1 for a_, b_ in pair if a_ < b_)
    l_ = sum(1 for a_, b_ in pair if a_ > b_)
    print(f"  R3 — patch vs v2Edge at 30 m: patch closer on {w}/{w + l_} "
          f"(sign p = {to_fixed(sign_p(w, l_), 4)}); "
          f"toll median {med_of([r['toll30_m'] for r in rows]):.1f} m")

    out = os.path.join(RESULTS, "e72_edgegrain" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        wcsv = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        for r in rows:
            wcsv.writerow(r)
    print(f"\n  wrote {os.path.basename(out)}")

    # ---- fig-p3-scale.svg: med|Δ%| and signed bias vs grid pitch ----
    os.makedirs(FIGS, exist_ok=True)
    W, H, ML, MB, MT, MR = 560, 360, 62, 48, 22, 16
    xs = [5, 10, 30, 60, 90]
    ymax = max(max(curve[d][0] for d in xs),
               max(abs(curve[d][1]) for d in xs), abs(pa)) * 1.15
    ymin = min(0.0, min(curve[d][1] for d in xs), ps) * 1.15

    def X(dx):
        return ML + (math.log(dx / 5) / math.log(90 / 5)) * (W - ML - MR)

    def Y(v):
        return MT + (ymax - v) / (ymax - ymin) * (H - MT - MB)

    def pl(pts_):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'font-family="sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" fill="white"/>']
    for v in range(0, int(ymax) + 1, 2):
        svg.append(f'<line x1="{ML}" y1="{Y(v):.1f}" x2="{W - MR}" y2="{Y(v):.1f}" '
                   f'stroke="#ddd"/>')
        svg.append(f'<text x="{ML - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    svg.append(f'<line x1="{ML}" y1="{Y(0):.1f}" x2="{W - MR}" y2="{Y(0):.1f}" '
               f'stroke="#999"/>')
    for dx in xs:
        svg.append(f'<text x="{X(dx):.1f}" y="{H - MB + 16}" '
                   f'text-anchor="middle">{dx}</text>')
    svg.append(f'<text x="{(ML + W - MR) / 2:.0f}" y="{H - 10}" text-anchor="middle">'
               f'grid pitch, m (log)</text>')
    svg.append(f'<text x="14" y="{(MT + H - MB) / 2:.0f}" text-anchor="middle" '
               f'transform="rotate(-90 14 {(MT + H - MB) / 2:.0f})">Δ%, '
               f'v2Edge vs measured</text>')
    svg.append(f'<polyline fill="none" stroke="#0072B2" stroke-width="2.2" '
               f'points="{pl([(X(d), Y(curve[d][0])) for d in xs])}"/>')
    svg.append(f'<polyline fill="none" stroke="#D55E00" stroke-width="2.2" '
               f'stroke-dasharray="6 3" '
               f'points="{pl([(X(d), Y(curve[d][1])) for d in xs])}"/>')
    for d in xs:
        svg.append(f'<circle cx="{X(d):.1f}" cy="{Y(curve[d][0]):.1f}" r="3.4" '
                   f'fill="#0072B2"/>')
        svg.append(f'<circle cx="{X(d):.1f}" cy="{Y(curve[d][1]):.1f}" r="3.4" '
                   f'fill="#D55E00"/>')
    svg.append(f'<rect x="{X(30) - 5:.1f}" y="{Y(pa) - 5:.1f}" width="10" '
               f'height="10" fill="#009E73"/>')
    svg.append(f'<text x="{ML + 10}" y="{MT + 16}" fill="#0072B2">med |Δ%|</text>')
    svg.append(f'<text x="{ML + 10}" y="{MT + 32}" fill="#D55E00">signed bias</text>')
    svg.append(f'<text x="{ML + 10}" y="{MT + 48}" fill="#009E73">valley patch @ 30 m '
               f'(med |Δ%|)</text>')
    svg.append('</svg>')
    fig = os.path.join(FIGS, "fig-p3-scale" + SUFF + ".svg")
    with open(fig, "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg))
    print(f"  wrote {os.path.relpath(fig, REPO)}")


if __name__ == "__main__":
    main()
