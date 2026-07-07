#!/usr/bin/env node
// ENTRY 20 — goal-driven calibration: can the deployed pipeline hit ±5% error / ±2% bias?
// Pre-registered protocol (journal Entry 20): two deployable levers only —
//   L1 (global): static mask-normalized Gaussian pre-smoothing of the deployed IGC-SP 5 m
//       raster, sigma ∈ {0, 10, 15, 20, 30, 45} m (0 = the original raster), profiles sampled
//       at 5 m arc steps off the smoothed raster (the app keeps its 5 m grid);
//   L2 (per-rider = the app's parameter panel): (CdA ∈ [0.2,0.6], Crr ∈ [0.003,0.015],
//       kSmooth ∈ [0.5,1.0]) fitted per rider on TRAIN; mass FROZEN (74.3/101.7/74.5),
//       rho 1.13, keff 0.98, per-ride P_flat from the ride's own extracted flat power.
// Split: deterministic 50/50 by sha256('entry20:' + rideName) parity (even = train).
// sigma* selected on TRAIN only (min over sigma of the WORST corpus's post-fit train med|Δ%|);
// validation evaluated ONCE at the frozen (sigma*, per-rider params).
// PASS = all three riders' validation med|Δ%| < 5 AND |median signed Δ%| < 2.
// Fallback F1 (runs ONLY if the primary fails): refit with epsOffset as a 4th SHARED
// parameter ∈ [0.05, 0.25] (per-rider CdA/Crr/kSmooth refit around it), re-select sigma,
// single validation eval.
//
// RASTER SMOOTHING (Phase A, goal_smooth_rasters.py, run with /Users/danlessa/conda/bin/python):
// the DEPLOYABLE scheme — sequential per-axis mask-normalized Gaussian passes over a FIXED
// validity mask m = (h > 0.5) (sampa_geral.tif declares no nodata; 0 = un-surveyed): first each
// ROW as corr1d(h·m, w_x)/corr1d(m, w_x) at valid cells (invalid cells stay invalid, excluded,
// never receive a value), then each COLUMN of that intermediate the same way with the SAME mask.
// Kernel w_k = exp(−k²/(2σ_px²)), k = −r..r, r = ceil(3σ_px), normalization = the sum of weights
// over VALID in-window cells only (one rule for borders and holes); per-axis σ_px from the
// geotransform (m/deg = π/180·6371000; px ≈ 5.3196 m lat / 4.8758 m lon at center lat −23.5896°).
// See the python helper's header for the full pinned parameters.
//
// ENGINE REUSE IS BYTE-IDENTICAL BY CONSTRUCTION (Entry 19's discipline): the physics/parse
// engine is extracted at runtime from regime_compare.mjs, and the geo/DEM-sampling machinery
// from igc_resolution_test.mjs (line-level brace-balanced grabs, eval'd — nothing re-typed).
// v2EdgeK below is the ONLY new physics code: r1dV2Edge generalized to (kSmooth, epsOffset)
// exactly per sampasimu app.js readCost(): beta = m·g·kSmooth/keff (kSmooth scales the gravity
// term: climb charge AND descent credit), abRatio stays UN-smoothed = (Crr·m·g + ½ρ·CdA·v_f²)/(m·g)
// (ε is a grade-geometry factor, not an energy one). Asserted ≡ r1dV2Edge to 1e-9 at
// (kSmooth=1, epsOffset=0.13) on every profile.
//
// Corpus = the ppaz/jaam/danlessa Entry-19 coverage sets ONLY (censo excluded by the goal's own
// dataset list). Ride membership is taken from Entry 19's own output (igc_resolution_test.csv,
// counts asserted 277/181/406), and every ride is INDEPENDENTLY re-derived from the FIT file
// (emp must reproduce the CSV emp to 1e-3 kJ; sigma=0 frozen-physics v2EdgeK must reproduce the
// CSV v2_igc5 to 1e-3 kJ — sanity gate 1), so the filters are verified per ride, not re-run.
//
// Phases (A = python, above):
//   B — profile cache: per ride, per sigma ∈ {0,10,15,20,30,45}, resample the GPS track to 5 m
//       arc steps (gridPositions/lonLatAt, verbatim Entry 19) and batch-sample the raster with
//       gdallocationinfo -valonly -wgs84 -r bilinear; validity floor 0.5 m, ≤1% gap fill
//       (buildDemProfile, verbatim). Cached to $SCRATCH/goal_profiles.{bin,meta.json};
//       determinism verified by rebuilding every 40th ride and byte-comparing.
//   C — calibration + validation (runs TWICE; the two report strings must be identical).
//
//   node goal_calibration.mjs        → report on stdout (timings on stderr) +
//                                      goal_calibration.csv (gitignored via *.csv)
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRATCH = '/private/tmp/claude-501/-Users-danlessa-repos-pedalhidro-simujaules/6a419542-bc75-4ec1-aced-8e8de9a58ae3/scratchpad';
const DEM5 = '/Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif';
const SIGMAS = [0, 10, 15, 20, 30, 45];
const rasterFor = sig => sig === 0 ? DEM5 : path.join(SCRATCH, `sampa_geral_sm${sig}m.tif`);
const SMOKE = !!process.env.GOAL_SMOKE;           // debug only: 3 rides/corpus, no count asserts
const EXPECT = { ppaz: 277, jaam: 181, danlessa: 406 };
const CORPORA = ['ppaz', 'jaam', 'danlessa'];

// ===== ENGINE: extracted verbatim at runtime (regime_compare.mjs + igc_resolution_test.mjs) =====
function grabBlock(lines, startRe) {
  const i = lines.findIndex(l => startRe.test(l));
  if (i < 0) throw new Error(`engine grab failed: ${startRe}`);
  const out = []; let depth = 0;
  for (let j = i; j < lines.length; j++) {
    const l = lines[j]; out.push(l);
    for (const ch of l) { if (ch === '{') depth++; else if (ch === '}') depth--; }
    if (depth === 0) break;
  }
  if (depth !== 0) throw new Error(`unbalanced grab: ${startRe}`);
  return out.join('\n');
}
const regimeLines = fs.readFileSync(path.join(HERE, 'regime_compare.mjs'), 'utf8').split('\n');
const igcLines = fs.readFileSync(path.join(HERE, 'igc_resolution_test.mjs'), 'utf8').split('\n');
const REGIME_BLOCKS = [
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
  /^function deadband\(/,
  /^function empiricalKJ\(/,
  /^function overallMeanPower\(/,
  /^function hasPower\(/,
  /^const medOf = /,
  /^let R1D_MIN_PRECLAMP = Infinity;/,
  /^function r1dV2Edge\(/,
  /^function pointRegimeData\(/,
  /^function binGrades\(/,
  /^const pwFrom = /,
  /^const dPct = /,
];
const IGC_BLOCKS = [
  /^function geoTrackFromFIT\(/,
  /^function gridPositions\(/,
  /^function lonLatAt\(/,
  /^function sampleRaster\(/,
  /^function buildDemProfile\(/,
];
const engineSrc = REGIME_BLOCKS.map(re => grabBlock(regimeLines, re)).join('\n')
  + `\nconst sampleMs = { s0: 0, s10: 0, s15: 0, s20: 0, s30: 0, s45: 0 };\n`
  + IGC_BLOCKS.map(re => grabBlock(igcLines, re)).join('\n');
const E = new Function('fs', 'path', 'zlib', 'HERE', 'execFileSync', engineSrc + `
return { haversine, flatEqSpeed, resampleProfile, buildProfile, parseFIT, ptsFromFIT, deadband,
  empiricalKJ, overallMeanPower, hasPower, medOf, r1dV2Edge, pointRegimeData, binGrades, pwFrom,
  dPct, ASSUMED, PHYS, ZWIFT, G, VMAX, VSTART, CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH,
  geoTrackFromFIT, gridPositions, lonLatAt, sampleRaster, buildDemProfile,
  getPhysProfile: () => physProfile, getManuf: () => FIT_MANUF,
  getMinPreclamp: () => R1D_MIN_PRECLAMP, getSampleMs: () => sampleMs };`)(fs, path, zlib, HERE, execFileSync);
const { flatEqSpeed, resampleProfile, buildProfile, ptsFromFIT, empiricalKJ, medOf, r1dV2Edge,
  pointRegimeData, binGrades, pwFrom, dPct, PHYS, G, VMAX, VSTART, CLIMB_THR, DESC_THR,
  ENGINE_DX, geoTrackFromFIT, gridPositions, lonLatAt, sampleRaster, buildDemProfile } = E;

// ===== v2EdgeK — r1dV2Edge generalized to (kSmooth, epsOffset), app.js readCost() convention =====
// kSmooth multiplies the gravity term only (beta = m·g·kSmooth/keff → climb charge AND descent
// credit); abRatio (= α/β at kSmooth 1) stays UN-smoothed; epsOffset replaces the constant 0.13.
// At (1, 0.13) this is r1dV2Edge verbatim (asserted, gate below).
let K_MIN_PRECLAMP = Infinity;
let V2K_HPLUS = 0, V2K_HMINUS = 0;
function v2EdgeK(prof, p, pwFlat, climbThr, kSmooth, epsOffset) {
  const mg = p.m * G, beta = mg * kSmooth / p.keff, w = p.wind;
  const vFlat = Math.max(0.05, flatEqSpeed(pwFlat > 0 ? pwFlat : 1, p));
  const aRoll = mg * p.Crr / p.keff;
  const aAero = 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) / p.keff;
  const abRatio = (aRoll + aAero) / (mg / p.keff);   // un-smoothed: = Crr + ½ρCdA·v_f²/(m·g)
  const xs = prof.x, hs = prof.h;
  let Ej = 0, hplus = 0, hminus = 0;
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    if (!(dx > 0)) continue;
    if (dh >= 0) {
      hplus += dh;
      Ej += aRoll * dx + ((dh < climbThr * dx) ? aAero * dx : 0) + beta * dh;
    } else {
      const ndh = -dh; hminus += ndh;
      let eps = abRatio * dx / ndh;
      if (eps > 1) eps = 1;
      eps -= epsOffset;
      if (eps < 0) eps = 0;
      let e = aRoll * dx + aAero * dx - eps * beta * ndh;
      if (e < K_MIN_PRECLAMP) K_MIN_PRECLAMP = e;
      if (e < 0) e = 0;
      Ej += e;
    }
  }
  V2K_HPLUS = hplus; V2K_HMINUS = hminus;
  return Ej / 1000;
}

// ===== Entry-19 CSV: ride membership + gate-1 reference values =====
function parseCsv(text) {
  const rows = []; let row = [], field = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) { if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false; } else field += c; }
    else if (c === '"') inQ = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); if (row.length > 1 || row[0] !== '') rows.push(row); row = []; field = ''; }
    else if (c !== '\r') field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows;
}
const refCsv = parseCsv(fs.readFileSync(path.join(HERE, 'igc_resolution_test.csv'), 'utf8'));
const refHdr = refCsv[0], refIdx = k => refHdr.indexOf(k);
const csvRides = { ppaz: [], jaam: [], danlessa: [] };
for (let i = 1; i < refCsv.length; i++) {
  const c = refCsv[i], corpus = c[refIdx('corpus')];
  if (!csvRides[corpus]) continue;
  csvRides[corpus].push({ ride: c[refIdx('ride')], emp: +c[refIdx('emp')], v2_igc5: +c[refIdx('v2_igc5')], km: +c[refIdx('km')] });
}
if (SMOKE) for (const c of CORPORA) csvRides[c] = csvRides[c].slice(0, 3);

// ===== PHASE B: profile cache =====
const CACHE_BIN = path.join(SCRATCH, SMOKE ? 'goal_profiles_smoke.bin' : 'goal_profiles.bin');
const CACHE_META = path.join(SCRATCH, SMOKE ? 'goal_profiles_smoke.meta.json' : 'goal_profiles.meta.json');

function buildRideProfiles(corpus, row, file) {
  const buf0 = fs.readFileSync(path.join(HERE, file));
  const buf = file.endsWith('.gz') ? zlib.gunzipSync(buf0) : buf0;
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const pts = ptsFromFIT(ab);
  buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
  const prof5 = resampleProfile(E.getPhysProfile(), ENGINE_DX);
  const total = prof5.x[prof5.x.length - 1];
  const emp = empiricalKJ(pts);
  if (Math.abs(emp - row.emp) > 1e-3) throw new Error(`emp mismatch ${corpus}/${row.ride}: ${emp} vs csv ${row.emp}`);
  const pw = pwFrom(binGrades(pointRegimeData(pts), CLIMB_THR, DESC_THR), pts);
  const geo = geoTrackFromFIT(ab);
  if (geo.length < 2) throw new Error(`no-geo ${corpus}/${row.ride}`);
  const base = pts[0].x;
  const d5 = gridPositions(total, 5);
  const abs5 = Float64Array.from(d5, d => d + base);
  const g5 = lonLatAt(geo, abs5);
  const hs = [], valid = [];
  for (const sig of SIGMAS) {
    const v = sampleRaster(rasterFor(sig), g5.lons, g5.lats, 's' + sig);
    const b = buildDemProfile(d5, v, 0.5);
    if (!b.prof || b.validFrac < 0.99) throw new Error(`coverage ${corpus}/${row.ride} sigma=${sig}: validFrac=${b ? b.validFrac : 'null'}`);
    hs.push(b.prof.h); valid.push(b.validFrac);
  }
  return { corpus, ride: row.ride, file, emp, total, pFlat: pw.flat, n: d5.length, valid, hs };
}

function buildCache() {
  const t0 = Date.now();
  const metaRides = [], chunks = [];
  let off = 0, done = 0, totalRides = CORPORA.reduce((s, c) => s + csvRides[c].length, 0);
  for (const corpus of CORPORA) {
    const man = JSON.parse(fs.readFileSync(path.join(HERE, `strava_${corpus}_manifest.json`), 'utf8'));
    const byId = new Map(man.map(a => [a.id, a.file]));
    for (const row of csvRides[corpus]) {
      const file = byId.get(row.ride);
      if (!file) throw new Error(`no manifest entry for ${corpus}/${row.ride}`);
      const r = buildRideProfiles(corpus, row, file);
      metaRides.push({ corpus: r.corpus, ride: r.ride, file: r.file, emp: r.emp, total: r.total, pFlat: r.pFlat, n: r.n, valid: r.valid, off });
      for (const h of r.hs) { chunks.push(Buffer.from(h.buffer, h.byteOffset, h.length * 8)); }
      off += r.n * SIGMAS.length;
      if (++done % 50 === 0) console.error(`  …cache ${done}/${totalRides} (${((Date.now() - t0) / 1000).toFixed(0)} s, sampleMs=${JSON.stringify(E.getSampleMs())})`);
    }
  }
  const meta = { version: 1, sigmas: SIGMAS, engineDx: ENGINE_DX, validFloor: 0.5, rides: metaRides };
  fs.writeFileSync(CACHE_BIN, Buffer.concat(chunks));
  fs.writeFileSync(CACHE_META, JSON.stringify(meta));
  console.error(`cache built: ${done} rides, ${off} doubles, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  return meta;
}

function loadOrBuildCache() {
  if (fs.existsSync(CACHE_META) && fs.existsSync(CACHE_BIN)) {
    const meta = JSON.parse(fs.readFileSync(CACHE_META, 'utf8'));
    const want = CORPORA.flatMap(c => csvRides[c].map(r => c + '|' + r.ride)).join(';');
    const have = meta.rides.map(r => r.corpus + '|' + r.ride).join(';');
    if (meta.version === 1 && want === have && JSON.stringify(meta.sigmas) === JSON.stringify(SIGMAS)) {
      console.error('cache: reusing existing (membership + sigmas match)');
      return meta;
    }
    console.error('cache: stale — rebuilding');
  }
  return buildCache();
}

const cacheMeta = loadOrBuildCache();
const cacheBuf = fs.readFileSync(CACHE_BIN);
const cacheF64 = new Float64Array(cacheBuf.buffer, cacheBuf.byteOffset, cacheBuf.length / 8);
const binSha = crypto.createHash('sha256').update(cacheBuf).digest('hex');
const metaSha = crypto.createHash('sha256').update(fs.readFileSync(CACHE_META)).digest('hex');

// materialize rides: per ride one x-grid + 6 {x,h} profiles (h = views into the cache buffer)
const rides = cacheMeta.rides.map(mr => {
  const x = gridPositions(mr.total, 5);
  if (x.length !== mr.n) throw new Error(`grid mismatch ${mr.ride}`);
  const profs = SIGMAS.map((s, k) => ({ x, h: cacheF64.subarray(mr.off + k * mr.n, mr.off + (k + 1) * mr.n) }));
  return { ...mr, profs };
});

// cache determinism: rebuild every 40th ride fresh (FIT parse + gdal) and byte-compare
function cacheDeterminismCheck() {
  let checked = 0, bad = 0;
  for (let i = 0; i < rides.length; i += 40) {
    const r = rides[i];
    const row = csvRides[r.corpus].find(q => q.ride === r.ride);
    const fresh = buildRideProfiles(r.corpus, row, r.file);
    if (fresh.emp !== r.emp || fresh.pFlat !== r.pFlat || fresh.total !== r.total || fresh.n !== r.n) bad++;
    else for (let k = 0; k < SIGMAS.length; k++) {
      const a = fresh.hs[k], b = r.profs[k].h;
      for (let j = 0; j < a.length; j++) if (a[j] !== b[j]) { bad++; break; }
    }
    checked++;
  }
  return { checked, bad };
}

// ===== PHASE C: calibration + validation =====
const sha256hex = s => crypto.createHash('sha256').update(s).digest('hex');
const isTrain = ride => BigInt('0x' + sha256hex('entry20:' + ride)) % 2n === 0n;
for (const r of rides) r.split = isTrain(r.ride) ? 'train' : 'val';

const byCorpus = c => rides.filter(r => r.corpus === c);
const trainOf = c => byCorpus(c).filter(r => r.split === 'train');
const valOf = c => byCorpus(c).filter(r => r.split === 'val');

const FROZEN = { CdA: 0.40, Crr: 0.008, kSmooth: 1.0 };
const pOf = (corpus, CdA, Crr) => ({ ...PHYS[corpus], CdA, Crr, vmax: VMAX, vstart: VSTART });

function deltasOf(set, sigIdx, CdA, Crr, kSmooth, epsOff) {
  return set.map(r => dPct(v2EdgeK(r.profs[sigIdx], pOf(r.corpus, CdA, Crr), r.pFlat, CLIMB_THR, kSmooth, epsOff), r.emp));
}
function evalSet(set, sigIdx, CdA, Crr, kSmooth, epsOff) {
  const d = deltasOf(set, sigIdx, CdA, Crr, kSmooth, epsOff);
  return { medAbs: medOf(d.map(Math.abs)), medSigned: medOf(d) };
}
const scoreOf = o => o.medAbs + (Math.abs(o.medSigned) > 1 ? 1000 + 100 * (Math.abs(o.medSigned) - 1) : 0);
const pctl = (xs, q) => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); if (!s.length) return NaN; const k = q * (s.length - 1), lo = Math.floor(k); return lo + 1 < s.length ? s[lo] + (s[lo + 1] - s[lo]) * (k - lo) : s[lo]; };

// Deterministic 3-level nested coarse-to-fine grid: 7(CdA)×7(Crr)×6(kSmooth) per level;
// refinement = ±1 previous step around the best, clipped to the global bounds; strict-<
// improvement in fixed iteration order (no randomness anywhere). Constraint |medΔ%| ≤ 1 as a
// large penalty (scoreOf).
const BOUNDS = { CdA: [0.2, 0.6], Crr: [0.003, 0.015], kSmooth: [0.5, 1.0] };
const NPTS = { CdA: 7, Crr: 7, kSmooth: 6 };
const linspace = (lo, hi, k) => Array.from({ length: k }, (_, i) => lo + (hi - lo) * i / (k - 1));
function fitRider(trainSet, sigIdx, epsOff, levels = 3) {
  let range = { CdA: BOUNDS.CdA.slice(), Crr: BOUNDS.Crr.slice(), kSmooth: BOUNDS.kSmooth.slice() };
  let best = null;
  for (let lvl = 0; lvl < levels; lvl++) {
    const grid = { CdA: linspace(range.CdA[0], range.CdA[1], NPTS.CdA), Crr: linspace(range.Crr[0], range.Crr[1], NPTS.Crr), kSmooth: linspace(range.kSmooth[0], range.kSmooth[1], NPTS.kSmooth) };
    best = null;
    for (const cda of grid.CdA) for (const crr of grid.Crr) for (const ks of grid.kSmooth) {
      const o = evalSet(trainSet, sigIdx, cda, crr, ks, epsOff);
      const s = scoreOf(o);
      if (!best || s < best.score) best = { CdA: cda, Crr: crr, kSmooth: ks, ...o, score: s };
    }
    const step = k => (range[k][1] - range[k][0]) / (NPTS[k] - 1);
    range = Object.fromEntries(['CdA', 'Crr', 'kSmooth'].map(k => [k,
      [Math.max(BOUNDS[k][0], best[k] - step(k)), Math.min(BOUNDS[k][1], best[k] + step(k))]]));
  }
  return best;
}

const f = (x, d = 2) => (x == null || !Number.isFinite(x)) ? '—' : x.toFixed(d);
function summarize(set, sigIdx, prm, epsOff) {
  const d = deltasOf(set, sigIdx, prm.CdA, prm.Crr, prm.kSmooth, epsOff);
  return { n: d.length, medAbs: medOf(d.map(Math.abs)), medSigned: medOf(d), p10: pctl(d, 0.10), p90: pctl(d, 0.90) };
}
const passFail = s => (s.medAbs < 5 && Math.abs(s.medSigned) < 2) ? 'PASS' : 'FAIL';
const sumLine = (tag, s) => `${tag.padEnd(46)} n=${String(s.n).padStart(3)}  med|Δ%|=${f(s.medAbs).padStart(6)}  medΔ%=${f(s.medSigned).padStart(7)}  p10=${f(s.p10).padStart(7)}  p90=${f(s.p90).padStart(7)}  ${passFail(s)}`;

function runPhaseC() {
  K_MIN_PRECLAMP = Infinity;
  const L = [];
  L.push('ENTRY 20 — goal calibration (±5% error / ±2% bias), pre-registered protocol');
  L.push(`corpora (Entry-19 coverage sets): ${CORPORA.map(c => `${c}=${byCorpus(c).length}`).join(' ')}`);
  L.push(`split (sha256 'entry20:'+ride, even=train): ${CORPORA.map(c => `${c} ${trainOf(c).length}/${valOf(c).length}`).join(' · ')}  (train/val)`);
  L.push(`cache: ${path.basename(CACHE_BIN)} sha256=${binSha.slice(0, 16)}… meta sha256=${metaSha.slice(0, 16)}…`);

  // ---- train matrix: per sigma, per rider post-fit (CdA, Crr, kSmooth at epsOffset 0.13) ----
  const fits = {};   // fits[sigIdx][corpus]
  L.push('\nTRAIN MATRIX — post-fit train med|Δ%| / medΔ% (fit: 7×7×6 ×3-level grid, |medΔ%|≤1 penalty):');
  L.push('sigma   ' + CORPORA.map(c => c.padStart(22)).join('') + '   worst med|Δ%|');
  const worstBySig = [];
  for (let si = 0; si < SIGMAS.length; si++) {
    fits[si] = {};
    let worst = -Infinity, row = `σ=${String(SIGMAS[si]).padEnd(4)}`;
    for (const c of CORPORA) {
      const t0 = Date.now();
      const b = fitRider(trainOf(c), si, 0.13);
      fits[si][c] = b;
      console.error(`  fit σ=${SIGMAS[si]} ${c}: ${((Date.now() - t0) / 1000).toFixed(1)} s → CdA=${f(b.CdA, 4)} Crr=${f(b.Crr, 5)} kS=${f(b.kSmooth, 4)} med|Δ%|=${f(b.medAbs)} medΔ%=${f(b.medSigned)}`);
      row += `${f(b.medAbs)} / ${f(b.medSigned)}`.padStart(22);
      worst = Math.max(worst, scoreOf(b));
    }
    worstBySig.push(worst);
    L.push(row + f(worst, 3).padStart(14));
  }
  // ---- sigma* selection on TRAIN only ----
  let sigStarIdx = 0;
  for (let si = 1; si < SIGMAS.length; si++) if (worstBySig[si] < worstBySig[sigStarIdx]) sigStarIdx = si;
  L.push(`\nσ* = ${SIGMAS[sigStarIdx]} m (min worst-corpus post-fit train med|Δ%|, penalty-inclusive)`);
  L.push('fitted params at σ*:');
  for (const c of CORPORA) {
    const b = fits[sigStarIdx][c];
    L.push(`  ${c.padEnd(9)} CdA=${f(b.CdA, 4)}  Crr=${f(b.Crr, 5)}  kSmooth=${f(b.kSmooth, 4)}  (train med|Δ%|=${f(b.medAbs)}, medΔ%=${f(b.medSigned)})`);
  }
  L.push('fitted params at σ=0 (for the σ-ablation below):');
  for (const c of CORPORA) {
    const b = fits[0][c];
    L.push(`  ${c.padEnd(9)} CdA=${f(b.CdA, 4)}  Crr=${f(b.Crr, 5)}  kSmooth=${f(b.kSmooth, 4)}  (train med|Δ%|=${f(b.medAbs)}, medΔ%=${f(b.medSigned)})`);
  }

  // ---- VALIDATION (single frozen eval) ----
  L.push('\nVALIDATION — frozen (σ*, per-rider fitted params), evaluated once:');
  let allPass = true;
  const valSummaries = {};
  for (const c of CORPORA) {
    const s = summarize(valOf(c), sigStarIdx, fits[sigStarIdx][c], 0.13);
    valSummaries[c] = s;
    if (!(s.medAbs < 5 && Math.abs(s.medSigned) < 2)) allPass = false;
    L.push('  ' + sumLine(`${c} @ σ*=${SIGMAS[sigStarIdx]}m calibrated`, s));
  }
  L.push(`  PRIMARY ENDPOINT: ${allPass ? 'PASS (all three riders meet med|Δ%|<5 ∧ |medΔ%|<2)' : 'FAIL'}`);

  // ---- honesty ablations ----
  L.push('\nABLATIONS (validation sets; context, not endpoints):');
  for (const c of CORPORA) L.push('  ' + sumLine(`${c} @ σ=0 calibrated (σ=0-fitted params)`, summarize(valOf(c), 0, fits[0][c], 0.13)));
  for (const c of CORPORA) L.push('  ' + sumLine(`${c} @ σ=0 with σ*-fitted params`, summarize(valOf(c), 0, fits[sigStarIdx][c], 0.13)));
  for (const c of CORPORA) L.push('  ' + sumLine(`${c} @ σ* UNCALIBRATED (frozen physics)`, summarize(valOf(c), sigStarIdx, FROZEN, 0.13)));
  for (const c of CORPORA) L.push('  ' + sumLine(`${c} @ σ=0 UNCALIBRATED (Entry-19 baseline)`, summarize(valOf(c), 0, FROZEN, 0.13)));

  // ---- FALLBACK F1 (only if the primary fails): shared epsOffset as 4th parameter ----
  let f1 = null;
  if (!allPass) {
    L.push('\nFALLBACK F1 — epsOffset as a 4th SHARED parameter ∈ [0.05, 0.25] (per-rider CdA/Crr/kSmooth');
    L.push('refit around it; 1-D coarse-to-fine on epsOffset: 5 pts × 3 levels; inner fits 2-level; re-select σ):');
    let er = [0.05, 0.25], bestE = null;
    for (let lvl = 0; lvl < 3; lvl++) {
      for (const eo of linspace(er[0], er[1], 5)) {
        // reuse cached inner results per (eo, σ) — keyed exactly, deterministic
        let bestSig = null;
        for (let si = 0; si < SIGMAS.length; si++) {
          let worst = -Infinity; const prms = {};
          for (const c of CORPORA) { const b = fitRider(trainOf(c), si, eo, 2); prms[c] = b; worst = Math.max(worst, scoreOf(b)); }
          if (!bestSig || worst < bestSig.worst) bestSig = { si, worst, prms };
        }
        if (!bestE || bestSig.worst < bestE.worst) bestE = { eo, ...bestSig };
        console.error(`  F1 eps=${f(eo, 4)}: best σ=${SIGMAS[bestSig.si]} worst=${f(bestSig.worst, 3)}`);
      }
      const step = (er[1] - er[0]) / 4;
      er = [Math.max(0.05, bestE.eo - step), Math.min(0.25, bestE.eo + step)];
    }
    // full 3-level refit at the chosen (epsOffset, σ), then single validation eval
    const prms = {};
    for (const c of CORPORA) prms[c] = fitRider(trainOf(c), bestE.si, bestE.eo, 3);
    L.push(`  F1 chosen: epsOffset=${f(bestE.eo, 4)}, σ=${SIGMAS[bestE.si]} m`);
    for (const c of CORPORA) L.push(`  ${c.padEnd(9)} CdA=${f(prms[c].CdA, 4)}  Crr=${f(prms[c].Crr, 5)}  kSmooth=${f(prms[c].kSmooth, 4)}  (train med|Δ%|=${f(prms[c].medAbs)}, medΔ%=${f(prms[c].medSigned)})`);
    let f1Pass = true;
    for (const c of CORPORA) {
      const s = summarize(valOf(c), bestE.si, prms[c], bestE.eo);
      if (!(s.medAbs < 5 && Math.abs(s.medSigned) < 2)) f1Pass = false;
      L.push('  ' + sumLine(`F1 ${c} @ σ=${SIGMAS[bestE.si]}m calibrated`, s));
    }
    L.push(`  F1 ENDPOINT: ${f1Pass ? 'PASS' : 'FAIL (F2: honest failure — stop)'}`);
    f1 = { ...bestE, prms, f1Pass };
  }

  return { report: L.join('\n'), sigStarIdx, fits, allPass, f1, minPreclamp: K_MIN_PRECLAMP, valSummaries };
}

// ===== SANITY GATES =====
const gates = [];
const gate = (name, pass, extra = '') => gates.push({ name, pass, extra });

// (2) corpus counts
gate('corpus counts = 277/181/406', SMOKE || CORPORA.every(c => byCorpus(c).length === EXPECT[c]),
  CORPORA.map(c => `${c}=${byCorpus(c).length}`).join(' '));

// (1) σ=0 frozen journal physics reproduces Entry 19's per-ride v2_igc5 (tol 1e-3 kJ; the CSV is
// 4-dp rounded) + v2EdgeK(1, 0.13) ≡ r1dV2Edge on every profile at every σ (tol 1e-9 kJ)
{
  let worstCsv = 0, worstCsvWhat = '', worstEq = 0;
  for (const r of rides) {
    const row = csvRides[r.corpus].find(q => q.ride === r.ride);
    const p = pOf(r.corpus, FROZEN.CdA, FROZEN.Crr);
    for (let si = 0; si < SIGMAS.length; si++) {
      const a = v2EdgeK(r.profs[si], p, r.pFlat, CLIMB_THR, 1.0, 0.13);
      r[`v2fr_s${SIGMAS[si]}`] = a; r[`hplus_s${SIGMAS[si]}`] = V2K_HPLUS;
      const b = r1dV2Edge(r.profs[si], p, { flat: r.pFlat }, CLIMB_THR);
      worstEq = Math.max(worstEq, Math.abs(a - b));
      if (si === 0) { const d = Math.abs(a - row.v2_igc5); if (d > worstCsv) { worstCsv = d; worstCsvWhat = `${r.corpus}/${r.ride}`; } }
    }
  }
  gate('σ=0 frozen physics ≡ Entry 19 v2_igc5 (tol 1e-3 kJ)', worstCsv < 1e-3, `worst |Δ| ${worstCsv.toExponential(2)} kJ (${worstCsvWhat})`);
  gate('v2EdgeK(kS=1, eps0=0.13) ≡ r1dV2Edge on all profiles/σ', worstEq < 1e-9, `max |Δ| ${worstEq.toExponential(2)} kJ`);
}

// (5) smoothing correctness spot check: hilliest ride (max h₊ at σ=0), h₊ monotone ↓ with σ
{
  let hilly = rides[0];
  for (const r of rides) if (r.hplus_s0 > hilly.hplus_s0) hilly = r;
  const hp = SIGMAS.map(s => hilly[`hplus_s${s}`]);
  let mono = true; for (let i = 1; i < hp.length; i++) if (!(hp[i] < hp[i - 1])) mono = false;
  gate('h₊ monotone ↓ with σ on the hilliest ride', mono,
    `${hilly.corpus}/${hilly.ride} (${f(hilly.km ?? hilly.total / 1000, 1)} km): h₊ = ${SIGMAS.map((s, i) => `σ${s}:${f(hp[i], 1)}`).join(' ')}`);
}

// cache determinism (subset rebuild, byte-identical)
{
  const t0 = Date.now();
  const { checked, bad } = cacheDeterminismCheck();
  console.error(`cache determinism subset check: ${checked} rides, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  gate('cache determinism (every-40th-ride rebuild byte-identical)', bad === 0, `${checked} rides rechecked, ${bad} mismatches`);
}

// (4) determinism: full Phase C twice → identical reports
console.error('Phase C run 1…');
const tC1 = Date.now();
const run1 = runPhaseC();
console.error(`Phase C run 1: ${((Date.now() - tC1) / 1000).toFixed(0)} s; run 2…`);
const tC2 = Date.now();
const run2 = runPhaseC();
console.error(`Phase C run 2: ${((Date.now() - tC2) / 1000).toFixed(0)} s`);
gate('determinism: Phase C ×2 → identical reports', run1.report === run2.report,
  `sha256 run1=${sha256hex(run1.report).slice(0, 12)} run2=${sha256hex(run2.report).slice(0, 12)}`);

// (3) dead-clamp: min pre-clamp descent edge across every walked profile at every parameter set
gate('dead-clamp: min pre-clamp descent edge > 0', run1.minPreclamp > 0 && run2.minPreclamp > 0,
  `global min ${run1.minPreclamp.toExponential(3)} J (runs 1≡2: ${run1.minPreclamp === run2.minPreclamp})`);

// ===== output =====
console.log(run1.report);
console.log('\n================ SANITY GATES ================');
let ok = true;
for (const g of gates) { console.log(`  [${g.pass ? 'PASS' : 'FAIL'}] ${g.name}${g.extra ? '  ' + g.extra : ''}`); if (!g.pass) ok = false; }
console.log(ok ? 'SANITY: ALL PASS' : 'SANITY: FAILURES ABOVE');

// per-ride CSV (gitignored via data/activities/*.csv)
{
  const si = run1.sigStarIdx;
  const cols = ['corpus', 'ride', 'split', 'emp', 'km', 'pflat',
    ...SIGMAS.flatMap(s => [`v2fr_s${s}`, `d_fr_s${s}`, `hplus_s${s}`]),
    'pred_cal_sigstar', 'd_cal_sigstar', 'pred_cal_sig0', 'd_cal_sig0'];
  const lines = [cols.join(',')];
  for (const r of rides) {
    const b = run1.fits[si][r.corpus], b0 = run1.fits[0][r.corpus];
    const predS = v2EdgeK(r.profs[si], pOf(r.corpus, b.CdA, b.Crr), r.pFlat, CLIMB_THR, b.kSmooth, 0.13);
    const pred0 = v2EdgeK(r.profs[0], pOf(r.corpus, b0.CdA, b0.Crr), r.pFlat, CLIMB_THR, b0.kSmooth, 0.13);
    const rec = { corpus: r.corpus, ride: r.ride, split: r.split, emp: r.emp, km: r.total / 1000, pflat: r.pFlat,
      pred_cal_sigstar: predS, d_cal_sigstar: dPct(predS, r.emp), pred_cal_sig0: pred0, d_cal_sig0: dPct(pred0, r.emp) };
    for (const s of SIGMAS) { rec[`v2fr_s${s}`] = r[`v2fr_s${s}`]; rec[`d_fr_s${s}`] = dPct(r[`v2fr_s${s}`], r.emp); rec[`hplus_s${s}`] = r[`hplus_s${s}`]; }
    lines.push(cols.map(k => typeof rec[k] === 'string' ? JSON.stringify(rec[k]) : (Number.isFinite(rec[k]) ? +Number(rec[k]).toFixed(4) : '')).join(','));
  }
  fs.writeFileSync(path.join(HERE, 'goal_calibration.csv'), lines.join('\n') + '\n');
  console.log(`\nwrote goal_calibration.csv (${rides.length} rides) · sampleMs=${JSON.stringify(E.getSampleMs())}`);
}
process.exit(ok ? 0 : 1);
