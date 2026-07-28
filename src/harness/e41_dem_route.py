#!/usr/bin/env python3
"""Entry 41 — the elevation-source substitution: paper 1's law on planner DEM profiles.

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 41 BEFORE any full run.

ONE substitution, everything else held: the elevation profile comes from a DEM
sampled along the recorded track instead of from the ride's own barometer.
Measured power, per-ride regime powers, the physics constants, ε₀, τ, c — all
unchanged within a protocol.  So every gap between an arm and the `own` control
is the elevation source and nothing else.

Seven elevation arms, ALL on the ride's own 5 m arc-length grid (a coarser
polyline step is sampled at that step and linearly interpolated back onto the
5 m grid — linear interpolation adds no local extrema, so h± and the τ = 2 m
deadband are unaffected by the re-gridding and only the SOURCE varies):

  own      recorded barometric stream                      (paper-1 control)
  igc5     IGC-SP 2010 5 m DTM, polyline step 5 m          (naive fine planner)
  igc5s10  the same, 1-D Gaussian σ = 10 m along the polyline   (Entry 20's σ*)
  igc5s30  the same, σ = 30 m                              (the 30 m calibration scale)
  igc30    the same raster, polyline step 30 m             (the free knob)
  fab5     FABDEM V1-2 (30 m global), polyline step 5 m    (quilojaules' source)
  fab30    FABDEM V1-2, polyline step 30 m

TWO PHYSICS PROTOCOLS per arm (registration amendment, Danilo, before results):
  reg  per-ride regime-consistent constants (m̂, Ĉrr, ĈdA_reg, wind) joined from
       e35_residual.csv — paper 1 Table 6's protocol.  PRIMARY.  At the frozen
       priors every corpus carries a standing bias, and an elevation-source change
       partly cancels or amplifies it, so med|Δ%| would read the bias rather than
       the source (Entry 17's bias-trade law; Entry 19 saw exactly this on JAAM).
       The honest (α, ε) pair at this α is ε_d everywhere (Entry 35).
  frz  paper 1's frozen priors.  Kept so the PARITY gate still has a published
       reference, and as the protocol contrast.

Models per arm: F1–F4 × {ε_d, ε_f} + the forward simulation.  The CSV stores the
closed form's COMPONENTS per arm (a_roll, a_aero, X, h±, aero gated/ungated,
smoothed h±), so every F-variant at any ε and any noise rate c is arithmetic
afterwards — which is what the registered per-source c refit (P3) needs.

QA gates (pre-registered; applied identically to every arm, so no arm is
advantaged).  The wide IGC raster is the full 2010 survey and its quality is not
homogeneous (seams; patches that behave as a DSM rather than a DTM), so:
  G1 track    the share of route length inside GPS-fix gaps > 50 m must be ≤ 0.5%.
              A planner's polyline has no dropouts; where the recording lost GPS the
              track is a straight chord and the DEM charges terrain the rider never
              crossed.  THIS GATE COMES FIRST — the largest profile artifacts on the
              deployed raster are track dropouts, not raster defects.  The share, not
              the max gap: a max-gap threshold scales with ride length and deletes D1.
  G2 validity ≥ 99% of samples with 0.5 m < h < 3000 m, on every arm.
  G3 anomaly  a one-step |Δh| > 10 m over a 5 m step (200% grade) is a defect, not
              terrain.  Counted per arm and REPORTED; the primary population keeps
              these rides and a registered secondary repeats the table without them.

Run:  python3 src/harness/e41_dem_route.py            (full; ~1 h cold, ~10 min warm)
      E41_SMOKE=1 python3 src/harness/e41_dem_route.py  (40 rides/corpus, no gates asserted)
Output: data/results/e41_dem_route.csv + console scoreboard.
Needs the conda python (gdal): /Users/danlessa/conda/bin/python.

MODULE IS IMPORT-SAFE — the driver lives in main().
"""

from __future__ import annotations

import gzip
import json
import math
import os
import subprocess
import sys
import time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from igc_resolution_test import (geo_track_from_fit, grid_positions,  # noqa: E402
                                 lon_lat_at, sample_raster)
from bicycling_energy_model import (approx_components, approximate,  # noqa: E402
                                    build_profile, canonical, deadband,
                                    empirical_kj, eps_geom,
                                    extract_regime_powers, flat_eq_speed,
                                    haversine, is_finite, jsdiv, load_pts,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G  # noqa: E402
from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

DATA = os.path.join(REPO, "data", "inputs", "activities")
RESULTS = os.path.join(REPO, "data", "results")
SCRATCH = os.path.join(RESULTS, "cache", "dem")
os.makedirs(SCRATCH, exist_ok=True)

# E41_SMOKE=1 -> 40 rides/corpus; E41_SMOKE=<n> -> n rides/corpus (iteration).
_smoke = os.environ.get("E41_SMOKE")
SMOKE = bool(_smoke)
SMOKE_N = 40 if _smoke in (None, "", "1") else int(_smoke)

# ---- rasters -------------------------------------------------------------
# The WIDE IGC-SP 2010 survey (5 m, EPSG:31983) — supersedes the validated
# sampa_geral.tif crop used by Entries 19–21, which covers only the censo bbox
# (0 of 44 D1 rides fall inside it).  On their overlap the two agree to 0.01 m
# median; the only >10 m disagreements are where the CROP runs off its own edge
# and reads 0.  Quality across the wider footprint is not homogeneous — hence G3.
IGC_WIDE = "/Users/danlessa/Documents/projects-qgis/mdt-igc-2010/mdt_igc_2010.tif"
FABDEM_DIR = os.path.join(SCRATCH, "fabdem")
FABDEM_VRT = os.path.join(SCRATCH, "fabdem_mosaic.vrt")
FABDEM_URL = "https://telhas.pedalhidrografi.co/fabdem/{tile}_FABDEM_V1-2.tif"

# ---- protocol constants (paper 1, frozen — never re-fitted here) ----------
FROZEN = {"Crr": 0.008, "CdA": 0.40, "rho": 1.13, "keff": 0.98, "wind": 0.0}
VMAX, VSTART = 38 / 3.6, 15 / 3.6
CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH = 0.02, -0.015, 5, 2
C_FROZEN = 3.0          # m/km — paper 1's ascent-noise rate, F4's scalar
EPS_F = 0.20            # the flat ε constant
# per-corpus mass: D1 logged per ride; D2 the generic prior; D3–D5 the
# sustained-climb inversion (paper 1 §2.3.2).  m̂·g is the invariant — these
# move with G and must never be frozen independently of it.
ANCHOR_M = {"longoes": None, "censo": 78.0, "ppaz": 74.5, "jaam": 101.9,
            "danlessa": 74.7}
PRIMARY_PROTO = "reg"           # the physics the headline is quoted at
PROTOCOLS = ("frz", "reg")      # frozen priors · regime-consistent per-ride physics
PROTO_LABEL = {"frz": "frozen priors", "reg": "regime-consistent per-ride"}
CORPORA = ("longoes", "censo", "ppaz", "jaam", "danlessa")
CORPUS_LABEL = {"longoes": "D1 longões", "censo": "D2 censo", "ppaz": "D3 P. Paz",
                "jaam": "D4 JAAM", "danlessa": "D5 author-full"}

# ---- QA thresholds (pre-registered) --------------------------------------
GAP_MIN = 50.0          # G1: a fix-to-fix gap beyond this is chord-interpolated
GAP_FRAC_MAX = 0.005    # G1: allowed share of route length inside such gaps
VALID_MIN = 0.99        # G2: fraction of samples inside the elevation band
ELEV_LO, ELEV_HI = 0.5, 3000.0
ANOM_STEP = 10.0        # G3: one-step |Δh| over a 5 m step that is a defect, m
# Conservative INNER rectangle of mdt_igc_2010.tif's footprint in WGS84 (the raster
# is a UTM-23S quad, so its lon/lat hull is not a rectangle — this is the largest
# rectangle inside it).  A pure pre-filter: rides outside it have no IGC elevation at
# all and G2 would drop them anyway, so skipping them early changes no result and
# saves fetching FABDEM tiles for Roraima, Lombardy and Poland.
IGC_BBOX = {"lonMin": -53.0248, "lonMax": -44.1360,
            "latMin": -25.1822, "latMax": -19.8283}

# ---- arms ----------------------------------------------------------------
# (name, source, polyline step m, gaussian sigma m)
ARMS = [("own", "own", 5, 0.0),
        ("igc5", "igc", 5, 0.0),
        ("igc5s10", "igc", 5, 10.0),
        ("igc5s30", "igc", 5, 30.0),
        ("igc30", "igc", 30, 0.0),
        ("fab5", "fab", 5, 0.0),
        ("fab30", "fab", 30, 0.0)]
ARM_NAMES = [a[0] for a in ARMS]
DEM_ARMS = [a for a in ARM_NAMES if a != "own"]

CACHE_BIN = os.path.join(SCRATCH, "e41_profiles_smoke.bin" if SMOKE
                         else "e41_profiles.bin")
CACHE_META = os.path.join(SCRATCH, "e41_profiles_smoke.meta.json" if SMOKE
                          else "e41_profiles.meta.json")
CACHE_VERSION = 1


def _unquote(x: str) -> str:
    """Strip the surrounding quotes the harness CSVs put on string cells."""
    return x[1:-1] if len(x) >= 2 and x[0] == '"' and x[-1] == '"' else x


def load_e35() -> dict:
    """Per-ride regime-consistent physics (Entry 35 / paper Table 6), keyed the way
    that harness keys rides: the ride label on D1, the track basename elsewhere."""
    path = os.path.join(RESULTS, "e35_residual.csv")
    if not os.path.exists(path):
        return {}
    out = {}
    # the harness CSVs quote string cells ("longoes","S. Pedro",…) — strip them, or
    # every key silently misses and the whole protocol falls back to the priors.
    with open(path, encoding="utf-8") as fh:
        head = [_unquote(h) for h in fh.readline().rstrip("\n").split(",")]
        for line in fh:
            c = [_unquote(x) for x in line.rstrip("\n").split(",")]
            if len(c) < len(head):
                continue
            r = dict(zip(head, c))
            try:
                out[(r["corpus"], r["ride"])] = {
                    "m": float(r["m"]), "Crr": float(r["crr"]),
                    "CdA": float(r["cda_reg"]), "wind": float(r["wind"])}
            except (KeyError, ValueError):
                continue
    return out


E35 = load_e35()


# ===== small statistics (house convention: mulberry32, B = 10⁴, seeds 42/43) =====
def med_of(xs) -> float:
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
    vals = [x for x in values if is_finite(x)]
    if len(vals) < 2:
        return float("nan"), float("nan")
    rand = rng(seed)
    n, B = len(vals), 10000
    stats = sorted(med_of([vals[int(rand() * n)] for _ in range(n)]) for _ in range(B))
    return stats[math.floor(0.025 * B)], stats[math.ceil(0.975 * B) - 1]


def sign_p(w: int, l: int) -> float:
    n = w + l
    if n == 0:
        return float("nan")
    p = 0.0
    for k in range(n + 1):
        pk = math.comb(n, k) / 2 ** n
        if k <= min(w, l) or k >= max(w, l):
            p += pk
    return min(1.0, p)


# ===== profile helpers =====
def gauss1d(h: list[float], sigma_m: float, dx: float = 5.0,
            trunc: float = 3.0) -> list[float]:
    """Mask-normalized 1-D Gaussian along the polyline — the profile-space twin
    of goal_smooth_rasters' deployable raster scheme (Entry 20), and the form a
    planner can actually run: it needs the polyline, not the raster."""
    if sigma_m <= 0:
        return list(h)
    s = sigma_m / dx
    r = int(math.ceil(trunc * s))
    k = [math.exp(-0.5 * (i / s) ** 2) for i in range(-r, r + 1)]
    n = len(h)
    out = [0.0] * n
    for i in range(n):
        lo, hi = max(0, i - r), min(n - 1, i + r)
        acc = wsum = 0.0
        for m in range(lo, hi + 1):
            wt = k[m - i + r]
            acc += wt * h[m]
            wsum += wt
        out[i] = acc / wsum
    return out


def regrid(xs_coarse: list[float], h_coarse: list[float],
           xs_fine: list[float]) -> list[float]:
    """Linear interpolation of a coarse-step profile onto the 5 m grid. Adds no
    local extrema, so h±, the deadband and ε_coast read the coarse geometry."""
    out = [0.0] * len(xs_fine)
    j = 0
    for i, d in enumerate(xs_fine):
        while j < len(xs_coarse) - 2 and xs_coarse[j + 1] < d:
            j += 1
        a, b = xs_coarse[j], xs_coarse[j + 1]
        f = 0.0 if b - a < 1e-9 else (d - a) / (b - a)
        f = max(0.0, min(1.0, f))
        out[i] = h_coarse[j] * (1 - f) + h_coarse[j + 1] * f
    return out


def sum_ascent(h) -> float:
    return sum(max(0.0, h[i] - h[i - 1]) for i in range(1, len(h)))


def anomaly_census(h) -> tuple[int, float]:
    """G3: one-step |Δh| beyond ANOM_STEP, and the ascent those steps inject."""
    n = 0
    inj = 0.0
    for i in range(1, len(h)):
        d = h[i] - h[i - 1]
        if abs(d) > ANOM_STEP:
            n += 1
            if d > 0:
                inj += d
    return n, inj


def valid_fill(vals: list[float]) -> tuple[list[float] | None, float]:
    """Validity band + linear gap fill (Entry 19's build_dem_profile, with an
    upper bound added: the wide survey stores voids as huge magnitudes)."""
    n = len(vals)
    h = [v if (is_finite(v) and ELEV_LO < v < ELEV_HI) else float("nan") for v in vals]
    n_bad = sum(1 for v in h if v != v)
    frac = 1 - n_bad / n
    if n_bad:
        first = next((i for i in range(n) if is_finite(h[i])), -1)
        if first < 0:
            return None, frac
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
    return h, frac


# ===== FABDEM mosaic =====
def fabdem_tile(lat: float, lon: float) -> str:
    la, lo = math.floor(lat), math.floor(lon)
    return (f"{'S' if la < 0 else 'N'}{abs(la):02d}"
            f"{'W' if lo < 0 else 'E'}{abs(lo):03d}")


def ensure_fabdem(tiles: set[str]) -> bool:
    """Fetch the 1°×1° FABDEM tiles the corpora touch and build a VRT.  A 1° cell
    is the coarsest geographic identifier there is and the host is the
    collective's own server — no ride-derived geometry leaves the machine."""
    os.makedirs(FABDEM_DIR, exist_ok=True)
    have = []
    for t in sorted(tiles):
        p = os.path.join(FABDEM_DIR, f"{t}_FABDEM_V1-2.tif")
        if not os.path.exists(p):
            print(f"  fetching FABDEM {t}…", file=sys.stderr)
            r = subprocess.run(["curl", "-sSf", "-o", p, FABDEM_URL.format(tile=t)])
            if r.returncode != 0:
                if os.path.exists(p):
                    os.remove(p)
                print(f"  (no FABDEM tile {t} — arm unavailable there)", file=sys.stderr)
                continue
        have.append(p)
    if not have:
        return False
    subprocess.run(["gdalbuildvrt", "-overwrite", FABDEM_VRT] + have,
                   stdout=subprocess.DEVNULL, check=True)
    return True


# ===== corpus drivers (paper-1 clean-corpus filters, verbatim) =====
def iter_corpus(name: str):
    """Yield (rel_path, ride_label, logged_mass_or_None) per candidate ride."""
    if name == "longoes":
        for e in json.load(open(os.path.join(DATA, "model_inputs.json"))):
            if not e.get("file") or not e.get("has_power"):
                continue
            yield (e["file"], e["label"], e["m"])
        return
    if name == "censo":
        man = json.load(open(os.path.join(DATA, "censohidrografico", "manifest.json")))
        for e in man:
            if e.get("file") and os.path.exists(os.path.join(DATA, e["file"])):
                yield (e["file"], e.get("name") or os.path.basename(e["file"]), None)
        return
    man = json.load(open(os.path.join(DATA, f"strava_{name}_manifest.json")))
    for a in man:
        if (a.get("sport") == "ride" and (a.get("powCov") or 0) > 0.5
                and (a.get("km") or 0) >= 20 and (a.get("altCov") or 0) >= 0.99):
            yield (a["file"], a["id"], None)


ZWIFT = 260


def read_buf(rel: str) -> bytes:
    with open(os.path.join(DATA, rel), "rb") as fh:
        b = fh.read()
    return gzip.decompress(b) if rel.endswith(".gz") else b


# ===== phase 1: geometry + raster sampling (cached) =====
def build_geometry(rel: str, label: str, corpus: str) -> dict | None:
    """The ride's 5 m arc grid, its lat/lon, the track-gap statistic and the
    sampled DEM columns.  Returns None when the ride is not a candidate at all."""
    meta: dict = {}
    pts = load_pts(os.path.join(DATA, rel), meta)
    if corpus not in ("censo", "longoes") and meta.get("manufacturer") == ZWIFT:
        return {"skip": "zwift"}
    emp = empirical_kj(pts)
    if not (is_finite(emp) and emp > 0):
        return {"skip": "no-emp"}
    prof5 = resample_profile(build_profile([q["x"] for q in pts],
                                           [q["alt"] for q in pts]), ENGINE_DX)
    total = prof5["x"][-1]
    if total < 3000:
        return {"skip": "too-short"}
    geo = geo_track_from_fit(read_buf(rel))
    if len(geo) < 2:
        return {"skip": "no-geo"}
    max_gap = 0.0
    gap_len = 0.0
    for i in range(1, len(geo)):
        d = haversine(geo[i - 1], geo[i])
        if d > max_gap:
            max_gap = d
        if d > GAP_MIN:
            gap_len += geo[i]["x"] - geo[i - 1]["x"]
    gap_frac = gap_len / max(1.0, geo[-1]["x"] - geo[0]["x"])
    base = pts[0]["x"]
    span = (min(geo[-1]["x"], base + total) - max(geo[0]["x"], base)) / total
    if span < 0.99:
        return {"skip": "geo-span"}
    for q in geo:
        if not (IGC_BBOX["lonMin"] <= q["lon"] <= IGC_BBOX["lonMax"]
                and IGC_BBOX["latMin"] <= q["lat"] <= IGC_BBOX["latMax"]):
            return {"skip": "outside-raster"}
    d5 = grid_positions(total, ENGINE_DX)
    d30 = grid_positions(total, 30)
    g5 = lon_lat_at(geo, [d + base for d in d5])
    g30 = lon_lat_at(geo, [d + base for d in d30])
    lats = g5["lats"]
    lons = g5["lons"]
    tiles = {fabdem_tile(lats[i], lons[i]) for i in range(0, len(lats), 200)}
    tiles.add(fabdem_tile(lats[-1], lons[-1]))
    return {"pts": pts, "prof5": prof5, "emp": emp, "total": total,
            "d5": d5, "d30": d30, "g5": g5, "g30": g30, "tiles": tiles,
            "max_gap": max_gap, "gap_frac": gap_frac, "geo_span": span,
            "label": label,
            "join": label if corpus == "longoes" else os.path.basename(rel)}


def sample_columns(geo: dict, fab_ok: bool) -> dict:
    """The four raw sampled columns: igc@5, igc@30, fab@5, fab@30."""
    out = {}
    out["igc5"] = sample_raster(IGC_WIDE, geo["g5"]["lons"], geo["g5"]["lats"], "igc5")
    out["igc30"] = sample_raster(IGC_WIDE, geo["g30"]["lons"], geo["g30"]["lats"], "igc30")
    if fab_ok:
        out["fab5"] = sample_raster(FABDEM_VRT, geo["g5"]["lons"], geo["g5"]["lats"], "fab5")
        out["fab30"] = sample_raster(FABDEM_VRT, geo["g30"]["lons"], geo["g30"]["lats"],
                                     "fab30")
    else:
        out["fab5"] = out["fab30"] = None
    return out


# ===== phase 2: models =====
def arm_profiles(geo: dict, cols: dict) -> tuple[dict, dict]:
    """arm name -> profile on the common 5 m grid, plus per-arm validity."""
    d5, d30 = geo["d5"], geo["d30"]
    profs: dict = {"own": {"x": d5, "h": list(geo["prof5"]["h"])}}
    valid = {"own": 1.0}
    base: dict = {}
    for key, xs, src in (("igc5", d5, "igc5"), ("igc30", d30, "igc30"),
                         ("fab5", d5, "fab5"), ("fab30", d30, "fab30")):
        raw = cols.get(src)
        if raw is None:
            base[key] = (None, 0.0)
            continue
        h, frac = valid_fill(raw)
        base[key] = (h, frac)
    for name, src, step, sigma in ARMS:
        if name == "own":
            continue
        h, frac = base[f"{src}{step}"]      # igc5 | igc30 | fab5 | fab30
        valid[name] = frac
        if h is None:
            profs[name] = None
            continue
        hh = h if step == ENGINE_DX else regrid(d30, h, d5)
        if sigma > 0:
            hh = gauss1d(hh, sigma, ENGINE_DX)
        profs[name] = {"x": d5, "h": hh}
    return profs, valid


def eval_arm(prof: dict, p: dict, pw: dict, vf: float) -> dict:
    """The closed form's components (so any F-variant at any ε and any c is
    arithmetic afterwards) plus the forward simulation, on one arm's profile."""
    profS = {"x": prof["x"], "h": deadband(prof["h"], TAU_SMOOTH)}
    a_raw = approx_components(prof, p, vf, CLIMB_THR)
    a_sm = approx_components(profS, p, vf, CLIMB_THR)
    mg = p["m"] * G
    aero_spd = vf + p["wind"]
    a_roll = mg * p["Crr"] / p["keff"]
    a_aero = 0.5 * p["rho"] * p["CdA"] * aero_spd * abs(aero_spd) / p["keff"]
    c = canonical(prof, pw, p)
    resid = abs(p["keff"] * c["legE"] - (c["dKE"] + c["Wrr"] + c["Waero"]
                                         + c["Wgrav"] + c["Wbrake"]))
    resid /= max(1.0, p["keff"] * c["legE"])
    epsG = eps_geom(prof, p, vf)
    n_anom, inj = anomaly_census(prof["h"])
    x_km = a_raw["X"] / 1000
    return {"X": a_raw["X"], "beta": a_raw["beta"], "a_roll": a_roll, "a_aero": a_aero,
            "hplus": a_raw["hplus"], "hminus": a_raw["hminus"], "aero_raw": a_raw["aero"],
            "hplus_sm": a_sm["hplus"], "hminus_sm": a_sm["hminus"], "aero_sm": a_sm["aero"],
            "eps_d": epsG if is_finite(epsG) else EPS_F,
            "canon": c["legE"] / 1000, "cons": resid,
            "cnoise": (a_raw["hplus"] - a_sm["hplus"]) / x_km if x_km > 0 else float("nan"),
            "n_anom": n_anom, "anom_hplus": inj}


def forms(a: dict, eps: float, c_rate: float = C_FROZEN) -> dict:
    """F1–F4 in kJ from one arm's stored components (paper 1 eq. F1–F4)."""
    roll = a["a_roll"] * a["X"]
    beta = a["beta"]
    x_km = a["X"] / 1000
    grav_raw = beta * a["hplus"] - eps * beta * a["hminus"]
    grav_sm = beta * a["hplus_sm"] - eps * beta * a["hminus_sm"]
    k = max(0.0, 1 - c_rate * x_km / a["hplus"]) if a["hplus"] > 0 else 1.0
    return {"f1": (roll + a["a_aero"] * a["X"] + grav_raw) / 1000,
            "f2": (roll + a["aero_raw"] + grav_raw) / 1000,
            "f3": (roll + a["aero_sm"] + grav_sm) / 1000,
            "f4": (roll + a["aero_raw"] + k * grav_raw) / 1000}


# ===== driver =====
def main() -> None:
    t0 = time.time()
    rows: list[dict] = []
    funnel: dict[str, dict[str, int]] = {}

    def note(c: str, k: str) -> None:
        funnel.setdefault(c, {})
        funnel[c][k] = funnel[c].get(k, 0) + 1

    # ---- pass 0: geometry for every candidate, and the FABDEM tile set ----
    print("pass 0 — geometry + track QA", file=sys.stderr)
    geos: list[tuple[str, dict]] = []
    tiles: set[str] = set()
    for corpus in CORPORA:
        n = 0
        for rel, label, m_log in iter_corpus(corpus):
            if SMOKE and n >= SMOKE_N:
                break
            n += 1
            note(corpus, "candidate")
            try:
                g = build_geometry(rel, label, corpus)
            except Exception:
                note(corpus, "unparseable")
                continue
            if g is None or "skip" in g:
                note(corpus, (g or {}).get("skip", "unparseable"))
                continue
            g["corpus"] = corpus
            g["rel"] = rel
            g["m_log"] = m_log
            geos.append((corpus, g))
            tiles |= g["tiles"]
        print(f"  {corpus}: {n} candidates, {len(geos)} kept so far "
              f"({to_fixed(time.time() - t0, 0)} s)", file=sys.stderr)

    fab_ok = ensure_fabdem(tiles)
    print(f"FABDEM tiles: {len(tiles)} touched, mosaic {'built' if fab_ok else 'UNAVAILABLE'}",
          file=sys.stderr)

    # ---- pass 1: raster sampling, cached on disk ----
    print("pass 1 — raster sampling", file=sys.stderr)
    cache = load_cache(geos)
    if cache is None:
        cache = build_cache(geos, fab_ok)

    # ---- pass 2: models ----
    print("pass 2 — models", file=sys.stderr)
    cons_max = 0.0
    for i, (corpus, g) in enumerate(geos):
        cols = cache_cols(cache, i, g)
        profs, valid = arm_profiles(g, cols)
        if profs.get("igc5") is None:
            note(corpus, "no-igc")
            continue
        pts = g["pts"]
        rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
        flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
        pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
              "flat": flat,
              "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
              "climbThr": CLIMB_THR, "descThr": DESC_THR}
        m_frz = g["m_log"] if g["m_log"] is not None else ANCHOR_M[corpus]
        j35 = E35.get((corpus, g["join"]))
        phys = {"frz": {**FROZEN, "m": m_frz, "vmax": VMAX, "vstart": VSTART}}
        phys["reg"] = ({"m": j35["m"], "Crr": j35["Crr"], "CdA": j35["CdA"],
                        "rho": FROZEN["rho"], "keff": FROZEN["keff"],
                        "wind": j35["wind"], "vmax": VMAX, "vstart": VSTART}
                       if j35 else dict(phys["frz"]))
        row = {"corpus": corpus, "ride": g["label"], "emp": g["emp"],
               "km": g["total"] / 1000, "m_frz": m_frz,
               "m_reg": phys["reg"]["m"], "cda_reg": phys["reg"]["CdA"],
               "crr_reg": phys["reg"]["Crr"], "wind_reg": phys["reg"]["wind"],
               "e35_join": int(j35 is not None),
               "max_gap": g["max_gap"], "gap_frac": g["gap_frac"],
               "geo_span": g["geo_span"]}
        armdat = {}
        for proto in PROTOCOLS:
            p = phys[proto]
            vf = flat_eq_speed(pw["flat"], p)
            row[f"vf_kmh_{proto}"] = vf * 3.6
            for name in ARM_NAMES:
                prof = profs.get(name)
                if prof is None:
                    row[f"{name}_ok"] = 0
                    continue
                a = eval_arm(prof, p, pw, vf)
                cons_max = max(cons_max, a["cons"])
                row[f"{name}_ok"] = 1
                row[f"{name}_valid"] = valid.get(name, 1.0)
                if proto == "frz":
                    armdat[name] = a
                    # geometry is protocol-independent — write it once
                    for k in ("hplus", "hminus", "hplus_sm", "cnoise",
                              "n_anom", "anom_hplus", "X"):
                        row[f"{name}_{k}"] = a[k]
                row[f"{name}_{proto}_eps_d"] = a["eps_d"]
                row[f"{name}_{proto}_canon_d"] = jsdiv(a["canon"] - g["emp"],
                                                       g["emp"]) * 100
                for tag, eps in (("d", a["eps_d"]), ("f", EPS_F)):
                    F = forms(a, eps)
                    for fk in ("f1", "f2", "f3", "f4"):
                        row[f"{name}_{proto}_{fk}{tag}"] = jsdiv(
                            F[fk] - g["emp"], g["emp"]) * 100
                # components kept so a per-source c refit is arithmetic (P3)
                for k in ("beta", "a_roll", "a_aero", "aero_raw", "aero_sm",
                          "hminus_sm"):
                    row[f"{name}_{proto}_{k}"] = a[k]
        # paper-1 physical floor, at the FROZEN protocol exactly as the
        # *_compare harnesses define it (β·h̃₊/1000 ≤ measured) — so the
        # population stays paper 1's, independent of the physics amendment
        own = armdat.get("own")
        row["dataOK"] = int(bool(own) and g["emp"] >= own["beta"] * own["hplus_sm"] / 1000)
        row["g1_track"] = int(g["gap_frac"] <= GAP_FRAC_MAX)
        row["g2_valid"] = int(all(row.get(f"{n_}_valid", 1.0) >= VALID_MIN
                                  for n_ in ARM_NAMES if row.get(f"{n_}_ok")))
        row["g3_clean"] = int(all(row.get(f"{n_}_n_anom", 0) == 0
                                  for n_ in ARM_NAMES if row.get(f"{n_}_ok")))
        rows.append(row)
        if (i + 1) % 100 == 0:
            print(f"  …{i + 1}/{len(geos)} ({to_fixed(time.time() - t0, 0)} s)",
                  file=sys.stderr)

    write_csv(rows)          # first: the report is long, the CSV must survive it
    report(rows, funnel, cons_max)
    ok = run_gates(rows, geos, cons_max)
    sys.exit(0 if (ok or SMOKE) else 1)


# ===== raster-sampling cache =====
def cache_key(geos) -> str:
    return ";".join(f"{c}|{g['label']}|{len(g['d5'])}" for c, g in geos)


def load_cache(geos) -> dict | None:
    if not (os.path.exists(CACHE_META) and os.path.exists(CACHE_BIN)):
        return None
    with open(CACHE_META, encoding="utf-8") as fh:
        meta = json.load(fh)
    if meta.get("version") != CACHE_VERSION or meta.get("key") != cache_key(geos):
        print("  cache stale — rebuilding", file=sys.stderr)
        return None
    with open(CACHE_BIN, "rb") as fh:
        meta["buf"] = fh.read()
    print("  cache: reusing existing", file=sys.stderr)
    return meta


def build_cache(geos, fab_ok: bool) -> dict:
    chunks = []
    entries = []
    off = 0
    for i, (corpus, g) in enumerate(geos):
        cols = sample_columns(g, fab_ok)
        ent = {"n5": len(g["d5"]), "n30": len(g["d30"]), "off": off, "has_fab": 0}
        for key, n in (("igc5", ent["n5"]), ("igc30", ent["n30"]),
                       ("fab5", ent["n5"]), ("fab30", ent["n30"])):
            v = cols.get(key)
            if v is None:
                v = [float("nan")] * n
            else:
                ent["has_fab"] = ent["has_fab"] or key.startswith("fab")
            chunks.append(array("d", v).tobytes())
            off += n
        entries.append(ent)
        if (i + 1) % 50 == 0:
            print(f"  …sampled {i + 1}/{len(geos)}", file=sys.stderr)
    buf = b"".join(chunks)
    with open(CACHE_BIN, "wb") as fh:
        fh.write(buf)
    meta = {"version": CACHE_VERSION, "key": cache_key(geos), "entries": entries}
    with open(CACHE_META, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    return {**meta, "buf": buf}


def cache_cols(cache: dict, i: int, g: dict) -> dict:
    e = cache["entries"][i]
    buf = cache["buf"]
    out = {}
    off = e["off"]
    for key, n in (("igc5", e["n5"]), ("igc30", e["n30"]),
                   ("fab5", e["n5"]), ("fab30", e["n30"])):
        a = array("d")
        a.frombytes(buf[off * 8:(off + n) * 8])
        vals = list(a)
        out[key] = None if all(v != v for v in vals) else vals
        off += n
    return out



def arm_components(r: dict, name: str, proto: str) -> dict | None:
    """Rebuild one arm's closed-form components from a CSV row, so F4 can be
    re-evaluated at any noise rate c without a second engine pass (P3b)."""
    try:
        return {"X": r[f"{name}_X"], "beta": r[f"{name}_{proto}_beta"],
                "a_roll": r[f"{name}_{proto}_a_roll"],
                "a_aero": r[f"{name}_{proto}_a_aero"],
                "hplus": r[f"{name}_hplus"], "hminus": r[f"{name}_hminus"],
                "aero_raw": r[f"{name}_{proto}_aero_raw"],
                "hplus_sm": r[f"{name}_hplus_sm"],
                "hminus_sm": r[f"{name}_{proto}_hminus_sm"],
                "aero_sm": r[f"{name}_{proto}_aero_sm"]}
    except KeyError:
        return None


def load_e26() -> dict:
    """Entry-26 portal exposure per ride, for P4b. Keyed (corpus, ride label)."""
    path = os.path.join(RESULTS, "e26_portal_profiles.csv")
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        head = [_unquote(h) for h in fh.readline().rstrip("\n").split(",")]
        for line in fh:
            c = [_unquote(x) for x in line.rstrip("\n").split(",")]
            if len(c) < len(head):
                continue
            r = dict(zip(head, c))
            try:
                out[(r["corpus"], r["ride"])] = {
                    "span_m": float(r["span_m"]),
                    "dh_removed": float(r["dh_plus_removed_igc5"])}
            except (KeyError, ValueError):
                continue
    return out


# ===== reporting =====
def f(x, d: int = 1) -> str:
    return "—" if x is None or not is_finite(x) else to_fixed(x, d)


def cell(vals: list[float], ci: bool = True) -> str:
    av = [abs(x) for x in vals]
    if not ci:
        return f(med_of(av), 1).rjust(18) + f(med_of(vals), 1).rjust(20)
    alo, ahi = boot_ci(av, 42)
    slo, shi = boot_ci(vals, 43)
    return (f"{f(med_of(av), 1)} [{f(alo, 1)},{f(ahi, 1)}]".rjust(18)
            + f"{f(med_of(vals), 1)} [{f(slo, 1)},{f(shi, 1)}]".rjust(20))


def report(rows, funnel, cons_max) -> None:
    print("\n" + "=" * 96)
    print("ENTRY 41 — the elevation-source substitution (paper 1's law on DEM profiles)")
    print("=" * 96)
    print(f"IGC raster: {IGC_WIDE}")
    print(f"frozen: Crr {FROZEN['Crr']} · CdA {FROZEN['CdA']} · ρ {FROZEN['rho']} · "
          f"k_eff {FROZEN['keff']} · wind 0 · G {G} · τ {TAU_SMOOTH} m · "
          f"c {C_FROZEN} m/km · ε_f {EPS_F}")

    print("\nCORPUS FUNNEL (candidates → analysed):")
    for c in CORPORA:
        e = funnel.get(c) or {}
        keep = [r for r in rows if r["corpus"] == c]
        prim = [r for r in keep if r["dataOK"] and r["g1_track"] and r["g2_valid"]]
        print(f"  {CORPUS_LABEL[c]:16s} cand={e.get('candidate', 0):4d} → "
              f"sampled={len(keep):4d} → primary={len(prim):4d}"
              f"   [skips: zwift={e.get('zwift', 0)} no-geo={e.get('no-geo', 0)} "
              f"geo-span={e.get('geo-span', 0)} short={e.get('too-short', 0)} "
              f"outside-raster={e.get('outside-raster', 0)} "
              f"unparseable={e.get('unparseable', 0)} no-igc={e.get('no-igc', 0)}]"
              f"   [gates: floor={sum(1 for r in keep if not r['dataOK'])} "
              f"G1={sum(1 for r in keep if not r['g1_track'])} "
              f"G2={sum(1 for r in keep if not r['g2_valid'])} "
              f"G3-flagged={sum(1 for r in keep if not r['g3_clean'])}]")

    prim = [r for r in rows if r["dataOK"] and r["g1_track"] and r["g2_valid"]]
    print(f"\nPRIMARY POPULATION n={len(prim)} · max conservation residual "
          f"{cons_max:.2e} (must be ≤ 1e-6)")

    # --- geometry per arm ---
    print("\nGEOMETRY — median h₊ (m), noise rate c(τ=2) (m/km), ε_d, anomalies/ride:")
    print("arm".ljust(10) + "h₊".rjust(8) + "h₊/h₊(own)".rjust(12)
          + "c(τ=2)".rjust(10) + "ε_d(reg)".rjust(10) + "anom".rjust(8)
          + "anom h₊".rjust(10))
    own_hp = med_of([r["own_hplus"] for r in prim if r.get("own_ok")])
    for name in ARM_NAMES:
        st = [r for r in prim if r.get(f"{name}_ok")]
        if not st:
            continue
        hp = med_of([r[f"{name}_hplus"] for r in st])
        print(name.ljust(10) + f(hp, 0).rjust(8)
              + f(hp / own_hp, 2).rjust(12)
              + f(med_of([r[f"{name}_cnoise"] for r in st]), 2).rjust(10)
              + f(med_of([r[f"{name}_reg_eps_d"] for r in st]), 3).rjust(8)
              + f(med_of([r[f"{name}_n_anom"] for r in st]), 1).rjust(8)
              + f(med_of([r[f"{name}_anom_hplus"] for r in st]), 1).rjust(10))

    # --- the treatment table ---
    for corpus in list(CORPORA) + ["D3+D4", "ALL"]:
        st = subset(prim, corpus)
        if len(st) < 5:
            continue
        title = CORPUS_LABEL.get(corpus, corpus)
        pool = corpus in ("D3+D4", "ALL")      # the two the letter publishes
        print(f"\n── {title} · n={len(st)} · {PROTO_LABEL[PRIMARY_PROTO]} physics"
              + (" ──" if pool else " (medians only) ──"))
        print("model".ljust(12) + "arm".ljust(10)
              + ("med|Δ%| [95% CI]" if pool else "med|Δ%|").rjust(18)
              + ("bias [95% CI]" if pool else "bias").rjust(20))
        for model, key in (("F3 · ε_d", "f3d"), ("F4 · ε_d", "f4d"),
                           ("F3 · ε_f", "f3f"), ("F4 · ε_f", "f4f"),
                           ("simulation", "canon_d")):
            for name in ARM_NAMES:
                k = f"{name}_{PRIMARY_PROTO}_{key}"
                v = [r[k] for r in st if r.get(f"{name}_ok") and is_finite(r.get(k))]
                if not v:
                    continue
                # CI only the three models the letter publishes; the ε_f rows are
                # context and print as medians (each CI is ~10 s at n ≈ 1,100).
                print(model.ljust(12) + name.ljust(10)
                      + cell(v, ci=pool and key in ("f3d", "f4d", "canon_d")))
            print()

    # --- paired own-vs-DEM ---
    print("\nPAIRED — per-ride Δ%(arm) − Δ%(own), F3 · ε_d (positive = the DEM over-charges):")
    print("corpus".ljust(16) + "".join(n.rjust(12) for n in DEM_ARMS))
    for corpus in list(CORPORA) + ["D3+D4", "ALL"]:
        st = subset(prim, corpus)
        if len(st) < 5:
            continue
        line = CORPUS_LABEL.get(corpus, corpus).ljust(16)
        for name in DEM_ARMS:
            k, k0 = f"{name}_{PRIMARY_PROTO}_f3d", f"own_{PRIMARY_PROTO}_f3d"
            d = [r[k] - r[k0] for r in st
                 if r.get(f"{name}_ok") and r.get("own_ok") and is_finite(r.get(k))]
            line += (f(med_of(d), 1) + " pp").rjust(12)
        print(line)

    # --- the physics-protocol contrast (the (α, ε) bundle rule, per source) ---
    print("\nPROTOCOL CONTRAST — F3 · ε_d med|Δ%| (bias) under each physics protocol:")
    print("arm".ljust(10) + "".join(f"{PROTO_LABEL[q]:>34s}" for q in PROTOCOLS))
    for name in ARM_NAMES:
        line = name.ljust(10)
        for q in PROTOCOLS:
            k = f"{name}_{q}_f3d"
            v = [r[k] for r in prim if r.get(f"{name}_ok") and is_finite(r.get(k))]
            line += (f"{f(med_of([abs(x) for x in v]), 1)} "
                     f"({f(med_of(v), 1)})").rjust(34) if v else "—".rjust(34)
        print(line)

    # --- P3: the per-source noise rate ---
    print("\nP3 — the per-source ascent-noise rate c(τ=2), median [95% CI] m/km:")
    for name in ARM_NAMES:
        v = [r[f"{name}_cnoise"] for r in prim
             if r.get(f"{name}_ok") and is_finite(r.get(f"{name}_cnoise"))]
        if not v:
            continue
        lo, hi = boot_ci(v, 42)
        print(f"  {name.ljust(10)} {f(med_of(v), 2).rjust(7)} "
              f"[{f(lo, 2)}, {f(hi, 2)}]   (frozen c = {C_FROZEN})")

    # --- P3b: F4 re-evaluated at each source's OWN noise rate ---
    print("\nP3b — F4 · ε_d at the frozen c = 3 m/km vs at the arm's own median c "
          f"({PROTO_LABEL[PRIMARY_PROTO]} physics):")
    print("arm".ljust(10) + "c used".rjust(9)
          + "frozen c: med|Δ%| (bias)".rjust(28) + "own c: med|Δ%| (bias)".rjust(26))
    for name in ARM_NAMES:
        st = [r for r in prim if r.get(f"{name}_ok")]
        cs = [r[f"{name}_cnoise"] for r in st if is_finite(r.get(f"{name}_cnoise"))]
        if not cs:
            continue
        c_arm = med_of(cs)
        a_frz, a_own = [], []
        for r in st:
            a = arm_components(r, name, PRIMARY_PROTO)
            eps = r.get(f"{name}_{PRIMARY_PROTO}_eps_d")
            if a is None or not is_finite(eps) or not is_finite(r["emp"]):
                continue
            a_frz.append(jsdiv(forms(a, eps, C_FROZEN)["f4"] - r["emp"], r["emp"]) * 100)
            a_own.append(jsdiv(forms(a, eps, c_arm)["f4"] - r["emp"], r["emp"]) * 100)
        if not a_frz:
            continue
        print(name.ljust(10) + f(c_arm, 2).rjust(9)
              + (f"{f(med_of([abs(x) for x in a_frz]), 1)} "
                 f"({f(med_of(a_frz), 1)})").rjust(28)
              + (f"{f(med_of([abs(x) for x in a_own]), 1)} "
                 f"({f(med_of(a_own), 1)})").rjust(26))

    # --- P4b: portal exposure (Entry 26 join) ---
    e26 = load_e26()
    if e26:
        exposed = []
        for r in prim:
            q = e26.get((r["corpus"], r["ride"]))
            k = f"igc5_{PRIMARY_PROTO}_f3d"
            k0 = f"own_{PRIMARY_PROTO}_f3d"
            if q is None or not (is_finite(r.get(k)) and is_finite(r.get(k0))):
                continue
            exposed.append((q["span_m"] / max(0.001, r["km"]), r[k] - r[k0]))
        if len(exposed) >= 20:
            exposed.sort()
            cut = exposed[int(0.9 * (len(exposed) - 1))][0]
            top = [d for e_, d in exposed if e_ >= cut]
            rest = [d for e_, d in exposed if e_ < cut]
            print(f"\nP4b — portal exposure (E26 join, n={len(exposed)} of {len(prim)}): "
                  f"top-decile cut {f(cut, 1)} span-m per route-km")
            print(f"  DEM-minus-own residual (igc5, F3·ε_d): top decile "
                  f"{f(med_of(top), 2)} pp (n={len(top)}) vs rest {f(med_of(rest), 2)} pp "
                  f"(n={len(rest)}) · difference {f(med_of(top) - med_of(rest), 2)} pp")
        else:
            print(f"\nP4b — portal exposure: only {len(exposed)} rides join E26 "
                  f"(its population is the old validated crop) — under-powered, reported as such")
    else:
        print("\nP4b — e26_portal_profiles.csv absent; portal secondary not evaluated")

    # --- G3 secondary ---
    clean = [r for r in prim if r["g3_clean"]]
    print(f"\nG3 SECONDARY — anomaly-free crops only (n={len(clean)} of {len(prim)}), "
          f"F3 · ε_d:")
    print("arm".ljust(10) + "med|Δ%| [95% CI]".rjust(18) + "bias [95% CI]".rjust(20))
    for name in ARM_NAMES:
        k = f"{name}_{PRIMARY_PROTO}_f3d"
        v = [r[k] for r in clean if r.get(f"{name}_ok") and is_finite(r.get(k))]
        if v:
            print(name.ljust(10) + cell(v))


# ===== gates =====
def parse_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read().strip()
    lines = text.split("\n")

    def split(line: str) -> list[str]:
        out, cur, q = [], "", False
        for ch in line:
            if ch == '"':
                q = not q
            elif ch == "," and not q:
                out.append(cur)
                cur = ""
            else:
                cur += ch
        out.append(cur)
        return out

    head = split(lines[0])
    return [dict(zip(head, split(l))) for l in lines[1:] if l.strip()]


def _num(s) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return float("nan")


# published per-ride Δ% columns → this harness's own-arm columns.
# longões: Entry 31's frozen re-run; the others: the *_compare harnesses.
PARITY_REF = {
    "longoes": ("longoes_frozen.csv", "ride",
                {"own_frz_f3d": "f3_d", "own_frz_f4d": "f4_d",
                 "own_frz_f3f": "f3_f", "own_frz_f4f": "f4_f",
                 "own_frz_canon_d": "canon_d"}),
    "censo": ("censo_comparison.csv", "ride",
              {"own_f3d": "sm_geom", "own_f4d": "pm_geom", "own_f3f": "sm_0.20",
               "own_f4f": "pm_0.20", "own_canon_d": "canon_d"}),
    "ppaz": ("ppaz_comparison.csv", "ride",
             {"own_frz_f3d": "sm_geom", "own_frz_f4d": "pm_geom",
              "own_frz_f3f": "sm_0.20", "own_frz_f4f": "pm_0.20",
              "own_frz_canon_d": "canon_d"}),
    "jaam": ("jaam_comparison.csv", "ride",
             {"own_frz_f3d": "sm_geom", "own_frz_f4d": "pm_geom",
              "own_frz_f3f": "sm_0.20", "own_frz_f4f": "pm_0.20",
              "own_frz_canon_d": "canon_d"}),
    "danlessa": ("danlessa_comparison.csv", "ride",
                 {"own_frz_f3d": "sm_geom", "own_frz_f4d": "pm_geom",
                  "own_frz_f3f": "sm_0.20", "own_frz_f4f": "pm_0.20",
                  "own_frz_canon_d": "canon_d"}),
}
PARITY_TOL = 0.02       # pp — the reference CSVs print 3–4 decimals


def gate_parity(rows) -> tuple[bool, str]:
    """The control arm IS paper 1's protocol, so it must reproduce the published
    per-ride Δ% ride by ride — a far stricter check than a median comparison."""
    worst, worst_what, n = 0.0, "", 0
    missing = 0
    for corpus, (fname, key, cmap) in PARITY_REF.items():
        path = os.path.join(RESULTS, fname)
        if not os.path.exists(path):
            return False, f"{fname} absent — run its harness first"
        ref = {r[key]: r for r in parse_csv(path)}
        for r in rows:
            if r["corpus"] != corpus or not r.get("own_ok"):
                continue
            q = ref.get(r["ride"])
            if q is None:
                missing += 1
                continue
            for mine, theirs in cmap.items():
                a, b = r.get(mine), _num(q.get(theirs))
                if not (is_finite(a) and is_finite(b)):
                    continue
                n += 1
                if abs(a - b) > worst:
                    worst, worst_what = abs(a - b), f"{corpus}/{r['ride']} {mine}"
    ok = n > 0 and worst <= PARITY_TOL
    return ok, (f"{n} per-ride comparisons, worst |Δ| {worst:.4f} pp ({worst_what}); "
                f"{missing} rides absent from the reference CSVs")


def gate_sigma_equivalence(rows, geos) -> tuple[bool, str]:
    """The letter prescribes 1-D profile smoothing; Entry 20 validated 2-D RASTER
    smoothing.  On the rides Entry 20 cached, the two must agree — otherwise the
    letter cannot inherit Entry 20's σ prescription."""
    meta_path = os.path.join(SCRATCH, "goal_profiles.meta.json")
    bin_path = os.path.join(SCRATCH, "goal_profiles.bin")
    if not (os.path.exists(meta_path) and os.path.exists(bin_path)):
        return True, "Entry-20 cache absent — gate skipped (disclosed)"
    meta = json.load(open(meta_path))
    if 10 not in meta["sigmas"]:
        return True, "Entry-20 cache lacks σ=10 — gate skipped"
    si = meta["sigmas"].index(10)
    buf = open(bin_path, "rb").read()
    ref = {(r["corpus"], r["ride"]): r for r in meta["rides"]}
    by_ride = {(c, g["label"]): g for c, g in geos}
    diffs = []
    for r in rows:
        q = ref.get((r["corpus"], r["ride"]))
        g = by_ride.get((r["corpus"], r["ride"]))
        if q is None or g is None or not r.get("igc5s10_ok"):
            continue
        n = q["n"]
        if n != len(g["d5"]):
            continue
        a = array("d")
        a.frombytes(buf[(q["off"] + si * n) * 8:(q["off"] + si * n + n) * 8])
        hp_raster = sum_ascent(a)
        if hp_raster <= 0:
            continue
        diffs.append((r["igc5s10_hplus"] - hp_raster) / hp_raster * 100)
    if not diffs:
        return True, "no overlap with the Entry-20 cache — gate skipped"
    m = med_of(diffs)
    p90 = sorted(abs(x) for x in diffs)[int(0.9 * (len(diffs) - 1))]
    ok = abs(m) < 10 and p90 < 25
    return ok, (f"n={len(diffs)} · median h₊ Δ(1-D σ10 − 2-D σ10) {m:+.2f}% · "
                f"p90 |Δ| {p90:.2f}%")


def gate_primitives() -> tuple[bool, str]:
    """Synthetic self-check of the two pieces of new profile machinery. Neither is
    covered by the ride-level gates: the route-length gate would pass even if the
    re-gridding smeared the geometry, and nothing else touches the 1-D Gaussian."""
    total = 3000.0
    d30, d5 = grid_positions(total, 30), grid_positions(total, ENGINE_DX)
    h30 = [100 + 20 * math.sin(i / 3.0) + (i % 7) for i in range(len(d30))]
    h5 = regrid(d30, h30, d5)
    d_hp = abs(sum_ascent(h30) - sum_ascent(h5))          # h₊ preserved exactly
    d_node = max(abs(h5[d5.index(x)] - h30[k])            # nodes preserved exactly
                 for k, x in enumerate(d30) if x in d5)

    def turns(h):
        sg = [1 if h[i] > h[i - 1] else (-1 if h[i] < h[i - 1] else 0)
              for i in range(1, len(h))]
        sg = [x for x in sg if x]
        return sum(1 for i in range(1, len(sg)) if sg[i] != sg[i - 1])

    d_turn = turns(h5) - turns(h30)                       # no new local extrema
    d_const = max(abs(x - 7.0) for x in gauss1d([7.0] * 200, 30.0, ENGINE_DX))
    ramp = [float(i) for i in range(200)]
    gr = gauss1d(ramp, 30.0, ENGINE_DX)
    d_ramp = max(abs(gr[i] - ramp[i]) for i in range(30, 170))
    ok = (d_hp == 0.0 and d_node == 0.0 and d_turn == 0
          and d_const < 1e-12 and d_ramp < 1e-9)
    return ok, (f"Δh₊ {d_hp:.1e} · Δnode {d_node:.1e} · Δturns {d_turn} · "
                f"Gauss(const) {d_const:.1e} · Gauss(ramp) {d_ramp:.1e}")


def run_gates(rows, geos, cons_max: float) -> bool:
    print("\n" + "=" * 96)
    print("SANITY GATES")
    ok = [True]

    def say(name: str, passed: bool, extra: str = "") -> None:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f"  — {extra}" if extra else ""))
        if not passed:
            ok[0] = False

    say("conservation identity on every arm's simulation (≤ 1e-6)", cons_max <= 1e-6,
        f"max relative residual {cons_max:.2e}")
    r_ok, r_msg = gate_primitives()
    say("re-gridding preserves h± exactly; the Gaussian is mask-normalized", r_ok, r_msg)
    p_ok, p_msg = gate_parity(rows)
    say("PARITY: the own arm reproduces paper 1's published per-ride Δ%", p_ok, p_msg)
    s_ok, s_msg = gate_sigma_equivalence(rows, geos)
    say("σ-equivalence: 1-D profile smoothing ≈ Entry-20's 2-D raster smoothing",
        s_ok, s_msg)
    # every arm is scored on the same x-grid — a re-gridding bug would show as a
    # route-length disagreement
    worst_x = 0.0
    for r in rows:
        for name in ARM_NAMES:
            if r.get(f"{name}_ok") and is_finite(r.get(f"{name}_X")):
                worst_x = max(worst_x, abs(r[f"{name}_X"] - r["own_X"]))
    say("all arms share the ride's route length (re-gridding is inert)", worst_x < 1e-6,
        f"max |ΔX| {worst_x:.2e} m")
    print("\nGATES: ALL PASS" if ok[0] else "\nGATES: FAILURES ABOVE")
    return ok[0]


def subset(rows, corpus: str) -> list[dict]:
    if corpus == "ALL":
        return rows
    if corpus == "D3+D4":
        return [r for r in rows if r["corpus"] in ("ppaz", "jaam")]
    return [r for r in rows if r["corpus"] == corpus]


def write_csv(rows) -> None:
    if not rows:
        print("no rows")
        return
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    name = "e41_dem_route_smoke.csv" if SMOKE else "e41_dem_route.csv"
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(
                (f'"{r[k]}"' if isinstance(r[k], str)
                 else ("" if k not in r or not is_finite(r[k]) else to_fixed(r[k], 4)))
                if k in r else "" for k in cols) + "\n")
    print(f"\nwrote {name} ({len(rows)} rides)")


if __name__ == "__main__":
    main()
