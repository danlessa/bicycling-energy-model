#!/usr/bin/env node
// REGIME-DECOMPOSED closed form E_new = E_flat(x₌;P₌) + E_climb(x₊;P₊) + E_descent(x₋;P₋),
// each component drawing from the base law E ≈ α·x + β·(h₊ − ε·h₋) with a REGIME-SPECIFIC
// reference speed (flat: flatEqSpeed(P₌); climb: v_c(P₊); descent: P₋+gravity equilibrium).
// Tests it against the current champion R0 (cf + 2 m deadband) and canonical on all corpora.
//
// Engines are VERBATIM (assembled from time_compare.mjs, itself verbatim from ppaz_compare.mjs +
// compare.mjs + energy-model-comparison.html — the ppaz engine block is a substring, asserted at
// build time). New logic only in regimeComponents / r0Champion / the drivers below.
//
// Two design traps (see the plan / Entry 17):
//  · Trap 1 (P·t tautology): E_new is a genuine prediction ONLY because every regime speed is
//    MODELLED from power+physics (flatEqSpeed, v_c, descentEqSpeed), never measured. Regime
//    POWERS are fair inputs (canonical + R0 already use them); regime TIMES/SPEEDS never enter.
//  · Trap 2 (descent double-count): descent aero is paid by gravity and sits in (1−ε)·β·h₋; the
//    three descent variants (R1a keeps ε; R1b/R1c drop it for explicit descent physics) are
//    NEVER mixed — ε and explicit descent aero never co-occur in one variant.
//
// Descent variants (pre-specified):
//  · R1a — base-law per-edge ε clamp, aero at v_flat: max(0, α_r·dx + α_a(v₌)·dx − ε·β·|dh|).
//  · R1b — P₋·t₋, t₋ over the modelled descent equilibrium speed (no ε).
//  · R1c — leg force-deficit held at flat cruise speed: max(0, (C_rr·mg·cosθ + ½ρCdA·(v₌+w)² +
//    mg·sinθ))·dx·secθ/k_eff (no ε, no P₋; sinθ<0 on descent so gravity offsets the resistances).
//
// PRE-DECLARED PRIMARY ENDPOINT: R1a at default ±(2%/1.5%) thresholds & corpus ε rule, med|Δ%|
// vs ∫P·dt on the 441 P. Paz rides, PAIRED against R0 (cf + 2 m deadband). Reported whatever it is.
//   node regime_compare.mjs
// Output: console report + regime_comparison.csv (gitignored via data/activities/*.csv).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const G = 9.81, NS = 240;
const VMAX = 38 / 3.6, VSTART = 15 / 3.6;
const CLIMB_THR = 0.02, DESC_THR = -0.015, ENGINE_DX = 5, TAU_SMOOTH = 2;
const VSTOP = 0.5 / 3.6;
const ASSUMED = { m: 78, CdA: 0.40, Crr: 0.008, rho: 1.13, keff: 0.98, wind: 0 };
// Per-rider physics: frozen masses (Entries 12/14/16) + <RIDER>_M/_CDA/_CRR env overrides — the
// fitted-vs-assumed rerun (Entry 16's machinery): swap in each rider's Entry-15 fitted constants
// to test whether the regime model's win/loss tracks R0's bias sign (the bias-trade prediction).
const PHYS = {};
for (const [r, m0] of [['ppaz', 74.3], ['jaam', 101.7], ['danlessa', 74.5]]) {
  const U = r.toUpperCase();
  PHYS[r] = { ...ASSUMED,
    m: process.env[`${U}_M`] ? +process.env[`${U}_M`] : m0,
    CdA: process.env[`${U}_CDA`] ? +process.env[`${U}_CDA`] : ASSUMED.CdA,
    Crr: process.env[`${U}_CRR`] ? +process.env[`${U}_CRR`] : ASSUMED.Crr,
  };
}
const ZWIFT = 260;
const SWEEP_CLIMB = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04];
const SWEEP_DESC = [-0.01, -0.015, -0.02, -0.03];

let H = new Float64Array(NS), physProfile = null;
let FIT_MANUF;

// ===== VERBATIM engines/instruments (haversine … readPts) — from time_compare.mjs =====
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
  FIT_MANUF = undefined;
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
        else if (def.gmn === 0 && f.num === 1) {   // file_id manufacturer (260 = Zwift -> virtual ride)
          const v = read(p, f.bt, def.little);
          if (v !== undefined) FIT_MANUF = v;
        }
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

function climbBalance(pts, p, CLIMB_PCT = 0.03, MINLEN = 100) {
  const mg = p.m * G, w = p.wind, out = { emeas: 0, egrav: 0, eroll: 0, eaero: 0, dh: 0, L: 0, n: 0, totalAsc: 0 };
  for (let i = 1; i < pts.length; i++) { const d = pts[i].alt - pts[i - 1].alt; if (d > 0) out.totalAsc += d; }
  const climbing = new Uint8Array(pts.length);
  let j = 0;
  for (let i = 0; i < pts.length; i++) {
    while (j < pts.length - 1 && pts[j].x - pts[i].x < MINLEN) j++;
    const dd = pts[j].x - pts[i].x;
    if (dd > 1 && (pts[j].alt - pts[i].alt) / dd >= CLIMB_PCT) climbing[i] = 1;
  }
  let s = -1;
  for (let i = 0; i <= pts.length; i++) {
    if (i < pts.length && climbing[i]) { if (s < 0) s = i; continue; }
    if (s < 0) continue;
    const a = s, b = i - 1; s = -1;
    const L = pts[b].x - pts[a].x, dh = pts[b].alt - pts[a].alt;
    if (L < MINLEN || dh <= 0) continue;
    let emeas = 0, time = 0;
    for (let k = a; k <= b; k++) { if (pts[k].power !== undefined) emeas += pts[k].power * (pts[k].dt || 0); time += pts[k].dt || 0; }
    const v = time > 0 ? L / time : 0, slope = dh / L, cos = 1 / Math.sqrt(1 + slope * slope);
    out.emeas += emeas / 1000;
    out.egrav += mg * dh / p.keff / 1000;
    out.eroll += p.Crr * mg * cos * L / p.keff / 1000;
    out.eaero += 0.5 * p.rho * p.CdA * (v + w) * Math.abs(v + w) * L / p.keff / 1000;
    out.dh += dh; out.L += L; out.n++;
  }
  return out;
}

// Descent 30 m cells: ε_bal AND the geometric ε_coast/s̄ in one pass (adapted from
// compare.mjs's epsFromBalance; the ε_coast accumulation mirrors eps_hypothesis.mjs).
function epsCellsPz(pts, p) {
  if (!pts || pts.length < 2) return null;
  const mg = p.m * G, beta = mg / p.keff, VSTOP = 0.5 / 3.6;
  const x0 = pts[0].x, totalM = pts[pts.length - 1].x - x0, DX = 30, nc = Math.floor(totalM / DX);
  if (nc < 2) return null;
  let j = 0;
  const altAt = d => { while (j < pts.length - 2 && pts[j + 1].x < d) j++; const seg = pts[j + 1].x - pts[j].x, f = seg > 1e-9 ? (d - pts[j].x) / seg : 0; return pts[j].alt * (1 - f) + pts[j + 1].alt * f; };
  const cellAlt = new Float64Array(nc + 1);
  for (let k = 0; k <= nc; k++) cellAlt[k] = altAt(x0 + k * DX);
  const cellE = new Float64Array(nc), cellVs = new Float64Array(nc), cellVt = new Float64Array(nc);
  for (const r of pts) {
    const k = Math.floor((r.x - x0) / DX); if (k < 0 || k >= nc) continue;
    const w = r.dt || 1;
    if (r.power !== undefined) cellE[k] += r.power * w;
    if (r.v !== undefined && r.v >= VSTOP) { cellVs[k] += r.v * w; cellVt[k] += w; }
  }
  let sv = 0, sw = 0;
  for (let k = 0; k < nc; k++) { const gr = (cellAlt[k + 1] - cellAlt[k]) / DX; if (Math.abs(gr) < 0.01 && cellVt[k] > 0) { sv += cellVs[k]; sw += cellVt[k]; } }
  if (!(sw > 0)) return null;
  const vf = sv / sw, aeroSpd = vf + p.wind;
  const alpha = (p.Crr * mg + 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd)) / p.keff;
  let Xd = 0, Hd = 0, Ed = 0, cw = 0;
  for (let k = 0; k < nc; k++) {
    const dh = cellAlt[k + 1] - cellAlt[k];
    if (dh < 0) {
      const s = -dh / DX;
      Xd += DX; Hd -= dh; Ed += cellE[k];
      cw += Math.min(1, alpha / (beta * s)) * (-dh);   // drop-weighted per-cell clamp
    }
  }
  if (Hd < 1) return null;
  return { epsBal: (alpha * Xd - Ed) / (beta * Hd), epsCoast: cw / Hd, sbar: Hd / Xd, vf, Hd };
}

// ptsFromGPX — VERBATIM from compare.mjs (the one longões GPX ride)
function ptsFromGPX(text) {
  const out = [];
  const re = /<trkpt\b([^>]*)>([\s\S]*?)<\/trkpt>/g;   // attr order-agnostic (lat/lon either way)
  let m;
  while ((m = re.exec(text))) {
    const attrs = m[1], body = m[2];
    const la = attrs.match(/lat="([-\d.]+)"/), lo = attrs.match(/lon="([-\d.]+)"/);
    if (!la || !lo) continue;
    const lat = +la[1], lon = +lo[1];
    const ele = body.match(/<ele>\s*([-\d.]+)/);
    const tm = body.match(/<time>\s*([^<]+)/);
    const pw = body.match(/<(?:\w+:)?power>\s*([\d.]+)/);
    out.push({ lat, lon, alt: ele ? +ele[1] : NaN,
               t: tm ? Date.parse(tm[1]) / 1000 : undefined,
               power: pw ? +pw[1] : undefined });
  }
  if (out.length < 2) throw new Error('GPX poucos pontos');
  let cum = 0; const pts = [{ x: 0, alt: out[0].alt, power: out[0].power, t: out[0].t }];
  for (let i = 1; i < out.length; i++) { cum += haversine(out[i - 1], out[i]); pts.push({ x: cum, alt: out[i].alt, power: out[i].power, t: out[i].t }); }
  finishPts(pts);
  return pts;
}

// approxTime — VERBATIM from energy-model-comparison.html
function approxTime(prof, p, vf, pw) {
  const mg = p.m * G, w = p.wind, vmax = p.vmax, xs = prof.x, hs = prof.h;
  let t = 0, X = 0, hplus = 0, hminus = 0, tClimb = 0, xClimb = 0, hpC = 0, tDesc = 0, xDesc = 0, hmD = 0;
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1], slope = dh / dx;
    const sec = Math.sqrt(1 + slope * slope), sin = slope / sec, cos = 1 / sec, ds = dx * sec;
    X += dx; if (dh > 0) hplus += dh; else hminus += -dh;
    let v;
    if (slope >= pw.climbThr) {                          // climb: v_c capped at v_f
      v = pw.climb > 0 ? Math.min(vf, p.keff * pw.climb / (p.Crr * mg * cos + mg * sin)) : 0.05;
      tClimb += ds / v; xClimb += dx; hpC += dh;
    } else if (slope <= pw.descThr) {                     // descent: equilibrium, capped at v_max
      let lo = 0.05, hi = 45;
      for (let k = 0; k < 28; k++) {
        const vv = 0.5 * (lo + hi);
        const f = 0.5 * p.rho * p.CdA * (vv + w) * Math.abs(vv + w) + p.Crr * mg * cos + mg * sin - p.keff * pw.descent / vv;
        f < 0 ? lo = vv : hi = vv;
      }
      v = Math.min(vmax, Math.max(0.5, 0.5 * (lo + hi)));
      tDesc += ds / v; xDesc += dx; hmD += -dh;
    } else v = vf;                                        // flat
    t += ds / Math.max(v, 0.02);
  }
  const kPlus = hpC > 0 ? (vf * tClimb - xClimb) / hpC : NaN;    // effective climb multiplier
  const kMinus = hmD > 0 ? (xDesc - vf * tDesc) / hmD : NaN;     // effective descent multiplier (time-ε)
  return { t, X, hplus, hminus, kPlus, kMinus };
}

// ===== NEW INSTRUMENT: per-regime moving time / distance / vertical =====
// Same 30 m forward grade window + power-gate + VSTOP gate as extractRegimePowers, but also
// accumulates, per regime (descent/flat/climb): moving time Σdt, horizontal Σdx, vertical Σdh
// (all over the SAME gated points that feed P̄, so t₊+t_flat+t₋ ≡ Σdt over gated points, and
// k₊_meas/k₋_meas use exactly the P̄ point set). Returns times (s), dists (m), verticals (m).
function extractRegimeStats(pts, climbThr, descThr) {
  const W = 30;
  const t = [0, 0, 0], x = [0, 0, 0], dh = [0, 0, 0];   // [descent, flat, climb]
  const pw = [[], [], []];
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].power === undefined) continue;
    if (pts[i].v !== undefined && pts[i].v < VSTOP) continue;
    let j = i; while (j < pts.length - 1 && pts[j].x - pts[i].x < W) j++;
    const dd = pts[j].x - pts[i].x;
    let grade;
    if (dd > 1) grade = (pts[j].alt - pts[i].alt) / dd;
    else { let k = i; while (k > 0 && pts[i].x - pts[k].x < W) k--; const db = pts[i].x - pts[k].x; grade = db > 1 ? (pts[i].alt - pts[k].alt) / db : 0; }
    const r = grade >= climbThr ? 2 : grade <= descThr ? 0 : 1;
    const dxLoc = i > 0 ? pts[i].x - pts[i - 1].x : 0;
    const dhLoc = i > 0 ? pts[i].alt - pts[i - 1].alt : 0;
    t[r] += pts[i].dt || 0;
    x[r] += dxLoc > 0 ? dxLoc : 0;
    dh[r] += dhLoc;
    pw[r].push({ p: pts[i].power, w: pts[i].dt || 1 });
  }
  const mean = b => { if (!b.length) return null; let sw = 0, swp = 0; for (const s of b) { sw += s.w; swp += s.w * s.p; } return sw ? swp / sw : null; };
  return {
    tD: t[0], tF: t[1], tC: t[2], xD: x[0], xF: x[1], xC: x[2],
    hC: dh[2], hD: -dh[0],                                  // climb vertical, descent drop (both ≥0 typ.)
    Pdesc: mean(pw[0]), Pflat: mean(pw[1]), Pclimb: mean(pw[2]),
    tMovBin: t[0] + t[1] + t[2], xBin: x[0] + x[1] + x[2],
  };
}
// Descent equilibrium speed at power Pdesc on mean descent grade s̄ (>0): the same P+gravity
// aero-equilibrium bisection approxTime uses, extracted for the bridge fallback. Capped vmax.
function descentEqSpeed(Pdesc, sbar, p, vmax) {
  const mg = p.m * G, w = p.wind, slope = -sbar, sec = Math.sqrt(1 + slope * slope), sin = slope / sec, cos = 1 / sec;
  let lo = 0.05, hi = 45;
  for (let k = 0; k < 40; k++) {
    const vv = 0.5 * (lo + hi);
    const f = 0.5 * p.rho * p.CdA * (vv + w) * Math.abs(vv + w) + p.Crr * mg * cos + mg * sin - p.keff * (Pdesc > 0 ? Pdesc : 0) / vv;
    f < 0 ? lo = vv : hi = vv;
  }
  return Math.min(vmax, Math.max(0.5, 0.5 * (lo + hi)));
}
// 30 m-cell profile h± (alternative to regime-binned, for the sensitivity run) — cells like epsGeom.
function cellHpm(prof) {
  const x0 = prof.x[0], total = prof.x[prof.x.length - 1] - x0, DX = 30, nc = Math.floor(total / DX);
  if (nc < 2) return { hplus: 0, hminus: 0 };
  let j = 0;
  const hAt = d => { while (j < prof.x.length - 2 && prof.x[j + 1] < d) j++; const seg = prof.x[j + 1] - prof.x[j], f = seg > 1e-9 ? (d - prof.x[j]) / seg : 0; return prof.h[j] * (1 - f) + prof.h[j + 1] * f; };
  const cell = new Float64Array(nc + 1);
  for (let k = 0; k <= nc; k++) cell[k] = hAt(x0 + k * DX);
  let hp = 0, hm = 0;
  for (let k = 0; k < nc; k++) { const d = cell[k + 1] - cell[k]; if (d > 0) hp += d; else hm += -d; }
  return { hplus: hp, hminus: hm };
}

const clamp01 = v => Math.max(0, Math.min(1, v));
const medOf = xs => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); const k = (s.length - 1) / 2; return s.length ? (s[Math.floor(k)] + s[Math.ceil(k)]) / 2 : NaN; };
const iqr = xs => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); const q = p => s[Math.floor(p * (s.length - 1))]; return s.length ? [q(0.25), q(0.75)] : [NaN, NaN]; };
const corrOf = (xs, ys) => { const n = xs.length; if (n < 3) return NaN; const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n; let sxy = 0, sxx = 0, syy = 0; for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) ** 2; syy += (ys[i] - my) ** 2; } return sxy / Math.sqrt(sxx * syy); };

const readPts = file => {
  let buf = fs.readFileSync(path.join(HERE, file));
  if (file.endsWith('.gz')) buf = zlib.gunzipSync(buf);
  if (file.endsWith('.gpx') || file.endsWith('.gpx.gz')) return ptsFromGPX(buf.toString('utf8'));
  return ptsFromFIT(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
};
// ===== NEW: regime-decomposed closed form =====
// Walk the (deadband-smoothed) 5 m profile edge by edge; classify each edge by local slope vs
// (thr.climbThr, thr.descThr); accumulate the base closed form per regime. `descentMode` picks
// the firewalled descent treatment. Flat edges use RAW signed β·dh (no floor) so the all-flat
// limit reduces EXACTLY to the v1 law α·x + β·Σdh (reduction test). eps = descent recovery factor
// (used ONLY by R1a). Returns kJ components (Σ = E) + per-regime x/h for diagnostics.
function regimeComponents(prof, p, pw, thr, eps, descentMode) {
  const mg = p.m * G, beta = mg / p.keff, w = p.wind;
  const aRoll = mg * p.Crr / p.keff;
  const vFlat = Math.max(0.05, flatEqSpeed(pw.flat > 0 ? pw.flat : 1, p));
  const aAeroFlat = 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) / p.keff;
  const xs = prof.x, hs = prof.h;
  let Eflat = 0, Eclimb = 0, Edesc = 0, xF = 0, xC = 0, xD = 0, hpC = 0, hmD = 0;
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    if (!(dx > 0)) continue;
    const slope = dh / dx, sec = Math.sqrt(1 + slope * slope), sin = slope / sec, cos = 1 / sec;
    if (slope >= thr.climbThr) {
      const vc = pw.climb > 0 ? Math.min(vFlat, p.keff * pw.climb / (p.Crr * mg * cos + mg * sin)) : vFlat;
      const aAeroC = 0.5 * p.rho * p.CdA * (vc + w) * Math.abs(vc + w) / p.keff;
      Eclimb += aRoll * dx + aAeroC * dx + beta * dh;   // climb: aero at v_c(P₊), gravity exact
      xC += dx; hpC += dh;
    } else if (slope <= thr.descThr) {
      const drop = -dh;
      if (descentMode === 'R1a') {
        Edesc += Math.max(0, aRoll * dx + aAeroFlat * dx - eps * beta * drop);
      } else if (descentMode === 'R1b') {
        const vD = descentEqSpeed(pw.descent, -slope, { ...p, vmax: VMAX }, VMAX);
        Edesc += (pw.descent > 0 ? pw.descent : 0) * (dx * sec / vD);
      } else {   // R1c: leg force-deficit at flat cruise speed (no ε, no P₋)
        const deficit = p.Crr * mg * cos + 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) + mg * sin;
        Edesc += Math.max(0, deficit) * (dx * sec) / p.keff;
      }
      xD += dx; hmD += drop;
    } else {
      Eflat += aRoll * dx + aAeroFlat * dx + beta * dh;   // flat: aero at v₌, gravity signed (no floor)
      xF += dx;
    }
  }
  return { E: (Eflat + Eclimb + Edesc) / 1000, Eflat: Eflat / 1000, Eclimb: Eclimb / 1000, Edesc: Edesc / 1000, xF, xC, xD, hpC, hmD, vFlat };
}

// Regime closed form on TOTALS — the apples-to-apples form (the champion R0 evaluates on totals: its
// roll/aero/gravity/ε-credit are all aggregate quantities, the edge walk only MEASURES x/x_climb/h±).
// Classify edges once to accumulate per-regime aggregates (x_r, h₊_r, h₋_r), then evaluate each
// regime's closed form ONCE: climb aero at a single v_c(s̄₊); descent clamp/equilibrium on the descent
// TOTAL, not per edge. Identical to regimeComponents on the linear terms; differs on the nonlinear
// v_c / max(0,·) / v₋ — where the per-edge form is the sampasimu v2Edge realisation (§9.1), not the law.
function regimeTotals(prof, p, pw, thr, eps, descentMode) {
  const mg = p.m * G, beta = mg / p.keff, w = p.wind;
  const aRoll = mg * p.Crr / p.keff;
  const vFlat = Math.max(0.05, flatEqSpeed(pw.flat > 0 ? pw.flat : 1, p));
  const aAeroFlat = 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) / p.keff;
  const xs = prof.x, hs = prof.h;
  let xF = 0, hpF = 0, hmF = 0, xC = 0, hpC = 0, xD = 0, hmD = 0;
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    if (!(dx > 0)) continue;
    const slope = dh / dx;
    if (slope >= thr.climbThr) { xC += dx; hpC += Math.max(0, dh); }
    else if (slope <= thr.descThr) { xD += dx; hmD += Math.max(0, -dh); }
    else { xF += dx; if (dh >= 0) hpF += dh; else hmF += -dh; }
  }
  const Eflat = (aRoll + aAeroFlat) * xF + beta * (hpF - hmF);   // flat: aggregate, gravity net (no ε)
  let Eclimb = 0;
  if (xC > 0) {   // climb: single v_c at the mean climb grade s̄₊
    const sC = hpC / xC, secC = Math.sqrt(1 + sC * sC), sinC = sC / secC, cosC = 1 / secC;
    const vc = pw.climb > 0 ? Math.min(vFlat, p.keff * pw.climb / (p.Crr * mg * cosC + mg * sinC)) : vFlat;
    Eclimb = (aRoll + 0.5 * p.rho * p.CdA * (vc + w) * Math.abs(vc + w) / p.keff) * xC + beta * hpC;
  }
  let Edesc = 0;
  if (xD > 0) {   // descent: clamp / equilibrium on the descent TOTAL at the mean descent grade s̄₋
    const sD = hmD / xD, secD = Math.sqrt(1 + sD * sD), sinD = -sD / secD, cosD = 1 / secD;
    if (descentMode === 'R1a') Edesc = Math.max(0, (aRoll + aAeroFlat) * xD - eps * beta * hmD);
    else if (descentMode === 'R1b') { const vD = descentEqSpeed(pw.descent, sD, { ...p, vmax: VMAX }, VMAX); Edesc = (pw.descent > 0 ? pw.descent : 0) * (xD * secD / vD); }
    else { const deficit = p.Crr * mg * cosD + 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) + mg * sinD; Edesc = Math.max(0, deficit) * xD * secD / p.keff; }
  }
  return { E: (Eflat + Eclimb + Edesc) / 1000, Eflat: Eflat / 1000, Eclimb: Eclimb / 1000, Edesc: Edesc / 1000 };
}

// R1d — the DEPLOYED sampasimu cost (Entry 18 pre-registration): per-edge VERBATIM v2Edge over the
// same profile. Unlike R1a's ride-frozen ε̄, ε is GRADE-LOCAL, recomputed from each edge's own grade:
// ε(s) = clamp₀₁(min(1, (α/β)/s) − 0.13), s = |dh|/dx. Roll always; aero charged iff dh < climbThr·dx
// (zero on climbs, full flat aero on descents — the champion's cf gating); β·dh uphill; NO regime
// powers — information budget ≡ R0 (P_flat + geometry + the frozen −0.13). The trailing max(0,·) is
// provably dead (Entry 18 / verify_v2edge_clamp.mjs); we keep it verbatim AND track the pre-clamp
// minimum so the run machine-asserts the dead-clamp claim on real data.
let R1D_MIN_PRECLAMP = Infinity;
function r1dV2Edge(prof, p, pw, climbThr) {
  const mg = p.m * G, beta = mg / p.keff, w = p.wind;
  const vFlat = Math.max(0.05, flatEqSpeed(pw.flat > 0 ? pw.flat : 1, p));
  const aRoll = mg * p.Crr / p.keff;
  const aAero = 0.5 * p.rho * p.CdA * (vFlat + w) * Math.abs(vFlat + w) / p.keff;
  const abRatio = (aRoll + aAero) / beta;   // α/β, same physics family as the champion's ε_geom
  const xs = prof.x, hs = prof.h;
  let E = 0;
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    if (!(dx > 0)) continue;
    let e;
    if (dh >= 0) {
      const aero = (dh < climbThr * dx) ? aAero * dx : 0;
      e = aRoll * dx + aero + beta * dh;
    } else {
      const ndh = -dh;
      let eps = abRatio * dx / ndh;
      if (eps > 1) eps = 1;
      eps -= 0.13;
      if (eps < 0) eps = 0;
      e = aRoll * dx + aAero * dx - eps * beta * ndh;
      if (e < R1D_MIN_PRECLAMP) R1D_MIN_PRECLAMP = e;
      if (e < 0) e = 0;
    }
    E += e;
  }
  return E / 1000;
}

// R0 champion — smooth (cf + 2 m deadband) AND poor-man's scalar, VERBATIM formulae from
// ppaz_compare.mjs pass B (aSm/aRaw/km/eSm/ePm). eps = the descent recovery the caller supplies.
function r0Champion(prof, profS, p, pw, eps) {
  const vf = flatEqSpeed(pw.flat, p), beta = p.m * G / p.keff;
  const aSm = approxComponents(profS, p, vf, pw), aRaw = approxComponents(prof, p, vf, pw);
  const km = aRaw.hplus > 0 ? Math.max(0, 1 - 3 * (prof.x[prof.x.length - 1] / 1000) / aRaw.hplus) : 1;
  const eSm = (aSm.roll + aSm.aero + aSm.climb - eps * beta * aSm.hminus) / 1000;
  const ePm = (aRaw.roll + aRaw.aero + km * (aRaw.climb - eps * beta * aRaw.hminus)) / 1000;
  return { eSm, ePm, vf };
}

// Per-point 30 m-window grade (VERBATIM logic from extractRegimePowers) computed ONCE, so the
// threshold sweep re-bins cheaply. binGrades(pd, ct, dt) MUST equal extractRegimePowers(ct, dt)
// (asserted in the sanity gate).
function pointRegimeData(pts) {
  const W = 30, out = [];
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].power === undefined) continue;
    if (pts[i].v !== undefined && pts[i].v < VSTOP) continue;
    let j = i; while (j < pts.length - 1 && pts[j].x - pts[i].x < W) j++;
    const dd = pts[j].x - pts[i].x;
    let grade;
    if (dd > 1) grade = (pts[j].alt - pts[i].alt) / dd;
    else { let k = i; while (k > 0 && pts[i].x - pts[k].x < W) k--; const db = pts[i].x - pts[k].x; grade = db > 1 ? (pts[i].alt - pts[k].alt) / db : 0; }
    out.push({ p: pts[i].power, w: pts[i].dt || 1, grade });
  }
  return out;
}
function binGrades(pd, ct, dt) {
  const bins = [[], [], []];
  for (const s of pd) bins[s.grade >= ct ? 2 : s.grade <= dt ? 0 : 1].push(s);
  const stat = b => { if (!b.length) return null; let sw = 0, swp = 0; for (const s of b) { sw += s.w; swp += s.w * s.p; } return sw ? swp / sw : null; };
  return { descent: stat(bins[0]), flat: stat(bins[1]), climb: stat(bins[2]) };
}
const pwFrom = (rp, pts) => { const flat = rp.flat != null ? rp.flat : overallMeanPower(pts); return { climb: rp.climb != null ? rp.climb : flat, flat, descent: rp.descent != null ? rp.descent : 0 }; };

const dPct = (model, emp) => emp > 0 ? (model - emp) / emp * 100 : NaN;

// ===== per-ride processing =====
const rows = [];
const sweep = { longoes: {}, censo: {}, ppaz: {}, jaam: {}, danlessa: {} };
function sweepKey(ct, dt) { return `${(ct * 100).toFixed(1)}/${(dt * 100).toFixed(1)}`; }

function processRide(pts, p0, label, corpus, epsRule) {
  if (!hasPower(pts)) return;
  buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
  const prof = resampleProfile(physProfile, ENGINE_DX);
  const profS = { x: prof.x, h: deadband(prof.h, TAU_SMOOTH) };
  const p = { ...p0, vmax: VMAX, vstart: VSTART };
  const mg = p.m * G, w = p.wind, beta = mg / p.keff;
  const emp = empiricalKJ(pts);
  if (!(emp > 0)) return;
  const pd = pointRegimeData(pts);
  const pw = pwFrom(binGrades(pd, CLIMB_THR, DESC_THR), pts);
  const thr = { climbThr: CLIMB_THR, descThr: DESC_THR };
  const vf = flatEqSpeed(pw.flat, p);
  // ε corpus rule: urban → flat 0.20; open → frozen ε_geom (−0.13), on the RAW profile (as R0)
  let eps = 0.20;
  if (epsRule !== 'urban') { const eg = epsGeom(prof, p, vf); eps = Number.isFinite(eg) ? eg : 0.20; }
  const r0 = r0Champion(prof, profS, p, pw, eps);
  // canonical selects power by local grade via pw.climbThr/descThr — must carry them (unlike the
  // closed-form paths, which take thresholds separately). Missing them ⇒ flat power everywhere.
  const canon = canonical(prof, { ...pw, climbThr: CLIMB_THR, descThr: DESC_THR }, p).legE / 1000;
  const R1a = regimeComponents(profS, p, pw, thr, eps, 'R1a');   // per-edge (sampasimu v2Edge-style)
  const R1b = regimeComponents(profS, p, pw, thr, eps, 'R1b');
  const R1c = regimeComponents(profS, p, pw, thr, eps, 'R1c');
  const R1aT = regimeTotals(profS, p, pw, thr, eps, 'R1a');       // TOTALS (apt closed form, matches R0)
  const R1bT = regimeTotals(profS, p, pw, thr, eps, 'R1b');
  const R1cT = regimeTotals(profS, p, pw, thr, eps, 'R1c');
  // R1d — deployed v2Edge (grade-local ε; Entry 18). Headline on the same deadband 5 m profile as
  // R1a/R0 (champion-matched); sensitivity grid = resolution × smoothing, because grade-local ε is
  // resolution-sensitive in a way the aggregate ε is not. Resolutions map to the deployment's real
  // elevation grids — 30 m ↔ FABDEM (what sampasimu serves), 5 m ↔ IGC-SP DTM (survey truth) — but
  // note we RESAMPLE the ride's own track at those spacings; source elevation bias is §8.7's k_DEM,
  // a separate axis. Smoothing: deadband τ=2 vs raw (the deployed default is k_s = 1, i.e. raw).
  const R1d = r1dV2Edge(profS, p, pw, CLIMB_THR);                 // 5 m + deadband (headline)
  const R1d5r = r1dV2Edge(prof, p, pw, CLIMB_THR);                // 5 m raw
  const prof30 = resampleProfile(physProfile, 30);
  const R1d30 = r1dV2Edge({ x: prof30.x, h: deadband(prof30.h, TAU_SMOOTH) }, p, pw, CLIMB_THR);   // 30 m + deadband
  const R1d30r = r1dV2Edge(prof30, p, pw, CLIMB_THR);             // 30 m raw (deployment-faithful)
  // E_new2 (R2) — TOTALS decomposition (Danilo): E_flat(d=x,P₌,h=0) + E_climb(d=0,P₊,h₊) +
  // E_descent(d=0,P₋,h₋) = α(P₌)·x + β·h₊ − ε·β·h₋, aero over the FULL distance at flat speed (no
  // climb-aero split — the 'off' aero mode), on the deadband profile. With d=0 the climb/descent
  // POWERS drop out (they'd scale a zero distance); β·h± carries them (E_climb≈P₊·t₊≈β·h₊, pure lift).
  const aSm = approxComponents(profS, p, vf, pw);
  const aAeroFull = 0.5 * p.rho * p.CdA * (vf + w) * Math.abs(vf + w) / p.keff;
  const R2 = (aSm.roll + aAeroFull * aSm.X + aSm.climb - eps * beta * aSm.hminus) / 1000;
  // adaptive ±α/β threshold: α/β from the default-threshold v_f (one-shot, no iteration); regime
  // powers RE-EXTRACTED at ±α/β (thread the same thresholds through powers and geometry).
  const ab = p.Crr + 0.5 * p.rho * p.CdA * (vf + w) * Math.abs(vf + w) / mg;
  const thrA = { climbThr: ab, descThr: -ab };
  const pwA = pwFrom(binGrades(pd, ab, -ab), pts);
  const R1a_ad = regimeComponents(profS, p, pwA, thrA, eps, 'R1a');
  // measured per-regime energy (Σ P·dt over the SAME 30 m classifier; assignment is definitional)
  const rs = extractRegimeStats(pts, CLIMB_THR, DESC_THR);
  const eMclimb = (rs.Pclimb != null ? rs.Pclimb : 0) * rs.tC / 1000;
  const eMflat = (rs.Pflat != null ? rs.Pflat : 0) * rs.tF / 1000;
  const eMdesc = (rs.Pdesc != null ? rs.Pdesc : 0) * rs.tD / 1000;
  // threshold sweep on R1a (ε held at the default-threshold value; powers re-extracted per cell)
  for (const ct of SWEEP_CLIMB) for (const dt of SWEEP_DESC) {
    const e = regimeComponents(profS, p, pwFrom(binGrades(pd, ct, dt), pts), { climbThr: ct, descThr: dt }, eps, 'R1a').E;
    (sweep[corpus][sweepKey(ct, dt)] ??= []).push(Math.abs(dPct(e, emp)));
  }
  rows.push({
    corpus, ride: label, emp, km: prof.x[prof.x.length - 1] / 1000, vf_kmh: vf * 3.6, ab, eps,
    r0sm: r0.eSm, r0pm: r0.ePm, canon, r1a: R1a.E, r1b: R1b.E, r1c: R1c.E, r1a_ad: R1a_ad.E, r2: R2,
    r1a_t: R1aT.E, r1b_t: R1bT.E, r1c_t: R1cT.E, r1d: R1d, r1d5r: R1d5r, r1d30: R1d30, r1d30r: R1d30r,
    r1a_flat: R1a.Eflat, r1a_climb: R1a.Eclimb, r1a_desc: R1a.Edesc,
    xF: R1a.xF, xC: R1a.xC, xD: R1a.xD, hpC: R1a.hpC, hmD: R1a.hmD, eMclimb, eMflat, eMdesc,
    d_r0sm: dPct(r0.eSm, emp), d_r0pm: dPct(r0.ePm, emp), d_canon: dPct(canon, emp),
    d_r1a: dPct(R1a.E, emp), d_r1b: dPct(R1b.E, emp), d_r1c: dPct(R1c.E, emp), d_r1a_ad: dPct(R1a_ad.E, emp), d_r2: dPct(R2, emp),
    d_r1a_t: dPct(R1aT.E, emp), d_r1b_t: dPct(R1bT.E, emp), d_r1c_t: dPct(R1cT.E, emp),
    d_r1d: dPct(R1d, emp), d_r1d5r: dPct(R1d5r, emp), d_r1d30: dPct(R1d30, emp), d_r1d30r: dPct(R1d30r, emp),
    d_rc: dPct(R1a.Eclimb, eMclimb), d_rf: dPct(R1a.Eflat, eMflat), d_rd: dPct(R1a.Edesc, eMdesc),
  });
}

// ===== sanity gates (SANITY=1 → synthetic checks then exit, before touching the corpora) =====
if (process.env.SANITY) {
  const approx = (a, b, tol = 1e-6) => Math.abs(a - b) <= tol * (1 + Math.abs(b));
  const pFlat = { m: 78, CdA: 0.40, Crr: 0.008, rho: 1.13, keff: 0.98, wind: 0, vmax: VMAX, vstart: VSTART };
  const mkProf = (n, dx, slopeFn) => { const x = new Float64Array(n), h = new Float64Array(n); for (let i = 0; i < n; i++) { x[i] = i * dx; h[i] = i > 0 ? h[i - 1] + slopeFn(i) * dx : 0; } return { x, h }; };
  let ok = true; const say = (name, pass, extra = '') => { console.log(`  [${pass ? 'PASS' : 'FAIL'}] ${name}${extra ? '  ' + extra : ''}`); if (!pass) ok = false; };

  const spts = []; for (let i = 0; i < 400; i++) spts.push({ x: i * 7, alt: 100 + 20 * Math.sin(i / 15), power: 150 + (i % 20), v: 6, dt: 1 });
  const rpE = extractRegimePowers(spts, CLIMB_THR, DESC_THR), rpB = binGrades(pointRegimeData(spts), CLIMB_THR, DESC_THR);
  say('binGrades ≡ extractRegimePowers', ['climb', 'flat', 'descent'].every(k => (rpE[k] == null && rpB[k] == null) || approx(rpE[k], rpB[k], 1e-9)));

  const prof = mkProf(2001, 5, i => 0.03 * Math.sin(i / 40));
  const pw = { climb: 200, flat: 150, descent: 80 };
  const vFlat = flatEqSpeed(pw.flat, pFlat), mg = pFlat.m * G, beta = mg / pFlat.keff;
  const aRoll = mg * pFlat.Crr / pFlat.keff, aAero = 0.5 * pFlat.rho * pFlat.CdA * vFlat * Math.abs(vFlat) / pFlat.keff;
  let X = 0, sumdh = 0; for (let i = 1; i < prof.x.length; i++) { X += prof.x[i] - prof.x[i - 1]; sumdh += prof.h[i] - prof.h[i - 1]; }
  const rawV1 = (aRoll * X + aAero * X + beta * sumdh) / 1000;
  const allFlat = regimeComponents(prof, pFlat, pw, { climbThr: 1e9, descThr: -1e9 }, 0.2, 'R1a').E;
  say('reduction: all-flat R1a == raw v1 law', approx(allFlat, rawV1), `R1a ${allFlat.toFixed(4)} vs v1 ${rawV1.toFixed(4)}`);

  const rc = regimeComponents(prof, pFlat, pw, { climbThr: CLIMB_THR, descThr: DESC_THR }, 0.2, 'R1a');
  say('additivity Σ components == E', approx(rc.Eflat + rc.Eclimb + rc.Edesc, rc.E, 1e-9));

  const flatProf = mkProf(2001, 5, () => 0), flatProfS = { x: flatProf.x, h: deadband(flatProf.h, TAU_SMOOTH) };
  const eqPw = { climb: pw.flat, flat: pw.flat, descent: pw.flat, climbThr: CLIMB_THR, descThr: DESC_THR };
  const rcF = regimeComponents(flatProfS, pFlat, eqPw, { climbThr: CLIMB_THR, descThr: DESC_THR }, 0.2, 'R1a');
  const r0F = r0Champion(flatProf, flatProfS, pFlat, eqPw, 0.2);
  const canF = canonical(flatProf, eqPw, pFlat).legE / 1000;
  say('flat anchor: R1a == R0.eSm', approx(rcF.E, r0F.eSm, 1e-6), `${rcF.E.toFixed(3)} vs ${r0F.eSm.toFixed(3)}`);
  say('flat anchor: R1a ≈ canonical (≤1.5%)', Math.abs(rcF.E - canF) / canF < 0.015, `R1a ${rcF.E.toFixed(2)} vs canon ${canF.toFixed(2)}`);

  const climbProf = mkProf(2001, 5, () => 0.06), climbProfS = { x: climbProf.x, h: deadband(climbProf.h, TAU_SMOOTH) };
  const rcC = regimeComponents(climbProfS, pFlat, { climb: 250, flat: 200, descent: 0 }, { climbThr: CLIMB_THR, descThr: DESC_THR }, 0.2, 'R1a');
  const peFloor = beta * climbProf.h[climbProf.h.length - 1] / 1000;
  say('pure climb: E_climb ≥ PE floor', rcC.Eclimb >= peFloor - 1e-6, `E_climb ${rcC.Eclimb.toFixed(1)} ≥ PE ${peFloor.toFixed(1)}`);
  // monotone climb ⇒ no spurious descent regime; the 2 m deadband lag leaves a short flat base
  // segment (roll+aero, no gravity), so climb must merely DOMINATE, not be the only regime.
  say('pure climb: no spurious descent + climb dominates', approx(rcC.Edesc, 0) && rcC.Eclimb / rcC.E > 0.97, `E_desc ${rcC.Edesc.toFixed(3)} · climb frac ${(rcC.Eclimb / rcC.E).toFixed(3)}`);

  // regimeTotals: same reduction + additivity, and it must EQUAL regimeComponents where there is no
  // nonlinearity to diverge on — a CONSTANT-grade climb (raw profile: single v_c, no clamp) ⇒ totals ≡ per-edge.
  const tAllFlat = regimeTotals(prof, pFlat, pw, { climbThr: 1e9, descThr: -1e9 }, 0.2, 'R1a').E;
  say('regimeTotals reduction: all-flat == raw v1', approx(tAllFlat, rawV1), `${tAllFlat.toFixed(4)} vs ${rawV1.toFixed(4)}`);
  const tc = regimeTotals(prof, pFlat, pw, { climbThr: CLIMB_THR, descThr: DESC_THR }, 0.2, 'R1a');
  say('regimeTotals additivity', approx(tc.Eflat + tc.Eclimb + tc.Edesc, tc.E, 1e-9));
  const cePw = { climb: 250, flat: 200, descent: 0 }, ct = { climbThr: CLIMB_THR, descThr: DESC_THR };
  const ceEdge = regimeComponents(climbProf, pFlat, cePw, ct, 0.2, 'R1a'), ceTot = regimeTotals(climbProf, pFlat, cePw, ct, 0.2, 'R1a');
  say('constant-grade climb: totals ≡ per-edge', Math.abs(ceEdge.E - ceTot.E) / ceTot.E < 1e-3, `edge ${ceEdge.E.toFixed(2)} vs totals ${ceTot.E.toFixed(2)}`);

  // R1d gates (Entry 18): (a) no-descent profile + climbThr=∞ reduces to raw v1 α·x + β·h₊;
  // (b) constant-grade descent ⇒ R1d ≡ R0.eSm exactly (grade-local ε = aggregate ε_geom, no Jensen
  // gap by construction); (c) pre-clamp positivity (asserted on the real corpora in the main run).
  const dPw = { climb: 200, flat: 150, descent: 60 };
  const r1dClimb = r1dV2Edge(climbProf, pFlat, dPw, 1e9);
  let cX = 0, cH = 0; for (let i = 1; i < climbProf.x.length; i++) { cX += climbProf.x[i] - climbProf.x[i - 1]; cH += climbProf.h[i] - climbProf.h[i - 1]; }
  const vD = flatEqSpeed(dPw.flat, pFlat);
  const aR = mg * pFlat.Crr / pFlat.keff, aA = 0.5 * pFlat.rho * pFlat.CdA * vD * Math.abs(vD) / pFlat.keff;
  const v1Climb = (aR * cX + aA * cX + beta * cH) / 1000;
  say('R1d reduction: no-descent + climbThr=∞ == raw v1', approx(r1dClimb, v1Climb), `${r1dClimb.toFixed(3)} vs ${v1Climb.toFixed(3)}`);
  const descProf = mkProf(2001, 5, () => -0.05), descProfS = { x: descProf.x, h: deadband(descProf.h, TAU_SMOOTH) };
  const epsD = epsGeom(descProf, pFlat, vD);
  const r0D = r0Champion(descProf, descProfS, pFlat, { ...dPw, climbThr: CLIMB_THR, descThr: DESC_THR }, epsD);
  const r1dD = r1dV2Edge(descProfS, pFlat, dPw, CLIMB_THR);
  say('R1d ≡ R0 on constant-grade descent (no Jensen gap)', Math.abs(r1dD - r0D.eSm) / Math.abs(r0D.eSm) < 1e-6, `R1d ${r1dD.toFixed(4)} vs R0 ${r0D.eSm.toFixed(4)} (ε_geom ${epsD.toFixed(3)})`);
  say('R1d pre-clamp positivity (synthetics)', R1D_MIN_PRECLAMP > 0, `min ${R1D_MIN_PRECLAMP.toExponential(2)} J`);

  console.log(ok ? '\nSANITY: ALL PASS' : '\nSANITY: FAILURES ABOVE');
  process.exit(ok ? 0 : 1);
}

// ===== drivers =====
let nL = 0, nC = 0, nP = 0, nJ = 0, nD = 0, zwTot = 0;
// longões (per-ride physics from model_inputs.json)
try {
  const inputs = JSON.parse(fs.readFileSync(path.join(HERE, 'model_inputs.json'), 'utf8'));
  for (const e of inputs) {
    if (!e.file || !e.has_power || !fs.existsSync(path.join(HERE, e.file))) continue;
    const p = { m: e.m, Crr: e.crr, CdA: e.cda, rho: e.rho, keff: e.keff, wind: (e.wind_kmh || 0) / 3.6 };
    try { processRide(readPts(e.file), p, e.label, 'longoes', 'open'); nL++; } catch (er) { /* skip */ }
  }
} catch (e) { console.error('longões load error', e.message); }
console.log(`longões: ${nL} power rides`);

// censo (ASSUMED rider, physical-floor filter — same as censo_compare/time_compare)
try {
  const man = JSON.parse(fs.readFileSync(path.join(HERE, 'censohidrografico', 'manifest.json'), 'utf8'));
  for (const e of man) {
    if (!e.file || !fs.existsSync(path.join(HERE, e.file))) continue;
    try {
      const pts = readPts(e.file);
      if (!hasPower(pts)) continue;
      const p = { ...ASSUMED, vmax: VMAX, vstart: VSTART };
      buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
      const profS = { x: resampleProfile(physProfile, ENGINE_DX).x, h: deadband(resampleProfile(physProfile, ENGINE_DX).h, TAU_SMOOTH) };
      const aSm = approxComponents(profS, p, flatEqSpeed(overallMeanPower(pts), p), null);
      if (empiricalKJ(pts) < (p.m * G / p.keff) * aSm.hplus / 1000) continue;   // dataOK floor
      processRide(pts, ASSUMED, e.name, 'censo', 'urban'); nC++;
    } catch (er) { /* skip */ }
  }
} catch (e) { console.error('censo load error', e.message); }
console.log(`censo: ${nC} rides (physical floor)`);

// independent riders + author full export (manifest, physics frozen + env overrides, Zwift excluded)
for (const [corpus, manifest] of [
  ['ppaz', 'strava_ppaz_manifest.json'],
  ['jaam', 'strava_jaam_manifest.json'],
  ['danlessa', 'strava_danlessa_manifest.json'],
]) {
  const phys = PHYS[corpus];
  let n = 0, zw = 0;
  try {
    const man = JSON.parse(fs.readFileSync(path.join(HERE, manifest), 'utf8'));
    const cand = man.filter(a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20 && a.altCov >= 0.99);
    for (const a of cand) {
      try {
        const pts = readPts(a.file);
        if (FIT_MANUF === ZWIFT) { zw++; continue; }
        processRide(pts, phys, a.id, corpus, 'open'); n++;
      } catch (er) { /* skip */ }
      if (n % 200 === 0 && n) console.log(`  …${corpus} ${n}/${cand.length}`);
    }
  } catch (e) { console.error(`${corpus} load error`, e.message); }
  zwTot += zw;
  if (corpus === 'ppaz') nP = n; else if (corpus === 'jaam') nJ = n; else nD = n;
  console.log(`${corpus}: ${n} rides (skipped ${zw} Zwift), m ${phys.m} kg · CdA ${phys.CdA} · Crr ${phys.Crr}`);
}

// ===== reporting =====
const byCorpus = c => rows.filter(r => r.corpus === c);
const CORP = [['longoes', 'longões (open, per-ride physics)'], ['censo', 'censo (urban, assumed)'], ['ppaz', 'P. Paz (open, assumed)'], ['jaam', 'JAAM (open, assumed)'], ['danlessa', 'author full (open, in-sample)']];
const f = (x, d = 1) => (x == null || Number.isNaN(x) || !Number.isFinite(x)) ? '—' : x.toFixed(d);
const KEYS = [['d_r0sm', 'R0 champion (cf+2m smooth)'], ['d_r0pm', 'R0 poor-man scalar'], ['d_canon', 'canonical (forward sim)'], ['d_r1a', 'R1a regime (ε clamp)'], ['d_r1b', 'R1b regime (P₋·t₋)'], ['d_r1c', 'R1c regime (force-deficit)'],
  ['d_r1a_t', 'R1a TOTALS (ε clamp)'], ['d_r1b_t', 'R1b TOTALS (P₋·t₋)'], ['d_r1c_t', 'R1c TOTALS (force-def)'],
  ['d_r1d', 'R1d v2Edge (grade-local ε)'],
  ['d_r2', 'R2 totals (α·x+β(h₊−εh₋))'], ['d_r1a_ad', 'R1a adaptive ±α/β']];

console.log('\n================================================================');
console.log('REGIME-DECOMPOSED MODEL — median |Δ%| vs measured ∫P·dt, per corpus');
console.log('(all share the same regime powers; canonical on the raw profile, R0/R1*/R2 on the 2 m');
console.log(' deadband profile — the established convention. The R1a-vs-R0 endpoint is profile-matched.)');
for (const [c, title] of CORP) {
  const set = byCorpus(c); if (!set.length) continue;
  console.log(`\n── ${title} ──  n=${set.length}`);
  console.log(`${'model'.padEnd(30)}${'med|Δ%|'.padStart(9)}${'medΔ%'.padStart(8)}`);
  for (const [k, lab] of KEYS) {
    const ds = set.map(r => r[k]).filter(Number.isFinite);
    console.log(`${lab.padEnd(30)}${f(medOf(ds.map(Math.abs))).padStart(9)}${f(medOf(ds)).padStart(8)}`);
  }
  console.log(`  median: ${f(medOf(set.map(r => r.km)))} km · v_f ${f(medOf(set.map(r => r.vf_kmh)))} km/h · α/β ${f(medOf(set.map(r => r.ab * 100)), 2)}% · ε ${f(medOf(set.map(r => r.eps)), 2)}`);
}

// paired sign + Wilcoxon (normal approx) on per-ride |Δ%|, A vs B (both already |Δ%| via keys)
function erf(x) { const t = 1 / (1 + 0.3275911 * Math.abs(x)); const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x); return x >= 0 ? y : -y; }
const pFromZ = z => Number.isFinite(z) ? 2 * (1 - 0.5 * (1 + erf(Math.abs(z) / Math.SQRT2))) : NaN;
function pairedAbs(set, kA, kB) {
  const d = []; let wins = 0, losses = 0;
  for (const r of set) {
    const a = Math.abs(r[kA]), b = Math.abs(r[kB]);
    if (!Number.isFinite(a) || !Number.isFinite(b)) continue;
    d.push(a - b); if (a < b) wins++; else if (a > b) losses++;   // A better ⇒ smaller |Δ%|
  }
  const n = wins + losses, zSign = n > 0 ? (wins - n / 2) / Math.sqrt(n / 4) : NaN;
  const nz = d.filter(x => x !== 0).map(x => ({ a: Math.abs(x), s: Math.sign(x) })).sort((p, q) => p.a - q.a);
  let i = 0, Wpos = 0; const m = nz.length;
  while (i < m) { let j = i; while (j < m - 1 && nz[j + 1].a === nz[i].a) j++; const rank = (i + j + 2) / 2; for (let k = i; k <= j; k++) if (nz[k].s > 0) Wpos += rank; i = j + 1; }
  const muW = m * (m + 1) / 4, sdW = Math.sqrt(m * (m + 1) * (2 * m + 1) / 24), zW = sdW > 0 ? (Wpos - muW) / sdW : NaN;
  return { wins, losses, n, winFrac: n ? wins / n : NaN, medDiff: medOf(d), pSign: pFromZ(zSign), pWilcoxon: pFromZ(zW) };
}

console.log('\n================================================================');
console.log('PRE-DECLARED PRIMARY ENDPOINT — R1a vs R0 (cf+2m smooth), P. Paz, med|Δ%| vs ∫P·dt');
const Pset = byCorpus('ppaz');
const r1aMed = medOf(Pset.map(r => Math.abs(r.d_r1a)).filter(Number.isFinite));
const r0Med = medOf(Pset.map(r => Math.abs(r.d_r0sm)).filter(Number.isFinite));
const pt = pairedAbs(Pset, 'd_r1a', 'd_r0sm');
console.log(`  R1a ${f(r1aMed)}%  vs  R0 ${f(r0Med)}%   (n=${Pset.length})`);
console.log(`  paired R1a−R0: R1a better on ${pt.wins}/${pt.n} (${f(pt.winFrac * 100, 0)}%) · med Δ|Δ%| ${f(pt.medDiff, 2)}pp · sign p=${f(pt.pSign, 3)} · Wilcoxon p=${f(pt.pWilcoxon, 3)}`);
console.log('================================================================');

console.log('\nENTRY-18 PRE-REGISTERED ENDPOINT — R1d (deployed v2Edge, grade-local ε) vs R0, P. Paz');
const r1dMed = medOf(Pset.map(r => Math.abs(r.d_r1d)).filter(Number.isFinite));
const pt18 = pairedAbs(Pset, 'd_r1d', 'd_r0sm');
console.log(`  R1d ${f(r1dMed)}%  vs  R0 ${f(r0Med)}%   (n=${Pset.length})`);
console.log(`  paired R1d−R0: R1d better on ${pt18.wins}/${pt18.n} (${f(pt18.winFrac * 100, 0)}%) · med Δ|Δ%| ${f(pt18.medDiff, 2)}pp · sign p=${f(pt18.pSign, 3)} · Wilcoxon p=${f(pt18.pWilcoxon, 3)}`);
// Jensen-direction check: grade-local ε gives MORE descent credit ⇒ R1d should predict LESS than R0
console.log('\n  Jensen direction (med per-ride r1d − r0sm, kJ; negative ⇒ R1d below R0 as predicted):');
for (const [c] of CORP) {
  const set = byCorpus(c); if (!set.length) continue;
  const dj = medOf(set.map(r => r.r1d - r.r0sm).filter(Number.isFinite));
  console.log(`    ${c.padEnd(10)} ${f(dj, 2)} kJ  (med |Δ%|: R1d ${f(medOf(set.map(r => Math.abs(r.d_r1d)).filter(Number.isFinite)))} vs R0 ${f(medOf(set.map(r => Math.abs(r.d_r0sm)).filter(Number.isFinite)))})`);
}
console.log('\n  R1d resolution×smoothing sensitivity (med |Δ%|): 5m+db (headline) · 5m raw · 30m+db (FABDEM-grid) · 30m raw (deployed default)');
for (const [c] of CORP) {
  const set = byCorpus(c); if (!set.length) continue;
  const g = k => f(medOf(set.map(r => Math.abs(r[k])).filter(Number.isFinite)));
  console.log(`    ${c.padEnd(10)} ${g('d_r1d')} · ${g('d_r1d5r')} · ${g('d_r1d30')} · ${g('d_r1d30r')}`);
}
console.log(`\n  dead-clamp assert: min pre-clamp descent edge across ALL rides = ${R1D_MIN_PRECLAMP.toExponential(2)} J ${R1D_MIN_PRECLAMP > 0 ? '(> 0 ✓ — the max(0,·) never fired)' : '(≤ 0 — CLAMP FIRED, Entry-18 claim violated!)'}`);

// HEAD-TO-HEAD (paired, each regime variant vs R0) on all THREE full open datasets on equal
// footing — P. Paz, JAAM, and the author's full export. The author is rider 1 (in-sample for the
// ε/−0.13 calibration), but R0 and every R1* SHARE that frozen calibration, so it cancels in the
// paired Δ — the head-to-head isolates the parameter-free regime split, a fair test even in-sample.
console.log('\n---------------- HEAD-TO-HEAD: regime variants vs R0 champion (paired) ----------------');
for (const [c, title] of [['ppaz', 'P. Paz'], ['jaam', 'JAAM'], ['danlessa', 'author full (in-sample ε)']]) {
  const set = byCorpus(c); if (!set.length) continue;
  const mR0 = medOf(set.map(r => Math.abs(r.d_r0sm)).filter(Number.isFinite));
  console.log(`  ${title}  (n=${set.length}, R0 ${f(mR0)}%):`);
  for (const [k, lab] of [['d_r1a', 'R1a edge'], ['d_r1a_t', 'R1a totals'], ['d_r1c_t', 'R1c totals'], ['d_r2', 'R2 totals'], ['d_r1d', 'R1d v2Edge']]) {
    const t = pairedAbs(set, k, 'd_r0sm'), mA = medOf(set.map(r => Math.abs(r[k])).filter(Number.isFinite));
    console.log(`     ${lab} ${f(mA)}%  · ${lab} better ${t.wins}/${t.n} (${f(t.winFrac * 100, 0)}%) · sign p=${f(t.pSign, 3)} · Wilcoxon p=${f(t.pWilcoxon, 3)}`);
  }
}
console.log('================================================================');

// threshold sweep (R1a med|Δ%| surface per corpus) + adaptive comparison
console.log('\n---------------- THRESHOLD SWEEP (R1a med|Δ%|; rows=climbThr%, cols=descThr%) ----------------');
for (const [c, title] of CORP) {
  const sw = sweep[c]; if (!byCorpus(c).length) continue;
  console.log(`\n${title}:`);
  console.log(`climb\\desc ${SWEEP_DESC.map(d => (d * 100).toFixed(1).padStart(7)).join('')}`);
  let best = { v: Infinity, k: '' };
  for (const ct of SWEEP_CLIMB) {
    const cells = SWEEP_DESC.map(dt => { const arr = sw[sweepKey(ct, dt)] || []; const m = medOf(arr); if (m < best.v) best = { v: m, k: sweepKey(ct, dt) }; return f(m).padStart(7); });
    console.log(`${(ct * 100).toFixed(1).padStart(6)}    ${cells.join('')}`);
  }
  const adMed = medOf(byCorpus(c).map(r => Math.abs(r.d_r1a_ad)).filter(Number.isFinite));
  const defMed = medOf(byCorpus(c).map(r => Math.abs(r.d_r1a)).filter(Number.isFinite));
  console.log(`  best fixed cell ${best.k} = ${f(best.v)}% · default 2.0/-1.5 = ${f(defMed)}% · adaptive ±α/β = ${f(adMed)}% (med α/β ${f(medOf(byCorpus(c).map(r => r.ab * 100)), 2)}%)`);
}

// per-regime attribution (R1a component vs measured regime energy)
console.log('\n---------------- PER-REGIME ATTRIBUTION (R1a component vs measured ΣP·dt in that regime) ----------------');
console.log(`${'corpus'.padEnd(10)}${'climb|Δ%|'.padStart(11)}${'flat|Δ%|'.padStart(10)}${'desc|Δ%|'.padStart(10)}   (median; where measured regime energy > 1 kJ)`);
for (const [c] of CORP) {
  const set = byCorpus(c); if (!set.length) continue;
  const g = (k, mk) => medOf(set.filter(r => r[mk] > 1).map(r => Math.abs(r[k])).filter(Number.isFinite));
  console.log(`${c.padEnd(10)}${f(g('d_rc', 'eMclimb')).padStart(11)}${f(g('d_rf', 'eMflat')).padStart(10)}${f(g('d_rd', 'eMdesc')).padStart(10)}`);
}

// ===== CSV (gitignored via data/activities/*.csv) =====
const cols = ['corpus', 'ride', 'emp', 'km', 'vf_kmh', 'ab', 'eps', 'r0sm', 'r0pm', 'canon', 'r1a', 'r1b', 'r1c', 'r1a_t', 'r1b_t', 'r1c_t', 'r1d', 'r1d5r', 'r1d30', 'r1d30r', 'r1a_ad', 'r2', 'r1a_flat', 'r1a_climb', 'r1a_desc', 'xF', 'xC', 'xD', 'hpC', 'hmD', 'eMclimb', 'eMflat', 'eMdesc', 'd_r0sm', 'd_r0pm', 'd_canon', 'd_r1a', 'd_r1b', 'd_r1c', 'd_r1a_t', 'd_r1b_t', 'd_r1c_t', 'd_r1d', 'd_r1d5r', 'd_r1d30', 'd_r1d30r', 'd_r1a_ad', 'd_r2', 'd_rc', 'd_rf', 'd_rd'];
const csv = [cols.join(',')].concat(rows.map(r => cols.map(k => typeof r[k] === 'string' ? JSON.stringify(r[k]) : (Number.isFinite(r[k]) ? +Number(r[k]).toFixed(3) : '')).join(','))).join('\n');
fs.writeFileSync(path.join(HERE, 'regime_comparison.csv'), csv + '\n');
console.log(`\nwrote regime_comparison.csv (${rows.length} rides: L ${nL} C ${nC} P ${nP} J ${nJ} D ${nD}, skipped ${zwTot} Zwift)`);
