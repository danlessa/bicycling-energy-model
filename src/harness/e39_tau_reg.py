#!/usr/bin/env python3
"""Entry 39 — the DECONFOUNDED τ-sweep: Entry 38 at the regime-consistent physics.

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 39 BEFORE any result was
seen. Identical to Entry 38's sweep except the physics: per-ride
regime-consistent constants (m̂ / Ĉrr / ĈdA_reg / wind) joined from
e35_residual.csv — the honest pair with near-zero standing biases, so
argmin med|Δ%| reads the filter scale instead of bias compensation.
Primary variant: ε_d on EVERY corpus (at the regime-consistent α the
honest pair is (α, ε_d) everywhere — Entry 35). τ* CI at B = 1,000
(disclosed); h_KE targets from corpus median measured flat speed.

Env: E39_SMOKE=1 (40 rides/corpus).
Run: python3 src/harness/e39_tau_reg.py
Output: data/results/e39_tau_reg.csv + console tables.
"""

from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approximate, build_profile, deadband,
                                    empirical_kj, eps_geom,
                                    extract_regime_powers, flat_eq_speed,
                                    is_finite, jsdiv, load_pts,
                                    measured_flat_speed, overall_mean_power,
                                    resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
SMOKE = os.environ.get("E39_SMOKE") == "1"

VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX = 0.02, -0.015, 5
FROZEN = {"Crr": 0.008, "CdA": 0.40, "rho": 1.13, "keff": 0.98, "wind": 0.0}
ANCHOR_M = {"longoes": None, "censo": 78.0, "ppaz": 74.5, "jaam": 101.9,
            "danlessa": 74.7}

import csv as _csv
E35J = {}
with open(os.path.join(RESULTS, "e35_residual.csv"), encoding="utf-8") as _fh:
    for _r in _csv.DictReader(_fh):
        E35J[(_r["corpus"], _r["ride"])] = _r
ZWIFT = 260
TAUS = [x / 2 for x in range(1, 13)]          # 0.5 … 6.0
PRIMARY = {"longoes": "d", "censo": "d", "ppaz": "d", "jaam": "d",
           "danlessa": "d"}      # eps_d everywhere: the honest pair at regime physics
PUBLISHED_T20 = {"censo": ("d", 4.6), "ppaz": ("d", 3.1), "jaam": ("d", 3.2),
                 "danlessa": ("d", 4.9)}       # Entry-35 regime column parity at τ=2


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


def sign_p(w: int, l: int) -> float:
    n = w + l
    p = 0.0
    for k in range(n + 1):
        pk = math.comb(n, k) / 2 ** n
        if k <= min(w, l) or k >= max(w, l):
            p += pk
    return min(1.0, p)


def run_ride(pts: list[dict], corpus: str, ride: str,
             m_logged: float | None) -> dict | None:
    emp = empirical_kj(pts)
    if not is_finite(emp) or emp <= 0:
        return None
    prof = resample_profile(build_profile([q["x"] for q in pts],
                                          [q["alt"] for q in pts]), ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None
    j = E35J.get((corpus, ride))
    if j is not None:
        p = {"m": float(j["m"]), "Crr": float(j["crr"]), "CdA": float(j["cda_reg"]),
             "rho": 1.13, "keff": 0.98, "wind": float(j["wind"]),
             "vmax": VMAX, "vstart": VSTART}
    else:
        m = m_logged if m_logged is not None else ANCHOR_M[corpus]
        p = {**FROZEN, "m": m, "vmax": VMAX, "vstart": VSTART}
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat
    vf = flat_eq_speed(flat, p)
    epsG = eps_geom(prof, p, vf)                       # raw profile: τ-independent
    eps_d = epsG if is_finite(epsG) else 0.2
    opt = {"climbAeroMode": "zero", "climbThr": CLIMB_THR,
           "descThr": DESC_THR, "climbPower": pw_climb}
    vm = measured_flat_speed(pts)
    row = {"corpus": corpus, "ride": ride, "emp": emp,
           "v_meas_kmh": vm * 3.6 if vm else float("nan")}
    x_km = (prof["x"][-1] - prof["x"][0]) / 1000
    for tau in TAUS:
        hS = deadband(prof["h"], tau)
        profS = {"x": prof["x"], "h": hS}
        for tag, eps in (("d", eps_d), ("f", 0.20)):
            a3 = approximate(profS, p, vf, eps, opt)
            row[f"t{int(tau*10):02d}_{tag}"] = jsdiv(a3["E"] / 1000 - emp, emp) * 100
        hp_raw = sum(max(0, prof["h"][i] - prof["h"][i - 1])
                     for i in range(1, len(prof["h"])))
        hp_s = sum(max(0, hS[i] - hS[i - 1]) for i in range(1, len(hS)))
        row[f"c{int(tau*10):02d}"] = (hp_raw - hp_s) / x_km
    return row


def iter_corpus(name: str):
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
        tag = PRIMARY[corpus]
        vms = [r["v_meas_kmh"] for r in rows if is_finite(r["v_meas_kmh"])]
        v_med = med_of(vms)
        h_ke = (v_med / 3.6) ** 2 / (2 * G)
        print(f"\n== {corpus} — {len(rows)} rides · primary ε_{tag} · "
              f"median v_meas {to_fixed(v_med, 1)} km/h → h_KE {to_fixed(h_ke, 2)} m ==")
        print("τ(m)   med|Δ%| [95% CI]        bias [95% CI]        c(τ) m/km")
        meds = []
        for tau in TAUS:
            k = f"t{int(tau*10):02d}_{tag}"
            v = [r[k] for r in rows if is_finite(r[k])]
            av = [abs(x) for x in v]
            alo, ahi = boot_ci(av, 42)
            slo, shi = boot_ci(v, 43)
            cv = med_of([r[f"c{int(tau*10):02d}"] for r in rows])
            meds.append((med_of(av), tau))
            print(f"{tau:4.1f}  {to_fixed(med_of(av), 2).rjust(6)} "
                  f"[{to_fixed(alo, 1)}, {to_fixed(ahi, 1)}]   "
                  f"{to_fixed(med_of(v), 2).rjust(6)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]   "
                  f"{to_fixed(cv, 1)}")
        tau_star = min(meds)[1]
        # bootstrap CI on tau* (B=1000, disclosed)
        rand = rng(42)
        n, B = len(rows), 1000
        stars = []
        keys = [f"t{int(tau*10):02d}_{tag}" for tau in TAUS]
        vals = [[abs(r[k]) for k in keys] for r in rows]
        for _ in range(B):
            idx = [int(rand() * n) for _ in range(n)]
            best, bt = float("inf"), TAUS[0]
            for ti, tau in enumerate(TAUS):
                mv = med_of([vals[i][ti] for i in idx])
                if mv < best:
                    best, bt = mv, tau
            stars.append(bt)
        stars.sort()
        print(f"τ* = {tau_star} m  [{stars[25]}, {stars[974]}]  (B=1,000)  "
              f"· h_KE target {to_fixed(h_ke, 2)} m")
        # P2 paired: τ=3.0 vs τ=2.0 on the primary variant
        k30, k20 = f"t30_{tag}", f"t20_{tag}"
        w = sum(1 for r in rows if abs(r[k30]) < abs(r[k20]))
        l = sum(1 for r in rows if abs(r[k30]) > abs(r[k20]))
        print(f"paired τ=3.0 vs τ=2.0 (ε_{tag}): closer on {w}/{w + l}, "
              f"p = {to_fixed(sign_p(w, l), 4)}")
        if corpus in PUBLISHED_T20:
            ptag, pub = PUBLISHED_T20[corpus]
            k = f"t20_{ptag}"
            got = med_of([abs(r[k]) for r in rows if is_finite(r[k])])
            ok = abs(got - pub) <= 0.11
            print(f"PARITY τ=2.0 ε_{ptag} vs Entry-35 regime: {to_fixed(got, 2)} vs {pub} "
                  + ("GATE-OK" if ok else "GATE-FAIL"))

    cols = list(all_rows[0].keys())
    with open(os.path.join(RESULTS, "e39_tau_reg.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in all_rows:
            fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 4))
                              for v in (r[k] for k in cols)) + "\n")
    print(f"\nwrote e39_tau_reg.csv ({len(all_rows)} rides)")


if __name__ == "__main__":
    main()
