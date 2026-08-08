# bicycling-energy-model

A standalone, **build-step-free** study tool comparing two models of the
mechanical energy (and time) of pedalling a route: an **approximate** closed-form
law and a **canonical** forward-dynamics simulation — run on the *same* physical
constants so the difference isolates the modelling simplifications, not the
parameters. One self-contained HTML file; the derivations live in
`research/notes/original_notes.md` (the original notes doc — still the spec for
the closed form: a model change lands there and in the code together).

Part of the Pedal Hidrográfico research. The energy law is shared with
`sampasimu` (Simujaules `energy-worker.js`) and `quilojaules`; this repo is the
home of the *derivation* and the side-by-side comparison.

## Layout

- `applet/index.html` — the **entire app**: canvas UI, both engines, the GPX and
  binary-FIT parsers, hardcoded Portuguese strings. **No dependencies, no
  bundler, no `package.json`** — open it directly in a browser. Deliberately
  standalone vanilla JS: it duplicates the Python engines by design (see
  "Verifying a change").
- `src/bicycling_energy_model/` — **the single Python implementation** of the
  engines/parsers (`engines.py`, `fit.py`, `profiles.py`, `regime.py`,
  `ride.py`, `jsfmt.py`). Everything else imports from here; there are no other
  Python copies. `jsfmt.py` is stdlib-`decimal` number formatting that keeps the
  rounding conventions the published tables were produced under (`to_fixed`
  rounds ties away from zero — Python's `format`/`round` are half-even; never
  use them for a printed number).
- `src/harness/` — the validation harnesses, **all Python, stdlib-only**
  (committable; inputs in `data/inputs/`, outputs in `data/results/` — both
  gitignored). They import the engines/parsers and `G` from
  `bicycling_energy_model`: `compare.py` (44 longões power rides),
  `censo_compare.py` (62 censo urban rides), `eps_hypothesis.py` (ε closed-form
  test), `eps_sp_test.py` (São Paulo ε), `ppaz_inventory.py` + `ppaz_compare.py`
  (441 second-rider rides: implied-mass inversion + frozen-ε transfer;
  `PPAZ_M=<kg>` env), `jaam_inventory.py` + `jaam_compare.py` (219 third-rider
  rides — Entry 14; `JAAM_M`), `danlessa_inventory.py` + `danlessa_compare.py`
  (the author's full export, Entry 16), `skc_compare.py` (Entry 43 — **D6**, the
  first non-Brazilian corpus: four European riders from the open scikit-cycling
  deposit; self-contained, it walks the corpus dir so there is no inventory step;
  `SKC_SMOKE=1`, `SKC_M`/`SKC_CDA`/`SKC_CRR`), `time_compare.py` (the time model
  `x*=x+k₊h₊−k₋h₋` — Entry 13), `cda_estimate.py` + `param_fit.py` (independent
  per-rider CdA/C_rr/mass + wind — Entry 15; `param_fit.py`'s `pts_with_geo`
  keeps lat/lon, the one point-builder that is NOT the shared `pts_from_fit`),
  `regime_compare.py` (Entry 17; `SANITY=1` for synthetic gates; hosts
  `r1d_v2_edge`, the deployed-v2Edge Python reference), `igc_resolution_test.py`
  (Entry 19), `goal_calibration.py` + `goal_smooth_rasters.py` (Entry 20;
  `GOAL_SMOKE=1`), `scale_trio.py` (Entry 21; `SCALE_SMOKE=1`; carries the
  Entry-20 anchor constants — refresh them whenever Entry 20 re-runs),
  `e48_equiv.py` (Entry 48 — TOST equivalence on the difference of
  medians under paired stratified resampling, margin ±1.0 pp, **seed 44**;
  `E48_SMOKE=1`. Seeds 42/43 are the published |Δ%| and signed CIs — never
  reuse one here), `e46_switch.py` (Entry 46 — §3.3's regime switch, four arms
  {constant, grade-inverse} × {unswitched, switched}, scored under both parameter
  classes. A **second-order** harness: it reads `e47_formselect.csv`'s per-ride
  E(ε=0)/E(ε=1) pair rather than re-parsing tracks, which is exact because
  `approximate` is linear in ε — so Entries 46 and 47 share a population by
  construction),
  **the Entry 52–61 chain, now paper 1's spine**: `e52_build.py` (walks D3–D6
  once and caches per-form energy components at every τ on a grid, so all
  downstream fitting is exact arithmetic — `E52_AERO=seg|reg`,
  `E52_FALLBACK=prior|rider`, defaults `reg`/`rider`; ~12 min, the only expensive
  step) → `e52_split.py` (A.1–A.8: random 15% hold-out, repeated stratified
  k-fold with **every** parameter refitted in-fold, CV binding with AIC reported,
  one test scoring; `e52_summary.csv` is what the gates read) ·
  `e54_transfer.py` (leave-one-rider-out) · `e56_struct.py` (τ and c
  sensitivity) · `e57_rider_fallback.py` (per-rider medians replacing the global
  priors) · `e58_intervals.py` (bootstrap CIs on fitted parameters + the
  50%-loss breaking points; numpy) · `e59_pooling.py` (ride- vs rider-weighted
  objectives — rider-weighting REFUTED) · `e60_regional.py` (per-landscape ε
  pools) · `e61_sweep.py` (synthetic sweep over real geometries; `E61_FULL=1`
  sweeps all 729 combinations in ~5.5 h and dumps `e61_raw.full.csv`, 145,800
  rows of raw simulation, so any re-fit is arithmetic) · `e53_linear_invert.py`
  (joint linear inversion — REFUTED, kept as the negative result),
  `e47_formselect.py` (Entry 47 — deficit-form selection by BIC under a Laplace
  likelihood, on D1∪D2 under two parameter arms, plus the labelled in-sample
  D3–D6 arm; `E47_SMOKE=1`. Hosts `invert_physics`, extracted from
  `perride_invert.run_ride` so the per-ride inversion has exactly one copy),
  `e63_f5_kebuffer.py` (Entry 63 — **F5**, the KE-buffer valley toll replacing
  the deadband's fitted τ with a per-valley physics-computed cap
  `min(D, H, h_KE − 2τ_n)`; runs Entry 52's A-chain verbatim on the E52 cache +
  seed-48 split, so its F3/F4 rows must reproduce `e52_split.csv` to the digit —
  that reproduction is the drift check. Per-ride toll sums cached on a 12-arm
  v_b grid in `e63_tolls.csv`, downstream refits arithmetic; internal gate
  F5(v_b=0) ≡ F3(τ_n) at 0 kJ. `E63_SMOKE=1`, `E63_TAUN=2.0` — env-suffixed
  sensitivity arm, `E63_DECOMP=1` pinned-τ control only, `E63_REBUILD=1`.
  Verdict: F5(τ_n=2) enters F3's 1-SE band; both arms rail v_b at ∞ — the cap
  doesn't bind at these corpora's grades. Entry 64 (same file): **F5f** (v_b
  frozen at never-brake, 1 parameter) WINS the A.5 selection under the 1-SE
  rule; **F5m** (v_b measured per ride — 95th-pct descent speed, `toll_vbm`)
  transfers better than F3 in the E54-style LORO contest (`E63_LORO=1`,
  p = 0.044, seed 54); the per-rider τ* ordering prediction FAILS
  (`E63_TAUPRED=1`, ρ ≈ 0.06) — magnitude right, ordering bias-contaminated.
  AIC still prefers F3, stated per the Entry-49 precedent. The E64 amendment's
  filterless arm (`E63_TAUN=0.0`) shows toll-alone recovers 53% of the F2→F3
  gap vs filter-alone 76% and both 82% — ~46 pp shared, so filter and toll are
  mostly the same term, but the deadband is NOT redundant: without it F5f
  leaves the 1-SE band and the LORO significance dissolves. Entry 65 (same
  file, modes `E63_RAINFLOW=1` and `E63_SMOOTH=<σ>`): both rival fragmentation
  fixes FAIL — rainflow over-tolls (39%, the one arm where v_b left the rail,
  fitting 32 km/h) and σ=15 smoothing is inert alone (0%) adding 2 pp with the
  toll — so the deadband's unique ~25 pp was re-attributed to amplitude-bounded
  long-wavelength elevation error (baro drift), which only amplitude-threshold
  removal touches; the filterless program is closed, F5f(τ_n=2) stays best),
  `e66_driftprobe.py` (Entry 66 — the closure-pair drift probe, no DTM:
  same-place different-time pairs measure each ride's baro drift internally
  (median 2.8 m, 3.4 m/h, 82% coverage). Entry 65's strong attribution
  REFUTED: the deadband's τ6-over-τ2 benefit is drift-blind (ρ ≈ 0,
  n = 1,413) — the unique share re-read as a fitted misfit absorber, not
  measurement-error removal; S2 (drift correction) deferred with a registered
  predicted-null. `E66_SMOKE=1`, `E66_REBUILD=1`. NB its record loader is a
  local copy because **`param_fit.py` is NOT import-safe** — importing it
  runs Entry 15 and rewrites `param_fit.csv`),
  `e67_residual.py` (Entry 67 — the residual decomposed, B+C: the coupling
  that lets τ=6 win is weak everywhere (pooled ρ ≈ 0.08, within ≈ 0.08,
  between ≈ −0.03 — neither the physics nor the absorber fingerprint), τ* is
  non-stationary (moved in 5/6 riders early→late) and F3's early-half
  constants age ~4.7× worse than F5f's on the same rider's later rides —
  the deadband's unique share carries ≈ zero transferable physics; F5f's
  ε+toll are stationary. Train half only; `E67_SMOKE=1`; pins `E63_TAUN=2.0`
  before importing the e63 module. Entry 68 (`E63_F5FCV=1`, the light
  τ_n-sweep mode in `e63_f5_kebuffer.py`): F5f's CV declines MONOTONICALLY in
  τ_n to the F3 anchor (F5f(6) ≡ F3(6) at 0.05405) with the toll margin
  decaying 0.0047→0 — the floor is load-bearing, so F5f's one-parameter claim
  needs an external pin; the registered pin is E66's measured drift amplitude
  (median 2.8 m), making τ_n telemetry, per corpus, not a chosen constant),
  `e69_frontier.py` (Entry 69 — the frontier COLLAPSES: keepability is flat
  in the floor (aging ~0.0006 at τ_n = 2/3/4.5 vs F3's 0.0030), so F3's
  non-keepable share is the τ REFIT, not the removal size. **F5p** — floor
  pinned per corpus by measured drift from `e66_drift.csv`, v_b frozen, ε the
  only fitted parameter — matches F3's CV (0.05413 vs 0.05406) and posts the
  program's best rider transfer (−0.27 pp vs F3, p = 0.0001). Pins read from
  the producing CSV, never hardcoded; F3's CV read from the chain CSV; the
  flat-basin law named: E39/E50/E51/E67-69 are the same principle. `E69_SMOKE=1`),
  `bootstrap_ci.py` (**the gate script**; exits non-zero on failure). **Narrowed
  2026-07-31 to only what the papers still claim** — 22 sections became 7, and a
  full run is 4.5 min instead of 15. Surviving sections are keyed to
  `pc:gateSection` in the article sidecars, and `check_paper_stats.py` asserts
  the correspondence both ways: `1` corpus populations · `3i` elevation
  substitution (paper 2) · `3p` Sobol shares (E50) · `3q` the A-chain (E52/55/57)
  · `3r` rider transfer (E54) · `3s` structural sensitivity (E56) · `3t` regional
  pools (E60). Sections for retired results were deleted with the prose they
  served — a gate on a number nobody publishes is a slow test that fails for
  reasons no reader sees,
  `longoes_frozen.py` (Entry 31; D1 under the frozen
  shared-constants protocol — the blind half of the paper's Table 2; the
  informed half stays `compare.py`), `param_sweep.py` (Entry 29; the pre-registered CdA × Crr × ρ sensitivity
  sweep on D2–D5 — per-ride aggregates once, every combination arithmetic;
  exact order-statistic CIs, a gate-checked deviation from the bootstrap
  convention; `SWEEP_SMOKE=1`, `SWEEP_FREEZE_M=1`; self-gates anchor m̂ and
  all 16 anchor medians on every full run), the Entry-26 scripts
  (`e26_pairs.py`, `e26_portal_profiles.py`, `e26_detour.py`), plus
  `fetch*.py` / `build_model_inputs.py` / `verify.py` and `dem/`
  (`dem/coords/` is gitignored — per-ride GPS).
  The `*_compare.py` take `<RIDER>_M`/`_CDA`/`_CRR` env overrides (Entry 16's
  fitted-vs-assumed machinery); every harness that reads one **suffixes its own
  output CSV** with the active override (`bem.env_suffix`, e.g.
  `ppaz_comparison.PPAZ_M78.csv`) instead of overwriting the canonical file a
  sweep must never touch — a sensitivity run and a real result cannot collide.
  **`regime_compare.py`, `igc_resolution_test.py`
  and `goal_calibration.py` are import-safe** (driver under
  `if __name__ == "__main__"`): the DEM chain imports them (`igc` ← `regime`;
  `goal` ← `regime`+`igc`; `scale_trio` ← all three) — keep them importable.
  **A smoke flag must never write the canonical CSV** — `INVERT_SMOKE=1` did
  until Entry 47 caught it by overwriting `perride_invert.csv` (1,409 rows → 204,
  silently breaking Tables 5–6 and the gate battery); smoke runs now suffix
  `.SMOKE`, as `skc_compare.py` and `e47_formselect.py` already did.
  Every FIT/GPX parse goes through `bicycling_energy_model.load_pts`, which
  caches the parsed points on disk under `data/results/cache/` keyed on
  (path, size, mtime, a schema version) — repeat runs and sensitivity sweeps
  skip the parse entirely; delete the directory to force a re-parse, and bump
  `ride.py`'s `_CACHE_SCHEMA` if a point's fields ever change (a stale cache
  entry is a silent correctness bug, not a crash). `goal_calibration.py` and
  `scale_trio.py` each re-run their whole analysis twice to prove determinism
  (Entries 20–21's gates); `FAST=1` skips that second run and the cache-subset
  rebuild during iteration — same result, just without the ×2 proof, so don't
  use it for a number that ships.
- `research/journal/` — `MODEL_COMPARISON_JOURNAL.md` (numbered entries, newest
  first — the **lab journal**, authoritative), `CURATED_JOURNAL.md` (the
  readable retelling, oldest first — update it when a lab entry lands; on
  disagreement the lab journal wins), `journal.qmd` (executable Quarto mirror;
  its python cells must carry the CURRENT constants — a stale literal in a
  runnable cell demonstrates the wrong model).
- `research/notes/` — `original_notes.md` (the derivations: the energy law and
  its `α, β, ε`; the coasting deficit ε₀; the climb-aero correction; the time
  model and the `ε ↔ k₋` bridge), `epsilon-origin.md` (how ε and the F1–F5
  ladder fall out of the canonical dynamics — branch fixed points, the recovery
  length, the KE buffer; the derivation note behind Entries 63–64),
  `claims.ttl` (machine-readable
  claims–questions–evidence graph, widely-used vocabularies only — schema.org
  Claim/Question, CiTO, PROV-O/P-Plan, Dublin Core; validate with `rdflib`
  after editing), `claims-explorer.html` (generated — regenerate via
  `research/scripts/make_claims_explorer.py`, never hand-edit),
  `data-graph.ttl` (the **evaluation-lineage DAG** in the I/T/O/S notation:
  corpora D, parameter classes P, transformers F, per-ride outputs O and the
  published statistics T derived from them — every `:cardinality` on an output
  is *counted from its CSV*, never asserted, because `|O| ≤ |D|` and reading a
  corpus size as a result population is the error it exists to catch; validate
  with `rdflib`),
  `paper1-adversarial-review.md` (the 2026-07-30 multi-agent adversarial pass:
  6 major + 13 minor findings, each tagged ✅ independently verified or ⚠️ not —
  **none applied yet**; M2, the unreported D6 reversal in Table 6, is the one to
  fix first), `literature-context.md`, `simujaules-literature-context.md`,
  `crr-cda-typical-values.md`, `dem-elevation-comparison.md`,
  `ascent-error-literature.md`, `censo-model-verification.md`,
  `VERIFICATION_NOTES.md`.
- `research/scripts/` — `make_claims_explorer.py` (claims.ttl → the interactive
  explorer page), `check_paper_stats.py` (cross-checks each article's claim
  annotations against `bootstrap_ci.py`. A published statistic carries an
  invisible anchor `<!--@c-<id>-->` at the number in the `.md`; its metadata
  lives in a **sidecar `<paper>.meta.ttl`** — kept out of prose humans are about
  to rewrite, rdflib-validated like every other `.ttl`, and it survives the draft
  moving to a format where an HTML comment would not. Written in the existing
  vocabulary so the sidecars, `claims.ttl` and `data-graph.ttl` load as one
  graph: a claim does `cito:citesAsEvidence dg:o_…` and `prov:wasDerivedFrom
  claims:assert…`, which is the article-claim → entry direction the journal
  deliverable needs. The check asserts anchors ↔ claims both ways, that
  `pc:value` is genuinely asserted in the gate section `pc:gateSection` names,
  and that `dcterms:type` is a known scope — `planned` claims are reported, not
  failed. Exits non-zero.)
- `research/packages/` — per-entry evidence RO-Crates; regenerate via
  `make_crates.py` (re-executes `bootstrap_ci.py` and aborts on gate failure).
  RO-Crate envelope at the repo root `ro-crate-metadata.json`.
- `research/article/` — the papers and pieces: `paper1-closed-form.md` (the
  IMRAD paper — EN only, no pt-BR mirror planned), `paper2-dem-deployment.md` (scaffold: letter — the
  law on planner/DEM profiles; consumes paper 1 only),
  `paper3-edge-cost.md` (scaffold: the edge-cost discretization paper;
  cites paper 2's scale prescription), the older monoliths `article-draft.md` +
  `article-draft.pt-BR.md` (canonical citation target) and the piece series
  (`piece1-energy-demand{,.pt-BR}.md`; Pieces 2–3 pending). **A piece edit and
  its pt-BR mirror move in lockstep** — run a bilingual parity diff before
  committing. `figs/` (`make_figures.py` — NOTE: it hardcodes the headline
  medians; a re-baselined number must be updated there too), `modelo-assets/` +
  `build-modelo.sh` (builds the published `/modelo/` pages into the sibling
  simujaules repo).
- `data/inputs/` — `sample.gpx` and `flecha_power.csv` committed; everything
  else is **gitignored and private** (`activities/{rwgps,strava,
  censohidrografico,strava_ppaz,strava_jaam,strava_danlessa,scikit_cycling}/`,
  `longoes.xlsx`,
  `censo-hidrografico.xlsx`, any `*.fit`). `longoes.xlsx` was purged from
  history (2026-07) — never re-add it. `strava_ppaz/`/`strava_jaam/` are
  independent riders' exports shared with consent; never commit any of it.
  `scikit_cycling/` is the **openly licensed** D6 deposit (CC BY 4.0) — but its
  tracks start at the riders' home addresses, so it is gitignored like the rest
  and no derived geometry is published; cite the DOI instead.
- `data/results/` — harness outputs (gitignored except the README, which maps
  file → producer → journal entry). Every file regenerates with one harness
  command.
- `mission-model/` — the repo's **mission** in SysML v2 / Mission Engineering
  terms (`00-mission` → `08-publication-roadmap`, read in order; 08 ends with the assistance/credit governance section): the effect chain,
  the four stakeholder classes, capabilities vs the systems delivering them, and
  MOPs vs MOEs. Plain text, compiled by nothing (no-build rule). Descriptive, not
  aspirational — it records that `MOE-5` (adoption in practice) is uninstrumented
  and that `cDeploy` is the thinnest capability. `05-deliverables` holds the article chain A1→A2→A3 (A4, the time dual, deferred on evidential grounds — Entry 13's descent bridge fails) and names A3 as the mission's binding constraint. Changes on a *paper* landing or a
  stakeholder shift, never on a re-baselined number.
- **Assistance policy** (`mission-model/08`, governance section): LLM assistance is for the **research
  phase** and for **deploying research infrastructure**. Once an article's content
  and results are frozen, the draft is written and diagrammed **entirely by
  humans** — the last machine-produced artefact in an article's chain is the
  pre-draft body handed over at that freeze. The principle: assisted where the
  output is machine-checkable, human where it is a claim on a reader's attention.
  The exception is the journal, the repos and their graphs, where machines are an
  expected primary reader.
- `README.md` — user-facing overview.

## The two models

- **Approximate** (closed form): `E ≈ α·x + β·(h₊ − ε·h₋)`, with
  `α = (C_rr·mg + ½ρCdA·(v_f+wind)²)/k_eff`, `β = mg/k_eff`. `ε ∈ [0,1]` lumps
  descent recovery; `v_f` is the flat reference speed. Geometry-only estimator
  `ε ≈ clamp₀₁(ε_coast − ε₀)` with the **coasting deficit** `ε₀ = 0.13`.
- **Canonical** (forward dynamics): distance-marching force balance
  `m·dv/ds = k_eff·P/v − C_rr·mg·cosθ − ½ρCdA·(v+wind)² − mg·sinθ`, per-regime
  pedal power, safe-speed (`v_max`) brake cap on descents. Returns leg energy
  `∫P·dt`, time, the wheel-work breakdown, and the speed profile.

The app also shows **v2Edge** — the per-edge realisation Simujaules deploys
(grade-local `ε(s) = clamp01(min(1, (α/β)/s) − ε₀)`, aero gated off climbs,
`k_s` scaling β only, dead `max(0,·)` clamp — Entries 18–21). The Python
reference is `regime_compare.py`'s `r1d_v2_edge`; the applet and sampasimu's
`energy-worker.js` are its hand-kept mirrors — a change to any copy lands in
all.

**Design principle — both models read the same physical constants** (`m, C_rr,
CdA, ρ, k_eff, wind`). Never let the two engines diverge on a constant.

**Gravity is `G = 9.7864`** — São Paulo's local value (IAG-USP absolute
gravimetry): every corpus here is ridden in the SP metropolitan region. It
lives in **one Python place** — `src/bicycling_energy_model/engines.py` — and
everything else (harnesses, `journal.qmd`) imports it from there. The only
other copy is deliberate: `applet/index.html`, the standalone JS mirror. Two
sites keep **9.81 on purpose** because they mirror the cost bundle *sampasimu
deployed pre-v63*: `verify_v2edge_clamp.py` and `e26_detour.py`'s `G_JS`
(cross-engine ratios must hold the engine's own constant). A number that
depends on masses inverted from ride data moves with G (`m̂ · g` is the
invariant) —
**never freeze an implied mass in a harness constant**: that is the Entry-27
mass-bug lesson; the implied masses in `regime_compare.py`'s `PHYS` and
`time_compare.py` must be refreshed whenever G or the inversion changes.

## Invariants — easy to break, hard to notice

- **A HELD parameter can invert a conclusion, not just add noise.** Three bugs of
  this shape landed in one session, each in code already producing published
  numbers: `e54_transfer` fitted at `TAU_PUB_I` (2 m) while the selected form
  used 6 m, inflating every per-rider optimum and manufacturing a spurious case
  for rider-weighted pooling; `e61_sweep` pinned F4's `c` at the published
  3.0 m/km, flipping its regional gap negative and supporting a "the split is
  F3-specific" reading that was wrong; and `e54`'s pooled comparator was a
  hardcoded 0.2879 that went stale the moment the aero estimator changed.
  **When a harness needs a fitted constant, read it from the producing CSV —
  never a literal.**
- **Never memoise on `id()`.** The sensitivity analyses build throwaway per-ride
  dicts with one perturbed component; CPython recycles their ids, so a cache
  keyed that way answers for the wrong row. It made every breaking point in
  `e58_intervals` read exactly 1.00×.
- **A loss must not change its population with the parameter.** `logratio` used
  to skip rides whose predicted energy went non-positive, and since E(ε) falls
  with ε that rewarded the optimiser for making badly-fitting rides vanish. The
  population is fixed once across the whole search range.

- **Canonical conserves energy; leg energy ≥ work done.** The identity
  `k_eff·legE = ΔKE + W_rr + W_aero + W_grav + W_brake` must hold, so on a climb
  `legE ≥ mg·h₊/k_eff`. Enforced by the **semi-implicit** KE update — a
  safeguarded Newton on `g(u)=u−A/√u−B`. Do **not** reintroduce a `VMIN`/KE
  floor: it injects energy and yields `legE < PE` on underpowered steep climbs.
- **Flat-match anchor.** On flat ground canonical ≈ approximate **iff** `v_f`
  equals `flatEqSpeed(P_flat)` (what *auto v_f* sets). `flat_eq_speed` is a
  bisection — keep it dependency-free (a NumPy import here once broke
  stdlib-only).
- **Descent split — don't double-count.** Descent aero is paid by gravity and
  already sits in `(1−ε)·β·h₋`. The climb-aero correction touches only climb
  segments (`slope ≥ climbThr`); rolling stays on all `x`, descents untouched.
- **`ε`-from-FIT uses the MEASURED flat speed**, not `flatEqSpeed` — otherwise
  a parameter mismatch inflates `α` and lies about `ε`. Deliberate.
- **Decomposition consistency.** `a.roll + a.aero + a.climb + a.recov === a.E`,
  and the `ε*`-match and clamp paths read those (corrected) components.
- **FIT parser** (one copy: `bicycling_energy_model/fit.py`). Honors
  per-definition endianness, compressed-timestamp headers, developer fields,
  FIT invalid markers; `record` is global message 20; near-duplicate points
  (`Δdist < 0.5 m`) are dropped. Optional `meta` dict collects file-level
  manufacturer (260 = Zwift ⇒ virtual) and sport. Regime power is speed-gated
  (`< 0.5 km/h`) and time-weighted.
- **Units.** Internals SI (N, J, m/s); display converts (kJ, km/h). `ε` and the
  grade thresholds are entered as **percent** and divided by 100.

## Conventions

- **UI strings in Portuguese; code identifiers and comments in English.**
- **No build, no deps.** The applet is vanilla JS in one file; the Python is
  stdlib-only. If a JS library ever becomes necessary, CDN + SRI, not a bundler.
- **Privacy:** never commit a raw `.fit` (GPS track) or anything under
  `data/inputs/activities/` — the repo is **public**
  (`origin` → `github.com/danlessa/bicycling-energy-model`). `data/results/`
  CSVs carry ride names/dates — also gitignored. Request geometry sent to third
  parties (e.g. Overpass) must never derive from ride endpoints.
- **Commits:** only when asked.

## Verifying a change

No build, no CI. The binding checks (V8-exactness and the JS parity harness
were retired in the 2026-07 re-baseline; git history has them):

- **Load `applet/index.html` in a browser** (or headless Chrome `--dump-dom`) —
  surfaces JS errors and shows the result.
- **Engine or parser change → it lands in TWO places**: the Python package
  (`src/bicycling_energy_model/`) and the applet. That is the only remaining
  duplication, and it is deliberate. For v2Edge, the deployed-cost mirror set is
  `r1d_v2_edge` (Python) + the applet + sampasimu's `energy-worker.js`.
- **Paper 1's chain, in order**, after any engine or physics change:
  `e52_build.py` → `e52_split.py` → `e57_rider_fallback.py` → `e52_build.py`
  **again** (the rider fallbacks feed back into the cache) → `e54`/`e56`/`e58`/`e60`.
  Then `bootstrap_ci.py` and `research/scripts/check_paper_stats.py`.
- **Run the harnesses** (need the local gitignored tracks; scripts resolve
  paths relative to their own location — run from anywhere):
  `python3 src/harness/compare.py` prints the longões scoreboard **and** the
  conservation residual (must stay ≤ 1e-6); then `censo_compare.py`,
  `eps_hypothesis.py`, `eps_sp_test.py`, `ppaz_compare.py`, `time_compare.py`,
  and **`python3 src/harness/bootstrap_ci.py`** — the gate battery for every
  published median; exits non-zero on failure. **A full run costs 10–15 minutes and
  ALL of it is the ~40 bootstrap CIs** (every median, count and ordering gate
  together takes 2 s), so it is run only when the maintainer asks for it. Two
  levers for iteration, both of which print a NON-AUTHORITATIVE banner:
  `GATES=3o,3n` computes intervals only in the named sections — elsewhere the CI
  checks report `CI-SKIP` while the median gates still run and still fail — and
  `GATE_B=200` lowers the resample count everywhere. `GATES=<your section>` is
  ~2 s. Sections are never skipped wholesale: later ones reuse CSVs parsed by
  earlier ones, so only the expensive part is skipped. `SANITY=1 regime_compare.py`
  runs the synthetic gates; the DEM chain (`igc_resolution_test`,
  `goal_calibration`, `scale_trio`) carries its own sanity-gate blocks — read
  the per-gate lines, not just the exit code (two documented-benign failures:
  goal's large-σ h₊ monotonicity on one ride; scale's exactly-zero degenerate
  grid corner).
- **A doc-visible number that moves must be updated everywhere it is
  restated.** The known number-bearing surface for a headline median:
  the two article monoliths + the two Piece-1 files (EN/pt-BR ×2),
  `research/journal/MODEL_COMPARISON_JOURNAL.md` (new entry; old entries keep
  their as-written values), `CURATED_JOURNAL.md`, `journal.qmd` (prose AND
  code literals), `research/notes/claims.ttl` (+ regenerate
  `research/packages/` and `claims-explorer.html`), `figs/make_figures.py`,
  the applet's presets/tooltips/comments, `original_notes.md`, `README.md`,
  and the harness anchor constants (`scale_trio.py`'s Entry-20 anchors,
  `bootstrap_ci.py` expectations). Run a bilingual parity diff on the article
  pair before committing.
- **Python that must match a published number:** use
  `bicycling_energy_model.jsfmt` (`to_fixed`/`js_str`) — JS-convention
  rounding; never Python's `round()`/`format()` for printed values.
- **Sanity cases** for an engine change: flat (canonical ≈ approximate at auto
  v_f), pure climb (`legE ≥ PE`), pure descent (≈ coast), and P=0 (the bike
  must *stall*, not gain energy — no KE floor).
