#!/usr/bin/env python3
"""TIME-MODEL empirical test across all three datasets (longões 44 · censo 62 · P. Paz 441).

Python port of harness/time_compare.mjs (same output, byte-identical console
report and CSV). The energy law is validated (Entries 1–12); its TIME twin —
t = x*/v_f with x* = x + k₊·h₊ − k₋·h₋, k₊ = v_f·β/P_climb (clean) and k₋ the
lumped time-ε, joined by the ε↔k₋ bridge through descent power (article §5) —
was explicitly THEORY-ONLY. This harness supplies the missing empirical leg.

Shared engine/pipeline functions come from src/bicycling_energy_model (the machine-verified
Python port): flatEqSpeed, resampleProfile, deadband, empiricalKJ,
overallMeanPower, ptsFromGPX, approxTime, canonical, buildProfile,
approxComponents and parseFIT/ptsFromFIT are body-identical to the .mjs's
copies (the file_id manufacturer arrives via the parse meta dict), as are the
small helpers isFinite/jsdiv. The harness-specific instruments (epsCellsPz,
extractRegimeStats, descentEqSpeed, cellHpm, the predictor battery and the
fits) are ported locally below, faithfully. The .mjs's dead copies
(extractRegimePowers, pushStats, epsGeom, climbBalance, iqr — defined there
but never called) are not ported.

Design (fixed after an adversarial methods review — see the plan / Entry 13):
 · Target: T_mov_bin = moving time over powered+moving segments.
 · Coefficient tests are v_f-free / part-whole-safe; ε is the FROZEN geometry
   estimator clamp01(ε_coast − 0.13).
 · Predictors vs T_mov_bin, both v_f modes; k₋ fit ONCE on longões then FROZEN.
 · PRE-DECLARED PRIMARY ENDPOINT: T1b, power-conditioned v_f, med|Δ%| vs
   T_mov_bin, on the 441 P. Paz rides. Reported whatever it is.

  python3 src/harness/time_compare.py     (reads the three gitignored track sets + manifests)
Output: console report + time_comparison.csv (gitignored via data/results/*).
"""

import gzip
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approx_components, approx_time, build_profile,
                                    canonical, deadband, empirical_kj,
                                    flat_eq_speed, is_finite, jsdiv,
                                    overall_mean_power, pts_from_fit,
                                    pts_from_gpx, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
os.makedirs(RESULTS, exist_ok=True)
VMAX, VSTART = 38 / 3.6, 15 / 3.6
VMAX_HI = 55 / 3.6                              # descent-cap sensitivity for the fast rider
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
VSTOP = 0.5 / 3.6
SQRT2 = math.sqrt(2)                            # Math.SQRT2
# ASSUMED generic rider for censo + P. Paz (P. Paz mass overridden below). Longões carry
# per-ride physics in model_inputs.json.
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}
PPAZ_MASS = float(os.environ["PPAZ_M"]) if os.environ.get("PPAZ_M") else 74.5  # Entry 12 inversion (re-baselined, Entry 27)
ZWIFT = 260

phys_profile = None   # the .mjs's `physProfile` global (set at the build_profile call sites)
FIT_MANUF = None      # the .mjs's `FIT_MANUF` global (set by read_pts via the parse meta dict)


def eprint(msg):
    """console.error: keep the stdout/stderr interleaving of the combined stream."""
    sys.stdout.flush()
    print(msg, file=sys.stderr)


# ===== engines: the .mjs's VERBATIM copies (epsCellsPz) =====
# flatEqSpeed / resampleProfile / canonical / buildProfile / ptsFromFIT /
# approxComponents come from bicycling_energy_model (body-identical).

def has_power(pts):
    return any(q.get("power") is not None for q in pts)


# Descent 30 m cells: ε_bal AND the geometric ε_coast/s̄ in one pass (adapted from
# compare.mjs's epsFromBalance; the ε_coast accumulation mirrors eps_hypothesis.mjs).
def eps_cells_pz(pts, p):
    if not pts or len(pts) < 2:
        return None
    mg = p["m"] * G
    beta = mg / p["keff"]
    VSTOP_L = 0.5 / 3.6
    x0 = pts[0]["x"]
    totalM = pts[-1]["x"] - x0
    DX = 30
    nc = math.floor(totalM / DX)
    if nc < 2:
        return None
    j = 0

    def alt_at(d):
        nonlocal j
        while j < len(pts) - 2 and pts[j + 1]["x"] < d:
            j += 1
        seg = pts[j + 1]["x"] - pts[j]["x"]
        fr = (d - pts[j]["x"]) / seg if seg > 1e-9 else 0
        return pts[j]["alt"] * (1 - fr) + pts[j + 1]["alt"] * fr

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


# ptsFromGPX — from bicycling_energy_model (VERBATIM port of compare.mjs's; the one longões GPX ride)
# approxTime — from bicycling_energy_model (VERBATIM port of applet/index.html's)

# ===== NEW INSTRUMENT: per-regime moving time / distance / vertical =====
# Same 30 m forward grade window + power-gate + VSTOP gate as extractRegimePowers, but also
# accumulates, per regime (descent/flat/climb): moving time Σdt, horizontal Σdx, vertical Σdh
# (all over the SAME gated points that feed P̄, so t₊+t_flat+t₋ ≡ Σdt over gated points, and
# k₊_meas/k₋_meas use exactly the P̄ point set). Returns times (s), dists (m), verticals (m).
def extract_regime_stats(pts, climb_thr, desc_thr):
    W = 30
    t = [0.0, 0.0, 0.0]
    x = [0.0, 0.0, 0.0]
    dh = [0.0, 0.0, 0.0]   # [descent, flat, climb]
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
        r = 2 if grade >= climb_thr else 0 if grade <= desc_thr else 1
        dxLoc = pts[i]["x"] - pts[i - 1]["x"] if i > 0 else 0
        dhLoc = pts[i]["alt"] - pts[i - 1]["alt"] if i > 0 else 0
        t[r] += pts[i].get("dt") or 0
        x[r] += dxLoc if dxLoc > 0 else 0
        dh[r] += dhLoc
        pw[r].append((pts[i]["power"], pts[i].get("dt") or 1))

    def mean(b):
        if not b:
            return None
        sw = swp = 0.0
        for pv, w in b:
            sw += w
            swp += w * pv
        return swp / sw if sw else None

    return {
        "tD": t[0], "tF": t[1], "tC": t[2], "xD": x[0], "xF": x[1], "xC": x[2],
        "hC": dh[2], "hD": -dh[0],                              # climb vertical, descent drop (both ≥0 typ.)
        "Pdesc": mean(pw[0]), "Pflat": mean(pw[1]), "Pclimb": mean(pw[2]),
        "tMovBin": t[0] + t[1] + t[2], "xBin": x[0] + x[1] + x[2],
    }


# Descent equilibrium speed at power Pdesc on mean descent grade s̄ (>0): the same P+gravity
# aero-equilibrium bisection approxTime uses, extracted for the bridge fallback. Capped vmax.
def descent_eq_speed(Pdesc, sbar, p, vmax):
    mg = p["m"] * G
    w = p["wind"]
    slope = -sbar
    sec = math.sqrt(1 + slope * slope)
    sin = slope / sec
    cos = 1 / sec
    lo, hi = 0.05, 45
    for _ in range(40):
        vv = 0.5 * (lo + hi)
        fv = (0.5 * p["rho"] * p["CdA"] * (vv + w) * abs(vv + w) + p["Crr"] * mg * cos
              + mg * sin - p["keff"] * (Pdesc if Pdesc > 0 else 0) / vv)
        if fv < 0:
            lo = vv
        else:
            hi = vv
    return min(vmax, max(0.5, 0.5 * (lo + hi)))


# 30 m-cell profile h± (alternative to regime-binned, for the sensitivity run) — cells like epsGeom.
def cell_hpm(prof):
    x0 = prof["x"][0]
    total = prof["x"][-1] - x0
    DX = 30
    nc = math.floor(total / DX)
    if nc < 2:
        return {"hplus": 0, "hminus": 0}
    j = 0

    def h_at(d):
        nonlocal j
        while j < len(prof["x"]) - 2 and prof["x"][j + 1] < d:
            j += 1
        seg = prof["x"][j + 1] - prof["x"][j]
        fr = (d - prof["x"][j]) / seg if seg > 1e-9 else 0
        return prof["h"][j] * (1 - fr) + prof["h"][j + 1] * fr

    cell = [h_at(x0 + k * DX) for k in range(nc + 1)]
    hp = hm = 0.0
    for k in range(nc):
        d = cell[k + 1] - cell[k]
        if d > 0:
            hp += d
        else:
            hm += -d
    return {"hplus": hp, "hminus": hm}


def clamp01(v):
    if v != v:
        return v
    return max(0, min(1, v))


def med_of(xs):
    s = sorted(x for x in xs if is_finite(x))
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2 if s else float("nan")


def corr_of(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sxx = syy = 0.0
    for i in range(n):
        sxy += (xs[i] - mx) * (ys[i] - my)
        sxx += (xs[i] - mx) ** 2
        syy += (ys[i] - my) ** 2
    return jsdiv(sxy, math.sqrt(sxx * syy))


def read_pts(file):
    global FIT_MANUF
    with open(os.path.join(DATA, file), "rb") as fh:
        buf = fh.read()
    if file.endswith(".gz"):
        buf = gzip.decompress(buf)
    if file.endswith(".gpx") or file.endswith(".gpx.gz"):
        return pts_from_gpx(buf.decode("utf-8", errors="replace"))
    meta = {}
    pts = pts_from_fit(buf, meta)
    FIT_MANUF = meta["manufacturer"]
    return pts


# ---- build the per-ride measured record (corpus-agnostic) ----
def measure_ride(pts, p, label, corpus):
    global phys_profile
    info = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    phys_profile = {"x": info["x"], "h": info["h"]}
    prof = resample_profile(phys_profile, ENGINE_DX)
    rs = extract_regime_stats(pts, CLIMB_THR, DESC_THR)
    Pflat = rs["Pflat"] if rs["Pflat"] is not None else overall_mean_power(pts)
    Pclimb = rs["Pclimb"] if rs["Pclimb"] is not None else Pflat
    Pdesc = rs["Pdesc"] if rs["Pdesc"] is not None else 0
    pw = {"climb": Pclimb, "flat": Pflat, "descent": Pdesc,
          "climbThr": CLIMB_THR, "descThr": DESC_THR}
    beta = p["m"] * G / p["keff"]
    vfPow = flat_eq_speed(Pflat, p)
    vfMeas = rs["xF"] / rs["tF"] if rs["tF"] > 0 and rs["xF"] > 0 else vfPow   # harmonic flat speed
    # measured total moving time (all v≥VSTOP points) + elapsed + stop fraction
    tMov = 0.0
    t0 = t1 = None
    for q in pts:
        if q.get("v") is not None and q["v"] >= VSTOP:
            tMov += q.get("dt") or 0
        if q.get("t") is not None:
            if t0 is None:
                t0 = q["t"]
            t1 = q["t"]
    tEl = t1 - t0 if (t0 is not None and t1 is not None and t1 > t0) else float("nan")
    stopFrac = max(0, 1 - tMov / tEl) if is_finite(tEl) and tEl > 0 else float("nan")
    timeOK = bool(tMov > 0 and rs["tMovBin"] >= 0.9 * tMov)
    cell = cell_hpm(prof)
    # frozen ε (geometry) for the bridge
    ec = eps_cells_pz(pts, p)
    epsFrozen = clamp01(ec["epsCoast"] - 0.13) if ec else float("nan")
    aeroSpd = vfPow + p["wind"]
    alpha = (p["Crr"] * p["m"] * G + 0.5 * p["rho"] * p["CdA"] * aeroSpd * abs(aeroSpd)) / p["keff"]
    sbarC = rs["hC"] / rs["xC"] if rs["hC"] > 0 and rs["xC"] > 0 else float("nan")
    sbarD = rs["hD"] / rs["xD"] if rs["hD"] > 0 and rs["xD"] > 0 else float("nan")
    # coefficient tests
    rPlus = Pclimb * rs["tC"] / (beta * rs["hC"]) if rs["hC"] > 0 and Pclimb > 0 else float("nan")
    kPlusMeas = (vfPow * rs["tC"] - rs["xC"]) / rs["hC"] if rs["hC"] > 0 else float("nan")
    vDescMeas = rs["xD"] / rs["tD"] if rs["xD"] > 0 and rs["tD"] > 0 else float("nan")
    denom = alpha - epsFrozen * beta * sbarD
    bridgeValid = bool(is_finite(sbarD) and is_finite(epsFrozen)
                       and Pdesc >= 0.2 * Pflat and denom > 0)
    if not is_finite(sbarD):
        vDescPred = float("nan")
    elif bridgeValid:
        vDescPred = Pdesc / denom
    else:
        vDescPred = descent_eq_speed(Pdesc, sbarD, dict(p, vmax=VMAX), VMAX)
    kMinusMeas = (rs["xD"] - vfPow * rs["tD"]) / rs["hD"] if rs["hD"] > 0 else float("nan")
    kMinusBridge = ((1 - jsdiv(vfPow, vDescPred)) / sbarD
                    if is_finite(vDescPred) and is_finite(sbarD) and sbarD > 0 else float("nan"))
    # mid/high-fidelity predictors (absolute seconds); T2 uses vf, T3 power-only
    at38 = approx_time(prof, dict(p, vmax=VMAX), vfPow, pw)
    at55 = approx_time(prof, dict(p, vmax=VMAX_HI), vfPow, pw)
    c38 = canonical(prof, pw, dict(p, vmax=VMAX))
    c55 = canonical(prof, pw, dict(p, vmax=VMAX_HI))
    return {
        "corpus": corpus, "ride": label,
        "X": rs["xBin"], "hC": rs["hC"], "hD": rs["hD"], "xC": rs["xC"], "xF": rs["xF"],
        "xD": rs["xD"], "tC": rs["tC"], "tF": rs["tF"], "tD": rs["tD"],
        "sbarC": sbarC, "sbarD": sbarD, "hC_cell": cell["hplus"], "hD_cell": cell["hminus"],
        "tMovBin": rs["tMovBin"], "tMov": tMov, "tEl": tEl, "stopFrac": stopFrac, "timeOK": timeOK,
        "Pflat": Pflat, "Pclimb": Pclimb, "Pdesc": Pdesc, "vfPow": vfPow, "vfMeas": vfMeas,
        "beta": beta, "alpha": alpha, "epsFrozen": epsFrozen,
        "rPlus": rPlus, "kPlusMeas": kPlusMeas, "vDescMeas": vDescMeas, "vDescPred": vDescPred,
        "bridgeValid": bridgeValid, "kMinusMeas": kMinusMeas, "kMinusBridge": kMinusBridge,
        "kMinusApprox": at38["kMinus"], "kPlusApprox": at38["kPlus"],
        "T2_38": at38["t"], "T2_55": at55["t"], "T3_38": c38["t"], "T3_55": c55["t"],
        "canonStall38": c38["stalled"],
    }


# ---- predictors: given a measured row, a v_f mode, and fitted (k₋ scalar, OLS) → predicted seconds ----
# physics-derived climb multiplier: t₊≈β·h₊/P̄_climb (pure lift), minus the horizontal
# baseline 1/s̄₊ already in x. NOTE the pure-lift form under-charges by the roll+aero share
# (≈ the Entry-7 energy over-charge k_h≈1.26) — a known, disclosed bias, not fitted out here.
def k_plus_exact(r, vf):
    if is_finite(r["sbarC"]) and r["sbarC"] > 0:
        return jsdiv(vf * r["beta"], r["Pclimb"]) - 1 / r["sbarC"]
    return jsdiv(vf * r["beta"], r["Pclimb"]) if r["Pclimb"] > 0 else 0


def predict(r, mode, fit):
    vf = r["vfPow"] if mode == "pow" else r["vfMeas"]
    hC, hD = r["hC"], r["hD"]
    kP = k_plus_exact(r, vf)
    out = {}
    out["T0"] = r["X"] / vf                                              # naive: flat-only
    out["TS"] = (r["X"] + 8 * hC) / vf                                   # Scarf literature k₊≈8, k₋=0
    out["T1a"] = (r["X"] + kP * hC) / vf                                 # physics k₊, no descent term
    out["T1b"] = (r["X"] + kP * hC - fit["kMinus"] * hD) / vf            # + longões-frozen scalar k₋
    kMinusR = r["kMinusBridge"] if is_finite(r["kMinusBridge"]) else 0
    out["T1c"] = (r["X"] + kP * hC - kMinusR * hD) / vf                  # + per-ride bridge k₋
    out["T2"] = r["T2_38"]                                               # approxTime (uses vfPow), mode-invariant
    out["T3"] = r["T3_38"]                                               # canonical forward sim
    # FAIR CEILING: same per-ride v_f as the physics, but k₊/k₋ FITTED on longões (not derived)
    # then frozen — isolates "does the physical k₊ match the best-fit k₊?" from the v_f model.
    out["TF"] = (r["X"] + fit["kP"] * hC - fit["kM"] * hD) / vf
    # naive linear ceiling (absolute seconds, NO per-ride v_f) — illustrates why per-ride speed
    # is load-bearing: this transfers badly precisely because it bakes in one fixed flat pace.
    out["OLS"] = fit["ols"][0] * r["X"] + fit["ols"][1] * hC + fit["ols"][2] * hD
    return out


# ---- drivers: assemble rows across the three corpora ----
rows = []


def push_ride(pts, p, label, corpus):
    try:
        if not has_power(pts):
            return
        r = measure_ride(pts, p, label, corpus)
        if r["tMovBin"] > 60:
            rows.append(r)
    except Exception:
        pass   # skip unparseable


# longões (model_inputs.json: per-ride physics)
nL = 0
try:
    inputs = json.load(open(os.path.join(DATA, "model_inputs.json")))
    for e in inputs:
        if not e.get("file") or not e.get("has_power"):
            continue
        fp = os.path.join(DATA, e["file"])
        if not os.path.exists(fp):
            continue
        p = {"m": e["m"], "Crr": e["crr"], "CdA": e["cda"], "rho": e["rho"], "keff": e["keff"],
             "wind": (e.get("wind_kmh") or 0) / 3.6, "vmax": VMAX, "vstart": VSTART}
        try:
            push_ride(read_pts(e["file"]), p, e["label"], "longoes")
            nL += 1
        except Exception:
            pass   # skip
except Exception as err:
    eprint(f"longões load error {err}")
print(f"longões: scanned {nL} power entries")

# censo (ASSUMED rider, physical-floor dataOK filter mirrors censo_compare.mjs)
nC = 0
try:
    man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
    for e in man:
        if not e.get("file"):
            continue
        fp = os.path.join(DATA, e["file"])
        if not os.path.exists(fp):
            continue
        p = {**ASSUMED, "vmax": VMAX, "vstart": VSTART}
        try:
            pts = read_pts(e["file"])
            if not has_power(pts):
                continue
            # physical floor (deadband-smoothed climb PE) — same as censo_compare
            info = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
            phys_profile = {"x": info["x"], "h": info["h"]}
            prof = resample_profile(phys_profile, ENGINE_DX)
            profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
            aSm = approx_components(profS, p, flat_eq_speed(overall_mean_power(pts), p), CLIMB_THR)
            emp = empirical_kj(pts)
            peFloor = (p["m"] * G / p["keff"]) * aSm["hplus"] / 1000
            if emp < peFloor:
                continue                 # dataOK filter
            push_ride(pts, p, e.get("name"), "censo")
            nC += 1
        except Exception:
            pass   # skip
except Exception as err:
    eprint(f"censo load error {err}")
print(f"censo: {nC} rides passed the physical floor")

# P. Paz (mass = Entry-12 inversion; Entry-12 manifest filters; Zwift excluded)
nP = 0
zw = 0


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else float("nan")


try:
    man = json.load(open(os.path.join(DATA, "strava_ppaz_manifest.json")))
    cand = [a for a in man if a.get("sport") == "ride" and _num(a.get("powCov")) > 0.5
            and _num(a.get("km")) >= 20 and _num(a.get("altCov")) >= 0.99]
    for a in cand:
        p = {**ASSUMED, "m": PPAZ_MASS, "vmax": VMAX, "vstart": VSTART}
        try:
            pts = read_pts(a["file"])
            if FIT_MANUF == ZWIFT:
                zw += 1
                continue
            push_ride(pts, p, a["id"], "ppaz")
            nP += 1
        except Exception:
            pass   # skip
        if nP % 100 == 0 and nP:
            print(f"  …ppaz {nP}/{len(cand)}")
except Exception as err:
    eprint(f"ppaz load error {err}")
print(f"ppaz: {nP} rides (skipped {zw} Zwift), mass {js_str(PPAZ_MASS)} kg\n")

# ---- clean gating per corpus ----
clean = [r for r in rows if r["timeOK"] and is_finite(r["tMovBin"]) and r["tMovBin"] > 0]
L = [r for r in clean if r["corpus"] == "longoes"]
C = [r for r in clean if r["corpus"] == "censo"]
P = [r for r in clean if r["corpus"] == "ppaz"]


# ---- fit on longões (T_mov_bin target), then FREEZE ----
# scalar k₋ (T1b), holding k₊ = the physics-derived kPlusExact
def fit_k_minus(train, mode):
    best = 0.0
    bestErr = float("inf")
    k = 0.0
    while k <= 20.0001:
        errs = []
        for r in train:
            vf = r["vfPow"] if mode == "pow" else r["vfMeas"]
            pred = (r["X"] + k_plus_exact(r, vf) * r["hC"] - k * r["hD"]) / vf
            errs.append(abs(pred - r["tMovBin"]) / r["tMovBin"] * 100)
        m = med_of(errs)
        if m < bestErr:
            bestErr = m
            best = k
        k += 0.1
    return {"k": float(to_fixed(best, 1)), "err": bestErr}


# FAIR-CEILING pair (k₊,k₋) both FITTED (power-conditioned v_f held per-ride) — the honest
# benchmark for the physics-derived k₊: same v_f model, best-fit hill coefficients.
def fit_pair(train):
    bkP = 0.0
    bkM = 0.0
    bestErr = float("inf")
    kp = 0.0
    while kp <= 25.0001:
        km = 0.0
        while km <= 15.0001:
            errs = [abs((r["X"] + kp * r["hC"] - km * r["hD"]) / r["vfPow"] - r["tMovBin"])
                    / r["tMovBin"] * 100 for r in train]
            m = med_of(errs)
            if m < bestErr:
                bestErr = m
                bkP = kp
                bkM = km
            km += 0.5
        kp += 0.5
    return {"kP": bkP, "kM": bkM, "err": bestErr}


def fit_ols(train):   # naive linear ceiling t = a·X + b·hC + c·hD (absolute seconds, no v_f)
    A = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    bvec = [0.0, 0.0, 0.0]
    for r in train:
        g = [r["X"], r["hC"], r["hD"]]
        y = r["tMovBin"]
        for i in range(3):
            for j in range(3):
                A[i][j] += g[i] * g[j]
            bvec[i] += g[i] * y

    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))

    D = det(A)
    if abs(D) < 1e-9:
        return [0, 0, 0]

    def col(m, c, v):
        return [[v[i] if j == c else x for j, x in enumerate(row)] for i, row in enumerate(m)]

    return [det(col(A, 0, bvec)) / D, det(col(A, 1, bvec)) / D, det(col(A, 2, bvec)) / D]


pairFit = fit_pair(L)
fitPow = {"kMinus": fit_k_minus(L, "pow")["k"], "kP": pairFit["kP"], "kM": pairFit["kM"],
          "ols": fit_ols(L)}
fitMeas = {"kMinus": fit_k_minus(L, "meas")["k"], "kP": pairFit["kP"], "kM": pairFit["kM"],
           "ols": fitPow["ols"]}
if fitPow["kMinus"] <= 0.05 or fitPow["kMinus"] >= 19.95:
    eprint(f"NOTE k₋(power-cond) grid at boundary: {js_str(fitPow['kMinus'])} — expected: vfPow "
           "over-estimates real moving-flat speed, so any k₋>0 worsens the median "
           "(speed-anchored fit disambiguates).")


def erf(x):
    t = 1 / (1 + 0.3275911 * abs(x))
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
             + 0.254829592) * t * math.exp(-x * x)
    return y if x >= 0 else -y


def p_from_z(z):
    return 2 * (1 - 0.5 * (1 + erf(abs(z) / SQRT2))) if is_finite(z) else float("nan")


# paired sign test + Wilcoxon signed-rank (normal approx) on per-ride |Δ%|, predA vs predB
def paired_test(set_, mode, fit, keyA, keyB):
    d = []   # |Δ%|_A − |Δ%|_B  (negative ⇒ A better)
    wins = losses = 0
    for r in set_:
        pr = predict(r, mode, fit)
        a = abs(pr[keyA] - r["tMovBin"]) / r["tMovBin"] * 100
        b = abs(pr[keyB] - r["tMovBin"]) / r["tMovBin"] * 100
        if not is_finite(a) or not is_finite(b):
            continue
        d.append(a - b)
        if a < b:
            wins += 1
        elif a > b:
            losses += 1
    n = wins + losses
    zSign = (wins - n / 2) / math.sqrt(n / 4) if n > 0 else float("nan")   # sign test, continuity ignored
    # Wilcoxon signed-rank on nonzero d
    nz = sorted(({"a": abs(x), "s": 1 if x > 0 else -1} for x in d if x != 0),
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
    zW = (Wpos - muW) / sdW if sdW > 0 else float("nan")   # >0 ⇒ A worse (larger |Δ%| ranks)
    return {"wins": wins, "losses": losses, "n": n,
            "winFrac": wins / n if n else float("nan"), "medDiff": med_of(d),
            "pSign": p_from_z(zSign), "pWilcoxon": p_from_z(zW)}


# ---- aggregate + report ----
PREDS = ["T0", "TS", "T1a", "T1b", "T1c", "T2", "T3", "TF", "OLS"]


def f(x, d=1):
    if x is None or (isinstance(x, float) and x != x):
        return "—"
    return to_fixed(x, d)


def scoreboard(set_, mode, fit):
    out = {}
    for key in PREDS:
        ds = []
        for r in set_:
            pr = predict(r, mode, fit)[key]
            v = ((pr - r["tMovBin"]) / r["tMovBin"] * 100
                 if is_finite(pr) and r["tMovBin"] > 0 else float("nan"))
            if is_finite(v):
                ds.append(v)
        out[key] = {"n": len(ds), "medAbs": med_of([abs(x) for x in ds]), "medSigned": med_of(ds)}
    return out


LAB = {"T0": "T0  x/v_f (naive)", "TS": "TS  Scarf k₊=8", "T1a": "T1a ascent-only (physics k₊)",
       "T1b": "T1b full (physics k₊, k₋ frozen)", "T1c": "T1c per-ride bridge k₋",
       "T2": "T2  approxTime", "T3": "T3  canonical", "TF": "TF  FAIR ceiling (k₊,k₋ fit)",
       "OLS": "OLS naive-linear (no v_f)"}


def print_score(title, set_, mode, fit):
    sb = scoreboard(set_, mode, fit)
    print(f"\n{title}  (n={len(set_)}, v_f={'power-conditioned' if mode == 'pow' else 'speed-anchored'})")
    print("predictor".ljust(34) + "n".rjust(4) + "med|Δ%|".rjust(9) + "medΔ%".rjust(8))
    for key in PREDS:
        print(LAB[key].ljust(34) + str(sb[key]["n"]).rjust(4)
              + f(sb[key]["medAbs"]).rjust(9) + f(sb[key]["medSigned"]).rjust(8))


print("================================================================")
print("TIME-MODEL TEST — target = moving time over powered segments (T_mov_bin)")
print(f"clean rides: longões {len(L)} · censo {len(C)} · ppaz {len(P)}")
print("\nFITTED ON LONGÕES, then FROZEN:")
print(f"  scalar k₋ (physics k₊):  power-cond={js_str(fitPow['kMinus'])}  speed-anch={js_str(fitMeas['kMinus'])}")
print(f"  FAIR ceiling (both fit, power-cond v_f):  k₊={js_str(fitPow['kP'])}  k₋={js_str(fitPow['kM'])}  (compare k₊ to the physics k₊)")
print(f"  naive-linear (abs seconds, no v_f):  t = {f(fitPow['ols'][0], 3)}·x + {f(fitPow['ols'][1], 3)}·h₊ + {f(fitPow['ols'][2], 3)}·h₋")

# coefficient-level (energy-side) diagnostic — NOT independent time evidence
print("\n---------------- CLIMB OVER-CHARGE (energy identity, disclosed as NON-time) ----------------")
print("r₊ = P̄_climb·t₊/(β·h₊) ≡ k_eff·E_climb/(mg·h₊): t₊ cancels (P̄_climb≡E_climb/t₊), so this is the")
print("Entry-7 ENERGY over-charge, NOT independent time evidence — reported only for cross-corpus stability.")
for nm, set_ in [("longões", L), ("censo", C), ("ppaz", P)]:
    rp = [r["rPlus"] for r in set_ if is_finite(r["rPlus"])]
    steep = [r["rPlus"] for r in set_ if r["sbarC"] >= 0.05 and is_finite(r["rPlus"])]
    print(f"  {nm.ljust(8)} r₊ med {f(med_of(rp), 2)} (n={len(rp)}) · steep s̄₊≥5% {f(med_of(steep), 2)}")

# descent-speed bridge test — lead with CORRELATION (median is over uncapped analytic form)
print("\n---------------- DESCENT BRIDGE (v_desc = P̄_desc/(α−ε·β·s̄), FROZEN ε) ----------------")
print("analytic bridge is UNCAPPED — near the α=ε·β·s̄ degeneracy it diverges; lead with correlation.")
for nm, set_ in [("longões", L), ("censo", C), ("ppaz", P)]:
    sub = [r for r in set_ if is_finite(r["vDescMeas"]) and is_finite(r["vDescPred"])
           and r["hD"] >= 50 and r["xD"] >= 1000 and r["sbarD"] >= 0.03]
    meas = [r["vDescMeas"] * 3.6 for r in sub]
    pred = [min(r["vDescPred"], 999) * 3.6 for r in sub]
    inValid = [r for r in set_ if r["hD"] >= 50 and r["xD"] >= 1000 and r["sbarD"] >= 0.03]
    validFrac = (sum(1 for r in inValid if r["bridgeValid"]) / len(inValid)
                 if inValid else float("nan"))
    print(f"  {nm.ljust(8)} v_desc real descents (s̄₋≥3%, h₋≥50 m, x₋≥1 km, n={len(sub)}): "
          f"corr {f(corr_of(pred, meas), 2)} · med meas {f(med_of(meas))} vs pred {f(med_of(pred))} km/h "
          f"· bridge-valid {f(validFrac * 100, 0)}%")
    print(f"           k₋_meas med {f(med_of([r['kMinusMeas'] for r in set_]), 2)} (free, corpus-dependent) "
          f"· stopFrac med {f(med_of([r['stopFrac'] for r in set_]) * 100, 0)}%")

# scoreboards
print("\n---------------- TOTAL-TIME PREDICTORS ----------------")
print_score("LONGÕES (in-sample fit)", L, "pow", fitPow)
print_score("CENSO (frozen)", C, "pow", fitPow)
print_score("P. PAZ (frozen)", P, "pow", fitPow)

print("\n================================================================")
pep = scoreboard(P, "pow", fitPow)["T1b"]
pt0 = scoreboard(P, "pow", fitPow)["T0"]
test = paired_test(P, "pow", fitPow, "T1b", "T0")
print("PRE-DECLARED PRIMARY ENDPOINT — T1b, power-conditioned v_f, P. Paz (out-of-sample):")
print(f"  median |Δ%| = {f(pep['medAbs'])} (signed {f(pep['medSigned'])}, n={pep['n']})  vs naive T0 {f(pt0['medAbs'])}  — modest")
print(f"  paired T1b−T0: wins {test['wins']}/{test['n']} ({f(test['winFrac'] * 100, 0)}%) · med Δ|Δ%| {f(test['medDiff'], 2)}pp · sign p={f(test['pSign'], 3)} · Wilcoxon p={f(test['pWilcoxon'], 3)}")
print(f"  vs FAIR fitted ceiling TF {f(scoreboard(P, 'pow', fitPow)['TF']['medAbs'])} (physics competitive)")
print("================================================================")

# diagnostics: speed-anchored (PARTIALLY IN-SAMPLE) + vmax + terciles + mass note
print("\n---------------- DIAGNOSTICS ----------------")
print("speed-anchored v_f = x_flat/t_flat SHARES measured flat time with the target — PARTIALLY IN-SAMPLE:")
print_score("P. PAZ speed-anchored v_f", P, "meas", fitMeas)
for nm, set_ in [("longões", L), ("censo", C), ("ppaz", P)]:
    t2_38 = med_of([abs(r["T2_38"] - r["tMovBin"]) / r["tMovBin"] * 100
                    if is_finite(r["T2_38"]) else float("nan") for r in set_])
    t2_55 = med_of([abs(r["T2_55"] - r["tMovBin"]) / r["tMovBin"] * 100
                    if is_finite(r["T2_55"]) else float("nan") for r in set_])
    t3_38 = med_of([abs(r["T3_38"] - r["tMovBin"]) / r["tMovBin"] * 100
                    if is_finite(r["T3_38"]) else float("nan") for r in set_])
    t3_55 = med_of([abs(r["T3_55"] - r["tMovBin"]) / r["tMovBin"] * 100
                    if is_finite(r["T3_55"]) else float("nan") for r in set_])
    print(f"vmax sens ({nm}): T2 38/55 km/h {f(t2_38)}/{f(t2_55)} · T3 {f(t3_38)}/{f(t3_55)}")
# hilliness terciles (P. Paz, EXPLORATORY — pre-motivated, not pre-registered): where the
# ascent term is physically expected to matter. Only the aggregate T1b-pow-ppaz was pre-declared.
print("\nP. Paz hilliness terciles (exploratory):")
byHill = sorted(({"r": r, "h": r["hC"] / max(1, r["X"])} for r in P), key=lambda o: o["h"])
third = math.floor(len(byHill) / 3)
for nm, seg in [("flat", byHill[0:third]), ("mid", byHill[third:2 * third]),
                ("hilly", byHill[2 * third:])]:
    set_ = [o["r"] for o in seg]
    sb = scoreboard(set_, "pow", fitPow)
    print(f"  {nm.ljust(6)} (n={len(set_)}, med h₊/x {f(med_of([o['h'] * 1000 for o in seg]), 1)} m/km): "
          f"T0 {f(sb['T0']['medAbs'])} · T1b {f(sb['T1b']['medAbs'])} · TF {f(sb['TF']['medAbs'])}")
print("\nNOTE: run `PPAZ_M=70 node time_compare.mjs` and `PPAZ_M=78 …` for the mass-sensitivity of the endpoint.")

# ---- CSV ----
cols = ["corpus", "ride", "X", "hC", "hD", "hC_cell", "hD_cell", "xC", "xF", "xD", "tC", "tF",
        "tD", "sbarC", "sbarD", "tMovBin", "tMov", "tEl", "stopFrac", "timeOK", "Pflat",
        "Pclimb", "Pdesc", "vfPow", "vfMeas", "epsFrozen", "rPlus", "kPlusMeas", "vDescMeas",
        "vDescPred", "bridgeValid", "kMinusMeas", "kMinusBridge", "T2_38", "T2_55", "T3_38",
        "T3_55"]
for r in clean:
    pr = predict(r, "pow", fitPow)
    r["_T1b"] = pr["T1b"]
    r["_T0"] = pr["T0"]


def csv_cell(v):
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)) and math.isfinite(v):
        return js_str(float(to_fixed(v, 3)))
    return ""


csv_text = "\n".join([",".join(cols + ["T1b_pred", "T0_pred"])]
                     + [",".join([csv_cell(r.get(k)) for k in cols]
                                 + [f(r["_T1b"], 1), f(r["_T0"], 1)]) for r in clean])
with open(os.path.join(RESULTS, "time_comparison.csv"), "w") as fh:
    fh.write(csv_text + "\n")
print(f"\nwrote time_comparison.csv ({len(clean)} rides)")
