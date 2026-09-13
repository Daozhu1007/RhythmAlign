# Fresh-Data Pilot Plan

Status: PLANNING ONLY — no pilot data collected, no participants, no
recruitment, no production changes. This document designs the smallest
fresh-data pilot that can re-freeze the real-device marker-QC and drift
thresholds, validate the acoustic benchmark protocol on multiple devices,
integrate Panako as a comparator, and decide whether the final benchmark
protocol is ready to freeze.

- Study-design authority: `HUMAN_LIGHT_STUDY_DESIGN.md` (Sections 6–8, 16).
- Machinery authority: `BENCHMARK_SHAKEDOWN.md` (verdict
  `SHAKEDOWN_PASS_WITH_FIXES`; one real-device acoustic round trip, GT_OK,
  −16.5 ppm, provisional marker gate 0.15, provisional drift gate ±500 ppm —
  both explicitly NOT final).
- Branch: `research/applied-system-paper`.
- Everything in this pilot is PILOT_ONLY / NOT_FINAL_PAPER_EVIDENCE. Pilot
  data can never be relabeled as final confirmatory evidence, and pilot
  songs are development-exposed forever (they must not appear in the final
  benchmark).

The engineering-provisional constants in force when this pilot starts
(`experiments/applied_system/marker_protocol.py`): marker confidence gate
0.15, drift tolerance ±500 ppm, mapping-disagreement gate 10 ms, chirp
0.75 s linear sweep 1→9 kHz @ 48 kHz, guards 1.0 s, trim margins 50 ms.
None of these may be promoted to final study constants without the fresh
multi-device evidence this pilot collects — and none may be tuned after
final data collection starts (Section 15).

---

## 1. Pilot Objective

Five questions, in priority order. The pilot exists to answer these and
nothing else; alignment performance is recorded for debugging only.

- **A. Marker-confidence stability across recording paths.** Are genuine
  marker matched-filter confidences stable enough across several realistic
  consumer recording paths (devices × rooms × playback sources) to freeze a
  final detection threshold by rule, with genuine and competing confidence
  distributions well separated?
- **B. Drift tolerance across realistic devices.** What clock-scale error do
  realistic consumer DAC→ADC chains actually exhibit, is it repeatable
  within a device, and does a rule-derived tolerance keep the fixed-offset
  model defensible?
- **C. Dual-marker GT survival.** Does the chirp|guard|payload|guard|chirp
  protocol — exactly-two-candidate rule, scale QC, mapping agreement,
  trim/leakage machinery — survive different phones, microphones, and
  playback devices on real music payloads (not only the synthetic
  shakedown fixture)?
- **D. Benchmark condition practicality.** Are the final benchmark's
  condition definitions (ordinary, low playback level, impulsive taps,
  environmental interference, mid-song/partial placement, alternate
  playback source) executable by the owner in one pass, without confusion,
  at the estimated time cost?
- **E. Panako integration.** Can Panako 2.1 be installed and run through
  WSL2 (Docker fallback) with pinned provenance, native match/no-match
  semantics preserved, and a pre-declared output→decision mapping — and is
  its placement precision adequate for the 100 ms offset task, or must its
  role be scoped to identification/selectivity?

Explicit non-goals: no wrong-accept rate estimation, no coverage
estimation, no participant contact, no final media collection, no changes
to frozen RhythmAlign v1.2.0.

## 2. Device Calibration Design

**Recommendation: `THREE_DEVICE_CALIBRATION_RECOMMENDED`** — three owner-
owned recording devices, two acceptable as a documented floor.

Why three: the provisional 0.15 confidence gate currently rests on ONE
device chain (one phone, one room, one occasion). Freezing a final
threshold from a second single device would just relocate the same
weakness. Three devices give the freeze rule three independent ADC/AGC /
codec chains — ideally spanning manufacturers — so the "weakest genuine
marker" input G and the "strongest competing content" input B of Section 3
are worst-case observations across paths rather than a single chain's
accident. Three devices also give the drift rule three independent clock
pairs, which is the minimum for distinguishing "one odd device" from "how
consumer clocks behave". No recruitment is involved: all devices are
things the owner already possesses (primary phone; a second phone, tablet,
or laptop internal microphone; one more phone/tablet/camera). If only two
genuinely exist, the pilot proceeds on two and the frozen protocol carries
an explicit "calibrated on two device chains" limitation; the freeze rule
itself does not change.

Minimum useful takes per device (this is threshold calibration, not a
publication sample — large N is explicitly avoided):

| Quantity needed | Where it comes from | Takes required |
|---|---|---|
| Genuine marker confidence distribution | Both markers of every valid take | 2–4 takes/device → 4–8 marker measurements |
| Max non-marker competing correlation | Ungated diagnostic peak trail of every take (`top_marker_peaks`, leakage re-scan) | every take, no extra cost |
| Clock-scale drift + within-device repeatability | One `scale_error` per take | 2–4 takes/device |
| Same-condition repeatability | An ordinary take repeated back-to-back | strict repeat pair on ≥2 devices |
| GT success/failure rate | Per-take GT verdict | all takes (small-N gate: any unexplained failure is investigated, not averaged away) |

Device roles (owner's actual hardware substituted freely; labels fixed):

- **D1** — primary phone (the validated shakedown chain). 5 takes.
- **D2** — second phone / tablet / laptop internal mic. 3 takes.
- **D3** — third device (tablet, camera, or second laptop). 4 takes.

Playback sources are a second axis: **P1** = PC speakers (the standard
harness path for the final benchmark), **P2** = a phone loudspeaker (one
take, tests playback-path generality). Total: 12 takes (Section 5).

## 3. Marker Confidence Freeze Rule

The final gate is computed from pilot data by a pre-declared rule — it is
NOT chosen as a round number and NOT hand-picked. Crucially, the pilot
analysis trail (`top_marker_peaks` diagnostics + per-marker trajectory
checks) records the UNGATED peak structure of every take, so the freeze
rule sees the true distributions even where the provisional 0.15 gate is
in force during ingestion. Nothing is lost to the gate.

Definitions, pooled over ALL valid pilot takes on ALL devices and
conditions (worst-case across paths):

- **G** = minimum confidence over all genuine markers (the exactly-two
  accepted markers of every GT_VALID take, both markers counted).
- **B** = maximum normalized matched-filter peak over all recorded
  non-marker content: every diagnostic peak outside ±1 template length of
  a true marker, plus every post-trim leakage re-scan maximum. Capture-edge
  partial-overlap lags are structurally excluded (protocol rule, not
  tuning).

**Freeze rule (band rule):**

1. Rejection floor `T_low = 3 × B` — the gate must sit at least 3× above
   the strongest competing content observed on real audio (same margin
   logic that produced the provisional 0.15 from B = 0.049).
2. Accept ceiling `T_high = 0.8 × G` — the gate must sit at least 20%
   below the weakest genuine marker observed on any device.
3. Feasibility: the band is non-empty iff `G/B ≥ 3.75`. If any device
   chain violates this, the distributions overlap too much for any single
   gate — that is a KILL/re-design signal (Section 14), never an invitation
   to nudge the rule.
4. Frozen value: `T = sqrt(T_low × T_high)`, the log-band midpoint —
   it maximizes the minimum relative margin on both sides. Missing a
   genuine marker and accepting a phantom both fail the take (exactly-two
   rule), so max–min robustness is the right objective; the result is a
   data-derived value, rounded to two decimals for documentation only.

Worked example on the existing single-device evidence (G = 0.226,
B = 0.049): band [0.147, 0.181] → T ≈ 0.16, close to but not identical to
the provisional 0.15. The pilot recomputes G and B across devices and
conditions and freezes whatever the rule then yields — 0.11 and 0.21 are
equally acceptable outcomes.

**Multi-signal validity (frozen together with T):**

- Exactly-two-candidate rule: mandatory, unchanged (structural).
- Full-template-overlap eligibility: mandatory, unchanged (structural).
- Sweep-trajectory corroboration (physics-based, immune to codec phase
  damage): decision rule, fixed NOW — if every genuine marker across the
  pilot corroborates (0.80 ≤ slope ratio ≤ 1.20 and r² ≥ 0.75) AND no
  non-marker diagnostic peak corroborates, the trajectory check is frozen
  as a GATING requirement (both accepted markers must corroborate). If it
  is noisy on any device, it is frozen as a recorded diagnostic with no
  gate, and gate robustness rests entirely on the band rule. One uniform
  policy for all devices; decided at pilot freeze time from pilot data
  only.
- Mapping-disagreement gate (10 ms) and third-party max NCC: recorded on
  every take; the 10 ms gate is re-affirmed unless a valid take shows
  borderline behavior, in which case the value is re-derived from the
  observed distribution with ≥3× margin and the reason documented.
- Per-device feasibility note recorded in the frozen spec: the observed
  per-device `G/B` ratios (the margin each chain actually delivered).

Anti-tuning clause: T and every policy above are computed once from pilot
measurements and frozen before any final media exists. Final benchmark
outcomes may not touch them under any result.

**Output of this section: a frozen marker-QC specification** = {T, count
rule, overlap rule, trajectory policy, mapping-disagreement gate, per-
device margins}, written into the protocol constants and the frozen
manifest before final data collection.

## 4. Drift Freeze Rule

The provisional ±500 ppm gate was set from simulated degradations plus a
plausibility argument; one real device then measured −16.5 ppm. The final
gate must have an interpretable reason, not "our devices happen to pass".

**Interpretable floor from the task contract.** RhythmAlign is a
fixed-offset aligner: unmodeled clock drift over a take of duration D
produces placement error up to `ppm × 1e-6 × D`. The final benchmark's
longest takes are ≈90 s, and the scoring tolerance is 100 ms. Requiring
drift-induced error ≤ 10 ms (≤10% of tolerance, comfortably inside the
50 ms sensitivity bound) gives:

    ppm_floor = 0.010 s / (90 s × 1e-6) ≈ 111 ppm

Any tolerance below ~111 ppm would reject devices whose drift the task can
actually absorb — so 111 ppm is the floor regardless of how clean the
pilot devices look.

**Freeze rule:**

1. Measure `scale_error` on every pilot take (12 estimates across 3
   device chains, 2 playback sources, stressed conditions included).
   Record per-device maxima and within-device spread; measurement error of
   the scale statistic is <1 ppm (sub-sample refinement over ≈3.1 M-sample
   separations) and is negligible.
2. `D_max` = maximum |scale_error| observed across all pilot takes.
3. `T_drift = max(3 × D_max, 111 ppm)` — 3× headroom over the worst real
   observation, never below the interpretable floor.
4. Detectability cap: `T_drift ≤ 1000 ppm`. The shakedown probe showed
   chirp detection stays robust to ≈1000 ppm and decorrelates beyond
   ≈1200 ppm, so the gate must live inside the detectable band to remain
   enforceable.
5. Cap breach = kill, not tuning: if `3 × D_max > 1000 ppm`, an ordinary
   consumer chain invalidates the fixed-offset model at benchmark
   durations — Section 14 kill criterion fires and the route is redesigned
   (e.g., explicit drift-aware GT handling as a declared protocol change
   BEFORE final data). The payload is never time-warped to make a device
   pass, in the pilot or ever: drift is flagged, cases are GT_FAILED, and
   the failure is reported.

Expected outcome (stated to avoid anchoring): if the pilot's worst chain
lands ≤ ~37 ppm, the rule freezes 111 ppm; a 60 ppm chain freezes 180 ppm;
the provisional 500 ppm survives only if some chain reaches ~167 ppm.
Whatever freezes, the document records the observed distribution, the rule,
and the resulting number — ±500 is not carried forward by inertia.

Fixed-offset validity statement for the paper: the frozen tolerance is
exactly the domain where "fixed offset" is a measured approximation with
bounded error (≤10 ms over 90 s), not an assumption; this paragraph
transfers verbatim into the final protocol.

## 5. Pilot Dataset Specification

Two real songs, three devices, three rendered buffer files, 12 takes.
Buffers are rendered by the agent from the owner's clean song files using
the existing deterministic protocol (chirp | guard 1 s | 60 s payload |
guard | chirp @ 48 kHz; ≈63.5 s files). Each take = one full playback of
one buffer file, recorded start-to-finish. Buffers are reused across takes
and devices, so cross-device comparisons see identical layouts.

| # | Device | Buffer | Condition | What it validates |
|---|---|---|---|---|
| 1 | D1 | BUF-A | ordinary | primary-chain baseline |
| 2 | D1 | BUF-A | ordinary repeat | within-device repeatability (strict pair with 1) |
| 3 | D1 | BUF-BMID | ordinary | mid-song payload: reference begins ≈90 s into the input (nonzero GT offset) on real audio |
| 4 | D1 | BUF-A | low playback volume | low-music-level stressed condition |
| 5 | D1 | BUF-BMID | taps on desk near mic during music | impulsive-interference condition on the difficult song |
| 6 | D2 | BUF-A | ordinary | second chain baseline |
| 7 | D2 | BUF-A | ordinary repeat | strict repeat pair on D2 |
| 8 | D2 | BUF-A | background music from a second playback device (disjoint song) | environmental-interference condition |
| 9 | D3 | BUF-A | ordinary | third chain baseline |
| 10 | D3 | BUF-A | low playback volume | third chain under stress |
| 11 | D3 | BUF-A | playback from P2 (phone loudspeaker) | playback-path generality |
| 12 | D3 | BUF-B1 | ordinary | difficult song on a second device |

**Exact counts:**

| Item | Count |
|---|---|
| Unique pilot songs | 2 (song A ordinary structure; song B structurally difficult) |
| Recording devices | 3 (2 = documented floor) |
| Playback sources | 2 (P1 PC speakers ×11, P2 phone speaker ×1) |
| Takes of song A | 9 (takes 1,2,4,6,7,8,9,10,11) |
| Takes of song B | 3 (takes 3,5 via BUF-BMID; 12 via BUF-B1) |
| Total positive captures | 12 |
| Wrong-reference pairings | 12 (constructed at analysis time; zero extra recording) |
| Extra songs needed | 1 (disjoint interference track for take 8; never a reference) |
| Deliberate GT_FAILED takes | 0 (already demonstrated deterministically on digital fixtures; owner time is not spent manufacturing failures) |
| Buffer files to render | 3 (BUF-A, BUF-B1, BUF-BMID) |

Condition coverage: ordinary 5, strict repeats 2, low level 2, taps 1,
interference 1, alternate playback 1, mid-song placement 2. This exercises
every final-benchmark condition family once (question D) without
duplicating the final benchmark's balanced design.

Deliberately excluded: no participant material, no authentic handcam
takes, no external-domain probes, no version-mismatch strata — all of
those belong to the final study, not to machinery calibration.

## 6. Source/Song Selection Rules

- **Song A (ordinary):** a commercially released track the owner already
  possesses, with steady tempo, a typical mix, and no famous
  silence gaps. Selected as "ordinary", NOT because RhythmAlign is known
  to handle it well — the selection rule explicitly forbids choosing
  pilot material on known-tool performance.
- **Song B (structurally difficult):** at least one of — heavy repeated
  structure (≥3 near-identical sections; preferred, since it stresses
  placement uniqueness for every comparator including Panako), dense
  continuous percussion, or a long low-feature intro. One difficult
  source suffices; this stays a small pilot.
- **Interference track (take 8):** any third song, structurally disjoint
  from A and B (different artist/era/texture); it is never a reference in
  any pairing.
- **Exposure rule:** pilot songs are development-exposed forever. Their
  titles, hashes, and provenance go into the pilot manifest and a
  dev-exposure ledger entry; they are excluded from the final benchmark's
  10-song pool by construction, and the final pool is logged only after
  the pilot songs are fixed (so no final song is chosen from pilot
  material and no pilot song leaks into final material).
- **Format rule:** owner provides the cleanest file they possess (FLAC /
  WAV / high-rate MP3 / AAC all acceptable); the agent decodes to the
  48 kHz payload render and records the source hash.

## 7. Wrong-Reference Pilot

Small by design: this pilot verifies that the no-match machinery behaves,
not any acceptance-rate estimate.

- **Construction:** at analysis time, every take is additionally scored
  against the OTHER pilot song's clean reference (takes of A × ref B,
  takes of B × ref A) → 12 directed no-match pairs. Zero recording
  burden.
- **What each pairing verifies:**
  - scoring contract (CORRECT_ACCEPT / WRONG_ACCEPT / SAFE_ABSTAIN /
    GT_FAILED) on real acoustic material, not only digital fixtures;
  - RhythmAlign v1.2.0's ABSTAIN (SELECTIVE_NO_MATCH) transports to real
    captures;
  - GCC-PHAT / NCC argmax wrong-accept behavior is observed and recorded
    natively (expected, and NOT a pilot failure — it is the always-output
    failure mode the final study measures);
  - Panako's native no-match behavior is observed and recorded (zero
    match rows → NO_MATCH, never forced to output);
  - fairness: all systems receive byte-identical trimmed inputs and the
    identical two-reference pool.
- **Explicit scope limit:** results are PILOT_ONLY; no wrong-accept rate,
  selectivity rate, or any rate derived from 12 constructed pairs may be
  quoted as a finding or appear in the paper as evidence.

## 8. Panako Integration Plan

**Environment findings (2026-09-14, this machine):** WSL2 is installed and
working (Ubuntu 24.04.4 LTS, kernel 6.6.87-microsoft-standard-WSL2; Java
and ffmpeg not yet installed inside — add via apt). Docker 29.2.1 is
installed. Native Windows has Java 22, but the project explicitly does not
support Windows natively (LMDB/ffmpeg integration; "not a priority") —
consistent with the shakedown probe.

**Route (per task preference order):**

1. *Supported prebuilt CLI/binary:* does not exist — Panako 2.1 (May 2022)
   publishes no release artifacts and no Maven package. Build-from-source
   is therefore REQUIRED, but inside a sanctioned route, not on bare
   Windows.
2. **WSL2 — primary route.** `sudo apt install openjdk-17-jdk ffmpeg`;
   clone Panako at a pinned commit (record the clone URL + commit hash);
   `./gradlew shadowJar`; run via `java -jar panako.jar`. Windows-host
   runners call it through a `wsl.exe -e bash -lc "…"` wrapper owned by
   the runner, not the benchmark; the wrapper translates paths
   (`D:\…` → `/mnt/d/…`); pilot-scale audio may be copied into the WSL
   filesystem if /mnt I/O is slow (LMDB store lives in WSL anyway).
3. **Docker — fallback.** The project ships a Dockerfile
   (`resources/scripts/`); `docker build -t panako:2.1`, bind-mount a work
   dir, relative audio paths, store under the mounted volume.
4. Build-from-source on native Windows: NOT attempted (unsupported).

**Effort cap:** ≈2 hours wall clock, one route switch allowed (WSL2 →
Docker). If both fail, Panako is recorded BLOCKED and the comparator
contract is re-decided openly (Section 9 note) — it is never silently
shipped without the fingerprint comparator, because Panako is the
strongest technical threat to the study's primary claim.

**Pinned provenance (recorded in the pilot environment record):** Panako
2.1 + clone commit hash, JDK version (WSL), ffmpeg version, OS images,
panako.jar SHA-256 (jar itself gitignored, never committed).

**Invocation and semantics (verified empirically at integration and then
frozen in writing BEFORE any pilot run):**

- `panako store <reference.wav>` once per reference into a FRESH store
  directory per run; store contains exactly the same reference pool every
  other comparator sees. Store determinism checked by storing once,
  querying twice, and requiring byte-identical outputs.
- Query command: `panako query <input.wav>` (the 2.1 README documents
  `query`; older texts say `match` — resolve empirically at install and
  record the exact subcommand).
- Native output: semicolon-separated table with header — `Index; Total;
  Query path; Query start (s); Query stop (s); Match path; Match id;
  Match start (s); Match stop (s); Match score; Time factor (%);
  Frequency factor (%); Seconds with match (%)`.
- Input format: the SAME trimmed 48 kHz WAVs every other comparator
  receives (byte-identical); Panako resamples internally via ffmpeg.
- **Decision mapping, frozen now (before any pilot run):** ≥1 match row →
  ACCEPT, predicted offset (production convention: reference begins this
  many seconds into the input) = `Match start − Query start`, taken from
  the row with the highest `Match score`; zero rows → NO_MATCH (native
  refusal, preserved verbatim, never forced to argmax). No threshold is
  invented on `Match score` or `Seconds with match`; those values are
  recorded natively for the semantics table.
- No-match evidence on this pilot: the 12 wrong-reference pairings all
  share zero content with the store, so Panako's refusal behavior is
  directly observed.
- Bonus diagnostic: the `Time factor (%)` column on positive pairs is an
  independent replay-speed estimate — recorded and compared against the
  marker-measured drift as a cross-system sanity check.

**Is Panako a fair comparator for PRECISE offset placement?** Fingerprint
matches are occurrence claims with coarse time resolution (fingerprint
blocks, not waveform phases), while the benchmark scores placement at a
100 ms tolerance. The pilot therefore measures Panako's offset error
against marker GT on the 12 positives and applies this pre-declared role
rule: if median |offset error| ≤ 100 ms, Panako serves as a full placement
comparator; otherwise its role is IDENTIFICATION/SELECTIVITY comparator —
accept/refuse correctness (the strongest threat to the selectivity claim)
— with its native placement error reported and explicitly scoped, and no
refinement step (post-hoc NCC polishing would create an undeclared hybrid
system and is forbidden). Either role keeps Panako ESSENTIAL; the role
assignment is frozen before the final benchmark.

## 9. Comparator Decisions

Re-evaluated after the Panako inspection:

| Comparator | Verdict | Reviewer question it answers |
|---|---|---|
| RhythmAlign v1.2.0 (frozen) | **ESSENTIAL** | The system under test: does its measured selectivity (ABSTAIN) and placement transport to fresh material at all? |
| GCC-PHAT argmax | **ESSENTIAL** | Does the canonical always-output baseline dominate without needing refusal? Is the historical wrong-accept structure real or a dev-data artifact? The scientific control for the selectivity claim. |
| Panako 2.1 fingerprint (WSL2/Docker) | **ESSENTIAL** (role scoped per Section 8 precision rule) | Do modern fingerprint systems with native match/no-match semantics already achieve selective-level safety at high coverage? The strongest technical threat to the primary claim; must be answered, not omitted. |
| Normalized cross-correlation argmax | **USEFUL_OPTIONAL** | Does the conclusion hold across the simple-baseline family? Near-zero marginal cost (already implemented); kept unless runtime is prohibitive. Known drift fragility recorded in the shakedown is preserved natively — never patched. |
| Kdenlive 26.08 native audio-reference alignment | **REMOVE from THIS pilot; ESSENTIAL in the final study** | "Why not just use the editor's native sync?" — answered by the owner-operated technical stratum (8–10 pairs, project XML scored) in the final benchmark. Owner GUI time is not spent re-validating machinery this pilot already covers. |
| Manual waveform alignment | **REMOVE** (benchmark arm) | None automatable — remains a pilot/final-study recovery-path observation only, never a benchmark arm. |
| SyncSink GUI as a separate arm | **REMOVE** | The Panako CLI arm already answers the fingerprint question; a GUI arm doubles owner burden for nothing load-bearing. |

Pilot-round comparator set: RhythmAlign, GCC-PHAT, NCC (near-free), Panako
(once integrated). All through the existing shared `RunnerRecord`
contract, all on identical trimmed bytes, all single-pass.

## 10. Pilot Metrics

All pilot metrics are PROTOCOL DIAGNOSTICS. Every artifact carries
`PILOT_ONLY / NOT_FINAL_PAPER_EVIDENCE`. Alignment performance is recorded
for debugging and explicitly excluded from paper evidence.

| Metric | Definition | Diagnostic purpose |
|---|---|---|
| GT success rate | GT_VALID takes / total takes, per device and overall | protocol survival on real chains (question C) |
| Genuine marker confidence | Both markers of every valid take; per-device min/median | input G of the freeze rule |
| Competing marker confidence | Max non-marker full-overlap peak per take (ungated trail) + leakage re-scan maxima | input B of the freeze rule |
| Confidence margin | Per-device and pooled G/B ratio; band width [3B, 0.8G] | feasibility (G/B ≥ 3.75) and headroom record |
| Clock drift ppm | `scale_error` per take; per-device max and spread | drift freeze rule input; within-device repeatability |
| Mapping disagreement | Two-marker payload-map disagreement per take | re-affirm the 10 ms gate |
| Marker candidate count | Accepted candidates per take (must be exactly 2) | count-rule behavior incl. stressed conditions |
| Trajectory corroboration | slope ratio + r² for every marker and top non-marker peak | gating-policy decision for the frozen spec |
| Comparator execution success | ran / errored per system per case | machinery completeness |
| Comparator output semantics | Per-system output table: native fields, decision mapping applied, refusal form | semantics frozen before final study; Panako table per Section 8 |
| Panako offset error vs GT | `Match start − Query start` vs marker GT, 12 positives | role assignment (placement vs identification) |
| Pipeline reproducibility | Full second run of ≥2 takes + scoring; byte-identity beyond volatile fields | reproducibility transport from digital fixtures to real audio |
| Alignment performance (RA + baselines on the 12 positives) | offsets, errors, decisions | DEBUGGING ONLY — labeled PILOT_ONLY, never presented as paper confirmation |

## 11. Owner Workload

All agent-executable work (buffer rendering, folder scaffold, ingestion,
GT, trimming, comparators, Panako via WSL, analysis, reports) is done by
the agent. The owner's physical work:

| Item | Time |
|---|---|
| One-time: receive kit (3 buffer WAVs + take list), copy BUF-A to the P2 playback phone | ≈10 min |
| Record 12 takes (≈2.5 min each: start recording → play file → stop → save as take number) | ≈30 min |
| Transfer recordings to the pilot folder (USB cable / cloud drive / shared folder) | ≈10 min |
| Total | **≈50–60 min**, one session possible, two comfortable |

No manual annotation, no offsets, no waveform inspection, no repeated CLI
commands, no renaming beyond `take01`, `take02`, …, no metadata entry.
The optional editor workflow (Kdenlive stratum) is NOT part of this pilot.

## 12. Agent-Automated Workflow

New research-only module `experiments/applied_system/pilot_harness.py`
(plus tests; extends, never modifies, `marker_protocol.py` machinery and
imports production code read-only):

1. **Kit build:** decode the owner's two clean songs + interference track;
   render BUF-A / BUF-B1 / BUF-BMID deterministically via
   `render_marker_buffer`; emit a per-take cheat sheet (plain language,
   Section 16) and a machine-readable take plan (device, buffer, condition,
   expected GT class). Pilot manifest records song sources + hashes +
   dev-exposure ledger entry.
2. **Ingest:** owner drops recordings into
   `results/pilot/incoming/` as `takeNN.<any extension>`; the harness
   auto-matches take IDs to the plan, decodes at NATIVE rate (ffmpeg
   fallback for AAC/m4a, no resampling — drift must survive), hashes
   everything, and tolerates duplicate/retake files by suffix
   (`take01_b.m4a` → recorded, both analyzed, agent classifies).
3. **Per-take analysis:** detect → GT → QC → trim → leakage re-scan →
   sweep-trajectory on both markers AND top non-marker peaks → direct
   correlation cross-check (payload probe vs marker GT) →
   `takeNN_report.json`. Ungated `top_marker_peaks` trail always recorded
   (Section 3).
4. **Freeze-rule computation:** after all 12 takes, compute G, B, per-device
   margins, band, T, D_max, T_drift, trajectory policy decision — printed
   as a proposal, frozen into the pilot protocol record once accepted.
5. **Comparator sweep:** freeze the pilot manifest (existing machinery),
   run RhythmAlign / GCC-PHAT / NCC / Panako single-pass on identical
   trimmed bytes + the 12 wrong-reference pairings; Panako invoked through
   the WSL wrapper; store rebuilt fresh; determinism double-query check.
6. **Outputs:** `results/pilot/` manifest, records, scores, semantics
   tables, summary report, reproduction check — all labeled
   `PILOT_ONLY / NOT_FINAL_PAPER_EVIDENCE`. Success/kill gates evaluated
   mechanically (Section 13/14).

## 13. Pilot Success Criteria

All gates must hold for the pilot to freeze the final protocol:

1. **GT survival:** ≥10/12 takes GT_VALID; every GT_FAILED take has a
   deterministic, explained reason (and at least one valid take per
   device).
2. **Confidence feasibility:** G/B ≥ 3.75 pooled AND on every device
   chain; frozen T sits inside [3B, 0.8G] with the margins recorded.
3. **Trajectory policy decidable:** uniform corroboration behavior across
   devices (all-genuine-corroborates AND no-competitor-corroborates) OR
   demonstrably noisy — either outcome yields a frozen policy; ambiguity
   does not.
4. **Drift feasibility:** 3 × D_max ≤ 1000 ppm; per-device spreads
   reported; every take's |scale_error| also individually ≤ 1000 ppm
   (else the take is GT_FAILED and gate 1 applies).
5. **Trim/leakage:** clean leakage re-scan on all 12 trimmed inputs;
   mapping disagreement ≤ gate everywhere.
6. **Comparators:** all four systems execute on identical bytes; Panako
   integrated (WSL2 or Docker) with pinned provenance and verified store
   determinism; native no-match observed on wrong pairs.
7. **Wrong-reference sanity:** RhythmAlign SAFE_ABSTAIN on ≥11/12 wrong
   pairs; any RA wrong-accept triggers investigation and is a kill-criterion
   input. GCC-PHAT/NCC wrong accepts are recorded as expected behavior,
   not failures.
8. **Reproducibility:** second full run byte-identical beyond volatile
   fields.

Outcome rules: all gates pass → freeze the final protocol (Section 15) and
declare the final benchmark ready to collect. Any kill criterion fires →
stop/redesign per Section 14. Mixed outcome (gate fails, no kill fires) →
fix machinery, re-run only the affected takes, and re-freeze; the pilot
stays development data throughout.

## 14. Pilot Kill Criteria

Pre-declared. A fired kill criterion STOPS or redesigns the route — no
goalpost movement, no threshold nudging, no data rescue. The route-G
historical case-study backup remains available.

1. **Marker GT unreliable across common devices:** GT_VALID fails on ≥1 of
   the 2–3 realistic device chains for reasons not fixed by machinery
   repair (i.e., the protocol itself, not the tooling, fails on ordinary
   hardware).
2. **Confidence distributions overlap:** G/B < 3.75 on any chain after
   correct detection — no defensible single gate exists; requires chirp
   redesign (e.g., segmented/drift-tolerant sweep) and a NEW pilot round
   before any final data.
3. **Fixed-offset invalidated:** 3 × D_max > 1000 ppm on an ordinary
   consumer chain (detectability cap breach) — benchmark durations cannot
   carry a fixed-offset contract on realistic hardware; redesign the
   protocol (declared drift handling) before final data, never warp.
4. **Fingerprint threat unintegratable:** Panako cannot be installed via
   WSL2 or Docker within the effort cap — the study loses its strongest
   comparator; the comparator contract must be re-decided openly
   (documented substitution or explicit scope reduction) BEFORE final
   data, or the paper route stops.
5. **Selectivity transport failure in miniature:** RhythmAlign produces
   ≥2 wrong accepts among the 12 pilot wrong-reference pairs on real
   captures — the released refusal behavior may not transport to fresh
   material; escalate to a redesign/stop decision before investing in the
   final benchmark.
6. **Conditions not reproducible:** the same written protocol yields
   erratic GT or unclassifiable captures across ordinary/repeat takes
   (owner cannot reliably produce valid takes following the one-page
   instructions) — the final benchmark's recording burden estimate is
   invalid and the study design must be re-scoped.
7. **Workload blowout:** actual owner time materially exceeds the
   50–60 min estimate (say, >2.5×) — the final benchmark's ~26–30-take
   plan is unrealistic as designed and must be re-scoped before freeze.

## 15. Final Protocol Freeze Checklist

Everything below is frozen AFTER the pilot and BEFORE any final benchmark
media is collected. Once frozen, final data may not tune any of it. After
final data collection starts, the only permitted changes are corrections
of demonstrable implementation bugs that do not depend on outcomes — each
documented transparently (what broke, why it is outcome-independent, what
changed, regression test), with affected cases re-run under the fixed
machinery and the change logged in the study record.

| # | Item | Frozen value / rule source |
|---|---|---|
| 1 | Marker waveform (chirp template) | `marker_protocol.py` constants — unchanged by pilot unless kill 2 fires (then redesigned + re-piloted) |
| 2 | Marker detector | matched filter + full-overlap rule + NMS — as shipped |
| 3 | Confidence rule | T from Section 3 band rule, from pilot data |
| 4 | Candidate-count rule | exactly 2 — unchanged |
| 5 | Trajectory check policy | gating vs diagnostic, per Section 3 decision rule |
| 6 | Drift tolerance | T_drift from Section 4 rule, from pilot data |
| 7 | Mapping-disagreement tolerance | 10 ms re-affirmed or re-derived per Section 3 |
| 8 | Trim rule | 50 ms margins, hole construction — as shipped |
| 9 | Manifest schema | existing frozen manifest machinery |
| 10 | System versions | RhythmAlign v1.2.0; Panako 2.1 + commit + jar hash; JDK/ffmpeg/Python/numpy/scipy/librosa recorded in environment |
| 11 | Baseline implementations | GCC-PHAT / NCC runners as committed; no patches post-freeze |
| 12 | Comparator configs | identical trimmed bytes, identical reference pool, Panako store-per-run + decision mapping per Section 8 |
| 13 | Offset correctness tolerance | 100 ms primary; 50/150 ms sensitivity — unchanged |
| 14 | Wrong-reference scoring | pre-published rotation table; any ACCEPT = WRONG_ACCEPT |
| 15 | Benchmark conditions | ordinary / low-level / taps / interference / partial / device-variation definitions as exercised by this pilot |
| 16 | Song/source selection rules | Section 6 rules + final 10-song pool logged (disjoint from pilot songs) |
| 17 | Final sample counts | 10 songs, 22–24 positive takes, 22–24 constructed wrong-reference pairs, ≥3 sessions, ≥2 devices (per study design Section 6) |

## 16. Exact Owner Recording Instructions

Plain language. You will play files the agent prepared and record them
with your devices. That is the entire job. No DSP terms, no analysis.

**One-time setup (≈10 min)**

1. The agent gives you a folder containing three audio files:
   `BUF-A.wav`, `BUF-B1.wav`, `BUF-BMID.wav`. Each is about one minute
   long: a short beep, the song, another beep. The beeps are supposed to
   be there.
2. Copy `BUF-A.wav` onto one of your phones or tablets (it will be played
   from that device for take 11 only).
3. Choose your three recording devices and label them for yourself:
   D1 = your main phone, D2 = your second phone / tablet / laptop,
   D3 = the third device. Note which is which.

**For every take (≈2.5 min each)**

4. Start recording on the device. Wait about 5 seconds of quiet first.
5. Play the listed file ONCE, in full, from the computer speakers (or the
   phone speaker for take 11). Do not pause. Do not change volume during
   a take (except takes 4 and 10, where the volume should be turned DOWN
   to a quiet background level before you start).
6. Wait about 5 seconds of quiet, then stop recording.
7. Save the recording with the take number as its name — `take01`,
   `take02`, … Any audio format is fine. Do not trim, edit, or convert
   the recording.
8. If something obviously went wrong (accidentally stopped too early,
   rang the doorbell mid-take), just record it again and keep BOTH files
   (`take05` and `take05_b`). The agent will sort it out.

**The take list**

| Take | Record with | Do this |
|---|---|---|
| 1 | D1 | play `BUF-A.wav` normally |
| 2 | D1 | play `BUF-A.wav` normally again (yes, again) |
| 3 | D1 | play `BUF-BMID.wav` normally |
| 4 | D1 | turn the volume down (quiet background level), play `BUF-A.wav` |
| 5 | D1 | play `BUF-BMID.wav`; while the music plays, tap your finger on the desk near the recording device — steady, like tapping a pen, the whole time |
| 6 | D2 | play `BUF-A.wav` normally |
| 7 | D2 | play `BUF-A.wav` normally again |
| 8 | D2 | play `BUF-A.wav` while a second device plays some OTHER music softly in the background (the agent tells you which track) |
| 9 | D3 | play `BUF-A.wav` normally |
| 10 | D3 | turn the volume down, play `BUF-A.wav` |
| 11 | D3 | play `BUF-A.wav` from the phone/tablet speaker (not the computer) and record it with D3 |
| 12 | D3 | play `BUF-B1.wav` normally |

**Rules that matter**

- Keep the whole recording, including the quiet parts before and after.
- Never edit or trim a recording.
- Do the takes in one session if you can; two sessions is fine.
- Don't play other music during a take (except take 8, where it is the
  point).
- When done, put all the files into `experiments/applied_system/results/pilot/incoming/`
  (or hand the folder to the agent) — that's it. The agent does everything
  else and reports back.

### PILOT DESIGN VERDICT
PILOT_READY

### DEVICES NEEDED
3 recording devices (recommendation: THREE_DEVICE_CALIBRATION_RECOMMENDED; 2 is the documented acceptable floor if no third device exists). All owner-owned; no recruitment.

### SONGS NEEDED
2 pilot songs (1 ordinary, 1 structurally difficult) plus 1 disjoint interference track for the background condition. Pilot songs are development-exposed forever and excluded from the final pool.

### TOTAL RECORDINGS NEEDED
12 acoustic takes (D1 ×5, D2 ×3, D3 ×4; song A ×9, song B ×3), reusing 3 rendered buffer files.

### OWNER RECORDING TIME
≈50–60 minutes total (≈30 min active recording + ≈20 min one-time setup and transfers); one session possible, two comfortable.

### WRONG-REFERENCE CASES
12 (constructed at analysis time by offering each take the other pilot song's reference; zero extra recording).

### MARKER THRESHOLD STRATEGY
Freeze the gate by pre-declared rule from pooled pilot measurements, not by choosing a nice number: with G = weakest genuine marker confidence observed on any device and B = strongest non-marker matched-filter peak observed anywhere (from the always-recorded ungated diagnostic trail), the gate must lie in the band [3×B, 0.8×G]; the frozen value is the band's log-midpoint sqrt(3B·0.8G). A non-empty band requires G/B ≥ 3.75 on every device chain — a chain that violates it is a kill/redesign signal, never a tuning opportunity. The raw gate is frozen together with the multi-signal QC spec: exactly-two-candidate rule and full-template-overlap eligibility (structural), and the physics-based sweep-trajectory check promoted to a gating requirement only if it cleanly separates genuine from competing peaks uniformly across all pilot devices, otherwise kept as a recorded diagnostic. The provisional 0.15 stays in force only until the pilot data freezes the rule's output.

### DRIFT THRESHOLD STRATEGY
Freeze the tolerance from the task contract plus pilot observations, not from the provisional number: measured `scale_error` on all 12 takes gives D_max (worst observed |drift|); the frozen gate is T_drift = max(3 × D_max, 111 ppm), capped at 1000 ppm because the chirp decorrelates beyond ≈1200 ppm and the gate must stay inside the detectable band. The 111 ppm floor is interpretable, not arbitrary: unmodeled drift over the longest benchmark take (≈90 s) must stay ≤10 ms, i.e. ≤10% of the 100 ms scoring tolerance. If 3 × D_max exceeds the 1000 ppm cap on an ordinary consumer chain, the fixed-offset model is invalid at benchmark durations — that fires the kill criterion and forces a declared protocol redesign; captures are never time-warped to pass.

### PANAKO STATUS
PARTIAL

### ESSENTIAL COMPARATORS
RhythmAlign v1.2.0 (frozen system under test); GCC-PHAT argmax (always-output scientific control); Panako 2.1 fingerprint via WSL2 (Docker fallback) — ESSENTIAL with its role (placement vs identification/selectivity) scoped by the pilot precision measurement; Kdenlive 26.08 native alignment is ESSENTIAL for the final study but deferred out of this pilot; NCC argmax USEFUL_OPTIONAL (near-free, included).

### HUMAN PARTICIPANTS NEEDED NOW
0

### WHAT THE OWNER MUST PHYSICALLY DO
1. Receive the kit folder with three ready-to-play audio files (BUF-A, BUF-B1, BUF-BMID) and copy BUF-A onto one phone/tablet. 2. Twelve times: start a recording on the listed device, wait 5 quiet seconds, play the listed file once in full from the listed speaker (volume down for takes 4 and 10; tap the desk during take 5; background music during take 8; phone speaker for take 11), wait 5 quiet seconds, stop, save as take01…take12 — never edit or trim. 3. Drop all files into results/pilot/incoming/. Nothing else: no annotation, no commands, no renaming schemes, no waveform checks — the agent runs everything after that.

### PILOT DATA STATUS
PILOT_ONLY — NOT FINAL PAPER EVIDENCE

### NEXT STEP
Build the pilot kit: render the three marker-buffer WAVs from the two chosen pilot songs and the interference track, scaffold `results/pilot/`, and hand the owner the one-page take list for the 12 recordings.
