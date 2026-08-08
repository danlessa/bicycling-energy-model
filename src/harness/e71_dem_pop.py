#!/usr/bin/env python3
"""Entry 71, stage 2 — aggregates over the re-based e41 walk.

Reads the MODE walk (E41_POP=p1 E41_D6=1: paper 1's population D3–D5 with
travel rides KEPT, plus D6 against FABDEM+baro) and produces the three
deliverables of the entry:

  T1  the re-based Table-1 grid: per arm, med|Δ%| [95% CI] · signed [95% CI]
      at the letter's convention (F3 with ε_d, regime-consistent physics),
      over the pools {D3+D4+D5, D5, D5*, D5\\D5*, D6} — D5* being the
      IGC-covered subset (igc_ok = 1), so the full-corpus-vs-covered-subset
      comparison against FABDEM is explicit;
  CT  the c(τ) curves per elevation chain: median (h₊ − h̃₊(τ))/km at
      τ ∈ {2, 3, 4.5, 6}, per pool — how the measured noise rate depends on
      the deadband threshold, per source (Danilo's question);
  F5  F3 vs F4 vs F5 per arm (F5 at each floor of the τ grid, the Entry-63
      valley toll with v_b = ∞) — paper 3's H5 scored on paper 2's inputs.

Pools never mix arms a ride does not carry: every cell's population is the
rides with that arm present (n printed). No gates here — this is the
descriptive stage; parity/anchor gating belongs to the entry that re-bases
the letter's numbers.

Output: data/results/e71_dem_pop.csv (long format) + console tables.
Run: python3 src/harness/e71_dem_pop.py   (E71_IN=<csv basename> to point at
     a different walk, e.g. the smoke one)
"""

from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import is_finite  # noqa: E402
from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

RESULTS = os.path.join(REPO, "data", "results")
IN = os.path.join(RESULTS, os.environ.get(
    "E71_IN", "e41_dem_route.E41_POPp1_E41_D61.csv"))
OUT = os.path.join(RESULTS, "e71_dem_pop"
                   + (".SMOKE" if "smoke" in IN else "") + ".csv")

ARMS = ("own", "igc5", "igc5s10", "igc5s30", "igc30", "fab5", "fab30")
TGRID = (2.0, 3.0, 4.5, 6.0)
PROTO = "reg"                     # the letter's headline protocol


def med_of(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[int(k)] + s[int(k + 0.5)]) / 2


def rng(seed):
    a = seed & 0xFFFFFFFF

    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rand


def boot_ci(vals, seed):
    vals = [x for x in vals if is_finite(x)]
    if len(vals) < 2:
        return float("nan"), float("nan")
    rand = rng(seed)
    n, B = len(vals), 10000
    st = sorted(med_of([vals[int(rand() * n)] for _ in range(n)])
                for _ in range(B))
    return st[int(0.025 * B)], st[int(0.975 * B) - 1]


def fnum(r, k):
    v = r.get(k, "")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def main() -> None:
    rows = []
    with open(IN, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    n_all = len(rows)
    # the letter's PRIMARY population: physical floor + track QA + raster
    # validity, exactly as gate 3i defines it — every published cell filters
    # this way, so the re-based numbers must too
    rows = [r for r in rows if fnum(r, "dataOK") == 1
            and fnum(r, "g1_track") == 1 and fnum(r, "g2_valid") == 1]
    print(f"Entry 71 — aggregates over {os.path.basename(IN)}: "
          f"{n_all} rides walked, {len(rows)} in the primary population "
          f"(dataOK ∧ G1 ∧ G2)")

    pools = {
        "D3+D4+D5": [r for r in rows if r["corpus"] in ("ppaz", "jaam", "danlessa")],
        "D5": [r for r in rows if r["corpus"] == "danlessa"],
        "D5*": [r for r in rows if r["corpus"] == "danlessa"
                and fnum(r, "igc_ok") == 1],
        "D5\\D5*": [r for r in rows if r["corpus"] == "danlessa"
                    and fnum(r, "igc_ok") == 0],
        "D6": [r for r in rows if r["corpus"] == "skc"],
    }
    out_rows = []

    # ---- T1: the re-based Table-1 grid (F3 · eps_d · reg) ----
    print(f"\nT1 — per arm, med|Δ%| [95% CI] · signed [95% CI]  (F3, ε_d, {PROTO})")
    print(f"  {'arm':<9}" + "".join(f"{p:>30}" for p in pools))
    for arm in ARMS:
        cells = []
        for pname, sub in pools.items():
            d = [fnum(r, f"{arm}_{PROTO}_f3d") for r in sub
                 if fnum(r, f"{arm}_ok") == 1]
            d = [x for x in d if is_finite(x)]
            if len(d) < 5:
                cells.append(f"{'—':>30}")
                continue
            a = [abs(x) for x in d]
            ca = boot_ci(a, 42)
            cs = boot_ci(d, 43)
            cells.append(f"{med_of(a):5.1f} [{ca[0]:4.1f},{ca[1]:4.1f}]"
                         f"·{med_of(d):+5.1f} [{cs[0]:+4.1f},{cs[1]:+4.1f}]"
                         .rjust(30))
            out_rows.append({"table": "T1", "pool": pname, "arm": arm,
                             "n": len(d), "med_abs": med_of(a),
                             "abs_lo": ca[0], "abs_hi": ca[1],
                             "med_signed": med_of(d),
                             "sgn_lo": cs[0], "sgn_hi": cs[1]})
        print(f"  {arm:<9}" + "".join(cells))
    for pname, sub in pools.items():
        print(f"  [{pname}: {len(sub)} rides]", end="")
    print()

    # ---- CT: c(τ) per chain ----
    print(f"\nCT — measured noise rate c(τ) = (h₊ − h̃₊(τ))/km, medians, m/km")
    print(f"  {'pool':<9}{'arm':<8}" + "".join(f"{t:>8g}" for t in TGRID))
    for pname in ("D3+D4+D5", "D6"):
        sub = pools[pname]
        for arm in ARMS:
            have = [r for r in sub if fnum(r, f"{arm}_ok") == 1
                    and is_finite(fnum(r, f"{arm}_hplus_t0"))]
            if len(have) < 5:
                continue
            cells = []
            for ti in range(len(TGRID)):
                cs = [(fnum(r, f"{arm}_hplus") - fnum(r, f"{arm}_hplus_t{ti}"))
                      / fnum(r, "km") for r in have if fnum(r, "km") > 0]
                m = med_of(cs)
                cells.append(f"{m:>8.2f}")
                out_rows.append({"table": "CT", "pool": pname, "arm": arm,
                                 "n": len(cs), "tau": TGRID[ti], "c_med": m})
            print(f"  {pname:<9}{arm:<8}" + "".join(cells))

    # ---- F5: F3 vs F4 vs F5(τ floors), med|Δ%| per arm ----
    print(f"\nF5 — med|Δ%|: F3 · F4(c=3) · F5 at floors {TGRID} (ε_d, {PROTO})")
    print(f"  {'pool':<9}{'arm':<8}{'n':>5}{'F3':>7}{'F4':>7}"
          + "".join(f"{'F5@' + str(t):>9}" for t in TGRID))
    for pname in ("D3+D4+D5", "D5\\D5*", "D6"):
        sub = pools[pname]
        for arm in ARMS:
            have = [r for r in sub if fnum(r, f"{arm}_ok") == 1]
            f3 = [abs(fnum(r, f"{arm}_{PROTO}_f3d")) for r in have]
            f3 = [x for x in f3 if is_finite(x)]
            if len(f3) < 5:
                continue
            f4 = med_of([abs(fnum(r, f"{arm}_{PROTO}_f4d")) for r in have])
            f5s = [med_of([abs(fnum(r, f"{arm}_{PROTO}_f5d_t{ti}"))
                           for r in have]) for ti in range(len(TGRID))]
            print(f"  {pname:<9}{arm:<8}{len(f3):>5}{med_of(f3):>7.2f}"
                  f"{f4:>7.2f}" + "".join(f"{v:>9.2f}" for v in f5s))
            out_rows.append({"table": "F5", "pool": pname, "arm": arm,
                             "n": len(f3), "f3": med_of(f3), "f4": f4,
                             **{f"f5_t{ti}": f5s[ti] for ti in range(len(TGRID))}})

    # ---- the prose statistics: paired swap cost + noise-rate CIs ----
    print("\nPAIRED — own vs arm, per-ride Δ|Δ%| and over-charge counts")
    for pname in ("D3+D4+D5", "D5*", "D5\\D5*", "D6"):
        sub = pools[pname]
        for arm in ("igc5", "fab30", "fab5"):
            pair = [(fnum(r, f"{arm}_{PROTO}_f3d"), fnum(r, f"own_{PROTO}_f3d"))
                    for r in sub if fnum(r, f"{arm}_ok") == 1]
            pair = [(a, b) for a, b in pair if is_finite(a) and is_finite(b)]
            if len(pair) < 5:
                continue
            over = sum(1 for a, b in pair if a > b)
            dm = med_of([a - b for a, b in pair])
            print(f"  {pname:<9}{arm:<7} n={len(pair):>5}  over-charges on "
                  f"{over}/{len(pair)}  med Δbias {dm:+.2f} pp")
            out_rows.append({"table": "PAIR", "pool": pname, "arm": arm,
                             "n": len(pair), "over": over, "med_dbias": dm})
    print("\nNOISE-RATE CIs at τ = 2 (m/km, medians [95% CI])")
    for pname in ("D3+D4+D5", "D6"):
        sub = pools[pname]
        for arm in ("own", "igc5", "fab30", "fab5"):
            cs = [(fnum(r, f"{arm}_hplus") - fnum(r, f"{arm}_hplus_t0"))
                  / fnum(r, "km") for r in sub
                  if fnum(r, f"{arm}_ok") == 1 and fnum(r, "km") > 0
                  and is_finite(fnum(r, f"{arm}_hplus_t0"))]
            if len(cs) < 5:
                continue
            ci = boot_ci(cs, 42)
            print(f"  {pname:<9}{arm:<7} {med_of(cs):6.2f} "
                  f"[{ci[0]:.2f}, {ci[1]:.2f}]  (n={len(cs)})")
            out_rows.append({"table": "CRATE", "pool": pname, "arm": arm,
                             "n": len(cs), "c_med": med_of(cs),
                             "c_lo": ci[0], "c_hi": ci[1]})

    cols: list[str] = []
    for r in out_rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"\nwrote {os.path.basename(OUT)}")


if __name__ == "__main__":
    main()
