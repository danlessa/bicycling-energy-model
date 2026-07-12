#!/usr/bin/env node
// Extract per-ride GPS track (lat, lon, recorded elevation, cumulative distance)
// from the .fit files, downsample by distance, and write one CSV per ride plus a
// tile manifest (1° tiles each ride touches). Feeds the DEM elevation comparison.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ACT = path.join(HERE, '..', '..', 'data', 'activities');
const OUTDIR = process.argv[2] || path.join(HERE, 'coords');   // where to write per-ride coord CSVs
const STEP = +(process.argv[3] || 50);   // downsample: keep a point roughly every STEP metres

// --- parseFIT, ported verbatim from applet/index.html (record msg 20) ---
function parseFIT(buffer) {
  const dv = new DataView(buffer);
  if (buffer.byteLength < 14) throw new Error('FIT muito curto');
  const headerSize = dv.getUint8(0), dataSize = dv.getUint32(4, true);
  if (String.fromCharCode(dv.getUint8(8), dv.getUint8(9), dv.getUint8(10), dv.getUint8(11)) !== '.FIT')
    throw new Error('no .FIT');
  const end = Math.min(headerSize + dataSize, buffer.byteLength);
  let pos = headerSize;
  const defs = {}, records = [];
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
    let local, isDef = false, hasDev = false;
    if (rh & 0x80) local = (rh >> 5) & 0x03;
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
      const def = defs[local]; if (!def) break;
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
          }
        }
        p += f.size;
      }
      pos = p + def.devSize;
      if (def.gmn === 20) records.push(rec);
    }
  }
  return records;
}

function tileName(lat, lon) {   // 1° tile SW-corner id, e.g. S24W047
  const la = Math.floor(lat), lo = Math.floor(lon);
  return (la < 0 ? 'S' : 'N') + String(Math.abs(la)).padStart(2, '0') +
         (lo < 0 ? 'W' : 'E') + String(Math.abs(lo)).padStart(3, '0');
}

fs.mkdirSync(OUTDIR, { recursive: true });
const inputs = JSON.parse(fs.readFileSync(path.join(ACT, 'model_inputs.json'), 'utf8'));
const tiles = new Set();
const summary = [];
for (const e of inputs) {
  if (!e.file || !e.file.endsWith('.fit')) continue;   // GPS-bearing fits only (Assou gpx handled separately if needed)
  let recs;
  try { recs = parseFIT(fs.readFileSync(path.join(ACT, e.file)).buffer); }
  catch (err) { summary.push({ ride: e.label, err: String(err.message) }); continue; }
  const gps = recs.filter(r => r.lat !== undefined && r.lon !== undefined && r.alt !== undefined);
  if (gps.length < 2) { summary.push({ ride: e.label, nrec: recs.length, gps: gps.length, note: 'no GPS' }); continue; }
  // downsample by distance (fall back to index if no dist field)
  const out = [];
  let lastD = -1e9, cum = 0, prev = null;
  for (const r of gps) {
    let d = r.dist;
    if (d === undefined) { if (prev) cum += haversine(prev, r); d = cum; prev = r; }
    if (d - lastD >= STEP || out.length === 0) { out.push({ lat: r.lat, lon: r.lon, ele: r.alt, d }); lastD = d; tiles.add(tileName(r.lat, r.lon)); }
  }
  const id = e.id;
  const lines = ['lon,lat,ele,d'].concat(out.map(p => `${p.lon.toFixed(6)},${p.lat.toFixed(6)},${p.ele.toFixed(1)},${p.d.toFixed(1)}`));
  fs.writeFileSync(path.join(OUTDIR, `${id}.csv`), lines.join('\n') + '\n');
  summary.push({ ride: e.label, id, pts: out.length, tiles: [...new Set(out.map(p => tileName(p.lat, p.lon)))].join(' ') });
}
function haversine(a, b) {
  const R = 6371000, t = Math.PI / 180;
  const s = Math.sin((b.lat - a.lat) * t / 2) ** 2 + Math.cos(a.lat * t) * Math.cos(b.lat * t) * Math.sin((b.lon - a.lon) * t / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

fs.writeFileSync(path.join(OUTDIR, '_tiles.txt'), [...tiles].sort().join('\n') + '\n');
console.log(`rides with GPS: ${summary.filter(s => s.pts).length}/${summary.length}`);
for (const s of summary) console.log(s.pts ? `  ${s.ride.slice(0,24).padEnd(24)} ${String(s.pts).padStart(5)} pts  [${s.tiles}]` : `  ${s.ride.slice(0,24).padEnd(24)} -- ${s.note || s.err}`);
console.log(`\n${tiles.size} unique 1° tiles -> ${path.join(OUTDIR, '_tiles.txt')}`);
console.log([...tiles].sort().join(' '));
