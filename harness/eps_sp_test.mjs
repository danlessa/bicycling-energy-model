#!/usr/bin/env node
// TEST of the São Paulo ε hypothesis (chat): urban stop-go suppresses descent recovery
// below the free-coasting closed form, because you re-pedal after every forced stop/corner.
//
//   ε_SP = clamp( ε_coast − Δε_brake ),   Δε_brake = (1/(g·H₋))·Σ_descent ½·Δ(v²) at decels
//
// For the 62 clean censo rides (power + speed) we compute, on shared 30 m descent cells with
// α at the MEASURED flat speed:
//   ε_true   = (α·X₋ − E_legs,₋)/(β·H₋)            descent-balance ε (epsFromFIT) — the truth
//   ε_coast  = Σ h₋·min(1, α/β·s)/H₋               free-coasting closed form (no offset)
// and from the raw speed trace the stop-go predictors:
//   brakeDesc= Σ_descend ½·(v↓)² / (g·H₋)          mechanistic Δε_brake
//   stops_km = forced stops (v→<1 km/h) per km     cheap planning proxy
// Then: does the gap (ε_coast − ε_true) track the braking density, and does the mechanistic
// ε_coast − brakeDesc beat the flat ε≈0.20 constant?
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '..', 'data', 'activities');
const RESULTS = path.join(HERE, '..', 'results');
fs.mkdirSync(RESULTS, { recursive: true });
const G = 9.81;
const ASSUMED = { m: 78, Crr: 0.008, CdA: 0.40, rho: 1.13, keff: 0.98, wind: 0 };

function haversine(a, b) {
  const R = 6371000, t = Math.PI / 180;
  const s = Math.sin((b.lat - a.lat) * t / 2) ** 2 + Math.cos(a.lat * t) * Math.cos(b.lat * t) * Math.sin((b.lon - a.lon) * t / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}
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
function ptsFromFIT(buffer) {
  const recs = parseFIT(buffer);
  if (recs.length < 2) throw new Error('FIT sem registros');
  const pts = [];
  if (recs.some(r => r.dist !== undefined)) {
    const di = [], dv = [];
    recs.forEach((r, i) => { if (r.dist !== undefined) { di.push(i); dv.push(dv.length ? Math.max(r.dist, dv[dv.length - 1]) : r.dist); } });   // clip non-monotone device distance
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
  finishPts(pts);
  return pts;
}

// shared 30 m-cell analysis: ε_true, ε_coast (α at measured flat speed) + the floor inputs.
function epsCells(pts, p) {
  const mg = p.m * G, beta = mg / p.keff;
  const x0 = pts[0].x, totalM = pts[pts.length - 1].x - x0, DX = 30, nc = Math.floor(totalM / DX);
  if (nc < 2) return null;
  let j = 0;
  const altAt = d => { while (j < pts.length - 2 && pts[j + 1].x < d) j++; const seg = pts[j + 1].x - pts[j].x, f = seg > 1e-9 ? (d - pts[j].x) / seg : 0; return pts[j].alt * (1 - f) + pts[j + 1].alt * f; };
  const cellAlt = new Float64Array(nc + 1);
  for (let k = 0; k <= nc; k++) cellAlt[k] = altAt(x0 + k * DX);
  const cellE = new Float64Array(nc), cellVs = new Float64Array(nc), cellVt = new Float64Array(nc);
  const VSTOP = 0.5 / 3.6;   // 0.5 km/h — gate stopped samples out of the flat speed, as extractRegimePowers does
  for (const r of pts) { const k = Math.floor((r.x - x0) / DX); if (k < 0 || k >= nc) continue; const w = r.dt || 1;
    if (r.power !== undefined) cellE[k] += r.power * w; if (r.v !== undefined && r.v >= VSTOP) { cellVs[k] += r.v * w; cellVt[k] += w; } }
  let sv = 0, sw = 0;
  for (let k = 0; k < nc; k++) { const gr = (cellAlt[k + 1] - cellAlt[k]) / DX; if (Math.abs(gr) < 0.01 && cellVt[k] > 0) { sv += cellVs[k]; sw += cellVt[k]; } }
  const vf = sw > 0 ? sv / sw : 5, aeroSpd = vf + p.wind;
  const alpha = (p.Crr * mg + 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd)) / p.keff;
  let Xd = 0, Hd = 0, Ed = 0, epsW = 0, Hp = 0;
  for (let k = 0; k < nc; k++) {
    const dh = cellAlt[k + 1] - cellAlt[k];
    if (dh < 0) { const drop = -dh, s = drop / DX; Xd += DX; Hd += drop; Ed += cellE[k]; epsW += drop * Math.min(1, alpha / (beta * s)); }
    else Hp += dh;
  }
  if (Hd < 1) return null;
  return { epsTrue: (alpha * Xd - Ed) / (beta * Hd), epsCoast: epsW / Hd, Hd, Hp, beta, vf,
           cellAlt, x0, DX, nc, emp: Object.values(cellE).reduce((a, b) => a + b, 0) };
}
// stop-go predictors from the raw speed trace, given which cells descend.
function brakeStats(pts, cells) {
  const { cellAlt, x0, DX, nc, Hd } = cells, VSTOP = 1 / 3.6;
  const descending = i => { const k = Math.floor((pts[i].x - x0) / DX); return k >= 0 && k < nc && cellAlt[k + 1] < cellAlt[k]; };
  let brakeDesc = 0, brakeAll = 0, hardDesc = 0, stops = 0, totalDist = pts[pts.length - 1].x - pts[0].x;
  for (let i = 1; i < pts.length; i++) {
    const v0 = pts[i - 1].v, v1 = pts[i].v;
    if (v0 === undefined || v1 === undefined) continue;
    if (v1 < v0) { const d = 0.5 * (v0 * v0 - v1 * v1); brakeAll += d;
      if (descending(i)) { brakeDesc += d; if (v0 - v1 > 1.0) hardDesc += d; } }  // hard = >1 m/s drop
    if (v0 >= VSTOP && v1 < VSTOP) stops++;     // moving → stopped transition
  }
  const gHd = G * Hd;
  return { brakeDesc: brakeDesc / gHd, brakeAll: brakeAll / gHd, hardDesc: hardDesc / gHd, stops_km: stops / (totalDist / 1000) };
}

// ---- driver ----
const man = JSON.parse(fs.readFileSync(path.join(DATA, 'censohidrografico', 'manifest.json'), 'utf8'));
const rows = [];
for (const e of man) {
  if (!e.file) continue;
  const fp = path.join(DATA, e.file);
  if (!fs.existsSync(fp)) continue;
  try {
    // NB: slice, not .buffer — Node pools small reads, so .buffer may be the shared pool
    const pts = ptsFromFIT((b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength))(fs.readFileSync(fp)));
    if (!pts.some(q => q.power !== undefined)) continue;
    const p = { ...ASSUMED };
    const c = epsCells(pts, p); if (!c) continue;
    const floor = p.m * G * c.Hp / p.keff;           // climbing PE (kJ·1000) from 30 m cells
    if (c.emp < floor) continue;                     // physical floor — not fully pedalled
    const b = brakeStats(pts, c);
    rows.push({ ride: e.name, epsTrue: c.epsTrue, epsCoast: c.epsCoast, gap: c.epsCoast - c.epsTrue,
      brakeDesc: b.brakeDesc, brakeAll: b.brakeAll, hardDesc: b.hardDesc, stops_km: b.stops_km, vf: c.vf * 3.6 });
  } catch (err) { /* skip */ }
}

// ---- stats helpers ----
const med = xs => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); const k = (s.length - 1) / 2; return s.length ? (s[Math.floor(k)] + s[Math.ceil(k)]) / 2 : NaN; };
const mean = xs => xs.reduce((a, b) => a + b, 0) / xs.length;
const corr = (a, b) => { const n = a.length, ma = mean(a), mb = mean(b); let sab = 0, saa = 0, sbb = 0;
  for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; } return sab / Math.sqrt(saa * sbb); };
const ols = (y, x) => { const n = y.length, mx = mean(x), my = mean(y); let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
  const b = sxy / sxx, a = my - b * mx; let ssr = 0; for (let i = 0; i < n; i++) ssr += (y[i] - (a + b * x[i])) ** 2;
  return { a, b, r2: 1 - ssr / syy, rms: Math.sqrt(ssr / n) }; };
const rmsRes = (pred) => Math.sqrt(mean(rows.map((r, i) => (r.epsTrue - pred[i]) ** 2)));
const f = (x, d = 2) => (x == null || !Number.isFinite(x)) ? '—' : x.toFixed(d);

console.log(`SÃO PAULO ε TEST — ${rows.length} clean censo rides (power + speed)`);
console.log(`assumed: m=${ASSUMED.m} CdA=${ASSUMED.CdA} Crr=${ASSUMED.Crr}; α at measured flat speed.\n`);
console.log(`medians: ε_true ${f(med(rows.map(r => r.epsTrue)))}  ε_coast ${f(med(rows.map(r => r.epsCoast)))}  gap ${f(med(rows.map(r => r.gap)))}  brakeDesc ${f(med(rows.map(r => r.brakeDesc)))}  stops/km ${f(med(rows.map(r => r.stops_km)), 1)}`);

const gap = rows.map(r => r.gap);
console.log(`\nDoes the gap (ε_coast − ε_true) track stop-go density?`);
for (const [lab, key] of [['Δε_brake (descent ½Δv²)', 'brakeDesc'], ['hard-brake (>1m/s, descent)', 'hardDesc'], ['all-decel ½Δv²', 'brakeAll'], ['stops/km', 'stops_km'], ['v_f (km/h)', 'vf']]) {
  const x = rows.map(r => r[key]); const o = ols(gap, x);
  console.log(`  gap ~ ${lab.padEnd(24)} corr=${f(corr(gap, x))}  slope=${f(o.b)}  intercept=${f(o.a)}  R²=${f(o.r2)}`);
}

console.log(`\nWhich estimator best predicts ε_true?  (RMS of ε_true − prediction)`);
const clamp = v => Math.max(0, Math.min(1, v));
const preds = {
  'ε_coast (no penalty)': rows.map(r => clamp(r.epsCoast)),
  'ε_coast − 0.13 (rural offset)': rows.map(r => clamp(r.epsCoast - 0.13)),
  'flat ε = 0.20 (SP constant)': rows.map(() => 0.20),
  'ε_coast − Δε_brake (mechanistic, slope 1)': rows.map(r => clamp(r.epsCoast - r.brakeDesc)),
};
// calibrated: ε_coast − c·brakeDesc and ε_coast − (a + b·stops_km)
const ob = ols(gap, rows.map(r => r.brakeDesc));
preds[`ε_coast − ${f(ob.b)}·Δε_brake (fitted)`] = rows.map(r => clamp(r.epsCoast - ob.b * r.brakeDesc));
const os = ols(gap, rows.map(r => r.stops_km));
preds[`ε_coast − (${f(os.a)}+${f(os.b)}·stops/km) (fitted)`] = rows.map(r => clamp(r.epsCoast - (os.a + os.b * r.stops_km)));
for (const [lab, pred] of Object.entries(preds)) console.log(`  ${lab.padEnd(44)} RMS=${f(rmsRes(pred))}  bias=${f(med(rows.map((r, i) => r.epsTrue - pred[i])))}`);

console.log(`\ngap variability: median ${f(med(gap))}, mean ${f(mean(gap))}, sd ${f(Math.sqrt(mean(gap.map(g => (g - mean(gap)) ** 2))))}`);
fs.writeFileSync(path.join(RESULTS, 'eps_sp.csv'),
  ['ride,epsTrue,epsCoast,gap,brakeDesc,brakeAll,stops_km,vf'].concat(rows.map(r =>
    `"${r.ride}",${f(r.epsTrue)},${f(r.epsCoast)},${f(r.gap)},${f(r.brakeDesc)},${f(r.brakeAll)},${f(r.stops_km, 1)},${f(r.vf, 1)}`)).join('\n') + '\n');
console.log(`\nwrote results/eps_sp.csv (${rows.length} rides)`);
