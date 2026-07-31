#!/usr/bin/env python3
"""Entry 54 — leave-one-rider-out transfer of the flat epsilon.

Entry 52 fitted eps = 0.288 on 1,734 rides drawn from all seven riders, so every
rider contributed to the constant later scored on all seven. That measures the
FORM's accuracy honestly -- the held-out rides chose neither form nor constant --
but it cannot answer the reader's actual question: if I take the published
number, having contributed nothing to it, does it work for me?

DESIGN, as registered (MODEL_COMPARISON_JOURNAL.md, Entry 54):
  donor      for each rider r, fit the flat eps on r's TRAINING-half rides
             alone, same loss as Entry 52 (mean |log(Ehat/E)|), at the selected
             form F3 at its FITTED tau.
  recipients score that eps on every OTHER rider's TEST-half rides. Strict
             transfer: a different person, and rides already held out from
             Entry 52's selection.
  compare    against the pooled eps = 0.288 the paper would publish, and
             against each recipient's OWN best eps -- the unreachable ceiling.
  report     the 7x7 donor-recipient matrix, its margins, and the pooled
             transfer penalty with a stratified bootstrap CI (seed 49).

Second-order, like Entries 46 and 51: reads Entry 52's cache, exact because F3
is linear in eps.

THE THRESHOLD IS PRE-REGISTERED: a median transfer penalty under 1.0 pp
supports the transfer hypothesis; at or above it, the hypothesis is refuted and
the paper publishes eps as a default with a stated cost rather than as a
universal constant.

Output: data/results/e54_transfer.csv + console report.
Run: python3 src/harness/e54_transfer.py        (E54_SMOKE=1)
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
from e52_build import GROUPS, TAU_GRID
from perride_invert import RESULTS
from skc_compare import boot_ci_strat, med_of

SEED = 49


def _pooled_eps() -> float:
    """The pooled constant, READ from e52_summary.csv rather than hardcoded.

    It was a literal (0.2879) and went stale the moment Entry 55 changed the
    aero estimator, silently comparing every donor against a constant the paper
    no longer ships. A comparator that can drift out of date is a bug waiting
    for a re-baseline.
    """
    with open(os.path.join(RESULTS, "e52_summary.csv"), encoding="utf-8") as fh:
        for line in fh:
            k, _, v = line.partition(",")
            if k == "eps":
                return float(v)
    raise SystemExit("e52_summary.csv has no eps — run e52_split.py first")


EPS_POOLED = _pooled_eps()
MARGIN_PP = 1.0            # Entry 48's registered relevance margin
FORM = "F3"
# tau must be the FITTED one, not the published default. It was TAU_PUB_I (2 m)
# while the selected form uses 6 m, so every per-rider optimum in this entry was
# computed under a deadband the paper does not ship -- which inflated the
# per-rider optima and made the pooled constant look badly placed (Entry 59).
_TI = None


def _ti() -> int:
    global _TI
    if _TI is None:
        rows = S.load()
        train, _ = S.split(rows)
        _TI = S.fit(train, FORM)[2]
    return _TI


def fit_eps(rows) -> float:
    """The flat eps minimising Entry 52's loss on `rows`, at the fitted tau."""
    lo, hi = S.EPS_BOUNDS
    best = 0.2
    for _ in range(5):
        step = (hi - lo) / 200
        cand = [lo + i * step for i in range(201)]
        best = min(cand, key=lambda e: S.cv_loss(rows, FORM, e, S.C_PUB, _ti()))
        lo, hi = best - step, best + step
    return best


def err(rows, eps) -> list[float]:
    return [abs(v) for v in S.pct(rows, FORM, eps, S.C_PUB, _ti())]


def main() -> None:
    rows = S.load()
    train, test = S.split(rows)
    tr = {g: [r for r in train if r["group"] == g] for g in GROUPS}
    te = {g: [r for r in test if r["group"] == g] for g in GROUPS}
    riders = [g for g in GROUPS if len(tr[g]) >= 8 and len(te[g]) >= 3]
    print("Entry 54 — leave-one-rider-out transfer of the flat epsilon")
    print(f"  {len(riders)} riders · train {sum(len(tr[g]) for g in riders)}"
          f" · test {sum(len(te[g]) for g in riders)}\n")

    # --- donors
    donor_eps = {g: fit_eps(tr[g]) for g in riders}
    own_eps = {g: fit_eps(te[g]) for g in riders}
    print(f"  {'rider':<12} {'donor eps (train)':>18} {'own best (test)':>17} {'n_tr':>5} {'n_te':>5}")
    for g in riders:
        print(f"  {g:<12} {to_fixed(donor_eps[g], 4):>18} {to_fixed(own_eps[g], 4):>17}"
              f" {len(tr[g]):>5} {len(te[g]):>5}")
    span = max(donor_eps.values()) - min(donor_eps.values())
    print(f"\n  P1 — donor eps span = {to_fixed(span, 4)}"
          f"  ({'>= 0.15, CONFIRMED' if span >= 0.15 else '< 0.15, REFUTED'})")

    # --- the donor x recipient matrix, donor's own diagonal excluded
    print(f"\n  median |D%| on each RECIPIENT's held-out rides (rows = donor)")
    hdr = "  " + " " * 13 + "".join(f"{g.replace('D6-user_','u'):>8}" for g in riders)
    print(hdr + f"{'row med':>9}")
    matrix = {}
    for d in riders:
        cells = []
        for rcp in riders:
            if rcp == d:
                cells.append(None)
                continue
            m = med_of(err(te[rcp], donor_eps[d]))
            matrix[(d, rcp)] = m
            cells.append(m)
        rowmed = med_of([c for c in cells if c is not None])
        print("  " + f"{d:<13}" + "".join("       ·" if c is None else f"{c:>8.2f}"
                                          for c in cells) + f"{rowmed:>9.2f}")
    # pooled-eps reference row
    ref = {rcp: med_of(err(te[rcp], EPS_POOLED)) for rcp in riders}
    print("  " + f"{'POOLED 0.288':<13}" + "".join(f"{ref[r]:>8.2f}" for r in riders)
          + f"{med_of(list(ref.values())):>9.2f}")
    ceil = {rcp: med_of(err(te[rcp], own_eps[rcp])) for rcp in riders}
    print("  " + f"{'own best':<13}" + "".join(f"{ceil[r]:>8.2f}" for r in riders)
          + f"{med_of(list(ceil.values())):>9.2f}")

    # --- P2: the transfer penalty, per ride, donor eps vs pooled eps
    pen_all, strata = [], []
    for rcp in riders:
        s_rcp = []
        for d in riders:
            if d == rcp:
                continue
            a = err(te[rcp], donor_eps[d])
            b = err(te[rcp], EPS_POOLED)
            s_rcp += [x - y for x, y in zip(a, b)]
        pen_all += s_rcp
        strata.append(s_rcp)
    pen = med_of(pen_all)
    ci = boot_ci_strat(strata, SEED)
    ok = abs(pen) < MARGIN_PP
    print(f"\n  P2 — TRANSFER PENALTY (single donor's eps vs the pooled one, same recipients)")
    print(f"       median {to_fixed(pen, 3)} pp  [{to_fixed(ci[0], 3)}, {to_fixed(ci[1], 3)}]"
          f"   registered margin +/-{MARGIN_PP} pp")
    print(f"       {'SUPPORTED — one published number serves any rider' if ok else 'REFUTED — eps is rider-dependent at this margin'}")

    # --- P3: worst donor by row median
    rowmed = {d: med_of([matrix[(d, r)] for r in riders if r != d]) for d in riders}
    worst = max(rowmed, key=lambda d: rowmed[d])
    print(f"\n  P3 — worst donor is {worst} (row median {to_fixed(rowmed[worst], 2)});"
          f" predicted D6-user_1 — {'CONFIRMED' if worst == 'D6-user_1' else 'REFUTED'}")

    # --- P4: asymmetry, donor spread vs recipient spread of the matrix
    colmed = {r: med_of([matrix[(d, r)] for d in riders if d != r]) for r in riders}
    d_spread = max(rowmed.values()) - min(rowmed.values())
    r_spread = max(colmed.values()) - min(colmed.values())
    print(f"  P4 — spread across donors {to_fixed(d_spread, 2)} pp vs across recipients"
          f" {to_fixed(r_spread, 2)} pp — "
          f"{'CONFIRMED' if d_spread > r_spread else 'REFUTED (recipient identity dominates)'}")

    out = os.path.join(RESULTS, "e54_transfer.csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("donor,recipient,donor_eps,med_abs,pooled_med_abs,own_best_med_abs\n")
        for d in riders:
            for rcp in riders:
                if d == rcp:
                    continue
                fh.write(f"{d},{rcp},{to_fixed(donor_eps[d], 4)},"
                         f"{to_fixed(matrix[(d, rcp)], 4)},{to_fixed(ref[rcp], 4)},"
                         f"{to_fixed(ceil[rcp], 4)}\n")
        fh.write(f"ALL,ALL,,{to_fixed(pen, 4)},{to_fixed(ci[0], 4)},{to_fixed(ci[1], 4)}\n")
    print(f"\nwrote {os.path.basename(out)}")


if __name__ == "__main__":
    main()
