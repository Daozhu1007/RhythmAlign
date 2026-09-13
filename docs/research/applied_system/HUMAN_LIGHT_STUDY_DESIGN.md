# Human-Light Applied Systems Study Design

Status: DESIGN ONLY. No data has been collected, no participant contacted, no
benchmark run, and no production code changed for this design. This document
redesigns the audit's study proposal
(`docs/research/repo_wide/PAPER_OPPORTUNITY_AUDIT.md`, route C) around a
system-benchmark-first methodology in which automated agents perform all
scientifically legitimate work and human participation shrinks to a small
feasibility pilot. It does not weaken the honesty requirements established by
the Astra exploration, the v1.2.0 provenance map, or the repo-wide audit.

Constraints this design inherits and does not relitigate:

- `STOP_ENGINEERING_ONLY` stands: no algorithmic-novelty claim is available.
  PCEN/HPSS/chroma/onset fusion and the D1 temporal-support safeguard are
  implemented heuristics on known ingredients, not contributions.
- Every real-audio population in the repository is `DEVELOPMENT` or a spent
  `HISTORICAL_HOLDOUT` (see `archive/alignment-paper-v1.2.0` provenance map).
  `POTENTIAL_FUTURE_CONFIRMATION` is empty. Final-paper evidence requires
  source-disjoint, independently timed, freshly acquired acoustic material.
- The evaluated software is frozen RhythmAlign v1.2.0. No threshold, feature,
  or policy change is permitted during the study, regardless of outcome.
- Prior baseline structure on exposed data: GCC-PHAT argmax recovered all 56
  exact-insertion positives but produced 20 wrong accepts on negatives;
  frozen v2 produced 26 correct accepts / 0 wrong accepts / 50 abstentions on
  the 76-case preserved corpus. These are development-era observations that
  motivate, but cannot confirm, the selectivity hypothesis tested here.

---

## 1. Recommended Paper Framing

The intellectual contribution is NOT "an algorithm for rhythm games." The
paper investigates a general production problem:

> **Reference-audio replacement for user-generated video**: replacing the
> degraded audio captured inside a video (speaker playback, room noise,
> impact transients, compression) with a clean reference recording placed at
> the correct position — and refusing to place it when the evidence does not
> support a placement.

Rhythm-game handcam editing is presented honestly as the primary real-world
stress-test domain, chosen because it concentrates the failure modes of this
problem class (low target-to-noise ratio, physical tapping, environmental
interference, repeated musical structure, consumer microphones) in a setting
where the correct answer is verifiable and the production need is real. The
domain is the laboratory, not the claim.

Three pillars carry the paper:

1. **A reproducible benchmark protocol** for reference-audio alignment on
   real consumer-capture recordings with independently established timing
   ground truth (Section 7) — including a wrong-reference/no-match stratum
   that most alignment evaluations omit.
2. **A system-level risk-coverage comparison** between a selective system
   (RhythmAlign v1.2.0, which can ABSTAIN) and always-output baselines
   (GCC-PHAT, normalized cross-correlation, a fingerprint-based tool), frozen
   before testing, on material none of them influenced (Sections 5, 8).
3. **A measured account of refusal cost**: a small creator feasibility pilot
   quantifying what ABSTAIN costs the user in time and recovery steps, so
   that "safe" is never claimed without "and here is what safe costs"
   (Section 10).

The framing sentence for the paper: *an applied-system study of selective
reference-audio replacement in degraded user-generated video, evaluated
primarily by a benchmark with independent timing ground truth and supported
by a small creator feasibility pilot.*

## 2. Core Research Question

**Primary (system/benchmark level):**

> Under difficult real acoustic capture conditions, does a selective
> alignment system — one that can refuse to output a placement — achieve a
> strictly better safety-for-coverage operating point than established
> always-output alignment methods, and at what measured cost in refused work?

**Secondary (workflow level, pilot only):**

> Is the complete selective workflow usable end-to-end by a real creator,
> including recovery after refusal, and approximately how much time does the
> recovery path take?

The audit's original primary question ("when does RhythmAlign reduce editing
effort compared with an editor's native synchronization") is demoted to
pilot-level support. That question, asked properly, needs the eight-creator
task study the owner cannot easily recruit; it is therefore replaced as the
load-bearing question, not silently dropped. The trade-off is explicit: the
redesigned paper cannot claim "creators save effort" as a population finding;
it can claim a measured correctness/safety advantage and a feasibility-
scoped account of workflow cost.

## 3. Defensible Claims and Non-Claims

### Candidate claims considered

- **C-A (selective safety).** On fresh, independently timed recordings from
  the stress-test domain, a selective alignment workflow achieves a lower
  catastrophic-error rate (confident wrong placements, including wrong-song
  accepts) than always-output baselines, while retaining useful positive
  coverage; refusal costs are quantified and bounded in a creator pilot.
- **C-B (benchmark/protocol).** We contribute a reproducible, independently
  timed benchmark with exact/approximate/no-match ground-truth strata and
  show that comparative conclusions about alignment methods change when
  realistic acoustic degradation and wrong-reference cases are included.
- **C-C (workflow effort, audit's original).** RhythmAlign reduces creator
  editing effort versus editor-native and manual synchronization at equal or
  better correctness, once refusal and recovery are counted.

### Selection

**C-A is the primary claim**, with C-B as a secondary contribution (the
protocol and labels are reusable artifacts even if the media cannot be
publicly released; see Section 15). C-C is reduced to pilot-scope
observations and is NOT claimed.

C-A is chosen because it is (a) measurable almost entirely by machine,
(b) genuinely open — the fresh benchmark could falsify it, since a
fingerprint tool with duration/occupancy checks may match selective
performance, and the historical wrong-accept structure of argmax baselines
might have been an artifact of exposed development data, (c) not a novelty
claim, and (d) directly grounded in prior development-era evidence that
motivates exactly this test.

### SYSTEM CLAIM vs GENERAL SCIENTIFIC CLAIM

- **System claim (measurable, primary):** as C-A above, scoped to RhythmAlign
  v1.2.0, the named frozen baselines, and the collected benchmark.
- **General scientific claim (conservative, stated once):** in reference-audio
  replacement for user-generated video, selective refusal converts alignment
  uncertainty into explicit abstention; whether that trade is worthwhile
  depends on the achieved (coverage, wrong-accept) operating point and the
  recovery cost, both of which are domain- and implementation-specific and
  must be measured rather than assumed. No claim is made that this structure
  generalizes to other systems or domains without equivalent measurement.

### Non-claims (explicit in the paper)

- No new alignment algorithm or DSP mechanism is contributed.
- No probability calibration: the system emits decisions and heuristic
  scores, not probabilities; no AUROC/calibration analysis is reported.
- No claim that ABSTAIN guarantees ACCEPT correctness; wrong accepts remain
  possible and are counted.
- No population-level user-preference or effort-savings claim from a 2-person
  pilot.
- No "first accessible audio synchronization" claim; editor-native sync and
  fingerprint tools exist and are compared.
- No zero-risk or safe-export guarantee; "selective" means measured refusal
  behavior, not certification.

## 4. Why the Rhythm-Game Domain Is / Is Not Defensible

Analysis of the owner's concern, academically:

- **Is the application too narrow?** As a *product* category, handcam
  editing is niche. As an *evaluation domain* it is defensible: the paper's
  unit of analysis is reference-audio replacement under consumer-capture
  degradation, which instantiates a broad problem class (UGC re-edits,
  cover/performance videos, any footage whose captured music must be
  replaced by a licensed clean master). The domain supplies the difficulty
  axis, not the contribution. Applied-system venues routinely accept
  single-domain evaluations when the task contract and failure analysis are
  generalizable in kind.
- **Can it function as a stress-test domain?** Yes, and this is its strongest
  justification: it naturally combines low music SNR, impulsive tapping,
  room/arcade interference, repeated musical structure, and consumer
  compression in a setting where timing ground truth is obtainable and the
  creator's production need is real. The audit's domain analysis supports
  this; nothing in prior research refutes it.
- **Which claims can generalize beyond the domain?** The evaluation
  methodology (independent marker-based timing GT; positive/negative/no-match
  strata; risk-coverage comparison of selective vs always-output systems),
  and — conditional on fresh results — the qualitative finding that
  always-output baselines make confident wrong placements under degraded
  capture while a selective system trades coverage for safety.
- **Which claims MUST stay rhythm-game-specific?** All magnitudes: coverage
  percentages, error distributions, wrong-accept counts, task times, and any
  statement about creators. These are domain measurements.
- **Does a small external probe help?** Marginally but cheaply. A probe of
  3–4 non-game clips (e.g., phone/laptop recordings of speaker playback in a
  different environment — dorm common room, street, cafe) demonstrates the
  benchmark *protocol* transfers to an adjacent UGC condition at trivial
  owner cost (~15–20 minutes, no participants). It is an existence check on
  contract transfer, explicitly NOT a generalization proof; the paper says
  exactly that. One extra domain cannot establish generalization, and this
  design does not pretend it can; but the probe converts the reviewer
  question "does this only work on arcade noise?" from rhetoric into a
  small answered measurement.

### DOMAIN VERDICT

**RHYTHM_GAME_PRIMARY_PLUS_SMALL_EXTERNAL_PROBE**

Rationale: `RHYTHM_GAME_ONLY_IS_DEFENSIBLE` would survive review with honest
scoping, but the probe's marginal cost is near zero and it directly blunts
the single most likely framing objection. `BROADER_DATASET_REQUIRED` is not
justified: a multi-domain dataset would multiply recording burden for a
modest paper whose claims are already domain-scoped, and it is exactly the
expansion the owner cannot afford.

## 5. Evaluation Architecture

Three layers with strictly different evidential weights. Layer A carries the
paper; Layer B supplies the decisive comparators inside Layer A plus one
owner-operated technical stratum; Layer C is supporting feasibility evidence.

### Layer A — Automatic Benchmark

Carries the primary quantitative evidence. Fully agent-executable after
material collection.

- **Unit of analysis:** one (recording, offered-reference) pair, scored
  against the pair's ground-truth stratum. Independence unit for all
  aggregation and uncertainty: the **song/source identity** (secondary
  strata: recording session, recording device). Multiple takes of one song,
  and multiple conditions derived from one session, are dependent measures
  and are aggregated as such; no pseudo-replication.
- **Populations:** (i) positive same-reference pairs — real acoustic
  recordings of playback whose true offset is established by the marker
  protocol (Section 7); (ii) wrong-reference (no-match) pairs — the same
  recordings offered a different song's reference, where any ACCEPT is a
  catastrophic wrong accept; (iii) optional small strata: same-song
  version-mismatch pairs, authentic in-game handcam takes with approximate
  manual GT, external-domain probe pairs.
- **Conditions** (chosen because each supports the claim, not for coverage of
  every possibility): ordinary room playback; low music level / tap-dominant
  capture; environmental interference (second playback source, disjoint from
  the reference pool); partial capture (playback started mid-song, truncation
  — created systematically by the playback harness); repeated-structure songs
  (a song-selection criterion: ≥3 songs deliberately chosen for heavy
  repetition, stressing placement uniqueness).
- **Systems under test, frozen before any final-data run:** RhythmAlign
  v1.2.0 (frozen release, both its natural decision modes reported:
  full-export policy and Analyze-Only numeric output); GCC-PHAT argmax;
  waveform normalized cross-correlation argmax; Panako fingerprint
  comparison (the engine behind SyncSink, scriptable CLI). All receive
  byte-identical trimmed audio (Section 7). No threshold or configuration
  may be tuned on final data under any outcome.
- **Mechanics:** agent-built harness decodes media, computes GT, generates a
  frozen manifest (hashes, strata, pair assignments), runs all systems, and
  writes raw per-pair JSON plus summary tables. The manifest is fixed before
  the first system run; single-pass execution; no per-case reruns.

### Layer B — System/Workflow Comparison

Two mechanisms:

1. **Technical arms inside Layer A** (agent-run): the always-output DSP
   baselines and the fingerprint tool above. These answer "is selectivity
   actually buying safety, or would a simple or fingerprinting method do as
   well?"
2. **Editor-native technical stratum (owner-operated, small):** the owner
   performs Kdenlive 26.08's documented native audio-reference alignment on
   8–10 benchmark pairs spanning strata, following a one-page written
   procedure; the resulting placement is read from the saved Kdenlive
   project file (MLT XML, machine-readable) and scored by the agent against
   GT. This measures the decisive practical substitute's technical success
   and operator time without faking GUI automation. Limitation stated in
   the paper: single operator (the owner), proxy for intended users.

Manual waveform alignment is NOT a technical arm (it cannot be automated
honestly); it appears only inside the pilot as part of recovery paths.
The full six-task, three-arm, eight-creator workflow comparison from the
audit is deliberately NOT conducted; its scientific role is covered by
Layer A's risk-coverage comparison plus the pilot's feasibility
observations.

### Layer C — Human Feasibility Pilot

Purpose-scoped, small, and honestly labeled (full protocol in Section 10):

- **Scale:** 2 creators × 4 fresh tasks each (8 task observations).
- **Purposes:** verify the workflow is understandable without training
  beyond the built-in help; measure approximate end-to-end task time;
  observe recovery behavior after ABSTAIN and after discovering a wrong
  reference; surface hidden interaction costs; validate that the comparator
  workflow is realistic; check that RhythmAlign does not obviously lack all
  workflow advantage.
- **What it explicitly cannot support:** population effort-savings,
  preference, usability or HCI conclusions, statistical comparison between
  workflows, generalization to creators at large. The paper reports it as a
  feasibility pilot with individual-level descriptive results.
- **Adequacy judgment:** 2×4 is sufficient *for this role* because nothing
  load-bearing rests on it — the claim was deliberately shaped so the
  benchmark carries the evidential weight. A larger study is NOT mandatory
  for the claim as designed; it would become mandatory only if the owner
  later chooses to claim population-level effort reduction (C-C), which
  this design rejects. If a 3rd/4th creator is trivially available, adding
  them strengthens robustness but is not required. Any human-participant
  work requires consent and a check of the institution's ethics/review
  requirements before recruitment; recruitment does not start in this
  design phase.

### Why this structure is scientifically legitimate

The audit's worry — that "eight people liked it" is weak evidence — is
answered by moving the load to evidence that does not depend on recruiting:
a benchmark with independently established ground truth is the same
evidential standard used in alignment-system literature (with the honesty
addition of a no-match stratum and refusal accounting, which many published
alignment evaluations omit). The pilot then answers the one question the
benchmark cannot: whether the selective workflow survives contact with real
users at plausible cost. The structure is SYSTEM = PRIMARY, HUMAN =
SUPPORTING by construction, not by aspiration.

## 6. Fresh Dataset Design

Historical corpora remain development/regression assets only. The following
is the fresh acquisition design. All media are real acoustic captures of
loudspeaker playback through consumer devices; no digital insertion of the
clean track into noise is used for any scored case.

### Feasibility pilot dataset (development; never final evidence)

| Property | Specification |
|---|---|
| Songs | 4, source-disjoint from all final songs |
| Real recordings | 6 takes (≈1 ordinary, 1 stressed per song; 1 repeat take) |
| Positive pairs | 6 |
| Wrong-reference pairs | 4 (constructed from the same takes, rotated assignment) |
| Conditions | ordinary + low-music + 1 interference + 1 partial |
| Sessions/devices | 1–2 sessions, ≥1 device (pilot need not span devices) |
| GT | full marker protocol (validates the GT machinery itself) |
| Purpose | validate harness, GT precision, trimming, scoring; dry-run pilot tasks |

### Final benchmark dataset (test; frozen protocol, untouched until freeze)

| Property | Specification |
|---|---|
| Unique songs | 10 clean source identities (owner's licensed library); ≥3 deliberately repetitive-structure; protocol requires logging exact source version |
| Real positive recordings | 22–24 takes: every song ≥2 takes (1 ordinary + 1 stressed), plus 2 partial takes and 2 device-variation takes |
| Positive conditions | ordinary room (10), low-music/tap-dominant (6), interference (4), partial (2), device variation (2) |
| Wrong-reference pairs | 22–24 directed no-match pairs — each take offered a different song's reference via a pre-published rotation table; constructed at analysis time, zero extra recording burden |
| Optional strata | 2–4 same-song version-mismatch pairs (needs 2–3 songs with a second version); 2–4 authentic in-game handcam takes (approximate manual GT stratum); 3–4 external-domain probe clips |
| Reliability takes | 2 songs recorded twice under the same condition — GT/pipeline reliability only, reported separately, never counted as independent samples |
| Sessions/devices | ≥3 sessions, ≥2 recording devices (e.g., two phones or phone + camera), ≥2 rooms if feasible |
| Exclusions | pre-declared categories: marker GT failure, ambient contamination by reference-pool material (interference sources chosen disjoint from all references), owner-declared capture defects — all logged with reasons decided blind to system outputs |

Independence limits stated in the paper: 10 songs is the population of
source identities; all within-song counts are dependent; the constructed
wrong-reference frequency is not a measured creator mistake rate; optional
strata are existence checks.

**Owner recording burden:** the playback harness (agent-built) plays
[marker chirp → 60–90 s music segment → marker chirp] from the owner's PC
speakers; the owner starts a recording device, clicks play, taps a surface
during tap-dominant takes (honest labeling: taps are performed during
playback, simulating handcam acoustics — the paper says exactly this),
stops recording. ≈2.5 min per take → ≈60–75 min of active recording across
3–4 sessions, plus sourcing clean song files the owner already possesses,
plus ~15–20 min for the external probe. This replaces the audit's more
elaborate two-annotator apparatus with a machine-computed equivalent
(Section 7).

## 7. Ground Truth Protocol

Requirement: timing GT independent of RhythmAlign and of every comparator.

**Method: end-of-take sync marker with playback-buffer-exact structure.**

1. The harness renders one playback buffer per take: a short broadband chirp
   (≈0.5–1 s, unique, high amplitude) followed by silence, the music
   segment, silence, and a final chirp. All timings between chirps and music
   are sample-exact by construction — one buffer, one playback.
2. The recording device captures the take. GT is computed by matched
   filtering the known chirp against the recorded audio: the final chirp's
   detected position t_chirp locates the buffer inside the recording
   timeline; GT offset = t_chirp − (buffer-relative position of music
   start). Only ONE detected marker is required; the leading chirp, when
   present, yields an independent second estimate (disagreement beyond a
   pre-set bound invalidates the take's GT). Recording start time is
   irrelevant.
3. Speaker-to-microphone propagation delay applies identically to chirp and
   music, so buffer-relative placement equals the placement a correct
   replacement export must use. GT therefore measures the task-relevant
   quantity, not the playback device's clock.
4. **Trimming:** chirp regions are removed from every recording before any
   alignment system sees it; all systems receive identical trimmed audio.
   The benchmark therefore contains no marker artifacts, and "markers
   changed the systems' behavior" is structurally excluded. Trim boundaries
   come from the GT machinery, never from any alignment system.
5. **Precision:** matched-filter detection on the native recording rate is
   sub-millisecond; the conservative documented uncertainty is ±5 ms plus
   validation on synthetic renders with known offsets and on the repeat
   takes. This beats the audit's ±33 ms manual-interval proposal and removes
   the two-annotator labor.

**GT strata (never collapsed into one accuracy number):**

| Stratum | Label source | Scoring rule |
|---|---|---|
| Exact/near-exact (marker takes) | matched filter, ±5 ms documented | CORRECT_ACCEPT = accepted and \|error\| ≤ tolerance; tolerance 100 ms primary, sensitivity at 50/150 ms (editorial-task criterion, not a perceptual threshold) |
| Approximate (authentic handcam takes, optional) | owner's blind manual annotation in an audio editor, uncertainty interval ±0.25–0.5 s, documented before system runs | correct only if the entire uncertainty interval satisfies the criterion; boundary cases indeterminate; reported separately |
| Pairing-only / no-match (wrong-reference, version-mismatch) | pre-published source log establishing the offered reference is not the performed music (version-mismatch: not the performed version) | any ACCEPT = WRONG_ACCEPT (catastrophic); reported separately from offset error |
| GT-failed / unknown | marker detection failed, or ambient contamination suspected | excluded from scored results with logged reason; never silently dropped |

Player taps are never used as timing evidence; no system's output is ever
used as GT; annotators and the owner never see system outputs before labels
are frozen.

## 8. Comparator Selection

| Comparator | Question it tests | Verdict | Automation | Refusal support | Same task contract? |
|---|---|---|---|---|---|
| GCC-PHAT argmax | Does the canonical simple method, forced to always output, already dominate? Is the historical wrong-accept structure real or a dev-data artifact? | **ESSENTIAL** — the scientific control for the selectivity claim | Fully (agent) | No (argmax; no-match only via external policy, not used) | Yes: same pair manifest, same trimmed audio, same GT |
| Normalized cross-correlation argmax | Does the conclusion hold across the simple-baseline family? | **OPTIONAL** (near-zero marginal cost; include unless run time is prohibitive) | Fully (agent) | No | Yes |
| Panako fingerprint CLI (engine behind SyncSink) | Do modern fingerprint systems with duration/occupancy-style checks already achieve selective-level safety at high coverage? This is the strongest technical threat to C-A. | **ESSENTIAL** (as a technical arm; SyncSink GUI itself only if the CLI path fails) | Fully or near-fully (CLI); fallback = small owner-run subset, documented | Implicit: match reporting can be empty; scored under its native behavior, never forced to argmax | Yes, with the honest caveat that fingerprint tools make occurrence claims, not whole-song replacement offsets; scored per its actual output semantics, per the audit's warning |
| Kdenlive 26.08 native audio-reference alignment | What does the editor the creator would actually use achieve, at what operator cost? | **ESSENTIAL** (owner-operated technical stratum + pilot arm) | GUI action by owner; result scored automatically from project XML | Its failure modes are operator-visible; recorded as observed | Yes for placement; export/mix steps differ and are accounted in pilot time |
| Manual waveform alignment | Automation's benefit floor | Pilot-only recovery path; **REJECT** as a benchmark arm (cannot be automated honestly) | No | n/a | Yes within pilot |
| SyncSink GUI as a third pilot arm | Full workflow comparison vs fingerprint workflow | **REJECT** for the pilot (doubles participant burden for a non-load-bearing question); the Panako technical arm already answers the fingerprint question | — | — | — |
| Second commercial editor (e.g., DaVinci Resolve auto-sync) | Editor generality | **REJECT** for minimum paper; optional in stronger version | — | — | — |
| Semi-synthetic digital-insertion cases | Harness/contract sanity checks | **OPTIONAL**, appendix-only, zero evidential weight | Fully | — | Dev-only |

The strongest comparator reflects real creator practice: Kdenlive native
alignment is what a handcam creator would actually do instead of
RhythmAlign; GCC-PHAT/Panako establish where the selective system sits
among technically credible alternatives. No comparator is included because
it is easy to beat: the two ESSENTIAL technical comparators are exactly the
ones most likely to falsify C-A.

## 9. Metrics

Minimal set; every count reports its denominator.

**Layer A (primary):**

| Metric | Definition | Notes |
|---|---|---|
| Positive coverage | CORRECT_ACCEPT ∪ SAFE_ABSTAIN split of positives; coverage = accepted positives / positives | with GT-stratum split |
| Conditional offset error | median, IQR, and max \|error\| among accepted positives | exact-GT stratum |
| Wrong-reference acceptance rate | accepted no-match pairs / no-match pairs | the catastrophic-error headline; exact counts printed in full |
| SAFE_ABSTAIN rate on negatives | refused no-match pairs / no-match pairs | selectivity's benefit side |
| Wrong-accept risk among accepts | WRONG_ACCEPT / (CORRECT_ACCEPT + WRONG_ACCEPT), per system | undefined-when-empty stated explicitly |
| Overall completion under accept-all | fraction of all pairs ending in a correct placement if the user accepts every system output | the always-output systems' real end-to-end number |
| Risk-coverage position | each system as one frozen point (RA additionally at its Analyze-Only mode) | no threshold sweeps on final data; any post-hoc curve is labeled descriptive and non-selectable |
| Latency | wall-clock per pair | secondary |

**Layer B additions:** Kdenlive technical success rate and operator time on
its stratum; Panako per-pair output semantics table.

**Layer C (pilot, per task):** total task time (active vs wait separated);
interventions and retries; magnitude of final manual offset correction
(measured against GT); task success (correct-reference export within
tolerance); recovery time and steps after ABSTAIN or after wrong-reference
discovery; one optional single-item effort rating. No SUS, no NASA-TLX —
neither supports the claim at N=2 and both imply an HCI rigor the pilot
does not have.

## 10. Human Pilot Protocol

- **Participants:** 2 adult rhythm-game creators (the population the tool
  targets), recruited from the owner's community. Consent obtained; the
  institution's ethics/review requirement checked before recruitment
  (flagged as possibly required depending on university and venue; not
  started in this design). Pilot participants and pilot songs are excluded
  from all final evaluation.
- **Tasks (4 per creator, all fresh pilot material, each a different song):**
  1. RhythmAlign ordinary: replace captured audio using full Export.
  2. Kdenlive ordinary: same goal using native alignment + normal editing.
  3. RhythmAlign challenge: the offered reference is wrong; the correct
     reference is present in the task materials. Observe refusal behavior
     (expected ABSTAIN, but a wrong ACCEPT is recorded honestly as such)
     and the full recovery path to a correct final export.
  4. Kdenlive challenge: same task in the editor.
- **Counterbalancing (lightweight):** creator A order = RA-ord, K-ord,
  RA-chal, K-chal; creator B = mirrored (K first, RA first within pair
  swapped). Fixed script; no assistance favoring either workflow; equivalent
  one-page instructions; 10-minute cap per task with a capped-completion
  score (assigned limit for failed/incorrect tasks; raw time also reported);
  short background question on editing experience.
- **Measurement:** observer timer + automatic logs where possible; final
  outputs scored blind by the agent against GT; a short post-task question
  on what ACCEPT/ABSTAIN meant to the creator (free text, analyzed
  descriptively).
- **Conclusions the pilot CANNOT support** (stated verbatim in the paper):
  any population-level effort or preference claim; any statistical workflow
  comparison; usability generalization. With two participants, order and
  individual differences cannot be separated from workflow effects; the
  pilot supports feasibility statements, observed cost ranges, and failure/
  recovery description only.
- **Larger human study?** Not required for C-A. Required only if the owner
  later pursues C-C (population effort claims), which this design declines.

## 11. Agent / Owner / Participant Work Split

| Work item | AGENT (GLM-5.3 Flash / Codex) | OWNER | PARTICIPANT | ETHICS/FACULTY |
|---|---|---|---|---|
| Playback/GT harness, benchmark scripts | **builds** | reviews | — | — |
| Recording sessions | prepares scripts, checklists, session log templates | **executes** (~1.5 h total) | — | — |
| GT computation, trimming, manifest, hashing | **executes** | — | — | — |
| RhythmAlign + GCC-PHAT + NCC + Panako runs | **executes** | — | — | — |
| Kdenlive technical stratum (8–10 pairs) | scores results from project XML | **operates GUI** (~1 h) | — | — |
| Pilot facilitation | materials, scoring, logs | **facilitates** (~2 h) | 2 creators × ~45 min | **consent + review check required before recruitment** |
| Statistics, plots, tables | **executes** | reviews | — | — |
| Robustness/sensitivity analyses | **executes** | — | — | — |
| Reproducibility package, permissions plan | **drafts** | approves, arranges media access for review | — | — |
| Paper drafting | **drafts methods/results** | owns claims, reviews, submits | — | — |

OWNER_REQUIRED work is irreducible without misrepresentation: real acoustic
recordings must be physically captured; the editor comparator must be
genuinely GUI-operated; pilot facilitation requires a human experimenter.
Everything else is agent-executable. Qualitatively, roughly **80–90 % of
total task work is agent-executable** by this design (harness, GT, all
technical runs, analysis, drafting), with the remainder split between owner
recording/comparator operation (~an afternoon plus an evening) and the
pilot (~half a day including two 45-minute sessions). No false precision is
implied by these ranges.

## 12. Statistical Analysis Plan

Proportional to the design, pre-declared:

- **Primary reporting:** raw counts with denominators; exact catastrophic
  failure counts (wrong accepts) per system; per-pair tables in the
  reproducibility package.
- **Distributions:** median/IQR of conditional offset error per system and
  stratum; all accepted-pair errors shown (no summary-only reporting).
- **Paired comparison:** systems run on identical pair manifests, so
  discordant-pair counts between RhythmAlign and each baseline are exact
  and reportable; if any inferential test is used, an exact McNemar/
  binomial test on discordant negative pairs is the single pre-declared
  test. Nothing else is tested at this N.
- **Uncertainty:** song-level bootstrap (resampling 10 source identities)
  for coverage and wrong-accept rates, reported with the explicit caveat
  that intervals will be wide and are descriptive aids, not evidence of
  equivalence or difference. No iid assumptions across takes of one song.
- **Sensitivity:** tolerance 50/100/150 ms reported side by side.
- **Pilot:** descriptive individual results only; no inferential claims.
- **Source-level aggregation** shown alongside pair-level results for every
  headline number.

## 13. Reviewer Threat Model

| Objection | Fatal? | Minimum evidence that answers it |
|---|---|---|
| "This is only a rhythm-game tool." | No | General problem framing; measured task characterization; external probe stratum showing the protocol transfers to an adjacent UGC condition (existence check, honestly labeled) |
| "The alignment algorithm is not novel." | No — claim never made | Paper claims system-level evidence; methods section describes known ingredients accurately; prior triage cited |
| "Why not just use editor X's native sync?" | **Yes if unanswered** | Kdenlive technical stratum with measured success/offset error/operator time + pilot arm |
| "Why not use fingerprints?" | **Yes if unanswered** | Panako technical arm on the full benchmark |
| "Dataset too small." | Partially | 22–24 positives / 22–24 negatives at 10 source identities with exact counts; scope claims matched to scale; benchmark is the honest minimum for a modest paper — cannot fully defeat this objection, only bound it |
| "Same songs reused too often." | No | ≥2 takes/song justified as condition variation; all inference at song level; dependency stated everywhere |
| "Benchmark is artificially constructed." | No | Real acoustic captures, not digital insertion; taps performed during playback disclosed; marker chirps trimmed before all systems; partial/interference conditions are realistic production situations; approximate-GT authentic takes anchor realism |
| "Two users are not an HCI study." | No | Pilot explicitly labeled feasibility-only; no HCI claim made; claim structure shifted to Layer A |
| "ABSTAIN just hides failures." | **Yes if recovery cost unmeasured** | Pilot measures recovery time/steps; completion-under-accept-all metric reports end-to-end correctness for all systems; refusal never reported without its measured cost |
| "System requires recovery, so time savings disappear." | Honest risk, not fatal | Reported as measured; if recovery dominates, that is the finding (and a kill-criterion input); the paper does not depend on a time-savings claim |
| "Results may not generalize." | No | Explicit non-claims; conservative general scientific claim; probe as existence check; domain-scope stated in abstract and limitations |
| "Ground truth is circular." | **Yes if GT fails** | Marker GT independent of all systems; precision validation; GT-failure exclusions logged blind |
| "No one can inspect the evidence." | Partially | Reproducibility package: manifests, hashes, scripts, per-pair JSON; media access arranged for reviewers under permission constraints (commercial music cannot be openly released; stated, with openly distributable synthetic fixtures) |

## 14. Kill Criteria

Pre-declared. If any fires, the applied-system paper stops; no goalpost
movement, no test-set retuning, no task replacement. The route-G backup
(undergraduate empirical case study of the falsification history) remains
available without new data.

1. **Comparator dominance:** Panako (or GCC-PHAT with a trivially defensible
   no-match rule, if one exists without tuning) achieves ≥ RhythmAlign's
   positive coverage with ≤ its wrong accepts on the fresh benchmark.
2. **Safety collapse:** RhythmAlign produces ≥ 3 wrong accepts among the
   ~22–24 wrong-reference pairs (i.e., the released selectivity does not
   transport to fresh material).
3. **Coverage collapse:** RhythmAlign's positive coverage on fresh material
   falls below ~50 % while an always-output baseline remains materially
   higher — selectivity without useful coverage is not a system result.
4. **GT infeasibility:** marker-based GT cannot be established at the
   documented precision on real recordings (repeated GT validation failure).
5. **Editor parity with no lesson:** Kdenlive native alignment matches
   RhythmAlign on correctness in the technical stratum AND the pilot shows
   no meaningful effort/correctness/recovery difference or informative
   failure behavior — the system contributes nothing measurable.
6. **Framing failure:** if, after pilot and benchmark, no bounded claim
   survives (no safety advantage, no workflow advantage, no transferable
   failure insight), the paper stops rather than repackaging.

Note the asymmetry: a negative result on C-A (e.g., kill 1 or 2 firing with
clean methodology) is itself a publishable bounded finding — "selectivity
did not transport to fresh acoustic material" — suitable for the backup
route; it is a stop for THIS paper, not for the research line.

## 15. Minimum Credible Paper

Everything that must exist before writing begins:

1. Frozen v1.2.0 subject; pinned comparator versions (Kdenlive 26.08 build,
   Panako release, GCC-PHAT/NCC reference implementations); recorded
   machine/decoder configuration.
2. Completed feasibility pilot (benchmark dry run + 2-creator human pilot);
   protocol frozen afterwards; pilot data excluded from final results.
3. Fresh final benchmark collected per Section 6: 10 songs, 22–24 positive
   takes, 22–24 constructed wrong-reference pairs, optional strata as
   available, ≥3 sessions, ≥2 devices; provenance ledger with hashes,
   session log, exclusion log (blind reasons).
4. GT computed and precision-validated per Section 7; strata assigned;
   frozen manifest published before first system run.
5. All Layer A runs executed single-pass on the frozen manifest with raw
   JSON retained (RhythmAlign both modes, GCC-PHAT, NCC, Panako).
6. Kdenlive owner-operated technical stratum complete (8–10 pairs, project
   XML scored).
7. Pilot outputs scored blind; pilot descriptive analysis complete.
8. Pre-declared analyses produced: counts, distributions, paired discordant
   counts, song-level bootstrap intervals, tolerance sensitivity, plots and
   paper-ready tables.
9. Reproducibility package + media permissions plan (reviewer access
   arrangement; open synthetic fixtures).

Only then does drafting start, with claims scoped exactly as Section 3.

### Three study sizes

| Size | Content | Status |
|---|---|---|
| MINIMUM PILOT | Pilot dataset (4 songs, 6 takes, 4 negatives) + 2 creators × 4 tasks | Protocol-validation gate; dev-only |
| MINIMUM CREDIBLE PAPER | As Section 6 final benchmark + Section 10 pilot + Section 8 essential comparators | **RECOMMENDED TARGET** |
| STRONGER OPTIONAL VERSION | 16 songs, ≥4 creators × 4–6 tasks, manual-waveform pilot arm, second editor, D1 ablation appendix | Only if recruitment and burden turn out easy; adds robustness, not a different claim class |

The recommended target optimizes credibility × feasibility × asset reuse ×
low recruitment burden: it reuses the released system, the archived tooling
patterns, and the audit's protocol skeleton; it asks ~3 hours of owner
recording and 2 participants; and its claim survives even a partially null
benchmark (an honest negative transport result remains publishable at the
undergraduate/modest-specialist level).

## 16. Recommended Next Experiment

Exactly one:

> **Benchmark-machinery shakedown (Layer A dry run, no participants).**
> Build the playback/GT harness and scoring pipeline; owner records the
> pilot dataset (4 songs, ~6 takes incl. 2 partial/interference takes,
> ~20 minutes of recording); agents compute marker GT, validate its
> precision on synthetic renders and repeat takes, trim, freeze a pilot
> manifest, and run RhythmAlign v1.2.0, GCC-PHAT, NCC, and Panako
> single-pass over the pilot pairs; produce a mini risk-coverage table and
> a GT-precision report. Success gates: GT uncertainty within the documented
> bound on ≥5/6 takes; all four systems execute on the identical trimmed
> inputs; scoring pipeline reproduces known-offset sanity cases. This is
> the cheapest experiment able to kill the design early (kill criteria 4
> and partially 2/3), and it precedes any human contact.

### STUDY VERDICT
HUMAN_LIGHT_DESIGN_VIABLE

### PAPER FRAMING
An applied-system study of selective reference-audio replacement in degraded
user-generated video, evaluated primarily by a benchmark with independent
timing ground truth and supported by a small creator feasibility pilot, with
rhythm-game handcam recording presented honestly as the primary stress-test
domain.

### DOMAIN STRATEGY
RHYTHM_GAME_PRIMARY_PLUS_SMALL_EXTERNAL_PROBE

### CORE CLAIM
On fresh, independently timed real-acoustic recordings from the stress-test
domain, frozen RhythmAlign v1.2.0 achieves a lower catastrophic-error rate
(confident wrong placements, including wrong-song accepts) than established
always-output alignment baselines while retaining useful positive coverage,
and the cost of its refusals is quantified and bounded in a creator
feasibility pilot; no algorithmic novelty is claimed, and all magnitudes
remain domain-scoped.

### PRIMARY EVIDENCE
A frozen-manifest Layer A benchmark: ~22–24 positive pairs and ~22–24
wrong-reference no-match pairs from 10 source-disjoint songs across ≥3
sessions and ≥2 devices, scored against marker-based ground truth
independent of every system, comparing RhythmAlign (both decision modes)
against GCC-PHAT, NCC, and Panako fingerprint outputs, with exact
catastrophic-failure counts, conditional offset-error distributions, and
song-level aggregated uncertainty; supplemented by an owner-operated
Kdenlive technical stratum and a 2-creator × 4-task feasibility pilot
measuring recovery cost after refusal.

### HUMAN BURDEN
2 adult creators × 4 tasks (~45 min each) for the pilot; owner recording of
~26–30 takes across 3–4 sessions (~1.5–2 h active) plus ~1 h operating the
Kdenlive technical stratum and ~2 h facilitating the pilot; no large
recruitment, no questionnaire battery; consent and an ethics/review check
before any participant contact.

### AGENT-AUTOMATABLE FRACTION
Roughly 80–90 % of total task work: harness construction, ground-truth
computation, trimming, manifests and hashing, all technical benchmark runs,
the Kdenlive output scoring, statistics, plots, reproducibility packaging,
and methods/results drafting are agent-executable; the irreducible remainder
is physical recording, genuine GUI comparator operation, and pilot
facilitation, which cannot be automated without misrepresenting real usage.

### FRESH DATA NEEDED
Final: 10 source-disjoint songs; 22–24 real acoustic positive takes
(ordinary / low-music / interference / partial / device-variation), ≥3
sessions, ≥2 devices; 22–24 wrong-reference pairs constructed from the same
takes via a pre-published rotation; optional 2–4 version-mismatch pairs,
2–4 authentic handcam takes (approximate-GT stratum), 3–4 external-domain
probe clips, and 2 repeat takes for GT reliability. Pilot: 4 songs, 6 takes,
4 negatives, fully disjoint from final songs.

### ESSENTIAL COMPARATORS
GCC-PHAT argmax (always-output control); Panako fingerprint CLI (strongest
technical threat); Kdenlive 26.08 native audio-reference alignment
(owner-operated technical stratum + pilot arm); NCC argmax included as a
near-free secondary baseline.

### BIGGEST REVIEWER RISK
That the selective-safety advantage evaporates on fresh material: the
historical wrong-accept structure of argmax baselines and RhythmAlign's
abstention behavior were both observed on development-exposed data, so a
reviewer's deepest challenge is "your central trade may be an artifact of
your own development history." The design answers this the only honest way —
a source-disjoint, frozen, single-pass benchmark — but if Panako or GCC-PHAT
matches selective safety at higher coverage, or RhythmAlign abstains so
often that coverage collapses, the primary claim dies and the paper must
stop or fall back to the route-G historical case study. The secondary risk
is dataset scale: ten songs bounds every generalization statement, which is
why the claims are scoped to the collected benchmark and framed as a
measured domain case, never as field-wide conclusions.

### KILL CONDITION
The paper stops if the fresh benchmark shows comparator dominance
(equal-or-better safety at equal-or-better coverage by an always-output or
fingerprint baseline), unacceptable wrong-accept transport (≥3 wrong accepts
among ~22–24 negatives), or positive coverage below ~50 % for RhythmAlign;
if marker ground truth cannot be validated at documented precision; if
Kdenlive parity combines with a pilot showing no effort, correctness, or
recovery advantage and no informative failure behavior; or if no bounded
claim survives — with no retuning, no task replacement, and no goalpost
movement after pilot results, and with the route-G backup remaining
available.

### NEXT EXPERIMENT
Benchmark-machinery shakedown: build the playback/GT harness, owner records
the 4-song pilot set (~20 min), agents validate GT precision, freeze the
pilot manifest, and run RhythmAlign, GCC-PHAT, NCC, and Panako single-pass
on identical trimmed inputs, producing a mini risk-coverage table — no
participants, no final data, no threshold changes.

### FILE CREATED
docs/research/applied_system/HUMAN_LIGHT_STUDY_DESIGN.md
