#!/usr/bin/env python3
"""THIRD-RIDER verification (JAAM) — Python port of harness/jaam_compare.mjs
(same console output, byte-identical CSV). JAAM's Strava history export
(strava_jaam/, gitignored — third-party GPS shared with consent) is the
external-validity test the article's §10.4 names as its deepest limitation:
every prior number comes from ONE rider and ONE meter.

Pipeline (the .mjs's engines are verbatim copies of censo_compare.mjs):
  0. inventory manifest from jaam_inventory; keep sport=ride, power coverage
     >50%, ≥20 km, altitude coverage ≥99%, not Zwift (file_id manufacturer 260).
  1. PASS A — implied total mass: invert the sustained-climb energy balance
     (climbBalance, verbatim from compare.mjs; Entry 7 machinery).
  2. PASS B — with m̂ frozen: canonical (fed the ride's own regime powers) +
     smooth approx (2 m deadband) + poor-man's scalar, ε swept {geom,
     0.00…0.25}; the censo physical floor + cadence cross-check.
  3. ε THIRD-RIDER TEST: per-ride ε_bal vs geometric ε_coast on 30 m cells,
     estimators FROZEN from the first rider — nothing refit.

Shared engine/pipeline functions come from src/bicycling_energy_model (the
machine-verified Python port) — including canonical, build_profile and
pts_from_fit (cadence field and the file_id manufacturer probe, via the meta
dict). The .mjs's mean-only extractRegimePowers is the package's full-stats
version read at ["mean"] (identical numbers).

Env: JAAM_M (frozen-mass override), JAAM_CDA / JAAM_CRR (Entry-15 fitted
physics), exactly as the .mjs.

Reads data/inputs/activities/strava_jaam_manifest.json (+ gitignored tracks);
writes data/results/jaam_comparison.csv. Run: python3 src/harness/jaam_compare.py
"""

from __future__ import annotations

import json
import math
import os
import random
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
# which pass A estimates from JAAM's own sustained climbs (m0 = reference for the
# linear inversion). ρ São Paulo ≈ 1.13; wind 0; k_eff 0.98 (repo defaults).
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}


def js_plus(s: str) -> float:
    """Unary + on an env string (JS number coercion; NaN on garbage)."""
    try:
        return float(s.strip() or "0")
    except ValueError:
        return float("nan")


# JAAM_CDA / JAAM_CRR: swap the generic assumed drag/rolling for the rider's own Entry-15 fitted
# values — the fitted-physics robustness test (do the conclusions survive the right constants?).
if os.environ.get("JAAM_CDA"):
    ASSUMED["CdA"] = js_plus(os.environ["JAAM_CDA"])
if os.environ.get("JAAM_CRR"):
    ASSUMED["Crr"] = js_plus(os.environ["JAAM_CRR"])
M0 = 78                       # reference mass for the climb-balance inversion
MIN_SUSTAINED_DH = 200        # m of sustained climb for a stable per-ride m̂
EPS_SWEEP = [("geom", None), ("0.00", 0.00), ("0.05", 0.05), ("0.10", 0.10),
             ("0.15", 0.15), ("0.20", 0.20), ("0.25", 0.25)]
ZWIFT = 260                   # FIT file_id manufacturer id for Zwift (virtual rides)

phys_profile = None   # the .mjs's `physProfile` global — set at the build_profile call site


# ---- .mjs-local engine copies, ported faithfully ----

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

man = json.load(open(os.path.join(DATA, "strava_jaam_manifest.json")))
CAND = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
        and a["km"] >= 20 and a["altCov"] >= 0.99]
print(f"JAAM THIRD-RIDER VERIFICATION — {len(CAND)} candidate rides (ride, power>50%, ≥20 km, alt≥99%)")


def read_pts(file: str) -> tuple[list[dict], int | None]:
    """Returns (pts, manufacturer) — manufacturer is the file_id probe the
    .mjs kept in the FIT_MANUF global (260 = Zwift)."""
    meta = {}
    pts = load_pts(os.path.join(DATA, file), meta)
    return pts, meta["manufacturer"]


# ---- PASS A: implied total mass from the sustained-climb balance ----
p0 = {**ASSUMED, "m": M0}
MH = []                             # per-ride m̂
SA = {"emeas": 0.0, "egrav": 0.0, "eroll": 0.0, "eaero": 0.0, "dh": 0.0, "n": 0}
zwift = 0
unparse = 0
usable = []
for a in CAND:
    try:
        pts, manuf = read_pts(a["file"])
        if manuf == ZWIFT:
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


def med_of(xs: list[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def q(xs: list[float], p: float) -> float:
    s = sorted(x for x in xs if is_finite(x))
    return s[math.floor(p * (len(s) - 1))] if s else float("nan")


mGlobal = M0 * jsdiv(SA["emeas"] - SA["eaero"], SA["egrav"] + SA["eroll"])
mHat = med_of(MH)
print(f"skipped: {zwift} Zwift/virtual, {unparse} unparseable\n")
print("IMPLIED TOTAL MASS — sustained-climb balance (≥3% over ≥100 m), CdA/Crr/ρ assumed as censo")
print(f"  {SA['n']} sections over {len(usable)} rides, Σ sustained Δh = {math.floor(SA['dh'] + 0.5)} m")
print(f"  global (energy-weighted) m̂ = {to_fixed(mGlobal, 1)} kg")
print(f"  per-ride median m̂ = {to_fixed(mHat, 1)} kg  "
      f"[IQR {to_fixed(q(MH, .25), 1)}–{to_fixed(q(MH, .75), 1)}, n={len(MH)}]")
M_USE = js_plus(os.environ["JAAM_M"]) if os.environ.get("JAAM_M") else mHat   # JAAM_M env: mass-sensitivity runs
print(f"  → using m = {to_fixed(M_USE, 1)} kg "
      f"{'(JAAM_M override)' if os.environ.get('JAAM_M') else '(per-ride median; robust to power dropouts)'}\n")

# ---- PASS B: full model comparison + ε cells, with m̂ frozen ----
rows = []
done = 0
for a in usable:
    try:
        pts, _manuf = read_pts(a["file"])
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
               "medAlt": a["medAlt"], "ascentPerKm": a["ascentPerKm"],   # non-locational terrain/altitude tags (Note 3)
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
    s = [r[key] for r in clean if is_finite(r[key])]
    total = 0.0
    for x in s:
        total += x
    return {"n": len(v), "medAbs": med_of(v), "medSigned": med_of(s),
            "mean": total / len(s) if s else float("nan")}


def print_row(lab: str, key: str) -> None:
    st = stat(key)
    print(lab.ljust(34) + str(st["n"]).rjust(4) + f(st["medAbs"]).rjust(9)
          + f(st["medSigned"]).rjust(8) + f(st["mean"]).rjust(8))


print(f"\nHEADLINE on {len(clean)} clean rides ({len(flagged)} excluded by the physical floor).")
print(f"geometry: dist median {f(med_of([r['dist_km'] for r in clean]))} km · "
      f"h₊ median {f(med_of([r['hplus'] for r in clean]), 0)} m · "
      f"v_f median {f(med_of([r['vf_kmh'] for r in clean]))} km/h · "
      f"ε_geom median {f(med_of([r['epsG'] for r in clean]), 2)}\n")
print("Δ% vs empirical (− = under, + = over):")
print("model".ljust(34) + "n".rjust(4) + "med|Δ%|".rjust(9) + "medΔ%".rjust(8) + "meanΔ%".rjust(8))
print_row("canonical (fed ride powers)", "canon_d")
print("  -- smooth approx (2 m deadband) --")
for t, _ in EPS_SWEEP:
    print_row(f"  smooth · ε={t}", f"sm_{t}")
print("  -- poor-man's (scalar k_smooth) --")
for t, _ in EPS_SWEEP:
    print_row(f"  poor-man's · ε={t}", f"pm_{t}")

# ---- ε THIRD-RIDER TEST (the out-of-sample result) ----
eOK = [r for r in clean if is_finite(r["epsBal"]) and is_finite(r["epsCoast"])]


def clamp01(x: float) -> float:
    if x != x:
        return x   # Math.max/min propagate NaN
    return max(0, min(1, x))


def rms(xs: list[float]) -> float:
    t = 0.0
    for x in xs:
        t += x * x
    return math.sqrt(jsdiv(t, len(xs)))


def corr_of(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = my = 0.0
    for x in xs:
        mx += x
    mx /= n
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
print("ε THIRD-RIDER TEST — estimators FROZEN from rider 1 (nothing refit)")
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
    print(f"    frozen  ε_coast − 0.13 (unclamped)      "
          f"{f(rms([r['epsBal'] - (r['epsCoast'] - 0.13) for r in sub]), 3)}")
    print(f"    frozen  flat ε = 0.20                {f(rms([x - 0.20 for x in eb]), 3)}")
    print(f"    frozen  flat ε = 0.23                {f(rms([x - 0.23 for x in eb]), 3)}")
    print(f"    in-sample flat = median ε_bal ({f(flatIn, 2)})  "
          f"{f(rms([x - flatIn for x in eb]), 3)}   <- JAAM's own best constant")

# ---- TERRAIN / GEOGRAPHY STRATIFICATION (Note 3: JAAM spans SP + a non-SP tail,
#      plain ↔ mountainous). Does the FROZEN estimator hold off the São Paulo band? ----
# Paired bootstrap on the RMS DIFFERENCE (frozen − flat 0.20) over the real-descent
# subset.  Entry 14 quotes this CI as the reason the subset is "inconclusive rather
# than a tie", but until now no harness emitted it — it was computed ad hoc, so it
# could not be regenerated when the subset moved (it shifted from n=21 to n=20 in the
# Entry-27 re-baseline).  Deterministic seed, percentile method, same B as bootstrap_ci.
_real = [r for r in eOK if r["sbar"] >= 0.03]
if len(_real) >= 5:
    _froz = [r["epsBal"] - (r["epsCoast"] - 0.13) for r in _real]
    _flat = [r["epsBal"] - 0.20 for r in _real]
    _rnd = random.Random(20260725)
    _n, _B, _bs = len(_real), 10000, []
    for _ in range(_B):
        _idx = [_rnd.randrange(_n) for _ in range(_n)]
        _bs.append(rms([_froz[i] for i in _idx]) - rms([_flat[i] for i in _idx]))
    _bs.sort()
    _lo, _hi = _bs[int(0.025 * _B)], _bs[int(0.975 * _B) - 1]
    print(f"\n  paired bootstrap on RMS(frozen) − RMS(flat 0.20), real descents (n={_n}): "
          f"{rms(_froz) - rms(_flat):+.3f} "
          f"[95% CI {_lo:+.3f}, {_hi:+.3f}] · straddles zero: {_lo < 0 < _hi} "
          f"(percentile, B=10⁴, seed 20260725)")

print("\n----------------------------------------------------------------")
print("TERRAIN / GEOGRAPHY CUTS — frozen ε_coast−0.13 (unclamped), real descents (s̄ ≥ 3%)")
print("note: JAAM power rides are ~93% São Paulo (medAlt ~737 m); the non-SP tail is small.")
real = [r for r in eOK if r["sbar"] >= 0.03]
cuts = [
    ("São Paulo band (600–1000 m)",
     [r for r in real if r["medAlt"] is not None and 600 <= r["medAlt"] < 1000]),
    ("non-SP altitude (<600 or ≥1000 m)",
     [r for r in real if r["medAlt"] is not None and (r["medAlt"] < 600 or r["medAlt"] >= 1000)]),
    ("plain (ascent < 8 m/km)",
     [r for r in real if r["ascentPerKm"] is not None and r["ascentPerKm"] < 8]),
    ("hilly (ascent ≥ 8 m/km)",
     [r for r in real if r["ascentPerKm"] is not None and r["ascentPerKm"] >= 8]),
]
print("cut".ljust(34) + "n".rjust(4) + "RMS frozen".rjust(12) + "RMS in-samp".rjust(12) + "med ε_bal".rjust(11))
for lab, sub in cuts:
    if len(sub) < 3:
        print("  " + lab.ljust(32) + str(len(sub)).rjust(4) + "  (too few)")
        continue
    eb = [r["epsBal"] for r in sub]
    rFrozen = rms([r["epsBal"] - (r["epsCoast"] - 0.13) for r in sub])
    rIn = rms([x - med_of(eb) for x in eb])
    print("  " + lab.ljust(32) + str(len(sub)).rjust(4) + f(rFrozen, 3).rjust(12)
          + f(rIn, 3).rjust(12) + f(med_of(eb), 2).rjust(11))

# ---- flagged + CSV ----
if flagged:
    print(f"\nFLAGGED (excluded) — ∫P·dt below climbing PE (n={len(flagged)}); "
          f"cadence coverage medians: {f(med_of([r['cadCov'] for r in flagged]) * 100, 0)}%")


def cell(v: object) -> str:
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "true" if v else "false"           # Array.join(boolean)
    if isinstance(v, (int, float)):
        if math.isfinite(v):
            return js_str(float(to_fixed(v, 3)))  # +Number(x).toFixed(3)
        return js_str(v)                          # NaN / ±Infinity
    if v is None:
        return ""                                 # Array.join(null) -> ''
    return str(v)


cols = list(rows[0].keys())
csv_text = "\n".join([",".join(cols)]
                     + [",".join(cell(r.get(k)) for k in cols) for r in rows])
CSV_NAME = f"jaam_comparison{env_suffix('JAAM_M', 'JAAM_CDA', 'JAAM_CRR')}.csv"
with open(os.path.join(RESULTS, CSV_NAME), "w", encoding="utf-8") as fh:
    fh.write(csv_text + "\n")
print(f"\nwrote {CSV_NAME} ({len(rows)} rides)")
