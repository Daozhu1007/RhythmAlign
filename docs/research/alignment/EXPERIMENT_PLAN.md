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

## Resume protocol amendment

The preserved 81-case corpus is complete and is retained without recomputation. Research resumes from WIP commit `5b1fcd472a94470872dc1f837a7f473c0edd5282`; frozen scientific files are verified against `ffa6b07`, allowing research HEAD to advance. No RA-1.2D evaluation results enter threshold selection. The final verification permits only Git's LF/CRLF checkout conversion when comparing preserved files with repository blobs; it records both hashes.

Before inspecting new probe outcomes, the remaining probe grids are fixed in `probes.py`: 384 feature-space null draws, 36 waveform null cases, five partial-support cases, three disjoint-repeat cases, four close-replica cases, and three decision-seam curve constructions. They distinguish local correctness from unique/global placement; the latter constructions must not be relabeled as ordinary wrong-song examples.

Following the preserved-corpus analysis and before running the additional search, add an exhaustive mismatch challenge: all 29 recording IDs against all 20 reference-track IDs, excluding each recording's own project (551 pairs). Use unchanged feature and decision functions with per-source feature reuse, verify equivalence on preserved real pairs, retain every outcome, and stop after the full fixed grid. This is exploratory adversarial search on previously exposed source identities, not a new population test or an additional holdout. If a wrong-project acceptance occurs, inspect its evidence before interpreting it as no-shared-content failure.

## Completion record and post-discovery amendments

Completed 2026-09-12. All planned stages above are complete. The 551-pair search found one accepted recording/reference mismatch. Because room recordings can contain another song, a **post-discovery** fixed control used all 20 clean references as queries against the other 19 references (380 directed pairs). This produced 22 accepted directions / 11 unordered song pairs. It was not called a fresh holdout or used for threshold fitting.

The first accepted clean pair was selected for independent file-entry validation, contribution localization and fixed first/last-five-second interventions. Both the room candidate and the clean candidate were rerun twice through the full frozen file API. Follow-ups include own-reference and clean-source controls, fresh feature generation, a fresh cropped-audio run, and single-method removal at the clean pair. These are causal/diagnostic follow-ups chosen after discovery, not confirmatory estimates of normal-user risk.

| Stage | Completion |
|---|---|
| Preserved corpus | 81 rows retained; 81 exact decision replays; 70/70 historical outcome/reason matches. |
| Baselines, ablations, dependence, risk-coverage | Complete on preserved curves/audio; raw counts and retrospective curves in `analysis.json`. |
| Feature nulls | 384/384; seed 20260912 + replicate 0–15, shared across condition cells. |
| Audio nulls | 36/36; reference seed 71, query seed 20260912 + 100 + replicate 0–5. |
| Support / repetition | 12/12 waveform cases; seeds base + 200/201/202 respectively. |
| Curve geometry | 3/3; per-method seeds base + 300 + method index; synthetic decision-seam evidence only. |
| Room mismatch grid | 551/551; all 49 source features regenerated, 21 preserved real-pair curve checks < 1e-7. |
| Clean mismatch grid | 380/380; exact same freshly generated source-feature cache; first accepted pair has independently verified 0.0 curve differences. |
| Counterexample follow-up | Complete; full file repeats, control pairs, attribution, boundary interventions, method removals. |
| Literature and synthesis | Complete in the two companion reports. |
| RA-1.2D relevance | Read-only comparison with `20d4816` after scientific experiments; executable AST equality with explicit presentation/ETA exclusions, worker call-path inspection. |
| Verification | Baseline suite 48 passed; waveform ±2.5 s sign controls passed; preserved Git content unchanged; figures visually inspected. |

## Commands and dependencies

From the repository root, using the recorded global Python 3.10.11 environment:

```powershell
# The following two commands created the preserved WIP results BEFORE pause.
# They are documented for fresh reproduction; they were NOT restarted on resume.
python experiments/alignment_research/study.py audit
python experiments/alignment_research/study.py corpus

# Completed resume stages, in dependency order.
python experiments/alignment_research/probes.py feature-nulls
python experiments/alignment_research/probes.py safeguards
python experiments/alignment_research/probes.py curve-counterexamples
python experiments/alignment_research/probes.py audio-nulls
python experiments/alignment_research/mismatch_search.py
python experiments/alignment_research/investigate_counterexample.py
python experiments/alignment_research/clean_mismatch_search.py
python experiments/alignment_research/investigate_counterexample.py clean
python experiments/alignment_research/investigate_counterexample.py ablate
python experiments/alignment_research/analyze.py
python experiments/alignment_research/verify.py
```

The clean search needs source features created by the recording mismatch search. Counterexample follow-ups append to the original validation result. Analysis reads all completed result files and the preserved 81 curve caches. The final verifier invokes `python -m pytest -q` itself. Repeating an experiment overwrites its named research output; copy the archived results first if comparing a new environment.

Recorded versions: NumPy 2.2.6, SciPy 1.15.3, librosa 0.11.0, numba 0.64.0, soundfile 0.13.1, imageio-ffmpeg 0.6.0, matplotlib 3.10.9, pytest 9.1.0; global `psutil` 7.1.3 is available for the baseline suite. The repository virtual environment lacked `psutil`, so it was not used for completed validation. The scripts record their environment and SHA values in JSON. Source manifests record complete file and decoded-array SHA-256 values; no personal absolute media paths are written to results.

Scientific inputs stay pinned to `ffa6b07`. The only change to the preserved harness is allowing a research HEAD while checking the actual frozen input contents. No feature, threshold, or production behavior was retuned. The final paper verdict is `ENGINEERING_ONLY`; the release-gate outcome is `RELEASE_BLOCKER_FOUND`. Future independent data and a production support-verification fix remain proposed downstream work, not missing stages of this completed study.
