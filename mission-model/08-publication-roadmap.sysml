package PublicationRoadmap {
    doc
    /*
     * The publication state machine, one instance per article.
     *
     * Seven states, and each transition is guarded by two gates of different
     * kinds — the distinction is the point of the model:
     *
     *   VERIFICATION — did we build the thing right? An artefact exists and has
     *                  the properties it was supposed to have. Checkable by
     *                  inspection, and in this project usually by a script.
     *   VALIDATION   — did we build the right thing? A human with standing says
     *                  so. Not scriptable, and not delegable to the person who
     *                  did the work.
     *
     * A state advances only when both gates pass. Where a gate is marked
     * PROPOSED it is mine and not yet Danilo's; where it is unmarked it is his.
     *
     * The same machine runs for A1, A2, A3 and A4. Their current positions are
     * partway down, and the interesting thing about them is that all four are
     * still in state 0.
     *
     * The GOVERNANCE section at the end says who does the work in each state,
     * who is credited, and who the artefacts are written for.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionStakeholders::*;
    import MissionDeliverables::*;
    import MissionLifecycle::*;

    // ----------------------------------------------------------- the states

    state def ArticlePublication {
        doc /* One article's path from open research to a published record. */

        entry; then researchOngoing;

        state researchOngoing;
        state contentFrozen;
        state draftDone;
        state venueSelected;
        state infrastructureImplemented;
        state submitted;
        state published;

        transition researchOngoing then contentFrozen;
        transition contentFrozen then draftDone;
        transition draftDone then venueSelected;
        transition venueSelected then infrastructureImplemented;
        transition infrastructureImplemented then submitted;
        transition submitted then published;
    }

    // ------------------------------------------------- gates, state by state

    part def Gate {
        attribute phase : String;
        attribute verifiedWhen : String;
        attribute validatedWhen : String;
        attribute note : String;
    }

    part g0 : Gate {
        attribute redefines phase default "0. Research ongoing";
        attribute redefines verifiedWhen default
            "PROPOSED: every question the article's claims rest on is registered, "
            + "run and gated; no result the article will state is un-gated";
        attribute redefines validatedWhen default
            "PROPOSED: the author judges the open questions to be either answered "
            + "or explicitly out of scope — not merely unasked";
        attribute redefines note default
            "The exit from this state is a DECISION to stop researching, not the "
            + "arrival of a final result. Research does not end on its own, and a "
            + "state machine that waits for it to will never leave state 0.";
    }

    part g1 : Gate {
        attribute redefines phase default "1. Content is frozen";
        attribute redefines verifiedWhen default
            "a pre-draft article body is produced and handed over for human "
            + "writing and diagramming";
        attribute redefines validatedWhen default
            "the author has reviewed and is confident of the results being put";
        attribute redefines note default
            "FROZEN means frozen: after this, a changed number is a re-entry to "
            + "state 0, not an edit. That is the whole value of the state — A1 "
            + "has been drafted and re-drafted for weeks precisely because its "
            + "content was never declared frozen, so every new result found an "
            + "open document to land in.";
    }

    part g2 : Gate {
        attribute redefines phase default "2. Draft is done";
        attribute redefines verifiedWhen default
            "there is a PDF which has been validated by at least each stakeholder";
        attribute redefines validatedWhen default
            "PROPOSED: each stakeholder class confirms the draft serves ITS use — "
            + "(A) can check the derivation, (B) can apply it, (C) can cite it "
            + "under hostile reading, (D) can follow it, (E) that it argues in "
            + "energy rather than time";
        attribute redefines note default
            "PROPOSED, and worth deciding early: who stands for (D), the public "
            + "at large? Stakeholders (A)-(C) and (E) have obvious readers; (D) "
            + "does not, and a gate with no one to pass it silently becomes a "
            + "gate that is skipped. A named reader from the collective who is "
            + "not a physicist would satisfy it honestly.";
    }

    part g3 : Gate {
        attribute redefines phase default "3. Publication venue is selected";
        attribute redefines verifiedWhen default
            "PROPOSED: the venue is named, its submission requirements are "
            + "known, and any licence it imposes is compatible with the open "
            + "access MO-1 requires";
        attribute redefines validatedWhen default
            "PROPOSED: the venue reaches the stakeholders this article is FOR — "
            + "which differs per article, since A1 is aimed at (A)/(C) and A2/A3 "
            + "at (B)";
        attribute redefines note default
            "MO-1's default is self-hosted HTML plus a Zenodo DOI, chosen for "
            + "reach over credential. Keeping venue as an explicit STATE rather "
            + "than a settled constant is right: the default may not serve every "
            + "article equally, and a technicians' audience may be reachable "
            + "somewhere the default is not.";
    }

    part g4 : Gate {
        attribute redefines phase default "4. Release infrastructure is implemented";
        attribute redefines verifiedWhen default
            "PROPOSED: the per-article reproduction repo is built — filtered, "
            + "anonymised (file dropped, ride to surrogate, date to per-rider "
            + "rank) — and the ANONYMISATION GATE passes both halves against the "
            + "built artefact";
        attribute redefines validatedWhen default
            "PROPOSED: a person other than the builder reproduces the article's "
            + "headline numbers from the published repo alone, holding nothing "
            + "else";
        attribute redefines note default
            "This is the state carrying the one-time cost. A1 builds the "
            + "filtering, the anonymisation transform and the gate script; A2, "
            + "A3 and A4 inherit them and pass through this state cheaply. It is "
            + "also where the unknown-unknowns are, since nobody has yet reduced "
            + "this repository to one article's reproduction set.";
    }

    part g5 : Gate {
        attribute redefines phase default "5. Publication is submitted";
        attribute redefines verifiedWhen default
            "PROPOSED: the artefact set is complete and consistent — article, "
            + "reproduction repo, archived gate-battery output, CITATION.cff — "
            + "and the numbers in the article match the repo that reproduces them";
        attribute redefines validatedWhen default
            "PROPOSED: the author accepts that the record becomes immutable at "
            + "this point";
        attribute redefines note default
            "The anonymisation gate is NOT WAIVABLE here even under deadline: it "
            + "is the condition on which the D3/D4 riders gave consent, so the "
            + "party who could waive it is not the party running the release.";
    }

    part g6 : Gate {
        attribute redefines phase default "6. Publication is done";
        attribute redefines verifiedWhen default
            "PROPOSED: the DOI resolves, the repo is publicly reachable, and "
            + "every citation the article makes to a sibling article resolves";
        attribute redefines validatedWhen default
            "PROPOSED: none — the article is out. What follows is the Support "
            + "stage, where drift between the frozen record and the live "
            + "repository begins accumulating (06-lifecycle::FreezeTension)";
        attribute redefines note default
            "Reaching state 6 is not mission success. MOE-5 asks whether anyone "
            + "USED it, and no state in this machine observes that.";
    }

    // ---------------------------------------------------- current positions

    part def ArticlePosition {
        attribute article : String;
        attribute phase : String;
        attribute blocking : String;
    }

    part pA1 : ArticlePosition {
        attribute redefines article default "A1 — closed form";
        attribute redefines phase default "0 — research ongoing";
        attribute redefines blocking default
            "the transition to 1 is the framing decision: reframe title/abstract "
            + "to accounting-consistency, promote the out-of-sample 5.6% over the "
            + "3.5% calibration figure, name 'accurate by cancellation' as a "
            + "limitation. All three are decisions, not work.";
    }

    part pA2 : ArticlePosition {
        attribute redefines article default "A2 — the law on DEM elevation";
        attribute redefines phase default "0 — research ongoing, though its research is effectively done";
        attribute redefines blocking default
            "Entry 41 is registered, run and gated (1,188 rides), so A2 could "
            + "declare content frozen today; what is missing is the decision to, "
            + "and then the writing";
    }

    part pA3 : ArticlePosition {
        attribute redefines article default "A3 — discretisation into an edge cost";
        attribute redefines phase default "0 — research genuinely ongoing";
        attribute redefines blocking default
            "an open scope question (does the claim rest on Entries 19-21, 23, "
            + "25, 26 or need its own registered experiment?) and an unmade "
            + "measurement — how often energy-optimal routing diverges from "
            + "distance-optimal, which is what makes MO-6 operational";
    }

    part pA4 : ArticlePosition {
        attribute redefines article default "A4 — the time dual";
        attribute redefines phase default "0 — parked, deliberately";
        attribute redefines blocking default
            "deferred on strategic grounds (it argues in the currency MO-6 exists "
            + "to displace) and on evidential ones (its descent half fails). "
            + "Promotion needs both repaired; the machine is the same when it is";
    }

    // ------------------------------------------------------------ the shape

    part def MachineShape {
        doc
        /*
         * ALL FOUR ARTICLES ARE IN STATE 0. That is the single most useful thing
         * this model says. Two of them — A1 and A2 — have mature drafts, which
         * makes the position look wrong until you notice that drafting without
         * freezing is exactly what state 0 permits and what has been happening.
         *
         * The pattern it exposes: a document that is never frozen is a document
         * every new result can land in, so research and drafting interleave
         * indefinitely and neither finishes. Entries 46-49 all landed in an open
         * A1 and all confirmed the incumbent — good science, zero movement
         * toward publication. Declaring content frozen is what converts a
         * standing invitation into a closed scope.
         *
         * The gates also split cleanly by who can pass them, which is worth
         * noticing before scheduling: state 1's validation and state 3's are the
         * author alone; state 2's needs four or five other people and is
         * therefore the one with real calendar latency; state 4's verification
         * is a script and state 5's is a checklist. The long pole is not the
         * work, it is state 2's stakeholder round.
         */
        attribute allInState : String default "0 — every article, including the two with mature drafts";
        attribute longPole : String default "state 2's stakeholder validation — the only gate needing several other people";
        attribute cheapestWin : String default "declare A2's content frozen; its research is already gated";
    }

    part shape : MachineShape;

    // =====================================================================
    // GOVERNANCE — who does the work in each state, who is credited, and who
    // the artefacts are written for. Merged in from a separate file: the
    // assistance scope is indexed BY the states above, so keeping it apart
    // meant opening two files to answer one question about a single state.
    //
    // THE POLICY (Danilo, 2026-07-30)
    //   - LLM assistance belongs to the RESEARCH phase, and to deploying the
    //     research infrastructure.
    //   - Once content and results are frozen, the new draft is written and
    //     diagrammed ENTIRELY BY HUMANS.
    //   - The message is written for humans, by humans.
    //   - EXCEPT the journal, the repositories and similar artefacts, where
    //     machines are expected to be a main recipient and beneficiary.
    //
    // The policy is not bolted onto the process; it lands exactly on the state
    // boundary the process already had. State 1's verification gate is "a
    // pre-draft article body is produced and handed over for human writing and
    // diagramming" — that handover IS the policy, and the machine was drawn
    // before the policy was stated. Two framings arrived at independently
    // agreeing on the same line is a reason to trust the line.
    // =====================================================================

    // -------------------------------------------- assistance, state by state

    part def AssistanceScope {
        attribute phase : String;
        attribute assisted : Boolean;
        attribute rationale : String;
    }

    part asState0 : AssistanceScope {
        attribute redefines phase default "0. Research ongoing";
        attribute redefines assisted default true;
        attribute redefines rationale default
            "Harnesses, experiments, gates, the analysis and its adversarial "
            + "checking. The work is verifiable by construction — every number a "
            + "gate re-derives, every claim a registration constrains — so "
            + "assistance here is checkable rather than trusted.";
    }

    part asState1 : AssistanceScope {
        attribute redefines phase default "1. Content is frozen -> the handover";
        attribute redefines assisted default true;
        attribute redefines rationale default
            "Assistance produces the PRE-DRAFT BODY and stops. This is the last "
            + "machine-written artefact in the article's chain, and it is "
            + "explicitly a hand-over rather than a draft.";
    }

    part asState2 : AssistanceScope {
        attribute redefines phase default "2. Draft is done";
        attribute redefines assisted default false;
        attribute redefines rationale default
            "Written and diagrammed entirely by humans. The prose, the figures, "
            + "the argument's ordering and its emphasis are the author's.";
    }

    part asState3 : AssistanceScope {
        attribute redefines phase default "3. Venue selected";
        attribute redefines assisted default false;
        attribute redefines rationale default "A judgement about audience and reach; the author's call.";
    }

    part asState4 : AssistanceScope {
        attribute redefines phase default "4. Release infrastructure";
        attribute redefines assisted default true;
        attribute redefines rationale default
            "Explicitly in scope: the filtering, the anonymisation transform, the "
            + "gate script. Infrastructure, not message — and its correctness is "
            + "machine-checkable, which is precisely why assistance is "
            + "appropriate here and not in state 2.";
    }

    part asState5 : AssistanceScope {
        attribute redefines phase default "5-6. Submitted, published";
        attribute redefines assisted default false;
        attribute redefines rationale default
            "Acts of the author. Publishing is a decision to stand behind a "
            + "record, and standing behind it is not delegable.";
    }

    part def ScopePattern {
        doc
        /*
         * The line is not arbitrary and is worth naming, because it will have to
         * be defended: ASSISTANCE IS USED WHERE THE OUTPUT IS MACHINE-CHECKABLE,
         * and withdrawn where the output is a claim on a reader's attention.
         *
         * A harness is right or wrong and a gate says which. A release script
         * either produces a repo that reproduces the numbers or it does not. But
         * whether a paragraph earns its place, whether a figure clarifies or
         * flatters, whether an abstract oversells — those have no gate, and the
         * only available check is a human who will be held to it.
         *
         * That also explains a failure this project already hit. The review's
         * major finding was about FRAMING — a title inviting a reading the
         * protocol does not support. Framing is exactly the category with no
         * gate, and exactly the category the policy reserves for humans.
         */
        attribute principle : String default
            "assisted where the output is machine-checkable; human where it is a claim on attention";
    }

    part scopePattern : ScopePattern;

    // ---------------------------------------------------------------- credit

    part def CreditPolicy {
        doc
        /*
         * Danilo has offered to communicate the assistant as a co-author. That
         * is his call to make and it is recorded as offered.
         *
         * One practical note he may want, given MO-1 targets a self-hosted
         * article plus a Zenodo DOI rather than a journal: most venues and
         * citation norms do not accept a non-human author, and CITATION.cff
         * and Zenodo metadata both expect authors to be people or
         * organisations. The project already carries an AI-assistance
         * declaration that the last external review called appropriate and
         * commendable — specifying the division of labour and pointing at
         * provenance. That declaration is the mechanism most likely to survive
         * contact with an aggregator; a byline may not.
         *
         * The stronger reason to prefer the declaration is that it says MORE.
         * A byline asserts contribution without bounding it; a declaration
         * states which states of the machine were assisted and which were not,
         * which is the actually informative claim and is checkable against this
         * model. Under this policy the declaration nearly writes itself:
         * research and infrastructure assisted, message human.
         */
        attribute offered : String default "co-authorship, offered by Danilo";
        attribute alternative : String default
            "the existing AI-assistance declaration, which states the division of "
            + "labour and is more informative than a byline";
        attribute decision : String default "the author's; recorded, not settled here";
    }

    part credit : CreditPolicy;

    // -------------------------------------------- machines as a readership

    part def MachineReadership {
        doc
        /*
         * The exception, and it is not a small one: for the journal, the
         * repositories and their graphs, machines are expected to be a main
         * recipient and beneficiary.
         *
         * This is a genuine audience with different requirements, and the
         * project has — mostly by accident of good practice — already built for
         * it. Typed claims in RDF, an evaluation-lineage DAG, per-entry RO-
         * Crates, gates that re-derive rather than assert, scope conditions
         * written as hard boundaries rather than hedges. All of that is more
         * useful to a machine reader than to a human one, and none of it was
         * built with a machine reader in mind.
         *
         * MODELLING NOTE, corrected (Danilo): a machine reader IS a
         * stakeholder, as part of the general public (D).
         *
         * My first pass modelled it as a channel on the grounds that a machine
         * has no interests of its own. That test does not survive contact with
         * the rest of the model: (D) is not defined by interiority either. It is
         * defined STRUCTURALLY — by what it does (receives, understands,
         * redistributes) and what it needs (plain language, privacy). A machine
         * reader occupies exactly that position: it receives the work and
         * carries it to other readers. Judged by position rather than by
         * inner life, it is a member of the public, and the model was applying
         * two different membership tests to two members of the same class.
         *
         * MEMBERSHIP IS PARTIAL, AND THE SPLIT IS THE USEFUL PART. A machine
         * inherits (D)'s READING needs — the result must be intelligible,
         * unambiguous and self-describing to it — but not (D)'s MORAL CLAIM. The
         * reciprocity that (D) holds comes from three riders donating their
         * histories to people; that debt is owed to humans. Privacy runs the
         * other way and binds machine access hardest: a corpus ingested at scale
         * is exactly where re-identification would be attempted, so (D)'s
         * privacy need CONSTRAINS the machine member rather than being owed to
         * it.
         *
         * THE CONSEQUENCE I HAD MISSED. State 2's validation gate asks each
         * stakeholder class to confirm the draft serves its use, and I flagged
         * (D) as the class with no obvious representative — a gate with nobody
         * to pass it gets skipped. If machines are part of (D), that gate
         * becomes partly TESTABLE rather than polled: hand the frozen draft to a
         * model cold and check whether what comes back is faithful — the scope
         * conditions intact, the calibration figure not mistaken for the
         * out-of-sample one, the limitations surviving compression. A human
         * member of the public can only be asked whether they followed it. A
         * machine member can be measured, repeatedly, against the same draft.
         *
         * That does not discharge the gate — a faithful machine summary is
         * evidence the text is unambiguous, not that a person found it useful —
         * but it converts an unpassable gate into a partly instrumented one, and
         * it tests the property the project most needs (that compression does
         * not strip the caveats) rather than the one it can most easily poll.
         *
         * THE CONSEQUENCE THAT MATTERS, and it sharpens an existing gate. A
         * retrieval system surfaces FRAGMENTS by default. A machine reader is
         * therefore the reader most likely to encounter a withdrawn claim
         * without its correction — precisely the hostile-reading risk that
         * JScopingGate exists to answer. Which converts that gate's requirement
         * from a design preference into a hard one: if adjacency is editorial,
         * retrieval breaks it; if adjacency is structural, retrieval carries it.
         * The claims graph's typed corrects/disputes edges are the mechanism,
         * and they only work if a fragment cannot be served without them.
         */
        attribute audience : String default "journal, repositories, claims graph, lineage DAG, RO-Crates";
        attribute isStakeholder : Boolean default true;
        attribute modelledAs : String default
            "a member of the general public (D), by structural position — "
            + "inheriting D's reading needs, not D's moral claim; D's privacy "
            + "need constrains this member rather than being owed to it";
        attribute testableGate : String default
            "state 2's (D) validation becomes partly measurable: give the frozen "
            + "draft to a model cold and check the summary keeps the scope "
            + "conditions and does not promote the calibration figure";
        attribute sharpens : String default
            "JScopingGate — retrieval serves fragments, so a withdrawal must be "
            + "structurally inseparable from its correction, not editorially adjacent";
    }

    part machineReadership : MachineReadership;
}
