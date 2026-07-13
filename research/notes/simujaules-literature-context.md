# Research context — where simujaules' energy-field approach sits in the literature

How **simujaules** (sampasimu) — the browser tool computing cycling **energy fields** over
DEMs: single-source Dijkstra on an 8-connected raster with the asymmetric edge cost
`E ≈ α·dx + β·(dh₊ − ε·dh₋)`, energy-budget reachability areas (the 300 kJ accessibility
KPIs), optimal-path extraction, and multi-source density fields — relates to the published
research. For each piece this note names the **closest prior art** and labels the position
*standard* / *incremental* / *novel (no located precedent)*. Companion to
[literature-context.md](literature-context.md), which positions the **per-edge energy law**
itself (Martin 1998, Bigazzi–Lindsey, WeBike, Rapaport, Chung) — this note positions the
**field / routing / accessibility approach** and only cross-references the law.

> **Provenance.** Built by the repo's `/deep-research` harness (105 agents, 5 search angles,
> 23 primary sources fetched, 111 claims extracted → top 25 adversarially verified by 3-vote
> panels → **23 confirmed, 2 refuted**). Same corpus-bounded reading as the companion review:
> **"novel" = no precedent located in the nearest corpus** (GIS least-cost-path, robotics
> terrain planning, anisotropic-Eikonal solvers) — **not** a full-literature priority claim.
> Important asymmetry in this run: dimensions 1–3 (cost surfaces, robotics, grid bias) are
> well-evidenced with unanimous votes; dimensions 4–6 (energy isochrones, cycling
> accessibility, in-browser cost surfaces) produced **zero verified claims** — their leads
> (§4) are surfaced-but-unverified and the novelty labels there are correspondingly weaker.
>
> **Update 2026-07-12 — PEDMC read in full.** The run's single biggest flagged threat (Cakir
> et al., TU Wien) has since been obtained and read. It **is** a located precedent for
> energy-budget cycling accessibility, and §2g's claims (i) and (ii) are demoted accordingly
> (*novel* → *incremental*). It does **not** threaten the raster-field, discretization-bias,
> calibration, or in-browser contributions — and its edge model instantiates the exact
> naive-slope artifact Entry 23 quantified. See **§2g** (rewritten) and **§2h** (the residual,
> now-narrower novelty). The Baum leads remain unverified.

---

## 1. The map — the literatures and the canonical model in each

| literature | canonical reference(s) | what they establish (verified) |
|---|---|---|
| **GIS anisotropic cost-distance / LCP over DEMs** | Herzog (Internet Archaeology 36, 2014); Alberti's `movecost` (SoftwareX 2019); GRASS `r.walk` | Anisotropic accumulated-cost **surfaces** + least-cost-path extraction over a DTM are routine, **including genuine energy cost functions** (Herzog metabolic kJ/(kg·m), Pandolf, Van Leusen). `movecost` is "truly anisotropic" since v0.2 (signed per-direction rise-over-run). Herzog notes min-kJ ≡ min-kcal (scaling can't change the argmin) — LCP directly yields energy-optimal routes. **Caveat: all of it is pedestrian/animal *metabolic* energy, not mechanical wheel-kJ.** |
| **The time-domain structural twin** | GRASS `r.walk` (Aitken 1977 / Langmuir 1984) | Dijkstra single-source on a raster, 8-connected with a `-k` Knight's-move flag (= a 16-move ladder, "slower, but more accurate"), edge cost `T = a·ΔS + b·ΔH_up + c·ΔH_mod_down + d·ΔH_steep_down` — horizontal per-metre + charged climb + **partially refunded moderate descent** + charged steep descent (>12°). Structurally simujaules' cost, one regime finer, in **seconds not joules**. |
| **Robotics energy-optimal terrain planning** | Rowe & Ross 1990 (IEEE T-RA 6(5)); Sun & Reif 2005 (IEEE T-RO 21(1)); Ganganath et al. 2014, 2015 (IEEE TII 11(3)) | Minimum-**energy** paths over contoured terrain with gravity+friction physics (`C = mg·s·(μcosφ + sinφ)`), anisotropic via impermissible-traversal ranges (power-limited climbs, sideslope overturn) and **braking ranges** on descent. All of it **point-to-point** planning. |
| **Grid-move discretization bias** | Huber & Church 1985 (J. Transp. Eng. 111(2)); Herzog 2013b/2014; Nash & Koenig (AI Magazine 2013) | Worst-case elongation of 8-connected paths ≈ **8 %**, cut to **2.8 %** by Knight's moves (16) and **1.4 %** by A/B-moves (32); worst-case route deviation 20 % → 11 % → 4.6 %. The published remedy is **subdividing long moves with interpolated intermediate elevations** — Entry 23's profile-integrated long edges. |
| **Anisotropic Eikonal / ordered upwind** | Sethian & Vladimirsky (PNAS 2001); Mirebeau (FM-LBR 2012/14); CAMIS (Sánchez-Ibáñez et al., Intell. Serv. Robotics 2022) | Continuum solvers for direction-dependent cost. **CAMIS is the published slope-energy instance**: heading-relative energetic cost (gravity + slippage) solved with bi-directional OUM, explicitly contrasted with edge-restricted graph search. |
| **Energy-as-impedance for cycling routing *and* accessibility** — **the nearest neighbour** | **PEDMC** — Cakir, Gratzer, Schirrer, Canestrini, Alinaghi, Giannopoulos, Kölbl & Kozek (2026), *Transp. Res. Interdiscip. Perspect.* 35:101777, DOI 10.1016/j.trip.2025.101777 (CC BY) | **Read in full (§2g).** *Physiological* (metabolic) cycling energy as an edge weight on an OSM **street graph** (Vienna's 19th district), then out-of-the-box Dijkstra/A* for (a) min-energy routing vs min-distance/min-time and (b) **energy-budget accessibility** — Fig. 9 maps all nodes reachable within `E_r,max = 500 kJ` from one origin, directionally asymmetric uphill vs downhill. Also models **intersections** (traffic-light wait + re-acceleration KE) and **per-edge wind projection** — both of which simujaules lacks. Python/OSMnx/NetworkX, offline batch. |
| **Budget reachability / isochrones** *(unverified leads only)* | Baum, Buchhold, Dibbelt & Wagner (arXiv:1512.09090); Baum et al. EV routing (arXiv:2011.10400) | Time-budget isochrones on road networks (Dijkstra family, interactive at scale, server-side); EV graphs with negative recuperation arcs + SoC clipping (**point-to-point** routing). Neither verified in this run — see §4. |

Bottom line: **the field computation and the asymmetric anisotropic cost are standard
machinery** in at least two mature literatures, and — since PEDMC — **energy-budget cycling
accessibility is no longer unprecedented either**. What remains unlocated is narrower and more
specific than the pre-PEDMC reading claimed: **off-network raster energy fields in cyclist
*wheel*-kJ, with an empirically fitted recovery factor, computed in the browser, and with the
move-grid discretization bias actually measured** (§2h).

---

## 2. Simujaules' ingredients, positioned (verified)

### 2a. Anisotropic energy cost surface + path extraction over a DEM — **standard**

`movecost` (Alberti 2019) is the closest whole-tool analogue: accumulated slope-dependent
anisotropic cost **surfaces** + LCPs over a DTM, with metabolic-energy cost functions, in R.
Herzog's archaeological LCP treats kJ as a first-class cost with an asymmetric one-way curve
(downhill critical slope 10–15 %, uphill 35–40 %). Simujaules is **incremental in domain**:
cycling *mechanical* wheel-kJ with a tunable ε-refund, delivered in a browser — the precedent
is "energy-based anisotropic cost surface over a DEM", not the same energy quantity, mode, or
delivery. *(votes 3-0, 3-0, 2-1, 3-0)*

### 2b. The per-edge asymmetric cost with partial descent refund — **standard structure, incremental units**

`r.walk` is the direct time-domain twin: Dijkstra, raster, 8/16-connected, piecewise-linear
asymmetric cost where moderate descent *reduces* cost (a partial refund) and steep descent
(>12°) *adds* cost. Verified down to `raster/r.walk/main.c` (three-branch piecewise on the
sign of dh). Two deliberate divergences: simujaules outputs **kJ, not seconds**, and uses an
unconditional `ε·β·|dh|` refund with a non-negativity clamp instead of r.walk's third
steep-descent-charging regime. *(votes 3-0 ×4)*

### 2c. The move-grid discretization bias and its remedy (journal Entry 23) — **standard bias, novel terrain measurement**

The 8/16/32 ladder itself is quantified published prior art: Queen's ≈ 8 % worst-case
elongation, +Knight's → 2.8 %, +A/B-moves → 1.4 % (Huber & Church 1985; Herzog 2013b; Herzog
2014 as the accessible synthesis) — the exact move sets of Entry 23's Farey ladder, and 8 %
independently matches the octile bound `√(4−2√2) ≈ 1.0824`. The published remedy is Entry 23's
construct: **subdivide long moves and interpolate intermediate elevations so slope costs are
integrated along the edge** (Herzog's version is 2-neighbour IDW and self-described as "a
crude estimate"). What was **not located**: any quantification on real *anisotropic
energy* terrain — Entry 23's headline that terrain roughly **doubles** the pure-geometry
prediction (+12.7 % median at 5 m vs +5.7 % flat control, via contour-oscillation under the
asymmetric cost) has no found precedent, and neither does the naive-endpoint-Δh sign-flip
result. Those are the entry's actual contributions; the ladder economics are not.
*(votes 3-0 ×3)*

### 2d. Robotics slope-energy planning — **standard lineage; the ε-refund is the differentiator**

Rowe & Ross (1990) → Sun & Reif (2005) → Ganganath (2014/2015) compute minimum-energy terrain
paths with `C = mg·s·(μcosφ + sinφ)`. Their descent treatment is the **ε=1 special case
clamped at zero**: full gravity credit down to the critical braking angle `φ_b = −arctan(μ)`,
then cost exactly 0 (braking dissipates everything; Ganganath's Algorithm 3 returns 0, and
with μ=0.01, φ_b ≈ −0.57°, essentially every real descent is free). **No tunable recovery
factor, no surplus carried across a descent** — describe it as "no tunable ε; surplus
discarded at a zero clamp", *not* as ε=0 (that phrasing was refuted 0-3). The non-negativity
motivation is also published: Minetti's (2002) walker cost goes negative on steep downhills,
violating Dijkstra's non-negative-weight requirement — the hazard simujaules' per-edge clamp
guards against in principle (Entry 18: on real data that clamp is provably dead code).
*(votes 3-0, 2-0, 3-0, 3-0, 2-1, 3-0)*

### 2e. Field vs point-to-point — the strongest novelty evidence in this corpus

The robotics prior art is **uniformly point-to-point**. Ganganath 2015 discretizes DEMs
*exactly* as simujaules' terrain mode (weighted graph, 8-connected neighbourhoods, node =
DEM cell) — yet its contribution (Z*) exists to **avoid** the exhaustive single-source
expansion: energy-Dijkstra appears only as the optimality reference, and its 92.71 % map
exploration (vs Z*'s 33.20 %) is framed as *inefficiency*. The energy **field** simujaules
ships is precisely the computation that literature works to prune away — no source-to-all-cells
field, reachability area, or accessibility output located anywhere in the lineage.
*(votes 3-0 ×4)*

### 2f. The anisotropic-Eikonal alternative (Entry 23 §9.4) — **standard contrast**

CAMIS (Sánchez-Ibáñez et al. 2022) is the published slope-energy anisotropic-Eikonal instance:
heading-relative energetic cost solved with bi-directional OUM, "the Eikonal is the particular
isotropic case", explicitly positioned against edge-restricted graph search. Entry 23's
Eikonal experiment (heading bias eliminated on flat, signed interpolation bias on real
terrain, integration blockers) is an *evaluation against* this family, not a use of it — cite
CAMIS as the continuum contrast. Nuance: OUM also runs on a grid/mesh; the correct contrast is
edge-restricted vs continuous-update, which both CAMIS and Entry 23 make. *(votes 3-0 ×2)*

### 2g. Energy-budget cycling accessibility — **incremental** (PEDMC is the located precedent)

**This claim has been demoted.** The pre-PEDMC reading asserted that (i) reachable-area-within-
N-kJ as an accessibility KPI and (ii) energy as the accessibility impedance for cycling had no
located precedent. **PEDMC has both.** Its Fig. 9 is an energy-budget reachability map —
single origin → every node reachable within `E_r,max = 500 kJ`, computed on the energy-weighted
graph, and *directionally asymmetric* (its Fig. 9a/9b contrast outbound-uphill against
inbound-downhill accessibility, exactly the consequence of an asymmetric cost that simujaules
trades on). Its Fig. 12 bins nodes by trip energy and reports the accessibility gain of
energy-optimal over distance-optimal routing (69.2 % vs 63.4 % of nodes in the cheapest bin).
Cite it; do not claim the concept.

The differences that remain are real but are **substrate, unit, and validation** — not the
idea:

| | **PEDMC** (Cakir et al. 2026) | **simujaules** |
|---|---|---|
| substrate | OSM **street graph**, edges = road segments | **raster DEM**, 8-connected free-terrain field *(+ a street-graph mode, where PEDMC is the precedent)* |
| energy quantity | **physiological/metabolic** J: `P_physio = a + b·P_mech`, `a = 199 W` idle, `b = 7.4` | **mechanical wheel-kJ** (`α·dx + β·(dh₊ − ε·dh₋)`), no metabolic layer |
| descent | **no recovery** — `P_mech` clamped at 0 (brakes dissipate); descent still costs the idle term `a·t` | tunable **ε ∈ [0,1]** partial refund, *empirically fitted* |
| speed | **decision variable**: per-edge energy-minimizing `v`, s.t. 200–1000 W and 5–30 km/h | flat reference speed `v_f` + per-regime power |
| intersections | **modelled** (`E_i = P⁰_inner·t_tl + ½mv²`) | **not modelled** |
| wind | **per-edge projection** of a global vector (`v_w = v_wind·cos γ`) | scalar headwind in `α` |
| calibration | **none, by design** ("without the need for data-driven calibration") | per-rider fitted `(CdA, C_rr, ε, k_smooth)`; validated on ~2 300 power-meter rides, 4 riders |
| output | routes, node accessibility, forth-and-back effort maps | energy **fields**, budget areas, density fields, paths |
| delivery | Python 3.13 / OSMnx / NetworkX, offline batch | **in-browser Web Worker**, no build step (+ Rust, bit-parity) |

Two of PEDMC's ingredients are things **simujaules does not have and arguably should**: the
intersection cost (traffic-light wait + re-acceleration kinetic energy — material in dense
urban graph mode) and the per-edge directional wind projection. Its round-trip ("forth &
back") effort mapping is also a product idea worth stealing.

**But note what its edge model is.** PEDMC's assumption **A4** ("an edge is described by
constant properties, e.g. a mean slope") and **eq. (5)**, `θ_ij = arctan(Δz_ij / d_ij)` from
the two endpoint node elevations, is *exactly* the naive endpoint-Δh construct that journal
**Entry 23** identified and quantified: costing a long edge from its endpoint height difference
**flattens the relief the edge crosses**, and on real terrain that error is large enough to
**flip the sign** of the discretization bias (naive sq16 at 30 m reads −1.3 % against a true
+2.7 %). On an OSM graph over rolling terrain — Vienna's 19th district is explicitly hilly in
its north-west — segment-mean slope systematically under-charges within-edge relief. This is a
substantive, citable methodological gap in PEDMC, and it is direct evidence that Entry 23's
contribution is *not* covered by this prior art. *(Their §2.5 notes the DEM is used only to
attach elevation to nodes; no profile integration along the segment is performed.)*

**Scale invariance — why the demotion is real but the precedent is fragile exactly where it
binds.** PEDMC advertises being "grounded in interpretable physical relations without the need
for data-driven calibration". Read precisely, that means *no artificial route-choice weighting
factors* (the contrast is with utility-based models like Broach et al.); it is **not** a claim
to be free of empirical content — their eq. (7) is itself a two-parameter regression on
Spitzer's (1982) seven-point table. Uncalibrated first-principles modelling is legitimate and
is what this repo's own `canonical()` engine does. The deficiency is not missing *calibration*
but missing **validation**: no predicted joule in the paper is ever compared to a measured one.

That has an asymmetric consequence, and it is the single most useful thing to say about them:

- **Their routing results are calibration-robust.** A minimum-energy path is an *argmin*, and
  an argmin is invariant under monotone rescaling of the cost — Herzog's "min-kJ ≡ min-kcal"
  point (§1). "Energy-optimal routes differ from distance-optimal routes" survives a badly
  mis-estimated `b`.
- **Their accessibility results are not.** Imposing a **budget** (`E_r,max = 500 kJ`) *breaks*
  scale invariance: a threshold on an absolute quantity is precisely what an uncalibrated
  absolute quantity cannot support. If `b = 7.4` is wrong — and 13.5 % delta efficiency against
  Ettema & Lorås's own 20–25 % suggests it is (§3) — the 500 kJ contour is in the wrong place
  and the 69.2 % / 63.4 % split moves with it.

The budget-accessibility product is exactly what demotes our §2g claim. So the correct posture
is: **they reached the concept first, and the concept is where their methodology is least able
to support the claim — which is why the validation chain (Entries 12–22) is load-bearing here
rather than decorative.** State it that way. A "they didn't validate, we did" argument is
strong; a "physics without fitting isn't science" argument is false, self-incriminating (our ε
is fitted), and reads as sour grapes.

### 2h. What remains novel after PEDMC (corpus-bounded, and now narrower)

The honest residual — smaller than the pre-PEDMC claim, but more specific and therefore
stronger:

1. **Off-network raster energy fields.** "kJ to reach every *cell*", not every node of a road
   graph. PEDMC cannot answer the question off the street network at all; the robotics lineage
   can, but only point-to-point (§2e). No cycling energy **field** over a DEM located.
2. **The move-grid discretization bias, measured on anisotropic energy terrain** (Entry 23).
   The isotropic geometric ladder is published (§2c); the terrain-doubling result, the
   contour-oscillation mechanism, and the naive-edge sign-flip are not — and PEDMC *embodies*
   the artifact rather than addressing it.
3. **An empirically fitted recovery factor ε, and a validated energy law.** PEDMC is
   uncalibrated *by design* and never compares a predicted joule against a measured one; this
   repo's ε, CdA and C_rr are fitted and tested against ~2 300 power-meter rides across four
   riders, with a pre-registered ±5 % accuracy goal (Entry 20) and bootstrap CIs (Entry 22).
   **This is the clearest depth difference and the easiest to defend.**
4. **In-browser, client-side DEM energy fields.** Unchallenged: PEDMC is offline Python batch.
5. **Wheel-kJ as the unit.** Weakest of the five — PEDMC's `P_physio` is an *affine* function
   of `P_mech`, so this is a unit and a metabolic-floor term, not a different idea. Do not
   lean on it.

*(§2g demotion and §2h are synthesis judgements against a source read in full, not voted
claims.)*

---

## 3. Corrections & citation flags (from verification)

- **Units divergence is the dominant qualifier everywhere.** Prior-art "energy" is pedestrian/
  animal *metabolic* expenditure (movecost's Pandolf/Van Leusen/Herzog) or robot mechanical
  energy (Rowe–Ross) — not the cyclist's aero+rolling+gravity wheel-kJ with a tunable ε. The
  precedent is *energy-as-anisotropic-edge-cost*, not the same quantity or mode.
- **The 8 %/2.8 %/1.4 % and 20 %/11 %/4.6 % figures are worst-case isotropic geometric
  bounds.** Cite the primaries — Huber & Church 1985 and Herzog 2013b — with Herzog 2014
  (DOI 10.11141/ia.36.5) as the accessible synthesis. Link the *section* pages
  (`intarch.ac.uk/journal/issue36/5/3.html`, `…/5/5-1-4.html`); the index page 403s to plain
  fetchers.
- **Ganganath 2015:** the CORE mirror (`core.ac.uk/download/pdf/61140802.pdf`) 404s — cite the
  PolyU IRA copy or DOI 10.1109/TII.2015.2412267.
- **`r.walk`'s `walk_coeff` is labelled "walking energy formula" but outputs TIME (seconds)**
  — a Naismith naming artifact. Do not cite r.walk as an energy-surface tool.
- **movecost's anisotropy is a v0.2 feature** (2-1 vote, but well-attributed in the changelog)
  — don't cite the original release for it.
- **arXiv:1512.09090 authors are Baum, Buchhold, Dibbelt, Wagner** — Pajor is *not* an author
  (a draft claim here said otherwise).
- **Refuted (2/25):** (1) "Minetti/Llobera–Sluckin curves have their minimum at ≈ −10 %
  grade, so descent is cheaper than flat" — 1-2, does not survive as stated; use Herzog's
  negative-cost observation (2d) instead. (2) "Ganganath's descent model is the ε=0 case" —
  0-3, it is ε=1-up-to-a-zero-clamp (see 2d).
- **Entry 18 caveat carried over:** simujaules' own per-edge clamp is an inert safeguard on
  real data — "avoids the negative-cost hazard by clamping" is true in principle only.

### PEDMC-specific flags (from the full read — verify against the typeset PDF)

*These come from a text extraction of the article, not the typeset PDF; the arithmetic ones are
worth a 30-second check before they go into print.*

- **⚠ Its kJ are NOT our kJ — never compare the budgets directly.** PEDMC's `E_r,max = 500 kJ`
  is *metabolic*; simujaules' 300 kJ is *at the wheel*. The map is `P_physio = 199 W + 7.4·P_mech`,
  so the two scales differ by roughly an order of magnitude **plus** a time-proportional idle
  term. Their Table 4 makes this concrete: a **1.65 km** route costs **185.2 kJ** (≈ 640 W mean
  metabolic ⇒ only ≈ 60 W mechanical). Any sentence putting "500 kJ" and "300 kJ" near each
  other without this conversion is wrong.
- **Their fitted `b = 7.4` implies a delta efficiency of 1/7.4 ≈ 13.5 %**, below the **20–25 %**
  range reported by Ettema & Lorås — the very source they cite for the concept. The regression
  is fitted on Spitzer's (1982) 7-point flat-track table using `C_d·A = 0.45 m²` and
  `C_r = 0.003`; a low `P_mech` from those parameters would inflate `b`. Treat `b` as an
  *effective* fitting constant, not a physiological measurement — the same caveat this repo
  applies to its own fitted CdA/C_rr (Entry 20).
- **Eq. (8) drops the `cos θ` that eq. (4) carries** on the rolling term. Almost certainly an
  unstated small-angle approximation (≈0.7 % on the rolling term at their 12 % traversability
  cutoff) rather than an error, but it is an inconsistency between their own two equations.
- **Fig. 12's energy-bin labels are internally inconsistent as extracted** ("0 kJ to 3 × 10⁶ kJ"
  = 3 GJ is not a bicycle trip; the axis is presumably 10⁶ **J**). Read the figure from the PDF
  before quoting the 69.2 % / 63.4 % accessibility split.
- **Slopes > 12 % are simply non-traversable** in PEDMC (the per-edge optimization goes
  infeasible against `v ≥ 5 km/h` and `P_physio ≤ 1000 W`). Fine for Vienna; it would delete
  real streets in São Paulo. simujaules has no feasibility cutoff — worth a sentence, since it
  is a genuine modelling difference rather than a flaw in either.
- **Its own bibliography is a lead mine** — see §4; `Shirabe (2008)` in particular is the one
  our sweep should have caught and didn't.

---

## 4. Gaps, leads, and follow-ups (dimensions 4–6 — unread unless marked)

None of the following survived into the verified set; treat as leads, not citations.

> **PEDMC — resolved (2026-07-12).** No longer a lead: obtained, read in full, and folded into
> **§2g/§2h**. Outcome: it **did** demote the accessibility-novelty claim, as anticipated.
> It is now a required citation, not an open risk.

### New leads harvested from PEDMC's own bibliography

Our sweep missed these; they sit closer to dimension 5 than anything it surfaced, and the first
is a *second* potential threat to §2h(1):

- **⚠ Shirabe (2008) — the one to read next.** Per PEDMC's §1.1: "a shortest path problem
  variant that aims at minimising the amount of **pedaling work** when traversing elevated
  bicycle networks… formulated as a quadratic integer program where edge weights depend on a
  cyclist's **kinetic energy and elevation changes**." That is *mechanical* work (not
  metabolic) as a cycling edge cost with elevation asymmetry — i.e. potentially a closer
  precedent for the **wheel-kJ** framing than PEDMC itself, which would further weaken §2h(5).
  PEDMC's stated gap in it ("ignores environmental effects like traffic lights, air drag, or
  global wind") suggests it will *not* threaten §2h(1)–(4). **Read before publishing.**
- **Raffler, Brezina & Emberger (2019)** — GIS-based **mechanical** energy expenditure used to
  explain spatial variation in bicycle commuting across Austria. Mechanical energy + GIS +
  cycling, but *aggregate regression on modal share*, not route-level or field-level; per PEDMC
  it "lacks the individualized modeling necessary for route optimization". Likely a supporting
  citation for "kJ is the right impedance", not a competing one.
- **Kölbl & Helbing (2003)** and **Kölbl & Kozek (2021)** — physiological energy expenditure as
  the single strongest explanatory variable for travel behaviour across modes, validated on
  national travel surveys (DE/CH/UK/US, 1972–2017). This is the **motivating** citation for
  energy-as-impedance and it is strong; worth borrowing for the working paper's framing
  regardless of the novelty question. (Kölbl is a PEDMC co-author.)
- Lesser: **Ausri & Bigazzi (2024)**, **Kolsung et al. (2020)** (cycling energy expenditure);
  **Hrnčíř et al. (2017)** (tri-criteria bicycle routing incl. elevation gain, Pareto);
  **Ziemke et al. (2017/2019)** (MATSim bicycle module, slope-aware but utility-based).

### Still-open leads from the original sweep

- **Baum, Buchhold, Dibbelt & Wagner (arXiv:1512.09090):** isochrones = *time*-budget
  reachability areas on road networks, Dijkstra family, milliseconds at continental scale
  (server-side). Budget-reachability **areas** exist as prior art; the energy-unit version is
  what's missing.
- **Baum et al. (arXiv:2011.10400):** EV road graphs with **negative recuperation arcs** and
  battery SoC clipping at 0/capacity — a published graph-based asymmetric energy model with
  recuperation, but **point-to-point** routing, not fields. Also a transferable caveat:
  energy-optimal routes detour onto slow minor roads because lower speed cuts aero drag —
  worth a sentence when interpreting optimal-energy fields vs time-optimal ones.
- **A/B Street "15-minute neighborhoods" (issue #393, 2020):** budget-limited Dijkstra
  floodfill reachability as an accessibility instrument — time-based, network-based, no
  elevation; the *pattern* precedent for KPI-style reachability, not the energy version.
- **In-browser raster compute:** GeoBlaze does client-side GeoTIFF analytics but no
  cost-distance/LCP/isochrones; the 2023 WebGIS comparison literature is vector-only
  (Turf.js). Client-side *routing* exists (route_snapper: Rust→WASM Dijkstra on a prebuilt
  street graph, 2021). No in-browser DEM cost-surface/energy-field tool was located —
  simujaules' delivery claim survives, unverified.
- **Open question from 2c:** does the anisotropic-fast-marching error-analysis literature
  (Sethian & Vladimirsky lineage) already contain a terrain-amplified grid-bias result that
  would demote Entry 23's "terrain doubles the octile prediction"? Not found; not exhausted.

---

## 5. Related work (drop-in)

> Computing cost fields over terrain by single-source shortest paths on a raster is
> long-established in GIS: GRASS's `r.walk` accumulates anisotropic hiking *time* on an 8- or
> 16-connected grid with separately coefficiented climb and descent terms — moderate descents
> partially refunded, steep descents charged — after Aitken (1977) and Langmuir (1984), and
> archaeological least-cost-path practice routinely substitutes metabolic *energy* cost
> functions (Herzog 2014; Alberti 2019). The bias introduced by restricting movement to a
> discrete move set is likewise quantified there: worst-case path elongation of ≈8 % for the
> 8-neighbourhood, reduced to 2.8 % and 1.4 % by 16- and 32-move sets (Huber & Church 1985;
> Herzog 2013), with subdivided, elevation-interpolated long moves as the standard remedy —
> our profile-integrated edges (§—) instantiate this, and our measurements extend it to
> asymmetric energy costs on real relief, where the bias roughly doubles its geometric bound.
> In robotics, minimum-energy paths over contoured terrain descend from Rowe and Ross (1990)
> through Sun and Reif (2005) to Ganganath et al. (2014; 2015), who discretize DEMs into
> 8-connected weighted graphs exactly as we do; their gravity-and-friction cost treats
> descents as free below a critical braking angle — a zero-clamped special case of our
> tunable recovery factor ε — and their contribution is heuristic *point-to-point* search
> that explicitly avoids the exhaustive single-source expansion whose product, the energy
> field itself, is our object of interest. Continuous alternatives to move-grid search exist
> as ordered-upwind/anisotropic-Eikonal solvers (Sethian & Vladimirsky 2001), including a
> slope-energy instance for planetary rovers (Sánchez-Ibáñez et al. 2022); we evaluate this
> family and retain edge-restricted search for its exactness, monotonicity, and
> budget-early-exit properties (§—). Budget-constrained *reachability areas* appear in the
> road-network isochrone literature with time as the budget (Baum et al. 2016) and in
> electric-vehicle routing as point-to-point search over graphs with recuperation arcs (Baum
> et al. 2020). Closest to the present work, Cakir et al. (2026) weight an OSM street graph of
> Vienna by a cyclist's *physiological* energy demand — a linear metabolic map over the same
> mechanical power balance, plus intersection and wind terms we do not model — and use it both
> to route and to map energy-budget accessibility, establishing energy-as-impedance for
> cycling accessibility as prior art. We differ in substrate, in unit, and in validation: our
> fields are computed off-network over a raster DEM rather than on a road graph, in mechanical
> wheel-kJ with an empirically fitted asymmetric recovery factor ε rather than in uncalibrated
> metabolic joules, and are validated against measured power-meter energy across four riders
> (§—). The distinction is not merely presentational: because their edges carry a single mean
> slope derived from endpoint elevations (their eq. 5 and assumption A4), the relief *within* an
> edge is flattened — the precise artifact our discretization analysis quantifies (§—), where
> costing long moves from endpoint height differences is shown to be capable of reversing the
> sign of the resulting bias. We are not aware of prior work computing cycling energy fields
> off-network over a DEM, of a published measurement of move-grid discretization bias under an
> asymmetric energy cost on real terrain, or of in-browser computation of such fields.

*(Fill the §— cross-references. **Cakir et al. is now read and safe to cite as written.** The
Baum 2016/2020 sentences remain unverified against the primaries — and **Shirabe (2008)** (§4)
should be read before the final "we are not aware of…" sentence stands, as it may be a closer
precedent for the mechanical-work framing.)*

---

## Sources (fetched; ✓ = grounded verified claims, ★ = read in full, ○ = surfaced only)

- ★ **Cakir, A., Gratzer, A. L., Schirrer, A., Canestrini, M., Alinaghi, N., Giannopoulos, I.,
  Kölbl, R. & Kozek, M. (2026), *Physiological energy demand modeling for cycling and network
  graphs* (PEDMC), Transportation Research Interdisciplinary Perspectives 35:101777,
  DOI 10.1016/j.trip.2025.101777** (open access, CC BY; online 12 Dec 2025). **The nearest
  neighbour — §2g, §2h, §3.** Read in full 2026-07-12.

- ✓ Herzog, *Least-cost Paths — Some Methodological Issues*, Internet Archaeology 36 (2014),
  DOI 10.11141/ia.36.5 — §3 (`…/issue36/5/3.html`), §5-1-4 (`…/issue36/5/5-1-4.html`)
- ✓ Herzog, *Theory and Practice of Cost Functions* (CAA proceedings)
- ✓ Alberti, `movecost` — SoftwareX (2019); github.com/ElsevierSoftwareX/SOFTX_2019_230; CRAN
- ✓ GRASS GIS `r.walk` manual (grass78/grass-stable) + `raster/r.walk/main.c` (OSGeo/grass)
- ✓ Rowe & Ross (1990), IEEE T-RA 6(5) — faculty.nps.edu/ncrowe/elevation2.htm
- ✓ Sun & Reif (2005), IEEE T-RO 21(1):102–114 — users.cs.duke.edu/~reif (PDF)
- ✓ Ganganath, Cheng & Tse (2014) — PolyU IRA 10397/53652
- ✓ Ganganath et al. (2015), IEEE TII 11(3):601–611, DOI 10.1109/TII.2015.2412267 — PolyU IRA
  10397/31415 (CORE mirror dead)
- ✓ Sánchez-Ibáñez et al., CAMIS — arXiv:2103.03849; Intell. Serv. Robotics (2022),
  DOI 10.1007/s11370-022-00450-6; github.com/spaceuma/CAMIS_python
- ✓ Sethian & Vladimirsky, Ordered Upwind Methods — PNAS (2001), doi 10.1073/pnas.201222998
- ○ Nash & Koenig, *Any-Angle Path Planning* — AI Magazine (2013)
- ○ Mirebeau, anisotropic Fast Marching (FM-LBR) — arXiv:1201.1546
- ○ Ferguson & Stentz, Field D* — CMU RI (2005)
- ○ IJGIS (2020) raster-LCP move-restriction paper — tandfonline 10.1080/13658816.2020.1850734
- ○ Baum, Buchhold, Dibbelt & Wagner, isochrones — arXiv:1512.09090
- ○ Baum et al., EV constrained shortest paths — arXiv:2011.10400
- ○ A/B Street issue #393 (15-minute neighborhoods); route_snapper; GeoBlaze; WebGIS
  in-browser geoprocessing comparison (2023)

**Unread, via PEDMC's bibliography (§4) — priority order:**

- ○ **Shirabe (2008)** — min-**pedalling-work** shortest paths on elevated bicycle networks
  (quadratic integer program; kinetic energy + elevation change edge weights). **Read next.**
- ○ Raffler, Brezina & Emberger (2019) — GIS mechanical-energy expenditure vs cycling modal
  share, Austria
- ○ Kölbl & Helbing (2003); Kölbl & Kozek (2021) — physiological energy as the governing
  variable of travel behaviour (the framing citation)
- ○ Hrnčíř et al. (2017) tri-criteria bicycle routing; Ziemke et al. (2017/2019) MATSim bicycle
  module; Ausri & Bigazzi (2024); Kolsung et al. (2020); Spitzer et al. (1982) (PEDMC's
  metabolic source data); Ettema & Lorås (2009) (delta efficiency)
