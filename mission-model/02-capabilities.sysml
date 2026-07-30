package MissionCapabilities {
    doc
    /*
     * Capabilities the mission requires, and the systems in this ecosystem that
     * deliver them. Mission Engineering keeps these separate on purpose: a
     * capability is what must be possible, a system is one way of achieving it,
     * and confusing the two is how a project ends up defending an
     * implementation instead of an outcome.
     *
     * Each capability below names the gap it closes and what its absence would
     * cost the mission.
     */

    import ScalarValues::*;
    import BicyclingEnergyMission::*;
    import MissionStakeholders::*;

    part def Capability {
        attribute name : String;
        attribute absenceCost : String;
        doc /* absenceCost: what the mission loses if this capability is missing. */
    }

    // ------------------------------------------------------------- capabilities

    part cEstimate : Capability {
        attribute redefines name default "Estimate route energy from geometry alone";
        attribute redefines absenceCost default
            "Without it there is nothing to publish: planning questions are "
            + "asked about routes that nobody has ridden with a power meter.";
    }

    part cQuantifyError : Capability {
        attribute redefines name default "State the error AND the signed bias, with intervals";
        attribute redefines absenceCost default
            "An unqualified number is unusable in a hearing and indefensible "
            + "under review; accuracy alone can hide two errors cancelling.";
    }

    part cTransfer : Capability {
        attribute redefines name default "Hold on riders and terrain outside the calibration set";
        attribute redefines absenceCost default
            "Without it the result describes its author, and every planning "
            + "application is unsupported extrapolation.";
    }

    part cReproduce : Capability {
        attribute redefines name default "Regenerate every published number from primary data";
        attribute redefines absenceCost default
            "Claims become assertions; an error found later cannot be traced to "
            + "the figures it contaminated.";
    }

    part cDeploy : Capability {
        attribute redefines name default "Put the estimate in a planner's hands as a tool";
        attribute redefines absenceCost default
            "The E2->E3 link breaks: correct, public, unused. This is the "
            + "capability whose absence is least visible from inside the repo.";
    }

    part cExplain : Capability {
        attribute redefines name default "Explain the result without physics training";
        attribute redefines absenceCost default
            "Stakeholders C and D are excluded, and the open-access choice that "
            + "the mission is built around buys nothing.";
    }

    part cProtectContributors : Capability {
        attribute redefines name default "Publish findings without exposing contributors";
        attribute redefines absenceCost default
            "A privacy failure ends the data supply permanently and is not "
            + "recoverable by any later correction.";
    }

    // ---------------------------------------------------------------- systems

    part def DeliverySystem {
        attribute name : String;
        attribute role : String;
    }

    part papers : DeliverySystem {
        attribute redefines name default "The paper series (paper 1 closed form; paper 2 DEM deployment; paper 3 edge cost)";
        attribute redefines role default "Carries the derivation, the evidence and the scope conditions. Serves (A) and (C).";
    }

    part labJournal : DeliverySystem {
        attribute redefines name default "The lab journal + claims graph + evaluation-lineage graph";
        attribute redefines role default
            "Pre-registrations, negative results, withdrawn claims and the "
            + "provenance of every published statistic. Serves (A), and is what "
            + "makes (C)'s adversarial robustness checkable rather than asserted.";
    }

    part gateBattery : DeliverySystem {
        attribute redefines name default "The gate battery (bootstrap_ci.py)";
        attribute redefines role default
            "Re-derives every published median and interval from the per-ride "
            + "outputs and fails loudly. The mechanism behind MO-4.";
    }

    part deployedTools : DeliverySystem {
        attribute redefines name default "Deployed tools — Simujaules energy fields, quilojaules per-route kJ, the applet";
        attribute redefines role default
            "The E2->E3 bridge: turns a published law into something a planner "
            + "operates. Serves (B) primarily and (D) incidentally.";
    }

    part pieces : DeliverySystem {
        attribute redefines name default "The piece series, bilingual (EN / pt-BR)";
        attribute redefines role default
            "Plain-language retellings. The only artefact addressed to (D), and "
            + "the reason the pt-BR mirror is not optional — the public whose "
            + "city this is reads Portuguese.";
    }

    // ------------------------------------------------ capability -> system map

    part def CapabilityAllocation {
        doc /* Which system carries which capability, and where a capability is thin. */
        attribute note : String;
    }

    part allocEstimate : CapabilityAllocation {
        attribute redefines note default "cEstimate -> papers + deployedTools. Well covered.";
    }
    part allocError : CapabilityAllocation {
        attribute redefines note default "cQuantifyError -> papers + gateBattery. Well covered.";
    }
    part allocTransfer : CapabilityAllocation {
        attribute redefines note default
            "cTransfer -> papers (six corpora, seven riders, one external). "
            + "Covered but NARROW IN RIDERS: seven is thin for a behavioural constant.";
    }
    part allocReproduce : CapabilityAllocation {
        attribute redefines note default "cReproduce -> gateBattery + labJournal. Well covered.";
    }
    part allocDeploy : CapabilityAllocation {
        attribute redefines note default
            "cDeploy -> deployedTools. THINNEST LINK: the tools exist and run, "
            + "but no adoption by an actual planning body is evidenced anywhere "
            + "in this repository. See MOE-5.";
    }
    part allocExplain : CapabilityAllocation {
        attribute redefines note default
            "cExplain -> pieces. PARTIALLY MET: piece 1 exists in both languages; "
            + "pieces 2-3 are pending, so the ladder's public rung is incomplete.";
    }
    part allocPrivacy : CapabilityAllocation {
        attribute redefines note default
            "cProtectContributors -> repository policy: no raw tracks, no "
            + "per-ride CSVs, no geometry derived from an external corpus, "
            + "endpoints trimmed from published maps. Enforced, and has already "
            + "caught one live violation mid-experiment.";
    }
}
