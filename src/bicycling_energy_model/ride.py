"""Per-ride pipeline — the compare.mjs wiring as one reviewable function.

Mirrors the harness defaults exactly: engineDx = 5 m, regime stat = time-
weighted mean (incl. zeros), climb/descent thresholds 2% / −1.5%, elevation
deadband tau = 2 m for the smoothed variants, auto v_f = flatEqSpeed(P_flat),
vmax 38 km/h, vstart 15 km/h.
"""

import math

from .engines import (G, approximate, canonical, deadband, flat_eq_speed,
                      resample_profile, v2_edge)
from .fit import empirical_kj, overall_mean_power, pts_from_fit
from .profiles import build_profile, pts_from_gpx
from .regime import eps_from_balance, extract_regime_powers

CLIMB_THR, DESC_THR = 0.02, -0.015
ENGINE_DX = 5
TAU_SMOOTH = 2
VMAX, VSTART = 38 / 3.6, 15 / 3.6


def load_pts(path):
    """Track file (.fit or .gpx) -> point list."""
    if str(path).lower().endswith(".gpx"):
        with open(path, encoding="utf-8") as f:
            return pts_from_gpx(f.read())
    with open(path, "rb") as f:
        return pts_from_fit(f.read())


def analyze_ride(pts, params, eps=0.20, v2_opts=None):
    """One ride through the whole workflow. `params`: m, crr, cda, rho, keff,
    wind_kmh (sheet units, as model_inputs.json). Returns the three energies
    (kJ) plus the smoothed variants, the fitted/balance eps, and geometry —
    the columns of compare.mjs's model_comparison.csv that feed the journal
    scoreboard. The conservation identity is asserted (<= 1e-6 relative)."""
    prof_info = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    phys = {"x": prof_info["x"], "h": prof_info["h"]}
    prof = resample_profile(phys, ENGINE_DX)
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw = {
        "climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else 0,
        "flat": flat,
        "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
        "climbThr": CLIMB_THR, "descThr": DESC_THR,
    }
    p = {"m": params["m"], "Crr": params["crr"], "CdA": params["cda"],
         "rho": params["rho"], "keff": params["keff"],
         "vmax": VMAX, "vstart": VSTART, "wind": (params.get("wind_kmh") or 0) / 3.6}
    vf = flat_eq_speed(pw["flat"], p)
    opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                        "descThr": DESC_THR, "climbPower": pw["climb"]}
    a_off = approximate(prof, p, vf, eps, opt("off"))
    a_cf = approximate(prof, p, vf, eps, opt("zero"))
    c = canonical(prof, pw, p)
    resid = abs(p["keff"] * c["legE"]
                - (c["dKE"] + c["Wrr"] + c["Waero"] + c["Wgrav"] + c["Wbrake"]))
    resid /= max(1.0, p["keff"] * c["legE"])
    assert resid <= 1e-6, f"conservation violated: rel resid {resid:.2e}"
    prof_s = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    a_cf_s = approximate(prof_s, p, vf, eps, opt("zero"))
    c_s = canonical(prof_s, pw, p)
    v2 = v2_edge(prof, p, vf, v2_opts or
                 {"kSmooth": 1.0, "epsOffset": 0.13, "climbThr": CLIMB_THR})
    emp = empirical_kj(pts)
    beta = p["m"] * G / p["keff"]
    b_hm = beta * a_cf_s["hminus"]
    eps_fit = ((a_cf_s["roll"] + a_cf_s["aero"] + a_cf_s["climb"] - emp * 1000) / b_hm
               if b_hm > 1e-6 else float("nan"))
    return {
        "emp_kj": emp,
        "canon_kj": c["legE"] / 1000, "canonS_kj": c_s["legE"] / 1000,
        "off_kj": a_off["E"] / 1000,
        "cf_kj": a_cf["E"] / 1000, "cfS_kj": a_cf_s["E"] / 1000,
        "v2_kj": v2["E"] / 1000, "v2_eps_implied": v2["epsImplied"],
        "eps_fit": eps_fit, "eps_balance": eps_from_balance(pts, p),
        "x_km": prof["x"][-1] / 1000,
        "hplus_raw": a_off["hplus"], "hplus_smooth": a_cf_s["hplus"],
        "hminus_raw": a_off["hminus"],
        "vf_ms": vf, "pw": pw, "cons_resid": resid,
        "time_s": c["t"], "stalled": c["stalled"],
    }


def d_pct(model_kj, emp_kj):
    """Signed percent deviation vs the empirical energy."""
    return (model_kj - emp_kj) / emp_kj * 100 if emp_kj else float("nan")


def median(values):
    v = sorted(x for x in values if isinstance(x, (int, float)) and math.isfinite(x))
    if not v:
        return float("nan")
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
