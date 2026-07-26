#!/usr/bin/env python3
"""REGIME-DECOMPOSED closed form — Python port of the retired regime_compare.mjs
(same console report, byte-identical data/results/regime_comparison.csv).

E_new = E_flat(x₌;P₌) + E_climb(x₊;P₊) + E_descent(x₋;P₋), each component drawing
from the base law E ≈ α·x + β·(h₊ − ε·h₋) with a REGIME-SPECIFIC reference speed
(flat: flatEqSpeed(P₌); climb: v_c(P₊); descent: P₋+gravity equilibrium). Tested
against the current champion R0 (cf + 2 m deadband) and canonical on all corpora.

Two design traps (see the journal / Entry 17):
 · Trap 1 (P·t tautology): E_new is a genuine prediction ONLY because every regime
   speed is MODELLED from power+physics (flat_eq_speed, v_c, descent_eq_speed),
   never measured. Regime POWERS are fair inputs; regime TIMES/SPEEDS never enter.
 · Trap 2 (descent double-count): descent aero is paid by gravity and sits in
   (1−ε)·β·h₋; the three descent variants (R1a keeps ε; R1b/R1c drop it for explicit
   descent physics) are NEVER mixed.

Descent variants (pre-specified):
 · R1a — base-law per-edge ε clamp, aero at v_flat.
 · R1b — P₋·t₋, t₋ over the modelled descent equilibrium speed (no ε).
 · R1c — leg force-deficit held at flat cruise speed (no ε, no P₋).
 · R1d — the DEPLOYED sampasimu v2Edge (grade-local ε; Entry 18).

PRE-DECLARED PRIMARY ENDPOINT: R1a at default ±(2%/1.5%) thresholds & corpus ε rule,
med|Δ%| vs ∫P·dt on the P. Paz rides, PAIRED against R0.

  python3 src/harness/regime_compare.py      (SANITY=1 → synthetic gates only)
Output: console report + data/results/regime_comparison.csv (gitignored via data/results/*).

MODULE IS IMPORT-SAFE — importing it runs nothing and touches no file; the whole
driver lives in main(). The sibling harnesses (igc_resolution_test, goal_calibration,
scale_trio) reuse the engine by IMPORTING from here, exactly as their .mjs siblings
extract regime_compare.mjs's source blocks at run time. Three globals are MUTATED by
the engine (the .mjs reaches them through getPhysProfile/getManuf/getMinPreclamp) —
read them as MODULE ATTRIBUTES, never `from regime_compare import …`, which would
freeze the value at import time:
    regime_compare.phys_profile     (set by build_profile)
    regime_compare.FIT_MANUF        (set by parse_fit)
    regime_compare.R1D_MIN_PRECLAMP (min pre-clamp descent edge, tracked by r1d_v2_edge)

JS name → Python name (the .mjs's top-level definitions, in file order):
  G, NS, VMAX, VSTART, CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH, VSTOP, ASSUMED,
  PHYS, ZWIFT, SWEEP_CLIMB, SWEEP_DESC   → same names
  physProfile → phys_profile      FIT_MANUF → FIT_MANUF
  haversine → haversine (bem)     flatEqSpeed → flat_eq_speed (bem)
  resampleProfile → resample_profile (bem)      canonical → canonical (bem)
  approxComponents → approx_components (bem)    buildProfile → build_profile (bem wrapper)
  extractRegimePowers → extract_regime_powers (bem, stats dicts — read ["mean"])
  parseFIT → parse_fit (bem wrapper)
  ptsFromFIT → pts_from_fit (bem wrapper)       deadband → deadband (bem)
  empiricalKJ → empirical_kj (bem)              overallMeanPower → overall_mean_power (bem)
  hasPower → has_power            pushStats → push_stats (bem)  epsGeom → eps_geom (bem)
  climbBalance → climb_balance (bem)            epsCellsPz → eps_cells_pz
  ptsFromGPX → pts_from_gpx (bem)
  approxTime → approx_time (bem)  extractRegimeStats → extract_regime_stats
  descentEqSpeed → descent_eq_speed             cellHpm → cell_hpm
  clamp01 → clamp01   medOf → med_of   iqr → iqr   corrOf → corr_of   readPts → read_pts
  regimeComponents → regime_components          regimeTotals → regime_totals
  R1D_MIN_PRECLAMP → R1D_MIN_PRECLAMP           r1dV2Edge → r1d_v2_edge
  r0Champion → r0_champion        pointRegimeData → point_regime_data
  binGrades → bin_grades          pwFrom → pw_from              dPct → d_pct
  rows/sweep → rows/sweep         sweepKey → sweep_key          processRide → process_ride
  erf → erf   pFromZ → p_from_z   pairedAbs → paired_abs        f → f
"""

from __future__ import annotations

from typing import Callable

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approx_components, approx_time, canonical, climb_balance,  # noqa: F401,E402
                                    deadband, empirical_kj, env_suffix, eps_geom,
                                    extract_regime_powers, flat_eq_speed, haversine,
                                    is_finite, jsdiv, load_pts, overall_mean_power,
                                    pts_from_gpx, push_stats, resample_profile)
from bicycling_energy_model import build_profile as _bem_build_profile  # noqa: E402
from bicycling_energy_model import parse_fit as _bem_parse_fit  # noqa: E402
from bicycling_energy_model import pts_from_fit as _bem_pts_from_fit  # noqa: E402
from bicycling_energy_model.engines import G  # noqa: E402
from bicycling_energy_model.jsfmt import js_str, to_exponential, to_fixed  # noqa: E402

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
NS = 240
VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
VSTOP = 0.5 / 3.6
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}


def jgt(v: float | None, t: float) -> bool:
    """JS `v > t` with v possibly undefined (a missing manifest field): always false."""
    return v is not None and v > t


def jge(v: float | None, t: float) -> bool:
    """JS `v >= t` with v possibly undefined: always false."""
    return v is not None and v >= t


def jnum(s: str) -> float:
    """JS unary plus on an env string (+process.env.X → Number(x))."""
    t = s.strip()
    if t == "":
        return 0.0
    try:
        if t.lower().lstrip("+-").startswith("0x"):
            return float(int(t, 16))
        return float(t)
    except ValueError:
        return float("nan")


# Per-rider physics: frozen masses (Entries 12/14/16) + <RIDER>_M/_CDA/_CRR env overrides — the
# fitted-vs-assumed rerun (Entry 16's machinery): swap in each rider's Entry-15 fitted constants
# to test whether the regime model's win/loss tracks R0's bias sign (the bias-trade prediction).
PHYS = {}
for _r, _m0 in (("ppaz", 74.5), ("jaam", 101.9), ("danlessa", 74.7)):
    _U = _r.upper()
    PHYS[_r] = {
        **ASSUMED,
        "m": jnum(os.environ[f"{_U}_M"]) if os.environ.get(f"{_U}_M") else _m0,
        "CdA": jnum(os.environ[f"{_U}_CDA"]) if os.environ.get(f"{_U}_CDA") else ASSUMED["CdA"],
        "Crr": jnum(os.environ[f"{_U}_CRR"]) if os.environ.get(f"{_U}_CRR") else ASSUMED["Crr"],
    }
ZWIFT = 260
SWEEP_CLIMB = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04]
SWEEP_DESC = [-0.01, -0.015, -0.02, -0.03]

phys_profile = None   # the .mjs's `physProfile` global (set by build_profile)
FIT_MANUF = None      # file_id manufacturer, set by parse_fit per file


# ===== VERBATIM engines/instruments (haversine … readPts) — from time_compare.mjs =====
# haversine, flatEqSpeed, resampleProfile, deadband, empiricalKJ, overallMeanPower,
# epsGeom, ptsFromGPX, approxTime, canonical — plus approxComponents,
# extractRegimePowers (FULL stats dicts; read ["mean"]), pushStats, climbBalance,
# isFinite, jsdiv — are the frozen JS reference → imported from bicycling_energy_model above.
# buildProfile/parseFIT/ptsFromFIT are bicycling_energy_model too, via thin wrappers
# below that keep the phys_profile / FIT_MANUF module globals the sibling harnesses
# (igc_resolution_test, goal_calibration, scale_trio) read as module attributes.

def build_profile(dist_arr: list[float], ele_arr: list[float | None]) -> dict:
    """bem.build_profile plus the phys_profile module-global side effect the
    sibling harnesses rely on (they call this then read regime_compare.phys_profile)."""
    global phys_profile
    info = _bem_build_profile(dist_arr, ele_arr)
    phys_profile = {"x": info["x"], "h": info["h"]}
    return info


# ---- FIT parsing — bem, via wrappers that keep the FIT_MANUF module global ----

def parse_fit(buf: bytes) -> list[dict]:
    """bem.parse_fit plus the FIT_MANUF module-global side effect (the sibling
    harnesses read regime_compare.FIT_MANUF after parsing a file)."""
    global FIT_MANUF
    meta = {}
    recs = _bem_parse_fit(buf, meta)
    FIT_MANUF = meta["manufacturer"]
    return recs


def pts_from_fit(buf: bytes) -> list[dict]:
    """bem.pts_from_fit plus the FIT_MANUF module-global side effect."""
    global FIT_MANUF
    meta = {}
    pts = _bem_pts_from_fit(buf, meta)
    FIT_MANUF = meta["manufacturer"]
    return pts


def has_power(pts: list[dict]) -> bool:
    return any(q.get("power") is not None for q in pts)


def eps_cells_pz(pts: list[dict], p: dict) -> dict | None:
    """Descent 30 m cells: ε_bal AND the geometric ε_coast/s̄ in one pass."""
    if not pts or len(pts) < 2:
        return None
    mg = p["m"] * G
    beta = mg / p["keff"]
    VSTOP_L = 0.5 / 3.6
    x0 = pts[0]["x"]
    totalM = pts[len(pts) - 1]["x"] - x0
    DX = 30
    nc = math.floor(totalM / DX)
    if nc < 2:
        return None
    j = 0

    def alt_at(d: float) -> float:
        nonlocal j
        while j < len(pts) - 2 and pts[j + 1]["x"] < d:
            j += 1
        seg = pts[j + 1]["x"] - pts[j]["x"]
        f = (d - pts[j]["x"]) / seg if seg > 1e-9 else 0
        return pts[j]["alt"] * (1 - f) + pts[j + 1]["alt"] * f

    cellAlt = [alt_at(x0 + k * DX) for k in range(nc + 1)]
    cellE = [0.0] * nc
    cellVs = [0.0] * nc
    cellVt = [0.0] * nc
    for r in pts:
        k = math.floor((r["x"] - x0) / DX)
        if k < 0 or k >= nc:
            continue
        w = r.get("dt") or 1
        if r.get("power") is not None:
            cellE[k] += r["power"] * w
        if r.get("v") is not None and r["v"] >= VSTOP_L:
            cellVs[k] += r["v"] * w
            cellVt[k] += w
    sv = sw = 0.0
    for k in range(nc):
        gr = (cellAlt[k + 1] - cellAlt[k]) / DX
        if abs(gr) < 0.01 and cellVt[k] > 0:
            sv += cellVs[k]
            sw += cellVt[k]
    if not sw > 0:
        return None
    vf = sv / sw
    aeroSpd = vf + p["wind"]
    alpha = (p["Crr"] * mg + 0.5 * p["rho"] * p["CdA"] * aeroSpd * abs(aeroSpd)) / p["keff"]
    Xd = Hd = Ed = cw = 0.0
    for k in range(nc):
        dh = cellAlt[k + 1] - cellAlt[k]
        if dh < 0:
            s = -dh / DX
            Xd += DX
            Hd -= dh
            Ed += cellE[k]
            cw += min(1, alpha / (beta * s)) * (-dh)   # drop-weighted per-cell clamp
    if Hd < 1:
        return None
    return {"epsBal": (alpha * Xd - Ed) / (beta * Hd), "epsCoast": cw / Hd,
            "sbar": Hd / Xd, "vf": vf, "Hd": Hd}


# ===== NEW INSTRUMENT: per-regime moving time / distance / vertical =====
def extract_regime_stats(pts: list[dict], climb_thr: float,
                         desc_thr: float) -> dict | None:
    """Same 30 m forward grade window + power-gate + VSTOP gate as extract_regime_powers,
    but also accumulates, per regime (descent/flat/climb): moving time Σdt, horizontal Σdx,
    vertical Σdh. Returns times (s), dists (m), verticals (m)."""
    W = 30
    t = [0, 0, 0]
    x = [0, 0, 0]
    dh = [0, 0, 0]   # [descent, flat, climb]
    pw = ([], [], [])
    n = len(pts)
    for i in range(n):
        if pts[i].get("power") is None:
            continue
        if pts[i].get("v") is not None and pts[i]["v"] < VSTOP:
            continue
        j = i
        while j < n - 1 and pts[j]["x"] - pts[i]["x"] < W:
            j += 1
        dd = pts[j]["x"] - pts[i]["x"]
        if dd > 1:
            grade = (pts[j]["alt"] - pts[i]["alt"]) / dd
        else:
            k = i
            while k > 0 and pts[i]["x"] - pts[k]["x"] < W:
                k -= 1
            db = pts[i]["x"] - pts[k]["x"]
            grade = (pts[i]["alt"] - pts[k]["alt"]) / db if db > 1 else 0
        r = 2 if grade >= climb_thr else (0 if grade <= desc_thr else 1)
        dxLoc = pts[i]["x"] - pts[i - 1]["x"] if i > 0 else 0
        dhLoc = pts[i]["alt"] - pts[i - 1]["alt"] if i > 0 else 0
        t[r] += pts[i].get("dt") or 0
        x[r] += dxLoc if dxLoc > 0 else 0
        dh[r] += dhLoc
        pw[r].append({"p": pts[i]["power"], "w": pts[i].get("dt") or 1})

    def mean(b: list) -> float | None:
        if not b:
            return None
        sw = swp = 0.0
        for s in b:
            sw += s["w"]
            swp += s["w"] * s["p"]
        return swp / sw if sw else None

    return {
        "tD": t[0], "tF": t[1], "tC": t[2], "xD": x[0], "xF": x[1], "xC": x[2],
        "hC": dh[2], "hD": -dh[0],                       # climb vertical, descent drop
        "Pdesc": mean(pw[0]), "Pflat": mean(pw[1]), "Pclimb": mean(pw[2]),
        "tMovBin": t[0] + t[1] + t[2], "xBin": x[0] + x[1] + x[2],
    }


def descent_eq_speed(Pdesc: float, sbar: float, p: dict, vmax: float) -> float:
    """Descent equilibrium speed at power Pdesc on mean descent grade s̄ (>0): the same
    P+gravity aero-equilibrium bisection approxTime uses. Capped vmax."""
    mg = p["m"] * G
    w = p["wind"]
    slope = -sbar
    sec = math.sqrt(1 + slope * slope)
    sin = slope / sec
    cos = 1 / sec
    lo, hi = 0.05, 45
    for _ in range(40):
        vv = 0.5 * (lo + hi)
        f = (0.5 * p["rho"] * p["CdA"] * (vv + w) * abs(vv + w) + p["Crr"] * mg * cos
             + mg * sin - p["keff"] * (Pdesc if Pdesc > 0 else 0) / vv)
        if f < 0:
            lo = vv
        else:
            hi = vv
    return min(vmax, max(0.5, 0.5 * (lo + hi)))


def cell_hpm(prof: dict) -> dict[str, float]:
    """30 m-cell profile h± (alternative to regime-binned) — cells like eps_geom."""
    x0 = prof["x"][0]
    total = prof["x"][len(prof["x"]) - 1] - x0
    DX = 30
    nc = math.floor(total / DX)
    if nc < 2:
        return {"hplus": 0, "hminus": 0}
    j = 0

    def h_at(d: float) -> float:
        nonlocal j
        while j < len(prof["x"]) - 2 and prof["x"][j + 1] < d:
            j += 1
        seg = prof["x"][j + 1] - prof["x"][j]
        f = (d - prof["x"][j]) / seg if seg > 1e-9 else 0
        return prof["h"][j] * (1 - f) + prof["h"][j + 1] * f

    cell = [h_at(x0 + k * DX) for k in range(nc + 1)]
    hp = hm = 0.0
    for k in range(nc):
        d = cell[k + 1] - cell[k]
        if d > 0:
            hp += d
        else:
            hm += -d
    return {"hplus": hp, "hminus": hm}


def clamp01(v: float) -> float:
    return max(0, min(1, v))


def med_of(xs: list[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def iqr(xs: list[float]) -> list[float]:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return [float("nan"), float("nan")]

    def q(p: float) -> float:
        return s[math.floor(p * (len(s) - 1))]

    return [q(0.25), q(0.75)]


def corr_of(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    sx = 0.0
    for b in xs:
        sx += b
    sy = 0.0
    for b in ys:
        sy += b
    mx = sx / n
    my = sy / n
    sxy = sxx = syy = 0.0
    for i in range(n):
        sxy += (xs[i] - mx) * (ys[i] - my)
        sxx += (xs[i] - mx) * (xs[i] - mx)   # JS x ** 2 is x*x in V8
        syy += (ys[i] - my) * (ys[i] - my)
    return jsdiv(sxy, math.sqrt(sxx * syy))


def read_pts(file: str) -> list[dict]:
    global FIT_MANUF
    meta = {}
    pts = load_pts(os.path.join(DATA, file), meta)
    if meta:
        FIT_MANUF = meta["manufacturer"]
    return pts


# ===== NEW: regime-decomposed closed form =====
def regime_components(prof: dict, p: dict, pw: dict, thr: dict, eps: float,
                      descent_mode: str) -> dict:
    """Walk the (deadband-smoothed) 5 m profile edge by edge; classify each edge by local
    slope vs (thr.climbThr, thr.descThr); accumulate the base closed form per regime.
    `descent_mode` picks the firewalled descent treatment. Flat edges use RAW signed β·dh
    (no floor) so the all-flat limit reduces EXACTLY to the v1 law α·x + β·Σdh."""
    mg = p["m"] * G
    beta = mg / p["keff"]
    w = p["wind"]
    aRoll = mg * p["Crr"] / p["keff"]
    vFlat = max(0.05, flat_eq_speed(pw["flat"] if pw["flat"] > 0 else 1, p))
    aAeroFlat = 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) / p["keff"]
    xs, hs = prof["x"], prof["h"]
    Eflat = Eclimb = Edesc = xF = xC = xD = hpC = hmD = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        if not dx > 0:
            continue
        slope = dh / dx
        sec = math.sqrt(1 + slope * slope)
        sin = slope / sec
        cos = 1 / sec
        if slope >= thr["climbThr"]:
            vc = (min(vFlat, p["keff"] * pw["climb"] / (p["Crr"] * mg * cos + mg * sin))
                  if pw["climb"] > 0 else vFlat)
            aAeroC = 0.5 * p["rho"] * p["CdA"] * (vc + w) * abs(vc + w) / p["keff"]
            Eclimb += aRoll * dx + aAeroC * dx + beta * dh   # climb: aero at v_c(P₊), gravity exact
            xC += dx
            hpC += dh
        elif slope <= thr["descThr"]:
            drop = -dh
            if descent_mode == "R1a":
                Edesc += max(0, aRoll * dx + aAeroFlat * dx - eps * beta * drop)
            elif descent_mode == "R1b":
                vD = descent_eq_speed(pw["descent"], -slope, {**p, "vmax": VMAX}, VMAX)
                Edesc += (pw["descent"] if pw["descent"] > 0 else 0) * (dx * sec / vD)
            else:   # R1c: leg force-deficit at flat cruise speed (no ε, no P₋)
                deficit = (p["Crr"] * mg * cos
                           + 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) + mg * sin)
                Edesc += max(0, deficit) * (dx * sec) / p["keff"]
            xD += dx
            hmD += drop
        else:
            Eflat += aRoll * dx + aAeroFlat * dx + beta * dh   # flat: aero at v₌, gravity signed
            xF += dx
    return {"E": (Eflat + Eclimb + Edesc) / 1000, "Eflat": Eflat / 1000,
            "Eclimb": Eclimb / 1000, "Edesc": Edesc / 1000,
            "xF": xF, "xC": xC, "xD": xD, "hpC": hpC, "hmD": hmD, "vFlat": vFlat}


def regime_totals(prof: dict, p: dict, pw: dict, thr: dict, eps: float,
                  descent_mode: str) -> dict:
    """Regime closed form on TOTALS — the apples-to-apples form (the champion R0 evaluates
    on totals). Classify edges once to accumulate per-regime aggregates, then evaluate each
    regime's closed form ONCE: climb aero at a single v_c(s̄₊); descent clamp/equilibrium on
    the descent TOTAL, not per edge."""
    mg = p["m"] * G
    beta = mg / p["keff"]
    w = p["wind"]
    aRoll = mg * p["Crr"] / p["keff"]
    vFlat = max(0.05, flat_eq_speed(pw["flat"] if pw["flat"] > 0 else 1, p))
    aAeroFlat = 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) / p["keff"]
    xs, hs = prof["x"], prof["h"]
    xF = hpF = hmF = xC = hpC = xD = hmD = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        if not dx > 0:
            continue
        slope = dh / dx
        if slope >= thr["climbThr"]:
            xC += dx
            hpC += max(0, dh)
        elif slope <= thr["descThr"]:
            xD += dx
            hmD += max(0, -dh)
        else:
            xF += dx
            if dh >= 0:
                hpF += dh
            else:
                hmF += -dh
    Eflat = (aRoll + aAeroFlat) * xF + beta * (hpF - hmF)   # flat: aggregate, gravity net (no ε)
    Eclimb = 0
    if xC > 0:   # climb: single v_c at the mean climb grade s̄₊
        sC = hpC / xC
        secC = math.sqrt(1 + sC * sC)
        sinC = sC / secC
        cosC = 1 / secC
        vc = (min(vFlat, p["keff"] * pw["climb"] / (p["Crr"] * mg * cosC + mg * sinC))
              if pw["climb"] > 0 else vFlat)
        Eclimb = ((aRoll + 0.5 * p["rho"] * p["CdA"] * (vc + w) * abs(vc + w) / p["keff"]) * xC
                  + beta * hpC)
    Edesc = 0
    if xD > 0:   # descent: clamp / equilibrium on the descent TOTAL at the mean grade s̄₋
        sD = hmD / xD
        secD = math.sqrt(1 + sD * sD)
        sinD = -sD / secD
        cosD = 1 / secD
        if descent_mode == "R1a":
            Edesc = max(0, (aRoll + aAeroFlat) * xD - eps * beta * hmD)
        elif descent_mode == "R1b":
            vD = descent_eq_speed(pw["descent"], sD, {**p, "vmax": VMAX}, VMAX)
            Edesc = (pw["descent"] if pw["descent"] > 0 else 0) * (xD * secD / vD)
        else:
            deficit = (p["Crr"] * mg * cosD
                       + 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) + mg * sinD)
            Edesc = max(0, deficit) * xD * secD / p["keff"]
    return {"E": (Eflat + Eclimb + Edesc) / 1000, "Eflat": Eflat / 1000,
            "Eclimb": Eclimb / 1000, "Edesc": Edesc / 1000}


# R1d — the DEPLOYED sampasimu cost (Entry 18 pre-registration): per-edge VERBATIM v2Edge.
# ε is GRADE-LOCAL: ε(s) = clamp₀₁(min(1, (α/β)/s) − 0.13), s = |dh|/dx. The trailing max(0,·)
# is provably dead; kept verbatim, with the pre-clamp minimum tracked.
R1D_MIN_PRECLAMP = float("inf")


def r1d_v2_edge(prof: dict, p: dict, pw: dict, climb_thr: float) -> float:
    global R1D_MIN_PRECLAMP
    mg = p["m"] * G
    beta = mg / p["keff"]
    w = p["wind"]
    vFlat = max(0.05, flat_eq_speed(pw["flat"] if pw["flat"] > 0 else 1, p))
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) / p["keff"]
    abRatio = (aRoll + aAero) / beta   # α/β, same physics family as the champion's ε_geom
    xs, hs = prof["x"], prof["h"]
    E = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        if not dx > 0:
            continue
        if dh >= 0:
            aero = aAero * dx if dh < climb_thr * dx else 0
            e = aRoll * dx + aero + beta * dh
        else:
            ndh = -dh
            eps = abRatio * dx / ndh
            if eps > 1:
                eps = 1
            eps -= 0.13
            if eps < 0:
                eps = 0
            e = aRoll * dx + aAero * dx - eps * beta * ndh
            if e < R1D_MIN_PRECLAMP:
                R1D_MIN_PRECLAMP = e
            if e < 0:
                e = 0
        E += e
    return E / 1000


def r0_champion(prof: dict, profS: dict, p: dict, pw: dict,
                eps: float) -> dict:
    """R0 champion — smooth (cf + 2 m deadband) AND poor-man's scalar, VERBATIM formulae
    from ppaz_compare.mjs pass B (aSm/aRaw/km/eSm/ePm)."""
    vf = flat_eq_speed(pw["flat"], p)
    beta = p["m"] * G / p["keff"]
    aSm = approx_components(profS, p, vf, CLIMB_THR)
    aRaw = approx_components(prof, p, vf, CLIMB_THR)
    km = (max(0, 1 - 3 * (prof["x"][len(prof["x"]) - 1] / 1000) / aRaw["hplus"])
          if aRaw["hplus"] > 0 else 1)
    eSm = (aSm["roll"] + aSm["aero"] + aSm["climb"] - eps * beta * aSm["hminus"]) / 1000
    ePm = (aRaw["roll"] + aRaw["aero"]
           + km * (aRaw["climb"] - eps * beta * aRaw["hminus"])) / 1000
    return {"eSm": eSm, "ePm": ePm, "vf": vf}


def point_regime_data(pts: list[dict]) -> list[dict]:
    """Per-point 30 m-window grade (VERBATIM logic from extract_regime_powers) computed ONCE,
    so the threshold sweep re-bins cheaply."""
    W = 30
    out = []
    n = len(pts)
    for i in range(n):
        if pts[i].get("power") is None:
            continue
        if pts[i].get("v") is not None and pts[i]["v"] < VSTOP:
            continue
        j = i
        while j < n - 1 and pts[j]["x"] - pts[i]["x"] < W:
            j += 1
        dd = pts[j]["x"] - pts[i]["x"]
        if dd > 1:
            grade = (pts[j]["alt"] - pts[i]["alt"]) / dd
        else:
            k = i
            while k > 0 and pts[i]["x"] - pts[k]["x"] < W:
                k -= 1
            db = pts[i]["x"] - pts[k]["x"]
            grade = (pts[i]["alt"] - pts[k]["alt"]) / db if db > 1 else 0
        out.append({"p": pts[i]["power"], "w": pts[i].get("dt") or 1, "grade": grade})
    return out


def bin_grades(pd: list[dict], ct: float, dt: float) -> dict:
    bins = ([], [], [])
    for s in pd:
        bins[2 if s["grade"] >= ct else (0 if s["grade"] <= dt else 1)].append(s)

    def stat(b: list) -> float | None:
        if not b:
            return None
        sw = swp = 0.0
        for s in b:
            sw += s["w"]
            swp += s["w"] * s["p"]
        return swp / sw if sw else None

    return {"descent": stat(bins[0]), "flat": stat(bins[1]), "climb": stat(bins[2])}


def pw_from(rp: dict, pts: list[dict]) -> dict:
    flat = rp["flat"] if rp["flat"] is not None else overall_mean_power(pts)
    return {"climb": rp["climb"] if rp["climb"] is not None else flat, "flat": flat,
            "descent": rp["descent"] if rp["descent"] is not None else 0}


def d_pct(model: float, emp: float) -> float:
    return (model - emp) / emp * 100 if emp > 0 else float("nan")


# ===== per-ride processing =====
rows = []
sweep = {"longoes": {}, "censo": {}, "ppaz": {}, "jaam": {}, "danlessa": {}}


def sweep_key(ct: float, dt: float) -> str:
    return f"{to_fixed(ct * 100, 1)}/{to_fixed(dt * 100, 1)}"


def process_ride(pts: list[dict], p0: dict, label: str, corpus: str,
                 eps_rule: str) -> None:
    if not has_power(pts):
        return
    build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile(phys_profile, ENGINE_DX)
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    p = {**p0, "vmax": VMAX, "vstart": VSTART}
    mg = p["m"] * G
    w = p["wind"]
    beta = mg / p["keff"]
    emp = empirical_kj(pts)
    if not emp > 0:
        return
    pd = point_regime_data(pts)
    pw = pw_from(bin_grades(pd, CLIMB_THR, DESC_THR), pts)
    thr = {"climbThr": CLIMB_THR, "descThr": DESC_THR}
    vf = flat_eq_speed(pw["flat"], p)
    # ε corpus rule: urban → flat 0.20; open → frozen ε_geom (−0.13), on the RAW profile (as R0)
    eps = 0.20
    if eps_rule != "urban":
        eg = eps_geom(prof, p, vf)
        eps = eg if is_finite(eg) else 0.20
    r0 = r0_champion(prof, profS, p, pw, eps)
    # canonical selects power by local grade via pw.climbThr/descThr — must carry them.
    canon = canonical(prof, {**pw, "climbThr": CLIMB_THR, "descThr": DESC_THR}, p)["legE"] / 1000
    R1a = regime_components(profS, p, pw, thr, eps, "R1a")   # per-edge (sampasimu v2Edge-style)
    R1b = regime_components(profS, p, pw, thr, eps, "R1b")
    R1c = regime_components(profS, p, pw, thr, eps, "R1c")
    R1aT = regime_totals(profS, p, pw, thr, eps, "R1a")      # TOTALS (apt closed form, matches R0)
    R1bT = regime_totals(profS, p, pw, thr, eps, "R1b")
    R1cT = regime_totals(profS, p, pw, thr, eps, "R1c")
    # R1d — deployed v2Edge (grade-local ε; Entry 18) on the resolution × smoothing grid.
    R1d = r1d_v2_edge(profS, p, pw, CLIMB_THR)                 # 5 m + deadband (headline)
    R1d5r = r1d_v2_edge(prof, p, pw, CLIMB_THR)                # 5 m raw
    prof30 = resample_profile(phys_profile, 30)
    R1d30 = r1d_v2_edge({"x": prof30["x"], "h": deadband(prof30["h"], TAU_SMOOTH)},
                        p, pw, CLIMB_THR)                      # 30 m + deadband
    R1d30r = r1d_v2_edge(prof30, p, pw, CLIMB_THR)             # 30 m raw (deployment-faithful)
    # E_new2 (R2) — TOTALS decomposition: α(P₌)·x + β·h₊ − ε·β·h₋, aero over the FULL distance
    # at flat speed (the 'off' aero mode), on the deadband profile.
    aSm = approx_components(profS, p, vf, CLIMB_THR)
    aAeroFull = 0.5 * p["rho"] * p["CdA"] * (vf + w) * abs(vf + w) / p["keff"]
    R2 = (aSm["roll"] + aAeroFull * aSm["X"] + aSm["climb"] - eps * beta * aSm["hminus"]) / 1000
    # adaptive ±α/β threshold: α/β from the default-threshold v_f (one-shot, no iteration);
    # regime powers RE-EXTRACTED at ±α/β.
    ab = p["Crr"] + 0.5 * p["rho"] * p["CdA"] * (vf + w) * abs(vf + w) / mg
    thrA = {"climbThr": ab, "descThr": -ab}
    pwA = pw_from(bin_grades(pd, ab, -ab), pts)
    R1a_ad = regime_components(profS, p, pwA, thrA, eps, "R1a")
    # measured per-regime energy (Σ P·dt over the SAME 30 m classifier)
    rs = extract_regime_stats(pts, CLIMB_THR, DESC_THR)
    eMclimb = (rs["Pclimb"] if rs["Pclimb"] is not None else 0) * rs["tC"] / 1000
    eMflat = (rs["Pflat"] if rs["Pflat"] is not None else 0) * rs["tF"] / 1000
    eMdesc = (rs["Pdesc"] if rs["Pdesc"] is not None else 0) * rs["tD"] / 1000
    # threshold sweep on R1a (ε held at the default-threshold value; powers re-extracted per cell)
    for ct in SWEEP_CLIMB:
        for dt in SWEEP_DESC:
            e = regime_components(profS, p, pw_from(bin_grades(pd, ct, dt), pts),
                                  {"climbThr": ct, "descThr": dt}, eps, "R1a")["E"]
            sweep[corpus].setdefault(sweep_key(ct, dt), []).append(abs(d_pct(e, emp)))
    rows.append({
        "corpus": corpus, "ride": label, "emp": emp,
        "km": prof["x"][len(prof["x"]) - 1] / 1000, "vf_kmh": vf * 3.6, "ab": ab, "eps": eps,
        "r0sm": r0["eSm"], "r0pm": r0["ePm"], "canon": canon, "r1a": R1a["E"], "r1b": R1b["E"],
        "r1c": R1c["E"], "r1a_ad": R1a_ad["E"], "r2": R2,
        "r1a_t": R1aT["E"], "r1b_t": R1bT["E"], "r1c_t": R1cT["E"], "r1d": R1d, "r1d5r": R1d5r,
        "r1d30": R1d30, "r1d30r": R1d30r,
        "r1a_flat": R1a["Eflat"], "r1a_climb": R1a["Eclimb"], "r1a_desc": R1a["Edesc"],
        "xF": R1a["xF"], "xC": R1a["xC"], "xD": R1a["xD"], "hpC": R1a["hpC"], "hmD": R1a["hmD"],
        "eMclimb": eMclimb, "eMflat": eMflat, "eMdesc": eMdesc,
        "d_r0sm": d_pct(r0["eSm"], emp), "d_r0pm": d_pct(r0["ePm"], emp),
        "d_canon": d_pct(canon, emp),
        "d_r1a": d_pct(R1a["E"], emp), "d_r1b": d_pct(R1b["E"], emp), "d_r1c": d_pct(R1c["E"], emp),
        "d_r1a_ad": d_pct(R1a_ad["E"], emp), "d_r2": d_pct(R2, emp),
        "d_r1a_t": d_pct(R1aT["E"], emp), "d_r1b_t": d_pct(R1bT["E"], emp),
        "d_r1c_t": d_pct(R1cT["E"], emp),
        "d_r1d": d_pct(R1d, emp), "d_r1d5r": d_pct(R1d5r, emp), "d_r1d30": d_pct(R1d30, emp),
        "d_r1d30r": d_pct(R1d30r, emp),
        "d_rc": d_pct(R1a["Eclimb"], eMclimb), "d_rf": d_pct(R1a["Eflat"], eMflat),
        "d_rd": d_pct(R1a["Edesc"], eMdesc),
    })


# ===== reporting helpers (module level in the .mjs too) =====
def f(x: float | None, d: int = 1) -> str:
    if x is None or not is_finite(x):
        return "—"
    return to_fixed(x, d)


def erf(x: float) -> float:
    t = 1 / (1 + 0.3275911 * abs(x))
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
             + 0.254829592) * t * math.exp(-x * x)
    return y if x >= 0 else -y


def p_from_z(z: float) -> float:
    return 2 * (1 - 0.5 * (1 + erf(abs(z) / math.sqrt(2)))) if is_finite(z) else float("nan")


def paired_abs(st: list[dict], kA: str, kB: str) -> dict:
    """paired sign + Wilcoxon (normal approx) on per-ride |Δ%|, A vs B."""
    d = []
    wins = losses = 0
    for r in st:
        a = abs(r[kA])
        b = abs(r[kB])
        if not is_finite(a) or not is_finite(b):
            continue
        d.append(a - b)
        if a < b:
            wins += 1        # A better ⇒ smaller |Δ%|
        elif a > b:
            losses += 1
    n = wins + losses
    zSign = (wins - n / 2) / math.sqrt(n / 4) if n > 0 else float("nan")
    nz = sorted(({"a": abs(x), "s": (1 if x > 0 else -1)} for x in d if x != 0),
                key=lambda o: o["a"])
    i = 0
    Wpos = 0.0
    m = len(nz)
    while i < m:
        j = i
        while j < m - 1 and nz[j + 1]["a"] == nz[i]["a"]:
            j += 1
        rank = (i + j + 2) / 2
        for k in range(i, j + 1):
            if nz[k]["s"] > 0:
                Wpos += rank
        i = j + 1
    muW = m * (m + 1) / 4
    sdW = math.sqrt(m * (m + 1) * (2 * m + 1) / 24)
    zW = (Wpos - muW) / sdW if sdW > 0 else float("nan")
    return {"wins": wins, "losses": losses, "n": n,
            "winFrac": wins / n if n else float("nan"), "medDiff": med_of(d),
            "pSign": p_from_z(zSign), "pWilcoxon": p_from_z(zW)}


# ===== CSV cell writer (JS: typeof 'string' → JSON.stringify; finite → +Number(v).toFixed(3);
# anything else → '') =====
_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def jquote(s: str) -> str:
    out = ['"']
    for ch in s:
        if ch in _ESC:
            out.append(_ESC[ch])
        elif ch < " ":
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def cell(v: object) -> str:
    if isinstance(v, str):
        return jquote(v)
    if is_finite(v):
        return js_str(float(to_fixed(v, 3)))
    return ""


COLS = ['corpus', 'ride', 'emp', 'km', 'vf_kmh', 'ab', 'eps', 'r0sm', 'r0pm', 'canon', 'r1a',
        'r1b', 'r1c', 'r1a_t', 'r1b_t', 'r1c_t', 'r1d', 'r1d5r', 'r1d30', 'r1d30r', 'r1a_ad',
        'r2', 'r1a_flat', 'r1a_climb', 'r1a_desc', 'xF', 'xC', 'xD', 'hpC', 'hmD', 'eMclimb',
        'eMflat', 'eMdesc', 'd_r0sm', 'd_r0pm', 'd_canon', 'd_r1a', 'd_r1b', 'd_r1c', 'd_r1a_t',
        'd_r1b_t', 'd_r1c_t', 'd_r1d', 'd_r1d5r', 'd_r1d30', 'd_r1d30r', 'd_r1a_ad', 'd_r2',
        'd_rc', 'd_rf', 'd_rd']


# ===== sanity gates (SANITY=1 → synthetic checks then exit, before touching the corpora) =====
def run_sanity() -> None:
    global R1D_MIN_PRECLAMP

    def approx(a: float, b: float, tol: float = 1e-6) -> bool:
        a = 0 if a is None else a
        b = 0 if b is None else b   # JS numeric coercion of null in Math.abs(a - b)
        return abs(a - b) <= tol * (1 + abs(b))

    pFlat = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0,
             "vmax": VMAX, "vstart": VSTART}

    def mkProf(n: int, dx: float, slopeFn: "Callable[[int], float]") -> dict:
        x = [0.0] * n
        h = [0.0] * n
        for i in range(n):
            x[i] = float(i * dx)
            h[i] = h[i - 1] + slopeFn(i) * dx if i > 0 else 0.0
        return {"x": x, "h": h}

    ok = [True]

    def say(name: str, passed: bool, extra: str = "") -> None:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}{('  ' + extra) if extra else ''}")
        if not passed:
            ok[0] = False

    spts = []
    for i in range(400):
        spts.append({"x": i * 7, "alt": 100 + 20 * math.sin(i / 15), "power": 150 + (i % 20),
                     "v": 6, "dt": 1})
    rpE = extract_regime_powers(spts, CLIMB_THR, DESC_THR)
    rpB = bin_grades(point_regime_data(spts), CLIMB_THR, DESC_THR)
    say("binGrades ≡ extractRegimePowers",
        all((rpE[k]["mean"] is None and rpB[k] is None)
            or approx(rpE[k]["mean"], rpB[k], 1e-9)
            for k in ("climb", "flat", "descent")))

    prof = mkProf(2001, 5, lambda i: 0.03 * math.sin(i / 40))
    pw = {"climb": 200, "flat": 150, "descent": 80}
    vFlat = flat_eq_speed(pw["flat"], pFlat)
    mg = pFlat["m"] * G
    beta = mg / pFlat["keff"]
    aRoll = mg * pFlat["Crr"] / pFlat["keff"]
    aAero = 0.5 * pFlat["rho"] * pFlat["CdA"] * vFlat * abs(vFlat) / pFlat["keff"]
    X = sumdh = 0.0
    for i in range(1, len(prof["x"])):
        X += prof["x"][i] - prof["x"][i - 1]
        sumdh += prof["h"][i] - prof["h"][i - 1]
    rawV1 = (aRoll * X + aAero * X + beta * sumdh) / 1000
    allFlat = regime_components(prof, pFlat, pw, {"climbThr": 1e9, "descThr": -1e9},
                                0.2, "R1a")["E"]
    say("reduction: all-flat R1a == raw v1 law", approx(allFlat, rawV1),
        f"R1a {to_fixed(allFlat, 4)} vs v1 {to_fixed(rawV1, 4)}")

    rc = regime_components(prof, pFlat, pw, {"climbThr": CLIMB_THR, "descThr": DESC_THR},
                           0.2, "R1a")
    say("additivity Σ components == E",
        approx(rc["Eflat"] + rc["Eclimb"] + rc["Edesc"], rc["E"], 1e-9))

    flatProf = mkProf(2001, 5, lambda i: 0)
    flatProfS = {"x": flatProf["x"], "h": deadband(flatProf["h"], TAU_SMOOTH)}
    eqPw = {"climb": pw["flat"], "flat": pw["flat"], "descent": pw["flat"],
            "climbThr": CLIMB_THR, "descThr": DESC_THR}
    rcF = regime_components(flatProfS, pFlat, eqPw, {"climbThr": CLIMB_THR, "descThr": DESC_THR},
                            0.2, "R1a")
    r0F = r0_champion(flatProf, flatProfS, pFlat, eqPw, 0.2)
    canF = canonical(flatProf, eqPw, pFlat)["legE"] / 1000
    say("flat anchor: R1a == R0.eSm", approx(rcF["E"], r0F["eSm"], 1e-6),
        f"{to_fixed(rcF['E'], 3)} vs {to_fixed(r0F['eSm'], 3)}")
    say("flat anchor: R1a ≈ canonical (≤1.5%)", abs(rcF["E"] - canF) / canF < 0.015,
        f"R1a {to_fixed(rcF['E'], 2)} vs canon {to_fixed(canF, 2)}")

    climbProf = mkProf(2001, 5, lambda i: 0.06)
    climbProfS = {"x": climbProf["x"], "h": deadband(climbProf["h"], TAU_SMOOTH)}
    rcC = regime_components(climbProfS, pFlat, {"climb": 250, "flat": 200, "descent": 0},
                            {"climbThr": CLIMB_THR, "descThr": DESC_THR}, 0.2, "R1a")
    peFloor = beta * climbProf["h"][len(climbProf["h"]) - 1] / 1000
    say("pure climb: E_climb ≥ PE floor", rcC["Eclimb"] >= peFloor - 1e-6,
        f"E_climb {to_fixed(rcC['Eclimb'], 1)} ≥ PE {to_fixed(peFloor, 1)}")
    # monotone climb ⇒ no spurious descent regime; the 2 m deadband lag leaves a short flat base
    # segment (roll+aero, no gravity), so climb must merely DOMINATE, not be the only regime.
    say("pure climb: no spurious descent + climb dominates",
        approx(rcC["Edesc"], 0) and rcC["Eclimb"] / rcC["E"] > 0.97,
        f"E_desc {to_fixed(rcC['Edesc'], 3)} · climb frac {to_fixed(rcC['Eclimb'] / rcC['E'], 3)}")

    # regimeTotals: same reduction + additivity, and it must EQUAL regimeComponents where there is
    # no nonlinearity to diverge on — a CONSTANT-grade climb ⇒ totals ≡ per-edge.
    tAllFlat = regime_totals(prof, pFlat, pw, {"climbThr": 1e9, "descThr": -1e9}, 0.2, "R1a")["E"]
    say("regimeTotals reduction: all-flat == raw v1", approx(tAllFlat, rawV1),
        f"{to_fixed(tAllFlat, 4)} vs {to_fixed(rawV1, 4)}")
    tc = regime_totals(prof, pFlat, pw, {"climbThr": CLIMB_THR, "descThr": DESC_THR}, 0.2, "R1a")
    say("regimeTotals additivity",
        approx(tc["Eflat"] + tc["Eclimb"] + tc["Edesc"], tc["E"], 1e-9))
    cePw = {"climb": 250, "flat": 200, "descent": 0}
    ct = {"climbThr": CLIMB_THR, "descThr": DESC_THR}
    ceEdge = regime_components(climbProf, pFlat, cePw, ct, 0.2, "R1a")
    ceTot = regime_totals(climbProf, pFlat, cePw, ct, 0.2, "R1a")
    say("constant-grade climb: totals ≡ per-edge",
        abs(ceEdge["E"] - ceTot["E"]) / ceTot["E"] < 1e-3,
        f"edge {to_fixed(ceEdge['E'], 2)} vs totals {to_fixed(ceTot['E'], 2)}")

    # R1d gates (Entry 18)
    dPw = {"climb": 200, "flat": 150, "descent": 60}
    r1dClimb = r1d_v2_edge(climbProf, pFlat, dPw, 1e9)
    cX = cH = 0.0
    for i in range(1, len(climbProf["x"])):
        cX += climbProf["x"][i] - climbProf["x"][i - 1]
        cH += climbProf["h"][i] - climbProf["h"][i - 1]
    vD = flat_eq_speed(dPw["flat"], pFlat)
    aR = mg * pFlat["Crr"] / pFlat["keff"]
    aA = 0.5 * pFlat["rho"] * pFlat["CdA"] * vD * abs(vD) / pFlat["keff"]
    v1Climb = (aR * cX + aA * cX + beta * cH) / 1000
    say("R1d reduction: no-descent + climbThr=∞ == raw v1", approx(r1dClimb, v1Climb),
        f"{to_fixed(r1dClimb, 3)} vs {to_fixed(v1Climb, 3)}")
    descProf = mkProf(2001, 5, lambda i: -0.05)
    descProfS = {"x": descProf["x"], "h": deadband(descProf["h"], TAU_SMOOTH)}
    epsD = eps_geom(descProf, pFlat, vD)
    r0D = r0_champion(descProf, descProfS, pFlat,
                      {**dPw, "climbThr": CLIMB_THR, "descThr": DESC_THR}, epsD)
    r1dD = r1d_v2_edge(descProfS, pFlat, dPw, CLIMB_THR)
    say("R1d ≡ R0 on constant-grade descent (no Jensen gap)",
        abs(r1dD - r0D["eSm"]) / abs(r0D["eSm"]) < 1e-6,
        f"R1d {to_fixed(r1dD, 4)} vs R0 {to_fixed(r0D['eSm'], 4)} (ε_geom {to_fixed(epsD, 3)})")
    say("R1d pre-clamp positivity (synthetics)", R1D_MIN_PRECLAMP > 0,
        f"min {to_exponential(R1D_MIN_PRECLAMP, 2)} J")

    print("\nSANITY: ALL PASS" if ok[0] else "\nSANITY: FAILURES ABOVE")
    sys.exit(0 if ok[0] else 1)


def main() -> None:
    os.makedirs(RESULTS, exist_ok=True)

    if os.environ.get("SANITY"):
        run_sanity()

    # ===== drivers =====
    nL = nC = nP = nJ = nD = zwTot = 0
    # longões (per-ride physics from model_inputs.json)
    try:
        with open(os.path.join(DATA, "model_inputs.json"), encoding="utf-8") as fh:
            inputs = json.load(fh)
        for e in inputs:
            if (not e.get("file") or not e.get("has_power")
                    or not os.path.exists(os.path.join(DATA, e["file"]))):
                continue
            p = {"m": e["m"], "Crr": e["crr"], "CdA": e["cda"], "rho": e["rho"],
                 "keff": e["keff"], "wind": (e.get("wind_kmh") or 0) / 3.6}
            try:
                process_ride(read_pts(e["file"]), p, e["label"], "longoes", "open")
                nL += 1
            except Exception:
                pass   # skip
    except Exception as ex:
        sys.stdout.flush()
        print("longões load error", str(ex), file=sys.stderr)
    print(f"longões: {nL} power rides")

    # censo (ASSUMED rider, physical-floor filter — same as censo_compare/time_compare)
    try:
        with open(os.path.join(DATA, "censohidrografico", "manifest.json"), encoding="utf-8") as fh:
            man = json.load(fh)
        for e in man:
            if not e.get("file") or not os.path.exists(os.path.join(DATA, e["file"])):
                continue
            try:
                pts = read_pts(e["file"])
                if not has_power(pts):
                    continue
                p = {**ASSUMED, "vmax": VMAX, "vstart": VSTART}
                build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
                profS = {"x": resample_profile(phys_profile, ENGINE_DX)["x"],
                         "h": deadband(resample_profile(phys_profile, ENGINE_DX)["h"], TAU_SMOOTH)}
                aSm = approx_components(profS, p, flat_eq_speed(overall_mean_power(pts), p),
                                        CLIMB_THR)
                if empirical_kj(pts) < (p["m"] * G / p["keff"]) * aSm["hplus"] / 1000:
                    continue   # dataOK floor
                process_ride(pts, ASSUMED, e["name"], "censo", "urban")
                nC += 1
            except Exception:
                pass   # skip
    except Exception as ex:
        sys.stdout.flush()
        print("censo load error", str(ex), file=sys.stderr)
    print(f"censo: {nC} rides (physical floor)")

    # independent riders + author full export (manifest, physics frozen + env overrides, Zwift out)
    for corpus, manifest in (("ppaz", "strava_ppaz_manifest.json"),
                             ("jaam", "strava_jaam_manifest.json"),
                             ("danlessa", "strava_danlessa_manifest.json")):
        phys = PHYS[corpus]
        n = zw = 0
        try:
            with open(os.path.join(DATA, manifest), encoding="utf-8") as fh:
                man = json.load(fh)
            cand = [a for a in man if a.get("sport") == "ride" and jgt(a.get("powCov"), 0.5)
                    and jge(a.get("km"), 20) and jge(a.get("altCov"), 0.99)]
            for a in cand:
                try:
                    pts = read_pts(a["file"])
                    if FIT_MANUF == ZWIFT:
                        zw += 1
                        continue
                    process_ride(pts, phys, a["id"], corpus, "open")
                    n += 1
                except Exception:
                    pass   # skip
                if n % 200 == 0 and n:
                    print(f"  …{corpus} {n}/{len(cand)}")
        except Exception as ex:
            sys.stdout.flush()
            print(f"{corpus} load error", str(ex), file=sys.stderr)
        zwTot += zw
        if corpus == "ppaz":
            nP = n
        elif corpus == "jaam":
            nJ = n
        else:
            nD = n
        print(f"{corpus}: {n} rides (skipped {zw} Zwift), m {js_str(phys['m'])} kg · "
              f"CdA {js_str(phys['CdA'])} · Crr {js_str(phys['Crr'])}")

    # ===== reporting =====
    def by_corpus(c: str) -> list[dict]:
        return [r for r in rows if r["corpus"] == c]

    CORP = [("longoes", "longões (open, per-ride physics)"), ("censo", "censo (urban, assumed)"),
            ("ppaz", "P. Paz (open, assumed)"), ("jaam", "JAAM (open, assumed)"),
            ("danlessa", "author full (open, in-sample)")]
    KEYS = [("d_r0sm", "R0 champion (cf+2m smooth)"), ("d_r0pm", "R0 poor-man scalar"),
            ("d_canon", "canonical (forward sim)"), ("d_r1a", "R1a regime (ε clamp)"),
            ("d_r1b", "R1b regime (P₋·t₋)"), ("d_r1c", "R1c regime (force-deficit)"),
            ("d_r1a_t", "R1a TOTALS (ε clamp)"), ("d_r1b_t", "R1b TOTALS (P₋·t₋)"),
            ("d_r1c_t", "R1c TOTALS (force-def)"),
            ("d_r1d", "R1d v2Edge (grade-local ε)"),
            ("d_r2", "R2 totals (α·x+β(h₊−εh₋))"), ("d_r1a_ad", "R1a adaptive ±α/β")]

    print("\n================================================================")
    print("REGIME-DECOMPOSED MODEL — median |Δ%| vs measured ∫P·dt, per corpus")
    print("(all share the same regime powers; canonical on the raw profile, R0/R1*/R2 on the 2 m")
    print(" deadband profile — the established convention. The R1a-vs-R0 endpoint is profile-matched.)")
    for c, title in CORP:
        st = by_corpus(c)
        if not st:
            continue
        print(f"\n── {title} ──  n={len(st)}")
        print(f"{'model'.ljust(30)}{'med|Δ%|'.rjust(9)}{'medΔ%'.rjust(8)}")
        for k, lab in KEYS:
            ds = [r[k] for r in st if is_finite(r[k])]
            print(f"{lab.ljust(30)}{f(med_of([abs(v) for v in ds])).rjust(9)}"
                  f"{f(med_of(ds)).rjust(8)}")
        print(f"  median: {f(med_of([r['km'] for r in st]))} km · "
              f"v_f {f(med_of([r['vf_kmh'] for r in st]))} km/h · "
              f"α/β {f(med_of([r['ab'] * 100 for r in st]), 2)}% · "
              f"ε {f(med_of([r['eps'] for r in st]), 2)}")

    print("\n================================================================")
    print("PRE-DECLARED PRIMARY ENDPOINT — R1a vs R0 (cf+2m smooth), P. Paz, med|Δ%| vs ∫P·dt")
    Pset = by_corpus("ppaz")
    r1aMed = med_of([x for x in (abs(r["d_r1a"]) for r in Pset) if is_finite(x)])
    r0Med = med_of([x for x in (abs(r["d_r0sm"]) for r in Pset) if is_finite(x)])
    pt = paired_abs(Pset, "d_r1a", "d_r0sm")
    print(f"  R1a {f(r1aMed)}%  vs  R0 {f(r0Med)}%   (n={len(Pset)})")
    print(f"  paired R1a−R0: R1a better on {pt['wins']}/{pt['n']} "
          f"({f(pt['winFrac'] * 100, 0)}%) · med Δ|Δ%| {f(pt['medDiff'], 2)}pp · "
          f"sign p={f(pt['pSign'], 3)} · Wilcoxon p={f(pt['pWilcoxon'], 3)}")
    print("================================================================")

    print("\nENTRY-18 PRE-REGISTERED ENDPOINT — R1d (deployed v2Edge, grade-local ε) vs R0, P. Paz")
    r1dMed = med_of([x for x in (abs(r["d_r1d"]) for r in Pset) if is_finite(x)])
    pt18 = paired_abs(Pset, "d_r1d", "d_r0sm")
    print(f"  R1d {f(r1dMed)}%  vs  R0 {f(r0Med)}%   (n={len(Pset)})")
    print(f"  paired R1d−R0: R1d better on {pt18['wins']}/{pt18['n']} "
          f"({f(pt18['winFrac'] * 100, 0)}%) · med Δ|Δ%| {f(pt18['medDiff'], 2)}pp · "
          f"sign p={f(pt18['pSign'], 3)} · Wilcoxon p={f(pt18['pWilcoxon'], 3)}")
    # Jensen-direction check: grade-local ε gives MORE descent credit ⇒ R1d predicts LESS than R0
    print("\n  Jensen direction (med per-ride r1d − r0sm, kJ; negative ⇒ R1d below R0 as predicted):")
    for c, _title in CORP:
        st = by_corpus(c)
        if not st:
            continue
        dj = med_of([x for x in (r["r1d"] - r["r0sm"] for r in st) if is_finite(x)])
        mA = med_of([x for x in (abs(r["d_r1d"]) for r in st) if is_finite(x)])
        mB = med_of([x for x in (abs(r["d_r0sm"]) for r in st) if is_finite(x)])
        print(f"    {c.ljust(10)} {f(dj, 2)} kJ  (med |Δ%|: R1d {f(mA)} vs R0 {f(mB)})")
    print("\n  R1d resolution×smoothing sensitivity (med |Δ%|): 5m+db (headline) · 5m raw · "
          "30m+db (FABDEM-grid) · 30m raw (deployed default)")
    for c, _title in CORP:
        st = by_corpus(c)
        if not st:
            continue

        def g(k: str, st: list[dict] = st) -> str:
            return f(med_of([x for x in (abs(r[k]) for r in st) if is_finite(x)]))

        print(f"    {c.ljust(10)} {g('d_r1d')} · {g('d_r1d5r')} · {g('d_r1d30')} · {g('d_r1d30r')}")
    print(f"\n  dead-clamp assert: min pre-clamp descent edge across ALL rides = "
          f"{to_exponential(R1D_MIN_PRECLAMP, 2)} J "
          + ("(> 0 ✓ — the max(0,·) never fired)" if R1D_MIN_PRECLAMP > 0
             else "(≤ 0 — CLAMP FIRED, Entry-18 claim violated!)"))

    # HEAD-TO-HEAD (paired, each regime variant vs R0) on all THREE full open datasets.
    print("\n---------------- HEAD-TO-HEAD: regime variants vs R0 champion (paired) ----------------")
    for c, title in (("ppaz", "P. Paz"), ("jaam", "JAAM"),
                     ("danlessa", "author full (in-sample ε)")):
        st = by_corpus(c)
        if not st:
            continue
        mR0 = med_of([x for x in (abs(r["d_r0sm"]) for r in st) if is_finite(x)])
        print(f"  {title}  (n={len(st)}, R0 {f(mR0)}%):")
        for k, lab in (("d_r1a", "R1a edge"), ("d_r1a_t", "R1a totals"), ("d_r1c_t", "R1c totals"),
                       ("d_r2", "R2 totals"), ("d_r1d", "R1d v2Edge")):
            t = paired_abs(st, k, "d_r0sm")
            mA = med_of([x for x in (abs(r[k]) for r in st) if is_finite(x)])
            print(f"     {lab} {f(mA)}%  · {lab} better {t['wins']}/{t['n']} "
                  f"({f(t['winFrac'] * 100, 0)}%) · sign p={f(t['pSign'], 3)} · "
                  f"Wilcoxon p={f(t['pWilcoxon'], 3)}")
    print("================================================================")

    # threshold sweep (R1a med|Δ%| surface per corpus) + adaptive comparison
    print("\n---------------- THRESHOLD SWEEP (R1a med|Δ%|; rows=climbThr%, cols=descThr%) ----------------")
    for c, title in CORP:
        sw = sweep[c]
        if not by_corpus(c):
            continue
        print(f"\n{title}:")
        print("climb\\desc " + "".join(to_fixed(d * 100, 1).rjust(7) for d in SWEEP_DESC))
        best = {"v": float("inf"), "k": ""}
        for ct in SWEEP_CLIMB:
            cells = []
            for dt in SWEEP_DESC:
                arr = sw.get(sweep_key(ct, dt)) or []
                m = med_of(arr)
                if m < best["v"]:
                    best = {"v": m, "k": sweep_key(ct, dt)}
                cells.append(f(m).rjust(7))
            print(f"{to_fixed(ct * 100, 1).rjust(6)}    " + "".join(cells))
        adMed = med_of([x for x in (abs(r["d_r1a_ad"]) for r in by_corpus(c)) if is_finite(x)])
        defMed = med_of([x for x in (abs(r["d_r1a"]) for r in by_corpus(c)) if is_finite(x)])
        abMed = med_of([r["ab"] * 100 for r in by_corpus(c)])
        print(f"  best fixed cell {best['k']} = {f(best['v'])}% · default 2.0/-1.5 = "
              f"{f(defMed)}% · adaptive ±α/β = {f(adMed)}% (med α/β {f(abMed, 2)}%)")

    # per-regime attribution (R1a component vs measured regime energy)
    print("\n---------------- PER-REGIME ATTRIBUTION (R1a component vs measured ΣP·dt in that regime) ----------------")
    print(f"{'corpus'.ljust(10)}{'climb|Δ%|'.rjust(11)}{'flat|Δ%|'.rjust(10)}{'desc|Δ%|'.rjust(10)}"
          "   (median; where measured regime energy > 1 kJ)")
    for c, _title in CORP:
        st = by_corpus(c)
        if not st:
            continue

        def g(k: str, mk: float | None, st: list[dict] = st) -> float:
            return med_of([x for x in (abs(r[k]) for r in st if r[mk] > 1) if is_finite(x)])

        print(f"{c.ljust(10)}{f(g('d_rc', 'eMclimb')).rjust(11)}"
              f"{f(g('d_rf', 'eMflat')).rjust(10)}{f(g('d_rd', 'eMdesc')).rjust(10)}")

    # ===== CSV (gitignored via data/results/*) =====
    csv = "\n".join([",".join(COLS)]
                    + [",".join(cell(r.get(k)) for k in COLS) for r in rows])
    csv_name = "regime_comparison" + env_suffix(
        "PPAZ_M", "PPAZ_CDA", "PPAZ_CRR", "JAAM_M", "JAAM_CDA", "JAAM_CRR",
        "DANLESSA_M", "DANLESSA_CDA", "DANLESSA_CRR") + ".csv"
    with open(os.path.join(RESULTS, csv_name), "w", encoding="utf-8") as fh:
        fh.write(csv + "\n")
    print(f"\nwrote {csv_name} ({len(rows)} rides: L {nL} C {nC} P {nP} J {nJ} "
          f"D {nD}, skipped {zwTot} Zwift)")


if __name__ == "__main__":
    main()
