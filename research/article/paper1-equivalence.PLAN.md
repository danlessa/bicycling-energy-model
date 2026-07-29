# Implementation plan — Entry 45: formal equivalence testing (TOST) for paper 1's parity claims, plus an optional error-distribution disclosure

> Renumbered twice on 2026-07-29: drafted as Entry 43, which went to the D6
> European-corpus registration; then 44, which went to the S-curve refit.
> This work is now **Entry 45**.

Audience: an implementing agent (Opus/Sonnet-class) working in this repo with
Danilo. Origin: an external review round (2026-07-29) pressed two points on
`research/article/paper1-closed-form.md` — (a) "no detectable difference"
is not evidence of equivalence; a TOST would harden the parity claims, and
(b) medians + CIs hide the shape of the error distributions. Item (a) is
approved. Item (b) is **undecided — Phase D below is gated on Danilo's
explicit go; do not start it, and do not register its predictions, without
that go.** Read paper 1 fully first, then this plan.

## 0. Ground rules (non-negotiable; violating any is stop-and-ask)

- **Privacy.** Repo is public. Nothing under `data/inputs/activities/` or
  `data/results/` (ride names/dates) is ever committed. This entry needs no
  new data — it re-analyses existing per-ride harness outputs.
- **Pre-registration discipline.** The registration (Phase B) goes into the
  lab journal as **Entry 45** (next free number; check the journal top —
  entries are newest-first, headed `## <date> — Entry N: <title>`) BEFORE
  the first full run. The equivalence margin especially must be committed
  to writing before any TOST result is seen — a margin chosen after
  peeking is circular and worthless. Post-hoc additions are labelled
  "exploratory, disclosed".
- **Numbers convention.** Bootstrap: mulberry32, B = 10⁴, percentile
  method; this entry takes the **next unused seeds** (the convention so
  far: 42 for |Δ%|, 43 for signed — use 44 for the equivalence CIs and 45
  for anything Phase D needs; grep `bootstrap_ci.py` and `e39_tau_reg.py`
  to confirm none are taken). Printed numbers via
  `bicycling_energy_model.jsfmt` (`to_fixed`, ties away from zero) — never
  Python `round()`/`format()`.
- **Gates.** Every number that lands in the paper gets a gate in
  `src/harness/bootstrap_ci.py` (pattern: the `E33`/`T6` sections);
  battery green before presenting. Add a `data/results/README.md` row and
  a `research/packages/make_crates.py` registry entry (ENTRIES +
  PRODUCER), then rerun `make_crates.py`.
- **Determinism.** No wall-clock, no RNG beyond the seeded bootstrap.
- **Type annotations.** Every function fully annotated (Entry-28
  invariant, enforced by a `journal.qmd` cell).
- **Do not touch** `paper2-dem-deployment.md`, `e41_dem_route.py`, or
  anything the parallel paper-2 session owns. Paper-1 text edits happen
  only in Phase E, only where this plan says.
- Commit only when Danilo says "commit". Run harnesses with
  `/Users/danlessa/conda/bin/python` (framework python3 lacks numpy —
  though this entry should stay stdlib-only like its siblings).

## 1. Phase A — reconnaissance (read, run nothing heavy)

1. Read paper 1 and enumerate every **parity claim** — grep the paper for
   `parity`, `indistinguishable`, `no detectable difference`, `snap back
   together`, `statistical tie`. As of this writing the claims live in:
   the Abstract (Results + the §3.3 pooled numbers), §1.4/H1, §3.1
   (informed p = 0.65 and blind p = 1.00, n = 44), §3.1's third check (D2,
   p = 0.37/0.53/0.70), §3.3 (the pooled 5.6 vs 6.3 and 5.9 vs 6.2),
   §3.5.1 (Table 5 "lockstep"), §3.5.2/Table 6 (3.9 vs 4.0 pooled),
   §3.6/H1 verdict, and the Conclusion. The registered TOST set is the
   subset of these that are *median-level model-vs-simulation* claims;
   "lockstep" (bias co-movement) is NOT a TOST target — leave it.
2. Read `src/harness/bootstrap_ci.py` end to end: where the per-ride
   CSVs are loaded, how the paired sign tests are computed, and the gate
   section pattern. The TOST consumes the **same per-ride |Δ%| columns**
   the existing gates already read — no engine re-runs needed. Identify
   the exact CSV + column for each registered claim (compare.py's
   informed/blind outputs; the frozen-grid outputs behind Table 3; the
   Entry-35 regime-consistent outputs behind Table 6).
3. Read Entry 22 (the gate-battery entry) and Entry 36 (a small
   registered-check entry) as format models for Entry 45.
4. Confirm the statistic. The paper's parity language is about **medians
   of |Δ%|**. The registered TOST statistic is the **difference of
   medians under paired resampling**: resample rides (within-corpus;
   stratified for pools, matching the existing convention), compute both
   models' medians on the SAME resample, take the difference
   `d = med|Δ%|_law − med|Δ%|_sim`, collect the bootstrap distribution of
   d. Do NOT switch to the median of per-ride differences — that is a
   different estimand from the one the paper's sentences make claims
   about.

## 2. Phase B — pre-register (Entry 45, before any full run)

Write the registration with:

- **The question.** Can the paper's parity-of-medians claims be upgraded
  from "no detectable difference" to formal equivalence within a margin?
- **The method.** TOST via bootstrap CI: equivalence at level α = 0.05 is
  declared iff the **90% percentile CI** of d (Phase A.4) lies entirely
  inside [−δ, +δ]. (Two one-sided tests at 0.05 each ⇔ the 90% CI
  inside the margin — state this identity in the entry.)
- **The margin, with its justification written before any result:**
  δ = **1.0 percentage point** on median |Δ%|. Grounds (verify these
  against current Table 3 before writing them in): 1.0 pp is at or below
  every CI half-width the paper publishes for these medians, and well
  below the ≈ 3–5 pp informed→blind protocol effect (§3.1) — a
  difference smaller than δ is operationally invisible to a planner
  choosing between the law and the simulation. Register δ once, for all
  comparisons; no per-corpus margins.
- **The registered comparisons** (one row each; the Phase-A enumeration,
  expected to be): F3·ε_d vs simulation on — D1 informed, D1 blind, D2
  frozen (disclose ε_f in-sample context), D3, D4, D5 frozen, D3+D4 pool,
  D3–D5 pool (both stratified), and the Table 6 regime-consistent D3+D4 /
  pooled rows (3.9 vs 4.0). F4 vs simulation only where the paper
  currently makes an F4 parity claim (D2; the blind cluster) —
  everything else F4 is exploratory-disclosed.
- **Predictions with failure modes:**
  - P1: the large-n pooled rows (n = 660, n = 1,281; Table 3 and Table 6)
    pass TOST at δ = 1.0.
  - P2: D1 (n = 44), informed and blind, is **inconclusive** (CI wider
    than the margin) — predicted, honest, and the paper's existing
    "equivalence not formally tested at n = 44" sentence then becomes
    "TOST inconclusive at n = 44", which is the same fact with a
    measurement attached.
  - P3: per-corpus mid-size rows (D3, D4, D5) — no strong prediction;
    whichever way they land is reported.
  - Failure mode: if a pooled row FAILS (CI outside the margin on one
    side), the paper's parity language for that row must be *weakened*,
    not defended — say so in the registration.
- **What is NOT registered:** no new physics, no re-fits, no per-ride
  difference estimands, no Phase D content unless Danilo has said go.

## 3. Phase C — instrument and run

- New harness `src/harness/e45_equiv.py`, stdlib-only, importing the CSV
  locations/loaders it needs (reuse `bootstrap_ci.py`'s loading helpers
  if importable; do not duplicate parsing logic — refactor a shared
  helper into the package or import from the harness if it is
  import-safe, else lift minimally with a comment).
- Output: `data/results/e45_equiv.csv` — one row per registered
  comparison: corpus, n, med_law, med_sim, d, CI90_lo, CI90_hi, margin,
  verdict ∈ {equivalent, inconclusive, fail-low, fail-high}; plus a
  console scoreboard.
- Smoke mode `E45_SMOKE=1` (B = 200) for iteration; full run B = 10⁴.
- Gates: add an `E45` section to `bootstrap_ci.py` asserting every
  registered row's d, CI and verdict; battery green.
- Crates: README row, `make_crates.py` ENTRIES/PRODUCER, rerun.

## 4. Phase D — OPTIONAL: error-distribution disclosure (GATED — needs Danilo's explicit go)

Do not start without the go. If green-lit, register it as an amendment
inside Entry 45 (labelled, dated) before running:

- Per registered comparison, disclose the shape of the per-ride Δ%
  distribution: quantiles (5/25/50/75/95), a skew statistic
  (median-vs-mean gap or Bowley skew — pick one, register it), and tail
  counts beyond ±20%.
- Deliverable options (Danilo picks): a compact table in the paper's
  appendix, OR a figure (per-corpus Δ% violin/ECDF) added to
  `research/article/figs/make_figures.py` (NOTE: it hardcodes headline
  medians — do not disturb them), OR journal-only (nothing in the paper).
- The case AGAINST (present it to Danilo fairly): the paper already
  reports signed medians + CIs everywhere (the accuracy+bias rule), which
  carries the first-order asymmetry; a shape table adds audit value but
  also length to an already dense paper.

## 5. Phase E — paper text (only after gates are green)

- Where TOST **passes**: upgrade the sentence — e.g. §3.3's pooled claim
  gains "formally equivalent within ±1.0 pp (TOST, 90% CI [a, b] ⊂
  [−1, +1]; lab journal, Entry 45)". Keep the existing sign-test
  reporting; TOST supplements, it does not replace.
- Where TOST is **inconclusive** (expected: D1): amend "equivalence is
  not formally tested" → "a registered equivalence test is inconclusive
  at this n (TOST 90% CI [a, b] vs ±1.0 pp; Entry 45)" in §3.1 and the
  H1 verdict line (§1.4 hypothesis wording itself does not change).
- Where it **fails**: weaken the parity language per the registration.
- Methods: add 2–3 sentences to §2.3.4 (Evaluation protocol) defining the
  TOST (margin, its justification, the 90%-CI identity, seeds). Mind the
  style rules: ≤ 200-word paragraphs, ≤ 5 paragraphs per header, cite
  equations by number, F1–F4 naming.
- Update every number-bearing surface the CLAUDE.md checklist names IF
  any published number changes (none should — TOST adds numbers, moves
  none). New numbers still propagate to: journal Entry 45,
  `CURATED_JOURNAL.md`, `journal.qmd` (prose + a runnable cell),
  `claims.ttl` (+ regenerate `claims-explorer.html` via
  `research/scripts/make_claims_explorer.py`), crates.
- Run the paper audits before presenting: paragraph word counts, per-
  header group sizes, link check, `\tag` inventory.

## 6. Phase F — verification checklist (all must pass before presenting)

1. `/Users/danlessa/conda/bin/python src/harness/bootstrap_ci.py` →
   all gates pass, including the new E43 section.
2. `e45_equiv.py` full run deterministic (re-run → identical CSV).
3. `make_crates.py` green.
4. Paper audits green; bilingual parity N/A (paper 1 is EN-only).
5. `git status` shows no private files staged. No commit without the word.

## 7. Decisions reserved for Danilo (ask, don't assume)

- The Phase D go/no-go, and if go, which deliverable form (table /
  figure / journal-only).
- Any change to the registered margin after seeing results (that is a
  disclosed deviation, new registration paragraph).
- Whether the Abstract's parity sentences also carry the TOST result or
  stay as-is with the body carrying it.
- Committing.

## 8. Known traps

- **Margin-after-peek.** If any TOST CI is computed before Entry 45's
  margin paragraph exists in the journal, stop, disclose, and treat the
  margin as compromised — pick it fresh only with Danilo.
- Difference-of-medians ≠ median-of-differences (Phase A.4) — the
  paper's claims are about the former.
- Stratified resampling for pooled rows must match the existing pooled-CI
  convention exactly (rides within corpus, then pool) or the TOST CI is
  not comparable to the published brackets.
- Populations: use exactly the ride sets behind the published medians
  (clean-corpus filters); any mismatch invalidates the comparison —
  the Entry-31/33 population-parity lesson.
- Seeds: never reuse 42/43; a reused seed silently correlates the
  equivalence CI with the published CIs.
- D2's ε_f rows are in-sample (selected on D2) — any D2 TOST verdict
  carries that caveat verbatim.
