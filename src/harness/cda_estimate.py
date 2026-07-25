#!/usr/bin/env python3
"""Independent m / C_rr / CdA estimation for the shared riders (journal Entry 15)
— Python port of the retired cda_estimate.mjs (same console report, byte-identical
data/results/cda_estimate.csv).

The clean signal is the CLIMB: on a positive slope braking is negligible, so the
work–energy balance over an uphill segment is exact and linear in (m, C_rr·m, CdA):
    E_i = m·A_i + (C_rr·m)·B_i + CdA·C_i
      A_i = g·Δh_i + ½·Δ(v²)_i     B_i = g·Δx_i     C_i = ½·ρ·Σ(v³·dt)_i
      E_i = k_eff·Σ(P·dt)_i
A 3-parameter no-intercept least squares over many climb segments returns all three
with no assumed value for any of them (see the .mjs comment block for the rationale).

    python3 src/harness/cda_estimate.py

Shared pipeline pieces come from src/bicycling_energy_model (the machine-verified
Python port): pts_from_fit (whose EXTENDED parseFIT — cadence field 4 + file_id
manufacturer — now lives in bicycling_energy_model) and finish_pts. Ported locally:
  - haversine — same arithmetic as reference.mjs, on math.sin/cos/asin.
  - ptsFromGPX — verbatim body, but must call the haversine above.
The .mjs also carries 14 functions that the driver never calls (flatEqSpeed,
resampleProfile, canonical, approxComponents, buildProfile, extractRegimePowers,
deadband, empiricalKJ, overallMeanPower, hasPower, pushStats, epsGeom,
climbBalance, epsCellsPz — dead copies kept for the engine-sync rule); they cannot
affect the output and are not reproduced here.

Output: console report + data/results/cda_estimate.csv.
"""

import json
import math
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import finish_pts, is_finite, jsdiv, load_pts, pts_from_fit
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
os.makedirs(RESULTS, exist_ok=True)


def read_pts(file):
    return load_pts(os.path.join(DATA, file))


def grade30(pts):
    W = 30
    for i in range(len(pts)):
        j = i
        while j < len(pts) - 1 and pts[j]["x"] - pts[i]["x"] < W:
            j += 1
        dd = pts[j]["x"] - pts[i]["x"]
        if dd > 1:
            pts[i]["grade"] = (pts[j]["alt"] - pts[i]["alt"]) / dd
        else:
            pts[i]["grade"] = pts[i - 1]["grade"] if i > 0 else 0


def collect_climbs(files):
    """Contiguous 30 m-window grade ≥ 1% runs with total Δh ≥ 50 m; clip the first
    10 m of vertical (entry inertia), then measure A/B/C/E over the remainder."""
    A, B, C, E, meta = [], [], [], [], []
    gentle = []   # {dh, dx, dKE, aeroInt(=∫v³dt), Ewheel} for grade∈[1,3.5]%, v̄≥6 m/s
    n_rides = n_err = 0
    for f in files:
        try:
            pts = read_pts(f)
            if len(pts) < 30:
                continue
            grade30(pts)
            rho = rho_at(median([p["alt"] for p in pts]))
            n_rides += 1
            st = -1
            run_max = float("-inf")
            run_max_i = -1
            for i in range(len(pts) + 1):
                if i < len(pts):
                    if st < 0:
                        if pts[i]["grade"] > 0:
                            st = i
                            run_max = pts[i]["alt"]
                            run_max_i = i
                        continue
                    if pts[i]["alt"] > run_max:
                        run_max = pts[i]["alt"]
                        run_max_i = i
                    if run_max - pts[i]["alt"] <= 8 and i < len(pts) - 1:
                        continue   # 8 m drop budget: survive dips
                if st < 0:
                    continue
                a0, b = st, run_max_i       # end run at its altitude peak
                st = -1
                run_max = float("-inf")
                if b <= a0 or pts[b]["alt"] - pts[a0]["alt"] < 50:
                    continue                # net Δh ≥ 50 m
                a = a0
                while a < b and pts[a]["alt"] - pts[a0]["alt"] < 10:
                    a += 1                  # clip first 10 m of climb
                dh = pts[b]["alt"] - pts[a]["alt"]
                dx = pts[b]["x"] - pts[a]["x"]
                if dh < 40 or dx < 100:
                    continue
                e_wheel = aero_int = time = 0.0
                ok = True
                for k in range(a + 1, b + 1):
                    dt = pts[k].get("dt") or 0
                    v = pts[k].get("v")
                    if pts[k].get("power") is None or v is None:
                        ok = False
                        break
                    e_wheel += pts[k]["power"] * dt
                    aero_int += v * v * v * dt
                    time += dt
                if not ok or not (time > 0) or e_wheel <= 0:
                    continue
                va, vb = pts[a].get("v"), pts[b].get("v")
                if va is None or vb is None:
                    continue
                A.append(G * dh + 0.5 * (vb * vb - va * va))   # mass: gravity + ΔKE
                B.append(G * dx)                               # rolling: g·Δx
                C.append(0.5 * rho * aero_int)                 # aero: ½ρ∫v³dt (per unit CdA)
                E.append(KEFF * e_wheel)                       # wheel work
                meta.append({"dh": dh, "dx": dx, "vmean": dx / time, "grade": dh / dx})
                gr = dh / dx
                vbar = dx / time
                if gr >= 0.01 and gr <= 0.035 and vbar >= 6:
                    gentle.append({"dh": dh, "dx": dx, "dKE": 0.5 * (vb * vb - va * va),
                                   "aeroInt": aero_int, "Ewheel": KEFF * e_wheel, "rho": rho})
        except Exception:
            n_err += 1
    return {"A": A, "B": B, "C": C, "E": E, "meta": meta, "gentle": gentle,
            "nRides": n_rides, "nErr": n_err}


def list_riders():
    R = []
    try:
        with open(os.path.join(DATA, "strava_ppaz_manifest.json"), encoding="utf8") as fh:
            man = json.load(fh)
        R.append({"name": "P. Paz",
                  "files": [a["file"] for a in man
                            if a["sport"] == "ride" and a["powCov"] > 0.5 and a["km"] >= 20]})
    except Exception as e:
        print("ppaz?", e, file=sys.stderr)
    try:
        with open(os.path.join(DATA, "strava_jaam_manifest.json"), encoding="utf8") as fh:
            man = json.load(fh)
        R.append({"name": "JAAM",
                  "files": [a["file"] for a in man
                            if a["sport"] == "ride" and a["powCov"] > 0.5 and a["km"] >= 20]})
    except Exception as e:
        print("jaam?", e, file=sys.stderr)
    try:
        with open(os.path.join(DATA, "model_inputs.json"), encoding="utf8") as fh:
            inp = [e for e in json.load(fh) if e.get("has_power") and e.get("file")]
        R.append({"name": "author/longões", "files": [e["file"] for e in inp],
                  "aCdA": median([e["cda"] for e in inp]),
                  "aM": median([e["m"] for e in inp]),
                  "aCrr": median([e["crr"] for e in inp])})
    except Exception as e:
        print("longões?", e, file=sys.stderr)
    return R


_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def jquote(s):
    """JSON.stringify string quoting (the CSV's rider cell)."""
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


print("================================================================")
print("INDEPENDENT m / C_rr / CdA — 3-param climb energy-balance regression (no braking uphill)")
print(f"k_eff={js_str(KEFF)}, ρ=ISA(altitude), wind=0. Segments: sustained uphill Δh≥50 m, "
      "first 10 m clipped, ≥40 m used.\n")

out = []
for r in list_riders():
    c = collect_climbs(r["files"])
    fit = ols3(c["A"], c["B"], c["C"], c["E"])
    m, crr_m, cda = fit["theta"]
    crr = jsdiv(crr_m, m)
    bs = bootstrap3(c["A"], c["B"], c["C"], c["E"])
    # Gentle-fast CdA: fix (m, C_rr) from the mass-robust climb fit (CdA≈0.35), then CdA per
    # gentle-fast segment = residual aero work / (½ρ∫v³dt); median over segments.
    m_fix = ols2_fixed(c["A"], c["B"], c["C"], c["E"], 0.35)
    M, CRR = m_fix["m"], m_fix["crr"]
    per_seg = [x for x in
               (jsdiv(s["Ewheel"] - M * s["dKE"] - M * G * s["dh"] - CRR * M * G * s["dx"],
                      0.5 * s["rho"] * s["aeroInt"]) for s in c["gentle"])
               if is_finite(x)]
    per_seg.sort()
    cda_g = median(per_seg)
    cda_giqr = ([per_seg[math.floor(0.25 * len(per_seg))], per_seg[math.floor(0.75 * len(per_seg))]]
                if len(per_seg) > 4 else [float("nan"), float("nan")])
    gr = [s["grade"] for s in c["meta"]]
    vm = [s["vmean"] for s in c["meta"]]
    print(f"── {r['name']} ──  {c['nRides']} rides ({c['nErr']} err), {len(c['E'])} climb segments")
    print(f"  grade range p10–p90: "
          f"{to_fixed(median([g for g in gr if g < median(gr)]) * 100, 1)}–"
          f"{to_fixed(median([g for g in gr if g > median(gr)]) * 100, 1)}%,  "
          f"climb speed median {to_fixed(median(vm) * 3.6, 1)} km/h  (aero leverage)")
    print(f"  m   = {to_fixed(m, 1)} kg     95% CI [{to_fixed(bs['mCI'][0], 0)}, {to_fixed(bs['mCI'][1], 0)}]")
    print(f"  C_rr= {to_fixed(crr, 4)}      95% CI [{to_fixed(bs['crrCI'][0], 4)}, {to_fixed(bs['crrCI'][1], 4)}]")
    print(f"  CdA = {to_fixed(cda, 3)} m²   95% CI [{to_fixed(bs['cdaCI'][0], 3)}, "
          f"{to_fixed(bs['cdaCI'][1], 3)}]   (R²={to_fixed(fit['r2'], 4)})")
    ab_corr = corr(c["A"], c["B"])
    print(f"  identifiability: corr(A_mass, B_roll) = {to_fixed(ab_corr, 3)}  "
          "(→1 ⇒ mass & C_rr collinear on climbs)")
    print(f"  gentle-fast CdA (grade 1–3.5%, v̄≥6 m/s, n={len(per_seg)} seg, m={to_fixed(M, 0)} kg "
          f"C_rr={to_fixed(CRR, 4)} from CdA=0.35 fit): CdA ≈ "
          f"{to_fixed(cda_g, 3) if is_finite(cda_g) else '—'} m²  "
          f"[IQR {to_fixed(cda_giqr[0], 2)}, {to_fixed(cda_giqr[1], 2)}]")
    ins = []
    for cd in (0.25, 0.35, 0.45):
        fx = ols2_fixed(c["A"], c["B"], c["C"], c["E"], cd)
        ins.append(f"CdA={js_str(cd)}→m={to_fixed(fx['m'], 0)}kg,C_rr={to_fixed(fx['crr'], 3)}")
    print("  CdA→mass insensitivity (fix CdA, fit m,C_rr):  " + "  ".join(ins))
    if r.get("aCdA") is not None:
        fA = ols2_fixed(c["A"], c["B"], c["C"], c["E"], r["aCdA"])
        print(f"  [anchor] longões assumed: CdA {to_fixed(r['aCdA'], 2)}, m {to_fixed(r['aM'], 0)}, "
              f"C_rr {to_fixed(r['aCrr'], 4)}   → with CdA fixed at truth: m={to_fixed(fA['m'], 0)} kg, "
              f"C_rr={to_fixed(fA['crr'], 4)}")
    print("")
    out.append({"rider": r["name"], "nSeg": len(c["E"]), "m": m, "crr": crr, "cda": cda,
                "r2": fit["r2"], "mCI": bs["mCI"], "cdaCI": bs["cdaCI"], "crrCI": bs["crrCI"]})

csv_text = ("rider,nSeg,mass_kg,crr,cda_m2,r2,m_lo,m_hi,cda_lo,cda_hi,crr_lo,crr_hi\n"
            + "\n".join(
                f"{jquote(o['rider'])},{o['nSeg']},{to_fixed(o['m'], 1)},{to_fixed(o['crr'], 4)},"
                f"{to_fixed(o['cda'], 3)},{to_fixed(o['r2'], 4)},{to_fixed(o['mCI'][0], 1)},"
                f"{to_fixed(o['mCI'][1], 1)},{to_fixed(o['cdaCI'][0], 3)},{to_fixed(o['cdaCI'][1], 3)},"
                f"{to_fixed(o['crrCI'][0], 4)},{to_fixed(o['crrCI'][1], 4)}"
                for o in out) + "\n")
with open(os.path.join(RESULTS, "cda_estimate.csv"), "w", encoding="utf8") as fh:
    fh.write(csv_text)
print("wrote cda_estimate.csv")
