<!-- DRAFT v2 — IMRAD paper, revised after the six-lens adversarial review
     (2026-07-27) and the author's preliminary feedback. Single-language draft
     for review; the pt-BR mirror is produced only after this shape is approved
     (from then on the lockstep rule applies). Sources of truth:
     research/journal/MODEL_COMPARISON_JOURNAL.md (numbers), journal.qmd
     (reproduction map). All values are the current, re-baselined ones
     (G = 9.7864), verified against src/harness/bootstrap_ci.py and the
     harness CSVs. Math in LaTeX ($...$); render target is pandoc/KaTeX. Figures 3-4 are
     mermaid blocks: the publish pipeline must render them (mermaid.js via
     CDN+SRI in the /modelo/ template, or pre-render at build); GitHub
     renders them natively. -->

# A Closed-Form Model for the Mechanical Energy of Cycling a Route, Tested on 1,285 Power-Meter Rides

**Danilo Lessa Bernardineli** — Pedal Hidrográfico, São Paulo

## Abstract

**Background.** The energy of cycling a route has three parts: a cost per kilometre of distance, a cost per metre climbed, and a partial refund per metre descended. Yet the quantity is hard to obtain: route planners optimise time, not energy; the tools that estimate it are simulation-based, with route-level accuracy unpublished; the physics literature validates instantaneous power or speed, never the route-level integral. A closed form simple enough for pen and paper — or a million edge evaluations per second in a router — would unlock it, if it can be trusted.

**Methods.** We test four models built on one three-term closed form, $E \approx \alpha\,x + \beta\,(h_+ - \varepsilon\,h_-)$ — flat cost rate $\alpha$, climbing rate $\beta$, refunded fraction $\varepsilon$ of the descent $h_-$ — against the power-meter energy $\int P\,dt$ of 1,285 unique rides (1,387 evaluations; five overlapping corpora, three riders, São Paulo; the urban corpus re-evaluates the author's recordings as a generic rider). The reference is a forward-dynamics simulation [Martin et al. 1998] run on the same constants per ride, so gaps are modelling error; each ride's measured power feeds both engines, so accuracy means consistency of the energy accounting, not blind prediction. The calibration corpus uses condition-informed per-ride parameters (logged mass; judged $C_{rr}$, $C_dA$, air density, wind, $\varepsilon$) and is re-run blind as a check; every other corpus is blind under one shared literature-typical set, with mass the only per-rider input. All behavioural constants are calibrated once and frozen.

**Results.** With informed parameters the four models err by 3.5% [95% CI 2.0, 5.6] (form 3, elevation smoothed), 5.9% [3.6, 8.3] (form 4, elevation corrected), 8.6% (form 2, split) and 19.1% (form 1, original) median, the simulation by 5.2% [3.8, 7.3]; two corrections carry the gain — no longer charging climb aerodynamics at the flat reference speed, and no longer counting sub-metre elevation noise as climbing — and the best form is statistically indistinguishable from the simulation ($p = 0.65$, $n = 44$; equivalence not formally tested). Blind, the corrected forms cluster at 7.6–8.2% versus the simulation's 8.4% ($p = 1.00$): parity is protocol-independent, and the ≈ 3–5-point shift on the corrected-form/simulation pair prices condition knowledge (an in-sample upper bound). For the descent term we derive the coasting limit $\varepsilon(s) = \min(1, (\alpha/\beta)/s)$, $s$ the descent grade, and calibrate the **coasting deficit** — the refund share riders never collect — at $\varepsilon_0 = 0.13$ *under the shared priors and sampling scale* (the measured gap spans 0.12–0.19 across plausible physics). Frozen, the law pools to **5.6% [5.2, 6.2] over the two independent riders' 660 rides** against the simulation's 6.3% [5.8, 6.8] (5.9% vs 6.2% adding the author's in-sample history, n = 1,281; 3.5–6.2% per corpus on those corpora, 6.4–7.7% on the urban regime test), and the deficit recurs on every rider (gaps 0.12–0.19 across assumed and fitted physics).

**Conclusions.** The proposed form 3, $E = \alpha_r\,x + \alpha_a\,x_{\mathrm{flat}} + \beta\,(\tilde h_+ - \varepsilon\,\tilde h_-)$ — air resistance only off the climbs, smoothed totals $\tilde h_\pm$ — matches the simulation under both protocols (pooled over the independent riders: 5.6% vs 6.3%); form 4, its totals-only approximation (subtract $c \approx 3$ m of phantom climb per kilometre), performs nearly as well and is computable by hand from distance, ascent, descent and a rough climbing share. Descent recovery has a geometry (the coasting limit) and a habit (the deficit): the deficit transfers across riders, while the dynamic term's edge over a flat constant is rider- and parameter-dependent — flat $\varepsilon \approx 0.20$ suffices in urban riding. The law is cheap enough to serve as a per-edge routing cost at the sampling scale it was calibrated on.

## Terminology

<a id="terminology"></a>

Symbols used throughout; grades are percent in the text, fractions in formulas; "—" in the unit column marks dimensionless quantities; corpus labels D1–D5 are defined in [Table 1](#tab1). The four physical constants below carry their frozen-protocol values; the informed calibration run judged them per ride ([§2.3](#2.3)). The *value* column gives the constant used, or the variable's scope: **rider** (fixed per rider), **route** (from route geometry), **ride** (per recorded ride), **local** (along the route), **instant** (per second).

| symbol | unit | value | name | meaning |
|---|---|---|---|---|
| $E$ | J | ride | route mechanical energy | Pedal energy over the route; ground truth is the power-meter integral $\int P\,dt$. |
| $x$ | m | route | route distance | Ground distance. |
| $h_+$, $h_-$ | m | route | total ascent, descent | Summed climbing / dropping, raw profile; deadband-smoothed totals are $\tilde h_+$, $\tilde h_-$ ([§1.2](#1.2)). |
| $x_+$, $x_-$, $x_{\mathrm{flat}}$ | m | route | climbing, descending, non-climbing distance | Distance on grades ≥ 2%, descending distance, and $x - x_+$; aero is charged only on $x_{\mathrm{flat}}$. |
| $s$ | — | local | grade (slope) | Rise over run (2% in text ≡ 0.02 in formulas); negative on descents in the regime definitions, magnitude in descent formulas ($\bar s = h_-/x_-$). |
| $m$ | kg | rider | total system mass | Rider + bicycle + gear; logged (D1), generic 78 kg (D2), or inverted from climbing data (D3–D5) ([§2.3](#2.3)). |
| $g$ | m/s² | 9.7864 | local gravity | São Paulo's measured value (IAG-USP). |
| $C_{rr}$ | — | 0.008 | rolling-resistance coefficient | Rolling drag as a fraction of weight. |
| $C_dA$ | m² | 0.40 | drag area | Frontal area × drag coefficient. |
| $\rho$ | kg/m³ | 1.13 | air density | At São Paulo's altitude. |
| $k_{\mathrm{eff}}$ | — | 0.98 | drivetrain efficiency | Fraction of leg power reaching the wheel. |
| $w$ | m/s | 0 | headwind | Zero in every frozen run; the informed D1 run judged it per ride. |
| $v_f$ | m/s | ride | flat reference speed | Flat cruising speed, derived per ride from its own flat-regime power ([§2.1](#2.1)); sets the aero charge, anchors the two models. |
| $P$ | W | instant | pedal power | Measured per second by the power meter. |
| $\alpha_r$, $\alpha_a$ | J/m | rider, ride | rolling, aero cost rates | Energy per metre for rolling, and for air at the relative speed $v_f + w$ (so $\alpha_a$ inherits $v_f$'s per-ride scope); $\alpha = \alpha_r + \alpha_a$. |
| $\beta$ | J/m | rider | climbing cost rate | Energy per metre climbed: $mg/k_{\mathrm{eff}}$. |
| $s_*$; $s_+$, $s_-$ | — | rider | flat-resistance grade; gravity-dominated regimes | Break-even slope $s_* = \alpha/\beta$ (≈ 1.6–2%); beyond it gravity dominates — ascents $s_+$ collapse speed, descents $s_-$ shed the surplus gravitational power to over-speed drag or braking. |
| $s_=$ | — | — | flat band | $\lvert s\rvert < s_*$: resistance dominates, aero at $v_f$ is fair, descents refund fully; the 2% gate approximates its edge. |
| $\varepsilon$ | — | route | descent-recovery factor | Fraction of descent potential energy refunded; measured values can be negative (Appendix A). |
| $\varepsilon_d$ | — | route | dynamic $\varepsilon$ | $\varepsilon_{\mathrm{coast}} - \varepsilon_0$ (unclamped; positive on every ride measured) — adapts to descent geometry ([§1.3](#1.3)). |
| $\varepsilon_f$ | — | 0.20 | flat $\varepsilon$ | One constant for every route; selected on D2, frozen. |
| $\varepsilon_{\mathrm{coast}}$ | — | route | coasting-limit recovery | Geometry-only ideal $\min(1, s_*/s)$, drop-weighted; needs no power data. |
| $\varepsilon_{\mathrm{bal}}$ | — | ride | measured descent balance | What a ride actually recovered: one ride-level quotient over its descent cells (30 m grid), from its own power stream ([§2.2](#2.2)). |
| $\varepsilon_0$ | — | 0.13 | coasting deficit | Gap between ideal and measured recovery; 0.13 at the shared priors and 30 m scale (0.12–0.19 across plausible physics, [§3.4](#3.4)); recurrence robust, value conditional. |
| $c$ | m/km | ≈ 3 | ascent-noise rate | Phantom climb per route-km, subtracted from raw totals; measured ([§2.4](#2.4)), frozen. |
| $\tau$ | m | 2 | deadband threshold | Elevation changes below $\tau$ are ignored when summing $h_\pm$. |
| $\Delta\%$ | % | ride | per-ride signed error | $(E_{\mathrm{model}} - E_{\mathrm{meas}})/E_{\mathrm{meas}}$; corpora summarized by medians of $\Delta\%$, $\lvert\Delta\%\rvert$. |

## 1. Introduction

<a id="1.1"></a>

### 1.1 An absent quantity

How much energy does it take to cycle a route? The question is basic — it determines how far a commuter can ride, how a collective plans a group ride through hilly terrain, whether a cargo-bike delivery round is feasible — and yet a trustworthy answer is hard to come by. Mainstream bicycle routers cost *time*, with heuristic hill penalties — none costs energy per edge (our own experimental deployment, [§4.1](#4.1), is the exception that motivated this study). The tools that do estimate ride energy are simulation-based pacing planners or platforms' post-hoc estimates: opaque to their users and, to our knowledge, never validated against measured route-level power in the open literature. The sports-science literature validates the *instantaneous* power balance to high precision [Martin et al. 1998; Dahmen et al. 2011] but not the route-level energy integral; route-choice models absorb elevation into fitted coefficients with no physical form [Scarf & Grehan 2005]. Energy is not so much absent from the toolbox as locked inside simulations — out of reach of a router that must cost thousands of edges, and of a rider with pen and paper.

Two audiences would use it if it were computable, and they impose opposite constraints. A routing engine must evaluate thousands of candidate edges, which rules out forward simulation and demands a closed form. A rider — or anyone teaching riders — needs something even stricter: a formula that works with pen and paper, from the three numbers any map already gives (distance, total ascent, total descent). Both constraints point to the same object, and Occam points there too: the simplest law that survives contact with measured data is the one worth deploying.

<a id="1.2"></a>

### 1.2 The proposed law

We propose an approximation that decomposes the mechanical work of a ride into three terms: (1) a cost per metre of horizontal distance — rolling and aerodynamic resistance — expressed by the rate $\alpha$; (2) a cost per metre of ascent — a gravitational *deposit* — expressed by the rate $\beta$; and (3) a partial *refund* per metre of descent — the deposit withdrawn back as forward progress — expressed by the recovery factor $\varepsilon$. Terms 1 and 2 are widely known: together they are the textbook steady-speed energy integral, resting on physics validated since the equation-of-motion experiments [di Prampero et al. 1979; Martin et al. 1998]. Term 3 is novel. It has been touched only obliquely in nearby literatures — as a per-grade coasting idle limit in a speed-choice model [Bigazzi & Lindsey 2019], and as per-instant regeneration efficiencies or symmetric potential terms in electric-vehicle energy models — but never as a route-level, closed-form recovery factor; [§1.3](#1.3) develops it and [§4.2](#4.2) maps the prior art. The three terms give the shape every form in this study shares,

$$E \;\approx\; \alpha\,x \;+\; \beta\,(h_+ - \varepsilon\,h_-),$$

with one flat cost rate $\alpha = \alpha_r + \alpha_a$, one climbing rate $\beta$ and one recovery factor $\varepsilon$, where

$$\alpha_r = \frac{C_{rr}\,m g}{k_{\mathrm{eff}}}, \qquad \alpha_a = \frac{\tfrac{1}{2}\rho\,C_dA\,(v_f + w)^2}{k_{\mathrm{eff}}}, \qquad \beta = \frac{m g}{k_{\mathrm{eff}}},$$

with $w$ the headwind, zero throughout the frozen protocol (so $\alpha_a$ reduces to the $v_f^2$ form there) and judged per ride in the informed calibration run ([§2.3](#2.3)).

We evaluate four forms of this family. They are not independent alternatives but a causal chain of refinements, each step addressing the previous form's main limitation: form 1, the shared shape as-is, led to form 2 (splitting the flat rate), which led to form 3 (smoothing the elevation), which led to form 4 (approximating the smoothing when only totals are available). Writing $\tilde h_\pm$ for the deadband-smoothed elevation totals:

1. **original** — air resistance at the flat reference speed over the whole distance; raw elevation totals:
   $$E_1 \;\approx\; \alpha\,x \;+\; \beta\,(h_+ - \varepsilon\,h_-);$$
2. **split** — the aero part gated off climbs, rolling still paid everywhere:
   $$E_2 \;\approx\; \alpha_r\,x \;+\; \alpha_a\,x_{\mathrm{flat}} \;+\; \beta\,(h_+ - \varepsilon\,h_-);$$
3. **split + elevation smoothed** — the elevation profile deadband-filtered point by point before summing, so $\tilde h_\pm$ are noise-free (the form we propose):
   $$E_3 \;\approx\; \alpha_r\,x \;+\; \alpha_a\,x_{\mathrm{flat}} \;+\; \beta\,(\tilde h_+ - \varepsilon\,\tilde h_-);$$
4. **split + elevation correction** — form 3, with the smoothed totals approximated from the raw ones, for when only $x$, $h_+$ and $h_-$ are known:
   $$E_4 \;\approx\; \alpha_r\,x \;+\; \alpha_a\,x_{\mathrm{flat}} \;+\; \beta\,(\tilde h_+ - \varepsilon\,\tilde h_-), \qquad \tilde h_\pm \approx h_\pm - c\,x.$$

All four forms are derived from the route-energy integral in [Appendix A](#appendix-a), and all four are scored against measured energy in [§3.1](#3.1) ([Table 2](#tab2)). All symbols and their plain-word meanings are collected in [Terminology](#terminology); [Figure 1](#fig1) maps each term of the proposed form onto a route profile; the filter threshold $\tau$ and the noise rate $c$ are specified below.

<a id="fig1"></a>

![**Figure 1.** The law mapped onto a route profile: rolling and air resistance are paid over distance (blue), climbs charge the full gravity premium with aero gated off (vermilion), descents refund the fraction $\varepsilon$ (green). Inset: sub-metre elevation noise inflates $h_+$ unless filtered.](figs/fig9-anatomy.svg)

The family's physical ingredients are well validated, but only below the route scale: the underlying power balance against steady-velocity trials on flat ground [Martin et al. 1998], and simulators built on it against speed on real tracks [Dahmen et al. 2011] — never against the route-level energy integral. Two systematic errors that only exist at that integral scale — one born when the closed form lumps aero into a single reference speed, one born when noisy elevation steps are summed into $h_+$ — therefore had no occasion to be noticed, let alone corrected. We propose two corrections; both are calibrated on a single corpus and then frozen ([§2.3](#2.3)).

- **Climb-aero split.** The original form bills air resistance at $v_f$ over the whole distance, but on ascent-dominated grades ($s_+$) speed falls far below $v_f$, so it over-charges every climb. The correction charges aero only over the non-climbing distance $x_{\mathrm{flat}} = x - x_+$; the frozen 2% gate defining $x_+$ is a rounded, rider-generic stand-in for the flat-resistance grade $s_*$.
- **Elevation deadband.** Recorded and DEM (digital elevation model — terrain heights from mapping data) elevation profiles carry sub-metre noise whose positive half-steps all count toward $h_+$ — a measurement artifact, not lifting work [Rapaport 2011]. Form 3 removes it with a backlash (deadband) filter of threshold $\tau = 2\,\mathrm{m}$, which leaves sustained climbs intact; form 4 approximates the smoothed totals from raw ones, $\tilde h_\pm \approx h_\pm - c\,x$, achieving the same on totals alone — **subtract about 3 m of phantom climbing per kilometre of route** ($c = 0.003$ with $x$ and $h_\pm$ in metres; the rate is measured on the calibration corpus at 3.1 m/km median, per-ride IQR (interquartile range) 2.6–3.7 — methodology in [§2.4](#2.4), evidence in [§3.1](#3.1)). Example: a 50 km ride whose raw profile reports 600 m of ascent is corrected to $600 - 3 \times 50 = 450$ m.

<a id="1.3"></a>

### 1.3 The descent term: a coasting limit and a coasting deficit

The refund is the term prior knowledge leaves least determined — and the one with the most to offer, because it turns a difficult phenomenon (what a rider actually does downhill) into something measurable and transferable. The question it answers: when a route descends $h_-$ metres, how much of the potential energy $m g h_-$ returns as forward progress rather than being lost to over-speed drag and braking? Published models either ignore descents, treat them symmetrically with climbs, or handle recovery per-instant, as the electric-vehicle literature does [Yuan et al. 2024; Ahmadi et al. 2024; Perger & Auer 2020]. We could locate no closed-form, route-level descent-recovery term validated against measured power.

We derive one in [Appendix A](#appendix-a) as the exact upper bound of recovery — the coasting limit (no pedalling), since the legs can never return energy: a descent of grade $s$ recovers the fraction of its potential energy not consumed by rolling and flat-reference air resistance,

$$\varepsilon_{\mathrm{coast}}(s) = \min\!\left(1,\ \frac{\alpha/\beta}{s}\right).$$

This is the descent-side mirror of the climb gate: within the flat band ($s_=$) every joule of drop offsets resistance one-for-one and the refund is total; on descent-dominated grades ($s_-$) the surplus must be dumped to over-speed drag or brakes, so the recoverable fraction decays as $1/s$ ([Figure 2](#fig2)). The same idle limit appears, per grade, in Bigazzi & Lindsey's utility-based speed-choice model [Bigazzi & Lindsey 2019]; here it is lifted to a route level — aggregating drop-weighted over a route's descent profile gives a geometry-only estimate $\varepsilon_{\mathrm{coast}}$ that needs no power data.

<a id="fig2"></a>

![**Figure 2.** The coasting-limit curve $\varepsilon_{\mathrm{coast}}(s)$ (blue), breaking at the flat-resistance grade $s_* = \alpha/\beta$ (drawn at 2%, a typical value): within the flat band ($s_=$) every descent refunds everything (clamp at 1); on descent-dominated grades ($s_-$) the refund decays as $1/s$. Real riders (dashed) track the same curve one coasting deficit $\varepsilon_0 = 0.13$ below it.](figs/fig10-coasting-deficit.svg)

Real riders do not ride the coasting limit: they pedal into descents, so their measured recovery sits below the bound by construction. (Braking, counter-intuitively, cancels out of the measured balance — it dissipates gravity's share of the ledger, never the legs' — so the shortfall is carried by descent pedalling, with braking acting only indirectly through the re-pedalling it forces; [Appendix A](#appendix-a).) Our hypothesis is that this shortfall is a constant offset — the **coasting deficit** $\varepsilon_0$ — so that the working estimator is

$$\varepsilon \;\approx\; \varepsilon_{\mathrm{coast}} - \varepsilon_0,$$

with $\varepsilon_0$ calibrated once against power-measured descent balances ([§2.2](#2.2), [§3.2](#3.2)) and then frozen. We call this estimator the **dynamic $\varepsilon$**, written $\varepsilon_d$ — it adapts to each route's descent geometry — in contrast to a **flat $\varepsilon$**, written $\varepsilon_f$: a single constant for every route, the alternative it is scored against throughout. The estimator is deliberately *unclamped*: it lives in $[-\varepsilon_0,\, 1-\varepsilon_0]$ by construction ($0 \leq \varepsilon_{\mathrm{coast}} \leq 1$), and a negative prediction — possible only on mean descent grades beyond $s_*/\varepsilon_0 \approx 15\%$, steeper than anything in the corpora — is not unphysical either, since measured recovery *can* go negative (a rider who pedals a descent harder than the flat bill). On the 1,300-odd rides where the estimator is defined it never left $(0, 1)$; [Appendix A](#appendix-a) states the exact bounds, and a proposed refinement that *fades* the deficit on steep grades — removing the negative region by mechanism — is registered in [§4.4](#4.4). What the deficit *is* — geometry or habit — and whether it transfers across riders are empirical questions, answered in [§3.2](#3.2)–[§3.3](#3.3).

<a id="1.4"></a>

### 1.4 Aim, hypotheses, and scope

**The aim of this study** is to test whether the closed form above accounts for the measured mechanical energy of real rides as well as a full simulation does. Three hypotheses, each tested against measured power:

1. **Attribution.** The closed form's error is not diffuse: the two corrected mechanisms — the climb-aero over-charge and ascent noise — account for almost all of it, and the corrected law reaches statistical parity with the forward simulation it approximates ([§3.1](#3.1)).
2. **Calibration.** On genuine descents (mean descent grade ≥ 3%), the gap between the coasting ideal and riders' measured descent balances is a single constant, not a function of the route ([§3.2](#3.2)).
3. **Transfer.** Calibrated on one rider and frozen, the energy law and the coasting deficit carry to independent riders' complete histories; whether the dynamic estimator's ($\varepsilon_d$) extra accuracy over a single flat constant also carries is part of the test ([§3.3](#3.3)).

One scope statement applies throughout: each ride is evaluated with its own measured power inputs, and mass is the one per-rider input — logged on the calibration corpus, implied from each independent rider's own climbing data, generic on the urban corpus ([§2.3](#2.3)). Our accuracy figures therefore measure the **consistency of the energy accounting** — whether the law maps a route's geometry and a rider's effort onto the measured energy — not blind route prediction, which would additionally require predicting the rider's power.

## 2. Methods

[Figure 3](#fig3) maps the whole study in one view — the inputs, the per-ride pipeline, and the outputs; the subsections detail each stage, and [Figure 4](#fig4) (in [§2.3](#2.3)) shows how the corpora relate.

<a id="fig3"></a>

**Figure 3.** The study pipeline: inputs, the per-ride pipeline, and outputs. Every arrow is one deterministic harness step; all outputs regenerate from the inputs with one command per corpus.

```mermaid
flowchart LR
  subgraph IN["inputs"]
    A["FIT recordings
    1,285 rides: power P(t), speed,
    barometric elevation (§2.4)"]
    B["physical parameters
    informed per-ride (D1) / frozen priors
    (D1 re-run, D2–D5); mass logged /
    inverted / generic (§2.3)"]
    C["behavioural constants
    ε₀ = 0.13 · c ≈ 3 m/km · ε_f = 0.20
    calibrated once, then frozen (§2.3)"]
  end
  subgraph PIPE["per-ride pipeline"]
    P1["1 · parse
    FIT → per-second points"]
    P2["2 · geometry
    resample 5 m · deadband τ = 2 m →
    x, x_flat, h±, h̃±, 30 m descent cells"]
    P3["3 · per-ride rates
    regime powers → v_f (flat balance);
    mass by corpus protocol"]
    P4["4 · evaluate five engines
    forms 1–4 + forward simulation
    → predicted E"]
    P5["5 · measure
    E_meas = ∫P·dt;
    ε_bal from descent cells (§2.2)"]
    P1 --> P2 --> P3 --> P4 --> P5
  end
  subgraph OUT["outputs"]
    O1["accuracy
    per-ride Δ% → medians, 95% CIs,
    paired sign tests; the gate battery
    re-derives every published number"]
    O2["descent recovery
    ε_coast vs ε_bal → the coasting
    deficit and its transfer (§3.2–3.3)"]
    O3["robustness maps
    fitted physics · mass sweep ·
    CdA × Crr × ρ sensitivity (§3.4)"]
  end
  A --> P1
  B --> P3
  B --> P4
  C --> P4
  P4 --> O1
  P5 --> O1
  P5 --> O2
  P4 --> O3
  classDef blue stroke:#0072B2,fill:#fff,color:#222
  classDef verm stroke:#D55E00,fill:#fff,color:#222
  classDef green stroke:#009E73,fill:#fff,color:#222
  classDef ink stroke:#222222,fill:#fff,color:#222
  class A,O1 blue
  class B,O3 verm
  class C,O2 green
  class P1,P2,P3,P4,P5 ink
```

<a id="2.1"></a>

### 2.1 The reference simulation and the shared-constants design

The reference is a distance-marching forward integration of the standard cycling power balance [Martin et al. 1998; di Prampero et al. 1979]:

$$m\,\frac{dv}{ds}\,v = \frac{k_{\mathrm{eff}}\,P}{v} - C_{rr}\,m g \cos\theta - \tfrac{1}{2}\rho\,C_dA\,(v + w)^2 - m g \sin\theta,$$

with pedal power $P$ per grade regime extracted from each ride's own power stream, signed relative wind $w$, and a safe-speed brake cap on descents. The integrator uses a semi-implicit kinetic-energy update that conserves energy to machine precision (the identity $k_{\mathrm{eff}} E_{\mathrm{legs}} = \Delta KE + W_{rr} + W_{\mathrm{aero}} + W_{\mathrm{grav}} + W_{\mathrm{brake}}$ is asserted per ride to $\leq 10^{-6}$ relative).

The design principle that makes the comparison meaningful: **both models read the same physical constants** — mass, $C_{rr}$, $C_dA$, $\rho$, $k_{\mathrm{eff}}$, and the headwind $w$ (held at zero throughout the frozen protocol) — per ride. The flat reference speed is likewise shared and derived per ride: the flat-regime pedal power is extracted from the ride's own power stream (speed-gated, time-weighted), and $v_f$ is the speed at which the flat power balance closes — so on flat ground the two models agree by construction, and every gap between them is modelling error, not a parameter mismatch. Gravity is São Paulo's measured local value ([Terminology](#terminology)); all corpora were ridden in the São Paulo metropolitan region.

<a id="2.2"></a>

### 2.2 Measuring descent recovery

To measure what a rider actually recovers on descents — the quantity the [§1.3](#1.3) hypothesis is calibrated against — we solve the descent energy balance for each ride ([Appendix A](#appendix-a) derives this quantity and its bounds):

$$\varepsilon_{\mathrm{bal}} = \frac{\alpha\,x_- - E_{\mathrm{legs},-}}{\beta\,h_-},$$

where $x_-$ is the route's descending distance (the descent-side sibling of $x_+$), $E_{\mathrm{legs},-}$ is the pedal energy $\int P\,dt$ spent while descending, and the balance is a single ride-level aggregate over descent cells identified on a 30 m grid, with $\alpha$ computed at each ride's *measured* flat speed (deliberately — using the model's reference speed here would let a parameter mismatch masquerade as recovery). This inversion of an energy identity to expose a hidden quantity follows the logic of Chung's virtual-elevation method [Chung 2012]. The coasting deficit is then the measured offset $\varepsilon_{\mathrm{coast}} - \varepsilon_{\mathrm{bal}}$, calibrated on one corpus and tested for constancy and transfer in [§3.2](#3.2)–[§3.3](#3.3).

<a id="2.3"></a>

### 2.3 Data, ground truth, and evaluation protocol

**Datasets.** Five corpora — 1,285 unique rides, 1,387 ride-evaluations (D1 ⊂ D5, and 58 of D2's 62 rides are the author's recordings also in D5, re-evaluated as a generic rider) — all ridden in and around São Paulo, all with per-second power meters ([Table 1](#tab1); [Figure 5](#fig5) draws every analysed route on one map).

<a id="tab1"></a>

**Table 1.** The five corpora and their roles.

| corpus | rides (clean) | character | role |
|---|--:|---|---|
| D1 longões | 44 | long brevet-style rides, open terrain (author) | calibration + primary comparison |
| D2 censo | 62 | urban stop-go group rides, generic rider assumed | out-of-domain regime test |
| D3 P. Paz | 441 | independent rider's full history, fast open-road | frozen-constant transfer |
| D4 JAAM | 219 | independent rider's full history, gentle terrain, strong descent-pedaller | frozen-constant transfer |
| D5 author-full | 621 | author's complete history (superset of D1) | large-sample in-sample validation |

The roles, precisely:

- **calibration** — the corpus where nearly everything tunable is tuned: $\varepsilon_0$, $c$ and the correction variants are fixed here, once ($\varepsilon_f$ is the exception, selected on D2), and frozen thereafter;
- **primary comparison** — the closed-form-vs-simulation contest of [§3.1](#3.1); because it shares the calibration corpus, it can support only parity-where-derived — which is what the next three roles exist to extend;
- **out-of-domain regime test** — the riding context changes (urban stop-go, fully generic assumed rider) while every constant stays frozen: does the law break when the *style of riding* changes?
- **frozen-constant transfer** — the *rider* changes: two independent full histories, constants frozen, only mass data-implied. The strongest out-of-sample evidence here: did calibration capture cycling, or just the calibration rider?
- **large-sample in-sample validation** — deliberately *not* independent (the calibration rider's complete history): it validates the machinery at scale — mass inversion against a known weight, the filters, the parser — not the law.

The design in one line: **fit → contest → change the regime → change the rider → stress the machinery**, each step removing one alternative explanation for the previous step's success ([Figure 4](#fig4)).

<a id="fig4"></a>

**Figure 4.** The study design: $\varepsilon_0$, $c$ and the form choice are calibrated on D1 ($\varepsilon_f$ is selected on D2) and all are frozen; the frozen model is then carried to a different riding regime, two different riders, and the calibration rider's full history at scale, and back to the same 44 rides as the blind coherence check (the informed-parameter primary comparison of Table 2's upper block sits *outside* the frozen chain). Throughout, each ride's own measured power and the shared constants feed both engines, scored as $\Delta\%$ against the measured $\int P\,dt$.

```mermaid
flowchart LR
  D1c["D1 · longões
  44 rides · author
  open, brevet-style terrain"] --> PRIM["primary comparison
  informed per-ride parameters:
  law vs simulation (§3.1, Table 2 upper)"]
  D1c --> CAL["calibrate
  ε₀ = 0.13 · c ≈ 3 m/km
  choose forms 3–4"]
  CAL --> FR{{"FROZEN
  + ε_f = 0.20 from D2"}}
  FR --> T1["D1 · same 44 rides
  blind coherence check
  (§3.1, Table 2 lower)"]
  FR --> T2["D2 · censo · 62
  regime test: urban stop-go,
  fully generic rider (§3.1–3.2)"]
  FR --> T3["D3 · 441 + D4 · 219
  rider transfer: independent full
  histories, only mass implied (§3.3)"]
  FR --> T4["D5 · author-full · 621
  machinery at scale: in-sample,
  validates instruments (§3.4)"]
  classDef blue stroke:#0072B2,fill:#fff,color:#222
  classDef verm stroke:#D55E00,fill:#fff,color:#222
  classDef green stroke:#009E73,fill:#fff,color:#222
  classDef grey stroke:#9aa0a6,fill:#fff,color:#222
  classDef ink stroke:#222222,fill:#fff,color:#222,font-weight:bold
  class D1c,T1 blue
  class PRIM verm
  class CAL blue
  class T2 green
  class T3 verm
  class T4 grey
  class FR ink
```

<a id="fig5"></a>

![**Figure 5.** Every analysed ride on one map: the censo's urban knot (green), JAAM's Vale do Paraíba corridor (blue), P. Paz's western open roads (vermilion), and the author's brevets radiating to the coast and mountains (grey). No basemap — the visible geography is the rides themselves. For privacy, the first and last 1.5 km of every ride are not drawn; legend counts are the rides drawn, which differ from [Table 1](#tab1)'s clean corpora in both directions — rides the analysis excluded may be drawn, and analysed rides without enough usable GPS after the trim are not.](figs/fig12-routes-map.png)

Ground truth is the raw $\int P\,dt$ per ride, coasting zeros included. Inclusion filters, applied identically everywhere:

- sport = cycling; virtual rides excluded via the FIT manufacturer field;
- power coverage > 50% of samples; altitude coverage ≥ 99%;
- distance ≥ 20 km (D1 and D3–D5; the censo corpus is the collective's curated census roster, which includes three shorter rides);
- a physical floor: $E_{\mathrm{legs}} \geq m g\,\tilde h_+/k_{\mathrm{eff}}$ — a measured energy below the climbing potential energy means the route was not fully pedalled (power dropouts, walking) — with a cadence-based cross-check for walked segments.

The independent riders' exports were shared with consent and are never published; all analysis code and output schemas are public.

**The two parameter protocols.** The calibration corpus is evaluated with *condition-informed per-ride parameters* — literature-anchored values adjusted by the author's judgment of each ride's conditions. Six of the seven fields vary per ride: the *logged* system mass 71–80 kg (loadout — a record, not a guess, and identical in the blind re-run), plus five judged fields — $C_{rr}$ 0.004–0.020 (surface), $C_dA$ 0.32–0.40 (setup), air density 1.01–1.22 kg/m³ (weather and altitude), signed head/tailwind −7 to +5 km/h, and the recovery $\varepsilon$ 0.10–0.60 (hand-chosen); only $k_{\mathrm{eff}} = 0.98$ is fixed. The judged five are best guesses, not measurements, but better-informed than any single shared set ([§4.3](#4.3) owns this choice; [§3.1](#3.1) re-runs D1 blind as the coherence check). Every other corpus is evaluated *blind* under the frozen literature-typical set of [Terminology](#terminology), wind zero. 

**Mass.** Mass is the one per-rider input everywhere. On D1 it is *known* — the ride log records each brevet's system mass, used unchanged in both runs. Which corpora get an *inverted* mass follows from the roles above: the transfer corpora (D3–D4), where mass is genuinely unknown — and D5, where the author is deliberately processed as if he were an unknown rider, so the machinery's output can be graded against his known weight. For these, total mass is inverted from the corpus's own sustained-climb (≥ 3% over ≥ 100 m) energy balances: $\hat m = m_0\,(E_{\mathrm{meas}} - E_{\mathrm{aero}})/(E_{\mathrm{grav}} + E_{\mathrm{roll}})$, where $m_0$ is the generic prior mass (78 kg) whose gravity and rolling energies scale linearly with mass, and $E_{\mathrm{aero}}$ is charged at each climb segment's *measured* speed — not the model's $v_f$ — so the inversion is independent of the reference-speed machinery; per-ride median over rides with ≥ 200 m of sustained climbing. This yields 74.5 kg [IQR 69.1–78.4] for D3, 101.9 kg [95.9–109.0] for D4, and 74.7 kg [67.7–81.0] for D5 — validated against the author's known ≈ 73 kg ([§3.4](#3.4)). Note $\hat m g$ is invariant under a change of gravity constant by construction.

**Why priors, not fits.** All other constants take the literature-typical values listed in [Terminology](#terminology) — mid-range published field values for an upright rider on typical asphalt. They are deliberately *not* fitted per rider from the ride data: estimating $C_{rr}$ or $C_dA$ from the same energy measurements the models are scored on would let the parameters absorb modelling error, making the accuracy figures partly self-fulfilling. Shared priors keep the scoreboard falsifiable; [§3.4](#3.4) tests every conclusion's sensitivity to that choice with independently fitted per-rider constants.

**Protocol.** The comparison statistic is the per-ride signed error $\Delta\%$ ([Terminology](#terminology)); we report medians of $|\Delta\%|$ and of $\Delta\%$ with bootstrap 95% confidence intervals (CIs) and compare models pairwise with exact sign tests. Conventions: CIs are percentile bootstrap ($10^4$ resamples) over rides resampled independently within a corpus; sign tests drop tied rides (e.g. effective $n$ = 436 of 441 and 215 of 219 on the transfer corpora); rides within one rider are not independent, D1 ⊂ D5, and an activity-level join shows 58 of the 62 clean censo rides are the author's own recordings also present in D5 — so cross-corpus agreement should be read as consistency, not as five independent replications. Both behavioural constants ($\varepsilon_0$; the noise rate $c$) are fit on D1 only; the flat constant's value $\varepsilon_f = 0.20$ was selected on the urban corpus (so D2's own $\varepsilon_f$ numbers read as in-sample). All are then **frozen**. For the descent term we carry the two frozen variants everywhere — the dynamic $\varepsilon_d$ and the flat $\varepsilon_f$ — and report both; where a corpus's own in-sample best is quoted, it is labelled as such. A gate script re-derives every published corpus median and CI band — and the paired tests, descent statistics and noise rate this paper leans on — from the per-ride outputs, failing loudly on any mismatch; the full provenance is a public lab journal with an executable mirror.

<a id="2.4"></a>

### 2.4 Elevation sources and the noise-rate measurement

Every corpus is evaluated on the ride recordings' **own elevation streams** from the FIT files — consumer head units, barometric where the device carries one — resampled to 5 m steps. No DEM enters the evaluation anywhere; DEM-served elevation belongs to the deployment context and its scale-dependence ([§4.4](#4.4)). Consumer barometers are the best consumer-grade ascent source — cumulative-ascent consistency at the 1.5–3% level between units [Menaspà et al. 2014] — but whether a device over- or under-reads ascent depends on the *benchmark's* smoothing scale, because cumulative ascent has no scale-free true value [Rapaport 2011]: field comparisons disagree even on the sign for exactly this reason (the project's ascent-error survey collates them; lab journal, Entry 24). The jitter itself has mundane physical origins: short-period pressure fluctuation at the sensor port (gusts, speed changes), sensor resolution steps, and GPS altitude scatter where no barometer is present — slow weather drift, by contrast, moves *absolute* altitude far more than it moves $h_+$. This paper therefore fixes its scales explicitly, and they differ by constant: $c$ and $\tau$ live on the 5 m-resampled profile (the deadband is the work-bearing threshold there), while $\varepsilon_0$ is calibrated on the 30 m descent cells of [§2.2](#2.2) — the same 30 m grid a DEM-backed deployment samples. "The calibration scale" in the Discussion means the latter.

The noise rate $c$ is measured on the calibration corpus as a per-ride quantity: the raw ascent total minus the deadband-filtered one, divided by route length. Two properties justify the construction. First, the removed metres do no measurable work — the sustained-climb energy check ([§3.1](#3.1)) shows the filtered profile still pays the full gravity bill where real climbing lives. Second, the removal accumulates with *distance*, not with climbing (it is a per-sample jitter process), which is what licenses form 4's scalar version $\tilde h_\pm \approx h_\pm - c\,x$. The measured rate — 3.1 m per route-km median, IQR 2.6–3.7 ([§3.1](#3.1)) — is adopted as $c \approx 3$ m/km. The rate is a property of the *elevation source at this pipeline's scale* (consumer barometric recordings, 5 m resampling), not a universal: DEM-derived profiles carry their own, larger noise rates, and the project's journal measures per-source ascent corrections and a 5 m-DEM re-fit of the equivalent scalar (Entries 6 and 19–21) — map-derived totals therefore need a source-appropriate $c$, exactly as the scale-dependence of [§4.4](#4.4) predicts. The ascent-error literature validates per-point elevation or device totals against reference surfaces; validating the ascent total against *measured pedalling energy*, as the climb check does, is this study's addition.

## 3. Results

<a id="3.1"></a>

### 3.1 Two corrections take the closed form to parity with simulation

On the 44-ride calibration corpus — evaluated, per the calibration protocol of [§2.3](#2.3), with the author's condition-informed per-ride parameters — the original form 1 errs by 19.1% median [17.3, 21.5] and over-predicts nearly every ride (+19.1% [+17.3, +21.6] median signed). The split alone (form 2) halves the error to 8.6% [7.2, 11.0] (better than form 1 on 43 of 44 rides; the median ride spends 21% of its distance climbing); smoothing the elevation with the 2 m deadband (form 3, the proposed law) removes the ascent-noise half ([Table 2](#tab2), [Figure 6](#fig6)).

<a id="tab2"></a>

**Table 2.** Calibration-corpus scoreboard (44 rides): median $\lvert\Delta\%\rvert$ [95% CI] and median signed $\Delta\%$. Upper block: the calibration run — condition-informed per-ride parameters (logged mass, identical in both runs; judged $C_{rr}$, $C_dA$, air density and head/tailwind; a hand-chosen per-ride $\varepsilon$; [§2.3](#2.3) gives the ranges). Lower block (italic): the same forms re-run *blind* under the frozen protocol every other corpus uses — one shared literature-typical constants set, dynamic $\varepsilon_d$ — in the upper block's row order, so each form's informed→blind shift reads straight down.

| model (D1) | median $\lvert\Delta\%\rvert$ | 95% CI | median $\Delta\%$ [95% CI] |
|---|--:|:--|--:|
| **form 3, split + elevation smoothed (proposed)** | **3.5** | [2.0, 5.6] | +2.1 [+0.5, +4.3] |
| forward simulation | 5.2 | [3.8, 7.3] | −1.8 [−3.9, +0.3] |
| form 4, split + elevation correction | 5.9 | [3.6, 8.3] | −0.6 [−2.7, +2.4] |
| form 2, split only | 8.6 | [7.2, 11.0] | +8.4 [+6.8, +11.0] |
| form 1, original | 19.1 | [17.3, 21.5] | +19.1 [+17.3, +21.6] |
| *frozen (blind): form 3* | *8.2* | *[4.5, 10.8]* | *+2.2 [−2.5, +4.5]* |
| *frozen (blind): forward simulation* | *8.4* | *[5.1, 10.9]* | *+2.5 [−1.6, +7.1]* |
| *frozen (blind): form 4* | *7.6* | *[5.6, 11.6]* | *−0.5 [−5.0, +3.7]* |
| *frozen (blind): form 2* | *7.9* | *[5.5, 13.6]* | *+4.9 [+0.9, +10.9]* |
| *frozen (blind): form 1* | *14.9* | *[10.6, 22.6]* | *+14.0 [+10.2, +22.5]* |

<a id="fig6"></a>

![**Figure 6.** The calibration scoreboard under both protocols: per form, the condition-informed per-ride parameters (orange) versus the blind frozen constants (grey), whiskers the 95% CIs, dashed lines the simulation under each protocol. Parity between the corrected forms and the simulation holds under both; the informed-blind shift (+4.7 on form 3, +3.2 on the simulation; forms 1–2 improve blind) prices condition knowledge, in-sample.](figs/fig1-attribution.svg)

The corrected closed form and the simulation are statistically indistinguishable (form 3 closer on 24 of 44 rides; sign test $p = 0.65$) — no detectable difference, though equivalence is not formally tested and $n = 44$ limits statistical power. That parity is the practically decisive outcome: the closed forms are the ones cheap enough to evaluate per edge in a router, and [§3.3](#3.3) tests them off this corpus.

The *blind* re-run (Table 2's lower block) is the coherence check: under the frozen protocol every other corpus uses — one shared literature-typical constants set, zero wind, dynamic $\varepsilon_d$ — the corrected forms cluster at 7.6–8.2% and the simulation at 8.4%, still statistically indistinguishable (form 3 vs simulation: 22 of 44, $p = 1.00$; form 4: 17 of 44, $p = 0.17$). Three readings follow. First, parity is protocol-independent — the corrected forms and the simulation move together, consistent with the sensitivity sweeps' finding ([§3.4](#3.4); lab journal, Entries 29–30) that parameter changes move both engines' absolute error at the several-point scale, in lockstep. Second, the informed→blind shift is form-specific: +4.7 points on the proposed form 3 and +3.2 on the simulation, but only +1.8 on form 4 — and forms 1–2 actually *improve* blind, their standing biases partially cancelling under the frozen $\varepsilon_d$. Read on the proposed-form/simulation pair, the ≈ 3–5-point shift is an in-sample point estimate of what condition-informed per-ride judgment buys over one constants-fit-all set — an *upper* bound, since the hand-chosen per-ride $\varepsilon$ shades into per-ride fitting; the sensitivity sweeps of [§3.4](#3.4) say parameters move absolute error at exactly this scale, and the gap motivates the per-ride-inference and measured-constants routes of [§4.4](#4.4). Third, blind, D1 is the *hardest* corpus — long wind-exposed brevets are where zero-wind generic constants bite hardest — and the transfer corpora, equally heterogeneous but judgment-less, carry that same blind penalty in all their numbers.

Three checks support the attribution. First, on *sustained* climbs (2,535 sections ≥ 3% over ≥ 100 m, 54% of all ascent) the measured energy matches the expected gravity + rolling + aero to within 3–5% (informed: 41,790 vs 43,233 kJ, ratio 0.97; frozen: vs 43,979 kJ, ratio 0.95) — the gravity term needs no discount; what inflates raw $h_+$ is the noise and rollers the deadband removes. Second, the deadband's premise is itself a measurement: across the 44 rides, raw minus deadband-filtered ascent accumulates at **3.1 m per route-kilometre** (median; IQR 2.6–3.7) — and it accumulates with *distance*, not with climbing, which is what licenses form 4's scalar version and sets $c \approx 3$. Together with the first check — the full $\beta\,\Delta h$ is paid where no sub-metre undulation exists — this locates the removed metres outside the real climbs. Third, carried frozen to the urban corpus (D2) with a fully generic assumed rider, the law with $\varepsilon_d$ lands at parity with the simulation (7.7% with form 3 and 6.4% with form 4 against 6.6%; [Table 3](#tab3), D2 column, carries the CIs), with nothing refit. The flat $\varepsilon_f = 0.20$ does better still there (4.7% / 3.9%, parity at $p = 0.70$) — but that constant was itself selected in-sample on these urban rides, so those medians read as a fitted benchmark, not as transfer; the frozen-variant numbers are the honest headline.

<a id="3.2"></a>

### 3.2 The coasting deficit: descent recovery has a geometry and a habit

Descent recovery is unambiguously real: with form 3, setting $\varepsilon = 0$ over-predicts every corpus (on the urban rides alone by +7.2% [+4.9, +9.2] median; form 4's version of the check is confounded on gentle terrain by the scalar correction's own bias). On the calibration corpus, the measured $\varepsilon_{\mathrm{bal}}$ tracks the geometry-only $\varepsilon_{\mathrm{coast}}$ exactly where descents carry energy: the correlation rises from 0.30 (all rides) to 0.60 (descent-energy-weighted) to 0.77 on real descents (mean descent grade ≥ 3%; 0.82 at ≥ 3.5%) ([Figure 7](#fig7)).

These correlations are partly part–whole (the two quantities share their dominant term $\alpha/\beta$), so the statistic we lead with is error reduction: on real descents, the calibrated line $\varepsilon_{\mathrm{coast}} - 0.13$ reaches RMS (root-mean-square — the typical size of a miss) 0.08 against a best-flat-constant baseline of RMS 0.13 — a 37% reduction, computed on unrounded values, in-sample. A worked example, from the ride nearest the subset's median residual (Afora): drop-weighted over its descent cells, $\varepsilon_{\mathrm{coast}} = 0.44$; subtracting the deficit, $0.44 - 0.13 = 0.31$; the measured balance is 0.31. (The hand recipe of [§4.1](#4.1) uses a cheaper *lumped* variant, $\min(1, (\alpha/\beta)/\bar s)$ at the mean descent grade — computable on paper, but it does not achieve the drop-weighted estimator's RMS, and the two differ most on rides mixing gentle and steep descents.)

<a id="fig7"></a>

![**Figure 7.** Geometry-only $\varepsilon_{\mathrm{coast}}$ vs the power-measured $\varepsilon_{\mathrm{bal}}$, one point per ride (area ∝ descent energy). On real descents the calibrated line $\varepsilon = \varepsilon_{\mathrm{coast}} - 0.13$ tracks the measurements; the shaded band is the 95% bootstrap CI of the median offset on that subset, [0.10, 0.17]. Gentle rides scatter but carry ≈ 0 descent energy. (The two axes share their dominant term $\alpha/\beta$, so visual agreement partly reflects shared inputs — the error-reduction statistic in the text is the load-bearing one.)](figs/fig4-eps-scatter.svg)

The residual between ideal and measured is a near-constant −0.13, and its *character* matters. The route-geometry covariates we tested all fail to explain it: curviness and unpaved fraction fit with the wrong sign (twisty, rough rides are the mountainous ones that recover *more*), and on the urban corpus no braking-density predictor survives ($R^2 \leq 0.14$; a mechanistic braking-energy subtraction over-corrects). On a descent, gravity — not the legs — repays what a red light took, so stop-go density does not move $\varepsilon$. The pattern is consistent with a rider-behaviour interpretation: the deficit encodes *how the rider descends* — residual pedalling into the descent (braking cancels out of the balance itself; [§1.3](#1.3), [Appendix A](#appendix-a)). If so, the deficit should transfer across routes but vary with descent style across riders — a testable prediction ([§3.3](#3.3)). (Bicycle setup — gearing that permits pedalling at speed, riding position — and regional riding culture could plausibly shape that habit's baseline; within these corpora they are unresolved, all three riders being São Paulo road cyclists.)

Two boundaries complete the picture. On flat terrain the clamp-to-1 prediction inverts — gentle rides are pedalled *through* dips, so measured $\varepsilon \to 0$ — harmlessly, since such rides carry ≈ 0 descent energy (this is why the estimator must be restricted to real descents; over all 44 rides it loses to a flat constant). And in urban stop-go riding, $\varepsilon_{\mathrm{coast}}$ over-credits recovery; a flat $\varepsilon \approx 0.20$ fits better there. Notably, the frozen $\varepsilon_d$ transferred to the urban corpus comes within 0.01 RMS of the flat constant selected in-sample *on that corpus* (0.09 vs 0.08) — the calibration survives the regime change even where the geometry itself stops helping.

<a id="3.3"></a>

### 3.3 Transfer: what survives being frozen and carried to other riders

With every behavioural constant frozen ($\varepsilon_0$ and $c$ from D1, $\varepsilon_f$ from D2), the energy law reproduces two independent riders' full histories to 3.5–5.8% median error with the regime-appropriate $\varepsilon$ — form 3 with $\varepsilon_d$ on the open-road rider (5.8), with $\varepsilon_f$ on the gentle-terrain rider (3.5) ([Table 3](#tab3)).

<a id="tab3"></a>

**Table 3.** Frozen-constant results on every non-calibration corpus: the urban regime test (D2), the two independent riders (D3–D4, transfer), the author's full history (D5, in-sample machinery validation at scale), and the D3–D5 pool. All four form × ε combinations are frozen; best out-of-sample law per corpus in bold (starred in-sample cells excluded). The flat constant is ε_f = 0.20. Starred cells are in-sample: ε_f was selected on D2. D2 is excluded from the pool because 58 of its 62 rides are already in D5. † marks D5, the calibration rider's own history. Subcolumns: *error* = median $\lvert\Delta\%\rvert$, *bias* = median signed $\Delta\%$. Brackets are 95% CIs throughout; the pooled column's are stratified bootstrap (rides resampled within each corpus, then pooled). Signed medians print with ties-away rounding; the D5 simulation's exact signed median is +0.05.

<table>
<thead>
<tr><th rowspan="2">frozen model</th><th colspan="2">D2 · censo · 62</th><th colspan="2">D3 · P. Paz · 441</th><th colspan="2">D4 · JAAM · 219</th><th colspan="2">D5 · author · 621†</th><th colspan="2">D3–D5 · pooled · 1,281</th></tr>
<tr><th>error</th><th>bias</th><th>error</th><th>bias</th><th>error</th><th>bias</th><th>error</th><th>bias</th><th>error</th><th>bias</th></tr>
</thead>
<tbody>
<tr><td>form 3 · ε<sub>d</sub></td><td>7.7 [6.0,9.3]</td><td>−5.1 [−7.6,−2.2]</td><td>5.8 [5.3,6.4]</td><td>+4.3 [+3.1,+4.9]</td><td>5.5 [4.4,6.4]</td><td>−4.7 [−5.7,−3.7]</td><td><strong>6.2</strong> [5.6,6.9]</td><td>−0.3 [−1.6,+0.6]</td><td><strong>5.9</strong> [5.5,6.2]</td><td>+0.4 [−0.1,+1.1]</td></tr>
<tr><td>form 4 · ε<sub>d</sub></td><td><strong>6.4</strong> [4.8,8.6]</td><td>−3.4 [−4.9,−0.3]</td><td><strong>4.9</strong> [4.4,5.8]</td><td>+0.6 [−0.1,+1.3]</td><td>9.0 [7.9,9.7]</td><td>−8.4 [−9.5,−7.5]</td><td>7.1 [6.4,8.1]</td><td>−1.9 [−3.0,−1.4]</td><td>6.6 [6.3,7.1]</td><td>−2.4 [−3.0,−1.9]</td></tr>
<tr><td>form 3 · ε<sub>f</sub></td><td>4.7* [3.3,6.2]</td><td>−0.9 [−3.3,+1.1]</td><td>10.1 [9.3,10.7]</td><td>+10.0 [+8.8,+10.7]</td><td><strong>3.5</strong> [3.1,4.2]</td><td>+0.4 [−0.8,+1.2]</td><td>8.1 [7.3,8.7]</td><td>+5.6 [+4.1,+6.6]</td><td>7.5 [7.0,8.0]</td><td>+5.9 [+5.2,+6.5]</td></tr>
<tr><td>form 4 · ε<sub>f</sub></td><td>3.9* [3.2,6.1]</td><td>+1.0 [−1.6,+3.5]</td><td>6.8 [6.0,7.6]</td><td>+5.4 [+4.1,+6.6]</td><td>5.6 [4.8,6.4]</td><td>−4.3 [−5.0,−3.3]</td><td>6.9 [6.2,7.5]</td><td>+3.8 [+2.8,+5.0]</td><td>6.6 [6.1,7.0]</td><td>+2.8 [+2.2,+3.5]</td></tr>
<tr><td>simulation</td><td>6.6 [4.7,8.7]</td><td>−3.5 [−6.4,−1.8]</td><td>6.8 [6.2,7.8]</td><td>+5.0 [+3.8,+5.9]</td><td>5.4 [4.9,6.1]</td><td>−5.0 [−5.8,−4.3]</td><td>6.1 [5.5,6.7]</td><td>+0.1 [−0.9,+0.9]</td><td>6.2 [5.9,6.6]</td><td>+0.7 [+0.1,+1.3]</td></tr>
</tbody>
</table>

<a id="fig8"></a>

![**Figure 8.** Table 3 as a slopegraph: median $\lvert\Delta\%\rvert$ per corpus for form 3 under each $\varepsilon$ rule, with the simulation for reference (whiskers: 95% CIs; faint: form 4; D2's $\varepsilon_f$ point is in-sample). The regime rule is the picture: the flat constant zigzags — best exactly where terrain is gentle or urban, worst on the open-road corpora — while the dynamic estimator stays level beside the simulation everywhere.](figs/fig8-regime-slopes.svg)

The grid — and [Figure 8](#fig8), its one-glance version — matches the regime rule from [§3.2](#3.2): the dynamic estimator wins on the open-road rider (D3), the flat constant on the gentle-terrain rider (D4) — and adds a sharper observation: the form × $\varepsilon$ interaction is itself regime-dependent. Form 4 with $\varepsilon_d$ is the *best* cell on P. Paz (4.9, that corpus's best cell) and the *worst* on JAAM (9.0), where the scalar elevation correction and the dynamic estimator compound on gentle terrain. With the regime-appropriate $\varepsilon$, the law stays at or better than simulation parity on both riders. Across the frozen transfer and scale corpora (D3–D5, [Table 3](#tab3)) the law holds at **3.5–6.2% median error** when the [§3.2](#3.2) regime rule picks the $\varepsilon$ variant; the frozen urban test sits at 6.4–7.7% (its flat constant being in-sample there), and the calibration corpus itself at 3.5% informed to 8.2% blind ([Table 2](#tab2)). Pooled over the transfer riders alone (D3+D4, $n = 660$; stratified bootstrap, rides resampled within each corpus), form 3 with $\varepsilon_d$ reads **5.6% [5.2, 6.2]** against the simulation's 6.3% [5.8, 6.8] — the genuinely out-of-sample number. Adding D5 (the calibration rider's own history, in-sample for the machinery) gives the full-pool 5.9% [5.5, 6.2] vs 6.2% [5.9, 6.6]. Per-ride allegiance splits across corpora — the law significantly closer on D3 (280/441, $p < 10^{-4}$), the simulation on D5 (351/621, $p = 0.0013$) — so the pooled tie is median parity, not per-ride equivalence.

**The coasting deficit recurs on every rider.** P. Paz's measured gap between $\varepsilon_{\mathrm{coast}}$ and $\varepsilon_{\mathrm{bal}}$ on real descents is 0.12 [0.10, 0.14]; JAAM's is 0.13 [0.10, 0.19]; the author's full history gives 0.14 [0.12, 0.16]; the calibration value was 0.13. (Positivity of the gap is structural only at the true physics — computed under assumed constants it is an empirical finding, and the sweep's implausible low-$\rho C_dA$ corners can invert it ([§3.4](#3.4)) — so we count the recurrence as *consistent across riders*, not as three independent confirmations.)

**The dynamic estimator's extra accuracy over a flat constant is rider-dependent.** For P. Paz, a coasting-style descender on open roads, the frozen estimator's descent-recovery error (RMS 0.096 on 161 real descents) beats even his own in-sample best flat constant (0.145) by 34% — under the generic assumed physics; under his fitted constants the margin collapses to a statistical tie ([§3.4](#3.4)). For JAAM, who pedals his descents (measured $\varepsilon_{\mathrm{bal}}$ 0.17–0.28 on mostly gentle terrain), the frozen estimator fails outright on the gentle bulk (RMS 0.47 vs a flat constant's 0.16) and on his few real descents ($n = 21$) sits at RMS 0.090 — against the frozen flat 0.20's 0.111 the difference is inconclusive (−0.020, 95% CI [−0.070, +0.024]), and against his own in-sample best flat constant (0.28, RMS 0.085) it is a tie. The practical rule stands: dynamic $\varepsilon_d$ on open, coastable terrain (mean descent grade ≥ 3%); flat $\varepsilon_f \approx 0.20$ otherwise; either way the deficit constant carries.

<a id="3.4"></a>

### 3.4 Robustness

**Fitted versus assumed physics.** An independent per-activity parameter fit (virtual-elevation family [Chung 2012]) puts P. Paz's effective $C_dA$ near 0.26 against the assumed 0.40. Re-running everything under his fitted constants ([Table 4](#tab4)) leaves the energy law's accuracy intact (4.7–7.0% median either way — Table 4's law row; the simulation's bias flips +5.0 → −6.9) but collapses the 34% descent-term margin to a statistical tie (RMS 0.085 vs 0.089), and shifts his measured deficit gap from 0.12 to 0.19 (the lower $C_dA$ lowers $\alpha$, hence $\varepsilon_{\mathrm{bal}}$ drops 0.36 → 0.14). JAAM's numbers are robust to the same swap (gap 0.13 → 0.12; tie either way). Under each rider's best-guess physics, then, both independent riders tell the same story — the dynamic estimator ties a flat constant — and the deficit's *recurrence* is robust while its *value* on one rider is parameter-sensitive. We keep the assumed-physics numbers as the headline (the whole $\varepsilon$ framework, including $\varepsilon_0$, is defined under them) and read the fitted rerun as the honest error bar: the 34% margin should not be leaned on, and the gap is 0.12–0.19 rather than a point value.

<a id="tab4"></a>

**Table 4.** Fitted versus assumed physics: each independent rider re-evaluated under his own fitted constants (P. Paz $C_dA$ 0.26, $C_{rr}$ 0.0053, $m$ 80.9 kg; JAAM 0.32, 0.011, 103.4 kg). Medians carry 95% CIs; the RMS pairs are point statistics.

| | P. Paz, assumed | P. Paz, fitted | JAAM, assumed | JAAM, fitted |
|---|--:|--:|--:|--:|
| energy law (form 3, $\varepsilon_d$) median (signed) | 5.8 [5.3, 6.4] (+4.3 [+3.1, +4.9]) | 7.0 [6.2, 7.6] (−6.2 [−7.1, −5.3]) | 5.5 [4.4, 6.4] (−4.7 [−5.7, −3.7]) | 4.7 [4.0, 5.7] (−3.5 [−4.6, −2.8]) |
| simulation median $\lvert\Delta\%\rvert$ (signed [95% CI]) | 6.8 [6.2, 7.8] (+5.0 [+3.8, +5.9]) | 7.5 [6.6, 8.7] (−6.9 [−8.1, −5.7]) | 5.4 [4.9, 6.1] (−5.0 [−5.8, −4.3]) | 5.0 [4.3, 5.6] (−4.0 [−4.9, −3.1]) |
| dynamic-$\varepsilon$ RMS vs own best flat (real descents; $n$ = 161 / 21) | 0.096 vs 0.145 | 0.085 vs 0.089 | 0.090 vs 0.085 | 0.088 vs 0.085 |
| measured deficit gap [95% CI] | 0.12 [0.10, 0.14] | 0.19 [0.17, 0.20] | 0.13 [0.10, 0.19] | 0.12 [0.10, 0.17] |

**Mass.** The implied-mass machinery validates in-sample: the author's full history returns 74.7 kg (sustained-climb inversion) and 71.4 kg (independent parameter fit) against a known ≈ 73 kg, and a parameter fit restricted to the 44 calibration brevets returns 79.9 kg — resolved as genuine loadout rather than bias, matching the logged 71–80 kg range of those rides. Sweeping P. Paz's mass 70/74.5/78 kg moves the frozen-estimator RMS only 0.101/0.096/0.092 (against his own in-sample flat constant's 0.153/0.145/0.139) — no conclusion in this section changes within the plausible range.

**Physical-constants sweep.** A pre-registered 108-point sweep over $C_dA \times C_{rr} \times \rho$ (lab journal, Entry 29) extends the two-point checks above to a map: six registered predictions, three confirmed and three refuted. Confirmed: $\rho$ and $C_dA$ enter every quantity only as their product (exact to float precision — the map is two-dimensional); the mass inversion *compensates* (±3 kg of $\hat m$ against ±60% parameter excursions, with the law's medians moving only by points); and the D3 dynamic-vs-flat verdict flips exactly where the fitted rerun said it would, as $\rho C_dA$ falls. Refuted: the deficit gap's value is *not* parameter-free — it is monotone in $\rho C_dA$, spanning −0.07 to +0.19 across the grid, so $\varepsilon_0 = 0.13$ means *at the prior, at this scale* (the positive gap's recurrence holds across the plausible region); the priors do *not* sit at an error minimum — variants with signed bias improve when the constants move against the bias, so the anchor is a prior, not an optimum; and there is no universal common minimizer — cells minimizing every variant at once exist on only two of four corpora, in different corners for different riders, so each variant's apparent gain (~1–2 points) is signed-bias cancellation: the circularity argument of [§2.3](#2.3) measured rather than argued. A companion sweep of the *simulation* (one-at-a-time; journal Entry 30) quantifies the shared-constants design of [§2.1](#2.1): both engines' absolute errors move in lockstep by up to ±6 points across the excursions, while the model-vs-model gap moves by 9–14× less on the transfer riders — which is why the paired conclusions survive parameter uncertainty that the absolute numbers do not.

**In-sample validation at scale.** On the author's 621 clean rides the frozen grid replays the calibration story at fourteen times the sample ([Table 3](#tab3), D5 column): form 3 with $\varepsilon_d$ and the simulation land within 0.1 point of each other (6.2 vs 6.1, both with near-zero bias) — though at this sample size the per-ride sign test *can* separate them: the simulation is marginally but significantly closer (351 of 621, $p = 0.0013$), the mirror image of D3, where the *law* is significantly closer (280 of 441, $p < 10^{-4}$). Median parity with opposite per-ride allegiances is the honest statement of the tie. The flat constant loses on the author's open terrain — the [§3.2](#3.2) regime rule confirmed at scale — and the coasting deficit recurs (measured gap 0.14 [0.12, 0.16] on 221 real descents).

**Per-ride inverted physics.** The last rung of the parameter ladder — priors (Tables 2–3), rider-level fits (Table 4) — is fully automatic *per-ride* inversion: every ride's own power stream sets its mass, $C_{rr}$ and $C_dA$, with no human judgment (lab journal, Entry 33, pre-registered). The recipe: rides are segmented into strict climbs (grade ≥ 2% throughout, ≥ 40 m gain) and strict in-band flats (≥ 1 km), transients clipped, segments kept only if well-behaved (no braking events, power present ≥ 90% of the time, no stops); mass comes from a temporally-spread subset of the climbs (an average-mass estimator), $C_{rr}$ from the *remaining* climbs at the prior $C_dA$ (segment-disjoint, breaking the per-climb $m$–$C_{rr}$ collinearity), and $C_dA$ from the flats; head/tailwind is zero for round trips and half the historical daily ground wind projected on the net bearing otherwise. Fields with no qualifying segment fall back to the priors, flagged. The mass estimator *validates*: corpus medians land at 75.4 kg (D3, anchor 74.5), 98.7 (D4, anchor 101.9), 73.7 (D5, known ≈ 74.7), and inside the logged 71–80 range on D1. The inverted $C_{rr}$ centres on 0.0083–0.0095 (the 0.008 prior was a good guess); the inverted $C_dA$ comes out *low* everywhere (0.26–0.39) — an **effective** aero that absorbs drafting and position, not a wind-tunnel number.

<a id="tab5"></a>

**Table 5.** The [Table 3](#tab3) analogue under per-ride inverted physics (m̂, $\hat C_{rr}$, $\hat C_dA$ from each ride's own segments; priors as flagged fallbacks). Populations differ slightly from Table 3 (this experiment's eligibility is parse + power + ≥ 3 km): D2 n = 69, D5 n = 636, pooled n = 1,296; the pooled column is a stratified bootstrap (rides resampled within each corpus). Cells: median $\lvert\Delta\%\rvert$ [95% CI] · median signed $\Delta\%$ [95% CI]; best law per corpus in bold. Because the constants are read from the ride being scored, this is partially in-sample per ride — it answers "can the ride's telemetry replace judgment and priors?", not the frozen-transfer question.

| model | D2 · 69 | D3 · 441 | D4 · 219 | D5 · 636 | D3–D5 pooled · 1,296 |
|---|--:|--:|--:|--:|--:|
| form 3 · $\varepsilon_d$ | 7.0 [5.4, 9.5] · −3.1 [−4.7, −1.1] | 5.1 [4.6, 5.5] · −3.8 [−4.4, −3.2] | 6.0 [5.2, 6.5] · −5.2 [−6.2, −4.4] | 7.5 [7.1, 8.0] · −4.0 [−4.7, −3.2] | 6.3 [6.0, 6.6] · −4.2 [−4.5, −3.7] |
| form 3 · $\varepsilon_f$ | 5.8 [4.9, 7.8] · −0.5 [−1.7, +2.4] | **3.2** [2.7, 3.6] · +0.2 [−0.3, +0.7] | **3.1** [2.6, 3.3] · −0.4 [−1.2, +0.4] | **5.3** [4.6, 6.1] · +0.9 [+0.3, +1.8] | **3.8** [3.6, 4.1] · +0.4 [−0.0, +0.8] |
| form 4 · $\varepsilon_f$ | **5.4** [3.2, 7.1] · +2.4 [−0.5, +6.1] | 4.8 [4.3, 5.2] · −3.0 [−3.6, −2.5] | 6.4 [5.9, 7.0] · −5.3 [−6.1, −4.4] | 5.8 [5.3, 6.3] · −0.4 [−1.1, +0.3] | 5.7 [5.2, 6.0] · −2.4 [−2.7, −1.9] |
| simulation | 7.8 [4.7, 9.5] · −2.2 [−4.7, +1.4] | 5.7 [5.3, 6.2] · −4.6 [−5.2, −4.0] | 5.8 [4.9, 6.5] · −4.9 [−6.0, −4.3] | 7.2 [6.7, 7.9] · −3.5 [−4.3, −2.6] | 6.4 [6.1, 6.7] · −4.3 [−4.7, −3.9] |

Two results stand out. First, the **flat-ε law under automatic physics** reaches 3.2 / 3.1 / 5.3% on the three riders with near-zero bias (+0.2 / −0.4 / +0.9), pooling to **3.8% [3.6, 4.1]** over the 1,296 rides — about two points better than the frozen pool's best (5.9% [5.5, 6.2]) at the same near-zero bias, CIs disjoint; on D3 the move is a collapse from the frozen run's 10.1% (bias +10.0): the effective $C_dA$ prices the drafting the frozen prior cannot see. Second, the **regime rule flips**: with the lower effective $\alpha$, $\varepsilon_{\mathrm{coast}}$ shrinks and the frozen $\varepsilon_0 = 0.13$ over-refunds, so $\varepsilon_f$ beats $\varepsilon_d$ on *every* corpus — including the open terrain where $\varepsilon_d$ won under priors. (Read accuracy and bias together: $\varepsilon_d$'s apparent D3 gain, 5.8 → 5.1, swaps a +4.3 bias for a −3.8 one — substitution, not improvement — while the $\varepsilon_f$ gains carry their biases to near zero with disjoint CIs, the real move.) This is the sweep's refuted P2 made concrete: the deficit's value travels with its physics ([§4.4](#4.4)), and the [§3.2](#3.2) regime rule is a statement about a (physics, ε-variant) *pair*. Parity with the simulation persists throughout (within 0.6 points per corpus, biases moving together — the lockstep again). Fully-inverted subsets do better still (2.6–4.6%) but are selection-biased toward mountainous rides and are not comparable to corpus medians.

**The [§1.4](#1.4) hypotheses, resolved.** H1 (attribution and parity): supported — two mechanisms carry the correction (under the frozen protocol the deadband's contribution appears in the bias rather than the median), and no paired test separates the corrected forms from the simulation at $n = 44$ (equivalence not formally tested; [§3.1](#3.1)). H2 (a single constant on genuine descents): confirmed at the shared physics and 30 m scale — the deficit recurs at 0.12–0.14 across riders — but it fails on gentle terrain ([§3.2](#3.2)), and its *value* is conditional on $\rho C_dA$ and sampling scale (the sweep above, [§4.4](#4.4)). H3 (transfer): the law and the deficit transfer; the dynamic estimator's extra accuracy over a flat constant is rider- and parameter-dependent ([§3.3](#3.3)).

## 4. Discussion

<a id="4.1"></a>

### 4.1 Applications and implications

**What the result licenses.** The closed form's error was never diffuse: two identifiable artifacts carried it, and once they are corrected we measured no accuracy cost on our corpora for abandoning simulation at the route level. That licenses three concrete uses.

*Routing.* The corrected law is $O(1)$ per edge and its inputs — length, ascent, descent, grade — are exactly what a DEM-backed router already has. A production deployment exists (the *Simujaules* energy-field router, <https://simujaules.pedalhidrografi.co>, which serves this law as its per-edge cost); one constraint from [§4.4](#4.4) applies: the behavioural constants are tied to the elevation-sampling scale they were calibrated on (30 m), so a deployment on a different DEM resolution must re-fit them or pre-smooth the raster.

*Planning by hand.* The law starts from three numbers any route page already shows — distance, total ascent, total descent — adds a rough climbing share and the rider's own flat cruising speed, and needs no arithmetic beyond a phone calculator. No simulation software, no app, no code. That makes the energy of a proposed route computable by anyone, which for a self-organized cycling collective is the difference between a model members can check and a black box they must trust. This is not hypothetical: *Pedal Hidrográfico* uses the law in practice to judge whether a planned tour is adequate for its participants, operationalized as a spreadsheet any member can run — no code involved. In that day-to-day use, predictions have landed within very roughly ~5% of riders' measured energies, give or take ten points (a field impression, not one of this paper's gated statistics). Occam earns his keep: the simplest law that survives the data is also the one that is teachable in an afternoon.

*Physiology-adjacent estimates.* Mechanical kJ converts to food energy with a happy coincidence: typical muscular efficiency (~24%) means each mechanical kJ costs ≈ 4.2 kJ of metabolic energy, and 1 food kcal = 4.184 kJ — so 1 mechanical kJ ≈ 1 food kcal, and the law's output doubles as a meal-planning number for long rides.

**The calculation recipe.** For a rider of total system mass $m$ (rider + bike + gear, kg) and flat cruising speed $v_f$:

> 1. **Constants** (defaults: $C_{rr} = 0.008$, $C_dA = 0.40\ \mathrm{m^2}$, $\rho = 1.13\ \mathrm{kg/m^3}$, $k_{\mathrm{eff}} = 0.98$, $g = 9.79\ \mathrm{m/s^2}$):
>    $\alpha_r = C_{rr}\,m g/k_{\mathrm{eff}}$ · $\alpha_a = \tfrac{1}{2}\rho\,C_dA\,v_f^2/k_{\mathrm{eff}}$ · $\beta = m g/k_{\mathrm{eff}}$.
> 2. **If you know your flat power $P$ instead of your cruising speed** (the power you hold on a flat stretch — not the whole-ride average, which mixes climbs and coasting zeros): $v_f$ is the speed at which flat power balances, $P = (\alpha_r + \alpha_a(v_f))\,v_f$ — the same anchor the study uses to match the two models ([§2.1](#2.1)). Guess-and-check converges in two or three tries because $P$ grows steeply with speed; see the worked example.
> 3. **Correct the elevation totals**: subtract 3 m per km of route from both $h_+$ and $h_-$ — a rate measured on barometric ride recordings; DEM/map-derived profiles need their own, larger rate ([§2.4](#2.4)), and skip this step if your source already smooths.
> 4. **Choose $\varepsilon$**: descents mostly steeper than 3% mean grade → the dynamic $\varepsilon_d = \min(1, (\alpha/\beta)/\bar s) - 0.13$ (no floor; a negative result — mean descent grade beyond $(\alpha/\beta)/0.13$, ≈ 11–15% — means the route out-steepens everything this law was validated on, so treat the estimate as extrapolation); urban stop-go or gentle terrain → the flat $\varepsilon_f = 0.20$. This mean-grade form is the lumped approximation of the drop-weighted estimator ([§3.2](#3.2)).
> 5. **Sum**: $E = \alpha_r x + \alpha_a x_{\mathrm{flat}} + \beta h_+ - \varepsilon\,\beta h_-$. The climbing-distance share is the recipe's fourth route input: read it from the profile if you have one, or use $\boldsymbol{x_{\mathrm{flat}} \approx 0.8\,x}$ as a rolling-terrain default (the calibration corpus's median ride climbs for 21% of its distance).
>
> This is form 4 — the proposed law with the scalar elevation correction ([Table 2](#tab2); 5.9% [3.6, 8.3] median with condition-informed parameters, 7.6% [5.6, 11.6] blind — the best form under the blind protocol): step 3 is the scalar stand-in for the deadband filter, and the split enters through $x_{\mathrm{flat}}$ in step 5 — rolling is paid over all of $x$, air only off the climbs. Note the unit switch: the rates are in J/m, so divide by 1{,}000 for kJ ($\beta = 749$ J/m $= 0.749$ kJ/m in the example).
>
> **Worked example** — 75 kg system, flat power $P = 50$ W, 25 km city ride, raw totals 200 m up / 200 m down.
>
> 1. Constants: $\alpha_r = 0.008 \times 75 \times 9.79/0.98 = 6.0$ J/m; $\beta = 75 \times 9.79/0.98 = 749$ J/m.
> 2. Speed from power: guess 14 km/h (4 m/s) → $(6.0 + 3.7) \times 4 = 39$ W, too low; guess 18 km/h (5 m/s) → $(6.0 + 5.8) \times 5 = 59$ W, too high; guess 16.6 km/h (4.6 m/s) → $(6.0 + 4.9) \times 4.6 = 50$ W ✓. So $v_f = 4.6$ m/s and $\alpha_a = 4.9$ J/m.
> 3. Corrected totals: $200 - 3 \times 25 = 125$ m of climb (descent likewise 125 m).
> 4. City riding → $\varepsilon = 0.20$.
> 5. Rolling: $6.0 \times 25{,}000 = 150$ kJ. Aero ($x_{\mathrm{flat}} = 0.8 \times 25 = 20$ km): $4.9 \times 20{,}000 = 98$ kJ. Climb: $0.749 \times 125 = 94$ kJ. Descent refund: $0.20 \times 0.749 \times 125 = 19$ kJ.
> 6. **Total: $150 + 98 + 94 - 19 \approx 320$ kJ — roughly 320 kcal of food.**
>
> (Same route in open mountains with mean descent grade 4%: $\alpha/\beta = 10.9/749 = 1.45\%$, so $\varepsilon = 0.0145/0.04 - 0.13 \approx 0.23$, and the refund grows to 22 kJ.)

**What the descent term means.** Recovery has a *geometry* (the coasting limit, parameter-free) and a *habit* (the coasting deficit, one constant). The geometry sets the ceiling; the habit sets the discount; and it is the habit constant — not the geometry's residual detail — that transfers across riders. A planner that knows nothing about a rider should use the dynamic $\varepsilon_d$ on open terrain and the flat $\varepsilon_f = 0.20$ in cities, and none of the route-side predictors we tested improved on that rule — what remains looks like behaviour, not geometry.

<a id="4.2"></a>

### 4.2 Relation to prior work

The forward model we benchmark against is the extensively validated instantaneous power balance [Martin et al. 1998; Dahmen et al. 2011]; our contribution is not there but in the route-level closed form and its assessment against measured route energy, which we did not find elsewhere. The nearest bodies of work treat recovery per-instant or symmetrically: Bigazzi & Lindsey's speed-choice model carries the same coasting/braking idle limit we build on, but applies it to per-grade steady-state speed choice, never to a route-level closed form [Bigazzi & Lindsey 2019]; EV energy models carry regeneration efficiencies or symmetric potential terms [Yuan et al. 2024; Ahmadi et al. 2024; Perger & Auer 2020]; route-choice models fit elevation coefficients with no physical form [Scarf & Grehan 2005]. The ascent-inflation artifact we correct is a measurement pathology already diagnosed *for cycling* by Rapaport, who supplies the diagnosis — and anticipates the roller-momentum intuition — but no correction; ours folds the correction into the energy law itself [Rapaport 2011]. Our parameter-inversion machinery follows the energy-balance logic of Chung's virtual-elevation method [Chung 2012].

To our knowledge the lumped, closed-form, route-level $\varepsilon$ — and a calibrated recovery constant shown to recur across riders — has no located precedent in the road-cycling-power and elevation-aware-routing literature we searched. That is a corpus-bounded claim about our search, not a proof of primacy.

<a id="4.3"></a>

### 4.3 Limitations

The calibration itself rests on the informed-parameters run: per-ride best-guess constants from literature values and the author's judgment — chosen because useful beats blind for the study's purpose, at a known coherence cost (the hand-chosen per-ride $\varepsilon$ shades into per-ride fitting; the fully frozen re-run of [§3.1](#3.1) is the check, and the ≈ 3–5-point shift on the proposed-form/simulation pair bounds, in-sample, what the judgment buys). Model *selection* — the correction chain, the $\tau = 2$ m threshold, the choice of forms 3–4 — was itself performed on the calibration corpus, so D1's numbers (and even its blind re-run, which inherits the selected forms) carry selection optimism the other corpora do not. The defense is structural: D3–D5 never touched the selection process and serve as the held-out validation set, which is why the pooled D3–D5 figure — not the calibration one — is this paper's headline accuracy claim. All accuracy figures are conditioned on each ride's measured power inputs and a data-implied or logged mass: they measure the consistency of the energy accounting, not blind prediction, which additionally requires a power model. The evidence base is **broad in conditions but narrow in riders**. Within the corpora, terrain and context vary as widely as the region allows — urban stop-go group rides, 200 km-class brevets, gravel and rough surfaces (the informed run's per-ride $C_{rr}$ spans 0.004–0.020), rain and wind (air density 1.01–1.22 kg/m³, head/tailwinds −7 to +5 km/h), solo and group riding — and the law holds across that spread. The rider sample, by contrast, is three people in one metropolitan region, all conventional road-position cyclists with power meters, and the transfer evidence rests on exactly two of them: "transfers across riders" therefore means *consistency over a very small sample*, not a population estimate. Vehicle classes outside the sample could shift the deficit constant or worse — recumbents change the drag regime that sets $s_*$; e-bikes break the leg-energy accounting outright unless motor output is metered separately; and descent habit itself may track gearing, position, or riding culture ([§3.2](#3.2)). The $\varepsilon$ correlations on the calibration corpus are in-sample and part–whole (we lead with error reductions for that reason). The headline numbers use literature-typical prior physics; the fitted-physics rerun ([§3.4](#3.4)) shows the law's accuracy and the deficit's recurrence survive that choice, but the dynamic estimator's margin over a flat constant and one rider's gap value do not — so the transferable content is the law, the regime rule, and the deficit's recurrence, not the 34% figure. The deficit's recurrence is consistency-across-riders rather than three independent confirmations, since its sign is structural. The behavioural constants are tied to the 30 m elevation-sampling scale ([§4.4](#4.4)).

<a id="4.4"></a>

### 4.4 Further developments

Four directions of future research extend this work. The first two already carry preliminary results in the project's lab journal; the last two are designed but not yet executed.

#### A time dual

Defining an effective flat distance $x^* = x + k_+ h_+ - k_- h_-$ — extending the equivalent-distance idea of Scarf & Grehan [2005] to descents — makes $k_-$ the time-image of $\varepsilon$, inter-derivable through the shared descent power. Tested on measured moving times, the ascent half transfers to an unseen rider (6.6% [5.9, 7.2] median vs a 7.6% [7.0, 8.5] naive baseline; sign test $p = 0.012$ on 243 of 433 rides at the data-implied mass, though the paired advantage is mass-sensitive — the win rate decays toward chance and the test loses significance at the top of a 70/74.5/78 kg sweep — while the 6.6% level itself is mass-robust). The descent bridge, like $\varepsilon$'s residual, is behaviour-limited.

#### The coasting deficit: constancy questioned, and the hypotheses already spent

The [§1.3](#1.3) hypothesis — that the shortfall from the coasting ideal is one constant — survived the route-geometry explanations we could test ([§3.2](#3.2)) but not two dependencies: the elevation-sampling scale ($c$, $\varepsilon_0$ and the climb threshold are all functions of the sampling interval and terrain regime, so a 5 m-DEM deployment over-charges relative to the 30 m calibration scale unless they are re-fitted or the raster pre-smoothed) and the assumed physics ([§3.4](#3.4)). The refined statement to carry forward: the deficit's *recurrence* is robust, its *value* is conditional on scale and physics. The open work is threefold. First, the untested candidates — route-side (surface roughness, junction density, sight lines, weather) and rider-side (bicycle setup, gearing, riding position, regional riding culture). Second, a scale-aware $\varepsilon_0(\Delta x)$ that would let one calibration serve several deployment resolutions. Third, a *grade-resolved* deficit. The balance form of [Appendix A](#appendix-a) makes the deficit's identity exact on real descents: $\delta = E_{\mathrm{legs},-}/(\beta\,h_-)$ — the descent pedal energy over the scaled drop — which factorizes into pedalling *occupancy* × pedal *intensity* ÷ released gravitational power, each observable in the power stream. If the deficit is residual pedalling, occupancy should fade on descents too steep to pedal into — an S-shaped pedalling-probability curve, $\varepsilon_0 \cdot g(\bar s)$ with logistic $g$, replacing the constant (with a dilution null to beat first: the same pedalling divided by more gravitational power fades $\propto 1/(\bar v \bar s)$ even at constant behaviour). That form would also retire the negative-prediction region structurally: as $g \to 0$ the estimator returns to the non-negative coasting limit, with the published constant as the $g \equiv 1$ special case. A first exploratory cut finds the grade-dependence real but *rider-conditional in sign* — the deficit fades with grade for two riders and rises for the third — so the curve's parameters are rider- and context-level, not universal; a pre-registered per-rider fit with a held-out test is the registered next step (lab journal, Entry 34).

#### Per-rider physics without circularity

The physical constants are literature-typical priors by design ([§2.3](#2.3)): fitting $C_{rr}$ or $C_dA$ to the same ride energies the models are scored on would let the parameters absorb modelling error, making the accuracy figures partly self-fulfilling. The estimator available today — the virtual-elevation family [Chung 2012] — reads $C_dA$ from fast, flat segments, where riders are tucked or drafting, so it recovers the aero-position value rather than the whole-ride average; used as a model input it *worsens* prediction (P. Paz's bias flips +5.0 → −6.9, [Table 4](#tab4)). The sensitivity map of [§3.4](#3.4) turns that risk from argument into measurement: the would-be gains from moving the constants are signed-bias cancellations pointing in different corners for different riders and variants — there is no common better direction to tune toward. What remains, therefore, are the routes that bring *external* information. One is per-ride inference from sources *other than* the energy target: archived weather for the wind, map surface tags for $C_{rr}$ — the [§3.1](#3.1) informed-parameters run bounds, in-sample, what such condition knowledge is worth (≈ 3–5 points on the proposed-form/simulation pair), and the transfer corpora, equally heterogeneous but judgment-less, are where it would pay. Another is data separation: constants fitted on one slice of a rider's history — or on dedicated coast-down or loop protocols — and scored on another. The other is fully experimental — reproduce the analysis under conditions where all four constants are precisely *known*: a weighed rider and bike, tyres with bench-measured $C_{rr}$ on a known surface, a measured drag area, logged weather. That removes the priors from the error budget entirely, at the cost of controlled rides replacing found ones. All three routes fold naturally into the blind-prediction protocol below.

#### Blind prediction

Closing the gap between accounting consistency and true route forecasting requires a pre-registered protocol with the rider's power model held out; this is planned.

## 5. Conclusions

A closed form with a handful of physical constants and three calibrated numbers accounts for the measured mechanical energy of real routes as well as a forward simulation does — 3.5% [2.0, 5.6] median error on the calibration corpus with condition-informed per-ride parameters (simulation: 5.2% [3.8, 7.3]), 8.2% vs 8.4% re-run blind under one shared constants set, and — pooled over the two independent riders' 660 frozen rides — 5.6% [5.2, 6.2] against the simulation's 6.3% [5.8, 6.8] (5.9% vs 6.2% with the author's in-sample history added; 3.5–6.2% per corpus on those corpora, 6.4–7.7% on the frozen urban test) — across 1,285 unique rides and three riders. Its two historical failure modes are identified and cheap to fix: gate the aero term off climbs, and subtract ≈ 3 m of phantom ascent per kilometre. Descent recovery, the term the literature leaves unspecified, decomposes into a parameter-free geometry — the coasting limit $\min(1,(\alpha/\beta)/s)$ — and a single behavioural constant, the coasting deficit — $\varepsilon_0 = 0.13$ at the literature priors and the 30 m sampling scale, 0.12–0.19 across plausible physics — whose *recurrence* across riders, positive throughout the plausible region of the sensitivity sweep, is the study's most portable empirical fact; its *value* is conditional, and travels only with its priors and scale. The law runs per-edge in a router at the sampling scale it was calibrated on, and runs on paper for everyone else. What it does not yet do is predict a ride before it is ridden — that requires a power model and a pre-registered blind test, and is the natural next step.

## Data and code availability

All analysis code, the forward simulator, the parsers, the per-entry lab journal, its executable mirror, and the statistical gate battery are public at `github.com/danlessa/bicycling-energy-model` (stdlib-only Python; no build step). Per-ride GPS tracks and the independent riders' exports are private by design (shared with consent, never committed); every published number regenerates from one documented harness command per dataset, and a bootstrap gate script fails loudly if any published median stops reproducing.

## AI-assistance declaration

The analysis harnesses, the lab journal's bookkeeping, and drafts of this text were produced with substantial LLM assistance (Anthropic Claude), under continuous author direction and review; all data collection, modelling decisions, calibration choices, and final claims are the author's. The full provenance — including mistakes caught and corrected — is preserved in the public lab journal.

## References

- **[Ahmadi et al. 2024]** Ahmadi, S., Tack, G., Harabor, D., Kilby, P. & Jalili, M. (2024). *Efficient Energy-Optimal Path Planning for Electric Vehicles Considering Vehicle Dynamics.* arXiv:2411.12964.
- **[Bigazzi & Lindsey 2019]** Bigazzi, A. & Lindsey, R. (2019). *A utility-based bicycle speed choice model with time and energy factors.* Transportation 46(3):995–1009.
- **[Chung 2012]** Chung, R. (2012). *Estimating CdA with a power meter* (the "virtual elevation" method). Technical note. <http://anonymous.coward.free.fr/wattage/cda/indirect-cda.pdf>
- **[Dahmen et al. 2011]** Dahmen, T., Byshko, R., Saupe, D., Röder, M. & Mantler, S. (2011). *Validation of a model and a simulator for road cycling on real tracks.* Sports Engineering 14(2–4):95–110. <https://www.uni-konstanz.de/mmsp/pubsys/publishedFiles/DaSa11.pdf>
- **[di Prampero et al. 1979]** di Prampero, P. E., Cortili, G., Mognoni, P. & Saibene, F. (1979). *Equation of motion of a cyclist.* J. Appl. Physiol. 47(1):201–206.
- **[Martin et al. 1998]** Martin, J. C., Milliken, D. L., Cobb, J. E., McFadden, K. L. & Coggan, A. R. (1998). *Validation of a Mathematical Model for Road Cycling Power.* J. Appl. Biomech. 14(3):276–291.
- **[Menaspà et al. 2014]** Menaspà, P., Impellizzeri, F. M., Haakonssen, E. C., Martin, D. T. & Abbiss, C. R. (2014). *Consistency of Commercial Devices for Measuring Elevation Gain.* Int. J. Sports Physiol. Perform. 9(5):884–886.
- **[Perger & Auer 2020]** Perger, T. & Auer, H. (2020). *Energy efficient route planning for electric vehicles with special consideration of the topography and battery lifetime.* Energy Efficiency 13:1705–1726.
- **[Rapaport 2011]** Rapaport, D. C. (2011). *Evaluating cumulative ascent: Mountain biking meets Mandelbrot.* Int. J. Mod. Phys. C 22(3):209–217.
- **[Scarf & Grehan 2005]** Scarf, P. & Grehan, P. (2005). *An empirical basis for route choice in cycling.* J. Sports Sci. 23(9):919–925.
- **[Yuan et al. 2024]** Yuan, X. et al. (2024). *Data-driven evaluation of electric vehicle energy consumption for generalizing standard testing to real-world driving.* Patterns 5(4):100950.

## Appendix A — Deriving the four forms from the route-energy integral

<a id="appendix-a"></a>

**A.1 The exact integral.** Integrating the power balance of [§2.1](#2.1) over a route of length $x$ gives the wheel-level work–energy identity

$$k_{\mathrm{eff}}\,E \;=\; \underbrace{C_{rr}\,m g \int_0^x \cos\theta\,dx'}_{W_{rr}} \;+\; \underbrace{\tfrac{1}{2}\rho\,C_dA \int_0^x v^2\,dx'}_{W_{\mathrm{aero}}} \;+\; \underbrace{m g\,(h_+ - h_-)}_{W_{\mathrm{grav}}} \;+\; W_{\mathrm{brake}} \;+\; \Delta KE,$$

where $\theta$ is the local slope angle, $v(x')$ the actual speed profile, $W_{\mathrm{brake}}$ the energy dissipated in the brakes, and $\Delta KE$ the net change of kinetic energy. (The simulation asserts this identity per ride to $\leq 10^{-6}$ relative.) Three simplifications are near-exact at bicycle grades: $\cos\theta \approx 1$ (error < 0.5% below 8%); $\Delta KE \approx 0$ for a rest-to-rest ride (the kinetic term telescopes); and the split of $W_{\mathrm{grav}}$ into a climb payment $m g\,h_+$ and a descent release $m g\,h_-$.

**A.2 Form 1 — one reference speed and a lumped refund.** Two moves produce $E_1$. First, replace the unknown speed profile by the flat reference speed, $v(x') \to v_f$, so $W_{\mathrm{aero}} \approx \tfrac{1}{2}\rho C_dA\,v_f^2\,x$ and the first two integrals collapse to $\alpha\,x$ with $\alpha = (C_{rr} m g + \tfrac{1}{2}\rho C_dA v_f^2)/k_{\mathrm{eff}}$. Second, absorb the descent-specific losses into a recovery factor. On a descent segment $i$ with horizontal length $\Delta x_i$, drop $h_i$ and actual speed $v_{d,i}$, those losses are

$$W_{\mathrm{waste},i} \;:=\; \underbrace{\tfrac{1}{2}\rho\,C_dA\,\big(v_{d,i}^2 - v_f^2\big)\,\Delta x_i}_{\text{drag in excess of the flat-reference bill}} \;+\; \underbrace{W_{\mathrm{brake},i}}_{\text{braking}}.$$

Define the segment's recovery as the fraction of the released potential energy $mg\,h_i$ that escapes those losses — the share that instead does useful work, covering rolling and air resistance the rider would otherwise pay with the legs:

$$\varepsilon_i \;:=\; 1 - \frac{W_{\mathrm{waste},i}}{mg\,h_i}.$$

This waste form can be turned into a balance a power meter can measure. Writing $E_{\mathrm{legs},i}$ for the pedal energy actually spent on the segment ($\int P\,dt$ restricted to it), the segment's own energy balance is $k_{\mathrm{eff}}E_{\mathrm{legs},i} = C_{rr}mg\,\Delta x_i + \tfrac{1}{2}\rho C_dA\,v_{d,i}^2\,\Delta x_i + W_{\mathrm{brake},i} + \Delta KE_i - mg\,h_i$, where $\Delta KE_i$ is the segment's kinetic-energy change — it telescopes away within a contiguous descent but leaves a net entry/exit boundary term, so the identities below hold up to that term (dropped hereafter for clarity; it is why $\varepsilon_{\mathrm{bal}}$ aggregates all descent cells into one ride-level quotient, where the entry/exit speeds are ordinary riding speeds, rather than forming per-cell recoveries). Substituting into $W_{\mathrm{waste},i}$ gives

$$mg\,h_i - W_{\mathrm{waste},i} \;=\; \underbrace{C_{rr}mg\,\Delta x_i + \tfrac{1}{2}\rho C_dA\,v_f^2\,\Delta x_i}_{k_{\mathrm{eff}}\,\alpha\,\Delta x_i} \;-\; k_{\mathrm{eff}}E_{\mathrm{legs},i},$$

with $\alpha$ and $\beta$ the rates of [§1.2](#1.2). Dividing by $mg\,h_i = k_{\mathrm{eff}}\,\beta\,h_i$ cancels $k_{\mathrm{eff}}$ and leaves

$$\varepsilon_i \;=\; \frac{\alpha\,\Delta x_i - E_{\mathrm{legs},i}}{\beta\,h_i}$$

— equivalently, the leg energy the descent saves versus riding $\Delta x_i$ on the flat, as a fraction of the released potential energy. Rearranged, each descent segment (writing $h_{-,i} = h_i$ for its drop) pays $E_{\mathrm{legs},i} = \alpha\,\Delta x_i - \varepsilon_i\,\beta\,h_{-,i}$: the flat bill minus its own credit. Summing leg energy over all segments (flats and climbs pay $\alpha\,\Delta x + \beta\,\Delta h_+$ under the $v_f$ lump) gives

$$E \;=\; \alpha\,x + \beta\,h_+ - \beta\sum_i \varepsilon_i\,h_{-,i}$$

— already the three-term law, except the credit is a sum. Writing it as $\varepsilon\,\beta\,h_-$ with a single scalar and $h_- = \sum_i h_{-,i}$ forces

$$\varepsilon \;=\; \frac{\sum_i \varepsilon_i\,h_{-,i}}{\sum_i h_{-,i}}:$$

the **drop-weighted** average is not a modelling choice but the unique scalar for which $E_1$ is exact — the weight is the drop $h_{-,i}$ because that is what each $\varepsilon_i$ multiplies. Aggregated over a ride this is the measured balance of [§2.2](#2.2), $\varepsilon_{\mathrm{bal}} = (\alpha x_- - E_{\mathrm{legs},-})/(\beta h_-)$ with $x_- = \sum_i \Delta x_i$. Form 1's remaining error therefore sits entirely in the $v_f$ lump and in the raw elevation totals — which is what forms 2–4 remove.

**A.3 Form 2 — reprice the climbs.** On an ascent-dominated grade ($s > s_*$) the quasi-steady speed follows from the power balance with aero small, $v_c \approx k_{\mathrm{eff}} P / (m g\,(C_{rr} + s))$, far below $v_f$ — so charging aero at $v_f$ over the climbing distance $x_+$ over-charges by $\approx \alpha_a x_+$ (the *dominant* error of form 1, [§3.1](#3.1)). Restricting the aero charge to the non-climbing distance removes it:

$$E_2 \;=\; E_1 - \alpha_a\,x_+ \;=\; \alpha_r\,x + \alpha_a\,x_{\mathrm{flat}} + \beta\,(h_+ - \varepsilon\,h_-).$$

The exact repricing would charge climb aero at $v_c$; zeroing it is the closed form's one-parameter-cheaper approximation. The license is asymptotic, not sharp: $v_c^2 \ll v_f^2$ holds well beyond the gate but only partially at the 2% boundary itself — the step gate approximates a smooth transition, and its residual is part of form 2–3's remaining error.

**A.4 Forms 3–4 — measure the ascent that costs work.** The $\Delta KE \approx 0$ simplification holds route-level, but the raw sum $h_+$ silently violates its premise at small scales: a sub-metre up-step inside a roller is paid by momentum — a kinetic fluctuation that telescopes away — and altitude jitter is not lifting work at all [Rapaport 2011]. Both inflate $h_+$ without appearing in $E$; on sustained climbs, where neither exists, the full $\beta\,\Delta h$ is paid with no discount ([§3.1](#3.1)). The deadband filter ($\tau = 2$ m) removes exactly the sub-scale part, giving $\tilde h_\pm$ and form 3. When only totals are known, the observation that jitter accrues per unit *distance* (a per-sample process, not a terrain one; measured 3.1 m/km, [§2.4](#2.4)) linearises the filter into $\tilde h_\pm \approx h_\pm - c\,x$, giving form 4.

**A.5 The coasting limit.** In A.2 the per-segment recovery $\varepsilon_i$ depends on rider behaviour ($v_{d,i}$, braking), not on the grade. Grade-dependence emerges in the limit: the legs can never return energy, $E_{\mathrm{legs},i} \geq 0$ — and both freewheeling and braking leave the legs idle with the same saving $\alpha\,\Delta x_i$. Setting $E_{\mathrm{legs},i} = 0$ in the balance form of $\varepsilon_i$ eliminates the behavioural degrees of freedom, and with $h_i/\Delta x_i = s_i$ what remains is a function of grade alone:

$$\varepsilon_{\mathrm{coast}}(s) \;=\; \min\!\Big(1,\ \frac{\alpha\,\Delta x}{\beta\,h}\Big) \;=\; \min\!\Big(1,\ \frac{s_*}{s}\Big), \qquad s_* = \frac{\alpha}{\beta},$$

the clamp being the flat-band case $s < s_*$: there the rider pedals lightly to hold $v_f$, saving exactly the gravity assist and no more. Drop-weighting over the profile (or lumping with the mean descent grade $\bar s = h_-/x_-$) gives the route-level estimator of [§1.3](#1.3). Real riders keep $E_{\mathrm{legs},-} > 0$ on descents, so $\varepsilon_{\mathrm{bal}}$ sits below $\varepsilon_{\mathrm{coast}}$ (braking cancels out of the balance — see the Bounds paragraph); the hypothesis that this shortfall is a constant — the coasting deficit $\varepsilon_0$ — is calibrated in [§3.2](#3.2).

**Bounds.** The two sides are asymmetric. The upper bound is a theorem: $E_{\mathrm{legs},i} \geq 0$ gives $\varepsilon_i \leq \varepsilon_{\mathrm{coast}}(s_i)$, always. There is **no physical lower bound** — but not by way of braking: setting $E_{\mathrm{legs},i} = 0$ in the balance form gives $\varepsilon_i = \alpha\,\Delta x_i/(\beta\,h_i) > 0$ *regardless of how much braking occurred*, because brakes dissipate gravity's share of the ledger, never the legs'. (A force-ceiling argument — maximal tyre friction $\mu\,m g\cos\theta$ sustained over the whole descent — would suggest arbitrarily deep negatives, but the energy budget binds long before the friction limit: sustaining that force without pedal input stops the bike within metres.) Negative recovery therefore requires $E_{\mathrm{legs},i} > \alpha\,\Delta x_i$ — pedalling the descent harder than the flat bill — which is legs-funded, bounded only by rider power, and observed on a few rides in the calibration corpus. (The braked-away energy is not free for the rider: after the speed drop they re-pedal to regain speed, and that replacement energy does appear in $E_{\mathrm{legs}}$ — on the *following* segments, booked as pedalling, which is exactly how the balance accounts it.) The estimator is accordingly published *unclamped*: $\varepsilon_{\mathrm{coast}} \in [0, 1]$ by construction bounds it to $[-\varepsilon_0,\, 1-\varepsilon_0]$, and it could go negative only where $\varepsilon_{\mathrm{coast}} < \varepsilon_0$ — mean descent grades beyond $s_*/\varepsilon_0 \approx 15\%$, which no ride in any corpus reaches (minimum observed value: $+0.01$). Earlier versions clamped to $[0, 1]$; both halves are provably inert on the data (the top because $\varepsilon_{\mathrm{coast}} \leq 1$ already, the floor because the corpora never trigger it), so every published number is identical either way — the clamp was removed as dead weight, not as a change of model. The *per-edge* realisation deployed in the router keeps its floor: single 30 m edges beyond 15% are common even where ride means are not.
