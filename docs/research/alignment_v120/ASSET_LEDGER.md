# ASSET LEDGER — alignment research assets relative to RhythmAlign v1.2.0

Purpose: classify every meaningful asset produced by the previous alignment
research so that future v1.2.0 research can reuse what is safe and cannot
accidentally present old measurements as v1.2.0 evidence or as independent
confirmation.

Research target (frozen subject): tag `v1.2.0` = commit
`3a622fc33af1212178296ad9dad57ce9693eed48` (on `main`; `main` HEAD
`91bc50c0a117b38176ec93b44b9e0d1b8aaf749d` is the post-tag release-record
docs commit). Pre-v1.2.0 research assets live on the local-only branch
`astra/alignment-research-wip` (final research commit
`8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e`).

## Classification rule

Exactly one **primary** category per asset; strictest applicable wins.

- **A. REUSE** — may be safely reused in future v1.2.0 research. Reuse does
  NOT turn old measurements into v1.2.0 measurements.
- **B. DISCOVERY_ONLY** — exploratory / hypothesis-generation evidence; explains
  how a weakness was found; never confirmatory for the final v1.2.0 method.
- **C. SUPERSEDED** — conclusions describe a system state that no longer exists
  in v1.2.0; preserved historically, never cited as current behavior.
- **D. INVALID_FOR_CONFIRMATION** — data that influenced the design/tuning of
  the temporal-support safeguard (or was consumed as development/validation
  evaluation), and therefore must NEVER be presented as independent
  confirmation that the safeguard generalizes.

Standing nuance: an artifact can be reusable as tooling while its DATA is
invalid for confirmation; where that applies the row records it explicitly.
"Pre/post blocker" is relative to the Astra blocker discovery (first accepted
room-grid mismatch, mid-study; the WIP commit `5b1fcd4` predates it).

---

## 0. Frozen subject anchors (reference rows — the research subject, not classified)

| Path (at `3a622fc`) | Role |
|---|---|
| `alignment_engine_v2.py` | Engine v2 default engine; contains `DecisionPolicy.bin_width_s = 1.0`, `max_top_bin_share = 0.25`, `_apply_temporal_support`, reason codes `ABSTAIN_CONCENTRATED_EVIDENCE` / `ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT` (verified in tag source, lines ~167/705–760) |
| `auto_sync.py` | Product worker; consumes ACCEPT and exports; ABSTAIN stops; no v1 fallback |
| `ui_main.py`, `locales/*.json` | ACCEPT/ABSTAIN presentation incl. abstention reason strings |
| `tests/test_ra12d1_temporal_support.py` | 11 temporal-support regression tests (introduced `67c8cbd`; full suite 80 passed at RC2 per RA-1.2E) |

## 1. Astra exploratory study — branch-only assets (`astra/alignment-research-wip` @ `8b78eb1`)

None of these files exist on `main` or at `v1.2.0`. All measurements describe
the pre-v1.2.0 system at scientific baseline `ffa6b07a591dbdb54ae8350f3d27dce3ed74c847`
(Engine v2 non-default), plus a read-only relevance check against `20d4816` (RA-1.2D).

| # | Path | Provenance | Type | Phase | Quant. evidence | Primary | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `docs/research/alignment/ALIGNMENT_RESEARCH_STUDY.md` | `8b78eb1` | report | post-blocker | YES | **B. DISCOVERY_ONLY** | The discovery record of the concentrated-evidence wrong-song failure. All numbers are ffa6b07-era. §12.4 `RELEASE_BLOCKER_FOUND` recommendation and "do not clear RA-1.2D for release" are **C. SUPERSEDED** sub-claims (resolved by RA-1.2D1/1.2E); its `ENGINEERING_ONLY` verdict is a pre-v1.2.0 judgment, not a v1.2.0 verdict. |
| 2 | `docs/research/alignment/EXPERIMENT_PLAN.md` | `5b1fcd4` (amended `8b78eb1`) | report | pre-blocker (amended post) | YES | **A. REUSE** | Protocol/metric/GT-strata definitions are system-independent. Its "historical holdout" naming must never be read as a fresh test set (see DATA_PROVENANCE). |
| 3 | `docs/research/alignment/LITERATURE_REVIEW.md` | `8b78eb1` | report | post-blocker | no | **A. REUSE** | System-independent bibliography + novelty-boundary mapping (Duong 2012; Six & Leman 2015; fingerprint/DTW/PCEN/HPSS/selective-prediction literature). Directly reusable for future review. |
| 4 | `experiments/alignment_research/study.py` | `5b1fcd4` (amended `8b78eb1`) | code | pre (amended post) | no | **A. REUSE** | Corpus builder/auditor/replay harness. The corpus DATA it produced is development data (see row 12). |
| 5 | `experiments/alignment_research/analyze.py` | `8b78eb1` | code | post-blocker | no | **A. REUSE** | Aggregation/tables/AUC/figures builder. |
| 6 | `experiments/alignment_research/probes.py` | `8b78eb1` | code | post-blocker | no | **A. REUSE** | Nulls, partial-support, repetition, decision-seam probe generators. |
| 7 | `experiments/alignment_research/mismatch_search.py` | `8b78eb1` | code | post-blocker | no | **A. REUSE** | Exhaustive room-grid runner (551 pairs). |
| 8 | `experiments/alignment_research/clean_mismatch_search.py` | `8b78eb1` | code | post-blocker | no | **A. REUSE** | Directed clean-grid runner (380 pairs). Its OUTPUT is category D (row 15). |
| 9 | `experiments/alignment_research/investigate_counterexample.py` | `8b78eb1` | code | post-blocker | no | **A. REUSE** | Counterexample repetition/attribution/intervention/ablation runner. Its OUTPUT is category D (row 16). |
| 10 | `experiments/alignment_research/verify.py` | `8b78eb1` | code | post-blocker | no | **A. REUSE** | Verification-record builder (AST equality, hashes, suite runner). |
| 11 | `experiments/alignment_research/results/corpus.json` | `5b1fcd4` | data | pre-blocker | YES | **D. INVALID_FOR_CONFIRMATION** | The 81-case preserved corpus (56 exact-GT positives, 20 wrong-song, 4 tiled, 1 manual anchor). Development corpus: informed Engine v2 A/B/C thresholds and was consulted throughout; reusable only as a regression-replay fixture, never as fresh confirmation. |
| 12 | `experiments/alignment_research/results/audit.json` | `5b1fcd4` | data | pre-blocker | YES | **A. REUSE** | Source-exposure/contamination audit (20 projects / 29 recordings; holdout exposure). Provenance metadata; feeds DATA_PROVENANCE. |
| 13 | `experiments/alignment_research/results/analysis.json` | `8b78eb1` | data | post-blocker | YES | **B. DISCOVERY_ONLY** | N=76 replay + baselines (v1 29/47/0; frozen v2 26/0/50; GCC-PHAT 56/56 positives), AUCs, nulls, grid summaries. All ffa6b07-era measurements. |
| 14 | `experiments/alignment_research/results/mismatch_search.json` | `8b78eb1` | data | post-blocker | YES | **B. DISCOVERY_ONLY** | 551 room-grid: 1 accept (`haiditan_ds_1` × `tr_hongzhoutian`, +59.7217 s). That accepted pair later became a RA-1.2D1 TEST row and the documented residual — for that specific case, see D-flag in DATA_PROVENANCE. |
| 15 | `experiments/alignment_research/results/clean_mismatch_search.json` | `8b78eb1` | data | post-blocker | YES | **D. INVALID_FOR_CONFIRMATION** | 380 directed clean pairs, 22 accepted / 11 unordered pairs (verified from rows). 18 component-A accepts (incl. the blocker) were the DEV data that chose `max_top_bin_share = 0.25`; the 4 component-B accepts were RA-1.2D1's held-out TEST; the file has since been re-inspected/re-run post-D1. The search event itself is also the B-category discovery of the wrong-song failure; the D label protects against confirmatory misuse. |
| 16 | `experiments/alignment_research/results/counterexample_validation.json` | `8b78eb1` | data | post-blocker | YES | **D. INVALID_FOR_CONFIRMATION** | Blocker pair `tr_lingduihua` → `tr_yanwulieche`: repeatable ACCEPT +1.4628571 s, PCEN Z 13.109 / margin 2.483, onset Z 2.012, overlap 148.57 s; plain-PCEN top-1 s bin share 0.945630 (verified from `contributions`), HPSS 0.701277; 5 s boundary masks/crops → ABSTAIN; single-method removals. This is the mechanism-identification evidence the safeguard was built from. |
| 17 | `experiments/alignment_research/results/safeguards.json` | `8b78eb1` | data | post-blocker | YES | **B. DISCOVERY_ONLY** | Partial-support (1/3 s abstain; 8/20/40 s accept) and repetition falsifications; refuted the "raise Z / margin" fix directions later re-confirmed in RA-1.2D1. |
| 18 | `experiments/alignment_research/results/feature_nulls.json` | `8b78eb1` | data | post-blocker | YES | **B. DISCOVERY_ONLY** | 384 synthetic feature-space null draws (search-length effect). |
| 19 | `experiments/alignment_research/results/audio_nulls.json` | `8b78eb1` | data | post-blocker | YES | **B. DISCOVERY_ONLY** | 36 audio nulls; all abstain; max method Z ≈ 6.65. |
| 20 | `experiments/alignment_research/results/curve_counterexamples.json` | `8b78eb1` | data | post-blocker | YES | **B. DISCOVERY_ONLY** | Synthetic decision-seam constructions (clustering/output-seam contract gap). |
| 21 | `experiments/alignment_research/results/verification.json` | `8b78eb1` | data | post-blocker | YES | **A. REUSE** | Provenance record: AST equality of engine code between `ffa6b07` and `20d4816` (excluding docstrings/`ENGINE_LABEL`/ETA factor), input hashes, 48-test suite. Valid provenance evidence for the Stage 2→3 chain. |
| 22 | `experiments/alignment_research/results/null_and_counterexample.png` | `8b78eb1` | figure | post-blocker | YES | **B. DISCOVERY_ONLY** | Null search-length + pre-D1 concentration figure. |
| 23 | `experiments/alignment_research/results/risk_coverage.png` | `8b78eb1` | figure | post-blocker | YES | **B. DISCOVERY_ONLY** | Pre-D1 risk-coverage figure (ffa6b07-era operating point). |

## 2. RA-1.2x engineering reports (on `main` and at `v1.2.0`)

| # | Path (at `3a622fc`) | Provenance | Type | Phase | Quant. evidence | Primary | Notes |
|---|---|---|---|---|---|---|---|
| 24 | `docs/RA-1.2A-LOW-SNR-ALIGNMENT.md` | `c036a1c` | report | pre-study | YES | **B. DISCOVERY_ONLY** | Discovery of the 零对话 low-SNR failure of the v1.1.x hybrid (−1.997 s vs manual +12.4±0.4 s); spike, no production change. Development-phase measurements. |
| 25 | `docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md` | `c8bbcd9` | report | pre-study | YES | **B. DISCOVERY_ONLY** | Engine v2 design + first calibration, non-default; `NEEDS_MORE_REAL_DATA`. Development measurements (29/29 real-positive ACCEPT = acceptance, not verified accuracy). |
| 26 | `docs/RA-1.2C-CALIBRATION-HARDENING.md` | `ffa6b07` | report | pre-study | YES | **B. DISCOVERY_ONLY** | Calibration hardening; still non-default; `READY_FOR_RA12D`. All thresholds here are development-chosen; the Astra scientific baseline `ffa6b07` is this state. |
| 27 | `docs/RA-1.2D-DEFAULT-INTEGRATION.md` | `20d4816` | report | post-blocker (blocker-unaware) | YES | **B. DISCOVERY_ONLY** | Engine v2 default-path integration + abstention UX. Also the provenance record of how the paused Astra WIP was preserved onto `astra/alignment-research-wip` (owner-approved pre-flight). |
| 28 | `docs/RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md` | `67c8cbd` | report | post-blocker | YES | **A. REUSE** | Authoritative derivation record of the temporal-support safeguard (design space incl. 4 measured rejections; DEV/TEST split; 0.25 calibration; held-out results; residual case). Describes the engine state that v1.2.0 froze (RA-1.2E verified zero algorithm diff after D1). Its §5/§6 DEV tables are D-category data (see §4 below); §7 held-out rows are spent-holdout evidence. |
| 29 | `docs/RA-1.2E-V1.2.0-RELEASE.md` | `e354d6b` (final record `91bc50c`) | report | post-blocker | YES | **A. REUSE** | Release record: frozen-state RC regression re-runs (§9: 76→80 tests, blocker abstains, 55/55 positives, 156/156 held-out abstain, 24/24 safety families, residual unchanged), owner gates, and Appendix A = verbatim release notes carrier. Product record, not research evidence. Also documents the RA-1.2E GT-population correction (0.0923 s is a manual-interval deviation, not exact-GT error). |

## 3. RA-1.2A/B/C/D experiment package (`experiments/low_snr_alignment/`, on all three refs)

Trivial infrastructure (`__init__.py`) not classified. All result JSONs are
development-era data for Engine v2: they can never be presented as independent
confirmation of v1.2.0.

| # | Path | Provenance | Type | Phase | Quant. | Primary | Notes |
|---|---|---|---|---|---|---|---|
| 30 | `README.md` | `c036a1c` | report | pre-study | no | **A. REUSE** | Package usage documentation. |
| 31 | `harness.py` | `c036a1c` | code | pre-study | no | **A. REUSE** | Experiment harness (decode, features, evaluation). |
| 32 | `run_experiment.py` | `c036a1c` | code | pre-study | no | **A. REUSE** | Runner for synthetic/semi-synthetic suites. |
| 33 | `synthetic_eval.py` | `c036a1c` | code | pre-study | no | **A. REUSE** | Synthetic evaluation. |
| 34 | `failure_analysis.py` | `c036a1c` | code | pre-study | no | **A. REUSE** | Failure analysis tooling. |
| 35 | `pcen_sweep.py` | `c036a1c` | code | pre-study | YES | **A. REUSE** | 36-config PCEN sweep tooling. Its REAL_OFFSET=12.4227 is prediction-derived, not an independent label (Astra §7.3). |
| 36 | `calibrate_nulls.py` | `c8bbcd9` | code | pre-study | YES | **A. REUSE** | Null calibration tooling. |
| 37 | `real_corpus_eval.py` | `c8bbcd9` | code | pre-study | YES | **A. REUSE** | Real-corpus runner. Data it produced is D (rows 49–51). |
| 38 | `engine_v2_owner_test.py` | `c8bbcd9` | code | pre-study | no | **A. REUSE** | Owner-facing engine smoke. |
| 39 | `product_smoke.py` | `20d4816` | code | post-blocker | no | **A. REUSE** | Real-SyncWorker product-path smoke; re-used at RC. |
| 40 | `blocker_product_smoke.py` | `e354d6b` | code | post-blocker | no | **A. REUSE** | v1.2.0 blocker product smoke (ABSTAIN, no export, no v1 fallback). |
| 41 | `semi_synthetic.py` | `ffa6b07` | code | pre-study | no | **A. REUSE** | Corruption-package constructor (L1–L4 confound noise+processing by design). |
| 42 | `semi_synthetic_eval.py` | `ffa6b07` | code | pre-study | no | **A. REUSE** | Semi-synthetic evaluation. |
| 43 | `semi_synthetic_plan.json` | `ffa6b07` | data | pre-study | no | **A. REUSE** | Plan/spec for the semi-synthetic corpus. |
| 44 | `soak_test.py` | `ffa6b07` | code | pre-study | no | **A. REUSE** | Repeated-invocation soak tooling. |
| 45 | `memory_scaling.py` | `ffa6b07` | code | pre-study | no | **A. REUSE** | Memory-scaling tooling. |
| 46 | `local_corpus.example.json` | `c8bbcd9` | data | pre-study | no | **A. REUSE** | Manifest example (path-free IDs + hashes). |
| 47 | `results/synthetic_run.json`, `results/synthetic_run_ra12b.json`, `results/run_baseline.json`, `results/run_final.json`, `results/failure_analysis.json` | `c036a1c` | data | pre-study | YES | **B. DISCOVERY_ONLY** | RA-1.2A/B-era development measurements (synthetic runs, failure analysis). |
| 48 | `results/null_calibration_n30.json` | `c8bbcd9` | data | pre-study | YES | **B. DISCOVERY_ONLY** | Mathematical null calibration (N=30). |
| 49 | `results/real_corpus_ra12b.json`, `results/real_corpus_ra12c.json`, `results/real_corpus_ra12d_default.json` | `c8bbcd9` / `ffa6b07` / `20d4816` | data | pre/post | YES | **D. INVALID_FOR_CONFIRMATION** | The 29 real positives across engine states. v1–v2 agreement/consistency data; the same positives are RA-1.2D1 positive DEV (preservation targets). Not correctness evidence. |
| 50 | `results/real_corpus_mismatch.json` | `c8bbcd9` | data | pre-study | YES | **D. INVALID_FOR_CONFIRMATION** | 10 ordinary wrong-song mismatches; reused as a RA-1.2D1 safety family (all SAFE_ABSTAIN). Development negatives. |
| 51 | `results/hard_negative_search_ra12c.json` | `ffa6b07` | data | pre-study | YES | **D. INVALID_FOR_CONFIRMATION** | Feature-similar hard negatives (+ tiled set in rows 52/53); RA-1.2D1 safety family. Development-selected ("onset density" = onset-strength summary; not a worst-case search — Astra §7.2). |
| 52 | `results/semi_synthetic_calibration_ra12c.json`, `results/semi_synthetic_calibration_ra12d_default.json` | `ffa6b07` / `20d4816` | data | pre/post | YES | **D. INVALID_FOR_CONFIRMATION** | 36 calibration-split exact-GT positives; calibration split entered RA-1.2D1 positive DEV. |
| 53 | `results/semi_synthetic_holdout_ra12c.json`, `results/semi_synthetic_holdout_ra12d_default.json` | `ffa6b07` / `20d4816` | data | pre/post | YES | **D. INVALID_FOR_CONFIRMATION** | 20 holdout-split exact-GT positives. Spent historical holdout: used as RA-1.2D1 positive TEST and re-run at RC. Historically valid evidence of the released state; NOT eligible as fresh confirmation. |
| 54 | `results/memory_scaling_ra12c.json`, `results/soak_synthetic_ra12c.json`, `results/soak_realfile_ra12c.json`, `results/soak_benchmark_repro_ra12c.json` | `ffa6b07` | data | pre-study | YES | **C. SUPERSEDED** | Performance/stability records of the pre-D1 non-default engine state (no longer exists; D1 added the support gate). Methodology reusable. |

## 4. RA-1.2D1 evidence package (`experiments/ra12d1_temporal_support/`, on `main`/`v1.2.0`, introduced `67c8cbd`)

All measured on the D1 engine state = the state v1.2.0 froze (RA-1.2E re-verified
outcomes at the RC). Scripts are reusable; result data is development- or
validation-consumed and cannot serve as fresh independent confirmation.

| # | Path | Type | Quant. | Primary | Notes |
|---|---|---|---|---|---|
| 55 | `DESIGN_NOTES.md` | report | YES | **A. REUSE** | Design-space record incl. 4 measured rejections (windowed dominance; windowed consistency; stationary texture; LORO). Methodologically reusable. |
| 56 | `reproduce_blocker.py`, `common.py`, `temporal_support.py`, `calibrate_dev.py`, `evaluate.py`, `prepare.py`, `validate_integration.py`, `validate_full_positives.py` | code | no | **A. REUSE** | Reproduction + calibration + evaluation tooling; runnable against v1.2.0. |
| 57 | `results/blocker_reproduction.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | Third independent reproduction of the blocker (+1.4628571 s, CASE B) on unmodified `20d4816`. Mechanism-identification data. |
| 58 | `results/dev_calibration_analysis.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | Measured rejection of the v1 (windowed-dominance) design on DEV. |
| 59 | `results/dev_concentration.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | 107 rows: 42 component-A wrong-song pairs (18 v2-accepted; decider concentration 0.480–1.048), 29 real + 17 calibration-split positives (true-accept decider range 0.014–0.108). This is the threshold-selection dataset. |
| 60 | `results/chosen_policy.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | Records bin 1.0 s / `max_top_share` 0.25, DEV outcome 18/18 + 46/46, provenance statement. |
| 61 | `results/eval_wrong_song_test.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | 158 rows = 156 held-out clean wrong-song pairs (all SAFE_ABSTAIN incl. the 4 known component-B accepts) + archived blocker (abstained, concentration 0.9456) + room-grid archived accept (still accepted). Spent historical holdout: the strongest existing negative evidence for v1.2.0, consumed by D1 validation and re-run at RC; never again fresh confirmation. |
| 62 | `results/eval_negatives.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | 24 development negatives post-gate (10 RA-1.2B mismatches + 10 hard negatives + 4 tiled): all SAFE_ABSTAIN. |
| 63 | `results/eval_positives.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | Positive-side gate evaluation on development populations. |
| 64 | `results/eval_baselines.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | GCC-PHAT/NCC baseline runs on the same corpus. Verified counts: GCC-PHAT 57/57 **GT-bearing** positives within tolerance (56/56 semi-synthetic + 零对话 vs manual ±0.4 s; error 0.0886 s vs interval center), NCC 54/57; 28 real positives are GT-less (`within_tol: null`) — engine-agreement only; wrong-song argmax peaks 0.004–0.031 with meaningless placements. Citable as historical baseline evidence; not fresh confirmation. |
| 65 | `results/integrated_validation.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | Post-gate blocker row (`ABSTAIN_CONCENTRATED_EVIDENCE`, top-bin share 0.9456, 149 bins) + real positive row (decider PCEN+HPSS share 0.0836, 39.5 effective bins). |
| 66 | `results/integrated_full_positives.json` | data | YES | **D. INVALID_FOR_CONFIRMATION** | 85 positives through the integrated engine: 55 CORRECT_ACCEPT / 30 SAFE_ABSTAIN / 0 WRONG_ACCEPT; max exact-GT error 0.0137 s; manual-GT row for 零对话 separated (RA-1.2E-corrected summary fields). |
| 67 | `results/equivalence_check.json` | data | YES | **A. REUSE** | Feature-reuse equivalence proof (bit-identical curves from cached features). Infrastructure evidence. |

## 5. Tests and local-only artifacts

| # | Path | Provenance | Type | Primary | Notes |
|---|---|---|---|---|---|
| 68 | `tests/test_ra12d1_temporal_support.py` | `67c8cbd` | code | **A. REUSE** | 11 mechanism/regression tests incl. the causal A/B proof (`max_top_bin_share = 1.01` accepts what 0.25 rejects). |
| 69 | `release_notes_v1.2.0.md` (repo root) | untracked local file, in NO commit on ANY ref | report | not a Git asset | Local release-notes carrier per RELEASE.md rules; reviewed content preserved verbatim in RA-1.2E Appendix A. Present untracked at consolidation start; absent from the working tree at commit time (external change mid-session; recorded in the consolidation report). Never classified, never committed by this task. |

## Counts (primary categories, rows 1–68; row 69 is a local-only artifact, not classified)

68 classification rows cover 86 files (six rows are explicit file groups).

- **A. REUSE**: 34 rows (41 files) — literature/protocol docs, all experiment
  tooling, the source-exposure audit, verification/equivalence records, D1
  derivation + release records, regression tests.
- **B. DISCOVERY_ONLY**: 15 rows (19 files) — the study report, aggregate
  pre-D1 measurements, probe/null results, figures, RA-1.2A/B/C/D reports,
  early synthetic-run data.
- **C. SUPERSEDED**: 1 row (4 files) — pre-D1 soak/memory performance records.
- **D. INVALID_FOR_CONFIRMATION**: 18 rows (22 files) — the preserved
  development corpus, clean-grid/counterexample data, all DEV calibration
  data, all D1 consumed-validation result JSONs, real-corpus agreement runs,
  hard negatives, semi-synthetic cal+holdout results.

Grouped rows count as one ledger row but may cover several files; per-file
membership is explicit in each row.

## Discrepancies and verification notes found during consolidation

1. `docs/research/alignment/PAPER_OUTLINE.md` (named in the consolidation
   task's expected inventory) **does not exist** on `astra/alignment-research-wip`
   and never did: the study explicitly declined to propose framings (study §16).
   Not a loss — an expected-file mismatch.
2. RA-1.2D1 §10 states GCC-PHAT "57/57" / NCC "54/57"; `eval_baselines.json`
   confirms this over the 57 **GT-bearing** positive rows (85 positive rows
   total; 28 real positives have no GT and carry `within_tol: null`). The doc's
   denominator is the GT-bearing subset — consistent once read precisely; the
   FACT_SHEET states the population split explicitly.
3. RA-1.2E already corrected RA-1.2D1's mixed GT populations (0.0923 s
   deviation vs 0.0137 s exact-GT max). The corrected values were re-verified
   from `integrated_full_positives.json` raw rows during consolidation.
4. The study's committed `corpus.json`/`audit.json` were produced before the
   WIP pause and never regenerated on resume (study §8) — consistent with the
   diff record (`5b1fcd4` introduced them; `8b78eb1` did not modify them).
5. Working-tree observation: the untracked `release_notes_v1.2.0.md` seen at
   consolidation start was no longer present when the research branch was
   created (no consolidation command touched it; external change). Content
   remains recoverable verbatim from RA-1.2E Appendix A.
