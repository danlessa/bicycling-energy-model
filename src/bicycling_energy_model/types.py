"""Typed parameter records and shared type aliases for the package.

The dataclass field names deliberately mirror the JS keys of the applet
(`m, Crr, CdA, ...`, `climbThr`, `kSmooth`) rather than snake_case — the
package is a line-by-line port and the 1:1 name correspondence is part of
what keeps the two implementations reviewable side by side.

Every engine function accepts either an instance or a plain mapping with the
same keys (coerced at the boundary via `.of()`), so the harnesses'
verbatim-port dicts keep working unchanged while the dataclasses are the
canonical, documented API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, TypedDict, Union

# The coasting deficit ε₀ (journal Entry 8; named in Entry 27): the share of a
# descent that pure coasting *would* refund but the rider does not collect —
# residual descent pedalling and pre-corner braking. Calibrated on 30 m descent
# cells; recurs at 0.12–0.133 across all three riders tested. Mirrored by hand
# in the applet and in sampasimu's energy-worker.js (the deliberate JS copies).
EPS0: float = 0.13


class Profile(TypedDict):
    """An elevation profile: cumulative ground distance + elevation, metres.
    Deliberately a TypedDict, not a dataclass — profiles are homogeneous
    array containers built and consumed as plain dicts everywhere."""
    x: list[float]
    h: list[float]


class Point(TypedDict, total=False):
    """One track sample as produced by pts_from_fit / pts_from_gpx."""
    x: float            # cumulative ground distance, m
    alt: float          # elevation, m (may be absent/None mid-stream)
    power: float | None
    cad: float | None   # cadence, rpm (None when the file carries none)
    t: float | None     # epoch seconds
    v: float | None     # speed, m/s
    dt: float           # sample weight, s (finish_pts)
    lat: float          # only in geo-keeping builders (pts_with_geo)
    lon: float


Points = list[Point]


def _of(cls: type, obj: Any, none_ok: bool = False) -> Any:
    """Boundary coercion: accept an instance, a mapping with the same keys
    (extras ignored — harness dicts sometimes carry more), or None where a
    fully-defaulted options class allows it."""
    if isinstance(obj, cls):
        return obj
    if obj is None:
        if none_ok:
            return cls()
        raise TypeError(f"{cls.__name__} required, got None")
    return cls(**{k: obj[k] for k in cls.__dataclass_fields__ if k in obj})


@dataclass(frozen=True)
class SimParams:
    """Rider + physics constants (the JS `p`). vmax/vstart are only needed by
    the dynamic models (canonical, approx_time) and may be omitted elsewhere."""
    m: float
    Crr: float
    CdA: float
    rho: float
    keff: float
    wind: float = 0.0
    vmax: float | None = None
    vstart: float | None = None

    @classmethod
    def of(cls, obj: Union["SimParams", Mapping[str, float]]) -> "SimParams":
        return _of(cls, obj)


@dataclass(frozen=True)
class RegimePowers:
    """Per-regime pedal powers + the grade thresholds that pick the regime."""
    climb: float
    flat: float
    descent: float
    climbThr: float
    descThr: float

    @classmethod
    def of(cls, obj: Union["RegimePowers", Mapping[str, float]]) -> "RegimePowers":
        return _of(cls, obj)


@dataclass(frozen=True)
class V2Options:
    """v2_edge knobs (defaults = the deployed constants)."""
    kSmooth: float = 1.0
    epsOffset: float = EPS0
    climbThr: float = 0.02

    @classmethod
    def of(cls, obj: Union["V2Options", Mapping[str, float], None]) -> "V2Options":
        return _of(cls, obj, none_ok=True)


@dataclass(frozen=True)
class ApproxOptions:
    """approximate() options; None fields fall back to the JS defaults."""
    climbAeroMode: str = "off"
    climbThr: float = 0.02
    descThr: float = -0.015
    climbPower: float = 0.0

    @classmethod
    def of(cls, obj: Union["ApproxOptions", Mapping[str, Any], None]) -> "ApproxOptions":
        return _of(cls, obj, none_ok=True)


# Entry 21's behavioural trio: (k_smooth, ε₀, climbThr) re-fitted purely as a
# 5 m → 30 m resolution transfer, for walking RAW ~5 m profiles with v2_edge.
# Bridges the resolution gap per-ride on the rider corpora, NOT on flat-urban
# censo — a function of (Δx, terrain regime), not Δx alone. The applet's
# "trio Δx=5 m" preset mirrors these values by hand.
TRIO_DX5 = V2Options(kSmooth=0.9375, epsOffset=0.0632, climbThr=0.025)
