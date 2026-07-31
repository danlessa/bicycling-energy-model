#!/usr/bin/env python3
"""Entry 53 — joint linear inversion of (m, C_rr, CdA), against the cascade.

Multiplying the force balance by v makes it LINEAR in the parameters:

    W_block = m*(d(v^2/2) + g*dh) + (m*C_rr)*(g*L) + CdA*(rho/2 * integral (v+w)^2 ds)

integrated over BLOCKS of ~200 m rather than per sample. The per-sample form is
algebraically identical but useless in practice: dh/ds at 10 m spacing is
dominated by barometric jitter (+/-0.5 m over 10 m is a spurious grade of
0.05), and a noisy regressor biases its own coefficient toward zero --
regression dilution. The first version of this script returned m = 9.4 kg and
a NEGATIVE CdA for exactly that reason. Blocks keep the linearity while
letting only dh over the whole block enter, which is what the cascade achieves
by restricting itself to sustained segments -- the difference is that blocks
cover the WHOLE ride instead of the quasi-steady part of it.

so one regression returns all three jointly, with C_rr = theta2/theta1. Same
idea as Chung's virtual-elevation method, solved directly instead of by
iteration.

RESULT: IT FAILS ITS OWN VALIDATION, and the failure is informative. On the 24
rides the cascade genuinely inverts, the linear fit returns m = 63 against 98,
C_rr = 0.038 against 0.009, CdA = 0.091 against 0.325. Median condition number
is ~328.

The diagnosis is IDENTIFIABILITY, not implementation. Separating C_rr (which
scales with v) from CdA (which scales with v^3) needs speed VARIATION within
the ride; at roughly steady speed the two columns are nearly parallel and no
estimator can split them. With fixed-length blocks X2 = g*L is additionally
near-constant, so it behaves as an intercept and absorbs whatever else is
unmodelled -- drivetrain loss, wind, power-meter bias -- which is why C_rr
inflates while m and CdA shrink to compensate.

So the joint fit removes the cascade's fallback CODE PATH but not the
INFORMATION DEFICIT the fallbacks exist to cover. The cascade's 77% prior rate
is not a defect of sequencing; it is an honest signal that three constants are
not identified from a single ride. Any real improvement has to add information
rather than rearrange the algebra -- pooling m across a rider (it is
near-constant within one: D6-user_1's IQR is 99.9-99.9 kg), fitting C_rr at
rider or corpus level, and leaving only CdA per ride.

WHAT IT IS MEANT TO FIX, measured on this repo's own data in Entry 52:
  - 77% of rides carry the C_rr prior 0.008 and 26% the CdA rail 0.400; both
    are genuinely inverted on only 15%. The cascade needs each stage separately
    identifiable on its own segment subset, and falls back when it is not.
  - Sequential estimation propagates error: m_hat's error contaminates C_rr,
    which contaminates CdA. The order is load-bearing in invert_physics.
  - The cascade fits on SUSTAINED climbs and flats -- quasi-steady by
    construction -- so transients are excluded from the fit and then met at
    simulation time. Entry 52 traced F_base's -4% Sao Paulo bias to exactly
    that. Here `a*v` is a regressor, so accelerations are fitted, not discarded.

VALIDATION LOGIC. On the subset where the cascade genuinely inverts all three
(no prior, no rail) it is well conditioned and trustworthy, so the linear fit
must AGREE there. Agreement there plus no rails elsewhere is the whole claim.
Disagreement there means the linear fit is wrong, not the cascade.

Run: python3 src/harness/e53_linear_invert.py    (E53_N=<rides>)
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

import numpy as np                       # documented deviation, as in e50

from bicycling_energy_model import build_profile, is_finite, resample_profile
from bicycling_energy_model.engines import G

from e44_scurve import corpus_rides
from e52_build import ANCHOR_KEY, GROUPS
from perride_invert import (CLIMB_THR, DESC_THR, ENGINE_DX, KEFF, RHO,
                            find_segments, invert_physics, seg_integrals)

N_RIDES = int(os.environ.get("E53_N", "250"))
V_MIN = 2.0            # m/s — below this the balance is dominated by noise
BLOCK_M = 200.0        # work-balance block length; see design() on dilution
BRAKE_EXCESS = 0.25    # block work deficit vs coasting => brakes assumed on


def design(pts, wind=0.0, block=BLOCK_M):
    """(X, y) over ~`block`-metre work-balance blocks — the dilution-safe form.

    Per block: W = m*(dKE/m-normalised + g*dh) + (m*Crr)*(g*L) + CdA*(rho/2*I2),
    with I2 = integral of (v+w)^2 ds. Only dh over the whole block enters, so
    altitude noise contributes once per block rather than once per sample."""
    X, y, meta = [], [], []
    i0, n = 0, len(pts)
    while i0 < n - 1:
        i1 = i0
        while i1 < n - 1 and pts[i1]["x"] - pts[i0]["x"] < block:
            i1 += 1
        if i1 <= i0:
            break
        a_, b_ = pts[i0], pts[i1]
        L = b_["x"] - a_["x"]
        dt = (b_.get("t") or 0) - (a_.get("t") or 0)
        if L < block * 0.5 or not dt or dt <= 0:
            i0 = i1
            continue
        # integrals inside the block
        W = 0.0
        I2 = 0.0
        ok = True
        vs = []
        for j in range(i0 + 1, i1 + 1):
            p0, p1 = pts[j - 1], pts[j]
            ddt = (p1.get("t") or 0) - (p0.get("t") or 0)
            dds = p1["x"] - p0["x"]
            if not ddt or ddt <= 0 or dds < 0:
                continue
            pw = p1.get("power")
            if pw is None or not is_finite(pw) or pw < 0:
                ok = False
                break
            v = dds / ddt
            vs.append(v)
            W += KEFF * pw * ddt
            I2 += (v + wind) ** 2 * dds
        if not ok or not vs or len(vs) < 3:
            i0 = i1
            continue
        vbar = sum(vs) / len(vs)
        if vbar < V_MIN:
            i0 = i1
            continue
        v_in = vs[0]
        v_out = vs[-1]
        dh = (b_.get("alt") or 0) - (a_.get("alt") or 0)
        dke = 0.5 * (v_out * v_out - v_in * v_in)          # per unit mass
        X.append([dke + G * dh, G * L, 0.5 * RHO * I2])
        y.append(W)
        meta.append((vbar, dh / L if L else 0.0, L))
        i0 = i1
    return np.asarray(X, float), np.asarray(y, float), meta


def drop_braking(X, y, meta, theta):
    """Blocks the balance over-predicts on a DESCENT: brake work is real work
    the rider did not do, and the model has no term for it. Restricted to
    descents so it cannot quietly trim ordinary residuals."""
    pred = X @ theta
    keep = np.ones(len(y), bool)
    scale = np.median(np.abs(y)) or 1.0
    for i, (vbar, grade, L) in enumerate(meta):
        if grade < DESC_THR and (pred[i] - y[i]) > BRAKE_EXCESS * scale:
            keep[i] = False
    return keep


def irls(X, y, iters=12, huber=1.345):
    """Huber-robust fit. Residuals here are heavy-tailed (dropouts, brake
    events, GPS altitude noise), so OLS would chase them."""
    w = np.ones(len(y))
    theta = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(iters):
        r = y - X @ theta
        s = 1.4826 * np.median(np.abs(r - np.median(r))) or 1.0
        u = np.abs(r) / s
        w = np.where(u <= huber, 1.0, huber / np.maximum(u, 1e-9))
        Xw = X * w[:, None]
        theta, *_ = np.linalg.lstsq(Xw, y * w, rcond=None)
    return theta


def fit_ride(pts):
    X, y, meta = design(pts)
    if len(y) < 200:
        return None
    theta = irls(X, y)
    keep = drop_braking(X, y, meta, theta)
    if keep.sum() >= 200:
        theta = irls(X[keep], y[keep])
    m, mcrr, cda = theta
    if not (is_finite(m) and m > 0):
        return None
    cond = float(np.linalg.cond(X[keep] if keep.sum() >= 200 else X))
    return {"m": float(m), "crr": float(mcrr / m), "cda": float(cda),
            "cond": cond, "n": int(keep.sum()), "drop": int((~keep).sum())}


def main() -> None:
    print("Entry 53 — joint linear inversion vs the sequential cascade\n")
    rows = []
    seen = 0
    for group, pts, mass in corpus_rides():
        if group not in GROUPS:
            continue
        seen += 1
        if seen > N_RIDES:
            break
        try:
            lin = fit_ride(pts)
            if lin is None:
                continue
            phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
            prof = resample_profile(phys, ENGINE_DX)
            cr, fl = find_segments(prof)
            wbc = [s for s in (seg_integrals(pts, c, 0.0) for c in cr) if s and s["ok"]]
            wbf = [s for s in (seg_integrals(pts, f, 0.0) for f in fl) if s and s["ok"]]
            cas = invert_physics(prof, wbc, wbf, ANCHOR_KEY.get(group), mass)
            if cas is None:
                continue
            rows.append({"g": group, "lin": lin, "cas": cas})
        except Exception:
            continue

    print(f"  {len(rows)} rides fitted by both methods\n")
    if not rows:
        return

    def med(v):
        v = sorted(v)
        return v[len(v) // 2] if v else float("nan")

    # the well-conditioned subset: the cascade genuinely inverted all three
    good = [r for r in rows
            if abs(r["cas"]["crr_hat"] - 0.008) > 1e-9
            and abs(r["cas"]["cda_hat"] - 0.400) > 1e-9]
    print(f"  cascade fell back on Crr: "
          f"{sum(1 for r in rows if abs(r['cas']['crr_hat'] - 0.008) < 1e-9)}/{len(rows)}")
    print(f"  cascade railed CdA       : "
          f"{sum(1 for r in rows if abs(r['cas']['cda_hat'] - 0.400) < 1e-9)}/{len(rows)}")
    print(f"  linear fit fell back     : 0/{len(rows)}   (it has no fallback path)")

    print(f"\n  VALIDATION on the {len(good)} rides the cascade genuinely inverted:")
    if good:
        for k, ck in (("m", "m_hat"), ("crr", "crr_hat"), ("cda", "cda_hat")):
            l = [r["lin"][k] for r in good]
            c = [r["cas"][ck] for r in good]
            rel = [100 * (a - b) / b for a, b in zip(l, c) if b]
            print(f"    {k:<4} linear {med(l):>9.4g}   cascade {med(c):>9.4g}"
                  f"   median rel diff {med(rel):>+7.1f}%")

    print(f"\n  FULL sample ({len(rows)} rides), what each method returns:")
    for k, ck in (("m", "m_hat"), ("crr", "crr_hat"), ("cda", "cda_hat")):
        l = sorted(r["lin"][k] for r in rows)
        c = sorted(r["cas"][ck] for r in rows)
        q = lambda v, p: v[min(len(v) - 1, int(p * (len(v) - 1)))]
        print(f"    {k:<4} linear  {q(l,.05):>9.4g} {q(l,.5):>9.4g} {q(l,.95):>9.4g}"
              f"    cascade  {q(c,.05):>9.4g} {q(c,.5):>9.4g} {q(c,.95):>9.4g}")

    cond = sorted(r["lin"]["cond"] for r in rows)
    print(f"\n  conditioning of the linear system: median {med(cond):.1f}, "
          f"95th {cond[int(.95 * (len(cond) - 1))]:.1f}")
    print(f"  braking points dropped: median "
          f"{med([100 * r['lin']['drop'] / max(1, r['lin']['drop'] + r['lin']['n']) for r in rows]):.1f}%")


if __name__ == "__main__":
    main()
