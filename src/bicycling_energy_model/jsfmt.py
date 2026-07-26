"""Number formatting for the harness reports and CSVs (stdlib `decimal`).

The rendering conventions come from ECMAScript because the published tables
were first produced that way, and they are *kept* — not for byte-compat with
the retired .mjs harnesses (that requirement was dropped with V8-exactness),
but because they are the conventions the published numbers were rounded
under, and silently switching rounding rules could flip a printed digit:

- ``to_fixed(x, d)`` — round the exact decimal value of the double to d
  places, ties AWAY from zero (JS toFixed). Python's format()/round() round
  ties to even — e.g. format(2.5, '.0f') is '2', to_fixed(2.5) is '3'.
- ``js_str(x)`` — shortest round-trip rendering with JS's layout rules:
  integer-valued doubles print without ``.0``, plain decimal notation down to
  1e-6 ('0.00001', not '1e-05'), exponents unpadded ('1e-7', not '1e-07').
  The digits themselves equal repr()'s (shortest round-trip is unique); only
  the layout differs.
- ``to_exponential(x, d)`` — d+1 significant digits, exponent unpadded
  (1.77e-8, not 1.77e-08).
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal


def to_fixed(x: float, d: int = 0) -> str:
    if x != x:
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        x = 0.0  # JS: (-0).toFixed(d) has no sign (−0 < 0 is false)
    if abs(x) >= 1e21:
        return js_str(x)
    q = Decimal(x).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    return f"{q:f}"


def js_str(x: float) -> str:
    """ECMA-262 Number::toString(10) on top of repr()'s shortest digits."""
    if isinstance(x, int):
        return str(x)
    x = float(x)
    if x != x:
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return "0"  # including -0.0
    sign = "-" if x < 0 else ""
    t = Decimal(repr(abs(x))).as_tuple()
    digits = "".join(map(str, t.digits)).rstrip("0") or "0"
    k = len(digits)
    n = t.exponent + len(t.digits)  # value = 0.digits × 10^n
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        mant = digits[0] + ("." + digits[1:] if k > 1 else "")
        body = f"{mant}e{'+' if e >= 0 else '-'}{abs(e)}"
    return sign + body


def to_exponential(x: float, d: int) -> str:
    if x != x:
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return ("0." + "0" * d if d else "0") + "e+0"
    sign = "-" if x < 0 else ""
    dx = Decimal(abs(x))
    e = dx.adjusted()
    m = dx.scaleb(-e).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    if m >= 10:
        m = (m / 10).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
        e += 1
    return f"{sign}{m}e{'+' if e >= 0 else '-'}{abs(e)}"
