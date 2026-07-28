#!/usr/bin/env python3
"""Entry 34 — execute the registered S-curve-deficit design.

The registration (MODEL_COMPARISON_JOURNAL.md Entry 34, fixed before any
fitting):
  1.  segment-level grain: per 30 m descent cell, deficit vs cell grade;
  1b. measure the factors — per grade bin, pedalling occupancy p_ped(s)
      (share of descent time at P > 10 W) and intensity P̄_ped(s); test the
      dilution model (δ ∝ 1/(v̄·s) at constant p·P̄) before attributing any
      fade to the S-curve;
  2.  per-rider logistic (ε₀', s₅₀, w) least squares on a CHRONOLOGICAL
      calibration half of the real-descent rides; nulls: frozen ε₀ = 0.13
      and the dilution-only model (plus a train-fitted constant, reported to
      attribute gains to *shape* vs mere refitting);
  3.  held-out chronological half, per-ride RMS of ε_bal − prediction;
      success = logistic ≥ 5% better than the FROZEN constant on ≥ 2 of 3
      riders;
  4.  failure mode: constant stays, S-curve published as refuted at this
      data's grade range.

Grade bins (fixed here, stated in the results): descent cells s ≤ −1.5%
binned at [1.5, 2, 3, 4, 5, 6, 8, 12, 20)%. Physics: frozen shared constants
(Crr 0.008, CdA 0.40, ρ 1.13, k_eff 0.98, wind 0), per-corpus anchor mass,
α at the MEASURED flat speed (the ε_bal convention). δ per bin uses the exact
ledger: δ_bin = E_legs,bin / (β · drop_bin).

Env: SCURVE_SMOKE=1 (40 rides/corpus).
Run: python3 src/harness/scurve_deficit.py
Output: data/results/scurve_deficit.csv (per-ride) + console tables.
"""

from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import is_finite, load_pts
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
SMOKE = os.environ.get("SCURVE_SMOKE") == "1"

PHYS = {"Crr": 0.008, "CdA": 0.40, "rho": 1.13, "keff": 0.98, "wind": 0.0}
MASS = {"ppaz": 74.5, "jaam": 101.9, "danlessa": 74.7}
ZWIFT = 260
DX, VSTOP, PED_W = 30, 0.5 / 3.6, 10.0
BIN_EDGES = [0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.12, 0.20]
EPS0_FROZEN = 0.13


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


def rms(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v) / len(v)) if v else float("nan")


def ride_stats(pts: list[dict], m: float) -> dict | None:
    """One pass: ride-level ε_bal/ε_coast/s̄/v̄₋ + per-bin cell accumulators."""
    if not pts or len(pts) < 2:
        return None
    mg = m * G
    beta = mg / PHYS["keff"]
    x0 = pts[0]["x"]
    total_m = pts[-1]["x"] - x0
    nc = math.floor(total_m / DX)
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

    cell_alt = [alt_at(x0 + k * DX) for k in range(nc + 1)]
    grade = [(cell_alt[k + 1] - cell_alt[k]) / DX for k in range(nc)]
    cE = [0.0] * nc          # ∫P dt (all samples)
    cT = [0.0] * nc          # Σdt
    cTped = [0.0] * nc       # Σdt at P > 10 W
    cEped = [0.0] * nc       # ∫P dt over pedalled samples
    cVs = [0.0] * nc
    cVt = [0.0] * nc
    for r in pts:
        k = math.floor((r["x"] - x0) / DX)
        if k < 0 or k >= nc:
            continue
        w = r.get("dt") or 1
        pw = r.get("power")
        cT[k] += w
        if pw is not None:
            cE[k] += pw * w
            if pw > PED_W:
                cTped[k] += w
                cEped[k] += pw * w
        if r.get("v") is not None and r["v"] >= VSTOP:
            cVs[k] += r["v"] * w
            cVt[k] += w
    sv = sw = 0.0
    for k in range(nc):
        if abs(grade[k]) < 0.01 and cVt[k] > 0:
            sv += cVs[k]
            sw += cVt[k]
    if not sw > 0:
        return None
    vf = sv / sw
    alpha = (PHYS["Crr"] * mg + 0.5 * PHYS["rho"] * PHYS["CdA"] * vf * vf) / PHYS["keff"]
    ab = alpha / beta
    Xd = Hd = Ed = Vd = Vt = cw = 0.0
    bins = [dict(t=0.0, tped=0.0, eped=0.0, e=0.0, drop=0.0, vs=0.0, vt=0.0)
            for _ in range(len(BIN_EDGES))]
    for k in range(nc):
        dh = cell_alt[k + 1] - cell_alt[k]
        if dh >= 0:
            continue
        drop, s = -dh, -grade[k]
        Xd += DX
        Hd += drop
        Ed += cE[k]
        Vd += cVs[k]
        Vt += cVt[k]
        cw += drop * min(1.0, ab / s)
        if s >= BIN_EDGES[0]:
            b = 0
            while b < len(BIN_EDGES) - 1 and s >= BIN_EDGES[b + 1]:
                b += 1
            bins[b]["t"] += cT[k]
            bins[b]["tped"] += cTped[k]
            bins[b]["eped"] += cEped[k]
            bins[b]["e"] += cE[k]
            bins[b]["drop"] += drop
            bins[b]["vs"] += cVs[k]
            bins[b]["vt"] += cVt[k]
    if Hd < 1:
        return None
    return {"epsBal": (alpha * Xd - Ed) / (beta * Hd), "epsCoast": cw / Hd,
            "sbar": Hd / Xd if Xd > 0 else float("nan"),
            "vdesc": Vd / Vt if Vt > 0 else float("nan"),
            "beta": beta, "bins": bins}


def logistic(s: float, s50: float, w: float) -> float:
    return 1.0 / (1.0 + math.exp((s - s50) / w))


def fit_models(train: list[dict]) -> dict:
    """Least squares on δ = ε_coast − ε_bal over the training rides."""
    d = [r["epsCoast"] - r["epsBal"] for r in train]
    # constant (train-fitted): mean
    c_fit = sum(d) / len(d)
    # dilution: δ = c / (v̄·s̄) — linear LS through origin
    u = [1.0 / (r["vdesc"] * r["sbar"]) for r in train]
    c_dil = (sum(di * ui for di, ui in zip(d, u)) / sum(ui * ui for ui in u)
             if sum(ui * ui for ui in u) > 0 else 0.0)
    # logistic: δ = ε₀'·g(s̄; s₅₀, w); ε₀' closed-form per (s₅₀, w) grid point
    best = (float("inf"), EPS0_FROZEN, 0.05, 0.01)
    s50_grid = [x / 400 for x in range(4, 81)]          # 1%..20% step 0.25%
    w_grid = [x / 400 for x in range(1, 25)]            # 0.25%..6% step 0.25%
    for s50 in s50_grid:
        for w in w_grid:
            g = [logistic(r["sbar"], s50, w) for r in train]
            gg = sum(x * x for x in g)
            if gg <= 0:
                continue
            e0 = sum(di * gi for di, gi in zip(d, g)) / gg
            e0 = max(0.0, min(0.6, e0))
            sse = sum((di - e0 * gi) ** 2 for di, gi in zip(d, g))
            if sse < best[0]:
                best = (sse, e0, s50, w)
    return {"c_fit": c_fit, "c_dil": c_dil,
            "e0": best[1], "s50": best[2], "w": best[3]}


def predict_resid(r: dict, model: str, f: dict) -> float:
    d = r["epsCoast"] - r["epsBal"]
    if model == "frozen":
        return d - EPS0_FROZEN
    if model == "const_fit":
        return d - f["c_fit"]
    if model == "dilution":
        return d - f["c_dil"] / (r["vdesc"] * r["sbar"])
    return d - f["e0"] * logistic(r["sbar"], f["s50"], f["w"])


def main() -> None:
    all_rows = []
    verdicts = []
    for corpus in ("ppaz", "jaam", "danlessa"):
        man = json.load(open(os.path.join(DATA, f"strava_{corpus}_manifest.json")))
        cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
                and a["km"] >= 20 and a["altCov"] >= 0.99]
        cand.sort(key=lambda a: a.get("date") or "")
        rides = []
        for a in (cand[:40] if SMOKE else cand):
            try:
                meta: dict = {}
                pts = load_pts(os.path.join(DATA, a["file"]), meta)
                if meta.get("manufacturer") == ZWIFT:
                    continue
                st = ride_stats(pts, MASS[corpus])
            except Exception:
                st = None
            if st is None or not (is_finite(st["epsBal"]) and is_finite(st["epsCoast"])
                                  and is_finite(st["vdesc"])):
                continue
            st["ride"] = os.path.basename(a["file"])
            st["date"] = a.get("date") or ""
            st["corpus"] = corpus
            rides.append(st)

        # ---- step 1b: measured factors per grade bin (whole corpus) ----
        beta = MASS[corpus] * G / PHYS["keff"]
        agg = [dict(t=0.0, tped=0.0, eped=0.0, e=0.0, drop=0.0, vs=0.0, vt=0.0)
               for _ in range(len(BIN_EDGES))]
        for r in rides:
            for b, cell in enumerate(r["bins"]):
                for key in agg[b]:
                    agg[b][key] += cell[key]
        print(f"\n== {corpus} — {len(rides)} rides with descent cells ==")
        print("bin s%      time_h  p_ped  P̄_ped(W)  v̄(km/h)   δ_bin  δ_dil(ref)")
        ref = None
        for b, a_ in enumerate(agg):
            if a_["t"] <= 0 or a_["drop"] < 50:
                continue
            lo = BIN_EDGES[b] * 100
            hi = BIN_EDGES[b + 1] * 100 if b + 1 < len(BIN_EDGES) else 99
            p_ped = a_["tped"] / a_["t"]
            pbar = a_["eped"] / a_["tped"] if a_["tped"] > 0 else 0.0
            vbar = a_["vs"] / a_["vt"] if a_["vt"] > 0 else float("nan")
            smid = (BIN_EDGES[b] + (BIN_EDGES[b + 1] if b + 1 < len(BIN_EDGES)
                                    else 0.25)) / 2
            delta = a_["e"] / (beta * a_["drop"])
            if ref is None and lo >= 3:
                ref = (p_ped, pbar)
            ddil = (ref[0] * ref[1] / (beta * vbar * smid)
                    if ref and vbar > 0 else float("nan"))
            print(f"[{lo:4.1f},{hi:4.1f})  {a_['t']/3600:6.1f}  {p_ped:5.2f}  "
                  f"{pbar:8.0f}  {vbar*3.6:7.1f}  {delta:6.3f}  {ddil:8.3f}")

        # ---- steps 2-4: chronological fit/test on real descents ----
        sub = [r for r in rides if r["sbar"] >= 0.03]
        half = len(sub) // 2
        train, test = sub[:half], sub[half:]
        if len(train) < 8 or len(test) < 8:
            print(f"fit/test skipped (real-descent n={len(sub)}: too thin)")
            continue
        f = fit_models(train)
        print(f"train n={len(train)} (dates {train[0]['date']}..{train[-1]['date']}) "
              f"test n={len(test)} ({test[0]['date']}..{test[-1]['date']})")
        print(f"fitted: const {f['c_fit']:.3f} · dilution c {f['c_dil']:.3f} · "
              f"logistic ε₀'={f['e0']:.3f} s₅₀={f['s50']*100:.2f}% w={f['w']*100:.2f}%")
        out = {}
        for model in ("frozen", "const_fit", "dilution", "logistic"):
            res = [predict_resid(r, model, f) for r in test]
            out[model] = rms(res)
        impr = 100 * (out["frozen"] - out["logistic"]) / out["frozen"]
        # bootstrap CI on the improvement (test rides, seed 42)
        rand = rng(42)
        n, B, stats = len(test), 10000, []
        for _ in range(B):
            samp = [test[int(rand() * n)] for _ in range(n)]
            rf = rms([predict_resid(r, "frozen", f) for r in samp])
            rl = rms([predict_resid(r, "logistic", f) for r in samp])
            stats.append(100 * (rf - rl) / rf)
        stats.sort()
        lo_ci, hi_ci = stats[int(0.025 * B)], stats[math.ceil(0.975 * B) - 1]
        ok = impr >= 5.0
        verdicts.append((corpus, impr, ok))
        print("held-out RMS: frozen {} · const-fit {} · dilution {} · logistic {}"
              .format(*(to_fixed(out[m], 4) for m in
                        ("frozen", "const_fit", "dilution", "logistic"))))
        print(f"logistic vs frozen: {to_fixed(impr, 1)}% improvement "
              f"[{to_fixed(lo_ci, 1)}, {to_fixed(hi_ci, 1)}] "
              f"→ {'PASS' if ok else 'fail'} (needs ≥ 5%)")
        for r in rides:
            all_rows.append({k: r[k] for k in
                             ("corpus", "ride", "date", "epsBal", "epsCoast",
                              "sbar", "vdesc")})

    n_pass = sum(1 for _, _, ok in verdicts if ok)
    print(f"\nREGISTERED VERDICT: logistic beats frozen by ≥5% on {n_pass}/3 riders "
          f"→ S-curve {'CONFIRMED' if n_pass >= 2 else 'NOT confirmed (constant stays)'}")

    if all_rows:
        cols = list(all_rows[0].keys())
        with open(os.path.join(RESULTS, "scurve_deficit.csv"), "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for r in all_rows:
                fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 4))
                                  for v in (r[k] for k in cols)) + "\n")
        print(f"wrote scurve_deficit.csv ({len(all_rows)} rides)")


if __name__ == "__main__":
    main()
