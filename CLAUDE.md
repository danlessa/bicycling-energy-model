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
  `bootstrap_ci.py` (bootstrap CIs + paired sign tests for every published
  median AND its 95% band — **the gate script**; exits non-zero on failure),
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
  model and the `ε ↔ k₋` bridge), `claims.ttl` (machine-readable
  claims–questions–evidence graph, widely-used vocabularies only — schema.org
  Claim/Question, CiTO, PROV-O/P-Plan, Dublin Core; validate with `rdflib`
  after editing), `claims-explorer.html` (generated — regenerate via
  `research/scripts/make_claims_explorer.py`, never hand-edit),
  `data-graph.ttl` (the **evaluation-lineage DAG** in the I/F/O/T notation:
  corpora D, parameter classes P, transformers F, per-ride outputs O and the
  published statistics T derived from them — every `:cardinality` on an output
  is *counted from its CSV*, never asserted, because `|O| ≤ |D|` and reading a
  corpus size as a result population is the error it exists to catch; validate
  with `rdflib`),
  `literature-context.md`, `simujaules-literature-context.md`,
  `crr-cda-typical-values.md`, `dem-elevation-comparison.md`,
  `ascent-error-literature.md`, `censo-model-verification.md`,
  `VERIFICATION_NOTES.md`.
- `research/scripts/` — `make_claims_explorer.py` (claims.ttl → the interactive
  explorer page).
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
- **Run the harnesses** (need the local gitignored tracks; scripts resolve
  paths relative to their own location — run from anywhere):
  `python3 src/harness/compare.py` prints the longões scoreboard **and** the
  conservation residual (must stay ≤ 1e-6); then `censo_compare.py`,
  `eps_hypothesis.py`, `eps_sp_test.py`, `ppaz_compare.py`, `time_compare.py`,
  and **`python3 src/harness/bootstrap_ci.py`** — the gate battery for every
  published median; exits non-zero on failure. `SANITY=1 regime_compare.py`
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
