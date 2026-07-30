# The curated journal — how far can a closed-form energy model go?

This is the **readable companion** to the lab journal
([MODEL_COMPARISON_JOURNAL.md](MODEL_COMPARISON_JOURNAL.md)). The two-journal
rule: the **lab journal is the authoritative record** — verbatim prompts,
pre-registrations, every number, every caveat, newest first. This file retells
the same entries as a story, oldest first, in plain language, keeping only
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

The honest current answer, after 28 entries: **yes, with disciplined
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

*What is ε, really? A geometric law with a behavioural offset — the coasting
deficit — and a failed braking theory.*

### Entry 8 — ε from geometry alone
**Data:** the 44 longões; the "measured" ε per ride is the descent-energy
balance read from each power track.

ε (the descent refund fraction) turns out to be predictable from grade:
coasting recovers `min(1, (α/β)/s̄)` of the descent, minus a near-constant
**0.13** for real-world braking and descent pedalling. That constant earned a
name — the **coasting deficit**, ε₀: the slice of the refund pure coasting
would have paid out but the rider never collects, because they keep pedalling
into the descent and brake before the corners. It is a property of riding
habit, not of the route — which is why it recurs on every rider tested, and
why Entry 10's braking-density predictors all failed to explain it. On real
descents this estimator beats any flat constant by **37% RMS**. Two intuitions
died honorably: flat terrain does *not* push ε→1 (riders pedal through dips,
so measured ε→0), and curviness/surface penalties fit with the wrong sign.
[[package]](../packages/entry08/ro-crate-preview.html)

### Entry 9 — First out-of-domain test: the collective's urban rides
**Data:** the censo — 87 activities linked from the collective's ride
census spreadsheet, downloaded and filtered to 62 clean urban power rides.

On 62 urban stop-go rides from the Pedal Hidrográfico censo — different style,
generic assumed rider — all models land **~4–7% median**. The cheap "poor
man's" variant is the best (3.9%), beating the simulation (6.6%). But the
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
sustained climbs: 74.5 kg), the energy law lands **4.9% median**, geometric ε
is the best variant, the frozen rider-1 ε estimator beats even P. Paz's own
best flat constant by ~35%, and the coasting deficit reproduces (0.12 vs
the calibrated 0.13). Looks like a full transfer. (Hold that thought.)
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

JAAM (219 rides, big rider, pedals the descents) confirms the energy law
(3.5–5.4% median) and the coasting deficit a third time (0.133) — but the
geometric-ε *skill* fails outright on the gentle rides and is inconclusive
on the real descents. The Entry-12 "35% win" is thus **rider-dependent: it works for
coasters, not for descent-pedalers**. Also corrected here for the record:
P. Paz and JAAM are independent riders, *not* collective members; three
independent riders is the stronger external-validity story anyway.
[[package]](../packages/entry14/ro-crate-preview.html)

### Entry 15 — Can we measure the rider from ride data alone?
**Data:** the clean-fitting activities of all three riders (single-rider
power balance holds, r² > 0.4): P. Paz 122, JAAM 27, author 5.

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
ladder written down): **all three riders pass** (3.69/2.79/4.92% at +0.97/
+0.12/+0.83 bias; the last with 0.08 pp to spare). When the corpus was later
re-baselined to São Paulo's gravity (Entry 27), JAAM's line was the only one
that genuinely moved; the other two held. The honest decomposition:
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
number. The one casualty: "the champion beats the simulation" (3.5% vs 5.2%
medians) is **not supported paired** — CIs overlap, champion closer on only
24/44 rides (p = 0.65). The article now claims **statistical parity** — which
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

### Entry 25 — the grid note, now part of the record
**Data:** none new — the canonical simujaules research note imported
verbatim.

Entry 23 was the condensed retelling; Entry 25 carries the **full canonical
note** into this repo word-for-word (the ladder tables, the mechanism, all
four attempts at beating the cost–accuracy law, the parametric-correction
study, and the shipped-v57 scorecard), so the journal stays self-contained
even if the sibling repo moves on.
[[package]](../packages/entry25/ro-crate-preview.html)

### Entry 26 — the grid's bias on real routes, and bridges that stop lying
**Data:** 90 endpoint pairs distilled from the Entry-19 corpus's 922 rides
(private, never committed) + OSM bridge/tunnel spans pulled for the whole
DEM; 922 rides again for the profile half.

Two pre-registered follow-ups, both answered.

**The direction ladder.** Entry 23 measured the 8-direction grid's
overestimate on *synthetic* start/end points; this re-measures it on **real
ride endpoints**. It survives the move: the 8-grid reads **≈12% above** the
near-continuum optimum, monotonically improving with more directions
(6% at 16, 2.4% at 32, 0.7% at 64), with no direction bias — exactly the
terrain-dominated picture Entry 23 found. Two new qualifications, though.
The gap **shrinks on longer routes** (15.8% on the shortest third of pairs
vs 10.3% on the longest), which explains what first looked like a
rider effect. And — the punchline — the gap **scales with how
climb-dominated the rider's cost is**: swapping the app's default rider for
a calibrated one (Entry 20's) halves both the climb-dominance ratio and the
gap (12% → 6.8%). So the pre-registered decision "should the app ship 16
directions?" **flips between two equally-legitimate rider settings** — it
has no rider-free answer. Under the app's defaults the rule failed by
0.31 pp (49.69% vs a 50% threshold), and its confidence interval straddles
the threshold anyway. Entry 23 taught "pre-register distributions, not point
ranges"; this one adds "pre-register the *estimator*, not just the
threshold."

**Portals** — simujaules' bridge/tunnel corrections, which stop a bare-earth
DEM from diving into the valley under every viaduct. As *profile*
corrections they help exactly where the DEM lies: urban censo rides improve
from 22.1% to **18.3%** median error (bias likewise), the author's corpus by
1.6 pp, pooled 922 rides from 10.2% to **9.4%** — and every corpus with
viaducts moves toward the measured energy. As *routing* edges they leave the
median route completely untouched (most optimal paths never need a bridge)
but produce a long tail — up to −9% on individual routes — and, more useful
for the 300 kJ mission, they **expand reachable area on 92% of route pairs**.
One prediction failed instructively: total ascent didn't drop on 90% of
corrected rides but only 76%, because splicing a flat deck into a profile
injects small steps at its two ends. That artifact is specific to *profiles* —
the app's real portal is a single routing edge with no splices.

Also recorded honestly: 65% of all rides are loops (start ≈ end), so the
route-pair corpus is the point-to-point minority; and an adversarial review
of the harnesses mid-run caught that the first implementation was sending
each pair's endpoint-derived bounding box to public map servers. Those
results were **thrown away** and the pull rewritten to cover the whole DEM
regardless of any ride.
[[package]](../packages/entry26/ro-crate-preview.html)

---

## Act VI — Housekeeping that taught something (Entries 27–28)

### Entry 27 — São Paulo's own gravity
**Data:** no new data — the entire harness suite re-run under one changed
constant.

Every number in this journal had been computed with the textbook g = 9.81.
São Paulo's actual local gravity, measured at IAG-USP, is **9.7864** — 0.24%
lower. Since every ride here is ridden in São Paulo, that is the physical
value, so the whole corpus was re-baselined. Two housekeeping wins came
along: the flat-speed solver went back to the browser app's simple
bisection (a closed-form replacement had quietly pulled in numpy, breaking
the rule that the analysis code needs nothing but the standard library —
and its formula was wrong in two branches), and the demand that Python match
JavaScript *bit for bit* was dropped in favour of matching it numerically,
which it does: 8 514 checks agree to one part in a billion.

The interesting part is **what didn't move**. Nine published medians shifted
by ≤0.2 pp, always in the predicted direction (less gravity → climbing costs
less → the models that over-predicted improved, the one that under-predicted
got slightly worse). But every result that transfers to *other riders* was
unchanged to four figures — because those corpora don't assume the rider's
mass, they **infer** it, so the gravity change went into the inferred mass
instead (74.3 → 74.5 kg, 101.7 → 101.9 kg — exactly the predicted ratio).
One line summarizes the whole exercise: *a corpus that fits its parameters is
insensitive to the constant; a corpus that assumes them is not.*

Two claims moved in opposite directions, and both are now stated more
carefully: the "the cheap formula only *ties* the simulation" finding got
**stronger** (the formula is now closer on 24 of 44 rides instead of 25 —
even less separable), while the claim that the rural coasting deficit
*ties* the city's own best constant softened to a **near**-tie (0.09 vs
0.08). The gate script did its job loudly: 14 of its 24 checks failed on the
first run, each naming the stale number it expected.

The entry also wrote down, *before* the slowest harnesses finished, what it
expected them to do: absorb the gravity change almost entirely, since they
fit their own parameters. Scoring that prediction took two attempts, and the
record keeps both. The first re-runs of the DEM chain showed small drifts —
and this journal briefly explained them with a tidy story about the
calibration being a grid search that "hops to a neighbouring grid point".
That explanation is **retracted**: the drifts were contamination, not
physics. Three harnesses still carried the riders' implied masses frozen as
code constants from before the re-baseline, so those runs mixed the new
gravity with the old masses — breaking by hand the very m·g invariance the
prediction was built on. The gate scripts and a same-day audit caught it,
and the chain was re-run clean. Clean, the pre-registered expectation is
confirmed, and cleanly: the routing-scale trio (Entry 21) — which fits a
*ratio*, so a common factor cancels — returns its published values to the
digit, the calibration goal (Entry 20) keeps the same smoothing radius and
the same PASS on all three riders at essentially its published numbers, and
the only genuine movers are the censo — the one corpus that *assumes* the
rider's mass — and one line of JAAM's Entry-20 validation. The one-line
summary survived its own audit: a corpus that fits its parameters really is
insensitive to the constant.
[[package]](../packages/entry27/ro-crate-preview.html)

### Entry 28 — Same science, tidier house
**Data:** no new data — code consolidation; all gates re-run green.

Twenty-seven entries of accretion had left the code where each entry dropped
it, with the same small helpers copied privately into harness after harness.
This entry consolidates: the shared helpers now live once, in one module all
the harnesses import; the Python package got a name that says what it is
(`src/bicycling_energy_model/`, formerly `analysis/bem/`); and the retired
JS-parity scaffolding — the frozen verbatim engines, their runner, and the
V8 math shims — was deleted outright, since Entry 27 already made the Python
package the single implementation. Git history keeps what was removed.

The rest is a restructure that gives everything a place named for what it
is: harnesses under `src/harness/`, inputs under `data/inputs/`, harness
outputs under `data/results/`, both journals under `research/journal/`, the
original derivation notes at `research/notes/original_notes.md`. Nothing
scientific changed, and that claim is not taken on faith: the gate scripts
and harnesses were re-run after the move and came back green — which is the
quiet payoff of Entry 22's discipline. A repo-wide reshuffle is safe
housekeeping exactly because every published number has a gate that would
have failed loudly.
[[package]](../packages/entry28/ro-crate-preview.html)

---

## Act VII — The sensitivity map (Entries 29–30)

### Entry 29 — Sweeping the constants nobody measured
**Data:** the four blind corpora, re-scored over a 108-point grid of
CdA × C_rr × ρ — pre-registered, six predictions on record before a single
cell was computed.

Three predictions held: ρ and CdA enter every quantity only as their
product (exact to fourteen decimal places — the grid is secretly
two-dimensional); the mass inversion *compensates* for parameter excursions
(±60% on the constants moves the inferred mass by ±3 kg and the law's
medians by points, not tens); and the dynamic-vs-flat verdict on P. Paz
flips exactly where the fitted-physics rerun said it would. Three fell: the
coasting deficit's measured value is *not* parameter-free (it slides
monotonically with ρ·CdA, from −0.07 to +0.19 across the grid — so 0.13
means *at the priors, at this scale*); the priors do not sit at any error
minimum; and no single cell minimizes every model at once. The lesson that
keeps paying: apparent gains from moving constants are signed-bias
cancellation — the circularity argument, measured rather than argued.
[[package]](../packages/entry29/ro-crate-preview.html)

### Entry 30 — The simulation rides the same rollercoaster
**Data:** the forward simulation under the same excursions, one at a time.

Both engines' absolute errors move together by up to ±6 points, while the
law-vs-simulation *gap* moves 9–14× less on the transfer riders. That
lockstep is why the paper's paired conclusions survive parameter
uncertainty that its absolute numbers do not — and it became the standing
signature to check every time a protocol changed.
[[package]](../packages/entry30/ro-crate-preview.html)

---

## Act VIII — The protocol reckoning (Entries 31–32)

### Entry 31 — What Table 2 actually was
**Data:** the 44 calibration brevets, re-run under the frozen constants
every other corpus uses.

An adversarial review caught the paper asserting a protocol the calibration
scoreboard never used: D1 had been scored with the ride log's own per-ride
physics and hand-entered ε. Rather than merely disclosing, the corpus was
re-run blind — and the story got better, not worse: the corrected forms
cluster at 7.6–8.2% against the simulation's 8.4% (parity exactly:
22 of 44, p = 1.00), and the informed-vs-blind gap became a *result*, the
measured price of condition knowledge. A second catch: 58 of the urban
corpus's 62 rides are the author's own recordings — the honest unique-ride
count is 1,285.
[[package]](../packages/entry31/ro-crate-preview.html)

### Entry 32 — The rot lives where the gates don't reach
**Data:** none new — a third review, and the regenerations it forced.

Every stale number the review caught (a descent-RMS table row, a
real-descent count, a paired p-value) was a number the gate battery did not
cover; every gated number was clean. The fixes were mechanical; the lesson
was structural, and the battery grew to cover the classes that had rotted.
The same entry retired the ε_d clamp — provably inert on every measured
ride — and recorded that the transfer-only pool (the two independent
riders, 660 rides) is the paper's honest headline: 5.6% against the
simulation's 6.3%.
[[package]](../packages/entry32/ro-crate-preview.html)

---

## Act IX — Physics from the rides themselves (Entries 33, 35, 36)

### Entry 33 — No human judgment: every ride sets its own constants
**Data:** 1,409 rides, each segmented into strict climbs and flats; mass,
rolling and aero inverted per ride from its own power stream; wind from a
loop test plus historical weather at a coarsened centroid.

The mass estimator validates beautifully (corpus medians within ~1–3 kg of
known and implied anchors; JAAM 98.7 vs 101.9). The inverted C_rr says the
0.008 prior was a good guess. The inverted aero comes out *low*
everywhere — an **effective** CdA that absorbs drafting — and that exposed
the study's deepest structural fact: only the (cost, refund) *pair* is
identified by ride energies. Handing the law an honest cost side while
keeping the frozen refund constant mis-pairs them, and the regime rule
flips. The flat-ε law under automatic physics hit 3.8% pooled — but the
bias columns showed why: compensation, not recovery.
[[package]](../packages/entry33/ro-crate-preview.html)

### Entry 35 — The residual, hunted down
**Data:** two registered arms — braking measured as excess deceleration
beyond the physics coasting decel, and a regime-consistent aero inverted
from each ride's flat power at its *measured* flat speed.

Braking is real but small once the instrument's own noise is subtracted
(≈ 0.7–1.4% of ride energy — the cadence cross-check exposed the raw
estimator as jitter-dominated, vindicating the skeptical prior). The
residual was the flats-selection bias of the segment aero: the
regime-consistent ĈdA closes it almost entirely, law and simulation in
lockstep, **with ε₀ = 0.13 untouched** — the frozen deficit works as
designed the moment the cost side is honest. Pooled: 3.9% vs the
simulation's 4.0%, the study's best frozen-behaviour numbers.
[[package]](../packages/entry35/ro-crate-preview.html)

### Entry 36 — ε₀ interrogated, and vindicated
**Data:** the deficit regressed per corpus, two ways — the mechanism-level
balance statistic and the law-level bias-zeroing value — with chronological
out-of-sample tests.

The balance-level deficit is a tight band (0.10–0.13 on the four non-urban
corpora, both physics protocols); the bias-zeroing values are larger
exactly where a known cost-side remainder exists — a costume, not a
constant. Out of sample, every refit transfers no better than the frozen
0.13, and the pooled "best estimate" (0.110) transfers *worse*. The
re-freeze question was asked and answered the same day: 0.13 stays, for
measured reasons.
[[package]](../packages/entry36/ro-crate-preview.html)

---

## Act X — The deficit's mechanism, and the bicycle as a suspension (Entries 34, 37–40)

### Entry 34 — The S-curve: right mechanism, wrong estimator
**Data:** 1,287 rides at 30 m descent-cell grain; pedalling occupancy and
intensity measured per grade bin; a pre-registered logistic fit with
held-out halves.

The intuition — the deficit is pedalling, and pedalling fades with
grade — is *confirmed as mechanism*: occupancy falls monotonically for all
three riders (0.6 → 0.05 from gentle to steep), faster than the dilution
null, while intensity is flat in grade and rider-conditional. But the
S-curve *estimator* lost its registered test 0 for 3: ride-mean grade blurs
the curve (given freedom, the fit reconstructs 0.13), and the frozen
constant out-transfers every refit under temporal drift. The published
summary: the S-curve is the mechanism; the constant is its correct
ride-level shadow.
[[package]](../packages/entry34/ro-crate-preview.html)

### Entry 37 — Momentum is a suspension
**Data:** none — arithmetic, and two exact results.

Cruising kinetic energy is worth h = v²/2g of climb (2.5–6.3 m at
25–40 km/h): the rider–terrain system is a travel-limited suspension —
KE↔PE exchange the spring, drag the damper, h_KE the travel. Two clean
facts fell out: the fitted deadband τ = 2 m equals h_KE at the calibration
rider's cruising speed, and excess speed decays on a flat with the *exact*,
C_rr-free length λ = m/(ρ·CdA) ≈ 200 m (C_rr sets the floor, not the
length; wind rescales by v/(v+w)). Smoothing stopped being data hygiene
alone and became, in part, physics — rider-relative physics.
[[package]](../packages/entry37/ro-crate-preview.html)

### Entries 38–39 — The τ-sweep, confounded and then rescued
**Data:** the deadband swept 0.5–6 m on every corpus, first under frozen
priors, then under the near-zero-bias regime physics.

Under frozen priors the sweep measured nothing but bias compensation — the
optimum tracked each corpus's standing bias, Entry 29's lesson at a new
dial. Deconfounded, the one corpus whose bias is flat in τ (the heaviest
rider) put its optimum exactly on the momentum prediction (τ* = 3.5 m
against h_KE = 3.1, with τ = 3 beating τ = 2 at p = 7×10⁻⁵) — the
suspension reading's first real evidence. Deployment keeps τ = 2 m: the
basins are flat; the case for per-rider τ is scientific, not practical.
[[package]](../packages/entry39/ro-crate-preview.html)

### Entry 40 — Rollers: a real signal with the wrong suspect
**Data:** a registered recyclable-energy covariate against the law's
residual, 1,409 rides.

Roller-rich rides are systematically over-predicted on every corpus — the
terrain signal is real — but the regression coefficients sit an order of
magnitude above the physical ceiling for momentum recycling, and the
covariate also correlates with the measured deficit, which recycling
forbids. Verdict: recycling itself is energetically sub-resolution
(≤ 0.5% of ride energy); the over-prediction belongs to the whole 2–6 m
oscillation band the 2 m deadband passes through — the same object
Entry 39 saw from the other side.
[[package]](../packages/entry40/ro-crate-preview.html)

---

## Act XI — Pricing the shortcuts (Entries 41–42)

### Entry 41 — The elevation-source substitution (in flight)
The DEM-deployment letter's registered experiment: paper 1's law on
planner-grade DEM profiles of the same rides, with the smoothing
prescription as the deliverable. Running as this act is written.

### Entry 42 — The pencil shortcut, priced and rejected
**Data:** 1,378 rides; the hand recipe's mean-descent-grade ε against the
drop-weighted estimator, under the honest per-ride physics.

The shortcut under-refunds by a near-constant 0.08–0.11 of ε on every
corpus — a definitional bias (its numerator counts all descent metres, its
denominator only the steep distance). On the rider corpora that error
*cancels* other residuals and flatters the accuracy column; the bias
column tells the truth, and the urban corpus fails outright. By the
decision rule fixed at registration, the paper's recipe stopped
recommending it the same day: by hand, use the flat ε = 0.20 — it errs on
the safe side — and leave the dynamic estimator to software.
[[package]](../packages/entry42/ro-crate-preview.html)

---

## Act XII — Leaving the country, and putting ε on trial (Entries 43–47)

### Entry 43 — The fifth rider set: four Europeans, nothing shared
**Data:** D6, an openly licensed deposit — 1,053 parseable rides, 743 scored,
740 clean, from four riders in Catalonia, Burgundy and the French Alps.

The first corpus sharing no rider, country, terrain regime, recording device
or model-selection history with the calibration set. The frozen law reached
its *closest* parity there: 3.16% against the simulation's 3.15%. Three
amendment arms followed. The riders pedal their descents far more than the
ultra-distance specialists do — confirmed physics-free, from descent
occupancy alone — which does not embarrass the deficit but explains it: ε₀
is generated by descent pedalling, so a corpus that pedals more should show
a larger one, and does. The same corpus broke F4's scalar `c` while leaving
the *form* intact, the sharpest evidence yet that `c` belongs to the
elevation source rather than to cycling.

### Entry 44 — The S-curve, reopened
Occupancy as a sigmoid in grade, fitted per rider on chronological halves.
The midpoints separate the rider populations *disjointly* — the specialists
stop pedalling on gentler ground than the amateurs do. An early 9-of-9 result
was withdrawn: it had scored the constant outside its own ≥3% scope and
leaked the flat intensity from the ride being predicted. Rescored honestly: 7
of 9.

### Entry 45 — What should ε₀ be?
A contest of ride-level summaries against ten-plus contestants. The
grade-inverse deficit `k/s̄` beat the constant out of sample where real
descents exist, becoming eq. (8). Two corrections shaped it. Asked what
happens when the mean descent grade is 0%, the answer was that `k/s̄` exceeds
1 below 0.51% — so eq. (8) acquired a domain. And a flat-terrain probe was
found to be measuring altimeter noise: its target ascent rate sat *below* the
corpus noise floor, making the search self-reinforcing. It was retracted and
rebuilt on deadband-smoothed cells.

### Entry 46 — The regime rule, enforced at last — and what it exposed
**Data:** 2,141 rides, 1,103 of them below the threshold.

§3.3 recommends the dynamic estimator only on mean descent grades ≥3%. No
harness implemented it: every published ε_d column applied the estimator to
every ride, including the 52% below the threshold. Built as four columns
beside the existing ones, the switch produced a contradiction — under the
frozen priors it makes the pooled median *worse* (5.08 → 5.62), under honest
per-ride physics it makes it *better* (5.51 → 4.12). Same rides, same rule,
opposite verdict.

The bias column settled it. Below the threshold the coasting limit clamps, so
the ε the estimator actually applies has median 0.544 — against the flat
constant's 0.20. That large refund cancels the over-prediction of the frozen
CdA = 0.40, a value well above the 0.26–0.32 these riders really invert to.
Under frozen priors ε_d therefore looks near-unbiased (+0.28) and the flat
constant looks terrible (+5.90); give the law honest physics and the two swap
places (−4.64 against +0.11).

So the rule is right, and the frozen grid's flat-ride cells were accurate *by
cancellation* — two errors agreeing to look like one success. It is the exact
failure the project's accuracy-and-bias reporting rule was written to catch,
and an accuracy column alone would have blessed it. The registered prediction
that eq. (8) is unusable without the switch did not survive: unswitched, the
grade-inverse form is slightly *better* overall, not worse.

### Entry 47 — Two pre-registered selections, and the incumbent wins
**Data:** 48 calibration rides (D1 ∪ D2 at s̄ ≥ 3%), 990 evaluation rides.

The form was chosen the way it should have been from the start: fitted on the
calibration corpora only, by BIC under a Laplace likelihood, twice — under
frozen priors and again under per-ride inverted physics — with ties going to
the fewest parameters. Both arms returned **ε₀ = 0.13**, the incumbent, with
no fitted parameter at all. The same contest on D3–D6 chose the grade-inverse
form decisively. The disagreement is one of statistical power, not direction:
48 rides cannot resolve what 990 can, and only the calibration arm is
entitled to build the tables. Nothing published moved — which is the point of
registering a selection that could have gone the other way.

Two findings arrived unregistered. Fitting the deficit against *energy* does
not recover it: the constants come back two to three times too small, because
a free deficit buys down the law's positive bias instead of measuring descent
pedalling. Fitted against the *deficit*, an independent implementation
returned 0.134 and 0.0052 against the published 0.13 and 0.0051. And a ΔBIC
of 128.8 — decisive by any convention — was worth 0.17 percentage points of
median error, because BIC scores the mean absolute residual while every
number this project publishes is a median.

The entry also caused and fixed a defect of its own: a smoke flag that
overwrote a canonical results file, silently reducing it from 1,409 rides to
204 until it was regenerated.

### Entry 48 — Parity, finally tested rather than assumed
**Data:** the ten registered law-vs-simulation comparisons behind the paper's
parity sentences.

An external review pressed a fair point: "no detectable difference" is an
absence of evidence, not evidence of equivalence. So the claims were put to a
formal equivalence test — TOST at a margin of ±1.0 percentage point, registered
before any interval was computed, because a margin chosen after peeking is
worth nothing.

The margin's stated justification had to be corrected during registration: the
plan claimed 1.0 pp sat at or below every published confidence half-width, which
is true of the 44-ride rows and false of the pooled ones, whose intervals are
tighter than the margin. The honest grounds are operational — below a
percentage point, nothing a planner decides changes.

Four comparisons came back formally equivalent, six inconclusive, none outside
the margin. The headline transfer pools passed, upgrading the paper's central
claim from a failure to reject into an equivalence result. The 44-ride
calibration corpus was inconclusive exactly as predicted — the same sentence as
before, now carrying a measurement instead of an apology.

The pattern in the inconclusive verdicts is the part worth keeping: five of six
fail to reach equivalence on the side where the *closed form beats the
simulation*. On P. Paz's 441 rides the interval lies entirely below zero — the
law does not merely match the simulation, it wins, possibly by more than the
margin, which is why equivalence cannot be declared. Reading "inconclusive" as
weakness would be backwards.

The exception earned a correction to the paper. On the urban corpus the
interval allows the closed form being over two points *worse*, and its point
estimate already sits outside the margin. That sentence had claimed parity on
the strength of a non-significant sign test. It now says what the data support.

---

## Recurring terms, once

- **The champion / F3** — the corrected closed form (the paper's F1–F4
  naming arrived with the IMRAD paper): aero split off climbs (Entry 3) +
  2 m deadband profile (Entry 5), ε by the corpus rule (Entry 9).
- **Canonical** — the forward-dynamics simulation; the reference, not the
  product.
- **ε** — fraction of descent PE refunded to the rider; dynamic estimator
  = drop-weighted coasting limit minus the deficit ε₀ ≈ 0.13, *unclamped*
  since Entry 32 (the clamp was provably inert); flat ε ≈ 0.20 in stop-go
  cities — and, since Entry 42, the recommended *hand* value everywhere.
- **α, β** — cost per metre travelled (roll+aero) and per metre climbed
  (gravity), both divided by drivetrain efficiency.
- **med |Δ%| / bias** — median absolute and median signed error vs measured
  ∫P·dt; the scoreboard currency throughout.
- **v2Edge** — the per-edge cost the sampasimu app deploys (grade-local ε);
  ties the champion at ~30 m resolution (Entry 18).
- **The bias-trade law** — any variant that shifts total energy wins exactly
  where the current parameter bias points the other way (Entry 17); the reason
  "cleaner physics" kept failing to beat the champion.
- **The pairing rule** — only the (cost, refund) *pair* is identified by
  ride energies (Entries 33/35): change the physics and ε₀ must move with
  it, or the regime rule inverts. The regime-consistent aero (ĈdA from flat
  power at *measured* flat speed) restores the pair automatically.
- **The suspension** — momentum as a travel-limited suspension (Entry 37):
  travel h_KE = v²/2g, damper length λ = m/(ρ·CdA); the deadband as, in
  part, a momentum filter.
- **Corpora** — longões (44 author brevets), censo (62 urban collective
  rides), P. Paz (441), JAAM (219), danlessa (the author's full export, 621
  clean) — the last three are the transfer tests.
