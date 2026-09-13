# Benchmark Machinery Shakedown — Result Report

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Nothing in this report may be counted in the final paper benchmark. No human
participants were involved. All numbers below describe the benchmark
MACHINERY (protocol, GT, trimming, manifest, scoring), not method
performance; the case set is a nine-case engineering set, not a dataset, and
the payloads are deterministic synthetic fixtures
(`experiments/applied_system/synth_payload.py`).

- Study-design authority: `HUMAN_LIGHT_STUDY_DESIGN.md` (this round
  implements its "Recommended Next Experiment", Section 16, machinery half).
- Branch: `research/applied-system-paper`; run executed from working tree
  at parent commit `48652dd` (pre-commit); production code untouched
  (verified by diff before commit).
- Frozen manifest: `0c59568f09a328eed0e44362e4385e95b5845d4d323a77cec2829a46a60091f9`
  (`experiments/applied_system/results/shakedown/manifest.json`).
- Reproducibility environment: `results/shakedown/environment.json`
  (Python 3.10.11, numpy 2.2.6, scipy 1.15.3, librosa 0.11.0, soundfile
  0.13.1, imageio-ffmpeg 0.6.0 / ffmpeg 7.1, Engine v2 (evidence-gated),
  frozen release v1.2.0).

## VERDICT

**SHAKEDOWN_PASS_WITH_FIXES**

All required PASS gates passed (independently derived GT; no marker
leakage; correct sign/trim accounting; reproducible manifest execution;
RhythmAlign + GCC-PHAT + NCC runners; deterministic scoring; zero per-case
manual repair). The WITH_FIXES qualifier covers exactly one non-fatal item:
the Panako fingerprint comparator is PENDING (build-from-source only, no
prebuilt artifact, Windows unsupported natively — integration plan frozen in
`experiments/applied_system/runners/panako_runner.py`).

## Shakedown questions (spec section 3)

| # | Question | Answer |
|---|---|---|
| 1 | Deterministic marker-buffer generation | YES — pure-function chirp/buffer render; byte-identical outputs across runs (test-enforced) |
| 2 | Marker detection independent of RhythmAlign | YES — self-contained normalized matched filter in `marker_protocol.py`; zero imports from production |
| 3 | Payload GT derived without alignment output | YES — GT comes only from the two chirp detections and the exact buffer layout |
| 4 | Two-marker QC detects drift / malformed captures | YES — truncation (1 candidate) and +1000 ppm drift (scale rule) both classified GT_FAILED, deterministically |
| 5 | Markers/guards removed without contaminating payload | YES — mechanical leakage re-scan on every trimmed input (max normalized chirp correlation 0.05–0.26, threshold 0.50) |
| 6 | One frozen manifest, byte-identical inputs | YES — every runner records the SHA-256 of consumed files; all match the frozen manifest |
| 7 | Scoring produces all four outcome classes | YES — all of CORRECT_ACCEPT / WRONG_ACCEPT / SAFE_ABSTAIN / GT_FAILED occurred and are unit-tested |
| 8 | Basic comparators through one common interface | YES — RhythmAlign, GCC-PHAT, NCC through the shared `RunnerRecord` contract |
| 9 | Full run reproducible from manifest + hashes + environment | YES — second complete run byte-identical beyond volatile runtime fields (21/21 records; `reproduction_check.json`) |
| 10 | Manual per-case intervention required | NO — the full pipeline ran unattended end to end |

## MARKER GT — works: YES

Protocol: one rendered playback buffer per case — chirp (0.75 s linear sweep
1→9 kHz at 48 kHz, deterministic, no RNG) | guard (1.0 s) | payload | guard
| chirp. Detection is a normalized matched filter (per-lag overlap-energy
normalization, parabolic sub-sample refinement, non-maximum suppression at
one template length, confidence threshold 0.50). GT requires EXACTLY two
accepted candidates; payload position is the drift-corrected linear map from
both markers (average of the two anchor estimates, disagreement capped at
10 ms).

Measured marker localization: exact to 0 samples on clean digital captures
and within ±0.5 ms under amplitude scaling, added noise (10 dB SNR),
leading/trailing silence, and hard clipping (unit-enforced). Marker
confidences on the shipped run: 0.72 (drifted case) to 1.00.

The conservative GT validity rule is enforced, not assumed: a capture with
only one detectable chirp is GT_FAILED even though the surviving chirp
locates the payload (the `gt_truncated` case demonstrates exactly this).

## DUAL-MARKER QC — works: YES

QC statistic: `scale_error = observed_marker_separation /
expected_marker_separation − 1`, with the observed separation measured
between the two detected chirp starts (65.5 s of buffer apart) — plus the
mapping-disagreement check and the exactly-two-candidates rule.

**What it detects** (demonstrated on this run): sample-clock rate mismatch
between playback and capture; missing/truncated capture sections (a dropped
marker changes the candidate count; gross separation shifts trip the scale
rule); marker mis-detection (confidence threshold + candidate count); and
gross resampling/time-stretch.

**Shakedown tolerance and its empirical context.** The provisional
tolerance is ±500 ppm. A controlled probe across drift magnitudes found:
detection of both markers stays robust up to ≈1000 ppm on this chirp
design; the scale rule correctly refuses GT from 500+ ppm; beyond ≈1200 ppm
the time-warped chirp decorrelates and detection itself fails (also a
deterministic GT failure, but with a different reason). The 500 ppm bound
therefore sits comfortably inside the detectable band.

**Why this tolerance is only provisional.** It is calibrated exclusively on
simulated digital degradations, not on real consumer DAC→ADC chains. Before
the final study, the tolerance must be re-frozen from real-device pilot
measurements: record the observed `scale_error` distribution across pilot
takes, set the bound above the observed maximum with a stated safety factor,
and freeze it in the manifest protocol constants BEFORE any final data
exists. This is a documented TODO for the pilot round, not for the final
benchmark.

**Drift is flagged, never warped.** The drift-corrected linear map is used
only to ESTIMATE GT; the payload audio is never resampled or compensated to
help any system. Excessive drift invalidates the case (GT_FAILED) because
RhythmAlign is a fixed-offset aligner — clock drift is scientifically
relevant to the task contract, not an implementation inconvenience.

## MARKER LEAKAGE — none

Mechanical verification per case: after trimming, the full matched-filter
detection is re-run on the exact bytes every system receives. Maximum
normalized chirp correlation across the seven trimmed inputs was 0.26
(noise case; 0.05–0.11 elsewhere), well below the 0.50 detection threshold —
no leakage. Additionally, both chirp regions and both guards are removed by
construction (holes span [chirp1_start − 50 ms, payload_start) and
[payload_end, chirp2_end + 50 ms]), the trimmed input's payload segment is
asserted verbatim against the source payload in tests, and `prepare` raises
a machinery error (rather than shipping input) if leakage is ever detected.

## GT / TRIM SIGN VALIDATION — works: YES

GT is reported relative to the TRIMMED benchmark input with the production
convention (positive = reference begins `gt_offset_s` into the input;
negative = capture starts |offset| into the reference). Verified three ways:

1. Unit tests recompute the payload position independently from the trim
   bookkeeping (`payload_start − trim_start − removed_before`) for both
   windows, and assert the payload bytes sit verbatim at the GT position in
   the trimmed input.
2. The negative/trim-equivalent case (`pos_negative_offset`, benchmark
   input starting 6.0 s into the payload) produced GT = −6.000000 s exactly,
   and the frozen engine accepted at −6.009 (CORRECT_ACCEPT).
3. The zero-lead case (recording = buffer exactly, no ambient) produced
   GT = 0.0 exactly, with both chirps intact and removed.

## MANIFEST REPRODUCIBILITY — works: YES

The manifest body is fully deterministic (no wall-clock fields); the frozen
hash covers every content byte. Verified mechanically: (a) two independent
`prepare` runs in different directories froze byte-identical manifests with
equal hashes (test-enforced); (b) `verify_frozen` re-derives the hash and
detects any post-freeze edit (tamper tests); (c) the `reproduce` stage
re-ran every runner from the same frozen manifest — all 21 records identical
beyond volatile runtime fields, and the scoring outputs were identical
(`reproduction_check.json: reproduced=true`). The manifest also snapshots
the protocol constants and every hash (payload, capture, trimmed input,
reference) so a run is fully auditable.

## RUNNERS

- **RhythmAlign (frozen v1.2.0): works — YES.** Production entry point
  `find_offset_v2` called unmodified per case (Analyze Only and Full Export
  consume the same decision, so the frozen decision is scored ONCE).
  Results on the engineering set: 6× CORRECT_ACCEPT (conditional offset
  errors 0–11.3 ms, consistent with the engine's 23.2 ms hop granularity,
  all far inside the 100 ms tolerance), 1× SAFE_ABSTAIN on the
  wrong-reference case, 0 protocol failures.
- **GCC-PHAT argmax: works — YES.** 6× CORRECT_ACCEPT (errors ≤ 0.23 ms),
  1× WRONG_ACCEPT on the wrong-reference case — the expected always-output
  failure mode, preserved natively (no threshold invented).
- **NCC argmax: works — YES** (as machinery; see finding below). 5×
  CORRECT_ACCEPT (errors ≤ 0.29 ms), 2× WRONG_ACCEPT: the wrong-reference
  case and — notably — the +250 ppm clock-drift case, where overlap-norm-
  alized waveform NCC locked onto a lag ~56 s away while GCC-PHAT stayed
  within 0.23 ms of GT. This is an infrastructure robustness observation
  about the NCC baseline under time-stretch (recorded honestly; no fix, no
  threshold, no re-run), relevant later when interpreting comparator
  behavior on drifted real captures.
- **Panako: PENDING.** Feasibility probe (2026-09-13): latest release 2.1
  (2022) ships no prebuilt artifacts; requires Gradle build from source and
  ffmpeg on PATH; Windows is unsupported natively (WSL or Docker routes
  only). This exceeds the shakedown setup budget by design, so no
  integration was attempted. A precise integration plan (environment,
  pinned build, store-per-run determinism check, native-semantics mapping:
  ≥1 match → ACCEPT, zero matches → native NO_MATCH, mapping frozen in
  writing before any pilot run) is in `runners/panako_runner.py`.

## MANUAL WORK REQUIRED

None for the machinery round: the full prepare → run → score → reproduce
pipeline executed unattended, and no case required manual repair, rescue,
or re-classification (GT failures were produced and consumed
deterministically).

Optional owner action (not required for this verdict): one or two real
playback→capture loop takes, fully specified in
`experiments/applied_system/OWNER_SHAKEDOWN_INSTRUCTIONS.md` (~5 minutes,
no participants), ingested by `acoustic_loop.py` to check the marker
protocol against real speakers/room/device.

## BLOCKERS

None unresolved for the machinery. Two findings are recorded for the pilot
round, neither fatal:

1. Panako integration is PENDING (planned, not blocking; spec section 18
   explicitly allows this under PASS_WITH_FIXES).
2. The NCC baseline's drift fragility (above) and the chirp's ≈1000 ppm
   detection ceiling are inputs to the pilot-round work: re-freeze the QC
   tolerance from real devices, and consider a drift-tolerant chirp
   redesign (e.g., segmented sweep) only if real-device measurements show
   consumer chains exceeding the detectable band.

## Bugs the shakedown caught in its own machinery

Recorded because they justify the shakedown's existence (both fixed and
regression-tested):

1. **NCC dust amplification**: the detector's (and NCC runner's) normalized
   correlation used an absolute 1e-30 energy floor; in digital-silence
   windows FFT roundoff dust divided by ~1e-15 produced normalized "peaks"
   of value ~100, creating phantom marker candidates. Fixed with an
   amplitude-invariant relative energy floor.
2. **Trim hole boundary**: the post-payload hole initially removed guard +
   margin but not the post-chirp itself; the mechanical leakage check
   caught the leftover chirp immediately (the check works as designed).

## Real-device acoustic loop check

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

**Date:** 2026-09-14. **Origin:** one owner-operated playback→capture round
trip of `media/playback_buffer_song_a.wav` (no participants).

**Recording:** owner phone voice-memo capture, AAC in an m4a container,
nominal 48 kHz, 70.485 s (3,383,296 samples). Original file preserved
unchanged at
`results/shakedown/media/2026年09月14日 00点19分.m4a`
(sha256 `e02f0ab2f0ae9218417366df183031db8a873a8b62716c7f5b5a0640fc0ec2d6`);
identical working copy at `results/shakedown/acoustic/owner_take1.m4a`.
Both are local research material under the media ignore policy (never
committed). Analysis ran on a native-rate ffmpeg decode
(`acoustic/owner_take1_decoded.wav`).

**First analysis attempt (honest failure record):** with the tooling as
committed at `2fc389e`, the take returned GT_FAILED with 0 candidates. The
recording itself was fine; three research-TOOLING defects were exposed
(documented below, all fixed with regression tests in
`tests/test_real_capture_regressions.py`). The recording was never edited
or rescued to make detection succeed.

**Measurements after the tooling fixes (verdict GT_OK):**

| Quantity | Value |
|---|---|
| Capture duration | 70.485 s @ 48 kHz native |
| Pre-marker | 189,396.1 samples = 3.9458 s (confidence 0.226) |
| Post-marker | 3,297,344.7 samples = 68.6947 s (confidence 0.2426) |
| Marker candidates | exactly 2 (rule satisfied) |
| Expected marker separation | 3,108,000 samples = 64.750 s |
| Observed marker separation | 3,107,948.6 samples = 64.7489 s |
| Clock scale | 0.99998346 → **−16.5 ppm drift** |
| Provisional drift gate | ±500 ppm (pass, ~30× headroom) |
| Mapping disagreement | 0.0 samples = 0.0 ms (gate 10 ms) |
| GT status | GT_VALID; GT offset on trimmed input +3.8957 s |
| Leakage re-scan on trimmed input | max normalized chirp correlation 0.030 (threshold 0.15) — no leakage |
| Independent direct-correlation cross-check | payload start within **2.2 ms** of marker GT (gate 10 ms) |
| Sweep-trajectory corroboration (diagnostic) | slope ratios 0.976 / 0.967 vs template — both markers are genuine rising 1→9 kHz sweeps |

**Verdict: GT_OK** — this ONE real take demonstrates that the marker GT and
dual-marker QC machinery survived one real speaker → room → phone
microphone → AAC round trip. It does NOT validate all devices, rooms, or
recorders; it is one existence proof, and it is NOT paper evidence.

**One-second margins: SUFFICIENT.** Playback actually began ~3.9 s into the
recording (player startup latency extended the owner's ~1 s lead), and the
second chirp completed at 69.45 s leaving a 1.04 s tail. Both chirps were
fully captured; the short margins caused no problem, and no re-record is
needed.

**Drift gate assessment:** −16.5 ppm on this device/chain is obviously
compatible with the provisional ±500 ppm gate. This is ONE device on ONE
occasion; the gate remains provisional and must still be re-derived from a
multi-device pilot before the final study. Nothing is frozen from this take.

**Tooling defects found by the real round trip (all fixed; production
RhythmAlign untouched):**

1. **Compressed-capture decode gap.** The acoustic-loop tool read captures
   via soundfile only; libsndfile cannot read AAC, so the owner's m4a
   failed outright ("Format not recognised"). Fix: fallback decode via the
   bundled ffmpeg with NO sample-rate or channel forcing (resampling would
   destroy the drift measurement), with the decoded WAV hashed into the
   report. Regression: `test_m4a_decode_native_rate`.
2. **Phantom marker peaks at capture edges.** The normalized matched filter
   accepted partial-overlap windows; ~2 ms of content at the recording end
   produced a spurious 0.32-confidence "marker" (above the then-0.50 gate).
   Fix: only lags where the FULL template fits inside the capture are
   eligible — which is also protocol-correct, since a partially captured
   chirp must fail GT anyway. Regressions:
   `test_full_template_overlap_required`,
   `test_partially_captured_chirp_fails`,
   `test_chirp_before_capture_start_fails`.
3. **Confidence gate never validated on real acoustics.** The synthetic-era
   0.50 gate rejected BOTH genuine markers on this take: measured
   normalized matched-filter confidence was 0.226 / 0.243, while every
   non-marker content peak stayed ≤ 0.049 (5–7× separation). Room
   reverberation, phone AGC, and AAC compression cap sample-level phase
   correlation well below its synthetic value even for intact sweeps
   (verified independently by the frequency-trajectory analysis). Fix: the
   gate constant is now a documented provisional 0.15 (≥3× rejection margin
   against observed real competing content), with the failure and fix
   recorded here and pinned by `test_min_marker_confidence_covers_real_
   device_regime`. This gate MUST be re-derived from a multi-device pilot
   before the final study; it is not frozen, and the digital shakedown's
   committed results (produced under the 0.50 gate) remain the untouched
   record of that engineering run.

**Second owner take required: NO.** The machinery question this round was
answered by the existing take; nothing about the capture needs redoing.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

## Artifacts

All under `experiments/applied_system/results/shakedown/` (JSON committed;
audio regenerable deterministically and gitignored):
`manifest.json` (frozen), `records/*.json` (21 raw per-pair records, native
semantics preserved, input hashes recorded), `scores.json` (deterministic
scoring with per-case absolute errors), `environment.json`,
`reproduction_check.json`, `panako_status.json`. Every artifact carries the
SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE labels.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.
