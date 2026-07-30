package MissionLifecycle {
    doc
    /*
     * Life cycle concepts for the deliverables, and the release roadmap for
     * A1 -> A2 -> A3.
     *
     * Starting position: NOTHING IS PUBLISHED YET. A monolithic working paper
     * exists in the repository and a Zenodo DOI is RESERVED for it
     * (10.5281/zenodo.21282165), but that is a draft reservation, not a public
     * record. So A1 will be this project's FIRST public release, and the
     * monolith is a draft to be retired rather than a record to be superseded.
     *
     * That makes A1's release more consequential than a decomposition would be:
     * there is no prior public artefact absorbing scrutiny, no existing
     * citation to inherit, and no published claim already carrying the caveats.
     * Everything the mission asserts in public, A1 asserts first.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionDeliverables::*;
    import MissionMeasures::*;

    // ------------------------------------------------------- life cycle stages

    part def Stage {
        attribute name : String;
        attribute entryCriterion : String;
        attribute exitCriterion : String;
    }

    part sScoping : Stage {
        doc
        /*
         * A stage the articles do not need and J does: deciding what the
         * deliverable IS. Its exit criterion is unusual in carrying a design
         * constraint rather than an evidence threshold — see
         * MissionDeliverables::JScopingGate.
         */
        attribute redefines name default "0. Scoping (non-article deliverables only)";
        attribute redefines entryCriterion default "a deliverable proposed but not defined";
        attribute redefines exitCriterion default
            "scope settled AND a structural answer to the deliverable's central "
            + "presentation risk — for J, that no admission is reachable without "
            + "its resolution in view, tested adversarially against the most "
            + "damaging out-of-context passages";
    }

    part sRegistration : Stage {
        attribute redefines name default "1. Registration (concept)";
        attribute redefines entryCriterion default "a question worth an experiment";
        attribute redefines exitCriterion default
            "a numbered lab-journal entry exists stating the estimand, the "
            + "instrument, the predictions AND the failure modes, written before "
            + "any result is inspected";
    }

    part sEvidence : Stage {
        attribute redefines name default "2. Evidence (development)";
        attribute redefines entryCriterion default "registration committed";
        attribute redefines exitCriterion default
            "harness written and run; results recorded including failed "
            + "predictions; every published figure gated in bootstrap_ci.py; "
            + "RO-Crate packaged";
    }

    part sDraft : Stage {
        attribute redefines name default "3. Draft";
        attribute redefines entryCriterion default "evidence gated";
        attribute redefines exitCriterion default
            "every number in the prose traceable to a gated source; scope "
            + "conditions stated as hard boundaries; lineage in the captions";
    }

    part sReview : Stage {
        attribute redefines name default "4. Review";
        attribute redefines entryCriterion default "draft complete";
        attribute redefines exitCriterion default
            "at least one external review round; every finding either fixed or "
            + "answered in writing; arithmetic and internal-consistency checks "
            + "independently reproduced";
    }

    part sRelease : Stage {
        attribute redefines name default "5. Release (production)";
        attribute redefines entryCriterion default "review closed, FULL gate battery green";
        attribute redefines exitCriterion default
            "DOI minted; HTML deployed; CITATION.cff updated; the propagation "
            + "checklist run across every number-bearing surface; the gate "
            + "battery output archived AS PUBLISHED; and a REPRODUCTION REPO "
            + "published alongside, which cannot be published until the "
            + "ANONYMISATION GATE passes (blocking — see AnonymisationGate)";
    }

    part sUtilization : Stage {
        attribute redefines name default "6. Utilization";
        attribute redefines entryCriterion default "released";
        attribute redefines exitCriterion default "none — this is where MOE-5 would be observed, if anything observed it";
    }

    part sSupport : Stage {
        attribute redefines name default "7. Support";
        attribute redefines entryCriterion default "released and the repository still moving";
        attribute redefines exitCriterion default "none — runs until retirement; see the freeze tension below";
    }

    part sRetirement : Stage {
        attribute redefines name default "8. Supersession / retirement";
        attribute redefines entryCriterion default "a later work covers the same claim better";
        attribute redefines exitCriterion default
            "the superseded record carries an explicit machine-readable relation "
            + "to its successor; it is never silently deleted or quietly edited";
    }

    // ------------------------------------------ the tension the life cycle has

    part def FreezeTension {
        doc
        /*
         * A published DOI is immutable; this repository is not. Entry 27
         * re-baselined gravity and moved every assumed-parameter number in the
         * project by up to 0.2 pp. A future re-baseline will do the same. So
         * the moment A1 is released, the repository's numbers and the published
         * numbers begin to diverge, and nothing currently detects that.
         *
         * The distinction that resolves it: a released article is a SNAPSHOT of
         * a claim, not a view onto the live repository. What must be archived at
         * release is therefore not just the prose but the evidence state — the
         * RO-Crates and the gate-battery output as it stood — so a reader in two
         * years can tell whether a disagreement with today's code is a drift or
         * an error.
         *
         * Policy, stated so the decision is not made ad hoc under pressure:
         *   - a number moving within its published CI  -> no action, drift noted in the journal
         *   - a number moving outside its published CI -> new version, old one related not replaced
         *   - a claim REVERSED                         -> erratum on the record, prominently
         * The middle case is the one that will actually occur and the one most
         * likely to be fudged.
         */
        attribute publishedIsImmutable : Boolean default true;
        attribute repositoryIsLive : Boolean default true;
        attribute detectionMechanism : String default "NONE — nothing compares a released article against current numbers";
    }

    part freezeTension : FreezeTension;

    // -------------------------------------------------- the reproduction repo

    part def ReproductionRepo {
        doc
        /*
         * DECISION (Danilo): A1/A2/A3 each ship with a repository that
         * reproduces the results written in that article AND NOTHING ELSE —
         * including the data, anonymised and filtered. One repo per article, a
         * filtered and cleaned-up subset of this one.
         *
         * The "nothing else" is the load-bearing half. A reproduction repo is
         * not a copy of the working repository with secrets removed; it is a
         * minimal artefact built to a single question — can a reader re-derive
         * the numbers in THIS article? Everything not answering that question is
         * a liability: other articles' harnesses invite scope confusion, the lab
         * journal belongs to J, and each extra path is another place a private
         * one can hide.
         *
         * WHAT MAKES THIS TRACTABLE is the I/T/O/S layering. The repo ships the
         * O layer (per-ride outputs), the T layer (the transformers that made
         * them) and the S derivation (the gate battery subset that re-derives
         * the published statistics). It does NOT ship D — no raw tracks, no
         * geometry, nothing with a coordinate in it. Every published number in
         * these articles is a statistic over O, so O is sufficient: the reader
         * reproduces the RESULTS without ever holding the rides.
         */
        attribute perArticle : Boolean default true;
        attribute ships : String default "O (per-ride outputs, anonymised) + T (the harnesses) + the gate subset + the article";
        attribute excludes : String default "D (raw tracks, any coordinate), other articles' machinery, the lab journal (that is J)";
    }

    part def AnonymisationDesign {
        doc
        /*
         * The apparent tension — exact reproducibility versus anonymisation
         * strength — largely dissolves once the identifying surface is measured
         * rather than assumed.
         *
         * ACROSS EVERY RESULT CSV THERE ARE THREE IDENTIFYING FIELDS: `ride`
         * (a name), `date`, and `file` (a path). Everything else is aggregate:
         * distance, ascent, energy, fitted constants, errors. So the question is
         * only what those three cost to remove.
         *
         *   file  -> dropped outright. Nothing consumes it.
         *   ride  -> surrogate identifier.
         *   date  -> a per-rider MONOTONIC RANK, not a calendar value.
         *
         * The date substitution is the one that matters and it costs nothing.
         * The only published statistics touching dates are the chronological
         * split-halves (Entries 44, 47, 49), which sort by date and assign
         * half = index % 2 — they consume the ORDER and never the value. A rank
         * preserves every such operation exactly. Assign the surrogate IDs in
         * chronological order too, so sorting by surrogate reproduces sorting by
         * date including tie-breaks, and the split-halves come out identical.
         *
         * That leaves the residual risk worth stating plainly: per-ride
         * distance-and-ascent rows remain a weak fingerprint against a public
         * activity profile. Removing the calendar value is what takes this from
         * near-certain matching to weak matching — a date plus a distance
         * identifies a ride, a distance alone mostly does not. Perturbing the
         * values would reduce it further and would break exact reproduction,
         * which is the one thing the repo exists to provide. The recommended
         * trade is therefore exact values, no dates, surrogate IDs.
         *
         * ON PUBLISHING A CENTROID. The proposal was one number per track. I would
         * argue against it at per-ride grain, on this project's own precedent.
         *
         * A per-ride centroid is endpoint-derived geometry wearing a disguise.
         * For a loop starting at home it sits near the home; over 441 rides of
         * one rider the density peak IS the home, recoverable by anyone who
         * plots them. This is the exact failure Entry 26 caught mid-experiment —
         * crop bboxes derived from ride endpoints, which invert back to those
         * endpoints — and the same reason D6's tracks are gitignored despite an
         * open licence. Quantisation does not save it: coarsening to ~10 km
         * still leaves a peak once there are hundreds of samples, because the
         * signal is in the repetition, not the resolution.
         *
         * And it buys nothing the repo exists for. NO published statistic in
         * A1-A3 depends on where a ride happened; location enters only through
         * the wind estimate, whose OUTPUT (wind_ms) is already in O without its
         * input. By the repo's own rule — ship what reproduces the results and
         * nothing else — per-ride centroids are excluded on reproducibility
         * grounds before privacy is even considered.
         *
         * What a reader legitimately needs is geographic CONTEXT: is this São
         * Paulo or the Alps, and what terrain does that imply? That is served
         * completely by one coarse centroid per rider or per corpus — a fact the
         * articles already state in prose. So: one per corpus, never one per
         * ride. The distinction costs the reader nothing and removes the vector
         * entirely.
         *
         * CONSENT IS A SEPARATE QUESTION FROM ANONYMITY, and is the open action.
         * D6 is CC BY 4.0, so derived aggregates are publishable outright.
         * D1 and D5 are the author's own. But D3 and D4 were shared by
         * independent riders for ANALYSIS; publishing per-ride derived rows is a
         * new use, however anonymised, and should be asked rather than assumed.
         * That request is the thing to raise early — it gates A1's release and
         * has a human on the other end of it.
         */
        attribute identifyingFields : String default "ride, date, file — measured across every result CSV, not assumed";
        attribute tracksExcluded : String default
            "already satisfied by construction: the O layer carries NO coordinates. "
            + "Verified column by column — `x` is distance-along-route in metres "
            + "(the engine convention), geoCov/geo_span are coverage fractions. "
            + "Rename or document `x` in the release: to an outside auditor "
            + "scanning for coordinates it reads like a longitude.";
        attribute centroidPolicy : String default
            "ONE coarse centroid per rider/corpus, never per ride";
        attribute substitution : String default "file dropped; ride -> surrogate; date -> per-rider monotonic rank";
        attribute costsReproducibility : Boolean default false;
        attribute residualRisk : String default "aggregate rows are a weak fingerprint; removing dates is what makes it weak";
        attribute openAction : String default "renewed consent from the D3 and D4 riders for publishing derived per-ride rows";
    }

    part def AnonymisationGate {
        doc
        /*
         * BLOCKING GATE on publishing a per-article reproduction repo. Nothing
         * is pushed until it passes, and it runs against the RELEASE ARTEFACT
         * rather than the working repository — the whole point is to catch what
         * survived the filtering, so checking the source proves nothing.
         *
         * IT HAS TWO HALVES AND THEY CHECK EACH OTHER. Either alone is trivially
         * satisfiable in the wrong direction: ship nothing and the repo is
         * perfectly anonymous and useless; ship everything and it reproduces
         * perfectly and exposes contributors. The gate is the CONJUNCTION, and
         * that is what makes it hard to game.
         *
         *   A. NOTHING IDENTIFYING SURVIVES
         *      - no `ride` names, no `date` values, no `file` paths anywhere
         *      - surrogate IDs present, assigned in chronological order
         *      - no coordinate columns — tested BY VALUE, not only by name: any
         *        float column whose range sits inside [-90, 90] paired with one
         *        inside [-180, 180] is flagged for a human, because the next
         *        leak will not be called `lat`
         *      - no *.fit, *.gpx, nothing under any activities path
         *      - at most ONE centroid per corpus; zero per ride
         *
         *   B. EVERYTHING PUBLISHED STILL REPRODUCES
         *      - the repo, run end to end from its own contents, re-derives
         *        every statistic the article prints, to the published precision
         *      - the chronological split-halves come out identical, which is the
         *        sharp test that the date-to-rank substitution was order-
         *        preserving rather than merely date-free
         *
         * The gate is a SCRIPT, not a checklist — same discipline as the rest of
         * the project: it exits non-zero, it is run before every publish, and
         * its output is archived with the release. A checklist here would be the
         * one manual step in a repository whose entire culture is that manual
         * verification is what fails.
         *
         * Note which failure is worse. A reproduction failure is embarrassing
         * and fixable by publishing again. An anonymisation failure cannot be
         * withdrawn — a copied repository is permanent, and the contributor
         * whose home it exposes was not the one who chose to publish. So on any
         * ambiguity half A wins, and the release waits.
         */
        attribute blocking : Boolean default true;
        attribute runsAgainst : String default "the release artefact, never the working repo";
        attribute halfA : String default "nothing identifying survives — names, dates, paths, coordinates by VALUE, tracks, per-ride centroids";
        attribute halfB : String default "everything published still reproduces, split-halves identical";
        attribute form : String default "an executable script that exits non-zero; output archived with the release";
        attribute onAmbiguity : String default "half A wins and the release waits — an anonymisation failure cannot be withdrawn";
    }

    part anonymisationGate : AnonymisationGate;

    part reproductionRepo : ReproductionRepo;
    part anonymisation : AnonymisationDesign;

    // ----------------------------------------------------- supersession of v1.0

    part def MonolithRetirement {
        doc
        /*
         * The monolith holds what is now A1 + A2 + A4 material. Because its DOI
         * is only RESERVED, retiring it is an internal decision with no public
         * cost: no citations break, no record needs a supersession relation, and
         * nothing has to be withdrawn. It is simply never released, and the
         * series ships in its place.
         *
         * The consequence that matters for 05-deliverables: deferring A4 means
         * its material stays UNPUBLISHED, not that it is already out with its
         * caveats attached. An earlier draft of this model claimed the latter,
         * reading a reserved DOI as a public record; that was wrong, and it
         * removed a cost that in fact exists. The time dual, including the
         * honest finding that its descent half does not hold, currently reaches
         * nobody outside this repository.
         *
         * Whether that unpublished negative result should be released on its own
         * — a short note that the dual's ascent half transfers and its descent
         * half does not — is a real question, and a different one from whether
         * A4 ships. Negative results are cheap to publish and rarely are.
         */
        attribute doiIsReservedOnly : Boolean default true;
        attribute publicCostOfRetiring : String default "none — nothing is citing it";
        attribute a4MaterialIsPublic : Boolean default false;
    }

    part monolithRetirement : MonolithRetirement;

    // ---------------------------------------------------------------- roadmap

    part def RoadmapItem {
        attribute article : String;
        attribute stage : String;
        attribute nextGate : String;
        attribute blockedBy : String;
    }

    part rA1 : RoadmapItem {
        attribute redefines article default "A1 — closed form (the project's FIRST public release)";
        attribute redefines stage default "4. Review (second external round returned)";
        attribute redefines nextGate default
            "close the review: the two framing calls (reframe title/abstract "
            + "away from 'validated' toward accounting-consistency; promote the "
            + "out-of-sample 5.6% over the 3.5% calibration figure), elevate "
            + "'accurate by cancellation' to a named limitation, then a FULL "
            + "gate battery run and the propagation checklist";
        attribute redefines blockedBy default "nothing technical — the remaining work is framing and is a maintainer decision";
    }

    part rA2 : RoadmapItem {
        attribute redefines article default "A2 — the law on DEM elevation";
        attribute redefines stage default "3. Draft (letter, ~4 pages; evidence from Entry 41 already gated)";
        attribute redefines nextGate default "complete the draft, then review";
        attribute redefines blockedBy default
            "A1's RELEASE, not A1's completion — A2 cites A1, and a citation "
            + "needs a resolvable DOI. Drafting proceeds in parallel; releasing "
            + "does not.";
    }

    part rA3 : RoadmapItem {
        attribute redefines article default "A3 — discretisation into an edge cost";
        attribute redefines stage default "3. Draft — scaffold only";
        attribute redefines nextGate default
            "decide whether the discretisation claim needs its own registered "
            + "experiment or rests on the existing edge-cost entries (19-21, 23, "
            + "25, 26); if the former, that registration is the true next step";
        attribute redefines blockedBy default "A2's scale prescription, which A3 cites; and A2's release for the citation";
    }

    // -------------------------------------------------------- the critical path

    part def CriticalPathFinding {
        doc
        /*
         * Release order is FORCED — A1 then A2 then A3 — not by preference but
         * by citation resolvability: each cites its predecessor, and a citation
         * needs a DOI that exists. Drafting can overlap; releasing cannot.
         *
         * Combined with 05-deliverables' finding that A3 is the deliverable
         * reaching the mission's terminal stakeholder, and 03-measures' finding
         * that MOE-5 cannot move before A3 lands, the chain closes:
         *
         *   A1's remaining FRAMING FIXES are on the critical path to the
         *   mission's only uninstrumented measure.
         *
         * That is an uncomfortable but useful result. The bottleneck on the
         * whole mission is not a missing experiment, not a weak number, not an
         * unwritten harness — it is two editorial decisions about how A1's
         * abstract and title are worded, which the last review round called
         * "framing, not science". Everything downstream queues behind them.
         *
         * The corollary is about sequencing risk rather than speed: the longer
         * A1 sits in review, the more the repository's live numbers drift from
         * the draft under review, and the larger the propagation run at release.
         * Reviews are not free to leave open.
         */
        attribute path : String default "A1 framing fixes -> A1 release -> A2 release -> A3 release -> MOE-5 becomes observable";
        attribute bottleneck : String default "two editorial decisions on A1's title and abstract";
    }

    part criticalPath : CriticalPathFinding;

    // ------------------------------------------------- what the life cycle lacks

    part def LifecycleGap {
        doc
        /*
         * Three stages are defined above but have no mechanism behind them.
         *
         * UTILIZATION has no instrument (this is MOE-5, already named).
         *
         * SUPPORT has no drift detector: nothing compares a released article's
         * numbers against the current repository. The cheapest fix is a gate
         * section pinned to the AS-PUBLISHED values of a released paper, which
         * fails when the live numbers leave the published intervals — turning
         * the freeze tension into a test rather than a worry. Note this
         * deliberately inverts the usual gate direction: every other gate
         * asserts the code still matches the paper; this one asserts the paper
         * still matches the code, and its failure is informative rather than an
         * error.
         *
         * RETIREMENT is untested but currently cheap: the monolith can be
         * retired with no public consequence because its DOI is only reserved.
         * The pattern still needs setting, because the first REAL exercise of it
         * — A1 superseded by a later work, after A1 is public and cited — will
         * not be cheap.
         */
        attribute unmechanised : String default "utilization (no instrument), support (no drift detector), retirement (no precedent)";
    }

    part lifecycleGap : LifecycleGap;
}
