#!/usr/bin/env python3
"""Censo Hidrográfico model verification — Python port of harness/censo_compare.mjs
(same output, byte-identical CSV and report). For each downloaded ride
(censohidrografico/), run the three energy models on the ride's OWN track and
compare to the measured ∫P·dt:
  canonical        — forward sim, fed the ride's FIT-extracted climb/flat/descent powers
  smooth approx    — α_r·x + α_a·x_flat + β(h₊−ε·h₋) on a 2 m deadband-SMOOTHED profile
  poor-man's       — same, raw profile, gravity scaled by k_smooth = 1 − 0.003·x/h₊

Per the rules: every factual quantity is DERIVED from the activity (geometry,
regime powers, v_f, ∫P·dt). Only the rider physics is assumed (m, CdA, Crr,
paved, ρ, wind, k_eff) and ε is swept: closed-form ε_geom (notas) AND constants
0.20 / 0.25.

Shared engine/pipeline functions come from analysis/bem (the machine-verified
Python port). The .mjs's own REDUCED or EXTENDED copies (canonical without
bookkeeping, buildProfile without the canvas resample, mean-only
extractRegimePowers, parseFIT/ptsFromFIT with the cadence field) are ported
locally below, faithfully.

Reads data/activities/censohidrografico/manifest.json (+ gitignored tracks);
writes results/censo_comparison.csv. Run: python3 harness/censo_compare.py
"""

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
# ASSUMED rider (Danilo's note): 78 kg, CdA 0.40, Crr 0.008, 100% paved.
# ρ for São Paulo (~760 m, ~22 °C) ≈ 1.13; wind 0; k_eff 0.98 (repo default).
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}
EPS_SWEEP = [("geom", None), ("0.00", 0.00), ("0.05", 0.05), ("0.10", 0.10),
             ("0.15", 0.15), ("0.20", 0.20), ("0.25", 0.25)]

phys_profile = None   # set by build_profile (the .mjs's `physProfile` global)


def is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


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
    vary analytically (harness-specific)."""
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


# ---- FIT parsing — the .mjs's EXTENDED copy (adds the cadence field) ----
# Structure mirrors bem.fit (the parity-verified port), plus f.num === 4 → cad
# and this harness's own signature error message ('no .FIT').

def _reader(buf, little):
    e = "<" if little else ">"

    def read(p, bt):
        b = bt & 0x1F
        try:
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
        except struct.error:
            return None
        return None  # strings / 64-bit ignored

    return read


def parse_fit(buf):
    if len(buf) < 14:
        raise ValueError("FIT muito curto")
    header_size = buf[0]
    data_size = struct.unpack_from("<I", buf, 4)[0]
    if buf[8:12] != b".FIT":
        raise ValueError("no .FIT")
    end = min(header_size + data_size, len(buf))
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
            for num, size, bt in d["fields"]:
                if d["gmn"] == 20:
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
            if d["gmn"] == 20:
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


# ===== driver =====

man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
rows = []
for e in man:
    if not e.get("file"):
        continue
    fp = os.path.join(DATA, e["file"])
    if not os.path.exists(fp):
        continue
    try:
        with open(fp, "rb") as fh:
            buf = fh.read()
        pts = pts_from_fit(buf)
        if not has_power(pts):
            continue                                    # benchmark needs power
        build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
        prof = resample_profile(phys_profile, ENGINE_DX)
        profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        flat = rp["flat"] if rp["flat"] is not None else overall_mean_power(pts)
        pw = {"climb": rp["climb"] if rp["climb"] is not None else flat, "flat": flat,
              "descent": rp["descent"] if rp["descent"] is not None else 0,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        p = {**ASSUMED, "vmax": VMAX, "vstart": VSTART}
        vf = flat_eq_speed(pw["flat"], p)
        beta = p["m"] * G / p["keff"]
        emp = empirical_kj(pts)                         # kJ benchmark
        c = canonical(prof, pw, p)
        aRaw = approx_components(prof, p, vf, pw)       # poor-man's base (raw)
        aSm = approx_components(profS, p, vf, pw)       # smooth base (deadband)
        km = (max(0, 1 - 3 * (prof["x"][-1] / 1000) / aRaw["hplus"])
              if aRaw["hplus"] > 0 else 1)              # k_smooth
        epsG = eps_geom(prof, p, vf)
        # Physical floor: pedalling energy MUST cover the (momentum-corrected, deadband-smoothed)
        # climbing potential energy mg·h₊_sm/k_eff. A measured ∫P·dt below it means the route was
        # NOT fully pedalled — a power-meter dropout OR the riders walked/pushed up steep climbs
        # (no pedalling → ~0 W while still ascending). Either way the cycling model over-predicts
        # by design, so these are excluded from the headline. walkFrac tells the two apart.
        peFloor = beta * aSm["hplus"] / 1000            # kJ
        dataOK = emp >= peFloor
        ps = push_stats(pts)
        row = {"ride": e.get("name"), "source": e.get("source"),
               "dist_km": prof["x"][-1] / 1000,
               "hplus": aRaw["hplus"], "hplus_sm": aSm["hplus"], "emp": emp,
               "peFloor": peFloor, "dataOK": dataOK, "push": ps["push"],
               "slow": ps["slow"], "cadCov": ps["cadCov"], "epsG": epsG, "km": km,
               "vf_kmh": vf * 3.6, "canon": c["legE"] / 1000,
               "canon_d": (c["legE"] / 1000 - emp) / emp * 100}
        for tag, ev in EPS_SWEEP:
            eps = (epsG if is_finite(epsG) else 0.2) if ev is None else ev
            eSm = (aSm["roll"] + aSm["aero"] + aSm["climb"] - eps * beta * aSm["hminus"]) / 1000             # smooth approx
            ePm = (aRaw["roll"] + aRaw["aero"] + km * (aRaw["climb"] - eps * beta * aRaw["hminus"])) / 1000  # poor-man's
            row[f"sm_{tag}"] = (eSm - emp) / emp * 100
            row[f"pm_{tag}"] = (ePm - emp) / emp * 100
        rows.append(row)
    except Exception:
        pass   # skip unparseable


def f(x, d=1):
    if x is None or (isinstance(x, float) and x != x):
        return "—"
    return to_fixed(x, d)


def med(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def jmin(xs):   # Math.min(...xs): NaN-propagating
    m = float("inf")
    for x in xs:
        if x != x:
            return float("nan")
        if x < m:
            m = x
    return m


def jmax(xs):   # Math.max(...xs): NaN-propagating
    m = float("-inf")
    for x in xs:
        if x != x:
            return float("nan")
        if x > m:
            m = x
    return m


clean = [r for r in rows if r["dataOK"]]                # headline = physically-plausible power streams
flagged = [r for r in rows if not r["dataOK"]]          # emp < climbing PE ⇒ dropouts in the power data


def stat(key):
    v = [x for x in (abs(r[key]) for r in clean) if is_finite(x)]
    s = [x for x in (r[key] for r in clean) if is_finite(x)]
    total = 0.0
    for x in s:
        total += x
    return {"n": len(v), "medAbs": med(v), "medSigned": med(s),
            "mean": total / len(s) if s else float("nan")}


print(f"CENSO HIDROGRÁFICO — {len(rows)} rides w/ power · benchmark = measured ∫P·dt")
print(f"assumed rider: m={js_str(ASSUMED['m'])} CdA={js_str(ASSUMED['CdA'])} "
      f"Crr={js_str(ASSUMED['Crr'])} ρ={js_str(ASSUMED['rho'])} wind={js_str(ASSUMED['wind'])} "
      f"k_eff={js_str(ASSUMED['keff'])} (100% paved)")
print(f"EXCLUDED {len(flagged)} rides with measured ∫P·dt < climbing PE (mg·h₊_sm/k_eff) — route not fully pedalled (dropout or walking).")
print(f"HEADLINE on {len(clean)} clean rides. geometry: dist median {f(med([r['dist_km'] for r in clean]))} km · "
      f"h₊ median {f(med([r['hplus'] for r in clean]), 0)} m · v_f median {f(med([r['vf_kmh'] for r in clean]))} km/h · "
      f"ε_geom median {f(med([r['epsG'] for r in clean]), 2)}")

print("\nΔ% vs empirical (− = under, + = over):")
print("model".ljust(34) + "n".rjust(4) + "med|Δ%|".rjust(9) + "medΔ%".rjust(8) + "meanΔ%".rjust(8))


def print_row(lab, key):
    s = stat(key)
    print(lab.ljust(34) + str(s["n"]).rjust(4) + f(s["medAbs"]).rjust(9)
          + f(s["medSigned"]).rjust(8) + f(s["mean"]).rjust(8))


print_row("canonical (fed ride powers)", "canon_d")
print("  -- smooth approx (2 m deadband) --")
for tag, _ in EPS_SWEEP:
    print_row(f"  smooth · ε={tag}", f"sm_{tag}")
print("  -- poor-man's (scalar k_smooth) --")
for tag, _ in EPS_SWEEP:
    print_row(f"  poor-man's · ε={tag}", f"pm_{tag}")

# ε-sensitivity: spread of medΔ% across the ε sweep, per approximate model
smSpread = [stat(f"sm_{t}")["medSigned"] for t, _ in EPS_SWEEP]
pmSpread = [stat(f"pm_{t}")["medSigned"] for t, _ in EPS_SWEEP]
print(f"\nε-sensitivity (medΔ% range over ε∈{{{','.join(t for t, _ in EPS_SWEEP)}}}):")
print(f"  smooth approx : {f(jmin(smSpread))} … {f(jmax(smSpread))}  (spread {f(jmax(smSpread) - jmin(smSpread))} pp)")
print(f"  poor-man's    : {f(jmin(pmSpread))} … {f(jmax(pmSpread))}  (spread {f(jmax(pmSpread) - jmin(pmSpread))} pp)")

# flagged rides (bad power data) — shown for transparency, not used in the headline
print("\nFLAGGED (excluded) — measured ∫P·dt below climbing PE ⇒ not fully pedalled.")
print("  push% = moving dist <4 km/h & cadence 0 (on foot); slow% = <4 km/h; cad% = cadence coverage:")
for r in sorted(flagged, key=lambda r: r["emp"] / r["peFloor"]):
    print(f"  {r['ride'][:30].ljust(30)} emp={f(r['emp'], 0)}kJ floor={f(r['peFloor'], 0)}kJ "
          f"({f(r['emp'] / r['peFloor'] * 100, 0)}%)  push={f(r['push'] * 100, 0)}% "
          f"slow={f(r['slow'] * 100, 0)}% cad={f(r['cadCov'] * 100, 0)}%  cΔ={f(r['canon_d'], 0)}%")

# csv (gitignored)
cols = (["ride", "source", "dist_km", "hplus", "emp", "peFloor", "dataOK", "push", "slow",
         "cadCov", "epsG", "km", "vf_kmh", "canon", "canon_d"]
        + [c for t, _ in EPS_SWEEP for c in (f"sm_{t}", f"pm_{t}")])


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return f'"{"true" if v else "false"}"'
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v != v:
            return to_fixed(v, 3)   # NaN, as JS NaN.toFixed(3)
        if float(v).is_integer():
            return str(int(v))
        return to_fixed(v, 3)
    return f'"{v}"'


csv_text = "\n".join([",".join(cols)]
                     + [",".join(cell(r.get(c)) for c in cols) for r in rows])
with open(os.path.join(RESULTS, "censo_comparison.csv"), "w") as fh:
    fh.write(csv_text + "\n")
print(f"\nwrote results/censo_comparison.csv ({len(rows)} rides)")
