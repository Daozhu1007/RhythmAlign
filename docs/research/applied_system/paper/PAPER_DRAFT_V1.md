STATUS: TECHNICAL-CORE DRAFT V1 — REVISED AFTER INDEPENDENT HOSTILE REVIEW AND COMPARATOR-INTEGRITY AUDITS; SECOND REVIEW PENDING; CREATOR FEASIBILITY PILOT NOT CONDUCTED.

# Benchmarking Selective Reference-Audio Alignment on Controlled Acoustic Rerecordings

Revised manuscript, PAPER-DRAFT-1, supersedes PAPER-DRAFT-0 (kept as revision history). Not submission-ready. Numeric authorities: [final reporting v2](../../../../experiments/applied_system/final_pack/results/final_benchmark_reporting_v2.json) (sealed at repository commit `9605c21127d14d72922593a7990571d48a461bb2`) and, for the valid GCC comparator, the corrected [gcc_phat_v2_lagfix_results.json](../../../../experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_results.json) with its frozen [correction manifest](../../../../experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_correction_manifest.json). Companion [tables](PAPER_TABLES_V1.md), [claim ledger](CLAIM_LEDGER_V1.md), [citation ledger](CITATION_LEDGER_V1.md), [citation-gap status](CITATION_GAPS_V1.md), and the [review response memo](HOSTILE_REVIEW_RESPONSE_V1.md) preserve the evidence and revision boundaries.

## Abstract

Replacing degraded captured audio in user-generated video with a clean reference requires both accurate timing and a decision about whether a proposed placement is supported. We benchmark frozen RhythmAlign v1.2.0, a selective reference-audio alignment system, on controlled acoustic rerecordings under rhythm-game handcam-style stress-test conditions. A performance-blind source-selection and dual-marker timing protocol produced 24 dependent positive takes from 10 source identities and 24 constructed wrong-reference pairs; no thresholds were tuned on final data. At a 100 ms correctness tolerance, RhythmAlign achieved 20/24 correct-placement yield with four abstentions, 0 wrong positive accepts, and 0/24 wrong-reference false accepts. The always-output correlation controls accepted every case: corrected GCC-PHAT (`gcc_phat_argmax_v2_lagfix`) produced 10/24 correct positive placements and 14 wrong, and normalized cross-correlation produced 19/24 correct and 5 wrong; each accepted all 24 wrong references. The five NCC wrong positives occurred at 1.2–4.7 s edge overlaps that RhythmAlign's frozen 30 s minimum-overlap candidate policy excludes, so this comparison reflects complete system contracts, not the causal effect of abstention. Panako under native shipped OLAF settings achieved 2/24 correct-placement yield with 0/24 wrong-reference false accepts. A separate single-operator Kdenlive technical stratum recovered 2/10 placements. These observations concern one domain, one frozen operating point, and controlled rather than field-sampled rerecordings; they are not calibrated future risk or creator workflow benefit. The evaluated systems differed primarily in unsupported-placement behavior, and the cost of recovering from refusal remains unmeasured.

## 1. Introduction

User-generated video can capture music through loudspeakers, room acoustics, consumer microphones, background sound, and physical impacts. A creator with access to the corresponding clean reference may want to replace the captured soundtrack while retaining the video's timing. This requires estimating where the reference belongs on the recording timeline. A numerically specific offset is insufficient: it must describe the intended recording and the correct occurrence of its content.

An incorrect automatic placement can create additional checking and repair work, or survive into an export. Refusal leaves work unfinished but exposes uncertainty before placement. The relative cost of these outcomes depends on the workflow; this study measures alignment decisions and correctness, without claiming that refusal saves creator time. We treat dependable behavior as a design objective — report wrong placements together with how much work receives a placement, and account explicitly for mismatched references — not as a property certified by the measured scores.

Rhythm-game handcam recording motivates a demanding test domain because musical playback coexists with taps, interference, and repeated musical structure. The final data are fresh acoustic rerecordings under handcam-style conditions, including tapping performed during playback. They are not a population sample of authentic arcade videos. The broader problem is selective reference-audio replacement; neither game-specific processing nor a new alignment algorithm is claimed.

Our bounded contributions are:

1. A controlled acoustic rerecording protocol for reference-placement evaluation, with timing labels independent of the evaluated matchers, source-exposure exclusions, and an explicit constructed wrong-reference stratum.
2. An inspectable frozen-system evaluation comparing RhythmAlign with unconstrained correlation controls, native OLAF fingerprint matching within a pinned Panako implementation, and a separately operated editor-native alignment command.
3. A documented applied finding that successful-match precision alone does not summarize system behavior on this benchmark; unsupported placements, short-overlap candidate policy, refusal, and native no-match behavior materially affect end-to-end placement outcomes.

We do not claim a new selective-prediction method, a new mismatch-evaluation paradigm, the first such benchmark, or the first refusal-aware synchronizer; Section 2 positions each against existing work.

## 2. Related Work

### 2.1 Correlation and audio synchronization

Delay estimation by correlation is established signal processing. Knapp and Carter's generalized correlation framework includes frequency weighting for time-delay estimation [R1]. GCC-PHAT supplies our phase-weighted, always-output control. Normalized cross-correlation addresses signal-amplitude and overlap effects; Lewis provides classical normalization background [R2]. Our frozen NCC implementation normalizes by the energy of the overlapping samples at each lag. It is not represented as an exact implementation of Lewis's locally mean-subtracted image-template statistic.

Audio synchronization also extends beyond a single fixed offset. Ewert, Müller, and Grosche combine chroma and onset information for high-resolution synchronization [R3]. Six and Leman use acoustic fingerprints and refinement for multimodal recording synchronization [R4]; Section 2.2 returns to their system. Our task is narrower than general performance alignment with tempo changes, drift compensation, or dropped-sample repair.

### 2.2 Fingerprinting and occurrence matching

Wang's Shazam-style landmark matching provides an established audio-identification precedent [R5]. The evaluated fingerprint comparator is the OLAF strategy inside a pinned Panako implementation. OLAF itself is a deliberately lightweight, portable fingerprinting system: Six introduced it in an ISMIR 2020 late-breaking/demo abstract [R11] and documented the portable search system in the Journal of Open Source Software [R12]. Panako's 2021 update is additional context for the software family [R6]. The benchmark evaluates the OLAF strategy within the pinned Panako implementation — not every OLAF or Panako configuration described by those publications.

Occurrence alignment with explicit support checking is close prior art. Ramona and Peeters align audio occurrences to verify and synchronize fingerprint annotations, handling incorrect annotations, repeated occurrences that must be discarded from alignment, and temporal occurrence support through matched-segment structure [R13]. Their work precedes and covers the idea of rejecting unsupported or erroneous occurrences; we claim no conceptual novelty for rejecting unsupported occurrences, and our temporal-support heuristic is an implementation choice within that known landscape. Panako's own duration and occupancy policy provides concrete implementation precedent in the evaluated family.

Public evaluation frameworks for audio identification also predate this work. Ramona et al. published a broadcast-monitoring evaluation framework with a public corpus, ground-truth annotation, and scoring toolkit [R14]. Relative to that family, the present work adds controlled acoustic rerecording acquisition, system-independent timing markers, a reference-placement task contract with constructed wrong references, explicitly frozen system outputs, and an applied editor-native comparator. We do not claim that mismatch evaluation itself is new.

### 2.3 SyncSink, refusal, and editor-native synchronization

Six and Leman's SyncSink goes beyond a matcher: it combines fingerprint-supported synchronization, match qualification, waveform-domain refinement, and a practical synchronization interface [R4]. The OLAF command-line runs measured here are NOT a direct empirical test of the complete SyncSink pipeline; they characterize one matcher configuration under this benchmark's task contract.

Selective classification formalizes the trade-off between coverage and error on accepted cases [R7]. We borrow that evaluation distinction, without importing classification guarantees into a heuristic audio system. A single frozen decision policy is measured; no risk-control theorem, probability calibration, or optimal operating point is established.

Native editing tools are practical alternatives. Kdenlive documents setting an audio reference and aligning another timeline clip to it [R8]. This motivates a technical stratum using the actual editor and saved project placements. It does not substitute for measuring creator recovery or end-to-end editing effort.

## 3. System

RhythmAlign v1.2.0 accepts a degraded recording and a clean reference and estimates a constant reference-start offset on the recording timeline. A positive offset delays the reference; a negative offset trims its beginning. The production pipeline decodes audio and forms complementary representations: chroma-change/onset evidence, onset-strength evidence, and per-channel energy normalization (PCEN), with and without harmonic/percussive separation (HPSS). PCEN and median-filter HPSS are established ingredients [R9, R10]. Their use here is an implementation choice.

Candidate offsets from correlation peaks are clustered. The decision policy checks feature strength, competing placements, geometric overlap, and corroborating evidence. Plain PCEN and PCEN with HPSS belong to the same evidence family; they are not independent votes. Onset agreement corroborates a primary candidate rather than supplying proof of independent support. The frozen temporal-support check additionally examines whether the deciding PCEN correlation is concentrated in a short portion of the overlap; the released rule uses nominal one-second bins and rejects a strongest-bin share above 0.25. This is a heuristic safeguard, not a calibrated probability of correctness.

The candidate policy also enforces a frozen minimum-overlap requirement of 30.0 s: candidates whose usable music/video overlap is below 30 s are excluded, and the system abstains when the best surviving cluster is below it. This edge-lag guard removes entire regions of the lag axis from consideration and is central to interpreting the comparator results in Section 6. Other gates (feature strength, uniqueness, corroboration, temporal support) apply in addition, so 30 s of overlap is necessary but not sufficient for acceptance.

The engine emits `ACCEPT` with an offset or `ABSTAIN` with a reason. An accepted decision can be inspected in Analyze Only or used by the export workflow to place the reference and produce an MP4 through FFmpeg. Normal export stops after abstention. Analyze Only and Full Export share the same alignment decision, so the benchmark scores it once. Export capability describes the system; the benchmark does not establish completed creator tasks or perceptual audiovisual quality.

The evaluated production commit is `3a622fc33af1212178296ad9dad57ce9693eed48` (v1.2.0). Reproduction is defined by that code and its defaults, not by retuning the prose description. The [implementation](../../../../alignment_engine_v2.py) and [frozen runner](../../../../experiments/applied_system/runners/rhythmalign_runner.py) provide the exact system contract.

## 4. Evaluation Method

### 4.1 Research questions

**RQ1:** On fresh acoustic data, how do the frozen systems differ in wrong placements among produced positive placements and in behavior on constructed wrong references?

**RQ2:** What correct-placement yield accompanies RhythmAlign's selective policy?

**RQ3:** How do native fingerprint matching and editor-native synchronization behave under the measured placement task?

"Wrong placement" denotes an accepted placement whose absolute offset error exceeds the frozen correctness tolerance, plus any accepted wrong reference. Observed error magnitudes are reported descriptively; no real-world consequence class is measured.

### 4.2 Fresh source selection

The exclusion ledger removes historical development, spent holdout, shakedown, and acoustic-pilot identities. Selection checked identity aliases and file hashes as well as decoding suitability, so a renamed or re-encoded source did not become fresh merely through a different filename. Freshness is relative to the documented development exposure history, not a claim that no algorithm developer has ever encountered these songs.

The declared source-only rule selected ten reference identities. Three were deliberately chosen for high long-lag recurrence; remaining slots and ordering followed deterministic hash rules. A separate interference identity was selected outside the reference and exclusion pools using source texture. Recurrence was a selection heuristic, not a validated difficulty measure. No comparator output entered source selection, recording allocation, or acquisition QC. Sources and exact versions were frozen before system execution. See [source selection](../FINAL_SOURCE_SELECTION.md).

### 4.3 Acoustic acquisition

The primary set comprises 24 positive takes from ten sources: ten ordinary, three low-level, three tap-dominant, four interference, two partial, and two device-variation takes (Table 1). Acquisition covered three sessions, two rooms, and two recording devices, with two further strict repeats kept separate. These are actual microphone recordings of loudspeaker playback, not clean music digitally inserted into noise. The owner attested the prescribed conditions; taps were performed during playback and interference came from separate playback. Room, device, session, and condition were not fully crossed, so condition effects cannot be isolated causally.

Several acquisition properties bound the evidence. The benchmark is controlled acoustic rerecording, not authentic field sampling: 10 source identities form a structured stress-test pool, repeated conditions within a source are dependent, and the wrong references are constructed rather than sampled from creator behavior. Playback buffers used a common 60 s music payload, so results represent one duration regime that favors tasks with substantial overlap; RhythmAlign's 30 s minimum-overlap requirement should be considered when interpreting applicability to shorter clips. Two further asymmetries are disclosed from frozen metadata. First, the four interference takes (final17–final20) produced trimmed inputs of approximately 136.9–139.3 s, versus approximately 62.9–68.7 s for the other primary takes; the acquisition record documents no reason for the longer interference captures, and we disclose the asymmetry without interpreting it. Second, the acquisition attestation summarizes "the second recording device (final17–final24)"; the per-take drift QC records are authoritative and assign final21–final22 to the primary device D1 within SESSION_2 (ROOM_A), with only final17–final20 and final23–final24 recorded on the second device D2. This paper follows the per-take records; the device-variation condition remains final23–final24 only. The clarification is provenance only; no evidence changed.

Partial buffers began inside the source rather than at its beginning; ground truth therefore includes the source slice's start time. The references remained the corresponding full sources. The two strict repeats repeated the ordinary takes for S01 and S02 and were neither primary replacements nor extra independent songs. All 26 recordings passed frozen acquisition QC. Optional authentic-handcam, version-mismatch, and external-domain strata do not contribute evidence to this draft.

### 4.4 Independent timing ground truth

Each sample-exact playback buffer contained a 0.75 s linear chirp spanning 1–9 kHz, a 1 s guard, the music payload, another 1 s guard, and a second chirp, rendered at 48 kHz. Marker peak amplitude was 0.9. A normalized matched filter located full-template candidates; one-template nonmaximum suppression and the frozen confidence threshold `0.163837792269` were applied. Exactly two accepted markers were required. The final protocol supersedes the earlier study design's tentative single-marker rule.

Let the two marker starts in buffer time be b1 and b2, and their detected recording times be r1 and r2. The map t(b) = r1 + (b − b1)(r2 − r1)/(b2 − b1) locates the payload on the recording clock. Drift was checked against ±128.486056 ppm and marker mapping disagreement against 10 ms; the trajectory gate was frozen off. Mapping agreement after the two-marker fit is a consistency check, not an independent precision estimate. Captured payload samples were never warped or time-stretched.

Marker and guard holes were removed with the frozen 50 ms external margins; retained segments were concatenated and a leakage scan applied. Timing labels were transferred to that trimmed timeline by subtracting removed samples. The reference-start offset equals the retained payload-start time minus the source slice start. Every comparator received hash-identical trimmed input and reference files, while retaining its own native internal decoding behavior. Markers were label machinery and were not available as alignment cues.

The frozen QC record also contains a marker-independent direct-correlation diagnostic. It did not gate inclusion or replace marker labels; agreement with that diagnostic is not promoted into independent confirmation of a correlation comparator. `GT_FAILED` would have been a retained protocol failure, excluded from alignment metrics with a blind reason; no final take required replacement. Full details are in the [protocol](../FINAL_BENCHMARK_PROTOCOL.md) and [acquisition QC](../FINAL_ACQUISITION_QC.md).

### 4.5 Comparators and comparator provenance

**RhythmAlign** used its native frozen `ACCEPT`/`ABSTAIN` decision once per pair.

**GCC-PHAT.** The initial frozen comparator, `gcc_phat_argmax_v1`, contained a confirmed index-to-lag conversion defect for unequal-length signals: it unwrapped the zero-padded FFT correlation at a length-independent midpoint, misreporting argmax indices in a band of negative lags by exactly one FFT length. The defect was discovered through independent manuscript review, not through outcome inspection. The correction was derived from linear-correlation lag geometry alone and validated on synthetic known-offset fixtures before any final case was re-executed; the set of affected records was predicted from frozen outputs and frozen file lengths and hash-sealed in a correction manifest before the rerun. The corrected implementation `gcc_phat_argmax_v2_lagfix` preserves the PHAT curve, FFT length, and argmax index bit-for-bit and changes only the lag mapping. A uniform rerun on the byte-identical frozen inputs changed exactly two reported offsets (the final21 positive and wrong-reference records) and zero scored outcomes at any tolerance. The original v1 runner, its 50 raw records, and all sealed artifacts are preserved verbatim as defective-implementation evidence; the correction is versioned and additive. The valid GCC comparator for this paper is `gcc_phat_argmax_v2_lagfix`; [lag audit](../GCC_PHAT_LAG_AUDIT.md) documents the full chain.

**NCC** (`ncc_argmax_v1`) used per-lag overlap-energy normalization and returned its argmax. It is an unconstrained full-lag argmax control: every lag with any nonzero overlap — down to a single sample — is a legal candidate, with no minimum-overlap requirement. RhythmAlign, by contrast, hard-excludes candidates below 30 s of usable overlap. The evaluated implementations of GCC-PHAT and NCC have no native rejection rule. We did not invent thresholds to make them selective, add an overlap threshold to NCC, or interpret output specificity as probabilistic confidence.

**Panako** used the pinned source commit `e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211`, its recorded binary hash, and the OLAF strategy at shipped settings. Each case used a fresh reference store. Native outputs were `ACCEPT`, `NO_MATCH`, or `ERROR`; the highest native match score supplied the match, and placement was query start minus match start. Empty matching output remained `NO_MATCH`. No hybrid refinement or final-data tuning was added.

**Kdenlive 26.08.1** was operated by the owner on ten preselected positive pairs spanning the conditions. Native audio-reference alignment was followed by saving the project; relative clip placement is extracted from its XML and scored against the frozen labels. The ten-pair axis remains separate from the automated 24-positive axis and has no wrong-reference arm. It measures one operator's technical runs, not a user study.

### 4.6 Wrong-reference protocol

Each primary take numbered i was offered reference slot S((i mod 10) + 1). This is a rotation over the take index, not a post-result choice of the most confusing source. The assignments were frozen before source identities were filled and verified to differ from each take's true source. There are 24 directed wrong-reference pairs, reusing the primary recordings. Any accepted placement is `WRONG_ACCEPT`; refusal is `SAFE_ABSTAIN`, a scoring label meaning no placement was emitted for a no-match case — it carries no claim about user or workflow consequences. There is no true offset for a mismatched reference, so output magnitudes are not offset errors.

### 4.7 Metrics and independence

An accepted positive is `CORRECT_ACCEPT` when absolute offset error is at most 100 ms, and `WRONG_ACCEPT` otherwise. The predeclared sensitivity tolerances are 50 and 150 ms. These are scoring tolerances, not an independently established perceptual synchrony threshold.

- **Acceptance coverage:** accepted placements / primary positives.
- **Correct-placement yield:** `CORRECT_ACCEPT` / primary positives.
- **Positive-case accepted error rate:** `WRONG_ACCEPT` / accepted positive placements; undefined if no positive is accepted. This is the wrong-placement share among accepted positives (the selective-prediction literature's accepted risk; we use the error-rate name to avoid implying workflow consequence).
- **Wrong-reference false-accept rate:** accepted wrong references / wrong-reference cases.
- **Conditional CORRECT_ACCEPT error:** absolute-error distribution restricted to correct accepts, reported alongside the distribution of all produced positive placements.

Source identity is the independence unit. The 24 within-song takes are dependent, and constructed negatives share both recordings and the reference pool. Raw denominators are primary. The frozen source-cluster bootstrap resamples ten identities for 10,000 replicates with seed 20260920, calculating rates within each resample. Its intervals are descriptive aids, not evidence of population equivalence, significance, or calibrated future risk. No new inferential test or analysis is introduced here; paired outcome counts (Table 7) are the frozen per-case discordance counts, reported without significance testing.

### 4.8 Frozen evaluation policy and corrections

An internal preregistration-like protocol fixed sources, exclusions, sample counts, conditions, pairings, software identities, decision semantics, and scoring before final runs. It was not an externally registered preregistration. Final outcomes were not used to tune thresholds. The owner-operated Kdenlive evidence was sealed before automated comparator execution; raw outputs and their hashes were retained.

Three outcome-independent corrections are preserved in the evidence chain. First, the initial Kdenlive procedure placed clips at timeline zero, preventing leftward placements; the uniform replacement procedure provided 180 s of headroom, derived from frozen input lengths, and original pair01 was retained as void evidence with pair01r2 supplying its scored placement. Second, the XML reader was corrected to handle nested track structures and chain resources uniformly before Kdenlive scoring; its original erroneous failure output remains archived. Third, the GCC-PHAT lag-mapping correction of Section 4.5 was derived, validated, and sealed before its uniform rerun. None of these corrections used ground-truth agreement to choose placements or outcomes.

The subsequent reporting audit preserved raw results while separating acceptance coverage from correct-placement yield, correcting NCC's accepted-error-rate denominator, labeling the successful-placement error distribution correctly, and expressing wrong-reference bootstrap uncertainty as rates. All paper-facing metrics use reporting v2. These are versioned reporting corrections, not revised outcomes.

## 6. Results

The automated benchmark contains 200 stored system records across primary positives, wrong references, and separate repeats, with no runner errors. Reporting v2 governs the main metrics, error distributions, bootstrap summaries, repeats, and Kdenlive totals; the GCC-PHAT columns additionally reflect the corrected `gcc_phat_argmax_v2_lagfix` rerun, whose scored counts are identical to the frozen v1 arm. Condition and source counts not duplicated in v2 are taken from the linked immutable final-results artifact; no mislabeled legacy derived metric is used.

**Table 2. Main results at 100 ms.** Acceptance coverage, correct-placement yield, and positive-case accepted error rate concern the 24 primary positives. The last column concerns the separate 24 wrong-reference pairs. GCC-PHAT = corrected `gcc_phat_argmax_v2_lagfix`; the original v1 implementation is preserved defective-implementation evidence.

| System | Acceptance coverage | Correct-placement yield | Positive-case accepted error rate | Wrong-ref false accept |
|---|---:|---:|---:|---:|
| RhythmAlign v1.2.0 | 20/24 (83.3%) | 20/24 (83.3%) | 0/20 (0%) | 0/24 (0%) |
| GCC-PHAT argmax (v2 lagfix) | 24/24 (100%) | 10/24 (41.7%) | 14/24 (58.3%) | 24/24 (100%) |
| NCC argmax (unconstrained) | 24/24 (100%) | 19/24 (79.2%) | 5/24 (20.8%) | 24/24 (100%) |
| Panako OLAF | 2/24 (8.3%) | 2/24 (8.3%) | 0/2 (0%) | 0/24 (0%) |

### 6.1 Positive alignment and paired outcomes

RhythmAlign returned 20 correct placements and four abstentions, without an observed wrong positive placement. GCC-PHAT (v2 lagfix) produced ten correct and fourteen wrong placements; NCC produced nineteen correct and five wrong placements. Panako produced two correct placements and 22 no-match outputs. Acceptance coverage and correct-placement yield coincide for RhythmAlign and Panako only because every positive they accepted was correct here. The always-output systems' acceptance coverage is 100%, regardless of their lower correct-placement yields.

The 20/24 versus 19/24 yield difference between RhythmAlign and NCC is not broad dominance. The frozen paired per-case counts (Table 7) show 17 positives both placed correctly, 3 RhythmAlign-only, 2 NCC-only, and 2 neither; the analogous GCC-PHAT counts are 10 both, 10 RhythmAlign-only, 0 GCC-only, 4 neither, and Panako's are 2 both, 18 RhythmAlign-only, 0 Panako-only, 4 neither. These are dependent within-source observations; no significance test is performed.

The frozen source-bootstrap 95% descriptive intervals for correct-placement yield are [0.60, 1.00] for RhythmAlign, [0.17, 0.70] for GCC-PHAT, [0.63, 0.95] for NCC, and [0.00, 0.19] for Panako. These wide intervals and the source dependence limit generalization. Table 4's source panel records the underlying counts; the descriptive comparison does not establish a population ranking.

### 6.2 Wrong-reference behavior

RhythmAlign refused all 24 constructed wrong-reference pairs, giving 0/24 false accepts. Panako likewise gave 0/24. GCC-PHAT (v2 lagfix) and NCC each returned a placement for every wrong reference, giving 24/24 under their native always-output semantics. These counts answer the no-match challenge, not the frequency with which creators select wrong files.

The wrong-reference rate-bootstrap intervals are [0, 0] for RhythmAlign and Panako and [1, 1] for both always-output baselines. They are degenerate because each source resample reproduces uniform observed behavior; they do not bound unobserved future risk. For wrong references, the median absolute output offsets were 64.2303 s for GCC-PHAT (v2 lagfix) and 104.4808 s for NCC, with maxima 132.7303 s and 155.5800 s. These are output magnitudes, not errors against a nonexistent true placement.

### 6.3 Placement error

Every CORRECT_ACCEPT placement was below 25 ms. Among correct positive placements, median errors were 7.9 ms for RhythmAlign, 0.22 ms for GCC-PHAT (v2 lagfix), 3.8 ms for NCC, and 15.1 ms for Panako (Table 3). This conditioning excludes the unsuccessful outputs and differs across systems.

Across all produced positive placements, GCC-PHAT's (v2 lagfix) median error was 29.3135 s and its maximum was 113.1878 s; NCC's median was 0.0039 s but its maximum was 153.3829 s. Thus even a small all-output median can conceal large wrong placements. RhythmAlign's all-produced maximum was 0.0157 s and Panako's was 0.0219 s because neither had wrong positive accepts in this set. Both conditional and all-produced distributions, with denominators, are retained in Table 3. Automated and Kdenlive outcome counts are unchanged across the frozen 50/100/150 ms grid. This is tolerance sensitivity, not a sweep of acceptance thresholds.

### 6.4 The comparator contract behind the NCC difference

NCC remains an unconstrained argmax control. Its five wrong positive placements occurred at short edge overlaps that RhythmAlign's frozen candidate policy excludes; therefore the comparison reflects both estimator and candidate-policy differences and does not isolate the causal value of abstention. Concretely, the five wrong NCC positives (final02, final18, final19, final20, final23) sit at usable overlaps of 1.675 s, 1.234 s, 3.589 s, 3.522 s, and 4.694 s — approximately 1.2–4.7 s — all below RhythmAlign's 30 s threshold, while all 19 NCC correct positives sit at 60.414 s of overlap or more and the 30 s policy line falls in the empty middle. RhythmAlign's edge-lag guard alone excludes all five placements, independent of its other gates. For contrast, GCC-PHAT's wrong positives mostly sit at 60 s-or-more overlaps — genuine spurious peaks with abundant overlapping evidence — plus one sub-30 s placement; its mechanism differs from NCC's.

The converse is equally unsupported: NCC's score at the true lag on the five takes is unknown, and scoring it would be a new experiment on exposed final data. We therefore draw no conclusion that NCC is inherently unsuited, that correlation cannot solve the task, that abstention alone caused the measured difference, or that a 30 s-filtered NCC would succeed. That hypothetical system was not evaluated.

### 6.5 Condition-level observations

RhythmAlign's correct-accept/refusal counts were 9/1 ordinary, 3/0 low-level, 3/0 tap-dominant, 2/2 interference, 2/0 partial, and 1/1 device variation. These are raw counts within conditions, not numerator/denominator rates; Table 4 gives each condition's denominator and all comparator outcomes. The small, dependent cells support no subgroup inference.

All four RhythmAlign abstentions occurred on S08 (Cryptarithm: final08 and final18) and S10 (Straight into the lights: final20 and final24), two sources flagged as repetitive before evaluation. S08 yielded 0/2 correct placements with two refusals, S10 yielded 1/3 with two refusals, and the third flagged source S09 yielded 3/3. This records a concentration of refusals, not proof that repetition caused them or that all repetitive sources fail.

### 6.6 Strict repeats

The two additional takes support observations only (Table 6). RhythmAlign accepted both originals and repeats, with changes in signed error relative to each take's own ground truth of +7.8 ms and +14.0 ms. Those are error changes, not raw offset movements: independent recording starts shift the appropriate reference position. Its raw output movements were 0.5573 s and 0.1161 s.

For repeat02, GCC-PHAT remained `ACCEPT` while changing from a correct original to a wrong repeat; its output moved 67.2049 s. NCC also remained `ACCEPT` but changed from a wrong original to a correct repeat, with 60.4599 s movement. GCC-PHAT's repeat01 and original were both wrong by about 61.9 s. These GCC repeat records are lag-identical under the v2 lagfix correction, so Table 6 holds unchanged for the valid comparator. Decision-state agreement therefore does not establish placement repeatability or correctness. Panako returned `NO_MATCH` for both repeats of originals it had accepted. No reliability rate or population repeatability conclusion is inferred from two repeats.

### 6.7 Kdenlive technical stratum

Kdenlive produced two correct and eight wrong placements among ten valid scoring pairs, with zero native failures (Table 5). Counts are identical at the three scoring tolerances. Pair02 and pair10 were correct, with errors of 5.3 ms and 0.1 ms; the wrong-placement errors ranged from approximately 0.85 s to 149.4 s. This separates successful operation of the native command from correct placement.

The stratum is bounded: ten selected positives covering seven source identities, one owner/operator, one editor version, and no wrong-reference arm. It is not a usability comparison, and its denominator is not the automated 24-positive set. The scoped reading is that the native command did not reliably recover placement on this selected technical stratum — not that creators should prefer one tool over another.

Nine valid runs have recorded operator times: median 58.6 s, interquartile range 45.1–60.7 s, total 551.5 s. Pair01r2 lacks a timer record and is not imputed. The void original pair01 contributes neither a placement nor a time to these summaries. These are times for one operator's technical procedure, not comparative creator task times, recovery costs, or HCI evidence.

## 7. Discussion

This benchmark does not isolate a pure "abstention effect." The evaluated systems differ in complete contracts: estimator behavior, candidate support domain, overlap policy, rejection or refusal behavior, and native no-match semantics. RhythmAlign excludes sub-30 s overlaps and can abstain; NCC and GCC-PHAT (v2 lagfix) score every lag and always emit; Panako applies its own native match policy. Within those contracts, RhythmAlign produced fewer wrong placements than the always-output controls while retaining 20/24 correct placements, and successful-match precision alone was insufficient to summarize behavior: GCC-PHAT's correct accepts were the most precise measured, yet it also produced fourteen wrong positives and accepted every wrong reference. Pretending the estimators differ only in whether they abstain would be the weaker scientific claim; the contract-level reading is the defensible one.

Refusal is visible unfinished work. RhythmAlign's four positive abstentions concentrated on two preflagged repetitive sources, while the other preflagged repetitive source was accepted throughout. The result is consistent with selective handling of difficult evidence, but this system-level benchmark cannot assign causality to any individual gate, and the 30 s edge-lag guard alone accounts for the NCC contrast of Section 6.4. There was no final ablation, and we do not attribute the measured advantage specifically to the temporal-support safeguard or to abstention as such.

Panako was conservative on this task at its native shipped settings: it accepted two positives and no wrong references. This does not establish that fingerprinting is generally weak, that the PANAKO and OLAF strategies are interchangeable, or that another configuration would have the same yield. Conversely, GCC-PHAT and NCC expose the consequence of returning an argmax without a refusal mechanism; their measurements do not show that correlation cannot support a selective detector. Adding such a detector — or a 30 s overlap threshold to NCC — would define a different system requiring its own independent evaluation, which we did not perform.

Kdenlive's separate technical stratum shows that editor-native synchronization was not automatically a successful substitute on these measured pairs. The comparison is bounded by the selection, editor version, procedure, and single operator. Its denominator cannot be compared as if it were the automated full set, and its recorded times cannot establish that RhythmAlign saves editing effort.

### 7.1 Unmeasured cost of abstention

The benchmark measures when the system refuses, but not the time or effort required for a creator to recover from that refusal. A predesigned 2-creator feasibility pilot exists but was not conducted for this benchmark-first draft. There are no pilot results, observed recovery paths, interface-understanding measurements, or creator task-time estimates to report. The unrun design is not evidence that refusal is inexpensive or understandable.

## 8. Limitations

The ten source identities limit the empirical population. Multiple takes from the same song are dependent, and room, device, session, and condition covary. Source selection was deliberately structured for stress testing rather than random sampling. All magnitudes concern one domain and controlled handcam-style acoustic capture — not field-prevalence samples — with no external-domain or separate authentic-handcam confirmation in this draft.

The comparator set carries contract asymmetries. The initial GCC-PHAT comparator required a post-final, outcome-independent lag-mapping correction; the corrected v2 lagfix implementation is valid for all principal results, and the defective v1 remains preserved evidence. The NCC comparison is contract-asymmetric because of the minimum-overlap difference documented in Section 6.4. No matched selective correlation comparator was evaluated, so no estimate of what a selective correlation detector would achieve exists. The common 60 s payload duration favors tasks with substantial overlap and limits inference for shorter clips.

The wrong-reference cases are constructed directed pairs drawn from the reference pool. They test rejection of known mismatches, not deployment prevalence, every possible wrong reference, or confusion between versions of the same song. Zero observed wrong accepts does not certify future risk, calibrate the scores, or establish any export guarantee.

Only one frozen operating point was evaluated. There was no final threshold sweep, no feature ablation, and no basis for claiming an optimal risk-coverage trade-off. Panako used native shipped OLAF settings only. The editor technical stratum is small and positive-only: Kdenlive used one version, one operator, and ten pairs, with one missing timer. Only two strict repeats were available. These design limits prevent broad comparator rankings and repeatability claims.

The exact final media are not openly redistributable because they include commercial music; result recomputation is open, but exact-media re-execution requires authorized access. Independent marker timing avoids deriving labels from any evaluated system, but does not eliminate acoustic, clock, or decoding uncertainty. The named exact-GT stratum is protocol-valid marker timing, not a claim of physically exact zero-uncertainty labels. Tiny differences among successful sub-millisecond and millisecond errors should not be treated as perceptual or universal precision rankings.

There has been no creator workflow or usability study for this draft. Abstention recovery cost, end-to-end task completion, effort savings, preference, and understanding of decisions remain unmeasured. Kdenlive technical operation and software export capability do not fill this evidence gap, and no population HCI claim is made. No calibrated future risk is established.

## 9. Reproducibility

Reproducibility is available at three distinct levels, and the draft does not conflate them.

**A. Result recomputation.** Committed raw outputs, manifests, hashes, scoring code, and the deterministic reporting module allow independent recomputation of every number in this paper from stored evidence, including the corrected GCC-PHAT distributions and the paired counts. The [validation script](validate_paper_v1.py) performs such recomputation without executing a comparator or accessing audio.

**B. System re-execution on the exact final media.** Re-running any comparator on the exact final corpus requires access to the exact acoustic captures and reference media, which are not openly redistributed because they include commercial music. The result is a reproducible protocol with restricted exact-media corpus; the corpus itself is not openly available for re-execution.

**C. Protocol replication.** The acquisition, ground-truth, and scoring machinery can be independently replicated using other authorized or openly licensed media.

The evidence package retains frozen source and acquisition manifests, source hashes, QC records, pair assignments, comparator identities/configurations, raw per-pair outputs, SHA-256 sidecars, and deterministic aggregation code. The reporting-v2 artifact identifies the hashes of its immutable raw assembly and original aggregate. Hashes prove identity, not availability: they let a holder of authorized media verify they possess the exact evidence, but do not by themselves distribute it. Source and capture media include commercial music and are not committed for unrestricted redistribution; any reviewer-access arrangement remains subject to permission, and this draft does not claim that such access has been arranged. Existing synthetic fixtures can validate scoring, timing, and project parsing without commercial audio, but carry no fresh acoustic performance evidence. An openly licensed performance replacement dataset has not been supplied by this study.

## 10. Conclusion

On the measured benchmark, frozen RhythmAlign produced fewer wrong placements than the evaluated always-output controls while retaining 20/24 correct placements, refused all 24 constructed wrong references, and abstained on four positives. The comparison reflects complete system contracts, including candidate-overlap policies and refusal/no-match behavior; it does not isolate a causal effect of abstention. Successful-match precision alone did not summarize system performance. The findings are bounded by ten dependent-take sources, one controlled-acoustic domain, one frozen operating point, and unmeasured creator recovery cost; a second-round review precedes any decision about human data.

## References

Entries use the [citation ledger](CITATION_LEDGER_V1.md), which records verification status and retrieval dates. Both former citation TODOs are resolved; no entry is invented.

- **R1.** Knapp, C. H., and Carter, G. C. (1976). The generalized correlation method for estimation of time delay. *IEEE Transactions on Acoustics, Speech, and Signal Processing*, 24(4), 320–327. [DOI](https://doi.org/10.1109/TASSP.1976.1162830).
- **R2.** Lewis, J. P. (1995). Fast Template Matching. *Vision Interface*, 120–123. [Expanded author treatment: Fast Normalized Cross-Correlation](https://scribblethink.org/Work/nvisionInterface/nip.html).
- **R3.** Ewert, S., Müller, M., and Grosche, P. (2009). High Resolution Audio Synchronization Using Chroma Onset Features. *ICASSP*, 1869–1872. [DOI](https://doi.org/10.1109/ICASSP.2009.4959972).
- **R4.** Six, J., and Leman, M. (2015). Synchronizing multimodal recordings using audio-to-audio alignment: an application of acoustic fingerprinting to facilitate music interaction research. *Journal on Multimodal User Interfaces*, 9(3), 223–229. [Institutional record](https://biblio.ugent.be/publication/6873558); [author manuscript](https://0110.be/files/attachments/434/2015.synchronized-recording.pdf).
- **R5.** Wang, A. L. (2003). An Industrial-Strength Audio Search Algorithm. *ISMIR*, 7–13. [DOI](https://doi.org/10.5281/zenodo.1416340).
- **R6.** Six, J. (2021). Panako 2.0—Updates for an acoustic fingerprinting system. *ISMIR Late-Breaking/Demo*. [Proceedings contribution](https://archives.ismir.net/ismir2021/latebreaking/000039.pdf). Context for the software family; the OLAF-specific references are R11 and R12.
- **R7.** El-Yaniv, R., and Wiener, Y. (2010). On the Foundations of Noise-free Selective Classification. *Journal of Machine Learning Research*, 11, 1605–1641. [Journal article](https://jmlr.org/papers/v11/el-yaniv10a.html).
- **R8.** KDE. *Kdenlive 26.08 Manual: Right-Click Menus*, "Set Audio Reference" and "Align Audio to Reference." [Official documentation](https://docs.kdenlive.org/en/cutting_and_assembling/right_click_menu.html), accessed 2026-09-20. The evaluated executable was 26.08.1; this is documentation, not a research paper.
- **R9.** Wang, Y., Getreuer, P., Hughes, T., Lyon, R. F., and Saurous, R. A. (2017). Trainable frontend for robust and far-field keyword spotting. *ICASSP*, 5670–5674. [Author publication page](https://getreuer.info/papers/wang2017trainable/index.html).
- **R10.** FitzGerald, D. (2010). Harmonic/Percussive Separation Using Median Filtering. *DAFx*. [Proceedings paper](https://dafx.de/paper-archive/2010/DAFx10/DerryFitzGerald_DAFx10_P15.pdf).
- **R11.** Six, J. (2020). OLAF: Overly Lightweight Acoustic Fingerprinting. Extended abstracts for the Late-Breaking Demo Session of the 21st International Society for Music Information Retrieval Conference (ISMIR 2020). [Venue string verified in the author's repository bibliography](https://github.com/JorenSix/Olaf/blob/master/paper.bib); no page numbers claimed.
- **R12.** Six, J. (2023). Olaf: a lightweight, portable audio search system. *Journal of Open Source Software*, 8(87), 5459. [DOI](https://doi.org/10.21105/joss.05459).
- **R13.** Ramona, M., and Peeters, G. (2011). Automatic Alignment of Audio Occurrences: Application to the Verification and Synchronization of Audio Fingerprinting Annotation. *Proc. 14th Int. Conference on Digital Audio Effects (DAFx-11)*, Paris, France, DAFX-429–DAFX-436. [Proceedings PDF](https://www.dafx.de/paper-archive/2011/Papers/94_e.pdf).
- **R14.** Ramona, M., Fenet, S., Blouet, R., Bredin, H., Fillon, T., and Peeters, G. (2012). A Public Audio Identification Evaluation Framework for Broadcast Monitoring. *Applied Artificial Intelligence*, 26(1–2), 119–136. [DOI](https://doi.org/10.1080/08839514.2012.629840).
