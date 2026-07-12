#!/usr/bin/env python3
"""TEST of the closed-form ε hypothesis (notas / chat) — Python port of the
retired eps_hypothesis.mjs (same stdout, byte-identical CSV).

  ε(s) = min(1, α/(β·s)),  α/β = Crr + ½ρCdA(v_f+w)²/(mg)          [coasting recovery]
  ε ≈ clamp[0,1]( ε_coast − c_κ·κ − c_u·f_unpaved )                [+ braking penalties]

Target = the per-ride descent-energy-balance ε (epsFromBalance, ported from the
app's epsFromFIT) — the same "truth" the harness already reports (median ≈ 0.27).

For each ride we compute, on the SAME 30 m descent cells the balance ε uses:
  ε_coast  drop-weighted Σ hᵢ·min(1, α/β·sᵢ) / H₋   (per-cell clamp; α at measured v_f)
  ε_lump   min(1, α/(β·s̄)),  s̄ = H₋/X₋               (cheap, totals only)
plus two ride "details": κ = curviness (rad/km, from GPS) and f_unpaved (sheet col I).
Then we check how well ε_coast predicts ε_bal, and whether κ / f_unpaved earn their keep.

Unlike compare.py, this harness writes RAW full-precision floats to its CSV
(JS String(number)), and κ/haversine flow through Math.sin/cos/asin/atan2 —
whose V8 builds (fdlibm + arm64 clang FMA contraction) differ from the platform
libm in the last ulp. The _js* block below is a bit-exact transliteration of
V8 12.9 src/base/ieee754.cc (node 23), verified bit-identical against node on
hundreds of thousands of samples across the relevant input ranges.

Reads data/activities/model_inputs.json + eps_features.json (+ the gitignored
tracks); writes results/eps_hypothesis.csv. Run: python3 harness/eps_hypothesis.py
"""

import json
import math
import os
import re
import struct
import sys
from datetime import datetime
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))

from bem import finish_pts, parse_fit
from bem.jsfmt import to_fixed
from bem.v8math import _js_asin, _js_atan2, _js_cos, _js_sin, js_num

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
os.makedirs(RESULTS, exist_ok=True)
G = 9.81


# ---------------------------------------------------------------------------
# shared pipeline pieces the .mjs embeds with bodies that differ from
# analysis/parity/reference.mjs (so they are ported here, not imported):
# haversine (same arithmetic, but must run on the V8 math above), ptsFromFIT
# (takes parsed records, not a buffer — the driver reuses the records for the
# curviness GPS pass), and parseGPX/ptsFromGeo (reference.mjs merges them into
# ptsFromGPX; this harness needs the raw geo list for curviness).
# ---------------------------------------------------------------------------

def haversine(a, b):
    R = 6371000
    t = math.pi / 180
    s1 = _js_sin((b["lat"] - a["lat"]) * t / 2)
    s2 = _js_sin((b["lon"] - a["lon"]) * t / 2)
    s = s1 * s1 + _js_cos(a["lat"] * t) * _js_cos(b["lat"] * t) * (s2 * s2)
    return 2 * R * _js_asin(min(1, math.sqrt(s)))


def pts_from_fit_recs(recs):
    """pts (energy) from parsed FIT records — interleaved dist/alt handling,
    as compare.mjs (the .mjs ptsFromFIT takes records, unlike bem's)."""
    if len(recs) < 2:
        raise ValueError("FIT sem registros")
    pts = []
    if any(r.get("dist") is not None for r in recs):
        di, dv = [], []
        for i, r in enumerate(recs):  # clip non-monotone device distance
            if r.get("dist") is not None:
                di.append(i)
                dv.append(max(r["dist"], dv[-1]) if dv else r["dist"])
        last_alt = None
        k = 0
        for i in range(len(recs)):
            if recs[i].get("alt") is not None:
                last_alt = recs[i]["alt"]
            if last_alt is None:
                continue
            while k < len(di) - 1 and di[k + 1] <= i:
                k += 1
            if i <= di[0]:
                x = dv[0]
            elif i >= di[-1]:
                x = dv[-1]
            else:
                f = (i - di[k]) / (di[k + 1] - di[k])
                x = dv[k] + (dv[k + 1] - dv[k]) * f
            pts.append({"x": x, "alt": last_alt, "power": recs[i].get("power"),
                        "t": recs[i].get("time"), "v": recs[i].get("speed")})
    else:
        geo = [r for r in recs
               if r.get("lat") is not None and r.get("lon") is not None
               and r.get("alt") is not None]
        if len(geo) < 2:
            raise ValueError("FIT sem distância nem GPS")
        cum = 0.0
        pts.append({"x": 0, "alt": geo[0]["alt"], "power": geo[0].get("power"),
                    "t": geo[0].get("time"), "v": geo[0].get("speed")})
        for i in range(1, len(geo)):
            cum += haversine(geo[i - 1], geo[i])
            pts.append({"x": cum, "alt": geo[i]["alt"], "power": geo[i].get("power"),
                        "t": geo[i].get("time"), "v": geo[i].get("speed")})
    finish_pts(pts)
    return pts


_TRKPT = re.compile(r'<trkpt\b([^>]*)>([\s\S]*?)</trkpt>')
_LAT = re.compile(r'lat="([-\d.]+)"')
_LON = re.compile(r'lon="([-\d.]+)"')
_ELE = re.compile(r'<ele>\s*([-\d.]+)')
_TIME = re.compile(r'<time>\s*([^<]+)')
_POWER = re.compile(r'<(?:\w+:)?power>\s*([\d.]+)')


def _date_parse(s):
    """Date.parse(s)/1000 for the ISO-8601 stamps GPX carries (NaN when
    unparseable, as JS)."""
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float("nan")


def parse_gpx(text):
    out = []
    for m in _TRKPT.finditer(text):
        la = _LAT.search(m.group(1))
        lo = _LON.search(m.group(1))
        if not la or not lo:
            continue
        ele = _ELE.search(m.group(2))
        tm = _TIME.search(m.group(2))
        pw = _POWER.search(m.group(2))
        out.append({"lat": float(la.group(1)), "lon": float(lo.group(1)),
                    "alt": float(ele.group(1)) if ele else float("nan"),
                    "t": _date_parse(tm.group(1)) if tm else None,
                    "power": float(pw.group(1)) if pw else None})
    if len(out) < 2:
        raise ValueError("GPX poucos pontos")
    return out


def pts_from_geo(geo):
    cum = 0.0
    pts = [{"x": 0, "alt": geo[0]["alt"], "power": geo[0].get("power"),
            "t": geo[0].get("t")}]
    for i in range(1, len(geo)):
        cum += haversine(geo[i - 1], geo[i])
        pts.append({"x": cum, "alt": geo[i]["alt"], "power": geo[i].get("power"),
                    "t": geo[i].get("t")})
    finish_pts(pts)
    return pts


# ---- curviness κ: total |heading change| per km on a ~RES-m resampled GPS track ----
# Resample to constant spacing first so GPS jitter / dense slow points don't inflate it.

def _is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def curviness(geo, RES=50):
    ll = [r for r in geo
          if r.get("lat") is not None and r.get("lon") is not None
          and _is_finite(r["lat"]) and _is_finite(r["lon"])]
    if len(ll) < 3:
        return None
    # cumulative distance
    d = [0]
    for i in range(1, len(ll)):
        d.append(d[i - 1] + haversine(ll[i - 1], ll[i]))
    total = d[-1]
    if total < 5 * RES:
        return None
    # resample lat/lon at RES spacing
    pts = []
    j = 0
    s = 0
    while s <= total:
        while j < len(ll) - 2 and d[j + 1] < s:
            j += 1
        seg = d[j + 1] - d[j]
        f = (s - d[j]) / seg if seg > 1e-9 else 0
        pts.append({"lat": ll[j]["lat"] + (ll[j + 1]["lat"] - ll[j]["lat"]) * f,
                    "lon": ll[j]["lon"] + (ll[j + 1]["lon"] - ll[j]["lon"]) * f})
        s += RES
    if len(pts) < 3:
        return None
    # local east-north metres (small-angle), heading per segment, sum |Δheading|
    lat0 = pts[0]["lat"] * math.pi / 180
    m_per_lon = 111320 * _js_cos(lat0)
    m_per_lat = 110540
    head = []
    for i in range(1, len(pts)):
        dx = (pts[i]["lon"] - pts[i - 1]["lon"]) * m_per_lon
        dy = (pts[i]["lat"] - pts[i - 1]["lat"]) * m_per_lat
        head.append(_js_atan2(dy, dx))
    turn = 0.0
    for i in range(1, len(head)):
        dth = head[i] - head[i - 1]
        while dth > math.pi:
            dth -= 2 * math.pi
        while dth < -math.pi:
            dth += 2 * math.pi
        turn += abs(dth)
    return turn / (total / 1000)  # rad per km


# ---- ε analysis: balance (truth) + coasting prediction, sharing 30 m cells, α, v_f ----

def eps_analysis(pts, p):
    if not pts or len(pts) < 2:
        return None
    mg = p["m"] * G
    beta = mg / p["keff"]
    x0 = pts[0]["x"]
    total_m = pts[-1]["x"] - x0
    DX = 30
    nc = math.floor(total_m / DX)
    if nc < 2:
        return None
    j = 0

    def alt_at(dd):
        nonlocal j
        while j < len(pts) - 2 and pts[j + 1]["x"] < dd:
            j += 1
        seg = pts[j + 1]["x"] - pts[j]["x"]
        f = (dd - pts[j]["x"]) / seg if seg > 1e-9 else 0
        return pts[j]["alt"] * (1 - f) + pts[j + 1]["alt"] * f

    cell_alt = [0.0] * (nc + 1)
    for k in range(nc + 1):
        cell_alt[k] = alt_at(x0 + k * DX)
    cell_e = [0.0] * nc
    cell_vs = [0.0] * nc
    cell_vt = [0.0] * nc
    VSTOP = 0.5 / 3.6  # stopped samples deflate v_f (hence α and ε) — gate them, as extractRegimePowers does
    for r in pts:
        k = math.floor((r["x"] - x0) / DX)
        if k < 0 or k >= nc:
            continue
        w = r.get("dt") or 1
        if r.get("power") is not None:
            cell_e[k] += r["power"] * w
        if r.get("v") is not None and r["v"] >= VSTOP:
            cell_vs[k] += r["v"] * w
            cell_vt[k] += w
    sv = 0
    sw = 0  # measured MOVING flat speed
    for k in range(nc):
        gr = (cell_alt[k + 1] - cell_alt[k]) / DX
        if abs(gr) < 0.01 and cell_vt[k] > 0:
            sv += cell_vs[k]
            sw += cell_vt[k]
    vf = sv / sw if sw > 0 else 5
    aero_spd = vf + p["wind"]
    alpha = (p["Crr"] * mg + 0.5 * p["rho"] * p["CdA"] * aero_spd * abs(aero_spd)) / p["keff"]
    Xd = 0
    Hd = 0
    Ed = 0
    epsW = 0  # descent totals + drop-weighted coasting ε
    for k in range(nc):
        dh = cell_alt[k + 1] - cell_alt[k]
        if dh < 0:
            drop = -dh
            s = drop / DX
            Xd += DX
            Hd += drop
            Ed += cell_e[k]
            epsW += drop * min(1, alpha / (beta * s))
    if Hd < 1:
        return None
    eps_bal = (alpha * Xd - Ed) / (beta * Hd)  # TRUTH (measured descent legs)
    eps_coast = epsW / Hd                      # per-cell clamped coasting prediction
    sbar = Hd / Xd                             # aggregate descent grade
    eps_lump = min(1, alpha / (beta * sbar))   # cheap lumped prediction
    return {"epsBal": eps_bal, "epsCoast": eps_coast, "epsLump": eps_lump,
            "sbar": sbar, "alpha": alpha, "beta": beta, "vf": vf, "Hd": Hd, "Xd": Xd}


# ---- tiny OLS (normal equations + Gaussian elimination) ----

def _div(a, b):
    """JS division semantics for the 0-denominator edge (NaN / ±Infinity)."""
    if b == 0:
        if a != a or a == 0:
            return float("nan")
        neg = (a < 0) != (math.copysign(1.0, b) < 0)
        return -math.inf if neg else math.inf
    return a / b


def ols(y, X):
    """X: rows of features (incl. intercept col if wanted); returns b, r2, pred."""
    n = len(y)
    k = len(X[0])
    A = [[0.0] * k for _ in range(k)]
    g = [0.0] * k
    for i in range(n):
        for a in range(k):
            g[a] += X[i][a] * y[i]
            for b in range(k):
                A[a][b] += X[i][a] * X[i][b]
    # solve A b = g
    M = [list(A[i]) + [g[i]] for i in range(k)]
    for c in range(k):
        piv = c
        for r in range(c + 1, k):
            if abs(M[r][c]) > abs(M[piv][c]):
                piv = r
        M[c], M[piv] = M[piv], M[c]
        d = M[c][c]
        if d == 0 or d != d:  # JS `M[c][c] || 1e-12`
            d = 1e-12
        for cc in range(c, k + 1):
            M[c][cc] /= d
        for r in range(k):
            if r != c:
                fa = M[r][c]
                for cc in range(c, k + 1):
                    M[r][cc] -= fa * M[c][cc]
    b = [row[k] for row in M]
    ybar = 0.0
    for v in y:
        ybar += v
    ybar = _div(ybar, n)
    ssr = 0.0
    sst = 0.0
    pred = []
    for i in range(n):
        yh = 0.0
        for a in range(k):
            yh += X[i][a] * b[a]
        pred.append(yh)
        dy = y[i] - yh
        ssr += dy * dy
        db = y[i] - ybar
        sst += db * db
    return {"b": b, "r2": 1 - _div(ssr, sst), "rms": math.sqrt(_div(ssr, n)), "pred": pred}


def corr(a, b):
    n = len(a)
    ma = 0.0
    for v in a:
        ma += v
    ma = _div(ma, n)
    mb = 0.0
    for v in b:
        mb += v
    mb = _div(mb, n)
    sab = saa = sbb = 0.0
    for i in range(n):
        da = a[i] - ma
        db = b[i] - mb
        sab += da * db
        saa += da * da
        sbb += db * db
    return _div(sab, math.sqrt(saa * sbb))


def med(xs):
    s = sorted(xs)
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


# ---- driver ----

inputs = json.load(open(os.path.join(DATA, "model_inputs.json")))
feats = json.load(open(os.path.join(DATA, "eps_features.json")))
rows = []
for e in inputs:
    if not e.get("file") or not e.get("has_power"):
        continue
    try:
        fp = os.path.join(DATA, e["file"])
        if e["file"].endswith(".gpx"):
            geo = parse_gpx(open(fp, encoding="utf-8").read())
            pts = pts_from_geo(geo)
        else:
            recs = parse_fit(open(fp, "rb").read())
            pts = pts_from_fit_recs(recs)
            geo = [r for r in recs if r.get("lat") is not None and r.get("lon") is not None]
        p = {"m": e["m"], "Crr": e["crr"], "CdA": e["cda"], "rho": e["rho"],
             "keff": e["keff"], "wind": (e.get("wind_kmh") or 0) / 3.6}
        a = eps_analysis(pts, p)
        if not a:
            continue
        kappa = curviness(geo)
        f = feats.get(e["id"]) or {}
        rows.append({"ride": e["label"], "epsBal": a["epsBal"], "epsCoast": a["epsCoast"],
                     "epsLump": a["epsLump"], "sbar": a["sbar"], "kappa": kappa,
                     "unpaved": f.get("unpaved"), "sheet": e.get("eps"),
                     "vf": a["vf"] * 3.6, "ab": a["alpha"] / a["beta"],
                     "bHd": a["beta"] * a["Hd"], "Hd": a["Hd"]})
    except Exception:
        pass  # skip

# keep rides with a finite balance ε (the target)
good = [r for r in rows if _is_finite(r["epsBal"])]


def f2(x, d=2):
    if x is None or not _is_finite(x):
        return "—"
    return to_fixed(x, d)


print(f"ε CLOSED-FORM HYPOTHESIS TEST   (n={len(good)} rides with descents+power)")
print("target = descent-energy-balance ε (epsFromBalance). predictor = min(1, α/β·s), drop-weighted.\n")
print("ride".ljust(24) + "ε_bal".rjust(7) + "ε_coast".rjust(8) + "ε_lump".rjust(7)
      + "s̄%".rjust(6) + "κ r/km".rjust(8) + "unpav".rjust(7))
print("-" * 67)
for r in good:
    print(r["ride"][:23].ljust(24) + f2(r["epsBal"]).rjust(7) + f2(r["epsCoast"]).rjust(8)
          + f2(r["epsLump"]).rjust(7) + f2(r["sbar"] * 100, 1).rjust(6)
          + f2(r["kappa"], 0).rjust(8) + f2(r["unpaved"]).rjust(7))

print("\n" + "=" * 67)
print("HOW WELL DOES THE COASTING CORE PREDICT ε_bal?")
yb = [r["epsBal"] for r in good]
for lab, key in [("ε_coast (per-cell clamp)", "epsCoast"), ("ε_lump (totals only)", "epsLump")]:
    x = [r[key] for r in good]
    resid = [good[i]["epsBal"] - x[i] for i in range(len(good))]
    sq = 0.0
    for v in resid:
        sq += v * v
    rms_raw = math.sqrt(_div(sq, len(resid)))
    print(f"  {lab.ljust(26)} corr={f2(corr(x, yb))}  med(pred)={f2(med(x))}"
          f"  med(ε_bal)={f2(med(yb))}  RMS(ε_bal−pred)={f2(rms_raw)}  medBias={f2(med(resid))}")

# where does it matter? weight each ride by its descent energy β·H₋ (J), and look at
# the real-descent subset — the flat rides that break the clamp carry ~no energy.


def w_corr(a, b, w):
    W = 0.0
    for v in w:
        W += v
    ma = 0.0
    for i, v in enumerate(a):
        ma += w[i] * v
    ma = _div(ma, W)
    mb = 0.0
    for i, v in enumerate(b):
        mb += w[i] * v
    mb = _div(mb, W)
    sab = saa = sbb = 0.0
    for i in range(len(a)):
        da = a[i] - ma
        db = b[i] - mb
        sab += w[i] * da * db
        saa += w[i] * (da * da)
        sbb += w[i] * (db * db)
    return _div(sab, math.sqrt(saa * sbb))


print("\n" + "=" * 67)
print("WHERE IT MATTERS — weight by descent energy β·H₋, and the real-descent subset")
W = [r["bHd"] for r in good]
_num = 0.0
for r in good:
    _num += r["bHd"] * (r["epsBal"] - r["epsCoast"])
_den = 0.0
for v in W:
    _den += v
w_bias = _div(_num, _den)
print(f"  energy-weighted: corr(ε_coast,ε_bal)="
      f"{f2(w_corr([r['epsCoast'] for r in good], [r['epsBal'] for r in good], W))}"
      f"  weighted bias(ε_bal−ε_coast)={f2(w_bias)}")
for thr in [0.025, 0.03, 0.035]:
    sub = [r for r in good if r["sbar"] >= thr]
    x = [r["epsCoast"] for r in sub]
    y = [r["epsBal"] for r in sub]
    resid = [r["epsBal"] - r["epsCoast"] for r in sub]
    print(f"  s̄ ≥ {to_fixed(thr * 100, 1)}%  (n={len(sub)}): corr={f2(corr(x, y))}"
          f"  medBias={f2(med(resid))}  med(ε_bal)={f2(med(y))} med(ε_coast)={f2(med(x))}")

# ---- estimator SKILL (error reduction) + part-whole disclosure ----
# The correlation headline is part-whole: ε_bal ≡ α/(β·s̄) − E_legs,₋/(β·H₋) EXACTLY,
# and ε_coast ≈ that same first term (drop-weighted, clamped) with the same per-ride α.
# So judge the closed form by RMS skill vs the best flat constant, not by corr alone.
print("\n" + "=" * 67)
print("ESTIMATOR SKILL — RMS(ε_bal − pred), skill = 1 − RMS/RMS_flat (flat = subset median ε_bal)")


def clamp01(v):
    return max(0, min(1, v))


def rms(xs):
    s = 0.0
    for v in xs:
        s += v * v
    return math.sqrt(_div(s, len(xs)))


for slab, sub in [("all rides", good), ("s̄ ≥ 3%", [r for r in good if r["sbar"] >= 0.03])]:
    base = med([r["epsBal"] for r in sub])
    rms_base = rms([r["epsBal"] - base for r in sub])
    print(f"  -- {slab} (n={len(sub)}, flat const = {f2(base)}, RMS_flat = {f2(rms_base)}) --")
    for lab, fx in [
        ("sheet g_d_eff", lambda r: r["sheet"]),
        ("ε_coast − 0.13 (clamped)", lambda r: clamp01(r["epsCoast"] - 0.13)),
        ("ε_lump − 0.13 (clamped, totals)", lambda r: clamp01(r["epsLump"] - 0.13)),
    ]:
        s2 = [r for r in sub if _is_finite(fx(r))]
        err = rms([r["epsBal"] - fx(r) for r in s2])
        print(f"  {lab.ljust(32)} RMS={f2(err)}  skill vs flat={f2(1 - _div(err, rms_base))}  (n={len(s2)})")
    shared = [r["ab"] / r["sbar"] for r in sub]  # the UNclamped shared geometry term α/(β·s̄)
    print(f"  part–whole: corr(α/(β·s̄), ε_bal)={f2(corr(shared, [r['epsBal'] for r in sub]))}"
          f"  corr(α/(β·s̄), ε_coast)={f2(corr(shared, [r['epsCoast'] for r in sub]))}")

# add the braking penalties: ε_bal ~ ε_coast + κ + unpaved  (need κ & unpaved present)
fit = [r for r in good if _is_finite(r["kappa"]) and _is_finite(r["unpaved"])]
print("\n" + "=" * 67)
print(f"BRAKING PENALTIES — OLS on the {len(fit)} rides with GPS+unpaved")
y = [r["epsBal"] for r in fit]
models = [
    ("ε_coast only", lambda r: [1, r["epsCoast"]]),
    ("ε_coast + κ", lambda r: [1, r["epsCoast"], r["kappa"]]),
    ("ε_coast + unpaved", lambda r: [1, r["epsCoast"], r["unpaved"]]),
    ("ε_coast + κ + unpaved", lambda r: [1, r["epsCoast"], r["kappa"], r["unpaved"]]),
]
for lab, fx in models:
    X = [fx(r) for r in fit]
    o = ols(y, X)
    terms = " ".join(
        f"{['b0', 'εc', 'κ' if (i == 2 and 'κ' in lab) else 'unp', 'unp'][i] if i < 4 else 'x'}"
        f"={to_fixed(v, 3)}"
        for i, v in enumerate(o["b"]))
    print(f"  {lab.ljust(24)} R²={f2(o['r2'])}  RMS={f2(o['rms'])}   {terms}")
print("\n(signs to expect if the hypothesis holds: ε_coast coeff > 0; κ and unpaved coeffs < 0)")

# ---- per-ride CSV (for research/article/figs/make_figures.py; no GPS, gitignored like the others) ----
csv_head = "ride,epsBal,epsCoast,epsLump,sbar,bHminus,kappa,unpaved,sheet"
csv_rows = [",".join([
    json.dumps(r["ride"], ensure_ascii=False), js_num(r["epsBal"]), js_num(r["epsCoast"]),
    js_num(r["epsLump"]), js_num(r["sbar"]), js_num(r["bHd"]),
    "" if r["kappa"] is None else js_num(r["kappa"]),
    "" if r["unpaved"] is None else js_num(r["unpaved"]),
    "" if r["sheet"] is None else js_num(r["sheet"]),
]) for r in good]
with open(os.path.join(RESULTS, "eps_hypothesis.csv"), "w") as fh:
    fh.write(csv_head + "\n" + "\n".join(csv_rows) + "\n")
print(f"\nwrote eps_hypothesis.csv ({len(good)} rides)")
