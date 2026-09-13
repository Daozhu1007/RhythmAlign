# RhythmAlign Repo-Wide Paper Opportunity Audit

## 1. Owner-Level Verdict

**MODEST_PAPER_ROUTE_EXISTS**

**YES.** RhythmAlign can realistically become the owner's first legitimate research paper. The strongest practical route is an **applied-system paper with a focused comparative evaluation of rhythm-game handcam editing**. Its contribution would be evidence about when an implemented, selectively automated workflow helps creators complete correct audio replacement, including the cost of refusal and recovery. That question does not require a new signal-processing algorithm. It does require observations beyond the developer's own successful exports.

The current project is a substantial starting artifact, not a completed paper. It has a released application, explicit acceptance/refusal behavior, an export pipeline, diagnostics, tests, and unusually detailed exploratory research. What it lacks is independently labeled contemporary task data and a comparison with an existing editor's automatic synchronization and ordinary manual editing. A small study can support bounded findings about these workflows; it cannot establish universal robustness, rare-error safety, or state-of-the-art alignment.

The narrow **STOP_ENGINEERING_ONLY** verdict remains valid. Neither temporal-support verification nor the combination of PCEN, HPSS, chroma, onsets, correlation and rejection is a defensible new-method thesis here. This audit recommends a different contribution and a lower, appropriate publication target. The expected outcome is a legitimate modest paper, with stronger student work possible if the evaluation is convincing. Acceptance is not assured, and no finished result is being predicted.

## 2. What RhythmAlign Actually Contributes

### Verified subject and evidence boundaries

Git and public release state were checked on **2026-09-13**, using local object inspection, `git ls-remote origin`, and the GitHub latest-release API. The working branch was already `astra/repo-wide-paper-audit`, initially clean and at the same commit as `main`. Research branches were read through their Git objects, without checkout or merging.

| Subject | Verified identity | Interpretation |
|---|---|---|
| Local and remote `main` | `91bc50c0a117b38176ec93b44b9e0d1b8aaf749d` | Current primary subject |
| Local and remote `v1.2.0` tag | `3a622fc33af1212178296ad9dad57ce9693eed48` | Lightweight release tag; production source is unchanged between tag and main |
| Post-tag difference | One release-record document, 101 added lines | No post-release algorithm change |
| Exploratory research branch | `8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e` | Final formal exploratory study; scientific baseline was `ffa6b07a591dbdb54ae8350f3d27dce3ed74c847` |
| v1.2.0 provenance/triage branch | `2c1fb6d818d12b20ac3e49fc0fae059627ec6f55` | Contains the later STOP_ENGINEERING_ONLY assessment |
| Public latest release | v1.2.0, published 2026-09-12 22:36:43 UTC | Neither draft nor prerelease; installer and portable ZIP listed |

The architecture review covered the complete tracked main tree: production modules, both workflows, locales, export and update code, release/build definitions, tests, experiment packages, and RA-1.2A/B/C/D/D1/E records. This is an audit of source and preserved evidence; the application, benchmarks, and historical tests were not rerun. The separate RhythmAlign-Research repository was neither inspected nor used. The public release's existence was checked; its binaries were not downloaded or independently revalidated. [Release][r-release], [final release record][r-e].

### Algorithm

RhythmAlign estimates **one constant placement offset** between a selected clean recording and audio captured with a handcam video. The underlying assumption is that the intended recording occurs with compatible speed and structure. Unknown edits, substantial clock drift, alternate versions and repeated occurrences can violate that assumption. There is no source-separation model, tempo correction, visual hand-motion alignment, or inference of the creator's intended song.

FFmpeg decodes both inputs to mono PCM, normally at 22,050 Hz. Four methods supply candidate offsets in three named families: a chroma-difference/onset hybrid, onset correlation, and plain-PCEN/PCEN-with-HPSS spectral correlation. Candidate clustering, strength and margin floors, possible-overlap checks and competitor checks select ACCEPT or ABSTAIN. The D1 post-check rejects an otherwise accepted placement if its deciding PCEN member's strongest nominal one-second bin contributes more than 0.25 of total signed correlation. These are implemented decision heuristics, not calibrated probabilities. [Engine v2][r-engine], [decoding/export module][r-auto].

The scientific distinction matters: the nominal 30-second overlap is available timeline intersection. The concentration check bounds one attribution ratio; it does not prove matching content throughout that intersection. Adjacent supporting bins can pass, and signed cancellation affects the ratio. Different feature families are correlated views of the same audio. The README's language about independent evidence and support spread across the song is therefore stronger than the demonstrated mathematical contract. A paper must use the narrower description without changing the released software. [Current README][r-readme], [scientific triage, §6][r-triage].

### System

| Component | What actually exists | Research relevance and boundary |
|---|---|---|
| Input and decoding | Video/reference selection, drag and drop, FFmpeg conversion, temporary-file cleanup | Accepts ordinary media files; no audio means there is no acoustic basis for automatic alignment |
| Candidate/evidence layer | Reusable engine entry points, structured decisions, cluster/evidence summaries | Makes failures and policy behavior inspectable |
| Refusal | Default GUI worker branches on v2's decision; ABSTAIN stops export with localized reasons | Explicit operational refusal; does not guarantee that every ACCEPT is correct |
| Analyze Only | Same default engine, signed numeric offset on success, nonnumeric refusal state otherwise | Supports subsequent work in an existing editor; not an independent verifier |
| User adjustment | Original/reference volume controls, presets, post-accept ±500 ms adjustment | Supports mixing and fine correction; cannot recover arbitrary placement after ABSTAIN |
| Export | Delay or trim reference; mix with original audio; default video stream copy and AAC audio; optional re-encoding | Completes the user's output task, with a temporary destination replaced after successful FFmpeg completion |
| Diagnostics | Copyable environment/settings/log report and separate CLI audio diagnostics | Useful for reproducibility and support; diagnostic output is not timing ground truth |
| Deployment | PyQt interface, English/Chinese locales, installer/portable build definitions, update manifest and SHA256 checks | Enables evaluation with creators who do not run Python; packaging is enabling infrastructure |
| Validation | Tests of decision behavior, refusal/export integration, offset signs, output cleanup, localization and updates | Checks executable contracts, not population accuracy or workflow usefulness |

The default path is in `BaseMediaWorker` in the [GUI module][r-ui]; it calls `find_offset_v2` without a silent legacy fallback. The legacy aligner remains in the repository. In particular, [the CLI diagnostic][r-diagnose] examines chroma correlation and does not reproduce the complete v2 acceptance policy. [The environment report][r-diagnostics] identifies the engine and dependencies but is not a scientific experiment log. An export helper can handle a video without original audio once an offset is supplied; that capability must not be misdescribed as automatic synchronization of silent videos.

### Empirical assets

The project contains a genuine exploratory investigation: hypotheses, null experiments, strong simple baselines, deliberate mismatches, exhaustive mismatch grids, evidence attribution, interventions, and corrections to favorable historical interpretations. The pre-D1 **22/380 directed clean wrong-song ACCEPTs** represent 11 unordered pairs. The localized regression attributed about **94.6% of net signed plain-PCEN correlation** to approximately one second. This is an existence result plus mechanism investigation in a specified implementation, not a current release failure rate. [Exploratory study][r-explore].

D1 and the release records document rejecting the discovered clean failures while retaining 55 previously accepted positives. That latter denominator combines 26 exact-insertion cases and 29 real pairing cases; it is not 55 independently timed natural recordings. The record of **80 passing tests** is a historical release check, not a new result from this audit. The later triage supplies the more careful interpretation of these facts. [D1 report][r-d1], [fact sheet][r-facts], [release record][r-e].

### Application/domain

The concrete workflow is replacing noisy rhythm-game handcam music while preserving its placement against the captured performance. Loud tapping, quiet music, room coloration, arcade neighbors, clipping and repeated musical structure plausibly complicate synchronization. Wrong reference selection creates an identity problem as well as a delay-estimation problem. A confident wrong export can invalidate the intended result and create rework; its real frequency and perceived severity have not been measured.

This is a coherent domain, but “underserved” remains a hypothesis. A creator may already solve the task efficiently using a normal editor. Handcam specificity becomes academically useful when measured constraints explain design choices and outcomes; game names and a distinctive user community do not independently establish novelty. Existing GUI synchronization software and editor synchronization directly challenge the broad application claim. [SyncSink][w-syncsink], [Kdenlive manual][w-kdenlive].

### Research infrastructure

Three experimental packages, retained JSON results, source identifiers/hashes, ground-truth strata, replay tooling, regression fixtures and documented version history substantially reduce startup effort. The archived experiment plan distinguishes exact, approximate, unknown and no-match labels and avoids source-naive statistical claims. Those are useful research practices. Raw historical media are not distributed in the repository, dependencies are mostly lower bounds rather than a complete frozen environment, and no independent external reproduction or creator study is documented. Auditability is stronger than turnkey public reproducibility. [Experiment plan][r-plan], [data provenance][r-provenance], [requirements][r-requirements].

## 3. What the Previous Astra Studies Actually Ruled Out

The first study formally tested hypotheses about confidence, evidence agreement, uniqueness, selectivity and HPSS. It found that the inherited favorable comparison did not survive expanded mismatch search. In that pre-D1 comparison, v2 produced 26 correct accepts, zero wrong accepts and 50 abstentions across 76 cases; GCC-PHAT recovered all 56 digitally inserted positives. Neither result implies general real-acoustic superiority. The study supplied a causal investigation and a release blocker, then appropriately refused to call the implementation a new method. Its negative findings are completed research assets. [Study and protocol][r-explore], [protocol][r-plan].

The later triage assessed the released D1 mechanism and found closer prior art: audio occurrence alignment already discarded short matched segments, and fingerprint systems already checked match duration and temporal occupancy. That specifically defeats the broad temporal-support novelty thesis. Ramona and Peeters' 2011 alignment work is a direct conceptual precedent; Panako's duration/occupancy policy provides concrete implementation precedent. This audit found no factual error that overturns that judgment. [Ramona and Peeters][w-ramona], [pinned Panako policy][w-panako], [triage][r-triage].

**STOP_ENGINEERING_ONLY does not mean that known algorithms cannot support a system study, that exploratory falsification has no scholarly value, or that an undergraduate cannot publish a rigorous case study.** It means the assessed method proposition did not warrant the proposed confirmatory investment. The earlier triage also considered a narrow comparative failure-analysis rescue and rejected funding it on current evidence. Route B below respects that investment concern rather than quietly reopening the same programme.

Some handoff sentences say that no v1.2.0 verdict exists yet, and the fact sheet lists temporal-support prior art as unresolved. Those statements predate SCIENTIFIC_TRIAGE and are superseded. Likewise, its real-positive table's zero-wrong entries cannot certify accuracy for recordings without precise independent labels. The authoritative interpretation is 29 accepts with preserved offsets, one approximate manual timing interval, and unknown independently measured timing error for the others. [Handoff][r-handoff], [fact sheet][r-facts], [triage][r-triage].

The new investment case is different: test whether the **complete workflow** saves effort while delivering correct results and making refusal manageable. An editor can equal or beat RhythmAlign's offset estimator and the system might still reduce user effort. Conversely, good offset performance can coexist with a workflow too inconvenient to justify a paper.

## 4. Candidate Paper Routes

Classifications below describe what is realistically achievable after the stated additional work, not submission readiness today. Paper archetype, research method and venue are different axes: an applied-system study can use human task measurements and be published in an undergraduate journal.

### A. Novel method / signal-processing paper

**NOT_CREDIBLE; outlook VERY_LOW.** No defensible new alignment principle has been demonstrated. Known features, threshold arrangements, refusal and concentration attribution do not establish method novelty. Existing temporal verification and multimodal synchronization work defeat the broad claims; adding a different concentration statistic would require a new independent justification. [Triaged prior-art comparison][r-triage], [Six and Leman, 2015][w-six].

This route has high conceptual novelty and comparative rigor requirements, substantial new baseline/data work, and no need for a user study unless making user claims. A conventional full signal-processing/MIR paper, often around six to eight pages depending on venue, would need a contribution that is presently absent. “More experiments on D1” is not the minimum missing item. The main rejection would be known method composition without a new result. Abandon this route for the current project.

### B. Empirical / failure-analysis paper

**POSSIBLE_BUT_WEAK today; potentially a LEGITIMATE_MODEST_PAPER after a distinct comparative result. Outlook MODERATE for a coherent bounded case study, LOW for a broader cross-system claim.** A clear question exists: *How do benchmark construction and localized matching evidence change conclusions about confidence-gated constant-offset synchronization?*

There is already a meaningful empirical result. An apparently favorable benchmark concealed concrete wrong-song accepts, and the investigation localized their support and tested interventions. Null maxima, unique-but-wrong peaks, correlated corroboration and preservation-versus-correctness distinctions form a coherent evaluation account. However, the general warnings about searched maxima, short matches and verification are established. The search found no identical PCEN/onset attribution account, but absence of an identical analysis is not evidence of a general discovery. [Archived literature review][r-literature], [Ramona and Peeters][w-ramona].

A specialist empirical paper would need independently acquired acoustic cases, a genuine fingerprint verifier, GCC-PHAT with a defensible rejection rule, and a frozen simple correlation selector. It should compare risk and useful coverage under explicit identity/occurrence labels, not celebrate an old version's failure. Those requirements are substantial and repeat the unresolved investment problem in the prior triage. No new empirical programme is recommended on this basis alone.

A benchmark/evaluation-methodology contribution is possible without a new algorithm if it provides reusable data, labels, protocols and a result that changes comparative conclusions. The current private, exposed corpus does not yet constitute that benchmark. Human participation is unnecessary for an exclusively technical claim; careful labeling is mandatory. A short specialist/workshop paper is more plausible than a broad journal study. Main rejection: one implementation's already understood bug, presented as a field-wide phenomenon.

### C. Applied-system / domain paper

**LEGITIMATE_MODEST_PAPER; outlook PROMISING. Primary route.** The contribution would combine a concrete task model, an implemented system and evidence about actual completion and recovery. It can use standard DSP honestly. The scientific addition is the evaluated relationship between design choices and a constrained creator workflow, not the existence of an executable.

The closest substitute is not only another research algorithm. SyncSink already provides a GUI for shared-audio synchronization, uses fingerprints followed by cross-covariance refinement, and produces FFmpeg commands. Kdenlive already aligns clips to an audio reference. These precedents rule out first-ever accessible audio synchronization and make a direct workflow comparator mandatory. They do not answer how this released application behaves with handcam noise, wrong references and refusal. [SyncSink][w-syncsink], [Kdenlive][w-kdenlive].

Conceptual novelty burden is moderate-to-low, while empirical rigor and system completeness remain essential. The implementation is sufficiently complete to evaluate now. A small creator task study is justified because reduced editing effort is the proposed benefit; a months-long field deployment is unnecessary for a bounded claim. Minimum additions are fresh timing labels, ordinary-editor comparison, full accounting of failures and recovery, and a reusable evaluation package. Main rejection: the normal editor already does the job with comparable effort, and no transferable lesson emerges.

Likely formats are a student research article or specialist short/case-study paper. A stronger full SMC-style paper is a conditional ceiling, not the default target. Sound and Music Computing explicitly covers content processing and software environments; its 2026 call uses peer review and proceedings publication, but that call is closed. [SMC 2026 call][w-smc].

### D. HCI / workflow study

**LEGITIMATE_MODEST_PAPER with a narrower small-study claim; outlook MODERATE.** The legitimate question is whether selective automation reduces effort and how creators respond to withheld assistance. Useful measures include completion time, corrections, retries, successful outputs, workload and behavior after ABSTAIN. Creator research already treats editing practices and tool control as scholarly questions; it is not necessary to pretend this is algorithm research. Kim and Kim's CHI 2024 study investigates creator needs and design opportunities, rather than validating RhythmAlign's task or outcomes. [Creator workflow study][w-creator].

A standalone HCI paper would need stronger grounding of the interaction question than a usability score. Relevant findings might concern mistaken trust in ACCEPT, repeated retries after refusal, or the cost of transferring work to another editor. Those are hypotheses, not observed behavior. A focused task study with eight creators can document substantial local effects and failure mechanisms; it cannot establish saturation, durable adoption, or rare-error equivalence merely by collecting many repeated tasks.

An independent HCI route requires recruitment, balanced task assignment, neutral facilitation, consent and the institution's applicable review process. It need not require 100 participants. Top HCI conferences demand a stronger interaction or conceptual contribution than this mature but conventional GUI currently supplies. The preferred approach is to use task observations inside Route C, avoiding a separate HCI-theory claim. Main rejection: a convenience sample, generic satisfaction scores and no insight beyond “automation is faster.”

### E. Research software / software-system paper

**POSSIBLE_BUT_WEAK overall; current JOSS submission NOT_CREDIBLE. Outlook LOW.** Research software publication is a real category: Sync Toolbox is a directly relevant published example. RhythmAlign could support research into selective synchronization or music-interaction recordings, but being an object of an internal audit is weaker than demonstrated reusable research utility. [Sync Toolbox, JOSS 2021][w-synctoolbox].

There is a concrete eligibility barrier: [LICENSE][r-license] is PolyForm Noncommercial 1.0.0. JOSS requires OSI-compliant open-source software; restricting commercial use conflicts with the Open Source Definition's field-of-endeavor freedom. A public repository and free personal use do not satisfy that requirement. The inspected JOSS submission policy also requires more than six months of public development and demonstrated research use. Main's earliest commit is dated 2026-05-09, about four months before this audit; commit dates alone do not establish public availability. [JOSS submissions][w-joss], [Open Source Definition, §6][w-osi].

Further gaps are a documented research use case, complete reproducible examples, an environment specification, contribution/support guidance and evidence of use beyond isolated development. Multiple authors are not intrinsically required. JOSS's review criteria consider credible scholarly significance and community readiness, while its submission gates require actual research use; an eventual submission should satisfy both. Its current paper format is 750–1,750 words, but the reviewed software carries the substantive burden. [Review criteria][w-joss-review], [paper format][w-joss-format].

JORS offers peer-reviewed software metapapers emphasizing research reuse and archiving. That is another legitimate format, not a verified licensing workaround: its detailed submission page could not be retrieved reliably here, so current license/fee eligibility is unconfirmed. No relicensing, research-package extraction or software-paper preparation is recommended in this audit. Main rejection: a consumer utility lacks the research reuse and eligibility required by the chosen software venue. [JORS scope][w-jors].

### F. Demo / short / workshop paper

**LEGITIMATE_MODEST_PAPER is possible; outlook PROMISING for an appropriate modest format.** A complete application and reproducible refusal example can support a demonstration with a bounded design/evaluation argument. Algorithm novelty is not universally required. System completeness, relevance and an intelligible contribution remain necessary; screenshots plus feature lists are weak even in short formats. A small number of observed tasks can support a demo's limited claims, but cannot be expanded into a population usability result.

Publication status must be track-specific. ISMIR 2026 LBD accepts up to two content pages plus an optional references page, screens submissions, and explicitly excludes them from official proceedings. Its advertised deadline is September 25, subject to an earlier capacity limit; this is an opportunity for feedback, not a peer-reviewed archival conference paper. [ISMIR LBD call][w-lbd]. UIST 2026 demos have a rigorous curation process and expect novel, compelling interaction; qualifying full demo submissions can receive a proceedings DOI, but the July deadline has passed and fit for this conventional interface is weak. [UIST call][w-uist].

Audio Mostly's verified 2025 call included peer-reviewed case-study/short formats, with short papers capped at 4,000 words excluding references. That is historical evidence that an honest format exists, not confirmation of a current 2026 call. The series' scope covers sound interaction and production tools. Main rejection: no contribution beyond a routine tool, or a workshop whose topic does not actually fit. “Workshop” is not a uniform rigor level or an archival guarantee. [Organizer-issued 2025 call][w-am-call], [series scope][w-am-scope].

### G. Undergraduate research paper / symposium

**LEGITIMATE_MODEST_PAPER; potential STRONG_STUDENT_PAPER after a careful study. Outlook PROMISING.** RhythmAlign is unusually mature as a starting point by the relevant criteria: there is a working artifact, a real task, falsifiable questions, preserved negative evidence, tests and an engineering response. That judgment concerns readiness to conduct research, not a measured ranking against other undergraduate projects.

A rigorous undergraduate project still needs a question, related work, explicit methodology, evidence, analysis, limitations and accessible reproduction materials. A bounded comparative system study satisfies that structure if its claims follow its results. A retrospective failure-analysis case study can also qualify if its scholarly contribution is a well-supported investigation, and its evidence is not advertised as new independent validation.

Reinvention is a concrete possible outlet: it accepts undergraduate work internationally, uses academic peer review, and publishes research articles of 2,000–5,000 words. Its interdisciplinary audience requires accessible framing. This is an actual journal route, not a promise that a CS system article will pass editorial screening. Its current rules include undergraduate eligibility, institutional ethics compliance and AI-use disclosure. [Journal/publisher][w-reinvention-about], [submission rules][w-reinvention], [AI/authorship policy][w-reinvention-ai].

A university symposium is a valuable research completion milestone even when it publishes only abstracts. CCSC Central Plains 2026 illustrates the distinction: student papers could be presented and posted online, but were explicitly excluded from the journal. Institutional eligibility, geography and future deadlines remain unverified; it is an example, not a submission recommendation. Main rejection: a project description without an answered research question, even at student level. [Student-paper rules][w-ccsc].

## 5. Decision Matrix

Scores are ordinal advisor judgments about a realistically completed route under the current constraints, not publication probabilities. **Higher is favorable** for question clarity (Q), reusable assets (A), undergraduate feasibility (F), and coherent-paper outlook (C). **Higher is harder/worse** for novelty burden (N), additional data (D), implementation (I), experimental burden (E), and prior-art rejection risk (R). For these nine columns, 1 is minimal/very low and 5 is maximal/very high in the stated direction.

For coherent-paper outlook, C=1/2/3/4/5 maps to VERY_LOW/LOW/MODERATE/PROMISING/STRONG. The ceiling (V) is a separate reach scale: 1=institutional presentation; 2=archival undergraduate or modest specialist short/workshop/demo; 3=full specialist conference or eligible research-software journal; 4=broader established field venue; 5=leading flagship contribution. It estimates potential reach if the missing evidence succeeds, not intrinsic research quality. No weighted total is meaningful across these different axes.

| Route | Q ↑ | N ↓ | A ↑ | D ↓ | I ↓ | E ↓ | F ↑ | R ↓ | C ↑ | V | Current investment judgment |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A Method | 2 | 5 | 2 | 5 | 5 | 5 | 1 | 5 | 1 | 2 | No supported method route |
| B Empirical/failures | 4 | 3 | 5 | 4 | 3 | 4 | 3 | 4 | 3 | 3 | Coherent local evidence; comparative extension costly |
| C Applied system | 5 | 2 | 5 | 3 | 1 | 3 | 4 | 3 | 4 | 3 | **Primary** |
| D HCI/workflow | 4 | 3 | 3 | 3 | 2 | 4 | 3 | 3 | 3 | 4 | Use focused task evidence within C |
| E Research software | 3 | 2 | 3 | 2 | 3 | 3 | 2 | 3 | 2 | 3 | Eligibility and research-use barriers |
| F Demo/short/workshop | 4 | 2 | 5 | 2 | 1 | 2 | 4 | 3 | 4 | 2 | Format depends on actual contribution and call |
| G Undergraduate | 5 | 1 | 5 | 1 | 1 | 2 | 5 | 2 | 4 | 2 | **Backup as a historical empirical case study** |

A's V=2 is an upper bound on a reframed account; no method venue is endorsed. E's V=3 is conditional on eligibility changes outside this audit. G's low data burden refers to the backup's historical question, not permission to omit fresh evidence for C. F and G are partly publication formats, so their apparent ease cannot be added to C as independent chances of acceptance.

| Route | Minimum additional work | Strongest missing evidence | Principal reviewer objection |
|---|---|---|---|
| A | A genuinely different justified contribution, not additional D1 tuning | New principle and fair independent comparisons | Established methods repackaged |
| B | Freeze a comparative question and test established verifiers on new acoustic sources | A replicated finding that changes comparative understanding | Implementation-specific known failure |
| C | Approximately 60–100 focused hours over 4–6 weeks, conditional on access; study in §7 | Correct end-to-end outcomes and effort versus the editor | No advantage or useful design lesson over substitutes |
| D | Recruit creators, ground an interaction question, observe balanced tasks and analyze behavior | Recovery/trust mechanisms tied to outcomes | Small satisfaction study without HCI insight |
| E | Resolve eligibility, research use, reproducibility and support gaps | Researchers actually able to reuse it | Consumer utility or noncompliant submission |
| F | Prepare a working demonstration plus a limited evaluated claim and applicable call | Something readers learn from the demo | Product tour or wrong track |
| G | Roughly 15–30 focused hours to delimit, verify and write the retrospective investigation | Independently checked provenance and accessible case evidence | Engineering diary presented as research |

Effort estimates are planning judgments, excluding editorial review, travel, recruitment delays and institutional approval time. They are not commitments or measured project durations.

## 6. Primary Recommendation

Choose **C: applied-system / domain paper**. Human task measurements are part of evaluating this system; they do not turn it into a second simultaneous HCI thesis.

**Provisional research question:** *For rhythm-game handcam audio replacement, when does RhythmAlign reduce the effort needed to obtain a correctly synchronized output compared with an editor's native audio synchronization and manual waveform alignment, once refusals and recovery are counted?*

**Provisional, falsifiable claim:** *For the defined creator population and constant-offset tasks, RhythmAlign can reduce active editing effort at useful correct-completion levels; its limits can be explained by refusal, reference mistakes and the cost of returning to an editor.* The comparative direction must be established by the study. A completed paper must replace “can” with measured counts, differences and qualified conclusions; this audit supplies no positive result.

The paper's defensible contribution would be the task specification, implemented design rationale, and comparative evidence linking decisions to outcomes. The distinctive question is not whether automation is fast, but whether a tool that sometimes withholds an offset is useful after the creator bears the recovery cost. An integration benefit can survive technical parity with established alignment. If all benefit comes from stream-copy export, that is a useful measured attribution but probably too thin alone for more than a student case study.

This has better expected value than the alternatives because the application already exists and both positive and negative workflow outcomes are interpretable. It requires no learned model, new DSP mechanism, mobile port, or large dataset. The practical assumption is access to about eight adult creators, independent labeling help and a modest set of new recordings. If those are unavailable, the backup in §11 preserves a genuine research question without claiming the absent user benefit.

## 7. Minimum Credible Paper

**Everything in this section is proposed, not performed or preregistered.** The numbers are a feasible design for a bounded system case study, not a power calculation or a venue's acceptance threshold. The study has one question, with technical outcome measurement and creator task observation addressing different parts of it.

### Fixed subject, data and labels

Keep RhythmAlign v1.2.0 and its thresholds fixed. Use a single pinned editor build, provisionally **Kdenlive 26.08**, whose current manual documents native audio-reference alignment. Record exact builds, machine, decoding settings and comparator configuration. A short feasibility pilot may establish labeling, task timing and editor operability; exclude its people and sources from final evaluation. Freeze the protocol before examining final outcomes. [Kdenlive documentation][w-kdenlive].

| Population | Proposed scale | Purpose and independence limit |
|---|---|---|
| Feasibility pilot | Two creators, four newly captured pairs from four songs | Verify measurement and workflow practicality; development only |
| Final acoustic positives | 12 previously unexposed songs, two handcam captures each: 24 recordings | Capture ordinary and difficult conditions across at least six sessions and two microphone/device configurations; variants of one song are dependent |
| Wrong-reference challenges | 12 predeclared recording/reference mismatches using the new sources | Test refusal under known target absence; reuse of sources means these are not 12 independent populations |
| Final creator study | Eight adult handcam creators, six tasks each: 48 task observations | Eight participants, not 48 independent users; tasks and songs also repeat |

Use genuine music-through-speaker/microphone captures with physical taps and ambient sound, not digital insertion of the clean track into existing noise. Within-song conditions may differ in capture difficulty; this is not an isolated SNR causal experiment. Record how material was acquired, room/arcade context, exact source version, camera, speaker and capture session. At least some material must represent the actual noisy target context; controlled home playback alone supports only a home-capture claim.

Independent timing is the main technical feasibility constraint. A concrete acquisition option is a timestamped source-playback record plus audiovisual synchronization markers before and after each take, with camera A/V latency and marker/source timing independently calibrated. Exclude markers from all alignment inputs using documented crops and coordinate transforms. Check a midpoint timing anchor against the source record. Two annotators should review identity and early/middle/late timing without seeing any method's proposed offset. Do not use player taps as exact music timing, or label a recording by accepting another aligner's output.

Set an initial acceptance tolerance of **100 ms**, with label uncertainty no greater than **33 ms**, and report sensitivity at 50 and 150 ms. These are proposed editorial-task criteria, not established rhythm-game perceptual thresholds. For uncertain interval labels, count a prediction as correct only when the entire uncertainty interval satisfies the criterion; retain boundary cases as indeterminate. If the apparatus cannot support that precision, revise the claim and protocol on pilot material rather than inventing precise labels.

Early/middle/late anchors must support one offset within the tolerance. Drift, edits, multiple valid occurrences and uncertain background-source identity belong in separately reported out-of-contract/unknown categories. Keep an enrollment/exclusion log with reasons decided independently of engine output. Wrong-reference controls require a source log establishing the selected reference is absent; uncertain ambient contamination stays unknown. Their artificial frequency is not a measured creator mistake rate.

### Comparators and task assignment

Use three complete workflows:

1. **RhythmAlign plus ordinary-editor recovery:** Full Export or Analyze Only as appropriate; correction/retry is allowed; Kdenlive is available for manual recovery after refusal or a discovered error. Charge every switch, retry and verification step.
2. **Kdenlive native synchronization plus manual recovery:** Use the documented audio-reference command, then normal inspection, correction, mixing and export. Native automation is the decisive practical substitute.
3. **Kdenlive manual waveform/listening alignment:** Same editor, task files and output goal, with automatic audio alignment disabled for this condition. This contextualizes automation's benefit without serving as the only baseline.

A limited **SyncSink technical comparison** on the 36 final pairs is also required as the nearest research-tool check: retain its native behavior, offset/absence outputs, settings and runtime. Use its actual public implementation, not a homemade weak fingerprint approximation. Do not count a correctly localized shared fragment as a false whole-song claim unless the comparator actually makes that claim. If SyncSink proves materially more competitive than the editor during the pilot, replace the manual-only task arm with SyncSink plus editing before the final protocol is frozen. Three human-study arms remain sufficient. [SyncSink implementation][w-syncsink].

No full slate of learned fingerprints, DTW and new GCC rejection policies is mandatory for this **workflow** claim. It is mandatory for the broader technical-superiority claim in Route B. Existing GCC-PHAT results remain contextual evidence that simple methods deserve respect. The paper must explicitly limit any comparative conclusion to the tested software and task contract.

Select a 12-task bank from the new material without consulting algorithm outcomes: six ordinary positives, three difficult positives and three initially wrong-reference tasks. For the latter, a correct reference must be available in the task materials; the goal is to diagnose and finish, not merely click a refusal button. Each participant completes two tasks per workflow, one ordinary and one challenge, with distinct songs for that participant. Counterbalance workflow order and allocate each task to four participants with arm assignments balanced as closely as possible. Publish the assignment, including unavoidable imbalance with eight people.

Record editing experience and give equivalent practice in all three workflows. Collect a short account of the participant's actual editing practice before presenting the task, to check domain relevance. Use a fixed script without assistance that favors one application. Eight creators enable a small comparative case study; they do not establish population representativeness. Obtain consent for observation and follow the institution's applicable research review requirements before recruitment.

### Outcomes and analysis

The endpoint is a **usable, independently checked output**, not merely an offset displayed or a participant clicking “done.” Specify reference identity, audio mix, video duration and export requirements consistently. Have a method-blinded checker score the exported result against the independent anchors. Count a wrong-reference export as wrong even if its lag is numerically close to some incidental event.

| Measure | Required reporting |
|---|---|
| Correct completion | Correct-reference output within timing tolerance; report count/denominator in every workflow and task stratum |
| Active editing effort | Selection, inspection, corrections, retries and recovery; report individual participant summaries and task distributions |
| Wall-clock completion | Includes analysis/render wait, with active time and automated wait separated |
| Incomplete/incorrect tasks | Fixed ten-minute task limit; retain raw time and reason rather than dropping failed tasks |
| Severe errors | Wrong reference, or at least one second of persistent placement error; distinguish automatic wrong ACCEPT, corrected error and final wrong output |
| Recovery | Time after refusal/error, editor switches, retries, manual adjustments and whether completion follows |
| Technical alignment | Correct/wrong ACCEPT and ABSTAIN, positive coverage, wrong-reference acceptance, absolute error, latency and reason counts |
| User interpretation | Brief perceived-effort and confidence ratings plus observations of what ACCEPT/ABSTAIN meant to the creator |

To prevent fast failure from masquerading as efficiency, report completion and effort together. One predeclared decision score can assign the ten-minute limit to failed/incorrect tasks and use observed completion time for successes. Label that as a capped completion score, not actual labor. Report raw active time separately, and never base the headline on accepted-only or completed-only timing.

Use participant-level paired summaries and song/session-level technical summaries. Display all eight participants and all task outcomes. Any interval or randomization analysis must respect the actual task assignment and repeated sources; avoid treating recordings, windows or reciprocal pairs as independent replications. At this scale, descriptive effect sizes, consistency and inspectable failures are more useful than a collection of fragile significance tests.

Report positive coverage and wrong-reference acceptance separately. Selective error is wrong ACCEPTs divided by all ACCEPTs and is undefined when none are accepted; show the raw numerator and denominator. Do not turn the constructed positive/negative mixture into deployment risk. Likewise, zero severe errors in this study cannot demonstrate equivalent safety or a low population error bound.

The system paper need not causally attribute its result to D1. Compare final workflows, describe observed paths, and identify alternative explanations. In particular, stream-copy export can reduce waiting independently of alignment, and Analyze Only can support successful editor work independently of full export. A later D1 ablation would answer a different question and is optional here.

### Predeclared stopping boundary

The pilot is a feasibility check, not a filter selecting only songs the system wins. If source identity/timing cannot be independently established, the native comparator cannot be operated fairly, or access to creators is implausible, do not commence the full protocol under this claim.

Before final data, define what the participating creators regard as worthwhile savings; **20% active time or 30 seconds per task** is a provisional planning threshold, not a scientific constant. Failure to reach it does not erase the research. But if RhythmAlign brings neither meaningful effort benefit nor improved observed completion/error handling and yields no substantive failure/recovery insight, the positive applied-system paper is not worth pursuing. Do not tune v1.2.0 or replace inconvenient final tasks to rescue it.

## 8. Existing Assets We Can Reuse

| Asset | Legitimate reuse | Boundary |
|---|---|---|
| Released engine, GUI and export code | Study artifact and architecture/design description | Preserve release identity; do not claim new DSP |
| Analyze Only, refusal reasons, diagnostics | Observe assistance, interpretation and recovery | Their presence is not proof of usability or accuracy |
| Tests and release records | Document contracts, build maturity and historical validation | Historical passes do not become new study outcomes |
| A/B/C experiments | Development rationale, candidate comparisons and exact-insertion fixtures | Sources and corruption packages were exposed; not fresh acoustic confirmation |
| Formal Astra exploration | Hypotheses, mismatch protocol, null probes, localization, interventions and negative findings | Label all pre-D1 measurements with that version and their exploratory status |
| D1 records | Explain engineering response and consumed holdout results | Preserve historical separation without calling the data untouched today |
| Provenance/triage documents | Ground-truth definitions, source-exposure map, known prior art | Later triage supersedes earlier open questions |
| Research scripts and JSON | Adapt existing runners and retain failure taxonomies; audit raw outcome tables | Check version assumptions before future reuse; archived scripts may pin the old engine |
| Packaging and bilingual documentation | Recruit nonprogrammers and reproduce the deployed workflow | No standalone scientific novelty; no inference of broad adoption |

The research assets reside on two branches as well as main. Their immutable Git references are part of the evidence; there is no need to merge them to cite them. The [handoff][r-handoff], [exploration][r-explore], [experiment plan][r-plan] and [provenance map][r-provenance] are the starting documents for reuse.

Keep three evidence classes visible in the eventual paper. **Scientific history** explains what was hypothesized and discovered. **Development evidence** explains which observations shaped v2/D1 and how known behavior changed. **Final evaluation** answers the newly fixed workflow question with new sources, labels and observations. Old data can still support an existence claim or retrospective explanation; they cannot establish fresh generalization of the repaired system. Historical holdouts retain their original value but cannot be presented as a second independent confirmation after reuse.

## 9. What New Evidence Is Required

**Mandatory for the primary route:** independently labeled new acoustic captures; a predeclared identity/timing contract and source-exposure check; the editor's real automatic synchronization comparator; the nearest research-tool technical check; and observed creator tasks that count refusal, recovery and incorrect outputs. The study must establish that the task occurs in these creators' practice rather than assume it from the developer's motivation.

Also mandatory is a reviewable reproduction package: exact software versions, configuration, task assignment, annotation method/uncertainty, all outcomes, exclusion reasons and analysis instructions. Arrange authorized access to the evaluated media and labels for checking. If public release of commercial music is unavailable, do not claim an open benchmark; use permissions, appropriate restricted review access, and openly distributable example fixtures. An inability to make central evidence inspectable materially weakens even a modest empirical paper. The new study's media permissions do not follow from the application's license.

**Optional:** longer field use, more creators, a second editor, additional recording domains, D1 removal, calibrated GCC-PHAT, modern learned fingerprints, a usability questionnaire, perceptual timing experiments and research-package refactoring. Each can answer additional questions, but none should become an automatic prerequisite for the bounded primary claim. Do not install or implement these additions during this audit.

The largest gap is not another graph from the existing corpus. It is evidence that independently checked outputs and user effort improve together, or a well-supported explanation of why they do not.

## 10. Reviewer Kill Tests

| Objection or observation | Consequence for the proposed paper |
|---|---|
| “The editor already does this equally well with equal or lower effort.” | Kills the positive benefit claim. A substantive recovery failure may still justify the backup; a cosmetic difference does not. |
| Users rarely perform the proposed task or already obtain clean synchronized source audio | The domain-need premise fails for that population; do not infer an underserved community. |
| Timing labels come from RhythmAlign, agreement with a baseline, or uncalibrated taps | Correctness claims fail. Relabeling from predictions is not a remedy. |
| Advantages disappear after counting failures, checking and editor recovery | The claimed workflow benefit fails; report the complete cost. |
| Results depend on depriving the editor of native synchronization or normal practice | Comparator is unfair; the evaluation cannot support the paper. |
| “Safe” means no wrong exports only among selected successes | Safety interpretation fails. Include every attempted task and distinguish refusal from completion. |
| Benefit is solely export wait, with no effort or design insight | Narrow the result to measured integration behavior; likely insufficient beyond a student case study. |
| Fresh data reuse old songs, versions, sessions or interference sources | They cannot be called source-disjoint confirmation. Keep them in development evidence. |
| Wrong-reference labels are actually audible background occurrences | Identity interpretation is unresolved; do not score native local matches as false whole-song decisions. |
| No one can inspect labels/media or reproduce central results | Broad empirical/benchmark framing fails; private results require explicit limitations and credible review access. |
| Frequent wrong ACCEPTs make creators do more checking than the ordinary workflow | Kills the benefit/safety narrative, even if algorithm-only offset accuracy looks good. |
| Small noisy differences are declared a win using post-hoc task selection | No defensible positive conclusion; no TEST retuning or selective reporting. |

A negative result is not inherently a killed research project. It can answer a worthwhile question. The stopping boundary is whether the evidence supports an informative, bounded conclusion with a suitable audience, rather than whether the application wins.

## 11. Backup Route

Choose exactly one backup: **G, an undergraduate empirical case-study paper about falsifying confidence assumptions in a deployed audio-synchronization project.**

The question is: *What did structured adversarial evaluation reveal that ordinary regression and favorable development benchmarks failed to reveal in RhythmAlign's acceptance policy?* The answer can use the archived pre-D1 result, signed contribution analysis, controlled interventions, D1 design choices and preserved regression outcomes. It need not claim an unknown DSP phenomenon or a superior released aligner.

Minimum extra work is to delimit this retrospective question, independently check the central evidence chain, make a representative failure/reproduction example inspectable under suitable permissions, and write the methods and limitations for an undergraduate research audience. A colleague's fresh reproduction checks the reported historical mechanism; it does not create a new source population. The original raw measurements remain dated and labeled. No new user study is required for this narrower historical claim.

This backup can remain legitimate if creator recruitment fails or workflow comparisons reveal no advantage. Its appropriate level is an undergraduate peer-reviewed research article or evaluated student research paper; a symposium may offer presentation rather than archival publication. It is weaker as a specialist MIR empirical paper because the general failure concern and verification principle are known. If the original evidence cannot be checked or the only account is a chronological development diary, this route also fails. [Original study][r-explore], [triage][r-triage], [Reinvention guidance][w-reinvention].

## 12. Routes to Abandon

- **Temporal-support verification as a novel alignment method.** Prior work already verifies extent and distribution; the exact one-second/0.25 heuristic does not restore conceptual novelty.
- **PCEN/HPSS/chroma/onset fusion as invention.** Describe established ingredients and the implementation choices accurately.
- **Development data as independent confirmation.** Neither the 29 real accepts, the semi-synthetic holdout nor the consumed D1 wrong-song holdout is fresh evaluation today.
- **Packaging as scientific novelty.** Installer, bilingual UI, stream copy and update checks make a useful artifact; only evaluated consequences can contribute to a system paper.
- **Rhythm-game specificity as sufficient novelty.** Show an actual task constraint and a measured consequence. Do not claim the first handcam solution because a selective search found no identical title.
- **A zero-risk, calibrated-confidence or guaranteed safe-export paper.** The scores and small dependent corpora cannot support those claims. Refusal is a behavior, not certification of every ACCEPT.
- **A new public benchmark/dataset paper without reusable data and labels.** Hashes and scripts are useful, but do not supply the missing media or permissions.
- **A “better than GCC/fingerprints” paper without actual fair comparisons.** Forced argmax on negatives is not a calibrated rejecting baseline.
- **A JOSS shortcut under the current license and research-use evidence.** A source-visible consumer tool does not automatically meet software-journal requirements.
- **Any denoising/source-separation paper attributed to this audit.** That separate research line is outside the inspected project and contributes no evidence here.

## 13. Realistic Publication Level

| Level | What can honestly be targeted | Status and fit |
|---|---|---|
| Undergraduate/student | Peer-reviewed original research article based on C, or the bounded G backup | **Most realistic archival target.** Reinvention is a verified international undergraduate outlet with academic peer review; topic-specific editorial fit is still uncertain. University symposia vary in publication status. |
| Workshop/short paper | Evaluated system case study with a concrete result and openly stated limitations | **Realistic conditional target.** Audio Mostly's 2025 short/case-study format is evidence of an appropriate category. No current 2026 call was verified; do not plan around invented deadlines. |
| Demo/software/application | A demonstrated system with a limited evaluated claim; eligible software paper only after substantial gaps are resolved | **Track-dependent.** ISMIR LBD is non-proceedings and screened; UIST demos are curated with a stronger interaction bar; JOSS is blocked now. These are not interchangeable publication types. |
| Full archival specialist conference/journal | A clear comparative system result and informative scope/limitations, with adequate reproducibility | **Possible ceiling, not the expected first submission.** SMC is plausible in scope; its 2026 papers are peer-reviewed, six pages encouraged/eight maximum, and proceedings are archived. The March 27 call is closed. |
| Broad flagship method/HCI paper | A substantially stronger method, comparative empirical discovery or interaction contribution | **Unsupported by current assets and minimum study.** A narrow task study cannot be relabeled a general contribution. |

The recommended first target level is therefore **a peer-reviewed undergraduate research article or a modest specialist system/case-study short paper**. The research question should determine which, once results exist. A poster accompanying an accepted archival paper is still that paper; a separately screened abstract is not transformed into a full paper by the conference's reputation.

Reinvention's publisher describes anonymous academic review and no author publication charge. Its submission rules require eligible undergraduate work, accessible writing and institutional ethics compliance. AI assistance must be disclosed, and human authors remain responsible for the research and claims. These requirements matter for a project whose research artifacts involved AI assistance; this audit is decision support, not evidence of independent human review or a submission-ready manuscript. [Publisher description][w-reinvention-about], [submission rules][w-reinvention], [AI policy][w-reinvention-ai].

Conference registration, attendance requirements and possible publication charges must be checked for the eventual cycle. No future call, acceptance, indexing status or affordable travel arrangement is assumed. An ISMIR LBD could provide worthwhile feedback, but it would not by itself fulfill a requirement for a peer-reviewed archival paper. [LBD rules][w-lbd], [SMC proceedings rules][w-smc].

### Source record

Repository sources are pinned to the verified commits above. Counts are attributed to preserved reports/results, not recomputed experiments. External policies were checked on 2026-09-13; explicitly dated older calls are examples of format, not current submission opportunities. The selective literature search covered synchronization systems, editor audio alignment, creator workflows, software publication and student/specialist formats. It found close substitutes, not proof that every handcam-specific prior system has been located.

| Source group | Specific material and use |
|---|---|
| Main production | [Engine][r-engine], [audio pipeline][r-auto], [GUI][r-ui], [CLI diagnostic][r-diagnose], [environment diagnostics][r-diagnostics], [README][r-readme], [license][r-license], [dependencies][r-requirements] — architecture and scope |
| Engineering history | [RA-1.2A][r-a], [RA-1.2B][r-b], [RA-1.2C][r-c], [RA-1.2D][r-d], [RA-1.2D1][r-d1], [RA-1.2E][r-e], [tests][r-tests], [release][r-release] — evolution and historical validation |
| Formal exploration | [ALIGNMENT_RESEARCH_STUDY][r-explore], [LITERATURE_REVIEW][r-literature], [EXPERIMENT_PLAN][r-plan] — pre-D1 hypotheses, results and protocols |
| Later scientific assessment | [ASTRA_HANDOFF][r-handoff], [FACT_SHEET][r-facts], [DATA_PROVENANCE][r-provenance], [SCIENTIFIC_TRIAGE][r-triage] — release provenance, supersession and method rejection |
| Nearest systems/verification | Six & Leman (2015), [Synchronizing Multimodal Recordings Using Audio-to-Audio Alignment][w-six]; Six, [SyncSink software][w-syncsink]; Ramona & Peeters (2011), [Automatic Alignment of Audio Occurrences][w-ramona]; [pinned Panako verification code][w-panako]; KDE, [Kdenlive 26.08 manual][w-kdenlive] |
| Workflow scholarship | Kim & Kim (2024), [Unlocking Creator-AI Synergy: Challenges, Requirements, and Design Opportunities in AI-Powered Short-Form Video Production][w-creator], CHI — creator-workflow research precedent, not handcam efficacy evidence |
| Software norms | Müller et al. (2021), [Sync Toolbox][w-synctoolbox], JOSS; JOSS [submissions][w-joss], [review criteria][w-joss-review], [paper format][w-joss-format]; OSI [Open Source Definition][w-osi]; JORS [journal scope][w-jors] |
| Relevant publication formats | [SMC 2026 call][w-smc]; [ISMIR 2026 LBD][w-lbd]; [UIST 2026 call][w-uist]; [Audio Mostly scope][w-am-scope] and [organizer-issued 2025 paper call][w-am-call] |
| Undergraduate publication | Warwick, [Reinvention journal description][w-reinvention-about]; journal [submissions][w-reinvention] and [AI/authorship][w-reinvention-ai]; [CCSC Central Plains 2026 student-paper rules][w-ccsc] |

[r-engine]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/alignment_engine_v2.py
[r-auto]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/auto_sync.py
[r-ui]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/ui_main.py
[r-diagnose]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/diagnose_offset.py
[r-diagnostics]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/diagnostics.py
[r-readme]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/README.md
[r-license]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/LICENSE
[r-requirements]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/requirements.txt
[r-release]: https://github.com/Daozhu1007/RhythmAlign/releases/tag/v1.2.0
[r-a]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/docs/RA-1.2A-LOW-SNR-ALIGNMENT.md
[r-b]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md
[r-c]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/docs/RA-1.2C-CALIBRATION-HARDENING.md
[r-d]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/docs/RA-1.2D-DEFAULT-INTEGRATION.md
[r-d1]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/docs/RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md
[r-e]: https://github.com/Daozhu1007/RhythmAlign/blob/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/docs/RA-1.2E-V1.2.0-RELEASE.md
[r-tests]: https://github.com/Daozhu1007/RhythmAlign/tree/91bc50c0a117b38176ec93b44b9e0d1b8aaf749d/tests
[r-explore]: https://github.com/Daozhu1007/RhythmAlign/blob/8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e/docs/research/alignment/ALIGNMENT_RESEARCH_STUDY.md
[r-literature]: https://github.com/Daozhu1007/RhythmAlign/blob/8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e/docs/research/alignment/LITERATURE_REVIEW.md
[r-plan]: https://github.com/Daozhu1007/RhythmAlign/blob/8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e/docs/research/alignment/EXPERIMENT_PLAN.md
[r-handoff]: https://github.com/Daozhu1007/RhythmAlign/blob/2c1fb6d818d12b20ac3e49fc0fae059627ec6f55/docs/research/alignment_v120/ASTRA_HANDOFF.md
[r-facts]: https://github.com/Daozhu1007/RhythmAlign/blob/2c1fb6d818d12b20ac3e49fc0fae059627ec6f55/docs/research/alignment_v120/FACT_SHEET.md
[r-provenance]: https://github.com/Daozhu1007/RhythmAlign/blob/2c1fb6d818d12b20ac3e49fc0fae059627ec6f55/docs/research/alignment_v120/DATA_PROVENANCE.md
[r-triage]: https://github.com/Daozhu1007/RhythmAlign/blob/2c1fb6d818d12b20ac3e49fc0fae059627ec6f55/docs/research/alignment_v120/SCIENTIFIC_TRIAGE.md
[w-six]: https://0110.be/files/attachments/434/2015.synchronized-recording.pdf
[w-syncsink]: https://github.com/JorenSix/SyncSink
[w-ramona]: https://www.dafx.de/paper-archive/2011/Papers/94_e.pdf
[w-panako]: https://github.com/JorenSix/Panako/blob/e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211/src/main/java/be/panako/strategy/panako/PanakoStrategy.java#L400
[w-kdenlive]: https://docs.kdenlive.org/en/cutting_and_assembling/right_click_menu.html
[w-creator]: https://jinikimcmu.github.io/assets/pdf/chi2024_creator_paper.pdf
[w-synctoolbox]: https://joss.theoj.org/papers/10.21105/joss.03434
[w-joss]: https://joss.readthedocs.io/en/latest/submitting.html
[w-joss-review]: https://joss.readthedocs.io/en/latest/review_criteria.html
[w-joss-format]: https://joss.readthedocs.io/en/latest/paper.html
[w-osi]: https://opensource.org/osd
[w-jors]: https://openresearchsoftware.metajnl.com/
[w-smc]: https://smc26.mbz.hr/en/submissions/call-for-papers
[w-lbd]: https://ismir2026.ismir.net/call-for-late-breaking-demo
[w-uist]: https://uist.acm.org/2026/cfp/
[w-am-call]: https://www.auditory.org/postings/2025/81.html
[w-am-scope]: https://audiomostly.com/2025/call/cfc/
[w-reinvention-about]: https://warwick.ac.uk/fac/cross_fac/iatl/research/reinvention/
[w-reinvention]: https://reinventionjournal.org/index.php/reinvention/about/submissions
[w-reinvention-ai]: https://reinventionjournal.org/index.php/reinvention/AIandAuthorship
[w-ccsc]: https://www.ccsc.org/centralplains/2026/students/papers.html

## 14. One Next Action

**Conduct one feasibility pilot with two creators and four fresh, independently timed pairs, comparing RhythmAlign with the editor's native synchronization.** Its purpose is to establish that the task, timing labels and complete workflow comparison are feasible. Pilot participants and songs remain outside final evaluation. This action is proposed only; the audit did not begin it.

### OVERALL VERDICT

MODEST_PAPER_ROUTE_EXISTS

### CAN RHYTHMALIGN BECOME MY FIRST REAL PAPER?

YES

### BEST PAPER TYPE

Applied-system paper with a focused comparative workflow evaluation.

### CORE RESEARCH QUESTION

When does RhythmAlign reduce the effort needed to produce correctly synchronized handcam audio replacement compared with an editor's native synchronization and manual alignment, once refusal and recovery are counted?

### WHY THIS IS MORE DEFENSIBLE THAN THE REJECTED METHOD THESIS

It tests a real system's value through observable outcomes. It does not claim invention of established alignment or temporal-verification ideas. The rejected method verdict remains intact.

### WHAT WE ALREADY HAVE

A released application, automatic and analyze-only workflows, refusal behavior, export, diagnostics, tests, and a formal exploratory failure investigation with preserved provenance.

### WHAT WE STILL NEED

Fresh independently timed acoustic recordings, fair editor and research-tool comparisons, eight creators' final task observations, and inspectable evidence. No such final evaluation has been performed.

### REALISTIC PUBLICATION LEVEL

A peer-reviewed undergraduate research article or a modest specialist system/case-study short paper. A screened demo or symposium presentation is valuable but does not automatically constitute an archival paper.

### BIGGEST RISK

The ordinary editor may already achieve the same outcomes with less effort, especially after RhythmAlign's refusals require manual recovery.

### BACKUP ROUTE

An undergraduate empirical case study of how adversarial evaluation exposed and explained the pre-D1 confidence failure.

### NEXT ACTION

Conduct one two-creator feasibility pilot on four fresh, independently timed pairs against native editor synchronization.

### FILE CREATED

docs/research/repo_wide/PAPER_OPPORTUNITY_AUDIT.md
