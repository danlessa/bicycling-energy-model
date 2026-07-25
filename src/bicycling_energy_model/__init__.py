"""bicycling_energy_model — pure-Python port of the research workflow.

Every function is a line-by-line transliteration of the JavaScript reference
(the app `applet/index.html`), kept in the SAME evaluation order so results
agree to float64 round-off. Since the JS->Python harness migration this
package IS the implementation the harnesses run on — `src/harness/*.py`
import from here rather than carrying copies. The cross-language JS parity
harness that machine-checked the port (8 514 comparisons within 1e-9
relative) was retired after proving it; git history keeps it.

Stdlib-only by design: no numpy, no dependencies — reviewable line by line.
"""

from .engines import (
    G,
    approx_components,
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
from .regime import (climb_balance, eps_from_balance, extract_regime_powers,
                     measured_flat_speed, push_stats)
from .ride import analyze_ride, load_pts
from .util import is_finite, jsdiv

__all__ = [
    "G", "flat_eq_speed", "resample_profile", "smooth_elevation", "deadband",
    "ascent_hyst", "canonical", "approximate", "v2_edge", "approx_time",
    "eps_geom", "parse_fit", "pts_from_fit", "finish_pts", "empirical_kj",
    "overall_mean_power", "haversine", "build_profile", "pts_from_gpx",
    "extract_regime_powers", "eps_from_balance", "measured_flat_speed",
    "analyze_ride", "load_pts",
    "approx_components", "climb_balance", "push_stats", "is_finite", "jsdiv",
]
