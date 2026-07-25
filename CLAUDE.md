# bicycling-energy-model

A standalone, **build-step-free** study tool comparing two models of the
mechanical energy (and time) of pedalling a route: an **approximate** closed-form
law and a **canonical** forward-dynamics simulation — run on the *same* physical
constants so the difference isolates the modelling simplifications, not the
parameters. One self-contained HTML file; the theory lives in `notas.md` (treat
it as the spec).

Part of the Pedal Hidrográfico research. The energy law is shared with
`sampasimu` (Simujaules `energy-worker.js`) and `quilojaules`; this repo is the
home of the *derivation* (`notas.md`) and the side-by-side comparison.

## Layout

- `applet/index.html` — the **entire app**: canvas UI, both engines,
  the GPX and binary-FIT parsers, hardcoded Portuguese strings (single-language,
  no i18n table). **No dependencies, no bundler, no `package.json`** — open it
  directly in a browser; it surfaces syntax errors immediately. Key functions:
  `canonical()`, `approximate()`, `v2Edge()`, `parseFIT()`, `buildProfile()`,
  `extractRegimePowers()`, `epsFromFIT()`, `recompute()`.
- `notas.md` — the derivations and spec: the energy law and its `α, β, ε`; the
  local recovery `ε(s)` and its descent-height-weighted aggregate; the climb-aero
  over-charge correction; the time model `x* = x + k₊·h₊ − k₋·h₋`; the `ε ↔ k₋`
  bridge through descent power. **Keep it in sync with the code** — a model
  change lands in both.
- `data/` — `sample.gpx` (synthetic) and `flecha_power.csv` (no GPS) committed;
  all `*.fit`, the `data/activities/{rwgps,strava,censohidrografico,strava_ppaz,strava_jaam,strava_danlessa}/`
  track dirs, `data/longoes.xlsx` and `data/censo-hidrografico.xlsx` are **gitignored** (GPS /
  private activity links / physiology / third-party data). `data/longoes.xlsx` was purged
  from history (2026-07) after an accidental commit — never re-add it. `strava_ppaz/` and
  `strava_jaam/` are two **independent** riders' full Strava exports (P. Paz, JAAM — **not**
  Pedal Hidrográfico members), shared with consent; `strava_danlessa/` is the author's own
  full Strava export (a superset of the longões, Entry 16) — never commit any of it. (Note: the
  author's own rwgps/strava rides — the "longões" — are the author's brevets, not PH rides;
  only the "censo" set is Pedal Hidrográfico.)
- `results/` — the harness outputs: per-ride result CSVs (gitignored except its
  README — they carry ride names/dates). Every file regenerates with one harness
  command (`results/README.md` maps file → producer → journal entry); the scripts
  create the folder on demand.
- `harness/` — the validation harnesses, **all Python, stdlib-only** (committable; the
  tracks they read live in `data/activities/`, their outputs in `results/` — both
  gitignored). They import the engines/parsers from `analysis/bem` rather than carrying
  copies: `compare.py` (44 longões power rides), `censo_compare.py` (62 censo urban
  rides), `eps_hypothesis.py` (ε closed-form test), `eps_sp_test.py` (São Paulo ε),
  `ppaz_inventory.py` + `ppaz_compare.py` (441 second-rider rides: implied-mass
  inversion + frozen-ε transfer test; `PPAZ_M=<kg>` env for mass sensitivity),
  `jaam_inventory.py` + `jaam_compare.py` (219 third-rider rides: same test — Entry 14,
  where the frozen-ε skill proves rider-dependent; `JAAM_M=<kg>` env),
  `danlessa_inventory.py` + `danlessa_compare.py` (the author's full Strava export, 1597
  power rides, as a fourth dataset — Entry 16; validates the mass machinery, in-sample-ish),
  `time_compare.py` (time model `x*=x+k₊h₊−k₋h₋` tested vs measured moving time on all
  three datasets; ascent transfers, descent bridge doesn't — Entry 13; `PPAZ_M` env),
  `cda_estimate.py` + `param_fit.py` (independent per-rider CdA/C_rr/mass + per-activity
  wind estimation — Entry 15; `param_fit.py`'s `pts_with_geo` keeps lat/lon for GPS bearing,
  the one point-builder that is NOT the verbatim `pts_from_fit`),
  `regime_compare.py` (the regime-decomposed closed form E_flat+E_climb+E_descent tested vs
  the champion on all five corpora — Entry 17, a rejected alternative: its win/loss is a bias
  trade, causally shown by the fitted-physics rerun; `SANITY=1` synthetic gates; evaluate
  regime closed forms on TOTALS, not per edge — per-edge ε discards its aggregate physicality;
  R1d = the deployed sampasimu v2Edge, whose clamp is provably dead — Entry 18),
  `igc_resolution_test.py` (v2Edge + R0 on the deployed IGC-SP 5 m raster vs 30 m resample vs
  FABDEM, 922 SP rides — Entry 19: 5 m resolution over-charge confirmed on the real DEM,
  ~30 m pre-smoothing mitigation triggered, FABDEM disqualified on flat terrain; needs
  gdalwarp/gdallocationinfo + sampasimu's dem/sampa_geral.tif),
  `goal_calibration.py` + `goal_smooth_rasters.py` (pre-registered ±5%/±2% goal — Entry 20:
  PASS on all three riders' validation halves at σ\*=10 m + per-rider (CdA, Crr, kSmooth);
  the calibration, not the smoothing, is the lever; fitted values are effective, not physical;
  `GOAL_SMOKE=1` for a 3-ride subset),
  `scale_trio.py` (the behavioural trio (k_s, ε₀, climbThr) re-fitted as a pure 5 m→30 m
  resolution transfer — Entry 21: bridges the rider corpora per-ride, fails on censo ⇒ the
  trio is a function of (Δx, terrain regime), not Δx alone; `SCALE_SMOKE=1`),
  `bootstrap_ci.py` (bootstrap 95% CIs + paired sign tests for the article's headline medians
  from the existing per-ride CSVs — Entry 22: champion-vs-canonical is parity, not "beats";
  gates reproduce every published median, exits non-zero on failure),
  plus `fetch*.py` / `build_model_inputs.py` / `verify.py` and `dem/` (DEM tooling;
  `dem/coords/` is gitignored — per-ride GPS).
  The `*_compare.py` take `<RIDER>_M`/`_CDA`/`_CRR` env overrides to swap the assumed physics
  for a rider's Entry-15 fitted values — the fitted-vs-assumed robustness test (Entry 16).
  **`regime_compare.py`, `igc_resolution_test.py` and `goal_calibration.py` are import-safe**
  (functions at module level, driver under `if __name__ == "__main__"`): the DEM chain
  imports them (`igc` ← `regime`; `goal` ← `regime`+`igc`; `scale_trio` ← all three).
  Their retired JS ancestors instead re-read each other's *source lines* at run time — that
  eval-the-siblings trick is gone; keep the modules importable.
- `research/notes/` — the research record: `MODEL_COMPARISON_JOURNAL.md` (numbered
  entries, newest first — the **lab journal**, authoritative), `CURATED_JOURNAL.md`
  (the readable retelling, oldest first, plain language — update it when a lab entry
  lands; on disagreement the lab journal wins),
  `literature-context.md` + `simujaules-literature-context.md`
  (positioning), `claims.ttl` (machine-readable claims–questions–evidence graph covering
  every journal entry, in widely-used vocabularies only — schema.org Claim/Question, CiTO,
  PROV-O/P-Plan, Dublin Core; per-entry evidence-package RO-Crates under
  `research/packages/` regenerate via `make_crates.py`; RO-Crate envelope at the repo
  root `ro-crate-metadata.json`),
  `crr-cda-typical-values.md`, `dem-elevation-comparison.md`,
  `ascent-error-literature.md` (barometer/DEM ascent-error lit review, Entry 24),
  `censo-model-verification.md`, `VERIFICATION_NOTES.md`.
- `research/article/` — the paper: `article-draft.md` + `article-draft.pt-BR.md`
  (the combined working paper, EN + pt-BR — canonical citation target), being split into a
  three-piece series: `piece1-energy-demand{,.pt-BR}.md` (the closed-form energy law; keeps the
  monolith's section numbers with pointer STUBS for §5/§8.8/§8.9 so cross-references stay
  stable), Piece 2 (routing/simujaules; write after Entry 26 reports) and Piece 3 (time dual)
  pending; a piece edit and its pt-BR mirror move in lockstep, `figs/` (`make_figures.py` + the committed SVGs),
  `modelo-assets/` and `build-modelo.sh` (builds the published pages at
  `simujaules.pedalhidrografi.co/modelo/` into the sibling simujaules repo).
  (DEM tooling lives in `harness/dem/`; `harness/dem/coords/` is gitignored —
  per-ride GPS.)
- `analysis/` — the Python core the whole repo now runs on (stdlib-only):
  `bem/` — **the single implementation of the engines/parsers** (`engines.py`,
  `fit.py`, `profiles.py`, `regime.py`, `ride.py`), plus `jsfmt.py` (ECMAScript number
  formatting: `to_fixed` rounds half-away-from-zero, unlike Python's half-even) and
  `v8math.py` (V8 `Math.{sin,cos,asin,atan,atan2}` + `Number::ToString`; Apple's libm
  differs from V8's fdlibm in the last ulp). **V8-exactness is no longer a required
  invariant** (dropped in the re-baseline): `v8math` is retained and still used where it
  already was — it is correct, and removing it would be churn — but a last-ulp difference
  in a printed digit is not a defect any more. The binding check is now the *numerical*
  parity below (1e-9 relative), not byte-identical output. `parity/` — the
  cross-language check: `reference.mjs` is the **frozen verbatim JS** of the retired
  `compare.mjs` engines, `js_runner.mjs` evaluates it, `run_parity.py` asserts the Python
  agrees (8 514 comparisons ≤ 1e-9; needs node). `journal.qmd` — executable Quarto mirror
  of the journal (data-gated cells skip without the private tracks).
- `README.md` — user-facing overview.

## The two models

- **Approximate** (closed form): `E ≈ α·x + β·(h₊ − ε·h₋)`, with
  `α = (C_rr·mg + ½ρCdA·(v_f+wind)²)/k_eff`, `β = mg/k_eff`. `ε ∈ [0,1]` lumps
  descent recovery; `v_f` is the flat reference speed. Per-edge descent clamp
  `max(0, α·dx − ε·β·|dh|)`.
- **Canonical** (forward dynamics): distance-marching force balance
  `m·dv/ds = k_eff·P/v − C_rr·mg·cosθ − ½ρCdA·(v+wind)² − mg·sinθ`, per-regime
  pedal power (climb/flat/descent chosen by local grade), safe-speed (`v_max`)
  brake cap on descents. Returns leg energy `∫P·dt`, time, the wheel-work
  breakdown, and the speed profile.

The app also shows **v2Edge** — the per-edge realisation Simujaules deploys
(grade-local `ε(s) = clamp01(min(1, (α/β)/s) − ε₀)`, aero gated off climbs,
`k_s` scaling β only, dead `max(0,·)` clamp — journal Entries 18–21). It is a
verbatim port of `regime_compare.py`'s `r1d_v2_edge` / sampasimu
`energy-worker.js`'s edge cost — a change to any copy must land in all
(same hand-kept-in-sync rule as the engines). It deliberately walks the RAW
profile (no deadband) at the engine dx, so the Entry-19 resolution over-charge
is visible live by moving dx between 5 and 30 m.

**Design principle — both read the same physical constants** (`m, C_rr, CdA, ρ,
k_eff, wind`). That is what makes the comparison meaningful: the gap is the
*model*, not the parameters. Never let the two engines diverge on a constant.

**Gravity is `G = 9.7864`** — São Paulo's local value (IAG-USP absolute gravimetry),
not 9.80665 or 9.81: every corpus here is ridden in the SP metropolitan region. It is
**hand-copied into 14 places** — `analysis/bem/engines.py`, `applet/index.html`,
`analysis/journal.qmd`, `analysis/parity/js_runner.mjs`'s injected preamble, and the
`G`/`KEFF, G`/`G, NS` line of each harness (`compare`, `censo_compare`,
`eps_hypothesis`, `eps_sp_test`, `ppaz_compare`, `jaam_compare`, `danlessa_compare`,
`time_compare`, `regime_compare`, `cda_estimate`, `param_fit`). A harness defines `G`
locally **and** imports `bem`'s engines, so moving one without the others mixes two
gravities inside a single computation — move them together or not at all. Three sites
keep **9.81 deliberately** because they mirror the cost bundle *sampasimu deploys*:
`verify_v2edge_clamp.py`, `e26_detour.py`'s `G_JS`, and the frozen `reference.mjs`
header comment. simujaules was re-based in step (its v63, `26c26e5`: one documented `G_SP` in
`app.js` plus its seven `docs/grid-*` mirrors), so the applet and the deployed app agree again —
but note its Rust backend holds **no** gravity constant (it receives the derived cost bundle, so
JS↔Rust parity is gravity-blind), and the shift is a two-term trade rather than one ratio: β and
`a_roll` −0.2406%, `a_aero` **+0.096%** (lower g ⇒ less rolling drag ⇒ `v_f` +0.048%), net ≈−0.2%
on a mixed edge. Still outstanding: the published `/modelo/` pages are built from THIS repo by
`research/build-modelo.sh` and still show pre-re-baseline numbers.

## Invariants — easy to break, hard to notice

- **Canonical conserves energy; leg energy ≥ work done.** The identity
  `k_eff·legE = ΔKE + W_rr + W_aero + W_grav + W_brake` must hold, so on a climb
  `legE ≥ mg·h₊/k_eff` (≥ the potential energy). It is enforced by the
  **semi-implicit** KE update — a safeguarded Newton on `g(u)=u−A/√u−B` that
  evaluates the stiff `k_eff·P/v` at the *new* speed. Do **not** reintroduce a
  `VMIN`/KE floor: it injects energy and yields `legE < PE` on underpowered steep
  climbs (the exact bug this replaced).
- **Flat-match anchor.** On flat ground canonical ≈ approximate **iff** `v_f`
  equals the flat-equilibrium speed at the flat power (`flatEqSpeed(P_flat)` —
  what *auto v_f* sets). It is the calibration point; divergences elsewhere are
  the real modelling story (e.g. uphill aero over-charge).
- **Descent split — don't double-count.** Descent aero is paid by gravity and
  already sits in `(1−ε)·β·h₋`. The **climb-aero correction** (`off`/`≈0`/`v_c`)
  must touch only climb segments (`slope ≥ climbThr`); rolling stays on all `x`,
  descents untouched.
- **`ε`-from-FIT uses the MEASURED flat speed**, not `flatEqSpeed` — otherwise a
  parameter mismatch (e.g. road `C_rr` on a gravel ride) inflates `α` and lies
  about `ε`. Keep that deliberate.
- **Decomposition consistency.** `a.roll + a.aero + a.climb + a.recov === a.E`,
  and the `ε*`-match and clamp paths read those (corrected) components — not a
  raw `α·X`. Change the aero accounting in one place ⇒ fix all of them.
- **FIT parser.** Honors per-definition endianness, compressed-timestamp
  headers, developer fields, and FIT invalid-value markers; `record` is global
  message 20. Near-duplicate points (`Δdist < 0.5 m`) are dropped so the
  integrator never divides by `dx = 0`. Regime power is speed-gated
  (`< 0.5 km/h` skipped) and time-weighted.
- **Units.** Internals are SI (N, J, m/s); display converts (kJ, km/h). `ε` and
  the grade thresholds are entered as **percent** and divided by 100. Powers in W.

## Conventions

- **UI strings in Portuguese; code identifiers and comments in English.**
- **No build, no deps.** Vanilla JS in one file. Don't add tooling; if a library
  ever becomes necessary, CDN + SRI (the ecosystem convention), not a bundler.
- **Privacy:** never commit a raw `.fit` (GPS track) — `*.fit` is gitignored, and
  the repo may go public under the `pedalhidro` org.
- **Commits:** only when asked. Remote is `origin` → `github.com/danlessa/bicycling-energy-model`
  (**public**) — so the privacy rules above are load-bearing; nothing with GPS or private
  activity links may be committed.

## Verifying a change

No build, no CI. Verify by:

- **Load `applet/index.html` in a browser** (or headless Chrome
  `--dump-dom` / `--screenshot`) — it surfaces JS errors and shows the result.
- **Engine or parser change → it lands in TWO places, not many.** The harnesses are all
  Python now and import from `analysis/bem/`, so the only copies are **`analysis/bem/`**
  and **the app (`applet/index.html`)** — keep those two in sync (the app is standalone
  vanilla JS by design; that duplication is deliberate and is the only one left). Then run
  `python3 analysis/parity/run_parity.py`, which machine-checks `bem` against the frozen
  verbatim JS in `analysis/parity/reference.mjs` (needs node).
- **Then re-run the harnesses** (need the local gitignored tracks; the scripts resolve
  `data/activities/` relative to their own location, so run from anywhere):
  `python3 harness/compare.py` (prints the longões scoreboard **and** the worst per-ride
  conservation residual — must stay ≤ 1e-6), `python3 harness/censo_compare.py`,
  `python3 harness/eps_hypothesis.py`, `python3 harness/eps_sp_test.py`,
  `python3 harness/ppaz_compare.py`, `python3 harness/time_compare.py`, and
  `python3 harness/bootstrap_ci.py` (gates every published median; exits non-zero on
  failure). `SANITY=1 python3 harness/regime_compare.py` runs the synthetic gates.
  Diff the numbers against the journal entries and `research/article/article-draft.md`;
  a doc-visible number that moves must be updated in both.
- **Writing Python that must match a published number?** Mind the traps the migration
  hit: `to_fixed`/`js_str` from `bem.jsfmt` (JS rounds half-up, Python half-even);
  `bem.v8math` for any trig feeding a printed raw float; JS `x/0` is `±inf` where Python
  raises; JS `Math.round` is half-up — never use Python's `round()`.
- **Sanity cases** for an engine change: flat (canonical ≈ approximate at auto v_f),
  pure climb (`legE ≥ PE`), pure descent (≈ coast), and P=0 (the bike must *stall*, not
  gain energy — no KE floor).
