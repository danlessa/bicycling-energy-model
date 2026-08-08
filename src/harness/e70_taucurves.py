#!/usr/bin/env python3
"""Entry 70 — the pinned-τ loss curves, per rider.

Entry 68 drew the pooled CV(τ_n) curve and found no data-internal floor;
Entry 69 showed the measured pin transfers best. The question this entry
answers (Danilo: "How that would look for each individual rider? I wonder if
there are regional differences on that curve"): per rider, bare F3 with τ
PINNED at each grid point and ε refit at that point — the basin's SHAPE,
normalised to each row's own minimum. Plus pooled SP (D3–D5) and pooled EU
(D6-*) rows for the regional read, kept with the warning they earn: a pooled
curve inherits its steepest member (E59's pooling lesson).

Deliberately IN-SAMPLE per group (train half only, ε refit per point): the
object is where each rider's basin sits and how steep it is, not a
generalisation estimate — Entries 66/67/69 already established that these
in-pool optima are bias-shaped rather than noise-shaped, and this entry's
table is that finding made visible (the fitted optima ANTI-track the
measured drift; the steepest curve runs monotonically to the grid rail).

Pure e52-cache arithmetic — no walks, no tolls, no test rides.

Output: data/results/e70_taucurves.csv (long format: pool × τ × loss/eps,
plus per-pool τ*, rail flag, measured drift). Run:
python3 src/harness/e70_taucurves.py            (E70_SMOKE=1)
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

SMOKE = bool(os.environ.get("E70_SMOKE"))
if SMOKE:
    os.environ["E52_SMOKE"] = "1"

from e52_build import TAU_GRID  # noqa: E402
from e52_split import EPS_BOUNDS, GROUPS, load, split  # noqa: E402
from perride_invert import RESULTS  # noqa: E402
from skc_compare import med_of  # noqa: E402

SHOW = (0.5, 1.0, 2.0, 3.0, 4.5, 6.0, 8.0, 12.0)   # printed subset
SUFF = ".SMOKE" if SMOKE else ""
MIN_N = 10


def drift_medians() -> dict[str, float]:
    path = os.path.join(RESULTS, "e66_drift" + SUFF + ".csv")
    by_g: dict[str, list[float]] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["drift_med_m"] != "":
                    by_g.setdefault(r["group"], []).append(float(r["drift_med_m"]))
    return {g: med_of(v) for g, v in by_g.items() if v}


def curve(sub) -> dict[float, tuple[float, float]]:
    """{tau: (loss, eps)} — eps refit per pinned tau, loss = mean |log|."""
    out = {}
    for ti, tau in enumerate(TAU_GRID):
        k = f"f3t{ti}"
        pre = [(r[k + "_roll"] + r[k + "_aero"] + r[k + "_climb"],
                r[k + "_recov1"], r["emp"] * 1000) for r in sub]

        def loss(e: float) -> float:
            t = 0.0
            for f, rec, emp in pre:
                v = f + e * rec
                t += abs(math.log(v / emp)) if v > 0 else 1e9
            return t / len(pre)

        lo, hi = EPS_BOUNDS
        best = 0.2
        for _ in range(5):
            step = (hi - lo) / 200
            best = min([lo + i * step for i in range(201)], key=loss)
            lo, hi = best - step, best + step
        out[tau] = (loss(best), best)
    return out


def main() -> None:
    rows = load()
    train, _test = split(rows)
    drift = drift_medians()
    pools = [(g, [r for r in train if r["group"] == g]) for g in GROUPS]
    pools += [("SP (D3-D5)", [r for r in train
                              if r["group"] in ("D3", "D4", "D5")]),
              ("EU (D6-*)", [r for r in train if r["group"].startswith("D6")])]
    print(f"Entry 70 — pinned-τ loss curves per rider (train, n = {len(train)})"
          + ("   [SMOKE]" if SMOKE else ""))
    hdr = "".join(f"{t:>7g}" for t in SHOW)
    print(f"\n  {'pool':<12}{'n':>5}{hdr}{'drift':>7}{'tau*':>6}")
    out_rows = []
    for g, sub in pools:
        if len(sub) < MIN_N:
            continue
        c = curve(sub)
        m = min(v for v, _e in c.values())
        tstar = min(c, key=lambda t: c[t][0])
        rail = tstar in (TAU_GRID[0], TAU_GRID[-1])
        cells = "".join(f"{100 * (c[t][0] / m - 1):>+7.1f}" for t in SHOW)
        d = drift.get(g)
        print(f"  {g:<12}{len(sub):>5}{cells}"
              f"{(f'{d:>7.1f}' if d is not None else '      -')}"
              f"{tstar:>6g}{' RAIL' if rail else ''}")
        for tau in TAU_GRID:
            out_rows.append({"pool": g, "n": len(sub), "tau": tau,
                             "loss": c[tau][0], "eps": c[tau][1],
                             "infl_pct": 100 * (c[tau][0] / m - 1),
                             "tau_star": tstar, "at_rail": int(rail),
                             "drift_med_m": d if d is not None else ""})
    print("\n  cells: % loss inflation vs the row's own best τ; RAIL marks an"
          "\n  optimum at the grid edge — an absorber signature, not a scale")
    out = os.path.join(RESULTS, "e70_taucurves" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"\nwrote {os.path.basename(out)}")


if __name__ == "__main__":
    main()
