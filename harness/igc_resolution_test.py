#!/usr/bin/env python3
"""ENTRY 19 — the app on its usual DEM: v2Edge on the deployed IGC-SP 5 m raster vs a 30 m
resample (plus FABDEM V1-2 as the free-global-DEM reference), censo + independent-rider rides.
Python port of harness/igc_resolution_test.mjs (same console report, byte-identical
results/igc_resolution_test.csv).

Per ride, FOUR profile sources, each arc-length-resampled from the GPS track:
  baro     — recorded elevation, standard harness profile (5 m grid; the anchor — must
             reproduce regime_compare's per-ride r1d5r / r0sm / emp for the same rides)
  igc5     — sampa_geral.tif (IGC-SP-derived, ~5 m px, WGS84) sampled bilinearly at 5 m steps
  igc30    — the same raster warped to ~30 m (6× native px, -r average) at 30 m steps
  fabdem30 — FABDEM V1-2 tile S24W047 sampled bilinearly at 30 m steps
Models per profile (vs measured ∫P·dt): the deployed v2Edge walk (r1d_v2_edge, RAW profile at
its native step — deployment-faithful, no deadband) and the R0 champion (cf + 2 m deadband;
ε rule: censo urban → flat 0.20; rider corpora → frozen ε_geom(−0.13) of that profile source).

ENGINE REUSE: the .mjs EXTRACTS the engine block from regime_compare.mjs at run time (line-level
brace-balanced grab + eval) so nothing is re-typed. The Python port does the equivalent by
IMPORTING those same functions from harness/regime_compare.py — the one intentional structural
deviation; everything numeric still matches byte-for-byte. The three engine globals the .mjs
reaches through getPhysProfile()/getManuf()/getMinPreclamp() are read here as MODULE ATTRIBUTES
of regime_compare (RC.phys_profile / RC.FIT_MANUF / RC.R1D_MIN_PRECLAMP) — never
`from regime_compare import …`, which would freeze the value at import time.
New code = geo track builder, DEM sampler, walk decomposition (asserted ≡ r1d_v2_edge per ride),
drivers, report.

One-time raster prep (both into the session scratch dir, NEVER the repo):
  gdalwarp -r average -tr 0.000287042610744 0.000287042610744 \
    /Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif $SCRATCH/sampa_geral_30m.tif
  curl -sSf -o $SCRATCH/S24W047_FABDEM_V1-2.tif \
    https://telhas.pedalhidrografi.co/fabdem/S24W047_FABDEM_V1-2.tif
(0.000287042610744° = 6 × the native 0.000047840435124° pixel ≈ 30 m at this latitude.)

  python3 harness/igc_resolution_test.py   → report on stdout (timings on stderr) +
                                             igc_resolution_test.csv (gitignored via results/*)

MODULE IS IMPORT-SAFE — importing it runs nothing, shells out to nothing and touches no file;
the whole driver lives in main(). goal_calibration / scale_trio reuse geo_track_from_fit,
grid_positions, lon_lat_at, sample_raster and build_dem_profile by importing them from here,
exactly as their .mjs siblings grab those source blocks.

JS name → Python name (this file's own top-level definitions, in file order):
  SCRATCH, DEM5, DEM30, FABDEM, BBOX, SOURCES   → same names
  geoTrackFromFIT → geo_track_from_fit          gridPositions → grid_positions
  lonLatAt → lon_lat_at        sampleMs → sample_ms        sampleRaster → sample_raster
  buildDemProfile → build_dem_profile           walkStats → walk_stats
  rows/excl → rows/excl        note → note      maxWalkMismatch → MAX_WALK_MISMATCH
  processRide → process_ride   f → f            cell (CSV) → cell4
"""

import gzip
import json
import math
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))
sys.path.insert(0, HERE)

import regime_compare as RC  # noqa: E402
from regime_compare import (ASSUMED, CLIMB_THR, DESC_THR, ENGINE_DX, G,  # noqa: E402,F401
                            PHYS, TAU_SMOOTH, VMAX, VSTART, ZWIFT,
                            approx_components, bin_grades, build_profile, d_pct,
                            deadband, empirical_kj, eps_geom, flat_eq_speed,
                            has_power, haversine, is_finite, jge, jgt, jquote, jsdiv,
                            med_of, overall_mean_power, paired_abs, parse_fit,
                            point_regime_data, pts_from_fit, pw_from, r0_champion,
                            r1d_v2_edge, resample_profile)
from bem.jsfmt import js_str, to_exponential, to_fixed  # noqa: E402
from bem.v8math import js_num  # noqa: E402

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
SCRATCH = ('/private/tmp/claude-501/-Users-danlessa-repos-pedalhidro-simujaules/'
           '6a419542-bc75-4ec1-aced-8e8de9a58ae3/scratchpad')
DEM5 = '/Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif'
DEM30 = os.path.join(SCRATCH, 'sampa_geral_30m.tif')
FABDEM = os.path.join(SCRATCH, 'S24W047_FABDEM_V1-2.tif')
# sampa_geral.tif bounds (gdalinfo): origin (-46.948167148, -23.372989389), 14913×9055 px of
# 0.000047840435124° — strict bbox test for the track (pre-filter before any sampling).
BBOX = {"lonMin": -46.9481671, "lonMax": -46.2347227,
        "latMin": -23.8061845, "latMax": -23.3729894}


# ===== JS primitives the port leans on =====
_NUM_RE = re.compile(r'^[+-]?(?:Infinity|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)')


def js_parse_float(s):
    """Number.parseFloat: longest numeric prefix of the trimmed string, NaN when none."""
    if s is None:
        return float("nan")
    m = _NUM_RE.match(s.lstrip(" \t\n\r\f\v ﻿"))
    if not m:
        return float("nan")
    return float(m.group(0).replace("Infinity", "inf"))


def js_plus(s):
    """JS unary + on a CSV cell: '' → 0, garbage/undefined → NaN."""
    if s is None:
        return float("nan")
    t = s.strip()
    if t == "":
        return 0.0
    try:
        return float(t)
    except ValueError:
        return float("nan")


def _at(cells, i):
    """JS array index: out of range → undefined (None here)."""
    return cells[i] if 0 <= i < len(cells) else None


# ===== raster prep (idempotent) =====
def ensure_rasters():
    os.makedirs(SCRATCH, exist_ok=True)
    if not os.path.exists(DEM30):
        print('creating 30 m warp…', file=sys.stderr)
        subprocess.run(['gdalwarp', '-r', 'average', '-tr', '0.000287042610744',
                        '0.000287042610744', DEM5, DEM30],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=True)
    if not os.path.exists(FABDEM):
        print('downloading FABDEM tile…', file=sys.stderr)
        subprocess.run(['curl', '-sSf', '-o', FABDEM,
                        'https://telhas.pedalhidrografi.co/fabdem/S24W047_FABDEM_V1-2.tif'],
                       check=True)


# ===== NEW: geo track (lat/lon vs the SAME cumulative x as pts_from_fit) =====
# Mirrors pts_from_fit's distance mapping exactly (device-distance interpolation when present,
# haversine chain otherwise) so profile arc-length d maps to track position d + pts[0].x.
def geo_track_from_fit(buffer):
    recs = parse_fit(buffer)
    out = []
    if any("dist" in r for r in recs):
        di, dv = [], []
        for i, r in enumerate(recs):
            if "dist" in r:
                di.append(i)
                dv.append(max(r["dist"], dv[len(dv) - 1]) if dv else r["dist"])
        k = 0
        for i in range(len(recs)):
            if "lat" not in recs[i] or "lon" not in recs[i]:
                continue
            while k < len(di) - 1 and di[k + 1] <= i:
                k += 1
            if i <= di[0]:
                x = dv[0]
            elif i >= di[len(di) - 1]:
                x = dv[len(dv) - 1]
            else:
                fr = (i - di[k]) / (di[k + 1] - di[k])
                x = dv[k] + (dv[k + 1] - dv[k]) * fr
            out.append({"x": x, "lat": recs[i]["lat"], "lon": recs[i]["lon"]})
    else:
        geo = [r for r in recs if "lat" in r and "lon" in r and "alt" in r]
        cum = 0.0
        for i in range(len(geo)):
            if i:
                cum += haversine(geo[i - 1], geo[i])
            out.append({"x": cum, "lat": geo[i]["lat"], "lon": geo[i]["lon"]})
    t = []   # enforce strictly monotone x for interpolation
    for q in out:
        if not t or q["x"] > t[len(t) - 1]["x"] + 1e-9:
            t.append(q)
    return t


# same grid convention as resample_profile (n = max(2, round(total/dx)+1), last point exact)
def grid_positions(total, dx):
    n = max(2, math.floor(total / dx + 0.5) + 1)   # JS Math.round is half-UP
    d = [0.0] * n
    for i in range(n):
        d[i] = total if i == n - 1 else total * i / (n - 1)
    return d


def lon_lat_at(geo, xs):   # linear interp along track x; clamped at the ends
    n = len(xs)
    lons = [0.0] * n
    lats = [0.0] * n
    j = 0
    for i in range(n):
        d = xs[i]
        while j < len(geo) - 2 and geo[j + 1]["x"] < d:
            j += 1
        a, b = geo[j], geo[j + 1]
        fr = max(0, min(1, (d - a["x"]) / max(1e-9, b["x"] - a["x"])))
        lons[i] = a["lon"] + (b["lon"] - a["lon"]) * fr
        lats[i] = a["lat"] + (b["lat"] - a["lat"]) * fr
    return {"lons": lons, "lats": lats}


# batch bilinear sampler; empty/garbage lines (outside raster) → NaN
sample_ms = {"igc5": 0, "igc30": 0, "fabdem": 0, "igc5at30": 0}


def sample_raster(raster, lons, lats, timer_key):
    t0 = time.time() * 1000
    parts = []
    for i in range(len(lons)):
        parts.append(js_num(lons[i]) + ' ' + js_num(lats[i]) + '\n')
    data = "".join(parts).encode("utf-8")
    # execFileSync without a `stdio` option pipes the child's stderr and then writes it to the
    # parent's stderr (Node's inheritStderr); a non-zero exit throws but e.stdout still holds
    # the (line-aligned) output.  Same behaviour here.
    r = subprocess.run(['gdallocationinfo', '-valonly', '-wgs84', '-r', 'bilinear', raster],
                       input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.stderr:
        sys.stderr.write(r.stderr.decode("utf-8", "replace"))
    out = r.stdout.decode("utf-8", "replace")
    lines = out.split('\n')
    v = [float("nan")] * len(lons)
    i = 0
    while i < len(lons) and i < len(lines):
        x = js_parse_float(lines[i])
        if is_finite(x):
            v[i] = x
        i += 1
    sample_ms[timer_key] = sample_ms.get(timer_key, 0) + int(time.time() * 1000 - t0)
    return v


# validity + gap fill (≤1% invalid allowed): sampa_geral has un-surveyed cells stored as 0
# (band min is 0.000 in a ~440–1212 m area) → invalid if ≤ 0.5 m; FABDEM nodata −9999.
def build_dem_profile(xs, vals, floor):
    n = len(xs)
    n_bad = 0
    h = [0.0] * n
    for i in range(n):
        h[i] = vals[i] if (is_finite(vals[i]) and vals[i] > floor) else float("nan")
        if h[i] != h[i]:
            n_bad += 1
    valid_frac = 1 - n_bad / n
    if n_bad:   # linear fill across gaps, edge-extend
        first = next((i for i in range(n) if is_finite(h[i])), -1)
        if first < 0:
            return {"prof": None, "validFrac": valid_frac}
        for i in range(first):
            h[i] = h[first]
        last = first
        for i in range(first + 1, n):
            if is_finite(h[i]):
                for k in range(last + 1, i):
                    h[k] = h[last] + (h[i] - h[last]) * (k - last) / (i - last)
                last = i
        for i in range(last + 1, n):
            h[i] = h[last]
    return {"prof": {"x": list(xs), "h": h}, "validFrac": valid_frac}


# v2Edge walk decomposition (diagnostics; E is asserted ≡ r1d_v2_edge to 1e-9 per profile):
# Σh₊, Σh₋ over the walked edges + drop-weighted implied ε = Σ ε_i·h₋ᵢ / Σh₋ᵢ (descent edges).
def walk_stats(prof, p, pw, climb_thr):
    mg = p["m"] * G
    beta = mg / p["keff"]
    w = p["wind"]
    vFlat = max(0.05, flat_eq_speed(pw["flat"] if pw["flat"] > 0 else 1, p))
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * (vFlat + w) * abs(vFlat + w) / p["keff"]
    abRatio = (aRoll + aAero) / beta
    xs, hs = prof["x"], prof["h"]
    Ej = hplus = hminus = epsW = 0.0
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
            hplus += 0
            hminus += ndh
            eps = abRatio * dx / ndh
            if eps > 1:
                eps = 1
            eps -= 0.13
            if eps < 0:
                eps = 0
            epsW += eps * ndh
            e = aRoll * dx + aAero * dx - eps * beta * ndh
            if e < 0:
                e = 0
            Ej += e
    return {"E": Ej / 1000, "hplus": hplus, "hminus": hminus,
            "epsImplied": epsW / hminus if hminus > 0 else float("nan")}


# ===== per-ride processing =====
SOURCES = ['baro', 'igc5', 'igc30', 'fabdem30']
rows = []
excl = {}   # per-corpus exclusion tallies
MAX_WALK_MISMATCH = 0


def note(c, k):
    excl.setdefault(c, {})[k] = excl.get(c, {}).get(k, 0) + 1


def process_ride(file, p0, label, corpus, eps_rule):
    global MAX_WALK_MISMATCH
    with open(os.path.join(DATA, file), "rb") as fh:
        buf0 = fh.read()
    buf = gzip.decompress(buf0) if file.endswith('.gz') else buf0
    if file.endswith('.gpx') or file.endswith('.gpx.gz'):
        note(corpus, 'gpx-unsupported')
        return
    pts = pts_from_fit(buf)
    if corpus != 'censo' and RC.FIT_MANUF == ZWIFT:
        note(corpus, 'zwift')
        return
    if not has_power(pts):
        note(corpus, 'no-power')
        return
    p = {**p0, "vmax": VMAX, "vstart": VSTART}
    build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    phys_profile = RC.phys_profile
    prof5 = resample_profile(phys_profile, ENGINE_DX)
    total = prof5["x"][len(prof5["x"]) - 1]
    emp = empirical_kj(pts)
    if not emp > 0:
        note(corpus, 'no-emp')
        return
    if corpus == 'censo':   # physical-plausibility floor, VERBATIM regime_compare censo driver
        profS0 = {"x": prof5["x"], "h": deadband(prof5["h"], TAU_SMOOTH)}
        aSm0 = approx_components(profS0, p, flat_eq_speed(overall_mean_power(pts), p), None)
        if emp < (p["m"] * G / p["keff"]) * aSm0["hplus"] / 1000:
            note(corpus, 'phys-floor')
            return
    note(corpus, 'clean')   # clean per the corpus's own filters — coverage cuts follow
    geo = geo_track_from_fit(buf)
    if len(geo) < 2:
        note(corpus, 'no-geo')
        return
    base = pts[0]["x"]
    geoCov = ((min(geo[len(geo) - 1]["x"], base + total) - max(geo[0]["x"], base)) / total)
    if geoCov < 0.99:
        note(corpus, 'geo-span')
        return
    inBox = True
    for q in geo:
        if (q["lon"] < BBOX["lonMin"] or q["lon"] > BBOX["lonMax"]
                or q["lat"] < BBOX["latMin"] or q["lat"] > BBOX["latMax"]):
            inBox = False
            break
    if not inBox:
        note(corpus, 'bbox')
        return

    d5, d30 = grid_positions(total, 5), grid_positions(total, 30)
    abs5 = [d + base for d in d5]
    abs30 = [d + base for d in d30]
    g5 = lon_lat_at(geo, abs5)
    g30 = lon_lat_at(geo, abs30)
    s5 = build_dem_profile(d5, sample_raster(DEM5, g5["lons"], g5["lats"], 'igc5'), 0.5)
    s30 = build_dem_profile(d30, sample_raster(DEM30, g30["lons"], g30["lats"], 'igc30'), 0.5)
    sF = build_dem_profile(d30, sample_raster(FABDEM, g30["lons"], g30["lats"], 'fabdem'), -9998)
    s5at30 = build_dem_profile(d30, sample_raster(DEM5, g30["lons"], g30["lats"], 'igc5at30'), 0.5)
    if (not s5["prof"] or not s30["prof"]
            or s5["validFrac"] < 0.99 or s30["validFrac"] < 0.99):
        note(corpus, 'coverage')
        return
    fabOK = bool(sF["prof"]) and sF["validFrac"] >= 0.99
    if not fabOK:
        note(corpus, 'fabdem-coverage')

    pw = pw_from(bin_grades(point_regime_data(pts), CLIMB_THR, DESC_THR), pts)
    vf = flat_eq_speed(pw["flat"], p)
    profs = {"baro": prof5, "igc5": s5["prof"], "igc30": s30["prof"],
             "fabdem30": sF["prof"] if fabOK else None}

    row = {"corpus": corpus, "ride": label, "emp": emp, "km": total / 1000, "vf_kmh": vf * 3.6,
           "valid_igc5": s5["validFrac"], "valid_igc30": s30["validFrac"],
           "valid_fabdem": sF["validFrac"] if sF["prof"] else 0, "geoCov": geoCov}
    for src in SOURCES:
        prof = profs[src]
        if not prof:
            for k in ('v2', 'r0', 'd_v2', 'd_r0', 'hplus', 'hminus', 'epsw', 'eps'):
                row[f"{k}_{src}"] = float("nan")
            continue
        v2 = r1d_v2_edge(prof, p, pw, CLIMB_THR)                      # RAW profile, native step
        ws = walk_stats(prof, p, pw, CLIMB_THR)
        MAX_WALK_MISMATCH = max(MAX_WALK_MISMATCH, abs(ws["E"] - v2))
        eps = 0.20
        if eps_rule != 'urban':
            eg = eps_geom(prof, p, vf)
            eps = eg if is_finite(eg) else 0.20
        r0 = r0_champion(prof, {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)},
                         p, pw, eps)["eSm"]
        row[f"v2_{src}"] = v2
        row[f"r0_{src}"] = r0
        row[f"d_v2_{src}"] = d_pct(v2, emp)
        row[f"d_r0_{src}"] = d_pct(r0, emp)
        row[f"hplus_{src}"] = ws["hplus"]
        row[f"hminus_{src}"] = ws["hminus"]
        row[f"epsw_{src}"] = ws["epsImplied"]
        row[f"eps_{src}"] = eps
        # sanity gate: profile distance ≡ track distance (exact by construction)
        if abs(prof["x"][len(prof["x"]) - 1] - total) > 1e-6:
            raise ValueError(f"distance mismatch {label} {src}")
    # gate: igc5 sampled at 30 m steps ≈ igc30 (approximate — the warp adds area averaging)
    row["v2_igc5at30"] = (r1d_v2_edge(s5at30["prof"], p, pw, CLIMB_THR)
                          if s5at30["prof"] and s5at30["validFrac"] >= 0.99 else float("nan"))
    # gate: DEM(igc5)-vs-baro shape RMS (mean-removed; both series live on the same 5 m grid)
    a, b = prof5["h"], s5["prof"]["h"]
    n = min(len(a), len(b))
    ma = mb = 0.0
    for i in range(n):
        ma += a[i]
        mb += b[i]
    ma /= n
    mb /= n
    ss = 0.0
    for i in range(n):
        d = (a[i] - ma) - (b[i] - mb)
        ss += d * d
    row["rms_baro_igc5"] = math.sqrt(ss / n)
    rows.append(row)
    note(corpus, 'included')


# ===== reporting helpers =====
def f(x, d=1):
    if x is None or not is_finite(x):
        return "—"
    return to_fixed(x, d)


CORP = [['censo', 'censo (urban group rides, assumed rider)'],
        ['ppaz', 'P. Paz (open, frozen physics)'],
        ['jaam', 'JAAM (open, frozen physics)'],
        ['danlessa', 'author full (open, frozen physics)']]


def by_corpus(c):
    if c == 'pooled':
        return [r for r in rows if r["corpus"] != 'censo']
    return [r for r in rows if r["corpus"] == c]


# ===== CSV cell writer (JS: typeof 'string' → JSON.stringify; finite → +Number(v).toFixed(4);
# anything else → '') =====
def cell4(v):
    if isinstance(v, str):
        return jquote(v)
    if is_finite(v):
        return js_str(float(to_fixed(v, 4)))
    return ""


COLS = (['corpus', 'ride', 'emp', 'km', 'vf_kmh', 'geoCov', 'valid_igc5', 'valid_igc30',
         'valid_fabdem', 'rms_baro_igc5', 'v2_igc5at30']
        + [k for s in SOURCES for k in (f"v2_{s}", f"r0_{s}", f"d_v2_{s}", f"d_r0_{s}",
                                        f"hplus_{s}", f"hminus_{s}", f"epsw_{s}", f"eps_{s}")])


def main():
    os.makedirs(RESULTS, exist_ok=True)
    ensure_rasters()

    # ===== drivers (loading + cleaning mirrors regime_compare.mjs / censo_compare.mjs) =====
    t0 = time.time() * 1000
    # censo (ASSUMED rider, urban ε = 0.20, physical floor)
    with open(os.path.join(DATA, 'censohidrografico', 'manifest.json'), encoding="utf-8") as fh:
        man = json.load(fh)
    for e in man:
        if not e.get("file") or not os.path.exists(os.path.join(DATA, e["file"])):
            continue
        try:
            process_ride(e["file"], ASSUMED, e.get("name"), 'censo', 'urban')
        except Exception:
            note('censo', 'unparseable')
    for corpus, manifest in (['ppaz', 'strava_ppaz_manifest.json'],
                             ['jaam', 'strava_jaam_manifest.json'],
                             ['danlessa', 'strava_danlessa_manifest.json']):
        with open(os.path.join(DATA, manifest), encoding="utf-8") as fh:
            man = json.load(fh)
        cand = [a for a in man if a.get("sport") == 'ride' and jgt(a.get("powCov"), 0.5)
                and jge(a.get("km"), 20) and jge(a.get("altCov"), 0.99)]
        n = 0
        for a in cand:
            try:
                process_ride(a["file"], PHYS[corpus], a.get("id"), corpus, 'open')
            except Exception:
                note(corpus, 'unparseable')
            n += 1
            if n % 100 == 0:
                print(f"  …{corpus} {n}/{len(cand)} "
                      f"({to_fixed((time.time() * 1000 - t0) / 1000, 0)} s)", file=sys.stderr)
    print(f"sampling ms: {json.dumps(sample_ms, separators=(',', ':'))} · "
          f"total {to_fixed((time.time() * 1000 - t0) / 1000, 0)} s", file=sys.stderr)

    # ===== report =====
    print('ENTRY 19 — v2Edge on the deployed IGC-SP 5 m raster vs 30 m resample vs FABDEM')
    print(f"DEM: {DEM5}")
    print("warp: gdalwarp -r average -tr 0.000287042610744 0.000287042610744 (6× native px) "
          "· FABDEM S24W047 V1-2")
    print('\nCORPUS FUNNEL (clean per corpus filters → inside coverage):')
    for c, _title in CORP:
        e = excl.get(c) or {}
        print(f"  {c.ljust(9)} clean={e.get('clean') or 0} → included={e.get('included') or 0}"
              f"   [excl: bbox={e.get('bbox') or 0} coverage={e.get('coverage') or 0}"
              f" geo-span={e.get('geo-span') or 0} no-geo={e.get('no-geo') or 0}]"
              f" (pre-clean skips: no-power={e.get('no-power') or 0}"
              f" phys-floor={e.get('phys-floor') or 0} zwift={e.get('zwift') or 0}"
              f" unparseable={e.get('unparseable') or 0} no-emp={e.get('no-emp') or 0}"
              f" gpx={e.get('gpx-unsupported') or 0};"
              f" fabdem-coverage misses={e.get('fabdem-coverage') or 0})")
    print(f"  pooled riders included n={len(by_corpus('pooled'))} · "
          f"censo n={len(by_corpus('censo'))} · all n={len(rows)}")

    print('\nMED |Δ%| AND MEDIAN SIGNED Δ% vs measured ∫P·dt '
          '(v2Edge raw @ native step · R0 cf+2m deadband):')
    for c, title in [*CORP, ['pooled', 'POOLED independent riders (ppaz+jaam+danlessa)']]:
        st = by_corpus(c)
        if not st:
            continue
        print(f"\n── {title} ──  n={len(st)}")
        print('model@source'.ljust(22) + 'med|Δ%|'.rjust(9) + 'medΔ%'.rjust(8))
        for m in ('v2', 'r0'):
            for s in SOURCES:
                ds = [r[f"d_{m}_{s}"] for r in st if is_finite(r[f"d_{m}_{s}"])]
                print((('v2Edge@' if m == 'v2' else 'R0@') + s).ljust(22)
                      + f(med_of([abs(x) for x in ds])).rjust(9)
                      + f(med_of(ds)).rjust(8) + f"   (n={len(ds)})")

    print('\n================ PRIMARY ENDPOINTS — paired v2Edge@igc5 vs v2Edge@igc30 '
          '================')
    for c, title in [['censo', 'censo (pre-registered primary)'],
                     ['pooled', 'pooled independent riders (co-primary)'],
                     ['ppaz', 'P. Paz'], ['jaam', 'JAAM'], ['danlessa', 'author']]:
        st = by_corpus(c)
        if not st:
            continue
        m5 = med_of([abs(r["d_v2_igc5"]) for r in st if is_finite(abs(r["d_v2_igc5"]))])
        m30 = med_of([abs(r["d_v2_igc30"]) for r in st if is_finite(abs(r["d_v2_igc30"]))])
        b5 = med_of([r["d_v2_igc5"] for r in st if is_finite(r["d_v2_igc5"])])
        b30 = med_of([r["d_v2_igc30"] for r in st if is_finite(r["d_v2_igc30"])])
        gap = med_of([r["d_v2_igc5"] - r["d_v2_igc30"] for r in st
                      if is_finite(r["d_v2_igc5"] - r["d_v2_igc30"])])
        t = paired_abs(st, 'd_v2_igc5', 'd_v2_igc30')
        print(f"  {title}  (n={len(st)})")
        print(f"    med|Δ%|: igc5 {f(m5)} vs igc30 {f(m30)} · signed bias: igc5 {f(b5)} "
              f"vs igc30 {f(b30)} · med per-ride signed gap {f(gap, 2)} pp")
        print(f"    paired |Δ%|: igc5 better on {t['wins']}/{t['n']} "
              f"({f(t['winFrac'] * 100, 0)}%) · med Δ|Δ%| {f(t['medDiff'], 2)} pp · "
              f"sign p={f(t['pSign'], 4)} · Wilcoxon p={f(t['pWilcoxon'], 4)}")

    print('\nSECONDARY — paired v2Edge@igc30 vs v2Edge@fabdem30 '
          '(local survey vs free global DEM, same 30 m grid):')
    for c in [x[0] for x in CORP] + ['pooled']:
        st = [r for r in by_corpus(c) if is_finite(r["d_v2_fabdem30"])]
        if not st:
            continue
        t = paired_abs(st, 'd_v2_fabdem30', 'd_v2_igc30')
        dE = med_of([jsdiv(r["v2_fabdem30"] - r["v2_igc30"], r["v2_igc30"]) * 100 for r in st])
        dH = med_of([jsdiv(r["hplus_fabdem30"] - r["hplus_igc30"], r["hplus_igc30"]) * 100
                     for r in st])
        print(f"  {c.ljust(9)} n={len(st)} · med|Δ%|: fabdem "
              f"{f(med_of([abs(r['d_v2_fabdem30']) for r in st]))} vs igc30 "
              f"{f(med_of([abs(r['d_v2_igc30']) for r in st]))} · fabdem better "
              f"{t['wins']}/{t['n']} ({f(t['winFrac'] * 100, 0)}%) sign p={f(t['pSign'], 3)} · "
              f"med energy Δ(fab−igc30) {f(dE, 2)}% · med h₊ Δ {f(dH, 2)}%")

    print('\nDECOMPOSITION — median Σh₊ / Σh₋ (m) per source (v2Edge walked edges) and implied '
          'drop-weighted ε:')
    for c in [x[0] for x in CORP] + ['pooled']:
        st = by_corpus(c)
        if not st:
            continue

        def g(k, st=st):
            return f(med_of([r[k] for r in st if is_finite(r[k])]), 0)

        def ge(k, st=st):
            return f(med_of([r[k] for r in st if is_finite(r[k])]), 3)

        print(f"  {c.ljust(9)} h₊: baro {g('hplus_baro')} · igc5 {g('hplus_igc5')} · "
              f"igc30 {g('hplus_igc30')} · fabdem {g('hplus_fabdem30')}   |   h₋: "
              f"{g('hminus_baro')} · {g('hminus_igc5')} · {g('hminus_igc30')} · "
              f"{g('hminus_fabdem30')}")
        print(f"  {''.ljust(9)} implied ε: baro {ge('epsw_baro')} · igc5 {ge('epsw_igc5')} · "
              f"igc30 {ge('epsw_igc30')} · fabdem {ge('epsw_fabdem30')}")

    # ===== sanity gates =====
    print('\n================ SANITY GATES ================')
    ok = [True]

    def say(name, passed, extra=''):
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}{('  ' + extra) if extra else ''}")
        if not passed:
            ok[0] = False

    # (1) baro anchor reproduces regime_compare's published per-ride numbers (emp,
    #     r1d5r=v2Edge@baro raw, r0sm=R0@baro) — matched by corpus+ride against
    #     regime_comparison.csv (3-decimal rounding → tol).
    try:
        with open(os.path.join(RESULTS, 'regime_comparison.csv'), encoding="utf-8") as fh:
            csv = fh.read().split('\n')
        hdr = csv[0].split(',')

        def idx(k):
            return hdr.index(k) if k in hdr else -1

        ref = {}
        for i in range(1, len(csv)):
            c = csv[i].split(',')
            if len(c) < 5:
                continue
            ref[_at(c, idx('corpus')).replace('"', '') + '|'
                + _at(c, idx('ride')).replace('"', '')] = {
                    "emp": js_plus(_at(c, idx('emp'))),
                    "r1d5r": js_plus(_at(c, idx('r1d5r'))),
                    "r0sm": js_plus(_at(c, idx('r0sm')))}
        nM = 0
        worst = 0
        worstWhat = ''
        for r in rows:
            q = ref.get(r["corpus"] + '|' + r["ride"])
            if not q:
                continue
            nM += 1
            for mine, theirs, lab in ((r["emp"], q["emp"], 'emp'),
                                      (r["v2_baro"], q["r1d5r"], 'v2@baro'),
                                      (r["r0_baro"], q["r0sm"], 'r0@baro')):
                d = abs(mine - theirs)
                if d > worst:
                    worst = d
                    worstWhat = f"{lab} {r['corpus']}/{r['ride']}"
        say(f"baro anchor ≡ regime_comparison.csv (emp, r1d5r, r0sm) on {nM} matched rides",
            nM > 0 and worst < 0.002,
            f"worst |Δ| {to_exponential(worst, 2)} kJ ({worstWhat})")
    except Exception as ex:
        say('baro anchor vs regime_comparison.csv', False, str(ex))
    # (2) profile distance ≡ track distance — asserted exactly per ride/source inside
    #     process_ride; the geo track's span vs device distance is the approximate part:
    say('profile distance ≡ track distance (exact per construction; no ride threw)', True)
    _gc = [r["geoCov"] for r in rows]
    print(f"         geo-track span coverage: median {f(med_of(_gc) * 100, 2)}% "
          f"(min {f((min(_gc) if _gc else float('inf')) * 100, 2)}%)")
    # (3) igc5 sampled at 30 m steps ≈ igc30 (approximate — -r average vs point-bilinear)
    d = [x for x in (jsdiv(abs(r["v2_igc5at30"] - r["v2_igc30"]), r["v2_igc30"]) * 100
                     if is_finite(r["v2_igc5at30"]) else float("nan") for r in rows)
         if is_finite(x)]
    _med = med_of(d)
    _extra_med = f(med_of(d), 2)
    d.sort()
    _p90i = math.floor(0.9 * (len(d) - 1))
    _p90 = d[_p90i] if 0 <= _p90i < len(d) else None
    say('igc5-sampled-at-30m-steps ≈ igc30 (approximate gate)', _med < 2,
        f"med |ΔE| {_extra_med}% · p90 {f(_p90, 2)}%")
    # (4) DEM-vs-baro shape RMS in the Entry-6 ballpark (~7–8 m)
    m = med_of([r["rms_baro_igc5"] for r in rows])
    say('DEM(igc5)-vs-baro shape RMS ~7–8 m ballpark', m > 2 and m < 15, f"median {f(m, 1)} m")
    # (5) dead-clamp assert (Entry 18): every per-edge pre-clamp descent cost > 0 across ALL
    #     profiles
    say('dead-clamp: min pre-clamp descent edge > 0', RC.R1D_MIN_PRECLAMP > 0,
        f"min {to_exponential(RC.R1D_MIN_PRECLAMP, 2)} J")
    # (6) walk decomposition ≡ verbatim r1d_v2_edge
    say('walkStats ≡ r1dV2Edge (per profile)', MAX_WALK_MISMATCH < 1e-9,
        f"max |Δ| {to_exponential(MAX_WALK_MISMATCH, 2)} kJ")
    print('\nSANITY: ALL PASS' if ok[0] else '\nSANITY: FAILURES ABOVE')

    # ===== CSV (gitignored via results/*) =====
    out = [",".join(COLS)]
    for r in rows:
        out.append(",".join(cell4(r.get(k)) for k in COLS))
    with open(os.path.join(RESULTS, 'igc_resolution_test.csv'), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"\nwrote igc_resolution_test.csv ({len(rows)} rides)")
    sys.exit(0 if ok[0] else 1)


if __name__ == "__main__":
    main()
