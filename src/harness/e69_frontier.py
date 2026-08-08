#!/usr/bin/env python3
"""Entry 69 — the accuracy-vs-keepability frontier, and the per-corpus pin.

Entry 68 showed F5f's CV declines monotonically in the noise floor tau_n all
the way to the F3 anchor, so the floor is load-bearing and only an external
pin can hold it. Entry 66 produced the one measurement that can: the
closure-pair drift amplitude, per ride and per corpus. This entry maps the
frontier and tests the pinned form:

  F5p  per-GROUP floor: tau_n(g) = the group's median measured drift snapped
       to the tau grid (nearest; ties round up), components from the f3t
       cache at that index, tolls from that arm's walk, v_b frozen at the
       never-brake arm — ZERO chosen constants; eps is the single fitted
       parameter. The pin is parameter-class telemetry (a noise scale, like
       m_hat), measured on all rides — it is not fitted on energy targets,
       which is why reading it corpus-wide is not a test leak.

FRONTIER METRICS, same protocol everywhere, every number recomputed here
(no literals; F3's chain CV is read from its producing CSV):
  CV      seed-48 train half, repeated stratified 5-fold x 4, eps in-fold
          (F3 additionally refits tau in-fold via e52_split.fit — its full
          five-form chain CV is read from e63_split.E63_TAUN2p0.csv)
  LORO    fit on six riders' train halves, score the 7th's test half;
          per-ride paired |D%| difference vs F3, stratified CI seed 54
  AGING   within-rider early/late halves (train only): late half scored
          with the rider's own early-half constants, minus its own best

The standalone runs of e63's LORO mode and e67's aging at tau_n = 3.0/4.5
(this entry's batch) are independent cross-checks of the same quantities.

Outputs: data/results/e69_pins.csv, e69_frontier.csv, e69_loro.csv,
e69_aging.csv. Run: python3 src/harness/e69_frontier.py   (E69_SMOKE=1)
"""

from __future__ import annotations

import csv
import glob
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

SMOKE = bool(os.environ.get("E69_SMOKE"))
if SMOKE:
    os.environ["E52_SMOKE"] = "1"

from bicycling_energy_model.engines import G  # noqa: E402
from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

from e52_build import C_PUB, TAU_GRID, e_form  # noqa: E402
from e52_split import (EPS_BOUNDS, GROUPS, SEED, cv_loss, fit, folds,  # noqa: E402
                       load, split)
from e63_f5_kebuffer import VB_INF_I  # noqa: E402
from e66_driftprobe import spearman  # noqa: E402
from perride_invert import KEFF, RESULTS  # noqa: E402
from skc_compare import boot_ci_strat, med_of, sign_p  # noqa: E402

SEED64 = 54
MIN_HALF = 5 if SMOKE else 20
SUFF = ".SMOKE" if SMOKE else ""
F5F_ARMS = (2.0, 3.0, 4.5)        # the frontier's fixed-floor rungs


# ------------------------------------------------------------- toll loading

def toll_files() -> dict[float, str]:
    """{tau_n: tolls-csv path} for every walked arm on disk (full walks only)."""
    out = {}
    for p in glob.glob(os.path.join(RESULTS, "e63_tolls*.csv")):
        base = os.path.basename(p)
        if ".SMOKE" in base and not SMOKE:
            continue
        if "RAINFLOW" in base or "SMOOTH" in base:
            continue
        if base == "e63_tolls" + (".SMOKE" if SMOKE else "") + ".csv":
            out[0.5] = p                     # the Entry-63 canonical arm
            continue
        m = base.split("E63_TAUN")
        if len(m) == 2:
            tau = float(m[1].split(".csv")[0].replace(".SMOKE", "").replace("p", "."))
            out[tau] = p
    return out


def load_tolls(path: str) -> dict[str, float]:
    """ride label -> toll at the never-brake arm, metres."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["ride"]] = float(r[f"toll_vb{VB_INF_I}"])
    return out


# ----------------------------------------------------------------- the pins

def snap(x: float) -> float:
    """Nearest tau-grid value; ties round UP (deterministic, documented)."""
    return min(TAU_GRID, key=lambda t: (abs(t - x), -t))


def group_pins() -> dict[str, tuple[float, float]]:
    """{group: (median measured drift m, pinned tau)} from e66_drift.csv."""
    path = os.path.join(RESULTS, "e66_drift" + SUFF + ".csv")
    by_g: dict[str, list[float]] = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["drift_med_m"] != "":
                by_g.setdefault(r["group"], []).append(float(r["drift_med_m"]))
    return {g: (med_of(v), snap(med_of(v))) for g, v in by_g.items() if v}


# ------------------------------------------------------- form evaluation

def attach(rows, pins, files) -> None:
    """Give every ride its F5p (tip, btp) and per-arm F5f bt columns, in kJ."""
    arm_tolls = {tau: load_tolls(files[tau]) for tau in F5F_ARMS}
    pin_taus = sorted({t for _d, t in pins.values()})
    pin_tolls = {tau: load_tolls(files[tau]) for tau in pin_taus}
    for r in rows:
        beta_kj = r["m_hat"] * G / KEFF / 1000.0
        for tau in F5F_ARMS:
            r[f"bt@{tau:g}"] = beta_kj * arm_tolls[tau].get(r["ride"], 0.0)
        _d, tau_p = pins[r["group"]]
        r["tip"] = TAU_GRID.index(tau_p)
        r["btp"] = beta_kj * pin_tolls[tau_p].get(r["ride"], 0.0)


def e_5(r, eps, key, ti) -> float:
    k = f"f3t{ti}"
    bt = r[key] * 1000.0
    return (r[k + "_roll"] + r[k + "_aero"] + (r[k + "_climb"] - bt)
            + eps * (r[k + "_recov1"] + bt)) / 1000.0


def evaluator(form):
    """(r, eps) -> kJ for 'F5p' or 'F5f@<tau>'."""
    if form == "F5p":
        return lambda r, e: e_5(r, e, "btp", r["tip"])
    tau = float(form.split("@")[1])
    ti = TAU_GRID.index(tau)
    return lambda r, e: e_5(r, e, f"bt@{tau:g}", ti)


def fit_eps(rows, ev) -> tuple[float, float]:
    sub = [(ev(r, 0.0), ev(r, 1.0) - ev(r, 0.0), r["emp"]) for r in rows
           if ev(r, EPS_BOUNDS[0]) > 0 and ev(r, EPS_BOUNDS[1]) > 0]
    if not sub:
        return 0.2, float("inf")

    def loss(e):
        tot = 0.0
        for fixed, rec, emp in sub:
            v = fixed + e * rec
            tot += abs(math.log(v / emp)) if v > 0 else float("inf")
        return tot / len(sub)

    lo, hi = EPS_BOUNDS
    best = 0.2
    for _ in range(5):
        step = (hi - lo) / 200
        best = min([lo + i * step for i in range(201)], key=loss)
        lo, hi = best - step, best + step
    return best, loss(best)


def loss_of(rows, ev, eps) -> float:
    v = [abs(math.log(x / r["emp"])) if (x := ev(r, eps)) > 0 else float("inf")
         for r in rows if ev(r, EPS_BOUNDS[0]) > 0 and ev(r, EPS_BOUNDS[1]) > 0]
    return sum(v) / len(v) if v else float("inf")


def pct_of(rows, ev, eps) -> list[float]:
    return [100.0 * (ev(r, eps) - r["emp"]) / r["emp"] for r in rows]


FORMS5 = tuple(f"F5f@{t:g}" for t in F5F_ARMS) + ("F5p",)


def cv_of(train, ev) -> tuple[float, float]:
    scores = []
    for rep in range(4):
        for tr, va in folds(train, 5, rep):
            e, _l = fit_eps(tr, ev)
            scores.append(loss_of(va, ev, e))
    n = len(scores)
    m = sum(scores) / n
    sd = math.sqrt(sum((s - m) ** 2 for s in scores) / (n - 1)) if n > 1 else 0.0
    return m, sd / math.sqrt(n)


def main() -> None:
    rows = load()
    pins = group_pins()
    files = toll_files()
    need = sorted({t for _d, t in pins.values()} | set(F5F_ARMS))
    missing = [t for t in need if t not in files]
    if missing:
        raise SystemExit("missing toll walks for tau_n = " + str(missing)
                         + " — build each with E63_TAUN=<x> E63_REBUILD=1 "
                           "E63_F5FCV=1 e63_f5_kebuffer.py")
    print(f"Entry 69 — the frontier + the per-corpus pin ({len(rows)} rides)"
          + ("   [SMOKE]" if SMOKE else ""))
    print(f"\n  pins from e66_drift{SUFF}.csv (median measured drift -> grid):")
    pin_rows = []
    for g in GROUPS:
        if g in pins:
            d, t = pins[g]
            pin_rows.append({"group": g, "drift_med_m": d, "tau_pin": t})
            print(f"    {g:<12} drift {d:>5.2f} m  -> tau_n = {t:g} m")
    attach(rows, pins, files)
    train, test = split(rows)

    # ---- CV rungs (F3's chain CV read from its producing CSV, not re-run)
    f3csv = os.path.join(RESULTS, "e63_split.E63_TAUN2p0" + SUFF + ".csv")
    f3cv = f3se = float("nan")
    with open(f3csv, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["form"] == "F3":
                f3cv, f3se = float(r["cv"]), float(r["cv_se"])
    cvs = {}
    for form in FORMS5:
        cvs[form] = cv_of(train, evaluator(form))
    print(f"\n  CV (train, eps in-fold):")
    print(f"    {'F3 (tau fitted; from chain CSV)':<32} "
          f"{f3cv:.5f} +/- {f3se:.5f}")
    for form in FORMS5:
        print(f"    {form:<32} {cvs[form][0]:.5f} +/- {cvs[form][1]:.5f}")

    # ---- LORO: one loop, F3 fitted once per donor set, every rung scored
    print(f"\n  LORO (donors' train halves -> recipient's test half)")
    per_ride: dict[str, list[tuple[float, float]]] = {f: [] for f in FORMS5}
    loro_rows = []
    for g in GROUPS:
        tr = [r for r in train if r["group"] != g]
        te = [r for r in test if r["group"] == g]
        if not te:
            continue
        e3, c3, ti3 = fit(tr, "F3")
        p3 = [100.0 * (e_form(r, "F3", e3, c3, ti3) - r["emp"]) / r["emp"]
              for r in te]
        row = {"group": g, "n": len(te), "f3_med_abs": med_of([abs(v) for v in p3])}
        for form in FORMS5:
            ev = evaluator(form)
            e5, _l = fit_eps(tr, ev)
            p5 = pct_of(te, ev, e5)
            row[form] = med_of([abs(v) for v in p5])
            per_ride[form].append(list(zip(p5, p3)))
        loro_rows.append(row)
        print(f"    {g:<12} n {len(te):>3}  F3 {row['f3_med_abs']:>6.2f}  "
              + "  ".join(f"{form} {row[form]:>6.2f}" for form in FORMS5))
    for form in FORMS5:
        diffs = [[abs(a) - abs(b) for a, b in grp] for grp in per_ride[form]]
        flat = [d for grp in diffs for d in grp]
        ci = boot_ci_strat(diffs, SEED64 + 2)
        win = sum(1 for d in flat if d < 0)
        los = sum(1 for d in flat if d > 0)
        print(f"    {form} vs F3 per-ride |D%|: median {med_of(flat):+.2f} pp "
              f"[{ci[0]:+.2f}, {ci[1]:+.2f}], closer on {win}/{win + los} "
              f"(sign p = {to_fixed(sign_p(win, los), 4)})")

    # ---- AGING: within-rider halves, F3 refit per half, rungs eps-only
    print(f"\n  AGING (late half under the rider's own early constants)")
    aging_rows = []
    for g in GROUPS:
        sub = [r for r in train if r["group"] == g]
        sub.sort(key=lambda r: int(r["ride"].rsplit("#", 1)[1]))
        h = len(sub) // 2
        if h < MIN_HALF:
            continue
        early, late = sub[:h], sub[h:]
        e3e, c3e, ti3e = fit(early, "F3")
        e3l, c3l, ti3l = fit(late, "F3")
        row = {"group": g, "n_half": h,
               "f3": (cv_loss(late, "F3", e3e, C_PUB, ti3e)
                      - cv_loss(late, "F3", e3l, C_PUB, ti3l))}
        for form in FORMS5:
            ev = evaluator(form)
            ee, _ = fit_eps(early, ev)
            el, _ = fit_eps(late, ev)
            row[form] = loss_of(late, ev, ee) - loss_of(late, ev, el)
        aging_rows.append(row)
        print(f"    {g:<12} F3 {row['f3']:.5f}  "
              + "  ".join(f"{form} {row[form]:.5f}" for form in FORMS5))
    if aging_rows:
        print(f"    medians: F3 {med_of([r['f3'] for r in aging_rows]):.5f}  "
              + "  ".join(f"{form} "
                          f"{med_of([r[form] for r in aging_rows]):.5f}"
                          for form in FORMS5))

    for name, rws in (("e69_pins", pin_rows), ("e69_loro", loro_rows),
                      ("e69_aging", aging_rows)):
        if not rws:
            continue
        out = os.path.join(RESULTS, name + SUFF + ".csv")
        with open(out, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rws[0].keys()))
            w.writeheader()
            for r in rws:
                w.writerow(r)
    out = os.path.join(RESULTS, "e69_frontier" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("form,cv,cv_se\n")
        fh.write(f"F3,{f3cv:.6f},{f3se:.6f}\n")
        for form in FORMS5:
            fh.write(f"{form},{cvs[form][0]:.6f},{cvs[form][1]:.6f}\n")
    print(f"\nwrote e69_pins/e69_frontier/e69_loro/e69_aging{SUFF}.csv")


if __name__ == "__main__":
    main()
