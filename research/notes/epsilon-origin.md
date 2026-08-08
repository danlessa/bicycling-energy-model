# The origin of ε: from the canonical dynamical system to F1–F5

*A derivation note. The canonical simulation is the ground truth every closed
form approximates; this note shows how ε — the descent-recovery factor — is
not a bolted-on fudge but a quantity the dynamics itself defines, and how each
form F1–F5 corresponds to keeping progressively more of the dynamical
structure. Companion to `original_notes.md` (the closed form's spec) and paper
1's Appendix A (whose equation numbers A1–A9 are cited where they coincide);
the experimental status of each claim traces to the lab journal entries named
in place. Numbers quoted at the shared constants ($m$ = 75 kg, $C_{rr}$ =
0.008, $C_dA$ = 0.40 m², $\rho$ = 1.13 kg/m³, $k_{\mathrm{eff}}$ = 0.98,
$g$ = 9.7864 m/s², $P$ = 100 W) unless stated.*

---

## 1. The canonical system and its invariant structure

The forward model (`engines.py canonical`) marches the force balance over
distance:

$$m\,v\,\frac{dv}{ds} \;=\; \frac{k_{\mathrm{eff}}\,P(s)}{v}
\;-\; C_{rr}\,m g\cos\theta \;-\; \tfrac12\rho C_dA\,(v+w)\lvert v+w\rvert
\;-\; m g\sin\theta,$$

with per-regime pedal power $P(s)$ (climb/flat/descent by grade), a brake that
caps kinetic energy at $\tfrac12 m v_b^2$, and leg energy
$E = \int P\,dt$. Integrated over a ride it yields the exact ledger (A1),
asserted per ride to $10^{-6}$ relative:

$$k_{\mathrm{eff}}\,E \;=\; W_{rr} + W_{\mathrm{aero}} + W_{\mathrm{grav}}
+ W_{\mathrm{brake}} + \Delta KE.$$

Everything that follows is bookkeeping on this identity. The dynamical
structure that matters is the system's **branch fixed points** and the
**boundary layers** between them:

- **Flat branch.** With $P = P_{\mathrm{flat}}$, $\theta = 0$, the stable
  fixed point is the flat equilibrium speed $v_f$ solving
  $(C_{rr} m g + \tfrac12\rho C_dA v_f^2)\,v_f = k_{\mathrm{eff}} P$
  (`flatEqSpeed`). Linearising about it, a speed excess decays as
  $e^{-s/L_{\mathrm{rec}}}$ with the **recovery length**

  $$L_{\mathrm{rec}} \;=\; \frac{m\,v_f^2}{C_{rr} m g
  + 3\cdot\tfrac12\rho C_dA\,v_f^2} \;\approx\; 92\ \mathrm{m}$$

  (the 3: at fixed power both the $P/v$ term and the drag steepen the
  restoring force, $d(v^3)/dv = 3v^2$; aero-dominated limit
  $2m/3\rho C_dA \approx 111$ m). Simulated: a 5% descent exited at 42 km/h
  takes 260 m / 30 s to re-enter ±10% of $v_f$, tail e-folding 94 m.
- **Climb branch** ($s > s_*$, see §2). Gravity dominates; the quasi-steady
  speed $v_c \approx k_{\mathrm{eff}} P / (m g\,(s + C_{rr})) \ll v_f$, aero
  negligible, relaxation fast. The profile is quasi-steady on any sustained
  climb.
- **Descent branch.** Coasting ($P = 0$), the terminal speed is
  $v_t(s) = \sqrt{m g\,(\sin\theta - C_{rr}\cos\theta)\,/\,\tfrac12\rho C_dA}$
  — 40–42 km/h at 5% — behaviourally capped at $v_b$ where terrain allows
  more. Approach length $\sim m/\rho C_dA \approx$ 170–330 m.
- **Boundary layers.** At every branch change the trajectory carries kinetic
  energy across. In height units the carried surplus is the **KE buffer**

  $$h_{KE} \;=\; \frac{v_{\mathrm{fast}}^2 - v_{\mathrm{slow}}^2}{2g}
  \;\approx\; 5\text{–}9\ \mathrm{m}$$

  (descent exit → climb: $(v_e^2 - v_c^2)/2g$; flat → climb:
  $(v_f^2 - v_c^2)/2g \approx 2$ m). This is Entry 37's "suspension travel".

So the canonical speed profile is: plateaus at branch fixed points, stitched
by exponential boundary layers of length $\sim L_{\mathrm{rec}}$, carrying
$\sim h_{KE}$ of energy in height units. **Every closed form is a statement
about how much of this structure to keep.**

## 2. Defining ε — the descent ledger

Integrate the ledger over one descent segment (drop $h$, horizontal length
$\Delta x$). The rider's legs may idle there while gravity pays resistance and
the brake bleeds the excess. Define the segment's waste (A2) as the drag paid
in excess of the flat-reference bill plus the braking, and the **recovery**
as the released potential energy's escape from that waste (A3):

$$\varepsilon_i \;:=\; 1 - \frac{W_{\mathrm{waste},i}}{m g\,h_i}
\qquad\Longleftrightarrow\qquad
\varepsilon_i \;=\; \frac{\alpha\,\Delta x_i - E_{\mathrm{legs},i}}{\beta\,h_i}
\quad\text{(A5, the balance form)},$$

with $\alpha = (C_{rr} m g + \tfrac12\rho C_dA v_f^2)/k_{\mathrm{eff}}$ the
flat cost rate and $\beta = m g / k_{\mathrm{eff}}$ the climb rate. Read it as
a ledger: *the leg energy a descent saves versus riding its length on the
flat, as a fraction of the released potential energy.* Each descent then pays
$E_{\mathrm{legs},i} = \alpha\,\Delta x_i - \varepsilon_i\,\beta\,h_i$, and
summing the route forces the unique scalar for which the law is exact — the
drop-weighted mean (A7):

$$\varepsilon \;=\; \frac{\sum_i \varepsilon_i\,h_{-,i}}{\sum_i h_{-,i}}.$$

Nothing here was assumed about behaviour: ε is *defined* by the dynamics'
energy ledger, and a power meter measures it (`eps_from_balance`).

## 3. Interpreting ε — what the dynamics says it must be

**The coasting ceiling (A9).** The legs can never return energy,
$E_{\mathrm{legs}} \ge 0$. Setting $E_{\mathrm{legs}} = 0$ in the balance form
eliminates behaviour and leaves grade alone:

$$\varepsilon_{\mathrm{coast}}(s) \;=\; \min\!\Big(1, \frac{s_*}{s}\Big),
\qquad s_* = \frac{\alpha}{\beta} \approx 2.1\%.$$

Dynamically: riding the descent branch at terminal speed, gravity's release
covers resistance at exactly the rate $\alpha$ per metre — the fraction
$s_*/s$ of the release — and the rest goes to brakes or KE. The clamp is the
flat band ($s < s_*$), where the assist is saved in full.

**The boundary term is where the refund physically travels.** The per-segment
ledger drops an entry/exit $\Delta KE$ (A2's parenthetical). That term is the
buffer of §1: a descent exits carrying $m g\,h_{KE}$ of released PE *in
transit*. Its fate depends on the next branch:

- **into a climb** — collected as free lift: the climb's first $h_{KE}$
  metres are paid by momentum, not legs;
- **into a run-out** — collected against the $\alpha$ bill over
  $\sim 2$–$3\,L_{\mathrm{rec}}$ (the legs pay $P/v < \alpha$ per metre while
  $v > v_f$);
- **into a stop or forced brake** — destroyed. By A6's accounting this is an
  *uncollected refund*, never a charge: brakes dissipate gravity's share of
  the ledger, and the re-purchase of speed appears as pedalling on later
  segments.

**The behavioural deficit.** Measured $\varepsilon_{\mathrm{bal}}$ sits below
$\varepsilon_{\mathrm{coast}}$ because riders pedal downhill
($E_{\mathrm{legs},-} > 0$; the dominant reading) and because interrupted
boundary layers leak refunds into $W_{\mathrm{brake}}$. The constant
$\varepsilon_0 = 0.13$ lumps both; the geometry estimator is
$\varepsilon \approx \varepsilon_{\mathrm{coast}} - \varepsilon_0$. Scale
check: at $v_b$ = 42 km/h a fully-lost buffer costs
$h_{KE}/h_- \approx 10\%$ of a 50 m descent's release — the same order as
$\varepsilon_0$, and it shrinks as $1/h_-$ (a corpus-average constant is a
statement about interruption statistics).

## 4. The ladder: F1–F5 as speed-profile approximations

Each form replaces the true $v(s)$ — plateaus + boundary layers — by
something cruder, and the discarded structure lands in a correction term or
in ε's calibration.

**F1 — one fixed point.** $v(s) \equiv v_f$ everywhere. The two resistance
integrals collapse to $\alpha x$; descent physics is lumped wholesale into ε:

$$E_1 = \alpha\,x + \beta\,(h_+ - \varepsilon\,h_-).$$

Dominant error: climbs are charged aero at $v_f$ although they ride at
$v_c \ll v_f$.

**F2 — two fixed points.** Keep the climb branch: on ascent-dominated grades
($s > s_*$, the same $s_*$ that caps ε — the coincidence is structural, both
mark where gravity carries half the load) aero is repriced from $v_f$ to
$v_c$, approximated as zero:

$$E_2 = \alpha_r\,x + \alpha_a\,x_{\mathrm{flat}}
+ \beta\,(h_+ - \varepsilon\,h_-). \tag{A8}$$

**F3 — acknowledge the boundary layers, unconditionally.** The
$\Delta KE \approx 0$ simplification is false at sub-buffer scale: relief
smaller than $h_{KE}$ is paid by momentum (kinetic fluctuations that
telescope), and altimeter jitter is not lifting work at all. The deadband
filter ($\tau$) produces $\tilde h_\pm$. Traced through one oscillation, the
backlash implementation **annihilates swings under $2\tau$ peak-to-peak and
counts every survivor short by exactly $2\tau$** — i.e. F3's filter is a
*fixed-cap, unconditional realisation of the KE buffer*, with $2\tau$ playing
$h_{KE}$'s role. Matching the ledgers predicts $2\tau(1-\varepsilon) \approx
h_{KE}$, i.e. $\tau^* \approx$ 4–5 m; the A-chain's fitted $\tau$ = 6 m and
the per-rider $\tau^*$ range 4.5–12 m sit at buffer scale, far above the
2 m jitter floor (Entries 38–39, 63–64). The filter also does a second,
non-dynamical job — removing instrument noise — and the two jobs share one
fitted knob.

**F4 — F3 for totals-only consumers.** When only $(x, h_\pm)$ are known, the
removal linearises per distance: $\tilde h_\pm \approx h_\pm - c\,x$
(measured jitter accrual 3.1 m/km; published $c$ = 3 m/km class). Same
physics, one information rung lower.

**F5 — compute the buffer instead of fitting it.** Entry 63's move: keep a
small noise-only deadband $\tau_n$, enumerate the filtered profile's
descent→climb valleys (drop $D$ at grade $s_-$, rise $H$ at $s_+$), and
transfer per valley

$$T = \sum_{\mathrm{valleys}} \min\!\big(D,\ H,\ \max(0,\, h_{KE} - 2\tau_n)\big),
\qquad \tilde h_+ \mathrel{-}= T,\ \ \tilde h_- \mathrel{-}= T,$$

with the buffer built from the branch fixed points of §1:
$h_{KE} = (v_e^2 - v_c^2)/2g$, $v_e = \min(v_b,\ \max(v_t(s_-), v_f))$, and
$v_c$ from the climb branch — the clamp $v_c \le v_e$ makes a
descent-into-run-out toll zero automatically (run-outs collect; only climbs
transfer). The amplitude caps reproduce the deadband's annihilation of
sub-buffer features. Variants: **F5f** freezes $v_b = \infty$ (the data
railed there twice — the cap never binds at these corpora's grades), leaving
ε as the *only* fitted parameter; **F5m** measures $v_b$ per ride from
telemetry (95th-percentile descent speed), moving it into the
$\hat m/\hat C_dA/\hat C_{rr}$ class.

Status (Entries 63–64, same A-chain as paper 1): F5f enters F3's 1-SE band at
$\tau_n$ = 2 m and wins the 1-SE-toward-simpler selection; F5m transfers
better than F3 across riders (leave-one-rider-out, p = 0.044); the filterless
arm ($\tau_n$ = 0) shows toll-alone recovers 53% of the F2→F3 gap,
filter-alone 76%, both 82% — the filter and the toll are ~seven-eighths the
same term, but the deadband is not redundant. F3 keeps the best raw CV and
AIC; ε stays a calibrated constant in paper 1 (§3.2's error budget).

## 5. The ladder at a glance

| form | speed profile kept | gravity term | fitted geometry params |
|---|---|---|--:|
| F1 | one fixed point ($v_f$) | $h_+ - \varepsilon h_-$, raw | — |
| F2 | + climb branch ($v_c$, aero → 0) | same | — |
| F3 | + boundary layers as a fixed cap | $\tilde h_\pm$ (deadband $\tau$) | $\tau$ |
| F4 | F3, totals only | $h_\pm - c\,x$ | $c$ |
| F5 | + buffers computed per valley from fixed points | $\tilde h_\pm(\tau_n) \mp T$ | — (F5f) / $v_b$ (F5) |

Reading the ladder backwards is the interpretation of ε: **ε is the
route-level residue of everything the kept speed profile discards about
descents** — gravity's payment of the α bill (the $s_*/s$ ceiling), the fate
of the boundary-layer buffers (collected, run out, or braked away), and the
rider's downhill pedalling. The more structure a form keeps (F3's cap, F5's
computed buffer), the less ε has to absorb, which is why its fitted value
falls from F1's 0.68 through F2's 0.46 to F3's 0.29 on the same data: the
constant is not a physical propensity but a ledger's remainder, and it
shrinks exactly as the ledger's other lines get their own terms.

---

*Pointers: `original_notes.md` (the closed form's spec); paper 1 Appendix
A.1–A.6 (the ledger, ceiling and bounds); Entry 13 (the time dual and the
$\varepsilon \leftrightarrow k_-$ bridge); Entries 37–40 (the suspension
reading, τ-sweeps, and the roller-band null); Entries 63–64 (+ amendment)
(recovery length, F5/F5f/F5m, the toll-filter overlap decomposition);
`src/harness/e63_f5_kebuffer.py` (the F5 instrument).*
