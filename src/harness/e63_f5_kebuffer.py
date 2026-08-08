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

ENTRY 64 — the registered next steps, in this same file so the algebra has one
copy. Two additional one-parameter forms ride the same chain:

  F5f  v_b frozen at the never-brake arm BEFORE fitting (Entry 63 watched the
       grid rail there twice, so freezing is registered, not peeking) — eps is
       the only fitted parameter, NPAR = 1, and under A.5's 1-SE-toward-simpler
       rule F5f WINS if it stays inside the band.
  F5m  v_b MEASURED per ride: the time-weighted 95th-percentile moving speed
       over descent-graded 30 m cells (the same cell/gating conventions as
       measured_flat_speed), falling back to the ride's v_f when a ride has no
       descent cells. v_b leaves the parameter class entirely — it joins
       m_hat/cda_hat/crr_hat as per-ride telemetry — so NPAR = 1.

Two diagnostic modes (both read the toll CSV, fit nothing on the test half):

  E63_LORO=1     leave-one-rider-out contest, F3 vs F5f vs F5m (Entry 54's
                 strictness: fit every free parameter on the OTHER riders'
                 train-half rides, score the held-out rider's test-half rides;
                 seed 54 for the CIs). The absorption question: a fitted tau
                 carries the calibration mix, a computed toll should travel.
  E63_TAUPRED=1  Entry 39's prediction sharpened: per rider group, the fitted
                 tau* (on that group's train-half alone) against
                 tau_noise + h_KE/(2(1-eps)) with h_KE from the group's
                 MEASURED v_b and v_f. Diagnostic table, no gate.
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

from bicycling_energy_model import (approximate, build_profile,  # noqa: E402
                                    deadband, extract_regime_powers,
                                    overall_mean_power, resample_profile)
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
# the same 30 m cell altitudes and moving gate measured_flat_speed uses — the
# measured v_b must share the flat speed's conventions or the two aren't
# comparable telemetry
from bicycling_energy_model.regime import _VSTOP, _cell_alt  # noqa: E402

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
VB_INF_I = VB_KMH.index(999.0)    # F5f's frozen arm
SEED64 = 54                       # 42..53 taken (see the harness seed ledger)
DECOMP = bool(os.environ.get("E63_DECOMP"))   # decomposition arm only
LORO = bool(os.environ.get("E63_LORO"))       # Entry 64 transfer contest
TAUPRED = bool(os.environ.get("E63_TAUPRED"))  # Entry 64 tau* prediction
# Entry 65's two rival answers to the fragmentation suspect. RAINFLOW replaces
# the single-pass adjacent-swing pairing with 4-point rainflow (closed cycles
# tolled min(R, buffer) innermost-first, flanks spliced so real feet recover
# full amplitude) — the raw profile stays raw. SMOOTH replaces the measurement:
# a Gaussian of scale sigma metres on the 5 m grid before enumeration, F5's
# components recomputed on the smoothed profile (they leave the e52 cache, so
# the build stores them and checks the two-point interpolation against fresh
# engine calls). Both are meant to run with E63_TAUN=0.0 — no deadband at all.
RAINFLOW = bool(os.environ.get("E63_RAINFLOW"))
SMOOTH = float(os.environ.get("E63_SMOOTH") or 0)   # Gaussian sigma, metres
SUFF = env_suffix("E63_TAUN", "E63_RAINFLOW", "E63_SMOOTH") + (".SMOKE" if SMOKE else "")
TOLLS_CSV = os.path.join(RESULTS, "e63_tolls" + SUFF + ".csv")
SM_CHECK: list[float] = []        # build-time sm-component vs engine deviations


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


def gaussian_smooth(h: list[float], dx: float, sigma: float) -> list[float]:
    """Gaussian smoothing on the uniform grid, kernel truncated at 3 sigma and
    renormalised at the edges (no phase shift, no padding invention)."""
    k = max(1, math.ceil(3 * sigma / dx))
    w = [math.exp(-0.5 * (i * dx / sigma) ** 2) for i in range(-k, k + 1)]
    n = len(h)
    out = [0.0] * n
    for i in range(n):
        s = wsum = 0.0
        for j in range(max(0, i - k), min(n, i + k + 1)):
            wj = w[j - i + k]
            s += wj * h[j]
            wsum += wj
        out[i] = s / wsum
    return out


def extrema_list(xs, hs) -> list[tuple[float, float]]:
    """Turn points [(x, h)] of the series, plateaus collapsed to their last
    sample (swing_list's convention), endpoints included."""
    pts = []
    dir_ = 0
    xm, hm = xs[0], hs[0]
    for i in range(1, len(xs)):
        dy = hs[i] - hs[i - 1]
        if dy == 0:
            continue
        d = 1 if dy > 0 else -1
        if d != dir_:
            pts.append((xm, hm))
            dir_ = d
        xm, hm = xs[i], hs[i]
    pts.append((xm, hm))
    return pts


def measured_vb(pts, vf: float) -> tuple[float, str]:
    """The ride's MEASURED descent speed cap (m/s): time-weighted 95th
    percentile of moving speed over 30 m cells whose grade <= DESC_THR —
    measured_flat_speed's cells and gates, pointed downhill. Falls back to v_f
    (and says so) when the ride has no qualifying descent samples."""
    DX = 30
    x0 = pts[0]["x"]
    nc = math.floor((pts[-1]["x"] - x0) / DX)
    if nc < 2:
        return vf, "vf"
    cell_alt = _cell_alt(pts, x0, DX, nc)
    desc = [(cell_alt[k + 1] - cell_alt[k]) / DX <= DESC_THR for k in range(nc)]
    vw = []
    for r in pts:
        k = math.floor((r["x"] - x0) / DX)
        if 0 <= k < nc and desc[k] and r.get("v") is not None and r["v"] >= _VSTOP:
            vw.append((r["v"], r.get("dt") or 1))
    if not vw:
        return vf, "vf"
    vw.sort()
    total = sum(w for _, w in vw)
    acc = 0.0
    for v, w in vw:
        acc += w
        if acc >= 0.95 * total:
            return v, "meas"
    return vw[-1][0], "meas"


def ride_tolls(prof, m, crr, cda, vf, p_climb, vb_m=None) -> dict:
    """Toll sums T(v_b) in metres for one ride, plus valley diagnostics.
    `vb_m` (m/s) is the ride's measured cap; its toll lands in `toll_vbm`."""
    hf = deadband(prof["h"], TAU_N)
    b = 0.5 * RHO * cda
    mg = m * G
    vbs = [v / 3.6 for v in VB_KMH] + [vb_m if vb_m is not None else vf]
    tolls = [0.0] * len(vbs)
    n_val = 0
    cap_sum = 0.0

    def buffers(s_d: float, s_u: float) -> list[float]:
        """Per-arm buffer heights for one valley (descent grade s_d into climb
        grade s_u). Coasting terminal on the descent (canonical's sin/cos);
        quasi-steady speed of the climb — the v_e clamp makes a shallow
        'climb' (v_c >= v_e, e.g. a run-out) toll exactly zero."""
        sec_d = math.sqrt(1 + s_d * s_d)
        sec_u = math.sqrt(1 + s_u * s_u)
        vt = math.sqrt(max(0.0, mg * (s_d - crr) / sec_d) / b)
        vc_den = mg * (s_u + crr) / sec_u
        vc = KEFF * p_climb / vc_den if vc_den > 0 else float("inf")
        out = []
        for vb in vbs:
            ve = min(vb, max(vt, vf))
            out.append(max(0.0, (ve * ve - min(vc, ve) ** 2) / (2 * G)
                           - 2 * TAU_N))
        return out

    if RAINFLOW:
        # 4-point rainflow over the turn points: a closed cycle is one roller
        # (its fall and rise share the range R), tolled min(R, buffer) and
        # spliced out so the enclosing swing re-merges — the true descent
        # feet recover their full amplitude in the residue pass below.
        def seg_grade(a, b_):
            run = b_[0] - a[0]
            return abs(b_[1] - a[1]) / run if run > 0 else 0.0

        st: list[tuple[float, float]] = []
        for pnt in extrema_list(prof["x"], hf):
            st.append(pnt)
            while len(st) >= 4:
                r1 = abs(st[-4][1] - st[-3][1])
                r2 = abs(st[-3][1] - st[-2][1])
                r3 = abs(st[-2][1] - st[-1][1])
                if not (r2 <= r1 and r2 <= r3):
                    break
                A, B = st[-3], st[-2]
                if B[1] < A[1]:      # dip: fall A->B nested in a rise
                    s_d, s_u = seg_grade(A, B), seg_grade(B, st[-1])
                else:                # blip: rise A->B nested in a fall
                    s_d, s_u = seg_grade(st[-4], A), seg_grade(A, B)
                if r2 > 0:
                    n_val += 1
                    cap_sum += r2
                    for k, buf in enumerate(buffers(s_d, s_u)):
                        tolls[k] += min(r2, buf)
                del st[-3:-1]
        for j in range(len(st) - 2):     # residue: the macro valleys
            a, bb, c = st[j], st[j + 1], st[j + 2]
            if bb[1] < a[1] and c[1] > bb[1]:
                D, H = a[1] - bb[1], c[1] - bb[1]
                n_val += 1
                cap_sum += min(D, H)
                for k, buf in enumerate(buffers(seg_grade(a, bb),
                                                seg_grade(bb, c))):
                    tolls[k] += min(D, H, buf)
    else:
        swings = [s for s in swing_list(prof["x"], hf) if s[2] > 0]
        for j in range(len(swings) - 1):
            d_dir, D, run_d = swings[j]
            u_dir, H, run_u = swings[j + 1]
            if d_dir != -1 or u_dir != 1:
                continue
            n_val += 1
            cap_sum += min(D, H)
            for k, buf in enumerate(buffers(D / run_d, H / run_u)):
                tolls[k] += min(D, H, buf)
    return {"n_valleys": n_val, "cap_m": cap_sum,
            **{f"toll_vb{k}": tolls[k] for k in range(len(VB_KMH))},
            "toll_vbm": tolls[-1]}


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
            vf = r["vf_kmh"] / 3.6
            vb_m, vb_src = measured_vb(pts, vf)
            if SMOOTH:
                prof = {"x": prof["x"],
                        "h": gaussian_smooth(prof["h"], ENGINE_DX, SMOOTH)}
            t = ride_tolls(prof, r["m_hat"], r["crr_hat"], r["cda_hat"],
                           vf, p_climb, vb_m)
            t.update({"vb_meas_kmh": vb_m * 3.6, "vb_src": vb_src})
            if SMOOTH:
                # F5's components leave the e52 cache under smoothing: compute
                # them here (two-point trick, exact by linearity in eps) and
                # check the interpolation against a fresh engine call.
                p = {"m": r["m_hat"], "Crr": r["crr_hat"], "CdA": r["cda_hat"],
                     "rho": RHO, "keff": KEFF, "wind": 0.0}
                opt = {"climbAeroMode": "zero", "climbThr": CLIMB_THR,
                       "descThr": DESC_THR, "climbPower": p_climb}
                a0 = approximate(prof, p, vf, 0.0, opt)
                a1 = approximate(prof, p, vf, 1.0, opt)
                t.update({"sm_roll": a0["roll"], "sm_aero": a0["aero"],
                          "sm_climb": a0["climb"], "sm_recov1": a1["recov"]})
                if len(SM_CHECK) < 50:
                    want = approximate(prof, p, vf, 0.37, opt)["E"]
                    got = (a0["roll"] + a0["aero"] + a0["climb"]
                           + 0.37 * a1["recov"])
                    SM_CHECK.append(abs(got - want) / abs(want) if want else 0.0)
        except Exception:
            continue
        out_rows.append({"group": group, "ride": label, **t})
    cols = (["group", "ride", "n_valleys", "cap_m", "vb_meas_kmh", "vb_src"]
            + [f"toll_vb{k}" for k in range(len(VB_KMH))] + ["toll_vbm"]
            + (["sm_roll", "sm_aero", "sm_climb", "sm_recov1"] if SMOOTH else []))
    with open(TOLLS_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"  wrote {os.path.basename(TOLLS_CSV)} ({len(out_rows)} rides)")
    if SMOOTH:
        worst = max(SM_CHECK) if SM_CHECK else float("inf")
        print(f"  sm-component two-point interpolation vs fresh engine on "
              f"{len(SM_CHECK)} rides: worst {worst:.3e} "
              f"{'GATE-OK' if worst < 1e-9 else 'GATE-FAIL'}")
        if not worst < 1e-9:
            raise SystemExit("smoothed components do not reproduce the engine")


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
        if t and ("toll_vbm" not in t or (SMOOTH and "sm_roll" not in t)):
            raise SystemExit(f"{os.path.basename(TOLLS_CSV)} predates this "
                             f"arm's columns — rerun with E63_REBUILD=1")
        if SMOOTH and not t:
            raise SystemExit(f"ride {r['ride']} missing from the smooth toll "
                             f"walk — F5 has no components for it; rebuild")
        beta_kj = r["m_hat"] * G / KEFF / 1000.0
        for k in range(len(VB_KMH)):
            m_toll = float(t[f"toll_vb{k}"]) if t else 0.0
            r[f"bt{k}"] = beta_kj * m_toll
        r["btm"] = beta_kj * float(t["toll_vbm"]) if t else 0.0
        r["vb_meas_kmh"] = float(t["vb_meas_kmh"]) if t else r["vf_kmh"]
        r["n_valleys"] = float(t["n_valleys"]) if t else 0.0
        if SMOOTH:
            for k in ("sm_roll", "sm_aero", "sm_climb", "sm_recov1"):
                r[k] = float(t[k])
        missing += 0 if t else 1
    if missing:
        print(f"  WARNING: {missing} cache rides missing from the toll walk "
              f"(tolled 0 — population unchanged)")
    return rows


# ----------------------------------------------------- stage 2: F5's algebra

def e_form5k(r: dict, eps: float, key: str) -> float:
    """F5-family energy in kJ: the base components (F3(tau_n)'s from the e52
    cache, or the smoothed-profile ones under E63_SMOOTH) with the valley toll
    (column `key`: bt<i> for a grid arm, btm for the measured cap) moved off
    both the climb charge and the descent credit."""
    k = "sm" if SMOOTH else f"f3t{TI_N}"
    bt = r[key] * 1000.0
    return (r[k + "_roll"] + r[k + "_aero"] + (r[k + "_climb"] - bt)
            + eps * (r[k + "_recov1"] + bt)) / 1000.0


def e_form5(r: dict, eps: float, vbi: int) -> float:
    return e_form5k(r, eps, f"bt{vbi}")


def usable5(r: dict, key: str) -> bool:
    """e52's fixed-population rule, per toll column (mirrors _usable per tau)."""
    return (e_form5k(r, EPS_BOUNDS[0], key) > 0
            and e_form5k(r, EPS_BOUNDS[1], key) > 0)


def cv_loss5(rows, eps, key) -> float:
    v = [abs(math.log(e / r["emp"])) if (e := e_form5k(r, eps, key)) > 0
         else float("inf") for r in rows if usable5(r, key)]
    return sum(v) / len(v) if v else float("inf")


def pct5(rows, eps, key) -> list[float]:
    return [100.0 * (e_form5k(r, eps, key) - r["emp"]) / r["emp"] for r in rows]


def fit_eps(rows, key) -> tuple[float, float]:
    """(eps, loss) minimising the CV loss at ONE toll column — e52's 5x201
    refinement. Precomputing (fixed, recov) changes nothing numerically; it
    only keeps 20 fold-fits affordable."""
    sub = [(e_form5k(r, 0.0, key), e_form5k(r, 1.0, key) - e_form5k(r, 0.0, key),
            r["emp"]) for r in rows if usable5(r, key)]
    if not sub:
        return 0.2, float("inf")

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
    return e_best, loss(e_best)


def fit5(rows) -> tuple[float, int]:
    """(eps, vb-index) over the whole grid — the exact mirror of F3's fit
    over the tau grid."""
    best = (float("inf"), 0.2, 0)
    for vbi in range(len(VB_KMH)):
        e, l = fit_eps(rows, f"bt{vbi}")
        if l < best[0]:
            best = (l, e, vbi)
    return best[1], best[2]


# Entry 64's family fitters, each returning (eps, toll-column)
def fit_f5(rows):
    e, vbi = fit5(rows)
    return e, f"bt{vbi}"


def fit_f5f(rows):
    return fit_eps(rows, f"bt{VB_INF_I}")[0], f"bt{VB_INF_I}"


def fit_f5m(rows):
    return fit_eps(rows, "btm")[0], "btm"


def aic5(rows, eps, key, npar=NPAR5) -> float:
    r = [abs(math.log(e / q["emp"])) if (e := e_form5k(q, eps, key)) > 0
         else float("inf") for q in rows if usable5(q, key)]
    n = len(r)
    if not n:
        return float("nan")
    b = sum(r) / n or 1e-12
    return 2 * npar - 2 * (-n * math.log(2 * b) - n)


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


def cv5(train, fit_fn=fit_f5) -> dict:
    """Fold CV for one F5-family member; fit_fn(rows) -> (eps, toll-column)."""
    scores = []
    for rep in range(4):                       # e52's N_REPEATS x K_FOLDS
        for tr, va in folds(train, 5, rep):
            e, key = fit_fn(tr)
            scores.append(cv_loss5(va, e, key))
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


# ---------------------------------------------------- Entry 64: diagnostics

def loro(rows) -> None:
    """Leave-one-rider-out contest, F3 vs F5f vs F5m — Entry 54's strictness:
    every free parameter fitted on the OTHER six riders' TRAIN-half rides, the
    held-out rider scored on their TEST-half rides (so no ride used here ever
    touched any selection). The absorption question: F3's fitted tau carries
    the calibration corpus's behaviour mix; a computed toll should travel."""
    train, test = split(rows)
    print(f"\n  Entry 64 LORO — fit on 6 riders' train halves, score the "
          f"7th's test half (seed {SEED} split, CIs seed {SEED64})")
    print(f"    {'recipient':<12} {'n':>4} {'F3':>6} {'F5f':>6} {'F5m':>6}"
          f"   {'F3 sgn':>7} {'F5f':>7} {'F5m':>7}   (med|D%| · signed)")
    diffs = {"F5f": [], "F5m": []}
    out_rows = []
    for g in GROUPS:
        tr = [r for r in train if r["group"] != g]
        te = [r for r in test if r["group"] == g]
        if not te:
            continue
        e3, c3, ti3 = fit(tr, "F3")
        ef, kf = fit_f5f(tr)
        em, km_ = fit_f5m(tr)
        p3 = pct(te, "F3", e3, c3, ti3)
        pf = pct5(te, ef, kf)
        pm = pct5(te, em, km_)
        diffs["F5f"].append([abs(a) - abs(b) for a, b in zip(pf, p3)])
        diffs["F5m"].append([abs(a) - abs(b) for a, b in zip(pm, p3)])
        row = {"group": g, "n": len(te),
               "f3_med_abs": med_of([abs(v) for v in p3]),
               "f5f_med_abs": med_of([abs(v) for v in pf]),
               "f5m_med_abs": med_of([abs(v) for v in pm]),
               "f3_med_signed": med_of(p3), "f5f_med_signed": med_of(pf),
               "f5m_med_signed": med_of(pm),
               "f3_tau": TAU_GRID[ti3], "f3_eps": e3,
               "f5f_eps": ef, "f5m_eps": em}
        out_rows.append(row)
        print(f"    {g:<12} {len(te):>4} {row['f3_med_abs']:>6.2f} "
              f"{row['f5f_med_abs']:>6.2f} {row['f5m_med_abs']:>6.2f}   "
              f"{row['f3_med_signed']:>7.2f} {row['f5f_med_signed']:>7.2f} "
              f"{row['f5m_med_signed']:>7.2f}")
    for tag in ("F5f", "F5m"):
        flat = [d for grp in diffs[tag] for d in grp]
        ci = boot_ci_strat(diffs[tag], SEED64 + (0 if tag == "F5f" else 1))
        win = sum(1 for d in flat if d < 0)
        los = sum(1 for d in flat if d > 0)
        print(f"    {tag} vs F3 per-ride |D%| difference: median "
              f"{med_of(flat):+.2f} pp [{ci[0]:+.2f}, {ci[1]:+.2f}], "
              f"{tag} closer on {win}/{win + los} "
              f"(sign p = {to_fixed(sign_p(win, los), 4)})")
    out = os.path.join(RESULTS, "e63_loro" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"  wrote {os.path.basename(out)}")


def taupred(rows) -> None:
    """Entry 39's prediction, sharpened by Entry 63's ledger matching:
    tau* ~= tau_noise + h_KE / (2 (1 - eps)), with h_KE now MEASURED per rider
    ((vb_meas^2 - vf^2)/2g, ride medians). Per-group tau* is fitted on that
    group's TRAIN-half rides alone (the test half stays unseen). Diagnostic:
    no gate, no test scoring."""
    train, _ = split(rows)
    print(f"\n  Entry 64 tau* prediction — per-rider fitted tau vs "
          f"tau_n + h_KE/(2(1-eps)), h_KE from measured v_b")
    print(f"    {'group':<12} {'n':>4} {'tau*':>5} {'eps':>7} {'vb_meas':>8} "
          f"{'vf':>6} {'h_KE':>6} {'tau_pred':>8}")
    out_rows = []
    for g in GROUPS:
        sub = [r for r in train if r["group"] == g]
        if len(sub) < 5:
            continue
        e3, _c3, ti3 = fit(sub, "F3")
        vb_med = med_of([r["vb_meas_kmh"] for r in sub])
        vf_med = med_of([r["vf_kmh"] for r in sub])
        hke = med_of([max(0.0, ((r["vb_meas_kmh"] / 3.6) ** 2
                                - (r["vf_kmh"] / 3.6) ** 2)) / (2 * G)
                      for r in sub])
        tpred = TAU_N + hke / (2 * (1 - e3)) if e3 < 1 else float("nan")
        out_rows.append({"group": g, "n": len(sub), "tau_star": TAU_GRID[ti3],
                         "eps": e3, "vb_meas_kmh": vb_med, "vf_kmh": vf_med,
                         "h_ke_m": hke, "tau_pred": tpred})
        print(f"    {g:<12} {len(sub):>4} {TAU_GRID[ti3]:>5.1f} {e3:>7.4f} "
              f"{vb_med:>8.1f} {vf_med:>6.1f} {hke:>6.2f} {tpred:>8.2f}")
    ts = [r["tau_star"] for r in out_rows]
    tp = [r["tau_pred"] for r in out_rows]

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return rk
    ra, rb = ranks(ts), ranks(tp)
    n = len(ts)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((a - ma) * (b - mb) for a, b in zip(ra, rb))
    den = math.sqrt(sum((a - ma) ** 2 for a in ra)
                    * sum((b - mb) ** 2 for b in rb))
    rho = num / den if den else float("nan")
    print(f"    Spearman rho(tau*, tau_pred) = {rho:+.3f} on {n} groups "
          f"(diagnostic; small n, tau* is grid-discrete)")
    out = os.path.join(RESULTS, "e63_taupred" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"  wrote {os.path.basename(out)}")


def main() -> None:
    rows = load()
    print(f"Entry 63 — F5 (KE-buffer valley toll) vs F3/F4 on {len(rows)} rides"
          + ("   [SMOKE]" if SMOKE else ""))
    if os.path.exists(TOLLS_CSV) and not os.environ.get("E63_REBUILD"):
        print(f"  reusing {os.path.basename(TOLLS_CSV)} (E63_REBUILD=1 to rewalk)")
    else:
        build_tolls(rows)
    rows = join_tolls(rows)

    if SMOOTH:
        # under smoothing the vb = 0 arm is "F2 on the smoothed profile" — a
        # new estimator, not any cached form; its engine check ran at build
        # time (sm-component interpolation vs fresh approximate() calls).
        print(f"\n  gate: sm components engine-checked at build "
              f"(Gaussian sigma = {SMOOTH:g} m); F5(vb=0) here IS smoothed-F2")
    else:
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
    vbm = sorted(r["vb_meas_kmh"] for r in rows)
    print(f"  measured v_b median {q(vbm, .5):.1f} km/h "
          f"(5th {q(vbm, .05):.1f}, 95th {q(vbm, .95):.1f})")

    if LORO:
        loro(rows)
        return
    if TAUPRED:
        taupred(rows)
        return

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
    cv["F5"] = cv5(train, fit_f5)
    cv["F5f"] = cv5(train, fit_f5f)            # Entry 64: frozen never-brake
    cv["F5m"] = cv5(train, fit_f5m)            # Entry 64: measured per-ride vb
    cv["F3tn"] = cv_f3_fixed(train, TI_N)      # the shared-noise-floor arm
    FAMILY = ("F3", "F4", "F5", "F5f", "F5m")
    for f in FAMILY:
        print(f"    {f:<4} CV {cv[f]['cv']:.5f} +/- {cv[f]['se']:.5f} "
              f"({cv[f]['n_scores']} fold scores)")
    print(f"    [decomposition: F3(tau={TAU_N} fixed) CV {cv['F3tn']['cv']:.5f} "
          f"+/- {cv['F3tn']['se']:.5f} — F5's gain over this is the toll's "
          f"contribution beyond the shared filter]")
    if SMOOTH:
        cv["F5s0"] = cv5(train, lambda rows: (fit_eps(rows, "bt0")[0], "bt0"))
        print(f"    [smoothing alone (F2 on the sigma={SMOOTH:g} m profile, "
              f"toll off): CV {cv['F5s0']['cv']:.5f} +/- {cv['F5s0']['se']:.5f}"
              f" — the F5 rows' gain over THIS is the toll's contribution "
              f"beyond the smoother]")

    # ---- A.5 over the family (F1/F2 stay in the table as e52 left them)
    fits = {}
    for f in ("F3", "F4"):
        e, c, ti = fit(train, f)
        fits[f] = {"eps": e, "c": c, "ti": ti,
                   "aic": aic(train, f, e, c, ti)}
    for f, fit_fn, npar_f in (("F5", fit_f5, 2), ("F5f", fit_f5f, 1),
                              ("F5m", fit_f5m, 1)):
        e5, key5 = fit_fn(train)
        fits[f] = {"eps": e5, "key": key5, "aic": aic5(train, e5, key5, npar_f)}
    npar = {"F3": 2, "F4": 2, "F5": 2, "F5f": 1, "F5m": 1}
    best = min(FAMILY, key=lambda f: cv[f]["cv"])
    thr = cv[best]["cv"] + cv[best]["se"]
    tied = [f for f in FAMILY if cv[f]["cv"] <= thr]
    winner = min(tied, key=lambda f: (npar[f], cv[f]["cv"]))
    aic_best = min(FAMILY, key=lambda f: fits[f]["aic"])

    def vb_col(f):
        if f == "F5":
            return f"{VB_KMH[int(fits[f]['key'][2:])]:g}"
        return {"F5f": "inf", "F5m": "meas"}.get(f, "")

    print(f"\n  A.5  {'form':<4} {'k':>2} {'CV':>9} {'1-SE':>5} {'AIC':>11} "
          f"{'eps':>8} {'tau':>5} {'c':>6} {'vb':>6}")
    for f in FAMILY:
        tau_s = str(TAU_GRID[fits[f]["ti"]]) if f == "F3" else "—"
        c_s = "{:.2f}".format(fits[f]["c"]) if f == "F4" else "—"
        print(f"       {f:<4} {npar[f]:>2} {cv[f]['cv']:>9.5f} "
              f"{'in' if cv[f]['cv'] <= thr else 'out':>5} "
              f"{fits[f]['aic']:>11.1f} {fits[f]['eps']:>8.4f} "
              f"{tau_s:>5} {c_s:>6} {vb_col(f):>6}")
    print(f"       CV best {best} · within 1 SE {tied} · AIC best {aic_best}"
          f" · WINNER {winner} (1-SE toward fewer parameters)")

    # ---- A.8: the held-out half, scored once, family + comparator
    print(f"\n  A.8  D_test scored ONCE (n = {len(test)})")
    print(f"    {'estimator':<26} {'med|D%|':>6} {'[95% CI]':<19}  "
          f"{'signed':>6} [95% CI]")
    res = {}
    for f in ("F3", "F4"):
        res[f] = score(test, f + (" (WINNER)" if f == winner else ""),
                       lambda s, f=f: pct(s, f, fits[f]["eps"], fits[f]["c"],
                                          fits[f]["ti"]))
    for f in ("F5", "F5f", "F5m"):
        res[f] = score(test, f + (" (WINNER)" if f == winner else ""),
                       lambda s, f=f: pct5(s, fits[f]["eps"], fits[f]["key"]))
    from bicycling_energy_model import is_finite
    ce = [100.0 * (r["canon_kj"] - r["emp"]) / r["emp"]
          for r in test if is_finite(r["canon_kj"])]
    if ce:
        print(f"    {'F_base (comparator)':<26} "
              f"{to_fixed(med_of([abs(v) for v in ce]), 2):>6}"
              f"{'':<20}  {to_fixed(med_of(ce), 2):>6}")
    wf = (pct(test, winner, fits[winner]["eps"], fits[winner]["c"],
              fits[winner]["ti"]) if winner in ("F3", "F4")
          else pct5(test, fits[winner]["eps"], fits[winner]["key"]))
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
        for f in FAMILY:
            fh.write(f"{f},{npar[f]},{cv[f]['cv']:.6f},{cv[f]['se']:.6f},"
                     f"{fits[f]['aic']:.3f},{to_fixed(fits[f]['eps'], 4)},"
                     f"{to_fixed(fits[f]['c'], 4) if f == 'F4' else ''},"
                     f"{TAU_GRID[fits[f]['ti']] if f == 'F3' else ''},"
                     f"{vb_col(f)},"
                     f"{to_fixed(res[f]['med_abs'], 4)},"
                     f"{to_fixed(res[f]['med_signed'], 4)},"
                     f"{1 if f == winner else 0}\n")
        # the diagnostic arm: CV only, deliberately no test columns
        fh.write(f"F3tn,1,{cv['F3tn']['cv']:.6f},{cv['F3tn']['se']:.6f},,"
                 f"{to_fixed(cv['F3tn']['eps'], 4)},,{TAU_N},,,,0\n")
    print(f"\nwrote {os.path.basename(out)}")


if __name__ == "__main__":
    main()
