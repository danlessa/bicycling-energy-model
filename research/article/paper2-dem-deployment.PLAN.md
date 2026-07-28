# Implementation plan — paper 2 (`paper2-dem-deployment.md`), the DEM-deployment letter

Audience: an implementing agent (Opus/Sonnet-class) working in this repo with
Danilo. Goal: turn the scaffold `paper2-dem-deployment.md` into a finished
letter, running its one registered experiment first. Paper 1
(`paper1-closed-form.md`) is the source of every constant, convention and
cross-reference — read it before anything else, then this plan, then the
scaffold.

## 0. Ground rules (non-negotiable; violating any of these is a stop-and-ask)

- **Privacy.** The repo is public. Never commit anything under
  `data/inputs/activities/`, `data/results/` (CSVs carry ride names/dates),
  or `src/harness/dem/coords/` (per-ride GPS). Never send geometry derived
  from rides to third parties. The DEM rasters are already local — no
  fetching keyed on ride coordinates.
- **Pre-registration discipline.** The experiment's protocol, estimands,
  predictions and failure modes go into a new lab-journal entry (next free
  number; Entry 41 unless taken) BEFORE the first full run. Post-hoc
  additions must be labelled "exploratory, disclosed".
- **Numbers convention.** Every published statistic = median |Δ%| AND median
  signed Δ% (accuracy and bias together), each with a 95% CI. Bootstrap:
  mulberry32, seeds 42 (|Δ%|) / 43 (signed), B = 10⁴, percentile method —
  copy the helper from `src/harness/e39_tau_reg.py`. Printed numbers use
  `bicycling_energy_model.jsfmt` (`to_fixed` — ties away from zero); never
  Python `round()`/`format()`.
- **Gates.** Every number that appears in the letter gets a gate in
  `src/harness/bootstrap_ci.py` (pattern: the `E33`/`T6` sections). The
  battery must exit green before any result is presented. Add a
  `data/results/README.md` row and a `research/packages/make_crates.py`
  registry entry (ENTRIES + PRODUCER) for the new entry, then rerun
  `make_crates.py`.
- **Physics constants.** `G = 9.7864` (import from
  `bicycling_energy_model.engines`); frozen priors Crr 0.008 / CdA 0.40 /
  ρ 1.13 / k_eff 0.98 / wind 0; ε₀ = 0.13 (UNCLAMPED ε_d — see paper 1
  eq. (4)–(5)); ε_f = 0.20; τ = 2 m; c ≈ 3 m/km. Never re-fit any of these
  here; the letter *tests* their transfer, it does not recalibrate them.
- **Type annotations.** Every function under `src/` (harnesses included)
  carries full annotations — the Entry-28 invariant, enforced by a runnable
  cell in `research/journal/journal.qmd`. String annotations are fine.
  As of this writing `e41_dem_route.py` has 17 unannotated functions; fix
  them before the qmd is next rendered.
- **Style rules (letter inherits paper 1's).** Models are F1–F4. No paragraph
  over 200 words; ≤ 5 paragraphs per header; numbered subsections; display
  equations tagged (`\tag{L1}`, `\tag{L2}`, … for the letter) and cited from
  prose; aggregation-scope notation `_t/_i/_r/_p/_c` per paper 1's
  Terminology (bare parameter symbol = frozen constant); per-segment
  quantities carry index i. Keywords: ≤ 10, field-facing.

## 1. Phase A — reconnaissance (read, run nothing heavy)

1. Read `paper1-closed-form.md` fully. Note the exact anchors the letter
   will cite: the pooled headline (5.6% [5.2, 6.2] vs 6.3% [5.8, 6.8],
   D3+D4), the per-corpus F3/F4 rows (Table 3), §2.4 (elevation sources,
   noise methodology, the two-scale reconciliation), §4.1 (the recipe and
   the Pedal Hidrográfico practice), §4.3.4 (the (α, ε) bundle rule),
   §4.4.3 (deadband-as-suspension; c is recording-chain-dependent:
   c(τ=2) spans 2.5–4.5 m/km across corpora — Entry 38).
2. Read journal Entries 6, 19, 20, 21, 26 (and 37–40 for the τ/roller
   context). Extract Entry 20's σ-per-resolution anchor values and its gate
   thresholds (med|Δ%| < 5, |bias| < 2) — these are the letter's inherited
   prescription. `src/harness/scale_trio.py` carries the Entry-20 anchor
   constants in code.
3. Read `src/harness/goal_calibration.py` (import-safe) — it already samples
   DEM rasters along ride tracks and applies σ smoothing. Identify the
   functions to REUSE (raster access, profile construction, σ application).
   Do not reimplement raster sampling. Also read `igc_resolution_test.py`
   and `regime_compare.py` (both import-safe; the DEM chain imports them).
4. Read `src/harness/e39_tau_reg.py` and `longoes_frozen.py` as the pattern
   for "evaluate the F-grid + simulation under a protocol" and console
   scoreboards. Read `e26_portal_profiles.py` for the bridge/tunnel
   detection the letter's P4 needs.
5. Confirm raster coverage per corpus (which of D1/D3/D4/D5 fall inside the
   local FABDEM/DEM-SP tiles). Report coverage counts to Danilo before
   registering — corpus selection is his call if coverage is partial.

## 2. Phase B — pre-register (journal entry, before any full run)

Write the entry with: the substitution protocol (DEM-chain elevation
sampled along the recorded track at planner resolution, with and without
Entry-20's σ; measured power and all paper-1 frozen constants unchanged;
ε_d recomputed on the substituted profile — it is geometry-dependent by
design); populations (state them; they will differ from paper 1's clean
corpora — disclose, as Entries 33/35 did); estimands (per-corpus F3·ε_d,
F4·ε_f?, F3·ε_f, simulation — match Table 3's rows — plus the paired
per-ride delta vs the own-stream run); and the scaffold's predictions
P1–P4 made numeric:

- P1: raw fine-DEM profiles over-charge; predict the bias sign and rough
  size from Entry 6/21's measured ascent-inflation rates (write the
  arithmetic into the registration).
- P2 (headline): with σ applied, med|Δ%| within 1–2 pp of the own-stream
  values and |bias| < 2 (Entry 20's gate levels).
- P3: F4's scalar c must be re-fit per source; registered as: the DEM
  profile's own noise rate (raw − deadband ascent per km) differs from the
  barometric 3.1 m/km beyond its CI, and using the per-source rate repairs
  F4's bias.
- P4: portal (bridge/tunnel) rides are the outlier tail; E26 detection
  flags them; report with and without.
- Failure modes stated for each (P2 failing flips the letter's conclusion —
  still publishable; say so in the registration).

## 3. Phase C — instrument (`src/harness/e41_dem_route.py`)

- Stdlib-only, imports from `bicycling_energy_model` and the import-safe
  DEM-chain harnesses. `E41_SMOKE=1` (40 rides/corpus). Driver may be
  module-level (the `longoes_frozen.py` pattern) since nothing imports it.
- Per ride: load pts (`load_pts` — cached); build TWO profiles: (a) own
  stream (paper-1 protocol, the control — must reproduce the published
  numbers, a built-in parity gate like `e38_tau.py`'s `PARITY` check);
  (b) DEM-substituted at each treatment (raw fine, σ-smoothed; resolutions
  per Entry 20's table). Evaluate F1–F4 × ε_d/ε_f + simulation per
  treatment. Also record per-profile noise rate c(τ=2) and the E26 portal
  flag.
- Output: `data/results/e41_dem_route.csv`, one row per ride × treatment
  set (wide columns like `e38_tau.csv`), plus a console scoreboard
  (accuracy · bias · CI per corpus × treatment).
- Determinism: no wall-clock, no RNG beyond the seeded bootstrap.
- Smoke first; sanity-check the parity gate BEFORE the full run; full runs
  in background. If the parity gate fails, stop and diagnose — do not
  proceed to results.

## 4. Phase D — results into the journal, gates, crates

- Append the results section to the registration entry: verdicts per
  prediction, the treatment table (accuracy+bias+CI), the paired
  own-stream-vs-DEM deltas, the per-source c measurement, portal-tail
  numbers. Honest failures stay failures; deviations get the "disclosed"
  label.
- Add gates to `bootstrap_ci.py` for every number the letter will print;
  README row; crates ENTRIES/PRODUCER + `make_crates.py` rerun; full
  battery green.

## 5. Phase E — write the letter (replace the scaffold's TODOs)

- Keep it a LETTER: target ≈ 1,500–2,200 words + 1–2 tables + at most 1
  figure. Structure per the scaffold: gap → what is known → the experiment
  → the prescription table → worked example (one Pedal Hidrográfico tour;
  ask Danilo which) → limitations → data availability.
- The prescription table is the deliverable: DEM source/resolution → σ →
  τ/c to use → measured accuracy band. Cite paper 1 by section for
  everything it owns (law, constants, bundle rule, recipe); do not restate
  derivations.
- Terminology: reference paper 1's table; define only letter-new symbols.
  Equations tagged (L1), (L2), …; prose cites them.
- Abstract ≤ 200 words; keywords ≤ 10 (GIS/geodesy + transport +
  cycling-energetics facing, e.g. digital elevation models, elevation gain
  estimation, route planning, cycling energetics, active transportation).
- Every number in the letter must be a gated number. Run the paragraph
  audits (word counts, group sizes) and the link/tag checks before
  presenting.

## 6. Phase F — verification checklist (all must pass before presenting)

1. `python3 src/harness/bootstrap_ci.py` → "all gates pass" (use
   `/Users/danlessa/conda/bin/python`).
2. `e41_dem_route.py` parity gate green (own-stream columns reproduce
   paper-1 published medians on matching populations).
3. `make_crates.py` → all crates build, gates pass inside.
4. Letter audits: no paragraph > 200 words; ≤ 5 paragraphs/header; all
   `\tag`s unique and cited; internal links resolve; F-naming only;
   scope-notation rule holds.
5. Paper 1 untouched except (optionally, ask first) one §4.4 sentence
   pointing to the letter once it exists.
6. `git status` shows no private files staged. Commit only when Danilo says
   "commit"; message style per recent history;
   `Co-Authored-By: Claude <the model> <noreply@anthropic.com>`.

## 7. Decisions reserved for Danilo (ask, don't assume)

- Corpus selection if raster coverage is partial (Phase A.5 report).
- The worked-example tour; the letter's title; whether the letter carries a
  Contributions block (paper 1 has one; letters usually don't).
- Any deviation from the registered protocol after results are seen.
- Committing, and anything touching paper 1.

## 8. Known traps (each has bitten before)

- `FAST=1` on the DEM chain skips the determinism double-run — never for a
  number that ships.
- Populations differ between harnesses (clean-corpus filters vs
  manifest-based) — parity comparisons must match populations or disclose.
- ε_d is UNCLAMPED (paper 1 eq. (4)); the per-edge clamp is paper-3
  territory — do not reintroduce clamps at ride level.
- `scale_trio.py` carries Entry-20 anchors; if Entry 20 is re-run, refresh
  them — otherwise do not touch.
- The (α, ε) bundle rule: if any treatment changes effective α (it should
  not — elevation only), the ε constants stop being valid; the design keeps
  physics fixed precisely to avoid this.
- Sign conventions: Δ% = (model − measured)/measured; positive = over-
  prediction; grades percent in text, fractions in formulas.
