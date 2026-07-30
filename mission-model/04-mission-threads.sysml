package MissionThreads {
    doc
    /*
     * Mission threads: end-to-end paths from a stakeholder's question to an
     * outcome, each one crossing the artefact ladder. A thread is worth writing
     * only if it can fail; each below names where it breaks.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionStakeholders::*;
    import MissionCapabilities::*;

    // ------------------------------------------------------------- (B) planner

    use case def AssessRouteFeasibility {
        subject planner : Technician;
        doc
        /*
         * "Is this proposed cycle route rideable by an ordinary commuter, or
         * does the hill at the middle of it make it a route only for the fit?"
         *
         * Path: route geometry -> terrain model -> energy law with universal
         * constants -> kJ with an error bar -> compare against a plausible
         * commuter's sustainable output.
         *
         * BREAKS IF: the method needs the commuter's mass, CdA or fitness. It
         * does not, by design — which is why rider-parameter deficit forms keep
         * being rejected even when they fit better.
         *
         * ALSO BREAKS IF: the terrain model is coarser than the law assumes.
         * The elevation source is a first-class part of the answer, not a
         * detail; paper 2 exists because of this.
         */
        objective {
            doc /* A defensible kJ figure with a stated error, from data the planner already holds. */
        }
    }

    use case def CompareNetworkAlternatives {
        subject planner : Technician;
        doc
        /*
         * "Of two corridors, which costs riders less energy across the
         * population that would use it?"
         *
         * This is where an energy FIELD beats a per-route number, and where a
         * systematic bias matters far more than a random error: a one-sided
         * error compounds across every pair in the network, while a symmetric
         * one largely cancels. This thread is the reason bias is reported
         * beside accuracy everywhere.
         *
         * BREAKS IF: only median error is quoted and the bias is left unstated.
         */
        objective {
            doc /* A ranking between alternatives that survives the estimate's error. */
        }
    }

    // ------------------------------------------------------------ (C) activist

    use case def ArgueForInfrastructure {
        subject advocate : Activist;
        doc
        /*
         * "This corridor is being dismissed as unrideable. Show, citably, that
         * it is not."
         *
         * Path: DOI-citable article -> a figure for the specific corridor ->
         * the scope conditions under which that figure holds.
         *
         * BREAKS IF: the claim cannot survive an authority's technical
         * consultant reading it adversarially. The defence is not confidence;
         * it is that the pre-registrations, the failed predictions and the
         * withdrawn readings are all public, so a hostile reader finds the
         * limitations already stated rather than concealed. A study that hid
         * its failures would be more persuasive right up until someone checked.
         */
        objective {
            doc /* A quantified, independently checkable claim usable in a public forum. */
        }
    }

    // ------------------------------------------------------------ (A) academic

    use case def ReuseOrRefuteTheLaw {
        subject scholar : Academic;
        doc
        /*
         * "Does this hold for my city, my riders, my terrain — and if not,
         * where exactly does it break?"
         *
         * Path: derivation -> stated scope conditions -> the harnesses ->
         * their own corpus.
         *
         * BREAKS IF: the scope conditions are implicit. The project's habit of
         * writing them as hard boundaries — this deficit form is defined only
         * above a 3% mean descent grade; this constant was selected in-sample
         * on that corpus; this pool deliberately excludes that corpus — is what
         * makes refutation possible, and refutation is the service this
         * stakeholder provides.
         */
        objective {
            doc /* Enough detail to reproduce, extend, or falsify the result. */
        }
    }

    // -------------------------------------------------------------- (D) public

    use case def UnderstandRideDifficulty {
        subject rider : GeneralPublic;
        doc
        /*
         * "How hard is this ride, and why is that hill worse than the distance
         * suggests?"
         *
         * Path: plain-language piece or interactive applet -> an intuition that
         * climbing dominates, that descents refund only part of it, and that
         * the refunded part depends on whether you pedal downhill.
         *
         * BREAKS IF: the only artefacts are the paper and the code. Currently
         * PARTIALLY BROKEN — piece 1 exists in both languages, pieces 2 and 3
         * are pending, so this thread is thinner than the other three.
         */
        objective {
            doc /* An honest, non-technical answer, in Portuguese as well as English. */
        }
    }

    // ------------------------------------------------- the thread that is missing

    use case def CloseTheLoop {
        subject planner : Technician;
        doc
        /*
         * The thread the mission needs and the repository does not have: a
         * documented instance of a planning or advocacy body grounding a real
         * decision in these estimates, written up with what they asked, what
         * they got, and whether it held.
         *
         * Until one exists, MOE-5 is unmeasured and the mission's second clause
         * — "so that it provides the evidential basis for urban and tour
         * planning" — is an intent supported by capability rather than by
         * evidence. Every other thread here is demonstrable today; this one is
         * the mission's open edge.
         */
        objective {
            doc /* One documented use in practice, with its outcome recorded — including if it failed. */
        }
    }
}
