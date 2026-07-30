package MissionStakeholders {
    doc
    /*
     * The four stakeholder classes and — more usefully — what each of them can
     * actually do with the work, what they need before they can do it, and how
     * each can be failed.
     *
     * Stating the failure mode per stakeholder is the part that earns its keep.
     * A single artefact cannot serve all four: the error bars that satisfy (A)
     * are noise to (D), and the plain-language summary that reaches (D) would
     * be dismissed by (A). The model therefore records a genuine tension rather
     * than a list of beneficiaries.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;

    part def Stakeholder {
        attribute name : String;
        attribute interest : String;
        doc /* What this group brings to, and takes from, the mission. */
    }

    // ------------------------------------------------------------ (A) academics

    part def Academic :> Stakeholder {
        doc
        /*
         * Engineering students and teachers. They consume the DERIVATION and
         * the protocol, not just the number: the appendix, the pre-registered
         * entries, the scope conditions. They are also the group most able to
         * find the study wrong, which is a service, not a risk.
         */
        attribute redefines name default "Academics — engineering students and teachers";
        attribute redefines interest default
            "A derivation that can be checked line by line, and evidence that "
            + "distinguishes what was calibrated from what was tested.";
        attribute needsDerivation : Boolean default true;
        attribute needsRawData : Boolean default true;
    }

    // ---------------------------------------------------------- (B) technicians

    part def Technician :> Stakeholder {
        doc
        /*
         * Urban-planning and tourism practitioners. The mission's terminal
         * users: they hold the decisions the work is meant to inform. They need
         * a method that runs on a route and a terrain model, with an honest
         * error, and will correctly refuse anything requiring per-rider
         * calibration.
         */
        attribute redefines name default "Technicians — urban planning and tourism sectors";
        attribute redefines interest default
            "A defensible energy figure for a route or a network, obtainable "
            + "from data they already hold, with an error they can quote.";
        attribute needsNoRiderParameters : Boolean default true;
        attribute needsToolNotPaper : Boolean default true;
    }

    // ------------------------------------------------------------ (C) activists

    part def Activist :> Stakeholder {
        doc
        /*
         * Cycling advocacy groups. They need the work as ARGUMENT — a citable,
         * quantified claim that a route is or is not rideable by an ordinary
         * person, usable in a public hearing against an authority that has its
         * own numbers. Their requirement is credibility under adversarial
         * reading, which is a stronger constraint than accuracy.
         */
        attribute redefines name default "Activists — bicycling advocacy groups";
        attribute redefines interest default
            "A citable, quantified, independently checkable claim that survives "
            + "hostile scrutiny in a public forum.";
        attribute needsCitableSource : Boolean default true;
        attribute needsAdversarialRobustness : Boolean default true;
    }

    // --------------------------------------------------------- (D) public

    part def GeneralPublic :> Stakeholder {
        doc
        /*
         * The public at large — including the riders whose rides constitute the
         * corpora. Two distinct claims on the mission. First, comprehension:
         * "how hard is this ride, really?" answered without a physics degree.
         * Second, and more binding, RECIPROCITY: three private riders donated
         * their complete histories, so the work owes the public an accessible
         * result and owes those riders that their data is never published.
         */
        attribute redefines name default "Public at large";
        attribute redefines interest default
            "An understandable answer to 'how hard is this ride', and the "
            + "assurance that donated ride data stays private.";
        attribute needsPlainLanguage : Boolean default true;
        attribute needsPrivacy : Boolean default true;
    }

    // ------------------------------------------- (E) the author and collective

    part def AuthorCollective :> Stakeholder {
        doc
        /*
         * The author and the Pedal Hidrográfico collective. Not a beneficiary —
         * a stakeholder with a NORMATIVE objective, and omitting it made the
         * mission look purely epistemic when it is not.
         *
         * The objective: shift the mainstream planning discourse away from TIME
         * and toward ENERGY as the currency in which cycling routes are argued.
         * The reason is equity, and it is a technical argument, not a slogan —
         * see AccessibilityArgument below.
         *
         * This stakeholder is why the mission is not neutral about which of its
         * own results get amplified, and it is a legitimate interest to declare
         * rather than to hide: a reader is entitled to know that the choice of
         * currency is itself a position the work advances.
         */
        attribute redefines name default "Author and collective — Pedal Hidrográfico";
        attribute redefines interest default
            "Establish energy as the currency in which cycling routes are "
            + "planned and argued, because an energy-optimal route is an "
            + "accessible route.";
        attribute holdsNormativePosition : Boolean default true;
    }

    part authorCollective : AuthorCollective;

    part def AccessibilityArgument {
        doc
        /*
         * Why energy rather than time, stated so it can be disagreed with.
         *
         * A TIME-optimal route is optimal for the rider who can ride it fast.
         * Ranking routes by travel time embeds the fit rider's advantage into
         * the recommendation: change the rider's power and the ranking changes,
         * so the infrastructure conclusion inherits whoever was assumed.
         *
         * An ENERGY-optimal route is far closer to rider-invariant. The
         * dominant term on real terrain is gravitational — beta*(h+ - eps*h-),
         * which scales with mass and is otherwise independent of how strong the
         * rider is. Two riders of very different fitness AGREE on which of two
         * hilly routes costs less energy; they disagree about which is faster.
         * So an energy ranking generalises across power profiles in a way a
         * time ranking does not.
         *
         * The honest qualification: invariance is approximate, not exact. The
         * rolling-and-aero term alpha carries the reference speed, so energy
         * rankings do drift with assumed pace — but the aero share is small at
         * the low reference output the collective plans around (~50 W), and
         * shrinks further as terrain steepens. The argument is therefore
         * STRONGEST exactly where this collective rides: São Paulo's relief is
         * where gravity dominates and the ranking is most nearly everyone's.
         *
         * TWO SEPARATE COMPARISONS, and they resolve differently.
         *
         * Against DISTANCE the question is not empirical at all — it is an
         * exchange rate readable straight off the law. With beta = mg/k_eff and
         * alpha the rolling-plus-aero term, beta/alpha is about 69 at the ~50 W
         * reference the collective plans around, rising past 120 as speed falls
         * and aero vanishes. One metre of ascent costs what 70 to 125 metres of
         * flat riding costs. A distance objective weights that metre the same as
         * any other. So the two objectives cannot coincide except by accident,
         * and they will select different paths wherever the network offers an
         * alternative at all — which on São Paulo's relief is routine. (Where
         * the network offers no alternative — one road up one valley — every
         * objective agrees, and the currency question is moot rather than
         * answered.)
         *
         * Against TIME the answer is the substantive one: time is
         * behaviour-driven and energy is much less so. This is not an assertion;
         * it is what Entry 13 found while testing the time dual. The dual's
         * ascent half transfers to an unseen rider, and its DESCENT half does
         * not predict measured descent speed at all — because how fast someone
         * descends is a choice about risk and comfort, not a fact about the
         * hill. A time-optimal route therefore inherits whichever descending
         * temperament was assumed.
         *
         * Energy is not behaviour-free either, and the model should not pretend
         * otherwise: the coasting deficit is descent-pedalling behaviour, and it
         * spans 0.08 to 0.30 across the seven riders measured. But that
         * dependence is CONFINED — it enters through one term, eps*h_minus,
         * and is bounded by that range — while the dominant term beta*h_plus is
         * mass times geometry and nothing else. Time's dependence is neither
         * confined nor bounded.
         *
         * The consequence for the deliverables is uncomfortable and worth
         * stating: the strongest available evidence for this argument sits
         * inside A4, the article deferred for arguing in the wrong currency. Its
         * negative result — that the time dual's descent half fails BECAUSE
         * descents are behaviour-limited — is precisely the demonstration that
         * time is the weaker planning currency.
         *
         * Which turns the mission's insistence on universal constants from a
         * deployability convenience into an equity requirement. A model needing
         * per-rider parameters could not make this argument at all: it would
         * rank routes for the rider it was fitted to.
         */
        stakeholder e : AuthorCollective;
        stakeholder c : Activist;
        stakeholder d : GeneralPublic;
    }

    part academics : Academic;
    part technicians : Technician;
    part activists : Activist;
    part publicAtLarge : GeneralPublic;

    // ----------------------------------------------------------------- concerns

    concern def Trustworthiness {
        doc /* Can a reader establish that the numbers are what they claim to be? */
        stakeholder a : Academic;
        stakeholder c : Activist;
    }

    concern def Applicability {
        doc /* Does the method run on the data the user actually holds? */
        stakeholder b : Technician;
    }

    concern def Comprehensibility {
        doc /* Can a non-specialist follow the claim and its limits? */
        stakeholder d : GeneralPublic;
        stakeholder c2 : Activist;
    }

    concern def Privacy {
        doc
        /*
         * Ride tracks are location histories that begin at people's homes. This
         * concern OVERRIDES the others where they conflict — no figure, map or
         * corpus is published if it would expose a contributor, which is why
         * the external corpus is cited by DOI and its geometry never drawn.
         */
        stakeholder d : GeneralPublic;
    }

    // --------------------------------------------- the tension, stated outright

    concern def AudienceTension {
        doc
        /*
         * The four groups cannot be served by one artefact, and pretending
         * otherwise produces a document that serves none of them. Academics
         * want the scope conditions and the failed hypotheses; the public wants
         * one number and a sentence. The project's answer is a LADDER of
         * artefacts — paper, piece, applet, deployed map — sharing one evidence
         * base, rather than one document trying to be four.
         *
         * Consequence to watch: every rung added multiplies the surfaces on
         * which a re-baselined number must be updated in lockstep.
         */
        stakeholder a : Academic;
        stakeholder b : Technician;
        stakeholder c : Activist;
        stakeholder d : GeneralPublic;
    }
}
