#!/usr/bin/env python3
"""ENTRY 21 — the resolution gap as a PARAMETER problem: fit the behavioural trio
(k_s, ε₀, climbThr) as a pure 5 m → 30 m RESOLUTION TRANSFER (stage 1, geometric —
measured energies NEVER touched), then test on validation whether igc5+trio inherits
igc30's measured accuracy (stage 2, endpoints E1/E2), per the journal's pre-registration.
Python port of harness/scale_trio.mjs (same console report, byte-identical
results/scale_trio.csv).

STAGE 1 (geometric): fit ONE shared trio over k_s∈[0.6,1.0], ε₀∈[0.0,0.20],
climbThr∈[0.01,0.04] (deterministic coarse-to-fine 9×11×7 grid + two ±1-step refinements)
minimizing the EQUAL-WEIGHTED mean over the three rider corpora of the corpus-median of
  |v2EdgeK(igc5 profile; trio, frozen physics) / v2EdgeK(igc30 profile; DEFAULT constants
   k_s=1, ε₀=0.13, thr=0.02, frozen physics) − 1|
over TRAIN rides only (Entry 20's sha256('entry20:'+ride) even=train split, verbatim).
Censo is NEVER in any fit. Ablations at the same objective: k_s-only, ε₀-only, k_s+ε₀, trio.

STAGE 2 (single frozen eval each, VALIDATION split; censo = all 58, out-of-sample):
  E1 (gap closure, frozen journal physics): med|Δ%| + median signed Δ% vs measured ∫P·dt for
      (a) igc5 default, (b) igc30 default, (c) igc5+trio; bridged = (c) within 1.0 pp med|Δ%|
      AND 1.5 pp bias of (b), per corpus incl. censo.
  E2 (physics coherence): per-rider (CdA, Crr) fit ONLY (trio + mass frozen) on TRAIN at
      igc5+trio, ONE validation eval per rider vs the Entry-20 gates (<5 ∧ <2).
  P1 implied drop-weighted ε · P2 fitted k_s vs h₊ ratio · P4 transfer-ratio distributions.

FAST STAGE-1 EVALUATION (harness-only): at frozen physics v2EdgeK decomposes exactly into
  E(k_s,ε₀,thr) = base + aAero·Σ_{ascent, dh/dx<thr} dx
                  + k_s·[ (mg/k_eff)·h₊ − Σ_desc max(0, epsr−ε₀)·(mg/k_eff)·|dh| ]
with sorted prefix/suffix sums giving O(log n) per (ride, combo); the descent clamp is provably
dead on the whole search box. The decomposition is asserted ≡ verbatim v2EdgeK at every
FITTED/REPORTED parameter set; every headline number is a verbatim v2EdgeK walk.

ENGINE REUSE: the .mjs EXTRACTS its engine at run time from THREE siblings — the physics/parse
engine from regime_compare.mjs, the geo/DEM sampling from igc_resolution_test.mjs, and the
generalized walk v2EdgeK + split/percentile/score helpers from goal_calibration.mjs (line-level
brace-balanced grabs, eval'd, nothing re-typed). The Python port does the equivalent by
IMPORTING those same functions from harness/regime_compare.py, harness/igc_resolution_test.py
and harness/goal_calibration.py — the one intentional structural deviation; everything numeric
still matches byte-for-byte. The engine globals the .mjs reaches through getPhysProfile() /
getKMin() / setKMin() are read and written as MODULE ATTRIBUTES (RC.phys_profile,
GC.K_MIN_PRECLAMP) — never `from … import …`, which would freeze the value at import time.
The .mjs also declares its OWN `const sampleMs = { r5: 0, r30: 0 };` in the eval'd scope, so the
grabbed sampleRaster times into *that* object: here we rebind IGC.sample_ms to the same two-key
dict, which the imported sample_raster then writes through (same effect, same bytes).

DATA: Entry 20's profile cache (goal_profiles.{bin,meta.json}; σ=0 = the unsmoothed igc5 profile
at 5 m steps) for the 864 rider rides, plus a SUPPLEMENTARY cache built here
(scale_trio_profiles.{bin,meta.json} in the session scratch dir) — the SAME format and the SAME
files as the .mjs (raw little-endian float64 concat + a JSON.stringify'd meta), so either
language can build it and the other reuse it: igc30 profiles for all 864 rider rides + the 58
Entry-19 censo rides, and igc5 profiles for the censo rides.

  python3 harness/scale_trio.py        → report on stdout (timings stderr) + scale_trio.csv
                                         (gitignored via results/*)
  SCALE_SMOKE=1 python3 harness/scale_trio.py  → debug: 3 rides/corpus, count/number gates skipped

JS name → Python name (this file's own top-level definitions, in file order):
  SCRATCH, DEM5, DEM30, GOAL_BIN, GOAL_META, SMOKE, SUPP_BIN, SUPP_META, EXPECT, CORPORA,
  ALL_CORP, DEFAULTS, SPACE, PHYS_BOUNDS, PHYS_NPTS, E20_SIGMA0_UNCAL_VAL, E20_SIGMA0_FITS,
  PLAUSIBLE, FROZEN                        → same names
  pOf → p_of              pFrozen → p_frozen          f → f           linspace → linspace
  WS_MAX_MISMATCH → WS_MAX_MISMATCH        walkStatsK → walk_stats_k
  csvRides → csv_rides    gMeta/gF64/gByKey → g_meta/g_f64/g_by_key
  buildRiderSupp → build_rider_supp        processCenso → process_censo
  buildSuppCache → build_supp_cache        loadOrBuildSupp → load_or_build_supp
  suppMeta/sF64/suppByKey → supp_meta/s_f64/supp_by_key
  rides → rides           byCorpus/trainOf/valOf → by_corpus/train_of/val_of
  suppDeterminismCheck → supp_determinism_check
  decompose → decompose   lowerBound/upperBound → lower_bound/upper_bound   decEval → dec_eval
  fitStage1 → fit_stage1  fitPhys → fit_phys
  summarizeDeltas → summarize_deltas        ratioStats → ratio_stats
  runAnalysis → run_analysis                gates/gate → gates/gate
  (CSV cell writer, inline in the .mjs) → cell6
  grabBlock/E/engineSrc → dropped (imports replace the runtime source grab)
"""

import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))
sys.path.insert(0, HERE)

import goal_calibration as GC  # noqa: E402
import igc_resolution_test as IGC  # noqa: E402
import regime_compare as RC  # noqa: E402
from goal_calibration import (is_train, js_json, js_plus, parse_csv,  # noqa: E402,F401
                              pctl, score_of, sha256hex, v2_edge_k)
from igc_resolution_test import (BBOX, build_dem_profile,  # noqa: E402
                                 geo_track_from_fit, grid_positions, lon_lat_at,
                                 sample_raster)
from regime_compare import (ASSUMED, CLIMB_THR, DESC_THR, ENGINE_DX, G,  # noqa: E402,F401
                            PHYS, TAU_SMOOTH, VMAX, VSTART, bin_grades,
                            build_profile, d_pct, deadband, empirical_kj,
                            flat_eq_speed, has_power, is_finite, jquote, jsdiv,
                            med_of, overall_mean_power, point_regime_data,
                            pts_from_fit, pw_from, r1d_v2_edge, resample_profile)
from bem.jsfmt import js_str, to_exponential, to_fixed  # noqa: E402

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
SCRATCH = ('/private/tmp/claude-501/-Users-danlessa-repos-pedalhidro-simujaules/'
           '6a419542-bc75-4ec1-aced-8e8de9a58ae3/scratchpad')
DEM5 = '/Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif'
DEM30 = os.path.join(SCRATCH, 'sampa_geral_30m.tif')
GOAL_BIN = os.path.join(SCRATCH, 'goal_profiles.bin')
GOAL_META = os.path.join(SCRATCH, 'goal_profiles.meta.json')
SMOKE = bool(os.environ.get('SCALE_SMOKE'))
SUPP_BIN = os.path.join(SCRATCH,
                        'scale_trio_profiles_smoke.bin' if SMOKE else 'scale_trio_profiles.bin')
SUPP_META = os.path.join(
    SCRATCH, 'scale_trio_profiles_smoke.meta.json' if SMOKE else 'scale_trio_profiles.meta.json')
EXPECT = {"ppaz": 277, "jaam": 181, "danlessa": 406, "censo": 58}
CORPORA = ['ppaz', 'jaam', 'danlessa']                # fit corpora (censo NEVER fitted)
ALL_CORP = ['ppaz', 'jaam', 'danlessa', 'censo']
DEFAULTS = {"kS": 1.0, "eps0": 0.13, "thr": 0.02}     # the deployed/journal constants
SPACE = {"kS": [0.6, 1.0, 9], "eps0": [0.0, 0.20, 11], "thr": [0.01, 0.04, 7]}   # lo, hi, npts
PHYS_BOUNDS = {"CdA": [0.2, 0.6], "Crr": [0.003, 0.015]}   # E2 per-rider fit
PHYS_NPTS = {"CdA": 7, "Crr": 7}
# Entry 20 anchors (journal): σ=0 uncalibrated VALIDATION med|Δ%| + the σ=0-fitted per-rider
# physics (for the E2 side-by-side; from Entry 20's run at σ=0, supplied by the work order).
E20_SIGMA0_UNCAL_VAL = {"ppaz": 8.53, "jaam": 2.64, "danlessa": 14.84}
E20_SIGMA0_FITS = {"ppaz": {"CdA": 0.2259, "Crr": 0.01344},
                   "jaam": {"CdA": 0.5519, "Crr": 0.00433},
                   "danlessa": {"CdA": 0.4148, "Crr": 0.00478}}
PLAUSIBLE = {"CdA": [0.25, 0.45], "Crr": [0.004, 0.012]}

# the .mjs's `const sampleMs = { r5: 0, r30: 0 };` injected into the eval'd engine scope, between
# the regime blocks and the igc blocks: the grabbed sampleRaster closes over it. Rebinding the
# module global of igc_resolution_test makes the imported sample_raster time into exactly this
# dict (and only these two keys are ever emitted). Must come AFTER `import goal_calibration`,
# which installs its own six-sigma dict for its own run.
IGC.sample_ms = {"r5": 0, "r30": 0}

FROZEN = {"CdA": 0.40, "Crr": 0.008}   # journal frozen physics (≡ ASSUMED CdA/Crr)


def now_ms():
    return time.time() * 1000


def p_of(corpus, CdA, Crr):
    if corpus == 'censo':
        return {**ASSUMED, "CdA": CdA, "Crr": Crr, "vmax": VMAX, "vstart": VSTART}
    return {**PHYS[corpus], "CdA": CdA, "Crr": Crr, "vmax": VMAX, "vstart": VSTART}


def p_frozen(corpus):
    return p_of(corpus, FROZEN["CdA"], FROZEN["Crr"])


def f(x, d=2):
    if x is None or not is_finite(x):
        return '—'
    return to_fixed(x, d)


def linspace(lo, hi, k):
    return [lo] if k == 1 else [lo + (hi - lo) * i / (k - 1) for i in range(k)]


# walkStatsK — diagnostics mirror of v2EdgeK (same trio generalization) that also accumulates
# the drop-weighted implied ε; E asserted ≡ v2EdgeK per call (gate).
WS_MAX_MISMATCH = 0


def walk_stats_k(prof, p, pw_flat, climb_thr, k_smooth, eps_offset):
    global WS_MAX_MISMATCH
    mg = p["m"] * G
    beta = mg * k_smooth / p["keff"]
    w = p["wind"]
    vFlat = max(0.05, flat_eq_speed(pw_flat if pw_flat > 0 else 1, p))
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) / p["keff"]
    abRatio = (aRoll + aAero) / (mg / p["keff"])
    xs, hs = prof["x"], prof["h"]
    Ej = 0.0
    hplus = 0.0
    hminus = 0.0
    epsW = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
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
            epsW += eps * ndh
            e = aRoll * dx + aAero * dx - eps * beta * ndh
            if e < 0:
                e = 0
            Ej += e
    Ekj = Ej / 1000
    ref = v2_edge_k(prof, p, pw_flat, climb_thr, k_smooth, eps_offset)
    d = abs(Ekj - ref)
    if d > WS_MAX_MISMATCH:
        WS_MAX_MISMATCH = d
    return {"E": Ekj, "hplus": hplus, "hminus": hminus,
            "epsImplied": epsW / hminus if hminus > 0 else float("nan")}


# ===== Entry-19 CSV: membership + reference values (riders AND censo) =====
csv_rides = {"ppaz": [], "jaam": [], "danlessa": [], "censo": []}

# ===== module state materialized in main() =====
g_by_key = {}
g_f64 = None
s_f64 = None
supp_meta = None
supp_by_key = {}
rides = []


# ===== SUPPLEMENTARY CACHE: rider igc30 + censo igc5/igc30 =====
def build_rider_supp(corpus, ride):
    mr = g_by_key.get(corpus + '|' + ride)
    if not mr:
        raise ValueError(f"no goal-cache entry for {corpus}/{ride}")
    with open(os.path.join(DATA, mr["file"]), "rb") as fh:
        buf0 = fh.read()
    buf = gzip.decompress(buf0) if mr["file"].endswith('.gz') else buf0
    pts = pts_from_fit(buf)
    build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof5 = resample_profile(RC.phys_profile, ENGINE_DX)
    total = prof5["x"][len(prof5["x"]) - 1]
    emp = empirical_kj(pts)
    pFlat = pw_from(bin_grades(point_regime_data(pts), CLIMB_THR, DESC_THR), pts)["flat"]
    if emp != mr["emp"] or total != mr["total"] or pFlat != mr["pFlat"]:
        raise ValueError(f"goal-meta mismatch {corpus}/{ride}: emp {js_str(emp)} vs "
                         f"{js_str(mr['emp'])}, total {js_str(total)} vs {js_str(mr['total'])}, "
                         f"pFlat {js_str(pFlat)} vs {js_str(mr['pFlat'])}")
    geo = geo_track_from_fit(buf)
    if len(geo) < 2:
        raise ValueError(f"no-geo {corpus}/{ride}")
    base = pts[0]["x"]
    d30 = grid_positions(total, 30)
    abs30 = [d + base for d in d30]
    g30 = lon_lat_at(geo, abs30)
    b = build_dem_profile(d30, sample_raster(DEM30, g30["lons"], g30["lats"], 'r30'), 0.5)
    if not b["prof"] or b["validFrac"] < 0.99:
        raise ValueError(f"igc30 coverage {corpus}/{ride}: {js_str(b['validFrac'])}")
    return {"corpus": corpus, "ride": ride, "file": mr["file"], "emp": emp, "total": total,
            "pFlat": pFlat, "n5": 0, "n30": len(d30), "h5": None, "h30": b["prof"]["h"]}


# Entry 19's censo pipeline, filters verbatim (ASSUMED rider, urban corpus: no zwift skip,
# phys-floor on, bbox + geo-span + igc5/igc30 coverage cuts). Returns None on any exclusion.
def process_censo(entry):
    p = {**ASSUMED, "vmax": VMAX, "vstart": VSTART}
    if entry["file"].endswith('.gpx') or entry["file"].endswith('.gpx.gz'):
        return None
    with open(os.path.join(DATA, entry["file"]), "rb") as fh:
        buf0 = fh.read()
    buf = gzip.decompress(buf0) if entry["file"].endswith('.gz') else buf0
    pts = pts_from_fit(buf)
    if not has_power(pts):
        return None
    build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof5 = resample_profile(RC.phys_profile, ENGINE_DX)
    total = prof5["x"][len(prof5["x"]) - 1]
    emp = empirical_kj(pts)
    if not emp > 0:
        return None
    # physical-plausibility floor, VERBATIM Entry 19 censo logic
    profS0 = {"x": prof5["x"], "h": deadband(prof5["h"], TAU_SMOOTH)}
    aSm0 = RC.approx_components(profS0, p, flat_eq_speed(overall_mean_power(pts), p), None)
    if emp < (p["m"] * G / p["keff"]) * aSm0["hplus"] / 1000:
        return None
    geo = geo_track_from_fit(buf)
    if len(geo) < 2:
        return None
    base = pts[0]["x"]
    geoCov = (min(geo[len(geo) - 1]["x"], base + total) - max(geo[0]["x"], base)) / total
    if geoCov < 0.99:
        return None
    for q in geo:
        if (q["lon"] < BBOX["lonMin"] or q["lon"] > BBOX["lonMax"]
                or q["lat"] < BBOX["latMin"] or q["lat"] > BBOX["latMax"]):
            return None
    d5, d30 = grid_positions(total, 5), grid_positions(total, 30)
    abs5 = [d + base for d in d5]
    abs30 = [d + base for d in d30]
    g5 = lon_lat_at(geo, abs5)
    g30 = lon_lat_at(geo, abs30)
    s5 = build_dem_profile(d5, sample_raster(DEM5, g5["lons"], g5["lats"], 'r5'), 0.5)
    s30 = build_dem_profile(d30, sample_raster(DEM30, g30["lons"], g30["lats"], 'r30'), 0.5)
    if (not s5["prof"] or not s30["prof"]
            or s5["validFrac"] < 0.99 or s30["validFrac"] < 0.99):
        return None
    pFlat = pw_from(bin_grades(point_regime_data(pts), CLIMB_THR, DESC_THR), pts)["flat"]
    return {"corpus": 'censo', "ride": entry.get("name"), "file": entry["file"], "emp": emp,
            "total": total, "pFlat": pFlat, "n5": len(d5), "n30": len(d30),
            "h5": s5["prof"]["h"], "h30": s30["prof"]["h"]}


def build_supp_cache():
    t0 = now_ms()
    recs = []
    done = 0
    total_rider = 0
    for c in CORPORA:
        total_rider += len(csv_rides[c])
    for corpus in CORPORA:
        for row in csv_rides[corpus]:
            recs.append(build_rider_supp(corpus, row["ride"]))
            done += 1
            if done % 50 == 0:
                print(f"  …supp cache riders {done}/{total_rider} "
                      f"({to_fixed((now_ms() - t0) / 1000, 0)} s, "
                      f"sampleMs={js_json(IGC.sample_ms)})", file=sys.stderr)
    # censo: full pipeline over the manifest (membership DERIVED, then asserted vs the CSV)
    with open(os.path.join(DATA, 'censohidrografico', 'manifest.json'), encoding="utf-8") as fh:
        man = json.load(fh)
    want_names = set(r["ride"] for r in csv_rides["censo"])
    for e in man:
        if not e.get("file") or not os.path.exists(os.path.join(DATA, e["file"])):
            continue
        if SMOKE and e.get("name") not in want_names:
            continue
        r = None
        try:
            r = process_censo(e)
        except Exception:
            pass   # unparseable — Entry 19 skipped these
        if r:
            recs.append(r)
    censo_got = [r for r in recs if r["corpus"] == 'censo']
    got_names = sorted(r["ride"] for r in censo_got)
    want_sorted = sorted(want_names)
    if js_json(got_names) != js_json(want_sorted):
        raise ValueError(f"censo membership mismatch: pipeline included "
                         f"[{'; '.join(got_names)}] vs CSV [{'; '.join(want_sorted)}]")
    # serialize
    meta_rides = []
    chunks = []
    off = 0
    for r in recs:
        meta_rides.append({"corpus": r["corpus"], "ride": r["ride"], "file": r["file"],
                           "emp": r["emp"], "total": r["total"], "pFlat": r["pFlat"],
                           "n5": r["n5"], "n30": r["n30"], "off": off})
        if r["n5"]:
            chunks.append(array('d', r["h5"]).tobytes())
        chunks.append(array('d', r["h30"]).tobytes())
        off += r["n5"] + r["n30"]
    membership = (';'.join(c + '|' + r["ride"] for c in CORPORA for r in csv_rides[c])
                  + '#' + ';'.join(want_sorted))
    meta = {"version": 1, "membership": membership, "rides": meta_rides}
    with open(SUPP_BIN, "wb") as fh:
        fh.write(b"".join(chunks))
    with open(SUPP_META, "w", encoding="utf-8") as fh:
        fh.write(js_json(meta))
    print(f"supp cache built: {len(meta_rides)} rides, {off} doubles, "
          f"{to_fixed((now_ms() - t0) / 1000, 0)} s", file=sys.stderr)
    return meta


def load_or_build_supp():
    membership = (';'.join(c + '|' + r["ride"] for c in CORPORA for r in csv_rides[c])
                  + '#' + ';'.join(sorted(r["ride"] for r in csv_rides["censo"])))
    if os.path.exists(SUPP_META) and os.path.exists(SUPP_BIN):
        with open(SUPP_META, encoding="utf-8") as fh:
            meta = json.load(fh)
        if meta["version"] == 1 and meta["membership"] == membership:
            print('supp cache: reusing existing (membership matches)', file=sys.stderr)
            return meta
        print('supp cache: stale — rebuilding', file=sys.stderr)
    return build_supp_cache()


def by_corpus(c):
    return [r for r in rides if r["corpus"] == c]


def train_of(c):
    return [r for r in by_corpus(c) if r["split"] == 'train']


def val_of(c):
    return [r for r in by_corpus(c) if r["split"] == 'val']


# supp-cache determinism: rebuild every 40th supp ride fresh (FIT parse + gdal) and compare
def supp_determinism_check():
    with open(os.path.join(DATA, 'censohidrografico', 'manifest.json'), encoding="utf-8") as fh:
        man = json.load(fh)
    checked = 0
    bad = 0
    for i in range(0, len(supp_meta["rides"]), 40):
        mr = supp_meta["rides"][i]
        if mr["corpus"] == 'censo':
            entry = next((e for e in man
                          if e.get("file") == mr["file"] and e.get("name") == mr["ride"]), None)
            fresh = process_censo(entry) if entry else None
        else:
            fresh = build_rider_supp(mr["corpus"], mr["ride"])
        if (not fresh or fresh["emp"] != mr["emp"] or fresh["pFlat"] != mr["pFlat"]
                or fresh["total"] != mr["total"] or fresh["n5"] != mr["n5"]
                or fresh["n30"] != mr["n30"]):
            bad += 1
            checked += 1
            continue
        stored5 = s_f64[mr["off"]: mr["off"] + mr["n5"]]
        stored30 = s_f64[mr["off"] + mr["n5"]: mr["off"] + mr["n5"] + mr["n30"]]
        ok = True
        for j in range(mr["n5"]):
            if fresh["h5"][j] != stored5[j]:
                ok = False
                break
        if ok:
            for j in range(mr["n30"]):
                if fresh["h30"][j] != stored30[j]:
                    ok = False
                    break
        if not ok:
            bad += 1
        checked += 1
    return {"checked": checked, "bad": bad}


# ===== STAGE-1 machinery: exact decomposition of v2EdgeK at frozen physics =====
def decompose(prof, p, pw_flat):
    mg = p["m"] * G
    mgk = mg / p["keff"]
    w = p["wind"]
    vFlat = max(0.05, flat_eq_speed(pw_flat if pw_flat > 0 else 1, p))
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) / p["keff"]
    abRatio = (aRoll + aAero) / mgk
    xs, hs = prof["x"], prof["h"]
    base = 0.0
    grav = 0.0
    ascG = []
    ascDx = []
    dEps = []
    dW = []
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        if not dx > 0:
            continue
        if dh >= 0:
            base += aRoll * dx
            grav += dh
            ascG.append(dh / dx)
            ascDx.append(dx)
        else:
            base += aRoll * dx + aAero * dx
            ndh = -dh
            eps = abRatio * dx / ndh
            if eps > 1:
                eps = 1
            dEps.append(eps)
            dW.append(mgk * ndh)
    # ascent aero: sorted grades + prefix aero-work  (JS Array#sort is stable ⇒ so is sorted());
    # the five stored series are array('d') — the exact float64 storage of the .mjs's
    # Float64Array, and the memory the per-train-ride caches need.
    ai = sorted(range(len(ascG)), key=lambda i: ascG[i])
    gArr = array('d', bytes(8 * len(ai)))
    prefAero = array('d', bytes(8 * (len(ai) + 1)))
    for k in range(len(ai)):
        gArr[k] = ascG[ai[k]]
        prefAero[k + 1] = prefAero[k] + aAero * ascDx[ai[k]]
    # descent credit: sorted epsr + suffix sums of W and epsr·W
    di = sorted(range(len(dEps)), key=lambda i: dEps[i])
    eArr = array('d', bytes(8 * len(di)))
    sufW = array('d', bytes(8 * (len(di) + 1)))
    sufEW = array('d', bytes(8 * (len(di) + 1)))
    for k in range(len(di) - 1, -1, -1):
        eArr[k] = dEps[di[k]]
        sufW[k] = sufW[k + 1] + dW[di[k]]
        sufEW[k] = sufEW[k + 1] + dEps[di[k]] * dW[di[k]]
    return {"base": base, "grav": mgk * grav, "gArr": gArr, "prefAero": prefAero,
            "eArr": eArr, "sufW": sufW, "sufEW": sufEW}


def lower_bound(a, x):
    lo, hi = 0, len(a)
    while lo < hi:
        m = (lo + hi) >> 1
        if a[m] < x:
            lo = m + 1
        else:
            hi = m
    return lo


def upper_bound(a, x):
    lo, hi = 0, len(a)
    while lo < hi:
        m = (lo + hi) >> 1
        if a[m] <= x:
            lo = m + 1
        else:
            hi = m
    return lo


def dec_eval(dec, kS, eps0, thr):
    ia = lower_bound(dec["gArr"], thr)     # ascent edges with grade < thr get aero
    id_ = upper_bound(dec["eArr"], eps0)   # descent edges with epsr > eps0 give credit
    credit = dec["sufEW"][id_] - eps0 * dec["sufW"][id_]
    return (dec["base"] + dec["prefAero"][ia] + kS * (dec["grav"] - credit)) / 1000


# deterministic coarse-to-fine grid fit (3 levels; ±1-step refinement clipped to bounds;
# strict-< improvement in fixed kS→eps0→thr order)
def fit_stage1(free_dims, objective):
    rng = {}
    for d in free_dims:
        rng[d] = [SPACE[d][0], SPACE[d][1]]
    best = None
    for _lvl in range(3):
        grids = {}
        for d in ('kS', 'eps0', 'thr'):
            grids[d] = (linspace(rng[d][0], rng[d][1], SPACE[d][2]) if d in free_dims
                        else [DEFAULTS[d]])
        best = None
        for kS in grids["kS"]:
            for eps0 in grids["eps0"]:
                for thr in grids["thr"]:
                    o = objective(kS, eps0, thr)
                    if best is None or o < best["obj"]:
                        best = {"kS": kS, "eps0": eps0, "thr": thr, "obj": o}
        for d in free_dims:
            step = (rng[d][1] - rng[d][0]) / (SPACE[d][2] - 1)
            rng[d] = [max(SPACE[d][0], best[d] - step), min(SPACE[d][1], best[d] + step)]
    return best


# E2: per-rider (CdA, Crr) fit at igc5+trio (goal_calibration's fitRider minus kSmooth; the
# trio owns kS/eps0/thr; verbatim v2EdgeK inside — K_MIN_PRECLAMP-tracked on every combo)
def fit_phys(train_set, trio):
    rng = {"CdA": list(PHYS_BOUNDS["CdA"]), "Crr": list(PHYS_BOUNDS["Crr"])}
    best = None
    for _lvl in range(3):
        grid = {"CdA": linspace(rng["CdA"][0], rng["CdA"][1], PHYS_NPTS["CdA"]),
                "Crr": linspace(rng["Crr"][0], rng["Crr"][1], PHYS_NPTS["Crr"])}
        best = None
        for cda in grid["CdA"]:
            for crr in grid["Crr"]:
                d = [d_pct(v2_edge_k(r["prof5"], p_of(r["corpus"], cda, crr), r["pFlat"],
                                     trio["thr"], trio["kS"], trio["eps0"]), r["emp"])
                     for r in train_set]
                o = {"medAbs": med_of([abs(x) for x in d]), "medSigned": med_of(d)}
                s = score_of(o)
                if best is None or s < best["score"]:
                    best = {"CdA": cda, "Crr": crr, **o, "score": s}

        def step(k, _rng=rng):
            return (_rng[k][1] - _rng[k][0]) / (PHYS_NPTS[k] - 1)

        rng = {k: [max(PHYS_BOUNDS[k][0], best[k] - step(k)),
                   min(PHYS_BOUNDS[k][1], best[k] + step(k))] for k in ('CdA', 'Crr')}
    return best


def summarize_deltas(d):
    return {"n": len(d), "medAbs": med_of([abs(x) for x in d]), "medSigned": med_of(d),
            "p10": pctl(d, 0.10), "p90": pctl(d, 0.90)}


def ratio_stats(ratios):
    return {"n": len(ratios), "med": med_of(ratios),
            "iqr": pctl(ratios, 0.75) - pctl(ratios, 0.25),
            "p10": pctl(ratios, 0.10), "p90": pctl(ratios, 0.90)}


# ===== CSV cell writer (JS: typeof 'string' → JSON.stringify; finite → +Number(v).toFixed(6);
# anything else → '') =====
def cell6(v):
    if isinstance(v, str):
        return jquote(v)
    if is_finite(v):
        return js_str(float(to_fixed(v, 6)))
    return ""


# ===== the full analysis (deterministic; run TWICE, byte-compared) =====
def run_analysis(g_bin_sha, s_bin_sha):
    global WS_MAX_MISMATCH
    GC.K_MIN_PRECLAMP = float("inf")
    WS_MAX_MISMATCH = 0
    L = []
    t0 = now_ms()

    # -- per-ride frozen-default walks (verbatim v2EdgeK) + diagnostics --
    for r in rides:
        p = p_frozen(r["corpus"])
        w5 = walk_stats_k(r["prof5"], p, r["pFlat"], DEFAULTS["thr"], DEFAULTS["kS"],
                          DEFAULTS["eps0"])
        w30 = walk_stats_k(r["prof30"], p, r["pFlat"], DEFAULTS["thr"], DEFAULTS["kS"],
                           DEFAULTS["eps0"])
        r["v2_5_def"] = w5["E"]
        r["hplus5"] = w5["hplus"]
        r["hminus5"] = w5["hminus"]
        r["epsw5_def"] = w5["epsImplied"]
        r["v2_30_def"] = w30["E"]
        r["hplus30"] = w30["hplus"]
        r["hminus30"] = w30["hminus"]
        r["epsw30_def"] = w30["epsImplied"]

    # -- STAGE 1: resolution-transfer fit on TRAIN rider rides (geometric; emp never used) --
    train_by_c = [train_of(c) for c in CORPORA]
    for st in train_by_c:
        for r in st:
            r["dec"] = decompose(r["prof5"], p_frozen(r["corpus"]), r["pFlat"])

    def objective(kS, eps0, thr):
        s = 0.0
        for st in train_by_c:
            s += med_of([abs(jsdiv(dec_eval(r["dec"], kS, eps0, thr), r["v2_30_def"]) - 1)
                         for r in st])
        return s / len(train_by_c)

    def per_corpus_obj(kS, eps0, thr):
        return [med_of([abs(jsdiv(dec_eval(r["dec"], kS, eps0, thr), r["v2_30_def"]) - 1)
                        for r in st]) for st in train_by_c]

    obj_default = objective(DEFAULTS["kS"], DEFAULTS["eps0"], DEFAULTS["thr"])
    t_fit = now_ms()
    abl = {
        "ks_only": fit_stage1(['kS'], objective),
        "eps_only": fit_stage1(['eps0'], objective),
        "ks_eps": fit_stage1(['kS', 'eps0'], objective),
        "trio": fit_stage1(['kS', 'eps0', 'thr'], objective),
    }
    print(f"  stage-1 fits: {to_fixed((now_ms() - t_fit) / 1000, 1)} s", file=sys.stderr)
    TRIO = abl["trio"]

    L.append('ENTRY 21 — scale trio (k_s, ε₀, climbThr): pure 5 m → 30 m resolution transfer')
    L.append('corpora: ' + ' '.join(f"{c}={len(by_corpus(c))}" for c in ALL_CORP)
             + ' · split (sha256 entry20:, even=train): '
             + ' · '.join(f"{c} {len(train_of(c))}/{len(val_of(c))}" for c in CORPORA)
             + ' · censo out-of-sample (never fitted)')
    L.append(f"caches: goal_profiles.bin sha256={g_bin_sha[0:16]}… supp={s_bin_sha[0:16]}…")
    L.append('')
    L.append('STAGE 1 — trio fit, objective = mean over rider corpora of train-median '
             '|v2(igc5;θ)/v2(igc30;default) − 1|')
    pcD = per_corpus_obj(DEFAULTS["kS"], DEFAULTS["eps0"], DEFAULTS["thr"])
    L.append(f"  baseline (defaults k_s=1.00 ε₀=0.130 thr=0.0200): obj={f(obj_default, 5)}"
             '  per-corpus '
             + ' '.join(f"{c}={f(pcD[i], 5)}" for i, c in enumerate(CORPORA)))
    for tag, name in (['ks_only', 'k_s only        '], ['eps_only', 'ε₀ only         '],
                      ['ks_eps', 'k_s + ε₀        '], ['trio', 'FULL TRIO       ']):
        b = abl[tag]
        pc = per_corpus_obj(b["kS"], b["eps0"], b["thr"])
        L.append(f"  {name} k_s={f(b['kS'], 4)} ε₀={f(b['eps0'], 4)} thr={f(b['thr'], 4)}"
                 f"  obj={f(b['obj'], 5)}  per-corpus "
                 + ' '.join(f"{c}={f(pc[i], 5)}" for i, c in enumerate(CORPORA)))

    # decomposition ≡ verbatim at every fitted/reported set (train rides)
    dec_worst = 0
    for kS, eps0, thr in ([[DEFAULTS["kS"], DEFAULTS["eps0"], DEFAULTS["thr"]]]
                          + [[b["kS"], b["eps0"], b["thr"]] for b in abl.values()]):
        for st in train_by_c:
            for r in st:
                a = dec_eval(r["dec"], kS, eps0, thr)
                b = v2_edge_k(r["prof5"], p_frozen(r["corpus"]), r["pFlat"], thr, kS, eps0)
                dec_worst = max(dec_worst, abs(a - b))

    # -- per-ride trio walks (verbatim) --
    for r in rides:
        w = walk_stats_k(r["prof5"], p_frozen(r["corpus"]), r["pFlat"], TRIO["thr"], TRIO["kS"],
                         TRIO["eps0"])
        r["v2_5_trio"] = w["E"]
        r["epsw5_trio"] = w["epsImplied"]
        r["ratio_def"] = jsdiv(r["v2_5_def"], r["v2_30_def"])
        r["ratio_trio"] = jsdiv(r["v2_5_trio"], r["v2_30_def"])

    # -- P4: transfer ratio distributions before/after --
    L.append('')
    L.append('P4 — per-ride ratio v2(igc5)/v2(igc30;default): median / IQR / p10 / p90')
    p4_sets = []
    for c in CORPORA:
        p4_sets.append([f"{c} train", train_of(c)])
        p4_sets.append([f"{c} val", val_of(c)])
    p4_sets.append(['censo all', by_corpus('censo')])
    for tag, st in p4_sets:
        b = ratio_stats([r["ratio_def"] for r in st])
        a = ratio_stats([r["ratio_trio"] for r in st])
        L.append(f"  {tag.ljust(15)} n={str(len(st)).rjust(3)}  "
                 f"before {f(b['med'], 4)} / {f(b['iqr'], 4)} / {f(b['p10'], 4)} / "
                 f"{f(b['p90'], 4)}   after {f(a['med'], 4)} / {f(a['iqr'], 4)} / "
                 f"{f(a['p10'], 4)} / {f(a['p90'], 4)}")

    # -- E1: gap closure on validation (censo: all rides, out-of-sample) --
    L.append('')
    L.append('E1 — VALIDATION (frozen journal physics; single frozen eval): '
             'med|Δ%| / medΔ% / p10 / p90 vs ∫P·dt')
    L.append('  ' + 'corpus'.ljust(16) + 'n'.rjust(4) + '   ' + 'igc5 default'.ljust(30)
             + 'igc30 default'.ljust(30) + 'igc5 + trio'.ljust(30)
             + 'bridged(≤1.0pp med, ≤1.5pp bias)')
    e1 = {}
    for c in ALL_CORP:
        st = by_corpus('censo') if c == 'censo' else val_of(c)
        s5 = summarize_deltas([d_pct(r["v2_5_def"], r["emp"]) for r in st])
        s30 = summarize_deltas([d_pct(r["v2_30_def"], r["emp"]) for r in st])
        sT = summarize_deltas([d_pct(r["v2_5_trio"], r["emp"]) for r in st])
        bridged = (abs(sT["medAbs"] - s30["medAbs"]) <= 1.0
                   and abs(sT["medSigned"] - s30["medSigned"]) <= 1.5)
        e1[c] = {"s5": s5, "s30": s30, "sT": sT, "bridged": bridged}

        def cell(s):
            return f"{f(s['medAbs'])} / {f(s['medSigned'])} / {f(s['p10'])} / {f(s['p90'])}"

        L.append('  ' + ('censo (o-o-s)' if c == 'censo' else c).ljust(16)
                 + str(len(st)).rjust(4) + '   ' + cell(s5).ljust(30) + cell(s30).ljust(30)
                 + cell(sT).ljust(30) + ('BRIDGED' if bridged else 'NOT BRIDGED')
                 + f" (Δmed={f(abs(sT['medAbs'] - s30['medAbs']))}pp "
                   f"Δbias={f(abs(sT['medSigned'] - s30['medSigned']))}pp)")
    e1_all_bridged = all(e1[c]["bridged"] for c in ALL_CORP)
    L.append('  E1 ENDPOINT: '
             + ('BRIDGED for all 4 corpora (P3: censo transfer holds)' if e1_all_bridged
                else 'NOT bridged for: '
                     + ', '.join(c for c in ALL_CORP if not e1[c]["bridged"])))

    # -- E2: per-rider physics coherence at igc5+trio --
    L.append('')
    L.append('E2 — per-rider (CdA, Crr) fit ONLY (trio + mass frozen), '
             'train fit → single validation eval')
    e2 = {}
    for c in CORPORA:
        t_e2 = now_ms()
        b = fit_phys(train_of(c), TRIO)
        print(f"  E2 fit {c}: {to_fixed((now_ms() - t_e2) / 1000, 1)} s → "
              f"CdA={f(b['CdA'], 4)} Crr={f(b['Crr'], 5)}", file=sys.stderr)
        d_val = [d_pct(v2_edge_k(r["prof5"], p_of(c, b["CdA"], b["Crr"]), r["pFlat"],
                                 TRIO["thr"], TRIO["kS"], TRIO["eps0"]), r["emp"])
                 for r in val_of(c)]
        sv = summarize_deltas(d_val)
        e2[c] = {"fit": b, "val": sv}
        for r in by_corpus(c):   # per-ride E2 prediction for the CSV
            r["cda_e2"] = b["CdA"]
            r["crr_e2"] = b["Crr"]
            r["v2_e2"] = v2_edge_k(r["prof5"], p_of(c, b["CdA"], b["Crr"]), r["pFlat"],
                                   TRIO["thr"], TRIO["kS"], TRIO["eps0"])

        def in_r(v, lohi):
            return v >= lohi[0] and v <= lohi[1]

        e20 = E20_SIGMA0_FITS[c]
        L.append(f"  {c.ljust(9)} fitted CdA={f(b['CdA'], 4)} Crr={f(b['Crr'], 5)} "
                 f"(train med|Δ%|={f(b['medAbs'])} medΔ%={f(b['medSigned'])})")
        L.append(f"  {''.ljust(9)} validation n={sv['n']}: med|Δ%|={f(sv['medAbs'])} "
                 f"medΔ%={f(sv['medSigned'])} p10={f(sv['p10'])} p90={f(sv['p90'])}  "
                 f"gate(<5 ∧ <±2): "
                 + ('PASS' if (sv["medAbs"] < 5 and abs(sv["medSigned"]) < 2) else 'FAIL'))
        L.append(f"  {''.ljust(9)} vs Entry-20 σ=0 fit CdA={f(e20['CdA'], 4)} "
                 f"Crr={f(e20['Crr'], 5)} · plausible (CdA 0.25–0.45, Crr 0.004–0.012): now CdA "
                 + ('IN' if in_r(b["CdA"], PLAUSIBLE["CdA"]) else 'OUT') + '/Crr '
                 + ('IN' if in_r(b["Crr"], PLAUSIBLE["Crr"]) else 'OUT') + ', was CdA '
                 + ('IN' if in_r(e20["CdA"], PLAUSIBLE["CdA"]) else 'OUT') + '/Crr '
                 + ('IN' if in_r(e20["Crr"], PLAUSIBLE["Crr"]) else 'OUT'))
    e2_all_pass = all(e2[c]["val"]["medAbs"] < 5 and abs(e2[c]["val"]["medSigned"]) < 2
                      for c in CORPORA)
    L.append('  E2 ENDPOINT: '
             + ('PASS (all riders meet med|Δ%|<5 ∧ |medΔ%|<2)' if e2_all_pass
                else 'FAIL for: ' + ', '.join(
                    c for c in CORPORA
                    if not (e2[c]["val"]["medAbs"] < 5 and abs(e2[c]["val"]["medSigned"]) < 2))))

    # -- P1: implied drop-weighted ε (median of per-ride drop-weighted ε, Entry-19 convention) --
    L.append('')
    L.append('P1 — implied drop-weighted ε (median per-ride): igc30@default vs igc5@default '
             'vs igc5@trio(ε₀*)')
    pooled = [r for r in rides if r["corpus"] != 'censo']
    for tag, st in [[c, by_corpus(c)] for c in ALL_CORP] + [['pooled riders', pooled]]:
        L.append(f"  {tag.ljust(14)} igc30 {f(med_of([r['epsw30_def'] for r in st]), 3)} · "
                 f"igc5@default {f(med_of([r['epsw5_def'] for r in st]), 3)} · "
                 f"igc5@trio {f(med_of([r['epsw5_trio'] for r in st]), 3)}")

    # -- P2: fitted k_s vs h₊ resolution ratio --
    L.append('')
    L.append('P2 — fitted k_s vs median per-ride h₊(igc30)/h₊(igc5)')
    for tag, st in [[c, by_corpus(c)] for c in ALL_CORP] + [['pooled riders', pooled]]:
        L.append(f"  {tag.ljust(14)} med h₊ ratio="
                 f"{f(med_of([jsdiv(r['hplus30'], r['hplus5']) for r in st]), 4)}"
                 f"  (h₊ med: igc5 {f(med_of([r['hplus5'] for r in st]), 0)} m · "
                 f"igc30 {f(med_of([r['hplus30'] for r in st]), 0)} m)")
    L.append(f"  fitted k_s = {f(TRIO['kS'], 4)} (trio) / {f(abl['ks_only']['kS'], 4)} "
             '(k_s-only ablation)')

    # -- dead-clamp: exact corner of the stage-1 grid (k_s=1, ε₀=0 IS evaluated; per-edge cost is
    # monotone ↓ in k_s and ↑ in ε₀, so this corner bounds every other stage-1 combo from below) --
    tracked = GC.K_MIN_PRECLAMP     # every verbatim walk so far (defaults, trio, E2 grid)
    GC.K_MIN_PRECLAMP = float("inf")
    for st in train_by_c:
        for r in st:
            v2_edge_k(r["prof5"], p_frozen(r["corpus"]), r["pFlat"], 0.01, 1.0, 0.0)
    corner_min = GC.K_MIN_PRECLAMP
    GC.K_MIN_PRECLAMP = min(tracked, corner_min)
    L.append('')
    L.append('dead-clamp: min pre-clamp descent edge — reported/fitted parameter sets '
             f"(verbatim walks): {to_exponential(tracked, 3)} J")
    L.append('            stage-1 grid corner (k_s=1, ε₀=0; bounds all evaluated stage-1 '
             f"combos): {to_exponential(corner_min, 3)} J")

    # per-ride CSV (deterministic; compared across the two runs)
    cols = ['corpus', 'ride', 'split', 'emp', 'km', 'pflat',
            'v2_igc5_def', 'v2_igc30_def', 'v2_igc5_trio', 'd_igc5_def', 'd_igc30_def',
            'd_igc5_trio', 'ratio_def', 'ratio_trio', 'hplus_igc5', 'hminus_igc5',
            'hplus_igc30', 'hminus_igc30', 'epsw_igc5_def', 'epsw_igc30_def', 'epsw_igc5_trio',
            'cda_e2', 'crr_e2', 'v2_e2', 'd_e2']
    csv_lines = [",".join(cols)]
    for r in rides:
        rec = {"corpus": r["corpus"], "ride": r["ride"], "split": r["split"], "emp": r["emp"],
               "km": r["total"] / 1000, "pflat": r["pFlat"],
               "v2_igc5_def": r["v2_5_def"], "v2_igc30_def": r["v2_30_def"],
               "v2_igc5_trio": r["v2_5_trio"],
               "d_igc5_def": d_pct(r["v2_5_def"], r["emp"]),
               "d_igc30_def": d_pct(r["v2_30_def"], r["emp"]),
               "d_igc5_trio": d_pct(r["v2_5_trio"], r["emp"]),
               "ratio_def": r["ratio_def"], "ratio_trio": r["ratio_trio"],
               "hplus_igc5": r["hplus5"], "hminus_igc5": r["hminus5"],
               "hplus_igc30": r["hplus30"], "hminus_igc30": r["hminus30"],
               "epsw_igc5_def": r["epsw5_def"], "epsw_igc30_def": r["epsw30_def"],
               "epsw_igc5_trio": r["epsw5_trio"],
               "cda_e2": r.get("cda_e2"), "crr_e2": r.get("crr_e2"), "v2_e2": r.get("v2_e2"),
               "d_e2": (d_pct(r["v2_e2"], r["emp"]) if r.get("v2_e2") is not None
                        else float("nan"))}
        csv_lines.append(",".join(cell6(rec.get(k)) for k in cols))

    print(f"analysis pass: {to_fixed((now_ms() - t0) / 1000, 1)} s", file=sys.stderr)
    return {"report": "\n".join(L), "csv": "\n".join(csv_lines) + "\n", "abl": abl, "TRIO": TRIO,
            "e1": e1, "e2": e2, "e1AllBridged": e1_all_bridged, "e2AllPass": e2_all_pass,
            "decWorst": dec_worst, "trackedMin": tracked, "cornerMin": corner_min,
            "wsMax": WS_MAX_MISMATCH, "objDefault": obj_default}


def main():
    global g_by_key, g_f64, s_f64, supp_meta, supp_by_key
    os.makedirs(RESULTS, exist_ok=True)

    # ===== Entry-19 CSV: membership + reference values (riders AND censo) =====
    with open(os.path.join(RESULTS, 'igc_resolution_test.csv'), encoding="utf-8") as fh:
        ref_csv = parse_csv(fh.read())
    ref_hdr = ref_csv[0]

    def ref_idx(k):
        return ref_hdr.index(k) if k in ref_hdr else -1

    def at(cells, i):
        return cells[i] if 0 <= i < len(cells) else None

    for i in range(1, len(ref_csv)):
        c = ref_csv[i]
        corpus = at(c, ref_idx('corpus'))
        if corpus not in csv_rides:
            continue
        csv_rides[corpus].append({"ride": at(c, ref_idx('ride')),
                                  "emp": js_plus(at(c, ref_idx('emp'))),
                                  "v2_igc5": js_plus(at(c, ref_idx('v2_igc5'))),
                                  "v2_igc30": js_plus(at(c, ref_idx('v2_igc30'))),
                                  "km": js_plus(at(c, ref_idx('km')))})
    if SMOKE:
        for c in ALL_CORP:
            csv_rides[c] = csv_rides[c][0:3]

    # ===== Entry-20 goal cache (rider igc5 σ=0 profiles + emp/pFlat/total) =====
    with open(GOAL_META, encoding="utf-8") as fh:
        g_meta = json.load(fh)
    if not SMOKE:
        want = ";".join(c + '|' + r["ride"] for c in CORPORA for r in csv_rides[c])
        have = ";".join(r["corpus"] + '|' + r["ride"] for r in g_meta["rides"])
        if want != have:
            raise ValueError('goal_profiles cache membership does not match Entry-19 CSV rider '
                             'sets — rebuild it with goal_calibration.mjs first')
        if g_meta["version"] != 1 or g_meta["sigmas"][0] != 0 or g_meta["engineDx"] != 5:
            raise ValueError('unexpected goal cache format')
    with open(GOAL_BIN, "rb") as fh:
        g_buf = fh.read()
    g_f64 = array('d')
    g_f64.frombytes(g_buf)
    g_by_key = {r["corpus"] + '|' + r["ride"]: r for r in g_meta["rides"]}

    # ===== raster prep (idempotent; Entry 19's recipe) =====
    os.makedirs(SCRATCH, exist_ok=True)
    if not os.path.exists(DEM30):
        print('creating 30 m warp (Entry 19 recipe)…', file=sys.stderr)
        subprocess.run(['gdalwarp', '-r', 'average', '-tr', '0.000287042610744',
                        '0.000287042610744', DEM5, DEM30],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=True)

    supp_meta = load_or_build_supp()
    with open(SUPP_BIN, "rb") as fh:
        s_buf = fh.read()
    s_f64 = array('d')
    s_f64.frombytes(s_buf)
    supp_by_key = {r["corpus"] + '|' + r["ride"]: r for r in supp_meta["rides"]}
    g_bin_sha = hashlib.sha256(g_buf).hexdigest()
    s_bin_sha = hashlib.sha256(s_buf).hexdigest()
    del g_buf, s_buf

    # ===== materialize rides =====
    for corpus in ALL_CORP:
        for row in csv_rides[corpus]:
            sr = supp_by_key.get(corpus + '|' + row["ride"])
            if not sr:
                raise ValueError(f"supp cache missing {corpus}/{row['ride']}")
            if corpus == 'censo':
                prof5 = {"x": grid_positions(sr["total"], 5),
                         "h": list(s_f64[sr["off"]: sr["off"] + sr["n5"]])}
            else:
                mr = g_by_key.get(corpus + '|' + row["ride"])
                if not mr:
                    raise ValueError(f"goal cache missing {corpus}/{row['ride']}")
                if (mr["total"] != sr["total"] or mr["emp"] != sr["emp"]
                        or mr["pFlat"] != sr["pFlat"]):
                    raise ValueError(f"goal/supp meta drift {corpus}/{row['ride']}")
                prof5 = {"x": grid_positions(mr["total"], 5),
                         "h": list(g_f64[mr["off"]: mr["off"] + mr["n"]])}   # σ=0 slice
            prof30 = {"x": grid_positions(sr["total"], 30),
                      "h": list(s_f64[sr["off"] + sr["n5"]:
                                      sr["off"] + sr["n5"] + sr["n30"]])}
            if len(prof5["x"]) != len(prof5["h"]) or len(prof30["x"]) != sr["n30"]:
                raise ValueError(f"grid mismatch {corpus}/{row['ride']}")
            rides.append({"corpus": corpus, "ride": row["ride"],
                          "split": 'censo' if corpus == 'censo'
                                   else ('train' if is_train(row["ride"]) else 'val'),
                          "emp": sr["emp"], "pFlat": sr["pFlat"], "total": sr["total"],
                          "csv": row, "prof5": prof5, "prof30": prof30})
    g_f64 = None   # the .mjs keeps gF64 alive; here the profiles are already materialized

    # ===== gates + runs =====
    gates = []

    def gate(name, passed, extra=''):
        gates.append({"name": name, "pass": passed, "extra": extra})

    gate('corpus counts = 277/181/406/58',
         SMOKE or all(len(by_corpus(c)) == EXPECT[c] for c in ALL_CORP),
         ' '.join(f"{c}={len(by_corpus(c))}" for c in ALL_CORP))

    # Entry-19 CSV reproduction at frozen default physics — riders igc5 (Entry-20 gate redux),
    # riders igc30 (validates the NEW supp cache), censo igc5+igc30 (the pre-registered censo
    # gate), censo emp; plus r1dV2Edge ≡ v2EdgeK(1, 0.13) spot equivalence on every censo profile.
    w5 = w30 = wc5 = wc30 = wEmp = wEq = 0
    what5 = what30 = whatc5 = whatc30 = ''
    for r in rides:
        p = p_frozen(r["corpus"])
        a5 = v2_edge_k(r["prof5"], p, r["pFlat"], CLIMB_THR, 1.0, 0.13)
        a30 = v2_edge_k(r["prof30"], p, r["pFlat"], CLIMB_THR, 1.0, 0.13)
        d5 = abs(a5 - r["csv"]["v2_igc5"])
        d30 = abs(a30 - r["csv"]["v2_igc30"])
        if r["corpus"] == 'censo':
            if d5 > wc5:
                wc5 = d5
                whatc5 = r["ride"]
            if d30 > wc30:
                wc30 = d30
                whatc30 = r["ride"]
            wEmp = max(wEmp, abs(r["emp"] - r["csv"]["emp"]))
            wEq = max(wEq, abs(a5 - r1d_v2_edge(r["prof5"], p, {"flat": r["pFlat"]}, CLIMB_THR)))
        else:
            if d5 > w5:
                w5 = d5
                what5 = f"{r['corpus']}/{r['ride']}"
            if d30 > w30:
                w30 = d30
                what30 = f"{r['corpus']}/{r['ride']}"
    gate('riders v2@igc5 frozen ≡ Entry-19 CSV v2_igc5 (tol 1e-3 kJ)', w5 < 1e-3,
         f"worst {to_exponential(w5, 2)} kJ ({what5})")
    gate('riders v2@igc30 frozen ≡ Entry-19 CSV v2_igc30 (tol 1e-3 kJ)', w30 < 1e-3,
         f"worst {to_exponential(w30, 2)} kJ ({what30})")
    gate('censo v2@igc5 frozen ≡ Entry-19 CSV (tol 1e-3 kJ)', wc5 < 1e-3,
         f"worst {to_exponential(wc5, 2)} kJ ({whatc5})")
    gate('censo v2@igc30 frozen ≡ Entry-19 CSV (tol 1e-3 kJ)', wc30 < 1e-3,
         f"worst {to_exponential(wc30, 2)} kJ ({whatc30})")
    gate('censo emp ≡ Entry-19 CSV (tol 1e-3 kJ)', wEmp < 1e-3,
         f"worst {to_exponential(wEmp, 2)} kJ")
    gate('v2EdgeK(1, 0.13) ≡ r1dV2Edge on censo igc5 profiles', wEq < 1e-9,
         f"max {to_exponential(wEq, 2)} kJ")

    # Entry-20 σ=0 uncalibrated VALIDATION reproduction (the igc5-frozen anchor)
    worst = 0
    got = {}
    for c in CORPORA:
        d = [d_pct(v2_edge_k(r["prof5"], p_frozen(c), r["pFlat"], CLIMB_THR, 1.0, 0.13),
                   r["emp"]) for r in val_of(c)]
        got[c] = med_of([abs(x) for x in d])
        worst = max(worst, abs(got[c] - E20_SIGMA0_UNCAL_VAL[c]))
    gate('Entry-20 σ=0 uncalibrated validation med|Δ%| ≡ 8.53/2.64/14.84 (tol 0.01)',
         SMOKE or worst < 0.01, ' '.join(f"{c}={f(got[c], 3)}" for c in CORPORA))

    # supp cache determinism (subset rebuild, byte-identical)
    t0 = now_ms()
    cd = supp_determinism_check()
    print(f"supp cache determinism subset check: {cd['checked']} rides, "
          f"{to_fixed((now_ms() - t0) / 1000, 0)} s", file=sys.stderr)
    gate('supp cache determinism (every-40th-ride rebuild byte-identical)', cd["bad"] == 0,
         f"{cd['checked']} rides rechecked, {cd['bad']} mismatches")

    print('analysis run 1…', file=sys.stderr)
    run1 = run_analysis(g_bin_sha, s_bin_sha)
    print('analysis run 2…', file=sys.stderr)
    run2 = run_analysis(g_bin_sha, s_bin_sha)
    gate('determinism: full analysis ×2 → identical report + CSV',
         run1["report"] == run2["report"] and run1["csv"] == run2["csv"],
         f"report sha {sha256hex(run1['report'])[0:12]}/{sha256hex(run2['report'])[0:12]} · "
         f"csv sha {sha256hex(run1['csv'])[0:12]}/{sha256hex(run2['csv'])[0:12]}")
    gate('stage-1 decomposition ≡ verbatim v2EdgeK at all fitted/reported sets (tol 1e-6 kJ)',
         run1["decWorst"] < 1e-6, f"max |Δ| {to_exponential(run1['decWorst'], 2)} kJ")
    gate('walkStatsK ≡ v2EdgeK on every diagnostic walk', run1["wsMax"] < 1e-9,
         f"max |Δ| {to_exponential(run1['wsMax'], 2)} kJ")
    gate('dead-clamp: min pre-clamp > 0 at reported/fitted parameter sets',
         run1["trackedMin"] > 0,
         f"min {to_exponential(run1['trackedMin'], 3)} J · stage-1 grid corner (k_s=1, ε₀=0) "
         f"exact min {to_exponential(run1['cornerMin'], 3)} J"
         + (' (degenerate corner: cost is exactly 0 in real arithmetic there — fp ulps)'
            if run1["cornerMin"] <= 0 else ''))

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

    with open(os.path.join(RESULTS, 'scale_trio.csv'), "w", encoding="utf-8") as fh:
        fh.write(run1["csv"])
    print(f"\nwrote scale_trio.csv ({len(rides)} rides) · sampleMs={js_json(IGC.sample_ms)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
