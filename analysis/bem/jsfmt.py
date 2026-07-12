"""ECMAScript number formatting — byte-compatible output for the harness ports.

The retired .mjs harnesses wrote CSVs/reports through JS's Number formatting;
the Python ports must reproduce those bytes exactly. Both languages hold the
same IEEE-754 doubles, so only the *decimal rendering* differs:

- ``to_fixed(x, d)`` — Number.prototype.toFixed: round the exact decimal value
  of the double to d places, ties AWAY from zero (sign extracted first). This
  differs from Python's format(), which rounds ties to even.
- ``js_str(x)`` — Number::toString for the values the harnesses emit raw:
  integer-valued doubles print without ``.0`` (String(150.0) === '150').
- ``to_exponential(x, d)`` — Number.prototype.toExponential: d+1 significant
  digits, exponent without zero-padding (1.77e-8, not 1.77e-08).
"""

import math
from decimal import ROUND_HALF_UP, Decimal


def to_fixed(x, d=0):
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


def js_str(x):
    if isinstance(x, int):
        return str(x)
    if x != x:
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return "0"
    if float(x).is_integer() and abs(x) < 1e21:
        return str(int(x))
    return repr(x)  # shortest round-trip, same digits as V8 in the normal range


def to_exponential(x, d):
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
