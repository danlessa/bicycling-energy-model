#!/usr/bin/env node
// Inventory of P. Paz's Strava history export (data/activities/strava_ppaz/, gitignored:
// third-party GPS shared with consent — see the article's Ethics section).
//
// Goal: find which activities are usable for the second-rider model verification —
// i.e. CYCLING rides WITH POWER (the empirical ∫P·dt benchmark needs a power meter).
// Scans every .fit / .fit.gz, reads sport + record stats, and writes
// strava_ppaz_manifest.json (gitignored via data/activities/*.json).
//
//   node ppaz_inventory.mjs
//
// parseFIT is the verbatim copy used by all harnesses (censo_compare.mjs), extended
// ONLY to also capture the sport enum (message 12 field 0 / session 18 field 5) —
// the record decoding is untouched.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '..', 'data', 'activities');
const DIR = path.join(DATA, 'strava_ppaz');
const SPORT = { 0: 'generic', 1: 'run', 2: 'ride', 5: 'swim', 11: 'walk', 17: 'hike' };

function parseFIT(buffer) {
  const dv = new DataView(buffer);
  if (buffer.byteLength < 14) throw new Error('FIT muito curto');
  const headerSize = dv.getUint8(0), dataSize = dv.getUint32(4, true);
  if (String.fromCharCode(dv.getUint8(8), dv.getUint8(9), dv.getUint8(10), dv.getUint8(11)) !== '.FIT') throw new Error('no .FIT');
  const end = Math.min(headerSize + dataSize, buffer.byteLength);
  let pos = headerSize; const defs = {}, records = [];
  let lastTs;   // running timestamp for compressed-timestamp headers (5-bit offset, 32 s rollover)
  let sport;    // first sport enum seen (msg 12 field 0, or session msg 18 field 5)
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
        else if ((def.gmn === 12 && f.num === 0) || (def.gmn === 18 && f.num === 5)) {
          const v = read(p, f.bt, def.little);
          if (v !== undefined && sport === undefined) sport = v;
        }
        else if (f.num === 253) {   // any message's timestamp advances the running clock
          const v = read(p, f.bt, def.little);
          if (v !== undefined) rec.time = v;
        }
        p += f.size;
      }
      pos = p + def.devSize;
      if (tsOffset !== undefined && rec.time === undefined && lastTs !== undefined) {
        let ts = (lastTs & ~31) | tsOffset;
        if (ts < lastTs) ts += 32;
        rec.time = ts;
      }
      if (rec.time !== undefined) lastTs = rec.time;
      if (def.gmn === 20) records.push(rec);
    }
  }
  return { records, sport };
}

const slice = b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const FIT_EPOCH = 631065600;   // 1989-12-31 UTC, seconds

const files = fs.readdirSync(DIR).filter(f => f.endsWith('.fit') || f.endsWith('.fit.gz')).sort();
const out = []; let errors = 0;
for (const f of files) {
  try {
    let buf = fs.readFileSync(path.join(DIR, f));
    if (f.endsWith('.gz')) buf = zlib.gunzipSync(buf);
    const { records: recs, sport } = parseFIT(slice(buf));
    if (recs.length < 2) throw new Error('sem registros');
    const n = recs.length;
    let nPow = 0, nPowPos = 0, nCad = 0, nAlt = 0, maxDist = 0, t0, t1;
    for (const r of recs) {
      if (r.power !== undefined) { nPow++; if (r.power > 0) nPowPos++; }
      if (r.cad !== undefined) nCad++;
      if (r.alt !== undefined) nAlt++;
      if (r.dist !== undefined && r.dist > maxDist) maxDist = r.dist;
      if (r.time !== undefined) { if (t0 === undefined) t0 = r.time; t1 = r.time; }
    }
    out.push({
      id: f.replace(/\.fit(\.gz)?$/, ''), file: path.join('strava_ppaz', f),
      sport: SPORT[sport] ?? (sport === undefined ? 'unknown' : `sport${sport}`),
      date: t0 !== undefined ? new Date((t0 + FIT_EPOCH) * 1000).toISOString().slice(0, 10) : null,
      hours: t0 !== undefined ? +((t1 - t0) / 3600).toFixed(2) : null,
      km: +(maxDist / 1000).toFixed(1), n,
      powCov: +(nPow / n).toFixed(3), powPos: +(nPowPos / n).toFixed(3),
      cadCov: +(nCad / n).toFixed(3), altCov: +(nAlt / n).toFixed(3),
    });
  } catch (e) { errors++; }
}
fs.writeFileSync(path.join(DATA, 'strava_ppaz_manifest.json'), JSON.stringify(out, null, 1));

// ---- summary ----
const bySport = {};
for (const a of out) (bySport[a.sport] ??= []).push(a);
console.log(`P. PAZ STRAVA EXPORT — ${files.length} FIT files, ${out.length} parsed, ${errors} errors\n`);
console.log('sport      n     w/ power(>50% cov)   rides>20km w/ power');
for (const [s, arr] of Object.entries(bySport).sort((a, b) => b[1].length - a[1].length)) {
  const pow = arr.filter(a => a.powCov > 0.5);
  const big = pow.filter(a => a.km > 20);
  console.log(`${s.padEnd(9)}${String(arr.length).padStart(5)}${String(pow.length).padStart(13)}${String(big.length).padStart(19)}`);
}
const rides = (bySport.ride || []).filter(a => a.powCov > 0.5);
if (rides.length) {
  const dates = rides.map(r => r.date).filter(Boolean).sort();
  const kms = rides.map(r => r.km).sort((a, b) => a - b);
  const q = p => kms[Math.floor(p * (kms.length - 1))];
  console.log(`\nRIDES WITH POWER: ${rides.length}`);
  console.log(`  dates ${dates[0]} … ${dates[dates.length - 1]}`);
  console.log(`  km: min ${q(0)}  p25 ${q(.25)}  median ${q(.5)}  p75 ${q(.75)}  max ${q(1)}`);
  console.log(`  alt coverage ≥99%: ${rides.filter(r => r.altCov >= 0.99).length}`);
  console.log(`  cadence coverage ≥50%: ${rides.filter(r => r.cadCov >= 0.5).length}`);
}
console.log('\nwrote strava_ppaz_manifest.json');
