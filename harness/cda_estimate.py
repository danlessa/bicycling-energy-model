#!/usr/bin/env python3
"""Independent m / C_rr / CdA estimation for the shared riders (journal Entry 15)
— Python port of harness/cda_estimate.mjs (same console report, byte-identical
results/cda_estimate.csv).

The clean signal is the CLIMB: on a positive slope braking is negligible, so the
work–energy balance over an uphill segment is exact and linear in (m, C_rr·m, CdA):
    E_i = m·A_i + (C_rr·m)·B_i + CdA·C_i
      A_i = g·Δh_i + ½·Δ(v²)_i     B_i = g·Δx_i     C_i = ½·ρ·Σ(v³·dt)_i
      E_i = k_eff·Σ(P·dt)_i
A 3-parameter no-intercept least squares over many climb segments returns all three
with no assumed value for any of them (see the .mjs comment block for the rationale).

    python3 harness/cda_estimate.py

Shared pipeline pieces come from analysis/bem (the machine-verified Python port):
finish_pts. The .mjs's own copies whose bodies DIFFER from
analysis/parity/reference.mjs are ported locally, faithfully:
  - parseFIT / ptsFromFIT — EXTENDED with the cadence field (num 4) and the
    file_id manufacturer capture (FIT_MANUF), plus this harness's own 'no .FIT'
    signature error message.
  - haversine — same arithmetic as reference.mjs, but run on bem.v8math's
    fdlibm sin/cos/asin so the GPS/GPX distance path is bit-identical to V8.
  - ptsFromGPX — verbatim body, but must call the V8-math haversine above.
The .mjs also carries 14 functions that the driver never calls (flatEqSpeed,
resampleProfile, canonical, approxComponents, buildProfile, extractRegimePowers,
deadband, empiricalKJ, overallMeanPower, hasPower, pushStats, epsGeom,
climbBalance, epsCellsPz — dead copies kept for the engine-sync rule); they cannot
affect the output and are not reproduced here.

Output: console report + results/cda_estimate.csv.
"""

import gzip
import json
import math
import os
import re
import struct
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))

from bem import finish_pts
from bem.jsfmt import to_fixed
from bem.v8math import _js_asin, _js_cos, _js_sin, js_num

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
os.makedirs(RESULTS, exist_ok=True)

FIT_MANUF = None   # referenced by the verbatim engine; unused here


def is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def jsdiv(a, b):
    """JS division semantics when b == 0 (Python raises; JS yields ±inf/NaN)."""
    if b != 0:
        return a / b
    if a == 0 or a != a:
        return float("nan")
    neg = (a < 0) != (math.copysign(1.0, b) < 0)
    return float("-inf") if neg else float("inf")


# ---- pipeline copies whose bodies differ from reference.mjs ----

def haversine(a, b):
    R = 6371000
    to_r = math.pi / 180
    s1 = _js_sin((b["lat"] - a["lat"]) * to_r / 2)
    s2 = _js_sin((b["lon"] - a["lon"]) * to_r / 2)
    s = s1 * s1 + _js_cos(a["lat"] * to_r) * _js_cos(b["lat"] * to_r) * (s2 * s2)
    return 2 * R * _js_asin(min(1, math.sqrt(s)))


def _reader(buf, little):
    """read(p, bt) closure — out-of-range reads raise (struct.error /
    IndexError), as DataView throws RangeError in JS."""
    e = "<" if little else ">"

    def read(p, bt):
        b = bt & 0x1F
        if b == 0x01:
            v = struct.unpack_from(e + "b", buf, p)[0]
            return None if v == 0x7F else v
        if b in (0x00, 0x02, 0x0A, 0x0D):
            v = buf[p]
            return None if v == 0xFF else v
        if b == 0x03:
            v = struct.unpack_from(e + "h", buf, p)[0]
            return None if v == 0x7FFF else v
        if b in (0x04, 0x0B):
            v = struct.unpack_from(e + "H", buf, p)[0]
            return None if v == 0xFFFF else v
        if b == 0x05:
            v = struct.unpack_from(e + "i", buf, p)[0]
            return None if v == 0x7FFFFFFF else v
        if b in (0x06, 0x0C):
            v = struct.unpack_from(e + "I", buf, p)[0]
            return None if v == 0xFFFFFFFF else v
        if b == 0x08:
            return struct.unpack_from(e + "f", buf, p)[0]
        if b == 0x09:
            return struct.unpack_from(e + "d", buf, p)[0]
        return None  # strings / 64-bit ignored

    return read


def parse_fit(buf):
    """The .mjs's EXTENDED parseFIT: cadence (field 4) + file_id manufacturer."""
    global FIT_MANUF
    if len(buf) < 14:
        raise ValueError("FIT muito curto")
    header_size = buf[0]
    data_size = struct.unpack_from("<I", buf, 4)[0]
    if buf[8:12] != b".FIT":
        raise ValueError("no .FIT")
    end = min(header_size + data_size, len(buf))
    FIT_MANUF = None
    pos = header_size
    defs = {}
    records = []
    last_ts = None   # running timestamp for compressed-timestamp headers (5-bit offset, 32 s rollover)
    while pos < end:
        rh = buf[pos]
        pos += 1
        ts_offset = None
        is_def = has_dev = False
        if rh & 0x80:
            local = (rh >> 5) & 0x03
            ts_offset = rh & 0x1F
        else:
            local = rh & 0x0F
            is_def = bool(rh & 0x40)
            has_dev = bool(rh & 0x20)
        if is_def:
            pos += 1
            little = buf[pos] == 0
            pos += 1
            gmn = struct.unpack_from("<H" if little else ">H", buf, pos)[0]
            pos += 2
            nf = buf[pos]
            pos += 1
            fields = []
            for _ in range(nf):
                fields.append((buf[pos], buf[pos + 1], buf[pos + 2]))  # num, size, bt
                pos += 3
            dev_size = 0
            if has_dev:
                nd = buf[pos]
                pos += 1
                for _ in range(nd):
                    dev_size += buf[pos + 1]
                    pos += 3
            defs[local] = {"gmn": gmn, "little": little, "fields": fields,
                           "devSize": dev_size, "read": _reader(buf, little)}
        else:
            d = defs.get(local)
            if d is None:
                raise ValueError("FIT corrompido (dado sem definição)")
            p = pos
            rec = {}
            read = d["read"]
            gmn = d["gmn"]
            for num, size, bt in d["fields"]:
                if gmn == 20:
                    v = read(p, bt)
                    if v is not None:
                        if num == 0:
                            rec["lat"] = v * (180 / 2147483648)
                        elif num == 1:
                            rec["lon"] = v * (180 / 2147483648)
                        elif num == 2:
                            if "alt" not in rec:
                                rec["alt"] = v / 5 - 500
                        elif num == 78:
                            rec["alt"] = v / 5 - 500
                        elif num == 5:
                            rec["dist"] = v / 100
                        elif num == 6:
                            if "speed" not in rec:
                                rec["speed"] = v / 1000
                        elif num == 73:
                            rec["speed"] = v / 1000
                        elif num == 7:
                            rec["power"] = v
                        elif num == 4:
                            rec["cad"] = v          # cadence (rpm) — 0 ⇒ not pedalling
                        elif num == 253:
                            rec["time"] = v
                elif gmn == 0 and num == 1:   # file_id manufacturer (260 = Zwift -> virtual ride)
                    v = read(p, bt)
                    if v is not None:
                        FIT_MANUF = v
                elif num == 253:   # any message's timestamp advances the running clock
                    v = read(p, bt)
                    if v is not None:
                        rec["time"] = v
                p += size
            pos = p + d["devSize"]
            # compressed-timestamp header: reconstruct the time from the 5-bit offset
            if ts_offset is not None and "time" not in rec and last_ts is not None:
                ts = (last_ts & ~31) | ts_offset
                if ts < last_ts:
                    ts += 32
                rec["time"] = ts
            if "time" in rec:
                last_ts = rec["time"]
            if gmn == 20:
                records.append(rec)
    return records


def pts_from_fit(buf):
    recs = parse_fit(buf)
    if len(recs) < 2:
        raise ValueError("FIT sem registros")
    pts = []
    if any("dist" in r for r in recs):
        di, dv = [], []
        for i, r in enumerate(recs):
            if "dist" in r:
                di.append(i)
                dv.append(max(r["dist"], dv[-1]) if dv else r["dist"])   # clip non-monotone device distance
        last_alt = None
        k = 0
        for i, r in enumerate(recs):
            if "alt" in r:
                last_alt = r["alt"]
            if last_alt is None:
                continue
            while k < len(di) - 1 and di[k + 1] <= i:
                k += 1
            if i <= di[0]:
                x = dv[0]
            elif i >= di[-1]:
                x = dv[-1]
            else:
                fr = (i - di[k]) / (di[k + 1] - di[k])
                x = dv[k] + (dv[k + 1] - dv[k]) * fr
            pts.append({"x": x, "alt": last_alt, "power": r.get("power"),
                        "cad": r.get("cad"), "t": r.get("time"), "v": r.get("speed")})
    else:
        geo = [r for r in recs if "lat" in r and "lon" in r and "alt" in r]
        if len(geo) < 2:
            raise ValueError("FIT sem distância nem GPS")
        cum = 0.0
        pts.append({"x": 0, "alt": geo[0]["alt"], "power": geo[0].get("power"),
                    "cad": geo[0].get("cad"), "t": geo[0].get("time"), "v": geo[0].get("speed")})
        for i in range(1, len(geo)):
            cum += haversine(geo[i - 1], geo[i])
            pts.append({"x": cum, "alt": geo[i]["alt"], "power": geo[i].get("power"),
                        "cad": geo[i].get("cad"), "t": geo[i].get("time"), "v": geo[i].get("speed")})
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


def pts_from_gpx(text):
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
    cum = 0.0
    pts = [{"x": 0, "alt": out[0]["alt"], "power": out[0].get("power"), "t": out[0].get("t")}]
    for i in range(1, len(out)):
        cum += haversine(out[i - 1], out[i])
        pts.append({"x": cum, "alt": out[i]["alt"], "power": out[i].get("power"),
                    "t": out[i].get("t")})
    finish_pts(pts)
    return pts


# ===== Independent CdA / mass / C_rr estimation (Entry 15) =====

KEFF, G = 0.98, 9.81


def rho_at(h):
    if h != h:   # Math.min/Math.max propagate NaN (Python's min/max do not)
        return float("nan")
    x = 11000 if h > 11000 else h        # Math.min(h, 11000)
    x = x if x > 0 else 0                # Math.max(0, ·)
    return 1.225 * math.pow(1 - 2.25577e-5 * x, 5.25588)


def median(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def ols3(A, B, C, E):
    """3-param no-intercept least squares  E = θ1·A + θ2·B + θ3·C (Gauss on the 3×3)."""
    n = len(E)
    M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    y = [0, 0, 0]
    syy = 0.0
    my = 0.0
    for e in E:
        my += e
    my = jsdiv(my, n)
    for i in range(n):
        f = [A[i], B[i], C[i]]
        for a in range(3):
            for b in range(3):
                M[a][b] += f[a] * f[b]
            y[a] += f[a] * E[i]
        syy += (E[i] - my) * (E[i] - my)   # (E[i] - my) ** 2 — V8's x**2 is x*x
    # Gaussian elimination on the 3×3
    m = [list(M[i]) + [y[i]] for i in range(3)]
    for c in range(3):
        piv = c
        for r in range(c + 1, 3):
            if abs(m[r][c]) > abs(m[piv][c]):
                piv = r
        m[c], m[piv] = m[piv], m[c]
        if abs(m[c][c]) < 1e-12:
            return {"theta": [float("nan")] * 3, "r2": float("nan"), "n": n}
        for r in range(3):
            if r != c:
                f = jsdiv(m[r][c], m[c][c])
                for k in range(c, 4):
                    m[r][k] -= f * m[c][k]
    theta = [jsdiv(m[0][3], m[0][0]), jsdiv(m[1][3], m[1][1]), jsdiv(m[2][3], m[2][2])]
    sse = 0.0
    for i in range(n):
        e = E[i] - theta[0] * A[i] - theta[1] * B[i] - theta[2] * C[i]
        sse += e * e
    return {"theta": theta, "r2": 1 - jsdiv(sse, syy), "n": n}


def ols2_fixed(A, B, C, E, cda_fix):
    """2-param no-intercept LS with CdA FIXED: subtract aero, fit E' = m·A + (Crr·m)·B."""
    s11 = s12 = s22 = y1 = y2 = 0.0
    for i in range(len(E)):
        Ep = E[i] - cda_fix * C[i]
        s11 += A[i] * A[i]
        s12 += A[i] * B[i]
        s22 += B[i] * B[i]
        y1 += A[i] * Ep
        y2 += B[i] * Ep
    det = s11 * s22 - s12 * s12
    if abs(det) < 1e-9:
        return {"m": float("nan"), "crr": float("nan")}
    m = jsdiv(y1 * s22 - y2 * s12, det)
    crr_m = jsdiv(s11 * y2 - s12 * y1, det)
    return {"m": m, "crr": jsdiv(crr_m, m)}


def corr(xs, ys):
    n = len(xs)
    mx = 0.0
    my = 0.0
    for i in range(n):
        mx += xs[i]
        my += ys[i]
    mx = jsdiv(mx, n)
    my = jsdiv(my, n)
    sxy = sxx = syy = 0.0
    for i in range(n):
        sxy += (xs[i] - mx) * (ys[i] - my)
        sxx += (xs[i] - mx) * (xs[i] - mx)   # ** 2 → x*x
        syy += (ys[i] - my) * (ys[i] - my)
    return jsdiv(sxy, math.sqrt(sxx * syy))


def bootstrap3(A, B, C, E, reps=400):
    """Bootstrap CIs on (m, CdA, Crr) — segments resampled with a fixed LCG.
    The seed step runs in DOUBLE arithmetic then ToInt32, exactly as JS
    (`seed * 1103515245` exceeds 2^53, so it rounds — Python ints would not)."""
    n = len(E)
    state = [12345]

    def rnd():
        prod = float(state[0]) * 1103515245.0 + 12345.0   # double, as JS
        state[0] = int(prod) & 0x7FFFFFFF                 # ToInt32 then & 0x7fffffff
        return state[0] / 0x7FFFFFFF

    ms, cdas, crrs = [], [], []
    for _ in range(reps):
        a, b, c, e = [], [], [], []
        for _i in range(n):
            j = math.floor(rnd() * n)
            a.append(A[j])
            b.append(B[j])
            c.append(C[j])
            e.append(E[j])
        f = ols3(a, b, c, e)
        if not is_finite(f["theta"][0]):
            continue
        ms.append(f["theta"][0])
        cdas.append(f["theta"][2])
        crrs.append(jsdiv(f["theta"][1], f["theta"][0]))

    def ci(arr):
        s = sorted(arr)
        return [s[math.floor(0.025 * len(s))], s[math.floor(0.975 * len(s))]]

    return {"mCI": ci(ms), "cdaCI": ci(cdas), "crrCI": ci(crrs)}


def read_pts(file):
    with open(os.path.join(DATA, file), "rb") as fh:
        buf = fh.read()
    if file.endswith(".gz") and not file.endswith(".gpx.gz"):
        buf = gzip.decompress(buf)
    if file.endswith(".gpx"):
        return pts_from_gpx(buf.decode("utf8"))
    return pts_from_fit(buf)


def grade30(pts):
    W = 30
    for i in range(len(pts)):
        j = i
        while j < len(pts) - 1 and pts[j]["x"] - pts[i]["x"] < W:
            j += 1
        dd = pts[j]["x"] - pts[i]["x"]
        if dd > 1:
            pts[i]["grade"] = (pts[j]["alt"] - pts[i]["alt"]) / dd
        else:
            pts[i]["grade"] = pts[i - 1]["grade"] if i > 0 else 0


def collect_climbs(files):
    """Contiguous 30 m-window grade ≥ 1% runs with total Δh ≥ 50 m; clip the first
    10 m of vertical (entry inertia), then measure A/B/C/E over the remainder."""
    A, B, C, E, meta = [], [], [], [], []
    gentle = []   # {dh, dx, dKE, aeroInt(=∫v³dt), Ewheel} for grade∈[1,3.5]%, v̄≥6 m/s
    n_rides = n_err = 0
    for f in files:
        try:
            pts = read_pts(f)
            if len(pts) < 30:
                continue
            grade30(pts)
            rho = rho_at(median([p["alt"] for p in pts]))
            n_rides += 1
            st = -1
            run_max = float("-inf")
            run_max_i = -1
            for i in range(len(pts) + 1):
                if i < len(pts):
                    if st < 0:
                        if pts[i]["grade"] > 0:
                            st = i
                            run_max = pts[i]["alt"]
                            run_max_i = i
                        continue
                    if pts[i]["alt"] > run_max:
                        run_max = pts[i]["alt"]
                        run_max_i = i
                    if run_max - pts[i]["alt"] <= 8 and i < len(pts) - 1:
                        continue   # 8 m drop budget: survive dips
                if st < 0:
                    continue
                a0, b = st, run_max_i       # end run at its altitude peak
                st = -1
                run_max = float("-inf")
                if b <= a0 or pts[b]["alt"] - pts[a0]["alt"] < 50:
                    continue                # net Δh ≥ 50 m
                a = a0
                while a < b and pts[a]["alt"] - pts[a0]["alt"] < 10:
                    a += 1                  # clip first 10 m of climb
                dh = pts[b]["alt"] - pts[a]["alt"]
                dx = pts[b]["x"] - pts[a]["x"]
                if dh < 40 or dx < 100:
                    continue
                e_wheel = aero_int = time = 0.0
                ok = True
                for k in range(a + 1, b + 1):
                    dt = pts[k].get("dt") or 0
                    v = pts[k].get("v")
                    if pts[k].get("power") is None or v is None:
                        ok = False
                        break
                    e_wheel += pts[k]["power"] * dt
                    aero_int += v * v * v * dt
                    time += dt
                if not ok or not (time > 0) or e_wheel <= 0:
                    continue
                va, vb = pts[a].get("v"), pts[b].get("v")
                if va is None or vb is None:
                    continue
                A.append(G * dh + 0.5 * (vb * vb - va * va))   # mass: gravity + ΔKE
                B.append(G * dx)                               # rolling: g·Δx
                C.append(0.5 * rho * aero_int)                 # aero: ½ρ∫v³dt (per unit CdA)
                E.append(KEFF * e_wheel)                       # wheel work
                meta.append({"dh": dh, "dx": dx, "vmean": dx / time, "grade": dh / dx})
                gr = dh / dx
                vbar = dx / time
                if gr >= 0.01 and gr <= 0.035 and vbar >= 6:
                    gentle.append({"dh": dh, "dx": dx, "dKE": 0.5 * (vb * vb - va * va),
                                   "aeroInt": aero_int, "Ewheel": KEFF * e_wheel, "rho": rho})
        except Exception:
            n_err += 1
    return {"A": A, "B": B, "C": C, "E": E, "meta": meta, "gentle": gentle,
            "nRides": n_rides, "nErr": n_err}


def list_riders():
    R = []
    try:
        with open(os.path.join(DATA, "strava_ppaz_manifest.json"), encoding="utf8") as fh:
            man = json.load(fh)
        R.append({"name": "P. Paz",
                  "files": [a["file"] for a in man
                            if a["sport"] == "ride" and a["powCov"] > 0.5 and a["km"] >= 20]})
    except Exception as e:
        print("ppaz?", e, file=sys.stderr)
    try:
        with open(os.path.join(DATA, "strava_jaam_manifest.json"), encoding="utf8") as fh:
            man = json.load(fh)
        R.append({"name": "JAAM",
                  "files": [a["file"] for a in man
                            if a["sport"] == "ride" and a["powCov"] > 0.5 and a["km"] >= 20]})
    except Exception as e:
        print("jaam?", e, file=sys.stderr)
    try:
        with open(os.path.join(DATA, "model_inputs.json"), encoding="utf8") as fh:
            inp = [e for e in json.load(fh) if e.get("has_power") and e.get("file")]
        R.append({"name": "author/longões", "files": [e["file"] for e in inp],
                  "aCdA": median([e["cda"] for e in inp]),
                  "aM": median([e["m"] for e in inp]),
                  "aCrr": median([e["crr"] for e in inp])})
    except Exception as e:
        print("longões?", e, file=sys.stderr)
    return R


_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def jquote(s):
    """JSON.stringify string quoting (the CSV's rider cell)."""
    out = ['"']
    for ch in s:
        if ch in _ESC:
            out.append(_ESC[ch])
        elif ch < " ":
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


print("================================================================")
print("INDEPENDENT m / C_rr / CdA — 3-param climb energy-balance regression (no braking uphill)")
print(f"k_eff={js_num(KEFF)}, ρ=ISA(altitude), wind=0. Segments: sustained uphill Δh≥50 m, "
      "first 10 m clipped, ≥40 m used.\n")

out = []
for r in list_riders():
    c = collect_climbs(r["files"])
    fit = ols3(c["A"], c["B"], c["C"], c["E"])
    m, crr_m, cda = fit["theta"]
    crr = jsdiv(crr_m, m)
    bs = bootstrap3(c["A"], c["B"], c["C"], c["E"])
    # Gentle-fast CdA: fix (m, C_rr) from the mass-robust climb fit (CdA≈0.35), then CdA per
    # gentle-fast segment = residual aero work / (½ρ∫v³dt); median over segments.
    m_fix = ols2_fixed(c["A"], c["B"], c["C"], c["E"], 0.35)
    M, CRR = m_fix["m"], m_fix["crr"]
    per_seg = [x for x in
               (jsdiv(s["Ewheel"] - M * s["dKE"] - M * G * s["dh"] - CRR * M * G * s["dx"],
                      0.5 * s["rho"] * s["aeroInt"]) for s in c["gentle"])
               if is_finite(x)]
    per_seg.sort()
    cda_g = median(per_seg)
    cda_giqr = ([per_seg[math.floor(0.25 * len(per_seg))], per_seg[math.floor(0.75 * len(per_seg))]]
                if len(per_seg) > 4 else [float("nan"), float("nan")])
    gr = [s["grade"] for s in c["meta"]]
    vm = [s["vmean"] for s in c["meta"]]
    print(f"── {r['name']} ──  {c['nRides']} rides ({c['nErr']} err), {len(c['E'])} climb segments")
    print(f"  grade range p10–p90: "
          f"{to_fixed(median([g for g in gr if g < median(gr)]) * 100, 1)}–"
          f"{to_fixed(median([g for g in gr if g > median(gr)]) * 100, 1)}%,  "
          f"climb speed median {to_fixed(median(vm) * 3.6, 1)} km/h  (aero leverage)")
    print(f"  m   = {to_fixed(m, 1)} kg     95% CI [{to_fixed(bs['mCI'][0], 0)}, {to_fixed(bs['mCI'][1], 0)}]")
    print(f"  C_rr= {to_fixed(crr, 4)}      95% CI [{to_fixed(bs['crrCI'][0], 4)}, {to_fixed(bs['crrCI'][1], 4)}]")
    print(f"  CdA = {to_fixed(cda, 3)} m²   95% CI [{to_fixed(bs['cdaCI'][0], 3)}, "
          f"{to_fixed(bs['cdaCI'][1], 3)}]   (R²={to_fixed(fit['r2'], 4)})")
    ab_corr = corr(c["A"], c["B"])
    print(f"  identifiability: corr(A_mass, B_roll) = {to_fixed(ab_corr, 3)}  "
          "(→1 ⇒ mass & C_rr collinear on climbs)")
    print(f"  gentle-fast CdA (grade 1–3.5%, v̄≥6 m/s, n={len(per_seg)} seg, m={to_fixed(M, 0)} kg "
          f"C_rr={to_fixed(CRR, 4)} from CdA=0.35 fit): CdA ≈ "
          f"{to_fixed(cda_g, 3) if is_finite(cda_g) else '—'} m²  "
          f"[IQR {to_fixed(cda_giqr[0], 2)}, {to_fixed(cda_giqr[1], 2)}]")
    ins = []
    for cd in (0.25, 0.35, 0.45):
        fx = ols2_fixed(c["A"], c["B"], c["C"], c["E"], cd)
        ins.append(f"CdA={js_num(cd)}→m={to_fixed(fx['m'], 0)}kg,C_rr={to_fixed(fx['crr'], 3)}")
    print("  CdA→mass insensitivity (fix CdA, fit m,C_rr):  " + "  ".join(ins))
    if r.get("aCdA") is not None:
        fA = ols2_fixed(c["A"], c["B"], c["C"], c["E"], r["aCdA"])
        print(f"  [anchor] longões assumed: CdA {to_fixed(r['aCdA'], 2)}, m {to_fixed(r['aM'], 0)}, "
              f"C_rr {to_fixed(r['aCrr'], 4)}   → with CdA fixed at truth: m={to_fixed(fA['m'], 0)} kg, "
              f"C_rr={to_fixed(fA['crr'], 4)}")
    print("")
    out.append({"rider": r["name"], "nSeg": len(c["E"]), "m": m, "crr": crr, "cda": cda,
                "r2": fit["r2"], "mCI": bs["mCI"], "cdaCI": bs["cdaCI"], "crrCI": bs["crrCI"]})

csv_text = ("rider,nSeg,mass_kg,crr,cda_m2,r2,m_lo,m_hi,cda_lo,cda_hi,crr_lo,crr_hi\n"
            + "\n".join(
                f"{jquote(o['rider'])},{o['nSeg']},{to_fixed(o['m'], 1)},{to_fixed(o['crr'], 4)},"
                f"{to_fixed(o['cda'], 3)},{to_fixed(o['r2'], 4)},{to_fixed(o['mCI'][0], 1)},"
                f"{to_fixed(o['mCI'][1], 1)},{to_fixed(o['cdaCI'][0], 3)},{to_fixed(o['cdaCI'][1], 3)},"
                f"{to_fixed(o['crrCI'][0], 4)},{to_fixed(o['crrCI'][1], 4)}"
                for o in out) + "\n")
with open(os.path.join(RESULTS, "cda_estimate.csv"), "w", encoding="utf8") as fh:
    fh.write(csv_text)
print("wrote cda_estimate.csv")
