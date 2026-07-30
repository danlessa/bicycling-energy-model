# `mission-model/` — the repository's mission, in Mission Engineering terms

Why this exists: everything else in this repository answers *how well does the
energy law work*. Nothing answers *what is the law for, and how would we know if
it were serving its purpose*. Mission Engineering is the discipline that asks the
second question, deliberately upstream of the system that answers the first.

**Mission.** Publish scientific articles on bicycling energy estimation so that
they provide the evidential basis for urban- and tour-planning use cases.
("Subsidise" is read as Portuguese *subsidiar* — to furnish the grounds for a
decision — not financial subsidy.)

## Files

| File | Holds |
|---|---|
| `00-mission.sysml` | The mission, its operational context, the E1→E4 effect chain, and five mission objectives (MO-1…MO-5) |
| `01-stakeholders.sysml` | The four stakeholder classes, their concerns, and the tension between them |
| `02-capabilities.sysml` | Seven required capabilities, the systems that deliver them, and where a capability is thin |
| `03-measures.sysml` | MOPs vs MOEs — and the gap between them |
| `04-mission-threads.sysml` | End-to-end threads per stakeholder, each with its failure mode |
| `05-deliverables.sysml` | The four articles, their enablement chain, and why A4 is deferred |
| `06-lifecycle.sysml` | Life-cycle stages, the freeze tension, and the A1→A2→A3 roadmap |
| `07-sub-missions.sysml` | One sub-mission per critical-path article, each with what it must *not* claim |
| `08-publication-roadmap.sysml` | Ordered, checkable steps to publication for A1, A2, A3 and J |

Read in order; each imports the one before.

## The deliverables

    A1 (closed form)  →  A2 (on DEMs)  →  A3 (discretised edge cost)
                                              │
                                              └→ energy-optimal routing,
                                                 corridor comparison, diagnostics

    A4 (time dual) — branch off A1, off the critical path

The chain is ordered by **enablement**, not preference: A2 cannot be written
without A1's law, and A3's discretisation question is *raised by* A2. The
consequence worth noting is that **A3, not A1, is the deliverable that reaches
the mission's terminal stakeholder** — routing over an edge-cost graph is what a
planning tool actually does. A1 is mature and A2 drafted, so A3 is the binding
constraint on the whole mission.

**A4 is deferred for two reasons, the first strategic.** Objective MO-6 is to
shift the planning discourse from *time* to *energy*, because an energy ranking
generalises across rider power profiles and a time ranking does not —
**energy-optimal routing is accessible routing**. A4 argues entirely in the
currency the mission exists to displace, so publishing it well would lend the
project's credibility to time-based reasoning at exactly the wrong moment. The
property that makes A4 planner-legible is what makes it strategically costly.
The second reason is evidential: Entry 13 found the dual half broken (ascent
holds, descent bridge does not), with a marginal, mass-sensitive headline. So
**defer, don't abandon**, with a two-part promotion condition — repair the
descent bridge *and* establish energy as the currency first, after which A4
becomes a bridge from the established frame back to the familiar one.

Separately: the dual's *negative* result is currently unpublished and reaches
nobody. Releasing that alone costs the strategic position little — a negative
result about time does not advance time as a currency — and is worth deciding on
its own merits.

## The three things the model actually surfaces

Written down mainly because they were not obvious before the modelling forced
the question.

**1. Every measure the project tracks is a Measure of Performance, and the
mission is stated in Measures of Effectiveness.** Accuracy, bias, formal
equivalence, reproducibility, gate coverage — all properties of the *model*, all
measurable from inside this repository, all in good shape. The mission succeeds
or fails on whether a planner ever grounds a decision in the result, and no
artefact here would detect that either way. `MOE-5` is the terminal measure of
the stated mission and it is uninstrumented. That is a normal position for a
research repository, but it means the mission's second clause is currently an
*intent* rather than a demonstrated effect. The deliverable chain sharpens this:
MOE-5 cannot plausibly move before **A3** lands, because until then there is no
artefact a planning body can route with. The gap is an unfinished mission with a
named unblocker, not a failing one.

**2. The four stakeholders cannot be served by one artefact.** The error bars
that satisfy academics are noise to the public; the plain-language summary that
reaches the public would be dismissed by academics. The project's answer is a
ladder — paper, piece, applet, deployed map — over one evidence base. The cost of
that answer is that a re-baselined number must move across every rung in
lockstep, which is exactly the propagation checklist the repository already
maintains. The public rung is the incomplete one: piece 1 is bilingual, pieces 2
and 3 are pending.

**3. `cDeploy` is the thinnest capability and the least visible from inside.**
The E2→E3 link — public evidence becoming something a planner can operate — is
carried entirely by the deployed tools. They exist and run. No adoption by an
actual planning body is evidenced anywhere in this repository, and the repo's own
instruments cannot see that gap, because they all point at the model.

## The roadmap

Release order is **forced** by citation resolvability — each article cites its
predecessor, and a citation needs a DOI that exists. Drafting can overlap;
releasing cannot.

| | Stage | Next gate | Blocked by |
|---|---|---|---|
| **A1** | Review — second external round returned | Close the two framing calls, elevate the cancellation limitation, full battery, propagation checklist | Nothing technical — a maintainer decision |
| **A2** | Draft (letter, ~4pp; Entry 41 evidence already gated) | Finish draft → review | A1's *release*, for the citation |
| **A3** | Scaffold | Decide whether the discretisation claim needs its own registered experiment | A2's scale prescription, then A2's release |

Combined with the previous two findings, the chain closes into an uncomfortable
result: **A1's remaining framing fixes are on the critical path to MOE-5**, the
mission's only uninstrumented measure. The bottleneck on the whole mission is not
a missing experiment or a weak number — it is two editorial decisions about A1's
title and abstract, which the last review called "framing, not science."

Nothing is published yet: the Zenodo DOI is **reserved, not minted**, so A1 will
be the project's first public release and the monolithic working paper is a draft
to be retired rather than a record to be superseded. Retiring it costs nothing
publicly — no citations break.

The life cycle's own gap: **Support has no drift detector.** A released article is
frozen; the repository is not, and a re-baseline has already moved every
assumed-parameter number once. The cheap fix is a gate section pinned to a
released paper's *as-published* values, which fails when the live numbers leave
the published intervals — deliberately inverting the usual gate direction.

## A fourth deliverable, off the article axis

**J — the open lab journal.** Publish the epistemic *process* — 16
pre-registrations with failure modes fixed in advance, 9 withdrawn or corrected
claims, 42 evidence crates, a 72-gate battery that re-derives rather than
compares — as an interactive, reproducible artefact traceable to the articles.
The components already exist (7,099-line append-only journal, executable
`journal.qmd`, claims explorer at 190 nodes, the I/T/O/S lineage DAG); what is
missing is publication, one navigable surface, and article-claim → entry links.

Three properties make it unusually cheap: no citation dependency, privacy already
clear (no activity paths, only pseudonyms the paper already carries), and — the
distinguishing one — **zero lockstep cost**. Every other rung of the ladder must
be updated when a published number moves; the journal must *not* be, since
entries keep their as-written values by rule. It is the only artefact addable
without adding propagation work. It also makes article-vs-repository drift
*legible*, which is most of what the lifecycle's missing Support-stage detector
would buy.

The risk is real: a corpus of withdrawn claims reads as rigour to a fair reader
and as ammunition to a hostile one. Both readings come from the same text — so
**answering it is a validation gate on J's scoping stage**, not a caveat.

What counts as an answer is structural, not rhetorical: a hostile reader won't
read a defensive preamble, and a preamble that must be read to work doesn't work.
The navigation has to make it impossible to reach an admission without its
resolution in view — and the mechanism already exists unused, since the claims
graph carries typed `disputes`/`qualifies`/`corrects` edges linking every
withdrawal to what replaced it. A withdrawn claim shown beside its correction
reads as the process working; the same claim shown alone reads as an error
admitted. Same text, opposite effect, and the difference is layout.

The gate is tested adversarially, as everything else here is: enumerate the
passages most damaging when quoted alone — *"accurate by cancellation rather than
by fit"*, the probe that turned out to be measuring altimeter noise, the 9-of-9
rescored to 7-of-9, the 52% that should have been 69% with the gate certifying
the wrong denominator — and for each ask whether a reader can reach it without
seeing what it was corrected to. If yes for any, the scope isn't settled.

What the gate must **not** become is a licence to prune. If the answer to hostile
reading were to publish fewer withdrawals, J would have destroyed the thing it
exists to show. It constrains presentation only; the corpus stays complete.

**Sequenced after A3** (maintainer decision); scope deliberately open. The
consequence to carry forward: A1 ships *without* J behind it, so it cannot lean
on the journal to show its limitations are stated — it must carry that in its own
text, which raises rather than lowers the stakes on its framing fixes.

## Reproduction repos — one per article

**A1/A2/A3 each ship with a repository that reproduces that article's results and
nothing else**, data included, anonymised and filtered — a cleaned-up subset of
this repo, not a copy with secrets removed.

The *nothing else* is the load-bearing half: other articles' harnesses invite
scope confusion, the lab journal belongs to J, and every extra path is one more
place a private one can hide.

The I/T/O/S layering is what makes it tractable. The repo ships **O** (per-ride
outputs), **T** (the harnesses) and the **S** derivation (the gate subset). It
never ships **D** — no tracks, no coordinates. Every published number is a
statistic over O, so O is sufficient: a reader reproduces the *results* without
ever holding the rides.

**The anonymisation tension mostly dissolves once measured.** Across every result
CSV there are exactly three identifying fields — `ride`, `date`, `file`:

| field | treatment | cost |
|---|---|---|
| `file` | dropped | none — nothing consumes it |
| `ride` | surrogate ID, assigned in chronological order | none |
| `date` | per-rider **monotonic rank**, not a calendar value | **none** |

The date substitution is the one that matters. The only published statistics
touching dates are the chronological split-halves (Entries 44, 47, 49), which
sort by date and take `half = index % 2` — they consume the *order*, never the
value. A rank preserves them exactly.

**Tracks are excluded by construction, already.** The O layer carries no
coordinates — verified column by column: `x` is distance-along-route in metres
(the engine's convention), `geoCov`/`geo_span` are coverage fractions. One
release chore falls out of that: rename or document `x`, because to an outside
auditor scanning for coordinates it reads like a longitude.

**On publishing a centroid — one per *corpus*, never one per ride.** A per-ride
centroid is endpoint-derived geometry in disguise: for a loop starting at home it
sits near the home, and over 441 rides of one rider the density peak *is* the
home. That is the exact failure Entry 26 caught mid-experiment (crop bboxes
derived from ride endpoints, which invert back to those endpoints), and the same
reason D6's tracks stay gitignored despite an open licence. Quantisation doesn't
save it — the signal is in the repetition, not the resolution.

It also buys nothing: no published statistic in A1–A3 depends on where a ride
happened. Location enters only through the wind estimate, whose *output*
(`wind_ms`) is already in O without its input. So per-ride centroids fail the
repo's own rule — ship what reproduces the results and nothing else — before
privacy is even considered. What a reader legitimately needs is geographic
context (São Paulo or the Alps?), and one coarse centroid per corpus serves that
completely, as the articles already do in prose.

Residual risk, stated plainly: per-ride distance-and-ascent rows are still a weak
fingerprint against a public activity profile. Removing the calendar value takes
this from near-certain matching to weak — a date *plus* a distance identifies a
ride, a distance alone mostly doesn't. Perturbing values would reduce it further
and break exact reproduction, which is the one thing the repo exists for. So:
exact values, no dates, surrogate IDs.

**Anonymisation is a blocking gate on publishing each repo** — an executable
script, run against the *release artefact* rather than the working repo (checking
the source proves nothing about what survived filtering), exiting non-zero,
output archived with the release.

It has two halves that check each other, because either alone is trivially
satisfiable in the wrong direction — ship nothing and it's anonymous and useless;
ship everything and it reproduces and exposes people:

- **A — nothing identifying survives.** No names, dates or paths; surrogate IDs in
  chronological order; no coordinate columns *tested by value, not just by name*
  (any float column ranging inside ±90 paired with one inside ±180 gets flagged,
  because the next leak won't be called `lat`); no `.fit`/`.gpx`; at most one
  centroid per corpus, zero per ride.
- **B — everything published still reproduces**, to the published precision, with
  the chronological split-halves coming out identical — the sharp test that the
  date→rank substitution preserved *order* and not merely removed dates.

On any ambiguity, **A wins and the release waits**. A reproduction failure is
embarrassing and fixable by publishing again; an anonymisation failure cannot be
withdrawn, and the contributor whose home it exposes wasn't the one who chose to
publish.

**Consent — resolved.** D6 is CC BY 4.0, so derived aggregates are publishable
outright; D1 and D5 are the author's own; and the D3/D4 riders have agreed,
**conditional on the tracks being anonymised**.

That condition changes what the gate *is*. It is no longer only a privacy control
the project imposes on itself — it is the term on which permission was granted.
Failing half A wouldn't be a lapse against policy; it would publish two people's
data outside the consent they gave. So the gate **cannot be waived by the
project**, because the project isn't the party whose agreement it encodes.

## The sub-missions

One per critical-path article. Each is a complete mission — own effect, own
primary stakeholder, own measures, own failure mode.

| | Sub-mission | Primary | Fails if |
|---|---|---|---|
| **SM-1** (A1) | Establish that the estimate is **credible** | (A) academics, (C) activists | The framing invites "validated against 2,025 rides" when the protocol is a shared-input consistency check |
| **SM-2** (A2) | Make it **operable from a map** | (B) technicians | The smoothing is tuned per DEM — then the elevation source is a hidden free parameter, the same disease as a per-rider constant, one level up |
| **SM-3** (A3) | Make it **searchable**, and MO-6 operational | (B), (C), (E) | The grid's own geometry decides the answer — connectivity bias, direction quantisation, a dead clamp (all three already caught once) |

The load-bearing field is **what each must *not* claim**. A1's credibility
depends on it not claiming planner-usability; A2's on it not claiming routing.
The temptation at each stage is to reach for the next stage's conclusion, because
that is where the interest is — and reaching is what a reviewer catches. Scope
discipline here isn't modesty, it's the mechanism by which each article survives
adversarial reading.

**Does energy-optimal routing differ from the alternatives?** I first posed this
as one open empirical risk to MO-6. It is two questions and they resolve
differently.

*Against distance — settled, and not empirically.* β/α is the exchange rate:
about **69** at the ~50 W planning reference, above **120** as speed falls and
aero vanishes. One metre of ascent costs what 70–125 metres of flat riding costs,
and a distance objective prices that metre like any other. The objectives cannot
coincide except by accident. A3 should *derive* this, not measure it — the only
empirical residue is how often a real network offers the alternative, since where
one road climbs one valley every objective agrees and the question is moot rather
than answered.

*Against time — the substantive one, and already half-answered.* Time is
behaviour-driven: Entry 13 found the time dual's descent half does not predict
measured descent speed, because descending pace is a choice about risk and
comfort, not a fact about the hill. Energy's behaviour-dependence is real but
**confined** — it enters through `ε·h₋` alone, bounded by the 0.08–0.30 spread
across seven riders, while the dominant `β·h₊` term is mass × geometry. A time
ranking inherits whichever temperament was assumed; an energy ranking largely
does not.

Which produces an awkward and useful result: **the strongest available evidence
for MO-6 sits inside A4** — the article deferred for arguing in the wrong
currency — and it is the half that *failed*. The dual's descent bridge breaks
precisely because time is behaviour-limited. So deferring A4-as-a-positive-claim
and publishing A4's-negative-result pull in opposite directions, and both are
right.

Two structural notes. The series is **not all-or-nothing**: SM-1 delivers a
checkable result serving (A) and (C) whether or not SM-2 lands, which is the main
practical argument for decomposing the monolith. And the sub-missions get
**harder to evaluate as they go** — SM-1 is judged by readers who can check a
derivation, SM-2 needs a planner to try it on their own raster, SM-3 needs
someone to route with it. The evidence available inside this repository thins out
along exactly the axis the mission travels.

## Publication roadmaps

`08-publication-roadmap.sysml` holds ordered steps with a checkable *done-when*
and an explicit blocker for each. Summary:

**A1** — science settled; everything left is editorial or infrastructural.
`A1.1` the three framing fixes · `A1.2` minor review items · `A1.3` propagation +
full battery + archive as-published · `A1.4` **build the release infrastructure**
(filtering, anonymisation transform, gate script) · `A1.5` release, and retire the
monolith unpublished.

**A2** — evidence already done and gated (Entry 41, 1,188 rides); what remains is
writing. `A2.1` finish the ~4pp letter · `A2.2` review · `A2.3` repo, reusing A1's
tooling · `A2.4` release citing A1's DOI.

**A3** — a scaffold whose first step is a *decision*: does the discretisation
claim rest on Entries 19–21, 23, 25, 26, or need its own registered experiment?
`A3.1` that decision · `A3.2` register/run/gate if needed · `A3.3` **measure the
divergence** · `A3.4` draft → review → repo → release citing A2.

**J** — after A3, scope open. `J.1` scoping, exiting only on the structural answer
to hostile reading · `J.2` assemble the surface so the claims graph's
`disputes`/`corrects` edges render as *adjacency* · `J.3` add the missing
article-claim → entry direction · `J.4` front-matter tally computed, not asserted
· `J.5` release with a **concept DOI and dated versions**, since J keeps growing —
that's the honest shape of an append-only log, not a compromise.

Three things the roadmaps make visible:

1. **Costs are front-loaded, not even.** A1 pays once for filtering, anonymisation
   and the gate; A2, A3 and J inherit them. Reading the three articles as
   comparable efforts overestimates A2/A3 and underestimates A1.
2. **Parallelism is available and underused.** `A1.4`, `A2.1`, `A3.1` and `A3.3`
   are all unblocked right now and none competes with `A1.1`'s editorial pass.
   `A1.4` especially should start early — it's where the unknown-unknowns are,
   since nobody has yet filtered this repo down to one article's reproduction set.
3. **The mission's own measurement is `A3.3`** — how often energy-optimal routing
   actually diverges from distance-optimal — not any article's argument. It is one
   step in one roadmap, currently unblocked and unstarted.

And the honest scheduling note: the whole chain queues behind two editorial
decisions in `A1.1`. That isn't a criticism of the science; it's a reason to treat
`A1.1` as a decision to be *made* rather than work to be done.

## Conventions

- **SysML v2 textual notation.** Files are plain text and are not compiled by
  anything in this repository, consistent with its no-build rule. To check them,
  paste into the SysML v2 pilot implementation or its Jupyter kernel; nothing
  here depends on that having been done.
- **`doc` comments carry the content.** The structure is deliberately light —
  the value is in the rationale, the failure modes and the named gaps, not in
  the type hierarchy.
- **Descriptive, not aspirational.** Where the mission is not met, the model says
  so (`MOE-5`, `allocDeploy`, `allocExplain`, `CloseTheLoop`) rather than stating
  the goal as though it were the status.
- **Privacy dominates.** Where the privacy concern conflicts with any other
  stakeholder need, it wins; this is recorded in the model because it has already
  decided at least one real experiment.

## Maintenance

This model describes intent and effect, so it changes far more slowly than the
numbers do — a re-baselined median does not touch it. Revisit it when a *paper*
lands, a stakeholder class changes, a capability is added or retired, or when
`MOE-5` finally has something to record.
