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

Usage: python3 harness/bootstrap_ci.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))
from bem.jsfmt import to_fixed

RESULTS = os.path.join(REPO, "results")
os.makedirs(RESULTS, exist_ok=True)
failed = False

NAN = float("nan")


def parse_float(s):
    """JS parseFloat: leading numeric prefix or NaN."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return NAN


def is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


# --- CSV parser (quoted fields, no embedded newlines; strips quotes) ---
def parse_csv(p):
    with open(os.path.join(RESULTS, p), encoding="utf-8") as fh:
        text = fh.read().strip()
    lines = text.split("\n")

    def split(line):
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
def rng(seed):
    a = seed & 0xFFFFFFFF

    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[(n - 1) // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


B = 10000


def boot_ci(values, seed):
    rand = rng(seed)
    n = len(values)
    stats = []
    for _ in range(B):
        stats.append(median([values[int(rand() * n)] for _ in range(n)]))
    stats.sort()
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


def report(label, deltas, expect_abs=None, expect_signed=None):
    global failed
    abs_v = [abs(x) for x in deltas]
    m_abs, m_sgn = median(abs_v), median(deltas)
    a_lo, a_hi = boot_ci(abs_v, 42)
    s_lo, s_hi = boot_ci(deltas, 43)
    gate = ""
    if expect_abs is not None:
        ok = abs(m_abs - expect_abs) <= 0.11 and (
            expect_signed is None or abs(m_sgn - expect_signed) <= 0.11)
        gate = " GATE-OK" if ok else f" GATE-FAIL(exp {expect_abs}/{'null' if expect_signed is None else expect_signed})"
        if not ok:
            failed = True
    print(f"{label.ljust(34)} n={str(len(deltas)).rjust(3)}  "
          f"med|Δ%|={to_fixed(m_abs, 2).rjust(6)} [{to_fixed(a_lo, 1)}, {to_fixed(a_hi, 1)}]  "
          f"medΔ%={to_fixed(m_sgn, 2).rjust(7)} [{to_fixed(s_lo, 1)}, {to_fixed(s_hi, 1)}]{gate}")


# exact two-sided binomial sign test on paired |Δ%|
def log_c(n, k):
    s = 0.0
    for i in range(1, k + 1):
        s += math.log(n - k + i) - math.log(i)
    return s


LN2 = 0.6931471805599453  # Math.LN2


def sign_p(w, l):
    n = w + l
    p = 0.0
    for k in range(n + 1):
        pk = math.exp(log_c(n, k) - n * LN2)
        if k <= min(w, l) or k >= max(w, l):
            p += pk
    return min(1, p)


def paired(label, rows, col_a, col_b):
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


def num(r, c):
    return parse_float(r.get(c))


def col(rows, c):
    return [x for x in (num(r, c) for r in rows) if is_finite(x)]


# ---------- 1. Longões scoreboard (44 rides), §8.1 ----------
print("== Longões (44 power rides), §8.1 scoreboard ==")
lg = parse_csv("model_comparison.csv")
LG = [
    ("approx cf + 2m smooth", "cfS_vs_emp", 3.6, 2.2),
    ("canonical", "canon_vs_emp", 5.1, -1.7),
    ("canonical + 2m smooth", "canonS_vs_emp", 5.6, -3.5),
    ("approx cf + k_smooth", "ksmooth_vs_emp", 5.8, -0.5),
    ("approx cf + sheet v_f", "cfsheet_vs_emp", 7.2, -0.5),
    ("approx cf + measured v_f", "cfmeas_vs_emp", 8.2, 6.7),
    ("approx cf", "cf_vs_emp", 8.7, 8.6),
    ("approx off (baseline)", "off_vs_emp", 19.3, 19.3),
]
for label, c, ea, es in LG:
    report(label, col(lg, c), ea, es)
paired("PAIRED champion (cfS) vs canonical", lg, "cfS_vs_emp", "canon_vs_emp")

# ---------- 2. Censo sweep (62 clean rides), §8.4 ----------
print("\n== Censo (clean urban rides), §8.4 sweep ==")
cz = [r for r in parse_csv("censo_comparison.csv") if r.get("dataOK") == "true"]
if len(cz) != 62:
    print(f"GATE-FAIL: expected 62 clean censo rides, got {len(cz)}")
    failed = True
CZ = [
    ("canonical", "canon_d", 6.5, -3.4),
    ("smooth · ε=0.10", "sm_0.10", 4.5, 3.4),
    ("smooth · ε=0.15", "sm_0.15", 5.0, 1.3),
    ("smooth · ε=0.20", "sm_0.20", 4.6, -0.8),
    ("poor-man · ε=0.20", "pm_0.20", 3.9, 1.1),
    ("poor-man · ε=0.25", "pm_0.25", 4.8, -1.2),
    ("poor-man · ε=geom", "pm_geom", 6.3, -3.2),
    ("smooth · ε=geom", "sm_geom", 7.6, -4.9),
    ("smooth · ε=0.00", "sm_0.00", 7.6, 7.4),
    ("poor-man · ε=0.00", "pm_0.00", 10.5, 10.5),
]
for label, c, ea, es in CZ:
    report(label, col(cz, c), ea, es)
paired("PAIRED poor-man ε0.20 vs canonical", cz, "pm_0.20", "canon_d")

# ---------- 3. P. Paz (441) and JAAM (219), §8.6 ----------
print("\n== P. Paz (441 rides), §8.6 ==")
pp = parse_csv("ppaz_comparison.csv")
report("poor-man · ε=geom", col(pp, "pm_geom"), 4.9, 0.6)
report("canonical", col(pp, "canon_d"), 6.8, 5.0)
paired("PAIRED pm_geom vs canonical", pp, "pm_geom", "canon_d")
paired("PAIRED pm_geom vs sm_0.20", pp, "pm_geom", "sm_0.20")

print("\n== JAAM (219 rides), §8.6 ==")
jm = parse_csv("jaam_comparison.csv")
report("smooth · ε=0.20", col(jm, "sm_0.20"), 3.5, None)
report("smooth · ε=geom", col(jm, "sm_geom"), 5.5, None)
paired("PAIRED sm_0.20 vs sm_geom", jm, "sm_0.20", "sm_geom")

# ---------- 4. Time model, P. Paz (§8.8 primary endpoint) ----------
# Target = tMovBin, exactly as time_compare's scoreboard() scores it.
print("\n== Time model, P. Paz (§8.8 primary endpoint) ==")
tm = [r for r in parse_csv("time_comparison.csv") if r.get("corpus") == "ppaz"]


def t_delta(r, c):
    return 100 * (num(r, c) - num(r, "tMovBin")) / num(r, "tMovBin")


report("T1b full (frozen)", [x for x in (t_delta(r, "T1b_pred") for r in tm) if is_finite(x)], 6.6, 3.8)
report("T0 naive x/v_f", [x for x in (t_delta(r, "T0_pred") for r in tm) if is_finite(x)], 7.6, None)

if failed:
    print("\nONE OR MORE GATES FAILED", file=sys.stderr)
    sys.exit(1)
print("\nall gates pass")
