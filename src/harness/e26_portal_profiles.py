#!/usr/bin/env python3
"""ENTRY 26 — Q2A (Experiment 2A): portals (bridges/tunnels) as PROFILE corrections.

Pre-registered question (journal Entry 26, "Q2A — the track-as-whole scenario"): does
portal-correcting the *profile* change prediction accuracy and bias against measured
∫P·dt?  Method: rebuild the Entry-19 igc5 (and igc30) profiles with a portal overlay —
where a ride's track runs along a mapped OSM bridge/tunnel span, replace the sampled
heights across the span with the v19 straight-deck interpolation between the raster
heights AT the two abutments; elsewhere untouched.  Re-run the Entry-19 walk (v2Edge at
native step + the R0 champion, the exact igc_resolution_test code paths) on corrected vs
raw profiles, all rides, PAIRED.

Pre-registered endpoints: paired Δ(med |Δ%|) and Δ(bias) per corpus and pooled; share of
rides touched (≥ 1 span) and the conditional effect on touched rides; the h₊ removed.
Predictions: P5 bias moves DOWN on touched rides; P6 pooled median moves < 1 pp but the
touched tail improves, most on censo; P7 h₊ drops on ≥ 90% of touched rides.
Falsifier: bias UP or worse scatter on touched rides ⇒ stop and diagnose.

DISCLOSED OPERATIONALIZATION (the pre-registration says "matched by proximity + heading";
these are the concrete thresholds, chosen before looking at any result):
  - OSM spans: Overpass `way["highway"]["bridge"]["bridge"!="no"]` +
    `way["highway"]["tunnel"]["tunnel"!="no"]` (the shipped simujaules v19 pull, extended
    from tunnel=yes to tunnel=* per the Entry-26 wording), fetched per 0.1° tile covering
    each ride's bbox (+0.005° margin), deduplicated by way id.  Every Overpass response is
    CACHED under data/results/e26_osm_cache/q2a/ keyed by a hash of the rounded tile bbox, so
    reruns are fully offline; live fetches are throttled (≥ 1 s apart) and retried with
    backoff on 429/5xx.  A span's abutments = the way's first/last geometry nodes (OSM
    splits bridge/tunnel ways at the structure); deckLenM = haversine polyline length.
  - Matching (done ONCE, on the igc5 5 m grid; the same along-track intervals then
    correct both igc5 and igc30 — keeps the two profiles paired): a grid point lies on a
    span when its distance to the span polyline is ≤ 25 m AND the local track heading is
    within 30° of the nearest span segment's heading (mod 180°, either direction).
    Maximal runs of consecutive matched points (gaps ≤ 3 points ≈ 15 m bridged — GPS
    lateral jitter tolerance).  A run matches a span when its along-track extent is
    ≥ 60% of deckLenM, both abutments project onto the track within 50 m, and the
    projected abutment extent |xB−xA| is within [0.6, 2.0]×deckLenM (guards partial
    crossings and pathological projections).  Distances/headings use a local
    equirectangular projection (111320·cos(lat₀) m/°lon, 110540 m/°lat).
  - Correction (v19 straight deck): profile samples with x ∈ [xA, xB] are replaced by
    linear interpolation between the raster heights at the two abutments — igc5 uses the
    native raster's abutment heights, igc30 the 30 m warp's (each profile keeps its own
    raster).  A crossing is dropped if any abutment height is invalid (≤ 0.5 m floor, as
    in Entry 19) on either raster.  Overlapping intervals (dual-carriageway twins) simply
    overwrite; span_m reports the merged corrected extent.
  - `spans_matched` = accepted crossings (a way crossed twice = 2; twin ways = 2).

SANITY GATES (abort on failure):
  1. no-op invariant — rides with zero matched spans reproduce the raw igc5/igc30
     energies EXACTLY (same code path runs with an empty interval list; float-equal);
  2. corrected profile distance ≡ raw (the corrected profile shares the raw x array);
  3. every deck interpolation bounded by [min, max] of the two abutment heights.

Output: data/results/e26_portal_profiles.csv (gitignored via data/results/*) — per-ride, plus an
aggregate stdout block with NO ride names.  E26_SMOKE=1 limits to the first 15 rides.

Deviation from the house stdlib-only rule: numpy (matching is O(points × spans); run with
/Users/danlessa/conda/bin/python).  Import-safe: the driver lives in main().
"""

import gzip
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import igc_resolution_test as IGC  # noqa: E402
from igc_resolution_test import (BBOX, DATA, DEM5, DEM30, RESULTS, cell4,  # noqa: E402
                                 build_dem_profile, f, geo_track_from_fit,
                                 grid_positions, lon_lat_at, sample_raster)
import regime_compare as RC  # noqa: E402
from regime_compare import (ASSUMED, CLIMB_THR, DESC_THR, ENGINE_DX, G, PHYS,  # noqa: E402
                            TAU_SMOOTH, VMAX, VSTART, ZWIFT, approx_components,
                            bin_grades, build_profile, d_pct, deadband, empirical_kj,
                            eps_geom, flat_eq_speed, has_power, haversine, is_finite,
                            jge, jgt, med_of, overall_mean_power, point_regime_data,
                            pts_from_fit, pw_from, r0_champion, r1d_v2_edge,
                            resample_profile)

# ===== constants =====
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
UA = "bicycling-energy-model E26-Q2A harness (research; contact: danilo.lessa@gmail.com)"
CACHE_DIR = os.path.join(RESULTS, "e26_osm_cache", "q2a")
TILE_DEG = 0.1
TILE_MARGIN = 0.005          # ride-bbox margin when choosing tiles / candidate ways (deg)
MATCH_DIST_M = 25.0          # point-to-span proximity threshold
MATCH_HEAD_DEG = 30.0        # heading agreement threshold (mod 180)
MIN_COVER = 0.60             # required track coverage of the span length
RUN_GAP_PTS = 3              # matched-run gap tolerance (grid points)
ABUT_PROJ_MAX_M = 50.0       # abutment must project onto the track within this
EXTENT_MAX_RATIO = 2.0       # projected extent cap, ×deckLenM
RASTER_FLOOR = 0.5           # invalid-height floor for sampa_geral (Entry 19)
M_PER_DEG_LAT = 110540.0
M_PER_DEG_LON_EQ = 111320.0

# ===== module state =====
WAYS = {}          # way id → {"id","kind","lats","lons","bbox","deck"}
TILES = {}         # tile cache key → [way ids]
fetch_stats = {"tiles": 0, "network": 0, "cached": 0}
rows = []
excl = {}          # per-corpus funnel tallies
drop = {}          # crossing-level drop tallies (matched but rejected)
NOOP_CHECKED = [0]           # zero-span rides byte-checked (gate 1)
DECK_BOUND_WORST = [0.0]     # worst deck-interp exceedance beyond abutment bounds (gate 3)


class GateError(Exception):
    """A pre-registered sanity gate failed — abort the run."""


def note(c, k):
    excl.setdefault(c, {})[k] = excl.get(c, {}).get(k, 0) + 1


def tally(k):
    drop[k] = drop.get(k, 0) + 1


# ===== raster prep (DEM30 only — FABDEM is not part of Q2A) =====
def ensure_dem30():
    os.makedirs(IGC.SCRATCH, exist_ok=True)
    if not os.path.exists(DEM30):
        print("creating 30 m warp…", file=sys.stderr)
        subprocess.run(["gdalwarp", "-r", "average", "-tr", "0.000287042610744",
                        "0.000287042610744", DEM5, DEM30],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=True)


# ===== Overpass tile pull (cached, throttled) =====
_last_req = [0.0]


def _overpass(query):
    for attempt in range(6):
        if attempt:
            time.sleep([5, 15, 30, 60, 120][attempt - 1])
        wait = 1.0 - (time.time() - _last_req[0])
        if wait > 0:
            time.sleep(wait)
        _last_req[0] = time.time()
        try:
            req = urllib.request.Request(
                OVERPASS_URL,
                data=("data=" + urllib.parse.quote(query)).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded",
                         "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = resp.read().decode("utf-8")
            js = json.loads(body)
            if "elements" in js:
                return js
            print("overpass: no elements key, retrying…", file=sys.stderr)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504):
                raise
            print(f"overpass HTTP {e.code}, backing off…", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"overpass error {type(e).__name__}, retrying…", file=sys.stderr)
    raise RuntimeError("Overpass failed after retries — aborting (spans would be missing)")


def _parse_tile(js):
    ids = []
    for el in js.get("elements", []):
        if el.get("type") != "way" or len(el.get("geometry") or []) < 2:
            continue
        wid = el["id"]
        ids.append(wid)
        if wid in WAYS:
            continue
        tg = el.get("tags") or {}
        g = el["geometry"]
        lats = np.array([p["lat"] for p in g], dtype=np.float64)
        lons = np.array([p["lon"] for p in g], dtype=np.float64)
        deck = 0.0
        for i in range(1, len(g)):
            deck += haversine({"lat": g[i - 1]["lat"], "lon": g[i - 1]["lon"]},
                              {"lat": g[i]["lat"], "lon": g[i]["lon"]})
        kind = "tunnel" if (tg.get("tunnel") and tg.get("tunnel") != "no") else "bridge"
        WAYS[wid] = {"id": wid, "kind": kind, "lats": lats, "lons": lons,
                     "bbox": (lats.min(), lats.max(), lons.min(), lons.max()),
                     "deck": deck}
    return ids


def tile_ways(ti, tj):
    s, w = ti * TILE_DEG, tj * TILE_DEG
    n, e = s + TILE_DEG, w + TILE_DEG
    key = f"{s:.4f},{w:.4f},{n:.4f},{e:.4f}"
    if key in TILES:
        return TILES[key]
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    path = os.path.join(CACHE_DIR, f"{h}.json")
    js = None
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                js = json.load(fh)
            fetch_stats["cached"] += 1
        except (json.JSONDecodeError, OSError):
            js = None
    if js is None:
        bbox = f"{s:.6f},{w:.6f},{n:.6f},{e:.6f}"
        q = ('[out:json][timeout:180];('
             f'way["highway"]["bridge"]["bridge"!="no"]({bbox});'
             f'way["highway"]["tunnel"]["tunnel"!="no"]({bbox});'
             ');out geom;')
        js = _overpass(q)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(js, fh, separators=(",", ":"))
        fetch_stats["network"] += 1
    fetch_stats["tiles"] += 1
    TILES[key] = _parse_tile(js)
    return TILES[key]


def ways_for_bbox(lat_min, lat_max, lon_min, lon_max):
    ids = set()
    ti0 = math.floor((lat_min - TILE_MARGIN) / TILE_DEG)
    ti1 = math.floor((lat_max + TILE_MARGIN) / TILE_DEG)
    tj0 = math.floor((lon_min - TILE_MARGIN) / TILE_DEG)
    tj1 = math.floor((lon_max + TILE_MARGIN) / TILE_DEG)
    for ti in range(ti0, ti1 + 1):
        for tj in range(tj0, tj1 + 1):
            ids.update(tile_ways(ti, tj))
    out = []
    for wid in ids:
        w = WAYS[wid]
        b = w["bbox"]
        if (b[0] <= lat_max + TILE_MARGIN and b[1] >= lat_min - TILE_MARGIN
                and b[2] <= lon_max + TILE_MARGIN and b[3] >= lon_min - TILE_MARGIN):
            out.append(w)
    return out


# ===== geometry: matching on the 5 m grid =====
def track_headings(px, py):
    """Local heading (deg, mod 180) from the centered neighbour difference."""
    n = len(px)
    ip = np.minimum(np.arange(n) + 1, n - 1)
    im = np.maximum(np.arange(n) - 1, 0)
    dx = px[ip] - px[im]
    dy = py[ip] - py[im]
    hd = np.full(n, np.nan)
    ok = np.hypot(dx, dy) > 1e-6
    hd[ok] = np.degrees(np.arctan2(dx[ok], dy[ok])) % 180.0
    return hd


def match_way_mask(px, py, hd, wx, wy):
    """Boolean per-grid-point: within 25 m of the span polyline AND heading within 30°."""
    n = len(px)
    pad = MATCH_DIST_M + 5.0
    sel = ((px >= wx.min() - pad) & (px <= wx.max() + pad)
           & (py >= wy.min() - pad) & (py <= wy.max() + pad))
    idx = np.nonzero(sel)[0]
    if idx.size == 0:
        return None
    qx, qy = px[idx], py[idx]
    ax, ay, bx, by = wx[:-1], wy[:-1], wx[1:], wy[1:]
    best_d2 = np.full(idx.size, np.inf)
    best_j = np.zeros(idx.size, dtype=np.int64)
    for j in range(len(ax)):
        abx, aby = bx[j] - ax[j], by[j] - ay[j]
        L2 = abx * abx + aby * aby
        if L2 < 1e-12:
            d2 = (qx - ax[j]) ** 2 + (qy - ay[j]) ** 2
        else:
            t = np.clip(((qx - ax[j]) * abx + (qy - ay[j]) * aby) / L2, 0.0, 1.0)
            d2 = (qx - (ax[j] + t * abx)) ** 2 + (qy - (ay[j] + t * aby)) ** 2
        upd = d2 < best_d2
        best_d2[upd] = d2[upd]
        best_j[upd] = j
    seg_hd = np.degrees(np.arctan2(bx - ax, by - ay)) % 180.0
    dh = np.abs(hd[idx] - seg_hd[best_j]) % 180.0
    dh = np.minimum(dh, 180.0 - dh)
    ok = (best_d2 <= MATCH_DIST_M ** 2) & (dh <= MATCH_HEAD_DEG)
    if not ok.any():
        return None
    mask = np.zeros(n, dtype=bool)
    mask[idx[ok]] = True
    return mask


def runs_from_mask(mask, max_gap):
    """Maximal runs of consecutive True, bridging gaps ≤ max_gap points."""
    idxs = np.nonzero(mask)[0]
    runs = []
    for i in idxs:
        if runs and i - runs[-1][1] <= max_gap + 1:
            runs[-1][1] = i
        else:
            runs.append([int(i), int(i)])
    return runs


def project_point(px, py, xs, i0, i1, qx, qy):
    """Min-distance projection of (qx,qy) onto track segments [i0, i1); returns
    (distance m, along-track x)."""
    ax, ay = px[i0:i1], py[i0:i1]
    bx, by = px[i0 + 1:i1 + 1], py[i0 + 1:i1 + 1]
    abx, aby = bx - ax, by - ay
    L2 = np.maximum(abx * abx + aby * aby, 1e-12)
    t = np.clip(((qx - ax) * abx + (qy - ay) * aby) / L2, 0.0, 1.0)
    d2 = (qx - (ax + t * abx)) ** 2 + (qy - (ay + t * aby)) ** 2
    j = int(np.argmin(d2))
    xa = xs[i0 + j]
    xb = xs[i0 + j + 1]
    return math.sqrt(float(d2[j])), float(xa + t[j] * (xb - xa))


def match_crossings(d5, lons, lats, ways):
    """All accepted (span, run) crossings on the 5 m grid.  Returns a list of dicts with
    the along-track interval and the LO/HI abutment lon/lat (heights sampled later)."""
    lat0, lon0 = lats[0], lons[0]
    mlon = M_PER_DEG_LON_EQ * math.cos(math.radians(lat0))
    mlat = M_PER_DEG_LAT
    px = (np.asarray(lons) - lon0) * mlon
    py = (np.asarray(lats) - lat0) * mlat
    xs = np.asarray(d5)
    hd = track_headings(px, py)
    n = len(xs)
    step = xs[-1] / (n - 1) if n > 1 else 1.0
    # Coarse track-occupancy grid (250 m cells): a ride's bbox is huge but the track is a
    # thin line — skip ways whose (padded) bbox touches no occupied cell.
    CELL = 250.0
    occ = set(zip((px // CELL).astype(np.int64).tolist(),
                  (py // CELL).astype(np.int64).tolist()))
    out = []
    for w in ways:
        deck = w["deck"]
        if not deck > 0:
            continue
        wx = (w["lons"] - lon0) * mlon
        wy = (w["lats"] - lat0) * mlat
        pad = MATCH_DIST_M + 5.0
        cx0 = int((wx.min() - pad) // CELL)
        cx1 = int((wx.max() + pad) // CELL)
        cy0 = int((wy.min() - pad) // CELL)
        cy1 = int((wy.max() + pad) // CELL)
        if not any((cx, cy) in occ
                   for cx in range(cx0, cx1 + 1) for cy in range(cy0, cy1 + 1)):
            continue
        mask = match_way_mask(px, py, hd, wx, wy)
        if mask is None:
            continue
        for i0, i1 in runs_from_mask(mask, RUN_GAP_PTS):
            if xs[i1] - xs[i0] < MIN_COVER * deck:
                tally("run-short")
                continue
            ext = int(math.ceil((deck + 2 * ABUT_PROJ_MAX_M) / step)) + 1
            w0 = max(0, i0 - ext)
            w1 = min(n - 1, i1 + ext)
            if w1 <= w0:
                tally("window-degenerate")
                continue
            dA, xA = project_point(px, py, xs, w0, w1, wx[0], wy[0])
            dB, xB = project_point(px, py, xs, w0, w1, wx[-1], wy[-1])
            if dA > ABUT_PROJ_MAX_M or dB > ABUT_PROJ_MAX_M:
                tally("abutment-far")
                continue
            extent = abs(xB - xA)
            if extent < MIN_COVER * deck or extent > EXTENT_MAX_RATIO * deck:
                tally("extent-off")
                continue
            # plain floats (not np.float64) — keep types consistent with sample_raster
            if xA <= xB:
                lo = (xA, float(w["lats"][0]), float(w["lons"][0]))
                hi = (xB, float(w["lats"][-1]), float(w["lons"][-1]))
            else:
                lo = (xB, float(w["lats"][-1]), float(w["lons"][-1]))
                hi = (xA, float(w["lats"][0]), float(w["lons"][0]))
            out.append({"xlo": lo[0], "latLO": lo[1], "lonLO": lo[2],
                        "xhi": hi[0], "latHI": hi[1], "lonHI": hi[2],
                        "deck": deck, "kind": w["kind"]})
    return out


# ===== the deck correction =====
def apply_deck(prof, intervals):
    """Return the portal-corrected profile: same x array (gate 2), heights replaced by the
    straight deck inside each interval.  intervals: (xlo, xhi, hlo, hhi), pre-sorted or not.
    Runs for EVERY ride (empty list ⇒ verbatim copy) so the no-op gate exercises the same
    code path."""
    h = list(prof["h"])
    xs = prof["x"]
    for xlo, xhi, hlo, hhi in sorted(intervals):
        span = xhi - xlo
        if not span > 0:
            continue
        b_lo, b_hi = (hlo, hhi) if hlo <= hhi else (hhi, hlo)
        for i in range(len(xs)):
            x = xs[i]
            if x < xlo:
                continue
            if x > xhi:
                break
            hn = hlo + (hhi - hlo) * (x - xlo) / span
            exceed = max(b_lo - hn, hn - b_hi, 0.0)
            if exceed > DECK_BOUND_WORST[0]:
                DECK_BOUND_WORST[0] = exceed
            if exceed > 1e-9:
                raise GateError(f"deck interpolation out of abutment bounds by {exceed} m")
            h[i] = hn
    out = {"x": prof["x"], "h": h}
    if out["x"] is not prof["x"]:   # gate 2: distance identity by construction
        raise GateError("corrected profile does not share the raw x array")
    return out


def hplus_of(prof):
    xs, hs = prof["x"], prof["h"]
    s = 0.0
    for i in range(1, len(xs)):
        if xs[i] - xs[i - 1] > 0 and hs[i] - hs[i - 1] > 0:
            s += hs[i] - hs[i - 1]
    return s


def merged_len(intervals):
    ivs = sorted((iv[0], iv[1]) for iv in intervals)
    total = 0.0
    cur = None
    for a, b in ivs:
        if cur and a <= cur[1]:
            cur[1] = max(cur[1], b)
        else:
            if cur:
                total += cur[1] - cur[0]
            cur = [a, b]
    if cur:
        total += cur[1] - cur[0]
    return total


# ===== per-ride processing (funnel VERBATIM from igc_resolution_test.process_ride,
# minus FABDEM / igc5at30 / baro-anchor bookkeeping) =====
def energies(prof5, prof30, p, pw, vf, eps_rule):
    """The Entry-19 code paths: v2Edge raw @ native step on both profiles; R0 champion on
    igc5 (censo → ε=0.20; riders → frozen ε_geom(−0.13) of the profile fed in)."""
    v2_5 = r1d_v2_edge(prof5, p, pw, CLIMB_THR)
    v2_30 = r1d_v2_edge(prof30, p, pw, CLIMB_THR)
    eps = 0.20
    if eps_rule != "urban":
        eg = eps_geom(prof5, p, vf)
        eps = eg if is_finite(eg) else 0.20
    r0_5 = r0_champion(prof5, {"x": prof5["x"], "h": deadband(prof5["h"], TAU_SMOOTH)},
                       p, pw, eps)["eSm"]
    return v2_5, r0_5, v2_30


def process_ride(file, p0, label, corpus, eps_rule):
    with open(os.path.join(DATA, file), "rb") as fh:
        buf0 = fh.read()
    buf = gzip.decompress(buf0) if file.endswith(".gz") else buf0
    if file.endswith(".gpx") or file.endswith(".gpx.gz"):
        note(corpus, "gpx-unsupported")
        return
    pts = pts_from_fit(buf)
    if corpus != "censo" and RC.FIT_MANUF == ZWIFT:
        note(corpus, "zwift")
        return
    if not has_power(pts):
        note(corpus, "no-power")
        return
    p = {**p0, "vmax": VMAX, "vstart": VSTART}
    build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    phys_profile = RC.phys_profile
    prof5b = resample_profile(phys_profile, ENGINE_DX)
    total = prof5b["x"][len(prof5b["x"]) - 1]
    emp = empirical_kj(pts)
    if not emp > 0:
        note(corpus, "no-emp")
        return
    if corpus == "censo":   # physical-plausibility floor, VERBATIM regime_compare driver
        profS0 = {"x": prof5b["x"], "h": deadband(prof5b["h"], TAU_SMOOTH)}
        aSm0 = approx_components(profS0, p, flat_eq_speed(overall_mean_power(pts), p), None)
        if emp < (p["m"] * G / p["keff"]) * aSm0["hplus"] / 1000:
            note(corpus, "phys-floor")
            return
    note(corpus, "clean")
    geo = geo_track_from_fit(buf)
    if len(geo) < 2:
        note(corpus, "no-geo")
        return
    base = pts[0]["x"]
    geoCov = ((min(geo[len(geo) - 1]["x"], base + total) - max(geo[0]["x"], base)) / total)
    if geoCov < 0.99:
        note(corpus, "geo-span")
        return
    for q in geo:
        if (q["lon"] < BBOX["lonMin"] or q["lon"] > BBOX["lonMax"]
                or q["lat"] < BBOX["latMin"] or q["lat"] > BBOX["latMax"]):
            note(corpus, "bbox")
            return

    d5, d30 = grid_positions(total, 5), grid_positions(total, 30)
    g5 = lon_lat_at(geo, [d + base for d in d5])
    g30 = lon_lat_at(geo, [d + base for d in d30])
    s5 = build_dem_profile(d5, sample_raster(DEM5, g5["lons"], g5["lats"], "igc5"),
                           RASTER_FLOOR)
    s30 = build_dem_profile(d30, sample_raster(DEM30, g30["lons"], g30["lats"], "igc30"),
                            RASTER_FLOOR)
    if (not s5["prof"] or not s30["prof"]
            or s5["validFrac"] < 0.99 or s30["validFrac"] < 0.99):
        note(corpus, "coverage")
        return

    pw = pw_from(bin_grades(point_regime_data(pts), CLIMB_THR, DESC_THR), pts)
    vf = flat_eq_speed(pw["flat"], p)

    # ----- portal overlay -----
    # From here on an exception is a HARNESS bug, never a bad file: escalate to GateError
    # so the drivers' igc-style `except Exception → unparseable` can never swallow it.
    try:
        ways = ways_for_bbox(min(g5["lats"]), max(g5["lats"]),
                             min(g5["lons"]), max(g5["lons"]))
        crossings = match_crossings(d5, g5["lons"], g5["lats"], ways)
        iv5, iv30 = [], []
        if crossings:
            ab_lons, ab_lats = [], []
            for c in crossings:
                ab_lons += [c["lonLO"], c["lonHI"]]
                ab_lats += [c["latLO"], c["latHI"]]
            h5 = sample_raster(DEM5, ab_lons, ab_lats, "abut5")
            h30 = sample_raster(DEM30, ab_lons, ab_lats, "abut30")
            for k, c in enumerate(crossings):
                vals = (h5[2 * k], h5[2 * k + 1], h30[2 * k], h30[2 * k + 1])
                if not all(is_finite(v) and v > RASTER_FLOOR for v in vals):
                    tally("abutment-nodata")
                    continue
                iv5.append((c["xlo"], c["xhi"], float(h5[2 * k]), float(h5[2 * k + 1])))
                iv30.append((c["xlo"], c["xhi"], float(h30[2 * k]), float(h30[2 * k + 1])))
        spans_matched = len(iv5)

        prof5_port = apply_deck(s5["prof"], iv5)   # same code path for every ride
        prof30_port = apply_deck(s30["prof"], iv30)

        v2_5r, r0_5r, v2_30r = energies(s5["prof"], s30["prof"], p, pw, vf, eps_rule)
        v2_5p, r0_5p, v2_30p = energies(prof5_port, prof30_port, p, pw, vf, eps_rule)
    except GateError:
        raise
    except Exception as ex:
        raise GateError(f"portal stage error ({corpus}, ride #{len(rows)}): "
                        f"{type(ex).__name__}: {ex}") from ex

    if spans_matched == 0:   # gate 1: the no-op invariant, float-exact
        if not (v2_5p == v2_5r and r0_5p == r0_5r and v2_30p == v2_30r):
            raise GateError(f"no-op invariant broken (corpus={corpus}, ride #{len(rows)})")
        NOOP_CHECKED[0] += 1
    if abs(prof5_port["x"][-1] - total) > 1e-6 or abs(prof30_port["x"][-1] - total) > 1e-6:
        raise GateError("corrected profile distance != raw")

    rows.append({
        "corpus": corpus, "ride": label, "emp": emp,
        "spans_matched": spans_matched,
        "span_m": merged_len(iv5) if iv5 else 0.0,
        "dh_plus_removed_igc5": hplus_of(s5["prof"]) - hplus_of(prof5_port),
        "v2_igc5_raw": v2_5r, "v2_igc5_port": v2_5p,
        "r0_igc5_raw": r0_5r, "r0_igc5_port": r0_5p,
        "v2_igc30_raw": v2_30r, "v2_igc30_port": v2_30p,
        "d_v2_5r": d_pct(v2_5r, emp), "d_v2_5p": d_pct(v2_5p, emp),
        "d_r0_5r": d_pct(r0_5r, emp), "d_r0_5p": d_pct(r0_5p, emp),
        "d_v2_30r": d_pct(v2_30r, emp), "d_v2_30p": d_pct(v2_30p, emp),
    })
    note(corpus, "included")


# ===== reporting =====
COLS = ["corpus", "ride", "emp", "spans_matched", "span_m", "dh_plus_removed_igc5",
        "v2_igc5_raw", "v2_igc5_port", "r0_igc5_raw", "r0_igc5_port",
        "v2_igc30_raw", "v2_igc30_port"]

CORP = [["censo", "censo (urban group rides, assumed rider)"],
        ["ppaz", "P. Paz (open, frozen physics)"],
        ["jaam", "JAAM (open, frozen physics)"],
        ["danlessa", "author full (open, frozen physics)"]]


def by_group(g):
    if g == "pooled":
        return [r for r in rows if r["corpus"] != "censo"]
    if g == "all":
        return list(rows)
    return [r for r in rows if r["corpus"] == g]


def p90(vals):
    if not vals:
        return float("nan")
    v = sorted(vals)
    return v[math.floor(0.9 * (len(v) - 1))]


def _pair_stats(st, kr, kp):
    """med|Δ%| and med signed Δ% for raw vs port + their deltas, on rides where both finite."""
    pr = [(r[kr], r[kp]) for r in st if is_finite(r[kr]) and is_finite(r[kp])]
    if not pr:
        return None
    ma_r = med_of([abs(a) for a, _ in pr])
    ma_p = med_of([abs(b) for _, b in pr])
    b_r = med_of([a for a, _ in pr])
    b_p = med_of([b for _, b in pr])
    return {"n": len(pr), "ma_r": ma_r, "ma_p": ma_p, "dma": ma_p - ma_r,
            "b_r": b_r, "b_p": b_p, "db": b_p - b_r,
            "p90_r": p90([abs(a) for a, _ in pr]), "p90_p": p90([abs(b) for _, b in pr])}


def _line(tag, s):
    if not s:
        return f"  {tag.ljust(10)} (no rides)"
    return (f"  {tag.ljust(10)} med|Δ%| {f(s['ma_r'], 2)} → {f(s['ma_p'], 2)} "
            f"(Δ {f(s['dma'], 3)} pp) · bias {f(s['b_r'], 2)} → {f(s['b_p'], 2)} "
            f"(Δ {f(s['db'], 3)} pp) · p90|Δ%| {f(s['p90_r'], 1)} → {f(s['p90_p'], 1)}"
            f"   (n={s['n']})")


def main():
    smoke = os.environ.get("E26_SMOKE") == "1"
    limit = 15 if smoke else None
    os.makedirs(RESULTS, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    ensure_dem30()

    t0 = time.time()
    with open(os.path.join(DATA, "censohidrografico", "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    for e in man:
        if limit and len(rows) >= limit:
            break
        if not e.get("file") or not os.path.exists(os.path.join(DATA, e["file"])):
            continue
        try:
            process_ride(e["file"], ASSUMED, e.get("name"), "censo", "urban")
        except GateError:
            raise
        except Exception:
            note("censo", "unparseable")
    for corpus, manifest in (["ppaz", "strava_ppaz_manifest.json"],
                             ["jaam", "strava_jaam_manifest.json"],
                             ["danlessa", "strava_danlessa_manifest.json"]):
        if limit and len(rows) >= limit:
            break
        with open(os.path.join(DATA, manifest), encoding="utf-8") as fh:
            man = json.load(fh)
        cand = [a for a in man if a.get("sport") == "ride" and jgt(a.get("powCov"), 0.5)
                and jge(a.get("km"), 20) and jge(a.get("altCov"), 0.99)]
        n = 0
        for a in cand:
            if limit and len(rows) >= limit:
                break
            try:
                process_ride(a["file"], PHYS[corpus], a.get("id"), corpus, "open")
            except GateError:
                raise
            except Exception:
                note(corpus, "unparseable")
            n += 1
            if n % 100 == 0:
                print(f"  …{corpus} {n}/{len(cand)} ({(time.time() - t0):.0f} s)",
                      file=sys.stderr)
    print(f"sampling ms: {json.dumps(IGC.sample_ms, separators=(',', ':'))} · "
          f"overpass tiles: {json.dumps(fetch_stats, separators=(',', ':'))} · "
          f"ways cached: {len(WAYS)} · total {(time.time() - t0):.0f} s", file=sys.stderr)

    # ===== report (aggregates only — no ride names) =====
    print("ENTRY 26 Q2A — portal-corrected profiles (OSM bridges/tunnels, v19 straight "
          "deck) vs raw, PAIRED" + ("   [SMOKE: first 15 rides]" if smoke else ""))
    print(f"DEM: {DEM5} (igc5) + 30 m warp (igc30) · spans: Overpass highway+bridge/tunnel, "
          f"{len(WAYS)} ways over {fetch_stats['tiles']} tile pulls "
          f"({fetch_stats['network']} network, {fetch_stats['cached']} cached)")
    print(f"matching: ≤{f(MATCH_DIST_M, 0)} m to span, heading ≤{f(MATCH_HEAD_DEG, 0)}° "
          f"(mod 180), coverage ≥{f(MIN_COVER * 100, 0)}% of deckLenM · "
          f"crossing drops: {json.dumps(drop, separators=(',', ':')) if drop else '{}'}")

    print("\nCORPUS FUNNEL (clean per corpus filters → included):")
    for c, _t in CORP:
        e = excl.get(c) or {}
        print(f"  {c.ljust(9)} clean={e.get('clean') or 0} → included={e.get('included') or 0}"
              f"   [excl: bbox={e.get('bbox') or 0} coverage={e.get('coverage') or 0}"
              f" geo-span={e.get('geo-span') or 0} no-geo={e.get('no-geo') or 0}]"
              f" (pre-clean skips: no-power={e.get('no-power') or 0}"
              f" phys-floor={e.get('phys-floor') or 0} zwift={e.get('zwift') or 0}"
              f" unparseable={e.get('unparseable') or 0} no-emp={e.get('no-emp') or 0}"
              f" gpx={e.get('gpx-unsupported') or 0})")
    print(f"  pooled riders n={len(by_group('pooled'))} · censo n={len(by_group('censo'))} "
          f"· all n={len(rows)}")

    print("\nPAIRED raw → portal-corrected, vs measured ∫P·dt:")
    for g, title in [*CORP, ["pooled", "POOLED independent riders (ppaz+jaam+danlessa)"],
                     ["all", "ALL (censo + riders)"]]:
        st = by_group(g)
        if not st:
            continue
        tc = [r for r in st if r["spans_matched"] > 0]
        print(f"\n── {title} ──  n={len(st)} · touched (≥1 span) "
              f"{len(tc)}/{len(st)} ({f(100 * len(tc) / len(st), 1)}%)")
        print(" ALL rides:")
        print(_line("v2@igc5", _pair_stats(st, "d_v2_5r", "d_v2_5p")))
        print(_line("R0@igc5", _pair_stats(st, "d_r0_5r", "d_r0_5p")))
        print(_line("v2@igc30", _pair_stats(st, "d_v2_30r", "d_v2_30p")))
        if tc:
            print(" TOUCHED rides:")
            print(_line("v2@igc5", _pair_stats(tc, "d_v2_5r", "d_v2_5p")))
            print(_line("R0@igc5", _pair_stats(tc, "d_r0_5r", "d_r0_5p")))
            print(_line("v2@igc30", _pair_stats(tc, "d_v2_30r", "d_v2_30p")))
            ndrop = sum(1 for r in tc if r["dh_plus_removed_igc5"] > 0)
            print(f"  h₊ removed (igc5): drops on {ndrop}/{len(tc)} "
                  f"({f(100 * ndrop / len(tc), 1)}%) · med removed "
                  f"{f(med_of([r['dh_plus_removed_igc5'] for r in tc]), 1)} m · med span "
                  f"{f(med_of([r['span_m'] for r in tc]), 0)} m · med spans/ride "
                  f"{f(med_of([r['spans_matched'] for r in tc]), 0)}")

    # ===== pre-registered verdicts (P5–P7) =====
    print("\n================ PRE-REGISTERED PREDICTIONS ================")
    tc_all = [r for r in rows if r["spans_matched"] > 0]
    s_v2 = _pair_stats(tc_all, "d_v2_5r", "d_v2_5p") if tc_all else None
    s_r0 = _pair_stats(tc_all, "d_r0_5r", "d_r0_5p") if tc_all else None
    if s_v2 and s_r0:
        p5 = s_v2["db"] < 0 and s_r0["db"] < 0
        print(f"  P5 (bias moves DOWN on touched rides): Δbias v2@igc5 {f(s_v2['db'], 3)} pp, "
              f"R0@igc5 {f(s_r0['db'], 3)} pp → {'CONFIRMED' if p5 else 'REFUTED'}")
        scatter_worse = s_v2["dma"] > 0 and s_r0["dma"] > 0
        if not p5 or scatter_worse:
            print("     FALSIFIER WATCH: bias up and/or scatter worse on touched rides — "
                  "diagnose (straight-deck model vs OSM-matching contamination) before any "
                  "deployment claim.")
    else:
        print("  P5: no touched rides — not evaluable on this subset")
    a_v2 = _pair_stats(rows, "d_v2_5r", "d_v2_5p")
    a_r0 = _pair_stats(rows, "d_r0_5r", "d_r0_5p")
    if a_v2 and a_r0:
        p6 = abs(a_v2["dma"]) < 1 and abs(a_r0["dma"]) < 1
        cen = [r for r in by_group("censo") if r["spans_matched"] > 0]
        rid = [r for r in by_group("pooled") if r["spans_matched"] > 0]
        c_v2 = _pair_stats(cen, "d_v2_5r", "d_v2_5p") if cen else None
        r_v2 = _pair_stats(rid, "d_v2_5r", "d_v2_5p") if rid else None
        print(f"  P6 (pooled median moves < 1 pp): Δmed|Δ%| all-rides v2@igc5 "
              f"{f(a_v2['dma'], 3)} pp, R0@igc5 {f(a_r0['dma'], 3)} pp → "
              f"{'CONFIRMED' if p6 else 'REFUTED'}")
        print(f"     touched-tail Δp90|Δ%| (v2@igc5): censo "
              f"{f(c_v2['p90_p'] - c_v2['p90_r'], 2) if c_v2 else '—'} pp · riders "
              f"{f(r_v2['p90_p'] - r_v2['p90_r'], 2) if r_v2 else '—'} pp "
              f"(prediction: improvement concentrated on censo)")
    if tc_all:
        ndrop = sum(1 for r in tc_all if r["dh_plus_removed_igc5"] > 0)
        share = 100 * ndrop / len(tc_all)
        print(f"  P7 (h₊ drops on ≥ 90% of touched rides): {ndrop}/{len(tc_all)} "
              f"({f(share, 1)}%) → {'CONFIRMED' if share >= 90 else 'REFUTED'}")
    else:
        print("  P7: no touched rides — not evaluable on this subset")

    # ===== sanity gates =====
    print("\n================ SANITY GATES ================")
    ok = True

    def say(name, passed, extra=""):
        nonlocal ok
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}{('  ' + extra) if extra else ''}")
        if not passed:
            ok = False

    nz = sum(1 for r in rows if r["spans_matched"] == 0)
    say("no-op invariant: zero-span rides reproduce raw energies EXACTLY (float-equal, "
        "same code path)", NOOP_CHECKED[0] == nz,
        f"{NOOP_CHECKED[0]}/{nz} zero-span rides byte-checked")
    say("corrected profile distance ≡ raw (shared x array; totals asserted per ride)", True)
    say("deck interpolation bounded by abutment heights",
        DECK_BOUND_WORST[0] <= 1e-9, f"worst exceedance {DECK_BOUND_WORST[0]:.2e} m")
    print("\nSANITY: ALL PASS" if ok else "\nSANITY: FAILURES ABOVE")

    # ===== CSV (gitignored via data/results/*) =====
    out = [",".join(COLS)]
    for r in rows:
        out.append(",".join(cell4(r.get(k)) for k in COLS))
    with open(os.path.join(RESULTS, "e26_portal_profiles.csv"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"\nwrote e26_portal_profiles.csv ({len(rows)} rides)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
