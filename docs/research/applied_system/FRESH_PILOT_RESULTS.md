# Fresh Acoustic Pilot Results

## 1. Status and Non-Evidence Warning

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** These development-pilot counts may never be presented as final confirmatory performance evidence.

- Verdict: `PILOT_PASS_PROTOCOL_FREEZE_READY`
- Measurement-freeze semantic hash: `20dbc530c9dffba14a4e51b6773ab8efbf1db1681f597babfd47e7ba6ab039cd`
- Measurement-freeze file SHA-256: `49f296ec3c8d58bbd1b05f403079c7268f3bc18679620a2ccc2579eeb50bd125`
- Transparent tooling correction: `1dbadb48c2e009e1f4b8767962e8d3074f0b3722a2db3022959b988942056028` — the omitted direct-correlation diagnostic was added after comparator execution without changing the original freeze or any outcome; 12/12 cross-checks passed.

## 2. Raw Recording Provenance

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Originals were hashed before/after automated decode and remained byte-identical.

| Take | Original | SHA-256 | Container | Codec | Hz | Channels | Duration s | Bytes |
|---|---|---|---|---|---|---|---|---|
| take01 | take01.m4a | 08da59ed4abe73df4468ebc88bdaca5032c47ecab4b2ebf6f678efd9c3658d8f | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.032 | 1109171 |
| take02 | take02.m4a | 5cff3d0338ee0bca4afacf3c60526c1ab73a1e647cc66344f3ac2b87e9254a33 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.459 | 1116060 |
| take03 | take03.m4a | a52ef6ef5301db67641de45ab8daa06c61ec046d28da03111fe0cab1212e673d | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.288 | 1113360 |
| take04 | take04.m4a | af68dbe8f50c73f55b63328b99c1590b60c495a38a879a327b37613a30261308 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.437 | 1115753 |
| take05 | take05.m4a | 1494efece25f15ab4882791e7ed7ec9aee0b33e97a6d99cea5efefbc4145a79d | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.477 | 1100109 |
| take06 | take06.m4a | 1f9b13e10e04aae589801f8a27d4c9a24a9e186f0503397e61dfa012f9401304 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 69.824 | 1138331 |
| take07 | take07.m4a | 611de34cce256e348c1c72f2b58978d89bb450e574babfc2409f47936ff68dbb | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.843 | 1122331 |
| take08 | take08.m4a | 41d9063d9e4cad6dd4a4b53e9a3ea13b0f0a66be1d04db2a040ff887bc878e47 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 72.640 | 1184150 |
| take09 | take09.aac | 89ff32b6d3968f05aaf73143d3f666c1afe671627634ff1ef5ec7bf75a29dd3e | aac | aac | 48000 | 2 | 68.075 | 839792 |
| take10 | take10.aac | 14abe9228afb7001dbbec050b9f4b8b5e90b7de8760c59f05f9cbbd75f06a098 | aac | aac | 48000 | 2 | 67.456 | 832202 |
| take11 | take11.aac | 77cfb151f33601cd755a8f8e40348fb472f47b0f274ce353bdd5a7a25ba2694c | aac | aac | 48000 | 2 | 66.667 | 822451 |
| take12 | take12.aac | 97e28c2b58806580dc7c9ad18ae81e998f7f04f14ca4649ef97e7acf4ae76e64 | aac | aac | 48000 | 2 | 66.347 | 818506 |

## 3. Device / Take Mapping

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Mapping comes only from the frozen take plan.

| Take | Device | Playback | Buffer | Condition |
|---|---|---|---|---|
| take01 | D1 | P1 | BUF-A | ordinary |
| take02 | D1 | P1 | BUF-A | ordinary_repeat_strict_pair_of_take01 |
| take03 | D1 | P1 | BUF-BMID | ordinary_mid_song_placement |
| take04 | D1 | P1 | BUF-A | low_playback_volume |
| take05 | D1 | P1 | BUF-BMID | desk_taps_during_music |
| take06 | D2 | P1 | BUF-A | ordinary |
| take07 | D2 | P1 | BUF-A | ordinary_repeat_strict_pair_of_take06 |
| take08 | D2 | P1 | BUF-A | background_interference_second_device |
| take09 | D3 | P1 | BUF-A | ordinary |
| take10 | D3 | P1 | BUF-A | low_playback_volume |
| take11 | D3 | P2 | BUF-A | phone_speaker_playback |
| take12 | D3 | P1 | BUF-B1 | ordinary_difficult_song |

## 4. Marker Confidence by Device

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Genuine values come from ungated full-overlap diagnostics; provisional 0.15 did not censor calibration.

| Take | Device | Pre G | Post G | Frozen candidate count |
|---|---|---|---|---|
| take01 | D1 | 0.304834 | 0.229883 | 2 |
| take02 | D1 | 0.236911 | 0.345578 | 2 |
| take03 | D1 | 0.258466 | 0.239545 | 2 |
| take04 | D1 | 0.286647 | 0.280863 | 2 |
| take05 | D1 | 0.246772 | 0.393852 | 2 |
| take06 | D2 | 0.268525 | 0.287943 | 2 |
| take07 | D2 | 0.244161 | 0.271278 | 2 |
| take08 | D2 | 0.308473 | 0.298954 | 2 |
| take09 | D3 | 0.231427 | 0.391448 | 2 |
| take10 | D3 | 0.284448 | 0.225580 | 2 |
| take11 | D3 | 0.490950 | 0.541559 | 2 |
| take12 | D3 | 0.263177 | 0.269706 | 2 |

- D1: G=0.229883, B=0.028656, G/B=8.022, drift range [-33.201, 28.220] ppm
- D2: G=0.244161, B=0.049581, G/B=4.924, drift range [26.228, 42.829] ppm
- D3: G=0.225580, B=0.032072, G/B=7.034, drift range [-4.980, 30.544] ppm

## 5. Competing Peak Diagnostics

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** B is the maximum of the strongest non-marker full-overlap peak and the exact post-trim leakage rescan.

| Take | Raw competitor | Trim rescan max | Take B |
|---|---|---|---|
| take01 | 0.024972 | 0.024970 | 0.024972 |
| take02 | 0.028656 | 0.028649 | 0.028656 |
| take03 | 0.026361 | 0.026350 | 0.026361 |
| take04 | 0.023055 | 0.023055 | 0.023055 |
| take05 | 0.025818 | 0.025825 | 0.025825 |
| take06 | 0.049571 | 0.049581 | 0.049581 |
| take07 | 0.039925 | 0.039905 | 0.039925 |
| take08 | 0.030153 | 0.030154 | 0.030154 |
| take09 | 0.026984 | 0.026984 | 0.026984 |
| take10 | 0.025665 | 0.025666 | 0.025666 |
| take11 | 0.031993 | 0.032072 | 0.032072 |
| take12 | 0.025599 | 0.025599 | 0.025599 |

## 6. Frozen Marker Rule

- Exact authoritative formula applied: `T_low = 3 × B`; `T_high = 0.8 × G`; feasibility iff `G/B ≥ 3.75`; `T = sqrt(T_low × T_high)`.
- Pooled G: `0.225580061`
- Pooled B: `0.049581107`
- Band: `[0.148743322, 0.180464049]`
- Frozen threshold (exact): `0.163837792269`; documentation only: `0.16`
- Trajectory: `TRAJECTORY_GATE_FROZEN_OFF` because all-genuine=False and any-non-marker=False.

## 7. Clock Drift by Device

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** No take was resampled or time-warped before drift measurement.

| Take | Device | Drift ppm | Clock scale | Mapping disagreement ms |
|---|---|---|---|---|
| take01 | D1 | 28.220452 | 1.000028220 | 0.000000 |
| take02 | D1 | -4.980080 | 0.999995020 | 0.000000 |
| take03 | D1 | -33.200531 | 0.999966799 | 0.000000 |
| take04 | D1 | -25.564409 | 0.999974436 | 0.000000 |
| take05 | D1 | -5.644090 | 0.999994356 | 0.000000 |
| take06 | D2 | 26.892430 | 1.000026892 | 0.000000 |
| take07 | D2 | 42.828685 | 1.000042829 | 0.000000 |
| take08 | D2 | 26.228420 | 1.000026228 | 0.000000 |
| take09 | D3 | -4.980080 | 0.999995020 | 0.000000 |
| take10 | D3 | 30.544489 | 1.000030544 | 0.000000 |
| take11 | D3 | -1.328021 | 0.999998672 | 0.000000 |
| take12 | D3 | 1.328021 | 1.000001328 | 0.000000 |

## 8. Frozen Drift Rule

- Exact authoritative formula applied: `T_drift = max(3 × D_max, 111 ppm)`, with `T_drift ≤ 1000 ppm`.
- Worst observed |ppm|: `42.828685`
- 3 × D_max: `128.486056` ppm
- Frozen tolerance: `128.486056` ppm
- Cap reached: `NO`

## 9. Repeatability

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Protocol-calibration repeat pairs only.

| Pair | Pre conf Δ | Post conf Δ | Drift Δ ppm | GT offset Δ ms | Both GT valid |
|---|---|---|---|---|---|
| take01 + take02 | 0.067923 | 0.115695 | 33.200531 | 41.021 | True |
| take06 + take07 | 0.024365 | 0.016665 | 15.936255 | 1298.667 | True |

## 10. GT Success / Failure

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** GT_FAILED is a protocol outcome, never alignment success/failure.

| Take | GT status | Reason | Reference GT offset s | Direct check Δ ms |
|---|---|---|---|---|
| take01 | GT_VALID | — | +2.991396 | +2.792 |
| take02 | GT_VALID | — | +3.032417 | +2.333 |
| take03 | GT_VALID | — | -87.025875 | -4.437 |
| take04 | GT_VALID | — | +3.205396 | -0.188 |
| take05 | GT_VALID | — | -86.985438 | +3.125 |
| take06 | GT_VALID | — | +4.713125 | +0.354 |
| take07 | GT_VALID | — | +3.414458 | +0.354 |
| take08 | GT_VALID | — | +5.929312 | +1.667 |
| take09 | GT_VALID | — | +2.632271 | +3.438 |
| take10 | GT_VALID | — | +2.528896 | +3.125 |
| take11 | GT_VALID | — | +1.731333 | +3.333 |
| take12 | GT_VALID | — | +1.772625 | -0.458 |

GT_VALID: **12 / 12**.

## 11. Frozen Wrong-Reference Pairings

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Semantic/selectivity pilot only; N=12 is not rate-estimation evidence. Pairing hash: `4aeb8c73f040c1dc43206cd123b69fb67fb21ba50108350fb2e757a7f71921c6`.

| Take | Source buffer | Frozen wrong reference |
|---|---|---|
| take01 | BUF-A | REF-B |
| take02 | BUF-A | REF-B |
| take03 | BUF-BMID | REF-A |
| take04 | BUF-A | REF-B |
| take05 | BUF-BMID | REF-A |
| take06 | BUF-A | REF-B |
| take07 | BUF-A | REF-B |
| take08 | BUF-A | REF-B |
| take09 | BUF-A | REF-B |
| take10 | BUF-A | REF-B |
| take11 | BUF-A | REF-B |
| take12 | BUF-B1 | REF-A |

## 12. Comparator Pilot Outcomes

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Raw development-pilot counts only; no paper-level rates or claims.

| System | Positive raw counts | Wrong-reference raw counts |
|---|---|---|
| rhythmalign_v1_2_0 | CORRECT_ACCEPT=12 | SAFE_ABSTAIN=12 |
| gcc_phat_argmax_v1 | CORRECT_ACCEPT=3, WRONG_ACCEPT=9 | WRONG_ACCEPT=12 |
| panako_fingerprint | CORRECT_ACCEPT=9, SAFE_ABSTAIN=3 | SAFE_ABSTAIN=12 |
| ncc_argmax_v1 | CORRECT_ACCEPT=6, WRONG_ACCEPT=6 | WRONG_ACCEPT=12 |

## 13. Panako Role Decision

Pre-declared rule: median positive |offset error| ≤100 ms → placement role. Observed pilot median: `0.0015416666666663303` s. Frozen role: **PLACEMENT_COMPARATOR**.

## 14. Pilot Success Criteria

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Criteria are protocol gates, not paper-performance claims.

| Criterion | Result |
|---|---|
| 1_gt_survival | PASS |
| 2_confidence_feasibility | PASS |
| 3_trajectory_policy_decidable | PASS |
| 4_drift_feasibility | PASS |
| 5_trim_leakage_mapping | PASS |
| 6_comparators | PASS |
| 7_wrong_reference_sanity | PASS |
| 8_reproducibility | PASS |

## 15. Kill Criteria Evaluation

**PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE.** Kill decisions use only the pre-declared pilot rules.

| Pre-declared criterion | State | Evidence |
|---|---|---|
| 1_marker_gt_unreliable_common_device | NOT_FIRED | {"zero_valid_devices": [], "direct_crosscheck_failures": []} |
| 2_confidence_distributions_overlap | NOT_FIRED | {"D1": 8.022099742619075, "D2": 4.924470130434823, "D3": 7.033553915932821} |
| 3_fixed_offset_invalidated | NOT_FIRED | 128.48605577686635 |
| 4_fingerprint_threat_unintegratable | NOT_FIRED | [] |
| 5_selectivity_transport_failure | NOT_FIRED | {"ra_wrong_accepts": 0} |
| 6_conditions_not_reproducible | NOT_FIRED | {"pairs": [{"pair": ["take01", "take02"], "pre_confidence_abs_delta": 0.0679232494220525, "post_confidence_abs_delta": 0.11569549405698368, "drift_ppm_abs_delta": 33.2005312084771, "reference_gt_offset_abs_delta_s": 0.041020833333333506, "both_gt_valid": true}, {"pair": ["take06", "take07"], "pre_confidence_abs_delta": 0.024364553934983185, "post_confidence_abs_delta": 0.01666478372351704, "drift_ppm_abs_delta": 15.936254980086773, "reference_gt_offset_abs_delta_s": 1.2986666666666666, "both_gt_valid": true}], "all_repeat_pairs_gt_consistent": true} |
| 7_workload_blowout | NOT_FIRED | "owner reported recordings done and no workload blowout or unusual event" |

## 16. Final Protocol Freeze Readiness

`PILOT_PASS_PROTOCOL_FREEZE_READY`. Final protocol: `FROZEN`. Final data must not begin unless the protocol is frozen.

## 17. Required Owner Action, If Any

`NONE`

Reproduction: `True` over 96 comparator records; non-volatile differences: `[]`.
