# Research context — where this energy model sits in the literature

How the `bicycling-energy-model` (its two engines, the closed-form law, the ε recovery
factor, `k_smooth`, the DEM/ascent work, and the validation on real rides) relates to the
published research. For each of our pieces this note names the **closest prior art** and
labels it *standard* / *incremental* / *apparently-novel*.

> **Provenance & caveat.** Compiled from targeted web searches with primary sources checked
> directly (URLs at the end). The repo's `/deep-research` harness was attempted twice and
> failed in this build (a `StructuredOutput` retry-cap bug in the workflow runtime, before any
> search ran), so this lacks that tool's adversarial citation-verification. **Novelty calls are
> therefore "apparent" — a literature search, not a patent/priority search.** Treat them as
> "I did not find prior art for X", not "X is new".

---

## 1. The map — six literatures and the canonical model in each

| literature | canonical reference(s) | what they establish |
|---|---|---|
| **Road-cycling power physics** | Martin et al. 1998 | A force-balance power model (gravity + aero + rolling + bearing + inertia) predicts measured road power at **R² = 0.97, SE = 2.7 W**. di Prampero's 1979 "equation of motion of a cyclist" is the earlier statement. |
| **Cycling energetics / physiology** | di Prampero 1986; Minetti 2002 | Energy cost of locomotion vs slope; the **uphill/downhill asymmetry** and the downhill *eccentric-braking* regime (Minetti, for running: cost minimises near −10…−20 % grade then *rises* again on steep descents). |
| **Energy-/effort-aware bike routing** | slope-cost path analysis; mesoscopic "driving-cycle" energy models | Route cost = integrated segment power; adding slope improves energy estimates markedly; revealed-preference work on energy-vs-time trade-offs. |
| **E-bike range / route energy** | static energy models w/ DEM + recuperation (e.g. e-Energy 2016; Electronics 2022) | Predict battery use over a planned route from DEM elevation, mass, speed, **and a recuperation/regeneration term** — the e-bike twin of our descent recovery. |
| **DEM / road-grade & cumulative ascent** | crowd-sourced-grade (PLOS 2023); "Mountain biking meets Mandelbrot" (2010) | Grade accuracy dominates energy error (**1 % grade error → ~57 W / 56 % at 20 km/h**); **cumulative ascent is scale-dependent ("fractal")** — there is no single true value, only a value *at a smoothing scale*; barometric beats raw GPS. |
| **CdA / Crr field estimation** | Chung "virtual elevation" method | Invert the power balance: guess CdA/Crr, integrate to a *virtual elevation*, adjust until it matches the real profile (or flattens on a loop). Energy-balance inversion to recover a hidden parameter. |
| *(practical / commercial)* | Best Bike Split; GoldenCheetah | Physics power-to-speed over a real course (CdA, Crr, gravity, wind) → race-time prediction within 2–3 %; CdA estimated from ride data (Chung-style "Aero Analyzer"). Closed, cloud, racing-oriented. |

The takeaway: **our two engines are squarely on the validated ground of this field.** The
`canonical()` simulation *is* the Martin-1998 / di Prampero force balance integrated forward.
The closed form's `α·x + β·h₊` is that same physics under a steady-speed assumption. So the
question is never "is the physics right" — it is "what do our *specific* simplifications and
*specific* analyses add?"

---

## 2. Our contributions, positioned

### 2a. `canonical()` forward simulation — **standard**
It is the Martin-1998 model (gravity, aero with wind, rolling on `cosθ`, a brake cap, KE via a
semi-implicit update). Closest prior art: Martin 1998; the Dahmen/Saupe Konstanz "model + simulator
on real tracks" line. *Additive only as a clean, open, auditable reference implementation* and as
the **shared-constants control** for §2c.

### 2b. Closed form `E ≈ α·x + β·(h₊ − ε·h₋)` — **mixed; the ε packaging is the additive part**
- `α·x + β·h₊` (charge resistance over distance, pay `mg·h₊` for climbing): **standard** — the
  textbook integral of the power balance at steady speed; every routing/e-bike energy model above
  uses it.
- The **lumped descent-recovery factor ε** and, especially, a **closed form for it** is where the
  contribution sits. The *concept* of asymmetric recovery is well known (Minetti's downhill regime;
  the e-bike *recuperation* term; the pacing literature on "you give back less on the descent than
  you spend on the climb"). What I did **not** find in the literature is our specific result:
  **`ε(s) = min(1, α/(β·s))` derived from a coasting (idle-leg) limit, drop-weighted over the
  descent profile, with a calibrated constant offset (`−0.13`), and validated against a
  power-measured descent-energy-balance ε** (corr 0.83–0.87 on real-descent rides). → *apparently
  novel as a packaged, validated closed form*; the closest prior art is Chung's virtual-elevation
  inversion (§2g) and the e-bike recuperation coefficient (which is usually a fixed efficiency, not
  a grade-dependent closed form).

### 2c. Parameter-shared closed-form-vs-simulation comparison — **apparently-novel framing**
Running both engines on the **same** physical constants so the gap isolates *modelling*
simplification from *parameter* error. Validation papers typically validate **one** model against
measurements (Martin 1998) or compare products. A controlled "cheap law vs full sim on identical
inputs, across many real rides" is a clean methodological framing I did not find packaged
elsewhere. *Additive* — and it is what licenses the headline result that the **closed form is as
accurate as the simulation** (~4–7 % median on our rides).

### 2d. `k_smooth` / deadband for *fractal* cumulative ascent — **apparently-novel synthesis**
The **problem** is established and citable: cumulative ascent is scale-dependent ("Mountain biking
meets Mandelbrot", 2010) and grade error dominates energy error (PLOS 2023). The **fix usually
discussed** is "smooth the elevation / use barometric / threshold the gains". Our move —
folding that smoothing into the *closed-form energy law* as a scalar
`k_smooth = 1 − c·x/h₊` (with `c ≈ 0.003`, a ~3 m/km "noise grade") so the law self-corrects from
*totals only* — is, as far as I found, **not** in the literature. → *apparently novel*; the
underlying scale-dependence and the deadband idea are not.

### 2e. Validation on real **non-racing social / urban** rides — **incremental but genuinely additive**
The validation corpus of this field is lab ergometers, time trials, and racing (Martin 1998; Best
Bike Split). Our test set — 44 power-meter club rides + 62 *urban São Paulo* social rides, with
stop-go, photo stops, and walking — is a **different population and regime**. Additive pieces: a
**physical-floor data-quality filter** (measured `∫P·dt` must exceed climbing PE `mg·h₊/k_eff`,
else the ride was not fully pedalled) and **cadence-based** disambiguation of sensor-dropout vs
pushing the bike. These are practical contributions to "validating energy models on messy
real-world data". Closest prior art: the crowd-sourced-grade / mesoscopic-cycling line, which also
works from real fitness-app data but targets *grade*, not energy-model validation.

### 2f. Energy↔time duality (`x* = x + k₊·h₊ − k₋·h₋`, `k₋` ≈ time-twin of ε) — **apparently-novel framing**
The *facts* are standard (climbing costs time, descending returns less than it cost — the Swain
pacing result). Stating it as a **symmetric pair of closed forms** with a descent *time*-coefficient
`k₋` that mirrors the descent *energy*-coefficient `ε`, linked through descent power, is a tidy
framing I did not find elsewhere. *Additive, modest.*

### 2g. The ε / k_DEM inference machinery — **incremental (Chung-adjacent)**
Our `epsFromFIT` (solve the descent energy balance for ε) and `k_DEM` (fit a per-source ascent
correction) are **the same family of move as Chung's virtual elevation**: invert an energy/identity
relation to recover a hidden quantity (Chung recovers CdA/Crr; we recover ε and an ascent scale).
Honest positioning: *method-standard, target-new*. We should cite Chung explicitly rather than
imply the inversion is ours.

### 2h. The São Paulo-ε **negative result** — **additive (negative results are under-published)**
"Urban stop-go braking suppresses ε" — **refuted**: recovery does not scale with braking density,
because on a descent *gravity* repays the post-stop re-acceleration, not the legs. Documented
negative results like this (with the mechanism) are exactly what the applied literature usually
omits. *Additive, small.*

---

## 3. Gaps, opportunities, and what's publishable

- **Most publishable as a short note:** the **closed-form ε** (§2b) *plus* the **parameter-shared
  comparison** (§2c) *plus* the **social/urban validation** (§2e), framed as *"A validated
  closed-form descent-recovery factor for route energy estimation, and when the cheap law suffices."*
  That bundle has a clear gap (closed-form ε is apparently new), a method (shared-constants control),
  and evidence (real rides, two regimes). Target: *Findings*, *PLOS One*, or a sports-eng venue.
- **Second note:** the **`k_smooth` / fractal-ascent-in-a-closed-form-law** (§2d) reads well next to
  the Mandelbrot-ascent paper and the crowd-sourced-grade paper — a focused "how to make a totals-only
  energy law robust to scale-dependent ascent" piece.
- **Open gaps worth chasing (and citable hooks):**
  - *Terrain-aware ε* — our data shows ε is grade-driven on open rides but a constant on urban
    ones; a single ε-selection rule across regimes is unresolved.
  - *Rider-behaviour variance* — the unexplained per-ride ε scatter (pedalling downhill) is a
    behaviour signal, not geometry; links to the pacing literature (Swain).
  - *k_DEM beyond São Paulo* — our per-source correction is calibrated on one region; the DEM
    community (FABDEM, Copernicus) would value a multi-region along-track validation.
- **Where we are *not* novel and should say so:** the forward model (Martin), the `α·x + β·h₊`
  core, the energy-balance inversion *technique* (Chung), and the existence of a recovery/recuperation
  term (e-bike literature). Claiming these would be wrong.

---

## 4. Related work (drop-in)

> The mechanical-power model of road cycling is well established: a force balance over gravity,
> aerodynamic drag, rolling resistance, bearing friction and inertia predicts measured power to
> within a few watts [Martin et al. 1998], building on di Prampero's equation of motion of a
> cyclist [di Prampero 1979, 1986]. The asymmetry of climbing and descending — and the eccentric
> "braking" regime on steep descents — is documented energetically by Minetti et al. [2002] and,
> for pacing, by Swain [1997]. Estimating route energy from elevation is standard in energy-aware
> bicycle routing and in e-bike range models, the latter including an explicit recuperation term
> analogous to our descent-recovery factor ε [e-bike energy-routing literature]. Two measurement
> realities shape any such estimate: grade error dominates the energy error (a 1 % grade error is
> ~57 W at 20 km/h [Salon et al., PLOS One 2023]), and cumulative ascent is scale-dependent — there
> is no single true elevation gain, only a value at a chosen smoothing scale ["Mountain biking
> meets Mandelbrot", 2010]. Our descent-balance and per-DEM-source fits follow the energy-balance
> inversion popularised by Chung's "virtual elevation" CdA/Crr method. Against this backdrop, this
> project contributes a validated closed form for ε, a totals-only `k_smooth` correction for fractal
> ascent, a parameter-shared closed-form-vs-simulation comparison, and validation on non-racing
> social and urban rides.

---

## Sources

- Martin, Milliken, Cobb, McFadden, Coggan (1998), *Validation of a Mathematical Model for Road
  Cycling Power*, J. Applied Biomechanics 14(3):276–291 —
  <https://journals.humankinetics.com/view/journals/jab/14/3/article-p276.xml>
- di Prampero (1986), *The Energy Cost of Human Locomotion on Land and in Water*, Int. J. Sports Med. —
  <http://robin.candau.free.fr/di_prampero_1986.pdf> (and "Equation of motion of a cyclist", J. Appl. Physiol. 1979)
- Minetti et al. (2002), *Energy cost of walking and running at extreme uphill and downhill slopes*,
  J. Appl. Physiol. — <https://journals.physiology.org/doi/full/10.1152/japplphysiol.01177.2001>
- Swain (1997), *A model for optimizing cycling performance by varying power on hills and in wind*,
  Med. Sci. Sports Exerc. — <https://pubmed.ncbi.nlm.nih.gov/9268969/>; sportsci.org "Cycling: Uphill
  and Downhill" — <https://sportsci.org/encyc/cyclingupdown/cyclingupdown.html>
- Chung, *Estimating CdA with a power meter* (virtual elevation) —
  <http://anonymous.coward.free.fr/wattage/cda/indirect-cda.pdf>; SILCA explainer —
  <https://silca.cc/blogs/silca/chunging-with-robert-chung>
- Salon et al. (2023), *By cyclists, for cyclists: Road grade and elevation estimation from
  crowd-sourced fitness application data*, PLOS One —
  <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0295027>
- *Evaluating cumulative ascent: Mountain biking meets Mandelbrot* (2010), arXiv:1011.4778 —
  <https://arxiv.org/abs/1011.4778>
- *An Algorithm to Predict E-Bike Power Consumption Based on Planned Routes* (2022), Electronics
  11(7):1105 — <https://www.mdpi.com/2079-9292/11/7/1105>; *Range prediction for electric bicycles*,
  ACM e-Energy 2016 — <https://dl.acm.org/doi/10.1145/2934328.2934349>
- Mesoscopic cycling-trip energy model (2024) —
  <https://www.sciencedirect.com/science/article/pii/S2950105924000214>; *Revealed Preferences for
  Utilitarian Cycling Energy Expenditure versus Travel Time*, Findings —
  <https://findingspress.org/article/120430>
- Best Bike Split (physics route-power planner; "Aero Analyzer" CdA from ride data) —
  <https://www.bestbikesplit.com/case-study-aero-analyzer>
