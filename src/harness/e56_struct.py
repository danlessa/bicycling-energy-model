#!/usr/bin/env python3
"""Entry 56 — sensitivity of the STRUCTURAL parameters tau and c.

Section 3.2 prices the four constants a USER supplies (m, CdA, Crr, eps). This
prices the two the METHOD supplies: F3's deadband tau and F4's climb-fraction
scalar c. Those are numbers this paper publishes and a user inherits without
choosing, so their sensitivity is the paper's own exposure and answers a
different question -- how precisely do they have to be stated?

Entry 55 gave direct reason to ask: tau moved 2 m -> 6 m and c moved
0.03 -> 1.18 purely because the aero estimator changed, so both are entangled
with the physics rather than free-standing.

METRIC, matching section 3.2 so the tables read side by side: LOSS INFLATION --
the percentage increase in CV loss when a parameter is moved +/-10% off its
fitted optimum, worse side reported. Not a derivative: each parameter sits at a
minimum where the derivative is ~0 by construction (the error Entry 52's first
A.7 made).

tau is cached on a grid, refined in e52_build.py to carry the +/-10% and +/-25%
neighbours of the plausible optima, so the figure is exact rather than
interpolated -- the loss is quadratic near its minimum and interpolation would
understate the curvature being measured.

Also reports the full loss profile over each parameter's range, which shows
whether a parameter is sharply peaked or nearly flat.

Output: data/results/e56_struct.csv + console report.
Run: python3 src/harness/e56_struct.py     (E52_AERO=seg for the other arm)
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model.jsfmt import to_fixed

import e52_split as S
from e52_build import AERO, C_PUB, TAU_GRID
from perride_invert import RESULTS


def nearest(target: float) -> int:
    """Index of the grid tau closest to `target`."""
    return min(range(len(TAU_GRID)), key=lambda i: abs(TAU_GRID[i] - target))


def main() -> None:
    rows = S.load()
    train, _ = S.split(rows)
    print(f"Entry 56 — structural-parameter sensitivity  [aero = {AERO}]")
    print(f"  fitting on {len(train)} training rides\n")

    # --- fitted optima, refit here rather than assumed
    e3, _, ti3 = S.fit(train, "F3")
    e4, c4, _ = S.fit(train, "F4")
    tau = TAU_GRID[ti3]
    print(f"  F3: eps = {to_fixed(e3, 4)}  tau = {tau} m")
    print(f"  F4: eps = {to_fixed(e4, 4)}  c   = {to_fixed(c4, 3)} m/km\n")

    base3 = S.cv_loss(train, "F3", e3, C_PUB, ti3)
    base4 = S.cv_loss(train, "F4", e4, c4)

    out = []

    # --- tau, exact on the refined grid
    lo_i, hi_i = nearest(tau * 0.9), nearest(tau * 1.1)
    lo = S.cv_loss(train, "F3", e3, C_PUB, lo_i)
    hi = S.cv_loss(train, "F3", e3, C_PUB, hi_i)
    infl_t = max(lo, hi) / base3 - 1.0
    print(f"  tau  {TAU_GRID[lo_i]} <- {tau} -> {TAU_GRID[hi_i]} m"
          f"   loss {lo:.5f} / {base3:.5f} / {hi:.5f}")
    out.append(("tau (F3 deadband)", tau, "m", infl_t))

    # --- c, continuous
    lo = S.cv_loss(train, "F4", e4, c4 * 0.9)
    hi = S.cv_loss(train, "F4", e4, c4 * 1.1)
    infl_c = max(lo, hi) / base4 - 1.0
    print(f"  c    {c4*0.9:.3f} <- {c4:.3f} -> {c4*1.1:.3f} m/km"
          f"   loss {lo:.5f} / {base4:.5f} / {hi:.5f}")
    out.append(("c (F4 scalar)", c4, "m/km", infl_c))

    # --- eps under each form, for a like-for-like anchor against section 3.2
    for form, e, extra, base in (("F3", e3, ti3, base3), ("F4", e4, c4, base4)):
        if form == "F3":
            l = S.cv_loss(train, form, e * 0.9, C_PUB, extra)
            h = S.cv_loss(train, form, e * 1.1, C_PUB, extra)
        else:
            l = S.cv_loss(train, form, e * 0.9, extra)
            h = S.cv_loss(train, form, e * 1.1, extra)
        out.append((f"eps ({form}, for reference)", e, "—", max(l, h) / base - 1.0))

    print(f"\n  {'parameter':<28} {'fitted':>9} {'unit':>6} {'loss inflation at ±10%':>24}")
    for name, val, unit, infl in sorted(out, key=lambda z: -z[3]):
        print(f"  {name:<28} {to_fixed(val, 3):>9} {unit:>6} {100*infl:>23.1f}%")

    # --- profiles: is it peaked or flat?
    print(f"\n  tau profile (F3, eps fixed at its optimum)")
    print(f"    {'tau (m)':>8} {'CV loss':>10} {'vs optimum':>12}")
    for i, t in enumerate(TAU_GRID):
        l = S.cv_loss(train, "F3", e3, C_PUB, i)
        mark = "  <- fitted" if i == ti3 else ""
        print(f"    {t:>8.1f} {l:>10.5f} {100*(l/base3-1):>11.1f}%{mark}")

    print(f"\n  c profile (F4, eps fixed at its optimum)")
    print(f"    {'c (m/km)':>9} {'CV loss':>10} {'vs optimum':>12}")
    for c in (0.0, 0.25, 0.5, 0.75, 1.0, c4, 1.5, 2.0, 3.0, 4.0):
        l = S.cv_loss(train, "F4", e4, c)
        mark = "  <- fitted" if abs(c - c4) < 1e-9 else ""
        print(f"    {c:>9.2f} {l:>10.5f} {100*(l/base4-1):>11.1f}%{mark}")

    path = os.path.join(RESULTS, "e56_struct" + ("" if AERO == "reg" else "." + AERO) + ".csv")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("parameter,fitted,unit,loss_inflation_pct\n")
        for name, val, unit, infl in out:
            fh.write(f'"{name}",{to_fixed(val, 4)},{unit},{to_fixed(100*infl, 3)}\n')
    print(f"\nwrote {os.path.basename(path)}")


if __name__ == "__main__":
    main()
