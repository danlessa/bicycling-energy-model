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

# transfer-only pool (D3+D4) — the paper's out-of-sample headline
for _lab, _col, _ea, _eci in (
        ("pooled D3+D4 smooth · ε=geom", "sm_geom", 5.6, (5.2, 6.2)),
        ("pooled D3+D4 canonical", "canon_d", 6.3, (5.8, 6.8))):
    strat_report(_lab, [col([r for r in rows_ if r.get("dataOK", "true") == "true"], _col)
                        for rows_ in _strata_transfer], _ea, _eci)

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
for _corpus, _em in PI_M.items():
    _mv = [num(r, "m_hat") for r in pi if r.get("corpus") == _corpus
           and r.get("m_src") in ("inverted", "thin")]
    _ok = abs(median(_mv) - _em) <= 0.11
    print(f"E33 m̂ {_corpus}: {to_fixed(median(_mv), 1)} (n={len(_mv)})"
          + (" GATE-OK" if _ok else f" GATE-FAIL(exp {_em})"))
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
