# bicycling-energy-model

A standalone, build-step-free study tool that compares two models of the
mechanical energy (and time) of pedalling a route:

- an **approximate** closed-form model — `E ≈ α·x + β·(h₊ − ε·h₋)` — the
  asymmetric uphill/downhill cycling-energy law used across the Pedal
  Hidrográfico tools (Simujaules / quilojaules);
- a **canonical** forward-dynamics simulation — a per-step force balance
  `m·dv/ds = k_eff·P/v − C_rr·mg·cosθ − ½ρ·CdA·(v+wind)² − mg·sinθ` with a
  safe-speed brake cap on descents (semi-implicit, so it stays exact even on
  near-stall climbs).

Both run on the **same physical constants**, so the difference isolates the
*modelling simplifications* (aero charged at a fixed flat speed, descent losses
lumped into ε, …) rather than a parameter mismatch.

## Use

Open **`energy-model-comparison.html`** in a browser — no build, no server, no
dependencies. You can:

- draw an elevation profile, or load a **GPX** or **FIT** file;
- from a FIT, auto-extract climb / flat / descent power (mean / median / mean-
  with-zeros, time-weighted, speed-gated) and derive the empirical descent
  recovery **ε** the ride exhibited;
- set per-regime power, climb/descent thresholds (incl. a "gravity ≥ 50%"
  button), headwind, and the engine resolution `dx`;
- compare total energy, the per-regime decomposition, the canonical speed
  profile, displacement energy, and the climb-aero correction (`off` / `≈0` /
  `v_c`) against canonical.

## Theory

**`notas.md`** holds the derivations: the energy law and its `α`, `β`, `ε`
coefficients; the local recovery `ε(s)` and its descent-height-weighted
aggregate; the climb-aero over-charge correction; the time model
(effective-flat-distance `x* = x + k₊·h₊ − k₋·h₋`, with `k₊ = v_f·β/P_climb`
clean and `k₋` the time-domain twin of `ε`); and the `ε ↔ k₋` bridge through the
descent power.

## Data

`data/` — `sample.gpx` (tiny GPX fixture) and `flecha_power.csv` (per-second
power / altitude / grade / regime export from a long brevet, used for the
empirical-ε and statistics work; no GPS coordinates). Raw `*.fit` tracks, the
per-rider spreadsheets, and the downloaded activity dirs under `data/activities/`
are **gitignored** — they carry GPS tracks and private activity links.

The model has been validated against power-meter rides from **three riders** — the
author (44 long "longões" + 62 urban "censo" rides) plus **two independent riders**
(P. Paz, 441 rides; JAAM, 219 rides; neither a Pedal Hidrográfico member, each shared
with consent). Frozen and tested on the two independent riders, the energy law and the
−0.13 offset transfer, while the geometric ε *skill* proves rider-dependent (it wins for
a coaster, is inconclusive for a fast descent-pedaller). The **time** model
(`x* = x + k₊·h₊ − k₋·h₋`) is also tested against measured moving time (`time_compare.mjs`):
the ascent half transfers, the descent bridge does not. The harnesses live in
`data/activities/` (`compare.mjs`, `censo_compare.mjs`, `eps_hypothesis.mjs`,
`eps_sp_test.mjs`, `ppaz_inventory.mjs`, `ppaz_compare.mjs`, `jaam_inventory.mjs`,
`jaam_compare.mjs`, `time_compare.mjs`, `regime_compare.mjs`) and the write-ups — including a draft paper — live
in **`research/`** (`MODEL_COMPARISON_JOURNAL.md`, `article-draft.md`, `literature-context.md`, …).

---

Extracted from the Pedal Hidrográfico research; the energy law is shared with
`sampasimu` (Simujaules) and `quilojaules`.
