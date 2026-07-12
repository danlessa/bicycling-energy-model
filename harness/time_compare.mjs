#!/usr/bin/env node
// TIME-MODEL empirical test across all three datasets (longões 44 · censo 62 · P. Paz 441).
// The energy law is validated (Entries 1–12); its TIME twin — t = x*/v_f with
// x* = x + k₊·h₊ − k₋·h₋, k₊ = v_f·β/P_climb (clean) and k₋ the lumped time-ε, joined by the
// ε↔k₋ bridge through descent power (article §5, the paper's SECOND novel claim) — was
// explicitly THEORY-ONLY (notas.md, article §10.4: "nothing calibrates k₋ against measured
// ride times"). This harness supplies the missing empirical leg.
//
// Engines are VERBATIM copies (assembled programmatically from ppaz_compare.mjs +
// compare.mjs's ptsFromGPX + applet/index.html's approxTime — keep in sync).
// New instruments: extractRegimeStats (per-regime moving time/dist/vertical, same 30 m
// grade window + VSTOP gate as extractRegimePowers) and the predictor battery.
//
// Design (fixed after an adversarial methods review — see the plan / Entry 13):
//  · Target: T_mov_bin = moving time over powered+moving segments (v ≥ 0.5 km/h, power present).
//    T_mov (all moving) and T_el (elapsed) reported for stop-fraction context; timeOK gates
//    rides whose powered segments cover < 90% of moving time.
//  · Coefficient tests are built v_f-free / part-whole-safe: r₊ = P̄_climb·t₊/(β·h₊) (→1 on
//    steep climbs) instead of a k₊ scatter that shares v_f; descent SPEED v_desc_meas = x₋/t₋
//    vs the bridge v_desc = P̄_desc/(α − ε·β·s̄₋) instead of a k₋ scatter that shares 1/s̄.
//    ε is the FROZEN geometry estimator clamp01(ε_coast − 0.13); bridge used only in its
//    validity region (P̄_desc ≥ 0.2·P̄_flat AND α − ε·β·s̄₋ > 0), else the equilibrium solver.
//  · One h± definition (30 m regime-binned) for measured AND predicted sides; a 30 m-cell
//    profile h± sensitivity reported once.
//  · Predictors vs T_mov_bin, both v_f modes (power-conditioned flatEqSpeed = headline;
//    speed-anchored x_flat/t_flat = diagnostic): T0 x/v_f · TS Scarf k₊=8 · T1a ascent-only ·
//    T1b full, scalar k₋ fit ONCE on longões then FROZEN · T1c per-ride bridge k₋ · T2
//    approxTime · T3 canonical · OLS ceiling (a·x+b·h₊+c·h₋ fit on longões, frozen).
//  · PRE-DECLARED PRIMARY ENDPOINT: T1b, power-conditioned v_f, med|Δ%| vs T_mov_bin, on the
//    441 P. Paz rides. Reported whatever it is.
//
//   node time_compare.mjs        (reads the three gitignored track sets + manifests)
// Output: console report + time_comparison.csv (gitignored via results/*).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '..', 'data', 'activities');
const RESULTS = path.join(HERE, '..', 'results');
fs.mkdirSync(RESULTS, { recursive: true });
const G = 9.81, NS = 240;
const VMAX = 38 / 3.6, VSTART = 15 / 3.6;
const VMAX_HI = 55 / 3.6;                       // descent-cap sensitivity for the fast rider
const CLIMB_THR = 0.02, DESC_THR = -0.015, ENGINE_DX = 5, TAU_SMOOTH = 2;
const VSTOP = 0.5 / 3.6;
// ASSUMED generic rider for censo + P. Paz (P. Paz mass overridden below). Longões carry
// per-ride physics in model_inputs.json.
const ASSUMED = { m: 78, CdA: 0.40, Crr: 0.008, rho: 1.13, keff: 0.98, wind: 0 };
const PPAZ_MASS = process.env.PPAZ_M ? +process.env.PPAZ_M : 74.3;   // Entry 12 inversion
const ZWIFT = 260;

let H = new Float64Array(NS), physProfile = null;
let FIT_MANUF;

// ===== engines: VERBATIM from ppaz_compare.mjs (haversine … epsCellsPz) =====
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

// approxTime — VERBATIM from applet/index.html
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
  let buf = fs.readFileSync(path.join(DATA, file));
  if (file.endsWith('.gz')) buf = zlib.gunzipSync(buf);
  if (file.endsWith('.gpx') || file.endsWith('.gpx.gz')) return ptsFromGPX(buf.toString('utf8'));
  return ptsFromFIT(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
};

// ---- build the per-ride measured record (corpus-agnostic) ----
function measureRide(pts, p, label, corpus) {
  buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
  const prof = resampleProfile(physProfile, ENGINE_DX);
  const rs = extractRegimeStats(pts, CLIMB_THR, DESC_THR);
  const Pflat = rs.Pflat != null ? rs.Pflat : overallMeanPower(pts);
  const Pclimb = rs.Pclimb != null ? rs.Pclimb : Pflat;
  const Pdesc = rs.Pdesc != null ? rs.Pdesc : 0;
  const pw = { climb: Pclimb, flat: Pflat, descent: Pdesc, climbThr: CLIMB_THR, descThr: DESC_THR };
  const beta = p.m * G / p.keff;
  const vfPow = flatEqSpeed(Pflat, p);
  const vfMeas = rs.tF > 0 && rs.xF > 0 ? rs.xF / rs.tF : vfPow;   // harmonic flat speed
  // measured total moving time (all v≥VSTOP points) + elapsed + stop fraction
  let tMov = 0, t0, t1;
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].v !== undefined && pts[i].v >= VSTOP) tMov += pts[i].dt || 0;
    if (pts[i].t !== undefined) { if (t0 === undefined) t0 = pts[i].t; t1 = pts[i].t; }
  }
  const tEl = (t0 !== undefined && t1 !== undefined && t1 > t0) ? t1 - t0 : NaN;
  const stopFrac = Number.isFinite(tEl) && tEl > 0 ? Math.max(0, 1 - tMov / tEl) : NaN;
  const timeOK = tMov > 0 && rs.tMovBin >= 0.9 * tMov;
  const cell = cellHpm(prof);
  // frozen ε (geometry) for the bridge
  const ec = epsCellsPz(pts, p);
  const epsFrozen = ec ? clamp01(ec.epsCoast - 0.13) : NaN;
  const aeroSpd = vfPow + p.wind, alpha = (p.Crr * p.m * G + 0.5 * p.rho * p.CdA * aeroSpd * Math.abs(aeroSpd)) / p.keff;
  const sbarC = rs.hC > 0 && rs.xC > 0 ? rs.hC / rs.xC : NaN;
  const sbarD = rs.hD > 0 && rs.xD > 0 ? rs.hD / rs.xD : NaN;
  // coefficient tests
  const rPlus = (rs.hC > 0 && Pclimb > 0) ? Pclimb * rs.tC / (beta * rs.hC) : NaN;
  const kPlusMeas = rs.hC > 0 ? (vfPow * rs.tC - rs.xC) / rs.hC : NaN;
  const vDescMeas = (rs.xD > 0 && rs.tD > 0) ? rs.xD / rs.tD : NaN;
  const denom = alpha - epsFrozen * beta * sbarD;
  const bridgeValid = Number.isFinite(sbarD) && Number.isFinite(epsFrozen) && Pdesc >= 0.2 * Pflat && denom > 0;
  const vDescPred = !Number.isFinite(sbarD) ? NaN
    : bridgeValid ? Pdesc / denom
    : descentEqSpeed(Pdesc, sbarD, { ...p, vmax: VMAX }, VMAX);
  const kMinusMeas = rs.hD > 0 ? (rs.xD - vfPow * rs.tD) / rs.hD : NaN;
  const kMinusBridge = (Number.isFinite(vDescPred) && Number.isFinite(sbarD) && sbarD > 0) ? (1 - vfPow / vDescPred) / sbarD : NaN;
  // mid/high-fidelity predictors (absolute seconds); T2 uses vf, T3 power-only
  const at38 = approxTime(prof, { ...p, vmax: VMAX }, vfPow, pw);
  const at55 = approxTime(prof, { ...p, vmax: VMAX_HI }, vfPow, pw);
  const c38 = canonical(prof, pw, { ...p, vmax: VMAX });
  const c55 = canonical(prof, pw, { ...p, vmax: VMAX_HI });
  return {
    corpus, ride: label,
    X: rs.xBin, hC: rs.hC, hD: rs.hD, xC: rs.xC, xF: rs.xF, xD: rs.xD, tC: rs.tC, tF: rs.tF, tD: rs.tD,
    sbarC, sbarD, hC_cell: cell.hplus, hD_cell: cell.hminus,
    tMovBin: rs.tMovBin, tMov, tEl, stopFrac, timeOK,
    Pflat, Pclimb, Pdesc, vfPow, vfMeas, beta, alpha, epsFrozen,
    rPlus, kPlusMeas, vDescMeas, vDescPred, bridgeValid, kMinusMeas, kMinusBridge,
    kMinusApprox: at38.kMinus, kPlusApprox: at38.kPlus,
    T2_38: at38.t, T2_55: at55.t, T3_38: c38.t, T3_55: c55.t, canonStall38: c38.stalled,
  };
}

// ---- predictors: given a measured row, a v_f mode, and fitted (k₋ scalar, OLS) → predicted seconds ----
// physics-derived climb multiplier: t₊≈β·h₊/P̄_climb (pure lift), minus the horizontal
// baseline 1/s̄₊ already in x. NOTE the pure-lift form under-charges by the roll+aero share
// (≈ the Entry-7 energy over-charge k_h≈1.26) — a known, disclosed bias, not fitted out here.
function kPlusExact(r, vf) { return Number.isFinite(r.sbarC) && r.sbarC > 0 ? vf * r.beta / r.Pclimb - 1 / r.sbarC : (r.Pclimb > 0 ? vf * r.beta / r.Pclimb : 0); }
function predict(r, mode, fit) {
  const vf = mode === 'pow' ? r.vfPow : r.vfMeas;
  const hC = r.hC, hD = r.hD;
  const kP = kPlusExact(r, vf);
  const out = {};
  out.T0 = r.X / vf;                                                   // naive: flat-only
  out.TS = (r.X + 8 * hC) / vf;                                        // Scarf literature k₊≈8, k₋=0
  out.T1a = (r.X + kP * hC) / vf;                                      // physics k₊, no descent term
  out.T1b = (r.X + kP * hC - fit.kMinus * hD) / vf;                    // + longões-frozen scalar k₋
  const kMinusR = Number.isFinite(r.kMinusBridge) ? r.kMinusBridge : 0;
  out.T1c = (r.X + kP * hC - kMinusR * hD) / vf;                       // + per-ride bridge k₋
  out.T2 = r.T2_38;                                                    // approxTime (uses vfPow), mode-invariant
  out.T3 = r.T3_38;                                                    // canonical forward sim
  // FAIR CEILING: same per-ride v_f as the physics, but k₊/k₋ FITTED on longões (not derived)
  // then frozen — isolates "does the physical k₊ match the best-fit k₊?" from the v_f model.
  out.TF = (r.X + fit.kP * hC - fit.kM * hD) / vf;
  // naive linear ceiling (absolute seconds, NO per-ride v_f) — illustrates why per-ride speed
  // is load-bearing: this transfers badly precisely because it bakes in one fixed flat pace.
  out.OLS = fit.ols[0] * r.X + fit.ols[1] * hC + fit.ols[2] * hD;
  return out;
}

// ---- drivers: assemble rows across the three corpora ----
const rows = [];
function pushRide(pts, p, label, corpus) {
  try {
    if (!hasPower(pts)) return;
    const r = measureRide(pts, p, label, corpus);
    if (r.tMovBin > 60) rows.push(r);
  } catch (e) { /* skip unparseable */ }
}

// longões (model_inputs.json: per-ride physics)
let nL = 0;
try {
  const inputs = JSON.parse(fs.readFileSync(path.join(DATA, 'model_inputs.json'), 'utf8'));
  for (const e of inputs) {
    if (!e.file || !e.has_power) continue;
    const fp = path.join(DATA, e.file);
    if (!fs.existsSync(fp)) continue;
    const p = { m: e.m, Crr: e.crr, CdA: e.cda, rho: e.rho, keff: e.keff, wind: (e.wind_kmh || 0) / 3.6, vmax: VMAX, vstart: VSTART };
    try { pushRide(readPts(e.file), p, e.label, 'longoes'); nL++; } catch (er) { /* skip */ }
  }
} catch (e) { console.error('longões load error', e.message); }
console.log(`longões: scanned ${nL} power entries`);

// censo (ASSUMED rider, physical-floor dataOK filter mirrors censo_compare.mjs)
let nC = 0;
try {
  const man = JSON.parse(fs.readFileSync(path.join(DATA, 'censohidrografico', 'manifest.json'), 'utf8'));
  for (const e of man) {
    if (!e.file) continue;
    const fp = path.join(DATA, e.file);
    if (!fs.existsSync(fp)) continue;
    const p = { ...ASSUMED, vmax: VMAX, vstart: VSTART };
    try {
      const pts = readPts(e.file);
      if (!hasPower(pts)) continue;
      // physical floor (deadband-smoothed climb PE) — same as censo_compare
      buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
      const prof = resampleProfile(physProfile, ENGINE_DX);
      const profS = { x: prof.x, h: deadband(prof.h, TAU_SMOOTH) };
      const aSm = approxComponents(profS, p, flatEqSpeed(overallMeanPower(pts), p), null);
      const emp = empiricalKJ(pts), peFloor = (p.m * G / p.keff) * aSm.hplus / 1000;
      if (emp < peFloor) continue;                 // dataOK filter
      pushRide(pts, p, e.name, 'censo'); nC++;
    } catch (er) { /* skip */ }
  }
} catch (e) { console.error('censo load error', e.message); }
console.log(`censo: ${nC} rides passed the physical floor`);

// P. Paz (mass = Entry-12 inversion; Entry-12 manifest filters; Zwift excluded)
let nP = 0, zw = 0;
try {
  const man = JSON.parse(fs.readFileSync(path.join(DATA, 'strava_ppaz_manifest.json'), 'utf8'));
  const cand = man.filter(a => a.sport === 'ride' && a.powCov > 0.5 && a.km >= 20 && a.altCov >= 0.99);
  for (const a of cand) {
    const p = { ...ASSUMED, m: PPAZ_MASS, vmax: VMAX, vstart: VSTART };
    try {
      const pts = readPts(a.file);
      if (FIT_MANUF === ZWIFT) { zw++; continue; }
      pushRide(pts, p, a.id, 'ppaz'); nP++;
    } catch (er) { /* skip */ }
    if (nP % 100 === 0 && nP) console.log(`  …ppaz ${nP}/${cand.length}`);
  }
} catch (e) { console.error('ppaz load error', e.message); }
console.log(`ppaz: ${nP} rides (skipped ${zw} Zwift), mass ${PPAZ_MASS} kg\n`);

// ---- clean gating per corpus ----
const clean = rows.filter(r => r.timeOK && Number.isFinite(r.tMovBin) && r.tMovBin > 0);
const byCorpus = c => clean.filter(r => r.corpus === c);
const L = byCorpus('longoes'), C = byCorpus('censo'), P = byCorpus('ppaz');

// ---- fit on longões (T_mov_bin target), then FREEZE ----
// scalar k₋ (T1b), holding k₊ = the physics-derived kPlusExact
function fitKMinus(train, mode) {
  let best = 0, bestErr = Infinity;
  for (let k = 0; k <= 20.0001; k += 0.1) {
    const errs = train.map(r => {
      const vf = mode === 'pow' ? r.vfPow : r.vfMeas;
      const pred = (r.X + kPlusExact(r, vf) * r.hC - k * r.hD) / vf;
      return Math.abs(pred - r.tMovBin) / r.tMovBin * 100;
    });
    const m = medOf(errs);
    if (m < bestErr) { bestErr = m; best = k; }
  }
  return { k: +best.toFixed(1), err: bestErr };
}
// FAIR-CEILING pair (k₊,k₋) both FITTED (power-conditioned v_f held per-ride) — the honest
// benchmark for the physics-derived k₊: same v_f model, best-fit hill coefficients.
function fitPair(train) {
  let bkP = 0, bkM = 0, bestErr = Infinity;
  for (let kp = 0; kp <= 25.0001; kp += 0.5) {
    for (let km = 0; km <= 15.0001; km += 0.5) {
      const errs = train.map(r => Math.abs((r.X + kp * r.hC - km * r.hD) / r.vfPow - r.tMovBin) / r.tMovBin * 100);
      const m = medOf(errs);
      if (m < bestErr) { bestErr = m; bkP = kp; bkM = km; }
    }
  }
  return { kP: bkP, kM: bkM, err: bestErr };
}
function fitOLS(train) {   // naive linear ceiling t = a·X + b·hC + c·hD (absolute seconds, no v_f)
  let A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], bvec = [0, 0, 0];
  for (const r of train) {
    const g = [r.X, r.hC, r.hD], y = r.tMovBin;
    for (let i = 0; i < 3; i++) { for (let j = 0; j < 3; j++) A[i][j] += g[i] * g[j]; bvec[i] += g[i] * y; }
  }
  const det = m => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  const D = det(A); if (Math.abs(D) < 1e-9) return [0, 0, 0];
  const col = (m, c, v) => m.map((row, i) => row.map((x, j) => j === c ? v[i] : x));
  return [det(col(A, 0, bvec)) / D, det(col(A, 1, bvec)) / D, det(col(A, 2, bvec)) / D];
}

const pairFit = fitPair(L);
const fitPow = { kMinus: fitKMinus(L, 'pow').k, kP: pairFit.kP, kM: pairFit.kM, ols: fitOLS(L) };
const fitMeas = { kMinus: fitKMinus(L, 'meas').k, kP: pairFit.kP, kM: pairFit.kM, ols: fitPow.ols };
if (fitPow.kMinus <= 0.05 || fitPow.kMinus >= 19.95) console.error(`NOTE k₋(power-cond) grid at boundary: ${fitPow.kMinus} — expected: vfPow over-estimates real moving-flat speed, so any k₋>0 worsens the median (speed-anchored fit disambiguates).`);

// paired sign test + Wilcoxon signed-rank (normal approx) on per-ride |Δ%|, predA vs predB
function pairedTest(set, mode, fit, keyA, keyB) {
  const d = [];   // |Δ%|_A − |Δ%|_B  (negative ⇒ A better)
  let wins = 0, losses = 0;
  for (const r of set) {
    const pr = predict(r, mode, fit);
    const a = Math.abs(pr[keyA] - r.tMovBin) / r.tMovBin * 100, b = Math.abs(pr[keyB] - r.tMovBin) / r.tMovBin * 100;
    if (!Number.isFinite(a) || !Number.isFinite(b)) continue;
    d.push(a - b); if (a < b) wins++; else if (a > b) losses++;
  }
  const n = wins + losses;
  const zSign = n > 0 ? (wins - n / 2) / Math.sqrt(n / 4) : NaN;   // sign test, continuity ignored
  // Wilcoxon signed-rank on nonzero d
  const nz = d.filter(x => x !== 0).map(x => ({ a: Math.abs(x), s: Math.sign(x) })).sort((p, q) => p.a - q.a);
  let i = 0, Wpos = 0; const m = nz.length;
  while (i < m) { let j = i; while (j < m - 1 && nz[j + 1].a === nz[i].a) j++; const rank = (i + j + 2) / 2; for (let k = i; k <= j; k++) if (nz[k].s > 0) Wpos += rank; i = j + 1; }
  const muW = m * (m + 1) / 4, sdW = Math.sqrt(m * (m + 1) * (2 * m + 1) / 24);
  const zW = sdW > 0 ? (Wpos - muW) / sdW : NaN;   // >0 ⇒ A worse (larger |Δ%| ranks)
  const pFromZ = z => Number.isFinite(z) ? 2 * (1 - 0.5 * (1 + erf(Math.abs(z) / Math.SQRT2))) : NaN;
  return { wins, losses, n, winFrac: n ? wins / n : NaN, medDiff: medOf(d), pSign: pFromZ(zSign), pWilcoxon: pFromZ(zW) };
}
function erf(x) { const t = 1 / (1 + 0.3275911 * Math.abs(x)); const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x); return x >= 0 ? y : -y; }

// ---- aggregate + report ----
const PREDS = ['T0', 'TS', 'T1a', 'T1b', 'T1c', 'T2', 'T3', 'TF', 'OLS'];
const f = (x, d = 1) => (x == null || Number.isNaN(x)) ? '—' : x.toFixed(d);
function scoreboard(set, mode, fit) {
  const out = {};
  for (const key of PREDS) {
    const ds = set.map(r => { const pr = predict(r, mode, fit)[key]; return Number.isFinite(pr) && r.tMovBin > 0 ? (pr - r.tMovBin) / r.tMovBin * 100 : NaN; }).filter(Number.isFinite);
    out[key] = { n: ds.length, medAbs: medOf(ds.map(Math.abs)), medSigned: medOf(ds) };
  }
  return out;
}
const LAB = { T0: 'T0  x/v_f (naive)', TS: 'TS  Scarf k₊=8', T1a: 'T1a ascent-only (physics k₊)', T1b: 'T1b full (physics k₊, k₋ frozen)', T1c: 'T1c per-ride bridge k₋', T2: 'T2  approxTime', T3: 'T3  canonical', TF: 'TF  FAIR ceiling (k₊,k₋ fit)', OLS: 'OLS naive-linear (no v_f)' };
function printScore(title, set, mode, fit) {
  const sb = scoreboard(set, mode, fit);
  console.log(`\n${title}  (n=${set.length}, v_f=${mode === 'pow' ? 'power-conditioned' : 'speed-anchored'})`);
  console.log(`${'predictor'.padEnd(34)}${'n'.padStart(4)}${'med|Δ%|'.padStart(9)}${'medΔ%'.padStart(8)}`);
  for (const key of PREDS) console.log(`${LAB[key].padEnd(34)}${String(sb[key].n).padStart(4)}${f(sb[key].medAbs).padStart(9)}${f(sb[key].medSigned).padStart(8)}`);
}

console.log('================================================================');
console.log('TIME-MODEL TEST — target = moving time over powered segments (T_mov_bin)');
console.log(`clean rides: longões ${L.length} · censo ${C.length} · ppaz ${P.length}`);
console.log(`\nFITTED ON LONGÕES, then FROZEN:`);
console.log(`  scalar k₋ (physics k₊):  power-cond=${fitPow.kMinus}  speed-anch=${fitMeas.kMinus}`);
console.log(`  FAIR ceiling (both fit, power-cond v_f):  k₊=${fitPow.kP}  k₋=${fitPow.kM}  (compare k₊ to the physics k₊)`);
console.log(`  naive-linear (abs seconds, no v_f):  t = ${f(fitPow.ols[0], 3)}·x + ${f(fitPow.ols[1], 3)}·h₊ + ${f(fitPow.ols[2], 3)}·h₋`);

// coefficient-level (energy-side) diagnostic — NOT independent time evidence
console.log('\n---------------- CLIMB OVER-CHARGE (energy identity, disclosed as NON-time) ----------------');
console.log('r₊ = P̄_climb·t₊/(β·h₊) ≡ k_eff·E_climb/(mg·h₊): t₊ cancels (P̄_climb≡E_climb/t₊), so this is the');
console.log('Entry-7 ENERGY over-charge, NOT independent time evidence — reported only for cross-corpus stability.');
for (const [nm, set] of [['longões', L], ['censo', C], ['ppaz', P]]) {
  const rp = set.map(r => r.rPlus).filter(Number.isFinite);
  const steep = set.filter(r => r.sbarC >= 0.05).map(r => r.rPlus).filter(Number.isFinite);
  console.log(`  ${nm.padEnd(8)} r₊ med ${f(medOf(rp), 2)} (n=${rp.length}) · steep s̄₊≥5% ${f(medOf(steep), 2)}`);
}

// descent-speed bridge test — lead with CORRELATION (median is over uncapped analytic form)
console.log('\n---------------- DESCENT BRIDGE (v_desc = P̄_desc/(α−ε·β·s̄), FROZEN ε) ----------------');
console.log('analytic bridge is UNCAPPED — near the α=ε·β·s̄ degeneracy it diverges; lead with correlation.');
for (const [nm, set] of [['longões', L], ['censo', C], ['ppaz', P]]) {
  const sub = set.filter(r => Number.isFinite(r.vDescMeas) && Number.isFinite(r.vDescPred) && r.hD >= 50 && r.xD >= 1000 && r.sbarD >= 0.03);
  const meas = sub.map(r => r.vDescMeas * 3.6), pred = sub.map(r => Math.min(r.vDescPred, 999) * 3.6);
  const inValid = set.filter(r => r.hD >= 50 && r.xD >= 1000 && r.sbarD >= 0.03);
  const validFrac = inValid.length ? inValid.filter(r => r.bridgeValid).length / inValid.length : NaN;
  console.log(`  ${nm.padEnd(8)} v_desc real descents (s̄₋≥3%, h₋≥50 m, x₋≥1 km, n=${sub.length}): corr ${f(corrOf(pred, meas), 2)} · med meas ${f(medOf(meas))} vs pred ${f(medOf(pred))} km/h · bridge-valid ${f(validFrac * 100, 0)}%`);
  console.log(`           k₋_meas med ${f(medOf(set.map(r => r.kMinusMeas)), 2)} (free, corpus-dependent) · stopFrac med ${f(medOf(set.map(r => r.stopFrac)) * 100, 0)}%`);
}

// scoreboards
console.log('\n---------------- TOTAL-TIME PREDICTORS ----------------');
printScore('LONGÕES (in-sample fit)', L, 'pow', fitPow);
printScore('CENSO (frozen)', C, 'pow', fitPow);
printScore('P. PAZ (frozen)', P, 'pow', fitPow);

console.log('\n================================================================');
const pep = scoreboard(P, 'pow', fitPow).T1b, pt0 = scoreboard(P, 'pow', fitPow).T0;
const test = pairedTest(P, 'pow', fitPow, 'T1b', 'T0');
console.log(`PRE-DECLARED PRIMARY ENDPOINT — T1b, power-conditioned v_f, P. Paz (out-of-sample):`);
console.log(`  median |Δ%| = ${f(pep.medAbs)} (signed ${f(pep.medSigned)}, n=${pep.n})  vs naive T0 ${f(pt0.medAbs)}  — modest`);
console.log(`  paired T1b−T0: wins ${test.wins}/${test.n} (${f(test.winFrac * 100, 0)}%) · med Δ|Δ%| ${f(test.medDiff, 2)}pp · sign p=${f(test.pSign, 3)} · Wilcoxon p=${f(test.pWilcoxon, 3)}`);
console.log(`  vs FAIR fitted ceiling TF ${f(scoreboard(P, 'pow', fitPow).TF.medAbs)} (physics competitive)`);
console.log('================================================================');

// diagnostics: speed-anchored (PARTIALLY IN-SAMPLE) + vmax + terciles + mass note
console.log('\n---------------- DIAGNOSTICS ----------------');
console.log('speed-anchored v_f = x_flat/t_flat SHARES measured flat time with the target — PARTIALLY IN-SAMPLE:');
printScore('P. PAZ speed-anchored v_f', P, 'meas', fitMeas);
for (const [nm, set] of [['longões', L], ['censo', C], ['ppaz', P]]) {
  const t2_38 = medOf(set.map(r => Number.isFinite(r.T2_38) ? Math.abs(r.T2_38 - r.tMovBin) / r.tMovBin * 100 : NaN));
  const t2_55 = medOf(set.map(r => Number.isFinite(r.T2_55) ? Math.abs(r.T2_55 - r.tMovBin) / r.tMovBin * 100 : NaN));
  const t3_38 = medOf(set.map(r => Number.isFinite(r.T3_38) ? Math.abs(r.T3_38 - r.tMovBin) / r.tMovBin * 100 : NaN));
  const t3_55 = medOf(set.map(r => Number.isFinite(r.T3_55) ? Math.abs(r.T3_55 - r.tMovBin) / r.tMovBin * 100 : NaN));
  console.log(`vmax sens (${nm}): T2 38/55 km/h ${f(t2_38)}/${f(t2_55)} · T3 ${f(t3_38)}/${f(t3_55)}`);
}
// hilliness terciles (P. Paz, EXPLORATORY — pre-motivated, not pre-registered): where the
// ascent term is physically expected to matter. Only the aggregate T1b-pow-ppaz was pre-declared.
console.log('\nP. Paz hilliness terciles (exploratory):');
const byHill = P.map(r => ({ r, h: r.hC / Math.max(1, r.X) })).sort((a, b) => a.h - b.h);
const third = Math.floor(byHill.length / 3);
for (const [nm, seg] of [['flat', byHill.slice(0, third)], ['mid', byHill.slice(third, 2 * third)], ['hilly', byHill.slice(2 * third)]]) {
  const set = seg.map(o => o.r);
  const sb = scoreboard(set, 'pow', fitPow);
  console.log(`  ${nm.padEnd(6)} (n=${set.length}, med h₊/x ${f(medOf(seg.map(o => o.h * 1000)), 1)} m/km): T0 ${f(sb.T0.medAbs)} · T1b ${f(sb.T1b.medAbs)} · TF ${f(sb.TF.medAbs)}`);
}
console.log('\nNOTE: run `PPAZ_M=70 node time_compare.mjs` and `PPAZ_M=78 …` for the mass-sensitivity of the endpoint.');

// ---- CSV ----
const cols = ['corpus', 'ride', 'X', 'hC', 'hD', 'hC_cell', 'hD_cell', 'xC', 'xF', 'xD', 'tC', 'tF', 'tD', 'sbarC', 'sbarD', 'tMovBin', 'tMov', 'tEl', 'stopFrac', 'timeOK', 'Pflat', 'Pclimb', 'Pdesc', 'vfPow', 'vfMeas', 'epsFrozen', 'rPlus', 'kPlusMeas', 'vDescMeas', 'vDescPred', 'bridgeValid', 'kMinusMeas', 'kMinusBridge', 'T2_38', 'T2_55', 'T3_38', 'T3_55'];
const predCols = [];
for (const r of clean) { const pr = predict(r, 'pow', fitPow); r._T1b = pr.T1b; r._T0 = pr.T0; }
const csv = [cols.concat(['T1b_pred', 'T0_pred']).join(',')]
  .concat(clean.map(r => cols.map(k => typeof r[k] === 'string' ? JSON.stringify(r[k]) : (typeof r[k] === 'boolean' ? (r[k] ? 1 : 0) : (Number.isFinite(r[k]) ? +Number(r[k]).toFixed(3) : ''))).concat([f(r._T1b, 1), f(r._T0, 1)]).join(',')))
  .join('\n');
fs.writeFileSync(path.join(RESULTS, 'time_comparison.csv'), csv + '\n');
console.log(`\nwrote time_comparison.csv (${clean.length} rides)`);
