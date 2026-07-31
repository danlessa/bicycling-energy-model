#!/usr/bin/env python3
"""Entry 52, stage 1 — the aggregate cache the A-chain runs on.

Walks D3-D6 ONCE, inverts the per-ride physics (A.3, which by design runs
before the split), and stores enough per ride to evaluate F1-F4 for ANY
(eps, c) by arithmetic alone. That is what makes A.4's repeated k-fold with
per-fold refitting affordable: without it every fold re-parses ~2,000 tracks.

WHY IT IS EXACT, not an approximation. `approximate` is linear in eps -- the
deficit enters only through recov = eps * recov(1) -- so two evaluations pin
the whole family:

    E_i(eps) = E_i(0) + eps * (E_i(1) - E_i(0))        i = 1, 2, 3

F4 carries a second parameter. It is built from F2's components as

    E_4(eps, c) = roll + aero + km(c) * (climb + eps * recov1)
    km(c)       = max(0, 1 - c * x_km / hplus)          published c = 3

which is linear in eps at fixed c and affine in km, so caching the four
components plus (x, hplus) pins that family too. Both facts are verified
against the real engine by `verify()` below rather than assumed.

D1/D2 are absent on purpose: matching on measured kJ puts 87% of D2 and 43%
of D1 inside D5, so they are re-processings of the same rider's rides, not
independent corpora (Entry 52's registration).

Output: data/results/e52_aggregates.csv
Run:    python3 src/harness/e52_build.py            (E52_SMOKE=1 for a subset)
"""

from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    deadband, empirical_kj,
                                    extract_regime_powers, is_finite,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import flat_eq_speed
from bicycling_energy_model.jsfmt import to_fixed

from perride_invert import (CLIMB_THR, DESC_THR, ENGINE_DX, KEFF, RESULTS, RHO,
                            TAU_SMOOTH, VMAX, VSTART, find_segments,
                            invert_physics, seg_integrals)
from e44_scurve import corpus_rides

SMOKE = bool(os.environ.get("E52_SMOKE"))
CHECK: list[float] = []   # build-time cache-vs-engine deviations
C_PUB = 3.0                      # F4's published climb-fraction constant
GROUPS = ("D3", "D4", "D5", "D6-user_1", "D6-user_2", "D6-user_3", "D6-user_5")
ANCHOR_KEY = {"D3": "ppaz", "D4": "jaam", "D5": "danlessa"}

COLS = ["group", "ride", "date", "emp",
        "m_hat", "m_src", "crr_hat", "crr_src", "cda_hat", "cda_src", "wind_ms",
        "f1_E0", "f1_E1", "f2_E0", "f2_E1", "f3_E0", "f3_E1",
        "a2_roll", "a2_aero", "a2_climb", "a2_recov1",
        "x_m", "hplus", "hminus", "vf_kmh", "canon_kj"]


def one_ride(pts, label, group, m_logged) -> dict | None:
    """Everything Entry 52 needs from one ride. Mirrors e47's one_ride setup so
    the two entries share a population by construction.

    WIND IS ZERO for every ride, and that is a property of the iterator rather
    than a choice: corpus_rides() carries no date or file path, because the
    weather fetch would key on centroids derived from third-party riders' home
    addresses. It applies uniformly to all forms, so it cannot bias the A.4
    comparison -- but it does sit inside the absolute error A.8 reports, and the
    paper says so rather than quietly assuming still air.
    """
    emp = empirical_kj(pts)
    if not (is_finite(emp) and emp > 0):
        return None
    phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile(phys, ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}

    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    if not (is_finite(flat) and flat > 0):
        return None
    p_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat

    wind = 0.0                      # see the docstring: a property of the iterator

    # --- A.3: the per-ride inversion, before the split, as data preparation
    climbs_raw, flats_raw = find_segments(prof)
    wb_climbs = [s for s in (seg_integrals(pts, c, wind) for c in climbs_raw) if s and s["ok"]]
    wb_flats = [s for s in (seg_integrals(pts, f, wind) for f in flats_raw) if s and s["ok"]]
    inv = invert_physics(prof, wb_climbs, wb_flats, ANCHOR_KEY.get(group), m_logged)
    if inv is None:
        return None

    p = {"m": inv["m_hat"], "Crr": inv["crr_hat"], "CdA": inv["cda_hat"],
         "rho": RHO, "keff": KEFF, "wind": wind, "vmax": VMAX, "vstart": VSTART}
    pw = {"flat": flat, "climb": p_climb}
    vf = flat_eq_speed(flat, p)
    if not (is_finite(vf) and vf > 0):
        return None
    opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                        "descThr": DESC_THR, "climbPower": p_climb}

    row = {"group": group, "ride": label, "date": "", "emp": emp,
           "m_hat": inv["m_hat"], "m_src": inv.get("m_src", ""),
           "crr_hat": inv["crr_hat"], "crr_src": inv.get("crr_src", ""),
           "cda_hat": inv["cda_hat"], "cda_src": inv.get("cda_src", ""),
           "wind_ms": wind, "vf_kmh": vf * 3.6}

    # --- the two-point cache: eps = 0 and eps = 1 pin every form
    for tag, (pr, mode) in (("f1", (prof, "off")), ("f2", (prof, "zero")),
                            ("f3", (profS, "zero"))):
        a0 = approximate(pr, p, vf, 0.0, opt(mode))
        a1 = approximate(pr, p, vf, 1.0, opt(mode))
        row[f"{tag}_E0"], row[f"{tag}_E1"] = a0["E"], a1["E"]
        if tag == "f2":
            row["a2_roll"], row["a2_aero"] = a0["roll"], a0["aero"]
            row["a2_climb"] = a0["climb"]
            row["a2_recov1"] = a1["recov"]      # recov at eps = 1
            row["hplus"], row["hminus"] = a0["hplus"], a0["hminus"]
    row["x_m"] = prof["x"][-1] - prof["x"][0]

    # --- non-circular check: the cached two-point interpolation against a FRESH
    # engine call at an eps neither endpoint used, plus F4 against the exact
    # expression perride_invert.py publishes. Compares to the engine, not to
    # e_form, so it can actually fail.
    if len(CHECK) < 300:
        worst = 0.0
        for tag, (pr, mode) in (("f1", (prof, "off")), ("f2", (prof, "zero")),
                                ("f3", (profS, "zero"))):
            for eps in (0.2, 0.37, 0.85):
                want = approximate(pr, p, vf, eps, opt(mode))["E"]
                got = row[tag + "_E0"] + eps * (row[tag + "_E1"] - row[tag + "_E0"])
                if want:
                    worst = max(worst, abs(got - want) / abs(want))
        for eps in (0.2, 0.37):
            a2 = approximate(prof, p, vf, eps, opt("zero"))
            km = (max(0, 1 - C_PUB * (prof["x"][-1] / 1000) / a2["hplus"])
                  if a2["hplus"] > 0 else 1)
            want = a2["roll"] + a2["aero"] + km * (a2["climb"] + a2["recov"])
            got = e_form(row, "F4", eps) * 1000
            if want:
                worst = max(worst, abs(got - want) / abs(want))
        CHECK.append(worst)

    try:
        row["canon_kj"] = canonical(prof, pw, p)["legE"] / 1000
    except Exception:
        row["canon_kj"] = float("nan")
    return row


# --------------------------------------------------------------- form algebra
# The single definition of F1-F4 in terms of the cache. Everything downstream
# (CV, selection, sensitivity, test) calls THESE, so a form cannot drift
# between stages.

def e_form(r: dict, form: str, eps: float, c: float = C_PUB) -> float:
    """Energy in kJ for one ride under one form at (eps, c)."""
    if form in ("F1", "F2", "F3"):
        k = {"F1": "f1", "F2": "f2", "F3": "f3"}[form]
        return (r[k + "_E0"] + eps * (r[k + "_E1"] - r[k + "_E0"])) / 1000
    if form == "F4":
        km = 1.0 - c * (r["x_m"] / 1000.0) / r["hplus"] if r["hplus"] > 0 else 1.0
        km = km if km > 0 else 0.0
        return (r["a2_roll"] + r["a2_aero"]
                + km * (r["a2_climb"] + eps * r["a2_recov1"])) / 1000
    raise ValueError(form)


FORMS = ("F1", "F2", "F3", "F4")
NPAR = {"F1": 1, "F2": 1, "F3": 1, "F4": 2}      # eps; F4 adds c


def verify() -> bool:
    """Report the build-time engine comparison. Non-circular: every deviation in
    CHECK came from comparing the cache against a fresh approximate() call."""
    if not CHECK:
        print("\n  cache-vs-engine: NO RIDES CHECKED — gate cannot pass")
        return False
    worst = max(CHECK)
    ok = worst < 1e-9
    print(f"\n  cache-vs-engine on {len(CHECK)} rides "
          f"(two-point interpolation + F4 algebra vs fresh engine calls)")
    print(f"    worst relative deviation: {worst:.3e}   "
          f"{'GATE-OK' if ok else 'GATE-FAIL'}")
    return ok


def main() -> None:
    print("Entry 52 stage 1 — building the aggregate cache for D3-D6")
    rows: list[dict] = []
    seen: dict[str, int] = {}
    for group, pts, mass in corpus_rides():
        if group not in GROUPS:          # drops D1/D2: they are inside D5
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if SMOKE and i >= 15:
            continue
        try:
            r = one_ride(pts, f"{group}#{i}", group, mass)
        except Exception:
            r = None
        if r:
            rows.append(r)
    for g in GROUPS:
        n = sum(1 for r in rows if r["group"] == g)
        print(f"  {g:<12} kept {n:>5} of {seen.get(g, 0)}")
    print(f"\n  {len(rows)} rides cached of {sum(seen.values())} seen")

    ok = verify()

    out = os.path.join(RESULTS, "e52_aggregates" + (".SMOKE" if SMOKE else "") + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nwrote {os.path.basename(out)}")
    if not ok:
        raise SystemExit("cache does not reproduce the engine — refusing to ship it")


if __name__ == "__main__":
    main()
