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
