#!/usr/bin/env python3
"""Entry 35 — the honest-physics residual: measured braking (arm A) and the
regime-consistent ĈdA (arm B).

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 35 BEFORE any result was
seen. Under Entry 33's per-ride inverted physics both engines under-predict
by 4-5 pp on D3-D5; the two registered candidate residuals:

Arm A — legs-funded braking, measured. Per adjacent-sample pair on
NON-descent 30 m cells (cell grade > -1.5%; descent braking cancels per
Appendix A), observed decel minus the physics coasting decel at the ride's
inverted constants; only the excess is booked (coasting contributes zero by
construction). E_brake = Σ m·max(0, a_obs − a_coast)·dx. Danilo's registered
bounds: braking time-share ≤ 1.7% of moving time on D3-D5, ≤ 5% on D2;
materiality rule: E_brake/E_meas < 1% exonerates, ≥ 3% is primary.

Arm B — the regime-consistent ĈdA (no segments, no selection):
  CdA_reg = (k_eff·P_flat/v_meas − Crr·m̂·g) / (½ρ·v_meas²)
with P_flat the regime extractor's flat power and v_meas the measured flat
speed; closes Entry 33's v_f gap by construction. The Table-5 law rows are
re-run under CdA_reg (all else as Entry 33, wind included) and the per-ride
law-matching ε* (form 3 solved for ε) is reported under both aeros.

Physics join: m̂/Ĉrr/ĈdA/wind per ride from perride_invert.csv (basename
key); unjoined rides fall back to anchor/prior constants, flagged.

Env: E35_SMOKE=1 (40 rides/corpus).
Run: python3 src/harness/e35_residual.py
Output: data/results/e35_residual.csv + console scoreboards.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    deadband, empirical_kj, eps_geom,
                                    extract_regime_powers, flat_eq_speed,
                                    is_finite, jsdiv, load_pts,
                                    measured_flat_speed, overall_mean_power,
                                    resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
SMOKE = os.environ.get("E35_SMOKE") == "1"

VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
RHO, KEFF, CRR0, CDA0 = 1.13, 0.98, 0.008, 0.40
ANCHOR_M = {"longoes": None, "censo": 78.0, "ppaz": 74.5, "jaam": 101.9,
            "danlessa": 74.7}
ZWIFT = 260
CELL = 30.0
A_CAP, V_FLOOR, DT_CAP = 6.0, 1.0, 10.0
CDA_RANGE = (0.10, 1.00)


def med_of(xs: list[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def rng(seed: int) -> "Callable[[], float]":
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def boot_ci(values: list[float], seed: int) -> tuple[float, float]:
    rand = rng(seed)
    n, B = len(values), 10000
    stats = sorted(med_of([values[int(rand() * n)] for _ in range(n)])
                   for _ in range(B))
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


# ---- Entry-33 constants join --------------------------------------------

INV = {}
with open(os.path.join(RESULTS, "perride_invert.csv"), encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        INV[(r["corpus"], r["ride"])] = r


def joined_phys(corpus: str, ride: str, m_logged: float | None) -> tuple[dict, str]:
    r = INV.get((corpus, ride))
    if r:
        return ({"m": float(r["m_hat"]), "Crr": float(r["crr_hat"]),
                 "CdA": float(r["cda_hat"]), "wind": float(r["wind_ms"])},
                "joined")
    m = m_logged if m_logged is not None else ANCHOR_M[corpus]
    return ({"m": m, "Crr": CRR0, "CdA": CDA0, "wind": 0.0}, "fallback")


# ---- per ride -------------------------------------------------------------

def run_ride(pts: list[dict], corpus: str, ride: str,
             m_logged: float | None) -> dict | None:
    emp = empirical_kj(pts)
    if not is_finite(emp) or emp <= 0:
        return None
    phys_prof = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile(phys_prof, ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    inv, join_src = joined_phys(corpus, ride, m_logged)
    m, crr, cda, wind = inv["m"], inv["Crr"], inv["CdA"], inv["wind"]
    mg = m * G

    # 30 m cell grades for the non-descent classification + sinθ term
    px, ph = prof["x"], prof["h"]
    x0 = px[0]
    nc = math.floor((px[-1] - x0) / CELL)
    j = 0

    def h_at(d: float) -> float:
        nonlocal j
        while j < len(px) - 2 and px[j + 1] < d:
            j += 1
        seg = px[j + 1] - px[j]
        f = (d - px[j]) / seg if seg > 1e-9 else 0.0
        return ph[j] * (1 - f) + ph[j + 1] * f

    cell_h = [h_at(x0 + k * CELL) for k in range(nc + 1)]
    grade = [(cell_h[k + 1] - cell_h[k]) / CELL for k in range(nc)]

    # ---- arm A: excess-decel braking on non-descent cells ----
    # Primary = the registered estimator. Two DISCLOSED sensitivity variants
    # (added after the smoke run showed noise signatures — ~180 events/h,
    # cadence>0 during 56-80% of flagged time): m03 requires excess > 0.3
    # m/s² (above 1 Hz speed-jitter); cad0 additionally requires cadence 0
    # (you stop pedalling to brake).
    e_brake = t_brake = t_brake_ped = t_mov_nd = 0.0
    e_brake_m03 = e_brake_cad0 = 0.0
    n_events = 0
    in_event = False
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        dt = b.get("dt") or 0.0
        va, vb = a.get("v"), b.get("v")
        if not dt or dt > DT_CAP or va is None or vb is None:
            in_event = False
            continue
        k = math.floor((b["x"] - x0) / CELL)
        if k < 0 or k >= nc or grade[k] <= DESC_THR:
            in_event = False
            continue
        vmid = 0.5 * (va + vb)
        if vmid < V_FLOOR:
            in_event = False
            continue
        t_mov_nd += dt
        a_obs = (va - vb) / dt
        if a_obs <= 0 or a_obs > A_CAP:
            in_event = False
            continue
        s = grade[k]
        sec = math.sqrt(1 + s * s)
        a_coast = (crr * G / sec + 0.5 * RHO * cda * vmid * vmid / m
                   + G * s / sec)
        excess = a_obs - a_coast
        if excess > 0:
            dx = max(0.0, b["x"] - a["x"])
            e_brake += m * excess * dx
            if excess > 0.3:
                e_brake_m03 += m * excess * dx
                if not (b.get("cad") or 0) > 0:
                    e_brake_cad0 += m * excess * dx
            t_brake += dt
            if (b.get("cad") or 0) > 0:
                t_brake_ped += dt
            if not in_event:
                n_events += 1
            in_event = True
        else:
            in_event = False

    # ---- arm B: regime-consistent CdA + model grid under it ----
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
          "flat": flat,
          "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
          "climbThr": CLIMB_THR, "descThr": DESC_THR}
    v_meas = measured_flat_speed(pts)
    cda_reg, reg_src = CDA0, "fallback"
    if v_meas and v_meas > 2.0 and flat and flat > 20:
        v_rel = v_meas + wind
        num = KEFF * flat / v_meas - crr * mg
        den = 0.5 * RHO * v_rel * abs(v_rel)
        if den > 0:
            c = num / den
            if CDA_RANGE[0] <= c <= CDA_RANGE[1]:
                cda_reg, reg_src = c, "regime"

    row = {"corpus": corpus, "ride": ride, "emp": emp, "join": join_src,
           "m": m, "crr": crr, "cda_seg": cda, "cda_reg": cda_reg,
           "reg_src": reg_src, "wind": wind,
           "e_brake_kj": e_brake / 1000.0,
           "brake_share_pct": 100.0 * (e_brake / 1000.0) / emp,
           "brake_share_m03_pct": 100.0 * (e_brake_m03 / 1000.0) / emp,
           "brake_share_cad0_pct": 100.0 * (e_brake_cad0 / 1000.0) / emp,
           "t_brake_s": t_brake, "t_mov_nd_s": t_mov_nd,
           "brake_time_pct": 100.0 * t_brake / t_mov_nd if t_mov_nd > 0 else float("nan"),
           "brake_cad_pct": 100.0 * t_brake_ped / t_brake if t_brake > 0 else 0.0,
           "n_events": n_events,
           "events_per_h": n_events / (t_mov_nd / 3600) if t_mov_nd > 0 else float("nan")}

    for tag, cda_use in (("seg", cda), ("reg", cda_reg)):
        p = {"m": m, "Crr": crr, "CdA": cda_use, "rho": RHO, "keff": KEFF,
             "wind": wind, "vmax": VMAX, "vstart": VSTART}
        vf = flat_eq_speed(pw["flat"], p)
        epsG = eps_geom(prof, p, vf)
        eps_d = epsG if is_finite(epsG) else 0.2
        opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                            "descThr": DESC_THR, "climbPower": pw["climb"]}
        c = canonical(prof, pw, p)
        a3_0 = approximate(profS, p, vf, 0.0, opt("zero"))
        a3_1 = approximate(profS, p, vf, 1.0, opt("zero"))
        a3_d = approximate(profS, p, vf, eps_d, opt("zero"))
        a3_f = approximate(profS, p, vf, 0.20, opt("zero"))
        a2 = approximate(prof, p, vf, 0.20, opt("zero"))
        km = (max(0, 1 - 3 * (prof["x"][-1] / 1000) / a2["hplus"])
              if a2["hplus"] > 0 else 1)
        e4f = a2["roll"] + a2["aero"] + km * (a2["climb"] + a2["recov"])
        row[f"f3_d_{tag}"] = jsdiv(a3_d["E"] / 1000 - emp, emp) * 100
        row[f"f3_f_{tag}"] = jsdiv(a3_f["E"] / 1000 - emp, emp) * 100
        row[f"f4_f_{tag}"] = jsdiv(e4f / 1000 - emp, emp) * 100
        row[f"canon_{tag}"] = jsdiv(c["legE"] / 1000 - emp, emp) * 100
        denom = a3_0["E"] - a3_1["E"]
        row[f"eps_star_{tag}"] = ((a3_0["E"] - emp * 1000) / denom
                                  if abs(denom) > 1 else float("nan"))
        row[f"eps_d_{tag}"] = eps_d
        row[f"vf_kmh_{tag}"] = vf * 3.6
    row["v_meas_kmh"] = (v_meas or float("nan")) * 3.6 if v_meas else float("nan")
    return row


def iter_corpus(name: str) -> "Iterator[tuple]":
    if name == "longoes":
        for e in json.load(open(os.path.join(DATA, "model_inputs.json"))):
            if not e.get("file") or not e.get("has_power"):
                continue
            yield (load_pts(os.path.join(DATA, e["file"])), e["label"], e["m"])
        return
    if name == "censo":
        man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
        files = [e["file"] for e in man if e.get("file")
                 and os.path.exists(os.path.join(DATA, e["file"]))]
        for f in (files[:40] if SMOKE else files):
            yield (load_pts(os.path.join(DATA, f)), os.path.basename(f), None)
        return
    man = json.load(open(os.path.join(DATA, f"strava_{name}_manifest.json")))
    cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
            and a["km"] >= 20 and a["altCov"] >= 0.99]
    for a in (cand[:40] if SMOKE else cand):
        meta: dict = {}
        pts = load_pts(os.path.join(DATA, a["file"]), meta)
        if meta.get("manufacturer") == ZWIFT:
            continue
        yield (pts, os.path.basename(a["file"]), None)


def main() -> None:
    all_rows = []
    for corpus in ("longoes", "censo", "ppaz", "jaam", "danlessa"):
        rows = []
        for pts, ride, m_logged in iter_corpus(corpus):
            try:
                r = run_ride(pts, corpus, ride, m_logged)
            except Exception:
                r = None
            if r:
                rows.append(r)
        all_rows.extend(rows)
        if not rows:
            continue
        joined = sum(1 for r in rows if r["join"] == "joined")
        print(f"\n== {corpus} — {len(rows)} rides (constants joined {joined}) ==")

        # arm A
        bt = [r["brake_time_pct"] for r in rows if is_finite(r["brake_time_pct"])]
        bs = [r["brake_share_pct"] for r in rows if is_finite(r["brake_share_pct"])]
        ev = [r["events_per_h"] for r in rows if is_finite(r["events_per_h"])]
        cadp = [r["brake_cad_pct"] for r in rows if r["t_brake_s"] > 0]
        blo, bhi = boot_ci(bt, 42)
        slo, shi = boot_ci(bs, 42)
        bm = [r["brake_share_m03_pct"] for r in rows if is_finite(r["brake_share_m03_pct"])]
        bc = [r["brake_share_cad0_pct"] for r in rows if is_finite(r["brake_share_cad0_pct"])]
        print(f"ARM A  brake time-share {to_fixed(med_of(bt), 2)}% "
              f"[{to_fixed(blo, 2)}, {to_fixed(bhi, 2)}] of non-descent moving time · "
              f"E_brake/E_meas {to_fixed(med_of(bs), 2)}% "
              f"[{to_fixed(slo, 2)}, {to_fixed(shi, 2)}] · "
              f"{to_fixed(med_of(ev), 1)} events/h · cadence>0 during braking "
              f"{to_fixed(med_of(cadp), 0)}%")
        print(f"       sensitivity: excess>0.3 m/s² → {to_fixed(med_of(bm), 2)}% of E · "
              f"+cadence-0 → {to_fixed(med_of(bc), 2)}% of E")

        # arm B
        creg = [r["cda_reg"] for r in rows if r["reg_src"] == "regime"]
        cseg = [r["cda_seg"] for r in rows if r["reg_src"] == "regime"]
        print(f"ARM B  ĈdA regime {to_fixed(med_of(creg), 3)} vs segment "
              f"{to_fixed(med_of(cseg), 3)} (n={len(creg)}) · "
              f"v_f(reg) {to_fixed(med_of([r['vf_kmh_reg'] for r in rows]), 1)} vs "
              f"measured {to_fixed(med_of([r['v_meas_kmh'] for r in rows if is_finite(r['v_meas_kmh'])]), 1)} km/h")
        print("model        segment-ĈdA err/bias         regime-ĈdA err/bias")
        for key, lab in (("f3_d", "form 3·ε_d"), ("f3_f", "form 3·ε_f"),
                         ("f4_f", "form 4·ε_f"), ("canon", "simulation")):
            line = f"{lab.ljust(12)}"
            for tag in ("seg", "reg"):
                v = [r[f"{key}_{tag}"] for r in rows if is_finite(r[f"{key}_{tag}"])]
                av = [abs(x) for x in v]
                alo, ahi = boot_ci(av, 42)
                sglo, sghi = boot_ci(v, 43)
                line += (f"  {to_fixed(med_of(av), 1)} [{to_fixed(alo, 1)},{to_fixed(ahi, 1)}]"
                         f" {to_fixed(med_of(v), 1)} [{to_fixed(sglo, 1)},{to_fixed(sghi, 1)}]")
            print(line)
        es_seg = [r["eps_star_seg"] for r in rows if is_finite(r["eps_star_seg"])]
        es_reg = [r["eps_star_reg"] for r in rows if is_finite(r["eps_star_reg"])]
        ed_reg = [r["eps_d_reg"] for r in rows if is_finite(r["eps_d_reg"])]
        print(f"matching ε*: segment {to_fixed(med_of(es_seg), 2)} → regime "
              f"{to_fixed(med_of(es_reg), 2)} (ε_d at regime physics "
              f"{to_fixed(med_of(ed_reg), 2)})")

    cols = list(all_rows[0].keys())
    with open(os.path.join(RESULTS, "e35_residual.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in all_rows:
            fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 4))
                              for v in (r[k] for k in cols)) + "\n")
    print(f"\nwrote e35_residual.csv ({len(all_rows)} rides)")


if __name__ == "__main__":
    main()
