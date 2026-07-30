package BicyclingEnergyMission {
    doc
    /*
     * The overarching mission of this repository, in Mission Engineering terms.
     *
     * Mission Engineering asks *why* a capability exists and *what effect* it is
     * meant to have in the world — deliberately upstream of the system that
     * delivers it. That separation is the point of this model: the repository
     * holds a closed-form energy law, six ride corpora and a gate battery, but
     * none of those is the mission. They are means. The mission is the effect
     * the published articles are meant to have on how cities and tours are
     * planned.
     *
     * MISSION STATEMENT
     *   Publish scientific articles on bicycling energy estimation so that they
     *   provide the evidential basis for urban- and tour-planning use cases.
     *
     * ("Subsidise" is read here in the sense of Portuguese *subsidiar* — to
     *  furnish the grounds for a decision — not financial subsidy.)
     *
     * The load-bearing consequence of stating it this way: an article that is
     * correct but unread, or read but unusable by a planner, is a mission
     * FAILURE even though the science succeeded. That is why the measures in
     * 03-measures.sysml separate model performance from mission effect, and why
     * the public at large is a first-class stakeholder rather than an audience.
     */

    import ScalarValues::*;

    // ---------------------------------------------------------------- context

    part def OperationalContext {
        doc
        /*
         * Where the mission has to hold. The corpora are ridden overwhelmingly
         * in the São Paulo metropolitan region — hilly, tropical, unevenly
         * paved — with one external corpus in Western Europe. Terrain is the
         * dimension the model is most exposed on, which is why the external
         * corpus exists at all.
         */
        attribute primaryRegion : String default "São Paulo metropolitan region";
        attribute externalRegion : String default "Western Europe (Catalonia, Burgundy, French Alps)";
        attribute terrainCharacter : String default "hilly, buried hydrography, high relief per km";
    }

    // ------------------------------------------------------------- the mission

    part def Mission {
        doc /* The mission as a first-class element, so objectives can subject it. */
        attribute statement : String default
            "Publish scientific articles on bicycling energy estimation so that they "
            + "provide the evidential basis for urban- and tour-planning use cases.";
        part context : OperationalContext;
    }

    part theMission : Mission;

    // ---------------------------------------------------- the intended effects
    // An effect chain, stated so that each link can fail independently. Most
    // research-to-practice models assume the chain; naming the links is what
    // makes the weak one visible.

    part def Effect {
        attribute name : String;
        attribute rationale : String;
    }

    part effectChain : Effect[4] {
        doc
        /*
         * E1 -> E2 -> E3 -> E4. The historically weak link is E2->E3: an
         * estimate that needs a rider's fitted parameters cannot be used by a
         * planner meeting an unknown rider, which is exactly why the published
         * law is restricted to universal constants.
         */
    }

    part e1 : Effect {
        attribute redefines name default "Estimable energy";
        attribute redefines rationale default
            "A route's mechanical energy cost becomes computable from geometry and "
            + "a handful of universal constants, with a stated and tested error.";
    }

    part e2 : Effect {
        attribute redefines name default "Public, auditable evidence";
        attribute redefines rationale default
            "The estimate, its error bars, its scope conditions and the code that "
            + "produced them are published openly, so a third party can check "
            + "rather than trust.";
    }

    part e3 : Effect {
        attribute redefines name default "Usable by a planner";
        attribute redefines rationale default
            "The method runs on data a planner actually has — a route and a "
            + "terrain model — WITHOUT requiring parameters fitted to the "
            + "individual rider. This is the link most likely to break.";
    }

    part e4 : Effect {
        attribute redefines name default "Better-grounded decisions";
        attribute redefines rationale default
            "Route, network and tour decisions are argued from a defensible "
            + "energy figure instead of from distance, gradient intuition, or "
            + "nothing at all.";
    }

    // ------------------------------------------------------ mission objectives

    requirement def MissionObjective {
        doc /* Objectives are stated so that failure is recognisable, not so that success is assured. */
        subject mission : Mission;
    }

    requirement <'MO-1'> publishOpenly : MissionObjective {
        doc
        /*
         * Publish where the audience is, not where the credential is. The
         * project deliberately targets an openly readable HTML article plus a
         * Zenodo DOI rather than a paywalled journal: reach and permanence beat
         * academic standing for THIS mission, because stakeholders C and D
         * cannot get past a paywall and would not read a PDF if they could.
         */
        attribute venue : String default "self-hosted HTML + Zenodo DOI (10.5281/zenodo.21282165)";
        attribute paywalled : Boolean default false;
    }

    requirement <'MO-2'> estimateWithStatedError : MissionObjective {
        doc
        /*
         * Every published figure carries an error AND a signed bias with
         * confidence intervals. Accuracy alone hides bias cancellation — the
         * project has caught exactly that failure in its own numbers.
         */
    }

    requirement <'MO-3'> transferToUnseenRiders : MissionObjective {
        doc
        /*
         * The law must hold on riders, countries, terrain and devices that
         * played no part in its calibration. Without this the work is a
         * description of one cyclist, not a planning instrument.
         */
    }

    requirement <'MO-4'> beReproducible : MissionObjective {
        doc
        /*
         * Every published number regenerates from primary data by one
         * documented command, and is re-derived by a public gate battery that
         * fails loudly. Private ride data is never published; derived
         * aggregates and all code are.
         */
    }

    requirement <'MO-6'> shiftThePlanningCurrency : MissionObjective {
        doc
        /*
         * A normative objective, declared rather than implied: move the
         * planning discourse from TIME to ENERGY as the currency in which
         * cycling routes are argued, because an energy ranking generalises
         * across rider power profiles in a way a time ranking does not
         * (MissionStakeholders::AccessibilityArgument).
         *
         * Consequence the model must own: the mission is NOT indifferent about
         * which of its own results are amplified. That is a legitimate position
         * and a declared one — but it is also a bias with a specific failure
         * mode, namely suppressing a sound result because it is inconvenient to
         * the position. The safeguard is that suppression decisions are
         * recorded with their reasons and remain reversible (see A4's
         * assessment, which is a deferral with a stated promotion condition,
         * not a burial).
         */
        attribute currency : String default "energy, not time";
    }

    requirement <'MO-5'> reachPractice : MissionObjective {
        doc
        /*
         * The mission's terminal objective, and the only one the repository
         * cannot satisfy alone: the estimates are actually consumed by planning
         * or advocacy work. Deployed tools are the bridge; adoption is the
         * evidence.
         */
    }
}
