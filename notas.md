

## Energy Model

### v1


The energy transmitted from a cyclist to the wheels during a segment is approximately:
$$E \approx \alpha x + \beta (h_+ - \epsilon h_-)$$

Where $k_{eff}$ the chain efficiency, x is the horizontal distance, and $h_+$ and $h_-$ are ascent and descent distance. $\alpha$ expresses energy spent per horizontal distance., and $\beta$ expresses energy spent per vertical distance. $\epsilon$ represents how much energy is recovered during descents after excess losses due to wind speed and braking. 

$$\alpha := \frac{m g C_{rr} + \frac{C_d A \rho v_f^2}{2}}{k_{eff}}$$

$m$ is the bicycle+rider mass, g is the gravitational constant, $C_{rr}$ is the rolling resistance, $C_d$ is the drag coefficient, $A$ is the effective frontal area, $\rho$ is the air density and $v_f$ is an estimate of rider speed on pure flats.

$$\beta := \frac{m g}{k_{eff}}$$

### v2

Two refinements to v1, each removing a systematic bias measured against power-meter
rides (see `data/MODEL_COMPARISON_JOURNAL.md`):

$$E \approx \alpha_r\, x + \alpha_a\, x_{flat} + k_h\,k_{smooth}\,\beta\,(h_+ - \epsilon\, h_-),
  \qquad k_h = 1$$

**(i) Split $\alpha$, charge aero only off the climbs.** v1 bills the aero part of
$\alpha$ at the flat speed $v_f$ over the whole distance, but the rider climbs far
slower, so v1 over-charges climbing aero (the dominant error — almost entirely on
climbs). Keep rolling over all of $x$, apply aero only over the non-climbing fraction:

$$\alpha_r := \frac{m g\, C_{rr}}{k_{eff}}, \qquad
  \alpha_a := \frac{C_d A\, \rho\, v_f^2}{2\, k_{eff}}, \qquad
  x_{flat} := x\,(1 - f_{climb}), \qquad
  f_{climb} := \frac{x_+}{x},$$

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
$$k_{smooth} := \frac{h_+^{\text{smoothed}}}{h_+^{\text{raw}}} \approx 0.74\ (\text{2 m deadband}).$$
With only totals, the cheapest estimate is the constant-rate form (spurious ascent is a
per-sample jitter accumulating with *distance*, not terrain):
$$h_+^{\text{corr}} = \max(0,\; h_+ - c\,x), \qquad
  k_{smooth} = 1 - \frac{c\,x}{h_+}, \qquad c \approx 3\ \text{m/km}$$
(measured 3.2 m/km, IQR 2.7–3.8 — calibrate per source). It **auto-adapts**: $\approx 0.89$
on a flat ride (30 m/km, noise floor a big share) and $\approx 0.98$ on a hilly one
(150 m/km, real ascent dominates). Apply the same to $h_-$.

**$k_{smooth}$ applies to the approximate model only** — the canonical simulation tracks
kinetic energy, so it already pays the rollers' momentum correctly and needs no smoothing
(smoothing its elevation is mildly counter-productive).


## Recovery factor $\epsilon$

$\epsilon$ lumps the descent-specific losses that $\alpha$ — charged at the flat
speed $v_f$ — does not carry: the *excess* aerodynamic drag from descending faster
than $v_f$, plus braking. For a descent of grade $s$, define the **local** recovery
as the fraction of that descent's potential energy $\beta h_-$ that is *not* wasted:

$$\epsilon(s) := 1 - \frac{(\text{aero excess} + \text{braking}) \text{ at the speed reached on grade } s}{m g\, h_- / k_{eff}}$$

Equivalently, from the segment energy balance (neglecting the kinetic term, which
telescopes over a rest-to-rest ride),

$$\epsilon(s) = \frac{\alpha\, dx - E_{legs}}{\beta\, h_-},$$

i.e. the leg energy the descent saves versus riding the same horizontal distance
$dx$ on the flat, as a fraction of the released potential energy $\beta h_-$.

A **single** $\epsilon$ for a whole ride is fixed by where $\epsilon$ enters the model
— only through the total credit $\epsilon\,\beta\,H_-$, with $H_- = \sum_i h_{-,i}$.
Matching that total to the sum of the per-descent recoveries gives the
**descent-height-weighted average**:

$$\epsilon = \frac{\sum_i \epsilon(s_i)\, h_{-,i}}{\sum_i h_{-,i}}
          = \frac{1}{H_-}\int_{\text{descents}} \epsilon\big(s(x)\big)\,\big|h'(x)\big|\,dx .$$

The weight is the **vertical drop** $h_-$ (not distance or time), because $\epsilon$
multiplies $\beta h_-$. Steeper, faster descents have lower $\epsilon(s)$ *and*
accumulate drop fastest, so they dominate the average — a single $\epsilon$ is exact
for the total credit but blurs the per-grade spread. Aggregated over a ride it reduces
to $\epsilon = \big(\alpha\,X_- - E_{legs,-}\big) / (\beta\,H_-)$, where $X_-$, $E_{legs,-}$
and $H_-$ are the horizontal distance, leg energy and drop summed over descent segments.


---


## Correcting the climb aero over-charge

The $\alpha x$ term bills aero at the flat speed $v_f$ over the **whole** horizontal
distance, but the rider climbs far slower than $v_f$, so the real climbing aero
(which scales as $v^2$) is much smaller. This makes the approximation systematically
*higher* than the canonical model on any ride with climbing.

Only the **aero** part of $\alpha$ is wrong, and only **on climbs** — the rolling
part $C_{rr}mg\cos\theta\,s = C_{rr}mg\,x$ is exact on any grade. So split

$$\alpha = \alpha_r + \alpha_a,\qquad \alpha_r = \frac{C_{rr}mg}{k_{eff}},\qquad \alpha_a = \frac{\tfrac12 \rho C_d A\, v_f^2}{k_{eff}},$$

keep the rolling term over all of $x$, and apply the aero term only over the
**non-climbing** fraction of the distance:

$$E \approx \alpha_r\,x \;+\; \alpha_a\,x\,f_{\text{flat}} \;+\; \beta\big(h_+ - \epsilon h_-\big),
\qquad f_{\text{flat}} = 1 - \frac{x_+}{x},$$

where $x_+$ is the horizontal distance spent climbing (summed directly from the profile,
or estimated as $x_+ \approx h_+/\bar g$ with a typical climb grade $\bar g$). This zeroes
the climbing aero — a slight over-correction, since the rider does move uphill, but climb
aero is a small share of the total either way.

**Near-exact variant (no simulation).** Instead of zeroing it, charge the uphill aero at
the quasi-steady climb speed. On a climb gravity dominates the resistance, so
$v_c \approx k_{eff}P_{climb}/(mg\,s)$, and per uphill metre

$$\text{aero}_{\text{climb}} = \tfrac12 \rho C_d A\, v_c^2\,dx
\;\approx\; \tfrac12 \rho C_d A\, \frac{(k_{eff}P_{climb})^2}{(mg\,s)^2}\,dx ,$$

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

$$x^* := x + k_+\,h_+ - k_-\,h_- .$$

**Climb term — clean and grade-independent.** On a climb almost all power goes into lifting,
$k_{eff}P_{climb}\approx mg\,v\sin\theta = mg\,\dfrac{dh}{dt}$, so the climb time is just
potential energy over power, $dt = mg\,dh/(k_{eff}P_{climb})$ — it depends on the **vertical
gain, not the road length**. Hence

$$k_+ = \frac{v_f\, m g}{k_{eff}P_{climb}} = \frac{v_f\,\beta}{P_{climb}}$$

(the *energy* coefficient $\beta$ rescaled into time by $v_f/P_{climb}$). A single $k_+$
reproduces total climb time exactly regardless of the grade mix. *(Small caveat: a constant
$k_+$ double-counts the horizontal baseline already in $x$ on gentle climbs; the exact
coefficient is $v_f mg/(k_{eff}P_{climb}) - 1/s$, but the $1/s$ term vanishes where it matters,
on steep climbs.)*

**Descent term — the time-twin of $\epsilon$.** Descent time is *speed*-limited, not
gravity-limited: $t = x_-/v_{desc}$, set by horizontal distance and the (grade-dependent,
$v_{max}$-capped) descent speed. Pinning it to $h_-$ forces $k_-$ to absorb the typical
descent grade, $k_- \approx (1 - v_f/v_{desc})/\bar s$, so $k_-$ is a **lumped, fitted
parameter** — exactly the role $\epsilon$ plays for energy. The two models line up
term-for-term:

| | clean (climb) | lumped (descent) |
|---|---|---|
| **energy** $\;\alpha x + \beta h_+ - \epsilon\,\beta h_-$ | $\beta = mg/k_{eff}$ | $\epsilon$ |
| **time** $\;x + k_+ h_+ - k_- h_-$ | $k_+ = v_f\beta/P_{climb}$ | $k_-$ |

because climbing is gravity-determined (clean physics) and descending is loss-determined
(messy) in **both** domains. With $t = x^*/v_f$ in hand, the average power $\bar P = E/t$
finally behaves everywhere — $\to 0$ on a coasting descent ($E\to0,\,t>0$), and exactly
$\alpha v_f$ (the flat power) on the flat.

If a fitted $k_-$ is unwanted, a **hybrid** keeps both coefficients physical at the cost of
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

$$v_{desc} = \frac{v_f}{1 - k_- s}.$$

From the **energy** side, the model's descent leg-energy per horizontal metre is
$\alpha - \epsilon\,\beta s$, and average power is energy $\times$ speed:

$$\bar P_{desc} = (\alpha - \epsilon\,\beta s)\,v_{desc} \;\Rightarrow\; v_{desc} = \frac{\bar P_{desc}}{\alpha - \epsilon\,\beta s}.$$

Equating the two gives the single relation that ties them together,

$$\frac{v_f}{1 - k_- s} = \frac{\bar P_{desc}}{\alpha - \epsilon\,\beta\,s},$$

so, given $\bar P_{desc}$ and the grade $s$,

$$k_- = \frac{1}{s}\!\left[1 - \frac{v_f}{\bar P_{desc}}(\alpha - \epsilon\,\beta s)\right],
\qquad
\epsilon = \frac{1}{\beta s}\!\left[\alpha - \frac{\bar P_{desc}}{v_f}(1 - k_- s)\right].$$

**Degenerate case — a pure coast.** Set $\bar P_{desc} = 0$: the bridge forces
$\alpha - \epsilon\,\beta s = 0$, i.e. $\epsilon = \alpha/(\beta s)$ — pinned by grade alone,
independent of speed — while $v_{desc}$ (hence $k_-$) is set entirely by the terminal
coasting speed, which $\epsilon$ says nothing about. With no power to bridge them the two
**decouple**: $\epsilon$ becomes purely geometric, $k_-$ purely aerodynamic. They are
inter-derivable only once the legs do measurable work on the descent.

