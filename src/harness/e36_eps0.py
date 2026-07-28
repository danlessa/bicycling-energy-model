#!/usr/bin/env python3
"""Entry 36 — ε₀ regressed per dataset, two ways, against the frozen 0.13.

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 36 BEFORE any result was
seen. At the regime-consistent physics (Entry 35 arm B: m̂ / Ĉrr / ĈdA_reg /
wind, joined from e35_residual.csv), per corpus:

  balance-ε₀  = median(ε_coast − ε_bal) on real-descent rides (s̄ ≥ 3%) —
                the Entry-8 calibration statistic (mechanism level);
  bias-ε₀     = median(ε_coast − ε*) over all rides — the ε₀ the energy law
                needs to zero form 3·ε_d's median signed error (law level;
                absorbs every non-ε residual).

ε_bal follows its standing convention (α at the MEASURED flat speed — which
at ĈdA_reg equals the regime-consistent α, so the pass is self-consistent).
Out-of-sample: chronological halves; both ε₀ variants fitted on the first
half, form 3·ε_d scored on the second against frozen 0.13 (accuracy AND
bias, 95% CIs). Frozen-priors physics carried as reference for balance-ε₀.

Env: E36_SMOKE=1 (40 rides/corpus).
Run: python3 src/harness/e36_eps0.py
Output: data/results/e36_eps0.csv + console tables.
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

from bicycling_energy_model import (approximate, build_profile, deadband,
                                    empirical_kj, extract_regime_powers,
                                    flat_eq_speed, is_finite, jsdiv, load_pts,
                                    measured_flat_speed, overall_mean_power,
                                    resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
SMOKE = os.environ.get("E36_SMOKE") == "1"

VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
RHO, KEFF, CRR0, CDA0 = 1.13, 0.98, 0.008, 0.40
ANCHOR_M = {"longoes": None, "censo": 78.0, "ppaz": 74.5, "jaam": 101.9,
            "danlessa": 74.7}
ZWIFT = 260
DX30, VSTOP = 30, 0.5 / 3.6
EPS0_FROZEN = 0.13


def med_of(xs: list[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def rng(seed: int):
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


E35 = {}
with open(os.path.join(RESULTS, "e35_residual.csv"), encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        E35[(r["corpus"], r["ride"])] = r


def eps_cells(pts: list[dict], m: float, crr: float, cda: float,
              wind: float) -> dict | None:
    """ε_bal / ε_coast / s̄ over 30 m descent cells, α at the MEASURED flat
    speed (the standing convention; eps_cells_pz pattern)."""
    if not pts or len(pts) < 2:
        return None
    mg = m * G
    beta = mg / KEFF
    x0 = pts[0]["x"]
    nc = math.floor((pts[-1]["x"] - x0) / DX30)
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

    cell_alt = [alt_at(x0 + k * DX30) for k in range(nc + 1)]
    cellE = [0.0] * nc
    cellVs = [0.0] * nc
    cellVt = [0.0] * nc
    for r in pts:
        k = math.floor((r["x"] - x0) / DX30)
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
        gr = (cell_alt[k + 1] - cell_alt[k]) / DX30
        if abs(gr) < 0.01 and cellVt[k] > 0:
            sv += cellVs[k]
            sw += cellVt[k]
    if not sw > 0:
        return None
    vf = sv / sw
    aero_spd = vf + wind
    alpha = (crr * mg + 0.5 * RHO * cda * aero_spd * abs(aero_spd)) / KEFF
    ab = alpha / beta
    Xd = Hd = Ed = cw = 0.0
    for k in range(nc):
        dh = cell_alt[k + 1] - cell_alt[k]
        if dh < 0:
            drop = -dh
            Xd += DX30
            Hd += drop
            Ed += cellE[k]
            cw += drop * min(1.0, ab / (drop / DX30))
    if Hd < 1:
        return None
    return {"epsBal": (alpha * Xd - Ed) / (beta * Hd), "epsCoast": cw / Hd,
            "sbar": Hd / Xd if Xd > 0 else float("nan")}


def run_ride(pts: list[dict], corpus: str, ride: str,
             m_logged: float | None, date: str) -> dict | None:
    e35 = E35.get((corpus, ride))
    if e35 is None:
        return None
    m, crr, wind = float(e35["m"]), float(e35["crr"]), float(e35["wind"])
    cda_reg = float(e35["cda_reg"])
    emp = float(e35["emp"])

    bal_reg = eps_cells(pts, m, crr, cda_reg, wind)
    bal_frz = eps_cells(pts, m, CRR0, CDA0, 0.0)
    if bal_reg is None:
        return None

    # form 3·ε_d machinery at regime physics: E(ε₀) is linear in ε₀ via ε_d
    p = {"m": m, "Crr": crr, "CdA": cda_reg, "rho": RHO, "keff": KEFF,
         "wind": wind, "vmax": VMAX, "vstart": VSTART}
    prof = resample_profile(build_profile([q["x"] for q in pts],
                                          [q["alt"] for q in pts]), ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat
    vf = flat_eq_speed(flat, p)
    opt = {"climbAeroMode": "zero", "climbThr": CLIMB_THR,
           "descThr": DESC_THR, "climbPower": pw_climb}
    a0 = approximate(profS, p, vf, 0.0, opt)
    a1 = approximate(profS, p, vf, 1.0, opt)
    span = a0["E"] - a1["E"]          # = β·h̃₋ (J per unit ε)

    # model-v_f ε_coast (eps_geom convention) so ε_d(ε₀) = eps_coast_model − ε₀
    aero_spd = vf + wind
    alpha_m = (crr * m * G + 0.5 * RHO * cda_reg * aero_spd * abs(aero_spd)) / KEFF
    beta = m * G / KEFF
    ab = alpha_m / beta
    px, ph = prof["x"], prof["h"]
    x0 = px[0]
    nc = math.floor((px[-1] - x0) / DX30)
    j = 0

    def h_at(d: float) -> float:
        nonlocal j
        while j < len(px) - 2 and px[j + 1] < d:
            j += 1
        seg = px[j + 1] - px[j]
        f = (d - px[j]) / seg if seg > 1e-9 else 0.0
        return ph[j] * (1 - f) + ph[j + 1] * f

    hs = [h_at(x0 + k * DX30) for k in range(nc + 1)]
    Hd = cw = 0.0
    for k in range(nc):
        dh = hs[k + 1] - hs[k]
        if dh < 0:
            Hd -= dh
            cw += -dh * min(1.0, ab / (-dh / DX30))
    coast_model = cw / Hd if Hd >= 1 else float("nan")

    def delta_pct(eps0: float) -> float:
        eps = coast_model - eps0 if is_finite(coast_model) else 0.2
        E = a0["E"] - eps * span
        return jsdiv(E / 1000 - emp, emp) * 100

    return {"corpus": corpus, "ride": ride, "date": date, "emp": emp,
            "balR_coast": bal_reg["epsCoast"], "balR_bal": bal_reg["epsBal"],
            "balR_sbar": bal_reg["sbar"],
            "balF_coast": bal_frz["epsCoast"] if bal_frz else float("nan"),
            "balF_bal": bal_frz["epsBal"] if bal_frz else float("nan"),
            "coast_model": coast_model,
            "eps_star": float(e35["eps_star_reg"]),
            "d_frozen": delta_pct(EPS0_FROZEN),
            "_delta_fn_a0": a0["E"], "_span": span,
            "gapR": bal_reg["epsCoast"] - bal_reg["epsBal"],
            "gapF": (bal_frz["epsCoast"] - bal_frz["epsBal"]) if bal_frz else float("nan"),
            "eps0_bias_i": (coast_model - float(e35["eps_star_reg"])
                            if is_finite(coast_model) and is_finite(float(e35["eps_star_reg"]))
                            else float("nan"))}


def iter_corpus(name: str):
    if name == "longoes":
        for e in json.load(open(os.path.join(DATA, "model_inputs.json"))):
            if not e.get("file") or not e.get("has_power"):
                continue
            yield (load_pts(os.path.join(DATA, e["file"])), e["label"],
                   e["m"], e.get("date") or "")
        return
    if name == "censo":
        man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
        files = [(e["file"], e.get("date") or "") for e in man if e.get("file")
                 and os.path.exists(os.path.join(DATA, e["file"]))]
        for f, d in (files[:40] if SMOKE else files):
            yield (load_pts(os.path.join(DATA, f)), os.path.basename(f), None, d)
        return
    man = json.load(open(os.path.join(DATA, f"strava_{name}_manifest.json")))
    cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
            and a["km"] >= 20 and a["altCov"] >= 0.99]
    cand.sort(key=lambda a: a.get("date") or "")
    for a in (cand[:40] if SMOKE else cand):
        meta: dict = {}
        pts = load_pts(os.path.join(DATA, a["file"]), meta)
        if meta.get("manufacturer") == ZWIFT:
            continue
        yield (pts, os.path.basename(a["file"]), None, a.get("date") or "")


def main() -> None:
    all_rows = []
    corpus_fits: dict = {}
    for corpus in ("longoes", "censo", "ppaz", "jaam", "danlessa"):
        rows = []
        for pts, ride, m_logged, date in iter_corpus(corpus):
            try:
                r = run_ride(pts, corpus, ride, m_logged, date)
            except Exception:
                r = None
            if r:
                rows.append(r)
        all_rows.extend(rows)
        if not rows:
            continue
        print(f"\n== {corpus} — {len(rows)} rides ==")

        # the two ε₀ estimands, whole corpus (with CIs)
        real = [r for r in rows if r["balR_sbar"] >= 0.03
                and is_finite(r["gapR"])]
        realF = [r for r in rows if r["balR_sbar"] >= 0.03 and is_finite(r["gapF"])]
        biasable = [r for r in rows if is_finite(r["eps0_bias_i"])]
        gR = [r["gapR"] for r in real]
        gF = [r["gapF"] for r in realF]
        bE = [r["eps0_bias_i"] for r in biasable]
        if gR:
            lo, hi = boot_ci(gR, 42)
            print(f"balance-ε₀ (regime physics, n={len(gR)}): "
                  f"{to_fixed(med_of(gR), 3)} [{to_fixed(lo, 3)}, {to_fixed(hi, 3)}]")
        if gF:
            lo, hi = boot_ci(gF, 42)
            print(f"balance-ε₀ (frozen physics,  n={len(gF)}): "
                  f"{to_fixed(med_of(gF), 3)} [{to_fixed(lo, 3)}, {to_fixed(hi, 3)}]")
        if bE:
            lo, hi = boot_ci(bE, 42)
            print(f"bias-ε₀    (regime physics, n={len(bE)}): "
                  f"{to_fixed(med_of(bE), 3)} [{to_fixed(lo, 3)}, {to_fixed(hi, 3)}]")

        # chronological OOS: fit on first half, score form 3·ε_d on second
        rows.sort(key=lambda r: r["date"])
        half = len(rows) // 2
        train, test = rows[:half], rows[half:]
        tr_real = [r["gapR"] for r in train
                   if r["balR_sbar"] >= 0.03 and is_finite(r["gapR"])]
        tr_bias = [r["eps0_bias_i"] for r in train if is_finite(r["eps0_bias_i"])]
        if len(tr_real) < 8 or len(tr_bias) < 8 or len(test) < 10:
            print("OOS skipped (thin halves)")
            continue
        fits = {"frozen 0.13": EPS0_FROZEN,
                "balance-ε₀(train)": med_of(tr_real),
                "bias-ε₀(train)": med_of(tr_bias)}
        corpus_fits[corpus] = (train, test, fits)
        print(f"OOS (train n={len(train)}, test n={len(test)}): "
              + " · ".join(f"{k} = {to_fixed(v, 3)}" for k, v in fits.items()
                           if k != "frozen 0.13"))
        for lab, e0 in fits.items():
            d = []
            for r in test:
                eps = (r["coast_model"] - e0) if is_finite(r["coast_model"]) else 0.2
                E = r["_delta_fn_a0"] - eps * r["_span"]
                d.append(jsdiv(E / 1000 - r["emp"], r["emp"]) * 100)
            av = [abs(x) for x in d]
            alo, ahi = boot_ci(av, 42)
            slo, shi = boot_ci(d, 43)
            print(f"  {lab.ljust(20)} med|Δ%| {to_fixed(med_of(av), 2)} "
                  f"[{to_fixed(alo, 1)}, {to_fixed(ahi, 1)}]  "
                  f"bias {to_fixed(med_of(d), 2)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]")

    # ---- pooled D3-D5: shared pooled-train constants, held-out on pooled test halves ----
    tr3 = [c for c in ("ppaz", "jaam", "danlessa") if c in corpus_fits]
    if len(tr3) == 3:
        pool_train_bal = med_of([g for c in tr3 for g in
                                 [r["gapR"] for r in corpus_fits[c][0]
                                  if r["balR_sbar"] >= 0.03 and is_finite(r["gapR"])]])
        pool_train_bias = med_of([g for c in tr3 for g in
                                  [r["eps0_bias_i"] for r in corpus_fits[c][0]
                                   if is_finite(r["eps0_bias_i"])]])
        print(f"\n== pooled D3-D5 OOS (stratified test halves) ==")
        print(f"shared pooled-train: balance-ε₀ = {to_fixed(pool_train_bal, 3)} · "
              f"bias-ε₀ = {to_fixed(pool_train_bias, 3)}")
        variants = [("frozen 0.13", lambda c: EPS0_FROZEN),
                    ("per-corpus balance(train)", lambda c: corpus_fits[c][2]["balance-ε₀(train)"]),
                    ("per-corpus bias(train)", lambda c: corpus_fits[c][2]["bias-ε₀(train)"]),
                    ("POOLED balance(train)", lambda c: pool_train_bal),
                    ("POOLED bias(train)", lambda c: pool_train_bias)]
        for lab, e0_of in variants:
            strata_d = []
            for c in tr3:
                _, test, _ = corpus_fits[c]
                e0 = e0_of(c)
                d = []
                for r in test:
                    eps = (r["coast_model"] - e0) if is_finite(r["coast_model"]) else 0.2
                    E = r["_delta_fn_a0"] - eps * r["_span"]
                    d.append(jsdiv(E / 1000 - r["emp"], r["emp"]) * 100)
                strata_d.append(d)
            pooled = [x for v in strata_d for x in v]
            av = [abs(x) for x in pooled]
            rand = rng(42)
            B = 10000
            stats_a, stats_s = [], []
            for _ in range(B):
                samp = []
                for v in strata_d:
                    n = len(v)
                    samp.extend(v[int(rand() * n)] for _ in range(n))
                stats_a.append(med_of([abs(x) for x in samp]))
            stats_a.sort()
            rand = rng(43)
            for _ in range(B):
                samp = []
                for v in strata_d:
                    n = len(v)
                    samp.extend(v[int(rand() * n)] for _ in range(n))
                stats_s.append(med_of(samp))
            stats_s.sort()
            print(f"  {lab.ljust(26)} med|Δ%| {to_fixed(med_of(av), 2)} "
                  f"[{to_fixed(stats_a[250], 1)}, {to_fixed(stats_a[9749], 1)}]  "
                  f"bias {to_fixed(med_of(pooled), 2)} "
                  f"[{to_fixed(stats_s[250], 1)}, {to_fixed(stats_s[9749], 1)}]")

    cols = [c for c in all_rows[0] if not c.startswith("_")]
    with open(os.path.join(RESULTS, "e36_eps0.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in all_rows:
            fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 4))
                              for v in (r[k] for k in cols)) + "\n")
    print(f"\nwrote e36_eps0.csv ({len(all_rows)} rides)")


if __name__ == "__main__":
    main()
