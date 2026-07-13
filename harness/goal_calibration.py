#!/usr/bin/env python3
"""ENTRY 20 — goal-driven calibration: can the deployed pipeline hit ±5% error / ±2% bias?
Python port of harness/goal_calibration.mjs (same console report, byte-identical
results/goal_calibration.csv).

Pre-registered protocol (journal Entry 20): two deployable levers only —
  L1 (global): static mask-normalized Gaussian pre-smoothing of the deployed IGC-SP 5 m
      raster, sigma ∈ {0, 10, 15, 20, 30, 45} m (0 = the original raster), profiles sampled
      at 5 m arc steps off the smoothed raster (the app keeps its 5 m grid);
  L2 (per-rider = the app's parameter panel): (CdA ∈ [0.2,0.6], Crr ∈ [0.003,0.015],
      kSmooth ∈ [0.5,1.0]) fitted per rider on TRAIN; mass FROZEN (74.3/101.7/74.5),
      rho 1.13, keff 0.98, per-ride P_flat from the ride's own extracted flat power.
Split: deterministic 50/50 by sha256('entry20:' + rideName) parity (even = train).
sigma* selected on TRAIN only (min over sigma of the WORST corpus's post-fit train med|Δ%|);
validation evaluated ONCE at the frozen (sigma*, per-rider params).
PASS = all three riders' validation med|Δ%| < 5 AND |median signed Δ%| < 2.
Fallback F1 (runs ONLY if the primary fails): refit with epsOffset as a 4th SHARED
parameter ∈ [0.05, 0.25] (per-rider CdA/Crr/kSmooth refit around it), re-select sigma,
single validation eval.

RASTER SMOOTHING (Phase A) is harness/goal_smooth_rasters.py — unchanged, still run with
/Users/danlessa/conda/bin/python; this port consumes its $SCRATCH/sampa_geral_sm*m.tif output.

ENGINE REUSE: the .mjs EXTRACTS the physics/parse engine from regime_compare.mjs and the
geo/DEM-sampling machinery from igc_resolution_test.mjs at run time (line-level brace-balanced
grabs, eval'd — nothing re-typed). The Python port does the equivalent by IMPORTING those same
functions from harness/regime_compare.py and harness/igc_resolution_test.py — the one
intentional structural deviation; everything numeric still matches byte-for-byte. The engine
globals the .mjs reaches through getPhysProfile() are read as MODULE ATTRIBUTES of
regime_compare (RC.phys_profile) — never `from regime_compare import …`, which would freeze the
value at import time. The .mjs also declares its OWN `sampleMs = {s0…s45}` in the eval'd scope,
so the grabbed sampleRaster times into *that* object: here we rebind IGC.sample_ms to the same
six-key dict, which the imported sample_raster then writes through (same effect, same bytes).
v2EdgeK below is the ONLY new physics code: r1dV2Edge generalized to (kSmooth, epsOffset)
exactly per sampasimu app.js readCost(). Asserted ≡ r1d_v2_edge to 1e-9 at (kSmooth=1,
epsOffset=0.13) on every profile (sanity gate).

Corpus = the ppaz/jaam/danlessa Entry-19 coverage sets ONLY, taken from Entry 19's own output
(results/igc_resolution_test.csv, counts asserted 277/181/406); every ride is INDEPENDENTLY
re-derived from the FIT file.

Phases (A = python, above):
  B — profile cache: per ride, per sigma, resample the GPS track to 5 m arc steps and batch-sample
      the raster with gdallocationinfo. Cached to $SCRATCH/goal_profiles.{bin,meta.json} — the
      SAME format and the SAME files as the .mjs (raw little-endian float64 concat + a
      JSON.stringify'd meta), because the report prints both files' sha256. Determinism is
      verified by rebuilding every 40th ride from the FIT + gdal and byte-comparing.
  C — calibration + validation (runs TWICE; the two report strings must be identical).

  python3 harness/goal_calibration.py   → report on stdout (timings on stderr) +
                                          goal_calibration.csv (gitignored via results/*)

MODULE IS IMPORT-SAFE — importing it runs nothing and touches no file; the driver lives in main().

JS name → Python name (this file's own top-level definitions, in file order):
  SIGMAS, DEM5, SCRATCH, SMOKE, EXPECT, CORPORA, FROZEN, BOUNDS, NPTS  → same names
  rasterFor → raster_for              v2EdgeK → v2_edge_k
  K_MIN_PRECLAMP/V2K_HPLUS/V2K_HMINUS → same (module globals)
  parseCsv → parse_csv                csvRides → csv_rides
  CACHE_BIN/CACHE_META → same         buildRideProfiles → build_ride_profiles
  buildCache → build_cache            loadOrBuildCache → load_or_build_cache
  cacheDeterminismCheck → cache_determinism_check      sha256hex → sha256hex
  isTrain → is_train                  byCorpus/trainOf/valOf → by_corpus/train_of/val_of
  pOf → p_of                          deltasOf → deltas_of        evalSet → eval_set
  scoreOf → score_of                  pctl → pctl                 linspace → linspace
  fitRider → fit_rider                f → f                       summarize → summarize
  passFail → pass_fail                sumLine → sum_line          runPhaseC → run_phase_c
  gates/gate → gates/gate             (CSV cell writer, inline in the .mjs) → cell4
  grabBlock/E/engineSrc → dropped (imports replace the runtime source grab)
"""

import gzip
import hashlib
import json
import math
import os
import sys
import time
from array import array
from itertools import islice

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))
sys.path.insert(0, HERE)

import igc_resolution_test as IGC  # noqa: E402
import regime_compare as RC  # noqa: E402
from igc_resolution_test import (build_dem_profile, geo_track_from_fit,  # noqa: E402
                                 grid_positions, lon_lat_at, sample_raster)
from regime_compare import (CLIMB_THR, DESC_THR, ENGINE_DX, G, PHYS,  # noqa: E402,F401
                            VMAX, VSTART, bin_grades, build_profile, d_pct,
                            empirical_kj, flat_eq_speed, is_finite, jquote, med_of,
                            point_regime_data, pts_from_fit, pw_from, r1d_v2_edge,
                            resample_profile)
from bem.jsfmt import js_str, to_exponential, to_fixed  # noqa: E402
from bem.v8math import js_num  # noqa: E402

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
SCRATCH = ('/private/tmp/claude-501/-Users-danlessa-repos-pedalhidro-simujaules/'
           '6a419542-bc75-4ec1-aced-8e8de9a58ae3/scratchpad')
DEM5 = '/Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif'
SIGMAS = [0, 10, 15, 20, 30, 45]


def raster_for(sig):
    return DEM5 if sig == 0 else os.path.join(SCRATCH, f'sampa_geral_sm{sig}m.tif')


SMOKE = bool(os.environ.get('GOAL_SMOKE'))   # debug only: 3 rides/corpus, no count asserts
EXPECT = {"ppaz": 277, "jaam": 181, "danlessa": 406}
CORPORA = ['ppaz', 'jaam', 'danlessa']

# the .mjs's `const sampleMs = { s0: 0, … s45: 0 }` injected into the eval'd engine scope: the
# grabbed sampleRaster closes over it. Rebinding the module global of igc_resolution_test makes
# the imported sample_raster time into exactly this dict (and only these six keys are emitted).
IGC.sample_ms = {"s0": 0, "s10": 0, "s15": 0, "s20": 0, "s30": 0, "s45": 0}


# ===== JS primitives =====
def js_json(v):
    """JSON.stringify (no spacing, insertion order, NaN/Infinity → null)."""
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return jquote(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return js_str(v) if math.isfinite(v) else "null"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(js_json(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(jquote(k) + ":" + js_json(x) for k, x in v.items()) + "}"
    raise TypeError(f"js_json: {type(v)}")


def js_plus(s):
    """JS unary + on a CSV cell: '' → 0, garbage → NaN."""
    if s is None:
        return float("nan")
    t = s.strip()
    if t == "":
        return 0.0
    try:
        return float(t)
    except ValueError:
        return float("nan")


def jmax(a, b):
    """Math.max(a, b) — propagates NaN (Python's max() does not)."""
    if a != a or b != b:
        return float("nan")
    return a if a > b else b


def now_ms():
    return time.time() * 1000


# ===== v2EdgeK — r1dV2Edge generalized to (kSmooth, epsOffset), app.js readCost() convention =====
# kSmooth multiplies the gravity term only (beta = m·g·kSmooth/keff → climb charge AND descent
# credit); abRatio (= α/β at kSmooth 1) stays UN-smoothed; epsOffset replaces the constant 0.13.
# At (1, 0.13) this is r1d_v2_edge verbatim (asserted, gate below).
# The edge walk is the .mjs's `for (let i = 1; i < xs.length; i++)` loop expressed as a pairwise
# zip — the same dx/dh subtractions of the same doubles in the same order, hoisted only to keep
# the hottest loop in the port affordable (≈20·10⁹ edge visits in the train matrix).
K_MIN_PRECLAMP = float("inf")
V2K_HPLUS = 0
V2K_HMINUS = 0


def v2_edge_k(prof, p, pw_flat, climb_thr, k_smooth, eps_offset):
    global K_MIN_PRECLAMP, V2K_HPLUS, V2K_HMINUS
    mg = p["m"] * G
    beta = mg * k_smooth / p["keff"]
    w = p["wind"]
    vFlat = max(0.05, flat_eq_speed(pw_flat if (pw_flat is not None and pw_flat > 0) else 1, p))
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) / p["keff"]
    abRatio = (aRoll + aAero) / (mg / p["keff"])   # un-smoothed: = Crr + ½ρCdA·v_f²/(m·g)
    xs, hs = prof["x"], prof["h"]
    Ej = 0.0
    hplus = 0.0
    hminus = 0.0
    kmin = K_MIN_PRECLAMP
    for x0, x1, h0, h1 in zip(xs, islice(xs, 1, None), hs, islice(hs, 1, None)):
        dx = x1 - x0
        dh = h1 - h0
        if not dx > 0:
            continue
        if dh >= 0:
            hplus += dh
            Ej += aRoll * dx + (aAero * dx if dh < climb_thr * dx else 0) + beta * dh
        else:
            ndh = -dh
            hminus += ndh
            eps = abRatio * dx / ndh
            if eps > 1:
                eps = 1
            eps -= eps_offset
            if eps < 0:
                eps = 0
            e = aRoll * dx + aAero * dx - eps * beta * ndh
            if e < kmin:
                kmin = e
            if e < 0:
                e = 0
            Ej += e
    K_MIN_PRECLAMP = kmin
    V2K_HPLUS = hplus
    V2K_HMINUS = hminus
    return Ej / 1000


# ===== Entry-19 CSV: ride membership + gate-1 reference values =====
def parse_csv(text):
    rows = []
    row = []
    field = ''
    in_q = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_q:
            if c == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    field += '"'
                    i += 1
                else:
                    in_q = False
            else:
                field += c
        elif c == '"':
            in_q = True
        elif c == ',':
            row.append(field)
            field = ''
        elif c == '\n':
            row.append(field)
            if len(row) > 1 or row[0] != '':
                rows.append(row)
            row = []
            field = ''
        elif c != '\r':
            field += c
        i += 1
    if field != '' or len(row):
        row.append(field)
        rows.append(row)
    return rows


csv_rides = {"ppaz": [], "jaam": [], "danlessa": []}

# ===== PHASE B: profile cache =====
CACHE_BIN = os.path.join(SCRATCH, 'goal_profiles_smoke.bin' if SMOKE else 'goal_profiles.bin')
CACHE_META = os.path.join(SCRATCH,
                          'goal_profiles_smoke.meta.json' if SMOKE else 'goal_profiles.meta.json')


def build_ride_profiles(corpus, row, file):
    with open(os.path.join(DATA, file), "rb") as fh:
        buf0 = fh.read()
    buf = gzip.decompress(buf0) if file.endswith('.gz') else buf0
    pts = pts_from_fit(buf)
    build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof5 = resample_profile(RC.phys_profile, ENGINE_DX)
    total = prof5["x"][len(prof5["x"]) - 1]
    emp = empirical_kj(pts)
    if abs(emp - row["emp"]) > 1e-3:
        raise ValueError(f"emp mismatch {corpus}/{row['ride']}: "
                         f"{js_num(emp)} vs csv {js_num(row['emp'])}")
    pw = pw_from(bin_grades(point_regime_data(pts), CLIMB_THR, DESC_THR), pts)
    geo = geo_track_from_fit(buf)
    if len(geo) < 2:
        raise ValueError(f"no-geo {corpus}/{row['ride']}")
    base = pts[0]["x"]
    d5 = grid_positions(total, 5)
    abs5 = [d + base for d in d5]
    g5 = lon_lat_at(geo, abs5)
    hs = []
    valid = []
    for sig in SIGMAS:
        v = sample_raster(raster_for(sig), g5["lons"], g5["lats"], 's' + str(sig))
        b = build_dem_profile(d5, v, 0.5)
        if not b["prof"] or b["validFrac"] < 0.99:
            raise ValueError(f"coverage {corpus}/{row['ride']} sigma={sig}: "
                             f"validFrac={js_num(b['validFrac']) if b else 'null'}")
        hs.append(b["prof"]["h"])
        valid.append(b["validFrac"])
    return {"corpus": corpus, "ride": row["ride"], "file": file, "emp": emp, "total": total,
            "pFlat": pw["flat"], "n": len(d5), "valid": valid, "hs": hs}


def build_cache():
    t0 = now_ms()
    meta_rides = []
    chunks = []
    off = 0
    done = 0
    total_rides = 0
    for c in CORPORA:
        total_rides += len(csv_rides[c])
    for corpus in CORPORA:
        with open(os.path.join(DATA, f'strava_{corpus}_manifest.json'), encoding="utf-8") as fh:
            man = json.load(fh)
        by_id = {}
        for a in man:
            by_id[a["id"]] = a["file"]
        for row in csv_rides[corpus]:
            file = by_id.get(row["ride"])
            if not file:
                raise ValueError(f"no manifest entry for {corpus}/{row['ride']}")
            r = build_ride_profiles(corpus, row, file)
            meta_rides.append({"corpus": r["corpus"], "ride": r["ride"], "file": r["file"],
                               "emp": r["emp"], "total": r["total"], "pFlat": r["pFlat"],
                               "n": r["n"], "valid": r["valid"], "off": off})
            for h in r["hs"]:
                chunks.append(array('d', h).tobytes())
            off += r["n"] * len(SIGMAS)
            done += 1
            if done % 50 == 0:
                print(f"  …cache {done}/{total_rides} "
                      f"({to_fixed((now_ms() - t0) / 1000, 0)} s, "
                      f"sampleMs={js_json(IGC.sample_ms)})", file=sys.stderr)
    meta = {"version": 1, "sigmas": SIGMAS, "engineDx": ENGINE_DX, "validFloor": 0.5,
            "rides": meta_rides}
    with open(CACHE_BIN, "wb") as fh:
        fh.write(b"".join(chunks))
    with open(CACHE_META, "w", encoding="utf-8") as fh:
        fh.write(js_json(meta))
    print(f"cache built: {done} rides, {off} doubles, "
          f"{to_fixed((now_ms() - t0) / 1000, 0)} s", file=sys.stderr)
    return meta


def load_or_build_cache():
    if os.path.exists(CACHE_META) and os.path.exists(CACHE_BIN):
        with open(CACHE_META, encoding="utf-8") as fh:
            meta = json.load(fh)
        want = ";".join(c + '|' + r["ride"] for c in CORPORA for r in csv_rides[c])
        have = ";".join(r["corpus"] + '|' + r["ride"] for r in meta["rides"])
        if meta["version"] == 1 and want == have and js_json(meta["sigmas"]) == js_json(SIGMAS):
            print('cache: reusing existing (membership + sigmas match)', file=sys.stderr)
            return meta
        print('cache: stale — rebuilding', file=sys.stderr)
    return build_cache()


# per-ride cache-materialized profiles (module state, like the .mjs's `rides`)
rides = []


def cache_determinism_check():
    """rebuild every 40th ride fresh (FIT parse + gdal) and byte-compare"""
    checked = 0
    bad = 0
    for i in range(0, len(rides), 40):
        r = rides[i]
        row = next((q for q in csv_rides[r["corpus"]] if q["ride"] == r["ride"]), None)
        fresh = build_ride_profiles(r["corpus"], row, r["file"])
        if (fresh["emp"] != r["emp"] or fresh["pFlat"] != r["pFlat"]
                or fresh["total"] != r["total"] or fresh["n"] != r["n"]):
            bad += 1
        else:
            for k in range(len(SIGMAS)):
                a = fresh["hs"][k]
                b = r["profs"][k]["h"]
                for j in range(len(a)):
                    if a[j] != b[j]:
                        bad += 1
                        break
        checked += 1
    return {"checked": checked, "bad": bad}


# ===== PHASE C: calibration + validation =====
def sha256hex(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def is_train(ride):
    return int(sha256hex('entry20:' + ride), 16) % 2 == 0


def by_corpus(c):
    return [r for r in rides if r["corpus"] == c]


def train_of(c):
    return [r for r in by_corpus(c) if r["split"] == 'train']


def val_of(c):
    return [r for r in by_corpus(c) if r["split"] == 'val']


FROZEN = {"CdA": 0.40, "Crr": 0.008, "kSmooth": 1.0}


def p_of(corpus, CdA, Crr):
    return {**PHYS[corpus], "CdA": CdA, "Crr": Crr, "vmax": VMAX, "vstart": VSTART}


def deltas_of(st, sig_idx, CdA, Crr, k_smooth, eps_off):
    return [d_pct(v2_edge_k(r["profs"][sig_idx], p_of(r["corpus"], CdA, Crr), r["pFlat"],
                            CLIMB_THR, k_smooth, eps_off), r["emp"]) for r in st]


def eval_set(st, sig_idx, CdA, Crr, k_smooth, eps_off):
    d = deltas_of(st, sig_idx, CdA, Crr, k_smooth, eps_off)
    return {"medAbs": med_of([abs(x) for x in d]), "medSigned": med_of(d)}


def score_of(o):
    return o["medAbs"] + (1000 + 100 * (abs(o["medSigned"]) - 1)
                          if abs(o["medSigned"]) > 1 else 0)


def pctl(xs, q):
    s = sorted(x for x in xs if is_finite(x))
    if not len(s):
        return float("nan")
    k = q * (len(s) - 1)
    lo = math.floor(k)
    return s[lo] + (s[lo + 1] - s[lo]) * (k - lo) if lo + 1 < len(s) else s[lo]


# Deterministic 3-level nested coarse-to-fine grid: 7(CdA)×7(Crr)×6(kSmooth) per level;
# refinement = ±1 previous step around the best, clipped to the global bounds; strict-<
# improvement in fixed iteration order (no randomness anywhere). Constraint |medΔ%| ≤ 1 as a
# large penalty (score_of).
BOUNDS = {"CdA": [0.2, 0.6], "Crr": [0.003, 0.015], "kSmooth": [0.5, 1.0]}
NPTS = {"CdA": 7, "Crr": 7, "kSmooth": 6}


def linspace(lo, hi, k):
    return [lo + (hi - lo) * i / (k - 1) for i in range(k)]


def fit_rider(train_set, sig_idx, eps_off, levels=3):
    rng = {"CdA": list(BOUNDS["CdA"]), "Crr": list(BOUNDS["Crr"]),
           "kSmooth": list(BOUNDS["kSmooth"])}
    best = None
    for _lvl in range(levels):
        grid = {"CdA": linspace(rng["CdA"][0], rng["CdA"][1], NPTS["CdA"]),
                "Crr": linspace(rng["Crr"][0], rng["Crr"][1], NPTS["Crr"]),
                "kSmooth": linspace(rng["kSmooth"][0], rng["kSmooth"][1], NPTS["kSmooth"])}
        best = None
        for cda in grid["CdA"]:
            for crr in grid["Crr"]:
                for ks in grid["kSmooth"]:
                    o = eval_set(train_set, sig_idx, cda, crr, ks, eps_off)
                    s = score_of(o)
                    if not best or s < best["score"]:
                        best = {"CdA": cda, "Crr": crr, "kSmooth": ks, **o, "score": s}

        def step(k, _rng=rng):
            return (_rng[k][1] - _rng[k][0]) / (NPTS[k] - 1)

        rng = {k: [max(BOUNDS[k][0], best[k] - step(k)), min(BOUNDS[k][1], best[k] + step(k))]
               for k in ('CdA', 'Crr', 'kSmooth')}
    return best


def f(x, d=2):
    if x is None or not is_finite(x):
        return '—'
    return to_fixed(x, d)


def summarize(st, sig_idx, prm, eps_off):
    d = deltas_of(st, sig_idx, prm["CdA"], prm["Crr"], prm["kSmooth"], eps_off)
    return {"n": len(d), "medAbs": med_of([abs(x) for x in d]), "medSigned": med_of(d),
            "p10": pctl(d, 0.10), "p90": pctl(d, 0.90)}


def pass_fail(s):
    return 'PASS' if (s["medAbs"] < 5 and abs(s["medSigned"]) < 2) else 'FAIL'


def sum_line(tag, s):
    return (f"{tag.ljust(46)} n={str(s['n']).rjust(3)}  med|Δ%|={f(s['medAbs']).rjust(6)}  "
            f"medΔ%={f(s['medSigned']).rjust(7)}  p10={f(s['p10']).rjust(7)}  "
            f"p90={f(s['p90']).rjust(7)}  {pass_fail(s)}")


def run_phase_c(bin_sha, meta_sha):
    global K_MIN_PRECLAMP
    K_MIN_PRECLAMP = float("inf")
    L = []
    L.append('ENTRY 20 — goal calibration (±5% error / ±2% bias), pre-registered protocol')
    L.append('corpora (Entry-19 coverage sets): '
             + ' '.join(f"{c}={len(by_corpus(c))}" for c in CORPORA))
    L.append("split (sha256 'entry20:'+ride, even=train): "
             + ' · '.join(f"{c} {len(train_of(c))}/{len(val_of(c))}" for c in CORPORA)
             + '  (train/val)')
    L.append(f"cache: {os.path.basename(CACHE_BIN)} sha256={bin_sha[0:16]}… "
             f"meta sha256={meta_sha[0:16]}…")

    # ---- train matrix: per sigma, per rider post-fit (CdA, Crr, kSmooth at epsOffset 0.13) ----
    fits = {}   # fits[sigIdx][corpus]
    L.append('\nTRAIN MATRIX — post-fit train med|Δ%| / medΔ% '
             '(fit: 7×7×6 ×3-level grid, |medΔ%|≤1 penalty):')
    L.append('sigma   ' + ''.join(c.rjust(22) for c in CORPORA) + '   worst med|Δ%|')
    worst_by_sig = []
    for si in range(len(SIGMAS)):
        fits[si] = {}
        worst = float("-inf")
        row = f"σ={str(SIGMAS[si]).ljust(4)}"
        for c in CORPORA:
            t0 = now_ms()
            b = fit_rider(train_of(c), si, 0.13)
            fits[si][c] = b
            print(f"  fit σ={SIGMAS[si]} {c}: {to_fixed((now_ms() - t0) / 1000, 1)} s → "
                  f"CdA={f(b['CdA'], 4)} Crr={f(b['Crr'], 5)} kS={f(b['kSmooth'], 4)} "
                  f"med|Δ%|={f(b['medAbs'])} medΔ%={f(b['medSigned'])}", file=sys.stderr)
            row += f"{f(b['medAbs'])} / {f(b['medSigned'])}".rjust(22)
            worst = jmax(worst, score_of(b))
        worst_by_sig.append(worst)
        L.append(row + f(worst, 3).rjust(14))
    # ---- sigma* selection on TRAIN only ----
    sig_star_idx = 0
    for si in range(1, len(SIGMAS)):
        if worst_by_sig[si] < worst_by_sig[sig_star_idx]:
            sig_star_idx = si
    L.append(f"\nσ* = {SIGMAS[sig_star_idx]} m "
             '(min worst-corpus post-fit train med|Δ%|, penalty-inclusive)')
    L.append('fitted params at σ*:')
    for c in CORPORA:
        b = fits[sig_star_idx][c]
        L.append(f"  {c.ljust(9)} CdA={f(b['CdA'], 4)}  Crr={f(b['Crr'], 5)}  "
                 f"kSmooth={f(b['kSmooth'], 4)}  (train med|Δ%|={f(b['medAbs'])}, "
                 f"medΔ%={f(b['medSigned'])})")
    L.append('fitted params at σ=0 (for the σ-ablation below):')
    for c in CORPORA:
        b = fits[0][c]
        L.append(f"  {c.ljust(9)} CdA={f(b['CdA'], 4)}  Crr={f(b['Crr'], 5)}  "
                 f"kSmooth={f(b['kSmooth'], 4)}  (train med|Δ%|={f(b['medAbs'])}, "
                 f"medΔ%={f(b['medSigned'])})")

    # ---- VALIDATION (single frozen eval) ----
    L.append('\nVALIDATION — frozen (σ*, per-rider fitted params), evaluated once:')
    all_pass = True
    val_summaries = {}
    for c in CORPORA:
        s = summarize(val_of(c), sig_star_idx, fits[sig_star_idx][c], 0.13)
        val_summaries[c] = s
        if not (s["medAbs"] < 5 and abs(s["medSigned"]) < 2):
            all_pass = False
        L.append('  ' + sum_line(f"{c} @ σ*={SIGMAS[sig_star_idx]}m calibrated", s))
    L.append('  PRIMARY ENDPOINT: '
             + ('PASS (all three riders meet med|Δ%|<5 ∧ |medΔ%|<2)' if all_pass else 'FAIL'))

    # ---- honesty ablations ----
    L.append('\nABLATIONS (validation sets; context, not endpoints):')
    for c in CORPORA:
        L.append('  ' + sum_line(f"{c} @ σ=0 calibrated (σ=0-fitted params)",
                                 summarize(val_of(c), 0, fits[0][c], 0.13)))
    for c in CORPORA:
        L.append('  ' + sum_line(f"{c} @ σ=0 with σ*-fitted params",
                                 summarize(val_of(c), 0, fits[sig_star_idx][c], 0.13)))
    for c in CORPORA:
        L.append('  ' + sum_line(f"{c} @ σ* UNCALIBRATED (frozen physics)",
                                 summarize(val_of(c), sig_star_idx, FROZEN, 0.13)))
    for c in CORPORA:
        L.append('  ' + sum_line(f"{c} @ σ=0 UNCALIBRATED (Entry-19 baseline)",
                                 summarize(val_of(c), 0, FROZEN, 0.13)))

    # ---- FALLBACK F1 (only if the primary fails): shared epsOffset as 4th parameter ----
    f1 = None
    if not all_pass:
        L.append('\nFALLBACK F1 — epsOffset as a 4th SHARED parameter ∈ [0.05, 0.25] '
                 '(per-rider CdA/Crr/kSmooth')
        L.append('refit around it; 1-D coarse-to-fine on epsOffset: 5 pts × 3 levels; '
                 'inner fits 2-level; re-select σ):')
        er = [0.05, 0.25]
        best_e = None
        for _lvl in range(3):
            for eo in linspace(er[0], er[1], 5):
                # reuse cached inner results per (eo, σ) — keyed exactly, deterministic
                best_sig = None
                for si in range(len(SIGMAS)):
                    worst = float("-inf")
                    prms = {}
                    for c in CORPORA:
                        b = fit_rider(train_of(c), si, eo, 2)
                        prms[c] = b
                        worst = jmax(worst, score_of(b))
                    if not best_sig or worst < best_sig["worst"]:
                        best_sig = {"si": si, "worst": worst, "prms": prms}
                if not best_e or best_sig["worst"] < best_e["worst"]:
                    best_e = {"eo": eo, **best_sig}
                print(f"  F1 eps={f(eo, 4)}: best σ={SIGMAS[best_sig['si']]} "
                      f"worst={f(best_sig['worst'], 3)}", file=sys.stderr)
            step = (er[1] - er[0]) / 4
            er = [max(0.05, best_e["eo"] - step), min(0.25, best_e["eo"] + step)]
        # full 3-level refit at the chosen (epsOffset, σ), then single validation eval
        prms = {}
        for c in CORPORA:
            prms[c] = fit_rider(train_of(c), best_e["si"], best_e["eo"], 3)
        L.append(f"  F1 chosen: epsOffset={f(best_e['eo'], 4)}, σ={SIGMAS[best_e['si']]} m")
        for c in CORPORA:
            L.append(f"  {c.ljust(9)} CdA={f(prms[c]['CdA'], 4)}  Crr={f(prms[c]['Crr'], 5)}  "
                     f"kSmooth={f(prms[c]['kSmooth'], 4)}  "
                     f"(train med|Δ%|={f(prms[c]['medAbs'])}, medΔ%={f(prms[c]['medSigned'])})")
        f1_pass = True
        for c in CORPORA:
            s = summarize(val_of(c), best_e["si"], prms[c], best_e["eo"])
            if not (s["medAbs"] < 5 and abs(s["medSigned"]) < 2):
                f1_pass = False
            L.append('  ' + sum_line(f"F1 {c} @ σ={SIGMAS[best_e['si']]}m calibrated", s))
        L.append('  F1 ENDPOINT: ' + ('PASS' if f1_pass else 'FAIL (F2: honest failure — stop)'))
        f1 = {**best_e, "prms": prms, "f1Pass": f1_pass}

    return {"report": "\n".join(L), "sigStarIdx": sig_star_idx, "fits": fits,
            "allPass": all_pass, "f1": f1, "minPreclamp": K_MIN_PRECLAMP,
            "valSummaries": val_summaries}


# ===== CSV cell writer (JS: typeof 'string' → JSON.stringify; finite → +Number(v).toFixed(4);
# anything else → '') =====
def cell4(v):
    if isinstance(v, str):
        return jquote(v)
    if is_finite(v):
        return js_str(float(to_fixed(v, 4)))
    return ""


def main():
    global rides
    os.makedirs(RESULTS, exist_ok=True)

    # ===== Entry-19 CSV: ride membership + gate-1 reference values =====
    with open(os.path.join(RESULTS, 'igc_resolution_test.csv'), encoding="utf-8") as fh:
        ref_csv = parse_csv(fh.read())
    ref_hdr = ref_csv[0]

    def ref_idx(k):
        return ref_hdr.index(k) if k in ref_hdr else -1

    for i in range(1, len(ref_csv)):
        c = ref_csv[i]
        corpus = c[ref_idx('corpus')]
        if corpus not in csv_rides:
            continue
        csv_rides[corpus].append({"ride": c[ref_idx('ride')], "emp": js_plus(c[ref_idx('emp')]),
                                  "v2_igc5": js_plus(c[ref_idx('v2_igc5')]),
                                  "km": js_plus(c[ref_idx('km')])})
    if SMOKE:
        for c in CORPORA:
            csv_rides[c] = csv_rides[c][0:3]

    cache_meta = load_or_build_cache()
    with open(CACHE_BIN, "rb") as fh:
        cache_buf = fh.read()
    cache_f64 = array('d')
    cache_f64.frombytes(cache_buf)
    bin_sha = hashlib.sha256(cache_buf).hexdigest()
    with open(CACHE_META, "rb") as fh:
        meta_sha = hashlib.sha256(fh.read()).hexdigest()
    del cache_buf

    # materialize rides: per ride one x-grid + 6 {x,h} profiles (h = slices of the cache buffer)
    for mr in cache_meta["rides"]:
        x = array('d', grid_positions(mr["total"], 5))
        if len(x) != mr["n"]:
            raise ValueError(f"grid mismatch {mr['ride']}")
        profs = [{"x": x, "h": cache_f64[mr["off"] + k * mr["n"]: mr["off"] + (k + 1) * mr["n"]]}
                 for k in range(len(SIGMAS))]
        rides.append({**mr, "profs": profs})
    del cache_f64

    for r in rides:
        r["split"] = 'train' if is_train(r["ride"]) else 'val'

    # ===== SANITY GATES =====
    gates = []

    def gate(name, passed, extra=''):
        gates.append({"name": name, "pass": passed, "extra": extra})

    # (2) corpus counts
    gate('corpus counts = 277/181/406',
         SMOKE or all(len(by_corpus(c)) == EXPECT[c] for c in CORPORA),
         ' '.join(f"{c}={len(by_corpus(c))}" for c in CORPORA))

    # (1) σ=0 frozen journal physics reproduces Entry 19's per-ride v2_igc5 (tol 1e-3 kJ; the CSV
    # is 4-dp rounded) + v2EdgeK(1, 0.13) ≡ r1dV2Edge on every profile at every σ (tol 1e-9 kJ)
    worst_csv = 0
    worst_csv_what = ''
    worst_eq = 0
    for r in rides:
        row = next((q for q in csv_rides[r["corpus"]] if q["ride"] == r["ride"]), None)
        p = p_of(r["corpus"], FROZEN["CdA"], FROZEN["Crr"])
        for si in range(len(SIGMAS)):
            a = v2_edge_k(r["profs"][si], p, r["pFlat"], CLIMB_THR, 1.0, 0.13)
            r[f"v2fr_s{SIGMAS[si]}"] = a
            r[f"hplus_s{SIGMAS[si]}"] = V2K_HPLUS
            b = r1d_v2_edge(r["profs"][si], p, {"flat": r["pFlat"]}, CLIMB_THR)
            worst_eq = jmax(worst_eq, abs(a - b))
            if si == 0:
                d = abs(a - row["v2_igc5"])
                if d > worst_csv:
                    worst_csv = d
                    worst_csv_what = f"{r['corpus']}/{r['ride']}"
    gate('σ=0 frozen physics ≡ Entry 19 v2_igc5 (tol 1e-3 kJ)', worst_csv < 1e-3,
         f"worst |Δ| {to_exponential(worst_csv, 2)} kJ ({worst_csv_what})")
    gate('v2EdgeK(kS=1, eps0=0.13) ≡ r1dV2Edge on all profiles/σ', worst_eq < 1e-9,
         f"max |Δ| {to_exponential(worst_eq, 2)} kJ")

    # (5) smoothing correctness spot check: hilliest ride (max h₊ at σ=0), h₊ monotone ↓ with σ
    hilly = rides[0]
    for r in rides:
        if r["hplus_s0"] > hilly["hplus_s0"]:
            hilly = r
    hp = [hilly[f"hplus_s{s}"] for s in SIGMAS]
    mono = True
    for i in range(1, len(hp)):
        if not hp[i] < hp[i - 1]:
            mono = False
    _km = hilly["km"] if hilly.get("km") is not None else hilly["total"] / 1000
    gate('h₊ monotone ↓ with σ on the hilliest ride', mono,
         f"{hilly['corpus']}/{hilly['ride']} ({f(_km, 1)} km): h₊ = "
         + ' '.join(f"σ{s}:{f(hp[i], 1)}" for i, s in enumerate(SIGMAS)))

    # cache determinism (subset rebuild, byte-identical)
    t0 = now_ms()
    cd = cache_determinism_check()
    print(f"cache determinism subset check: {cd['checked']} rides, "
          f"{to_fixed((now_ms() - t0) / 1000, 0)} s", file=sys.stderr)
    gate('cache determinism (every-40th-ride rebuild byte-identical)', cd["bad"] == 0,
         f"{cd['checked']} rides rechecked, {cd['bad']} mismatches")

    # (4) determinism: full Phase C twice → identical reports
    print('Phase C run 1…', file=sys.stderr)
    tC1 = now_ms()
    run1 = run_phase_c(bin_sha, meta_sha)
    print(f"Phase C run 1: {to_fixed((now_ms() - tC1) / 1000, 0)} s; run 2…", file=sys.stderr)
    tC2 = now_ms()
    run2 = run_phase_c(bin_sha, meta_sha)
    print(f"Phase C run 2: {to_fixed((now_ms() - tC2) / 1000, 0)} s", file=sys.stderr)
    gate('determinism: Phase C ×2 → identical reports', run1["report"] == run2["report"],
         f"sha256 run1={sha256hex(run1['report'])[0:12]} run2={sha256hex(run2['report'])[0:12]}")

    # (3) dead-clamp: min pre-clamp descent edge across every walked profile at every parameter set
    gate('dead-clamp: min pre-clamp descent edge > 0',
         run1["minPreclamp"] > 0 and run2["minPreclamp"] > 0,
         f"global min {to_exponential(run1['minPreclamp'], 3)} J (runs 1≡2: "
         + ('true' if run1["minPreclamp"] == run2["minPreclamp"] else 'false') + ')')

    # ===== output =====
    print(run1["report"])
    print('\n================ SANITY GATES ================')
    ok = True
    for g in gates:
        print(f"  [{'PASS' if g['pass'] else 'FAIL'}] {g['name']}"
              + ('  ' + g["extra"] if g["extra"] else ''))
        if not g["pass"]:
            ok = False
    print('SANITY: ALL PASS' if ok else 'SANITY: FAILURES ABOVE')

    # per-ride CSV (gitignored via results/*)
    si = run1["sigStarIdx"]
    cols = (['corpus', 'ride', 'split', 'emp', 'km', 'pflat']
            + [k for s in SIGMAS for k in (f"v2fr_s{s}", f"d_fr_s{s}", f"hplus_s{s}")]
            + ['pred_cal_sigstar', 'd_cal_sigstar', 'pred_cal_sig0', 'd_cal_sig0'])
    lines = [",".join(cols)]
    for r in rides:
        b = run1["fits"][si][r["corpus"]]
        b0 = run1["fits"][0][r["corpus"]]
        predS = v2_edge_k(r["profs"][si], p_of(r["corpus"], b["CdA"], b["Crr"]), r["pFlat"],
                          CLIMB_THR, b["kSmooth"], 0.13)
        pred0 = v2_edge_k(r["profs"][0], p_of(r["corpus"], b0["CdA"], b0["Crr"]), r["pFlat"],
                          CLIMB_THR, b0["kSmooth"], 0.13)
        rec = {"corpus": r["corpus"], "ride": r["ride"], "split": r["split"], "emp": r["emp"],
               "km": r["total"] / 1000, "pflat": r["pFlat"], "pred_cal_sigstar": predS,
               "d_cal_sigstar": d_pct(predS, r["emp"]), "pred_cal_sig0": pred0,
               "d_cal_sig0": d_pct(pred0, r["emp"])}
        for s in SIGMAS:
            rec[f"v2fr_s{s}"] = r[f"v2fr_s{s}"]
            rec[f"d_fr_s{s}"] = d_pct(r[f"v2fr_s{s}"], r["emp"])
            rec[f"hplus_s{s}"] = r[f"hplus_s{s}"]
        lines.append(",".join(cell4(rec.get(k)) for k in cols))
    with open(os.path.join(RESULTS, 'goal_calibration.csv'), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote goal_calibration.csv ({len(rides)} rides) · "
          f"sampleMs={js_json(IGC.sample_ms)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
