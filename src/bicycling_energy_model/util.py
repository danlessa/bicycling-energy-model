"""Small shared helpers the harnesses used to carry as per-file copies."""

import math
import os


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


def env_suffix(*names):
    """Build a filename suffix from whichever of `names` are set in the
    environment, e.g. env_suffix('PPAZ_M', 'PPAZ_CDA') with PPAZ_M=78 set
    returns '.PPAZ_M78'; '' if none are set. A `<RIDER>_M`/`_CDA`/`_CRR`
    sensitivity sweep must not silently overwrite the canonical CSV that
    downstream harnesses and bootstrap_ci's gates trust — this lets a harness
    route an active override to its own file instead."""
    parts = [f"{n}{os.environ[n]}".replace(".", "p").replace("-", "m")
             for n in names if os.environ.get(n)]
    return ("." + "_".join(parts)) if parts else ""
