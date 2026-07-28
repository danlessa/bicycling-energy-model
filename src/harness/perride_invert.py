#!/usr/bin/env python3
"""Entry 33 — per-ride physics inversion (m̂ / Ĉrr / ĈdA) → the Table-3 analogue.

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 33 BEFORE any result was
seen. Danilo's six-step strategy, every free parameter fixed in the entry:

  0. wind: round trip ⇒ 0; else historical daily wind at the 0.25°-quantized
     track centroid (open-meteo archive, disk-cached), signed headwind = half
     the ground speed projected on the net travel bearing.
  1. segmentation on 30 m cells of the 5 m profile: climbs (s ≥ 2% every
     cell, gain ≥ 40 m), flats (every cell in the flat band, length ≥ 1 km).
  2. clip: first 100 m of each flat; climbs until 10 m of gain is consumed.
  3. well-behaved: no braking (decel > 1.5 m/s² from > 3 m/s), power present
     ≥ 90% of time, moving ≥ 99% of time, no recording gap > 10 s.
  4. mass from a temporally-spread subset of climbs (min(n, max(2, ceil(n/3))),
     greedy max-min spread) — an average-mass estimator; gain-weighted.
  5. Ĉrr from the REMAINING climbs at frozen CdA0 (segment-disjoint from the
     mass, breaking the per-climb m–Crr collinearity); gain-weighted.
  6. ĈdA from flats given m̂ and Ĉrr; weight x/(1+σ_h), σ_h the intra-segment
     elevation SD.

Fallbacks per field (prior Crr 0.008 / CdA 0.40 / per-corpus anchor mass);
the CSV records every constant's source. ρ = 1.13 frozen (P1 degeneracy: ĈdA
is really the ρ·CdA product), k_eff = 0.98, G from the package. Scoring: the
Table-3 grid (forms 1–4 × unclamped ε_d / ε_f = 0.20 + canonical) on D1–D5.

Env: INVERT_SMOKE=1 (40 rides/corpus) · INVERT_NOFETCH=1 (no network; cache
misses score w = 0, flagged).

Run: python3 src/harness/perride_invert.py
Output: data/results/perride_invert.csv (gitignored, like every result).
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    deadband, empirical_kj, eps_geom,
                                    extract_regime_powers, flat_eq_speed,
                                    is_finite, jsdiv, load_pts,
                                    overall_mean_power, parse_fit,
                                    resample_profile)
from bicycling_energy_model.engines import G
from bicycling_energy_model.jsfmt import to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
CACHE = os.path.join(RESULTS, "cache")
os.makedirs(CACHE, exist_ok=True)

SMOKE = os.environ.get("INVERT_SMOKE") == "1"
NOFETCH = os.environ.get("INVERT_NOFETCH") == "1"

VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
RHO, KEFF, CRR0, CDA0 = 1.13, 0.98, 0.008, 0.40
CELL = 30.0
FLAT_MIN_LEN, CLIMB_MIN_GAIN = 1000.0, 40.0
FLAT_CLIP, CLIMB_CLIP_GAIN = 100.0, 10.0
BRAKE_DECEL, BRAKE_VMIN = 1.5, 3.0
POW_COV, POW_MIN, MOVE_COV, MAX_GAP = 0.90, 10.0, 0.99, 10.0
M_RANGE, CRR_RANGE, CDA_RANGE = (40.0, 200.0), (0.001, 0.04), (0.10, 1.00)
ANCHOR_M = {"longoes": None, "censo": 78.0, "ppaz": 74.5, "jaam": 101.9,
            "danlessa": 74.7}
ZWIFT = 260


# ---------------------------------------------------------------- utilities

def med_of(xs: list[float]) -> float:
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def rng(seed: int):
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def boot_ci(values: list[float], seed: int) -> tuple[float, float]:
    rand = rng(seed)
    n, B = len(values), 10000
    stats = sorted(med_of([values[int(rand() * n)] for _ in range(n)])
                   for _ in range(B))
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


# ---------------------------------------------------------------- geo + wind

def _haversine(a: dict, b: dict) -> float:
    R = 6371000.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


_GEO_CACHE_PATH = os.path.join(CACHE, "geo_summary.json")
_geo_cache: dict = (json.load(open(_GEO_CACHE_PATH))
                    if os.path.exists(_GEO_CACHE_PATH) else {})
_geo_dirty = [0]


def geo_summary(path: str) -> dict | None:
    """start/end separation, route distance, net bearing, 0.25°-quantized
    centroid — the only geometry that ever leaves this function. Disk-cached
    on (path, size, mtime)."""
    st = os.stat(path)
    key = f"{os.path.relpath(path, DATA)}|{st.st_size}|{int(st.st_mtime)}"
    if key in _geo_cache:
        return _geo_cache[key]
    out = _geo_summary_cold(path)
    _geo_cache[key] = out
    _geo_dirty[0] += 1
    if _geo_dirty[0] % 50 == 0:
        json.dump(_geo_cache, open(_GEO_CACHE_PATH, "w"))
    return out


def _geo_summary_cold(path: str) -> dict | None:
    import gzip
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    recs = parse_fit(raw)
    g = [r for r in recs if r.get("lat") is not None and r.get("lon") is not None]
    if len(g) < 30:
        return None
    sep = _haversine(g[0], g[-1])
    dist = sum(_haversine(g[i - 1], g[i]) for i in range(1, len(g)))
    p1, p2 = math.radians(g[0]["lat"]), math.radians(g[-1]["lat"])
    dl = math.radians(g[-1]["lon"] - g[0]["lon"])
    bearing = math.degrees(math.atan2(
        math.sin(dl) * math.cos(p2),
        math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))) % 360
    clat = round((sum(r["lat"] for r in g) / len(g)) / 0.25) * 0.25
    clon = round((sum(r["lon"] for r in g) / len(g)) / 0.25) * 0.25
    return {"sep": sep, "dist": dist, "bearing": bearing,
            "clat": clat, "clon": clon}


_WIND_CACHE_PATH = os.path.join(CACHE, "wind_daily.json")
_wind_cache: dict = (json.load(open(_WIND_CACHE_PATH))
                     if os.path.exists(_WIND_CACHE_PATH) else {})


def daily_wind(clat: float, clon: float, date: str) -> tuple[float, float] | None:
    """(speed km/h, direction-from °) at the quantized centroid, cached."""
    key = f"{clat},{clon},{date}"
    if key in _wind_cache:
        v = _wind_cache[key]
        return None if v is None else tuple(v)
    if NOFETCH:
        return None
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={clat}&longitude={clon}&start_date={date}&end_date={date}"
           "&daily=wind_speed_10m_max,wind_direction_10m_dominant"
           "&timezone=America%2FSao_Paulo")
    try:
        d = json.load(urllib.request.urlopen(url, timeout=20))["daily"]
        out = (d["wind_speed_10m_max"][0], d["wind_direction_10m_dominant"][0])
        if out[0] is None or out[1] is None:
            out = None
    except Exception:
        out = None
    _wind_cache[key] = out
    json.dump(_wind_cache, open(_WIND_CACHE_PATH, "w"))
    return out


def headwind_ms(geo: dict, date: str | None) -> tuple[float, str]:
    """Signed headwind (m/s, + = headwind) per the Entry-33 step-0 rule."""
    if geo is None:
        return 0.0, "nogeo"
    if geo["sep"] < max(1000.0, 0.02 * geo["dist"]):
        return 0.0, "loop"
    if not date:
        return 0.0, "nodate"
    w = daily_wind(geo["clat"], geo["clon"], date)
    if w is None:
        return 0.0, "nofetch"
    v_ms = w[0] / 3.6
    return 0.5 * v_ms * math.cos(math.radians(w[1] - geo["bearing"])), "fetched"


# ---------------------------------------------------------------- segmentation

def cells_of(prof: dict) -> list[tuple[float, float, float]]:
    """(x_start, x_end, grade) per 30 m cell, linear-interpolated elevations."""
    px, ph = prof["x"], prof["h"]
    x0, x1 = px[0], px[-1]
    nc = int((x1 - x0) / CELL)
    if nc < 2:
        return []
    j = 0

    def h_at(d: float) -> float:
        nonlocal j
        while j < len(px) - 2 and px[j + 1] < d:
            j += 1
        seg = px[j + 1] - px[j]
        f = (d - px[j]) / seg if seg > 1e-9 else 0.0
        return ph[j] * (1 - f) + ph[j + 1] * f

    hs = [h_at(x0 + k * CELL) for k in range(nc + 1)]
    return [(x0 + k * CELL, x0 + (k + 1) * CELL, (hs[k + 1] - hs[k]) / CELL)
            for k in range(nc)]


def find_segments(prof: dict) -> tuple[list[dict], list[dict]]:
    """Maximal cell runs: climbs (s >= 2% everywhere, gain >= 40 m, first
    10 m of gain clipped) and flats (in-band everywhere, >= 1 km, first
    100 m clipped)."""
    cells = cells_of(prof)
    climbs, flats = [], []

    def flush(kind: str, run: list[tuple[float, float, float]]) -> None:
        if not run:
            return
        if kind == "climb":
            gain = sum((b - a) * s for a, b, s in run)
            if gain < CLIMB_MIN_GAIN:
                return
            acc, i = 0.0, 0
            while i < len(run) and acc < CLIMB_CLIP_GAIN:
                acc += (run[i][1] - run[i][0]) * run[i][2]
                i += 1
            run = run[i:]
            gain = sum((b - a) * s for a, b, s in run)
            if run and gain >= CLIMB_MIN_GAIN - CLIMB_CLIP_GAIN:
                climbs.append({"x0": run[0][0], "x1": run[-1][1], "gain": gain,
                               "sbar": gain / (run[-1][1] - run[0][0])})
        else:
            if run[-1][1] - run[0][0] < FLAT_MIN_LEN:
                return
            x0 = run[0][0] + FLAT_CLIP
            if run[-1][1] - x0 >= FLAT_MIN_LEN - FLAT_CLIP:
                gain = sum((b - a) * s for a, b, s in run if b > x0)
                flats.append({"x0": x0, "x1": run[-1][1], "gain": gain})

    run_c: list = []
    run_f: list = []
    for c in cells:
        s = c[2]
        if s >= CLIMB_THR:
            run_c.append(c)
        else:
            flush("climb", run_c)
            run_c = []
        if DESC_THR < s < CLIMB_THR:
            run_f.append(c)
        else:
            flush("flat", run_f)
            run_f = []
    flush("climb", run_c)
    flush("flat", run_f)
    return climbs, flats


# ---------------------------------------------------------------- segment physics

def seg_integrals(pts: list[dict], seg: dict, wind: float) -> dict | None:
    """Balance integrals + well-behaved flags over the points in [x0, x1]."""
    sel = [q for q in pts if seg["x0"] <= q["x"] <= seg["x1"]]
    if len(sel) < 10:
        return None
    E = A = xg = t_tot = t_mov = t_pow = 0.0
    gap = brake = False
    for i in range(1, len(sel)):
        a, b = sel[i - 1], sel[i]
        dt = b.get("dt") or 0.0
        dx = b["x"] - a["x"]
        v = b.get("v")
        if v is None:
            v = dx / dt if dt > 0 else 0.0
        raw_gap = (b["t"] - a["t"]) if (b.get("t") is not None
                                        and a.get("t") is not None) else dt
        if raw_gap and raw_gap > MAX_GAP:
            gap = True
        va = a.get("v")
        if (va is not None and va > BRAKE_VMIN and dt > 0
                and (va - v) / dt > BRAKE_DECEL):
            brake = True
        t_tot += dt
        if v >= 0.5 / 3.6:
            t_mov += dt
        p = b.get("power")
        if p is not None and p > POW_MIN:
            t_pow += dt
        if p is not None:
            E += p * dt
        vr = v + wind
        A += vr * abs(vr) * dx
        xg += dx
    if t_tot <= 0 or xg <= 0:
        return None
    v_in = med_of([q.get("v") for q in sel[:3] if q.get("v") is not None])
    v_out = med_of([q.get("v") for q in sel[-3:] if q.get("v") is not None])
    dke_per_m = (0.5 * (v_out ** 2 - v_in ** 2)
                 if is_finite(v_in) and is_finite(v_out) else 0.0)
    sbar = seg.get("sbar", seg["gain"] / xg if xg else 0.0)
    ok = ((not brake) and (not gap)
          and t_pow / t_tot >= POW_COV and t_mov / t_tot >= MOVE_COV)
    return {"E": E, "A": A, "x": xg, "xg_cos": xg / math.sqrt(1 + sbar ** 2),
            "h": seg["gain"], "dke_per_m": dke_per_m, "ok": ok,
            "mid": 0.5 * (seg["x0"] + seg["x1"])}


def invert_mass(seg: dict) -> float:
    den = G * (seg["h"] + CRR0 * seg["xg_cos"]) + seg["dke_per_m"]
    if den <= 0:
        return float("nan")
    return (KEFF * seg["E"] - 0.5 * RHO * CDA0 * seg["A"]) / den


def invert_crr(seg: dict, m: float) -> float:
    den = m * G * seg["xg_cos"]
    if den <= 0:
        return float("nan")
    return (KEFF * seg["E"] - 0.5 * RHO * CDA0 * seg["A"]
            - m * G * seg["h"] - m * seg["dke_per_m"]) / den


def invert_cda(seg: dict, m: float, crr: float) -> float:
    if seg["A"] <= 0:
        return float("nan")
    return (KEFF * seg["E"] - crr * m * G * seg["xg_cos"]
            - m * G * seg["h"] - m * seg["dke_per_m"]) / (0.5 * RHO * seg["A"])


def spread_pick(segs: list[dict], k: int) -> tuple[list[dict], list[dict]]:
    """Greedy max-min temporal spread on segment midpoints: first, last, then
    repeatedly the segment farthest from every pick. Returns (picked, rest)."""
    if len(segs) <= k:
        return segs, []
    by_mid = sorted(segs, key=lambda s: s["mid"])
    picked = [by_mid[0], by_mid[-1]]
    pool = by_mid[1:-1]
    while len(picked) < k and pool:
        best = max(pool, key=lambda s: min(abs(s["mid"] - p["mid"]) for p in picked))
        picked.append(best)
        pool.remove(best)
    return picked, [s for s in segs if s not in picked]


# ---------------------------------------------------------------- per-ride

def run_ride(pts: list[dict], label: str, corpus: str, date: str | None,
             fit_path: str | None, m_fallback: float | None = None) -> dict | None:
    emp = empirical_kj(pts)
    if not is_finite(emp) or emp <= 0:
        return None
    phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile(phys, ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}

    try:
        geo = geo_summary(fit_path) if fit_path else None
    except Exception:
        geo = None
    wind, wind_src = headwind_ms(geo, date)

    climbs_raw, flats_raw = find_segments(prof)
    climbs = [s for s in (seg_integrals(pts, c, wind) for c in climbs_raw) if s]
    flats = [s for s in (seg_integrals(pts, f, wind) for f in flats_raw) if s]
    wb_climbs = [s for s in climbs if s["ok"]]
    wb_flats = [s for s in flats if s["ok"]]

    # step 4 — mass
    m_src = "fallback"
    m_hat = m_fallback if m_fallback is not None else ANCHOR_M[corpus]
    crr_pool: list[dict] = wb_climbs
    if wb_climbs:
        k = min(len(wb_climbs), max(2, math.ceil(len(wb_climbs) / 3)))
        picked, rest = spread_pick(wb_climbs, k)
        est = [(invert_mass(s), s["h"]) for s in picked]
        est = [(m, h) for m, h in est if is_finite(m) and M_RANGE[0] <= m <= M_RANGE[1]]
        if est:
            m_hat = sum(m * h for m, h in est) / sum(h for _, h in est)
            m_src = "inverted" if len(est) >= 2 else "thin"
            crr_pool = rest
    if m_hat is None:
        return None

    # step 5 — Crr from the remaining climbs
    crr_src, crr_hat = "fallback", CRR0
    est = [(invert_crr(s, m_hat), s["h"]) for s in crr_pool]
    est = [(c, h) for c, h in est if is_finite(c) and CRR_RANGE[0] <= c <= CRR_RANGE[1]]
    if est and m_src != "fallback":
        crr_hat = sum(c * h for c, h in est) / sum(h for _, h in est)
        crr_src = "inverted"

    # step 6 — CdA from flats (needs sigma_h per flat)
    cda_src, cda_hat = "fallback", CDA0
    if wb_flats:
        est = []
        for s in wb_flats:
            hs = [h for x, h in zip(prof["x"], prof["h"]) if s["mid"] - s["x"] / 2 <= x <= s["mid"] + s["x"] / 2]
            mu = sum(hs) / len(hs) if hs else 0.0
            sd = math.sqrt(sum((h - mu) ** 2 for h in hs) / len(hs)) if hs else 0.0
            c = invert_cda(s, m_hat, crr_hat)
            if is_finite(c) and CDA_RANGE[0] <= c <= CDA_RANGE[1]:
                est.append((c, s["x"] / (1 + sd)))
        if est:
            cda_hat = sum(c * w for c, w in est) / sum(w for _, w in est)
            cda_src = "inverted"

    # scoring — the Table-3 grid under the inverted physics
    p = {"m": m_hat, "Crr": crr_hat, "CdA": cda_hat, "rho": RHO, "keff": KEFF,
         "wind": wind, "vmax": VMAX, "vstart": VSTART}
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
          "flat": flat,
          "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
          "climbThr": CLIMB_THR, "descThr": DESC_THR}
    vf = flat_eq_speed(pw["flat"], p)
    epsG = eps_geom(prof, p, vf)
    eps_d = epsG if is_finite(epsG) else 0.2
    opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                        "descThr": DESC_THR, "climbPower": pw["climb"]}
    c = canonical(prof, pw, p)
    row = {"corpus": corpus, "ride": label, "emp": emp,
           "m_hat": m_hat, "m_src": m_src, "crr_hat": crr_hat,
           "crr_src": crr_src, "cda_hat": cda_hat, "cda_src": cda_src,
           "wind_ms": wind, "wind_src": wind_src,
           "m_logged": m_fallback if m_fallback is not None else float("nan"),
           "n_climb": len(climbs), "n_flat": len(flats),
           "n_wb_climb": len(wb_climbs), "n_wb_flat": len(wb_flats),
           "vf_kmh": vf * 3.6, "epsG": eps_d,
           "canon_d": jsdiv(c["legE"] / 1000 - emp, emp) * 100}
    for tag, eps in (("d", eps_d), ("f", 0.20)):
        a1 = approximate(prof, p, vf, eps, opt("off"))
        a2 = approximate(prof, p, vf, eps, opt("zero"))
        a3 = approximate(profS, p, vf, eps, opt("zero"))
        km = (max(0, 1 - 3 * (prof["x"][-1] / 1000) / a2["hplus"])
              if a2["hplus"] > 0 else 1)
        e4 = a2["roll"] + a2["aero"] + km * (a2["climb"] + a2["recov"])
        for name, E in (("f1", a1["E"]), ("f2", a2["E"]), ("f3", a3["E"]), ("f4", e4)):
            row[f"{name}_{tag}"] = jsdiv(E / 1000 - emp, emp) * 100
    return row


# ---------------------------------------------------------------- corpora

def iter_corpus(name: str):
    """Yields (pts, label, date, fit_path) per ride."""
    if name == "longoes":
        inputs = json.load(open(os.path.join(DATA, "model_inputs.json")))
        for e in inputs:
            if not e.get("file") or not e.get("has_power"):
                continue
            path = os.path.join(DATA, e["file"])
            yield load_pts(path), e["label"], e.get("date"), path, e["m"]

        return
    if name == "censo":
        man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
        files = [(e["file"], e.get("date")) for e in man if e.get("file")
                 and os.path.exists(os.path.join(DATA, e["file"]))]
        for f, d in (files[:40] if SMOKE else files):
            path = os.path.join(DATA, f)
            yield load_pts(path), os.path.basename(f), d, path, None
        return
    man = json.load(open(os.path.join(DATA, f"strava_{name}_manifest.json")))
    cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
            and a["km"] >= 20 and a["altCov"] >= 0.99]
    for a in (cand[:40] if SMOKE else cand):
        meta: dict = {}
        path = os.path.join(DATA, a["file"])
        pts = load_pts(path, meta)
        if meta.get("manufacturer") == ZWIFT:
            continue
        yield pts, os.path.basename(a["file"]), a.get("date"), path, None


COLS = [("form 1 · ε_d", "f1_d"), ("form 2 · ε_d", "f2_d"),
        ("form 3 · ε_d", "f3_d"), ("form 4 · ε_d", "f4_d"),
        ("form 3 · ε_f", "f3_f"), ("form 4 · ε_f", "f4_f"),
        ("canonical", "canon_d")]


def main() -> None:
    all_rows = []
    for corpus in ("longoes", "censo", "ppaz", "jaam", "danlessa"):
        rows = []
        for item in iter_corpus(corpus):
            pts, label, date, path, m_logged = item
            try:
                r = run_ride(pts, label, corpus, date, path, m_logged)
            except Exception:
                r = None
            if r is None:
                continue
            if r["m_src"] == "fallback" and m_logged is not None:
                r["m_src"] = "logged"
            rows.append(r)
        all_rows.extend(rows)

        print(f"\n== {corpus} — {len(rows)} rides ==")
        inv = [r for r in rows if r["m_src"] in ("inverted", "thin")]
        full = [r for r in rows if r["m_src"] == "inverted"
                and r["crr_src"] == "inverted" and r["cda_src"] == "inverted"]
        wnz = [r for r in rows if r["wind_src"] == "fetched"]
        print(f"coverage: mass inverted {len(inv)}/{len(rows)}, "
              f"full inversion {len(full)}, wind fetched {len(wnz)}, "
              f"crr {sum(1 for r in rows if r['crr_src']=='inverted')}, "
              f"cda {sum(1 for r in rows if r['cda_src']=='inverted')}")
        if inv:
            ms = sorted(r["m_hat"] for r in inv)
            q1, q3 = ms[int(0.25 * (len(ms) - 1))], ms[int(0.75 * (len(ms) - 1))]
            print(f"m̂ median {to_fixed(med_of(ms), 1)} kg "
                  f"(IQR {to_fixed(q1, 1)}–{to_fixed(q3, 1)}) "
                  f"vs anchor {ANCHOR_M[corpus] or 'logged 71–80'}")
        crr_i = [r["crr_hat"] for r in rows if r["crr_src"] == "inverted"]
        cda_i = [r["cda_hat"] for r in rows if r["cda_src"] == "inverted"]
        if crr_i:
            print(f"Ĉrr median {to_fixed(med_of(crr_i), 4)} (n={len(crr_i)})")
        if cda_i:
            print(f"ĈdA median {to_fixed(med_of(cda_i), 3)} (n={len(cda_i)})")
        print("model".ljust(18) + "med|Δ%| [95% CI]".rjust(22) + "medΔ% [95% CI]".rjust(24))
        for lab, key in COLS:
            av = [abs(r[key]) for r in rows if is_finite(r[key])]
            sv = [r[key] for r in rows if is_finite(r[key])]
            if not av:
                continue
            alo, ahi = boot_ci(av, 42)
            slo, shi = boot_ci(sv, 43)
            print(lab.ljust(18)
                  + f"{to_fixed(med_of(av), 2)} [{to_fixed(alo, 1)}, {to_fixed(ahi, 1)}]".rjust(22)
                  + f"{to_fixed(med_of(sv), 2)} [{to_fixed(slo, 1)}, {to_fixed(shi, 1)}]".rjust(24))
        if full and len(full) >= 10:
            print(f"full-inversion subset (n={len(full)}, selection-biased): "
                  f"f3_d {to_fixed(med_of([abs(r['f3_d']) for r in full]), 1)} · "
                  f"canon {to_fixed(med_of([abs(r['canon_d']) for r in full]), 1)}")

    json.dump(_geo_cache, open(_GEO_CACHE_PATH, "w"))
    cols = list(all_rows[0].keys())
    out = os.path.join(RESULTS, "perride_invert.csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in all_rows:
            fh.write(",".join((f'"{v}"' if isinstance(v, str) else to_fixed(v, 4))
                              for v in (r[k] for k in cols)) + "\n")
    print(f"\nwrote perride_invert.csv ({len(all_rows)} rides)")


if __name__ == "__main__":
    main()
