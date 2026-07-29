#!/usr/bin/env python3
"""Entry 44 — the S-curve reopened: pin the magnitude, contest speed against slope.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 44) before any fit. Tests the
reformulation of the coasting deficit that follows from Appendix A's ledger
identity, rewritten as a ratio of two powers:

    delta = k_eff * P_desc / (m * g * s * v)          [legs / gravity]
          = occ(.) * I(.) * k_eff / (m * g * s * v)

  H-M   I = P_flat, independent of grade (zero free parameters).
  H-P   occ is a decreasing sigmoid with a UNIVERSAL width and a rider-specific
        midpoint.
  H-P2  the governing variable is SPEED, not slope (cadence runs out; slope is
        only a correlated proxy).

Five registered predictions P1-P5; see the journal entry. P5 is the one that can
sink the rest: if most non-pedalling descent time is braking rather than
freewheeling, the sigmoid is not a pedalling choice at all.

Everything is deterministic: fits are grid searches, the split-half is by
chronological ride index (odd/even), no RNG anywhere.

Output: data/results/e44_scurve_cells.csv   (per rider x bin aggregates)
        data/results/e44_scurve_fits.csv    (per rider fitted sigmoids + transfer)
Run: python3 src/harness/e44_scurve.py       (E44_SMOKE=1 for a subset)
"""

from __future__ import annotations

import json
import math
import os
import sys
from typing import Iterator, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import climb_balance, is_finite, load_pts
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

from skc_compare import FROZEN, M0, MIN_SUSTAINED_DH, RESULTS, med_of, ride_files
from skc_invert import iter_brazil

DATA = os.path.join(REPO, "data", "inputs", "activities")
SMOKE = bool(os.environ.get("E44_SMOKE"))

# --- registered protocol constants (Entry 44; do not tune) ---
CELL = 30.0
POW_ON = 10.0                     # pedalling threshold, W
VSTOP = 0.5 / 3.6                 # moving gate, m/s
BRAKE_DECEL, BRAKE_VMIN = 1.5, 3.0
GRADE_EDGES = (0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 9.9)
SPEED_EDGES = (10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 999.0)   # km/h
KEFF = FROZEN["keff"]
ANCHOR = {"D3": 74.5, "D4": 101.9, "D5": 74.7, "D2": 78.0}

# grid-search ranges, fixed in the registration
S50_GRID = [i * 0.001 for i in range(0, 201)]          # 0-20 %, step 0.1 pp
SW_GRID = [0.002 + i * 0.001 for i in range(0, 79)]    # 0.2-8 %, step 0.1 pp
V50_GRID = [i * 0.5 for i in range(0, 141)]            # 0-70 km/h, step 0.5
VW_GRID = [1.0 + i * 0.5 for i in range(0, 49)]        # 1-25 km/h, step 0.5


def bin_of(x: float, edges: Sequence[float]) -> int:
    for i, e in enumerate(edges):
        if x < e:
            return i
    return len(edges) - 1


def cells_of_ride(pts: Sequence[dict]) -> list[dict] | None:
    """Per 30 m cell: grade, time-weighted speed, pedalling time, energy, braking."""
    if len(pts) < 2:
        return None
    x0 = pts[0]["x"]
    nc = math.floor((pts[-1]["x"] - x0) / CELL)
    if nc < 2:
        return None
    j = 0

    def alt_at(d: float) -> float:
        nonlocal j
        while j < len(pts) - 2 and pts[j + 1]["x"] < d:
            j += 1
        seg = pts[j + 1]["x"] - pts[j]["x"]
        f = (d - pts[j]["x"]) / seg if seg > 1e-9 else 0.0
        return pts[j]["alt"] * (1 - f) + pts[j + 1]["alt"] * f

    ca = [alt_at(x0 + k * CELL) for k in range(nc + 1)]
    out = [{"s": (ca[k + 1] - ca[k]) / CELL, "t": 0.0, "t_pow": 0.0,
            "t_brake": 0.0, "e": 0.0, "vs": 0.0} for k in range(nc)]
    prev_v = None
    for r in pts:
        k = math.floor((r["x"] - x0) / CELL)
        v, w, p = r.get("v"), (r.get("dt") or 1.0), r.get("power")
        if v is not None and prev_v is not None and w > 0:
            if prev_v > BRAKE_VMIN and (prev_v - v) / w > BRAKE_DECEL and 0 <= k < nc:
                out[k]["t_brake"] += w
        prev_v = v
        if k < 0 or k >= nc or v is None or v < VSTOP:
            continue
        c = out[k]
        c["t"] += w
        c["vs"] += v * w
        if p is not None:
            c["e"] += p * w
            if p >= POW_ON:
                c["t_pow"] += w
    for c in out:
        c["v"] = c["vs"] / c["t"] if c["t"] > 0 else float("nan")
    return out


def flat_power(cells: Sequence[dict]) -> tuple[float, float]:
    """(P_flat, I_flat) on |s| < 1% cells.

    P_flat is the flat-regime MEAN power — what the model already uses to set
    v_f, and what H-M names literally. I_flat is the mean power WHILE PEDALLING
    on the flat. The distinction matters and the first run got it wrong: the
    descent magnitude I is a while-pedalling quantity, so comparing it against a
    mean that includes flat coasting conflates magnitude with occupancy and
    inflates the ratio for exactly the riders who coast most (it put D5 at 1.3
    when his descent pedalling is the study's lowest). Both are reported; the
    like-for-like I/I_flat is the honest test of H-M, and P_flat is kept because
    it is what the registration literally said."""
    e = t = tp = ep = 0.0
    for c in cells:
        if abs(c["s"]) < 0.01:
            e += c["e"]
            t += c["t"]
            tp += c["t_pow"]
            ep += c["e"] if c["t_pow"] > 0 else 0.0
    p_flat = e / t if t > 0 else float("nan")
    # energy while pedalling is not stored per cell; approximate the flat
    # while-pedalling power as total flat energy over flat pedalling time, which
    # is exact when coasting contributes no energy (power < POW_ON adds < 10 W).
    i_flat = e / tp if tp > 0 else float("nan")
    return p_flat, i_flat


def sigmoid(x: float, x50: float, w: float) -> float:
    z = (x - x50) / w
    if z > 60:
        return 0.0
    if z < -60:
        return 1.0
    return 1.0 / (1.0 + math.exp(z))


def fit_sigmoid(pts: Sequence[tuple[float, float, float]],
                x50_grid: Sequence[float],
                w_grid: Sequence[float]) -> tuple[float, float, float]:
    """(x, observed occupancy, weight) -> (x50, w, weighted RMSE). Grid search."""
    best = (float("nan"), float("nan"), float("inf"))
    if not pts:
        return best
    for x50 in x50_grid:
        for w in w_grid:
            se = tw = 0.0
            for x, o, wt in pts:
                d = sigmoid(x, x50, w) - o
                se += wt * d * d
                tw += wt
            if tw <= 0:
                continue
            rmse = math.sqrt(se / tw)
            if rmse < best[2]:
                best = (x50, w, rmse)
    return best


def rmse_of(pts: Sequence[tuple[float, float, float]], x50: float, w: float) -> float:
    se = tw = 0.0
    for x, o, wt in pts:
        d = sigmoid(x, x50, w) - o
        se += wt * d * d
        tw += wt
    return math.sqrt(se / tw) if tw > 0 else float("nan")


def corpus_rides() -> Iterator[tuple[str, Sequence[dict], float]]:
    """(group, pts, mass) over every corpus, deterministic order."""
    p0 = {**FROZEN, "m": M0}
    mh: dict[str, list[float]] = {}
    d6: list[tuple[str, str]] = []
    for rider, path in ride_files():
        try:
            pts = load_pts(path)
        except Exception:
            continue
        if len(pts) < 10:
            continue
        npow = sum(1 for q in pts if q.get("power") is not None)
        nalt = sum(1 for q in pts if q.get("alt") is not None)
        if npow / len(pts) <= 0.5 or nalt / len(pts) < 0.99 or pts[-1]["x"] / 1000 < 20:
            continue
        d6.append((rider, path))
        cb = climb_balance(pts, p0)
        if cb["n"] > 0 and cb["dh"] >= MIN_SUSTAINED_DH and (cb["egrav"] + cb["eroll"]) > 0:
            m = M0 * (cb["emeas"] - cb["eaero"]) / (cb["egrav"] + cb["eroll"])
            if is_finite(m) and 40.0 <= m <= 200.0:
                mh.setdefault(rider, []).append(m)
    anchor6 = {r: med_of(v) for r, v in mh.items() if v}
    for rider, path in d6:
        try:
            yield "D6-" + rider, load_pts(path), anchor6.get(rider, M0)
        except Exception:
            continue
    inputs = {e["label"]: e for e in
              json.load(open(os.path.join(DATA, "model_inputs.json")))}
    for corpus, lab in (("longoes", "D1"), ("ppaz", "D3"), ("jaam", "D4"),
                        ("danlessa", "D5"), ("censo", "D2")):
        try:
            for pts, name in iter_brazil(corpus):
                m = (inputs[name]["m"] if lab == "D1" and name in inputs
                     else ANCHOR.get(lab, M0))
                yield lab, pts, m
        except Exception as exc:
            print(f"  ({corpus}: {type(exc).__name__} — skipped)")


def main() -> None:
    print("Entry 44 — S-curve reopened" + ("  [E44_SMOKE]" if SMOKE else ""))
    ng, nv = len(GRADE_EDGES), len(SPEED_EDGES)

    # per group: bin aggregates, split by half (0 = fit, 1 = held out)
    agg: dict[str, dict] = {}
    ride_rows: list[dict] = []
    seen: dict[str, int] = {}
    for group, pts, mass in corpus_rides():
        idx = seen.get(group, 0)
        seen[group] = idx + 1
        if SMOKE and idx >= 25:
            continue
        half = idx % 2
        cells = cells_of_ride(pts)
        if not cells:
            continue
        pf, iflat = flat_power(cells)
        a = agg.setdefault(group, {
            "gt": [[0.0] * ng for _ in range(2)], "gp": [[0.0] * ng for _ in range(2)],
            "ge": [[0.0] * ng for _ in range(2)], "gb": [[0.0] * ng for _ in range(2)],
            "gsum": [[0.0] * ng for _ in range(2)],
            "vt": [[0.0] * nv for _ in range(2)], "vp": [[0.0] * nv for _ in range(2)],
            "vsum": [[0.0] * nv for _ in range(2)], "n": 0})
        a["n"] += 1
        r_t = r_p = 0.0
        rb = [0.0] * ng          # descent time per grade bin, this ride
        rh = [0.0] * ng          # drop (m) per grade bin
        re_ = [0.0] * ng         # measured descent leg energy (J) per grade bin
        for c in cells:
            if c["s"] >= -0.005 or c["t"] <= 0 or not is_finite(c["v"]):
                continue
            gi = bin_of(-c["s"], GRADE_EDGES)
            vi = bin_of(c["v"] * 3.6, SPEED_EDGES)
            a["gt"][half][gi] += c["t"]
            a["gp"][half][gi] += c["t_pow"]
            a["ge"][half][gi] += c["e"]
            a["gb"][half][gi] += c["t_brake"]
            a["gsum"][half][gi] += (-c["s"]) * c["t"]
            a["vt"][half][vi] += c["t"]
            a["vp"][half][vi] += c["t_pow"]
            a["vsum"][half][vi] += c["v"] * 3.6 * c["t"]
            rb[gi] += c["t"]
            rh[gi] += (-c["s"]) * CELL
            re_[gi] += c["e"]
            if -c["s"] >= 0.03:
                r_t += c["t"]
                r_p += c["t_pow"]
        if r_t > 0 and is_finite(pf) and pf > 0:
            ride_rows.append({"group": group, "half": half, "km": pts[-1]["x"] / 1000,
                              "occ": r_p / r_t, "p_flat": pf, "i_flat": iflat,
                              "m": mass, "tbin": rb, "hbin": rh, "ebin": re_})

    groups = sorted(agg, key=lambda g: (not g.startswith("D6"), g))

    # ---------------- P5 first: is it braking or freewheeling? ----------------
    print("\nP5 — braking share of NON-PEDALLING descent time, 3-8% band "
          "(registered: must be under 30%)")
    p5_fail = []
    for g in groups:
        a = agg[g]
        t = sum(a["gt"][h][i] for h in (0, 1) for i in (3, 4, 5, 6))
        p = sum(a["gp"][h][i] for h in (0, 1) for i in (3, 4, 5, 6))
        b = sum(a["gb"][h][i] for h in (0, 1) for i in (3, 4, 5, 6))
        idle = t - p
        share = b / idle if idle > 0 else float("nan")
        flag = "" if not is_finite(share) or share < 0.30 else "   <-- OVER 30%"
        if is_finite(share) and share >= 0.30:
            p5_fail.append(g)
        print(f"  {g.ljust(12)} non-pedalling {to_fixed(idle / 60, 0).rjust(6)} min, "
              f"braking {to_fixed(share, 3)}{flag}")

    # ---------------- P1: is the magnitude flat in grade? ----------------
    print("\nP1 (H-M) — I / I_flat by grade band, like-for-like while-pedalling "
          "(registered band 0.85-1.15 up to 10%)")
    pflat_of = {g: med_of([r["p_flat"] for r in ride_rows if r["group"] == g])
                for g in groups}
    iflat_of = {g: med_of([r["i_flat"] for r in ride_rows if r["group"] == g])
                for g in groups}
    labels = ["<1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-8", "8-10", "10-15", ">15"]
    print("group".ljust(12) + "".join(l.rjust(7) for l in labels))
    for g in groups:
        a = agg[g]
        cells = []
        for i in range(1, ng):
            t = sum(a["gt"][h][i] for h in (0, 1))
            p = sum(a["gp"][h][i] for h in (0, 1))
            e = sum(a["ge"][h][i] for h in (0, 1))
            inten = (e / p) if p > 0 else float("nan")   # W while pedalling
            r = inten / iflat_of[g] if iflat_of[g] and is_finite(inten) else float("nan")
            cells.append(to_fixed(r, 2).rjust(7) if is_finite(r) and t > 60 else "".rjust(7))
        print(g.ljust(12) + "".join(cells))

    # ---------------- P2: slope vs speed ----------------
    print("\nP2 (H-P2) — sigmoid fits: occupancy vs |slope| and vs speed")
    fits: list[dict] = []
    for g in groups:
        a = agg[g]
        gpts = [[], []]
        vpts = [[], []]
        for h in (0, 1):
            for i in range(ng):
                t = a["gt"][h][i]
                if t > 60:
                    gpts[h].append((a["gsum"][h][i] / t, a["gp"][h][i] / t, t))
            for i in range(nv):
                t = a["vt"][h][i]
                if t > 60:
                    vpts[h].append((a["vsum"][h][i] / t, a["vp"][h][i] / t, t))
        s50, sw, s_in = fit_sigmoid(gpts[0], S50_GRID, SW_GRID)
        v50, vw, v_in = fit_sigmoid(vpts[0], V50_GRID, VW_GRID)
        s_out = rmse_of(gpts[1], s50, sw) if gpts[1] and is_finite(s50) else float("nan")
        v_out = rmse_of(vpts[1], v50, vw) if vpts[1] and is_finite(v50) else float("nan")
        fits.append({"group": g, "n": a["n"], "s50_pct": s50 * 100, "s_width_pct": sw * 100,
                     "s_rmse_in": s_in, "s_rmse_out": s_out,
                     "v50_kmh": v50, "v_width_kmh": vw,
                     "v_rmse_in": v_in, "v_rmse_out": v_out})
    print("group".ljust(12) + "n".rjust(5) + "s50%".rjust(8) + "w%".rjust(7)
          + "RMSEout".rjust(9) + " | " + "v50".rjust(7) + "w".rjust(7) + "RMSEout".rjust(9))
    for f in fits:
        print(f["group"].ljust(12) + str(f["n"]).rjust(5)
              + to_fixed(f["s50_pct"], 2).rjust(8) + to_fixed(f["s_width_pct"], 2).rjust(7)
              + to_fixed(f["s_rmse_out"], 3).rjust(9) + " | "
              + to_fixed(f["v50_kmh"], 1).rjust(7) + to_fixed(f["v_width_kmh"], 1).rjust(7)
              + to_fixed(f["v_rmse_out"], 3).rjust(9))
    for tag, k50, kw, kout in (("slope", "s50_pct", "s_width_pct", "s_rmse_out"),
                               ("speed", "v50_kmh", "v_width_kmh", "v_rmse_out")):
        mids = [f[k50] for f in fits if is_finite(f[k50])]
        ws = [f[kw] for f in fits if is_finite(f[kw])]
        outs = [f[kout] for f in fits if is_finite(f[kout])]
        if not mids:
            continue
        print(f"  {tag}: midpoint spread {to_fixed(min(mids), 1)}-{to_fixed(max(mids), 1)}"
              f" (ratio {to_fixed(max(mids) / min(mids), 2) if min(mids) > 0 else '—'})"
              f", width spread {to_fixed(min(ws), 1)}-{to_fixed(max(ws), 1)}"
              f", median held-out RMSE {to_fixed(med_of(outs), 4)}")

    # universal-width test: refit each rider with the width FIXED to the pooled median
    print("\n  universal-width transfer (width fixed to the pooled median, midpoint free):")
    for tag, grid50, gridw, key in (("slope", S50_GRID, SW_GRID, "g"),
                                    ("speed", V50_GRID, VW_GRID, "v")):
        wmed = med_of([f["s_width_pct" if key == "g" else "v_width_kmh"] for f in fits
                       if is_finite(f["s_width_pct" if key == "g" else "v_width_kmh"])])
        wfix = wmed / 100 if key == "g" else wmed
        outs = []
        for g in groups:
            a = agg[g]
            pf0, pf1 = [], []
            for h, dest in ((0, pf0), (1, pf1)):
                rng_ = range(ng) if key == "g" else range(nv)
                for i in rng_:
                    t = a["gt"][h][i] if key == "g" else a["vt"][h][i]
                    if t > 60:
                        x = (a["gsum"][h][i] / t) if key == "g" else (a["vsum"][h][i] / t)
                        p = (a["gp"][h][i] if key == "g" else a["vp"][h][i]) / t
                        dest.append((x, p, t))
            best = (float("nan"), float("inf"))
            for x50 in grid50:
                r = rmse_of(pf0, x50, wfix)
                if is_finite(r) and r < best[1]:
                    best = (x50, r)
            o = rmse_of(pf1, best[0], wfix) if pf1 and is_finite(best[0]) else float("nan")
            if is_finite(o):
                outs.append(o)
        print(f"    {tag}: fixed width {to_fixed(wmed, 2)}, "
              f"median held-out RMSE {to_fixed(med_of(outs), 4)} (n={len(outs)})")

    # ---------------- P4: within-rider, does occupancy fall with ride length? ----
    print("\nP4 — within-rider Spearman(ride distance, descent occupancy)  "
          "(registered: negative on >= 5 of 9)")

    def spear(xs: Sequence[float], ys: Sequence[float]) -> float:
        n = len(xs)
        if n < 8:
            return float("nan")
        rx = sorted(range(n), key=lambda i: xs[i])
        ry = sorted(range(n), key=lambda i: ys[i])
        a = [0.0] * n
        b = [0.0] * n
        for r, i in enumerate(rx):
            a[i] = r
        for r, i in enumerate(ry):
            b[i] = r
        ma, mb = sum(a) / n, sum(b) / n
        num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
        den = math.sqrt(sum((a[i] - ma) ** 2 for i in range(n))
                        * sum((b[i] - mb) ** 2 for i in range(n)))
        return num / den if den else float("nan")

    neg = 0
    tot = 0
    for g in groups:
        s = [r for r in ride_rows if r["group"] == g]
        rho = spear([r["km"] for r in s], [r["occ"] for r in s])
        if is_finite(rho):
            tot += 1
            if rho < 0:
                neg += 1
        print(f"  {g.ljust(12)} n = {str(len(s)).rjust(4)}  rho = {to_fixed(rho, 3)}")
    print(f"  -> negative on {neg}/{tot}")

    # ---------------- P3: the composite, cell-grain, held out ----------------
    print("\nP3 (composite) — cell-grain delta(s) vs the frozen eps_0 = 0.13, "
          "scored on HELD-OUT halves (registered: model wins on >= 5 of 9)")
    print("group".ljust(12) + "n_out".rjust(7) + "med|d_model-d_meas|".rjust(21)
          + "med|0.13-d_meas|".rjust(19) + "   winner")
    # eps_0 = 0.13 is DEFINED on real descents (mean grade >= 3%), so the
    # comparison is restricted to those bins. Scoring over all descending cells
    # — the first attempt — pitted the constant against terrain where riders
    # pedal 54-88% of the time, gave delta_meas of order 1, and manufactured a
    # 9/9 win that meant nothing.
    REAL = [i for i in range(ng) if i >= 4]
    x_of_bin = {}
    for g in groups:
        a = agg[g]
        x_of_bin[g] = [((a["gsum"][0][i] + a["gsum"][1][i])
                        / (a["gt"][0][i] + a["gt"][1][i]))
                       if (a["gt"][0][i] + a["gt"][1][i]) > 0 else float("nan")
                       for i in range(ng)]
    wins = 0
    scored = 0
    p3_rows = []
    for f in fits:
        g = f["group"]
        s50, w = f["s50_pct"] / 100, f["s_width_pct"] / 100
        if not (is_finite(s50) and is_finite(w)):
            continue
        # I_flat from the FIT half only — using the ride's own would leak
        # ride-specific information the constant baseline does not get.
        i_fit = med_of([r["i_flat"] for r in ride_rows
                        if r["group"] == g and r["half"] == 0 and is_finite(r["i_flat"])])
        if not (is_finite(i_fit) and i_fit > 0):
            continue
        em, ec = [], []
        for r in ride_rows:
            if r["group"] != g or r["half"] != 1:
                continue
            h_m = sum(r["hbin"][i] for i in REAL)
            e_m = sum(r["ebin"][i] for i in REAL)
            if h_m < 50:
                continue
            beta = r["m"] * G / KEFF
            d_meas = e_m / (beta * h_m)
            e_pred = sum(sigmoid(x_of_bin[g][i], s50, w) * i_fit * r["tbin"][i]
                         for i in REAL if is_finite(x_of_bin[g][i]))
            d_pred = e_pred / (beta * h_m)
            if not (is_finite(d_meas) and is_finite(d_pred)):
                continue
            em.append(abs(d_pred - d_meas))
            ec.append(abs(0.13 - d_meas))
            p3_rows.append({"group": g, "d_meas": d_meas, "d_model": d_pred})
        if len(em) < 5:
            continue
        scored += 1
        mm, mc = med_of(em), med_of(ec)
        win = mm < mc
        wins += 1 if win else 0
        print(g.ljust(12) + str(len(em)).rjust(7) + to_fixed(mm, 4).rjust(21)
              + to_fixed(mc, 4).rjust(19) + ("   model" if win else "   constant"))
    print(f"  -> model wins on {wins}/{scored}"
          + ("   P3 SUPPORTED" if wins >= 5 else "   P3 NOT SUPPORTED"))
    if p5_fail:
        print(f"\n!! P5 FAILED for {p5_fail} — braking dominates there; the sigmoid is not "
              "interpretable as a pedalling choice for those groups.")

    # ---------------- write ----------------
    rows = []
    for g in groups:
        a = agg[g]
        for i in range(ng):
            t = sum(a["gt"][h][i] for h in (0, 1))
            if t <= 0:
                continue
            p = sum(a["gp"][h][i] for h in (0, 1))
            rows.append({"group": g, "axis": "grade", "bin": i,
                         "x": sum(a["gsum"][h][i] for h in (0, 1)) / t * 100,
                         "t_s": t, "occ": p / t,
                         "I_W": (sum(a["ge"][h][i] for h in (0, 1)) / p) if p > 0 else float("nan"),
                         "brake_share": (sum(a["gb"][h][i] for h in (0, 1)) / (t - p)) if t > p else float("nan")})
        for i in range(nv):
            t = sum(a["vt"][h][i] for h in (0, 1))
            if t <= 0:
                continue
            p = sum(a["vp"][h][i] for h in (0, 1))
            rows.append({"group": g, "axis": "speed", "bin": i,
                         "x": sum(a["vsum"][h][i] for h in (0, 1)) / t,
                         "t_s": t, "occ": p / t, "I_W": float("nan"),
                         "brake_share": float("nan")})
    for name, data in (("e44_scurve_cells", rows), ("e44_scurve_fits", fits)):
        if not data:
            continue
        cols = list(dict.fromkeys(k for r in data for k in r))
        dest = os.path.join(RESULTS, f"{name}{'.SMOKE' if SMOKE else ''}.csv")
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for r in data:
                fh.write(",".join(
                    (f'"{v}"' if isinstance(v, str)
                     else to_fixed(v, 4) if is_finite(v) else "")
                    for v in (r.get(k, float("nan")) for k in cols)) + "\n")
        print(f"wrote {os.path.basename(dest)} ({len(data)} rows)")


if __name__ == "__main__":
    main()
