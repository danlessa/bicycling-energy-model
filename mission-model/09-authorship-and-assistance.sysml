package AuthorshipAndAssistance {
    doc
    /*
     * Where machine assistance is used, where it stops, and who the artefacts
     * are written FOR. Danilo's policy, 2026-07-30, recorded because it governs
     * the publication state machine rather than sitting beside it.
     *
     * THE POLICY
     *   - LLM assistance belongs to the RESEARCH phase, and to deploying the
     *     research infrastructure.
     *   - Once content and results are frozen, the new draft is written and
     *     diagrammed ENTIRELY BY HUMANS.
     *   - The message is written for humans, by humans.
     *   - EXCEPT for the journal, the repositories and similar artefacts, where
     *     machines are expected to be a main recipient and beneficiary.
     *
     * The policy is not a restriction bolted onto the process; it lands exactly
     * on the state boundary the process already has. State 1's verification gate
     * is "a pre-draft article body is produced and handed over for human writing
     * and diagramming" — that handover IS the policy, and the state machine was
     * drawn before the policy was stated. Two independent framings agreeing on
     * the same boundary is a reason to trust the boundary.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionStakeholders::*;
    import PublicationRoadmap::*;

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
         * Modelling note: a machine is not a STAKEHOLDER here. It has no
         * interest of its own; the interest belongs to the human downstream of
         * it — a student, a planner, an advocate who asks a model about cycling
         * energy and gets an answer grounded in this work rather than
         * hallucinated around it. So machines are modelled as a CHANNEL with
         * distinct requirements, and the stakeholders stay the five already
         * named.
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
        attribute isStakeholder : Boolean default false;
        attribute modelledAs : String default "a channel with distinct requirements; the interest belongs to the human downstream";
        attribute sharpens : String default
            "JScopingGate — retrieval serves fragments, so a withdrawal must be "
            + "structurally inseparable from its correction, not editorially adjacent";
    }

    part machineReadership : MachineReadership;
}
