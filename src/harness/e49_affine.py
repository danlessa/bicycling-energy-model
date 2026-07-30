#!/usr/bin/env python3
"""Entry 49 — the affine deficit delta_5 = eps_coast*k1 + k2, global vs per rider.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 49) before the form was fitted.

    delta_5 = k1*eps_coast + k2   =>   eps_d = (1 - k1)*eps_coast - k2

so the form is an affine RESCALING of the coasting limit: k1 shrinks it, k2
offsets it. It NESTS the refitted constant (k1 = 0 is eps_0 with a free value),
so it cannot be worse in sample and the only real question is whether k1 differs
from zero by enough to pay for its parameter. It does NOT nest eps_2 = k/s_bar,
which is not affine in eps_coast — those two are genuine rivals.

Population: D3-D6 (seven riders), sigma = parse + power + s_bar >= 3%, matching
Entries 45 and 47 so the numbers are comparable. A secondary run over all rides
is reported separately, because Entry 46 showed the sub-3% regime differs.

Arms: global (2 parameters) and per rider (2 x 7 = 14). Baselines: eps_0 frozen
(0), eps_0 refitted (1), eps_2 = k/s_bar (1).

HELD-OUT IS THE DECIDING STATISTIC, not BIC: with 14 parameters the per-rider arm
is in-sample by construction, so it is scored on chronological split-halves (fit
one half of a rider's rides, score the other, both ways) as Entries 44 and 47 did.

Every form is fitted TWICE — against the energy residual and against the measured
deficit — because Entry 47 found the two spaces disagree by a factor of 2.5-3,
a delta fitted on energy absorbing model bias rather than measuring pedalling.

SECOND-ORDER: reads e47_formselect.csv (per-ride E at eps=0 and eps=1, exact
because approximate() is linear in eps) rather than re-parsing tracks. O_49 =
T(O_47), and the shared population is what makes the entries comparable.

Output: data/results/e49_affine.csv + console scoreboard.
Run: python3 src/harness/e49_affine.py        (E49_SMOKE=1 for a coarse grid)
"""

from __future__ import annotations

import math
import os
import sys
from typing import Callable, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import is_finite
from bicycling_energy_model.jsfmt import to_fixed

RESULTS: str = os.path.join(REPO, "data", "results")
SMOKE: bool = bool(os.environ.get("E49_SMOKE"))
GATE: float = 0.03
EPS0_PUB: float = 0.13
GROUPS: tuple[str, ...] = ("D3", "D4", "D5",
                           "D6-user_1", "D6-user_2", "D6-user_3", "D6-user_5")

# A ride, flattened: (eps_coast, E0, E1, emp, s_bar, dmeas, group, half)
Ride = tuple[float, float, float, float, float, float, str, int]


def load(pfx: str = "ag", gated: bool = True) -> list[Ride]:
    import csv
    out: list[Ride] = []
    with open(os.path.join(RESULTS, "e47_formselect.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            g = r["group"].strip('"')
            if g not in GROUPS:
                continue

            def f(k: str) -> float:
                try:
                    return float(r[k])
                except (KeyError, ValueError):
                    return float("nan")

            ec, e0, e1 = f(pfx + "_eps_coast"), f(pfx + "_E0"), f(pfx + "_E1")
            emp, sb, dm = f("emp"), f(pfx + "_sbar_cells"), f(pfx + "_dmeas")
            if not all(is_finite(v) for v in (ec, e0, e1, emp, sb)) or emp <= 0 or sb <= 0:
                continue
            if gated and sb < GATE:
                continue
            try:
                half = int(float(r["half"]))
            except (KeyError, ValueError):
                half = 0
            out.append((ec, e0, e1, emp, sb, dm, g, half))
    return out


# ---- the contestants -------------------------------------------------------
# delta(ride, params) -> the deficit. Per-rider forms read params by group.
Delta = Callable[[Ride, Sequence[float]], float]


def d_frozen(r: Ride, q: Sequence[float]) -> float:
    return EPS0_PUB


def d_const(r: Ride, q: Sequence[float]) -> float:
    return q[0]


def d_grade(r: Ride, q: Sequence[float]) -> float:
    return q[0] / r[4]


def d_affine(r: Ride, q: Sequence[float]) -> float:
    return q[0] * r[0] + q[1]


def resid(rows: Sequence[Ride], fn: Delta, q: Sequence[float],
          space: str = "energy") -> list[float]:
    out: list[float] = []
    for r in rows:
        if space == "deficit":
            if not is_finite(r[5]):
                continue
            out.append(r[5] - fn(r, q))
            continue
        eps = r[0] - fn(r, q)
        out.append(100.0 * ((r[1] + (r[2] - r[1]) * eps) / 1000 - r[3]) / r[3])
    return out


def fit(rows: Sequence[Ride], fn: Delta, bounds: list[tuple[float, float]],
        space: str = "energy") -> tuple[float, ...]:
    """LAD by deterministic refining grid — no RNG, identical on every re-run."""
    npar = len(bounds)
    if npar == 0:
        return ()
    lo = [b[0] for b in bounds]
    hi = [b[1] for b in bounds]
    ng = (120 if npar == 1 else 40) if SMOKE else (240 if npar == 1 else 60)
    passes = 3 if SMOKE else 4
    bq: tuple[float, ...] = tuple(lo)
    bv = float("inf")
    for _ in range(passes):
        st = [(hi[i] - lo[i]) / ng for i in range(npar)]
        if npar == 1:
            cand = [(lo[0] + i * st[0],) for i in range(ng + 1)]
        else:
            cand = [(lo[0] + i * st[0], lo[1] + j * st[1])
                    for i in range(ng + 1) for j in range(ng + 1)]
        for q in cand:
            v = sum(abs(x) for x in resid(rows, fn, q, space))
            if v < bv - 1e-12:
                bq, bv = q, v
        lo = [max(bounds[i][0], bq[i] - st[i]) for i in range(npar)]
        hi = [min(bounds[i][1], bq[i] + st[i]) for i in range(npar)]
    return bq


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[(n - 1) // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def bic_of(res: Sequence[float], npar: int) -> float:
    n = len(res)
    b = sum(abs(v) for v in res) / n
    return 2 * n * math.log(2 * b) + 2 * n + npar * math.log(n)


# Deliberately wide. The first run used [-1, 1.5] x [-0.6, 0.6] and the per-rider
# fits piled onto BOTH edges, which means a bound was choosing the answer. Widened
# until nothing binds; `at_bound` below reports it if anything still does.
AFF_B: list[tuple[float, float]] = [(-2.0, 3.0), (-1.5, 1.5)]


def at_bound(q: Sequence[float], bounds: list[tuple[float, float]]) -> bool:
    """True if any fitted parameter sits on its box edge — the fit is then the
    bound's answer, not the data's."""
    return any(abs(v - b[0]) < 1e-9 or abs(v - b[1]) < 1e-9 for v, b in zip(q, bounds))


def admissible(rows: Sequence[Ride], fn: Delta, q: Sequence[float]) -> float:
    """Fraction of rides whose implied eps_d lands OUTSIDE [0, 1].

    eps is a refunded FRACTION of descent potential energy: below 0 the descent
    costs energy, above 1 it returns more than it holds. Either is unphysical, so
    a form that buys accuracy by leaving the interval is fitting something other
    than recovery. eps_geom is unclamped by design, which is what makes this
    checkable rather than hidden."""
    if not rows:
        return float("nan")
    bad = 0
    for r in rows:
        e = r[0] - fn(r, q)
        if e < 0.0 or e > 1.0:
            bad += 1
    return bad / len(rows)


def per_rider(rows: Sequence[Ride], fn: Delta, bounds: list[tuple[float, float]],
              space: str = "energy") -> tuple[dict[str, tuple[float, ...]], list[float]]:
    """Fit one parameter set per rider; return the fits and the pooled residuals."""
    fits: dict[str, tuple[float, ...]] = {}
    res: list[float] = []
    for g in GROUPS:
        sub = [r for r in rows if r[6] == g]
        if len(sub) < 6:
            continue
        q = fit(sub, fn, bounds, space)
        fits[g] = q
        res += resid(sub, fn, q, space)
    return fits, res


def frac_out(rows: Sequence[Ride], fn: Delta, bounds: list[tuple[float, float]],
             per: bool, fits: dict[str, tuple[float, ...]],
             q: Sequence[float]) -> tuple[float, bool]:
    """(fraction of rides with eps_d outside [0,1], any parameter on a bound)."""
    if per:
        bad = tot = 0
        hit = False
        for g, qq in fits.items():
            sub = [r for r in rows if r[6] == g]
            bad += round(admissible(sub, fn, qq) * len(sub))
            tot += len(sub)
            hit = hit or at_bound(qq, bounds)
        return (bad / tot if tot else float("nan")), hit
    return admissible(rows, fn, q), (at_bound(q, bounds) if q else False)


def heldout(rows: Sequence[Ride], fn: Delta, bounds: list[tuple[float, float]],
            per: bool) -> list[float]:
    """Chronological split-half: fit on one half, score the other, both ways."""
    out: list[float] = []
    for h in (0, 1):
        tr = [r for r in rows if r[7] != h]
        te = [r for r in rows if r[7] == h]
        if len(tr) < 8 or not te:
            continue
        if per:
            for g in GROUPS:
                gtr = [r for r in tr if r[6] == g]
                gte = [r for r in te if r[6] == g]
                if len(gtr) < 6 or not gte:
                    continue
                out += resid(gte, fn, fit(gtr, fn, bounds), "energy")
        else:
            out += resid(te, fn, fit(tr, fn, bounds), "energy")
    return out


def run(rows: list[Ride], title: str) -> list[dict[str, object]]:  # noqa: C901
    print(f"\n{'=' * 84}\n{title}   |O| = {len(rows)}\n{'=' * 84}")
    per_g = {g: sum(1 for r in rows if r[6] == g) for g in GROUPS}
    print("  " + " · ".join(f"{g} {n}" for g, n in per_g.items() if n))

    SPEC: list[tuple[str, Delta, list[tuple[float, float]], bool]] = [
        ("eps0 frozen", d_frozen, [], False),
        ("eps0 refit", d_const, [(0.0, 0.60)], False),
        ("eps2 k/s_bar", d_grade, [(0.0, 0.05)], False),
        ("delta5 global", d_affine, AFF_B, False),
        ("delta5 per rider", d_affine, AFF_B, True),
    ]
    out: list[dict[str, object]] = []
    for name, fn, bounds, per in SPEC:
        if per:
            fits, res = per_rider(rows, fn, bounds)
            npar = len(bounds) * len(fits)
            shown = "per rider (below)"
            q = ()
        else:
            q = fit(rows, fn, bounds)
            res = resid(rows, fn, q)
            npar = len(bounds)
            shown = ", ".join(to_fixed(v, 4) for v in q) if q else "—"
            fits = {}
        f_out, bound_hit = frac_out(rows, fn, bounds, per, fits, q)
        ho = heldout(rows, fn, bounds, per)
        # deficit-space companion fit
        if per:
            _, dres = per_rider(rows, fn, bounds, "deficit")
            dq = "per rider"
        else:
            qd = fit(rows, fn, bounds, "deficit")
            dq = ", ".join(to_fixed(v, 4) for v in qd) if qd else "—"
        out.append({"form": name, "npar": npar, "params": shown,
                    "frac_eps_out": f_out, "at_bound": bound_hit,
                    "bic": bic_of(res, npar),
                    "med": median([abs(v) for v in res]),
                    "signed": median(res),
                    "held": median([abs(v) for v in ho]) if ho else float("nan"),
                    "deficit_params": dq, "fits": fits})

    lo = min(float(r["bic"]) for r in out)
    for r in out:
        r["dbic"] = float(r["bic"]) - lo
    tied = [r for r in out if float(r["dbic"]) < 2.0]
    champ = min(tied, key=lambda r: (int(r["npar"]), float(r["dbic"])))

    print(f"\n  {'form':<18}{'par':>4}  {'fitted':<22}{'BIC':>9}{'dBIC':>7}"
          f"{'med|D%|':>9}{'signed':>8}{'HELD-OUT':>10}{'eps∉[0,1]':>11}")
    for r in sorted(out, key=lambda r: float(r["bic"])):
        mark = "  <-- lowest BIC" if r is min(out, key=lambda x: float(x["bic"])) else ""
        print(f"  {str(r['form']):<18}{int(r['npar']):>4}  {str(r['params']):<22}"
              f"{to_fixed(float(r['bic']), 1):>9}{to_fixed(float(r['dbic']), 1):>7}"
              f"{to_fixed(float(r['med']), 2):>9}{to_fixed(float(r['signed']), 2):>8}"
              f"{to_fixed(float(r['held']), 2):>10}"
              f"{to_fixed(100 * float(r['frac_eps_out']), 1) + '%':>11}"
              + ("  BOUND" if r["at_bound"] else "") + mark)
    print(f"\n  parsimony champion (dBIC < 2 -> fewest parameters): {champ['form']}")
    best_ho = min((r for r in out if is_finite(float(r["held"]))),
                  key=lambda r: float(r["held"]))
    print(f"  BEST HELD-OUT (the deciding statistic): {best_ho['form']} "
          f"at {to_fixed(float(best_ho['held']), 2)}")

    print("\n  deficit-space fits (the space the published constants live in):")
    for r in out:
        print(f"    {str(r['form']):<18} {r['deficit_params']}")

    aff = [r for r in out if r["form"] == "delta5 per rider"][0]
    if aff["fits"]:
        print("\n  per-rider (k1, k2), energy space:")
        for g, q in aff["fits"].items():          # type: ignore[union-attr]
            print(f"    {g:<12} k1 = {to_fixed(q[0], 4):>8}   k2 = {to_fixed(q[1], 4):>8}")
    return out


def main() -> None:
    print("Entry 49 — the affine deficit delta_5 = k1*eps_coast + k2"
          + ("  [E49_SMOKE]" if SMOKE else ""))
    # P_f,r is the intended parameter class (Danilo, 2026-07-30): the per-ride
    # inverted, regime-consistent physics. The P_a,g arm was run first on my
    # misreading and is kept as a disclosed secondary — deleting a result I have
    # already seen would be the worse choice.
    scopes: list[tuple[str, str, bool, str]] = [
        ("fr-gated", "fr", True,
         "PRIMARY — D3-D6 over P_f,r, s_bar >= 3% (Entries 45/47's population)"),
        ("fr-all", "fr", False,
         "P_f,r, every ride (Entry 46's regime caveat applies)"),
        ("ag-gated", "ag", True,
         "DISCLOSED — the P_a,g arm, run first on a misreading of the request"),
        ("ag-all", "ag", False, "DISCLOSED — P_a,g, every ride"),
    ]
    results: list[tuple[str, list[dict[str, object]]]] = []
    for tag, pfx, gated, title in scopes:
        results.append((tag, run(load(pfx=pfx, gated=gated), title)))
    res_g = results[0][1]

    name = "e49_affine.SMOKE.csv" if SMOKE else "e49_affine.csv"
    cols = ["scope", "form", "npar", "params", "bic", "dbic", "med", "signed",
            "held", "frac_eps_out", "deficit_params"]
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for scope, rows_out in results:
            for r in rows_out:
                cells = [f'"{scope}"']
                for c in cols[1:]:
                    v = r[c]
                    if isinstance(v, str):
                        cells.append(f'"{v}"')
                    elif isinstance(v, int):
                        cells.append(str(v))
                    elif isinstance(v, bool):
                        cells.append("true" if v else "false")
                    else:
                        cells.append(to_fixed(float(v), 4) if is_finite(float(v)) else "")
                fh.write(",".join(cells) + "\n")
    print(f"\nwrote {name}")


if __name__ == "__main__":
    main()
