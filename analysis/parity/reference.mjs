// FROZEN JS REFERENCE — the verbatim engine + pts-pipeline functions from the
// retired harness/compare.mjs (converted to Python 2026-07; see harness/compare.py).
// These are the exact implementations that produced the published numbers.
// analysis/parity/run_parity.py extracts them at run time and machine-checks the
// Python port (analysis/bem) against them. DO NOT EDIT — this file is a historical
// reference; a model change lands in the app (applet/index.html) and in bem, and
// parity for changed behaviour is asserted against the app copy.
// Globals the functions expect (same as compare.mjs):
//   const G = 9.81, NS = 240; let H, physProfile;

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
function haversine(a, b) {
  const R = 6371000, toR = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toR, dLon = (b.lon - a.lon) * toR;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}
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
function ascentHyst(h, tau) {
  let gain = 0;
  if (tau <= 0) { for (let i = 1; i < h.length; i++) { const d = h[i] - h[i - 1]; if (d > 0) gain += d; } return gain; }
  let ref = h[0];
  for (let i = 1; i < h.length; i++) { const d = h[i] - ref; if (d >= tau) { gain += d; ref = h[i]; } else if (d <= -tau) { ref = h[i]; } }
  return gain;
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
