#!/usr/bin/env python3
"""Cross-language parity harness: the Python port (analysis/bem) vs the
VERBATIM JS reference implementations (extracted at run time by
js_runner.mjs from the app + compare.mjs — no drifting copies).

Cases: flat-equilibrium speed grid (headwind/tailwind branches), the four
engines over synthetic profiles (flat / climb / descent / rolling / rough
random walk / stall), deadband + ascent hysteresis, geometry-eps, and a
synthetic binary FIT file exercising per-definition endianness, compressed-
timestamp headers, developer fields, invalid-value markers, a non-record
message advancing the clock, and separate dist/alt records.

Exit 0 = every number agrees within REL_TOL (float64 round-off). Run from
anywhere; needs `node` in PATH.
"""

import base64
import json
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from bem import (approx_time, approximate, ascent_hyst, build_profile,  # noqa: E402
                 canonical, deadband, empirical_kj, eps_from_balance, eps_geom,
                 extract_regime_powers, flat_eq_speed, measured_flat_speed,
                 overall_mean_power, pts_from_fit, resample_profile,
                 smooth_elevation, v2_edge)
from bem.regime import eps_from_balance as _  # noqa: F401,E402  (import check)

REL_TOL = 1e-9
ABS_TOL = 1e-9

FAILS = []
CHECKS = [0]


def close(a, b, path):
    CHECKS[0] += 1
    if a is None and b is None:
        return
    if isinstance(a, bool) or isinstance(b, bool):
        if bool(a) != bool(b):
            FAILS.append(f"{path}: {a} != {b}")
        return
    if isinstance(a, str) or isinstance(b, str):
        if a != b:
            FAILS.append(f"{path}: {a!r} != {b!r}")
        return
    if a is None or b is None:
        FAILS.append(f"{path}: {a!r} != {b!r}")
        return
    fa, fb = float(a), float(b)
    if math.isnan(fa) and math.isnan(fb):
        return
    if fa == fb:
        return
    if abs(fa - fb) <= ABS_TOL + REL_TOL * max(abs(fa), abs(fb)):
        return
    FAILS.append(f"{path}: {fa!r} != {fb!r} (Δ {abs(fa-fb):.3e})")


def unsafe(v):
    """Undo js_runner's JSON tagging."""
    if v == "__nan__":
        return float("nan")
    if v == "__inf__":
        return float("inf")
    if v == "__-inf__":
        return float("-inf")
    return v


def cmp_tree(py, js, path):
    js = unsafe(js)
    if isinstance(py, dict):
        for k, pv in py.items():
            cmp_tree(pv, (js or {}).get(k), f"{path}.{k}")
        return
    if isinstance(py, (list, tuple)):
        if js is None or len(js) != len(py):
            FAILS.append(f"{path}: length {len(py)} != {None if js is None else len(js)}")
            return
        for i, pv in enumerate(py):
            cmp_tree(pv, js[i], f"{path}[{i}]")
        return
    close(py, js, path)


# ── deterministic profiles ───────────────────────────────────────────────────

def prng(seed):
    """mulberry32-style PRNG — deterministic across runs (no random module)."""
    state = [seed & 0xFFFFFFFF]

    def rnd():
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = state[0]
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t ^= t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF) & 0xFFFFFFFF
        t &= 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rnd


def make_profiles():
    profs = {}
    n = 1001
    profs["flat"] = {"x": [i * 5.0 for i in range(n)], "h": [20.0] * n}
    profs["climb6"] = {"x": [i * 5.0 for i in range(n)], "h": [10 + 0.06 * i * 5 for i in range(n)]}
    profs["descent5"] = {"x": [i * 5.0 for i in range(n)], "h": [10 + 0.05 * 5 * (n - 1 - i) for i in range(n)]}
    profs["rolling"] = {"x": [i * 5.0 for i in range(n)],
                        "h": [40 + 25 * math.sin(i / 37) + 6 * math.sin(i / 5.1) for i in range(n)]}
    rnd = prng(42)
    h, hh = 100.0, []
    xs = []
    x = 0.0
    for i in range(1500):
        x += 3 + 6 * rnd()
        h += (rnd() - 0.5) * 2.2
        xs.append(x)
        hh.append(max(0.0, h))
    profs["rough"] = {"x": xs, "h": hh}          # non-uniform dx + jitter
    profs["steep_stall"] = {"x": [i * 5.0 for i in range(201)],
                            "h": [0.18 * i * 5 for i in range(201)]}  # 18% wall
    return profs


P_BASE = {"m": 75, "Crr": 0.008, "CdA": 0.4, "rho": 1.1, "keff": 0.97,
          "vmax": 38 / 3.6, "vstart": 15 / 3.6, "wind": 0}
PW_BASE = {"climb": 150, "flat": 90, "descent": 10, "climbThr": 0.02, "descThr": -0.015}


def make_fit():
    """Synthetic FIT: little- AND big-endian record definitions, a lap message
    (non-20) advancing the clock, compressed-timestamp records, invalid-value
    markers, developer fields, and a stretch with dist/alt in separate records."""
    out = bytearray()

    def def_msg(local, gmn, fields, little=True, dev=None):
        out.append(0x40 | local | (0x20 if dev else 0))
        out.append(0)                       # reserved
        out.append(0 if little else 1)      # architecture
        out.extend(struct.pack("<H" if little else ">H", gmn))
        out.append(len(fields))
        for num, size, bt in fields:
            out.extend(bytes([num, size, bt]))
        if dev:
            out.append(len(dev))
            for num, size, idx in dev:
                out.extend(bytes([num, size, idx]))

    def rec(local, payload):
        out.append(local)
        out.extend(payload)

    T0 = 1_000_000_000
    # local 0: LE record — ts u32, dist u32/100, alt u16 (field 2), power u16, speed u16 (field 6)
    def_msg(0, 20, [(253, 4, 0x86), (5, 4, 0x86), (2, 2, 0x84), (7, 2, 0x84), (6, 2, 0x84)])
    x = alt_raw = 0.0
    rnd = prng(7)
    t = T0
    for i in range(400):
        t += 1
        x += 4.5 + 2 * rnd()
        alt = 700 + 30 * math.sin(i / 25) + 2 * (rnd() - 0.5)
        pwr = 0xFFFF if i % 97 == 0 else int(120 + 60 * math.sin(i / 15) + 30 * rnd())
        spd = int((4.0 + 2.5 * rnd()) * 1000)
        rec(0, struct.pack("<IIHHH", t, int(x * 100), int((alt + 500) * 5), pwr, spd))
    # non-20 message (lap, gmn 19) with only a timestamp — advances the clock
    def_msg(1, 19, [(253, 4, 0x86)])
    t += 30
    rec(1, struct.pack("<I", t))
    # local 2: BE record + a 3-byte developer field; enhanced alt (78) u32
    def_msg(2, 20, [(253, 4, 0x86), (5, 4, 0x86), (78, 4, 0x86), (7, 2, 0x84)],
            little=False, dev=[(0, 3, 0)])
    for i in range(300):
        t += 1
        x += 5.0 + 1.5 * rnd()
        alt = 715 + 20 * math.sin(i / 18)
        pwr = int(100 + 50 * rnd())
        rec(2, struct.pack(">IIIH", t, int(x * 100), int((alt + 500) * 5), pwr) + b"\x01\x02\x03")
    # compressed-timestamp records on local 0's definition (local id must be ≤ 3)
    for i in range(60):
        t += 1
        x += 4.0
        alt = 710 + i * 0.1
        hdr = 0x80 | (0 << 5) | (t & 0x1F)
        out.append(hdr)
        out += struct.pack("<IIHHH", 0xFFFFFFFF, int(x * 100), int((alt + 500) * 5),
                           int(90 + i), int(4500))
    # dist/alt in SEPARATE records: local 3 = dist-only, then alt-only via local 0 invalid dist
    def_msg(3, 20, [(253, 4, 0x86), (5, 4, 0x86)])
    for i in range(40):
        t += 1
        if i % 2 == 0:
            x += 9.0
            rec(3, struct.pack("<II", t, int(x * 100)))
        else:
            alt = 712 + i * 0.05
            rec(0, struct.pack("<IIHHH", t, 0xFFFFFFFF, int((alt + 500) * 5), 130, 4200))
    header = struct.pack("<BBHI4s", 14, 0x10, 2140, len(out), b".FIT") + b"\x00\x00"
    return bytes(header + out) + b"\x00\x00"  # trailing CRC (ignored by the parser)


def main():
    profs = make_profiles()
    cases = []
    py_results = []

    # 1. flatEqSpeed grid — including strong tailwind (non-monotone branch)
    for P in (40, 90, 150, 250):
        for wind in (-8, -3, 0, 3, 8):
            p = dict(P_BASE, wind=wind / 3.6)
            cases.append({"kind": "flatEq", "P": P, "p": p})
            py_results.append(flat_eq_speed(P, p))

    # 2. engines over the profile zoo × configs
    configs = [
        dict(dx=5, tau=0, eps=0.20, mode="off", wind=0),
        dict(dx=5, tau=2, eps=0.20, mode="zero", wind=0),
        dict(dx=30, tau=2, eps=0.35, mode="vc", wind=5 / 3.6),
        dict(dx=0, tau=2, eps=0.10, mode="off", wind=-5 / 3.6),
    ]
    for pname, prof in profs.items():
        for cfg in configs:
            p = dict(P_BASE, wind=cfg["wind"])
            pw = dict(PW_BASE)
            if pname == "steep_stall":
                pw = dict(PW_BASE, climb=0)  # P=0 into an 18% wall → must stall
            vf = flat_eq_speed(pw["flat"], p)
            opts = {"climbAeroMode": cfg["mode"], "climbThr": 0.02, "descThr": -0.015,
                    "climbPower": pw["climb"]}
            v2opts = {"kSmooth": 0.94 if cfg["tau"] else 1.0,
                      "epsOffset": 0.063 if cfg["tau"] else 0.13, "climbThr": 0.02}
            cases.append({"kind": "engines", "profile": prof, "dx": cfg["dx"],
                          "tau": cfg["tau"], "p": p, "pw": pw, "vf": vf,
                          "eps": cfg["eps"], "opts": opts, "v2opts": v2opts})
            pr = resample_profile(prof, cfg["dx"]) if cfg["dx"] else prof
            pa = smooth_elevation(pr, cfg["tau"])
            can = canonical(pr, pw, p)
            a = approximate(pa, p, vf, cfg["eps"], opts)
            v2 = v2_edge(pr, p, vf, v2opts)
            at = approx_time(pa, p, vf, pw)
            py_results.append({
                "canonical": {"legE": can["legE"], "t": can["t"], "Wrr": can["Wrr"],
                              "Waero": can["Waero"], "Wgrav": can["Wgrav"],
                              "Wbrake": can["Wbrake"], "dKE": can["dKE"],
                              "dispE": can["dispE"], "avgV": can["avgV"],
                              "minV": can["minV"], "stalled": can["stalled"],
                              "speedSum": sum(can["speed"]), "brkSum": sum(can["brk"])},
                "approx": a, "v2": v2, "atime": at,
            })

    # 3. deadband / ascent hysteresis
    for tau in (0, 1, 2, 3, 5):
        h = profs["rough"]["h"]
        cases.append({"kind": "deadband", "h": h, "tau": tau})
        py_results.append({"h": deadband(h, tau) if tau > 0 else deadband(h, tau),
                           "asc": ascent_hyst(h, tau)})

    # 4. epsGeom
    for pname in ("rolling", "rough", "descent5"):
        p = dict(P_BASE)
        vf = flat_eq_speed(90, p)
        cases.append({"kind": "epsgeom", "profile": profs[pname], "p": p, "vf": vf})
        py_results.append(eps_geom(profs[pname], p, vf))

    # 5. the synthetic FIT through the whole pipeline
    fit = make_fit()
    p = dict(P_BASE, wind=0)
    cases.append({"kind": "fit", "b64": base64.b64encode(fit).decode(),
                  "climbThr": 0.02, "descThr": -0.015, "p": p})
    pts = pts_from_fit(fit)
    rp = extract_regime_powers(pts, 0.02, -0.015)
    prof_info = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    from bem.fit import parse_fit
    recs = parse_fit(fit)

    def js_rec(r):  # dict key order irrelevant; None-keys absent in JS
        return {k: v for k, v in r.items() if v is not None}

    def js_pt(q):
        return {k: v for k, v in q.items() if v is not None}

    py_results.append({
        "nRecs": len(recs), "recs": [js_rec(r) for r in recs[:8]], "lastRec": js_rec(recs[-1]),
        "nPts": len(pts), "pts": [js_pt(q) for q in pts[:5]],
        "empKJ": empirical_kj(pts), "meanP": overall_mean_power(pts),
        "rp": rp,
        "vfMeas": measured_flat_speed(pts),
        "epsBal": eps_from_balance(pts, p),
        "epsFit": {"eps": eps_from_balance(pts, p), "vf": measured_flat_speed(pts) or 5},
        "profSum": {"x": sum(prof_info["x"]), "h": sum(prof_info["h"]), "n": prof_info["n"]},
    })

    js = subprocess.run(
        ["node", os.path.join(HERE, "js_runner.mjs")],
        input=json.dumps(cases).encode(), capture_output=True, check=True)
    js_results = json.loads(js.stdout)

    for i, (py, jsr) in enumerate(zip(py_results, js_results)):
        kind = cases[i]["kind"]
        cmp_tree(py, jsr, f"case{i}:{kind}")

    print(f"{CHECKS[0]} comparisons across {len(cases)} cases")
    if FAILS:
        print(f"FAIL — {len(FAILS)} mismatches:")
        for f in FAILS[:40]:
            print(" ", f)
        sys.exit(1)
    print("PARITY OK — Python port matches the verbatim JS to float64 round-off")


if __name__ == "__main__":
    main()
