# Paper Tables V2

STATUS: SCIENTIFIC-CONTENT FINAL CANDIDATE TABLES V2 — second-review wording revision only; every table identical to PAPER_TABLES_V1.md (kept as revision history); sealed benchmark evidence; creator pilot NOT_CONDUCTED.

Numeric authority: [reporting v2](../../../../experiments/applied_system/final_pack/results/final_benchmark_reporting_v2.json) (V2) for all systems, plus the corrected [gcc_phat_v2_lagfix_results.json](../../../../experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_results.json) (G2) and its frozen correction manifest for the valid GCC comparator. Composition uses the frozen benchmark/acquisition manifests; condition, source, and paired panels use only raw counts in the immutable original final-results artifact (F), never its obsolete coverage fields. Kdenlive per-pair detail uses its frozen result artifact (K). All tables are projections of stored evidence, not new performance analyses. Fractions retain exact denominators; displayed decimals are rounded. V2 is a wording-only revision: every table and every number below is identical to PAPER_TABLES_V1.md; the only textual change is the added counterfactual-scoping sentence in the NCC overlap contract panel.

## Table 1 — Benchmark composition

| Component | n | Sources / inputs | Role |
| --- | --- | --- | --- |
| ORDINARY | 10 | S01, S02, S03, S04, S05, S06, S07, S08, S09, S10 | Primary EXACT_GT |
| LOW_LEVEL | 3 | S01, S03, S05 | Primary EXACT_GT |
| TAP_DOMINANT | 3 | S02, S04, S06 | Primary EXACT_GT |
| INTERFERENCE | 4 | S07, S08, S09, S10 | Primary EXACT_GT |
| PARTIAL | 2 | S01, S02 | Primary EXACT_GT |
| DEVICE_VARIATION | 2 | S09, S10 | Primary EXACT_GT |
| Primary positives total | 24 | 10 source identities | Dependent within source |
| Constructed wrong references | 24 | Same primary recordings | NO_MATCH; directed, frozen take-index rotation |
| Strict repeats | 2 | S01, S02 | Separate from primary counts |
| Kdenlive positive pairs | 10 | Selected primary takes | Separate technical stratum; no negative arm |

Acquisition: 3 sessions, 2 rooms, 2 recording devices; 26/26 captures GT_VALID (24 primary + 2 repeats). Sources are the independence unit; primary takes and reused wrong-reference recordings are dependent. Exactly 3 source identities were preflagged for repetitive structure. The four interference takes (final17–final20) produced trimmed inputs of approximately 136.9–139.3 s versus approximately 62.9–68.7 s for the other primary takes (frozen lengths in the correction manifest; reason not documented in the acquisition record). Per-take drift QC assigns final21–final22 to D1 (SESSION_2, ROOM_A); only final17–final20 and final23–final24 used D2. Optional authentic-handcam, version-mismatch, external-domain, and creator-pilot evidence is not included. Source: frozen manifests, FINAL_SOURCE_SELECTION.md, FINAL_ACQUISITION_QC.md, gcc_phat_v2_lagfix_correction_manifest.json.

## Table 2 — Main system results

100 ms primary correctness tolerance. First three metrics: primary positives only. Last metric: constructed wrong references only. Kdenlive has a separate denominator (Table 5). GCC-PHAT = corrected `gcc_phat_argmax_v2_lagfix` (original v1 evidence preserved as defective-implementation evidence; scored counts identical). NCC = unconstrained full-lag argmax (no minimum-overlap requirement). RhythmAlign minimum usable overlap = 30 s.

| System | Acceptance coverage | Correct-placement yield | Positive-case accepted error rate | Wrong-ref false accept |
| --- | --- | --- | --- | --- |
| RhythmAlign v1.2.0 | 20/24 (83.3%) | 20/24 (83.3%) | 0/20 (0%) | 0/24 (0%) |
| GCC-PHAT argmax (v2 lagfix) | 24/24 (100%) | 10/24 (41.7%) | 14/24 (58.3%) | 24/24 (100%) |
| NCC argmax (unconstrained) | 24/24 (100%) | 19/24 (79.2%) | 5/24 (20.8%) | 24/24 (100%) |
| Panako OLAF | 2/24 (8.3%) | 2/24 (8.3%) | 0/2 (0%) | 0/24 (0%) |

Acceptance coverage = accepts / positives; correct-placement yield = correct accepts / positives; positive-case accepted error rate = wrong positive accepts / all positive accepts. Acceptance coverage and correct-placement yield coincide for RhythmAlign and Panako here only because their observed positive accepts were all correct. GCC-PHAT and NCC always output. Source: V2.body.reporting_metrics_100ms.per_system with GCC counts asserted equal to G2 per-case recomputation. Counts are unchanged at 50/100/150 ms (V2.body.counts_by_tolerance; G2.summary_outcome_counts_by_tolerance).

## Table 3 — Placement error

Positive placements only. The conditioning and unit columns are essential: successful-case errors in milliseconds and all-produced errors in seconds describe different distributions. Refusals produce no offset and are not assigned zero error. GCC-PHAT rows are recomputed from the corrected v2 lagfix records (G2 per-case; the frozen inclusive-quartile method reproduces the stored V2 distributions for the lag-identical records).

| System | Conditioning | n | Unit | Median absolute error | IQR | Maximum |
| --- | --- | --- | --- | --- | --- | --- |
| RhythmAlign v1.2.0 | CORRECT_ACCEPT only | 20 | ms | 7.90 | 5.47–10.61 | 15.68 |
| RhythmAlign v1.2.0 | All produced positive placements | 20 | s | 0.0079 | 0.0055–0.0106 | 0.0157 |
| GCC-PHAT argmax (v2 lagfix) | CORRECT_ACCEPT only | 10 | ms | 0.22 | 0.21–0.30 | 3.77 |
| GCC-PHAT argmax (v2 lagfix) | All produced positive placements | 24 | s | 29.3135 | 0.0002–55.3648 | 113.1878 |
| NCC argmax (unconstrained) | CORRECT_ACCEPT only | 19 | ms | 3.79 | 3.71–3.90 | 3.94 |
| NCC argmax (unconstrained) | All produced positive placements | 24 | s | 0.0039 | 0.0037–0.0039 | 153.3829 |
| Panako OLAF | CORRECT_ACCEPT only | 2 | ms | 15.13 | 11.73–18.52 | 21.92 |
| Panako OLAF | All produced positive placements | 2 | s | 0.0151 | 0.0117–0.0185 | 0.0219 |

Every CORRECT_ACCEPT placement was below 25 ms. This does not describe every accepted placement. In particular, the all-produced NCC median remains small while its maximum reveals a large wrong-placement tail. Wrong-reference outputs have no true timing target and are excluded from these error distributions. Source: V2.body.error_distributions_positives; G2 per-case records for GCC-PHAT.

## Table 4 — Condition-level raw counts

Each system cell is **CORRECT_ACCEPT / WRONG_ACCEPT / refusal**, as three counts, not a fraction. Refusal means native ABSTAIN for RhythmAlign and NO_MATCH for Panako. No subgroup inference.

| Condition | n | RhythmAlign v1.2.0 | GCC-PHAT argmax (v2 lagfix) | NCC argmax (unconstrained) | Panako OLAF |
| --- | --- | --- | --- | --- | --- |
| ORDINARY | 10 | 9/0/1 | 5/5/0 | 9/1/0 | 2/0/8 |
| LOW_LEVEL | 3 | 3/0/0 | 2/1/0 | 3/0/0 | 0/0/3 |
| TAP_DOMINANT | 3 | 3/0/0 | 2/1/0 | 3/0/0 | 0/0/3 |
| INTERFERENCE | 4 | 2/0/2 | 0/4/0 | 1/3/0 | 0/0/4 |
| PARTIAL | 2 | 2/0/0 | 1/1/0 | 2/0/0 | 0/0/2 |
| DEVICE_VARIATION | 2 | 1/0/1 | 0/2/0 | 1/1/0 | 0/0/2 |

Source: F.body.condition_level_100ms. Row totals equal n for every system and sum to the Table 2 numerator counts.

**Source-level companion panel.** The same count convention applies; these are the ten independence units, not ten further observations.

| Source | Primary n | RhythmAlign v1.2.0 | GCC-PHAT argmax (v2 lagfix) | NCC argmax (unconstrained) | Panako OLAF |
| --- | --- | --- | --- | --- | --- |
| S01 | 3 | 3/0/0 | 0/3/0 | 3/0/0 | 1/0/2 |
| S02 | 3 | 3/0/0 | 3/0/0 | 2/1/0 | 1/0/2 |
| S03 | 2 | 2/0/0 | 2/0/0 | 2/0/0 | 0/0/2 |
| S04 | 2 | 2/0/0 | 1/1/0 | 2/0/0 | 0/0/2 |
| S05 | 2 | 2/0/0 | 1/1/0 | 2/0/0 | 0/0/2 |
| S06 | 2 | 2/0/0 | 2/0/0 | 2/0/0 | 0/0/2 |
| S07 | 2 | 2/0/0 | 0/2/0 | 2/0/0 | 0/0/2 |
| S08 | 2 | 0/0/2 | 0/2/0 | 1/1/0 | 0/0/2 |
| S09 | 3 | 3/0/0 | 0/3/0 | 1/2/0 | 0/0/3 |
| S10 | 3 | 1/0/2 | 1/2/0 | 2/1/0 | 0/0/3 |

Source: F.body.source_level_100ms. On wrong references, each source has the same denominator as its primary n: RhythmAlign and Panako refuse every case; GCC-PHAT and NCC accept every case. The four RhythmAlign positive refusals are final08/final18 (S08) and final20/final24 (S10). S08, S09, and S10 were preflagged repetitive; concentration on S08/S10 is descriptive, not causal.

## Table 5 — Kdenlive technical stratum

Kdenlive 26.08.1; one owner/operator; 10 selected positives across 7 source identities; one editor version; positive-only (no wrong-reference arm); not a usability comparison. The scoped reading: the native command did not reliably recover placement on this selected technical stratum.

| Quantity | Observed value | Denominator / scope |
| --- | --- | --- |
| CORRECT_ACCEPT | 2 | 10 valid positive pairs |
| WRONG_ACCEPT | 8 | 10 valid positive pairs |
| Native failures | 0 | 10 valid positive pairs |
| Timed runs | 9 | 10 valid runs; pair01r2 missing, never imputed |
| Operator-time median | 58.6 s | 9 timed runs |
| Operator-time IQR | 45.1–60.7 s | 9 timed runs |
| Operator-time total | 551.5 s | 9 timed runs |

| Pair | Scoring run | Take | Condition | Outcome at 100 ms | Absolute error (s) | Operator time (s) |
| --- | --- | --- | --- | --- | --- | --- |
| pair01 | pair01r2 | final01 | ORDINARY | WRONG_ACCEPT | 149.415667 | Missing |
| pair02 | pair02 | final02 | ORDINARY | CORRECT_ACCEPT | 0.005250 | 92.465 |
| pair03 | pair03 | final03 | ORDINARY | WRONG_ACCEPT | 1.956479 | 113.147 |
| pair04 | pair04 | final04 | ORDINARY | WRONG_ACCEPT | 17.508750 | 41.009 |
| pair05 | pair05 | final11 | LOW_LEVEL | WRONG_ACCEPT | 149.357229 | 50.635 |
| pair06 | pair06 | final12 | TAP_DOMINANT | WRONG_ACCEPT | 3.365000 | 58.593 |
| pair07 | pair07 | final17 | INTERFERENCE | WRONG_ACCEPT | 2.565500 | 59.219 |
| pair08 | pair08 | final18 | INTERFERENCE | WRONG_ACCEPT | 0.845208 | 60.740 |
| pair09 | pair09 | final21 | PARTIAL | WRONG_ACCEPT | 87.056104 | 45.120 |
| pair10 | pair10 | final23 | DEVICE_VARIATION | CORRECT_ACCEPT | 0.000125 | 30.608 |

Source: V2.body.kdenlive_stratum for summaries; K.body.per_pair for individual errors/times. Counts are identical at 50/100/150 ms. Original pair01 V1 is void evidence only; pair01r2 is its scored replacement under the uniform 180 s headroom procedure. Original failure evidence and the outcome-independent XML correction remain preserved. Pair01r2 timing is missing, not zero, and the void run's time is not substituted. Correct pair02/pair10 errors round to 5.3/0.1 ms; eight wrong errors range from approximately 0.85 to 149.4 s.

## Table 6 — Strict-repeat observations

Only two repeat takes, excluded from primary counts. Absolute output movement is |offset_repeat − offset_original|. Signed error change is (offset_repeat − GT_repeat) − (offset_original − GT_original). Different recording starts change GT; raw movement alone is not repeatability. Dashes mean values not supplied in V2 for Panako's refusal comparisons: the originals were accepted, but no repeat placement or paired timing change exists. The GCC rows' underlying records (final01, final02, repeat01, repeat02) are lag-identical under the v2 lagfix correction, so this table holds unchanged for the valid comparator (asserted by the paper checker).

| Comparison | System | Native states | State agreement | Absolute output movement (s) | Signed error change (ms) | Original absolute error (s) | Repeat absolute error (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| repeat01 vs final01 | RhythmAlign v1.2.0 | ACCEPT → ACCEPT | Yes | 0.5573 | +7.83 | 0.007594 | 0.000231 |
| repeat01 vs final01 | GCC-PHAT argmax (v2 lagfix) | ACCEPT → ACCEPT | Yes | 0.5651 | -0.04 | 61.894792 | 61.894833 |
| repeat01 vs final01 | Panako OLAF | ACCEPT → NO_MATCH | No | — | — | — | — |
| repeat01 vs final01 | NCC argmax (unconstrained) | ACCEPT → ACCEPT | Yes | 0.5624 | +2.71 | 0.001250 | 0.003958 |
| repeat02 vs final02 | RhythmAlign v1.2.0 | ACCEPT → ACCEPT | Yes | 0.1161 | +14.03 | 0.005929 | 0.008096 |
| repeat02 vs final02 | GCC-PHAT argmax (v2 lagfix) | ACCEPT → ACCEPT | Yes | 67.2049 | -67074.81 | 0.000208 | 67.075021 |
| repeat02 vs final02 | Panako OLAF | ACCEPT → NO_MATCH | No | — | — | — | — |
| repeat02 vs final02 | NCC argmax (unconstrained) | ACCEPT → ACCEPT | Yes | 60.4599 | -60329.75 | 60.333667 | 0.003917 |

Source: V2.body.strict_repeats.comparisons. RhythmAlign's +7.8/+14.0 ms figures are changes in signed error, not raw output movement. GCC-PHAT repeat01 is consistently wrong. On repeat02, GCC-PHAT changes correct → wrong and NCC wrong → correct despite ACCEPT → ACCEPT in both cases; their raw movements are approximately 67.2 and 60.5 s. Panako refuses both repeats after accepting their originals. These are observations, not reliability rates.

## Table 7 — Paired outcomes versus RhythmAlign (primary positives, 100 ms)

Frozen per-case discordance counts (F.body.discordant_counts_vs_rhythmalign), reported to prevent reading 20/24 versus 19/24 as broad dominance. Dependent within-source observations; no significance test is performed.

| Comparator | Both correct | Comparator-only correct | RhythmAlign-only correct | Neither |
| --- | --- | --- | --- | --- |
| GCC-PHAT argmax (v2 lagfix) | 10 | 0 | 10 | 4 |
| NCC argmax (unconstrained) | 17 | 2 | 3 | 2 |
| Panako OLAF | 2 | 0 | 18 | 4 |

Wrong-reference pairing over the same 24 constructed pairs:

| Comparator | Both refused/no-match | Comparator wrong-accept only | RhythmAlign wrong-accept only | Both wrong accepts |
| --- | --- | --- | --- | --- |
| GCC-PHAT argmax (v2 lagfix) | 0 | 24 | 0 | 0 |
| NCC argmax (unconstrained) | 0 | 24 | 0 | 0 |
| Panako OLAF | 24 | 0 | 0 | 0 |

**NCC overlap contract panel.** The five NCC wrong positives occur at usable overlaps of 1.675 s (final02), 1.234 s (final18), 3.589 s (final19), 3.522 s (final20), 4.694 s (final23) — approximately 1.2–4.7 s — all below RhythmAlign's 30 s minimum-overlap threshold, while all 19 NCC correct positives sit at 60.414 s or more; the 30 s line falls in the empty middle. RhythmAlign's edge-lag guard alone excludes all five placements. Because a 30 s-constrained NCC was not evaluated, this observation does not determine the counterfactual performance of a matched NCC system. Source: NCC_OVERLAP_CONTRACT_AUDIT.md; recomputed by the paper checker from frozen NCC lag_samples and correction-manifest lengths (pinned by tests/test_comparator_integrity_audit.py).
