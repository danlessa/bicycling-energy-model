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
     * at the bottom, and the interesting thing about them is that all four are
     * still in state 0.
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
}
