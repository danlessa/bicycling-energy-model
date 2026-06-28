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
- `data/` — `sample.gpx` and `flecha_power.csv` (no GPS) committed;
  `flechamista.fit` is **gitignored** (carries a GPS track).
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
- **Commits:** only when asked. No remote yet.

## Verifying a change

No build, no CI. Verify by:

- **Load `energy-model-comparison.html` in a browser** (or headless Chrome
  `--dump-dom` / `--screenshot`) — it surfaces JS errors and shows the result.
- **Engine change → node.** Extract the pure function
  (`awk '/^function canonical\(/{p=1} p{print} p&&/^}/{exit}' energy-model-comparison.html`)
  and run it on small profiles, asserting the **energy balance**
  (`k_eff·legE = ΔKE + W_rr + W_aero + W_grav + W_brake`) and sanity cases:
  flat, pure climb (`legE ≥ PE`), pure descent (≈ coast).
- **Parser change → node.** Parse `data/flechamista.fit` (`DataView`) or
  `data/sample.gpx` and check record count, distance, and regime powers.
