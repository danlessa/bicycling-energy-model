#!/usr/bin/env python3
"""Entry 60 — two eps pools, one per landscape, through the full chain.

The diagnostic that prompted this held tau and the form fixed at the pooled
fit's choices, so it could not tell whether the regional gap is a property of
eps or an artefact of evaluating both regions under one region's structure.
This runs the selection independently per region and then scores each region's
held-out rides once.

Three arms, all on the same split:
  A  one pool          the incumbent: one eps for everything
  B  regional eps      form and tau from the pooled selection, eps per region
  C  regional chain    form, tau and eps all selected within the region

B vs C is the question P2 asks: if C beats B materially, the regions differ in
more than eps and the paper cannot ship one form.

Output: data/results/e60_regional.csv + console report.
Run: python3 src/harness/e60_regional.py
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
from e52_build import FORMS, GROUPS, TAU_GRID
from perride_invert import RESULTS
from skc_compare import boot_ci_strat, med_of, sign_p

SEED = 52
BR = {"D3", "D4", "D5"}
REGIONS = ("D3-D5 (São Paulo)", "D6 (Europe)")


def region_of(r: dict) -> str:
    return REGIONS[0] if r["group"] in BR else REGIONS[1]


def score(rows, form, eps, c, ti, seed):
    a = [abs(v) for v in S.pct(rows, form, eps, c, ti)]
    sg = S.pct(rows, form, eps, c, ti)
    gs = [[abs(x) for x in S.pct([r for r in rows if r["group"] == g], form, eps, c, ti)]
          for g in GROUPS]
    ci = boot_ci_strat([x for x in gs if x], seed)
    return med_of(a), ci, med_of(sg), a


def main() -> None:
    rows = S.load()
    train, test = S.split(rows)
    tr = {k: [r for r in train if region_of(r) == k] for k in REGIONS}
    te = {k: [r for r in test if region_of(r) == k] for k in REGIONS}
    print("Entry 60 — regional eps pools through the full chain")
    for k in REGIONS:
        print(f"  {k:<20} train {len(tr[k]):>5}   test {len(te[k]):>4}")

    # ---- arm A: the incumbent single pool
    e_a, c_a, ti_a = S.fit(train, "F3")
    print(f"\n  A · one pool          F3, eps = {to_fixed(e_a, 4)}, tau = {TAU_GRID[ti_a]} m")

    # ---- arm C: an independent selection inside each region
    print(f"\n  C · regional selection (does the region want a different FORM or tau?)")
    print(f"    {'region':<20} {'winner':>7} {'CV':>9} {'eps':>8} {'tau':>6} {'c':>7}")
    sel = {}
    for k in REGIONS:
        cv = S.cross_validate(tr[k])
        w = S.select(tr[k], cv)
        sel[k] = (w["form"], cv[w["form"]]["eps"], cv[w["form"]]["c"], cv[w["form"]]["ti"])
        print(f"    {k:<20} {w['form']:>7} {cv[w['form']]['cv']:>9.5f} "
              f"{to_fixed(cv[w['form']]['eps'], 4):>8} {TAU_GRID[cv[w['form']]['ti']]:>6} "
              f"{to_fixed(cv[w['form']]['c'], 2) if w['form'] == 'F4' else '—':>7}")

    # ---- arm B: pooled form and tau, regional eps
    eps_b = {}
    for k in REGIONS:
        lo, hi = S.EPS_BOUNDS
        best = 0.2
        for _ in range(5):
            step = (hi - lo) / 200
            cand = [lo + i * step for i in range(201)]
            best = min(cand, key=lambda e: S.cv_loss(tr[k], "F3", e, c_a, ti_a))
            lo, hi = best - step, best + step
        eps_b[k] = best
    print(f"\n  B · regional eps, pooled form+tau: "
          + " · ".join(f"{k.split()[0]} {to_fixed(eps_b[k], 4)}" for k in REGIONS))

    # ---- held-out, scored once per region
    print(f"\n  HELD-OUT (scored once)")
    print(f"    {'region':<20} {'arm':<22} {'med|D%|':>8} {'[95% CI]':<16} {'signed':>8}")
    out, keep = [], {}
    for k in REGIONS:
        base = None
        for tag, (form, eps, c, ti) in (
                ("A one pool", ("F3", e_a, c_a, ti_a)),
                ("B regional eps", ("F3", eps_b[k], c_a, ti_a)),
                ("C regional chain", sel[k])):
            m, ci, sg, arr = score(te[k], form, eps, c, ti, SEED)
            if base is None:
                base, keep[k] = arr, arr
            d = "" if tag.startswith("A") else f"   {m - med_of(base):+.2f} pp"
            print(f"    {k:<20} {tag:<22} {to_fixed(m, 2):>8} "
                  f"[{to_fixed(ci[0], 2)}, {to_fixed(ci[1], 2)}]".ljust(17)
                  + f"{to_fixed(sg, 2):>8}{d}")
            out.append((k, tag, form, eps, m, sg))
            if tag.startswith("B"):
                w = sum(1 for x, y in zip(arr, base) if x < y)
                l = sum(1 for x, y in zip(arr, base) if x > y)
                print(f"    {'':<20} {'  paired vs A':<22} closer on {w}/{w + l}, "
                      f"p = {to_fixed(sign_p(w, l), 4)}")
        print()

    # ---- P3: does F4 split the same way?
    print("  P3 — F4 under the same treatment")
    for k in REGIONS:
        e4, c4, ti4 = S.fit(tr[k], "F4")
        m, _, sg, _ = score(te[k], "F4", e4, c4, ti4, SEED)
        print(f"    {k:<20} eps = {to_fixed(e4, 4)}  c = {to_fixed(c4, 2)}  "
              f"held-out {to_fixed(m, 2)}")
        out.append((k, "F4 regional", "F4", e4, m, sg))

    path = os.path.join(RESULTS, "e60_regional.csv")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("region,arm,form,eps,test_med_abs,test_med_signed\n")
        for k, tag, form, eps, m, sg in out:
            fh.write(f'"{k}","{tag}",{form},{to_fixed(eps, 4)},'
                     f"{to_fixed(m, 4)},{to_fixed(sg, 4)}\n")
    print(f"\nwrote {os.path.basename(path)}")


if __name__ == "__main__":
    main()
