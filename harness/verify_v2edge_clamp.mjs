// verify_v2edge_clamp.mjs — Entry 18's numerical evidence (self-contained, no ride data).
//
// Claim 1 (dead clamp): sampasimu's v2Edge descent cost is strictly positive for every
// (dist, dh, params), so its trailing max(0, e) never fires. Algebra (α = aRoll + aAero,
// ε(s) = clamp01(min(1, (α/β)/s) − 0.13), s = |dh|/d):
//   gentle  s ≤ α/β        : ε = 0.87 and β|dh| ≤ α·d  ⇒  e ≥ 0.13·α·d
//   middle  ε ∈ (0, 0.87)  : the α parts cancel exactly ⇒  e = 0.13·β·|dh|
//   steep   ε floored at 0 : e = α·d
// (k_smooth < 1 scales β down while abRatio stays un-smoothed — margins only widen.)
// This is the same bound as the app's A* admissibility proof (descFloor = 0.13·α > 0).
//
// Claim 2 (Jensen sign): grade-local per-edge ε credit ≥ the aggregate-ε_geom credit,
// because f(x) = max(0, x − 0.13) is convex on [0, 1] — so the deployed app gives MORE
// descent credit than the champion R0, never less (equality on constant grade).
//
// Run: node verify_v2edge_clamp.mjs   (exits non-zero on any violation)

const OFF = 0.13;

// Verbatim structure of sampasimu energy-worker.js v2Edge, returning the PRE-clamp value.
function v2EdgeDescentPreclamp(dist, ndh, c) {
  let eps = c.abRatio * dist / ndh;
  if (eps > 1) eps = 1;
  eps -= OFF;
  if (eps < 0) eps = 0;
  return c.aRoll * dist + c.aAero * dist - eps * c.beta * ndh;
}

function flatEqSpeed(P, m, crr, cda, rho, keff) {
  const a = crr * m * 9.81, b = 0.5 * rho * cda;
  let lo = 0, hi = 40;
  for (let i = 0; i < 80; i++) { const v = (lo + hi) / 2; ((a + b * v * v) * v < keff * P) ? lo = v : hi = v; }
  return (lo + hi) / 2;
}

function bundle(m, crr, cda, rho, keff, pFlat, kSmooth) {
  const vf = flatEqSpeed(pFlat, m, crr, cda, rho, keff);
  const mg = m * 9.81, aeroCoef = 0.5 * rho * cda * vf * vf, KJ = 1000;
  return {
    aRoll: mg * crr / keff / KJ,
    aAero: aeroCoef / keff / KJ,
    beta: mg * kSmooth / keff / KJ,           // kSmooth scales β…
    abRatio: crr + aeroCoef / mg,             // …but abRatio stays un-smoothed (as in app.js)
  };
}

let fail = 0;
const check = (ok, msg) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${msg}`); if (!ok) fail = 1; };

// ---- Claim 1: sweep. Parameters × geometry, track the global minimum pre-clamp cost.
let minPre = Infinity, minAt = null, combos = 0;
for (const m of [50, 75, 120])
  for (const crr of [0.002, 0.008, 0.02])
    for (const cda of [0.2, 0.45, 0.6])
      for (const pFlat of [40, 80, 200])
        for (const kSmooth of [0.5, 0.8, 1]) {
          const c = bundle(m, crr, cda, 1.1, 0.97, pFlat, kSmooth);
          for (let dist = 0.5; dist <= 60; dist += 0.5)
            for (let g = 0.001; g <= 5; g *= 1.15) {          // grades 0.1%–500%
              const pre = v2EdgeDescentPreclamp(dist, g * dist, c);
              combos++;
              if (pre < minPre) minPre = pre, minAt = { m, crr, cda, pFlat, kSmooth, dist, g };
            }
        }
check(minPre > 0, `dead clamp: min pre-clamp descent cost over ${combos} combos = ${minPre.toExponential(3)} kJ (> 0) at ${JSON.stringify(minAt)}`);

// Analytic floor spot-check: middle regime must equal 0.13·β·|dh| exactly.
{
  const c = bundle(75, 0.008, 0.45, 1.1, 0.97, 80, 1);
  const dist = 10, s = c.abRatio / 0.5, ndh = s * dist;       // ε = 0.5 − 0.13, middle regime
  const pre = v2EdgeDescentPreclamp(dist, ndh, c);
  check(Math.abs(pre - OFF * c.beta * ndh) < 1e-12, `middle-regime identity e = 0.13·β·|dh| (${pre.toExponential(6)})`);
}

// ---- Claim 2: Jensen. Per-edge credit ≥ aggregate credit on random descent profiles.
function credits(edges, ab) {                                  // edges: [{d, drop}]
  let per = 0, H = 0, xw = 0;
  for (const { d, drop } of edges) {
    const x = Math.min(1, ab * d / drop);                      // = min(1, (α/β)/s)
    per += Math.max(0, x - OFF) * drop;                        // app: offset+clamp per edge
    H += drop; xw += x * drop;
  }
  const agg = Math.max(0, Math.min(1, xw / H - OFF)) * H;      // champion: aggregate ε_geom
  return { per, agg };
}
let jensenOk = true, worst = 0;
let seed = 42; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
for (let t = 0; t < 20000; t++) {
  const ab = 0.005 + rnd() * 0.05;
  const n = 2 + Math.floor(rnd() * 30);
  const edges = Array.from({ length: n }, () => { const d = 1 + rnd() * 50; return { d, drop: d * (0.001 + rnd() * 1.5) }; });
  const { per, agg } = credits(edges, ab);
  if (per < agg - 1e-9) { jensenOk = false; worst = Math.min(worst, per - agg); }
}
check(jensenOk, 'Jensen: per-edge (grade-local) descent credit ≥ aggregate ε_geom credit on 20k random profiles');
{
  const edges = Array.from({ length: 10 }, () => ({ d: 10, drop: 0.4 }));  // constant grade
  const { per, agg } = credits(edges, 0.0187);
  check(Math.abs(per - agg) < 1e-9, `constant grade ⇒ equality (per ${per.toFixed(6)} = agg ${agg.toFixed(6)})`);
}

process.exit(fail);
