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
N_COMBO = int(os.environ.get("E61_COMBOS", "64"))
# When FULL=1 the 3-level grid is swept instead of the 2-level one: 3^6 = 729
# combinations. The RAW per-route simulation is dumped alongside the fits so
# any later re-analysis -- a different loss, a different form, a landscape
# descriptor -- can be done without re-running canonical, which is what costs
# the hours. Rows are flushed per combination, so an interrupted run leaves
# usable data rather than nothing.
FULL = bool(os.environ.get("E61_FULL"))
N_ROUTES = int(os.environ.get("E61_ROUTES", "30"))      # per region
# tau is HELD at the value fitted on real data, not swept: the question is what
# geometry implies about eps, and letting the deadband float per region would
# confound the two. c is NOT held -- it is fitted jointly with eps below,
# because F4 is a two-parameter form and pinning c at the published 3.0 m/km
# (which Entry 55 measured as costing 21.7% of the loss) would have made F4's
# regional row an artefact of a known-bad constant.
# NOTHING is held fixed: each form's own free parameters are fitted jointly --
# F3 gets (eps, tau), F4 gets (eps, c). tau cannot be fitted from cached
# components because it changes the PROFILE, so each grid value needs its own
# approximate() pass. Holding c at the published 3.0 m/km, as the first version
# did, would have made F4's regional row an artefact of a constant Entry 55
# measured as costing 21.7% of the loss.
TAU_SWEEP = (0.0, 2.0, 4.0, 6.0, 8.0, 12.0)
BR = {"D3", "D4", "D5"}

# Two-level full factorial (Danilo's revision): 2^6 = 64 combinations, every
# marginal effect balanced by construction -- better for the P3/P4 behaviour
# questions than a random subsample of the 3-level grid, and cheap enough to
# run whole. Crr given as [0.04, 0.08] is read as [0.004, 0.008]: 0.04 is an
# order of magnitude above any road rolling coefficient.
if FULL:
    CRR = (0.004, 0.008, 0.012)
    CDA = (0.30, 0.40, 0.50)
    MASS = (70.0, 85.0, 100.0)
    PFLAT = (50.0, 100.0, 200.0)
    KCLIMB = (1.0, 1.5, 2.0)
    KDESC = (0.0, 0.1, 0.5)
else:
    CRR = (0.004, 0.008)
    CDA = (0.30, 0.40)
    MASS = (75.0, 90.0)
    PFLAT = (75.0, 150.0)
    KCLIMB = (1.0, 2.0)
    KDESC = (0.0, 0.5)


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


def fit_eps2(comp) -> tuple:
    """Fit (eps, c) jointly for F4. comp rows are
    (roll, aero, climb, recov1, x_km, hplus, truth) in kJ / m."""
    import math

    def loss(e, c):
        s, n = 0.0, 0
        for roll, aero, climb, rec1, xkm, hp, t in comp:
            km = max(0.0, 1.0 - c * xkm / hp) if hp > 0 else 1.0
            v = roll + aero + km * (climb + e * rec1)
            if v > 0 and t > 0:
                s += abs(math.log(v / t))
                n += 1
        return s / n if n else float("inf")

    elo, ehi, clo, chi = -0.2, 1.0, 0.0, 6.0
    be, bc = 0.2, 1.0
    for _ in range(4):
        es = [elo + i * (ehi - elo) / 30 for i in range(31)]
        cs = [clo + i * (chi - clo) / 30 for i in range(31)]
        be, bc = min(((e, c) for e in es for c in cs), key=lambda q: loss(*q))
        de, dc = (ehi - elo) / 30, (chi - clo) / 30
        elo, ehi = be - de, be + de
        clo, chi = max(0.0, bc - dc), bc + dc
    return be, bc


def _eps_min(rows_e0e1) -> tuple:
    """(eps, loss) minimising mean |log| for a list of (E0, E1, truth)."""
    import math

    def loss(e):
        s, n = 0.0, 0
        for e0, e1, t in rows_e0e1:
            v = e0 + e * (e1 - e0)
            if v > 0 and t > 0:
                s += abs(math.log(v / t))
                n += 1
        return s / n if n else float("inf")
    lo, hi, best = -0.2, 1.0, 0.2
    for _ in range(5):
        step = (hi - lo) / 200
        best = min((lo + i * step for i in range(201)), key=loss)
        lo, hi = best - step, best + step
    return best, loss(best)


def fit_eps_tau(by_tau: dict) -> tuple:
    """F3: joint (eps, tau) over the tau grid. by_tau[tau] = [(E0,E1,truth)]."""
    best = None
    for tau, rows_ in by_tau.items():
        e, l = _eps_min(rows_)
        if best is None or l < best[2]:
            best = (e, tau, l)
    return best[0], best[1]


def fit_eps_c(comp) -> tuple:
    """F4: joint (eps, c). comp = (roll, aero, climb, recov1, x_km, hplus, truth)."""
    import math

    def loss(e, c):
        s, n = 0.0, 0
        for roll, aero, climb, rec1, xkm, hp, t in comp:
            km = max(0.0, 1.0 - c * xkm / hp) if hp > 0 else 1.0
            v = roll + aero + km * (climb + e * rec1)
            if v > 0 and t > 0:
                s += abs(math.log(v / t))
                n += 1
        return s / n if n else float("inf")
    elo, ehi, clo, chi, be, bc = -0.2, 1.0, 0.0, 6.0, 0.2, 1.0
    for _ in range(4):
        es = [elo + i * (ehi - elo) / 30 for i in range(31)]
        cs = [clo + i * (chi - clo) / 30 for i in range(31)]
        be, bc = min(((e, c) for e in es for c in cs), key=lambda q: loss(*q))
        de, dc = (ehi - elo) / 30, (chi - clo) / 30
        elo, ehi, clo, chi = be - de, be + de, max(0.0, bc - dc), bc + dc
    return be, bc


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
    raw_path = os.path.join(RESULTS, "e61_raw" + (".full" if FULL else "") + ".csv")
    raw_cols = (["combo", "region", "route", "crr", "cda", "m", "pflat", "kclimb",
                 "kdesc", "vf", "truth_kj", "f1_e0", "f1_e1", "f2_e0", "f2_e1",
                 "f4_roll", "f4_aero", "f4_climb", "f4_recov1", "f4_xkm", "f4_hplus"]
                + [f"f3t{t}_e{j}" for t in TAU_SWEEP for j in (0, 1)])
    raw = open(raw_path, "w", encoding="utf-8")
    raw.write(",".join(raw_cols) + "\n")
    fit_path = os.path.join(RESULTS, "e61_sweep" + (".full" if FULL else "") + ".csv")
    fit_cols = ["combo", "region", "form", "crr", "cda", "m", "pflat", "kclimb",
                "kdesc", "eps", "c", "tau", "n"]
    fitf = open(fit_path, "w", encoding="utf-8")
    fitf.write(",".join(fit_cols) + "\n")

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
            pairs = {f: [] for f in ("F1", "F2", "F4")}
            f3_by_tau = {t: [] for t in TAU_SWEEP}
            for ri, prof in enumerate(rr[reg]):
                try:
                    truth = canonical(prof, pw, p)["legE"] / 1000.0
                except Exception:
                    continue
                if not (is_finite(truth) and truth > 0):
                    continue
                for f, mode in (("F1", "off"), ("F2", "zero")):
                    o = dict(opt, climbAeroMode=mode)
                    a0 = approximate(prof, p, vf, 0.0, o)
                    a1 = approximate(prof, p, vf, 1.0, o)
                    pairs[f].append((a0["E"] / 1000, a1["E"] / 1000, truth))
                for tau in TAU_SWEEP:
                    ps = {"x": prof["x"], "h": deadband(prof["h"], tau)}
                    o = dict(opt, climbAeroMode="zero")
                    a0 = approximate(ps, p, vf, 0.0, o)
                    a1 = approximate(ps, p, vf, 1.0, o)
                    f3_by_tau[tau].append((a0["E"] / 1000, a1["E"] / 1000, truth))
                a0 = approximate(prof, p, vf, 0.0, opt)
                a1 = approximate(prof, p, vf, 1.0, opt)
                pairs["F4"].append((a0["roll"] / 1000, a0["aero"] / 1000,
                                    a0["climb"] / 1000, a1["recov"] / 1000,
                                    prof["x"][-1] / 1000, a0["hplus"], truth))
                _f1, _f2 = pairs["F1"][-1], pairs["F2"][-1]
                _vals = [ci, reg, ri, crr, cda, m, pf, kc, kd, f"{vf:.6f}",
                         f"{truth:.6f}", f"{_f1[0]:.6f}", f"{_f1[1]:.6f}",
                         f"{_f2[0]:.6f}", f"{_f2[1]:.6f}"] + \
                        [f"{x:.6f}" for x in pairs["F4"][-1][:6]] + \
                        [f"{f3_by_tau[t][-1][j]:.6f}" for t in TAU_SWEEP for j in (0, 1)]
                raw.write(",".join(str(v) for v in _vals) + "\n")
            fits = {}
            for f in ("F1", "F2"):
                if len(pairs[f]) >= 10:
                    fits[f] = (_eps_min(pairs[f])[0], float("nan"), float("nan"))
            if len(f3_by_tau[TAU_SWEEP[0]]) >= 10:
                e3, t3 = fit_eps_tau(f3_by_tau)
                fits["F3"] = (e3, float("nan"), t3)
            if len(pairs["F4"]) >= 10:
                e4, c4 = fit_eps_c(pairs["F4"])
                fits["F4"] = (e4, c4, float("nan"))
            for f, (e_hat, c_hat, t_hat) in fits.items():
                rows.append({"combo": ci, "region": reg, "form": f,
                             "crr": crr, "cda": cda, "m": m, "pflat": pf,
                             "kclimb": kc, "kdesc": kd, "eps": e_hat,
                             "c": c_hat, "tau": t_hat,
                             "n": len(f3_by_tau[TAU_SWEEP[0]]) if f == "F3" else len(pairs[f])})
        for r in rows[-8:]:
            if r["combo"] == ci:
                fitf.write(",".join(str(r[c]) for c in fit_cols) + "\n")
        raw.flush()
        fitf.flush()
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

    print(f"\n  jointly fitted structural parameters (nothing held)")
    for reg in ("BR", "EU"):
        t3 = [r["tau"] for r in rows if r["form"] == "F3" and r["region"] == reg
              and is_finite(r["tau"])]
        c4 = [r["c"] for r in rows if r["form"] == "F4" and r["region"] == reg
              and is_finite(r["c"])]
        print(f"    {reg}:  F3 tau median {to_fixed(med_of(t3), 2) if t3 else '—':>6} m"
              f"    F4 c median {to_fixed(med_of(c4), 3) if c4 else '—':>7} m/km")

    print(f"\n  F3 eps against every swept factor (P3, P4) — full factorial, so each")
    print(f"  column is a balanced marginal over all other factors")
    for name, key, vals in (("k_descent", "kdesc", KDESC), ("P_flat", "pflat", PFLAT),
                            ("k_climb", "kclimb", KCLIMB), ("CdA", "cda", CDA),
                            ("Crr", "crr", CRR), ("m", "m", MASS)):
        cells = [med(lambda r, k=key, v=v: r["form"] == "F3" and r[k] == v) for v in vals]
        print(f"    {name:<10} " + "  ".join(f"{v:>5}: {to_fixed(c, 4)}"
                                             for v, c in zip(vals, cells)))

    raw.close()
    fitf.close()
    print(f"\nwrote {os.path.basename(fit_path)} ({len(rows)} fits)"
          f" and {os.path.basename(raw_path)} (raw per-route simulation,"
          f" re-fittable without re-running canonical)")


if __name__ == "__main__":
    main()
