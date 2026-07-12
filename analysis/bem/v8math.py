"""Bit-exact V8 number rendering and Math transcendentals.

Extracted from the eps_hypothesis port for reuse by every harness that emits
RAW full-precision floats (String(number) in JS) whose values flow through
Math.sin/cos/asin/atan/atan2 — Apple libm differs from V8's fdlibm in the
last ulp, and that ulp reaches the output bytes. Exposes:

- js_num(x)  — ECMAScript Number::ToString(10), full algorithm (exponent
  thresholds 1e21 / 1e-6, no exponent zero-padding).
- v8_sin, v8_cos, v8_asin, v8_atan, v8_atan2 — transliterated from V8
  12.9 src/base/ieee754.cc INCLUDING the arm64 clang FMA contraction,
  via a software correctly-rounded FMA (no math.fma in Python 3.12).

Verified bit-identical against node on ~1.7M samples (see the
eps_hypothesis port's gate) — do not "simplify" the float arithmetic.
"""

import math
import struct
from decimal import Decimal

# ---------------------------------------------------------------------------
# bit-exact V8 Math.{sin,cos,asin,atan,atan2} (fdlibm ports)
#
# Python's math module calls the platform libm, which differs from V8's
# fdlibm-derived implementations (src/base/ieee754.cc) in the last ulp on some
# inputs; those ulps reach the CSV through String(number). Transliterated from
# V8 12.9.202.28 (node 23) INCLUDING the FMA contraction clang applies on
# arm64 (-ffp-contract=on): every `a*b ± c` / `c ± a*b` in the C source is a
# fused multiply-add in the shipped binary (confirmed by disassembly of the
# node binary's __ZN2v84base7ieee754* symbols). Python 3.12 has no math.fma,
# so _fma() emulates a correctly rounded FMA (Boldo-Melquiond round-to-odd).
# ---------------------------------------------------------------------------

_D = struct.Struct(">d")
_Q = struct.Struct(">Q")
_QS = struct.Struct(">q")
_SPLIT = 134217729.0  # 2^27 + 1 (Veltkamp)
_INF = math.inf
_nextafter = math.nextafter


def _fma(a, b, c):
    """Correctly rounded a*b + c (round-to-nearest-even), pure float ops:
    TwoProd (Dekker/Veltkamp) + TwoSum + round-to-odd correction (Boldo &
    Melquiond, IEEE TC 2008). Valid away from overflow/underflow of the
    intermediate splits, which holds for every call site here. Verified
    against exact rational arithmetic on 200k random triples."""
    # p + e = a*b exactly
    p = a * b
    t = _SPLIT * a
    ah = t - (t - a)
    al = a - ah
    t = _SPLIT * b
    bh = t - (t - b)
    bl = b - bh
    e = ((ah * bh - p) + ah * bl + al * bh) + al * bl
    # sh + sl = c + p exactly
    sh = c + p
    t = sh - p
    sl = (c - t) + (p - (sh - t))
    # v + w = e + sl exactly
    v = e + sl
    t = v - sl
    w = (e - t) + (sl - (v - t))
    # round v to odd in the direction of the residue w
    if w != 0.0 and v == v:
        if not (_QS.unpack(_D.pack(v))[0] & 1):
            v = _nextafter(v, _INF if w > 0.0 else -_INF)
    return sh + v


def _hi(x):
    """High 32 bits of the double x (unsigned)."""
    return _Q.unpack(_D.pack(x))[0] >> 32


def _hi_s(x):
    """High word as a signed int32 (C's GET_HIGH_WORD into int32_t)."""
    h = _Q.unpack(_D.pack(x))[0] >> 32
    return h - 0x100000000 if h >= 0x80000000 else h


def _lo(x):
    """Low 32 bits of the double x (unsigned)."""
    return _Q.unpack(_D.pack(x))[0] & 0xFFFFFFFF


def _fw(hi, lo):
    """Double from (high word, low word)."""
    return _D.unpack(_Q.pack(((hi & 0xFFFFFFFF) << 32) | (lo & 0xFFFFFFFF)))[0]


# __kernel_sin / __kernel_cos coefficients
_S1 = _fw(0xBFC55555, 0x55555549)
_S2 = _fw(0x3F811111, 0x1110F8A6)
_S3 = _fw(0xBF2A01A0, 0x19C161D5)
_S4 = _fw(0x3EC71DE3, 0x57B1FE7D)
_S5 = _fw(0xBE5AE5E6, 0x8A2B9CEB)
_S6 = _fw(0x3DE5D93A, 0x5ACFD57C)
_C1 = _fw(0x3FA55555, 0x5555554C)
_C2 = _fw(0xBF56C16C, 0x16C15177)
_C3 = _fw(0x3EFA01A0, 0x19CB1590)
_C4 = _fw(0xBE927E4F, 0x809C52AD)
_C5 = _fw(0x3E21EE9E, 0xBDB4B1C4)
_C6 = _fw(0xBDA8FAE9, 0xBE8838D4)

# __ieee754_rem_pio2 constants (fast + medium paths; the huge-argument
# __kernel_rem_pio2 path is never reached by |x| <= 2^19*(pi/2) and raises)
_INVPIO2 = _fw(0x3FE45F30, 0x6DC9C883)
_PIO2_1 = _fw(0x3FF921FB, 0x54400000)
_PIO2_1T = _fw(0x3DD0B461, 0x1A626331)
_PIO2_2 = _fw(0x3DD0B461, 0x1A600000)
_PIO2_2T = _fw(0x3BA3198A, 0x2E037073)
_PIO2_3 = _fw(0x3BA3198A, 0x2E000000)
_PIO2_3T = _fw(0x397B839A, 0x252049C1)
_NPIO2_HW = [
    0x3FF921FB, 0x400921FB, 0x4012D97C, 0x401921FB, 0x401F6A7A, 0x4022D97C,
    0x4025FDBB, 0x402921FB, 0x402C463A, 0x402F6A7A, 0x4031475C, 0x4032D97C,
    0x40346B9C, 0x4035FDBB, 0x40378FDB, 0x403921FB, 0x403AB41B, 0x403C463A,
    0x403DD85A, 0x403F6A7A, 0x40407E4C, 0x4041475C, 0x4042106C, 0x4042D97C,
    0x4043A28C, 0x40446B9C, 0x404534AC, 0x4045FDBB, 0x4046C6CB, 0x40478FDB,
    0x404858EB, 0x404921FB,
]

# atan tables
_ATANHI = [_fw(0x3FDDAC67, 0x0561BB4F), _fw(0x3FE921FB, 0x54442D18),
           _fw(0x3FEF730B, 0xD281F69B), _fw(0x3FF921FB, 0x54442D18)]
_ATANLO = [_fw(0x3C7A2B7F, 0x222F65E2), _fw(0x3C81A626, 0x33145C07),
           _fw(0x3C700788, 0x7AF0CBBD), _fw(0x3C91A626, 0x33145C07)]
_AT = [_fw(0x3FD55555, 0x5555550D), _fw(0xBFC99999, 0x9998EBC4),
       _fw(0x3FC24924, 0x920083FF), _fw(0xBFBC71C6, 0xFE231671),
       _fw(0x3FB745CD, 0xC54C206E), _fw(0xBFB3B0F2, 0xAF749A6D),
       _fw(0x3FB10D66, 0xA0D03D51), _fw(0xBFADDE2D, 0x52DEFD9A),
       _fw(0x3FA97B4B, 0x24760DEB), _fw(0xBFA2B444, 0x2C6A6C2F),
       _fw(0x3F90AD3A, 0xE322DA11)]

# atan2 / asin constants
_PI_O_4 = _fw(0x3FE921FB, 0x54442D18)
_PI_O_2 = _fw(0x3FF921FB, 0x54442D18)
_PI = _fw(0x400921FB, 0x54442D18)
_PI_LO = _fw(0x3CA1A626, 0x33145C07)
_TINY = 1.0e-300
_PIO2_HI = _fw(0x3FF921FB, 0x54442D18)
_PIO2_LO = _fw(0x3C91A626, 0x33145C07)
_PIO4_HI = _fw(0x3FE921FB, 0x54442D18)
_PS0 = _fw(0x3FC55555, 0x55555555)
_PS1 = _fw(0xBFD4D612, 0x03EB6F7D)
_PS2 = _fw(0x3FC9C155, 0x0E884455)
_PS3 = _fw(0xBFA48228, 0xB5688F3B)
_PS4 = _fw(0x3F49EFE0, 0x7501B288)
_PS5 = _fw(0x3F023DE1, 0x0DFDF709)
_QS1 = _fw(0xC0033A27, 0x1C8A2D4B)
_QS2 = _fw(0x40002AE5, 0x9C598AC8)
_QS3 = _fw(0xBFE6066C, 0x1B8D0159)
_QS4 = _fw(0x3FB3B8C5, 0xB12E9282)


def _ksin(x, y, iy):
    ix = _hi(x) & 0x7FFFFFFF
    if ix < 0x3E400000:  # |x| < 2**-27
        return x
    z = x * x
    v = z * x
    # r = S2+z*(S3+z*(S4+z*(S5+z*S6)))  (every add contracted)
    r = _fma(z, _fma(z, _fma(z, _fma(z, _S6, _S5), _S4), _S3), _S2)
    if iy == 0:
        # x + v*(S1+z*r)
        return _fma(v, _fma(z, r, _S1), x)
    # x - ((z*(half*y - v*r) - y) - v*S1)
    return x - _fma(-v, _S1, _fma(z, _fma(0.5, y, -(v * r)), -y))


def _kcos(x, y):
    ix = _hi(x) & 0x7FFFFFFF
    if ix < 0x3E400000:  # |x| < 2**-27
        return 1.0
    z = x * x
    # r = z*(C1+z*(C2+z*(C3+z*(C4+z*(C5+z*C6)))))
    r = z * _fma(z, _fma(z, _fma(z, _fma(z, _fma(z, _C6, _C5), _C4), _C3), _C2), _C1)
    if ix < 0x3FD33333:  # |x| < 0.3
        # one - (0.5*z - (z*r - x*y))
        return 1.0 - _fma(0.5, z, -_fma(z, r, -(x * y)))
    if ix > 0x3FE90000:  # x > 0.78125
        qx = 0.28125
    else:
        qx = _fw(ix - 0x00200000, 0)  # x/4
    iz = _fma(0.5, z, -qx)  # 0.5*z - qx
    a = 1.0 - qx
    # a - (iz - (z*r - x*y))
    return a - (iz - _fma(z, r, -(x * y)))


def _rem_pio2(x):
    """Returns (n, y0, y1): x rem pi/2 in y0+y1 (fast + medium paths)."""
    hx = _hi_s(x)
    ix = hx & 0x7FFFFFFF
    if ix <= 0x3FE921FB:  # |x| ~<= pi/4
        return 0, x, 0.0
    if ix < 0x4002D97C:  # |x| < 3pi/4, special case with n=+-1
        if hx > 0:
            z = x - _PIO2_1
            if ix != 0x3FF921FB:  # 33+53 bit pi is good enough
                y0 = z - _PIO2_1T
                y1 = (z - y0) - _PIO2_1T
            else:  # near pi/2, use 33+33+53 bit pi
                z -= _PIO2_2
                y0 = z - _PIO2_2T
                y1 = (z - y0) - _PIO2_2T
            return 1, y0, y1
        z = x + _PIO2_1
        if ix != 0x3FF921FB:
            y0 = z + _PIO2_1T
            y1 = (z - y0) + _PIO2_1T
        else:
            z += _PIO2_2
            y0 = z + _PIO2_2T
            y1 = (z - y0) + _PIO2_2T
        return -1, y0, y1
    if ix <= 0x413921FB:  # |x| ~<= 2^19*(pi/2), medium size
        t = abs(x)
        n = int(_fma(t, _INVPIO2, 0.5))  # (int32_t)(t*invpio2+half)
        fn = float(n)
        r = _fma(-fn, _PIO2_1, t)  # t - fn*pio2_1
        w = fn * _PIO2_1T  # 1st round good to 85 bit
        if n < 32 and ix != _NPIO2_HW[n - 1]:
            y0 = r - w  # quick check no cancellation
        else:
            j = ix >> 20
            y0 = r - w
            i = j - ((_hi(y0) >> 20) & 0x7FF)
            if i > 16:  # 2nd iteration needed, good to 118
                t2 = r
                w = fn * _PIO2_2
                r = t2 - w
                w = _fma(fn, _PIO2_2T, -((t2 - r) - w))
                y0 = r - w
                i = j - ((_hi(y0) >> 20) & 0x7FF)
                if i > 49:  # 3rd iteration need, 151 bits acc
                    t3 = r
                    w = fn * _PIO2_3
                    r = t3 - w
                    w = _fma(fn, _PIO2_3T, -((t3 - r) - w))
                    y0 = r - w
        y1 = (r - y0) - w
        if hx < 0:
            return -n, -y0, -y1
        return n, y0, y1
    if ix >= 0x7FF00000:  # inf or NaN
        v = x - x
        return 0, v, v
    raise ValueError("_rem_pio2: argument too large for the ported reduction")


def _js_sin(x):
    ix = _hi(x) & 0x7FFFFFFF
    if ix <= 0x3FE921FB:  # |x| ~< pi/4
        return _ksin(x, 0.0, 0)
    if ix >= 0x7FF00000:  # sin(Inf or NaN) is NaN
        return x - x
    n, y0, y1 = _rem_pio2(x)
    n &= 3
    if n == 0:
        return _ksin(y0, y1, 1)
    if n == 1:
        return _kcos(y0, y1)
    if n == 2:
        return -_ksin(y0, y1, 1)
    return -_kcos(y0, y1)


def _js_cos(x):
    ix = _hi(x) & 0x7FFFFFFF
    if ix <= 0x3FE921FB:  # |x| ~< pi/4
        return _kcos(x, 0.0)
    if ix >= 0x7FF00000:  # cos(Inf or NaN) is NaN
        return x - x
    n, y0, y1 = _rem_pio2(x)
    n &= 3
    if n == 0:
        return _kcos(y0, y1)
    if n == 1:
        return -_ksin(y0, y1, 1)
    if n == 2:
        return -_kcos(y0, y1)
    return _ksin(y0, y1, 1)


def _js_asin(x):
    hx = _hi_s(x)
    ix = hx & 0x7FFFFFFF
    if ix >= 0x3FF00000:  # |x| >= 1
        if ((ix - 0x3FF00000) | _lo(x)) == 0:  # asin(1) = +-pi/2
            return _fma(x, _PIO2_HI, x * _PIO2_LO)  # x*pio2_hi + x*pio2_lo
        return float("nan")  # asin(|x|>1) is NaN
    if ix < 0x3FE00000:  # |x| < 0.5
        if ix < 0x3E400000:  # |x| < 2**-27
            return x
        t = x * x
        # p = t*(pS0+t*(pS1+t*(pS2+t*(pS3+t*(pS4+t*pS5)))))
        p = t * _fma(t, _fma(t, _fma(t, _fma(t, _fma(t, _PS5, _PS4), _PS3), _PS2), _PS1), _PS0)
        # q = one+t*(qS1+t*(qS2+t*(qS3+t*qS4)))
        q = _fma(t, _fma(t, _fma(t, _fma(t, _QS4, _QS3), _QS2), _QS1), 1.0)
        w = p / q
        return _fma(x, w, x)  # x + x*w
    # 1 > |x| >= 0.5
    w = 1.0 - abs(x)
    t = w * 0.5
    p = t * _fma(t, _fma(t, _fma(t, _fma(t, _fma(t, _PS5, _PS4), _PS3), _PS2), _PS1), _PS0)
    q = _fma(t, _fma(t, _fma(t, _fma(t, _QS4, _QS3), _QS2), _QS1), 1.0)
    s = math.sqrt(t)
    if ix >= 0x3FEF3333:  # |x| > 0.975
        w = p / q
        # t = pio2_hi - (2.0*(s+s*w) - pio2_lo)
        t = _PIO2_HI - _fma(2.0, _fma(s, w, s), -_PIO2_LO)
    else:
        w = _fw(_hi(s), 0)  # SET_LOW_WORD(w, 0) on w = s
        c = _fma(-w, w, t) / (s + w)  # (t - w*w)/(s+w)
        r = p / q
        # p = 2.0*s*r - (pio2_lo - 2.0*c)
        p = _fma(2.0 * s, r, -_fma(-2.0, c, _PIO2_LO))
        q = _fma(-2.0, w, _PIO4_HI)  # pio4_hi - 2.0*w
        t = _PIO4_HI - (p - q)
    return t if hx > 0 else -t


def _js_atan(x):
    hx = _hi_s(x)
    ix = hx & 0x7FFFFFFF
    if ix >= 0x44100000:  # |x| >= 2^66
        if ix > 0x7FF00000 or (ix == 0x7FF00000 and _lo(x) != 0):
            return x + x  # NaN
        if hx > 0:
            return _ATANHI[3] + _ATANLO[3]
        return -_ATANHI[3] - _ATANLO[3]
    if ix < 0x3FDC0000:  # |x| < 0.4375
        if ix < 0x3E400000:  # |x| < 2^-27
            return x
        id_ = -1
    else:
        x = abs(x)
        if ix < 0x3FF30000:  # |x| < 1.1875
            if ix < 0x3FE60000:  # 7/16 <= |x| < 11/16
                id_ = 0
                x = _fma(2.0, x, -1.0) / (2.0 + x)  # (2.0*x - one)/(2.0+x)
            else:  # 11/16 <= |x| < 19/16
                id_ = 1
                x = (x - 1.0) / (x + 1.0)
        else:
            if ix < 0x40038000:  # |x| < 2.4375
                id_ = 2
                x = (x - 1.5) / _fma(1.5, x, 1.0)  # (x - 1.5)/(one + 1.5*x)
            else:  # 2.4375 <= |x| < 2^66
                id_ = 3
                x = -1.0 / x
    z = x * x
    w = z * z
    # s1 = z*(aT0+w*(aT2+w*(aT4+w*(aT6+w*(aT8+w*aT10)))))
    s1 = z * _fma(w, _fma(w, _fma(w, _fma(w, _fma(w, _AT[10], _AT[8]), _AT[6]), _AT[4]), _AT[2]), _AT[0])
    # s2 = w*(aT1+w*(aT3+w*(aT5+w*(aT7+w*aT9))))
    s2 = w * _fma(w, _fma(w, _fma(w, _fma(w, _AT[9], _AT[7]), _AT[5]), _AT[3]), _AT[1])
    if id_ < 0:
        return _fma(-x, s1 + s2, x)  # x - x*(s1+s2)
    # z = atanhi[id] - ((x*(s1+s2) - atanlo[id]) - x)
    z = _ATANHI[id_] - (_fma(x, s1 + s2, -_ATANLO[id_]) - x)
    return -z if hx < 0 else z


def _js_atan2(y, x):
    hx = _hi_s(x)
    lx = _lo(x)
    ix = hx & 0x7FFFFFFF
    hy = _hi_s(y)
    ly = _lo(y)
    iy = hy & 0x7FFFFFFF
    if ((ix | ((lx | ((-lx) & 0xFFFFFFFF)) >> 31)) > 0x7FF00000 or
            (iy | ((ly | ((-ly) & 0xFFFFFFFF)) >> 31)) > 0x7FF00000):
        return x + y  # x or y is NaN
    if (((hx - 0x3FF00000) & 0xFFFFFFFF) | lx) == 0:
        return _js_atan(y)  # x = 1.0
    m = ((hy >> 31) & 1) | ((hx >> 30) & 2)  # 2*sign(x) + sign(y)
    if (iy | ly) == 0:  # y = 0
        if m in (0, 1):
            return y  # atan(+-0, +anything) = +-0
        if m == 2:
            return _PI + _TINY  # atan(+0, -anything) = pi
        return -_PI - _TINY  # atan(-0, -anything) = -pi
    if (ix | lx) == 0:  # x = 0
        return -_PI_O_2 - _TINY if hy < 0 else _PI_O_2 + _TINY
    if ix == 0x7FF00000:  # x is INF
        if iy == 0x7FF00000:
            if m == 0:
                return _PI_O_4 + _TINY
            if m == 1:
                return -_PI_O_4 - _TINY
            if m == 2:
                return _fma(3.0, _PI_O_4, _TINY)  # 3.0*pi_o_4 + tiny
            return -_fma(3.0, _PI_O_4, _TINY)
        if m == 0:
            return 0.0
        if m == 1:
            return -0.0
        if m == 2:
            return _PI + _TINY
        return -_PI - _TINY
    if iy == 0x7FF00000:  # y is INF
        return -_PI_O_2 - _TINY if hy < 0 else _PI_O_2 + _TINY
    k = (iy - ix) >> 20
    if k > 60:  # |y/x| > 2**60
        z = _fma(0.5, _PI_LO, _PI_O_2)  # pi_o_2 + 0.5*pi_lo
        m &= 1
    elif hx < 0 and k < -60:
        z = 0.0  # 0 > |y|/x > -2**-60
    else:
        z = _js_atan(abs(y / x))  # safe to do y/x
    if m == 0:
        return z  # atan(+, +)
    if m == 1:
        return -z  # atan(-, +)
    if m == 2:
        return _PI - (z - _PI_LO)  # atan(+, -)
    return (z - _PI_LO) - _PI  # atan(-, -)


# ---------------------------------------------------------------------------
# JS Number::ToString for the raw CSV cells (Array.join stringifies numbers
# at full precision; Python's repr uses a different exponent style outside
# [1e-4, 1e16), so reformat repr's shortest digits per ECMA-262 7.1.12.1).
# ---------------------------------------------------------------------------

def js_num(x):
    if isinstance(x, int) and not isinstance(x, bool):
        return str(x)
    if x != x:
        return "NaN"
    if x == math.inf:
        return "Infinity"
    if x == -math.inf:
        return "-Infinity"
    if x == 0:
        return "0"
    if float(x).is_integer() and abs(x) < 1e21:
        return str(int(x))  # String(1.0) === '1' (repr would keep the '.0')
    sign = "-" if x < 0 else ""
    t = Decimal(repr(abs(x))).as_tuple()
    digits = "".join(map(str, t.digits))
    k = len(digits)
    n = t.exponent + k  # value = 0.digits * 10^n
    if k <= n <= 21:
        s = digits + "0" * (n - k)
    elif 0 < n <= 21:
        s = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        s = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        s = (digits[0] + ("." + digits[1:] if k > 1 else "")
             + "e" + ("+" if e >= 0 else "-") + str(abs(e)))
    return sign + s
