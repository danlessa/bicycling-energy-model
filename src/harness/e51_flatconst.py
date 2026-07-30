#!/usr/bin/env python3
"""Entry 51 — the replacement flat epsilon: train/test on D3-D6 under P_f,r.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 51) before the split was drawn.
If Entry 50 sends the deficit to future research, paper 1 ships a flat epsilon —
and the incumbent value is not obviously right. eps_f = 0.20 was selected on D2
(urban stop-go, generic assumed rider, in-sample there), while Entry 49 measured
the best flat epsilon on real descents under this same parameter class at
0.344 [0.292, 0.394], an interval EXCLUDING 0.20.

    I = (D3..D6, P_a,g . P_f,r(m, Crr, CdA))    T = F3 with a flat eps

DESIGN, as registered:
  split      chronological odd/even within each of the seven riders (Entries
             44/47/49's rule) — deterministic, no RNG, riders balanced.
  fit        on TRAIN, the flat eps minimising median |D%|; the LAD (sum of
             absolute) optimum is reported beside it, because the published
             statistic is a median while the fitting convention is LAD and
             Entry 47 showed those can disagree.
  estimate   on TEST, median |D%| and signed bias with 95% bootstrap CIs
             (mulberry32, seed 47 — 42/43 published, 44 TOST, 45 E49, 46 E50),
             stratified within rider.
  report     per corpus as well as pooled, because the whole question is
             whether ONE number travels.

COMPARATORS, all scored on the same test half: the fitted constant; the
incumbent 0.20; the dynamic eps_d = eps_coast - 0.13; Entry 49's 0.344; and
eps = 0, which prices the descent term's existence.

SECOND-ORDER: reads e47_formselect.csv, whose per-ride E(eps=0) and E(eps=1)
under P_f,r pin the whole family exactly, since the closed form is linear in eps.

Output: data/results/e51_flatconst.csv + console report.
Run: python3 src/harness/e51_flatconst.py
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

from bicycling_energy_model import is_finite
from bicycling_energy_model.jsfmt import to_fixed

from skc_compare import RESULTS, boot_ci_strat, med_of, sign_p

SEED = 47
EPS_INCUMBENT = 0.20           # selected on D2, urban, in-sample there
EPS_E49 = 0.344                # Entry 49's best flat eps on real descents
EPS0 = 0.13                    # the deficit the dynamic estimator subtracts
GROUPS = ("D3", "D4", "D5", "D6-user_1", "D6-user_2", "D6-user_3", "D6-user_5")


def load() -> list[dict]:
    out: list[dict] = []
    with open(os.path.join(RESULTS, "e47_formselect.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            g = r["group"].strip('"')
            if g not in GROUPS:
                continue

            def f(k: str) -> float:
                try:
                    return float(r[k])
                except (KeyError, ValueError):
                    return float("nan")

            e0, e1, emp, ec = f("fr_E0"), f("fr_E1"), f("emp"), f("fr_eps_coast")
            if not all(is_finite(v) for v in (e0, e1, emp, ec)) or emp <= 0:
                continue
            try:
                half = int(float(r["half"]))
            except (KeyError, ValueError):
                half = 0
            out.append({"g": g, "e0": e0, "e1": e1, "emp": emp, "ec": ec, "half": half})
    return out


def err(rows, eps) -> list[float]:
    """Signed Delta% for a scalar eps, or callable eps(row) for the dynamic one."""
    out = []
    for r in rows:
        e = eps(r) if callable(eps) else eps
        kj = (r["e0"] + (r["e1"] - r["e0"]) * e) / 1000
        out.append(100.0 * (kj - r["emp"]) / r["emp"])
    return out


def fit_median(rows) -> float:
    """The flat eps minimising median |D%| — grid then refine, deterministic."""
    lo, hi = -0.2, 1.0
    best = 0.0
    for _ in range(5):
        step = (hi - lo) / 240
        cand = [lo + i * step for i in range(241)]
        best = min(cand, key=lambda e: med_of([abs(v) for v in err(rows, e)]))
        lo, hi = best - step, best + step
    return best


def fit_lad(rows) -> float:
    lo, hi = -0.2, 1.0
    best = 0.0
    for _ in range(5):
        step = (hi - lo) / 240
        cand = [lo + i * step for i in range(241)]
        best = min(cand, key=lambda e: sum(abs(v) for v in err(rows, e)))
        lo, hi = best - step, best + step
    return best


def strata(rows) -> list[list[float]]:
    return [[r for r in rows if r["g"] == g] for g in GROUPS]


def report(rows, label, eps) -> tuple[float, float]:
    e = err(rows, eps)
    a = [abs(v) for v in e]
    gs = [[abs(x) for x in err([r for r in rows if r["g"] == g], eps)] for g in GROUPS]
    gs = [x for x in gs if x]
    ci_a = boot_ci_strat(gs, SEED)
    gs2 = [[x for x in err([r for r in rows if r["g"] == g], eps)] for g in GROUPS]
    ci_s = boot_ci_strat([x for x in gs2 if x], SEED + 1)
    print(f"    {label:<28} {to_fixed(med_of(a), 2):>6} "
          f"[{to_fixed(ci_a[0], 2)}, {to_fixed(ci_a[1], 2)}]".ljust(20)
          + f"  {to_fixed(med_of(e), 2):>6} "
          f"[{to_fixed(ci_s[0], 2)}, {to_fixed(ci_s[1], 2)}]")
    return med_of(a), med_of(e)


def main() -> None:
    rows = load()
    train = [r for r in rows if r["half"] == 0]
    test = [r for r in rows if r["half"] == 1]
    print("Entry 51 — the replacement flat epsilon, train/test on D3-D6 under P_f,r")
    print(f"  {len(rows)} rides · train {len(train)} · test {len(test)}")

    e_med = fit_median(train)
    e_lad = fit_lad(train)
    e_med_test = fit_median(test)
    print(f"\n  fitted on TRAIN : median-optimal eps = {to_fixed(e_med, 4)}"
          f"   LAD-optimal = {to_fixed(e_lad, 4)}")
    print(f"  (for the registered identifiability check, the TEST half's own optimum "
          f"is {to_fixed(e_med_test, 4)})")

    print(f"\n  TEST-half performance, F3 under P_f,r"
          f"\n    {'estimator':<28} {'med|D%|':>6} {'[95% CI]':<20}  {'signed':>6} [95% CI]")
    res = {}
    res["fitted"] = report(test, f"fitted flat  {to_fixed(e_med, 3)}", e_med)
    res["incumbent"] = report(test, f"incumbent    {EPS_INCUMBENT}", EPS_INCUMBENT)
    res["e49"] = report(test, f"Entry 49     {EPS_E49}", EPS_E49)
    res["dynamic"] = report(test, "dynamic eps_d (eps_coast-0.13)",
                            lambda r: r["ec"] - EPS0)
    res["zero"] = report(test, "eps = 0 (no descent term)", 0.0)

    print("\n  per-corpus median-optimal eps on TRAIN (does one number travel?)")
    for g in GROUPS:
        sub = [r for r in train if r["g"] == g]
        if len(sub) < 8:
            continue
        e = fit_median(sub)
        te = [r for r in test if r["g"] == g]
        m = med_of([abs(v) for v in err(te, e_med)]) if te else float("nan")
        print(f"    {g:<12} n={len(sub):>4}  eps* = {to_fixed(e, 3):>7}"
              f"   test med|D%| under the POOLED fit = {to_fixed(m, 2)}")

    w = sum(1 for a, b in zip([abs(v) for v in err(test, e_med)],
                              [abs(v) for v in err(test, lambda r: r["ec"] - EPS0)]) if a < b)
    l = sum(1 for a, b in zip([abs(v) for v in err(test, e_med)],
                              [abs(v) for v in err(test, lambda r: r["ec"] - EPS0)]) if a > b)
    print(f"\n  PAIRED flat vs dynamic on test: flat closer on {w}/{w + l}, "
          f"sign test p = {to_fixed(sign_p(w, l), 4)}")
    d = res["fitted"][0] - res["dynamic"][0]
    print(f"  the fallback's price: {to_fixed(d, 2)} pp of median error "
          f"({'flat is better' if d < 0 else 'flat is worse'})")

    cols = ["estimator", "eps", "test_med_abs", "test_med_signed"]
    with open(os.path.join(RESULTS, "e51_flatconst.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for k, (a, sg) in res.items():
            ev = {"fitted": e_med, "incumbent": EPS_INCUMBENT, "e49": EPS_E49,
                  "dynamic": float("nan"), "zero": 0.0}[k]
            fh.write(f'"{k}",{to_fixed(ev, 4) if is_finite(ev) else ""},'
                     f"{to_fixed(a, 4)},{to_fixed(sg, 4)}\n")
    print("\nwrote e51_flatconst.csv")


if __name__ == "__main__":
    main()
