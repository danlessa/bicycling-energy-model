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

**A4 is deferred, and the reason matters.** The obvious reason would be that time
doesn't interest planners — that is false, and travel time is in fact the
standard currency of transport appraisal, so a validated time model would be the
most planner-legible of the four. The real reason is evidential: Entry 13 tested
the dual and found it half broken (the ascent term holds, the descent bridge does
not), with a marginal, mass-sensitive headline result. A4 would ship a claim whose
weaker half is known to fail, into the one domain where practitioners have
well-calibrated alternatives. So: **defer, don't abandon** — if the descent bridge
is ever repaired, A4 moves from branch to critical path.

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
