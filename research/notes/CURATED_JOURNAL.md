# The curated journal — how far can a closed-form energy model go?

This is the **readable companion** to the lab journal
([MODEL_COMPARISON_JOURNAL.md](MODEL_COMPARISON_JOURNAL.md)). The two-journal
rule: the **lab journal is the authoritative record** — verbatim prompts,
pre-registrations, every number, every caveat, newest first. This file retells
the same 24 entries as a story, oldest first, in plain language, keeping only
the numbers that carry the plot. When they disagree, the lab journal wins.
When a new entry lands there, add its retelling here.

Machine-readable versions of everything below: the claims graph
([claims.ttl](claims.ttl), browsable via
[claims-explorer.html](claims-explorer.html)) and one evidence package per
entry ([../packages/](../packages/)).

## The driving question

**Can a closed-form model — one formula, no simulation — predict the energy of
cycling a route, reliably and robustly?** The formula in question:

> E ≈ α·x + β·(h₊ − ε·h₋)
>
> *"Energy is a rolling+air cost per kilometre, plus a price for every metre
> climbed, minus a partial refund for every metre descended."*

The honest current answer, after 24 entries: **yes, with disciplined
corrections and per-rider calibration** — the corrected closed form is
statistically **at parity with a full forward-dynamics simulation** (Entry 22)
at a fraction of the compute, its accuracy transfers to riders it has never
seen (~4–7% median error), and a calibrated deployment meets a pre-registered
±5%/±2% goal (Entry 20). What does *not* transfer: the behavioural pieces —
the descent-recovery *skill* is rider-dependent (Entry 14), the time-model's
descent half is unconfirmed (Entry 13), and the "constants" quietly depend on
the terrain sampling scale (Entries 19–21).

---

## Act I — Building the comparison, finding the champion (Entries 1–7)

*One weekend (2026-06-28). From a naive formula 19% off to a corrected one
that beats the simulation.*

### Entry 1 — The ground rules
**Data:** the 44 longões — the author's long-distance brevet recordings
(FIT/GPX tracks with power meter), out of 52 catalogued rides; parameters
from the rider's own spreadsheet.

Everything is pinned before anything is compared: 44 of the author's 52
long-ride recordings have power meters and tracks; ground truth is the raw
work integral ∫P·dt from the power meter (it matches the rider's own
spreadsheet to ~0.3%); and **both models read the same physical constants**,
so any gap between them is the model's fault, not the parameters'.
[[package]](../packages/entry01/ro-crate-preview.html)

### Entry 2 — First contact: the formula is 19% too expensive
**Data:** the 44 longões tracks.

Out of the box, the forward simulation ("canonical") lands within **5.1%** of
measured energy with no bias. The naive closed form is **+19.2% high on
essentially every ride**. The culprit is obvious in hindsight: the formula
bills air resistance at flat cruising speed over the *whole* ride, but climbs
are ridden slowly, where air resistance is nearly nothing.
[[package]](../packages/entry02/ro-crate-preview.html)

### Entry 3 — Stop charging air on the climbs
**Data:** the 44 longões.

Splitting α into rolling (always paid) and aero (paid only off-climb) roughly
**halves the error: +19.2% → +8.5%**, better on 43 of 44 rides. Interestingly,
charging climbs a *reduced* aero at climbing speed does worse than charging
zero. [[package]](../packages/entry03/ro-crate-preview.html)

### Entry 4 — The second lever is the reference speed
**Data:** the 44 longões, plus the rider's spreadsheet (its `P_flat/P_avg`
column).

The remaining +8.5% mostly traces to v_f, the flat reference speed — the
speed the formula charges air resistance at. Deriving v_f from the ride's
extracted flat power over-estimates how fast the rider actually rode on the
flat; replacing it with the **measured flat speed** — the ride's own average
ground speed over its flat-classified segments (grade between −1.5% and +2%,
stopped samples excluded) — cuts the residual to **+2.7%**.
[[package]](../packages/entry04/ro-crate-preview.html)

### Entry 5 — The elevation data was lying (the champion is born)
**Data:** the 44 longões.

Splitting each ride's energy into its three grade regimes — **climb**
(≥ +2%), **flat**, **descent** (≤ −1.5%) — shows the closed form's error
lives entirely on the climbs (+26.7% there, vs ±4% on the flat). And ~20% of
recorded "ascent" turns out to be sub-3-metre altimeter jitter, which the
linear β·h₊ term pays in full — ~93% of the residual climb over-charge. A
**2 m deadband filter** on the elevation profile fixes it. Applied to the
Entry-3 aero-split form (not the measured-v_f variant of Entry 4), it reaches
**3.4% median error — better than the raw simulation (5.1%)**. This recipe
(aero split + 2 m deadband) is the **champion** every later entry tries to
beat. A twist worth remembering: the same filter mildly *hurts* the
simulation (5.1% → 5.6%) — it is nearly immune to ascent noise, but
smoothing reclassifies micro-climbs as flat and slightly miscounts the power
spent on real undulations.
[[package]](../packages/entry05/ro-crate-preview.html)

### Entry 6 — No elevation source tells the truth
**Data:** the 12 longões inside the São Paulo DEM tile (S24W047), each
sampled against five elevation sources — the recorded barometer, the IGC-SP
5 m aerial survey, FABDEM, COP30, SRTM.

Against the 5 m aerial survey of São Paulo (IGC): the barometer *under*-reads
ascent (−11% raw), satellite surface models *over*-read (SRTM +34%), FABDEM
lands +6%. Rules that stuck: sample DEMs bilinearly (nearest-neighbour adds
~30 pp of staircase artifact), and treat ascent as *bracketed*, not measured.
(The "FABDEM ≈ survey" finding was later shown to hold only on hilly terrain —
see Entry 19.) [[package]](../packages/entry06/ro-crate-preview.html)

### Entry 7 — Climbing has no discount
**Data:** the 44 longões — 2 535 sustained-climb sections (> 3% over
> 100 m).

On sustained climbs (>3% over >100 m) the rider pays the full gravitational
bill: k_h ≈ **0.96–1.0**. So the popular idea of a uniform "climbing discount"
is wrong — sustained climbs cost full price, and all the apparent discount
lives in rollers and noise, which is exactly what the deadband removes. The
lever confirmed: correct the *profile*, not the physics.
[[package]](../packages/entry07/ro-crate-preview.html)

---

## Act II — The descent-recovery puzzle (Entries 8–11)

*What is ε, really? A geometric law with a behavioural offset — and a failed
braking theory.*

### Entry 8 — ε from geometry alone
**Data:** the 44 longões; the "measured" ε per ride is the descent-energy
balance read from each power track.

ε (the descent refund fraction) turns out to be predictable from grade:
coasting recovers `min(1, (α/β)/s̄)` of the descent, minus a near-constant
**−0.13 offset** for real-world braking and descent pedalling. On real
descents this estimator beats any flat constant by **37% RMS**. Two intuitions
died honorably: flat terrain does *not* push ε→1 (riders pedal through dips,
so measured ε→0), and curviness/surface penalties fit with the wrong sign.
[[package]](../packages/entry08/ro-crate-preview.html)

### Entry 9 — First out-of-domain test: the collective's urban rides
**Data:** the censo — 87 activities linked from the collective's ride
census spreadsheet, downloaded and filtered to 62 clean urban power rides.

On 62 urban stop-go rides from the Pedal Hidrográfico censo — different style,
generic assumed rider — all models land **~4–7% median**. The cheap "poor
man's" variant is the best (3.9%), beating the simulation (6.5%). But the
geometric ε over-credits urban descents; a flat **ε ≈ 0.20** works better in
stop-go traffic. The corpus rule is born: geometric ε on open roads, flat 0.20
in the city. [[package]](../packages/entry09/ro-crate-preview.html)

### Entry 10 — The braking theory of urban ε: refuted
**Data:** the 59 clean censo rides carrying a usable descent-balance ε.

The obvious hypothesis — city ε is suppressed by braking density (traffic
lights, corners) — is **wrong**. No braking/stop metric predicts the per-ride
gap (R² ≤ 0.07). The physics reason is elegant: on a descent, gravity refunds
the speed a red light took away, so braking is nearly invisible to *leg*
energy. São Paulo's ε is just a constant.
[[package]](../packages/entry10/ro-crate-preview.html)

### Entry 11 — The adversarial audit
**Data:** no new data — the longões and censo harnesses re-run after each
code fix.

A 13-agent review of everything so far: one privacy purge, a latent
energy-injecting bug that no benchmark ride could reach, a stopped-samples
gate that moved urban ε from 0.14 to 0.23, and one humbling correction — the
celebrated ε correlations (0.83+) were **part–whole artifacts**; the honest
statistic is RMS skill vs a flat baseline (which survives). No headline
conclusion reversed. [[package]](../packages/entry11/ro-crate-preview.html)

---

## Act III — Other riders: what transfers and what doesn't (Entries 12–16)

*The model meets bodies it was never calibrated on.*

### Entry 12 — A second rider
**Data:** P. Paz's full Strava export (shared with consent) — 1 054 files
filtered to 441 clean power rides.

P. Paz (independent rider, own power meter, faster and coastable riding
style) shared 441 rides. With *nothing refit* except mass (inverted from
sustained climbs: 74.3 kg), the energy law lands **4.9% median**, geometric ε
is the best variant, the frozen rider-1 ε estimator beats even P. Paz's own
best flat constant by ~35%, and the −0.13 offset reproduces (0.12). Looks like
a full transfer. (Hold that thought.)
[[package]](../packages/entry12/ro-crate-preview.html)

### Entry 13 — The time model, finally tested
**Data:** all three corpora against measured moving time — 43 longões,
58 censo, 441 P. Paz.

The energy↔time dual (t = x*/v_f with climb/descent distance equivalents) had
never touched measured times. Verdict: **a split**. The ascent half is real
and transfers — the physics-derived k₊ beats even a *fitted* constant on the
new rider (6.6% vs 10.9%). The descent half fails: predicted descent speeds
overshoot reality everywhere, because real descents are limited by nerve and
brakes, not aerodynamic equilibrium. k₋ stays a free, corpus-dependent number.
[[package]](../packages/entry13/ro-crate-preview.html)

### Entry 14 — A third rider breaks the ε skill
**Data:** JAAM's full export (shared with consent) — 1 282 files, 360 power
rides, 219 clean.

JAAM (219 rides, big rider, pedals his descents) confirms the energy law
(3.5–5.4% median) and the 0.13 offset a third time — but the geometric-ε
*skill* fails outright on his gentle rides and is inconclusive on his real
descents. The Entry-12 "35% win" is thus **rider-dependent: it works for
coasters, not for descent-pedalers**. Also corrected here for the record:
P. Paz and JAAM are independent riders, *not* collective members; three
independent riders is the stronger external-validity story anyway.
[[package]](../packages/entry14/ro-crate-preview.html)

### Entry 15 — Can we measure the rider from ride data alone?
**Data:** the clean-fitting activities of all three riders (single-rider
power balance holds, r² > 0.4): P. Paz 123, JAAM 27, author 5.

Yes — all four parameters (mass, CdA, C_rr, per-activity wind) are recoverable
from uncontrolled rides, each by a different trick: mass from braking-free
sustained climbs (JAAM's "implausible" 103 kg turned out to be his real
weight, rider-confirmed); CdA only after modelling wind per activity via a
linearised regression on GPS bearing (naive flat-power fits give *negative*
CdA — riders hold effort, not power). A synthetic-wind self-test caught a
CdA↔wind degeneracy before it could lie.
[[package]](../packages/entry15/ro-crate-preview.html)

### Entry 16 — Fitted physics, and the author's own 1597 rides
**Data:** the author's full Strava export (1 597 power rides → 621 clean),
plus fitted-physics re-runs of the P. Paz and JAAM corpora.

Re-running everything with each rider's *fitted* constants: accuracy is robust
(~4–7% either way), but P. Paz's 35% ε win **collapses to a tie** — the
assumed-high CdA had inflated it. Both independent riders now tie; the
geometric-ε skill adds little beyond a flat constant. The author's full export
validates the mass machinery (71–75 kg vs known ≈73). And a systematic
finding: fitted CdA always comes out ~35% below the assumed 0.40, because
flat-speed fits see the tucked, drafting rider — *effective* constants, not
physical ones. [[package]](../packages/entry16/ro-crate-preview.html)

---

## Act IV — The deployed app under the microscope (Entries 17–21)

*Structure doesn't beat bias-cancellation; resolution is a parameter; and a
pre-registered goal is met.*

### Entry 17 — A cleaner model that isn't better
**Data:** all five corpora — longões 44, censo 62, P. Paz 441, JAAM 219,
author-full 621.

The obvious "improvement" — decompose each ride into flat/climb/descent
segments, each with its own physics and measured power — **loses to the
champion despite using strictly more information**. The reason is the
journal's most reusable lesson: the win/loss is a **bias trade**. The regime
form adds ~+4.6 pp of climb aero the champion deliberately zeroes, so it wins
exactly where the champion under-predicts and loses where it over-predicts. A
causal rerun (swap in fitted constants → bias signs flip → winners flip,
6-for-6) upgraded that from correlation to mechanism. The champion's
"conveniences" *are* load-bearing bias-cancellation. Also learned: evaluate
closed forms on ride **totals**, not per-edge — ε is an aggregate quantity by
construction, and applying it per edge discards its physicality.
[[package]](../packages/entry17/ro-crate-preview.html)

### Entry 18 — Correcting our own attack on the app
**Data:** a 1.78-million-combination synthetic parameter sweep (the proof
needs no ride data), then the five corpora for the deployed-cost scoreboard.

Entry 17 blamed the deployed sampasimu cost function (v2Edge) for a per-edge
over-charge. Wrong target: the app recomputes ε from each edge's *own grade*,
and a proof plus a 1.78M-case sweep shows its descent clamp is **dead code** —
it can never fire. The real story is subtler: grade-local ε is
**resolution-sensitive**. At ~30 m sampling v2Edge ties the champion; at 5 m,
finer grades read steeper, the credit collapses, and it loses. A happy
accident: the app runs at the resolution where its ε is least wrong. (Process
lesson: the misattribution survived review because the harness *named* its
construction after the app — nobody diffed it against the deployed code.)
[[package]](../packages/entry18/ro-crate-preview.html)

### Entry 19 — The 5 m survey is too sharp
**Data:** the 922 rides inside the deployed raster's coverage (58 censo +
277 P. Paz + 181 JAAM + 406 author), each walked on four elevation sources:
barometer, IGC 5 m, IGC resampled to 30 m, FABDEM 30 m.

On the app's own deployed raster (IGC-SP, 5 m), the resolution over-charge is
real: **+9.4 pp** signed gap on urban rides, +3.6 pp pooled across 864
independent-rider rides — the pre-registered threshold fired, putting ~30 m
pre-smoothing on the app's roadmap. Two surprises: the *surveyed* 5 m DTM is
worse than the noisy barometer for urban energy (real micro-relief that graded
roads smooth away gets charged as if ridden); and **FABDEM fails flat
terrain** (+57% median ascent pooled, up to +135%) — Entry 6's "bare-earth
sources agree" held only on hills. For the 300 kJ accessibility mission this
matters directly: today's deployment understates the city's reachable
frontier by ~+9.5% median. [[package]](../packages/entry19/ro-crate-preview.html)

### Entry 20 — The pre-registered goal: PASS
**Data:** the three riders' Entry-19 coverage sets (864 rides), split 50/50
into train/validation by hash; censo excluded by the goal's own terms (group
rides draft).

Can the deployed pipeline hit **±5% error / ±2% bias**? Protocol declared
before any tuning (50/50 hash split, validation evaluated once, fallback
ladder written down): **all three riders pass** (3.69/2.74/4.94% at +0.96/
+0.31/+0.81 bias; the last with 0.06 pp to spare). The honest decomposition:
**calibration is the lever, not smoothing** — a σ=0 ablation with calibrated
parameters also passes. The fitted (CdA, Crr, kSmooth) are *effective* values
that absorb resolution bias; don't read them as physics.
[[package]](../packages/entry20/ro-crate-preview.html)

### Entry 21 — The "constants" depend on the map's grain
**Data:** Entry 20's cached profiles (864 rides × 5 m/30 m), plus the
58 censo rides as the never-fitted transfer corpus.

Hypothesis: the behavioural trio (k_s, ε₀, climbThr) was calibrated on 30 m
data, so re-fitting it at 5 m — as a pure resolution transfer, never touching
measured energy — should bridge the gap. **Partly right**: it bridges all
three rider corpora per-ride, and the fitted k_s lands exactly on its
predicted mechanism (the h₊ ratio). But it fails on the flattest, never-fitted
corpus — so the trio is a function of **(resolution × terrain regime)**, not
resolution alone. There is no universal constant set; there is a calibration
per (rider, map). [[package]](../packages/entry21/ro-crate-preview.html)

---

## Act V — Honest error bars (Entry 22)

### Entry 22 — "Beats" becomes "parity", and that's still the win
**Data:** no new tracks — the per-ride result CSVs already written by the
earlier harnesses.

Bootstrapped confidence intervals and paired sign tests on every headline
number. The one casualty: "the champion beats the simulation" (3.6% vs 5.1%
medians) is **not supported paired** — CIs overlap, champion closer on only
25/44 rides (p = 0.45). The article now claims **statistical parity** — which
is still the practically decisive result, because the closed form is the
engine cheap enough to route with. Rankings that survive testing keep their
claims (e.g. P. Paz geometric-ε wins at p < 10⁻⁴). Every published median is
now gated by a script that fails loudly if it drifts.
[[package]](../packages/entry22/ro-crate-preview.html)

---

## Side quests (Entries 23–24)

### Entry 23 — The routing grid itself inflates energy
**Data:** no ride data — a 900×900-cell crop of the deployed 5 m DTM
(central São Paulo) with synthetic sources and targets, in the sibling
simujaules repo.

(From the simujaules repo.) The 8-direction move grid overestimates *optimal*
route energy — +12.7% median vs a near-continuum reference — and real terrain
doubles the pure-geometry prediction, because zigzagging across contours pays
the asymmetric climb/descent tax at every oscillation. A 16-direction ladder
with profile-integrated moves recovers ⅔ of it; naive long moves flip the
error's sign (the trap). Shipped as v57 options; the pre-registration
scorecard came back mixed — lesson: pre-register distributions, not point
ranges. [[package]](../packages/entry23/ro-crate-preview.html)

### Entry 24 — What the literature says ascent is worth
**Data:** literature only — no engine ran, no published number changed.

A survey of barometer and DEM ascent-error studies brackets everything
Entries 6 and 19 measured, and sharpens one point the literature leaves
unresolved: cumulative ascent **has no true value** — only a value at a chosen
smoothing scale — so "which h₊ is right?" is ill-posed as geometry. Our
harness has the referee geometry lacks: measured pedalling energy. That turns
the smoothing scale into a *fittable parameter* (which is literally what
Entry 20 fitted), a validation no located study performs.
[[package]](../packages/entry24/ro-crate-preview.html)

---

## Recurring terms, once

- **The champion** — the corrected closed form: aero split off climbs
  (Entry 3) + 2 m deadband profile (Entry 5), ε by the corpus rule (Entry 9).
- **Canonical** — the forward-dynamics simulation; the reference, not the
  product.
- **ε** — fraction of descent PE refunded to the rider; geometric estimator
  `min(1, (α/β)/s̄) − 0.13` (Entry 8), flat ≈ 0.20 in stop-go cities.
- **α, β** — cost per metre travelled (roll+aero) and per metre climbed
  (gravity), both divided by drivetrain efficiency.
- **med |Δ%| / bias** — median absolute and median signed error vs measured
  ∫P·dt; the scoreboard currency throughout.
- **v2Edge** — the per-edge cost the sampasimu app deploys (grade-local ε);
  ties the champion at ~30 m resolution (Entry 18).
- **The bias-trade law** — any variant that shifts total energy wins exactly
  where the current parameter bias points the other way (Entry 17); the reason
  "cleaner physics" kept failing to beat the champion.
- **Corpora** — longões (44 author brevets), censo (62 urban collective
  rides), P. Paz (441), JAAM (219), danlessa (the author's full export, 621
  clean) — the last three are the transfer tests.
