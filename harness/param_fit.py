#!/usr/bin/env python3
"""Per-activity CdA / C_rr / wind / mass estimation (journal Entry 15) —
Python port of harness/param_fit.mjs (same stdout, byte-identical CSV).

Adds WIND (the missing parameter) via GPS BEARING: a ride that heads in several
directions under one wind vector shows a directional asymmetry in aero cost that
identifies CdA AND the wind together (Chung "virtual elevation" / aerometers).
Mass is fixed at the rider level from braking-free climbs; then a 4-parameter
no-intercept least squares on the linearised power balance gives (C_rr, CdA, CdA·We,
CdA·Wn) per activity, iterated 3× to fold the w² term back in.

  python3 harness/param_fit.py     -> results/param_fit.csv + the console report

WHY THIS ONE CARRIES ITS OWN MATH (and not just analysis/bem):

* ``ptsWithGeo`` is the one point-builder in the repo that is NOT the verbatim
  ptsFromFIT — it keeps lat/lon because the fit needs a per-sample BEARING (see
  CLAUDE.md).  Bearings and haversine run through Math.atan2/sin/cos, so every
  trig call here uses bem.v8math's bit-exact V8 (fdlibm) kernels; Apple's libm
  differs in the last ulp and that ulp reaches the fitted CdA/C_rr digits.
* ``js_pow`` below is a bit-exact transliteration of v8::base::ieee754::pow —
  needed because JS ``v ** 3`` and ``Math.pow(b, 5.25588)`` (rhoAt) are genuine
  fdlibm pow calls, which differ from Python's libm pow on ~10% of inputs.
  Read the docstring: V8's pow is fdlibm *with FMA contraction* AND with the
  final correction term in the DENOMINATOR.  Verified bit-identical against node
  on 180k samples across the ranges this harness uses.
* ``js_hypot`` reproduces V8's Kahan-compensated Math.hypot (C99 hypot differs).
* parseFIT is the EXTENDED copy (cadence field 4 + file_id manufacturer), like
  ppaz_compare's; haversine is byte-identical to analysis/parity/reference.mjs
  but must run on the V8 kernels, so it is ported here rather than imported.

The .mjs also carries a pile of dead engine code (canonical, approxComponents,
buildProfile, extractRegimePowers, ptsFromFIT, deadband, empiricalKJ,
overallMeanPower, hasPower, pushStats, epsGeom, climbBalance, epsCellsPz,
flatEqSpeed, resampleProfile) copied from its sibling harnesses and never called
— approxComponents would even throw (it reads an undefined CLIMB_THR).  None of
it is ported: it cannot reach the output.
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

from bem.jsfmt import to_fixed
from bem.v8math import (_fma, _fw, _hi, _hi_s, _js_asin, _js_atan2, _js_cos,
                        _js_sin, _lo, js_num)

DATA = os.path.join(REPO, "data", "activities")
RESULTS = os.path.join(REPO, "results")
os.makedirs(RESULTS, exist_ok=True)

FIT_MANUF = None   # file_id manufacturer, set by parse_fit (kept for parity; unused here)

KEFF, G = 0.98, 9.81
TO_R = math.pi / 180


# ---------------------------------------------------------------------------
# JS semantics helpers
# ---------------------------------------------------------------------------

def is_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def jsdiv(a, b):
    """JS division when b == 0 (Python raises; JS yields NaN / ±Infinity)."""
    if b != 0:
        return a / b
    if a == 0 or a != a:
        return float("nan")
    neg = (a < 0) != (math.copysign(1.0, b) < 0)
    return float("-inf") if neg else float("inf")


def jmin(a, b):
    """Math.min(a, b) — NaN-propagating (Python's min is not)."""
    if a != a or b != b:
        return float("nan")
    return a if a < b else b


def jmax(a, b):
    """Math.max(a, b) — NaN-propagating."""
    if a != a or b != b:
        return float("nan")
    return a if a > b else b


def jnum(s):
    """JS unary plus on a string (+x → Number(x); NaN on garbage)."""
    t = s.strip()
    if t == "":
        return 0.0
    try:
        if t.lower().lstrip("+-").startswith("0x"):
            return float(int(t, 16))
        return float(t)
    except ValueError:
        return float("nan")


_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def jquote(s):
    """JSON.stringify(string) — the CSV's rider column."""
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


# ---------------------------------------------------------------------------
# bit-exact V8 Math.pow  (v8::base::ieee754::pow, arm64 clang -ffp-contract=on)
#
# fdlibm __ieee754_pow, with two departures that the disassembly of the node
# binary settles and that are BOTH load-bearing (fixing either one on its own
# misses V8 by 1 ulp on ~5% of inputs):
#   * every `a*b ± c` in the kernel is a fused multiply-add (fmadd/fmsub), and
#   * the final correction reads   r = (z*t1) / ((t1 - 2) - (w + z*w))
#     i.e. `w + z*w` sits in the DENOMINATOR, not subtracted from the quotient
#     as in stock fdlibm.
# Verified bit-identical to node on 180k samples over the ranges used here
# (y = 3 for v³, y = 5.25588 for the ISA density, plus wide random x/y).
# ---------------------------------------------------------------------------

_BP = (1.0, 1.5)
_DP_H = (0.0, _fw(0x3FE2B803, 0x40000000))
_DP_L = (0.0, _fw(0x3E4CFDEB, 0x43CFD006))
_TWO53 = 9007199254740992.0
_PHUGE = 1.0e300
_PTINY = 1.0e-300
_OVT = 8.0085662595372944372e-17
_L1 = _fw(0x3FE33333, 0x33333303)
_L2 = _fw(0x3FDB6DB6, 0xDB6FABFF)
_L3 = _fw(0x3FD55555, 0x518F264D)
_L4 = _fw(0x3FD17460, 0xA91D4101)
_L5 = _fw(0x3FCD864A, 0x93C9DB65)
_L6 = _fw(0x3FCA7E28, 0x4A454EEF)
_P1 = _fw(0x3FC55555, 0x5555553E)
_P2 = _fw(0xBF66C16C, 0x16BEBD93)
_P3 = _fw(0x3F11566A, 0xAF25DE2C)
_P4 = _fw(0xBEBBBD41, 0xC5D26BF1)
_P5 = _fw(0x3E663769, 0x72BEA4D0)
_LG2 = _fw(0x3FE62E42, 0xFEFA39EF)
_LG2_H = _fw(0x3FE62E43, 0x00000000)
_LG2_L = _fw(0xBE205C61, 0x0CA86C39)
_CP = _fw(0x3FEEC709, 0xDC3A03FD)
_CP_H = _fw(0x3FEEC709, 0xE0000000)
_CP_L = _fw(0xBE3E2FE0, 0x145B01F5)
_IVLN2 = _fw(0x3FF71547, 0x652B82FE)
_IVLN2_H = _fw(0x3FF71547, 0x60000000)
_IVLN2_L = _fw(0x3E54AE0B, 0xF85DDF44)
_NAN = float("nan")


def _slw0(x):
    return _fw(_hi(x), 0)


def _shw(x, hi):
    return _fw(hi, _lo(x))


def _i32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def js_pow(x, y):
    hx = _hi_s(x)
    lx = _lo(x)
    hy = _hi_s(y)
    ly = _lo(y)
    ix = hx & 0x7FFFFFFF
    iy = hy & 0x7FFFFFFF
    if (iy | ly) == 0:                       # y == ±0
        return 1.0
    if (ix > 0x7FF00000 or (ix == 0x7FF00000 and lx != 0)
            or iy > 0x7FF00000 or (iy == 0x7FF00000 and ly != 0)):
        return x + y                         # ±NaN
    yisint = 0
    if hx < 0:
        if iy >= 0x43400000:
            yisint = 2                       # even integer y
        elif iy >= 0x3FF00000:
            k = (iy >> 20) - 0x3FF
            if k > 20:
                j = ly >> (52 - k)
                if ((j << (52 - k)) & 0xFFFFFFFF) == ly:
                    yisint = 2 - (j & 1)
            elif ly == 0:
                j = iy >> (20 - k)
                if (j << (20 - k)) == iy:
                    yisint = 2 - (j & 1)
    if ly == 0:
        if iy == 0x7FF00000:                 # y is ±inf
            if ((ix - 0x3FF00000) | lx) == 0:
                return y - y                 # (±1)**±inf is NaN
            if ix >= 0x3FF00000:
                return y if hy >= 0 else 0.0
            return -y if hy < 0 else 0.0
        if iy == 0x3FF00000:                 # y is ±1
            return 1.0 / x if hy < 0 else x
        if hy == 0x40000000:                 # y is 2
            return x * x
        if hy == 0x3FE00000 and hx >= 0:     # y is 0.5, x >= +0
            return math.sqrt(x)
    ax = abs(x)
    if lx == 0 and (ix == 0x7FF00000 or ix == 0 or ix == 0x3FF00000):
        z = ax                               # x is ±0, ±inf, ±1
        if hy < 0:
            z = 1.0 / z
        if hx < 0:
            if ((ix - 0x3FF00000) | yisint) == 0:
                z = _NAN                     # (-1)**non-int
            elif yisint == 1:
                z = -z                       # (x<0)**odd
        return z
    n = ((hx & 0xFFFFFFFF) >> 31) - 1
    if (n | yisint) == 0:
        return _NAN                          # (x<0)**(non-int)
    s = 1.0
    if (n | (yisint - 1)) == 0:
        s = -1.0                             # (-ve)**(odd int)
    if iy > 0x41E00000:                      # |y| > 2**31
        if iy > 0x43F00000:                  # |y| > 2**64: must over/underflow
            if ix <= 0x3FEFFFFF:
                return _PHUGE * _PHUGE if hy < 0 else _PTINY * _PTINY
            if ix >= 0x3FF00000:
                return _PHUGE * _PHUGE if hy > 0 else _PTINY * _PTINY
        if ix < 0x3FEFFFFF:
            return s * _PHUGE * _PHUGE if hy < 0 else s * _PTINY * _PTINY
        if ix > 0x3FF00000:
            return s * _PHUGE * _PHUGE if hy > 0 else s * _PTINY * _PTINY
        t = ax - 1.0                         # |1-x| tiny: log(x) by series
        w = (t * t) * _fma(-t, (0.3333333333333333333333 - t * 0.25), 0.5)
        u = _IVLN2_H * t
        v = _fma(t, _IVLN2_L, -(w * _IVLN2))
        t1 = _slw0(u + v)
        t2 = v - (t1 - u)
    else:
        n = 0
        if ix < 0x00100000:                  # subnormal x
            ax *= _TWO53
            n -= 53
            ix = _hi(ax)
        n += (ix >> 20) - 0x3FF
        j = ix & 0x000FFFFF
        ix = j | 0x3FF00000                  # normalize ix
        if j <= 0x3988E:
            k = 0                            # |x| < sqrt(3/2)
        elif j < 0xBB67A:
            k = 1                            # |x| < sqrt(3)
        else:
            k = 0
            n += 1
            ix -= 0x00100000
        ax = _shw(ax, ix)
        u = ax - _BP[k]
        v = 1.0 / (ax + _BP[k])
        ss = u * v
        s_h = _slw0(ss)
        t_h = _fw((((ix >> 1) | 0x20000000) + 0x00080000 + (k << 18)) & 0xFFFFFFFF, 0)
        t_l = ax - (t_h - _BP[k])
        s_l = v * _fma(-s_h, t_l, _fma(-s_h, t_h, u))
        s2 = ss * ss
        r = _fma(s_l, (s_h + ss), (s2 * s2) * _fma(
            s2, _fma(s2, _fma(s2, _fma(s2, _fma(s2, _L6, _L5), _L4), _L3), _L2), _L1))
        s2 = s_h * s_h
        t_h = _slw0((s2 + 3.0) + r)
        t_l = r - ((t_h - 3.0) - s2)
        u = s_h * t_h
        v = _fma(s_l, t_h, t_l * ss)
        p_h = _slw0(u + v)
        p_l = v - (p_h - u)
        z_h = _CP_H * p_h
        z_l = _DP_L[k] + _fma(p_h, _CP_L, p_l * _CP)
        t = float(n)
        t1 = _slw0((_DP_H[k] + (z_h + z_l)) + t)
        t2 = z_l - (((t1 - t) - _DP_H[k]) - z_h)
    y1 = _slw0(y)                            # split y into y1 + y2
    p_l = _fma((y - y1), t1, t2 * y)
    p_h = t1 * y1
    z = p_h + p_l
    j = _hi_s(z)
    i = _lo(z)
    if j >= 0x40900000:                                  # z >= 1024
        if ((j - 0x40900000) | i) != 0:
            return s * _PHUGE * _PHUGE                   # overflow
        if p_l + _OVT > z - p_h:
            return s * _PHUGE * _PHUGE                   # overflow
    elif (j & 0x7FFFFFFF) >= 0x4090CC00:                 # z <= -1075
        if (_i32(j - 0xC090CC00) | i) != 0:
            return s * _PTINY * _PTINY                   # underflow
        if p_l <= z - p_h:
            return s * _PTINY * _PTINY                   # underflow
    i = j & 0x7FFFFFFF                                   # compute 2**(p_h+p_l)
    k = (i >> 20) - 0x3FF
    n = 0
    if i > 0x3FE00000:                                   # |z| > 0.5: n = [z+0.5]
        n = _i32(j + (0x00100000 >> (k + 1)))
        k = ((n & 0x7FFFFFFF) >> 20) - 0x3FF
        t = _fw(n & ~(0x000FFFFF >> k) & 0xFFFFFFFF, 0)
        n = ((n & 0x000FFFFF) | 0x00100000) >> (20 - k)
        if j < 0:
            n = -n
        p_h -= t
    t = _slw0(p_l + p_h)
    u = t * _LG2_H
    v = _fma((p_l - (t - p_h)), _LG2, t * _LG2_L)
    z = u + v
    w = v - (z - u)
    t = z * z
    t1 = _fma(-t, _fma(t, _fma(t, _fma(t, _fma(t, _P5, _P4), _P3), _P2), _P1), z)
    r = jsdiv(z * t1, (t1 - 2.0) - _fma(z, w, w))
    z = (z - r) + 1.0
    j = _i32(_hi_s(z) + _i32(n << 20))
    if (j >> 20) <= 0:
        z = math.ldexp(z, n)                             # subnormal output
    else:
        z = _shw(z, j)
    return s * z


def js_hypot(a, b):
    """V8's Math.hypot (builtins-math.cc): normalise by the max, then Kahan-
    compensate the sum of squares. C99 hypot() gives a different last bit."""
    av = [abs(a), abs(b)]
    mx = 0.0
    for v in av:
        if not (v <= mx):        # negated so NaN wins, as V8 does
            mx = v
    if mx == 0:
        return 0
    total = 0.0
    comp = 0.0
    for v in av:
        n = v / mx
        summand = n * n - comp
        preliminary = total + summand
        comp = (preliminary - total) - summand
        total = preliminary
    return math.sqrt(total) * mx


# ---------------------------------------------------------------------------
# shared pipeline pieces (bodies as in analysis/parity/reference.mjs, but they
# must run on the V8 kernels, so they are ported here rather than imported)
# ---------------------------------------------------------------------------

def haversine(a, b):
    R = 6371000
    to_r = math.pi / 180
    d_lat = (b["lat"] - a["lat"]) * to_r
    d_lon = (b["lon"] - a["lon"]) * to_r
    s1 = _js_sin(d_lat / 2)
    s2 = _js_sin(d_lon / 2)
    s = s1 * s1 + _js_cos(a["lat"] * to_r) * _js_cos(b["lat"] * to_r) * (s2 * s2)
    return 2 * R * _js_asin(jmin(1, math.sqrt(s)))


def rho_at(h):
    return 1.225 * js_pow(1 - 2.25577e-5 * jmax(0, jmin(h, 11000)), 5.25588)


def median(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


def q(xs, p):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return float("nan")
    return s[max(0, math.floor(p * (len(s) - 1)))]


# ---- FIT parsing — the EXTENDED copy (cadence field 4 + file_id manufacturer) ----

def _reader(buf, little):
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
        return None

    return read


def parse_fit(buf):
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
    last_ts = None   # running timestamp for compressed-timestamp headers
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
                fields.append((buf[pos], buf[pos + 1], buf[pos + 2]))   # num, size, bt
                pos += 3
            dev_size = 0
            if has_dev:
                nd = buf[pos]
                pos += 1
                for _ in range(nd):
                    dev_size += buf[pos + 1]
                    pos += 3
            defs[local] = {"gmn": gmn, "fields": fields, "devSize": dev_size,
                           "read": _reader(buf, little)}
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
                            rec["cad"] = v          # cadence (rpm)
                        elif num == 253:
                            rec["time"] = v
                elif gmn == 0 and num == 1:   # file_id manufacturer (260 = Zwift)
                    v = read(p, bt)
                    if v is not None:
                        FIT_MANUF = v
                elif num == 253:              # any message's timestamp advances the clock
                    v = read(p, bt)
                    if v is not None:
                        rec["time"] = v
                p += size
            pos = p + d["devSize"]
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


# ---- raw records: FIT (verbatim) or the one author-longões GPX ----

_TRKPT = re.compile(r'<trkpt\b([^>]*)>([\s\S]*?)</trkpt>')
_LAT = re.compile(r'lat="([-\d.]+)"')
_LON = re.compile(r'lon="([-\d.]+)"')
_ELE = re.compile(r'<ele>\s*([-\d.]+)')
_TIME = re.compile(r'<time>\s*([^<]+)')
_POWER = re.compile(r'<(?:\w+:)?power>\s*([\d.]+)')


def _date_parse(s):
    """Date.parse(s) / 1000 (NaN when unparseable, as JS)."""
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float("nan")


def parse_gpx_records(text):
    """minimal GPX record reader — lat/lon/ele/time/power (no speed, no cadence)."""
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
                    "alt": float(ele.group(1)) if ele else None,
                    "time": _date_parse(tm.group(1)) if tm else None,
                    "power": float(pw.group(1)) if pw else None})
    return out


def raw_records(file):
    with open(os.path.join(DATA, file), "rb") as fh:
        buf = fh.read()
    if file.endswith(".gz") and not file.endswith(".gpx.gz"):
        buf = gzip.decompress(buf)
    if file.endswith(".gpx"):
        return parse_gpx_records(buf.decode("utf-8"))
    return parse_fit(buf)   # records carry lat/lon/alt/dist/speed/power/cad/time


# ---- enriched points with bearing, distance, grade, acceleration (needs GPS) ----

def pts_with_geo(recs):
    g = [r for r in recs
         if r.get("lat") is not None and r.get("lon") is not None
         and r.get("alt") is not None and r.get("time") is not None]
    if len(g) < 30:
        return None
    pts = []
    cum = 0
    for i in range(len(g)):
        if i > 0:
            cum += haversine(g[i - 1], g[i])
        pts.append({"x": cum, "alt": g[i]["alt"], "v": g[i].get("speed"),
                    "power": g[i].get("power"), "cad": g[i].get("cad"),
                    "t": g[i]["time"], "lat": g[i]["lat"], "lon": g[i]["lon"]})
    # dt (clamp pauses <= 10 s), fallback speed from distance/time
    n = len(pts)
    for i in range(n):
        raw = (pts[i]["t"] - pts[i - 1]["t"]) if i > 0 else None
        pts[i]["dt"] = jmin(jmax(raw, 0), 10) if raw is not None else 1
        if pts[i]["v"] is None and i > 0:
            dtv = raw if raw > 0 else pts[i]["dt"]
            pts[i]["v"] = (pts[i]["x"] - pts[i - 1]["x"]) / dtv if dtv > 0 else 0
    # bearing (rad from north), grade (30 m window), acceleration
    W = 30
    for i in range(n):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        d_lon = (b["lon"] - a["lon"]) * TO_R
        cos_blat = _js_cos(b["lat"] * TO_R)                # used twice; same value
        y = _js_sin(d_lon) * cos_blat
        xb = (_js_cos(a["lat"] * TO_R) * _js_sin(b["lat"] * TO_R)
              - _js_sin(a["lat"] * TO_R) * cos_blat * _js_cos(d_lon))
        pts[i]["bear"] = _js_atan2(y, xb)
        j = i
        while j < n - 1 and pts[j]["x"] - pts[i]["x"] < W:
            j += 1
        dd = pts[j]["x"] - pts[i]["x"]
        if dd > 1:
            pts[i]["grade"] = (pts[j]["alt"] - pts[i]["alt"]) / dd
        else:
            pts[i]["grade"] = pts[i - 1]["grade"] if i > 0 else 0
        if (i > 0 and pts[i]["v"] is not None and pts[i - 1]["v"] is not None
                and pts[i]["dt"] > 0):
            pts[i]["acc"] = (pts[i]["v"] - pts[i - 1]["v"]) / pts[i]["dt"]
        else:
            pts[i]["acc"] = 0
    return pts


# ---- k-param no-intercept linear least squares (normal equations + Gauss) ----

def ols_k(feats, ys):
    k = len(feats[0])
    n = len(ys)
    M = [[0.0] * (k + 1) for _ in range(k)]
    syy = 0.0
    my = 0.0
    for y in ys:
        my += y
    my /= n
    for i in range(n):
        f = feats[i]
        yi = ys[i]
        for a in range(k):
            Ma = M[a]
            fa = f[a]
            for b in range(k):
                Ma[b] += fa * f[b]
            Ma[k] += fa * yi
        d = yi - my
        syy += d * d               # (ys[i] - my) ** 2 — V8's x**2 is exactly x*x
    for c in range(k):
        piv = c
        for r in range(c + 1, k):
            if abs(M[r][c]) > abs(M[piv][c]):
                piv = r
        M[c], M[piv] = M[piv], M[c]
        if abs(M[c][c]) < 1e-15:
            return None
        for r in range(k):
            if r != c:
                fac = M[r][c] / M[c][c]
                for j in range(c, k + 1):
                    M[r][j] -= fac * M[c][j]
    out = [M[i][k] / M[i][i] for i in range(k)]
    sse = 0.0
    for i in range(n):
        e = ys[i]
        for a in range(k):
            e -= out[a] * feats[i][a]
        sse += e * e
    return {"theta": out, "r2": 1 - jsdiv(sse, syy)}


# ---- per-activity fit — LINEARISED aero regression (no wind grid) ----
# T = P·keff − (m·a + m·g·sinθ)·v
#   = Crr·[m g cosθ v] + CdA·[½ρv³] + (CdA·We)·[−ρv² sin β] + (CdA·Wn)·[−ρv² cos β]
# A clean 4-parameter no-intercept regression; one refinement pass folds the w²
# term back in as a known correction to T.

def fit_activity(pts, m):
    rho = rho_at(median([p["alt"] for p in pts]))
    S = []
    for p in pts:
        if (p["power"] is None or p["v"] is None or p["v"] < 3 or p["power"] <= 0):
            continue
        if abs(p["acc"]) > 1.5:
            continue
        grade = p["grade"]
        sec = math.sqrt(1 + grade * grade)
        v = p["v"]
        bear = p["bear"]
        S.append({"v": v, "pw": p["power"], "acc": p["acc"], "sin": grade / sec,
                  "cos": 1 / sec, "bear": bear,
                  "flatFast": abs(grade) < 0.03 and v >= 5,
                  # cached: identical across the 3 refinement passes (pure fns of `bear`/`v`)
                  "sinB": _js_sin(bear), "cosB": _js_cos(bear), "v3": js_pow(v, 3)})
    if len(S) < 200:
        return None
    n_aero = 0
    for s in S:
        if s["flatFast"]:
            n_aero += 1
    vs = [s["v"] for s in S]
    v_spread = q(vs, 0.9) - q(vs, 0.1)
    aero_dirs = [s for s in S if s["flatFast"]]
    ds_n = len(aero_dirs) or 1
    sc = 0.0
    for s in aero_dirs:
        sc += s["cosB"]
    sn = 0.0
    for s in aero_dirs:
        sn += s["sinB"]
    ac, an = sc / ds_n, sn / ds_n
    dir_spread = math.sqrt(jmax(0, 1 - ac * ac - an * an))

    # feats depend only on (m, G, rho, S) — identical in all three passes
    feats = [[m * G * s["cos"] * s["v"], 0.5 * rho * s["v3"],
              -rho * s["v"] * s["v"] * s["sinB"], -rho * s["v"] * s["v"] * s["cosB"]]
             for s in S]

    cda, crr, We, Wn = 0.3, 0.006, 0, 0
    r2 = float("nan")
    for _ in range(3):
        ys = []
        for s in S:
            w = -(We * s["sinB"] + Wn * s["cosB"])
            w2corr = 0.5 * rho * cda * s["v"] * w * w     # known w² correction (last pass)
            ys.append(s["pw"] * KEFF - (m * s["acc"] + m * G * s["sin"]) * s["v"] - w2corr)
        f = ols_k(feats, ys)
        if not f:
            return None
        crr = f["theta"][0]
        cda = f["theta"][1]
        r2 = f["r2"]
        if not cda > 0.02:
            return None                                    # unphysical CdA
        We = f["theta"][2] / cda
        Wn = f["theta"][3] / cda
    first, last = pts[0], pts[len(pts) - 1]
    net = haversine(first, last)
    plen = last["x"] - first["x"]
    return {"cda": cda, "crr": crr, "We": We, "Wn": Wn, "W": js_hypot(We, Wn),
            "windDir": math.fmod(_js_atan2(We, Wn) / TO_R + 360, 360),
            "r2": r2, "n": len(S), "nAero": n_aero, "vSpread": v_spread,
            "dirSpread": dir_spread,
            "straight": net / plen if plen > 0 else 1, "km": plen / 1000}


# ---- rider mass from braking-free climbs (CdA-insensitive; nominal CdA = 0.35) ----

def rider_mass(files):
    A, B, C, E = [], [], [], []
    for f in files:
        try:
            recs = raw_records(f)
            pts = pts_with_geo(recs)
            if not pts:
                continue
            rho = rho_at(median([p["alt"] for p in pts]))
            npts = len(pts)
            st, r_max, r_max_i = -1, float("-inf"), -1
            for i in range(npts + 1):
                if i < npts:
                    if st < 0:
                        if pts[i]["grade"] > 0:
                            st = i
                            r_max = pts[i]["alt"]
                            r_max_i = i
                        continue
                    if pts[i]["alt"] > r_max:
                        r_max = pts[i]["alt"]
                        r_max_i = i
                    if r_max - pts[i]["alt"] <= 8 and i < npts - 1:
                        continue
                if st < 0:
                    continue
                a0, b = st, r_max_i
                st, r_max = -1, float("-inf")
                if b <= a0 or pts[b]["alt"] - pts[a0]["alt"] < 50:
                    continue
                a = a0
                while a < b and pts[a]["alt"] - pts[a0]["alt"] < 10:
                    a += 1
                dh = pts[b]["alt"] - pts[a]["alt"]
                dx = pts[b]["x"] - pts[a]["x"]
                if dh < 40 or dx < 100:
                    continue
                Ew, aero, ok = 0.0, 0.0, True
                for k in range(a + 1, b + 1):
                    p = pts[k]
                    if p["power"] is None or p["v"] is None:
                        ok = False
                        break
                    Ew += p["power"] * p["dt"]
                    aero += js_pow(p["v"], 3) * p["dt"]
                if not ok or Ew <= 0:
                    continue
                va, vb = pts[a]["v"], pts[b]["v"]
                if va is None or vb is None:
                    continue
                A.append(G * dh + 0.5 * (vb * vb - va * va))
                B.append(G * dx)
                C.append(0.5 * rho * aero)
                E.append(KEFF * Ew)
        except Exception:
            pass   # skip
    # 2-param (m, Crr·m) with CdA fixed at 0.35
    s11 = s12 = s22 = y1 = y2 = 0.0
    for i in range(len(E)):
        Ep = E[i] - 0.35 * C[i]
        s11 += A[i] * A[i]
        s12 += A[i] * B[i]
        s22 += B[i] * B[i]
        y1 += A[i] * Ep
        y2 += B[i] * Ep
    det = s11 * s22 - s12 * s12
    return {"m": jsdiv(y1 * s22 - y2 * s12, det), "nSeg": len(E)}


def list_riders():
    R = []

    def load(mf, filt):
        with open(os.path.join(DATA, mf), encoding="utf-8") as fh:
            return [a for a in json.load(fh) if filt(a)]

    def ride(a):
        return a["sport"] == "ride" and a["powCov"] > 0.5 and a["km"] >= 20

    try:
        R.append({"name": "P. Paz",
                  "range": {"m": [72, 90], "cda": [0.25, 0.45], "crr": [0.004, 0.015]},
                  "files": [a["file"] for a in load("strava_ppaz_manifest.json", ride)]})
    except Exception as e:
        sys.stdout.flush()
        print(e, file=sys.stderr)
    try:
        R.append({"name": "JAAM",
                  "range": {"m": [93, 107], "cda": [0.25, 0.45], "crr": [0.004, 0.015]},
                  "files": [a["file"] for a in load("strava_jaam_manifest.json", ride)]})
    except Exception as e:
        sys.stdout.flush()
        print(e, file=sys.stderr)
    try:
        R.append({"name": "author/longões",
                  "range": {"m": [68, 80], "cda": [0.28, 0.45], "crr": [0.004, 0.015]},
                  "files": [e["file"] for e in load(
                      "model_inputs.json",
                      lambda e: e.get("has_power") and e.get("file"))]})
    except Exception as e:
        sys.stdout.flush()
        print(e, file=sys.stderr)
    # the author's FULL Strava export — the strongest anchor (true physics known)
    try:
        R.append({"name": "author/danlessa",
                  "range": {"m": [68, 80], "cda": [0.28, 0.45], "crr": [0.004, 0.015]},
                  "files": [a["file"] for a in load("strava_danlessa_manifest.json", ride)]})
    except Exception as e:
        sys.stdout.flush()
        print(e, file=sys.stderr)
    return R


print("================================================================")
print("PER-ACTIVITY CdA / C_rr / WIND / MASS  (wind via GPS bearing; mass rider-level from climbs)")
print("k_eff=0.98, ρ=ISA(altitude). Per activity: grid 2-D wind, non-neg linear (C_rr,CdA) at each.\n")

# ---- SYNTHETIC-WIND RECOVERY SELF-TEST (SYNTH=1): inject a known wind into the power
# (using each ride's own fitted CdA/C_rr/mass) and check the fit recovers it. ----
if os.environ.get("SYNTH"):
    We0 = jnum(os.environ["SYNTH_WE"]) if os.environ.get("SYNTH_WE") else 4
    Wn0 = jnum(os.environ["SYNTH_WN"]) if os.environ.get("SYNTH_WN") else 0
    R0 = list_riders()[0]
    m0 = rider_mass(R0["files"])["m"]
    print(f"SYNTHETIC WIND RECOVERY — inject (We={js_num(We0)}, Wn={js_num(Wn0)}) m/s, "
          f"rider {R0['name']}, m={to_fixed(m0, 0)} kg\n")
    done = 0
    for f in R0["files"]:
        if done >= 8:
            break
        try:
            pts = pts_with_geo(raw_records(f))
        except Exception:
            continue
        if not pts:
            continue
        base = fit_activity(pts, m0)
        if not base or base["dirSpread"] < 0.4 or base["nAero"] < 200:
            continue
        rho = rho_at(median([p["alt"] for p in pts]))
        # overwrite each point's power with the model power under the true wind
        for p in pts:
            if p["power"] is None or p["v"] is None or p["v"] < 3 or p["power"] <= 0:
                continue
            sec = math.sqrt(1 + p["grade"] * p["grade"])
            sin = p["grade"] / sec
            cos = 1 / sec
            w = -(We0 * _js_sin(p["bear"]) + Wn0 * _js_cos(p["bear"]))
            air = p["v"] + w
            Pw = ((m0 * p["acc"] + m0 * G * sin) * p["v"]
                  + base["crr"] * m0 * G * cos * p["v"]
                  + base["cda"] * 0.5 * rho * air * air * p["v"]) / KEFF
            p["power"] = Pw if Pw > 0 else 0.01     # noiseless synthetic power
        rec = fit_activity(pts, m0)
        if not rec:
            continue
        print(f"  {done + 1}: dirSpread {to_fixed(base['dirSpread'], 2)}, "
              f"straight {to_fixed(base['straight'], 2)}, nAero {base['nAero']}  →  "
              f"recovered |W| {to_fixed(rec['W'], 2)} m/s, dir {to_fixed(rec['windDir'], 0)}°  "
              f"(CdA {to_fixed(rec['cda'], 3)}, C_rr {to_fixed(rec['crr'], 4)})   "
              f"[truth 4.0 m/s, 270°]")
        done += 1
    sys.exit(0)


# Self-calibrate the wind-magnitude attenuation: inject a known 4 m/s wind (using each
# ride's own fitted CdA/C_rr/mass), refit, and take the median recovered/injected ratio α.
# Regression dilution (speed↔direction correlate on real roads) makes α ≈ 0.7; we de-bias
# real winds by 1/α.
def wind_attenuation(files, m, n_cal=25):
    We0, Wn0 = 4, 0
    ratios = []
    for f in files:
        if len(ratios) >= n_cal:
            break
        try:
            pts = pts_with_geo(raw_records(f))
        except Exception:
            continue
        if not pts:
            continue
        base = fit_activity(pts, m)
        if (not base or base["dirSpread"] < 0.5 or base["nAero"] < 300
                or not (base["cda"] > 0.15 and base["cda"] < 0.55)):
            continue
        rho = rho_at(median([p["alt"] for p in pts]))
        for p in pts:
            if p["power"] is None or p["v"] is None or p["v"] < 3 or p["power"] <= 0:
                continue
            sec = math.sqrt(1 + p["grade"] * p["grade"])
            sin = p["grade"] / sec
            cos = 1 / sec
            w = -(We0 * _js_sin(p["bear"]) + Wn0 * _js_cos(p["bear"]))
            air = p["v"] + w
            p["power"] = jmax(0.01, ((m * p["acc"] + m * G * sin) * p["v"]
                                     + base["crr"] * m * G * cos * p["v"]
                                     + base["cda"] * 0.5 * rho * air * air * p["v"]) / KEFF)
        rec = fit_activity(pts, m)
        if rec and rec["cda"] > 0.15 and rec["cda"] < 0.55:
            ratios.append(rec["W"] / js_hypot(We0, Wn0))
    a = median(ratios)
    return {"alpha": a if (a > 0.3 and a < 1.2) else 1, "n": len(ratios)}


rows = []
for r in list_riders():
    rm = rider_mass(r["files"])
    m = rm["m"]
    acts = []
    n_geo = n_fit = n_gate = 0
    for f in r["files"]:
        try:
            pts = pts_with_geo(raw_records(f))
            if not pts:
                continue
            n_geo += 1
            fit = fit_activity(pts, m)
            if not fit:
                continue
            n_fit += 1
            if fit["r2"] > 0.4 and fit["n"] >= 200:
                acts.append(fit)
                n_gate += 1
        except Exception:
            pass   # skip
    print(f"  [attrition] {len(r['files'])} files → {n_geo} with GPS → {n_fit} fittable "
          f"→ {n_gate} pass r²>0.4,n≥200")
    # "clean" = physically-plausible CdA + direction/speed spread to identify the wind
    good = [a for a in acts if a["dirSpread"] > 0.3 and a["vSpread"] > 3.5
            and a["cda"] > 0.15 and a["cda"] < 0.55]
    cdas = [a["cda"] for a in good]
    crrs = [a["crr"] for a in good]
    wa = wind_attenuation(r["files"], m)
    alpha, n_cal = wa["alpha"], wa["n"]
    winds = [a["W"] / alpha for a in good]              # de-biased wind magnitude
    rng = r["range"]

    def in_r(v, lohi):
        return "✓" if (v >= lohi[0] and v <= lohi[1]) else "✗"

    print(f"── {r['name']} ──  {len(acts)} activities fit ({len(good)} clean: "
          f"CdA∈[0.15,0.55], wind geometry)")
    print(f"  MASS  = {to_fixed(m, 1)} kg   [rider-level, {rm['nSeg']} climb seg]      "
          f"target {js_num(rng['m'][0])}–{js_num(rng['m'][1])}  {in_r(m, rng['m'])}")
    print(f"  CdA   = {to_fixed(median(cdas), 3)} m²  [IQR {to_fixed(q(cdas, .25), 2)}–"
          f"{to_fixed(q(cdas, .75), 2)}]   target {js_num(rng['cda'][0])}–"
          f"{js_num(rng['cda'][1])}  {in_r(median(cdas), rng['cda'])}")
    print(f"  C_rr  = {to_fixed(median(crrs), 4)}   [IQR {to_fixed(q(crrs, .25), 4)}–"
          f"{to_fixed(q(crrs, .75), 4)}]  target {js_num(rng['crr'][0])}–"
          f"{js_num(rng['crr'][1])}  {in_r(median(crrs), rng['crr'])}")
    print(f"  |wind|= {to_fixed(median(winds), 1)} m/s ({to_fixed(median(winds) * 3.6, 0)} km/h) "
          f"median, de-biased ÷α (α={to_fixed(alpha, 2)}, {n_cal}-ride synth calib); "
          f"per-activity range {to_fixed(q(winds, .1) * 3.6, 0)}–"
          f"{to_fixed(q(winds, .9) * 3.6, 0)} km/h")
    print(f"  median activity: {to_fixed(median([a['km'] for a in acts]), 0)} km, "
          f"straightness {to_fixed(median([a['straight'] for a in acts]), 2)}, "
          f"fit R² {to_fixed(median([a['r2'] for a in acts]), 2)}\n")
    rows.append({"rider": r["name"], "m": m, "cda": median(cdas), "crr": median(crrs),
                 "wind": median(winds), "alpha": alpha, "nAct": len(acts),
                 "nGood": len(good)})

csv_text = ("rider,mass_kg,cda_m2,crr,wind_ms_debiased,alpha,nAct,nGood\n"
            + "\n".join(
                f"{jquote(o['rider'])},{to_fixed(o['m'], 1)},{to_fixed(o['cda'], 3)},"
                f"{to_fixed(o['crr'], 4)},{to_fixed(o['wind'], 2)},{to_fixed(o['alpha'], 3)},"
                f"{o['nAct']},{o['nGood']}"
                for o in rows) + "\n")
with open(os.path.join(RESULTS, "param_fit.csv"), "w", encoding="utf-8") as fh:
    fh.write(csv_text)
print("wrote param_fit.csv")
