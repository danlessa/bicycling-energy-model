## Energy Model

### Current (v2)

The required energy for the wheels to ride a route with distance $x$, total ascent $h_+$ and total descent $h_-$ is given by:

$$
E_{wheel} \approx x (\alpha_{r}  +\alpha_{a} (1 - f_+))+\beta (h_+ -\epsilon h_-)
$$

It is assumed that the elevation profile that gives $h_+$ and $h_-$ is filtered out for short climbs up to 2m. For state of the art DEMs, the following approximation can be used in place of smoothening:

$$
E_{wheel} \approx x (\alpha_{r}  +\alpha_{a} (1 - f_+))+\beta k_{s} (h_+ -\epsilon h_-)
$$

The parameters can then be described as follows

- $f_+ := \frac{x_+}{x}$
- $\alpha_r := mg C_{rr}$
- $\alpha_a := \frac{C_d A \rho v_f^2}{2}$
- $\beta := mg$
- $k_s$ (smoothing): $\approx 0.74$ is the **measured 2 m-deadband ratio on recorded
  barometric profiles**. The value for a DEM source (FABDEM / IGC-SP 2010) is not yet measured
  — a first-principles estimate is $\approx 0.8$–$0.9$ (see `research/notes/dem-elevation-comparison.md`).
- $\epsilon$: typically between 10% and 30%
  - Rough geometric estimate $\epsilon \approx \min(1, \frac{\alpha}{\beta \bar{s}})-0.13 \pm 0.1$
    (the $-0.13$ offset is calibrated in-sample on the 44 power rides; on the quasi-independent
    censo set a flat $\epsilon\approx0.20$ did as well or better — see the journal).

$E_{leg} = E_{wheel} / k_{eff}$  (the legs supply more than the wheel receives; $\alpha_r,\alpha_a,\beta$ above are wheel quantities)

### v1

The energy transmitted from a cyclist to the wheels during a segment is approximately:

$$
E \approx \alpha x + \beta (h_+ - \epsilon h_-)
$$

Where $k_{eff}$ the chain efficiency, x is the horizontal distance, and $h_+$ and $h_-$ are ascent and descent distance. $\alpha$ expresses energy spent per horizontal distance., and $\beta$ expresses energy spent per vertical distance. $\epsilon$ represents how much energy is recovered during descents after excess losses due to wind speed and braking.

$$
\alpha := \frac{m g C_{rr} + \frac{C_d A \rho v_f^2}{2}}{k_{eff}}
$$

$m$ is the bicycle+rider mass, g is the gravitational constant, $C_{rr}$ is the rolling resistance, $C_d$ is the drag coefficient, $A$ is the effective frontal area, $\rho$ is the air density and $v_f$ is an estimate of rider speed on pure flats.

$$
\beta := \frac{m g}{k_{eff}}
$$

### v2

Two refinements to v1, each removing a systematic bias measured against power-meter
rides (see `research/notes/MODEL_COMPARISON_JOURNAL.md`):

$$
E \approx \alpha_r\, x + \alpha_a\, x_{flat} + k_h\,k_{smooth}\,\beta\,(h_+ - \epsilon\, h_-),
  \qquad k_h = 1
$$

**(i) Split $\alpha$, charge aero only off the climbs.** v1 bills the aero part of
$\alpha$ at the flat speed $v_f$ over the whole distance, but the rider climbs far
slower, so v1 over-charges climbing aero (the dominant error — almost entirely on
climbs). Keep rolling over all of $x$, apply aero only over the non-climbing fraction:

$$
\alpha_r := \frac{m g\, C_{rr}}{k_{eff}}, \qquad
  \alpha_a := \frac{C_d A\, \rho\, v_f^2}{2\, k_{eff}}, \qquad
  x_{flat} := x\,(1 - f_{climb}), \qquad
  f_{climb} := \frac{x_+}{x},
$$

with $x_+$ the horizontal distance on climbing segments (grade $\ge$ a climb threshold).
This is the closed-form twin of the per-segment correction derived in [Correcting the
climb aero over-charge](#correcting-the-climb-aero-over-charge); the *near-exact* variant
there charges climb aero at the quasi-steady climb speed $v_c$ instead of zeroing it.

**(ii) $k_h = 1$, with a roller/noise smoothing $k_{smooth}$.** On the **sustained** climbs
(mean slope $> 3\%$ over $> 100$ m, where there is no momentum recovery and aero is small)
the rider pays the **full** $mg\,\Delta h/k_{eff}$: measured $\int P\,dt$ equals the expected
gravity+rolling+aero to within 3% (journal Entry 7, 2535 sections over 44 rides). So the
gravity coefficient is **$k_h = 1$** — $\beta h_+$ is correct on real climbing; there is no
uniform discount.

What makes the *raw* $h_+$ over-count $E$ is **not** the real climbs but the rest: short
**rollers** (the preceding descent's momentum carries the rider over the next rise without
paying $mg\,h$) and sub-metre **noise** (altitude jitter, not real climbing). $k_{smooth}
\in(0,1]$ removes that part while keeping sustained climbs intact.

The **right** realisation is a per-segment **deadband** ($\approx 2$ m) on the profile: it
keeps a 100 m climb at full strength and trims sub-$\tau$ undulations — then $h_\pm$ are the
smoothed sums and $k_{smooth}=1$.

The **poor man's** version — estimate the smoothing *without* doing it, for the closed form's
low-compute case (only the totals $h_+,h_-,x$, no per-segment pass) — is a scalar

$$
k_{smooth} := \frac{h_+^{\text{smoothed}}}{h_+^{\text{raw}}} \approx 0.74\ (\text{2 m deadband}).
$$

With only totals, the cheapest estimate is the constant-rate form (spurious ascent is a
per-sample jitter accumulating with *distance*, not terrain):

$$
h_+^{\text{corr}} = \max(0,\; h_+ - c\,x), \qquad
  k_{smooth} = 1 - \frac{c\,x}{h_+}, \qquad c \approx 0.003\ \ (=3\ \text{m/km})
$$

where **$x$ and $h_+$ are both in metres** (as in $\alpha x$), so $c$ is **dimensionless** —
a $\approx 0.3\%$ "noise grade" the DEM/track adds. (Measured 3.2 m/km, IQR 2.7–3.8 —
calibrate per source.) It **auto-adapts**: $k_{smooth} \approx 0.89$ on a flat ride
($h_+/x \approx 30$ m/km, where the noise floor is a big share) and $\approx 0.98$ on a hilly
one ($\approx 150$ m/km, where real ascent dominates). Apply the same to $h_-$.

**$k_{smooth}$ applies to the approximate model only** — the canonical simulation tracks
kinetic energy, so it already pays the rollers' momentum correctly and needs no smoothing
(smoothing its elevation is mildly counter-productive).

## Recovery factor $\epsilon$

$\epsilon$ lumps the descent-specific losses that $\alpha$ — charged at the flat
speed $v_f$ — does not carry: the *excess* aerodynamic drag from descending faster
than $v_f$, plus braking. For a descent of grade $s$, define the **local** recovery
as the fraction of that descent's potential energy $\beta h_-$ that is *not* wasted:

$$
\epsilon(s) := 1 - \frac{(\text{aero excess} + \text{braking}) \text{ at the speed reached on grade } s}{m g\, h_- / k_{eff}}
$$

Equivalently, from the segment energy balance (neglecting the kinetic term, which
telescopes over a rest-to-rest ride),

$$
\epsilon(s) = \frac{\alpha\, dx - E_{legs}}{\beta\, h_-},
$$

i.e. the leg energy the descent saves versus riding the same horizontal distance
$dx$ on the flat, as a fraction of the released potential energy $\beta h_-$.

A **single** $\epsilon$ for a whole ride is fixed by where $\epsilon$ enters the model
— only through the total credit $\epsilon\,\beta\,H_-$, with $H_- = \sum_i h_{-,i}$.
Matching that total to the sum of the per-descent recoveries gives the
**descent-height-weighted average**:

$$
\epsilon = \frac{\sum_i \epsilon(s_i)\, h_{-,i}}{\sum_i h_{-,i}}
          = \frac{1}{H_-}\int_{\text{descents}} \epsilon\big(s(x)\big)\,\big|h'(x)\big|\,dx .
$$

The weight is the **vertical drop** $h_-$ (not distance or time), because $\epsilon$
multiplies $\beta h_-$. Steeper, faster descents have lower $\epsilon(s)$ *and*
accumulate drop fastest, so they dominate the average — a single $\epsilon$ is exact
for the total credit but blurs the per-grade spread. Aggregated over a ride it reduces
to $\epsilon = \big(\alpha\,X_- - E_{legs,-}\big) / (\beta\,H_-)$, where $X_-$, $E_{legs,-}$
and $H_-$ are the horizontal distance, leg energy and drop summed over descent segments.

### Closed form: predicting $\epsilon$ from the route ($\epsilon_{coast}$)

The leg energy on a descent is bounded — the legs can never *return* energy
($E_{legs}\ge 0$) and the recovery can never exceed the released drop ($\epsilon\le 1$).
Setting $E_{legs}=0$ (the rider freewheels, or brakes — both leave the legs idle, and
both give the *same* leg saving $\alpha\,dx$) collapses $\epsilon(s)$ to a function of
**grade alone**:

$$
\epsilon_{coast}(s) = \min\!\Big(1,\ \frac{\alpha\,dx}{\beta\,h_-}\Big) = \min\!\Big(1,\ \frac{\alpha}{\beta\,s}\Big),
\qquad \frac{\alpha}{\beta} = C_{rr} + \frac{\tfrac12\rho C_dA\,(v_f+w)^2}{mg}.
$$

$\alpha/\beta$ is the **flat-resistance grade** — the slope whose gravity exactly balances
flat rolling+aero (so flat riding "feels like" climbing $\alpha/\beta$). The clamp at $1$
is the gentle-descent case $s<\alpha/\beta$: there the rider pedals lightly to hold $v_f$,
saving exactly the gravity assist, so $\epsilon=1$ (not more). Drop-weighted over the
profile, or from totals only:

$$
\epsilon_{coast} = \frac{1}{H_-}\sum_{\text{desc}} h_{-,i}\,\min\!\Big(1,\tfrac{\alpha}{\beta s_i}\Big)
\qquad\text{or, lumped,}\qquad \epsilon_{coast}\approx \min\!\Big(1,\tfrac{\alpha}{\beta\,\bar s}\Big),\ \ \bar s=\tfrac{H_-}{X_-}.
$$

**Empirical test** (44 power rides, predictor vs. the measured
$\epsilon=(\alpha X_- - E_{legs,-})/(\beta H_-)$ on 30 m cells with $\alpha$ at the
*measured* flat speed — `harness/eps_hypothesis.mjs`, Journal Entry 8):

- **The grade law holds where $\epsilon$ matters.** Correlation with the measured
  $\epsilon$ climbs from $0.38$ over all rides to $0.83$ on $\bar s\ge 3\%$ and $0.87$ on
  $\bar s\ge 3.5\%$; descent-energy-weighted ($w=\beta H_-$) it is $0.65$.
- **A near-constant $-0.13$ offset** (residual descent pedalling/braking the coasting
  ideal omits) calibrates it. Working estimator:

$$
\boxed{\ \epsilon \approx \mathrm{clamp}_{[0,1]}\big(\epsilon_{coast} - 0.13\big)\ }
$$

**Per-edge vs. aggregate application.** The estimator above is stated on the drop-weighted
aggregate — one $\epsilon$ per ride. A per-edge realisation (apply the clamp to every
individual segment's $\epsilon_{coast}(s_i) - 0.13$, *then* sum the segment credits — as
`sampasimu`'s `v2Edge` does, since a per-edge graph cost has no natural notion of "the whole
route") is also licensed by the derivation: both forms are linear in the un-clamped
$\epsilon_{coast}(s_i)-0.13$, so they agree **exactly** wherever the clamp doesn't bind. They
diverge only where a route mixes gentle and cliff-steep descents: the aggregate form lets a
long gentle stretch's high $\epsilon_{coast}$ pull the *route-level* offset up before the
clamp floors it at 0, while the per-edge form floors each cliff segment independently —
never letting easy coasting elsewhere "average out" a drop no rider actually coasts down. The
per-edge form is therefore the more physically defensible of the two on mixed profiles; on a
synthetic worst case (a route mostly gentle grade with one short pitch beyond ε's floor grade,
≈14%) the two forms diverge by roughly 10% of the descent-credit term, and the divergence is
invisible on the smooth terrain most rides are made of, where the clamp rarely binds at all.

- **The clamp-to-$1$ limit is reversed on flat terrain.** Gentle rides are pedalled
  *through* the dips, so the measured $\epsilon\to 0$, not $1$ (NS3 Caracaí: predicted
  $\approx0.9$, measured $0.01$). Harmless: those rides carry $\beta H_-\approx 0$ descent
  energy, which is why energy-weighting alone lifts the correlation $0.38\to0.65$.
- **Braking penalties don't survive.** Curviness $\kappa$ (rad/km) and unpaved fraction
  fit with the *wrong sign* — twisty/rough rides are the mountainous ones with real
  sustained descents, so they recover *more*, swamping the corner-braking loss. $\epsilon$'s
  remaining scatter is rider behaviour (pedalling downhill gives measured $\epsilon<0$ on a
  few rides), not route geometry.

*Worked example* (RMC200 Mogi): $\alpha/\beta=0.0202$, $\bar s=3.4\%$ ⇒
$\min(1,\,0.0202/0.0341)=0.59$; minus $0.13$ ⇒ $\mathbf{0.46}$, vs. measured $0.47$.

### Per-edge realisation (v2Edge) — what Simujaules deploys

Routing needs an $O(1)$-local edge cost, so the deployed engine (sampasimu
`energy-worker.js` and its Rust port) evaluates the law **per edge**, with the
recovery recomputed from each edge's *own* grade $s = |dh|/dx$ instead of a
ride-aggregate $\epsilon$ (journal Entries 18–21):

$$
dh \ge 0:\quad \alpha_r\,dx + [s < s_{climb}]\,\alpha_a\,dx + k_s\,\beta\,dh
\qquad
dh < 0:\quad \max\!\big(0,\ \alpha_r\,dx + \alpha_a\,dx - \epsilon(s)\,k_s\,\beta\,|dh|\big)
$$

with $\epsilon(s) = \mathrm{clamp}_{01}\!\big(\min(1,\,(\alpha/\beta)/s) - \epsilon_0\big)$,
$\epsilon_0 = 0.13$. Two structural facts, both load-bearing:

- $\alpha/\beta$ inside $\epsilon(s)$ stays **un-smoothed** ($k_s$ scales only $\beta$):
  $\epsilon$ is a grade-geometry factor, not an energy one.
- The trailing $\max(0,\cdot)$ is **provably dead code** — $\epsilon(s)$ keeps every
  descent edge at or above a strictly positive floor ($0.13\,\alpha\,dx$ in the gentle
  regime, $0.13\,\beta\,|dh|$ in the middle, $\alpha\,dx$ steep); confirmed at
  $+4.6\,$J minimum pre-clamp over 1402 real rides (Entry 18,
  `verify_v2edge_clamp.mjs`).

**Resolution caveat.** The grade-local $\epsilon(s)$ is *resolution-sensitive* in a
way the aggregate is not: at sampling steps $\ll 30\,$m, local grades read steeper,
$\epsilon(s)$ collapses toward 0 on descent edges, and v2Edge over-charges — measured
+9.5% pooled median at 5 m vs +6.3% at 30 m on the deployed IGC-SP raster
(Entry 19; the $-0.13$ was calibrated on **30 m** cells). Deployed mitigations:
$\sigma = 10\,$m raster pre-smoothing at DEM load, and — the decisive lever —
**per-rider calibration** of effective $(C_dA, C_{rr}, k_s)$ on the rider's own
history, which meets a ±5% error / ±2% bias goal on three independent riders
(Entry 20; fitted values are *effective*, not physical). Alternatively the
behavioural trio $(k_s, \epsilon_0, s_{climb})$ re-fitted as a pure 30 m → 5 m
resolution transfer — $k_s = 0.94$, $\epsilon_0 = 0.063$, $s_{climb} = 2.5\%$ —
bridges the gap per-ride on open/hilly terrain but **not** on flat urban terrain:
the trio is a function of (sampling step, terrain regime), not of the step alone
(Entry 21).

**Standing of the two forms** (Entry 22): for *ride energy* the aggregate-$\epsilon$
champion and the canonical simulation are at statistical parity (medians 3.6% vs
5.1% on the longões, overlapping CIs, sign test $p = 0.45$); v2Edge ties the champion
near its native ~30 m grid and is the routing-compatible form.

---

## Correcting the climb aero over-charge

The $\alpha x$ term bills aero at the flat speed $v_f$ over the **whole** horizontal
distance, but the rider climbs far slower than $v_f$, so the real climbing aero
(which scales as $v^2$) is much smaller. This makes the approximation systematically
*higher* than the canonical model on any ride with climbing.

Only the **aero** part of $\alpha$ is wrong, and only **on climbs** — the rolling
part $C_{rr}mg\cos\theta\,s = C_{rr}mg\,x$ is exact on any grade. So split

$$
\alpha = \alpha_r + \alpha_a,\qquad \alpha_r = \frac{C_{rr}mg}{k_{eff}},\qquad \alpha_a = \frac{\tfrac12 \rho C_d A\, v_f^2}{k_{eff}},
$$

keep the rolling term over all of $x$, and apply the aero term only over the
**non-climbing** fraction of the distance:

$$
E \approx \alpha_r\,x \;+\; \alpha_a\,x\,f_{\text{flat}} \;+\; \beta\big(h_+ - \epsilon h_-\big),
\qquad f_{\text{flat}} = 1 - \frac{x_+}{x},
$$

where $x_+$ is the horizontal distance spent climbing (summed directly from the profile,
or estimated as $x_+ \approx h_+/\bar g$ with a typical climb grade $\bar g$). This zeroes
the climbing aero — a slight over-correction, since the rider does move uphill, but climb
aero is a small share of the total either way.

**Near-exact variant (no simulation).** Instead of zeroing it, charge the uphill aero at
the quasi-steady climb speed. On a climb gravity dominates the resistance, so
$v_c \approx k_{eff}P_{climb}/(mg\,s)$, and per uphill metre

$$
\text{aero}_{\text{climb}} = \tfrac12 \rho C_d A\, v_c^2\,dx
\;\approx\; \tfrac12 \rho C_d A\, \frac{(k_{eff}P_{climb})^2}{(mg\,s)^2}\,dx ,
$$

which captures the $(v_c/v_f)^2$ reduction grade-by-grade (steeper $\Rightarrow$ slower
$\Rightarrow$ even less aero), at the cost of one extra input $P_{climb}$. In practice
keep the rolling term in the denominator, $v_c \approx k_{eff}P_{climb}/(C_{rr}mg\cos\theta + mg\sin\theta)$,
and **cap $v_c \le v_f$** so a gentle grade (where rolling/aero, not gravity, set the
speed) keeps the full flat aero instead of an over-large $v_c$.

**Caution — leave descents alone.** Do *not* apply a flat-fraction to the descent aero:
on descents the air resistance is paid by gravity, not the legs, and is already accounted
for inside $(1-\epsilon)\,\beta h_-$. Down-weighting $\alpha_a$ there would double-count.

## Time, and the "effective flat distance"

Energy alone can't forecast **time**: $t = E/P$ is degenerate on a descent, where the leg
energy $E\to 0$ *and* the descent power $P\to 0$. Time is $\int ds/v$, a different quantity,
so it needs its own model. Define an **effective flat distance** $x^*$ and read the time off
the flat speed, $t = x^*/v_f$, with the same skeleton as the energy law:

$$
x^* := x + k_+\,h_+ - k_-\,h_- .
$$

**Climb term — clean and grade-independent.** On a climb almost all power goes into lifting,
$k_{eff}P_{climb}\approx mg\,v\sin\theta = mg\,\dfrac{dh}{dt}$, so the climb time is just
potential energy over power, $dt = mg\,dh/(k_{eff}P_{climb})$ — it depends on the **vertical
gain, not the road length**. Hence

$$
k_+ = \frac{v_f\, m g}{k_{eff}P_{climb}} = \frac{v_f\,\beta}{P_{climb}}
$$

(the *energy* coefficient $\beta$ rescaled into time by $v_f/P_{climb}$). A single $k_+$
reproduces total climb time exactly regardless of the grade mix. *(Small caveat: a constant
$k_+$ double-counts the horizontal baseline already in $x$ on gentle climbs; the exact
coefficient is $v_f mg/(k_{eff}P_{climb}) - 1/s$, but the $1/s$ term vanishes where it matters,
on steep climbs.)*

**Descent term — the time-twin of $\epsilon$.** Descent time is *speed*-limited, not
gravity-limited: $t = x_-/v_{desc}$, set by horizontal distance and the (grade-dependent,
$v_{max}$-capped) descent speed. Pinning it to $h_-$ forces $k_-$ to absorb the typical
descent grade, $k_- \approx (1 - v_f/v_{desc})/\bar s$, so $k_-$ is a **lumped, free
parameter** — exactly the role $\epsilon$ plays for energy. (The time model is now tested
against measured ride *times* on all three datasets — `time_compare.mjs`, journal Entry 13.
Split verdict: the ascent term $k_+$ transfers across riders, but the $\epsilon\!\leftrightarrow\!k_-$
bridge does *not* predict measured descent speed, so $k_-$ stays **free and corpus-dependent**,
not derived — real descents are behaviour/$v_{max}$-limited, not equilibrium-limited.)
The two models line up term-for-term:


|                                                           | clean (climb)              | lumped (descent) |
| --------------------------------------------------------- | -------------------------- | ---------------- |
| **energy** $\;\alpha x + \beta h_+ - \epsilon\,\beta h_-$ | $\beta = mg/k_{eff}$       | $\epsilon$       |
| **time** $\;x + k_+ h_+ - k_- h_-$                        | $k_+ = v_f\beta/P_{climb}$ | $k_-$            |

because climbing is gravity-determined (clean physics) and descending is loss-determined
(messy) in **both** domains. With $t = x^*/v_f$ in hand, the average power $\bar P = E/t$
finally behaves everywhere — $\to 0$ on a coasting descent ($E\to0,\,t>0$), and exactly
$\alpha v_f$ (the flat power) on the flat.

If a free $k_-$ is unwanted, a **hybrid** keeps both coefficients physical at the cost of
the symmetry: $x^* = x_{\text{flat}} + k_+ h_+ + (v_f/v_{desc})\,x_-$ (climb on vertical,
descent on horizontal). And with the full profile, the exact form is just the per-segment
integral $t = \sum dx / v(s)$.

### Linking $\epsilon$ and $k_-$

The energy knob $\epsilon$ and the time knob $k_-$ are **not** derivable from each other on
their own — but they become so through one bridge, the **descent power** $\bar P_{desc}$,
which is exactly what one expects since $\epsilon$ is an *energy* fudge, $k_-$ is a *time*
fudge, and $\text{power} = \text{energy}/\text{time}$ is the exchange rate between them.

Both encode the same hidden descent speed $v_{desc}$, read off two ways. From the **time**
side, the descent's effective distance $x_-(1 - k_- s)$ must take the real time $x_-/v_{desc}$:

$$
v_{desc} = \frac{v_f}{1 - k_- s}.
$$

From the **energy** side, the model's descent leg-energy per horizontal metre is
$\alpha - \epsilon\,\beta s$, and average power is energy $\times$ speed:

$$
\bar P_{desc} = (\alpha - \epsilon\,\beta s)\,v_{desc} \;\Rightarrow\; v_{desc} = \frac{\bar P_{desc}}{\alpha - \epsilon\,\beta s}.
$$

Equating the two gives the single relation that ties them together,

$$
\frac{v_f}{1 - k_- s} = \frac{\bar P_{desc}}{\alpha - \epsilon\,\beta\,s},
$$

so, given $\bar P_{desc}$ and the grade $s$,

$$
k_- = \frac{1}{s}\!\left[1 - \frac{v_f}{\bar P_{desc}}(\alpha - \epsilon\,\beta s)\right],
\qquad
\epsilon = \frac{1}{\beta s}\!\left[\alpha - \frac{\bar P_{desc}}{v_f}(1 - k_- s)\right].
$$

**Degenerate case — a pure coast.** Set $\bar P_{desc} = 0$: the bridge forces
$\alpha - \epsilon\,\beta s = 0$, i.e. $\epsilon = \alpha/(\beta s)$ — pinned by grade alone,
independent of speed — while $v_{desc}$ (hence $k_-$) is set entirely by the terminal
coasting speed, which $\epsilon$ says nothing about. With no power to bridge them the two
**decouple**: $\epsilon$ becomes purely geometric, $k_-$ purely aerodynamic. They are
inter-derivable only once the legs do measurable work on the descent.
