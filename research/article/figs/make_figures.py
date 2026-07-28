#!/usr/bin/env python3
"""Regenerate the article figures as dependency-free SVGs (stdlib only).

Reads the harness CSV outputs (all gitignored — they need the local tracks):
  data/results/model_comparison.csv     (compare.py)
  data/results/eps_hypothesis.csv       (eps_hypothesis.py)
  data/results/censo_comparison.csv     (censo_compare.py)

Writes research/article/figs/fig{1..5}.svg (committed — they carry no GPS, only
per-ride energies and ε, whose ride names are already public in the article).

  python3 research/article/figs/make_figures.py

No numpy/matplotlib: the repo is deliberately build-step-free, so the figures
are hand-emitted SVG (text, diffable, scale-clean) in the same spirit as the
vanilla-JS apps. Colours are the Okabe-Ito colourblind-safe palette.
"""
import csv, math, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RES = os.path.join(ROOT, 'data', 'results')

# Okabe-Ito
BLUE, VERM, GREEN, GREY, INK = '#0072B2', '#D55E00', '#009E73', '#9aa0a6', '#222222'
FONT = 'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else float('nan')


def nice_ticks(lo, hi, n=5):
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    start = math.ceil(lo / step) * step
    out, v = [], start
    while v <= hi + step * 1e-9:
        out.append(round(v, 10))
        v += step
    return out


class Fig:
    """Minimal SVG canvas with one linear x/y mapping and axis helpers."""
    def __init__(self, w, h, pad=(58, 22, 46, 60)):  # T,R,B,L
        self.w, self.h, self.p = w, h, pad
        self.body = []
        self.x0, self.x1 = pad[3], w - pad[1]
        self.y0, self.y1 = pad[0], h - pad[2]

    def map(self, x, y, xr, yr):
        (xa, xb), (ya, yb) = xr, yr
        px = self.x0 + (x - xa) / (xb - xa) * (self.x1 - self.x0)
        py = self.y1 - (y - ya) / (yb - ya) * (self.y1 - self.y0)
        return px, py

    def frame(self, xr, yr, xlabel, ylabel, xticks=None, yticks=None,
              xfmt=lambda v: f'{v:g}', yfmt=lambda v: f'{v:g}', title=''):
        b = self.body
        b.append(f'<rect x="{self.x0}" y="{self.y0}" width="{self.x1-self.x0}" '
                 f'height="{self.y1-self.y0}" fill="#fff" stroke="{GREY}" stroke-width="1"/>')
        if title:
            b.append(f'<text x="{self.w/2:.0f}" y="16" text-anchor="middle" {FONT} '
                     f'font-size="13" font-weight="600" fill="{INK}">{title}</text>')
        for xt in (xticks if xticks is not None else nice_ticks(*xr)):
            px, _ = self.map(xt, yr[0], xr, yr)
            if px < self.x0 - .5 or px > self.x1 + .5:
                continue
            b.append(f'<line x1="{px:.1f}" y1="{self.y0}" x2="{px:.1f}" y2="{self.y1}" '
                     f'stroke="#eef0f2" stroke-width="1"/>')
            b.append(f'<text x="{px:.1f}" y="{self.y1+16:.0f}" text-anchor="middle" {FONT} '
                     f'font-size="11" fill="{INK}">{xfmt(xt)}</text>')
        for yt in (yticks if yticks is not None else nice_ticks(*yr)):
            _, py = self.map(xr[0], yt, xr, yr)
            if py < self.y0 - .5 or py > self.y1 + .5:
                continue
            b.append(f'<line x1="{self.x0}" y1="{py:.1f}" x2="{self.x1}" y2="{py:.1f}" '
                     f'stroke="#eef0f2" stroke-width="1"/>')
            b.append(f'<text x="{self.x0-8:.0f}" y="{py+4:.1f}" text-anchor="end" {FONT} '
                     f'font-size="11" fill="{INK}">{yfmt(yt)}</text>')
        b.append(f'<text x="{(self.x0+self.x1)/2:.0f}" y="{self.h-6}" text-anchor="middle" '
                 f'{FONT} font-size="12" fill="{INK}">{xlabel}</text>')
        cy = (self.y0 + self.y1) / 2
        b.append(f'<text x="14" y="{cy:.0f}" text-anchor="middle" {FONT} font-size="12" '
                 f'fill="{INK}" transform="rotate(-90 14 {cy:.0f})">{ylabel}</text>')

    def dot(self, x, y, xr, yr, r, fill, op=1.0, stroke='none', tip=None, cls=None):
        px, py = self.map(x, y, xr, yr)
        extra = (f' data-tip="{tip}"' if tip else '') + (f' class="{cls}"' if cls else '')
        self.body.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="{fill}" '
                         f'fill-opacity="{op}" stroke="{stroke}" stroke-width="0.8"{extra}/>')

    def line(self, pts, xr, yr, color, w=2.0, dash='', cls=None):
        d = ' '.join(('M' if i == 0 else 'L') + f'{self.map(x,y,xr,yr)[0]:.1f},{self.map(x,y,xr,yr)[1]:.1f}'
                     for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ''
        cl = f' class="{cls}"' if cls else ''
        self.body.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{da}{cl}/>')

    def legend(self, items, x, y):
        # items: (label, colour) or (label, colour, series-key). Keyed entries
        # are emitted as <g class="lg" data-series=…> — the page JS makes them
        # click-to-toggle for the matching .key elements in the same SVG.
        for i, it in enumerate(items):
            lab, col, key = (it + (None,))[:3] if len(it) == 2 else it
            yy = y + i * 18
            row = (f'<rect x="{x}" y="{yy-9}" width="12" height="12" rx="2" fill="{col}"/>'
                   f'<text x="{x+18}" y="{yy+1}" {FONT} font-size="11" fill="{INK}">{lab}</text>')
            if key:
                row = f'<g class="lg" data-series="{key}">{row}</g>'
            self.body.append(row)

    def save(self, name):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
               f'width="{self.w}" height="{self.h}" font-size="12">'
               f'<rect width="{self.w}" height="{self.h}" fill="#fff"/>' + ''.join(self.body) + '</svg>\n')
        with open(os.path.join(HERE, name), 'w') as fh:
            fh.write(svg)
        print('wrote', name)


def load(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


# ---- Figure 1: error attribution — where the closed form's error comes from ----
# Waterfall over the 44 power rides (compare.py, §8.1): baseline 19.1% → climb-aero fix
# (cf split) 8.6% → + 2 m deadband 3.5%; canonical 5.2% as the dashed reference.
# HARDCODED — these mirror compare.py's scoreboard and must be re-synced whenever it
# moves (they were missed in the Entry-27 gravity re-baseline and caught by an audit). The full
# variant ranking stays in the §8.1 table — this figure carries the attribution story.
def fig1():
    """Calibration scoreboard under BOTH protocols (Entry 31): per form,
    informed per-ride parameters (solid) vs blind frozen constants (light),
    with 95% CI whiskers and the simulation under each protocol as lines."""
    rows = [  # label, informed (med, lo, hi), blind (med, lo, hi)
        ('form 1\noriginal', (19.1, 17.3, 21.5), (14.9, 10.6, 22.6)),
        ('form 2\n+ aero split', (8.6, 7.2, 11.0), (7.9, 5.5, 13.6)),
        ('form 3\n+ 2 m deadband', (3.5, 2.0, 5.6), (8.2, 4.5, 10.8)),
        ('form 4\n+ scalar c', (5.9, 3.6, 8.3), (7.6, 5.6, 11.6)),
    ]
    SIM_INF, SIM_BLD = 5.2, 8.4
    f = Fig(560, 370, pad=(46, 24, 66, 54))
    xr, yr = (0, 4), (0, 24)
    f.frame(xr, yr, '', 'median |Δ%| vs measured ∫P·dt',
            xticks=[], yticks=[0, 5, 10, 15, 20],
            title='Calibration scoreboard: informed vs blind (44 rides)')
    bw = 0.26
    for i, (lab, inf, bld) in enumerate(rows):
        for k, ((v, lo, hi), fill, op) in enumerate(((inf, VERM, 0.9), (bld, GREY, 0.75))):
            cx0 = i + 0.5 + (k - 0.5) * (bw + 0.04)
            xl, yb = f.map(cx0 - bw / 2, 0, xr, yr)
            xrr, yt = f.map(cx0 + bw / 2, v, xr, yr)
            tip = f'{lab.replace(chr(10), " ")} — {"informed" if k == 0 else "blind"}: {v:.1f}% [{lo:.1f}, {hi:.1f}]'
            f.body.append(f'<rect x="{xl:.1f}" y="{yt:.1f}" width="{xrr-xl:.1f}" '
                          f'height="{yb-yt:.1f}" rx="2.5" fill="{fill}" '
                          f'fill-opacity="{op}" data-tip="{tip}"/>')
            cx = (xl + xrr) / 2
            _, ylo = f.map(0, lo, xr, yr)
            _, yhi = f.map(0, hi, xr, yr)
            f.body.append(f'<line x1="{cx:.1f}" y1="{ylo:.1f}" x2="{cx:.1f}" y2="{yhi:.1f}" '
                          f'stroke="{INK}" stroke-width="1.2"/>')
            for yy in (ylo, yhi):
                f.body.append(f'<line x1="{cx-4:.1f}" y1="{yy:.1f}" x2="{cx+4:.1f}" y2="{yy:.1f}" '
                              f'stroke="{INK}" stroke-width="1.2"/>')
            f.body.append(f'<text x="{cx:.1f}" y="{yhi-6:.1f}" text-anchor="middle" {FONT} '
                          f'font-size="10.5" font-weight="600" fill="{INK}">{v:.1f}</text>')
        xc, _ = f.map(i + 0.5, 0, xr, yr)
        for k2, line in enumerate(lab.split('\n')):
            f.body.append(f'<text x="{xc:.1f}" y="{f.y1+16+k2*13:.0f}" text-anchor="middle" '
                          f'{FONT} font-size="11" fill="{INK}">{line}</text>')
    for v, dash, lab_ in ((SIM_INF, '5 4', 'simulation, informed 5.2%'),
                          (SIM_BLD, '2 3', 'simulation, blind 8.4%')):
        _, yc = f.map(0, v, xr, yr)
        xlab, _ = f.map(2.0, 0, xr, yr)
        f.body.append(f'<line x1="{f.x0}" y1="{yc:.1f}" x2="{f.x1}" y2="{yc:.1f}" '
                      f'stroke="{GREEN}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
        dy = -5 if v == SIM_BLD else 13
        f.body.append(f'<text x="{xlab:.0f}" y="{yc+dy:.1f}" text-anchor="middle" {FONT} '
                      f'font-size="10.5" fill="{GREEN}">{lab_}</text>')
    lx = f.x1 - 218
    f.body.append(f'<rect x="{lx}" y="{f.y0+8}" width="11" height="11" rx="2" fill="{VERM}" fill-opacity="0.9"/>')
    f.body.append(f'<text x="{lx+16}" y="{f.y0+17}" {FONT} font-size="10.5" fill="{INK}">informed per-ride</text>')
    f.body.append(f'<rect x="{lx+118}" y="{f.y0+8}" width="11" height="11" rx="2" fill="{GREY}" fill-opacity="0.75"/>')
    f.body.append(f'<text x="{lx+134}" y="{f.y0+17}" {FONT} font-size="10.5" fill="{INK}">blind frozen</text>')
    f.save('fig1-attribution.svg')


# ---- Figure 2: predicted vs measured energy, 44 rides ----
def fig2():
    rows = load(os.path.join(RES, 'model_comparison.csv'))
    pts = []
    for r in rows:
        emp = num(r['empirical'])
        can = num(r['canonical'])
        cfS = num(r['cfS_vs_emp'])  # smoothed-cf % error -> reconstruct predicted kJ
        if None in (emp, can, cfS):
            continue
        pts.append((emp / 1000, can / 1000, emp * (1 + cfS / 100) / 1000,
                    (can - emp) / emp * 100, cfS))
    hi = max(max(p[0], p[1], p[2]) for p in pts) * 1.05
    xr = yr = (0, hi)
    f = Fig(420, 400, pad=(40, 18, 46, 52))
    f.frame(xr, yr, 'measured ∫P·dt  (MJ)', 'predicted energy  (MJ)',
            title='Predicted vs measured (44 rides)')
    f.line([(0, 0), (hi, hi)], xr, yr, GREY, 1.2, dash='4 3')
    for emp, can, cfs, dcan, dcfs in pts:
        f.dot(emp, cfs, xr, yr, 4.2, VERM, 0.8, cls='s0',
              tip=f'approx cf+2m: measured {emp:.2f} MJ → predicted {cfs:.2f} MJ ({dcfs:+.1f}%)')
        f.dot(emp, can, xr, yr, 4.2, BLUE, 0.7, cls='s1',
              tip=f'canonical: measured {emp:.2f} MJ → predicted {can:.2f} MJ ({dcan:+.1f}%)')
    f.legend([('approx cf + 2 m smooth', VERM, 's0'), ('canonical', BLUE, 's1'),
              ('perfect (y = x)', GREY)], f.x0 + 12, f.y0 + 16)
    f.save('fig2-pred-vs-meas.svg')


# ---- Figure 3: fractal ascent shrinkage vs deadband threshold ----
# Σh₊ over the 44 rides at each hysteresis threshold (compare.py, §6.1).
def fig3():
    data = [(0, 92.4), (1, 83.3), (2, 77.4), (3, 73.3), (5, 66.9), (10, 56.2)]
    xr, yr = (0, 10), (0, 100)
    f = Fig(440, 320, pad=(34, 18, 46, 54))
    f.frame(xr, yr, 'elevation deadband τ  (m)', 'cumulative ascent Σh₊  (km)',
            xticks=[0, 1, 2, 3, 5, 10], yticks=[0, 20, 40, 60, 80, 100],
            title='Ascent is scale-dependent (fractal)')
    f.line(data, xr, yr, GREEN, 2.4)
    for x, y in data:
        f.dot(x, y, xr, yr, 3.6, GREEN,
              tip=f'τ = {x} m: Σh₊ = {y} km ({y / data[0][1] * 100:.0f}% of raw)')
    # mark the chosen τ = 2 m default
    px, py = f.map(2, 77.4, xr, yr)
    f.body.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{f.y1:.1f}" '
                  f'stroke="{VERM}" stroke-width="1.4" stroke-dasharray="3 3"/>')
    f.body.append(f'<text x="{px+6:.1f}" y="{py-8:.1f}" {FONT} font-size="11" fill="{VERM}">'
                  f'τ = 2 m default (84% of raw)</text>')
    f.save('fig3-ascent-fractal.svg')


# ---- Figure 4: ε_coast vs measured ε_bal, sized by descent energy ----
def fig4():
    rows = load(os.path.join(RES, 'eps_hypothesis.csv'))
    P = []
    for r in rows:
        ec, eb, sb, be = num(r['epsCoast']), num(r['epsBal']), num(r['sbar']), num(r['bHminus'])
        if None in (ec, eb, sb, be):
            continue
        P.append((ec, eb, sb, be))
    bmax = max(p[3] for p in P)
    xr, yr = (0, 1), (-0.4, 1)
    f = Fig(440, 400, pad=(40, 18, 46, 54))
    f.frame(xr, yr, 'ε_coast  (geometry-only prediction)', 'ε_bal  (power-measured)',
            xticks=[0, .25, .5, .75, 1], yticks=[-.25, 0, .25, .5, .75, 1],
            xfmt=lambda v: f'{v:g}', yfmt=lambda v: f'{v:g}',
            title='ε closed form vs measured (44 rides)')
    f.line([(0, 0), (1, 1)], xr, yr, GREY, 1.2, dash='4 3')            # y = x
    # 95% CI band on the fitted line's one parameter: bootstrap the median
    # offset ε_coast − ε_bal over the drawn real-descent subset (mulberry32
    # seed 42, B=10^4 — the bootstrap_ci.py convention), band = the region
    # between the parallel lines y = x − hi … y = x − lo.
    offs = sorted(ec - eb for ec, eb, sb, be in P if sb >= 0.03)

    def _rng(seed):
        a = seed & 0xFFFFFFFF

        def rand():
            nonlocal a
            a = (a + 0x6D2B79F5) & 0xFFFFFFFF
            t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
            t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
            return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
        return rand

    rand, n, B = _rng(42), len(offs), 10000
    boots = sorted(med([offs[int(rand() * n)] for _ in range(n)]) for _ in range(B))
    o_lo, o_hi = boots[int(0.025 * B)], boots[int(0.975 * B) - 1]
    corners = [(max(0, o_lo), max(0, -o_lo)), (1, 1 - o_lo), (1, 1 - o_hi), (max(0, o_hi), max(0, -o_hi))]
    px = ['{:.1f},{:.1f}'.format(*f.map(x, y, xr, yr)) for x, y in corners]
    f.body.append(f'<polygon points="{" ".join(px)}" fill="{GREEN}" opacity="0.13" stroke="none"/>')
    f.line([(0.13, 0), (1, 0.87)], xr, yr, GREEN, 2.0)                 # y = x − 0.13 (calibrated)
    for ec, eb, sb, be in P:
        r = 3 + 7 * math.sqrt(be / bmax)          # area ∝ descent energy β·H₋
        # The figure CANNOT reproduce the harness's real-descent subset exactly:
        # jaam_comparison.csv rounds sbar to 3 dp and TWO rides write as 0.030, so
        # this test yields 21 (>=) or 19 (>) where the harness — working from the
        # unrounded s̄ — counts 20.  Rather than fake a count, the legend states the
        # CRITERION and no n; the exact n lives in the text, which quotes the
        # harness.  (Do not 'fix' this by tuning the threshold; fix it by widening
        # the CSV's precision if the exact subset is ever needed here.)
        real = sb >= 0.03
        f.dot(ec, eb, xr, yr, r, VERM if real else GREY, 0.55 if real else 0.30,
              stroke='#fff' if real else 'none', cls='s0' if real else 's1',
              tip=f'ε_coast {ec:.2f} → ε_bal {eb:.2f} · s̄ {sb*100:.1f}% · βH₋ {be/1000:.0f} kJ')
    f.body.append(f'<text x="{f.x1-10:.0f}" y="{f.y0+18:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε = ε_coast − 0.13</text>')
    f.body.append(f'<text x="{f.x1-10:.0f}" y="{f.y0+32:.0f}" text-anchor="end" {FONT} '
                  f'font-size="10" fill="{GREEN}" opacity="0.85">band: 95% CI of the median '
                  f'offset [{o_lo:.2f}, {o_hi:.2f}]</text>')
    f.legend([('real descents (s̄ ≥ 3%)', VERM, 's0'), ('gentle (near-zero descent kJ)', GREY, 's1')],
             f.x0 + 12, f.y1 - 40)
    f.body.append(f'<text x="{f.x0+12:.0f}" y="{f.y1-4:.0f}" {FONT} font-size="10" '
                  f'fill="{GREY}">point area ∝ descent energy β·H₋</text>')
    f.save('fig4-eps-scatter.svg')


# ---- Figure 5: censo ε-sweep (median Δ% vs ε), the transfer test ----
def fig5():
    rows = [r for r in load(os.path.join(RES, 'censo_comparison.csv'))
            if r['dataOK'] in ('1', 'true', 'True')]
    eps = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
    sm = [med([num(r[f'sm_{e:.2f}']) for r in rows]) for e in eps]
    pm = [med([num(r[f'pm_{e:.2f}']) for r in rows]) for e in eps]
    xr, yr = (0, 0.25), (-6, 16)
    f = Fig(440, 340, pad=(40, 18, 46, 54))
    f.frame(xr, yr, 'descent-recovery factor ε', 'median Δ%  (model − measured)',
            xticks=[0, .05, .1, .15, .2, .25], yticks=[-5, 0, 5, 10, 15],
            title='Censo ε-sweep — 62 urban rides (transfer test)')
    f.line([(0, 0), (0.25, 0)], xr, yr, GREY, 1.0, dash='4 3')
    f.line(list(zip(eps, sm)), xr, yr, BLUE, 2.2, cls='s0')
    f.line(list(zip(eps, pm)), xr, yr, VERM, 2.2, cls='s1')
    for e, y in zip(eps, sm):
        f.dot(e, y, xr, yr, 3.4, BLUE, cls='s0',
              tip=f'smooth · ε = {e:.2f}: median Δ% {y:+.1f}')
    for e, y in zip(eps, pm):
        f.dot(e, y, xr, yr, 3.4, VERM, cls='s1',
              tip=f"poor-man's · ε = {e:.2f}: median Δ% {y:+.1f}")
    px, py = f.map(0.20, 0, xr, yr)
    f.body.append(f'<line x1="{px:.1f}" y1="{f.y0:.1f}" x2="{px:.1f}" y2="{f.y1:.1f}" '
                  f'stroke="{GREEN}" stroke-width="1.4" stroke-dasharray="3 3"/>')
    f.body.append(f'<text x="{px-6:.1f}" y="{f.y0+14:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε ≈ 0.20 optimum</text>')
    f.legend([('smooth approx', BLUE, 's0'), ("poor-man's scalar", VERM, 's1')], f.x0 + 12, f.y1 - 34)
    f.save('fig5-censo-sweep.svg')


# ---- Figure 6: the SECOND-RIDER ε test (estimators frozen from rider 1) ----
def fig6():
    path6 = os.path.join(RES, 'ppaz_comparison.csv')
    if not os.path.exists(path6):
        print('skip fig6 (no ppaz_comparison.csv — run ppaz_compare.py)')
        return
    rows = load(path6)
    P = []
    for r in rows:
        ec, eb, sb, hd = num(r['epsCoast']), num(r['epsBal']), num(r['sbar']), num(r['Hd'])
        if None in (ec, eb, sb, hd):
            continue
        P.append((ec, eb, sb, hd))
    hmax = max(p[3] for p in P)
    xr, yr = (0, 1), (-0.4, 1.2)
    f = Fig(440, 400, pad=(40, 18, 46, 54))
    f.frame(xr, yr, 'ε_coast  (geometry-only prediction)', 'ε_bal  (power-measured, rider 2)',
            xticks=[0, .25, .5, .75, 1], yticks=[-.25, 0, .25, .5, .75, 1],
            title='Second rider (441 rides) — calibration frozen from rider 1')
    f.line([(0, 0), (1, 1)], xr, yr, GREY, 1.2, dash='4 3')            # y = x
    f.line([(0.13, 0), (1, 0.87)], xr, yr, GREEN, 2.0)                 # y = x − 0.13 (FROZEN)
    for ec, eb, sb, hd in P:
        r = 2.2 + 5.5 * math.sqrt(hd / hmax)      # area ∝ descent drop H₋
        real = sb >= 0.03
        f.dot(ec, min(eb, 1.2), xr, yr, r, VERM if real else GREY, 0.45 if real else 0.22,
              stroke='none', cls='s0' if real else 's1',
              tip=f'ε_coast {ec:.2f} → ε_bal {eb:.2f} · s̄ {sb*100:.1f}% · H₋ {hd:.0f} m')
    f.body.append(f'<text x="{f.x1-10:.0f}" y="{f.y0+18:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε = ε_coast − 0.13 (frozen)</text>')
    f.legend([('real descents (s̄ ≥ 3%, n = 156)', VERM, 's0'), ('gentle rides', GREY, 's1')],
             f.x0 + 12, f.y1 - 40)
    f.body.append(f'<text x="{f.x0+12:.0f}" y="{f.y1-4:.0f}" {FONT} font-size="10" '
                  f'fill="{GREY}">point area ∝ descent drop H₋</text>')
    f.save('fig6-ppaz-eps.svg')


# ---- Figure 7: predicted (T1b) vs measured moving time, all three corpora ----
def fig7():
    path7 = os.path.join(RES, 'time_comparison.csv')
    if not os.path.exists(path7):
        print('skip fig7 (no time_comparison.csv — run time_compare.py)')
        return
    rows = [r for r in load(path7) if r['timeOK'] in ('1', 'true', 'True')]
    col = {'longoes': BLUE, 'censo': VERM, 'ppaz': GREEN}
    P = []
    for r in rows:
        meas, pred = num(r['tMovBin']), num(r['T1b_pred'])
        if None in (meas, pred):
            continue
        P.append((meas / 3600, pred / 3600, r['corpus']))   # hours
    hi = max(max(p[0], p[1]) for p in P) * 1.04
    xr = yr = (0, hi)
    f = Fig(430, 400, pad=(40, 18, 46, 52))
    f.frame(xr, yr, 'measured moving time  (h)', 'predicted time — T1b  (h)',
            title='Predicted vs measured moving time')
    f.line([(0, 0), (hi, hi)], xr, yr, GREY, 1.2, dash='4 3')
    # draw ppaz first (most points), then censo, then longões on top
    key = {'ppaz': 's2', 'censo': 's1', 'longoes': 's0'}
    for corp in ('ppaz', 'censo', 'longoes'):
        for meas, pred, c in P:
            if c == corp:
                f.dot(meas, pred, xr, yr, 3.6, col[corp], 0.6, cls=key[corp],
                      tip=f'{corp}: measured {meas:.2f} h → predicted {pred:.2f} h '
                          f'({(pred / meas - 1) * 100:+.1f}%)')
    f.legend([('longões (rider 1, open)', BLUE, 's0'), ('censo (rider 1, urban)', VERM, 's1'),
              ('P. Paz (rider 2)', GREEN, 's2'), ('perfect (y = x)', GREY)], f.x0 + 12, f.y0 + 16)
    f.save('fig7-time.svg')


# ---- Figure 8: the THIRD-RIDER ε test (JAAM) — the frozen line does NOT track ----
# Deliberate contrast to fig6 (P. Paz): same axes, same frozen line, a rider it fails on.
def fig8():
    path8 = os.path.join(RES, 'jaam_comparison.csv')
    if not os.path.exists(path8):
        print('skip fig8 (no jaam_comparison.csv — run jaam_compare.py)')
        return
    rows = load(path8)
    P = []
    for r in rows:
        ec, eb, sb, hd = num(r['epsCoast']), num(r['epsBal']), num(r['sbar']), num(r['Hd'])
        if None in (ec, eb, sb, hd):
            continue
        P.append((ec, eb, sb, hd))
    hmax = max(p[3] for p in P)
    xr, yr = (0, 1), (-0.4, 1.2)
    f = Fig(440, 400, pad=(40, 18, 46, 54))
    f.frame(xr, yr, 'ε_coast  (geometry-only prediction)', 'ε_bal  (power-measured, rider 3)',
            xticks=[0, .25, .5, .75, 1], yticks=[-.25, 0, .25, .5, .75, 1],
            title='Third rider JAAM — fits the real descents, misses the gentle bulk')
    f.line([(0, 0), (1, 1)], xr, yr, GREY, 1.2, dash='4 3')            # y = x
    f.line([(0.13, 0), (1, 0.87)], xr, yr, GREEN, 2.0)                 # y = x − 0.13 (FROZEN)
    for ec, eb, sb, hd in P:
        r = 2.2 + 5.5 * math.sqrt(hd / hmax)
        real = sb >= 0.03
        f.dot(ec, min(eb, 1.2), xr, yr, r, VERM if real else GREY, 0.55 if real else 0.20,
              stroke='none', cls='s0' if real else 's1',
              tip=f'ε_coast {ec:.2f} → ε_bal {eb:.2f} · s̄ {sb*100:.1f}% · H₋ {hd:.0f} m')
    f.body.append(f'<text x="{f.x1-10:.0f}" y="{f.y0+18:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε = ε_coast − 0.13 (frozen)</text>')
    f.legend([('real descents (s̄ ≥ 3%)', VERM, 's0'), ('gentle rides (bulk)', GREY, 's1')],
             f.x0 + 12, f.y1 - 40)
    f.body.append(f'<text x="{f.x0+12:.0f}" y="{f.y1-4:.0f}" {FONT} font-size="10" '
                  f'fill="{GREY}">most of this rider\'s riding is gentle — measured ε_bal sits far below the line</text>')
    f.save('fig8-jaam-eps.svg')


if __name__ == '__main__':
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7(); fig8()


# ---- Figure 8: the regime rule as a slopegraph over Table 3 ----
def fig14():
    """med|Δ%| per corpus for the two form-3 ε rules + the simulation
    (Table 3's narrative in one glance); form-4 variants as faint context.
    Numbers = the gated Table 3 values (update on re-baseline)."""
    CORP = ['D2\ncenso', 'D3\nP. Paz', 'D4\nJAAM', 'D5\nauthor†', 'D3–D5\npooled']
    SERIES = [  # label, color, dash, width, opacity, [(med, lo, hi)]
        ('form 3 · ε_d', VERM, '', 2.4, 1.0,
         [(7.7, 6.0, 9.3), (5.8, 5.3, 6.4), (5.5, 4.4, 6.4), (6.2, 5.6, 6.9), (5.9, 5.5, 6.2)]),
        ('form 3 · ε_f', BLUE, '6 4', 2.4, 1.0,
         [(4.7, 3.3, 6.2), (10.1, 9.3, 10.7), (3.5, 3.1, 4.2), (8.1, 7.3, 8.7), (7.5, 7.0, 8.0)]),
        ('simulation', GREEN, '2 3', 2.0, 1.0,
         [(6.6, 4.7, 8.7), (6.8, 6.2, 7.8), (5.4, 4.9, 6.1), (6.1, 5.5, 6.7), (6.2, 5.9, 6.6)]),
        ('form 4 · ε_d', GREY, '', 1.2, 0.55,
         [(6.4, 4.8, 8.6), (4.9, 4.4, 5.8), (9.0, 7.9, 9.7), (7.1, 6.4, 8.1), (6.6, 6.3, 7.1)]),
        ('form 4 · ε_f', GREY, '6 4', 1.2, 0.55,
         [(3.9, 3.2, 6.1), (6.8, 6.0, 7.6), (5.6, 4.8, 6.4), (6.9, 6.2, 7.5), (6.6, 6.1, 7.0)]),
    ]
    f = Fig(560, 380, pad=(40, 130, 60, 54))
    xr, yr = (-0.3, 4.3), (2.5, 11)
    f.frame(xr, yr, '', 'median |Δ%|', xticks=[], yticks=[3, 5, 7, 9, 11],
            title='The regime rule across corpora (Table 3)')
    for li, (lab, color, dash, w, op, pts) in enumerate(SERIES):
        jitter = (li - 2) * 0.045          # avoid whisker overlap at shared x
        path = [f.map(i + jitter, v, xr, yr) for i, (v, lo, hi) in enumerate(pts)]
        d = 'M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in path)
        dd = f' stroke-dasharray="{dash}"' if dash else ''
        f.body.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"'
                      f'{dd} opacity="{op}"/>')
        for i, (v, lo, hi) in enumerate(pts):
            cx, cy = f.map(i + jitter, v, xr, yr)
            if op == 1.0:
                _, ylo = f.map(0, lo, xr, yr)
                _, yhi = f.map(0, hi, xr, yr)
                f.body.append(f'<line x1="{cx:.1f}" y1="{ylo:.1f}" x2="{cx:.1f}" y2="{yhi:.1f}" '
                              f'stroke="{color}" stroke-width="1" opacity="0.5"/>')
            f.body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{3.2 if op == 1 else 2.2}" '
                          f'fill="{color}" opacity="{op}" data-tip="{lab}: {v:.1f} [{lo:.1f}, {hi:.1f}]"/>')
        lx, ly = path[-1]
        dy = {0: 10, 1: 4, 2: -2, 3: -6, 4: 14}[li]   # separate coincident end labels
        f.body.append(f'<text x="{lx + 8:.0f}" y="{ly + dy:.0f}" {FONT} font-size="11" '
                      f'fill="{color}" opacity="{max(op, 0.8)}">{lab}</text>')
    for i, lab in enumerate(CORP):
        xc, _ = f.map(i, 0, xr, yr)
        for k, line in enumerate(lab.split('\n')):
            f.body.append(f'<text x="{xc:.0f}" y="{f.y1 + 16 + k * 13:.0f}" text-anchor="middle" '
                          f'{FONT} font-size="11" fill="{INK}">{line}</text>')
    f.body.append(f'<text x="{f.x0 + 6:.0f}" y="{f.y1 - 8:.0f}" {FONT} font-size="10.5" '
                  f'fill="{GREY}">lower is better · whiskers: 95% CI · faint: form 4 · '
                  f'* D2 ε_f is in-sample</text>')
    f.save('fig8-regime-slopes.svg')
