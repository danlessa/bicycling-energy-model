#!/usr/bin/env python3
"""Entry 43 — D6: the frozen law on four European riders (scikit-cycling).

Corpus: scikit-cycling `power_regression`, Zenodo 10.5281/zenodo.1202440
(CC BY 4.0), 1,057 Garmin .fit from four riders in France (Burgundy,
Franche-Comté, the Alps) and Catalonia, 2012-2015. Unpacked, gitignored, into
data/inputs/activities/scikit_cycling/user_{1,2,3,5}/<year>/*.fit — the tracks
start at the riders' home addresses, so nothing derived from their geometry is
ever committed.

This is the study's first corpus with no São Paulo rider, no shared recording
chain, and PUBLISHED rider masses (86/72/61/72 kg, from the deposit's own
analysis code) — so the implied-mass inversion can be graded against four known
values rather than the author's one.

Protocol — paper 1's FROZEN blind protocol, nothing refitted here:
  Crr 0.008 · CdA 0.40 · rho 1.13 · k_eff 0.98 · wind 0 · tau 2 m · c 3 m/km
  · eps_0 0.13 (unclamped eps_d) · eps_f 0.20; mass inverted PER RIDER from the
  sustained-climb balance (>= 3% over >= 100 m; rides with >= 200 m of
  sustained climbing), exactly as D3/D4.

Gravity: the package `G` (Sao Paulo) is used unchanged — patching it would
desync the copy `regime.py` bound at import. D6's true g is 9.805; since m*g is
the identified product, the closed forms are exactly invariant and only the
published-mass comparison rescales (see G_D6/G_RESCALE below and Entry 43).

Inclusion (identical to D3/D4): sport = cycling, power coverage > 50%,
altitude coverage >= 99%, >= 20 km, non-virtual (FIT manufacturer != 260).

Output: data/results/skc_comparison.csv + a console scoreboard with mulberry32
bootstrap 95% CIs (the gate convention: seed 42 for |D%|, 43 for signed).

Run: python3 src/harness/skc_compare.py     (SKC_SMOKE=1 for a 40-ride subset)
"""

from __future__ import annotations

import glob
import math
import os
import sys
from typing import Callable, Iterable, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    climb_balance, deadband, empirical_kj,
                                    env_suffix, eps_geom, extract_regime_powers,
                                    flat_eq_speed, is_finite, jsdiv, load_pts,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import js_str, to_fixed

CORPUS = "scikit_cycling"
DATA = os.path.join(REPO, "data", "inputs", "activities")
ROOT = os.path.join(DATA, CORPUS)
RESULTS = os.path.join(REPO, "data", "results")
os.makedirs(RESULTS, exist_ok=True)

VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
FROZEN = {"Crr": 0.008, "CdA": 0.40, "rho": 1.13, "keff": 0.98, "wind": 0.0}
EPS_F, C_SCALAR = 0.20, 3.0
M0 = 78.0                     # generic prior mass: the inversion's linear reference
MIN_SUSTAINED_DH = 200.0      # per-ride sustained climbing needed to contribute m̂
ZWIFT = 260

G_D6 = 9.805                  # IGF at ~45 deg N less free-air; Entry 43
G_RESCALE = G / G_D6          # m̂ is identified as m*g -> rescale for the mass check

# Published BODY masses from the deposit's own analysis code (mathematical_model.py:
# weight_user = {'user_1': 86., 'user_2': 72., 'user_3': 61., 'user_5': 72.}).
# Validation target only — never an input to any scored arm.
PUBLISHED_KG = {"user_1": 86.0, "user_2": 72.0, "user_3": 61.0, "user_5": 72.0}

SMOKE = bool(os.environ.get("SKC_SMOKE"))
# House convention: a sensitivity sweep overrides constants by env and the output
# CSV is suffixed with the active override, so a sweep can never overwrite the
# canonical file a gate trusts. SKC_M replaces every rider's INVERTED mass.
ENV_NAMES = ("SKC_M", "SKC_CDA", "SKC_CRR")


def jnum(s: str) -> float:
    """JS unary plus on an env string (+process.env.X -> Number(x))."""
    t = s.strip()
    return float(t) if t else float("nan")


def med_of(xs: Iterable[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def quant(xs: Iterable[float], p: float) -> float:
    s = sorted(x for x in xs if is_finite(x))
    return s[math.floor(p * (len(s) - 1))] if s else float("nan")


def rng(seed: int) -> Callable[[], float]:
    """mulberry32 — the repo-wide bootstrap RNG (bit-identical to the JS one)."""
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def boot_ci(values: Sequence[float], seed: int, B: int = 10000) -> tuple[float, float]:
    rand = rng(seed)
    n = len(values)
    if n < 2:
        return float("nan"), float("nan")
    stats = sorted(med_of([values[int(rand() * n)] for _ in range(n)]) for _ in range(B))
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


def boot_ci_strat(groups: Sequence[Sequence[float]], seed: int,
                  B: int = 10000) -> tuple[float, float]:
    """Stratified: resample within each rider, then pool (the pooled-CI convention)."""
    rand = rng(seed)
    stats = []
    for _ in range(B):
        pool: list[float] = []
        for g in groups:
            n = len(g)
            pool.extend(g[int(rand() * n)] for _ in range(n))
        stats.append(med_of(pool))
    stats.sort()
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


def sign_p(w: int, l: int) -> float:
    n = w + l
    if n == 0:
        return 1.0
    p = 0.0
    for k in range(n + 1):
        pk = math.comb(n, k) / 2 ** n
        if k <= min(w, l) or k >= max(w, l):
            p += pk
    return min(1.0, p)


def has_power(pts: Sequence[dict]) -> bool:
    return any(q.get("power") is not None for q in pts)


def eps_cells(pts: Sequence[dict], p: dict) -> dict | None:
    """Descent 30 m cells: eps_bal AND the geometric eps_coast/s_bar in one pass.
    Ported verbatim from ppaz_compare.eps_cells_pz so D6's deficit is measured by
    exactly the machinery D3/D4 were — alpha at the MEASURED flat speed (never
    flat_eq_speed: a parameter mismatch would inflate alpha and lie about eps)."""
    if not pts or len(pts) < 2:
        return None
    mg = p["m"] * G
    beta = mg / p["keff"]
    VSTOP = 0.5 / 3.6
    x0 = pts[0]["x"]
    totalM = pts[len(pts) - 1]["x"] - x0
    DX = 30
    nc = math.floor(totalM / DX)
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

    cellAlt = [alt_at(x0 + k * DX) for k in range(nc + 1)]
    cellE = [0.0] * nc
    cellVs = [0.0] * nc
    cellVt = [0.0] * nc
    for r in pts:
        k = math.floor((r["x"] - x0) / DX)
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
        gr = (cellAlt[k + 1] - cellAlt[k]) / DX
        if abs(gr) < 0.01 and cellVt[k] > 0:
            sv += cellVs[k]
            sw += cellVt[k]
    if not sw > 0:
        return None
    vf = sv / sw
    aeroSpd = vf + p["wind"]
    alpha = (p["Crr"] * mg + 0.5 * p["rho"] * p["CdA"] * aeroSpd * abs(aeroSpd)) / p["keff"]
    Xd = Hd = Ed = cw = 0.0
    for k in range(nc):
        dh = cellAlt[k + 1] - cellAlt[k]
        if dh < 0:
            s = -dh / DX
            Xd += DX
            Hd -= dh
            Ed += cellE[k]
            cw += min(1, alpha / (beta * s)) * (-dh)   # drop-weighted per-cell clamp
    if Hd < 1:
        return None
    return {"epsBal": (alpha * Xd - Ed) / (beta * Hd), "epsCoast": cw / Hd,
            "sbar": Hd / Xd, "vf": vf, "Hd": Hd}


def ride_files() -> list[tuple[str, str]]:
    """(rider, absolute path) for every .fit in the corpus, deterministically ordered."""
    out = [(p.split(os.sep)[-3], p)
           for p in sorted(glob.glob(os.path.join(ROOT, "user_*", "*", "*.fit")))]
    if SMOKE:
        keep: dict[str, int] = {}
        sub = []
        for rider, p in out:
            if keep.get(rider, 0) < 10:
                keep[rider] = keep.get(rider, 0) + 1
                sub.append((rider, p))
        return sub
    return out


def coverage(pts: Sequence[dict]) -> tuple[float, float, float]:
    n = len(pts)
    npow = sum(1 for q in pts if q.get("power") is not None)
    nalt = sum(1 for q in pts if q.get("alt") is not None)
    return npow / n, nalt / n, pts[-1]["x"] / 1000.0


def main() -> None:
    files = ride_files()
    frozen = dict(FROZEN)
    if os.environ.get("SKC_CDA"):
        frozen["CdA"] = jnum(os.environ["SKC_CDA"])
    if os.environ.get("SKC_CRR"):
        frozen["Crr"] = jnum(os.environ["SKC_CRR"])
    M_OVERRIDE = jnum(os.environ["SKC_M"]) if os.environ.get("SKC_M") else 0.0
    print(f"D6 — scikit-cycling (Zenodo 1202440) · {len(files)} .fit found"
          + ("  [SKC_SMOKE: 10 rides/rider]" if SMOKE else ""))
    if frozen != FROZEN or os.environ.get("SKC_M"):
        print(f"  ENV OVERRIDE active{env_suffix(*ENV_NAMES)} — sensitivity run, "
              f"NOT the canonical result")

    # ---- selection: paper 1's blind inclusion filters ----
    kept: list[tuple[str, str, list[dict]]] = []
    drop = {"parse": 0, "virtual": 0, "sport": 0, "pow": 0, "alt": 0, "km": 0}
    for rider, path in files:
        meta: dict = {}
        try:
            pts = load_pts(path, meta)
        except Exception:
            drop["parse"] += 1
            continue
        if len(pts) < 10:
            drop["parse"] += 1
            continue
        if meta.get("manufacturer") == ZWIFT:
            drop["virtual"] += 1
            continue
        if meta.get("sport") not in (None, 2):
            drop["sport"] += 1
            continue
        powcov, altcov, km = coverage(pts)
        if not has_power(pts) or powcov <= 0.5:
            drop["pow"] += 1
            continue
        if altcov < 0.99:
            drop["alt"] += 1
            continue
        if km < 20:
            drop["km"] += 1
            continue
        kept.append((rider, path, pts))
    print("  attrition: " + " · ".join(f"{k} {v}" for k, v in drop.items() if v)
          + f"  ->  {len(kept)} rides")

    riders = sorted({r for r, _, _ in kept})

    # ---- PASS A: implied mass per rider, from that rider's own sustained climbs ----
    p0 = {**frozen, "m": M0}
    mhat: dict[str, float] = {}
    mh_all: dict[str, list[float]] = {r: [] for r in riders}
    for rider, _, pts in kept:
        cb = climb_balance(pts, p0)
        if cb["n"] > 0 and cb["dh"] >= MIN_SUSTAINED_DH and (cb["egrav"] + cb["eroll"]) > 0:
            mh_all[rider].append(M0 * (cb["emeas"] - cb["eaero"]) / (cb["egrav"] + cb["eroll"]))
    print("\nIMPLIED SYSTEM MASS — sustained-climb balance (>=3% over >=100 m), "
          "frozen Crr/CdA/rho")
    print("rider".ljust(9) + "n".rjust(5) + "m_hat kg".rjust(11) + "IQR".rjust(16)
          + "published".rjust(11) + "implied bike+kit".rjust(19))
    for r in riders:
        v = mh_all[r]
        mhat[r] = med_of(v) if v else M0
        pub = PUBLISHED_KG.get(r, float("nan"))
        # m*g is the identified product -> rescale to D6's local g before comparing
        excess = mhat[r] * G_RESCALE - pub
        print(r.ljust(9) + js_str(len(v)).rjust(5)
              + to_fixed(mhat[r], 1).rjust(11)
              + f"{to_fixed(quant(v, .25), 1)}-{to_fixed(quant(v, .75), 1)}".rjust(16)
              + to_fixed(pub, 1).rjust(11)
              + to_fixed(excess, 1).rjust(19))
    # P4's ordering test must be tie-aware: user_2 and user_5 share a published
    # 72 kg, so their relative order is UNDETERMINED and a strict list comparison
    # reports a violation that does not exist. Count only discordant pairs whose
    # published masses actually differ.
    bad = [(a, b) for i, a in enumerate(riders) for b in riders[i + 1:]
           if PUBLISHED_KG.get(a, 0) != PUBLISHED_KG.get(b, 0)
           and ((PUBLISHED_KG[a] > PUBLISHED_KG[b]) != (mhat[a] > mhat[b]))]
    print(f"  P4 ordering preserved over the {sum(1 for i, a in enumerate(riders) for b in riders[i+1:] if PUBLISHED_KG.get(a, 0) != PUBLISHED_KG.get(b, 0))} "
          f"determinate pairs: {not bad}"
          + (f"  (discordant: {bad})" if bad else ""))

    # ---- PASS B: the F-grid + simulation, per ride, with m̂ frozen ----
    rows: list[dict] = []
    cons_max = 0.0
    for rider, path, pts in kept:
        phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
        if not phys:
            continue
        prof = resample_profile(phys, ENGINE_DX)
        profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
        pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
              "flat": flat,
              "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        p = {**frozen, "m": M_OVERRIDE if M_OVERRIDE else mhat[rider],
             "vmax": VMAX, "vstart": VSTART}
        vf = flat_eq_speed(pw["flat"], p)
        emp = empirical_kj(pts)
        if not is_finite(emp) or emp <= 0:
            continue
        epsG = eps_geom(prof, p, vf)
        eps_d = epsG if is_finite(epsG) else EPS_F
        opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                            "descThr": DESC_THR, "climbPower": pw["climb"]}
        c = canonical(prof, pw, p)
        resid = abs(p["keff"] * c["legE"]
                    - (c["dKE"] + c["Wrr"] + c["Waero"] + c["Wgrav"] + c["Wbrake"])) \
            / max(1, p["keff"] * c["legE"])
        cons_max = max(cons_max, resid)
        hp_raw = sum(max(0.0, prof["h"][i] - prof["h"][i - 1]) for i in range(1, len(prof["h"])))
        hp_sm = sum(max(0.0, profS["h"][i] - profS["h"][i - 1]) for i in range(1, len(profS["h"])))
        km = prof["x"][-1] / 1000.0
        beta = p["m"] * G / p["keff"]
        row = {"rider": rider, "ride": os.path.basename(path)[:-4], "dist_km": km,
               "m": p["m"], "emp": emp, "vf_kmh": vf * 3.6, "epsG": eps_d,
               "hplus": hp_raw, "hplus_sm": hp_sm,
               "noise_rate": (hp_raw - hp_sm) / km,
               "climb_rate": hp_sm / km,
               "peFloor": beta * hp_sm / 1000,
               "canon": c["legE"] / 1000,
               "canon_d": jsdiv(c["legE"] / 1000 - emp, emp) * 100}
        row["dataOK"] = emp >= row["peFloor"]
        for tag, eps in (("d", eps_d), ("f", EPS_F)):
            a1 = approximate(prof, p, vf, eps, opt("off"))       # F1 original
            a2 = approximate(prof, p, vf, eps, opt("zero"))      # F2 split, raw
            a3 = approximate(profS, p, vf, eps, opt("zero"))     # F3 split + deadband
            ks = (max(0.0, 1 - C_SCALAR * km / a2["hplus"])) if a2["hplus"] > 0 else 1.0
            e4 = a2["roll"] + a2["aero"] + ks * (a2["climb"] + a2["recov"])   # F4, J
            for name, E in (("f1", a1["E"]), ("f2", a2["E"]), ("f3", a3["E"]), ("f4", e4)):
                row[f"{name}_{tag}"] = jsdiv(E / 1000 - emp, emp) * 100
        eb = eps_cells(pts, p)
        if eb and eb.get("Hd", 0) >= 1 and eb.get("sbar", 0) >= 0.03:
            row["eps_bal"] = eb["epsBal"]
            row["eps_coast"] = eb["epsCoast"]
            row["eps_gap"] = eb["epsCoast"] - eb["epsBal"]
            row["sbar"] = eb["sbar"]
        rows.append(row)

    clean = [r for r in rows if r["dataOK"]]
    print(f"\nPASS B — {len(rows)} evaluated, {len(clean)} above the physical floor "
          f"(floor drops {len(rows) - len(clean)}) · max conservation resid {cons_max:.2e}")

    COLS = [("F1 · eps_d (original)", "f1_d"), ("F2 · eps_d (split)", "f2_d"),
            ("F3 · eps_d (split+deadband)", "f3_d"), ("F4 · eps_d (split+scalar c)", "f4_d"),
            ("F3 · eps_f = 0.20", "f3_f"), ("F4 · eps_f = 0.20", "f4_f"),
            ("simulation (frozen)", "canon_d")]

    def scoreboard(sub: Sequence[dict], title: str, strat: bool = False) -> None:
        if not sub:
            return
        print(f"\n{title}  (n = {len(sub)})")
        print("model".ljust(30) + "med|D%| [95% CI]".rjust(22) + "medD% [95% CI]".rjust(23))
        for lab, key in COLS:
            av = [abs(r[key]) for r in sub if is_finite(r.get(key, float("nan")))]
            sv = [r[key] for r in sub if is_finite(r.get(key, float("nan")))]
            if not av:
                continue
            if strat:
                ga = [[abs(r[key]) for r in sub if r["rider"] == rr and is_finite(r[key])]
                      for rr in riders]
                gs = [[r[key] for r in sub if r["rider"] == rr and is_finite(r[key])]
                      for rr in riders]
                ga = [g for g in ga if g]
                gs = [g for g in gs if g]
                alo, ahi = boot_ci_strat(ga, 42)
                slo, shi = boot_ci_strat(gs, 43)
            else:
                alo, ahi = boot_ci(av, 42)
                slo, shi = boot_ci(sv, 43)
            print(lab.ljust(30)
                  + f"{to_fixed(med_of(av), 2)} [{to_fixed(alo, 1)}, {to_fixed(ahi, 1)}]".rjust(22)
                  + f"{to_fixed(med_of(sv), 2)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]".rjust(23))

    for r in riders:
        sub = [x for x in clean if x["rider"] == r]
        scoreboard(sub, f"--- {r}  (published {to_fixed(PUBLISHED_KG.get(r, 0), 0)} kg, "
                        f"climb {to_fixed(med_of([x['climb_rate'] for x in sub]), 1)} m/km)")
    scoreboard(clean, "--- D6 POOLED (stratified within rider)", strat=True)

    print("\npaired sign tests (|D%|, pooled):")
    for la, ka, lb, kb in (("F3.eps_d", "f3_d", "simulation", "canon_d"),
                           ("F3.eps_f", "f3_f", "simulation", "canon_d"),
                           ("F4.eps_d", "f4_d", "simulation", "canon_d"),
                           ("F2", "f2_d", "F1", "f1_d"),
                           ("F3.eps_d", "f3_d", "F4.eps_d", "f4_d")):
        w = sum(1 for r in clean if abs(r[ka]) < abs(r[kb]))
        l = sum(1 for r in clean if abs(r[ka]) > abs(r[kb]))
        print(f"  {la} vs {lb}: closer on {w}/{w + l}, p = {to_fixed(sign_p(w, l), 4)}")

    print("\nP2 — the c mismatch (registered: F4 bias 3-6 points BELOW F3's):")
    nr = [r["noise_rate"] for r in clean]
    print(f"  measured noise rate: median {to_fixed(med_of(nr), 2)} m/km "
          f"[IQR {to_fixed(quant(nr, .25), 2)}-{to_fixed(quant(nr, .75), 2)}]  "
          f"vs the frozen c = {to_fixed(C_SCALAR, 1)}")
    for tag in ("d", "f"):
        b3 = med_of([r[f"f3_{tag}"] for r in clean])
        b4 = med_of([r[f"f4_{tag}"] for r in clean])
        print(f"  eps_{tag}: F3 bias {to_fixed(b3, 2)} · F4 bias {to_fixed(b4, 2)} "
              f"· delta {to_fixed(b4 - b3, 2)} points")

    print("\nP3 — the coasting deficit on real descents (mean descent grade >= 3%):")
    for r in riders + ["POOLED"]:
        sub = [x for x in clean
               if "eps_gap" in x and (r == "POOLED" or x["rider"] == r)]
        if len(sub) < 3:
            print(f"  {r.ljust(9)} n = {len(sub)} — too few")
            continue
        gaps = [x["eps_gap"] for x in sub]
        lo, hi = boot_ci(gaps, 42, B=2000 if SMOKE else 10000)
        print(f"  {r.ljust(9)} n = {js_str(len(sub)).rjust(4)}  gap "
              f"{to_fixed(med_of(gaps), 3)} [{to_fixed(lo, 2)}, {to_fixed(hi, 2)}]  "
              f"(eps_coast {to_fixed(med_of([x['eps_coast'] for x in sub]), 2)}, "
              f"eps_bal {to_fixed(med_of([x['eps_bal'] for x in sub]), 2)})")

    if rows:
        # Union of every row's keys, not row[0]'s: a column absent from the
        # FIRST row (eps_gap, when that ride has no real descent) was being
        # dropped from the header and therefore from every row.
        cols = list(dict.fromkeys(k for _r in rows for k in _r))
        # A smoke run must never land on the canonical path a gate trusts —
        # same reasoning as the env-override suffix, different trigger.
        dest = os.path.join(
            RESULTS,
            f"skc_comparison{'.SMOKE' if SMOKE else ''}{env_suffix(*ENV_NAMES)}.csv")
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for r in rows:
                fh.write(",".join(
                    (f'"{v}"' if isinstance(v, str)
                     else js_str(v) if isinstance(v, bool)
                     else to_fixed(v, 3) if is_finite(v) else "")
                    for v in (r.get(k, float("nan")) for k in cols)) + "\n")
        print(f"\nwrote {os.path.basename(dest)} ({len(rows)} rides)")


if __name__ == "__main__":
    main()
