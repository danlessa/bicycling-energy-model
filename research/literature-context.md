# Research context — where this energy model sits in the literature

How the `bicycling-energy-model` (its two engines, the closed-form law, the ε recovery
factor, `k_smooth`, the DEM/ascent work, and the validation on real rides) relates to the
published research. For each piece this note names the **closest prior art** and labels it
*standard* / *incremental* / *novel (no located precedent)*.

> **Provenance.** Built by the repo's `/deep-research` harness (105 agents, 6 search angles,
> 23 primary sources fetched, 101 claims extracted → **22 of 25 confirmed** by 3-vote
> adversarial verification, 3 refuted). Earlier hand-compiled draft superseded.
> **"Novel" = no precedent found in the *closest* road-cycling-power and elevation-routing
> prior art** — the search did **not** sweep the full transportation, operations-research, or
> sports-physiology literatures, so read it as "no precedent located in the nearest corpus",
> not "provably first".

---

## 1. The map — the literatures and the canonical model in each

| literature | canonical reference(s) | what they establish (verified) |
|---|---|---|
| **Road-cycling power physics** | Martin et al. 1998; di Prampero 1979 | A force balance — aero ½ρCdA·v² + rolling Crr·mg·cosθ + gravity mg·sinθ + inertia + bearing friction, all ÷ drivetrain efficiency — predicts measured power at **R²=0.97, SE=2.7 W**. **But only for *instantaneous power* on 38 steady-velocity trials on a flat (0.3 %) taxiway**; it did *not* validate route energy ∫P·dt and not on hills — the authors flag varied terrain as future work. Re-used essentially unchanged by Dahmen-Saupe 2011, Danek et al. 2020, Bigazzi-Lindsey 2019, Frontiers 2025. |
| **Cycling energetics / physiology** | di Prampero 1979/1986; Minetti 2002 | The force-balance lineage (di Prampero). Minetti is **walking/running on slopes** — useful only as a *conceptual* climb/descend-asymmetry analogy; **do not** parallel ε to eccentric/concentric muscle efficiency (that mechanism is physiological, not the cyclist's gravity/brake budget — see §3). |
| **Energy-/effort-aware bike routing** | Bigazzi-Lindsey 2019; mesoscopic "driving-cycle" models; Valhalla (heuristic) | Per-segment power integrated to a route cost. Bigazzi-Lindsey is the **nearest idle-limit precedent** for ε (below). Valhalla is a *heuristic* `use_hills∈[0,1]` router that costs **time**, penalises downhill ("what goes down must go up"), and explicitly does **not** model true descent recovery — a contrast, not prior art. |
| **E-bike range / route energy** | Gebhard et al., ACM e-Energy 2016 (WeBike) | Static, segment-wise energy over a planned route from DEM + mass + speed **+ a recuperation term** — the e-bike twin of ε. Validated on **real non-racing commuting data** (WeBike fleet + OSM), but the target is **battery range**, not mechanical ∫P·dt. |
| **DEM / road-grade & cumulative ascent** | Rapaport 2011 ("Mountain biking meets Mandelbrot") | Cumulative ascent is **scale-dependent / coastline-paradox-like** — "there is really no correct answer"; fractal exponents D=1.26 (GPS) / 1.18 (barometric). Rapaport even **anticipates the roller-momentum intuition verbatim** ("a small ascent followed by the corresponding descent might go almost unnoticed … due to momentum, but if superimposed on an already significant uphill grade its presence will certainly be felt") — but offers it as a qualitative caveat, with **no deadband and no energy-law formula**. |
| **CdA / Crr field estimation** | Chung "virtual elevation" | Invert the power balance for slope; integrate to a *virtual elevation*; adjust CdA/Crr until it matches the real profile. Energy-balance inversion to recover a hidden parameter. |

Bottom line: **our `canonical()` engine is firmly standard** — the Martin-1998 / di Prampero
force balance, the same one four modern papers reuse unchanged. So the question is only what
our *specific simplifications and analyses* add.

---

## 2. Our contributions, positioned (verified)

### 2a. `canonical()` forward simulation — **standard**
It is the Martin-1998 model. Closest prior art: Martin 1998; Dahmen-Saupe 2011 ("the P-v-model
as adopted from Martin et al., 1998", solved with `ode45`); Danek et al. 2020 (Eq. 2, same
balance, cites Martin); Frontiers 2025 (GA pacing, cites Martin). *Additive only* as a clean
open reference implementation and as the **shared-constants control** for §2c.

### 2b. Closed-form `E ≈ α·x + β·(h₊ − ε·h₋)` and a closed form for ε — **novel (no located precedent)**
- The `α·x + β·h₊` skeleton is the textbook steady-speed *energy integral* (climbing costs `mg·h`
  by conservation; every routing/e-bike model uses it). **Standard.**
  - ⚠️ **Correction (I over-claimed this mid-run).** A draft claim that *Martin 1998 explicitly
    endorses the small-angle simplifications licensing our `β·h₊`* was **refuted 0-3** in final
    synthesis. Martin makes small-angle simplifications **inside his instantaneous-power model**,
    but did **not** publish a route-energy *closed form* `E = α·x + β·(h₊ − ε·h₋)`. So the closed
    form's **provenance is the repo's own derivation**; the underlying physics is universal, the
    *packaging* is not Martin's.
- **The lumped ε∈[0,1] and a closed form for it have no counterpart in the searched corpus.**
  Every nearby paper integrates the equation of motion **numerically** (Runge-Kutta/`ode45`, or
  discretized + GA) and contains **no ε, no recovery factor, no idle-limit derivation**
  (Dahmen-Saupe; Danek; Frontiers 2025 — verified by grep of each).
- **Nearest precedent — cite it: Bigazzi & Lindsey 2019.** Their utility-based speed-choice model
  *does* carry the same **coasting/braking idle limit** we use to derive ε — on a negative grade
  with `v² ≤ μ₁/(−μ₃)` the tractive power is 0 (only baseline metabolic `δ₀`). But they apply it
  to **per-grade steady-state speed choice**, never to a **route-level closed-form
  `ε ≈ clamp(min(1, α/β·s̄) − 0.13)`**. *So the idle-limit idea exists; the closed-form route-level
  ε aggregation, and its validation against power, do not.* → **genuinely additive.**

### 2c. Parameter-shared closed-form-vs-simulation comparison — **incremental (additive framing)**
Dahmen-Saupe 2011 is the methodological cousin: least-squares-calibrate **one** shared model to
isolate *parameter* error. Running **two different engines** (closed form + forward sim) on the
**same** constants to isolate the *modelling-simplification* gap was **not found** in the corpus
(each prior work runs a single model). *Additive framing on a standard idea.*

### 2d. `k_smooth` deadband for *fractal* ascent inside a closed-form law — **novel formalization**
The **problem** is established and now precisely citable: ascent is scale-dependent (Rapaport
2011), and grade error dominates energy error. Rapaport even states the roller-momentum intuition
**in words** — but measures ascent by spatial averaging and **stops short of any deadband or
energy-law formula**. Folding the correction into a *totals-only* scalar `k_smooth = 1 − c·x/h₊`
**inside the closed-form energy law** was **not found** elsewhere. → *additive formalization*; the
scale-dependence and the deadband idea individually are not new.

### 2e. Validation on real **non-racing social / urban** rides reproducing ∫P·dt — **additive**
The cycling-power literature validates **instantaneous speed or power on controlled tracks**
(Martin: flat taxiway; Dahmen-Saupe: speed on rural tracks, *excluding* steep descents/braking) —
**not integrated route energy on uncontrolled rides**. The nearest real-non-racing-data precedent
is **Gebhard 2016** (WeBike e-bikes + OSM), but it predicts **battery range, not mechanical
∫P·dt**. So validating integrated mechanical route energy on social/urban rides — to ~4–7 % median
— is additive. (Read against Martin's R²=0.97 / SE 2.7 W: ours is *looser, but on far harder data*.
Note: the ~4–7 % figure is the repo's self-report, not re-derived by the verifier.)

### 2f. Energy↔time duality (`k₋` mirrors `ε`) — **novel (no located precedent, medium confidence)**
No nearby work ties a *time* coefficient to descent recovery; several drop time entirely
(Dahmen-Saupe: "we eliminate the time"). Bigazzi-Lindsey has time **and** energy but as *separate*
additive utility terms, not a duality. *Additive* — but this is a **negative existence claim** over
the nearest corpus only, so the honest strength is "no precedent located", not "first".

### 2g. The ε / k_DEM inference machinery — **incremental (Chung-adjacent)**
`epsFromFIT` (solve the descent energy balance for ε) and `k_DEM` (fit a per-source ascent
correction) are the **same move as Chung's virtual elevation** — invert an energy identity to
recover a hidden quantity. *Method-standard, target-new.* Cite Chung explicitly.

### 2h. The São Paulo-ε **negative result** — **additive (negative results under-published)**
"Urban stop-go braking suppresses ε" — refuted in our own data (gravity, not the legs, repays the
post-stop re-acceleration on a descent). Documented negative results with a mechanism are exactly
what the applied literature omits.

---

## 3. Corrections & citation flags (from verification)

- **di Prampero:** the **1979** "Equation of motion of a cyclist" is **PMID 468661** (di Prampero,
  Cortili, Mognoni, Saibene, *J. Appl. Physiol.* 47(1):201–6) — the force-balance ancestor. **Do
  not** cite **PMID 7015457**, which is the *1981* "Energetics of muscular exercise" review (a
  different paper that search engines conflate).
- **Martin 1998 quote attribution:** several sources serve the Martin quote under a **Fonda &
  Šarabon 2012 uphill-cycling review** title. Cite **Martin 1998** directly
  (humankinetics / Utah PDF), with the review only as secondary.
- **Do not parallel ε to eccentric/concentric muscle efficiency** (Minetti) — that claim was
  **refuted 1-2** (wrong mechanism). Minetti is a *conceptual* asymmetry analogy only.
- **Do not claim Martin licenses the `β·h₊` closed form** — **refuted 0-3** (see §2b).
- All "novel" calls are **corpus-bounded** (closest road-cycling-power + elevation-routing prior
  art), not a full-literature priority search.

---

## 4. Gaps, opportunities, and what's publishable

- **Most publishable, as a short note:** the **closed-form ε** (§2b) + the **parameter-shared
  comparison** (§2c) + the **∫P·dt-on-social-rides validation** (§2e) — framed against the gap that
  prior validation is *instantaneous power on controlled tracks*. **Cite Bigazzi-Lindsey 2019 as
  the nearest idle-limit precedent** and position ε as the route-level closed-form aggregation they
  did not take. Target: *Findings*, *PLOS One*, or a sports-/transport-engineering venue.
- **Second note:** `k_smooth` / fractal-ascent-in-a-closed-form-law (§2d), next to Rapaport 2011.
- **Open questions surfaced (worth a follow-up search before claiming priority):**
  1. Does any **e-bike-energy or operations-research** paper (outside the road-cycling-power corpus)
     already publish a route-level descent-recovery factor or an energy↔time descent duality?
     The §2b/§2f negatives are bounded by the searched corpus.
  2. Is ~4–7 % median ∫P·dt **competitive** with any *integrated-route-energy* validation? No
     apples-to-apples benchmark was located (Martin is instantaneous power; Gebhard is battery range).
  3. Has a `k_smooth`-style deadband been formalized **inside an energy law** in GPS-track-energy /
     Strava-elevation-correction work, vs. as a profile-averaging operation (Rapaport)?

---

## 5. Related work (drop-in)

> The mechanical-power model of road cycling is well established: a force balance over gravity,
> aerodynamic drag, rolling resistance, bearing friction and inertia predicts measured power to a
> few watts [Martin et al. 1998; di Prampero et al. 1979], and is reused essentially unchanged in
> recent work [Dahmen & Saupe 2011; Danek et al. 2020; Bigazzi & Lindsey 2019]. That validation,
> however, is of *instantaneous power on controlled, near-flat trials*, not of integrated route
> energy on uncontrolled rides. Estimating route energy from elevation is standard in energy-aware
> bicycle routing and in e-bike range models, the latter carrying an explicit recuperation term
> analogous to our descent-recovery factor ε [Gebhard et al. 2016]; the closest precedent for ε's
> idle/coasting limit is the negative-grade boundary of Bigazzi & Lindsey [2019], though they apply
> it to per-grade speed choice rather than a route-level closed form. Two measurement realities
> shape any such estimate: grade error dominates the energy error, and cumulative ascent is
> scale-dependent — there is no single true elevation gain, only a value at a chosen smoothing scale
> [Rapaport 2011]. Our descent-balance and per-DEM-source fits follow the energy-balance inversion
> of Chung's "virtual elevation" method. Against this backdrop the project contributes a closed form
> for ε with a coasting-limit derivation and power-validated calibration, a totals-only `k_smooth`
> correction for fractal ascent, a parameter-shared closed-form-vs-simulation comparison, and
> validation on non-racing social and urban rides — none of which were located in the nearest prior
> art.

---

## Sources (verified, primary unless noted)

- **Martin, Milliken, Cobb, McFadden, Coggan (1998)**, *Validation of a Mathematical Model for Road
  Cycling Power*, J. Appl. Biomech. 14(3):276–291 (R²=0.97, SE 2.7 W) —
  <https://journals.humankinetics.com/view/journals/jab/14/3/article-p276.xml> ·
  <https://collections.lib.utah.edu/dl_files/b4/8e/b48ef26086091662c561e673d7bd990d77868437.pdf>
- **di Prampero, Cortili, Mognoni, Saibene (1979)**, *Equation of motion of a cyclist*, J. Appl.
  Physiol. 47(1):201–6 — PMID **468661** (NOT 7015457). 1986 energy-cost review —
  <http://robin.candau.free.fr/di_prampero_1986.pdf>
- **Dahmen & Saupe (2011)**, *Validation of a Model and a Simulator for Road Cycling on Real Tracks*
  — <https://www.uni-konstanz.de/mmsp/pubsys/publishedFiles/DaSa11.pdf>
- **Danek et al. (2020)**, cyclist power-balance parameter estimation — <https://arxiv.org/pdf/2005.04229>
- **Bigazzi & Lindsey (2019)**, *A utility-based bicycle speed choice model with time and energy
  factors*, Transportation 46:995–1009 —
  <https://civil-reactlab.sites.olt.ubc.ca/files/2022/11/Bigazzi_2019_A-utility-based-bicycle-speed-choice-model-with-time-and-energy-factors.pdf>
- **Minetti et al. (2002)**, *Energy cost of walking and running at extreme uphill and downhill
  slopes*, J. Appl. Physiol. 93(3):1039–46 —
  <https://journals.physiology.org/doi/full/10.1152/japplphysiol.01177.2001> (conceptual analogy only)
- **Rapaport (2011)**, *Evaluating cumulative ascent: Mountain biking meets Mandelbrot*, Int. J. Mod.
  Phys. C 22(3):209–217 — <https://arxiv.org/abs/1011.4778>
- **Gebhard et al. (2016)**, *Range prediction for electric bicycles*, ACM e-Energy (WeBike) —
  <https://dl.acm.org/doi/10.1145/2934328.2934349>; e-bike route energy, Electronics 11(7):1105 —
  <https://www.mdpi.com/2079-9292/11/7/1105>
- **Chung**, *Estimating CdA with a power meter* (virtual elevation) —
  <http://anonymous.coward.free.fr/wattage/cda/indirect-cda.pdf>
- **Valhalla** elevation costing (heuristic `use_hills`, contrast not prior art) —
  <https://valhalla.github.io/valhalla/sif/elevation_costing/>
- **Frontiers (2025)**, GA pacing optimization on a Martin-1998 power model —
  <https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2025.1683815/full>
