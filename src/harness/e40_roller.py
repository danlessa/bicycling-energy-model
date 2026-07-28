#!/usr/bin/env python3
"""Entry 40 — roller recycling: the recyclable-energy-share covariate vs the
form-3 residual.

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 40 BEFORE any result was
seen. Per ride, on the τ = 2 m deadbanded profile, monotone-run decomposition
gives drop→gap→rise triples; the recyclable drop is
    rec_i = min(A_drop, A_rise, h_KE) · exp(−gap/λ)
with h_KE = v_meas²/2G and λ = m/(ρ·ĈdA_reg) (physics joined from
e35_residual.csv). Regressor RES = 100·β·Σrec/E_meas (% of ride energy in
momentum-payable form); the OLS slope of Δ%(f3_d, regime physics) on RES
estimates the transfer efficiency η directly. P3 ledger check: RES vs the
Entry-36 measured gap δ on the real-descent subset (must be ≈ null).

Env: E40_SMOKE=1 (40 rides/corpus).
Run: python3 src/harness/e40_roller.py
Output: data/results/e40_roller.csv + console tables.
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

from bicycling_energy_model import (build_profile, deadband, is_finite,
                                    load_pts, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
SMOKE = os.environ.get("E40_SMOKE") == "1"

ENGINE_DX, TAU, RHO, KEFF = 5, 2.0, 1.13, 0.98
ZWIFT = 260


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


def ranks(v: list[float]) -> list[float]:
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    for rank, i in enumerate(idx):
        r[i] = rank
    return r


def spearman(xs: list[float], ys: list[float]) -> float:
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    den = math.sqrt(sum((r - mx) ** 2 for r in rx) * sum((r - my) ** 2 for r in ry))
    return num / den if den > 0 else float("nan")


def ols_slope(xs: list[float], ys: list[float]) -> float:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return (sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs))) / den
            if den > 0 else float("nan"))


E35 = {}
with open(os.path.join(RESULTS, "e35_residual.csv"), encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        E35[(r["corpus"], r["ride"])] = r
E36 = {}
with open(os.path.join(RESULTS, "e36_eps0.csv"), encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        E36[(r["corpus"], r["ride"])] = r


def monotone_runs(x: list[float], h: list[float]) -> list[tuple[str, float, float]]:
    """(kind, amplitude, length) runs over the deadbanded profile."""
    runs = []
    i = 1
    n = len(h)
    while i < n:
        dh = h[i] - h[i - 1]
        kind = "rise" if dh > 1e-9 else ("drop" if dh < -1e-9 else "flat")
        j = i
        amp = 0.0
        x0 = x[i - 1]
        while j < n:
            d = h[j] - h[j - 1]
            k2 = "rise" if d > 1e-9 else ("drop" if d < -1e-9 else "flat")
            if k2 != kind:
                break
            amp += d
            j += 1
        runs.append((kind, abs(amp), x[j - 1] - x0))
        i = j
    return runs


def recyclable(runs: list[tuple[str, float, float]], h_ke: float,
               lam: float) -> tuple[float, float, int]:
    """Σ rec_i over drop→(flat gap)→rise triples; also total drop and count."""
    total = 0.0
    hdrop = 0.0
    n_rec = 0
    for i, (kind, amp, _ln) in enumerate(runs):
        if kind != "drop":
            continue
        hdrop += amp
        gap = 0.0
        j = i + 1
        if j < len(runs) and runs[j][0] == "flat":
            gap = runs[j][2]
            j += 1
        if j < len(runs) and runs[j][0] == "rise":
            rec = min(amp, runs[j][1], h_ke) * math.exp(-gap / lam)
            if rec > 0:
                total += rec
                n_rec += 1
    return total, hdrop, n_rec


def iter_corpus(name: str):
    if name == "longoes":
        for e in json.load(open(os.path.join(DATA, "model_inputs.json"))):
            if not e.get("file") or not e.get("has_power"):
                continue
            yield (os.path.join(DATA, e["file"]), e["label"])
        return
    if name == "censo":
        man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
        files = [e["file"] for e in man if e.get("file")
                 and os.path.exists(os.path.join(DATA, e["file"]))]
        for f in (files[:40] if SMOKE else files):
            yield (os.path.join(DATA, f), os.path.basename(f))
        return
    man = json.load(open(os.path.join(DATA, f"strava_{name}_manifest.json")))
    cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
            and a["km"] >= 20 and a["altCov"] >= 0.99]
    for a in (cand[:40] if SMOKE else cand):
        yield (os.path.join(DATA, a["file"]), os.path.basename(a["file"]))


def main() -> None:
    all_rows = []
    for corpus in ("longoes", "censo", "ppaz", "jaam", "danlessa"):
        rows = []
        for path, ride in iter_corpus(corpus):
            j = E35.get((corpus, ride))
            if j is None:
                continue
            try:
                meta: dict = {}
                pts = load_pts(path, meta)
                if meta.get("manufacturer") == ZWIFT:
                    continue
                prof = resample_profile(build_profile(
                    [q["x"] for q in pts], [q["alt"] for q in pts]), ENGINE_DX)
            except Exception:
                continue
            if prof["x"][-1] - prof["x"][0] < 3000:
                continue
            m = float(j["m"])
            cda = float(j["cda_reg"])
            vm = float(j["v_meas_kmh"]) / 3.6 if j.get("v_meas_kmh") not in ("", "NaN") else float("nan")
            if not is_finite(vm) or vm <= 0:
                continue
            h_ke = vm * vm / (2 * G)
            lam = m / (RHO * cda)
            beta = m * G / KEFF
            hS = deadband(prof["h"], TAU)
            rec, hdrop, n_rec = recyclable(
                monotone_runs(prof["x"], hS), h_ke, lam)
            emp = float(j["emp"])
            res = 100.0 * beta * rec / (emp * 1000.0)
            e36 = E36.get((corpus, ride))
            row = {"corpus": corpus, "ride": ride, "res_pct": res,
                   "rec_m": rec, "hdrop_m": hdrop,
                   "share": rec / hdrop if hdrop > 0 else float("nan"),
                   "n_rollers": n_rec, "h_ke": h_ke, "lam": lam,
                   "f3_d_reg": float(j["f3_d_reg"]),
                   "f3_d_seg": float(j["f3_d_seg"]),
                   "gapR": (float(e36["gapR"]) if e36 and e36.get("gapR") not in ("", "NaN")
                            else float("nan")),
                   "sbar": (float(e36["balR_sbar"]) if e36 and e36.get("balR_sbar") not in ("", "NaN")
                            else float("nan"))}
            rows.append(row)
        all_rows.extend(rows)
        if not rows:
            continue
        xs = [r["res_pct"] for r in rows]
        ys = [r["f3_d_reg"] for r in rows]
        rho = spearman(xs, ys)
        slope = ols_slope(xs, ys)
        # bootstrap CI on the slope (η̂), B=10⁴, seed 42
        rand = rng(42)
        n, B = len(rows), 10000
        st = []
        for _ in range(B):
            idx = [int(rand() * n) for _ in range(n)]
            st.append(ols_slope([xs[i] for i in idx], [ys[i] for i in idx]))
        st = sorted(s for s in st if is_finite(s))
        lo, hi = st[int(0.025 * len(st))], st[math.ceil(0.975 * len(st)) - 1]
        print(f"\n== {corpus} — {len(rows)} rides ==")
        print(f"RES median {to_fixed(med_of(xs), 2)}% of E "
              f"(share of drop {to_fixed(med_of([r['share'] for r in rows]), 2)}, "
              f"{to_fixed(med_of([float(r['n_rollers']) for r in rows]), 0)} rollers/ride, "
              f"h_KE {to_fixed(med_of([r['h_ke'] for r in rows]), 1)} m, "
              f"λ {to_fixed(med_of([r['lam'] for r in rows]), 0)} m)")
        print(f"P1/P2: OLS coeff η̂ = {to_fixed(slope, 2)} [{to_fixed(lo, 2)}, {to_fixed(hi, 2)}] · "
              f"Spearman ρ(RES, Δ%) = {to_fixed(rho, 3)}")
        real = [r for r in rows if is_finite(r["gapR"]) and is_finite(r["sbar"])
                and r["sbar"] >= 0.03]
        if len(real) >= 15:
            rho3 = spearman([r["res_pct"] for r in real], [r["gapR"] for r in real])
            print(f"P3 ledger check: ρ(RES, δ) = {to_fixed(rho3, 3)} "
                  f"on {len(real)} real-descent rides")

    cols = list(all_rows[0].keys())
    with open(os.path.join(RESULTS, "e40_roller.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in all_rows:
            fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 4))
                              for v in (r[k] for k in cols)) + "\n")
    print(f"\nwrote e40_roller.csv ({len(all_rows)} rides)")


if __name__ == "__main__":
    main()
