#!/usr/bin/env python3
"""Conceptual (data-free) diagrams for the IMRAD paper (paper.md).

Unlike make_figures.py these plot no ride data — they are explanatory
drawings, regenerated here so no committed SVG is ever hand-edited.

  fig9-anatomy.svg           — the closed-form law mapped onto a route profile
  fig10-coasting-deficit.svg — eps_coast(s) geometry and the coasting deficit

Style matches make_figures.py: Okabe-Ito palette, system sans.
Run: python3 research/article/figs/make_diagrams.py
"""

from __future__ import annotations

import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BLUE, VERM, GREEN, GREY, INK = '#0072B2', '#D55E00', '#009E73', '#9aa0a6', '#222222'
FONT = 'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'


def txt(x: float, y: float, s: str, size: int = 12, anchor: str = 'middle',
        fill: str = INK, style: str = '') -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" {FONT} '
            f'font-size="{size}" fill="{fill}" {style}>{s}</text>')


def path(pts: list[tuple[float, float]], stroke: str, width: float = 2.0,
         dash: str = '', fill: str = 'none', opacity: float = 1.0) -> str:
    d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    dd = f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"'
            f'{dd} opacity="{opacity}" stroke-linejoin="round" stroke-linecap="round"/>')


def arrow(x1: float, y1: float, x2: float, y2: float, color: str,
          width: float = 1.6) -> str:
    """Straight arrow with a small head at (x2, y2)."""
    ang = math.atan2(y2 - y1, x2 - x1)
    a1 = ang + math.radians(153)
    a2 = ang - math.radians(153)
    h = 7
    return (f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{color}" '
            f'stroke-width="{width}" fill="none"/>'
            f'<path d="M{x2:.1f},{y2:.1f} L{x2 + h * math.cos(a1):.1f},'
            f'{y2 + h * math.sin(a1):.1f} M{x2:.1f},{y2:.1f} '
            f'L{x2 + h * math.cos(a2):.1f},{y2 + h * math.sin(a2):.1f}" '
            f'stroke="{color}" stroke-width="{width}" fill="none"/>')


# ---------------------------------------------------------------- fig 9
def fig9() -> None:
    W, H = 720, 400
    # profile geometry (x in [40, 680]; ground line y = 250)
    x0, x1, yg = 40.0, 680.0, 250.0

    # piecewise elevation: flat — climb — plateau — descent — flat
    knots = [(0.00, 0.0), (0.22, 0.0), (0.42, 90.0), (0.55, 90.0),
             (0.80, 20.0), (1.00, 20.0)]

    def elev(f: float) -> float:
        for (fa, ha), (fb, hb) in zip(knots, knots[1:]):
            if fa <= f <= fb:
                t = (f - fa) / (fb - fa) if fb > fa else 0.0
                return ha + t * (hb - ha)
        return knots[-1][1]

    def X(f: float) -> float:
        return x0 + f * (x1 - x0)

    def Y(h: float) -> float:
        return yg - h * 1.15

    prof = [(X(f / 200), Y(elev(f / 200))) for f in range(201)]

    b = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']

    # regime shading under the profile: climb (verm) and descent (green)
    for fa, fb, col in ((0.22, 0.42, VERM), (0.55, 0.80, GREEN)):
        seg = [(X(f / 200), Y(elev(f / 200)))
               for f in range(int(fa * 200), int(fb * 200) + 1)]
        poly = seg + [(X(fb), yg), (X(fa), yg)]
        d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in poly) + ' Z'
        b.append(f'<path d="{d}" fill="{col}" opacity="0.13" stroke="none"/>')

    b.append(path([(x0, yg), (x1, yg)], GREY, 1))          # ground line
    b.append(path(prof, INK, 2.2))                          # profile

    # term callouts
    b.append(arrow(X(0.04), yg + 14, X(0.19), yg + 14, BLUE))
    b.append(txt(X(0.11), yg + 32, 'rolling + aero', 12, 'middle', BLUE))
    b.append(txt(X(0.11), yg + 46, 'α·dx everywhere flat', 11, 'middle', BLUE))

    b.append(txt(X(0.30), Y(95) - 26, 'climb: pay full gravity', 12, 'middle', VERM))
    b.append(txt(X(0.30), Y(95) - 12, 'β·h₊ — aero gated off', 11, 'middle', VERM))
    b.append(arrow(X(0.335), Y(30), X(0.335), Y(78), VERM))

    b.append(arrow(X(0.645), Y(72), X(0.645), Y(32), GREEN))
    b.append(txt(X(0.675), yg + 32, 'descent: partial refund', 12, 'middle', GREEN))
    b.append(txt(X(0.675), yg + 46, 'credit ε·β·h₋, recovery ε ∈ [0,1]', 11, 'middle', GREEN))

    # deadband inset: jittery vs smoothed
    ix, iy, iw, ih = 480, 60, 190, 74
    b.append(f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="#fff" '
             f'stroke="{GREY}" stroke-width="1" rx="4"/>')
    jag = [(ix + 12 + i * (iw - 24) / 40,
            iy + 40 - 6 * math.sin(i / 2.1) - 5 * math.sin(i * 1.7))
           for i in range(41)]
    smo = [(ix + 12 + i * (iw - 24) / 40, iy + 40 - 6 * math.sin(i / 2.1))
           for i in range(41)]
    b.append(path(jag, GREY, 1.3))
    b.append(path(smo, INK, 1.8))
    b.append(txt(ix + iw / 2, iy + 14, 'sub-metre noise inflates h₊', 11))
    b.append(txt(ix + iw / 2, iy + ih - 6, 'deadband τ = 2 m keeps real climbs', 10, 'middle', GREY))

    # equation strip with color-matched terms
    ey = 348
    b.append(txt(W / 2, ey - 22, 'the whole model:', 11, 'middle', GREY))
    eq = (f'<tspan fill="{INK}">E&#160;&#8776;&#160;</tspan>'
          f'<tspan fill="{BLUE}">α_r·x&#160;+&#160;α_a·x_flat</tspan>'
          f'<tspan fill="{INK}">&#160;+&#160;</tspan>'
          f'<tspan fill="{VERM}">β·h₊</tspan>'
          f'<tspan fill="{INK}">&#160;−&#160;</tspan>'
          f'<tspan fill="{GREEN}">ε·β·h₋</tspan>')
    b.append(f'<text x="{W / 2}" y="{ey}" text-anchor="middle" {FONT} '
             f'font-size="19" font-weight="600">{eq}</text>')
    b.append(txt(W / 2, ey + 20,
                 'x = distance · h₊ = total ascent · h₋ = total descent · '
                 'α, β from six rider constants', 11, 'middle', GREY))

    b.append('</svg>')
    out = os.path.join(HERE, 'fig9-anatomy.svg')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(''.join(b))
    print('wrote fig9-anatomy.svg')


# ---------------------------------------------------------------- fig 10
def fig10() -> None:
    W, H = 640, 420
    L, R, T, B = 70, 24, 30, 64
    x0, x1 = L, W - R
    y0, y1 = T, H - B
    AB = 0.02          # flat-resistance grade alpha/beta
    EPS0 = 0.13
    smax = 0.12

    def X(s: float) -> float:
        return x0 + (s / smax) * (x1 - x0)

    def Y(e: float) -> float:
        return y1 - e * (y1 - y0) / 1.05

    def eps_coast(s: float) -> float:
        return min(1.0, AB / s) if s > 0 else 1.0

    b = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']

    # axes + gridlines
    for e in (0.0, 0.25, 0.5, 0.75, 1.0):
        b.append(path([(x0, Y(e)), (x1, Y(e))], '#eef0f2', 1))
        b.append(txt(x0 - 8, Y(e) + 4, f'{e:.2f}', 11, 'end', GREY))
    for s in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12):
        b.append(txt(X(s), y1 + 16, f'{s * 100:.0f}%', 11, 'middle', GREY))
    b.append(path([(x0, y0), (x0, y1), (x1, y1)], GREY, 1.2))
    b.append(txt((x0 + x1) / 2, H - 26, 'descent grade s', 12))
    b.append(f'<text x="16" y="{(y0 + y1) / 2:.0f}" text-anchor="middle" {FONT} '
             f'font-size="12" fill="{INK}" transform="rotate(-90 16 {(y0 + y1) / 2:.0f})">'
             f'recovered fraction ε</text>')

    # curves
    ss = [0.004 + i * (smax - 0.004) / 300 for i in range(301)]
    b.append(path([(X(s), Y(eps_coast(s))) for s in ss], BLUE, 2.4))
    b.append(path([(X(s), Y(max(0.0, eps_coast(s) - EPS0))) for s in ss],
                  VERM, 2.4, dash='7,4'))

    # flat-resistance grade marker
    b.append(path([(X(AB), y1), (X(AB), Y(1.0))], GREY, 1, dash='3,4'))
    b.append(txt(X(AB), y0 + 4, 'α/β: gravity = flat resistance', 11, 'middle', GREY))

    # the deficit arrow at s = 4%
    s_at = 0.04
    b.append(arrow(X(s_at), Y(eps_coast(s_at)), X(s_at), Y(eps_coast(s_at) - EPS0) - 3, INK))
    b.append(txt(X(s_at) + 12, Y(eps_coast(s_at) - EPS0) + 16,
                 'coasting deficit ε₀ = 0.13', 12, 'start'))
    b.append(txt(X(s_at) + 12, Y(eps_coast(s_at) - EPS0) + 32,
                 'pedalling into the descent (braking cancels out)', 11, 'start', GREY))

    # curve labels
    b.append(txt(X(0.045), Y(0.62), 'ideal coasting: ε = min(1, (α/β)/s)',
                 12, 'start', BLUE))
    b.append(txt(X(0.070), Y(max(0.0, eps_coast(0.070) - EPS0)) + 34,
                 'real riders: ε = ε_coast − ε₀', 12, 'start', VERM))

    # clamp-at-1 region annotation
    b.append(txt(X(0.010), Y(1.0) + 16, 'gentle: full refund (clamp at 1)', 10.5, 'middle', BLUE))

    b.append('</svg>')
    out = os.path.join(HERE, 'fig10-coasting-deficit.svg')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(''.join(b))
    print('wrote fig10-coasting-deficit.svg')


if __name__ == '__main__':
    fig9()
    fig10()


# ---------------------------------------------------------------- fig 11
def fig11() -> None:
    """Study design: calibrate on D1, freeze, carry to four target corpora."""
    W, H = 780, 524
    b = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']

    def box(x: float, y: float, w: float, h: float, color: str,
            lines: list[tuple[str, int, str]], lw: float = 1.6) -> None:
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" '
                 f'stroke="{color}" stroke-width="{lw}" rx="6"/>')
        ty = y + 20
        for s, size, fill in lines:
            b.append(txt(x + w / 2, ty, s, size, 'middle', fill))
            ty += size + 5

    # source corpus
    box(16, 196, 138, 96, BLUE, [
        ('D1 · longões', 13, INK), ('44 rides · author', 11, GREY),
        ('open, brevet-style', 11, GREY), ('terrain', 11, GREY)])

    # calibration step
    b.append(arrow(158, 244, 200, 244, INK))
    box(204, 196, 148, 96, BLUE, [
        ('calibrate', 13, BLUE), ('ε₀ = 0.13', 11, INK),
        ('c ≈ 3 m/km', 11, INK), ('choose form 3/4', 11, INK)])

    # padlock = freeze
    b.append(arrow(356, 244, 392, 244, INK))
    lx, ly = 398, 228
    b.append(f'<rect x="{lx}" y="{ly}" width="34" height="26" fill="{INK}" rx="4"/>')
    b.append(f'<path d="M{lx + 8},{ly} v-8 a9,9 0 0 1 18,0 v8" fill="none" '
             f'stroke="{INK}" stroke-width="3.4"/>')
    b.append(txt(lx + 17, ly + 44, 'FROZEN', 11, 'middle', INK,
                 'font-weight="600"'))

    # four target corpora
    targets = [
        (24, BLUE, [('D1 · same 44 rides', 12, INK),
                    ('primary comparison', 11, BLUE),
                    ('law vs simulation (§3.1) —', 10, GREY),
                    ('parity where derived', 10, GREY)]),
        (140, GREEN, [('D2 · censo · 62', 12, INK),
                      ('regime test', 11, GREEN),
                      ('urban stop-go, fully', 10, GREY),
                      ('generic rider (§3.1–3.2)', 10, GREY)]),
        (256, VERM, [('D3 · 441   D4 · 219', 12, INK),
                     ('rider transfer', 11, VERM),
                     ('independent full histories;', 10, GREY),
                     ('only mass implied (§3.3)', 10, GREY)]),
        (372, GREY, [('D5 · author-full · 621', 12, INK),
                     ('machinery at scale', 11, INK),
                     ('in-sample, 9 years;', 10, GREY),
                     ('validates instruments (§3.4)', 10, GREY)]),
    ]
    for y, color, lines in targets:
        box(500, y, 262, 96, color, lines)
        b.append(arrow(438, 244 if y != 24 else 238,
                       496, y + 48, GREY, 1.3))

    # protocol strip
    b.append(path([(16, 486), (762, 486)], '#eef0f2', 1))
    b.append(txt(W / 2, 508, 'every ride, everywhere: its own measured power + '
                 'the shared constants → closed form AND simulation → Δ% against '
                 'the measured ∫P·dt', 11, 'middle', GREY))

    b.append('</svg>')
    out = os.path.join(HERE, 'fig11-methodology.svg')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(''.join(b))
    print('wrote fig11-methodology.svg')
