#!/usr/bin/env python3
"""Entry 63 — F5, the KE-buffer valley toll, benchmarked against F3/F4.

MOTIVATION (Entry 63's registration). The backlash deadband that turns F2 into
F3 does two jobs at once: it annihilates swings under 2*tau and charges every
surviving swing a fixed 2*tau toll. The second job has a physical reading: the
kinetic-energy buffer a rider carries across a descent->climb valley — the
descent's last metres of release are stored as KE and lift the climb's first
metres, so neither is leg-paid nor leg-credited. The buffer height is
computable from constants the chain already inverts per ride,

    h_KE = (v_e^2 - v_c^2) / 2g,   v_e = min(v_b, max(v_t(s_-), v_f)),

with v_t the coasting terminal speed on the descent's mean grade, v_f the flat
equilibrium speed, v_c the quasi-steady speed of the following climb and v_b
the rider's braking cap. F5 makes that toll explicit and per-valley instead of
fitted-and-constant:

    F5 = F3(tau_n = 0.5 m)  with  climb -= beta*T,  recov1 += beta*T,
    T(v_b) = sum over valleys of min(D, H, max(0, h_KE - 2*tau_n))

where D/H are the filtered amplitudes of the descent/climb swings meeting at
the valley and tau_n is a small noise-only deadband (jitter is measurement,
not physics — it stays filtered under any form). The v_c clamp (v_c <= v_e)
makes a descent-into-flat valley toll ZERO automatically: a run-out collects
the buffer against the alpha bill, so the credit survives — only a real climb
transfers it. F5 carries (eps, v_b): the same parameter count as F3's
(eps, tau), but tau's job is now split into a fixed noise floor and a
physics-computed, per-valley cap.

WHY THE SURGERY IS EXACT: approximate() returns climb = beta*hplus and
recov1 = -beta*hminus identically (engines.py), so subtracting beta*T from the
climb component and adding it to recov1 IS evaluating F3(tau_n) on totals with
hplus-T and hminus-T. Linearity in eps is untouched, so the two-point cache
still pins the family, and the vb=0 arm (v_e = 0 => T = 0) must reproduce
F3(tau=0.5) to 1e-9 — an internal gate, mirrored on e52's F3(tau=0)==F2.

PROTOCOL: the A-chain of Entry 52, unchanged — same cache, same seed-48 split,
same folds, same loss, F3/F4 fitted by e52_split's own fit() — so F5's numbers
are comparable to the published ones by construction (the e46/e47 shared-
population precedent). F3/F4 test numbers must REPRODUCE e52_split.csv; that
reproduction is itself a check that nothing drifted.

CAVEATS (stated, not hidden): v_e assumes the descent reaches quasi-steady
speed (short steep descents overestimate, bounded by the min(D,..) amplitude
cap); wind is zero corpus-wide (inherited from the iterator, applies to every
form equally); v_b is one global behavioural constant, fitted like eps.

Outputs: data/results/e63_tolls.csv (per-ride toll sums on the v_b grid),
         data/results/e63_split.csv  (the F3/F4/F5 comparison table)
Run:     python3 src/harness/e63_f5_kebuffer.py     (E63_SMOKE=1 for a subset;
         E63_REBUILD=1 to force the toll walk when the CSV already exists)
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

SMOKE = bool(os.environ.get("E63_SMOKE"))
if SMOKE:                      # align e52's suffix logic before importing it
    os.environ["E52_SMOKE"] = "1"

from bicycling_energy_model import (build_profile, deadband,  # noqa: E402
                                    extract_regime_powers, overall_mean_power,
                                    resample_profile)
from bicycling_energy_model.engines import G  # noqa: E402
from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402
from bicycling_energy_model.util import env_suffix  # noqa: E402

from e52_build import C_PUB, TAU_GRID, TAU_PUB_I, e_form  # noqa: E402
from e52_split import (EPS_BOUNDS, GROUPS, SEED, aic,  # noqa: E402
                       cross_validate, cv_loss, fit, folds, load, logratio,
                       pct, split, twin_exposure)
from e44_scurve import corpus_rides  # noqa: E402
from perride_invert import (CLIMB_THR, DESC_THR, ENGINE_DX, KEFF,  # noqa: E402
                            RESULTS, RHO)
from skc_compare import boot_ci_strat, med_of, sign_p  # noqa: E402

# The noise-only deadband, metres. Default 0.5; E63_TAUN=2.0 is the
# sensitivity arm at the jitter-motivated floor of A.4 (must sit on TAU_GRID
# so the cached F3 components exist). Env-suffixed outputs per the repo rule:
# a sensitivity run must never overwrite the canonical CSV.
TAU_N = float(os.environ.get("E63_TAUN") or 0.5)
if TAU_N not in TAU_GRID:
    raise SystemExit(f"E63_TAUN={TAU_N} is not on e52's tau grid {TAU_GRID}")
TI_N = TAU_GRID.index(TAU_N)      # its index in the cached F3 grid
# v_b grid, km/h. 0 is the degenerate arm (v_e = 0 => every toll 0 => F5 must
# equal F3(tau_n) exactly — the internal gate); 999 is the never-brake arm.
VB_KMH = (0.0, 24.0, 28.0, 32.0, 36.0, 40.0, 42.0, 44.0, 48.0, 55.0, 65.0, 999.0)
NPAR5 = 2                         # eps + v_b, same count as F3's eps + tau
DECOMP = bool(os.environ.get("E63_DECOMP"))   # decomposition arm only
SUFF = env_suffix("E63_TAUN") + (".SMOKE" if SMOKE else "")
TOLLS_CSV = os.path.join(RESULTS, "e63_tolls" + SUFF + ".csv")


# ------------------------------------------------------------ stage 1: tolls

def swing_list(xs, hs) -> list[tuple[int, float, float]]:
    """Alternating monotone swings (dir, amplitude m, run m) of a filtered
    elevation series. Turn points sit at the LAST sample the signal moved in
    the old direction, so backlash plateaus dilute neither swing's grade."""
    out = []
    dir_ = 0
    x0 = xm = xs[0]
    h0 = hm = hs[0]
    for i in range(1, len(xs)):
        dy = hs[i] - hs[i - 1]
        if dy == 0:
            continue
        d = 1 if dy > 0 else -1
        if d != dir_:
            if dir_ != 0:
                out.append((dir_, abs(hm - h0), xm - x0))
            dir_, x0, h0 = d, xm, hm
        xm, hm = xs[i], hs[i]
    if dir_ != 0:
        out.append((dir_, abs(hm - h0), xm - x0))
    return out


def ride_tolls(prof, m, crr, cda, vf, p_climb) -> dict:
    """Toll sums T(v_b) in metres for one ride, plus valley diagnostics."""
    hf = deadband(prof["h"], TAU_N)
    swings = [s for s in swing_list(prof["x"], hf) if s[2] > 0]
    b = 0.5 * RHO * cda
    mg = m * G
    tolls = [0.0] * len(VB_KMH)
    n_val = 0
    cap_sum = 0.0
    for j in range(len(swings) - 1):
        d_dir, D, run_d = swings[j]
        u_dir, H, run_u = swings[j + 1]
        if d_dir != -1 or u_dir != 1:
            continue
        n_val += 1
        cap_sum += min(D, H)
        s_d, s_u = D / run_d, H / run_u
        sec_d = math.sqrt(1 + s_d * s_d)
        sec_u = math.sqrt(1 + s_u * s_u)
        # coasting terminal on the descent's mean grade (canonical's sin/cos)
        vt = math.sqrt(max(0.0, mg * (s_d - crr) / sec_d) / b)
        # quasi-steady speed of the following climb; the v_e clamp below makes
        # a shallow "climb" (v_c >= v_e, e.g. a run-out) toll exactly zero
        vc_den = mg * (s_u + crr) / sec_u
        vc = KEFF * p_climb / vc_den if vc_den > 0 else float("inf")
        for k, vb_kmh in enumerate(VB_KMH):
            ve = min(vb_kmh / 3.6, max(vt, vf))
            buf = max(0.0, (ve * ve - min(vc, ve) ** 2) / (2 * G) - 2 * TAU_N)
            tolls[k] += min(D, H, buf)
    return {"n_valleys": n_val, "cap_m": cap_sum,
            **{f"toll_vb{k}": tolls[k] for k in range(len(VB_KMH))}}


def build_tolls(cache_rows) -> None:
    """Walk the corpora ONCE (labels replicate e52_build's counter exactly so
    the join is by construction) and write the per-ride toll table."""
    idx = {r["ride"]: r for r in cache_rows}
    out_rows = []
    seen: dict[str, int] = {}
    for group, pts, _mass in corpus_rides():
        if group not in GROUPS:
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if SMOKE and i >= 15:
            continue
        label = f"{group}#{i}"
        r = idx.get(label)
        if r is None:
            continue
        try:
            phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
            prof = resample_profile(phys, ENGINE_DX)
            rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
            flat = (rp["flat"]["mean"] if rp["flat"]["mean"] is not None
                    else overall_mean_power(pts))
            p_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat
            t = ride_tolls(prof, r["m_hat"], r["crr_hat"], r["cda_hat"],
                           r["vf_kmh"] / 3.6, p_climb)
        except Exception:
            continue
        out_rows.append({"group": group, "ride": label, **t})
    cols = (["group", "ride", "n_valleys", "cap_m"]
            + [f"toll_vb{k}" for k in range(len(VB_KMH))])
    with open(TOLLS_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"  wrote {os.path.basename(TOLLS_CSV)} ({len(out_rows)} rides)")


def join_tolls(rows) -> list[dict]:
    """Attach beta*T (kJ) per v_b arm; a ride the walk missed tolls 0 and is
    counted out loud rather than dropped — the population must match e52's."""
    tolls: dict[str, dict] = {}
    with open(TOLLS_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            tolls[r["ride"]] = r
    missing = 0
    for r in rows:
        t = tolls.get(r["ride"])
        beta_kj = r["m_hat"] * G / KEFF / 1000.0
        for k in range(len(VB_KMH)):
            m_toll = float(t[f"toll_vb{k}"]) if t else 0.0
            r[f"bt{k}"] = beta_kj * m_toll
        r["n_valleys"] = float(t["n_valleys"]) if t else 0.0
        missing += 0 if t else 1
    if missing:
        print(f"  WARNING: {missing} cache rides missing from the toll walk "
              f"(tolled 0 — population unchanged)")
    return rows


# ----------------------------------------------------- stage 2: F5's algebra

def e_form5(r: dict, eps: float, vbi: int) -> float:
    """F5 energy in kJ: F3(tau_n)'s components with the valley toll moved off
    both the climb charge and the descent credit."""
    k = f"f3t{TI_N}"
    bt = r[f"bt{vbi}"] * 1000.0
    return (r[k + "_roll"] + r[k + "_aero"] + (r[k + "_climb"] - bt)
            + eps * (r[k + "_recov1"] + bt)) / 1000.0


def usable5(r: dict, vbi: int) -> bool:
    """e52's fixed-population rule, per v_b arm (mirrors _usable per tau)."""
    return (e_form5(r, EPS_BOUNDS[0], vbi) > 0
            and e_form5(r, EPS_BOUNDS[1], vbi) > 0)


def cv_loss5(rows, eps, vbi) -> float:
    v = [abs(math.log(e / r["emp"])) if (e := e_form5(r, eps, vbi)) > 0
         else float("inf") for r in rows if usable5(r, vbi)]
    return sum(v) / len(v) if v else float("inf")


def pct5(rows, eps, vbi) -> list[float]:
    return [100.0 * (e_form5(r, eps, vbi) - r["emp"]) / r["emp"] for r in rows]


def fit5(rows) -> tuple[float, int]:
    """(eps, vb-index) minimising the CV loss: e52's 5x201 eps refinement at
    every grid arm, arm picked by loss — the exact mirror of F3's fit over the
    tau grid. Precomputing (fixed, recov) per arm changes nothing numerically;
    it only keeps 20 fold-fits affordable."""
    best = (float("inf"), 0.2, 0)
    for vbi in range(len(VB_KMH)):
        sub = [(e_form5(r, 0.0, vbi), e_form5(r, 1.0, vbi) - e_form5(r, 0.0, vbi),
                r["emp"]) for r in rows if usable5(r, vbi)]
        if not sub:
            continue

        def loss(e: float) -> float:
            tot = 0.0
            for fixed, rec, emp in sub:
                v = fixed + e * rec
                tot += abs(math.log(v / emp)) if v > 0 else float("inf")
            return tot / len(sub)

        lo, hi = EPS_BOUNDS
        e_best = 0.2
        for _ in range(5):
            step = (hi - lo) / 200
            cand = [lo + i * step for i in range(201)]
            e_best = min(cand, key=loss)
            lo, hi = e_best - step, e_best + step
        l_best = loss(e_best)
        if l_best < best[0]:
            best = (l_best, e_best, vbi)
    return best[1], best[2]


def aic5(rows, eps, vbi) -> float:
    r = [abs(math.log(e / q["emp"])) if (e := e_form5(q, eps, vbi)) > 0
         else float("inf") for q in rows if usable5(q, vbi)]
    n = len(r)
    if not n:
        return float("nan")
    b = sum(r) / n or 1e-12
    return 2 * NPAR5 - 2 * (-n * math.log(2 * b) - n)


def cv_f3_fixed(train, ti) -> dict:
    """The decomposition arm: F3 with tau PINNED at the noise floor, only eps
    refitted in-fold. F5's gain over this number is what the valley toll buys
    beyond the filtering both share; F3-fitted's gain over F5 is what the extra
    fitted removal buys beyond the physics. CV only — the test half is never
    scored under this arm (it is a diagnostic, not a registered form)."""
    def eps_opt(rows):
        lo, hi = EPS_BOUNDS
        best = 0.2
        for _ in range(5):
            step = (hi - lo) / 200
            best = min([lo + i * step for i in range(201)],
                       key=lambda e: cv_loss(rows, "F3", e, C_PUB, ti))
            lo, hi = best - step, best + step
        return best
    scores = []
    for rep in range(4):
        for tr, va in folds(train, 5, rep):
            scores.append(cv_loss(va, "F3", eps_opt(tr), C_PUB, ti))
    n = len(scores)
    mean = sum(scores) / n
    sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / (n - 1)) if n > 1 else 0.0
    return {"cv": mean, "se": sd / math.sqrt(n), "n_scores": n,
            "eps": eps_opt(train)}


def cv5(train) -> dict:
    scores = []
    for rep in range(4):                       # e52's N_REPEATS x K_FOLDS
        for tr, va in folds(train, 5, rep):
            e, vbi = fit5(tr)
            scores.append(cv_loss5(va, e, vbi))
    n = len(scores)
    mean = sum(scores) / n
    sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / (n - 1)) if n > 1 else 0.0
    return {"cv": mean, "se": sd / math.sqrt(n), "n_scores": n}


def score(test, label, evaluate) -> dict:
    """A.8 line for one estimator: med|D%| and signed, stratified bootstrap CIs
    — the exact shape of e52_split.score_test."""
    e = evaluate(test)
    a = [abs(v) for v in e]
    by_g = lambda f: [x for x in (f([r for r in test if r["group"] == g])
                                  for g in GROUPS) if x]
    ci_a = boot_ci_strat(by_g(lambda s: [abs(v) for v in evaluate(s)]), SEED)
    ci_s = boot_ci_strat(by_g(evaluate), SEED + 1)
    print(f"    {label:<26} {to_fixed(med_of(a), 2):>6} "
          f"[{to_fixed(ci_a[0], 2)}, {to_fixed(ci_a[1], 2)}]".ljust(19)
          + f"  {to_fixed(med_of(e), 2):>6} "
          f"[{to_fixed(ci_s[0], 2)}, {to_fixed(ci_s[1], 2)}]")
    return {"med_abs": med_of(a), "med_signed": med_of(e)}


def main() -> None:
    rows = load()
    print(f"Entry 63 — F5 (KE-buffer valley toll) vs F3/F4 on {len(rows)} rides"
          + ("   [SMOKE]" if SMOKE else ""))
    if os.path.exists(TOLLS_CSV) and not os.environ.get("E63_REBUILD"):
        print(f"  reusing {os.path.basename(TOLLS_CSV)} (E63_REBUILD=1 to rewalk)")
    else:
        build_tolls(rows)
    rows = join_tolls(rows)

    # internal gate: the vb = 0 arm zeroes every toll, so F5 must be F3(tau_n)
    d = max(abs(e_form5(r, 0.3, 0) - e_form(r, "F3", 0.3, C_PUB, TI_N))
            for r in rows)
    print(f"\n  gate: F5(vb=0) vs F3(tau={TAU_N}) max abs diff = {d:.3e} kJ "
          f"{'GATE-OK' if d < 1e-9 else 'GATE-FAIL'}")
    if not d < 1e-9:
        raise SystemExit("F5's degenerate arm does not reproduce F3 — abort")

    n_val = sorted(r["n_valleys"] for r in rows)
    t42 = sorted(r[f"bt{VB_KMH.index(42.0)}"] / (r["m_hat"] * G / KEFF / 1000.0)
                 for r in rows)
    q = lambda v, p: v[min(len(v) - 1, int(p * (len(v) - 1)))]
    print(f"  valleys/ride median {q(n_val, .5):.0f} "
          f"(5th {q(n_val, .05):.0f}, 95th {q(n_val, .95):.0f}); "
          f"T(42 km/h) median {q(t42, .5):.1f} m "
          f"(5th {q(t42, .05):.1f}, 95th {q(t42, .95):.1f})")

    train, test = split(rows)
    print(f"\n  A.1/A.2  train {len(train)} · test {len(test)} — seed {SEED}, "
          f"the SAME split as Entry 52 (shared population by construction)")
    hit, ntest = twin_exposure(train, test)
    print(f"           twin exposure {hit}/{ntest} ({100 * hit / ntest:.0f}%)")

    if DECOMP:
        nf = cv_f3_fixed(train, TI_N)
        print(f"\n  decomposition arm only: F3 with tau pinned at {TAU_N} m "
              f"(the shared noise floor, eps in-fold)")
        print(f"    F3(tau={TAU_N} fixed)  CV {nf['cv']:.5f} +/- {nf['se']:.5f} "
              f"({nf['n_scores']} fold scores)   full-train eps {nf['eps']:.4f}")
        return

    print("\n  A.4  repeated stratified 5-fold x 4, parameters refitted in-fold")
    cv = cross_validate(train)                 # F1-F4 through e52's own path
    cv["F5"] = cv5(train)
    cv["F3tn"] = cv_f3_fixed(train, TI_N)      # the shared-noise-floor arm
    for f in ("F3", "F4", "F5"):
        print(f"    {f}  CV {cv[f]['cv']:.5f} +/- {cv[f]['se']:.5f} "
              f"({cv[f]['n_scores']} fold scores)")
    print(f"    [decomposition: F3(tau={TAU_N} fixed) CV {cv['F3tn']['cv']:.5f} "
          f"+/- {cv['F3tn']['se']:.5f} — F5's gain over this is the toll's "
          f"contribution beyond the shared filter]")

    # ---- A.5 over {F3, F4, F5} (F1/F2 stay in the table as e52 left them)
    fits = {}
    for f in ("F3", "F4"):
        e, c, ti = fit(train, f)
        fits[f] = {"eps": e, "c": c, "ti": ti,
                   "aic": aic(train, f, e, c, ti)}
    e5, vbi5 = fit5(train)
    fits["F5"] = {"eps": e5, "vbi": vbi5, "aic": aic5(train, e5, vbi5)}
    forms = ("F3", "F4", "F5")
    npar = {"F3": 2, "F4": 2, "F5": NPAR5}
    best = min(forms, key=lambda f: cv[f]["cv"])
    thr = cv[best]["cv"] + cv[best]["se"]
    tied = [f for f in forms if cv[f]["cv"] <= thr]
    winner = min(tied, key=lambda f: (npar[f], cv[f]["cv"]))
    aic_best = min(forms, key=lambda f: fits[f]["aic"])
    print(f"\n  A.5  {'form':<4} {'CV':>9} {'1-SE':>5} {'AIC':>11} {'eps':>8} "
          f"{'tau':>5} {'c':>6} {'vb':>6}")
    for f in forms:
        extra = {"F3": (TAU_GRID[fits[f]["ti"]] if f == "F3" else None),
                 "F4": None, "F5": None}
        print(f"       {f:<4} {cv[f]['cv']:>9.5f} "
              f"{'in' if cv[f]['cv'] <= thr else 'out':>5} "
              f"{fits[f]['aic']:>11.1f} {fits[f]['eps']:>8.4f} "
              f"{(TAU_GRID[fits[f]['ti']] if f == 'F3' else float('nan')):>5.1f} "
              f"{(fits[f]['c'] if f == 'F4' else float('nan')):>6.2f} "
              f"{(VB_KMH[fits[f]['vbi']] if f == 'F5' else float('nan')):>6.1f}")
    print(f"       CV best {best} · within 1 SE {tied} · AIC best {aic_best}"
          f" · WINNER {winner}")
    if "F5" in fits:
        vbs = VB_KMH[fits["F5"]["vbi"]]
        print(f"       F5 fitted v_b = {vbs:g} km/h"
              + ("  (degenerate arm — F5 collapses to F3(tau=0.5): the toll "
                 "buys nothing)" if fits["F5"]["vbi"] == 0 else ""))

    # ---- A.8: the held-out half, scored once, all three forms + comparator
    print(f"\n  A.8  D_test scored ONCE (n = {len(test)})")
    print(f"    {'estimator':<26} {'med|D%|':>6} {'[95% CI]':<19}  "
          f"{'signed':>6} [95% CI]")
    res = {}
    for f in ("F3", "F4"):
        res[f] = score(test, f + (" (WINNER)" if f == winner else ""),
                       lambda s, f=f: pct(s, f, fits[f]["eps"], fits[f]["c"],
                                          fits[f]["ti"]))
    res["F5"] = score(test, "F5" + (" (WINNER)" if winner == "F5" else ""),
                      lambda s: pct5(s, fits["F5"]["eps"], fits["F5"]["vbi"]))
    from bicycling_energy_model import is_finite
    ce = [100.0 * (r["canon_kj"] - r["emp"]) / r["emp"]
          for r in test if is_finite(r["canon_kj"])]
    if ce:
        print(f"    {'F_base (comparator)':<26} "
              f"{to_fixed(med_of([abs(v) for v in ce]), 2):>6}"
              f"{'':<20}  {to_fixed(med_of(ce), 2):>6}")
    wf = (pct5(test, fits["F5"]["eps"], fits["F5"]["vbi"]) if winner == "F5"
          else pct(test, winner, fits[winner]["eps"], fits[winner]["c"],
                   fits[winner]["ti"]))
    if ce:
        pair = list(zip([abs(v) for v in wf], [abs(v) for v in ce]))
        win = sum(1 for a_, b_ in pair if a_ < b_)
        los = sum(1 for a_, b_ in pair if a_ > b_)
        print(f"    winner vs F_base: closer on {win}/{win + los}, "
              f"sign p = {to_fixed(sign_p(win, los), 4)}")

    out = os.path.join(RESULTS, "e63_split" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("form,npar,cv,cv_se,aic,eps,c,tau,vb_kmh,"
                 "test_med_abs,test_med_signed,winner\n")
        for f in forms:
            fh.write(f"{f},{npar[f]},{cv[f]['cv']:.6f},{cv[f]['se']:.6f},"
                     f"{fits[f]['aic']:.3f},{to_fixed(fits[f]['eps'], 4)},"
                     f"{to_fixed(fits[f]['c'], 4) if f == 'F4' else ''},"
                     f"{TAU_GRID[fits[f]['ti']] if f == 'F3' else ''},"
                     f"{VB_KMH[fits[f]['vbi']] if f == 'F5' else ''},"
                     f"{to_fixed(res[f]['med_abs'], 4)},"
                     f"{to_fixed(res[f]['med_signed'], 4)},"
                     f"{1 if f == winner else 0}\n")
        # the diagnostic arm: CV only, deliberately no test columns
        fh.write(f"F3tn,1,{cv['F3tn']['cv']:.6f},{cv['F3tn']['se']:.6f},,"
                 f"{to_fixed(cv['F3tn']['eps'], 4)},,{TAU_N},,,,0\n")
    print(f"\nwrote {os.path.basename(out)}")


if __name__ == "__main__":
    main()
