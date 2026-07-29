#!/usr/bin/env python3
"""Entry 45, amendment — can we observe the deficit on NEARLY FLAT terrain?

Entry 45 fitted every form on rides with mean descent grade s_bar >= 3%, so the
choice between G (delta = k/s_bar, which diverges as terrain flattens) and G3
(a sigmoid, which saturates at 1) rests on a region with ZERO observations.
Danilo's probe: cherry-pick long, elevation-balanced SEGMENTS out of real rides
whose mean descent grade is far below the fitted range, and measure delta there.

Selection, fixed before running:
  * the N LONGEST activities in the corpus (Danilo: long rides give a 20 km
    window room to move); deterministic, no RNG. E45_SEG_N sets N, default 100
  * sliding windows of >= 20 km
  * cumulative ascent and descent balanced within 10% (so the window is not a net
    descent living off stored potential energy, and is comparable to a whole ride)
  * ranked by how close the window's s_bar comes to the 0.5% target
  * ONE window kept per ride, the closest, to keep the sample independent

Reported: the achievable s_bar range (the honest answer may be "0.5% is not
reachable on recorded profiles, because sub-cell altimeter noise floors the
grade of a descent cell"), and the measured delta wherever we do land, against
what G and G3 predict there.

Output: data/results/e45_flatseg.csv + console.
Run: python3 src/harness/e45_flatseg.py
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import is_finite
from bicycling_energy_model.engines import G as GRAV
from bicycling_energy_model.jsfmt import to_fixed

from bicycling_energy_model import build_profile, deadband, resample_profile
from e44_scurve import CELL, KEFF, VSTOP, cells_of_ride, corpus_rides
from skc_compare import RESULTS, med_of

N_ACT = int(os.environ.get("E45_SEG_N", "100"))
MIN_KM = 20.0
BALANCE = 0.10          # |h+ - h-| <= 10% of the larger
TARGETS = (0.005, 0.010, 0.020, 0.030)   # sweep, not a single point
TAU = 2.0               # the deadband F3 uses; h_minus must be TERRAIN, not jitter
DX = 5                  # profile grid, as everywhere else


def cells_smoothed(pts) -> "list[dict] | None":
    """30 m cells built from DEADBAND-SMOOTHED elevation.

    The first version of this probe used raw cells, and it measured noise: on a
    near-flat window the 'drop' was 2.4 m/km against a corpus noise rate of
    3.1 m/km, so delta = E_legs/(beta*h_minus) was dividing real pedal energy by
    altimeter jitter — and the search, by hunting for the flattest window, was
    steering itself toward exactly the windows where that ratio was most
    inflated. Deadbanding fixes BOTH ends: it removes the spurious drop from the
    denominator AND stops spurious 'descent' cells contributing pedal energy to
    the numerator."""
    prof = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    if not prof:
        return None
    p5 = resample_profile(prof, DX)
    hs = deadband(p5["h"], TAU)
    per = int(CELL / DX)
    nc = (len(hs) - 1) // per
    if nc < 2:
        return None
    x0 = p5["x"][0]
    out = [{"s": (hs[(k + 1) * per] - hs[k * per]) / CELL, "t": 0.0, "e": 0.0}
           for k in range(nc)]
    for r in pts:
        k = int((r["x"] - x0) // CELL)
        if k < 0 or k >= nc:
            continue
        v, w, pw = r.get("v"), (r.get("dt") or 1.0), r.get("power")
        if v is None or v < VSTOP:
            continue
        out[k]["t"] += w
        if pw is not None:
            out[k]["e"] += pw * w
    return out
# delta here is the UNCLAMPED ledger identity, so G must be judged with the
# ledger-target fit (0.0099), NOT the clamped paper-target fit (0.0051). The two
# differ by ~1.9x and mixing them has now caused three separate wrong readings in
# this entry. Whichever quantity is measured, the constant must match it.
K_G = 0.0099            # Entry 45, LEDGER-target fit
K_G_PAPER = 0.0051      # Entry 45, clamped paper-target fit (not used here)


def windows(cells: list[dict], min_cells: int) -> "list[tuple]":
    """Prefix sums -> (i, j, h_plus, h_minus, x_minus) for windows >= min_cells."""
    n = len(cells)
    if n < min_cells + 1:
        return []
    up = [0.0] * (n + 1)
    dn = [0.0] * (n + 1)
    xd = [0.0] * (n + 1)
    for i, c in enumerate(cells):
        d = c["s"] * CELL
        up[i + 1] = up[i] + (d if d > 0 else 0.0)
        dn[i + 1] = dn[i] + (-d if d < 0 else 0.0)
        xd[i + 1] = xd[i] + (CELL if d < 0 else 0.0)
    out = []
    step = max(1, min_cells // 8)
    for i in range(0, n - min_cells, step):
        for j in range(i + min_cells, n + 1, step):
            hp, hm, xm = up[j] - up[i], dn[j] - dn[i], xd[j] - xd[i]
            if hm < 20 or xm < 500:
                continue
            if abs(hp - hm) > BALANCE * max(hp, hm):
                continue
            out.append((i, j, hp, hm, xm))
    return out


def main() -> None:
    allrides = list(corpus_rides())
    # the N longest rides, ties broken by group then length for determinism
    allrides.sort(key=lambda t: (-(t[1][-1]["x"] if t[1] else 0), t[0]))
    sample = allrides[:N_ACT]
    print(f"Entry 45 amendment — flat-segment probe\n"
          f"  {len(allrides)} rides available -> scanning the {len(sample)} LONGEST "
          f"({to_fixed(sample[0][1][-1]['x']/1000, 0)} km down to "
          f"{to_fixed(sample[-1][1][-1]['x']/1000, 0)} km)")

    min_cells = int(MIN_KM * 1000 / CELL)
    rows = []
    for group, pts, mass in sample:
        cells = cells_smoothed(pts)
        raw = cells_of_ride(pts)
        if not cells or len(cells) < min_cells:
            continue
        wins = windows(cells, min_cells)
        if not wins:
            continue
        beta = mass * GRAV / KEFF
        for tgt in TARGETS:
            best = min(wins, key=lambda w: abs(w[3] / w[4] - tgt))
            i, j, hp, hm, xm = best
            sb = hm / xm
            e = sum(c["e"] for c in cells[i:j] if c["s"] < 0)
            if hm <= 0 or not is_finite(e):
                continue
            # noise audit: raw-minus-smoothed ascent over the same window
            nz = float("nan")
            if raw and j <= len(raw):
                rh = sum(max(0.0, c["s"] * CELL) for c in raw[i:j])
                sh = sum(max(0.0, c["s"] * CELL) for c in cells[i:j])
                nz = (rh - sh) / ((j - i) * CELL / 1000)
            rows.append({"group": group, "target_pct": tgt * 100,
                         "km": (j - i) * CELL / 1000, "s_bar": sb,
                         "h_plus": hp, "h_minus": hm, "x_minus_km": xm / 1000,
                         "hm_per_km": hm / ((j - i) * CELL / 1000),
                         "noise_per_km": nz,
                         "balance": abs(hp - hm) / max(hp, hm),
                         "delta": e / (beta * hm)})

    if not rows:
        print("  no qualifying window found")
        return
    print(f"\n  {len(rows)} windows (>= {MIN_KM:.0f} km, balanced within "
          f"{BALANCE*100:.0f}%), cells built on DEADBAND-SMOOTHED elevation\n")
    print("target".rjust(7) + "n".rjust(5) + "median s_bar".rjust(14)
          + "min s_bar".rjust(11) + "med h-/km".rjust(11) + "med noise/km".rjust(14)
          + "median delta".rjust(14) + "G pred".rjust(9) + "meas/G".rjust(9))
    for tgt in TARGETS:
        sub = [r for r in rows if abs(r["target_pct"] - tgt * 100) < 1e-9]
        if not sub:
            continue
        ms = med_of([r["s_bar"] for r in sub])
        print(f"{tgt*100:>6.1f}%{len(sub):>5}"
              + (to_fixed(ms * 100, 2) + "%").rjust(14)
              + (to_fixed(min(r["s_bar"] for r in sub) * 100, 2) + "%").rjust(11)
              + to_fixed(med_of([r["hm_per_km"] for r in sub]), 1).rjust(11)
              + to_fixed(med_of([r["noise_per_km"] for r in sub]), 1).rjust(14)
              + to_fixed(med_of([r["delta"] for r in sub]), 3).rjust(14)
              + to_fixed(K_G / ms, 3).rjust(9)
              + to_fixed(med_of([r["delta"] for r in sub]) / (K_G / ms), 2).rjust(9))
    print("\n  'noise/km' is raw-minus-smoothed ascent in the same window. Where it is")
    print("  comparable to h-/km the window is jitter, not terrain, and delta is not")
    print("  interpretable -- that is what invalidated the first version of this probe.")
    flat = [r for r in rows if r["s_bar"] < 0.02]
    if flat:
        print(f"\n  windows below 2% mean descent grade: {len(flat)}")
        print(f"    median h-/km {to_fixed(med_of([r['hm_per_km'] for r in flat]), 1)}"
              f" vs median noise/km {to_fixed(med_of([r['noise_per_km'] for r in flat]), 1)}")
        print(f"    median delta {to_fixed(med_of([r['delta'] for r in flat]), 3)}")
    else:
        print("\n  NO window below 2% mean descent grade survives the deadband:")
        print("  genuinely flat, elevation-balanced 20 km segments do not exist in")
        print("  these corpora, so the region where the candidate forms disagree is")
        print("  NOT OBSERVABLE in ride data. The choice there is a modelling prior.")

    cols = list(dict.fromkeys(k for r in rows for k in r))
    dest = os.path.join(RESULTS, "e45_flatseg.csv")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join((f'"{v}"' if isinstance(v, str)
                               else to_fixed(v, 5) if is_finite(v) else "")
                              for v in (r[k] for k in cols)) + "\n")
    print(f"\nwrote {os.path.basename(dest)} ({len(rows)} windows)")


if __name__ == "__main__":
    main()
