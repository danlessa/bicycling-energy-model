#!/usr/bin/env python3
"""Entry 29 Tier A — physical-constants sensitivity sweep (CdA × Crr × ρ).

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 29 BEFORE any result was
seen. Grid (all anchors on-lattice): CdA {0.25..0.50 step .05} × Crr
{0.004..0.014 step .002} × ρ {1.00, 1.13, 1.225} = 108 combinations.

Design: each ride is reduced ONCE to combination-independent aggregates
(geometry sums for the closed forms, the 30 m descent-cell lists for the ε
machinery, the sustained-climb sums for the mass inversion); every
combination is then pure arithmetic — no per-combination harness reruns.
Mass is re-inverted per combination (self-consistent mode; the anchor m̂
must reproduce the published 74.5 / 101.9 / 74.7 kg). SWEEP_FREEZE_M=1
freezes mass at the anchor value instead.

CI bands: exact order-statistic (binomial-rank) 95% CI for the median —
distribution-free, deterministic, RNG-free. This deviates from the repo's
seeded-bootstrap convention because ~10⁴ cells are not computable in stdlib
time; the deviation is gate-checked (SWEEP_SMOKE) against the mulberry32
bootstrap on anchor cells.

Gates. Both modes assert (i) the order-statistic CI vs the mulberry32
bootstrap on the anchor cell (≤ 0.3 pp per bound at n ≥ 150,
widening stepwise below — the conservative gap grows as n shrinks) and (ii) the P1 ρ·CdA degeneracy
identity on an off-grid equal-product pair (float precision). The FULL run
additionally asserts the anchor m̂ (74.5 / 101.9 / 74.7 ± 0.15) and all 16
anchor med|Δ%| values against the published gate-battery numbers (± 0.11) —
end-to-end parity with the shipped harnesses. SWEEP_SMOKE=1 runs 40
rides/corpus over anchor + extreme combinations with published masses forced
(a 40-ride subset cannot re-invert the corpus mass).

Run:  python3 src/harness/param_sweep.py          (~5-10 min, parse cache warm)
      SWEEP_SMOKE=1 python3 src/harness/param_sweep.py
Output: data/results/param_sweep.csv (gitignored, like every result).
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

from bicycling_energy_model import (build_profile, canonical, climb_balance,
                                    deadband, empirical_kj, eps_geom,
                                    approx_components, extract_regime_powers,
                                    flat_eq_speed, is_finite, jsdiv, load_pts,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")

CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
KEFF, WIND, M0, EPS0 = 0.98, 0.0, 78.0, 0.13
MIN_SUSTAINED_DH = 200
ZWIFT = 260

SMOKE = os.environ.get("SWEEP_SMOKE") == "1"
FREEZE_M = os.environ.get("SWEEP_FREEZE_M") == "1"
CANON = os.environ.get("SWEEP_CANON") == "1"      # Tier B (Entry 30)
VMAX, VSTART = 38 / 3.6, 15 / 3.6

CDA_GRID = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
CRR_GRID = [0.004, 0.006, 0.008, 0.010, 0.012, 0.014]
RHO_GRID = [1.00, 1.13, 1.225]
ANCHOR = (0.40, 0.008, 1.13)

# published anchor values the full run must reproduce (gate battery vintage)
ANCHOR_M = {"ppaz": 74.5, "jaam": 101.9, "danlessa": 74.7}
ANCHOR_CANON = {"censo": 6.6, "ppaz": 6.8, "jaam": 5.4, "danlessa": 6.1}
ANCHOR_MED = {  # (corpus, variant) -> published med|Δ%| at the anchor combination
    ("censo", "sm_geom"): 7.7, ("censo", "pm_geom"): 6.4,
    ("censo", "sm_flat"): 4.7, ("censo", "pm_flat"): 3.9,
    ("ppaz", "sm_geom"): 5.8, ("ppaz", "pm_geom"): 4.9,
    ("ppaz", "sm_flat"): 10.1, ("ppaz", "pm_flat"): 6.8,
    ("jaam", "sm_geom"): 5.5, ("jaam", "pm_geom"): 9.0,
    ("jaam", "sm_flat"): 3.5, ("jaam", "pm_flat"): 5.6,
    ("danlessa", "sm_geom"): 6.2, ("danlessa", "pm_geom"): 7.1,
    ("danlessa", "sm_flat"): 8.1, ("danlessa", "pm_flat"): 6.9,
}
VARIANTS = ("sm_geom", "pm_geom", "sm_flat", "pm_flat")


# ---------------------------------------------------------------- helpers

def med_of(xs: list[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


_CI_RANK: dict[int, int] = {}


def _rank_for(n: int) -> int:
    """Largest k with P(Bin(n, 1/2) < k) <= 0.025, exact integer arithmetic."""
    if n in _CI_RANK:
        return _CI_RANK[n]
    total = 1 << n
    cum = 0
    k = 0
    while True:
        nxt = cum + math.comb(n, k)
        if nxt * 40 > total:            # cum/total would exceed 0.025
            break
        cum = nxt
        k += 1
    _CI_RANK[n] = k
    return k


def median_ci(xs: list[float]) -> tuple[float, float]:
    """Exact order-statistic 95% CI for the median (conservative)."""
    s = sorted(x for x in xs if is_finite(x))
    n = len(s)
    if n < 6:
        return (float("nan"), float("nan"))
    k = _rank_for(n)
    lo = s[max(0, k - 1)] if k > 0 else s[0]
    hi = s[n - k] if k > 0 else s[-1]
    return (lo, hi)


def mulberry_boot_ci(values: list[float], seed: int = 42) -> tuple[float, float]:
    """The repo's bootstrap convention (bootstrap_ci.py), for the smoke cross-check."""
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    n, B = len(values), 10000
    stats = sorted(med_of([values[int(rand() * n)] for _ in range(n)]) for _ in range(B))
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------- per-ride reduction

def geom_sums(prof: dict) -> tuple[float, float, float, float]:
    """X, x_aero (dx where slope < CLIMB_THR), h+, h- — approx_components' geometry."""
    xs, hs = prof["x"], prof["h"]
    X = xaero = hplus = hminus = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        X += dx
        if dh / dx < CLIMB_THR:
            xaero += dx
        if dh >= 0:
            hplus += dh
        else:
            hminus += -dh
    return X, xaero, hplus, hminus


def geo_cells(prof: dict) -> tuple[list[tuple[float, float]], float]:
    """eps_geom's 30 m descent cells on the resampled profile: [(drop, grade)], Hd."""
    px, ph = prof["x"], prof["h"]
    x0 = px[0]
    nc = math.floor((px[-1] - x0) / 30)
    if nc < 2:
        return [], 0.0
    j = 0

    def h_at(d: float) -> float:
        nonlocal j
        while j < len(px) - 2 and px[j + 1] < d:
            j += 1
        seg = px[j + 1] - px[j]
        f = (d - px[j]) / seg if seg > 1e-9 else 0.0
        return ph[j] * (1 - f) + ph[j + 1] * f

    cellH = [h_at(x0 + k * 30) for k in range(nc + 1)]
    cells, Hd = [], 0.0
    for k in range(nc):
        dh = cellH[k + 1] - cellH[k]
        if dh < 0:
            cells.append((-dh, -dh / 30))
            Hd += -dh
    return cells, Hd


def bal_cells(pts: list[dict]) -> dict | None:
    """eps_cells_pz's combination-independent parts: measured flat speed,
    descent Xd/Hd/Ed and the per-cell (drop, grade) list."""
    if not pts or len(pts) < 2:
        return None
    VSTOP = 0.5 / 3.6
    x0 = pts[0]["x"]
    nc = math.floor((pts[-1]["x"] - x0) / 30)
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

    cellAlt = [alt_at(x0 + k * 30) for k in range(nc + 1)]
    cellE = [0.0] * nc
    cellVs = [0.0] * nc
    cellVt = [0.0] * nc
    for r in pts:
        k = math.floor((r["x"] - x0) / 30)
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
        gr = (cellAlt[k + 1] - cellAlt[k]) / 30
        if abs(gr) < 0.01 and cellVt[k] > 0:
            sv += cellVs[k]
            sw += cellVt[k]
    if not sw > 0:
        return None
    Xd = Hd = Ed = 0.0
    cells = []
    for k in range(nc):
        dh = cellAlt[k + 1] - cellAlt[k]
        if dh < 0:
            Xd += 30
            Hd -= dh
            Ed += cellE[k]
            cells.append((-dh, -dh / 30))
    if Hd < 1:
        return None
    return {"v": sv / sw, "Xd": Xd, "Hd": Hd, "Ed": Ed, "cells": cells}


def reduce_ride(pts: list[dict], invert_mass: bool, with_bal: bool) -> dict | None:
    if not any(q.get("power") is not None for q in pts):
        return None
    info = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile({"x": info["x"], "h": info["h"]}, ENGINE_DX)
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    pflat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    raw = geom_sums(prof)
    sm = geom_sums(profS)
    km = max(0, 1 - 3 * (prof["x"][-1] / 1000) / raw[2]) if raw[2] > 0 else 1
    rec = {"emp": empirical_kj(pts), "pflat": pflat, "raw": raw, "sm": sm, "km": km,
           "geo": geo_cells(prof), "bal": bal_cells(pts) if with_bal else None,
           "cb": None}
    if CANON:
        rec["prof"] = prof
        rec["pw"] = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else pflat,
                     "flat": pflat,
                     "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
                     "climbThr": CLIMB_THR, "descThr": DESC_THR}
    if invert_mass:
        p0 = {"m": M0, "CdA": ANCHOR[0], "Crr": ANCHOR[1], "rho": ANCHOR[2],
              "keff": KEFF, "wind": WIND}
        cb = climb_balance(pts, p0)
        if cb["n"] > 0:
            mg0 = M0 * G
            rec["cb"] = {"emeas": cb["emeas"], "dh": cb["dh"],
                         "egrav": cb["egrav"],
                         "S_cosL": cb["eroll"] * 1000 * KEFF / (ANCHOR[1] * mg0),
                         "S_v2L": cb["eaero"] * 1000 * KEFF / (0.5 * ANCHOR[2] * ANCHOR[0])}
    return rec


# ---------------------------------------------------------------- per-combination evaluation

def eval_combo(rides: list[dict], CdA: float, Crr: float, rho: float,
               m_fixed: float | None) -> dict:
    # mass: re-invert unless fixed
    if m_fixed is None:
        mh = []
        for r in rides:
            cb = r["cb"]
            if cb and cb["dh"] >= MIN_SUSTAINED_DH:
                eroll = Crr * M0 * G * cb["S_cosL"] / KEFF / 1000
                eaero = 0.5 * rho * CdA * cb["S_v2L"] / KEFF / 1000
                mh.append(M0 * (cb["emeas"] - eaero) / (cb["egrav"] + eroll))
        m = med_of(mh)
    else:
        m = m_fixed
    mg = m * G
    beta = mg / KEFF
    a_roll = Crr * mg / KEFF
    p = {"m": m, "CdA": CdA, "Crr": Crr, "rho": rho, "keff": KEFF, "wind": WIND}
    per = {v: [] for v in VARIANTS}
    gaps, sstars, vfs, ebs, preds = [], [], [], [], []
    for r in rides:
        vf = flat_eq_speed(r["pflat"], p)
        a_aero = 0.5 * rho * CdA * vf * vf / KEFF
        ab = (a_roll + a_aero) / beta
        Xs, xas, hps, hms = r["sm"]
        Xr, xar, hpr, hmr = r["raw"]
        if not (r["emp"] >= beta * hps / 1000):       # physical floor (combo-dependent)
            continue
        cells, Hd = r["geo"]
        if Hd >= 1:
            epsg = clamp01(sum(d * min(1.0, ab / s) for d, s in cells) / Hd - EPS0)
        else:
            epsg = 0.2                                 # harness fallback (nan → 0.2)
        for tag, eps in (("sm_geom", epsg), ("sm_flat", 0.20)):
            e = (a_roll * Xs + a_aero * xas + beta * hps - eps * beta * hms) / 1000
            per[tag].append(jsdiv(e - r["emp"], r["emp"]) * 100)
        for tag, eps in (("pm_geom", epsg), ("pm_flat", 0.20)):
            e = (a_roll * Xr + a_aero * xar + r["km"] * (beta * hpr - eps * beta * hmr)) / 1000
            per[tag].append(jsdiv(e - r["emp"], r["emp"]) * 100)
        sstars.append(ab)
        vfs.append(vf * 3.6)
        b = r["bal"]
        if b:
            a_meas = (Crr * mg + 0.5 * rho * CdA * b["v"] * b["v"]) / KEFF
            eps_bal = (a_meas * b["Xd"] - b["Ed"]) / (beta * b["Hd"])
            eps_coast = sum(min(1.0, a_meas / (beta * s)) * d for d, s in b["cells"]) / b["Hd"]
            if b["Hd"] / b["Xd"] >= 0.03 and is_finite(eps_bal) and is_finite(eps_coast):
                gaps.append(eps_coast - eps_bal)
                ebs.append(eps_bal)
                preds.append(clamp01(eps_coast - EPS0))
    # dynamic-vs-flat verdict on real descents (P3): RMS of ε_bal against the
    # frozen dynamic estimator vs the corpus's own in-sample best flat constant
    def _rms(v: list[float]) -> float:
        return math.sqrt(sum(x * x for x in v) / len(v)) if v else float("nan")
    flat_in = med_of(ebs)
    out = {"m_hat": m, "n_clean": len(per["sm_geom"]),
           "sstar_med": med_of(sstars), "vf_med": med_of(vfs),
           "gap_n": len(gaps), "gap_med": med_of(gaps),
           "rms_dyn": _rms([ebs[i] - preds[i] for i in range(len(ebs))]),
           "rms_flat_in": _rms([x - flat_in for x in ebs])}
    out["gap_lo"], out["gap_hi"] = median_ci(gaps)
    for v in VARIANTS:
        av = [abs(x) for x in per[v]]
        out[f"{v}_med"] = med_of(av)
        out[f"{v}_lo"], out[f"{v}_hi"] = median_ci(av)
        out[f"{v}_sgn"] = med_of(per[v])
        out[f"{v}_sgn_lo"], out[f"{v}_sgn_hi"] = median_ci(per[v])
        out[f"_{v}_deltas"] = per[v]                   # kept for gates, not written
    return out


def eval_canon(rides: list[dict], CdA: float, Crr: float, rho: float,
               m_fixed: float | None) -> dict:
    """Tier B: the canonical simulation at one combination (Entry 30)."""
    if m_fixed is None:
        mh = []
        for r in rides:
            cb = r["cb"]
            if cb and cb["dh"] >= MIN_SUSTAINED_DH:
                eroll = Crr * M0 * G * cb["S_cosL"] / KEFF / 1000
                eaero = 0.5 * rho * CdA * cb["S_v2L"] / KEFF / 1000
                mh.append(M0 * (cb["emeas"] - eaero) / (cb["egrav"] + eroll))
        m = med_of(mh)
    else:
        m = m_fixed
    beta = m * G / KEFF
    p = {"m": m, "CdA": CdA, "Crr": Crr, "rho": rho, "keff": KEFF, "wind": WIND,
         "vmax": VMAX, "vstart": VSTART}
    deltas = []
    for r in rides:
        if not (r["emp"] >= beta * r["sm"][2] / 1000):     # same physical floor
            continue
        c = canonical(r["prof"], r["pw"], p)
        deltas.append(jsdiv(c["legE"] / 1000 - r["emp"], r["emp"]) * 100)
    out = {"m_hat": m, "n_clean": len(deltas),
           "canon_med": med_of([abs(x) for x in deltas]),
           "canon_sgn": med_of(deltas)}
    out["canon_lo"], out["canon_hi"] = median_ci([abs(x) for x in deltas])
    out["canon_sgn_lo"], out["canon_sgn_hi"] = median_ci(deltas)
    out["_deltas"] = deltas
    return out


# ---------------------------------------------------------------- corpus loading

def load_corpus(name: str) -> list[dict]:
    rides = []
    if name == "censo":
        man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
        files = [e["file"] for e in man if e.get("file")
                 and os.path.exists(os.path.join(DATA, e["file"]))]
        for f in (files[:40] if SMOKE else files):
            try:
                rec = reduce_ride(load_pts(os.path.join(DATA, f)), False, False)
                if rec:
                    rides.append(rec)
            except Exception:
                pass
        return rides
    man = json.load(open(os.path.join(DATA, f"strava_{name}_manifest.json")))
    cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
            and a["km"] >= 20 and a["altCov"] >= 0.99]
    for a in (cand[:40] if SMOKE else cand):
        try:
            meta: dict = {}
            pts = load_pts(os.path.join(DATA, a["file"]), meta)
            if meta.get("manufacturer") == ZWIFT:
                continue
            rec = reduce_ride(pts, True, True)
            if rec:
                rides.append(rec)
        except Exception:
            pass
    return rides


# ---------------------------------------------------------------- driver

def main_canon() -> None:
    """Tier B (Entry 30): canonical simulation, one-at-a-time around the anchor,
    leaning on the Entry-29-confirmed rho*CdA degeneracy (rho fixed at 1.13);
    one equal-product partner cell checks the degeneracy on the simulation."""
    corpora = ["censo", "ppaz", "jaam", "danlessa"]
    PARTNER = (0.40 * 1.13, 0.008, 1.00)               # bitwise-equal product
    oat = ([ANCHOR, (0.25, 0.008, 1.13), PARTNER] if SMOKE else
           [(a, 0.008, 1.13) for a in CDA_GRID]
           + [(0.40, b, 1.13) for b in CRR_GRID if b != 0.008]
           + [PARTNER])
    fails = 0
    rows = []
    for corpus in corpora:
        print(f"loading {corpus} …", flush=True)
        rides = load_corpus(corpus)
        print(f"  {len(rides)} rides reduced", flush=True)
        m_fixed_corpus = 78.0 if corpus == "censo" else None
        anchor_out = None
        for (CdA, Crr, rho) in oat:
            m_fixed = m_fixed_corpus
            if SMOKE and corpus != "censo":
                m_fixed = ANCHOR_M[corpus]
            out = eval_canon(rides, CdA, Crr, rho, m_fixed)
            if (CdA, Crr, rho) == ANCHOR:
                anchor_out = out
                if not SMOKE:
                    exp = ANCHOR_CANON[corpus]
                    ok = abs(out["canon_med"] - exp) <= 0.11
                    print(f"  GATE canon med {corpus}: {to_fixed(out['canon_med'], 2)} "
                          f"vs {exp} {'OK' if ok else 'FAIL'}")
                    fails += 0 if ok else 1
                    if corpus in ANCHOR_M:
                        ok = abs(out["m_hat"] - ANCHOR_M[corpus]) <= 0.15
                        print(f"  GATE m̂ {corpus}: {to_fixed(out['m_hat'], 1)} "
                              f"{'OK' if ok else 'FAIL'}")
                        fails += 0 if ok else 1
                av = sorted(abs(x) for x in out["_deltas"])
                if len(av) >= 20:
                    blo, bhi = mulberry_boot_ci(av)
                    tol = 0.3 if len(av) >= 150 else (1.5 if len(av) >= 50 else 3.0)
                    ok = (abs(blo - out["canon_lo"]) <= tol
                          and abs(bhi - out["canon_hi"]) <= tol)
                    print(f"  GATE CI method {corpus}: order-stat "
                          f"[{to_fixed(out['canon_lo'], 2)}, {to_fixed(out['canon_hi'], 2)}] "
                          f"vs bootstrap [{to_fixed(blo, 2)}, {to_fixed(bhi, 2)}] "
                          f"{'OK' if ok else 'FAIL'}")
                    fails += 0 if ok else 1
            if (CdA, Crr, rho) == PARTNER and anchor_out is not None:
                d = abs(out["canon_med"] - anchor_out["canon_med"])
                ok = d <= 1e-9
                print(f"  GATE Q1 canon degeneracy {corpus}: |Δmed| = {d:.2e} "
                      f"{'OK' if ok else 'FAIL'}")
                fails += 0 if ok else 1
            row = {"corpus": corpus, "CdA": CdA, "Crr": Crr, "rho": rho,
                   "rhoCdA": rho * CdA}
            row.update({k: v for k, v in out.items() if not k.startswith("_")})
            rows.append(row)
    cols = list(rows[0].keys())
    out_path = os.path.join(RESULTS, "param_sweep_canon.csv" if not SMOKE
                            else "param_sweep_canon_smoke.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (to_fixed(v, 4) if isinstance(v, float) else v)
                        for k, v in r.items()})
    print(f"\nwrote {os.path.basename(out_path)} ({len(rows)} rows)")
    if fails:
        print(f"{fails} GATE(S) FAILED", file=sys.stderr)
        sys.exit(1)
    print("all sweep gates pass")


def main() -> None:
    corpora = ["censo", "ppaz", "jaam", "danlessa"]
    combos = ([(ANCHOR), (0.25, 0.004, 1.00), (0.50, 0.014, 1.225)] if SMOKE
              else [(a, b, c) for a in CDA_GRID for b in CRR_GRID for c in RHO_GRID])
    fails = 0
    rows = []
    for corpus in corpora:
        print(f"loading {corpus} …", flush=True)
        rides = load_corpus(corpus)
        print(f"  {len(rides)} rides reduced", flush=True)
        m_fixed_corpus = 78.0 if corpus == "censo" else None
        anchor_m = None
        for (CdA, Crr, rho) in combos:
            m_fixed = m_fixed_corpus
            if SMOKE and corpus != "censo":
                m_fixed = ANCHOR_M[corpus]             # smoke subset can't re-invert
            if FREEZE_M and corpus != "censo":
                if anchor_m is None:
                    anchor_m = eval_combo(rides, *ANCHOR, None)["m_hat"]
                m_fixed = anchor_m
            out = eval_combo(rides, CdA, Crr, rho, m_fixed)
            # ---- gates at the anchor combination ----
            if (CdA, Crr, rho) == ANCHOR:
                if not SMOKE and corpus in ANCHOR_M:
                    ok = abs(out["m_hat"] - ANCHOR_M[corpus]) <= 0.15
                    print(f"  GATE m̂ {corpus}: {to_fixed(out['m_hat'], 1)} vs "
                          f"{ANCHOR_M[corpus]} {'OK' if ok else 'FAIL'}")
                    fails += 0 if ok else 1
                for v in VARIANTS:
                    exp = ANCHOR_MED.get((corpus, v))
                    if exp is not None and not SMOKE:
                        ok = abs(out[f"{v}_med"] - exp) <= 0.11
                        print(f"  GATE med {corpus}/{v}: {to_fixed(out[f'{v}_med'], 2)} "
                              f"vs {exp} {'OK' if ok else 'FAIL'}")
                        fails += 0 if ok else 1
                # CI-method cross-check (both modes; cheap: one cell per corpus)
                av = sorted(abs(x) for x in out["_sm_geom_deltas"])
                if len(av) >= 20:
                    blo, bhi = mulberry_boot_ci(av)
                    olo, ohi = out["sm_geom_lo"], out["sm_geom_hi"]
                    # order-stat is conservative; the two converge with n — at
                    # small n (smoke subsets, censo) allow the known gap
                    tol = 0.3 if len(av) >= 150 else (1.5 if len(av) >= 50 else 3.0)
                    ok = abs(blo - olo) <= tol and abs(bhi - ohi) <= tol
                    print(f"  GATE CI method {corpus}: order-stat [{to_fixed(olo, 2)}, "
                          f"{to_fixed(ohi, 2)}] vs bootstrap [{to_fixed(blo, 2)}, "
                          f"{to_fixed(bhi, 2)}] {'OK' if ok else 'FAIL'}")
                    fails += 0 if ok else 1
            row = {"corpus": corpus, "CdA": CdA, "Crr": Crr, "rho": rho,
                   "rhoCdA": rho * CdA}
            row.update({k: v for k, v in out.items() if not k.startswith("_")})
            rows.append(row)
        # ---- P1 degeneracy gate: equal ρ·CdA, different (ρ, CdA) — must be identical
        a1 = eval_combo(rides, 0.40, 0.008, 1.13, m_fixed_corpus)
        a2 = eval_combo(rides, 0.452, 0.008, 1.00, m_fixed_corpus)
        d = max(abs(a1[f"{v}_med"] - a2[f"{v}_med"]) for v in VARIANTS
                if is_finite(a1[f"{v}_med"]))
        ok = d <= 1e-9
        print(f"  GATE P1 degeneracy {corpus}: max|Δmed| = {d:.2e} {'OK' if ok else 'FAIL'}")
        fails += 0 if ok else 1

    cols = list(rows[0].keys())
    out_path = os.path.join(RESULTS, "param_sweep.csv" if not SMOKE
                            else "param_sweep_smoke.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (to_fixed(v, 4) if isinstance(v, float) else v)
                        for k, v in r.items()})
    print(f"\nwrote {os.path.basename(out_path)} ({len(rows)} rows)")
    if fails:
        print(f"{fails} GATE(S) FAILED", file=sys.stderr)
        sys.exit(1)
    print("all sweep gates pass")


if __name__ == "__main__":
    main_canon() if CANON else main()
