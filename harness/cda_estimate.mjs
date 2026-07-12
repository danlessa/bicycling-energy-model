#!/usr/bin/env node
// Independent m / C_rr / CdA estimation for the shared riders (journal Entry 15). Engines
// (haversine, parseFIT, finishPts, ptsFromFIT) VERBATIM from ppaz_compare.mjs; ptsFromGPX
// verbatim from compare.mjs. New analysis in the driver.  node cda_estimate.mjs
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '..', 'data', 'activities');
const RESULTS = path.join(HERE, '..', 'results');
fs.mkdirSync(RESULTS, { recursive: true });
let FIT_MANUF; let physProfile = null;   // referenced by the verbatim engine; unused here

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

// ptsFromGPX — verbatim from compare.mjs
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

// ===== Independent CdA / mass / C_rr estimation (Entry 15) =====
// Naive flat-power regression fails (riders hold steady *effort*, not power → high flat speed
// pairs with low power → CdA<0). Coast-down / descent-terminal fails too (braking contaminates
// every descent; GPS-speed differentiation is noise; author anchor came out m≈40 kg, CdA<0).
//
// The clean signal is the CLIMB (JAAM/Danilo insight): on a positive slope BRAKING IS
// NEGLIGIBLE, so every watt the meter records goes into the physics. Over an uphill segment,
// the work–energy balance is exact:
//   k_eff·∫P·dt  =  ΔKE  +  W_grav  +  W_roll  +  W_aero
//     = ½m·Δ(v²) + m·g·Δh + C_rr·m·g·Δx + CdA·(½ρ∫v³dt)
//   ⇒  E_i = m·A_i + (C_rr·m)·B_i + CdA·C_i,  with
//       A_i = g·Δh_i + ½·Δ(v²)_i   (mass: gravity + kinetic)
//       B_i = g·Δx_i               (rolling: horizontal distance; Σcosθ·ds = Δx)
//       C_i = ½·ρ·Σ(v³·dt)_i       (aero work per unit CdA)
//       E_i = k_eff·Σ(P·dt)_i      (wheel work)
// A 3-parameter, no-intercept least squares over many climb segments returns m, C_rr, CdA
// with NO assumed value for any of them: grade variation separates gravity(A) from rolling(B),
// speed variation separates aero(C) from rolling(B).
//
// Segment recipe (Danilo): every sustained uphill with Δh > 40 m, CLIP the first 10 m of climb
// (kills the flat→climb entry inertia), measure over the rest. k_eff = 0.98, ρ = ISA(altitude),
// wind = 0 (climbs are slow ⇒ aero and wind both small — a caveat for CdA, not for m). Author
// longões = a method anchor (its per-ride CdA/m/C_rr are themselves assumptions, not truth).

const KEFF = 0.98, G = 9.81;
const rhoAt = h => 1.225 * Math.pow(1 - 2.25577e-5 * Math.max(0, Math.min(h, 11000)), 5.25588);
const median = xs => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); const k = (s.length - 1) / 2; return s.length ? (s[Math.floor(k)] + s[Math.ceil(k)]) / 2 : NaN; };

// 3-param no-intercept least squares  E = θ1·A + θ2·B + θ3·C  (3×3 normal equations, Gauss)
function ols3(A, B, C, E) {
  const n = E.length;
  const M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], y = [0, 0, 0];
  let syy = 0, my = 0; for (const e of E) my += e; my /= n;
  for (let i = 0; i < n; i++) {
    const f = [A[i], B[i], C[i]];
    for (let a = 0; a < 3; a++) { for (let b = 0; b < 3; b++) M[a][b] += f[a] * f[b]; y[a] += f[a] * E[i]; }
    syy += (E[i] - my) ** 2;
  }
  // Gaussian elimination on the 3×3
  const m = M.map((row, i) => [...row, y[i]]);
  for (let c = 0; c < 3; c++) {
    let piv = c; for (let r = c + 1; r < 3; r++) if (Math.abs(m[r][c]) > Math.abs(m[piv][c])) piv = r;
    [m[c], m[piv]] = [m[piv], m[c]];
    if (Math.abs(m[c][c]) < 1e-12) return { theta: [NaN, NaN, NaN], r2: NaN, n };
    for (let r = 0; r < 3; r++) if (r !== c) { const f = m[r][c] / m[c][c]; for (let k = c; k < 4; k++) m[r][k] -= f * m[c][k]; }
  }
  const theta = [m[0][3] / m[0][0], m[1][3] / m[1][1], m[2][3] / m[2][2]];
  let sse = 0; for (let i = 0; i < n; i++) { const e = E[i] - theta[0] * A[i] - theta[1] * B[i] - theta[2] * C[i]; sse += e * e; }
  return { theta, r2: 1 - sse / syy, n };
}
// 2-param no-intercept LS with CdA FIXED: subtract aero, fit E' = m·A + (Crr·m)·B
function ols2Fixed(A, B, C, E, cdaFix) {
  let s11=0,s12=0,s22=0,y1=0,y2=0;
  for (let i=0;i<E.length;i++){ const Ep=E[i]-cdaFix*C[i]; s11+=A[i]*A[i]; s12+=A[i]*B[i]; s22+=B[i]*B[i]; y1+=A[i]*Ep; y2+=B[i]*Ep; }
  const det=s11*s22-s12*s12; if(Math.abs(det)<1e-9) return {m:NaN,crr:NaN};
  const m=(y1*s22-y2*s12)/det, crrM=(s11*y2-s12*y1)/det; return {m, crr:crrM/m};
}
function corr(xs,ys){const n=xs.length;let mx=0,my=0;for(let i=0;i<n;i++){mx+=xs[i];my+=ys[i];}mx/=n;my/=n;let sxy=0,sxx=0,syy=0;for(let i=0;i<n;i++){sxy+=(xs[i]-mx)*(ys[i]-my);sxx+=(xs[i]-mx)**2;syy+=(ys[i]-my)**2;}return sxy/Math.sqrt(sxx*syy);}
// bootstrap CIs on (m, CdA, Crr) — resample segments with a fixed LCG (Math.random is unavailable/banned)
function bootstrap3(A, B, C, E, reps = 400) {
  const n = E.length; let seed = 12345;
  const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  const ms = [], cdas = [], crrs = [];
  for (let r = 0; r < reps; r++) {
    const a = [], b = [], c = [], e = [];
    for (let i = 0; i < n; i++) { const j = Math.floor(rnd() * n); a.push(A[j]); b.push(B[j]); c.push(C[j]); e.push(E[j]); }
    const f = ols3(a, b, c, e); if (!Number.isFinite(f.theta[0])) continue;
    ms.push(f.theta[0]); cdas.push(f.theta[2]); crrs.push(f.theta[1] / f.theta[0]);
  }
  const ci = arr => { const s = arr.slice().sort((x, y) => x - y); return [s[Math.floor(0.025 * s.length)], s[Math.floor(0.975 * s.length)]]; };
  return { mCI: ci(ms), cdaCI: ci(cdas), crrCI: ci(crrs) };
}

const slice = b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
function readPts(file) {
  let buf = fs.readFileSync(path.join(DATA, file));
  if (file.endsWith('.gz') && !file.endsWith('.gpx.gz')) buf = zlib.gunzipSync(buf);
  if (file.endsWith('.gpx')) return ptsFromGPX(buf.toString('utf8'));
  return ptsFromFIT(slice(buf));
}
function grade30(pts) { const W = 30; for (let i = 0; i < pts.length; i++) { let j = i; while (j < pts.length - 1 && pts[j].x - pts[i].x < W) j++; const dd = pts[j].x - pts[i].x; pts[i].grade = dd > 1 ? (pts[j].alt - pts[i].alt) / dd : (i > 0 ? pts[i - 1].grade : 0); } }

// Collect climb segments: contiguous 30 m-window grade ≥ 1% runs with total Δh ≥ 50 m; clip the
// first 10 m of vertical (entry inertia), then measure A/B/C/E over the remainder (≥ 40 m).
function collectClimbs(files) {
  const A = [], B = [], C = [], E = [], meta = [];
  const gentle = [];   // {dh, dx, dKE, aeroInt(=∫v³dt), Ewheel} for grade∈[1,3.5]%, v̄≥6 m/s
  let nRides = 0, nErr = 0;
  for (const f of files) {
    try {
      const pts = readPts(f); if (pts.length < 30) continue;
      grade30(pts);
      const rho = rhoAt(median(pts.map(p => p.alt).filter(Number.isFinite)));
      nRides++;
      let st = -1, runMax = -Infinity, runMaxI = -1;
      for (let i = 0; i <= pts.length; i++) {
        if (i < pts.length) {
          if (st < 0) { if (pts[i].grade > 0) { st = i; runMax = pts[i].alt; runMaxI = i; } continue; }
          if (pts[i].alt > runMax) { runMax = pts[i].alt; runMaxI = i; }
          if (runMax - pts[i].alt <= 8 && i < pts.length - 1) continue;   // 8 m drop budget: survive dips
        }
        if (st < 0) continue;
        const a0 = st, b = runMaxI; st = -1; runMax = -Infinity;          // end run at its altitude peak
        if (b <= a0 || pts[b].alt - pts[a0].alt < 50) continue;          // net Δh ≥ 50 m
        let a = a0; while (a < b && pts[a].alt - pts[a0].alt < 10) a++;  // clip first 10 m of climb
        const dh = pts[b].alt - pts[a].alt, dx = pts[b].x - pts[a].x;
        if (dh < 40 || dx < 100) continue;
        let E_wheel = 0, aeroInt = 0, time = 0, ok = true;
        for (let k = a + 1; k <= b; k++) {
          const dt = pts[k].dt || 0, v = pts[k].v;
          if (pts[k].power === undefined || v === undefined) { ok = false; break; }
          E_wheel += pts[k].power * dt; aeroInt += v * v * v * dt; time += dt;
        }
        if (!ok || !(time > 0) || E_wheel <= 0) continue;
        const va = pts[a].v, vb = pts[b].v; if (va === undefined || vb === undefined) continue;
        A.push(G * dh + 0.5 * (vb * vb - va * va));   // mass: gravity + ΔKE
        B.push(G * dx);                                // rolling: g·Δx
        C.push(0.5 * rho * aeroInt);                   // aero: ½ρ∫v³dt (per unit CdA)
        E.push(KEFF * E_wheel);                        // wheel work
        meta.push({ dh, dx, vmean: dx / time, grade: dh / dx });
        const gr = dh / dx, vbar = dx / time;
        if (gr >= 0.01 && gr <= 0.035 && vbar >= 6) gentle.push({ dh, dx, dKE: 0.5 * (vb * vb - va * va), aeroInt, Ewheel: KEFF * E_wheel, rho });
      }
    } catch (e) { nErr++; }
  }
  return { A, B, C, E, meta, gentle, nRides, nErr };
}

function listRiders() {
  const R = [];
  try { const man = JSON.parse(fs.readFileSync(path.join(DATA, 'strava_ppaz_manifest.json'), 'utf8'));
    R.push({ name: 'P. Paz', files: man.filter(a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20).map(a => a.file) }); } catch (e) { console.error('ppaz?', e.message); }
  try { const man = JSON.parse(fs.readFileSync(path.join(DATA, 'strava_jaam_manifest.json'), 'utf8'));
    R.push({ name: 'JAAM', files: man.filter(a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20).map(a => a.file) }); } catch (e) { console.error('jaam?', e.message); }
  try { const inp = JSON.parse(fs.readFileSync(path.join(DATA, 'model_inputs.json'), 'utf8')).filter(e => e.has_power && e.file);
    R.push({ name: 'author/longões', files: inp.map(e => e.file), aCdA: median(inp.map(e => e.cda)), aM: median(inp.map(e => e.m)), aCrr: median(inp.map(e => e.crr)) }); } catch (e) { console.error('longões?', e.message); }
  return R;
}

console.log('================================================================');
console.log('INDEPENDENT m / C_rr / CdA — 3-param climb energy-balance regression (no braking uphill)');
console.log(`k_eff=${KEFF}, ρ=ISA(altitude), wind=0. Segments: sustained uphill Δh≥50 m, first 10 m clipped, ≥40 m used.\n`);

const out = [];
for (const r of listRiders()) {
  const c = collectClimbs(r.files);
  const fit = ols3(c.A, c.B, c.C, c.E);
  const [m, crrM, cda] = fit.theta, crr = crrM / m;
  const bs = bootstrap3(c.A, c.B, c.C, c.E);
  // Gentle-fast CdA: fix (m, C_rr) from the mass-robust climb fit (CdA≈0.35), then CdA per
  // gentle-fast segment = residual aero work / (½ρ∫v³dt); median over segments. One refine pass.
  const mFix = ols2Fixed(c.A, c.B, c.C, c.E, 0.35), M = mFix.m, CRR = mFix.crr;
  const perSeg = c.gentle.map(s => (s.Ewheel - M * s.dKE - M * G * s.dh - CRR * M * G * s.dx) / (0.5 * s.rho * s.aeroInt)).filter(Number.isFinite);
  perSeg.sort((a, b) => a - b);
  const cdaG = median(perSeg);
  const cdaGiqr = perSeg.length > 4 ? [perSeg[Math.floor(0.25 * perSeg.length)], perSeg[Math.floor(0.75 * perSeg.length)]] : [NaN, NaN];
  const gr = c.meta.map(s => s.grade), vm = c.meta.map(s => s.vmean);
  console.log(`── ${r.name} ──  ${c.nRides} rides (${c.nErr} err), ${c.E.length} climb segments`);
  console.log(`  grade range p10–p90: ${(median(gr.filter(g => g < median(gr))) * 100).toFixed(1)}–${(median(gr.filter(g => g > median(gr))) * 100).toFixed(1)}%,  climb speed median ${(median(vm) * 3.6).toFixed(1)} km/h  (aero leverage)`);
  console.log(`  m   = ${m.toFixed(1)} kg     95% CI [${bs.mCI[0].toFixed(0)}, ${bs.mCI[1].toFixed(0)}]`);
  console.log(`  C_rr= ${crr.toFixed(4)}      95% CI [${bs.crrCI[0].toFixed(4)}, ${bs.crrCI[1].toFixed(4)}]`);
  console.log(`  CdA = ${cda.toFixed(3)} m²   95% CI [${bs.cdaCI[0].toFixed(3)}, ${bs.cdaCI[1].toFixed(3)}]   (R²=${fit.r2.toFixed(4)})`);
  const abCorr = corr(c.A, c.B);
  console.log(`  identifiability: corr(A_mass, B_roll) = ${abCorr.toFixed(3)}  (→1 ⇒ mass & C_rr collinear on climbs)`);
  console.log(`  gentle-fast CdA (grade 1–3.5%, v̄≥6 m/s, n=${perSeg.length} seg, m=${M.toFixed(0)} kg C_rr=${CRR.toFixed(4)} from CdA=0.35 fit): CdA ≈ ${Number.isFinite(cdaG)?cdaG.toFixed(3):'—'} m²  [IQR ${cdaGiqr[0]?.toFixed(2)}, ${cdaGiqr[1]?.toFixed(2)}]`);
  console.log(`  CdA→mass insensitivity (fix CdA, fit m,C_rr):  ` +
    [0.25, 0.35, 0.45].map(cd => { const f = ols2Fixed(c.A, c.B, c.C, c.E, cd); return `CdA=${cd}→m=${f.m.toFixed(0)}kg,C_rr=${f.crr.toFixed(3)}`; }).join('  '));
  if (r.aCdA !== undefined) {
    const fA = ols2Fixed(c.A, c.B, c.C, c.E, r.aCdA);
    console.log(`  [anchor] longões assumed: CdA ${r.aCdA.toFixed(2)}, m ${r.aM.toFixed(0)}, C_rr ${r.aCrr.toFixed(4)}   → with CdA fixed at truth: m=${fA.m.toFixed(0)} kg, C_rr=${fA.crr.toFixed(4)}`);
  }
  console.log('');
  out.push({ rider: r.name, nSeg: c.E.length, m, crr, cda, r2: fit.r2, mCI: bs.mCI, cdaCI: bs.cdaCI, crrCI: bs.crrCI });
}
fs.writeFileSync(path.join(RESULTS, 'cda_estimate.csv'),
  'rider,nSeg,mass_kg,crr,cda_m2,r2,m_lo,m_hi,cda_lo,cda_hi,crr_lo,crr_hi\n' +
  out.map(o => `${JSON.stringify(o.rider)},${o.nSeg},${o.m.toFixed(1)},${o.crr.toFixed(4)},${o.cda.toFixed(3)},${o.r2.toFixed(4)},${o.mCI[0].toFixed(1)},${o.mCI[1].toFixed(1)},${o.cdaCI[0].toFixed(3)},${o.cdaCI[1].toFixed(3)},${o.crrCI[0].toFixed(4)},${o.crrCI[1].toFixed(4)}`).join('\n') + '\n');
console.log('wrote cda_estimate.csv');
