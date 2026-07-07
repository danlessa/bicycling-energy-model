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
| **approximate `cf` + 2 m elev smooth** (deadband) | **3.6** | +2.2 | 5 |
| canonical (forward sim) | 5.1 | −1.7 | 2 |
| canonical + 2 m elev smooth | 5.6 | −3.5 | 5 |
| approximate `cf` + scalar `k_smooth` (no smoothing) | 5.8 | −0.5 | 7 |
| approximate `cf` + sheet `v_f` (`P_flat/P_avg`) | 7.2 | −0.5 | 4 |
| approximate `cf` + measured `v_f` | 8.2 | +6.7 | 4 |
| approximate + climb-fraction (`cf`) | 8.7 | +8.6 | 3 |
| approximate `off` + 2 m elev smooth | 10.2 | +9.9 | 5 |
| approximate `off` (baseline) | 19.3 | +19.3 | 2 |

*(Entry 11, 2026-07: a general review turned up several small code bugs — a gated flat-speed
computation, compressed-timestamp FIT recovery, a signed-drag fix — that shifted these numbers by
≤0.3 pp, except "measured `v_f`" which moved more (7.5→8.2) because the flat-speed gate itself
changed. See Entry 11.)*

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
  [`censo_compare.mjs`](../data/activities/censo_compare.mjs)) — [`9fc247b`](../data/activities/censo_compare.mjs)
- **Entry 10** (São Paulo ε hypothesis test, [`eps_sp_test.mjs`](../data/activities/eps_sp_test.mjs)) — `707c584`
- **Entry 11** (general review: code fixes + honesty corrections across engines, parsers, and
  every downstream number) — `906de11`
- **Entry 12** (second rider: P. Paz's Strava export, [`ppaz_inventory.mjs`](../data/activities/ppaz_inventory.mjs) +
  [`ppaz_compare.mjs`](../data/activities/ppaz_compare.mjs)) — `2148deb`
- **Entry 13** (time model tested on all three datasets, [`time_compare.mjs`](../data/activities/time_compare.mjs)) — `eeb38cd`
- **Entry 14** (third rider JAAM + a framing correction: P. Paz/JAAM are *independent* riders, not
  collective members, [`jaam_inventory.mjs`](../data/activities/jaam_inventory.mjs) +
  [`jaam_compare.mjs`](../data/activities/jaam_compare.mjs)) — this commit
- **Entry 15** (independent per-rider CdA/C_rr/mass + per-activity wind estimation,
  [`cda_estimate.mjs`](../data/activities/cda_estimate.mjs) +
  [`param_fit.mjs`](../data/activities/param_fit.mjs)) — `1d4eb2c`
- **Entry 16** (fitted rider physics vs assumed; the author's full Strava export as a fourth dataset,
  [`danlessa_inventory.mjs`](../data/activities/danlessa_inventory.mjs) +
  [`danlessa_compare.mjs`](../data/activities/danlessa_compare.mjs) + `*_CDA`/`*_CRR` overrides) — `736f33f`
- **Entry 17** (a regime-decomposed closed form E_new = E_flat + E_climb + E_descent, and a totals
  variant E_new2, tested vs the champion on all five corpora,
  [`regime_compare.mjs`](../data/activities/regime_compare.mjs)) — this commit
- **Entry 19** (the app's usual DEM: v2Edge on the deployed IGC-SP 5 m raster vs its 30 m resample,
  censo rides, [`igc_resolution_test.mjs`](../data/activities/igc_resolution_test.mjs)) — this commit
- **Entry 18** (correction: R1a is NOT the deployed sampasimu cost — dead-clamp proof + Jensen
  sign flip + R1d pre-registration and results (the Jensen prediction fails to a resolution effect;
  the bias-trade law claims R1d too),
  [`verify_v2edge_clamp.mjs`](../data/activities/verify_v2edge_clamp.mjs) +
  [`regime_compare.mjs`](../data/activities/regime_compare.mjs)) — this commit

---

## 2026-07-06 — Entry 19: the app on its usual DEM — v2Edge on the deployed IGC-SP 5 m raster vs a 30 m resample

*Prompt (Danilo): "most of the time we use IGC-SP DTM which has 5 m resolution — is this a
concern?" (after Entry 18's R1d showed v2Edge's grade-local ε collapses at fine sampling).
Test it on the deployed raster itself: sampasimu's `dem/sampa_geral.tif` — IGC-SP-derived,
WGS84, ~5 m pixels, covering the São Paulo censo bbox. Danilo: use `sampa_geral.tif`, which
has been VALIDATED, not the wider-coverage `mdt_igc_2010.tif` (known QA issues in several
regions).*

### Pre-registration (declared before running)

**Question.** Entry 18's R1d found v2Edge ties the champion at ~30 m sampling but over-charges
at 5 m — on *recorded-track* profiles, where fine grades are partly baro/GPS noise. The app's
usual input is a smooth surveyed 5 m DTM. Does the resolution over-charge transfer to the
deployment, and how big is it?

**Stakes (Danilo).** sampasimu is the main instrument of **Sampa 300 Quilojaules** (*A Cidade
de 300 kJ*, `initiative-300kj-city`): the mission measures whether a super-majority of
metropolitan São Paulo can reach each other and essential services within a **300 kJ
round-trip energy budget** over real terrain, using the app's synthetic energy fields for
what's possible / current / could be done. A systematic high bias on the deployed 5 m DEM
therefore *understates the city's measured accessibility* (the 300 kJ frontier shrinks), and
the descent-credit distortion moves where the frontier sits — so the bias magnitude quantified
here propagates directly into the mission's headline measure, not just into per-ride kJ.

**Data.** The clean censo rides (Entry 9's filters, verbatim) whose tracks fall inside
`sampa_geral.tif` with ≥99% valid samples. *Amendment (Danilo, pre-results): also include the
P. Paz, JAAM, and author-full (danlessa) clean power rides inside the same coverage — censo
rides are GROUP urban rides (drafting, stop-go), so the three independent riders' individual
rides are the better-isolated corpus. Each rider keeps their own frozen physics and per-corpus
ε rule exactly as in `regime_compare.mjs`. The censo endpoint stays as declared; the pooled
independent-rider rides become a co-primary for the same endpoint.* Three profile sources per ride, each built by
arc-length-resampling the GPS track and sampling the raster bilinearly at those points:
(a) **baro** — the recorded elevation (harness baseline / anchor); (b) **igc5** — the deployed
5 m raster at 5 m steps (deployment-faithful); (c) **igc30** — the same raster warped to ~30 m
(6× native pixel, `-r average`) at 30 m steps (the R1d sweet-spot regime). *Amendment (Danilo,
pre-results): add (d) **fabdem30** — the FABDEM V1-2 tile (S24W047, from the collective's
`telhas.pedalhidrografi.co/fabdem/` server) at 30 m steps — the globally-available reference
source, connecting this entry to Entry 6's k_DEM axis: it answers what the app would get on
the free global DEM instead of the local survey, and whether igc30 ≈ fabdem30 (Entry 6 found
the two bare-earth sources within ~6% on ascent).*

**Models per profile.** The deployed **v2Edge walk** (Entry 18's R1d realisation, code reused
verbatim from `regime_compare.mjs`) and the **R0 champion** (smooth cf + 2 m deadband, censo ε
rule = flat 0.20), both vs measured `∫P·dt`.

**Primary endpoint.** Paired med |Δ%| and signed bias of **v2Edge@igc5 vs v2Edge@igc30**.

**Predictions.** (P1) igc5 over-charges relative to igc30 (positive signed-bias gap) via two
additive mechanisms: finer grades → grade-local ε collapse (less descent credit), and roller
inflation of `β·h₊` (Entry 6). (P2) The gap is SMALLER than R1d's raw-baro 5 m catastrophe
(censo 12.3%) because a surveyed DTM's 5 m grades are mostly real, not noise. (P3) R0 on the
same profiles degrades less from igc30→igc5 than v2Edge does (its ε is aggregate; only the
`β·h₊` inflation hits it). **Decision rule for the app:** signed-bias gap (v2Edge@igc5 −
v2Edge@igc30) > ~3–4 pp ⇒ the static ~30 m pre-smoothing mitigation goes on sampasimu's
roadmap; < 2 pp ⇒ disclosure-only stands.

**Sanity gates.** Profile distance ≡ track distance; empirical `∫P·dt` matches the published
censo values for the same rides; igc5 sampled at 30 m steps ≈ igc30 (the warp adds averaging,
so approximate, not exact); per-edge cost > 0 everywhere (the Entry 18 dead-clamp assert);
DEM-vs-baro elevation RMS in the Entry-6 ballpark (~7–8 m shape RMS) as a sampling-correctness
check.

### Results

**Corpus & integrity.** 922 rides passed coverage (censo **58** of 62 clean; P. Paz **277**;
JAAM **181**; author full **406**; pooled independent riders **864**). Strict
all-points-inside-bbox + ≥99% valid samples; engines runtime-extracted from
`regime_compare.mjs` (byte-identical by construction); the full run executed twice with
**byte-identical output**. All sanity gates pass: the baro anchor reproduces
`regime_comparison.csv` on 912 matched rides to 5e-4 kJ; dead-clamp min pre-clamp edge
**+4.46 J** across all 922×4 profiles; igc5-sampled-at-30 m ≈ igc30 to 1.0% median energy
(residual = the warp's area averaging); profile ≡ track distance exact. One gate met only in
spirit: DEM-vs-baro shape RMS came out **3.7 m** median, below the Entry-6 7–8 m ballpark —
plausibly because Entry 6's RMS was FABDEM-vs-baro while this is the tighter IGC-vs-baro.

**Med |Δ%| / median signed Δ% vs ∫P·dt** (v2Edge on raw profiles at native step — the
deployment-faithful walk, ≡ Entry 18's `r1d5r` on baro; R0 = cf + 2 m deadband, per-corpus ε
rule, ε_geom recomputed per profile source):

| | v2@baro | v2@igc5 | v2@igc30 | v2@fab30 | R0@baro | R0@igc5 | R0@igc30 | R0@fab30 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| censo (58) | 12.0 / +12.0 | **22.1 / +22.1** | 12.3 / +12.3 | 15.8 / +15.8 | 4.7 / −1.1 | 5.6 / +3.4 | 4.4 / +1.0 | 6.1 / +0.1 |
| ppaz (277) | 6.4 / +6.1 | 9.0 / +9.0 | 8.1 / +8.1 | 18.8 / +18.8 | 5.2 / +4.4 | 6.6 / +5.5 | 6.2 / +5.1 | 8.4 / +8.2 |
| jaam (181) | 4.8 / −3.7 | 2.9 / −0.5 | 3.4 / −1.9 | 14.4 / +14.4 | 5.5 / −4.9 | 5.0 / −4.5 | 5.6 / −5.1 | 3.4 / −2.2 |
| danlessa (406) | 9.6 / +9.2 | 14.8 / +14.7 | 9.8 / +9.5 | 19.0 / +19.0 | 5.5 / +0.8 | 5.9 / +3.3 | 5.0 / +0.9 | 6.0 / +2.8 |
| **pooled (864)** | 6.9 / +5.4 | **9.6 / +9.5** | 7.1 / +6.3 | 17.6 / +17.6 | 5.4 / +0.7 | 5.8 / +2.3 | 5.4 / +0.7 | 5.8 / +3.1 |

**Primary endpoints — the resolution over-charge is real, and the decision rule is
TRIGGERED.** Paired v2Edge@igc5 vs @igc30: **censo** med per-ride signed gap **+9.44 pp**
(igc5 better on 3% of rides, sign & Wilcoxon p < 1e-4); **pooled riders** **+3.64 pp** (igc5
better 25%, p < 1e-4). Both exceed the pre-registered ~3–4 pp threshold ⇒ **the static ~30 m
pre-smoothing mitigation goes on sampasimu's roadmap** — and igc30 *is* that mitigation's
preview (an average warp is what pre-smoothing produces), so its measured benefit is already
on the table: censo 22.1 → 12.3, pooled 9.6 → 7.1 med |Δ%|. Per corpus the gap is
heterogeneous: danlessa +5.4 pp, ppaz +2.0 pp, and JAAM +1.4 pp where igc5 actually *wins* on
|Δ%| (55%, p = 0.16) — Entry 17's bias-trade law yet again: JAAM is the under-predicted
corpus, so the spurious extra energy lands as accuracy.

**Predictions.** **P1 confirmed**, with both mechanisms measured separately: roller inflation
(igc5 h₊ > igc30 h₊ on **919/922** rides; censo median +14%) and ε collapse (implied
drop-weighted ε from the walk: censo 0.219@igc5 vs 0.255@igc30; pooled 0.414 vs 0.456).
**P2 REFUTED for censo**: the surveyed 5 m DTM is *worse* than the recorded baro (v2@baro
12.0 vs v2@igc5 22.1) — real survey micro-relief that graded roads smooth away gets charged
as if ridden; P2 holds for the rider corpora (gaps 1.4–5.4 pp, far from censo's 9.4).
**P3 confirmed**: R0's aggregate ε shields it — igc30→igc5 degrades R0 by 0.4–1.2 pp
(pooled 5.4 → 5.8) vs v2Edge's 2.5 pp (7.1 → 9.6).

**The base gap persists at 30 m.** Even at its sweet spot the deployed walk over-charges
(pooled signed **+6.3%**, censo **+12.3%**) while R0 sits at +0.7 / +1.0 — Entry 18's R1d
conclusion (aggregate ε is the better *ride-energy* estimator) reproduces on real DEM
profiles. The resolution mitigation removes the incremental 3.6–9.4 pp, not this base gap.

**Secondary — FABDEM is not an adequate substitute here; Entry 6 qualified.** Paired on the
same rides, fabdem30 is far worse than igc30 for the rider corpora: pooled med |Δ%| **17.6 vs
7.1** (fabdem better on 9%, p < 1e-4), median energy +10.4%, median h₊ **+57%** pooled and
**+101% / +135%** on P. Paz / JAAM — flat lowland rides accumulate FABDEM per-pixel noise as
rollers (a 27 km P. Paz ride: h₊ 99 m on igc30 vs 391 m on fabdem30) and v2Edge's grade-local
ε then amplifies the charge. Censo is the mild case (energy +2.2%, h₊ +1.6%). **Entry 6's
"two bare-earth sources agree within ~6%" was measured on 10 hilly longões and does NOT
generalize to flat urban terrain.** For the mission: the *validated local survey is
load-bearing* — the free global DEM would overstate ride energies by ~+18% median and shrink
the measured 300 kJ frontier drastically.

**Stakes readout (Sampa 300 Quilojaules).** At today's deployment (igc5) the pooled median
over-charge is **+9.5%** (censo group rides +22%) — the 300 kJ round-trip frontier is
materially understated. With the 30 m pre-smoothing the residual is +6.3% pooled (+12%
censo): better, and conservatively signed, but not neutral — the remaining lever is the base
v2Edge-vs-R0 gap, and closing *that* reopens the viewing≡routing requirement (per-edge ε vs
aggregate ε), so it is a product decision, not a patch.

*Deviations from the brief (all disclosed):* v2Edge walks RAW profiles (deployment-faithful;
makes the baro anchor ≡ `r1d5r`); ε_geom recomputed per profile source for the open corpora
(censo stays flat 0.20); engine reuse by runtime extraction + eval of `regime_compare.mjs`
(stronger than substring assertion); `sampa_geral.tif` has no declared nodata — un-surveyed
cells read 0, so validity = sample > 0.5 m; the RMS-gate note above. No subsampling anywhere.

Tooling: `node igc_resolution_test.mjs` (~15 min; needs `gdalwarp`/`gdallocationinfo`, the
sampasimu `dem/sampa_geral.tif`, and network for the FABDEM tile on first run; writes the
gitignored `igc_resolution_test.csv`).

---

## 2026-07-06 — Entry 18: correction — R1a is not sampasimu's realisation (the app's per-edge ε never clamps), and the Jensen sign flips

*Prompt (Danilo): implement Entry 17's recommendation in sampasimu, under two product
requirements — viewing energy ≡ routing energy (one number everywhere), and Dijkstra-fast
local edge costs. The pre-implementation audit refuted the premise instead; this entry records
the correction. No measured number changes — Entry 17's scoreboard and all its ride statistics
stand untouched.*

**What Entry 17 got wrong.** It treated `regimeComponents`' R1a — ONE ride-frozen ε (the
aggregate `clamp01(ε_geom − 0.13)`, or the flat 0.20) applied to every 5 m edge under
`max(0,·)` — as "the *sampasimu `v2Edge`* realisation", and read R1a's descent over-charge
(P. Paz 9.3 vs 7.3 med |Δ%|) as a concrete strike against the deployed app (§9.1). But the app
does something different: `v2Edge` recomputes ε **from each edge's own grade**,
`ε(s) = clamp₀₁(min(1, (α/β)/s) − 0.13)` with `s = |dh|/d`. The two constructions share only
the words "per-edge".

**The app's descent cost is provably positive — its clamp is dead code.** With
`α = aRoll + aAero`, the three regimes of ε(s):

- **gentle**, `s ≤ α/β`: ε saturates at `1 − 0.13 = 0.87` and `β·|dh| ≤ α·d`, so
  `e = α·d − 0.87·β·|dh| ≥ 0.13·α·d`;
- **middle**, ε ∈ (0, 0.87): the α parts cancel exactly, leaving `e = 0.13·β·|dh|`;
- **steep**, ε floored at 0: `e = α·d`.

Always strictly positive — the trailing `max(0, e)` in `v2Edge` (and its Rust port) is
unreachable, defensive-only code. This is not even a new result: it is exactly the
`descFloor = 0.13·α > 0` bound sampasimu's own A\* admissibility proof derives
(`energy-worker.js`). Numerically confirmed by
[`verify_v2edge_clamp.mjs`](../data/activities/verify_v2edge_clamp.mjs): a 1.78 M-combo sweep
over (dist, grade, mass, C_rr, CdA, P_flat, k_smooth ≤ 1 — which only widens the margin) finds
a global minimum pre-clamp cost of +4.1e-4 kJ, plus the middle-regime identity to 1e-12. By
contrast R1a's frozen ε̄ has no such protection: on a steep edge `ε̄·s > α/β` easily, the
pre-clamp cost goes negative, the floor fires, and credit that should net against gentler
stretches is destroyed. **The 9.3-vs-7.3 over-charge is a property of the frozen-ε-per-edge
construction, not of the deployed app.**

**And the sign flips.** The real difference between the app's grade-local ε and the champion's
aggregate ε_geom is a Jensen gap: `f(x) = max(0, x − 0.13)` is convex on [0, 1], so the
drop-weighted mean of `f(min(1, (α/β)/sᵢ))` (the app) is ≥ `f` of the drop-weighted mean (the
champion) — verified on 20 k random descent profiles (same script), with equality exactly on
constant grade. More `f` = more descent credit: **sampasimu mildly *under*-charges descents
relative to the champion**, the opposite direction of Entry 17's claim.

**What stands.** Entry 17's methodological lesson stands in full: evaluate closed forms on
totals, and a frozen aggregate ε applied per edge under a clamp genuinely over-charges
descents — all its measured numbers are untouched. What falls is only the attribution: §9.1
needs no softening on the app's account, and every "strike against sampasimu `v2Edge`" should
read "strike against R1a's frozen-ε construction". Inline corrections added to Entry 17 below
(Entry-14/15 style).

**Pre-registered next test — R1d, the app's *actual* realisation.** Whether grade-local ε is
empirically better or worse than the champion is now a genuine open question. Declared before
running: add **R1d** to `regime_compare.mjs` — per-edge over the same deadbanded 5 m profile
as R1a, edge cost = the verbatim `v2Edge` (roll always; aero charged iff `dh < climbThr·dx`,
so full flat aero on descents; `β·dh` uphill; grade-local ε downhill; no regime powers —
information budget identical to R0: `P₌` + geometry + the frozen −0.13). **Primary endpoint:**
med |Δ%| vs ∫P·dt on the 441 P. Paz rides, paired vs R0. Secondary: all five corpora + the
fitted-physics rerun (Entry 17's bias-sign machinery). *Prediction:* R1d tracks R0 closely
from slightly below (the Jensen extra credit), so it should edge R0 where R0 over-predicts
(P. Paz, assumed physics) and lose slightly where R0 under-predicts (JAAM). Sanity gates:
all-flat thresholds reduce to the raw v1 law; constant-grade descent ⇒ R1d ≡ R0 exactly (no
Jensen gap by construction); machine-assert per-edge cost > 0 everywhere (the dead-clamp
proof). Also run a 30 m-resampled profile variant as sensitivity: grade-local ε is
resolution-sensitive in a way the aggregate is not, and the deployment lives on a ~30 m DEM
grid.

*Process note.* The misattribution survived Entry 17's adversarial review because the harness
*named* its own construction after the deployment — every reviewer verified R1a against the
plan, and none diffed it against the deployed cost function. Meanwhile sampasimu's own
cross-repo audit (its v52) had verified the app's code as correct-to-spec, so each repo was
verified in isolation and the bridge between them — "R1a is what the app does" — was the one
unverified claim. Same cure as Entry 17's V&V note: put "is this the thing it's named after?"
to the code, not the prose.

### R1d results (same day) — the clamp is dead on real data, the Jensen prediction fails, and the bias-trade law claims another model

R1d ran as pre-registered (`regime_compare.mjs`, verbatim `v2Edge` walk; sanity gates all pass,
including **R1d ≡ R0 on a constant-grade descent to 1e-6** — so every real-data difference is grade
*variance*, not construction).

- **The dead-clamp claim holds on real data.** Across all 1 402 rides (and again under fitted
  physics), the minimum pre-clamp descent edge is **+4.6 J** (fitted: +3.9 J) — the deployed
  `max(0,·)` never fired once on ~5 800 ride-profiles' worth of real edges. The R1a-style credit
  destruction genuinely cannot happen in the app.
- **Pre-registered endpoint (P. Paz, assumed): R1d loses** — **7.1%** vs R0 **5.8%** (R1d better on
  27%, p < 0.001). Full scoreboard (med |Δ%|, R1d vs R0): longões **6.4 vs 6.7** (R1d wins), censo
  4.7 vs 4.6 (tie), P. Paz 7.1 vs 5.8 (loses), JAAM **4.5 vs 5.5** (wins, 75%, p < 0.001),
  author 7.1 vs 6.3 (loses, 44%).
- **The Jensen prediction FAILED — and the pre-registered sensitivity explains why.** The prediction
  said R1d sits *below* R0 (grade-local ε ⇒ more credit, by convexity). Empirically R1d sits **above**
  R0 on every corpus (median per-ride Δ +8 to +96 kJ): the champion's ε_geom samples grades on **30 m
  cells of the raw profile**, while R1d samples **5 m deadbanded edges** — finer grades are steeper
  grades, `ε(s)` collapses toward 0 on steep edges, and the *resolution* effect (less credit)
  overwhelms the *convexity* effect (more credit). Entry 18's own hedge ("grade-local ε is
  resolution-sensitive in a way the aggregate is not") turned out to be the headline, not the caveat.
  The resolution×smoothing grid confirms it: at the FABDEM-like **30 m grid R1d improves** almost
  everywhere (longões 5.6, P. Paz 6.8, author 6.6) and the deployment-faithful **30 m raw** splits
  honours with the champion (longões 6.5 vs 6.7, JAAM **4.2** vs 5.5, censo 6.1 vs 4.6, P. Paz 7.5 vs
  5.8) — while **5 m raw on urban baro tracks is catastrophic** (censo 12.3%: elevation noise reads
  as steep grades and destroys the credit). A happy accident for the deployment: v2Edge behaves
  *best* near the 30 m DEM grid it actually runs on.
- **The bias-trade law claims R1d too.** Under fitted physics (all champion biases negative), R1d
  flips to winning everywhere: P. Paz **71%** (6.4 vs 7.0), JAAM 63%, author **81%** (9.8 vs 12.1).
  Same rides, same model, the winner follows R0's bias sign — R1d's extra energy is not climb aero
  (it uses the same cf gate as R0) but *reduced descent credit from resolution*, and it obeys the
  same law: whatever direction a variant shifts total energy, it wins exactly where the champion's
  parameter bias points the other way.

**Verdict.** The app is vindicated where Entry 17 indicted it (the clamp is dead code; no frozen-ε
over-charge), but its grade-local ε is **not better than the champion's aggregate** — at the
harness's 5 m grid it is strictly worse (a resolution artifact of ε(s), exactly as the physicality
argument predicts: grade-local recovery is not meaningful at scales where the grade itself is
noise), and at its native ~30 m grid it roughly ties. For *ride energy*, the champion's aggregate ε
stands; for *routing*, v2Edge stands too — running at the resolution where its grade-local ε is
least wrong. The remaining practical note for sampasimu: avoid feeding v2Edge profiles much finer
than ~30 m (the credit collapses), and the k_DEM/§8.7 source-bias axis is separate from and additive
to this resolution effect.

Tooling: `node verify_v2edge_clamp.mjs` (self-contained, no ride data; exits non-zero on any
violation); `node regime_compare.mjs` (R1d in the scoreboard + the Entry-18 endpoint block, Jensen
check, resolution×smoothing grid, and the dead-clamp assert; fitted rerun via the Entry-17 envs).

---

## 2026-07-06 — Entry 17: a regime-decomposed closed form — does splitting the ride by slope beat the champion?

*Prompt (Danilo): test an alternative closed form `E_new = E_flat(x₌;P₌) + E_climb(x₊;P₊) +
E_descent(x₋;P₋)` — decompose the ride by a climb/descent slope threshold and let each regime draw
the base law with its own regime power; ideally link the threshold to where β (and β·ε) dominates α.
Plus a totals variant `E_new2 = E_flat(d=x,P₌,h=0) + E_climb(d=0,P₊,h₊) + E_descent(d=0,P₋,h₋)`. Also
treat the author's full export as a full test alongside P. Paz and JAAM.*

The champion closed form (§3.2) is single-regime with patches: one flat reference speed, aero **zeroed**
on climbs (the `cf` α-split), a 2 m deadband, and a lumped descent credit ε. This entry tests whether a
structurally cleaner *segment* decomposition — each regime evaluating the base law with its **own** power
(flat `flatEqSpeed(P₌)`; climb aero at the quasi-steady `v_c(P₊)`; descent from the `P₋`+gravity
equilibrium) — is any better. Harness: `regime_compare.mjs` (engine block verbatim from `time_compare.mjs`,
ppaz block asserted as a substring; new logic = `regimeComponents`/`r0Champion`/the drivers only).

**The two models, written out.** Both build on the base per-metre coefficients
`α_r = C_rr·mg/k_eff` (roll), `α_a(v) = ½ρC_dA·(v+w)|v+w|/k_eff` (aero at speed `v`), `β = mg/k_eff`
(gravity), and `α(P) = α_r + α_a(flatEqSpeed(P))`. Each ride is a chain of edges `i` with horizontal
length `dxᵢ`, rise `dhᵢ`, slope `sᵢ = dhᵢ/dxᵢ`, `secᵢ = √(1+sᵢ²)`, `sinθᵢ = sᵢ/secᵢ`, `cosθᵢ = 1/secᵢ`.
Regime powers `P₌, P₊, P₋` (flat/climb/descent, from the 30 m-window classifier) and thresholds
`(climbThr, descThr)` default `(+2%, −1.5%)`. ε is the frozen `clamp₀₁(ε_geom − 0.13)` (open) or `0.20`
(urban).

*(A) E_new — the segment decomposition.* Classify each edge by slope; each regime evaluates the base
law over **its own edges** with **its own** reference speed. The reference speeds are all *modelled*
(never measured): flat `v₌ = flatEqSpeed(P₌)`; climb `v_c(i) = min(v₌, k_eff·P₊/(C_rr·mg·cosθᵢ + mg·sinθᵢ))`;
descent `v₋(i) = descentEqSpeed(P₋, |sᵢ|)` (the `P₋`+gravity aero-equilibrium, capped at `v_max`).

```
E_new = E_flat + E_climb + E_descent,   with regime(i) = climb  if sᵢ ≥ climbThr
                                                        descent if sᵢ ≤ descThr
                                                        flat    otherwise
  E_flat   = Σ_{flat i}   [ α_r·dxᵢ + α_a(v₌)·dxᵢ + β·dhᵢ ]            (dhᵢ signed; no floor)
  E_climb  = Σ_{climb i}  [ α_r·dxᵢ + α_a(v_c(i))·dxᵢ + β·dhᵢ ]        (dhᵢ > 0)
  E_descent (one of three, never mixed):
    R1a  = Σ_{desc i} max(0,  α_r·dxᵢ + α_a(v₌)·dxᵢ − ε·β·|dhᵢ| )                 (base-law ε clamp)
    R1b  = Σ_{desc i} P₋ · (dxᵢ·secᵢ / v₋(i))                                     (= P₋·t₋; no ε)
    R1c  = Σ_{desc i} max(0,  C_rr·mg·cosθᵢ + ½ρC_dA·(v₌+w)|v₌+w| + mg·sinθᵢ )·dxᵢ·secᵢ / k_eff
                                                     (leg force-deficit at flat cruise; sinθᵢ<0; no ε, no P₋)
```

*(B) E_new2 — the totals decomposition (Danilo).* Read the base closed form `E(d, P, h) = α(P)·d + β·h`
off three whole-ride totals, with `d=0` on the climb/descent components:

```
E_new2 = E_flat(d=x, P=P₌, h=0) + E_climb(d=0, P=P₊, h=h₊) + E_descent(d=0, P=P₋, h=−h₋)
       = α(P₌)·x               + β·h₊                     − ε·β·h₋
       = α_r·x + α_a(v₌)·x  +  β·h₊  −  ε·β·h₋             (aero over the WHOLE distance x — the 'off' mode)
```

`d=0` makes the climb/descent **powers drop out** (they would only scale a zero distance), so `β·h₊`
carries the climb (`E_climb ≈ P₊·t₊ ≈ β·h₊`, pure lift) and `−ε·β·h₋` the descent credit. `x, h₊, h₋`
are the deadband-profile totals. This is exactly the v1 base law with aero un-split — hence its kinship
to the article's `off` baseline.

**Totals vs per-edge — and how the champion evaluates (Danilo's question).** A *closed form* should
evaluate each regime's formula **once on its aggregate totals** (`x_r, h₊_r, h₋_r`, mean grade, regime
power), not sum a per-edge walk. This matters, because **the champion R0 evaluates on totals**: in
`approxComponents`, `roll = α_r·X`, `aero = α_a·x_nonclimb`, `climb = β·h₊`, and the descent credit
`ε·β·h₋` are all *aggregate* quantities — the edge loop only *measures* `X / x_climb / h± / hminus`;
there is no per-edge clamp, no per-edge `v_c` (its climb term is gravity-only), and ε is itself the
drop-weighted `ε_geom`. So E_new is evaluated **two ways**, and the *totals* form is the apples-to-apples
comparison: **`regimeTotals`** classifies edges once to get the regime aggregates, then evaluates each
regime's law once (climb aero at a single `v_c(s̄₊)`; the descent clamp/equilibrium on the descent
*total* at `s̄₋`). The per-edge **`regimeComponents`** is the *sampasimu `v2Edge`* realisation (article
§9.1) — it clamps `max(0,·)` and re-solves `v_c`/`v₋` per 5 m edge. *(Corrected in Entry 18: R1a is
NOT the app's realisation — it applies one ride-frozen ε per edge, while the deployed `v2Edge`
recomputes ε from each edge's own grade, and its clamp provably never fires.)* The two are *identical on the linear
terms* (roll, gravity, flat aero — verified: a constant-grade climb gives totals ≡ per-edge to 1e-3) and
diverge only on the nonlinear `v_c`/`max(0,·)`/`v₋`; the per-edge `max(0,·)` clamps steep-descent credits
to zero edge-by-edge (it *cannot* net them), so it systematically **over**-charges descents relative to
the totals form.

**Why totals is not just convenient but *physically* right for ε (Danilo's point).** ε is not a local
edge property — *by construction* it is the **drop-weighted aggregate** `ε = Σ ε(sᵢ)·h₋ᵢ / H₋` (§4.1),
and its physical content is a *bundle* of whole-descent phenomena — the excess aero of descending faster
than `v_f`, **plus braking**, minus any descent pedalling — averaged over the descent. Those phenomena are
not resolvable at a 5 m edge (braking on a corner is repaid by gravity two edges later; the −0.13 offset
is a *ride-level* braking/pedalling residual). So applying ε **per edge** discards exactly the physicality
that defines it — it treats a lumped, behaviourally-set average as if it were a local coasting law. The
totals form is therefore the faithful realisation, and the empirical descent over-charge of the per-edge
variant (P. Paz 9.3 vs 7.3) is the symptom, not the cause. This **contests the article's §9.1 framing**,
which calls the per-edge `v2Edge` form "the more physically defensible" (it never lets a shallow stretch
average out a cliff): that argument holds for a *routing cost* that must be additive per edge, but for
*estimating a ride's energy* the aggregate ε is the physical one — §9.1 should be softened to say the
per-edge form is a routing-driven realisation, not the more physical one. (sampasimu keeps per-edge
because a Dijkstra edge cost must be local; that is a deployment constraint, not a claim about ε.)
*(Qualified in Entry 18: the totals-vs-per-edge lesson stands for the frozen-ε R1a tested here, but the
§9.1 softening is NOT needed on the app's account — the deployed `v2Edge` uses a grade-local ε whose
clamp never fires, and it sits on the credit-generous side of the aggregate, not the over-charging one.)*

**Design & the two traps.** Three firewalled descent variants (never mixed): **R1a** keeps the base-law
per-edge ε clamp `max(0, α_r·dx + α_a(v₌)·dx − ε·β·|dh|)`; **R1b** = `P₋·t₋` over the *modelled* descent
equilibrium speed (no ε); **R1c** = leg force-deficit held at flat cruise speed (no ε, no P₋). Danilo's
totals form is **R2** = `α(P₌)·x + β·h₊ − ε·β·h₋` with aero over the *whole* distance ('off' mode). Two
traps were guarded and adversarially verified clean: **(1) the P·t tautology** — every predicted regime
speed is modelled from power+physics, never measured, so `Σ P̄·t ≡ ∫P·dt` can't sneak in (measured regime
energies are used *only* as the per-regime attribution denominators); **(2) descent double-count** — ε and
an explicit descent-aero charge never co-occur in one variant. Sanity gates pass (both `regimeComponents`
and `regimeTotals`): all-flat thresholds reduce to the raw v1 law exactly; Σ components ≡ E; flat anchor
R1a = R0 = canonical; pure climb E_climb ≥ PE floor; **constant-grade climb: totals ≡ per-edge to 1e-3**
(confirming the two forms differ only on nonlinearities). R0 and canonical reproduce the published
harnesses (longões canonical 5.1, JAAM 5.4; P. Paz R0-smooth 5.8 / poor-man 4.9 — all exact). Two bugs
were caught and fixed en route (canonical called without `pw.climbThr/descThr` → flat power everywhere;
`beta` undefined in the driver).

**Pre-declared primary endpoint (P. Paz, per-edge R1a vs R0, paired): the regime model LOSES** — R1a
**9.3%** median |Δ%| vs R0 **5.8%**, better on only 20% of the 441 rides (p < 0.001). *But that number is
inflated by the per-edge clamp.* On the apt **totals** closed form the loss shrinks a lot: **R1a-totals
7.3%** (32% win) and the best regime variant **R1c-totals 6.2%** (38%) — still short of R0's 5.8% on the
endpoint, but no longer a rout. (The pre-registered endpoint stays the per-edge R1a; the totals form is
reported as the fairer, champion-matched comparison, not a moved goalpost.)

**The win/loss is rider-dependent — a *bias trade*, not an accuracy gain.** Scoreboard, median |Δ%|
(signed bias in parens for R0); regime variants shown as **totals** (the closed form), with per-edge R1a
in the last column for contrast:

| corpus | R0 champ | canonical | R1a-t | R1b-t | R1c-t | R2 totals | R1a per-edge |
|---|--:|--:|--:|--:|--:|--:|--:|
| longões | 6.7 (−2.1) | 5.1 | 6.1 | **4.1** | 6.5 | 5.6 | 4.6 |
| censo | 4.6 (−0.8) | 6.5 | **4.2** | 5.9 | 6.8 | 4.4 | 4.5 |
| **P. Paz** | **5.8 (+4.3)** | 6.7 | 7.3 | 8.5 | **6.2** | 10.9 | 9.3 |
| JAAM | 5.5 (−4.7) | 5.4 | 4.6 | **4.1** | 4.9 | 4.2 | **3.9** |
| author full | 6.3 (+0.1) | 6.3 | **6.4** | 7.2 | **6.4** | 8.3 | 7.6 |

Head-to-head vs R0 (paired, totals): **P. Paz** — regime variants lose (R1a-t/R1c-t win 32/38%, p < 0.001);
**JAAM** — regime variants **win** (R1a-t/R1c-t 79/72%, p < 0.001); **author full** — R1a-t and R1c-t both
**tie** (54% win, Wilcoxon p = 0.15 / 0.01). The pattern is mechanical: **the regime form adds a
near-constant ~+4.6 pp energy shift** (the climb aero at `v_c(P₊)` the champion zeroes), so it helps
exactly the corpora where R0 *under*-predicts (longões −2.1, JAAM −4.7, censo −0.8 → wins) and hurts where
R0 *over*-predicts (P. Paz +4.3) or is already unbiased (author +0.1 → ties). The sign of R0's own bias
predicts the outcome (pooled corr(sign(R0 bias), |R1a|−|R0|) ≈ 0.78). Because that bias sign is itself
rider-dependent (and driven by the assumed-CdA error of Entry 16), the regime model *cannot* be a
universal win — the endpoint's verdict is contingent on which rider's bias sign was chosen. **The per-edge
realisation is uniformly worse than the totals form on the over-predicted corpora** (P. Paz 9.3 vs 7.3):
its `max(0,·)` clamp cannot net a cliff against a shallow stretch, so it over-charges descents — a concrete
strike against the sampasimu `v2Edge` per-edge ε on descent-heavy routes (article §9.1). *(Corrected in
Entry 18: the strike lands on R1a's frozen-ε construction only — the deployed sampasimu cost recomputes
ε per edge from local grade, never clamps, and Jensen-sides toward MORE descent credit than the champion.)*

**The causal test — flip the bias, flip the winner (fitted-physics rerun).** The bias-trade reading was,
so far, correlational. Entry 16's machinery makes it causal: swap in each rider's Entry-15 *fitted*
constants (`PPAZ_M=80.7 PPAZ_CDA=0.26 PPAZ_CRR=0.0053`, `JAAM 103.2/0.323/0.0108`, `DANLESSA
71.2/0.256/0.0072`) and R0's bias signs move — P. Paz *flips* to under-prediction (+4.3 → −6.2; the fitted
CdA removes drag Entry 16 showed was over-stated), JAAM shrinks (−4.7 → −3.5), the author swings hard
negative (+0.1 → −10.9; the fitted aero-position CdA under-predicts whole rides — Entry 16 Part C
replaying). **Pre-registered prediction: the regime outcome should track the *new* bias signs, not the
riders.** It does, 6-for-6:

| corpus | R0 bias, assumed → fitted | regime (R1a-totals) vs R0, assumed → fitted |
|---|---|---|
| P. Paz | +4.3 → **−6.2** (flips) | **loses (32%) → wins (71%, p < 0.001)**; 6.4 vs 7.0 med |
| JAAM | −4.7 → −3.5 (shrinks) | wins (72%) → wins (72%), median margin 0.9 → 0.1 pp |
| author full | +0.1 → **−10.9** | tie (54%) → wins (83%); 11.6 vs 12.1 med |

Same rider, same rides, same model — only the physics constants changed, and the winner followed the bias
sign every time. This **upgrades the bias-trade from interpretation to demonstrated mechanism**: the
regime decomposition is a roughly constant *positive energy padding* (the climb aero the champion zeroes),
and it "wins" precisely when the parameter set under-predicts. It is not a structural accuracy gain — with
well-chosen constants (the author corpus under assumed physics, bias +0.1), the champion is unbeaten.
(Note the fitted run is *not* the better configuration overall — author accuracy degrades 6.3 → 12.1
because param_fit's CdA is the aero-position value; here it serves only as the lever that moves the bias.)

**Information asymmetry — stated both ways (it strengthens the negative).** The R1 variants **and canonical** consume
all three regime powers; the champion *closed form* uses only `P₌` + geometry + the frozen ε (its climb
term is gravity-only `β·h₊`, verified). So R1 **fails to beat R0 despite strictly more information**. And
canonical *also* uses three powers yet only ties R0 — so the extra power inputs are not what would help;
R1a's whole effect is the climb-aero charge. (We do **not** claim "R1 ≈ the forward sim": the ~0.97
per-ride correlation is non-discriminating — every pair correlates ~0.97 — and by *bias and accuracy*
canonical tracks R0, not R1a.)

**The threshold idea (link the boundary to α/β) partly holds.** The flat-resistance grade
`α/β = C_rr + ½ρC_dA(v_f+w)²/(mg)` does land near the 2% default and **orders with rider speed**: censo
1.42% (v_f 16.5 km/h) < author/longões ~1.95–1.98% < JAAM 2.29% < P. Paz 2.49% (fast/light). But the
**symmetric ±α/β adaptive threshold beats neither the default nor the best fixed cell** in any corpus,
because the optimal thresholds are *asymmetric*: the descent side wants to be steeper (−3%) on the fast
open corpora (longões, P. Paz, author) — pushing gentle descents into the flat regime — while censo
matches −α/β (−1.5) and JAAM prefers a shallower −1.0. So α/β is a decent *scale* for the threshold but
does not, symmetric, retro-justify the default; the descent boundary is not universal.

**Per-regime attribution (diagnostic, per-edge R1a).** The R1a component vs the measured ΣP·dt in that
regime: climb 10–12%, flat 4.5–17.6%, **descent 43–61% — the worst in every corpus**. The descent
sub-model is where the regime form struggles most; the lumped-ε champion is hardest to beat there.
*Caveat:* the
modelled components classify by 5 m-edge slope on the deadband profile while the measured `eM*` use the
30 m-window point classifier on raw points, so part of this gap is partition mismatch, not pure
descent-model error — it never enters the scoreboard.

**Verdict.** The regime-decomposed closed form — evaluated properly on totals, matching how the champion
works — is **competitive but not a robust improvement**. It *loses the pre-declared P. Paz endpoint*
(best totals variant R1c-t 6.2% vs R0 5.8%), **ties** on the unbiased author corpus (6.4 vs 6.3), and
**wins** only where the champion under-predicts (cleanly out-of-sample on JAAM, 79%). The win/loss is a
**bias trade**: the regime form adds the ~+4.6 pp climb aero the champion zeroes, so R0's own bias sign
decides the outcome. Its structural cleanliness buys nothing the champion's "conveniences" don't already
buy: **zeroing climb aero and lumping descent recovery into ε do real bias-cancellation work**, and adding
the physics back per-regime trades one bias for another. Two concrete lessons survive: **(1)** the
**totals** evaluation is the right one — the per-edge `max(0,·)` realisation (sampasimu `v2Edge` *— not
so, see Entry 18: the app's grade-local ε never clamps; this describes R1a's frozen-ε form only*)
over-charges descents by clamping cliffs it cannot net (P. Paz 9.3 vs 7.3), a strike against per-edge ε on
descent-heavy routes (§9.1); and **(2)** `α/β` is the natural *scale* of the regime threshold (it orders
with rider speed and sits at the 2% default), even though a symmetric adaptive rule does not pay because
the optimum is asymmetric. Danilo's totals form R2 adds the *most* energy, so it is weakest on the
over-predicted corpora — re-confirming the α-split (the article's 19.3 → 8.7% climb-aero fix) rather than
replacing it. The fitted-physics rerun settles the mechanism causally: same rides, same model, different
constants → the winner follows R0's bias sign 6-for-6.

*Process note (verification vs validation).* The adversarial review verified the harness was **built
right** (code, stats, traps) but missed both conceptual errors — the per-edge-vs-totals category error and
ε's aggregate physicality — because the plan itself specified per-edge; reviewers inherit the plan's blind
spots. Both corrections came from the domain owner. The classic V&V split, and the known cure: validation
("the right thing?") is best done by stakeholders; future entry plans should put the "is the comparison
apples-to-apples with the champion's own evaluation style?" question to the owner *before* execution.

Tooling: `node regime_compare.mjs` (all five corpora; `SANITY=1` runs the synthetic gates;
`<RIDER>_M`/`_CDA`/`_CRR` envs swap in fitted physics — the causal rerun above is
`PPAZ_M=80.7 PPAZ_CDA=0.26 PPAZ_CRR=0.0053 JAAM_M=103.2 JAAM_CDA=0.323 JAAM_CRR=0.0108 DANLESSA_M=71.2 DANLESSA_CDA=0.256 DANLESSA_CRR=0.0072 node regime_compare.mjs`).
Writes the gitignored `regime_comparison.csv`.

---

## 2026-07-04 — Entry 16: does it hold with the *real* rider physics? + the author's full export

*Prompt (Danilo): (a) test how the article conclusions change if we use the Entry-15 *fitted* rider
physics instead of the generic assumed constants — that's our best guess for riders 2–3; (b) then, add
the author's own full Strava export (`strava_danlessa`, 1597 power rides) and analyse it as another
rider dataset.*

Two connected robustness checks. Tooling: `PPAZ_CDA`/`PPAZ_CRR` (and `JAAM_`, `DANLESSA_`) env overrides
on the compare harnesses swap the generic assumed drag/rolling for each rider's Entry-15 fitted values;
`danlessa_inventory.mjs` + `danlessa_compare.mjs` add the author's full export (verbatim engines).

### Part A — fitted physics vs assumed (riders 2–3)

The article feeds riders 2–3 the *generic* CdA 0.40 / C_rr 0.008. Entry 15 gives their own best estimates
(P. Paz CdA 0.26 / C_rr 0.0053 / m 80.7; JAAM 0.323 / 0.0108 / 103.2). Rerunning the energy + ε tests
with the fitted set:

| | assumed | fitted | verdict |
|---|--:|--:|:--|
| **P. Paz** canonical med \|Δ%\| (bias) | 6.8% (+5.0) | 7.5% (−6.9) | accuracy robust, **bias flips** |
| **P. Paz** frozen-ε RMS vs in-sample (s̄≥3%) | 0.091 vs 0.139 | 0.083 vs 0.086 | **35% win → tie** |
| **P. Paz** offset gap (med ε_coast − ε_bal) | 0.12 | 0.19 | shifts |
| **JAAM** canonical med \|Δ%\| (bias) | 5.4% (−5.0) | 4.9% (−4.0) | robust |
| **JAAM** frozen-ε RMS vs in-sample (s̄≥3%) | 0.091 vs 0.086 | 0.089 vs 0.086 | tie → tie (robust) |
| **JAAM** offset gap | 0.13 | 0.13 | robust |

- **The energy law's accuracy (~4–7% median) is robust to the parameter choice** for both riders — but
  fitted physics does *not* improve it. On P. Paz the bias flips +5% → −7%: the generic 0.40 was actually
  *closer* to the whole-ride-optimal CdA than the flat-fit 0.26 (see Part C for why).
- **JAAM is fully robust** because its fitted CdA↓ (0.40→0.32) and C_rr↑ (0.008→0.011) nearly cancel in
  α = (C_rr·mg + ½ρCdA·v_f²)/k_eff, so v_f (29.2 km/h), ε_geom (0.61), ε_bal, the frozen-ε tie, and the
  0.13 offset all hold.
- **P. Paz's headline "35% ε win" does NOT survive.** With the correct (lower) CdA, α drops, so measured
  ε_bal drops (0.36→0.14) and the geometric estimator no longer beats his own best flat constant — it
  **ties** (0.083 vs 0.086), exactly like JAAM. The 35% figure was inflated by the assumed-high CdA pushing
  the in-sample constant far from the geometric estimate. **This qualifies §8.6 of the article** (see
  below): under best-guess physics both independent riders *tie*, a cleaner and more honest story — the
  geometric-ε skill adds little beyond a flat constant for either. (Caveat: the −0.13 offset was calibrated
  on rider 1's *assumed* physics, so mixing fitted physics for riders 2–3 is a mild inconsistency; but
  rider 1's fitted CdA ≈ assumed for the *longões*, so the offset itself barely moves — Part B checks it.)

### Part B — the author's full Strava export as a fourth dataset (danlessa)

`strava_danlessa`: **2880 FIT files, 1597 power rides** (782 ≥ 20 km), 2017-08 → 2026-06, altitude 39–2852 m,
terrain to 91 m/km. The author is rider 1 (the *calibration* rider), so this is **not** an out-of-sample
transfer test — it is a large-sample validation of the *machinery*. Flagged in-sample-ish in the harness.

- **`param_fit`** (98 clean activities): mass **71.2 kg** ✓, CdA 0.256, C_rr 0.0072, wind ~3 km/h.
- **`danlessa_compare`** (621 clean rides, assumed physics): implied mass **74.5 kg** [IQR 67.6–80.8];
  canonical energy **6.1 % median at +0.1 % bias** (near-zero — the best-calibrated dataset, as expected
  for the calibration rider); smooth ε_geom 6.2 % (−0.3 %); frozen-ε RMS **0.090 vs in-sample 0.121** on
  210 real descents; **offset gap 0.13** (ε_coast 0.37 − ε_bal 0.24) — recurs exactly.
- **Mass validation — and the Entry-15 "over-read" retired.** Two independent methods land at **71–75 kg**
  against Danilo's known **≈ 73 kg**. The earlier author/longões estimate (79.8 kg, n=5) was *not* a bias:
  the longões are loaded ultra-distance **brevets** (extra gear/food/water ⇒ genuinely ~80 kg system),
  while the full export of normal training rides gives ~71–75 kg. The estimator tracks the actual loadout.
- The 0.13 offset and the frozen-ε win *do* hold here — but this is the calibration rider, so it confirms
  self-consistency, not independence.

### Part C — the connecting thread: fitted CdA sits ~35 % below the assumed 0.40

Across all riders the *fitted* CdA clusters **0.26–0.34** (P. Paz 0.26, JAAM 0.32, author 0.26), well under
the generic assumed 0.40. The likely cause: `param_fit` reads CdA from *fast, flat* samples — exactly where
a rider is most aerodynamic (tucked) or **drafting in a group** — so it recovers the aero-position CdA, not
the upright/solo average. That is why feeding CdA 0.26 into the *whole-ride* energy model under-predicts
(Part A, P. Paz bias +5%→−7%): the whole ride includes non-aero-optimal riding the flat-fit never saw.

**Net.** (1) The energy law's ~4–7 % accuracy is robust to assumed-vs-fitted physics. (2) JAAM's ε result
is fully robust; **P. Paz's 35 % ε win is not — it becomes a tie under best-guess physics**, matching JAAM
(article §8.6 needs this qualification). (3) The author's full export validates the mass machinery (71–75 vs
known 73; longões was brevet loadout) and the 0.13 offset, in-sample. (4) The fitted CdA is systematically
the aero-position value (~0.26–0.34), below the generic 0.40 — informative, not a bug.

Tooling: `PPAZ_M=80.7 PPAZ_CDA=0.26 PPAZ_CRR=0.0053 node ppaz_compare.mjs` (and `JAAM_`, `DANLESSA_`);
`node danlessa_inventory.mjs && node danlessa_compare.mjs`; `node param_fit.mjs` (now 4 riders). All read
the gitignored exports, write gitignored CSVs.

---

## 2026-07-03 — Entry 15: independently estimating CdA, C_rr, mass and wind — what the data can and cannot give

*Prompt (Danilo): can we independently estimate CdA for P. Paz and JAAM? Then, over several
iterations: uphill segments are braking-free (the cleanest data); this is akin to virtual-elevation;
wind matters per activity; and finally a `/goal` — every dataset should yield per-activity CdA, C_rr,
wind and rider+bike mass within plausible ranges (author m 68–80 kg, CdA 0.28–0.45, C_rr 0.004–0.015;
P. Paz 72–90 / 0.25–0.45 / 0.004–0.015; JAAM 73–95 / 0.25–0.45 / 0.004–0.015; wind ±15/±10 km/h
single-direction, ±5 km/h circular).*

**Why this matters.** Entry 14 flagged JAAM's implied mass (101.7 kg) as implausibly high and
*guessed* it was a CdA misspecification. This entry tests that — and refutes it. Two tools:
[`cda_estimate.mjs`](../data/activities/cda_estimate.mjs) (the exploration of what fails and why) and
[`param_fit.mjs`](../data/activities/param_fit.mjs) (the working per-activity estimator). Engines
(`parseFIT`, `haversine`) are verbatim copies; the point builder `ptsWithGeo` is new because it must
keep lat/lon for **bearing**, which the verbatim `ptsFromFIT` discards. The author's longões (whose
model constants are themselves assumptions, not truth) serve as a method **anchor** throughout.

**What FAILS (and why — the useful negative results).**

- **Naive flat-power regression** `P·k_eff/v = C_rr·mg + ½ρCdA·v²` on flat samples: gives CdA < 0.
  Riders hold steady *effort*, not steady *power* — high flat speed pairs with low power (draft,
  tailwind, false downgrade), a negative confound that swamps the v² aero signal.
- **Coast-down / descent-terminal** (cadence = 0 ⇒ pure physics, no meter/drivetrain confound):
  also fails. Braking contaminates every descent (always extra deceleration), and differentiating
  GPS speed is pure noise — author anchor came out m ≈ 40 kg, CdA < 0.
- **Free 3-param climb energy-balance** (JAAM's braking-free-uphill insight: over a climb,
  `k_eff·∫P·dt = m·[gΔh+½Δv²] + C_rr·m·[gΔx] + CdA·[½ρ∫v³dt]`): recovers mass, but **CdA is
  unidentifiable** — climbs are slow (10–15 km/h) so the aero term has no leverage; the free CdA goes
  negative (CI spans 0) and drags C_rr up / mass down. On climbs `A ≈ grade·B`, so mass and C_rr are
  near-collinear too (separated only by grade range).

**What WORKS — key structural facts.**

- **Mass is C_rr/CdA-robust from braking-free climbs.** Fixing CdA anywhere in 0.25–0.45 moves the
  climb mass only ~4 kg per 0.10 CdA. So CdA is emphatically **not** what set JAAM's high mass —
  Entry 14's guess was wrong. At a nominal CdA = 0.35 the climb masses are P. Paz 81, JAAM 103,
  author 80 kg (anchor assumed 73; the method over-reads ~10%, see caveats).
- **Wind is the parameter that unlocks CdA** (Danilo's insight; this is virtual-elevation with a wind
  vector, à la Notio/Aerolab). A ride heading several directions under one wind vector
  `w = −(W_e·sinβ + W_n·cosβ)` shows a directional asymmetry in aero cost that identifies CdA *and*
  the wind together. `param_fit.mjs`: mass fixed at the rider level (from climbs), then **per activity**
  a **linearised 4-parameter regression** recovers (C_rr, CdA, CdA·W_e, CdA·W_n). *The linearisation is
  load-bearing* — dropping the small `w²` term makes the aero power linear
  (`½ρCdA·v³ − ρCdA·v²·(W_e sinβ + W_n cosβ)`), so CdA comes from the v³ term and the wind vector from
  the v²·sinβ / v²·cosβ direction terms. Keeping `w²` (the first version's grid over the full `(v+w)²`)
  created a **CdA↔wind degeneracy** — a synthetic-wind self-test injecting a known 4 m/s recovered
  15 m/s with CdA collapsing to ~0. The linearised fit passes that self-test (recovers the right axis,
  direction, and — after a per-rider attenuation de-bias — magnitude).

**Per-activity results (median over clean-fitting activities, r² > 0.4):**

| rider | mass (climbs) | CdA | C_rr | activities | target ranges |
|---|--:|--:|--:|--:|:--|
| **P. Paz** | 80.7 kg ✓ | **0.259** ✓ [IQR .22–.34] | 0.0053 ✓ | 123 (95 wind-usable) | 72–90 / .25–.45 / .004–.015 |
| **JAAM** | 103 kg ✓ | **0.322** ✓ [.30–.38] | 0.0107 ✓ | 27 | **93–107** / .25–.45 / .004–.015 |
| **author** (anchor) | 79.8 kg ✓ | **0.334** ✓ [.33–.37] | 0.0083 ✓ | 5 | 68–80 / .28–.45 / .004–.015 |

- **All four parameters (mass, CdA, C_rr, wind) land inside the target ranges for all three riders**,
  and the method **validates on the anchor**: the author's estimated CdA 0.33 against the 0.39 assumed
  in the model, C_rr 0.008 against the assumed 0.008. The wind vector is what made this possible — the
  climb-only and flat-power methods could not.
- **Wind — solved (v2).** De-biased per-activity wind: P. Paz ~3 km/h [1–7], JAAM ~2 km/h [1–5]
  (both mostly *circular* loops), author ~9 km/h [3–10] (mostly *point-to-point* brevets). This tracks
  the stated geometry rule exactly — circular ⇒ small net wind (±5 km/h), single-direction ⇒ larger
  along-route wind (±10–15). The de-bias factor is self-calibrated per rider by injecting a known wind
  and measuring recovery: α ≈ 0.7 for circular riders, α ≈ 0.5 for the point-to-point author (a
  near-straight ride correlates speed with direction, so the wind coefficient is heavily attenuated —
  hence the ×2 correction and the larger recovered wind).
- **JAAM's mass is rider-confirmed.** After the first draft flagged 103 kg as "~10 % over range," JAAM
  confirmed to Danilo that his total is **≈ 100 ± 7 kg** — so the estimate (103) is *accurate*, the
  original 73–95 prior was simply too low, and **the sustained-climb inversion recovered the true mass**
  (Entry 14's 101.7 kg was right, not an artifact). This *validates* the mass machinery rather than
  indicting it, and removes the "surge / meter over-read" worry for JAAM.

**Honest open items.**

1. **JAAM's mass — RESOLVED** (see above): rider-confirmed ≈ 100 ± 7 kg, so the 103 kg estimate is
   accurate and the prior range was too low. The earlier "intra-climb surge / meter over-read"
   hypothesis is withdrawn for JAAM. (The author anchor's 80 vs its *assumed* 73 is now the only
   possible residual over-read — but "73" is itself an unconfirmed model assumption, so the anchor may
   simply be ~80 kg; no evidence of a systematic bias survives.)
2. **Wind — RESOLVED (see above).** The first version's small winds were a *degeneracy artifact*, not
   low wind: a synthetic-wind self-test (inject a known 4 m/s, check recovery) exposed it — the fit
   returned 15 m/s with CdA ≈ 0. Linearising the aero term removed the degeneracy (the self-test now
   recovers axis + direction), and a per-rider synthetic-injection calibration de-biases the ~30 %
   regression attenuation. The residual limitation is that attenuation itself: on near-straight rides
   the correction is large (×2), so absolute wind magnitude carries more uncertainty than direction.
3. **Only ~25 % of rides fit** (r² > 0.4): group/draft rides and urban stop-go break the single-rider
   balance — expected, but it thins JAAM (27) and the author (5). This is the last genuine open item.

**Net.** **All four parameters — mass, CdA, C_rr, and per-activity wind — are recoverable from
uncontrolled ride data**, and all three riders land in their plausible ranges (the `/goal`). The keys:
mass from braking-free climbs (CdA-insensitive; rider-confirmed accurate for JAAM at ≈ 100 ± 7 kg); CdA
and C_rr only once wind is modelled per activity (flat-power, coast-down, and climb-only all fail for
CdA), via a *linearised* aero regression that avoids the CdA↔wind degeneracy; and the wind vector
itself from the GPS-bearing directional asymmetry, de-biased for regression attenuation.
**This retires Entry 14's "likely CdA misspecification" guess: JAAM's CdA is a normal 0.32, and the
high implied mass is simply genuine mass — the rider really is ~100 kg.** Tooling: `node cda_estimate.mjs`
(the exploration) and `node param_fit.mjs` (the estimator;
~1 min; writes gitignored CSVs). This is a v1 — the two numeric open items above are the next passes.

---

## 2026-07-03 — Entry 14: a third rider (JAAM) qualifies the transfer — and a framing correction

*Prompt (Danilo): a third rider's export was added at `strava_jaam`; test it. Two corrections: P. Paz
and JAAM are **not** members of Pedal Hidrográfico (independent riders who shared data with consent);
and the author's own rwgps/strava rides — the "longões" — are **not** Pedal Hidrográfico activities
either (only the "censo" set is). Earlier entries/drafts that called P. Paz "a second collective member"
or leaned on "same collective" as the external-validity caveat were wrong and are corrected here.*

**What this is.** A **third fully-independent rider** (JAAM — different person, different power meter,
not the author, not P. Paz, not in the collective), `data/activities/strava_jaam/` (gitignored,
shared with consent). `jaam_compare.mjs` reuses `ppaz_compare.mjs`'s **verbatim** engines (byte-identical,
re-verified by diff in an adversarial audit), retargeted to JAAM's manifest, plus a terrain/altitude
stratification. Numbers below are pinned to `jaam_comparison.csv` md5 `03359f5…` (219 rows); an
adversarial 3-agent review verified the harness, recomputed every figure, and set the honest framing.

**Inventory** (`jaam_inventory.mjs`): 1 282 FIT files, 0 errors, 2022-12 → 2026-07; **360 power rides**,
230 ≥ 20 km. Danilo noted JAAM rides many countries (Colombia, Germany, Ukraine, US, …) from
mountainous to plain — **but that breadth is almost all in the *non-power* activities**: the power rides
cluster tightly at **~737 m median altitude** (p10 721, p90 785 — the São Paulo band), with only a thin
non-SP tail (~15 rides: a 2023 sea-level cluster, plus late-2025 dead-flat "300 m" rides that are almost
certainly indoor). So the *testable* corpus is **~93 % São Paulo**. (Altitude is read from the elevation
stream — non-locational; no coordinate is stored.)

**Implied mass — a caveat, not a measurement.** We don't know JAAM's mass, so it is inverted from the
sustained-climb balance as for P. Paz: per-ride median **m̂ = 101.7 kg** [IQR 95.7–108.7]. That is
implausibly high at first glance (P. Paz 74.3, author ~78). *(Hypothesised here as a CdA
misspecification — **corrected in Entry 15**: JAAM's independently-estimated CdA is a normal 0.32, the
climb mass is CdA-insensitive, and **JAAM later confirmed his total is ≈ 100 ± 7 kg** — so 101.7 kg was
not implausible at all; the sustained-climb inversion recovered his true mass. He is simply a large
rider.)* The energy scoreboard uses this (correct) mass, so its accuracy is genuine here — disclosed.

**Energy law — transfers (with a data-implied mass).** On 219 clean rides (median 56.7 km, h₊ 329 m):
canonical **5.4 %** median |Δ%| (4.2 % by the per-ride statistic), smooth approx best at **3.5 %**
(ε = 0.20; ε = 0.25 gives 3.7 % — the optimum is *flat and shallow*, not a sharp 0.20). Note the reversal
from P. Paz: here the **flat ε ≈ 0.20 beats `ε_geom`** (smooth ε_geom 5.5 %, poor-man's ε_geom 9.0 %),
because JAAM's fast v_f drives `ε_geom` median to **0.61** — it *over*-credits descents this rider never
banks. Read as: the functional form + one fitted mass reproduce measured `∫P·dt` to ~4–5 % on a third
independent rider; this transfers the *form*, it does not *predict* (mass is fitted).

**The −0.13 offset is consistent a third time — but read the hedge.** On real descents (s̄ ≥ 3%, n = 21)
the measured gap med(ε_coast) − med(ε_bal) = **0.133** [bootstrap 95 % CI 0.102–0.186], matching the
calibrated 0.13 (rider 1) and P. Paz's 0.12. **But the *sign* is structural**: `ε_coast` is a coasting
upper bound on `ε_bal` (all 21 rides have ε_coast > ε_bal — the §8.3 part–whole issue), and all three
riders share city/gear context. So this is "**consistent across riders**," not "independently confirmed
three times." The magnitude landing near 0.13 each time is still notable; the direction is not evidence.

**The geometric ε *skill* does NOT transfer to JAAM — inconclusive on descents, fails on the bulk.**
Frozen `clamp01(ε_coast − 0.13)` vs measured `ε_bal`:

| subset | frozen | flat 0.20 | flat 0.23 | in-sample flat | corr |
|---|--:|--:|--:|--:|--:|
| all clean (n = 215) | **0.469** | 0.157 | 0.167 | 0.152 | −0.31 |
| real descents s̄ ≥ 3% (n = 21) | **0.090** | 0.111 | 0.094 | 0.085 | 0.270 |

- On the **gentle-heavy bulk it fails outright** (RMS 0.47 vs a flat constant's 0.16) — JAAM rides mostly
  gentle terrain (median s̄ 1.5%) and, being strong, **pedals the descents** (measured ε_bal 0.17–0.28),
  so `ε_coast`'s coasting assumption has almost nothing to bite on. This is the §8.3 flat-terrain reversal
  at rider scale.
- On the **thin real-descent subset it is inconclusive**: frozen 0.090 vs flat-0.20 0.111 is a
  **−0.020 RMS difference with 95 % CI [−0.072, 0.024] straddling zero**; it *ties* JAAM's own best flat
  constant (0.085); and corr 0.270 is **not significant** (t = 1.22, df = 19, p ≈ 0.24). Not a win, not a
  tie, not a clean failure — **underpowered/inconclusive on descents.** Mass-robust: frozen RMS
  0.105 / 0.090 / 0.083 at 90 / 101.7 / 110 kg, tracking the in-sample flat throughout.

**This qualifies the P. Paz headline.** Entry 12 reported the frozen estimator *beating* P. Paz's own
best constant by ~35 %. JAAM shows that win is **rider-dependent**: P. Paz is a coaster (banks descent
recovery → `ε_coast` has signal), JAAM is a fast descent-pedaler (banks little → no signal). **Net across
three independent riders and meters: the energy law and the calibrated −0.13 offset transfer robustly;
the geometric-ε *skill* does not — it works for riders who coast, not for those who pedal down.** That is
exactly the paper's standing position (§8.3: "ε's remaining scatter is rider behaviour, not route
geometry"), now demonstrated across riders.

**Geography stays untested.** The multi-country breadth is all in non-power activities; JAAM's
power + real-descent non-SP subset is **n = 2**. No climatic or cross-region claim is supportable.

**Framing correction (propagated to the article).** P. Paz and JAAM are **independent third-party riders,
not Pedal Hidrográfico members**; the longões are the author's own brevets, not collective rides; only the
censo is Pedal Hidrográfico. The external-validity caveat is therefore *not* "same collective" (wrong) but
"**all three riders' power/descent benchmarks happen to fall in the São Paulo altitude band — coincidental
geographic co-location across independent riders, not a shared-collective artifact; geography and climate
remain untested.**" Three *independent* riders is the stronger external-validity story than "same collective."

Caveats: ~4 non-Zwift-tagged flat "300 m" (likely indoor) rides survive into the energy scoreboard — the
median is immune, and the ε test/mass inversion drop them structurally (flat ⇒ no descent cells, no
sustained climbs). Rider-3 CdA/C_rr assumed (the mass sweep varies mass, not the suspected CdA culprit).
Tooling: `node jaam_inventory.mjs && node jaam_compare.mjs` (`JAAM_M=<kg>` for the mass sweep); both read
the gitignored export and write gitignored outputs.

---

## 2026-07-02 — Entry 13: the time model, finally tested — ascent half holds, descent bridge does not

*Prompt (Danilo): write a plan to test the time model with the existing datasets; hand to Opus/Sonnet to execute.*

**This retires the standing "time model is theory only" caveat** (§10.4, notas). The energy↔time dual
`t = x*/v_f`, `x* = x + k₊·h₊ − k₋·h₋` (article §5, the paper's second novel claim) had never been
compared to a measured ride time. [`time_compare.mjs`](../data/activities/time_compare.mjs) does that
across all three corpora at once (longões 43 · censo 58 · P. Paz 441 clean rides). Engines are verbatim
copies (assembled programmatically from `ppaz_compare.mjs` + `compare.mjs`'s `ptsFromGPX` +
`energy-model-comparison.html`'s `approxTime`); the new pieces are `extractRegimeStats` (per-regime
moving time/distance/vertical on the same 30 m grade window + VSTOP gate that feeds P̄) and the predictor
battery. The design was fixed by an adversarial methods review *before* running, and the results by a
second adversarial review (3 independent agents + synthesis) *before* this write-up — which caught two
things I had wrong and are corrected below.

**Target.** Measured **moving time over powered segments** `T_mov_bin = t₊ + t_flat + t₋` (points with
power present and v ≥ 0.5 km/h). The three regime times sum to it by construction (accounting identity
exact); regime power coverage is a median 99.7% of all moving time (`timeOK ≥ 90%` gates the rest).
Elapsed time and stop fraction are reported for context but *not* modelled — stops are behaviour, not
physics (median stop fraction: longões 25%, censo 44%, P. Paz 11%).

**Pre-declared primary endpoint** (fixed before the run, reported whatever it came out): **T1b — the full
model with power-conditioned v_f and k₋ frozen from longões — median |Δ%| vs T_mov_bin on the 441 P. Paz
rides.** Result: **6.6%** (signed +3.8), vs the naive `x/v_f` baseline **7.6%**. A **modest but real**
improvement: T1b beats T0 on **56%** of 433 rides (sign test p = 0.011, Wilcoxon p < 0.001), and the gain
is mass-robust (6.2 / 6.6 / 7.1% at 70 / 74.3 / 78 kg). It is concentrated exactly where the ascent term
should matter — on the hilliest P. Paz tercile T0 12.0% → T1b 5.8%, while the flattest tercile is
unchanged (5.8 → 5.7) — an *exploratory* (pre-motivated, not pre-registered) subgroup.

**The ascent half transfers better than a *fitted* ceiling.** The fair benchmark for the physics-derived
`k₊ = v_f·β/P_climb − 1/s̄₊` is not a naive regression but the same equivalent-flat-distance model with
`k₊, k₋` **fitted** on longões (holding the same per-ride v_f), then frozen — call it TF. In-sample TF
wins (longões 2.0% vs T1b 5.5%), because the physics k₊ under-charges climb time by the roll+aero share
(the fitted k₊ = 19.5 absorbs it). But **frozen on the genuinely-new rider, the physics beats the fitted
constant: P. Paz T1b 6.6% vs TF 10.9%** — a single fitted k₊ over-generalizes across riders/speeds where
a per-ride *physical* k₊ adapts. (A naive absolute-seconds linear fit with no per-ride v_f is far worse
still, 26.8% frozen — it bakes in one flat pace; that's why per-ride v_f is load-bearing.) On the urban
censo the fitted ceiling wins (TF 7.4% vs T1b 14.2%), so the physics is **competitive, not dominant**.

**Total-time scoreboard (power-conditioned v_f, median |Δ%| / signed):**

| predictor | longões (fit) | censo (frozen) | P. Paz (frozen) |
|---|--:|--:|--:|
| T0 naive `x/v_f` | 16.8 / −16.8 | 20.8 / −20.8 | 7.6 / −0.5 |
| TS Scarf `k₊=8` | 8.9 | 14.5 | 8.4 |
| T1a ascent-only (physics k₊) | 5.5 / −5.2 | 14.2 | 6.6 / +3.8 |
| **T1b full (physics k₊, k₋ frozen)** | **5.5** | **14.2** | **6.6 / +3.8** |
| T2 approxTime (per-segment) | 4.3 / +0.1 | 11.4 | 7.4 / +6.1 |
| T3 canonical forward sim | 3.6 / −0.3 | 13.5 | 8.6 / +7.5 |
| TF fair fitted ceiling (k₊,k₋) | 2.0 | 7.4 | 10.9 |

- **k₋ pins to 0 in power-conditioned mode** (grid boundary) — *not* "descents don't matter." Power-conditioned
  `v_f = flatEqSpeed(P̄_flat)` slightly *over*-estimates real moving-flat speed (coasting, corners,
  micro-slowdowns), so T0 under-predicts time (−0.5…−20.8% signed); any k₋ > 0 subtracts more and worsens
  the median. The **speed-anchored** fit (measured flat speed) disambiguates: there k₋ = 0.3 and, with the
  flat speed measured, the ascent term clearly helps — P. Paz T0 5.2% → T1a/T1b **2.0%**. But speed-anchored
  v_f = x_flat/t_flat *shares measured flat time with the target*, so it is **partially in-sample** and
  reported only as a secondary diagnostic, never as the headline.

**The descent bridge is NOT confirmed.** The ε↔k₋ bridge predicts descent speed `v_desc = P̄_desc/(α − ε·β·s̄₋)`
(with ε the frozen geometry estimator). Against measured `x₋/t₋` on real descents (s̄₋ ≥ 3%, h₋ ≥ 50 m,
x₋ ≥ 1 km): correlation **0.59 longões / 0.08 censo / 0.14 P. Paz**, and it systematically **over-predicts**
(med meas vs pred: 30 vs 38, 16 vs 37, 32 vs 52 km/h). The analytic form is uncapped — near the α = ε·β·s̄
degeneracy it diverges (unphysical hundreds of km/h) — and even where finite it omits the safe-speed/vmax
cap the canonical engine applies: real descents are **behaviour- and cap-limited, not aero-gravity-power
equilibrium-limited**. So the descent credit `k₋` stays a **free, corpus-dependent** coefficient
(measured median 5.9 rural longões, ≈0/negative −1.4 urban censo, 4.8 P. Paz), *not* pinned by the bridge.

**What is NOT evidence (a correction from the review).** I had proposed a coefficient-level "time" test
`r₊ = P̄_climb·t₊/(β·h₊)` ≈ 1.26, stable across all three corpora. It is a **near-tautology**: since
`P̄_climb ≡ E_climb/t₊`, the climb time `t₊` cancels and `r₊ = k_eff·E_climb/(mg·h₊)` — it is exactly the
Entry-7 *energy* climb over-charge re-expressed, carrying no independent *time* information. Its stability
(≈1.26 = ~26% of climb pedal energy paying rolling+aero rather than lift) is the stability of the *energy*
over-charge and is reported as such, not as corroboration of the time law. The honest time evidence is the
total-time predictors above.

**Verdict — a calibrated split, mirroring the energy ε story.**

- **Ascent half: empirically supported and transfers out-of-sample** — modest in aggregate (6.6% vs 7.6%,
  significant), concentrated on hilly rides, and beating a *fitted* ceiling on the new rider. The
  gravity-only climb-time law `k₊ = v_f·β/P_climb` is the real, transferable piece (with a known ~26%
  roll+aero under-charge on the pure-lift form).
- **Descent half: not confirmed** — the analytic ε↔k₋ bridge does not predict measured descent speed; `k₋`
  remains an empirical, corpus-dependent lumped parameter, behaviour/cap-limited.

Caveats: power-conditioned is the clean out-of-sample mode; speed-anchored and the k₋_meas/v_desc
diagnostics reuse measured time (in-sample). T2/T3 integrate the full geometric profile while the target is
powered-moving time (≤10% coverage slack; partly explains T2's censo −11% bias). Only T1b-power-P. Paz was
pre-declared; the terciles, modes, and per-corpus splits are exploratory. Two riders (the author + the
independent rider P. Paz — see the Entry-14 framing correction: P. Paz is *not* a collective member),
same São Paulo region (Entry-12 caveats carry over).

Tooling: `node time_compare.mjs` (reads the three gitignored track sets + manifests; writes
`time_comparison.csv`, gitignored). `PPAZ_M=<kg> node time_compare.mjs` for the mass sweep.

---

## 2026-07-02 — Entry 12: a second rider — the frozen ε estimator survives the transfer

*Prompt (Danilo): P. Paz shared their full Strava history export (`data/activities/strava_ppaz/`,
gitignored — third-party GPS, shared with consent). Incorporate it into the analysis.*

**This is the external-validity test §10.4 named as the deepest limitation** — until now every
number came from one rider and one power meter. P. Paz is a different rider, on a different
meter, with a different riding profile (median v_f **26.6 km/h** vs Danilo's 16.5 urban /
23.4 longões — a faster, open-road rider).

**Inventory** ([`ppaz_inventory.mjs`](../data/activities/ppaz_inventory.mjs)): 1 054 FIT files
parsed, 0 errors, 2023-10 → 2026-07. 1 052 rides, **753 with power** (>50% coverage), 493 of
them ≥ 20 km. After the harness filters (altitude ≥ 99%, not-Zwift via FIT `file_id`
manufacturer — **45 virtual rides excluded** — and power present): **441 usable rides**, none
excluded by the physical floor (P. Paz's meter shows no censo-style dropouts).

**Implied mass, not assumed** ([`ppaz_compare.mjs`](../data/activities/ppaz_compare.mjs) pass A).
We don't know P. Paz's mass, so it is *inverted from the sustained-climb energy balance* (the
Entry 7 machinery): on climbs ≥ 3% over ≥ 100 m, measured ≈ (grav+roll)·(m/m₀) + aero. Over
**10 124 sections, 209 km of sustained Δh**: global m̂ = 75.6 kg; **per-ride median m̂ = 74.3 kg**
[IQR 69.0–78.2, n = 247 rides with ≥ 200 m sustained] — physically plausible for rider+bike+gear,
and tight. CdA 0.40 / C_rr 0.008 / ρ 1.13 assumed as in the censo run.

**Energy scoreboard on 441 clean rides** (medians: 58.2 km, 566 m h₊, ε_geom 0.54):

| model | med \|Δ%\| | medΔ% | meanΔ% |
|---|--:|--:|--:|
| **poor-man's · ε=geom** | **4.9** | **+0.6** | +0.8 |
| smooth approx · ε=geom | 5.8 | +4.3 | +3.9 |
| poor-man's · ε=0.25 | 6.3 | +4.1 | +4.7 |
| canonical (fed ride powers) | 6.8 | +5.0 | +5.1 |
| poor-man's · ε=0.20 | 6.8 | +5.4 | +6.0 |
| smooth approx · ε=0.20 | 10.1 | +10.0 | +10.0 |
| (ε=0.00: smooth 14.2 / poor-man's 9.8) | — | — | — |

- **All models land within ~5–7% median with fully assumed physics** (only mass data-implied) —
  the censo-level result reproduces on a rider we know nothing about a priori.
- **`ε_geom` is the *best* variant here (+0.6% bias)** — the reverse of the censo, and exactly
  what the corpus-bounded rule predicts: P. Paz's riding is open and coastable (median ride
  58 km at 26.6 km/h), so the free-coasting geometry applies; flat ε = 0.20 *under*-credits
  recovery on this corpus (+5…+10% over-prediction). The censo/longões rule — `ε_geom` on open
  routes, flat ≈ 0.20 on urban stop-go — is confirmed from the other side.

**The ε second-rider test — nothing refit.** Per-ride descent-balance ε_bal vs geometric
ε_coast on 30 m cells (α at P. Paz's measured flat speed), with every estimator **frozen from
rider 1**:

| estimator (frozen) | RMS, all n=436 | RMS, s̄ ≥ 3% (n=156) |
|---|--:|--:|
| **`clamp01(ε_coast − 0.13)`** | **0.280** | **0.091** |
| flat ε = 0.20 | 0.484 | 0.227 |
| flat ε = 0.23 | 0.464 | 0.204 |
| *in-sample* flat = median ε_bal | 0.356 | 0.139 |

- **The frozen rider-1 estimator beats even P. Paz's own best flat constant by ~35%**
  (0.091 vs 0.139 at s̄ ≥ 3%, n = 156 — seven times the n=22 subset it was calibrated on) — and,
  unlike on rider 1, it wins on *all* rides too (0.280 vs 0.356), because this rider's gentle
  rides still coast.
- **The −0.13 offset reproduces independently**: P. Paz's measured gap med(ε_coast) − med(ε_bal)
  at s̄ ≥ 3% is **0.12** (0.48 − 0.36). Two riders, two meters, same near-constant offset.
- **Mass-insensitivity**: rerunning with m ∈ {70, 74.3, 78} kg moves the frozen-estimator RMS
  only 0.096/0.091/0.088 (in-sample flat 0.147/0.139/0.133) — the conclusion does not depend on
  the in-sample mass calibration. (`PPAZ_M=<kg> node ppaz_compare.mjs`.)
- corr(ε_coast, ε_bal) = 0.81 at s̄ ≥ 3% — but as always (Entry 11) that correlation is
  part–whole; the frozen-vs-flat RMS comparison above is the honest statistic, and it is the
  out-of-sample one.

**Caveats, honestly.** *(Framing corrected in Entry 14: P. Paz is an **independent** rider, NOT a
collective member; the "same collective" wording below was wrong.)* Same São Paulo **city region**
(shared roads; though measured on an independent body and meter);
rider-2 CdA/C_rr still assumed, mass calibrated in-sample from climbs (ε result shown
insensitive); the ε evaluation shares its *method* (30 m cells, measured flat speed) with
rider 1, so a method-level artifact would not be caught by this test. n(riders) = 2 — but the
step from 1 to 2 is the big one.

Tooling: `node ppaz_inventory.mjs && node ppaz_compare.mjs` (reads the gitignored export;
writes `strava_ppaz_manifest.json` + `ppaz_comparison.csv`, both gitignored).

---

## 2026-07 — Entry 11: general review — code fixes, and what they moved

*Prompt (Danilo): a general review over the results, methodology, codebase, and data.*

A 13-agent adversarially-verified review (findings independently re-checked against the files
before being reported) surfaced one urgent privacy issue (fixed separately: `data/longoes.xlsx`
was purged from git history) and a set of code bugs and methodological overclaims. Every finding
below was verified by re-running the harnesses; the numbers in this entry and retroactively in
Entries 7–10 are the corrected, re-run values.

**Code fixes (no published headline conclusion reverses; several numbers shift by ≤0.3 pp, one
by more):**

- **A latent KE-floor bug in `canonical()`.** The zero-propulsion branch kept a `Math.max(B, 1e-12)`
  floor on kinetic energy — exactly the energy-injecting bug the repo's own invariant forbids
  (`CLAUDE.md`: "do not reintroduce a VMIN/KE floor"). It was unreachable by any of the 44+62
  benchmark rides (none has a zero-power regime), so **no published number was affected**, but it
  was live code. Fixed: the zero-power branch now solves the exact linear-KE equation and halts
  the bike (`stalled` flag) rather than flooring — in the app and both `.mjs` copies.
- **`measuredFlatSpeed`/`epsFromBalance` didn't gate out stopped samples** (`extractRegimePowers`,
  one function above, already did). Including v≈0 samples in the "flat speed" average deflates
  `v_f` and hence `α` and `ε` on any ride with stops. Fixed (VSTOP = 0.5 km/h gate) in the app and
  all four `.mjs` harnesses. This is the one fix with a real, disclosed effect: on the São Paulo
  censo set (stop-go riding), the descent-balance `ε_true` moves **0.14 → 0.23** (Entry 10, revised
  below) — because those rides have the most stopped time to have been wrongly averaged in.
- **Compressed-timestamp FIT records got no timestamp**, defaulting `dt=1 s` downstream; harmless
  *only* because the affected devices happened to log at exactly 1 Hz. Fixed: the 5-bit
  timestamp-offset header is now decoded (as `data/activities/verify.py` already did), in the app
  and all four `.mjs` copies.
- **`flatEqSpeed` used unsigned drag** while both engines use signed `rel·|rel|` — broke the
  flat-match anchor under a strong tailwind (not triggered by any current ride). Fixed with a
  monotone-safe bisection.
- **`loadFIT` in the app couldn't load 3 of the 44 rides** (interleaved dist/alt records) — the
  harnesses already had the index-interpolation fix; ported it to the app.
- Smaller robustness fixes (harnesses only, no number changes): `Buffer` pool hazard on small FIT
  reads, `parseFIT` throwing consistently instead of silently truncating on 3 of 4 copies, a
  final-point profile-dedup edge case that could create `dx≈0`, non-monotone device-distance
  clipping, and a machine-checked per-ride conservation-identity assert (`compare.mjs` now prints
  the worst residual — **1.77e-8**, comfortably under the 1e-6 bar).

**Methodological honesty corrections (documentation, no code change):**

- **The ε correlations (0.83/0.87) are part–whole, not independent validation.** `ε_bal` (the
  "truth") and `ε_coast` (the predictor) share their dominant geometry term *and* the same per-ride
  `α`; at `s̄ ≥ 3%` the shared term `α/(β·s̄)` *alone* correlates **0.72** with `ε_bal` (re-measured;
  it correlates 0.99 with `ε_coast` — they are nearly the same quantity). The honest statistic is
  the **RMS error reduction vs. a flat-constant baseline**: at `s̄ ≥ 3%`, `ε_coast − 0.13` reaches
  RMS 0.08 against a flat-median baseline of RMS 0.13 — a genuine **37% RMS reduction**, which is
  the number to lead with, not the correlation. (New `eps_hypothesis.mjs` output section
  "ESTIMATOR SKILL".)
- **`E_leg = E_wheel · k_eff` in `notas.md` had the efficiency on the wrong side** (should be
  `E_wheel / k_eff` — the legs supply *more* than the wheel receives). Fixed.
- **k₋ is a free parameter, not a fitted one** — the energy↔time duality (`x* = x + k₊·h₊ − k₋·h₋`)
  has never been checked against measured ride *times* anywhere in this repo; only the *energy* law
  is validated. `notas.md` and the article now say so explicitly.
- Assorted smaller corrections: the article's §3 named the wrong `climbAeroMode` for its own
  headline (`'off'` → should be `'zero'`); two censo-scoreboard rows (the `ε=0.00` variants for
  "smooth" and "poor-man's") were transposed; the excluded-rides discussion said "6 of 7" had high
  cadence coverage — it's **5 of 7** (Cânions da Brasilandia's 56% coverage is genuinely ambiguous,
  not clearly pedalled); `k_s ≈ 0.74` was stated as measured for FABDEM/IGC-SP when it is only
  measured for the recorded-barometric deadband ratio (the DEM value remains an open TODO, ~0.8–0.9
  estimated); the sampasimu cost table in the article dropped the climb-threshold condition on the
  uphill aero term.

Revised Entry 8/9/10 numbers are folded into those entries below (marked where they moved).
**Entries 2–6 are left as originally written** (a historical record of the code at the time) — the
same code fixes shift their embedded numbers too, but only by ≤0.6 pp (e.g. Entry 2's `approx off`
19.2%→19.3%, Entry 3's climb-fraction 8.5%→8.6%, Entry 4's measured-`v_f` 22.1→22.8 km/h and its
associated 2.7%→6.7% residual — a real, larger shift from the same VSTOP gate as Entry 8/10, since
Entry 4 also uses the measured flat speed). None of these reverse a conclusion; re-run
`compare.mjs` for the exact current values rather than trusting the historical prose figures.

---

## 2026-06-29 — Entry 10: is São Paulo's ε a braking-driven quantity? (no — it's a constant)

*Prompt (Danilo): hypothesise how to estimate ε for São Paulo. Hypothesis tested: urban
stop-go suppresses descent recovery below the free-coasting closed form, so*
`ε_SP = clamp(ε_coast − Δε_brake)`, *with* `Δε_brake = (1/(g·H₋))·Σ_descent ½·Δ(v²)` *at forced
decelerations — readable from the speed trace (post-hoc) or a route's signal/stop/corner density
(planning).*

Tested on **59 clean censo rides** (power → true descent-balance ε via `epsFromFIT`; speed →
braking density), α at the *measured* flat speed, assumed rider. Tool:
[data/activities/eps_sp_test.mjs](../data/activities/eps_sp_test.mjs). Medians: ε_true **0.23**,
ε_coast **0.40**, gap **0.15** (sd 0.08).

*(Revised by Entry 11's `measuredFlatSpeed`/`epsFromBalance` VSTOP fix — stopped samples were
deflating the flat speed on this stop-go corpus more than on the open longões rides; ε_true moved
from an originally-reported 0.14. The refutation below is unchanged in substance and, if anything,
stronger: ε_coast − 0.13 now ties the flat constant instead of losing to it.)*

**Refuted — the gap does not track stop-go density:**

| predictor for the gap (ε_coast − ε_true) | corr | R² |
|---|--:|--:|
| Δε_brake (descent ½Δv²) | 0.11 | 0.01 |
| hard-brake (>1 m/s, descent) | −0.16 | 0.02 |
| all-decel ½Δv² | 0.24 | 0.06 |
| stops/km | −0.26 | 0.07 |
| v_f | 0.37 | 0.14 |

None of the stop-go/braking predictors explain the per-ride gap (R² ≤ 0.07, two wrong-signed).
`v_f` alone now shows the strongest (still modest) association, R²=0.14 — plausibly because
faster-descending rides simply have less braking to reconcile, not a stop-go effect per se; it
does not change the refutation. The mechanistic `ε_coast − Δε_brake` still *over*-corrects
(Δε_brake median 0.34 ≫ gap 0.15 → RMS 0.19, **worse** than a flat constant). Estimator RMS vs
ε_true: flat **ε=0.20 → 0.08**; `ε_coast − 0.13` → **0.08** (now *tied* with the flat constant,
previously it lost 0.12 vs 0.10); mechanistic → 0.19; ε_coast (no penalty) → 0.18.

**Why it fails — Entry 8's logic biting back.** Braking is *invisible* to ε (coast or brake,
the legs are idle: `E_legs=0`). The cost is *re-acceleration* — but on a **descent, gravity
re-supplies the braked-away speed**, so the re-accel is nearly free in leg terms. The KE shed at
a red light is handed back by the ongoing descent, not by extra pedalling. So urban stop-go does
**not** suppress descent-ε; the intuition mispriced where the energy goes.

**Conclusion — São Paulo's ε is a constant, not a route-specific braking term.** The over-credit
of ε_coast (gap median 0.15, close to the open-road −0.13 offset of Entry 8) is a roughly
*constant* offset that scales with nothing measurable here. Practical rule: **ε ≈ 0.20** for the
model (the Entry 9 energy-sweep optimum), or pure descent-balance ε ≈ **0.23** (the assumed
`C_rr = 0.008` may still be a touch low for rough city asphalt). With the Entry 11 fix,
`ε_coast − 0.13` now performs *as well as* the flat 0.20 constant (both RMS 0.08) — so the rural
offset transfers to São Paulo essentially unchanged; **drop the braking correction** regardless.

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
(Danilo: pedalling ⇔ cadence > 0). On **5 of the 7**, cadence coverage is 73–100 % and the
walking signal — moving < 4 km/h **with cadence 0** — is only **~1 %**. So those riders were
*pedalling, not walking*; the deficit is a **power-channel problem** (power dropping out while
cadence kept logging, or an under-reading meter). The other 2 (Mirantes, 31 % cadence coverage;
Cânions da Brasilandia, 56 %) have low enough cadence coverage that walking is not ruled out —
genuinely ambiguous, likely a fuller sensor dropout for Mirantes at least. Either way the floor
excludes all 7. They over-predict by +79…+373 % and would wreck the mean.

**Result on the 62 clean rides** — Δ% vs measured ∫P·dt, ε swept:

| model | med \|Δ%\| | medΔ% | meanΔ% |
|---|--:|--:|--:|
| canonical (fed ride powers) | 6.5 | −3.4 | −0.8 |
| smooth approx · ε=0.10 | 4.5 | +3.4 | +5.7 |
| smooth approx · ε=0.15 | 5.0 | +1.3 | +3.5 |
| smooth approx · ε=0.20 | 4.6 | −0.8 | +1.2 |
| **poor-man's · ε=0.20** | **3.9** | +1.1 | +4.7 |
| poor-man's · ε=0.25 | 4.8 | −1.2 | +2.1 |
| poor-man's · ε=geom (0.29) | 6.3 | −3.2 | +1.1 |
| smooth approx · ε=geom (0.29) | 7.6 | −4.9 | −1.9 |
| smooth approx · ε=0.00 | 7.6 | +7.4 | +10.2 |
| poor-man's · ε=0.00 | 10.5 | +10.5 | +15.1 |

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

**The grade core holds where ε carries energy — but read the correlations with care (see Entry 11):**

| view | corr(ε_coast, ε_bal) | bias (ε_bal − ε_coast) |
|---|--:|--:|
| all 44 rides (unweighted) | 0.30 | −0.17 |
| weighted by descent energy `β·H₋` | **0.60** | −0.18 |
| real descents, `s̄ ≥ 3.0%` (n=22) | **0.77** | −0.12 |
| real descents, `s̄ ≥ 3.5%` (n=15) | **0.82** | −0.12 |

*(Re-run under Entry 11's `measuredFlatSpeed` VSTOP fix; correlations moved down slightly from an
originally-reported 0.38/0.65/0.83/0.87 — same qualitative picture. More importantly: these
correlations are **part–whole**, not an independent check — `ε_bal` and `ε_coast` share their
dominant geometry term and the same per-ride α, so at `s̄≥3%` the shared term `α/(β·s̄)` *alone*
already correlates 0.72 with `ε_bal` (and 0.99 with `ε_coast` itself). The better statistic is the
**RMS error reduction vs. a flat-constant baseline**: at `s̄≥3%`, `ε_coast − 0.13` reaches RMS 0.08
against a flat-median baseline of RMS 0.13 — a **37% RMS reduction**. Over *all* 44 rides the
calibrated estimator actually *loses* to the flat median (skill −0.38) because of the flat-terrain
reversal below — restrict to real descents before using it.)*

- **Validated estimator:** `ε ≈ clamp[0,1]( ε_coast − 0.13 )`. The −0.13 is a near-constant
  offset (residual descent pedalling/braking the coasting ideal ignores); it turns the
  `s̄≥3%` median ε_coast 0.39 → 0.26, matching the measured 0.27.
- **"Flat → ε→1" is *reversed* by the data** (intuitions #2/#3). Gentle rides are pedalled
  *through* the dips, so measured ε→0, not 1 (NS3 Caracaí: predicted ≈0.9, measured **0.01**).
  This is most of the unweighted bias — but it is **harmless**, because those rides carry
  `β·H₋ ≈ 0` descent energy (hence energy-weighting alone lifts corr 0.30 → 0.60).
- **Curve / off-road penalties fail** (intuitions #4/#5): κ and `f_unpaved` fit with the
  **wrong sign**. They are confounded with *mountainous terrain* — twisty/rough
  rides are exactly the ones with real sustained descents, which recover *more*. The
  braking-loss effect is real but swamped.
- **Descent intuition #1 is the load-bearing one and it holds.** The remaining scatter is
  rider *behaviour* — several rides have measured ε < 0 (pedalling downhill, `E_legs > α·X₋`),
  which no route-geometry term can predict.

*Worked example (RMC200 Mogi):* α/β = 0.0202, s̄ = 3.4% ⇒ min(1, 0.0202/0.0341) = 0.59;
minus 0.13 ⇒ **0.46**, vs. measured **0.47**. (Unaffected by the Entry 11 fixes — confirmed on re-run.)

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
| expected (grav 37 366 + roll 4 424 + aero 1 544) | 43 333 |
| **measured / expected** | **0.96** |
| **k_h(sustained) = (measured − roll − aero)/gravity** | **0.96** |

(per-ride median 1.02, range 0.57–1.23. *Aero and the ratio shifted marginally on Entry 11's
re-run — v within climb sections is now derived from the unclamped Δt — the headline `k_h≈1`
conclusion is unchanged.)*

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
| **smoothened** (cf + real 2 m deadband, `k_smooth=1`) | **3.6** | +2.2 |
| canonical (forward sim) | 5.1 | −1.7 |
| **k_smooth** (cf + scalar `1 − c·x/h₊`, no smoothing) | 5.8 | −0.5 |

The **real deadband is best** (3.6 %); the **scalar `k_smooth` is unbiased (−0.5 %) but ~2×
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
  cross-checking the real terrain ascent. *(Qualified in Entry 19: this was measured on 10
  hilly longões and does NOT generalize to flat urban/lowland terrain — there FABDEM's
  per-pixel noise reads as rollers, inflating h₊ by +57% median over the pooled SP rides,
  +101–135% on the flattest corpora.)*
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
