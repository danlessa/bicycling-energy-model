#!/usr/bin/env node
// AUTHOR full-export verification: the author's full Strava history export (strava_danlessa/, gitignored —
// third-party GPS shared with consent). The external-validity test the article's §10.4
// names as its deepest limitation: every prior number comes from ONE rider and ONE meter.
//
// Pipeline (engines are verbatim copies of censo_compare.mjs — keep the copies in sync):
//   0. inventory manifest from ppaz_inventory.mjs; keep sport=ride, power coverage >50%,
//      ≥20 km, altitude coverage ≥99%, not Zwift (file_id manufacturer 260).
//   1. PASS A — implied total mass: invert the sustained-climb energy balance
//      (climbBalance, verbatim from compare.mjs; Entry 7 machinery). On sustained climbs
//      measured ≈ (grav+roll)·(m/m0) + aero, all but aero linear in m, so
//      m̂ = m0·(emeas − eaero)/(egrav + eroll). Headline m̂ = median of per-ride m̂ over
//      rides with ≥ 200 m of sustained climb (robust to power dropouts).
//   2. PASS B — with m̂ frozen: canonical (fed the ride's own regime powers) + smooth
//      approx (2 m deadband) + poor-man's scalar, ε swept {geom, 0.00…0.25}; the censo
//      physical floor (∫P·dt ≥ m̂·g·h₊_sm/k_eff) + cadence cross-check.
//   3. ε AUTHOR CONSISTENCY TEST (rider 1 — the −0.13 offset was calibrated on this rider, so this is IN-SAMPLE-ish): per-ride descent-balance ε_bal vs geometric ε_coast on 30 m
//      cells (α at the MEASURED flat speed, VSTOP-gated). The estimators are FROZEN from
//      the first rider: clamp01(ε_coast − 0.13), flat 0.20, flat 0.23. Nothing here is
//      refit — this is out-of-sample across rider, meter, and terrain.
//
//   node ppaz_inventory.mjs && node ppaz_compare.mjs
//
// Output: console report + danlessa_comparison.csv (gitignored via data/activities/*.csv).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const G = 9.81, NS = 240;
const VMAX = 38 / 3.6, VSTART = 15 / 3.6;
const CLIMB_THR = 0.02, DESC_THR = -0.015, ENGINE_DX = 5, TAU_SMOOTH = 2;
// ASSUMED rider physics (same generic values as the censo run) — EXCEPT the mass,
// which pass A estimates from author's own sustained climbs (m0 = reference for the
// linear inversion). ρ São Paulo ≈ 1.13; wind 0; k_eff 0.98 (repo defaults).
const ASSUMED = { m: 78, CdA: 0.40, Crr: 0.008, rho: 1.13, keff: 0.98, wind: 0 };
// DANLESSA_CDA / DANLESSA_CRR: swap the generic assumed drag/rolling for the rider's own Entry-15 fitted
// values — the fitted-physics robustness test (do the conclusions survive the right constants?).
if (process.env.DANLESSA_CDA) ASSUMED.CdA = +process.env.DANLESSA_CDA;
if (process.env.DANLESSA_CRR) ASSUMED.Crr = +process.env.DANLESSA_CRR;
const M0 = 78;                      // reference mass for the climb-balance inversion
const MIN_SUSTAINED_DH = 200;       // m of sustained climb for a stable per-ride m̂
const EPS_SWEEP = [['geom', null], ['0.00', 0.00], ['0.05', 0.05], ['0.10', 0.10], ['0.15', 0.15], ['0.20', 0.20], ['0.25', 0.25]];
const ZWIFT = 260;                  // FIT file_id manufacturer id for Zwift (virtual rides)

let H = new Float64Array(NS), physProfile = null;
let FIT_MANUF;                      // file_id manufacturer, set by parseFIT per file

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

// ===== driver =====
const man = JSON.parse(fs.readFileSync(path.join(HERE, 'strava_danlessa_manifest.json'), 'utf8'));
const CAND = man.filter(a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20 && a.altCov >= 0.99);
console.log(`AUTHOR (danlessa) FULL-EXPORT VERIFICATION — ${CAND.length} candidate rides (ride, power>50%, ≥20 km, alt≥99%)`);

const readPts = file => {
  let buf = fs.readFileSync(path.join(HERE, file));
  if (file.endsWith('.gz')) buf = zlib.gunzipSync(buf);
  return ptsFromFIT(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
};

// ---- PASS A: implied total mass from the sustained-climb balance ----
const p0 = { ...ASSUMED, m: M0 };
const MH = [];                             // per-ride m̂
let SA = { emeas: 0, egrav: 0, eroll: 0, eaero: 0, dh: 0, n: 0 };
let zwift = 0, unparse = 0;
const usable = [];
for (const a of CAND) {
  try {
    const pts = readPts(a.file);
    if (FIT_MANUF === ZWIFT) { zwift++; continue; }
    if (!hasPower(pts)) continue;
    usable.push(a);
    const cb = climbBalance(pts, p0);
    if (cb.n > 0) {
      SA.emeas += cb.emeas; SA.egrav += cb.egrav; SA.eroll += cb.eroll; SA.eaero += cb.eaero;
      SA.dh += cb.dh; SA.n += cb.n;
      if (cb.dh >= MIN_SUSTAINED_DH) MH.push(M0 * (cb.emeas - cb.eaero) / (cb.egrav + cb.eroll));
    }
  } catch (err) { unparse++; }
}
const medOf = xs => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); const k = (s.length - 1) / 2; return s.length ? (s[Math.floor(k)] + s[Math.ceil(k)]) / 2 : NaN; };
const q = (xs, p) => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); return s.length ? s[Math.floor(p * (s.length - 1))] : NaN; };
const mGlobal = M0 * (SA.emeas - SA.eaero) / (SA.egrav + SA.eroll);
const mHat = medOf(MH);
console.log(`skipped: ${zwift} Zwift/virtual, ${unparse} unparseable\n`);
console.log('IMPLIED TOTAL MASS — sustained-climb balance (≥3% over ≥100 m), CdA/Crr/ρ assumed as censo');
console.log(`  ${SA.n} sections over ${usable.length} rides, Σ sustained Δh = ${Math.round(SA.dh)} m`);
console.log(`  global (energy-weighted) m̂ = ${mGlobal.toFixed(1)} kg`);
console.log(`  per-ride median m̂ = ${mHat.toFixed(1)} kg  [IQR ${q(MH, .25).toFixed(1)}–${q(MH, .75).toFixed(1)}, n=${MH.length}]`);
const M_USE = process.env.DANLESSA_M ? +process.env.DANLESSA_M : mHat;   // DANLESSA_M env: mass-sensitivity runs
console.log(`  → using m = ${M_USE.toFixed(1)} kg ${process.env.DANLESSA_M ? '(DANLESSA_M override)' : '(per-ride median; robust to power dropouts)'}\n`);

// ---- PASS B: full model comparison + ε cells, with m̂ frozen ----
const rows = [];
let done = 0;
for (const a of usable) {
  try {
    const pts = readPts(a.file);
    buildProfile(pts.map(qq => qq.x), pts.map(qq => qq.alt));
    const prof = resampleProfile(physProfile, ENGINE_DX);
    const profS = { x: prof.x, h: deadband(prof.h, TAU_SMOOTH) };
    const rp = extractRegimePowers(pts, CLIMB_THR, DESC_THR);
    const flat = rp.flat != null ? rp.flat : overallMeanPower(pts);
    const pw = { climb: rp.climb != null ? rp.climb : flat, flat, descent: rp.descent != null ? rp.descent : 0, climbThr: CLIMB_THR, descThr: DESC_THR };
    const p = { ...ASSUMED, m: M_USE, vmax: VMAX, vstart: VSTART };
    const vf = flatEqSpeed(pw.flat, p);
    const beta = p.m * G / p.keff;
    const emp = empiricalKJ(pts);
    const c = canonical(prof, pw, p);
    const aRaw = approxComponents(prof, p, vf, pw);
    const aSm = approxComponents(profS, p, vf, pw);
    const km = aRaw.hplus > 0 ? Math.max(0, 1 - 3 * (prof.x[prof.x.length - 1] / 1000) / aRaw.hplus) : 1;
    const epsG = epsGeom(prof, p, vf);
    const peFloor = beta * aSm.hplus / 1000;
    const dataOK = emp >= peFloor;
    const ps = pushStats(pts);
    const ec = epsCellsPz(pts, p);
    const row = { ride: a.id, date: a.date, dist_km: prof.x[prof.x.length - 1] / 1000,
      hplus: aRaw.hplus, hplus_sm: aSm.hplus, emp, peFloor, dataOK, push: ps.push, slow: ps.slow, cadCov: ps.cadCov,
      epsG, km, vf_kmh: vf * 3.6,
      epsBal: ec ? ec.epsBal : NaN, epsCoast: ec ? ec.epsCoast : NaN, sbar: ec ? ec.sbar : NaN, Hd: ec ? ec.Hd : NaN, vfMeas_kmh: ec ? ec.vf * 3.6 : NaN,
      canon: c.legE / 1000, canon_d: (c.legE / 1000 - emp) / emp * 100 };
    for (const [tag, ev] of EPS_SWEEP) {
      const eps = ev == null ? (Number.isFinite(epsG) ? epsG : 0.2) : ev;
      const eSm = (aSm.roll + aSm.aero + aSm.climb - eps * beta * aSm.hminus) / 1000;
      const ePm = (aRaw.roll + aRaw.aero + km * (aRaw.climb - eps * beta * aRaw.hminus)) / 1000;
      row[`sm_${tag}`] = (eSm - emp) / emp * 100;
      row[`pm_${tag}`] = (ePm - emp) / emp * 100;
    }
    rows.push(row);
  } catch (err) { /* skip */ }
  if (++done % 100 === 0) console.log(`  …pass B ${done}/${usable.length}`);
}

const f = (x, d = 1) => (x == null || Number.isNaN(x)) ? '—' : x.toFixed(d);
const clean = rows.filter(r => r.dataOK);
const flagged = rows.filter(r => !r.dataOK);
const stat = key => { const v = clean.map(r => Math.abs(r[key])).filter(Number.isFinite), s = clean.map(r => r[key]).filter(Number.isFinite);
  return { n: v.length, medAbs: medOf(v), medSigned: medOf(s), mean: s.reduce((x, y) => x + y, 0) / s.length }; };
const print = (lab, key) => { const s = stat(key); console.log(`${lab.padEnd(34)}${String(s.n).padStart(4)}${f(s.medAbs).padStart(9)}${f(s.medSigned).padStart(8)}${f(s.mean).padStart(8)}`); };

console.log(`\nHEADLINE on ${clean.length} clean rides (${flagged.length} excluded by the physical floor).`);
console.log(`geometry: dist median ${f(medOf(clean.map(r => r.dist_km)))} km · h₊ median ${f(medOf(clean.map(r => r.hplus)), 0)} m · v_f median ${f(medOf(clean.map(r => r.vf_kmh)))} km/h · ε_geom median ${f(medOf(clean.map(r => r.epsG)), 2)}\n`);
console.log(`Δ% vs empirical (− = under, + = over):`);
console.log(`${'model'.padEnd(34)}${'n'.padStart(4)}${'med|Δ%|'.padStart(9)}${'medΔ%'.padStart(8)}${'meanΔ%'.padStart(8)}`);
print('canonical (fed ride powers)', 'canon_d');
console.log('  -- smooth approx (2 m deadband) --');
for (const [t] of EPS_SWEEP) print(`  smooth · ε=${t}`, `sm_${t}`);
console.log("  -- poor-man's (scalar k_smooth) --");
for (const [t] of EPS_SWEEP) print(`  poor-man's · ε=${t}`, `pm_${t}`);

// ---- ε AUTHOR CONSISTENCY TEST (rider 1 — the −0.13 offset was calibrated on this rider, so this is IN-SAMPLE-ish) (the out-of-sample result) ----
const eOK = clean.filter(r => Number.isFinite(r.epsBal) && Number.isFinite(r.epsCoast));
const clamp01 = x => Math.max(0, Math.min(1, x));
const rms = (xs) => Math.sqrt(xs.reduce((s, x) => s + x * x, 0) / xs.length);
const corrOf = (xs, ys) => { const n = xs.length, mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
  let sxy = 0, sxx = 0, syy = 0; for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) ** 2; syy += (ys[i] - my) ** 2; }
  return sxy / Math.sqrt(sxx * syy); };
console.log('\n================================================================');
console.log('ε AUTHOR CONSISTENCY TEST (rider 1 — the −0.13 offset was calibrated on this rider, so this is IN-SAMPLE-ish) — estimators FROZEN from rider 1 (nothing refit)');
for (const [lab, sub] of [['all clean rides', eOK], ['s̄ ≥ 3%', eOK.filter(r => r.sbar >= 0.03)]]) {
  if (sub.length < 5) continue;
  const eb = sub.map(r => r.epsBal), ecst = sub.map(r => r.epsCoast);
  const flatIn = medOf(eb);
  console.log(`\n  -- ${lab} (n=${sub.length}) --`);
  console.log(`  med ε_bal ${f(medOf(eb), 2)} · med ε_coast ${f(medOf(ecst), 2)} · med s̄ ${f(medOf(sub.map(r => r.sbar)) * 100, 1)}% · corr ${f(corrOf(ecst, eb), 2)}`);
  console.log(`  RMS(ε_bal − pred):`);
  console.log(`    frozen  clamp01(ε_coast − 0.13)      ${f(rms(sub.map(r => r.epsBal - clamp01(r.epsCoast - 0.13))), 3)}`);
  console.log(`    frozen  flat ε = 0.20                ${f(rms(eb.map(x => x - 0.20)), 3)}`);
  console.log(`    frozen  flat ε = 0.23                ${f(rms(eb.map(x => x - 0.23)), 3)}`);
  console.log(`    in-sample flat = median ε_bal (${f(flatIn, 2)})  ${f(rms(eb.map(x => x - flatIn)), 3)}   <- author's own best constant`);
}

// ---- flagged + CSV ----
if (flagged.length) {
  console.log(`\nFLAGGED (excluded) — ∫P·dt below climbing PE (n=${flagged.length}); cadence coverage medians: ${f(medOf(flagged.map(r => r.cadCov)) * 100, 0)}%`);
}
const cols = Object.keys(rows[0]);
const csv = [cols.join(',')].concat(rows.map(r => cols.map(k => typeof r[k] === 'string' ? JSON.stringify(r[k]) : (Number.isFinite(r[k]) ? +Number(r[k]).toFixed(3) : r[k])).join(','))).join('\n');
fs.writeFileSync(path.join(HERE, 'danlessa_comparison.csv'), csv + '\n');
console.log(`\nwrote danlessa_comparison.csv (${rows.length} rides)`);
