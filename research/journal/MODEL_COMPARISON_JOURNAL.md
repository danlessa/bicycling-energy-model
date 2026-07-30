# Model comparison journal

A running log of comparing the two energy models against measured rides. **Entries
are reverse-chronological — most recent first.** The foundational methodology is the
last (oldest) entry. Three energies per ride, all in kJ:

- **empirical** — measured pedalling energy `∫P·dt` from the track (ground truth)
- **canonical** — `canonical().legE`, the forward-dynamics model's `∫P·dt`
- **approximate** — `approximate().E`, the closed-form `α·x + β(h₊ − ε·h₋)`

Tooling: [src/harness/build_model_inputs.py](../../src/harness/build_model_inputs.py)
(per-ride parameters from the sheet) → [src/harness/compare.py](../../src/harness/compare.py)
(runs the **real** engines, ported verbatim from `applet/index.html`).
Output: `data/results/model_comparison.csv` (gitignored). Dataset & verification:
[data/inputs/activities/README.md](../../data/inputs/activities/README.md),
[VERIFICATION_NOTES.md](../notes/VERIFICATION_NOTES.md).

Running scoreboard — median |Δ%| vs empirical `∫P·dt` over 44 power rides (best first):

| model / variant | median \|Δ%\| | median Δ% | entry |
|---|--:|--:|:--:|
| **approximate `cf` + 2 m elev smooth** (deadband) | **3.5** | +2.1 | 5 |
| canonical (forward sim) | 5.2 | −1.8 | 2 |
| canonical + 2 m elev smooth | 5.7 | −3.6 | 5 |
| approximate `cf` + scalar `k_smooth` (no smoothing) | 5.9 | −0.6 | 7 |
| approximate `cf` + sheet `v_f` (`P_flat/P_avg`) | 7.2 | −0.6 | 4 |
| approximate `cf` + measured `v_f` | 8.0 | +6.6 | 4 |
| approximate + climb-fraction (`cf`) | 8.6 | +8.4 | 3 |
| approximate `off` + 2 m elev smooth | 10.2 | +9.8 | 5 |
| approximate `off` (baseline) | 19.1 | +19.1 | 2 |

*(Entry 27, 2026-07-25: the scoreboard above is **re-baselined to São Paulo's gravity**
(G = 9.7864, IAG-USP) — every row moved by ≤0.2 pp; the pre-re-baseline values are in
Entry 27's delta table. Entry 11, 2026-07: a general review turned up several small code bugs — a gated flat-speed
computation, compressed-timestamp FIT recovery, a signed-drag fix — that shifted these numbers by
≤0.3 pp, except "measured `v_f`" which moved more (7.5→8.2) because the flat-speed gate itself
changed. See Entry 11.)*

**Code provenance** — the commit holding each entry's analysis code:

- **Entries 1–4** (harness `build_model_inputs.py` + `compare.py`: methodology, baseline,
  climb-fraction, P_flat/P_avg) — [`797173f`](../../src/harness/compare.py)
- **Entry 5** (per-regime, elevation noise, deadband filter, τ=2) — `cd2f549`; the filter +
  `k_h` wired into the app/`research/notes/original_notes.md` in `7e46fab`
- **Entry 6** (DEM/IGC comparison, `harness/dem/`) — `7d958ca`; IGC 5 m + `k_DEM`/`k_h`
  split in `3f98465`, `a184286`
- **Entry 7** (sustained-climb `k_h` fit, `climbBalance` in `compare.py`) — [`9135ab9`](../../src/harness/compare.py)
- **Entry 8** (closed-form `ε` hypothesis + test, [`eps_hypothesis.py`](../../src/harness/eps_hypothesis.py)) — [`6640780`](../../src/harness/eps_hypothesis.py)
- **Entry 9** (censo-hidrográfico urban rides, [`fetch_censo.py`](../../src/harness/fetch_censo.py) +
  [`censo_compare.py`](../../src/harness/censo_compare.py)) — [`9fc247b`](../../src/harness/censo_compare.py)
- **Entry 10** (São Paulo ε hypothesis test, [`eps_sp_test.py`](../../src/harness/eps_sp_test.py)) — `707c584`
- **Entry 11** (general review: code fixes + honesty corrections across engines, parsers, and
  every downstream number) — `906de11`
- **Entry 12** (second rider: P. Paz's Strava export, [`ppaz_inventory.py`](../../src/harness/ppaz_inventory.py) +
  [`ppaz_compare.py`](../../src/harness/ppaz_compare.py)) — `2148deb`
- **Entry 13** (time model tested on all three datasets, [`time_compare.py`](../../src/harness/time_compare.py)) — `eeb38cd`
- **Entry 14** (third rider JAAM + a framing correction: P. Paz/JAAM are *independent* riders, not
  collective members, [`jaam_inventory.py`](../../src/harness/jaam_inventory.py) +
  [`jaam_compare.py`](../../src/harness/jaam_compare.py)) — this commit
- **Entry 15** (independent per-rider CdA/C_rr/mass + per-activity wind estimation,
  [`cda_estimate.py`](../../src/harness/cda_estimate.py) +
  [`param_fit.py`](../../src/harness/param_fit.py)) — `1d4eb2c`
- **Entry 16** (fitted rider physics vs assumed; the author's full Strava export as a fourth dataset,
  [`danlessa_inventory.py`](../../src/harness/danlessa_inventory.py) +
  [`danlessa_compare.py`](../../src/harness/danlessa_compare.py) + `*_CDA`/`*_CRR` overrides) — `736f33f`
- **Entry 17** (a regime-decomposed closed form E_new = E_flat + E_climb + E_descent, and a totals
  variant E_new2, tested vs the champion on all five corpora,
  [`regime_compare.py`](../../src/harness/regime_compare.py)) — this commit
- **Entry 18** (correction: R1a is NOT the deployed sampasimu cost — dead-clamp proof + Jensen
  sign flip + R1d pre-registration and results (the Jensen prediction fails to a resolution effect;
  the bias-trade law claims R1d too),
  [`verify_v2edge_clamp.py`](../../src/harness/verify_v2edge_clamp.py) +
  [`regime_compare.py`](../../src/harness/regime_compare.py)) — this commit
- **Entry 19** (the app's usual DEM: v2Edge on the deployed IGC-SP 5 m raster vs its 30 m resample,
  censo rides, [`igc_resolution_test.py`](../../src/harness/igc_resolution_test.py)) — this commit
- **Entry 20** (goal-driven: can the deployed pipeline hit ±5% error / ±2% bias? smoothing σ +
  per-rider calibration, train/validation,
  [`goal_calibration.py`](../../src/harness/goal_calibration.py)) — this commit
- **Entry 21** (hypothesis: the resolution gap is a PARAMETER problem — scale-dependent
  behavioural trio (k_s, ε₀, climbThr) vs scale-free rider physics; fit the trio as a pure
  5 m→30 m resolution transfer, no DEM edits,
  [`scale_trio.py`](../../src/harness/scale_trio.py)) — this commit
- **Entry 22** (bootstrap 95% CIs + paired sign tests for the article's headline medians; the
  champion-vs-canonical "beats" claim demoted to parity,
  [`bootstrap_ci.py`](../../src/harness/bootstrap_ci.py)) — this commit
- **Entry 23** (move-grid connectivity bias in sampasimu's terrain mode — study and code live in
  the sibling repo: `../simujaules/docs/grid-connectivity-sensitivity-2026-07-11.md` (canonical
  copy) + its `grid-sens.mjs`/`grid-correct.mjs`/`grid-adaptive.mjs`/`grid-pull.mjs`/`grid-eik.mjs`/
  `grid-longedge.mjs`) — simujaules commits `f83f2f9`→`17ee186` (note), `1ba06ae` (v57 options)
- **Entry 24** (literature review: cumulative-ascent error of consumer barometers vs DEMs,
  positioned against Entries 6/19–21,
  [`ascent-error-literature.md`](../notes/ascent-error-literature.md)) — this commit
- **Entry 25** (the simujaules grid-connectivity note imported verbatim; canonical original in
  `../simujaules/docs/grid-connectivity-sensitivity-2026-07-11.md`) — this commit
- **Entry 26** (pre-registration only: the direction ladder on the Entry-19 corpus's real
  endpoints, and portals (bridges/tunnels) in the track-as-whole and discretized scenarios —
  harnesses to follow) — this commit
- **Entry 27** (re-baseline: G = 9.7864 across all 14 rider-physics sites, `flat_eq_speed` back
  to the applet's bisection (numpy dropped, the Python package stdlib-only again), V8-exactness
  retired; full-suite rerun + gate/journal/article reconciliation) — this commit
- **Entry 28** (harness dedup — one shared implementation in
  [`src/bicycling_energy_model/`](../../src/bicycling_energy_model/) replacing the per-file
  copies, `v8math.py` and `analysis/parity/` retired — plus the `src/`/`research/journal/`/
  `data/inputs|results/` repo restructure) — this commit
- **Entry 29** (pre-registration + Tier A results: physical-constants sensitivity sweep over
  CdA × Crr × ρ, closed forms + ε machinery on D2–D5 via per-ride aggregates,
  [`param_sweep.py`](../../src/harness/param_sweep.py)) — this commit
- **Entry 30** (pre-registration + Tier B results: the canonical simulation under the same
  sweep, one-at-a-time, `SWEEP_CANON=1` in
  [`param_sweep.py`](../../src/harness/param_sweep.py)) — this commit
- **Entry 42** (pre-registration + results: the lumped ε_d — is mean descent grade a valid
  proxy for the drop-weighted estimator at energy level?,
  [`e42_lump.py`](../../src/harness/e42_lump.py)) — this commit
- **Entry 41** (pre-registration + results: the elevation-source substitution — paper 1's
  law on planner DEM profiles, seven arms on one arc grid, with the track-quality /
  raster-validity / anomaly QA gates,
  [`e41_dem_route.py`](../../src/harness/e41_dem_route.py)) — this commit
- **Entry 40** (pre-registration + results: the roller-recycling covariate — recyclable
  energy share vs the form-3 residual; slope = transfer efficiency η̂,
  [`e40_roller.py`](../../src/harness/e40_roller.py)) — this commit
- **Entry 39** (pre-registration + results: the deconfounded τ-sweep — Entry 38 re-run at
  the regime-consistent per-ride physics, [`e39_tau_reg.py`](../../src/harness/e39_tau_reg.py)) — this commit
- **Entry 38** (pre-registration + results: the τ-sweep across riders — does the optimal
  deadband track h_KE = v_f²/2g?, [`e38_tau.py`](../../src/harness/e38_tau.py)) — this commit
- **Entry 37** (hypothesis note, no run: the KE-equivalent height — momentum as the
  deadband's mechanism, roller spacing as an ε covariate, and the dissipation length
  λ = m/(ρ·C_dA)) — this commit
- **Entry 36** (pre-registration + results: ε₀ regressed per dataset — balance-level vs
  bias-zeroing, at regime-consistent and frozen physics, with a chronological out-of-sample
  test, [`e36_eps0.py`](../../src/harness/e36_eps0.py)) — this commit
- **Entry 35** (pre-registration + results: the honest-physics residual — measured braking
  charge (arm A) and the regime-consistent ĈdA (arm B),
  [`e35_residual.py`](../../src/harness/e35_residual.py)) — this commit
- **Entry 34** (the S-curve deficit hypothesis: grade-resolved ε₀·g(s) as pedalling
  probability — exploratory first cut + registered confirmatory design) — this commit
- **Entry 33** (pre-registration + results: per-ride physics inversion — m̂/Ĉrr/ĈdA from each
  ride's own qualifying segments + wind step, the Table-3 analogue,
  [`perride_invert.py`](../../src/harness/perride_invert.py)) — this commit
- **Entry 32** (review-v3 consolidation: Table 4 descent-RMS full regeneration, the D3+D4
  transfer-only pool, per-corpus allegiance sign tests, and the gate battery extended to the
  numbers the review caught un-gated — [`bootstrap_ci.py`](../../src/harness/bootstrap_ci.py)) — this commit

---

## Data traceability

Every entry's data operations in the **I/T/O/S** notation, one row each. An input
$I = (D, P)$ crosses a corpus with a parameter class ($P_{a,g}$ assumed-global,
$P_{a,r}$ assumed-per-ride, $P_{f,r}$ fitted-per-ride, $P_{f,p}$ fitted-per-person;
overrides joined by $\cdot$). A transformer $T$ is a model or an estimator — $T$ is the
class, the named forms F1–F4 and $F_\mathrm{base}$ (the forward simulation) are its
instances. An output $O = T(I)\,|\,\sigma$ is **per ride**, and its count is the rows its
CSV actually holds, which is *not* the corpus size: $\sigma$ intervenes, sometimes cutting
(48 of 113 on Entry 47) and sometimes widening (69 rows for D2's 62 clean rides, because
flagged rides are kept with their results). A statistic $S(O)$ is what gets published.

**The counts below are the population to reason about — never the corpus size.** Reading a
$\lvert D \rvert$ where the claim needs an $\lvert O \rvert$ is the error this table
exists to prevent; it produced a published 52% that should have been 69%, and the gate
written for it inherited the same wrong denominator. The full graph, with each cardinality
counted from its CSV rather than asserted, is [`research/data-graph.ttl`](../data-graph.ttl).

| entry | $I = (D, P)$ | $T$ | $O$ (rows) | $S$ |
|--:|---|---|---|---|
| 50 | $(D_3..D_6, P_{a,g} \cdot P_{f,r})$ | $F_{\mathrm{base}}$ under perturbation of $(m, C_dA, C_{rr}, \lambda)$ | `e50_sensitivity.csv` | does ε earn its density in paper 1? ($S_T > 0.50$ to keep it) |
| 49 | $(D_3..D_6, P_{a,g} \cdot P_{f,r})$ via $O_{47}$ | $F_3^{\delta_5}$, affine in $\varepsilon_{\mathrm{coast}}$, global and per rider | `e49_affine.csv` — second-order | does the coasting limit need rescaling? |
| 48 | the published per-ride $O$ of Entries 1/31/9/12/14/16 | TOST, difference of medians, paired bootstrap | `e48_equiv.csv` (one row per comparison) — second-order | parity sentences upgraded or not |
| 47 | $(D_1 \cup D_2, P_{a,g})$ and $(D_1 \cup D_2, P_{a,g} \cdot P_{f,r})$ | F3 $\times$ {$\varepsilon_0,\varepsilon_2,\varepsilon_3$}, selected by BIC | `e47_formselect.csv` (2,141 rows; contests on 48 and 990) | **$\varepsilon_0$ retained**; nothing published moved |
| 46 | $(D_1..D_6, P_{a,g})$ and $(\cdot P_{f,r})$ | regime switch, 4 arms | `e46_switch.csv` (2,141) — a **second-order** $O = T(O_{47})$ | §3.3 vindicated; the frozen sub-3% cells cancel |
| 45 | $(D_1..D_6, P_{a,g})$ | ride-level deficit contest | `e45_ridelevel.csv` (1,039), `e45_ridelevel.paper.csv` (1,038), `e45_flatseg.csv` (396 segments) | **eq. (8)**, $k$ = 0.0051 |
| 44 | $(D_1..D_6, P_{f,r})$ | occupancy sigmoid, split-half | `e44_scurve_cells.csv` (153 cells), `e44_scurve_fits.csv` (9 rider-halves) | $s_{50}$ separates the populations |
| 43 | $(D_6, P_{a,g} \cdot P_{f,p}(m))$ | F1–F4, $F_\mathrm{base}$; inversion; occupancy | `skc_comparison.csv` (743), `skc_invert.csv` (743), `skc_descent_occupancy.csv` (2,193), `skc_eps_vs_pedal.csv` (1,038) | **Table 1, Table 3, Tables 5–6**; 3.16 vs 3.15 |
| 42 | $(D_1..D_5, P_{f,r})$ | F3, lumped $\varepsilon_d$ | `e42_lump.csv` (1,378) | the hand recipe stops recommending it |
| 41 | $(D_1..D_5 \text{ routes}, \mathrm{DEM})$ | F3 on planner profiles | `e41_dem_route.csv` (1,188) | **paper 2's headline** |
| 40 | $(D_1..D_5, P_{f,r})$ | roller covariate | `e40_roller.csv` (1,409) | roller recycling |
| 39 | $(D_1..D_5, P_{f,r})$ | deconfounded $\tau$-sweep | `e39_tau_reg.csv` (1,409) | momentum vs measurement |
| 38 | $(D_1..D_5, P_{f,r})$ | deadband $\tau$-sweep | `e38_tau.csv` (1,409) | $\tau^*$ vs $v_f^2/2g$ |
| 37 | — | hypothesis note | no run | KE-equivalent height |
| 36 | $(D_1..D_5, P_{f,r})$ | $\varepsilon_0$ regressed per dataset | `e36_eps0.csv` (1,400) | 0.13 survives two regressions |
| 35 | $(D_1..D_5, P_{f,r})$ | F3 vs $F_\mathrm{base}$ residual | `e35_residual.csv` (1,409) | where the missing 4–5 points live |
| 34 | $(D_1..D_5, P_{f,r})$ | occupancy sigmoid | `scurve_deficit.csv` (1,287) | $\varepsilon_0$ as a pedalling probability |
| 33 | $(D_1..D_5, P_{a,g} \cdot P_{f,r}(m, C_{rr}, C_dA))$ | inversion + F1–F4 | `perride_invert.csv` (1,409) | **Tables 5 and 6** |
| 32 | — | review | no new $O$ | the un-gated numbers were where the rot was |
| 31 | $(D_1, P_{a,g})$ | F1–F4, $F_\mathrm{base}$ | `longoes_frozen.csv` (44) | **Table 2's blind block**; the D2∩D5 discovery |
| 30 | $(D_2..D_5, P_{a,g} \times \mathrm{grid})$ | $F_\mathrm{base}$ under the same sweep | `param_sweep_canon.csv` (48) | Tier B |
| 29 | $(D_2..D_5, P_{a,g} \times \mathrm{grid})$ | F3, $C_dA \times C_{rr} \times \rho$ | `param_sweep.csv` (432 corpus×combination) | the sensitivity envelope |
| 28 | — | package refactor | no $O$ | one implementation for all harnesses |
| 27 | — | $G$ = 9.7864 re-baseline | every $O$ regenerated | ≤ 0.2 pp; **$\hat m \cdot g$ is the invariant** |
| 26 | $(\mathrm{OSM} + \mathrm{DEM}, P_{a,g})$ | v2Edge on real endpoints | `e26_grid.csv` (86), `e26_portal_profiles.csv` (922), `e26_detour.csv` (321) | the direction ladder; portals |
| 25 | — | — | no new $O$ (imported verbatim) | grid-connectivity note |
| 24 | — | literature review | no $O$ | what an ascent measurement is worth |
| 23 | — | move-grid connectivity | no new $O$ (imported note) | connectivity bias in terrain mode |
| 22 | every $O$ above | stratified bootstrap, B = 10⁴ | — | **every published median AND its 95% band** |
| 21 | $(\mathrm{DEM}, P_{a,g})$ | v2Edge, three scales | `scale_trio.csv` (922) | **the scale prescription** (paper 2/3) |
| 20 | $(\mathrm{DEM}, P_{a,g})$ | v2Edge + smoothing sweep | `goal_calibration.csv` (864) | the ±5%/±2% goal; anchor constants |
| 19 | $(\mathrm{DEM}_{5\,\mathrm{m}}, \mathrm{DEM}_{30\,\mathrm{m}})$ | v2Edge | `igc_resolution_test.csv` (922) | the resolution gap |
| 18 | $(D_1..D_5, P_{a,g})$ | v2Edge (unclamped) | `regime_comparison.csv` (1,402) | correction: the app's per-edge $\varepsilon$ never clamps |
| 17 | $(D_1..D_5, P_{a,g})$ | regime-decomposed / v2Edge | `regime_comparison.csv` (1,402) | the regime split does not beat the champion |
| 16 | $(D_5, P_{a,g} \cdot P_{f,p}(m))$ | F1–F4, $F_\mathrm{base}$ | `danlessa_comparison.csv` (636 rows, 621 clean) | Table 3's D5 column |
| 15 | $(D_1 \cup D_3 \cup D_4, P_{f,p})$ | physics inversion + wind | `cda_estimate.csv` (3), `param_fit.csv` (4) | Table 4's fitted constants |
| 14 | $(D_4, P_{a,g} \cdot P_{f,p}(m))$ | F1–F4, $F_\mathrm{base}$ | `jaam_comparison.csv` (219) | Table 3's D4 column |
| 13 | $(D_1 \cup D_3, P_{a,g} \cdot P_{f,p}(m))$ | time model $x^* = x + k_+h_+ - k_-h_-$ | `time_comparison.csv` (542) | gated, but out of paper 1 |
| 12 | $(D_3, P_{a,g} \cdot P_{f,p}(m))$ | F1–F4, $F_\mathrm{base}$ | `ppaz_comparison.csv` (441) | Table 3's D3 column |
| 11 | — | — | no new $O$; every $O$ above regenerated | ≤ 0.3 pp shifts across the board |
| 10 | $(D_2, P_{a,g})$ | $\varepsilon$ from the descent balance | `eps_sp.csv` (59) | $\varepsilon_f$ = 0.20 |
| 9 | $(D_2, P_{a,g})$ | F1–F4, $F_\mathrm{base}$ | `censo_comparison.csv` (69 rows, 62 clean) | Table 3's D2 column |
| 8 | $(D_1, P_{a,r})$ | $\varepsilon$ from geometry | `eps_hypothesis.csv` (44) | **$\varepsilon_0$ = 0.13** |
| 7 | $(D_1, P_{a,r})$ | sustained-climb balance | `model_comparison.csv` (44) | $k_h$ |
| 6 | $(D_1, \mathrm{DEM})$ | elevation substitution | `harness/dem/` products | `dem-elevation-comparison.md`; $k_\mathrm{DEM}$ |
| 5 | $(D_1, P_{a,r})$ | F3 (deadband $\tau$ = 2 m) | `model_comparison.csv` (44) | scoreboard champion row; $\tau$ = 2 m |
| 4 | $(D_1, P_{a,r})$ | F2, $v_f$ variants | `model_comparison.csv` (44) | scoreboard $v_f$ rows |
| 3 | $(D_1, P_{a,r})$ | F2 (climb-fraction $\alpha$) | `model_comparison.csv` (44) | scoreboard `cf` rows |
| 2 | $(D_1, P_{a,r})$ | F1–F4, $F_\mathrm{base}$ | `model_comparison.csv` (44) | scoreboard baseline row |
| 1 | $(D_1, P_{a,r})$ | F1–F4, $F_\mathrm{base}$ | `model_comparison.csv` (44) | the running scoreboard |

Entries with no $O$ are reviews, registrations, imported notes or refactors — they change
what the other rows *mean* without producing a per-ride table of their own.

---

---

## 2026-07-30 — Entry 50: is ε worth its density? — a variance decomposition of F1–F4's error over (m, C_dA, C_rr, ε)

**Lineage** — $I$: $(D_3..D_6, P_{a,g} \cdot P_{f,r}(m, C_{rr}, C_dA))$ · $T$: $F_1$–$F_4$ under parameter perturbation · $O$: `e50_sensitivity.csv` · $S$: whether the ε research belongs in paper 1 or in a letter of its own

*Prompt (Danilo): "Estimate the parameters sensitivity on first and second order on O
prediction error… where the parameters of interest are (m, CdA, Crr, eps), where T is to be
F_base, and eps comes from it. If the sensitivity towards eps is less than 40% parametric
uncertainty, then I would argue us to be content with F_base on the article, and push the
entire research on eps forms towards a new article (or letter)." On the threshold's reading:
"[ε's share of total variance] is what i want."*

### Pre-registration (written before any perturbation was run)

**The question is editorial, and the instrument is physical.** Paper 1 spends a large share of
its density on the deficit — its derivation, its ledger identity, four contested forms, three
journal entries of contest. That expenditure is justified only if ε is a *material lever on
prediction error*. If it is not, the article is paying density for a theoretical result whose
practical claim is small, and both halves would be better served apart: a shorter empirical
paper 1, and a letter that gets to be properly theoretical.

**The transformer is $F_1$–$F_4$, not $F_{\mathrm{base}}$** (Danilo's correction, before the
run). That is the better design and it removes two compromises the first draft needed.

*ε becomes a real parameter.* The simulation has no ε, which forced an awkward proxy — a
multiplier on descent power, with ε derived from the resulting ledger. The closed forms take ε
directly, so it is perturbed as itself and no proxy has to be defended.

*A full Sobol becomes affordable.* $F_{\mathrm{base}}$ is a forward integration per ride, which
made anything beyond a local expansion unaffordable. The closed forms reduce, per ride and per
form, to a handful of **precomputed geometry aggregates** — $x$, $x_{\mathrm{flat}}$, $h_+$,
$h_-$ (each form with its own: F1 charges aero on all $x$, F2–F4 on $x_{\mathrm{flat}}$, F3 on
the deadband-smoothed profile, F4 on the scalar-corrected one). After that precomputation
$E(\theta)$ is closed-form arithmetic plus one bisection for $v_f$, so a genuine Sobol design
runs over every ride rather than a subsample. The local-quadratic compromise is withdrawn.

*The one nonlinearity, which is also the interaction channel.* $E$ is **exactly linear in ε**
(established in Entry 47: $\varepsilon$ enters only through $-\beta\varepsilon h_-$), and linear
in $m$ and $C_{rr}$ through $\alpha_r$ and $\beta$. The coupling comes through $v_f$: the flat
reference speed is solved from the flat power against $(m, C_{rr}, C_dA)$, and it then re-enters
$\alpha_a$ quadratically. So every interaction term in this analysis has one physical origin, and
the second-order result is a statement about **how much the aero term's speed anchor entangles
the parameters** — which is exactly the $(\alpha, \varepsilon)$ pairing the paper already
describes qualitatively.

**Four forms is a new dimension, and an informative one.** ε's *share* is not a property of the
data alone; it depends on how much OTHER error the form has left. F1 carries the uncorrected
climb-aero overcharge and F2–F4 progressively remove error, so the same absolute ε effect
occupies a growing share as the model improves. Reporting all four gives a
sensitivity-versus-model-quality curve, and it guards against the trap of reading a large share
as importance when it is really the residue of a good model.

**The decision rule is applied to $F_3$** — the proposed law, the one that ships, the one the
tables lead with. F1, F2 and F4 are reported for context and for the curve; they do not vote.

**Input ranges, empirical rather than invented** — the 5th/median/95th percentiles of the
per-ride inversions actually observed on D3–D5, plus ε's measured across-rider spread:

| parameter | 5th | median | 95th |
|---|--:|--:|--:|
| $m$ (kg) | 66.5 | 74.7 | 101.9 |
| $C_dA$ | 0.149 | 0.358 | 0.526 |
| $C_{rr}$ | 0.0069 | 0.0080 | 0.0112 |
| ε | 0.08 | — | 0.30 |

**A caveat that must be stated before the run, because it is the result's main weakness:** a
variance decomposition ranks parameters partly by *how wide their assumed ranges are*. These
ranges are empirical, which is the right choice for a deployment question, but $C_dA$'s spans a
factor of 3.5 and will plausibly dominate for that reason alone. The entry therefore also
reports the decomposition under an alternative parameterisation (±1 SD rather than 5–95
percentile) and the verdict must hold under both, or it is a statement about the ranges rather
than about the model.

**Decision rule, registered.** $S_T(\varepsilon) \leq 0.50$ sends the ε research to a letter;
ε must exceed **half of total prediction-error variance** to keep its place in paper 1.
(Raised from 0.40 by Danilo before the run.)

That is a deliberately demanding bar and its character should be stated rather than discovered
later. With four parameters an equal split is 0.25 each, so 0.50 asks ε to explain **more than
$m$, $C_dA$ and $C_{rr}$ combined** — to be the dominant parameter, not merely an important
one. The stance it encodes is defensible and worth naming: density in a paper about *prediction*
is reserved for effects that dominate prediction.

**But it changes what this entry is.** At 0.40 the threshold was doing discriminating work; at
0.50, given Entry 45's 0.17 pp margin and Entry 49's unidentified form, the outcome is close to
foreseeable and the decision is largely already made. The entry's value therefore shifts from
*deciding* to (i) quantifying **by how much** ε falls short, which is the number the letter will
need to justify its own existence, and (ii) the second-order structure, which nobody has
measured and which no prior entry predicts. Recording this so the entry is not later read as a
test that discriminated when it mostly confirmed.

It also raises the stakes on P3: if ε and $C_dA$ cannot be separated, ε's "share" is ill-defined
and **no threshold can be applied cleanly in either direction** — which would be a more
interesting result than either verdict.

**The consequence, in Danilo's later and simpler words: "If the effect is dominant, we include
on this paper, else, it is a future direction of research."**

- **If ε exceeds 0.50**: it is the dominant lever and the deficit work stays in paper 1.
- **If ε falls at or below 0.50**: it becomes a **future direction of research** — not a
  commitment to write a letter, and not a judgement that the work is wrong. Paper 1 then ships
  **a flat constant ε** (Danilo, before the run — *"my idea was actually to just use the flat
  constant. At most we'll cite some of our developments during discussion"*). That is a deeper
  cut than keeping the frozen $\varepsilon_0$: the coasting limit, the deficit, the dynamic
  estimator and the four-form contest all leave paper 1 together, surviving as a citation in the
  discussion. What remains is one number.

  **Which raises a question the fallback does not answer for free: WHICH flat constant?**
  $\varepsilon_f = 0.20$ was selected on D2 — urban stop-go, and in-sample there. Entry 49
  measured the best flat ε on *real descents* under exactly this entry's parameter class
  ($P_{f,r}$) at **0.344 [0.292, 0.394]**, an interval that **excludes 0.20**. So the fallback
  inherits a calibration decision of its own, and the honest reading is that $\varepsilon_f$ is
  regime-specific rather than universal. This entry should report the best flat constant per
  corpus alongside the sensitivity result, since the fallback branch needs it.

  **And it reaches further downstream than paper 1.** Danilo: *"flat constant is all we need for
  Article 2 and Article 3 after all."* For A2 that is simply true — the DEM paper measures what
  an elevation-source swap costs, and the ε it carries is a passenger. For A3 it is stronger
  than a simplification: **the grade-local ε is precisely what creates the problems A3 exists to
  solve.** A per-edge cost built on $\varepsilon(s) = \mathrm{clamp}_{01}(\min(1,(\alpha/\beta)/s) -
  \varepsilon_0)$ is where the clamping question, the scale-dependence and the dead-clamp finding
  of Entry 18 all live. With a flat ε the per-edge cost collapses to
  $\alpha\,\Delta x + \beta(\Delta h_+ - \varepsilon_f \Delta h_-)$ — linear in edge geometry,
  scale-free in ε, and additive along a path without qualification. A large part of A3's stated
  difficulty would simply not arise.

  That cuts both ways and the entry should say so. The deployed Simujaules router uses the
  grade-local form today, so adopting a flat constant is a change to a **deployed cost
  function**, not only to a manuscript — and the fair comparison then owed is flat-vs-grade-local
  *at the edge scale*, which is A3's own experiment and not this one's.

*(This supersedes the prompt's original phrasing, "be content with $F_{\mathrm{base}}$ on the
article". That phrase is ambiguous in this project's notation — $F_{\mathrm{base}}$ is the
forward simulation, while the sense intended was closer to "the incumbent form, unrefined". The
later wording carries no such ambiguity and is the operative one.)*

**The question that now settles it most directly — promoted to primary.** With a flat constant
as the fallback, the operative comparison is no longer "does ε matter" but **"does the
*geometry-derived* ε beat a flat number by enough to justify its density?"** Under $P_{f,r}$,
does the dynamic $\varepsilon_d$ beat a flat $\varepsilon_f$ **at all**? §3.3.2 already reports P. Paz's 34%
descent-term margin collapsing to a tie under his fitted constants, and Entry 46 found
$\varepsilon_f$ winning outright below 3% under honest physics (3.37 against 5.90). If the
dynamic estimator's advantage over a constant is ≈ 0 under the parameter class the article
increasingly favours, then the coasting-limit apparatus has no *predictive* claim left in paper
1 regardless of what the variance decomposition says.

**Predictions.**

- **P1**: $C_dA$ dominates, and largely because its empirical range is widest — testable, since
  the ±1 SD parameterisation should shrink its share more than the others'.
- **P2**: $S_T(\varepsilon) \leq 0.50$, so the decision rule fires toward the letter. Stated with a
  declared bias: three entries already point this way (Entry 45's 0.17 pp margin, Entry 46's
  finding that the ε choice and the parameter class trade against each other, Entry 49's
  unidentified affine form), and Danilo holds this hypothesis. **That makes the refuting outcome
  the one to state clearly: if $S_T(\varepsilon) > 0.50$, or if the ε–$C_dA$ Hessian cross
  term is large enough that ε cannot be separated from the physics at all, the ε research stays
  in paper 1 and this entry has argued against its own author.**
- **P3**: the largest off-diagonal Hessian term is ε–$C_dA$, the pairing Entry 46 found
  reversing verdicts. If so, "ε's share" is partly ill-defined and the entry must say so rather
  than report a clean number.

*Failure modes.* If the local expansion and the subsample Sobol disagree, the local result is
withdrawn. If the verdict flips between the two range parameterisations, no verdict is issued —
the answer would be a statement about assumed uncertainty, not about the model.

**What this entry does NOT decide.** Whether the ε decomposition is a scientific contribution.
Low predictive sensitivity argues for *deferring* it out of an empirical paper, not for
devaluing it — every external reviewer named the coasting-limit/deficit decomposition the
paper's most novel theoretical result, and a low variance share would be evidence about its
predictive leverage only. "Future direction of research" is therefore the honest label: the
question of what form the deficit takes stays open and interesting, and stops being paper 1's
burden to carry.

---

## 2026-07-30 — Entry 49: the affine deficit $\delta_5 = \varepsilon_{\mathrm{coast}} k_1 + k_2$ — global vs per rider

**Lineage** — $I$: $(D_3..D_6, P_{a,g} \cdot P_{f,r}(m, C_{rr}, C_dA))$ via $O_{47}$, with $(\cdot P_{f,p}(m))$ as a disclosed secondary · $T$: $F_3^{\delta_5}$, fitted globally and per rider · $O$: `e49_affine.csv` ($O_{49} = T(O_{47})$) · $S$: whether the coasting limit needs rescaling, and whether that rescaling is a rider property

*Prompt (Danilo): "assume $\delta_5 = \varepsilon_{\mathrm{coast}} k_1 + k_2$, where $k_1$ and
$k_2$ can be fitted both globally or per rider. Test it against D3/D4/D5/D6 when fitting
globally and per rider."*

*Label kept as given. The published family runs $\varepsilon_0$–$\varepsilon_3$, so this leaves
a gap at 4; renaming it would have made the journal disagree with the request that created it.*

### Pre-registration (written before the form was fitted)

**What the form is, algebraically.** Since $\varepsilon_d = \varepsilon_{\mathrm{coast}} - \delta$,

$$\delta_5 = k_1\varepsilon_{\mathrm{coast}} + k_2 \quad\Longrightarrow\quad
\varepsilon_d = (1 - k_1)\,\varepsilon_{\mathrm{coast}} - k_2 \tag{9}$$

so $\delta_5$ is **an affine rescaling of the coasting limit**: $k_1$ shrinks it, $k_2$ offsets
it. Two consequences fix what the test can and cannot show. First, $\delta_5$ **nests** the
refitted constant — at $k_1 = 0$ it *is* $\varepsilon_0$ with a free value — so it can never be
worse in sample, and the only interesting question is whether $k_1$ differs from zero by enough
to pay for its parameter. Second, it does **not** nest $\varepsilon_2 = k/\bar s$: the
grade-inverse form is not affine in $\varepsilon_{\mathrm{coast}}$, so the two are genuine rivals
rather than nested alternatives.

**Population.** D3–D6 only, as asked — the evaluation corpora, seven riders (D3, D4, D5, and
D6's four counted individually). $\sigma$: parse + power + $\bar s \geq 3\%$, matching Entries
45 and 47 so the numbers are comparable; $\lvert O \rvert$ is expected to be **990**, the count
Entry 47 established. A secondary run on all rides regardless of $\bar s$ is reported
separately and labelled, because Entry 46 showed the sub-3% regime behaves differently.

**Two fits, as asked.** *Global*: one $(k_1, k_2)$ for all seven riders — 2 free parameters.
*Per rider*: one pair each — 14 free parameters. Baselines: $\varepsilon_0$ frozen at 0.13
(0 parameters), $\varepsilon_0$ refitted (1), $\varepsilon_2 = k/\bar s$ (1).

**Instrument.** As Entry 47, so the entries are comparable: BIC under a Laplace likelihood on
the signed $\Delta\%$ energy residuals, parameters by LAD on that same quantity, deterministic
refining grid, $\Delta$BIC < 2 to the fewest parameters. Every form is *also* fitted in deficit
space against the clamped $\varepsilon_{\mathrm{coast}} - \varepsilon_{\mathrm{bal}}$ and
reported beside it — Entry 47 found the two spaces disagree by a factor of 2.5–3, and a form
fitted on energy absorbs bias rather than measuring pedalling. **Held-out is the deciding
statistic here, not BIC**: with 14 parameters the per-rider arm is in-sample by construction,
so it is scored on chronological split-halves (fit on one half of a rider's rides, score the
other, both ways) exactly as Entries 44 and 47 did.

**Predictions.**

- **P1** — $k_1 > 0$. The coasting limit over-credits recovery: it clamps to 1 on gentle
  descents, and gentle descents are where riders pedal ([§3.2.3](#3.2.3) sees this on urban
  rides; Entry 46 sees the same over-refund on sub-3% rides under honest physics). If so, the
  geometry needs *shrinking*, and $k_1$ measures by how much.
- **P2** — the global arm beats $\varepsilon_0$ on BIC, since it nests the refitted constant and
  P1 says the extra parameter buys something real.
- **P3** — the per-rider arm wins in sample and **fails to beat the global arm out of sample**.
  Seven riders cannot support 14 parameters, and Entry 47 already dropped $\varepsilon_1$ (the
  rider constant) for this reason. If P3 is wrong — if per-rider transfers — that is the
  interesting result, because it would make the deficit a rider property rather than a
  route one, which is the opposite of what $\varepsilon_0$'s universality assumes.

*Failure modes.* If $k_1 \approx 0$ within its CI, $\delta_5$ collapses to a refitted constant
and should be reported as such, not dressed up as a new form. If the global arm's held-out
error is no better than $\varepsilon_2$'s, the affine form is a more complicated way to buy
nothing and does not enter the paper.

**Not registered.** No change to any published column. Whatever this finds, paper 1's shipped
deficit stays $\varepsilon_0$ until a *calibration-side* selection says otherwise — that was
Entry 47's protocol and this entry does not reopen it.

### Amendment (2026-07-30, before the P_{f,r} run, after the P_{a,g} one)

*Danilo: "The intended analysis is to be D3 to D6 over $P_{f,r}$."*

The registration above wrote the input as $(D_3..D_6, P_{a,g} \cdot P_{f,p}(m))$ — the frozen
priors. That was my reading of the request, and it was wrong: the intended parameter class is
**$P_{f,r}$, the per-ride inverted regime-consistent physics**. The primary arm is re-run under
it and is what the verdicts below are scored on.

Two disclosures, because the ordering matters:

1. **The $P_{a,g}$ arm was run and seen first.** It is reported below as a labelled secondary
   rather than deleted — discarding a result I have already looked at would be the worse
   choice, and the two together are informative precisely because Entry 46 found the parameter
   class capable of reversing a verdict about $\varepsilon$.
2. **Predictions P1–P3 were registered before either arm was fitted** and are not restated or
   adjusted now. The $P_{f,r}$ arm is therefore a clean test of them in the sense that matters
   (no prediction was written after seeing data), while carrying the caveat that a *related*
   arm had been seen.

### Results (run 2026-07-30, `e49_affine.py`; primary = $P_{f,r}$, $\lvert O \rvert$ = 990)

| form | par | fitted | BIC | med $\lvert\Delta\%\rvert$ | signed | **held-out** | $\varepsilon \notin [0,1]$ |
|---|--:|---|--:|--:|--:|--:|--:|
| $\delta_5$ per rider | 14 | (below) | **8171** | 4.37 | −1.05 | 4.38 | 0.2% · on a bound |
| flat $\varepsilon$ fitted | 1 | 0.3444 | 8842 | 5.08 | −0.46 | 5.05 | 0% |
| $\delta_5$ global | 2 | $k_1$ = 0.922, $k_2$ = −0.311 | 8847 | 5.02 | −0.50 | 5.04 | 0% |
| $\varepsilon_2 = k/\bar s$ | 1 | 0.0032 | 8968 | 5.12 | −2.24 | 5.08 | 0% |
| $\varepsilon_0$ refit | 1 | 0.0665 | 8995 | 5.52 | −2.57 | 5.55 | 0% |
| **$\varepsilon_0$ frozen (0.13)** | **0** | — | 9052 | **4.94** | **+0.24** | **4.94** | 0% |

AIC, added alongside (Danilo, post-registration): 8103 / 8837 / 8838 / 8963 / 8990 / 9052 in the
same row order. At $n = 990$ the penalties are $k\ln n = 6.9k$ against $2k$, so AIC charges a
third of what BIC does — and **nothing reorders**. The flat constant still edges $\delta_5$
(8836.9 vs 8837.5, a smaller gap than BIC's 5.5 but the same sign), and the per-rider arm still
leads on both criteria while failing every other check. Where a conclusion here depends on the
penalty, it is the *size* of $\delta_5$'s defeat, never its direction.

**The two-parameter fit is unidentified — this is the headline.** Bootstrapping the global fit
(stratified by rider, B = 10⁴, seed 45; the objective is *linear* in $(k_1, k_2)$, so LAD is a
median regression solvable by IRLS and the refits are affordable):

| quantity | point | 95% CI |
|---|--:|:--|
| $k_1$ | 0.9225 | [0.464, 2.727] |
| slope $1 - k_1$ | 0.0775 | **[−1.727, +0.536]** |
| intercept $-k_2$ | 0.3115 | [0.095, 1.214] |
| **flat $\varepsilon$ (1 parameter)** | **0.3444** | **[0.292, 0.394]** |

$k_1 > 0$ is solid — the interval excludes zero, so **P1 holds**: the coasting limit needs
shrinking. Everything past that is not supported. The slope's interval runs from strongly
*inverted* to substantially positive, because $k_1$ and $k_2$ trade off against each other; the
form cannot say by how much the geometry should be rescaled. *An earlier draft of this entry
read the point estimate (slope 0.078) as "the fit nearly deletes the geometry". That was an
overclaim on an interval this wide, and it is withdrawn.* What the data do identify is the
**one**-parameter answer, and sharply: a flat $\varepsilon = 0.344$ [0.292, 0.394].

**$\delta_5$'s second parameter buys nothing.** Against the flat constant it nests at $k_1 = 1$,
and the comparison is unambiguous: the flat form has the **lower** BIC (8842 vs 8847) with half
the parameters, and an identical held-out error (5.05 vs 5.04). The affine form is a flat
constant carrying one unidentified extra parameter. **P2 fails on the honest comparison** —
$\delta_5$ beats $\varepsilon_0$ on BIC, but so does the strictly simpler form it contains.

**And the fitted answer does not generalise.** Both fitted forms want to discard or discount
$\varepsilon_{\mathrm{coast}}$, yet frozen $\varepsilon_0$ — which keeps the geometry at *full*
weight and subtracts 0.13 — has the best held-out error of every cheap form (4.94 against
5.04/5.05/5.08/5.55) and by far the smallest bias (+0.24 against −0.46, −0.50, −2.24, −2.57).
So the in-sample pull toward deleting the geometry is an artefact of fitting, not a property of
the data: at full weight the geometry helps, and the sample cannot resolve any better weight
than the one already published.

**P3 fails on its metric and should not be believed.** Per-rider held-out (4.38) beats global
(5.04), so a rider's rescaling does transfer to that rider's other rides. Four reasons that is
not what it looks like: the fits **disagree on sign** ($k_1$ from −1.08 to +2.67 across seven
riders); one rider stays **pinned to a bound** after the box was widened from $\pm0.6$ to
$\pm1.5$; it is the only form that leaves the physical interval (0.2% of rides get
$\varepsilon_d \notin [0,1]$, refunding more than the descent holds); and within-rider held-out
never tests a **new** rider, which is what deployment needs — [§3.2.2](#3.2.2) already declines
rider-parameter forms on exactly that ground. Fourteen parameters bought 0.56 pp.

**Verdict: nothing here enters paper 1.** The affine form is unidentified and dominated by the
constant it contains; the per-rider arm is incoherent; the incumbent $\varepsilon_0 = 0.13$ has
the best held-out error and bias of every form with fewer than 14 parameters. This is the third
entry running (47, 46, 49) in which the published constant survives a challenger.

**One number worth keeping.** On real descents under honest per-ride physics the best *flat*
$\varepsilon$ is **0.344 [0.292, 0.394]** — an interval that excludes the published
$\varepsilon_f = 0.20$. No contradiction: $\varepsilon_f$ was selected on D2, urban stop-go
riding, a different regime from $\bar s \geq 3\%$ open descents. But it says the flat constant
is regime-specific, and 0.20 should not be carried onto real descents as if it were universal.

**Secondary — every ride ($\lvert O \rvert$ = 2,028).** Same shape; with the sub-3% rides
included $\varepsilon_2$ (held-out 4.23) beats frozen $\varepsilon_0$ (5.48), reversing the
gated ordering — consistent with Entry 46, where the sub-3% band is exactly where the parameter
class and the $\varepsilon$ choice trade against each other.

**Disclosed — the $P_{a,g}$ arm** (run first, on my misreading). Global $k_1$ = 0.712
[0.256, 2.944] — same story, same width. Held-out: per rider 3.98, $\varepsilon_2$ 4.13, global
4.15, frozen $\varepsilon_0$ 4.21. The two arms agree on everything load-bearing ($k_1 > 0$ but
unidentified; per-rider incoherent; nothing worth shipping) and disagree on the ordering of the
cheap forms — the Entry-46 lesson restated: when the question is about $\varepsilon$, the
parameter class is not a background detail.

---

## 2026-07-30 — Entry 48: formal equivalence testing (TOST) for the parity claims — pre-registration

**Lineage** — $I$: the published per-ride $O$ of Entries 1/31/9/12/14/16/33 · $T$: TOST on the difference of medians under paired resampling · $O$: `e48_equiv.csv` (one row per registered comparison; $O_{48} = T(O_{\text{published}})$) · $S$: upgrades, or fails to upgrade, paper 1's parity sentences

*Origin: an external review round (2026-07-29) pressed that "no detectable difference" is not
evidence of equivalence. Plan in [`research/article/paper1-equivalence.PLAN.md`](../article/paper1-equivalence.PLAN.md),
drafted as Entry 43, renumbered to 44 and then 45 as those numbers were taken by the D6
registration and the S-curve refit; 45–47 have since been used too, so this is **Entry 48**.*

### Pre-registration (written before any equivalence CI was computed)

**The question.** Paper 1 repeatedly says the closed form and the simulation are
"statistically indistinguishable", with a non-significant paired sign test as the evidence.
That is an absence of evidence, not evidence of absence. Can those claims be upgraded to
formal equivalence within a stated margin — and where they cannot, is the failure to upgrade
itself reportable?

**The method.** TOST by bootstrap. For each comparison, resample rides (within corpus;
stratified for pools, matching the published pooled-CI convention exactly), compute **both**
models' median $\lvert\Delta\%\rvert$ on the *same* resample, and take
$d = \mathrm{med}\lvert\Delta\%\rvert_{\text{law}} - \mathrm{med}\lvert\Delta\%\rvert_{\text{sim}}$.
Equivalence at $\alpha = 0.05$ is declared iff the **90% percentile CI of $d$ lies entirely
inside $[-\delta, +\delta]$** — two one-sided tests at 0.05 each are exactly the 90% CI being
contained, which is why the interval is 90% and not 95%. B = 10⁴, mulberry32, **seed 44**
(42 and 43 are taken by the published $\lvert\Delta\%\rvert$ and signed CIs; reusing one would
silently correlate this interval with those).

The estimand is the **difference of medians**, not the median of per-ride differences. The
paper's sentences compare two published medians, so that is the quantity under test; the
other estimand is a different claim and is not registered.

**The margin: $\delta = 1.0$ percentage point on median $\lvert\Delta\%\rvert$**, one value
for every comparison, no per-corpus margins.

*The plan's stated grounds were checked and are partly wrong; the corrected justification
is registered instead.* The plan asserted that 1.0 pp "is at or below every CI half-width the
paper publishes for these medians". That holds for the $n = 44$ rows (half-widths 1.4–3.7 pp)
but **fails for the pooled rows**, whose published half-widths are 0.4–0.6 pp — narrower than
the margin. Recording the corrected grounds:

1. *Operational.* On medians of 3.5–8.4%, a 1.0 pp difference does not change any decision a
   planner makes between evaluating the law per edge and running the simulation. That is the
   sense in which the two would be interchangeable.
2. *Smaller than the protocol effect.* The informed→blind shift is +4.6 pp on F3 and +3.2 pp
   on the simulation ([§3.1](#3.1)). A margin at 1.0 pp is well inside the effect of parameter
   *judgment*, so passing TOST at this margin is a weaker claim than "the protocol does not
   matter" — deliberately conservative.
3. *It straddles the published precision.* 1.0 pp sits above the pooled rows' half-widths and
   below the $n = 44$ rows'. That asymmetry is not a defect; it is precisely what makes P1 and
   P2 below the predictions they are, and it is why the margin is registered now, before any
   $d$ is computed.

**The registered comparisons.** F3 with $\varepsilon_d$ against the simulation, on: D1
informed (`model_comparison.csv`, `cfS_vs_emp` vs `canon_vs_emp`), D1 blind
(`longoes_frozen.csv`, `f3_d` vs `canon_d`), D2 frozen, D3, D4, D5 (`sm_geom` vs `canon_d` in
each corpus CSV), the D3+D4 transfer pool and the D3–D5 pool (both stratified). F4 against the
simulation only where the paper makes an F4 parity claim — D1 blind and D2 (`pm_geom`).
Everything else is exploratory and labelled so. D2's $\varepsilon_f$ rows are in-sample
(the constant was selected on D2) and any D2 verdict carries that caveat verbatim.

**Predictions.**

- **P1** — the large-$n$ pooled rows pass TOST at $\delta = 1.0$.
- **P2** — D1, informed and blind ($n = 44$), is **inconclusive**: the CI is wider than the
  margin. This is the honest expected outcome, and it converts the paper's existing
  "equivalence is not formally tested" into "a registered equivalence test is inconclusive at
  this $n$" — the same fact with a measurement attached, which is strictly more informative.
- **P3** — the mid-size per-corpus rows (D2, D3, D4, D5): no prediction. Whichever way they
  land is reported.

*Failure mode.* If a pooled row **fails** — its CI lying outside the margin on one side — the
paper's parity language for that row is **weakened**, not defended. Stated here so that the
response to a bad result is fixed before the result exists.

**Not registered.** No new physics, no refits, no per-ride difference estimands. The plan's
Phase D (error-distribution disclosure — quantiles, skew, tail counts) is **gated on Danilo's
explicit go** and is not started; if it happens it is registered as a dated amendment here
before running.

### Results (run 2026-07-30, `e48_equiv.py`, B = 10⁴, seed 44; deterministic on re-run)

| comparison | n | med law | med sim | $d$ | 90% CI | verdict |
|---|--:|--:|--:|--:|:--|---|
| D1 informed · F3 | 44 | 3.54 | 5.15 | −1.61 | [−3.34, +0.33] | inconclusive |
| D1 blind · F3 | 44 | 8.17 | 8.37 | −0.20 | [−2.14, +1.70] | inconclusive |
| D1 blind · F4 | 44 | 7.63 | 8.37 | −0.74 | [−2.17, +2.72] | inconclusive |
| D2 frozen · F3 | 62 | 7.71 | 6.63 | **+1.08** | [−0.04, +2.18] | inconclusive |
| D2 frozen · F4 | 62 | 6.45 | 6.63 | −0.19 | [−1.98, +1.59] | inconclusive |
| D3 · F3 | 441 | 5.76 | 6.76 | −1.00 | [−1.56, −0.63] | inconclusive |
| D4 · F3 | 219 | 5.49 | 5.44 | +0.04 | [−0.61, +0.43] | **equivalent** |
| D5 · F3 | 621 | 6.18 | 6.14 | +0.04 | [−0.33, +0.47] | **equivalent** |
| POOL D3+D4 · F3 | 660 | 5.63 | 6.26 | −0.63 | [−0.90, −0.33] | **equivalent** |
| POOL D3−D5 · F3 | 1,281 | 5.90 | 6.23 | −0.32 | [−0.55, −0.07] | **equivalent** |

Four equivalent, six inconclusive, **none outside the margin**. Every median reproduces its
published value (3.54 vs 3.5, 5.63 vs 5.6, 5.90 vs 5.9, …) and **no ride was dropped for
being unpaired** in any comparison — the populations behind the TOST are exactly the
populations behind the published brackets.

**P1 holds.** Both pooled rows are formally equivalent: D3+D4 at [−0.90, −0.33] and D3–D5 at
[−0.55, −0.07], each wholly inside ±1.0. The paper's headline transfer claim is now an
equivalence result rather than a failure to reject.

**P2 holds.** D1 is inconclusive on both protocols, informed [−3.34, +0.33] and blind
[−2.14, +1.70]. At $n = 44$ the interval is two to three times the margin, exactly as
registered. "Equivalence is not formally tested" becomes "a registered equivalence test is
inconclusive at this $n$" — the same fact carrying a measurement.

**P3 had no prediction; the pattern it produced is the interesting part.** *Every*
inconclusive verdict except one is inconclusive on the side where the **closed form is
better than the simulation**. D3 is the clearest: its CI [−1.56, −0.63] is wholly negative,
so the law does not merely match the simulation there, it beats it — possibly by more than
the margin, which is why equivalence cannot be declared. Reading "inconclusive" as a weakness
of the law would be exactly backwards in five of six cases.

**The exception is D2 · F3, and it should be said plainly.** Its interval [−0.04, +2.18]
allows the closed form being up to 2.2 pp *worse* than the simulation on the urban corpus.
The point estimate, +1.08, is already outside the margin. The sign test the paper currently
quotes there ($p = 0.37$) is not evidence of parity, and the TOST declines to supply the
equivalence the sentence implies. D2's parity language is softened accordingly — the
registered failure mode was written for pooled rows, but its principle (weaken, do not
defend) applies here on its own terms. F4 on the same corpus is unremarkable
([−1.98, +1.59], straddling zero), so this is specific to F3 on urban stop-go riding, where
[§3.2.3](#3.2.3) already documents that $\varepsilon_{\mathrm{coast}}$ over-credits recovery.

**Deviation from the plan, disclosed.** The implementation plan listed Table 6's
regime-consistent rows (3.9 vs 4.0) among the registered comparisons; the registration above
dropped them, and this run does not include them. The reason is that Table 6's protocol
inverts physics from the scored ride itself, so a law-vs-simulation parity claim there is a
different kind of claim — partially in-sample per ride — and mixing it into a set otherwise
made of frozen-transfer comparisons would make one margin do two jobs. Left for a later entry.

**Phase D (error-distribution disclosure) — declined by Danilo, 2026-07-30.** Not gated any
longer, and not deferred: it will not be done. The reason stands on the plan's own argument
against it — the paper already reports a signed median with a CI beside every accuracy figure
(the accuracy-and-bias rule), which carries the first-order asymmetry the disclosure would
restate, and paper 1 is dense already. Recorded here so a later reader finds a decision rather
than an open item.

---

---

## 2026-07-30 — Entry 47: which deficit form? — pre-registration of the two selections, in I/T/O/S

**Lineage** — $I$: $(D_1 \cup D_2, P_{a,g})$ and $(D_1 \cup D_2, P_{a,g} \cdot P_{f,r})$ · $T$: F3 $\times$ {$\varepsilon_0,\varepsilon_2,\varepsilon_3$}, selected by BIC · $O$: `e47_formselect.csv` (2,141 rows; contests on 48 and 990) · $S$: **$\varepsilon_0$ retained**; nothing published moved

*Prompt (Danilo), proposing the protocol and asking for feedback before any work began:
"1. Test all forms on D1 and calibrate against it. That's the 'best calibration-dataset arm',
or $\varepsilon_{d,\mathrm{train}}$; 2. Use the champion form on D1 for building tables 3–6;
3. Find the champion form for D3–D6 and add as a separate column. That would be the 'best
in-sample configuration arm'. Or $\varepsilon_{d,\mathrm{all}}$. My prediction is that
$\varepsilon_{d,\mathrm{train}}$ gives either $\varepsilon_0$ or $\varepsilon_2$." Then, on the
instrument: "Should we use BIC instead? What do you think about it?"; on widening the
calibration side to D1 ∪ D2: "Agreed"; and on the rider-constant form: "drop it".*

### The notation this entry is written in

Landed with this entry in paper 1's Terminology and its four table captions. An **input**
$I = (D, P)$ pairs a corpus with a parameter class ($P_{a,g}$ assumed-global, $P_{a,r}$
assumed-per-ride, $P_{f,r}$ fitted-per-ride, $P_{f,p}$ fitted-per-person), overrides joined by
$\cdot$. A **transformer** $T$ is a model — $F_1$–$F_4$, or $F_{\mathrm{base}}$ for the forward
simulation, which is a *peer* of the closed forms and not the reference; $T$ is the class, $F_i$ the instance. An **output**
$O = T(I)\,|\,\sigma$ is per-ride, with $\sigma$ the inclusion rule. A **statistic** $S(O)$ is
what a table prints.

The load-bearing part is $\lvert O \rvert \leq \lvert D \rvert$: a transformer preserves ride
grain but **not** population. Entry 46's own scope figure is the worked example — 52% was
computed over $\lvert D \rvert = 2{,}155$ for a claim whose $O$ covered Table 3's corpora only
($1{,}366$, giving 69%), and the gate written for it hardcoded the same wrong denominator, so
it certified the error instead of catching it. `research/data-graph.ttl` now carries the whole
lineage as a DAG with every $\lvert O \rvert$ **counted from its CSV** rather than asserted.

### Pre-registration (written before any calibration-side result was inspected)

I have deliberately not looked at any D1 ∪ D2 contest output. Entry 45's numbers are on the
*evaluation* side (D3–D6) and on the ledger target; the calibration side is untouched.

**The question.** Paper 1's deficit $\delta$ is currently the frozen constant $\varepsilon_0 =
0.13$, chosen on D1 in Entry 8 and never contested against a *form*. Entry 45 showed the
grade-inverse $\varepsilon_2 = k/\bar s$ beats it out of sample at $\bar s \geq 3\%$. That
result was found on the evaluation corpora, so it cannot select the form the paper ships.

**Two selections, run separately.**

1. $\varepsilon_d(P_{a,g})$ — $\operatorname{argmin}_\delta \mathrm{BIC}$ over
   $F_3^{\delta}(D_1 \cup D_2,\ P_{a,g})$. The frozen-protocol arm: this is the one whose
   champion may build Tables 3–6, because it never touches D3–D6.
2. $\varepsilon_d(P_{f,r})$ — $\operatorname{argmin}_\delta \mathrm{BIC}$ over
   $F_3^{\delta}(D_1 \cup D_2,\ P_{a,g} \cdot P_{f,r}(m, C_{rr}, C_dA))$. The per-ride-physics
   arm, so the form choice can be checked against a different parameter class rather than
   confounded with the frozen priors.

$\sigma$ for both: parse + power + $\bar s \geq 3\%$, which is $\varepsilon_2$'s tested domain
and the regime §3.3 nominates. Registered $\lvert O \rvert$: **48**, counted from
Entry 45's population before registration — D1 contributes 22 and D2 contributes 26. Note what
that costs: the $\bar s \geq 3\%$ gate halves the calibration corpus ($\lvert D_1 \rvert = 44
\to \lvert O \rvert = 22$), which is the whole reason BIC and not a held-out split is the
primary instrument here.

**Contestants.** $\varepsilon_0$ (frozen constant, 0 free parameters at the registered value, 1
if refitted on this population), $\varepsilon_2$ ($k/\bar s$, 1 parameter), $\varepsilon_3$
($a + b\varphi$, 2 parameters). $\varepsilon_1$ (rider constant) is **dropped**: with two
riders on the calibration side it is a two-parameter restatement of the corpus label.

**Instrument.** BIC primary, under a Laplace likelihood on the signed $\Delta\%$ residuals —
Laplace because every published statistic here is a median, and BIC because $\lvert O \rvert
\approx 48$ makes a held-out split too weak to separate one- from two-parameter forms.
$\Delta\mathrm{BIC} < 2$ is **not** a win: the fewest-parameter form takes it, which makes
$\varepsilon_0$ the default champion and puts the burden on the alternatives. Held-out error
(split-half, chronological odd/even, as Entry 44) is reported as an explicitly **underpowered
secondary** — reported because it is the quantity a reader expects, labelled because at this
$n$ it cannot decide.

**The target must match the constant.** Both selections score the *clamped* deficit
$\varepsilon_{\mathrm{coast}} - \varepsilon_{\mathrm{bal}}$ — paper 1's published quantity —
and every contestant is fitted to that same quantity. The unclamped ledger identity is a
different number (pooled median 0.253 against 0.13; $k = 0.0099$ against 0.0051) and mixing the
two produced four wrong readings across Entries 43–45. This is now a comment in the harness.

**Estimands.** Per contestant: BIC, $\Delta$BIC against the winner, free-parameter count, fitted
parameter values with 95% CIs, median $\lvert\Delta\%\rvert$ and median signed $\Delta\%$ (95%
CIs, mulberry32 seeds 42/43, B = 10⁴), and the split-half held-out median.

**Then, and only then**, $\varepsilon_{d,\mathrm{all}}$: the same contest re-run on D3–D6 and
reported as a **separate, explicitly labelled in-sample column**. It answers "what would the
best-configured law have been?" and is never the paper's headline — the Table 3 pool stays the
frozen-transfer number.

**Predictions.** P1 (Danilo's): $\varepsilon_d(P_{a,g})$ selects $\varepsilon_0$ or
$\varepsilon_2$, not $\varepsilon_3$. P2: the two selections agree on the champion — if the form
choice flips with the parameter class, the form is absorbing parameter error and no arm should
ship. P3: $\varepsilon_{d,\mathrm{all}}$ selects $\varepsilon_2$, since Entry 45 already found
it superior there; a disagreement between P1 and P3 is the interesting outcome and would say
the calibration side is too small to see what 1,038 evaluation rides can.

*Failure modes.* If $\Delta$BIC among all three is under 2, the honest outcome is "48 rides
cannot choose a form", $\varepsilon_0$ stays by parsimony, and the paper says so. If
$\varepsilon_2$ wins the calibration arm, Tables 3–6 are re-baselined under the full
propagation checklist — not patched.

**Scope.** Nothing published moves until `bootstrap_ci.py` carries a gate section for whatever
this selects.

---

### Results (run 2026-07-30, `e47_formselect.py`; |O| = 48 calibration, 990 in-sample)

**Population.** $\sigma$ reproduces Entry 45's exactly — 22/26/156/20/224/149/267/162/12
across the nine groups, 1,038 in total, ride for ride. The registered $\lvert O \rvert = 48$
is confirmed.

It was confirmed only after a correction. The first run returned 43, because I gated on the
$\bar s$ of $\varepsilon_{\mathrm{geom}}$'s own cells while Entry 45 and every published
harness gate on $\varepsilon_{\mathrm{cells}}$'. Two definitions of "mean descent grade",
disagreeing on 5 of 113 rides. The registration said a disagreement would be reported and not
silently adopted, so: the registered gate is the published one, and the champion is reported
under **both** — it does not move. Note the shape of the near-miss — the first cross-check I
wrote compared only the *survivors*, which cannot see a ride the other gate would have kept.
A one-sided check on a population question is the same error as the 52% denominator.

**Selection 1 — $\varepsilon_d(P_{a,g})$, |O| = 48.**

| form | par | fitted | BIC | $\Delta$BIC | med $\lvert\Delta\%\rvert$ | signed | held |
|---|--:|---|--:|--:|--:|--:|--:|
| $\varepsilon_2$ | 1 | $k$ = 0.0020 | 465.7 | 0.0 | 11.32 | −1.15 | 11.32 |
| **$\varepsilon_0$ frozen** | **0** | — | **465.8** | **0.0** | **9.17** | **+2.26** | **9.17** |
| $\varepsilon_0$ fitted | 1 | $c$ = 0.0556 | 466.3 | 0.6 | 11.41 | −1.47 | 11.28 |
| $\varepsilon_3$ | 2 | 0.0052, 0.3667 | 469.9 | 4.2 | 11.61 | −2.66 | 13.06 |

Champion $\varepsilon_0$, 95% CIs 9.17 [6.12, 11.83] and +2.26 [−3.42, 6.43].

**Selection 2 — $\varepsilon_d(P_{f,r})$, |O| = 48.**

| form | par | fitted | BIC | $\Delta$BIC | med $\lvert\Delta\%\rvert$ | signed | held |
|---|--:|---|--:|--:|--:|--:|--:|
| **$\varepsilon_0$ frozen** | **0** | — | **459.1** | **0.0** | **6.72** | **+0.68** | **6.72** |
| $\varepsilon_2$ | 1 | $k$ = 0.0033 | 460.9 | 1.8 | 7.85 | −1.78 | 8.23 |
| $\varepsilon_0$ fitted | 1 | $c$ = 0.0705 | 461.6 | 2.5 | 8.78 | −2.61 | 9.10 |
| $\varepsilon_3$ | 2 | 0.0875, −0.0704 | 465.5 | 6.4 | 8.27 | −2.03 | 8.60 |

Champion $\varepsilon_0$, 95% CIs 6.72 [4.69, 11.25] and +0.68 [−3.24, 5.63].

**$\varepsilon_{d,\mathrm{all}}$ — the in-sample arm, D3–D6, |O| = 990.** Both arms select
$\varepsilon_2$, and not narrowly: $\Delta$BIC 128.8 ($P_{a,g}$, $k$ = 0.0020) and 88.2
($P_{f,r}$, $k$ = 0.0032) over the frozen constant.

**Verdicts.** P1 holds — the calibration arm selects $\varepsilon_0$, one of the two Danilo
named. P2 holds — the two parameter classes agree, at both stages, so the form choice is not
absorbing parameter error. P3 holds — $\varepsilon_{d,\mathrm{all}}$ selects $\varepsilon_2$.

**P1 and P3 disagree, which the registration named as the interesting outcome**, and it says
what it was registered to say: 48 calibration rides cannot see what 990 evaluation rides can.
That is a statement about power, not about $\varepsilon_2$ being wrong — and it is the reason
the arm entitled to build the tables is the calibration arm and not the other one.

**Consequence for paper 1: nothing moves.** The champion of the only arm licensed to select
is $\varepsilon_0 = 0.13$, which is what the paper already ships. The pre-registration
endorsed the incumbent, and the value of that is precisely that it could have gone the other
way — $\varepsilon_2$ won the in-sample arm decisively, on 20× the rides.

### AIC beside BIC (added 2026-07-30 at Danilo's request, after the fact)

BIC was the registered instrument; AIC is reported beside it everywhere BIC appears, because
which penalty is used is a fact about how much evidence there is, not a detail. Both are
$-2\log L$; they differ only in the per-parameter charge, $k\ln n$ against a flat $2k$. At
$n = 48$ that is 3.87 against 2, so BIC charges nearly twice as much.

| arm | form | BIC | $\Delta$BIC | AIC | $\Delta$AIC |
|---|---|--:|--:|--:|--:|
| $P_{a,g}$ | $\varepsilon_2$ | 465.7 | 0.0 | **463.8** | 0.0 |
| $P_{a,g}$ | **$\varepsilon_0$ frozen** | 465.8 | 0.0 | 465.8 | **1.9** |
| $P_{f,r}$ | **$\varepsilon_0$ frozen** | 459.1 | 0.0 | 459.1 | 0.0 |
| $P_{f,r}$ | $\varepsilon_2$ | 460.9 | 1.8 | 459.1 | 0.0 |

**The champion does not change** — under AIC's own $\Delta < 2 \Rightarrow$ fewest parameters
rule, $\varepsilon_0$ still takes both arms. But the margin in the $P_{a,g}$ arm is
$\Delta$AIC = **1.9 against a threshold of 2.0**: the incumbent survives that arm by a tenth of
a unit. Under the weaker penalty $\varepsilon_2$ has the lowest raw AIC there, and only the
parsimony tie-break keeps $\varepsilon_0$. Stated plainly because "both selections return
$\varepsilon_0$" is true but, on one arm, barely.

*(An intermediate reading of these numbers — that AIC "flips the champion" — compared raw AIC
minima and forgot the tie-break the protocol applies to whichever criterion is used. Withdrawn.)*

### Three findings that were not registered

**1. Fitting $\delta$ against energy does not recover $\delta$.** Every form was fitted twice:
against the energy residual (primary) and against the measured deficit (how
$\varepsilon_0 = 0.13$ was originally derived). On D3–D6 the deficit-space fits land at
$c$ = 0.1339 and $k$ = 0.0052 — reproducing the published 0.13 and 0.0051 almost exactly,
from an independent implementation. The energy-space fits land at $c$ = 0.0441 and
$k$ = 0.0020, a factor of 2.5–3 lower. The gap is bias absorption: the frozen law
over-predicts (signed +1.92 with $\varepsilon_0$), and a $\delta$ free to move in energy space
buys that bias down by crediting recovery the descents did not deliver. **A $\delta$ fitted on
energy is no longer a measurement of descent pedalling**, which is the physical claim
§1.3.2 rests on. The published constants come from deficit space, and this is the argument
for keeping them there.

**2. $\Delta$BIC's scale is not the reader's scale.** On D3–D6, $\varepsilon_2$ beats
$\varepsilon_0$ by $\Delta$BIC = 128.8 — decisive by any convention — and by **0.17 pp** of
median error (4.04 vs 4.21). In the $P_{f,r}$ arm it is starker: $\varepsilon_2$ wins on BIC
by 88.2 while being *worse* on the median (5.04 vs 4.94). BIC scores the mean absolute
residual; every statistic this paper prints is a median. LAD fitting lowers the sum, which can
raise the median. Both numbers are correct and they disagree, so any future claim of the form
"$\varepsilon_2$ beats $\varepsilon_0$" must name the metric.

**3. Neither constant is bias-free, and they miss in opposite directions.** With
$\varepsilon_0$ the signed median is +1.92 ($P_{a,g}$) and +0.24 ($P_{f,r}$); every fitted form
lands between −1.3 and −2.6. Trading a small positive bias for a larger negative one is not an
improvement, which the accuracy column alone would have hidden.

### Harness note — a defect this entry caused and fixed

`INVERT_SMOKE=1` wrote to `perride_invert.csv`, the canonical file. A smoke run during this
entry overwrote it, 1,409 rows to 204, silently invalidating Tables 5–6 and the gate battery
until it was regenerated. Smoke output is now suffixed `.SMOKE`, as `skc_compare.py` already
did. The per-ride inversion was also extracted from `run_ride` into `invert_physics` so this
entry could reuse it rather than copy it; verified behaviour-neutral by diffing a smoke run
against the pre-refactor output (identical but for the filename).

---

## 2026-07-29 — Entry 46: implementing the regime switch — pre-registration

**Lineage** — $I$: $(D_1..D_6, P_{a,g})$ **and** $(D_1..D_6, P_{a,g} \cdot P_{f,r})$ · $T$: regime switch, 4 arms · $O$: `e46_switch.csv` (2,141; $O_{46} = T(O_{47})$) · $S$: the rule is right, the frozen grid's sub-3% cells are a cancellation

*Prompt (Danilo), after Entry 45 established that §3.3's regime rule is stated but never
enforced: "Are we saying that we should recommend using G only when the mean descent is above
3%, and use a flat constant for eps elsewhere?" — and, on the plan to correct the article first
and register the implementation: "ok do it and commit".*

### Pre-registration (written before any run)

**The gap.** Paper 1 §3.3 recommends dynamic $\varepsilon_d$ on mean descent grade $\geq 3\%$
and flat $\varepsilon_f = 0.20$ otherwise. **No harness implements it.** The `s̄ >= 0.03`
expressions in `ppaz_compare.py`, `jaam_compare.py`, `danlessa_compare.py` and `time_compare.py`
select reporting subsets; none switches the estimator. Every published $\varepsilon_d$ column
applies the dynamic estimator to all rides, including the 69% of Table 3's own corpora whose mean descent grade is
below 3% (52% if the count is taken over all nine corpora Entry 45 scored — the
figure first written here, with the wrong denominator for the claim) — the regime the paper says it should not be used in.

**The experiment.** Add a per-ride switch to the frozen-grid harnesses: use
$\varepsilon_d = \varepsilon_{\mathrm{coast}} - \varepsilon_0$ when $\bar s \geq 3\%$ and
$\varepsilon_f = 0.20$ otherwise, as a **new column** beside the existing unswitched ones —
nothing is overwritten. Then repeat with eq. (8)'s grade-inverse deficit in place of
$\varepsilon_0$, giving four arms: {constant, grade-inverse} × {unswitched, switched}.

**Estimands.** Per corpus and pooled: median $|\Delta\%|$ and median signed $\Delta\%$ with 95%
CIs (mulberry32, seeds 42/43, B = 10⁴), plus paired sign tests against the published
unswitched-constant column.

**Predictions.** P1: switching improves the gentle-terrain corpora (D4, D2) and barely moves
the open-road ones (D3, D5, D6) — the rule was inferred from exactly that contrast, so this is
a consistency check, not a discovery. P2: with the switch in place, the grade-inverse deficit
beats the constant on the open corpora, because it is then only ever evaluated where Entry 45
found it accurate. P3: unswitched, the grade-inverse deficit is *worse* than the constant,
because two-thirds of Table 3's rides fall in the band where it under-predicts by 20–70%. **P3 is the one that
matters** — if it holds, eq. (8) is unusable without the switch, and the article's conditional
framing is correct rather than merely cautious.

*Failure modes.* If switching changes nothing anywhere, §3.3's rule is decorative and should be
dropped from the paper rather than implemented. If it changes the headline pooled numbers, this
becomes a re-baseline with the full propagation checklist and gates, not an addendum.

**Scope.** Nothing published is overwritten until gates exist. `bootstrap_ci.py` is still held
open by the parallel paper-2 line; Entry 45's constant and this entry's columns both need gate
sections before any of it reaches a table.

*(Correction, Entry 47: "`bootstrap_ci.py` is still held open by the parallel paper-2 line" was
wrong when written — the battery had already landed in `e827330`. Entries 43–45 were gated in
§3j/§3k the same day. The registration's substance stands; only the blocker did not exist.)*

### Results (run 2026-07-30, `e46_switch.py`; 2,141 rides, 1,103 below the gate)

Built as four columns beside the existing ones, nothing overwritten:
$\varepsilon_d$ or eq. (8)'s $k/\bar s$, each unswitched or switched to
$\varepsilon_f = 0.20$ below $\bar s = 3\%$. Scored under **both** parameter classes.

**The two parameter classes reverse the answer.** Under the frozen priors
$P_{a,g}$ — the class every published column uses — switching makes things *worse*:
pooled median $\lvert\Delta\%\rvert$ 5.08 → 5.62. Under per-ride inverted physics
$P_{f,r}$ it makes them *better*: 5.51 → 4.12. Same rides, same rule, opposite verdict.

**The bias column says which is real.** On the 1,103 rides below the gate:

| $P$ | $\varepsilon$ applied | med $\lvert\Delta\%\rvert$ | signed |
|---|---|--:|--:|
| $P_{a,g}$ | $\varepsilon_d$ | 5.56 | **+0.28** |
| $P_{a,g}$ | $\varepsilon_f = 0.20$ | 6.99 | +5.90 |
| $P_{f,r}$ | $\varepsilon_d$ | 5.90 | −4.64 |
| $P_{f,r}$ | $\varepsilon_f = 0.20$ | 3.37 | **+0.11** |

Under each class exactly one choice is near-unbiased, and they are *opposite* choices.
The mechanism is visible in the numbers: below 3% the coasting limit clamps, so the
median $\varepsilon_{\mathrm{coast}}$ is 0.674 and the applied $\varepsilon_d$ is
**0.544** — against $\varepsilon_f$'s 0.20. That is a very large refund. With the
frozen $C_dA = 0.40$ (well above the 0.26–0.32 these riders actually invert to) the law
over-predicts, and a 0.544 refund cancels it to +0.28. Give the law honest physics and
the over-prediction goes away — whereupon the same refund over-shoots to −4.64, and the
modest $\varepsilon_f = 0.20$ lands at +0.11.

**So §3.3's rule is right, and the frozen grid's sub-3% cells are a cancellation.**
$\varepsilon_d$ on flat rides is not measuring recovery; it is absorbing the frozen
aero prior. This is the same disease Entry 47 found one step away — a $\delta$ fitted on
energy absorbing bias instead of measuring pedalling — and it is exactly what the
project's accuracy-**and**-bias reporting rule exists to catch. A lone accuracy column
would have read the frozen arm's 5.56 as evidence the estimator works below 3%.

**Verdicts against the registration.**

*P1 — partially, and for the wrong reason.* Switching improves the gentle corpora as
predicted (D2 8.24 → 5.71, D4 5.23 → 3.44) but does **not** merely "barely move" the open
ones: D3 worsens 5.64 → 8.27 and D5 6.35 → 7.84. Those corpora are 64–65% sub-gate rides,
so the switch acts on most of their mass, and it removes the cancellation that was
flattering them.

*P2 — mixed, and too small to call.* With the switch, grade-inverse beats the constant on
D5 (0.04 pp), D6-user_2 (0.07) and D6-user_3 (1.36), and loses on D3 (0.10) and
D6-user_1 (0.06). Four of five margins are under 0.15 pp.

*P3 — fails as stated.* Unswitched, grade-inverse is **better** than the constant overall
(4.83 vs 5.08), not worse. It is worse only inside the sub-3% band, and by 0.12 pp
(5.68 vs 5.56) rather than the 20–70% the registration anticipated. That gap was a
*deficit-space* under-prediction; carried into energy it nearly vanishes — the same
metric slippage Entry 47 documented. At and above 3% grade-inverse leads 3.99 to 4.34,
consistent with Entry 45. **Eq. (8) is therefore not "unusable without the switch"**, and
the article's conditional framing is cautious rather than forced.

**Consequence.** No published number changes: every published column is unswitched and
stays. What changes is what the frozen grid's sub-3% $\varepsilon_d$ cells *mean* — they
are accurate by cancellation, not by fit. Implementing the switch is therefore correct
but must be done together with honest per-ride physics; bolting it onto the frozen grid
alone would trade a cancelled bias for an exposed one and make the published medians
worse. Recorded in paper 1 [§3.3](#3.3); the switch itself stays unimplemented in the
published harnesses, now for a stated reason rather than by omission.

---

## 2026-07-29 — Entry 45: what should ε₀ be? — a contest of ride-level summaries

**Lineage** — $I$: $(D_1..D_6, P_{a,g})$ · $T$: ride-level deficit contest · $O$: `e45_ridelevel.csv` (1,039), `e45_ridelevel.paper.csv` (1,038), `e45_flatseg.csv` (396 segments) · $S$: **eq. (8)**, $k$ = 0.0051

*Prompt (Danilo), before letting any of Entries 43–44 reach the article: "i feel we should have
a competing hypothesis for eps_0 for summarizing ride-level", then two candidate forms —
"eg. delta = eps_0 * s_50" and "what about k / s50?"*

### Pre-registration (written before any estimator is fitted)

**Why the question is well posed.** Because $\delta = E_{\mathrm{legs},-}/(\beta h_-)$, summing
over cells gives

$$\delta_{\mathrm{ride}} \;=\; \frac{\sum_i E_i}{\beta \sum_i h_i}
\;=\; \frac{\sum_i \delta_i\,h_i}{\sum_i h_i}$$

— the ride-level deficit is **exactly** the drop-weighted mean of the cell-level $\delta(s)$.
No approximation. That also names Entry 34's error precisely: it evaluated $\delta(\bar s)$,
the curve *at* the mean grade, when the correct object is the *mean of the curve*. For a
sigmoid those differ by Jensen's inequality, and they differ most exactly where descents live.

**The target.** $\delta_{\mathrm{meas}} = E_{\mathrm{desc}}/(\beta h_-)$ over every descent cell
of a ride, on rides whose drop-weighted mean descent grade $\bar s \geq 3\%$ (paper 1's
real-descent gate). This is the exact ledger quantity, so every estimator predicts the same
thing. It differs slightly from `eps_cells`' clamped $\varepsilon_{\mathrm{coast}} -
\varepsilon_{\mathrm{bal}}$; the difference is disclosed rather than hidden.

**The contestants.** All scored identically; nothing may see the held-out half. The shared
cell-level curve, from the identity above with occupancy substituted for the pedalling share,
is

$$\delta(s) \;=\; \underbrace{\frac{1}{1 + e^{(s - s_{50})/w}}}_{\mathrm{occ}(s)}
\;\cdot\; \frac{\hat I_{\mathrm{flat}}\,k_{\mathrm{eff}}}{m\,g\,s\,v}
\tag{$\ast$}$$

with $s_{50}, w$ the rider's occupancy sigmoid from Entry 44 and $\hat I_{\mathrm{flat}}$ the
rider's median while-pedalling flat power — **both taken from the fit half only**. C, D and E
are the three ways of pushing $(\ast)$ to a ride-level number.

| | name | form, written out | input variables | # in | free parameters | # par |
|---|---|---|---|--:|---|--:|
| A | **frozen constant** | $\delta = 0.13$ | — | 0 | none (frozen upstream) | 0 |
| A′ | **pooled constant** | $\delta = \operatorname{med}\{\delta_{\mathrm{meas}}\}_{\text{fit half}}$ | — | 0 | 1 global | **1** |
| B | **rider constant** | $\delta = \operatorname{med}\{\delta_{\mathrm{meas}}\}_{\text{rider, fit half}}$ | rider identity | 0 | 1 per rider | **9** |
| B′ | **threshold-linear** | $\delta = k\,s_{50}$ | $s_{50}$ | 1 | 1 global + $s_{50}$ per rider | **10** |
| B″ | **threshold-inverse** | $\delta = k/s_{50}$ | $s_{50}$ | 1 | 1 global + $s_{50}$ per rider | **10** |
| **C** | **mean-grade curve** | $\displaystyle \delta_C = \frac{1}{1 + e^{(\bar s - s_{50})/w}} \cdot \frac{\hat I_{\mathrm{flat}}\,k_{\mathrm{eff}}}{m\,g\,\bar s\,\bar v}$ — i.e. $(\ast)$ at the ride's **mean** descent grade | $\bar s,\ \bar v,\ m,\ \hat I_{\mathrm{flat}}$ | 4 | $(s_{50}, w)$ per rider | **18** |
| D | **dispersion-corrected curve** | $\delta_D = \delta_C + \tfrac{1}{2}\,\delta''(\bar s)\operatorname{Var}(s)$, $\delta''$ a central difference on $(\ast)$, $\operatorname{Var}(s)$ drop-weighted | C's + $\operatorname{Var}(s)$ | 5 | $(s_{50}, w)$ per rider | **18** |
| F | **encounter fraction** | $\delta = a + b\varphi$ | $\varphi$ (needs the full grade distribution + $s_{50}$) | 1 | 2 global + $s_{50}$ per rider | **11** |
| G | **grade-inverse** | $\delta = k/\bar s$ | $\bar s$ | **1** | 1 global | **1** |
| E | **cell integral** | $\displaystyle \delta_E = \frac{\hat I_{\mathrm{flat}}}{\beta\,h_-}\sum_i \frac{t_i}{1 + e^{(s_i - s_{50})/w}}$ — $(\ast)$ integrated **per cell** | $\{t_i, s_i\}$ per cell, $m$, $\hat I_{\mathrm{flat}}$ | per-cell | $(s_{50}, w)$ per rider | **18** |

Two accounting notes, because the parameter counts are what make this a fair contest rather
than a fit-off. First, **$m$ and $\hat I_{\mathrm{flat}}$ are not new costs** — paper 1's model
already requires the rider's mass and flat power (the latter sets $v_f$), so C's marginal
demand over the deployed model is only $\bar s$, $\bar v$ and the rider's $(s_{50}, w)$.
Second, the per-rider parameters are **inherited from Entry 44, fitted on half 0**, and are
counted here rather than treated as free: an estimator carrying 18 fitted numbers must beat one
carrying 1 by enough to justify them.

Here $\bar s = h_-/x_-$ is the drop-weighted mean descent grade, $\bar v$ the time-weighted mean
descent speed, $\beta = mg/k_{\mathrm{eff}}$, and $t_i, s_i$ the time and grade of cell $i$.
C and E differ *only* in whether the sigmoid is evaluated once at $\bar s$ or once per cell —
which is exactly the Jensen question, and why D sits between them as the second-order bridge.

*(Notation expanded 2026-07-29 for legibility at Danilo's request; the forms are unchanged from
the registration and the code was not touched.)*

**Protocol.** Split-half by chronological ride index, odd/even (deterministic, no RNG); every
constant, coefficient and per-rider quantity ($s_{50}$, width, $I_{\mathrm{flat}}$,
$\varepsilon_{0,\mathrm{rider}}$) is taken from the **fit half only**; scoring is median
$|\delta_{\mathrm{pred}} - \delta_{\mathrm{meas}}|$ on the held-out half, per corpus and pooled.
$s_{50}$ and the sigmoid width come from Entry 44's fits, which were themselves fitted on
half 0 — so there is no leak. All nine rider-corpora.

**Preliminary corpus-level evidence, recorded here so the predictions are not retrofitted.**
Over the eight open-road corpora: $\delta/s_{50}$ spans 3.0×, $\delta\cdot s_{50}$ spans 7.1×,
$\delta\cdot\bar s$ spans 2.6×; Spearman$(s_{50},\delta) = +0.286$,
Spearman$(\varphi,\delta) = +0.810$, Spearman$(\bar s,\delta) = -0.857$.

**Predictions.** **G and F are the two to beat, G favoured on parsimony.** B beats A; B′ beats
A but loses to B; **B″ finishes last of the rider-only forms** (its inverse fights a positive
$s_{50}$–$\delta$ relationship); C stays broken; D lands between C and F. Registered
quantitatively: G's held-out median error is below A's on at least 7 of 9 corpora.

**The caveat that governs how any win is read.** $1/s$ sits *inside* the identity, and
$\varphi$ is a step-function stand-in for the occupancy integral that *defines* $\delta$. So
strong correlations for G and F are substantially mechanical and are **not** evidence of
discovery. The only honest test is held-out predictive error against A, which is why the
contest is scored that way and why no correlation is reported as a result.

*Failure modes.* If A is not beaten, paper 1's constant stands and Entries 43–44 change nothing
at ride level. If G wins, the paper-1 change is one line — $\varepsilon_d =
\varepsilon_{\mathrm{coast}} - k/\bar s$, using a statistic the model already computes for
$\varepsilon_{\mathrm{coast}}$ — and needs its own gates before it ships. If E beats every
compressed form by a wide margin, ride-level summarisation is the wrong frame and the whole
refinement belongs at per-edge grain (paper 3).

### Results

`python3 src/harness/e45_ridelevel.py`. 1,039 rides qualify; 525 fit, **514 held out**.

**An unfair baseline, caught and replaced before reporting.** The target is the *unclamped*
ledger identity, and `eps_cells` **clamps** $\varepsilon_{\mathrm{coast}}$ per cell
($\min(1, \alpha/\beta s)$ saturates on shallow ground). The two therefore differ by a
definitional offset: pooled median $\delta_{\mathrm{meas}} = 0.253$ against
$\varepsilon_0 = 0.13$. Every *fitted* contestant absorbs that offset for free; the frozen
0.13 cannot. Scoring against A alone would have credited the structured forms for an offset
rather than for structure — the same scope error as Entry 44's first P3 pass. **A′, the best
single universal constant fitted on the fit half, is the honest floor**; A is still reported,
flagged as off-target.

| estimator | pooled held-out median error | beats A′ | # par |
|---|--:|--:|--:|
| **E — cell integral** | **0.0540** | 7/9 | 18 |
| **C — mean-grade curve** | **0.0586** | 8/9 | 18 |
| F — encounter fraction | 0.0714 | 7/9 | 11 |
| B — rider constant | 0.0731 | 8/9 | 9 |
| **G — grade-inverse** | 0.0781 | 7/9 | **1** |
| A′ — pooled constant | 0.0973 | — | 1 |
| B′ — threshold-linear | 0.0984 | 5/9 | 10 |
| A — frozen constant (off-target) | 0.1194 | — | 0 |
| B″ — threshold-inverse | 0.1300 | 2/9 | 10 |
| D — dispersion-corrected curve | 0.5938 | 0/9 | 18 |

**Complexity-adjusted comparison** *(added at Danilo's request: "is there a test that compares
each form to our benchmark taking into account both the error reduction and the extra degree of
freedom? Maybe χ²_red?").* χ²_red is not usable here — it needs a per-observation σ on
$\delta_{\mathrm{meas}}$, which we do not have, so any χ² would be an invented denominator.
Two tools that do apply: **BIC on the fit half** under a Laplace likelihood (the one a
median/MAE metric implies), and a **paired sign test** on held-out per-ride absolute errors
against A′. One accounting point: **only fitted parameters enter the penalty.** Input variables
are covariates, not degrees of freedom — reading a measured $\bar s$ costs data availability,
not freedom to overfit. So the statistical comparison is G's 1 against C/E's 18, while the
input counts remain a separate deployment axis.

| | $k$ | fit MAE | ΔBIC vs A′ | held-out | wins vs A′ | $p$ |
|---|--:|--:|--:|--:|--:|--:|
| A — frozen constant | 0 | 0.1719 | +335.7 | 0.1194 | 157/514 | <10⁻⁴ |
| A′ — pooled constant | 1 | 0.1241 | — | 0.0973 | — | — |
| B — rider constant | 9 | 0.0911 | −274.2 | 0.0731 | 316/514 | <10⁻⁴ |
| **B′ — threshold-linear** | 10 | 0.1106 | **−64.7** | 0.0984 | **255/514** | **0.89** |
| B″ — threshold-inverse | 10 | 0.1921 | +514.9 | 0.1300 | 158/514 | <10⁻⁴ |
| C — mean-grade curve | 18 | 0.0852 | −288.9 | 0.0586 | 303/514 | 0.0001 |
| D — dispersion-corrected | 18 | 20.21 | +5454 | 0.5938 | 72/514 | <10⁻⁴ |
| **F — encounter fraction** | 11 | 0.0847 | **−338.7** | 0.0714 | 331/514 | <10⁻⁴ |
| **G — grade-inverse** | **1** | 0.1031 | −194.4 | 0.0781 | **356/514** | <10⁻⁴ |
| E — cell integral | 18 | 0.0818 | −330.6 | 0.0540 | 325/514 | <10⁻⁴ |

**The three axes crown three different winners**, and that is the substantive result: raw
held-out accuracy → **E** (0.0540); complexity-adjusted fit → **F** (ΔBIC −338.7); held-out
*win rate* → **G**, which beats the pooled constant on 69% of rides, more often than any other
form despite ranking fifth on median error. G wins often by small margins; C and E win less
often by larger ones.

**B′ is the methodological lesson of this entry.** BIC *endorses* it decisively
(ΔBIC = −64.7) because it fits the fit half better (MAE 0.1106 vs 0.1241) — yet its held-out
win rate is 255 of 514, **$p = 0.89$, a literal coin flip**. Ten parameters bought in-sample
fit that did not transfer, and BIC's $k\ln n$ penalty was too weak to catch it at $n = 525$.
This is why the held-out score is primary here and the information criterion is corroboration:
AIC/BIC are *approximations to cross-validation* for when cross-validation is unaffordable, and
we can afford it. Where the two disagree, the held-out result wins.

### Amendment results — the flat-terrain probe, and two more forms

*Prompt (Danilo): "Can we select 100 random activities, and cherry pick some segments larger so
that they have a 0.5% mean descent... balanced in terms of cumulative ascent and descent", then
"let's select the top 100 larger activities".* The point: every ride in the contest sits at
$\bar s \geq 3\%$, so the choice between an unbounded $k/\bar s$ and a bounded alternative rested
on a region with **no observations**. `e45_flatseg.py` cuts balanced $\geq 20$ km windows out of
the 100 longest rides and measures $\delta$ there.

**The first version of the probe was wrong, and the way it was wrong is worth recording.** It
built cells from raw elevation. On a near-flat window that put $h_-$ at 2.4 m/km against a
corpus noise rate of 3.1 m/km — the "drop" was altimeter jitter — so
$\delta = E_{\mathrm{legs}}/(\beta h_-)$ divided real pedal energy by measurement error and
returned 3.14. Worse, the search was **self-reinforcing**: hunting for the flattest window
steered it toward exactly the windows where the denominator was most noise. Rebuilt on
deadband-smoothed elevation ($\tau = 2$ m, the filter F3 already uses), which cleans *both*
ends — spurious drop out of the denominator, spurious "descent" cells out of the numerator.

**Result, 396 windows.** Against the ledger-target fit $k = 0.0099$:

| target | median $\bar s$ | $h_-$/km | noise/km | measured $\delta$ | G predicts | meas/G |
|--:|--:|--:|--:|--:|--:|--:|
| 0.5% | 2.07% | 5.3 | 2.4 | 0.548 | 0.478 | 1.15 |
| 2.0% | 2.16% | 6.4 | 2.5 | 0.478 | 0.459 | 1.04 |
| 3.0% | 3.00% | 9.0 | 2.6 | 0.311 | 0.330 | 0.94 |

G tracks to within 6% at 2–3% and 15% near 2%, **entirely out of sample**. The requested 0.5%
is unreachable: balanced 20 km windows that flat do not exist in these corpora (floor 0.78%).

**A third mixing of the two targets, and the rule that prevents a fourth.** The first reading of
this table compared measured $\delta$ (the *unclamped* ledger quantity) against $k = 0.0051$
(the *clamped* paper-target fit). The two differ by 1.9×, and that single mismatch produced a
spurious "G under-predicts by 4–7×", a retracted "$\delta\bar s$ rises fourfold", and — earlier —
Entry 44's P3 scope error. The rule, now a comment in the harness: **whichever quantity is
measured, the constant must be the one fitted to that same quantity.**

**Two candidate forms, both refuted.** G2, the same model with the *force* fixed in newtons
rather than $k$ dimensionless (so the charge does not scale with mass), scores 0.0592 against
G's 0.0545 — the charge does appear to scale with mass, mildly. G3, a sigmoid in $\bar s$
motivated by Danilo's S-curve rationale (bounded, $\delta \to 1$ as terrain flattens), fits
better (ΔBIC −163 vs −113) but transfers slightly worse (0.0589) — and the flat probe kills its
premise: measured $\delta$ below 1% is **1.778**, above the 0.5 maximum any $x/(1+x^2)$ form can
reach. **$\delta$ does diverge as terrain flattens**; G's failing is that it diverges *too
slowly*, not that it diverges.

**Where G breaks, and why.** $\delta = P_{\mathrm{desc}}/(\beta \bar s \bar v)$ with
$P_{\mathrm{desc}} = \mathrm{occ}(\bar s)I$, so G's constant is really
$k = \mathrm{occ}(\bar s)I/(\beta\bar v)$ — constant only while occupancy is small and slowly
varying. Below the occupancy midpoint both terms push the wrong way (occ climbs toward 1,
$\bar v$ falls) and $k$ must rise. It does:

| $\bar s$ band | 3–5% | 2–3% | 1.5–2% | 1–1.5% | 0.5–1% |
|---|--:|--:|--:|--:|--:|
| implied $k$ | 0.00929 | 0.01020 | 0.01180 | 0.01567 | 0.01695 |
| vs 0.0099 | 0.94 | 1.03 | 1.19 | 1.58 | 1.71 |

The empirical break is ≈ 2%, and Entry 44's fitted $s_{50}$ (2.1–5.9% across riders) predicts
exactly that — **the break point is the rider's own occupancy midpoint**, which is why a fixed
threshold has to sit at the conservative end of that spread.

**A hybrid was tested at Danilo's suggestion and is worse.** Falling back to a constant below
1% *doubles* the error in the band it was meant to protect (1.525 vs G's 0.779), because
measured $\delta$ there is 1.778 — seven times A′ and thirteen times A. A constant moves in the
wrong direction. If a guard is wanted, evaluate G at $\max(\bar s, 1\%)$: it costs nothing
(0.788 vs 0.779) and avoids a divide-by-zero without pretending the deficit stops growing.

**What this does to the article claim.** §3.3's regime rule (dynamic $\varepsilon_d$ on mean
descent grade ≥ 3%, flat $\varepsilon_f$ otherwise) is a **recommendation that no harness
implements** — the `s̄ >= 0.03` filters in the `*_compare.py` files are reporting slices, not
gates, and Table 3 applies $\varepsilon_d$ to every ride including the **69%** of Table 3's corpora below 3%. The
article text was corrected accordingly: the cross-reference now points at §3.3 rather than a
section invented the same day, the scope condition is labelled unenforced, and the claim is
shrunk to *where the dynamic estimator applies at all, its deficit should be grade-inverse*.
Implementing the switch is registered as Entry 46.

**What the parameter counts buy.** Error reduction against the pooled constant (A′, 0.0973),
per fitted parameter:

| | reduction vs A′ | # par | verdict |
|---|--:|--:|---|
| G — grade-inverse | **−20%** | **1** | the whole gain of a rider constant, for one number |
| B — rider constant | −25% | 9 | nine numbers to beat G by 5 points |
| F — encounter fraction | −27% | 11 | |
| C — mean-grade curve | −40% | 18 | the accuracy buy |
| E — cell integral | −44% | 18 | +4 points over C for per-cell data |
| B′ — threshold-linear | +1% | 10 | **ten parameters to do worse than one** |
| B″ — threshold-inverse | +34% | 10 | |

**G is the parsimony winner by a distance**: one route statistic and one universal constant
recover four-fifths of what a nine-parameter per-rider table buys. And the two rider-only
predictive forms are the clearest negative result here — B′ and B″ spend ten fitted numbers to
land at or below a single pooled constant.

**Registered predictions, scored honestly — four of seven wrong.** ✓ B beats the constant
(8/9). ✓ B″ finishes last of the rider-only forms (2/9). ✓ G clears its registered 7-of-9
threshold. ✗ "G and F are the two to beat" — E and C lead; G is fifth. ✗ "B′ beats A" — B′
**ties** the honest floor (0.0984 vs 0.0973, 5/9), so it adds nothing. ✗ "C stays broken" — C
is second best. ✗ "D between C and F" — D collapses.

**Both rider-only forms are dead, and structurally so.** $k\,s_{50}$ ties a plain constant and
$k/s_{50}$ is far worse. A rider parameter *without terrain* adds variance without signal,
because the deficit is not a property of the rider — it is a property of the **encounter**
between a rider's threshold and a route's grades. That is the same conclusion $\varphi$ was
built on, arrived at from the opposite direction.

**C works, which contradicts Entry 34 — and the difference is diagnostic.** Entry 34 fitted a
logistic *in ε space* and evaluated it at ride-mean grade; that failed. Here C evaluates the
*physical* curve $\delta(s) = \mathrm{occ}(s)\,I\,k_{\mathrm{eff}}/(mgsv)$ at the same mean
grade, and it is second best. Most of C's power therefore comes from the physics denominator
(the $1/s$, the ride's own $\bar v$ and $m$), not from the sigmoid. Entry 34's verdict was
about the behavioural curve, not about mean-grade evaluation as such.

**E beats C by only 8%.** Per-cell integration buys little over evaluating the physical curve
at the ride's mean grade — a deployment result: the per-edge machinery is not needed for a
ride-level number.

**The ladder, by what a caller knows:** profile only → **G, $k/\bar s$**, 20% better than the
best constant, zero rider parameters. Profile + rider's $I_{\mathrm{flat}}$ and $s_{50}$ →
**C**, 40% better. Full per-cell profile → **E**, 44% better.

*Caveats.* The target is the unclamped identity and differs from paper 1's published quantity
by ≈ 0.12 — **none of these numbers can enter paper 1 without re-deriving on paper 1's own
clamped gap**, with gates. All fitted constants come from the fit half of this same data; nine
rider-corpora, four from one deposit, two sharing a rider. D's collapse is mathematical, not a
bug: $\delta \propto 1/s$ has $\delta'' \propto 2/s^3$, so the second-order expansion is
invalid at gentle grades.

---

## 2026-07-29 — Entry 44: the S-curve, reopened — pinning the magnitude and testing speed against slope

**Lineage** — $I$: $(D_1..D_6, P_{f,r})$ · $T$: occupancy sigmoid, split-half · $O$: `e44_scurve_cells.csv` (153 cells), `e44_scurve_fits.csv` (9 rider-halves) · $S$: $s_{50}$ separates the populations

*Prompt (Danilo), after Entry 43's arms established that the deficit spread is behavioural:
"I feel we need to go back to the S-curve hypothesis. If δ = Effect Magnitude of Pedalling
during Descent(slope) × Probability of Pedalling During Descent(slope), then maybe we can set
the effect magnitude as being a function rather than being a constant. Right now, magnitude is
ε₀ and probability is 1. Probability is purely behavioural. Magnitude is partly behavioural and
partly constrained… Still, epsilon is unitless, I'm not sure how to relate power measurements
to eps." Then: "what would be our hypothesis for M and P?"*

### Pre-registration (written before any fit)

**The units bridge — the thing that was blocking the reformulation.** Appendix A's ledger
identity $\delta = E_{\mathrm{legs},-}/(\beta h_-)$ rewrites, for a descent of length $x_-$
with mean grade $\bar s = h_-/x_-$ and mean speed $\bar v$ (so $t = x_-/\bar v$), as

$$\delta \;=\; \frac{\bar P_{\mathrm{desc}}\,(x_-/\bar v)}
{(mg/k_{\mathrm{eff}})\,\bar s\,x_-} \;=\;
\frac{k_{\mathrm{eff}}\,\bar P_{\mathrm{desc}}}{m\,g\,\bar s\,\bar v}$$

The denominator $m g \bar s \bar v$ is the **gravitational power released**, in watts.
$\varepsilon$ is unitless because it is a *ratio of two powers* — what the legs add over what
gravity gives. This makes the frozen constant physically readable: at 80 kg on a 5% descent at
36 km/h gravity supplies ≈ 390 W, so **$\varepsilon_0 = 0.13$ is ≈ 50 W of descent pedalling**
(the author's 0.118 ≈ 44 W; user_2's 0.298 ≈ 120 W). The constant was always a wattage in
disguise.

**The reformulation.** Splitting descent power into occupancy × intensity,
$\bar P_{\mathrm{desc}} = \mathrm{occ}(\cdot)\,I(\cdot)$:

$$\delta \;=\; \underbrace{\mathrm{occ}(\cdot)}_{\text{behaviour}} \;\times\;
\underbrace{I(\cdot)}_{\text{behaviour}} \;\times\;
\underbrace{\frac{k_{\mathrm{eff}}}{m\,g\,s\,v(s)}}_{\text{pure physics}}$$

**H-M (magnitude): $I = P_{\mathrm{flat}}$, independent of grade — zero free parameters.** Entry 43's
arm-C measurement over nine rider-corpora gives $I/P_{\mathrm{flat}} = 0.96$ [IQR 0.85–1.11], and Entry 34
independently found intensity "roughly flat in grade and strongly rider-conditional"; H-M names
what it is conditional on. The behavioural reading is that descent pedalling is close to
**binary** — coast, or ride normally — which is why the magnitude carries little information
and the occupancy carries it all. *Falsifier:* $I/P_{\mathrm{flat}}$ drifts across grade bands beyond its
CI. The pre-declared refinement if it fails is a **gearing ceiling** (53×11 at 100 rpm spins
out near 55 km/h), which would make $I$ a function of speed, not slope.

**H-P (probability): occupancy is a decreasing sigmoid,
$\mathrm{occ}(x) = 1/\bigl(1 + e^{(x - x_{50})/w}\bigr)$, with a universal width $w$ and a
rider-specific midpoint $x_{50}$** — one parameter per rider, and
the parameter in which the ultra-distance-versus-amateur spectrum of Entry 43 arm B lives.

**H-P2 (the sharp one): the governing variable is SPEED, not slope.** What ends pedalling is
cadence running out, not gradient as such; slope works only as a proxy correlated with speed.
The two forms make a discriminating prediction: **on the same gradient, a heavier or more
aerodynamic rider descends faster and should pedal less.** *Test:* fit $\mathrm{occ}(|s|)$ and $\mathrm{occ}(v)$
separately, and compare their transfer.

**Why this is worth reopening after Entry 34 failed.** Entry 34's S-curve lost its ride-level
test because "ride-mean descent grade blurs the cell-level curve" — it evaluated a nonlinear
curve *at the mean grade*, which is not the mean of the curve. The fix is to integrate per
cell and aggregate afterwards. Two things have also changed: the magnitude is now pinned to
$P_{\mathrm{flat}}$ instead of free (H-M), and D6 widens the occupancy range from three riders at 0.15–0.21
to nine spanning 0.07–0.62, with an Alpine rider supplying the steep tail where the sigmoid
bends. This is per-edge territory — paper 3's — and §4.4.2 already predicted a grade-resolved
deficit would only pay at that grain.

**Protocol, fixed here.** 30 m cells (repo standard); pedalling = power ≥ 10 W; moving gate
0.5 km/h; braking = deceleration > 1.5 m/s² from > 3 m/s (`perride_invert`'s BRAKE_DECEL /
BRAKE_VMIN). Grade bins (descent, |s|): 0.5–1–2–3–4–5–6–8–10–15–∞ %. Speed bins: 0–10–20–30–
40–50–60–∞ km/h. Sigmoids fitted by deterministic grid search minimising time-weighted squared
error on binned occupancy — x₅₀ over 0–20% (step 0.1) or 0–70 km/h (step 0.5), w over
0.2–8 %/step 0.1 or 1–25 km/h/step 0.5. **Split-half transfer** by chronological ride index,
odd/even (deterministic, no RNG): fit on one half, score the other. All nine rider-corpora
(D1, D2, D3, D4, D5, D6×4).

**Predictions.**

- **P1 (H-M).** $I/P_{\mathrm{flat}}$ stays within 0.85–1.15 in every grade bin up to 10%. *Failure:* a
  systematic drift; the direction matters — falling at high grade means the gearing ceiling and
  H-M becomes $I = \min(P_{\mathrm{flat}},\ \text{gearing bound})$.
- **P2 (H-P2).** $\mathrm{occ}(v)$ transfers across riders better than $\mathrm{occ}(|s|)$: lower held-out RMSE with
  a **common** width, and less rider-to-rider spread in the fitted midpoint once expressed in
  its own variable. *Failure:* slope wins, and the cadence mechanism is wrong — the sigmoid is
  then a terrain response, not a physiological one.
- **P3 (composite).** The cell-grain $\delta(s)$ beats the frozen $\varepsilon_0 = 0.13$ on held-out halves for at
  least 5 of the 9 rider-corpora, measured as ride-level $|\Delta\delta|$. *Failure:* fewer than 5, and
  Entry 34's verdict stands — the constant is the correct summary and the S-curve stays a
  mechanism with no estimator, which is a publishable negative for paper 3.
- **P4 (behavioural corollary).** Danilo's efficiency explanation predicts *within* a rider,
  not only between riders: on longer rides the same rider's occupancy should fall. D5's 617
  rides span short outings to 200 km brevets. Registered as: negative Spearman(ride distance,
  occupancy) within rider on at least 5 of 9. *Failure:* flat within riders means the
  between-rider difference is culture or terrain rather than efficiency management, and the
  Entry-43 mechanism needs restating.
- **P5 (the sanity check that could sink everything).** If most non-pedalling descent time is
  **braking** rather than freewheeling, neither slope nor speed is the governing variable —
  road geometry is — and none of this transfers to a planner holding only a profile.
  Registered as: braking is under 30% of non-pedalling descent time in the 3–8% band.
  *Failure:* report it and stop; the sigmoids are then not interpretable as a pedalling choice.

**Not registered / out of scope.** No change to any published paper-1 number. $\varepsilon_0 = 0.13$ stays
frozen everywhere else. This entry fits occupancy only — it does not refit ε, the priors, or
the forms.

### Results

`python3 src/harness/e44_scurve.py` → `e44_scurve_cells.csv`, `e44_scurve_fits.csv`.
All nine rider-corpora, 2,156 rides.

**P5 — PASSES, and it was the one that could have voided the rest.** Hard braking is
**0.2–3.3%** of non-pedalling descent time in the 3–8% band, across 21,000 minutes of it. That
time is genuinely freewheeling, so the sigmoid is a pedalling *choice* and not a road-geometry
artefact, and the result transfers to a planner holding only a profile. *Caveat:* the detector
is a hard-brake threshold (> 1.5 m/s² from > 3 m/s); gentle feathering would not register, so
this bounds hard braking, not all braking.

**The headline: $s_{50}$ recovers the rider spectrum as a single parameter.**

| corpus | $s_{50}$ | | corpus | $s_{50}$ |
|---|--:|---|---|--:|
| D2 urban | 0.7% | | D6 user_1 | 4.2% |
| D5 the author | **2.1%** | | D6 user_3 | 4.3% |
| D1 longões | 2.8% | | D6 user_5 | 4.8% |
| D4 JAAM | 2.9% | | D6 user_2 | **5.9%** |
| D3 P. Paz | 3.3% | | | |

The four Brazilian ultra-distance corpora occupy 2.1–3.3% and the four European amateurs
4.2–5.9% — **disjoint**. Entry 43 arm B's coasting-versus-pedalling spectrum turns out to be
one fitted number: the grade at which a rider stops pedalling half the time. And H-P's
structure holds: fixing the width to a common 1.7% costs little in transfer (held-out RMSE
0.0497 → 0.0668), so the width is universal and the midpoint carries the behaviour.

**P2 — H-P2 REFUTED.** Slope beats speed by **3.1×** on held-out RMSE (0.0497 vs 0.1546), and
the speed fits are degenerate: widths pinned at the grid ceiling for seven of nine riders,
midpoints scattered 0–58 km/h. The cadence/spin-out mechanism is wrong — riders decide by
gradient, not by how fast they are moving. *Disclosed limitation:* speed got 7 bins to slope's
11, so the contest was not resolution-matched; the gap is large enough that this is unlikely to
explain it, but a matched-resolution rerun would settle it.

**P1 — H-M fails as registered; magnitude is a real but second-order function.** Like-for-like
$I/I_{\mathrm{flat}}$ by grade band drifts to **0.62–0.83** at steep grades for user_1, P. Paz, JAAM and the
author, holds flat at 0.85–0.98 for D1, and *rises* to 1.29 for user_3, the Alpine rider. The
registered 0.85–1.15 band therefore fails for most riders, but the variation is a factor of
≈ 0.7–1.0 with a rider-dependent sign, against occupancy's 9× between-rider spread and its
steep grade dependence. Danilo's instinct that the magnitude should be a function is vindicated
— it is just the smaller of the two effects.

*Methods bug caught mid-run, disclosed.* The first pass compared descent power *while
pedalling* against flat power *including coasting*, which conflates magnitude with occupancy
and inflates the ratio for exactly the riders who coast most — it put D5 at 1.25–1.38 when his
descent pedalling is the study's lowest. Corrected to a like-for-like while-pedalling
denominator, D5 reads 0.83–0.96. All P1 numbers above are the corrected ones.

**P3 — SUPPORTED, 7 of 9 on held-out halves.** Median
$|\delta_{\mathrm{model}} - \delta_{\mathrm{meas}}|$ against
$|0.13 - \delta_{\mathrm{meas}}|$:

| corpus | n | model | constant | winner |
|---|--:|--:|--:|---|
| D6 user_1 | 96 | 0.0496 | 0.0492 | constant (a tie) |
| D6 user_2 | 170 | 0.0498 | 0.1723 | model |
| D6 user_3 | 86 | 0.0286 | 0.0774 | model |
| D6 user_5 | 6 | 0.0791 | 0.0399 | constant (n = 6) |
| D1 | 22 | 0.0372 | 0.0821 | model |
| D2 | 34 | 0.0113 | 0.1026 | model |
| D3 | 208 | 0.0298 | 0.0552 | model |
| D4 | 103 | 0.0360 | 0.0442 | model |
| D5 | 302 | 0.0284 | 0.0825 | model |

**This is the result Entry 34 could not get.** A grade-resolved deficit *does* pay — at cell
grain, integrating per cell and aggregating afterwards, which is precisely the correction
§4.4.2 predicted would be needed and precisely paper 3's setting. The two non-wins are a dead
heat (user_1, 0.0496 vs 0.0492) and an underpowered group (user_5, n = 6).

*Second methods bug caught before reporting, disclosed.* The first P3 scoring returned **9/9**
and was wrong twice over. It ran $\delta$ over *all* descending cells, but $\varepsilon_0 = 0.13$ is defined on
real descents (≥ 3%) — and on shallow descents riders pedal 54–88% of the time, so $\delta$ there is
of order 1 and the constant was being judged far outside its declared scope. It also drew
$I_{\mathrm{flat}}$ from the ride being predicted, leaking ride-specific information the constant baseline
never gets. Rescoring on ≥ 3% cells with $I_{\mathrm{flat}}$ taken from the fit half only gives the 7/9
above. **A 9/9 that flatters the new model is exactly the result to distrust.**

**P4 — FAILS, and the failure is the more interesting story.** Within-rider
Spearman(ride distance, descent occupancy) is negative on only **4 of 9**, and the author's own
617 rides give ρ = −0.061 — indistinguishable from zero. So the ultra-distance riders' coasting
is **not** within-ride efficiency management: riders do not coast more as a ride gets longer.
It reads instead as a stable rider trait — training, equipment, riding culture — which supports
paper 1 §3.2's "habit" framing over an optimisation framing, and is a cleaner mechanism than
the one registered.

### What this licenses, and what it does not

The deficit now has a mechanism (occupancy), a shape (a slope sigmoid of universal width), a
rider parameter ($s_{50}$, which separates the two rider populations without overlap), and a
demonstrated out-of-sample gain at cell grain. That is a per-edge cost function, i.e. **paper 3
material**, and it should be developed there rather than retro-fitted into paper 1.

It does **not** license changing anything in paper 1. $\varepsilon_0 = 0.13$ remains the correct ride-level
summary — Entry 34's verdict stands at that grain and P3 says nothing about it. The nine
midpoints come from nine rider-corpora, four of which are one deposit and two of which
(D1 ⊂ D5) share a rider, so $s_{50}$'s population spread is a description of these riders, not an
estimate for cyclists. And H-M's failure means a deployed per-edge form needs either a
magnitude taper or an honest statement that it assumes $I \approx I_{\mathrm{flat}}$.

---

## 2026-07-29 — Entry 43: the fifth rider set — the frozen law on four European riders (D6)

**Lineage** — $I$: $(D_6, P_{a,g} \cdot P_{f,p}(m))$ · $T$: F1–F4, $F_\mathrm{base}$; inversion; occupancy · $O$: `skc_comparison.csv` (743), `skc_invert.csv` (743), `skc_descent_occupancy.csv` (2,193), `skc_eps_vs_pedal.csv` (1,038) · $S$: **Table 1, Table 3, Tables 5–6**; 3.16 vs 3.15

*Prompt (Danilo), after an external-review round in which all five reviewers named the narrow
rider sample as the study's main weakness, and after a survey of open cycling data: "let's
register a journal entry to incorporate it, and test it." Standing constraints from the same
conversation: "it's not enough to have more N_riders. We need them to be distributed in a
variety of settings and contexts" and "we would need power and elevation measurements too."*

### Pre-registration (written before any energy evaluation)

**The question.** Every corpus in paper 1 is ridden by one of three São Paulo riders on one
recording chain. Does the frozen law — the forms, the two corrections, ε₀ = 0.13, ε_f = 0.20,
τ = 2 m, c = 3 m/km, all calibrated on D1 and never refitted — transfer to riders who share
no rider, no country, no terrain regime and no device with the calibration set?

**The corpus (D6).** scikit-cycling `power_regression`, Zenodo
[10.5281/zenodo.1202440](https://doi.org/10.5281/zenodo.1202440), CC BY 4.0, deposited 2018 by
Lemaitre & Lemaitre as the data behind a Science & Cycling abstract. It is the only open
deposit found in a two-agent survey that carries per-sample **latitude/longitude + altitude +
measured power** at more than single-rider scale. 1,057 `.fit` files, four riders
(`user_1/2/3/5`; there is no `user_4`), 2012–2015. The corpus never touched this study's model
selection, so it is a fully held-out test — the cleanest available.

**Reconnaissance (geometry and metadata only; no energies computed).** 1,053 files parse with
the repo's own loader, 4 fail. FIT `manufacturer` is Garmin and `sport` is cycling on all 1,053
— no virtual rides to exclude. Under paper 1's blind inclusion filters (powCov > 0.5,
altCov ≥ 0.99, ≥ 20 km, non-virtual) **745 rides survive**: 194 / 347 / 190 / 14 for
users 1 / 2 / 3 / 5. Coordinates are present in ~91% of sampled files (the shared
`pts_from_fit` drops lat/lon by design; `param_fit.pts_with_geo` is the reader that keeps
them). Decoding the semicircle coordinates puts the corpus in **Western Europe, 40.7–50.7°N**:
user_2 mostly Catalonia (42°N, 3°E), user_1 and user_5 mostly Burgundy/Franche-Comté (47°N,
4–5°E), and **user_3 in the French Alps around Grenoble (45°N, 6°E)**.

Two reconnaissance measurements are load-bearing and are recorded here *before* any model runs,
because two predictions below are derived from them arithmetically:

| quantity | D6 | paper 1 (D1) | GoldenCheetah (1 athlete, for scale) |
|---|--:|--:|--:|
| noise rate $c = (\text{raw} - \text{deadband})\,h_+/\mathrm{km}$ | **1.24** [IQR 0.85–1.73] | 3.1 [2.6–3.7] | 6.5 [5.3–7.8] |
| smoothed climbing rate | 7.56 [5.52–12.01] m/km | — | 6.7 |

Per rider the climbing rate is 7.61 / 6.70 / **17.84** / 7.11 m/km — user_3 is a genuinely
mountainous rider, and is also the lightest at a published 61 kg.

**Published masses — a first.** The deposit's own analysis code publishes the riders' body
masses: `{user_1: 86, user_2: 72, user_3: 61, user_5: 72}` kg. Paper 1's implied-mass inversion
has so far been validated against exactly one known value (the author's ≈ 73 kg, §2.3.3).
D6 supplies four more spanning 61–86 kg, so the inversion can be tested across a range rather
than at a point. **The published masses are used only as a validation target — never as an
input to any scored arm.**

**Gravity — and how it is handled without mutating a shared constant.** `G = 9.7864` is São
Paulo's local value and is wrong for this corpus. From the International Gravity Formula at the
ride-count-weighted latitude (≈ 45°N), less a free-air correction at typical ride altitude, D6's
true value is **g = 9.805** (within-corpus spread ±0.005, i.e. 0.05%, over the 41–50°N range).

*Implementation decision, taken before any energy run.* `G` is a module global in
`engines.py` that sibling modules bind by value at import, so patching it for one corpus would
silently desync `regime.py`'s copy — precisely the Entry-27 class of bug. Instead the run uses
the package's `G` unchanged and exploits the invariance CLAUDE.md already documents: **m̂·g is
what the data identifies**. Both the rolling part of α and the whole of β carry the product
mg, so every closed-form energy is *exactly* invariant under (m, g) → (m·g/g′, g′); the forward
simulation differs only through the inertial term m·dv/ds, which carries m without g and is
negligible at route scale. The mass inversion therefore runs at the package `G` and the
**published-mass comparison (P4) rescales** by 9.7864/9.805 = 0.99809. The 0.19% figure also
converts paper 1 §2.1's *assertion* that away rides move β by under 0.3% into a measurement.

**Protocol.** Two, both registered, exactly as Entry 41 did. **Primary: the frozen-prior blind
protocol** — Crr 0.008 · CdA 0.40 · ρ 1.13 · k_eff 0.98 · wind 0, τ = 2 m, c = 3 m/km,
ε₀ = 0.13, ε_f = 0.20, mass inverted per rider from sustained climbs (≥ 3% over ≥ 100 m,
≥ 200 m of sustained climbing per ride) — because that is the protocol paper 1 published in
Table 3, and the only one with a directly comparable reference. **Secondary: regime-consistent
per-ride physics** (Entry 33/35, paper 1 §3.5.2, Table 6), where m̂, Ĉrr and ĈdA_reg come from
each ride's own power stream. The secondary protocol exists because paper 1 §4.3.4's bundle
rule says the ε constants are paired to the physics: on riders whose tyres, position and
loadout are unknown, the frozen priors are a guess, and the ride-consistent α is the honest
pairing. Nothing is refitted on D6 under either protocol.

**Estimands.** Per rider and pooled: median |Δ%| and median signed Δ%, each with 95% CI
(mulberry32, seeds 42/43, B = 10⁴, percentile; stratified within rider for the pool), for
F1–F4 × {ε_d, ε_f} and the forward simulation. Plus the measured deficit gap
ε_coast − ε_bal on real descents (mean descent grade ≥ 3%), and the implied mass per rider.

**Predictions.**

- **P1 — the law transfers.** Under the primary protocol, F3 with the regime-appropriate ε
  lands in the 3.5–6.2% band D3–D5 occupy, and within 1 point of the simulation on the pooled
  column. *Failure:* above 8%, or a gap to the simulation beyond 2 points, means the law does
  not survive leaving Brazil — which would be the single most important negative result in
  the study, and would go in the paper as such.
- **P2 — F4 over-corrects, and by a computable amount.** This corpus's measured noise rate is
  1.24 m/km but F4 subtracts a frozen 3.0, so it removes 1.76 m/km of *real* ascent. On the
  median 56.5 km ride that is 99 m wrongly removed against a median true h₊ of ≈ 427 m — 23%
  of the climb term. Netting the descent side (both h₊ and h₋ shrink, so the refund shrinks
  too, restoring ε_f of it): ≈ 79 m equivalent, ≈ 63 kJ at β ≈ 800 J/m, against a ride energy
  of order 1,500 kJ. **Predicted: F4 carries a negative bias 3–6 points below F3's**, growing
  with distance and shrinking with climbing rate. *Failure:* if F4's bias is not meaningfully
  more negative than F3's, then the deadband and the scalar are not measuring the same thing
  and §2.4's linearisation argument needs revisiting.
- **P3 — the deficit recurs.** The measured gap falls in 0.10–0.19, the band paper 1's
  Terminology already declares across plausible physics and pairings. *Failure:* a gap outside
  that band, or of inconsistent sign across the four riders, bounds the deficit's portability
  to Brazilian riders and must be reported as such.
- **P4 — the mass inversion validates against known values.** Per rider, m̂ minus the published
  body mass falls in 7–12 kg (bike + kit + bottles), and the **ordering is preserved**
  (user_1 > user_2 ≈ user_5 > user_3). The ordering test is the strong one: it is
  parameter-free. *Failure:* a systematic offset outside that window indicts the elevation
  chain (the direction is diagnostic — inflated h₊ biases m̂ down), and an ordering violation
  indicts the inversion itself.
- **P5 — the regime rule holds.** ε_d beats ε_f on user_3 (Alpine, 17.8 m/km); the flat
  constant does better on the gentler riders. *Failure:* an inversion here is a real hit on
  §3.2's rule, though §3.5.1 already documents that the rule is a statement about an
  (α, ε) pair and can flip when the physics is re-paired — which is exactly why both protocols
  are registered.

**Stated in advance, so it is not read as a result.** Four riders is not a population. D6
answers "does the law leave São Paulo" and "does the deficit recur off Brazil"; it does not
answer "what is ε₀ across cyclists". The riders are all European road cyclists on Garmin
head units, which is one recording chain and one riding culture, and the corpus is 2012–2015.
Rides start at the riders' home addresses despite the `user_N` anonymisation, so no derived
geometry is published and the raw files are gitignored.

**Deviations from the registration will be labelled "exploratory, disclosed".**

### Results

`python3 src/harness/skc_compare.py` → `data/results/skc_comparison.csv`. Selection ran as
registered: 1,057 files → 4 unparseable, 227 dropped for power coverage, 81 for distance →
**745 rides**, of which 743 evaluate and **740 clear the physical floor** (3 dropped). Max
conservation residual 5.76 × 10⁻⁸, inside the 10⁻⁶ invariant.

**Pooled, stratified within rider (n = 740).** Median |Δ%| · median signed Δ%, 95% CIs:

| model | med \|Δ%\| | bias |
|---|--:|--:|
| F1 · ε_d (original) | 12.59 [12.1, 13.0] | +12.55 [12.1, 13.0] |
| F2 · ε_d (split) | 4.28 [4.0, 4.6] | +3.42 [3.0, 4.0] |
| **F3 · ε_d (split + deadband)** | **3.16 [2.9, 3.5]** | **+1.97 [1.6, 2.3]** |
| F4 · ε_d (split + scalar c) | 4.04 [3.8, 4.4] | −2.22 [−2.6, −1.9] |
| F3 · ε_f = 0.20 | 8.45 [8.0, 8.8] | +8.42 [8.0, 8.7] |
| F4 · ε_f = 0.20 | 3.58 [3.2, 3.9] | +2.58 [2.3, 3.0] |
| simulation (frozen) | 3.15 [2.9, 3.3] | +1.96 [1.7, 2.4] |

Per rider, F3·ε_d: 5.76 (user_1) · 2.21 (user_2) · 3.83 (user_3) · 2.18 (user_5); the
simulation 4.63 · 2.05 · 3.80 · 1.52. user_5's 14 rides make its column indicative only.

**P1 — supported, and beyond the registration.** F3·ε_d pools to **3.16% against the
simulation's 3.15%** — 0.01 points apart, the closest median parity anywhere in the study, on
740 rides from four riders sharing no rider, country, terrain or device with the calibration
set. The registered band was 3.5–6.2%; the result lands *below* it, i.e. the law transfers
better than predicted, which is recorded here as a deviation on the favourable side rather
than quietly absorbed. The per-ride sign test still favours the simulation (F3·ε_d closer on
338/740, p = 0.0205) — median parity, not per-ride equivalence, the same split D5 shows.

Two of paper 1's core claims replicate cleanly out of sample: the **climb-aero split** cuts
error from 12.59% to 4.28% (F2 closer than F1 on 696/737 rides, p < 10⁻⁴), and the **deadband**
takes it further to 3.16%.

**P2 — confirmed quantitatively.** The registration predicted, from geometry alone and before
any energy was computed, that F4's frozen c = 3 m/km against this corpus's measured 1.24 would
push its bias **3–6 points below F3's**. Measured: **−4.19 points** under ε_d (+1.97 → −2.22)
and −5.85 under ε_f. Both inside the registered window. This is the study's first
out-of-sample *quantitative* prediction, and it lands: the scalar correction is a property of
the recording chain, not a universal, exactly as §2.4 warns.

Worth noting how the failure hides: on user_1 the over-correction *improves* apparent accuracy
(F4 3.54 vs F3 5.76) by cancelling a positive bias, while on user_2 it degrades it (4.72 vs
2.21). Accuracy alone would have told opposite stories about the same defect on two riders —
the accuracy-and-bias-together rule earning its keep.

**P3 — split verdict; the registered band fails per rider.** The gap on real descents
(mean descent grade ≥ 3%):

| rider | n | gap | ε_coast | ε_bal |
|---|--:|--:|--:|--:|
| user_1 | 148 | 0.117 [0.11, 0.13] | 0.49 | 0.36 |
| user_2 | 265 | **0.298** [0.28, 0.31] | 0.66 | 0.37 |
| user_3 | 162 | **0.080** [0.07, 0.09] | 0.44 | 0.37 |
| user_5 | 12 | 0.175 [0.15, 0.21] | 0.60 | 0.42 |
| pooled | 587 | 0.160 [0.14, 0.18] | 0.56 | 0.37 |

The **sign recurs on all four riders** and the pooled 0.160 sits inside the registered
0.10–0.19. But the per-rider spread is **0.080–0.298**, a 3.7× range far outside it, and two of
four riders fall outside the band. Per the registered failure mode this **bounds the deficit's
portability**: what travels is the sign, not the value.

The sub-finding is more interesting than the verdict, and is flagged as **exploratory,
disclosed** because nothing predicted it: **ε_bal is nearly rider-invariant at 0.36–0.42 while
ε_coast ranges 0.44–0.66.** On this corpus the gap's spread is driven almost entirely by the
*geometric ceiling*, not by the behavioural term — the opposite decomposition to the one
§4.1.3 tells ("the geometry sets the ceiling; the habit sets the discount"). A constant
*recovery* would describe D6 better than a constant *deficit* does. Whether that survives the
regime-consistent protocol (where α, hence ε_coast, is re-derived per ride) is the obvious next
experiment and is NOT claimed here.

**P4 — the inversion validates against four known masses.** Implied system mass minus published
body mass, after the m·g rescale: user_2 +8.4, user_3 +7.8, user_5 +10.9 — all inside the
registered 7–12 kg bike-and-kit window — and **user_1 +13.7, outside it**. The ordering is
**preserved over all five determinate pairs**. (The harness first printed a violation; that was
a bug in the test, not the data — user_2 and user_5 share a published 72 kg, so their relative
order is undetermined and a strict list comparison mis-scored the tie. The test is now
tie-aware; the verdict is unchanged data, corrected reading.) Three-of-four inside the window
on riders whose bikes are unknown is a real external validation of machinery that had, until
now, exactly one known value to check against.

**P5 — half supported, half untested.** ε_d beats ε_f decisively on user_3, the Alpine rider
(3.83 vs 9.00), as registered. But it also wins on the three gentler riders (2.21 vs 7.68;
5.76 vs 10.39; 2.18 vs 9.88), where the registration expected the flat constant to do better.
Read against §3.2, the rule's other branch is not so much refuted as **not exercised**: all
four are open-road riders whose real descents are genuinely coastable (ε_coast 0.44–0.66), and
none ride urban stop-go, which is the regime ε_f was selected on. D6 tests one branch of the
regime rule and is silent on the other.

### What this does and does not license

D6 answers the reviewers' question — *does the law leave São Paulo?* — with a clear yes at
median parity, and it independently replicates the climb-aero split, the deadband, and the
sign of the coasting deficit on riders who share nothing with the calibration corpus. It does
**not** deliver a population value for ε₀; if anything it argues the value is less portable
than paper 1 currently implies, and the ε_bal-invariance above suggests the decomposition
itself may want revisiting.

**Not yet done:** gates in `bootstrap_ci.py` for these medians. `bootstrap_ci.py` currently
carries uncommitted edits from the parallel paper-2 line, so the gate section is deliberately
deferred rather than merged blind — it must land before any of these numbers enter a paper.

### Amendment (registered before running; 2026-07-29, same day)

*Prompt (Danilo), on the P3 spread: "My suspicion is that the dataset comes from seasoned
amateur road cyclists. They do have a tendency to pedal while descending. Their power strategy
is not efficiency-maximizing. This does not happens with myself, JAAM and PPaz, which are
specialists in self-supported, ultra-distance rides, where efficiency is a key concern. Can we
also test doing the parameter inversion protocol rather than frozen parameters?"*

Two arms, both registered here before either runs. Arm A executes the secondary protocol the
main registration already declared; Arm B is a **new** test of a rider-behaviour hypothesis and
is registered fresh.

**Arm A — the regime-consistent protocol on D6.** Per-ride m̂_r and Ĉrr_r from the Entry-33
segment inversion (importing `perride_invert`'s machinery unchanged — it is import-safe), then
the Entry-35 regime-consistent aero
$\hat C_{dA,r}^{\mathrm{reg}} = \bigl(k_{\mathrm{eff}} P_{\mathrm{flat}}/v_{\mathrm{meas}} - \hat C_{rr,r}\,\hat m_r g\bigr) / \bigl(\tfrac{1}{2}\rho\,v_{\mathrm{meas}}^2\bigr)$,
which closes the flat balance at the *measured* flat speed by construction. Wind stays 0: `perride_invert`'s wind path
fetches weather at the ride's 0.25°-quantized centroid, and for D6 those centroids derive from
third-party riders' home addresses, so the fetch is deliberately not used here (it also keeps
D6 on the same zero-wind footing as every other blind corpus). ε₀ = 0.13 stays frozen; nothing
about ε is refitted. *Registered expectation:* if D6's high ε_bal (0.36–0.42 vs the Brazilian
riders' 0.17–0.28) is an artefact of the frozen C_dA = 0.40 being wrong for these riders, the
regime-consistent α should move ε_coast and ε_bal together and **shrink the per-rider deficit
spread** from its frozen 0.080–0.298. If the spread survives, the frozen priors were not the
cause.

**Arm B — is it descent pedalling? A physics-free measurement.** The hypothesis above predicts
a *behavioural* difference, so it is tested with a quantity that involves no C_dA, no C_rr and
no α — nothing that could smuggle in a parameter error. On 30 m cells with grade ≤ −3% and
speed ≥ 0.5 km/h, measured identically on D6 and on D1/D3/D4/D5:

- **descent pedalling occupancy** = Σ dt with power ≥ 10 W ÷ Σ dt, and
- **descent intensity ratio** = mean descent power ÷ mean flat power (same ride).

Both are read straight off the power stream. *Registered prediction (Danilo's, stated as his):*
D6's occupancy exceeds the Brazilian riders' at comparable descent grade, because
ultra-distance self-supported riding selects for coasting and amateur road riding does not.
*Failure:* if D6 occupancy is equal or lower, the P3 spread is not descent-pedalling behaviour
and the ε_bal invariance needs a different explanation. Occupancy is grade-dependent
(Entry 34), so the comparison is reported per descent-grade band, not pooled — a corpus with
steeper descents would otherwise look like a corpus that coasts more.

Thresholds (10 W, −3%, 0.5 km/h) are fixed here, before the run, and are the values the repo
already uses elsewhere (`POW_MIN`, the real-descent gate, `VSTOP`).

### Amendment results

`python3 src/harness/skc_invert.py` → `skc_invert.csv` (743 rides) and
`skc_descent_occupancy.csv` (2,193 rides across all six corpora).

**A methods bug caught between the first and second run, disclosed.** Arm A's first pass fell
back to a generic 78 kg wherever the strict Entry-33 segment gates found no qualifying climb —
which was **55% of rides** (mass inverted on only 332/743, Ĉrr on 214). For user_1, whose
sustained-climb mass is 99.9 kg, that put a 20 kg error on the majority of his rides, and it
meant Arm A changed the *mass* source at the same time as the *aero* source, making the
frozen-vs-inverted contrast uninterpretable. Fixed: the fallback is now each rider's own
sustained-climb anchor, **recomputed at runtime** (never frozen into a literal — an implied
mass moves with G; Entry 27). A second defect surfaced with it: the per-ride inversion has
non-physical tails — two rides return a *negative* mass — so `perride_invert`'s physical-range
filter now runs before the median. At full scale the filter touches 3 of 429 values and the
anchors reproduce the frozen protocol's masses (99.9 · 80.7 · 68.8 · 83.1 vs 99.9 · 80.6 ·
68.9 · 83.1), which is what makes the re-run a clean **aero-only** contrast. All numbers below
are the corrected run.

**Arm A — regime-consistent aero, 743 rides.** Inverted ĈdA_reg medians: 0.396 · 0.385 ·
0.349 · 0.419. Notably these sit *close to the frozen 0.40*, unlike the Brazilian corpora,
where §3.4's inversion came out low everywhere (0.26–0.39): **the frozen prior's adequacy is
itself rider-dependent.** Ĉrr fell back to 0.008 on 71% of rides, so the protocol is best
described as "regime-consistent aero at anchored mass", not full per-ride inversion.

| model | pooled med \|Δ%\| | bias | (frozen protocol, for contrast) |
|---|--:|--:|--:|
| F3 · ε_d | 3.05 [2.7, 3.3] | +0.81 [0.3, 1.2] | 3.16 · +1.97 |
| F4 · ε_d | 4.34 [4.0, 4.7] | −3.37 [−3.7, −3.1] | 4.04 · −2.22 |
| F3 · ε_f | 6.71 [6.4, 7.0] | +6.68 [6.4, 7.0] | 8.45 · +8.42 |
| F4 · ε_f | **2.49 [2.3, 2.7]** | +0.99 [0.5, 1.5] | 3.58 · +2.58 |
| simulation | **1.59 [1.5, 1.8]** | +0.55 [0.3, 0.7] | 3.15 · +1.96 |

**Parity breaks on D6.** Under the frozen protocol the law and the simulation were 0.01 points
apart (3.16 vs 3.15). Under the regime-consistent aero the simulation improves by half
(3.15 → 1.59) while F3·ε_d barely moves (3.16 → 3.05), **opening a 1.46-point gap**. This is
the opposite of what the same protocol change does on the Brazilian corpora, where Table 6 has
them pooling to 3.9 vs 4.0 — still parity. The form ranking also shifts (F4·ε_f becomes the
best closed form at 2.49), which is the (α, ε) bundle rule of §4.3.4 doing exactly what it
says: the ranking is a property of a (physics, ε-variant) pair, not of the forms.

**Arm B — the descent-pedalling hypothesis is confirmed.** Occupancy (share of descent time
with power ≥ 10 W), by grade band, 2,193 rides:

| corpus | 3–5% | 5–8% | >8% | P_desc/P_flat |
|---|--:|--:|--:|--:|
| D6 user_2 (Catalonia) | 0.716 | 0.491 | 0.157 | **0.624** |
| D6 user_1 | 0.600 | 0.401 | 0.167 | 0.387 |
| D6 user_5 | 0.555 | 0.306 | 0.364 | 0.416 |
| D6 user_3 (Alps) | 0.510 | 0.239 | 0.082 | 0.310 |
| D1 longões | 0.411 | 0.201 | 0.097 | 0.311 |
| D3 P. Paz | 0.436 | 0.218 | 0.112 | 0.234 |
| D4 JAAM | 0.373 | 0.267 | 0.254 | 0.287 |
| D5 the author | 0.262 | 0.113 | 0.039 | **0.157** |
| D2 censo (urban) | 0.101 | 0.039 | 0.016 | 0.100 |

Pooled D6 vs the Brazilian corpora, with disjoint 95% CIs in **every** band: 3–5%
0.654 [0.633, 0.668] vs 0.334 [0.321, 0.344]; 5–8% 0.407 [0.389, 0.426] vs
0.167 [0.158, 0.176]; >8% 0.137 [0.121, 0.152] vs 0.076 [0.067, 0.082]. **Roughly double the
pedalling occupancy at every gradient**, including the steep band where gravity most invites
coasting. The intensity ratio makes the same point in one number: user_2 rides descents at 62%
of his flat power, the author at 16%.

The metric independently reproduces §3.3's characterisation of JAAM as a rider who pedals his
descents — he is the highest Brazilian above 8% (0.254) — without that ever being an input.
P. Paz sits between JAAM and the author, which is consistent with §3.3 calling him a
"coasting-style descender" *relative to a typical rider*: on the steep band that the ε
machinery actually uses he is at 0.112, less than half JAAM's. (An earlier draft of this entry
read his being above the author as a tension with §3.3. It is not: the corpora describe a
**spectrum**, not two categories, and the author simply sits at its coasting extreme.) Within
D6 the same gradient appears — the Alpine user_3 is the least pedalling of the four (0.310
intensity, essentially D1's) — so the measure tracks terrain as well as riding culture.

Ordered by descent intensity the whole study now reads as one continuum: the author 0.157 ·
P. Paz 0.234 · JAAM 0.287 · user_3 0.310 · D1 0.311 · user_1 0.387 · user_5 0.416 ·
user_2 0.624 (D2's urban 0.100 is a different regime — stopping, not coasting). The
ultra-distance self-supported riders occupy the low end and the amateur road cyclists the
high end, which is the hypothesis this amendment was written to test.

**A mechanism proposed and then withdrawn — note precisely WHICH one.** What is withdrawn
below is a claim about the *law-versus-simulation gap*, not about the deficit. The claim that
descent pedalling drives **ε₀ itself** is a different proposition, and arm C tests it directly
and supports it. The obvious link between the arms is that the
simulation is fed each ride's own descent regime power while ε_d is a purely geometric refund
that cannot represent a rider adding power downhill — so the law should lose most on the
riders who pedal descents hardest. **The per-rider ordering does not support it.** Law-minus-
simulation gaps are user_1 2.74 · user_2 0.81 · user_5 0.68 · user_3 0.36, while descent
intensity orders user_2 > user_5 > user_1 > user_3. user_1 has the largest gap and only middling
pedalling. A more likely reading for him is mass: his anchor is 99.9 kg against a published
body mass of 86 (the +13.7 kg that already failed P4's window), which inflates β and shows up
as his +4.51 F3·ε_d bias — the largest over-prediction in the corpus. The weaker claim that
*does* survive is that F3·ε_d's **bias** orders with descent intensity on three of four riders
(user_2 −1.30 most pedalling, user_3 +2.06 least), with user_1 the exception and user_1 the
rider with the known mass anomaly. At n = 4 riders this is a hypothesis for a future corpus,
not a result.

**P3 under inverted physics — the registered expectation is refuted.** The amendment predicted
that if the deficit spread came from the frozen C_dA being wrong for these riders, the
regime-consistent α would shrink it. It does not: 0.120 · 0.306 · 0.095 · 0.178 (range 0.211)
against the frozen 0.117 · 0.298 · 0.080 · 0.175 (range 0.218) — **unchanged**. The spread is
not a physics artefact. Given Arm B, rider behaviour is the live explanation, though the
per-rider mapping above is not clean enough to call it demonstrated.

### Arm C — does descent pedalling predict the deficit? (`skc_eps_vs_pedal.py`)

*Prompt (Danilo): "this reinforces the robustness of the interpretation of ε₀ as being
generated by descent pedalling."* Tested at **ride** level rather than by eyeballing corpus
medians, on the 1,038 rides across all six corpora that carry a real descent
(mean descent grade ≥ 3%): Spearman between the physics-free pedal ratio
(mean descent power ÷ mean flat power) and the measured deficit ε_coast − ε_bal.

| group | n | pedal ratio | deficit | ρ(pedal, deficit) [95% CI] |
|---|--:|--:|--:|--:|
| D6 user_1 | 149 | 0.362 | 0.117 | 0.791 [0.70, 0.86] |
| D6 user_2 | 267 | 0.590 | 0.297 | **0.907 [0.87, 0.93]** |
| D6 user_3 | 162 | 0.258 | 0.080 | 0.627 [0.49, 0.74] |
| D6 user_5 | 12 | 0.416 | 0.175 | 0.629 [0.01, 0.98] |
| D1 longões | 22 | 0.191 | 0.122 | 0.813 [0.56, 0.95] |
| D2 censo | 26 | 0.110 | 0.093 | 0.197 [−0.25, 0.60] |
| D3 P. Paz | 156 | 0.182 | 0.098 | 0.407 [0.25, 0.55] |
| D4 JAAM | 20 | 0.146 | 0.127 | 0.817 [0.50, 0.94] |
| D5 the author | 224 | 0.174 | 0.117 | 0.607 [0.50, 0.69] |

**Pooled ρ = 0.726 [0.69, 0.76]; positive in 9 of 9 groups**, median within-group ρ = 0.629.
The within-rider figure is the load-bearing one: on the days a given rider pedals his descents
harder, *his own* measured deficit is larger. That holds for every rider in the study.

**The circularity caveat, stated plainly, because it changes what this is worth.** Paper 1
already derives the deficit's exact ledger identity (§4.4.2, [Appendix A](#appendix-a)):
δ = E_legs,− / (β h_−) — the deficit **is** descent pedal energy over the scaled drop. Both
quantities correlated here therefore contain E_legs,−, so a positive ρ is substantially
*mechanical*, not an independent discovery. (It is not 1.0 — the pedal ratio normalises by
flat power and descent time rather than by β h_−, which is why ρ runs 0.41–0.91 — but the
shared term dominates.) **Arm C is a consistency check, not new evidence.**

What the three arms buy together is better than a correlation: a **closed chain**.
(1) Arm B measures, with no ε and no physics anywhere in it, that the D6 riders pedal descents
about twice as much as the Brazilian riders — a fact about power streams alone.
(2) The §4.4.2 identity then *requires* their deficits to differ; this is not an inference.
(3) P3 measures exactly that difference (0.080–0.306) and shows it survives the
regime-consistent physics, so it is not a parameter artefact.
Danilo's reading — "some people coast, others pedal a bit and others pedal a lot, and this
affects ε₀" — is therefore not merely supported by correlation; it is the identity plus a
measured population difference. The honest limit is that this **bounds the constant's
portability**: ε₀ ≈ 0.13 is a property of a riding population, and the ultra-distance
self-supported riders it was calibrated on sit at the coasting end of the spectrum.

D2 (urban) is the weakest correlation (0.197, CI spanning zero) and should be read as a
different regime: there the descent energy is disposed of by braking at intersections rather
than by pedalling, which is the §3.2 mechanism, not this one.

### Notes carried forward

The exploratory ε_bal-invariance noted in the main results **weakens** under this protocol:
ε_bal spans 0.31–0.43 (it was 0.36–0.42 frozen) against ε_coast's 0.43–0.66. Still the tighter
of the two, but no longer near-constant, so the "constant recovery rather than constant
deficit" reading should not be carried further without a dedicated test.

---

## 2026-07-28 — Entry 42: the lumped ε_d — pricing the hand recipe's proxy

**Lineage** — $I$: $(D_1..D_5, P_{f,r})$ · $T$: F3, lumped $\varepsilon_d$ · $O$: `e42_lump.csv` (1,378) · $S$: the hand recipe stops recommending it

*Prompt (Danilo), on review-v4's finding that §4.1.2's lumped variant is validated nowhere at
energy level: "we should use the inverted params protocol. let's assume that mean descent
grade = corrected vertical meters / x_downhill (eg. fraction of distance below threshold).
test it and compare. If the result is not favourable, then we should not recommend using the
mean descent as a proxy."*

### Pre-registration (written before any result was seen)

**The gap.** Every ε_d cell in the paper's tables uses the drop-weighted estimator (eq. (5),
`eps_geom`); the §4.1.2 hand recipe prescribes the lumped variant, eq. (3) at the mean
descent grade. The lumped form's only evidence is Entry 8's ε-space ladder on D1 under
retired conventions. This entry scores it at energy level, everywhere.

**Protocol** ([`e42_lump.py`](../../src/harness/e42_lump.py)). Corpora D1–D5, Entry-33/35
populations. Physics: the **regime-consistent per-ride set** (m̂ᵣ, Ĉ_rr,ᵣ, ĈdAᵣ^reg, wind,
joined from `e35_residual.csv`) — the near-zero-bias pair, so the lumped-vs-drop-weighted
difference is not laundered through a standing bias (the Entry-39 deconfounding logic).
Definitions, fixed now:

- **s̄_lump = h̃₋ / x₋** — corrected vertical metres (τ = 2 m deadbanded descent total) over
  the descending distance (Σ of 30 m cells of the deadbanded profile with grade ≤ −1.5%,
  the paper's x₋);
- **ε_lump = min(1, (α/β)/s̄_lump) − ε₀**, unclamped, α/β at the ride's model v_f — exactly
  the recipe's arithmetic;
- scored: F3 · ε_lump and F4 · ε_lump against measured energy, beside F3/F4 · ε_d
  (drop-weighted; the F3 · ε_d column must reproduce Entry 35's regime medians — parity
  gate) — accuracy AND bias with 95% CIs, paired lumped-vs-drop-weighted sign tests;
- diagnostics: per-ride ε_lump − ε_d (median, IQR) and Spearman ρ of |paired Δ%-difference|
  against the descent-grade dispersion (SD of descent-cell grades) — the mixed-descent
  mechanism, finally measured.

**Registered predictions.**

- **P1 (favourable threshold):** the lumped penalty is ≤ 0.5 pp of med|Δ%| per corpus with
  bias shifts ≤ 1 pp — the proxy is fine for hand use.
- **P2 (mechanism):** where the two diverge, it is on mixed-descent rides (ρ > 0 against
  grade dispersion), and the lumped form's error is an *over-refund* (the min(1,·) cap
  binds harder on the lumped mean than drop-weighting allows: gentle cells drag s̄ down,
  inflating ε_lump).
- **P3 (the decision rule, fixed by Danilo now):** if the penalty exceeds ~1 pp of median
  error or shifts bias materially on any open corpus, **the paper stops recommending mean
  descent grade as a proxy** — §4.1.2 is rewritten (flat ε_f as the hand default, the
  drop-weighted estimator labelled software-only), rather than the proxy being kept with a
  caveat. Either outcome is publishable; the unfavourable one changes the recipe.

### Results (first full run, 2026-07-28 — 1,378 rides; populations shrink slightly where no cell clears the descent threshold: D3 433, D4 215, D5 617)

Parity gates green on D1–D4; D5 reads 5.04 vs the 4.9 anchor — the 617-vs-636 population
difference, same disclosed class as Entries 33/35. F3 rows (med|Δ%| [CI] · bias [CI]):

| corpus | F3 · ε_d (drop-weighted) | F3 · ε_lump | paired (lump closer) | ε_lump − ε_d |
|---|--:|--:|--:|--:|
| D1 | 6.6 [3.8, 8.1] · +0.1 [−1.7, +5.0] | 6.3 [4.1, 8.8] · **+3.6** [+1.3, +8.8] | 19/44, p = 0.45 | −0.079 |
| D2 | 4.6 [2.7, 6.1] · +1.4 [−0.3, +3.7] | **7.2** [5.1, 10.4] · **+6.1** [+4.3, +8.3] | 16/69, p < 10⁻⁴ | −0.112 |
| D3 | 3.1 [2.9, 3.3] · −1.4 [−1.9, −0.9] | 3.1 [2.7, 3.5] · +0.6 [+0.1, +0.9] | 221/432, p = 0.67 | −0.083 |
| D4 | 3.2 [2.8, 3.6] · −2.7 [−3.0, −2.2] | 2.6 [2.3, 2.8] · −1.3 [−1.7, −0.6] | 143/215, p < 10⁻⁴ | −0.110 |
| D5 | 5.0 [4.7, 5.5] · −0.8 [−1.4, −0.1] | 4.7 [4.2, 5.4] · **+2.7** [+1.7, +3.4] | 287/617, p = 0.09 | −0.098 |

**The mechanism (P2: half-confirmed, direction refuted).** The proxy under-refunds by a
near-constant **−0.08 to −0.11 of ε on every corpus** — the registered prediction had the
sign backwards. The cause is definitional: h̃₋ accumulates descent metres from *all*
downhill cells while x₋ counts only cells steeper than −1.5%, so s̄_lump = h̃₋/x₋ is biased
steep and eq. (3) refunds less. The dispersion mechanism is confirmed (ρ of the paired
|Δ%-difference| against descent-grade SD: +0.17 to +0.55, positive everywhere): mixed
descents diverge most, as registered.

**Why the accuracy columns flatter the proxy (do not be fooled).** On D3/D4/D5 the
under-refund's positive push *cancels* the regime-physics residual negative biases — D4's
"significant win" (p < 10⁻⁴) is two wrongs netting, the exact artifact class Entry 29
taught us not to reward. The bias columns tell the truth: shifts of +1.4 to +4.7 pp
everywhere. And this regime-physics test was the proxy's *best case*: under the frozen
priors (the recipe's actual context) D1/D5 carry positive standing biases, so the proxy's
push would compound rather than cancel.

**Verdict (P3, the registered decision rule): UNFAVOURABLE.** D2 fails on accuracy outright
(+2.6 pp, p < 10⁻⁴); the open corpora fail on the bias criterion (+3.5 pp on D1 and D5).
Per the rule Danilo fixed at registration, **the paper stops recommending mean descent
grade as a proxy**: §4.1.2's hand default becomes the flat ε_f = 0.20 — honestly framed as
conservative (it under-refunds open descents, so the hand estimate errs toward
*overestimating* the energy demand, the safe direction for planning) — and the
drop-weighted ε_d of eq. (5) is labelled software-only. Executed in the paper the same day.

Instrument: [`e42_lump.py`](../../src/harness/e42_lump.py) (`E42_SMOKE=1`); output
`e42_lump.csv` (1,378 rides); the five ε-offset medians and the two decisive paired tests
are gated in `bootstrap_ci.py`.

---

## 2026-07-28 — Entry 41: the elevation-source substitution — paper 1's law on planner DEM profiles

**Lineage** — $I$: $(D_1..D_5 \text{ routes}, \mathrm{DEM})$ · $T$: F3 on planner profiles · $O$: `e41_dem_route.csv` (1,188) · $S$: **paper 2's headline**

*Prompt (Danilo): implement `research/article/paper2-dem-deployment.PLAN.md` — the letter on
deploying the closed form at planning time, where there is no barometric stream. Mid-flight
amendments: use the WIDE IGC-SP raster (`mdt_igc_2010.tif`) rather than the validated
`sampa_geral.tif` crop, "but be careful, as the data quality is not homogeneous — some places
have seams… if we detect them when cropping, we should not use it for that crop"; and "it is
supposed to be a DTM, but sometimes behaves as a DSM… keep an eye on anomalies and don't be
afraid to filter rides out."*

### Pre-registration (written before any full run)

**The question.** Paper 1 validates $E \approx \alpha x + \beta(h_+ - \varepsilon h_-)$ on
the rides' **own barometric elevation streams**, and excludes DEMs by design (§2.3.4 after the same-day renumbering). A
planner has no such stream: it has a polyline and a DEM. What does the elevation-source swap
cost the law, and what is the cheapest repair that keeps it?

**The design — ONE substitution.** Every ride is re-evaluated with the elevation profile
replaced by a DEM sampled along its own recorded track. Measured power, per-ride regime
powers, masses, the frozen priors (Crr 0.008 · CdA 0.40 · ρ 1.13 · k_eff 0.98 · wind 0 ·
G 9.7864), τ = 2 m, c = 3 m/km, ε₀ = 0.13, ε_f = 0.20 — all unchanged. So every gap between
an arm and the control is the elevation source and nothing else. ε_d IS recomputed on the
substituted profile: it is geometry-dependent by construction (paper 1 eq. (4)–(5),
unclamped), and holding it fixed would hide half the effect.

**Seven arms, one grid.** Every arm lives on the ride's own 5 m arc-length grid. A coarser
polyline step is sampled at that step and linearly interpolated back onto the 5 m grid —
linear interpolation adds no local extrema, so h±, the τ deadband and ε_coast read the coarse
geometry while the scoring grid stays fixed. Only the SOURCE varies.

| arm | elevation source | polyline step | pre-smoothing |
|---|---|---|---|
| `own` | recorded barometer (paper-1 control) | 5 m | — |
| `igc5` | IGC-SP 2010 5 m DTM | 5 m | — |
| `igc5s10` | IGC-SP 2010 5 m DTM | 5 m | 1-D Gaussian σ = 10 m |
| `igc5s30` | IGC-SP 2010 5 m DTM | 5 m | 1-D Gaussian σ = 30 m |
| `igc30` | IGC-SP 2010 5 m DTM | 30 m | — |
| `fab5` | FABDEM V1-2 (30 m, global) | 5 m | — |
| `fab30` | FABDEM V1-2 (30 m, global) | 30 m | — |

The σ arms smooth the **profile**, not the raster — the operation a planner can actually run
(it holds a polyline, not a 20 GB GeoTIFF), and mask-normalized exactly like Entry 20's
deployable raster scheme. That substitution is a **gate, not a result** (below).

**Amendment — the physics protocol (Danilo, before any full run: "we should use the
ride-inverted params rather than the frozen priors").** Every arm is evaluated under **two**
protocols, and the **regime-consistent per-ride physics is primary**: m̂, Ĉrr, ĈdA_reg and
wind joined per ride from `e35_residual.csv` (Entry 35 / paper 1 §3.5.2, Table 6). The reason is the
same deconfounding that produced Entry 39 out of Entry 38: at the frozen priors every corpus
carries a standing bias, so swapping the elevation source partly *cancels or amplifies* that
bias and med|Δ%| reads the bias rather than the source. Entry 19 measured exactly this
failure — "JAAM is the under-predicted corpus, so the spurious extra energy lands as
accuracy," and igc5 beat igc30 there for no good reason. At the regime-consistent α the
honest (α, ε) pair is ε_d on every corpus (Entry 35), so the bundle rule (paper 1 §4.3.4)
is respected rather than assumed. The **frozen-prior protocol is retained** as the second
arm of the contrast, and it is what the PARITY gate checks — it is the protocol paper 1
published, so it is the only one with a published reference. Rides with no `e35_residual`
row fall back to the frozen constants, flagged per ride (`e35_join`). The physical floor
that defines the population stays at the frozen protocol, so the population is paper 1's
regardless of the amendment. One property of this choice is load-bearing and is stated here
so it is not mistaken for circularity: the per-ride constants are inverted ONCE, from the
ride's own recorded stream, and then held FIXED across all seven arms. Re-inverting them per
arm would let mass and drag absorb the elevation error and hide exactly what the experiment
measures — the circularity paper 1 §2.3.3 warns about (renumbered same day). The constants are a property of the
rider and the bicycle; a planner knows them without knowing the DEM.

**Models.** F1–F4 × {ε_d, ε_f} + the forward simulation, per arm. The CSV stores the closed
form's components per arm (a_roll, a_aero, X, h± raw and deadbanded, aero gated and ungated),
so any F-variant at any ε and any noise rate c is arithmetic afterwards — which is what P3's
per-source c refit needs, with no second engine pass.

**Populations.** The paper-1 clean corpora (D1–D5, their own filters verbatim, including the
physical floor E_meas ≥ β·h̃₊/k_eff evaluated on the `own` arm) intersected with the QA gates
below. They will NOT equal paper 1's corpora — raster coverage and track quality both cut —
and the funnel is reported per corpus. Notably **D1 and D5 contain rides outside São Paulo**
(D1: Roraima, Rio de Janeiro, Poland/Ukraine; D5: Lombardy), which simply fall outside the
raster; this is disclosed, not repaired.

**QA gates** (pre-registered, applied identically to every arm so no arm is advantaged):

- **G1 track quality** — the share of route length sitting inside GPS-fix gaps > 50 m must be
  ≤ **0.5%**. A planner's polyline has no dropouts; where the recording lost GPS, the track
  is a straight chord and the DEM charges terrain the rider never crossed. **This gate comes
  first**: the largest profile artifacts on the *validated* raster are track dropouts, not
  raster defects (measured, this entry: the worst one-step |Δh| on Entry 20's 864 cached
  profiles are 638 m, 537 m, 320 m — all at GPS gaps of 294 m, 223 m, 1,426 m). A single
  max-gap threshold was tried first and rejected as disproportionate: it scales with ride
  length, so it deleted all of D1. Census over all 1,493 candidate rides (this entry, before
  any energy was scored): median gap share 0.000–0.006% per corpus, so the gate bites only on
  the tail — it keeps 38/43 D1, 66/70 D2, 484/486 D3, 222/223 D4, 630/671 D5.
- **G2 raster validity** — ≥ 99% of a ride's samples with 0.5 m < h < 3000 m, on every arm.
  The wide survey stores voids as huge magnitudes (band min −40,263, max +7,955), so the
  band is two-sided, unlike Entry 19's `h > 0.5` on the crop.
- **G3 anomaly census** — a one-step |Δh| > 10 m over a 5 m step is a 200% grade: a defect
  (block seam, void edge, or an un-filtered building/canopy wall where the DTM behaves as a
  DSM), not terrain. Counted per arm and reported. G1+G2 and G1+G2+G3 are **co-primary**
  populations and the letter reports both: the anomaly-free one is what a planner gets after
  QA-ing its crop (Danilo's "filter rides out"), the full one is what it gets if it does not
  check. G3 is applied jointly across arms — a ride is dropped only if ANY arm carries an
  anomaly — so the comparison stays paired and no source is advantaged by its own defects.

**Estimands.** Per corpus and per arm: median |Δ%| and median signed Δ%, each with a 95%
percentile bootstrap CI (mulberry32, seeds 42/43, B = 10⁴ — house convention), for
F3·ε_d, F4·ε_d, F3·ε_f, F4·ε_f and the simulation; the paired per-ride Δ%(arm) − Δ%(own);
the per-arm noise rate c(τ=2) = (h₊ − h̃₊)/x; the per-arm h₊ ratio to the control; the per-arm
ε_d. Headline pool = D3+D4 (the two independent riders), mirroring paper 1's out-of-sample
headline.

**Registered predictions.**

- **P1 — the raw fine DEM over-charges.** Entry 6 put the recorded barometer 21% *below* the
  5 m survey on smoothed ascent (k_DEM = 1.26); Entry 19 found h₊(igc5) > h₊(igc30) on
  919/922 rides. Arithmetic for a typical D3 ride (h̃₊ ≈ 500 m, E ≈ 900 kJ, β = 0.744 kJ/m):
  a +26% ascent inflation is Δh₊ ≈ 130 m → +97 kJ gross, of which the descent term refunds
  ≈ ε ≈ 0.45, leaving ≈ +6%. **Registered: `igc5`'s signed bias exceeds `own`'s by a median
  +3 to +10 pp on the D3+D4 pool, positive on every corpus.** Falsified by a negative or
  null shift.
- **P2 (headline) — smoothing restores the calibration.** Entry 20's gate levels are
  med|Δ%| < 5 and |bias| < 2. **Registered: at σ = 30 m — the scale ε₀ was calibrated on —
  F3·ε_d's med|Δ%| lands within 2 pp of its own-stream value and |bias| < 2 on D3+D4.**
  *Failure mode:* if P2 fails, the letter's conclusion inverts — planner-grade DEM energy
  needs per-source recalibration and the prescription table becomes a warning table. Either
  outcome is publishable; the letter ships either way.
- **P3 — c is a property of the source, not a constant.** Paper 1 measures c = 3.1 m/km on
  barometric recordings (IQR 2.6–3.7); Entry 38 puts c(τ=2) at 2.5–4.5 m/km across corpora.
  **Registered: (a) `igc5`'s c exceeds 4.5 m/km and `fab5`'s exceeds 6.0 m/km, each with a
  95% CI clear of the barometric 3.1; (b) recomputing F4 with the arm's own median c brings
  F4's bias within 2 pp of F3's on the same arm**, whereas the frozen c = 3 leaves it
  strongly positive on the noisiest sources.
- **P4 — the artifact tail.** Two operationalizations, because E26's portal detector fires
  on 915 of 923 rides and is therefore useless as a binary flag. **(a)** The G3 anomaly-free
  subset shifts the DEM arms' median by ≥ 1 pp toward the control relative to the full
  population. **(b)** Where the E26 join exists, the top decile of portal exposure
  (`span_m` per route-km, `dh_plus_removed_igc5`) carries a more positive DEM-minus-own
  residual than the rest by ≥ 1 pp.

**Extension — the portal CORRECTION (Danilo, after the first full run: "there's something
missing, which is to compute also the effect of including portals"). Registered here before
the extension run; the first run's results above stand unchanged.** P4 as written said
"E26 detection flags them; report with and without", and the first run read "with and
without" as with/without the affected *rides* (the exposure-decile contrast, P4b). That
leaves the operationally useful question unanswered: what does *correcting* portals buy?
Every DEM arm therefore gains a corrected twin `<arm>p`. Where the track runs along a mapped
OSM bridge or tunnel span — Entry 26's detector with every threshold verbatim (25 m
proximity, 30° heading, 60% coverage, 50 m abutment projection, extent within [0.6, 2.0]×
deck) — the heights across the span are replaced by a straight deck. Closed forms only; the
simulation adds nothing to a geometry question and costs the most.

*Two disclosed deviations from Entry 26.* (i) The deck runs between **the arm's own profile
heights at the projected abutments**, not E26's raster heights at the abutment nodes: it
needs no extra raster sampling, it cannot introduce a step at the span ends, and each arm is
corrected in its own elevation units. (ii) The treatment is **offline-only** — a ride joins
iff every 0.1° OSM tile its bbox needs is already in E26's cache, so the run issues no
Overpass request and no ride-derived geometry leaves the machine. That restricts the
treatment to E26's footprint (the old validated-crop area), so D1's brevets are largely
outside it; rides not covered are reported as such rather than fetched.

**Registered prediction P5.** The correction removes ascent (median Δh₊ < 0 on every arm)
and moves each DEM arm's bias toward the control, by more on the raw fine survey than on the
σ = 30 m arm — because smoothing already flattens part of the valley a bridge spans. Failure
mode: no bias improvement, or h₊ rising, would mean the detector is matching spans the track
does not cross, and the portal thread would be closed as unusable at route grain rather than
carried into the letter.

**Registered prediction P6 — the straight deck OVER-corrects (Danilo, before the extension
run: "I would expect them to mostly overcorrect. Most bridges tend to go up and then down,
while the portal assumes a straight line between the endpoints").** A road bridge carries a
vertical curve: the rider climbs onto the crown and descends off it, and that ascent is real
work. Entry 26's v19 deck is a straight line between abutments, so it erases the crown along
with the DEM's spurious valley — an over-correction on bridges. Tunnels should behave the
opposite way: there the DTM climbs over the pierced ridge while the road runs level or dips,
so a straight line is close to right and the correction is nearly all signal.

*The test needs no model.* For each matched span we accumulate ascent **inside the span
only**, three ways: from the raw DEM, from the straight deck, and from **the ride's own
barometric profile** — which is what the rider actually climbed over that structure, and
therefore the reference the deck is answerable to. Registered: (a) deck − baro < 0 on
bridges (the deck erases real crown), (b) |deck − baro| < |raw − baro| overall (the
correction still helps more than it hurts), and (c) the bridge/tunnel split shows the deck
closer to the barometer on tunnels than on bridges. If (b) fails the deck is a net harm at
route grain and the letter says so; if (a) holds while (b) does, the honest prescription is
"correct portals, and expect a small residual under-charge on bridge-rich routes".

**Sanity gates (abort on failure).**

1. **PARITY** — the `own` arm IS paper 1's protocol, so it must reproduce the published
   *per-ride* Δ% from `longoes_frozen.csv` (D1) and `{censo,ppaz,jaam,danlessa}_comparison.csv`
   (D2–D5) for F3·ε_d, F4·ε_d, F3·ε_f, F4·ε_f and the simulation, to ≤ 0.02 pp. Far stricter
   than a median comparison; if it fails, nothing downstream is trustworthy.
2. **σ-equivalence** — the 1-D profile Gaussian at σ = 10 m must reproduce Entry 20's 2-D
   *raster* Gaussian at the same σ on the rides Entry 20 cached (median h₊ agreement within
   10%, p90 within 25%). *Falsifier:* if it fails, the letter cannot inherit Entry 20's σ
   prescription and must present the 1-D form on its own evidence.
3. **Conservation** — the simulation's energy identity ≤ 1e-6 relative on every arm.
4. **Re-gridding is inert** — every arm reports the same route length to float equality.

**Disclosed deviations.** (i) A 4-rides-per-corpus smoke run preceded this registration, to
wire the harness and prove the four sanity gates; its treatment numbers (n = 11) were seen.
The predictions above are anchored to Entries 6/19/20/38 arithmetic, not to that smoke, and
the smoke's own arms are not quoted anywhere. (ii) The wide raster replaces the validated
`sampa_geral.tif` crop of Entries 19–21; on their overlap the two agree to 0.01 m median, and
the only >10 m disagreements are where the *crop* runs off its own edge and reads 0 — but the
wide product's quality is not homogeneous, which is what G2/G3 exist for. (iii) FABDEM 1°×1°
tiles are fetched from the collective's own server; a 1° cell is the coarsest geographic
identifier there is, so no ride-derived geometry leaves the machine. (iv) A pre-filter drops
rides falling outside the largest WGS84 rectangle inscribed in the IGC raster's UTM footprint
before any sampling. It is inert — such rides have no IGC elevation at all and G2 would drop
them — and exists only so the FABDEM fetch does not pull tiles for Roraima, Lombardy and
Poland.

### Results (first full run, 2026-07-28 — 1,117 rides)

**Integrity.** All five sanity gates green: PARITY (the `own` arm reproduces the published
per-ride Δ% of `longoes_frozen.csv` and the four `*_comparison.csv` to ≤ 0.02 pp),
σ-equivalence (1-D profile vs Entry-20 2-D raster smoothing at σ = 10), conservation
(max relative residual 6.3e-8), re-gridding inertness (Δ route length exactly 0), and the
synthetic primitives check. Corpus funnel (candidates → sampled → primary): D1 44 → 29 → 22,
D2 70 → 68 → 60, D3 486 → 398 → 393, D4 223 → 203 → 197, D5 691 → 490 → 445. The wide raster
is what makes D1 possible at all — on Entries 19–21's validated crop its coverage is 0 of 44.
The largest single cut is `outside-raster` (170 rides: Roraima, Rio, Lombardy, Poland), then
Zwift (104) and G1 (36).

**Geometry — what each source does to the profile** (medians over the 1,117):

| arm | h₊ (m) | h₊ / h₊(own) | c(τ=2) m/km [95% CI] | ε_d |
|---|--:|--:|--:|--:|
| `own` barometer | 424 | 1.00 | **3.10 [3.01, 3.18]** | 0.439 |
| `igc5` local 5 m @5 m | 501 | 1.18 | 4.95 [4.89, 5.00] | 0.374 |
| `igc5s10` +σ=10 m | 443 | 1.04 | 3.74 [3.66, 3.81] | 0.389 |
| `igc5s30` +σ=30 m | 363 | 0.86 | 2.62 [2.56, 2.68] | 0.424 |
| `igc30` local 5 m @30 m | 446 | 1.05 | 3.77 [3.69, 3.83] | 0.384 |
| `fab5` FABDEM @5 m | 1002 | **2.36** | **10.14 [9.86, 10.59]** | 0.322 |
| `fab30` FABDEM @30 m | 731 | 1.72 | 7.52 [7.12, 7.76] | 0.348 |

The control's own rate lands at **3.10 m/km [3.01, 3.18]** — paper 1 measured 3.1 m/km on 44
rides; this is the same number on 25× the sample and a different physics protocol. Treat it
as an independent replication of §2.4's constant, not as a new result.

**The substitution cost** — F3 · ε_d, median |Δ%| [95% CI] · median signed Δ% [95% CI]:

| arm | D3+D4 · 590 | ALL · 1,117 |
|---|--:|--:|
| `own` | 3.2 [2.9, 3.4] · −2.0 [−2.4, −1.6] | 3.8 [3.6, 4.1] · −1.7 [−2.2, −1.3] |
| `igc5` | 3.6 [3.3, 3.9] · −0.9 [−1.5, −0.4] | 4.3 [4.0, 4.6] · +1.0 [+0.3, +1.7] |
| `igc5s10` | 3.5 [3.3, 3.9] · −1.3 [−1.7, −0.8] | 4.2 [4.0, 4.4] · −0.1 [−0.5, +0.4] |
| **`igc5s30`** | **3.4 [3.2, 3.8] · −1.9 [−2.2, −1.7]** | **4.0 [3.8, 4.2] · −1.7 [−1.9, −1.3]** |
| `igc30` | 3.5 [3.2, 3.8] · −1.3 [−1.6, −0.8] | 4.2 [4.0, 4.4] · +0.1 [−0.4, +0.5] |
| `fab5` | 4.0 [3.4, 4.7] · +3.6 [+2.8, +4.5] | 5.3 [4.6, 6.0] · +4.3 [+3.6, +4.9] |
| `fab30` | 3.4 [3.2, 4.0] · +1.6 [+0.8, +2.6] | 4.6 [4.1, 4.9] · +2.0 [+1.5, +2.7] |

The pooled column is not five independent replications — D1 ⊂ D5 and most of D2 is the
author's own recordings re-scored as a generic rider (paper 1 §2.3.4 after renumbering), so paper 1 excludes D2
from its pool. D3+D4 is the clean transfer column. Because every arm is scored on the
identical ride set, the *paired* arm-vs-control statistics are unaffected by the overlap;
only the absolute pooled level inherits it.

Per corpus (med |Δ%| · bias), `own` → `igc5` → `igc5s30`: D1 7.5·+1.7 → 21.8·+21.8 → 8.0·+8.0;
D2 3.4·+0.3 → 8.1·+7.0 → 5.1·+1.2; D3 3.1·−1.2 → 4.0·+0.6 → 3.6·−1.7; D4 3.4·−2.8 →
2.8·−2.1 → 3.3·−2.3; D5 4.9·−1.7 → 5.3·+3.1 → 4.7·−1.2.

**P1 — direction confirmed universally, magnitude refuted on the registered pool.** The raw
fine DEM over-charges on every corpus (bias shift +0.7 to +20.1 pp) and on **940 of 1,117
rides** paired (median +2.68 pp). But the registered window was +3 to +10 pp on D3+D4, and
the observed shift there is **+1.1 pp** (−2.0 → −0.9); pooled over all five it is +2.7 pp.
The prediction was arithmetic from Entry 6's k_DEM = 1.26 — which was measured on *hilly
longões*, and that is exactly where it lands: D1's shift is +20.1 pp. The transfer riders ride
graded open roads, where the survey and the barometer nearly agree. **The over-charge is
terrain-dependent**, which is Entry 21's refined hypothesis (constants are functions of
(Δx, terrain-roughness regime), not of Δx alone) arriving from the energy side.

**P2 — CONFIRMED, and by more than registered.** At σ = 30 m the law returns to the control:
med |Δ%| 3.4 vs 3.2 on D3+D4 (**0.2 pp**, registered ≤ 2) and 4.0 vs 3.8 pooled, with bias
−1.9 vs −2.0 and −1.7 vs −1.7 — the control's own bias reproduced to a tenth of a point.
Nothing was re-fitted to achieve it: σ is Entry 20's lever, moved from the raster to the
profile. The letter's headline is therefore not "DEMs are bad" but **"one smoothing scale,
applied to the sampled profile, buys the barometer's behaviour."**

**P3 — (a) CONFIRMED decisively, (b) REFUTED as stated.** Every DEM source's noise rate sits
far outside the barometric CI: `igc5` 4.95 [4.89, 5.00] (registered > 4.5), `fab5` 10.14
[9.86, 10.59] (registered > 6.0). So paper 1's frozen c = 3 m/km is a property of *consumer
barometric recordings at 5 m resampling*, not of routes. Substituting each arm's own median c
in F4 rescues the catastrophic case — `fab5`'s bias falls from **+19.2 to +0.9** — but does
not land within 2 pp of F3's bias on the same arm, and on the low-noise arms it *overshoots*
negative (`igc5` +2.4 → −2.0; `fab30` +7.4 → −3.9). The mechanism is structural: F4 scales
climb *and* refund by one factor (1 − c·x/h₊), so at large c it over-corrects the descent
side, which F3's deadband handles separately. Practical rule: with the profile in hand use
F3's deadband; F4 with a per-source c is a rescue for totals-only inputs, not a substitute.

**P4 — the artifact tail, confirmed on both operationalizations.** (a) On the 745 anomaly-free
crops the coarse source improves markedly — `fab5` 5.3 → **3.4** med |Δ%| (−1.9 pp, registered
≥ 1) and `fab30` 4.6 → 3.6 — while the fine local survey barely moves (`igc5` 4.3 → 3.8,
−0.5 pp, below the registered threshold). Strikingly, on clean crops FABDEM (3.4) *beats* the
barometric control (3.7): the anomaly filter removes precisely the rides where a 30 m product
misreads. (b) Portal exposure, joined from Entry 26 on the 877 rides where that population
overlaps: the top decile (≥ 71.2 span-metres per route-km) carries a DEM-minus-control
residual of **+5.39 pp against the rest's +1.50 pp** — a 3.89 pp difference, well past the
registered ≥ 1 pp. Bridges and tunnels are a real and separable part of the substitution cost.

**The physics protocol earned its amendment.** F3 · ε_d, frozen priors → regime-consistent,
med |Δ%| (bias): `own` 5.6 (+0.3) → 3.8 (−1.7); `igc5` 6.1 (+3.3) → 4.3 (+1.0); `fab5` 7.8
(+6.4) → 5.3 (+4.3). Every arm improves by ≈ 1.8 pp of median error, so the source effect is
read against a much smaller residual. The amendment's stated purpose is visible in the smoke
that preceded it, where at the frozen priors FABDEM appeared *more accurate than the ride's
own barometer* purely because its over-charge offset a standing under-prediction.

**Verdict.** The law survives the elevation-source swap far better than the ascent-inflation
literature would suggest, and the surviving error is prescriptive rather than diffuse. On the
local 5 m survey the swap costs 0.5 pp of median accuracy and a +2.7 pp bias swing, both
removed by a σ = 30 m smoothing of the sampled profile. On the free global 30 m product the
swap costs 1.5 pp and +6.0 pp of bias when the polyline is sampled at 5 m steps; sampling it
at 30 m halves that, and using FABDEM's own c = 10.1 m/km instead of the frozen 3 turns F4
from unusable (+19.2% bias) into serviceable (+0.9%). Two scope limits are load-bearing:
the penalty is terrain-dependent (D1's brevets pay 20 pp where D3/D4 pay 1), and portal-rich
routes are a separable tail worth its own handling.

### Extension results — the portal correction (2026-07-28, second full run)

**Coverage.** 950 of the 1,117 primary rides have their OSM tiles already cached, and 943 of
those carry at least one matched span (median 1,350 m of deck over 18 spans per ride). The
167 uncovered rides are mostly D1's brevets, outside Entry 26's footprint; no Overpass
request was issued.

**P6 — CONFIRMED on all three parts: the straight deck over-corrects, and it is the bridges.**
Ascent accumulated *inside* the matched spans, median metres per ride, against the ride's own
barometer as the truth for what was climbed over the structure (19.5 m):

| source | raw | straight deck | deck − baro [95% CI] | raw − baro [95% CI] |
|---|--:|--:|--:|--:|
| `igc5` | 43.6 | 11.4 | **−2.79 [−3.52, −2.08]** | +13.27 [+10.00, +19.67] |
| `igc5s30` | 24.9 | 7.0 | −5.84 [−7.89, −4.51] | **+0.05 [−0.29, +0.28]** |
| `fab5` | 33.1 | 7.7 | −6.57 [−7.61, −5.46] | +11.17 [+10.16, +12.55] |
| `fab30` | 25.0 | 7.3 | −6.78 [−8.04, −5.81] | +4.98 [+4.25, +5.83] |

(a) **deck − baro < 0**, CI clear of zero on every arm: the deck removes more than the DEM
invented. (b) **|deck − baro| ≪ |raw − baro|** on the raw sources (2.8 against 13.3 on
`igc5`): the correction still removes about four-fifths of the spurious ascent, so it helps
far more than it hurts. (c) The **bridge/tunnel split carries the whole effect and matches
the mechanism exactly**: on bridges `igc5`'s deck − baro is −2.43 [−3.26, −1.68] m against
tunnels' −0.29 [−0.40, −0.20] — eight times the over-correction, with disjoint CIs. A road
bridge carries a vertical curve the rider climbs and the straight line erases; a tunnel's
roadway really is close to a chord under the DTM's ridge, so there the correction is nearly
all signal. Danilo's prediction, made before the run, is right in sign, in magnitude, and in
its attribution to bridges.

**The finding that changes the recipe: the two repairs do NOT stack.** On the σ = 30 m arm
the raw profile's in-span ascent already matches the barometer — **+0.05 m [−0.29, +0.28]**,
a CI straddling zero. Smoothing has *already* removed the portal artifact, because a valley
a bridge spans is exactly the kind of sub-30 m feature the Gaussian flattens. Applying the
deck on top then subtracts a second time, and the energy gets significantly **worse**:
3.81 (−2.07) → 3.87 (−2.37) med |Δ%|, corrected closer on only 400 of 935 rides,
p < 10⁻⁴. Correct portals **or** pre-smooth — not both.

**Energy effect** (F3 · ε_d, regime-consistent physics, the 943 touched rides; the control
reads 3.72 [3.47, 4.03] · −2.10 [−2.48, −1.61] on this subset):

| arm | raw | portal-corrected | corrected closer | p |
|---|--:|--:|--:|--:|
| `igc5` | 3.92 · −0.29 | **3.73 · −1.29** | 501/943 | 0.059 |
| `igc5s10` | 3.92 · −0.95 | 3.81 · −1.62 | 458/942 | 0.42 |
| `igc5s30` | 3.81 · −2.07 | 3.87 · −2.37 | 400/935 | **< 10⁻⁴ (worse)** |
| `igc30` | 3.89 · −0.87 | 3.82 · −1.54 | 466/940 | 0.82 |
| `fab5` | 3.91 · +2.71 | **3.68 · +2.39** | 644/942 | **< 10⁻⁴** |
| `fab30` | 3.66 · +0.75 | **3.59 · +0.53** | 613/938 | **< 10⁻⁴** |

Read against the control: correcting portals moves the raw fine survey from 3.92 (−0.29) to
3.73 (−1.29) — onto the barometer on both axes (3.72, −2.10). The per-ride paired test is
only marginal there (p = 0.059), so the honest statement is that the *bias* moves a full
point toward the control while the *scatter* gain is within noise. On the coarse global
source both move significantly. On the smoothed arm it is a net harm.

**Verdict.** The portal correction is worth applying to a raw DEM profile and worth skipping
after pre-smoothing. Its residual is a known-sign under-charge concentrated on bridges —
about 2.4 m of erased crown per touched ride on the fine survey — which a future refinement
could recover by fitting a vertical curve rather than a chord, but which at route grain costs
under half a percent of ride energy and is dwarfed by the +13 m it removes.

*Deviations, disclosed:* the deck runs between the arm's own profile heights at the projected
abutments rather than Entry 26's raster heights at the abutment nodes; the treatment is
offline-only, so it is restricted to Entry 26's cached OSM footprint and D1 is largely absent;
closed forms only, no simulation. The extension was registered (P5, P6) before its run, after
the main results above were already in hand — the two runs are reported separately for that
reason.

Instrument: [`e41_dem_route.py`](../../src/harness/e41_dem_route.py) (`E41_SMOKE=n`); output
`e41_dem_route.csv` (1,189 rides written, 1,117 in the primary population). The per-arm
medians, their CIs, the per-source noise rates, the h₊ ratios and the paired substitution
costs are gated in `bootstrap_ci.py`.

---

## 2026-07-28 — Entry 40: roller recycling — the covariate test

**Lineage** — $I$: $(D_1..D_5, P_{f,r})$ · $T$: roller covariate · $O$: `e40_roller.csv` (1,409) · $S$: roller recycling

*Prompt (Danilo): "Let's test that" — Entry 37's registered roller-drop-share covariate
against the form-3 residual.*

### Pre-registration (written before any result was seen)

**The claim under test.** Rollers that survive the deadband but sit within the momentum
budget — amplitude between τ = 2 m and h_KE = v²/2g — and are closely spaced (within the
dissipation length λ) are partially paid by momentum. Form 3 charges them in full, so rides
rich in such terrain should be *over-predicted* (positive signed Δ%), and the effect should
be invisible to ε_bal (the recycling lands on the next rise's ledger line, not the
descent's).

**The covariate** ([`e40_roller.py`](../../src/harness/e40_roller.py)). Per ride, on the
τ = 2 m deadbanded profile (form 3's own terrain), decompose into monotone runs
(rise / flat / drop). For each drop of amplitude A_d followed — after a flat gap g — by a
rise of amplitude A_r, the recyclable drop is

$$\mathrm{rec}_i = \min(A_d,\ A_r,\ h_{KE})\cdot e^{-g_i/\lambda}$$

with h_KE = v_meas²/2G (the ride's measured flat speed) and λ = m/(ρ·ĈdA_reg) (the ride's
regime-consistent physics; both joined from `e35_residual.csv`) — the Entry-37 dissipation
law as the spacing weight, no free parameter. The regressor is the **recyclable energy
share**, RES = 100·β·Σ recᵢ / E_meas — the percentage of the ride's energy sitting in
momentum-payable form. With that normalisation the OLS slope of Δ% on RES estimates the
transfer efficiency η directly.

**Residuals**: form 3 · ε_d at the regime-consistent physics (`f3_d_reg`, Entry 35 — the
near-zero-bias protocol, same deconfounding logic as Entry 39), frozen-protocol residuals
as reference. P3's ledger check uses Entry 36's measured gap (δ = ε_coast − ε_bal, regime
physics, real-descent subset).

**Registered predictions.**

- **P1 (sign and size):** within-corpus OLS slope of Δ% on RES is positive on D3–D5, with
  η̂ ∈ (0.2, 1.0] (bootstrap CI; rides resampled).
- **P2 (rank):** Spearman ρ(RES, Δ%) > 0 on D1 and D3–D5. D2 is expected weak (urban
  profiles carry little recyclable drop; also its composite α).
- **P3 (the ledger line):** ρ(RES, δ) shows no comparable positive relation on the
  real-descent subset — recycling must be invisible to the descent balance, per the
  Entry-37 bookkeeping argument. A strong positive ρ here would *falsify the mechanism's
  claimed ledger line* even if P1 holds.
- **Failure mode:** no positive RES–Δ% relation anywhere ⇒ momentum recycling is
  sub-resolution at ride grain; the suspension reading stays interpretive; no correction
  term is added.

### Results (first full run, 2026-07-28 — 1,409 rides)

| corpus | RES median (% of E) | rollers/ride | ρ(RES, Δ%) | regression coeff. η̂ [CI] | ρ(RES, δ) — P3 |
|---|--:|--:|--:|--:|--:|
| D1 | 0.48 | 52 | **+0.444** | 10.6 [3.8, 17.1] | −0.06 (n = 22) ✓ null |
| D2 | 0.44 | 19 | +0.125 | 21.1 [0.3, 114.9] | +0.04 (n = 27) ✓ null |
| D3 | 0.23 | 19 | **+0.204** | 1.5 [0.2, 2.9] | **+0.198 (n = 157)** ✗ |
| D4 | 0.03 | 9 | **+0.429** | 9.3 [4.9, 16.1] | −0.30 (n = 20) |
| D5 | 0.46 | 16 | **+0.394** | 17.6 [13.3, 25.5] | **+0.240 (n = 226)** ✗ |

**P2 (direction): CONFIRMED, universally.** ρ(RES, Δ%) is positive on all five corpora —
at these sample sizes, overwhelmingly so on D1/D3/D4/D5. Roller-rich rides ARE
systematically over-predicted by form 3. The terrain signal is real.

**P1 (mechanism scale): REFUTED.** The physical ceiling for direct recycling is η = 1 (a
Joule cannot be over-charged more than once), and the registered window was (0.2, 1.0].
Observed regression coefficients (the cross-ride OLS coefficient of Δ% on RES — a
statistic, not a terrain grade): 1.5–21, an order of magnitude above the ceiling everywhere except D3
(whose CI [0.2, 2.9] merely grazes the window). Whatever drives the over-prediction of
roller terrain carries 10–20× more energy than the momentum-payable amount RES measures.

**P3 (the ledger falsifier): FIRES on the two big corpora.** RES correlates positively
with the measured deficit δ on D3 (+0.198, n = 157) and D5 (+0.240, n = 226) — if RES were
measuring recycling, δ had to stay blind to it. It doesn't. Together with P1's unphysical
slopes, the attribution is settled: **RES is a proxy for roller-terrain character, not a
measurement of momentum recycling.** (The δ link itself is coherent with Entry 34: roller
descents are gentle, gentle grades have high pedalling occupancy, high occupancy = high δ.)

**Verdict and synthesis.** The registered failure mode lands in its sharpened form:
momentum recycling is *sub-resolution at ride grain* — RES medians of 0.03–0.5% of E mean
that even at η = 1 the mechanism could move ride medians by half a point at most, and the
robust roller-terrain over-prediction the test surfaced (P2) must therefore be driven by
something an order of magnitude larger. The prime suspect ties the day's threads together:
**the τ = 2 m deadband under-filters roller terrain** — oscillations above τ that survive
into h̃± carry noise and momentum-payable relief the law charges in full, which is the same
under-filtering that Entry 39's clean corpus (D4: τ* = 3.5) diagnosed from the other side.
No correction term is added; the roller over-prediction is recorded as a real, unattributed
route-geometry effect, with the speed/terrain-dependent deadband as the registered joint
suspect for both entries. The suspension interpretation (Entry 37) survives as mechanics —
its ride-level energetic footprint is simply too small to matter, which is itself now a
measured fact.

Instrument: [`e40_roller.py`](../../src/harness/e40_roller.py) (`E40_SMOKE=1`); output
`e40_roller.csv` (1,409 rides).

---

## 2026-07-28 — Entry 39: the deconfounded τ-sweep — momentum vs measurement, with the bias fog lifted

**Lineage** — $I$: $(D_1..D_5, P_{f,r})$ · $T$: deconfounded $\tau$-sweep · $O$: `e39_tau_reg.csv` (1,409) · $S$: momentum vs measurement

*Prompt (Danilo), on Entry 38's confound: "can we use the per-ride physics inversion
protocol?"*

### Pre-registration (written before any result was seen)

**Design.** Entry 38's sweep re-run with ONE change: physics per ride = the
regime-consistent set of Entry 35 arm B (m̂, Ĉrr, ĈdA_reg, wind, joined from
`e35_residual.csv`; fallbacks flagged) — chosen over Entry 33's segment-aero inversion
because only the regime-consistent pair has near-zero standing biases (≈ +0.1 / +1.4 /
−1.3 / −2.7 / −0.5 on D1–D5 at τ = 2), which is the whole point: Entry 38 showed
argmin-|Δ%| reads *bias compensation* when the model carries a standing bias, so the
momentum scale is only visible when the bias fog is lifted. Primary variant: **ε_d on every
corpus including D2** — at the regime-consistent α the honest pair is (α, ε_d) everywhere
(Entry 35's D2: 4.6 vs ε_f's 8.0), a registered deviation from Entry 38's regime rule,
owned by the pairing logic. Everything else identical: τ ∈ {0.5 … 6.0, 0.5}, same
populations, same statistics, τ* CI at B = 1,000, c(τ) reported.

**Registered predictions.**

- **P1 (the ordering, now visible):** τ*(D3) ≈ τ*(D4) > τ*(D1) ≈ τ*(D5) > τ*(D2), with
  η = 1 targets 3.2 / 3.1 / 2.05 / 1.75 / 0.87 m.
- **P2 (paired):** τ = 3.0 beats τ = 2.0 on a per-ride majority on D3 and D4; the reverse
  on D5 and D2.
- **P3 (coherence):** with biases ≈ 0, the bias-zero crossing and τ* should roughly
  coincide per corpus (they were decoupled in Entry 38 — that was the confound's
  signature).
- **Failure mode:** if τ* is still not ordered by v_f²/2g *with the bias fog lifted*, the
  momentum-filter reading of τ is refuted properly (not merely as-tested): the deadband
  stays measurement hygiene at a universal 2 m, and Entry 37's suspension mechanics remain
  physics without a fitted parameter to show for it. D4's residual −2.7 bias is the one
  known remaining contaminant; its τ* gets read with that caveat.

### Results (first full run, 2026-07-28 — 1,409 rides; all four τ = 2.0 parity gates vs the Entry-35 regime column GREEN)

| corpus | τ* [CI] | h_KE target | target in CI? | bias slope over grid | bias-zero |
|---|--:|--:|--:|--:|--:|
| D1 | 3.5 [0.5, 6.0] | 2.05 | yes (CI vacuous) | +3.3 → −3.3 | ≈ 2.2 |
| D2 | 2.5 [1.5, 3.0] | 0.87 | **no** | +8.2 → −5.4 (steepest) | 2.5 |
| D3 | 1.5 [1.5, 4.5] | 3.24 | yes | −0.5 → −2.9 | < 0.5 |
| D4 | **3.5 [3.0, 5.0]** | **3.10** | **yes — dead on** | −2.8 → −3.0 (**flat**) | none |
| D5 | 1.0 [0.5, 2.0] | 1.75 | yes (edge) | +1.9 → −4.3 | ≈ 1.45 |

**The confound mechanism is now demonstrated in both directions.** P. Paz's τ* moved 4.5 →
1.5 between Entries 38 and 39 — his standing bias flipped from +4.3 (frozen) to −1.3
(regime), and τ* followed the bias's sign exactly as the Entry-38 diagnosis predicted. D2's
τ* sits precisely on its bias-zero (2.5 = 2.5): with the steepest bias slope on the grid,
its optimum is pure bias compensation and its h_KE target (0.87) is unreadable — the
composite total-loss α makes urban a non-test. **So the informative corpora are the ones
where bias is flat or near zero in τ — and there the momentum reading scores its best
evidence yet:**

- **D4 (JAAM) is the clean read and it lands dead on target.** His bias barely moves across
  the whole grid (−2.8 → −3.0: nothing for τ* to compensate), his basin has genuine shape,
  and τ* = 3.5 [3.0, 5.0] against h_KE(28.1 km/h) = 3.10 m. Between Entries 38 and 39 his
  optimum moved from the grid floor to exactly his momentum target the moment the bias fog
  lifted. The paired test is the single strongest pro-momentum statistic in the project:
  **τ = 3.0 beats τ = 2.0 on 137/215 rides, p = 0.0001** (P2 confirmed, significant).
- **D5 (author, near-zero bias at small τ)**: τ* = 1.0 [0.5, 2.0] with bias-zero at ≈ 1.45,
  bracketing the 1.75 target from below; paired test significantly *for* τ = 2 over 3
  (p = 0.0068) — P2's predicted direction, confirmed.
- **D3 remains bias-dragged** (−1.3 standing, slope −0.5 → −2.9): τ* = 1.5 and the paired
  test significantly favours 2 over 3 (p = 0.0084), against P2's call — but its CI still
  contains the 3.24 target, i.e. the corpus is uninformative rather than opposed.

**Verdicts.** P1 (clean v_f²/2g ordering): NOT confirmed — τ* still tracks residual bias
wherever bias has τ-slope; 4 of 5 CIs contain their targets but only D4 constitutes
evidence. P2: 2 of 4 calls confirmed with significance (D4, D5), one significant miss (D3,
bias-dragged), one non-test (D2). P3 (τ* ≈ bias-zero when biases are small): holds on
D2/D5, fails on D1 (n = 44, vacuous CI) — the coherence check works exactly where it has
power. **Overall: the momentum-filter reading is upgraded from "refuted as tested"
(Entry 38) to "supported on the corpora that can see it"** — the fast heavy rider's
deadband wants to be ≈ 3–3.5 m exactly as v²/2g predicts, the slow rider's wants ≈ 1–2 m,
and every deviation from the pattern is accounted for by the measured τ-slope of the
standing bias. Not a law yet: one clean corpus is one data point.

**Deployment verdict: τ = 2 m stays.** Every basin is flat within CIs near its optimum
(max available gain ≈ 0.2–0.4 pp, in-sample); the case for per-rider τ is scientific, not
practical — for now. The registered next step if this thread continues: per-rider τ tied to
v_f²/2g *as a prediction* on a new rider's data, not a fit.

Instrument: [`e39_tau_reg.py`](../../src/harness/e39_tau_reg.py) (`E39_SMOKE=1`); output
`e39_tau_reg.csv` (1,409 rides). c(τ) is physics-free and reproduces Entry 38's values.

---

## 2026-07-28 — Entry 38: the τ-sweep — does the optimal deadband track v_f²/2g?

**Lineage** — $I$: $(D_1..D_5, P_{f,r})$ · $T$: deadband $\tau$-sweep · $O$: `e38_tau.csv` (1,409) · $S$: $\tau^*$ vs $v_f^2/2g$

*Prompt (Danilo), on Entry 37's registered test: "let's do it."*

### Pre-registration (written before any result was seen)

**Question.** Entry 37 observed the fitted deadband τ = 2 m ≈ h_KE(author's flat speed) and
predicted the momentum-filter reading: τ* ≈ η·v_f²/2g per rider. Test: sweep τ per corpus
and read the optimum.

**Protocol** ([`e38_tau.py`](../../src/harness/e38_tau.py)). Corpora D1–D5, populations as
Entries 33/35. Physics: the frozen shared-constants protocol (per-corpus anchor mass, logged
on D1; C_rr 0.008 / C_dA 0.40 / ρ 1.13 / k_eff 0.98 / wind 0) — deliberately Table 3's
protocol, so the τ = 2.0 column must reproduce the published per-corpus medians end-to-end
(a built-in parity gate). Model: form 3 (split + deadband at τ), both ε variants — ε_d
(unclamped, eps_geom on the raw profile: τ-independent by construction) and ε_f = 0.20 —
with ε_d primary on D1/D3–D5 and ε_f primary on D2 (the regime rule). τ grid: 0.5–6.0 m,
step 0.5. Statistics: per corpus and τ, med|Δ%| and bias with the standard seeded bootstrap;
τ* = argmin over the grid of med|Δ%| (primary variant), with a bootstrap CI on τ* (rides
resampled, argmin recomputed; B = 1,000, disclosed as smaller than the 10⁴ convention for
stdlib-runtime reasons). Corpus h_KE targets from each corpus's median measured flat speed.

**Registered predictions.**

- **P1 (ordering):** τ*(D3) ≈ τ*(D4) > τ*(D1) ≈ τ*(D5) > τ*(D2); with η = 1 the point
  targets are ≈ 3.2 / 3.1 / 1.9 / 1.8 / 0.9 m.
- **P2 (paired form, robust to the shallow basin):** on D3 and D4, form 3 · ε_d at τ = 3.0
  beats τ = 2.0 on a majority of rides (exact sign test); on D5 the reverse. (Entry 5 found
  a broad basin on D1 — the discriminating statistic is the cross-corpus *order* of τ*, not
  sharp point estimates.)
- **P3 (the scalar follows):** the ascent-noise rate c(τ) at each corpus's τ* replaces
  3 m/km accordingly (reported; form 4's constant inherits any τ change).
- **Failure mode:** τ* flat or identical across riders ⇒ Entry 37's τ ≈ h_KE(v_f) match on
  the author's corpus is numerology; the universal τ = 2 m stays and the momentum-filter
  reading is dropped.

### Results (first full run, 2026-07-28 — 1,409 rides)

**Parity first.** The τ = 2.0 column reproduces Table 3 exactly on D3 (5.75 vs 5.8) and D4
(5.49 vs 5.5) — identical populations — and misses on D2 (5.71 vs 4.7*) and D5 (6.35 vs
6.2), the two corpora where this harness's population differs from the published clean one
(69 vs 62, 636 vs 621; the same disclosed difference as Entries 33/35). The machinery is
sound; the comparison basis shifts with the population.

**The sweep** (τ* = argmin med|Δ%| of the regime-appropriate variant, B = 1,000 CI on τ*):

| corpus | τ* [CI] | h_KE target (η = 1) | bias at τ = 2 | bias-zero crossing |
|---|--:|--:|--:|--:|
| D1 | 1.0 [0.5, 6.0] | 2.05 | +2.2 | ≈ 3.0 m |
| D2 | 1.5 [1.0, 2.5] | 0.87 | −0.1 (ε_f) | ≈ 2.0 m |
| D3 | 4.5 [1.0, 6.0] | 3.24 | +4.3 | none on grid (still +2.8 at 6.0) |
| D4 | 1.0 [0.5, 3.0] | 3.10 | −4.7 | none (−4.4 already at 0.5) |
| D5 | 0.5 [0.5, 2.5] | 1.75 | +0.1 | ≈ 2.1 m |

**P1 (ordering): REFUTED.** D4 breaks it decisively — JAAM cruises at 28 km/h (target
3.1 m) but his optimum sits at the grid floor. **P2 (paired τ = 3 vs 2): REFUTED** — D3
trends the predicted way but p = 0.20; D4 is *significant in the opposite direction*
(92/215, p = 0.04); D5 trends as predicted, p = 0.10. Per the registered failure mode:
**the universal τ = 2 m stays, and the momentum-filter reading of τ loses this test.**

**The confound, named — this is Entry 29's lesson at the τ dial.** Under the frozen
protocol the corpora carry standing biases of ±4–5 pp, and argmin-|Δ%| moves τ to *cancel
the bias*, not to find the filter scale: P. Paz's +4.3 standing bias drags his τ* to 4.5
(more smoothing removes more h₊, offsetting the overcharge); JAAM's −4.7 drags his to the
floor (any ascent removal deepens his undercharge); the two near-unbiased corpora (D1, D5 —
same rider) put the bias-zero crossing at 3.0 and 2.1 m, bracketing the fitted 2 m but not
scaling as v_f² (same rider, two values). So the test as registered *cannot see* the
momentum scale through the bias fog — the evidence is weakly against, not decisive. A
deconfounded version — the same sweep at the regime-consistent physics of Entry 35, where
the standing biases are ≈ 0 — is the natural follow-up, noted but NOT registered here.

**P3 — the noise rate travels with the corpus, not just with τ.** c(τ = 2) reads 3.1 (D1,
the gated value), 4.5 (D2), 2.5 (D3), 2.6 (D4), 3.7 (D5) m/km — device and terrain move it
by ±1.5 m/km around the calibrated 3. Form 4's scalar is a D1 fact that happens to sit
mid-range; worth remembering when the law is deployed against other recording chains.

**What survives.** Entry 37's suspension interpretation is untouched as *mechanism* (the
KE arithmetic and the dissipation length stand on their own); what failed is the specific
claim that the energy-error-optimal deadband tracks it, tested through a biased criterion.
Deployment keeps τ = 2 m; the paper's smoothing story stays measurement-first; the
suspension reading stays a registered interpretation awaiting a deconfounded test.

Instrument: [`e38_tau.py`](../../src/harness/e38_tau.py) (`E38_SMOKE=1`); output
`e38_tau.csv` (1,409 rides × 12 τ × both ε variants + c(τ)).

---

## 2026-07-28 — Entry 37: the KE-equivalent height — momentum under rollers (hypothesis note, no run)

**Lineage** — $I$: — · $T$: hypothesis note · $O$: no run · $S$: KE-equivalent height

*Prompt (Danilo): "On hilly terrain, esp. closely spaced hills together, we would expect the
descent inertia to play a role when going over the next hill. For a 75 kg rider at speeds of
25, 30, 35 and 40 km/h, the kinetic energy would be equivalent to the gravitational potential
of 2.4 m, 3.5 m, 4.8 m and 6.3 m. Note that only a part of it would actually be transferred
[…] a substantial part of the kinetic energy gets dissipated on the intermediate flat
section. This is somewhat captured by the deadband filter. The larger the amount of short
hills (and close spacing between them / smaller the flat section), the more we would expect
epsilon to play a role."*

The numbers verify exactly (h_KE = v²/2g at G = 9.7864: 2.46 / 3.55 / 4.83 / 6.31 m), and
two quantitative consequences fall out immediately.

**1. The deadband may literally be the momentum filter.** The fitted τ = 2 m (Entry 5, on
the author's corpus) sits at the KE-equivalent height of the author's measured flat speed:
h_KE(21.2 km/h) = 1.77 m ≈ τ. A bump smaller than h_KE(v) is paid by momentum and repaid on
its far side — energetically it *is* flat ground, which is exactly what the deadband encodes.
If this identification is right, τ is not a universal constant but a **speed-dependent**
one, τ ≈ η·v_f²/2g (η ≤ 1 the transfer efficiency): P. Paz and JAAM cruise at ≈ 28 km/h, so
their momentum filter should sit near **3.1–3.2 m**, not 2 m. Registered test (future run):
sweep τ per corpus (the Entry-5 protocol on D3–D5) and check whether the med|Δ%|-minimising
τ tracks v_f²/2g across riders. If yes, the deployed constant τ = 2 m under-filters fast
riders — and c ≈ 3 m/km (form 4's scalar) inherits the same speed dependence.

**2. "Close spacing" has a physical scale, and it is speed-independent.** Excess KE above
the equilibrium speed decays over a flat with characteristic length **λ = m/(ρ·C_dA)** (pure
quadratic drag; rolling adds a slow linear drain): ≈ 220 m for the author (C_dA ≈ 0.30),
≈ 170 m at the frozen prior, ≈ 230 m for JAAM (heavier — heavier riders coast farther).
So hills within ≈ 200 m of each other recycle descent KE into the next rise; flats beyond
≈ 2–3 λ (500–700 m) dissipate most of it. Danilo's "smaller the flat section" clause,
quantified.

**λ, made precise** *(Danilo: "I suspect that the characteristic length should include Crr
and wind speed too. Can we have an interpretation of it?")*. On a windless flat the coasting
equation is linear in v²: writing q = v², coasting gives dq/dx = −q/λ − 2C_rr·G, so

$$q(x) + q_c = (q_0 + q_c)\,e^{-x/\lambda}, \qquad \lambda = \frac{m}{\rho C_dA}\ \text{(exact)}, \qquad q_c = \frac{2 C_{rr}\,m g}{\rho C_dA}.$$

Three readings, numerically verified (75 kg, C_dA 0.31): (i) **C_rr does not enter the
length** — exactly, not approximately: it sets the *floor* q_c (≈ 20.8 km/h equivalent)
toward which v² relaxes, which is why it shortens the coast *window* (35 → 25 km/h takes
only ≈ 96 m ≈ 0.45 λ) without touching λ = 214 m. In the recycling *ledger* the
cancellation is structural: rolling costs the same per metre at any speed, so the coasting
rider pays no more rolling than the pedalling counterfactual would — rolling never counts
as excess dissipation. (ii) **Wind rescales the excess-decay length** by the air/ground
speed ratio: linearised, λ_w ≈ m·v/(ρC_dA·(v+w)) — a +7 km/h headwind at 25 km/h shortens
214 → 167 m, a tailwind stretches it to 297 m. (iii) **The interpretation sentence**: after
coasting one λ, 63% of the v²-excess above the rolling floor has been shed; after 2λ, 86% —
independent of C_rr, with wind acting only through the λ rescaling.

**Where the effect should show — and where it should NOT.** Rollers with amplitude between
τ = 2 m and h_KE(v) (≈ 2–6 m) are charged full β·h± by form 3 but are partially
momentum-paid in reality, so the *form-3 signed residual* should trend positive
(over-prediction) with a ride's share of drop in such rollers spaced ≲ λ apart. Crucially,
this should NOT appear in ε_bal: the balance books only descent-cell pedal energy, and on
rollers the recycled KE surfaces as *cheaper pedalling on the following rise* — a different
ledger line (this reconciles the §3.2 boundary finding that measured ε_bal → 0 on gentle
terrain even though the energy is demonstrably being recycled). So the registered covariate
is roller-drop share vs form-3 residual, NOT vs ε_bal — and it joins Entry 34's untested
route-side candidates with a mechanism and a scale attached.

Edge-cost consequence (paper 3, edge-cost — renumbered same day when the DEM letter took the paper-2 slot): momentum is **non-local** — no per-edge cost can carry KE
across edges, so any edge realisation over-charges closely-spaced rollers by construction;
λ ≈ 200 m and h_KE ≈ 2–6 m bound the error's scale and the raster smoothing that would
absorb it. Registered as a pitfall in the edge-cost scaffold (paper 3).

**Interpretation addendum (same day, Danilo): momentum acts as a smoother.** "The scale of
smoothing is determined not only by the physical geometry, but by its interaction with the
host movement." This reframes what the deadband *is*. The paper currently justifies
smoothing as measurement hygiene (§2.4: sub-metre jitter is sensor noise accumulating at
3.1 m/km — the profile is *wrong* and the filter repairs it). The momentum reading adds a
second, independent justification: even on a perfectly measured profile, micro-relief below
h_KE should not be charged, because the rider's inertia carries it — the *cost function* is
wrong on a correct profile, and the filter repairs that instead. The fitted τ = 2 m serves
both masters, and they happen to coincide at the calibration rider's cruising speed — which
may be exactly why one constant worked so well. Three consequences:

1. **Smoothing is rider-relative, not absolute.** The same profile at different speeds is
   effectively different terrain; "the calibration scale" of §2.4/§4.4 is not a property of
   the DEM alone but of the rider–terrain interaction. Two constants that the project has
   treated as elevation-pipeline facts (τ, and through it c) are partly *dynamics* facts.
2. **The deadband's functional form fits the mechanism — and the mechanism is a
   suspension** *(Danilo's sharpening: "or more precisely, as a suspension, or spring. The
   hills are the bumps on a larger scale")*. The rider–terrain system is literally a
   spring–damper: the KE ↔ PE exchange over a roller is the spring (conservative — energy
   stored on the rise, returned on the far side), drag along the traverse is the damper
   (dissipation length λ ≈ m/ρC_dA), and **h_KE is the suspension's travel** — bumps within
   it are absorbed and returned, bumps beyond it *bottom out* and transmit the load to the
   chassis, i.e. the legs pay β·dh. The bicycle already carries this cascade at smaller
   scales (tyre: mm; fork: cm); momentum is the next stage up (metres), and hills are simply
   the bumps at that stage's scale. An amplitude-threshold filter with distance-bounded
   memory — exactly what `deadband(τ)` implements — is the transfer function of a
   travel-limited suspension: the mechanism did not need a new filter family, it needed a
   new reading of the existing one's parameter (τ = travel = η·v_f²/2g; damping = λ).
3. **Fixed-scale deployment bakes in one speed.** A raster pre-smoothed at a single σ
   (the edge-cost paper's mitigation for the 5 m/30 m problem) encodes one rider speed; the momentum
   reading says the right smoothing varies with v_f — across riders, and even within one
   ride between regimes.

Entry 38's τ-sweep is the discriminating test between the two readings: pure measurement
noise predicts one universal τ (the noise process is rider-independent); the interaction
reading predicts τ* ordered by v_f²/2g.

Status: hypothesis registered with test designs; Entry 38 ran the τ-sweep the same day —
refuted as tested (bias-confounded criterion; the universal τ = 2 m stays), the suspension
mechanism itself untouched. See Entry 38 for the verdict and the deconfounded follow-up.---

## 2026-07-28 — Entry 36: ε₀ per dataset — regressed, two ways, against the frozen 0.13

**Lineage** — $I$: $(D_1..D_5, P_{f,r})$ · $T$: $\varepsilon_0$ regressed per dataset · $O$: `e36_eps0.csv` (1,400) · $S$: 0.13 survives two regressions

*Prompt (Danilo): "I think that a loose end is to regress eps_0 per dataset rather than using
the frozen 0.13 one."*

### Pre-registration (written before any result was seen)

**The question.** Every entry so far carries ε₀ = 0.13 frozen from Entry 8's D1 calibration.
Entry 31 showed the *measured gap* recurs at 0.12–0.14 across riders under frozen physics;
Entry 35 showed the frozen 0.13 pairs correctly with a regime-consistent α. What was never
done: fit ε₀ per corpus and ask (a) how universal it actually is, (b) how much the law gains
out-of-sample from corpus-level fitting, and (c) how much of each corpus's leftover bias is
ε-shaped at all. The design separates two estimands that only coincide in a perfect model:

- **balance-ε₀** (mechanism level): median of ε_coast − ε_bal over real-descent rides
  (s̄ ≥ 3%), the Entry-8 calibration statistic — what the deficit *is*;
- **bias-ε₀** (law level): the ε₀ the energy law needs to zero form 3 · ε_d's median signed
  error — per ride ε₀ᵢ = ε_coast,ᵢ − ε*ᵢ (ε* the law-matching ε), corpus value = median —
  what the deficit would have to *pretend to be* to also absorb every non-ε residual.

Both are computed at the **regime-consistent physics** (Entry 35 arm B: m̂, Ĉrr, ĈdA_reg,
wind — the honest pair), with the frozen-priors physics carried as reference; ε_bal follows
its standing convention (α at the measured flat speed — which at ĈdA_reg is the
regime-consistent α itself, making the pass self-consistent). Out-of-sample discipline:
chronological halves per corpus; fit both ε₀ variants on the first half, score form 3 · ε_d
on the second half against the frozen 0.13, reporting accuracy AND bias with 95% CIs.

**Registered predictions.**

- **P1 (the mechanism is near-universal):** balance-ε₀ at regime physics stays in a narrow
  band around the frozen value (≈ 0.10–0.17) on every corpus — both ε_coast and ε_bal shift
  with α together (Entry 34's ledger; the cap is the only leak), so the mechanism-level
  deficit should be nearly physics- and corpus-invariant.
- **P2 (the law-level fit absorbs the remainder):** bias-ε₀ > balance-ε₀ on every corpus,
  with the largest excess on D4 (JAAM, the largest E35 leftover bias) — the difference is
  the non-ε residual wearing an ε costume.
- **P3 (fitting buys little out-of-sample):** the held-out gain of corpus-fitted bias-ε₀
  over frozen 0.13 is ≤ 1–2 pp of median |Δ%| on D3–D5 — worthwhile only where the E35
  leftover bias was ≥ 2 pp (D4).
- **P4 (consistency identity):** (bias-ε₀ − balance-ε₀) × (β·h̃₋/E) reproduces each
  corpus's E35 leftover bias to within the CIs — the decomposition closes.

**Failure modes.** P1 broken (balance-ε₀ scattering wide) ⇒ the deficit's universality was
an artifact of the frozen bookkeeping and the paper's recurrence claim needs a scale-down.
P3 broken upward (fitting buys > 2 pp) ⇒ per-corpus ε₀ becomes a recommended calibration
step and the article's single-constant story needs the qualifier.

Instrument: `e36_eps0.py` (constants joined from `e35_residual.csv`/`perride_invert.csv`;
`E36_SMOKE=1`). Corpora D1–D5; D2 flagged (its ĈdA_reg is a stop-go composite, Entry 35).

### Results (first full run, 2026-07-28 — 1,400 rides)

**P1 — the mechanism constant is universal: CONFIRMED.** Balance-ε₀ (median ε_coast − ε_bal,
real descents, 95% CIs):

| corpus | regime physics | frozen physics |
|---|--:|--:|
| D1 (n = 22) | 0.113 [0.089, 0.128] | 0.122 [0.075, 0.146] |
| D2 (n = 26) | 0.070 [0.058, 0.094] | 0.092 [0.077, 0.112] |
| D3 (n = 156) | 0.115 [0.104, 0.126] | 0.097 [0.083, 0.106] |
| D4 (n = 20) | 0.098 [0.091, 0.116] | 0.126 [0.098, 0.149] |
| D5 (n = 224) | 0.115 [0.098, 0.126] | 0.119 [0.108, 0.133] |
| **D3–D5 pooled** (n = 403, stratified) | **0.115 [0.104, 0.123]** | **0.109 [0.101, 0.117]** |

A tight band — **0.10–0.13 across all five corpora and both physics** (D2's 0.07 carries its
stop-go/composite-α caveat). At regime physics the band centres at ≈ 0.115, with the frozen
0.13 at its top edge (three CIs exclude 0.13 narrowly); the cost of keeping 0.13 is < 0.5 pp
of bias — not worth a re-baseline, and the recurrence claim survives its sternest test yet.

**P2 — bias-ε₀ > balance-ε₀, largest on D4: CONFIRMED.** Bias-ε₀ (regime physics): D1 0.127
[0.035, 0.186] ≈ balance (its residual was ≈ 0); D2 0.099 [0.058, 0.137]; D3 **0.201**
[0.176, 0.219]; D4 **0.356** [0.318, 0.402] — the largest excess, exactly where Entry 35's
leftover bias was largest; D5 **0.153** [0.136, 0.179]; pooled D3–D5 **0.202
[0.181, 0.217]** (stratified, n = 1,279). The excess over balance-ε₀ is the non-ε residual
wearing an ε costume.

**P3 — fitting buys almost nothing out-of-sample: CONFIRMED (stronger than registered).**
Chronological halves, form 3 · ε_d on the held-out half (med|Δ%| · bias, 95% CIs):

| corpus | frozen 0.13 | balance-ε₀(train) | bias-ε₀(train) |
|---|--:|--:|--:|
| D1 | **6.0** [2.2, 10.5] · +4.0 | 6.3 · +4.8 | 7.8 · +7.8 |
| D2 | **2.9** [1.6, 5.5] · −0.9 | 3.9 · −3.0 | 5.1 · −4.6 |
| D3 | **3.2** [2.9, 3.8] · −2.4 | 3.5 · −3.2 | 3.4 · −1.4 |
| D4 | 3.6 [3.3, 4.2] · −3.5 | 3.7 · −3.7 | **2.9** [2.6, 3.3] · −2.4 |
| D5 | 5.1 [4.6, 5.7] · −1.3 | 5.2 · −1.4 | **4.9** [4.5, 5.5] · −0.9 |
| D3–D5 pooled (stratified test halves; shared pooled-train constants 0.110 / 0.166) | 4.2 [4.0, 4.4] · −2.6 | 4.3 [4.1, 4.6] · −3.0 | **3.9** [3.7, 4.2] · −1.7 |

(The pooled row's fitted variants use one shared pooled-train constant each; pooling the
per-corpus fits instead gives 4.4 / 3.9 — same picture.) Fitting ε₀ per dataset *hurts* on D1 and D2 (temporal drift again: D1's train-half bias-ε₀
is 0.232 against a whole-corpus 0.127 — the Entry-34 lesson at corpus grain), is a wash on
D3, and pays only on D4 (+0.65 pp) and marginally D5 (+0.2 pp) — under the registered
≤ 1–2 pp ceiling, and positive only where Entry 35's leftover bias was ≥ 2 pp, exactly as
predicted. **The frozen 0.13 stands.**

**P4 — the consistency identity closes.** (bias-ε₀ − balance-ε₀) × (β·h̃₋/E) per corpus:
D3 0.086 × ≈ 15% ≈ 1.3 pp (Entry 35 leftover: −1.3); D4 0.258 × ≈ 10% ≈ 2.6 (leftover −2.7);
D5 0.038 × ≈ 13% ≈ 0.5 (leftover −0.5). The decomposition is exact to the rounding: the
remaining residual is **not ε-shaped** — it is cost-side, concentrated in the heaviest,
highest-power rider (his braking reads 0.8% of E in Entry 35's strict variant; the rest is
open).

**The re-freeze question, asked and answered the same day.** Danilo: "I wonder if we should
use the median value of that pooled corpus as the frozen constant, given that it is our best
estimate so far" — then, reading P3: "actually P3 doesn't attest that, nevermind." The
pooled row above is the receipt: the pooled-train balance-ε₀ (0.110, nominally the best
mechanism-level estimate) transfers *worse* than the frozen 0.13 on the pooled held-out
halves (4.3 vs 4.2, bias −3.0 vs −2.6), because the OOS bias under regime physics runs
negative and a smaller ε₀ refunds more. Two further reasons recorded with the decision:
0.13's D1-only calibration is what keeps D3–D5 genuinely held-out for the paper's headline
claims, and the pooled 0.115 [0.104, 0.123] remains published here as the refined
*measurement* of the deficit — a better estimate of the mechanism, not a better deployment
constant. **ε₀ = 0.13 stays frozen.**

**Synthesis.** The loose end ties off in the frozen constant's favour: ε₀ ≈ 0.11–0.13 is a
universal mechanism-level constant across five corpora, two physics protocols and three
riders; per-dataset regression is either a costume for non-ε error (bias-ε₀) or a noisier
re-measurement of the same constant (balance-ε₀), and neither transfers better than 0.13
out-of-sample except where the costume covers a real, identified cost-side remainder (D4).
Instrument: [`e36_eps0.py`](../../src/harness/e36_eps0.py) (`E36_SMOKE=1`); output
`e36_eps0.csv` (1,400 rides).

---

## 2026-07-28 — Entry 35: the honest-physics residual — where do the missing 4–5 points live?

**Lineage** — $I$: $(D_1..D_5, P_{f,r})$ · $T$: F3 vs $F_\mathrm{base}$ residual · $O$: `e35_residual.csv` (1,409) · $S$: where the missing 4–5 points live

*Prompt (Danilo), on Entry 33's shared −4…−5 pp under-prediction bias at inverted physics and
the (α, ε) pairing analysis: run arms A and B as journal entries; the two-CdA transfer split
is NOT tested ("CdA on flat = CdA everywhere is an okay assumption. People also like to tuck
on descents. Can be noted as a limitation though.").*

### Pre-registration (written before any result was seen)

**The question.** Under per-ride inverted physics (Entry 33), BOTH engines under-predict by
4–5 pp on D3–D5 — the missing cost is engine-shared, so it is input-side or un-modelled
dissipation, not model-form. Two candidate residuals, each with its own arm. Descent speeds
are used nowhere (Danilo: "descent speed is generally a messy measurement due to braking");
descent braking is excluded by the Appendix-A cancellation (it dissipates gravity's share,
not the legs').

**Arm A — measure the legs-funded braking.** Per adjacent-sample pair on NON-descent 30 m
cells (cell grade > −1.5%), with the ride's inverted physics (m̂, Ĉrr, ĈdA joined from
`perride_invert.csv`; fallbacks where not inverted):

- observed decel a_obs = (v_prev − v)/dt (only when positive, v̄ ≥ 1 m/s, dt ≤ 10 s);
- physics decel a_coast(v, s) = C_rr·G·cosθ + ½ρ·ĈdA·v̄²/m̂ + G·sinθ — coasting decels
  contribute ZERO by construction (Danilo: "and coasting" — a raw ΔKE sum would double-count
  drag the model already charges);
- braking force excess = max(0, a_obs − a_coast); E_brake += m̂·excess·dx; t_brake += dt;
  cadence > 0 during braking tracked as a cross-check flag.

Registered predictions:

- **P-A1 (Danilo's bound):** braking time-share of moving time on non-descent cells is
  ≤ 3 s per 3 min (≈ 1.7%) on D3–D5, and ≤ 3 s per 60 s (5%) on D2.
- **P-A2 (materiality — the rate does not settle it):** 60 full-KE kills per 3 h ≈ 100 kJ
  ≈ 7% of a ride, so a low time-share is compatible with a material energy-share. Decision
  rule fixed now: E_brake/E_meas < 1% on D3–D5 ⇒ braking exonerated as the residual;
  ≥ 3% ⇒ primary contributor; between ⇒ partial.

**Arm B — the regime-consistent ĈdA.** Entry 33's segment-ĈdA over-predicts the flat
equilibrium speed (model v_f vs measured flat speed: P. Paz 29.9 vs 28.6, author 22.6 vs
21.2 km/h — the well-behaved flats are selectively the fastest, most sheltered riding).
The regime-consistent estimator needs no segments at all:

$$\hat C_dA^{\mathrm{reg}} = \frac{k_{\mathrm{eff}}\,P_{\mathrm{flat}}/v_{\mathrm{meas}} - C_{rr}\,\hat m\,g}{\tfrac{1}{2}\rho\,v_{\mathrm{meas}}^2}$$

with P_flat the regime extractor's flat power and v_meas the measured flat speed — it closes
the v_f gap by construction. Re-run the Table-5 law rows (forms 3·ε_d, 3·ε_f, 4·ε_f,
simulation) with ĈdA_reg replacing the segment ĈdA (all else as Entry 33, wind included),
and compute the per-ride law-matching ε* (form 3 solved for ε).

Registered predictions:

- **P-B1:** ĈdA_reg > segment-ĈdA on every corpus (the selection bias has one sign), and
  the published ĈdA_reg − ĈdA gap becomes the measure of that bias.
- **P-B2:** the shared negative bias narrows by roughly the α_a share of the v_f gap
  (~1.5–2 pp on D3/D5), law and simulation in lockstep (the Entry-30 signature).
- **P-B3:** the matching ε* rises from ≈ 0.20 toward ε_coast − δ, but does not reach it
  unless arm A's energy is also material.

**Failure modes, fixed now.** A exonerated + B closes only ~2 pp ⇒ the remaining ~2–3 pp
residual stays attributed to the (α, ε) bundle rule, published as such. The untested
flat-CdA-everywhere transfer assumption is recorded as a limitation (tucking on descents
plausibly compensates the absence of drafting there), NOT as an arm.

Instrument: `e35_residual.py` (one pass per ride, both arms; `E35_SMOKE=1`). Corpora:
D1–D5, populations as Entry 33 (join on file basename; unjoined rides fall back to
anchor/prior constants, flagged).

### Results (first full run, 2026-07-28 — 1,409 rides, constants joined for all)

**Arm A — the braking measurement: the registered instrument fails its own validity check;
the robust reading vindicates the skepticism.** Per corpus — raw registered estimator, then
the disclosed variants (excess > 0.3 m/s²; + cadence 0):

| corpus | time-share (raw) | E_brake/E: raw | > 0.3 m/s² | + cadence 0 | events/h | cadence>0 while "braking" |
|---|--:|--:|--:|--:|--:|--:|
| D1 | 6.1% [5.2, 7.4] | 5.4% [3.1, 6.4] | 3.2% | **0.6%** | 135 | 80% |
| D2 | 9.0% [8.7, 9.6] | 5.6% [4.9, 6.3] | 2.7% | **1.4%** | 177 | 58% |
| D3 | 4.8% [4.6, 5.1] | 2.9% [2.6, 3.3] | 1.8% | **0.7%** | 76 | 70% |
| D4 | 5.6% [5.1, 6.3] | 3.3% [2.9, 3.9] | 2.1% | **0.8%** | 93 | 63% |
| D5 | 7.8% [7.4, 8.1] | 4.9% [4.7, 5.3] | 3.1% | **1.3%** | 161 | 69% |

Taken literally, the raw estimator refutes P-A1 (time-shares 5–9% ≫ the 1.7%/5% bounds) and
reads "primary contributor" under P-A2 (≥ 3% of E on three corpora). But its own cross-check
disqualifies that literal reading: **58–80% of the flagged time has the cadence spinning** —
riders do not pedal while braking — and the event rate (one per 20–45 s, D1 brevets ≈ urban
D2) is physically implausible as brake events. The registered estimator measures *decel in
excess of coasting*, which includes every pedal-modulated slowdown and every speed-jitter
spike above the (small, at effective ĈdA) coasting decel. The defensible bound: legs-funded
braking is **between the cadence-0 variant and the raw number, with the honest point estimate
near the strict reading — ≈ 0.6–0.8% of E on the open corpora (D1/D3/D4), ≈ 1.3–1.4% on the
stop-heavier D2/D5** — under the registered 1% exoneration line for the open corpora, and
showing the urban ≈ 2× contrast Danilo's bounds implied (0.7 vs 1.4). **Verdict: braking is
NOT the residual**; the skeptical prior was right where the instrument was trustworthy.

**Arm B — the regime-consistent ĈdA closes the residual.** P-B1 confirmed on every corpus
(ĈdA_reg > segment-ĈdA: 0.328 vs 0.288 on D3, 0.449 vs 0.395 on D4, 0.399 vs 0.365 on D5,
0.373 vs 0.342 on D1 — medians over the regime-invertible rides; v_f(reg) = measured to
0.1 km/h by construction). P-B2 not just confirmed but exceeded — the shared bias closes
nearly fully, law and simulation in lockstep:

| corpus | form 3 · ε_d, segment-ĈdA | form 3 · ε_d, regime-ĈdA | simulation, segment → regime |
|---|--:|--:|--:|
| D1 | 5.4 [3.8, 10.9] · −0.3 [−3.2, +3.1] | 6.6 [3.8, 8.1] · +0.1 [−1.7, +5.0] | 5.0 · +0.2 → 3.3 · +1.1 |
| D2 | 6.9 [5.4, 9.5] · −3.1 [−4.7, −1.1] | 4.6 [2.7, 6.1] · +1.4 [−0.3, +3.7] | 7.8 · −2.2 → 7.6 · +4.6 |
| D3 | 5.1 [4.6, 5.5] · −3.8 [−4.4, −3.2] | **3.1 [2.8, 3.3] · −1.3 [−1.8, −0.8]** | 5.7 · −4.6 → 3.2 · −1.2 |
| D4 | 6.0 [5.2, 6.5] · −5.2 [−6.2, −4.4] | **3.2 [2.8, 3.6] · −2.7 [−3.1, −2.2]** | 5.8 · −4.9 → 3.3 · −2.4 |
| D5 | 7.5 [7.1, 8.0] · −4.0 [−4.7, −3.2] | **4.9 [4.6, 5.3] · −0.5 [−1.2, −0.1]** | 7.2 · −3.5 → 5.1 · +0.3 |

Throughout, **ε₀ stays frozen at 0.13** — no ε quantity is fitted anywhere in this entry.
ε_d in each column is ε_coast(that column's physics) − 0.13: only ε_coast's input α/β moves
with the aero, which is the definition of the dynamic estimator. The bias closing under the
same frozen deficit is therefore the cleanest demonstration that Entry 33's failure was the
pairing, never ε₀ itself.

Pooled D3–D5 (stratified, n = 1,296): **form 3 · ε_d 3.9 [3.6, 4.1] · −1.4 [−1.8, −1.0]**
against the simulation's 4.0 [3.7, 4.2] · −0.8 [−1.1, −0.5] — versus 6.3 · −4.2 under the
segment ĈdA, and versus Entry 33's best (ε_f at 3.8 · +0.4). The dynamic ε returns: under a
ride-consistent α, **ε_d matches ε_f's pooled accuracy while keeping the regime rule and the
mechanism** — and ε_f, symmetrically, flips to *under*-refunding (+2.5 to +4.8 biases), its
Entry-33 "win" now fully identified as compensation. P-B3 confirmed in direction: the
matching ε* rises 0.21 → 0.34 (D3), 0.17 → 0.37 (D4), 0.23 → 0.33 (D5), toward but not
reaching ε_d — the residual gap matches the remaining small biases (−0.5 to −2.7, largest on
JAAM). D2's ĈdA_reg = 0.62 is not aero — with v_meas depressed by stop-go, the
regime-consistent constant becomes a *total-loss* coefficient — and yet the (α, ε_d) pair
still improves there (6.9 → 4.6): the pairing logic holds even when α is a composite.

**Synthesis.** Entry 33's missing 4–5 points were, in order: (i) the flats-selection bias of
the segment ĈdA (arm B closes most of it — the well-behaved flats are the fastest, most
sheltered riding, so the segment estimator under-prices the ride's true air losses);
(ii) legs-funded braking, real but small (≈ 0.7–1.4% of E, arm A robust reading);
(iii) an unexplained remainder of −0.5 to −2.7 pp (largest for the heaviest, highest-power
rider). The (α, ε) bundle rule survives but shrinks: with a *regime-consistent* per-ride
inversion, the honest pair is restored automatically and the Entry-33 flip un-flips. The
practical recipe this licenses (journal-level for now; article later): m̂ from climbs,
ĈdA_reg from the flat regime pair, C_rr prior — then the dynamic ε_d and the regime rule
work as designed, at ≈ 3–5% with small bias, fully automatic.

Instrument: [`e35_residual.py`](../../src/harness/e35_residual.py) (`E35_SMOKE=1`); output
`e35_residual.csv` (1,409 rides). The two arm-A sensitivity variants were added after the
smoke run exposed the noise signatures and are disclosed as such above; the registered raw
estimator is reported unchanged alongside them.

---

## 2026-07-28 — Entry 34: the S-curve deficit — ε₀ as a grade-conditional pedalling probability

**Lineage** — $I$: $(D_1..D_5, P_{f,r})$ · $T$: occupancy sigmoid · $O$: `scurve_deficit.csv` (1,287) · $S$: $\varepsilon_0$ as a pedalling probability

*Prompt (Danilo), on the unclamped ε_d going negative beyond s_*/ε₀ ≈ 15%: "I feel this is a
weakness that we should figure out, esp. considering the intuition of coasting deficit being
associated with pedalling. Pedalling is way more likely on gentler grades than steeper ones.
We should have a continuous transition from 1 to 0 rather than clamping it. I would expect the
probability of pedalling on descents to follow a S-shaped curve, whose curve parameters is
conditional on both event context, rider behaviour and route characteristics."*

**The object under study — disambiguated.** What this entry explores is the characterisation
of

$$\varepsilon := \varepsilon_{\mathrm{coast}} - \delta,$$

where δ is the **deficit term** — the amount by which real recovery falls short of the coasting
ideal. Three levels must not be conflated:

1. **The decomposition** ε = ε_coast − δ is a *definition* of δ (given ε_coast's geometry).
2. **The mechanistic identity**: the Appendix ledger (below) gives δ an exact mechanistic
   expression — per descent segment, δᵢ = E_legs,i/(β·hᵢ). This is not a hypothesis; it is
   what δ *is*, model-free.
3. **Models of δ** are the hypotheses. The published law is the **constant model**,
   δ ≈ ε₀ = 0.13. This entry registers alternatives that infer δ from ride observables:

$$\text{constant:}\ \ \delta \approx \varepsilon_0 \qquad\text{vs}\qquad \text{S-curve:}\ \ \delta(\bar s) \approx \varepsilon_0 \cdot g(\bar s), \quad g(s) = \frac{1}{1 + e^{(s - s_{50})/w}}$$

with g the S-shaped pedalling probability (Danilo's hypothesis: pedalling is far likelier on
gentle grades than steep ones) and (s₅₀, w) conditional on rider, event context and route
character. Structural payoff of the S-curve model: as g → 0 on steep grades the estimator
returns to the non-negative coasting limit — the negative-prediction weakness disappears *by
mechanism*, not by clamp; the constant model is the g ≡ 1 special case, which the corpora
cannot distinguish from the S-curve below ~6% mean grade. Two further models of δ enter as
nulls/refinements via the factorization below: the *dilution* model (constant behaviour,
δ ∝ 1/(v̄·s̄)) and the *measured-factors* model (δ from observed pedalling occupancy ×
intensity).

**The exact source of ε₀, from the Appendix ledger** *(added on Danilo's note: "describe what
is the source of the original eps_0 given the appendix derivations… eps = eps_coast −
eps_due_to_deficit, where eps_due_to_deficit = P(descent_pedalling) ×
magnitude_of_loss_when_pedalling; i suspect that magnitude of loss when pedalling is
conditional on average power output on descents").*

Paper Appendix A.2's balance form is E_legs,i = α·Δxᵢ − εᵢ·β·hᵢ per descent segment. On real
descents (s > s_*, where ε_coast = (α/β)/s = α·Δxᵢ/(β·hᵢ)) this rearranges **exactly** to

$$\varepsilon_i = \varepsilon_{\mathrm{coast}}(s_i) - \frac{E_{\mathrm{legs},i}}{\beta\,h_i} \quad\Rightarrow\quad \delta_i = \frac{E_{\mathrm{legs},i}}{\beta\,h_i}$$

— δᵢ IS the segment's descent pedal energy over its k_eff-scaled drop, no approximation
(level 2 above). **Ride-level δ (no subscript) is then defined as the drop-weighted mean of
the δᵢ** — the same aggregation the appendix uses for ε itself — and it telescopes: the hᵢ
cancel, leaving

$$\delta \;=\; \frac{\sum_i \delta_i\,h_i}{\sum_i h_i} \;=\; \frac{E_{\mathrm{legs},-}}{\beta\,H_-}$$

— total descent pedal energy over the scaled total drop. This is exactly what the measured
ε_coast − ε_bal estimates, so the exploratory table below and the ride-level factorization
are statements about this δ. So the calibrated ε₀ = 0.13 is the empirical statement *riders pedal ≈ 13% of the released
potential energy back into their descents*. Danilo's factorization is then an identity split
of that numerator: writing E_legs,- = p_ped · P̄_ped · t₋ (occupancy × intensity × time),

$$\delta = \frac{p_{\mathrm{ped}}\,\bar P_{\mathrm{ped}}\,t_-}{\beta\,H_-} = \frac{p_{\mathrm{ped}}\,\bar P_{\mathrm{ped}}}{\beta\,\bar v_-\,\bar s_-}$$

— (probability of pedalling) × (pedal power while pedalling) ÷ (gravitational power released,
k_eff-scaled). **How g relates to the factorization** *(Danilo: "how does p · P̄ · t relate to g?")*. They are
not the same object. The identity gives δ's full grade profile as a product of three factors:

$$\delta(s) = \underbrace{p_{\mathrm{ped}}(s)}_{\text{occupancy}} \cdot \underbrace{\frac{\bar P_{\mathrm{ped}}(s)}{\beta\,\bar v(s)\,s}}_{\text{magnitude}}$$

The S-curve model δ ≈ ε₀·g(s̄) is the hypothesis that **g is the occupancy factor alone** —
g(s) := p_ped(s), the S-shaped probability of pedalling — with **ε₀ absorbing the magnitude
factor at the gentle-grade reference where g ≈ 1**. That reading makes ε₀ a rider's intensity
habit (P̄_ped over released power at their typical descents), which is precisely why ε₀ should
be rider-conditional (the magnitude conjecture above). But the magnitude factor is *also*
grade-dependent — the 1/(v̄·s) dilution — so the observable fade of δ with grade is the
*product* of the S-curve and the dilution, steeper than either alone. Fitting ε₀·g(s) to raw
δ therefore conflates them: g would absorb dilution it doesn't own. That is what design step
1b prevents — measure p_ped(s) directly and g is identified on its own; the dilution needs no
fit at all (v̄ and s are observed).

Three consequences sharpen the hypothesis:

1. **Both factors are directly observable** in the power stream — p_ped as the fraction of
   descent time with P > threshold, P̄_ped as the mean power over those samples (the regime
   extractor's speed-gated descent power is nearly this already). g(s) need not be inferred
   from residuals; it can be *measured* as p_ped(s) per grade bin.
2. **A mechanical null exists**: even at constant behaviour (p_ped, P̄_ped fixed), δ ∝
   1/(v̄₋·s̄₋) — the same pedalling dilutes against more gravitational power on steeper drops.
   A fade with grade is therefore predicted by dilution alone; the S-curve model is confirmed
   only if p_ped itself falls with s beyond what dilution explains. Conversely P. Paz's
   *rising* δ means his p_ped·P̄_ped grows super-linearly with grade — strong behaviour, not
   noise.
3. **The magnitude term carries the rider-conditionality**: P̄_ped on descents is a power
   *habit* (Danilo's conjecture: conditional on the rider's average descent power output),
   which is exactly where JAAM's high-power riding style and P. Paz's coasting style should
   separate — testable as corr(per-ride δ, descent-regime power / (β·v̄₋·s̄₋)) across each
   corpus.

**Exploratory first cut (DISCLOSED PEEK — this is not a confirmation).** Ride-level measured
δ (= ε_coast − ε_bal) vs mean descent grade s̄ on real descents (s̄ ≥ 3%), current canonical
CSVs:

| rider | s̄ ∈ [3,4)% | [4,5)% | [5,6)% | Spearman ρ(s̄, δ) |
|---|--:|--:|--:|--:|
| P. Paz (n = 161) | +0.083 | +0.113 | +0.116 | **+0.13** (rises) |
| JAAM (n = 21) | +0.137 | — | — | **−0.57** (fades, small n) |
| author (n = 221) | +0.138 | +0.098 | +0.056 | **−0.28** (fades) |

The grade-dependence of δ is real but **rider-conditional in sign**: the author and JAAM fade (as
the pedalling-probability story predicts), P. Paz *rises* — the coasting-style open-road
descender pedals *more* (relative to his coasting ideal) on his steeper descents, or his
steeper descents carry something else (surface? corners?) the ride-level s̄ can't see. This is
exactly the "parameters conditional on rider behaviour" clause of the hypothesis — and it
rules out a universal one-curve replacement for ε₀ at ride level.

**Registered confirmatory design (fixed before any fitting).**

1. **Grain**: segment-level, not ride-level — per 30 m descent cell, deficit vs cell grade
   within rides (ride-level s̄ is a coarse proxy and confounds route mix with behaviour).
1b. **Measure the factors, don't infer them**: per grade bin, pedalling occupancy p_ped(s)
   (share of descent time at P > 10 W) and intensity P̄_ped(s); test the dilution model of δ
   (δ ∝ 1/(v̄s) at constant p_ped·P̄_ped) BEFORE attributing any fade to the S-curve, and
   test corr(δ, descent-regime power) for the magnitude-conditionality conjecture.
2. **Fit**: per-rider logistic (ε₀, s₅₀, w) by least squares on a chronological calibration
   half of each rider's real-descent rides; frozen constant-ε₀ = 0.13 as the null, the
   dilution-only model as the second null.
3. **Test**: held-out chronological half, RMS of ε_bal − ε_d(s̄) per ride; success =
   out-of-sample RMS improvement ≥ 5% over the constant on ≥ 2 of 3 riders.
4. **Failure mode**: keep the constant ε₀ (g ≡ 1) and publish the S-curve as refuted at this
   data's grade range; the negative-prediction region stays labelled extrapolation.
5. Event context and route covariates (brevet vs training; unpaved fraction) enter only
   AFTER the grade-only fit, as residual predictors — same discipline as Entry 8's ε ladder.

Owner in the paper: §4.4's coasting-deficit thread. Status at registration: fit NOT run.

### Results (registered design executed same day — `scurve_deficit.py`)

**Step 1b — the factors, measured at cell grain (1,287 rides, 30 m descent cells, bins
[1.5, 2, 3, 4, 5, 6, 8, 12, 20)%).** The pedalling-occupancy S-curve is REAL and universal in
direction — p_ped(s) falls monotonically for **all three riders**, including P. Paz, whose
*ride-level* deficit rose with s̄ (the ride-level peek was confounded by route mix, exactly
why the registration demanded cell grain):

| rider | p_ped 1.5–2% | 3–4% | 5–6% | 8–12% | 12–20% | P̄_ped range (W) |
|---|--:|--:|--:|--:|--:|--:|
| P. Paz | 0.62 | 0.36 | 0.20 | 0.07 | 0.05 | 86–123 |
| JAAM | 0.66 | 0.38 | 0.20 | 0.12 | 0.11 | 133–178 |
| author | 0.41 | 0.21 | 0.10 | 0.05 | 0.03 | 89–121 |

Intensity P̄_ped(s) is roughly **flat in grade** and strongly **rider-conditional** (author
≈ 90 W, P. Paz ≈ 110, JAAM ≈ 170 — tracking their overall power levels): Danilo's magnitude
conjecture confirmed — the deficit's size carrier is the rider's descent power habit, its
grade shape is occupancy. And the measured per-bin δ falls FASTER than the dilution null
(P. Paz at 8–12%: measured 0.017 vs dilution-only 0.059) — the fade is behaviour, not just
arithmetic. One anomaly: the ≥ 20% bin ticks back up on every rider (author: δ 0.085 — likely
walking/pushing power on unridable pitches; `push_stats` is the tool to test that, future
work).

**Steps 2–4 — the ride-level estimator test: 0/3, the constant stays.** Chronological
halves, held-out RMS of ε_bal − prediction. Four models of δ per rider: *frozen 0.13* (the
published constant, nothing fitted); *const-fit* (same constant shape, value refit on the
training half — separates "the S-shape helps" from "refitting the level helps"); *dilution*
(the mechanical null δ̂ = c/(v̄₋·s̄₋), c fitted on train — fade from arithmetic at constant
behaviour); *logistic* (the S-curve, ε₀′·g(s̄), three parameters fitted on train):

| rider | train/test n | frozen 0.13 | const-fit | dilution | logistic | logistic vs frozen |
|---|--:|--:|--:|--:|--:|--:|
| P. Paz | 78/78 | **0.076** | 0.102 | 0.101 | 0.102 | −33% [−57, −14] |
| JAAM | 10/10 | **0.045** | 0.082 | 0.058 | 0.072 | −62% [−123, −4] |
| author | 112/112 | 0.090 | 0.090 | 0.092 | 0.090 | −0.0% [−5.1, +4.5] |

**REGISTERED VERDICT: not confirmed** — the S-curve does not improve the ride-level
estimator; per the registration's failure mode the constant ε₀ stays, and the S-curve is
refuted *as a ride-level estimator upgrade* at this data's grade range.

**Why both results are right — the reconciliation.** Three mechanisms, all visible in the
tables. (i) *Ride-level s̄ cannot carry the cell-level curve*: a ride's descents mix grades,
so δ(s̄) is a blurred mixture — the author's fitted logistic (ε₀' = 0.476, s₅₀ = 1%, w = 3%)
evaluates to ≈ 0.13 at typical s̄: given full freedom, **the fit reconstructs the frozen
constant**. (ii) *Temporal drift beats refitting*: P. Paz's train-half mean deficit is 0.063,
his test half sits near 0.13 — every train-fitted model (including the fitted constant)
transfers WORSE than the frozen 0.13, which happens to sit where his later rides do. The
frozen constant's out-of-sample robustness is itself a finding. (iii) JAAM's n = 10/10 is
too thin to fit three parameters honestly. The refined statement for the paper: **the
S-curve is the confirmed mechanism (occupancy fades monotonically with grade; intensity is
the rider-level carrier), and the constant ε₀ is its correct ride-level summary** — a
grade-resolved estimator would need per-segment evaluation (the router's per-edge grain,
edge-cost-paper territory), not a ride-level s̄.

Instrument: [`scurve_deficit.py`](../../src/harness/scurve_deficit.py) (deterministic,
seeded bootstrap CIs; `SCURVE_SMOKE=1`); output `scurve_deficit.csv` (1,287 rides).

---

## 2026-07-28 — Entry 33: per-ride physics inversion — the Table-3 analogue under m̂/Ĉrr/ĈdA inverted from each ride's own segments

**Lineage** — $I$: $(D_1..D_5, P_{a,g} \cdot P_{f,r}(m, C_{rr}, C_dA))$ · $T$: inversion + F1–F4 · $O$: `perride_invert.csv` (1,409) · $S$: **Tables 5 and 6**

*Prompt (Danilo): "generate another result aiming to produce something analogue to Table 3, one
where m, Crr and CdA are inverted per ride", with a six-step strategy (wind rule; flat/climb
segmentation; clipping; well-behaved flags; mass from a temporally-spread climb subset; Crr from
the remaining climbs at frozen CdA; CdA from flats).*

### Pre-registration (written before any result was seen)

**Question.** Table 3 scores the law under one frozen constants set (plus per-corpus mass).
Table 4 showed *rider-level* fitted physics moves individual numbers but not conclusions. The
open middle: *per-ride* inversion — every ride carries its own m̂, Ĉrr, ĈdA extracted from its
own power stream, with no human judgment. If it works, it is the answer to §4.4's "infer
per-ride parameters from the ride data itself"; if it is too ill-conditioned, that is the
result.

**Protocol** ([`perride_invert.py`](../../src/harness/perride_invert.py)). Frozen throughout:
ρ = 1.13 (by the P1 degeneracy, ĈdA is really the ρ·C_dA product at 1.13), k_eff = 0.98,
G = 9.7864, climb threshold 2%, flat band (−1.5%, 2%), ε machinery unchanged (unclamped ε_d,
ε_f = 0.20). Priors double as fallbacks: C_rr⁰ = 0.008, C_dA⁰ = 0.40, per-corpus anchor mass
(logged on D1; 78 / 74.5 / 101.9 / 74.7 on D2–D5).

- **Step 0 — wind.** Round trip (GPS start–end separation < max(1 km, 2% of distance)) ⇒
  w = 0. Else: historical daily wind (speed max, dominant direction, 10 m) at the track
  *centroid quantized to 0.25°* (≈ 25 km cells — no endpoint or fine geometry leaves the
  machine, per the repo privacy rule), open-meteo archive, disk-cached; signed headwind
  w = ½ · V_ground · cos(wind_from − net travel bearing), positive = headwind (the engines'
  sign). Cache miss with fetch disabled ⇒ w = 0, flagged.
- **Step 1 — segmentation** on the 5 m profile aggregated to 30 m cells (the ε cell scale):
  *climb segments* = maximal cell runs with s ≥ 2% in every cell and total gain ≥ 40 m;
  *flat segments* = maximal runs with every cell inside the flat band and length ≥ 1 km.
- **Step 2 — clip** the first 100 m of each flat; climbs until 10 m of gain is consumed.
- **Step 3 — well-behaved flags** (all three required, evaluated on the raw points):
  (a) no braking: no deceleration steeper than 1.5 m/s² (from speeds > 3 m/s);
  (b) power present: P > 10 W over ≥ 90% of segment time;
  (c) no stops: moving time (v ≥ 0.5 km/h) ≥ 99% of total and no recording gap > 10 s.
- **Step 4 — mass** from n_m = min(n, max(2, ⌈n/3⌉)) well-behaved climbs chosen for temporal
  spread (greedy max-min on segment midpoints — first, last, then most-isolated), so m̂ is an
  *average-mass* estimator over the ride: per segment
  m̂ᵢ = (k_eff·Eᵢ − ½ρC_dA⁰·Aᵢ) / (g(hᵢ + C_rr⁰·x̃ᵢ) + ½Δ(v²)ᵢ), with Eᵢ = ∫P dt,
  Aᵢ = ∫v_rel|v_rel| dx, x̃ᵢ = cosθ̄·xᵢ; gain-weighted mean of segments with m̂ᵢ ∈ [40, 200] kg.
- **Step 5 — Ĉrr** from the *remaining* well-behaved climbs (disjoint from step 4's, so the
  m–C_rr collinearity on any one climb is broken across segments), at frozen C_dA⁰:
  C_rr,ᵢ = (k_eff·Eᵢ − ½ρC_dA⁰Aᵢ − m̂g·hᵢ − ½m̂Δ(v²)ᵢ)/(m̂g·x̃ᵢ), gain-weighted
  ("larger / more inclined" ≡ gain = length × grade), valid range [0.001, 0.04].
- **Step 6 — ĈdA** from the well-behaved flats, given m̂ and Ĉrr:
  C_dA,ᵢ = (k_eff·Eᵢ − Ĉrr·m̂g·x̃ᵢ − m̂g·Δhᵢ − ½m̂Δ(v²)ᵢ)/(½ρAᵢ), weight xᵢ/(1 + σ_h,ᵢ)
  (σ_h = intra-segment elevation SD — the operationalisation of "lower height variability"),
  valid range [0.10, 1.00] m².

Any estimator with no valid segment falls back to its prior, per-field, and the CSV records
the source of every constant. Scoring: the Table-3 grid (forms 1–4 × ε_d/ε_f + canonical,
v_f from the ride's flat power at the inverted physics) on D1–D5; mulberry32 bootstrap CIs,
seeds 42/43. `INVERT_SMOKE=1` = 40 rides/corpus; `INVERT_NOFETCH=1` = no network.

**Pre-registered predictions.**

- **P1 (mass validates).** Corpus-median m̂ lands within ±3 kg of the known/implied anchors
  (D1 logged 71–80; D5 ≈ 73–75; D3 ≈ 74.5; D4 ≈ 102) on the rides where mass inverts.
- **P2 (moves toward fitted physics).** Where rider-level fitted constants differ most from
  the priors (JAAM: C_dA 0.323, C_rr 0.0108), the per-ride table moves the corpus medians
  toward Table 4's fitted column, not away.
- **P3 (coverage is corpus-shaped).** D2's urban rides almost never contain a 1 km
  uninterrupted in-band flat or a clean 40 m climb → near-total fallback, D2's column ≈
  Table 3's. Coverage is highest on D1 (brevets: long flats, sustained climbs).
- **P4 (segment noise, ride stability).** Per-segment estimates scatter widely, but
  ride-level m̂ is stable: within-corpus IQR ≤ ±8 kg on D3–D5's mass-inverted rides.
- **P5 (parity persists).** Law-vs-simulation parity survives per-ride physics (both engines
  read the same inverted constants — the Entry-30 lockstep, now at per-ride grain).
- **P6 (no free lunch).** The fully-inverted subset is selection-biased toward mountainous,
  well-measured rides; its medians are NOT comparable to the corpus medians and will be
  reported separately.

### Results (first full run, 2026-07-28 — 1,409 rides)

**Populations.** D1 44 · D2 69 · D3 441 · D4 219 · D5 636. Note D2/D5 are *larger* than the
published clean corpora (62/621): this harness's eligibility is parse + power + ≥ 3 km, not the
per-corpus clean filters — the analogue table is therefore its own population, disclosed as
such (the frozen-vs-inverted comparisons below are between medians of slightly different ride
sets on those two corpora).

**Coverage** (P3: corpus-shaped, confirmed). mass inverted / full inversion / wind fetched:
D1 33/19/0 · D2 17/**1**/0 · D3 230/106/178 · D4 103/20/82 · D5 340/56/192. The urban corpus
almost never offers a qualifying segment, exactly as registered; D1's brevets are loops or
out-and-back (zero wind fetches — every non-loop is on the corpora with manifest dates).
452 wind lookups total, all through the 0.25°-quantized-centroid cache.

**P1 — the mass inversion validates (confirmed; D4 at the boundary).**

| corpus | m̂ median (IQR) | anchor | Δ |
|---|--:|--:|--:|
| D1 | 76.6 (69.9–82.9) | logged 71–80 | in range |
| D2 (n = 17) | 82.3 (73.7–84.7) | 78.0 | +4.3 (thin) |
| D3 | 75.4 (71.3–79.8) | 74.5 | **+0.9** |
| D4 | 98.7 (94.7–103.3) | 101.9 | −3.2 |
| D5 | 73.7 (68.4–80.8) | 74.7 | **−1.0** |

P4 (ride-level stability) also confirmed: every IQR half-width ≤ ±6.2 kg, under the ±8
registration.

**The inverted constants — per-corpus summary (medians over the inverted subsets, seeded
bootstrap 95% CIs; n in parentheses).**

| corpus | m̂ (kg) | mass ref | Ĉrr | ĈdA (m²) |
|---|--:|--:|--:|--:|
| D1 | 76.6 [73.1, 82.4] (33) | logged 71–80 | 0.0093 [0.0082, 0.0110] (23) | 0.308 [0.269, 0.347] (34) |
| D2 | 82.3 [73.7, 84.7] (17) | 78.0 | 0.0063 (n = 1) | 0.344 [0.294, 0.418] (31) |
| D3 | 75.4 [74.2, 76.1] (230) | 74.5 | 0.0083 [0.0079, 0.0088] (146) | 0.258 [0.246, 0.277] (374) |
| D4 | 98.7 [97.0, 100.9] (103) | 101.9 | 0.0095 [0.0080, 0.0112] (22) | 0.391 [0.380, 0.398] (202) |
| D5 | 73.7 [72.1, 74.6] (340) | 74.7 | 0.0088 [0.0081, 0.0096] (87) | 0.293 [0.285, 0.302] (385) |
| *prior / fallback* | *anchor* | — | *0.008* | *0.40* |

Accuracy and bias where ride-level ground truth exists — D1's logged masses: per-ride
m̂ − m_logged has median bias **+2.4 kg [−0.7, +4.4]** and median |error| **5.3 kg
[3.1, 6.4]** (n = 33) — the per-ride estimate is ±5 kg-noisy, the corpus median converges.
On D3/D5 the m̂ CIs (±1 kg) bracket the anchors; on D4 the CI [97.0, 100.9] sits ~3 kg
below the whole-corpus climb inversion (101.9) — two different estimators (temporally-spread
segment subset vs corpus-pooled sustained climbs) resolving a real, small difference, not a
failure. Ĉrr: the 0.008 prior was a good guess everywhere, and D4 moves toward JAAM's fitted
0.0108 (P2: supported for C_rr). ĈdA inverts **low everywhere** — 0.26 (D3) / 0.29 (D5) /
0.31 (D1) against the 0.40 prior, with only heavy-rider D4 near it (0.391) — and the CIs are
tight enough that this is not noise. Reading: the flat-derived ĈdA is an *effective* aero —
it absorbs drafting (P. Paz's group brevets), riding position on easy ground, and the ρ·C_dA
degeneracy — not a wind-tunnel number. It is, however, the aero the rides actually
experienced.

**The analogue scoreboard vs frozen Table 3** — accuracy and bias together, 95% CIs
throughout (frozen = paper Table 3's published values; * = ε_f in-sample on D2; frozen and
inverted D2/D5 populations differ slightly, 62/621 vs 69/636):

| corpus | model | frozen med\|Δ%\| | frozen medΔ% | inverted med\|Δ%\| | inverted medΔ% |
|---|---|--:|--:|--:|--:|
| D2 | form 3 · ε_d | 7.7 [6.0, 9.3] | −5.1 [−7.6, −2.2] | 7.0 [5.4, 9.5] | −3.1 [−4.7, −1.1] |
| D2 | form 3 · ε_f | 4.7* [3.3, 6.2] | −0.9 [−3.3, +1.1] | 5.8 [4.9, 7.8] | −0.5 [−1.7, +2.4] |
| D2 | form 4 · ε_f | 3.9* [3.2, 6.1] | +1.0 [−1.6, +3.5] | 5.4 [3.2, 7.1] | +2.4 [−0.5, +6.1] |
| D2 | simulation | 6.6 [4.7, 8.7] | −3.5 [−6.4, −1.8] | 7.8 [4.7, 9.5] | −2.2 [−4.7, +1.4] |
| D3 | form 3 · ε_d | 5.8 [5.3, 6.4] | +4.3 [+3.1, +4.9] | 5.1 [4.6, 5.5] | −3.8 [−4.4, −3.2] |
| D3 | form 3 · ε_f | 10.1 [9.3, 10.7] | +10.0 [+8.8, +10.7] | **3.2 [2.7, 3.6]** | **+0.2 [−0.3, +0.7]** |
| D3 | form 4 · ε_f | 6.8 [6.0, 7.6] | +5.4 [+4.1, +6.6] | 4.8 [4.3, 5.2] | −3.0 [−3.6, −2.5] |
| D3 | simulation | 6.8 [6.2, 7.8] | +5.0 [+3.8, +5.9] | 5.7 [5.3, 6.2] | −4.6 [−5.2, −4.0] |
| D4 | form 3 · ε_d | 5.5 [4.4, 6.4] | −4.7 [−5.7, −3.7] | 6.0 [5.2, 6.5] | −5.2 [−6.2, −4.4] |
| D4 | form 3 · ε_f | 3.5 [3.1, 4.2] | +0.4 [−0.8, +1.2] | 3.1 [2.6, 3.3] | −0.4 [−1.2, +0.4] |
| D4 | form 4 · ε_f | 5.6 [4.8, 6.4] | −4.3 [−5.0, −3.3] | 6.4 [5.9, 7.0] | −5.3 [−6.1, −4.4] |
| D4 | simulation | 5.4 [4.9, 6.1] | −5.0 [−5.8, −4.3] | 5.8 [4.9, 6.5] | −4.9 [−6.0, −4.3] |
| D5 | form 3 · ε_d | 6.2 [5.6, 6.9] | −0.3 [−1.6, +0.6] | 7.5 [7.1, 8.0] | −4.0 [−4.7, −3.2] |
| D5 | form 3 · ε_f | 8.1 [7.3, 8.7] | +5.6 [+4.1, +6.6] | **5.3 [4.6, 6.1]** | **+0.9 [+0.3, +1.8]** |
| D5 | form 4 · ε_f | 6.9 [6.2, 7.5] | +3.8 [+2.8, +5.0] | 5.8 [5.3, 6.3] | −0.4 [−1.1, +0.3] |
| D5 | simulation | 6.1 [5.5, 6.7] | +0.1 [−0.9, +0.9] | 7.2 [6.7, 7.9] | −3.5 [−4.3, −2.6] |

Read jointly, the moves separate into three kinds. (i) *Genuine improvement* — D3 f3·ε_f:
accuracy 10.1 → 3.2 with the bias going +10.0 → +0.2 and the CIs disjoint; D5 f3·ε_f
8.1 → 5.3 with bias +5.6 → +0.9, CIs disjoint. The effective aero removes a real, signed
overcharge. (ii) *Bias substitution, not improvement* — D3 f3·ε_d's accuracy "gain"
(5.8 → 5.1) swaps a +4.3 bias for a −3.8 one, CIs of the biases on opposite sides of zero:
the over-refund replaces the overcharge, the Entry-29 cancellation pattern. (iii) *Within-CI
noise* — most D4 rows and the D2 column (thin coverage, population shift): accuracy CIs
overlap heavily, no call to make.

The headline is the **flat-ε row**: under fully automatic per-ride physics the ε_f law lands
at 3.2 / 3.1 / 5.3 on D3–D5 — on D3 a 10.1 → 3.2 collapse, with the frozen run's +10.0 bias
going to **+0.2** (D4 −0.4, D5 +0.9: near-zero bias on all three riders). Meanwhile the
ε_d rows *worsen* on D4/D5 (biases −3.8 / −5.2 / −4.0): with the effective (lower) α, ε_coast
shrinks and the frozen ε₀ = 0.13 over-refunds — precisely Entry 29's learning L2 (the deficit
estimate is conditional on ρ·C_dA) and Entry 34's constant-model conditionality, now visible
as a sign flip in the regime rule: **under inverted physics the flat constant beats ε_d on
every corpus, including the open terrain where ε_d won under frozen priors.** The regime
rule is a statement about a (physics, ε-variant) *pair*, not about ε alone.

**Pooled D3–D5** (stratified bootstrap, n = 1,296): f3·ε_d 6.3 [6.0, 6.6] · −4.2
[−4.5, −3.7]; **f3·ε_f 3.8 [3.6, 4.1] · +0.4 [−0.0, +0.8]**; f4·ε_f 5.7 [5.2, 6.0] · −2.4
[−2.7, −1.9]; simulation 6.4 [6.1, 6.7] · −4.3 [−4.7, −3.9]. Against the frozen pool's best
(5.9 [5.5, 6.2], form 3 · ε_d, bias +0.4): the automatic-physics flat-ε law is ~2 points
more accurate at the same near-zero bias, CIs disjoint.

**Why ε_f beats ε_d here — the (α, ε) pairing** *(Danilo: "the last mystery: why does ε_f
beat ε_d on Table 5?")*. In the law only the *pair* (α, ε) is identified by ride energies:
the refund exists to offset what the cost side charges, so the same measurements are fit by
(frozen α, ε ≈ 0.5) and by (effective α, ε ≈ 0.2) — and ε_bal itself is bookkeeping under an
assumed α (ε_bal = (αX₋ − E_legs)/(βH₋); only δ = E_legs/(βH₋) is physics-free, Entry 34).
ε₀ = 0.13 was calibrated so that ε_coast − 0.13 tracks ε_bal *as booked under the frozen
priors* — it anchors ε_d to the frozen pair. Table 5 hands the cost side the honest effective
α (ĈdA 0.26–0.29, drafting absorbed) but ε_d barely moves off its frozen anchor (ppaz median
0.54 → 0.49; the cap cushions ε_coast and α falls only ~15%), while the honest recovery at
effective physics is ≈ 0.20 — exactly what ε_f's near-zero bias certifies. The mismatch,
(ε_d − 0.20) ≈ 0.3 times a descent-energy share βh̃₋/E ≈ 15%, predicts a 4–6 pp
under-prediction — and the measured f3_d − f3_f bias deltas are −4.0 / −5.6 / −4.9 pp.
Cross-checks: JAAM never flipped because his ĈdA (0.391) ≈ the prior — his frozen pair was
already honest, and ε_f already beat ε_d in Table 3 (3.5 vs 5.5); the flip happens exactly
where ĈdA moved. And the fitted-physics gap shift (0.12 → 0.19, Entry 31) is the same fact
from the other side: re-pair the physics and ε₀ must be re-calibrated (Entry 29's L2, now
with its mechanism). The structural reason ε_d
*cannot* follow a cost-side change is a lever mismatch: the ε that matches a ride's energy
responds to an α error with lever x/(βH₋) (whole-ride distance per drop — ≈ 0.135 per newton
of α on D3, median x/H₋ ≈ 100), while ε_coast responds with lever x₋/(βH₋) ≈ 1/s̄ ≈ 0.04 per
newton — a ~3.5× mismatch. A −2 N α change (CdA 0.40 → 0.26) moves the matching ε by ≈ −0.27
but ε_d by only ≈ −0.05: the compensation ε_d was providing under frozen priors lived in the
wrong term, and no descent-geometry-only estimator can provide it. The regime rule of §3.2 is
therefore a statement about the frozen *pair* — carried to another physics, the ε variant
must be re-selected or ε₀ re-fit; and more fundamentally, ε should not be asked to absorb
cost-side error at all.

**P5 — parity persists (confirmed).** Law vs simulation within 0.6 pp of med|Δ%| on every
corpus, and the two engines' biases move together (both go negative under the effective
physics on D3–D5) — the Entry-30 lockstep at per-ride grain.

**P6 — subsets (confirmed, reported separately only).** Full-inversion subsets: D1 n = 19
f3_d 3.7 / canon 3.9 · D3 n = 106 4.6 / 6.2 · D4 n = 20 2.6 / 2.6 · D5 n = 56 4.6 / 4.2 —
better than their corpora, as selection toward mountainous well-measured rides predicts; not
comparable to corpus medians.

**The epistemic caveat (registered up front, restated with the result).** The inversion reads
each ride's own power stream and then scores models on that same ride — partially in-sample
*per ride*, a different question from frozen-prior transfer: "can the ride's telemetry replace
judgment and priors?" Answer: **yes for mass** (P1), **effectively for aero** (with drafting
folded into the constant — which is why it fixes the frozen run's D3 bias), **noisily for
C_rr** (coverage 33–146 rides/corpus, medians sane). For *prediction before the ride*, the
per-rider aggregates of these per-ride inversions (75.4 / 98.7 / 73.7 kg; effective ĈdA
0.26–0.39) are the transferable output.

Output: `perride_invert.csv` (1,409 rides, every constant's source flagged) + the geo/wind
caches. Gated: the four analogue-table rows × four corpora (medians + CI bands) and the four
m̂ medians, in `bootstrap_ci.py`.

---

## 2026-07-28 — Entry 32: review v3 — the un-gated numbers were exactly where the rot was

**Lineage** — $I$: — · $T$: review · $O$: no new $O$ · $S$: the un-gated numbers were where the rot was

*Prompt (Danilo): "do another review for quality", then "ok do it" on the consolidated findings.*

A third adversarial review (six lenses; five completed — the journal-fidelity lens stalled and
was spot-checked by hand instead) over the post-Entry-31 paper. No new *protocol* defects: the
dual-protocol design survived. What it found instead is a pattern worth recording as a
methodological lesson: **every number the review caught stale or irreproducible was a number
the gate battery did not cover.** The gated medians and CI bands were all clean; the rot lived
in Table 4's descent-RMS row, a real-descent count, a paired-test p-value, and prose claims
("statistically indistinguishable", "4–5 points", "exactly as predicted") that no script
re-derives. The fix was therefore twofold: regenerate + correct, and *extend the gates to the
class of number that failed*.

**Regenerations** (all from the current canonical/fitted CSVs, the same files every existing
gate passes on; method = the JAAM-gate convention: clean rides, ε_bal/ε_coast finite,
s̄ ≥ 3%, RMS of ε_bal − clamp01(ε_coast − 0.13) vs RMS around the corpus's own median ε_bal):

| statistic | was (stale vintage) | is (current) |
|---|---|---|
| D3 P. Paz assumed RMS pair | 0.091 vs 0.139 | **0.096 vs 0.145** (n = 161; margin 35% → 34%) |
| D3 P. Paz fitted RMS pair | 0.082 vs 0.086 | **0.085 vs 0.089** (still a statistical tie) |
| D4 JAAM assumed RMS pair | 0.091 vs 0.086 | **0.090 vs 0.085** (Entry 31's values; Table 4 had kept the old ones) |
| D4 JAAM fitted RMS pair | 0.089 vs 0.086 | **0.088 vs 0.085** |
| D5 author real-descent stats | "210 real descents", RMS 0.090/0.121 | **n = 221**, 0.092/0.126 (gap 0.14 unchanged) |
| P. Paz mass-sweep triple 70/74.5/78 kg | 0.096/0.091/0.088 | **0.101/0.096/0.092** (own-flat 0.153/0.145/0.139) |
| time model T1b vs T0 paired p | 0.011 | **0.0124** (243/433; endpoint p's now stated qualitatively) |

**New analyses the review forced.** (1) The *transfer-only* pool D3+D4 (n = 660, stratified
bootstrap, seeds 42/43): form 3 · ε_d **5.6 [5.2, 6.2]** (signed +1.1 [+0.4, +1.7]) vs
canonical **6.3 [5.8, 6.8]** (+1.3 [+0.6, +2.0]). The paper now leads with this as the
genuinely out-of-sample number and demotes the full D3–D5 pool (5.9 vs 6.2) to "with the
author's in-sample history added" — the reviewer was right that 48.5% of the old headline pool
was the calibration rider. (2) Per-corpus paired allegiance: on D3 the *law* is significantly
closer (280/441, p < 1e-4); on D5 the *simulation* is (351/621, p = 0.0013). Median parity
with opposite per-ride allegiances is the honest statement — "statistically indistinguishable"
was wrong on D5 and is retired everywhere a paired test can separate the engines.

**Claim repairs (no number change).** The informed→blind shift is form-specific
(+4.7 form 3, +3.2 simulation, +1.8 form 4; forms 1–2 *improve* blind via bias cancellation)
— "4–5 points moving both engines together" restated per-engine at all five sites, flagged
in-sample. H1 downgraded confirmed → supported (frozen protocol moves the deadband's
contribution to the bias; equivalence never formally tested). "Exactly as the Entry-30 sweep
predicted" weakened to consistency (Entry 30's registration excluded D1). Mass exempted from
the "judged" list everywhere (it is logged, identical in both runs — it buys none of the
informed-blind gap). §3.1's First/Third/Second enumeration reordered. A.4's noise rate
3.2 → 3.1. Scale reconciliation: §2.4 now states which constant lives at which scale
(c, τ on the 5 m profile; ε₀ on 30 m descent cells = the deployment scale). Fig 3 rewired
(E_meas → accuracy arrow was missing); Fig 4 now draws the informed primary comparison
*outside* the frozen chain and credits ε_f to D2.

**The ε_d clamp removed (Danilo: "it is adding nothing for us").** The ride-level
dynamic estimator is now ε_d = ε_coast − ε₀, *unclamped* — in `eps_geom`
([`engines.py`](../../src/bicycling_energy_model/engines.py)), the applet mirror, the
compare-harness RMS predictors, `param_sweep.py`, the gate battery, the paper, the spec
(`original_notes.md`) and `claims.ttl`, together. Justification measured, not assumed: the
top half is inert by construction (ε_coast ≤ 1 ⇒ ε_d ≤ 0.87) and the floor never fired on
any measured ride — min ε_coast per corpus 0.270 (D3), 0.309 (D4), 0.142 (D5), and D1's
stored ε_d never reached 0 — so removal is provably drift-free at the ride level:
`longoes_frozen.csv` and `censo_comparison.csv` regenerate **bit-identical**, and the full
gate battery passes unchanged. Two deliberate survivors: the **per-edge** v2Edge floor
(sampasimu / applet edge realisation / `r1d_v2_edge`) stays — single 30 m edges beyond
s_*/ε₀ ≈ 15% are common even where ride means are not, so there the floor is model content —
and Entries 8/10's exploratory harnesses (`eps_hypothesis.py`, `eps_sp_test.py`) keep their
explicitly-labelled clamped variants as historical record. The sweep corners: Entry 29's
registration ran clamped; re-run unclamped the anchor gates still pass (the anchor never
clamps), and only implausible low-ρC_dA corner cells can differ — Entry 29's published grid
keeps its as-written values, per the journal convention. Also this session: the paper renamed
`paper.md` → `paper1-closed-form.md`, and a second paper scaffolded
([`paper3-edge-cost.md`](../../research/article/paper3-edge-cost.md)) for the edge-cost
discretization question, where the clamp asymmetry is registered as a pitfall.

**Gate extensions** ([`bootstrap_ci.py`](../../src/harness/bootstrap_ci.py), all passing):
the three descent-RMS pairs (D3/D4/D5, n + both RMS values, tol 0.002), the D3/D5 allegiance
sign tests (printed), the transfer-only pooled medians + CI bands, and the time-model paired
test (243/433, p = 0.012). The paper's "gate script" sentence rescoped to what is actually
gated. Lesson, stated once: *a review lens aimed at "numbers the gates don't cover" is worth
more than three aimed at the gated ones.*

---

## 2026-07-28 — Entry 31: the D1 protocol correction — frozen re-run, the D2∩D5 discovery, and the review-v2 response

**Lineage** — $I$: $(D_1, P_{a,g})$ · $T$: F1–F4, $F_\mathrm{base}$ · $O$: `longoes_frozen.csv` (44) · $S$: **Table 2's blind block**; the D2∩D5 discovery

*Prompt (Danilo): a second adversarial review over the rewritten paper; on its blocking finding
B1, "re-run (b)"; beyond that, "do all fixes and improvements".*

A six-lens adversarial review of the IMRAD paper (verification consolidator re-computing every
disputed number from the repo's own data) returned 3 blocking / 20 important / 13 polish
findings. The three blocking ones each changed published numbers or claims; this entry records
them and the re-runs they forced.

**B1 — Table 2's protocol was not what the paper claimed.** `compare.py` scores every D1
approximate form with the longões sheet's hand-entered per-ride ε and per-ride sheet physics
(m/Crr/CdA/ρ/k_eff/wind per ride) — the monolith disclosed this; the IMRAD compression dropped
the disclosure and then §2.3 asserted the frozen literature-typical protocol corpus-wide.
Decision: **re-run D1 under the frozen protocol** ([`longoes_frozen.py`](../../src/harness/longoes_frozen.py):
Crr 0.008 / CdA 0.40 / ρ 1.13 / k_eff 0.98 / wind 0; mass = the per-ride logged system mass,
the one legitimate per-rider input; v_f from extracted flat power; ε frozen to ε_d or ε_f).
The new D1 scoreboard (44 rides, conservation ≤ 1.5e-08):

| model | med\|Δ%\| [95% CI] | medΔ% [95% CI] |
|---|--:|--:|
| form 1 · ε_d | 14.9 [10.6, 22.6] | +14.0 [+10.2, +22.5] |
| form 2 · ε_d | 7.9 [5.5, 13.6] | +4.9 [+0.9, +10.9] |
| form 3 · ε_d | 8.2 [4.5, 10.8] | +2.2 [−2.5, +4.5] |
| form 4 · ε_d | 7.6 [5.6, 11.6] | −0.5 [−5.0, +3.7] |
| form 3 · ε_f = 0.20 | 9.2 [7.0, 13.3] | +7.8 [+3.1, +12.5] |
| form 4 · ε_f = 0.20 | 7.9 [5.9, 11.8] | +3.6 [+0.8, +9.2] |
| canonical | 8.4 [5.1, 10.9] | +2.5 [−1.6, +7.1] |

Paired: form 2 beats form 1 on 37/44 (p < 1e-4); form 3 vs canonical 22/44 (**p = 1.00** —
parity, exactly); form 4 vs canonical 17/44 (p = 0.17). Sustained-climb balance under frozen
physics: 2,535 sections, 41,790 vs 43,979 kJ, **ratio 0.95**.

**What moved and what did not — and the reframe (Danilo).** The sheet run is not flattery: it
is an *informed-parameters* run — per-ride best guesses: literature-anchored values adjusted by
the author's judgment of each ride's wind, surface (paved/unpaved → C_rr) and loadout, plus a
hand-chosen per-ride ε (which shades into per-ride fitting). Its 3.5% (simulation 5.2%) is what
the law achieves with condition-informed judgment; the frozen 8.2% (simulation 8.4%) is what it
achieves blind. The difference, ≈ 4–5 pp on both engines at once, is the measured value of that
judgment over a single constants-fit-all set. **Hierarchy decision (Danilo): the paper
calibrates against the informed run — useful beats blind for the study's purpose — with the
frozen run as the coherence check and the choice owned in the paper's §4.3;** both runs are
first-class in Table 2 and both are gated — consistent with the Entry-29/30 sweeps (parameters
move absolute error at the several-pp scale, in lockstep) and a direct motivation for the
measured-constants route of the paper's §4.4. Fully frozen, D1 becomes the HARDEST corpus
(long, wind-exposed brevets are where zero-wind generic constants bite hardest). The paper's core claims survive intact: parity is
p = 1.00, the attribution ladder still stands (the split remains the dominant fix,
14.9 → 7.9; the deadband's contribution shifts from the median to the bias, +4.9 → +2.2),
and Tier B's Q2 (both engines move in lockstep) is what predicted this shape. The old
compare.py numbers remain valid AS the informed-parameters run (kept, still gated); the paper
publishes BOTH runs in its Table 2, informed as the calibration headline (see the hierarchy
decision below) and frozen as the blind coherence check.

**B3 — D2 is not disjoint from D5.** An exact activity-level join (energy ±1%, distance ±2%)
matches **58 of the 62 clean censo rides to clean D5 rides** — the censo recordings are
overwhelmingly the author's own device on collective rides, re-evaluated under the
generic-rider assumption. Unique rides = 1,387 − 44 (D1 ⊂ D5) − 58 = **1,285**, not the 1,343
the paper's title carried. Disclosed in §2.3; title/abstract/Conclusions recounted.

**Regenerated in one pass (review items I3/P3/I16).** JAAM real descents (s̄ ≥ 3%): n = **21**
(not 20), frozen-ε_d RMS **0.090** vs frozen-flat 0.111, difference −0.020 [−0.070, +0.024],
own in-sample best flat (0.28) RMS **0.085** — the paper had stitched two vintages. Gap
convention fixed as med(ε_coast) − med(ε_bal) with bootstrap CIs: P. Paz 0.12 [0.10, 0.14],
JAAM 0.13 [0.10, 0.19], author-full **0.14 [0.12, 0.16]** (the published 0.13 was 0.37 − 0.24
on pre-rounded medians), P. Paz fitted 0.19 [0.17, 0.20], JAAM fitted 0.12 [0.10, 0.17].
Fitted-physics law medians for the paper's Table 4: P. Paz sm·ε_d 7.0 [6.2, 7.6]
(−6.2 [−7.1, −5.3]), JAAM 4.7 [4.0, 5.7] (−3.5 [−4.6, −2.8]).

**The noise rate, regenerated and evidenced.** The paper asserted c's provenance ("measured
3.2 m/km, IQR 2.7–3.8") without in-paper evidence (Danilo's catch). Recomputed under the
current pipeline: **3.1 m/km median, IQR 2.6–3.7** (44 rides; raw − deadband h₊ per route-km;
pure geometry, so G-independent — the small drift from Entry 5's 3.2 is pipeline vintage).
Now measured in `longoes_frozen.py` (per-ride `noise_rate` column), gated in `bootstrap_ci.py`,
and stated as §3.1's third attribution check.

**Other review corrections applied to the paper** (the full list lives in the review record):
the deficit's causal story corrected to descent pedalling + clamp effects (braking cancels out
of ε_bal — the paper's own A.5 algebra); the per-segment balance's dropped ΔKE term stated;
the s sign convention (magnitude in descent formulas) declared; wind added to the constants
table (0 for D2–D5, per-ride logged on the old D1 run); the "3.5–6.2% on every corpus" range
rebuilt from frozen-only numbers; form 4's fourth input (the climbing-distance fraction)
disclosed; ε = 0 over-prediction qualified to form 3; acronyms expanded; fig1 relabelled to
the paper's form vocabulary; sweep-paragraph rewritten to name all six predictions.

---

## 2026-07-27 — Entry 30: pre-registration — Tier B: the canonical simulation under the sweep

**Lineage** — $I$: $(D_2..D_5, P_{a,g} \times \mathrm{grid})$ · $T$: $F_\mathrm{base}$ under the same sweep · $O$: `param_sweep_canon.csv` (48) · $S$: Tier B

*Prompt (Danilo): "let's do tier b".*

Entry 29 swept the closed forms; the canonical simulation was deferred because it is the
expensive engine (a distance-marching integration per ride per combination). This entry
registers Tier B before results.

**Design.** One-at-a-time around the anchor, leaning on Entry 29's exactly-confirmed ρ·CdA
degeneracy (the simulation's drag term also carries ρ and CdA only as their product): the CdA
axis {0.25 … 0.50} at Crr 0.008, the Crr axis {0.004 … 0.014} at CdA 0.40, ρ fixed at 1.13 —
11 distinct combinations plus one equal-product degeneracy-check partner (CdA = 0.40·1.13 at
ρ = 1.00). Corpora **D2–D5**, mass re-inverted per combination exactly as Tier A. **D1 is
excluded, by scope correction to Entry 29's "Tier B (… D1)":** the longões pipeline feeds
per-ride *sheet* physics (each ride its own m/Crr/CdA/ρ), so there is no shared-constant
anchor to perturb — the corpus asks a different question than this sweep.

**Implementation.** `SWEEP_CANON=1` mode of `param_sweep.py`: the reduction pass additionally
keeps each ride's resampled profile and regime powers; each combination then runs
`canonical()` per ride. Same order-statistic CIs on med|Δ%| and med Δ%; same gates (anchor
canonical medians vs the published 6.6 / 6.8 / 5.4 / 6.1; CI-method cross-check; degeneracy
pair ≤ 1e-9 pp). Output `param_sweep_canon.csv`.

**Pre-registered predictions.**
- **Q1 (degeneracy):** the canonical simulation depends on ρ and CdA only through ρ·CdA —
  the equal-product partner matches the anchor to numerical precision.
- **Q2 (paired stability — the design principle, quantified):** because both engines read the
  same constants, the *model-vs-model* gap is much less parameter-sensitive than either
  model's absolute error: across the OAT range, the spread of (canonical med|Δ%| − form-3
  med|Δ%|) is less than half the spread of canonical med|Δ%| itself, per corpus.
- **Q3 (bias monotonicity):** canonical signed bias rises monotonically along both axes
  (more assumed resistance → more predicted energy) on every corpus.
- **Q4 (comparable magnitude):** the canonical error's sensitivity is the same order as the
  closed forms' — the constants, not the engine, set the sensitivity scale.

### Results (appended after the registration above was frozen)

All gates pass: anchor canonical medians reproduce the published 6.6 / 6.8 / 5.4 / 6.1, anchor
m̂ exact, CI methods converged, and 48 rows landed in `param_sweep_canon.csv`.

**Q1 (degeneracy) — CONFIRMED, bitwise.** The equal-product partner matches the anchor to
|Δmed| = 0.00e+00 on every corpus (the partner passes CdA = 0.40·1.13 as the same float, so
the products are identical bit patterns and the whole integration reproduces exactly).

**Q2 (paired stability — the design principle quantified) — CONFIRMED, decisively.** Across
the OAT range, spread of (canonical med|Δ%| − form-3 med|Δ%|) vs spread of canonical med|Δ%|:
censo 3.0 vs 8.5 pp (ratio 0.36), P. Paz 0.8 vs 6.8 (0.11), JAAM 0.8 vs 11.7 (**0.07**),
author-full 1.1 vs 3.5 (0.31). On the transfer riders the model-vs-model comparison is
**9–14× less parameter-sensitive** than either model's absolute error — the shared-constants
design (§2.1 of the paper) measured, not asserted.

**Q3 (bias monotonicity) — CONFIRMED, 8/8 axes.** Canonical signed bias rises monotonically
along both axes on every corpus (e.g. JAAM CdA-axis −15.0 → +0.5; censo Crr-axis
−12.9 → +11.5). The anchor sits mid-ladder everywhere, its residual biases (+5.0 / −5.0 / …)
small against the axis span.

**Q4 (comparable magnitude) — CONFIRMED.** Canonical spreads 3.5–11.7 pp vs form-3 spreads
2.9–11.0 pp over the same cells — same order, form 3 slightly wider on the censo, canonical
slightly wider elsewhere. The constants, not the engine, set the sensitivity scale.

**Reading.** Tier B closes the sweep's loop: absolute accuracy is parameter-limited at the
several-pp scale for BOTH engines, in lockstep — which is precisely why the paper's paired
conclusions (parity, the regime rule, the deficit's recurrence) survive parameter excursions
that move the absolute numbers by ±6 pp. Four-for-four on Tier B predictions vs two-for-six
on Tier A is itself informative: what we understand well is the machinery's structure; what we
understood less well (Tier A's P2/P5/P6) was where the *data* gets to talk.

## 2026-07-27 — Entry 29: pre-registration — the physical-constants sensitivity sweep (CdA × Crr × ρ)

**Lineage** — $I$: $(D_2..D_5, P_{a,g} \times \mathrm{grid})$ · $T$: F3, $C_dA \times C_{rr} \times \rho$ · $O$: `param_sweep.csv` (432 corpus×combination) · $S$: the sensitivity envelope

*Prompt (Danilo): scope a parameter sweep over CdA ∈ [0.25, 0.50] step 0.05, Crr ∈ [0.003, 0.015]
step 0.002, ρ ∈ [1.0, 1.225] step 0.05; pre-register it; add 95% CI bands for the absolute median
error; implement Tier A.*

Motivation: the paper (§2.3, §4.4) defends the literature-typical priors (CdA 0.40, Crr 0.008,
ρ 1.13) with an anti-circularity argument and names a systematic sensitivity map as the cheap
next step — §3.4's mass sweep and fitted-physics rerun are two isolated points of that map.
This entry registers the map's design **before** looking at any result.

**Grid.** Simplified from the prompt's rough suggestion so every anchor is a lattice point:
CdA {0.25 … 0.50 step 0.05} (6, prior 0.40 on-grid); Crr {0.004 … 0.014 step 0.002} (6, prior
0.008 on-grid); ρ {1.00, 1.13, 1.225} (3 — the prior plus the physical extremes; the axis is
predicted exactly redundant by P1, so three points suffice to *test* that) → **108 combinations**. Mass is
**re-inverted per combination** (the self-consistent mode: m̂ uses the same constants, so the
sweep measures the deployable system, compensation included); a frozen-mass mode
(`SWEEP_FREEZE_M=1`) isolates the direct effect on demand.

**Tier A scope** (this entry): the closed forms (form 3 = deadband, form 4 = scalar) under both
frozen ε rules (dynamic ε_d, flat ε_f = 0.20) plus the ε machinery (ε_bal, ε_coast, the deficit
gap on s̄ ≥ 3% — D3–D5 only; the censo harness has no descent-balance cells), on **D2 censo,
D3 P. Paz, D4 JAAM, D5 author-full** — the four corpora sharing the manifest pipeline. D1 and the canonical simulation are Tier B (one-at-a-time around the
prior; separate entry). Implementation: per-ride **aggregates extracted once** (X, x_aero,
h± raw/smoothed, k_smooth geometry, regime powers, measured flat speed, the 30 m descent-cell
(drop, grade) lists, and the climb-balance sums e_meas/Σdh/Σcos·L/Σv²L), then each combination
is arithmetic — no per-combo harness reruns. The physical floor stays combo-dependent (β moves
with m̂), so the clean-ride count n may vary by combination and is recorded.

**CI bands.** Every med|Δ%| (and the gap median) carries a 95% CI. For ~10⁴ cells the seeded
mulberry32 bootstrap is not computable in stdlib time, so the sweep uses the **exact
order-statistic (binomial-rank) CI for the median** — distribution-free, deterministic, RNG-free.
Deviation from the repo's bootstrap convention is deliberate and **gate-checked**: the smoke gate
recomputes one anchor cell with the mulberry32 bootstrap and asserts the two intervals agree
within 0.3 pp per bound.

**Pre-registered predictions.**
- **P1 (degeneracy, exact):** ρ and CdA never appear separately anywhere in Tier A — only as
  the product ρ·CdA (aero rate, ε machinery, mass inversion's e_aero). Cells with equal
  (ρ·CdA, Crr) must agree to float precision; the sweep is effectively 2-D. Registered as a
  falsifiable internal-consistency gate, not just an observation.
- **P2 (deficit robustness):** the measured gap med(ε_coast − ε_bal) stays within ≈ 0.10–0.19
  across the physically plausible box (the §3.4 fitted-physics excursion bounds it); a
  systematic drift beyond that range would qualify the constancy hypothesis further.
- **P3 (verdict boundary):** the dynamic-vs-flat RMS verdict on D3 flips from win to tie as
  ρ·CdA falls toward P. Paz's fitted 0.26 — the Entry-16 mechanism, now as a boundary in the
  map rather than two points.
- **P4 (mass compensation):** re-inverted m̂ falls as ρ·CdA rises (the inversion assigns less
  of the measured climb energy to aero's complement); m̂·g stays the meaningful invariant and
  the energy-law medians move much less than the constants do.
- **P5 (interior optimum, Danilo):** the median error rises as any parameter moves to the
  extrema of its range — operationally: for each corpus × variant, med|Δ%| at every grid
  extremum (one axis at its end, the others at the anchor) is ≥ its anchor value.
- **P6 (common minimizer, Danilo):** there is a parameter choice that minimizes the error
  across all models simultaneously — operationally: some single (ρ·CdA, Crr) cell lies within
  the 95% CI of every variant's own grid minimum, per corpus.

*(P5–P6 were added after the harness was implemented and its smoke gates ran, but before any
full-run result was inspected.)*

**Outputs & gates.** `data/results/param_sweep.csv` (one row per combination × corpus:
m̂, n_clean, med|Δ%| + CI + signed for sm/pm × ε_d/ε_f, gap median + CI, median s*, median v_f).
Both modes assert the CI-method cross-check (≤ 0.3 pp per bound at n ≥ 150; the order
statistic's known conservative gap is allowed below that) and the P1 degeneracy identity on
an off-grid equal-product pair (float precision). The FULL run additionally asserts the anchor
m̂ (74.5 / 101.9 / 74.7 ± 0.15) and all 16 anchor med|Δ%| against the published gate-battery
values (± 0.11) — end-to-end parity with the shipped harnesses. `SWEEP_SMOKE=1` runs a
40-ride, 3-combination subset with published masses forced (a subset cannot re-invert mass).

### Results (appended after the pre-registration above was frozen)

All gates pass: anchor m̂ reproduces 74.5 / 101.9 / 74.7 exactly (0.1 kg print precision), all
16 anchor med|Δ%| match the published gate-battery values, the CI methods agree at production n
(e.g. P. Paz sm·ε_d: order-stat [5.29, 6.37] vs bootstrap [5.29, 6.36]), and 432 rows landed in
`param_sweep.csv` (with 95% CIs on both med|Δ%| and med Δ%, per the prompt).

**P1 (ρ·CdA degeneracy) — CONFIRMED, exact.** Equal-product off-grid pair agrees to
≤ 4 × 10⁻¹⁴ pp on every corpus. The sweep is 2-D: (ρ·CdA, Crr).

**P2 (gap 0.10–0.19 across the box) — REFUTED over the full grid.** gap_med spans
−0.065 … +0.188 (P. Paz), 0.001 … 0.180 (JAAM), 0.011 … 0.184 (author-full). The gap rises
monotonically with ρ·CdA (it is α-driven); it stays in the predicted band only near the
plausible mid-box. The deficit's *value* is parameter-conditional — stronger than §3.4's
two-point version of the same statement; its positivity (recurrence) holds everywhere except
the implausible low-ρ·CdA corners of one corpus, where the per-cell clamp lets ε_coast dip
below ε_bal.

**P3 (D3 verdict boundary) — CONFIRMED.** The dynamic estimator beats the in-sample flat
constant on 95/108 cells for P. Paz (anchor 0.091 vs 0.139) and loses exactly where predicted —
the low-ρ·CdA corner (0.097 vs 0.076); JAAM stays at tie-or-lose on most of the grid (dyn wins
35/108), the author-full 94/108. The Entry-16 two-point flip is a smooth boundary in ρ·CdA.

**P4 (mass compensation) — CONFIRMED.** m̂ falls with ρ·CdA: 77.3 → 72.0 kg (P. Paz),
104.5 → 100.5 (JAAM), 76.5 → 73.3 (author) as ρ·CdA goes 0.25 → 0.61 at Crr 0.008 — a ±3 kg
compensation against ±60% parameter excursions, while the law's medians move only a few pp.

**P5 (interior optimum, Danilo) — REFUTED, 29 violations.** Errors do NOT rise toward every
extremum: variants with signed bias at the anchor improve when the constants move against the
bias. Cleanest examples: P. Paz sm·ε_f improves 10.1 → 5.8 at CdA 0.25 (its +10 over-prediction
shrinks); JAAM pm·ε_d improves 9.0 → 3.6 at Crr 0.014 (its −8.4 under-prediction fills in);
censo sm·ε_d improves 7.7 → 5.4 at CdA 0.50. The anchor is not an error minimum — it is the
literature-typical prior, and the sweep now quantifies what that costs (~1–2 pp of median error
versus each variant's in-grid best).

**P6 (common minimizer, Danilo) — REFUTED as a universal claim.** Per corpus, cells lying
within every variant's min-CI: censo 3, P. Paz 1, JAAM 0, author-full 0. And the per-variant
minima sit in *different corners for different corpora* (P. Paz pm·ε_d at ρ·CdA 0.25/Crr 0.014;
JAAM's minima near ρ·CdA 0.45–0.57): no single parameter choice minimizes error across models,
let alone across riders. This is the sweep's sharpest lesson: per-variant, per-rider tuning
could buy ≈ 1–2 pp of median error, but there is no consistent "better constants" direction —
the gains are signed-bias cancellation, exactly the circularity §2.3 of the paper declines.

**Reading.** The error surface is shallow (per-variant grid minima 3.5–6.1% vs anchor values
3.5–10.1%); the constants matter at the pp level, not the factor level; and the quantities that
were *supposed* to be parameter-robust behave as claimed (recurrence of a positive gap,
anchor-region verdicts), while the quantities §3.4 already flagged as parameter-sensitive (the
gap's value, the dynamic-vs-flat margin) are confirmed to be so, now as continuous maps rather
than point pairs. Tier B (canonical, one-at-a-time; D1) remains open.

**Learnings (Danilo's summary, refined).**
1. **The mass inversion is robust — because it compensates.** ±3 kg of output against ±60%
   parameter excursions; m̂ absorbs what the aero term over/under-claims, so m̂·g keeps doing
   invariant-preserving work and the law's medians barely move.
2. **ε₀'s *value* is conditional on ρ·CdA; its *existence* is not.** The gap is monotone in
   ρ·CdA, so "0.13" means "at the literature-typical prior, at the 30 m scale"; the
   unconditional fact is a positive, near-common gap recurring across riders over the
   plausible box.
3. **In-data tuning of Crr/CdA is bias laundering.** The apparent gains are signed-bias
   cancellations pointing in different corners for different riders and variants — no common
   better direction exists. The clean escapes bring *external* information: direct measurement
   (weighed mass, bench Crr, measured CdA, logged ρ) or, weaker, temporally held-out fitting.

---

## 2026-07-25 — Entry 28: one implementation to rule the harnesses — dedup, package rename, layout

**Lineage** — $I$: — · $T$: package refactor · $O$: no $O$ · $S$: one implementation for all harnesses

*Prompt (Danilo): reduce code duplication on harness/ — "the canonical model is implemented
7× over the code"; make the codebase cohesive; we don't have a debt to the past. Plus a
folder restructure: src/, research/journal/, data/inputs|results/, drop the JS parity relics.*

**What was true.** The "two places" rule (bem + applet) had rotted: `canonical` existed 7×,
`build_profile` 7×, `pts_from_fit` 8×, `parse_fit` **12×** (in 7 drifted variants), plus
six helpers (`is_finite` ×13, `jsdiv` ×7 in 4 phrasings, `approx_components` ×6,
`extract_regime_powers` ×6, `push_stats` ×5, `climb_balance` ×5). The drift was benign —
AST-normalised clustering showed the engine copies byte-identical and the parser variants
differing only by additive features (cadence, file_id manufacturer, sport) — but only a
measurement could say so.

**Method (the part worth reusing).** No copy was deleted on inspection alone:
(1) AST-normalised clustering to count *distinct implementations* rather than copies;
(2) a union implementation in the package (`parse_fit(buf, meta=None)` collecting
manufacturer/sport; points always carry `cad`);
(3) **bit-identical equivalence proven on real rides before any deletion** — 132/132
file-comparisons across all 11 parser variants; `canonical`/`build_profile`/`pts_from_fit`
byte-equal outputs incl. the `phys_profile` arrays, per donor family;
(4) mechanical swap, then the fast harnesses + the full `bootstrap_ci` gate battery re-run
green (conservation residual unchanged at 1.77e-8).
Two deliberate copies remain and are documented: `r1d_v2_edge` (the deployed-sampasimu
v2Edge mirror) and `extract_coords`' reduced parser. One transcription slip (a dropped
`isinstance(x, bool)` guard in the shared `is_finite`) was caught by three independent
review agents — verified unreachable at every call site before being restored.

**Also retired.** `v8math.py` (459 lines of fdlibm trig kept only for V8 bit-exactness,
which the re-baseline dropped) — in passing, its `Number::ToString` port turned out to
have a latent spec bug for integers in [2⁵³, 1e21), never reachable from real outputs; the
replacement (`repr`-based ECMA-262 rendering in `jsfmt`) matches real V8 on 10⁶ random
doubles including that range. `param_fit`'s hand-rolled fdlibm `pow`. The JS parity
harness (`analysis/parity/`) — its job (proving the Python port equals the retired JS) is
done and archived in git history; the binding checks are now `bootstrap_ci.py` plus each
harness's sanity-gate block. `jsdiv` was *not* retirable: ~40 call sites divide by
legitimately-zero quantities and rely on ±inf/NaN flowing into medians/filters — it is now
one documented shared function instead of seven.

**Layout.** `analysis/bem` → `src/bicycling_energy_model/`; `harness/` → `src/harness/`;
journals → `research/journal/`; `notas.md` → `research/notes/original_notes.md`;
`data/activities` → `data/inputs/activities`, `results/` → `data/results/`;
`make_claims_explorer.py` → `research/scripts/`. Gravity now lives in ONE Python place
(`bicycling_energy_model.engines.G`, imported by every harness); the applet remains the
deliberate JS mirror. Net (the dedup itself, measured before the file-move renames):
**~7,460 lines removed against ~2,405 added** across `analysis/bem` + `harness/` + `applet/`,
zero behavioural change, gates green before and after.

Tooling: `harness-dedup` + `harness-dedup-wave2` workflows (18 + 13 agents), equivalence
scripts inline; verification = compare/censo/eps×2/bootstrap_ci re-runs + the DEM chain's
own sanity gates.

---

## 2026-07-25 — Entry 27: re-baseline — São Paulo's gravity, bisect back in `bem`, and V8-exactness retired

**Lineage** — $I$: — · $T$: $G$ = 9.7864 re-baseline · $O$: every $O$ regenerated · $S$: ≤ 0.2 pp; **$\hat m \cdot g$ is the invariant**

*Prompt (Danilo): "G=9.7864 is a standard value for são paulo, according to lab measurements at
IAG-USP" → "note: we can drop the requirement of being v8-exact. We can also revert to bisect if
there's benefit to it." → "re-baseline approved". This entry is the bookkeeping of a
constants-only change: **no model, harness logic or corpus changed**, so every number that moves
here moves for exactly one reason (gravity), and the entry's job is to show which ones did.*

**The change, in three parts.**

1. **`G = 9.7864` replaces 9.81** — São Paulo's local gravity from IAG-USP absolute gravimetry.
   Every corpus in this repo is ridden in the SP metropolitan region, so the local value is the
   physical one. It is hand-copied into **14 sites**: `bem/engines.py`, `applet/index.html`,
   `analysis/journal.qmd`, the parity preamble in `js_runner.mjs`, and the `G` / `KEFF, G` /
   `G, NS` line of each of the eleven harnesses. **This was also a latent correctness fix**: a
   harness defines `G` locally *and* imports `bem`'s engines, so the half-applied working-tree
   state (bem at 9.7864, harnesses at 9.81) had been running **two different gravities inside a
   single computation**. Three sites keep 9.81 **deliberately** and now say so in-line —
   `verify_v2edge_clamp.py`, `e26_detour.py`'s `G_JS`, and the frozen `reference.mjs` header —
   because they mirror the bundle *sampasimu deploys*, and that repo is not re-based.
2. **`flat_eq_speed` reverts from a Cardano closed form to the applet's monotone-safe bisection**,
   mirrored step for step (same bracket, same 60 halvings, tailwind fallback branch), and
   `solve_cubic` is deleted. Three wins: **numpy is gone, so `analysis/` is stdlib-only again**
   (verified by importing `bem` under the system python3, which has no numpy); the
   applet↔`bem` two-copy rule holds again; and a wrong code path disappears — the committed
   Cardano returned `-q/2 + √delta` instead of the cube-root sum and never shifted back from the
   depressed cubic. 60 halvings on [0, 40] already resolve v to ~3e-17, so the closed form bought
   nothing measurable.
3. **V8-exactness is no longer a required invariant.** `v8math` stays (it is correct; removing it
   would be churn with no benefit) but a last-ulp difference in a printed digit is no longer a
   defect. The binding cross-language check is now the *numerical* parity — which **passes
   unchanged: 8 514 comparisons, ≤1e-9 relative, against the frozen verbatim JS**, with both
   sides at the new G. That parity result is also the strongest evidence the bisect revert was
   right: the frozen JS bisects, so Cardano would have shown up as a divergence.

**Direction of the change, predicted before running.** `β = mg/k_eff` falls by 0.24%, and `α`
falls only through its rolling part, so every model charges slightly less for climbing. Variants
that **over**-predict should improve; the **under**-predicting canonical should worsen. That is
exactly what happened, and nothing moved by more than 0.2 pp.

### What moved (and what did not)

**Longões (44 rides), med |Δ%| / med Δ%:**

| model | before | after |
|---|--:|--:|
| **champion** (cf + 2 m deadband) | 3.6 / +2.2 | **3.5 / +2.1** |
| canonical | 5.1 / −1.7 | **5.2 / −1.8** |
| canonical + 2 m | 5.6 / −3.5 | **5.7 / −3.6** |
| cf + scalar `k_smooth` | 5.8 / −0.5 | **5.9 / −0.6** |
| cf + sheet `v_f` | 7.2 / −0.5 | 7.2 / **−0.6** |
| cf + measured `v_f` | 8.2 / +6.7 | **8.0 / +6.6** |
| cf | 8.7 / +8.6 | **8.6 / +8.4** |
| off + 2 m | 10.2 / +9.9 | 10.2 / **+9.8** |
| off (baseline) | 19.3 / +19.3 | **19.1 / +19.1** |

Conservation identity unchanged at **1.77e-8** worst per-ride residual (bar: 1e-6).

**Censo (62 clean urban rides):** canonical 6.5 → **6.6**; smooth ε=0.10 4.5 → **4.4**; ε=0.15
5.0 → **4.8**; ε=0.20 4.6 → **4.7**; ε=geom 7.6 → **7.7**; ε=0.00 7.6 → **7.4**; poor-man's
ε=0.20 **3.9 (unchanged — the censo headline holds)**; ε=0.25 4.8 → **5.0**; ε=geom 6.3 → **6.4**;
ε=0.00 10.5 → **10.4**.

**The rider corpora did not move at all** — P. Paz poor-man's ε_geom **4.9 / +0.6**, canonical
**6.8 / +5.0**, smooth ε=0.20 **10.1**, and the frozen-ε result **RMS 0.091 vs the in-sample
flat 0.139** (the ~35% win) are identical to four significant figures; JAAM smooth ε=0.20
**3.5 / +0.4**, ε=geom **5.5**, canonical **5.4 / −5.0** likewise; the author's full export keeps
canonical **6.1** (bias +0.1 → **+0.0**) and frozen-ε **0.090**.

**Why that split is the interesting part.** Where mass is **inverted from the data**, the gravity
change lands in the *parameter* and leaves accuracy untouched: implied mass rises by exactly the
predicted 1/G ratio — P. Paz **74.3 → 74.5 kg**, JAAM **101.7 → 101.9**, the author **74.5 →
74.7** (and Entry 15's climb masses likewise). Where mass is **assumed** (the longões' sheet
parameters, the censo's generic 78 kg), there is no free parameter to absorb it, so the shift
shows up in med |Δ%| instead. A one-line summary of the whole re-baseline: *a fitted corpus is
gravity-insensitive; an assumed corpus is not.*

**The ε closed form is untouched.** Correlations 0.30 / 0.60 / 0.77 / 0.82 (all / energy-weighted
/ s̄≥3% / s̄≥3.5%), the part–whole diagnostics 0.72 and 0.99, and the headline **37% RMS reduction**
(RMS 0.08 vs a flat baseline's 0.13 at s̄ ≥ 3%) are all bit-for-bit the published values, because
`ε_coast = min(1, (α/β)/s)` depends on gravity only through the aero term's `mg` denominator.

**Two claims move, in opposite directions.**

- **Entry 22's "parity, not beats" gets STRONGER.** Paired, the champion is now closer than the
  canonical sim on **24 of 44 rides (55%), sign test p = 0.65** (was 25/44, 57%, p = 0.45) — even
  less separable, so the article's parity wording is now conservative rather than borderline. The
  other four paired tests are identical (censo 33/62 p = 0.70; P. Paz 265/441 and 331/436;
  JAAM 140/215, all p < 10⁻⁴).
- **§8.5's São Paulo transfer weakens from a tie to a near-tie.** The frozen rural offset
  `ε_coast − 0.13` now scores **RMS 0.09** against the in-sample flat ε = 0.20's **0.08** (both
  were 0.08). The refutation it supports is unaffected — the mechanistic braking correction still
  sits at 0.19, worse than a constant, and every R² stays ≤ 0.14 — but the sentence "it *ties* the
  flat constant selected in-sample on this very set" must now read "*nearly* ties (0.09 vs 0.08)".

**Time model: headline intact, secondary rows shift.** The pre-declared endpoint is unchanged —
T1b **6.6%** vs the naive T0 **7.6%** on the 441 P. Paz rides (signed **+3.8**, as Entry 13
published it; the briefly-published +3.7 was the stale-mass artifact — see the correction
below) — and so are the descent-bridge numbers (median measured 30.1 vs predicted 38.0 km/h and
`k₋_meas` 5.85 rural both hold, and P. Paz's bridge correlation stays at **0.14** — the
briefly-published 0.15 was the stale-mass artifact). Secondary rows move by ≤0.1 pp: longões T1a/T1b 5.5 → **5.6**,
T2 4.3 → **4.4**, T3 3.6 → **3.7**; censo TS 14.5 → **14.6**, T1a/T1b 14.2 → **14.3**,
T3 13.5 → **13.6**, TF 7.4 → **7.3**; P. Paz (mass-inverted, so unchanged) T2 stays **7.4**, T3 stays **8.6**.

**Gates.** `bootstrap_ci.py` did its job loudly: **14 of 24 gates failed** on the first post-change
run, each naming its old expectation, and 10 passed untouched (every value that moved by less than
the ±0.11 rounding tolerance). The expectations are now re-baselined from the fresh scoreboards and
**all 24 pass**. Bootstrap CIs shifted in the last digit where their medians did.

**The DEM chain (Entries 19–21).** `igc_resolution_test` re-ran in full and its **conclusion is
untouched** — the only genuine mover is censo, the *assumed*-mass corpus: v2Edge@igc5 22.1 →
**21.9** vs igc30 12.3 → **12.1** (paired signed gap 9.44 → **9.41 pp**). **The pooled riders are
unchanged from the published values** — 9.6 vs 7.1, gap **+3.64 pp** (the per-rider rows P. Paz
9.0 vs 8.1, JAAM 2.9 vs 3.4, the author 14.8 vs 9.8 likewise hold), FABDEM pooled **17.6**, and
h₊(igc5) > h₊(igc30) on **919/922** rides. Both pre-registered thresholds stay triggered, every
significance verdict holds (censo igc5 better on 2/58, p < 1e-4; JAAM still the corpus where igc5
wins on |Δ%|, 100/181, p = 0.16), and the implied drop-weighted ε is unchanged at **0.414@5 m vs
0.456@30 m**. One sanity gate needed a rerun rather than a re-baseline: igc cross-checks its baro
anchor against `regime_comparison.csv`, so running it *before* `regime_compare` had been
regenerated compared new-G against old-G (worst |Δ| 3.94 kJ) — an ordering artifact, not a
regression; every other gate passed, including `walkStats ≡ r1dV2Edge` at max |Δ| = 0.

**CORRECTION (same day): the first DEM-chain re-runs were contaminated, and the scoring
below them was wrong in the most instructive way available.** The morning re-runs of
Entries 17/19/20/21 moved gravity but not the *implied masses frozen as code constants*:
`regime_compare.py`'s `PHYS` table and `time_compare.py`'s `PPAZ_MASS` still carried
74.3 / 101.7 / 74.5 kg — the pre-re-baseline inversions — while this very entry records
those inversions moving to **74.5 / 101.9 / 74.7** under São Paulo's gravity. Since
`m̂·g` is exactly the invariant a mass-inverting corpus preserves, running new-g against
old-m̂ made β ≈ 0.27% low for every rider in the DEM chain. Three symptoms caught it the
same day: `bootstrap_ci` expected the time endpoint at 6.6/**3.8** while the harness
produced 3.7; an audit agent flagged `time_compare.py:62` as carrying a constant the same
pass declared superseded; and the Entry-20 movements (up to 0.32 pp) exceeded anything a
0.24% constant should do to a fitted corpus.

**With the masses corrected, the clean re-runs return Entries 19–21 essentially to their
published values, and the pre-registered expectation is confirmed *cleanly*:**

- **Entry 19**: pooled riders **unchanged** — med|Δ%| 9.6 vs 7.1, paired gap +3.64 pp,
  implied ε 0.414@5m / 0.456@30m, FABDEM 17.6, h₊(5)>h₊(30) on 919/922. Only censo (an
  *assumed*-mass corpus) genuinely moves: 22.1 → 21.9 vs 12.3 → 12.1, gap 9.44 → **9.41 pp**.
  Both pre-registered decision thresholds stay triggered.
- **Entry 20**: σ* = 10 m re-selected; PRIMARY ENDPOINT PASS on all three riders —
  ppaz 3.69/+0.97 (published 3.69/+0.96), danlessa 4.92/+0.83 (4.94/+0.81, margin
  0.06 → 0.08 pp), σ=0-calibrated 3.67/2.26/4.95 (3.66/2.25/4.95). The one genuine mover
  is **JAAM: 2.74/+0.31 → 2.79/+0.12**. Every ablation keeps its role.

  *Why JAAM moves when the others don't (mechanism, from evidence already in the two runs).*
  For a mass-inverted corpus `m̂·g` is exactly invariant, so in principle nothing should
  change; the only real perturbation between the published and clean runs is the **0.1 kg
  rounding of the frozen masses** (exact-invariant values 74.479 / 101.945 / 74.680 vs the
  frozen 74.5 / 101.9 / 74.7 — errors +0.028% / **−0.044%** / +0.027%). Two fixed-parameter
  controls bound that direct effect at ~0.01–0.02 pp: the uncalibrated ablation (jaam
  2.65 → 2.66) and danlessa's own calibrated row, whose re-fit landed on the **identical**
  cell (0.348 / 0.0077 / 0.768 in both runs) and moved only 0.02 pp. JAAM's re-fit instead
  **hopped one step along the CdA↔Crr ridge** — published (0.378, 0.0097, 0.976) → clean
  (0.363, 0.0101, 0.968) — and the 0.19 pp bias move is the validation-half difference
  between those two near-tied cells, not physics. JAAM is the hop-prone rider because his
  corpus has the weakest aero/rolling identifiability: fast, gentle (median s̄ 1.5%), narrow
  speed range, so only α_roll + α_aero's *sum* is pinned — within the clean run alone, the
  σ=0 and σ=10 fits sit at wildly different cells (CdA 0.552 vs 0.363!) with train medians
  2.92 vs 2.91. This is Entry 20's "fitted values are effective, not physical" caveat made
  quantitative: the second digit of a validation bias is a property of which ridge point the
  train half picks, not of the rider. (Distinct from the retracted lumpy-grid claim below:
  that one attributed the *stale-mass artifacts* to grid discreteness without a control;
  this one has the seed, two controls, and both parameter cells in evidence.)
- **Entry 21**: the fit returns **exactly** — the full trio **0.9375 / 0.0632 / 0.025** and
  k_s-only 0.8844, both the published values; censo is still NOT bridged, gap **4.45 pp**
  (published 4.44 — censo again the genuine mover); the E1 per-rider deltas (med|Δ%| / bias)
  come back at 0.04/0.15, 0.17/0.55, 0.62/1.01, so the published "≤0.62 / ≤1.00" bound
  becomes **≤0.62 / ≤1.01**; E2 still fails danlessa (5.22 vs the 5% gate, 0.22 pp over,
  as published).

**Retraction: the "discrete grid search absorbs lumpily" explanation published in this
entry earlier today is withdrawn.** The 0.02–0.32 pp movements it explained were the mass
bug, not calibration granularity; with consistent physics the grid search lands on
(almost exactly) the published cells. Likewise the earlier claim that P. Paz's
descent-bridge correlation moved 0.14 → 0.15: the clean run gives **0.14** — the "move"
was the bug. And the note that goal/scale "exit non-zero only on documented-benign gates"
was too kind: `scale_trio`'s Entry-20 anchor gate was failing because the anchors
themselves were stale constants — the same defect class again, now refreshed
(8.535/2.636/14.862) with a comment tying them to Entry-20 re-runs.

**The lesson is now an invariant, not an anecdote.** Two constants families must move
together with G or not at all: the hand-copied G sites (already documented) and **any
implied mass frozen in code** (`regime_compare.PHYS`, `time_compare.PPAZ_MASS`,
`scale_trio`'s Entry-20 anchors). CLAUDE.md now states: never freeze an implied mass in a
harness constant; if a fitted/derived value is used as an anchor, it must name the run
that produced it and be refreshed when that run re-runs. (The gates did their job: every
one of the three detection paths above was a mechanism this repo built deliberately —
gate expectations, adversarial audits, and pre-registered directional predictions.)

**What is NOT re-baselined, deliberately.**

- **Entry 26 keeps its numbers.** It was published hours before this change, and its Q1/Q2B
  figures come from *simujaules'* JS engine, which still runs 9.81 — re-running the Python side
  alone would make them less comparable, not more. Its Q2A profile numbers would shift ≈0.1 pp on
  the same logic as the censo scoreboard. Following the Entry 11 precedent, earlier entries keep
  the numbers they were written with; this entry is the pointer to the current values.
- **Entries 2–6 keep their historical numbers** (the same convention Entry 11 established).
- **`sampasimu` WAS re-based the same day** (simujaules `26c26e5`, v63, committed but not yet
  pushed/deployed), so the divergence this entry originally recorded is closed at the source
  level: `app.js` now carries a single documented `G_SP = 9.7864` feeding the one cost bundle it
  ships to `energy-worker.js`, `graph-engine.js` and the Rust backend, and its seven `docs/grid-*`
  mirrors moved with it. Two facts from that pass are worth importing here. **(i) The Rust backend
  has no gravity constant at all** — it receives the derived `{aRoll, aAero, beta, abRatio}` bundle
  over the wire, so the JS↔Rust bit-parity invariant is *gravity-blind* (its 97 energy cases still
  match at max |Δ| = 0, but they do not exercise this constant; what pins it there is
  `test-energy-v2.mjs`). **(ii) The shift is not a single ratio.** β and `a_roll` fall 0.2406%, but
  `a_aero` *rises* 0.096% — lower gravity means less rolling drag, so the flat-equilibrium speed
  `v_f` rises 0.048% and the aero term follows — and `abRatio` rises 0.193%. Net on a mixed
  flat/±5% edge: **−0.197%**. So "0.24%" is the climb-dominated figure and ≈0.2% the mixed one; the
  numbers in this entry are unaffected (they are measured, not scaled), but the *mechanism* is a
  two-term trade, not one multiplier.
- **The published `/modelo/` pages are now stale.** Those HTML/PDF builds live in the simujaules
  repo but are generated from *this* repo by `research/build-modelo.sh`, so re-publishing the
  re-baselined article is a follow-up here, not there. Until then the deployed paper shows
  pre-re-baseline numbers.

**The sustained-climb balance moved, and it moved the right way.** Entry 7's energy balance was
re-baselined with the rest of `compare.py` but never made this entry's delta table. Recording it
(2535 sections over the 44 rides): expected gravity 37 366 → **37 276** kJ, rolling 4 424 →
**4 413**, aero 1 544 unchanged, total 43 333 → **43 233**; measured/expected 0.96 → **0.97**;
per-ride k_h median 1.02 → **1.03**; `k_h(sustained)` unmoved at **0.96**. This is the one number
in the re-baseline whose *direction* is not arbitrary: the measured side is a power-meter reading
and cannot move, so lowering gravity lowers only the expected side and the balance **improves** —
the residual gap narrows from 3.56% to 3.34%. The `k_h ≈ 1` conclusion Entry 7 rests on is
untouched; it is simply supported a little better under São Paulo's gravity than under 9.81.

Chasing that number also caught a defect *older* than the re-baseline: `notas.md` claimed the
sustained balance holds "to within 3%", which was false before (3.56%) and after (3.34%). All four
article files had it right at "within 4%"; the spec now matches them and cites the ratio.

**A third audit wave — and the sync surface is bigger than anyone documented.** Parts 1–2c were
each verified before committing and an independent audit still found stale numbers each time. This
wave finally explains why: it went looking in the files *no earlier pass had opened*, and a single
published median turns out to live in up to **seven** places.

- `research/notes/CURATED_JOURNAL.md` had never been re-baselined at all — and it still asserted
  the paper's most contested claim in its pre-re-baseline direction ("the champion beats the
  simulation", 3.6 vs 5.1, 25/44, p = 0.45). The re-baseline is precisely what turned that into
  parity, so the readable retelling was contradicting the lab journal on the one point the lab
  journal had deliberately softened.
- `analysis/journal.qmd` carried the pre-re-baseline trio as **literal arguments in a runnable
  cell**. Stale prose misinforms a reader; a stale literal in an executed cell demonstrates the
  wrong model to anyone who runs the notebook. That is the dangerous class.
- `applet/index.html` — the live tool — had a preset button loading `k_s` 0.94 / ε₀ 6.3% into the
  UI: the only stale value a reader can *act* on without reading a word. (Two of its code comments
  were stale too, one of them since well before this re-baseline: the Entry-8 correlations read
  0.83–0.87 where the measured values are **0.771** and **0.823** — the article had the right pair
  all along.)
- `research/notes/claims.ttl`, and through it every generated `research/packages/entryN/` RO-Crate
  and `claims-explorer.html`, which are derived artifacts committed to the repo.
- `notas.md`, the spec.

The lesson is not "audit harder"; three careful passes had already run. It is that **the
number-bearing surface is undocumented**, so each pass rediscovers part of it. `CLAUDE.md` already
documents exactly such a surface for gravity (14 hand-copied sites) *because this problem happened
before*. The published medians deserve the same: one list of every file that restates a headline
number, so the next re-baseline is a checklist instead of archaeology. Standing follow-up.

One null result is worth stating too. The four article files came back clean, and the P. Paz
mass-sensitivity sweeps — flagged because their midpoint (74.3 kg) no longer matched the implied
mass (74.5 kg) — were **label** defects only. Re-running `ppaz_compare` at 70 / 74.5 / 78 kg
reproduces 0.096 / 0.091 / 0.088, and `time_compare` reproduces 6.2 / 6.6 / 7.1, both exactly as
published; the 74.5 kg runs reproduce every other §8.6 and §8.8 figure. The results were right —
only the grid point they were labelled with had moved.

**But that re-run surfaced a real overstatement in §8.8.** The time model's *level* is mass-robust
as claimed (6.2 / 6.6 / 7.1%), yet its *paired advantage over the naive baseline* is not: across
the same sweep T1b's win rate over T0 decays **65% → 56% → 52%** and loses significance at the top
end (sign p < 0.001 → 0.011 → **0.36**). The pre-declared endpoint sits at the data-implied mass
and stands, but "mass-robust" was doing more work than the numbers support. Both article languages
now say so.

**One more recorded delta: the Entry-15 fit population itself moved.** `param_fit`'s
single-activity power-balance gate (r² > 0.4) is gravity-sensitive, so P. Paz's clean-fitting
activity count is 123 → **122** (wind-usable 95 → **91**), and the fitted masses follow the
familiar ratio (80.7 → **80.9**, JAAM 103.1 → **103.4**, author/longões 79.8 → **79.9**,
author/full 71.2 → **71.4** on 101 activities). The recovered CdA/C_rr stay in range; every
Entry-15 conclusion stands. (Entry 15's own table keeps its as-written values, per convention.)

**The Entry-16 fitted-physics rerun is now regenerated too** (it was the one env-override
pass the re-baseline had not re-run; the audits caught the gap). At the re-baselined fitted
constants (`PPAZ_M=80.9 PPAZ_CDA=0.260 PPAZ_CRR=0.0053` — only the mass moved, by the G-ratio):
canonical is **7.5% / −6.9** exactly as published, the measured ε_bal on real descents is 0.14 as
published, and the frozen-estimator tie sharpens one count: RMS **0.083 → 0.082** against the
unchanged best-flat 0.086. Verdict untouched — still a tie. One process note worth keeping: the
article briefly carried 0.082 this morning, an audit flagged it as an unverifiable drift from the
historical 0.083, and it was "safely" reverted — the regeneration now shows 0.082 had been right.
The lesson cuts the other way from most of today's: when a number can be *regenerated* for the
price of one harness run, regenerate it; reverting to the historical value is only the safe move
when the check is expensive. (This rerun was the first real user of the new no-clobber sweep
CSVs — it wrote `ppaz_comparison.PPAZ_M80p9_PPAZ_CDA0p260_PPAZ_CRR0p0053.csv`, leaving the
canonical CSV untouched — and of the parse cache, which is why it took ~2 minutes, not ~10.)

**Terminology, adopted here.** The `−0.13` has been "the offset" for nineteen entries, which made
every sentence about it a description rather than a reference. It now has a name: **the coasting
deficit**, ε₀ — the share of the descent that pure coasting *would* refund but the rider does not
collect, because they keep pedalling into the descent and brake before the corners. The name is
chosen to carry the finding, not just the number: ε₀ is a property of **riding habit, not route
geometry**, which is precisely why Entry 10's braking-density predictors all failed to explain it
(the wrong kind of thing was being regressed) and why it recurs at 0.12–0.133 on three riders who
share no roads. The symbol ε₀ already existed in `notas.md` and in the deployed `v2Edge`; this
entry only supplies the words. Old entries keep their prose — "the −0.13 offset" and "the coasting
deficit" are the same quantity — with one exception: Entry 8, the definition site, got a single
retroactive parenthetical naming it (no value touched), because a reader who lands there first
should not have to wait nineteen entries for the term.

**Net.** A 0.24% change in one constant moves nine published medians by ≤0.2 pp, moves none of the
rider-transfer results at all, strengthens the parity claim, softens one transfer claim from "ties"
to "nearly ties", and leaves every qualitative conclusion in the journal and the article standing.
The re-baseline's real value is the two side effects: `analysis/` is stdlib-only again, and the
14-way gravity duplication is now documented as the sync hazard it is.

Tooling: the full suite, in order — `compare`, `censo_compare`, `eps_hypothesis`, `eps_sp_test`,
`ppaz_compare`, `jaam_compare`, `danlessa_compare`, `time_compare`, `param_fit`, `cda_estimate`,
`regime_compare`, `igc_resolution_test`, `scale_trio`, `goal_calibration`, then
`analysis/parity/run_parity.py` and `bootstrap_ci.py` as the gates. `goal_calibration` exits 1
on the documented-benign large-σ h₊ monotonicity gate only (the one Entry 20 itself diagnosed
and dismissed); `scale_trio` now exits 0, its Entry-20 anchors refreshed (see the correction
above).

---

## 2026-07-24 — Entry 26: pre-registered — the direction ladder on real ride endpoints, and portals (bridges/tunnels) in both the track and the search

**Lineage** — $I$: $(\mathrm{OSM} + \mathrm{DEM}, P_{a,g})$ · $T$: v2Edge on real endpoints · $O$: `e26_grid.csv` (86), `e26_portal_profiles.csv` (922), `e26_detour.csv` (321) · $S$: the direction ladder; portals

*Prompt (Danilo): "I want to prepare two experiments, one that follows up on E23 and E19: Right
now, simujaules has implemented support for long edges and more grid directions (eg. 8, 16, 32,
64 and 128). Also, it has support for the notions of 'portals', which corrects DEMs for bridges
and tunnels. Question 1: By how much does using 8/16/32/64/128 directions affect the discretized
case (eg. E23) when using the E19 corpus? Question 2: By how much does including portals affect
the model prediction accuracy and bias? This generates two subquestions: A) how does portals
affect the track-as-whole scenario? and B) how does portals affect the discretized scenario."
Protocol declared BEFORE any run; results will be appended dated, Entry 19/20-style.*

**Context — what shipped since the studies being followed up.** Entry 23/25 measured the
grid-connectivity bias on *synthetic* source/target pairs (radius rings on a 900×900 crop);
simujaules v57 then shipped the direction ladder as a user option (`nDirs` 4–128, Farey headings,
profile-integrated long moves, per-worker long-edge tables in density runs; non-8 is
browser-only, so Rust parity is untouched). Separately, since v19 simujaules has **portals**: one
directed edge per OSM `bridge=*`/`tunnel=*` span between its two abutment cells, costed by the
same grid model on `(deckLenM, Δh)` and relaxed alongside the 8 grid neighbours in
`dijkstra`/`densityField` (A\* top-N and the max-cost DP are portal-blind — documented
limitation). Entry 19's 922-ride corpus is the natural bridge between those synthetic grid
studies and measured energy — that is what both experiments exploit.

### Experiment 1 (Q1) — the direction ladder on the Entry-19 corpus's real endpoints

- **Question.** By how much do 8/16/32/64/128 directions change terrain-mode *optimal* energies
  when the sources/targets are the Entry-19 corpus's real ride endpoints, rather than Entry 23's
  synthetic rings?
- **Data.** The start/end cells of the 922 Entry-19 rides inside `sampa_geral.tif` coverage;
  drop pairs closer than 800 m apart (Entry 23's floor) and deduplicate near-identical pairs
  (< 250 m at both ends). **Privacy: endpoints are GPS-derived (often homes). The pair list
  lives with the gitignored per-ride data (`harness/dem/coords/` rules apply) and is exported to
  the sibling repo locally, never committed; published outputs are aggregates only.**
- **Conditions.** The SHIPPED `buildMoves` ladder, `nDirs ∈ {8, 16, 32, 64, 128}`,
  profile-integrated long edges, on the deployed raster at v55 σ = 10 m smoothing; physics
  bundle 1 = UI defaults (the Entry 23/25 bundle), bundle 2 = one Entry-20 calibrated rider set
  (sensitivity). `sq128` is the reference, as in Entry 25 §4.
- **Primary endpoint.** Per-pair `E_opt(nDirs)/E_opt(128) − 1`: median / mean / p90 at
  `nDirs = 8` and `16`.
- **Secondary.** Budget-reach at each source's median-E8 budget (the KPI statistic); the detour
  ratio `E_opt(8) / E_trackwalk` per ride (connecting the discretized optimum to Entry 19's
  fixed-route numbers); the wall-time ladder on real pairs.
- **Predictions (distributions, not point ranges — Entry 25 §12's lesson).**
  P1: the sq8 median lands in [8%, 18%] above sq128 (Entry 23 measured +12.7% on synthetic
  pairs at 5 m; real endpoint pairs sample corridors non-uniformly, so the band is wide).
  P2: sq16 recovers 55–75% of the sq8 gap (Entry 23: ≈ ⅔).
  P3: the per-pair ladder is monotone non-increasing for ≥ 95% of pairs.
  P4: no direction signature (terrain-dominated regime, Entry 25 §6).
- **Decision rule.** If sq16 recovers ≥ 50% of the median gap at ≤ 3× single-source wall time on
  real pairs, recommend `nDirs = 16` (+ long-edge tables) as the density/KPI default on the
  simujaules roadmap; otherwise the 8-default stands with the Entry 23 disclosure unchanged.

### Experiment 2 (Q2) — portals: bridges and tunnels as DEM corrections

Shared input: OSM `bridge=*` / `tunnel=*` spans pulled for the `sampa_geral` bbox (Overpass),
deduplicated; each span contributes a portal `(endA, endB, deckLenM)` with the deck as the
straight line between abutment ground heights — exactly the shipped v19 portal model.

**Q2A — the track-as-whole scenario.** Does portal-correcting the *profile* change prediction
accuracy and bias against measured `∫P·dt`?

- **Method.** Rebuild the Entry-19 `igc5` (and `igc30`) profiles with a portal overlay: where a
  ride's track runs along a mapped span (matched by proximity + heading to the OSM way), replace
  the sampled heights across the span with the deck interpolation; elsewhere untouched. Re-run
  the Entry-19 walk (v2Edge and the R0 champion) on corrected vs raw profiles, all 922 rides,
  paired.
- **Endpoints.** Paired Δ(med |Δ%|) and Δ(bias) per corpus and pooled; the share of rides
  touched (≥ 1 span) and the conditional effect on touched rides; the h₊ removed by the
  correction.
- **Predictions.** P5: bias moves DOWN (toward measured) on touched rides — bare-earth dips
  charge phantom climb + descent, and Entry 6 already showed the baro is right at bridges.
  P6: the pooled median moves little (< 1 pp; spans are a small distance share) but the
  touched-ride tail improves visibly, most on the viaduct-heavy urban censo.
  P7: h₊ drops on ≥ 90% of touched rides.
- **Falsifier.** If bias moves UP or scatter worsens on touched rides, either the straight-deck
  model is wrong for SP viaducts or the OSM matching is contaminating ordinary streets — stop
  and diagnose before any deployment claim.

**Q2B — the discretized scenario.** Do portals change optimal-route energies and reach?

- **Method.** Experiment 1's endpoint pairs, at `nDirs = 8` and `16`, WITH vs WITHOUT the portal
  set — same engine, the shipped portal relaxation.
- **Endpoints.** The per-pair `ΔE_opt` distribution (machine-assert `ΔE ≤ 0` everywhere — extra
  edges can only help a shortest-path); the share of pairs improved; budget-reach gain; and the
  interaction with Q1: does the portal gain shrink at 16 directions (finer headings can already
  route around some gaps)?
- **Predictions.** P8: the median gain is small but the tail is large — river/valley crossings
  dominate (the v19 real-data check at Av. Dr. Arnaldo saw a local 19× energy drop).
  P9: reach gains concentrate along the Pinheiros/Tietê crossing corridors.
  P10: portal gains are mostly independent of `nDirs` (portals fix topology, directions fix
  geometry).

**Sanity gates.** The no-portal run must be byte-identical to Experiment 1 (the v19 no-op
invariant); every portal edge cost ≥ 0; the Entry 25 harness's bit-identity gate against the
real `energy-worker.js` on every run; portal-corrected profiles re-verified for distance
identity with their tracks.

**Tooling plan.** Q2A lives in this repo (a portal-profile builder beside
`igc_resolution_test.py`: Overpass pull + gdal sampling; outputs gitignored like every per-ride
artifact). Q1/Q2B live in the sibling simujaules repo (the `grid-sens.mjs` harness lineage,
reading the locally-exported endpoint pairs). Nothing with coordinates is committed anywhere.

### Results (same day) — the ladder gap reproduces on real endpoints but its VERDICT is bundle-conditional; portals pay where the DEM lies

**Corpus.** [`e26_pairs.py`](../../src/harness/e26_pairs.py) turned the 922 Entry-19 rides into
**90 unique endpoint pairs**: 595 rides (65%) were dropped by the pre-registered 800 m floor —
they are *loops* that start and end at home — and 237 folded into a near-duplicate pair, so
Experiment 1's real-endpoint corpus is the point-to-point subset (327 rides → 90 pairs; censo 25,
ppaz 30, jaam 7, danlessa 28; median separation 4.6 km, max 38 km; one pair absorbs 58 rides).
**86 of 90** computed; the other 4 exceed the harness's 16 M-cell crop cap (all long pairs,
logged individually). A re-run of the exporter reproduces `e26_pairs.json` **byte-for-byte**.

**Integrity.** Every field in Q1/Q2B is produced by the **real `energy-worker.js`** in a sandbox
(shipped v57 `buildMoves`/long-edge tables, v19 `buildPortalAdj`) — nothing reimplemented. Gates:
bit-identity of the harness's own 8-move field vs the worker **max|Δ| = 0** on every invocation;
the v19 portal no-op (empty portal set ≡ none) **max|Δ| = 0**; every portal edge cost ≥ 0. Q2A:
the no-op invariant holds float-exactly on all 7 zero-span rides, corrected-profile distance ≡ raw,
and deck interpolation stays inside its abutment heights (worst exceedance 0.00e+00 m).

#### Q1 — the direction ladder on real ride endpoints (86 pairs, `grid-e26.mjs`)

Median `E_opt(n)/E_opt(128) − 1` at the target cell, per physics bundle:

| bundle (climb-dominance β/(aRoll+aAero)) | sq8 | sq16 | sq32 | sq64 | sq16 recovery of the sq8 gap | t16/t8 |
|---|--:|--:|--:|--:|--:|--:|
| **1 — UI defaults** (53.5:1) | **11.90%** | 5.99% | 2.38% | 0.73% | **49.69%** [CI 45.9, 53.8] | 2.19× |
| **2 — Entry-20 calibrated** (28.5:1) | **6.82%** | 2.88% | 1.03% | 0.32% | **57.72%** [CI 52.8, 61.8] | 2.12× |

**The headline is that the two declared bundles disagree, and each confirms exactly what the other
refutes.** Under bundle 1 the sq8 gap sits at 11.90% — inside the pre-registered [8, 18] band and
close to Entry 23's +12.7% on synthetic rings, so **P1 CONFIRMED** — while sq16 recovers only
**49.69%** of it, below the [55, 75] band with the whole bootstrap CI under 55%: **P2 REFUTED**.
Under bundle 2 the gap nearly halves to 6.82% (**P1 REFUTED**, now *below* the band) and the
recovery rises to 57.72% (**P2 CONFIRMED**). **P3 CONFIRMED** in both: 86/86 pairs are monotone
non-increasing along the ladder. **P4 CONFIRMED**: the apparent heading signature (12.35 pp spread
across 22.5° bins) collapses to **3.35 pp** once each pair is measured against its own corpus
median — the raw "peak" bin was 9/13 ppaz pairs — so no lattice direction signature survives, the
terrain-dominated regime of Entry 25 §6.

**The pre-registered decision rule therefore has no bundle-free answer.** It asked for ≥ 50%
recovery at ≤ 3× wall time. Bundle 1: **49.69% — FAIL by 0.31 pp** (time passes at 2.19×), so the
8-direction default stands. Bundle 2: 57.72% — PASS, recommend 16. Worse for the rule's
authority, bundle 1's verdict is not even resolvable: its CI [45.9, 53.8] straddles 50%, and the
*per-pair* recovery estimator — equally consistent with the wording "recovers ≥ 50% of the median
gap" — reads **51.57%** (IQR 47.4–57.0), which would PASS. Entry 25 §12's lesson was
"pre-register distributions, not point ranges"; this entry adds **"pre-register the estimator,
not just the threshold."**

**Why the bundles differ — Entry 25 §7's untested claim, now measured.** That note predicted the
bias "scales with β/(aRoll+aAero) ≈ 53:1, so heavier climb-dominance ⇒ larger bias; a strong-rider
bundle would shrink it somewhat. Not swept here." Halving the ratio (53.5 → 28.5) roughly halves
the sq8 gap (11.90 → 6.82%) and lifts sq16's relative recovery — the mechanism confirmed
quantitatively, which is also why the ladder question cannot be settled independently of the rider.

**A new mechanism the synthetic study could not see: pair LENGTH.** The per-corpus spread at sq8
(ppaz **22.12%** vs jaam 7.80%, censo 10.81%, danlessa 10.98%) is not a rider or terrain effect —
it tracks separation. The gap falls from **15.79%** on the shortest third of pairs to **10.25%** on
the longest, and ppaz's pairs are by far the shortest (median 2.8 km vs censo's 11.9 km): a
lattice's per-step error is a larger share of a small total. Entry 23's fixed ≥ 800 m rings held
length roughly constant and so could not surface this.

**Secondary — reach.** At the same budget, sq16 reaches **+9.01%** more area than sq8 (bundle 1;
+6.61% bundle 2) — the accessibility-KPI reading of the same bias.

**Secondary — the detour ratio, and an honest failure of the endpoint as specified.**
[`e26_detour.py`](../../src/harness/e26_detour.py) walks each pair's member rides on their own igc5
profile under the *same* cost bundle as the grid (including g = 9.81, mirrored from the JS, so the
ratio measures detour and not a gravity mismatch) and divides. Pooled over all 321 member rides the
ratio is **0.070** — a meaningless number, because after the 800 m floor the surviving pairs are
mostly *near-loops*: median route detour **12.4×**, ppaz **24.8×** (a 60–100 km ride whose ends are
3 km apart). Restricted to genuine journeys (track ≤ 2× straight line; n = 21 rides over 12 pairs,
median detour 1.73×) the ratio is **0.467** at sq8 and **0.421** at sq128: on a real A→B journey
roughly **half** the ride's energy is street-constraint and detour rather than terrain necessity.
The endpoint is reported both ways, with the stratification as the finding.

#### Q2A — portals as PROFILE corrections, vs measured `∫P·dt` (922 rides, paired)

`e26_portal_profiles.py` matched OSM spans to each track (≤ 25 m, heading ≤ 30° mod 180, ≥ 60% of
the span covered — the disclosed operationalization of "proximity + heading"), replaced the sampled
heights across each matched span with the v19 straight deck, and re-walked. Touched: **915/922**
rides (median 17 spans/ride).

| corpus | v2@igc5 med \|Δ%\| raw → portal | Δ bias | R0@igc5 med \|Δ%\| | v2@igc30 |
|---|---|--:|---|---|
| censo (58) | 22.13 → **18.32** | −3.81 | 5.59 → 4.88 | 12.29 → 9.64 |
| ppaz (277) | 9.06 → 8.42 | −0.64 | 6.64 → 6.16 | 8.12 → 7.71 |
| jaam (181) | 2.88 → 2.90 | +0.02 | 4.97 → 4.93 | 3.39 → 3.47 |
| danlessa (406) | 14.79 → **13.21** | −1.72 | 5.92 → 5.66 | 9.87 → 8.37 |
| **all (922)** | 10.24 → **9.35** | −0.95 | 5.78 → 5.56 | 7.41 → 6.88 |

**P5 CONFIRMED on 9 of 10 strata** — stated properly as |bias| shrinking, since "bias moves DOWN"
is the wrong test for a corpus whose raw bias is negative (the harness's pooled `Δbias < 0` scoring
would have missed this). The exception is **jaam under the champion R0**, whose already-negative
bias moves further negative (−4.52 → −4.70, |bias| +0.18 pp). **P6 CONFIRMED**: the pooled median
moves < 1 pp (−0.90 pp v2, −0.23 pp R0) while the tail improvement concentrates on the
viaduct-heavy censo exactly as predicted (touched-ride Δp90 −4.53 pp censo vs −2.70 pp riders).

**P7 REFUTED — with a diagnosable mechanism.** h₊ drops on only **697/915 (76.2%)** of touched
rides, not ≥ 90%. The split is systematic: censo drops on 96.4% (median 20.1 m removed), jaam on
49.2% (median **−0.1 m** — ascent sometimes *added*), and the ascent-rose group has markedly
shorter spans and less relief removed (median 1079 m / 2.3 m vs 1415 m / 16.3 m). The cause is
**junction steps**: the deck endpoints are raster heights sampled at the exact OSM abutments while
the neighbouring profile points come off the 5 m grid, so each splice can inject a small step, and
on gentle terrain with many short spans those steps outweigh the dips removed. Note this artifact
belongs to *transplanting the portal model into a profile* — the deployed portal is a single
Dijkstra edge with no junctions, so Q2B is structurally immune. A blended splice (deck endpoints
taken from the profile's own heights) is the obvious follow-up.

#### Q2B — portals in the discretized (optimal-route) scenario

| bundle | ΔE at B, med | ΔE min | pairs improved | reach gain @8 | reach gain @16 | pairs with reach gain |
|---|--:|--:|--:|--:|--:|--:|
| 1 — UI defaults | **0.000 kJ** | −7.07% | 28/86 (33%) | +0.49% | +0.64% | **79/86**, 78/86 |
| 2 — calibrated | 0.000 kJ | −8.11% | 18/86 (21%) | +0.15% | +0.18% | 76/86, 73/86 |

**P8 CONFIRMED** in the exact predicted shape: the median portal effect on a specific A→B optimum
is **identically zero** (most optimal paths never need a bridge) while the tail is large — down to
−7.07% at 8 directions and −8.95% at 16, i.e. −6.8 kJ on a 231 kJ pair. **P10 CONFIRMED**: the
gains are broadly `nDirs`-independent (28 vs 27 pairs improved; if anything marginally larger at
16). **P9 NOT EVALUATED** — "gains concentrate along the Pinheiros/Tietê corridors" is a spatial
claim, and this harness deliberately emits no coordinates; testing it needs a separate mapping
pass, which is left as follow-up rather than quietly scored. The **budget-reach** endpoint added
during the run is the sensitive one: portals expand reachable area on **79 of 86** pairs even where
the specific path is untouched — so for the 300 kJ accessibility mission portals matter more as an
*area* correction than as a per-route one. Portal benefit is also bundle-dependent (33% → 21% of
pairs improved), for the same reason as Q1: a lower β pays less for bridging a dip.

**GATE amendment (disclosed).** The pre-registration wrote the "extra edges can only help" check as
an exact `ΔE ≤ 0`. It fired on a real pair at **+1.9e-6 kJ on a 24.7 kJ path** — relative 7.7e-8,
i.e. f32 epsilon: the engine stores E in **f32** (f64 heap keys), so adding portal edges reorders
relaxation and a settled value can move in its last bit with the optimal path unchanged. The assert
is now f32-aware (rel 4e-7 + 1e-6 kJ floor), **reports** the worst residual each session
(1.907e-6 kJ, rel 7.7e-8 over the bundle-1 run; 0.000e+0 over bundle 2), and still aborts on any
structural violation.

#### Deviations from the pre-registration (all disclosed)

1. **PRIVACY — the first implementation leaked endpoint geometry, and its results were discarded.**
   The pre-registration said spans are "pulled for the `sampa_geral` bbox"; the harness as first
   written instead pulled **per-pair crop bboxes** (endpoints + 2 km) from public Overpass mirrors,
   and such a bbox inverts back to the pair's endpoints — which are often homes. Caught by an
   adversarial review of the harness while it ran. It now pulls a **fixed 0.1° tile grid spanning
   the whole DEM, unconditionally and once** (48 tiles, 5 761 ways), so every request is a function
   of the DEM extent alone; the 43 pairs computed under the old scheme were thrown away rather than
   reused. Verified pair-by-pair that the tile union is a strict *superset* of the per-pair pulls
   (1514 ≥ 1496, 331 ≥ 315, 89 ≥ 87, 66 ≥ 64 ways), so the fix costs no coverage. The requests
   already sent cannot be recalled; that is the cost of the error and it is recorded here.
2. **f32 tolerance** on the portal monotonicity assert (above).
3. **P9 not evaluated** (needs a mapping pass; no coordinates leave the harness).
4. **4 of 90 pairs skipped** on the 16 M-cell crop cap — the four longest; the cap is a runtime
   bound, disclosed per pair in the log, and it removes the pairs *least* affected by the bias
   (the gap shrinks with length), so the reported medians are mildly conservative.
5. **Bundle 2 keeps P_flat = 80 W** (only the rider constants swap): a routing field has no ride
   to read a flat power from. Its (CdA, Crr, k_s) are Entry 20's *effective* values, not physical.
6. **The detour ratio needed a journeys-only stratum** to mean anything (above).
7. **G = 9.81 throughout** — `regime_compare.py`'s constant, which the whole DEM chain inherits
   (it does NOT read `analysis/bem/engines.py`'s G), so every number here is directly comparable to
   Entry 19's. Noted because the two definitions must be re-baselined together.
8. A soft-failed Overpass response (HTTP 200 carrying `remark: runtime error…`) was cacheable in
   the first implementation; it now deletes the cache file and fails loudly.

**Net.** The grid-connectivity bias survives the move from synthetic rings to real ride endpoints
(sq8 ≈ 12% above the near-continuum optimum under the app's own defaults, monotone, direction-blind)
and gains two qualifications the synthetic study could not give: it **shrinks with pair length** and
it **scales with the rider's climb-dominance** — so the pre-registered "ship 16 directions?"
decision flips between two equally-declared physics bundles and cannot be answered bundle-free.
Portals are the cleaner win: as profile corrections they move measured-energy accuracy and bias in
the right direction on every corpus that has viaducts (censo −3.81 pp, pooled −0.90 pp), and as
routing edges they leave the median route untouched while expanding reachable area on 92% of pairs.

Tooling: `python3 harness/e26_pairs.py` → `node ../simujaules/docs/grid-e26.mjs`
(`E26_BUNDLE=cal` for bundle 2, `E26_SMOKE=1` for a 5-pair check) →
`python3 harness/e26_portal_profiles.py` → `python3 harness/e26_detour.py`
(`E26_GRID=e26_grid_cal.csv` to score the other bundle). All outputs land in the gitignored
`results/` (`e26_pairs.json`, `e26_pair_rides.json`, `e26_grid.csv`, `e26_grid_cal.csv`,
`e26_portal_profiles.csv`, `e26_detour.csv`, `e26_osm_cache/`).

---

## 2026-07-24 — Entry 25: the simujaules grid-connectivity note, imported verbatim

**Lineage** — $I$: — · $T$: — · $O$: no new $O$ (imported verbatim) · $S$: grid-connectivity note

*Prompt (Danilo): "Include ../simujaules/docs/grid-connectivity-sensitivity-2026-07-11 as entry
E25." Entry 23 is the condensation of this study, written when the note was imported the first
time; this entry carries the canonical note VERBATIM (headings demoted one level to fit the
journal's structure) so the journal is self-contained — the sibling repo's copy remains the
canonical original. Claims and evidence for the study are recorded under Entry 23; Entry 26
pre-registers its follow-ups. No number changes here.*

### Research note — move-grid connectivity bias in terrain-mode optimal energy

**Date:** 2026-07-11 · **Status:** analysis complete; findings SHIPPED as
options in v57 (2026-07-12) — see §12 for the outcome, including the §11
pre-registration scorecard
**Harness:** `docs/grid-sens.mjs` (self-validating; reproduction §13)
**Cross-ref:** intended as an entry for
`../bicycling-energy-model/research/MODEL_COMPARISON_JOURNAL.md` (the journal
lives in the sibling `bicycling-energy-model` repo, not here); relates to
journal Entries 18–20 as described in §2.

### Abstract

Terrain mode routes on an 8-connected raster, so its "optimal" energies are
upper bounds on the continuum optimum: paths jag between the 8 discrete
headings. We measure that bias on a real DEM against a converged ladder of
move sets — square 4/8/16/32/64/128 (Farey heading subdivisions) and
hexagonal 6/12 — with a flat-terrain control that reproduces each lattice's
theoretical worst case. On the deployed IGC-SP 5 m DTM (v55 smoothing,
UI-default physics) the app's 8-move grid reads **+12.7 % median (+21 %
mean, +47 % p90)** above the near-continuum optimum at route scale, and
**undercounts budget-reachable area by ~19 %**; at 30 m the figures are
+8.1 % median and ~15 %. This is roughly **double** the pure octile-geometry
prediction: the dominant mechanism is not distance inflation but forced
height oscillation around contour lines under the asymmetric climb/descent
cost. A 16-move set recovers ≈ ⅔ of the bias — but only with
profile-integrated long edges; the naive endpoint-Δh generalization flattens
the relief its edges cross and flips to *under*-estimating (−1 % to −8.5 %
median at 30 m), destroying the upper-bound guarantee. Hex lattices are not
competitive. The original 8-over-4 choice is strongly validated.

### 1. Motivation and question

Suspicion (Danilo, 2026-07-11): terrain mode overestimates optimal energy
because of route jaggedness from the 8-cell move grid. Requested: a
sensitivity analysis vs a 16-cell neighborhood on a small DEM; extended to
4/64/128 and hexagonal 6/12 for completeness. The question matters because
(a) the energy field's absolute values feed the 300 kJ-initiative
accessibility KPIs (threshold counting is bias-sensitive), and (b) any fix
touches every bit-parity engine surface, so it needs quantified benefit
before a work order.

### 2. Relation to prior findings (journal Entries 18–20)

Distinct from, and additive in direction with, the known cost-model biases:

- **Entry 19** (resolution over-charge): `v2Edge`'s grade-local ε reads
  conservatively HIGH on fine DTMs (~+9 % median at 5 m vs ∫P·dt on real
  rides). That is a *cost-model* bias measured along fixed street routes.
- **This note** measures a *search-discretization* bias: even under a perfect
  edge cost, the 8-grid's optimal path is jagged, so route-optimal energies
  read high. The two mechanisms are independent and both one-sided positive
  on fine DTMs; they compound (not additively in any precise sense) toward
  conservative terrain-mode energies.
- **Entry 18 / the O(1)-locality requirement** constrains remedies: profile
  integration of long edges (§4) keeps edge costs O(1)-local (fixed ≤ 2·max
  sample count per edge), so a 16-move engine would not violate the
  no-path-history invariant.

### 3. Hypotheses (stated before the runs)

- H1: E8 > continuum optimum, with the flat-geometry octile bound (≤ 8.24 %,
  direction-peaked at 22.5°) as the naive expectation.
- H2: a 16-move set removes most of the gap.
- H3 (methodological): naive endpoint-Δh long moves are confounded — they
  also change terrain sampling, over-crediting the richer neighborhoods.

H1 held but the naive expectation was wrong in an interesting way (terrain
doubles it and erases the direction signature, §6). H2 held (≈ ⅔
recovered). H3 held strongly — at 30 m the naive ladder crosses below the
true optimum (§5.3).

### 4. Method

**Harness.** `docs/grid-sens.mjs`, standalone node. Mirrors (hand-copied,
same rule as the repo's other mirror tests): `v2Edge` ← `energy-worker.js`;
`readCost`'s folded UI-default physics ← the `census/census-density.mjs`
mirror (m 75 kg, Crr 0.008, CdA 0.45, ρ 1.1, k_eff 0.97, P_flat 80 W →
aRoll 6.07e-3, aAero 8.12e-3, β 0.7585 kJ/m); v55 σ = 10 m pre-smoothing ←
the `test-dem-smoothing.mjs` mirror. Dijkstra relax rules mirror the worker
exactly (f32 E storage, f64 heap keys, settled-byte staleness filter).

**Validation gate.** Every run first executes the REAL `energy-worker.js` in
a sandbox and asserts the harness's own 8-move field is bit-identical
(max|Δ| = 0 kJ, zero finite-mismatches) — observed on all runs. The flat
control (§5.1) additionally reproduces each lattice's closed-form worst case.

**Move sets.** Square lattices by Farey/Stern–Brocot level: 8 → +mediants →
16 → 32 → 64 → 128 headings (levels 0–2 coincide with the coprime
max-norm ≤ R sets; 64/128 are the Farey continuations). Square-4 (von
Neumann) as a degenerate baseline. Hexagonal lattices (node spacing = the
raster's min pixel, heights bilinearly resampled from the same smoothed
raster): hex-6 (60° headings) and hex-12 (+the √3-length 30°-offset moves).
**Square-128 is the reference**; square-64 lands within 0.2–0.9 % of it
everywhere, so the ladder has converged and "vs continuum" below means "vs
sq128".

**The confound and its control (H3).** A long move costed from its
endpoints' Δh alone *skips the relief under it*. With climb at
β ≈ 0.76 kJ/m against ≈ 0.014 kJ/m flat travel, skipping one 1 m bump fakes
more saving than ~50 m of route straightening — a terrain-resampling change
masquerading as a jaggedness fix. All long moves are therefore
**profile-integrated**: bilinear height samples every ~1 cell along the
segment, `v2Edge` summed per sub-segment (2·max(|dr|,|dc|) sub-steps; hex √3
moves in 2 sub-steps). Naive endpoint-Δh variants of square-16/32 are run
separately to size the artifact. Long moves also require their swept cells
passable (supercover sampling), so they cannot tunnel through nodata.

**Conditions.**
1. *5 m:* central-SP crop of the deployed `sampa_centro.tif` (IGC 5 m DTM),
   900×900 px ≈ 4.4×4.8 km, σ = 10 m smoothing per the v55 auto rule,
   4 spread sources.
2. *30 m emulation:* 1500×1500 crop anti-alias-smoothed (σ = 15 m) and 6×
   decimated → 250×250 at ~30 m, no further smoothing (matching how a
   coarse source is used in-app), 6 sources.
3. *Flat control:* heights constant, 700×700, 2 sources — isolates pure
   lattice geometry.

**Statistic.** Overestimate `E_mode/E_sq128 − 1` over all target cells
≥ 800 m from the source (0.3–13 M targets per condition; hex evaluated at
hex nodes mapped to the nearest raster cell). No energy budget (eMax 0), so
no truncation interacts. Reach = area within the median of each source's own
E8 field.

### 5. Results

#### 5.1 Overestimate vs the near-continuum optimum (median / mean / p90)

| move set | 5 m DTM (smoothed) | 30 m emulation | flat median | lattice-theory max (observed) |
|---|---|---|---|---|
| square-4 | 31.0 % / 47.6 % / 102 % | 27.8 % / 33.7 % / 61 % | 32.0 % | 41.4 % (41.3 %) ✓ |
| hex-6 | 18.1 % / 29.3 % / 63 % | 14.1 % / 16.8 % / 32 % | 11.3 % | 15.5 % (16.2 %) ✓ |
| **square-8 (app)** | **12.7 % / 21.3 % / 47 %** | **8.1 % / 9.7 % / 18 %** | **5.7 %** | 8.24 % (9.2 %) ✓ |
| hex-12 | 7.9 % / 12.9 % / 28 % | 3.8 % / 4.7 % / 9.8 % | 2.5 % | 3.5 % (4.2 %) ✓ |
| square-16 | 5.8 % / 9.0 % / 19 % | 2.7 % / 3.2 % / 5.9 % | 1.2 % | 2.8 % ✓ |
| square-32 | 2.1 % / 3.1 % / 6.6 % | 0.9 % / 1.0 % / 1.8 % | 0.25 % | 0.7 % ✓ |
| square-64 | 0.6 % / 0.9 % / 2.0 % | 0.14 % / 0.2 % / 0.5 % | 0.05 % | — |

(Flat-control maxima slightly exceed the single-lattice theory values because
the reference sq128 has its own ~0.1–1 % residual; the agreement is the
validation, not a coincidence.)

#### 5.2 The direct question: 8 vs 16 (profile-integrated)

| | 5 m | 30 m | flat |
|---|---|---|---|
| E8/E16 − 1 median | **6.9 %** | 3.9 % | 3.8 % |
| E8/E16 − 1 mean / p90 | 10.6 % / 22.6 % | 4.2 % / 6.0 % | 3.9 % / 7.0 % |
| E8/E32 − 1 median | 10.4 % | 5.7 % | 5.1 % |

#### 5.3 The naive-edge artifact (H3), isolated

Median vs continuum, naive endpoint-Δh long edges (true profile value in
parentheses):

| | 5 m | 30 m |
|---|---|---|
| square-16 naive | +5.1 % (+5.8 %) | **−1.3 %** (+2.7 %) |
| square-32 naive | −0.2 % (+2.1 %) | **−8.5 %** (+0.9 %) |

At 30 m the naive edges span 60–90 m and flatten whole hillocks: the sign of
the error flips. Where a naive ladder lands near zero (sq32-naive at 5 m) it
is two large errors cancelling, not accuracy.

#### 5.4 Budget reach (what the accessibility KPIs feel)

Area reachable within the median of each source's E8 field, relative to
square-8:

| | square-4 | hex-6 | square-8 | hex-12 | square-16 | square-32 | continuum |
|---|---|---|---|---|---|---|---|
| 5 m | −21 % | −7.6 % | 0 | +7.2 % | +10.7 % | +16.1 % | **+19.0 %** |
| 30 m | −23 % | −9.7 % | 0 | +6.0 % | +9.6 % | +13.2 % | **+14.9 %** |

#### 5.5 Runtime and the cost–accuracy scaling law (measured)

Per-mode wall time (harness, 900×900 = 810 k cells, one source, this
machine): sq4 0.30 s · sq8 0.47 s · sq16 1.13 s · sq32 2.71 s · sq64 7.22 s
· sq128 18.1 s · hex6 0.57 s · hex12 1.34 s · sq16-naive 0.91 s ·
sq32-naive 1.74 s. Memory unchanged (same per-cell arrays).

Pairing those times with the ladder medians gives the cost–accuracy
exponent k, defined by error ∝ time^(−k) per step:

| step | time × | 5 m err ÷ | k (5 m) | 30 m err ÷ | k (30 m) | flat err ÷ | k (flat) |
|---|---|---|---|---|---|---|---|
| sq8 → sq16 | 2.40 | 2.19 | 0.90 | 3.0 | 1.25 | 4.75 | 1.78 |
| sq16 → sq32 | 2.40 | 2.76 | 1.16 | 3.0 | 1.25 | 4.8 | 1.79 |
| sq32 → sq64 | 2.66 | 3.50 | 1.28 | 6.4 | 1.90 | 5.0 | 1.64 |
| **overall 8 → 64** | **15.4** | **21.2** | **1.12** | 57.9 | 1.49 | 114 | 1.73 |

Three readings. (a) On the rough 5 m DTM, **error × time ≈ constant**
(k ≈ 1.1): each ladder step buys almost exactly its cost's worth — "3× less
error for 3× more time" is the honest summary of the tested range. (b) The
exponent is terrain-dependent and k ≈ 1 is the WORST case: the
contour-oscillation error term decays only ~linearly in the heading gap
(gap halves per level ⇒ error ÷~2) while pure geometry decays quadratically
(÷4; flat column, k ≈ 1.7, near the theoretical ln4/ln2.5 ≈ 1.5 plus
sub-quadratic cost growth). As the terrain term is exhausted, each column's
later steps accelerate toward the flat rate (5 m: ÷2.2 → ÷2.8 → ÷3.5).
(c) The hex points sit strictly off the square Pareto frontier (hex12:
1.34 s for 7.9 % vs sq16's 1.13 s for 5.8 %) — the square ladder is the
efficient family, not just the convenient one.

Because k ≈ 1, the tradeoff curve itself has NO knee on rough terrain — the
stopping rule cannot come from the scaling law and must come from external
error floors (§8.2). Why k → 1 is natural for this paradigm: cost per level
doubles with the edge count (×~2.4 with sub-sampling), while the dominant
terrain error term halves with the heading gap — "more headings" alone can
never beat error·cost ≈ const in the terrain-dominated regime. Prospects
for k < 1 are in §9.

### 6. Mechanism: why terrain doubles the geometric penalty

On flat ground the E8/E16 gap follows octile theory exactly: medians rise
0.8 % → 6.9 % from on-axis to 22.5–30° and fall back — the classic
direction signature. On real terrain that signature vanishes (5.7–7.8 %
medians across ALL headings at 5 m) and the overall gap doubles. The
dominant cost is not extra path length but **height oscillation**: an 8-grid
path following a contour line must zigzag across it, and the asymmetric cost
(climb charged at β, descent refunded at ε·β with ε ≤ 1 − 0.13) taxes every
oscillation cycle. Finer heading sets track contours instead of chopping
across them. Consistently: the bias grows with terrain detail (5 m > 30 m >
flat), and is largest in high-relief subareas (p90 47 % at 5 m).

### 7. Threats to validity

- **Reference ≠ true continuum.** sq128 is a lattice too; but sq64→sq128
  moves < 1 %, so remaining truncation is second-order vs the reported gaps.
- **Between-cell terrain is modeled**, as the bilinear surface (sub-sampled
  every ~1 cell on long edges). Finer sub-stepping would charge long edges
  slightly more, shrinking the reported gaps marginally — the direction of
  this error makes the headline numbers mild upper bounds on the pure
  jaggedness effect.
- **Free-terrain optimum is not physical ground truth.** Real riding is
  street-constrained (graph mode is unaffected by all of this). The study
  measures terrain mode against its own continuum limit — the right target
  for "does the grid bias the field", not for "is the number the rider's
  kJ" (that is per-rider calibration territory, Entry 20).
- **One geography, one cost bundle.** Central São Paulo relief; UI defaults
  (80 W). The mechanism scales with β/(aRoll+aAero) ≈ 53:1, so heavier
  climb-dominance ⇒ larger bias; a strong-rider bundle would shrink it
  somewhat. Not swept here.
- **The 30 m condition is an emulation** (anti-aliased decimation of the
  5 m survey), not a real 30 m product like FABDEM (whose per-pixel noise is
  a separate, documented hazard).
- Sample sizes are millions of target cells but spatially correlated;
  figures are descriptive distributions, not independent draws.

### 8. Implications for the app

1. Terrain-mode optimal energies are **grid-native upper bounds**: ~13 %
   median (5 m) / ~8 % (30 m) above the continuum optimum at route scale.
   The 300 kJ-KPI counting is therefore a **conservative floor**
   (accessible area within a median budget undercounted ~15–19 %). The bias
   direction never flips under the current engine — a safety property worth
   keeping deliberately (a shared-constant correction can center the
   aggregate at the cost of exactly that property — §10).
2. If tightening is wanted, **square-16 with profile-integrated knight
   moves** is the sweet spot: recovers ≈ ⅔ of the bias at ~2.5–3× relax
   cost, stays O(1)-local, keeps the upper-bound property. Square-32 gets
   within 1–2 % at ~3× more again.
3. **The naive 16/32 implementation must never ship** — it silently
   converts a bounded overestimate into an unbounded-sign resampling error
   (§5.3). Any work order must specify profile integration and re-run this
   harness as the acceptance test.
4. Hex lattices are dominated (hex-6 worse than the current grid; hex-12
   between 8 and 16 for a full lattice rewrite). Square-4 would have been
   catastrophic — the original 8-choice is vindicated.
5. Scope of an eventual 16-move work order: `dijkstra()`, `densityField()`,
   the Rust port (+`test-backend.mjs` parity), portal composition, passes
   semantics, `densityPoolSize`/`estimateRunTime` constants, and the A*
   heuristic (a 16-heading octile-style lower bound). Until then, the honest
   framing above costs nothing.

### 9. Beating k = 1 — candidate optimizations

Since "more headings" alone is pinned at error·cost ≈ const on rough
terrain (§5.5), sub-linear cost per unit accuracy requires reusing work,
spending selectively, or changing the discretization class:

1. **Precomputed long-edge tables — tried (2026-07-11): the one candidate
   that WORKS, for density runs** (`docs/grid-longedge.mjs`). Store every
   long move's profile integral in a per-directed-heading table once, then
   relax by table lookup. Structural fact the harness confirms: a single
   Dijkstra integrates each directed edge EXACTLY ONCE (settled-guard ⇒
   one out-edge scan per cell), so for one search precompute cannot win —
   measured: K=1 loses outright (sq16: 1.53 s vs 0.92 s on-demand). The
   win is AMORTIZED across searches sharing the grid — precisely the
   density pool's shape. Measured (900×900, 6 sources): precompute 0.87 s
   (sq16) / 2.89 s (sq32); per-search time drops 0.92 → 0.66 s (sq16,
   −28 %) and 2.34 → 1.20 s (sq32, −49 %) — MORE than the sub-step share,
   because lookup also skips the sweep-passability checks and bilinear
   reads; break-even at ~3 searches; results **bit-identical** to
   on-demand integration (max|Δ| = 0 — same op order), so exactness,
   upper-boundedness and the parity story fully survive. Amortized against
   the sq8 baseline this rewrites the ladder economics for density/KPI
   runs: sq16 at ×1.40 cost for ÷2.19 error → **k ≈ 2.3**; sq32 at ×2.55
   for ÷6.05 → **k ≈ 1.9**. The binding constraint is MEMORY: f64 tables
   are 64 B/cell (sq16) / 192 B/cell (sq32) — 52/156 MB on this crop, but
   ~4.3 GB (sq16 f32) on the 135 M-cell target, so the big DEM would need
   per-slice recompute or overlap with the existing memory budget
   machinery. Single-source runs keep on-demand integration (k ≈ 1 stands
   there).
2. **Slope-adaptive neighborhoods — tried (2026-07-11) and REFUTED on this
   terrain** (`docs/grid-adaptive.mjs`). Design: unit moves everywhere;
   long moves relaxed only when either endpoint's local grade (max |dh|/d
   over the 8 unit neighbors, flag dilated 1 cell) exceeds a threshold. The
   gated edge set nests between sq8 and sq16/32, so results stay valid
   upper bounds — the pointwise nesting E8 ≥ E_ad ≥ E_uniform held with 0
   violations in every run. But the premise ("sloped fraction well under
   half") is FALSE for this deployment: at the grade thresholds that
   preserve accuracy, the steep-cell share is 91–98 % (5 m, σ=10 m
   smoothed) and 96–100 % (30 m) — central São Paulo has essentially no
   flat fraction at ≥ 0.5–1 % grade. Measured Pareto (5 m, 3 sources):
   ad16@1 % = sq16's error at sq16's cost (k 0.99 vs uniform 1.01); at the
   first threshold that prunes meaningfully (4 %, 65 % steep) the error
   grows faster than the time falls (med 4.03 → 5.53 % for −7 % time,
   k 0.69 — WORSE than uniform). Same picture at 30 m. Verdict: the gate
   only pays on landscapes with genuinely large flat fractions — exactly
   where the grid bias is already small — so the option is dominated.
   (This also retracts §9's earlier composition claim of "sq32 accuracy at
   sq16 cost": with (2) dead, (1) alone caps the in-paradigm gain.)
3. **Post-hoc path smoothing (string pulling) — tried (2026-07-11): recovers
   the zigzag, not the route** (`docs/grid-pull.mjs`). Windowed DP over the
   8-grid path's nodes (any pair within 64 nodes joinable by a straight
   segment, profile-integrated costing, masked cells block), iterated over
   the surviving breakpoints so the effective shortcut range grows
   geometrically. On 90 paths (3 sources × 3 rings 1.2/2.0/2.8 km × 16
   headings, 5 m condition): raw path bias vs sq128 med 9.6 % / p90 25.5 %
   → pulled **5.4 % / 16.1 %** — **44 % of the median bias recovered at
   ~60 ms/path**. Iterating adds nothing: the residual is CORRIDOR LOCK-IN
   — the polyline can only visit points of the original path, and the
   route-choice component of the bias (finer headings finding different
   terrain lines) is unrecoverable post hoc. Economics: excellent for the
   displayed route / top-N (60 ms ≪ any field upgrade; result stays an
   upper bound and is its own integrated cost — no viewing≡routing
   conflict); useless for fields; for the K×K accessibility matrix it
   LOSES to a sq16 field per ref row for K ≳ 12 (44 % recovery at
   (K−1)·60 ms vs ~55 % recovery at +0.7 s/row) — so it is a
   route-display tool, not a field fix.
4. **Anisotropic Eikonal — evaluated (2026-07-11): the heading bias
   genuinely vanishes, but a SIGNED interpolation bias replaces it**
   (`docs/grid-eik.mjs`). Implemented a semi-Lagrangian fast-sweeping
   solver: each cell updates from a foot point anywhere on its radius-1
   ring (64 samples, u and h bilinear at the foot ⇒ effectively continuous
   headings); Gauss-Seidel sweeps handle the strong anisotropy
   (β/(aRoll+aAero) ≈ 53) via iteration count instead of causal-ordering
   machinery. Results: on FLAT terrain it nails the analytic answer to
   0.18 % mean / 0.39 % max (vs sq8's 3.9 %) in 2 sweep-groups — heading
   bias eliminated, exactly as theory promises. On real terrain, however,
   it lands BELOW the converged sq128 reference — **−1.3/−1.5 % median at
   5 m; −4 to −12 % at 30 m** (12–17 sweep-groups; 15–22 s at 360 k cells
   vs sq128's 7 s, sq32's ~1 s) — the true continuum is only ~0.2 % below
   sq128, so this is error, and its resolution signature identifies it:
   bilinear foot heights SMOOTH within-cell relief, undercharging climbs —
   the semi-Lagrangian sibling of the naive-long-edge artifact, scaling
   with per-cell relief. Verdict: at the app's resolutions the ladder
   dominates it (sq32: +1.6–2 % guaranteed-sign error at a fraction of the
   cost, vs ±1.4 % signed at 5 m and outright worse at 30 m), and the
   integration blockers are structural — no discrete predecessor tree
   (passes counts), no budget early-exit (sweeps touch the whole grid), no
   bit-parity story (iterative, order-dependent convergence), and the
   upper-bound/floor guarantee is lost in BOTH directions. Scientifically
   validated, practically dominated for this product.

A statistical field deflation is NOT on this list as an accuracy
optimization — §10 measures why (dispersion survives; one-sidedness dies);
it is a reporting-layer option only.

**§9 bottom line after testing all four candidates (2026-07-11):** exactly
one candidate beats k ≈ 1, and only in the density regime: precomputed
long-edge tables (1) give amortized **k ≈ 2.3 (sq16) / 1.9 (sq32)** across
searches sharing the grid, bit-exact, with memory as the binding
constraint — single-source runs stay at k ≈ 1. Slope-adaptivity is dead on
this terrain (2); string pulling is a route-display tool (3); the Eikonal
route trades the heading bias for a signed interpolation bias that is
worse at 30 m and merely sq32-class at 5 m, minus every guarantee the
product relies on (4). The efficient frontier for the app: for
density/KPI runs, sq16 (or sq32) with precomputed long-edge tables —
~×1.4 (×2.6) wall time for ⅔ (5/6) of the bias removed; for single-source
runs, on-demand profile integration at the honest k ≈ 1 deal; string
pulling for the displayed route; §10's threshold-layer correction where a
centered aggregate is preferred over a floor.

### 10. Parametric correction: how far does a shared constant go?

Question (Danilo): can the overestimate be absorbed into the parameters —
e.g. inflate the energy budget, or deflate reported energies by a shared
calibration constant? Measured with `docs/grid-correct.mjs` (sq8 vs sq128
fields, same conditions):

| | 5 m (3 sources) | 30 m (6 sources) |
|---|---|---|
| shared constant c* (mean of per-source median ratios) | 1.115 | 1.090 |
| per-source c spread | 1.074 – 1.184 | 1.053 – 1.150 |
| \|error\| raw, med / p90 / p99 | 9.3 % / 24 % / 48 % | 8.1 % / 18 % / 31 % |
| \|error\| after ÷c*, med / p90 / p99 | **4.1 % / 11 % / 33 %** | **2.6 % / 8 % / 20 %** |
| targets flipped to UNDER-estimates | 63 % | 60 % |
| 2-param fit (+ kJ/m hilliness covariate), R² | 0.16 | 0.20 |
| \|error\| after 2-param, med / p90 / p99 | 4.6 % / 11 % / 25 % | 2.7 % / 7 % / 17 % |
| reach-matching budget inflation c_b (range across sources/budgets) | 1.06 – 1.22 | 1.05 – 1.15 |

Findings:

- **A shared constant removes the center, and only the center**: median
  |error| halves-to-thirds, but the p90 tail stays ~8–11 % and extreme
  corridors 20–33 % — the bias is route-structured (which slopes a pair's
  optimal path crosses), and a scalar cannot see that. The obvious
  covariate (energy per metre = hilliness+detour proxy) explains only
  R² ≈ 0.16–0.20 and buys ~nothing at the median: there is no cheap
  2-parameter fix either.
- **The constant is not universal.** It shifts with resolution (1.115 vs
  1.090), varies ±5 pp across source neighborhoods within ONE city crop,
  and will move with the cost bundle (it scales with climb-dominance) and
  geography. "Shared" must mean *calibrated per DEM + parameter set*, not
  a hard-coded number. A cheap in-app calibration exists: run 2–3 refs at
  sq32-profile in the background (~3 s each at 810 k cells) and take
  c ≈ med(E8/E32)·1.02 — the same machinery as this harness.
- **The correction has a real price: one-sidedness.** Raw grid energies
  are guaranteed upper bounds (KPIs are floors); after ÷c* ~60 % of pairs
  become underestimates with ±4 % (med) / ±10 % (p90) pair-level noise.
  For population-aggregated KPIs the pair noise largely averages out — the
  aggregate becomes approximately centered instead of conservative — but
  any "≥ threshold" claim loses its floor semantics.
- **Where it belongs if adopted**: at the threshold/budget layer (inflate
  eMax and the KPI thresholds E₁/E₂ by c — equivalent to deflating
  energies, but keeps a single energy number everywhere, consistent with
  the "viewing energy ≡ routing energy" product rule; a second corrected
  per-cell energy is explicitly NOT allowed by that rule). Honest labeling:
  "grid-corrected estimate (centered)" vs the default "grid-native floor".

### 11. Pre-registered predictions for a 16-move engine (if built)

To be checked by re-running this harness's acceptance criteria against the
real engine: (a) field-median energy drops 5–8 % on the 5 m DTM, 3–5 % at
30 m; (b) budget-reach area grows 9–11 % (5 m); (c) density-run wall time
grows ≤ 3×; (d) passes corridors sharpen along contour lines (visual);
(e) bit-parity JS↔Rust preserved including the profile sub-sampling order.

### 12. Outcome — shipped in v57 (2026-07-12)

All three actionable findings shipped as user options (feature commit
`1ba06ae`, release `19ec3b1`):

- **Move directions** (`#n-dirs`, 4–128, default 8): `buildMoves()` in
  `energy-worker.js` implements the Farey ladder with profile-integrated
  long moves; density runs amortize per-worker long-edge tables (§9.1's
  winner); passes are stamped over swept cells. nDirs ≠ 8 is browser-only —
  the Rust backend keeps the classic 8-move engine, so the parity
  invariant is untouched (the nDirs = 8 default is bit-identical, suite-
  and backend-parity-verified).
- **String pulling** (`#string-pull`): §9.3's route-display tool, applied
  worker-side to the single path and top-N (round/maximize excluded).
- **Grid correction** (`#kpi-corr`): §10's threshold-layer correction with
  the explicit floor-guarantee warning.

**§11 pre-registration scorecard** (validated against the REAL shipped
worker on the 900×900 5 m crop, 3 sources, 2026-07-12):

| prediction | measured | verdict |
|---|---|---|
| (a) field-median energy drop 5–8 % | 3.9 / 8.7 / 4.6 % per source | **borderline** — the band was drawn from the 4-source pooled median and is too narrow for real per-source terrain spread |
| (b) budget-reach gain 9–11 % | 3.1 / 9.4 / 3.3 % per source | **miscalibrated** — reach gain is strongly source-dependent; one of three in band |
| (c) wall time ≤ 3× | ×2.49 (single-source, on-demand) | **confirmed** |
| (d) corridors sharpen along contours | not formally tested (visual) | open |
| (e) JS↔Rust bit-parity preserved | N/A by design — nDirs ≠ 8 never reaches the backend; the 8-default parity is test-asserted | resolved differently than predicted |

Honest reading: the engine behaves as the harness said it would (the
harness IS bit-validated against it), but the pre-registered BANDS were
overconfident about per-source variance — a lesson for future entries:
pre-register distributions, not point ranges.

### 13. Reproduction

```sh
cd docs
curl -O https://simujaules.pedalhidrografi.co/dem/sampa_centro.tif   # 34 MB
(cd ../census && npm install)                                        # geotiff
node grid-sens.mjs --sources 4 --crop 500,1200,900,900               # 5 m ladder (~3 min)
node grid-sens.mjs --sources 6 --crop 500,1200,1500,1500 --decimate 6  # 30 m (~1 min)
node grid-sens.mjs --sources 2 --crop 700,1300,700,700 --flat        # flat control
node grid-correct.mjs --sources 3 --crop 500,1200,900,900            # §10, 5 m (~2 min)
node grid-correct.mjs --sources 6 --crop 500,1200,1500,1500 --decimate 6  # §10, 30 m
node grid-adaptive.mjs --sources 3 --crop 500,1200,900,900           # §9.2, 5 m (~2 min)
node grid-adaptive.mjs --sources 6 --crop 500,1200,1500,1500 --decimate 6 # §9.2, 30 m
node grid-pull.mjs --sources 3 --crop 500,1200,900,900               # §9.3 string pulling
node grid-eik.mjs --sources 1 --crop 800,1400,400,400 --flatcheck    # §9.4 flat validation
node grid-eik.mjs --sources 2 --crop 700,1300,600,600                # §9.4, 5 m
node grid-eik.mjs --sources 3 --crop 500,1200,1500,1500 --decimate 6 # §9.4, 30 m
node grid-longedge.mjs --sources 8 --crop 500,1200,900,900           # §9.1 long-edge tables
```

Every run self-validates its 8-move engine bit-identical against
`energy-worker.js` before reporting. Nothing here ships (`deploy.sh` stages
an explicit file list; `docs/` never deploys).

---

## 2026-07-12 — Entry 24: what the literature says a cumulative-ascent measurement is worth — and why our energy endpoint can decide what geometry cannot

**Lineage** — $I$: — · $T$: literature review · $O$: no $O$ · $S$: what an ascent measurement is worth

*Prompt (Danilo): "literature review on the typical cumulative ascent error when using
consumer grade barometers, and when using FABDEM or terrain data from aerophotogrammetry —
compare to the journal entries." No engine ran; no published number changed. Full survey with
sources: [ascent-error-literature.md](../notes/ascent-error-literature.md).*

**Consumer barometers.** Device-level cumulative-ascent (h₊) error is **~1–5%** under benign
conditions, with between-unit consistency at the ~1–2% level: Menaspà et al. 2014 (IJSPP)
measure CV 1.5% across Garmin head units (0.2% SRM) with brands ~3% apart, and their
follow-up abstract reports dry-conditions under-reads of ~2% (Garmin) / ~5% (SRM); a
28-device figure of 1.5–1.9% standard error circulates via Johnson et al. 2023 (PLOS One).
Sánchez & Villena 2020 (202 mountain efforts vs an aerial-photogrammetry benchmark) find the
*opposite sign* — baro consistently over-estimates, GPS-only under-estimates, ~5% raw →
~1% post-processed. Weather drift is second-order for h₊ (a 6 h field test: ~13 m of
pressure drift → ~15 m spurious gain, ≲1% of a long ride) — it corrupts absolute altitude,
not ascent.

**DEMs.** The DEM literature validates *per-point* elevation, where FABDEM is the best
global source (Hawker 2022: MAE 1.12 m built-up / 2.88 m forest; independent flood-prone
validation 2024: MAE 1.43 m, RMSE 2.62 m, vs GLO-30 ~4.9 m, SRTM ~5.4 m RMSE) and
aerophotogrammetric 5 m DTMs of the IGC class sit at sub-metre-to-~1 m σz. **Per-point
accuracy does not transfer to accumulated ascent.** The one located study measuring h₊
directly (Sánchez et al., ICECET 2024 — trail running vs a 20 cm LiDAR truth) finds a raw
4 m DEM ~12 pp *worse* than the consumer watches it would correct, error growing
monotonically with grid coarsening (+11 pp at 3.2 m → ~+48 pp at 51 m) and
nearest-neighbour sampling badly worse than bilinear everywhere. Consensus direction across
the field: GPS-only under-reads, DEM correction over-reads (Garmin's correction +5–10%,
Menaspà 2014; Strava prioritises baro over its own basemap).

**Against our entries — everything checks, two things are sharper here.**

- Entry 6's DEM-along-track inflation (FABDEM +35%, COP30 +50%, SRTM +71% vs baro,
  bilinear; NN staircase +30 pp) sits inside the literature's band, and the
  bilinear-vs-nearest warning is independently replicated.
- Entry 6's baro −11/−21% vs the IGC 5 m DTM does **not** contradict the lit's 1–5%: the
  small errors are vs monotone climbs or device-vs-device; ours is baro-vs-terrain
  micro-relief at 5 m — a benchmark-scale gap, not device error. Sánchez 2020's
  *over*-reading baro is the same comparison in the on-foot regime, where the athlete's
  path actually traverses the micro-relief.
- Entry 19's FABDEM ascent failure on flat terrain (h₊ +57% pooled, +101/135% on
  P. Paz/JAAM) is consistent with — but sharper than — the literature: per-pixel ~1.5–3 m
  MAE is exactly what accumulates into doubled ascent on lowlands, yet no located DEM
  validation propagates per-point error into along-track h₊ by terrain regime.
- Entry 19's other twist — the *survey-grade* 5 m DTM over-charging energy relative to the
  baro (censo 22.1 vs 12.0 med |Δ%|) — has no located precedent; the nearest is ICECET's
  "raw 4 m DEM worse than the watch", which agrees in direction.

**The decidability point (the reason this entry exists).** The scale literature
(swisstopo's coastline-paradox note; Rapaport, already in
[literature-context.md](literature-context.md)) ends at: h₊ has no true value, only a value
at a chosen smoothing scale — so "which ascent is right?" is ill-posed as a *geometry*
question, and the sign disagreements above are unresolvable on their own terms (each
benchmark just embodies a different scale). Our harness adds the external referee geometry
lacks: measured pedalling energy `∫P·dt`. "Which h₊ best predicts the energy actually spent
through `β·h₊`?" has a well-defined loss, which turns the smoothing scale from a convention
into a *fittable parameter* — that is literally Entry 20 (σ\* = 10 m and per-rider kSmooth
fall out of minimising energy error, not chosen a priori), and Entry 21's finding that the
fitted scale is a function of (Δx, terrain regime) is then a result, not a nuisance. Two
qualifiers: it is decidable *for a purpose* (energy-effective ascent for a road bike — a
trail runner's referee would pick a finer scale, which dissolves the Menaspà/Sánchez sign
conflict), and the answer is rider/terrain-conditional, not universal. No located study
validates any ascent source against measured pedalling energy; that gap is where
Entries 19–21 live.

Tooling: none (survey only). Sources and the full comparison table:
[ascent-error-literature.md](../notes/ascent-error-literature.md).

---

## 2026-07-11 — Entry 23: move-grid connectivity bias in simujaules terrain-mode optimal energy

**Lineage** — $I$: — · $T$: move-grid connectivity · $O$: no new $O$ (imported note) · $S$: connectivity bias in terrain mode

*Prepared in the simujaules session and imported here. The full tables, threats-to-validity, and
the reproducible harness live in the sibling repo:
`../simujaules/docs/grid-connectivity-sensitivity-2026-07-11.md` (the canonical long-form note) +
`docs/grid-sens.mjs` and companions — simujaules commits `f83f2f9`→`17ee186` (note),
`1ba06ae` (v57 options). Paths below are relative to `../simujaules/`.*

**Question** (Danilo): does the 8-connected move grid make terrain mode
overestimate optimal energy via route jaggedness? Sensitivity vs 16-move
requested; extended to square 4/8/16/32/64/128 (Farey heading ladders) and
hexagonal 6/12, all profile-integrated, with square-128 as the converged
near-continuum reference (sq64 within 0.2–0.9 % of it).

**Verdict: yes — and terrain ≈ doubles the pure-geometry prediction.**
On a 900×900 central-SP crop of the deployed IGC 5 m DTM (v55 σ=10 m
smoothing, UI-default physics, 4 sources, targets ≥ 800 m):

- **sq8 vs continuum: +12.7 % median, +21.3 % mean, +47 % p90.** At an
  emulated 30 m (anti-aliased 6× decimation): +8.1 % / +9.7 % / +18 %.
  Flat-terrain control: +5.7 % median — i.e. real terrain doubles it.
- **Budget reach** (area within the median of the source's own E8 field)
  undercounts by **~19 %** (5 m) / ~15 % (30 m) vs continuum — the KPI
  counting in simujaules is a conservative floor. Bias is one-sided: grid
  results are upper bounds.
- **sq16 (profile-integrated) recovers ≈ ⅔ of the bias** (12.7→5.8 %
  median at 5 m; 8.1→2.7 % at 30 m) at ~2.5–3× relax cost; sq32 gets within
  1–2 %. Hex-6 is WORSE than sq8; hex-12 sits between sq8 and sq16 —
  dominated by sq16 on the existing raster. sq4 would be catastrophic
  (+28–32 % median): the original 8-choice is vindicated.

**Mechanism.** Not octile distance inflation. On flat ground the E8/E16 gap
follows octile theory exactly (0.8 %→6.9 %→1.0 % across the 0–45° fold,
peak at 22.5–30°; lattice worst cases reproduced: sq4 41.3 % ≈ √2−1, sq8
9.2 % ≈ 8.24 % bound, hex6 16.2 % ≈ 2/√3−1). On terrain the direction
signature VANISHES (5.7–7.8 % medians across all headings) and the gap
doubles: the dominant cost is **height oscillation** — an 8-grid path
tracking a contour must zigzag across it, and the asymmetric cost (climb at
β = 0.7585 kJ/m; descent refunded at ε·β, ε ≤ 1 − 0.13; flat travel
0.0142 kJ/m) taxes every oscillation. Hence bias grows with terrain detail
(5 m > 30 m > flat).

**Methodological trap worth recording** (the reason naive comparisons
mislead): long moves costed from endpoint Δh alone *flatten the relief they
cross* — a terrain-resampling change masquerading as a jaggedness fix
(skipping one 1 m bump fakes more saving than ~50 m of straightening).
Naive sq16 at 30 m reads **−1.3 % median vs continuum** (true: +2.7 %);
naive sq32 **−8.5 %** (true: +0.9 %) — the error's sign flips and the
upper-bound guarantee dies. Where a naive ladder lands near zero (sq32 at
5 m: −0.2 %) it is two large errors cancelling. All reported ladders
therefore use profile-integrated long edges (bilinear height samples every
~1 cell, v2Edge per sub-segment — still O(1)-local, so compatible with the
Entry-18 engine constraint). Any future 16-move work order MUST specify
profile integration and use this harness as its acceptance test.

**Relation to prior entries.** Independent of Entry 19's cost-model
resolution over-charge (~+9 % median at 5 m along fixed routes): this is a
search-discretization bias on route-optimal energies. Both are one-sided
positive on fine DTMs and compound toward conservative terrain-mode
energies; neither affects graph/network mode. Per-rider calibration
(Entry 20) remains the accuracy carrier for absolute kJ.

**Validation.** The harness self-validates its 8-move engine bit-identical
(max|Δ| = 0, zero finite-mismatches) against the real `energy-worker.js` on
every run, and the flat control reproduces each lattice's closed-form worst
case — both held on all reported runs.

**Cost–accuracy scaling law** (measured per-mode times, 810 k cells:
sq8 0.47 s → sq16 1.13 → sq32 2.71 → sq64 7.22 → sq128 18.1): with error ∝
time^(−k), the rough-terrain ladder gives k ≈ 0.90/1.16/1.28 per step
(overall 1.12) — **error × time ≈ constant**, "3× less error for 3× more
time", with no knee in the curve itself. k ≈ 1 is the natural ceiling for
uniform heading ladders in the terrain-dominated regime (cost doubles per
level with edge count; the contour-oscillation error term only halves with
the heading gap); on smoother terrain k rises toward the flat-geometry
quadratic (30 m: 1.25–1.9; flat: ~1.7). The stopping rule therefore comes
from external floors: sq16's 5.8 % residual is already at the Entry-19
model-bias/calibration scale, sq32's 2.1 % below it. Hex points sit off the
square Pareto frontier (hex12: 1.34 s / 7.9 % vs sq16 1.13 s / 5.8 %).
Candidate routes to k < 1 (simujaules note §9): **slope-adaptive
neighborhoods were tried and REFUTED on this terrain**
(`docs/grid-adaptive.mjs`; long moves gated by either-endpoint local grade;
edge-set nesting E8 ≥ E_ad ≥ E_uniform held with 0 violations): at the
thresholds that preserve accuracy the steep-cell share is 91–98 % (5 m) /
96–100 % (30 m) — central SP has no flat fraction to skip — and the first
threshold that prunes (4 % grade, 65 % steep) degrades error faster than
time (k 0.69, worse than uniform); the gate only pays where the bias is
already small, i.e. dominated. **String pulling — tried**
(`docs/grid-pull.mjs`; windowed DP over the 8-grid path with
profile-integrated straight segments, iterated over surviving breakpoints):
recovers **44 % of the median path bias (9.6 → 5.4 %) at ~60 ms/path**;
iteration adds nothing — the residual is corridor lock-in (the
route-choice component of the bias is unrecoverable post hoc). Excellent
for the displayed route/top-N (result stays an upper bound and is its own
integrated cost); useless for fields; loses to a sq16 field for the K×K
accessibility matrix at K ≳ 12. **Anisotropic Eikonal — evaluated**
(`docs/grid-eik.mjs`; semi-Lagrangian fast-sweeping, foot point anywhere on
the radius-1 ring, u and h bilinear at the foot ⇒ effectively continuous
headings; Gauss-Seidel sweeps absorb the anisotropy): on flat terrain it
eliminates heading bias exactly as promised (0.18 % mean vs the analytic
answer, vs sq8's 3.9 %, in 2 sweep-groups); on real terrain it lands
**BELOW** the converged sq128 reference — −1.3/−1.5 % median at 5 m, −4 to
−12 % at 30 m (12–17 sweep-groups) — while the true continuum sits only
~0.2 % below sq128: bilinear foot heights smooth within-cell relief and
undercharge climbs, the semi-Lagrangian sibling of the naive-long-edge
artifact, scaling with per-cell relief. At the app's resolutions the
ladder dominates it (sq32: +1.6–2 % guaranteed-sign error at a fraction of
the cost), and it forfeits passes counts, budget early-exit, bit-parity,
and the floor guarantee in both directions. **Precomputed long-edge tables
— tried: the one candidate that works, for density runs**
(`docs/grid-longedge.mjs`; every long move's profile integral stored in
per-directed-heading tables, relaxed by lookup). Structural fact
confirmed: one Dijkstra integrates each directed edge exactly once
(settled-guard), so K=1 LOSES (sq16 1.53 s vs 0.92 s incl. precompute);
the win is amortized across searches sharing the grid — the density pool's
exact shape. Measured: per-search 0.92 → 0.66 s (sq16, −28 %) and
2.34 → 1.20 s (sq32, −49 %) — more than the sub-step share, since lookup
also skips sweep checks and bilinear reads; break-even ~3 searches;
**bit-identical** to on-demand (max|Δ| = 0). Amortized ladder economics
for density/KPI runs: sq16 ×1.40 cost for ÷2.19 error → **k ≈ 2.3**; sq32
×2.55 for ÷6.05 → **k ≈ 1.9**. Binding constraint: memory (64 B/cell sq16
f64; ~4.3 GB f32 on the 135 M-cell target — per-slice recompute there).
Bottom line after testing all four candidates: exactly one beats k ≈ 1
and only in the density regime — precomputed long-edge tables; the
efficient frontier is sq16/32-with-tables for density/KPI fields,
on-demand integration for single-source runs (k ≈ 1 stands), string
pulling for displayed routes, and the threshold-layer correction where a
centered aggregate beats a floor.

**Parametric correction — how far a shared constant goes**
(`docs/grid-correct.mjs`): deflating energies (equivalently inflating the
budget/thresholds) by a per-condition constant c* (1.115 at 5 m, 1.090 at
30 m) halves-to-thirds the median |error| (9.3 → 4.1 % at 5 m; 8.1 → 2.6 %
at 30 m) **but only the center moves**: p90 stays 8–11 %, extreme corridors
20–33 %, and ~60 % of pairs flip to underestimates — the one-sided
floor guarantee dies. The bias is route-structured: a kJ/m hilliness
covariate explains only R² ≈ 0.16–0.20 and buys nothing at the median (no
cheap 2-parameter fix). The constant is NOT universal — ±5 pp across source
neighborhoods within one city crop, resolution-dependent, cost-bundle-
dependent — so it must be calibrated per DEM + parameter set (a background
2–3-ref sq32 probe suffices, ~3 s/ref). If adopted, it belongs at the
threshold/budget layer (inflate eMax/E₁/E₂ by c), labeled as a centered
estimate vs the default grid-native floor; a second corrected per-cell
energy number would violate the viewing≡routing product rule.

**Pre-registered predictions if a 16-move engine is built**: field-median
energy −5–8 % (5 m) / −3–5 % (30 m); budget-reach +9–11 % (5 m); density
wall time ≤ 3×; passes corridors sharpen along contours; JS↔Rust bit-parity
preserved including sub-sampling order.

**Outcome (2026-07-12): shipped and scored.** All three actionable findings
shipped as options in simujaules v57 (live at
simujaules.pedalhidrografi.co): a move-directions select (4–128, default 8
bit-identical; Farey ladder with profile-integrated long moves, amortized
per-worker tables in density runs, passes stamped over swept cells;
non-8 browser-only so the Rust-parity invariant is untouched), string
pulling for the displayed route/top-N, and the KPI grid-correction input
(threshold layer, with the floor-guarantee warning). Pre-registration
scorecard against the REAL shipped worker (900×900 5 m crop, 3 sources):
wall time ×2.49 ≤ 3 **confirmed**; field-median energy drop 3.9–8.7 % per
source vs the predicted 5–8 % band — **borderline** (band too narrow for
per-source terrain spread); budget-reach gain 3.1–9.4 % vs 9–11 % —
**miscalibrated** (strongly source-dependent); JS↔Rust parity resolved by
design rather than by porting. Methodological lesson worth recording:
pre-register distributions, not point ranges.

**Reproduce**: see the reproduction section of the simujaules note
(`docs/grid-sens.mjs` + companion harnesses; needs `sampa_centro.tif` +
`census/node_modules`; ~5 min total for the three main conditions).

---

## 2026-07-09 — Entry 22: error bars for the headline medians — the champion "beats" the sim only on the median, so the article now claims parity

**Lineage** — $I$: every $O$ above · $T$: stratified bootstrap, B = 10⁴ · $O$: — · $S$: **every published median AND its 95% band**

*Prompt (Danilo): revise the article for the review weaknesses — fold Entries 19–21 in, re-frame
the title/abstract around what transfers, and put uncertainty on the headline numbers. This entry
records the new statistics; no engine ran and no published median changed.*

**What was computed.** [`bootstrap_ci.py`](../../src/harness/bootstrap_ci.py) reads the
per-ride CSVs already written by the other harnesses (`model_comparison`, `censo_comparison`,
`ppaz_comparison`, `jaam_comparison`, `time_comparison` — no FIT parsing, no engines) and adds
two kinds of statistics the article previously lacked:

- **Bootstrap 95% CIs on the headline medians** (percentile method, 10⁴ resamples over rides,
  deterministic seed). Gate: every published median must reproduce to the journal's 1-decimal
  rounding (±0.11) before its CI is reported — all gates pass, exit non-zero otherwise. The time
  endpoint reproduces only against `tMovBin` (the harness's actual scoreboard target), not
  `tMov` — mind that if reusing the CSV.
- **Exact two-sided paired sign tests on |Δ%|** for every head-to-head the article states as a
  ranking.

**The one finding that changed a claim.** On the 44 longões, the champion (cf + 2 m deadband,
3.6% median) vs the canonical sim (5.1%): CIs **[2.0, 5.6] vs [3.8, 7.1]** overlap, and paired,
the champion is closer on only **25/44 rides (57%, sign test p = 0.45)**. The "beats the forward
simulation" headline was a median-point comparison that the paired test does not support. The
article (v0.16) now claims **statistical parity** everywhere it said "beats" (abstract, §8.1,
Fig. 1 caption, §11) — which is still the practically decisive result, since the closed form is
the engine cheap enough to route with.

**Rankings that ARE paired-significant** (and now say so in §8.4/§8.6): P. Paz pm·ε_geom beats
the flat-ε 0.20 variant on 76% of rides and the canonical sim on 60% (both p < 10⁻⁴); JAAM
sm·ε=0.20 beats sm·ε_geom on 65% (p < 10⁻⁴). Parity results stated as such: censo pm·ε=0.20 vs
canonical 33/62 (p = 0.70). The §8.8 time endpoint keeps its already-published paired tests
(56% of 433, p = 0.011) and gains CIs (T1b 6.6 [5.9, 7.2] vs T0 7.6 [7.0, 8.5]).

**Article v0.16 (both languages), the rest of the revision.** New **§8.9** compresses Entries
19–21 (resolution over-charge → pre-registered goal PASS with calibration as the lever →
scale/terrain-dependent behavioural trio); the recipe moves to **§8.10** and gains a calibration
step 7. Title re-framed ("a Descent-Recovery Offset That Transfers Across Riders" — the offset is
the robust piece, not the geometric skill). §6.3 flags the implicit-scale consequence; §7.1
documents the CI/sign-test methodology; §9.1 corrects the outdated "~30 m grid the deployment
uses" claim (the usual raster is the 5 m IGC-SP) and records the shipped v55 σ = 10 m
pre-smoothing; §10.2 gains a provenance row; §10.4 scopes the calibration result against
planning-mode; §11 adds the constants-are-the-frontier finding and the terrain-indexed-trio open
question. `article-draft.pt-BR.md` mirrors every change.

Tooling: `python3 bootstrap_ci.py` (instant; needs only the gitignored per-ride CSVs; exits
non-zero on any gate failure).

---

## 2026-07-07 — Entry 21: hypothesis — the resolution gap is a parameter problem, not a DEM problem

**Lineage** — $I$: $(\mathrm{DEM}, P_{a,g})$ · $T$: v2Edge, three scales · $O$: `scale_trio.csv` (922) · $S$: **the scale prescription** (paper 2/3)

*Prompt (Danilo, `/goal`): "Can we bridge that gap through parameters on the closed form
rather than messing with the DEM? Investigate and make an hypothesis. Purely empirical is
fine, physically/behaviourally-coherent is desirable."*

### The hypothesis (H21)

**The closed form's constants split into two kinds.** The *rider physics* (m, CdA, C_rr, ρ,
k_eff) are scale-free. The *behavioural/calibration* constants are **functions of the profile
sampling interval Δx, by construction**: ε₀ = 0.13 was calibrated on **30 m descent cells**
(Entry 8); k_s is the roller/momentum discount whose target — the sub-resolution relief a
rider coasts over — is exactly what changes when Δx changes; climbThr = 2% separates "real
climb" from "undulation" at some reference scale. Entry 19's "resolution over-charge" is then
not a DEM defect but **stale calibration: 30 m constants applied to 5 m grades**. H21: a
single, rider-independent re-calibration of the trio **(k_s, ε₀, climbThr)** at Δx = 5 m
bridges the gap — no DEM modification — and, fitted this way, the per-rider physics recovered
on top land nearer physically plausible values than Entry 20's contaminated effective fits
(which pushed JAAM's CdA to 0.55 and C_rr to 0.0043 to absorb resolution error).

*Supporting evidence already on file:* Entry 20's σ=0-calibrated ablation PASSED validation
(3.66/2.25/4.95) — parameters demonstrably CAN absorb the gap; the open question is whether
they can do it coherently (shared, rider-independent, mechanism-matched) rather than by
per-rider effective-value contamination. Entry 20's mechanism decomposition gives the
targets: h₊(igc5) > h₊(igc30) on 919/922 rides (k_s's mechanism) and implied drop-weighted
ε 0.414@5 m vs 0.456@30 m (ε₀'s mechanism).

### Pre-registered protocol

- **Two-stage design — the trio is fitted as a pure RESOLUTION TRANSFER, never against
  measured energies.** Stage 1 (geometric): fit shared (k_s, ε₀, climbThr) so the 5 m walk
  reproduces the 30 m walk ride-by-ride — minimize the median (equal-weighted across the
  three rider corpora) of |v2(igc5; trio, frozen physics) / v2(igc30; default constants,
  frozen physics) − 1| over TRAIN rides (Entry 20's split, reused verbatim). Measured ∫P·dt
  is never touched in stage 1, so the trio cannot absorb rider-physics error by
  construction. Stage 2 (accuracy, evaluated once on VALIDATION): does igc5+trio inherit
  igc30's measured accuracy?
- **Data**: Entry 20's cached profiles (864 rides × {igc5, igc30}), same hash split. Plus
  the 58 censo rides' igc5/igc30 profiles (sampled the same way) as a **fully out-of-sample
  transfer corpus** — censo is never used in any fit (and its group-ride drafting confounds
  absolute accuracy, so it enters only the gap-closure comparison, not the accuracy gate).
- **Search space**: k_s ∈ [0.6, 1.0], ε₀ ∈ [0.0, 0.20], climbThr ∈ [0.01, 0.04];
  deterministic coarse-to-fine grid. Ablations: k_s-only, ε₀-only, k_s+ε₀, full trio —
  attribute the gap between the two mechanisms.
- **Endpoints** (validation split, frozen journal physics):
  - **E1 (gap closure)**: per-corpus med |Δ%| and bias of v2@igc5+trio vs the igc30-frozen
    anchor (Entry 20 numbers). Bridged = igc5+trio within 1.0 pp med|Δ%| and 1.5 pp bias of
    igc30-frozen, per corpus, INCLUDING the unfitted censo.
  - **E2 (coherence of physics on top)**: re-fit per-rider (CdA, C_rr) ONLY (k_s now owned
    by the shared trio; mass frozen) on train at igc5+trio; validation must still meet the
    Entry-20 goal gates (med|Δ%| < 5, |bias| < 2); and the fitted CdA/C_rr should land
    nearer the plausible ranges (CdA 0.25–0.45, C_rr 0.004–0.012) than Entry 20's σ=0 fits.
- **Coherence predictions** (each checkable, each falsifies part of H21):
  - P1: fitted ε₀(5 m) < 0.13, and the implied drop-weighted 5 m ε moves to ≈ the 30 m
    implied value (0.456 pooled).
  - P2: fitted k_s < 1, consistent in magnitude with the median h₊(igc30)/h₊(igc5) ratio
    (~0.88 on censo-like terrain) — though k_s also scales the descent credit, so exact
    equality is not expected, only the right ballpark and sign.
  - P3: the trio transfers to censo (biggest gap corpus, zero fitting exposure).
  - P4: trio-corrected per-ride energies correlate with igc30 energies tighter than
    igc5-default does (the transfer is per-ride, not just in the median).
- **Deployment note (if H21 holds)**: the app could ship "Δx-aware default constants"
  (set k_s/ε₀/climbThr defaults from the DEM pixel size at load) as a parameters-only
  alternative to v55's raster smoothing — same requirements-compatibility (O(1)-local,
  viewing ≡ routing), zero DEM mutation. NOT implemented as part of this entry.
- **Caveat pinned upfront**: matching ride TOTALS along fixed paths is the first-order
  target; edge-level costs (hence field shapes/route choice) may still differ between
  igc5+trio and igc30 — flagged for a follow-up if H21 holds.

### Results — H21 partially supported: parameters DO bridge the gap, but only within the terrain regime they were fitted on

**Integrity.** Harness [`scale_trio.py`](../../src/harness/scale_trio.py) (engines verbatim;
stage-1 inner loop uses an exact algebraic decomposition of the walk, asserted ≡ the verbatim
engine to 6.8e-10 kJ at every reported set). All gates pass: Entry-19 per-ride reproduction
(riders AND the newly-sampled censo igc5/igc30, worst 5e-5 kJ), Entry-20 igc5-frozen anchors
reproduced (8.53/2.64/14.84), dead-clamp global min **+2.14 J** on every non-degenerate set
(the k_s=1, ε₀=0 grid corner is exactly 0 by algebra — fp ulps, not a live clamp), analysis
double-run byte-identical.

**Stage 1 (geometric fit, measured energies never touched).** Fitted trio:
**k_s = 0.9375, ε₀ = 0.0632, climbThr = 0.025**; train objective (mean corpus-median
|v2(igc5;trio)/v2(igc30;default) − 1|) 0.0282 → **0.0076**. Ablations: k_s alone does most of
the work (→ 0.0083, at k_s = 0.8844); ε₀ alone → 0.0127. The two knobs trade off (k_s+ε₀
lands at 0.869/0.144) — the trio's k_s sits higher (0.9375) because ε₀ 0.13→0.063 takes over
part of the correction.

**E1 — gap closure (validation, frozen physics; med|Δ%| / bias):**

| corpus | igc5 default | igc30 default (target) | igc5 + trio | bridged? |
|---|---|---|---|:--|
| ppaz (121) | 8.53 / +8.53 | 7.64 / +7.44 | 7.60 / +7.60 | **YES** (Δ 0.05 / 0.16 pp) |
| jaam (94) | 2.64 / −0.31 | 2.83 / −1.86 | 2.67 / −1.31 | **YES** (0.16 / 0.55) |
| danlessa (216) | 14.84 / +14.81 | 9.89 / +9.45 | 10.51 / +10.45 | **YES** (0.62 / 1.00) |
| **censo (58, o-o-s)** | 22.10 / +22.10 | 12.26 / +12.26 | 16.71 / +16.71 | **NO** (4.44 / 4.44) |

**Coherence:** P1 holds — ε₀(5 m) = 0.063 < 0.13, implied drop-weighted ε moves 0.414 →
0.479 ≈ the 30 m value 0.456 (pooled). P2 holds strikingly — the k_s-only fit (0.8844) lands
essentially ON the median h₊(igc30)/h₊(igc5) ratio (0.8958 pooled): k_s is doing exactly its
roller-discount job. P4 holds for the riders — per-ride ratios move to ≈1.00 with IQRs
shrinking (e.g. danlessa validation 1.050/0.028 → 1.009/0.023), so it is a genuine per-ride
transfer, not a median artifact. **P3 fails**: censo (never fitted, flattest terrain, biggest
gap) closes only ~55% of its 9.8 pp gap. **E2 fails its gate**: per-rider (CdA, C_rr) refit
on top passes ppaz (4.83/+0.54) and jaam (2.38/+0.36) but danlessa lands 5.22/−0.37 (0.22 pp
over); and the recovered physics is NOT systematically more plausible than Entry 20's (3/6
parameters in plausible range before and after — the residual bias now escapes into C_rr↓
0.0037/0.0032 instead of CdA).

**Verdict — the refined hypothesis.** The answer to the prompt is **yes, with a scope
limit**: a single rider-independent, mechanism-coherent re-calibration of the behavioural
trio at Δx = 5 m — fitted purely as a resolution transfer, no DEM edits, no measured data —
bridges the resolution gap **on the terrain regime it was fitted on** (all three rider
corpora, per-ride, with each constant moving exactly as its mechanism predicts). What
falsifies the strong form is censo: **the resolution error is terrain-dependent** (flat urban
terrain has proportionally more sub-30 m roller content — its h₊ ratio is 0.867 vs the
riders' ~0.90 — and one constant k_s cannot carry both regimes). So H21 refines to:
**the behavioural constants are functions of (Δx, terrain-roughness regime), not of Δx
alone.** A constant trio is a good parameters-only bridge for open/hilly riding; the v55
raster smoothing remains the terrain-adaptive fix (it acts per-cell, so flat and hilly
regions each lose exactly their own sub-σ relief) — which is WHY it transfers where the trio
does not. Practical reading for sampasimu: Δx-aware default constants would be an honest
lightweight fallback when a user disables smoothing, but they are not a full substitute; and
the E2 outcome cautions that per-rider "physics" fitted on top of ANY resolution correction
still absorbs behavioural residuals (drafting, position, meter) — treat fitted CdA/C_rr as
effective values regardless.

Tooling: `python3 scale_trio.py` (~5 min cold, ~15 s cache-hit; reuses Entry 20's profile
cache + Entry 19's warp raster; writes the gitignored `scale_trio.csv`).

---

## 2026-07-07 — Entry 20: goal-driven — can the deployed pipeline hit ±5% error / ±2% bias?

**Lineage** — $I$: $(\mathrm{DEM}, P_{a,g})$ · $T$: v2Edge + smoothing sweep · $O$: `goal_calibration.csv` (864) · $S$: the ±5%/±2% goal; anchor constants

*Prompt (Danilo, `/goal`): "Simujaules, when routing a path, should have a prediction error of
less than ±5%, with a bias lower than ±2%. danlessa/ppaz/jaam as the training/validation
datasets."*

**Metric interpretation (stated so it can be contested).** Per-corpus **validation-set**
med |Δ%| < 5 **and** |median signed Δ%| < 2, for each of the three riders' Entry-19 coverage
sets, with Δ% = (deployed prediction − measured ∫P·dt)/measured. "Deployed prediction" = the
v2Edge walk on `sampa_geral.tif`-derived profiles at 5 m arc steps (the app's pipeline),
plus only levers that are actually deployable in the app. Censo is excluded by the goal's own
dataset list (group rides — drafting breaks the single-rider energy balance).

### Scoping (from Entry 19's per-ride CSV — no new computation)

- Baseline deployed (igc5, frozen journal physics, no calibration): ppaz 9.0/+9.0,
  jaam 2.9/−0.5, danlessa 14.8/+14.7 — only jaam passes.
- Split-simulated protocol (50/50 hash split; per-rider **scalar** fitted on train; 30 m
  regime as smoothing proxy): validation ppaz **4.69/−0.70 PASS**, jaam **2.48/+0.22 PASS**,
  danlessa **5.23/−0.17** — bias passes, scatter fails by 0.23 pp.
- danlessa's train residual structure at 30 m (post-scalar): slow-v_f tercile **+5.17**
  medΔ% (med|Δ%| 10.2) vs fast tercile −2.01 (3.14); hilliness terciles −1.7 → +2.6. Both
  tilts map onto app-native knobs: the CdA/Crr split acts through v_f², kSmooth scales β.

### Pre-registered protocol (declared before any tuning run)

- **Split**: within each rider's Entry-19 coverage set, deterministic 50/50 by
  `sha256('entry20:' + rideName)` parity — train = even, validation = odd. Validation is
  evaluated ONCE, at the end, at frozen settings; no peeking during tuning.
- **Lever 1 (global, deployable — the Entry 19 roadmap mitigation)**: static Gaussian
  pre-smoothing of the 5 m raster, σ ∈ {0, 10, 15, 20, 30, 45} m, profiles sampled at 5 m
  arc steps off the smoothed raster (the app keeps its 5 m grid; heights are prepared
  app-side at DEM load and shipped identically to all three engines — no parity impact).
  σ selected on TRAIN only: minimize the worst corpus's train med |Δ%| after per-rider fits.
  *Amendment (pre-results): the smoothing scheme is pinned to the DEPLOYABLE form — 
  sequential per-axis mask-normalized Gaussian passes (rows then columns, truncation 3σ,
  per-axis σ_px from the geotransform), which the app can run in place at 135 M cells with
  O(row) temp memory — not the exact 2-D normalized convolution (identical away from nodata
  holes; differs only near hole edges). The harness tests exactly what would ship.*
- **Lever 2 (per-rider, deployable = the app's parameter panel)**: fit
  (CdA ∈ [0.2, 0.6], Crr ∈ [0.003, 0.015], kSmooth ∈ [0.5, 1.0]) per rider on TRAIN;
  mass FROZEN at the journal values (74.3 / 101.7 / 74.5), ρ 1.13, k_eff 0.98, per-ride
  P_flat from the ride's own extracted flat power (deployment analog: the rider knows their
  day's flat power). v_f, abRatio, and ε are recomputed inside the fit (flatEqSpeed depends
  on CdA/Crr). Objective per rider: minimize train med |Δ%| subject to |train medΔ%| ≤ 1
  (a buffer inside the 2% criterion).
- **Endpoint**: the three validation sets at the frozen (σ, per-rider params). PASS = all
  three meet med |Δ%| < 5 ∧ |medΔ%| < 2.
- **Fallback ladder** (only if validation fails; pre-declared): (F1) refit with `epsOffset`
  as a 4th, SHARED (never per-rider) parameter — it is a behavioural constant the journal
  calibrated once, so re-fitting it demands this explicit disclosure; (F2) report the honest
  failure and stop — no per-rider σ, no post-hoc ride exclusions, no metric reinterpretation.
- **Sanity gates**: σ=0 uncalibrated reproduces Entry 19's igc5 numbers exactly; the
  calibrator at the frozen journal physics reproduces the cached v2_igc5 per ride; profile
  cache determinism (two builds byte-identical); the Entry-18 dead-clamp assert on every
  walked profile.

### Results — **PRIMARY ENDPOINT: PASS** (no fallback needed)

**Integrity.** Harness [`goal_calibration.py`](../../src/harness/goal_calibration.py) +
[`goal_smooth_rasters.py`](../../src/harness/goal_smooth_rasters.py) (the amended deployable
smoothing scheme, constants pinned in both headers for the app port). 864 rides
(277/181/406), split 156/121 · 87/94 · 190/216 (train/validation). Sanity gates: σ=0 frozen
physics ≡ Entry 19's `v2_igc5` to 5.0e-5 kJ; dead-clamp global min pre-clamp edge **+2.44 J**
across every profile at every evaluated parameter set; Phase C run twice → byte-identical
(sha256-matched); cache spot-rebuild (every 40th ride, fresh from FIT+gdal) byte-identical.
Gate 5 (h₊ monotone in σ) FAILED as literally stated and was diagnosed benign: at the
SELECTED σ\*=10, h₊(σ10) < h₊(σ0) on **864/864** rides; the ≥1-uptick rides (107/864, worst
+5.5% on a single step) are all at σ≥20 — large-σ displacement of steep terrain, inherent to
the scheme, absent at the deployed σ.

**Train matrix** (post-fit train med|Δ%|, per-rider (CdA, Crr, kSmooth) fitted at each σ,
|medΔ%|≤1 constraint): worst corpus = 4.02 (σ0), **3.95 (σ10)**, 3.96 (σ15), 4.15 (σ20),
4.16 (σ30), 4.25 (σ45) → **σ\* = 10 m** by the pre-registered rule. Fitted at σ\*:
ppaz (0.206, 0.0142, 0.548), jaam (0.378, 0.0097, 0.976), danlessa (0.348, 0.0077, 0.768) —
*effective* values (they absorb residual model/resolution bias; do not read them as physical
CdA/Crr).

**Validation (single frozen eval at σ\*=10 + per-rider fits):**

| corpus | n | med \|Δ%\| | med Δ% | p10 | p90 | gate (<5 ∧ <±2) |
|---|--:|--:|--:|--:|--:|:--|
| ppaz | 121 | **3.69** | **+0.96** | −7.2 | +7.2 | **PASS** |
| jaam | 94 | **2.74** | **+0.31** | −3.4 | +5.8 | **PASS** |
| danlessa | 216 | **4.94** | **+0.81** | −7.7 | +14.9 | **PASS** (margin 0.06 pp) |

**Ablations (validation sets) — the honest decomposition:**

- **σ=0 calibrated** (σ0-fitted params): 3.66 / 2.25 / 4.95 — also passes all three.
  **Post-calibration, smoothing buys ≈ nothing**: the per-rider calibration is the lever
  that carries the goal; the effective parameters absorb the resolution bias. σ\*=10 remains
  the *validated* deployed configuration (it is what the pre-registered selection produced,
  and its params need their σ: σ=0 with σ\*-fitted params FAILS danlessa at +2.77 bias).
- **σ\*=10 uncalibrated** (frozen journal physics): 8.74/+8.74 FAIL, 2.65/−1.31 PASS,
  11.96/+11.83 FAIL — light smoothing alone does NOT rescue uncalibrated accuracy (the
  Entry-19 30 m regime needed σ≈30-equivalent averaging; σ10 is deliberately lighter).
- **σ=0 uncalibrated** (the deployed baseline, validation split): 8.53 / 2.64 / 14.84 —
  fails, as Entry 19 said.

**Verdict.** The goal — validation med |Δ%| < 5 with |bias| < 2% per rider — is **met** by
the deployable configuration (σ\*=10 m mask-normalized pre-smoothing + per-rider effective
(CdA, Crr, kSmooth) calibrated on the rider's own ~100–200 rides, mass frozen at the known
value). The single biggest lever is the calibration, not the smoothing — matching Entry 17's
bias-trade lesson from the other side: with well-chosen constants the model family is
already good enough, and the constants are learnable from a rider's history. danlessa passes
with 0.06 pp of margin — treat that corpus as at-spec, not comfortably inside it (its full
export spans 9 years of bikes/meters/loadouts; per-era calibration would likely widen the
margin but was not pre-registered, so it was not run).

*Deviations (disclosed):* ride-set membership taken from Entry 19's CSV (equivalence
enforced per ride by the emp + v2_igc5 reproduction gates); cache determinism verified by
fresh-rebuilding every 40th ride rather than a full second build; Phase A implemented per
the pre-registration's deployable-scheme amendment.

Tooling: `python3 goal_calibration.py` (~25 min full; needs the conda python for the raster
prep, gdallocationinfo, `sampa_geral.tif`; writes the gitignored `goal_calibration.csv`).

---

## 2026-07-06 — Entry 19: the app on its usual DEM — v2Edge on the deployed IGC-SP 5 m raster vs a 30 m resample

**Lineage** — $I$: $(\mathrm{DEM}_{5\,\mathrm{m}}, \mathrm{DEM}_{30\,\mathrm{m}})$ · $T$: v2Edge · $O$: `igc_resolution_test.csv` (922) · $S$: the resolution gap

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
ε rule exactly as in `regime_compare.py`. The censo endpoint stays as declared; the pooled
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
verbatim from `regime_compare.py`) and the **R0 champion** (smooth cf + 2 m deadband, censo ε
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
`regime_compare.py` (byte-identical by construction); the full run executed twice with
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
(censo stays flat 0.20); engine reuse by runtime extraction + eval of `regime_compare.py`
(stronger than substring assertion); `sampa_geral.tif` has no declared nodata — un-surveyed
cells read 0, so validity = sample > 0.5 m; the RMS-gate note above. No subsampling anywhere.

Tooling: `python3 igc_resolution_test.py` (~15 min; needs `gdalwarp`/`gdallocationinfo`, the
sampasimu `dem/sampa_geral.tif`, and network for the FABDEM tile on first run; writes the
gitignored `igc_resolution_test.csv`).

---

## 2026-07-06 — Entry 18: correction — R1a is not sampasimu's realisation (the app's per-edge ε never clamps), and the Jensen sign flips

**Lineage** — $I$: $(D_1..D_5, P_{a,g})$ · $T$: v2Edge (unclamped) · $O$: `regime_comparison.csv` (1,402) · $S$: correction: the app's per-edge $\varepsilon$ never clamps

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
[`verify_v2edge_clamp.py`](../../src/harness/verify_v2edge_clamp.py): a 1.78 M-combo sweep
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
running: add **R1d** to `regime_compare.py` — per-edge over the same deadbanded 5 m profile
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

R1d ran as pre-registered (`regime_compare.py`, verbatim `v2Edge` walk; sanity gates all pass,
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

Tooling: `python3 verify_v2edge_clamp.py` (self-contained, no ride data; exits non-zero on any
violation); `python3 regime_compare.py` (R1d in the scoreboard + the Entry-18 endpoint block, Jensen
check, resolution×smoothing grid, and the dead-clamp assert; fitted rerun via the Entry-17 envs).

---

## 2026-07-06 — Entry 17: a regime-decomposed closed form — does splitting the ride by slope beat the champion?

**Lineage** — $I$: $(D_1..D_5, P_{a,g})$ · $T$: regime-decomposed / v2Edge · $O$: `regime_comparison.csv` (1,402) · $S$: the regime split does not beat the champion

*Prompt (Danilo): test an alternative closed form `E_new = E_flat(x₌;P₌) + E_climb(x₊;P₊) +
E_descent(x₋;P₋)` — decompose the ride by a climb/descent slope threshold and let each regime draw
the base law with its own regime power; ideally link the threshold to where β (and β·ε) dominates α.
Plus a totals variant `E_new2 = E_flat(d=x,P₌,h=0) + E_climb(d=0,P₊,h₊) + E_descent(d=0,P₋,h₋)`. Also
treat the author's full export as a full test alongside P. Paz and JAAM.*

The champion closed form (§3.2) is single-regime with patches: one flat reference speed, aero **zeroed**
on climbs (the `cf` α-split), a 2 m deadband, and a lumped descent credit ε. This entry tests whether a
structurally cleaner *segment* decomposition — each regime evaluating the base law with its **own** power
(flat `flatEqSpeed(P₌)`; climb aero at the quasi-steady `v_c(P₊)`; descent from the `P₋`+gravity
equilibrium) — is any better. Harness: `regime_compare.py` (engine block verbatim from `time_compare.py`,
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

$$E_{\mathrm{new}} = E_{\mathrm{flat}} + E_{\mathrm{climb}} + E_{\mathrm{descent}}, \qquad \mathrm{regime}(i) = \begin{cases} \text{climb} & s_i \ge \text{climbThr} \\ \text{descent} & s_i \le \text{descThr} \\ \text{flat} & \text{otherwise} \end{cases}$$

$$\begin{aligned}
E_{\mathrm{flat}} &= \sum_{\text{flat } i} \big[\, \alpha_r\,dx_i + \alpha_a(v_{=})\,dx_i + \beta\,dh_i \,\big] \quad && \text{($dh_i$ signed; no floor)} \\
E_{\mathrm{climb}} &= \sum_{\text{climb } i} \big[\, \alpha_r\,dx_i + \alpha_a(v_c(i))\,dx_i + \beta\,dh_i \,\big] \quad && \text{($dh_i > 0$)}
\end{aligned}$$

$E_{\mathrm{descent}}$ (one of three, never mixed):

$$\begin{aligned}
R1a &= \sum_{\mathrm{desc}\ i} \max\big(0,\ \alpha_r\,dx_i + \alpha_a(v_{=})\,dx_i - \varepsilon\,\beta\,|dh_i|\big) && \text{(base-law $\varepsilon$ clamp)} \\
R1b &= \sum_{\mathrm{desc}\ i} P_-\cdot \frac{dx_i\,\mathrm{sec}_i}{v_-(i)} && \text{($= P_-\,t_-$; no $\varepsilon$)} \\
R1c &= \sum_{\mathrm{desc}\ i} \max\big(0,\ C_{rr}\,mg\cos\theta_i + \tfrac{1}{2}\rho C_dA\,(v_{=}+w)|v_{=}+w| + mg\sin\theta_i\big)\cdot \frac{dx_i\,\mathrm{sec}_i}{k_{\mathrm{eff}}} && \text{(leg force-deficit at flat cruise; $\sin\theta_i < 0$; no $\varepsilon$, no $P_-$)}
\end{aligned}$$

*(B) E_new2 — the totals decomposition (Danilo).* Read the base closed form `E(d, P, h) = α(P)·d + β·h`
off three whole-ride totals, with `d=0` on the climb/descent components:

$$\begin{aligned}
E_{\mathrm{new2}} &= E_{\mathrm{flat}}(d{=}x,\, P{=}P_{=},\, h{=}0) + E_{\mathrm{climb}}(d{=}0,\, P{=}P_+,\, h{=}h_+) + E_{\mathrm{descent}}(d{=}0,\, P{=}P_-,\, h{=}{-h_-}) \\
&= \alpha(P_{=})\,x + \beta\,h_+ - \varepsilon\,\beta\,h_- \\
&= \alpha_r\,x + \alpha_a(v_{=})\,x + \beta\,h_+ - \varepsilon\,\beta\,h_- \qquad \text{(aero over the WHOLE distance $x$ — the ‘off’ mode)}
\end{aligned}$$

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

Tooling: `python3 regime_compare.py` (all five corpora; `SANITY=1` runs the synthetic gates;
`<RIDER>_M`/`_CDA`/`_CRR` envs swap in fitted physics — the causal rerun above is
`PPAZ_M=80.7 PPAZ_CDA=0.26 PPAZ_CRR=0.0053 JAAM_M=103.2 JAAM_CDA=0.323 JAAM_CRR=0.0108 DANLESSA_M=71.2 DANLESSA_CDA=0.256 DANLESSA_CRR=0.0072 node regime_compare.py`).
Writes the gitignored `regime_comparison.csv`.

---

## 2026-07-04 — Entry 16: does it hold with the *real* rider physics? + the author's full export

**Lineage** — $I$: $(D_5, P_{a,g} \cdot P_{f,p}(m))$ · $T$: F1–F4, $F_\mathrm{base}$ · $O$: `danlessa_comparison.csv` (636 rows, 621 clean) · $S$: Table 3's D5 column

*Prompt (Danilo): (a) test how the article conclusions change if we use the Entry-15 *fitted* rider
physics instead of the generic assumed constants — that's our best guess for riders 2–3; (b) then, add
the author's own full Strava export (`strava_danlessa`, 1597 power rides) and analyse it as another
rider dataset.*

Two connected robustness checks. Tooling: `PPAZ_CDA`/`PPAZ_CRR` (and `JAAM_`, `DANLESSA_`) env overrides
on the compare harnesses swap the generic assumed drag/rolling for each rider's Entry-15 fitted values;
`danlessa_inventory.py` + `danlessa_compare.py` add the author's full export (verbatim engines).

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

Tooling: `PPAZ_M=80.7 PPAZ_CDA=0.26 PPAZ_CRR=0.0053 node ppaz_compare.py` (and `JAAM_`, `DANLESSA_`);
`python3 danlessa_inventory.py && node danlessa_compare.py`; `python3 param_fit.py` (now 4 riders). All read
the gitignored exports, write gitignored CSVs.

---

## 2026-07-03 — Entry 15: independently estimating CdA, C_rr, mass and wind — what the data can and cannot give

**Lineage** — $I$: $(D_1 \cup D_3 \cup D_4, P_{f,p})$ · $T$: physics inversion + wind · $O$: `cda_estimate.csv` (3), `param_fit.csv` (4) · $S$: Table 4's fitted constants

*Prompt (Danilo): can we independently estimate CdA for P. Paz and JAAM? Then, over several
iterations: uphill segments are braking-free (the cleanest data); this is akin to virtual-elevation;
wind matters per activity; and finally a `/goal` — every dataset should yield per-activity CdA, C_rr,
wind and rider+bike mass within plausible ranges (author m 68–80 kg, CdA 0.28–0.45, C_rr 0.004–0.015;
P. Paz 72–90 / 0.25–0.45 / 0.004–0.015; JAAM 73–95 / 0.25–0.45 / 0.004–0.015; wind ±15/±10 km/h
single-direction, ±5 km/h circular).*

**Why this matters.** Entry 14 flagged JAAM's implied mass (101.7 kg) as implausibly high and
*guessed* it was a CdA misspecification. This entry tests that — and refutes it. Two tools:
[`cda_estimate.py`](../../src/harness/cda_estimate.py) (the exploration of what fails and why) and
[`param_fit.py`](../../src/harness/param_fit.py) (the working per-activity estimator). Engines
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
  the wind together. `param_fit.py`: mass fixed at the rider level (from climbs), then **per activity**
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
high implied mass is simply genuine mass — the rider really is ~100 kg.** Tooling: `python3 cda_estimate.py`
(the exploration) and `python3 param_fit.py` (the estimator;
~1 min; writes gitignored CSVs). This is a v1 — the two numeric open items above are the next passes.

---

## 2026-07-03 — Entry 14: a third rider (JAAM) qualifies the transfer — and a framing correction

**Lineage** — $I$: $(D_4, P_{a,g} \cdot P_{f,p}(m))$ · $T$: F1–F4, $F_\mathrm{base}$ · $O$: `jaam_comparison.csv` (219) · $S$: Table 3's D4 column

*Prompt (Danilo): a third rider's export was added at `strava_jaam`; test it. Two corrections: P. Paz
and JAAM are **not** members of Pedal Hidrográfico (independent riders who shared data with consent);
and the author's own rwgps/strava rides — the "longões" — are **not** Pedal Hidrográfico activities
either (only the "censo" set is). Earlier entries/drafts that called P. Paz "a second collective member"
or leaned on "same collective" as the external-validity caveat were wrong and are corrected here.*

**What this is.** A **third fully-independent rider** (JAAM — different person, different power meter,
not the author, not P. Paz, not in the collective), `data/activities/strava_jaam/` (gitignored,
shared with consent). `jaam_compare.py` reuses `ppaz_compare.py`'s **verbatim** engines (byte-identical,
re-verified by diff in an adversarial audit), retargeted to JAAM's manifest, plus a terrain/altitude
stratification. Numbers below are pinned to `jaam_comparison.csv` md5 `03359f5…` (219 rows); an
adversarial 3-agent review verified the harness, recomputed every figure, and set the honest framing.

**Inventory** (`jaam_inventory.py`): 1 282 FIT files, 0 errors, 2022-12 → 2026-07; **360 power rides**,
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
Tooling: `python3 jaam_inventory.py && node jaam_compare.py` (`JAAM_M=<kg>` for the mass sweep); both read
the gitignored export and write gitignored outputs.

---

## 2026-07-02 — Entry 13: the time model, finally tested — ascent half holds, descent bridge does not

**Lineage** — $I$: $(D_1 \cup D_3, P_{a,g} \cdot P_{f,p}(m))$ · $T$: time model $x^* = x + k_+h_+ - k_-h_-$ · $O$: `time_comparison.csv` (542) · $S$: gated, but out of paper 1

*Prompt (Danilo): write a plan to test the time model with the existing datasets; hand to Opus/Sonnet to execute.*

**This retires the standing "time model is theory only" caveat** (§10.4, notas). The energy↔time dual
`t = x*/v_f`, `x* = x + k₊·h₊ − k₋·h₋` (article §5, the paper's second novel claim) had never been
compared to a measured ride time. [`time_compare.py`](../../src/harness/time_compare.py) does that
across all three corpora at once (longões 43 · censo 58 · P. Paz 441 clean rides). Engines are verbatim
copies (assembled programmatically from `ppaz_compare.py` + `compare.py`'s `ptsFromGPX` +
`applet/index.html`'s `approxTime`); the new pieces are `extractRegimeStats` (per-regime
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

Tooling: `python3 time_compare.py` (reads the three gitignored track sets + manifests; writes
`time_comparison.csv`, gitignored). `PPAZ_M=<kg> node time_compare.py` for the mass sweep.

---

## 2026-07-02 — Entry 12: a second rider — the frozen ε estimator survives the transfer

**Lineage** — $I$: $(D_3, P_{a,g} \cdot P_{f,p}(m))$ · $T$: F1–F4, $F_\mathrm{base}$ · $O$: `ppaz_comparison.csv` (441) · $S$: Table 3's D3 column

*Prompt (Danilo): P. Paz shared their full Strava history export (`data/activities/strava_ppaz/`,
gitignored — third-party GPS, shared with consent). Incorporate it into the analysis.*

**This is the external-validity test §10.4 named as the deepest limitation** — until now every
number came from one rider and one power meter. P. Paz is a different rider, on a different
meter, with a different riding profile (median v_f **26.6 km/h** vs Danilo's 16.5 urban /
23.4 longões — a faster, open-road rider).

**Inventory** ([`ppaz_inventory.py`](../../src/harness/ppaz_inventory.py)): 1 054 FIT files
parsed, 0 errors, 2023-10 → 2026-07. 1 052 rides, **753 with power** (>50% coverage), 493 of
them ≥ 20 km. After the harness filters (altitude ≥ 99%, not-Zwift via FIT `file_id`
manufacturer — **45 virtual rides excluded** — and power present): **441 usable rides**, none
excluded by the physical floor (P. Paz's meter shows no censo-style dropouts).

**Implied mass, not assumed** ([`ppaz_compare.py`](../../src/harness/ppaz_compare.py) pass A).
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
  the in-sample mass calibration. (`PPAZ_M=<kg> node ppaz_compare.py`.)
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

Tooling: `python3 ppaz_inventory.py && node ppaz_compare.py` (reads the gitignored export;
writes `strava_ppaz_manifest.json` + `ppaz_comparison.csv`, both gitignored).

---

## 2026-07 — Entry 11: general review — code fixes, and what they moved

**Lineage** — $I$: — · $T$: — · $O$: no new $O$; every $O$ above regenerated · $S$: ≤ 0.3 pp shifts across the board

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
  timestamp-offset header is now decoded (as `harness/verify.py` already did), in the app
  and all four `.mjs` copies.
- **`flatEqSpeed` used unsigned drag** while both engines use signed `rel·|rel|` — broke the
  flat-match anchor under a strong tailwind (not triggered by any current ride). Fixed with a
  monotone-safe bisection.
- **`loadFIT` in the app couldn't load 3 of the 44 rides** (interleaved dist/alt records) — the
  harnesses already had the index-interpolation fix; ported it to the app.
- Smaller robustness fixes (harnesses only, no number changes): `Buffer` pool hazard on small FIT
  reads, `parseFIT` throwing consistently instead of silently truncating on 3 of 4 copies, a
  final-point profile-dedup edge case that could create `dx≈0`, non-monotone device-distance
  clipping, and a machine-checked per-ride conservation-identity assert (`compare.py` now prints
  the worst residual — **1.77e-8**, comfortably under the 1e-6 bar).

**Methodological honesty corrections (documentation, no code change):**

- **The ε correlations (0.83/0.87) are part–whole, not independent validation.** `ε_bal` (the
  "truth") and `ε_coast` (the predictor) share their dominant geometry term *and* the same per-ride
  `α`; at `s̄ ≥ 3%` the shared term `α/(β·s̄)` *alone* correlates **0.72** with `ε_bal` (re-measured;
  it correlates 0.99 with `ε_coast` — they are nearly the same quantity). The honest statistic is
  the **RMS error reduction vs. a flat-constant baseline**: at `s̄ ≥ 3%`, `ε_coast − 0.13` reaches
  RMS 0.08 against a flat-median baseline of RMS 0.13 — a genuine **37% RMS reduction**, which is
  the number to lead with, not the correlation. (New `eps_hypothesis.py` output section
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
`compare.py` for the exact current values rather than trusting the historical prose figures.

---

## 2026-06-29 — Entry 10: is São Paulo's ε a braking-driven quantity? (no — it's a constant)

**Lineage** — $I$: $(D_2, P_{a,g})$ · $T$: $\varepsilon$ from the descent balance · $O$: `eps_sp.csv` (59) · $S$: $\varepsilon_f$ = 0.20

*Prompt (Danilo): hypothesise how to estimate ε for São Paulo. Hypothesis tested: urban
stop-go suppresses descent recovery below the free-coasting closed form, so*
`ε_SP = clamp(ε_coast − Δε_brake)`, *with* `Δε_brake = (1/(g·H₋))·Σ_descent ½·Δ(v²)` *at forced
decelerations — readable from the speed trace (post-hoc) or a route's signal/stop/corner density
(planning).*

Tested on **59 clean censo rides** (power → true descent-balance ε via `epsFromFIT`; speed →
braking density), α at the *measured* flat speed, assumed rider. Tool:
[harness/eps_sp_test.py](../../src/harness/eps_sp_test.py). Medians: ε_true **0.23**,
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

**Lineage** — $I$: $(D_2, P_{a,g})$ · $T$: F1–F4, $F_\mathrm{base}$ · $O$: `censo_comparison.csv` (69 rows, 62 clean) · $S$: Table 3's D2 column

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

Tooling: [harness/fetch_censo.py](../../src/harness/fetch_censo.py) (RWGPS-preferred
downloader) → [harness/censo_compare.py](../../src/harness/censo_compare.py). Output
`results/censo_comparison.csv` (gitignored, like the tracks and the sheet).

---

## 2026-06-28 — Entry 8: a closed form for ε from route geometry

**Lineage** — $I$: $(D_1, P_{a,r})$ · $T$: $\varepsilon$ from geometry · $O$: `eps_hypothesis.csv` (44) · $S$: **$\varepsilon_0$ = 0.13**

*Prompt (Danilo): hypothesise a closed form for ε from each activity's details. Intuitions:
long descents → a non-zero floor tied to max safe speed; close/low rollers and flat terrain
→ ε→1; tight curves → lower ε; off-road → lower ε.*

**Hypothesis.** On any descent where the legs are idle (coast *or* brake — both save the
same `α·dx`), `ε(s) = (α·dx − E_legs)/(β·h₋)` collapses to a function of grade alone:

$$\varepsilon_{\mathrm{coast}}(s) = \min\!\Big(1,\ \frac{\alpha}{\beta\,s}\Big), \qquad \frac{\alpha}{\beta} = C_{rr} + \frac{\tfrac{1}{2}\rho C_dA\,(v_f + w)^2}{m g}$$

$$\varepsilon \approx \mathrm{clamp}_{[0,1]}\big(\varepsilon_{\mathrm{coast}} - c_\kappa\,\kappa - c_u\,f_{\mathrm{unpaved}}\big) \qquad (+\ \text{braking penalties})$$

drop-weighted over the descent profile (or lumped with `s̄ = H₋/X₋`). Tested against the
per-ride **descent-energy-balance ε** (`epsFromBalance`, the app's `epsFromFIT`: 30 m cells,
`ε = (α·X₋ − E_legs,₋)/(β·H₋)`, α at the *measured* flat speed) over the 44 power rides.
Tool: [harness/eps_hypothesis.py](../../src/harness/eps_hypothesis.py) (κ = curviness in
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

- **Validated estimator:** `ε ≈ clamp[0,1]( ε_coast − ε₀ )`, `ε₀ = 0.13`. The offset is
  near-constant (residual descent pedalling/braking the coasting ideal ignores); it turns the
  `s̄≥3%` median ε_coast 0.39 → 0.26, matching the measured 0.27. *(Named retroactively, Entry 27:
  ε₀ is the **coasting deficit** — the share of the descent pure coasting would refund that the
  rider never collects. Later entries still say "the −0.13 offset"; same quantity.)*
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
rides. Written up in [notas.md](../notes/original_notes.md) (*Closed form: predicting ε from the route*) and
wired into the app as an auto-ε option. The closed form does **not** replace the per-ride
`epsFromFIT` where a power track exists — it is for *planning* (no track, geometry only).

---

## 2026-06-28 — Entry 7: fitting k_h on sustained climbs (the clean way)

**Lineage** — $I$: $(D_1, P_{a,r})$ · $T$: sustained-climb balance · $O$: `model_comparison.csv` (44) · $S$: $k_h$

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

**Lineage** — $I$: $(D_1, \mathrm{DEM})$ · $T$: elevation substitution · $O$: `harness/dem/` products · $S$: `dem-elevation-comparison.md`; $k_\mathrm{DEM}$

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

**Lineage** — $I$: $(D_1, P_{a,r})$ · $T$: F3 (deadband $\tau$ = 2 m) · $O$: `model_comparison.csv` (44) · $S$: scoreboard champion row; $\tau$ = 2 m

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
`compare.py` (`TAU_SMOOTH = 2`).

---

## 2026-06-28 — Entry 4: the `P_flat/P_avg` term and the `v_f` lever

**Lineage** — $I$: $(D_1, P_{a,r})$ · $T$: F2, $v_f$ variants · $O$: `model_comparison.csv` (44) · $S$: scoreboard $v_f$ rows

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
before recommending a `v_f` policy for the app/`research/notes/original_notes.md`.

---

## 2026-06-28 — Entry 3: climb-fraction correction in α

**Lineage** — $I$: $(D_1, P_{a,r})$ · $T$: F2 (climb-fraction $\alpha$) · $O$: `model_comparison.csv` (44) · $S$: scoreboard `cf` rows

*Prompt: how does the approximate behave if the climb-fraction correction is folded
into α?*

`notas.md` already specifies it ("Correcting the climb aero over-charge"): split
`α = α_r + α_a`, keep rolling `α_r` over all of x, and apply the aero part `α_a`
only over the **non-climbing fraction** `f_flat = 1 − x₊/x`:

$$E \approx \alpha_r\,x + \alpha_a\,x\,f_{\mathrm{flat}} + \beta\,(h_+ - \varepsilon\,h_-)$$

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

**Lineage** — $I$: $(D_1, P_{a,r})$ · $T$: F1–F4, $F_\mathrm{base}$ · $O$: `model_comparison.csv` (44) · $S$: scoreboard baseline row

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

**Lineage** — $I$: $(D_1, P_{a,r})$ · $T$: F1–F4, $F_\mathrm{base}$ · $O$: `model_comparison.csv` (44) · $S$: the running scoreboard

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
`buildProfile` are copied verbatim from `applet/index.html`. The
conservation identity `k_eff·legE = ΔKE + W_rr + W_aero + W_grav + W_brake` holds to
1e-6 relative error on spot-checked rides — confirming the canonical port.

### Reproduce

```sh
# from the repo root
python3 harness/build_model_inputs.py     # per-ride parameters from the sheet -> model_inputs.json
python3 harness/compare.py                  # canonical + approximate variants; writes model_comparison.csv
```
