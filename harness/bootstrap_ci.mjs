// bootstrap_ci.mjs — bootstrap 95% CIs + paired sign tests for the article's
// headline medians (journal Entry 22; article v0.16 §7.1/§8.1/§8.4/§8.6/§8.8).
//
// Reads ONLY the per-ride CSVs already written by the other harnesses — no
// engine runs, no FIT parsing:
//   model_comparison.csv                      (compare.mjs, 44 longões)
//   censo_comparison.csv    (censo_compare.mjs, 62 clean)
//   ppaz_comparison.csv / jaam_comparison.csv (ppaz_compare / jaam_compare)
//   time_comparison.csv                       (time_compare.mjs)
//
// Every published median is reproduced as a GATE (±0.11 tolerance for the
// 1-decimal journal rounding) before its CI is reported; any gate failure
// exits non-zero. Bootstrap: percentile method, B = 10⁴, deterministic
// mulberry32 seed so the run is reproducible. Paired comparisons: exact
// two-sided sign test on |Δ%|.
//
// Usage: node bootstrap_ci.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '..', 'data', 'activities');
const RESULTS = path.join(HERE, '..', 'results');
fs.mkdirSync(RESULTS, { recursive: true });
let failed = false;

// --- CSV parser (quoted fields, no embedded newlines; strips quotes) ---
function parseCSV(p) {
  const text = fs.readFileSync(path.join(RESULTS, p), 'utf8').trim();
  const lines = text.split('\n');
  const split = (line) => {
    const out = []; let cur = '', q = false;
    for (const ch of line) {
      if (ch === '"') q = !q;
      else if (ch === ',' && !q) { out.push(cur); cur = ''; }
      else cur += ch;
    }
    out.push(cur);
    return out;
  };
  const head = split(lines[0]);
  return lines.slice(1).map(l => {
    const cells = split(l);
    return Object.fromEntries(head.map((h, i) => [h, cells[i]]));
  });
}

// --- deterministic RNG (mulberry32) ---
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  const n = s.length;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
};

const B = 10000;
function bootCI(values, seed) {
  const rand = rng(seed);
  const n = values.length;
  const stats = new Array(B);
  for (let b = 0; b < B; b++) {
    const sample = new Array(n);
    for (let i = 0; i < n; i++) sample[i] = values[(rand() * n) | 0];
    stats[b] = median(sample);
  }
  stats.sort((a, b) => a - b);
  return [stats[Math.floor(0.025 * B)], stats[Math.ceil(0.975 * B) - 1]];
}

function report(label, deltas, expectAbs = null, expectSigned = null) {
  const abs = deltas.map(Math.abs);
  const mAbs = median(abs), mSgn = median(deltas);
  const [aLo, aHi] = bootCI(abs, 42);
  const [sLo, sHi] = bootCI(deltas, 43);
  let gate = '';
  if (expectAbs != null) {
    const ok = Math.abs(mAbs - expectAbs) <= 0.11 &&
      (expectSigned == null || Math.abs(mSgn - expectSigned) <= 0.11);
    gate = ok ? ' GATE-OK' : ` GATE-FAIL(exp ${expectAbs}/${expectSigned})`;
    if (!ok) failed = true;
  }
  console.log(
    `${label.padEnd(34)} n=${String(deltas.length).padStart(3)}  ` +
    `med|Δ%|=${mAbs.toFixed(2).padStart(6)} [${aLo.toFixed(1)}, ${aHi.toFixed(1)}]  ` +
    `medΔ%=${mSgn.toFixed(2).padStart(7)} [${sLo.toFixed(1)}, ${sHi.toFixed(1)}]${gate}`);
}

// exact two-sided binomial sign test on paired |Δ%|
function logC(n, k) { let s = 0; for (let i = 1; i <= k; i++) s += Math.log(n - k + i) - Math.log(i); return s; }
function signP(w, l) {
  const n = w + l; let p = 0;
  for (let k = 0; k <= n; k++) {
    const pk = Math.exp(logC(n, k) - n * Math.LN2);
    if (k <= Math.min(w, l) || k >= Math.max(w, l)) p += pk;
  }
  return Math.min(1, p);
}
function paired(label, rows, colA, colB) {
  let w = 0, l = 0;
  for (const r of rows) {
    const a = Math.abs(parseFloat(r[colA])), b = Math.abs(parseFloat(r[colB]));
    if (!Number.isFinite(a) || !Number.isFinite(b)) continue;
    if (a < b) w++; else if (a > b) l++;
  }
  console.log(`${label}: A closer on ${w}/${w + l} (${(100 * w / (w + l)).toFixed(0)}%), sign test p=${signP(w, l).toFixed(4)}`);
}

const num = (r, c) => parseFloat(r[c]);
const col = (rows, c) => rows.map(r => num(r, c)).filter(Number.isFinite);

// ---------- 1. Longões scoreboard (44 rides), §8.1 ----------
console.log('== Longões (44 power rides), §8.1 scoreboard ==');
const lg = parseCSV('model_comparison.csv');
const LG = [
  ['approx cf + 2m smooth', 'cfS_vs_emp', 3.6, 2.2],
  ['canonical', 'canon_vs_emp', 5.1, -1.7],
  ['canonical + 2m smooth', 'canonS_vs_emp', 5.6, -3.5],
  ['approx cf + k_smooth', 'ksmooth_vs_emp', 5.8, -0.5],
  ['approx cf + sheet v_f', 'cfsheet_vs_emp', 7.2, -0.5],
  ['approx cf + measured v_f', 'cfmeas_vs_emp', 8.2, 6.7],
  ['approx cf', 'cf_vs_emp', 8.7, 8.6],
  ['approx off (baseline)', 'off_vs_emp', 19.3, 19.3],
];
for (const [label, c, ea, es] of LG) report(label, col(lg, c), ea, es);
paired('PAIRED champion (cfS) vs canonical', lg, 'cfS_vs_emp', 'canon_vs_emp');

// ---------- 2. Censo sweep (62 clean rides), §8.4 ----------
console.log('\n== Censo (clean urban rides), §8.4 sweep ==');
const cz = parseCSV('censo_comparison.csv').filter(r => r.dataOK === 'true');
if (cz.length !== 62) { console.log(`GATE-FAIL: expected 62 clean censo rides, got ${cz.length}`); failed = true; }
const CZ = [
  ['canonical', 'canon_d', 6.5, -3.4],
  ['smooth · ε=0.10', 'sm_0.10', 4.5, 3.4],
  ['smooth · ε=0.15', 'sm_0.15', 5.0, 1.3],
  ['smooth · ε=0.20', 'sm_0.20', 4.6, -0.8],
  ['poor-man · ε=0.20', 'pm_0.20', 3.9, 1.1],
  ['poor-man · ε=0.25', 'pm_0.25', 4.8, -1.2],
  ['poor-man · ε=geom', 'pm_geom', 6.3, -3.2],
  ['smooth · ε=geom', 'sm_geom', 7.6, -4.9],
  ['smooth · ε=0.00', 'sm_0.00', 7.6, 7.4],
  ['poor-man · ε=0.00', 'pm_0.00', 10.5, 10.5],
];
for (const [label, c, ea, es] of CZ) report(label, col(cz, c), ea, es);
paired('PAIRED poor-man ε0.20 vs canonical', cz, 'pm_0.20', 'canon_d');

// ---------- 3. P. Paz (441) and JAAM (219), §8.6 ----------
console.log('\n== P. Paz (441 rides), §8.6 ==');
const pp = parseCSV('ppaz_comparison.csv');
report('poor-man · ε=geom', col(pp, 'pm_geom'), 4.9, 0.6);
report('canonical', col(pp, 'canon_d'), 6.8, 5.0);
paired('PAIRED pm_geom vs canonical', pp, 'pm_geom', 'canon_d');
paired('PAIRED pm_geom vs sm_0.20', pp, 'pm_geom', 'sm_0.20');

console.log('\n== JAAM (219 rides), §8.6 ==');
const jm = parseCSV('jaam_comparison.csv');
report('smooth · ε=0.20', col(jm, 'sm_0.20'), 3.5, null);
report('smooth · ε=geom', col(jm, 'sm_geom'), 5.5, null);
paired('PAIRED sm_0.20 vs sm_geom', jm, 'sm_0.20', 'sm_geom');

// ---------- 4. Time model, P. Paz (§8.8 primary endpoint) ----------
// Target = tMovBin, exactly as time_compare.mjs's scoreboard() scores it.
console.log('\n== Time model, P. Paz (§8.8 primary endpoint) ==');
const tm = parseCSV('time_comparison.csv').filter(r => r.corpus === 'ppaz');
const tDelta = (r, c) => 100 * (num(r, c) - num(r, 'tMovBin')) / num(r, 'tMovBin');
report('T1b full (frozen)', tm.map(r => tDelta(r, 'T1b_pred')).filter(Number.isFinite), 6.6, 3.8);
report('T0 naive x/v_f', tm.map(r => tDelta(r, 'T0_pred')).filter(Number.isFinite), 7.6, null);

if (failed) { console.error('\nONE OR MORE GATES FAILED'); process.exit(1); }
console.log('\nall gates pass');
