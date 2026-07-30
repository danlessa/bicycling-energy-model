package MissionDeliverables {
    doc
    /*
     * The mission's deliverables: four articles, three of them on one dependency
     * chain and one off it.
     *
     *     A1 (closed form)  ->  A2 (on DEMs)  ->  A3 (discretised edge cost)
     *                                                 |
     *                                                 +-> comparison & diagnostics
     *     A4 (time dual)  — branch off A1, off the critical path
     *
     * Modelling them as a chain rather than a list makes two things visible that
     * a list hides. First, the chain is strictly ordered by ENABLEMENT, not by
     * preference: A2 cannot be written without A1's law, and A3's discretisation
     * question does not even arise until A2 has put the law on planner-grade
     * terrain data. Second, A3 — not A1 — is the deliverable that actually
     * reaches the mission's terminal stakeholder, because routing over an
     * edge-cost graph is what a planning tool does.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionStakeholders::*;
    import MissionCapabilities::*;
    import MissionMeasures::*;

    part def Article {
        attribute id : String;
        attribute establishes : String;
        attribute unblocks : String;
        attribute status : String;
        attribute onCriticalPath : Boolean;
        doc /* onCriticalPath: does the route from this article to MOE-5 pass through it? */
    }

    // ------------------------------------------------------------------- A1

    part a1 : Article {
        attribute redefines id default "A1 — the closed form itself";
        attribute redefines establishes default
            "E = alpha*x + beta*(h+ - eps*h-) with universal constants: that a "
            + "route's energy is computable from geometry, that the two "
            + "historical failure modes (aero charged on climbs, phantom "
            + "ascent) are identifiable and correctable, and that descent "
            + "recovery decomposes into a parameter-free coasting limit plus a "
            + "behavioural deficit. Formally equivalent to forward simulation "
            + "on the transfer pools.";
        attribute redefines unblocks default
            "A2 — there is no point asking how the law behaves on DEM profiles "
            + "until the law and its error are established on the riders' own "
            + "elevation streams.";
        attribute redefines status default "mature; under external review";
        attribute redefines onCriticalPath default true;
    }

    // ------------------------------------------------------------------- A2

    part a2 : Article {
        attribute redefines id default "A2 — the closed form on DEM elevation";
        attribute redefines establishes default
            "What happens when the elevation stream is replaced by a planner's "
            + "terrain model: how much of the error is the MODEL and how much is "
            + "the SOURCE, and the smoothing prescription that makes a DEM "
            + "profile behave like a barometric one.";
        attribute redefines unblocks default
            "A3 — and it is what turns the law from something requiring a ridden "
            + "track into something requiring only a map. That substitution IS "
            + "the E2->E3 bridge for stakeholder (B).";
        attribute redefines status default "drafted; consumes A1 only";
        attribute redefines onCriticalPath default true;
    }

    // ------------------------------------------------------------------- A3

    part a3 : Article {
        attribute redefines id default "A3 — discretisation into an edge cost";
        attribute redefines establishes default
            "How to turn a route-level law into a per-edge cost that a shortest-"
            + "path search can consume without the discretisation itself "
            + "changing the answer — scale, clamping, and where a per-edge "
            + "realisation stops agreeing with the route-level integral.";
        attribute redefines unblocks default
            "Energy-optimal ROUTING, and with it the comparison and diagnostic "
            + "use cases: ranking corridors, mapping where a network is "
            + "expensive, finding the cheapest of several alternatives.";
        attribute redefines status default "scaffold; cites A2's scale prescription";
        attribute redefines onCriticalPath default true;
    }

    // ------------------------------------------------------------------- A4

    part a4 : Article {
        attribute redefines id default "A4 — the time dual";
        attribute redefines establishes default
            "The energy<->time dual t = x*/v_f with x* = x + k+*h+ - k-*h-: "
            + "that the same geometry which prices energy also prices time.";
        attribute redefines unblocks default
            "Nothing else in the chain. It is a branch off A1, not a link.";
        attribute redefines status default
            "unwritten; tested in the lab journal (Entry 13) — the ASCENT half "
            + "holds, the DESCENT bridge does NOT";
        attribute redefines onCriticalPath default false;
    }

    // ------------------------------------------- J — the open lab journal

    part def NonArticleDeliverable {
        attribute id : String;
        attribute statement : String;
        attribute composedOf : String;
        attribute status : String;
        attribute onCriticalPath : Boolean;
    }

    part j : NonArticleDeliverable {
        doc
        /*
         * A deliverable off the article axis entirely: publish the epistemic
         * PROCESS as an interactive, reproducible, citable artefact traceable to
         * the articles' claims.
         *
         * The motivating observation: the journal is currently more convincing
         * than the papers, and none of it reaches a reader. SM-1's success
         * criterion is that an adversarial reader finds the limitations already
         * stated — and the strongest demonstration of that habit (16
         * pre-registrations with failure modes fixed in advance, 9 withdrawn or
         * corrected claims, predictions recorded as failed, 42 evidence crates,
         * a battery of 72 gates that re-derives rather than compares) lives in
         * files a reader will never open.
         *
         * Nothing needs building. The components exist: a 7,099-line append-only
         * lab journal, a readable retelling, an executable Quarto mirror that
         * re-runs against live data, an interactive claims graph (190 nodes, 270
         * edges), the I/T/O/S evaluation-lineage DAG, and per-entry RO-Crates.
         * What is missing is publication, one navigable surface over them, and
         * article-claim -> entry links in the machine-readable direction.
         */
        attribute redefines id default "J — the open lab journal";
        attribute redefines statement default
            "Publish the project's epistemic process — pre-registrations, failed "
            + "predictions, withdrawn claims, evidence lineage and the gate "
            + "battery — as an interactive, reproducible artefact traceable to "
            + "the articles it underwrites.";
        attribute redefines composedOf default
            "MODEL_COMPARISON_JOURNAL.md (append-only, 49 entries) + "
            + "CURATED_JOURNAL.md + journal.qmd (executable) + "
            + "claims-explorer.html + data-graph.ttl + research/packages/ crates "
            + "+ the gate battery output";
        attribute redefines status default "components exist and are current; unpublished, unassembled; sequenced AFTER A3, scope deliberately open";
        attribute redefines onCriticalPath default false;
    }

    part def JRationale {
        doc
        /*
         * THREE PROPERTIES MAKE J UNUSUALLY CHEAP.
         *
         * 1. No citation dependency. Nothing cites J, so unlike A2 and A3 it is
         *    not gated on anyone else's DOI. It can ship whenever it is ready.
         *
         * 2. ZERO LOCKSTEP COST — the property that distinguishes it from every
         *    other rung of the artefact ladder. Paper, piece and applet must all
         *    be updated when a published number moves; that propagation burden
         *    is the standing cost of the ladder. The journal must NOT be updated:
         *    entries keep their as-written values by existing rule. J is
         *    therefore the only artefact that can be added without adding
         *    propagation work.
         *
         * 3. Privacy already verified for this purpose: the journal contains no
         *    activity paths and no identifiers beyond the pseudonyms the paper
         *    already carries.
         *
         * AND IT PARTLY CLOSES A LIFECYCLE GAP. 06-lifecycle names the Support
         * stage as having no drift detector — a released article is frozen while
         * the repository keeps moving. A published, dated, append-only journal
         * is exactly what lets a reader who finds today's numbers differing from
         * A1's tell DRIFT from ERROR. It does not detect drift automatically,
         * but it makes drift legible, which is most of the value.
         *
         * THE RISK, which is real and needs managing rather than noting. A
         * journal of withdrawn claims reads as rigour to a fair reader and as
         * ammunition to a hostile one: "by their own account they got it wrong
         * nine times." Both readings are available from the same text. The
         * mitigation is to make the norm explicit and quantified in front
         * matter — that withdrawal is the process working, with the tally shown
         * — rather than leaving a reader to infer it from 7,099 lines. An
         * unframed corpus of self-criticism is a liability; a framed and counted
         * one is the credential.
         */
        attribute cheapBecause : String default "no citation dependency; zero lockstep cost; privacy already clear";
        attribute closes : String default "makes article-vs-repository drift legible (06-lifecycle's Support gap)";
        attribute risk : String default "self-criticism reads as ammunition unless the norm is framed and counted";
    }

    part jRationale : JRationale;

    part def JTiming {
        doc
        /*
         * DECISION (Danilo): J is sequenced AFTER A3. Scope is deliberately left
         * open and will be settled when it is reached.
         *
         * I had recommended releasing it with A1, on the reasoning that A1's
         * weakest point is asserted rather than visible rigour. That reasoning
         * does not survive the priority call, and the priority call is the right
         * one on its own terms: A1->A2->A3 is the critical path to the mission's
         * only uninstrumented measure, and J is corroboration for claims that
         * are already made. Putting a zero-dependency deliverable in front of
         * the chain would be exactly the pattern the project should avoid.
         *
         * THE CONSEQUENCE, which is worth carrying forward rather than
         * discovering later: A1 ships WITHOUT the journal behind it, so it
         * cannot lean on the pre-registrations, the withdrawn claims or the
         * gate battery to establish that its limitations are stated. It must
         * carry that in its own text. That does not weaken A1 — it raises the
         * stakes on the three framing fixes, because they become the whole of
         * SM-1's defence rather than its visible half.
         *
         * Sequencing J last also improves it: by then it covers three published
         * articles instead of one, and the article-claim -> entry traceability
         * it exists to provide has three targets rather than a single one.
         */
        attribute decision : String default "after A3 (Danilo)";
        attribute scope : String default "deliberately unscoped — to be settled when reached";
        attribute consequence : String default
            "A1 ships without J, but WITH a reproduction repo, so a reader can "
            + "verify MOP-4 rather than take it on trust; what stays invisible "
            + "until J is the epistemic process — the pre-registrations, the "
            + "failed predictions, the withdrawals. The credibility burden on "
            + "A1's own text is therefore lighter than first stated, but the "
            + "framing fixes still carry it alone";
    }

    part jTiming : JTiming;

    part def JScopingGate {
        doc
        /*
         * VALIDATION GATE — the scoping stage for J cannot exit until the
         * hostile-reading risk has an ANSWER, not an acknowledgement. Danilo's
         * call, and the right one: the risk is the deliverable's central design
         * problem rather than a caveat attached to it, so it belongs in the exit
         * criteria of the stage that decides what J is.
         *
         * WHAT WOULD COUNT AS AN ANSWER. Not a defensive preamble — a reader
         * hostile enough to quote a withdrawal against the project will not read
         * the preamble, and a preamble that has to be read to work does not
         * work. The answer has to be STRUCTURAL: the navigation must make it
         * impossible to reach an admission without its resolution in view.
         *
         * The mechanism already exists and is unused for this purpose. The
         * claims graph carries typed cito:disputes / cito:qualifies / cito:
         * corrects edges between assertions, so every withdrawal is already
         * linked to what replaced it. J's surface should render those edges as
         * adjacency rather than as a graph a reader must traverse deliberately.
         * A withdrawn claim displayed beside its correction reads as the process
         * working; the same claim displayed alone reads as an error admitted.
         * Same text, opposite effect, and the difference is layout.
         *
         * HOW THE GATE IS TESTED. Adversarially, as the project tests everything
         * else. Take the passages most damaging when quoted alone — candidates
         * from this year include "the frozen grid's sub-3% cells are accurate by
         * cancellation rather than by fit", the flat-terrain probe that turned
         * out to be measuring altimeter noise, the 9-of-9 result rescored to
         * 7-of-9 after a leak was found, the published 52% that should have been
         * 69% with the gate certifying the wrong denominator, and the smoke flag
         * that overwrote a canonical results file. For each: can a reader reach
         * it without also seeing what it was corrected to? If yes for any of
         * them, the gate FAILS and the scope is not settled.
         *
         * A second and cheaper component, which the risk note already proposed:
         * quantify the norm in front matter — N pre-registrations with failure
         * modes fixed in advance, M withdrawals — so the tally is the first
         * thing seen. Counting converts "they were wrong repeatedly" into "they
         * catch things repeatedly", which is the honest reading and the one a
         * bare corpus does not supply on its own.
         *
         * WHAT THE GATE MUST NOT BECOME. A reason to soften, prune or curate the
         * record. If the answer to hostile reading were to publish fewer
         * withdrawals, the deliverable would have destroyed the thing it exists
         * to show. The gate constrains PRESENTATION only; the corpus stays
         * complete.
         */
        attribute stage : String default "scoping — exit criterion";
        attribute criterion : String default
            "a structural answer to the hostile-reading risk: no admission "
            + "reachable without its resolution in view";
        attribute test : String default
            "adversarial — the most damaging out-of-context passages are "
            + "enumerated, and each must be unreachable without its correction";
        attribute alsoRequired : String default "the norm quantified in front matter (pre-registrations, withdrawals)";
        attribute mustNotBecome : String default "a licence to prune the record — presentation only, corpus stays complete";
    }

    part jScopingGate : JScopingGate;

    // ---------------------------------------------------- dependency structure

    part def Enablement {
        attribute src : String;
        attribute dst : String;
        attribute nature : String;
    }

    part d1to2 : Enablement {
        attribute redefines src default "A1";
        attribute redefines dst default "A2";
        attribute redefines nature default "hard — A2 evaluates A1's law; without it there is nothing to substitute into";
    }
    part d2to3 : Enablement {
        attribute redefines src default "A2";
        attribute redefines dst default "A3";
        attribute redefines nature default "hard — A3 cites A2's scale prescription; the discretisation question is raised BY A2";
    }
    part d1to4 : Enablement {
        attribute redefines src default "A1";
        attribute redefines dst default "A4";
        attribute redefines nature default "soft — A4 reuses A1's geometry terms but nothing downstream waits on A4";
    }

    // ------------------------------------------- deliverable -> stakeholder map

    part def Serves {
        attribute article : String;
        attribute audience : String;
    }

    part s1 : Serves {
        attribute redefines article default "A1";
        attribute redefines audience default
            "(A) primarily — the derivation and the protocol. (C) secondarily, "
            + "as the citable source. Reaches (B) only through A2/A3.";
    }
    part s2 : Serves {
        attribute redefines article default "A2";
        attribute redefines audience default
            "(B) primarily — this is the article that makes the method run on a "
            + "planner's own data. (A) secondarily.";
    }
    part s3 : Serves {
        attribute redefines article default "A3";
        attribute redefines audience default
            "(B) and (C) — routing, corridor comparison and network diagnostics "
            + "are exactly what a planning body and an advocacy group argue over.";
    }
    part s4 : Serves {
        attribute redefines article default "A4";
        attribute redefines audience default "(A) and (D) — an elegant duality, and an intuitive one.";
    }

    // ------------------------------------------------------- A4, assessed

    part def A4Assessment {
        doc
        /*
         * Danilo's judgement: A4 is of interest mainly to academics and the
         * general public, and is "somewhat of a distraction". The model records
         * that, and sharpens the reason — because the obvious reason is wrong
         * and the real one is stronger.
         *
         * The obvious reason would be that time does not matter to planners.
         * That is false, and worth saying plainly: travel TIME is the standard
         * currency of transport planning — it is what appears in appraisal, in
         * mode choice, in level-of-service. A validated time model would on the
         * face of it be the most planner-relevant deliverable of the four.
         *
         * The real reason A4 is a distraction is EVIDENTIAL, not topical. Entry
         * 13 tested the dual against measured ride times and found it half
         * broken: the ascent term holds, the descent bridge does not. Its
         * headline paired result is also marginal (p = 0.012) and mass-
         * sensitive, losing significance at the top of the parameter sweep. So
         * A4 would ship a claim whose weaker half is known to fail, into the
         * one domain where practitioners already have well-calibrated
         * alternatives and would notice.
         *
         * That reframes the decision — but it is the SECOND reason, and the
         * first is strategic (added after the author supplied it; the model had
         * missed it entirely).
         *
         * STRATEGIC REASON, primary. Objective MO-6 is to shift the planning
         * discourse from time to energy, because an energy ranking generalises
         * across rider power profiles and a time ranking does not — energy-
         * optimal routing is accessible routing. A4 is a rigorous, elegant
         * argument conducted ENTIRELY IN THE CURRENCY THE MISSION IS TRYING TO
         * DISPLACE. Publishing it well would lend the project's credibility to
         * time-based reasoning at exactly the moment the series is arguing for
         * energy. The very property that makes A4 planner-legible — that
         * practitioners already budget in time — is what makes it strategically
         * costly here.
         *
         * So the two reasons point the same way for different reasons, and both
         * are worth keeping: A4 is not ready (evidential), and being ready would
         * not by itself make it wise (strategic).
         *
         * The safeguard against this becoming motivated suppression: the
         * deferral is recorded with a promotion condition and stays reversible.
         * Repair the descent bridge AND establish energy as the currency first,
         * and A4 becomes a bridge from the established frame back to the
         * familiar one — which is a far better position to publish it from than
         * leading with it would have been.
         *
         * A twist that strengthens the case for publishing the negative result:
         * A4's failure is EVIDENCE FOR MO-6. The descent half of the dual fails
         * because descending pace is behaviour-limited rather than geometric —
         * which is exactly the demonstration that time is the weaker planning
         * currency and energy the more transferable one. The strongest available
         * support for the mission's normative claim currently sits inside the
         * article deferred for arguing in the wrong currency, and it is the half
         * that did not work.
         *
         * So the deferral of A4-as-a-positive-claim and the publication of
         * A4's-negative-result pull in opposite directions, and both are right.
         *
         * A separate question, not the same one: the dual's NEGATIVE result
         * (the ascent half transfers, the descent half does not) is currently
         * unpublished and reaches nobody. Releasing that as a short note costs
         * the strategic position little — a negative result about time does not
         * advance time as a currency — and negative results are rarely
         * published at all. Worth deciding on its own merits.
         */
        attribute verdict : String default "defer, do not abandon";
        attribute reason : String default
            "primary: strategic — A4 argues in time, the currency MO-6 exists to displace; "
            + "secondary: evidential — the descent half of the dual fails";
        attribute conditionToPromote : String default
            "BOTH: repair or replace the descent bridge, AND energy established as the "
            + "currency first — then A4 bridges from the established frame to the familiar one";
    }

    part a4Assessment : A4Assessment;

    // ------------------------------------------------------ sequencing verdict

    part def SequencingVerdict {
        doc
        /*
         * The chain A1 -> A2 -> A3 is the mission's critical path, and A3 is its
         * terminus: routing and diagnostics are where stakeholder (B) actually
         * consumes the work, and (B) is the stakeholder the mission's second
         * clause names. A1 is mature and A2 drafted, so the binding constraint
         * on the whole mission is A3.
         *
         * Which sharpens the measurement gap in 03-measures.sysml. MOE-5
         * (adoption in practice) cannot plausibly move before A3 lands, because
         * until then there is no artefact a planning body can route with. The
         * gap is therefore not evidence of a failing mission — it is evidence
         * of an unfinished one, and it has a named unblocker.
         */
        attribute criticalPath : String default "A1 -> A2 -> A3";
        attribute bindingConstraint : String default "A3 — the last link before the mission's terminal use cases";
        attribute offPath : String default "A4 (deferred, see A4Assessment)";
    }

    part sequencing : SequencingVerdict;
}
