#!/usr/bin/env node
// Censo Hidrográfico model verification: for each downloaded ride (censohidrografico/),
// run the three energy models on the ride's OWN track and compare to the measured ∫P·dt:
//   canonical        — forward sim, fed the ride's FIT-extracted climb/flat/descent powers
//   smooth approx    — α_r·x + α_a·x_flat + β(h₊−ε·h₋) on a 2 m deadband-SMOOTHED profile
//   poor-man's       — same, raw profile, gravity scaled by k_smooth = 1 − 0.003·x/h₊
//
// Per the rules: every factual quantity is DERIVED from the activity (geometry, regime
// powers, v_f, ∫P·dt). Only the rider physics is assumed (m, CdA, Crr, paved, ρ, wind,
// k_eff) and ε is swept: closed-form ε_geom (notas) AND constants 0.20 / 0.25.
//
// Engines ported verbatim from energy-model-comparison.html / compare.mjs.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const G = 9.81, NS = 240;
const VMAX = 38 / 3.6, VSTART = 15 / 3.6;
const CLIMB_THR = 0.02, DESC_THR = -0.015, ENGINE_DX = 5, TAU_SMOOTH = 2;
// ASSUMED rider (Danilo's note): 78 kg, CdA 0.40, Crr 0.008, 100% paved.
// ρ for São Paulo (~760 m, ~22 °C) ≈ 1.13; wind 0; k_eff 0.98 (repo default).
const ASSUMED = { m: 78, CdA: 0.40, Crr: 0.008, rho: 1.13, keff: 0.98, wind: 0 };
const EPS_SWEEP = [['geom', null], ['0.00', 0.00], ['0.05', 0.05], ['0.10', 0.10], ['0.15', 0.15], ['0.20', 0.20], ['0.25', 0.25]];

let H = new Float64Array(NS), physProfile = null;

function haversine(a, b) {
  const R = 6371000, toR = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toR, dLon = (b.lon - a.lon) * toR;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}
function flatEqSpeed(P, p) {
  const a = p.Crr * p.m * G, b = 0.5 * p.rho * p.CdA, w = p.wind || 0;
  // SIGNED drag (tailwind pushes); monotone only for v+w ≥ 0, so bisect that branch first
  const wheel = v => { const rel = v + w; return (a + b * rel * Math.abs(rel)) * v; };
  const target = p.keff * P;
  let lo = Math.max(0, -w), hi = 40;
  if (wheel(lo) > target) { hi = lo; lo = 0; }
  for (let k = 0; k < 60; k++) { const v = (lo + hi) / 2; if (wheel(v) < target) lo = v; else hi = v; }
  return (lo + hi) / 2;
}
function resampleProfile(src, dx) {
  const total = src.x[src.x.length - 1];
  const n = Math.max(2, Math.round(total / dx) + 1);
  const x = new Float64Array(n), h = new Float64Array(n);
  let j = 0;
  for (let i = 0; i < n; i++) {
    const d = i === n - 1 ? total : total * i / (n - 1);
    while (j < src.x.length - 2 && src.x[j + 1] < d) j++;
    const seg = src.x[j + 1] - src.x[j], f = seg > 1e-9 ? (d - src.x[j]) / seg : 0;
    x[i] = d; h[i] = src.h[j] * (1 - f) + src.h[j + 1] * f;
  }
  return { x, h };
}
function canonical(prof, pw, p) {
  const { m, Crr, CdA, rho, keff, vmax } = p;
  const xs = prof.x, hs = prof.h, n = xs.length;
  const DT_MAX = 0.25, DS_MIN = 0.2;
  const KEinit = 0.5 * m * p.vstart * p.vstart;
  let KE = KEinit, legE = 0, t = 0, Wrr = 0, Waero = 0, Wgrav = 0, Wbrake = 0;
  const keCap = 0.5 * m * vmax * vmax;
  let stalled = false;   // P=0 with resistance > KE: halt, never floor the KE (a floor injects energy)
  for (let i = 1; i < n; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    const slope = dh / dx, sec = Math.sqrt(1 + slope * slope);
    const cos = 1 / sec, sin = slope / sec;
    const Frr = Crr * m * G * cos, Fgrav = m * G * sin;
    let P;
    if (slope >= pw.climbThr) P = pw.climb; else if (slope <= pw.descThr) P = pw.descent; else P = pw.flat;
    let remaining = dx * sec;
    while (remaining > 1e-9) {
      const v = Math.sqrt(2 * KE / m);
      const dsSub = Math.min(remaining, Math.max(v * DT_MAX, DS_MIN));
      const rel = v + p.wind;
      const Faero = 0.5 * rho * CdA * rel * Math.abs(rel);
      const R = Frr + Faero + Fgrav;
      const Pleg = (v >= vmax) ? Math.min(Math.max(R * v / keff, 0), P) : P;
      const A = keff * Pleg * dsSub * Math.sqrt(m / 2), B = KE - R * dsSub;
      let KEn;
      if (A > 0) {
        let lo = 1e-12, hi = Math.max(KE, B, 1) + A + 1;
        while (hi - A / Math.sqrt(hi) - B <= 0) hi *= 2;
        KEn = (KE > lo && KE < hi) ? KE : 0.5 * (lo + hi);
        for (let it = 0; it < 40; it++) {
          const root = Math.sqrt(KEn), g = KEn - A / root - B;
          g > 0 ? hi = KEn : lo = KEn;
          let next = KEn - g / (1 + 0.5 * A / (KEn * root));
          if (!(next > lo && next < hi)) next = 0.5 * (lo + hi);
          if (Math.abs(next - KEn) <= 1e-9 * KEn + 1e-12) { KEn = next; break; }
          KEn = next;
        }
      } else {
        // A = 0 (no propulsion): exact linear-KE solution — NO floor (a floor injects energy).
        KEn = B;
        if (KEn <= 0) {   // resistance exhausts the KE inside this substep: finite stop, halt
          const dsStop = R > 0 ? KE / R : 0;
          t += R > 0 ? Math.sqrt(2 * m * Math.max(KE, 0)) / R : 0;
          Wrr += Frr * dsStop; Waero += Faero * dsStop; Wgrav += Fgrav * dsStop;
          KE = 0; stalled = true; break;
        }
      }
      const vNew = Math.sqrt(2 * KEn / m), dt = dsSub / vNew;
      legE += Pleg * dt; t += dt;
      Wrr += Frr * dsSub; Waero += Faero * dsSub; Wgrav += Fgrav * dsSub;
      KE = KEn;
      if (KE > keCap) { Wbrake += KE - keCap; KE = keCap; }
      remaining -= dsSub;
    }
    if (stalled) break;   // cannot proceed at zero power — return the partial, conservative leg
  }
  return { legE, t, stalled };
}
// approximate with cf (climbAeroMode='zero'): returns components so ε can vary analytically.
function approxComponents(prof, p, vf, pw) {
  const beta = p.m * G / p.keff, mg = p.m * G, w = p.wind;
  const aeroSpd = vf + w;
  const aRoll = mg * p.Crr / p.keff;
  const aAero = 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd) / p.keff;
  const xs = prof.x, hs = prof.h;
  let X = 0, hplus = 0, hminus = 0, aeroSum = 0;
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1], slope = dh / dx;
    X += dx;
    const aeroDx = slope >= CLIMB_THR ? 0 : aAero;   // cf: aero only off climbs
    aeroSum += aeroDx * dx;
    if (dh >= 0) hplus += dh; else hminus += -dh;
  }
  return { roll: aRoll * X, aero: aeroSum, climb: beta * hplus, beta, hminus, X, hplus };
}
function buildProfile(distArr, eleArr) {
  const X = [distArr[0]], E = [eleArr[0]];
  for (let i = 1; i < distArr.length; i++) {
    const close = distArr[i] - X[X.length - 1] < 0.5;
    if (close && i < distArr.length - 1) continue;
    if (close) { X[X.length - 1] = distArr[i]; E[E.length - 1] = eleArr[i]; }   // final point: replace, never create dx≈0
    else { X.push(distArr[i]); E.push(eleArr[i]); }
  }
  const base = X[0]; for (let i = 0; i < X.length; i++) X[i] -= base;
  const n = X.length, total = X[n - 1];
  if (n < 2 || !(total > 0)) throw new Error('distância nula');
  const first = E.findIndex(e => Number.isFinite(e));
  if (first < 0) throw new Error('faixa sem elevação');
  for (let i = 0; i < first; i++) E[i] = E[first];
  let last = first;
  for (let i = first + 1; i < n; i++) { if (Number.isFinite(E[i])) { for (let k = last + 1; k < i; k++) E[k] = E[last] + (E[i] - E[last]) * (k - last) / (i - last); last = i; } }
  for (let i = last + 1; i < n; i++) E[i] = E[last];
  let minE = Infinity, maxE = -Infinity;
  for (const e of E) { if (e < minE) minE = e; if (e > maxE) maxE = e; }
  const px = new Float64Array(n), ph = new Float64Array(n);
  for (let i = 0; i < n; i++) { px[i] = X[i]; ph[i] = E[i] - minE; }
  physProfile = { x: px, h: ph };
  return { total, range: maxE - minE, n };
}
function extractRegimePowers(pts, climbThr, descThr) {
  const W = 30, bins = [[], [], []], VSTOP = 0.5 / 3.6;
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].power === undefined) continue;
    if (pts[i].v !== undefined && pts[i].v < VSTOP) continue;
    let j = i; while (j < pts.length - 1 && pts[j].x - pts[i].x < W) j++;
    const dd = pts[j].x - pts[i].x;
    let grade;
    if (dd > 1) grade = (pts[j].alt - pts[i].alt) / dd;
    else { let k = i; while (k > 0 && pts[i].x - pts[k].x < W) k--; const db = pts[i].x - pts[k].x; grade = db > 1 ? (pts[i].alt - pts[k].alt) / db : 0; }
    const r = grade >= climbThr ? 2 : grade <= descThr ? 0 : 1;
    bins[r].push({ p: pts[i].power, w: pts[i].dt || 1 });
  }
  const stat = b => { if (!b.length) return null; let sw = 0, swp = 0; for (const s of b) { sw += s.w; swp += s.w * s.p; } return sw ? swp / sw : null; };
  return { descent: stat(bins[0]), flat: stat(bins[1]), climb: stat(bins[2]) };
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
            else if (f.num === 4) rec.cad = v;          // cadence (rpm) — 0 ⇒ not pedalling
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
      pts.push({ x, alt: lastAlt, power: recs[i].power, cad: recs[i].cad, t: recs[i].time, v: recs[i].speed });
    }
  } else {
    const geo = recs.filter(r => r.lat !== undefined && r.lon !== undefined && r.alt !== undefined);
    if (geo.length < 2) throw new Error('FIT sem distância nem GPS');
    let cum = 0; pts.push({ x: 0, alt: geo[0].alt, power: geo[0].power, cad: geo[0].cad, t: geo[0].time, v: geo[0].speed });
    for (let i = 1; i < geo.length; i++) { cum += haversine(geo[i - 1], geo[i]); pts.push({ x: cum, alt: geo[i].alt, power: geo[i].power, cad: geo[i].cad, t: geo[i].time, v: geo[i].speed }); }
  }
  finishPts(pts);
  return pts;
}
function deadband(h, tau) {
  const out = new Float64Array(h.length);
  let y = h[0]; out[0] = y;
  for (let i = 1; i < h.length; i++) { if (h[i] > y + tau) y = h[i] - tau; else if (h[i] < y - tau) y = h[i] + tau; out[i] = y; }
  return out;
}
function empiricalKJ(pts) { let e = 0; for (const q of pts) if (q.power !== undefined) e += q.power * (q.dt || 0); return e / 1000; }
function overallMeanPower(pts) { let sw = 0, swp = 0; for (const q of pts) if (q.power !== undefined) { sw += (q.dt || 1); swp += (q.dt || 1) * q.power; } return sw ? swp / sw : 0; }
function hasPower(pts) { return pts.some(q => q.power !== undefined); }
// Walking/pushing detector. The clean test is CADENCE (Danilo): pedalling ⇔ cadence > 0,
// so "moving but cadence 0" is not pedalling (coasting or on foot); pair it with a walking
// pace (< 4 km/h — you CAN granny-gear below 6, so 4 is the bike/foot line) to isolate
// pushing from coasting. Returns distance-weighted fractions of MOVING distance:
//   push  — < 4 km/h AND cadence 0 (no sensor ⇒ assume the slow crawl is on foot)
//   slow  — < 4 km/h regardless of cadence (speed-only fallback)
//   cadCov— cadence-sensor coverage (so push is trustworthy only when this is high)
function pushStats(pts) {
  let moving = 0, slow = 0, push = 0, cadKnown = 0;
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i].x - pts[i - 1].x, v = pts[i].v, cad = pts[i].cad;
    if (!(dx > 0) || v === undefined || v < 0.5 / 3.6) continue;   // skip standstills
    moving += dx;
    if (cad !== undefined) cadKnown += dx;
    if (v < 4 / 3.6) { slow += dx; if (cad !== undefined ? cad === 0 : true) push += dx; }
  }
  return { push: moving ? push / moving : 0, slow: moving ? slow / moving : 0, cadCov: moving ? cadKnown / moving : 0 };
}
// closed-form ε_geom = clamp(Σ h₋·min(1, α/β·s)/H₋ − 0.13) over 30 m descent cells (notas/app).
function epsGeom(prof, p, vf) {
  const mg = p.m * G, beta = mg / p.keff, aeroSpd = vf + p.wind;
  const alpha = (p.Crr * mg + 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd)) / p.keff;
  const ab = alpha / beta;
  const x0 = prof.x[0], totalM = prof.x[prof.x.length - 1] - x0, DX = 30, nc = Math.floor(totalM / DX);
  if (nc < 2) return NaN;
  let j = 0;
  const hAt = d => { while (j < prof.x.length - 2 && prof.x[j + 1] < d) j++; const seg = prof.x[j + 1] - prof.x[j], f = seg > 1e-9 ? (d - prof.x[j]) / seg : 0; return prof.h[j] * (1 - f) + prof.h[j + 1] * f; };
  const cellH = new Float64Array(nc + 1);
  for (let k = 0; k <= nc; k++) cellH[k] = hAt(x0 + k * DX);
  let Hd = 0, epsW = 0;
  for (let k = 0; k < nc; k++) { const dh = cellH[k + 1] - cellH[k]; if (dh < 0) { const drop = -dh; Hd += drop; epsW += drop * Math.min(1, ab / (drop / DX)); } }
  if (Hd < 1) return NaN;
  return Math.max(0, Math.min(1, epsW / Hd - 0.13));
}

// ===== driver =====
const man = JSON.parse(fs.readFileSync(path.join(HERE, 'censohidrografico', 'manifest.json'), 'utf8'));
const rows = [];
for (const e of man) {
  if (!e.file) continue;
  const fp = path.join(HERE, e.file);
  if (!fs.existsSync(fp)) continue;
  try {
    // NB: slice, not .buffer — Node pools small reads, so .buffer may be the shared pool
    const pts = ptsFromFIT((b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength))(fs.readFileSync(fp)));
    if (!hasPower(pts)) continue;                      // benchmark needs power
    buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
    const prof = resampleProfile(physProfile, ENGINE_DX);
    const profS = { x: prof.x, h: deadband(prof.h, TAU_SMOOTH) };
    const rp = extractRegimePowers(pts, CLIMB_THR, DESC_THR);
    const flat = rp.flat != null ? rp.flat : overallMeanPower(pts);
    const pw = { climb: rp.climb != null ? rp.climb : flat, flat, descent: rp.descent != null ? rp.descent : 0, climbThr: CLIMB_THR, descThr: DESC_THR };
    const p = { ...ASSUMED, m: ASSUMED.m, Crr: ASSUMED.Crr, CdA: ASSUMED.CdA, vmax: VMAX, vstart: VSTART };
    const vf = flatEqSpeed(pw.flat, p);
    const beta = p.m * G / p.keff;
    const emp = empiricalKJ(pts);                      // kJ benchmark
    const c = canonical(prof, pw, p);
    const aRaw = approxComponents(prof, p, vf, pw);    // poor-man's base (raw)
    const aSm = approxComponents(profS, p, vf, pw);    // smooth base (deadband)
    const km = aRaw.hplus > 0 ? Math.max(0, 1 - 3 * (prof.x[prof.x.length - 1] / 1000) / aRaw.hplus) : 1;  // k_smooth
    const epsG = epsGeom(prof, p, vf);
    // Physical floor: pedalling energy MUST cover the (momentum-corrected, deadband-smoothed)
    // climbing potential energy mg·h₊_sm/k_eff. A measured ∫P·dt below it means the route was
    // NOT fully pedalled — a power-meter dropout OR the riders walked/pushed up steep climbs
    // (no pedalling → ~0 W while still ascending). Either way the cycling model over-predicts
    // by design, so these are excluded from the headline. walkFrac tells the two apart.
    const peFloor = beta * aSm.hplus / 1000;           // kJ
    const dataOK = emp >= peFloor;
    const ps = pushStats(pts);
    const row = { ride: e.name, source: e.source, dist_km: prof.x[prof.x.length - 1] / 1000,
      hplus: aRaw.hplus, hplus_sm: aSm.hplus, emp, peFloor, dataOK, push: ps.push, slow: ps.slow, cadCov: ps.cadCov, epsG, km, vf_kmh: vf * 3.6,
      canon: c.legE / 1000, canon_d: (c.legE / 1000 - emp) / emp * 100 };
    for (const [tag, ev] of EPS_SWEEP) {
      const eps = ev == null ? (Number.isFinite(epsG) ? epsG : 0.2) : ev;
      const eSm = (aSm.roll + aSm.aero + aSm.climb - eps * beta * aSm.hminus) / 1000;             // smooth approx
      const ePm = (aRaw.roll + aRaw.aero + km * (aRaw.climb - eps * beta * aRaw.hminus)) / 1000;  // poor-man's
      row[`sm_${tag}`] = (eSm - emp) / emp * 100;
      row[`pm_${tag}`] = (ePm - emp) / emp * 100;
    }
    rows.push(row);
  } catch (err) { /* skip unparseable */ }
}

const f = (x, d = 1) => (x == null || Number.isNaN(x)) ? '—' : x.toFixed(d);
const med = xs => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); const k = (s.length - 1) / 2; return s.length ? (s[Math.floor(k)] + s[Math.ceil(k)]) / 2 : NaN; };
const clean = rows.filter(r => r.dataOK);                 // headline = physically-plausible power streams
const flagged = rows.filter(r => !r.dataOK);              // emp < climbing PE ⇒ dropouts in the power data
const stat = key => { const v = clean.map(r => Math.abs(r[key])).filter(Number.isFinite), s = clean.map(r => r[key]).filter(Number.isFinite);
  return { n: v.length, medAbs: med(v), medSigned: med(s), mean: s.reduce((a, b) => a + b, 0) / s.length }; };

console.log(`CENSO HIDROGRÁFICO — ${rows.length} rides w/ power · benchmark = measured ∫P·dt`);
console.log(`assumed rider: m=${ASSUMED.m} CdA=${ASSUMED.CdA} Crr=${ASSUMED.Crr} ρ=${ASSUMED.rho} wind=${ASSUMED.wind} k_eff=${ASSUMED.keff} (100% paved)`);
console.log(`EXCLUDED ${flagged.length} rides with measured ∫P·dt < climbing PE (mg·h₊_sm/k_eff) — route not fully pedalled (dropout or walking).`);
console.log(`HEADLINE on ${clean.length} clean rides. geometry: dist median ${f(med(clean.map(r => r.dist_km)))} km · h₊ median ${f(med(clean.map(r => r.hplus)), 0)} m · v_f median ${f(med(clean.map(r => r.vf_kmh)))} km/h · ε_geom median ${f(med(clean.map(r => r.epsG)), 2)}`);
console.log('\nΔ% vs empirical (− = under, + = over):');
console.log(`${'model'.padEnd(34)}${'n'.padStart(4)}${'med|Δ%|'.padStart(9)}${'medΔ%'.padStart(8)}${'meanΔ%'.padStart(8)}`);
const print = (lab, key) => { const s = stat(key); console.log(`${lab.padEnd(34)}${String(s.n).padStart(4)}${f(s.medAbs).padStart(9)}${f(s.medSigned).padStart(8)}${f(s.mean).padStart(8)}`); };
print('canonical (fed ride powers)', 'canon_d');
console.log('  -- smooth approx (2 m deadband) --');
for (const [tag] of EPS_SWEEP) print(`  smooth · ε=${tag}`, `sm_${tag}`);
console.log("  -- poor-man's (scalar k_smooth) --");
for (const [tag] of EPS_SWEEP) print(`  poor-man's · ε=${tag}`, `pm_${tag}`);

// ε-sensitivity: spread of medΔ% across the ε sweep, per approximate model
const smSpread = EPS_SWEEP.map(([t]) => stat(`sm_${t}`).medSigned), pmSpread = EPS_SWEEP.map(([t]) => stat(`pm_${t}`).medSigned);
console.log(`\nε-sensitivity (medΔ% range over ε∈{${EPS_SWEEP.map(([t]) => t).join(',')}}):`);
console.log(`  smooth approx : ${f(Math.min(...smSpread))} … ${f(Math.max(...smSpread))}  (spread ${f(Math.max(...smSpread) - Math.min(...smSpread))} pp)`);
console.log(`  poor-man's    : ${f(Math.min(...pmSpread))} … ${f(Math.max(...pmSpread))}  (spread ${f(Math.max(...pmSpread) - Math.min(...pmSpread))} pp)`);

// flagged rides (bad power data) — shown for transparency, not used in the headline
console.log(`\nFLAGGED (excluded) — measured ∫P·dt below climbing PE ⇒ not fully pedalled.`);
console.log(`  push% = moving dist <4 km/h & cadence 0 (on foot); slow% = <4 km/h; cad% = cadence coverage:`);
for (const r of flagged.sort((a, b) => (a.emp / a.peFloor) - (b.emp / b.peFloor)))
  console.log(`  ${r.ride.slice(0, 30).padEnd(30)} emp=${f(r.emp, 0)}kJ floor=${f(r.peFloor, 0)}kJ (${f(r.emp / r.peFloor * 100, 0)}%)  push=${f(r.push * 100, 0)}% slow=${f(r.slow * 100, 0)}% cad=${f(r.cadCov * 100, 0)}%  cΔ=${f(r.canon_d, 0)}%`);

// csv (gitignored)
const cols = ['ride', 'source', 'dist_km', 'hplus', 'emp', 'peFloor', 'dataOK', 'push', 'slow', 'cadCov', 'epsG', 'km', 'vf_kmh', 'canon', 'canon_d']
  .concat(EPS_SWEEP.flatMap(([t]) => [`sm_${t}`, `pm_${t}`]));
fs.writeFileSync(path.join(HERE, 'censohidrografico', 'censo_comparison.csv'),
  [cols.join(',')].concat(rows.map(r => cols.map(c => { const v = r[c]; return v == null ? '' : (typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(3)) : `"${v}"`); }).join(','))).join('\n') + '\n');
console.log(`\nwrote censohidrografico/censo_comparison.csv (${rows.length} rides)`);
