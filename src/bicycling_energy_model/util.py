"""Small shared helpers the harnesses used to carry as per-file copies."""

import math


def is_finite(x):
    """None-tolerant finiteness check (the JS `Number.isFinite` idiom the
    harnesses inherited: None/NaN/±inf are all 'not a usable number').
    Excludes bools — `isinstance(True, int)` is True in Python, and the JS
    original would reject a boolean."""
    return (x is not None and isinstance(x, (int, float))
            and not isinstance(x, bool) and math.isfinite(x))


def jsdiv(a, b):
    """a / b with ECMAScript division semantics: x/0 -> ±Infinity, 0/0 -> NaN
    (Python raises ZeroDivisionError instead).

    NOT retirable in favour of plain `/`: several call sites divide by
    quantities that are legitimately zero on degenerate inputs (a singular
    normal-equation determinant, a zero-variance correlation denominator, an
    empty-set mean), and the downstream medians/filters rely on getting an
    inf/nan they can drop rather than an exception. One copy, used by all.
    """
    if b != 0:
        return a / b
    if a == 0 or a != a:
        return float("nan")
    neg = (a < 0) != (math.copysign(1.0, b) < 0)
    return float("-inf") if neg else float("inf")
