#!/usr/bin/env python3
"""Entry 59 — three ways to pool eps across riders, scored on held-out rides.

Entry 54 found a single donor's eps beating the pooled constant on riders it
had never seen. The per-rider optima explain it: ALL of them sit above the
ride-weighted fit, which a convex compromise could never do. The per-ride
log-ratio losses are asymmetric, so minimising the mean over rides is not
minimising the typical rider's error -- and eps is published to serve a rider.

Three objectives, fitted on TRAIN, scored ONCE on TEST:
  A  ride-weighted   mean of |log(Ehat/E)| over rides           (the incumbent)
  B  rider-weighted  mean OVER RIDERS of each rider's mean loss
  C  rider-median    median of the per-rider optima

Run for all four forms: if the effect is real it should not be peculiar to F3.

Output: data/results/e59_pooling.csv + console report.
Run: python3 src/harness/e59_pooling.py
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
from e52_build import FORMS, GROUPS
from perride_invert import RESULTS
from skc_compare import boot_ci_strat, med_of, sign_p

SEED = 51
MIN_RIDES = 8


def _grid_min(score) -> float:
    """Deterministic grid-then-refine minimiser over eps, shared by all arms."""
    lo, hi = S.EPS_BOUNDS
    best = 0.2
    for _ in range(5):
        step = (hi - lo) / 200
        cand = [lo + i * step for i in range(201)]
        best = min(cand, key=score)
        lo, hi = best - step, best + step
    return best


def fit_ride(rows, form, c, ti) -> float:
    """A — the incumbent: every ride counts once."""
    return _grid_min(lambda e: S.cv_loss(rows, form, e, c, ti))


def fit_rider(by_rider, form, c, ti) -> float:
    """B — every RIDER counts once, regardless of ride count."""
    def score(e):
        ls = [S.cv_loss(v, form, e, c, ti) for v in by_rider if v]
        return sum(ls) / len(ls)
    return _grid_min(score)


def fit_rider_median(by_rider, form, c, ti) -> float:
    """C — the median of the per-rider optima."""
    return med_of([fit_ride(v, form, c, ti) for v in by_rider if len(v) >= MIN_RIDES])


def main() -> None:
    rows = S.load()
    train, test = S.split(rows)
    tr = [[r for r in train if r["group"] == g] for g in GROUPS]
    tr = [v for v in tr if len(v) >= MIN_RIDES]
    print(f"Entry 59 — pooling objectives, {len(tr)} riders, "
          f"train {len(train)} / test {len(test)}\n")

    out = []
    for form in FORMS:
        _, c, ti = S.fit(train, form)
        eps = {"A ride-weighted": fit_ride(train, form, c, ti),
               "B rider-weighted": fit_rider(tr, form, c, ti),
               "C rider-median": fit_rider_median(tr, form, c, ti)}
        print(f"  {form}")
        print(f"    {'objective':<18} {'eps':>7} {'test med|D%|':>14} {'[95% CI]':<16} {'signed':>8}")
        base = None
        for k, e in eps.items():
            a = [abs(v) for v in S.pct(test, form, e, c, ti)]
            sg = S.pct(test, form, e, c, ti)
            gs = [[abs(x) for x in S.pct([r for r in test if r["group"] == g], form, e, c, ti)]
                  for g in GROUPS]
            ci = boot_ci_strat([x for x in gs if x], SEED)
            m = med_of(a)
            if base is None:
                base = m
            print(f"    {k:<18} {to_fixed(e, 4):>7} {to_fixed(m, 2):>14} "
                  f"[{to_fixed(ci[0], 2)}, {to_fixed(ci[1], 2)}]".ljust(17)
                  + f"{to_fixed(med_of(sg), 2):>8}"
                  + ("" if k.startswith("A") else f"   {to_fixed(m - base, 2):>6} pp vs A"))
            out.append((form, k, e, m, med_of(sg)))
        # paired test, best rider-pooled arm against the incumbent
        best_k = min(("B rider-weighted", "C rider-median"),
                     key=lambda k: med_of([abs(v) for v in S.pct(test, form, eps[k], c, ti)]))
        aa = [abs(v) for v in S.pct(test, form, eps["A ride-weighted"], c, ti)]
        bb = [abs(v) for v in S.pct(test, form, eps[best_k], c, ti)]
        w = sum(1 for x, y in zip(bb, aa) if x < y)
        l = sum(1 for x, y in zip(bb, aa) if x > y)
        print(f"    paired: {best_k} closer on {w}/{w + l}, p = {to_fixed(sign_p(w, l), 4)}\n")

    path = os.path.join(RESULTS, "e59_pooling.csv")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("form,objective,eps,test_med_abs,test_med_signed\n")
        for form, k, e, m, sg in out:
            fh.write(f"{form},{k},{to_fixed(e, 4)},{to_fixed(m, 4)},{to_fixed(sg, 4)}\n")
    print(f"wrote {os.path.basename(path)}")


if __name__ == "__main__":
    main()
