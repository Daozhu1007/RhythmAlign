# Second Review Response V2

Response memo for the second independent review of PAPER-DRAFT-1, executed during MANUSCRIPT-FINALIZATION-1 on branch `research/applied-system-paper` (starting HEAD `ed337e9`). This memo documents the resolution of the two remaining rewrite-only issues. It supersedes nothing in [HOSTILE_REVIEW_RESPONSE_V1_1.md](HOSTILE_REVIEW_RESPONSE_V1_1.md), which remains the response of record for the first review's M1–M4 and m1–m3 issues. Tone is factual by design. This memo quotes removed wording in order to document it; the automated wording gate deliberately covers the manuscript set (draft, tables, claim ledger, citation ledger, citation gaps, first-review memo), not the response memos.

## Second-review verdict and status

- Verdict: **TECHNICAL_CORE_DEFENSIBLE_WITH_MINOR_REVISION**.
- MORE_EXPERIMENTS_REQUIRED: **NO**.
- Pilot status: **PILOT_NOT_NEEDED_FOR_CURRENT_SCOPE** (none conducted; none required for the current scope).
- All first-review issues **M1–M4** and **m1–m3**: **RESOLVED** (dispositions preserved in [HOSTILE_REVIEW_RESPONSE_V1_1.md](HOSTILE_REVIEW_RESPONSE_V1_1.md)).
- Remaining issues: exactly two, both rewrite-only (Issue A and Issue B below).
- No new data collected; no result changed; no experiment was run or modified. No threshold, comparator, protocol, production code, source set, or frozen artifact changed.

## Issue A — GCC-PHAT zero-overlap wording

**Reviewer issue.** Ordinary linear cross-correlation has a physical non-overlap region in the lag geometry, but PHAT weighting/normalization means the weighted FFT curve must not be described as mathematically guaranteed to be zero there.

**Disposition.** Accepted; clarifying wording added; no evidence changed.

**Change made.** §4.5 of [PAPER_DRAFT_V2.md](PAPER_DRAFT_V2.md) now states that the corrected v2 unwrap follows the physically meaningful linear-lag support determined by the two signal lengths and that the original midpoint unwrap was invalid for unequal lengths; it explicitly disclaims any statement that PHAT weighting preserves the ordinary zero-overlap zeros exactly or that out-of-support PHAT-weighted values are numerical roundoff; and it records the operative fact that none of the 50 stored final GCC argmax indices fell in the physical zero-overlap index region, so the subtlety does not alter any measured v2 final outcome. CLAIM_LEDGER_V2 entry L30 forbids transferring the ordinary correlation's zero-overlap identity to the PHAT-weighted curve, characterizing out-of-support PHAT values as implementation dust, or claiming the benchmark validates a general out-of-support theorem. The preserved [GCC lag audit](../GCC_PHAT_LAG_AUDIT.md) received a purely additive clarifying addendum (§12) distinguishing the ordinary correlation's algebraic zero-overlap identity from the PHAT-weighted curve; every original audit section is preserved verbatim and no recorded value, hash, prediction, or outcome changed.

**New data required?** No.

## Issue B — NCC counterfactual wording

**Reviewer issue.** The Discussion contained one overbroad sentence: "The 30 s edge-lag guard alone accounts for the NCC contrast."

**Disposition.** Accepted; sentence removed and replaced with the established, counterfactually scoped statement.

**Change made.** The manuscript now states that RhythmAlign's 30 s candidate-overlap requirement excludes all five observed erroneous NCC placements, and — because a 30 s-constrained NCC was not evaluated — that this observation does not determine the counterfactual performance of a matched NCC system (§6.4, §7, and the Table 7 NCC overlap contract panel in [PAPER_TABLES_V2.md](PAPER_TABLES_V2.md)). The evidence establishes exactly: all five OBSERVED NCC wrong-positive placements occur at usable overlaps below 30 s; RhythmAlign's frozen candidate policy excludes those five observed placements; candidate-domain differences materially contribute to the observed comparison; and the comparison reflects estimator and candidate-policy differences and does not isolate the causal effect of abstention (retained verbatim in the required contract sentence and abstract). The manuscript draws no conclusion about what NCC would output after imposing a 30 s minimum-overlap rule, whether the true lag would then become NCC's argmax, whether NCC would refuse, or whether all five NCC errors would disappear under a matched policy. CLAIM_LEDGER_V2 entry L31 records the prohibition.

**New data required?** No. Scoring a 30 s-constrained NCC on the exposed final data would be a new experiment, reserved by the frozen protocol for a new protocol and new data.

## Cross-cutting statement

No experiment, comparator execution, threshold, scoring rule, pairing, protocol, or production code changed during MANUSCRIPT-FINALIZATION-1. All frozen raw records, sidecars, and sealed artifacts remain hash-verified unchanged; the only edit outside the paper directory is the purely additive clarifying addendum to GCC_PHAT_LAG_AUDIT.md. Numerical results are identical to PAPER_DRAFT_V1/PAPER_TABLES_V1: `validate_paper_v2.py` proves the V1→V2 manuscript, table, and ledger diffs are exactly the enumerated wording edits, with every decimal-bearing token identical to V1 and the abstract unchanged. New data collected: **NO**. Result changes: **NO**. Experiments run: **NO**. Pilot: **NOT_CONDUCTED** — PILOT_NOT_NEEDED_FOR_CURRENT_SCOPE. Citation TODOs: **0** (no literature expansion; [CITATION_LEDGER_V1.md](CITATION_LEDGER_V1.md) unchanged). Verdict: **SCIENTIFIC_CONTENT_FINAL_CANDIDATE**; venue formatting pending; submission readiness not claimed.
