#!/usr/bin/env python3
"""fig12-routes-map.png — every analysed ride drawn on one map.

PRIVACY: this figure derives from raw GPS of the author AND the two
independent riders (exports shared with consent, never published as
tracks). Mitigations baked in: the first and last TRIM_M metres of every
ride are dropped (endpoint privacy zones), lines are rendered thin and
translucent at metropolitan scale, and there is no street basemap — the
only geography visible is what thousands of overlapping rides trace out.
The output PNG is NOT committed unless Danilo explicitly approves it.

Ride selection: the parse-cache index (data/results/cache) lists every
file the harnesses actually parsed — a slight superset of the clean
corpora; each cached name is matched back to its corpus directory.

Run:  python3 research/article/figs/make_map.py   (few minutes: parses
      ~1.5k FIT files for lat/lon, which the points cache does not keep)
"""

from __future__ import annotations

import gzip
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from bicycling_energy_model import parse_fit, haversine  # noqa: E402

ACT = os.path.join(ROOT, 'data', 'inputs', 'activities')
CACHE = os.path.join(ROOT, 'data', 'results', 'cache')

BLUE, VERM, GREEN, GREY = '#0072B2', '#D55E00', '#009E73', '#9aa0a6'
TRIM_M = 1500.0          # endpoint privacy zone
STEP_M = 60.0            # min spacing between kept points
GAP_M = 2000.0           # split line on GPS gaps larger than this
BOX = (-25.5, -21.5, -49.0, -44.0)   # lat_min, lat_max, lon_min, lon_max (SP region)

CORPORA = [   # (label, directory, colour, alpha, linewidth) — draw order
    ('D5 author-full', 'strava_danlessa', GREY, 0.16, 0.5),
    ('D3 P. Paz', 'strava_ppaz', VERM, 0.16, 0.5),
    ('D4 JAAM', 'strava_jaam', BLUE, 0.16, 0.5),
    ('D2 censo', os.path.join('censohidrografico', 'rwgps'), GREEN, 0.45, 0.7),
    ('D2 censo', os.path.join('censohidrografico', 'strava'), GREEN, 0.45, 0.7),
]


def cached_names() -> set[str]:
    """Original filenames the harnesses parsed, recovered from cache keys."""
    names = set()
    for f in os.listdir(CACHE):
        if not f.endswith('.pkl') or not f.startswith('v1_'):
            continue
        core = f[len('v1_'):]                     # <hash>_<orig>.<size>.<mtime>.pkl
        core = core.split('_', 1)[1]
        names.add('.'.join(core.split('.')[:-3]))  # strip .<size>.<mtime>.pkl
    return names


def track(path: str) -> list[tuple[float, float]] | None:
    """Trimmed, downsampled (lat, lon) polyline for one ride; None if unusable."""
    raw = open(path, 'rb').read()
    if path.endswith('.gz'):
        raw = gzip.decompress(raw)
    try:
        recs = parse_fit(raw)
    except Exception:
        return None
    g = [r for r in recs if r.get('lat') is not None and r.get('lon') is not None]
    if len(g) < 100:
        return None
    # cumulative distance for the trim zones
    cum = [0.0]
    for i in range(1, len(g)):
        cum.append(cum[-1] + haversine(g[i - 1], g[i]))
    total = cum[-1]
    if total < 2 * TRIM_M + 3000:                 # too short to survive trimming
        return None
    pts, last_keep = [], -1e9
    for i, r in enumerate(g):
        if cum[i] < TRIM_M or cum[i] > total - TRIM_M:
            continue
        if not (BOX[0] <= r['lat'] <= BOX[1] and BOX[2] <= r['lon'] <= BOX[3]):
            continue
        if cum[i] - last_keep < STEP_M:
            continue
        if pts and cum[i] - last_keep > GAP_M:
            pts.append((math.nan, math.nan))      # break the line on gaps
        pts.append((r['lat'], r['lon']))
        last_keep = cum[i]
    return pts if len(pts) >= 20 else None


def main() -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    analysed = cached_names()
    fig, ax = plt.subplots(figsize=(7.4, 7.0), dpi=240)
    counts: dict[str, int] = {}
    all_lat, all_lon = [], []

    for label, sub, colour, alpha, lw in CORPORA:
        d = os.path.join(ACT, sub)
        if not os.path.isdir(d):
            continue
        files = [f for f in sorted(os.listdir(d)) if f in analysed]
        done = 0
        for f in files:
            t = track(os.path.join(d, f))
            if not t:
                continue
            la = [p[0] for p in t]
            lo = [p[1] for p in t]
            ax.plot(lo, la, color=colour, alpha=alpha, lw=lw,
                    solid_capstyle='round', zorder=2)
            all_lat += [v for v in la if v == v]
            all_lon += [v for v in lo if v == v]
            counts[label] = counts.get(label, 0) + 1
            done += 1
            if done % 100 == 0:
                print(f'  {label}: {done}/{len(files)}', flush=True)
        print(f'{label} [{sub}]: drew {counts.get(label, 0)} rides '
              f'(of {len(files)} cached)', flush=True)

    # frame: central quantiles + padding, metric aspect
    all_lat.sort(); all_lon.sort()
    q = lambda v, p: v[int(p * (len(v) - 1))]
    la0, la1 = q(all_lat, 0.005), q(all_lat, 0.995)
    lo0, lo1 = q(all_lon, 0.005), q(all_lon, 0.995)
    pla, plo = 0.06 * (la1 - la0), 0.06 * (lo1 - lo0)
    ax.set_xlim(lo0 - plo, lo1 + plo)
    ax.set_ylim(la0 - pla, la1 + pla)
    midlat = (la0 + la1) / 2
    ax.set_aspect(1.0 / math.cos(math.radians(midlat)))
    ax.axis('off')

    # 10 km scale bar (bottom left)
    km10_deg = 10.0 / (111.32 * math.cos(math.radians(midlat)))
    x0 = lo0 - plo + 0.05 * (lo1 - lo0)
    y0 = la0 - pla + 0.04 * (la1 - la0)
    ax.plot([x0, x0 + km10_deg], [y0, y0], color='#222222', lw=2)
    ax.text(x0 + km10_deg / 2, y0 + 0.008 * (la1 - la0), '10 km',
            ha='center', va='bottom', fontsize=8, color='#222222')

    # legend with drawn counts
    from matplotlib.lines import Line2D
    order = ['D5 author-full', 'D3 P. Paz', 'D4 JAAM', 'D2 censo']
    colours = {'D5 author-full': GREY, 'D3 P. Paz': VERM,
               'D4 JAAM': BLUE, 'D2 censo': GREEN}
    handles = [Line2D([], [], color=colours[k], lw=2.4,
                      label=f'{k} · {counts.get(k, 0)} rides') for k in order]
    ax.legend(handles=handles, loc='upper right', fontsize=8, frameon=False)
    ax.text(0.0, -0.01, 'endpoints trimmed 1.5 km per ride · no basemap: '
            'the geography is the rides themselves',
            transform=ax.transAxes, fontsize=7, color=GREY, va='top')

    out = os.path.join(HERE, 'fig12-routes-map.png')
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    print('wrote', out)


if __name__ == '__main__':
    main()
