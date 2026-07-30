#!/usr/bin/env python3
"""Entry 50 — does eps earn its density? Variance decomposition of F1-F4's error.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 50) before any perturbation was
run. The question is editorial and the instrument is physical: paper 1 spends a
large share of its density on the deficit, and that is justified only if eps is a
material lever on prediction error.

    I = (D3..D6, P_a,g . P_f,r(m, Crr, CdA))     T = F1..F4     O = per-draw error

DECISION RULE (registered): S_T(eps) > 0.50 on F3 keeps the deficit work in paper
1; at or below, it becomes a future direction of research and paper 1 ships a flat
constant. F1, F2 and F4 are context and do not vote.

WHY THIS IS CHEAP. Each closed form reduces, per ride, to four geometry
aggregates - X, x_flat, h_plus, h_minus - after which E is arithmetic:

    E = a_roll*X + a_aero*x_aero + K * beta*(h_plus - eps*h_minus)

with x_aero = X for F1 (aero charged everywhere) and x_flat for F2-F4, the
profile smoothed for F3, and K = the F4 elevation-scalar factor (1 elsewhere).
So the profile is walked ONCE per ride and every subsequent evaluation is a
handful of flops. That is what makes a genuine Sobol design affordable over all
rides rather than the local-quadratic expansion the F_base draft needed.

THE ONE NONLINEARITY, which is also the only interaction channel: v_f is solved
from the ride's flat power against (m, Crr, CdA) and re-enters a_aero
quadratically. E is exactly linear in eps, and linear in m and Crr at fixed v_f.
So every interaction term this reports has a single physical origin - the aero
term's speed anchor - which is the (alpha, eps) pairing the paper describes
qualitatively.

RANGES are the empirical 5th/95th of the per-ride inversions actually observed,
not invented ones; eps spans its measured across-rider spread. Because a variance
decomposition ranks parameters partly by how wide their assumed ranges are, the
whole analysis is repeated under a +/-1 SD parameterisation and the verdict must
hold under both (registered as the result's main weakness).

Output: data/results/e50_sensitivity.csv + console report.
Run: python3 src/harness/e50_sensitivity.py        (E50_SMOKE=1 for a small N)
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np   # deviation from the harness stdlib-only rule, and deliberate:
# a Sobol design over 2,039 rides is ~10^10 scalar operations in pure Python and
# seconds when the v_f bisection and the energy evaluation are vectorised over
# rides. goal_smooth_rasters.py and e26_portal_profiles.py already import numpy.
from typing import Callable, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import (build_profile, deadband, empirical_kj,
                                    extract_regime_powers, is_finite,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

from perride_invert import (CLIMB_THR, DESC_THR, ENGINE_DX, KEFF, RESULTS, RHO,
                            TAU_SMOOTH, find_segments, geo_summary, headwind_ms,
                            invert_physics, iter_corpus, seg_integrals)
from e44_scurve import corpus_rides

SMOKE = bool(os.environ.get("E50_SMOKE"))
N_SOBOL = 64 if SMOKE else 4096
SEED = 46                      # 42/43 published CIs, 44 TOST, 45 Entry-49 CIs
GROUPS = ("D3", "D4", "D5", "D6-user_1", "D6-user_2", "D6-user_3", "D6-user_5")
FORMS = ("F1", "F2", "F3", "F4")
DECIDING_FORM = "F3"
THRESHOLD = 0.50
C_NOISE = 3.0                  # m/km, F4's scalar elevation correction

# Empirical 5th / 95th of the per-ride inversions on D3-D5, plus eps's measured
# across-rider spread. PARAM ORDER IS FIXED EVERYWHERE: m, CdA, Crr, eps.
NAMES = ("m", "CdA", "Crr", "eps")
RANGES_EMPIRICAL = ((66.5, 101.9), (0.149, 0.526), (0.0069, 0.0112), (0.08, 0.30))
# +/-1 SD about the median, the registered robustness parameterisation
RANGES_SD = ((66.9, 82.5), (0.245, 0.471), (0.0069, 0.0091), (0.11, 0.27))


# ----------------------------------------------------------------- ride prep

class Ride:
    """One ride reduced to what every form needs, plus its measured energy."""

    __slots__ = ("group", "emp", "p_flat", "X", "xf_raw", "hp_raw", "hm_raw",
                 "xf_sm", "hp_sm", "hm_sm", "wind", "k4")

    def __init__(self) -> None:
        self.k4 = 1.0


def aggregates(prof: dict, climb_thr: float) -> tuple[float, float, float, float]:
    """(X, x_flat, h_plus, h_minus) — the profile walked once.

    x_flat is the distance whose local slope is BELOW climb_thr, i.e. the
    distance F2-F4 charge aero over. Mirrors engines.approx_components exactly.
    """
    xs, hs = prof["x"], prof["h"]
    X = xf = hp = hm = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        X += dx
        if dh / dx < climb_thr:
            xf += dx
        if dh >= 0:
            hp += dh
        else:
            hm += -dh
    return X, xf, hp, hm


def build_rides() -> list[Ride]:
    out: list[Ride] = []
    seen: dict[str, int] = {}
    for group, pts, mass in corpus_rides():
        if group not in GROUPS:
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if SMOKE and i >= 20:
            continue
        try:
            emp = empirical_kj(pts)
            if not (is_finite(emp) and emp > 0):
                continue
            phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
            prof = resample_profile(phys, ENGINE_DX)
            if prof["x"][-1] - prof["x"][0] < 3000:
                continue
            profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
            rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
            p_flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
            if not (is_finite(p_flat) and p_flat > 0):
                continue
            r = Ride()
            r.group, r.emp, r.p_flat, r.wind = group, emp, p_flat, 0.0
            r.X, r.xf_raw, r.hp_raw, r.hm_raw = aggregates(prof, CLIMB_THR)
            _, r.xf_sm, r.hp_sm, r.hm_sm = aggregates(profS, CLIMB_THR)
            if r.hp_raw <= 0 or r.X <= 0:
                continue
            # F4's scalar elevation correction, as the published harnesses form it
            r.k4 = max(0.0, 1 - C_NOISE * (r.X / 1000) / r.hp_raw)
            out.append(r)
        except Exception:
            continue
    return out


# -------------------------------------------------------------- the forms

def flat_speed(p_flat: float, m: float, crr: float, cda: float,
               wind: float) -> float:
    """Scalar bisection for v_f — kept for the engine-parity check."""
    a = crr * m * G
    b = 0.5 * RHO * cda

    def wheel(v: float) -> float:
        rel = v + wind
        return (a + b * rel * abs(rel)) * v

    lo, hi = 0.0, 40.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if wheel(mid) < KEFF * p_flat:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def flat_speed_vec(pf: "np.ndarray", m: float, crr: float,
                   cda: float) -> "np.ndarray":
    """v_f for every ride at once. Same bracket and 60 halvings as the engine,
    so it is the scalar solver run in parallel rather than a different method
    (verified equal to flat_eq_speed to 0 ulp on a real ride)."""
    a = crr * m * G
    b = 0.5 * RHO * cda
    lo = np.zeros_like(pf)
    hi = np.full_like(pf, 40.0)
    tgt = KEFF * pf
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        w = (a + b * mid * np.abs(mid)) * mid
        under = w < tgt
        lo = np.where(under, mid, lo)
        hi = np.where(under, hi, mid)
    return 0.5 * (lo + hi)


def energy(r: Ride, form: str, m: float, cda: float, crr: float,
           eps: float, vf: float) -> float:
    """Closed-form energy in kJ. Linear in eps; vf carries all the coupling."""
    beta = m * G / KEFF
    a_roll = crr * m * G / KEFF
    rel = vf + r.wind
    a_aero = 0.5 * RHO * cda * rel * abs(rel) / KEFF
    if form == "F1":                      # aero charged over the whole route
        return (a_roll * r.X + a_aero * r.X + beta * (r.hp_raw - eps * r.hm_raw)) / 1000
    if form == "F2":                      # aero gated off climbs
        return (a_roll * r.X + a_aero * r.xf_raw + beta * (r.hp_raw - eps * r.hm_raw)) / 1000
    if form == "F3":                      # F2 on the deadband-smoothed profile
        return (a_roll * r.X + a_aero * r.xf_sm + beta * (r.hp_sm - eps * r.hm_sm)) / 1000
    # F4: F2 with the scalar elevation correction applied to the gravity terms
    return (a_roll * r.X + a_aero * r.xf_raw
            + r.k4 * beta * (r.hp_raw - eps * r.hm_raw)) / 1000


class Corpus:
    """The rides as column arrays, so a draw costs one vectorised pass."""

    def __init__(self, rides: Sequence[Ride]) -> None:
        col = lambda f: np.array([getattr(r, f) for r in rides], dtype=float)
        self.emp = col("emp")
        self.pf = col("p_flat")
        self.X = col("X")
        self.xf_raw, self.hp_raw, self.hm_raw = col("xf_raw"), col("hp_raw"), col("hm_raw")
        self.xf_sm, self.hp_sm, self.hm_sm = col("xf_sm"), col("hp_sm"), col("hm_sm")
        self.k4 = col("k4")
        self.n = len(rides)

    def err(self, form: str, th: Sequence[float]) -> float:
        """Median |Delta%| for one parameter draw — the scalar Sobol sees."""
        m, cda, crr, eps = th
        vf = flat_speed_vec(self.pf, m, crr, cda)
        beta = m * G / KEFF
        a_roll = crr * m * G / KEFF
        a_aero = 0.5 * RHO * cda * vf * np.abs(vf) / KEFF
        if form == "F1":
            e = a_roll * self.X + a_aero * self.X + beta * (self.hp_raw - eps * self.hm_raw)
        elif form == "F2":
            e = a_roll * self.X + a_aero * self.xf_raw + beta * (self.hp_raw - eps * self.hm_raw)
        elif form == "F3":
            e = a_roll * self.X + a_aero * self.xf_sm + beta * (self.hp_sm - eps * self.hm_sm)
        else:
            e = (a_roll * self.X + a_aero * self.xf_raw
                 + self.k4 * beta * (self.hp_raw - eps * self.hm_raw))
        return float(np.median(np.abs(100.0 * (e / 1000 - self.emp) / self.emp)))


# ------------------------------------------------------------------ Sobol

def rng(seed: int) -> Callable[[], float]:
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def sobol(rides: "Corpus", form: str, ranges: Sequence[tuple[float, float]],
          n: int, seed: int) -> dict:
    """Saltelli estimators for first-order S_i, total-order S_Ti, and pairwise S_ij.

    Deterministic: the sample matrices come from the project's mulberry32, not
    from a library RNG, so a re-run reproduces exactly.
    """
    k = len(ranges)
    rand = rng(seed)

    def draw() -> list[list[float]]:
        return [[lo + (hi - lo) * rand() for (lo, hi) in ranges] for _ in range(n)]

    A, B = draw(), draw()
    fA = [rides.err(form, a) for a in A]
    fB = [rides.err(form, b) for b in B]
    f0 = sum(fA) / n
    varY = sum((v - f0) ** 2 for v in fA) / (n - 1)
    if varY <= 0:
        return {"var": 0.0}

    # AB_i: A with column i taken from B
    fAB = []
    for i in range(k):
        rows = [a[:i] + [b[i]] + a[i + 1:] for a, b in zip(A, B)]
        fAB.append([rides.err(form, r) for r in rows])

    S, ST = [], []
    for i in range(k):
        # Saltelli 2010: S_i via fB*(fAB_i - fA); S_Ti via (fA - fAB_i)^2
        s = sum(fB[j] * (fAB[i][j] - fA[j]) for j in range(n)) / n / varY
        st = sum((fA[j] - fAB[i][j]) ** 2 for j in range(n)) / (2 * n) / varY
        S.append(s)
        ST.append(st)

    # second order: BA_ij = A with columns i and j from B  (closed-index route)
    S2 = {}
    for i in range(k):
        for j in range(i + 1, k):
            rows = []
            for a, b in zip(A, B):
                r = a[:]
                r[i], r[j] = b[i], b[j]
                rows.append(r)
            fABij = [rides.err(form, r) for r in rows]
            # closed second-order minus the two first-order closed indices
            vij = sum(fB[t] * (fABij[t] - fA[t]) for t in range(n)) / n / varY
            S2[(i, j)] = vij - S[i] - S[j]
    return {"S": S, "ST": ST, "S2": S2, "var": varY, "mean": f0}


# ------------------------------------------------------------------ report

def run(rides: "Corpus", ranges, tag: str, out_rows: list[dict]) -> dict:
    print(f"\n{'=' * 74}\n{tag}   |O| = {rides.n} rides, N = {N_SOBOL}\n{'=' * 74}")
    print(f"  {'form':<5}" + "".join(f"{f'S_{nm}':>9}" for nm in NAMES)
          + "  |" + "".join(f"{f'ST_{nm}':>9}" for nm in NAMES) + f"{'med|D%|':>10}")
    res = {}
    for form in FORMS:
        r = sobol(rides, form, ranges, N_SOBOL, SEED)
        res[form] = r
        print(f"  {form:<5}" + "".join(f"{to_fixed(v, 3):>9}" for v in r["S"])
              + "  |" + "".join(f"{to_fixed(v, 3):>9}" for v in r["ST"])
              + f"{to_fixed(r['mean'], 2):>10}")
        for i, nm in enumerate(NAMES):
            out_rows.append({"scope": tag, "form": form, "param": nm,
                             "S1": r["S"][i], "ST": r["ST"][i], "meanErr": r["mean"]})
    print(f"\n  strongest pairwise interactions ({DECIDING_FORM}):")
    s2 = sorted(res[DECIDING_FORM]["S2"].items(), key=lambda kv: -abs(kv[1]))[:3]
    for (i, j), v in s2:
        print(f"    {NAMES[i]:>4} x {NAMES[j]:<5} S2 = {to_fixed(v, 4)}")
    return res


def main() -> None:
    print("Entry 50 — variance decomposition of F1-F4 error over (m, CdA, Crr, eps)"
          + ("  [E50_SMOKE]" if SMOKE else ""))
    rides = build_rides()
    from collections import Counter
    print("rides:", len(rides), dict(Counter(r.group for r in rides)))

    corpus = Corpus(rides)
    rows: list[dict] = []
    emp = run(corpus, RANGES_EMPIRICAL, "empirical 5th-95th", rows)
    sd = run(corpus, RANGES_SD, "+/-1 SD (robustness)", rows)

    print(f"\n{'=' * 74}\nDECISION — registered rule: S_T(eps) > {THRESHOLD} on "
          f"{DECIDING_FORM} keeps eps in paper 1\n{'=' * 74}")
    ie = NAMES.index("eps")
    for tag, r in (("empirical", emp), ("+/-1 SD", sd)):
        st = r[DECIDING_FORM]["ST"][ie]
        print(f"  {tag:<12} S_T(eps) on {DECIDING_FORM} = {to_fixed(st, 4)}"
              f"   -> {'KEEP in paper 1' if st > THRESHOLD else 'FUTURE RESEARCH'}")
    print("\n  share by form (empirical ranges), S_T(eps):")
    for f in FORMS:
        print(f"    {f}  {to_fixed(emp[f]['ST'][ie], 4)}")

    name = "e50_sensitivity.SMOKE.csv" if SMOKE else "e50_sensitivity.csv"
    cols = ["scope", "form", "param", "S1", "ST", "meanErr"]
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(f'"{r[c]}"' if isinstance(r[c], str)
                              else to_fixed(float(r[c]), 6) for c in cols) + "\n")
    print(f"\nwrote {name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
