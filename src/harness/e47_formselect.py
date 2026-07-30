#!/usr/bin/env python3
"""Entry 47 — which deficit form? Two selections by BIC on D1 u D2.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 47) before any calibration-side
result was inspected. Two selections, run separately:

    eps_d(P_a,g)   argmin_delta BIC over F3^delta(D1 u D2, P_a,g)
    eps_d(P_f,r)   argmin_delta BIC over F3^delta(D1 u D2, P_a,g . P_f,r(m,Crr,CdA))

Contestants (delta is the coasting deficit subtracted from the coasting limit):

    eps0_frozen   delta = 0.13                    0 free parameters
    eps0_fit      delta = c                       1
    eps2          delta = k / s_bar               1
    eps3          delta = a + b * phi             2

eps1 (rider constant) is dropped: with two riders on the calibration side it is
a two-parameter restatement of the corpus label.

sigma = parse + power + >= 3 km + s_bar >= 3%. Registered |O| = 48 (D1 22, D2 26).

INSTRUMENT. BIC under a Laplace likelihood on the signed Delta% energy residuals.
Laplace because every published statistic here is a median; BIC because n ~ 48
makes a held-out split too weak to separate 1- from 2-parameter forms. MLE under
Laplace is argmin sum|r|, so each form's parameters are fitted by minimising the
same quantity the BIC then scores -- a proper BIC, not a mixed objective.
DeltaBIC < 2 is NOT a win: the fewest-parameter form takes it.

TARGET DISCIPLINE. Every contestant is fitted to the CLAMPED convention -- the
per-cell min(1, (alpha/beta)/s) that eps_geom and eps_cells both apply -- which is
paper 1's published quantity. The unclamped ledger identity is a different number
(pooled median 0.253 vs 0.13; k = 0.0099 vs 0.0051) and mixing them produced four
wrong readings across Entries 43-45. Whichever quantity is measured, the constant
must be fitted to that same quantity.

Two fits are reported per form, because they answer different questions:
  energy-space   parameters minimise sum|Delta%|   -- what the law needs (primary)
  deficit-space  parameters fit eps_coast - eps_bal -- how eps_0 = 0.13 was derived

Output: data/results/e47_formselect.csv (per ride, both arms) + console scoreboard.
Run: python3 src/harness/e47_formselect.py      (E47_SMOKE=1 for a subset)
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import (approximate, build_profile, deadband,
                                    empirical_kj, extract_regime_powers,
                                    is_finite, overall_mean_power,
                                    resample_profile)
from bicycling_energy_model.engines import G, flat_eq_speed
from bicycling_energy_model.jsfmt import to_fixed

from perride_invert import (CLIMB_THR, DESC_THR, ENGINE_DX, KEFF,
                            RESULTS, RHO, TAU_SMOOTH, VMAX, VSTART,
                            find_segments, geo_summary, headwind_ms,
                            invert_physics, iter_corpus, seg_integrals)
from e44_scurve import corpus_rides
from skc_compare import boot_ci, eps_cells, med_of

SMOKE = bool(os.environ.get("E47_SMOKE"))
REAL_GATE = 0.03                 # sigma: paper 1's real-descent gate
EPS0_PUB = 0.13                  # the published constant, contestant eps0_frozen
DX = 30.0                        # the cell size eps_geom uses
# The frozen protocol as each corpus's PUBLISHED harness applies it:
# longoes_frozen.py uses {**FROZEN, "m": logged}, censo_compare.py the generic
# 78 kg (D2 assumes a generic rider). Mass is therefore assumed-per-ride on D1
# and assumed-global on D2 -- copied rather than idealised, so this arm is
# comparable to Table 2's blind block and Table 3's D2 column.
FROZEN = {"Crr": 0.008, "CdA": 0.40, "rho": RHO, "keff": KEFF,
          "wind": 0.0, "vmax": VMAX, "vstart": VSTART}
M_GENERIC = 78.0
GROUP = {"longoes": "D1", "censo": "D2"}
# group -> the ANCHOR_M key invert_physics falls back on. D6 has no anchor and
# never needs one: corpus_rides() supplies a per-rider inverted mass.
ANCHOR_KEY = {"D1": "longoes", "D2": "censo", "D3": "ppaz", "D4": "jaam",
              "D5": "danlessa"}


def load_s50() -> dict[str, float]:
    """Entry 44's sigmoid midpoints, as fractions. Fitted on half 0 -> no leak."""
    import csv as _csv
    out: dict[str, float] = {}
    with open(os.path.join(RESULTS, "e44_scurve_fits.csv"), encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            try:
                out[r["group"].strip('"')] = float(r["s50_pct"]) / 100
            except ValueError:
                continue
    return out


S50 = load_s50()


# ----------------------------------------------------------------- geometry

def descent_summary(prof: dict, ab: float, s50: float) -> dict | None:
    """eps_coast, s_bar and phi on eps_geom's OWN cells.

    Mirrors engines.eps_geom step for step (same 30 m cells, same interpolating
    walker, same per-cell min(1, ab/s) clamp) and returns the pieces instead of
    the single number, so the deficit that gets subtracted and the predictors
    that model it are computed on one footing. eps_geom subtracts EPS0 from the
    value this returns as `eps_coast`.
    """
    px, ph = prof["x"], prof["h"]
    x0 = px[0]
    nc = math.floor((px[len(px) - 1] - x0) / DX)
    if nc < 2:
        return None
    j = 0

    def h_at(d: float) -> float:
        nonlocal j
        while j < len(px) - 2 and px[j + 1] < d:
            j += 1
        seg = px[j + 1] - px[j]
        f = (d - px[j]) / seg if seg > 1e-9 else 0.0
        return ph[j] * (1 - f) + ph[j + 1] * f

    cellH = [h_at(x0 + k * DX) for k in range(nc + 1)]
    Hd = epsW = xd = phiW = 0.0
    for k in range(nc):
        dh = cellH[k + 1] - cellH[k]
        if dh < 0:
            drop = -dh
            s = drop / DX
            Hd += drop
            xd += DX
            epsW += drop * min(1.0, ab / s)
            if s < s50:
                phiW += drop
    if Hd < 1 or xd <= 0:
        return None
    return {"eps_coast": epsW / Hd, "s_bar": Hd / xd, "phi": phiW / Hd, "Hd": Hd}


# ------------------------------------------------------------- contestants
# Each returns delta (the deficit) for one ride, given its predictors.

def d_frozen(r: dict, q: tuple) -> float:
    return EPS0_PUB


def d_const(r: dict, q: tuple) -> float:
    return q[0]


def d_grade(r: dict, q: tuple) -> float:
    return q[0] / r["s_bar"]


def d_phi(r: dict, q: tuple) -> float:
    return q[0] + q[1] * r["phi"]


FORMS = [
    ("eps0_frozen", "delta = 0.13",       d_frozen, 0, []),
    ("eps0_fit",    "delta = c",          d_const,  1, [(0.0, 0.60)]),
    ("eps2",        "delta = k / s_bar",  d_grade,  1, [(0.0, 0.05)]),
    ("eps3",        "delta = a + b*phi",  d_phi,    2, [(-0.30, 0.60), (-1.0, 1.0)]),
]


# ------------------------------------------------------------------ fitting

def residuals(rows: list[dict], fn, q: tuple, arm: str) -> list[float]:
    """Signed Delta% of F3 against measured energy, for every ride."""
    out = []
    for r in rows:
        eps = r["eps_coast"] - fn(r, q)
        e_kj = (r[arm + "_E0"] + (r[arm + "_E1"] - r[arm + "_E0"]) * eps) / 1000
        out.append(100.0 * (e_kj - r["emp"]) / r["emp"])
    return out


def dev_residuals(rows: list[dict], fn, q: tuple, arm: str) -> list[float]:
    """Residuals in DEFICIT space: measured (eps_coast - eps_bal) minus predicted."""
    return [r[arm + "_dmeas"] - fn(r, q) for r in rows
            if is_finite(r.get(arm + "_dmeas", float("nan")))]


def fit(rows: list[dict], fn, npar: int, bounds: list, arm: str,
        space: str = "energy") -> tuple:
    """argmin sum|residual| by deterministic nested grid refinement.

    No RNG and no gradient: the objective is piecewise linear in the parameters
    (Delta% is exactly linear in eps, and eps is linear in delta for all four
    forms), so a refining grid finds the optimum and gives the same answer on
    every machine and every re-run.
    """
    resid = residuals if space == "energy" else dev_residuals
    if npar == 0:
        return (), sum(abs(v) for v in resid(rows, fn, (), arm))
    lo = [b[0] for b in bounds]
    hi = [b[1] for b in bounds]
    n_grid = 240 if npar == 1 else 60
    best_q, best_v = None, float("inf")
    for _ in range(4):                              # 4 refinement passes
        steps = [(hi[i] - lo[i]) / n_grid for i in range(npar)]
        if npar == 1:
            cand = [(lo[0] + i * steps[0],) for i in range(n_grid + 1)]
        else:
            cand = [(lo[0] + i * steps[0], lo[1] + j * steps[1])
                    for i in range(n_grid + 1) for j in range(n_grid + 1)]
        for q in cand:
            v = sum(abs(x) for x in resid(rows, fn, q, arm))
            if v < best_v - 1e-12:
                best_q, best_v = q, v
        # re-clamp to the ORIGINAL bounds: without this the refinement walks
        # outside them whenever the optimum sits on an edge, and delta < 0 is
        # not a small numerical liberty -- it means eps_d > eps_coast, i.e. the
        # rider recovering more than free-wheeling would give.
        lo = [max(bounds[i][0], best_q[i] - steps[i]) for i in range(npar)]
        hi = [min(bounds[i][1], best_q[i] + steps[i]) for i in range(npar)]
    return best_q, best_v


def bic(rows: list[dict], fn, q: tuple, npar: int, arm: str) -> tuple:
    """BIC under a Laplace likelihood on the signed Delta% residuals.

    b_hat = mean|r| is the Laplace MLE scale; logL = -n ln(2 b_hat) - n, so
    BIC = -2 logL + k ln n = 2n ln(2 b_hat) + 2n + k ln n. The 2n term is common
    to every model and cancels in DeltaBIC, but it is kept so the printed BIC is
    a real BIC rather than a shifted one.
    """
    r = residuals(rows, fn, q, arm)
    n = len(r)
    b = sum(abs(v) for v in r) / n
    if not (b > 0):
        return float("nan"), float("nan"), n
    return 2 * n * math.log(2 * b) + 2 * n + npar * math.log(n), b, n


def aic_of(bic_val: float, npar: int, n: int) -> float:
    """AIC from BIC: both are -2logL + penalty, so they differ only in it.

    Added at Danilo's request AFTER the registration, which named BIC. It is
    reported beside BIC and does NOT drive the registered selection — but where
    the two disagree, that is stated, because the disagreement is a fact about
    how much evidence there is, not a detail. At n = 48, ln(n) = 3.87 against
    AIC's flat 2, so BIC charges nearly twice as much per parameter.
    """
    return bic_val - npar * math.log(n) + 2 * npar


# --------------------------------------------------------------- ride build

FUNNEL: dict[str, int] = {}
# s_bar for EVERY ride that reaches the gate, under both definitions, so the
# comparison with Entry 45's count is two-sided: a check that only looks at
# survivors cannot see the rides the other gate would have kept.
SBAR_ALL: list[tuple[str, float, float]] = []


def drop(stage: str) -> None:
    FUNNEL[stage] = FUNNEL.get(stage, 0) + 1


def build_rows() -> list[dict]:
    rows: list[dict] = []
    for corpus in ("longoes", "censo"):
        seen = 0
        for pts, label, date, path, m_logged in iter_corpus(corpus):
            if SMOKE and seen >= 25:
                break
            seen += 1
            try:
                r = one_ride(pts, label, GROUP[corpus], date, path, m_logged)
            except Exception:
                r = None
            if r is not None:
                rows.append(r)
    # chronological split-half, per corpus: odd/even on date order (Entry 44's rule)
    for g in sorted({r["group"] for r in rows}):
        sub = sorted([r for r in rows if r["group"] == g],
                     key=lambda r: (r["date"] or "", r["ride"]))
        for i, r in enumerate(sub):
            r["half"] = i % 2
    return rows


def build_rows_all() -> list[dict]:
    """D3-D6 for the in-sample eps_{d,all} arm.

    Uses corpus_rides() -- the same iterator Entries 44/45 used, which supplies
    D6's per-rider inverted mass at runtime rather than a frozen literal. It
    carries no date or file path, so wind is 0 for every ride here; that is also
    what D6 requires, since the weather fetch would key on centroids derived from
    third-party riders' home addresses. This arm is therefore NOT Table 5's
    protocol and is reported as in-sample and separate, never as a headline.
    """
    rows: list[dict] = []
    seen: dict[str, int] = {}
    for group, pts, mass in corpus_rides():
        if group in ("D1", "D2"):
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if SMOKE and i >= 15:
            continue
        if group not in S50:
            continue
        try:
            r = one_ride(pts, f"{group}#{i}", group, None, None, mass)
        except Exception:
            r = None
        if r is not None:
            rows.append(r)
    for g in sorted({r["group"] for r in rows}):
        sub = sorted([r for r in rows if r["group"] == g], key=lambda r: r["ride"])
        for i, r in enumerate(sub):
            r["half"] = i % 2
    return rows


def one_ride(pts, label, group, date, path, m_logged) -> dict | None:
    corpus = ANCHOR_KEY.get(group)
    drop("0 seen")
    emp = empirical_kj(pts)
    if not (is_finite(emp) and emp > 0):
        drop("1 no power")
        return None
    phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile(phys, ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        drop("2 under 3 km")
        return None
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}

    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    if not (is_finite(flat) and flat > 0):
        drop("3 no flat power")
        return None
    p_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat

    try:
        geo = geo_summary(path) if path else None
    except Exception:
        geo = None
    wind, _ = headwind_ms(geo, date)

    row = {"corpus": corpus or group, "group": group, "ride": label, "date": date or "",
           "emp": emp, "half": 0}

    # --- the two parameter arms
    m_ag = m_logged if (m_logged is not None and is_finite(m_logged)) else M_GENERIC
    arms = {"ag": {**FROZEN, "m": m_ag}}
    row["m_ag"] = m_ag
    climbs_raw, flats_raw = find_segments(prof)
    wb_climbs = [s for s in (seg_integrals(pts, c, wind) for c in climbs_raw) if s and s["ok"]]
    wb_flats = [s for s in (seg_integrals(pts, f, wind) for f in flats_raw) if s and s["ok"]]
    inv = invert_physics(prof, wb_climbs, wb_flats, corpus, m_logged)
    if inv is None:
        drop("4 inversion failed")
        return None
    arms["fr"] = {"m": inv["m_hat"], "Crr": inv["crr_hat"], "CdA": inv["cda_hat"],
                  "rho": RHO, "keff": KEFF, "wind": wind, "vmax": VMAX,
                  "vstart": VSTART}
    row["m_hat"] = inv["m_hat"]
    row["m_src"] = inv["m_src"]
    row["crr_hat"] = inv["crr_hat"]
    row["cda_hat"] = inv["cda_hat"]
    row["wind_ms"] = wind

    opt = {"climbAeroMode": "zero", "climbThr": CLIMB_THR,
           "descThr": DESC_THR, "climbPower": p_climb}

    # both s_bar definitions, recorded BEFORE any gate
    p_ag = arms["ag"]
    vf_ag = flat_eq_speed(flat, p_ag)
    mg_ag = p_ag["m"] * G
    ab_ag = ((p_ag["Crr"] * mg_ag + 0.5 * p_ag["rho"] * p_ag["CdA"]
              * (vf_ag + p_ag["wind"]) * abs(vf_ag + p_ag["wind"])) / p_ag["keff"]) \
        / (mg_ag / p_ag["keff"])
    d_pre = descent_summary(prof, ab_ag, S50[group])
    eb_pre = eps_cells(pts, p_ag)
    SBAR_ALL.append((group,
                     d_pre["s_bar"] if d_pre else float("nan"),
                     eb_pre.get("sbar", float("nan")) if eb_pre else float("nan")))
    keep = False
    for arm, p in arms.items():
        vf = flat_eq_speed(flat, p)
        mg = p["m"] * G
        beta = mg / p["keff"]
        aero_spd = vf + p["wind"]
        alpha = (p["Crr"] * mg + 0.5 * p["rho"] * p["CdA"]
                 * aero_spd * abs(aero_spd)) / p["keff"]
        d = descent_summary(prof, alpha / beta, S50[group])
        if d is None:
            if arm == "ag":
                drop("5 no descent cells")
            continue
        # F3 = the smoothed profile under climb-aero 'zero'. E is EXACTLY linear
        # in eps (recov = -beta*eps*h_minus), so two evaluations pin the family.
        e0 = approximate(profS, p, vf, 0.0, opt)["E"]
        e1 = approximate(profS, p, vf, 1.0, opt)["E"]
        # GATE: the two-point shortcut is only valid because approximate() is
        # exactly linear in eps (recov = -beta*eps*h_minus and nothing else
        # reads eps). Check it on every ride rather than trust the reading.
        mid = approximate(profS, p, vf, 0.5, opt)["E"]
        if abs(mid - 0.5 * (e0 + e1)) > 1e-6 * max(1.0, abs(mid)):
            raise AssertionError(f"approximate() not linear in eps on {label}")
        eb = eps_cells(pts, p)
        row[arm + "_sbar_cells"] = eb.get("sbar", float("nan")) if eb else float("nan")
        dmeas = ((eb["epsCoast"] - eb["epsBal"])
                 if eb and eb.get("Hd", 0) >= 1 and eb.get("sbar", 0) >= REAL_GATE
                 else float("nan"))
        row.update({arm + "_E0": e0, arm + "_E1": e1, arm + "_vf": vf * 3.6,
                    arm + "_Hd": d["Hd"],
                    arm + "_eps_coast": d["eps_coast"], arm + "_s_bar": d["s_bar"],
                    arm + "_phi": d["phi"], arm + "_dmeas": dmeas})
        keep = True
    return row if keep else None


# ------------------------------------------------------------------ report

def arm_view(rows: list[dict], arm: str, gate: str = "cells") -> list[dict]:
    """The rides that survive sigma, flattened to the arm's predictors.

    `gate` picks which mean-descent-grade definition sigma uses:
      "cells" -- eps_cells' s_bar, what Entry 45 and every published harness
                 gate on, and what the registration's |O| = 48 was counted from
      "geom"  -- the s_bar of eps_geom's own cells, i.e. the profile the energy
                 law actually reads
    They disagree on 5 of 113 rides here, so the champion is reported under both.
    """
    out = []
    for r in rows:
        if arm + "_E0" not in r:
            continue
        sb = r[arm + "_sbar_cells"] if gate == "cells" else r[arm + "_s_bar"]
        if not (is_finite(sb) and sb >= REAL_GATE):
            continue
        q = dict(r)
        q["eps_coast"] = r[arm + "_eps_coast"]
        q["s_bar"] = r[arm + "_s_bar"]
        q["phi"] = r[arm + "_phi"]
        out.append(q)
    return out


def run_arm(rows: list[dict], arm: str, title: str,
            gate: str = "cells") -> list[dict]:
    view = arm_view(rows, arm, gate)
    n = len(view)
    per = {}
    for r in view:
        per[r["group"]] = per.get(r["group"], 0) + 1
    breakdown = ", ".join(f"{g} {per[g]}" for g in sorted(per))
    print(f"\n{'=' * 78}\n{title}   |O| = {n}   ({breakdown})\n{'=' * 78}")
    if n < 8:
        print("  too few rides to select a form.")
        return []

    results = []
    for name, expr, fn, npar, bounds in FORMS:
        q, _ = fit(view, fn, npar, bounds, arm)
        B, b_hat, _ = bic(view, fn, q, npar, arm)
        res = residuals(view, fn, q, arm)
        absr = [abs(v) for v in res]
        med_a, med_s = med_of(absr), med_of(res)
        ci_a, ci_s = boot_ci(absr, 42), boot_ci(res, 43)
        # held-out: fit on one half, score the other, both ways
        ho: list[float] = []
        for h in (0, 1):
            tr = [r for r in view if r["half"] != h]
            te = [r for r in view if r["half"] == h]
            if len(tr) < 6 or not te:
                continue
            qh, _ = fit(tr, fn, npar, bounds, arm) if npar else ((), 0.0)
            ho += [abs(v) for v in residuals(te, fn, qh, arm)]
        # deficit-space fit, for comparison with how eps_0 was originally derived
        dv = [r for r in view if is_finite(r.get(arm + "_dmeas", float("nan")))]
        qd, _ = fit(dv, fn, npar, bounds, arm, space="deficit") if (npar and dv) else ((), 0.0)
        med_d = med_of([abs(v) for v in residuals(view, fn, qd, arm)]) if dv else float("nan")
        results.append({"name": name, "expr": expr, "npar": npar, "q": q,
                        "bic": B, "aic": aic_of(B, npar, n), "b_hat": b_hat, "med_abs": med_a, "ci_a": ci_a,
                        "med_sgn": med_s, "ci_s": ci_s,
                        "held": med_of(ho) if ho else float("nan"),
                        "qd": qd, "med_abs_dev": med_d})

    best = min(r["bic"] for r in results)
    for r in results:
        r["dbic"] = r["bic"] - best
    best_a = min(r["aic"] for r in results)
    for r in results:
        r["daic"] = r["aic"] - best_a

    # DeltaBIC < 2 -> the fewest-parameter form takes it
    tied = [r for r in results if r["dbic"] < 2.0]
    champ = min(tied, key=lambda r: (r["npar"], r["dbic"]))

    print(f"\n  {'form':<12} {'delta':<20} {'par':>3} {'fitted':<18} "
          f"{'BIC':>8} {'dBIC':>7} {'AIC':>8} {'dAIC':>7} {'med|D%|':>9} {'signed':>9} {'held':>7}")
    for r in sorted(results, key=lambda r: r["bic"]):
        qs = ", ".join(to_fixed(v, 4) for v in r["q"]) if r["q"] else "-"
        mark = "  <-- champion" if r is champ else ""
        print(f"  {r['name']:<12} {r['expr']:<20} {r['npar']:>3} {qs:<18} "
              f"{to_fixed(r['bic'], 1):>8} {to_fixed(r['dbic'], 1):>7} "
              f"{to_fixed(r['aic'], 1):>8} {to_fixed(r['daic'], 1):>7} "
              f"{to_fixed(r['med_abs'], 2):>9} {to_fixed(r['med_sgn'], 2):>9} "
              f"{to_fixed(r['held'], 2):>7}{mark}")
    print(f"\n  95% CIs (B = 10^4, mulberry32 seeds 42/43):")
    for r in sorted(results, key=lambda r: r["bic"]):
        print(f"    {r['name']:<12} med|D%| {to_fixed(r['med_abs'], 2)} "
              f"[{to_fixed(r['ci_a'][0], 2)}, {to_fixed(r['ci_a'][1], 2)}]  ·  "
              f"signed {to_fixed(r['med_sgn'], 2)} "
              f"[{to_fixed(r['ci_s'][0], 2)}, {to_fixed(r['ci_s'][1], 2)}]")
    print(f"\n  deficit-space fit (how eps_0 = 0.13 was originally derived):")
    for r in sorted(results, key=lambda r: r["bic"]):
        qs = ", ".join(to_fixed(v, 4) for v in r["qd"]) if r["qd"] else "-"
        print(f"    {r['name']:<12} params {qs:<20} -> med|D%| {to_fixed(r['med_abs_dev'], 2)}")

    a_tied = [r for r in results if r["daic"] < 2.0]
    a_champ = min(a_tied, key=lambda r: (r["npar"], r["daic"]))
    if a_champ["name"] != champ["name"]:
        print(f"\n  !! AIC DISAGREES: it selects {a_champ['name']} "
              f"(dAIC {to_fixed(champ['aic'] - a_champ['aic'], 2)} over the BIC champion).\n"
              f"     BIC is the registered instrument and stands; the disagreement is "
              f"reported, not resolved.")
    else:
        print(f"\n  AIC agrees: {a_champ['name']}")
    print(f"\n  CHAMPION: {champ['name']}  ({champ['expr']}"
          + (f", fitted {', '.join(to_fixed(v, 4) for v in champ['q'])}" if champ["q"] else "")
          + ")")
    if champ["dbic"] > 0:
        print(f"    won on parsimony: dBIC = {to_fixed(champ['dbic'], 1)} < 2 against "
              f"the lowest-BIC form, so the fewest parameters take it.")
    return results


def main() -> None:
    print("Entry 47 — deficit form selection on D1 u D2" + ("  [E47_SMOKE]" if SMOKE else ""))
    rows = build_rows()
    print(f"\nrides built: {len(rows)}")
    print("\nsigma funnel (why |O| is not |D|):")
    for k in sorted(FUNNEL):
        print(f"    {k:<22} {FUNNEL[k]:>4}")
    # The registration's |O| = 48 came from Entry 45, which gates on eps_cells'
    # s_bar. This harness gates on eps_geom's cells -- the profile the energy law
    # actually reads. Report the disagreement rather than adopt either silently.
    for g in ("D1", "D2"):
        sub = [t for t in SBAR_ALL if t[0] == g]
        a = sum(1 for _, x, _ in sub if is_finite(x) and x >= REAL_GATE)
        b = sum(1 for _, _, y in sub if is_finite(y) and y >= REAL_GATE)
        agree = sum(1 for _, x, y in sub
                    if is_finite(x) and is_finite(y)
                    and (x >= REAL_GATE) == (y >= REAL_GATE))
        print(f"    {g}: of {len(sub)} rides, eps_geom-cells gate keeps {a}, "
              f"eps_cells gate keeps {b}, the two agree on {agree}")

    out = []
    ARMS = (("ag", "SELECTION 1 — eps_d(P_a,g)   frozen priors"),
            ("fr", "SELECTION 2 — eps_d(P_f,r)   per-ride inverted physics"))
    for arm, title in ARMS:
        out.append((arm, run_arm(rows, arm, title, gate="cells")))

    print(f"\n{'=' * 78}\nGATE SENSITIVITY — the same two selections under eps_geom's "
          f"s_bar\n{'=' * 78}")
    print("  The registered sigma counted |O| = 48 from eps_cells' s_bar. Re-run under the\n"
          "  other definition: if the champion moves, the choice of gate is doing work and\n"
          "  must be declared; if it does not, the ambiguity is harmless.")
    for arm, title in ARMS:
        v = arm_view(rows, arm, "geom")  # noqa: F841 -- title unused here
        res = []
        for name, expr, fn, npar, bounds in FORMS:
            q, _ = fit(v, fn, npar, bounds, arm)
            B, _, _ = bic(v, fn, q, npar, arm)
            res.append({"name": name, "npar": npar, "bic": B})
        lo = min(r["bic"] for r in res)
        tied = [r for r in res if r["bic"] - lo < 2.0]
        champ = min(tied, key=lambda r: (r["npar"], r["bic"] - lo))
        print(f"    {arm}: |O| = {len(v)}  champion {champ['name']}")

    # ---- eps_{d,all}: the in-sample arm on D3-D6, run LAST and labelled
    print(f"\n{'=' * 78}\nEPS_d,all — the in-sample arm: the same contest on D3-D6"
          f"\n{'=' * 78}")
    print("  Explicitly in-sample and explicitly secondary. It answers 'what would the\n"
          "  best-configured law have been?', never 'what should ship'. Table 3's pool\n"
          "  stays the frozen-transfer number.")
    rows_all = build_rows_all()
    print(f"\n  rides built: {len(rows_all)}")
    for arm, title in ARMS:
        run_arm(rows_all, arm, "  " + title.replace("SELECTION", "EPS_d,all"),
                gate="cells")
    rows += rows_all

    name = "e47_formselect.SMOKE.csv" if SMOKE else "e47_formselect.csv"
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            cells = []
            for k in cols:
                v = r.get(k)
                if isinstance(v, str):
                    cells.append(f'"{v}"')
                elif v is not None and is_finite(v):
                    cells.append(to_fixed(v, 6))
                else:
                    cells.append("")           # absent or non-finite -> empty
            fh.write(",".join(cells) + "\n")
    print(f"\nwrote {name} ({len(rows)} rides)")


if __name__ == "__main__":
    main()
