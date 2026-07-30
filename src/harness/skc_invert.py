#!/usr/bin/env python3
"""Entry 43, amendment — D6 under INVERTED physics, and the descent-pedalling test.

Two arms, both registered in the Entry-43 amendment before either was run.

ARM A — the regime-consistent protocol on D6 (the secondary protocol the main
registration declared). Per ride: m̂_r and Ĉrr_r from the Entry-33 segment
inversion (`perride_invert`'s machinery, imported unchanged — it is import-safe),
then the Entry-35 regime-consistent aero

    ĈdA_reg = (k_eff * P_flat / v_meas - Ĉrr * m̂ * g) / (0.5 * rho * v_meas^2)

which closes the flat balance at the MEASURED flat speed by construction
(paper 1 §3.5.2). eps_0 = 0.13 stays frozen; nothing about eps is refitted.
Wind is 0: `perride_invert`'s wind path fetches weather at the ride's
0.25-degree-quantized centroid, and D6's centroids derive from third-party
riders' home addresses, so the fetch is deliberately not used (it also keeps D6
on the same zero-wind footing as every other blind corpus).

ARM B — is the deficit spread descent pedalling? A physics-free measurement, run
identically on D6 and on D1/D3/D4/D5. On 30 m cells with grade <= -3% and speed
>= 0.5 km/h: pedalling OCCUPANCY (share of time with power >= 10 W) and the
INTENSITY ratio (mean descent power / mean flat power). Neither touches C_dA,
C_rr or alpha, so neither can smuggle in a parameter error. Reported per
descent-grade band, because occupancy is grade-dependent (Entry 34) and a corpus
with steeper descents would otherwise look like one that coasts more.

Output: data/results/skc_invert.csv (arm A, per ride)
        data/results/skc_descent_occupancy.csv (arm B, per ride, all corpora)

Run: python3 src/harness/skc_invert.py      (SKC_SMOKE=1 for a small subset)
"""

from __future__ import annotations

import glob
import json
import math
import os
import sys
from typing import Iterator, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    deadband, empirical_kj, eps_geom,
                                    extract_regime_powers, flat_eq_speed,
                                    is_finite, jsdiv, load_pts,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

import perride_invert as PI
from skc_compare import (CLIMB_THR, DESC_THR, ENGINE_DX, EPS_F, FROZEN, M0,
                         MIN_SUSTAINED_DH, PUBLISHED_KG, RESULTS, TAU_SMOOTH,
                         VMAX, VSTART, boot_ci, eps_cells, med_of, quant,
                         ride_files, sign_p)
from bicycling_energy_model import climb_balance

DATA = os.path.join(REPO, "data", "inputs", "activities")
SMOKE = bool(os.environ.get("SKC_SMOKE"))
ZWIFT = 260

# Arm B thresholds — fixed in the registration, and the values the repo already
# uses elsewhere (perride_invert.POW_MIN, the real-descent gate, VSTOP).
DESC_GATE, POW_ON, VSTOP = -0.03, 10.0, 0.5 / 3.6
CELL = 30.0
BANDS = ((-0.03, -0.05), (-0.05, -0.08), (-0.08, -1.00))
BAND_LAB = ("3-5%", "5-8%", ">8%")


# ------------------------------------------------------------------ arm A

def invert_ride(pts: Sequence[dict], m_anchor: float) -> dict | None:
    """Entry-33 m̂/Ĉrr + the Entry-35 regime-consistent ĈdA, wind 0.

    `m_anchor` is the rider's sustained-climb mass from the frozen protocol, and
    is the fallback when a ride has no qualifying climb segment — the role
    `perride_invert.ANCHOR_M` plays for the paper-1 corpora. It is computed at
    runtime, never frozen into a constant here: an implied mass moves with G, and
    a stale literal is the Entry-27 bug. Using a generic 78 kg instead would
    change the MASS source at the same time as the aero source and make the
    frozen-vs-inverted contrast uninterpretable."""
    phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    if not phys:
        return None
    prof = resample_profile(phys, ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None

    climbs_raw, flats_raw = PI.find_segments(prof)
    climbs = [s for s in (PI.seg_integrals(pts, c, 0.0) for c in climbs_raw) if s]
    flats = [s for s in (PI.seg_integrals(pts, f, 0.0) for f in flats_raw) if s]
    wb_climbs = [s for s in climbs if s["ok"]]
    wb_flats = [s for s in flats if s["ok"]]

    m_src, m_hat = "fallback", m_anchor
    crr_pool = wb_climbs
    if wb_climbs:
        k = min(len(wb_climbs), max(2, math.ceil(len(wb_climbs) / 3)))
        picked, rest = PI.spread_pick(wb_climbs, k)
        est = [(PI.invert_mass(s), s["h"]) for s in picked]
        est = [(m, h) for m, h in est
               if is_finite(m) and PI.M_RANGE[0] <= m <= PI.M_RANGE[1]]
        if est:
            m_hat = sum(m * h for m, h in est) / sum(h for _, h in est)
            m_src = "inverted" if len(est) >= 2 else "thin"
            crr_pool = rest

    crr_src, crr_hat = "fallback", PI.CRR0
    est = [(PI.invert_crr(s, m_hat), s["h"]) for s in crr_pool]
    est = [(c, h) for c, h in est
           if is_finite(c) and PI.CRR_RANGE[0] <= c <= PI.CRR_RANGE[1]]
    if est and m_src != "fallback":
        crr_hat = sum(c * h for c, h in est) / sum(h for _, h in est)
        crr_src = "inverted"

    # Entry-33 CdA (from flat SEGMENTS) — kept for the contrast, not primary
    cda33_src, cda33 = "fallback", PI.CDA0
    if wb_flats:
        est2 = []
        for s in wb_flats:
            hs = [h for x, h in zip(prof["x"], prof["h"])
                  if s["mid"] - s["x"] / 2 <= x <= s["mid"] + s["x"] / 2]
            mu = sum(hs) / len(hs) if hs else 0.0
            sd = math.sqrt(sum((h - mu) ** 2 for h in hs) / len(hs)) if hs else 0.0
            c = PI.invert_cda(s, m_hat, crr_hat)
            if is_finite(c) and PI.CDA_RANGE[0] <= c <= PI.CDA_RANGE[1]:
                est2.append((c, s["x"] / (1 + sd)))
        if est2:
            cda33 = sum(c * w for c, w in est2) / sum(w for _, w in est2)
            cda33_src = "inverted"

    return {"prof": prof, "m_hat": m_hat, "m_src": m_src,
            "crr_hat": crr_hat, "crr_src": crr_src,
            "cda33": cda33, "cda33_src": cda33_src}


def measured_flat_speed(pts: Sequence[dict]) -> float:
    """Time-weighted mean speed on |grade| < 1% 30 m cells, VSTOP-gated."""
    if len(pts) < 2:
        return float("nan")
    x0 = pts[0]["x"]
    nc = math.floor((pts[-1]["x"] - x0) / CELL)
    if nc < 2:
        return float("nan")
    j = 0

    def alt_at(d: float) -> float:
        nonlocal j
        while j < len(pts) - 2 and pts[j + 1]["x"] < d:
            j += 1
        seg = pts[j + 1]["x"] - pts[j]["x"]
        f = (d - pts[j]["x"]) / seg if seg > 1e-9 else 0.0
        return pts[j]["alt"] * (1 - f) + pts[j + 1]["alt"] * f

    cell_alt = [alt_at(x0 + k * CELL) for k in range(nc + 1)]
    vs = vt = 0.0
    for r in pts:
        k = math.floor((r["x"] - x0) / CELL)
        if k < 0 or k >= nc:
            continue
        if abs((cell_alt[k + 1] - cell_alt[k]) / CELL) >= 0.01:
            continue
        v, w = r.get("v"), (r.get("dt") or 1)
        if v is not None and v >= VSTOP:
            vs += v * w
            vt += w
    return vs / vt if vt > 0 else float("nan")


def score(pts: Sequence[dict], prof: dict, p: dict) -> dict | None:
    """The Table-3 grid under a given physics set."""
    emp = empirical_kj(pts)
    if not is_finite(emp) or emp <= 0:
        return None
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
          "flat": flat,
          "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
          "climbThr": CLIMB_THR, "descThr": DESC_THR}
    vf = flat_eq_speed(pw["flat"], p)
    epsG = eps_geom(prof, p, vf)
    eps_d = epsG if is_finite(epsG) else EPS_F
    opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                        "descThr": DESC_THR, "climbPower": pw["climb"]}
    c = canonical(prof, pw, p)
    out = {"emp": emp, "vf_kmh": vf * 3.6, "epsG": eps_d,
           "canon_d": jsdiv(c["legE"] / 1000 - emp, emp) * 100}
    for tag, eps in (("d", eps_d), ("f", EPS_F)):
        a1 = approximate(prof, p, vf, eps, opt("off"))
        a2 = approximate(prof, p, vf, eps, opt("zero"))
        a3 = approximate(profS, p, vf, eps, opt("zero"))
        km = prof["x"][-1] / 1000.0
        ks = max(0.0, 1 - 3.0 * km / a2["hplus"]) if a2["hplus"] > 0 else 1.0
        e4 = a2["roll"] + a2["aero"] + ks * (a2["climb"] + a2["recov"])
        for name, E in (("f1", a1["E"]), ("f2", a2["E"]), ("f3", a3["E"]), ("f4", e4)):
            out[f"{name}_{tag}"] = jsdiv(E / 1000 - emp, emp) * 100
    return out


# ------------------------------------------------------------------ arm B

def descent_behaviour(pts: Sequence[dict]) -> dict | None:
    """Physics-free: pedalling occupancy and intensity on real-descent cells."""
    if len(pts) < 2:
        return None
    x0 = pts[0]["x"]
    nc = math.floor((pts[-1]["x"] - x0) / CELL)
    if nc < 2:
        return None
    j = 0

    def alt_at(d: float) -> float:
        nonlocal j
        while j < len(pts) - 2 and pts[j + 1]["x"] < d:
            j += 1
        seg = pts[j + 1]["x"] - pts[j]["x"]
        f = (d - pts[j]["x"]) / seg if seg > 1e-9 else 0.0
        return pts[j]["alt"] * (1 - f) + pts[j + 1]["alt"] * f

    cell_alt = [alt_at(x0 + k * CELL) for k in range(nc + 1)]
    grade = [(cell_alt[k + 1] - cell_alt[k]) / CELL for k in range(nc)]
    t_on = [0.0] * len(BANDS)
    t_all = [0.0] * len(BANDS)
    e_on = [0.0] * len(BANDS)
    flat_e = flat_t = 0.0
    for r in pts:
        k = math.floor((r["x"] - x0) / CELL)
        if k < 0 or k >= nc:
            continue
        v, w, pwr = r.get("v"), (r.get("dt") or 1), r.get("power")
        if v is None or v < VSTOP or pwr is None:
            continue
        s = grade[k]
        if abs(s) < 0.01:
            flat_e += pwr * w
            flat_t += w
        if s > DESC_GATE:
            continue
        for b, (hi, lo) in enumerate(BANDS):
            if lo < s <= hi:
                t_all[b] += w
                if pwr >= POW_ON:
                    t_on[b] += w
                e_on[b] += pwr * w
                break
    if sum(t_all) <= 0:
        return None
    out: dict = {"desc_t": sum(t_all),
                 "occ_all": sum(t_on) / sum(t_all),
                 "p_desc": sum(e_on) / sum(t_all),
                 "p_flat": flat_e / flat_t if flat_t > 0 else float("nan")}
    out["intensity"] = (out["p_desc"] / out["p_flat"]
                        if out["p_flat"] and is_finite(out["p_flat"]) and out["p_flat"] > 0
                        else float("nan"))
    for b, lab in enumerate(BAND_LAB):
        out[f"occ_{lab}"] = t_on[b] / t_all[b] if t_all[b] > 0 else float("nan")
        out[f"t_{lab}"] = t_all[b]
    return out


def iter_brazil(name: str) -> Iterator[tuple]:
    """(pts, label) per ride for the paper-1 corpora — manifest-driven, as e35 does."""
    if name == "longoes":
        for e in json.load(open(os.path.join(DATA, "model_inputs.json"))):
            if not e.get("file") or not e.get("has_power"):
                continue
            yield load_pts(os.path.join(DATA, e["file"])), e["label"]
        return
    if name == "censo":
        man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
        files = [e["file"] for e in man
                 if e.get("file") and os.path.exists(os.path.join(DATA, e["file"]))]
        for f in (files[:40] if SMOKE else files):
            yield load_pts(os.path.join(DATA, f)), os.path.basename(f)
        return
    man = json.load(open(os.path.join(DATA, f"strava_{name}_manifest.json")))
    cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
            and a["km"] >= 20 and a["altCov"] >= 0.99]
    for a in (cand[:40] if SMOKE else cand):
        meta: dict = {}
        pts = load_pts(os.path.join(DATA, a["file"]), meta)
        if meta.get("manufacturer") == ZWIFT:
            continue
        yield pts, os.path.basename(a["file"])


# ------------------------------------------------------------------ driver

def main() -> None:
    print("Entry 43 amendment — D6 under inverted physics + the descent-pedalling test"
          + ("  [SKC_SMOKE]" if SMOKE else ""))

    # ---------- anchor masses (the frozen protocol's per-rider m̂) ----------
    # Recomputed here rather than copied from Entry 43's console output: an
    # implied mass moves with G and with the inversion, and a frozen literal is
    # the Entry-27 bug. This is the SAME sustained-climb inversion skc_compare
    # runs, so Arm A differs from the frozen arm in the AERO only.
    p0 = {**FROZEN, "m": M0}
    mh: dict[str, list[float]] = {}
    for rider, path in ride_files():
        try:
            pts = load_pts(path)
        except Exception:
            continue
        if len(pts) < 10:
            continue
        cb = climb_balance(pts, p0)
        if cb["n"] > 0 and cb["dh"] >= MIN_SUSTAINED_DH and (cb["egrav"] + cb["eroll"]) > 0:
            m = M0 * (cb["emeas"] - cb["eaero"]) / (cb["egrav"] + cb["eroll"])
            # The per-ride inversion has non-physical tails (a ride whose climb
            # aero exceeds its measured energy returns a NEGATIVE mass). The
            # median absorbs them at corpus scale, but a negative mass must never
            # reach a scored arm, so filter to the physical range perride_invert
            # already enforces before taking the median.
            if is_finite(m) and PI.M_RANGE[0] <= m <= PI.M_RANGE[1]:
                mh.setdefault(rider, []).append(m)
    anchor = {r: med_of(v) for r, v in mh.items() if v}
    print("\nanchor mass per rider (frozen sustained-climb inversion, the Arm-A fallback): "
          + " · ".join(f"{r} {to_fixed(m, 1)}" for r, m in sorted(anchor.items())))

    # ---------- ARM A ----------
    rows: list[dict] = []
    for rider, path in ride_files():
        meta: dict = {}
        try:
            pts = load_pts(path, meta)
        except Exception:
            continue
        if len(pts) < 10 or meta.get("manufacturer") == ZWIFT:
            continue
        npow = sum(1 for q in pts if q.get("power") is not None)
        nalt = sum(1 for q in pts if q.get("alt") is not None)
        if npow / len(pts) <= 0.5 or nalt / len(pts) < 0.99 or pts[-1]["x"] / 1000 < 20:
            continue
        inv = invert_ride(pts, anchor.get(rider, M0))
        if inv is None:
            continue
        prof = inv["prof"]
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        p_flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
        v_meas = measured_flat_speed(pts)
        cda_reg, cda_reg_src = inv["cda33"], "fallback33"
        if is_finite(v_meas) and v_meas > 1 and p_flat and is_finite(p_flat):
            num = PI.KEFF * p_flat / v_meas - inv["crr_hat"] * inv["m_hat"] * G
            cand = num / (0.5 * PI.RHO * v_meas ** 2)
            if is_finite(cand) and PI.CDA_RANGE[0] <= cand <= PI.CDA_RANGE[1]:
                cda_reg, cda_reg_src = cand, "regime"
        p = {"m": inv["m_hat"], "Crr": inv["crr_hat"], "CdA": cda_reg,
             "rho": PI.RHO, "keff": PI.KEFF, "wind": 0.0,
             "vmax": VMAX, "vstart": VSTART}
        sc = score(pts, prof, p)
        if sc is None:
            continue
        # SECOND protocol, for paper 1's Table 5: the same per-ride m̂ and Ĉrr but
        # the Entry-33 segment CdA rather than the Entry-35 regime-consistent one.
        # Table 5 and Table 6 differ in exactly this, so D6 needs both to appear
        # in both. Columns are suffixed _t5; the unsuffixed ones remain Table 6's.
        p_t5 = {**p, "CdA": inv["cda33"]}
        sc_t5 = score(pts, prof, p_t5)
        row = {"rider": rider, "ride": os.path.basename(path)[:-4],
               "dist_km": prof["x"][-1] / 1000, "m_hat": inv["m_hat"],
               "m_src": inv["m_src"], "crr_hat": inv["crr_hat"],
               "crr_src": inv["crr_src"], "cda33": inv["cda33"],
               "cda_reg": cda_reg, "cda_reg_src": cda_reg_src,
               "v_meas_kmh": v_meas * 3.6 if is_finite(v_meas) else float("nan"),
               **sc,
               **({f"{k}_t5": v for k, v in sc_t5.items()} if sc_t5 else {})}
        eb = eps_cells(pts, p)
        if eb and eb.get("Hd", 0) >= 1 and eb.get("sbar", 0) >= 0.03:
            row["eps_bal"] = eb["epsBal"]
            row["eps_coast"] = eb["epsCoast"]
            row["eps_gap"] = eb["epsCoast"] - eb["epsBal"]
        rows.append(row)

    riders = sorted({r["rider"] for r in rows})
    print(f"\n=== ARM A — regime-consistent per-ride physics, {len(rows)} rides ===")
    print("rider".ljust(9) + "n".rjust(5) + "m_hat".rjust(9) + "Crr_hat".rjust(10)
          + "CdA_reg".rjust(10) + "CdA_33".rjust(9) + "published".rjust(11))
    for r in riders:
        s = [x for x in rows if x["rider"] == r]
        print(r.ljust(9) + str(len(s)).rjust(5)
              + to_fixed(med_of([x["m_hat"] for x in s]), 1).rjust(9)
              + to_fixed(med_of([x["crr_hat"] for x in s]), 4).rjust(10)
              + to_fixed(med_of([x["cda_reg"] for x in s]), 3).rjust(10)
              + to_fixed(med_of([x["cda33"] for x in s]), 3).rjust(9)
              + to_fixed(PUBLISHED_KG.get(r, 0), 1).rjust(11))

    COLS = [("F3 · eps_d", "f3_d"), ("F4 · eps_d", "f4_d"),
            ("F3 · eps_f", "f3_f"), ("F4 · eps_f", "f4_f"),
            ("simulation", "canon_d")]
    for r in riders + ["POOLED"]:
        sub = [x for x in rows if r == "POOLED" or x["rider"] == r]
        if len(sub) < 5:
            continue
        print(f"\n--- {r}  (n = {len(sub)})")
        print("model".ljust(16) + "med|D%| [95% CI]".rjust(22) + "medD% [95% CI]".rjust(23))
        for lab, key in COLS:
            av = [abs(x[key]) for x in sub if is_finite(x.get(key, float("nan")))]
            sv = [x[key] for x in sub if is_finite(x.get(key, float("nan")))]
            if not av:
                continue
            alo, ahi = boot_ci(av, 42)
            slo, shi = boot_ci(sv, 43)
            print(lab.ljust(16)
                  + f"{to_fixed(med_of(av), 2)} [{to_fixed(alo, 1)}, {to_fixed(ahi, 1)}]".rjust(22)
                  + f"{to_fixed(med_of(sv), 2)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]".rjust(23))

    print("\nP3 under inverted physics — does the deficit spread shrink?")
    print("  (frozen was: user_1 0.117 · user_2 0.298 · user_3 0.080 · user_5 0.175)")
    for r in riders + ["POOLED"]:
        sub = [x for x in rows if "eps_gap" in x and (r == "POOLED" or x["rider"] == r)]
        if len(sub) < 3:
            continue
        gaps = [x["eps_gap"] for x in sub]
        lo, hi = boot_ci(gaps, 42, B=2000 if SMOKE else 10000)
        print(f"  {r.ljust(9)} n = {str(len(sub)).rjust(4)}  gap "
              f"{to_fixed(med_of(gaps), 3)} [{to_fixed(lo, 2)}, {to_fixed(hi, 2)}]  "
              f"(eps_coast {to_fixed(med_of([x['eps_coast'] for x in sub]), 2)}, "
              f"eps_bal {to_fixed(med_of([x['eps_bal'] for x in sub]), 2)})")

    if rows:
        # Union of every row's keys, not row[0]'s: a column absent from the
        # FIRST row (eps_gap, when that ride has no real descent) was being
        # dropped from the header and therefore from every row.
        cols = list(dict.fromkeys(k for _r in rows for k in _r))
        dest = os.path.join(RESULTS, f"skc_invert{'.SMOKE' if SMOKE else ''}.csv")
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for x in rows:
                fh.write(",".join(
                    (f'"{v}"' if isinstance(v, str)
                     else to_fixed(v, 4) if is_finite(v) else "")
                    for v in (x.get(k, float("nan")) for k in cols)) + "\n")
        print(f"\nwrote {os.path.basename(dest)} ({len(rows)} rides)")

    # ---------- ARM B ----------
    if os.environ.get("SKC_SKIP_B"):
        print("\n(ARM B skipped: SKC_SKIP_B set — it is physics-free and unaffected "
              "by the Arm-A mass-anchor fix)")
        return
    print("\n=== ARM B — descent pedalling, physics-free, all corpora ===")
    beh: list[dict] = []
    for rider, path in ride_files():
        try:
            pts = load_pts(path)
        except Exception:
            continue
        if len(pts) < 10:
            continue
        d = descent_behaviour(pts)
        if d:
            beh.append({"corpus": "D6-" + rider, "ride": os.path.basename(path)[:-4], **d})
    for corpus, label in (("longoes", "D1"), ("ppaz", "D3"), ("jaam", "D4"),
                          ("danlessa", "D5"), ("censo", "D2")):
        try:
            for pts, lab in iter_brazil(corpus):
                d = descent_behaviour(pts)
                if d:
                    beh.append({"corpus": label, "ride": lab, **d})
        except Exception as exc:
            print(f"  ({corpus}: {type(exc).__name__} — skipped)")

    print("\ncorpus".ljust(12) + "n".rjust(5) + "occupancy by descent grade".rjust(30)
          + "intensity".rjust(11))
    print("".ljust(17) + "3-5%".rjust(9) + "5-8%".rjust(9) + ">8%".rjust(9)
          + "P_desc/P_flat".rjust(14))
    order = sorted({b["corpus"] for b in beh},
                   key=lambda c: (not c.startswith("D6"), c))
    for c in order:
        s = [b for b in beh if b["corpus"] == c]
        cells = "".join(
            to_fixed(med_of([b[f"occ_{lab}"] for b in s
                             if is_finite(b.get(f"occ_{lab}", float("nan")))]), 3).rjust(9)
            for lab in BAND_LAB)
        print(c.ljust(12) + str(len(s)).rjust(5) + cells
              + to_fixed(med_of([b["intensity"] for b in s
                                 if is_finite(b.get("intensity", float("nan")))]), 3).rjust(14))

    print("\nD6 vs the Brazilian corpora, per band (occupancy median [95% CI]):")
    for lab in BAND_LAB:
        d6 = [b[f"occ_{lab}"] for b in beh
              if b["corpus"].startswith("D6") and is_finite(b.get(f"occ_{lab}", float("nan")))]
        br = [b[f"occ_{lab}"] for b in beh
              if not b["corpus"].startswith("D6") and is_finite(b.get(f"occ_{lab}", float("nan")))]
        if len(d6) < 5 or len(br) < 5:
            continue
        dl, dh = boot_ci(d6, 42, B=2000 if SMOKE else 10000)
        bl, bh = boot_ci(br, 42, B=2000 if SMOKE else 10000)
        verdict = ("D6 HIGHER (hypothesis supported)" if dl > bh else
                   "D6 LOWER (hypothesis refuted)" if dh < bl else
                   "overlapping CIs (inconclusive)")
        print(f"  {lab.ljust(6)} D6 {to_fixed(med_of(d6), 3)} [{to_fixed(dl, 3)}, {to_fixed(dh, 3)}]"
              f"  (n={len(d6)})   BR {to_fixed(med_of(br), 3)} [{to_fixed(bl, 3)}, {to_fixed(bh, 3)}]"
              f"  (n={len(br)})   -> {verdict}")

    if beh:
        # Union of every row's keys, not row[0]'s: a column absent from the
        # FIRST row (eps_gap, when that ride has no real descent) was being
        # dropped from the header and therefore from every row.
        cols = list(dict.fromkeys(k for _r in beh for k in _r))
        dest = os.path.join(RESULTS,
                            f"skc_descent_occupancy{'.SMOKE' if SMOKE else ''}.csv")
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for x in beh:
                fh.write(",".join(
                    (f'"{v}"' if isinstance(v, str)
                     else to_fixed(v, 4) if is_finite(v) else "")
                    for v in (x.get(k, float("nan")) for k in cols)) + "\n")
        print(f"\nwrote {os.path.basename(dest)} ({len(beh)} rides)")


if __name__ == "__main__":
    main()
