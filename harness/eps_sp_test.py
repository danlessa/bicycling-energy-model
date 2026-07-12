#!/usr/bin/env python3
"""TEST of the São Paulo ε hypothesis (chat): urban stop-go suppresses descent
recovery below the free-coasting closed form, because you re-pedal after every
forced stop/corner.

  ε_SP = clamp( ε_coast − Δε_brake ),   Δε_brake = (1/(g·H₋))·Σ_descent ½·Δ(v²) at decels

For the 62 clean censo rides (power + speed) we compute, on shared 30 m descent
cells with α at the MEASURED flat speed:
  ε_true   = (α·X₋ − E_legs,₋)/(β·H₋)            descent-balance ε (epsFromFIT) — the truth
  ε_coast  = Σ h₋·min(1, α/β·s)/H₋               free-coasting closed form (no offset)
and from the raw speed trace the stop-go predictors:
  brakeDesc= Σ_descend ½·(v↓)² / (g·H₋)          mechanistic Δε_brake
  stops_km = forced stops (v→<1 km/h) per km     cheap planning proxy
Then: does the gap (ε_coast − ε_true) track the braking density, and does the
mechanistic ε_coast − brakeDesc beat the flat ε≈0.20 constant?

Python port of eps_sp_test.mjs (same output, byte-identical CSV and report).
The FIT parser comes from analysis/bem — machine-checked against the frozen JS
reference by analysis/parity/run_parity.py. Run: python3 harness/eps_sp_test.py
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))

from bem import pts_from_fit
from bem.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
os.makedirs(RESULTS, exist_ok=True)
G = 9.81
ASSUMED = {"m": 78, "Crr": 0.008, "CdA": 0.40, "rho": 1.13, "keff": 0.98, "wind": 0}


def is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def jsdiv(a, b):
    """JS division semantics: x/0 -> ±Infinity, 0/0 -> NaN (Python raises)."""
    try:
        return a / b
    except ZeroDivisionError:
        if a == 0 or a != a:
            return float("nan")
        return math.copysign(float("inf"), a) * math.copysign(1.0, b)


# shared 30 m-cell analysis: ε_true, ε_coast (α at measured flat speed) + the floor inputs.
def eps_cells(pts, p):
    mg = p["m"] * G
    beta = mg / p["keff"]
    x0 = pts[0]["x"]
    total_m = pts[-1]["x"] - x0
    DX = 30
    nc = math.floor(total_m / DX)
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

    cell_alt = [0.0] * (nc + 1)
    for k in range(nc + 1):
        cell_alt[k] = alt_at(x0 + k * DX)
    cell_e = [0.0] * nc
    cell_vs = [0.0] * nc
    cell_vt = [0.0] * nc
    VSTOP = 0.5 / 3.6   # 0.5 km/h — gate stopped samples out of the flat speed, as extractRegimePowers does
    for r in pts:
        k = math.floor((r["x"] - x0) / DX)
        if k < 0 or k >= nc:
            continue
        w = r["dt"] or 1
        if r.get("power") is not None:
            cell_e[k] += r["power"] * w
        if r.get("v") is not None and r["v"] >= VSTOP:
            cell_vs[k] += r["v"] * w
            cell_vt[k] += w
    sv = 0.0
    sw = 0.0
    for k in range(nc):
        gr = (cell_alt[k + 1] - cell_alt[k]) / DX
        if abs(gr) < 0.01 and cell_vt[k] > 0:
            sv += cell_vs[k]
            sw += cell_vt[k]
    vf = sv / sw if sw > 0 else 5
    aero_spd = vf + p["wind"]
    alpha = (p["Crr"] * mg + 0.5 * p["rho"] * p["CdA"] * aero_spd * abs(aero_spd)) / p["keff"]
    Xd = 0.0
    Hd = 0.0
    Ed = 0.0
    eps_w = 0.0
    Hp = 0.0
    for k in range(nc):
        dh = cell_alt[k + 1] - cell_alt[k]
        if dh < 0:
            drop = -dh
            s = drop / DX
            Xd += DX
            Hd += drop
            Ed += cell_e[k]
            eps_w += drop * min(1, alpha / (beta * s))
        else:
            Hp += dh
    if Hd < 1:
        return None
    emp = 0.0
    for v in cell_e:
        emp += v
    return {"epsTrue": (alpha * Xd - Ed) / (beta * Hd), "epsCoast": eps_w / Hd,
            "Hd": Hd, "Hp": Hp, "beta": beta, "vf": vf,
            "cellAlt": cell_alt, "x0": x0, "DX": DX, "nc": nc, "emp": emp}


# stop-go predictors from the raw speed trace, given which cells descend.
def brake_stats(pts, cells):
    cell_alt, x0, DX, nc, Hd = (cells["cellAlt"], cells["x0"], cells["DX"],
                                cells["nc"], cells["Hd"])
    VSTOP = 1 / 3.6

    def descending(i):
        k = math.floor((pts[i]["x"] - x0) / DX)
        return k >= 0 and k < nc and cell_alt[k + 1] < cell_alt[k]

    brake_desc = 0.0
    brake_all = 0.0
    hard_desc = 0.0
    stops = 0
    total_dist = pts[-1]["x"] - pts[0]["x"]
    for i in range(1, len(pts)):
        v0, v1 = pts[i - 1].get("v"), pts[i].get("v")
        if v0 is None or v1 is None:
            continue
        if v1 < v0:
            d = 0.5 * (v0 * v0 - v1 * v1)
            brake_all += d
            if descending(i):
                brake_desc += d
                if v0 - v1 > 1.0:
                    hard_desc += d   # hard = >1 m/s drop
        if v0 >= VSTOP and v1 < VSTOP:
            stops += 1     # moving → stopped transition
    g_hd = G * Hd
    return {"brakeDesc": brake_desc / g_hd, "brakeAll": brake_all / g_hd,
            "hardDesc": hard_desc / g_hd, "stops_km": stops / (total_dist / 1000)}


# ---- driver ----
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
            pts = pts_from_fit(fh.read())
        if not any(q.get("power") is not None for q in pts):
            continue
        p = dict(ASSUMED)
        c = eps_cells(pts, p)
        if not c:
            continue
        floor = p["m"] * G * c["Hp"] / p["keff"]         # climbing PE (kJ·1000) from 30 m cells
        if c["emp"] < floor:                             # physical floor — not fully pedalled
            continue
        b = brake_stats(pts, c)
        rows.append({"ride": e["name"], "epsTrue": c["epsTrue"], "epsCoast": c["epsCoast"],
                     "gap": c["epsCoast"] - c["epsTrue"], "brakeDesc": b["brakeDesc"],
                     "brakeAll": b["brakeAll"], "hardDesc": b["hardDesc"],
                     "stops_km": b["stops_km"], "vf": c["vf"] * 3.6})
    except Exception:
        pass  # skip


# ---- stats helpers ----
def med(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def mean(xs):
    t = 0.0
    for x in xs:
        t += x
    return jsdiv(t, len(xs))


def corr(a, b):
    n = len(a)
    ma, mb = mean(a), mean(b)
    sab = saa = sbb = 0.0
    for i in range(n):
        sab += (a[i] - ma) * (b[i] - mb)
        saa += (a[i] - ma) ** 2
        sbb += (b[i] - mb) ** 2
    return jsdiv(sab, math.sqrt(saa * sbb))


def ols(y, x):
    n = len(y)
    mx, my = mean(x), mean(y)
    sxy = sxx = syy = 0.0
    for i in range(n):
        sxy += (x[i] - mx) * (y[i] - my)
        sxx += (x[i] - mx) ** 2
        syy += (y[i] - my) ** 2
    b = jsdiv(sxy, sxx)
    a = my - b * mx
    ssr = 0.0
    for i in range(n):
        ssr += (y[i] - (a + b * x[i])) ** 2
    return {"a": a, "b": b, "r2": 1 - jsdiv(ssr, syy), "rms": math.sqrt(jsdiv(ssr, n))}


def rms_res(pred):
    return math.sqrt(mean([(rows[i]["epsTrue"] - pred[i]) ** 2 for i in range(len(rows))]))


def f(x, d=2):
    if x is None or not is_finite(x):
        return "—"
    return to_fixed(x, d)


print(f"SÃO PAULO ε TEST — {len(rows)} clean censo rides (power + speed)")
print(f"assumed: m={js_str(ASSUMED['m'])} CdA={js_str(ASSUMED['CdA'])} "
      f"Crr={js_str(ASSUMED['Crr'])}; α at measured flat speed.\n")
print(f"medians: ε_true {f(med([r['epsTrue'] for r in rows]))}  "
      f"ε_coast {f(med([r['epsCoast'] for r in rows]))}  "
      f"gap {f(med([r['gap'] for r in rows]))}  "
      f"brakeDesc {f(med([r['brakeDesc'] for r in rows]))}  "
      f"stops/km {f(med([r['stops_km'] for r in rows]), 1)}")

gap = [r["gap"] for r in rows]
print("\nDoes the gap (ε_coast − ε_true) track stop-go density?")
for lab, key in [("Δε_brake (descent ½Δv²)", "brakeDesc"), ("hard-brake (>1m/s, descent)", "hardDesc"),
                 ("all-decel ½Δv²", "brakeAll"), ("stops/km", "stops_km"), ("v_f (km/h)", "vf")]:
    x = [r[key] for r in rows]
    o = ols(gap, x)
    print(f"  gap ~ {lab.ljust(24)} corr={f(corr(gap, x))}  slope={f(o['b'])}  "
          f"intercept={f(o['a'])}  R²={f(o['r2'])}")

print("\nWhich estimator best predicts ε_true?  (RMS of ε_true − prediction)")
clamp = lambda v: max(0, min(1, v))
preds = {
    "ε_coast (no penalty)": [clamp(r["epsCoast"]) for r in rows],
    "ε_coast − 0.13 (rural offset)": [clamp(r["epsCoast"] - 0.13) for r in rows],
    "flat ε = 0.20 (SP constant)": [0.20 for _ in rows],
    "ε_coast − Δε_brake (mechanistic, slope 1)": [clamp(r["epsCoast"] - r["brakeDesc"]) for r in rows],
}
# calibrated: ε_coast − c·brakeDesc and ε_coast − (a + b·stops_km)
ob = ols(gap, [r["brakeDesc"] for r in rows])
preds[f"ε_coast − {f(ob['b'])}·Δε_brake (fitted)"] = \
    [clamp(r["epsCoast"] - ob["b"] * r["brakeDesc"]) for r in rows]
os_ = ols(gap, [r["stops_km"] for r in rows])
preds[f"ε_coast − ({f(os_['a'])}+{f(os_['b'])}·stops/km) (fitted)"] = \
    [clamp(r["epsCoast"] - (os_["a"] + os_["b"] * r["stops_km"])) for r in rows]
for lab, pred in preds.items():
    print(f"  {lab.ljust(44)} RMS={f(rms_res(pred))}  "
          f"bias={f(med([rows[i]['epsTrue'] - pred[i] for i in range(len(rows))]))}")

print(f"\ngap variability: median {f(med(gap))}, mean {f(mean(gap))}, "
      f"sd {f(math.sqrt(mean([(g - mean(gap)) ** 2 for g in gap])))}")
csv_text = "\n".join(["ride,epsTrue,epsCoast,gap,brakeDesc,brakeAll,stops_km,vf"]
                     + [f'"{r["ride"]}",{f(r["epsTrue"])},{f(r["epsCoast"])},{f(r["gap"])},'
                        f'{f(r["brakeDesc"])},{f(r["brakeAll"])},{f(r["stops_km"], 1)},{f(r["vf"], 1)}'
                        for r in rows])
with open(os.path.join(RESULTS, "eps_sp.csv"), "w") as fh:
    fh.write(csv_text + "\n")
print(f"\nwrote results/eps_sp.csv ({len(rows)} rides)")
