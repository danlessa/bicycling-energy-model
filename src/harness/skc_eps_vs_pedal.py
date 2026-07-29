#!/usr/bin/env python3
"""Entry 43, amendment arm C — does descent pedalling PREDICT the deficit eps_0?

Arms A and B established (a) that the per-rider deficit spread survives the
regime-consistent physics, so it is not a parameter artefact, and (b) that D6's
riders pedal descents about twice as much as the Brazilian ultra-distance riders.
Danilo's reading: "some people coast, others pedal a bit and others pedal a lot,
and this affects eps_0."

This arm tests that reading directly and at RIDE level rather than by eyeballing
four corpus medians. Per ride, on the same 30 m real-descent cells:

  deficit  = eps_coast - eps_bal      (the Entry-43 / ppaz_compare machinery)
  pedal    = mean descent power / mean flat power    (physics-free, Arm B)

and reports Spearman(pedal, deficit) pooled and WITHIN each rider/corpus. The
within-rider correlation is the load-bearing one: a pooled correlation could be
produced entirely by between-rider differences in terrain or physics, whereas a
within-rider one says that on the days a rider pedals his descents more, his
measured deficit is larger — which is what the mechanism claims.

Sign convention: pedalling on a descent adds E_legs, which LOWERS eps_bal and so
RAISES the deficit. The mechanism therefore predicts a POSITIVE correlation.

Output: data/results/skc_eps_vs_pedal.csv + console.
Run: python3 src/harness/skc_eps_vs_pedal.py      (SKC_SMOKE=1 for a subset)
"""

from __future__ import annotations

import json
import math
import os
import sys
from typing import Iterator, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import (climb_balance, is_finite, load_pts)
from bicycling_energy_model.jsfmt import to_fixed

from skc_compare import (FROZEN, M0, MIN_SUSTAINED_DH, RESULTS, boot_ci,
                         eps_cells, med_of, ride_files)
from skc_invert import descent_behaviour, iter_brazil

DATA = os.path.join(REPO, "data", "inputs", "activities")
SMOKE = bool(os.environ.get("SKC_SMOKE"))
ZWIFT = 260

# Anchor masses for the paper-1 corpora, as perride_invert carries them. D1 uses
# its own logged per-ride mass. These are inputs to eps_bal via alpha and beta;
# the deficit is not hugely sensitive to them, but they must be the SAME values
# the published corpus numbers were produced under.
ANCHOR = {"D3": 74.5, "D4": 101.9, "D5": 74.7, "D2": 78.0}


def spearman(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, int]:
    """Rank correlation with average ranks for ties."""
    n = len(xs)
    if n < 5:
        return float("nan"), n

    def ranks(v: Sequence[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: v[i])
        out = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    a, b = ranks(xs), ranks(ys)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    den = math.sqrt(sum((a[i] - ma) ** 2 for i in range(n))
                    * sum((b[i] - mb) ** 2 for i in range(n)))
    return (num / den if den else float("nan")), n


def boot_rho(xs: Sequence[float], ys: Sequence[float], seed: int = 44,
             B: int = 2000) -> tuple[float, float]:
    """Percentile CI on Spearman by resampling ride pairs (mulberry32)."""
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    n = len(xs)
    if n < 10:
        return float("nan"), float("nan")
    stats = []
    for _ in range(B):
        idx = [int(rand() * n) for _ in range(n)]
        r, _ = spearman([xs[i] for i in idx], [ys[i] for i in idx])
        if is_finite(r):
            stats.append(r)
    if not stats:
        return float("nan"), float("nan")
    stats.sort()
    return stats[int(0.025 * len(stats))], stats[min(len(stats) - 1,
                                                     int(0.975 * len(stats)))]


def rows_for(pts: Sequence[dict], group: str, label: str, m: float) -> dict | None:
    p = {**FROZEN, "m": m}
    eb = eps_cells(pts, p)
    if not eb or eb.get("Hd", 0) < 1 or eb.get("sbar", 0) < 0.03:
        return None
    db = descent_behaviour(pts)
    if not db or not is_finite(db.get("intensity", float("nan"))):
        return None
    return {"group": group, "ride": label, "m": m,
            "deficit": eb["epsCoast"] - eb["epsBal"],
            "eps_bal": eb["epsBal"], "eps_coast": eb["epsCoast"],
            "sbar": eb["sbar"], "intensity": db["intensity"],
            "occ_all": db["occ_all"], "p_desc": db["p_desc"],
            "p_flat": db["p_flat"]}


def main() -> None:
    rows: list[dict] = []

    # ---- D6: anchor mass per rider, recomputed (never a frozen literal) ----
    p0 = {**FROZEN, "m": M0}
    mh: dict[str, list[float]] = {}
    d6: list[tuple[str, str]] = []
    for rider, path in ride_files():
        try:
            pts = load_pts(path)
        except Exception:
            continue
        if len(pts) < 10:
            continue
        npow = sum(1 for q in pts if q.get("power") is not None)
        nalt = sum(1 for q in pts if q.get("alt") is not None)
        if npow / len(pts) <= 0.5 or nalt / len(pts) < 0.99 or pts[-1]["x"] / 1000 < 20:
            continue
        d6.append((rider, path))
        cb = climb_balance(pts, p0)
        if cb["n"] > 0 and cb["dh"] >= MIN_SUSTAINED_DH and (cb["egrav"] + cb["eroll"]) > 0:
            mm = M0 * (cb["emeas"] - cb["eaero"]) / (cb["egrav"] + cb["eroll"])
            if is_finite(mm) and 40.0 <= mm <= 200.0:
                mh.setdefault(rider, []).append(mm)
    anchor6 = {r: med_of(v) for r, v in mh.items() if v}
    for rider, path in d6:
        try:
            pts = load_pts(path)
        except Exception:
            continue
        r = rows_for(pts, "D6-" + rider, os.path.basename(path)[:-4],
                     anchor6.get(rider, M0))
        if r:
            rows.append(r)

    # ---- the paper-1 corpora ----
    inputs = {e["label"]: e for e in json.load(open(os.path.join(DATA, "model_inputs.json")))}
    for corpus, lab in (("longoes", "D1"), ("ppaz", "D3"), ("jaam", "D4"),
                        ("danlessa", "D5"), ("censo", "D2")):
        try:
            for pts, name in iter_brazil(corpus):
                m = (inputs[name]["m"] if lab == "D1" and name in inputs
                     else ANCHOR.get(lab, M0))
                r = rows_for(pts, lab, name, m)
                if r:
                    rows.append(r)
        except Exception as exc:
            print(f"  ({corpus}: {type(exc).__name__} — skipped)")

    groups = sorted({r["group"] for r in rows},
                    key=lambda g: (not g.startswith("D6"), g))
    print(f"\nARM C — does descent pedalling predict the deficit?   n = {len(rows)} rides "
          "with a real descent (mean descent grade >= 3%)\n")
    print("group".ljust(12) + "n".rjust(5) + "pedal ratio".rjust(13)
          + "deficit".rjust(10) + "rho(pedal, deficit) [95% CI]".rjust(32))
    for g in groups:
        s = [r for r in rows if r["group"] == g]
        rho, n = spearman([r["intensity"] for r in s], [r["deficit"] for r in s])
        lo, hi = boot_rho([r["intensity"] for r in s], [r["deficit"] for r in s])
        ci = (f"[{to_fixed(lo, 2)}, {to_fixed(hi, 2)}]" if is_finite(lo) else "—")
        print(g.ljust(12) + str(len(s)).rjust(5)
              + to_fixed(med_of([r["intensity"] for r in s]), 3).rjust(13)
              + to_fixed(med_of([r["deficit"] for r in s]), 3).rjust(10)
              + f"{to_fixed(rho, 3)} {ci}".rjust(32))

    xs = [r["intensity"] for r in rows]
    ys = [r["deficit"] for r in rows]
    rho, _ = spearman(xs, ys)
    lo, hi = boot_rho(xs, ys)
    print("\nPOOLED across every corpus: rho = "
          f"{to_fixed(rho, 3)} [{to_fixed(lo, 2)}, {to_fixed(hi, 2)}]  (n = {len(rows)})")
    within = [spearman([r["intensity"] for r in rows if r["group"] == g],
                       [r["deficit"] for r in rows if r["group"] == g])[0]
              for g in groups]
    within = [w for w in within if is_finite(w)]
    print(f"WITHIN-group rho: median {to_fixed(med_of(within), 3)}, "
          f"range {to_fixed(min(within), 2)} to {to_fixed(max(within), 2)}, "
          f"positive on {sum(1 for w in within if w > 0)}/{len(within)} groups")
    print("\n(positive rho = more descent pedalling goes with a LARGER deficit,\n"
          " which is the direction the behavioural reading predicts)")

    if rows:
        cols = list(dict.fromkeys(k for r in rows for k in r))
        dest = os.path.join(RESULTS,
                            f"skc_eps_vs_pedal{'.SMOKE' if SMOKE else ''}.csv")
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for r in rows:
                fh.write(",".join(
                    (f'"{v}"' if isinstance(v, str)
                     else to_fixed(v, 4) if is_finite(v) else "")
                    for v in (r.get(k, float("nan")) for k in cols)) + "\n")
        print(f"\nwrote {os.path.basename(dest)} ({len(rows)} rides)")


if __name__ == "__main__":
    main()
