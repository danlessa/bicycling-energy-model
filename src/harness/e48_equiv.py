#!/usr/bin/env python3
"""Entry 48 — formal equivalence testing (TOST) for paper 1's parity claims.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 48) before any equivalence CI
was computed. Paper 1 says the closed form and the simulation are "statistically
indistinguishable", evidenced by a non-significant paired sign test. That is an
absence of evidence, not evidence of absence. This asks whether the claims can be
upgraded to formal equivalence within a registered margin.

METHOD. For each comparison, resample rides (within corpus; stratified for pools,
matching the published pooled-CI convention), compute BOTH models' median |D%| on
the SAME resample, and take

    d = med|D%|_law - med|D%|_sim

Equivalence at alpha = 0.05 is declared iff the 90% percentile CI of d lies
entirely inside [-margin, +margin]. Two one-sided tests at 0.05 each is exactly
the 90% interval being contained -- which is why it is 90% and not 95%.

MARGIN = 1.0 percentage point, registered for every comparison. The estimand is
the DIFFERENCE OF MEDIANS, not the median of per-ride differences: the paper's
sentences compare two published medians.

SEED 44. Seeds 42 and 43 carry the published |D%| and signed CIs; reusing one
would silently correlate this interval with those.

POPULATION PARITY. The published medians are computed per column, dropping
non-finite values independently. A paired test needs rides where BOTH columns are
finite, so this harness intersects them and REPORTS any ride it had to drop --
a silent mismatch would make d incomparable to the published brackets (the
Entry-31/33 lesson).

Output: data/results/e48_equiv.csv + console scoreboard.
Run: python3 src/harness/e48_equiv.py        (E48_SMOKE=1 for B = 200)
"""

from __future__ import annotations

import math
import os
import sys
from typing import Callable, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import is_finite
from bicycling_energy_model.jsfmt import to_fixed

RESULTS: str = os.path.join(REPO, "data", "results")
SMOKE: bool = bool(os.environ.get("E48_SMOKE"))
B: int = 200 if SMOKE else 10000
SEED: int = 44
MARGIN: float = 1.0


def parse_csv(name: str) -> list[dict[str, str]]:
    """Mirrors bootstrap_ci.parse_csv so populations match exactly."""
    with open(os.path.join(RESULTS, name), encoding="utf-8") as fh:
        text = fh.read().strip()
    lines = text.split("\n")

    def split(line: str) -> list[str]:
        out: list[str] = []
        cur, q = "", False
        for ch in line:
            if ch == '"':
                q = not q
            elif ch == "," and not q:
                out.append(cur)
                cur = ""
            else:
                cur += ch
        out.append(cur)
        return out

    head = split(lines[0])
    return [dict(zip(head, split(l))) for l in lines[1:]]


def rng(seed: int) -> Callable[[], float]:
    """mulberry32 with JS 32-bit semantics — the project's only RNG."""
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[(n - 1) // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def num(r: dict[str, str], c: str) -> float:
    try:
        return float(r[c])
    except (KeyError, ValueError):
        return float("nan")


def pairs_of(rows: list[dict[str, str]], law: str,
             sim: str) -> tuple[list[tuple[float, float]], int, int]:
    """(|law|, |sim|) per ride where BOTH are finite, plus each column's own count."""
    out: list[tuple[float, float]] = []
    n_law = n_sim = 0
    for r in rows:
        a, b = num(r, law), num(r, sim)
        if is_finite(a):
            n_law += 1
        if is_finite(b):
            n_sim += 1
        if is_finite(a) and is_finite(b):
            out.append((abs(a), abs(b)))
    return out, n_law, n_sim


def tost(strata: list[list[tuple[float, float]]],
         seed: int) -> tuple[float, float, float, float, float]:
    """(d, ci_lo, ci_hi, med_law, med_sim) — paired, stratified bootstrap.

    Both medians come from the SAME resample, so d's interval carries the
    correlation between the two engines' errors. Computing two independent CIs
    and differencing them would overstate the width badly: the engines share
    every input, so their errors move together.
    """
    rand = rng(seed)
    flat = [p for s in strata for p in s]
    med_law = median([p[0] for p in flat])
    med_sim = median([p[1] for p in flat])
    d = med_law - med_sim

    stats: list[float] = []
    for _ in range(B):
        la: list[float] = []
        si: list[float] = []
        for s in strata:
            n = len(s)
            for _ in range(n):
                p = s[int(rand() * n)]
                la.append(p[0])
                si.append(p[1])
        stats.append(median(la) - median(si))
    stats.sort()
    lo = stats[math.floor(0.05 * B)]
    hi = stats[math.ceil(0.95 * B) - 1]
    return d, lo, hi, med_law, med_sim


def verdict(lo: float, hi: float, margin: float) -> str:
    if lo >= -margin and hi <= margin:
        return "equivalent"
    if lo > margin:
        return "fail-high"      # the law is worse by more than the margin
    if hi < -margin:
        return "fail-low"       # the law is better by more than the margin
    return "inconclusive"


# ---- the registered comparisons -------------------------------------------
# (label, [(csv, filter, law_col, sim_col)], registered?)
Filter = Callable[[dict[str, str]], bool]


def keep_all(r: dict[str, str]) -> bool:
    return True


def data_ok(r: dict[str, str]) -> bool:
    return r.get("dataOK", "true") == "true"


SPEC: list[tuple[str, list[tuple[str, Filter, str, str]], bool]] = [
    ("D1 informed · F3", [("model_comparison.csv", keep_all,
                           "cfS_vs_emp", "canon_vs_emp")], True),
    ("D1 blind · F3", [("longoes_frozen.csv", keep_all, "f3_d", "canon_d")], True),
    ("D1 blind · F4", [("longoes_frozen.csv", keep_all, "f4_d", "canon_d")], True),
    ("D2 frozen · F3", [("censo_comparison.csv", data_ok, "sm_geom", "canon_d")], True),
    ("D2 frozen · F4", [("censo_comparison.csv", data_ok, "pm_geom", "canon_d")], True),
    ("D3 · F3", [("ppaz_comparison.csv", keep_all, "sm_geom", "canon_d")], True),
    ("D4 · F3", [("jaam_comparison.csv", keep_all, "sm_geom", "canon_d")], True),
    ("D5 · F3", [("danlessa_comparison.csv", data_ok, "sm_geom", "canon_d")], True),
    ("POOL D3+D4 · F3", [("ppaz_comparison.csv", keep_all, "sm_geom", "canon_d"),
                         ("jaam_comparison.csv", keep_all, "sm_geom", "canon_d")], True),
    ("POOL D3-D5 · F3", [("ppaz_comparison.csv", keep_all, "sm_geom", "canon_d"),
                         ("jaam_comparison.csv", keep_all, "sm_geom", "canon_d"),
                         ("danlessa_comparison.csv", data_ok, "sm_geom", "canon_d")], True),
]


def main() -> None:
    print("Entry 48 — TOST equivalence, margin "
          f"±{to_fixed(MARGIN, 1)} pp, seed {SEED}, B = {B}"
          + ("  [E48_SMOKE]" if SMOKE else ""))
    print("  Equivalence iff the 90% CI of (law − sim) median difference ⊂ "
          f"[−{to_fixed(MARGIN, 1)}, +{to_fixed(MARGIN, 1)}]\n")
    print(f"  {'comparison':<20}{'n':>6}{'med law':>9}{'med sim':>9}{'d':>8}"
          f"   {'90% CI':<20} verdict")

    rows_out: list[dict[str, object]] = []
    for label, parts, registered in SPEC:
        strata: list[list[tuple[float, float]]] = []
        dropped = 0
        for csv_name, filt, law, sim in parts:
            rows = [r for r in parse_csv(csv_name) if filt(r)]
            pr, n_law, n_sim = pairs_of(rows, law, sim)
            dropped += max(n_law, n_sim) - len(pr)
            strata.append(pr)
        n = sum(len(s) for s in strata)
        d, lo, hi, ml, ms = tost(strata, SEED)
        v = verdict(lo, hi, MARGIN)
        flag = "" if dropped == 0 else f"  [{dropped} unpaired ride(s) dropped]"
        print(f"  {label:<20}{n:>6}{to_fixed(ml, 2):>9}{to_fixed(ms, 2):>9}"
              f"{to_fixed(d, 2):>8}   "
              + f"[{to_fixed(lo, 2)}, {to_fixed(hi, 2)}]".ljust(20)
              + f" {v}{flag}")
        rows_out.append({"comparison": label, "n": n, "med_law": ml, "med_sim": ms,
                         "d": d, "ci90_lo": lo, "ci90_hi": hi, "margin": MARGIN,
                         "verdict": v, "unpaired_dropped": dropped,
                         "registered": registered})

    eq = [r for r in rows_out if r["verdict"] == "equivalent"]
    inc = [r for r in rows_out if r["verdict"] == "inconclusive"]
    bad = [r for r in rows_out if str(r["verdict"]).startswith("fail")]
    print(f"\n  {len(eq)} equivalent · {len(inc)} inconclusive · {len(bad)} outside the margin")
    if bad:
        print("  OUTSIDE THE MARGIN (the registration says weaken the paper's language, "
              "not defend it):")
        for r in bad:
            print(f"    {r['comparison']}: d = {to_fixed(float(r['d']), 2)} "
                  f"[{to_fixed(float(r['ci90_lo']), 2)}, {to_fixed(float(r['ci90_hi']), 2)}]")

    name = "e48_equiv.SMOKE.csv" if SMOKE else "e48_equiv.csv"
    cols = ["comparison", "n", "med_law", "med_sim", "d", "ci90_lo", "ci90_hi",
            "margin", "verdict", "unpaired_dropped", "registered"]
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows_out:
            cells: list[str] = []
            for c in cols:
                v2 = r[c]
                if isinstance(v2, str):
                    cells.append(f'"{v2}"')
                elif isinstance(v2, bool):
                    cells.append("true" if v2 else "false")
                elif isinstance(v2, int):
                    cells.append(str(v2))
                else:
                    cells.append(to_fixed(float(v2), 4))
            fh.write(",".join(cells) + "\n")
    print(f"\nwrote {name} ({len(rows_out)} comparisons)")


if __name__ == "__main__":
    main()
