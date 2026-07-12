#!/usr/bin/env node
// Parity runner — evaluates the VERBATIM JS reference implementations against
// cases supplied on stdin (JSON) and prints results as JSON on stdout.
//
// Functions are extracted from the source files at RUN TIME (same technique
// as igc_resolution_test.mjs's engine reuse): no copies here to drift. App
// functions come from applet/index.html; the pts pipeline from
// compare.mjs. Every function in both files starts at column 0 with
// "function NAME(" and ends at the first column-0 "}".
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = fs.readFileSync(path.join(HERE, '..', '..', 'applet', 'index.html'), 'utf8');
const CMP = fs.readFileSync(path.join(HERE, '..', '..', 'harness', 'compare.mjs'), 'utf8');

function extract(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`function ${name} not found`);
  const end = src.indexOf('\n}', start);
  if (end < 0) throw new Error(`end of ${name} not found`);
  return src.slice(start, end + 2);
}

const APP_FNS = ['flatEqSpeed', 'resampleProfile', 'smoothElevation', 'canonical',
  'approximate', 'v2Edge', 'approxTime', 'parseFIT', 'extractRegimePowers',
  'epsFromFIT', 'epsGeom'];
const CMP_FNS = ['haversine', 'ptsFromFIT', 'finishPts', 'empiricalKJ',
  'overallMeanPower', 'measuredFlatSpeed', 'epsFromBalance', 'deadband',
  'ascentHyst', 'buildProfile'];

// buildProfile writes the module globals physProfile/H — replicate them.
const preamble = 'const G = 9.81, NS = 240; let H = new Float64Array(NS); let physProfile = null;\n';
const body = APP_FNS.map(n => extract(APP, n)).join('\n')
  + '\n' + CMP_FNS.map(n => extract(CMP, n)).join('\n')
  + '\nreturn { flatEqSpeed, resampleProfile, smoothElevation, canonical, approximate,'
  + ' v2Edge, approxTime, parseFIT, extractRegimePowers, epsFromFIT, epsGeom, haversine,'
  + ' ptsFromFIT, empiricalKJ, overallMeanPower, measuredFlatSpeed, epsFromBalance,'
  + ' deadband, ascentHyst, buildProfile, getPhysProfile: () => physProfile };';
const F = new Function(preamble + body)();

// JSON-safe: Infinity/NaN -> tagged strings; typed arrays -> plain arrays.
const safe = (v) => {
  if (typeof v === 'number') return Number.isFinite(v) ? v : (Number.isNaN(v) ? '__nan__' : (v > 0 ? '__inf__' : '__-inf__'));
  if (ArrayBuffer.isView(v)) return Array.from(v, safe);
  if (Array.isArray(v)) return v.map(safe);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, safe(x)]));
  return v;
};
const sum = (arr) => { let s = 0; for (const x of arr) s += x; return s; };

const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = cases.map((c) => {
  if (c.kind === 'flatEq') return safe(F.flatEqSpeed(c.P, c.p));
  if (c.kind === 'engines') {
    const prof = c.dx ? F.resampleProfile(c.profile, c.dx) : c.profile;
    const profA = F.smoothElevation(prof, c.tau || 0);
    const can = F.canonical(prof, c.pw, c.p);
    const a = F.approximate(profA, c.p, c.vf, c.eps, c.opts);
    const v2 = F.v2Edge(prof, c.p, c.vf, c.v2opts);
    const at = F.approxTime(profA, c.p, c.vf, c.pw);
    return safe({
      canonical: { legE: can.legE, t: can.t, Wrr: can.Wrr, Waero: can.Waero,
        Wgrav: can.Wgrav, Wbrake: can.Wbrake, dKE: can.dKE, dispE: can.dispE,
        avgV: can.avgV, minV: can.minV, stalled: can.stalled,
        speedSum: sum(can.speed), brkSum: sum(can.brk) },
      approx: a, v2, atime: at,
    });
  }
  if (c.kind === 'fit') {
    const buf = Buffer.from(c.b64, 'base64');
    const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    const recs = F.parseFIT(ab);
    const pts = F.ptsFromFIT(ab);
    const rp = F.extractRegimePowers(pts, c.climbThr, c.descThr);
    F.buildProfile(pts.map(q => q.x), pts.map(q => q.alt));
    const phys = F.getPhysProfile();
    return safe({
      nRecs: recs.length, recs: recs.slice(0, 8), lastRec: recs[recs.length - 1],
      nPts: pts.length, pts: pts.slice(0, 5),
      empKJ: F.empiricalKJ(pts), meanP: F.overallMeanPower(pts),
      rp,
      vfMeas: F.measuredFlatSpeed(pts),
      epsBal: F.epsFromBalance(pts, c.p),
      epsFit: F.epsFromFIT(pts, c.p),
      profSum: { x: sum(phys.x), h: sum(phys.h), n: phys.x.length },
    });
  }
  if (c.kind === 'epsgeom') return safe(F.epsGeom(c.profile, c.p, c.vf));
  if (c.kind === 'deadband') return safe({ h: F.deadband(c.h, c.tau), asc: F.ascentHyst(c.h, c.tau) });
  throw new Error(`unknown kind ${c.kind}`);
});
process.stdout.write(JSON.stringify(out));
