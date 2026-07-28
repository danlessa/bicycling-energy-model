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

«TODO after §2»

**Keywords:** digital elevation models, elevation gain estimation, route planning, cycling energetics, active transportation, FABDEM, terrain sampling scale, open science

<a id="1"></a>

## 1. The gap between a validated law and a usable one

<a id="1.1"></a>

### 1.1 What is missing at planning time

A companion paper validates a closed form for the mechanical energy of cycling a route against the power-meter energy of 1,285 rides [paper 1]. In the form a planner would use it — paper 1's F3, with air resistance charged only off the climbs and the elevation totals deadband-filtered — it reads

$$E \;\approx\; \underbrace{\alpha_r\,x}_{\text{rolling}} \;+\; \underbrace{\alpha_a\,x_{\mathrm{flat}}}_{\text{air}} \;+\; \underbrace{\beta\,\big(\tilde h_+ - \varepsilon\,\tilde h_-\big)}_{\text{climb, less the refund}}, \tag{L1}
$$

with the rates $\alpha_r$, $\alpha_a$, $\beta$ and the recovery factor $\varepsilon$ as paper 1 defines them, and $\tilde h_\pm$ the elevation totals after a $\tau = 2$ m deadband. Every one of those 1,285 evaluations reads the elevation profile the ride *recorded*, from a barometric altimeter on the handlebars; that paper excludes digital elevation models (DEMs) by design (§2.3.3), so that its accuracy figures isolate modelling error.

Nobody plans a route with a barometer. A planner — a person with a map, a routing website, or a spreadsheet — has a polyline and a DEM. That is the commonest real use of the law and the one paper 1 does not cover, and it is also our own: *Pedal Hidrográfico* judges whether a proposed tour suits its participants using this law in a spreadsheet (paper 1 §4.1), and *quilojaules* implements it over FABDEM elevation and OSRM routing. The failure mode to beat is ascent inflation. Cumulative ascent has no scale-free true value [Rapaport 2011; swisstopo] — finer sampling finds more climbing, without converging — so the deadband $\tau = 2$ m and the noise rate $c \approx 3$ m/km that paper 1 measured on barometric recordings have no reason to be the right filter for a DEM, and the recovery constant $\varepsilon_0 = 0.13$ was itself calibrated at a 30 m sampling scale (paper 1 §4.4.2).

<a id="1.2"></a>

### 1.2 What is already known

The per-point vertical accuracy of modern DEMs is excellent and beside the point. FABDEM, the best of the free global products, reports a mean absolute error of 1.12 m in built-up terrain [Hawker et al. 2022] and 1.43 m against independent benchmarks [Bielski et al. 2024]. But per-point accuracy does not transfer to *accumulated* ascent: metre-scale noise, summed signed over thousands of samples, inflates $h_+$ by tens of percent. The one study to measure this directly finds ascent error growing monotonically with grid coarsening — from ≈ 0 at 0.4 m to +48 pp at 51 m against a LiDAR benchmark — and a raw 4 m DEM performing *worse* than the consumer watch it was meant to correct [Sánchez et al. 2024].

Our own lab journal has measured the pieces of the deployment that concerns us. Sampled along the same tracks, a bare-earth 30 m DEM and the local 5 m survey disagree on ascent by ~6% on hilly terrain but by +57% pooled — and +101 to +135% on the flattest corpora — where per-pixel noise reads as rollers [E6, E19]. A static pre-smoothing of the raster restores the coarser-scale behaviour [E20]; the behavioural constants turn out to be functions of the sampling scale *and* the terrain-roughness regime [E21]; and DEMs charge for bridges and tunnels the rider never climbed [E26]. What none of that answers is the planner's question: those entries score a per-edge routing cost rather than the ride-level law, they use one validated raster crop, and they never put the law's accuracy on DEM elevation next to its accuracy on the ride's own stream. This letter measures that difference and turns it into a recipe.

<a id="2"></a>

## 2. What the elevation-source swap costs

<a id="2.1"></a>

### 2.1 One substitution, seven elevation sources

We re-evaluate paper 1's corpora with exactly one thing changed: the elevation profile comes from a DEM sampled along the ride's own recorded track instead of from its barometer. Measured power, per-ride regime powers, the physical constants, $\tau$, $c$ and $\varepsilon_0$ are held. Each ride therefore supplies its own control, and the paired difference between an arm and that control is the elevation source and nothing else.

Every arm lives on the same 5 m arc-length grid. Where an arm samples the DEM at a coarser polyline step, its profile is linearly interpolated back onto the 5 m grid; linear interpolation introduces no local extrema, so $h_\pm$, the deadband and $\varepsilon_{\mathrm{coast}}$ all read the coarse geometry while the scoring grid stays fixed. The seven arms cross two sources — the local 5 m aerophotogrammetric survey (IGC-SP 2010) and the free global FABDEM V1-2 at 30 m — with two knobs a planner actually controls: the polyline sampling step (5 m or 30 m) and an optional pre-smoothing of the *profile*, a mask-normalized Gaussian of width $\sigma$ applied along the route,

$$h^{\sigma}_i \;=\; \frac{\sum_{|j| \le 3\sigma/\Delta} w_j\,h_{i+j}}{\sum_{|j| \le 3\sigma/\Delta} w_j}, \qquad w_j = \exp\!\big(-\tfrac{1}{2}(j\Delta/\sigma)^2\big), \tag{L2}
$$

the sums running only over samples that exist, so the filter is well behaved at the route's ends. Smoothing the profile rather than the raster is what a planner can do: it holds a polyline, not a 20 GB GeoTIFF. That substitution is validated rather than assumed — against the raster-space smoothing of [E20], on the rides that entry cached, the two agree on $h_+$ to «TODO»% median.

The quantity the prescription turns on is each source's own ascent-noise rate — paper 1's $c$, measured per source rather than assumed,

$$c_{\mathrm{source}} \;=\; \frac{h_+ - \tilde h_+}{x}, \tag{L3}
$$

the metres of phantom climb per route-kilometre that the deadband removes. Paper 1 measures $c \approx 3$ m/km on barometric recordings and freezes it; whether that constant survives a change of elevation source is the letter's third question. Finally, the recovery term is recomputed on each substituted profile: it is geometry-dependent by construction (paper 1 eqs. (4)–(5)), so freezing it would hide half of what the elevation source does.

<a id="2.2b"></a>

### 2.2 Physics protocol, populations and quality gates

Accuracy is quoted at **regime-consistent per-ride physics** — each ride's mass, rolling coefficient and drag area inverted from its own flat-regime balance (paper 1 §3.5.2, Table 6) — not at the frozen literature priors. The reason is that at the priors each corpus carries a standing bias of several points, and swapping the elevation source partly cancels or amplifies that bias, so median $|\Delta\%|$ would read the bias rather than the source. The effect is not hypothetical: at the priors the global 30 m DEM appears *more* accurate than the ride's own barometer on our data, purely because its over-charge offsets an under-prediction. Paper 1 §4.3.4's bundle rule makes the same point from theory — only the (cost, refund) pair is identified — and at this $\alpha$ the honest pairing is the dynamic $\varepsilon_d$ on every corpus. Results under the frozen priors are reported alongside as the protocol contrast.

Populations are paper 1's clean corpora intersected with three pre-registered quality gates, applied identically to every arm so that no source is advantaged by its own defects. **G1, track quality:** at most 0.5% of route length may sit inside GPS-fix gaps over 50 m. Where a recording lost GPS, the track is a straight chord and the DEM charges terrain the rider never crossed — and this, not raster error, produces the largest profile artifacts we find (single-step jumps of 300–640 m, all at fix gaps of 220 m to 17 km). A planner's polyline has no such gaps. **G2, raster validity:** at least 99% of a ride's samples must fall in 0.5–3000 m; the wide survey stores voids as extreme magnitudes. **G3, anomaly census:** a one-step $|\Delta h|$ over 10 m across a 5 m step is a 200% grade — a block seam, a void edge, or a patch where the nominal bare-earth model retained a structure. We report the full population and the anomaly-free subset side by side: the first is what a planner gets if it does not inspect its crop, the second what it gets if it does.

<a id="2.2"></a>

### 2.2 Results

«TODO»

<a id="3"></a>

## 3. The planner's recipe

«TODO»

<a id="4"></a>

## 4. Worked example: *Contornar Anhangabaú*

«TODO»

<a id="5"></a>

## 5. Limitations

**The planner's polyline is not the ridden line.** Every arm here samples elevation along a *recorded* GPS track, so the letter isolates the elevation source with the route geometry held fixed. A real planner starts from a router's polyline, which differs from the line eventually ridden; the resulting detour factor is measured separately [E26] and compounds with everything below. In the other direction, the recorded track is what makes the comparison paired and clean, and a planner's polyline carries no GPS dropouts — the defect that this letter's first quality gate exists to remove.

**No measured power at planning time.** Both engines here read each ride's own power stream, exactly as paper 1's do, so these figures measure the consistency of the energy accounting under an elevation-source change — not blind prediction. Predicting a ride before it happens additionally requires a model of the rider's power; the planner's recipe substitutes the rider's own flat cruising speed for it (paper 1 §4.1), and a pre-registered blind test remains future work (paper 1 §4.4.5).

**DEM vintage and surface.** The local survey dates from 2010 and the global product from a 2011–2015 radar epoch; roadworks, new viaducts and quarrying since then are invisible to both. FABDEM's canopy and building removal is imperfect in dense urban canyons, and the wide local survey is not homogeneous — it carries block seams and patches where the nominal bare-earth model retains structures. That is why the quality gates below are part of the recipe and not an afterthought.

**Scope.** One metropolitan region, two rasters, three riders. The σ and $c$ values prescribed here are per-source measurements, not universals; the *method* for obtaining them — measure your source's own noise rate on a handful of tracks — is what transfers. Rides outside the raster footprint are excluded, which removes part of two corpora and is disclosed in the funnel rather than repaired.

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
