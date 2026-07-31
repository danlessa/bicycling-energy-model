#!/usr/bin/env python3
"""Entry 52, stage 2 — the A-chain: split, cross-validate, select, test.

Runs A.1-A.8 exactly as pre-registered in MODEL_COMPARISON_JOURNAL.md (Entry
52), on the cache e52_build.py produces. Nothing here re-parses a track, so the
whole chain is seconds.

  A.1  hold out 15% of each of D3, D4, D5, D6 at random (seed fixed, drawn once)
  A.2  the remainder, unified across corpora, is D_train
  A.3  report the dispersion of the per-ride inverted constants (the inversion
       itself already happened, in stage 1, before the split)
  A.4  repeated stratified k-fold on D_train, fitting each form's parameters
       INSIDE each fold and scoring on the held-back part
  A.5  select by CV, binding; AIC computed and reported beside it; 1-SE rule
       breaks ties toward the simpler form
  A.6  refit the winner on all of D_train
  A.7  sensitivity of the winner over (m, CdA, Crr, eps)
  A.8  score D_test ONCE

LOSS is mean |log(Ehat/E)| -- symmetric, scale-free, L1-robust. REPORTING stays
median |Delta%| so every published number keeps its meaning. The two are
different on purpose and the entry says so.

THE GATE is structural: test statistics are unreachable until the A.5 winner has
been serialised. `_WINNER` starts None and `score_test` refuses to run without
it, so a coding slip cannot leak the test half into selection.

Run: python3 src/harness/e52_split.py        (E52_SMOKE=1 for the smoke cache)
"""

from __future__ import annotations

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import is_finite
from bicycling_energy_model.jsfmt import to_fixed

from e52_build import AERO, C_PUB, FORMS, GROUPS, NPAR, TAU_GRID, TAU_PUB_I, e_form
from perride_invert import RESULTS
from skc_compare import boot_ci_strat, med_of, sign_p

SMOKE = bool(os.environ.get("E52_SMOKE"))
SEED = 48                     # 42/43 published, 44 TOST, 45 E49, 46 E50, 47 E51
TEST_FRAC = 0.15
K_FOLDS = 5
N_REPEATS = 4
EPS_BOUNDS = (-0.20, 1.00)
C_BOUNDS = (0.0, 12.0)

_WINNER: dict | None = None   # set by select(); score_test() refuses without it


# ------------------------------------------------------------------ plumbing

def mulberry32(seed: int):
    """The project's deterministic RNG, same generator every harness uses."""
    s = seed & 0xFFFFFFFF

    def rnd() -> float:
        nonlocal s
        s = (s + 0x6D2B79F5) & 0xFFFFFFFF
        t = s
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rnd


def load() -> list[dict]:
    path = os.path.join(RESULTS, "e52_aggregates" + ("" if AERO == "reg" else "." + AERO) + (".SMOKE" if SMOKE else "") + ".csv")
    rows = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                d = {k: float(v) for k, v in r.items()
                     if k not in ("group", "ride", "date", "m_src", "crr_src", "cda_src")}
            except ValueError:
                continue
            d.update({k: r[k] for k in ("group", "ride", "m_src", "crr_src", "cda_src")})
            if d["emp"] > 0 and is_finite(d["emp"]):
                rows.append(d)
    return rows


# --------------------------------------------------------------- the losses

def logratio(rows, form, eps, c=C_PUB, ti=TAU_PUB_I) -> list[float]:
    """|log(Ehat/E)| per ride — the FITTING loss (symmetric, scale-free)."""
    out = []
    for r in rows:
        e = e_form(r, form, eps, c, ti)
        if e > 0:
            out.append(abs(math.log(e / r["emp"])))
    return out


def pct(rows, form, eps, c=C_PUB, ti=TAU_PUB_I) -> list[float]:
    """Signed Delta% per ride — the REPORTING statistic."""
    return [100.0 * (e_form(r, form, eps, c, ti) - r["emp"]) / r["emp"] for r in rows]


def cv_loss(rows, form, eps, c=C_PUB, ti=TAU_PUB_I) -> float:
    v = logratio(rows, form, eps, c, ti)
    return sum(v) / len(v) if v else float("inf")


# --------------------------------------------------------------- A.4 fitting

def fit(rows, form) -> tuple[float, float, int]:
    """Fit a form's free parameters on `rows` by minimising the CV loss.
    Grid then refine, deterministic.

    F3 carries (eps, tau) and F4 (eps, c) -- tau is fitted here rather than
    inherited, because Entry 52's findings caught it frozen at the historical
    2 m, selected on data overlapping D3-D6 and therefore fitted outside the
    chain on rides now in the test half. tau is searched over the cached grid,
    so it is a discrete parameter; that is reported rather than smoothed over."""
    def eps_opt(ti, c):
        lo, hi = EPS_BOUNDS
        best = 0.2
        for _ in range(5):
            step = (hi - lo) / 200
            cand = [lo + i * step for i in range(201)]
            best = min(cand, key=lambda e: cv_loss(rows, form, e, c, ti))
            lo, hi = best - step, best + step
        return best

    if form == "F3":
        best = min(((eps_opt(ti, C_PUB), C_PUB, ti) for ti in range(len(TAU_GRID))),
                   key=lambda q: cv_loss(rows, form, q[0], q[1], q[2]))
        return best
    if form != "F4":
        return eps_opt(TAU_PUB_I, C_PUB), C_PUB, TAU_PUB_I
    lo, hi = EPS_BOUNDS
    best_e, best_c = 0.2, C_PUB
    clo, chi = C_BOUNDS
    for _ in range(4):
        es = [lo + i * (hi - lo) / 40 for i in range(41)]
        cs = [clo + i * (chi - clo) / 40 for i in range(41)]
        best_e, best_c = min(((e, c) for e in es for c in cs),
                             key=lambda q: cv_loss(rows, form, q[0], q[1]))
        de, dc = (hi - lo) / 40, (chi - clo) / 40
        lo, hi = best_e - de, best_e + de
        clo, chi = max(C_BOUNDS[0], best_c - dc), best_c + dc
    return best_e, best_c, TAU_PUB_I


def aic(rows, form, eps, c, ti=TAU_PUB_I) -> float:
    """AIC under a Laplace likelihood on the log-ratio residual — the
    likelihood that matches the L1 fitting loss. Reported, not binding
    (Entry 49's precedent: held-out primary, information criterion
    corroborating)."""
    r = logratio(rows, form, eps, c, ti)
    n = len(r)
    if not n:
        return float("nan")
    b = sum(r) / n or 1e-12
    loglik = -n * math.log(2 * b) - n
    return 2 * NPAR[form] - 2 * loglik


# ------------------------------------------------------------- A.1 the split

def split(rows) -> tuple[list[dict], list[dict]]:
    """15% of EACH corpus to test, drawn once at a fixed seed."""
    rnd = mulberry32(SEED)
    train, test = [], []
    for g in GROUPS:
        sub = sorted([r for r in rows if r["group"] == g], key=lambda r: r["ride"])
        idx = list(range(len(sub)))
        for i in range(len(idx) - 1, 0, -1):           # Fisher-Yates, deterministic
            j = int(rnd() * (i + 1))
            idx[i], idx[j] = idx[j], idx[i]
        n_test = max(1, int(round(TEST_FRAC * len(sub))))
        picked = set(idx[:n_test])
        for i, r in enumerate(sub):
            (test if i in picked else train).append(r)
    return train, test


def twin_exposure(train, test, dtol=0.05, htol=0.10) -> tuple[int, int]:
    """The disclosure the registration promised: how many test rides have a
    near-twin in train, by (distance, ascent) within tolerance, same rider.
    A random split cannot rule this out, so it is measured instead."""
    hit = 0
    for t in test:
        for r in train:
            if r["group"] != t["group"]:
                continue
            if t["x_m"] <= 0 or t["hplus"] <= 0:
                continue
            if (abs(r["x_m"] - t["x_m"]) / t["x_m"] < dtol
                    and abs(r["hplus"] - t["hplus"]) / t["hplus"] < htol):
                hit += 1
                break
    return hit, len(test)


# ------------------------------------------------------------------ A.4/A.5

def folds(rows, k, rep):
    """Stratified k-fold within rider, deterministic per repeat."""
    rnd = mulberry32(SEED + 1000 * rep)
    assign: dict[int, int] = {}
    for g in GROUPS:
        sub = [i for i, r in enumerate(rows) if r["group"] == g]
        idx = list(range(len(sub)))
        for i in range(len(idx) - 1, 0, -1):
            j = int(rnd() * (i + 1))
            idx[i], idx[j] = idx[j], idx[i]
        for pos, si in enumerate(idx):
            assign[sub[si]] = pos % k
    for f in range(k):
        tr = [r for i, r in enumerate(rows) if assign[i] != f]
        va = [r for i, r in enumerate(rows) if assign[i] == f]
        yield tr, va


def cross_validate(train) -> dict:
    """A.4 — repeated stratified k-fold. Every free parameter, including F2's
    and F4's, is fitted INSIDE the fold: a parameter fitted once outside would
    flatter the forms that carry one."""
    out = {}
    for form in FORMS:
        scores = []
        for rep in range(N_REPEATS):
            for tr, va in folds(train, K_FOLDS, rep):
                e, c, ti = fit(tr, form)
                scores.append(cv_loss(va, form, e, c, ti))
        n = len(scores)
        mean = sum(scores) / n
        sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / (n - 1)) if n > 1 else 0.0
        out[form] = {"cv": mean, "se": sd / math.sqrt(n), "n_scores": n}
    return out


def select(train, cv) -> dict:
    """A.5 — CV binding, 1-SE rule toward the simpler form; AIC reported."""
    global _WINNER
    for form in FORMS:
        e, c, ti = fit(train, form)
        cv[form].update({"eps": e, "c": c, "ti": ti, "tau": TAU_GRID[ti],
                         "aic": aic(train, form, e, c, ti)})
    best = min(FORMS, key=lambda f: cv[f]["cv"])
    thr = cv[best]["cv"] + cv[best]["se"]
    tied = [f for f in FORMS if cv[f]["cv"] <= thr]
    winner = min(tied, key=lambda f: (NPAR[f], cv[f]["cv"]))
    aic_best = min(FORMS, key=lambda f: cv[f]["aic"])
    _WINNER = {"form": winner, "eps": cv[winner]["eps"], "c": cv[winner]["c"],
               "ti": cv[winner]["ti"], "tau": cv[winner]["tau"],
               "cv_best": best, "aic_best": aic_best, "tied": tied}
    return _WINNER


# ------------------------------------------------------------------ A.7/A.8

def sensitivity(train, form, eps, c, ti=TAU_PUB_I) -> list[tuple]:
    """A.7 — one-at-a-time sensitivity of the CV loss to the constants, using
    the dispersion A.3 measured. The constants are baked into the cached
    energies, so this perturbs them through the terms they scale: mass and the
    climb term move together (beta = mg/keff), CdA through aero, Crr through
    roll. Reported as elasticities, not as a variance decomposition -- Entry 50
    already did the Sobol version and this is a consistency check on it."""
    base = cv_loss(train, form, eps, c, ti)
    out = []
    tag = {"F1": "f1", "F2": "f2", "F3": f"f3t{ti}", "F4": "f2"}[form]
    for name, key, frac in ((f"m / climb", f"{tag}_climb", 0.10),
                            (f"CdA / aero", f"{tag}_aero", 0.10),
                            (f"Crr / roll", f"{tag}_roll", 0.10),
                            ("eps", None, 0.10)):
        if key is None:
            hi = cv_loss(train, form, eps * (1 + frac), c, ti)
            lo = cv_loss(train, form, eps * (1 - frac), c, ti)
        else:
            def bumped(mult):
                return [{**r, key: r[key] * mult} for r in train]
            hi = cv_loss(bumped(1 + frac), form, eps, c, ti)
            lo = cv_loss(bumped(1 - frac), form, eps, c, ti)
        # LOSS INFLATION, not a derivative. eps is FITTED, so the loss sits at a
        # minimum in it and a central difference is ~0 by construction -- which
        # made the first version report CdA (the most damaging constant) as
        # 0.023 purely because its penalty is symmetric. What matters is how
        # much a perturbation COSTS, so report the worse side.
        infl = (max(lo, hi) / base - 1.0) if base else float("nan")
        out.append((name, base, lo, hi, infl))
    return out


def score_test(test, form, eps, c, label, ti=TAU_PUB_I) -> dict:
    """A.8 — the single scoring of the held-out half. Refuses to run before the
    A.5 winner exists: that is the registered gate, enforced structurally."""
    if _WINNER is None:
        raise RuntimeError("A.8 reached before A.5 selected a form — gate violation")
    e = pct(test, form, eps, c, ti)
    a = [abs(v) for v in e]
    gs = [[abs(x) for x in pct([r for r in test if r["group"] == g], form, eps, c, ti)]
          for g in GROUPS]
    gs = [x for x in gs if x]
    ci_a = boot_ci_strat(gs, SEED)
    gs2 = [[x for x in pct([r for r in test if r["group"] == g], form, eps, c, ti)]
           for g in GROUPS]
    ci_s = boot_ci_strat([x for x in gs2 if x], SEED + 1)
    print(f"    {label:<26} {to_fixed(med_of(a), 2):>6} "
          f"[{to_fixed(ci_a[0], 2)}, {to_fixed(ci_a[1], 2)}]".ljust(19)
          + f"  {to_fixed(med_of(e), 2):>6} "
          f"[{to_fixed(ci_s[0], 2)}, {to_fixed(ci_s[1], 2)}]")
    return {"med_abs": med_of(a), "med_signed": med_of(e)}


def main() -> None:
    rows = load()
    print(f"Entry 52 — the A-chain on {len(rows)} rides of D3-D6 under P_f,r"
          + ("   [SMOKE]" if SMOKE else ""))

    # ---- A.1 / A.2
    train, test = split(rows)
    print(f"\n  A.1/A.2  train {len(train)} · test {len(test)} "
          f"({100 * len(test) / len(rows):.0f}%)")
    hit, ntest = twin_exposure(train, test)
    print(f"           twin exposure: {hit}/{ntest} test rides "
          f"({100 * hit / ntest:.0f}%) have a same-rider train ride within "
          f"5% distance and 10% ascent")

    # ---- A.3
    print("\n  A.3  dispersion of the per-ride inverted constants (train)")
    print(f"    {'constant':<10} {'5th':>9} {'median':>9} {'95th':>9}  {'at prior/rail':>14}")
    for key, prior in (("m_hat", None), ("cda_hat", 0.40), ("crr_hat", 0.008)):
        v = sorted(r[key] for r in train)
        q = lambda p: v[min(len(v) - 1, int(p * (len(v) - 1)))]
        pin = (sum(1 for x in v if abs(x - prior) < 1e-9) if prior else 0)
        note = f"{100 * pin / len(v):.0f}%" if prior else "—"
        print(f"    {key:<10} {q(.05):>9.4g} {q(.50):>9.4g} {q(.95):>9.4g}  {note:>14}")

    # ---- A.4
    print(f"\n  A.4  repeated stratified {K_FOLDS}-fold x {N_REPEATS}, "
          f"loss = mean |log(Ehat/E)|, parameters refitted inside every fold")
    cv = cross_validate(train)
    for f in FORMS:
        print(f"    {f}  CV {cv[f]['cv']:.5f} +/- {cv[f]['se']:.5f} "
              f"({cv[f]['n_scores']} fold scores)")

    # ---- A.5
    w = select(train, cv)
    print(f"\n  A.5  selection")
    print(f"    {'form':<5} {'CV':>9} {'1-SE band':>11} {'AIC':>11} {'eps':>7} {'tau':>5} {'c':>6} {'k':>3}")
    thr = cv[w['cv_best']]['cv'] + cv[w['cv_best']]['se']
    for f in FORMS:
        mark = "  <- CV" if f == w["cv_best"] else ""
        mark += "  <- AIC" if f == w["aic_best"] else ""
        print(f"    {f:<5} {cv[f]['cv']:>9.5f} {'in' if cv[f]['cv'] <= thr else 'out':>11} "
              f"{cv[f]['aic']:>11.1f} {cv[f]['eps']:>7.4f} "
              f"{(cv[f]['tau'] if f == 'F3' else float('nan')):>5.1f} "
              f"{(cv[f]['c'] if f == 'F4' else float('nan')):>6.2f} {NPAR[f]:>3}{mark}")
    print(f"\n    CV best {w['cv_best']} · within 1 SE {w['tied']} "
          f"· AIC best {w['aic_best']}")
    print(f"    WINNER (CV binding, 1-SE toward simpler): {w['form']} "
          f"with eps = {to_fixed(w['eps'], 4)}"
          + (f", tau = {w['tau']} m" if w["form"] == "F3" else "")
          + (f", c = {to_fixed(w['c'], 3)}" if w["form"] == "F4" else ""))
    agree = "AGREE" if w["aic_best"] == w["cv_best"] else "DISAGREE"
    print(f"    P6 — CV and AIC {agree}"
          + ("" if agree == "AGREE" else "; Entry 49's precedent governs (held-out primary)"))

    # ---- A.6 / A.7
    # internal check: tau = 0 is a no-op deadband, so F3 must reproduce F2 exactly
    d = max(abs(e_form(r, "F3", 0.3, C_PUB, 0) - e_form(r, "F2", 0.3)) for r in train[:400])
    print(f"\n    check: F3(tau=0) vs F2 max abs diff = {d:.3e} kJ "
          f"{'GATE-OK' if d < 1e-9 else 'GATE-FAIL'}")
    print(f"\n  A.6  refit on all of D_train: eps = {to_fixed(w['eps'], 4)}"
          + (f", tau = {w['tau']} m" if w["form"] == "F3" else ""))
    print(f"\n  A.7  sensitivity of the winner's CV loss (+/-10% one at a time,"
          f" reported as the cost of being wrong)")
    print(f"    {'perturbed':<12} {'base':>9} {'-10%':>9} {'+10%':>9} {'loss infl.':>11}")
    sens = sorted(sensitivity(train, w["form"], w["eps"], w["c"], w["ti"]),
                  key=lambda z: -z[4])
    for name, base, lo, hi, el in sens:
        print(f"    {name:<12} {base:>9.5f} {lo:>9.5f} {hi:>9.5f} {100 * el:>10.1f}%")
    print(f"    ranked most to least damaging; corroborates Entry 50 if eps ranks last")

    # ---- A.8
    print(f"\n  A.8  D_test scored ONCE (n = {len(test)})")
    print(f"    {'estimator':<26} {'med|D%|':>6} {'[95% CI]':<19}  {'signed':>6} [95% CI]")
    res = {}
    for f in FORMS:
        tag = f + (" (WINNER)" if f == w["form"] else "")
        res[f] = score_test(test, f, cv[f]["eps"], cv[f]["c"], tag, cv[f]["ti"])
    # F_base: a comparator, not a contestant
    ce = [100.0 * (r["canon_kj"] - r["emp"]) / r["emp"]
          for r in test if is_finite(r["canon_kj"])]
    if ce:
        print(f"    {'F_base (comparator)':<26} {to_fixed(med_of([abs(v) for v in ce]), 2):>6} "
              f"{'':<19}  {to_fixed(med_of(ce), 2):>6}")
        wf = [abs(v) for v in pct(test, w["form"], w["eps"], w["c"], w["ti"])]
        pair = [(a, abs(b)) for a, b in zip(wf, ce)]
        win = sum(1 for a, b in pair if a < b)
        los = sum(1 for a, b in pair if a > b)
        print(f"    P3 — closed form closer than F_base on {win}/{win + los}, "
              f"sign test p = {to_fixed(sign_p(win, los), 4)}")

    out = os.path.join(RESULTS, "e52_split" + ("" if AERO == "reg" else "." + AERO) + (".SMOKE" if SMOKE else "") + ".csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("form,npar,cv,cv_se,aic,eps,c,tau,test_med_abs,test_med_signed,winner\n")
        for f in FORMS:
            fh.write(f"{f},{NPAR[f]},{cv[f]['cv']:.6f},{cv[f]['se']:.6f},"
                     f"{cv[f]['aic']:.3f},{to_fixed(cv[f]['eps'], 4)},"
                     f"{to_fixed(cv[f]['c'], 4) if f == 'F4' else ''},"
                     f"{cv[f]['tau'] if f == 'F3' else ''},"
                     f"{to_fixed(res[f]['med_abs'], 4)},"
                     f"{to_fixed(res[f]['med_signed'], 4)},"
                     f"{1 if f == w['form'] else 0}\n")
    # summary row set: the numbers the gate battery re-derives and the article
    # cites. Written here so a published claim traces to a file, not a console log.
    summ = os.path.join(RESULTS, "e52_summary" + ("" if AERO == "reg" else "." + AERO) + (".SMOKE" if SMOKE else "") + ".csv")
    with open(summ, "w", encoding="utf-8") as fh:
        fh.write("key,value\n")
        fh.write(f"f3_test_med_abs,{to_fixed(res[w['form']]['med_abs'], 4)}\n")
        fh.write(f"f3_test_med_signed,{to_fixed(res[w['form']]['med_signed'], 4)}\n")
        fh.write(f"eps,{to_fixed(w['eps'], 4)}\n")
        fh.write(f"tau,{w['tau']}\n")
        fh.write(f"winner,{w['form']}\n")
        fh.write(f"n_train,{len(train)}\n")
        fh.write(f"n_test,{len(test)}\n")
        if ce:
            fh.write(f"fbase_test_med_abs,{to_fixed(med_of([abs(v) for v in ce]), 4)}\n")
            fh.write(f"fbase_test_med_signed,{to_fixed(med_of(ce), 4)}\n")
        fh.write(f"twin_pct,{to_fixed(100 * hit / ntest, 4)}\n")
        # F4 too: the paper ships BOTH the profile form (F3) and the
        # totals-only form (F4), so both need a gated number.
        for f in FORMS:
            fh.write(f"{f.lower()}_test_med_abs,{to_fixed(res[f]['med_abs'], 4)}\n")
            fh.write(f"{f.lower()}_test_med_signed,{to_fixed(res[f]['med_signed'], 4)}\n")
    print(f"\nwrote {os.path.basename(out)} and {os.path.basename(summ)}")


if __name__ == "__main__":
    main()
