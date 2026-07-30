package PublicationRoadmap {
    doc
    /*
     * Concrete publication roadmaps: one per article, plus one for J.
     *
     * 06-lifecycle defines the stages; this names the actual steps, in order,
     * with what blocks each. Steps are written so that "done" is checkable —
     * a roadmap whose items cannot be marked finished is a wish list.
     *
     * ONE COST OBSERVATION SHAPES ALL OF IT. A1 carries a large one-time
     * infrastructure cost that A2, A3 and J then inherit for free: the repo
     * filtering, the anonymisation transform, the anonymisation gate script,
     * and the release procedure itself all get built once, at A1. So A1's
     * release is substantially more work than its remaining EDITORIAL work
     * suggests, and A2's is substantially less than its content suggests. Any
     * estimate that reads the two as comparable will be wrong in both
     * directions.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionDeliverables::*;
    import MissionLifecycle::*;
    import SubMissions::*;

    part def Step {
        attribute n : String;
        attribute action : String;
        attribute doneWhen : String;
        attribute blockedBy : String;
    }

    // ======================================================== A1

    part def A1Roadmap {
        doc
        /*
         * A1 is in review with the science settled. Everything remaining is
         * either editorial or infrastructural, and the editorial part is on the
         * critical path to the whole mission (06-lifecycle::CriticalPathFinding).
         *
         * The sequencing risk to watch: steps 1 and 4 are independent and can
         * run in parallel, but step 4 is where the unknown-unknowns live —
         * nobody has yet filtered this repository down to one article's
         * reproduction set. Starting it late is how a release slips.
         */
        attribute stage : String default "Review -> Release";
    }

    part a1s1 : Step {
        attribute redefines n default "A1.1";
        attribute redefines action default
            "Close the review: reframe title/abstract from 'validated' to "
            + "accounting-consistency; promote the out-of-sample 5.6% [5.2, 6.2] "
            + "over the 3.5% calibration figure; elevate 'accurate by "
            + "cancellation' from a §3.2.2 result to a named limitation in §4.3";
        attribute redefines doneWhen default "each review finding is fixed or answered in writing";
        attribute redefines blockedBy default "nothing — a maintainer decision, and the mission's bottleneck";
    }

    part a1s2 : Step {
        attribute redefines n default "A1.2";
        attribute redefines action default
            "Minor review items: thin §3.2.2's four consecutive methodological "
            + "paragraphs, tag pre-registered vs exploratory claims in-text, "
            + "label the eps_d table rows as frozen eps_0";
        attribute redefines doneWhen default "paragraph and per-header audits pass; links resolve";
        attribute redefines blockedBy default "A1.1 (same pass over the text)";
    }

    part a1s3 : Step {
        attribute redefines n default "A1.3";
        attribute redefines action default
            "Propagation: update every number-bearing surface the checklist "
            + "names, then run the FULL gate battery (maintainer-approved) and "
            + "archive its output as-published";
        attribute redefines doneWhen default "battery exits zero; output archived alongside the article";
        attribute redefines blockedBy default "A1.1-A1.2, and the maintainer's approval to run the battery";
    }

    part a1s4 : Step {
        attribute redefines n default "A1.4";
        attribute redefines action default
            "BUILD THE RELEASE INFRASTRUCTURE (one-time, inherited by A2/A3/J): "
            + "the repo-filtering step, the anonymisation transform (file "
            + "dropped, ride -> surrogate in chronological order, date -> "
            + "per-rider rank), and the anonymisation gate script";
        attribute redefines doneWhen default
            "the gate runs against a built A1 repo and passes BOTH halves — "
            + "nothing identifying survives, and the article's statistics "
            + "re-derive with split-halves identical";
        attribute redefines blockedBy default
            "nothing; independent of A1.1-A1.3 and should start in parallel, "
            + "since this is where the unknown-unknowns are";
    }

    part a1s5 : Step {
        attribute redefines n default "A1.5";
        attribute redefines action default
            "Release: mint the DOI, deploy the HTML, update CITATION.cff, "
            + "publish the reproduction repo, and decide the monolith's fate "
            + "(retire unpublished — its DOI is only reserved, so nothing breaks)";
        attribute redefines doneWhen default "DOI resolves; the repo is public; the monolith is explicitly retired";
        attribute redefines blockedBy default "A1.3 and A1.4 both green";
    }

    // ======================================================== A2

    part def A2Roadmap {
        doc
        /*
         * A2's evidence is already done and gated — Entry 41's registered
         * experiment, 1,188 rides. What remains is writing, review, and a
         * release that inherits A1's infrastructure. This is the cheapest of the
         * three articles by a wide margin, and its scope discipline (a ~4-page
         * letter, not a full article) is what keeps it that way.
         */
        attribute stage : String default "Draft";
    }

    part a2s1 : Step {
        attribute redefines n default "A2.1";
        attribute redefines action default "Complete the letter from the existing 187-line draft; hold the ~4-page target";
        attribute redefines doneWhen default "every number traceable to a gated source; the smoothing prescription stated a priori";
        attribute redefines blockedBy default "nothing — can proceed during A1's review";
    }
    part a2s2 : Step {
        attribute redefines n default "A2.2";
        attribute redefines action default "External review round";
        attribute redefines doneWhen default "findings fixed or answered";
        attribute redefines blockedBy default "A2.1";
    }
    part a2s3 : Step {
        attribute redefines n default "A2.3";
        attribute redefines action default "Build the A2 reproduction repo by reusing A1's filtering + anonymisation + gate";
        attribute redefines doneWhen default "the gate passes both halves on the A2 repo";
        attribute redefines blockedBy default "A1.4 (the infrastructure), not A1.5";
    }
    part a2s4 : Step {
        attribute redefines n default "A2.4";
        attribute redefines action default "Release citing A1's DOI";
        attribute redefines doneWhen default "DOI resolves; the citation to A1 resolves";
        attribute redefines blockedBy default "A1.5 — a citation needs a DOI that exists";
    }

    // ======================================================== A3

    part def A3Roadmap {
        doc
        /*
         * A3 is a scaffold, and its first step is a DECISION rather than work:
         * whether the discretisation claim rests on the existing edge-cost
         * entries (19-21 on scale and resolution, 23 and 25 on grid
         * connectivity, 26 on the direction ladder and portals) or needs its own
         * registered experiment. That decision sets everything after it, and
         * getting it wrong in the cheap direction — writing first, discovering
         * the gap in review — is the expensive failure.
         *
         * A3 also carries the mission's own open question, which no other
         * article can answer (SubMissions::SM3Measures): how often, on a real
         * network, the energy-optimal path departs from the distance-optimal
         * one. That is what makes MO-6 operational rather than philosophical,
         * and it is a measurement nobody has made.
         */
        attribute stage : String default "Scaffold";
    }

    part a3s1 : Step {
        attribute redefines n default "A3.1";
        attribute redefines action default
            "DECIDE: does the discretisation claim rest on Entries 19-21, 23, 25 "
            + "and 26, or does it need its own registered experiment?";
        attribute redefines doneWhen default "the decision is written down with its reasoning";
        attribute redefines blockedBy default "nothing — and it is A3's true next step";
    }
    part a3s2 : Step {
        attribute redefines n default "A3.2";
        attribute redefines action default
            "If a new experiment is needed: register it (estimand, instrument, "
            + "predictions, failure modes) BEFORE running, then run and gate";
        attribute redefines doneWhen default "entry registered, run, results recorded including failures, gate section added";
        attribute redefines blockedBy default "A3.1";
    }
    part a3s3 : Step {
        attribute redefines n default "A3.3";
        attribute redefines action default
            "Measure the divergence: how often does the energy-optimal path "
            + "differ from the distance-optimal one on a real network, and by "
            + "how much? Entry 26's ladder and detour data are the seed";
        attribute redefines doneWhen default "a distribution, not an anecdote — with the network and endpoints stated";
        attribute redefines blockedBy default
            "nothing technical; this is the measurement that makes MO-6 "
            + "operational and it has never been made";
    }
    part a3s4 : Step {
        attribute redefines n default "A3.4";
        attribute redefines action default "Draft -> review -> reproduction repo -> release citing A2";
        attribute redefines doneWhen default "DOI resolves; gate passes; citation to A2 resolves";
        attribute redefines blockedBy default "A3.2, A3.3, and A2.4 for the citation";
    }

    // ======================================================== J

    part def JRoadmap {
        doc
        /*
         * J is sequenced after A3 and deliberately unscoped until reached. Its
         * roadmap is therefore shorter and its first step is the scoping gate,
         * not assembly.
         *
         * J's release model differs from the articles' in a way that matters.
         * An article is a frozen snapshot; J is an append-only log that keeps
         * growing. So J wants a CONCEPT DOI with dated versions rather than a
         * single record — and that is not a compromise, it is the honest shape
         * of the artefact. A lab journal that stopped when it was published
         * would be a different and less useful thing.
         */
        attribute stage : String default "Proposed; scoping not started";
    }

    part js1 : Step {
        attribute redefines n default "J.1";
        attribute redefines action default
            "Scoping, whose exit criterion is the structural answer to the "
            + "hostile-reading risk: no admission reachable without its "
            + "resolution in view (MissionDeliverables::JScopingGate)";
        attribute redefines doneWhen default
            "the adversarial test passes — for each enumerated damaging passage, "
            + "a reader cannot reach it without its correction";
        attribute redefines blockedBy default "A3 released (priority decision)";
    }
    part js2 : Step {
        attribute redefines n default "J.2";
        attribute redefines action default
            "Assemble one navigable surface over the existing components, "
            + "rendering the claims graph's disputes/qualifies/corrects edges as "
            + "ADJACENCY rather than as a graph to traverse deliberately";
        attribute redefines doneWhen default "the surface satisfies J.1's criterion by construction, not by discipline";
        attribute redefines blockedBy default "J.1";
    }
    part js3 : Step {
        attribute redefines n default "J.3";
        attribute redefines action default
            "Add the missing traceability direction: article claim -> the entry "
            + "that established it -> the output evidencing it -> the gate that "
            + "re-derives it. The entry->output->gate half exists; the article-> "
            + "entry half does not";
        attribute redefines doneWhen default "every claim in A1-A3 resolves to its entry, machine-readably";
        attribute redefines blockedBy default "A1-A3 published, so the claims are fixed targets";
    }
    part js4 : Step {
        attribute redefines n default "J.4";
        attribute redefines action default
            "Front matter: quantify the norm — pre-registrations, withdrawals, "
            + "predictions recorded as failed — so the tally is read before the "
            + "corpus";
        attribute redefines doneWhen default "counts are computed from the journal, not asserted";
        attribute redefines blockedBy default "J.2";
    }
    part js5 : Step {
        attribute redefines n default "J.5";
        attribute redefines action default "Release with a CONCEPT DOI and dated versions, since J keeps growing";
        attribute redefines doneWhen default "concept DOI resolves to the latest version; the versioning policy is stated";
        attribute redefines blockedBy default "J.1-J.4";
    }

    // ======================================================== shape

    part def RoadmapShape {
        doc
        /*
         * What the four roadmaps look like together.
         *
         * PARALLELISM IS AVAILABLE AND UNDERUSED. A1.4 (release infrastructure)
         * and A2.1 (the letter) are both unblocked right now and neither
         * competes with A1.1's editorial pass. The critical path runs through
         * the editorial work; everything else can be moved off it.
         *
         * COSTS ARE FRONT-LOADED, NOT EVEN. A1 pays once for filtering,
         * anonymisation and the gate; A2 and A3 inherit them. Reading the three
         * as comparable efforts overestimates A2 and A3 and underestimates A1.
         *
         * THE MISSION'S OWN MEASUREMENT SITS IN A3.3, not in any article's
         * argument. Whether energy-optimal routing materially differs from
         * distance-optimal routing is the question MO-6 rests on, and it is one
         * step in one roadmap, currently unblocked and unstarted.
         *
         * AND ONE HONEST NOTE ON ORDER. The whole chain queues behind two
         * editorial decisions in A1.1. That is not a criticism of the science —
         * it is a scheduling fact, and the useful response is to treat A1.1 as a
         * decision to be MADE rather than work to be done.
         */
        attribute unblockedNow : String default "A1.1 (decision), A1.4 (infrastructure), A2.1 (drafting), A3.1 (decision), A3.3 (measurement)";
        attribute criticalPath : String default "A1.1 -> A1.2 -> A1.3 -> A1.5 -> A2.4 -> A3.4 -> J";
        attribute frontLoaded : String default "A1 pays the one-time release infrastructure; A2, A3 and J inherit it";
    }

    part shape : RoadmapShape;
}
