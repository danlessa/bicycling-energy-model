#!/usr/bin/env node
// ENTRY 20 (journal; renumbered from 21 post-hoc) — the resolution gap as a PARAMETER problem: fit the behavioural trio
// (k_s, ε₀, climbThr) as a pure 5 m → 30 m RESOLUTION TRANSFER (stage 1, geometric —
// measured energies NEVER touched), then test on validation whether igc5+trio inherits
// igc30's measured accuracy (stage 2, endpoints E1/E2), per the journal's pre-registration.
//
// STAGE 1 (geometric): fit ONE shared trio over k_s∈[0.6,1.0], ε₀∈[0.0,0.20],
// climbThr∈[0.01,0.04] (deterministic coarse-to-fine 9×11×7 grid + two ±1-step refinements)
// minimizing the EQUAL-WEIGHTED mean over the three rider corpora of the corpus-median of
//   |v2EdgeK(igc5 profile; trio, frozen physics) / v2EdgeK(igc30 profile; DEFAULT constants
//    k_s=1, ε₀=0.13, thr=0.02, frozen physics) − 1|
// over TRAIN rides only (Entry 21's sha256('entry20:'+ride) even=train split, verbatim).
// Censo is NEVER in any fit. Ablations at the same objective: k_s-only, ε₀-only, k_s+ε₀, trio.
//
// STAGE 2 (single frozen eval each, VALIDATION split; censo = all 58, out-of-sample):
//   E1 (gap closure, frozen journal physics): med|Δ%| + median signed Δ% vs measured ∫P·dt for
//       (a) igc5 default (Entry-21 anchor), (b) igc30 default (anchor), (c) igc5+trio.
//       Bridged = (c) within 1.0 pp med|Δ%| AND 1.5 pp bias of (b), per corpus incl. censo.
//   E2 (physics coherence): per-rider (CdA∈[0.2,0.6], Crr∈[0.003,0.015]) fit ONLY (trio +
//       mass frozen) on TRAIN at igc5+trio (min med|Δ%| s.t. |medΔ%|≤1, scoreOf penalty),
//       ONE validation eval per rider vs the Entry-21 gates (<5 ∧ <2); fitted (CdA, Crr)
//       side-by-side with Entry 21's σ=0 fits and the plausible ranges.
//   P1: implied drop-weighted ε at igc5+trio vs igc30-default (+ igc5-default context).
//   P2: fitted k_s vs median per-ride h₊(igc30)/h₊(igc5) per corpus.
//   P4: per-ride ratio v2(igc5)/v2(igc30-default) distribution (median/IQR/p10/p90)
//       before (defaults) and after (trio), per corpus incl. censo.
//
// ENGINE REUSE IS BYTE-IDENTICAL BY CONSTRUCTION (Entries 19/20 discipline): physics/parse
// engine from regime_compare.mjs, geo/DEM sampling from igc_resolution_test.mjs, and the
// generalized walk v2EdgeK + split/percentile/score helpers from goal_calibration.mjs — all
// line-level brace-balanced runtime grabs, eval'd, nothing re-typed. v2EdgeK already takes
// (climbThr, kSmooth, epsOffset) = the trio (kSmooth ≡ k_s: β = m·g·k_s/k_eff scales climb
// charge AND descent credit; abRatio stays UN-smoothed; ε = clamp01(min(1, abRatio·dx/|dh|)
// − ε₀)); v_f = flatEqSpeed(P_flat, physics) — trio-independent at frozen physics.
//
// FAST STAGE-1 EVALUATION (new, harness-only): at frozen physics v2EdgeK decomposes exactly
// (real arithmetic) into
//   E(k_s,ε₀,thr) = base + aAero·Σ_{ascent edges, dh/dx<thr} dx
//                   + k_s·[ (mg/k_eff)·h₊ − Σ_desc max(0, epsr−ε₀)·(mg/k_eff)·|dh| ]
// with per-edge epsr = min(1, abRatio·dx/|dh|) precomputed; sorted-prefix/suffix sums give
// O(log n) per (ride, combo). The descent clamp is PROVABLY dead on the whole search box:
// for epsr<1 edges e = C·(1−k_s) + k_s·ε₀·W ≥ 0 and for clamped edges e = C − k_s(1−ε₀)·W
// ≥ W·(1−k_s(1−ε₀)) ≥ 0 (k_s≤1, ε₀≥0; C=(aRoll+aAero)·dx ≥ W=(mg/keff)·|dh| when clamped),
// with equality ONLY at the degenerate corner (k_s=1, ε₀=0) — that corner IS on the coarse
// grid, so its exact min pre-clamp is measured by a verbatim corner walk; per-edge e is
// monotone ↓ in k_s and ↑ in ε₀, so the corner min bounds every other evaluated combo from
// below. The decomposition is asserted ≡ verbatim v2EdgeK at every FITTED/REPORTED parameter
// set; every headline number is a verbatim v2EdgeK walk (K_MIN_PRECLAMP-tracked).
//
// DATA: Entry 21's profile cache (goal_profiles.{bin,meta.json}; σ=0 = the unsmoothed igc5
// profile at 5 m steps) for the 864 rider rides, plus a SUPPLEMENTARY cache built here
// (scale_trio_profiles.{bin,meta.json} in the session scratch dir): igc30 profiles (30 m arc
// steps off Entry 19's sampa_geral_30m.tif 6×-average warp) for all 864 rider rides + the 58
// Entry-19 censo rides, and igc5 profiles (5 m steps off sampa_geral.tif) for the censo rides.
// Censo membership/emp/P_flat reproduce Entry 19's censo pipeline verbatim (ASSUMED rider,
// phys-floor, bbox/coverage filters); sampling = gdallocationinfo -valonly -wgs84 -r bilinear,
// validity floor 0.5 m, ≤1% linear gap fill (buildDemProfile, verbatim).
//
// SANITY GATES: rider igc5 σ=0 frozen ≡ Entry 19 CSV v2_igc5 (Entry 21's gate redux); rider
// igc30 frozen ≡ CSV v2_igc30 (validates the new cache); censo igc5/igc30 frozen ≡ CSV (the
// pre-registered censo reproduction gate); censo emp ≡ CSV; Entry 21's σ=0 uncalibrated
// validation numbers (8.53/2.64/14.84) reproduced; walkStatsK ≡ v2EdgeK; decomposition ≡
// verbatim at fitted sets; dead-clamp; supplementary-cache subset determinism (every 40th
// ride rebuilt fresh, byte-identical); full analysis run TWICE → byte-identical report+CSV.
//
//   node scale_trio.mjs        → report on stdout (timings stderr) + scale_trio.csv
//                                (gitignored via data/activities/*.csv)
//   SCALE_SMOKE=1 node scale_trio.mjs   → debug: 3 rides/corpus, count/number gates skipped
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRATCH = '/private/tmp/claude-501/-Users-danlessa-repos-pedalhidro-simujaules/6a419542-bc75-4ec1-aced-8e8de9a58ae3/scratchpad';
const DEM5 = '/Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif';
const DEM30 = path.join(SCRATCH, 'sampa_geral_30m.tif');
const GOAL_BIN = path.join(SCRATCH, 'goal_profiles.bin');
const GOAL_META = path.join(SCRATCH, 'goal_profiles.meta.json');
const SMOKE = !!process.env.SCALE_SMOKE;
const SUPP_BIN = path.join(SCRATCH, SMOKE ? 'scale_trio_profiles_smoke.bin' : 'scale_trio_profiles.bin');
const SUPP_META = path.join(SCRATCH, SMOKE ? 'scale_trio_profiles_smoke.meta.json' : 'scale_trio_profiles.meta.json');
const EXPECT = { ppaz: 277, jaam: 181, danlessa: 406, censo: 58 };
const CORPORA = ['ppaz', 'jaam', 'danlessa'];               // fit corpora (censo NEVER fitted)
const ALL_CORP = ['ppaz', 'jaam', 'danlessa', 'censo'];
const DEFAULTS = { kS: 1.0, eps0: 0.13, thr: 0.02 };        // the deployed/journal constants
const SPACE = { kS: [0.6, 1.0, 9], eps0: [0.0, 0.20, 11], thr: [0.01, 0.04, 7] };  // lo, hi, npts
const PHYS_BOUNDS = { CdA: [0.2, 0.6], Crr: [0.003, 0.015] };  // E2 per-rider fit
const PHYS_NPTS = { CdA: 7, Crr: 7 };
// Entry 21 anchors (journal): σ=0 uncalibrated VALIDATION med|Δ%| + the σ=0-fitted per-rider
// physics (for the E2 side-by-side; from Entry 21's run at σ=0, supplied by the work order).
const E20_SIGMA0_UNCAL_VAL = { ppaz: 8.53, jaam: 2.64, danlessa: 14.84 };
const E20_SIGMA0_FITS = { ppaz: { CdA: 0.2259, Crr: 0.01344 }, jaam: { CdA: 0.5519, Crr: 0.00433 }, danlessa: { CdA: 0.4148, Crr: 0.00478 } };
const PLAUSIBLE = { CdA: [0.25, 0.45], Crr: [0.004, 0.012] };

// ===== ENGINE: extracted verbatim at runtime (regime_compare + igc_resolution_test + goal_calibration) =====
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
const goalLines = fs.readFileSync(path.join(HERE, 'goal_calibration.mjs'), 'utf8').split('\n');
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
  /^const BBOX = /,
  /^function geoTrackFromFIT\(/,
  /^function gridPositions\(/,
  /^function lonLatAt\(/,
  /^function sampleRaster\(/,
  /^function buildDemProfile\(/,
];
const GOAL_BLOCKS = [
  /^let K_MIN_PRECLAMP = Infinity;/,
  /^let V2K_HPLUS = 0, V2K_HMINUS = 0;/,
  /^function v2EdgeK\(/,
  /^function parseCsv\(/,
  /^const sha256hex = /,
  /^const isTrain = /,
  /^const pctl = /,
  /^const scoreOf = /,
];
const engineSrc = REGIME_BLOCKS.map(re => grabBlock(regimeLines, re)).join('\n')
  + `\nconst sampleMs = { r5: 0, r30: 0 };\n`
  + IGC_BLOCKS.map(re => grabBlock(igcLines, re)).join('\n') + '\n'
  + GOAL_BLOCKS.map(re => grabBlock(goalLines, re)).join('\n');
const E = new Function('fs', 'path', 'zlib', 'HERE', 'execFileSync', 'crypto', engineSrc + `
return { haversine, flatEqSpeed, resampleProfile, approxComponents, buildProfile, parseFIT,
  ptsFromFIT, deadband, empiricalKJ, overallMeanPower, hasPower, medOf, r1dV2Edge,
  pointRegimeData, binGrades, pwFrom, dPct, ASSUMED, PHYS, ZWIFT, G, VMAX, VSTART, CLIMB_THR,
  DESC_THR, ENGINE_DX, TAU_SMOOTH, BBOX, geoTrackFromFIT, gridPositions, lonLatAt, sampleRaster,
  buildDemProfile, v2EdgeK, parseCsv, sha256hex, isTrain, pctl, scoreOf,
  getPhysProfile: () => physProfile, getManuf: () => FIT_MANUF,
  getKMin: () => K_MIN_PRECLAMP, setKMin: v => { K_MIN_PRECLAMP = v; },
  getHplus: () => V2K_HPLUS, getHminus: () => V2K_HMINUS,
  getR1dMin: () => R1D_MIN_PRECLAMP, getSampleMs: () => sampleMs };`)(fs, path, zlib, HERE, execFileSync, crypto);
const { flatEqSpeed, resampleProfile, buildProfile, ptsFromFIT, deadband, empiricalKJ,
  overallMeanPower, hasPower, medOf, r1dV2Edge, pointRegimeData, binGrades, pwFrom, dPct,
  ASSUMED, PHYS, G, VMAX, VSTART, CLIMB_THR, DESC_THR, ENGINE_DX, TAU_SMOOTH, BBOX,
  geoTrackFromFIT, gridPositions, lonLatAt, sampleRaster, buildDemProfile, v2EdgeK, parseCsv,
  sha256hex, isTrain, pctl, scoreOf } = E;

const FROZEN = { CdA: 0.40, Crr: 0.008 };   // journal frozen physics (≡ ASSUMED CdA/Crr)
const pOf = (corpus, CdA, Crr) => corpus === 'censo'
  ? { ...ASSUMED, CdA, Crr, vmax: VMAX, vstart: VSTART }
  : { ...PHYS[corpus], CdA, Crr, vmax: VMAX, vstart: VSTART };
const pFrozen = corpus => pOf(corpus, FROZEN.CdA, FROZEN.Crr);
const f = (x, d = 2) => (x == null || !Number.isFinite(x)) ? '—' : x.toFixed(d);
const linspace = (lo, hi, k) => k === 1 ? [lo] : Array.from({ length: k }, (_, i) => lo + (hi - lo) * i / (k - 1));

// walkStatsK — diagnostics mirror of v2EdgeK (same trio generalization) that also accumulates
// the drop-weighted implied ε; E asserted ≡ v2EdgeK per call (gate).
let WS_MAX_MISMATCH = 0;
function walkStatsK(prof, p, pwFlat, climbThr, kSmooth, epsOffset) {
  const mg = p.m * G, beta = mg * kSmooth / p.keff, w = p.wind;
  const vFlat = Math.max(0.05, flatEqSpeed(pwFlat > 0 ? pwFlat : 1, p));
  const aRoll = mg * p.Crr / p.keff;
  const aAero = 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) / p.keff;
  const abRatio = (aRoll + aAero) / (mg / p.keff);
  const xs = prof.x, hs = prof.h;
  let Ej = 0, hplus = 0, hminus = 0, epsW = 0;
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
      epsW += eps * ndh;
      let e = aRoll * dx + aAero * dx - eps * beta * ndh;
      if (e < 0) e = 0;
      Ej += e;
    }
  }
  const Ekj = Ej / 1000;
  const ref = v2EdgeK(prof, p, pwFlat, climbThr, kSmooth, epsOffset);
  WS_MAX_MISMATCH = Math.max(WS_MAX_MISMATCH, Math.abs(Ekj - ref));
  return { E: Ekj, hplus, hminus, epsImplied: hminus > 0 ? epsW / hminus : NaN };
}

// ===== Entry-19 CSV: membership + reference values (riders AND censo) =====
const refCsv = parseCsv(fs.readFileSync(path.join(HERE, 'igc_resolution_test.csv'), 'utf8'));
const refHdr = refCsv[0], refIdx = k => refHdr.indexOf(k);
const csvRides = { ppaz: [], jaam: [], danlessa: [], censo: [] };
for (let i = 1; i < refCsv.length; i++) {
  const c = refCsv[i], corpus = c[refIdx('corpus')];
  if (!csvRides[corpus]) continue;
  csvRides[corpus].push({ ride: c[refIdx('ride')], emp: +c[refIdx('emp')], v2_igc5: +c[refIdx('v2_igc5')], v2_igc30: +c[refIdx('v2_igc30')], km: +c[refIdx('km')] });
}
if (SMOKE) for (const c of ALL_CORP) csvRides[c] = csvRides[c].slice(0, 3);

// ===== Entry-21 goal cache (rider igc5 σ=0 profiles + emp/pFlat/total) =====
const gMeta = JSON.parse(fs.readFileSync(GOAL_META, 'utf8'));
if (!SMOKE) {
  const want = CORPORA.flatMap(c => csvRides[c].map(r => c + '|' + r.ride)).join(';');
  const have = gMeta.rides.map(r => r.corpus + '|' + r.ride).join(';');
  if (want !== have) throw new Error('goal_profiles cache membership does not match Entry-19 CSV rider sets — rebuild it with goal_calibration.mjs first');
  if (gMeta.version !== 1 || gMeta.sigmas[0] !== 0 || gMeta.engineDx !== 5) throw new Error('unexpected goal cache format');
}
const gBuf = fs.readFileSync(GOAL_BIN);
const gF64 = new Float64Array(gBuf.buffer, gBuf.byteOffset, gBuf.length / 8);
const gByKey = new Map(gMeta.rides.map(r => [r.corpus + '|' + r.ride, r]));
const NSIG = gMeta.sigmas.length;

// ===== raster prep (idempotent; Entry 19's recipe) =====
fs.mkdirSync(SCRATCH, { recursive: true });
if (!fs.existsSync(DEM30)) {
  console.error('creating 30 m warp (Entry 19 recipe)…');
  execFileSync('gdalwarp', ['-r', 'average', '-tr', '0.000287042610744', '0.000287042610744', DEM5, DEM30], { stdio: ['ignore', 'ignore', 'inherit'] });
}

// ===== SUPPLEMENTARY CACHE: rider igc30 + censo igc5/igc30 =====
function buildRiderSupp(corpus, ride) {
  const mr = gByKey.get(corpus + '|' + ride);
  if (!mr) throw new Error(`no goal-cache entry for ${corpus}/${ride}`);
  const buf0 = fs.readFileSync(path.join(HERE, mr.file));
  const buf = mr.file.endsWith('.gz') ? zlib.gunzipSync(buf0) : buf0;
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const pts = ptsFromFIT(ab);
  buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
  const prof5 = resampleProfile(E.getPhysProfile(), ENGINE_DX);
  const total = prof5.x[prof5.x.length - 1];
  const emp = empiricalKJ(pts);
  const pFlat = pwFrom(binGrades(pointRegimeData(pts), CLIMB_THR, DESC_THR), pts).flat;
  if (emp !== mr.emp || total !== mr.total || pFlat !== mr.pFlat) throw new Error(`goal-meta mismatch ${corpus}/${ride}: emp ${emp} vs ${mr.emp}, total ${total} vs ${mr.total}, pFlat ${pFlat} vs ${mr.pFlat}`);
  const geo = geoTrackFromFIT(ab);
  if (geo.length < 2) throw new Error(`no-geo ${corpus}/${ride}`);
  const base = pts[0].x;
  const d30 = gridPositions(total, 30);
  const abs30 = Float64Array.from(d30, d => d + base);
  const g30 = lonLatAt(geo, abs30);
  const b = buildDemProfile(d30, sampleRaster(DEM30, g30.lons, g30.lats, 'r30'), 0.5);
  if (!b.prof || b.validFrac < 0.99) throw new Error(`igc30 coverage ${corpus}/${ride}: ${b.validFrac}`);
  return { corpus, ride, file: mr.file, emp, total, pFlat, n5: 0, n30: d30.length, h5: null, h30: b.prof.h };
}

// Entry 19's censo pipeline, filters verbatim (ASSUMED rider, urban corpus: no zwift skip,
// phys-floor on, bbox + geo-span + igc5/igc30 coverage cuts). Returns null on any exclusion.
function processCenso(entry) {
  const p = { ...ASSUMED, vmax: VMAX, vstart: VSTART };
  if (entry.file.endsWith('.gpx') || entry.file.endsWith('.gpx.gz')) return null;
  const buf0 = fs.readFileSync(path.join(HERE, entry.file));
  const buf = entry.file.endsWith('.gz') ? zlib.gunzipSync(buf0) : buf0;
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const pts = ptsFromFIT(ab);
  if (!hasPower(pts)) return null;
  buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
  const prof5 = resampleProfile(E.getPhysProfile(), ENGINE_DX);
  const total = prof5.x[prof5.x.length - 1];
  const emp = empiricalKJ(pts);
  if (!(emp > 0)) return null;
  { // physical-plausibility floor, VERBATIM Entry 19 censo logic
    const profS0 = { x: prof5.x, h: deadband(prof5.h, TAU_SMOOTH) };
    const aSm0 = E.approxComponents(profS0, p, flatEqSpeed(overallMeanPower(pts), p), null);
    if (emp < (p.m * G / p.keff) * aSm0.hplus / 1000) return null;
  }
  const geo = geoTrackFromFIT(ab);
  if (geo.length < 2) return null;
  const base = pts[0].x;
  const geoCov = (Math.min(geo[geo.length - 1].x, base + total) - Math.max(geo[0].x, base)) / total;
  if (geoCov < 0.99) return null;
  for (const q of geo) if (q.lon < BBOX.lonMin || q.lon > BBOX.lonMax || q.lat < BBOX.latMin || q.lat > BBOX.latMax) return null;
  const d5 = gridPositions(total, 5), d30 = gridPositions(total, 30);
  const abs5 = Float64Array.from(d5, d => d + base), abs30 = Float64Array.from(d30, d => d + base);
  const g5 = lonLatAt(geo, abs5), g30 = lonLatAt(geo, abs30);
  const s5 = buildDemProfile(d5, sampleRaster(DEM5, g5.lons, g5.lats, 'r5'), 0.5);
  const s30 = buildDemProfile(d30, sampleRaster(DEM30, g30.lons, g30.lats, 'r30'), 0.5);
  if (!s5.prof || !s30.prof || s5.validFrac < 0.99 || s30.validFrac < 0.99) return null;
  const pFlat = pwFrom(binGrades(pointRegimeData(pts), CLIMB_THR, DESC_THR), pts).flat;
  return { corpus: 'censo', ride: entry.name, file: entry.file, emp, total, pFlat, n5: d5.length, n30: d30.length, h5: s5.prof.h, h30: s30.prof.h };
}

function buildSuppCache() {
  const t0 = Date.now();
  const recs = [];
  let done = 0;
  const totalRider = CORPORA.reduce((s, c) => s + csvRides[c].length, 0);
  for (const corpus of CORPORA) for (const row of csvRides[corpus]) {
    recs.push(buildRiderSupp(corpus, row.ride));
    if (++done % 50 === 0) console.error(`  …supp cache riders ${done}/${totalRider} (${((Date.now() - t0) / 1000).toFixed(0)} s, sampleMs=${JSON.stringify(E.getSampleMs())})`);
  }
  // censo: full pipeline over the manifest (membership DERIVED, then asserted vs the CSV)
  const man = JSON.parse(fs.readFileSync(path.join(HERE, 'censohidrografico', 'manifest.json'), 'utf8'));
  const wantNames = new Set(csvRides.censo.map(r => r.ride));
  for (const e of man) {
    if (!e.file || !fs.existsSync(path.join(HERE, e.file))) continue;
    if (SMOKE && !wantNames.has(e.name)) continue;
    let r = null;
    try { r = processCenso(e); } catch { /* unparseable — Entry 19 skipped these */ }
    if (r) recs.push(r);
  }
  const censoGot = recs.filter(r => r.corpus === 'censo');
  const gotNames = censoGot.map(r => r.ride).sort();
  const wantSorted = [...wantNames].sort();
  if (JSON.stringify(gotNames) !== JSON.stringify(wantSorted)) {
    throw new Error(`censo membership mismatch: pipeline included [${gotNames.join('; ')}] vs CSV [${wantSorted.join('; ')}]`);
  }
  // serialize
  const metaRides = [], chunks = [];
  let off = 0;
  for (const r of recs) {
    metaRides.push({ corpus: r.corpus, ride: r.ride, file: r.file, emp: r.emp, total: r.total, pFlat: r.pFlat, n5: r.n5, n30: r.n30, off });
    if (r.n5) chunks.push(Buffer.from(r.h5.buffer, r.h5.byteOffset, r.n5 * 8));
    chunks.push(Buffer.from(r.h30.buffer, r.h30.byteOffset, r.n30 * 8));
    off += r.n5 + r.n30;
  }
  const membership = CORPORA.flatMap(c => csvRides[c].map(r => c + '|' + r.ride)).join(';') + '#' + wantSorted.join(';');
  const meta = { version: 1, membership, rides: metaRides };
  fs.writeFileSync(SUPP_BIN, Buffer.concat(chunks));
  fs.writeFileSync(SUPP_META, JSON.stringify(meta));
  console.error(`supp cache built: ${metaRides.length} rides, ${off} doubles, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  return meta;
}

function loadOrBuildSupp() {
  const membership = CORPORA.flatMap(c => csvRides[c].map(r => c + '|' + r.ride)).join(';') + '#' + csvRides.censo.map(r => r.ride).sort().join(';');
  if (fs.existsSync(SUPP_META) && fs.existsSync(SUPP_BIN)) {
    const meta = JSON.parse(fs.readFileSync(SUPP_META, 'utf8'));
    if (meta.version === 1 && meta.membership === membership) {
      console.error('supp cache: reusing existing (membership matches)');
      return meta;
    }
    console.error('supp cache: stale — rebuilding');
  }
  return buildSuppCache();
}

const suppMeta = loadOrBuildSupp();
const sBuf = fs.readFileSync(SUPP_BIN);
const sF64 = new Float64Array(sBuf.buffer, sBuf.byteOffset, sBuf.length / 8);
const suppByKey = new Map(suppMeta.rides.map(r => [r.corpus + '|' + r.ride, r]));
const gBinSha = crypto.createHash('sha256').update(gBuf).digest('hex');
const sBinSha = crypto.createHash('sha256').update(sBuf).digest('hex');

// ===== materialize rides =====
const rides = [];
for (const corpus of ALL_CORP) for (const row of csvRides[corpus]) {
  const sr = suppByKey.get(corpus + '|' + row.ride);
  if (!sr) throw new Error(`supp cache missing ${corpus}/${row.ride}`);
  let prof5;
  if (corpus === 'censo') {
    prof5 = { x: gridPositions(sr.total, 5), h: sF64.subarray(sr.off, sr.off + sr.n5) };
  } else {
    const mr = gByKey.get(corpus + '|' + row.ride);
    if (!mr) throw new Error(`goal cache missing ${corpus}/${row.ride}`);
    if (mr.total !== sr.total || mr.emp !== sr.emp || mr.pFlat !== sr.pFlat) throw new Error(`goal/supp meta drift ${corpus}/${row.ride}`);
    prof5 = { x: gridPositions(mr.total, 5), h: gF64.subarray(mr.off, mr.off + mr.n) };  // σ=0 slice
  }
  const prof30 = { x: gridPositions(sr.total, 30), h: sF64.subarray(sr.off + sr.n5, sr.off + sr.n5 + sr.n30) };
  if (prof5.x.length !== prof5.h.length || prof30.x.length !== sr.n30) throw new Error(`grid mismatch ${corpus}/${row.ride}`);
  rides.push({ corpus, ride: row.ride, split: corpus === 'censo' ? 'censo' : (isTrain(row.ride) ? 'train' : 'val'),
    emp: sr.emp, pFlat: sr.pFlat, total: sr.total, csv: row, prof5, prof30 });
}
const byCorpus = c => rides.filter(r => r.corpus === c);
const trainOf = c => byCorpus(c).filter(r => r.split === 'train');
const valOf = c => byCorpus(c).filter(r => r.split === 'val');

// supp-cache determinism: rebuild every 40th supp ride fresh (FIT parse + gdal) and compare
function suppDeterminismCheck() {
  const man = JSON.parse(fs.readFileSync(path.join(HERE, 'censohidrografico', 'manifest.json'), 'utf8'));
  let checked = 0, bad = 0;
  for (let i = 0; i < suppMeta.rides.length; i += 40) {
    const mr = suppMeta.rides[i];
    let fresh;
    if (mr.corpus === 'censo') {
      const entry = man.find(e => e.file === mr.file && e.name === mr.ride);
      fresh = entry ? processCenso(entry) : null;
    } else fresh = buildRiderSupp(mr.corpus, mr.ride);
    if (!fresh || fresh.emp !== mr.emp || fresh.pFlat !== mr.pFlat || fresh.total !== mr.total || fresh.n5 !== mr.n5 || fresh.n30 !== mr.n30) { bad++; checked++; continue; }
    const stored5 = sF64.subarray(mr.off, mr.off + mr.n5), stored30 = sF64.subarray(mr.off + mr.n5, mr.off + mr.n5 + mr.n30);
    let ok = true;
    for (let j = 0; j < mr.n5; j++) if (fresh.h5[j] !== stored5[j]) { ok = false; break; }
    if (ok) for (let j = 0; j < mr.n30; j++) if (fresh.h30[j] !== stored30[j]) { ok = false; break; }
    if (!ok) bad++;
    checked++;
  }
  return { checked, bad };
}

// ===== STAGE-1 machinery: exact decomposition of v2EdgeK at frozen physics =====
function decompose(prof, p, pwFlat) {
  const mg = p.m * G, mgk = mg / p.keff, w = p.wind;
  const vFlat = Math.max(0.05, flatEqSpeed(pwFlat > 0 ? pwFlat : 1, p));
  const aRoll = mg * p.Crr / p.keff;
  const aAero = 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) / p.keff;
  const abRatio = (aRoll + aAero) / mgk;
  const xs = prof.x, hs = prof.h;
  let base = 0, grav = 0;
  const ascG = [], ascDx = [], dEps = [], dW = [];
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    if (!(dx > 0)) continue;
    if (dh >= 0) {
      base += aRoll * dx;
      grav += dh;
      ascG.push(dh / dx); ascDx.push(dx);
    } else {
      base += aRoll * dx + aAero * dx;
      const ndh = -dh;
      let eps = abRatio * dx / ndh;
      if (eps > 1) eps = 1;
      dEps.push(eps); dW.push(mgk * ndh);
    }
  }
  // ascent aero: sorted grades + prefix aero-work
  const ai = ascG.map((_, i) => i).sort((a, b) => ascG[a] - ascG[b]);
  const gArr = new Float64Array(ai.length), prefAero = new Float64Array(ai.length + 1);
  for (let k = 0; k < ai.length; k++) { gArr[k] = ascG[ai[k]]; prefAero[k + 1] = prefAero[k] + aAero * ascDx[ai[k]]; }
  // descent credit: sorted epsr + suffix sums of W and epsr·W
  const di = dEps.map((_, i) => i).sort((a, b) => dEps[a] - dEps[b]);
  const eArr = new Float64Array(di.length), sufW = new Float64Array(di.length + 1), sufEW = new Float64Array(di.length + 1);
  for (let k = di.length - 1; k >= 0; k--) {
    eArr[k] = dEps[di[k]];
    sufW[k] = sufW[k + 1] + dW[di[k]];
    sufEW[k] = sufEW[k + 1] + dEps[di[k]] * dW[di[k]];
  }
  return { base, grav: mgk * grav, gArr, prefAero, eArr, sufW, sufEW };
}
const lowerBound = (a, x) => { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] < x) lo = m + 1; else hi = m; } return lo; };
const upperBound = (a, x) => { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] <= x) lo = m + 1; else hi = m; } return lo; };
function decEval(dec, kS, eps0, thr) {
  const ia = lowerBound(dec.gArr, thr);                     // ascent edges with grade < thr get aero
  const id = upperBound(dec.eArr, eps0);                    // descent edges with epsr > eps0 give credit
  const credit = dec.sufEW[id] - eps0 * dec.sufW[id];
  return (dec.base + dec.prefAero[ia] + kS * (dec.grav - credit)) / 1000;
}

// deterministic coarse-to-fine grid fit (3 levels; ±1-step refinement clipped to bounds;
// strict-< improvement in fixed kS→eps0→thr order)
function fitStage1(freeDims, objective) {
  const range = {};
  for (const d of freeDims) range[d] = [SPACE[d][0], SPACE[d][1]];
  let best = null;
  for (let lvl = 0; lvl < 3; lvl++) {
    const grids = {};
    for (const d of ['kS', 'eps0', 'thr']) grids[d] = freeDims.includes(d) ? linspace(range[d][0], range[d][1], SPACE[d][2]) : [DEFAULTS[d]];
    best = null;
    for (const kS of grids.kS) for (const eps0 of grids.eps0) for (const thr of grids.thr) {
      const o = objective(kS, eps0, thr);
      if (!best || o < best.obj) best = { kS, eps0, thr, obj: o };
    }
    for (const d of freeDims) {
      const step = (range[d][1] - range[d][0]) / (SPACE[d][2] - 1);
      range[d] = [Math.max(SPACE[d][0], best[d] - step), Math.min(SPACE[d][1], best[d] + step)];
    }
  }
  return best;
}

// E2: per-rider (CdA, Crr) fit at igc5+trio (goal_calibration's fitRider minus kSmooth; the
// trio owns kS/eps0/thr; verbatim v2EdgeK inside — K_MIN_PRECLAMP-tracked on every combo)
function fitPhys(trainSet, trio) {
  let range = { CdA: PHYS_BOUNDS.CdA.slice(), Crr: PHYS_BOUNDS.Crr.slice() };
  let best = null;
  for (let lvl = 0; lvl < 3; lvl++) {
    const grid = { CdA: linspace(range.CdA[0], range.CdA[1], PHYS_NPTS.CdA), Crr: linspace(range.Crr[0], range.Crr[1], PHYS_NPTS.Crr) };
    best = null;
    for (const cda of grid.CdA) for (const crr of grid.Crr) {
      const d = trainSet.map(r => dPct(v2EdgeK(r.prof5, pOf(r.corpus, cda, crr), r.pFlat, trio.thr, trio.kS, trio.eps0), r.emp));
      const o = { medAbs: medOf(d.map(Math.abs)), medSigned: medOf(d) };
      const s = scoreOf(o);
      if (!best || s < best.score) best = { CdA: cda, Crr: crr, ...o, score: s };
    }
    const step = k => (range[k][1] - range[k][0]) / (PHYS_NPTS[k] - 1);
    range = Object.fromEntries(['CdA', 'Crr'].map(k => [k, [Math.max(PHYS_BOUNDS[k][0], best[k] - step(k)), Math.min(PHYS_BOUNDS[k][1], best[k] + step(k))]]));
  }
  return best;
}

function summarizeDeltas(d) {
  return { n: d.length, medAbs: medOf(d.map(Math.abs)), medSigned: medOf(d), p10: pctl(d, 0.10), p90: pctl(d, 0.90) };
}
function ratioStats(ratios) {
  return { n: ratios.length, med: medOf(ratios), iqr: pctl(ratios, 0.75) - pctl(ratios, 0.25), p10: pctl(ratios, 0.10), p90: pctl(ratios, 0.90) };
}

// ===== the full analysis (deterministic; run TWICE, byte-compared) =====
function runAnalysis() {
  E.setKMin(Infinity);
  WS_MAX_MISMATCH = 0;
  const L = [];
  const t0 = Date.now();

  // -- per-ride frozen-default walks (verbatim v2EdgeK) + diagnostics --
  for (const r of rides) {
    const p = pFrozen(r.corpus);
    const w5 = walkStatsK(r.prof5, p, r.pFlat, DEFAULTS.thr, DEFAULTS.kS, DEFAULTS.eps0);
    const w30 = walkStatsK(r.prof30, p, r.pFlat, DEFAULTS.thr, DEFAULTS.kS, DEFAULTS.eps0);
    r.v2_5_def = w5.E; r.hplus5 = w5.hplus; r.hminus5 = w5.hminus; r.epsw5_def = w5.epsImplied;
    r.v2_30_def = w30.E; r.hplus30 = w30.hplus; r.hminus30 = w30.hminus; r.epsw30_def = w30.epsImplied;
  }

  // -- STAGE 1: resolution-transfer fit on TRAIN rider rides (geometric; emp never used) --
  const trainByC = CORPORA.map(c => trainOf(c));
  for (const set of trainByC) for (const r of set) r.dec = decompose(r.prof5, pFrozen(r.corpus), r.pFlat);
  const objective = (kS, eps0, thr) => {
    let sum = 0;
    for (const set of trainByC) sum += medOf(set.map(r => Math.abs(decEval(r.dec, kS, eps0, thr) / r.v2_30_def - 1)));
    return sum / trainByC.length;
  };
  const perCorpusObj = (kS, eps0, thr) => trainByC.map(set => medOf(set.map(r => Math.abs(decEval(r.dec, kS, eps0, thr) / r.v2_30_def - 1))));

  const objDefault = objective(DEFAULTS.kS, DEFAULTS.eps0, DEFAULTS.thr);
  const tFit = Date.now();
  const abl = {
    ks_only: fitStage1(['kS'], objective),
    eps_only: fitStage1(['eps0'], objective),
    ks_eps: fitStage1(['kS', 'eps0'], objective),
    trio: fitStage1(['kS', 'eps0', 'thr'], objective),
  };
  console.error(`  stage-1 fits: ${((Date.now() - tFit) / 1000).toFixed(1)} s`);
  const TRIO = abl.trio;

  L.push('ENTRY 20 — scale trio (k_s, ε₀, climbThr): pure 5 m → 30 m resolution transfer');
  L.push(`corpora: ${ALL_CORP.map(c => `${c}=${byCorpus(c).length}`).join(' ')} · split (sha256 entry20:, even=train): ${CORPORA.map(c => `${c} ${trainOf(c).length}/${valOf(c).length}`).join(' · ')} · censo out-of-sample (never fitted)`);
  L.push(`caches: goal_profiles.bin sha256=${gBinSha.slice(0, 16)}… supp=${sBinSha.slice(0, 16)}…`);
  L.push('');
  L.push('STAGE 1 — trio fit, objective = mean over rider corpora of train-median |v2(igc5;θ)/v2(igc30;default) − 1|');
  const pcD = perCorpusObj(DEFAULTS.kS, DEFAULTS.eps0, DEFAULTS.thr);
  L.push(`  baseline (defaults k_s=1.00 ε₀=0.130 thr=0.0200): obj=${f(objDefault, 5)}  per-corpus ${CORPORA.map((c, i) => `${c}=${f(pcD[i], 5)}`).join(' ')}`);
  for (const [tag, name] of [['ks_only', 'k_s only        '], ['eps_only', 'ε₀ only         '], ['ks_eps', 'k_s + ε₀        '], ['trio', 'FULL TRIO       ']]) {
    const b = abl[tag];
    const pc = perCorpusObj(b.kS, b.eps0, b.thr);
    L.push(`  ${name} k_s=${f(b.kS, 4)} ε₀=${f(b.eps0, 4)} thr=${f(b.thr, 4)}  obj=${f(b.obj, 5)}  per-corpus ${CORPORA.map((c, i) => `${c}=${f(pc[i], 5)}`).join(' ')}`);
  }

  // decomposition ≡ verbatim at every fitted/reported set (train rides)
  let decWorst = 0;
  for (const [kS, eps0, thr] of [[DEFAULTS.kS, DEFAULTS.eps0, DEFAULTS.thr],
    ...Object.values(abl).map(b => [b.kS, b.eps0, b.thr])]) {
    for (const set of trainByC) for (const r of set) {
      const a = decEval(r.dec, kS, eps0, thr);
      const b = v2EdgeK(r.prof5, pFrozen(r.corpus), r.pFlat, thr, kS, eps0);
      decWorst = Math.max(decWorst, Math.abs(a - b));
    }
  }

  // -- per-ride trio walks (verbatim) --
  for (const r of rides) {
    const w = walkStatsK(r.prof5, pFrozen(r.corpus), r.pFlat, TRIO.thr, TRIO.kS, TRIO.eps0);
    r.v2_5_trio = w.E; r.epsw5_trio = w.epsImplied;
    r.ratio_def = r.v2_5_def / r.v2_30_def;
    r.ratio_trio = r.v2_5_trio / r.v2_30_def;
  }

  // -- P4: transfer ratio distributions before/after --
  L.push('');
  L.push('P4 — per-ride ratio v2(igc5)/v2(igc30;default): median / IQR / p10 / p90');
  const p4Sets = [];
  for (const c of CORPORA) { p4Sets.push([`${c} train`, trainOf(c)]); p4Sets.push([`${c} val`, valOf(c)]); }
  p4Sets.push(['censo all', byCorpus('censo')]);
  for (const [tag, set] of p4Sets) {
    const b = ratioStats(set.map(r => r.ratio_def)), a = ratioStats(set.map(r => r.ratio_trio));
    L.push(`  ${tag.padEnd(15)} n=${String(set.length).padStart(3)}  before ${f(b.med, 4)} / ${f(b.iqr, 4)} / ${f(b.p10, 4)} / ${f(b.p90, 4)}   after ${f(a.med, 4)} / ${f(a.iqr, 4)} / ${f(a.p10, 4)} / ${f(a.p90, 4)}`);
  }

  // -- E1: gap closure on validation (censo: all rides, out-of-sample) --
  L.push('');
  L.push('E1 — VALIDATION (frozen journal physics; single frozen eval): med|Δ%| / medΔ% / p10 / p90 vs ∫P·dt');
  L.push(`  ${'corpus'.padEnd(16)}${'n'.padStart(4)}   ${'igc5 default'.padEnd(30)}${'igc30 default'.padEnd(30)}${'igc5 + trio'.padEnd(30)}bridged(≤1.0pp med, ≤1.5pp bias)`);
  const e1 = {};
  for (const c of ALL_CORP) {
    const set = c === 'censo' ? byCorpus('censo') : valOf(c);
    const s5 = summarizeDeltas(set.map(r => dPct(r.v2_5_def, r.emp)));
    const s30 = summarizeDeltas(set.map(r => dPct(r.v2_30_def, r.emp)));
    const sT = summarizeDeltas(set.map(r => dPct(r.v2_5_trio, r.emp)));
    const bridged = Math.abs(sT.medAbs - s30.medAbs) <= 1.0 && Math.abs(sT.medSigned - s30.medSigned) <= 1.5;
    e1[c] = { s5, s30, sT, bridged };
    const cell = s => `${f(s.medAbs)} / ${f(s.medSigned)} / ${f(s.p10)} / ${f(s.p90)}`;
    L.push(`  ${(c === 'censo' ? 'censo (o-o-s)' : c).padEnd(16)}${String(set.length).padStart(4)}   ${cell(s5).padEnd(30)}${cell(s30).padEnd(30)}${cell(sT).padEnd(30)}${bridged ? 'BRIDGED' : 'NOT BRIDGED'} (Δmed=${f(Math.abs(sT.medAbs - s30.medAbs))}pp Δbias=${f(Math.abs(sT.medSigned - s30.medSigned))}pp)`);
  }
  const e1AllBridged = ALL_CORP.every(c => e1[c].bridged);
  L.push(`  E1 ENDPOINT: ${e1AllBridged ? 'BRIDGED for all 4 corpora (P3: censo transfer holds)' : 'NOT bridged for: ' + ALL_CORP.filter(c => !e1[c].bridged).join(', ')}`);

  // -- E2: per-rider physics coherence at igc5+trio --
  L.push('');
  L.push('E2 — per-rider (CdA, Crr) fit ONLY (trio + mass frozen), train fit → single validation eval');
  const e2 = {};
  for (const c of CORPORA) {
    const tE2 = Date.now();
    const b = fitPhys(trainOf(c), TRIO);
    console.error(`  E2 fit ${c}: ${((Date.now() - tE2) / 1000).toFixed(1)} s → CdA=${f(b.CdA, 4)} Crr=${f(b.Crr, 5)}`);
    const dVal = valOf(c).map(r => dPct(v2EdgeK(r.prof5, pOf(c, b.CdA, b.Crr), r.pFlat, TRIO.thr, TRIO.kS, TRIO.eps0), r.emp));
    const sv = summarizeDeltas(dVal);
    e2[c] = { fit: b, val: sv };
    for (const r of byCorpus(c)) {   // per-ride E2 prediction for the CSV
      r.cda_e2 = b.CdA; r.crr_e2 = b.Crr;
      r.v2_e2 = v2EdgeK(r.prof5, pOf(c, b.CdA, b.Crr), r.pFlat, TRIO.thr, TRIO.kS, TRIO.eps0);
    }
    const inR = (v, [lo, hi]) => v >= lo && v <= hi;
    const e20 = E20_SIGMA0_FITS[c];
    L.push(`  ${c.padEnd(9)} fitted CdA=${f(b.CdA, 4)} Crr=${f(b.Crr, 5)} (train med|Δ%|=${f(b.medAbs)} medΔ%=${f(b.medSigned)})`);
    L.push(`  ${''.padEnd(9)} validation n=${sv.n}: med|Δ%|=${f(sv.medAbs)} medΔ%=${f(sv.medSigned)} p10=${f(sv.p10)} p90=${f(sv.p90)}  gate(<5 ∧ <±2): ${(sv.medAbs < 5 && Math.abs(sv.medSigned) < 2) ? 'PASS' : 'FAIL'}`);
    L.push(`  ${''.padEnd(9)} vs Entry-21 σ=0 fit CdA=${f(e20.CdA, 4)} Crr=${f(e20.Crr, 5)} · plausible (CdA 0.25–0.45, Crr 0.004–0.012): now CdA ${inR(b.CdA, PLAUSIBLE.CdA) ? 'IN' : 'OUT'}/Crr ${inR(b.Crr, PLAUSIBLE.Crr) ? 'IN' : 'OUT'}, was CdA ${inR(e20.CdA, PLAUSIBLE.CdA) ? 'IN' : 'OUT'}/Crr ${inR(e20.Crr, PLAUSIBLE.Crr) ? 'IN' : 'OUT'}`);
  }
  const e2AllPass = CORPORA.every(c => e2[c].val.medAbs < 5 && Math.abs(e2[c].val.medSigned) < 2);
  L.push(`  E2 ENDPOINT: ${e2AllPass ? 'PASS (all riders meet med|Δ%|<5 ∧ |medΔ%|<2)' : 'FAIL for: ' + CORPORA.filter(c => !(e2[c].val.medAbs < 5 && Math.abs(e2[c].val.medSigned) < 2)).join(', ')}`);

  // -- P1: implied drop-weighted ε (median of per-ride drop-weighted ε, Entry-19 convention) --
  L.push('');
  L.push('P1 — implied drop-weighted ε (median per-ride): igc30@default vs igc5@default vs igc5@trio(ε₀*)');
  const pooled = rides.filter(r => r.corpus !== 'censo');
  for (const [tag, set] of [...ALL_CORP.map(c => [c, byCorpus(c)]), ['pooled riders', pooled]]) {
    L.push(`  ${tag.padEnd(14)} igc30 ${f(medOf(set.map(r => r.epsw30_def)), 3)} · igc5@default ${f(medOf(set.map(r => r.epsw5_def)), 3)} · igc5@trio ${f(medOf(set.map(r => r.epsw5_trio)), 3)}`);
  }

  // -- P2: fitted k_s vs h₊ resolution ratio --
  L.push('');
  L.push('P2 — fitted k_s vs median per-ride h₊(igc30)/h₊(igc5)');
  for (const [tag, set] of [...ALL_CORP.map(c => [c, byCorpus(c)]), ['pooled riders', pooled]]) {
    L.push(`  ${tag.padEnd(14)} med h₊ ratio=${f(medOf(set.map(r => r.hplus30 / r.hplus5)), 4)}  (h₊ med: igc5 ${f(medOf(set.map(r => r.hplus5)), 0)} m · igc30 ${f(medOf(set.map(r => r.hplus30)), 0)} m)`);
  }
  L.push(`  fitted k_s = ${f(TRIO.kS, 4)} (trio) / ${f(abl.ks_only.kS, 4)} (k_s-only ablation)`);

  // -- dead-clamp: exact corner of the stage-1 grid (k_s=1, ε₀=0 IS evaluated; per-edge cost is
  // monotone ↓ in k_s and ↑ in ε₀, so this corner bounds every other stage-1 combo from below) --
  const tracked = E.getKMin();          // every verbatim walk so far (defaults, trio, E2 grid)
  E.setKMin(Infinity);
  for (const set of trainByC) for (const r of set) v2EdgeK(r.prof5, pFrozen(r.corpus), r.pFlat, 0.01, 1.0, 0.0);
  const cornerMin = E.getKMin();
  E.setKMin(Math.min(tracked, cornerMin));
  L.push('');
  L.push(`dead-clamp: min pre-clamp descent edge — reported/fitted parameter sets (verbatim walks): ${tracked.toExponential(3)} J`);
  L.push(`            stage-1 grid corner (k_s=1, ε₀=0; bounds all evaluated stage-1 combos): ${cornerMin.toExponential(3)} J`);

  // per-ride CSV (deterministic; compared across the two runs)
  const cols = ['corpus', 'ride', 'split', 'emp', 'km', 'pflat',
    'v2_igc5_def', 'v2_igc30_def', 'v2_igc5_trio', 'd_igc5_def', 'd_igc30_def', 'd_igc5_trio',
    'ratio_def', 'ratio_trio', 'hplus_igc5', 'hminus_igc5', 'hplus_igc30', 'hminus_igc30',
    'epsw_igc5_def', 'epsw_igc30_def', 'epsw_igc5_trio', 'cda_e2', 'crr_e2', 'v2_e2', 'd_e2'];
  const csvLines = [cols.join(',')];
  for (const r of rides) {
    const rec = { corpus: r.corpus, ride: r.ride, split: r.split, emp: r.emp, km: r.total / 1000, pflat: r.pFlat,
      v2_igc5_def: r.v2_5_def, v2_igc30_def: r.v2_30_def, v2_igc5_trio: r.v2_5_trio,
      d_igc5_def: dPct(r.v2_5_def, r.emp), d_igc30_def: dPct(r.v2_30_def, r.emp), d_igc5_trio: dPct(r.v2_5_trio, r.emp),
      ratio_def: r.ratio_def, ratio_trio: r.ratio_trio,
      hplus_igc5: r.hplus5, hminus_igc5: r.hminus5, hplus_igc30: r.hplus30, hminus_igc30: r.hminus30,
      epsw_igc5_def: r.epsw5_def, epsw_igc30_def: r.epsw30_def, epsw_igc5_trio: r.epsw5_trio,
      cda_e2: r.cda_e2, crr_e2: r.crr_e2, v2_e2: r.v2_e2, d_e2: r.v2_e2 != null ? dPct(r.v2_e2, r.emp) : NaN };
    csvLines.push(cols.map(k => typeof rec[k] === 'string' ? JSON.stringify(rec[k]) : (Number.isFinite(rec[k]) ? +Number(rec[k]).toFixed(6) : '')).join(','));
  }

  console.error(`analysis pass: ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  return { report: L.join('\n'), csv: csvLines.join('\n') + '\n', abl, TRIO, e1, e2, e1AllBridged, e2AllPass,
    decWorst, trackedMin: tracked, cornerMin, wsMax: WS_MAX_MISMATCH, objDefault };
}

// ===== gates + runs =====
const gates = [];
const gate = (name, pass, extra = '') => gates.push({ name, pass, extra });

gate('corpus counts = 277/181/406/58', SMOKE || ALL_CORP.every(c => byCorpus(c).length === EXPECT[c]),
  ALL_CORP.map(c => `${c}=${byCorpus(c).length}`).join(' '));

// Entry-19 CSV reproduction at frozen default physics — riders igc5 (Entry-21 gate redux),
// riders igc30 (validates the NEW supp cache), censo igc5+igc30 (the pre-registered censo gate),
// censo emp; plus r1dV2Edge ≡ v2EdgeK(1, 0.13) spot equivalence on every censo profile.
{
  let w5 = 0, w30 = 0, wc5 = 0, wc30 = 0, wEmp = 0, wEq = 0;
  let what5 = '', what30 = '', whatc5 = '', whatc30 = '';
  for (const r of rides) {
    const p = pFrozen(r.corpus);
    const a5 = v2EdgeK(r.prof5, p, r.pFlat, CLIMB_THR, 1.0, 0.13);
    const a30 = v2EdgeK(r.prof30, p, r.pFlat, CLIMB_THR, 1.0, 0.13);
    const d5 = Math.abs(a5 - r.csv.v2_igc5), d30 = Math.abs(a30 - r.csv.v2_igc30);
    if (r.corpus === 'censo') {
      if (d5 > wc5) { wc5 = d5; whatc5 = r.ride; }
      if (d30 > wc30) { wc30 = d30; whatc30 = r.ride; }
      wEmp = Math.max(wEmp, Math.abs(r.emp - r.csv.emp));
      wEq = Math.max(wEq, Math.abs(a5 - r1dV2Edge(r.prof5, p, { flat: r.pFlat }, CLIMB_THR)));
    } else {
      if (d5 > w5) { w5 = d5; what5 = `${r.corpus}/${r.ride}`; }
      if (d30 > w30) { w30 = d30; what30 = `${r.corpus}/${r.ride}`; }
    }
  }
  gate('riders v2@igc5 frozen ≡ Entry-19 CSV v2_igc5 (tol 1e-3 kJ)', w5 < 1e-3, `worst ${w5.toExponential(2)} kJ (${what5})`);
  gate('riders v2@igc30 frozen ≡ Entry-19 CSV v2_igc30 (tol 1e-3 kJ)', w30 < 1e-3, `worst ${w30.toExponential(2)} kJ (${what30})`);
  gate('censo v2@igc5 frozen ≡ Entry-19 CSV (tol 1e-3 kJ)', wc5 < 1e-3, `worst ${wc5.toExponential(2)} kJ (${whatc5})`);
  gate('censo v2@igc30 frozen ≡ Entry-19 CSV (tol 1e-3 kJ)', wc30 < 1e-3, `worst ${wc30.toExponential(2)} kJ (${whatc30})`);
  gate('censo emp ≡ Entry-19 CSV (tol 1e-3 kJ)', wEmp < 1e-3, `worst ${wEmp.toExponential(2)} kJ`);
  gate('v2EdgeK(1, 0.13) ≡ r1dV2Edge on censo igc5 profiles', wEq < 1e-9, `max ${wEq.toExponential(2)} kJ`);
}

// Entry-21 σ=0 uncalibrated VALIDATION reproduction (the igc5-frozen anchor)
{
  let worst = 0; const got = {};
  for (const c of CORPORA) {
    const d = valOf(c).map(r => dPct(v2EdgeK(r.prof5, pFrozen(c), r.pFlat, CLIMB_THR, 1.0, 0.13), r.emp));
    got[c] = medOf(d.map(Math.abs));
    worst = Math.max(worst, Math.abs(got[c] - E20_SIGMA0_UNCAL_VAL[c]));
  }
  gate('Entry-21 σ=0 uncalibrated validation med|Δ%| ≡ 8.53/2.64/14.84 (tol 0.01)', SMOKE || worst < 0.01,
    CORPORA.map(c => `${c}=${f(got[c], 3)}`).join(' '));
}

// supp cache determinism (subset rebuild, byte-identical)
{
  const t0 = Date.now();
  const { checked, bad } = suppDeterminismCheck();
  console.error(`supp cache determinism subset check: ${checked} rides, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  gate('supp cache determinism (every-40th-ride rebuild byte-identical)', bad === 0, `${checked} rides rechecked, ${bad} mismatches`);
}

console.error('analysis run 1…');
const run1 = runAnalysis();
console.error('analysis run 2…');
const run2 = runAnalysis();
gate('determinism: full analysis ×2 → identical report + CSV', run1.report === run2.report && run1.csv === run2.csv,
  `report sha ${sha256hex(run1.report).slice(0, 12)}/${sha256hex(run2.report).slice(0, 12)} · csv sha ${sha256hex(run1.csv).slice(0, 12)}/${sha256hex(run2.csv).slice(0, 12)}`);
gate('stage-1 decomposition ≡ verbatim v2EdgeK at all fitted/reported sets (tol 1e-6 kJ)', run1.decWorst < 1e-6,
  `max |Δ| ${run1.decWorst.toExponential(2)} kJ`);
gate('walkStatsK ≡ v2EdgeK on every diagnostic walk', run1.wsMax < 1e-9, `max |Δ| ${run1.wsMax.toExponential(2)} kJ`);
gate('dead-clamp: min pre-clamp > 0 at reported/fitted parameter sets', run1.trackedMin > 0,
  `min ${run1.trackedMin.toExponential(3)} J · stage-1 grid corner (k_s=1, ε₀=0) exact min ${run1.cornerMin.toExponential(3)} J${run1.cornerMin <= 0 ? ' (degenerate corner: cost is exactly 0 in real arithmetic there — fp ulps)' : ''}`);

// ===== output =====
console.log(run1.report);
console.log('\n================ SANITY GATES ================');
let ok = true;
for (const g of gates) { console.log(`  [${g.pass ? 'PASS' : 'FAIL'}] ${g.name}${g.extra ? '  ' + g.extra : ''}`); if (!g.pass) ok = false; }
console.log(ok ? 'SANITY: ALL PASS' : 'SANITY: FAILURES ABOVE');

fs.writeFileSync(path.join(HERE, 'scale_trio.csv'), run1.csv);
console.log(`\nwrote scale_trio.csv (${rides.length} rides) · sampleMs=${JSON.stringify(E.getSampleMs())}`);
process.exit(ok ? 0 : 1);
