#!/usr/bin/env python3
"""bootstrap_ci.py — bootstrap 95% CIs + paired sign tests for the article's
headline medians (journal Entry 22; article v0.16 §7.1/§8.1/§8.4/§8.6/§8.8).

Python port of the retired bootstrap_ci.mjs (byte-identical output).

Reads ONLY the per-ride CSVs already written by the other harnesses — no
engine runs, no FIT parsing:
  model_comparison.csv                      (compare.py, 44 longões)
  censo_comparison.csv    (censo_compare, 62 clean)
  ppaz_comparison.csv / jaam_comparison.csv (ppaz_compare / jaam_compare)
  time_comparison.csv                       (time_compare)

Every published median is reproduced as a GATE (±0.11 tolerance for the
1-decimal journal rounding) before its CI is reported; any gate failure
exits non-zero. Bootstrap: percentile method, B = 10⁴, deterministic
mulberry32 seed so the run is reproducible. Paired comparisons: exact
two-sided sign test on |Δ%|.

Usage: python3 src/harness/bootstrap_ci.py
"""

from __future__ import annotations

from typing import Callable

import math
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


B = 10000


def boot_ci(values: list[float], seed: int) -> tuple[float, float]:
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
        if expect_ci is not None:
            ok = ok and abs(a_lo - expect_ci[0]) <= 0.06 and abs(a_hi - expect_ci[1]) <= 0.06
        if expect_ci_signed is not None:
            ok = ok and abs(s_lo - expect_ci_signed[0]) <= 0.06 and abs(s_hi - expect_ci_signed[1]) <= 0.06
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


def paired(label: str, rows: list[dict], col_a: str, col_b: str) -> None:
    w = l = 0
    for r in rows:
        a, b = abs(parse_float(r.get(col_a))), abs(parse_float(r.get(col_b)))
        if not is_finite(a) or not is_finite(b):
            continue
        if a < b:
            w += 1
        elif a > b:
            l += 1
    print(f"{label}: A closer on {w}/{w + l} ({to_fixed(100 * w / (w + l), 0)}%), "
          f"sign test p={to_fixed(sign_p(w, l), 4)}")


def strat_signed_gate(label: str, strata_cols: list[list[float]], es: float,
                      ecis: tuple[float, float]) -> None:
    global failed
    pooled = [x for v in strata_cols for x in v]
    ms = median(pooled)
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


# ---------- 1. Longões scoreboard (44 rides), §8.1 ----------
print("== Longões (44 power rides), §8.1 scoreboard ==")
lg = parse_csv("model_comparison.csv")
LG = [
    ("approx cf + 2m smooth", "cfS_vs_emp", 3.5, 2.1, (2.0, 5.6)),
    ("canonical", "canon_vs_emp", 5.2, -1.8, (3.8, 7.3)),
    ("canonical + 2m smooth", "canonS_vs_emp", 5.7, -3.6, None),
    ("approx cf + k_smooth", "ksmooth_vs_emp", 5.9, -0.6, (3.6, 8.3)),
    ("approx cf + sheet v_f", "cfsheet_vs_emp", 7.2, -0.6, None),
    ("approx cf + measured v_f", "cfmeas_vs_emp", 8.0, 6.6, None),
    ("approx cf", "cf_vs_emp", 8.6, 8.4, (7.2, 11.0)),
    ("approx off (baseline)", "off_vs_emp", 19.1, 19.1, (17.3, 21.5)),
]
for label, c, ea, es, eci in LG:
    report(label, col(lg, c), ea, es, expect_ci=eci)
paired("PAIRED champion (cfS) vs canonical", lg, "cfS_vs_emp", "canon_vs_emp")

# ---------- 1b. Longões FROZEN protocol (Entry 31 / paper Table 2) ----------
print("\n== Longões FROZEN protocol (44 rides), Entry 31 ==")
lf = parse_csv("longoes_frozen.csv")
LF = [
    ("form 1 · ε_d (original)", "f1_d", 14.9, 14.0, (10.6, 22.6)),
    ("form 2 · ε_d (split)", "f2_d", 7.9, 4.9, (5.5, 13.6)),
    ("form 3 · ε_d (proposed)", "f3_d", 8.2, 2.2, (4.5, 10.8)),
    ("form 4 · ε_d (scalar c)", "f4_d", 7.6, -0.5, (5.6, 11.6)),
    ("canonical (frozen)", "canon_d", 8.4, 2.5, (5.1, 10.9)),
]
for label, c, ea, es, eci in LF:
    report(label, col(lf, c), ea, es, expect_ci=eci)
_nr = sorted(col(lf, "noise_rate"))
_nm = median(_nr)
_ok = abs(_nm - 3.1) <= 0.11
print(f"ascent-noise rate: median {to_fixed(_nm, 2)} m/km "
      f"[IQR {to_fixed(_nr[int(0.25*(len(_nr)-1))], 1)}–{to_fixed(_nr[int(0.75*(len(_nr)-1))], 1)}]"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 3.1)"))
if not _ok:
    failed = True
paired("PAIRED frozen form 3 vs canonical", lf, "f3_d", "canon_d")
paired("PAIRED frozen form 4 vs canonical", lf, "f4_d", "canon_d")

# ---------- 2. Censo sweep (62 clean rides), §8.4 ----------
print("\n== Censo (clean urban rides), §8.4 sweep ==")
cz = [r for r in parse_csv("censo_comparison.csv") if r.get("dataOK") == "true"]
if len(cz) != 62:
    print(f"GATE-FAIL: expected 62 clean censo rides, got {len(cz)}")
    failed = True
CZ = [
    ("canonical", "canon_d", 6.6, -3.5, (4.7, 8.7), None),
    ("smooth · ε=0.10", "sm_0.10", 4.4, 3.3, None, None),
    ("smooth · ε=0.15", "sm_0.15", 4.8, 1.1, None, None),
    ("smooth · ε=0.20", "sm_0.20", 4.7, -0.9, (3.3, 6.2), None),
    ("poor-man · ε=0.20", "pm_0.20", 3.9, 1.1, (3.2, 6.1), None),
    ("poor-man · ε=0.25", "pm_0.25", 5.0, -1.4, None, None),
    ("poor-man · ε=geom", "pm_geom", 6.4, -3.4, (4.8, 8.6), None),
    ("smooth · ε=geom", "sm_geom", 7.7, -5.1, (6.0, 9.3), None),
    ("smooth · ε=0.00", "sm_0.00", 7.4, 7.2, None, (4.9, 9.2)),
    ("poor-man · ε=0.00", "pm_0.00", 10.4, 10.4, None, (8.2, 13.7)),
]
for label, c, ea, es, eci, ecis in CZ:
    report(label, col(cz, c), ea, es, expect_ci=eci, expect_ci_signed=ecis)
paired("PAIRED poor-man ε0.20 vs canonical", cz, "pm_0.20", "canon_d")
paired("PAIRED frozen sm_geom vs canonical", cz, "sm_geom", "canon_d")
paired("PAIRED frozen pm_geom vs canonical", cz, "pm_geom", "canon_d")

# ---------- 3. P. Paz (441) and JAAM (219), §8.6 ----------
print("\n== P. Paz (441 rides), §8.6 ==")
pp = parse_csv("ppaz_comparison.csv")
report("poor-man · ε=geom", col(pp, "pm_geom"), 4.9, 0.6, expect_ci=(4.4, 5.8))
report("smooth · ε=geom", col(pp, "sm_geom"), 5.8, 4.3, expect_ci=(5.3, 6.4))
report("smooth · ε=0.20", col(pp, "sm_0.20"), 10.1, 10.0, expect_ci=(9.3, 10.7))
report("poor-man · ε=0.20", col(pp, "pm_0.20"), 6.8, 5.4, expect_ci=(6.0, 7.6))
report("canonical", col(pp, "canon_d"), 6.8, 5.0, expect_ci=(6.2, 7.8))
paired("PAIRED pm_geom vs canonical", pp, "pm_geom", "canon_d")
paired("PAIRED pm_geom vs sm_0.20", pp, "pm_geom", "sm_0.20")

print("\n== JAAM (219 rides), §8.6 ==")
jm = parse_csv("jaam_comparison.csv")
report("smooth · ε=0.20", col(jm, "sm_0.20"), 3.5, 0.4, expect_ci=(3.1, 4.2))
report("smooth · ε=geom", col(jm, "sm_geom"), 5.5, -4.7, expect_ci=(4.4, 6.4))
report("poor-man · ε=geom", col(jm, "pm_geom"), 9.0, -8.4, expect_ci=(7.9, 9.7))
report("poor-man · ε=0.20", col(jm, "pm_0.20"), 5.6, -4.3, expect_ci=(4.8, 6.4))
report("canonical", col(jm, "canon_d"), 5.4, -5.0, expect_ci=(4.9, 6.1))
paired("PAIRED sm_0.20 vs sm_geom", jm, "sm_0.20", "sm_geom")

# JAAM real-descent statistics (paper §3.3; regenerated one-pass, Entry 31)
_sub = [r for r in jm if r.get("dataOK") == "true"
        and is_finite(num(r, "epsBal")) and is_finite(num(r, "epsCoast"))
        and num(r, "sbar") >= 0.03]
_eb = [num(r, "epsBal") for r in _sub]
_pred = [num(r, "epsCoast") - 0.13 for r in _sub]
_rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
_dyn = _rms([_eb[i] - _pred[i] for i in range(len(_eb))])
_f20 = _rms([x - 0.20 for x in _eb])
_best = _rms([x - median(_eb) for x in _eb])
_ok = (len(_sub) == 21 and abs(_dyn - 0.090) <= 0.005
       and abs(_f20 - 0.111) <= 0.005 and abs(_best - 0.085) <= 0.005)
print(f"JAAM real descents: n={len(_sub)} rms_dyn={to_fixed(_dyn, 3)} "
      f"rms_flat0.20={to_fixed(_f20, 3)} rms_best_in={to_fixed(_best, 3)}"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp n=21/0.090/0.111/0.085)"))
if not _ok:
    failed = True

# ---------- 3b. Author-full D5 (621 rides), paper §3.4 ----------
print("\n== Author-full (621 rides), paper §3.4 ==")
dl = [r for r in parse_csv("danlessa_comparison.csv") if r.get("dataOK", "true") == "true"]
if len(dl) != 621:
    print(f"GATE-FAIL: expected 621 clean author-full rides, got {len(dl)}")
    failed = True
report("smooth · ε=geom", col(dl, "sm_geom"), 6.2, -0.3, expect_ci=(5.6, 6.9))
report("poor-man · ε=geom", col(dl, "pm_geom"), 7.1, -1.9, expect_ci=(6.4, 8.1))
report("smooth · ε=0.20", col(dl, "sm_0.20"), 8.1, 5.6, expect_ci=(7.3, 8.7))
report("poor-man · ε=0.20", col(dl, "pm_0.20"), 6.9, 3.8, expect_ci=(6.2, 7.5))
report("canonical", col(dl, "canon_d"), 6.1, None, expect_ci=(5.5, 6.7))

# ---------- 3b2. Paired sign tests + descent statistics (paper §3.3-3.4) ----------
print("\n== Paired tests and descent statistics (paper §3.3-3.4) ==")
paired("PAIRED D3 sm_geom vs canonical", pp, "sm_geom", "canon_d")
paired("PAIRED D5 sm_geom vs canonical", dl, "sm_geom", "canon_d")


def descent_rms(rows: list[dict], label: str, exp_n: int | None = None,
                exp_pair: tuple[float, float] | None = None) -> None:
    """Frozen dynamic-eps RMS vs the corpus's own in-sample best flat, on
    real descents (s_bar >= 3%) — the paper's Table 4 RMS row."""
    global failed
    sub = [r for r in rows if r.get("dataOK", "true") == "true"
           and is_finite(num(r, "epsBal")) and is_finite(num(r, "epsCoast"))
           and num(r, "sbar") >= 0.03]
    eb = [num(r, "epsBal") for r in sub]
    pred = [num(r, "epsCoast") - 0.13 for r in sub]
    rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
    dyn = rms([eb[i] - pred[i] for i in range(len(eb))])
    flat_in = rms([x - median(eb) for x in eb])
    gap = median([num(r, "epsCoast") for r in sub]) - median(eb)
    ok = True
    if exp_n is not None:
        ok = ok and len(sub) == exp_n
    if exp_pair is not None:
        ok = ok and abs(dyn - exp_pair[0]) <= 0.002 and abs(flat_in - exp_pair[1]) <= 0.002
    print(f"{label.ljust(34)} n={str(len(sub)).rjust(3)}  "
          f"RMS dyn={to_fixed(dyn, 3)} vs own-flat={to_fixed(flat_in, 3)}  "
          f"gap={to_fixed(gap, 2)}"
          + ("" if exp_pair is None else (" GATE-OK" if ok else
             f" GATE-FAIL(exp n={exp_n} {exp_pair})")))
    if not ok:
        failed = True


descent_rms(pp, "D3 descents (assumed)", 161, (0.096, 0.145))
descent_rms(jm, "D4 descents (assumed)", 21, (0.090, 0.085))
descent_rms(dl, "D5 descents (in-sample)", 221, (0.092, 0.126))

# ---------- 3c. Pooled D3-D5 (paper Table 3; stratified bootstrap) ----------
print("\n== Pooled D3–D5 (1,281 rides), paper Table 3 ==")


def strat_report(label: str, strata: list[list[float]], expect_abs: float,
                 expect_ci: tuple[float, float]) -> None:
    """Pooled median with stratified bootstrap: resample within each corpus,
    pool, take the median (respects the within-corpus sampling model)."""
    global failed
    pooled_abs = [abs(x) for s in strata for x in s]
    m = median(pooled_abs)

    def ci(vals_per_stratum: list[list[float]], seed: int) -> tuple[float, float]:
        rand = rng(seed)
        stats = []
        for _ in range(B):
            samp = []
            for s in vals_per_stratum:
                n = len(s)
                samp.extend(s[int(rand() * n)] for _ in range(n))
            stats.append(median(samp))
        stats.sort()
        return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]

    lo, hi = ci([[abs(x) for x in s] for s in strata], 42)
    ok = (abs(m - expect_abs) <= 0.11
          and abs(lo - expect_ci[0]) <= 0.06 and abs(hi - expect_ci[1]) <= 0.06)
    print(f"{label.ljust(34)} n={len(pooled_abs)}  med|Δ%|={to_fixed(m, 2)} "
          f"[{to_fixed(lo, 1)}, {to_fixed(hi, 1)}]"
          + (" GATE-OK" if ok else f" GATE-FAIL(exp {expect_abs} ci{expect_ci})"))
    if not ok:
        failed = True


_strata_src = [pp, jm, dl]
_strata_transfer = [pp, jm]
for _lab, _col, _ea, _eci in (
        ("pooled smooth · ε=geom", "sm_geom", 5.9, (5.5, 6.2)),
        ("pooled poor-man · ε=geom", "pm_geom", 6.6, (6.3, 7.1)),
        ("pooled smooth · ε=0.20", "sm_0.20", 7.5, (7.0, 8.0)),
        ("pooled poor-man · ε=0.20", "pm_0.20", 6.6, (6.1, 7.0)),
        ("pooled canonical", "canon_d", 6.2, (5.9, 6.6))):
    strat_report(_lab, [col([r for r in rows_ if r.get("dataOK", "true") == "true"], _col)
                        for rows_ in _strata_src], _ea, _eci)

for _lab, _col, _es, _ecis in (
        ("T3 pooled signed sm_geom", "sm_geom", 0.4, (-0.1, 1.1)),
        ("T3 pooled signed pm_geom", "pm_geom", -2.4, (-3.0, -1.9)),
        ("T3 pooled signed sm_flat", "sm_0.20", 5.9, (5.2, 6.5)),
        ("T3 pooled signed pm_flat", "pm_0.20", 2.8, (2.2, 3.5)),
        ("T3 pooled signed canon", "canon_d", 0.7, (0.1, 1.3))):
    strat_signed_gate(_lab, [col([r for r in rows_ if r.get("dataOK", "true") == "true"], _col)
                             for rows_ in _strata_src], _es, _ecis)

# transfer-only pool (D3+D4) — the paper's out-of-sample headline (abs + signed)
for _lab, _col, _ea, _eci, _es, _ecis in (
        ("pooled D3+D4 smooth · ε=geom", "sm_geom", 5.6, (5.2, 6.2), 1.1, (0.4, 1.7)),
        ("pooled D3+D4 canonical", "canon_d", 6.3, (5.8, 6.8), 1.3, (0.6, 2.0))):
    _strata_cols = [col([r for r in rows_ if r.get("dataOK", "true") == "true"], _col)
                    for rows_ in _strata_transfer]
    strat_report(_lab, _strata_cols, _ea, _eci)
    _pooled_signed = [x for v in _strata_cols for x in v]
    _ms = median(_pooled_signed)
    _rand = rng(43)
    _stats = []
    for _ in range(B):
        _samp = []
        for v in _strata_cols:
            _n = len(v)
            _samp.extend(v[int(_rand() * _n)] for _ in range(_n))
        _stats.append(median(_samp))
    _stats.sort()
    _slo, _shi = _stats[250], _stats[9749]
    _ok = (abs(_ms - _es) <= 0.11 and abs(_slo - _ecis[0]) <= 0.06
           and abs(_shi - _ecis[1]) <= 0.06)
    print(f"  signed: {to_fixed(_ms, 2)} [{to_fixed(_slo, 1)}, {to_fixed(_shi, 1)}]"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_es} {_ecis})"))
    if not _ok:
        failed = True

# ---------- 3d. Per-ride inverted physics (Entry 33 / paper Table 5) ----------
print("\n== Per-ride inverted physics (Entry 33, Table 5) ==")
pi = parse_csv("perride_invert.csv")
PI = {
    "censo": [("f3_d", 7.0, -3.1, (5.4, 9.5)), ("f3_f", 5.8, -0.5, (4.9, 7.8)),
              ("f4_f", 5.4, 2.4, (3.2, 7.1)), ("canon_d", 7.8, -2.2, (4.7, 9.5))],
    "ppaz": [("f3_d", 5.1, -3.8, (4.6, 5.5)), ("f3_f", 3.2, 0.2, (2.7, 3.6)),
             ("f4_f", 4.8, -3.0, (4.3, 5.2)), ("canon_d", 5.7, -4.6, (5.3, 6.2))],
    "jaam": [("f3_d", 6.0, -5.2, (5.2, 6.5)), ("f3_f", 3.1, -0.4, (2.6, 3.3)),
             ("f4_f", 6.4, -5.3, (5.9, 7.0)), ("canon_d", 5.8, -4.9, (4.9, 6.5))],
    "danlessa": [("f3_d", 7.5, -4.0, (7.1, 8.0)), ("f3_f", 5.3, 0.9, (4.6, 6.1)),
                 ("f4_f", 5.8, -0.4, (5.3, 6.3)), ("canon_d", 7.2, -3.5, (6.7, 7.9))],
}
PI_M = {"longoes": 76.6, "censo": 82.3, "ppaz": 75.4, "jaam": 98.7, "danlessa": 73.7}
for _corpus, _exp in (("ppaz", 7.1), ("jaam", 9.7), ("danlessa", 9.3)):
    _sub = [r for r in pi if r.get("corpus") == _corpus]
    _v = [abs(num(r, "f4_d")) for r in _sub if is_finite(num(r, "f4_d"))]
    _ok = abs(median(_v) - _exp) <= 0.11
    print(f"E33 {_corpus} f4_d (caption note): {to_fixed(median(_v), 2)}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_exp})"))
    if not _ok:
        failed = True
for _corpus, _rows in PI.items():
    _sub = [r for r in pi if r.get("corpus") == _corpus]
    for _c, _ea, _es, _eci in _rows:
        report(f"E33 {_corpus} {_c}", col(_sub, _c), _ea, _es, expect_ci=_eci)
# pooled D3-D5 (Table 5 pooled column) — stratified, same convention as Table 3's pool
_pi_strata = [[r for r in pi if r.get("corpus") == c] for c in ("ppaz", "jaam", "danlessa")]
for _lab, _col, _ea, _eci in (
        ("E33 pooled f3_d", "f3_d", 6.3, (6.0, 6.6)),
        ("E33 pooled f3_f", "f3_f", 3.8, (3.6, 4.1)),
        ("E33 pooled f4_f", "f4_f", 5.7, (5.2, 6.0)),
        ("E33 pooled canon", "canon_d", 6.4, (6.1, 6.7))):
    strat_report(_lab, [col(s, _col) for s in _pi_strata], _ea, _eci)
# constants medians (Entry 33 constants table) + D1 per-ride mass accuracy
for _corpus, _field, _src, _exp, _tol in (
        ("ppaz", "crr_hat", "crr_src", 0.0083, 0.00011), ("jaam", "crr_hat", "crr_src", 0.0095, 0.00011),
        ("danlessa", "crr_hat", "crr_src", 0.0088, 0.00011),
        ("ppaz", "cda_hat", "cda_src", 0.258, 0.0011), ("jaam", "cda_hat", "cda_src", 0.391, 0.0011),
        ("danlessa", "cda_hat", "cda_src", 0.293, 0.0011)):
    _v = [num(r, _field) for r in pi if r.get("corpus") == _corpus
          and r.get(_src) == "inverted"]
    _ok = abs(median(_v) - _exp) <= _tol
    print(f"E33 {_field} {_corpus}: {median(_v):.4f} (n={len(_v)})"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_exp})"))
    if not _ok:
        failed = True
_d1 = [r for r in pi if r.get("corpus") == "longoes" and r.get("m_src") in ("inverted", "thin")
       and is_finite(num(r, "m_logged"))]
_me = [num(r, "m_hat") - num(r, "m_logged") for r in _d1]
_ok = abs(median(_me) - 2.4) <= 0.11 and abs(median([abs(e) for e in _me]) - 5.3) <= 0.11
print(f"E33 D1 m̂−m_logged: bias {to_fixed(median(_me), 1)}, |err| "
      f"{to_fixed(median([abs(e) for e in _me]), 1)} (n={len(_d1)})"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp +2.4/5.3)"))
if not _ok:
    failed = True
# ---------- 3e. Regime-consistent aero (Entry 35 / paper Table 6) ----------
print("\n== Regime-consistent aero (Entry 35, Table 6) ==")
e35 = parse_csv("e35_residual.csv")
T6 = {
    "censo": [("f3_d_reg", 4.6, 1.4, (2.7, 6.1)), ("f3_f_reg", 8.0, 6.4, (6.4, 10.6)),
              ("f4_f_reg", 8.4, 8.0, (7.2, 11.2)), ("canon_reg", 7.6, 4.6, (4.6, 9.9))],
    "ppaz": [("f3_d_reg", 3.1, -1.3, (2.8, 3.3)), ("f3_f_reg", 4.0, 3.6, (3.3, 4.7)),
             ("f4_f_reg", 3.9, -0.2, (3.5, 4.3)), ("canon_reg", 3.2, -1.2, (2.8, 3.6))],
    "jaam": [("f3_d_reg", 3.2, -2.7, (2.8, 3.6)), ("f3_f_reg", 2.8, 2.5, (2.1, 3.4)),
             ("f4_f_reg", 4.2, -2.4, (3.7, 4.8)), ("canon_reg", 3.3, -2.4, (2.6, 3.6))],
    "danlessa": [("f3_d_reg", 4.9, -0.5, (4.6, 5.3)), ("f3_f_reg", 5.9, 4.8, (5.1, 6.7)),
                 ("f4_f_reg", 5.3, 3.5, (4.7, 5.9)), ("canon_reg", 5.1, 0.3, (4.8, 5.7))],
}
for _corpus, _rows in T6.items():
    _sub = [r for r in e35 if r.get("corpus") == _corpus]
    for _c, _ea, _es, _eci in _rows:
        report(f"T6 {_corpus} {_c}", col(_sub, _c), _ea, _es, expect_ci=_eci)
_e35_strata = [[r for r in e35 if r.get("corpus") == c] for c in ("ppaz", "jaam", "danlessa")]
for _lab, _col, _ea, _eci in (
        ("T6 pooled f3_d_reg", "f3_d_reg", 3.9, (3.6, 4.1)),
        ("T6 pooled f3_f_reg", "f3_f_reg", 4.5, (4.1, 4.8)),
        ("T6 pooled f4_f_reg", "f4_f_reg", 4.5, (4.2, 4.8)),
        ("T6 pooled canon_reg", "canon_reg", 4.0, (3.7, 4.2))):
    strat_report(_lab, [col(s, _col) for s in _e35_strata], _ea, _eci)
for _lab, _col, _es, _ecis in (
        ("T6 pooled signed f3_d", "f3_d_reg", -1.4, (-1.8, -1.0)),
        ("T6 pooled signed f3_f", "f3_f_reg", 3.8, (3.4, 4.2)),
        ("T6 pooled signed f4_f", "f4_f_reg", 0.8, (0.2, 1.3)),
        ("T6 pooled signed canon", "canon_reg", -0.8, (-1.1, -0.5))):
    strat_signed_gate(_lab, [col(s, _col) for s in _e35_strata], _es, _ecis)

# braking strict-reading medians (paper §3.4 prose: 0.6-0.8% open / 1.3-1.4% stop-heavy)
for _corpus, _exp in (("longoes", 0.64), ("censo", 1.36), ("ppaz", 0.72),
                      ("jaam", 0.79), ("danlessa", 1.34)):
    _v = [num(r, "brake_share_cad0_pct") for r in e35 if r.get("corpus") == _corpus
          and is_finite(num(r, "brake_share_cad0_pct"))]
    _ok = abs(median(_v) - _exp) <= 0.011
    print(f"T6 brake-strict {_corpus}: {to_fixed(median(_v), 2)}%"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_exp})"))
    if not _ok:
        failed = True

# ---------- 3f. eps0 per dataset (Entry 36) ----------
print("\n== ε₀ per dataset (Entry 36) ==")
e36 = parse_csv("e36_eps0.csv")
for _corpus, _bal, _bias in (("longoes", 0.113, 0.127), ("censo", 0.070, 0.099),
                             ("ppaz", 0.115, 0.201), ("jaam", 0.098, 0.356),
                             ("danlessa", 0.115, 0.153)):
    _sub = [r for r in e36 if r.get("corpus") == _corpus]
    _g = [num(r, "gapR") for r in _sub if is_finite(num(r, "gapR"))
          and num(r, "balR_sbar") >= 0.03]
    _b = [num(r, "eps0_bias_i") for r in _sub if is_finite(num(r, "eps0_bias_i"))]
    _ok = abs(median(_g) - _bal) <= 0.0011 and abs(median(_b) - _bias) <= 0.0011
    print(f"E36 {_corpus}: balance-ε₀ {median(_g):.3f} bias-ε₀ {median(_b):.3f}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_bal}/{_bias})"))
    if not _ok:
        failed = True

_e36_str = [[r for r in e36 if r.get("corpus") == c] for c in ("ppaz", "jaam", "danlessa")]
_pg = [num(r, "gapR") for s in _e36_str for r in s
       if is_finite(num(r, "gapR")) and num(r, "balR_sbar") >= 0.03]
_pf = [num(r, "gapF") for s in _e36_str for r in s
       if is_finite(num(r, "gapF")) and num(r, "balR_sbar") >= 0.03]
_pb = [num(r, "eps0_bias_i") for s in _e36_str for r in s if is_finite(num(r, "eps0_bias_i"))]
_ok = (abs(median(_pg) - 0.115) <= 0.0011 and abs(median(_pf) - 0.109) <= 0.0011
       and abs(median(_pb) - 0.202) <= 0.0011)
print(f"E36 pooled D3-D5: balance-ε₀ reg {median(_pg):.3f} frz {median(_pf):.3f} "
      f"bias-ε₀ {median(_pb):.3f}" + (" GATE-OK" if _ok else " GATE-FAIL(exp .115/.109/.202)"))
if not _ok:
    failed = True

_pi_str = [[r for r in pi if r.get("corpus") == c] for c in ("ppaz", "jaam", "danlessa")]
for _lab, _col, _es, _ecis in (
        ("T5 pooled signed f3_d", "f3_d", -4.2, (-4.5, -3.7)),
        ("T5 pooled signed f3_f", "f3_f", 0.4, (-0.0, 0.8)),
        ("T5 pooled signed f4_f", "f4_f", -2.4, (-2.7, -1.9)),
        ("T5 pooled signed canon", "canon_d", -4.3, (-4.7, -3.9))):
    strat_signed_gate(_lab, [col(s, _col) for s in _pi_str], _es, _ecis)

for _corpus, _em in PI_M.items():
    _mv = [num(r, "m_hat") for r in pi if r.get("corpus") == _corpus
           and r.get("m_src") in ("inverted", "thin")]
    _ok = abs(median(_mv) - _em) <= 0.11
    print(f"E33 m̂ {_corpus}: {to_fixed(median(_mv), 1)} (n={len(_mv)})"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_em})"))
    if not _ok:
        failed = True

# ---------- 3g. Deadband-suspension thread (Entries 38-40 / paper §4.4) ----------
print("\n== Deadband thread (E39 τ* + E40 roller), §4.4 ==")
e39 = parse_csv("e39_tau_reg.csv")
_j39 = [r for r in e39 if r.get("corpus") == "jaam"]
_w = sum(1 for r in _j39 if is_finite(num(r, "t30_d")) and is_finite(num(r, "t20_d"))
         and abs(num(r, "t30_d")) < abs(num(r, "t20_d")))
_l = sum(1 for r in _j39 if is_finite(num(r, "t30_d")) and is_finite(num(r, "t20_d"))
         and abs(num(r, "t30_d")) > abs(num(r, "t20_d")))
_m35 = median([abs(num(r, "t35_d")) for r in _j39 if is_finite(num(r, "t35_d"))])
_m20 = median([abs(num(r, "t20_d")) for r in _j39 if is_finite(num(r, "t20_d"))])
_ok = (_w == 137 and _w + _l == 215 and sign_p(_w, _l) <= 0.001
       and abs(_m35 - 3.06) <= 0.011 and abs(_m20 - 3.24) <= 0.011)
print(f"E39 jaam: τ=3 beats τ=2 on {_w}/{_w + _l} (p={to_fixed(sign_p(_w, _l), 5)}); "
      f"med|Δ%| τ3.5={to_fixed(_m35, 2)} τ2.0={to_fixed(_m20, 2)}"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 137/215, 3.06/3.24)"))
if not _ok:
    failed = True


def _ranks(v: list) -> list:
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    for rank, i in enumerate(idx):
        r[i] = rank
    return r


def _spearman(xs: list, ys: list) -> float:
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    n_ = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    d_ = math.sqrt(sum((r - mx) ** 2 for r in rx) * sum((r - my) ** 2 for r in ry))
    return n_ / d_ if d_ > 0 else NAN


e40 = parse_csv("e40_roller.csv")
for _corpus, _erho, _eres in (("longoes", 0.444, 0.48), ("censo", 0.125, 0.44),
                              ("ppaz", 0.204, 0.23), ("jaam", 0.429, 0.03),
                              ("danlessa", 0.394, 0.46)):
    _sub = [r for r in e40 if r.get("corpus") == _corpus]
    _xy = [(num(r, "res_pct"), num(r, "f3_d_reg")) for r in _sub
           if is_finite(num(r, "res_pct")) and is_finite(num(r, "f3_d_reg"))]
    _rho = _spearman([a for a, _ in _xy], [b for _, b in _xy])
    _res = median([a for a, _ in _xy])
    _ok = abs(_rho - _erho) <= 0.0015 and abs(_res - _eres) <= 0.011
    print(f"E40 {_corpus}: ρ(RES,Δ%)={_rho:+.3f} RES med={to_fixed(_res, 2)}%"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_erho}/{_eres})"))
    if not _ok:
        failed = True

# ---------- 3h. Lumped-eps proxy (Entry 42) ----------
print("\n== Lumped ε proxy (Entry 42) ==")
e42 = parse_csv("e42_lump.csv")
for _corpus, _de in (("longoes", -0.079), ("censo", -0.112), ("ppaz", -0.083),
                     ("jaam", -0.110), ("danlessa", -0.098)):
    _v = [num(r, "d_eps") for r in e42 if r.get("corpus") == _corpus
          and is_finite(num(r, "d_eps"))]
    _ok = abs(median(_v) - _de) <= 0.0011
    print(f"E42 {_corpus}: med(ε_lump − ε_d) = {median(_v):+.3f}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_de})"))
    if not _ok:
        failed = True
for _corpus, _w, _n in (("censo", 16, 69), ("jaam", 143, 215)):
    _sub = [r for r in e42 if r.get("corpus") == _corpus]
    _wc = sum(1 for r in _sub if is_finite(num(r, "f3_lump")) and is_finite(num(r, "f3_d"))
              and abs(num(r, "f3_lump")) < abs(num(r, "f3_d")))
    _lc = sum(1 for r in _sub if is_finite(num(r, "f3_lump")) and is_finite(num(r, "f3_d"))
              and abs(num(r, "f3_lump")) > abs(num(r, "f3_d")))
    _ok = _wc == _w and _wc + _lc == _n and sign_p(_wc, _lc) <= 0.001
    print(f"E42 paired {_corpus}: {_wc}/{_wc + _lc}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_w}/{_n})"))
    if not _ok:
        failed = True

# ---------- 3i. Elevation-source substitution (Entry 41 / paper 2) ----------
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

# ---------- 3j. D6 + the deficit's form (Entries 43-45, paper §1.3.2/§3.2) ----------
print("\n== D6 European corpus (Entry 43) ==")
d6 = parse_csv("skc_comparison.csv")
_d6ok = [r for r in d6 if r.get("dataOK", "true") == "true"]
_ok = len(d6) == 743 and len(_d6ok) == 740
print(f"E43 population: {len(d6)} evaluated, {len(_d6ok)} above the physical floor"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 743/740)"))
if not _ok:
    failed = True
_riders = ["user_1", "user_2", "user_3", "user_5"]
_d6str = [[r for r in _d6ok if r.get("rider") == u] for u in _riders]
# Guard: an empty stratum means a filter matched nothing (a renamed column, or a
# boolean written "True" where every other harness writes "true" — both happened
# while this section was being written). Report it as a FAILURE rather than
# crashing the battery on an empty median, which is what it did the first time.
if not all(_d6str) or not _d6ok:
    print("E43 strata: EMPTY — a filter matched nothing GATE-FAIL")
    failed = True
else:
    # strat_report REQUIRES an expected CI — passing None crashed it on the
    # `abs(lo - expect_ci[0])` comparison. The bands are Entry 43's published
    # stratified brackets.
    for _lab, _col_, _ea, _eci in (("E43 F3·ε_d pooled", "f3_d", 3.16, (2.9, 3.5)),
                                   ("E43 simulation pooled", "canon_d", 3.15, (2.9, 3.3))):
        strat_report(_lab, [col(s, _col_) for s in _d6str], _ea, _eci)
# P2: F4's bias sits 3-6 points BELOW F3's, predicted from the corpus noise rate
_b3 = median(col(_d6ok, "f3_d"))
_b4 = median(col(_d6ok, "f4_d"))
_ok = -6.0 <= _b4 - _b3 <= -3.0
print(f"E43 P2 F4−F3 bias delta = {_b4 - _b3:+.2f} points"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp -6..-3)"))
if not _ok:
    failed = True
# the measured noise rate that P2 was derived from, before any energy was computed
_nr = median(col(_d6ok, "noise_rate"))
_ok = abs(_nr - 1.24) <= 0.05
print(f"E43 noise rate c = {_nr:.2f} m/km"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 1.24)"))
if not _ok:
    failed = True
# P3: the deficit spread across riders — the paper's portability bound
for _u, _g in (("user_1", 0.117), ("user_2", 0.298), ("user_3", 0.080)):
    _v = [num(r, "eps_gap") for r in _d6ok if r.get("rider") == _u
          and is_finite(num(r, "eps_gap"))]
    _ok = abs(median(_v) - _g) <= 0.006
    print(f"E43 deficit gap {_u}: {median(_v):.3f}"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_g})"))
    if not _ok:
        failed = True

print("\n== Occupancy sigmoids (Entry 44, paper §1.3.2) ==")
e44 = parse_csv("e44_scurve_fits.csv")
_s50 = {r["group"]: num(r, "s50_pct") for r in e44}
# the article claims the two rider populations do not overlap in s50
_br = [_s50[g] for g in ("D1", "D3", "D4", "D5") if g in _s50]
_eu = [_s50[g] for g in _s50 if g.startswith("D6")]
_ok = bool(_br) and bool(_eu) and max(_br) < min(_eu)
print(f"E44 s50: Brazilian {min(_br):.1f}-{max(_br):.1f}% vs European "
      f"{min(_eu):.1f}-{max(_eu):.1f}%"
      + (" GATE-OK (disjoint)" if _ok else " GATE-FAIL(expected disjoint)"))
if not _ok:
    failed = True
# H-P2 refuted: slope must beat speed on held-out RMSE by a wide margin
_sr = median([num(r, "s_rmse_out") for r in e44 if is_finite(num(r, "s_rmse_out"))])
_vr = median([num(r, "v_rmse_out") for r in e44 if is_finite(num(r, "v_rmse_out"))])
_ok = _vr / _sr >= 2.5
print(f"E44 slope vs speed held-out RMSE: {_sr:.4f} vs {_vr:.4f} ({_vr/_sr:.1f}x)"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp >=2.5x)"))
if not _ok:
    failed = True

print("\n== Grade-inverse deficit, eq. (8) (Entry 45, paper §3.2.1) ==")
# eq. (8)'s constant is fitted on paper 1's CLAMPED quantity. Refitting it here
# from the per-ride CSV is the gate: it catches the clamped/unclamped mix-up that
# produced three wrong readings while this entry was being written.
e45 = parse_csv("e45_ridelevel.paper.csv")
# Compare `half` NUMERICALLY: the CSV writer formats every non-string as a float,
# so the column holds "0.00000"/"1.00000" and a string test against "0" silently
# selects nothing. Third filter-matched-nothing bug in this section; numeric
# comparison is robust to either format.
_fit = [r for r in e45 if num(r, "half") < 0.5 and is_finite(num(r, "d_meas"))]
_out = [r for r in e45 if num(r, "half") >= 0.5 and is_finite(num(r, "d_meas"))]
if not _fit or not _out:
    print(f"E45 split: fit={len(_fit)} out={len(_out)} — a filter matched nothing GATE-FAIL")
    failed = True
else:
    _k = median([num(r, "d_meas") * num(r, "s_bar") for r in _fit])
    _ok = abs(_k - 0.0051) <= 0.0002
    print(f"E45 eq.(8) k = {_k:.4f} (n_fit={len(_fit)})"
          + (" GATE-OK" if _ok else " GATE-FAIL(exp 0.0051)"))
    if not _ok:
        failed = True
    # eq. (8) must return the frozen 0.13 at the calibration corpus's typical descent
    # Tolerance tightened to +/-0.001 and the expectation corrected to 0.130.
    # At +/-0.004 this gate PASSED while the article printed 0.131 — a number
    # derived from the ROUNDED k (0.0051/0.039 = 0.1308) rather than the fitted
    # one (0.00506/0.039 = 0.1297). A gate whose tolerance exceeds the rounding
    # precision of the claim cannot defend that claim.
    # Anchored on D1's MEASURED median descent grade, recomputed here. The
    # previous version used 3.9% — which is the grade at which eq. (8) exactly
    # equals 0.13, i.e. reverse-engineered from the desired output and then
    # described in the article as "D1's typical descent". D1's median is 3.80%.
    _d1s = [num(r, "s_bar") for r in e45 if r.get("group") == "D1"
            and is_finite(num(r, "s_bar"))]
    _at = _k / median(_d1s) if _d1s else float("nan")
    _ok = bool(_d1s) and abs(_at - 0.133) <= 0.002
    print(f"E45 eq.(8) at D1's median s̄={100*median(_d1s):.2f}%: {_at:.4f} "
          f"(article claims 0.133)"
          + (" GATE-OK" if _ok else " GATE-FAIL(exp 0.133)"))
    if not _ok:
        failed = True
    # held-out: eq. (8) beats the best single constant, and by the published margin
    _apr = median([num(r, "d_meas") for r in _fit])
    _eg = median([abs(_k / num(r, "s_bar") - num(r, "d_meas")) for r in _out
                  if num(r, "s_bar") > 0])
    _ea = median([abs(_apr - num(r, "d_meas")) for r in _out])
    _w = sum(1 for r in _out if num(r, "s_bar") > 0
             and abs(_k / num(r, "s_bar") - num(r, "d_meas")) < abs(_apr - num(r, "d_meas")))
    _l = sum(1 for r in _out if num(r, "s_bar") > 0
             and abs(_k / num(r, "s_bar") - num(r, "d_meas")) > abs(_apr - num(r, "d_meas")))
    _ok = (abs(_eg - 0.055) <= 0.003 and abs(_ea - 0.067) <= 0.003
           and _w == 344 and sign_p(_w, _l) <= 1e-4)
    print(f"E45 held-out: eq.(8) {_eg:.4f} vs constant {_ea:.4f}, wins {_w}/{_w + _l}, "
          f"p={sign_p(_w, _l):.1e}"
          + (" GATE-OK" if _ok else " GATE-FAIL(exp 0.055/0.067/344)"))
    if not _ok:
        failed = True
    # the scope figure the article leans on: half the rides fall BELOW the 3% regime
    # The article's scope figure is about the evaluation behind TABLE 3, i.e.
    # D2-D5 (1,366 rides), NOT all nine corpora scored in Entry 45 (2,155, which
    # adds D1 and 745 rides of an external deposit this paper never introduces).
    # The first version of this gate used 2155 and so certified 52% when the
    # article's own claim needs 69% — a mismatched denominator the gate could not
    # see because it hardcoded the same wrong one.
    _t3 = [r for r in e45 if r.get("group") in ("D2", "D3", "D4", "D5")]
    _t3n = 1366
    _share = 1 - len(_t3) / _t3n
    _ok = 0.66 <= _share <= 0.71
    print(f"E45 scope (Table 3 corpora): {len(_t3)} of {_t3n} at s̄>=3% -> "
          f"{100*_share:.0f}% below the regime threshold"
          + (" GATE-OK" if _ok else " GATE-FAIL(exp ~69%)"))
    if not _ok:
        failed = True

# ---------- 4. Time model, P. Paz (§8.8 primary endpoint) ----------
# Target = tMovBin, exactly as time_compare's scoreboard() scores it.
print("\n== Time model, P. Paz (§8.8 primary endpoint) ==")
tm = [r for r in parse_csv("time_comparison.csv") if r.get("corpus") == "ppaz"]


def t_delta(r: dict, c: str) -> float:
    return 100 * (num(r, c) - num(r, "tMovBin")) / num(r, "tMovBin")


report("T1b full (frozen)", [x for x in (t_delta(r, "T1b_pred") for r in tm) if is_finite(x)], 6.6, 3.8, expect_ci=(5.9, 7.2))
report("T0 naive x/v_f", [x for x in (t_delta(r, "T0_pred") for r in tm) if is_finite(x)], 7.6, None, expect_ci=(7.0, 8.5))
_tw = sum(1 for r in tm if is_finite(t_delta(r, "T1b_pred")) and is_finite(t_delta(r, "T0_pred"))
          and abs(t_delta(r, "T1b_pred")) < abs(t_delta(r, "T0_pred")))
_tl = sum(1 for r in tm if is_finite(t_delta(r, "T1b_pred")) and is_finite(t_delta(r, "T0_pred"))
          and abs(t_delta(r, "T1b_pred")) > abs(t_delta(r, "T0_pred")))
_tp = sign_p(_tw, _tl)
_ok = _tw == 243 and abs(_tp - 0.012) <= 0.001
print(f"PAIRED T1b vs T0: {_tw}/{_tw + _tl}, p={to_fixed(_tp, 4)}"
      + (" GATE-OK" if _ok else " GATE-FAIL(exp 243/433 p=0.012)"))
if not _ok:
    failed = True

if failed:
    print("\nONE OR MORE GATES FAILED", file=sys.stderr)
    sys.exit(1)
print("\nall gates pass")
