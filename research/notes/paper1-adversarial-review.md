# Adversarial review — `paper1-closed-form.md`

**Date:** 2026-07-30 · **Status:** findings recorded, none applied yet ·
**Verdict:** do not freeze content until M1–M6 are addressed.

## How this was produced

A multi-agent adversarial pass, not a read-through. Eight independent attack
lenses — arithmetic, derivation, statistics, overclaim, circularity,
reproducibility, hostile-practitioner, structure — each hunting for defects with
access to the paper, the lab journal, the gate battery and the claim sidecars.
Every candidate finding then went to **three skeptics** with different mandates
(*does the paper already concede it? has the journal settled it? does it
matter?*); a finding needed 2-of-3 to survive.

All agents were primed with the five limitations the paper already concedes
(§4.3.3 cancellation, §4.3.6 wind, §3.2.3's refuted stop-go covariate, the
seven-rider scope, eq. (8)'s absence from the tables) so those would not return
as fresh findings.

**51 candidates → 35 survived → 6 major + 13 minor after synthesis.**
162 agents, ~10.6M tokens, 70 minutes.

> **Caveat on provenance.** These are machine-generated findings. Everything
> below marked ✅ I re-derived myself from the data or the text; everything marked
> ⚠️ is the reviewers' claim, plausible but unverified by me. Do not treat the
> unverified ones as established.

---

## MAJOR

### M1 ✅ The scope statistic is wrong, self-contradictory, and its gate asserts rather than counts

The paper states the share of rides to which ε_d is applied below its own 3%
recommendation threshold **twice, with different values**: 69% in the abstract
and §3.2.2 (*"940 of Table 3's 1,366 rides"*), 52% in §4.3.3.

Counted from `data/results/e46_switch.csv`:

| population | below 3% | n | share |
|---|--:|--:|--:|
| D2–D5 | 930 | 1,356 | **68.6%** |
| D2–D6 (Table 3 as printed) | 1,081 | 2,097 | **51.5%** |
| all six corpora | 1,103 | 2,141 | 51.5% |

So: the published pair `940 / 1,366` is wrong in **both** terms — counted is
`930 / 1,356`. And 69% and 52% are not a contradiction; they are the same
statistic **with and without D6**. Since D6 is Table 3's sixth row, a Table 5/6
column and Contribution 7, 52% is the figure that matches Table 3 as printed and
69% is the one that silently drops the paper's second-largest corpus.

`bootstrap_ci.py` hardcodes `_t3n = 1366`, so the gate **certifies a denominator
matching no population** — the precise failure `data-graph.ttl` was written to
prevent, recurring one generation later. `data-graph.ttl` also asserts the
D3–D5 pool is 1,366 against Table 3's printed 1,281.

**Fix.** Choose one population and name it. Replace the hardcoded `_t3n` with a
count over the CSV. Correct `data-graph.ttl`. Note the bolded 69% survives under
the D2–D5 reading (68.6%); only the parenthetical counts and the unnamed
population are wrong.

### M2 ✅ Table 6's D6 reversal is measured, gated, and never stated in prose

Table 6, D6 column (n = 743), with **disjoint 95% CIs**:

| | median \|Δ%\| |
|---|--:|
| simulation | **1.6** [1.5, 1.8] |
| F4 · ε_f (best law) | 2.5 [2.3, 2.7] |
| F3 · ε_d | 3.0 [2.7, 3.3] |

The prose after Table 6 reports only the D3–D5 pool (*"3.9% against the
simulation's 4.0%"*). §4.1.1 states without qualification that *"we measured no
accuracy cost on our corpora for abandoning simulation at the route level."*

**Verified: D6 appears zero times in the entire Discussion and Conclusions.**
The lab journal carries it under a bold heading — *"Parity breaks on D6"* — and
§3k of the battery gates all four cells. This is a disclosure gap, not ignorance.

It matters more than the others because it lands on (i) the protocol §4.1.2
recommends, (ii) the corpus §2.3.1 calls *"the cleanest held-out test
available"*, (iii) the largest single law-vs-simulation comparison in the paper,
and (iv) a gap (1.46 pp) **exceeding the paper's own registered ±1.0 pp
relevance margin**. Entry 48's TOST set contains no D6 row, so no formal test
covers it either. The paper reports adverse results against interest everywhere
else — D2's TOST, D5's sign test, three refuted predictions. This is the one it
does not.

**Fix.** Two sentences: state the reversal and that it is protocol-specific
(under the frozen protocol D6 is at parity); scope §4.1.1's licensing sentence.

### M3 ✅ §4.3.1 calls D3–D5 the held-out set; D5 contains the calibration corpus

§4.3.1: *"D3–D5 never touched the selection process and serve as the held-out
validation set, which is why the pooled D3–D5 figure — not the calibration one —
is this paper's headline accuracy claim."*

The paper's own §2.3.4 says D1 ⊂ D5 and 58 of D2's 62 clean rides are in D5. So
~102 of that pool's rides are the ones that fixed ε₀, c, τ, the F3/F4 choice and
ε_f. The second clause also contradicts the abstract, §3.3.1 and §5, which all
name D3+D4 (660 rides, 5.6%) as the genuinely out-of-sample number.

An unqualified independence claim sitting inside the subsection titled
*"selection optimism"* is exactly where a reviewer probes for circularity. The
fix helps the paper: the clean figure (5.6%) beats the contaminated pool's 5.9%.

### M4 ✅ §4.3.4 still describes a three-rider study

*"The rider sample, by contrast, is three people in one metropolitan region…"*,
closing with *"three independent confirmations"*. **Verified: the §4.3 block
contains no "seven", no "D6", no "European"** — while the abstract's new Scope
paragraph cites §4.3.4 as where the seven-rider limit is priced.

It also still *speculates* that descent habit *"may track gearing, position, or
riding culture"* — which Entry 43 Arm B measured (D6 vs Brazilian descent
occupancy, disjoint CIs in every grade band). And §5 says the deficit's value
*"travels only with its priors and scale"*, omitting the rider — the one axis
with a measured 3.7× spread (0.08–0.30) that the abstract itself headlines.

### M5 ⚠️ D6's published masses are advertised as external grading and never reported

§2.3.1 promises the implied-mass inversion *"can be graded against four known
values rather than the author's one"*; §2.3.3 reports only D3/D4/D5 masses. The
cross-reference is dangling — no D6 mass appears anywhere in the paper.

Entry 43's registered prediction P4 reportedly found user_2 +8.4, user_3 +7.8,
user_5 +10.9 (inside the registered 7–12 kg window) and **user_1 +13.7, outside
it** — a ~100 kg implied system mass for an 86 kg rider. user_1 is also D6's
worst F3·ε_d rider. Contribution 9 sells this as *"validated against logged and
known masses"*, and the one registered D6 prediction whose verdict is dropped is
the one that partially failed.

*Not independently verified — check Entry 43 before acting.*

### M6 ⚠️ The gate-coverage claim is broader than the battery

Three sentences claim every published number is re-derived (Contribution 8,
§2.3.4, Fig. 1 caption, Data availability). Reportedly not covered:

- **`eps_hypothesis.csv` is absent from the battery** — every D1 descent
  statistic in §3.2, *including the 0.13 → 0.08 RMS / 37% reduction that §3.2
  nominates as the statistic it leads with*, and on which §3.6's H2 verdict
  rests. The reviewer reproduced the numbers by hand (RMS 0.0788 vs 0.1233), so
  this is coverage, not error.
- The four env-suffixed CSVs behind Table 4's **fitted** column and §3.4.2's mass
  sweep. (Table 4's *assumed* columns are gated — the finding as originally filed
  overstated this.)
- `descent_rms()` prints the gap but never gates it, and no bootstrap CI is
  computed for any gap, so the published bands [0.10, 0.14], [0.10, 0.19],
  [0.12, 0.16] have no re-derivation.

Matters because §3.4.1 uses the ungated fitted column to retract the 34% descent
margin and widen ε₀ to 0.12–0.19, which §5 restates as the portability bound. A
future re-baseline would move these silently while the battery passes green.

*Not independently verified.*

---

## MINOR

| # | Where | What | Fix |
|---|---|---|---|
| m1 | abstract, §3.2.2 | *"0.067 → 0.055, winning 344 of 513"* belongs to **A′** (the constant refitted on the fit half), not to frozen ε₀. Reviewer reproduces: ε₂ beats A′ 344/169 but beats 0.13 **328/185**, held-out 0.064 → 0.055. Inflates the margin over the deployed constant by ~25%. `bootstrap_ci.py` hardcodes the mis-attributed pair. | Name the baseline; add ε₀'s own pair |
| m2 | §1.3.2 | *"the two deficit forms differ by less than 0.05"* — true to s̄ = 6.375%, but 0.077 at 9.69%, the top of the tested range | *"at most 0.08 over 3.0–9.7%"* |
| m3 | Table 5 | D6 column bolds F4·ε_f 4.6 while F3·ε_d 4.3 is the minimum; sits above the claim that ε_f beats ε_d on every corpus, which this column refutes | Move the bold; qualify the claim |
| m4 | Table 3 | D3–D6 pooled column bolds nothing though 4.9 is its minimum | Two tags |
| m5 | §3.2.2, §4.3.3 | *"well above the 0.26–0.32 these riders invert to"* — §3.5.1 reports the same inversion as **0.26–0.39**; 0.40 is not "well above" for D4 (0.391) or any D6 rider. The cancellation verdict rests on the bias flip and survives | Quote 0.26–0.39 |
| m6 | §3.2.2 | bare `$c$` used for the ε₀-form's fitted constant while Terminology binds `$c$` to the ascent-noise rate | Rename to ε₀ |
| m7 | §4.1.3 | *"at s̄ = 6% it refunds 0.085"* — 0.085 is the **deficit subtracted**, not the refund | *"docks 0.085 from the coasting limit"* |
| m8 | §4.1.2 | *"drag dominates the flat balance"* — rolling is 55.1% at the 50 W anchor; crossover at 18.4 km/h. Conclusion (insensitivity to mass) holds | Restate the reason |
| m9 | §3.2.2 | *"All four forms were fitted on D1 ∪ D2"* — Entry 47 dropped ε₁, and the winning ε₀-frozen was not fitted | Say which four |
| m10 | §1.3.2, A.5 | the *"exact ledger identity"* is cited to Appendix A three times and never displayed there; exact only for the **unclamped** quantity | Display it; state the clamp |
| m11 | A.5 | *"or lumping with the mean descent grade"* — identical unclamped, but median(ε_lump − ε_coast) = 0.131 on D1 under the clamp | Qualify |
| m12 | §4.1.3 | *"it is the habit constant that transfers across riders"*, unqualified — the abstract denies exactly this | Cross-reference |
| **m13** ✅ | §3.1.2 | **My defect.** Claim anchors sit after the wrong numbers: `d1.blind.f3.med` (pc:value 8.2) follows *"the simulation at 8.4%"*; `d2.f3.med` (7.7) follows *"against 6.6%"* | Move both anchors |

### m13 is worse than filed, and it is a tooling defect

`check_paper_stats.py` **passed both**. It verifies that an anchor *exists* and
that `pc:value` is asserted in the named gate section — but never that the number
the anchor *sits at* matches `pc:value`. So an anchor can point at the wrong
statistic indefinitely and the check stays green.

That undercuts the annotation system's main promise. **Fix the checker first**
(compare the number immediately preceding the anchor against `pc:value`, with
the same rounding tolerance), then re-run it over all 25 claims — there may be
more than these two.

---

## What held

Attacked and found sound:

- **Every headline number.** 5.6% [5.2, 6.2] D3+D4; 5.9% D3–D5; 3.9% regime
  pool; 3.5%/5.9% informed; 8.2/8.4 blind; all Table 3/5/6 cells reproduce.
- **The eq. (8) contest arithmetic**, recomputed independently: k = 0.005060,
  A′ = 0.13340, held-out 0.0545, 344/169. Only the *attribution* is off (m1).
- **The 69% figure itself** under the D2–D5 reading (68.6%).
- **The D1 descent statistics** (RMS 0.0788 vs 0.1233, 36–37%) — ungated but
  correct.
- **Corpus-overlap accounting** (2,025 unique / 2,127 evaluations, D1 ⊂ D5,
  58 of 62), disclosed and acted on in Table 3's caption.
- **The accuracy + signed bias + CI convention**, honoured in every results table
  without exception.
- **Adverse results reported against interest** wherever reported at all.
- **Every TOST interval printed in full**, so the ±1.0 margin conceals nothing.
- **The five pre-declared concessions** are as stated.

---

## Recommendation

**Do not freeze.** M2 is the one that would embarrass the paper if a reader found
it first: an adverse, gate-certified, disjoint-CI result on the paper's own
cleanest held-out corpus, under the protocol it recommends, contradicting
§4.1.1 — in the journal under a bold heading, absent from the Discussion
entirely. M1 puts two irreconcilable numbers on the paper's central
self-criticism and lets a stale gate certify one of them.

The work is small and almost entirely prose. **M2–M5 are 1–2 sentences each; M1
is a recount plus three edits; M6 is ~15 lines of gate code or an honest
rescoping.** The minors are one-line fixes, except m13 which needs the checker
fixed first.

**No result, table cell, CI or planner recommendation changes as a consequence of
any of this.**
