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
and as ammunition to a hostile one. Both readings come from the same text. The
mitigation is framing the norm explicitly and quantifying it in front matter —
an unframed body of self-criticism is a liability, a framed and counted one is
the credential.

**Sequenced after A3** (maintainer decision); scope deliberately open. The
consequence to carry forward: A1 ships *without* J behind it, so it cannot lean
on the journal to show its limitations are stated — it must carry that in its own
text, which raises rather than lowers the stakes on its framing fixes.

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
