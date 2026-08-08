<!-- Claim annotations for this article live in paper2-dem-deployment.meta.ttl, keyed to the
     invisible @c-<id> anchors in the text below. See that file for the rationale. -->

<!--
  paper2-dem-deployment.md — DRAFT. Second paper of the series; format target:
  LETTER / application note (~4 pages), not a full article.

  Sources of truth: research/journal/MODEL_COMPARISON_JOURNAL.md Entry 41 (the
  registered experiment and its numbers), src/harness/e41_dem_route.py (the
  instrument), src/harness/bootstrap_ci.py (the gate battery). Every number
  below is gated. Style inherits paper 1: models named F1–F4, display equations
  tagged (L1)…, ≤200-word paragraphs, ≤5 paragraphs per header, accuracy AND
  signed bias with 95% CIs everywhere.

  Position in the series:
  - Consumes paper 1 (paper1-closed-form.md) only: the law (F3/F4), the frozen
    behavioural constants, the (α, ε) bundle rule. No search machinery — this is
    ROUTE-grain, which is why it is paper 2: it ships before the routing paper.
  - Paper 3 (paper3-edge-cost.md, edge-grain routing) CITES this letter's scale
    prescription instead of re-deriving it.
  - Paper 1 deliberately excludes DEMs from its evaluation (§2.3.3) — that
    exclusion is what this letter exists to complement.
-->

# A Recipe for Estimating Bicycling Route Energy at Planning Time, with Corrections for the Elevation Source

**Danilo Lessa Bernardineli** — Dynamical Systems Group; Pedal Hidrográfico, São Paulo

## Abstract

**Problem.** A companion paper validates a closed form for the mechanical energy of cycling a route against 1,285 power-metered rides — on each ride's own barometric elevation. A planner has no barometer: it has a polyline and a digital elevation model. We measure what that substitution costs, and prescribe the repairs.

**Method.** We re-evaluate 1,164 rides from the companion paper's three São Paulo calibration corpora — travel rides kept, so the author's corpus extends beyond the survey's footprint — plus 670 rides from four European riders against the global product alone, changing one thing: elevation comes from a DEM sampled along the recorded track. Measured power, per-ride physics and every behavioural constant are held, so each ride is its own control. Seven arms cross two sources — a local 5 m survey and the global 30 m FABDEM — with the knobs a planner controls: the polyline sampling step, and pre-smoothing of the profile.

**Results.** The local survey costs a third of a point of median error (3.8% → 4.1%)<!--@c-a2.swap.cost--> and swings the bias from −1.

9% to +0.3%; smoothing the sampled profile at σ = 30 m restores the control's bias to a tenth of a point (4.0%, −1.8%)<!--@c-a2.smoothing.prescription-->

. FABDEM costs three to four times as much. The ascent-noise rate is a property of the chain, not a constant — 3.01<!--@c-a2.noise.rate--> m/km

 [2.93, 3.10] for the barometer against 10.15 [9.84, 10.60] for oversampled FABDEM, and 1.26 [1.19, 1.32] for the European corpus's cleaner recording chains — and carrying the wrong one leaves the totals-only form biased +19%. The penalty is terrain-dependent, measured here within a single rider and device: on the author's rides outside the survey — travel rides on rougher terrain — FABDEM's bias more than doubles relative to the same rider's covered rides. On the European corpus FABDEM at its native step costs 4.1% at +3.2% bias against a 3.4% barometric control: the prescription transfers.

**Conclusion.** Planning-time DEM energy needs one table: pick the source, smooth the profile, use that chain's own noise rate.

**Keywords:** digital elevation models, elevation gain estimation, route planning, cycling energetics, active transportation, FABDEM, terrain sampling scale, open science

<a id="1"></a>


## 1. The gap between a validated law and a usable one

<a id="1.1"></a>

### 1.1 What is missing at planning time

A companion paper validates a closed form for the mechanical energy of cycling a route against the power-meter energy of 1,285 rides [paper 1]. In the form a planner would use it — paper 1's F3, air resistance charged only off the climbs, elevation totals deadband-filtered — it is eq. (L1),

$$E \;\approx\; \underbrace{\alpha_r\,x}_{\text{rolling}} \;+\; \underbrace{\alpha_a\,x_{\mathrm{flat}}}_{\text{air}} \;+\; \underbrace{\beta\,\big(\tilde h_+ - \varepsilon\,\tilde h_-\big)}_{\text{climb, less the refund}}, \tag{L1}
$$

with the rates and the recovery factor $\varepsilon$ as paper 1 defines them, and $\tilde h_\pm$ the totals after a $\tau = 2$ m deadband. All 1,285 evaluations read the elevation the ride *recorded*, from a handlebar barometer; that paper excludes digital elevation models (DEMs) by design (§2.3.3), so its accuracy figures isolate modelling error.

Nobody plans a route with a barometer. A planner — a person with a map, a routing website, or a spreadsheet — has a polyline and a DEM. That is the commonest real use of the law, the one paper 1 does not cover, and our own: *Pedal Hidrográfico* judges whether a proposed tour suits its participants with this law in a spreadsheet (paper 1 §4.1), and *quilojaules* implements it over FABDEM and OSRM. The failure mode to beat is ascent inflation. Cumulative ascent has no scale-free true value [Rapaport 2011; swisstopo] — finer sampling finds more climbing, without converging — so $\tau$ and the noise rate $c \approx 3$ m/km, both measured on barometric recordings, have no reason to be the right filter for a DEM, and $\varepsilon_0 = 0.13$ was itself calibrated at a 30 m sampling scale (paper 1 §4.4.2).

<a id="1.2"></a>

### 1.2 What is already known

The per-point vertical accuracy of modern DEMs is excellent and beside the point: FABDEM, the best free global product, reports a mean absolute error of 1.12 m in built-up terrain [Hawker et al. 2022] and 1.43 m against independent benchmarks [Bielski et al. 2024]. The barometric chain is no more absolute — consumer units agree with each other on cumulative ascent only to 1.5–3% [Menaspà et al. 2014] — but it is the chain paper 1's constants were measured on, which is what makes it this letter's reference rather than its ground truth. Per-point accuracy does not transfer to *accumulated* ascent — metre-scale noise, summed signed over thousands of samples, inflates $h_+$ by tens of percent. The one study to measure this directly finds ascent error growing monotonically with grid coarsening, from ≈ 0 at 0.4 m to +48 pp at 51 m against a LiDAR benchmark, with a raw 4 m DEM performing *worse* than the consumer watch it was meant to correct [Sánchez et al. 2024].

Our own lab journal has measured the pieces. Along the same tracks, a bare-earth 30 m DEM and the local 5 m survey disagree on ascent by ~6% on hilly terrain but +57% pooled, and +101 to +135% on the flattest corpora, where per-pixel noise reads as rollers [E6, E19]. Pre-smoothing the raster restores coarser-scale behaviour [E20]; the behavioural constants prove to be functions of sampling scale *and* terrain-roughness regime [E21]; and DEMs charge for bridges and tunnels the rider never climbed [E26]. None of that answers the planner's question: those entries score a per-edge routing cost rather than the ride-level law, use one validated raster crop, and never put the law's accuracy on DEM elevation beside its accuracy on the ride's own stream. This letter measures that difference and turns it into a recipe.

<a id="2"></a>

## 2. What the elevation-source swap costs

<a id="2.1"></a>

### 2.1 One substitution, seven elevation sources

We re-evaluate paper 1's corpora with one thing changed: elevation comes from a DEM sampled along the ride's own recorded track instead of from its barometer. Measured power, regime powers, the physical constants, $\tau$, $c$ and $\varepsilon_0$ are held, so each ride supplies its own control and the paired difference between an arm and that control is the elevation source alone.

Every arm lives on the same 5 m arc-length grid; an arm sampling at a coarser polyline step is linearly interpolated back onto it, which introduces no local extrema, so $h_\pm$, the deadband and $\varepsilon_{\mathrm{coast}}$ read the coarse geometry while the scoring grid stays fixed. The seven arms cross two sources — the local 5 m aerophotogrammetric survey (IGC-SP 2010) and the free global FABDEM V1-2 at 30 m — with the two knobs a planner controls: the polyline sampling step (5 or 30 m) and an optional pre-smoothing of the *profile*, a mask-normalized Gaussian of width $\sigma$ along the route,

$$h^{\sigma}_i \;=\; \frac{\sum_{|j| \le 3\sigma/\Delta} w_j\,h_{i+j}}{\sum_{|j| \le 3\sigma/\Delta} w_j}, \qquad w_j = \exp\!\big(-\tfrac{1}{2}(j\Delta/\sigma)^2\big), \tag{L2}
$$

the sums running only over samples that exist, so the filter behaves at the route's ends. Smoothing the profile rather than the raster is what a planner can do — it holds a polyline, not a 20 GB GeoTIFF — and the substitution is validated rather than assumed: against the raster-space smoothing of [E20] the two agree on $h_+$ to −1.1% median (p90 6.9%).

The prescription turns on each source's own ascent-noise rate — paper 1's $c$, measured per source rather than assumed,

$$c_{\mathrm{source}} \;=\; \frac{h_+ - \tilde h_+}{x}, \tag{L3}
$$

the metres of phantom climb per route-kilometre the deadband removes. Whether paper 1's frozen $c \approx 3$ m/km survives a change of elevation source is the letter's third question. The recovery term is recomputed on each substituted profile: it is geometry-dependent by construction (paper 1 eqs. (4)–(5)), so freezing it would hide half of what the source does.

<a id="2.2"></a>

### 2.2 Physics protocol, populations and quality gates

Accuracy is quoted at **regime-consistent per-ride physics** — each ride's mass, rolling coefficient and drag area inverted from its own flat-regime balance (paper 1 §3.5.2, Table 6) — not at the frozen literature priors. At the priors each corpus carries a standing bias of several points, and swapping the elevation source partly cancels or amplifies it, so median $|\Delta\%|$ would read the bias rather than the source. This is not hypothetical: at the priors the global 30 m DEM appears *more* accurate than the ride's own barometer, purely because its over-charge offsets an under-prediction. Paper 1 §4.3.4's bundle rule makes the same point from theory — only the (cost, refund) pair is identified — and at this $\alpha$ the honest pairing is $\varepsilon_d$ everywhere. The frozen-prior results are reported alongside as a protocol contrast. The per-ride constants are inverted once, from the recorded stream, then held fixed across arms; re-inverting per arm would let mass and drag absorb the elevation error.

Populations are paper 1's own calibration corpora (D3–D5; D1/D2 are excluded as re-processings of D5's author, that paper's registration) plus the European D6 as the out-of-region column, intersected with three pre-registered quality gates, applied identically to every arm so no source is advantaged by its own defects. Travel rides outside the local survey's footprint are **kept**, with the survey arms absent rather than the rides dropped — the within-rider terrain split of [§2.3](#2.3) exists because of this choice. **G1, track quality:** at most 0.5% of route length inside GPS-fix gaps over 50 m. Where a recording lost GPS the track is a straight chord and the DEM charges terrain never crossed — and this, not raster error, produces the largest artifacts we find (single-step jumps of 300–640 m, all at fix gaps of 220 m to 17 km); a planner's polyline has none. **G2, raster validity:** ≥ 99% of samples in 0.5–3000 m. **G3, anomaly census:** a one-step $|\Delta h|$ over 10 m across a 5 m step is a 200% grade — a block seam, a void edge, or a patch where the bare-earth model kept a structure. We report the full population and the anomaly-free subset side by side: what a planner gets if it does not inspect its crop, and what it gets if it does.

<a id="2.3"></a>

### 2.3 What the swap costs

On 1,164 rides across the companion paper's three calibration corpora (D3 434, D4 201, D5 529 — the author's corpus now including its 84 rides outside the survey footprint), replacing the barometer with the **local 5 m survey costs the law a third of a point of median accuracy** — 3.8% → 4.1% — and swings its bias from −1.9% to +0.3% ([Table 1](#tab1)). Smoothing the sampled profile with σ = 30 m removes the swing entirely: 4.0% median error at −1.8% bias, the control's own bias reproduced to a tenth of a point, with nothing re-fitted. The **free global 30 m product costs three to four times as much**: 5.1% and +4.3% bias when its polyline is sampled at 5 m steps, 4.5% and +2.2% at 30 m steps. And on the 670 European rides — where only the global product exists — the same recipe lands at 4.1% (+3.2%) at FABDEM's native step against a 3.4% (+0.3%) barometric control: **the prescription transfers to a landscape and instrument fleet that contributed nothing to it**.

<a id="tab1"></a>

**Table 1.** The elevation-source substitution, F3 with the dynamic $\varepsilon_d$, at regime-consistent per-ride physics — inverted once from each recording, held fixed across arms. Cells: median $\lvert\Delta\%\rvert$ [95% CI] · median signed $\Delta\%$ [95% CI]. The population is the companion paper's own (D3–D5; its D1/D2 are re-processings of D5's author and are excluded — that paper's registration, applied here), with travel rides **kept**: IGC arms exist only where the survey does, so their cells cover the 1,035-ride covered subset while `own` and FABDEM cover all 1,164. **D6 — four European riders, 670 rides — faces only its barometer and the global product**, and is the out-of-region transfer column. Best DEM arm per column in bold.

| elevation arm | D3+D4+D5 · 1,164 | D6 · 670 |
|---|--:|--:|
| `own` — recorded barometer (control) | 3.8 [3.6, 4.1] · −1.9 [−2.3, −1.4] | 3.4 [3.1, 3.6] · +0.3 [−0.2, +0.7] |
| local 5 m survey @ 5 m | 4.1 [3.9, 4.4] · +0.3 [−0.2, +1.1] | — |
| local 5 m survey @ 5 m, σ = 10 m | 4.0 [3.8, 4.3] · −0.4 [−0.9, −0.0] | — |
| **local 5 m survey @ 5 m, σ = 30 m** | **4.0 [3.8, 4.2] · −1.8 [−2.1, −1.5]** | — |
| local 5 m survey @ 30 m | 4.0 [3.8, 4.2] · −0.3 [−0.9, +0.2] | — |
| FABDEM 30 m @ 5 m | 5.1 [4.5, 6.0] · +4.3 [+3.6, +4.8] | 5.5 [5.1, 5.9] · +5.3 [+4.7, +5.8] |
| **FABDEM 30 m @ 30 m** | 4.5 [4.0, 4.9] · +2.2 [+1.7, +2.8] | **4.1 [3.9, 4.5] · +3.2 [+2.6, +3.7]** |

The over-charge is real but modest, and **strongly terrain-dependent — measured here within a single rider and device**. Paired per ride, the raw local survey over-charges on 860 of 1,035 covered rides by a median +2.2 pp. The sharper contrast no longer needs a second corpus: on the author's 445 covered rides FABDEM at 5 m steps carries +5.1 pp of paired over-charge; on the same author's 84 rides *outside* the survey — travel rides on rougher terrain — the same product's over-charge grows to +7.2 pp and its median error to 7.7% [5.0, 12.1], while the rider's own barometer holds at 4.7%. Same person, same instrument: the difference is the terrain under the raster. Planning a mountain route from a coarse DEM is a different proposition from planning an urban loop.

Two further results carry the prescription. **The noise rate is a property of the source, not a constant**: the deadband removes 3.01 m/km [2.93, 3.10] from the barometer's profile — independently reproducing paper 1's 3.1 m/km on a disjoint protocol — against 4.90 [4.83, 4.95] for the local survey and **10.15 [9.84, 10.60] for FABDEM oversampled at 5 m**, whose ascent total is 2.42× the barometer's. The European corpus doubles the point from the other side: its recording chains remove only **1.26 m/km [1.19, 1.32]** — devices and terrain both cleaner — while its FABDEM rates (5.61 at 30 m, 7.87 at 5 m) stay FABDEM-sized; neither number could be guessed from the São Paulo ones, which is the prescription. Each source's own rate rescues the totals-only form F4 on the noisiest chain; it does not make F4 equal to F3, and on low-noise chains it over-corrects, because F4 scales climb and refund by one factor while the deadband treats them separately. And **defects are a separable tail**: on the 745 crops free of elevation anomalies FABDEM's error falls 5.3% → 3.4%, and the top decile of bridge/tunnel exposure carries +5.4 pp of DEM-minus-control residual against +1.5 pp for the rest. (These and the bridge/tunnel results below are quoted on the original five-corpus walk, where they were measured and gated; their re-base to this table's population is registered follow-up work — the effects are properties of the rasters and structures, not of the corpus mix.)

Bridges and tunnels deserve their own treatment, and measuring it exposes a trap. Replacing the DEM's heights across a mapped span with a straight deck [E26] is a real repair on a raw profile: on the 943 rides carrying a matched span it removes +13.3 m [+10.0, +19.7] of the ascent the fine survey invents inside those spans, and moves the arm from 3.92% (−0.29% bias) onto the control's 3.72% (−2.10%) — reaching 3.73% (−1.29%). But the deck **over-corrects**, because a road bridge carries a vertical curve the rider genuinely climbs and a straight line erases it: measured against the ride's own barometer inside the spans, the deck under-charges by −2.79 m [−3.52, −2.08], and the shortfall is eight times larger on bridges (−2.43 m [−3.26, −1.68]) than on tunnels (−0.29 m [−0.40, −0.20]), whose roadway really is close to a chord beneath the DTM's ridge.

The trap is that **the two repairs do not stack**: after σ = 30 m smoothing the profile's in-span ascent already matches the barometer (+0.05 m [−0.29, +0.28]) — the valley a bridge spans is exactly the sub-30 m feature the Gaussian flattens — so applying the deck as well subtracts twice and makes the result significantly worse (400 of 935 rides closer, $p < 10^{-4}$).

<a id="3"></a>

## 3. The planner's recipe

[Table 2](#tab2) is the deliverable: pick your row, take its $\sigma$ and its $c$, and expect its band. Every row uses paper 1's law and the behavioural bundle the deployed router carries, unchanged — $\tau = 2$ m, $\varepsilon_0 = 0.13$, the 2% climb gate. (Paper 1's re-baselined selection chain now *fits* the deadband and lands at 6 m on the recording chain; these rows were measured under the 2 m bundle and stay with it. The two are reconciled by the rule this section already states — behavioural constants travel with their sampling chain — and priced by the basin being flat at route grain; the lab journal's Entries 67–70 add the sharper reason: the fitted refinement beyond a *measured* noise floor is corpus-absorbing rather than transferable, which argues for exactly what this letter ships — per-source measured scales — and against inheriting anyone's fitted τ.) Only $\sigma$ and $c$ move, and both are properties of the elevation chain rather than of the rider or the route. The row to prefer is the one that reproduces the *control*, not the one nearest zero bias. The σ = 10 m row reads −0.1% and looks unbiased; the σ = 30 m row reads −1.7%, matching the barometer. But −1.7% is what the law and the per-ride physics leave on the barometric chain itself, so an elevation chain that reproduces it has added nothing, while one reading −0.1% has added +1.6 pp of over-charge that happens to cancel the protocol's own residual. Selecting on that cancellation is exactly the bias-trade artifact [§2.2](#2.2) exists to avoid, and it would not survive a change of physics protocol or corpus.

<a id="tab2"></a>

**Table 2.** The prescription. The last two columns describe **disjoint workflows**: with the profile in hand you apply $\sigma$ and F3's deadband and never need $c$; with only totals you use F4 with that chain's $c$ and cannot smooth. The accuracy band is F3 with $\varepsilon_d$ over the 1,164 calibration-population rides (median $\lvert\Delta\%\rvert$ · signed bias, 95% CIs in [Table 1](#tab1)); $c$ is the chain's measured ascent-noise rate, eq. (L3). Rows are ordered by accuracy. **The bands do not transfer to terrain unlike the calibration mix** — [Table 1](#tab1)'s within-rider travel split shows FABDEM's error rising from 5.7% to 7.7% on the same rider's rougher out-of-survey rides — but they do transfer across *regions and fleets* on comparable terrain: the European corpus's FABDEM-at-30 m band (4.1% · +3.2%) brackets the São Paulo one.

| elevation chain | sample the polyline at | with a profile: pre-smooth $\sigma$ | totals only: use $c$ = | expect |
|---|---|---|---|---|
| ride's own barometer *(reference)* | 5 m | — | 3.0 m/km | 3.8% · −1.9% |
| local 5 m survey | 5 m | **30 m** | 2.6 m/km | **4.0% · −1.8%** |
| local 5 m survey | 5 m | 10 m | 3.7 m/km | 4.0% · −0.4% |
| local 5 m survey | 30 m | — | 3.7 m/km | 4.0% · −0.3% |
| local 5 m survey | 5 m | — | 4.9 m/km | 4.1% · +0.3% |
| FABDEM 30 m | 30 m | — | 7.4 m/km | 4.5% · +2.2% |
| FABDEM 30 m | 5 m | — | 10.2 m/km | 5.1% · +4.3% |
| *(D6)* ride's own barometer | 5 m | — | 1.3 m/km | 3.4% · +0.3% |
| *(D6)* FABDEM 30 m | 30 m | — | 5.6 m/km | 4.1% · +3.2% |

Five rules follow. **One — smooth the profile, not the raster.** A $\sigma = 30$ m Gaussian along the sampled polyline, eq. (L2), buys back the barometer's behaviour on the local survey and needs no raster preprocessing: thirty lines over an array the planner already holds, reproducing raster-space smoothing at the same $\sigma$ to −1.1% of $h_+$. **Two — never move the elevation chain without moving $c$ with it.** Paper 1's $c \approx 3$ m/km measures consumer barometric recordings at 5 m resampling; carrying it onto FABDEM leaves F4 biased +19%. This is the scale half of paper 1 §4.3.4's bundle rule: the behavioural constants travel with their physics *and* their sampling chain.

**Three — do not oversample a coarse DEM.** Sampling FABDEM every 5 m instead of every 30 m more than doubles the ascent total and costs 0.7 pp of accuracy and 2.3 pp of bias, because bilinear interpolation along a diagonal path manufactures sub-cell relief. **Four — inspect the crop.** Screen the sampled profile for one-step rises beyond ~10 m over 5 m: those are seams, void edges, or retained structures, not terrain. On crops that pass, the global product's error falls from 5.3% to 3.4% — *better than the barometer itself*, because the screen removes precisely the rides a 30 m product misreads.

**Five — correct bridges and tunnels, or smooth, but not both.** On a *raw* profile, replacing the heights across a mapped span with a straight deck is worth having: it removes most of the ascent the DEM invents over a spanned valley and puts the fine survey back on the barometer. It slightly over-corrects, by erasing the bridge's own vertical curve — about 2.4 m of real crown per touched ride — so treat it as a repair with a known-sign residual rather than an exact one. And skip it entirely if you pre-smooth: at σ = 30 m the portal artifact is already gone, and correcting again does measurable harm.

Two things are unchanged. A planner sampling a DEM holds the whole profile, so it can use the drop-weighted $\varepsilon_d$ of paper 1 eq. (5) — the software-only estimator that paper's hand recipe cannot reach [E42]. And with a profile in hand, use F3's deadband; F4 with a per-source $c$ is a rescue for totals-only inputs, not a substitute.

One refinement is registered rather than recommended. The deadband's work has since been decomposed (lab journal, Entries 63–69): most of it is a kinetic-energy valley toll computable from the profile's own descent→climb valleys — $\min(D, H, h_{KE})$ with the buffer built from the rider's flat and terminal speeds — and a variant with the noise floor *measured* per chain and that toll on top matched the fitted deadband's accuracy while transferring across riders better. A planner holds everything this needs: the profile's valleys, the rider's $v_f$, and — from this letter — the chain's measured noise scale. It is a candidate upgrade to the recipe, not part of its validated bands, and it belongs to the edge-cost companion where the mechanism is native.

<a id="4"></a>

## 4. Worked example: *Contornar Anhangabaú*

One of Pedal Hidrográfico's census rides, downtown São Paulo, 36.0 km with 440 m of recorded ascent; the rider's measured pedalling energy was 643 kJ. Evaluated on its own barometric stream the law lands at −1.6%. Sampled from the local 5 m survey the same route reports 602 m of ascent — 37% more — and the estimate rises to +8.7%. Smoothing that profile with $\sigma = 30$ m brings the ascent back to 449 m, the noise rate from 6.2 to 3.5 m/km, the recovery factor from 0.35 back to 0.45, and the estimate to **0.0%**.

FABDEM oversampled at 5 m gives 689 m and +8.7%; at 30 m steps, 575 m and +4.5%. The totals-only form tells the same story more sharply: at the frozen $c = 3$ m/km it errs by +13.9% on the survey and +19.8% on FABDEM, and it is each chain's own $c$ — 6.2 and 9.3 m/km for this route — that brings those back into range. A planner following the second row of [Table 2](#tab2) would have quoted 643 kJ for a ride that cost 643 kJ — a closer landing than the recipe promises, since the typical ride on that row sits within about four percent.

<a id="5"></a>

## 5. Limitations

**The planner's polyline is not the ridden line.** Every arm samples elevation along a *recorded* GPS track, so the letter isolates the elevation source with route geometry held fixed. A real planner starts from a router's polyline, which differs from the line eventually ridden; that detour factor is measured separately [E26] and compounds with everything here.

**No measured power at planning time.** Both engines read each ride's own power stream, as paper 1's do, so these figures measure the consistency of the energy accounting under an elevation-source change — not blind prediction, which additionally needs a model of the rider's power (paper 1 §4.4.5).

**DEM vintage and surface.** The local survey dates from 2010 and the global product from a 2011–2015 radar epoch; roadworks and new viaducts are invisible to both. FABDEM's building removal is imperfect in dense urban canyons, and the wide local survey is not homogeneous — which is why the quality screen is part of the recipe rather than an afterthought.

**Scope.** Two regions, two rasters, seven riders — the European column facing the global product only — and a penalty that the within-rider travel split shows is a property of the terrain under the raster. The σ and $c$ values here are per-source measurements, not universals; what transfers is the *method* — measure your own chain's noise rate on a handful of tracks. That prescription is now backed by direct evidence, not just prudence: the journal's Entries 67–70 show that smoothing-scale refinements *fitted* to a corpus are absorbing — non-stationary within riders and non-transferable across them — while measured per-chain scales carry over, which is precisely the division of labour this table implements. Rides outside the raster footprint are excluded and disclosed in the funnel rather than repaired.

## Data and code availability

The instrument is `src/harness/e41_dem_route.py`; it writes one per-ride CSV, and every published number in this letter is re-derived from that CSV by the project's gate battery (`src/harness/bootstrap_ci.py`), which exits non-zero on any mismatch. All analysis code is public at `github.com/danlessa/bicycling-energy-model` (stdlib-only Python, no build step). Per-ride GPS tracks and the independent riders' exports are private by design. The local 5 m survey (IGC-SP 2010) is a third-party product not redistributed here; the FABDEM tiles are public. The full protocol, its registered predictions and its deviations are lab-journal Entry 41.

## AI-assistance declaration

The analysis harness, the lab journal's bookkeeping, and drafts of this text were produced with substantial LLM assistance (Anthropic Claude) under continuous author direction and review; all data collection, modelling decisions and final claims are the author's.

## References

- **[paper 1]** Lessa Bernardineli, D. *A Closed-Form Model for the Mechanical Energy of Cycling a Route, Tested on 1,285 Power-Meter Rides.* Companion paper.
- **[Bielski et al. 2024]** Bielski, C. et al. (2024). *Vertical accuracy assessment of freely available global DEMs in flood-prone environments.* Int. J. Digital Earth 17(1).
- **[Hawker et al. 2022]** Hawker, L. et al. (2022). *A 30 m global map of elevation with forests and buildings removed.* Environ. Res. Lett. 17:024016.
- **[Menaspà et al. 2014]** Menaspà, P. et al. (2014). *Consistency of Commercial Devices for Measuring Elevation Gain.* Int. J. Sports Physiol. Perform. 9(5):884–886.
- **[Rapaport 2011]** Rapaport, D. C. (2011). *Evaluating cumulative ascent: Mountain biking meets Mandelbrot.* Int. J. Mod. Phys. C 22(3):209–217.
- **[Sánchez et al. 2024]** Sánchez, R. et al. (2024). *Assessing the impact of DEM resolution on elevation gain estimations in trail running.* ICECET 2024.
- **[swisstopo]** Swiss Federal Office of Topography. *Elevation profile — the coastline paradox's trap.* geo.admin.ch.
