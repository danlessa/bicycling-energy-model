#!/usr/bin/env python3
"""Entry 57, stage 1 — per-rider fallback constants from the TRAINING half.

Reads the existing e52 cache, reproduces Entry 52's split exactly, and writes
each rider's median of the constants that were GENUINELY inverted on their
training rides. e52_build.py then uses those instead of the global priors
(CRR0 = 0.008, CDA0 = 0.40, the per-corpus anchor mass).

WHY TRAIN ONLY. The medians are applied to both halves, so computing them over
all rides would let a held-out ride help set the constant used to predict it.
The split is deterministic given the seed, so reproducing it here costs
nothing and keeps the two stages consistent by construction.

WHY MEDIAN, not mean: the per-ride inversions are heavy-tailed and several sit
at their range bounds, so a mean would be dragged by the rides that failed
least gracefully.

Output: data/results/e52_rider_fallback.csv
Run:    python3 src/harness/e57_rider_fallback.py
Then:   E52_FALLBACK=rider python3 src/harness/e52_build.py
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
from e52_build import GROUPS
from perride_invert import RESULTS
from skc_compare import med_of

FIELDS = (("m_hat", "m_src"), ("crr_hat", "crr_src"), ("cda_hat", "cda_src"))
MIN_N = 3          # below this the rider median is not trustworthy; keep the prior


def main() -> None:
    rows = S.load()
    train, _ = S.split(rows)
    print(f"Entry 57 — rider-median fallbacks from {len(train)} training rides\n")
    print(f"  {'rider':<12} " + "".join(f"{k:>22}" for k, _ in FIELDS))

    out = {}
    for g in GROUPS:
        sub = [r for r in train if r["group"] == g]
        if not sub:
            continue
        cells, rec = [], {}
        for val, src in FIELDS:
            good = [r[val] for r in sub if r.get(src) not in ("fallback", "", None)]
            if len(good) >= MIN_N:
                rec[val] = med_of(good)
                cells.append(f"{rec[val]:>14.5g} (n={len(good)})")
            else:
                cells.append(f"{'— too few —':>22}")
        out[g] = rec
        print(f"  {g:<12} " + "".join(f"{c:>22}" for c in cells))

    path = os.path.join(RESULTS, "e52_rider_fallback.csv")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("group,m_hat,crr_hat,cda_hat\n")
        for g, rec in out.items():
            fh.write(f"{g},"
                     + ",".join(to_fixed(rec[k], 6) if k in rec else ""
                                for k, _ in FIELDS) + "\n")
    print(f"\nwrote {os.path.basename(path)}")
    print("  these REPLACE the global priors; every constant now originates in")
    print("  the rider's own telemetry, and no ride is dropped.")


if __name__ == "__main__":
    main()
