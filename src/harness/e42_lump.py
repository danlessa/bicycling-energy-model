#!/usr/bin/env python3
"""Entry 42 — the lumped ε_d: is mean descent grade a valid proxy at energy level?

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 42 BEFORE any result was
seen. Per ride under the regime-consistent physics (m̂_r / Ĉ_rr,r / ĈdA_r^reg /
wind joined from e35_residual.csv):

  s̄_lump  = h̃₋ / x₋      (τ = 2 m deadbanded descent total over the
                            descending distance: 30 m cells of the deadbanded
                            profile with grade ≤ −1.5%)
  ε_lump  = min(1, (α/β)/s̄_lump) − ε₀    (unclamped; the §4.1.2 recipe's
                                           arithmetic, α/β at the model v_f)

Scored: F3/F4 · ε_lump vs F3/F4 · ε_d (drop-weighted eps_geom) vs measured
energy — accuracy AND bias with 95% CIs, paired sign tests, and the
mixed-descent diagnostic (ε_lump − ε_d and |paired Δ%-diff| vs descent-grade
dispersion). Parity gate: the F3·ε_d column must reproduce Entry 35's regime
medians (4.6 / 3.1 / 3.2 / 4.9 on D2–D5, 6.6 on D1).

Env: E42_SMOKE=1 (40 rides/corpus).
Run: python3 src/harness/e42_lump.py
Output: data/results/e42_lump.csv + console tables.
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
                                    eps_geom, extract_regime_powers,
                                    flat_eq_speed, is_finite, jsdiv, load_pts,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import EPS0, G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
SMOKE = os.environ.get("E42_SMOKE") == "1"

VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU = 0.02, -0.015, 5, 2
RHO, KEFF = 1.13, 0.98
ANCHOR_M = {"longoes": None, "censo": 78.0, "ppaz": 74.5, "jaam": 101.9,
            "danlessa": 74.7}
FROZEN = {"Crr": 0.008, "CdA": 0.40}
ZWIFT = 260
CELL = 30.0
PARITY = {"longoes": 6.6, "censo": 4.6, "ppaz": 3.1, "jaam": 3.2,
          "danlessa": 4.9}


def med_of(xs: "list[float]") -> float:
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


def boot_ci(values: "list[float]", seed: int) -> "tuple[float, float]":
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


def ranks(v: "list[float]") -> "list[float]":
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    for rank, i in enumerate(idx):
        r[i] = rank
    return r


def spearman(xs: "list[float]", ys: "list[float]") -> float:
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    den = math.sqrt(sum((r - mx) ** 2 for r in rx) * sum((r - my) ** 2 for r in ry))
    return num / den if den > 0 else float("nan")


E35 = {}
with open(os.path.join(RESULTS, "e35_residual.csv"), encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        E35[(r["corpus"], r["ride"])] = r


def descent_stats(profS: dict) -> "dict | None":
    """x₋, h̃₋, and descent-cell grade dispersion on the deadbanded profile."""
    px, ph = profS["x"], profS["h"]
    x0 = px[0]
    nc = math.floor((px[-1] - x0) / CELL)
    if nc < 2:
        return None
    j = 0

    def h_at(d: float) -> float:
        nonlocal j
        while j < len(px) - 2 and px[j + 1] < d:
            j += 1
        seg = px[j + 1] - px[j]
        f = (d - px[j]) / seg if seg > 1e-9 else 0.0
        return ph[j] * (1 - f) + ph[j + 1] * f

    hs = [h_at(x0 + k * CELL) for k in range(nc + 1)]
    x_dn = h_dn = 0.0
    grades = []
    for k in range(nc):
        s = (hs[k + 1] - hs[k]) / CELL
        if s <= DESC_THR:
            x_dn += CELL
            h_dn += -(hs[k + 1] - hs[k])
            grades.append(-s)
    if x_dn <= 0 or h_dn < 1:
        return None
    mu = sum(grades) / len(grades)
    sd = math.sqrt(sum((g - mu) ** 2 for g in grades) / len(grades))
    return {"x_dn": x_dn, "h_dn": h_dn, "sbar_lump": h_dn / x_dn, "grade_sd": sd}


def run_ride(pts: list, corpus: str, ride: str, m_logged: "float | None") -> "dict | None":
    j = E35.get((corpus, ride))
    if j is None:
        return None
    emp = float(j["emp"])
    m, crr, cda, wind = (float(j["m"]), float(j["crr"]),
                         float(j["cda_reg"]), float(j["wind"]))
    p = {"m": m, "Crr": crr, "CdA": cda, "rho": RHO, "keff": KEFF,
         "wind": wind, "vmax": VMAX, "vstart": VSTART}
    prof = resample_profile(build_profile([q["x"] for q in pts],
                                          [q["alt"] for q in pts]), ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU)}
    ds = descent_stats(profS)
    if ds is None:
        return None
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat
    vf = flat_eq_speed(flat, p)
    epsG = eps_geom(prof, p, vf)
    eps_d = epsG if is_finite(epsG) else 0.2
    # the recipe's arithmetic: alpha/beta at model v_f, lumped grade
    mg = m * G
    aero_spd = vf + wind
    alpha = (crr * mg + 0.5 * RHO * cda * aero_spd * abs(aero_spd)) / KEFF
    beta = mg / KEFF
    eps_lump = min(1.0, (alpha / beta) / ds["sbar_lump"]) - EPS0
    opt = {"climbAeroMode": "zero", "climbThr": CLIMB_THR,
           "descThr": DESC_THR, "climbPower": pw_climb}
    row = {"corpus": corpus, "ride": ride, "emp": emp,
           "sbar_lump": ds["sbar_lump"], "grade_sd": ds["grade_sd"],
           "eps_d": eps_d, "eps_lump": eps_lump,
           "d_eps": eps_lump - eps_d}
    a2 = approximate(prof, p, vf, 0.20, opt)
    km = (max(0, 1 - 3 * (prof["x"][-1] / 1000) / a2["hplus"])
          if a2["hplus"] > 0 else 1)
    for tag, eps in (("d", eps_d), ("lump", eps_lump)):
        a3 = approximate(profS, p, vf, eps, opt)
        a2e = approximate(prof, p, vf, eps, opt)
        e4 = a2e["roll"] + a2e["aero"] + km * (a2e["climb"] + a2e["recov"])
        row[f"f3_{tag}"] = jsdiv(a3["E"] / 1000 - emp, emp) * 100
        row[f"f4_{tag}"] = jsdiv(e4 / 1000 - emp, emp) * 100
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
        meta = {}
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
        print(f"\n== {corpus} — {len(rows)} rides ==")
        print("model            med|Δ%| [95% CI]        bias [95% CI]")
        for lab, key in (("F3 · ε_d (drop-wt)", "f3_d"), ("F3 · ε_lump", "f3_lump"),
                         ("F4 · ε_d (drop-wt)", "f4_d"), ("F4 · ε_lump", "f4_lump")):
            v = [r[key] for r in rows if is_finite(r[key])]
            av = [abs(x) for x in v]
            alo, ahi = boot_ci(av, 42)
            slo, shi = boot_ci(v, 43)
            print(f"{lab.ljust(18)} {to_fixed(med_of(av), 2).rjust(6)} "
                  f"[{to_fixed(alo, 1)}, {to_fixed(ahi, 1)}]   "
                  f"{to_fixed(med_of(v), 2).rjust(7)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]")
        got = med_of([abs(r["f3_d"]) for r in rows])
        ok = abs(got - PARITY[corpus]) <= 0.11
        print(f"PARITY F3·ε_d vs Entry-35 regime: {to_fixed(got, 2)} vs {PARITY[corpus]} "
              + ("GATE-OK" if ok else "GATE-FAIL"))
        w = sum(1 for r in rows if abs(r["f3_lump"]) < abs(r["f3_d"]))
        l = sum(1 for r in rows if abs(r["f3_lump"]) > abs(r["f3_d"]))
        print(f"paired F3 lump vs drop-wt: lump closer on {w}/{w + l}, "
              f"p = {to_fixed(sign_p(w, l), 4)}")
        de = [r["d_eps"] for r in rows if is_finite(r["d_eps"])]
        deq = sorted(de)
        print(f"ε_lump − ε_d: med {to_fixed(med_of(de), 3)} "
              f"(IQR {to_fixed(deq[int(0.25*(len(deq)-1))], 2)}–"
              f"{to_fixed(deq[int(0.75*(len(deq)-1))], 2)})")
        dd = [(abs(r['f3_lump'] - r['f3_d']), r['grade_sd']) for r in rows
              if is_finite(r['f3_lump']) and is_finite(r['f3_d'])]
        rho = spearman([a for a, _ in dd], [b for _, b in dd])
        print(f"ρ(|Δ%-difference|, descent-grade SD) = {to_fixed(rho, 3)}")

    cols = list(all_rows[0].keys())
    with open(os.path.join(RESULTS, "e42_lump.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in all_rows:
            fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 4))
                              for v in (r[k] for k in cols)) + "\n")
    print(f"\nwrote e42_lump.csv ({len(all_rows)} rides)")


if __name__ == "__main__":
    main()
