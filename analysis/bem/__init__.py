"""bem — pure-Python port of the bicycling-energy-model research workflow.

Every function is a line-by-line transliteration of the JavaScript reference
(the app `applet/index.html`, and the frozen verbatim JS of the retired
harness engines in `analysis/parity/reference.mjs`), kept in the SAME
evaluation order so results agree to float64 round-off. Since the JS->Python
harness migration this package IS the implementation the harnesses run on —
`harness/*.py` import from here rather than carrying copies. The cross-language parity harness (`analysis/parity/`) machine-
checks that agreement; run it after touching either side.

Stdlib-only by design: no numpy, no dependencies — reviewable line by line.
"""

from .engines import (
    G,
    flat_eq_speed,
    resample_profile,
    smooth_elevation,
    deadband,
    ascent_hyst,
    canonical,
    approximate,
    v2_edge,
    approx_time,
    eps_geom,
)
from .fit import parse_fit, pts_from_fit, finish_pts, empirical_kj, overall_mean_power
from .profiles import haversine, build_profile, pts_from_gpx
from .regime import extract_regime_powers, eps_from_balance, measured_flat_speed
from .ride import analyze_ride, load_pts

__all__ = [
    "G", "flat_eq_speed", "resample_profile", "smooth_elevation", "deadband",
    "ascent_hyst", "canonical", "approximate", "v2_edge", "approx_time",
    "eps_geom", "parse_fit", "pts_from_fit", "finish_pts", "empirical_kj",
    "overall_mean_power", "haversine", "build_profile", "pts_from_gpx",
    "extract_regime_powers", "eps_from_balance", "measured_flat_speed",
    "analyze_ride", "load_pts",
]
