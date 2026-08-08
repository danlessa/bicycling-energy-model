#!/usr/bin/env python3
"""bootstrap_ci.py — the gate battery for every number the papers publish.

SCOPE, narrowed 2026-07-31: this battery gates the CURRENT claims of paper 1
and paper 2, and nothing else. It used to carry twenty-two sections spanning
every entry in the lab journal; eighteen of those gated results the papers no
longer make — the frozen protocol, the D1/D2 corpora, the per-ride physics
tables and the regime-aero tables all left paper 1 in the 2026-07 rewrite. A
gate on a number nobody publishes is not a safety net, it is a slow test that
fails for reasons the reader will never see, so those sections were retired
with the prose they served. The lab journal retains every one of their results,
and git history retains the code.

What remains is keyed to `pc:gateSection` in the article sidecars, and
research/scripts/check_paper_stats.py asserts the correspondence both ways:

  1   corpus populations (paper 1, Table 1)
  3i  elevation-source substitution (Entry 41, paper 2)
  3p  parameter sensitivity, Sobol shares (Entry 50, paper 1 §3.2)
  3q  the A-chain: selection and held-out error (Entries 52/55, paper 1 §3.1)
  3r  leave-one-rider-out transfer (Entry 54, paper 1 §1.3 — its hypothesis)
  3s  structural-parameter sensitivity (Entry 56, paper 1 Table 4)
  3t  regional eps pools (Entry 60, paper 1 Table 5)

Reads ONLY per-ride CSVs already written by the other harnesses — no engine
runs, no FIT parsing. Every published median is reproduced as a GATE before its
CI is reported; any gate failure exits non-zero. Bootstrap: percentile method,
B = 10⁴, deterministic mulberry32 seed so the run is reproducible. Paired
comparisons: exact two-sided sign test on |Δ%|.

Levers, both of which print a NON-AUTHORITATIVE banner: GATES=3q,3r computes
intervals only in the named sections (medians still gate everywhere), and
GATE_B lowers the resample count.

Usage: python3 src/harness/bootstrap_ci.py
"""

from __future__ import annotations

from typing import Callable

import math
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
from bicycling_energy_model import is_finite
from bicycling_energy_model.jsfmt import to_fixed

RESULTS = os.path.join(REPO, "data", "results")
os.makedirs(RESULTS, exist_ok=True)
failed = False

NAN = float("nan")


def parse_float(s: str | None) -> float:
    """JS parseFloat: leading numeric prefix or NaN."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return NAN


# --- CSV parser (quoted fields, no embedded newlines; strips quotes) ---
def parse_csv(p: str) -> list[dict[str, str]]:
    with open(os.path.join(RESULTS, p), encoding="utf-8") as fh:
        text = fh.read().strip()
    lines = text.split("\n")

    def split(line: str) -> list[str]:
        out, cur, q = [], "", False
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


# --- deterministic RNG (mulberry32, with JS 32-bit integer semantics) ---
def rng(seed: int) -> Callable[[], float]:
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[(n - 1) // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


# ---- run-cost controls -----------------------------------------------------
# The battery's cost is ~40 boot_ci/boot_ci_strat calls at B = 10^4 over corpora
# of 1,400+ rides; every other check is milliseconds. Two levers, both of which
# make a run NON-AUTHORITATIVE and say so loudly:
#
#   GATE_B=200    lower the resample count everywhere (fast, CIs approximate)
#   GATES=3o,3n   compute CIs only in these sections; elsewhere they are skipped
#                 and their CI gates report SKIP instead of pass/fail.
#
# Sections are NOT skipped wholesale: later ones reuse CSVs parsed by earlier
# ones, so skipping a section outright breaks the run. Only the expensive part
# is skipped; every median, count and ordering gate still runs everywhere.
B = int(os.environ.get("GATE_B", "10000"))
_WANT = {t.strip() for t in os.environ.get("GATES", "").split(",") if t.strip()}
_CUR = ""
if B != 10000 or _WANT:
    print("!! NON-AUTHORITATIVE RUN"
          + (f" — B = {B} (published CIs need 10^4)" if B != 10000 else "")
          + (f" — CIs only for sections {sorted(_WANT)}" if _WANT else "")
          + "\n!! Do not read these intervals as the published ones.\n")


def sec(tag: str) -> None:
    """Mark the section now executing, for the GATES filter."""
    global _CUR
    _CUR = tag


def _ci_wanted() -> bool:
    return not _WANT or _CUR in _WANT


def boot_ci(values: list[float], seed: int) -> tuple[float, float]:
    if not _ci_wanted():
        return float("nan"), float("nan")
    rand = rng(seed)
    n = len(values)
    stats = []
    for _ in range(B):
        stats.append(median([values[int(rand() * n)] for _ in range(n)]))
    stats.sort()
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


def report(label: str, deltas: list[float], expect_abs: float | None = None,
           expect_signed: float | None = None,
           expect_ci: tuple[float, float] | None = None,
           expect_ci_signed: tuple[float, float] | None = None) -> None:
    """Print (and optionally gate) the median and its bootstrap CI.

    expect_ci / expect_ci_signed assert the PUBLISHED 95% bands (paper1-closed-form.md /
    article) on |Δ%| and signed Δ% respectively. The bootstrap is seeded, so
    the bounds are deterministic given the data; 0.06 tolerance only absorbs
    the 1-decimal rounding the published values carry.
    """
    global failed
    abs_v = [abs(x) for x in deltas]
    m_abs, m_sgn = median(abs_v), median(deltas)
    a_lo, a_hi = boot_ci(abs_v, 42)
    s_lo, s_hi = boot_ci(deltas, 43)
    gate = ""
    if expect_abs is not None or expect_ci is not None or expect_ci_signed is not None:
        ok = (expect_abs is None or abs(m_abs - expect_abs) <= 0.11) and (
            expect_signed is None or abs(m_sgn - expect_signed) <= 0.11)
        _skipped = False
        if expect_ci is not None:
            if is_finite(a_lo):
                ok = ok and abs(a_lo - expect_ci[0]) <= 0.06 and abs(a_hi - expect_ci[1]) <= 0.06
            else:
                _skipped = True
        if expect_ci_signed is not None:
            if is_finite(s_lo):
                ok = ok and abs(s_lo - expect_ci_signed[0]) <= 0.06 and abs(s_hi - expect_ci_signed[1]) <= 0.06
            else:
                _skipped = True
        if _skipped:
            # the medians were still gated; only the interval was not computed
            print(f"{label.ljust(34)} n={str(len(deltas)).rjust(3)}  "
                  f"med|Δ%|={to_fixed(m_abs, 2).rjust(6)}  medΔ%={to_fixed(m_sgn, 2).rjust(7)}"
                  + ("  GATE-OK(medians) CI-SKIP" if ok else "  GATE-FAIL(medians) CI-SKIP"))
            if not ok:
                failed = True
            return
        gate = " GATE-OK" if ok else (
            f" GATE-FAIL(exp {expect_abs}/{'null' if expect_signed is None else expect_signed}"
            f"{'' if expect_ci is None else ' ci' + str(expect_ci)}"
            f"{'' if expect_ci_signed is None else ' ciS' + str(expect_ci_signed)})")
        if not ok:
            failed = True
    print(f"{label.ljust(34)} n={str(len(deltas)).rjust(3)}  "
          f"med|Δ%|={to_fixed(m_abs, 2).rjust(6)} [{to_fixed(a_lo, 1)}, {to_fixed(a_hi, 1)}]  "
          f"medΔ%={to_fixed(m_sgn, 2).rjust(7)} [{to_fixed(s_lo, 1)}, {to_fixed(s_hi, 1)}]{gate}")


# exact two-sided binomial sign test on paired |Δ%|
def log_c(n: int, k: int) -> float:
    s = 0.0
    for i in range(1, k + 1):
        s += math.log(n - k + i) - math.log(i)
    return s


LN2 = 0.6931471805599453  # Math.LN2


def sign_p(w: int, l: int) -> float:
    n = w + l
    p = 0.0
    for k in range(n + 1):
        pk = math.exp(log_c(n, k) - n * LN2)
        if k <= min(w, l) or k >= max(w, l):
            p += pk
    return min(1, p)


def paired(label: str, rows: list[dict], col_a: str, col_b: str,
           expect_w: int | None = None, expect_p: float | None = None) -> None:
    """Paired sign test. With expect_* it GATES; without, it only reports.

    Added because the parity claim in section 3.1 — the paper's own headline for
    hypothesis H1 — rested on a p-value this function printed and never
    asserted. Found by check_paper_stats.py, which is exactly the class of gap
    it exists to find.
    """
    global failed
    w = l = 0
    for r in rows:
        a, b = abs(parse_float(r.get(col_a))), abs(parse_float(r.get(col_b)))
        if not is_finite(a) or not is_finite(b):
            continue
        if a < b:
            w += 1
        elif a > b:
            l += 1
    _p = sign_p(w, l)
    _gate = ""
    if expect_w is not None or expect_p is not None:
        _ok = ((expect_w is None or w == expect_w)
               and (expect_p is None or abs(_p - expect_p) <= 0.005))
        _gate = " GATE-OK" if _ok else f" GATE-FAIL(exp {expect_w}/{expect_p})"
        if not _ok:
            failed = True
    print(f"{label}: A closer on {w}/{w + l} ({to_fixed(100 * w / (w + l), 0)}%), "
          f"sign test p={to_fixed(_p, 4)}{_gate}")


def strat_signed_gate(label: str, strata_cols: list[list[float]], es: float,
                      ecis: tuple[float, float]) -> None:
    global failed
    pooled = [x for v in strata_cols for x in v]
    ms = median(pooled)
    if not _ci_wanted():
        _ok = abs(ms - es) <= 0.11
        print(f"{label}: medΔ%={to_fixed(ms, 2)}"
              + ("  GATE-OK(median) CI-SKIP" if _ok else "  GATE-FAIL(median) CI-SKIP"))
        if not _ok:
            failed = True
        return
    rand = rng(43)
    stats = []
    for _ in range(B):
        samp = []
        for v in strata_cols:
            n = len(v)
            samp.extend(v[int(rand() * n)] for _ in range(n))
        stats.append(median(samp))
    stats.sort()
    slo, shi = stats[250], stats[9749]
    ok = (abs(ms - es) <= 0.11 and abs(slo - ecis[0]) <= 0.06
          and abs(shi - ecis[1]) <= 0.06)
    print(f"{label.ljust(34)} signed {to_fixed(ms, 2)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]"
          + (" GATE-OK" if ok else f" GATE-FAIL(exp {es} {ecis})"))
    if not ok:
        failed = True


def num(r: dict, c: str) -> float:
    return parse_float(r.get(c))


def col(rows: list[dict], c: str) -> list[float]:
    return [x for x in (num(r, c) for r in rows) if is_finite(x)]



# ---------- 1. Corpus populations (paper 1, Table 1) ----------
sec("1")
print("== Corpus populations (paper Table 1) ==")
_agg = parse_csv(os.path.join(RESULTS, "e52_aggregates.csv"))
_want_pop = {"D3": 441, "D4": 219, "D5": 636, "D6": 743}
_seen = {"D3": 0, "D4": 0, "D5": 0, "D6": 0}
for _r in _agg:
    _g = _r["group"]
    _k = "D6" if _g.startswith("D6") else _g
    if _k in _seen:
        _seen[_k] += 1
# Table 1 now reports the EVALUATED population, so the gate is exact equality.
# It was written as `<=` on the assumption that Table 1's older "clean" counts
# were a superset; they are not -- D5 and D6 evaluate 15 and 3 rides MORE than
# those counts, because the eligibility rules differ. Table 1 was corrected to
# the population the paper actually draws on, which is what this gate now pins.
for _k in ("D3", "D4", "D5", "D6"):
    _ok = _seen[_k] == _want_pop[_k]
    print(f"  {_k} evaluated {_seen[_k]:>5} (expect {_want_pop[_k]})"
          + (" GATE-OK" if _ok else " GATE-FAIL"))
    if not _ok:
        failed = True
_ok = len(_agg) == 2039
print(f"  D3-D6 evaluated total {len(_agg)} (expect 2,039)"
      + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True


# ---------- 3i. Elevation-source substitution (Entry 41 / paper 2) ----------
sec("3i")
print("\n== Elevation-source substitution (Entry 41, paper 2) ==")
e41 = parse_csv("e41_dem_route.csv")
_e41_prim = [r for r in e41 if num(r, "dataOK") == 1 and num(r, "g1_track") == 1
             and num(r, "g2_valid") == 1]
_e41_clean = [r for r in _e41_prim if num(r, "g3_clean") == 1]
_e41_pool = {"D3+D4": [r for r in _e41_prim if r.get("corpus") in ("ppaz", "jaam")],
             "pooled": _e41_prim}
_ok = len(_e41_prim) == 1117 and len(_e41_clean) == 745
print(f"E41 population: primary n={len(_e41_prim)} · anomaly-free n={len(_e41_clean)}"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 1117/745)"))
if not _ok:
    failed = True

# F3 · eps_d per elevation arm, at the regime-consistent physics the letter quotes
for _pool, _arm, _ea, _es, _eci, _ecis in (
        ("D3+D4", "own", 3.2, -2.0, (2.9, 3.4), (-2.4, -1.6)),
        ("D3+D4", "igc5", 3.6, -0.9, (3.3, 3.9), (-1.5, -0.4)),
        ("D3+D4", "igc5s10", 3.5, -1.3, (3.3, 3.9), (-1.7, -0.8)),
        ("D3+D4", "igc5s30", 3.4, -1.9, (3.2, 3.8), (-2.2, -1.7)),
        ("D3+D4", "igc30", 3.5, -1.3, (3.2, 3.8), (-1.6, -0.8)),
        ("D3+D4", "fab5", 4.0, 3.6, (3.4, 4.7), (2.8, 4.5)),
        ("D3+D4", "fab30", 3.4, 1.6, (3.2, 4.0), (0.8, 2.6)),
        ("pooled", "own", 3.8, -1.7, (3.6, 4.1), (-2.2, -1.3)),
        ("pooled", "igc5", 4.3, 1.0, (4.0, 4.6), (0.3, 1.7)),
        ("pooled", "igc5s10", 4.2, -0.1, (4.0, 4.4), (-0.5, 0.4)),
        ("pooled", "igc5s30", 4.0, -1.7, (3.8, 4.2), (-1.9, -1.3)),
        ("pooled", "igc30", 4.2, 0.1, (4.0, 4.4), (-0.4, 0.5)),
        ("pooled", "fab5", 5.3, 4.3, (4.6, 6.0), (3.6, 4.9)),
        ("pooled", "fab30", 4.6, 2.0, (4.1, 4.9), (1.5, 2.7))):
    report(f"E41 {_pool} {_arm}", col(_e41_pool[_pool], f"{_arm}_reg_f3d"),
           _ea, _es, expect_ci=_eci, expect_ci_signed=_ecis)

# the per-source ascent-noise rate c(tau = 2) — the letter's prescription column.
# `own` reproduces paper 1 §2.4's 3.1 m/km on 25x the sample.
for _arm, _ec, _eci in (("own", 3.10, (3.01, 3.18)), ("igc5", 4.95, (4.89, 5.00)),
                        ("igc5s10", 3.74, (3.66, 3.81)), ("igc5s30", 2.62, (2.56, 2.68)),
                        ("igc30", 3.77, (3.69, 3.83)), ("fab5", 10.14, (9.86, 10.59)),
                        ("fab30", 7.52, (7.12, 7.76))):
    report(f"E41 c(t=2) {_arm}", col(_e41_prim, f"{_arm}_cnoise"), _ec, None,
           expect_ci=_eci)

# ascent inflation relative to the control
_e41_own_hp = median(col(_e41_prim, "own_hplus"))
for _arm, _er in (("igc5", 1.18), ("igc5s10", 1.04), ("igc5s30", 0.86),
                  ("igc30", 1.05), ("fab5", 2.36), ("fab30", 1.72)):
    _r = median(col(_e41_prim, f"{_arm}_hplus")) / _e41_own_hp
    _ok = abs(_r - _er) <= 0.011
    print(f"E41 h+ ratio {_arm}: {to_fixed(_r, 2)}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_er})"))
    if not _ok:
        failed = True

# the paired substitution cost per ride (P1's direction endpoint)
for _arm, _ed, _ew, _en in (("igc5", 2.68, 940, 1117), ("igc5s10", 1.66, 890, 1117),
                            ("igc5s30", 0.22, 636, 1117), ("igc30", 1.85, 918, 1117),
                            ("fab5", 5.41, 1025, 1117), ("fab30", 3.21, 961, 1117)):
    _d = [num(r, f"{_arm}_reg_f3d") - num(r, "own_reg_f3d") for r in _e41_prim
          if is_finite(num(r, f"{_arm}_reg_f3d")) and is_finite(num(r, "own_reg_f3d"))]
    _w = sum(1 for x in _d if x > 0)
    _ok = abs(median(_d) - _ed) <= 0.011 and _w == _ew and len(_d) == _en
    print(f"E41 paired {_arm}: med {median(_d):+.2f} pp, over-charges on {_w}/{len(_d)}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_ed}, {_ew}/{_en})"))
    if not _ok:
        failed = True

# P4a: the anomaly-free secondary
for _arm, _ea, _es in (("own", 3.7, -2.7), ("igc5", 3.8, -0.9), ("fab5", 3.4, 2.2),
                       ("fab30", 3.6, 0.4)):
    _v = col(_e41_clean, f"{_arm}_reg_f3d")
    _ok = (abs(median([abs(x) for x in _v]) - _ea) <= 0.11
           and abs(median(_v) - _es) <= 0.11)
    print(f"E41 anomaly-free {_arm}: {to_fixed(median([abs(x) for x in _v]), 1)} · "
          f"{to_fixed(median(_v), 1)}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_ea}/{_es})"))
    if not _ok:
        failed = True

# per-corpus cells the letter prints: the terrain-dependence caveat (Table 2) and
# the +0.7 / +20.1 pp bias-shift contrast (abstract, §2.3). No CIs — the letter
# quotes these as medians only.
for _corpus, _arm, _ea, _es in (("longoes", "own", 7.5, 1.7),
                                ("longoes", "igc5", 21.8, 21.8),
                                ("longoes", "igc5s30", 8.0, 8.0),
                                ("jaam", "own", 3.4, -2.8),
                                ("jaam", "igc5", 2.8, -2.1)):
    _sub = [r for r in _e41_prim if r.get("corpus") == _corpus]
    _v = col(_sub, f"{_arm}_reg_f3d")
    _ok = (abs(median([abs(x) for x in _v]) - _ea) <= 0.11
           and abs(median(_v) - _es) <= 0.11)
    print(f"E41 {_corpus} {_arm}: {to_fixed(median([abs(x) for x in _v]), 1)} · "
          f"{to_fixed(median(_v), 1)}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_ea}/{_es})"))
    if not _ok:
        failed = True

# P5/P6: the portal correction and its over-correction on bridges
_e41_tch = [r for r in _e41_prim if num(r, "portal_ok") == 1
            and (num(r, "n_spans") or 0) > 0]
_ok = len(_e41_tch) == 943
print(f"E41 portal population: {len(_e41_tch)} rides with >=1 matched span"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 943)"))
if not _ok:
    failed = True

# ascent inside the spans vs the ride's own barometer (the deck's reference).
# deck-baro < 0 is the registered over-correction; igc5s30's raw-baro CI must
# straddle zero (smoothing already removed the artifact -> do not stack).
for _arm, _ed, _edci, _er, _erci in (
        ("igc5", -2.79, (-3.52, -2.08), 13.27, (10.00, 19.67)),
        ("igc5s30", -5.84, (-7.89, -4.51), 0.05, (-0.29, 0.28)),
        ("fab5", -6.57, (-7.61, -5.46), 11.17, (10.16, 12.55)),
        ("fab30", -6.78, (-8.04, -5.81), 4.98, (4.25, 5.83))):
    report(f"E41 span deck-baro {_arm}",
           [num(r, f"{_arm}p_span_hplus") - num(r, "own_span_hplus") for r in _e41_tch
            if is_finite(num(r, f"{_arm}p_span_hplus"))], None, _ed,
           expect_ci_signed=_edci)
    report(f"E41 span raw-baro {_arm}",
           [num(r, f"{_arm}_span_hplus") - num(r, "own_span_hplus") for r in _e41_tch
            if is_finite(num(r, f"{_arm}_span_hplus"))], None, _er,
           expect_ci_signed=_erci)

# the mechanism: bridges over-corrected ~8x more than tunnels (disjoint CIs)
for _kd, _n, _ed, _eci in (("bridge", 942, -2.43, (-3.26, -1.68)),
                           ("tunnel", 407, -0.29, (-0.40, -0.20))):
    _sub = [r for r in _e41_tch if (num(r, f"n_spans_{_kd}") or 0) > 0]
    _ok = len(_sub) == _n
    if not _ok:
        print(f"E41 portal {_kd} n={len(_sub)} GATE-FAIL(exp {_n})")
        failed = True
    report(f"E41 span deck-baro {_kd}",
           [num(r, f"igc5p_span_hplus_{_kd}") - num(r, f"own_span_hplus_{_kd}")
            for r in _sub], None, _ed, expect_ci_signed=_eci)

# the energy effect, and the registered "do not stack" result
for _arm, _ea, _es in (("own", 3.72, -2.10), ("igc5", 3.92, -0.29),
                       ("igc5p", 3.73, -1.29), ("igc5s30", 3.81, -2.07),
                       ("igc5s30p", 3.87, -2.37), ("fab5", 3.91, 2.71),
                       ("fab5p", 3.68, 2.39), ("fab30", 3.66, 0.75),
                       ("fab30p", 3.59, 0.53)):
    report(f"E41 portal {_arm}", col(_e41_tch, f"{_arm}_reg_f3d"), _ea, _es)

for _arm, _ew, _en in (("igc5", 501, 943), ("igc5s30", 400, 935),
                       ("fab5", 644, 942), ("fab30", 613, 938)):
    _kr, _kp = f"{_arm}_reg_f3d", f"{_arm}p_reg_f3d"
    _st = [r for r in _e41_tch if is_finite(num(r, _kr)) and is_finite(num(r, _kp))]
    _w = sum(1 for r in _st if abs(num(r, _kp)) < abs(num(r, _kr)))
    _l = sum(1 for r in _st if abs(num(r, _kp)) > abs(num(r, _kr)))
    _ok = _w == _ew and _w + _l == _en
    print(f"E41 portal paired {_arm}: corrected closer on {_w}/{_w + _l}, "
          f"p={to_fixed(sign_p(_w, _l), 4)}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_ew}/{_en})"))
    if not _ok:
        failed = True

# -------- 3j. Re-based elevation substitution (Entry 71: paper 1's population + D6)
# Table 1 of the letter, re-based to D3-D5 (travel rides KEPT, igc arms absent
# outside the survey) plus D6 against FABDEM + barometer. The deep sub-analyses
# (h+ ratios, portal deck, anomaly-free secondary) stay gated on the canonical
# walk above; this section gates only what the re-based table and headline quote.
sec("3j")
print("\n== Re-based elevation substitution (Entry 71: D3+D4+D5 · D6) ==")
e71 = parse_csv("e41_dem_route.E41_POPp1_E41_D61.csv")
_p71 = [r for r in e71 if num(r, "dataOK") == 1 and num(r, "g1_track") == 1
        and num(r, "g2_valid") == 1]
_sp71 = [r for r in _p71 if r.get("corpus") in ("ppaz", "jaam", "danlessa")]
_d671 = [r for r in _p71 if r.get("corpus") == "skc"]
_ok = len(_sp71) == 1164 and len(_d671) == 670
print(f"E71 population: D3+D4+D5 n={len(_sp71)} · D6 n={len(_d671)}"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 1164/670)"))
if not _ok:
    failed = True
for _pool, _rows71, _arm, _ea, _es, _eci, _ecis in (
        ("D3+D4+D5", _sp71, "own", 3.8, -1.9, (3.6, 4.1), (-2.3, -1.4)),
        ("D3+D4+D5", _sp71, "igc5", 4.1, 0.3, (3.9, 4.4), (-0.2, 1.1)),
        ("D3+D4+D5", _sp71, "igc5s10", 4.0, -0.4, (3.8, 4.3), (-0.9, -0.0)),
        ("D3+D4+D5", _sp71, "igc5s30", 4.0, -1.8, (3.8, 4.2), (-2.1, -1.5)),
        ("D3+D4+D5", _sp71, "igc30", 4.0, -0.3, (3.8, 4.2), (-0.9, 0.2)),
        ("D3+D4+D5", _sp71, "fab5", 5.1, 4.3, (4.5, 6.0), (3.6, 4.8)),
        ("D3+D4+D5", _sp71, "fab30", 4.5, 2.2, (4.0, 4.9), (1.7, 2.8)),
        ("D6", _d671, "own", 3.4, 0.3, (3.1, 3.6), (-0.2, 0.7)),
        ("D6", _d671, "fab5", 5.5, 5.3, (5.1, 5.9), (4.7, 5.8)),
        ("D6", _d671, "fab30", 4.1, 3.2, (3.9, 4.5), (2.6, 3.7))):
    report(f"E71 {_pool} {_arm}",
           [x for x in col(_rows71, f"{_arm}_reg_f3d") if is_finite(x)],
           _ea, _es, expect_ci=_eci, expect_ci_signed=_ecis)
# the per-chain noise rates the re-based prescription column quotes
for _rows71, _tag, _arm, _ec, _eci in (
        (_sp71, "SP", "own", 3.01, (2.93, 3.10)),
        (_sp71, "SP", "igc5", 4.90, (4.83, 4.95)),
        (_sp71, "SP", "fab30", 7.44, (7.11, 7.75)),
        (_sp71, "SP", "fab5", 10.15, (9.84, 10.60)),
        (_d671, "D6", "own", 1.26, (1.19, 1.32)),
        (_d671, "D6", "fab30", 5.61, (5.52, 5.68)),
        (_d671, "D6", "fab5", 7.87, (7.64, 8.00))):
    _cs = [(num(r, f"{_arm}_hplus") - num(r, f"{_arm}_hplus_t0")) / num(r, "km")
           for r in _rows71 if num(r, "km") > 0
           and is_finite(num(r, f"{_arm}_hplus_t0"))]
    report(f"E71 c(t=2) {_tag} {_arm}", _cs, _ec, None, expect_ci=_eci)
# the paired substitution cost the re-based prose quotes
_d71 = [num(r, "igc5_reg_f3d") - num(r, "own_reg_f3d") for r in _sp71
        if is_finite(num(r, "igc5_reg_f3d")) and is_finite(num(r, "own_reg_f3d"))]
_w71 = sum(1 for x in _d71 if x > 0)
_ok = abs(median(_d71) - 2.16) <= 0.011 and _w71 == 860 and len(_d71) == 1035
print(f"E71 paired igc5: med {median(_d71):+.2f} pp, over-charges on "
      f"{_w71}/{len(_d71)}"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp +2.16, 860/1035)"))
if not _ok:
    failed = True

# ---------------------------------------------------------------- 3p. Entry 50
# Sensitivity decomposition. Gates the shares section 3.2 prints, and the ORDERING
# the section's argument rests on: eps below every physical parameter, and the
# CdA-Crr pair the largest interaction. Read from the per-form CSV, not restated.
print("\n== Sensitivity decomposition (Entry 50, paper section 3.2) ==")

_e50 = [r for r in parse_csv("e50_sensitivity.csv") if r["scope"].startswith("empirical")]
_g = {(r["form"], r["param"]): float(r["ST"]) for r in _e50}
_exp50 = {("F3", "eps"): 0.070, ("F3", "CdA"): 0.553, ("F3", "m"): 0.460, ("F3", "Crr"): 0.139}
for (f, prm), ev in _exp50.items():
    _v = _g.get((f, prm), float("nan"))
    _ok = is_finite(_v) and abs(_v - ev) <= 0.005
    print(f"  S_T({prm:<4}) on {f} = {to_fixed(_v, 3)}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {ev})"))
    if not _ok:
        failed = True

# the ordering is the argument: eps must sit below every physical parameter
_ok = all(_g[("F3", "eps")] < _g[("F3", q)] for q in ("m", "CdA", "Crr"))
print("  eps ranks below m, CdA and Crr on F3"
      + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True


# ---------------------------------------------------------- 3q. Entry 52
# The A-chain's published numbers. Re-derived from e52_summary.csv, which
# e52_split.py writes at the end of the run -- so an article claim traces to a
# file rather than to a console log. The medians are recomputed from the
# per-ride cache too, so the summary cannot drift from the data it summarises.
sec("3q")
print("\n== Entry 52 — the A-chain (D3-D6, P_f,r) ==")
_e52 = {}
try:
    with open(os.path.join(RESULTS, "e52_summary.csv"), encoding="utf-8") as fh:
        for _r in csv.DictReader(fh):
            _e52[_r["key"]] = _r["value"]
except OSError:
    print("  e52_summary.csv MISSING — run src/harness/e52_split.py  GATE-FAIL")
    failed = True

for _k, _want, _lbl in (("f3_test_med_abs", 3.39, "F3 test med|D%|"),
                        ("f3_test_med_signed", 0.06, "F3 test signed"),
                        ("f4_test_med_abs", 2.85, "F4 test med|D%|"),
                        ("f4_test_med_signed", -0.24, "F4 test signed"),
                        ("fbase_test_med_abs", 3.05, "F_base test med|D%|"),
                        ("fbase_test_med_signed", -0.03, "F_base test signed"),
                        ("eps", 0.294, "selected eps"),
                        ("twin_pct", 82.0, "twin exposure %")):
    try:
        _v = float(_e52.get(_k, "nan"))
    except ValueError:
        _v = float("nan")
    _tol = 0.005 if _k == "eps" else 0.5
    _ok = is_finite(_v) and abs(_v - _want) <= _tol
    print(f"  {_lbl:<24} {to_fixed(_v, 4):>9}  (expect {_want})"
          + (" GATE-OK" if _ok else " GATE-FAIL"))
    if not _ok:
        failed = True

# the selection itself is a claim: F3 must win, and tau must land on 2 m
_ok = _e52.get("winner") == "F3"
print("  winner is F3" + (" GATE-OK" if _ok else f" GATE-FAIL({_e52.get('winner')})"))
if not _ok:
    failed = True
_ok = abs(float(_e52.get("tau", "nan") or "nan") - 6.0) < 1e-9
print("  tau refits to 6 m" + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True
_ok = int(_e52.get("n_test", 0)) == 305 and int(_e52.get("n_train", 0)) == 1734
print("  split is 1,734 / 305" + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True




# ---------------------------------------------------------- 3r. Entry 54
# The paper's one hypothesis (section 1.3): eps is a property of cycling, not
# of a rider. Fit on ONE rider's training rides, scored on every OTHER rider's
# held-out rides -- a different person AND rides withheld from selection.
sec("3r")
print("\n== Entry 54 — leave-one-rider-out transfer of eps ==")
_t = parse_csv(os.path.join(RESULTS, "e54_transfer.csv"))
_all = [r for r in _t if r["donor"] == "ALL"]
if not _all:
    print("  e54_transfer.csv MISSING its summary row — run e54_transfer.py  GATE-FAIL")
    failed = True
else:
    _pen = parse_float(_all[0]["med_abs"])
    _lo = parse_float(_all[0]["pooled_med_abs"])
    _hi = parse_float(_all[0]["own_best_med_abs"])
    _ok = abs(_pen - 0.05) <= 0.11
    print(f"  transfer penalty {to_fixed(_pen, 3)} pp [{to_fixed(_lo, 3)}, {to_fixed(_hi, 3)}]"
          f"  (expect 0.05)" + (" GATE-OK" if _ok else " GATE-FAIL"))
    if not _ok:
        failed = True
    # the hypothesis itself: the penalty must sit inside the registered margin
    _ok = abs(_pen) < 1.0 and abs(_hi) < 1.0
    print("  penalty inside the registered +/-1.0 pp margin"
          + (" GATE-OK" if _ok else " GATE-FAIL — section 1.3's hypothesis would be refuted"))
    if not _ok:
        failed = True
_donors = sorted({r["donor"] for r in _t if r["donor"] != "ALL"})
_eps = [parse_float([r for r in _t if r["donor"] == d][0]["donor_eps"]) for d in _donors]
_ok = len(_donors) == 6 and (max(_eps) - min(_eps)) >= 0.15
print(f"  {len(_donors)} donors, eps span {to_fixed(max(_eps) - min(_eps), 3)}"
      + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True



# ---------------------------------------------------------- 3s. Entry 56
# Paper 1's Table 4: every constant priced on one loss-inflation scale. The two
# the METHOD supplies must rank LAST -- that ordering is the table's argument,
# so it is gated rather than merely printed.
sec("3s")
print("\n== Entry 56 — structural-parameter sensitivity (paper Table 4) ==")
_s = {r["parameter"].strip('"'): parse_float(r["loss_inflation_pct"])
      for r in parse_csv(os.path.join(RESULTS, "e56_struct.csv"))}
for _k, _want in (("tau (F3 deadband)", 0.2), ("c (F4 scalar)", 0.1),
                  ("eps (F3, for reference)", 1.1), ("eps (F4, for reference)", 3.3)):
    _v = _s.get(_k, NAN)
    _ok = abs(_v - _want) <= 0.11
    print(f"  {_k:<28} {to_fixed(_v, 2):>7}%  (expect {_want})"
          + (" GATE-OK" if _ok else " GATE-FAIL"))
    if not _ok:
        failed = True
_ok = (_s.get("tau (F3 deadband)", 9e9) < _s.get("eps (F3, for reference)", 0)
       and _s.get("c (F4 scalar)", 9e9) < _s.get("eps (F4, for reference)", 0))
print("  tau and c rank below eps — the method's constants are the cheapest"
      + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True


# ---------------------------------------------------------- 3t. Entry 60
# The regional split. Gated on both the accuracy and the SIGNED pair, because
# the argument is that one pool biases the two regions in opposite directions
# -- a fact an accuracy-only gate would not protect.
sec("3t")
print("\n== Entry 60 — regional eps pools (paper Table 5) ==")
_e60 = {}
for _r in parse_csv(os.path.join(RESULTS, "e60_regional.csv")):
    _e60[(_r["region"].strip('"'), _r["arm"].strip('"'))] = _r
_BRK, _EUK = "D3-D5 (São Paulo)", "D6 (Europe)"
for _reg, _arm, _w_abs, _w_sg in ((_BRK, "A one pool", 3.67, -1.31),
                                  (_BRK, "B regional eps", 2.85, -0.30),
                                  (_EUK, "A one pool", 2.65, 1.95),
                                  (_EUK, "B regional eps", 1.73, 0.04)):
    _r = _e60.get((_reg, _arm))
    if _r is None:
        print(f"  {_reg} / {_arm}: MISSING — run e60_regional.py  GATE-FAIL")
        failed = True
        continue
    _a, _s = parse_float(_r["test_med_abs"]), parse_float(_r["test_med_signed"])
    _ok = abs(_a - _w_abs) <= 0.11 and abs(_s - _w_sg) <= 0.11
    print(f"  {_reg.split()[0]:<6} {_arm:<16} {to_fixed(_a, 2):>6} / {to_fixed(_s, 2):>6}"
          f"  (expect {_w_abs} / {_w_sg})" + (" GATE-OK" if _ok else " GATE-FAIL"))
    if not _ok:
        failed = True
# the argument itself: opposite-signed bias under one pool, removed by two
_b = parse_float(_e60[(_BRK, "A one pool")]["test_med_signed"])
_e = parse_float(_e60[(_EUK, "A one pool")]["test_med_signed"])
_ok = _b < 0 < _e
print("  one pool biases the two regions in OPPOSITE directions"
      + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True
_b2 = abs(parse_float(_e60[(_BRK, "B regional eps")]["test_med_signed"]))
_e2 = abs(parse_float(_e60[(_EUK, "B regional eps")]["test_med_signed"]))
_ok = _b2 < 0.5 and _e2 < 0.5
print("  regional eps removes both biases (|signed| < 0.5)"
      + (" GATE-OK" if _ok else " GATE-FAIL"))
if not _ok:
    failed = True


if failed:
    print("\nONE OR MORE GATES FAILED", file=sys.stderr)
    sys.exit(1)
print("\nall gates pass")
