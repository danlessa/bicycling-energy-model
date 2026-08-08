#!/usr/bin/env python3
"""Entry 67 — decomposing the deadband's unique share: absorber or physics?

Entries 63-66 left the F2->F3 gap split into ~46-53 pp of KE-buffer physics
(the toll reproduces it) and ~25-29 pp unique to the fitted tau = 6 deadband,
with every measurement-error mechanism acquitted (fragmentation, white
jitter, drift). Two remaining readings: a FLEXIBLE MISFIT ABSORBER (the
threshold shaves h+ wherever the ledger runs hot — rider-shaped, not
transferable) or UNMODELED PHYSICS (a feature class the toll misses —
geometry-shaped, transferable, worth a term). This entry runs the two
diagnostics that separate them without any new walk:

B — THE ABSORBER SIGNATURE (cache arithmetic, train half only).
  Per ride: r = log(E(tau2, eps2)/emp), the signed misfit under the weak
  filter; delta = log E(tau2, eps6) - log E(tau6, eps6), the removal's
  log-scale effect at COMMON eps — pure geometry; benefit = |r| - |r'|.
  Since eps is refit at each tau, a uniform bias shift is already absorbed by
  eps — the fitted tau = 6 can only win through the COUPLING rho(delta, r):
  removable mass sitting preferentially on overpredicted rides. Where that
  coupling lives decides the reading:
    within riders  -> a geometry/feature class couples mass to misfit
                      (candidate physics, could upgrade the toll);
    between riders -> rider-level bias soaked by a rider-blind knob
                      (absorber; Entry 39's tau*-tracks-bias, sharpened).

C — STATIONARITY (within-rider time split, train half only).
  Each rider's train rides are split into early/late halves by activity
  order (Strava activity ids and the D6 filename dates are chronological —
  stated as the proxy it is). Per half: fitted (eps, tau*) for F3 and eps for
  F5f (tau_n = 2 + toll, the physics form). Physics is stationary; an
  absorber tracks whatever drifted (device, season, routes). Also the AGING
  test: score each late half with its own early-half constants — the form
  whose constants transfer forward in time carries the transferable content.

Outputs: data/results/e67_signature.csv (per-ride), e67_stability.csv
(per rider-half). Run: python3 src/harness/e67_residual.py  (E67_SMOKE=1)
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

SMOKE = bool(os.environ.get("E67_SMOKE"))
if SMOKE:
    os.environ["E52_SMOKE"] = "1"
# the F5f comparator lives at the tau_n = 2 arm — pin the e63 module there
# BEFORE importing it (its TAU_N/TI_N/TOLLS_CSV are module constants).
# Entry 69 runs this harness at OTHER arms (E63_TAUN=3.0/4.5, the frontier
# map): an explicit arm suffixes this harness's outputs too, so a sensitivity
# run can never overwrite the canonical Entry-67 CSVs (the repo rule).
_ARM = os.environ.get("E63_TAUN")
os.environ.setdefault("E63_TAUN", "2.0")

from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

from e52_build import C_PUB, TAU_GRID, e_form  # noqa: E402
from e52_split import GROUPS, cv_loss, fit, load, split  # noqa: E402
from e63_f5_kebuffer import (TAU_N as TAUN5, cv_loss5, fit_f5f,  # noqa: E402
                             join_tolls)
from e66_driftprobe import eps_opt_f3, ranks, spearman  # noqa: E402
from bicycling_energy_model.engines import G  # noqa: E402
from bicycling_energy_model.util import env_suffix  # noqa: E402
from perride_invert import KEFF, RESULTS  # noqa: E402
from skc_compare import med_of  # noqa: E402

TI_2, TI_6 = TAU_GRID.index(2.0), TAU_GRID.index(6.0)
SUFF = (env_suffix("E63_TAUN") if _ARM else "") + (".SMOKE" if SMOKE else "")
MIN_HALF = 5 if SMOKE else 20   # rides per half below which C's fits are noise


def part_b(train) -> None:
    e2 = eps_opt_f3(train, TI_2)
    e6 = eps_opt_f3(train, TI_6)
    rows = []
    for c in train:
        E2, E6 = e_form(c, "F3", e2, C_PUB, TI_2), e_form(c, "F3", e6, C_PUB, TI_6)
        E2c, E6c = e_form(c, "F3", e6, C_PUB, TI_2), E6
        if min(E2, E6, E2c) <= 0 or c["emp"] <= 0:
            continue
        r = math.log(E2 / c["emp"])
        rows.append({"group": c["group"], "ride": c["ride"],
                     "resid_tau2": r,
                     "delta_geom": math.log(E2c / E6c),
                     "benefit": abs(r) - abs(math.log(E6 / c["emp"])),
                     "removal_km": (c[f"f3t{TI_2}_climb"] - c[f"f3t{TI_6}_climb"])
                     / (c["m_hat"] * G / KEFF) / (c["x_m"] / 1000),
                     "hplus_km": c["hplus"] / (c["x_m"] / 1000)})
    print(f"\n  B — the absorber signature (train, n = {len(rows)}; "
          f"eps2 = {e2:.4f}, eps6 = {e6:.4f})")
    r_ = [q["resid_tau2"] for q in rows]
    d_ = [q["delta_geom"] for q in rows]
    b_ = [q["benefit"] for q in rows]
    print(f"    rho(benefit, resid)          = {spearman(b_, r_):+.3f}   "
          f"(mechanical — reported for completeness)")
    print(f"    rho(benefit, delta_geom)     = {spearman(b_, d_):+.3f}")
    print(f"    rho(delta_geom, resid) POOLED = {spearman(d_, r_):+.3f}   "
          f"<- the coupling that lets tau=6 win")
    per_g = []
    print(f"    {'group':<12} {'n':>5} {'rho(delta,resid)':>17} "
          f"{'med resid':>10} {'med delta':>10}")
    for g in GROUPS:
        sub = [q for q in rows if q["group"] == g]
        if len(sub) < MIN_HALF:
            continue
        rg = spearman([q["delta_geom"] for q in sub],
                      [q["resid_tau2"] for q in sub])
        per_g.append((g, len(sub), rg,
                      med_of([q["resid_tau2"] for q in sub]),
                      med_of([q["delta_geom"] for q in sub])))
        print(f"    {g:<12} {len(sub):>5} {rg:>17.3f} "
              f"{per_g[-1][3]:>10.4f} {per_g[-1][4]:>10.4f}")
    if len(per_g) >= 3:
        within = med_of([p[2] for p in per_g])
        between = spearman([p[4] for p in per_g], [p[3] for p in per_g])
        print(f"    WITHIN-rider coupling (median of per-group rho) = {within:+.3f}")
        print(f"    BETWEEN-rider coupling (rider medians, n = {len(per_g)}) "
              f"= {between:+.3f}")
    else:
        print(f"    (within/between decomposition needs >=3 groups with "
              f">= {MIN_HALF} rides — {len(per_g)} available)")
    print(f"    geometry covariates of the misfit, within riders:")
    for tag, key in (("removal/km", "removal_km"), ("h+/km", "hplus_km")):
        per = [spearman([q[key] for q in rows if q["group"] == g],
                        [q["resid_tau2"] for q in rows if q["group"] == g])
               for g, n, *_ in per_g]
        print(f"      rho({tag:>10}, resid) per-rider median = "
              f"{med_of(per):+.3f}")
    out = os.path.join(RESULTS, "e67_signature" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for q in rows:
            w.writerow(q)
    print(f"    wrote {os.path.basename(out)}")


def part_c(train) -> None:
    print(f"\n  C — stationarity: within-rider early/late halves "
          f"(activity order as chronology; halves < {MIN_HALF} rides skipped)")
    print(f"    {'group':<12} {'n/2':>4} {'tau*_e':>6} {'tau*_l':>6} "
          f"{'eps_e':>7} {'eps_l':>7} {'eps5_e':>7} {'eps5_l':>7} "
          f"{'age F3':>7} {'age F5f':>7}")
    out_rows = []
    for g in GROUPS:
        sub = [r for r in train if r["group"] == g]
        sub.sort(key=lambda r: int(r["ride"].rsplit("#", 1)[1]))
        h = len(sub) // 2
        if h < MIN_HALF:
            continue
        early, late = sub[:h], sub[h:]
        fits = {}
        for tag, half in (("e", early), ("l", late)):
            eps, _c, ti = fit(half, "F3")
            e5, k5 = fit_f5f(half)
            fits[tag] = {"eps": eps, "ti": ti, "e5": e5, "k5": k5}
        # aging: late half scored with EARLY constants minus its own best —
        # the in-time transfer penalty, per form (same loss as the CV)
        age3 = (cv_loss(late, "F3", fits["e"]["eps"], C_PUB, fits["e"]["ti"])
                - cv_loss(late, "F3", fits["l"]["eps"], C_PUB, fits["l"]["ti"]))
        age5 = (cv_loss5(late, fits["e"]["e5"], fits["e"]["k5"])
                - cv_loss5(late, fits["l"]["e5"], fits["l"]["k5"]))
        row = {"group": g, "n_half": h,
               "tau_early": TAU_GRID[fits["e"]["ti"]],
               "tau_late": TAU_GRID[fits["l"]["ti"]],
               "eps3_early": fits["e"]["eps"], "eps3_late": fits["l"]["eps"],
               "eps5_early": fits["e"]["e5"], "eps5_late": fits["l"]["e5"],
               "aging_f3": age3, "aging_f5f": age5}
        out_rows.append(row)
        print(f"    {g:<12} {h:>4} {row['tau_early']:>6.1f} "
              f"{row['tau_late']:>6.1f} {row['eps3_early']:>7.4f} "
              f"{row['eps3_late']:>7.4f} {row['eps5_early']:>7.4f} "
              f"{row['eps5_late']:>7.4f} {age3:>7.5f} {age5:>7.5f}")
    if out_rows:
        n_move = sum(1 for r in out_rows if r["tau_early"] != r["tau_late"])
        print(f"    tau* moved early->late in {n_move}/{len(out_rows)} riders; "
              f"median aging penalty F3 "
              f"{med_of([r['aging_f3'] for r in out_rows]):.5f} vs F5f "
              f"{med_of([r['aging_f5f'] for r in out_rows]):.5f} "
              f"(lower = constants transfer forward in time better)")
        out = os.path.join(RESULTS, "e67_stability" + SUFF + ".csv")
        with open(out, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            for r in out_rows:
                w.writerow(r)
        print(f"    wrote {os.path.basename(out)}")


def main() -> None:
    rows = join_tolls(load())      # e63's tolls at tau_n = 2 for F5f
    train, _test = split(rows)
    print(f"Entry 67 — absorber or physics? (train {len(train)}, tau_n arm "
          f"{TAUN5:g} m)" + ("   [SMOKE]" if SMOKE else ""))
    part_b(train)
    part_c(train)


if __name__ == "__main__":
    main()
