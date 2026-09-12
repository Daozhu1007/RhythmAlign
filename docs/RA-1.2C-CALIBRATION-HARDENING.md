# RA-1.2C — Alignment Engine v2 Calibration Hardening and Repeated-Invocation Stability

Status: **calibration hardening complete; Engine v2 remains NON-DEFAULT —
the GUI still calls the v1.1.x path.**
Recommendation: **READY_FOR_RA12D** (see §24), with the human-listening
gate still open (§3).

---

## 1. Git baseline

| item | value |
|---|---|
| Branch | `main` |
| HEAD at task start | `c8bbcd9f8a427d4c79c06a8e97f3c52c408784a4` (`docs: RA-1.2B alignment engine v2 evidence gate (non-default path)`) |
| Upstream relation | `origin/main`, 0 ahead / 0 behind |
| Working tree at start | clean |
| Baseline suite | `python -m pytest -q` → **32 passed in 15.63 s** |
| Baseline engine state | Engine v2 exists, non-default; GUI/default path v1.1.x (`_CONFIDENCE_THRESHOLD == 2.0`) |

## 2. Epistemic wording corrections (carried into this report)

Three distinctions are now used strictly and separately everywhere below:

1. **acceptance ≠ independently verified accuracy.** RA-1.2B's 29/29
   positive ACCEPT is *acceptance* under the calibrated policy. Only
   零对话 has independently established manual ground truth. For the other
   positives, v1–v2 agreement is **regression-consistency evidence**
   ("v1–v2 consistency"), not independent correctness.
2. **零对话 accuracy claim.** Engine v2: **+12.4923 s**. Independent
   evidence: **≈ +12.4 ± 0.4 s**. The correct statement is: *"Engine v2
   falls inside the independently established ground-truth interval"* —
   NOT "independently verified 90 ms accuracy"; the manual ground truth
   itself carries ±0.4 s uncertainty. (0.0923 s deviation from the GT
   center, well inside the interval.)
3. **Wrong-song mismatches.** v1.1.x accepting 10/10 deliberate
   wrong-track stress cases demonstrates that its Z ≥ 2.0 gate is not a
   semantic correctness measure. It does NOT mean "v1 fails 100 % in
   normal user usage" — these are constructed wrong-track cases, and v1
   aligns all 29 real positive pairs consistently.

## 3. Owner human-test status

`HUMAN_LISTENING_PENDING`

- The RA-1.2B owner-test artifact
  `零对话_engine_v2_test.mp4` (v2-aligned preview,
  distinct from the source video and the old v1-based `零对话_synced.mp4`)
  exists and was **not** regenerated or overwritten.
- No owner listening verdict has been supplied as of this task. Nothing
  here invents or presumes one. The listening test remains open and is a
  required gate before RA-1.2D ships anything.

## 4. Semi-synthetic real-noise corpus design

New: `experiments/low_snr_alignment/semi_synthetic.py` (generator library),
`semi_synthetic_plan.json` (committed, path-free), `semi_synthetic_eval.py`
(runner: `build-sources` / `select-hard-negatives` / `run --split …`).
Local absolute paths live only in the gitignored
`local_sources.json` / `local_corpus.json`; generated audio goes to the
gitignored `results/` scratch tree. All media is used READ-ONLY.

Concept: **real handcam/arcade recording (background, with its own taps,
ambience, adjacent machines, speech, phone-mic coloration, compression
artifacts) + a clean target track from a DIFFERENT project inserted at an
EXACT known offset + documented degradation.** The background's own loud
song acts as structured real-world interference — a harder and more
realistic noise source than Gaussian synthetic audio. The purpose is not
to simulate an arcade loudspeaker.

Degradation conditions (deterministic, seeded, documented in code):

| level | gain (track RMS vs background RMS) | condition chain |
|---|---|---|
| L1 | −6 dB | clean |
| L2 | −12 dB | 80 Hz–5.5 kHz band-limit (4th-order Butterworth, zero-phase) |
| L3 | −18 dB | band-limit + mild room reverb (0.25 s decaying-noise IR, 25 % wet) |
| L4 | −24 dB | band-limit + reverb + mild soft-knee compression (tanh, unit slope) |

Evaluation tolerance: **0.15 s** (≈ 6 analysis hops at hop 512 / 22050 Hz;
matches the engine cluster tolerance and the synthetic suite). Ground
truth is exact by construction (sample-exact insertion) and never derived
from any algorithm prediction.

Cases: 36 calibration positives + 20 holdout positives (12/10 recordings
as backgrounds, offsets varied: +0.4 s … +27.5 s, negatives to −12.4 s,
near-zero included; every case ≥ 45 s overlap), 4 tiled-loop ambiguity
cases (target's first 9.6/11.2 s tiled end-to-end — evidence genuinely
non-unique), and 10 feature-similar real hard negatives (§8).

## 5. Calibration / holdout split

Split unit = **project** (one song + all its recordings), 20 projects / 29
recordings, 10 + 10 projects / 13 + 16 recordings:

- **CALIBRATION:** 零对话， 红Lividi, DROPS, 延误列车， 白妄想， 共感觉， 分诊
  (4 recordings), 萨姆沙, 90decision, QUEEN
- **HOLDOUT:** DanceRobotDance, 白39, 宙天， 海底谭 (6 recordings), Let u
  dive, 乐意效劳， 吃药睡觉， 巴别塔， 才不是恶魔呢， 矛盾心理 (2 recordings)

零对话 stays in calibration (its ground truth anchored RA-1.2A/B); its
recording doubles as the closest-to-real ambience-only background.

## 6. Leakage audit

Enforced mechanically (`ss.audit_split`, unit-tested in
`tests/test_ra12c_calibration.py`):

- every project, song, recording, and generated seed appears in **exactly
  one** side (audit: 0 violations);
- every case's background AND target belong to its declared split;
- no positive target is its background's own song (no duplicate-placement
  confounds);
- hard-negative pairings are split-pure (calibration recordings ×
  calibration wrong-tracks; holdout × holdout) and never the recording's
  own song;
- threshold selection inspected **only** calibration data; the holdout was
  evaluated **once**, after the policy was frozen (§10).

## 7. Threshold-robustness measurements (calibration only)

With the frozen RA-1.2B policy, over 44 calibration cases
(36 positives + 2 tiled + 6 hard negatives + the RA-1.2B synthetic nulls
and 10 ordinary real mismatches):

**Truth side** (semi-synthetic positives, per-level accept rate):

| level | calibration | holdout (§11, frozen policy) |
|---|---|---|
| L1 (−6 dB clean) | 8/8 accept | 5/5 accept |
| L2 (−12 dB band-limit) | 7/9 accept | 4/5 accept |
| L3 (−18 dB band-limit+reverb) | 2/10 accept | 0/5 accept |
| L4 (−24 dB +compression) | 0/9 accept | 0/5 accept |

At L3/L4 the failing checks are `tonal_z` (truth-cluster tonal Z decays to
3.5–4.8 under the loud different-song interferer) and missing onset
corroboration — the engine refuses single-family acceptance, which is the
RA-1.2A lesson working as designed. The abstain boundary reproduces on
disjoint holdout sources.

**Garbage side** (hard negatives on real structured noise — this is the
new, important calibration fact):

- pcen-family cluster Z on garbage reaches **13.0** (loud recordings make
  wrong-track correlation look "strong") — the RA-1.2B concern "pcen null
  max 5.55 vs floor 5.6" was based on quiet-background nulls and
  *understates* the real garbage level by 2.4×.
- BUT garbage pcen **margins stay ≤ 1.013** (every garbage peak is
  non-unique), garbage tonal cluster Z ≤ 4.75 (hard) / 4.94 (ordinary),
  garbage onset cluster Z ≤ 1.84 (hard) / 2.01 (ordinary).
- Upper-bound closest approach of ANY garbage cluster to CASE A
  qualification (generously assuming per-family maxima share one
  cluster): **0.95** — binding constraint `tonal_z_floor` (4.75/5.0).
  For CASE B: **0.82** (binding: pcen margin 1.23/1.4).

**Conclusion on the floors:**

- The absolute Z floors are **not** what separates truth from garbage on
  real recordings — garbage Z can exceed true-positive Z. The separators
  are (a) CASE A's cross-family co-ranking (tonal #1 AND pcen #1 at the
  same cluster, never observed on garbage in 40 RA-1.2B + 8 RA-1.2C
  garbage realizations) and (b) CASE B's uniqueness margin ≥ 1.4
  (garbage ≤ 1.06 across 18 real mismatch/tiled cases).
- Therefore `tonal_z_floor = 5.0` is **load-bearing** (garbage reaches
  4.75–4.94; it must not move down), and `pcen_z_floor`/`onset` floors
  are *secondary joint conditions*, correctly described as NOT clean null
  separators (pcen garbage 13.0 > 5.6; onset garbage 2.01 > 2.0).
- Raising `margin_floor_a` above 1.0 was evaluated and **rejected**: the
  synthetic `low_snr_taps` truth measures pcen margin **1.009** — the
  1.0 co-rank semantic is genuinely load-bearing for near-threshold true
  positives, exactly mirroring garbage margins at 1.013. Margins alone do
  not separate; the dual-family co-rank does.

## 8. Hard-negative construction

`select-hard-negatives` scores every split-legal wrong track against a
recording using coarse similarity in the engine's own evidence families:
chroma cosine (chroma_stft mean), tempo proximity (librosa tempo),
onset-density difference, PCEN low-band (first 32 mel) cosine; rank-normalized
and averaged; best wrong track wins. Selection never uses filenames.
Wrong tracks are **not inserted** — the case is the real recording vs a
similar wrong song (like the RA-1.2B mismatches, but adversarially
selected). A recurring winner is the 90decision track (chroma cosine
0.97–0.99 to four calibration recordings); full ranked tables in
`results/hard_negative_search_ra12c.json`.

Families now covered by negatives: 10 ordinary real mismatches (RA-1.2B) +
**10 feature-similar hard negatives** + **4 tiled real-noise ambiguity
cases** + 30 synthetic nulls (RA-1.2B) + 2 synthetic ambiguity cases.

## 9. Calibration distributions (summary)

- Semi-synthetic positives at accepted clusters (typical): tonal Z 6–19,
  pcen_hpss Z 25–73, margins 1.2–9.1 — far above floors; L3/L4 truth
  clusters decay tonally (§7).
- All 6 calibration hard negatives: ABSTAIN (5 ×
  `ABSTAIN_NO_CLUSTER_MEETS_FLOORS`, 1 × `ABSTAIN_AMBIGUOUS_CLUSTER`).
- Both calibration tiled cases: ABSTAIN
  (`ABSTAIN_AMBIGUOUS_CLUSTER`).
- Full per-case path-free evidence:
  `results/semi_synthetic_calibration_ra12c.json`.

## 10. Frozen policy

**Unchanged from RA-1.2B** — `DecisionPolicy` defaults in
`alignment_engine_v2.py`: `tonal_z_floor 5.0`, `pcen_z_floor 5.6`,
`pcen_primary_z_floor 7.0`, `onset_corroboration_z_floor 2.0`,
`margin_floor_a 1.00`, `margin_floor_b 1.40`, `min_overlap_s 30`,
`ambiguity_z_ratio 0.95`. Frozen before the holdout ran; the holdout was
evaluated exactly once. Justification in §7: every observed failure mode
of garbage is already blocked by a *structural* condition with measured
headroom, and the two knife-edge numbers flagged by RA-1.2B were
re-characterized with better data rather than adjusted (adjusting either
would reduce safety or kill known true positives).

## 11. Holdout results (frozen policy, evaluated once)

26 cases: **9 CORRECT_ACCEPT / 17 SAFE_ABSTAIN / 0 WRONG_ACCEPT.**

- Positives: L1 5/5 accept, L2 4/5, L3 0/5, L4 0/5 — the accept/abstain
  boundary replicates the calibration boundary on disjoint sources.
- All 4 holdout hard negatives ABSTAIN (`ABSTAIN_NO_CLUSTER_MEETS_FLOORS`).
- Both holdout tiled cases ABSTAIN (`ABSTAIN_AMBIGUOUS_CLUSTER`).
- Every accepted offset within 0.15 s of exact GT (max error 0.009 s).
- Evidence: `results/semi_synthetic_holdout_ra12c.json`.

## 12. Negative false-accept results (all negative families, frozen policy)

| negative family | N | WRONG_ACCEPT |
|---|---|---|
| ordinary real mismatches (RA-1.2B) | 10 | 0 |
| feature-similar real hard negatives | 10 | 0 |
| tiled real-noise ambiguity | 4 | 0 (4 abstain) |
| synthetic no-signal nulls (RA-1.2B, unchanged policy) | 30 | 0 |
| synthetic tiled/no-signal suite (RA-1.2B) | 2 | 0 |

While v1.1.x false-accepts 10/10 ordinary real mismatches (hybrid Z
3.44–5.96, gate 2.0).

## 13. Original 零对话 result (unchanged, with corrected wording)

Engine v2: **ACCEPTED at +12.4923 s** via CASE B
(`ACCEPT_PRIMARY_WITH_CORROBORATION`; pcen_hpss Z 10.44 / margin 1.893,
onset corroboration Z 2.268). The independent manual ground truth is
+12.4 ± 0.4 s, so **Engine v2 falls inside the independently established
ground-truth interval**. v1.1.x still accepts the wrong offset −1.9969 s
(hybrid alone, Z 5.49). Re-measured in this task's frozen-policy corpus
run; deterministic across all 25 repeated file-path soak calls (§17).

## 14. Existing real-positive consistency results (frozen policy re-run)

29/29 positives accepted; 28/28 agree with accepted v1 within 0.15 s (v2
runs +0.047 s vs v1 — a systematic sub-hop alignment difference, well
inside tolerance); the one disagreement is 零对话 where v1 is wrong and
v2 falls inside ground truth. 10/10 ordinary mismatches abstain; 0 worker
errors. Per-case table: `results/real_corpus_ra12c.json`. This is v1–v2
**consistency**, not independent verification (§2).

## 15. Owner-review sample recommendation

Five cases (not 29), chosen for coverage; **no exports were generated** —
existing synced outputs are reused where present:

| case | v1 | v2 | evidence path | diagnostics (accepted cluster) | existing output |
|---|---|---|---|---|---|
| 零对话 (`lingduihua_132`) | −1.997 s (WRONG) | **+12.4923 s** | CASE B | pcen Z 10.44 / m 1.893; onset Z 2.268 | v2 test preview exists (RA-1.2B); v1-based `_synced` also present |
| 海底谭2 (`haiditan_ds_2`) — closest to the confidence boundary | +9.125 s (Z 6.23) | +9.1719 s | CASE A | tonal Z 6.23; pcen Z 21.0 | `海底谭2_synced.mp4` exists |
| 白39 (`bai39_134`) — strongest recording | +10.820 s (Z 22.1) | +10.8437 s | CASE A | tonal Z 22.1 / m 5.3; pcen Z 45.5 / m 6.5 | none in folder |
| QUEEN — published strong normal | +15.255 s (Z 15.9) | +15.302 s | CASE A | tonal Z 15.9 / m 3.8; pcen Z 31.7 / m 3.7 | `QUEEN_synced.mp4` exists |
| 分诊4 (`fenzhen_ds_4`) — weakest strong | +10.147 s (Z 9.08) | +10.1936 s | CASE A | tonal Z 9.08 / m 2.34; pcen Z 34.9 / m 5.9 | `_synced` exists |

Listening focus: (1) confirm the v2 preview fixes the 零对话 drift heard
before; (2) confirm boundary + strong cases sound identical to v1 (they
should — sub-hop differences). Owner verdict still pending (§3).

## 16. Repeated-invocation soak results (same process)

New `experiments/low_snr_alignment/soak_test.py` (RSS, OS handles, leaked
`ra_*` temp files, per-call runtime; JSON reports in `results/`).

1. **Synthetic, 60 × `decide_alignment` in one process** (alternating
   accept/no-signal inputs): decisions deterministic; per-call runtime
   flat (1.41 s); RSS warms up once (105 → 245 MB by call ~16, allocator
   warm-up) then plateaus (≈ +0.05 MB/call steady state over calls
   6–60); handles 924 → 927 (+3 over 59 calls); temp leaks 0.
2. **Real file path, 25 × `find_offset_v2`** (lingduihua pair; ffmpeg
   extraction every call): identical decision +12.4923 s on every call;
   runtime flat (≈ 3.8 s/call); RSS flat at ≈ 230 MB (no monotonic
   growth across 25 calls); handles +3 total; temp leaks 0.

**No unbounded resource growth is attributable to Engine v2 repeated
invocation.** A persistent desktop process calling Engine v2 repeatedly is
memory- and handle-safe on this evidence.

## 17. Root cause / bounded conclusion for the RA-1.2B 25–30-case crash

`soak_test.py benchmark-repro` re-implements the exact RA-1.2B in-process
benchmark loop (per case: 2 × ffmpeg `extract_audio` → `librosa.load` → v1
hybrid → full Engine v2), all in ONE process, with per-case RSS/handle/
temp-file sampling and incremental JSON writing so a hard native death
would still leave evidence.

**Result: the crash did NOT reproduce.** 35/35 corpus cases completed
in-process (exit 0), passing the 25–30-case death point of the original
runs. Evidence (`results/soak_benchmark_repro_ra12c.json`):

- RSS: 86 → ~262 MB with a one-time warm-up; past case 5 the slope is
  **+0.21 MB/case** (≈ +6 MB over 30 cases, oscillating 255–268 MB —
  bounded at benchmark scale, not a runaway leak);
- OS handles: flat in steady state (925 at end; slope ≈ −0.13/case);
- leaked `ra_*` temp files: 0 (the engine's `finally` cleanup works);
- per-case runtime flat (first 8.1 s, mean 5.3 s, last 4.8 s — no
  progressive slowdown);
- every v2 decision identical to the worker-isolated run.

Bounded conclusion: the RA-1.2B silent deaths are **not reproducible** on
this machine/configuration today; no resource leak in the loop could be
found that would explain them (no handle growth, no temp-file growth, no
unbounded RSS growth, no runtime drift). The original cause therefore
remains unproven — plausible candidates stay environment-specific
(that machine state, memory pressure, or a dependency state since
changed), not Engine v2 logic. This does NOT satisfy "simply keep worker
isolation": the production single-session path is now *directly*
demonstrated stable by three same-process soak campaigns (§16), which is
the property a persistent desktop app needs. Worker isolation remains a
recommended defense for long headless batch benchmarks, where a native
crash would cost the whole run.

## 18. Memory / runtime scaling

`memory_scaling.py` (deterministic long fixtures: tonal music + taps +
noise recording, 240 s; track length varies):

| track duration | v2 wall | peak Python allocation (tracemalloc) | RSS before → after |
|---|---|---|---|
| 180 s | 8.87 s | 328.7 MB | 121 → 293 MB |
| 420 s | 7.70 s | 513.4 MB | 315 → 329 MB |
| 720 s | 10.30 s | 879.7 MB | 355 → 369 MB |

- Wall time is essentially flat across 4× duration (FFT-based correlation
  dominates; run-to-run machine variance exceeds the trend).
- Peak Python allocation scales ≈ linearly with duration (2.68× for 4×);
  the 720 s peak (~880 MB) is *transient* — RSS after the call returns to
  ~370 MB, and the soak runs show no accumulation across repeated calls.
- Generator split at 720 s: hybrid 5.5 s, pcen_hpss 3.3 s, pcen 0.9 s,
  onset 0.6 s — hybrid (production chroma-CENS) is the largest single
  cost, PCEN/HPSS are moderate.
- The 420/720 s fixtures abstain (taps-dominated low-SNR mix); this
  section measures resources, not accuracy.

**Optimization decision: no engine change.** The only identical-output
reuse available in Engine v2 (sharing one mel spectrogram between `pcen`
and `pcen_hpss`) would save ≈ one mel matrix (~12 MB at 12 min) — not
material against an ~880 MB peak that is dominated by production
`_align_hybrid` internals and full-curve FFT correlation. Per the task
bar ("materially reduces memory without changing results"), the change is
not justified; correctness stays untouched. Ordinary user videos
(2.5–3.5 min) peak around 300–500 MB transient — acceptable for the
desktop app, re-measurable if RA-1.2D wants headroom.

## 19. Remaining risks

1. **Human listening gate still open** (`HUMAN_LISTENING_PENDING`): the
   owner has not yet judged the v2 test export. This is a product gate,
   not an engineering one.
2. Real low-SNR evidence base is still ONE independently ground-truthed
   recording (零对话). The semi-synthetic corpus now bridges the gap
   with 56 exact-GT real-noise positives, but its backgrounds mostly
   contain a loud *different* song — a harder interferer than true
   ambience-only recordings; the L3/L4 abstain boundary is a policy
   choice, not an accuracy measurement.
3. The holdout is 26 cases; positive-side statistics are small (9
   accepts). Confidence is honest but limited; no claim of statistical
   generality beyond the dataset.
4. CASE B remains corridor-dependent on onset corroboration (truth 2.27
   vs garbage 2.01): a true low-SNR recording with weaker onset agreement
   will (safely) abstain.
5. The original benchmark parent-process death could not be reproduced in
   35 in-process cases on this machine (§17) — the root cause remains
   unproven; the production single-session path is demonstrated safe by
   soak evidence instead (§16), and worker isolation remains available
   for long batch runs.
6. `positive_strong` classes remain consensus-based (v1–v2 consistency),
   not independently ground-truthed (§2).

## 20. Exact files changed

Added:
- `experiments/low_snr_alignment/semi_synthetic.py` — generator + split-audit library
- `experiments/low_snr_alignment/semi_synthetic_plan.json` — path-free corpus plan (split, cases, seeds, hard-negative selection)
- `experiments/low_snr_alignment/semi_synthetic_eval.py` — build-sources / select-hard-negatives / run CLI
- `experiments/low_snr_alignment/soak_test.py` — repeated-invocation harness (synthetic / real-file / benchmark-repro)
- `experiments/low_snr_alignment/memory_scaling.py` — long-duration scaling measurement
- `experiments/low_snr_alignment/results/semi_synthetic_calibration_ra12c.json` — evidence
- `experiments/low_snr_alignment/results/semi_synthetic_holdout_ra12c.json` — evidence
- `experiments/low_snr_alignment/results/hard_negative_search_ra12c.json` — evidence (selection metrics)
- `experiments/low_snr_alignment/results/real_corpus_ra12c.json` — evidence (frozen-policy re-run)
- `experiments/low_snr_alignment/results/soak_synthetic_ra12c.json` — evidence
- `experiments/low_snr_alignment/results/soak_realfile_ra12c.json` — evidence
- `experiments/low_snr_alignment/results/soak_benchmarkrepro_ra12c.json` — evidence
- `experiments/low_snr_alignment/results/memory_scaling_ra12c.json` — evidence
- `tests/test_ra12c_calibration.py` — 16 media-independent tests
- `docs/RA-1.2C-CALIBRATION-HARDENING.md` — this report

Modified:
- `.gitignore` — ignores `experiments/low_snr_alignment/local_sources.json`
- `experiments/low_snr_alignment/README.md` — documents the RA-1.2C tooling

Not changed: `auto_sync.py`, `alignment_engine_v2.py`, `ui_main.py`,
`diagnose_offset.py`, version/release metadata. No media, no local
manifests, no generated audio committed; all committed evidence JSONs are
path-free (case ids + numbers only).

## 21. Exact validation results

| check | command | result |
|---|---|---|
| baseline suite (start) | `python -m pytest -q` | 32 passed in 15.63 s |
| full suite (end) | `python -m pytest -q` | **48 passed** |
| new tests | `python -m pytest tests/test_ra12c_calibration.py -q` | 16 passed |
| syntax | `python -m compileall -q auto_sync.py alignment_engine_v2.py diagnose_offset.py ui_main.py tests experiments` | OK (exit 0) |
| whitespace | `git diff --check` | clean |
| split leakage audit | `semi_synthetic_eval.py build-sources` + unit test | 0 violations |
| calibration run | `semi_synthetic_eval.py run --split calibration` | 44 cases: 17 CA / 27 SA / 0 WA |
| hard-negative search | `semi_synthetic_eval.py select-hard-negatives` | 10 selected, split-pure |
| holdout run (frozen policy) | `semi_synthetic_eval.py run --split holdout` | 26 cases: 9 CA / 17 SA / 0 WA |
| real corpus re-run | `real_corpus_eval.py --json …_ra12c.json` | 29/29 accepted, 28 agree, 10/10 abstain, 0 errors |
| soak synthetic | `soak_test.py synthetic --n 60` | stable (§16) |
| soak real-file | `soak_test.py real-file --n 25` | stable (§16) |
| soak benchmark-repro | `soak_test.py benchmark-repro --n 35` | §17 |
| memory scaling | `memory_scaling.py` | §18 |
| path-leak check | personal-path pattern search over all files added/modified in this task | 0 matches |

## 22. Final Git state

Committed as one coherent commit on `main` (parent `c8bbcd9`, the
RA-1.2B evidence gate) and pushed to `origin/main` after all validation
checks in §21 passed. No release, no tag, no version bump, no
default-path change: the GUI still calls `auto_sync.find_offset()`;
`auto_sync.py`, `alignment_engine_v2.py`, `ui_main.py`, and all
version/release metadata are byte-identical to the baseline.
`local_corpus.json`, `local_sources.json`, all media, and all generated
audio remain untracked/local; every committed evidence JSON is path-free
(case ids + numbers only).

## 23. Recommendation

**READY_FOR_RA12D**

Justification: the frozen RA-1.2B policy survived a disjoint
source-identity holdout (0 wrong accepts), ten adversarially-selected
feature-similar hard negatives (0 accepts, while v1.1.x accepts all ten
ordinary mismatches), and real-noise tiled-ambiguity cases (all abstain);
calibration showed the separator structure is the dual-family co-rank and
uniqueness margins — not the knife-edge absolute floors — and the floors
are therefore correctly left unchanged. Repeated invocation is
demonstrated stable in-process (60 synthetic + 25 full-file calls: no
memory/handle/temp growth, deterministic decisions), removing the
stability objection for a persistent desktop app. RA-1.2D may integrate
Engine v2 as the default path and prepare the v1.2.x release, subject to
the still-open owner listening test (§3) and honest disclosure that
human-ground-truth coverage remains one recording deep.
