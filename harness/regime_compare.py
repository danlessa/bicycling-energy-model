#!/usr/bin/env python3
"""REGIME-DECOMPOSED closed form — Python port of harness/regime_compare.mjs
(same console report, byte-identical results/regime_comparison.csv).

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

  python3 harness/regime_compare.py          (SANITY=1 → synthetic gates only)
Output: console report + results/regime_comparison.csv (gitignored via results/*).

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
  resampleProfile → resample_profile (bem)      canonical → canonical (LOCAL, reduced)
  approxComponents → approx_components          buildProfile → build_profile (LOCAL, reduced)
  extractRegimePowers → extract_regime_powers (LOCAL, mean-only)
  parseFIT → parse_fit (LOCAL, extended)        finishPts → finish_pts (bem)
  ptsFromFIT → pts_from_fit (LOCAL, extended)   deadband → deadband (bem)
  empiricalKJ → empirical_kj (bem)              overallMeanPower → overall_mean_power (bem)
  hasPower → has_power            pushStats → push_stats        epsGeom → eps_geom (bem)
  climbBalance → climb_balance    epsCellsPz → eps_cells_pz     ptsFromGPX → pts_from_gpx (bem)
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

import gzip
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))

from bem import (approx_time, deadband, empirical_kj, eps_geom, finish_pts,  # noqa: F401,E402
                 flat_eq_speed, haversine, overall_mean_power, pts_from_gpx,
                 resample_profile)
from bem.jsfmt import js_str, to_exponential, to_fixed  # noqa: E402
from bem.v8math import _js_sin  # noqa: E402

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
G, NS = 9.81, 240
VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
VSTOP = 0.5 / 3.6
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}


def is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def jsdiv(a, b):
    """JS division semantics when b == 0 (Python raises; JS yields ±inf/NaN)."""
    if b != 0:
        return a / b
    if a == 0 or a != a:
        return float("nan")
    neg = (a < 0) != (math.copysign(1.0, b) < 0)
    return float("-inf") if neg else float("inf")


def jgt(v, t):
    """JS `v > t` with v possibly undefined (a missing manifest field): always false."""
    return v is not None and v > t


def jge(v, t):
    """JS `v >= t` with v possibly undefined: always false."""
    return v is not None and v >= t


def jnum(s):
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
for _r, _m0 in (("ppaz", 74.3), ("jaam", 101.7), ("danlessa", 74.5)):
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
# haversine, flatEqSpeed, resampleProfile, finishPts, deadband, empiricalKJ,
# overallMeanPower, epsGeom, ptsFromGPX, approxTime are byte-for-byte the frozen JS
# reference → imported from bem above. The REDUCED/EXTENDED copies follow.

def canonical(prof, pw, p):
    """Forward-dynamics sim — the .mjs's REDUCED copy (no speed/regime/brake
    bookkeeping arrays; returns legE, t, stalled only). Same dynamics as bem.canonical."""
    m, Crr, CdA, rho, keff, vmax = p["m"], p["Crr"], p["CdA"], p["rho"], p["keff"], p["vmax"]
    xs, hs = prof["x"], prof["h"]
    n = len(xs)
    DT_MAX, DS_MIN = 0.25, 0.2
    KEinit = 0.5 * m * p["vstart"] * p["vstart"]
    KE = KEinit
    legE = t = Wrr = Waero = Wgrav = Wbrake = 0.0
    keCap = 0.5 * m * vmax * vmax
    stalled = False   # P=0 with resistance > KE: halt, never floor the KE (a floor injects energy)
    wind = p["wind"]
    for i in range(1, n):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        slope = dh / dx
        sec = math.sqrt(1 + slope * slope)
        cos = 1 / sec
        sin = slope / sec
        Frr = Crr * m * G * cos
        Fgrav = m * G * sin
        if slope >= pw["climbThr"]:
            P = pw["climb"]
        elif slope <= pw["descThr"]:
            P = pw["descent"]
        else:
            P = pw["flat"]
        remaining = dx * sec
        while remaining > 1e-9:
            v = math.sqrt(2 * KE / m)
            dsSub = min(remaining, max(v * DT_MAX, DS_MIN))
            rel = v + wind
            Faero = 0.5 * rho * CdA * rel * abs(rel)
            R = Frr + Faero + Fgrav
            Pleg = min(max(R * v / keff, 0), P) if v >= vmax else P
            A = keff * Pleg * dsSub * math.sqrt(m / 2)
            B = KE - R * dsSub
            if A > 0:
                lo = 1e-12
                hi = max(KE, B, 1) + A + 1
                while hi - A / math.sqrt(hi) - B <= 0:
                    hi *= 2
                KEn = KE if (KE > lo and KE < hi) else 0.5 * (lo + hi)
                for _ in range(40):
                    root = math.sqrt(KEn)
                    g = KEn - A / root - B
                    if g > 0:
                        hi = KEn
                    else:
                        lo = KEn
                    nxt = KEn - g / (1 + 0.5 * A / (KEn * root))
                    if not (nxt > lo and nxt < hi):
                        nxt = 0.5 * (lo + hi)
                    if abs(nxt - KEn) <= 1e-9 * KEn + 1e-12:
                        KEn = nxt
                        break
                    KEn = nxt
            else:
                # A = 0 (no propulsion): exact linear-KE solution — NO floor (a floor injects energy).
                KEn = B
                if KEn <= 0:   # resistance exhausts the KE inside this substep: finite stop, halt
                    dsStop = KE / R if R > 0 else 0
                    t += math.sqrt(2 * m * max(KE, 0)) / R if R > 0 else 0
                    Wrr += Frr * dsStop
                    Waero += Faero * dsStop
                    Wgrav += Fgrav * dsStop
                    KE = 0
                    stalled = True
                    break
            vNew = math.sqrt(2 * KEn / m)
            dt = dsSub / vNew
            legE += Pleg * dt
            t += dt
            Wrr += Frr * dsSub
            Waero += Faero * dsSub
            Wgrav += Fgrav * dsSub
            KE = KEn
            if KE > keCap:
                Wbrake += KE - keCap
                KE = keCap
            remaining -= dsSub
        if stalled:
            break   # cannot proceed at zero power — return the partial, conservative leg
    return {"legE": legE, "t": t, "stalled": stalled}


def approx_components(prof, p, vf, pw):
    """approximate with cf (climbAeroMode='zero'): returns components so ε can vary
    analytically."""
    beta = p["m"] * G / p["keff"]
    mg = p["m"] * G
    w = p["wind"]
    aeroSpd = vf + w
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * aeroSpd * abs(aeroSpd) / p["keff"]
    xs, hs = prof["x"], prof["h"]
    X = hplus = hminus = aeroSum = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        slope = dh / dx
        X += dx
        aeroDx = 0.0 if slope >= CLIMB_THR else aAero   # cf: aero only off climbs
        aeroSum += aeroDx * dx
        if dh >= 0:
            hplus += dh
        else:
            hminus += -dh
    return {"roll": aRoll * X, "aero": aeroSum, "climb": beta * hplus,
            "beta": beta, "hminus": hminus, "X": X, "hplus": hplus}


def build_profile(dist_arr, ele_arr):
    """The .mjs's REDUCED buildProfile: physics profile only (no canvas H[240]
    resample); sets the phys_profile global and returns {total, range, n}."""
    global phys_profile
    X = [dist_arr[0]]
    E = [ele_arr[0]]
    n_in = len(dist_arr)
    for i in range(1, n_in):
        close = dist_arr[i] - X[len(X) - 1] < 0.5
        if close and i < n_in - 1:
            continue
        if close:   # final point: replace, never create dx≈0
            X[len(X) - 1] = dist_arr[i]
            E[len(E) - 1] = ele_arr[i]
        else:
            X.append(dist_arr[i])
            E.append(ele_arr[i])
    base = X[0]
    for i in range(len(X)):
        X[i] -= base
    n = len(X)
    total = X[n - 1]
    if n < 2 or not total > 0:
        raise ValueError("distância nula")
    first = next((i for i, e in enumerate(E) if is_finite(e)), -1)
    if first < 0:
        raise ValueError("faixa sem elevação")
    for i in range(first):
        E[i] = E[first]
    last = first
    for i in range(first + 1, n):
        if is_finite(E[i]):
            for k in range(last + 1, i):
                E[k] = E[last] + (E[i] - E[last]) * (k - last) / (i - last)
            last = i
    for i in range(last + 1, n):
        E[i] = E[last]
    minE = float("inf")
    maxE = float("-inf")
    for e in E:
        if e < minE:
            minE = e
        if e > maxE:
            maxE = e
    px = [X[i] for i in range(n)]
    ph = [E[i] - minE for i in range(n)]
    phys_profile = {"x": px, "h": ph}
    return {"total": total, "range": maxE - minE, "n": n}


def extract_regime_powers(pts, climb_thr, desc_thr):
    """The .mjs's REDUCED copy: dt-weighted MEAN power per regime (plain numbers or
    None — not bem's stats dicts)."""
    W = 30
    bins = ([], [], [])
    VSTOP_L = 0.5 / 3.6
    n = len(pts)
    for i in range(n):
        if pts[i].get("power") is None:
            continue
        if pts[i].get("v") is not None and pts[i]["v"] < VSTOP_L:
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
        bins[r].append({"p": pts[i]["power"], "w": pts[i].get("dt") or 1})

    def stat(b):
        if not b:
            return None
        sw = swp = 0.0
        for s in b:
            sw += s["w"]
            swp += s["w"] * s["p"]
        return swp / sw if sw else None

    return {"descent": stat(bins[0]), "flat": stat(bins[1]), "climb": stat(bins[2])}


# ---- FIT parsing — the .mjs's EXTENDED copy (cadence field + file_id manufacturer) ----

def _reader(buf, little):
    """read(p, bt) closure — out-of-range reads raise (struct.error / IndexError),
    as DataView throws RangeError in JS."""
    e = "<" if little else ">"

    def read(p, bt):
        b = bt & 0x1F
        if b == 0x01:
            v = struct.unpack_from(e + "b", buf, p)[0]
            return None if v == 0x7F else v
        if b in (0x00, 0x02, 0x0A, 0x0D):
            v = buf[p]
            return None if v == 0xFF else v
        if b == 0x03:
            v = struct.unpack_from(e + "h", buf, p)[0]
            return None if v == 0x7FFF else v
        if b in (0x04, 0x0B):
            v = struct.unpack_from(e + "H", buf, p)[0]
            return None if v == 0xFFFF else v
        if b == 0x05:
            v = struct.unpack_from(e + "i", buf, p)[0]
            return None if v == 0x7FFFFFFF else v
        if b in (0x06, 0x0C):
            v = struct.unpack_from(e + "I", buf, p)[0]
            return None if v == 0xFFFFFFFF else v
        if b == 0x08:
            return struct.unpack_from(e + "f", buf, p)[0]
        if b == 0x09:
            return struct.unpack_from(e + "d", buf, p)[0]
        return None  # strings / 64-bit ignored

    return read


def parse_fit(buf):
    global FIT_MANUF
    if len(buf) < 14:
        raise ValueError("FIT muito curto")
    header_size = buf[0]
    data_size = struct.unpack_from("<I", buf, 4)[0]
    if buf[8:12] != b".FIT":
        raise ValueError("no .FIT")
    end = min(header_size + data_size, len(buf))
    FIT_MANUF = None
    pos = header_size
    defs = {}
    records = []
    last_ts = None   # running timestamp for compressed-timestamp headers (5-bit offset, 32 s rollover)
    while pos < end:
        rh = buf[pos]
        pos += 1
        ts_offset = None
        is_def = has_dev = False
        if rh & 0x80:
            local = (rh >> 5) & 0x03
            ts_offset = rh & 0x1F
        else:
            local = rh & 0x0F
            is_def = bool(rh & 0x40)
            has_dev = bool(rh & 0x20)
        if is_def:
            pos += 1
            little = buf[pos] == 0
            pos += 1
            gmn = struct.unpack_from("<H" if little else ">H", buf, pos)[0]
            pos += 2
            nf = buf[pos]
            pos += 1
            fields = []
            for _ in range(nf):
                fields.append((buf[pos], buf[pos + 1], buf[pos + 2]))   # num, size, bt
                pos += 3
            dev_size = 0
            if has_dev:
                nd = buf[pos]
                pos += 1
                for _ in range(nd):
                    dev_size += buf[pos + 1]
                    pos += 3
            defs[local] = {"gmn": gmn, "little": little, "fields": fields,
                           "devSize": dev_size, "read": _reader(buf, little)}
        else:
            d = defs.get(local)
            if d is None:
                raise ValueError("FIT corrompido (dado sem definição)")
            p = pos
            rec = {}
            read = d["read"]
            gmn = d["gmn"]
            for num, size, bt in d["fields"]:
                if gmn == 20:
                    v = read(p, bt)
                    if v is not None:
                        if num == 0:
                            rec["lat"] = v * (180 / 2147483648)
                        elif num == 1:
                            rec["lon"] = v * (180 / 2147483648)
                        elif num == 2:
                            if "alt" not in rec:
                                rec["alt"] = v / 5 - 500
                        elif num == 78:
                            rec["alt"] = v / 5 - 500
                        elif num == 5:
                            rec["dist"] = v / 100
                        elif num == 6:
                            if "speed" not in rec:
                                rec["speed"] = v / 1000
                        elif num == 73:
                            rec["speed"] = v / 1000
                        elif num == 7:
                            rec["power"] = v
                        elif num == 4:
                            rec["cad"] = v          # cadence (rpm) — 0 ⇒ not pedalling
                        elif num == 253:
                            rec["time"] = v
                elif gmn == 0 and num == 1:   # file_id manufacturer (260 = Zwift -> virtual ride)
                    v = read(p, bt)
                    if v is not None:
                        FIT_MANUF = v
                elif num == 253:   # any message's timestamp advances the running clock
                    v = read(p, bt)
                    if v is not None:
                        rec["time"] = v
                p += size
            pos = p + d["devSize"]
            # compressed-timestamp header: reconstruct the time from the 5-bit offset
            if ts_offset is not None and "time" not in rec and last_ts is not None:
                ts = (last_ts & ~31) | ts_offset
                if ts < last_ts:
                    ts += 32
                rec["time"] = ts
            if "time" in rec:
                last_ts = rec["time"]
            if gmn == 20:
                records.append(rec)
    return records


def pts_from_fit(buf):
    recs = parse_fit(buf)
    if len(recs) < 2:
        raise ValueError("FIT sem registros")
    pts = []
    if any("dist" in r for r in recs):
        di, dv = [], []
        for i, r in enumerate(recs):
            if "dist" in r:
                di.append(i)
                dv.append(max(r["dist"], dv[len(dv) - 1]) if dv else r["dist"])   # clip non-monotone
        last_alt = None
        k = 0
        for i, r in enumerate(recs):
            if "alt" in r:
                last_alt = r["alt"]
            if last_alt is None:
                continue
            while k < len(di) - 1 and di[k + 1] <= i:
                k += 1
            if i <= di[0]:
                x = dv[0]
            elif i >= di[len(di) - 1]:
                x = dv[len(dv) - 1]
            else:
                fr = (i - di[k]) / (di[k + 1] - di[k])
                x = dv[k] + (dv[k + 1] - dv[k]) * fr
            pts.append({"x": x, "alt": last_alt, "power": r.get("power"),
                        "cad": r.get("cad"), "t": r.get("time"), "v": r.get("speed")})
    else:
        geo = [r for r in recs if "lat" in r and "lon" in r and "alt" in r]
        if len(geo) < 2:
            raise ValueError("FIT sem distância nem GPS")
        cum = 0.0
        pts.append({"x": 0, "alt": geo[0]["alt"], "power": geo[0].get("power"),
                    "cad": geo[0].get("cad"), "t": geo[0].get("time"), "v": geo[0].get("speed")})
        for i in range(1, len(geo)):
            cum += haversine(geo[i - 1], geo[i])
            pts.append({"x": cum, "alt": geo[i]["alt"], "power": geo[i].get("power"),
                        "cad": geo[i].get("cad"), "t": geo[i].get("time"), "v": geo[i].get("speed")})
    finish_pts(pts)
    return pts


def has_power(pts):
    return any(q.get("power") is not None for q in pts)


def push_stats(pts):
    """Walking/pushing detector (cadence + walking pace). Distance-weighted fractions
    of MOVING distance: push / slow / cadCov."""
    moving = slow = push = cad_known = 0.0
    for i in range(1, len(pts)):
        dx = pts[i]["x"] - pts[i - 1]["x"]
        v = pts[i].get("v")
        cad = pts[i].get("cad")
        if not dx > 0 or v is None or v < 0.5 / 3.6:   # skip standstills
            continue
        moving += dx
        if cad is not None:
            cad_known += dx
        if v < 4 / 3.6:
            slow += dx
            if (cad == 0) if cad is not None else True:
                push += dx
    return {"push": push / moving if moving else 0,
            "slow": slow / moving if moving else 0,
            "cadCov": cad_known / moving if moving else 0}


def climb_balance(pts, p, CLIMB_PCT=0.03, MINLEN=100):
    """Sustained-climb energy balance (verbatim from compare.mjs; Entry 7 machinery)."""
    mg = p["m"] * G
    w = p["wind"]
    out = {"emeas": 0.0, "egrav": 0.0, "eroll": 0.0, "eaero": 0.0,
           "dh": 0.0, "L": 0.0, "n": 0, "totalAsc": 0.0}
    n = len(pts)
    for i in range(1, n):
        d = pts[i]["alt"] - pts[i - 1]["alt"]
        if d > 0:
            out["totalAsc"] += d
    climbing = [0] * n
    j = 0
    for i in range(n):
        while j < n - 1 and pts[j]["x"] - pts[i]["x"] < MINLEN:
            j += 1
        dd = pts[j]["x"] - pts[i]["x"]
        if dd > 1 and (pts[j]["alt"] - pts[i]["alt"]) / dd >= CLIMB_PCT:
            climbing[i] = 1
    s = -1
    for i in range(n + 1):
        if i < n and climbing[i]:
            if s < 0:
                s = i
            continue
        if s < 0:
            continue
        a, b = s, i - 1
        s = -1
        L = pts[b]["x"] - pts[a]["x"]
        dh = pts[b]["alt"] - pts[a]["alt"]
        if L < MINLEN or dh <= 0:
            continue
        emeas = time = 0.0
        for k in range(a, b + 1):
            if pts[k].get("power") is not None:
                emeas += pts[k]["power"] * (pts[k].get("dt") or 0)
            time += pts[k].get("dt") or 0
        v = L / time if time > 0 else 0
        slope = dh / L
        cos = 1 / math.sqrt(1 + slope * slope)
        out["emeas"] += emeas / 1000
        out["egrav"] += mg * dh / p["keff"] / 1000
        out["eroll"] += p["Crr"] * mg * cos * L / p["keff"] / 1000
        out["eaero"] += 0.5 * p["rho"] * p["CdA"] * (v + w) * abs(v + w) * L / p["keff"] / 1000
        out["dh"] += dh
        out["L"] += L
        out["n"] += 1
    return out


def eps_cells_pz(pts, p):
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

    def alt_at(d):
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
def extract_regime_stats(pts, climb_thr, desc_thr):
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

    def mean(b):
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


def descent_eq_speed(Pdesc, sbar, p, vmax):
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


def cell_hpm(prof):
    """30 m-cell profile h± (alternative to regime-binned) — cells like eps_geom."""
    x0 = prof["x"][0]
    total = prof["x"][len(prof["x"]) - 1] - x0
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


def clamp01(v):
    return max(0, min(1, v))


def med_of(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def iqr(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return [float("nan"), float("nan")]

    def q(p):
        return s[math.floor(p * (len(s) - 1))]

    return [q(0.25), q(0.75)]


def corr_of(xs, ys):
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


def read_pts(file):
    with open(os.path.join(DATA, file), "rb") as fh:
        buf = fh.read()
    if file.endswith(".gz"):
        buf = gzip.decompress(buf)
    if file.endswith(".gpx") or file.endswith(".gpx.gz"):
        return pts_from_gpx(buf.decode("utf-8"))
    return pts_from_fit(buf)


# ===== NEW: regime-decomposed closed form =====
def regime_components(prof, p, pw, thr, eps, descent_mode):
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


def regime_totals(prof, p, pw, thr, eps, descent_mode):
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


def r1d_v2_edge(prof, p, pw, climb_thr):
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


def r0_champion(prof, profS, p, pw, eps):
    """R0 champion — smooth (cf + 2 m deadband) AND poor-man's scalar, VERBATIM formulae
    from ppaz_compare.mjs pass B (aSm/aRaw/km/eSm/ePm)."""
    vf = flat_eq_speed(pw["flat"], p)
    beta = p["m"] * G / p["keff"]
    aSm = approx_components(profS, p, vf, pw)
    aRaw = approx_components(prof, p, vf, pw)
    km = (max(0, 1 - 3 * (prof["x"][len(prof["x"]) - 1] / 1000) / aRaw["hplus"])
          if aRaw["hplus"] > 0 else 1)
    eSm = (aSm["roll"] + aSm["aero"] + aSm["climb"] - eps * beta * aSm["hminus"]) / 1000
    ePm = (aRaw["roll"] + aRaw["aero"]
           + km * (aRaw["climb"] - eps * beta * aRaw["hminus"])) / 1000
    return {"eSm": eSm, "ePm": ePm, "vf": vf}


def point_regime_data(pts):
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


def bin_grades(pd, ct, dt):
    bins = ([], [], [])
    for s in pd:
        bins[2 if s["grade"] >= ct else (0 if s["grade"] <= dt else 1)].append(s)

    def stat(b):
        if not b:
            return None
        sw = swp = 0.0
        for s in b:
            sw += s["w"]
            swp += s["w"] * s["p"]
        return swp / sw if sw else None

    return {"descent": stat(bins[0]), "flat": stat(bins[1]), "climb": stat(bins[2])}


def pw_from(rp, pts):
    flat = rp["flat"] if rp["flat"] is not None else overall_mean_power(pts)
    return {"climb": rp["climb"] if rp["climb"] is not None else flat, "flat": flat,
            "descent": rp["descent"] if rp["descent"] is not None else 0}


def d_pct(model, emp):
    return (model - emp) / emp * 100 if emp > 0 else float("nan")


# ===== per-ride processing =====
rows = []
sweep = {"longoes": {}, "censo": {}, "ppaz": {}, "jaam": {}, "danlessa": {}}


def sweep_key(ct, dt):
    return f"{to_fixed(ct * 100, 1)}/{to_fixed(dt * 100, 1)}"


def process_ride(pts, p0, label, corpus, eps_rule):
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
    aSm = approx_components(profS, p, vf, pw)
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
def f(x, d=1):
    if x is None or not is_finite(x):
        return "—"
    return to_fixed(x, d)


def erf(x):
    t = 1 / (1 + 0.3275911 * abs(x))
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
             + 0.254829592) * t * math.exp(-x * x)
    return y if x >= 0 else -y


def p_from_z(z):
    return 2 * (1 - 0.5 * (1 + erf(abs(z) / math.sqrt(2)))) if is_finite(z) else float("nan")


def paired_abs(st, kA, kB):
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


def jquote(s):
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


def cell(v):
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
def run_sanity():
    global R1D_MIN_PRECLAMP

    def approx(a, b, tol=1e-6):
        a = 0 if a is None else a
        b = 0 if b is None else b   # JS numeric coercion of null in Math.abs(a - b)
        return abs(a - b) <= tol * (1 + abs(b))

    pFlat = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0,
             "vmax": VMAX, "vstart": VSTART}

    def mkProf(n, dx, slopeFn):
        x = [0.0] * n
        h = [0.0] * n
        for i in range(n):
            x[i] = float(i * dx)
            h[i] = h[i - 1] + slopeFn(i) * dx if i > 0 else 0.0
        return {"x": x, "h": h}

    ok = [True]

    def say(name, passed, extra=""):
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}{('  ' + extra) if extra else ''}")
        if not passed:
            ok[0] = False

    spts = []
    for i in range(400):
        spts.append({"x": i * 7, "alt": 100 + 20 * _js_sin(i / 15), "power": 150 + (i % 20),
                     "v": 6, "dt": 1})
    rpE = extract_regime_powers(spts, CLIMB_THR, DESC_THR)
    rpB = bin_grades(point_regime_data(spts), CLIMB_THR, DESC_THR)
    say("binGrades ≡ extractRegimePowers",
        all((rpE[k] is None and rpB[k] is None) or approx(rpE[k], rpB[k], 1e-9)
            for k in ("climb", "flat", "descent")))

    prof = mkProf(2001, 5, lambda i: 0.03 * _js_sin(i / 40))
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


def main():
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
                aSm = approx_components(profS, p, flat_eq_speed(overall_mean_power(pts), p), None)
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
    def by_corpus(c):
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

        def g(k, st=st):
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

        def g(k, mk, st=st):
            return med_of([x for x in (abs(r[k]) for r in st if r[mk] > 1) if is_finite(x)])

        print(f"{c.ljust(10)}{f(g('d_rc', 'eMclimb')).rjust(11)}"
              f"{f(g('d_rf', 'eMflat')).rjust(10)}{f(g('d_rd', 'eMdesc')).rjust(10)}")

    # ===== CSV (gitignored via results/*) =====
    csv = "\n".join([",".join(COLS)]
                    + [",".join(cell(r.get(k)) for k in COLS) for r in rows])
    with open(os.path.join(RESULTS, "regime_comparison.csv"), "w", encoding="utf-8") as fh:
        fh.write(csv + "\n")
    print(f"\nwrote regime_comparison.csv ({len(rows)} rides: L {nL} C {nC} P {nP} J {nJ} "
          f"D {nD}, skipped {zwTot} Zwift)")


if __name__ == "__main__":
    main()
