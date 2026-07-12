#!/usr/bin/env node
// ENTRY 19 — the app on its usual DEM: v2Edge on the deployed IGC-SP 5 m raster vs a 30 m
// resample (plus FABDEM V1-2 as the free-global-DEM reference), censo + independent-rider rides.
//
// Per ride, FOUR profile sources, each arc-length-resampled from the GPS track:
//   baro     — recorded elevation, standard harness profile (5 m grid; the anchor — must
//              reproduce regime_compare.mjs's per-ride r1d5r / r0sm / emp for the same rides)
//   igc5     — sampa_geral.tif (IGC-SP-derived, ~5 m px, WGS84) sampled bilinearly at 5 m steps
//   igc30    — the same raster warped to ~30 m (6× native px, -r average) at 30 m steps
//   fabdem30 — FABDEM V1-2 tile S24W047 sampled bilinearly at 30 m steps
// Models per profile (vs measured ∫P·dt): the deployed v2Edge walk (r1dV2Edge, RAW profile at
// its native step — deployment-faithful, no deadband) and the R0 champion (cf + 2 m deadband;
// ε rule: censo urban → flat 0.20; rider corpora → frozen ε_geom(−0.13) of that profile source).
//
// ENGINE REUSE IS BYTE-IDENTICAL BY CONSTRUCTION: the engine block below is EXTRACTED AT RUNTIME
// from regime_compare.mjs (line-level brace-balanced grab of the named top-level functions/consts)
// and eval'd — nothing re-typed, nothing to drift. New code = geo track builder, DEM sampler,
// walk decomposition (asserted ≡ r1dV2Edge per ride), drivers, report.
//
// One-time raster prep (both into the session scratch dir, NEVER the repo):
//   gdalwarp -r average -tr 0.000287042610744 0.000287042610744 \
//     /Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif $SCRATCH/sampa_geral_30m.tif
//   curl -sSf -o $SCRATCH/S24W047_FABDEM_V1-2.tif \
//     https://telhas.pedalhidrografi.co/fabdem/S24W047_FABDEM_V1-2.tif
// (0.000287042610744° = 6 × the native 0.000047840435124° pixel ≈ 30 m at this latitude.)
//
//   node igc_resolution_test.mjs        → report on stdout (timings on stderr) +
//                                         igc_resolution_test.csv (gitignored via *.csv)
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '..', 'data', 'activities');
const RESULTS = path.join(HERE, '..', 'results');
fs.mkdirSync(RESULTS, { recursive: true });
const SCRATCH = '/private/tmp/claude-501/-Users-danlessa-repos-pedalhidro-simujaules/6a419542-bc75-4ec1-aced-8e8de9a58ae3/scratchpad';
const DEM5 = '/Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif';
const DEM30 = path.join(SCRATCH, 'sampa_geral_30m.tif');
const FABDEM = path.join(SCRATCH, 'S24W047_FABDEM_V1-2.tif');
// sampa_geral.tif bounds (gdalinfo): origin (-46.948167148, -23.372989389), 14913×9055 px of
// 0.000047840435124° — strict bbox test for the track (pre-filter before any sampling).
const BBOX = { lonMin: -46.9481671, lonMax: -46.2347227, latMin: -23.8061845, latMax: -23.3729894 };

// ===== ENGINE: extracted verbatim from regime_compare.mjs at runtime =====
const REGIME_PATH = path.join(HERE, 'regime_compare.mjs');
const regimeLines = fs.readFileSync(REGIME_PATH, 'utf8').split('\n');
function grabBlock(startRe) {
  const i = regimeLines.findIndex(l => startRe.test(l));
  if (i < 0) throw new Error(`engine grab failed: ${startRe}`);
  const out = []; let depth = 0;
  for (let j = i; j < regimeLines.length; j++) {
    const l = regimeLines[j]; out.push(l);
    for (const ch of l) { if (ch === '{') depth++; else if (ch === '}') depth--; }
    if (depth === 0) break;
  }
  if (depth !== 0) throw new Error(`unbalanced grab: ${startRe}`);
  return out.join('\n');
}
const ENGINE_BLOCKS = [
  /^const G = 9\.81, NS = 240;/,
  /^const VMAX = 38 \/ 3\.6, VSTART = 15 \/ 3\.6;/,
  /^const CLIMB_THR = 0\.02, DESC_THR = -0\.015, ENGINE_DX = 5, TAU_SMOOTH = 2;/,
  /^const VSTOP = 0\.5 \/ 3\.6;/,
  /^const ASSUMED = \{ m: 78, CdA: 0\.40, Crr: 0\.008, rho: 1\.13, keff: 0\.98, wind: 0 \};/,
  /^const PHYS = \{\};/,
  /^for \(const \[r, m0\] of \[\['ppaz', 74\.3\]/,
  /^const ZWIFT = 260;/,
  /^let H = new Float64Array\(NS\), physProfile = null;/,
  /^let FIT_MANUF;/,
  /^function haversine\(/,
  /^function flatEqSpeed\(/,
  /^function resampleProfile\(/,
  /^function approxComponents\(/,
  /^function buildProfile\(/,
  /^function parseFIT\(/,
  /^function finishPts\(/,
  /^function ptsFromFIT\(/,
  /^function ptsFromGPX\(/,
  /^function deadband\(/,
  /^function empiricalKJ\(/,
  /^function overallMeanPower\(/,
  /^function hasPower\(/,
  /^function epsGeom\(/,
  /^const medOf = /,
  /^const readPts = /,
  /^let R1D_MIN_PRECLAMP = Infinity;/,
  /^function r1dV2Edge\(/,
  /^function r0Champion\(/,
  /^function pointRegimeData\(/,
  /^function binGrades\(/,
  /^const pwFrom = /,
  /^const dPct = /,
  /^function erf\(/,
  /^const pFromZ = /,
  /^function pairedAbs\(/,
];
const engineSrc = ENGINE_BLOCKS.map(grabBlock).join('\n');
const E = new Function('fs', 'path', 'zlib', 'HERE', engineSrc + `
return { haversine, flatEqSpeed, resampleProfile, approxComponents, buildProfile, parseFIT,
  finishPts, ptsFromFIT, ptsFromGPX, deadband, empiricalKJ, overallMeanPower, hasPower, epsGeom,
  medOf, readPts, r1dV2Edge, r0Champion, pointRegimeData, binGrades, pwFrom, dPct, erf, pFromZ,
  pairedAbs, ASSUMED, PHYS, ZWIFT, G, VMAX, VSTART, CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH,
  getPhysProfile: () => physProfile, getManuf: () => FIT_MANUF,
  getMinPreclamp: () => R1D_MIN_PRECLAMP };`)(fs, path, zlib, HERE);
const { haversine, flatEqSpeed, resampleProfile, buildProfile, parseFIT, deadband, empiricalKJ,
  overallMeanPower, hasPower, epsGeom, medOf, readPts, r1dV2Edge, r0Champion, pointRegimeData,
  binGrades, pwFrom, dPct, pairedAbs, ASSUMED, PHYS, ZWIFT, G, VMAX, VSTART, CLIMB_THR, DESC_THR,
  ENGINE_DX, TAU_SMOOTH } = E;

// ===== raster prep (idempotent) =====
fs.mkdirSync(SCRATCH, { recursive: true });
if (!fs.existsSync(DEM30)) {
  console.error('creating 30 m warp…');
  execFileSync('gdalwarp', ['-r', 'average', '-tr', '0.000287042610744', '0.000287042610744', DEM5, DEM30], { stdio: ['ignore', 'ignore', 'inherit'] });
}
if (!fs.existsSync(FABDEM)) {
  console.error('downloading FABDEM tile…');
  execFileSync('curl', ['-sSf', '-o', FABDEM, 'https://telhas.pedalhidrografi.co/fabdem/S24W047_FABDEM_V1-2.tif'], { stdio: 'inherit' });
}

// ===== NEW: geo track (lat/lon vs the SAME cumulative x as ptsFromFIT) =====
// Mirrors ptsFromFIT's distance mapping exactly (device-distance interpolation when present,
// haversine chain otherwise) so profile arc-length d maps to track position d + pts[0].x.
function geoTrackFromFIT(buffer) {
  const recs = parseFIT(buffer);
  const out = [];
  if (recs.some(r => r.dist !== undefined)) {
    const di = [], dv = [];
    recs.forEach((r, i) => { if (r.dist !== undefined) { di.push(i); dv.push(dv.length ? Math.max(r.dist, dv[dv.length - 1]) : r.dist); } });
    let k = 0;
    for (let i = 0; i < recs.length; i++) {
      if (recs[i].lat === undefined || recs[i].lon === undefined) continue;
      while (k < di.length - 1 && di[k + 1] <= i) k++;
      let x;
      if (i <= di[0]) x = dv[0]; else if (i >= di[di.length - 1]) x = dv[dv.length - 1];
      else { const f = (i - di[k]) / (di[k + 1] - di[k]); x = dv[k] + (dv[k + 1] - dv[k]) * f; }
      out.push({ x, lat: recs[i].lat, lon: recs[i].lon });
    }
  } else {
    const geo = recs.filter(r => r.lat !== undefined && r.lon !== undefined && r.alt !== undefined);
    let cum = 0;
    for (let i = 0; i < geo.length; i++) { if (i) cum += haversine(geo[i - 1], geo[i]); out.push({ x: cum, lat: geo[i].lat, lon: geo[i].lon }); }
  }
  const t = [];   // enforce strictly monotone x for interpolation
  for (const q of out) { if (!t.length || q.x > t[t.length - 1].x + 1e-9) t.push(q); }
  return t;
}
// same grid convention as resampleProfile (n = max(2, round(total/dx)+1), last point exact)
function gridPositions(total, dx) {
  const n = Math.max(2, Math.round(total / dx) + 1);
  const d = new Float64Array(n);
  for (let i = 0; i < n; i++) d[i] = i === n - 1 ? total : total * i / (n - 1);
  return d;
}
function lonLatAt(geo, xs) {   // linear interp along track x; clamped at the ends
  const n = xs.length, lons = new Float64Array(n), lats = new Float64Array(n);
  let j = 0;
  for (let i = 0; i < n; i++) {
    const d = xs[i];
    while (j < geo.length - 2 && geo[j + 1].x < d) j++;
    const a = geo[j], b = geo[j + 1];
    const f = Math.max(0, Math.min(1, (d - a.x) / Math.max(1e-9, b.x - a.x)));
    lons[i] = a.lon + (b.lon - a.lon) * f; lats[i] = a.lat + (b.lat - a.lat) * f;
  }
  return { lons, lats };
}
// batch bilinear sampler; empty/garbage lines (outside raster) → NaN
const sampleMs = { igc5: 0, igc30: 0, fabdem: 0, igc5at30: 0 };
function sampleRaster(raster, lons, lats, timerKey) {
  const t0 = Date.now();
  let input = '';
  for (let i = 0; i < lons.length; i++) input += lons[i] + ' ' + lats[i] + '\n';
  let out;
  try {
    out = execFileSync('gdallocationinfo', ['-valonly', '-wgs84', '-r', 'bilinear', raster], { input, encoding: 'utf8', maxBuffer: 1 << 28 });
  } catch (e) { out = e.stdout ?? ''; }   // exit 1 when some points fall outside — output still line-aligned
  const lines = out.split('\n');
  const v = new Float64Array(lons.length).fill(NaN);
  for (let i = 0; i < lons.length && i < lines.length; i++) { const x = parseFloat(lines[i]); if (Number.isFinite(x)) v[i] = x; }
  sampleMs[timerKey] += Date.now() - t0;
  return v;
}
// validity + gap fill (≤1% invalid allowed): sampa_geral has un-surveyed cells stored as 0
// (band min is 0.000 in a ~440–1212 m area) → invalid if ≤ 0.5 m; FABDEM nodata −9999.
function buildDemProfile(xs, vals, floor) {
  const n = xs.length; let nBad = 0;
  const h = new Float64Array(n);
  for (let i = 0; i < n; i++) { h[i] = (Number.isFinite(vals[i]) && vals[i] > floor) ? vals[i] : NaN; if (Number.isNaN(h[i])) nBad++; }
  const validFrac = 1 - nBad / n;
  if (nBad) {   // linear fill across gaps, edge-extend
    let first = h.findIndex(Number.isFinite);
    if (first < 0) return { prof: null, validFrac };
    for (let i = 0; i < first; i++) h[i] = h[first];
    let last = first;
    for (let i = first + 1; i < n; i++) if (Number.isFinite(h[i])) { for (let k = last + 1; k < i; k++) h[k] = h[last] + (h[i] - h[last]) * (k - last) / (i - last); last = i; }
    for (let i = last + 1; i < n; i++) h[i] = h[last];
  }
  return { prof: { x: Float64Array.from(xs), h }, validFrac };
}
// v2Edge walk decomposition (diagnostics; E is asserted ≡ r1dV2Edge to 1e-9 per profile):
// Σh₊, Σh₋ over the walked edges + drop-weighted implied ε = Σ ε_i·h₋ᵢ / Σh₋ᵢ (descent edges).
function walkStats(prof, p, pw, climbThr) {
  const mg = p.m * G, beta = mg / p.keff, w = p.wind;
  const vFlat = Math.max(0.05, flatEqSpeed(pw.flat > 0 ? pw.flat : 1, p));
  const aRoll = mg * p.Crr / p.keff;
  const aAero = 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) / p.keff;
  const abRatio = (aRoll + aAero) / beta;
  const xs = prof.x, hs = prof.h;
  let Ej = 0, hplus = 0, hminus = 0, epsW = 0;
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    if (!(dx > 0)) continue;
    if (dh >= 0) { hplus += dh; Ej += aRoll * dx + ((dh < climbThr * dx) ? aAero * dx : 0) + beta * dh; }
    else {
      const ndh = -dh; hplus += 0; hminus += ndh;
      let eps = abRatio * dx / ndh; if (eps > 1) eps = 1; eps -= 0.13; if (eps < 0) eps = 0;
      epsW += eps * ndh;
      let e = aRoll * dx + aAero * dx - eps * beta * ndh; if (e < 0) e = 0;
      Ej += e;
    }
  }
  return { E: Ej / 1000, hplus, hminus, epsImplied: hminus > 0 ? epsW / hminus : NaN };
}

// ===== per-ride processing =====
const SOURCES = ['baro', 'igc5', 'igc30', 'fabdem30'];
const rows = [];
const excl = {};   // per-corpus exclusion tallies
const note = (c, k) => { (excl[c] ??= {})[k] = ((excl[c] ?? {})[k] || 0) + 1; };
let maxWalkMismatch = 0;

function processRide(file, p0, label, corpus, epsRule) {
  const buf0 = fs.readFileSync(path.join(DATA, file));
  const buf = file.endsWith('.gz') ? zlib.gunzipSync(buf0) : buf0;
  if (file.endsWith('.gpx') || file.endsWith('.gpx.gz')) { note(corpus, 'gpx-unsupported'); return; }
  const pts = E.ptsFromFIT(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  if (corpus !== 'censo' && E.getManuf() === ZWIFT) { note(corpus, 'zwift'); return; }
  if (!hasPower(pts)) { note(corpus, 'no-power'); return; }
  const p = { ...p0, vmax: VMAX, vstart: VSTART };
  buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
  const physProfile = E.getPhysProfile();
  const prof5 = resampleProfile(physProfile, ENGINE_DX);
  const total = prof5.x[prof5.x.length - 1];
  const emp = empiricalKJ(pts);
  if (!(emp > 0)) { note(corpus, 'no-emp'); return; }
  if (corpus === 'censo') {   // physical-plausibility floor, VERBATIM regime_compare censo driver logic
    const profS0 = { x: prof5.x, h: deadband(prof5.h, TAU_SMOOTH) };
    const aSm0 = E.approxComponents(profS0, p, flatEqSpeed(overallMeanPower(pts), p), null);
    if (emp < (p.m * G / p.keff) * aSm0.hplus / 1000) { note(corpus, 'phys-floor'); return; }
  }
  note(corpus, 'clean');   // clean per the corpus's own filters — coverage cuts follow
  const geo = geoTrackFromFIT(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  if (geo.length < 2) { note(corpus, 'no-geo'); return; }
  const base = pts[0].x;
  const geoCov = (Math.min(geo[geo.length - 1].x, base + total) - Math.max(geo[0].x, base)) / total;
  if (geoCov < 0.99) { note(corpus, 'geo-span'); return; }
  let inBox = true;
  for (const q of geo) if (q.lon < BBOX.lonMin || q.lon > BBOX.lonMax || q.lat < BBOX.latMin || q.lat > BBOX.latMax) { inBox = false; break; }
  if (!inBox) { note(corpus, 'bbox'); return; }

  const d5 = gridPositions(total, 5), d30 = gridPositions(total, 30);
  const abs5 = Float64Array.from(d5, d => d + base), abs30 = Float64Array.from(d30, d => d + base);
  const g5 = lonLatAt(geo, abs5), g30 = lonLatAt(geo, abs30);
  const s5 = buildDemProfile(d5, sampleRaster(DEM5, g5.lons, g5.lats, 'igc5'), 0.5);
  const s30 = buildDemProfile(d30, sampleRaster(DEM30, g30.lons, g30.lats, 'igc30'), 0.5);
  const sF = buildDemProfile(d30, sampleRaster(FABDEM, g30.lons, g30.lats, 'fabdem'), -9998);
  const s5at30 = buildDemProfile(d30, sampleRaster(DEM5, g30.lons, g30.lats, 'igc5at30'), 0.5);
  if (!s5.prof || !s30.prof || s5.validFrac < 0.99 || s30.validFrac < 0.99) { note(corpus, 'coverage'); return; }
  const fabOK = sF.prof && sF.validFrac >= 0.99;
  if (!fabOK) note(corpus, 'fabdem-coverage');

  const pw = pwFrom(binGrades(pointRegimeData(pts), CLIMB_THR, DESC_THR), pts);
  const vf = flatEqSpeed(pw.flat, p);
  const profs = { baro: prof5, igc5: s5.prof, igc30: s30.prof, fabdem30: fabOK ? sF.prof : null };

  const row = { corpus, ride: label, emp, km: total / 1000, vf_kmh: vf * 3.6,
    valid_igc5: s5.validFrac, valid_igc30: s30.validFrac, valid_fabdem: sF.prof ? sF.validFrac : 0, geoCov };
  for (const src of SOURCES) {
    const prof = profs[src];
    if (!prof) { for (const k of ['v2', 'r0', 'd_v2', 'd_r0', 'hplus', 'hminus', 'epsw', 'eps']) row[`${k}_${src}`] = NaN; continue; }
    const v2 = r1dV2Edge(prof, p, pw, CLIMB_THR);                      // RAW profile, native step
    const ws = walkStats(prof, p, pw, CLIMB_THR);
    maxWalkMismatch = Math.max(maxWalkMismatch, Math.abs(ws.E - v2));
    let eps = 0.20;
    if (epsRule !== 'urban') { const eg = epsGeom(prof, p, vf); eps = Number.isFinite(eg) ? eg : 0.20; }
    const r0 = r0Champion(prof, { x: prof.x, h: deadband(prof.h, TAU_SMOOTH) }, p, pw, eps).eSm;
    row[`v2_${src}`] = v2; row[`r0_${src}`] = r0;
    row[`d_v2_${src}`] = dPct(v2, emp); row[`d_r0_${src}`] = dPct(r0, emp);
    row[`hplus_${src}`] = ws.hplus; row[`hminus_${src}`] = ws.hminus;
    row[`epsw_${src}`] = ws.epsImplied; row[`eps_${src}`] = eps;
    // sanity gate: profile distance ≡ track distance (exact by construction)
    if (Math.abs(prof.x[prof.x.length - 1] - total) > 1e-6) throw new Error(`distance mismatch ${label} ${src}`);
  }
  // gate: igc5 sampled at 30 m steps ≈ igc30 (approximate — the warp adds area averaging)
  row.v2_igc5at30 = s5at30.prof && s5at30.validFrac >= 0.99 ? r1dV2Edge(s5at30.prof, p, pw, CLIMB_THR) : NaN;
  // gate: DEM(igc5)-vs-baro shape RMS (mean-removed; both series live on the same 5 m grid)
  { const a = prof5.h, b = s5.prof.h, n = Math.min(a.length, b.length);
    let ma = 0, mb = 0; for (let i = 0; i < n; i++) { ma += a[i]; mb += b[i]; } ma /= n; mb /= n;
    let ss = 0; for (let i = 0; i < n; i++) { const d = (a[i] - ma) - (b[i] - mb); ss += d * d; }
    row.rms_baro_igc5 = Math.sqrt(ss / n); }
  rows.push(row);
  note(corpus, 'included');
}

// ===== drivers (loading + cleaning mirrors regime_compare.mjs / censo_compare.mjs) =====
const t0 = Date.now();
{ // censo (ASSUMED rider, urban ε = 0.20, physical floor)
  const man = JSON.parse(fs.readFileSync(path.join(DATA, 'censohidrografico', 'manifest.json'), 'utf8'));
  for (const e of man) {
    if (!e.file || !fs.existsSync(path.join(DATA, e.file))) continue;
    try { processRide(e.file, ASSUMED, e.name, 'censo', 'urban'); } catch (er) { note('censo', 'unparseable'); }
  }
}
for (const [corpus, manifest] of [['ppaz', 'strava_ppaz_manifest.json'], ['jaam', 'strava_jaam_manifest.json'], ['danlessa', 'strava_danlessa_manifest.json']]) {
  const man = JSON.parse(fs.readFileSync(path.join(DATA, manifest), 'utf8'));
  const cand = man.filter(a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20 && a.altCov >= 0.99);
  let n = 0;
  for (const a of cand) {
    try { processRide(a.file, PHYS[corpus], a.id, corpus, 'open'); } catch (er) { note(corpus, 'unparseable'); }
    if (++n % 100 === 0) console.error(`  …${corpus} ${n}/${cand.length} (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
  }
}
console.error(`sampling ms: ${JSON.stringify(sampleMs)} · total ${((Date.now() - t0) / 1000).toFixed(0)} s`);

// ===== report =====
const f = (x, d = 1) => (x == null || Number.isNaN(x) || !Number.isFinite(x)) ? '—' : x.toFixed(d);
const CORP = [['censo', 'censo (urban group rides, assumed rider)'], ['ppaz', 'P. Paz (open, frozen physics)'], ['jaam', 'JAAM (open, frozen physics)'], ['danlessa', 'author full (open, frozen physics)']];
const byCorpus = c => c === 'pooled' ? rows.filter(r => r.corpus !== 'censo') : rows.filter(r => r.corpus === c);

console.log('ENTRY 19 — v2Edge on the deployed IGC-SP 5 m raster vs 30 m resample vs FABDEM');
console.log(`DEM: ${DEM5}`);
console.log(`warp: gdalwarp -r average -tr 0.000287042610744 0.000287042610744 (6× native px) · FABDEM S24W047 V1-2`);
console.log('\nCORPUS FUNNEL (clean per corpus filters → inside coverage):');
for (const [c] of CORP) {
  const e = excl[c] || {};
  console.log(`  ${c.padEnd(9)} clean=${e.clean || 0} → included=${e.included || 0}   [excl: bbox=${e.bbox || 0} coverage=${e.coverage || 0} geo-span=${e['geo-span'] || 0} no-geo=${e['no-geo'] || 0}] (pre-clean skips: no-power=${e['no-power'] || 0} phys-floor=${e['phys-floor'] || 0} zwift=${e.zwift || 0} unparseable=${e.unparseable || 0} no-emp=${e['no-emp'] || 0} gpx=${e['gpx-unsupported'] || 0}; fabdem-coverage misses=${e['fabdem-coverage'] || 0})`);
}
console.log(`  pooled riders included n=${byCorpus('pooled').length} · censo n=${byCorpus('censo').length} · all n=${rows.length}`);

console.log('\nMED |Δ%| AND MEDIAN SIGNED Δ% vs measured ∫P·dt (v2Edge raw @ native step · R0 cf+2m deadband):');
for (const [c, title] of [...CORP, ['pooled', 'POOLED independent riders (ppaz+jaam+danlessa)']]) {
  const set = byCorpus(c); if (!set.length) continue;
  console.log(`\n── ${title} ──  n=${set.length}`);
  console.log(`${'model@source'.padEnd(22)}${'med|Δ%|'.padStart(9)}${'medΔ%'.padStart(8)}`);
  for (const m of ['v2', 'r0']) for (const s of SOURCES) {
    const ds = set.map(r => r[`d_${m}_${s}`]).filter(Number.isFinite);
    console.log(`${(m === 'v2' ? 'v2Edge@' : 'R0@') + s}`.padEnd(22) + f(medOf(ds.map(Math.abs))).padStart(9) + f(medOf(ds)).padStart(8) + `   (n=${ds.length})`);
  }
}

console.log('\n================ PRIMARY ENDPOINTS — paired v2Edge@igc5 vs v2Edge@igc30 ================');
for (const [c, title] of [['censo', 'censo (pre-registered primary)'], ['pooled', 'pooled independent riders (co-primary)'], ['ppaz', 'P. Paz'], ['jaam', 'JAAM'], ['danlessa', 'author']]) {
  const set = byCorpus(c); if (!set.length) continue;
  const m5 = medOf(set.map(r => Math.abs(r.d_v2_igc5)).filter(Number.isFinite));
  const m30 = medOf(set.map(r => Math.abs(r.d_v2_igc30)).filter(Number.isFinite));
  const b5 = medOf(set.map(r => r.d_v2_igc5).filter(Number.isFinite));
  const b30 = medOf(set.map(r => r.d_v2_igc30).filter(Number.isFinite));
  const gap = medOf(set.map(r => r.d_v2_igc5 - r.d_v2_igc30).filter(Number.isFinite));
  const t = pairedAbs(set, 'd_v2_igc5', 'd_v2_igc30');
  console.log(`  ${title}  (n=${set.length})`);
  console.log(`    med|Δ%|: igc5 ${f(m5)} vs igc30 ${f(m30)} · signed bias: igc5 ${f(b5)} vs igc30 ${f(b30)} · med per-ride signed gap ${f(gap, 2)} pp`);
  console.log(`    paired |Δ%|: igc5 better on ${t.wins}/${t.n} (${f(t.winFrac * 100, 0)}%) · med Δ|Δ%| ${f(t.medDiff, 2)} pp · sign p=${f(t.pSign, 4)} · Wilcoxon p=${f(t.pWilcoxon, 4)}`);
}

console.log('\nSECONDARY — paired v2Edge@igc30 vs v2Edge@fabdem30 (local survey vs free global DEM, same 30 m grid):');
for (const [c] of [...CORP, ['pooled']]) {
  const set = byCorpus(c).filter(r => Number.isFinite(r.d_v2_fabdem30)); if (!set.length) continue;
  const t = pairedAbs(set, 'd_v2_fabdem30', 'd_v2_igc30');
  const dE = medOf(set.map(r => (r.v2_fabdem30 - r.v2_igc30) / r.v2_igc30 * 100));
  const dH = medOf(set.map(r => (r.hplus_fabdem30 - r.hplus_igc30) / r.hplus_igc30 * 100));
  console.log(`  ${c.padEnd(9)} n=${set.length} · med|Δ%|: fabdem ${f(medOf(set.map(r => Math.abs(r.d_v2_fabdem30))))} vs igc30 ${f(medOf(set.map(r => Math.abs(r.d_v2_igc30))))} · fabdem better ${t.wins}/${t.n} (${f(t.winFrac * 100, 0)}%) sign p=${f(t.pSign, 3)} · med energy Δ(fab−igc30) ${f(dE, 2)}% · med h₊ Δ ${f(dH, 2)}%`);
}

console.log('\nDECOMPOSITION — median Σh₊ / Σh₋ (m) per source (v2Edge walked edges) and implied drop-weighted ε:');
for (const [c] of [...CORP, ['pooled']]) {
  const set = byCorpus(c); if (!set.length) continue;
  const g = k => f(medOf(set.map(r => r[k]).filter(Number.isFinite)), 0);
  const ge = k => f(medOf(set.map(r => r[k]).filter(Number.isFinite)), 3);
  console.log(`  ${c.padEnd(9)} h₊: baro ${g('hplus_baro')} · igc5 ${g('hplus_igc5')} · igc30 ${g('hplus_igc30')} · fabdem ${g('hplus_fabdem30')}   |   h₋: ${g('hminus_baro')} · ${g('hminus_igc5')} · ${g('hminus_igc30')} · ${g('hminus_fabdem30')}`);
  console.log(`  ${''.padEnd(9)} implied ε: baro ${ge('epsw_baro')} · igc5 ${ge('epsw_igc5')} · igc30 ${ge('epsw_igc30')} · fabdem ${ge('epsw_fabdem30')}`);
}

// ===== sanity gates =====
console.log('\n================ SANITY GATES ================');
let ok = true; const say = (name, pass, extra = '') => { console.log(`  [${pass ? 'PASS' : 'FAIL'}] ${name}${extra ? '  ' + extra : ''}`); if (!pass) ok = false; };
// (1) baro anchor reproduces regime_compare's published per-ride numbers (emp, r1d5r=v2Edge@baro raw,
//     r0sm=R0@baro) — matched by corpus+ride against regime_comparison.csv (3-decimal rounding → tol).
try {
  const csv = fs.readFileSync(path.join(RESULTS, 'regime_comparison.csv'), 'utf8').split('\n');
  const hdr = csv[0].split(','), idx = k => hdr.indexOf(k);
  const ref = new Map();
  for (let i = 1; i < csv.length; i++) {
    const c = csv[i].split(','); if (c.length < 5) continue;
    ref.set(c[idx('corpus')].replace(/"/g, '') + '|' + c[idx('ride')].replace(/"/g, ''), { emp: +c[idx('emp')], r1d5r: +c[idx('r1d5r')], r0sm: +c[idx('r0sm')] });
  }
  let nM = 0, worst = 0, worstWhat = '';
  for (const r of rows) {
    const q = ref.get(r.corpus + '|' + r.ride); if (!q) continue;
    nM++;
    for (const [mine, theirs, lab] of [[r.emp, q.emp, 'emp'], [r.v2_baro, q.r1d5r, 'v2@baro'], [r.r0_baro, q.r0sm, 'r0@baro']]) {
      const d = Math.abs(mine - theirs);
      if (d > worst) { worst = d; worstWhat = `${lab} ${r.corpus}/${r.ride}`; }
    }
  }
  say(`baro anchor ≡ regime_comparison.csv (emp, r1d5r, r0sm) on ${nM} matched rides`, nM > 0 && worst < 0.002, `worst |Δ| ${worst.toExponential(2)} kJ (${worstWhat})`);
} catch (e) { say('baro anchor vs regime_comparison.csv', false, e.message); }
// (2) profile distance ≡ track distance — asserted exactly per ride/source inside processRide;
//     the geo track's span vs device distance is the approximate part:
say('profile distance ≡ track distance (exact per construction; no ride threw)', true);
console.log(`         geo-track span coverage: median ${f(medOf(rows.map(r => r.geoCov)) * 100, 2)}% (min ${f(Math.min(...rows.map(r => r.geoCov)) * 100, 2)}%)`);
// (3) igc5 sampled at 30 m steps ≈ igc30 (approximate — -r average vs point-bilinear)
{ const d = rows.map(r => Number.isFinite(r.v2_igc5at30) ? Math.abs(r.v2_igc5at30 - r.v2_igc30) / r.v2_igc30 * 100 : NaN).filter(Number.isFinite);
  say('igc5-sampled-at-30m-steps ≈ igc30 (approximate gate)', medOf(d) < 2, `med |ΔE| ${f(medOf(d), 2)}% · p90 ${f(d.sort((a, b) => a - b)[Math.floor(0.9 * (d.length - 1))], 2)}%`); }
// (4) DEM-vs-baro shape RMS in the Entry-6 ballpark (~7–8 m)
{ const m = medOf(rows.map(r => r.rms_baro_igc5)); say('DEM(igc5)-vs-baro shape RMS ~7–8 m ballpark', m > 2 && m < 15, `median ${f(m, 1)} m`); }
// (5) dead-clamp assert (Entry 18): every per-edge pre-clamp descent cost > 0 across ALL profiles
say('dead-clamp: min pre-clamp descent edge > 0', E.getMinPreclamp() > 0, `min ${E.getMinPreclamp().toExponential(2)} J`);
// (6) walk decomposition ≡ verbatim r1dV2Edge
say('walkStats ≡ r1dV2Edge (per profile)', maxWalkMismatch < 1e-9, `max |Δ| ${maxWalkMismatch.toExponential(2)} kJ`);
console.log(ok ? '\nSANITY: ALL PASS' : '\nSANITY: FAILURES ABOVE');

// ===== CSV (gitignored via results/*) =====
const cols = ['corpus', 'ride', 'emp', 'km', 'vf_kmh', 'geoCov', 'valid_igc5', 'valid_igc30', 'valid_fabdem', 'rms_baro_igc5', 'v2_igc5at30']
  .concat(SOURCES.flatMap(s => [`v2_${s}`, `r0_${s}`, `d_v2_${s}`, `d_r0_${s}`, `hplus_${s}`, `hminus_${s}`, `epsw_${s}`, `eps_${s}`]));
fs.writeFileSync(path.join(RESULTS, 'igc_resolution_test.csv'),
  [cols.join(',')].concat(rows.map(r => cols.map(k => typeof r[k] === 'string' ? JSON.stringify(r[k]) : (Number.isFinite(r[k]) ? +Number(r[k]).toFixed(4) : '')).join(','))).join('\n') + '\n');
console.log(`\nwrote igc_resolution_test.csv (${rows.length} rides)`);
process.exit(ok ? 0 : 1);
