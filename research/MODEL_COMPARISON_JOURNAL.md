# Model comparison journal

A running log of comparing the two energy models against measured rides. **Entries
are reverse-chronological — most recent first.** The foundational methodology is the
last (oldest) entry. Three energies per ride, all in kJ:

- **empirical** — measured pedalling energy `∫P·dt` from the track (ground truth)
- **canonical** — `canonical().legE`, the forward-dynamics model's `∫P·dt`
- **approximate** — `approximate().E`, the closed-form `α·x + β(h₊ − ε·h₋)`

Tooling: [data/activities/build_model_inputs.py](../data/activities/build_model_inputs.py)
(per-ride parameters from the sheet) → [data/activities/compare.mjs](../data/activities/compare.mjs)
(runs the **real** engines, ported verbatim from `energy-model-comparison.html`).
Output: `data/activities/model_comparison.csv` (gitignored). Dataset & verification:
[data/activities/README.md](../data/activities/README.md),
[VERIFICATION_NOTES.md](VERIFICATION_NOTES.md).

Running scoreboard — median |Δ%| vs empirical `∫P·dt` over 44 power rides (best first):

| model / variant | median \|Δ%\| | median Δ% | entry |
|---|--:|--:|:--:|
| **approximate `cf` + 2 m elev smooth** (deadband) | **3.4** | +2.2 | 5 |
| canonical (forward sim) | 5.1 | −1.7 | 2 |
| canonical + 2 m elev smooth | 5.6 | −3.6 | 5 |
| approximate `cf` + scalar `k_smooth` (no smoothing) | 5.8 | −0.7 | 7 |
| approximate `cf` + sheet `v_f` (`P_flat/P_avg`) | 7.2 | −0.5 | 4 |
| approximate `cf` + measured `v_f` | 7.5 | +2.7 | 4 |
| approximate + climb-fraction (`cf`) | 8.7 | +8.5 | 3 |
| approximate `off` + 2 m elev smooth | 10.0 | +9.8 | 5 |
| approximate `off` (baseline) | 19.2 | +19.2 | 2 |

**Code provenance** — the commit holding each entry's analysis code:

- **Entries 1–4** (harness `build_model_inputs.py` + `compare.mjs`: methodology, baseline,
  climb-fraction, P_flat/P_avg) — [`797173f`](../data/activities/compare.mjs)
- **Entry 5** (per-regime, elevation noise, deadband filter, τ=2) — `cd2f549`; the filter +
  `k_h` wired into the app/`notas.md` in `7e46fab`
- **Entry 6** (DEM/IGC comparison, `research/dem/`) — `7d958ca`; IGC 5 m + `k_DEM`/`k_h`
  split in `3f98465`, `a184286`
- **Entry 7** (sustained-climb `k_h` fit, `climbBalance` in `compare.mjs`) — [`9135ab9`](../data/activities/compare.mjs)
- **Entry 8** (closed-form `ε` hypothesis + test, [`eps_hypothesis.mjs`](../data/activities/eps_hypothesis.mjs)) — [`6640780`](../data/activities/eps_hypothesis.mjs)
- **Entry 9** (censo-hidrográfico urban rides, [`fetch_censo.py`](../data/activities/fetch_censo.py) +
  [`censo_compare.mjs`](../data/activities/censo_compare.mjs)) — this commit

---

## 2026-06-28 — Entry 9: closed-form models vs the Pedal Hidrográfico urban rides

*Prompt (Danilo): verify canonical / smooth-approximate / poor-man's-approximate against the
collective's own rides (`censo-hidrografico.xlsx`, Strava/RWGPS links), assuming the rider
(78 kg, CdA 0.40, C_rr 0.008, 100 % paved) and sweeping ε. Only **derived** metrics from the
activities — never the censo's own energy columns.*

**A different dataset from the `longoes` rides above** — 62 short **urban São Paulo** social
rides (median 33 km, 454 m climb, **16.5 km/h**, ~14 m/km — hilly but **stop-go**: traffic
lights, intersections, corners), vs. the 44 long, openable power-meter rides of Entries 1–8. Pipeline: 87 activity links (cols Q/R, RWGPS preferred) →
70 downloadable (16 are other riders' Strava, not exportable by the owner's cookie) → 69 with
power → **62 after a physical-plausibility cut**. Everything factual is derived from the track
(geometry, FIT-extracted regime powers, v_f, ∫P·dt); the sheet supplies only the links.

**Physical floor — drop the not-fully-pedalled rides.** Pedalling energy must cover the
(momentum-corrected, 2 m-deadband) climbing PE `mg·h₊_sm/k_eff`; **7 rides measure below it**
(down to 53 %) — impossible for a fully-pedalled ride. *Why?* The clean test is **cadence**
(Danilo: pedalling ⇔ cadence > 0). On 6 of the 7, cadence coverage is 73–100 % and the
walking signal — moving < 4 km/h **with cadence 0** — is only **~1 %**. So the riders were
*pedalling, not walking*; the deficit is a **power-channel problem** (power dropping out while
cadence kept logging, or an under-reading meter). The 7th (Mirantes, 31 % cadence coverage) is
a fuller sensor dropout. Walking does happen on these rides in general, but for *these* it is
ruled out — and the floor excludes them either way. They over-predict by +79…+373 % and would
wreck the mean.

**Result on the 62 clean rides** — Δ% vs measured ∫P·dt, ε swept:

| model | med \|Δ%\| | medΔ% | meanΔ% |
|---|--:|--:|--:|
| canonical (fed ride powers) | 6.5 | −3.4 | −0.8 |
| smooth approx · ε=0.10 | 4.5 | +3.4 | +5.7 |
| smooth approx · ε=0.15 | 4.9 | +1.3 | +3.4 |
| smooth approx · ε=0.20 | 4.7 | −0.8 | +1.2 |
| **poor-man's · ε=0.20** | **3.9** | +1.1 | +4.6 |
| poor-man's · ε=0.25 | 4.8 | −1.2 | +2.0 |
| poor-man's · ε=geom (0.29) | 6.4 | −3.3 | +1.1 |
| smooth approx · ε=geom (0.29) | 7.6 | −4.9 | −2.0 |
| (ε=0.00, both) | 7.5 / 10.5 | +7.4 / +10.5 | — |

- **All three models reproduce measured energy to ~4–7 %** — and with a *generic assumed
  rider*, not per-ride fitted params. So as a **planning tool** (know mass/CdA/C_rr, run the
  closed form) the model lands within ~5 % on real rides.
- **The poor-man's scalar `k_smooth` is as good as the full simulation** (3.9 % vs canonical
  6.5 %). The `k_smooth = 1 − 0.003·x/h₊` shortcut loses nothing here — strong support for the
  low-compute closed form.
- **ε ≈ 0.15–0.20 is the sweet spot** (med \|Δ%\| floor ~4 %); `ε=0` over-predicts +7…+10 %, so
  descent recovery is real and needed. ε-sensitivity is ~12–14 pp across the full ladder.
- **`ε_geom` (median 0.29) over-credits descent recovery here → ~3–5 % under-prediction.**
  `ε_geom` assumes *free coasting*, but São Paulo's riding is **stop-go** — constant braking
  for traffic, lights and corners suppresses recovery well below the coasting ideal. This is
  the **braking penalty** (Entry 8's intuition #4) that the open rural rides couldn't isolate
  — the urban set surfaces it. So: `ε_geom` (or higher) on open routes you can actually coast;
  a flat **ε ≈ 0.20** on urban stop-go ones. (A slightly low assumed `C_rr` for rough city
  asphalt may also nudge the under-prediction.)

Tooling: [data/activities/fetch_censo.py](../data/activities/fetch_censo.py) (RWGPS-preferred
downloader) → [data/activities/censo_compare.mjs](../data/activities/censo_compare.mjs). Output
`censohidrografico/censo_comparison.csv` (gitignored, like the tracks and the sheet).

---

## 2026-06-28 — Entry 8: a closed form for ε from route geometry

*Prompt (Danilo): hypothesise a closed form for ε from each activity's details. Intuitions:
long descents → a non-zero floor tied to max safe speed; close/low rollers and flat terrain
→ ε→1; tight curves → lower ε; off-road → lower ε.*

**Hypothesis.** On any descent where the legs are idle (coast *or* brake — both save the
same `α·dx`), `ε(s) = (α·dx − E_legs)/(β·h₋)` collapses to a function of grade alone:

```text
ε_coast(s) = min(1, α/(β·s)),   α/β = Crr + ½ρCdA(v_f+w)²/(mg)
ε ≈ clamp[0,1]( ε_coast − c_κ·κ − c_u·f_unpaved )     (+ braking penalties)
```

drop-weighted over the descent profile (or lumped with `s̄ = H₋/X₋`). Tested against the
per-ride **descent-energy-balance ε** (`epsFromBalance`, the app's `epsFromFIT`: 30 m cells,
`ε = (α·X₋ − E_legs,₋)/(β·H₋)`, α at the *measured* flat speed) over the 44 power rides.
Tool: [data/activities/eps_hypothesis.mjs](../data/activities/eps_hypothesis.mjs) (κ = curviness in
rad/km from the GPS, `f_unpaved` = sheet col I).

**The grade core holds — but only where ε carries energy:**

| view | corr(ε_coast, ε_bal) | bias (ε_bal − ε_coast) |
|---|--:|--:|
| all 44 rides (unweighted) | 0.38 | −0.18 |
| weighted by descent energy `β·H₋` | **0.65** | −0.19 |
| real descents, `s̄ ≥ 3.0%` (n=22) | **0.83** | −0.13 |
| real descents, `s̄ ≥ 3.5%` (n=15) | **0.87** | −0.13 |

- **Validated estimator:** `ε ≈ clamp[0,1]( ε_coast − 0.13 )`. The −0.13 is a near-constant
  offset (residual descent pedalling/braking the coasting ideal ignores); it turns the
  `s̄≥3%` median ε_coast 0.39 → 0.26, matching the measured 0.27.
- **"Flat → ε→1" is *reversed* by the data** (intuitions #2/#3). Gentle rides are pedalled
  *through* the dips, so measured ε→0, not 1 (NS3 Caracaí: predicted ≈0.9, measured **0.01**).
  This is the whole −0.18 unweighted bias — but it is **harmless**, because those rides carry
  `β·H₋ ≈ 0` descent energy (hence energy-weighting alone lifts corr 0.38 → 0.65).
- **Curve / off-road penalties fail** (intuitions #4/#5): κ and `f_unpaved` fit with the
  **wrong sign** (+0.03, +0.14). They are confounded with *mountainous terrain* — twisty/rough
  rides are exactly the ones with real sustained descents, which recover *more*. The
  braking-loss effect is real but swamped.
- **Descent intuition #1 is the load-bearing one and it holds.** The remaining scatter is
  rider *behaviour* — several rides have measured ε < 0 (pedalling downhill, `E_legs > α·X₋`),
  which no route-geometry term can predict.

*Worked example (RMC200 Mogi):* α/β = 0.0202, s̄ = 3.4% ⇒ min(1, 0.0202/0.0341) = 0.59;
minus 0.13 ⇒ **0.46**, vs. measured **0.47**.

Net: a one-parameter `min(1, α/β·s̄) − 0.13`, computable from activity details (Crr, CdA,
v_f, descent-grade distribution), beats the sheet's flat 0.23/0.27 constant on real-descent
rides. Written up in [notas.md](../notas.md) (*Closed form: predicting ε from the route*) and
wired into the app as an auto-ε option. The closed form does **not** replace the per-ride
`epsFromFIT` where a power track exists — it is for *planning* (no track, geometry only).

---

## 2026-06-28 — Entry 7: fitting k_h on sustained climbs (the clean way)

*Prompt (Danilo): fit k_h by taking sustained ascent sections (mean slope > 3 % over
> 100 m) and comparing measured energy output to expected.*

This isolates the climb physics: on a *sustained* climb there is no momentum recovery and
aero is small, so the rider must pay ≈ `mg·Δh/k_eff` + rolling. Over the 44 power rides,
**2535** such sections (≥ 3 %, ≥ 100 m), summed:

| | kJ |
|---|--:|
| measured Σ∫P·dt on climbs | 41 790 |
| expected (grav 37 366 + roll 4 424 + aero 1 424) | 43 214 |
| **measured / expected** | **0.97** |
| **k_h(sustained) = (measured − roll − aero)/gravity** | **0.96** |

(per-ride median 1.03, range 0.57–1.23.)

- **On real sustained climbs `k_h ≈ 1`** — the rider pays the full `mg·Δh`, so the model's
  gravity term `β·h₊` is correct there. This settles the earlier 0.56-vs-0.9 confusion:
  there is **no uniform discount** on real climbing.
- **Sustained climbs are only 54 % of total ascent.** The other 46 % is rollers / gentle
  grades / noise — and *that* is where the aggregate `k_h < 1` comes from (momentum carries
  the rider over a roller without paying `mg·h`; noise isn't real climbing at all).
- **So a *uniform* scalar `k_h` (the earlier 0.56) is the wrong model.** The right correction
  is "pay full on sustained climbs, discount the rollers" — exactly what the per-segment
  **deadband** (notas v2's `k_h`, Entry 5) does: it keeps a 100 m+ climb intact and removes
  sub-τ undulations. The scalar crudely lumped the two and over-corrected the real climbs.
- **For the DEM sources:** sustained climbs are big features all sources capture similarly,
  so `k_h(sustained) ≈ 1` for FABDEM/IGC too; the per-source difference (Entry 6's `k_DEM`)
  lives in the rollers/noise, not the real climbs. (The baro lags slightly even on climbs, so
  a bare-earth DEM's sustained Δh is marginally higher — a second-order refinement.)

**Resolution of the Entry-6 TODO:** keep `β·h₊` at full strength on sustained climbs; realise
the roller/noise correction as a **deadband (~2 m)**, not a scalar.

**Cross-check — the three v2 realisations vs the empirical `∫P·dt` (≈ sheet `Work Bike`):**

| model | median \|Δ%\| | median Δ% |
|---|--:|--:|
| **smoothened** (cf + real 2 m deadband, `k_smooth=1`) | **3.4** | +2.2 |
| canonical (forward sim) | 5.1 | −1.7 |
| **k_smooth** (cf + scalar `1 − c·x/h₊`, no smoothing) | 5.8 | −0.7 |

The **real deadband is best** (3.4 %); the **scalar `k_smooth` is unbiased (−0.7 %) but ~2×
the scatter** — a constant rate can't match each ride's roller mix — landing alongside the
canonical forward-sim. So: use the deadband when you have the profile; the scalar `k_smooth`
is the cheap, unbiased fallback for the low-compute closed form.

---

## 2026-06-28 — Entry 6: external DEMs (FABDEM/SRTM/COP30) and k_h for DEM-derived h₊/h₋

*Prompt: pull FABDEM, SRTM, COP30 for the routes and see how the elevation differs; then —
what is k_h for h₊/h₋ derived from a DEM?*

Sampled three independent 30 m DEMs at every track point for the 12 rides inside the São
Paulo tile S24W047, vs the recorded barometric track. Full write-up:
[dem-elevation-comparison.md](dem-elevation-comparison.md).

**Headline.** DEMs are accurate *terrain* models (elevation shape matches the recorded
track to ~7–8 m RMS; SRTM sits ~7 m above FABDEM = the canopy/buildings FABDEM strips).
But **DEM ascent sampled along the GPS track is inflated** — a DEM is the terrain, not the
engineered road. Two parts: nearest-neighbour sampling adds ~30 pp of staircase artifact
(**use bilinear**), and a real residual remains because the road is graded/cut and DEMs
keep terrain roughness (plus canopy/buildings for the DSMs).

A later check added the **IGC-SP 2010 5 m aerophotogrammetric DTM** (bare-earth, covers 10
of the 12 rides) and it shows **no single source is ground truth for ascent — they bracket
it.** Σ h₊ (3 m-hyst, bilinear) over the 10 IGC-covered rides, IGC as reference:

| source | res | Σ h₊ (3 m) | vs IGC | **k_DEM** |
|---|--|--:|--:|--:|
| recorded baro | — | 13 622 (raw 15 292) | −21 % (raw −11 %) | 1.26 |
| **IGC** (bare-earth) | **5 m** | **17 162** | reference | 1.00 |
| FABDEM (bare-earth) | 30 m | 18 160 | +6 % | 0.95 |
| COP30 (DSM) | 30 m | 20 310 | +18 % | 0.84 |
| SRTM (DSM) | 30 m | 22 951 | +34 % | 0.75 |

**`k_DEM = IGC / source`** is the **geometric** correction (source → 5 m survey truth), and it
is the solid result here. `k_DEM(h₊) ≈ k_DEM(h₋)` (symmetric). It is **small for bare-earth
sources** — FABDEM is within 5 % of the 5 m truth — confirming the DEM *geometry* error is
minor (the DSMs over-record via canopy/buildings; the baro under-records via lag).

Per-ride `k_DEM` (median, min–max over the 10 rides): **FABDEM 0.93 (0.81–1.09, tight)**,
COP30 0.84 (0.79–0.95), SRTM 0.72 (0.59–0.90, noisiest), baro 1.23 (1.10–1.54 — terrain-
dependent, worst on rough/gravel: r2 arrochai 1.54, Cantareira 2 1.46).

- **The two bare-earth sources agree (~17–18 km, within 6 %)** — IGC 5 m ≈ FABDEM 30 m,
  cross-checking the real terrain ascent.
- **The recorded baro *under*-records** (−11 % raw, −21 % smoothed): the altimeter lags and
  smooths, so short climbs read as ~null grade (Danilo's observation). It is the LOW
  outlier — **not** ground truth (correcting an earlier overstatement). The DSMs *over*-record
  (SRTM +34 %).
- **But DTMs/DEMs miss bridges and tunnels** — a bridge dips the surface into the spanned
  valley, a tunnel climbs it over the pierced ridge — so they over-record exactly where the
  baro is right. The truth is bracketed: baro low, DTM high.

**The model's energy `k_h` is a *separate*, milder correction — and not yet cleanly measured
per source.** It maps geometry → pedalling energy (lower, because momentum carries the rider
over rollers without paying `mg·h`). An earlier estimate here (`k_h(FABDEM) ≈ 0.56`) **over-
stated it**: it scaled from the baro's Entry-5 `k_h ≈ 0.74`, but that 0.74 is entangled with
the `v_f` error (Entry 4: fixing `v_f` alone cut the over-prediction +8.5 % → +2.7 %, so the
*true* `h₊` smoothing is small, baro `k_h ~0.9`) and uses a different pipeline. From first
principles — small `k_DEM` + a mild momentum term — bare-earth `k_h` should be **~0.8–0.9**.
**TODO:** fit `k_h` per source by running the approximate (with the corrected `v_f`) against
the empirical `∫P·dt` with each source's profile. (The canonical needs no `k_h` — it handles
momentum explicitly via KE.)

---

## 2026-06-28 — Entry 5: per-regime breakdown, elevation noise in h₊, and a smoothing filter

*Prompts: how do the models compare on climb / flat / descent separately? how much is
elevation noise affecting h₊? then — apply a filter and compare.*

### 5.1 Where the error lives — per-regime energy

Each model's energy split into climb / flat / descent (same ±2 % / −1.5 % thresholds),
summed over the 44 rides (kJ), vs empirical `∫P·dt` per regime:

| regime | share | empirical | canon Δ% | off Δ% | cf Δ% |
|---|--:|--:|--:|--:|--:|
| **climb** | 48 % | 57 274 | +7.5 | +48.1 | +26.7 |
| flat | 45 % | 53 756 | −3.8 | −2.6 | −2.6 |
| descent | 7 % | 8 003 | −17.9 | +17.4 | +17.4 |

- **Flat (45 %): everyone within ±4 %** — the flat-match anchor holds; `cf` ≡ `off` on
  the flat (the correction only touches climbs). Neither model has a flat problem.
- **Climb (48 %): the entire approximate error lives here.** `off` over-charges climb
  energy by **+48 %** (the uphill aero over-charge, isolated); `cf` cuts it to +27 %;
  canonical is +7.5 %. The approximate's whole +19 % total is a climb story.
- **Descent (7 %): small, opposite misses** — canonical −18 % (its coast-to-`v_max` sim
  pedals less than the rider did), approximate +17 % (the `ε≈0.25` recovery under-credits).
  They partly cancel; only 7 % of energy.

### 5.2 How much of the climb residual is elevation noise in h₊

Total ascent `h₊` over rides, at hysteresis thresholds (raw = every positive step;
τ-m = commit only after τ m net rise):

| smoothing | Σ h₊ (km) | % of raw |
|---|--:|--:|
| raw | 92.4 | 100 % |
| 1 m | 83.3 | 90 % |
| 2 m | 77.4 | 84 % |
| 3 m | 73.3 | 79 % |
| 5 m | 66.9 | 72 % |
| **engine (5 m grid, current)** | **91.7** | **99 %** |

- **~20 % of raw `h₊` is sub-3 m jitter** (0.2 m altitude quantization + high sample
  rate). Both sources noisy: RWGPS −20 %, Strava −22 % raw→3 m.
- **The engine doesn't denoise it** — the 5 m distance-resample is interpolation, not
  filtering, so 99 % of the raw noise flows into `β·h₊`.
- **Energy:** `β·h₊` = 69 039 kJ raw → 54 758 kJ at 3 m. The 14 282 kJ difference is
  **25 % of empirical climb energy** and **~93 % of `cf`'s climb over-prediction** — so
  almost all of `cf`'s remaining climb miss is ascent noise, not model form. It also
  explains why the approximate (whose `β·h₊` is *linear* in raw ascent) is hit far
  harder than canonical.

### 5.3 Applying an elevation filter — and an asymmetry

Added a **deadband filter** on the profile elevation (ignores moves < τ, tracks larger
ones) and re-ran both engines on the smoothed profile. Tried τ = 2 and 3 m (engine `h₊`
91.7 km raw → 68.4 km at 2 m → 63.0 km at 3 m):

| variant (median \|Δ%\|) | raw | +2 m | +3 m |
|---|--:|--:|--:|
| canonical | 5.1 | **5.6** | 6.2 |
| approx `off` | 19.2 | 10.0 | **7.4** |
| **approx `cf`** | 8.7 | **3.4** | 3.1 |
| `cf` climb-regime Δ% | +26.7 | **−4.5** | −12.0 |

- **`cf` + smoothing → median |Δ%| ≈ 3 % — the closed-form law now beats the raw
  canonical forward-sim (5.1 %).** The climb-fraction aero fix and elevation denoising
  together close essentially the whole gap.
- **The filter helps the approximate but mildly *hurts* canonical** — the two models feel
  elevation noise through different mechanisms:
  - The approximate's `β·h₊` is **linear in ascent** — a 1 m noise bump adds `β·1 m` of
    spurious energy, so denoising fixes it directly.
  - The canonical's energy is `Σ P·dt ≈ distance × power` — a small bump adds almost no
    horizontal distance, so it is nearly **immune** to ascent noise. Smoothing instead
    perturbs its **regime classification** (former micro-climbs become "flat", swapping
    `P_climb`→`P_flat`), slightly *under*-counting the power spent on real undulations.
- **Chosen default: τ = 2 m** (`TAU_SMOOTH = 2`). It's a hair behind τ = 3 on the
  aggregate median (3.4 vs 3.1) but **far better balanced per-regime** (`cf` climb −4.5
  vs −12) and **gentler on canonical** (5.6 vs 6.2) — a model that is right regime-by-
  regime beats one that is right in aggregate by cancellation.
- **Takeaway:** denoise `h₊` for the **approximate** (it needs it); the **canonical** is
  fine on the raw profile — smoothing it is mildly counter-productive.

Reproduce: the per-regime, elevation-noise, and filter blocks are at the end of
`compare.mjs` (`TAU_SMOOTH = 2`).

---

## 2026-06-28 — Entry 4: the `P_flat/P_avg` term and the `v_f` lever

*Prompt: the sheet has a `P_flat/P_avg` column (col AB) — flat power as a fraction
of average power (= energy / moving time). Can we take it into account?*

The approximate's `v_f` (flat reference speed) sets the aero part of α (∝ `v_f²`).
The harness sets `v_f = flatEqSpeed(P_flat)` with `P_flat` **extracted** from the
grade-binned track power. The sheet's `P_flat/P_avg` is the rider's *alternative*
way to get `P_flat = ratio · ⟨W⟩_mes`. Wired it in (and, as a tie-breaker, also
tried `v_f` = the **measured** flat ground speed, the `epsFromFIT` definition).

**Reconciliation — the sheet's ratio is much lower than the data's.**

| | median |
|---|--:|
| extracted flat power ÷ ⟨W⟩_mes (data) | **0.94** |
| `P_flat/P_avg` (sheet col AB) | **0.60** |

So the actual flat-segment power is ~94 % of the rider's average power, but the
sheet assumes 60 % — i.e. the data's flat power is ~1.6× the rider's assumption.

**Effect on the approximate (all on top of the climb-fraction `cf` base):**

| `v_f` source | median `v_f` | median Δ% | median \|Δ%\| |
|---|--:|--:|--:|
| `flatEqSpeed(extracted P_flat)` — current | 23.4 km/h | +8.5 | 8.7 |
| **measured flat ground speed** | 22.1 km/h | **+2.7** | 7.5 |
| sheet `P_flat/P_avg` → `flatEqSpeed` | 19.7 km/h | **−0.5** | 7.2 |

**Findings.**

- **`v_f` is the second lever** (after climb aero, Entry 3). `flatEqSpeed(extracted
  P_flat)` yields 23.4 km/h — *higher* than the actually-measured flat speed (22.1)
  on 32 / 44 rides — so it over-charges aero and is most of the remaining +8.5 %.
- **The principled fix is the measured flat speed**, not a derived one: feeding the
  real flat ground speed into `v_f` cuts the residual from +8.5 % to **+2.7 %**.
- **The sheet's `P_flat/P_avg` (0.60) drives `v_f` to 19.7 km/h — a touch *below*
  the measured 22.1 — and nulls the bias (−0.5 %).** It "works", but by slightly
  over-correcting `v_f`: a useful proxy that lands near zero partly by absorbing
  other residuals, not because flat power is really 60 % of average (it is ~94 %).
- Net: incorporating `P_flat/P_avg` *does* help, and it usefully exposes that the
  closed form is sensitive to how `v_f` is sourced. The cleanest, least-tuned route
  to the same place is to source `v_f` from the measured flat speed directly.

**Open question for next time.** `flatEqSpeed(P_flat)` over-predicts the real flat
speed by ~6 % median — is that a `flatEqSpeed` convexity effect (mean power → higher
eq speed than mean speed) or are the sheet `CdA`/`C_rr` slightly low? Worth checking
before recommending a `v_f` policy for the app/`notas.md`.

---

## 2026-06-28 — Entry 3: climb-fraction correction in α

*Prompt: how does the approximate behave if the climb-fraction correction is folded
into α?*

`notas.md` already specifies it ("Correcting the climb aero over-charge"): split
`α = α_r + α_a`, keep rolling `α_r` over all of x, and apply the aero part `α_a`
only over the **non-climbing fraction** `f_flat = 1 − x₊/x`:

```text
E ≈ α_r·x + α_a·x·f_flat + β(h₊ − ε·h₋)
```

Summed from the profile this is exactly the engine's `'zero'` climb-aero mode; the
near-exact variant `'vc'` charges climb aero at `v_c ≈ k_eff·P_climb/(C_rr·mg·cosθ +
mg·sinθ)`, capped at `v_f`. Ran both:

| approximate variant | median \|Δ%\| | median Δ% | mean Δ% |
|---|--:|--:|--:|
| `off` (full v_f aero) | 19.2 | +19.2 | +22.0 |
| **climb-fraction (`zero`)** | **8.7** | **+8.5** | +12.1 |
| near-exact (`v_c`) | 12.5 | +12.5 | +15.8 |
| *canonical (reference)* | 5.1 | −1.7 | +1.1 |

Median climb fraction across rides: **21 %**.

**Findings.**

- **The climb-fraction correction roughly halves the over-prediction** (+19.2 % →
  +8.5 % median) and beats `off` on **43 / 44 rides**.
- **Zeroing climb aero (`zero`) beats charging it at `v_c` (8.5 % vs 12.5 %).**
  Climbs are slow, so real climb aero `(v_c/v_f)²` is closer to 0 than to the `v_c`
  estimate. (Caveat: `zero` may also be absorbing part of the `v_f` residual later
  found in Entry 4 — it is not necessarily more physically right.)
- **A residual ~+8.5 % remains** — climb aero is the largest single source of the
  approximate's bias, but not the only one. Entry 4 chases the rest (`v_f`).

---

## 2026-06-28 — Entry 2: baseline run (climb-aero `off`)

First full run over the 44 power rides. Δ% = (model − empirical)/empirical.

| model vs empirical | n | median \|Δ%\| | median Δ% | mean Δ% |
|---|--:|--:|--:|--:|
| **canonical** (forward sim) | 44 | **5.1** | −1.7 | +1.1 |
| **approximate** (`off`) | 44 | **19.2** | +19.2 | +22.0 |

**Findings.**

- **Canonical reproduces measured energy to ~5 % with no bias.** Three grade-binned
  constant powers + forward dynamics recover the real `∫P·dt`. Cleanest rides land
  within ±1 %: NS1 Uiramutã +0.3, Rio Unite d2 −0.5, Gravel Ucraniano −0.9.
- **Approximate sits ~19 % high on essentially every ride.** The consistent positive
  sign is the **uphill aero over-charge** — α bills aero at `v_f` over the whole
  distance though climbs are ridden far slower. (Addressed in Entries 3–4.)
- **Outliers (canonical over-predicts):** RMC300 Guararema +33.8, RMC300 Salesópolis
  2022 +24.9 (climb fraction 38 %), RMC200 Mogi +23.6 (its Strava original is a
  partial 88/210 km upload), Rio Unite d3 +22.1 (climb fraction 45 %). These cluster
  on high-climb-fraction RWGPS rides where elevation noise inflates simulated climb
  work — consistent with the ~10 % ascent disagreement in the verification pass.

**Two parser issues fixed to reach 44/44 (both worth noting for the app):**

1. **Interleaved distance/altitude** — 3 Strava FITs (S. Pedro, Petr3, Ubatuba
   Cunha) log distance and altitude in *separate* record messages. Requiring both
   per-record yields zero points (the app's `loadFIT` would hit this too). Fixed by
   interpolating distance over record index (a naive forward-fill flattens climbs).
2. **GPX attribute order** — Assou's `.gpx` writes `lon` before `lat`; reader is now
   attribute-order agnostic.

---

## 2026-06-28 — Entry 1: methodology & how the three energies are built

The comparison is only meaningful if the inputs are pinned. This entry is the
reference for all the runs above.

### Data per ride

44 of 52 catalogued rides have measured power and a track file (the rest: 6
pre-power-meter 2020 Strava rides + 2 planned routes). Each ride contributes a
**track** (`.fit`, or Assou's `.gpx`) parsed by the app's verbatim `parseFIT` into
`{x=distance, alt, power, speed, dt}`, and a **parameter set** read straight from
the `Atividades v2` sheet — the rider's own values, nothing refit here.

### Empirical `∫P·dt`

Raw measured pedalling energy: `Σ power·dt` over **every** power sample and its time
delta (coasting zeros included). Equals the sheet's `Work Bike` column and matches
it to ~0.3 % median (verification pass). This is the ground truth.

### Canonical — three *constant per-regime* powers, derived from the file

> *Did canonical use the file's power time-series or a climb/flat/descent constant?*
> **Constant per regime, derived from the file.**

The track's measured power is **compressed to three constants** —
`P_climb / P_flat / P_descent` — by `extractRegimePowers`: each sample binned by its
local grade over a 30 m window into climb (≥ +2 %) / flat / descent (≤ −1.5 %), each
regime's power = the **time-weighted mean including zeros** (`fitStat='mean'`, app
default — the energy-consistent statistic, since mean·time = `∫P·dt` for the regime).
The forward sim marches the profile, assigns each 5 m segment one of the three
constants by its local grade, and integrates `legE = ∫P·dt` under semi-implicit
dynamics, braking-capped at `v_max`.

Not circular with empirical: per regime `empirical = mean_r · T_actual_r` while
`canonical = mean_r · T_model_r`, so agreement tests whether the dynamics reproduce
the ride's *time-in-regime* (its speed), not just the bookkeeping.

### Approximate — closed form on sheet parameters

`E = α·x + β(h₊ − ε·h₋)`, `α = (C_rr·mg + ½ρCdA·(v_f+wind)²)/k_eff`, `β = mg/k_eff`.

- **ε**: *from the spreadsheet* (`g_d_eff`, col AA — the rider's guess). The app can
  estimate ε from a FIT (`epsFromFIT`), but the comparison uses the rider's value,
  consistent with sourcing every other parameter from the sheet. ε only scales the
  descent-recovery term, so it is orthogonal to the climb-aero/`v_f` levers.
- **v_f**: baseline = `flatEqSpeed(P_flat)` at the flat regime power (the flat-match
  anchor); alternatives explored in Entry 4.
- **climb-aero**: `off` baseline; `zero`/`vc` in Entry 3.

### Parameter provenance

| Parameter | Source | Note |
|---|---|---|
| mass `m` | sheet `Weight` (M) | per ride |
| `CdA` | sheet `CdA` (N) | per ride |
| `C_rr` | sheet `efCrr` (AE) | blended road/offroad by unpaved fraction |
| headwind | sheet `Headwind` (L) | per ride, +against travel |
| air density `ρ` | sheet `Rho` (AT) | per ride |
| `k_eff` | sheet `Eff` (AR) | per ride (~0.98) |
| ε (recovery) | sheet `g_d_eff` (AA) | per ride, **rider's guess** |
| `P_flat/P_avg` | sheet (AB) | rider's flat-power ratio (Entry 4) |
| `P_climb/flat/descent` | **from track** | time-weighted mean incl. zeros, grade-binned |
| `v_f` | computed | `flatEqSpeed(P_flat)` (baseline) |
| `v_max`, `v_start` | app default | 38 / 15 km/h, all rides |
| climb/descent thresholds | app default | +2 % / −1.5 %, all rides |
| engine `dx` | app default | 5 m resample |

**Design principle held:** both engines read the *same* `{m, C_rr, CdA, ρ, k_eff,
wind}`, so any gap is the model, not the parameters.

### Port fidelity

`canonical`, `approximate`, `parseFIT`, `extractRegimePowers`, `flatEqSpeed`,
`buildProfile` are copied verbatim from `energy-model-comparison.html`. The
conservation identity `k_eff·legE = ΔKE + W_rr + W_aero + W_grav + W_brake` holds to
1e-6 relative error on spot-checked rides — confirming the canonical port.

### Reproduce

```sh
cd data/activities
python3 build_model_inputs.py     # per-ride parameters from the sheet -> model_inputs.json
node compare.mjs                  # canonical + approximate variants; writes model_comparison.csv
```
