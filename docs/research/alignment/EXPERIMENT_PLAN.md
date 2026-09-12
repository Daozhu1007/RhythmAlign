# Alignment research protocol

Baseline: `ffa6b07a591dbdb54ae8350f3d27dce3ed74c847`. Written before running new experiments in this study. All experiments are exploratory: the existing reports and their outcomes were available before this protocol. No threshold or feature change will be applied to production. The historical RA-1.2C holdout will be called **historical holdout**, never a fresh test set for this study.

## Falsifiable hypotheses

| ID | Claim under test | Evidence against the claim |
|---|---|---|
| H1 | Within-feature peak Z is an unreliable universal confidence score under structured interference. | A Z-only selector matches full v2 risk at comparable coverage across new sources and null types. Z is not itself a probability; reliability ranking and threshold transportability are the measurable claims. |
| H2 | Cross-family evidence adds predictive value beyond the strongest individual feature. | One feature or simple score fusion attains the same or better risk-coverage trade-off; errors strongly coincide. |
| H3 | Competing-peak structure predicts correctness better than Z alone on difficult cases. | Margin-only ranking is no better, or unique incorrect peaks survive margins. |
| H4 | Selective alignment lowers wrong-accept risk at useful coverage. | It only rejects cases other methods already solve, or accepts structural counterexamples despite agreement. Report coverage explicitly; useful coverage remains application-dependent. |
| H5 | HPSS materially improves PCEN alignment robustness at low SNR. | Removing HPSS preserves or improves correctness/coverage; improvement is restricted to the development example. |

## Planned experiments, in priority order

1. Recompute committed counts and extrema, audit source identities across RA-1.2B/C, and inspect report/code disagreements. Preserve exact, approximate, unknown, and no-match ground-truth strata.
2. Run all 56 historical exact-insertion positives and 14 historical hard-negative/tiled cases from local source manifests, plus the motivating manual-label case. Reuse the frozen engine's complete feature curves for baselines and ablations. Decode original media read-only into ignored scratch; save content hashes and path-free IDs. Compare waveform overlap-normalized correlation, GCC-PHAT, chroma, onset, hybrid, PCEN, PCEN+HPSS, equal standardized score fusion, naive voting, and v2 where feasible. Full audio durations, 22,050 Hz, hop 512, no implicit input normalization.
3. Ablate HPSS, plain PCEN, tonal, onset corroboration, uniqueness, ambiguity, and overlap separately. Diagnostic policy modifications stay inside the research process. Baseline choices and threshold sweeps are descriptive, not holdout-calibrated operating policies.
4. Measure feature-curve dependence and top-1 error co-occurrence on exact-GT positives. Report paired counts, without treating repeated sources as independent observations.
5. Test null search length and feature dimension using independent feature-space sequences, then validate selected duration/null conditions with the actual audio engine. Seeds start at 20260912. Distinguish Gaussian mathematical nulls from real-audio nulls.
6. Attempt to falsify geometric overlap and ambiguity safeguards using short shared excerpts, unequal repeated occurrences, and feature-curve counterexamples. A constructed accepted partial match must be classified under an explicit task contract, not casually called a wrong-song failure.

## Evaluation and provenance

For exact single-offset positives, acceptance within 0.15 s is CORRECT_ACCEPT; acceptance outside is WRONG_ACCEPT; refusal is SAFE_ABSTAIN. Manual-label case uses its documented 0.4 s interval half-width, not 0.15 s. No-match cases count any output as WRONG_ACCEPT. Repeated/partial matches require both content-match and unique-placement reporting; policy ambiguity violations are separate from incorrect offsets.

Report raw correct/wrong/abstain counts, coverage, conditional wrong-accept risk, unconditional wrong-accept fraction, positive coverage, reason frequencies, and descriptive risk-coverage sweeps. No fabricated probability calibration, no fitting to the historical holdout, and no iid confidence bounds asserted for repeated-source cases. Proposed new-data calibration is separate from completed exploratory results.

Commands, environment, seeds, case construction, hashes, and actual completion status will be recorded with research scripts/results. Planned experiments that cannot be completed will remain explicitly planned.
