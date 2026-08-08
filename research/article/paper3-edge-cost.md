<!-- Claim annotations for this article live in paper3-edge-cost.meta.ttl, keyed to the
     invisible @c-<id> anchors in the text below. See that file for the rationale. -->

<!--
  paper3-edge-cost.md — SCAFFOLD (not a draft). Third paper of the series.

  Working question: how do you discretize the ride-level closed form of paper 1
  into a per-edge cost usable inside a shortest-path search (Dijkstra and
  variants) for minimum-energy routing — and what breaks when you do?

  Status: outline + evidence inventory + registered gaps. Every section carries
  either the existing evidence (journal entry / harness) or a TODO naming the
  experiment that would fill it. Numbers here are placeholders quoted from the
  lab journal — nothing is gated for this paper yet; a paper-2 gate battery is
  itself a TODO.

  Relation to paper 1 (paper1-closed-form.md): inherits the frozen constants protocol
  (Crr 0.008, CdA 0.40, ρ 1.13, k_eff 0.98, wind 0, G 9.7864), the behavioural
  constants (ε₀ = 0.13, c ≈ 3 m/km, climb threshold 2%) and the four-form
  family. Paper 1 validates the law per ride; this paper asks whether the same
  physics survives being chopped into 30 m edges and summed by a router.
-->

# From a Ride-Level Energy Law to an Edge Cost: Discretizing the Closed Form for Minimum-Energy Bicycle Routing

**Status: scaffold.** Sections below are the intended IMRAD skeleton; `TODO`
marks work not yet done, `[E##]` cites the lab journal entry (and harness)
holding the evidence that already exists.

## Abstract (sketch)

Minimum-energy bicycle routing needs a per-edge cost, but the energy law of
the companion paper is a *ride-level* statement: its elevation treatment
(deadband smoothing) is sequential over the whole profile, its ε is a
route-aggregate, and its aero split needs a climbing share. We propose and
validate an edge realisation — grade-local recovery
ε(s) = clamp₀₁(min(1, (α/β)/s) − ε₀), aero gated off climb edges, the scalar
noise correction in place of the (non-local) deadband — that is additive,
non-negative, direction-asymmetric, and cheap enough for Dijkstra over a
metropolitan DEM grid. TODO: headline validation numbers (edge-sum vs measured
∫P·dt over the paper-1 corpora; parity/attribution claims). We document the
pitfalls: every behavioural constant is a function of the elevation-sampling
scale; the deadband cannot be pushed into an edge weight; naive clamping
double-counts on steep descents; and DEM noise enters *per edge*, not per
ride. The realisation is deployed in an open-source energy-field router
(Simujaules); all code and gates are published.


<!-- The two claims A3 must eventually carry. Neither has a value yet. -->


## 1. Introduction

- **1.1 The routing problem.** Minimum-energy (not minimum-distance/time)
  routing over an 8-connected DEM grid; asymmetric costs (A→B ≠ B→A) make the
  field a directed one; why energy fields (isochrone-style reachability in kJ)
  rather than single routes. Existing tools route by distance/time/“hilliness”
  heuristics; TODO literature pass (energy-aware routing, e-bike routing,
  Sobek/Brouter-style cost functions — extend `research/notes/literature-context.md`
  and `simujaules-literature-context.md`).
- **1.2 What the ride-level law provides.** Recap of paper 1's form 3/4 and
  the coasting-deficit ε; why it cannot be used as-is per edge (three
  non-local ingredients: deadband, route-aggregate ε, climbing share).
  **Update [E63–E69]: the deadband's non-locality is now decomposed** —
  roughly seven-eighths of its explanatory work is a kinetic-energy valley
  toll min(D, H, h_KE) computable from the profile's descent→climb valleys
  (buffer h_KE = (v_e² − v_c²)/2g from the branch fixed points), the rest a
  measurable noise floor plus a fitted residue shown to be corpus-absorbing
  (non-stationary within riders, non-transferable across them). The
  physically load-bearing part of the filter is therefore *graph-computable*:
  valleys are known at graph-build time. The dynamical scale that a strictly
  edge-local cost drops is the KE boundary layer — recovery length
  L_rec = m·v_f²/(C_rr·m·g + 3·½ρC_dA·v_f²) ≈ 90 m at the shared constants,
  i.e. ~3 edges at 30 m pitch — which is exactly why kinetic continuity
  between edges cannot be recovered by re-weighting single edges and needs a
  per-valley (two-edge-window) term instead.
- **1.3 The proposed edge realisation ("v2Edge").** [E17–E18,
  `regime_compare.py::r1d_v2_edge`] For an edge of length Δx and grade s:
  - climb edge (s ≥ 2%): E = α_r·Δx + β·k_s·Δh (aero gated off);
  - flat edge: E = (α_r + α_a)·Δx;
  - descent edge: E = α_r·Δx + β·k_s·(1 − ε(s))·|Δh| with grade-local
    ε(s) = clamp₀₁(min(1, (α/β)/s) − ε₀), floored at 0;
  - k_s scales β only (the scalar stand-in for the deadband).
  State the required cost-function properties for the search to be exact:
  additivity, non-negativity (ε ≤ 1 guarantees it), locality, and why
  direction-asymmetry is fine for Dijkstra but rules out bidirectional/A*
  without an admissible heuristic (TODO: derive the trivial lower-bound
  heuristic α_r·d and check admissibility).
- **1.4 Hypotheses.** TODO — pre-register before running anything new.
  Candidates: (H1) edge-sum over a measured ride's own path reproduces the
  ride-level form 3 within the paper-1 CI at the calibration scale; (H2) the
  edge cost's error grows monotonically as DEM resolution departs from the
  30 m calibration scale unless constants are re-fitted or the raster
  pre-smoothed [E19–E21 partial]; (H3) minimum-energy routes differ
  materially from minimum-distance ones only above a hilliness threshold
  (detour experiments, [E26 `e26_detour.py`]); (H4) the two elevation repairs
  do not stack at edge grain either — pre-smoothing the raster and re-weighting
  portal edges remove the same artifact, so applying both over-corrects, as
  measured at route grain in [E41] (§3.2 below). H4's edge-grain twist: a bridge
  may span one or two cells, so its vertical curve is sub-resolution and the
  straight-deck over-correction could be *larger* here than the −2.43 m
  [−3.26, −1.68] measured per touched ride at route grain.
  **New candidates from the E63–E69 programme:** (H5) a *valley patch* — the
  KE toll applied at graph-build time to each descent→climb node, replacing
  k_s's scalar stand-in for the deadband — reproduces the ride-level filtered
  form at edge grain without any non-local pass; the route-grain evidence
  (toll alone carries ~half the filter's benefit, toll + measured floor
  matches it, the fitted remainder is absorbing and NOT worth reproducing per
  edge) sets the expected ceiling before any run. (H6) the interruption
  component of ε₀ becomes *computable* here: the router knows junction
  density and node degree — precisely the collection-truncation information
  the ride-level calibration never had — so a per-node truncation term
  should explain part of the urban/highway ε split [E60–E61] from graph
  structure alone. (H7) the cost bundle's constants follow the measured-pin
  doctrine [E68–E69]: noise floors measured per chain (paper 2's rates),
  buffer from rider physics, ε the single fitted scalar — any constant
  *fitted* at edge grain is presumed absorbing until it survives a
  LORO-style transfer gate.

## 2. Methods

- **2.1 The engines.** Python reference `r1d_v2_edge` (in
  `src/harness/regime_compare.py`); the deployed mirrors (applet +
  Simujaules `energy-worker.js`, JS/Rust bit-parity). The mirror-set rule:
  any change lands in all copies.
- **2.2 Grids and DEMs.** FABDEM / DEM-SP; 8-connected grid, diagonal edge
  lengths; per-edge grade from cell elevations. Elevation-noise model per
  edge (paper 1 §2.4's per-sample jitter — here it hits *every edge
  independently*, no cancellation over a profile). [E6, E19]
- **2.3 Validation corpora and protocol.** Reuse paper-1 corpora D1–D5 under
  the frozen protocol; map each measured ride onto the grid (TODO: map-matching
  procedure — snap GPS to grid path; define acceptance criteria) and score
  edge-sum vs measured ∫P·dt with the same median/CI/gate conventions
  (mulberry32, seeds 42/43, B = 10⁴).
- **2.4 Scale experiments.** The existing chain: IGC 5 m ground truth
  [E19 `igc_resolution_test.py`], σ-smoothing calibration
  [E20 `goal_calibration.py`, `goal_smooth_rasters.py`], the
  resolution × smoothing × threshold trio [E21 `scale_trio.py`]. The
  ROUTE-grain prescription (DEM source → σ → constants) is paper 2's
  deliverable (paper2-dem-deployment.md, a letter this paper cites); this
  paper keeps only the EDGE-grain consequences (per-edge grade error,
  cost-surface stability under σ).
  **DONE — cite, do not re-derive** [E41]: paper 2's Table 2 IS that
  prescription (source × polyline step × σ → the c to use → the measured
  accuracy band), with σ applied to the *profile* rather than the raster —
  validated against E20's raster-space smoothing to −1.1% of h₊ (p90 6.9%).
  Its measured per-source noise rates are the numbers to inherit: barometric
  3.10 m/km [3.01, 3.18], IGC-SP 5 m 4.95 [4.89, 5.00], FABDEM sampled at
  30 m 7.52 [7.12, 7.76], FABDEM oversampled at 5 m 10.14 [9.86, 10.59].
  Two route-grain results this paper must NOT assume carry over unchanged:
  (i) the penalty is terrain-dependent (bias shift +0.7 pp on gentle terrain
  vs +20.1 pp on mountain brevets), so an edge-grain scale rule fitted on
  urban grids will not hold on escarpments; (ii) oversampling a coarse DEM
  is itself a cost (FABDEM at 5 m steps doubles h₊ vs 30 m steps and costs
  0.7 pp accuracy / 2.3 pp bias) — a router on an 8-connected grid samples
  at the grid pitch, so this is a *grid-design* parameter here, not a free
  choice.
- **2.5 Sanity gates.** Synthetic gates already exist (`SANITY=1
  regime_compare.py`; scale/goal per-gate blocks, two documented-benign
  failures). TODO: a paper-2 `bootstrap_ci`-style battery re-deriving every
  number this paper will publish.

## 3. Results (planned)

- **3.1 Edge-sum vs ride-level law vs measurement** on D1 (and D2–D5 where
  grid coverage allows). TODO — the central new computation.
- **3.2 Scale dependence.** What [E19–E21] already show, promoted to results:
  constants drift with sampling interval; a 5 m DEM over-charges vs the 30 m
  calibration unless pre-smoothed (the Entry-20 σ anchors) or re-fitted;
  the deadband is *not* expressible as an edge weight (proof sketch: it is a
  running max/min over the path — non-local by construction) — hence the
  scalar c correction is the only form-3-family option available per edge.
  **Registered carry-over from [E41] — the repairs do not stack.** At route
  grain, σ-smoothing and the bridge/tunnel (portal) deck correction address
  the SAME artifact: after σ = 30 m the profile's in-span ascent already
  matches the barometer (+0.05 m [−0.29, +0.28]), and applying the deck as
  well subtracts twice and makes energy significantly worse (400/935 rides
  closer, p < 10⁻⁴). Both levers exist at edge grain too — the raster can be
  pre-smoothed AND portal edges re-weighted — so the same double-subtraction
  is available and must be tested, not assumed away. Related: the straight
  deck is a known-sign OVER-correction, because a road bridge carries a
  vertical curve the rider climbs and a chord erases it — measured against
  the ride's own barometer, −2.43 m [−3.26, −1.68] on bridges vs −0.29
  [−0.40, −0.20] on tunnels. At edge grain a bridge may span only one or two
  cells, so the crown is sub-resolution and the error could be larger, not
  smaller. TODO: an H4 pre-registering both.
- **3.3 Route studies.** Detour/portal experiments [E26]; minimum-energy vs
  minimum-distance routes on real Pedal Hidrográfico territory; energy-field
  maps (Simujaules). TODO: quantify H3.
- **3.4 Pitfall inventory (each with a demonstration).**
  - the dead `max(0,·)` clamp (deployed quirk — document, and what fixing it
    changes) [E18];
  - aero-gate discontinuity at the 2% threshold (cost jumps as an edge
    crosses the threshold; effect on route stability);
  - non-negativity vs steep-descent recovery (why ε ≤ 1 keeps Dijkstra
    honest; what a negative-cost variant would require — Johnson-style
    reweighting or a potential function γ·h, TODO: show mgh/k_eff *is* such a
    potential and what remains after subtracting it). Note the deliberate
    asymmetry with paper 1: the *ride-level* ε_d is published unclamped
    (its floor never binds on ride means — paper-1 Appendix A / journal
    Entry 32), but the *edge-level* ε(s) keeps its floor, because single
    30 m edges beyond the floor grade (≈ 15%) are common even where ride
    means are not — the floor is edge-scale model content, not dead code;
  - per-edge noise (no profile-level cancellation; expected inflation as a
    function of edge length — connect to c);
  - asymmetry and turn costs (out of scope for the physics, but state what
    the router must not assume);
  - momentum non-locality (paper-1 journal Entry 37): kinetic energy worth
    h_KE = v²/2g ≈ 2–6 m of climb carries across edges, and no per-edge cost
    can transport it — closely-spaced rollers (within the dissipation length
    λ = m/(ρ·C_dA) ≈ 200 m) are over-charged by construction. h_KE and λ
    bound the error's scale and the raster pre-smoothing that would absorb
    it; the deadband τ ≈ η·v_f²/2g reading makes the filter speed-dependent,
    which a deployment must either accept as calibrated-at-one-speed or
    parameterise;
  - the grade-resolved deficit (paper-1 journal Entry 34): pedalling occupancy
    fades monotonically with cell grade for all riders while intensity is
    rider-level — a per-EDGE ε₀(s) = ε₀·g(s) is therefore physically licensed
    at exactly this paper's grain, where paper 1's ride-level test could not
    profit from it. Candidate refinement of the edge ε(s) beyond the constant
    deficit; needs the paper-1 held-out discipline at edge grain.

## 4. Discussion (planned)

- What transfers from paper 1 unchanged (the physics split, the frozen
  constants, ε₀'s recurrence) vs what is genuinely new risk (scale coupling,
  locality restrictions). The refined ε₀(Δx) idea (paper 1 §4.4) is this
  paper's natural contribution if the scale experiments support a functional
  form. Limitations: one metropolitan region; grid model excludes surface
  type per edge (TODO: OSM surface tags as a C_rr field — privacy rule:
  Overpass queries must never derive from ride endpoints).

## 5. Conclusions (placeholder)

TODO after 3.1.

## Appendix (planned)

- A. Derivation: from the paper-1 integral formalism to the edge sum; the
  exact discretization error terms (what vanishes as Δx → 0, what does not —
  the deadband term does not).
- B. Admissible heuristic for A* (if 1.3's TODO pans out).
- C. Bit-parity protocol between JS and Rust engines.
