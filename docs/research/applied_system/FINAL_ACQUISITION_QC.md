# Final Acquisition QC

## Status

`FINAL_QC_PASS` — created 2026-09-19T18:36:35Z on branch `research/applied-system-paper`
(verified at QC runtime).

- 26/26 expected recordings ingested; 26/26 GT_VALID
  (24/24 primary, 2/2
  strict repeats) under the frozen GT/QC contract.
- Frozen QC parameters (from `final_acquisition_manifest.json` gt_contract,
  verified at runtime): marker confidence threshold
  `0.163837792269`, drift tolerance ±`128.486056`
  ppm, mapping disagreement ≤`10` ms,
  exactly 2 full-template marker candidates, trajectory gate
  `TRAJECTORY_GATE_FROZEN_OFF`, frozen 50 ms-margin hole trim, post-trim leakage
  below the frozen threshold, captures never warped or resampled.

## Comparator-Blindness Statement

**NO FINAL COMPARATOR WAS RUN DURING THIS QC. RhythmAlign, GCC-PHAT, NCC, Panako, and Kdenlive never received any final recording, trimmed input, reference, or buffer during this task. QC used only: marker detection, ffmpeg decoding, hashing, marker confidence diagnostics, drift measurement, GT mapping, the frozen trimming machinery, marker leakage checks, and manifest validation. No alignment performance result exists yet for any final take.**

## Owner Acquisition Attestation

Attested by the owner on 2026-09-20; recorded verbatim below
and embedded in the QC freeze. Filesystem timestamps were NOT used as a
substitute for this acquisition metadata.

- All 26 takes (final01-final24, repeat01, repeat02) were recorded following the frozen tables in OWNER_FINAL_RECORDING_INSTRUCTIONS.md.
- SESSION_1 (final01-final10, repeat01, repeat02) used ROOM_A + D1.
- SESSION_2 (final11-final16, final21, final22) used ROOM_A + D1.
- SESSION_3 (final17-final20, final23, final24) used ROOM_B + D2.
- The prescribed special conditions were followed: low-volume playback (final11/13/15), steady finger tapping during playback (final12/14/16), soft interference playback from the second device (final17-final20), partial buffers played in full as delivered (final21/22), and the second recording device (final17-final24).
- No editing, trimming, optimization, or format conversion was intentionally applied to any raw recording; files were copied as recorded.
- Acquisition completed in full (all 26 takes) before this QC task; no interim stop was made. The earlier interim-stop advice was operational guidance, not a frozen acquisition criterion.
- The frozen protocol imposes no minimum time gap between sessions; none was added, and none is required.

## Raw File Inventory Summary

All 26 raw files decoded cleanly; no zero-byte or truncated file; raw
SHA-256 identical before and after all analysis (byte-identical
preservation). Raw recordings stay gitignored and uncommitted.

| Take | File | SHA-256 | Bytes | Container | Codec | Hz | Ch | Dur s | GT |
|---|---|---|---|---|---|---|---|---|---|
| final01 | final01.m4a | b82e19a29f42bd45200a96f17ad018aeab40762fd7dbb9743db6fede28e0ad24 | 1125170 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 69.013 | GT_VALID |
| final02 | final02.m4a | 71384dc9e6a2c6338776fbb20aa844561463e6ee7ee27086a0c3647e9401b3c0 | 1118272 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.587 | GT_VALID |
| final03 | final03.m4a | 54a7db261e02afd82744f013b710b3a5a72b90a9fcbdeba80375965262fcdde1 | 1104661 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.755 | GT_VALID |
| final04 | final04.m4a | 2eff88fab23265a8aa808d690fdb05514faaa820eb3eec04802af146fe7b3f9e | 1179020 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 72.320 | GT_VALID |
| final05 | final05.m4a | b392ee1107616a032a0ad256fa9dae1ed12b61bf2469960d31f70a76a6c4fafb | 1093560 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.072 | GT_VALID |
| final06 | final06.m4a | 092d72edd36792145fc0d41e3493db018910ab31d07a780dbd5087dee0b1843e | 1114872 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.373 | GT_VALID |
| final07 | final07.m4a | e5b6fc73092aecb669da82acf9becfddd79d386df4d0ba882eb02ff1e78c337e | 1095910 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.221 | GT_VALID |
| final08 | final08.m4a | 617bf6a58fce5d51369f466edca633c20322e45cd02a3ce4799bad63de9ac0d7 | 1120669 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.736 | GT_VALID |
| final09 | final09.m4a | 14b4531f0dd94f76ebc72f9cd3f86c5c271276dab9c93b5ffcda8ff824123bc9 | 1089438 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 66.816 | GT_VALID |
| final10 | final10.m4a | 4ee1e51a68b8ebb842116b638bc4f5c03a1993b48c47718b1c3199d8fb84c122 | 1110202 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.096 | GT_VALID |
| final11 | final11.m4a | 0bc303ca944b8d06e56e82283f60c629f85e8c26d817a92ffe3615dd1b61164e | 1102264 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.605 | GT_VALID |
| final12 | final12.m4a | 3b49556a9beb90da250dcf07a4e664e0becdfcbeac71555a960d351a5466ef49 | 1093994 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.093 | GT_VALID |
| final13 | final13.m4a | 43812dae14ea11b3ff536fe40829cf212ce4fba5687e69bafd8a63c87099c8d6 | 1093591 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.072 | GT_VALID |
| final14 | final14.m4a | 805697a365312c0a3130851bacf62c654a6a8cb55f3eeeb8db63e512082c7da3 | 1098415 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.371 | GT_VALID |
| final15 | final15.m4a | afc6a59a6c93f07a5d2a9df5aefab5432f29eb88c23f54de94c59b2fcace693d | 1084151 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 66.496 | GT_VALID |
| final16 | final16.m4a | 3b383a1f006bc37391719648ef0910577677ceb878dcbf00564d13fd00dad5a3 | 1114470 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.352 | GT_VALID |
| final17 | final17.m4a | a64b6fd35df009f31c1ea86f6c5371ecb758ef7f54d541d39e083046bfdcbd1e | 2289090 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 140.480 | GT_VALID |
| final18 | final18.m4a | c99026eb19eee8d4bbc0789a2a20ad8bc63eca2ab9a237660c63569b288b20ca | 2328338 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 142.891 | GT_VALID |
| final19 | final19.m4a | 194bc44eac61529c7361872e6b0388fe5bdc796627d5a61c026976422a2ef933 | 2316546 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 142.165 | GT_VALID |
| final20 | final20.m4a | 139ffdffdb487838fc3b3f2113c54c7d1055d2ed77605ba9f6a85aae63df3a62 | 2314099 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 142.016 | GT_VALID |
| final21 | final21.m4a | 7dc367d4240872c499355746726e579390bc3dc5cccf85df6386bbdb7fedd486 | 1126537 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 69.099 | GT_VALID |
| final22 | final22.m4a | 0b2218dbd6ca5eac0b7f0ce82d2be7e8c51d8b50a265e263d3335a9185763062 | 1108135 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.968 | GT_VALID |
| final23 | final23.m4a | fbd4670167ad0bc5056345dcc226a75f6d870c37a04a20f2d9ca070590dd77fe | 1110501 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.117 | GT_VALID |
| final24 | final24.m4a | cefa9d911a42feed66de69ca459fd3f9cc2c76614f4f332ca621b813da40cadf | 1108753 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.011 | GT_VALID |
| repeat01 | repeat01.m4a | be51f9932ef9d372f81e71d1e78ea48003cb5ff7e59edb8f2f3dc4383011cb39 | 1110911 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 68.139 | GT_VALID |
| repeat02 | repeat02.m4a | 90308388e1f03340fb62145b9cbaa005ab7cf529e063d5d487bc730d500fd53c | 1099870 | mov,mp4,m4a,3gp,3g2,mj2 | aac | 48000 | 2 | 67.456 | GT_VALID |

- Duplicate / copy-mix-up check: 26 distinct
  hashes across 26 recordings; duplicates:
  `{}`; collisions with
  buffer/reference hashes:
  `[]`.
- Retakes (`_b`-style) present and preserved:
  `{"final01": [], "final02": [], "final03": [], "final04": [], "final05": [], "final06": [], "final07": [], "final08": [], "final09": [], "final10": [], "final11": [], "final12": [], "final13": [], "final14": [], "final15": [], "final16": [], "final17": [], "final18": [], "final19": [], "final20": [], "final21": [], "final22": [], "final23": [], "final24": [], "repeat01": [], "repeat02": []}`.

## Session / Room / Device Mapping

Mapping source is the owner attestation cross-recorded against the frozen
acquisition manifest; no inter-session time-gap requirement was invented.

- **SESSION_1** — room ROOM_A, recording device D1, playback P1; 12 takes (12 GT_VALID); conditions: ORDINARY, ORDINARY_REPEAT_STRICT_PAIR_OF_FINAL01, ORDINARY_REPEAT_STRICT_PAIR_OF_FINAL02; takes final01…repeat02.
- **SESSION_2** — room ROOM_A, recording device D1, playback P1; 8 takes (8 GT_VALID); conditions: LOW_LEVEL, PARTIAL, TAP_DOMINANT; takes final11…final22.
- **SESSION_3** — room ROOM_B, recording device D2, playback P1; 6 takes (6 GT_VALID); conditions: DEVICE_VARIATION, INTERFERENCE; takes final17…final24.

## Marker QC

Frozen threshold `0.163837792269`; exactly two full-template
candidates required; no manual rescue; trajectory gate OFF (trajectory
recorded as diagnostics only).

| Take | Pre conf | Post conf | Candidates | 3rd-party max NCC |
|---|---|---|---|---|
| final01 | 0.594045 | 0.420610 | 2 | 0.048231 |
| final02 | 0.430741 | 0.428056 | 2 | 0.044715 |
| final03 | 0.422465 | 0.418542 | 2 | 0.055854 |
| final04 | 0.416874 | 0.432931 | 2 | 0.057351 |
| final05 | 0.423139 | 0.423886 | 2 | 0.044086 |
| final06 | 0.432023 | 0.428121 | 2 | 0.053853 |
| final07 | 0.428994 | 0.427154 | 2 | 0.046650 |
| final08 | 0.420536 | 0.418624 | 2 | 0.032024 |
| final09 | 0.419259 | 0.420558 | 2 | 0.032361 |
| final10 | 0.400270 | 0.415477 | 2 | 0.028125 |
| final11 | 0.385099 | 0.375576 | 2 | 0.043594 |
| final12 | 0.443653 | 0.435696 | 2 | 0.034167 |
| final13 | 0.403222 | 0.345477 | 2 | 0.039072 |
| final14 | 0.442747 | 0.447113 | 2 | 0.046861 |
| final15 | 0.420924 | 0.398188 | 2 | 0.043619 |
| final16 | 0.376790 | 0.452858 | 2 | 0.043692 |
| final17 | 0.566781 | 0.531093 | 2 | 0.026189 |
| final18 | 0.593556 | 0.560893 | 2 | 0.043978 |
| final19 | 0.540114 | 0.544330 | 2 | 0.036450 |
| final20 | 0.616787 | 0.563291 | 2 | 0.032454 |
| final21 | 0.333842 | 0.342757 | 2 | 0.034821 |
| final22 | 0.336376 | 0.343304 | 2 | 0.032904 |
| final23 | 0.610770 | 0.612592 | 2 | 0.026370 |
| final24 | 0.612397 | 0.608808 | 2 | 0.031788 |
| repeat01 | 0.366390 | 0.393028 | 2 | 0.039908 |
| repeat02 | 0.400503 | 0.409249 | 2 | 0.047839 |

- Minimum pre-marker confidence: 0.333841870
- Minimum post-marker confidence: 0.342756858
- Candidate-count failures: `[]`
- Overlap failures: `[]`
  (full-template overlap is enforced inside the frozen detector)
- Post-trim leakage failures: `[]`

## Drift QC

| Take | Device | Drift ppm | Mapping disagreement ms |
|---|---|---|---|
| final01 | D1 | -4.721302 | 0.000000 |
| final02 | D1 | -4.885584 | 0.000000 |
| final03 | D1 | -4.968394 | 0.000000 |
| final04 | D1 | -4.765446 | 0.000000 |
| final05 | D1 | -4.884147 | 0.000000 |
| final06 | D1 | -4.979386 | 0.000000 |
| final07 | D1 | -5.099303 | 0.000000 |
| final08 | D1 | -5.050822 | 0.000000 |
| final09 | D1 | -5.049472 | 0.000000 |
| final10 | D1 | -4.995197 | 0.000000 |
| final11 | D1 | -4.427843 | 0.000000 |
| final12 | D1 | -4.455020 | 0.000000 |
| final13 | D1 | -5.390469 | 0.000000 |
| final14 | D1 | -3.968247 | 0.000000 |
| final15 | D1 | -4.061584 | 0.000000 |
| final16 | D1 | -4.114493 | 0.000000 |
| final17 | D2 | 28.742658 | 0.000000 |
| final18 | D2 | 28.283282 | 0.000000 |
| final19 | D2 | 28.117160 | 0.000000 |
| final20 | D2 | 28.043349 | 0.000000 |
| final21 | D1 | -4.531768 | 0.000000 |
| final22 | D1 | -4.469653 | 0.000000 |
| final23 | D2 | 28.268016 | 0.000000 |
| final24 | D2 | 27.942096 | 0.000000 |
| repeat01 | D1 | -5.140323 | 0.000000 |
| repeat02 | D1 | -4.637285 | 0.000000 |

- Observed drift range: [-5.390469,
  28.742658] ppm
- Frozen tolerance: ±128.486056 ppm — failures:
  `[]`
- Per-device clock signatures are consistent (D1 takes cluster near one
  offset, D2 takes near another), as expected from the attested session
  mapping.

## Mapping QC

- Maximum two-marker mapping disagreement: 9.701e-15 s
- Frozen tolerance: ≤10 ms — failures:
  `[]`
- The disagreement statistic is evaluated after drift correction between
  the two markers (identical to the frozen pilot machinery); the raw clock
  drift itself is gated separately by the ±128.486056 ppm
  tolerance above.

## GT Status

GT_VALID requires: exactly two frozen-threshold marker candidates, drift
inside ±128.486056 ppm, mapping agreement within 10 ms,
clean trim, and no post-trim marker leakage. GT_FAILED is a protocol
failure, never an alignment result.

| Take | GT status | Reason | Ref GT offset s | Direct check Δ s |
|---|---|---|---|---|
| final01 | GT_VALID | — | +3.815667 | +0.001292 |
| final02 | GT_VALID | — | +2.978083 | +0.003812 |
| final03 | GT_VALID | — | +2.956479 | +0.003938 |
| final04 | GT_VALID | — | +7.675417 | +0.003958 |
| final05 | GT_VALID | — | +3.054500 | +0.003979 |
| final06 | GT_VALID | — | +3.436875 | +0.003792 |
| final07 | GT_VALID | — | +2.915271 | +0.003979 |
| final08 | GT_VALID | — | +4.283583 | +0.003833 |
| final09 | GT_VALID | — | +2.548250 | +0.003938 |
| final10 | GT_VALID | — | +3.463104 | +0.003771 |
| final11 | GT_VALID | — | +2.890563 | +0.003667 |
| final12 | GT_VALID | — | +2.731667 | +0.003958 |
| final13 | GT_VALID | — | +2.635854 | +0.003958 |
| final14 | GT_VALID | — | +2.867750 | +0.004000 |
| final15 | GT_VALID | — | +2.427250 | +0.003917 |
| final16 | GT_VALID | — | +4.205896 | +0.003792 |
| final17 | GT_VALID | — | +2.365500 | +0.001313 |
| final18 | GT_VALID | — | +2.388125 | +0.001375 |
| final19 | GT_VALID | — | +2.153688 | +0.001333 |
| final20 | GT_VALID | — | +3.072792 | +0.001250 |
| final21 | GT_VALID | — | -86.456104 | +0.003958 |
| final22 | GT_VALID | — | -84.862146 | +0.004000 |
| final23 | GT_VALID | — | +3.650125 | +0.001333 |
| final24 | GT_VALID | — | +3.018896 | +0.001250 |
| repeat01 | GT_VALID | — | +3.250563 | +0.004000 |
| repeat02 | GT_VALID | — | +2.847958 | +0.003958 |

**GT_VALID: 26 / 26** (primary
24/24; strict repeats 2/2).
The marker-independent direct GT cross-check (raw correlation of a 20 s
reference payload probe against the trimmed input, tolerance 10 ms,
diagnostic/non-gating) passed for
26 of 26 takes; failures:
`[]`.

## Repeat Recordings

`repeat01` (strict repeat of final01, S01) and `repeat02` (strict repeat of
final02, S02) were QC'd like every take, remain separate strict-repeat
reliability recordings, and are NOT converted into primary replacements.

## Any Failures

NONE.

Byte-integrity failures: `[]`.

## Replacement Decision

NONE — no replacement is requested.

## QC Freeze Hash

- Path: `experiments/applied_system/final_pack/results/final_acquisition_qc.json`
- Canonical `qc_freeze_sha256`: `962455b6b2962b06b5e9b7019bef71f4be686e17abb7162932c347c8b261ae9d`
- File SHA-256: `574d5367c29bbf68736fb2090e10466c6ce6981b82840236588f5d2e589b5476`

The freeze is write-once and immutable; it is never rewritten from later
comparator results.

## Readiness for Comparator Execution

**YES** — every required final acquisition unit satisfies the frozen GT/QC contract; the acquisition freeze is immutable; final comparator execution may begin in a separate task.

**NO FINAL COMPARATOR WAS RUN DURING THIS QC.**
