#!/usr/bin/env python3
"""Entry 46 — implementing the regime switch registered in the journal.

Paper 1 section 3.3 recommends the dynamic estimator on mean descent grades
>= 3% and the flat eps_f = 0.20 otherwise. NO HARNESS IMPLEMENTS IT: every
published eps_d column applies the dynamic estimator to every ride, including
the ~52% of all scored rides (69% of Table 3's own corpora) whose mean descent
grade falls below the threshold. This entry builds the switch as new columns
beside the existing ones. Nothing published is overwritten.

Four arms, as registered — {constant, grade-inverse} x {unswitched, switched}:

    A  const_unsw   eps = eps_coast - 0.13                     (today's column)
    B  const_sw     eps = eps_coast - 0.13   if s_bar >= 3%, else 0.20
    C  grade_unsw   eps = eps_coast - k/s_bar                  k = 0.0051
    D  grade_sw     eps = eps_coast - k/s_bar if s_bar >= 3%, else 0.20

SECOND-ORDER OUTPUT. This reads `e47_formselect.csv` rather than re-parsing the
tracks: that file already carries, per ride, the closed form evaluated at eps = 0
and eps = 1 under both parameter arms. approximate() is exactly linear in eps
(recov = -beta*eps*h_minus and nothing else reads it), so those two points pin
the whole family and any eps can be scored in closed form. In the notation this
is O_46 = T(O_47) -- an output derived from an output, not from D. The practical
consequence is that Entries 46 and 47 share a population by construction, which
is what makes the paired sign tests below legitimate.

s_bar is eps_cells' drop-weighted mean descent grade -- the quantity every
published harness gates on and the one Entry 45 fitted k against. The OTHER
definition (eps_geom's own cells) is carried in the same CSV and is reported as
a sensitivity, because the two disagree on a handful of rides.

Output: data/results/e46_switch.csv (per ride, four arms) + console scoreboard.
Run: python3 src/harness/e46_switch.py
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import is_finite
from bicycling_energy_model.jsfmt import to_fixed

from skc_compare import RESULTS, boot_ci, boot_ci_strat, med_of, sign_p

EPS0 = 0.13          # the published constant
K_EQ8 = 0.0051       # eq. (8)'s constant, fitted in Entry 45
EPS_F = 0.20         # the flat constant, selected on D2
GATE = 0.03          # section 3.3's rule
ARMS = ("const_unsw", "const_sw", "grade_unsw", "grade_sw")
POOL35 = ("D3", "D4", "D5")
POOL36 = ("D3", "D4", "D5", "D6-user_1", "D6-user_2", "D6-user_3", "D6-user_5")


def fnum(r: dict, k: str) -> float:
    try:
        return float(r[k])
    except (KeyError, ValueError, TypeError):
        return float("nan")


def eps_of(arm: str, eps_coast: float, s_bar: float) -> float:
    """The four arms. Deliberately UNCLAMPED, matching engines.eps_geom."""
    if arm in ("const_sw", "grade_sw") and s_bar < GATE:
        return EPS_F
    delta = EPS0 if arm.startswith("const") else K_EQ8 / s_bar
    return eps_coast - delta


def load(pfx: str, sbar_col: str) -> list[dict]:
    """Per-ride rows with all four arms scored, under parameter arm `pfx`."""
    import csv
    path = os.path.join(RESULTS, "e47_formselect.csv")
    out = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            e0, e1 = fnum(r, pfx + "_E0"), fnum(r, pfx + "_E1")
            emp, sb = fnum(r, "emp"), fnum(r, pfx + sbar_col)
            ec = fnum(r, pfx + "_eps_coast")
            if not all(is_finite(v) for v in (e0, e1, emp, sb, ec)) or emp <= 0 or sb <= 0:
                continue
            row = {"group": r["group"].strip('"'), "ride": r["ride"].strip('"'),
                   "s_bar": sb, "eps_coast": ec, "emp": emp, "real": sb >= GATE}
            for a in ARMS:
                eps = eps_of(a, ec, sb)
                row[a + "_eps"] = eps
                row[a] = 100.0 * ((e0 + (e1 - e0) * eps) / 1000 - emp) / emp
            out.append(row)
    return out


def line(tag: str, rows: list[dict], arm: str, strata: list[str] | None = None) -> None:
    v = [r[arm] for r in rows]
    a = [abs(x) for x in v]
    if strata:
        gs = [[abs(r[arm]) for r in rows if r["group"] == g] for g in strata]
        gs = [x for x in gs if x]
        ci_a = boot_ci_strat(gs, 42)
        gs2 = [[r[arm] for r in rows if r["group"] == g] for g in strata]
        ci_s = boot_ci_strat([x for x in gs2 if x], 43)
    else:
        ci_a, ci_s = boot_ci(a, 42), boot_ci(v, 43)
    print(f"    {tag:<14} {to_fixed(med_of(a), 2):>7} "
          f"[{to_fixed(ci_a[0], 2)}, {to_fixed(ci_a[1], 2)}]".ljust(22)
          + f" {to_fixed(med_of(v), 2):>7} "
          f"[{to_fixed(ci_s[0], 2)}, {to_fixed(ci_s[1], 2)}]")


def paired(rows: list[dict], arm: str, base: str = "const_unsw") -> str:
    w = sum(1 for r in rows if abs(r[arm]) < abs(r[base]))
    l = sum(1 for r in rows if abs(r[arm]) > abs(r[base]))
    if w + l == 0:
        return "identical"
    return f"{w}/{w + l} p={to_fixed(sign_p(w, l), 4)}"


def report(rows: list[dict], title: str) -> None:
    print(f"\n{'=' * 76}\n{title}\n{'=' * 76}")
    n_lo = sum(1 for r in rows if not r["real"])
    print(f"  {len(rows)} rides · {n_lo} ({to_fixed(100 * n_lo / len(rows), 0)}%) "
          f"below the 3% gate — the population the switch acts on")

    groups = sorted({r["group"] for r in rows})
    for g in groups + ["POOL D3-D5", "POOL D3-D6"]:
        if g.startswith("POOL"):
            keys = POOL35 if "D3-D5" in g else POOL36
            sub = [r for r in rows if r["group"] in keys]
            strata = list(keys)
        else:
            sub = [r for r in rows if r["group"] == g]
            strata = None
        if not sub:
            continue
        lo = sum(1 for r in sub if not r["real"])
        print(f"\n  {g}  (n = {len(sub)}, {to_fixed(100 * lo / len(sub), 0)}% below gate)")
        print(f"    {'arm':<14} {'med |D%|':>7} {'[95% CI]':<22} {'signed':>7} [95% CI]")
        for a in ARMS:
            line(a, sub, a, strata)
        for a in ARMS[1:]:
            print(f"      vs const_unsw · {a:<11} {paired(sub, a)}")


def verdicts(rows: list[dict]) -> None:
    print(f"\n{'=' * 76}\nREGISTERED PREDICTIONS\n{'=' * 76}")

    def med(sub, a):
        return med_of([abs(r[a]) for r in sub])

    gentle, open_ = ("D2", "D4"), ("D3", "D5")
    print("\n  P1 — switching improves the gentle-terrain corpora, barely moves the open ones")
    for g in gentle + open_ + ("D6-user_2",):
        sub = [r for r in rows if r["group"] == g]
        if not sub:
            continue
        d = med(sub, "const_sw") - med(sub, "const_unsw")
        kind = "gentle" if g in gentle else "open  "
        print(f"    {g:<12} {kind}  const_unsw {to_fixed(med(sub, 'const_unsw'), 2)} "
              f"-> const_sw {to_fixed(med(sub, 'const_sw'), 2)}  "
              f"({'improves' if d < -0.05 else 'worsens' if d > 0.05 else 'flat'} "
              f"{to_fixed(d, 2)} pp)")

    print("\n  P2 — WITH the switch, grade-inverse beats the constant on the open corpora")
    for g in open_ + ("D6-user_1", "D6-user_2", "D6-user_3"):
        sub = [r for r in rows if r["group"] == g]
        if not sub:
            continue
        d = med(sub, "grade_sw") - med(sub, "const_sw")
        print(f"    {g:<12} const_sw {to_fixed(med(sub, 'const_sw'), 2)} vs "
              f"grade_sw {to_fixed(med(sub, 'grade_sw'), 2)}  "
              f"({'grade-inverse wins' if d < 0 else 'constant wins'} "
              f"by {to_fixed(abs(d), 2)} pp)")

    print("\n  P3 — UNSWITCHED, grade-inverse is worse than the constant  [the one that matters]")
    allr = rows
    d = med(allr, "grade_unsw") - med(allr, "const_unsw")
    print(f"    all corpora  const_unsw {to_fixed(med(allr, 'const_unsw'), 2)} vs "
          f"grade_unsw {to_fixed(med(allr, 'grade_unsw'), 2)}  "
          f"-> grade-inverse is {'WORSE' if d > 0 else 'better'} by "
          f"{to_fixed(abs(d), 2)} pp")
    below = [r for r in allr if not r["real"]]
    above = [r for r in allr if r["real"]]
    print(f"    below 3% (n={len(below)}): const {to_fixed(med(below, 'const_unsw'), 2)} vs "
          f"grade {to_fixed(med(below, 'grade_unsw'), 2)}")
    print(f"    at/above 3% (n={len(above)}): const {to_fixed(med(above, 'const_unsw'), 2)} vs "
          f"grade {to_fixed(med(above, 'grade_unsw'), 2)}")
    worst = max(allr, key=lambda r: abs(r["grade_unsw"]))
    print(f"    worst unswitched grade-inverse ride: s_bar = "
          f"{to_fixed(100 * worst['s_bar'], 2)}%, k/s_bar = "
          f"{to_fixed(K_EQ8 / worst['s_bar'], 2)}, D% = {to_fixed(worst['grade_unsw'], 0)}")


def main() -> None:
    print("Entry 46 — the regime switch, implemented")
    rows = load("ag", "_sbar_cells")
    report(rows, "PRIMARY — frozen priors P_a,g, switch on eps_cells' s_bar")
    verdicts(rows)

    rows_fr = load("fr", "_sbar_cells")
    report(rows_fr, "SECONDARY — per-ride inverted physics P_f,r")

    # sensitivity: the other s_bar definition
    alt = load("ag", "_s_bar")
    print(f"\n{'=' * 76}\nGATE SENSITIVITY — switch on eps_geom's s_bar instead\n{'=' * 76}")
    for a in ARMS:
        print(f"    {a:<14} {to_fixed(med_of([abs(r[a]) for r in alt]), 2):>7} "
              f"(primary {to_fixed(med_of([abs(r[a]) for r in rows]), 2)})")

    cols = ["group", "ride", "s_bar", "eps_coast", "emp", "real"] + \
           [a + s for a in ARMS for s in ("", "_eps")]
    with open(os.path.join(RESULTS, "e46_switch.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(
                (f'"{r[c]}"' if isinstance(r[c], str)
                 else ("true" if r[c] else "false") if isinstance(r[c], bool)
                 else to_fixed(r[c], 6) if is_finite(r[c]) else "")
                for c in cols) + "\n")
    print(f"\nwrote e46_switch.csv ({len(rows)} rides)")


if __name__ == "__main__":
    main()
