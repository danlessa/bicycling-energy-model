#!/usr/bin/env node
// Per-activity CdA/C_rr/wind/mass estimation (journal Entry 15). parseFIT/haversine VERBATIM
// from ppaz_compare.mjs; the point builder (ptsWithGeo) is new because it must keep lat/lon for
// bearing (the verbatim ptsFromFIT drops it).  node param_fit.mjs
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
let FIT_MANUF; let physProfile = null;

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

// ===== Per-activity CdA / C_rr / wind / mass estimation (journal Entry 15, /goal) =====
// Adds WIND (the missing parameter) via GPS BEARING. A ride that heads in several directions
// under one wind vector shows a directional asymmetry in aero cost that identifies CdA AND the
// wind together — the principle behind Chung "virtual elevation" + aerometers (Notio/Aerolab).
//
// Full instantaneous power balance per sample i (bearing βᵢ from lat/lon, wind vector (We,Wn)):
//   Pᵢ·k_eff = [ m·aᵢ + m·g·sinθᵢ ]·vᵢ  +  C_rr·(m·g·cosθᵢ)·vᵢ  +  CdA·(½ρ(vᵢ+wᵢ)²)·vᵢ
//   wᵢ = −(We·sinβᵢ + Wn·cosβᵢ)   (along-track headwind; +headwind raises air speed vᵢ+wᵢ)
//
// Fit per activity: MASS fixed at the rider level (from braking-free climbs — mass is
// CdA-insensitive and near-constant per rider); then grid the 2-D wind vector and, at each
// wind, a 2-parameter NON-NEGATIVE linear least-squares gives (C_rr, CdA) by minimising the
// POWER residual (weights fast/aero-rich samples). Pick the wind with least SSE; refine.
// Report per-activity (CdA, C_rr, |W|, wind dir, straightness) and per-rider aggregates against
// the target ranges. k_eff = 0.98, ρ = ISA(altitude). Author longões = method anchor.

const KEFF = 0.98, G = 9.81, TO_R = Math.PI / 180;
const rhoAt = h => 1.225 * Math.pow(1 - 2.25577e-5 * Math.max(0, Math.min(h, 11000)), 5.25588);
const median = xs => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); const k = (s.length - 1) / 2; return s.length ? (s[Math.floor(k)] + s[Math.ceil(k)]) / 2 : NaN; };
const q = (xs, p) => { const s = xs.filter(Number.isFinite).slice().sort((a, b) => a - b); return s.length ? s[Math.max(0, Math.floor(p * (s.length - 1)))] : NaN; };

const slice = b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
function rawRecords(file) {
  let buf = fs.readFileSync(path.join(HERE, file));
  if (file.endsWith('.gz') && !file.endsWith('.gpx.gz')) buf = zlib.gunzipSync(buf);
  if (file.endsWith('.gpx')) return parseGPXrecords(buf.toString('utf8'));
  return parseFIT(slice(buf));   // verbatim; records carry lat/lon/alt/dist/speed/power/cad/time
}
// minimal GPX record reader (the one author longões GPX) — lat/lon/ele/time/power
function parseGPXrecords(text) {
  const out = []; const re = /<trkpt\b([^>]*)>([\s\S]*?)<\/trkpt>/g; let m;
  while ((m = re.exec(text))) {
    const la = m[1].match(/lat="([-\d.]+)"/), lo = m[1].match(/lon="([-\d.]+)"/); if (!la || !lo) continue;
    const ele = m[2].match(/<ele>\s*([-\d.]+)/), tm = m[2].match(/<time>\s*([^<]+)/), pw = m[2].match(/<(?:\w+:)?power>\s*([\d.]+)/);
    out.push({ lat: +la[1], lon: +lo[1], alt: ele ? +ele[1] : undefined, time: tm ? Date.parse(tm[1]) / 1000 : undefined, power: pw ? +pw[1] : undefined });
  }
  return out;
}

// Enriched points with bearing, distance, grade, acceleration. Requires GPS lat/lon.
function ptsWithGeo(recs) {
  const g = recs.filter(r => r.lat !== undefined && r.lon !== undefined && r.alt !== undefined && r.time !== undefined);
  if (g.length < 30) return null;
  const pts = []; let cum = 0;
  for (let i = 0; i < g.length; i++) {
    if (i > 0) cum += haversine(g[i - 1], g[i]);
    pts.push({ x: cum, alt: g[i].alt, v: g[i].speed, power: g[i].power, cad: g[i].cad, t: g[i].time, lat: g[i].lat, lon: g[i].lon });
  }
  // dt (clamp pauses ≤10 s), fallback speed from distance/time
  for (let i = 0; i < pts.length; i++) {
    const raw = i > 0 ? pts[i].t - pts[i - 1].t : undefined;
    pts[i].dt = raw !== undefined ? Math.min(Math.max(raw, 0), 10) : 1;
    if (pts[i].v === undefined && i > 0) { const dtv = raw > 0 ? raw : pts[i].dt; pts[i].v = dtv > 0 ? (pts[i].x - pts[i - 1].x) / dtv : 0; }
  }
  // bearing (deg from north), grade (30 m window), acceleration
  const W = 30;
  for (let i = 0; i < pts.length; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
    const dLon = (b.lon - a.lon) * TO_R, y = Math.sin(dLon) * Math.cos(b.lat * TO_R);
    const xb = Math.cos(a.lat * TO_R) * Math.sin(b.lat * TO_R) - Math.sin(a.lat * TO_R) * Math.cos(b.lat * TO_R) * Math.cos(dLon);
    pts[i].bear = Math.atan2(y, xb);   // radians
    let j = i; while (j < pts.length - 1 && pts[j].x - pts[i].x < W) j++;
    const dd = pts[j].x - pts[i].x; pts[i].grade = dd > 1 ? (pts[j].alt - pts[i].alt) / dd : (i > 0 ? pts[i - 1].grade : 0);
    pts[i].acc = (i > 0 && pts[i].v !== undefined && pts[i - 1].v !== undefined && pts[i].dt > 0) ? (pts[i].v - pts[i - 1].v) / pts[i].dt : 0;
  }
  return pts;
}

// 2-param NON-NEGATIVE linear LS (Crr, CdA) at a given wind, minimising power residual.
function fitCrrCdA(samples, m, rho, We, Wn) {
  let s11 = 0, s12 = 0, s22 = 0, y1 = 0, y2 = 0, syy = 0, my = 0, n = samples.length;
  const tgt = [], f1 = [], f2 = [];
  for (const s of samples) {
    const w = -(We * Math.sin(s.bear) + Wn * Math.cos(s.bear));
    const air = s.v + w;
    const T = s.pw * KEFF - (m * s.acc + m * G * s.sin) * s.v;   // power minus (KE+gravity)
    const a1 = m * G * s.cos * s.v;                              // Crr feature (rolling power)
    const a2 = 0.5 * rho * air * air * s.v;                     // CdA feature (aero power)
    tgt.push(T); f1.push(a1); f2.push(a2); my += T;
  }
  my /= n;
  for (let i = 0; i < n; i++) { s11 += f1[i] * f1[i]; s12 += f1[i] * f2[i]; s22 += f2[i] * f2[i]; y1 += f1[i] * tgt[i]; y2 += f2[i] * tgt[i]; syy += (tgt[i] - my) ** 2; }
  const det = s11 * s22 - s12 * s12;
  let crr = det ? (y1 * s22 - y2 * s12) / det : NaN, cda = det ? (s11 * y2 - s12 * y1) / det : NaN;
  // non-negativity: if one is negative, clamp it to 0 and refit the other alone
  if (crr < 0) { crr = 0; cda = y2 / s22; }
  if (cda < 0) { cda = 0; crr = y1 / s11; if (crr < 0) crr = 0; }
  let sse = 0; for (let i = 0; i < n; i++) { const e = tgt[i] - crr * f1[i] - cda * f2[i]; sse += e * e; }
  return { crr, cda, sse, r2: 1 - sse / syy };
}

// Per-activity fit: mass fixed; grid wind then refine; returns params + diagnostics.
function fitActivity(pts, m) {
  const rho = rhoAt(median(pts.map(p => p.alt)));
  const samples = [];
  for (const p of pts) {
    if (p.power === undefined || p.v === undefined || p.v < 3) continue;   // moving, has power
    if (p.power <= 0) continue;                                            // pedalling (avoid brake/coast)
    if (Math.abs(p.acc) > 1.5) continue;                                   // drop wild accelerations
    const sec = Math.sqrt(1 + p.grade * p.grade);
    samples.push({ v: p.v, pw: p.power, acc: p.acc, sin: p.grade / sec, cos: 1 / sec, bear: p.bear });
  }
  if (samples.length < 200) return null;
  // speed & direction spread (identifiability gates)
  const vs = samples.map(s => s.v), vSpread = q(vs, 0.9) - q(vs, 0.1);
  const dirs = samples.map(s => s.bear);
  const dirSpread = Math.sqrt((1 - (dirs.reduce((a, b) => a + Math.cos(b), 0) / dirs.length) ** 2 - (dirs.reduce((a, b) => a + Math.sin(b), 0) / dirs.length) ** 2)); // circular spread 0..1
  let best = null;
  for (let We = -8; We <= 8.001; We += 1) for (let Wn = -8; Wn <= 8.001; Wn += 1) {
    const f = fitCrrCdA(samples, m, rho, We, Wn);
    if (!best || f.sse < best.sse) best = { ...f, We, Wn };
  }
  // refine ±1 m/s at 0.25 resolution
  const b0 = best;
  for (let We = b0.We - 1; We <= b0.We + 1.001; We += 0.25) for (let Wn = b0.Wn - 1; Wn <= b0.Wn + 1.001; Wn += 0.25) {
    const f = fitCrrCdA(samples, m, rho, We, Wn);
    if (f.sse < best.sse) best = { ...f, We, Wn };
  }
  // straightness = net displacement / path length (→1 point-to-point, →0 circular/out-and-back)
  const first = pts[0], last = pts[pts.length - 1];
  const net = haversine(first, last), plen = last.x - first.x;
  return { cda: best.cda, crr: best.crr, W: Math.hypot(best.We, best.Wn), windDir: (Math.atan2(best.We, best.Wn) / TO_R + 360) % 360,
    r2: best.r2, n: samples.length, vSpread, dirSpread, straight: plen > 0 ? net / plen : 1, km: plen / 1000 };
}

// Rider mass from braking-free climbs (CdA-insensitive; fixed nominal CdA=0.35).
function riderMass(files) {
  const A = [], B = [], C = [], E = [];
  for (const f of files) {
    try {
      const recs = rawRecords(f); const pts = ptsWithGeo(recs); if (!pts) continue;
      const rho = rhoAt(median(pts.map(p => p.alt)));
      let st = -1, rMax = -Infinity, rMaxI = -1;
      for (let i = 0; i <= pts.length; i++) {
        if (i < pts.length) { if (st < 0) { if (pts[i].grade > 0) { st = i; rMax = pts[i].alt; rMaxI = i; } continue; } if (pts[i].alt > rMax) { rMax = pts[i].alt; rMaxI = i; } if (rMax - pts[i].alt <= 8 && i < pts.length - 1) continue; }
        if (st < 0) continue;
        const a0 = st, b = rMaxI; st = -1; rMax = -Infinity;
        if (b <= a0 || pts[b].alt - pts[a0].alt < 50) continue;
        let a = a0; while (a < b && pts[a].alt - pts[a0].alt < 10) a++;
        const dh = pts[b].alt - pts[a].alt, dx = pts[b].x - pts[a].x; if (dh < 40 || dx < 100) continue;
        let Ew = 0, aero = 0, ok = true; for (let k = a + 1; k <= b; k++) { const p = pts[k]; if (p.power === undefined || p.v === undefined) { ok = false; break; } Ew += p.power * p.dt; aero += p.v ** 3 * p.dt; }
        if (!ok || Ew <= 0) continue; const va = pts[a].v, vb = pts[b].v; if (va === undefined || vb === undefined) continue;
        A.push(G * dh + 0.5 * (vb * vb - va * va)); B.push(G * dx); C.push(0.5 * rho * aero); E.push(KEFF * Ew);
      }
    } catch (e) { /* skip */ }
  }
  // 2-param (m, Crr·m) with CdA fixed 0.35
  let s11 = 0, s12 = 0, s22 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < E.length; i++) { const Ep = E[i] - 0.35 * C[i]; s11 += A[i] * A[i]; s12 += A[i] * B[i]; s22 += B[i] * B[i]; y1 += A[i] * Ep; y2 += B[i] * Ep; }
  const det = s11 * s22 - s12 * s12; return { m: (y1 * s22 - y2 * s12) / det, nSeg: E.length };
}

function listRiders() {
  const R = [];
  const load = (mf, filt) => JSON.parse(fs.readFileSync(path.join(HERE, mf), 'utf8')).filter(filt);
  try { R.push({ name: 'P. Paz', range: { m: [72, 90], cda: [0.25, 0.45], crr: [0.004, 0.015] }, files: load('strava_ppaz_manifest.json', a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20).map(a => a.file) }); } catch (e) { console.error(e.message); }
  try { R.push({ name: 'JAAM', range: { m: [73, 95], cda: [0.25, 0.45], crr: [0.004, 0.015] }, files: load('strava_jaam_manifest.json', a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20).map(a => a.file) }); } catch (e) { console.error(e.message); }
  try { R.push({ name: 'author/longões', range: { m: [68, 80], cda: [0.28, 0.45], crr: [0.004, 0.015] }, files: load('model_inputs.json', e => e.has_power && e.file).map(e => e.file) }); } catch (e) { console.error(e.message); }
  return R;
}

console.log('================================================================');
console.log('PER-ACTIVITY CdA / C_rr / WIND / MASS  (wind via GPS bearing; mass rider-level from climbs)');
console.log('k_eff=0.98, ρ=ISA(altitude). Per activity: grid 2-D wind, non-neg linear (C_rr,CdA) at each.\n');

const rows = [];
for (const r of listRiders()) {
  const rm = riderMass(r.files); const m = rm.m;
  const acts = []; let nGeo = 0, nFit = 0, nGate = 0;
  for (const f of r.files) {
    try {
      const pts = ptsWithGeo(rawRecords(f)); if (!pts) continue; nGeo++;
      const fit = fitActivity(pts, m); if (!fit) continue; nFit++;
      if (fit.r2 > 0.4 && fit.n >= 200) { acts.push(fit); nGate++; }
    } catch (e) { /* skip */ }
  }
  console.log(`  [attrition] ${r.files.length} files → ${nGeo} with GPS → ${nFit} fittable → ${nGate} pass r²>0.4,n≥200`);
  // aggregate: use activities with decent direction spread (wind identifiable) for CdA
  const good = acts.filter(a => a.dirSpread > 0.3 && a.vSpread > 3.5);   // enough turning + speed range
  const cdas = good.map(a => a.cda), crrs = good.map(a => a.crr), winds = acts.map(a => a.W);
  const inR = (v, [lo, hi]) => v >= lo && v <= hi ? '✓' : '✗';
  console.log(`── ${r.name} ──  ${acts.length} activities fit (${good.length} with wind-identifiable geometry)`);
  console.log(`  MASS  = ${m.toFixed(1)} kg   [rider-level, ${rm.nSeg} climb seg]      target ${r.range.m[0]}–${r.range.m[1]}  ${inR(m, r.range.m)}`);
  console.log(`  CdA   = ${median(cdas).toFixed(3)} m²  [IQR ${q(cdas, .25).toFixed(2)}–${q(cdas, .75).toFixed(2)}]   target ${r.range.cda[0]}–${r.range.cda[1]}  ${inR(median(cdas), r.range.cda)}`);
  console.log(`  C_rr  = ${median(crrs).toFixed(4)}   [IQR ${q(crrs, .25).toFixed(4)}–${q(crrs, .75).toFixed(4)}]  target ${r.range.crr[0]}–${r.range.crr[1]}  ${inR(median(crrs), r.range.crr)}`);
  console.log(`  |wind|= ${median(winds).toFixed(1)} m/s (${(median(winds) * 3.6).toFixed(0)} km/h) median per activity; range ${(q(winds, .1) * 3.6).toFixed(0)}–${(q(winds, .9) * 3.6).toFixed(0)} km/h`);
  console.log(`  median activity: ${median(acts.map(a => a.km)).toFixed(0)} km, straightness ${median(acts.map(a => a.straight)).toFixed(2)}, fit R² ${median(acts.map(a => a.r2)).toFixed(2)}\n`);
  rows.push({ rider: r.name, m, cda: median(cdas), crr: median(crrs), wind: median(winds), nAct: acts.length, nGood: good.length });
}
fs.writeFileSync(path.join(HERE, 'param_fit.csv'), 'rider,mass_kg,cda_m2,crr,wind_ms,nAct,nGoodGeom\n' +
  rows.map(o => `${JSON.stringify(o.rider)},${o.m.toFixed(1)},${o.cda.toFixed(3)},${o.crr.toFixed(4)},${o.wind.toFixed(2)},${o.nAct},${o.nGood}`).join('\n') + '\n');
console.log('wrote param_fit.csv');
