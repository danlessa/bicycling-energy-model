#!/usr/bin/env python3
"""AUTHOR full-export verification — Python port of harness/danlessa_compare.mjs
(same console output, byte-identical CSV). The author's full Strava history
export (strava_danlessa/, gitignored). The external-validity test the
article's §10.4 names as its deepest limitation: every prior number comes
from ONE rider and ONE meter.

Pipeline:
  0. inventory manifest from danlessa_inventory.py; keep sport=ride, power
     coverage >50%, ≥20 km, altitude coverage ≥99%, not Zwift (file_id
     manufacturer 260).
  1. PASS A — implied total mass: invert the sustained-climb energy balance
     (climbBalance; Entry 7 machinery). Headline m̂ = median of per-ride m̂
     over rides with ≥ 200 m of sustained climb.
  2. PASS B — with m̂ frozen: canonical (fed the ride's own regime powers)
     + smooth approx (2 m deadband) + poor-man's scalar, ε swept
     {geom, 0.00…0.25}; physical floor + cadence cross-check.
  3. ε AUTHOR CONSISTENCY TEST (rider 1 — IN-SAMPLE-ish): per-ride ε_bal vs
     geometric ε_coast on 30 m cells, estimators FROZEN from rider 1.

Shared engine/pipeline functions come from src/bicycling_energy_model (the
machine-verified Python port) — including canonical, build_profile and
parse_fit/pts_from_fit (cadence in the points; the file_id manufacturer probe
via the `meta` dict). The .mjs's REDUCED mean-only extractRegimePowers is
covered by the package's full stats version — the call site reads ["mean"]
with the same None fallbacks.

Env overrides as the .mjs: DANLESSA_M (mass-sensitivity runs), DANLESSA_CDA /
DANLESSA_CRR (Entry-15 fitted-physics robustness test).

Reads data/inputs/activities/strava_danlessa_manifest.json (+ gitignored tracks);
writes data/results/danlessa_comparison.csv. Run: python3 src/harness/danlessa_compare.py
"""

from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approx_components, build_profile, canonical,
                                    climb_balance, deadband, empirical_kj,
                                    env_suffix, eps_geom, extract_regime_powers,
                                    flat_eq_speed, is_finite, jsdiv, load_pts,
                                    overall_mean_power, pts_from_fit,
                                    push_stats, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
os.makedirs(RESULTS, exist_ok=True)
VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
# ASSUMED rider physics (same generic values as the censo run) — EXCEPT the mass,
# which pass A estimates from the author's own sustained climbs (M0 = reference
# for the linear inversion). ρ São Paulo ≈ 1.13; wind 0; k_eff 0.98 (repo defaults).
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}
# DANLESSA_CDA / DANLESSA_CRR: swap the generic assumed drag/rolling for the rider's
# own Entry-15 fitted values — the fitted-physics robustness test.
if os.environ.get("DANLESSA_CDA"):
    ASSUMED["CdA"] = float(os.environ["DANLESSA_CDA"])
if os.environ.get("DANLESSA_CRR"):
    ASSUMED["Crr"] = float(os.environ["DANLESSA_CRR"])
M0 = 78                      # reference mass for the climb-balance inversion
MIN_SUSTAINED_DH = 200       # m of sustained climb for a stable per-ride m̂
EPS_SWEEP = [("geom", None), ("0.00", 0.00), ("0.05", 0.05), ("0.10", 0.10),
             ("0.15", 0.15), ("0.20", 0.20), ("0.25", 0.25)]
ZWIFT = 260                  # FIT file_id manufacturer id for Zwift (virtual rides)

phys_profile = None   # the .mjs's `physProfile` global — set at each build_profile call site
FIT_MANUF = None      # file_id manufacturer, set by read_pts per file (bicycling_energy_model parse_fit meta)


# ---- harness-specific helpers ----

def has_power(pts: list[dict]) -> bool:
    return any(q.get("power") is not None for q in pts)


def eps_cells_pz(pts: list[dict], p: dict) -> dict | None:
    """Descent 30 m cells: ε_bal AND the geometric ε_coast/s̄ in one pass
    (adapted from compare.mjs's epsFromBalance; the ε_coast accumulation
    mirrors eps_hypothesis.mjs)."""
    if not pts or len(pts) < 2:
        return None
    mg = p["m"] * G
    beta = mg / p["keff"]
    VSTOP = 0.5 / 3.6
    x0 = pts[0]["x"]
    totalM = pts[-1]["x"] - x0
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

man = json.load(open(os.path.join(DATA, "strava_danlessa_manifest.json")))
CAND = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
        and a["km"] >= 20 and a["altCov"] >= 0.99]
print(f"AUTHOR (danlessa) FULL-EXPORT VERIFICATION — {len(CAND)} candidate rides "
      "(ride, power>50%, ≥20 km, alt≥99%)")


def read_pts(file: str) -> list[dict]:
    global FIT_MANUF
    meta = {}
    pts = load_pts(os.path.join(DATA, file), meta)
    FIT_MANUF = meta["manufacturer"]
    return pts


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
                MH.append(jsdiv(M0 * (cb["emeas"] - cb["eaero"]), cb["egrav"] + cb["eroll"]))
    except Exception:
        unparse += 1


def med_of(xs: list[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def q(xs: list[float], p: float) -> float:
    s = sorted(x for x in xs if is_finite(x))
    return s[math.floor(p * (len(s) - 1))] if s else float("nan")


mGlobal = jsdiv(M0 * (SA["emeas"] - SA["eaero"]), SA["egrav"] + SA["eroll"])
mHat = med_of(MH)
print(f"skipped: {zwift} Zwift/virtual, {unparse} unparseable\n")
print("IMPLIED TOTAL MASS — sustained-climb balance (≥3% over ≥100 m), CdA/Crr/ρ assumed as censo")
print(f"  {SA['n']} sections over {len(usable)} rides, Σ sustained Δh = {math.floor(SA['dh'] + 0.5)} m")
print(f"  global (energy-weighted) m̂ = {to_fixed(mGlobal, 1)} kg")
print(f"  per-ride median m̂ = {to_fixed(mHat, 1)} kg  "
      f"[IQR {to_fixed(q(MH, .25), 1)}–{to_fixed(q(MH, .75), 1)}, n={len(MH)}]")
M_USE = float(os.environ["DANLESSA_M"]) if os.environ.get("DANLESSA_M") else mHat   # DANLESSA_M env: mass-sensitivity runs
print(f"  → using m = {to_fixed(M_USE, 1)} kg "
      + ("(DANLESSA_M override)" if os.environ.get("DANLESSA_M")
         else "(per-ride median; robust to power dropouts)") + "\n")

# ---- PASS B: full model comparison + ε cells, with m̂ frozen ----
rows = []
done = 0
for a in usable:
    try:
        pts = read_pts(a["file"])
        info = build_profile([qq["x"] for qq in pts], [qq["alt"] for qq in pts])
        phys_profile = {"x": info["x"], "h": info["h"]}
        prof = resample_profile(phys_profile, ENGINE_DX)
        profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
        pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
              "flat": flat,
              "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        p = {**ASSUMED, "m": M_USE, "vmax": VMAX, "vstart": VSTART}
        vf = flat_eq_speed(pw["flat"], p)
        beta = p["m"] * G / p["keff"]
        emp = empirical_kj(pts)
        c = canonical(prof, pw, p)
        aRaw = approx_components(prof, p, vf, CLIMB_THR)
        aSm = approx_components(profS, p, vf, CLIMB_THR)
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


def f(x: float | None, d: int = 1) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "—"
    return to_fixed(x, d)


clean = [r for r in rows if r["dataOK"]]
flagged = [r for r in rows if not r["dataOK"]]


def stat(key: str) -> dict:
    v = [x for x in (abs(r[key]) for r in clean) if is_finite(x)]
    s = [x for x in (r[key] for r in clean) if is_finite(x)]
    total = 0.0
    for x in s:
        total += x
    return {"n": len(v), "medAbs": med_of(v), "medSigned": med_of(s),
            "mean": total / len(s) if s else float("nan")}


def print_row(lab: str, key: str) -> None:
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

# ---- ε AUTHOR CONSISTENCY TEST (the out-of-sample result) ----
eOK = [r for r in clean if is_finite(r["epsBal"]) and is_finite(r["epsCoast"])]


def rms(xs: list[float]) -> float:
    s = 0.0
    for x in xs:
        s += x * x
    return math.sqrt(s / len(xs))


def corr_of(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = 0.0
    for x in xs:
        mx += x
    mx /= n
    my = 0.0
    for y in ys:
        my += y
    my /= n
    sxy = sxx = syy = 0.0
    for i in range(n):
        sxy += (xs[i] - mx) * (ys[i] - my)
        sxx += (xs[i] - mx) ** 2
        syy += (ys[i] - my) ** 2
    return jsdiv(sxy, math.sqrt(sxx * syy))


print("\n================================================================")
print("ε AUTHOR CONSISTENCY TEST (rider 1 — the −0.13 offset was calibrated on this rider, "
      "so this is IN-SAMPLE-ish) — estimators FROZEN from rider 1 (nothing refit)")
for lab, sub in [("all clean rides", eOK), ("s̄ ≥ 3%", [r for r in eOK if r["sbar"] >= 0.03])]:
    if len(sub) < 5:
        continue
    eb = [r["epsBal"] for r in sub]
    ecst = [r["epsCoast"] for r in sub]
    flatIn = med_of(eb)
    print(f"\n  -- {lab} (n={len(sub)}) --")
    print(f"  med ε_bal {f(med_of(eb), 2)} · med ε_coast {f(med_of(ecst), 2)} · "
          f"med s̄ {f(med_of([r['sbar'] for r in sub]) * 100, 1)}% · corr {f(corr_of(ecst, eb), 2)}")
    print("  RMS(ε_bal − pred):")
    print("    frozen  ε_coast − 0.13 (unclamped)      "
          f"{f(rms([r['epsBal'] - (r['epsCoast'] - 0.13) for r in sub]), 3)}")
    print(f"    frozen  flat ε = 0.20                {f(rms([x - 0.20 for x in eb]), 3)}")
    print(f"    frozen  flat ε = 0.23                {f(rms([x - 0.23 for x in eb]), 3)}")
    print(f"    in-sample flat = median ε_bal ({f(flatIn, 2)})  "
          f"{f(rms([x - flatIn for x in eb]), 3)}   <- author's own best constant")

# ---- flagged + CSV ----
if flagged:
    print(f"\nFLAGGED (excluded) — ∫P·dt below climbing PE (n={len(flagged)}); "
          f"cadence coverage medians: {f(med_of([r['cadCov'] for r in flagged]) * 100, 0)}%")
cols = list(rows[0].keys())


def cell(v: object) -> str:
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "true" if v else "false"
    if is_finite(v):
        return js_str(float(to_fixed(v, 3)))
    if v is None:
        return "null"
    return js_str(v)   # NaN / ±Infinity


csv_text = "\n".join([",".join(cols)]
                     + [",".join(cell(r[k]) for k in cols) for r in rows])
CSV_NAME = f"danlessa_comparison{env_suffix('DANLESSA_M', 'DANLESSA_CDA', 'DANLESSA_CRR')}.csv"
with open(os.path.join(RESULTS, CSV_NAME), "w") as fh:
    fh.write(csv_text + "\n")
print(f"\nwrote {CSV_NAME} ({len(rows)} rides)")
