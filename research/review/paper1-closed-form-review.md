# Review Assessment — `paper1-closed-form.md` (v2 draft, 870 lines)

**Reviewer:** Cline (Sonnet 4.5), iterative review
**Date:** 2026-07-30
**Scope:** Manuscript claims, internal consistency, math, framing. Gate battery and lab journal assumed trustworthy per author's instruction.
**For handoff to:** Claude Opus 5

---

## 1. Overall impression

A strong, methodologically careful paper whose central idea — decomposing descent recovery into a **parameter-free coasting limit** plus a **behavioural coasting deficit** connected by an exact ledger identity — is genuinely novel and well-derived. The statistical hygiene is above average for this literature: pre-registration, a formal TOST equivalence procedure with a registered margin, held-out corpora, honest dual-pool framing, and explicit scope caveats throughout. The derivations (Appendix A) are correct, the worked example checks out, and cross-table numbers are consistent.

The main vulnerability is **framing weight**: the title and Abstract lean harder on "tested / validated against 2,025 rides" than the shared-input consistency protocol licenses, because both the closed form and the simulation benchmark read the same measured power per ride. The TOST equivalence procedure (now added) substantially closes the statistical gap — formal equivalence to the simulation is established on the transfer pools where $n$ suffices — but "equivalent to the simulation" is still "equivalent to an unvalidated-at-route-level reference under shared inputs." The paper is honest about this in §4.3.2; the title isn't.

---

## 2. Strengths

1. **The deficit identity is the sharpest contribution.** $\delta = E_{\mathrm{legs},-}/(\beta h_-)$ turns "what form does the deficit take?" into a question about pedalling *occupancy* rather than *effort*. It gives a principled, non-ad-hoc reason to prefer a grade-inverse form (the $1/s$ falls out of the physics), and the out-of-sample contest ($\varepsilon_2$ winning 344/513, $k = 0.0051$) is the cleanest empirical result. Verified: from $\varepsilon_{\mathrm{bal}} = (\alpha x_- - E_{\mathrm{legs},-})/(\beta h_-)$ and the $E_{\mathrm{legs}} = 0$ coasting limit, the difference is exactly $E_{\mathrm{legs},-}/(\beta h_-)$. Holds.

2. **Formal equivalence testing (TOST) now in place** (§2.3.4). Registered ±1.0 pp margin (Entry 48), 90% CI of the difference of medians, stratified resampling for pools. The estimand is correctly the difference of medians (not median of per-ride differences), matching the published sentences. This is the right machinery for the parity claims.

3. **Honest dual-pool framing.** D3–D5 and D3–D6 reported side by side, with explicit note that "adding D6 lowers the pooled error only because D6 is the best corpus." Rare and commendable.

4. **Honest scoping throughout.** The ε₂ ≥ 3% restriction, "partially in-sample" labels on per-ride-physics figures, "(α, ε) pair is what's identified," "transfers = 3 riders," and the retracted D2 parity claim (§3.1.2: "*Parity is the one claim in this section the equivalence test declines to support*") are all stated, not hidden.

5. **Lineage notation** (Terminology, line 56). Every table caption now carries an explicit $O = T^{\varepsilon}(D, P) \mid \sigma$ expression. A genuine methodological improvement that makes each result's provenance precise.

6. **The §4.1.2 worked example is arithmetically correct.** Verified end-to-end: $\alpha_r = 6.0$ J/m, $\beta = 749$ J/m, $v_f = 4.6$ m/s from $P = 50$ W ($\alpha_a = 4.9$), corrected totals 125 m, $150 + 98 + 94 - 19 = 323 \approx 320$ kJ. The unit-switch note (J/m → kJ/m) is correct and useful.

---

## 3. Substantive concerns

### Major — the title/Abstract overstate a shared-input consistency check

Both the closed form and the simulation ingest the same measured power stream, the same mass, the same constants per ride (§2.1). So "parity" means the closed form *accounts for energy the same way a simulation that already knows the ingredients does* — not predictive validation. §4.3.2 states this. But:

- The **title** ("Tested on 2,025 Power-Meter Rides") and the **Abstract's opening** ("validated against measured power") invite the misreading.
- The **simulation benchmark is itself unvalidated at route level** — Martin et al. validated the instantaneous balance on flat steady-speed; Dahmen validated speed on tracks; *neither* validated the route-level energy integral. So "equivalent to the simulation" is equivalence to an unvalidated reference.

**Recommendation:** Reframe the headline from "matches a validated simulation" to "matches a forward integration of the validated instantaneous balance, under shared inputs." Lead the Abstract with the accounting-consistency scope. The blind-prediction protocol (§4.4.5) is the real validation and is only "planned" — foreground it as the missing rung.

### Major — the headline 3.5% carries selection optimism the transfer figures don't

Every modelling choice (F1→F4 chain, τ = 2 m, 2% gate, $c \approx 3$ m/km, $\varepsilon_0 = 0.13$) was made on the same 44 author-ridden calibration rides, and the informed run adds hand-chosen per-ride $\varepsilon$ spanning **0.10–0.60** (a sixfold range on the one behavioural parameter the paper studies). The paper calls this "shading into per-ride fitting" — it is per-ride fitting of the target variable. The blind re-run (8.2%) is the honest number, ~2.3× the informed figure.

The defense is structural (D3–D5 never touched selection) and now strengthened by the TOST equivalence on the transfer pools. But the **headline 3.5% still leads the Abstract and Conclusions**. The genuinely out-of-sample frozen-transfer pooled figure — **5.6% [5.2, 6.2]** (D3+D4, $n = 660$) — is a stronger headline and is now stated as such in §3.3, just not promoted.

**Recommendation:** Promote 5.6% to the Abstract headline; present 3.5% as "the calibration ceiling under condition knowledge."

### Moderate — "accurate by cancellation rather than by fit" qualifies every gentle-terrain frozen-pool number

§3.2.2 (line 495) reports the implementation of the ε₂ regime switch and a surprising result:
- Under **frozen priors**: switch makes pooled median *worse* (5.08 → 5.62).
- Under **per-ride inverted physics**: switch makes it *better* (5.51 → 4.12).
- Reason: on the 1,103 sub-threshold rides, frozen CdA = 0.40 (high) over-predicts, but ε_d's clamped median of 0.544 (generous refund on gentle grades) cancels it. Under honest physics (inverted CdA 0.26–0.32), that cancellation vanishes.

The paper's own framing is disarming: "**the frozen grid's sub-threshold ε_d cells are accurate by cancellation rather than by fit.**" This is honest, but it reveals that the **headline frozen-pool accuracy (5.6–5.9%) on gentle terrain rests on a fortuitous cancellation** between two compensating errors. If a planner follows the recipe with their own (lower) fitted CdA, the cancellation breaks and the error moves toward the +5.9 pp ε_f bias shown in Table 6. The paper warns about this (§4.1.2 step-caution, §4.3.4 pairing), but the "accurate by cancellation" finding should be **elevated from a lab-journal-cited parenthetical to a named limitation** — it qualifies every frozen-pool number on gentle-terrain corpora (D4 JAAM, D5, the D3–D5 pool).

### Moderate — ε₀'s *value* is not portable, only its *sign*

Table 4 and §3.4 show that under fitted physics P. Paz's deficit gap moves 0.12 → 0.19 and the 34% margin collapses to a tie. The sweep (§3.4.2) shows the gap spans −0.07 to +0.19 across the parameter grid. The Conclusions call the deficit's *recurrence* "the study's most portable empirical fact" — but positivity of the gap is *structurally* true at the real physics ($E_{\mathrm{legs}} \geq 0 \Rightarrow \varepsilon_{\mathrm{bal}} \leq \varepsilon_{\mathrm{coast}}$) and only *empirically* true under the assumed priors. Calling it "the most portable empirical fact" overstates it — it's closer to a theorem with an empirical sign-check. A planner needs the **value**, which travels only with its priors and scale.

### Moderate — D6's strong performance may reflect data quality, not model quality

D6 is the cleanest external test (shares nothing) and the best result (3.2% vs 3.2%). But D6 is also the **cleanest recording chain** (1.2 m/km noise vs 3.1). The paper shows F4's $c$ fails on D6 *because the chain is cleaner*. The inverse concern is underexplored: how much of any corpus's error is the **elevation source** rather than the **model**? If D6's low error is partly better sensors, then "best performance on the most independent corpus" is partly a statement about sensor quality.

### Moderate — the c ≈ 3 m/km correction and the "removed metres do no work" check share a model

The deadband removes 3.1 m/km; F4 subtracts exactly that rate. Justification is two-fold: (1) the removed metres "do no measurable work" (sustained-climb check), and (2) they accumulate with distance not climbing. But check (1) is performed *under the same model*: if the model's gravity term is right on sustained climbs (which it is — cleanest physics), then of course the sub-metre jitter looks like noise. The momentum-suspension reinterpretation (§4.4.3) is the real physical argument but is described as "honest but partial" with roller over-prediction "unattributed" (rank correlations up to +0.44). **The paper's second correction rests on a mechanism that is itself an open question.** Not fatal — the correction helps — but the causal story is incomplete, and a reviewer should ask whether τ = 2 m is physical or tuned.

### Minor — statistical multiplicity and pre-registration boundary

The paper correctly notes ~12 paired tests imply ~1 false positive at α = 0.05. Good. But several claims ride on single p-values that are marginal or mass-sensitive (e.g., the time-dual, §4.4.1: p = 0.012 but loses significance at the top of the mass sweep). The reader should be told **which tests were pre-registered vs exploratory** — the paper references pre-registration (Entries 29, 33, 34, 48) but doesn't mark, in-text, which table claims are pre-registered. A simple "(pre-registered)" tag on the relevant rows would close this.

---

## 4. Internal consistency & correctness checks

### Numbers across Abstract / Tables / Conclusions — all consistent (one exception)

| Check | Locations | Status |
|---|---|---|
| F3 3.5% [2.0, 5.6], F4 5.9% [3.6, 8.3], sim 5.2% [3.8, 7.3] | Abstract ↔ Table 2 | ✓ |
| Pooled D3+D4 ($n = 660$) = 5.6% [5.2, 6.2] vs sim 6.3% [5.8, 6.8] | Abstract ↔ §3.3.1 | ✓ (441 + 219 = 660 ✓) |
| 3.9% [3.6, 4.1] pooled under per-ride physics | Conclusions ↔ Table 6 | ✓ |
| $k = 0.0051$ | Abstract ↔ §3.2.1 ↔ eq. (8) ↔ Conclusions | ✓ |
| TOST D3+D4: [−0.90, −0.33]; D3–D5: [−0.55, −0.07] | §3.3.1 ↔ §3.6 | ✓ |
| D6 F3·ε_d 3.2 vs sim 3.2 (3.16 vs 3.15 before rounding) | §3.3.1 ↔ Table 3 caption | ✓ |

### ⚠️ One inconsistency found: Abstract deficit range

The **Abstract** (line 23) says the deficit's value spans "**0.12–0.19** on the three São Paulo riders," but:
- **Contribution 4** (line 38) says "**0.12–0.14** on the São Paulo three"
- **§3.3.2** gives point estimates: P. Paz 0.12, JAAM 0.13, author 0.14 (range **0.12–0.14**)

The 0.19 is either JAAM's CI upper bound [0.10, 0.19] or P. Paz's value under *fitted* physics (Table 4: 0.19 [0.17, 0.20]) — a different protocol. The Abstract mixes a point-estimate range with a CI bound or a different-physics value.

**Fix:** Read 0.12–0.14 (point estimates under assumed physics) consistently, or state the convention.

### Mathematical checks (Appendix A) — all verified

| Derivation | Check | Status |
|---|---|---|
| Coasting limit $\varepsilon_{\mathrm{coast}}(s) = \min(1, s_*/s)$ | From $E_{\mathrm{legs}} = 0$ in balance form (A5), with $h_i/\Delta x_i = s_i$ | ✓ clean |
| Deficit identity $\delta = E_{\mathrm{legs},-}/(\beta h_-)$ | Exact from balance form; difference of ε_coast and ε_bal | ✓ exact |
| Braking cancels out of the balance | $W_{\mathrm{brake}}$ doesn't appear in the $E_{\mathrm{legs}}$ term — brakes dissipate gravity's share, never legs' | ✓ follows from balance form |
| Eq. (8) domain ($k/\bar s$ diverges below $\bar s = k \approx 0.51\%$) | Correctly restricted to $\bar s \geq 3\%$ | ✓ |
| Bounds $[-\varepsilon_0, 1-\varepsilon_0]$ | Since $\varepsilon_{\mathrm{coast}} \in [0,1]$ by construction | ✓ |
| F1→F2→F3→F4 chain vs integral (A1) | Each step a stated approximation with a stated residual | ✓ faithful |

### Worked example (§4.1.2)

Verified end-to-end:
- $\alpha_r = 0.008 \times 75 \times 9.79 / 0.98 = 6.0$ J/m ✓
- $\beta = 75 \times 9.79 / 0.98 = 749$ J/m ✓
- $v_f = 4.6$ m/s from $P = 50$ W: $(6.0 + 4.9) \times 4.6 = 50$ W ✓, $\alpha_a = 4.9$ J/m ✓
- Corrected totals: $200 - 3 \times 25 = 125$ m ✓
- Rolling: $6.0 \times 25{,}000 = 150$ kJ ✓
- Aero: $4.9 \times 20{,}000 = 98$ kJ ✓
- Climb: $0.749 \times 125 = 94$ kJ ✓
- Descent refund: $0.20 \times 0.749 \times 125 = 19$ kJ ✓
- **Total: $150 + 98 + 94 - 19 = 323 \approx 320$ kJ** ✓

---

## 5. Editorial notes

1. **Density has increased.** The lineage notation paragraph (line 56), the TOST protocol paragraph (line 409), the switch-implementation paragraph (line 495), the BIC-contest paragraph (line 501), and the metric-caution paragraph (line 503) are all valuable additions — but §3.2.2 is now very dense (four consecutive methodological paragraphs in what should be a results subsection). Consider moving the TOST protocol and the lineage notation to an appendix or a methods-only section, keeping §3.2.2 focused on the deficit result.

2. **The lineage notation is well-defined but under-used in prose.** It appears only in table captions. If the notation is worth introducing, a reader should see it used at least once in the main text (e.g., in §3.3.1 when stating "the genuinely out-of-sample number," the lineage expression would make the claim precise). Otherwise it reads as notation-for-notation's-sake. Conversely, if it's only for captions, it could be stated more briefly there.

3. **The BIC contest paragraph (line 501) introduces D1∪D2 as a joint calibration set** for the deficit contest — 48 rides with $\bar s \geq 3\%$ — but this is the first time D1∪D2 is mentioned as a joint calibration set for the deficit contest. The calibration protocol of §2.3 says $\varepsilon_0$ and $c$ are "fit on D1 only," so D2 entering the deficit's BIC contest is a second use of D2 (it already selected $\varepsilon_f$). This is not wrong — D2 is explicitly in-sample — but it should be noted that D2 contributes to both the regime-test *and* the deficit-form selection, which adds to its selection optimism.

4. **"Broad in conditions, narrow in riders" (§4.3.3) deserves more weight.** Three São Paulo road cyclists is a thin sample for claims about behavioural constants. D6's four Europeans help, but the deficit values there span 0.08–0.30 — a 3.75× range — which suggests the "constant" is rider-dependent to a degree that limits deployability for an unknown rider. The paper says this; it could say it more prominently.

5. **The ε₂ result is prominent but absent from the headline tables.** The paper derives ε₂, shows it wins 344/513, recommends it in the recipe (§4.1.2 step 4) — then notes (§3.2.2) that the tables *don't implement the regime switch* and "adopting it would move Table 3's ε_d column." The switch-implementation paragraph (line 495) now reports what the switch does, but the headline tables still use the frozen ε₀, not eq. (8). A reviewer may find this dissonant. Consider adding "(frozen ε₀; see §3.2.2 for the ε₂ switch)" to the ε_d row labels.

6. **Reference completeness.** The claim "no located precedent for a route-level closed-form ε" (§4.2) is corpus-bounded and stated as such — appropriate. One gap: the paper cites Bigazzi & Lindsey 2019 for the per-grade coasting idle but doesn't deeply compare its *route-level* aggregation to their *per-grade* result — a sentence on why aggregation changes the claim would strengthen novelty.

7. **The AI-assistance declaration is appropriate and commendable** — it specifies the division of labour and points to provenance. No change needed.

---

## 6. Specific fixes recommended

| # | Severity | Location | Issue | Fix |
|---|---|---|---|---|
| 1 | Major | Title / Abstract | "Tested/validated against 2,025 rides" overstates shared-input consistency check | Reframe as "accounts for measured energy"; foreground blind-prediction as missing rung |
| 2 | Major | Abstract / Conclusions | Headline 3.5% carries selection optimism; 5.6% is the out-of-sample figure | Promote 5.6% [5.2, 6.2] to Abstract headline; 3.5% as "calibration ceiling" |
| 3 | Moderate | §3.2.2 (line 495) | "Accurate by cancellation" buried in parenthetical | Elevate to named limitation in §4.3 |
| 4 | Moderate | Abstract (line 23) | Deficit range "0.12–0.19" inconsistent with body's "0.12–0.14" | Reconcile to 0.12–0.14 (point estimates) or state convention |
| 5 | Minor | §3.2.2 | Four consecutive methodological paragraphs in a results subsection | Move TOST protocol and lineage notation to methods/appendix |
| 6 | Minor | Tables 3/5/6 | ε_d rows use frozen ε₀, not ε₂ from eq. (8) | Add "(frozen ε₀)" to row labels; cross-ref §3.2.2 |
| 7 | Minor | In-text | Pre-registered vs exploratory tests not marked | Add "(pre-registered)" tags to relevant claims |

---

## 7. Bottom line

The revision is a **clear improvement** over the prior draft. The two major statistical gaps are closed: equivalence is now formally tested (TOST) where $n$ allows and honestly declared inconclusive where it doesn't ($n = 44$), and the D2 parity overclaim is retracted in-text. The lineage notation and the switch-implementation result add rigor and a surprising, important finding.

The paper's core science — the coasting limit / deficit decomposition, the deficit-as-occupancy identity, the out-of-sample ε₂ contest — remains correct, novel, and well-defended.

**The remaining work is framing, not science:**
1. Fix the title/Abstract to match the accounting-consistency protocol.
2. Promote the frozen-transfer 5.6% figure to the headline.
3. Elevate the "accurate by cancellation" finding to a named limitation.
4. Fix the Abstract deficit-range inconsistency.
5. Consider trimming §3.2.2's density.

The blind-prediction protocol (§4.4.5) remains the missing rung and should continue to be foregrounded as such. The TOST equivalence on the transfer pools ($n = 660$ and $n = 1{,}281$) is a genuinely strong result that substantially supports the parity claims — it is the paper's strongest piece of statistical evidence and should be highlighted accordingly.