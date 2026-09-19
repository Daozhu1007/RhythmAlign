# Paper Scope After the Final Benchmark

Status: decision memo (RESULTS-INTEGRITY-1, 2026-09-20). The final
benchmark is complete and sealed; the 2-creator feasibility pilot of
`HUMAN_LIGHT_STUDY_DESIGN.md` Section 10 has NOT been run.

## Verdict

**BOTH_ROUTES_AVAILABLE.** The technical core can be drafted
immediately; running the pilot before submission unlocks the original
(stronger) claim package. Neither route weakens any reported number.

## 1. What paper can be written NOW?

The full benchmark paper: frozen protocol, risk-coverage comparison
under the four corrected metric definitions (RhythmAlign 0 wrong accepts
anywhere and 83.3% correct-placement yield vs 24/24 wrong-reference
false accepts for GCC-PHAT and NCC; Panako safe at 2/24), Kdenlive
technical stratum (2/10), strict-repeat instability finding, and the
v2-corrected reporting semantics. Claims C-A (minus its pilot clause)
and C-B are fully supported. Every coverage/refusal statement must stop
at "the system refuses; the benchmark does not measure what refusal
costs the user".

## 2. What additional claim would the 2-creator pilot unlock?

Only the pilot-scoped additions: a measured, feasibility-level account
of refusal recovery (approximate time and steps after ABSTAIN), observed
recovery behavior after a wrong-reference discovery, evidence that the
ACCEPT/ABSTAIN interface is understandable without training, and
approximate end-to-end task time. No population-level HCI claim — the
design already forbids that.

## 3. Is the pilot necessary for submission under the original route?

Yes. `HUMAN_LIGHT_STUDY_DESIGN.md` builds its recommended minimum paper
as benchmark + essential comparators + pilot, and C-A as frozen includes
"refusal costs are quantified and bounded in a creator pilot"; pillar 3
exists so that "safe" is never claimed without "and here is what safe
costs". Submitting the original scope without the pilot would misstate
the design's own claim package.

## 4. What is the cost of skipping it?

The paper proceeds under a narrowed claim: delete the C-A pilot clause
and pillar 3, reframe refusal cost as an explicitly unmeasured
limitation (RhythmAlign's 4 abstentions are silent coverage loss of
unknown recovery cost), and drop the framing sentence's pilot clause.
The measured correctness/safety result survives untouched. Costs: a
reviewer can ask exactly the question the pilot answers ("what does an
abstention cost a real creator?") and the paper must answer "not
measured, by design scope"; the paper loses its human-feasibility
pillar and reads as benchmark-plus-editor-stratum only. This is honest
but is a visible scope reduction from the design document.

## 5. Recommended next move

Draft the paper NOW on the benchmark-only skeleton (nothing drafted
depends on the pilot), keep the Section 10 pilot protocol ready, and
decide before submission — pilot first if recruitment/consent is
practical, otherwise submit the reframed benchmark-only paper with
refusal cost stated as an open measured-tomorrow limitation.
