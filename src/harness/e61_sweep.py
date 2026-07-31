#!/usr/bin/env python3
"""Entry 61 — synthetic sweep: is the regional eps gap terrain or behaviour?

Entry 60 found eps ~0.24 on Sao Paulo and ~0.37 on the European deposit. Two
explanations fit equally: the LANDSCAPES differ, or the RIDERS do, and the
corpora confound rider with place.

This separates them. The canonical engine is run over both regions' real route
geometries with behaviour FIXED by the sweep (k_climb, k_descent) -- the same
synthetic rider everywhere. Any regional gap that survives is terrain, because
no rider is left to vary.

Ground truth is canonical leg energy, so real power-meter noise is absent and
the question is purely what geometry plus known physics implies.

COST. The full 3^6 = 729-combination grid over 200 routes is 145,800 canonical
runs at 252 ms -- 10.2 hours. This pass draws a random SUBSAMPLE of the grid
(N_COMBO, seed 53) over ALL 200 routes: the question is about routes, so the
route sample is kept whole and the physics grid is subsampled. A random draw
over a full-factorial grid is unbiased for the marginal effects reported here.

Output: data/results/e61_sweep.csv + console report.
Run: python3 src/harness/e61_sweep.py      (E61_COMBOS=n, E61_ROUTES=n)
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

import random

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    deadband, is_finite, resample_profile)
from bicycling_energy_model.engines import flat_eq_speed
from bicycling_energy_model.jsfmt import to_fixed

from e44_scurve import corpus_rides
from e52_build import GROUPS, TAU_GRID, C_PUB
from perride_invert import (CLIMB_THR, DESC_THR, ENGINE_DX, KEFF, RESULTS, RHO,
                            VMAX, VSTART)
from skc_compare import med_of

SEED = 53
N_COMBO = int(os.environ.get("E61_COMBOS", "24"))
N_ROUTES = int(os.environ.get("E61_ROUTES", "100"))     # per region
TAU = 6.0                                               # the shipped deadband
BR = {"D3", "D4", "D5"}

CRR = (0.004, 0.008, 0.012)      # 0.0012 in the prompt read as 0.012 (Entry 61)
CDA = (0.30, 0.40, 0.50)
MASS = (70.0, 85.0, 100.0)
PFLAT = (50.0, 100.0, 200.0)
KCLIMB = (1.0, 1.5, 2.0)
KDESC = (0.0, 0.1, 0.5)


def routes():
    """(region, profile) for N_ROUTES per region, deterministic."""
    got = {"BR": [], "EU": []}
    for group, pts, _ in corpus_rides():
        if group not in GROUPS:
            continue
        k = "BR" if group in BR else "EU"
        if len(got[k]) >= N_ROUTES:
            if len(got["BR"]) >= N_ROUTES and len(got["EU"]) >= N_ROUTES:
                break
            continue
        try:
            prof = resample_profile(
                build_profile([q["x"] for q in pts], [q["alt"] for q in pts]), ENGINE_DX)
        except Exception:
            continue
        if prof["x"][-1] - prof["x"][0] < 3000:
            continue
        got[k].append(prof)
    return got


def combos():
    grid = [(a, b, c, d, e, f) for a in CRR for b in CDA for c in MASS
            for d in PFLAT for e in KCLIMB for f in KDESC]
    rnd = random.Random(SEED)
    return grid if N_COMBO >= len(grid) else rnd.sample(grid, N_COMBO)


def fit_eps(pairs) -> float:
    """Flat eps minimising mean |log(Ehat/E)|; pairs are (E0, E1, truth) in kJ."""
    lo, hi = -0.2, 1.0
    best = 0.2

    def loss(e):
        import math
        s, n = 0.0, 0
        for e0, e1, t in pairs:
            v = e0 + e * (e1 - e0)
            if v > 0 and t > 0:
                s += abs(math.log(v / t))
                n += 1
        return s / n if n else float("inf")

    for _ in range(5):
        step = (hi - lo) / 200
        best = min((lo + i * step for i in range(201)), key=loss)
        lo, hi = best - step, best + step
    return best


def main() -> None:
    rr = routes()
    grid = combos()
    print(f"Entry 61 — synthetic sweep  ({len(grid)} of 729 combinations, "
          f"{len(rr['BR'])}+{len(rr['EU'])} routes)")
    print(f"  ~{len(grid) * (len(rr['BR']) + len(rr['EU'])) * 0.252 / 60:.0f} min of canonical\n")

    rows = []
    for ci, (crr, cda, m, pf, kc, kd) in enumerate(grid):
        p = {"m": m, "Crr": crr, "CdA": cda, "rho": RHO, "keff": KEFF,
             "wind": 0.0, "vmax": VMAX, "vstart": VSTART}
        pw = {"climb": pf * kc, "flat": pf, "descent": pf * kd,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        vf = flat_eq_speed(pf, p)
        if not (is_finite(vf) and vf > 0):
            continue
        opt = {"climbAeroMode": "zero", "climbThr": CLIMB_THR,
               "descThr": DESC_THR, "climbPower": pw["climb"]}
        for reg in ("BR", "EU"):
            pairs = {f: [] for f in ("F1", "F2", "F3", "F4")}
            for prof in rr[reg]:
                try:
                    truth = canonical(prof, pw, p)["legE"] / 1000.0
                except Exception:
                    continue
                if not (is_finite(truth) and truth > 0):
                    continue
                profS = {"x": prof["x"], "h": deadband(prof["h"], TAU)}
                for f, pr, mode in (("F1", prof, "off"), ("F2", prof, "zero"),
                                    ("F3", profS, "zero")):
                    o = dict(opt, climbAeroMode=mode)
                    a0 = approximate(pr, p, vf, 0.0, o)
                    a1 = approximate(pr, p, vf, 1.0, o)
                    pairs[f].append((a0["E"] / 1000, a1["E"] / 1000, truth))
                a0 = approximate(prof, p, vf, 0.0, opt)
                a1 = approximate(prof, p, vf, 1.0, opt)
                km = (max(0.0, 1 - C_PUB * (prof["x"][-1] / 1000) / a0["hplus"])
                      if a0["hplus"] > 0 else 1.0)
                e0 = (a0["roll"] + a0["aero"] + km * a0["climb"]) / 1000
                e1 = e0 + km * a1["recov"] / 1000
                pairs["F4"].append((e0, e1, truth))
            for f, pr in pairs.items():
                if len(pr) >= 10:
                    rows.append({"combo": ci, "region": reg, "form": f,
                                 "crr": crr, "cda": cda, "m": m, "pflat": pf,
                                 "kclimb": kc, "kdesc": kd, "eps": fit_eps(pr),
                                 "n": len(pr)})
        if (ci + 1) % 4 == 0:
            print(f"  {ci + 1}/{len(grid)} combinations done", flush=True)

    def med(sel):
        v = [r["eps"] for r in rows if sel(r)]
        return med_of(v) if v else float("nan")

    print(f"\n  eps by region and form (median over {len(grid)} physics settings)")
    print(f"    {'form':<6} {'BR (D3-D5)':>12} {'EU (D6)':>10} {'gap':>8}")
    for f in ("F1", "F2", "F3", "F4"):
        b = med(lambda r, f=f: r["form"] == f and r["region"] == "BR")
        e = med(lambda r, f=f: r["form"] == f and r["region"] == "EU")
        print(f"    {f:<6} {to_fixed(b, 4):>12} {to_fixed(e, 4):>10} {to_fixed(e - b, 4):>8}")

    print(f"\n  F3 eps against the swept behaviour (P3, P4)")
    for name, key, vals in (("k_descent", "kdesc", KDESC), ("P_flat", "pflat", PFLAT),
                            ("k_climb", "kclimb", KCLIMB)):
        cells = [med(lambda r, k=key, v=v: r["form"] == "F3" and r[k] == v) for v in vals]
        print(f"    {name:<10} " + "  ".join(f"{v:>5}: {to_fixed(c, 4)}"
                                             for v, c in zip(vals, cells)))

    path = os.path.join(RESULTS, "e61_sweep.csv")
    cols = ["combo", "region", "form", "crr", "cda", "m", "pflat", "kclimb", "kdesc", "eps", "n"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(r[c]) for c in cols) + "\n")
    print(f"\nwrote {os.path.basename(path)}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
