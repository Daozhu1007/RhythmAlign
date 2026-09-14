# Final Benchmark Protocol

Status: **FROZEN BEFORE FINAL DATA COLLECTION**

This is the internal preregistration-like freeze for the final confirmatory benchmark. Pilot material and outcomes are development-only. **FINAL DATA MUST NOT BE USED TO CHANGE THESE RULES.**

## Authority and freeze provenance

- Pilot verdict: `PILOT_PASS_PROTOCOL_FREEZE_READY`
- Pilot measurement freeze: `20dbc530c9dffba14a4e51b6773ab8efbf1db1681f597babfd47e7ba6ab039cd`
- Pilot freeze file SHA-256: `49f296ec3c8d58bbd1b05f403079c7268f3bc18679620a2ccc2579eeb50bd125`
- Final exclusion ledger: `ab7572e352421e433b3ed6aff009fdc437d3c57bca73e257c626fcaef5385b9e`
- Outcome-independent diagnostic correction: `1dbadb48c2e009e1f4b8767962e8d3074f0b3722a2db3022959b988942056028`; the original measurement freeze was unchanged and all 12 direct GT cross-checks passed.
- Subject: frozen RhythmAlign v1.2.0; production code remains unchanged.

## The 17-item freeze checklist

1. **Marker waveform:** 0.75 s deterministic linear chirp, 1–9 kHz, peak 0.9, rendered at the capture protocol rate; template implementation is `marker_protocol.py`.
2. **Marker detector:** normalized matched filter with per-lag overlap energy, full-template-overlap eligibility, one-template NMS.
3. **Confidence rule:** exact threshold `0.163837792269` (documentation `0.16`), derived only by `T=sqrt((3B)(0.8G))` before comparator execution.
4. **Candidate count:** exactly two accepted marker candidates; one marker is never valid GT.
5. **Trajectory policy:** `TRAJECTORY_GATE_FROZEN_OFF`; trajectory remains recorded when off.
6. **Drift tolerance:** ±`128.486056` ppm from `max(3D_max,111)`, inside the 1000 ppm cap; captures are never warped.
7. **Mapping disagreement:** ≤`10.000` ms.
8. **Trim rule:** remove both marker/guard holes with 50 ms external margins, concatenate retained audio, never resample/time-stretch; every system consumes the identical trimmed WAV bytes.
9. **Manifest schema:** immutable canonical JSON body hash; repo-relative paths; raw/decoded/trimmed/reference hashes; exact strata, source identity, condition, session, device, and comparator eligibility; freeze before first final system run.
10. **System versions:** RhythmAlign v1.2.0 at `3a622fc33af1212178296ad9dad57ce9693eed48`; Panako commit `e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211` with jar hash `77c56eabf93defe64ddddf0fb75478c415dc7b64ddb065b5a34a27f6b9fb2276`; environment records OS, Python, ffmpeg, Java, numpy, scipy, librosa, and soundfile.
11. **Baseline implementations:** committed `gcc_phat_argmax_v1` and `ncc_argmax_v1`; NCC remains USEFUL_OPTIONAL and is run unless a recorded machinery failure makes it unavailable.
12. **Comparator configs/semantics:** RhythmAlign native ACCEPT/ABSTAIN once per pair; GCC-PHAT and NCC ALWAYS_OUTPUT argmax with no invented rejection; Panako OLAF native ACCEPT/NO_MATCH/ERROR, highest native match score, `offset=Query start−Match start`, no threshold or hybrid refinement. Panako final role is **PLACEMENT_COMPARATOR**. Kdenlive 26.08 remains the essential owner-operated final technical stratum and is scored from project XML, not simulated.
13. **Offset correctness:** 100 ms primary; 50/150 ms sensitivity. Exact GT and approximate GT are never pooled.
14. **Wrong-reference scoring:** every final take is offered reference slot `S(i mod 10)+1`; any ACCEPT is WRONG_ACCEPT, refusal is SAFE_ABSTAIN. Slot rotation is fixed before song identities are filled and never changed from results.
15. **Benchmark conditions:** 24 scored positives: 10 ordinary (S01–S10); 6 low-level/tap-dominant (S01–S06, three each assigned in the frozen acquisition manifest before recording); 4 interference (S07–S10); 2 partial (S01–S02); 2 device-variation (S09–S10). Interference sources are outside every reference/exclusion identity.
16. **Song/source selection:** 10 owner-licensed source identities, exact versions/hashes logged before recording, all cleanly decodable, ≥3 deliberately repetitive; none may occur in the exclusion ledger. No song is selected using system performance.
17. **Final sample counts:** 10 songs; exactly 24 scored positive takes; exactly 24 directed wrong-reference pairs; 2 additional strict-repeat reliability takes reported separately; ≥3 sessions, ≥2 devices, ≥2 rooms; 10 Kdenlive technical pairs; optional 2–4 version-mismatch, 2–4 authentic-handcam approximate-GT, and 3–4 external probes remain separate existence-check strata and are not silently added to primary counts.

## Ground-truth strata and scoring

- `EXACT_GT`: dual-marker GT; ACCEPT within tolerance → CORRECT_ACCEPT, outside → WRONG_ACCEPT; ABSTAIN/NO_MATCH → SAFE_ABSTAIN.
- `APPROXIMATE_GT`: optional authentic takes with a pre-system manual uncertainty interval; reported separately and correct only when the full interval satisfies the criterion.
- `NO_MATCH`: wrong reference/version mismatch; any ACCEPT → WRONG_ACCEPT; refusal → SAFE_ABSTAIN.
- `GT_FAILED`: retained as protocol failure, excluded from alignment metrics, never silently dropped or replaced after system output is known. A required acquisition replacement is decided from GT/QC alone and logged before any comparator sees that case.

## Independence and aggregation

The source/song identity is the independence unit. Pair-level raw counts are always shown; multiple takes/conditions from one song are dependent. Primary reporting is raw counts with denominators, source-level aggregation, conditional accepted-offset median/IQR/max, exact discordant-pair counts, and song-level bootstrap uncertainty. No pilot count enters final estimates.

## Post-freeze bug and tuning policy

After final collection starts, thresholds, features, conditions, pairings, sample counts, scoring, roles, and exclusions cannot change. Only a demonstrable outcome-independent implementation bug may be corrected: preserve original failure evidence, explain why the correction is outcome-independent, add a regression test, version the correction without overwriting the original artifact, and rerun every affected case under the same scientific contract. Result-dependent changes require a new protocol and new final data.

## Prohibited actions

- No final-data threshold/configuration tuning, per-case rescue, manual marker rescue, payload warping, task replacement, or pairing substitution.
- No reuse of pilot songs (Bloody Trail; スティールユー / Steel You; Divide et impera), historical development/holdout songs, or shakedown material.
- No final benchmark collection begins automatically from this document; the owner starts acquisition in a separate task.

**FINAL DATA MUST NOT BE USED TO CHANGE THESE RULES.**
