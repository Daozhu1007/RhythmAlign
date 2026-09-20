STATUS: TECHNICAL-CORE DRAFT — BENCHMARK COMPLETE; CREATOR FEASIBILITY PILOT NOT CONDUCTED.

# Reliable Reference-Audio Replacement for Noisy User-Generated Video: Design and Evaluation of a Selective Alignment System

Working manuscript, PAPER-DRAFT-0. Not submission-ready. Numeric authority: [final reporting v2](../../../../experiments/applied_system/final_pack/results/final_benchmark_reporting_v2.json), sealed at repository commit `9605c21127d14d72922593a7990571d48a461bb2`. Companion [tables](PAPER_TABLES_V0.md), [claim ledger](CLAIM_LEDGER_V0.md), and [citation gaps](CITATION_GAPS_V0.md) preserve the evidence and revision boundaries.

## Abstract

Replacing degraded captured audio in user-generated video with a clean reference requires both accurate timing and a decision about whether a proposed placement is supported. An always-output estimator can return a precise-looking offset even when the reference is wrong. We evaluate frozen RhythmAlign v1.2.0 as a selective alignment system for this task, using rhythm-game handcam-style acoustic recording as the stress-test domain. A performance-blind source selection and dual-marker timing protocol produced 24 dependent positive takes from 10 source identities and 24 constructed wrong-reference pairs; no thresholds were tuned on final data. At a 100 ms correctness tolerance, RhythmAlign achieved 20/24 acceptance coverage and 20/24 correct-placement yield (both 83.3%), with accepted risk 0/20 and wrong-reference false accepts 0/24. Always-output GCC-PHAT and normalized cross-correlation accepted all positives, with correct-placement yields of 10/24 and 19/24, respectively, and each accepted all 24 wrong references. Panako under its native shipped settings achieved 2/24 correct-placement yield with 0/24 wrong-reference false accepts. In a separate, single-operator Kdenlive technical stratum, 2/10 placements were correct. These observations concern one domain and one frozen operating point, not calibrated future risk or creator workflow benefit. The measured distinction was the systems' behavior on unsupported placements, rather than the precision of their successful matches; the cost of recovering from refusal remains unmeasured.

## 1. Introduction

User-generated video can capture music through loudspeakers, room acoustics, consumer microphones, background sound, and physical impacts. A creator with access to the corresponding clean reference may want to replace the captured soundtrack while retaining the video's timing. This requires estimating where the reference belongs on the recording timeline. A numerically specific offset is insufficient: it must describe the intended recording and the correct occurrence of its content.

An incorrect automatic placement can create additional checking and repair work, or survive into an export. Refusal leaves work unfinished but exposes uncertainty before placement. The relative cost of these outcomes depends on the workflow; this study measures alignment decisions and correctness, without claiming that refusal saves creator time. We use “reliable” as an operational design objective: report accepted-case errors together with how much work receives a placement, and account explicitly for mismatched references. It is not a universal property certified by the system's scores.

Rhythm-game handcam recording motivates a demanding test domain because musical playback coexists with taps, interference, and repeated musical structure. The final data are fresh acoustic rerecordings under handcam-style conditions, including tapping performed during playback. They are not a population sample of authentic arcade videos. The broader problem is selective reference-audio replacement; neither game-specific processing nor a new alignment algorithm is claimed.

Our bounded contributions are:

1. A reproducible fresh-acoustic benchmark protocol with system-independent marker timing, source-exposure exclusions, and an explicit wrong-reference stratum.
2. An evaluation of frozen RhythmAlign v1.2.0 against always-output correlation baselines and native Panako matching, supplemented by a separately scored editor-native Kdenlive stratum.
3. Evidence, within this benchmark, that accounting for refusal and erroneous outputs changes the interpretation obtained from successful-placement precision alone.

## 2. Related Work

### 2.1 Correlation and audio synchronization

Delay estimation by correlation is established signal processing. Knapp and Carter's generalized correlation framework includes frequency weighting for time-delay estimation [R1]. GCC-PHAT supplies our phase-weighted, always-output control. Normalized cross-correlation addresses signal-amplitude and overlap effects; Lewis provides classical normalization background [R2]. Our frozen NCC implementation normalizes by the energy of the overlapping samples at each lag. It is not represented as an exact implementation of Lewis's locally mean-subtracted image-template statistic.

Audio synchronization also extends beyond a single fixed offset. Ewert, Müller, and Grosche combine chroma and onset information for high-resolution synchronization [R3]. Six and Leman use acoustic fingerprints and refinement for multimodal recording synchronization [R4]. Their work and the associated SyncSink software precede the integration of alignment into an accessible workflow. Our task is narrower than general performance alignment with tempo changes, drift compensation, or dropped-sample repair.

### 2.2 Fingerprinting and occurrence matching

Wang's Shazam-style landmark matching provides an established audio-identification precedent [R5]. Panako is an available acoustic-fingerprinting implementation; its 2021 update is a late-breaking/demo contribution [R6]. The benchmark uses the OLAF strategy within a pinned Panako implementation, not an assertion that the separate PANAKO strategy or every configuration described by that publication was evaluated. [CITATION TODO: C1 — OLAF-specific primary method reference and complete metadata for the evaluated strategy.]

Fingerprint occurrence matching can support synchronization, but a detected occurrence and a whole-reference placement are different output contracts. Here the native match coordinates define the proposed offset without a research-added refinement or acceptance threshold. Earlier occurrence-alignment work also motivates checking support across time. [CITATION TODO: C2 — complete bibliographic metadata and passage check for Ramona and Peeters, Automatic Alignment of Audio Occurrences (2011), identified in the committed prior-art audit.] These precedents preclude treating evidence combination or temporal support as our algorithmic invention.

### 2.3 Refusal and editor-native synchronization

Selective classification formalizes the trade-off between coverage and error on accepted cases [R7]. We borrow that evaluation distinction, without importing classification guarantees into a heuristic audio system. A single frozen decision policy is measured; no risk-control theorem, probability calibration, or optimal operating point is established.

Native editing tools are practical alternatives. Kdenlive documents setting an audio reference and aligning another timeline clip to it [R8]. This motivates a technical stratum using the actual editor and saved project placements. It does not substitute for measuring creator recovery or end-to-end editing effort.

## 3. System

RhythmAlign v1.2.0 accepts a degraded recording and a clean reference and estimates a constant reference-start offset on the recording timeline. A positive offset delays the reference; a negative offset trims its beginning. The production pipeline decodes audio and forms complementary representations: chroma-change/onset evidence, onset-strength evidence, and per-channel energy normalization (PCEN), with and without harmonic/percussive separation (HPSS). PCEN and median-filter HPSS are established ingredients [R9, R10]. Their use here is an implementation choice.

Candidate offsets from correlation peaks are clustered. The decision policy checks feature strength, competing placements, geometric overlap, and corroborating evidence. Plain PCEN and PCEN with HPSS belong to the same evidence family; they are not independent votes. Onset agreement corroborates a primary candidate rather than supplying proof of independent support. The frozen temporal-support check additionally examines whether the deciding PCEN correlation is concentrated in a short portion of the overlap. The released rule uses nominal one-second bins and rejects a strongest-bin share above 0.25; the rule was selected on development material and was unchanged for this evaluation. This is a heuristic safeguard, not a calibrated probability of correctness.

The engine emits `ACCEPT` with an offset or `ABSTAIN` with a reason. An accepted decision can be inspected in Analyze Only or used by the export workflow to place the reference and produce an MP4 through FFmpeg. Normal export stops after abstention. Analyze Only and Full Export share the same alignment decision, so the benchmark scores it once. Export capability describes the system; the benchmark does not establish completed creator tasks or perceptual audiovisual quality.

The evaluated production commit is `3a622fc33af1212178296ad9dad57ce9693eed48` (v1.2.0). Reproduction is defined by that code and its defaults, not by retuning the prose description. The [implementation](../../../../alignment_engine_v2.py) and [frozen runner](../../../../experiments/applied_system/runners/rhythmalign_runner.py) provide the exact system contract.

## 4. Evaluation Method

### 4.1 Research questions

**RQ1:** On fresh acoustic data, does the frozen selective system produce fewer catastrophic wrong placements than the specified always-output baselines?

**RQ2:** What correct-placement yield accompanies that selective policy?

**RQ3:** How do native fingerprint matching and editor-native synchronization behave under the measured placement task?

“Catastrophic” denotes unsupported placement, including any accepted wrong reference and the large positive-placement errors observed here. It is not a new severity threshold fitted to the data; formal scoring uses the frozen correctness tolerance and no-match labels.

### 4.2 Fresh source selection

The exclusion ledger removes historical development, spent holdout, shakedown, and acoustic-pilot identities. Selection checked identity aliases and file hashes as well as decoding suitability, so a renamed or re-encoded source did not become fresh merely through a different filename. Freshness is relative to the documented development exposure history, not a claim that no algorithm developer has ever encountered these songs.

The declared source-only rule selected ten reference identities. Three were deliberately chosen for high long-lag recurrence; remaining slots and ordering followed deterministic hash rules. A separate interference identity was selected outside the reference and exclusion pools using source texture. Recurrence was a selection heuristic, not a validated difficulty measure. No comparator output entered source selection, recording allocation, or acquisition QC. Sources and exact versions were frozen before system execution. See [source selection](../FINAL_SOURCE_SELECTION.md).

### 4.3 Acoustic acquisition

The primary set comprises 24 positive takes from ten sources: ten ordinary, three low-level, three tap-dominant, four interference, two partial, and two device-variation takes (Table 1). Acquisition covered three sessions, two rooms, and two recording devices, with two further strict repeats kept separate. These are actual microphone recordings of loudspeaker playback, not clean music digitally inserted into noise. The owner attested the prescribed conditions; taps were performed during playback and interference came from separate playback. Room, device, session, and condition were not fully crossed, so condition effects cannot be isolated causally.

Playback buffers used a 60 s source segment. Partial buffers began inside the source rather than at its beginning; ground truth therefore includes the source slice's start time. The references remained the corresponding full sources. The two strict repeats repeated the ordinary takes for S01 and S02 and were neither primary replacements nor extra independent songs. All 26 recordings passed frozen acquisition QC. Optional authentic-handcam, version-mismatch, and external-domain strata do not contribute evidence to this draft.

### 4.4 Independent timing ground truth

Each sample-exact playback buffer contained a 0.75 s linear chirp spanning 1–9 kHz, a 1 s guard, the music payload, another 1 s guard, and a second chirp, rendered at 48 kHz. Marker peak amplitude was 0.9. A normalized matched filter located full-template candidates; one-template nonmaximum suppression and the frozen confidence threshold `0.163837792269` were applied. Exactly two accepted markers were required. The final protocol supersedes the earlier study design's tentative single-marker rule.

Let the two marker starts in buffer time be b1 and b2, and their detected recording times be r1 and r2. The map t(b) = r1 + (b − b1)(r2 − r1)/(b2 − b1) locates the payload on the recording clock. Drift was checked against ±128.486056 ppm and marker mapping disagreement against 10 ms; the trajectory gate was frozen off. Mapping agreement after the two-marker fit is a consistency check, not an independent precision estimate. Captured payload samples were never warped or time-stretched.

Marker and guard holes were removed with the frozen 50 ms external margins; retained segments were concatenated and a leakage scan applied. Timing labels were transferred to that trimmed timeline by subtracting removed samples. The reference-start offset equals the retained payload-start time minus the source slice start. Every comparator received hash-identical trimmed input and reference files, while retaining its own native internal decoding behavior. Markers were label machinery and were not available as alignment cues.

The frozen QC record also contains a marker-independent direct-correlation diagnostic. It did not gate inclusion or replace marker labels; agreement with that diagnostic is not promoted into independent confirmation of a correlation comparator. `GT_FAILED` would have been a retained protocol failure, excluded from alignment metrics with a blind reason; no final take required replacement. Full details are in the [protocol](../FINAL_BENCHMARK_PROTOCOL.md) and [acquisition QC](../FINAL_ACQUISITION_QC.md).

### 4.5 Comparators

**RhythmAlign** used its native frozen `ACCEPT`/`ABSTAIN` decision once per pair. **GCC-PHAT** (`gcc_phat_argmax_v1`) used phase-weighted correlation and returned its argmax. **NCC** (`ncc_argmax_v1`) used per-lag overlap-energy normalization and returned its argmax. The latter two have no native rejection rule in the evaluated implementations. We did not invent thresholds to make them selective, nor interpret output specificity as probabilistic confidence.

**Panako** used the pinned source commit `e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211`, its recorded binary hash, and the OLAF strategy at shipped settings. Each case used a fresh reference store. Native outputs were `ACCEPT`, `NO_MATCH`, or `ERROR`; the highest native match score supplied the match, and placement was query start minus match start. Empty matching output remained `NO_MATCH`. No hybrid refinement or final-data tuning was added.

**Kdenlive 26.08.1** was operated by the owner on ten preselected positive pairs spanning the conditions. Native audio-reference alignment was followed by saving the project; relative clip placement was extracted from its XML and scored against the frozen labels. The ten-pair axis remains separate from the automated 24-positive axis and has no wrong-reference result. It measures one operator's technical runs, not a user study.

### 4.6 Wrong-reference protocol

Each primary take numbered i was offered reference slot S((i mod 10) + 1). This is a rotation over the take index, not a post-result choice of the most confusing source. The assignments were frozen before source identities were filled and verified to differ from each take's true source. There are 24 directed wrong-reference pairs, reusing the primary recordings. Any accepted placement is `WRONG_ACCEPT`; refusal is `SAFE_ABSTAIN`. There is no true offset for a mismatched reference, so output magnitudes are not offset errors.

### 4.7 Metrics and independence

An accepted positive is `CORRECT_ACCEPT` when absolute offset error is at most 100 ms, and `WRONG_ACCEPT` otherwise. The predeclared sensitivity tolerances are 50 and 150 ms. These are scoring tolerances, not an independently established perceptual synchrony threshold.

- **Acceptance coverage:** accepted placements / primary positives.
- **Correct-placement yield:** `CORRECT_ACCEPT` / primary positives.
- **Accepted risk:** `WRONG_ACCEPT` / accepted positive placements; undefined if no positive is accepted.
- **Wrong-reference false-accept rate:** accepted wrong references / wrong-reference cases.
- **Conditional CORRECT_ACCEPT error:** absolute-error distribution restricted to correct accepts, reported alongside the distribution of all produced positive placements.

Source identity is the independence unit. The 24 within-song takes are dependent, and constructed negatives share both recordings and the reference pool. Raw denominators are primary. The frozen source-cluster bootstrap resamples ten identities for 10,000 replicates with seed 20260920, calculating rates within each resample. Its intervals are descriptive aids, not evidence of population equivalence, significance, or calibrated future risk. No new inferential test or analysis is introduced here.

### 4.8 Frozen evaluation policy and corrections

An internal preregistration-like protocol fixed sources, exclusions, sample counts, conditions, pairings, software identities, decision semantics, and scoring before final runs. It was not an externally registered preregistration. Final outcomes were not used to tune thresholds. The owner-operated Kdenlive evidence was sealed before automated comparator execution; raw outputs and their hashes were retained.

Two outcome-independent corrections are preserved in the evidence chain. First, the initial Kdenlive procedure placed clips at timeline zero, preventing leftward placements. The uniform replacement procedure provided 180 s of headroom, derived from frozen input lengths; original pair01 was retained as void evidence and pair01r2 supplied its scored placement. Second, the XML reader was corrected to handle nested track structures and chain resources uniformly before Kdenlive scoring; its original erroneous failure output remains archived. Neither correction used ground-truth agreement to choose placements. Pair01r2's missing timer record was documented without imputation or a timing rerun.

The subsequent reporting audit preserved raw results while separating acceptance coverage from correct-placement yield, correcting NCC's accepted-risk denominator, labeling the successful-placement error distribution correctly, and expressing wrong-reference bootstrap uncertainty as rates. All paper-facing metrics use reporting v2. These are versioned reporting corrections, not revised outcomes.

## 6. Results

The automated benchmark contains 200 stored system records across primary positives, wrong references, and separate repeats, with no runner errors. Reporting v2 governs the main metrics, error distributions, bootstrap summaries, repeats, and Kdenlive totals. Condition and source counts not duplicated in v2 are taken from the linked immutable final-results artifact; no mislabeled legacy derived metric is used.

**Table 2. Main results at 100 ms.** Acceptance coverage, correct-placement yield, and accepted risk concern the 24 primary positives. The last column concerns the separate 24 wrong-reference pairs.

| System | Acceptance coverage | Correct-placement yield | Accepted risk | Wrong-ref false accept |
|---|---:|---:|---:|---:|
| RhythmAlign v1.2.0 | 20/24 (83.3%) | 20/24 (83.3%) | 0/20 (0%) | 0/24 (0%) |
| GCC-PHAT argmax | 24/24 (100%) | 10/24 (41.7%) | 14/24 (58.3%) | 24/24 (100%) |
| NCC argmax | 24/24 (100%) | 19/24 (79.2%) | 5/24 (20.8%) | 24/24 (100%) |
| Panako OLAF | 2/24 (8.3%) | 2/24 (8.3%) | 0/2 (0%) | 0/24 (0%) |

### 6.1 Positive alignment

RhythmAlign returned 20 correct placements and four abstentions, without an observed wrong positive placement. GCC-PHAT produced ten correct and fourteen wrong placements; NCC produced nineteen correct and five wrong placements. Panako produced two correct placements and 22 no-match outputs. Acceptance coverage and correct-placement yield coincide for RhythmAlign and Panako only because every positive they accepted was correct here. The always-output systems' acceptance coverage is 100%, regardless of their lower correct-placement yields.

The frozen source-bootstrap 95% descriptive intervals for correct-placement yield are [0.60, 1.00] for RhythmAlign, [0.17, 0.70] for GCC-PHAT, [0.63, 0.95] for NCC, and [0.00, 0.19] for Panako. These wide intervals and the source dependence limit generalization. Table 4's source panel records the underlying counts; the descriptive comparison does not establish a population ranking.

### 6.2 Wrong-reference safety

RhythmAlign refused all 24 constructed wrong-reference pairs, giving 0/24 false accepts. Panako likewise gave 0/24. GCC-PHAT and NCC each returned a placement for every wrong reference, giving 24/24 under their native always-output semantics. These counts answer the no-match challenge, not the frequency with which creators select wrong files.

The wrong-reference rate-bootstrap intervals are [0, 0] for RhythmAlign and Panako and [1, 1] for both always-output baselines. They are degenerate because each source resample reproduces uniform observed behavior; they do not bound unobserved future risk. For wrong references, the median absolute output offsets were 64.2 s for GCC-PHAT and 104.5 s for NCC, with maxima 132.7 s and 155.6 s. These are output magnitudes, not errors against a nonexistent true placement.

### 6.3 Placement error

Every CORRECT_ACCEPT placement was below 25 ms. Among correct positive placements, median errors were 7.9 ms for RhythmAlign, 0.22 ms for GCC-PHAT, 3.8 ms for NCC, and 15.1 ms for Panako (Table 3). This conditioning excludes the unsuccessful outputs and differs across systems.

Across all produced positive placements, GCC-PHAT's median error was 29.3135 s and its maximum was 184.1055 s; NCC's median was 0.0039 s but its maximum was 153.3829 s. Thus even a small all-output median can conceal severe wrong placements. RhythmAlign's all-produced maximum was 0.0157 s and Panako's was 0.0219 s because neither had wrong positive accepts in this set. Both conditional and all-produced distributions, with denominators, are retained in Table 3. Automated and Kdenlive outcome counts are unchanged across the frozen 50/100/150 ms grid. This is tolerance sensitivity, not a sweep of acceptance thresholds.

### 6.4 Condition-level observations

RhythmAlign's correct-accept/refusal counts were 9/1 ordinary, 3/0 low-level, 3/0 tap-dominant, 2/2 interference, 2/0 partial, and 1/1 device variation. These are raw counts within conditions, not numerator/denominator rates; Table 4 gives each condition's denominator and all comparator outcomes. The small, dependent cells support no subgroup inference.

All four RhythmAlign abstentions occurred on S08 (Cryptarithm: final08 and final18) and S10 (Straight into the lights: final20 and final24), two sources flagged as repetitive before evaluation. S08 yielded 0/2 correct placements with two refusals, S10 yielded 1/3 with two refusals, and the third flagged source S09 yielded 3/3. This records a concentration of refusals, not proof that repetition caused them or that all repetitive sources fail.

### 6.5 Strict repeats

The two additional takes support observations only (Table 6). RhythmAlign accepted both originals and repeats, with changes in signed error relative to each take's own ground truth of +7.8 ms and +14.0 ms. Those are error changes, not raw offset movements: independent recording starts shift the appropriate reference position. Its raw output movements were 0.5573 s and 0.1161 s.

For repeat02, GCC-PHAT remained `ACCEPT` while changing from a correct original to a wrong repeat; its output moved 67.2049 s. NCC also remained `ACCEPT` but changed from a wrong original to a correct repeat, with 60.4599 s movement. GCC-PHAT's repeat01 and original were both wrong by about 61.9 s. Decision-state agreement therefore does not establish placement repeatability or correctness. Panako returned `NO_MATCH` for both repeats of originals it had accepted. No reliability rate or population repeatability conclusion is inferred from two repeats.

### 6.6 Kdenlive technical stratum

Kdenlive produced two correct and eight wrong placements among ten valid scoring pairs, with zero native failures (Table 5). Counts are identical at the three scoring tolerances. Pair02 and pair10 were correct, with errors of 5.3 ms and 0.1 ms; the wrong-placement errors ranged from approximately 0.85 s to 149.4 s. This separates successful operation of the native command from correct placement.

Nine valid runs have recorded operator times: median 58.6 s, interquartile range 45.1–60.7 s, total 551.5 s. Pair01r2 lacks a timer record and is not imputed. The void original pair01 contributes neither a placement nor a time to these summaries. These are times for one operator's technical procedure, not comparative creator task times, recovery costs, or HCI evidence.

## 7. Discussion

On this benchmark, frozen RhythmAlign reduced observed wrong placements relative to the specified always-output correlation baselines while retaining 20/24 correct-placement yield. Successful correlation matches could be more precise than RhythmAlign's successful matches; that precision did not describe their large-error tails or their behavior when the reference was wrong. Reporting only successful offsets would therefore miss the principal practical separation.

Refusal is visible unfinished work. RhythmAlign's four positive abstentions concentrated on two preflagged repetitive sources, while the other preflagged repetitive source was accepted throughout. The result is consistent with selective handling of difficult evidence, but this system-level benchmark cannot assign causality to any individual gate. There was no final ablation, and we do not attribute the measured advantage specifically to the temporal-support safeguard.

Panako was conservative on this task at its native shipped settings: it accepted two positives and no wrong references. This does not establish that fingerprinting is generally weak, that the PANAKO and OLAF strategies are interchangeable, or that another configuration would have the same yield. Conversely, GCC-PHAT and NCC expose the consequence of returning an argmax without a refusal mechanism; their measurements do not show that correlation cannot support a selective detector. Adding such a detector would define a different system requiring its own independent evaluation.

Kdenlive's separate technical stratum shows that editor-native synchronization was not automatically a successful substitute on these measured pairs. The comparison is bounded by the selection, editor version, procedure, and single operator. Its denominator cannot be compared as if it were the automated full set, and its recorded times cannot establish that RhythmAlign saves editing effort.

### 7.1 Unmeasured cost of abstention

The benchmark measures when the system refuses, but not the time or effort required for a creator to recover from that refusal. A predesigned 2-creator feasibility pilot exists but was not conducted for this benchmark-first draft. There are no pilot results, observed recovery paths, interface-understanding measurements, or creator task-time estimates to report. The unrun design is not evidence that refusal is inexpensive or understandable.

## 8. Limitations

The ten source identities limit the empirical population. Multiple takes from the same song are dependent, and room, device, session, and condition covary. Source selection was deliberately structured for stress testing rather than random sampling. All magnitudes concern one domain and controlled handcam-style acoustic capture; there is no external-domain confirmation or separate authentic-handcam confirmation in this draft.

The wrong-reference cases are constructed directed pairs drawn from the reference pool. They test rejection of known mismatches, not deployment prevalence, every possible wrong reference, or confusion between versions of the same song. Zero observed wrong accepts does not certify future risk, calibrate the scores, or establish a safe-export guarantee.

Only one frozen operating point was evaluated. There was no final threshold sweep, no feature ablation, and no basis for claiming an optimal risk-coverage trade-off. Panako used native shipped OLAF settings only. Kdenlive used one version, one operator, and ten pairs, with one missing timer. Only two strict repeats were available. These design limits prevent broad comparator rankings and repeatability claims.

Independent marker timing avoids deriving labels from any evaluated system, but does not eliminate acoustic, clock, or decoding uncertainty. The named exact-GT stratum is protocol-valid marker timing, not a claim of physically exact zero-uncertainty labels. Tiny differences among successful sub-millisecond and millisecond errors should not be treated as perceptual or universal precision rankings.

There has been no creator workflow or usability study for this draft. Abstention recovery cost, end-to-end task completion, effort savings, preference, and understanding of decisions remain unmeasured. Kdenlive technical operation and software export capability do not fill this evidence gap.

## 9. Reproducibility

The evidence package retains frozen source and acquisition manifests, source hashes, QC records, pair assignments, comparator identities/configurations, raw per-pair outputs, SHA-256 sidecars, and deterministic aggregation code. The reporting-v2 artifact identifies the hashes of its immutable raw assembly and original aggregate. It separates corrected terminology from preserved historical files. The paper's [validation script](validate_paper_v0.py) checks the tables and abstract against these records without executing a comparator or accessing audio.

Source and capture media include commercial music and are not committed for unrestricted redistribution. Hashes and metadata support provenance but cannot replace authorized access to the exact media for reproduction. Any reviewer-access arrangement remains subject to permission; this draft does not claim that such access has already been arranged. Existing synthetic fixtures can validate scoring, timing, and project parsing without commercial audio, but carry no fresh acoustic performance evidence. An openly licensed performance replacement dataset has not been supplied by this study.

## 10. Conclusion

Fresh acoustic evaluation of frozen RhythmAlign v1.2.0 yielded 20/24 correct positive placements, four refusals, and no observed false accepts among 24 constructed wrong-reference pairs. The findings are bounded by ten sources, dependent takes, one stress-test domain, and one operating point. Creator recovery costs remain open. For this benchmark, the main robustness distinction was not millisecond-level precision after a successful match, but whether the system refused unsupported placements.

## References

Entries below use metadata already present in committed literature notes; the citation ledger records live verification limits. Missing strategy-specific and occurrence-alignment metadata remain explicit TODOs rather than invented references.

- **R1.** Knapp, C. H., and Carter, G. C. (1976). The generalized correlation method for estimation of time delay. *IEEE Transactions on Acoustics, Speech, and Signal Processing*, 24(4), 320–327. [DOI](https://doi.org/10.1109/TASSP.1976.1162830).
- **R2.** Lewis, J. P. (1995). Fast Template Matching. *Vision Interface*, 120–123. [Expanded author treatment: Fast Normalized Cross-Correlation](https://scribblethink.org/Work/nvisionInterface/nip.html).
- **R3.** Ewert, S., Müller, M., and Grosche, P. (2009). High Resolution Audio Synchronization Using Chroma Onset Features. *ICASSP*, 1869–1872. [Institution-hosted paper](https://resources.mpi-inf.mpg.de/MIR/SyncRWC60/2009_EwertMuellerGrosche_HighResAudioSync_ICASSP.pdf).
- **R4.** Six, J., and Leman, M. (2015). Synchronizing multimodal recordings using audio-to-audio alignment: an application of acoustic fingerprinting to facilitate music interaction research. *Journal on Multimodal User Interfaces*, 9(3), 223–229. [Institutional record](https://biblio.ugent.be/publication/6873558); [author manuscript](https://0110.be/files/attachments/434/2015.synchronized-recording.pdf).
- **R5.** Wang, A. L. (2003). An Industrial-Strength Audio Search Algorithm. *ISMIR*. [Paper listed in committed literature notes](https://www.ee.columbia.edu/~dpwe/papers/Wang03-shazam.pdf).
- **R6.** Six, J. (2021). Panako 2.0—Updates for an acoustic fingerprinting system. *ISMIR Late-Breaking/Demo*. [Proceedings contribution](https://archives.ismir.net/ismir2021/latebreaking/000039.pdf). This is context for the software family, not a substitute for the missing OLAF-specific reference.
- **R7.** El-Yaniv, R., and Wiener, Y. (2010). On the Foundations of Noise-free Selective Classification. *Journal of Machine Learning Research*, 11, 1605–1641. [Journal article](https://jmlr.org/papers/v11/el-yaniv10a.html).
- **R8.** KDE. *Kdenlive 26.08 Manual: Right-Click Menus*, “Set Audio Reference” and “Align Audio to Reference.” [Official documentation](https://docs.kdenlive.org/en/cutting_and_assembling/right_click_menu.html), accessed 2026-09-20. The evaluated executable was 26.08.1; this is documentation, not a research paper.
- **R9.** Wang, Y., Getreuer, P., Hughes, T., Lyon, R. F., and Saurous, R. A. (2017). Trainable frontend for robust and far-field keyword spotting. *ICASSP*, 5670–5674. [Author publication page](https://getreuer.info/papers/wang2017trainable/index.html).
- **R10.** FitzGerald, D. (2010). Harmonic/Percussive Separation Using Median Filtering. *DAFx*. [Proceedings paper](https://dafx.de/paper-archive/2010/DAFx10/DerryFitzGerald_DAFx10_P15.pdf).
