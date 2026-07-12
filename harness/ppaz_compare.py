#!/usr/bin/env python3
"""SECOND-RIDER verification — Python port of harness/ppaz_compare.mjs (same
console report, byte-identical CSV). P. Paz's Strava history export
(strava_ppaz/, gitignored — third-party GPS shared with consent). The
external-validity test the article's §10.4 names as its deepest limitation:
every prior number comes from ONE rider and ONE meter.

Pipeline (engines are verbatim copies of censo_compare.mjs — keep the copies in sync):
  0. inventory manifest from ppaz_inventory.py; keep sport=ride, power coverage >50%,
     ≥20 km, altitude coverage ≥99%, not Zwift (file_id manufacturer 260).
  1. PASS A — implied total mass: invert the sustained-climb energy balance
     (climbBalance, verbatim from compare.mjs; Entry 7 machinery). On sustained climbs
     measured ≈ (grav+roll)·(m/m0) + aero, all but aero linear in m, so
     m̂ = m0·(emeas − eaero)/(egrav + eroll). Headline m̂ = median of per-ride m̂ over
     rides with ≥ 200 m of sustained climb (robust to power dropouts).
  2. PASS B — with m̂ frozen: canonical (fed the ride's own regime powers) + smooth
     approx (2 m deadband) + poor-man's scalar, ε swept {geom, 0.00…0.25}; the censo
     physical floor (∫P·dt ≥ m̂·g·h₊_sm/k_eff) + cadence cross-check.
  3. ε SECOND-RIDER TEST: per-ride descent-balance ε_bal vs geometric ε_coast on 30 m
     cells (α at the MEASURED flat speed, VSTOP-gated). The estimators are FROZEN from
     the first rider: clamp01(ε_coast − 0.13), flat 0.20, flat 0.23. Nothing here is
     refit — this is out-of-sample across rider, meter, and terrain.

  python3 harness/ppaz_inventory.py && python3 harness/ppaz_compare.py

Shared engine/pipeline functions come from analysis/bem (the machine-verified
Python port): haversine, flatEqSpeed, resampleProfile, epsGeom, finishPts,
deadband, empiricalKJ, overallMeanPower. The .mjs's own REDUCED or EXTENDED
copies (canonical without bookkeeping, buildProfile without the canvas
resample, mean-only extractRegimePowers, parseFIT/ptsFromFIT with the cadence
field AND the file_id manufacturer capture) plus the harness-specific
approxComponents / climbBalance / epsCellsPz / pushStats are ported locally
below, faithfully.

Output: console report + ppaz_comparison.csv (gitignored via results/*).
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

from bem import (deadband, empirical_kj, eps_geom, finish_pts, flat_eq_speed,
                 haversine, overall_mean_power, resample_profile)
from bem.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
os.makedirs(RESULTS, exist_ok=True)
G = 9.81
VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
# ASSUMED rider physics (same generic values as the censo run) — EXCEPT the mass,
# which pass A estimates from P. Paz's own sustained climbs (m0 = reference for the
# linear inversion). ρ São Paulo ≈ 1.13; wind 0; k_eff 0.98 (repo defaults).
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}


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


# PPAZ_CDA / PPAZ_CRR: swap the generic assumed drag/rolling for the rider's own Entry-15 fitted
# values — the fitted-physics robustness test (do the conclusions survive the right constants?).
if os.environ.get("PPAZ_CDA"):
    ASSUMED["CdA"] = jnum(os.environ["PPAZ_CDA"])
if os.environ.get("PPAZ_CRR"):
    ASSUMED["Crr"] = jnum(os.environ["PPAZ_CRR"])

M0 = 78                      # reference mass for the climb-balance inversion
MIN_SUSTAINED_DH = 200       # m of sustained climb for a stable per-ride m̂
EPS_SWEEP = [("geom", None), ("0.00", 0.00), ("0.05", 0.05), ("0.10", 0.10),
             ("0.15", 0.15), ("0.20", 0.20), ("0.25", 0.25)]
ZWIFT = 260                  # FIT file_id manufacturer id for Zwift (virtual rides)

phys_profile = None   # set by build_profile (the .mjs's `physProfile` global)
FIT_MANUF = None      # file_id manufacturer, set by parse_fit per file


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


# ---- .mjs-local engine copies, ported faithfully ----

def canonical(prof, pw, p):
    """Forward-dynamics sim — the .mjs's REDUCED copy (no per-regime/speed
    bookkeeping; returns legE, t, stalled only). Same dynamics as bem.canonical."""
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
    """approximate with cf (climbAeroMode='zero'): returns components so ε can
    vary analytically."""
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
        close = dist_arr[i] - X[-1] < 0.5
        if close and i < n_in - 1:
            continue
        if close:   # final point: replace, never create dx≈0
            X[-1] = dist_arr[i]
            E[-1] = ele_arr[i]
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
    """The .mjs's REDUCED copy: dt-weighted mean power per regime (plain
    numbers or None — not bem's stats dicts)."""
    W = 30
    bins = ([], [], [])
    VSTOP = 0.5 / 3.6
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
        bins[r].append((pts[i]["power"], pts[i].get("dt") or 1))

    def stat(b):
        if not b:
            return None
        sw = swp = 0.0
        for pwr, w in b:
            sw += w
            swp += w * pwr
        return swp / sw if sw else None

    return {"descent": stat(bins[0]), "flat": stat(bins[1]), "climb": stat(bins[2])}


# ---- FIT parsing — the .mjs's EXTENDED copy (cadence field + file_id manufacturer) ----
# Structure mirrors bem.fit (the parity-verified port), plus f.num === 4 → cad,
# gmn 0 field 1 → FIT_MANUF, and this harness's own signature error ('no .FIT').

def _reader(buf, little):
    """read(p, bt) closure — out-of-range reads raise (struct.error /
    IndexError), as DataView throws RangeError in JS."""
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
                fields.append((buf[pos], buf[pos + 1], buf[pos + 2]))  # num, size, bt
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
                dv.append(max(r["dist"], dv[-1]) if dv else r["dist"])   # clip non-monotone device distance
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
            elif i >= di[-1]:
                x = dv[-1]
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
        pts.append({"x": 0.0, "alt": geo[0]["alt"], "power": geo[0].get("power"),
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
    """Walking/pushing detector. The clean test is CADENCE (Danilo): pedalling
    ⇔ cadence > 0, so "moving but cadence 0" is not pedalling (coasting or on
    foot); pair it with a walking pace (< 4 km/h — you CAN granny-gear below
    6, so 4 is the bike/foot line) to isolate pushing from coasting. Returns
    distance-weighted fractions of MOVING distance:
      push  — < 4 km/h AND cadence 0 (no sensor ⇒ assume the slow crawl is on foot)
      slow  — < 4 km/h regardless of cadence (speed-only fallback)
      cadCov— cadence-sensor coverage (so push is trustworthy only when this is high)
    """
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
    """Sustained-climb energy balance (verbatim from compare.mjs; Entry 7
    machinery): on sections climbing >= CLIMB_PCT over >= MINLEN m, compare
    the MEASURED sum P·dt to the EXPECTED gravity + rolling + aero."""
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
    """Descent 30 m cells: ε_bal AND the geometric ε_coast/s̄ in one pass
    (adapted from compare.mjs's epsFromBalance; the ε_coast accumulation
    mirrors eps_hypothesis.mjs)."""
    if not pts or len(pts) < 2:
        return None
    mg = p["m"] * G
    beta = mg / p["keff"]
    VSTOP = 0.5 / 3.6
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
        if r.get("v") is not None and r["v"] >= VSTOP:
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


# ===== driver =====

man = json.load(open(os.path.join(DATA, "strava_ppaz_manifest.json")))
CAND = [a for a in man
        if a["sport"] == "ride" and a["powCov"] > 0.5 and a["km"] >= 20 and a["altCov"] >= 0.99]
print(f"P. PAZ SECOND-RIDER VERIFICATION — {len(CAND)} candidate rides (ride, power>50%, ≥20 km, alt≥99%)")


def read_pts(file):
    with open(os.path.join(DATA, file), "rb") as fh:
        buf = fh.read()
    if file.endswith(".gz"):
        buf = gzip.decompress(buf)
    return pts_from_fit(buf)


# ---- PASS A: implied total mass from the sustained-climb balance ----
p0 = {**ASSUMED, "m": M0}
MH = []                             # per-ride m̂
SA = {"emeas": 0.0, "egrav": 0.0, "eroll": 0.0, "eaero": 0.0, "dh": 0.0, "n": 0}
zwift = unparse = 0
usable = []
for a in CAND:
    try:
        pts = read_pts(a["file"])
        if FIT_MANUF == ZWIFT:
            zwift += 1
            continue
        if not has_power(pts):
            continue
        usable.append(a)
        cb = climb_balance(pts, p0)
        if cb["n"] > 0:
            SA["emeas"] += cb["emeas"]
            SA["egrav"] += cb["egrav"]
            SA["eroll"] += cb["eroll"]
            SA["eaero"] += cb["eaero"]
            SA["dh"] += cb["dh"]
            SA["n"] += cb["n"]
            if cb["dh"] >= MIN_SUSTAINED_DH:
                MH.append(M0 * (cb["emeas"] - cb["eaero"]) / (cb["egrav"] + cb["eroll"]))
    except Exception:
        unparse += 1


def med_of(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def q(xs, p):
    s = sorted(x for x in xs if is_finite(x))
    return s[math.floor(p * (len(s) - 1))] if s else float("nan")


mGlobal = jsdiv(M0 * (SA["emeas"] - SA["eaero"]), SA["egrav"] + SA["eroll"])
mHat = med_of(MH)
print(f"skipped: {zwift} Zwift/virtual, {unparse} unparseable\n")
print("IMPLIED TOTAL MASS — sustained-climb balance (≥3% over ≥100 m), CdA/Crr/ρ assumed as censo")
print(f"  {SA['n']} sections over {len(usable)} rides, Σ sustained Δh = {js_str(math.floor(SA['dh'] + 0.5))} m")
print(f"  global (energy-weighted) m̂ = {to_fixed(mGlobal, 1)} kg")
print(f"  per-ride median m̂ = {to_fixed(mHat, 1)} kg  "
      f"[IQR {to_fixed(q(MH, .25), 1)}–{to_fixed(q(MH, .75), 1)}, n={len(MH)}]")
M_USE = jnum(os.environ["PPAZ_M"]) if os.environ.get("PPAZ_M") else mHat   # PPAZ_M env: mass-sensitivity runs
print(f"  → using m = {to_fixed(M_USE, 1)} kg "
      + ("(PPAZ_M override)" if os.environ.get("PPAZ_M") else "(per-ride median; robust to power dropouts)")
      + "\n")

# ---- PASS B: full model comparison + ε cells, with m̂ frozen ----
rows = []
done = 0
for a in usable:
    try:
        pts = read_pts(a["file"])
        build_profile([qq["x"] for qq in pts], [qq["alt"] for qq in pts])
        prof = resample_profile(phys_profile, ENGINE_DX)
        profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        flat = rp["flat"] if rp["flat"] is not None else overall_mean_power(pts)
        pw = {"climb": rp["climb"] if rp["climb"] is not None else flat, "flat": flat,
              "descent": rp["descent"] if rp["descent"] is not None else 0,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        p = {**ASSUMED, "m": M_USE, "vmax": VMAX, "vstart": VSTART}
        vf = flat_eq_speed(pw["flat"], p)
        beta = p["m"] * G / p["keff"]
        emp = empirical_kj(pts)
        c = canonical(prof, pw, p)
        aRaw = approx_components(prof, p, vf, pw)
        aSm = approx_components(profS, p, vf, pw)
        km = (max(0, 1 - 3 * (prof["x"][-1] / 1000) / aRaw["hplus"])
              if aRaw["hplus"] > 0 else 1)
        epsG = eps_geom(prof, p, vf)
        peFloor = beta * aSm["hplus"] / 1000
        dataOK = emp >= peFloor
        ps = push_stats(pts)
        ec = eps_cells_pz(pts, p)
        row = {"ride": a["id"], "date": a["date"], "dist_km": prof["x"][-1] / 1000,
               "hplus": aRaw["hplus"], "hplus_sm": aSm["hplus"], "emp": emp,
               "peFloor": peFloor, "dataOK": dataOK, "push": ps["push"],
               "slow": ps["slow"], "cadCov": ps["cadCov"],
               "epsG": epsG, "km": km, "vf_kmh": vf * 3.6,
               "epsBal": ec["epsBal"] if ec else float("nan"),
               "epsCoast": ec["epsCoast"] if ec else float("nan"),
               "sbar": ec["sbar"] if ec else float("nan"),
               "Hd": ec["Hd"] if ec else float("nan"),
               "vfMeas_kmh": ec["vf"] * 3.6 if ec else float("nan"),
               "canon": c["legE"] / 1000,
               "canon_d": jsdiv(c["legE"] / 1000 - emp, emp) * 100}
        for tag, ev in EPS_SWEEP:
            eps = (epsG if is_finite(epsG) else 0.2) if ev is None else ev
            eSm = (aSm["roll"] + aSm["aero"] + aSm["climb"] - eps * beta * aSm["hminus"]) / 1000
            ePm = (aRaw["roll"] + aRaw["aero"] + km * (aRaw["climb"] - eps * beta * aRaw["hminus"])) / 1000
            row[f"sm_{tag}"] = jsdiv(eSm - emp, emp) * 100
            row[f"pm_{tag}"] = jsdiv(ePm - emp, emp) * 100
        rows.append(row)
    except Exception:
        pass   # skip
    done += 1
    if done % 100 == 0:
        print(f"  …pass B {done}/{len(usable)}")


def f(x, d=1):
    if x is None or (isinstance(x, float) and x != x):
        return "—"
    return to_fixed(x, d)


clean = [r for r in rows if r["dataOK"]]
flagged = [r for r in rows if not r["dataOK"]]


def stat(key):
    v = [x for x in (abs(r[key]) for r in clean) if is_finite(x)]
    s = [x for x in (r[key] for r in clean) if is_finite(x)]
    total = 0.0
    for x in s:
        total += x
    return {"n": len(v), "medAbs": med_of(v), "medSigned": med_of(s),
            "mean": total / len(s) if s else float("nan")}


def print_row(lab, key):
    s = stat(key)
    print(lab.ljust(34) + str(s["n"]).rjust(4) + f(s["medAbs"]).rjust(9)
          + f(s["medSigned"]).rjust(8) + f(s["mean"]).rjust(8))


print(f"\nHEADLINE on {len(clean)} clean rides ({len(flagged)} excluded by the physical floor).")
print(f"geometry: dist median {f(med_of([r['dist_km'] for r in clean]))} km · "
      f"h₊ median {f(med_of([r['hplus'] for r in clean]), 0)} m · "
      f"v_f median {f(med_of([r['vf_kmh'] for r in clean]))} km/h · "
      f"ε_geom median {f(med_of([r['epsG'] for r in clean]), 2)}\n")
print("Δ% vs empirical (− = under, + = over):")
print("model".ljust(34) + "n".rjust(4) + "med|Δ%|".rjust(9) + "medΔ%".rjust(8) + "meanΔ%".rjust(8))
print_row("canonical (fed ride powers)", "canon_d")
print("  -- smooth approx (2 m deadband) --")
for tag, _ in EPS_SWEEP:
    print_row(f"  smooth · ε={tag}", f"sm_{tag}")
print("  -- poor-man's (scalar k_smooth) --")
for tag, _ in EPS_SWEEP:
    print_row(f"  poor-man's · ε={tag}", f"pm_{tag}")

# ---- ε SECOND-RIDER TEST (the out-of-sample result) ----
eOK = [r for r in clean if is_finite(r["epsBal"]) and is_finite(r["epsCoast"])]


def clamp01(x):
    return max(0, min(1, x))


def rms(xs):
    s = 0.0
    for x in xs:
        s += x * x
    return math.sqrt(jsdiv(s, len(xs)))


def corr_of(xs, ys):
    n = len(xs)
    sx = 0.0
    for x in xs:
        sx += x
    sy = 0.0
    for y in ys:
        sy += y
    mx = sx / n
    my = sy / n
    sxy = sxx = syy = 0.0
    for i in range(n):
        dxi = xs[i] - mx
        dyi = ys[i] - my
        sxy += dxi * dyi
        sxx += dxi * dxi   # (xs[i] - mx) ** 2 — fdlibm pow(x,2) is exactly x*x
        syy += dyi * dyi
    return jsdiv(sxy, math.sqrt(sxx * syy))


print("\n================================================================")
print("ε SECOND-RIDER TEST — estimators FROZEN from rider 1 (nothing refit)")
for lab, sub in (("all clean rides", eOK), ("s̄ ≥ 3%", [r for r in eOK if r["sbar"] >= 0.03])):
    if len(sub) < 5:
        continue
    eb = [r["epsBal"] for r in sub]
    ecst = [r["epsCoast"] for r in sub]
    flatIn = med_of(eb)
    print(f"\n  -- {lab} (n={len(sub)}) --")
    print(f"  med ε_bal {f(med_of(eb), 2)} · med ε_coast {f(med_of(ecst), 2)} · "
          f"med s̄ {f(med_of([r['sbar'] for r in sub]) * 100, 1)}% · corr {f(corr_of(ecst, eb), 2)}")
    print("  RMS(ε_bal − pred):")
    print(f"    frozen  clamp01(ε_coast − 0.13)      "
          f"{f(rms([r['epsBal'] - clamp01(r['epsCoast'] - 0.13) for r in sub]), 3)}")
    print(f"    frozen  flat ε = 0.20                {f(rms([x - 0.20 for x in eb]), 3)}")
    print(f"    frozen  flat ε = 0.23                {f(rms([x - 0.23 for x in eb]), 3)}")
    print(f"    in-sample flat = median ε_bal ({f(flatIn, 2)})  "
          f"{f(rms([x - flatIn for x in eb]), 3)}   <- P. Paz's own best constant")

# ---- flagged + CSV ----
if flagged:
    print(f"\nFLAGGED (excluded) — ∫P·dt below climbing PE (n={len(flagged)}); "
          f"cadence coverage medians: {f(med_of([r['cadCov'] for r in flagged]) * 100, 0)}%")

_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def jquote(s):
    """JSON.stringify string quoting (as the .mjs CSV writer uses)."""
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
    # typeof 'string' → JSON.stringify; finite number → +Number(v).toFixed(3)
    # (a NUMBER again — integer-valued prints bare); rest → Array.join semantics
    # (true/false, NaN, null → '').
    if isinstance(v, str):
        return jquote(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)) and math.isfinite(v):
        return js_str(float(to_fixed(v, 3)))
    if v is None:
        return ""
    return js_str(v)   # NaN → 'NaN', ±Infinity


cols = list(rows[0].keys())
csv_text = "\n".join([",".join(cols)]
                     + [",".join(cell(r.get(k)) for k in cols) for r in rows])
with open(os.path.join(RESULTS, "ppaz_comparison.csv"), "w", encoding="utf-8") as fh:
    fh.write(csv_text + "\n")
print(f"\nwrote ppaz_comparison.csv ({len(rows)} rides)")
