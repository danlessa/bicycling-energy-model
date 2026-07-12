#!/usr/bin/env node
// Model comparison: for each ride with measured power, run the REAL approximate()
// and canonical() engines (ported verbatim from applet/index.html) on
// the ride's own parameters + its track, and put three energies side by side:
//   approx     — closed-form  approximate().E   (and per-edge clamped)
//   canonical  — forward sim   canonical().legE  (the model's ∫P·dt)
//   empirical  — measured      Σ power·dt from the track  (ground truth)
//
// Inputs: model_inputs.json (params per ride, from build_model_inputs.py) + the
// .fit/.gpx tracks. Output: model_comparison.csv + a console table.
//
// Wiring mirrors recompute() with the app defaults: engineDx=5 m, fitStat='mean'
// (time-weighted mean incl. zeros — the energy-consistent regime power),
// climbAeroMode='off', auto v_f = flatEqSpeed(P_flat), vmax=38, vstart=15 km/h.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '..', 'data', 'activities');
const RESULTS = path.join(HERE, '..', 'results');
fs.mkdirSync(RESULTS, { recursive: true });
const G = 9.81, NS = 240;
const VMAX = 38 / 3.6, VSTART = 15 / 3.6;       // app defaults (km/h -> m/s)
const CLIMB_THR = 0.02, DESC_THR = -0.015, ENGINE_DX = 5, CLIMB_AERO = 'off';
const TAU_SMOOTH = 2;   // elevation deadband threshold (m) — rejects sub-tau jitter in h+

let H = new Float64Array(NS), physProfile = null;   // globals buildProfile writes

// ===== engine functions, ported verbatim from applet/index.html =====
function haversine(a, b) {
  const R = 6371000, toR = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toR, dLon = (b.lon - a.lon) * toR;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}
function flatEqSpeed(P, p) {
  const a = p.Crr * p.m * G, b = 0.5 * p.rho * p.CdA, w = p.wind || 0;
  // SIGNED drag (a tailwind pushes: rel < 0), matching the engines' rel·|rel|.
  // wheel(v) is only guaranteed monotone for airspeed rel = v+w ≥ 0, so under a
  // tailwind bisect the monotone branch [−w, 40] first and fall back to [0, −w].
  const wheel = v => { const rel = v + w; return (a + b * rel * Math.abs(rel)) * v; };
  const target = p.keff * P;
  let lo = Math.max(0, -w), hi = 40;
  if (wheel(lo) > target) { hi = lo; lo = 0; }
  for (let k = 0; k < 60; k++) {
    const v = (lo + hi) / 2;
    if (wheel(v) < target) lo = v; else hi = v;
  }
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
  let KE = KEinit;
  let legE = 0, t = 0, Wrr = 0, Waero = 0, Wgrav = 0, Wbrake = 0;
  const legER = [0, 0, 0];   // per-regime legE bookkeeping [descent, flat, climb] (does not affect dynamics)
  const speed = new Float64Array(n), brk = new Uint8Array(n), regime = new Int8Array(n);
  speed[0] = Math.sqrt(2 * KE / m);
  let minV = speed[0];
  const keCap = 0.5 * m * vmax * vmax;
  let stalled = false;   // P=0 with resistance > KE: the bike halts (no KE floor — it would inject energy)
  for (let i = 1; i < n; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1];
    const slope = dh / dx, sec = Math.sqrt(1 + slope * slope);
    const cos = 1 / sec, sin = slope / sec;
    const Frr = Crr * m * G * cos, Fgrav = m * G * sin;
    let reg, P;
    if (slope >= pw.climbThr) { reg = 1; P = pw.climb; }
    else if (slope <= pw.descThr) { reg = -1; P = pw.descent; }
    else { reg = 0; P = pw.flat; }
    regime[i] = reg;
    let remaining = dx * sec, braked = 0;
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
      legE += Pleg * dt; legER[reg + 1] += Pleg * dt; t += dt;
      Wrr += Frr * dsSub; Waero += Faero * dsSub; Wgrav += Fgrav * dsSub;
      KE = KEn;
      if (KE > keCap) { Wbrake += KE - keCap; KE = keCap; braked = 1; }
      remaining -= dsSub;
    }
    const v = Math.sqrt(2 * KE / m);
    speed[i] = v; brk[i] = braked; if (v < minV) minV = v;
    if (stalled) break;   // cannot proceed at zero power — return the partial, conservative leg
  }
  const dist = xs[n - 1] - xs[0];
  const dKE = KE - KEinit;
  const dispE = dKE + Wrr + Waero + Wbrake;
  return { legE, t, Wrr, Waero, Wgrav, Wbrake, speed, brk, regime, stalled,
           legEByReg: { descent: legER[0], flat: legER[1], climb: legER[2] },
           avgV: dist / t, minV, KEinit, KEfin: KE, dKE, dispE };
}
function approximate(prof, p, vf, eps, opts) {
  const beta = p.m * G / p.keff, mg = p.m * G, w = p.wind;
  const aeroSpd = vf + w;
  const aRoll = mg * p.Crr / p.keff;
  const aAero = 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd) / p.keff;
  const mode = (opts && opts.climbAeroMode) || 'off';
  const climbThr = opts && opts.climbThr != null ? opts.climbThr : 0.02;
  const Pc = (opts && opts.climbPower) || 0;
  const dThr = opts && opts.descThr != null ? opts.descThr : -0.015;   // for the regime split
  const xs = prof.x, hs = prof.h;
  let X = 0, hplus = 0, hminus = 0, aeroSum = 0, clamped = 0;
  const EByReg = [0, 0, 0];   // [descent, flat, climb] split of E (sums to E; same thresholds as canonical)
  for (let i = 1; i < xs.length; i++) {
    const dx = xs[i] - xs[i - 1], dh = hs[i] - hs[i - 1], slope = dh / dx;
    X += dx;
    let aeroDx = aAero;
    if (mode !== 'off' && slope >= climbThr) {
      if (mode === 'zero') aeroDx = 0;
      else {
        const sec = Math.sqrt(1 + slope * slope), sin = slope / sec, cos = 1 / sec;
        const vc = Pc > 0 ? Math.min(vf, p.keff * Pc / (p.Crr * mg * cos + mg * sin)) : 0;
        aeroDx = 0.5 * p.rho * p.CdA * (vc + w) * Math.abs(vc + w) / p.keff;
      }
    }
    const segAero = aeroDx * dx; aeroSum += segAero;
    const alphaSeg = aRoll * dx + segAero;
    const segGrav = dh >= 0 ? beta * dh : -eps * beta * (-dh);  // climb lift / descent recovery
    if (dh >= 0) { hplus += dh; clamped += alphaSeg + beta * dh; }
    else { hminus += -dh; clamped += Math.max(0, alphaSeg - eps * beta * (-dh)); }
    const rg = slope >= climbThr ? 2 : slope <= dThr ? 0 : 1;   // by the same regime thresholds
    EByReg[rg] += alphaSeg + segGrav;
  }
  const roll = aRoll * X, aero = aeroSum, climb = beta * hplus, recov = -eps * beta * hminus;
  return { E: roll + aero + climb + recov, clamped, alpha: aRoll + aAero, beta, X, hplus, hminus, roll, aero, climb, recov,
           EByReg: { descent: EByReg[0], flat: EByReg[1], climb: EByReg[2] } };
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
  for (let i = first + 1; i < n; i++) {
    if (Number.isFinite(E[i])) {
      for (let k = last + 1; k < i; k++) E[k] = E[last] + (E[i] - E[last]) * (k - last) / (i - last);
      last = i;
    }
  }
  for (let i = last + 1; i < n; i++) E[i] = E[last];
  let minE = Infinity, maxE = -Infinity;
  for (const e of E) { if (e < minE) minE = e; if (e > maxE) maxE = e; }
  const px = new Float64Array(n), ph = new Float64Array(n);
  for (let i = 0; i < n; i++) { px[i] = X[i]; ph[i] = E[i] - minE; }
  physProfile = { x: px, h: ph };
  let j = 0;
  for (let s = 0; s < NS; s++) {
    const d = total * s / (NS - 1);
    while (j < n - 2 && X[j + 1] < d) j++;
    const seg = X[j + 1] - X[j], f = seg > 1e-9 ? (d - X[j]) / seg : 0;
    H[s] = ph[j] * (1 - f) + ph[j + 1] * f;
  }
  const sm = H.slice();
  for (let s = 1; s < NS - 1; s++) H[s] = (sm[s - 1] + 2 * sm[s] + sm[s + 1]) / 4;
  return { total, range: maxE - minE, n };
}
function extractRegimePowers(pts, climbThr, descThr) {
  const W = 30;
  const bins = [[], [], []];
  const VSTOP = 0.5 / 3.6;
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
  const stat = b => {
    if (!b.length) return { mean: null, meanNZ: null, median: null, time: 0, n: 0 };
    let sw = 0, swp = 0, swNZ = 0, swpNZ = 0;
    for (const s of b) { sw += s.w; swp += s.w * s.p; if (s.p > 0) { swNZ += s.w; swpNZ += s.w * s.p; } }
    b.sort((a, c) => a.p - c.p);
    let acc = 0, median = b[b.length - 1].p;
    for (const s of b) { acc += s.w; if (acc >= sw / 2) { median = s.p; break; } }
    return { mean: sw ? swp / sw : null, meanNZ: swNZ ? swpNZ / swNZ : null, median, time: sw, n: b.length };
  };
  return { descent: stat(bins[0]), flat: stat(bins[1]), climb: stat(bins[2]) };
}
// parseFIT — ported verbatim (record msg 20; endianness, compressed-ts, dev fields)
function parseFIT(buffer) {
  const dv = new DataView(buffer);
  if (buffer.byteLength < 14) throw new Error('FIT muito curto');
  const headerSize = dv.getUint8(0), dataSize = dv.getUint32(4, true);
  if (String.fromCharCode(dv.getUint8(8), dv.getUint8(9), dv.getUint8(10), dv.getUint8(11)) !== '.FIT')
    throw new Error('assinatura .FIT ausente');
  const end = Math.min(headerSize + dataSize, buffer.byteLength);
  let pos = headerSize;
  const defs = {}, records = [];
  let lastTs;   // running timestamp for compressed-timestamp headers (5-bit offset, 32 s rollover)
  const read = (p, bt, little) => {
    switch (bt & 0x1F) {
      case 0x01: { const v = dv.getInt8(p); return v === 0x7F ? undefined : v; }
      case 0x00: case 0x02: case 0x0A: case 0x0D: { const v = dv.getUint8(p); return v === 0xFF ? undefined : v; }
      case 0x03: { const v = dv.getInt16(p, little); return v === 0x7FFF ? undefined : v; }
      case 0x04: case 0x0B: { const v = dv.getUint16(p, little); return v === 0xFFFF ? undefined : v; }
      case 0x05: { const v = dv.getInt32(p, little); return v === 0x7FFFFFFF ? undefined : v; }
      case 0x06: case 0x0C: { const v = dv.getUint32(p, little) >>> 0; return v === 0xFFFFFFFF ? undefined : v; }
      case 0x08: return dv.getFloat32(p, little);
      case 0x09: return dv.getFloat64(p, little);
      default: return undefined;
    }
  };
  while (pos < end) {
    const rh = dv.getUint8(pos); pos++;
    let local, isDef = false, hasDev = false, tsOffset;
    if (rh & 0x80) { local = (rh >> 5) & 0x03; tsOffset = rh & 0x1F; }
    else { local = rh & 0x0F; isDef = !!(rh & 0x40); hasDev = !!(rh & 0x20); }
    if (isDef) {
      pos++;
      const little = dv.getUint8(pos) === 0; pos++;
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
        if (def.gmn === 20) {
          const v = read(p, f.bt, def.little);
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
          }
        } else if (f.num === 253) {   // any message's timestamp advances the running clock
          const v = read(p, f.bt, def.little);
          if (v !== undefined) rec.time = v;
        }
        p += f.size;
      }
      pos = p + def.devSize;
      // compressed-timestamp header: reconstruct the time from the 5-bit offset
      // (verify.py does the same; without this, dt defaults to 1 s downstream)
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

// ===== track -> pts (mirrors loadFIT); plus a minimal gpx-with-power reader =====
function ptsFromFIT(buffer) {
  const recs = parseFIT(buffer);
  if (recs.length < 2) throw new Error('FIT sem registros');
  const pts = [];
  if (recs.some(r => r.dist !== undefined)) {
    // Some devices log distance and altitude in SEPARATE record messages (never
    // the same one). Requiring both per-record drops everything; forward-filling
    // x as constant collapses the altitude detail in buildProfile (flattens
    // climbs). So interpolate distance by record index between dist anchors —
    // x rises smoothly and every altitude sample is kept. For normal files
    // (dist on every record) this reproduces the raw distance exactly.
    const di = [], dv = [];
    recs.forEach((r, i) => { if (r.dist !== undefined) { di.push(i); dv.push(dv.length ? Math.max(r.dist, dv[dv.length - 1]) : r.dist); } });   // clip non-monotone device distance
    let lastAlt, k = 0;
    for (let i = 0; i < recs.length; i++) {
      if (recs[i].alt !== undefined) lastAlt = recs[i].alt;
      if (lastAlt === undefined) continue;
      while (k < di.length - 1 && di[k + 1] <= i) k++;
      let x;
      if (i <= di[0]) x = dv[0];
      else if (i >= di[di.length - 1]) x = dv[dv.length - 1];
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
function finishPts(pts) {   // dt weight (clamp pauses) + speed fallback — as loadFIT
  for (let i = 0; i < pts.length; i++) {
    const raw = (i > 0 && pts[i].t !== undefined && pts[i - 1].t !== undefined) ? pts[i].t - pts[i - 1].t : undefined;
    const w = raw !== undefined ? Math.min(Math.max(raw, 0), 10) : 1;
    pts[i].dt = w;
    if (pts[i].v === undefined && i > 0) {
      const dtv = raw !== undefined && raw > 0 ? raw : w;   // speed from the UNCLAMPED interval (clamped Δt overstates v across pauses)
      if (dtv > 0) pts[i].v = (pts[i].x - pts[i - 1].x) / dtv;
    }
  }
}

// ===== driver =====
function empiricalKJ(pts) {     // measured pedalling energy Σ power·dt (J -> kJ)
  let e = 0;
  for (const q of pts) if (q.power !== undefined) e += q.power * (q.dt || 0);
  return e / 1000;
}
function overallMeanPower(pts) {
  let sw = 0, swp = 0;
  for (const q of pts) if (q.power !== undefined) { sw += (q.dt || 1); swp += (q.dt || 1) * q.power; }
  return sw ? swp / sw : 0;
}
// Measured pedalling energy Σ power·dt split by regime (J), binned by the sample's
// grade over a 30 m window — same thresholds as canonical/extractRegimePowers. Sums
// to the total empirical, so it is comparable to the models' EByReg / legEByReg.
function empiricalByRegime(pts, climbThr, descThr) {
  const W = 30, byReg = { climb: 0, flat: 0, descent: 0 };
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].power === undefined) continue;
    let j = i; while (j < pts.length - 1 && pts[j].x - pts[i].x < W) j++;
    const dd = pts[j].x - pts[i].x;
    let grade;
    if (dd > 1) grade = (pts[j].alt - pts[i].alt) / dd;
    else { let k = i; while (k > 0 && pts[i].x - pts[k].x < W) k--; const db = pts[i].x - pts[k].x; grade = db > 1 ? (pts[i].alt - pts[k].alt) / db : 0; }
    const e = pts[i].power * (pts[i].dt || 0);
    if (grade >= climbThr) byReg.climb += e; else if (grade <= descThr) byReg.descent += e; else byReg.flat += e;
  }
  return byReg;
}
// fraction of horizontal distance ridden on climbs (slope >= thr) — the f_climb
// behind notas.md's climb-fraction aero correction (f_flat = 1 - this).
function climbFraction(prof, thr) {
  const xs = prof.x, hs = prof.h; let X = 0, Xc = 0;
  for (let i = 1; i < xs.length; i++) { const dx = xs[i] - xs[i - 1]; X += dx; if ((hs[i] - hs[i - 1]) / dx >= thr) Xc += dx; }
  return X > 0 ? Xc / X : 0;
}
// Sustained-climb energy balance (Danilo's method for fitting k_h cleanly).
// Find sections climbing >= CLIMB_PCT over >= MINLEN m (no momentum recovery, aero
// small), and on each compare the MEASURED Σ P·dt to the EXPECTED gravity + rolling
// + aero. On a real sustained climb the rider must pay ~mg·Δh/k_eff, so
//   k_h(sustained) = (measured − rolling − aero) / (mg·Δh/k_eff)
// should be ~1 — isolating the climb physics from the roller/noise effect that drags
// the whole-ride h₊ down. Returns kJ sums + Δh accounting.
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
// Cumulative ascent of an elevation array with a hysteresis threshold tau (m):
// tau=0 sums every positive step (max noise); tau>0 commits a gain only after a
// net rise of tau, rejecting sub-tau jitter. The raw->tau shrink quantifies noise.
function ascentHyst(h, tau) {
  let gain = 0;
  if (tau <= 0) { for (let i = 1; i < h.length; i++) { const d = h[i] - h[i - 1]; if (d > 0) gain += d; } return gain; }
  let ref = h[0];
  for (let i = 1; i < h.length; i++) { const d = h[i] - ref; if (d >= tau) { gain += d; ref = h[i]; } else if (d <= -tau) { ref = h[i]; } }
  return gain;
}
// Deadband (backlash) filter: returns a smoothed elevation array that ignores
// moves smaller than tau and tracks larger ones (lagging by tau). Removes sub-tau
// jitter from h+/h- while preserving real climbs — a usable de-noised PROFILE.
function deadband(h, tau) {
  const out = new Float64Array(h.length);
  let y = h[0]; out[0] = y;
  for (let i = 1; i < h.length; i++) {
    if (h[i] > y + tau) y = h[i] - tau;
    else if (h[i] < y - tau) y = h[i] + tau;
    out[i] = y;
  }
  return out;
}
// MEASURED flat ground speed (m/s): time-weighted mean MOVING speed on near-flat
// 30 m cells (|grade| < 1%) — the v_f definition from epsFromFIT in the app.
// Stopped samples (v < 0.5 km/h) are gated out, same as extractRegimePowers:
// including them deflates v_f (hence α and ε) on stop-go rides.
function measuredFlatSpeed(pts) {
  const DX = 30, x0 = pts[0].x, total = pts[pts.length - 1].x - x0, nc = Math.floor(total / DX);
  const VSTOP = 0.5 / 3.6;
  if (nc < 2) return null;
  let j = 0; const altAt = d => { while (j < pts.length - 2 && pts[j + 1].x < d) j++; const seg = pts[j + 1].x - pts[j].x, f = seg > 1e-9 ? (d - pts[j].x) / seg : 0; return pts[j].alt * (1 - f) + pts[j + 1].alt * f; };
  const cellAlt = new Float64Array(nc + 1); for (let k = 0; k <= nc; k++) cellAlt[k] = altAt(x0 + k * DX);
  const sv = new Float64Array(nc), sw = new Float64Array(nc);
  for (const r of pts) { const k = Math.floor((r.x - x0) / DX); if (k < 0 || k >= nc) continue; const w = r.dt || 1; if (r.v !== undefined && r.v >= VSTOP) { sv[k] += r.v * w; sw[k] += w; } }
  let SV = 0, SW = 0;
  for (let k = 0; k < nc; k++) { const gr = (cellAlt[k + 1] - cellAlt[k]) / DX; if (Math.abs(gr) < 0.01 && sw[k] > 0) { SV += sv[k]; SW += sw[k]; } }
  return SW > 0 ? SV / SW : null;
}
// Descent-energy-balance ε (ported from the app's epsFromFIT): 30 m cells,
//   ε = (α·X₋ − E_legs,₋) / (β·H₋),  α using the MEASURED flat speed.
// Local to descents — not polluted by climb/aero errors, so far more stable per ride.
function epsFromBalance(pts, p) {
  if (!pts || pts.length < 2) return NaN;
  const mg = p.m * G, beta = mg / p.keff, VSTOP = 0.5 / 3.6;
  const x0 = pts[0].x, totalM = pts[pts.length - 1].x - x0, DX = 30, nc = Math.floor(totalM / DX);
  if (nc < 2) return NaN;
  let j = 0;
  const altAt = d => { while (j < pts.length - 2 && pts[j + 1].x < d) j++; const seg = pts[j + 1].x - pts[j].x, f = seg > 1e-9 ? (d - pts[j].x) / seg : 0; return pts[j].alt * (1 - f) + pts[j + 1].alt * f; };
  const cellAlt = new Float64Array(nc + 1);
  for (let k = 0; k <= nc; k++) cellAlt[k] = altAt(x0 + k * DX);
  const cellE = new Float64Array(nc), cellVs = new Float64Array(nc), cellVt = new Float64Array(nc);
  for (const r of pts) {
    const k = Math.floor((r.x - x0) / DX); if (k < 0 || k >= nc) continue;
    const w = r.dt || 1;
    if (r.power !== undefined) cellE[k] += r.power * w;
    if (r.v !== undefined && r.v >= VSTOP) { cellVs[k] += r.v * w; cellVt[k] += w; }   // moving samples only
  }
  let sv = 0, sw = 0;   // v_f = time-weighted mean MOVING ground speed on flat cells (|grade| < 1%)
  for (let k = 0; k < nc; k++) { const gr = (cellAlt[k + 1] - cellAlt[k]) / DX; if (Math.abs(gr) < 0.01 && cellVt[k] > 0) { sv += cellVs[k]; sw += cellVt[k]; } }
  const vf = sw > 0 ? sv / sw : 5, aeroSpd = vf + p.wind;
  const alpha = (p.Crr * mg + 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd)) / p.keff;
  let Xd = 0, Hd = 0, Ed = 0;
  for (let k = 0; k < nc; k++) { const dh = cellAlt[k + 1] - cellAlt[k]; if (dh < 0) { Xd += DX; Hd -= dh; Ed += cellE[k]; } }
  return Hd < 1 ? NaN : (alpha * Xd - Ed) / (beta * Hd);
}

const inputs = JSON.parse(fs.readFileSync(path.join(DATA, 'model_inputs.json'), 'utf8'));
const rows = [];
// energy-weighted per-regime totals across rides (kJ), for the climb/flat/descent breakdown
const mkReg = () => ({ emp: 0, canon: 0, off: 0, cf: 0, canonS: 0, offS: 0, cfS: 0 });  // *S = elevation-smoothed
const REG = { climb: mkReg(), flat: mkReg(), descent: mkReg() };
// elevation-noise accounting: Σ ascent (m) at smoothing levels + Σ climb-gravity energy (kJ)
const TAUS = [0, 1, 2, 3, 5, 10];
const ELEV = { h: Object.fromEntries(TAUS.map(t => [t, 0])), eng: 0, engS: 0, gravRaw: 0, grav3: 0,
               bySrc: { rwgps_trip: { raw: 0, h3: 0 }, strava: { raw: 0, h3: 0 } } };
const KH = [];   // per-ride {xkm, hpRaw, hpSm, c=spurious/km, kh, hilly=hpRaw/km} for the heuristic study
const CONS = { max: 0, ride: null };   // worst per-ride conservation residual (must stay ≤ 1e-6)
const SC = { emeas: 0, egrav: 0, eroll: 0, eaero: 0, dh: 0, L: 0, n: 0, totalAsc: 0, perRide: [] };  // sustained-climb energy balance
for (const e of inputs) {
  if (!e.file || !e.has_power) continue;
  try {
    const fp = path.join(DATA, e.file);
    // NB: slice, not .buffer — Node pools small reads, so .buffer may be the shared pool
    const pts = e.file.endsWith('.gpx')
      ? ptsFromGPX(fs.readFileSync(fp, 'utf8'))
      : ptsFromFIT((b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength))(fs.readFileSync(fp)));
    buildProfile(pts.map(q => q.x), pts.map(q => q.alt));   // sets physProfile
    const prof = resampleProfile(physProfile, ENGINE_DX);
    const rp = extractRegimePowers(pts, CLIMB_THR, DESC_THR);
    const stat = s => (rp[s].mean != null ? rp[s].mean : 0);
    const flat = rp.flat.mean != null ? rp.flat.mean : overallMeanPower(pts);
    const pw = { climb: stat('climb'), flat, descent: stat('descent'), climbThr: CLIMB_THR, descThr: DESC_THR };
    const p = { m: e.m, Crr: e.crr, CdA: e.cda, rho: e.rho, keff: e.keff,
                vmax: VMAX, vstart: VSTART, wind: (e.wind_kmh || 0) / 3.6 };
    // v_f from the EXTRACTED flat power (grade-binned mean) — the harness default
    const vf = flatEqSpeed(pw.flat, p);
    // v_f from the SHEET's P_flat/P_avg term: P_flat = ratio · <W>_mes, both from the
    // sheet (<W>_mes = the rider's avg power = Work/Moving Time). Lets the rider's
    // flat-power model set v_f instead of the direct grade-binned extraction.
    const pAvg = overallMeanPower(pts);                  // data avg (over recorded time), for reference
    const pFlatSheet = (e.pflat_pavg != null && e.wmes != null) ? e.pflat_pavg * e.wmes : pw.flat;
    const vfSheet = flatEqSpeed(pFlatSheet, p);
    const opt = mode => ({ climbAeroMode: mode, climbThr: CLIMB_THR, descThr: DESC_THR, climbPower: pw.climb });
    const aOff = approximate(prof, p, vf, e.eps, opt('off'));   // current: full v_f aero everywhere
    const aCf  = approximate(prof, p, vf, e.eps, opt('zero'));  // climb-fraction: aero only on f_flat (notas eq.)
    const aVc  = approximate(prof, p, vf, e.eps, opt('vc'));    // near-exact: climb aero at v_c
    const aCfSheet = approximate(prof, p, vfSheet, e.eps, opt('zero')); // cf + sheet v_f
    const vfMeas = measuredFlatSpeed(pts) || vf;                        // measured flat ground speed
    const aCfMeas = approximate(prof, p, vfMeas, e.eps, opt('zero'));   // cf + measured v_f
    const c = canonical(prof, pw, p);
    // machine-check the conservation identity k_eff·legE = ΔKE + W_rr + W_aero + W_grav + W_brake per ride
    const consResid = Math.abs(p.keff * c.legE - (c.dKE + c.Wrr + c.Waero + c.Wgrav + c.Wbrake)) / Math.max(1, p.keff * c.legE);
    if (consResid > 1e-6) console.error(`CONSERVATION VIOLATION ${e.label}: rel resid ${consResid.toExponential(2)}`);
    if (consResid > CONS.max) { CONS.max = consResid; CONS.ride = e.label; }
    // same engines on the elevation-deadband-SMOOTHED profile (same pw, vf, params)
    const profS = { x: prof.x, h: deadband(prof.h, TAU_SMOOTH) };
    const aOffS = approximate(profS, p, vf, e.eps, opt('off'));
    const aCfS = approximate(profS, p, vf, e.eps, opt('zero'));         // SMOOTHENED: cf + real deadband
    const cS = canonical(profS, pw, p);
    // k_smooth: poor-man's deadband — scale the RAW-profile gravity term by the scalar
    // k_smooth = 1 - c·x/h+ (c=3 m/km), instead of actually running the deadband (notas v2).
    const km = aCf.hplus > 0 ? Math.max(0, 1 - 3 * (prof.x[prof.x.length - 1] / 1000) / aCf.hplus) : 1;
    const eKsmooth = aCf.roll + aCf.aero + km * (aCf.climb + aCf.recov);   // J
    const emp = empiricalKJ(pts);                               // kJ
    // fit ε per ride against the SMOOTHENED model (k_h=1, deadband h±): solve
    //   E = roll + aero + β·h₊ − ε·β·h₋ = empirical  ⇒  ε* = (roll+aero+β·h₊ − emp)/(β·h₋)
    const betaR = e.m * G / e.keff, bHm = betaR * aCfS.hminus;
    const epsFit = bHm > 1e-6 ? (aCfS.roll + aCfS.aero + aCfS.climb - emp * 1000) / bHm : NaN;
    const epsBal = epsFromBalance(pts, p);   // descent-energy-balance ε (stable, local to descents)
    const empReg = empiricalByRegime(pts, CLIMB_THR, DESC_THR);
    for (const rg of ['climb', 'flat', 'descent']) {
      REG[rg].emp += empReg[rg] / 1000;
      REG[rg].canon += c.legEByReg[rg] / 1000;
      REG[rg].off += aOff.EByReg[rg] / 1000;
      REG[rg].cf += aCf.EByReg[rg] / 1000;
      REG[rg].canonS += cS.legEByReg[rg] / 1000;
      REG[rg].offS += aOffS.EByReg[rg] / 1000;
      REG[rg].cfS += aCfS.EByReg[rg] / 1000;
    }
    // elevation-noise: ascent on the NATIVE profile at each hysteresis threshold
    const beta = e.m * G / e.keff, hN = physProfile.h;
    for (const t of TAUS) ELEV.h[t] += ascentHyst(hN, t);
    ELEV.eng += aOff.hplus;                                  // what the engine actually used (5 m grid raw)
    ELEV.engS += aOffS.hplus;                                // h+ after the deadband filter
    const hRaw = ascentHyst(hN, 0), h3 = ascentHyst(hN, 3);
    ELEV.gravRaw += beta * hRaw / 1000; ELEV.grav3 += beta * h3 / 1000;
    const hpSm = ascentHyst(deadband(hN, TAU_SMOOTH), 0), xkm = prof.x[prof.x.length - 1] / 1000;
    KH.push({ ride: e.label, xkm, hpRaw: hRaw, hpSm, c: (hRaw - hpSm) / xkm, kh: hpSm / hRaw, hilly: hRaw / xkm });
    // sustained-climb energy balance (Danilo's k_h fit)
    const cb = climbBalance(pts, p);
    for (const k of ['emeas', 'egrav', 'eroll', 'eaero', 'dh', 'L', 'n', 'totalAsc']) SC[k] += cb[k];
    if (cb.egrav > 0) SC.perRide.push({ ride: e.label, kh: (cb.emeas - cb.eroll - cb.eaero) / cb.egrav, frac: cb.dh / cb.totalAsc });
    const sk = e.source === 'strava' ? 'strava' : 'rwgps_trip';
    if (ELEV.bySrc[sk]) { ELEV.bySrc[sk].raw += hRaw; ELEV.bySrc[sk].h3 += h3; }
    const kj = j => j / 1000, dlt = j => (kj(j) - emp) / emp * 100;
    rows.push({
      ride: e.label, source: e.source,
      dist_km: prof.x[prof.x.length - 1] / 1000,
      climb_frac: climbFraction(prof, CLIMB_THR),
      empirical: emp, canonical: kj(c.legE),
      approx_off: kj(aOff.E), approx_cf: kj(aCf.E), approx_vc: kj(aVc.E), approx_cf_sheet: kj(aCfSheet.E),
      canon_vs_emp: dlt(c.legE), off_vs_emp: dlt(aOff.E), cf_vs_emp: dlt(aCf.E), vc_vs_emp: dlt(aVc.E),
      cfsheet_vs_emp: dlt(aCfSheet.E), cfmeas_vs_emp: dlt(aCfMeas.E),
      canonS_vs_emp: dlt(cS.legE), offS_vs_emp: dlt(aOffS.E), cfS_vs_emp: dlt(aCfS.E),
      ksmooth_vs_emp: dlt(eKsmooth), eps_sheet: e.eps, eps_fit: epsFit, eps_bal: epsBal,
      p_avg: pAvg, wmes: e.wmes, pflat_extracted: pw.flat, pflat_sheet: pFlatSheet,
      data_ratio: e.wmes ? pw.flat / e.wmes : null, sheet_ratio: e.pflat_pavg,  // both flat/<W>_mes
      vf_kmh: vf * 3.6, vf_sheet_kmh: vfSheet * 3.6, vf_meas_kmh: vfMeas * 3.6,
      pClimb: pw.climb, pFlat: pw.flat, pDescent: pw.descent,
    });
  } catch (err) {
    rows.push({ ride: e.label, source: e.source, error: String(err.message || err) });
  }
}

// console table — Δ% vs empirical for canonical and the three approx variants
const f = (x, d = 0) => x == null || Number.isNaN(x) ? '—' : x.toFixed(d);
console.log('Δ% vs empirical ∫P·dt   (off = current; cf = climb-fraction aero; vc = climb aero at v_c)');
console.log(`${'RIDE'.padEnd(22)}${'dist'.padStart(5)}${'cl%'.padStart(5)}${'emp'.padStart(7)}  ${'canon'.padStart(6)}${'off'.padStart(6)}${'cf'.padStart(6)}${'vc'.padStart(6)}`);
console.log('-'.repeat(64));
for (const r of rows) {
  if (r.error) { console.log(`${r.ride.slice(0,22).padEnd(22)}  ERROR: ${r.error}`); continue; }
  console.log(
    r.ride.slice(0,22).padEnd(22) + f(r.dist_km,0).padStart(5) + f(r.climb_frac*100,0).padStart(5) +
    f(r.empirical,0).padStart(7) + '  ' + f(r.canon_vs_emp,1).padStart(6) +
    f(r.off_vs_emp,1).padStart(6) + f(r.cf_vs_emp,1).padStart(6) + f(r.vc_vs_emp,1).padStart(6));
}
// summary
const good = rows.filter(r => !r.error);
const med = (xs) => { const s = xs.slice().sort((a,b)=>a-b); const k=(s.length-1)/2; return s.length? (s[Math.floor(k)]+s[Math.ceil(k)])/2 : NaN; };
const stats = (key) => {
  const v = good.map(r => Math.abs(r[key])).filter(x => Number.isFinite(x));
  const signed = good.map(r => r[key]).filter(x => Number.isFinite(x));
  return { n: v.length, medAbs: med(v), medSigned: med(signed), mean: signed.reduce((a,b)=>a+b,0)/signed.length };
};
console.log('='.repeat(64));
console.log(`${'model vs empirical'.padEnd(30)}${'n'.padStart(4)}${'med|Δ%|'.padStart(9)}${'medΔ%'.padStart(8)}${'meanΔ%'.padStart(8)}`);
for (const [lab, key] of [['canonical (forward sim)','canon_vs_emp'],['approx off (current)','off_vs_emp'],['approx climb-fraction (cf)','cf_vs_emp'],['approx near-exact v_c','vc_vs_emp'],['approx cf + sheet v_f','cfsheet_vs_emp'],['approx cf + measured v_f','cfmeas_vs_emp'],
  [`canonical + ${TAU_SMOOTH} m smooth`,'canonS_vs_emp'],[`approx off + ${TAU_SMOOTH} m smooth`,'offS_vs_emp'],[`approx cf + ${TAU_SMOOTH} m smooth`,'cfS_vs_emp']]) {
  const s = stats(key);
  console.log(`${lab.padEnd(30)}${String(s.n).padStart(4)}${f(s.medAbs,1).padStart(9)}${f(s.medSigned,1).padStart(8)}${f(s.mean,1).padStart(8)}`);
}
console.log(`median climb fraction: ${f(med(good.map(r=>r.climb_frac))*100,0)}%`);
// P_flat/P_avg reconciliation: data (extracted flat / sheet <W>_mes) vs sheet column AB
const dr = good.map(r=>r.data_ratio).filter(Number.isFinite);
const sr = good.map(r=>r.sheet_ratio).filter(Number.isFinite);
console.log(`P_flat/<W>_mes — data(extracted): median ${f(med(dr),2)}  ·  sheet(AB): median ${f(med(sr),2)}  (n_sheet=${sr.length})`);
console.log(`v_f — extracted flatEqSpeed: ${f(med(good.map(r=>r.vf_kmh)),1)}  ·  sheet-derived: ${f(med(good.map(r=>r.vf_sheet_kmh)),1)}  ·  measured flat: ${f(med(good.map(r=>r.vf_meas_kmh)),1)} km/h (medians)`);

// ---- per-regime breakdown (energy-weighted totals across rides, kJ) ----
const totEmp = REG.climb.emp + REG.flat.emp + REG.descent.emp;
console.log('\n' + '='.repeat(64));
console.log('PER-REGIME energy (Σ over rides, kJ) and Δ% vs empirical ∫P·dt');
console.log(`${'regime'.padEnd(9)}${'share'.padStart(6)}${'emp'.padStart(8)}${'canon'.padStart(8)}${'off'.padStart(8)}${'cf'.padStart(8)}   ${'canonΔ%'.padStart(8)}${'offΔ%'.padStart(7)}${'cfΔ%'.padStart(7)}`);
console.log('-'.repeat(74));
for (const rg of ['climb', 'flat', 'descent']) {
  const r = REG[rg], d = m => r.emp ? (m - r.emp) / r.emp * 100 : NaN;
  console.log(
    rg.padEnd(9) + f(r.emp / totEmp * 100, 0).padStart(5) + '%' +
    f(r.emp, 0).padStart(8) + f(r.canon, 0).padStart(8) + f(r.off, 0).padStart(8) + f(r.cf, 0).padStart(8) + '   ' +
    f(d(r.canon), 1).padStart(8) + f(d(r.off), 1).padStart(7) + f(d(r.cf), 1).padStart(7));
}

// ---- elevation noise in h+ ----
console.log('\n' + '='.repeat(64));
console.log('ELEVATION NOISE — total ascent h+ (km, Σ over rides) vs hysteresis threshold');
const hraw = ELEV.h[0];
console.log(`${'smoothing'.padEnd(18)}${'Σ h+ (km)'.padStart(10)}${'% of raw'.padStart(9)}`);
for (const t of TAUS) console.log(`${(t === 0 ? 'raw (every step)' : 'hysteresis ' + t + ' m').padEnd(18)}${f(ELEV.h[t] / 1000, 1).padStart(10)}${f(ELEV.h[t] / hraw * 100, 0).padStart(8)}%`);
console.log(`engine (5 m grid)  ${f(ELEV.eng / 1000, 1).padStart(8)}${f(ELEV.eng / hraw * 100, 0).padStart(8)}%   <- what approximate's beta*h+ uses`);
const noiseKJ = ELEV.gravRaw - ELEV.grav3;
console.log(`\nClimb-gravity energy beta*h+ : raw ${f(ELEV.gravRaw, 0)} kJ -> 3 m-smoothed ${f(ELEV.grav3, 0)} kJ`);
console.log(`noise in h+ (raw - 3 m): ${f(ELEV.h[0] - ELEV.h[3], 0)} m total = ${f(noiseKJ, 0)} kJ`
  + ` = ${f(noiseKJ / REG.climb.emp * 100, 0)}% of empirical CLIMB energy, ${f(noiseKJ / totEmp * 100, 1)}% of total`);
for (const sk of ['rwgps_trip', 'strava']) {
  const s = ELEV.bySrc[sk];
  console.log(`  ${sk.padEnd(11)} raw->3 m shrink: ${f((1 - s.h3 / s.raw) * 100, 0)}% (raw ${f(s.raw / 1000, 1)} km -> ${f(s.h3 / 1000, 1)} km)`);
}

// ---- effect of the 3 m elevation filter ----
console.log('\n' + '='.repeat(64));
console.log(`APPLYING THE ${TAU_SMOOTH} m ELEVATION FILTER — engine h+ ${f(ELEV.eng/1000,1)} km -> ${f(ELEV.engS/1000,1)} km`);
console.log(`${'metric'.padEnd(26)}${'raw'.padStart(9)}${'+filter'.padStart(9)}`);
const climbD = (k) => REG.climb.emp ? (REG.climb[k] - REG.climb.emp) / REG.climb.emp * 100 : NaN;
console.log(`${'CLIMB energy Δ% — canon'.padEnd(26)}${f(climbD('canon'),1).padStart(9)}${f(climbD('canonS'),1).padStart(9)}`);
console.log(`${'CLIMB energy Δ% — off'.padEnd(26)}${f(climbD('off'),1).padStart(9)}${f(climbD('offS'),1).padStart(9)}`);
console.log(`${'CLIMB energy Δ% — cf'.padEnd(26)}${f(climbD('cf'),1).padStart(9)}${f(climbD('cfS'),1).padStart(9)}`);
const medSign = (k) => med(good.map(r => r[k]).filter(Number.isFinite));
console.log(`${'TOTAL median Δ% — canon'.padEnd(26)}${f(medSign('canon_vs_emp'),1).padStart(9)}${f(medSign('canonS_vs_emp'),1).padStart(9)}`);
console.log(`${'TOTAL median Δ% — off'.padEnd(26)}${f(medSign('off_vs_emp'),1).padStart(9)}${f(medSign('offS_vs_emp'),1).padStart(9)}`);
console.log(`${'TOTAL median Δ% — cf'.padEnd(26)}${f(medSign('cf_vs_emp'),1).padStart(9)}${f(medSign('cfS_vs_emp'),1).padStart(9)}`);

// ---- low-compute heuristic for k_h (no profile, only totals h+, x) ----
console.log('\n' + '='.repeat(64));
console.log('HEURISTIC for k_h from totals only — target = deadband-smoothed h+');
const cMed = med(KH.map(r => r.c));               // spurious ascent rate (m/km)
const khMed = med(KH.map(r => r.kh));             // constant-k_h fallback
console.log(`spurious ascent rate c = h+_raw - h+_smooth per km:  median ${f(cMed,1)} m/km  (IQR ${f(med(KH.map(r=>r.c).filter(x=>x<cMed)),1)}–${f(med(KH.map(r=>r.c).filter(x=>x>cMed)),1)})`);
console.log(`constant k_h (smooth/raw):  median ${f(khMed,2)}  (range ${f(Math.min(...KH.map(r=>r.kh)),2)}–${f(Math.max(...KH.map(r=>r.kh)),2)})`);
// score each heuristic: predicted corrected h+ vs the true smoothed h+, |rel err|
const errConstKh = KH.map(r => Math.abs(khMed * r.hpRaw - r.hpSm) / r.hpSm);
const errRate    = KH.map(r => Math.abs(Math.max(0, r.hpRaw - cMed * r.xkm) - r.hpSm) / r.hpSm);
console.log(`\nheuristic h+_corr vs true smoothed h+ — median |rel err|:`);
console.log(`  (A) constant k_h = ${f(khMed,2)}                 : ${f(med(errConstKh)*100,1)}%`);
console.log(`  (B) subtract rate: h+ - ${f(cMed,1)}·x_km        : ${f(med(errRate)*100,1)}%   <- physics-based`);
console.log(`implied k_h(hilliness) = 1 - c/(h+/x):  flat ride 30 m/km -> ${f(1-cMed/30,2)},  hilly 150 m/km -> ${f(1-cMed/150,2)}`);

// ---- sustained-climb energy balance (the clean k_h fit) ----
console.log('\n' + '='.repeat(64));
console.log('SUSTAINED-CLIMB ENERGY BALANCE — sections ≥3% over ≥100 m (measured vs expected)');
const SCexp = SC.egrav + SC.eroll + SC.eaero;
console.log(`  ${SC.n} climb sections over ${SC.perRide.length} rides; sustained Δh = ${f(SC.dh,0)} m = ${f(SC.dh/SC.totalAsc*100,0)}% of total ascent`);
console.log(`  measured Σ∫P·dt on climbs : ${f(SC.emeas,0)} kJ`);
console.log(`  expected (grav+roll+aero) : ${f(SCexp,0)} kJ   (grav ${f(SC.egrav,0)} + roll ${f(SC.eroll,0)} + aero ${f(SC.eaero,0)})`);
console.log(`  measured / expected       : ${f(SC.emeas/SCexp,2)}`);
console.log(`  k_h(sustained) = (measured − roll − aero) / gravity = ${f((SC.emeas-SC.eroll-SC.eaero)/SC.egrav,2)}`);
const khs = SC.perRide.map(r=>r.kh).filter(Number.isFinite).sort((a,b)=>a-b);
console.log(`  per-ride k_h(sustained): median ${f(med(khs),2)}  [${f(khs[0],2)}–${f(khs[khs.length-1],2)}]`);

// ---- cross-comparison: canonical vs smoothed vs k_smooth (benchmark = empirical ∫P·dt ≈ sheet Work Bike) ----
console.log('\n' + '='.repeat(64));
console.log('CROSS-COMPARISON vs empirical ∫P·dt (≈ sheet Work Bike), 44 rides');
console.log(`${'model'.padEnd(34)}${'n'.padStart(3)}${'med|Δ%|'.padStart(9)}${'medΔ%'.padStart(8)}${'meanΔ%'.padStart(8)}`);
for (const [lab, key] of [
  ['canonical (forward sim)', 'canon_vs_emp'],
  [`smoothed (cf + real ${TAU_SMOOTH} m deadband)`, 'cfS_vs_emp'],
  ['k_smooth (cf + scalar, no smoothing)', 'ksmooth_vs_emp']]) {
  const s = stats(key);
  console.log(`${lab.padEnd(34)}${String(s.n).padStart(3)}${f(s.medAbs,1).padStart(9)}${f(s.medSigned,1).padStart(8)}${f(s.mean,1).padStart(8)}`);
}

// ---- fitted ε per ride (smoothed model) vs the sheet's g_d_eff ----
console.log('\n' + '='.repeat(64));
console.log('ε per ride: sheet g_d_eff · whole-ride fit (smoothed) · descent-energy-balance (epsFromFIT)');
console.log(`${'ride'.padEnd(26)}${'sheet'.padStart(7)}${'fit'.padStart(7)}${'balance'.padStart(9)}`);
for (const r of good) console.log(`${r.ride.slice(0,25).padEnd(26)}${f(r.eps_sheet,2).padStart(7)}${f(r.eps_fit,2).padStart(7)}${f(r.eps_bal,2).padStart(9)}`);
const efit = good.map(r => r.eps_fit).filter(Number.isFinite).sort((a,b)=>a-b);
const ebal = good.map(r => r.eps_bal).filter(Number.isFinite).sort((a,b)=>a-b);
console.log(`median: sheet ${f(med(good.map(r=>r.eps_sheet)),2)}  fit ${f(med(efit),2)} [${f(efit[0],2)}..${f(efit[efit.length-1],2)}]  balance ${f(med(ebal),2)} [${f(ebal[0],2)}..${f(ebal[ebal.length-1],2)}]`);

// csv
const cols = ['ride','source','dist_km','climb_frac','empirical','canonical','approx_off','approx_cf','approx_vc','approx_cf_sheet','canon_vs_emp','off_vs_emp','cf_vs_emp','vc_vs_emp','cfsheet_vs_emp','cfmeas_vs_emp','cfS_vs_emp','canonS_vs_emp','ksmooth_vs_emp','p_avg','wmes','pflat_extracted','pflat_sheet','data_ratio','sheet_ratio','vf_kmh','vf_sheet_kmh','vf_meas_kmh','pClimb','pFlat','pDescent','error'];
const csv = [cols.join(',')].concat(good.concat(rows.filter(r=>r.error)).map(r =>
  cols.map(c => { const v = r[c]; return v == null ? '' : (typeof v === 'number' ? (Number.isInteger(v)?v:v.toFixed(2)) : `"${v}"`); }).join(','))).join('\n');
fs.writeFileSync(path.join(RESULTS, 'model_comparison.csv'), csv + '\n');
console.log(`\nwrote model_comparison.csv (${good.length} rides)`);
console.log(`conservation identity: worst per-ride rel residual ${CONS.max.toExponential(2)} (${CONS.ride ?? '—'}) — must stay ≤ 1e-6`);
