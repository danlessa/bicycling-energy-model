"""Regime binning and the descent-balance / measured-flat-speed estimators —
ports of the app's extractRegimePowers/epsFromFIT and compare.mjs's
measuredFlatSpeed/epsFromBalance.
"""

import math

from .engines import G

_VSTOP = 0.5 / 3.6  # samples below 0.5 km/h are stopped — gated out


def extract_regime_powers(pts, climb_thr, desc_thr):
    """TIME-WEIGHTED power statistics per regime (JS extractRegimePowers).

    Each sample is binned by its grade over a 30 m distance WINDOW (0.2 m
    altitude quantization makes raw per-record grades quantize to ~4%) and
    weighted by its dt. Returns weighted mean / mean-nonzero / median per
    regime plus time and sample counts."""
    W = 30
    bins = ([], [], [])  # descent, flat, climb -> (power, weight)
    n = len(pts)
    for i in range(n):
        if pts[i].get("power") is None:
            continue
        if pts[i].get("v") is not None and pts[i]["v"] < _VSTOP:
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
            grade = (pts[i]["alt"] - pts[k]["alt"]) / db if db > 1 else 0.0
        r = 2 if grade >= climb_thr else 0 if grade <= desc_thr else 1
        bins[r].append((pts[i]["power"], pts[i].get("dt") or 1))

    def stat(b):
        if not b:
            return {"mean": None, "meanNZ": None, "median": None, "time": 0, "n": 0}
        sw = swp = sw_nz = swp_nz = 0.0
        for pwr, w in b:
            sw += w
            swp += w * pwr
            if pwr > 0:
                sw_nz += w
                swp_nz += w * pwr
        b_sorted = sorted(b, key=lambda s: s[0])  # weighted median (incl zeros)
        acc = 0.0
        median = b_sorted[-1][0]
        for pwr, w in b_sorted:
            acc += w
            if acc >= sw / 2:
                median = pwr
                break
        return {"mean": swp / sw if sw else None,
                "meanNZ": swp_nz / sw_nz if sw_nz else None,
                "median": median, "time": sw, "n": len(b)}

    return {"descent": stat(bins[0]), "flat": stat(bins[1]), "climb": stat(bins[2])}


def _cell_alt(pts, x0, DX, nc):
    """30 m cell-boundary altitudes by linear interpolation (shared helper)."""
    j = 0
    px = pts
    out = [0.0] * (nc + 1)
    for k in range(nc + 1):
        d = x0 + k * DX
        while j < len(px) - 2 and px[j + 1]["x"] < d:
            j += 1
        seg = px[j + 1]["x"] - px[j]["x"]
        f = (d - px[j]["x"]) / seg if seg > 1e-9 else 0.0
        out[k] = px[j]["alt"] * (1 - f) + px[j + 1]["alt"] * f
    return out


def measured_flat_speed(pts):
    """MEASURED flat ground speed (m/s): time-weighted mean MOVING speed on
    near-flat 30 m cells, |grade| < 1% (compare.mjs measuredFlatSpeed)."""
    DX = 30
    x0 = pts[0]["x"]
    total = pts[-1]["x"] - x0
    nc = math.floor(total / DX)
    if nc < 2:
        return None
    cell_alt = _cell_alt(pts, x0, DX, nc)
    sv = [0.0] * nc
    sw = [0.0] * nc
    for r in pts:
        k = math.floor((r["x"] - x0) / DX)
        if k < 0 or k >= nc:
            continue
        w = r.get("dt") or 1
        if r.get("v") is not None and r["v"] >= _VSTOP:
            sv[k] += r["v"] * w
            sw[k] += w
    SV = SW = 0.0
    for k in range(nc):
        gr = (cell_alt[k + 1] - cell_alt[k]) / DX
        if abs(gr) < 0.01 and sw[k] > 0:
            SV += sv[k]
            SW += sw[k]
    return SV / SW if SW > 0 else None


def eps_from_balance(pts, p):
    """Descent-energy-balance eps (compare.mjs epsFromBalance; the app's
    epsFromFIT): eps = (alpha*X- − E_legs,-)/(beta*H-) over 30 m cells, alpha
    at the MEASURED flat speed (deliberately NOT flatEqSpeed — a parameter
    mismatch would inflate alpha and lie about eps). NaN when H- < 1 m."""
    if not pts or len(pts) < 2:
        return float("nan")
    mg = p["m"] * G
    beta = mg / p["keff"]
    x0 = pts[0]["x"]
    total_m = pts[-1]["x"] - x0
    DX = 30
    nc = math.floor(total_m / DX)
    if nc < 2:
        return float("nan")
    cell_alt = _cell_alt(pts, x0, DX, nc)
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
        if r.get("v") is not None and r["v"] >= _VSTOP:
            cellVs[k] += r["v"] * w
            cellVt[k] += w
    sv = sw = 0.0
    for k in range(nc):
        gr = (cell_alt[k + 1] - cell_alt[k]) / DX
        if abs(gr) < 0.01 and cellVt[k] > 0:
            sv += cellVs[k]
            sw += cellVt[k]
    vf = sv / sw if sw > 0 else 5.0
    aero_spd = vf + p["wind"]
    alpha = (p["Crr"] * mg + 0.5 * p["rho"] * p["CdA"] * aero_spd * abs(aero_spd)) / p["keff"]
    Xd = Hd = Ed = 0.0
    for k in range(nc):
        dh = cell_alt[k + 1] - cell_alt[k]
        if dh < 0:
            Xd += DX
            Hd -= dh
            Ed += cellE[k]
    return float("nan") if Hd < 1 else (alpha * Xd - Ed) / (beta * Hd)
