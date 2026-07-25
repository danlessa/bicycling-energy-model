"""Track -> profile assembly: haversine, buildProfile, GPX points.

Ports of the app's haversine/buildProfile (physics part — the canvas
downsampling is UI-only and not ported) and compare.mjs's ptsFromGPX.
"""

import math
import re


def haversine(a, b):
    R = 6371000
    to_r = math.pi / 180
    d_lat = (b["lat"] - a["lat"]) * to_r
    d_lon = (b["lon"] - a["lon"]) * to_r
    s = (math.sin(d_lat / 2) ** 2
         + math.cos(a["lat"] * to_r) * math.cos(b["lat"] * to_r) * math.sin(d_lon / 2) ** 2)
    return 2 * R * math.asin(min(1.0, math.sqrt(s)))


def build_profile(dist_arr, ele_arr):
    """Cumulative distance + raw elevation (NaN/None allowed) -> NATIVE-
    resolution physics profile {x, h} plus info (JS buildProfile, minus the
    canvas H[240] downsampling). Near-duplicate points (delta < 0.5 m) are
    dropped so no segment has dx = 0; elevation gaps are edge-filled and
    linearly interpolated; h is shifted to min 0."""
    X = [dist_arr[0]]
    E = [ele_arr[0]]
    n_in = len(dist_arr)
    for i in range(1, n_in):
        close = dist_arr[i] - X[-1] < 0.5
        if close and i < n_in - 1:
            continue
        if close:  # last point: replace, never create dx ~ 0
            X[-1] = dist_arr[i]
            E[-1] = ele_arr[i]
        else:
            X.append(dist_arr[i])
            E.append(ele_arr[i])
    base = X[0]
    for i in range(len(X)):
        X[i] -= base
    n = len(X)
    total = X[n - 1]
    if n < 2 or not total > 0:
        raise ValueError("distância nula")

    def finite(e):
        return e is not None and isinstance(e, (int, float)) and math.isfinite(e)

    first = next((i for i, e in enumerate(E) if finite(e)), -1)
    if first < 0:
        raise ValueError("faixa sem elevação")
    for i in range(first):
        E[i] = E[first]
    last = first
    for i in range(first + 1, n):
        if finite(E[i]):
            for k in range(last + 1, i):
                E[k] = E[last] + (E[i] - E[last]) * (k - last) / (i - last)
            last = i
    for i in range(last + 1, n):
        E[i] = E[last]
    min_e = min(E)
    max_e = max(E)
    h = [e - min_e for e in E]
    return {"x": X, "h": h, "total": total, "range": max_e - min_e, "n": n}


_TRKPT = re.compile(r'<trkpt\b([^>]*)>([\s\S]*?)</trkpt>')
_LAT = re.compile(r'lat="([-\d.]+)"')
_LON = re.compile(r'lon="([-\d.]+)"')
_ELE = re.compile(r'<ele>\s*([-\d.]+)')
_TIME = re.compile(r'<time>\s*([^<]+)')
_POWER = re.compile(r'<(?:\w+:)?power>\s*([\d.]+)')


def pts_from_gpx(text):
    """GPX text -> point list (compare.mjs ptsFromGPX: regex, attr order-
    agnostic). Cumulative x by haversine; alt may be NaN (filled later by
    build_profile). Times parsed as epoch seconds when ISO-8601."""
    from datetime import datetime

    out = []
    for m in _TRKPT.finditer(text):
        attrs, body = m.group(1), m.group(2)
        la, lo = _LAT.search(attrs), _LON.search(attrs)
        if not la or not lo:
            continue
        ele = _ELE.search(body)
        tm = _TIME.search(body)
        pw = _POWER.search(body)
        t = None
        if tm:
            try:
                t = datetime.fromisoformat(tm.group(1).strip().replace("Z", "+00:00")).timestamp()
            except ValueError:
                t = None
        out.append({
            "lat": float(la.group(1)), "lon": float(lo.group(1)),
            "alt": float(ele.group(1)) if ele else float("nan"),
            "t": t, "power": float(pw.group(1)) if pw else None, "v": None,
        })
    if len(out) < 2:
        raise ValueError("GPX com poucos pontos")
    pts = [{"x": 0.0, "alt": out[0]["alt"], "power": out[0]["power"],
            "t": out[0]["t"], "v": None}]
    cum = 0.0
    for i in range(1, len(out)):
        cum += haversine(out[i - 1], out[i])
        pts.append({"x": cum, "alt": out[i]["alt"], "power": out[i]["power"],
                    "t": out[i]["t"], "v": None})
    from .fit import finish_pts
    finish_pts(pts)
    return pts
