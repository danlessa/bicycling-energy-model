package MissionMeasures {
    doc
    /*
     * Measures, split the way Mission Engineering splits them:
     *
     *   MOP — Measure of Performance: how well the SYSTEM does its job.
     *         Property of the model. Fully under this repository's control.
     *   MOE — Measure of Effectiveness: how well the MISSION succeeds.
     *         Property of the world. Mostly NOT under this repository's control.
     *
     * The distinction is the most useful thing in this whole model. Every
     * measure the project currently tracks is an MOP. The mission is stated in
     * terms of effect on planning practice, and effect on practice is measured
     * by none of them. That is not a gap in the science; it is a gap between
     * what is measured and what is claimed, and naming it is the point.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionCapabilities::*;

    // ------------------------------------------------------------------- MOPs

    attribute def Measure {
        attribute name : String;
        attribute current : String;
        attribute threshold : String;
        attribute tracked : Boolean;
    }

    attribute <'MOP-1'> accuracyOnTransfer : Measure {
        attribute redefines name default "Median |Δ%| against measured leg energy, out-of-sample riders";
        attribute redefines current default "5.6% [5.2, 6.2] on the D3+D4 transfer pool (n = 660)";
        attribute redefines threshold default "<= 10% — beyond that a planner's decision would flip on the error";
        attribute redefines tracked default true;
    }

    attribute <'MOP-2'> biasOnTransfer : Measure {
        attribute redefines name default "Median signed Δ%, with interval";
        attribute redefines current default "+1.1 [+0.4, +1.7] on the same pool";
        attribute redefines threshold default "interval to contain or nearly contain zero; a one-sided error compounds over a network";
        attribute redefines tracked default true;
    }

    attribute <'MOP-3'> parityWithSimulation : Measure {
        attribute redefines name default "Formal equivalence to the forward simulation (TOST, ±1.0 pp margin)";
        attribute redefines current default "Equivalent on both transfer pools; inconclusive at n = 44";
        attribute redefines threshold default "90% CI of the median difference inside ±1.0 pp";
        attribute redefines tracked default true;
    }

    attribute <'MOP-4'> reproducibility : Measure {
        attribute redefines name default "Published figures re-derived by the public gate battery";
        attribute redefines current default "282 gates green under the fast path; the interval gates need a full run";
        attribute redefines threshold default "every published median AND its interval gated; exit non-zero on failure";
        attribute redefines tracked default true;
    }

    attribute <'MOP-5'> riderBreadth : Measure {
        attribute redefines name default "Independent riders the law has been tested on";
        attribute redefines current default "7 riders across 6 corpora, 1 corpus outside Brazil";
        attribute redefines threshold default "enough to bound a BEHAVIOURAL constant — 7 is thin, and the paper says so";
        attribute redefines tracked default true;
    }

    // ------------------------------------------------------------------- MOEs

    attribute <'MOE-1'> reachability : Measure {
        attribute redefines name default "Can each stakeholder class obtain and read the result?";
        attribute redefines current default
            "(A) yes — full paper, journal, code. (B) yes — deployed tools. "
            + "(C) yes — citable DOI. (D) PARTIAL — piece 1 is bilingual, pieces 2-3 pending.";
        attribute redefines threshold default "all four classes served by at least one artefact at their register";
        attribute redefines tracked default false;
    }

    attribute <'MOE-2'> usabilityWithoutRiderData : Measure {
        attribute redefines name default "Does the recommended method run without per-rider calibration?";
        attribute redefines current default
            "Yes, and it is enforced: rider-parameter forms are repeatedly "
            + "rejected in the journal precisely because a planner meeting an "
            + "unknown rider cannot supply them.";
        attribute redefines threshold default "universal constants only";
        attribute redefines tracked default true;
    }

    attribute <'MOE-3'> survivesAdversarialReading : Measure {
        attribute redefines name default "Does the claim hold up when someone tries to break it?";
        attribute redefines current default
            "Repeatedly tested from inside — pre-registered predictions have "
            + "failed and been recorded as failed; several published readings "
            + "have been withdrawn. External review rounds have found real errors.";
        attribute redefines threshold default "no published claim rests on an un-gated number";
        attribute redefines tracked default true;
    }

    attribute <'MOE-4'> contributorHarm : Measure {
        attribute redefines name default "Privacy incidents affecting a data contributor";
        attribute redefines current default
            "Zero published. One violation was caught in-flight during an "
            + "experiment and the affected work discarded — the control worked, "
            + "which is the only evidence that matters here.";
        attribute redefines threshold default "zero, non-negotiable; this measure dominates the others on conflict";
        attribute redefines tracked default true;
    }

    attribute <'MOE-5'> adoptionInPractice : Measure {
        attribute redefines name default "Planning or advocacy work that actually used these estimates";
        attribute redefines current default
            "UNMEASURED. No instance is evidenced in this repository, and no "
            + "mechanism exists to detect one.";
        attribute redefines threshold default "at least one documented planning or advocacy use";
        attribute redefines tracked default false;
    }

    // ------------------------------------------------------------- the finding

    part def MeasurementGap {
        doc
        /*
         * MOE-5 is the mission's terminal measure and it is the one nobody is
         * watching. Everything the project instruments — accuracy, bias,
         * equivalence, reproducibility — is an MOP: a property of the model,
         * measurable from inside the repository, and already excellent. The
         * mission as stated succeeds or fails on whether an urban planner or a
         * tourism office ever grounds a decision in the result, and no artefact
         * here would notice either way.
         *
         * This is a normal and honest position for a research repository. But
         * it means "so that it provides the evidential basis for urban and tour
         * planning" is currently an INTENT rather than a demonstrated effect,
         * and the model should say so rather than let the mission statement
         * imply otherwise.
         *
         * Cheapest credible instruments, in increasing cost:
         *   - record citations and inbound links to the DOI and the /modelo/ pages;
         *   - record any request for the coordinate-stripped aggregates;
         *   - one documented walkthrough with a planning or advocacy body,
         *     written up as a mission thread with its outcome.
         */
        attribute severity : String default "the terminal measure of the stated mission is uninstrumented";
    }

    part theGap : MeasurementGap;
}
