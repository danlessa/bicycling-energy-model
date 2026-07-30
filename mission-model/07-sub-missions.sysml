package SubMissions {
    doc
    /*
     * One sub-mission per deliverable on the critical path. Each is a complete
     * mission in its own right — it has its own effect, its own primary
     * stakeholder, its own measures and its own way of failing — and the general
     * mission succeeds only if all three do, plus adoption.
     *
     * The discipline that makes the decomposition worth anything is the
     * `mustNotClaim` attribute on each. A1's credibility depends on it NOT
     * claiming planner-usability; A2's depends on it NOT claiming routing. The
     * temptation at each stage is to reach for the next stage's conclusion,
     * because that is where the interest is — and reaching is exactly what a
     * reviewer catches. Scope discipline is not modesty here; it is the
     * mechanism by which each article survives being read adversarially.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionStakeholders::*;
    import MissionDeliverables::*;
    import MissionMeasures::*;

    part def SubMission {
        attribute id : String;
        attribute statement : String;
        attribute primaryStakeholder : String;
        attribute deliversEffect : String;
        attribute mustNotClaim : String;
        attribute succeedsIf : String;
        attribute failsIf : String;
    }

    // ===================================================== SM-1 (A1)

    part sm1 : SubMission {
        attribute redefines id default "SM-1 — establish that the estimate is CREDIBLE";
        attribute redefines statement default
            "Establish that a route's mechanical energy is computable in closed "
            + "form from geometry and universal constants, with an error, a bias "
            + "and scope conditions that a hostile reader can check and, if "
            + "wrong, refute.";
        attribute redefines primaryStakeholder default
            "(A) academics — they check the derivation; (C) activists — they need "
            + "something citable that survives an authority's consultant reading it";
        attribute redefines deliversEffect default "E1 estimable energy + E2 public auditable evidence";
        attribute redefines mustNotClaim default
            "That a planner can USE it. A1 is evaluated on rides that were "
            + "actually ridden with a power meter; nothing in it establishes "
            + "behaviour on a planner's terrain model. That is SM-2's ground and "
            + "borrowing it is the single most likely way A1 fails review.";
        attribute redefines succeedsIf default
            "an adversarial reader finds the limitations already stated rather "
            + "than concealed — the failed predictions, the withdrawn readings, "
            + "the in-sample labels and the scope boundaries are all in the text";
        attribute redefines failsIf default
            "the framing invites 'validated against 2,025 rides' when the "
            + "protocol is a shared-input consistency check — precisely what the "
            + "last review flagged as its major concern";
    }

    part def SM1Measures {
        doc
        /*
         * SM-1's measures are about SCRUTINY, not accuracy — accuracy is a
         * property the model already has and reports. What SM-1 must earn is
         * that the accuracy claim is believable, which is a different thing and
         * fails differently.
         *
         * Note the asymmetry with the general mission: SM-1 can succeed
         * completely while MOE-5 stays at zero. That is not a defect. A1's job
         * is to be right and checkable; being used is two articles away.
         */
        attribute m1 : String default "every published median AND interval re-derived by a public gate battery";
        attribute m2 : String default "review findings fixed or answered in writing — currently one round open";
        attribute m3 : String default "no claim of predictive validation where the protocol is consistency";
        attribute m4 : String default "the honest headline is the out-of-sample figure, not the calibration one";
    }
    part sm1Measures : SM1Measures;

    // ===================================================== SM-2 (A2)

    part sm2 : SubMission {
        attribute redefines id default "SM-2 — make the estimate OPERABLE FROM A MAP";
        attribute redefines statement default
            "Establish what happens when the ridden elevation stream is replaced "
            + "by a planner's terrain model — how much of the error is the model "
            + "and how much the source — and state the smoothing prescription "
            + "that makes a DEM profile behave like a barometric one.";
        attribute redefines primaryStakeholder default
            "(B) technicians — this is the article that removes the requirement "
            + "to have ridden the route first";
        attribute redefines deliversEffect default
            "E3 usable by a planner. SM-2 IS the E2->E3 bridge; without it the "
            + "law needs a ridden track and no planning use case can reach it.";
        attribute redefines mustNotClaim default
            "That routing works. Knowing a route's energy from a map is not the "
            + "same as being able to SEARCH for the cheapest route, which needs "
            + "a per-edge cost and is SM-3's ground.";
        attribute redefines succeedsIf default
            "the DEM-substituted error stays within a stated bound of the "
            + "barometric baseline, and the smoothing prescription is stated "
            + "a priori and transfers across elevation sources";
        attribute redefines failsIf default
            "the smoothing is tuned per DEM. Then the elevation source is a "
            + "hidden free parameter and the method silently requires a "
            + "calibration the planner cannot perform — the same disease as a "
            + "per-rider constant, one level up.";
    }

    part def SM2Measures {
        doc
        /*
         * The measure that matters is TRANSFERABILITY OF THE PRESCRIPTION, not
         * the error under any one DEM. An error figure for one raster is a
         * property of that raster; a prescription that holds across rasters is
         * a property of the method, and only the second is publishable as
         * guidance.
         */
        attribute m1 : String default "error under DEM substitution, against the ride's own elevation stream, per source";
        attribute m2 : String default "the smoothing prescription stated once and applied unchanged to every source";
        attribute m3 : String default "the residual attributed between MODEL and SOURCE rather than lumped";
    }
    part sm2Measures : SM2Measures;

    // ===================================================== SM-3 (A3)

    part sm3 : SubMission {
        attribute redefines id default "SM-3 — make the estimate SEARCHABLE, and the currency argument operational";
        attribute redefines statement default
            "Establish that the route-level law discretises into a per-edge cost "
            + "a shortest-path search can consume without the discretisation "
            + "changing the answer — and thereby make energy-optimal routing, "
            + "corridor comparison and network diagnostics possible.";
        attribute redefines primaryStakeholder default
            "(B) technicians and (C) activists — routing and corridor comparison "
            + "are what a planning body and an advocacy group argue over; and "
            + "(E) the author, because this is where MO-6 becomes actionable";
        attribute redefines deliversEffect default "E4 better-grounded decisions";
        attribute redefines mustNotClaim default
            "That the routes it finds are the routes people should ride. A "
            + "minimum-energy path is one objective among several — safety, "
            + "traffic, surface, shade — and presenting it as THE answer would "
            + "hand critics an easy and fair objection.";
        attribute redefines succeedsIf default
            "the discretised cost agrees with the route-level integral within a "
            + "stated bound, the discretisation artefacts are characterised "
            + "rather than merely avoided, and the search is cheap enough to run "
            + "in a browser on a self-hosted box";
        attribute redefines failsIf default
            "the grid's own geometry decides the answer — connectivity bias, "
            + "direction quantisation, or a clamp that turns out to be dead code "
            + "(all three have already been caught in the deployed engine)";
    }

    part def SM3Measures {
        doc
        /*
         * SM-3 carries a measure the other two do not, and it is the one that
         * puts the mission's normative objective at risk:
         *
         *   DOES ENERGY-OPTIMAL ROUTING ACTUALLY DIFFER FROM DISTANCE- OR
         *   TIME-OPTIMAL ROUTING, MATERIALLY AND OFTEN?
         *
         * If the cheapest-energy route is usually the same road the shortest
         * path already picked, then MO-6 is philosophically sound and
         * operationally empty: the currency shift would change how a decision is
         * JUSTIFIED without changing the decision. The accessibility argument
         * would survive as an argument and lose its practical bite.
         *
         * This is falsifiable, it is A3's to answer, and nobody has answered it.
         * Entry 26's direction ladder and detour measurements on real ride
         * endpoints are the seed evidence — they already quantify how far an
         * energy-aware path departs from the direct one — but they were run to
         * validate the search, not to test the currency claim, so the question
         * has never been asked in that form.
         *
         * Stated as a risk rather than a prediction: the answer could go either
         * way, and the honest position is that the mission's normative objective
         * currently rests on an untested operational premise. On São Paulo's
         * relief the premise is plausible — gravity dominates, so detours around
         * hills should be real — but plausible is not measured, and the terrain
         * where it is most plausible is also the terrain the corpora are most
         * concentrated in.
         */
        attribute m1 : String default "agreement between the per-edge cost and the route-level integral";
        attribute m2 : String default "discretisation artefacts characterised: connectivity, direction quantisation, clamping";
        attribute m3 : String default
            "MATERIAL DIVERGENCE of energy-optimal from distance-optimal routes — "
            + "the untested premise MO-6 rests on";
        attribute m4 : String default "search cost compatible with a browser / self-hosted deployment";
    }
    part sm3Measures : SM3Measures;

    // ===================================================== the composition

    part def Composition {
        doc
        /*
         * How the three compose, and what the decomposition does NOT buy.
         *
         * Sequential in RELEASE (citation resolvability) but not in value: SM-1
         * delivers a checkable result whether or not SM-2 ever lands, and that
         * result already serves stakeholders (A) and (C). So the series is not
         * an all-or-nothing bet — each rung is worth something standing alone,
         * which is the main practical argument for the decomposition over the
         * monolith it replaces.
         *
         * What it does not buy: the general mission still needs all three PLUS
         * adoption. Three successful sub-missions with MOE-5 at zero is a
         * complete, well-evidenced, unused body of work — the exact outcome the
         * effect chain in 00-mission was written to make visible rather than
         * comfortable.
         *
         * And one asymmetry worth stating: the sub-missions get harder to
         * evaluate as they go. SM-1's success is judged by readers who can check
         * a derivation. SM-2's needs a planner to try it on their own raster.
         * SM-3's needs someone to route with it and compare. The evidence
         * available inside this repository thins out along exactly the axis the
         * mission travels.
         */
        attribute releaseOrder : String default "SM-1 -> SM-2 -> SM-3, forced by citation resolvability";
        attribute standaloneValue : String default "each rung is worth something alone; the series is not all-or-nothing";
        attribute residualRisk : String default "all three can succeed with MOE-5 still zero";
    }

    part composition : Composition;
}
