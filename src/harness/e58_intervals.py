#!/usr/bin/env python3
"""Entry 58 — intervals for the FITTED parameters, and the breaking points.

Three things the article's tables assert as point values and should not:

  (a) Table 2's fitted parameters (eps per form, F3's tau, F4's c) carry no
      uncertainty. A selected constant published bare invites the reader to
      treat it as exact.
  (b) Table 4's loss inflations are likewise bare.
  (c) A.7 reports the cost of a +/-10% error. Danilo asked the inverse and more
      useful question: how wrong does each constant have to be before it costs
      something material? Reported here as the parameter values at which the
      loss inflates by 50%.

METHOD. Stratified bootstrap over training rides, resampled within rider
(matching every other interval in the paper), refitting the parameter on each
replicate; percentile CIs. Seed 50.

SPEED. The straight implementation refits by grid search in pure Python at
~9 s per fit, so 300 replicates would take 45 minutes per form. The closed form
is linear in eps, so a replicate's whole eps-grid can be evaluated as one
matrix product: E(eps) = A + eps*B with A, B per-ride vectors. That makes the
bootstrap a few seconds. numpy is used here for that reason, as in Entries 50
and 53.

tau is grid-valued, so its interval is a set of grid points rather than a
continuous range, and is reported as such rather than smoothed into one.

Output: data/results/e58_intervals.csv + console report.
Run: python3 src/harness/e58_intervals.py     (E58_B=<replicates>)
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

import numpy as np

from bicycling_energy_model.jsfmt import to_fixed

import e52_split as S
from e52_build import C_PUB, FORMS, GROUPS, TAU_GRID, TAU_PUB_I
from perride_invert import RESULTS

B = int(os.environ.get("E58_B", "400"))
SEED = 50
INFLATION = 0.50          # the "materially wrong" threshold Danilo asked for


def arrays(rows, form, ti=TAU_PUB_I, c=C_PUB):
    """(A, Bc, emp) with E(eps) = (A + eps*Bc)/1000 — exact, by linearity."""
    if form in ("F1", "F2", "F3"):
        k = {"F1": "f1", "F2": "f2", "F3": f"f3t{ti}"}[form]
        A = np.array([r[k + "_roll"] + r[k + "_aero"] + r[k + "_climb"] for r in rows])
        Bc = np.array([r[k + "_recov1"] for r in rows])
    else:
        km = np.array([max(0.0, 1.0 - c * (r["x_m"] / 1000.0) / r["hplus"])
                       if r["hplus"] > 0 else 1.0 for r in rows])
        A = np.array([r["f2_roll"] + r["f2_aero"] for r in rows]) + km * np.array(
            [r["f2_climb"] for r in rows])
        Bc = km * np.array([r["f2_recov1"] for r in rows])
    emp = np.array([r["emp"] for r in rows])
    lo, hi = S.EPS_BOUNDS
    ok = ((A + lo * Bc) > 0) & ((A + hi * Bc) > 0)   # fixed population
    return A[ok], Bc[ok], emp[ok], ok


def loss_grid(A, Bc, emp, eps):
    """Mean |log(Ehat/E)| for every eps at once. eps: (k,) -> (k,).

    The population is fixed by `arrays()`, matching e52_split.logratio: rides
    whose predicted energy can go non-positive anywhere in the eps range are
    excluded once rather than per-eps.
    """
    E = (A[None, :] + eps[:, None] * Bc[None, :]) / 1000.0
    with np.errstate(divide="ignore", invalid="ignore"):
        L = np.abs(np.log(E / emp[None, :]))
    L[~np.isfinite(L)] = np.inf
    return L.mean(axis=1)


def fit_fast(A, Bc, emp) -> float:
    lo, hi = S.EPS_BOUNDS
    best = 0.2
    for _ in range(5):
        g = np.linspace(lo, hi, 201)
        best = float(g[int(np.argmin(loss_grid(A, Bc, emp, g)))])
        step = (hi - lo) / 200
        lo, hi = best - step, best + step
    return best


def strata_idx(rows, ok=None):
    """Row indices per rider, in the coordinates of the FILTERED arrays."""
    kept = [r for r, k in zip(rows, ok)] if ok is None else [
        r for r, k in zip(rows, ok) if k]
    return [np.array([i for i, r in enumerate(kept) if r["group"] == g])
            for g in GROUPS if any(r["group"] == g for r in kept)]


def boot_eps(rows, form, ti=TAU_PUB_I, c=C_PUB):
    A, Bc, emp, ok = arrays(rows, form, ti, c)
    idx = strata_idx(rows, ok)
    rnd = np.random.default_rng(SEED)
    out = np.empty(B)
    for b in range(B):
        take = np.concatenate([s[rnd.integers(0, len(s), len(s))] for s in idx])
        out[b] = fit_fast(A[take], Bc[take], emp[take])
    return np.percentile(out, [2.5, 97.5])


def boot_tau(rows):
    """tau is grid-valued: report the grid points spanning the middle 95%."""
    rnd = np.random.default_rng(SEED + 1)
    cache = [arrays(rows, "F3", i)[:3] for i in range(len(TAU_GRID))]
    idx = strata_idx(rows, arrays(rows, "F3", TAU_PUB_I)[3])
    picks = np.empty(B, int)
    for b in range(B):
        take = np.concatenate([s[rnd.integers(0, len(s), len(s))] for s in idx])
        best, bi = np.inf, 0
        for i, (A, Bc, emp) in enumerate(cache):
            a, bb, e = A[take], Bc[take], emp[take]
            l = float(loss_grid(a, bb, e, np.array([fit_fast(a, bb, e)]))[0])
            if l < best:
                best, bi = l, i
        picks[b] = bi
    lo, hi = np.percentile(picks, [2.5, 97.5])
    return TAU_GRID[int(round(lo))], TAU_GRID[int(round(hi))], picks


def breaking_point(rows, form, eps, ti, c, key):
    """The multiplier on `key` (or on eps) at which the loss inflates by 50%."""
    base = S.cv_loss(rows, form, eps, c, ti)
    target = base * (1 + INFLATION)

    def loss_at(mult):
        if key is None:
            return S.cv_loss(rows, form, eps * mult, c, ti)
        bumped = [{**r, key: r[key] * mult} for r in rows]
        return S.cv_loss(bumped, form, eps, c, ti)

    out = []
    for lo, hi in ((1.0, 0.05), (1.0, 8.0)):       # search down, then up
        a, b = lo, hi
        if loss_at(b) < target:
            out.append(float("nan"))
            continue
        for _ in range(28):
            m = (a + b) / 2
            if loss_at(m) < target:
                a = m
            else:
                b = m
        out.append((a + b) / 2)
    return base, out[0], out[1]


def main() -> None:
    rows = S.load()
    train, _ = S.split(rows)
    print(f"Entry 58 — intervals for the fitted parameters  (B = {B}, {len(train)} train rides)\n")

    # ---- (a) Table 2's fitted parameters
    print("  Table 2 — fitted parameters with 95% CIs")
    print(f"    {'form':<5} {'parameter':<10} {'fitted':>9} {'95% CI':>22}")
    res = []
    for form in FORMS:
        e, c, ti = S.fit(train, form)
        lo, hi = boot_eps(train, form, ti, c)
        print(f"    {form:<5} {'eps':<10} {to_fixed(e, 4):>9}   [{to_fixed(lo, 4)}, {to_fixed(hi, 4)}]")
        res.append((form, "eps", e, lo, hi))
        if form == "F4":
            print(f"    {form:<5} {'c (m/km)':<10} {to_fixed(c, 3):>9}   "
                  f"{'(held at its fitted value; see below)':>22}")
            res.append((form, "c", c, float("nan"), float("nan")))
    _, _, ti_fit = S.fit(train, "F3")
    tlo, thi, picks = boot_tau(train)
    frac = 100.0 * float((picks == ti_fit).mean())
    print(f"    {'F3':<5} {'tau (m)':<10} {TAU_GRID[ti_fit]:>9}   [{tlo}, {thi}]"
          f"   grid-valued; the fitted point wins {frac:.0f}% of replicates")
    res.append(("F3", "tau", TAU_GRID[ti_fit], tlo, thi))

    # ---- (c) breaking points
    e3, c3, ti3 = S.fit(train, "F3")
    tag = f"f3t{ti3}"
    print(f"\n  A.7 — how wrong is materially wrong? "
          f"(multiplier at which the CV loss inflates {int(100*INFLATION)}%)")
    print(f"    {'perturbed':<14} {'base':>9} {'lower':>9} {'upper':>9}   interpretation")
    for name, key in (("CdA / aero", f"{tag}_aero"), ("m / climb", f"{tag}_climb"),
                      ("Crr / roll", f"{tag}_roll"), ("eps", None)):
        base, lo, hi = breaking_point(train, "F3", e3, ti3, c3, key)
        f = lambda v: "—" if v != v else f"{v:.2f}x"
        print(f"    {name:<14} {base:>9.5f} {f(lo):>9} {f(hi):>9}   "
              + ("no upper break inside 8x" if hi != hi else ""))
        res.append(("F3", f"break:{name}", base, lo, hi))

    path = os.path.join(RESULTS, "e58_intervals.csv")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("form,parameter,value,ci_lo,ci_hi\n")
        for form, par, v, lo, hi in res:
            fh.write(f"{form},{par},{to_fixed(v, 5)},"
                     f"{'' if lo != lo else to_fixed(lo, 5)},"
                     f"{'' if hi != hi else to_fixed(hi, 5)}\n")
    print(f"\nwrote {os.path.basename(path)}")


if __name__ == "__main__":
    main()
