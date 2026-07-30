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

    // ---------------------------------------------------- dependency structure

    part def Enablement {
        attribute from : String;
        attribute to : String;
        attribute nature : String;
    }

    part d1to2 : Enablement {
        attribute redefines from default "A1";
        attribute redefines to default "A2";
        attribute redefines nature default "hard — A2 evaluates A1's law; without it there is nothing to substitute into";
    }
    part d2to3 : Enablement {
        attribute redefines from default "A2";
        attribute redefines to default "A3";
        attribute redefines nature default "hard — A3 cites A2's scale prescription; the discretisation question is raised BY A2";
    }
    part d1to4 : Enablement {
        attribute redefines from default "A1";
        attribute redefines to default "A4";
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
