#!/usr/bin/env python3
"""Entry 31 — D1 (longões) re-run under the FROZEN shared-constants protocol.

The 2026-07-28 adversarial review (blocking finding B1) established that the
historical D1 scoreboard (compare.py / Table 2 of the paper) is evaluated
with per-ride SHEET physics (each ride's own m/Crr/CdA/ρ/k_eff/wind from
longoes.xlsx) and the sheet's hand-entered per-ride ε — not the protocol the
paper states. Danilo's call: re-run D1 under the frozen protocol and
republish Table 2 (option (b)), rather than merely disclosing (a).

Frozen protocol (identical to D2–D5's manifest pipeline):
  Crr 0.008 · CdA 0.40 · ρ 1.13 · k_eff 0.98 · wind 0 (literature-typical
  priors); mass = the ride log's per-ride logged system mass (the one
  legitimate per-rider input — the author's mass IS known here, no inversion
  needed); v_f = flat_eq_speed(extracted flat-regime power); ε frozen as the
  dynamic ε_d = clamp01(ε_coast − 0.13) (eps_geom, fallback 0.20) or the
  flat ε_f = 0.20. No per-ride ε, no sheet physics.

Rows (per-ride Δ% in the CSV): form 1 (original: aero everywhere, raw h±),
form 2 (split, raw), form 3 (split + deadband), form 4 (split + scalar c
correction) — each under ε_d and ε_f — plus the canonical simulation with
the same frozen constants and the ride's own regime powers. Also recomputed
under frozen physics: the conservation residual, the sustained-climb
energy-balance ratio (the §3.1 attribution check), and paired sign tests
(form 3 vs canonical, form 4 vs canonical, form 2 vs form 1).

Output: data/results/longoes_frozen.csv + a console scoreboard with
mulberry32 bootstrap 95% CIs (the gate convention).

Run: python3 src/harness/longoes_frozen.py
"""

from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    climb_balance, deadband, empirical_kj,
                                    eps_geom, extract_regime_powers,
                                    flat_eq_speed, is_finite, jsdiv, load_pts,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
FROZEN = {"Crr": 0.008, "CdA": 0.40, "rho": 1.13, "keff": 0.98, "wind": 0.0}

inputs = json.load(open(os.path.join(DATA, "model_inputs.json")))


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


def sign_p(w: int, l: int) -> float:
    n = w + l
    p = 0.0
    for k in range(n + 1):
        pk = math.comb(n, k) / 2 ** n
        if k <= min(w, l) or k >= max(w, l):
            p += pk
    return min(1.0, p)


rows = []
SC = {"emeas": 0.0, "egrav": 0.0, "eroll": 0.0, "eaero": 0.0, "dh": 0.0, "n": 0}
cons_max = 0.0
for e in inputs:
    if not e.get("file") or not e.get("has_power"):
        continue
    pts = load_pts(os.path.join(DATA, e["file"]))
    phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile(phys, ENGINE_DX)
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
          "flat": flat,
          "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
          "climbThr": CLIMB_THR, "descThr": DESC_THR}
    p = {**FROZEN, "m": e["m"], "vmax": VMAX, "vstart": VSTART}
    vf = flat_eq_speed(pw["flat"], p)
    emp = empirical_kj(pts)
    epsG = eps_geom(prof, p, vf)
    eps_d = epsG if is_finite(epsG) else 0.2
    opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                        "descThr": DESC_THR, "climbPower": pw["climb"]}
    c = canonical(prof, pw, p)
    resid = abs(p["keff"] * c["legE"]
                - (c["dKE"] + c["Wrr"] + c["Waero"] + c["Wgrav"] + c["Wbrake"])) \
        / max(1, p["keff"] * c["legE"])
    cons_max = max(cons_max, resid)
    hp_raw = sum(max(0, prof["h"][i] - prof["h"][i - 1]) for i in range(1, len(prof["h"])))
    hp_sm = sum(max(0, profS["h"][i] - profS["h"][i - 1]) for i in range(1, len(profS["h"])))
    row = {"ride": e["label"], "emp": emp, "m": e["m"], "vf_kmh": vf * 3.6,
           "epsG": eps_d, "canon": c["legE"] / 1000,
           "canon_d": jsdiv(c["legE"] / 1000 - emp, emp) * 100,
           "noise_rate": (hp_raw - hp_sm) / (prof["x"][-1] / 1000)}
    for tag, eps in (("d", eps_d), ("f", 0.20)):
        a1 = approximate(prof, p, vf, eps, opt("off"))      # form 1: original
        a2 = approximate(prof, p, vf, eps, opt("zero"))     # form 2: split, raw
        a3 = approximate(profS, p, vf, eps, opt("zero"))    # form 3: split + deadband
        km = (max(0, 1 - 3 * (prof["x"][-1] / 1000) / a2["hplus"])
              if a2["hplus"] > 0 else 1)
        e4 = a2["roll"] + a2["aero"] + km * (a2["climb"] + a2["recov"])   # form 4 (J)
        for name, E in (("f1", a1["E"]), ("f2", a2["E"]), ("f3", a3["E"]), ("f4", e4)):
            row[f"{name}_{tag}"] = jsdiv(E / 1000 - emp, emp) * 100
    cb = climb_balance(pts, p)
    for k in ("emeas", "egrav", "eroll", "eaero", "dh"):
        SC[k] += cb[k]
    SC["n"] += cb["n"]
    rows.append(row)

print(f"D1 FROZEN-PROTOCOL RE-RUN — {len(rows)} rides · "
      f"max conservation resid {cons_max:.2e} (must be ≤ 1e-6)")
print(f"frozen: Crr {FROZEN['Crr']} CdA {FROZEN['CdA']} ρ {FROZEN['rho']} "
      f"k_eff {FROZEN['keff']} wind 0 · mass = per-ride logged · ε ∈ {{ε_d, ε_f = 0.20}}\n")

COLS = [("form 1 · ε_d (original)", "f1_d"), ("form 2 · ε_d (split)", "f2_d"),
        ("form 3 · ε_d (split+deadband)", "f3_d"), ("form 4 · ε_d (split+scalar c)", "f4_d"),
        ("form 3 · ε_f=0.20", "f3_f"), ("form 4 · ε_f=0.20", "f4_f"),
        ("canonical (frozen constants)", "canon_d")]
print("model".ljust(32) + "med|Δ%| [95% CI]".rjust(22) + "medΔ% [95% CI]".rjust(24))
for lab, key in COLS:
    av = [abs(r[key]) for r in rows if is_finite(r[key])]
    sv = [r[key] for r in rows if is_finite(r[key])]
    alo, ahi = boot_ci(av, 42)
    slo, shi = boot_ci(sv, 43)
    print(lab.ljust(32)
          + f"{to_fixed(med_of(av), 2)} [{to_fixed(alo, 1)}, {to_fixed(ahi, 1)}]".rjust(22)
          + f"{to_fixed(med_of(sv), 2)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]".rjust(24))

print("\npaired sign tests (|Δ%|):")
for la, ka, lb, kb in (("form 2", "f2_d", "form 1", "f1_d"),
                       ("form 3", "f3_d", "canonical", "canon_d"),
                       ("form 4", "f4_d", "canonical", "canon_d")):
    w = sum(1 for r in rows if abs(r[ka]) < abs(r[kb]))
    l = sum(1 for r in rows if abs(r[ka]) > abs(r[kb]))
    print(f"  {la} vs {lb}: closer on {w}/{w + l}, p = {to_fixed(sign_p(w, l), 4)}")

nr = sorted(r["noise_rate"] for r in rows)
n_ = len(nr)
print(f"\nascent-noise accumulation (raw − deadband h₊ per route-km): "
      f"median {to_fixed((nr[(n_-1)//2] + nr[n_//2]) / 2, 2)} m/km, "
      f"IQR {to_fixed(nr[int(0.25*(n_-1))], 1)}–{to_fixed(nr[int(0.75*(n_-1))], 1)} "
      f"— the measurement behind c ≈ 3 m/km (form 4)")

ratio = SC["emeas"] / (SC["egrav"] + SC["eroll"] + SC["eaero"])
print(f"\nsustained-climb balance (frozen physics): {SC['n']} sections, "
      f"Σ measured {js_str(math.floor(SC['emeas'] + 0.5))} vs expected "
      f"{js_str(math.floor(SC['egrav'] + SC['eroll'] + SC['eaero'] + 0.5))} kJ "
      f"→ ratio {to_fixed(ratio, 2)}")

cols = list(rows[0].keys())
with open(os.path.join(RESULTS, "longoes_frozen.csv"), "w", encoding="utf-8") as fh:
    fh.write(",".join(cols) + "\n")
    for r in rows:
        fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 3))
                          for v in (r[k] for k in cols)) + "\n")
print(f"\nwrote longoes_frozen.csv ({len(rows)} rides)")
