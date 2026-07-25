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

Shared engine/pipeline functions come from src/bicycling_energy_model (the
machine-verified Python port) — including canonical, build_profile and
pts_from_fit, whose package versions are supersets of the .mjs's
reduced/extended copies (verified bit-identical on this corpus). The former
per-file helpers (is_finite, approx_components, extract_regime_powers,
push_stats) come from the package too; its FULL extract_regime_powers returns
stats dicts whose ["mean"] equals the retired mean-only local copy.

Reads data/inputs/activities/censohidrografico/manifest.json (+ gitignored tracks);
writes data/results/censo_comparison.csv. Run: python3 src/harness/censo_compare.py
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approx_components, build_profile, canonical, deadband,
                                    empirical_kj, eps_geom, extract_regime_powers, flat_eq_speed,
                                    is_finite, overall_mean_power, pts_from_fit, push_stats,
                                    resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
os.makedirs(RESULTS, exist_ok=True)

VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
# ASSUMED rider (Danilo's note): 78 kg, CdA 0.40, Crr 0.008, 100% paved.
# ρ for São Paulo (~760 m, ~22 °C) ≈ 1.13; wind 0; k_eff 0.98 (repo default).
ASSUMED = {"m": 78, "CdA": 0.40, "Crr": 0.008, "rho": 1.13, "keff": 0.98, "wind": 0}
EPS_SWEEP = [("geom", None), ("0.00", 0.00), ("0.05", 0.05), ("0.10", 0.10),
             ("0.15", 0.15), ("0.20", 0.20), ("0.25", 0.25)]

phys_profile = None   # the .mjs's `physProfile` global — set at the build_profile call site


def has_power(pts):
    return any(q.get("power") is not None for q in pts)


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
        info = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
        phys_profile = {"x": info["x"], "h": info["h"]}
        prof = resample_profile(phys_profile, ENGINE_DX)
        profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
        pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat, "flat": flat,
              "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        p = {**ASSUMED, "vmax": VMAX, "vstart": VSTART}
        vf = flat_eq_speed(pw["flat"], p)
        beta = p["m"] * G / p["keff"]
        emp = empirical_kj(pts)                         # kJ benchmark
        c = canonical(prof, pw, p)
        aRaw = approx_components(prof, p, vf, CLIMB_THR)   # poor-man's base (raw)
        aSm = approx_components(profS, p, vf, CLIMB_THR)   # smooth base (deadband)
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
print(f"\nwrote data/results/censo_comparison.csv ({len(rows)} rides)")
