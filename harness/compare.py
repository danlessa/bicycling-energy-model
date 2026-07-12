#!/usr/bin/env python3
"""Longões model comparison — canonical vs approximate vs empirical ∫P·dt.

Python port of the retired compare.mjs (same output, byte-identical CSV and
report). The engines and parsers come from analysis/bem — the line-by-line
port of the app's JS whose equivalence is machine-checked by
analysis/parity/run_parity.py against the frozen JS reference.

Reads data/activities/model_inputs.json (+ the gitignored tracks); writes
results/model_comparison.csv. Run: python3 harness/compare.py
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))

from bem import (approximate, ascent_hyst, build_profile, canonical, deadband,
                 empirical_kj, eps_from_balance, extract_regime_powers,
                 flat_eq_speed, load_pts, measured_flat_speed,
                 overall_mean_power, resample_profile)
from bem.jsfmt import to_exponential, to_fixed

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
os.makedirs(RESULTS, exist_ok=True)

G = 9.81
VMAX, VSTART = 38 / 3.6, 15 / 3.6            # app defaults (km/h -> m/s)
CLIMB_THR, DESC_THR, ENGINE_DX = 0.02, -0.015, 5
TAU_SMOOTH = 2   # elevation deadband threshold (m) — rejects sub-tau jitter in h+


# ---- compare-specific helpers (ported verbatim from compare.mjs) ----

def empirical_by_regime(pts, climb_thr, desc_thr):
    """Empirical ∫P·dt split by the LOCAL grade over a 30 m window — same
    thresholds as canonical/extractRegimePowers. Sums to the total empirical."""
    W = 30
    by_reg = {"climb": 0.0, "flat": 0.0, "descent": 0.0}
    n = len(pts)
    for i in range(n):
        if pts[i].get("power") is None:
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
        e = pts[i]["power"] * (pts[i].get("dt") or 0)
        if grade >= climb_thr:
            by_reg["climb"] += e
        elif grade <= desc_thr:
            by_reg["descent"] += e
        else:
            by_reg["flat"] += e
    return by_reg


def climb_fraction(prof, thr):
    """Fraction of horizontal distance ridden on climbs (slope >= thr)."""
    xs, hs = prof["x"], prof["h"]
    X = Xc = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        X += dx
        if (hs[i] - hs[i - 1]) / dx >= thr:
            Xc += dx
    return Xc / X if X > 0 else 0


def climb_balance(pts, p, CLIMB_PCT=0.03, MINLEN=100):
    """Sustained-climb energy balance (Danilo's method for fitting k_h cleanly):
    on sections climbing >= CLIMB_PCT over >= MINLEN m, compare the MEASURED
    sum P·dt to the EXPECTED gravity + rolling + aero."""
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


# ---- per-ride loop ----

inputs = json.load(open(os.path.join(DATA, "model_inputs.json")))
rows = []
# energy-weighted per-regime totals across rides (kJ); *S = elevation-smoothed
REG = {rg: {k: 0.0 for k in ("emp", "canon", "off", "cf", "canonS", "offS", "cfS")}
       for rg in ("climb", "flat", "descent")}
# elevation-noise accounting: sum ascent (m) at smoothing levels + climb-gravity energy (kJ)
TAUS = [0, 1, 2, 3, 5, 10]
ELEV = {"h": {t: 0.0 for t in TAUS}, "eng": 0.0, "engS": 0.0, "gravRaw": 0.0, "grav3": 0.0,
        "bySrc": {"rwgps_trip": {"raw": 0.0, "h3": 0.0}, "strava": {"raw": 0.0, "h3": 0.0}}}
KH = []          # per-ride heuristic-study rows
CONS = {"max": 0.0, "ride": None}   # worst per-ride conservation residual (must stay <= 1e-6)
SC = {"emeas": 0.0, "egrav": 0.0, "eroll": 0.0, "eaero": 0.0, "dh": 0.0, "L": 0.0,
      "n": 0, "totalAsc": 0.0, "perRide": []}   # sustained-climb energy balance

for e in inputs:
    if not e.get("file") or not e.get("has_power"):
        continue
    try:
        fp = os.path.join(DATA, e["file"])
        pts = load_pts(fp)
        phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
        prof = resample_profile(phys, ENGINE_DX)
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        stat = lambda s: rp[s]["mean"] if rp[s]["mean"] is not None else 0
        flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
        pw = {"climb": stat("climb"), "flat": flat, "descent": stat("descent"),
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        p = {"m": e["m"], "Crr": e["crr"], "CdA": e["cda"], "rho": e["rho"], "keff": e["keff"],
             "vmax": VMAX, "vstart": VSTART, "wind": (e.get("wind_kmh") or 0) / 3.6}
        # v_f from the EXTRACTED flat power (grade-binned mean) — the harness default
        vf = flat_eq_speed(pw["flat"], p)
        # v_f from the SHEET's P_flat/P_avg term (P_flat = ratio * <W>_mes, both from the sheet)
        pAvg = overall_mean_power(pts)
        pFlatSheet = (e["pflat_pavg"] * e["wmes"]
                      if e.get("pflat_pavg") is not None and e.get("wmes") is not None
                      else pw["flat"])
        vfSheet = flat_eq_speed(pFlatSheet, p)
        opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                            "descThr": DESC_THR, "climbPower": pw["climb"]}
        aOff = approximate(prof, p, vf, e["eps"], opt("off"))    # current: full v_f aero everywhere
        aCf = approximate(prof, p, vf, e["eps"], opt("zero"))    # climb-fraction aero
        aVc = approximate(prof, p, vf, e["eps"], opt("vc"))      # near-exact: climb aero at v_c
        aCfSheet = approximate(prof, p, vfSheet, e["eps"], opt("zero"))
        ms = measured_flat_speed(pts)
        vfMeas = ms if ms else vf                                # measured flat ground speed
        aCfMeas = approximate(prof, p, vfMeas, e["eps"], opt("zero"))
        c = canonical(prof, pw, p)
        # machine-check the conservation identity per ride
        consResid = abs(p["keff"] * c["legE"]
                        - (c["dKE"] + c["Wrr"] + c["Waero"] + c["Wgrav"] + c["Wbrake"])) \
            / max(1, p["keff"] * c["legE"])
        if consResid > 1e-6:
            print(f"CONSERVATION VIOLATION {e['label']}: rel resid {to_exponential(consResid, 2)}",
                  file=sys.stderr)
        if consResid > CONS["max"]:
            CONS["max"] = consResid
            CONS["ride"] = e["label"]
        # same engines on the elevation-deadband-SMOOTHED profile (same pw, vf, params)
        profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
        aOffS = approximate(profS, p, vf, e["eps"], opt("off"))
        aCfS = approximate(profS, p, vf, e["eps"], opt("zero"))
        cS = canonical(profS, pw, p)
        # k_smooth: scalar poor-man's deadband on the RAW-profile gravity term (notas v2)
        km = max(0, 1 - 3 * (prof["x"][-1] / 1000) / aCf["hplus"]) if aCf["hplus"] > 0 else 1
        eKsmooth = aCf["roll"] + aCf["aero"] + km * (aCf["climb"] + aCf["recov"])   # J
        emp = empirical_kj(pts)                                                     # kJ
        # fit eps per ride against the SMOOTHENED model (k_h=1, deadband h±)
        betaR = e["m"] * G / e["keff"]
        bHm = betaR * aCfS["hminus"]
        epsFit = ((aCfS["roll"] + aCfS["aero"] + aCfS["climb"] - emp * 1000) / bHm
                  if bHm > 1e-6 else float("nan"))
        epsBal = eps_from_balance(pts, p)   # descent-energy-balance eps
        empReg = empirical_by_regime(pts, CLIMB_THR, DESC_THR)
        for rg in ("climb", "flat", "descent"):
            REG[rg]["emp"] += empReg[rg] / 1000
            REG[rg]["canon"] += c["legEByReg"][rg] / 1000
            REG[rg]["off"] += aOff["EByReg"][rg] / 1000
            REG[rg]["cf"] += aCf["EByReg"][rg] / 1000
            REG[rg]["canonS"] += cS["legEByReg"][rg] / 1000
            REG[rg]["offS"] += aOffS["EByReg"][rg] / 1000
            REG[rg]["cfS"] += aCfS["EByReg"][rg] / 1000
        # elevation-noise: ascent on the NATIVE profile at each hysteresis threshold
        beta = e["m"] * G / e["keff"]
        hN = phys["h"]
        for t in TAUS:
            ELEV["h"][t] += ascent_hyst(hN, t)
        ELEV["eng"] += aOff["hplus"]     # what the engine actually used (5 m grid raw)
        ELEV["engS"] += aOffS["hplus"]   # h+ after the deadband filter
        hRaw = ascent_hyst(hN, 0)
        h3 = ascent_hyst(hN, 3)
        ELEV["gravRaw"] += beta * hRaw / 1000
        ELEV["grav3"] += beta * h3 / 1000
        hpSm = ascent_hyst(deadband(hN, TAU_SMOOTH), 0)
        xkm = prof["x"][-1] / 1000
        KH.append({"ride": e["label"], "xkm": xkm, "hpRaw": hRaw, "hpSm": hpSm,
                   "c": (hRaw - hpSm) / xkm, "kh": hpSm / hRaw, "hilly": hRaw / xkm})
        # sustained-climb energy balance (Danilo's k_h fit)
        cb = climb_balance(pts, p)
        for k in ("emeas", "egrav", "eroll", "eaero", "dh", "L", "n", "totalAsc"):
            SC[k] += cb[k]
        if cb["egrav"] > 0:
            SC["perRide"].append({"ride": e["label"],
                                  "kh": (cb["emeas"] - cb["eroll"] - cb["eaero"]) / cb["egrav"],
                                  "frac": cb["dh"] / cb["totalAsc"]})
        sk = "strava" if e.get("source") == "strava" else "rwgps_trip"
        if sk in ELEV["bySrc"]:
            ELEV["bySrc"][sk]["raw"] += hRaw
            ELEV["bySrc"][sk]["h3"] += h3
        kj = lambda j: j / 1000
        dlt = lambda j: (kj(j) - emp) / emp * 100
        rows.append({
            "ride": e["label"], "source": e.get("source"),
            "dist_km": prof["x"][-1] / 1000,
            "climb_frac": climb_fraction(prof, CLIMB_THR),
            "empirical": emp, "canonical": kj(c["legE"]),
            "approx_off": kj(aOff["E"]), "approx_cf": kj(aCf["E"]), "approx_vc": kj(aVc["E"]),
            "approx_cf_sheet": kj(aCfSheet["E"]),
            "canon_vs_emp": dlt(c["legE"]), "off_vs_emp": dlt(aOff["E"]),
            "cf_vs_emp": dlt(aCf["E"]), "vc_vs_emp": dlt(aVc["E"]),
            "cfsheet_vs_emp": dlt(aCfSheet["E"]), "cfmeas_vs_emp": dlt(aCfMeas["E"]),
            "canonS_vs_emp": dlt(cS["legE"]), "offS_vs_emp": dlt(aOffS["E"]),
            "cfS_vs_emp": dlt(aCfS["E"]),
            "ksmooth_vs_emp": dlt(eKsmooth), "eps_sheet": e["eps"], "eps_fit": epsFit,
            "eps_bal": epsBal,
            "p_avg": pAvg, "wmes": e.get("wmes"), "pflat_extracted": pw["flat"],
            "pflat_sheet": pFlatSheet,
            "data_ratio": pw["flat"] / e["wmes"] if e.get("wmes") else None,
            "sheet_ratio": e.get("pflat_pavg"),
            "vf_kmh": vf * 3.6, "vf_sheet_kmh": vfSheet * 3.6, "vf_meas_kmh": vfMeas * 3.6,
            "pClimb": pw["climb"], "pFlat": pw["flat"], "pDescent": pw["descent"],
        })
    except Exception as err:
        rows.append({"ride": e["label"], "source": e.get("source"), "error": str(err)})


# ---- console report (byte-identical to the JS output) ----

def f(x, d=0):
    if x is None or (isinstance(x, float) and x != x):
        return "—"
    return to_fixed(x, d)


def med(xs):
    s = sorted(xs)
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


print("Δ% vs empirical ∫P·dt   (off = current; cf = climb-fraction aero; vc = climb aero at v_c)")
print("RIDE".ljust(22) + "dist".rjust(5) + "cl%".rjust(5) + "emp".rjust(7) + "  "
      + "canon".rjust(6) + "off".rjust(6) + "cf".rjust(6) + "vc".rjust(6))
print("-" * 64)
for r in rows:
    if r.get("error"):
        print(f"{r['ride'][:22].ljust(22)}  ERROR: {r['error']}")
        continue
    print(r["ride"][:22].ljust(22) + f(r["dist_km"], 0).rjust(5) + f(r["climb_frac"] * 100, 0).rjust(5)
          + f(r["empirical"], 0).rjust(7) + "  " + f(r["canon_vs_emp"], 1).rjust(6)
          + f(r["off_vs_emp"], 1).rjust(6) + f(r["cf_vs_emp"], 1).rjust(6) + f(r["vc_vs_emp"], 1).rjust(6))

good = [r for r in rows if not r.get("error")]


def stats(key):
    v = [abs(r[key]) for r in good if is_finite(r[key])]
    signed = [r[key] for r in good if is_finite(r[key])]
    total = 0.0
    for x in signed:
        total += x
    return {"n": len(v), "medAbs": med(v), "medSigned": med(signed),
            "mean": total / len(signed) if signed else float("nan")}


print("=" * 64)
print("model vs empirical".ljust(30) + "n".rjust(4) + "med|Δ%|".rjust(9) + "medΔ%".rjust(8) + "meanΔ%".rjust(8))
for lab, key in [("canonical (forward sim)", "canon_vs_emp"), ("approx off (current)", "off_vs_emp"),
                 ("approx climb-fraction (cf)", "cf_vs_emp"), ("approx near-exact v_c", "vc_vs_emp"),
                 ("approx cf + sheet v_f", "cfsheet_vs_emp"), ("approx cf + measured v_f", "cfmeas_vs_emp"),
                 (f"canonical + {TAU_SMOOTH} m smooth", "canonS_vs_emp"),
                 (f"approx off + {TAU_SMOOTH} m smooth", "offS_vs_emp"),
                 (f"approx cf + {TAU_SMOOTH} m smooth", "cfS_vs_emp")]:
    s = stats(key)
    print(lab.ljust(30) + str(s["n"]).rjust(4) + f(s["medAbs"], 1).rjust(9)
          + f(s["medSigned"], 1).rjust(8) + f(s["mean"], 1).rjust(8))
print(f"median climb fraction: {f(med([r['climb_frac'] for r in good]) * 100, 0)}%")
dr = [r["data_ratio"] for r in good if is_finite(r["data_ratio"])]
sr = [r["sheet_ratio"] for r in good if is_finite(r["sheet_ratio"])]
print(f"P_flat/<W>_mes — data(extracted): median {f(med(dr), 2)}  ·  sheet(AB): median {f(med(sr), 2)}  (n_sheet={len(sr)})")
print(f"v_f — extracted flatEqSpeed: {f(med([r['vf_kmh'] for r in good]), 1)}  ·  "
      f"sheet-derived: {f(med([r['vf_sheet_kmh'] for r in good]), 1)}  ·  "
      f"measured flat: {f(med([r['vf_meas_kmh'] for r in good]), 1)} km/h (medians)")

# ---- per-regime breakdown (energy-weighted totals across rides, kJ) ----
totEmp = REG["climb"]["emp"] + REG["flat"]["emp"] + REG["descent"]["emp"]
print("\n" + "=" * 64)
print("PER-REGIME energy (Σ over rides, kJ) and Δ% vs empirical ∫P·dt")
print("regime".ljust(9) + "share".rjust(6) + "emp".rjust(8) + "canon".rjust(8) + "off".rjust(8)
      + "cf".rjust(8) + "   " + "canonΔ%".rjust(8) + "offΔ%".rjust(7) + "cfΔ%".rjust(7))
print("-" * 74)
for rg in ("climb", "flat", "descent"):
    r = REG[rg]
    d = lambda m: (m - r["emp"]) / r["emp"] * 100 if r["emp"] else float("nan")
    print(rg.ljust(9) + f(r["emp"] / totEmp * 100, 0).rjust(5) + "%"
          + f(r["emp"], 0).rjust(8) + f(r["canon"], 0).rjust(8) + f(r["off"], 0).rjust(8)
          + f(r["cf"], 0).rjust(8) + "   "
          + f(d(r["canon"]), 1).rjust(8) + f(d(r["off"]), 1).rjust(7) + f(d(r["cf"]), 1).rjust(7))

# ---- elevation noise in h+ ----
print("\n" + "=" * 64)
print("ELEVATION NOISE — total ascent h+ (km, Σ over rides) vs hysteresis threshold")
hraw = ELEV["h"][0]
print("smoothing".ljust(18) + "Σ h+ (km)".rjust(10) + "% of raw".rjust(9))
for t in TAUS:
    print(("raw (every step)" if t == 0 else f"hysteresis {t} m").ljust(18)
          + f(ELEV["h"][t] / 1000, 1).rjust(10) + f(ELEV["h"][t] / hraw * 100, 0).rjust(8) + "%")
print(f"engine (5 m grid)  {f(ELEV['eng'] / 1000, 1).rjust(8)}{f(ELEV['eng'] / hraw * 100, 0).rjust(8)}%"
      "   <- what approximate's beta*h+ uses")
noiseKJ = ELEV["gravRaw"] - ELEV["grav3"]
print(f"\nClimb-gravity energy beta*h+ : raw {f(ELEV['gravRaw'], 0)} kJ -> 3 m-smoothed {f(ELEV['grav3'], 0)} kJ")
print(f"noise in h+ (raw - 3 m): {f(ELEV['h'][0] - ELEV['h'][3], 0)} m total = {f(noiseKJ, 0)} kJ"
      f" = {f(noiseKJ / REG['climb']['emp'] * 100, 0)}% of empirical CLIMB energy, "
      f"{f(noiseKJ / totEmp * 100, 1)}% of total")
for sk in ("rwgps_trip", "strava"):
    s = ELEV["bySrc"][sk]
    print(f"  {sk.ljust(11)} raw->3 m shrink: {f((1 - s['h3'] / s['raw']) * 100, 0)}% "
          f"(raw {f(s['raw'] / 1000, 1)} km -> {f(s['h3'] / 1000, 1)} km)")

# ---- effect of the 3 m elevation filter ----
print("\n" + "=" * 64)
print(f"APPLYING THE {TAU_SMOOTH} m ELEVATION FILTER — engine h+ "
      f"{f(ELEV['eng'] / 1000, 1)} km -> {f(ELEV['engS'] / 1000, 1)} km")
print("metric".ljust(26) + "raw".rjust(9) + "+filter".rjust(9))
climbD = lambda k: ((REG["climb"][k] - REG["climb"]["emp"]) / REG["climb"]["emp"] * 100
                    if REG["climb"]["emp"] else float("nan"))
print("CLIMB energy Δ% — canon".ljust(26) + f(climbD("canon"), 1).rjust(9) + f(climbD("canonS"), 1).rjust(9))
print("CLIMB energy Δ% — off".ljust(26) + f(climbD("off"), 1).rjust(9) + f(climbD("offS"), 1).rjust(9))
print("CLIMB energy Δ% — cf".ljust(26) + f(climbD("cf"), 1).rjust(9) + f(climbD("cfS"), 1).rjust(9))
medSign = lambda k: med([r[k] for r in good if is_finite(r[k])])
print("TOTAL median Δ% — canon".ljust(26) + f(medSign("canon_vs_emp"), 1).rjust(9) + f(medSign("canonS_vs_emp"), 1).rjust(9))
print("TOTAL median Δ% — off".ljust(26) + f(medSign("off_vs_emp"), 1).rjust(9) + f(medSign("offS_vs_emp"), 1).rjust(9))
print("TOTAL median Δ% — cf".ljust(26) + f(medSign("cf_vs_emp"), 1).rjust(9) + f(medSign("cfS_vs_emp"), 1).rjust(9))

# ---- low-compute heuristic for k_h (no profile, only totals h+, x) ----
print("\n" + "=" * 64)
print("HEURISTIC for k_h from totals only — target = deadband-smoothed h+")
cMed = med([r["c"] for r in KH])          # spurious ascent rate (m/km)
khMed = med([r["kh"] for r in KH])        # constant-k_h fallback
print(f"spurious ascent rate c = h+_raw - h+_smooth per km:  median {f(cMed, 1)} m/km  "
      f"(IQR {f(med([r['c'] for r in KH if r['c'] < cMed]), 1)}–{f(med([r['c'] for r in KH if r['c'] > cMed]), 1)})")
print(f"constant k_h (smooth/raw):  median {f(khMed, 2)}  "
      f"(range {f(min(r['kh'] for r in KH), 2)}–{f(max(r['kh'] for r in KH), 2)})")
errConstKh = [abs(khMed * r["hpRaw"] - r["hpSm"]) / r["hpSm"] for r in KH]
errRate = [abs(max(0, r["hpRaw"] - cMed * r["xkm"]) - r["hpSm"]) / r["hpSm"] for r in KH]
print("\nheuristic h+_corr vs true smoothed h+ — median |rel err|:")
print(f"  (A) constant k_h = {f(khMed, 2)}                 : {f(med(errConstKh) * 100, 1)}%")
print(f"  (B) subtract rate: h+ - {f(cMed, 1)}·x_km        : {f(med(errRate) * 100, 1)}%   <- physics-based")
print(f"implied k_h(hilliness) = 1 - c/(h+/x):  flat ride 30 m/km -> {f(1 - cMed / 30, 2)},  "
      f"hilly 150 m/km -> {f(1 - cMed / 150, 2)}")

# ---- sustained-climb energy balance (the clean k_h fit) ----
print("\n" + "=" * 64)
print("SUSTAINED-CLIMB ENERGY BALANCE — sections ≥3% over ≥100 m (measured vs expected)")
SCexp = SC["egrav"] + SC["eroll"] + SC["eaero"]
print(f"  {SC['n']} climb sections over {len(SC['perRide'])} rides; sustained Δh = {f(SC['dh'], 0)} m "
      f"= {f(SC['dh'] / SC['totalAsc'] * 100, 0)}% of total ascent")
print(f"  measured Σ∫P·dt on climbs : {f(SC['emeas'], 0)} kJ")
print(f"  expected (grav+roll+aero) : {f(SCexp, 0)} kJ   "
      f"(grav {f(SC['egrav'], 0)} + roll {f(SC['eroll'], 0)} + aero {f(SC['eaero'], 0)})")
print(f"  measured / expected       : {f(SC['emeas'] / SCexp, 2)}")
print(f"  k_h(sustained) = (measured − roll − aero) / gravity = "
      f"{f((SC['emeas'] - SC['eroll'] - SC['eaero']) / SC['egrav'], 2)}")
khs = sorted(r["kh"] for r in SC["perRide"] if is_finite(r["kh"]))
print(f"  per-ride k_h(sustained): median {f(med(khs), 2)}  [{f(khs[0], 2)}–{f(khs[-1], 2)}]")

# ---- cross-comparison: canonical vs smoothed vs k_smooth ----
print("\n" + "=" * 64)
print("CROSS-COMPARISON vs empirical ∫P·dt (≈ sheet Work Bike), 44 rides")
print("model".ljust(34) + "n".rjust(3) + "med|Δ%|".rjust(9) + "medΔ%".rjust(8) + "meanΔ%".rjust(8))
for lab, key in [("canonical (forward sim)", "canon_vs_emp"),
                 (f"smoothed (cf + real {TAU_SMOOTH} m deadband)", "cfS_vs_emp"),
                 ("k_smooth (cf + scalar, no smoothing)", "ksmooth_vs_emp")]:
    s = stats(key)
    print(lab.ljust(34) + str(s["n"]).rjust(3) + f(s["medAbs"], 1).rjust(9)
          + f(s["medSigned"], 1).rjust(8) + f(s["mean"], 1).rjust(8))

# ---- fitted eps per ride (smoothed model) vs the sheet's g_d_eff ----
print("\n" + "=" * 64)
print("ε per ride: sheet g_d_eff · whole-ride fit (smoothed) · descent-energy-balance (epsFromFIT)")
print("ride".ljust(26) + "sheet".rjust(7) + "fit".rjust(7) + "balance".rjust(9))
for r in good:
    print(r["ride"][:25].ljust(26) + f(r["eps_sheet"], 2).rjust(7) + f(r["eps_fit"], 2).rjust(7)
          + f(r["eps_bal"], 2).rjust(9))
efit = sorted(r["eps_fit"] for r in good if is_finite(r["eps_fit"]))
ebal = sorted(r["eps_bal"] for r in good if is_finite(r["eps_bal"]))
print(f"median: sheet {f(med([r['eps_sheet'] for r in good]), 2)}  "
      f"fit {f(med(efit), 2)} [{f(efit[0], 2)}..{f(efit[-1], 2)}]  "
      f"balance {f(med(ebal), 2)} [{f(ebal[0], 2)}..{f(ebal[-1], 2)}]")

# ---- csv ----
cols = ["ride", "source", "dist_km", "climb_frac", "empirical", "canonical", "approx_off",
        "approx_cf", "approx_vc", "approx_cf_sheet", "canon_vs_emp", "off_vs_emp", "cf_vs_emp",
        "vc_vs_emp", "cfsheet_vs_emp", "cfmeas_vs_emp", "cfS_vs_emp", "canonS_vs_emp",
        "ksmooth_vs_emp", "p_avg", "wmes", "pflat_extracted", "pflat_sheet", "data_ratio",
        "sheet_ratio", "vf_kmh", "vf_sheet_kmh", "vf_meas_kmh", "pClimb", "pFlat", "pDescent",
        "error"]


def cell(v):
    if v is None:
        return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if isinstance(v, float) and v != v:
            return "NaN"
        if float(v).is_integer():
            return str(int(v))
        return to_fixed(v, 2)
    return f'"{v}"'


csv_text = "\n".join([",".join(cols)]
                     + [",".join(cell(r.get(c)) for c in cols)
                        for r in good + [r for r in rows if r.get("error")]])
with open(os.path.join(RESULTS, "model_comparison.csv"), "w") as fh:
    fh.write(csv_text + "\n")
print(f"\nwrote model_comparison.csv ({len(good)} rides)")
print(f"conservation identity: worst per-ride rel residual {to_exponential(CONS['max'], 2)} "
      f"({CONS['ride'] if CONS['ride'] is not None else '—'}) — must stay ≤ 1e-6")
