#!/usr/bin/env python3
"""Regenerate the article figures as dependency-free SVGs (stdlib only).

Reads the harness CSV outputs (all gitignored — they need the local tracks):
  data/activities/model_comparison.csv          (compare.mjs)
  data/activities/eps_hypothesis.csv            (eps_hypothesis.mjs)
  data/activities/censohidrografico/censo_comparison.csv  (censo_compare.mjs)

Writes research/figs/fig{1..5}.svg (committed — they carry no GPS, only
per-ride energies and ε, whose ride names are already public in the article).

  python3 research/figs/make_figures.py

No numpy/matplotlib: the repo is deliberately build-step-free, so the figures
are hand-emitted SVG (text, diffable, scale-clean) in the same spirit as the
vanilla-JS apps. Colours are the Okabe-Ito colourblind-safe palette.
"""
import csv, math, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ACT = os.path.join(ROOT, 'data', 'activities')

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

    def dot(self, x, y, xr, yr, r, fill, op=1.0, stroke='none'):
        px, py = self.map(x, y, xr, yr)
        self.body.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="{fill}" '
                         f'fill-opacity="{op}" stroke="{stroke}" stroke-width="0.8"/>')

    def line(self, pts, xr, yr, color, w=2.0, dash=''):
        d = ' '.join(('M' if i == 0 else 'L') + f'{self.map(x,y,xr,yr)[0]:.1f},{self.map(x,y,xr,yr)[1]:.1f}'
                     for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.body.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{da}/>')

    def legend(self, items, x, y):
        for i, (lab, col) in enumerate(items):
            yy = y + i * 18
            self.body.append(f'<rect x="{x}" y="{yy-9}" width="12" height="12" rx="2" fill="{col}"/>')
            self.body.append(f'<text x="{x+18}" y="{yy+1}" {FONT} font-size="11" fill="{INK}">{lab}</text>')

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


# ---- Figure 1: the longões scoreboard (median |Δ%| per variant) ----
# Aggregate medians over the 44 power rides (compare.mjs scoreboard, §8.1).
def fig1():
    rows = [
        ('approx cf + 2 m smooth', 3.6, True),
        ('canonical (forward sim)', 5.1, False),
        ('canonical + 2 m smooth', 5.6, False),
        ('approx cf + scalar k_smooth', 5.8, False),
        ('approx cf + sheet v_f', 7.2, False),
        ('approx cf + measured v_f', 8.2, False),
        ('approx + climb-fraction (cf)', 8.7, False),
        ('approx off + 2 m smooth', 10.2, False),
        ('approx off (baseline)', 19.3, False),
    ]
    f = Fig(560, 300, pad=(30, 20, 40, 210))
    xr, yr = (0, 20), (0, len(rows))
    f.frame(xr, yr, 'median |Δ%| vs measured ∫P·dt', '', yticks=[])
    bh = (f.y1 - f.y0) / len(rows) * 0.66
    for i, (lab, v, win) in enumerate(rows):
        yc = f.y0 + (i + 0.5) / len(rows) * (f.y1 - f.y0)
        x0, _ = f.map(0, 0, xr, yr)
        x1, _ = f.map(min(v, 20), 0, xr, yr)
        col = VERM if win else (BLUE if 'canonical' in lab else GREY)
        f.body.append(f'<rect x="{x0:.1f}" y="{yc-bh/2:.1f}" width="{x1-x0:.1f}" height="{bh:.1f}" '
                      f'rx="2" fill="{col}" fill-opacity="{1 if win else 0.85}"/>')
        f.body.append(f'<text x="{x0-8:.0f}" y="{yc+4:.1f}" text-anchor="end" {FONT} '
                      f'font-size="11" fill="{INK}" font-weight="{600 if win else 400}">{lab}</text>')
        f.body.append(f'<text x="{x1+5:.1f}" y="{yc+4:.1f}" {FONT} font-size="11" '
                      f'fill="{INK}" font-weight="{600 if win else 400}">{v:.1f}</text>')
    f.save('fig1-scoreboard.svg')


# ---- Figure 2: predicted vs measured energy, 44 rides ----
def fig2():
    rows = load(os.path.join(ACT, 'model_comparison.csv'))
    pts = []
    for r in rows:
        emp = num(r['empirical'])
        can = num(r['canonical'])
        cfS = num(r['cfS_vs_emp'])  # smoothed-cf % error -> reconstruct predicted kJ
        if None in (emp, can, cfS):
            continue
        pts.append((emp / 1000, can / 1000, emp * (1 + cfS / 100) / 1000))
    hi = max(max(p[0], p[1], p[2]) for p in pts) * 1.05
    xr = yr = (0, hi)
    f = Fig(420, 400, pad=(40, 18, 46, 52))
    f.frame(xr, yr, 'measured ∫P·dt  (MJ)', 'predicted energy  (MJ)',
            title='Predicted vs measured (44 rides)')
    f.line([(0, 0), (hi, hi)], xr, yr, GREY, 1.2, dash='4 3')
    for emp, can, cfs in pts:
        f.dot(emp, cfs, xr, yr, 4.2, VERM, 0.8)
        f.dot(emp, can, xr, yr, 4.2, BLUE, 0.7)
    f.legend([('approx cf + 2 m smooth', VERM), ('canonical', BLUE), ('perfect (y = x)', GREY)],
             f.x0 + 12, f.y0 + 16)
    f.save('fig2-pred-vs-meas.svg')


# ---- Figure 3: fractal ascent shrinkage vs deadband threshold ----
# Σh₊ over the 44 rides at each hysteresis threshold (compare.mjs, §6.1).
def fig3():
    data = [(0, 92.4), (1, 83.3), (2, 77.4), (3, 73.3), (5, 66.9), (10, 56.2)]
    xr, yr = (0, 10), (0, 100)
    f = Fig(440, 320, pad=(34, 18, 46, 54))
    f.frame(xr, yr, 'elevation deadband τ  (m)', 'cumulative ascent Σh₊  (km)',
            xticks=[0, 1, 2, 3, 5, 10], yticks=[0, 20, 40, 60, 80, 100],
            title='Ascent is scale-dependent (fractal)')
    f.line(data, xr, yr, GREEN, 2.4)
    for x, y in data:
        f.dot(x, y, xr, yr, 3.6, GREEN)
    # mark the chosen τ = 2 m default
    px, py = f.map(2, 77.4, xr, yr)
    f.body.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{f.y1:.1f}" '
                  f'stroke="{VERM}" stroke-width="1.4" stroke-dasharray="3 3"/>')
    f.body.append(f'<text x="{px+6:.1f}" y="{py-8:.1f}" {FONT} font-size="11" fill="{VERM}">'
                  f'τ = 2 m default (84% of raw)</text>')
    f.save('fig3-ascent-fractal.svg')


# ---- Figure 4: ε_coast vs measured ε_bal, sized by descent energy ----
def fig4():
    rows = load(os.path.join(ACT, 'eps_hypothesis.csv'))
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
    f.line([(0.13, 0), (1, 0.87)], xr, yr, GREEN, 2.0)                 # y = x − 0.13 (calibrated)
    for ec, eb, sb, be in P:
        r = 3 + 7 * math.sqrt(be / bmax)          # area ∝ descent energy β·H₋
        real = sb >= 0.03
        f.dot(ec, eb, xr, yr, r, VERM if real else GREY, 0.55 if real else 0.30,
              stroke='#fff' if real else 'none')
    f.body.append(f'<text x="{f.x1-10:.0f}" y="{f.y0+18:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε = ε_coast − 0.13</text>')
    f.legend([('real descents (s̄ ≥ 3%)', VERM), ('gentle (near-zero descent kJ)', GREY)],
             f.x0 + 12, f.y1 - 40)
    f.body.append(f'<text x="{f.x0+12:.0f}" y="{f.y1-4:.0f}" {FONT} font-size="10" '
                  f'fill="{GREY}">point area ∝ descent energy β·H₋</text>')
    f.save('fig4-eps-scatter.svg')


# ---- Figure 5: censo ε-sweep (median Δ% vs ε), the transfer test ----
def fig5():
    rows = [r for r in load(os.path.join(ACT, 'censohidrografico', 'censo_comparison.csv'))
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
    f.line(list(zip(eps, sm)), xr, yr, BLUE, 2.2)
    f.line(list(zip(eps, pm)), xr, yr, VERM, 2.2)
    for e, y in zip(eps, sm):
        f.dot(e, y, xr, yr, 3.4, BLUE)
    for e, y in zip(eps, pm):
        f.dot(e, y, xr, yr, 3.4, VERM)
    px, py = f.map(0.20, 0, xr, yr)
    f.body.append(f'<line x1="{px:.1f}" y1="{f.y0:.1f}" x2="{px:.1f}" y2="{f.y1:.1f}" '
                  f'stroke="{GREEN}" stroke-width="1.4" stroke-dasharray="3 3"/>')
    f.body.append(f'<text x="{px-6:.1f}" y="{f.y0+14:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε ≈ 0.20 optimum</text>')
    f.legend([('smooth approx', BLUE), ("poor-man's scalar", VERM)], f.x0 + 12, f.y1 - 34)
    f.save('fig5-censo-sweep.svg')


# ---- Figure 6: the SECOND-RIDER ε test (estimators frozen from rider 1) ----
def fig6():
    path6 = os.path.join(ACT, 'ppaz_comparison.csv')
    if not os.path.exists(path6):
        print('skip fig6 (no ppaz_comparison.csv — run ppaz_compare.mjs)')
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
              stroke='none')
    f.body.append(f'<text x="{f.x1-10:.0f}" y="{f.y0+18:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε = ε_coast − 0.13 (frozen)</text>')
    f.legend([('real descents (s̄ ≥ 3%, n = 156)', VERM), ('gentle rides', GREY)],
             f.x0 + 12, f.y1 - 40)
    f.body.append(f'<text x="{f.x0+12:.0f}" y="{f.y1-4:.0f}" {FONT} font-size="10" '
                  f'fill="{GREY}">point area ∝ descent drop H₋</text>')
    f.save('fig6-ppaz-eps.svg')


# ---- Figure 7: predicted (T1b) vs measured moving time, all three corpora ----
def fig7():
    path7 = os.path.join(ACT, 'time_comparison.csv')
    if not os.path.exists(path7):
        print('skip fig7 (no time_comparison.csv — run time_compare.mjs)')
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
    for corp in ('ppaz', 'censo', 'longoes'):
        for meas, pred, c in P:
            if c == corp:
                f.dot(meas, pred, xr, yr, 3.6, col[corp], 0.6)
    f.legend([('longões (rider 1, open)', BLUE), ('censo (rider 1, urban)', VERM),
              ('P. Paz (rider 2)', GREEN), ('perfect (y = x)', GREY)], f.x0 + 12, f.y0 + 16)
    f.save('fig7-time.svg')


# ---- Figure 8: the THIRD-RIDER ε test (JAAM) — the frozen line does NOT track ----
# Deliberate contrast to fig6 (P. Paz): same axes, same frozen line, a rider it fails on.
def fig8():
    path8 = os.path.join(ACT, 'jaam_comparison.csv')
    if not os.path.exists(path8):
        print('skip fig8 (no jaam_comparison.csv — run jaam_compare.mjs)')
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
            title='Third rider JAAM — fits the 21 real descents, misses the gentle bulk')
    f.line([(0, 0), (1, 1)], xr, yr, GREY, 1.2, dash='4 3')            # y = x
    f.line([(0.13, 0), (1, 0.87)], xr, yr, GREEN, 2.0)                 # y = x − 0.13 (FROZEN)
    for ec, eb, sb, hd in P:
        r = 2.2 + 5.5 * math.sqrt(hd / hmax)
        real = sb >= 0.03
        f.dot(ec, min(eb, 1.2), xr, yr, r, VERM if real else GREY, 0.55 if real else 0.20,
              stroke='none')
    f.body.append(f'<text x="{f.x1-10:.0f}" y="{f.y0+18:.0f}" text-anchor="end" {FONT} '
                  f'font-size="11" fill="{GREEN}">ε = ε_coast − 0.13 (frozen)</text>')
    f.legend([('real descents (s̄ ≥ 3%, n = 21)', VERM), ('gentle rides (bulk)', GREY)],
             f.x0 + 12, f.y1 - 40)
    f.body.append(f'<text x="{f.x0+12:.0f}" y="{f.y1-4:.0f}" {FONT} font-size="10" '
                  f'fill="{GREY}">most of this rider\'s riding is gentle — measured ε_bal sits far below the line</text>')
    f.save('fig8-jaam-eps.svg')


if __name__ == '__main__':
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7(); fig8()
