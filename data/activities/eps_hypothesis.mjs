#!/usr/bin/env node
// TEST of the closed-form ε hypothesis (notas / chat):
//
//   ε(s) = min(1, α/(β·s)),  α/β = Crr + ½ρCdA(v_f+w)²/(mg)          [coasting recovery]
//   ε ≈ clamp[0,1]( ε_coast − c_κ·κ − c_u·f_unpaved )                [+ braking penalties]
//
// Target = the per-ride descent-energy-balance ε (epsFromBalance, ported from the app's
// epsFromFIT) — the same "truth" the harness already reports (median ≈ 0.27).
//
// For each ride we compute, on the SAME 30 m descent cells the balance ε uses:
//   ε_coast  drop-weighted Σ hᵢ·min(1, α/β·sᵢ) / H₋   (per-cell clamp; α at measured v_f)
//   ε_lump   min(1, α/(β·s̄)),  s̄ = H₋/X₋               (cheap, totals only)
// plus two ride "details": κ = curviness (rad/km, from GPS) and f_unpaved (sheet col I).
// Then we check how well ε_coast predicts ε_bal, and whether κ / f_unpaved earn their keep.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const G = 9.81;

// ---- parseFIT (record msg 20; lat/lon/alt/dist/speed/power) ----
function parseFIT(buffer) {
  const dv = new DataView(buffer);
  if (buffer.byteLength < 14) throw new Error('FIT muito curto');
  const headerSize = dv.getUint8(0), dataSize = dv.getUint32(4, true);
  if (String.fromCharCode(dv.getUint8(8), dv.getUint8(9), dv.getUint8(10), dv.getUint8(11)) !== '.FIT') throw new Error('no .FIT');
  const end = Math.min(headerSize + dataSize, buffer.byteLength);
  let pos = headerSize; const defs = {}, records = [];
  let lastTs;   // running timestamp for compressed-timestamp headers (5-bit offset, 32 s rollover)
  const read = (p, bt, little) => { switch (bt & 0x1F) {
    case 0x01: { const v = dv.getInt8(p); return v === 0x7F ? undefined : v; }
    case 0x00: case 0x02: case 0x0A: case 0x0D: { const v = dv.getUint8(p); return v === 0xFF ? undefined : v; }
    case 0x03: { const v = dv.getInt16(p, little); return v === 0x7FFF ? undefined : v; }
    case 0x04: case 0x0B: { const v = dv.getUint16(p, little); return v === 0xFFFF ? undefined : v; }
    case 0x05: { const v = dv.getInt32(p, little); return v === 0x7FFFFFFF ? undefined : v; }
    case 0x06: case 0x0C: { const v = dv.getUint32(p, little) >>> 0; return v === 0xFFFFFFFF ? undefined : v; }
    case 0x08: return dv.getFloat32(p, little);
    case 0x09: return dv.getFloat64(p, little);
    default: return undefined; } };
  while (pos < end) {
    const rh = dv.getUint8(pos); pos++;
    let local, isDef = false, hasDev = false, tsOffset;
    if (rh & 0x80) { local = (rh >> 5) & 0x03; tsOffset = rh & 0x1F; }
    else { local = rh & 0x0F; isDef = !!(rh & 0x40); hasDev = !!(rh & 0x20); }
    if (isDef) {
      pos++; const little = dv.getUint8(pos) === 0; pos++;
      const gmn = dv.getUint16(pos, little); pos += 2;
      const nf = dv.getUint8(pos); pos++;
      const fields = [];
      for (let i = 0; i < nf; i++) { fields.push({ num: dv.getUint8(pos), size: dv.getUint8(pos + 1), bt: dv.getUint8(pos + 2) }); pos += 3; }
      let devSize = 0;
      if (hasDev) { const nd = dv.getUint8(pos); pos++; for (let i = 0; i < nd; i++) { devSize += dv.getUint8(pos + 1); pos += 3; } }
      defs[local] = { gmn, little, fields, devSize };
    } else {
      const def = defs[local];
      if (!def) throw new Error('FIT corrompido (dado sem definição)');
      let p = pos; const rec = {};
      for (const f of def.fields) {
        if (def.gmn === 20) { const v = read(p, f.bt, def.little);
          if (v !== undefined) {
            if (f.num === 0) rec.lat = v * (180 / 2147483648);
            else if (f.num === 1) rec.lon = v * (180 / 2147483648);
            else if (f.num === 2) { if (rec.alt === undefined) rec.alt = v / 5 - 500; }
            else if (f.num === 78) rec.alt = v / 5 - 500;
            else if (f.num === 5) rec.dist = v / 100;
            else if (f.num === 6) { if (rec.speed === undefined) rec.speed = v / 1000; }
            else if (f.num === 73) rec.speed = v / 1000;
            else if (f.num === 7) rec.power = v;
            else if (f.num === 253) rec.time = v;
          } }
        else if (f.num === 253) {   // any message's timestamp advances the running clock
          const v = read(p, f.bt, def.little);
          if (v !== undefined) rec.time = v;
        }
        p += f.size;
      }
      pos = p + def.devSize;
      // compressed-timestamp header: reconstruct the time from the 5-bit offset
      if (tsOffset !== undefined && rec.time === undefined && lastTs !== undefined) {
        let ts = (lastTs & ~31) | tsOffset;
        if (ts < lastTs) ts += 32;
        rec.time = ts;
      }
      if (rec.time !== undefined) lastTs = rec.time;
      if (def.gmn === 20) records.push(rec);
    }
  }
  return records;
}
function haversine(a, b) {
  const R = 6371000, t = Math.PI / 180;
  const s = Math.sin((b.lat - a.lat) * t / 2) ** 2 + Math.cos(a.lat * t) * Math.cos(b.lat * t) * Math.sin((b.lon - a.lon) * t / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}
function finishPts(pts) {
  for (let i = 0; i < pts.length; i++) {
    const raw = (i > 0 && pts[i].t !== undefined && pts[i - 1].t !== undefined) ? pts[i].t - pts[i - 1].t : undefined;
    const w = raw !== undefined ? Math.min(Math.max(raw, 0), 10) : 1;
    pts[i].dt = w;
    if (pts[i].v === undefined && i > 0) {
      const dtv = raw !== undefined && raw > 0 ? raw : w;   // speed from the UNCLAMPED interval
      if (dtv > 0) pts[i].v = (pts[i].x - pts[i - 1].x) / dtv;
    }
  }
}
// pts (energy) from FIT — interleaved dist/alt handling, as compare.mjs
function ptsFromFIT(recs) {
  if (recs.length < 2) throw new Error('FIT sem registros');
  const pts = [];
  if (recs.some(r => r.dist !== undefined)) {
    const di = [], dv = [];
    recs.forEach((r, i) => { if (r.dist !== undefined) { di.push(i); dv.push(r.dist); } });
    let lastAlt, k = 0;
    for (let i = 0; i < recs.length; i++) {
      if (recs[i].alt !== undefined) lastAlt = recs[i].alt;
      if (lastAlt === undefined) continue;
      while (k < di.length - 1 && di[k + 1] <= i) k++;
      let x;
      if (i <= di[0]) x = dv[0]; else if (i >= di[di.length - 1]) x = dv[dv.length - 1];
      else { const f = (i - di[k]) / (di[k + 1] - di[k]); x = dv[k] + (dv[k + 1] - dv[k]) * f; }
      pts.push({ x, alt: lastAlt, power: recs[i].power, t: recs[i].time, v: recs[i].speed });
    }
  } else {
    const geo = recs.filter(r => r.lat !== undefined && r.lon !== undefined && r.alt !== undefined);
    if (geo.length < 2) throw new Error('FIT sem distância nem GPS');
    let cum = 0; pts.push({ x: 0, alt: geo[0].alt, power: geo[0].power, t: geo[0].time, v: geo[0].speed });
    for (let i = 1; i < geo.length; i++) { cum += haversine(geo[i - 1], geo[i]); pts.push({ x: cum, alt: geo[i].alt, power: geo[i].power, t: geo[i].time, v: geo[i].speed }); }
  }
  finishPts(pts); return pts;
}
function parseGPX(text) {
  const out = [];
  const re = /<trkpt\b([^>]*)>([\s\S]*?)<\/trkpt>/g; let m;
  while ((m = re.exec(text))) {
    const la = m[1].match(/lat="([-\d.]+)"/), lo = m[1].match(/lon="([-\d.]+)"/);
    if (!la || !lo) continue;
    const ele = m[2].match(/<ele>\s*([-\d.]+)/), tm = m[2].match(/<time>\s*([^<]+)/), pw = m[2].match(/<(?:\w+:)?power>\s*([\d.]+)/);
    out.push({ lat: +la[1], lon: +lo[1], alt: ele ? +ele[1] : NaN, t: tm ? Date.parse(tm[1]) / 1000 : undefined, power: pw ? +pw[1] : undefined });
  }
  if (out.length < 2) throw new Error('GPX poucos pontos');
  return out;
}
function ptsFromGeo(geo) {
  let cum = 0; const pts = [{ x: 0, alt: geo[0].alt, power: geo[0].power, t: geo[0].t }];
  for (let i = 1; i < geo.length; i++) { cum += haversine(geo[i - 1], geo[i]); pts.push({ x: cum, alt: geo[i].alt, power: geo[i].power, t: geo[i].t }); }
  finishPts(pts); return pts;
}

// ---- curviness κ: total |heading change| per km on a ~RES-m resampled GPS track ----
// Resample to constant spacing first so GPS jitter / dense slow points don't inflate it.
function curviness(geo, RES = 50) {
  const ll = geo.filter(r => r.lat !== undefined && r.lon !== undefined && Number.isFinite(r.lat) && Number.isFinite(r.lon));
  if (ll.length < 3) return null;
  // cumulative distance
  const d = [0]; for (let i = 1; i < ll.length; i++) d.push(d[i - 1] + haversine(ll[i - 1], ll[i]));
  const total = d[d.length - 1]; if (total < 5 * RES) return null;
  // resample lat/lon at RES spacing
  const pts = []; let j = 0;
  for (let s = 0; s <= total; s += RES) {
    while (j < ll.length - 2 && d[j + 1] < s) j++;
    const seg = d[j + 1] - d[j], f = seg > 1e-9 ? (s - d[j]) / seg : 0;
    pts.push({ lat: ll[j].lat + (ll[j + 1].lat - ll[j].lat) * f, lon: ll[j].lon + (ll[j + 1].lon - ll[j].lon) * f });
  }
  if (pts.length < 3) return null;
  // local east-north metres (small-angle), heading per segment, sum |Δheading|
  const lat0 = pts[0].lat * Math.PI / 180, mPerLon = 111320 * Math.cos(lat0), mPerLat = 110540;
  const head = [];
  for (let i = 1; i < pts.length; i++) {
    const dx = (pts[i].lon - pts[i - 1].lon) * mPerLon, dy = (pts[i].lat - pts[i - 1].lat) * mPerLat;
    head.push(Math.atan2(dy, dx));
  }
  let turn = 0;
  for (let i = 1; i < head.length; i++) {
    let dth = head[i] - head[i - 1];
    while (dth > Math.PI) dth -= 2 * Math.PI; while (dth < -Math.PI) dth += 2 * Math.PI;
    turn += Math.abs(dth);
  }
  return turn / (total / 1000);   // rad per km
}

// ---- ε analysis: balance (truth) + coasting prediction, sharing 30 m cells, α, v_f ----
function epsAnalysis(pts, p) {
  if (!pts || pts.length < 2) return null;
  const mg = p.m * G, beta = mg / p.keff;
  const x0 = pts[0].x, totalM = pts[pts.length - 1].x - x0, DX = 30, nc = Math.floor(totalM / DX);
  if (nc < 2) return null;
  let j = 0;
  const altAt = dd => { while (j < pts.length - 2 && pts[j + 1].x < dd) j++; const seg = pts[j + 1].x - pts[j].x, f = seg > 1e-9 ? (dd - pts[j].x) / seg : 0; return pts[j].alt * (1 - f) + pts[j + 1].alt * f; };
  const cellAlt = new Float64Array(nc + 1); for (let k = 0; k <= nc; k++) cellAlt[k] = altAt(x0 + k * DX);
  const cellE = new Float64Array(nc), cellVs = new Float64Array(nc), cellVt = new Float64Array(nc);
  const VSTOP = 0.5 / 3.6;   // stopped samples deflate v_f (hence α and ε) — gate them, as extractRegimePowers does
  for (const r of pts) { const k = Math.floor((r.x - x0) / DX); if (k < 0 || k >= nc) continue; const w = r.dt || 1;
    if (r.power !== undefined) cellE[k] += r.power * w; if (r.v !== undefined && r.v >= VSTOP) { cellVs[k] += r.v * w; cellVt[k] += w; } }
  let sv = 0, sw = 0;   // measured MOVING flat speed
  for (let k = 0; k < nc; k++) { const gr = (cellAlt[k + 1] - cellAlt[k]) / DX; if (Math.abs(gr) < 0.01 && cellVt[k] > 0) { sv += cellVs[k]; sw += cellVt[k]; } }
  const vf = sw > 0 ? sv / sw : 5, aeroSpd = vf + p.wind;
  const alpha = (p.Crr * mg + 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd)) / p.keff;
  let Xd = 0, Hd = 0, Ed = 0, epsW = 0;   // descent totals + drop-weighted coasting ε
  for (let k = 0; k < nc; k++) {
    const dh = cellAlt[k + 1] - cellAlt[k];
    if (dh < 0) { const drop = -dh, s = drop / DX; Xd += DX; Hd += drop; Ed += cellE[k];
      epsW += drop * Math.min(1, alpha / (beta * s)); }
  }
  if (Hd < 1) return null;
  const epsBal = (alpha * Xd - Ed) / (beta * Hd);   // TRUTH (measured descent legs)
  const epsCoast = epsW / Hd;                        // per-cell clamped coasting prediction
  const sbar = Hd / Xd;                              // aggregate descent grade
  const epsLump = Math.min(1, alpha / (beta * sbar));// cheap lumped prediction
  return { epsBal, epsCoast, epsLump, sbar, alpha, beta, vf, Hd, Xd };
}

// ---- tiny OLS (normal equations + Gaussian elimination) ----
function ols(y, X) {   // X: rows of features (incl. intercept col if wanted); returns {b, r2, pred}
  const n = y.length, k = X[0].length;
  const A = Array.from({ length: k }, () => new Float64Array(k)), g = new Float64Array(k);
  for (let i = 0; i < n; i++) for (let a = 0; a < k; a++) { g[a] += X[i][a] * y[i]; for (let b = 0; b < k; b++) A[a][b] += X[i][a] * X[i][b]; }
  // solve A b = g
  const M = A.map((row, i) => Array.from(row).concat(g[i]));
  for (let c = 0; c < k; c++) {
    let piv = c; for (let r = c + 1; r < k; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    [M[c], M[piv]] = [M[piv], M[c]];
    const d = M[c][c] || 1e-12;
    for (let cc = c; cc <= k; cc++) M[c][cc] /= d;
    for (let r = 0; r < k; r++) if (r !== c) { const fa = M[r][c]; for (let cc = c; cc <= k; cc++) M[r][cc] -= fa * M[c][cc]; }
  }
  const b = M.map(row => row[k]);
  const ybar = y.reduce((s, v) => s + v, 0) / n;
  let ssr = 0, sst = 0; const pred = [];
  for (let i = 0; i < n; i++) { let yh = 0; for (let a = 0; a < k; a++) yh += X[i][a] * b[a]; pred.push(yh); ssr += (y[i] - yh) ** 2; sst += (y[i] - ybar) ** 2; }
  return { b, r2: 1 - ssr / sst, rms: Math.sqrt(ssr / n), pred };
}
const corr = (a, b) => { const n = a.length, ma = a.reduce((s, v) => s + v, 0) / n, mb = b.reduce((s, v) => s + v, 0) / n;
  let sab = 0, saa = 0, sbb = 0; for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; } return sab / Math.sqrt(saa * sbb); };
const med = xs => { const s = xs.slice().sort((a, b) => a - b); const k = (s.length - 1) / 2; return s.length ? (s[Math.floor(k)] + s[Math.ceil(k)]) / 2 : NaN; };

// ---- driver ----
const inputs = JSON.parse(fs.readFileSync(path.join(HERE, 'model_inputs.json'), 'utf8'));
const feats = JSON.parse(fs.readFileSync(path.join(HERE, 'eps_features.json'), 'utf8'));
const rows = [];
for (const e of inputs) {
  if (!e.file || !e.has_power) continue;
  try {
    const fp = path.join(HERE, e.file);
    let pts, geo;
    if (e.file.endsWith('.gpx')) { geo = parseGPX(fs.readFileSync(fp, 'utf8')); pts = ptsFromGeo(geo); }
    else { const recs = parseFIT((b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength))(fs.readFileSync(fp))); pts = ptsFromFIT(recs); geo = recs.filter(r => r.lat !== undefined && r.lon !== undefined); }
    const p = { m: e.m, Crr: e.crr, CdA: e.cda, rho: e.rho, keff: e.keff, wind: (e.wind_kmh || 0) / 3.6 };
    const a = epsAnalysis(pts, p); if (!a) continue;
    const kappa = curviness(geo);
    const f = feats[e.id] || {};
    rows.push({ ride: e.label, epsBal: a.epsBal, epsCoast: a.epsCoast, epsLump: a.epsLump,
      sbar: a.sbar, kappa, unpaved: f.unpaved == null ? null : f.unpaved, sheet: e.eps,
      vf: a.vf * 3.6, ab: a.alpha / a.beta, bHd: a.beta * a.Hd, Hd: a.Hd });
  } catch (err) { /* skip */ }
}

// keep rides with a finite balance ε (the target)
const good = rows.filter(r => Number.isFinite(r.epsBal));
const f2 = (x, d = 2) => (x == null || !Number.isFinite(x)) ? '—' : x.toFixed(d);

console.log(`ε CLOSED-FORM HYPOTHESIS TEST   (n=${good.length} rides with descents+power)`);
console.log('target = descent-energy-balance ε (epsFromBalance). predictor = min(1, α/β·s), drop-weighted.\n');
console.log(`${'ride'.padEnd(24)}${'ε_bal'.padStart(7)}${'ε_coast'.padStart(8)}${'ε_lump'.padStart(7)}${'s̄%'.padStart(6)}${'κ r/km'.padStart(8)}${'unpav'.padStart(7)}`);
console.log('-'.repeat(67));
for (const r of good) console.log(
  r.ride.slice(0, 23).padEnd(24) + f2(r.epsBal).padStart(7) + f2(r.epsCoast).padStart(8) + f2(r.epsLump).padStart(7) +
  f2(r.sbar * 100, 1).padStart(6) + f2(r.kappa, 0).padStart(8) + f2(r.unpaved).padStart(7));

console.log('\n' + '='.repeat(67));
console.log('HOW WELL DOES THE COASTING CORE PREDICT ε_bal?');
const yb = good.map(r => r.epsBal);
for (const [lab, key] of [['ε_coast (per-cell clamp)', 'epsCoast'], ['ε_lump (totals only)', 'epsLump']]) {
  const x = good.map(r => r[key]);
  const resid = good.map((r, i) => r.epsBal - x[i]);
  const rmsRaw = Math.sqrt(resid.reduce((s, v) => s + v * v, 0) / resid.length);
  console.log(`  ${lab.padEnd(26)} corr=${f2(corr(x, yb))}  med(pred)=${f2(med(x))}  med(ε_bal)=${f2(med(yb))}  RMS(ε_bal−pred)=${f2(rmsRaw)}  medBias=${f2(med(resid))}`);
}

// where does it matter? weight each ride by its descent energy β·H₋ (J), and look at
// the real-descent subset — the flat rides that break the clamp carry ~no energy.
const wCorr = (a, b, w) => { const W = w.reduce((s, v) => s + v, 0);
  const ma = a.reduce((s, v, i) => s + w[i] * v, 0) / W, mb = b.reduce((s, v, i) => s + w[i] * v, 0) / W;
  let sab = 0, saa = 0, sbb = 0; for (let i = 0; i < a.length; i++) { sab += w[i] * (a[i] - ma) * (b[i] - mb); saa += w[i] * (a[i] - ma) ** 2; sbb += w[i] * (b[i] - mb) ** 2; } return sab / Math.sqrt(saa * sbb); };
console.log('\n' + '='.repeat(67));
console.log('WHERE IT MATTERS — weight by descent energy β·H₋, and the real-descent subset');
const W = good.map(r => r.bHd);
const wBias = good.reduce((s, r) => s + r.bHd * (r.epsBal - r.epsCoast), 0) / W.reduce((s, v) => s + v, 0);
console.log(`  energy-weighted: corr(ε_coast,ε_bal)=${f2(wCorr(good.map(r => r.epsCoast), good.map(r => r.epsBal), W))}  weighted bias(ε_bal−ε_coast)=${f2(wBias)}`);
for (const thr of [0.025, 0.03, 0.035]) {
  const sub = good.filter(r => r.sbar >= thr);
  const x = sub.map(r => r.epsCoast), y = sub.map(r => r.epsBal);
  const resid = sub.map(r => r.epsBal - r.epsCoast);
  console.log(`  s̄ ≥ ${(thr * 100).toFixed(1)}%  (n=${sub.length}): corr=${f2(corr(x, y))}  medBias=${f2(med(resid))}  med(ε_bal)=${f2(med(y))} med(ε_coast)=${f2(med(x))}`);
}

// ---- estimator SKILL (error reduction) + part-whole disclosure ----
// The correlation headline is part-whole: ε_bal ≡ α/(β·s̄) − E_legs,₋/(β·H₋) EXACTLY,
// and ε_coast ≈ that same first term (drop-weighted, clamped) with the same per-ride α.
// So judge the closed form by RMS skill vs the best flat constant, not by corr alone.
console.log('\n' + '='.repeat(67));
console.log('ESTIMATOR SKILL — RMS(ε_bal − pred), skill = 1 − RMS/RMS_flat (flat = subset median ε_bal)');
const clamp01 = v => Math.max(0, Math.min(1, v));
const rms = xs => Math.sqrt(xs.reduce((s, v) => s + v * v, 0) / xs.length);
for (const [slab, sub] of [['all rides', good], ['s̄ ≥ 3%', good.filter(r => r.sbar >= 0.03)]]) {
  const base = med(sub.map(r => r.epsBal));
  const rmsBase = rms(sub.map(r => r.epsBal - base));
  console.log(`  -- ${slab} (n=${sub.length}, flat const = ${f2(base)}, RMS_flat = ${f2(rmsBase)}) --`);
  for (const [lab, fx] of [
    ['sheet g_d_eff', r => r.sheet],
    ['ε_coast − 0.13 (clamped)', r => clamp01(r.epsCoast - 0.13)],
    ['ε_lump − 0.13 (clamped, totals)', r => clamp01(r.epsLump - 0.13)],
  ]) {
    const s2 = sub.filter(r => Number.isFinite(fx(r)));
    const e = rms(s2.map(r => r.epsBal - fx(r)));
    console.log(`  ${lab.padEnd(32)} RMS=${f2(e)}  skill vs flat=${f2(1 - e / rmsBase)}  (n=${s2.length})`);
  }
  const shared = sub.map(r => r.ab / r.sbar);   // the UNclamped shared geometry term α/(β·s̄)
  console.log(`  part–whole: corr(α/(β·s̄), ε_bal)=${f2(corr(shared, sub.map(r => r.epsBal)))}  corr(α/(β·s̄), ε_coast)=${f2(corr(shared, sub.map(r => r.epsCoast)))}`);
}

// add the braking penalties: ε_bal ~ ε_coast + κ + unpaved  (need κ & unpaved present)
const fit = good.filter(r => Number.isFinite(r.kappa) && Number.isFinite(r.unpaved));
console.log('\n' + '='.repeat(67));
console.log(`BRAKING PENALTIES — OLS on the ${fit.length} rides with GPS+unpaved`);
const y = fit.map(r => r.epsBal);
const models = [
  ['ε_coast only',                    r => [1, r.epsCoast]],
  ['ε_coast + κ',                     r => [1, r.epsCoast, r.kappa]],
  ['ε_coast + unpaved',               r => [1, r.epsCoast, r.unpaved]],
  ['ε_coast + κ + unpaved',           r => [1, r.epsCoast, r.kappa, r.unpaved]],
];
for (const [lab, fx] of models) {
  const X = fit.map(fx); const o = ols(y, X);
  const terms = o.b.map((v, i) => `${['b0', 'εc', i === 2 && lab.includes('κ') ? 'κ' : 'unp', 'unp'][i] || 'x'}=${v.toFixed(3)}`).join(' ');
  console.log(`  ${lab.padEnd(24)} R²=${f2(o.r2)}  RMS=${f2(o.rms)}   ${terms}`);
}
console.log('\n(signs to expect if the hypothesis holds: ε_coast coeff > 0; κ and unpaved coeffs < 0)');
