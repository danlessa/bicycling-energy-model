#!/usr/bin/env python3
"""Entry 45 — what should eps_0 be? A contest of ride-level summaries.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 45) before any estimator was
fitted. The target is the exact ledger quantity

    delta_meas = E_desc / (beta * h_minus)          over every descent cell,
                                                    on rides with s_bar >= 3%

and the ride-level identity delta_ride = sum(delta_i h_i) / sum(h_i) makes it the
drop-weighted mean of the cell-level curve — which is why evaluating the curve AT
the mean grade (Entry 34) was the wrong object.

Contestants, all scored on held-out halves, nothing seeing the scoring half:

    A   0.13                                  paper 1 today
    B   rider constant (fitted)               rider
    B'  k * s50                               rider, predictive (Danilo)
    B'' k / s50                               rider, predictive (Danilo)
    C   delta(s_bar)                          route mean grade (Entry 34)
    D   C + 1/2 delta''(s_bar) Var(s)         route mean AND dispersion
    F   a + b * phi                           rider x route
    G   k / s_bar                             route only, one constant
    E   sum occ(s_i) I t_i / (beta h_minus)   the cell integral: the ceiling

Split-half is chronological odd/even (deterministic, no RNG). s50 and the sigmoid
width come from Entry 44's fits, themselves fitted on half 0, so there is no leak.

Output: data/results/e45_ridelevel.csv (per ride) + console scoreboard.
Run: python3 src/harness/e45_ridelevel.py       (E45_SMOKE=1 for a subset)
"""

from __future__ import annotations

import csv
import math
import os
import sys
from typing import Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import is_finite
from bicycling_energy_model.engines import G as GRAV
from bicycling_energy_model.jsfmt import to_fixed

from e44_scurve import (CELL, GRADE_EDGES, KEFF, bin_of, cells_of_ride,
                        corpus_rides, flat_power, sigmoid)
from skc_compare import FROZEN, RESULTS, eps_cells, med_of, sign_p

SMOKE = bool(os.environ.get("E45_SMOKE"))
NG = len(GRADE_EDGES)
REAL_GATE = 0.03            # ride qualifies if drop-weighted mean descent grade >= 3%
EPS0 = 0.13                 # contestant A
# Which quantity the contest predicts. "ledger" = the exact unclamped identity
# E_desc/(beta*h); "paper" = paper 1's PUBLISHED deficit, the clamped
# eps_coast - eps_bal from eps_cells. They differ by ~0.12 (pooled median 0.253
# vs 0.13) because eps_cells clamps eps_coast per cell. Any constant that is to
# REPLACE eps_0 in the article must be fitted on "paper" — fitting on "ledger"
# and shipping the number would be off by that offset.
TARGET = os.environ.get("E45_TARGET", "ledger")


def load_fits() -> dict[str, tuple[float, float]]:
    """(s50, width) per group, both as FRACTIONS, from Entry 44 (fitted on half 0)."""
    path = os.path.join(RESULTS, "e44_scurve_fits.csv")
    out: dict[str, tuple[float, float]] = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            g = r["group"].strip('"')
            try:
                out[g] = (float(r["s50_pct"]) / 100, float(r["s_width_pct"]) / 100)
            except ValueError:
                continue
    return out


def delta_of_grade(s: float, v: float, m: float, i_flat: float,
                   s50: float, w: float) -> float:
    """The cell-level curve: delta(s) = occ(s) * I * k_eff / (m g s v)."""
    if s <= 0 or v <= 0 or m <= 0:
        return float("nan")
    return sigmoid(s, s50, w) * i_flat * KEFF / (m * GRAV * s * v)


def main() -> None:
    print("Entry 45 — ride-level summary contest" + ("  [E45_SMOKE]" if SMOKE else ""))
    fits = load_fits()

    rows: list[dict] = []
    seen: dict[str, int] = {}
    for group, pts, mass in corpus_rides():
        idx = seen.get(group, 0)
        seen[group] = idx + 1
        if SMOKE and idx >= 30:
            continue
        if group not in fits:
            continue
        cells = cells_of_ride(pts)
        if not cells:
            continue
        p_flat, i_flat = flat_power(cells)
        if not (is_finite(i_flat) and i_flat > 0):
            continue
        tb = [0.0] * NG
        hb = [0.0] * NG
        h_m = x_m = e_m = 0.0
        vs = vt = 0.0
        sh: list[tuple[float, float]] = []       # (grade, drop) for the moments
        for c in cells:
            if c["s"] >= 0 or c["t"] <= 0 or not is_finite(c["v"]):
                continue
            s = -c["s"]
            gi = bin_of(s, GRADE_EDGES)
            tb[gi] += c["t"]
            hb[gi] += s * CELL
            h_m += s * CELL
            x_m += CELL
            e_m += c["e"]
            vs += c["v"] * c["t"]
            vt += c["t"]
            sh.append((s, s * CELL))
        if h_m < 50 or x_m <= 0 or vt <= 0:
            continue
        s_bar = h_m / x_m
        if s_bar < REAL_GATE:                     # paper 1's real-descent gate
            continue
        v_bar = vs / vt
        beta = mass * GRAV / KEFF
        d_meas_ledger = e_m / (beta * h_m)
        var_s = sum(w * (s - s_bar) ** 2 for s, w in sh) / h_m
        s50, w50 = fits[group]
        phi = sum(w for s, w in sh if s < s50) / h_m
        eb = eps_cells(pts, {**FROZEN, "m": mass})
        d_paper = ((eb["epsCoast"] - eb["epsBal"])
                   if eb and eb.get("Hd", 0) >= 1 and eb.get("sbar", 0) >= 0.03
                   else float("nan"))
        if TARGET == "paper" and not is_finite(d_paper):
            continue
        rows.append({"group": group, "half": idx % 2, "s_bar": s_bar, "var_s": var_s,
                     "d_paper": d_paper,
                     "v_bar": v_bar, "m": mass, "i_flat": i_flat, "phi": phi,
                     "h_minus": h_m, "d_meas_ledger": d_meas_ledger,
                     "tb": tb, "hb": hb})

    for r in rows:                      # the active target
        r["d_meas"] = r["d_meas_ledger"] if TARGET == "ledger" else r["d_paper"]
    rows = [r for r in rows if is_finite(r["d_meas"])]
    print(f"  TARGET = {TARGET}"
          + ("  (exact unclamped ledger identity)" if TARGET == "ledger"
             else "  (paper 1's published clamped eps_coast - eps_bal)"))
    groups = sorted({r["group"] for r in rows},
                    key=lambda g: (not g.startswith("D6"), g))
    print(f"  {len(rows)} rides qualify (mean descent grade >= 3%)\n")

    # ---- fit every constant on the FIT half only ----
    fit = [r for r in rows if r["half"] == 0]
    out = [r for r in rows if r["half"] == 1]
    if not fit or not out:
        print("  not enough rides")
        return

    # global constants
    k_bprime = med_of([r["d_meas"] / (fits[r["group"]][0]) for r in fit
                       if fits[r["group"]][0] > 0])          # B'  delta = k * s50
    k_bsec = med_of([r["d_meas"] * fits[r["group"]][0] for r in fit])   # B'' delta = k / s50
    k_g = med_of([r["d_meas"] * r["s_bar"] for r in fit])               # G   delta = k / s_bar
    # G2: the same model in ENERGY coordinates. beta*delta*h_minus = (beta*k)*x_minus,
    # so the deficit is a constant force c [N] over the descending distance rather
    # than a fraction of the drop. G fixes k (dimensionless -> the charge scales
    # with mass); G2 fixes c (newtons -> it does not). Physically a residual pedal
    # force should not care much about rider mass, so G2 is the better-motivated
    # parameterisation and this decides between them.
    c_g2 = med_of([r["d_meas"] * r["s_bar"] * r["m"] * GRAV / KEFF for r in fit])
    # G3: Danilo's S-curve rationale. k/s_bar has no upper bound, but the physical
    # limits are known at BOTH ends: as s_bar -> 0 measured recovery -> 0 while
    # eps_coast -> 1, so delta -> 1; as s_bar grows riders coast and delta -> 0.
    # A sigmoid in mean grade has exactly those limits and cannot diverge.
    # Two global parameters, no rider parameter. Grid-searched on the fit half.
    best3 = (float("nan"), float("nan"), float("inf"))
    for a3 in [0.005 + i * 0.0005 for i in range(0, 121)]:      # midpoint 0.5-6.5%
        for b3 in [0.002 + i * 0.0005 for i in range(0, 60)]:   # width 0.2-3.2%
            e = sum(abs(sigmoid(r["s_bar"], a3, b3) - r["d_meas"]) for r in fit)
            if e < best3[2]:
                best3 = (a3, b3, e)
    a_g3, b_g3, _ = best3
    # F: least squares a + b*phi on the fit half
    n = len(fit)
    mx = sum(r["phi"] for r in fit) / n
    my = sum(r["d_meas"] for r in fit) / n
    sxx = sum((r["phi"] - mx) ** 2 for r in fit)
    sxy = sum((r["phi"] - mx) * (r["d_meas"] - my) for r in fit)
    b_f = sxy / sxx if sxx > 0 else 0.0
    a_f = my - b_f * mx
    # A': the BEST single universal constant, fitted on the fit half. This is the
    # honest floor, and A = 0.13 is not: the target here is the unclamped ledger
    # identity E_desc/(beta*h), which runs ~0.12 above paper 1's clamped
    # eps_coast - eps_bal (pooled median 0.253 vs 0.13). Every fitted contestant
    # absorbs that definitional offset for free; the frozen 0.13 cannot, so
    # scoring against it alone would credit the structured forms for an offset
    # rather than for structure. A is still reported, flagged.
    k_aprime = med_of([r["d_meas"] for r in fit])
    # B: per-rider constant
    b_rider = {g: med_of([r["d_meas"] for r in fit if r["group"] == g]) for g in groups}
    # per-rider I_flat from the fit half
    i_rider = {g: med_of([r["i_flat"] for r in fit if r["group"] == g]) for g in groups}

    print(f"  fitted on {len(fit)} rides:  k(B') = {to_fixed(k_bprime, 3)}"
          f" · k(B'') = {to_fixed(k_bsec, 4)} · k(G) = {to_fixed(k_g, 4)}"
          f" · F: delta = {to_fixed(a_f, 3)} + {to_fixed(b_f, 3)}*phi")

    def predict(r: dict, name: str) -> float:
        g = r["group"]
        s50, w50 = fits[g]
        i_f = i_rider.get(g, r["i_flat"])
        if name == "A":
            return EPS0
        if name == "A'":
            return k_aprime
        if name == "B":
            return b_rider.get(g, float("nan"))
        if name == "B'":
            return k_bprime * s50
        if name == "B''":
            return k_bsec / s50 if s50 > 0 else float("nan")
        if name == "C":
            return delta_of_grade(r["s_bar"], r["v_bar"], r["m"], i_f, s50, w50)
        if name == "D":
            h = max(1e-4, 0.1 * r["s_bar"])
            f0 = delta_of_grade(r["s_bar"], r["v_bar"], r["m"], i_f, s50, w50)
            fp = delta_of_grade(r["s_bar"] + h, r["v_bar"], r["m"], i_f, s50, w50)
            fm = delta_of_grade(r["s_bar"] - h, r["v_bar"], r["m"], i_f, s50, w50)
            if not all(is_finite(x) for x in (f0, fp, fm)):
                return float("nan")
            return f0 + 0.5 * ((fp - 2 * f0 + fm) / (h * h)) * r["var_s"]
        if name == "F":
            return a_f + b_f * r["phi"]
        if name == "G":
            return k_g / r["s_bar"] if r["s_bar"] > 0 else float("nan")
        if name == "G3":
            return sigmoid(r["s_bar"], a_g3, b_g3)
        if name == "G2":
            beta = r["m"] * GRAV / KEFF
            return c_g2 / (beta * r["s_bar"]) if r["s_bar"] > 0 else float("nan")
        if name == "E":
            beta = r["m"] * GRAV / KEFF
            tot = 0.0
            for i in range(NG):
                if r["tb"][i] <= 0 or r["hb"][i] <= 0:
                    continue
                s_i = r["hb"][i] / (r["tb"][i] * r["v_bar"]) if r["v_bar"] > 0 else 0.0
                s_i = s_i if s_i > 0 else r["s_bar"]
                tot += sigmoid(s_i, s50, w50) * i_f * r["tb"][i]
            return tot / (beta * r["h_minus"])
        return float("nan")

    NAMES = ["A", "A'", "B", "B'", "B''", "C", "D", "F", "G", "G2", "G3", "E"]
    LABEL = {"A": "A  0.13 (off-target)", "A'": "A' best constant", "B": "B  rider constant",
             "B'": "B' k*s50", "B''": "B\" k/s50", "C": "C  delta(s_bar)",
             "D": "D  + Jensen", "F": "F  a+b*phi", "G": "G  k/s_bar", "G2": "G2 force c/(b*s)", "G3": "G3 sigmoid(s_bar)",
             "E": "E  cell integral"}

    print("\nHELD-OUT median |delta_pred - delta_meas|  (lower is better; "
          f"n = {len(out)} rides)\n")
    hdr = "estimator".ljust(20) + "pooled".rjust(9)
    for g in groups:
        hdr += g.replace("D6-user_", "u").rjust(8)
    print(hdr)
    beat_A = {nm: 0 for nm in NAMES}
    pooled = {}
    for nm in NAMES:
        errs = [abs(predict(r, nm) - r["d_meas"]) for r in out
                if is_finite(predict(r, nm))]
        pooled[nm] = med_of(errs)
        line = LABEL[nm].ljust(20) + to_fixed(pooled[nm], 4).rjust(9)
        for g in groups:
            sub = [r for r in out if r["group"] == g]
            e = [abs(predict(r, nm) - r["d_meas"]) for r in sub if is_finite(predict(r, nm))]
            ea = [abs(k_aprime - r["d_meas"]) for r in sub]
            v = med_of(e)
            if is_finite(v) and is_finite(med_of(ea)) and v < med_of(ea):
                beat_A[nm] += 1
            line += (to_fixed(v, 3) if is_finite(v) else "—").rjust(8)
        print(line)
    print("\nbeats A' (the best single constant) on how many of the "
          f"{len(groups)} corpora:")
    for nm in NAMES:
        if nm in ("A", "A'"):
            continue
        print(f"  {LABEL[nm].ljust(20)} {beat_A[nm]}/{len(groups)}"
              + ("   <- registered threshold met" if nm == "G" and beat_A[nm] >= 7 else ""))

    # ---- complexity-adjusted comparison ----
    # Fitted-parameter counts. INPUT counts are deliberately NOT added in: only
    # fitted quantities can overfit, so only they belong in a BIC penalty.
    # Reading a measured s_bar costs data availability, not degrees of freedom.
    NPAR = {"A": 0, "A'": 1, "B": 9, "B'": 10, "B''": 10,
            "C": 18, "D": 18, "F": 11, "G": 1, "G2": 1, "G3": 2, "E": 18}
    print("\ncomplexity-adjusted: BIC on the FIT half (Laplace likelihood, which is the")
    print("one the median/MAE metric implies), and a paired sign test on the HELD-OUT half.")
    print("\n" + "estimator".ljust(20) + "k".rjust(4) + "fit MAE".rjust(10)
          + "dBIC vs A'".rjust(12) + "dAIC vs A'".rjust(12) + "held-out".rjust(10)
          + "vs A' (wins/n)".rjust(16) + "p".rjust(9))
    nfit = len(fit)
    bic = {}
    aic = {}          # same -2logL, flat 2k penalty (Danilo, post-registration)
    for nm in NAMES:
        e = [abs(predict(r, nm) - r["d_meas"]) for r in fit if is_finite(predict(r, nm))]
        if not e:
            continue
        mae = sum(e) / len(e)
        # Laplace: -2logL = 2n ln(2*MAE) + 2n ; the 2n cancels in a difference
        bic[nm] = 2 * nfit * math.log(2 * mae) + NPAR[nm] * math.log(nfit)
        aic[nm] = 2 * nfit * math.log(2 * mae) + 2 * NPAR[nm]
    base = bic.get("A'")
    for nm in NAMES:
        if nm not in bic:
            continue
        e = [abs(predict(r, nm) - r["d_meas"]) for r in fit if is_finite(predict(r, nm))]
        mae = sum(e) / len(e)
        w = l = 0
        for r in out:
            pv, av = predict(r, nm), predict(r, "A'")
            if not (is_finite(pv) and is_finite(av)):
                continue
            a, b = abs(pv - r["d_meas"]), abs(av - r["d_meas"])
            if a < b:
                w += 1
            elif a > b:
                l += 1
        db = bic[nm] - base
        da = aic[nm] - aic["A'"]
        mark = "" if nm in ("A", "A'") else ("  better" if db < -10 else
                                             "  worse" if db > 10 else "  ~tie")
        print(LABEL[nm].ljust(20) + str(NPAR[nm]).rjust(4) + to_fixed(mae, 4).rjust(10)
              + (to_fixed(db, 1) if nm != "A'" else "—").rjust(12)
              + (to_fixed(da, 1) if nm != "A'" else "—").rjust(12)
              + to_fixed(pooled[nm], 4).rjust(10)
              + f"{w}/{w + l}".rjust(16) + to_fixed(sign_p(w, l), 4).rjust(9) + mark)
    print("  (dBIC < -10 = decisive support over the pooled constant; > +10 = decisively worse.")
    print("   dAIC is the same quantity under a flat 2k penalty instead of k*ln(n); where the")
    print("   two disagree, the extra parameter is worth having only under the weaker penalty.)")
    print("   The sign test asks only whether the held-out win rate is real, ignoring cost.)")

    order = sorted((nm for nm in NAMES if is_finite(pooled[nm])), key=lambda nm: pooled[nm])
    print("\npooled ranking (best first): "
          + " < ".join(f"{nm} {to_fixed(pooled[nm], 4)}" for nm in order))

    cols = ["group", "half", "s_bar", "var_s", "v_bar", "m", "i_flat", "phi",
            "h_minus", "d_meas", "d_meas_ledger", "d_paper"]
    dest = os.path.join(RESULTS,
                        f"e45_ridelevel.{TARGET}{'.SMOKE' if SMOKE else ''}.csv")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(",".join(cols + NAMES) + "\n")
        for r in rows:
            vals = [(f'"{r[c]}"' if isinstance(r[c], str)
                     else to_fixed(r[c], 5) if is_finite(r[c]) else "") for c in cols]
            vals += [to_fixed(predict(r, nm), 5) if is_finite(predict(r, nm)) else ""
                     for nm in NAMES]
            fh.write(",".join(vals) + "\n")
    print(f"\nwrote {os.path.basename(dest)} ({len(rows)} rides)")


if __name__ == "__main__":
    main()
