#!/usr/bin/env python3
"""verify_v2edge_clamp.py — Entry 18's numerical evidence (self-contained, no ride data).

Python port of the retired verify_v2edge_clamp.mjs (byte-identical output).

Claim 1 (dead clamp): sampasimu's v2Edge descent cost is strictly positive for every
(dist, dh, params), so its trailing max(0, e) never fires. Algebra (alpha = aRoll + aAero,
eps(s) = clamp01(min(1, (alpha/beta)/s) - 0.13), s = |dh|/d):
  gentle  s <= alpha/beta      : eps = 0.87 and beta|dh| <= alpha*d  =>  e >= 0.13*alpha*d
  middle  eps in (0, 0.87)     : the alpha parts cancel exactly      =>  e = 0.13*beta*|dh|
  steep   eps floored at 0     : e = alpha*d
(k_smooth < 1 scales beta down while abRatio stays un-smoothed — margins only widen.)
This is the same bound as the app's A* admissibility proof (descFloor = 0.13*alpha > 0).

Claim 2 (Jensen sign): grade-local per-edge eps credit >= the aggregate-eps_geom credit,
because f(x) = max(0, x - 0.13) is convex on [0, 1] — so the deployed app gives MORE
descent credit than the champion R0, never less (equality on constant grade).

Run: python3 harness/verify_v2edge_clamp.py   (exits non-zero on any violation)
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis"))
from bem.jsfmt import to_exponential, to_fixed

OFF = 0.13


# Verbatim structure of sampasimu energy-worker.js v2Edge, returning the PRE-clamp value.
def v2edge_descent_preclamp(dist, ndh, c):
    eps = c["abRatio"] * dist / ndh
    if eps > 1:
        eps = 1
    eps -= OFF
    if eps < 0:
        eps = 0
    return c["aRoll"] * dist + c["aAero"] * dist - eps * c["beta"] * ndh


def flat_eq_speed(P, m, crr, cda, rho, keff):
    a = crr * m * 9.81
    b = 0.5 * rho * cda
    lo, hi = 0, 40
    for _ in range(80):
        v = (lo + hi) / 2
        if (a + b * v * v) * v < keff * P:
            lo = v
        else:
            hi = v
    return (lo + hi) / 2


def bundle(m, crr, cda, rho, keff, p_flat, k_smooth):
    vf = flat_eq_speed(p_flat, m, crr, cda, rho, keff)
    mg = m * 9.81
    aero_coef = 0.5 * rho * cda * vf * vf
    KJ = 1000
    return {
        "aRoll": mg * crr / keff / KJ,
        "aAero": aero_coef / keff / KJ,
        "beta": mg * k_smooth / keff / KJ,     # kSmooth scales beta…
        "abRatio": crr + aero_coef / mg,       # …but abRatio stays un-smoothed (as in app.js)
    }


fail = 0


def check(ok, msg):
    global fail
    print(f"{'ok  ' if ok else 'FAIL'} {msg}")
    if not ok:
        fail = 1


# ---- Claim 1: sweep. Parameters x geometry, track the global minimum pre-clamp cost.
minPre = math.inf
minAt = None
combos = 0
for m in (50, 75, 120):
    for crr in (0.002, 0.008, 0.02):
        for cda in (0.2, 0.45, 0.6):
            for pFlat in (40, 80, 200):
                for kSmooth in (0.5, 0.8, 1):
                    c = bundle(m, crr, cda, 1.1, 0.97, pFlat, kSmooth)
                    dist = 0.5
                    while dist <= 60:
                        g = 0.001
                        while g <= 5:                      # grades 0.1%–500%
                            pre = v2edge_descent_preclamp(dist, g * dist, c)
                            combos += 1
                            if pre < minPre:
                                minPre = pre
                                minAt = {"m": m, "crr": crr, "cda": cda, "pFlat": pFlat,
                                         "kSmooth": kSmooth, "dist": dist, "g": g}
                            g *= 1.15
                        dist += 0.5
check(minPre > 0, f"dead clamp: min pre-clamp descent cost over {combos} combos = "
                  f"{to_exponential(minPre, 3)} kJ (> 0) at {json.dumps(minAt, separators=(',', ':'))}")

# Analytic floor spot-check: middle regime must equal 0.13*beta*|dh| exactly.
c = bundle(75, 0.008, 0.45, 1.1, 0.97, 80, 1)
dist = 10
s = c["abRatio"] / 0.5
ndh = s * dist                                             # eps = 0.5 - 0.13, middle regime
pre = v2edge_descent_preclamp(dist, ndh, c)
check(abs(pre - OFF * c["beta"] * ndh) < 1e-12,
      f"middle-regime identity e = 0.13·β·|dh| ({to_exponential(pre, 6)})")


# ---- Claim 2: Jensen. Per-edge credit >= aggregate credit on random descent profiles.
def credits(edges, ab):                                    # edges: [{d, drop}]
    per = H = xw = 0.0
    for e in edges:
        d, drop = e["d"], e["drop"]
        x = min(1, ab * d / drop)                          # = min(1, (alpha/beta)/s)
        per += max(0, x - OFF) * drop                      # app: offset+clamp per edge
        H += drop
        xw += x * drop
    agg = max(0, min(1, xw / H - OFF)) * H                 # champion: aggregate eps_geom
    return per, agg


jensenOk = True
worst = 0.0
# NB: the JS PRNG runs in float64 (seed*1103515245 overflows 2^53 and rounds) —
# reproduce that exactly by keeping the seed a float, not an exact int.
seed = 42.0


def rnd():
    global seed
    seed = (seed * 1103515245.0 + 12345.0) % 2147483648.0
    return seed / 2147483648.0


for _ in range(20000):
    ab = 0.005 + rnd() * 0.05
    n = 2 + math.floor(rnd() * 30)
    edges = []
    for _ in range(n):
        d = 1 + rnd() * 50
        edges.append({"d": d, "drop": d * (0.001 + rnd() * 1.5)})
    per, agg = credits(edges, ab)
    if per < agg - 1e-9:
        jensenOk = False
        worst = min(worst, per - agg)
check(jensenOk, "Jensen: per-edge (grade-local) descent credit ≥ aggregate ε_geom credit on 20k random profiles")

edges = [{"d": 10, "drop": 0.4} for _ in range(10)]        # constant grade
per, agg = credits(edges, 0.0187)
check(abs(per - agg) < 1e-9, f"constant grade ⇒ equality (per {to_fixed(per, 6)} = agg {to_fixed(agg, 6)})")

sys.exit(fail)
