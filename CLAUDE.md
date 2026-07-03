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

- `energy-model-comparison.html` — the **entire app**: canvas UI, both engines,
  the GPX and binary-FIT parsers, hardcoded Portuguese strings (single-language,
  no i18n table). **No dependencies, no bundler, no `package.json`** — open it
  directly in a browser; it surfaces syntax errors immediately. Key functions:
  `canonical()`, `approximate()`, `parseFIT()`, `buildProfile()`,
  `extractRegimePowers()`, `epsFromFIT()`, `recompute()`.
- `notas.md` — the derivations and spec: the energy law and its `α, β, ε`; the
  local recovery `ε(s)` and its descent-height-weighted aggregate; the climb-aero
  over-charge correction; the time model `x* = x + k₊·h₊ − k₋·h₋`; the `ε ↔ k₋`
  bridge through descent power. **Keep it in sync with the code** — a model
  change lands in both.
- `data/` — `sample.gpx` (synthetic) and `flecha_power.csv` (no GPS) committed;
  all `*.fit`, the `data/activities/{rwgps,strava,censohidrografico,strava_ppaz}/` track
  dirs, `data/longoes.xlsx` and `data/censo-hidrografico.xlsx` are **gitignored** (GPS /
  private activity links / physiology / third-party data). `data/longoes.xlsx` was purged
  from history (2026-07) after an accidental commit — never re-add it. `strava_ppaz/` is
  a second rider's full Strava export, shared with consent — never commit any of it.
- `data/activities/` — the validation harnesses (committable; the tracks they read are
  not): `compare.mjs` (44 longões power rides), `censo_compare.mjs` (62 censo urban
  rides), `eps_hypothesis.mjs` (ε closed-form test), `eps_sp_test.mjs` (São Paulo ε),
  `ppaz_inventory.mjs` + `ppaz_compare.mjs` (441 second-rider rides: implied-mass
  inversion + frozen-ε transfer test; `PPAZ_M=<kg>` env for mass sensitivity),
  `time_compare.mjs` (time model `x*=x+k₊h₊−k₋h₋` tested vs measured moving time on all
  three datasets; ascent transfers, descent bridge doesn't — Entry 13; `PPAZ_M` env),
  plus `fetch*.py` / `build_model_inputs.py` / `verify.py`. Each `.mjs` ports the app's
  engine + FIT parser verbatim — **keep all copies in sync** (app + six harnesses +
  `ppaz_inventory`'s parser; they drifted before).
- `research/` — the write-ups: `MODEL_COMPARISON_JOURNAL.md` (numbered entries, newest
  first), `literature-context.md` (positioning), `article-draft.md` + `article-draft.pt-BR.md`
  (the draft paper, EN + pt-BR), `crr-cda-typical-values.md`, `dem-elevation-comparison.md`,
  `censo-model-verification.md`, `VERIFICATION_NOTES.md`, and `dem/` (DEM tooling;
  `dem/coords/` is gitignored — per-ride GPS).
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

**Design principle — both read the same physical constants** (`m, C_rr, CdA, ρ,
k_eff, wind`). That is what makes the comparison meaningful: the gap is the
*model*, not the parameters. Never let the two engines diverge on a constant.

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

- **Load `energy-model-comparison.html` in a browser** (or headless Chrome
  `--dump-dom` / `--screenshot`) — it surfaces JS errors and shows the result.
- **Engine or parser change → re-run the harnesses** (need the local gitignored tracks):
  from `data/activities/`, `node compare.mjs` (prints the longões scoreboard **and** the
  worst per-ride conservation residual — must stay ≤ 1e-6), `node censo_compare.mjs`,
  `node eps_hypothesis.mjs`, `node eps_sp_test.mjs`, `node ppaz_compare.mjs`,
  `node time_compare.mjs`. Diff the numbers against the journal
  entries and `research/article-draft.md`; a doc-visible number that moves must be updated
  in both. A change to the engine or FIT parser must be applied to **all** copies (the app
  + the six harness `.mjs` + `ppaz_inventory.mjs`'s parser) or they drift.
- **Sanity cases** for an engine change: flat (canonical ≈ approximate at auto v_f),
  pure climb (`legE ≥ PE`), pure descent (≈ coast), and P=0 (the bike must *stall*, not
  gain energy — no KE floor).
