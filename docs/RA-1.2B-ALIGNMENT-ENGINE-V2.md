# RA-1.2B — Alignment Engine v2 Evidence Gate

Status: **implemented, non-default — GUI still uses the v1.1.x path.**
Recommendation: **NEEDS_MORE_REAL_DATA** (see §22)

---

## 1. Git starting state

| item | value |
|---|---|
| Repository | `Daozhu1007/RhythmAlign` (local checkout `D:\Code\RhythmAlign`) |
| Branch | `main` |
| HEAD at task start | `c036a1c8318b0a1c5439ba1b7ac40b76f3754c59` (`docs: RA-1.2A low-SNR alignment spike (experiments + report)`) |
| Upstream relation | `origin/main`, 0 ahead / 0 behind |
| Working tree at start | clean |
| Test suite at start | `python -m pytest -q` → **19 passed in 3.65 s** |

## 2. RA-1.2A corrections

Two targeted edits to `docs/RA-1.2A-LOW-SNR-ALIGNMENT.md`; the report was not
rewritten wholesale.

1. **Independence contradiction (§10 worked example).** The example claimed
   "two independent families (PCEN-family + onset-flux) agree", contradicting
   the same section's own family model. Rewritten in the primary +
   corroborating + contradiction-check model: pcen_hpss is the strong
   *primary* evidence, onset top-1 agreement is *corroboration* (onset and
   PCEN are both temporal-flux evidence and correlated — supporting, never
   deciding), and the hybrid/chroma cluster at −1.997 s fails the
   contradiction checks. No naive majority voting was introduced.
2. **Synthetic claim (§7).** "the only method that also survived the harshest
   synthetic interference case" corrected: pcen_hpss was the only successful
   *new low-SNR candidate*; the legacy hybrid also passed that synthetic case
   but is the incumbent that fails the real recording, so pcen_hpss is not
   literally the only method overall.
3. **Commit-message typo.** The pushed `c036a1c` message says "PCEN+HPEN".
   Per task instruction, historical commit metadata was left untouched (no
   history rewrite, no force-push).

## 3. Local corpus discovery summary (read-only)

`D:\Daozh\Videos\` was scanned read-only (no media modified, renamed,
normalized, or deleted). Findings:

- **29 confident positive pairs** (handcam/gameplay video + clean track in
  the same folder project), listed in §4.
- **10 real mismatch negatives** constructed from those pairs (§5).
- Videos with **no in-tree clean track** (e.g. the 13.1 series, cpfc,
  INTERNETOVERDOSE, on your mark, 再见公主， 右曲， 强风大背头， 心跳不止，
  水神1.5, 海底谭 (已发)， 猫娘打架， 红枪， all Arcaea手元 folders, demo
  videos) cannot form positive pairs and were not used.
- **Excluded as ambiguous pairings (not guessed):**
  - `已发/Override/` — two different candidate tracks (`track.mp3` and the
    named `オーバーライド…mp3`); which one belongs to the video is unclear.
  - `13.2/共感觉/AP/共感怪物AP.mp4` — the video title suggests a different
    song than `共感觉.mp3`.

Manifest format: `experiments/low_snr_alignment/local_corpus.example.json`
(committed schema example) and `local_corpus.json` (gitignored, holds the
absolute local paths). Committed evidence JSONs contain **case ids and
numbers only** — verified `grep Daozh|舞萌` = 0 matches.

## 4. Real positive pairs (29)

| class | count | cases |
|---|---|---|
| `positive_low_snr` (ground truth manually established) | 1 | `lingduihua_132` (RA-1.2A failure case, GT +12.4 ± 0.4 s) |
| `positive_strong` (provisional, measured at benchmark time) | 28 | `lividi_132`, `drops_132`, `yanwulieche_132`, `baixiwang_132`, `goganjue_niaojia_132`, `dancerobotdance_133`, `bai39_134`, `hongzhoutian_135`, `fenzhen_ds_1..4`, `haiditan_ds_0..5`, `samesha_411`, `decision90`, `letudive`, `queen`, `leyixiaolao`, `chiyaoshuijiao`, `babieta`, `caibushimo`, `maodunxinli`, `maodunxinli_niaojia` |

Pairing basis: same-folder project organization, filename identity with the
track title, or existing `*_synced.mp4` outputs produced by RhythmAlign.
The strong/low-SNR split is *declared provisional* in the manifest; the
benchmark records v1 hybrid Z per pair so the class is measured, not
assumed (§7). 24 of 28 provisional-strong pairs have a `*_synced.mp4`
output, confirming the user previously ran alignment on them.

## 5. Real mismatch negatives (10)

Each pairs a real handcam video with a track **confirmed to be a different
song**: different folder, unrelated title, no filename correspondence; the
video's own track is excluded. The video side still contains real player
taps, arcade ambience, adjacent machines, speech, phone-mic coloration and
compression artifacts — with **no correct target-track correspondence**.
All 10 are expected-ABSTAIN cases and double as real-noise null
measurements (§7):

`mm_lingduihua_x_decision90`, `mm_lingduihua_x_leyixiaolao`,
`mm_haiditan1_x_maodunxinli`, `mm_fenzhen2_x_drops`,
`mm_maodunniujia_x_zhoutian`, `mm_bai39_x_caibushimo`,
`mm_queen_x_lingduihua` (A+B / B+A′ pattern), `mm_drd_x_babieta`,
`mm_samesha_x_goganjue`, `mm_hongzhoutian_x_yanwulieche`.

No real "true no-signal" recording exists in the corpus; synthetic nulls
(§6) cover that side. This limitation is recorded, not papered over.

## 6. Synthetic calibration population

- **Null realizations: N = 30** (RA-1.2A used 5), `calibrate_nulls.py`,
  no-signal recordings (Gaussian noise + metronomic taps, seeds 100–129).
- **Expected-behavior synthetic suite**: 6 cases (`synthetic_eval.py`,
  §13–16 below), including a NEW `repeated_structure_tiled` case whose
  recording contains the same 8 s loop tiled — genuinely non-unique
  evidence.

## 7. Per-family score / null distributions

### Synthetic no-signal nulls (N = 30)

| family | Z q95 | Z max | margin (top1/top2) max |
|---|---|---|---|
| hybrid | 4.19 | 4.29 | 1.235 |
| onset | 1.55 | 1.55 | 1.010 |
| pcen | 4.65 | 5.02 | 1.253 |
| pcen_hpss | 5.19 | **5.25** | 1.334 |

Joint risk for CASE A: tonal #1 and pcen_hpss #1 landed within 0.15 s of
each other in **1/30** realizations; the co-ranked cluster's Z was below
the floors, so it did not accept. **Engine false accepts: 0/30.**

### Real mismatch negatives (N = 10)

| metric | hybrid (tonal) | pcen_hpss | pcen | onset |
|---|---|---|---|---|
| max global curve Z | 5.96 | 5.55 | 5.36 | 2.01 |
| max cluster Z | 4.94 | 5.55 | 5.13 | 2.01 |
| max cluster margin | 1.311 | 1.059 | 1.081 | 1.021 |

- **v1.1.x production false-accepts 10/10 mismatches** (hybrid Z 3.44–5.96,
  threshold 2.0) — the product risk RA-1.2A identified, now demonstrated on
  ten real recordings.
- **Engine v2 false-accepts 0/10.**
- **No cluster in any mismatch carried both tonal and pcen evidence
  (0/10)** — the CASE A dual-family requirement never came close to firing
  on unrelated content.
- Cluster margins on real garbage stay ≤ 1.06 for the pcen family and
  ≤ 1.31 for hybrid; CASE B's 1.40 floor sits above both.

### Real positives (N = 29)

Measured split (benchmark, not assumption): **27 pairs `positive_strong`**
(v1 hybrid Z 9.08–22.14), **2 pairs borderline/low-SNR** (`lingduihua_132`
Z 5.49 — the known low-SNR case — and `haiditan_ds_2` Z 6.23, which both
engines still align consistently). 29/29 accepted by Engine v2; full
per-case table in §12; path-free evidence in
`experiments/low_snr_alignment/results/real_corpus_ra12b.json`.

## 8. Final evidence model

Four generators, three families (families, not votes):

| generator | family | role |
|---|---|---|
| `hybrid` (production `_align_hybrid`: chroma CENS deltas + 0.2 onset) | `tonal` | primary A; NEVER accepts alone (RA-1.2A showed it false-confident on real low-SNR and on every real mismatch) |
| `pcen_hpss` (harmonic-separated PCEN mel delta) | `pcen_spectral` | primary B; the low-SNR workhorse |
| `pcen` (plain PCEN mel delta) | `pcen_spectral` | diagnostic member of the SAME family — one vote with pcen_hpss, never two |
| `onset` (production `_align_onset`) | `onset_temporal` | corroboration only (correlated with PCEN deltas by construction) |

Candidate representation (`CandidateEvidence`): method, family, offset,
Z, peak margin, usable overlap, runtime, top competing candidate offsets,
optional notes. Full curves are kept per family
(`FamilyResult`) for cluster evaluation.

Clusters: candidates within ±0.15 s (≈ 6 hops) group into one cluster;
representative offset = member median. Per-family cluster evidence = the
family's **own best independent peak inside the cluster window** (±0.3 s) —
measuring at the representative point instead penalized sharp true peaks
(this exact bug was found and fixed during 零对话 validation: the pcen_hpss
peak, 2 frames off the median representative, dropped from Z 10.44 to 4.16).
Margin of a cluster = best in-window value / best independent peak outside
it. Two same-family members (pcen, pcen_hpss) collapse to the strongest —
they can never double-count.

## 9. Final decision rules and WHY

`DecisionPolicy` (frozen defaults in `alignment_engine_v2.py`):

| parameter | value | why |
|---|---|---|
| `cluster_tol_s` | 0.15 | ≈ 6 hops; RA-1.2A clustering scale |
| `min_overlap_s` | 30.0 | CASE E edge-lag guard: a match plausible over < 30 s of shared audio is not trustworthy |
| `margin_floor_a` | 1.00 | CASE A uniqueness semantic: each primary must rank the cluster as its own #1 (< 1.0 ⇒ another peak beats it). The cross-family agreement is the discriminator, not peak dominance |
| `margin_floor_b` | 1.40 | CASE B is the single-family path — it demands a clearly dominant peak. Above every measured garbage margin (real ≤ 1.06 pcen / 1.31 hybrid; synthetic ≤ 1.33) |
| `tonal_z_floor` | 5.0 | above the highest real-mismatch hybrid cluster Z (4.94) |
| `pcen_z_floor` | 5.6 | above the highest pcen-family null Z observed anywhere (real 5.55, synthetic 5.25). Thin headroom — see §20 |
| `pcen_primary_z_floor` | 7.0 | CASE B: 1.45 above the highest pcen null (5.55); the real low-SNR truth measures 10.44 |
| `onset_corroboration_z_floor` | 2.0 | above synthetic onset nulls (max 1.55) and ≈ real mismatch max (2.01); real corroboration at the truth measures 2.27. Defense in depth only |
| `ambiguity_z_ratio` | 0.95 | CASE D: a competitor carrying every deciding family at ≥ 95 % of the accepted cluster's strength means content ambiguity |

Acceptance:

- **CASE A — healthy strong recording**: one cluster carries BOTH primaries
  (tonal Z ≥ 5.0 AND pcen Z ≥ 5.6), each ranks it #1 (margin ≥ 1.0), overlap
  ≥ 30 s, and no comparable competitor → ACCEPT. Why: these two families
  have genuinely different failure modes (chroma: coincidental tonal
  structure; pcen_hpss: manufactured structure from noise); garbage would
  have to co-rank the same offset in both feature spaces, which never
  happened in 40 null/mismatch realizations.
- **CASE B — 零对话-like low-SNR recording**: pcen_hpss Z ≥ 7.0 AND pcen
  margin ≥ 1.4 AND onset corroboration (onset curve Z ≥ 2.0 at the cluster)
  AND overlap ≥ 30 s → ACCEPT. Why: a very strong, unique, low-SNR-spectral
  peak plus agreement from the (correlated, but differently-computed)
  temporal-change family is the observed signature of the true alignment on
  the real failure; onset here is corroboration of a dominant primary, not
  a second vote.

Abstention (machine-actionable reason codes):

- **CASE C — no shared signal / mismatched song**: neither case's floors are
  met → `ABSTAIN_NO_CLUSTER_MEETS_FLOORS` (10/10 real mismatches,
  0/30 synthetic nulls accepted; also `repeated_structure_tiled` and
  `no_shared_signal` synthetic cases).
- **CASE D — repeated / structurally ambiguous**: two qualifying clusters,
  or one qualifying cluster with a materially comparable competitor
  (≥ 0.95 × strength in every deciding family) → `ABSTAIN_AMBIGUOUS_CLUSTER`.
- **CASE E — implausible overlap**: overlap < 30 s at every candidate →
  `ABSTAIN_INSUFFICIENT_OVERLAP`.
- Strong pcen primary present but onset corroboration missing →
  `ABSTAIN_PRIMARY_NOT_CORROBORATED` (the conservative choice for
  recordings where only one family speaks).

The product priority is enforced structurally: **false ACCEPT is worse than
false ABSTAIN**, so every ambiguous situation resolves to ABSTAIN, and the
single-family path requires the strongest evidence combination.

## 10. Why the policy is not majority voting

- There are exactly **three** families, and one of them (`onset_temporal`)
  can never *decide* anything — it can only corroborate a pcen_hpss primary
  that already cleared a floor 1.45× above any measured garbage peak.
- `pcen` and `pcen_hpss` are collapsed into one family member before any
  counting happens (enforced in `_build_clusters`; unit-tested).
- `hybrid` can never accept alone even at Z 10 — it needs pcen agreement
  (its real-world false-confident failures: −1.997 s at Z 5.49 on 零对话，
  and Z 3.44–5.96 on all ten mismatched pairs).
- "Two methods agree" as a rule would accept the hybrid+chroma cluster at
  −1.997 s on the real failure (they always agree — same feature family).
  The engine instead requires agreement between families with *different*
  failure modes, plus uniqueness, overlap, and ambiguity checks.

## 11. Engine v2 architecture

New module `alignment_engine_v2.py` (production-quality, UI-independent,
**not wired into the GUI**):

```
find_offset_v2(video_path, music_path, sr=22050, policy=None)
    -> AlignmentDecision          # file entry, extraction + ffmpeg glue
decide_alignment(y_video, y_music, sr, hop_length, policy, durations_s)
    -> AlignmentDecision          # audio entry
decide_from_families(family_results, sr, hop, policy, video_dur, music_dur)
    -> AlignmentDecision          # decision layer (test seam)
decision_message(decision, tr=None)
    -> str                        # presentation, separable from decisions
```

`AlignmentDecision`: `status` (`accepted` | `abstained`), `offset`
(float | None), `reason_code` (machine-actionable), `evidence` (per-family
Z/runtime/errors + durations + cluster count), `clusters` (serialized
candidate diagnostics incl. per-family cluster Z/margin, competing
offsets, overlap), `policy` (thresholds in effect), `runtime_s`.
Abstention is a *decision*, not an exception — no
`CorrelationLowConfidenceError` is raised; the v1 contract is untouched.

Generators reuse production internals (`_align_hybrid`, `_align_onset`,
`extract_audio`) so v1 and v2 numbers stay directly comparable; PCEN
features are ported into the engine (production code must not import the
experiments package).

## 12. Unit / regression test coverage

### Engine unit tests

`tests/test_alignment_engine_v2.py` — 13 tests, media-independent,
deterministic:

- CASE A dual-family agreement accepts the common peak;
- CASE C: no-evidence abstains; misleading high-Z single-family peak
  abstains;
- **family bookkeeping: `pcen` + `pcen_hpss` agreeing on a strong wrong
  candidate is ONE vote** → `ABSTAIN_PRIMARY_NOT_CORROBORATED`, never an
  accept;
- CASE B: strong pcen primary + onset corroboration accepts; same primary
  without onset abstains;
- CASE D: comparable competing cluster (both primaries, ≥ 0.95 strength)
  abstains as ambiguous;
- CASE E: strong dual-family peak with 20 s overlap abstains
  (`min_overlap_s` = 30);
- decision serialization (`as_dict` round-trip, policy echo) and
  presentation separation (`decision_message`); default v1 path untouched
  (`_CONFIDENCE_THRESHOLD == 2.0`, `find_offset` intact);
- end-to-end synthetic audio: strong signal accepts within 0.2 s; no-signal
  abstains; full `find_offset_v2` file path (WAV in/out through ffmpeg)
  accepts and abstains.

Result: **13 passed**. Whole suite: 19 pre-existing + 13 = 32 passed
(§22).

### Real-corpus benchmark results (29 positives / 10 negatives)

29/29 positives accepted by Engine v2; 28/28 pairs where v1 accepted agree
within tolerance (max deviation ≈ 0.05 s) — the single non-agreement is
`lingduihua_132`, where v1 is WRONG (−1.997 s) and Engine v2 is right
(+12.492 s). 10/10 mismatches abstain (`ABSTAIN_NO_CLUSTER_MEETS_FLOORS`);
0 dual-family clusters on any mismatch; 0 worker errors. Every healthy
pair accepts via CASE A (`ACCEPT_DUAL_FAMILY`):

| case | v1 hybrid (Z) | engine v2 | reason | agree |
|---|---|---|---|---|
| lingduihua_132 | −1.997 (5.49) WRONG | **+12.492** | ACCEPT_PRIMARY_WITH_CORROBORATION | **no (v1 wrong)** |
| lividi_132 | +9.868 (15.23) | +9.915 | ACCEPT_DUAL_FAMILY | yes |
| drops_132 | +10.240 (15.44) | +10.286 | ACCEPT_DUAL_FAMILY | yes |
| yanwulieche_132 | +10.704 (19.72) | +10.751 | ACCEPT_DUAL_FAMILY | yes |
| baixiwang_132 | +10.588 (15.97) | +10.635 | ACCEPT_DUAL_FAMILY | yes |
| goganjue_niaojia_132 | +10.217 (12.35) | +10.286 | ACCEPT_DUAL_FAMILY | yes |
| dancerobotdance_133 | +10.402 (13.23) | +10.449 | ACCEPT_DUAL_FAMILY | yes |
| bai39_134 | +10.820 (22.14) | +10.844 | ACCEPT_DUAL_FAMILY | yes |
| hongzhoutian_135 | +32.670 (19.68) | +32.717 | ACCEPT_DUAL_FAMILY | yes |
| fenzhen_ds_1..4 | +9.149/+10.542/+6.571/+10.147 (Z 9.1–13.3) | +9.195/+10.588/+6.618/+10.194 | ACCEPT_DUAL_FAMILY | yes |
| haiditan_ds_0..5 | +11.749/+11.146/+9.125/+14.048/+9.334/+9.172 (Z 6.2–15.6) | +11.796/+11.192/+9.172/+14.095/+9.358/+9.195 | ACCEPT_DUAL_FAMILY | yes |
| samesha_411 | +14.025 (16.01) | +14.071 | ACCEPT_DUAL_FAMILY | yes |
| decision90 | +9.334 (17.38) | +9.381 | ACCEPT_DUAL_FAMILY | yes |
| letudive | +13.351 (15.98) | +13.398 | ACCEPT_DUAL_FAMILY | yes |
| queen | +15.255 (15.87) | +15.302 | ACCEPT_DUAL_FAMILY | yes |
| leyixiaolao | +11.378 (19.82) | +11.424 | ACCEPT_DUAL_FAMILY | yes |
| chiyaoshuijiao | +9.009 (19.05) | +9.056 | ACCEPT_DUAL_FAMILY | yes |
| babieta | +10.170 (18.21) | +10.217 | ACCEPT_DUAL_FAMILY | yes |
| caibushimo | +14.257 (15.71) | +14.303 | ACCEPT_DUAL_FAMILY | yes |
| maodunxinli | +15.952 (21.66) | +15.998 | ACCEPT_DUAL_FAMILY | yes |
| maodunxinli_niaojia | +12.980 (19.27) | +13.050 | ACCEPT_DUAL_FAMILY | yes |

## 13. Strong-signal behavior

Synthetic `strong_music` (music + 0.004 noise at +7.30 s): accepted at
+7.291 s via CASE A (error 9 ms). Real corpus: every healthy pair should
accept via CASE A with v1/v2 agreement — results in the §12 table
(`real_corpus_ra12b.json`).

## 14. Low-SNR behavior

Synthetic `low_snr_taps` (taps +28 dB, near-periodic, the RA-1.2A
regression where plain pcen and logmel_flux pick wrong offsets): accepted
at +13.607 s via CASE A (error 7 ms) — tonal #1 (Z 6.95) and pcen_hpss #1
(Z 5.67) co-rank the truth. Real 零对话 (music buried in arcade ambience):
accepted at +12.4923 s via CASE B (§17).

## 15. No-signal / mismatch abstention behavior

- Synthetic `no_shared_signal`: abstained (`NO_CLUSTER_MEETS_FLOORS`).
- 30 synthetic null realizations: 0 accepts.
- 10 real mismatched-song pairs: 0 accepts — while production v1.1.x
  false-accepts **all ten** with confident-looking Z up to 5.96. This is
  the safety improvement RA-1.2B exists for.

## 16. Ambiguity behavior

- `repeated_structure` (looped music, single span in the recording): the
  8 s twins are NOT materially comparable — pcen_hpss separates the true
  placement 1.35 : 1 — so the engine accepts the *correct* offset
  (+9.799 vs GT 9.80, error 1 ms); expectation `no_wrong_accept`, pass.
- `repeated_structure_tiled` (recording contains the tiled loop — evidence
  genuinely non-unique, all families tie at 8 s multiples): abstained,
  `ABSTAIN_AMBIGUOUS_CLUSTER`. A competing cluster carrying both primaries
  at ≥ 0.95 strength forces the abstain.

## 17. 零对话 Engine v2 result

| engine | status | offset | evidence |
|---|---|---|---|
| v1.1.x production (`find_offset`) | accepted (WRONG) | **−1.9969 s** (Z 5.49) | hybrid alone, Z ≥ 2.0 gate |
| **Engine v2** (`find_offset_v2`) | **ACCEPTED** | **+12.4923 s** | `ACCEPT_PRIMARY_WITH_CORROBORATION` |

Evidence at the accepted cluster: pcen_hpss Z 10.44 / margin 1.893
(primary), plain pcen Z 5.88 (same-family diagnostic), onset Z 2.268
(corroboration, top-1 at +12.446 s); the hybrid cluster at −1.997 s
(Z 5.49) fails every acceptance case because no pcen evidence supports it.
Error vs the independently established ground truth +12.4 ± 0.4 s:
**0.09 s**. This is precisely the RA-1.2A CASE-B pattern (wrong/confident
hybrid, very strong unique pcen_hpss, weak-but-agreeing onset).

## 18. Test-export path

One local test export was produced through the existing
`auto_sync.mix_and_export` path (stream copy):

    D:\Daozh\Videos\舞萌手元\13.2\零对话\零对话_engine_v2_test.mp4

It does NOT overwrite the source video or the previous
`零对话_synced.mp4`, and it is **not committed** (local test artifact for
owner listening judgment).

## 19. Runtime / memory measurements (零对话， 179.7 s video / 152.0 s track)

| stage | time |
|---|---|
| audio extraction (2× ffmpeg) | ≈ 3.1 s |
| hybrid generator | 3.16 s |
| onset generator | 0.33 s |
| pcen_hpss generator | 4.05 s |
| pcen generator (diagnostic) | 0.50 s |
| **Engine v2 total wall** | **8.54 s** |
| v1.1.x total wall (comparison) | ≈ 5.6 s |

Peak Python-allocation memory: **247.4 MB**; process RSS 218 → 265 MB
(psutil). A 10-minute video scales the mel/HPSS matrices ≈ 3.3× — still
modest, worth re-measuring before any default-path switch.

Duplicate-work analysis: the mel spectrogram for `pcen` and `pcen_hpss`
could be computed once and shared (saves ≈ 0.2–0.3 s, < 4 %); onset
strength is computed inside both `_align_hybrid` and `_align_onset`
(saves ≈ 0.3 s). Both wins are small and would couple the generators'
internals; per the task, optimization stays secondary to correctness and
was not done.

## 20. Remaining risks

1. **pcen_z_floor headroom is thin**: floor 5.6 vs highest measured pcen
   null 5.55 (real) — and the synthetic `low_snr_taps` true peak measures
   Z 5.67, only 0.07 above the floor. The calibration set is too small to
   widen this honestly; more real low-SNR positives are needed.
2. **Only ONE manually ground-truthed real low-SNR positive** (零对话).
   The 28 other positives are consensus-based (v1/v2 agreement), and 24 of
   them previously produced synced outputs; none independently verifies
   low-SNR generalization.
3. **Onset corroboration floor (2.0) vs real corroboration at the truth
   (2.27)**: headroom 0.27. A real low-SNR recording with weaker onset
   agreement would (correctly, conservatively) abstain via CASE B.
4. Real "true no-signal" recordings (music completely absent) are not in
   the corpus; synthetic nulls stand in.
5. Ambiguity calibration on real repeated-structure charts is untested
   (the tiled-loop synthetic is the stand-in).
6. `positive_strong` classes are provisional; some recordings may contain
   internal (loopback) game audio, which makes them trivial cases.
7. HPSS memory on long videos (§19) — measure before any default switch.
8. Abstain UX (manual-offset handoff) is a product decision for RA-1.2C.

## 21. Exact files changed

Added:
- `alignment_engine_v2.py` — Engine v2 module (non-default)
- `tests/test_alignment_engine_v2.py` — 13 media-independent tests
- `experiments/low_snr_alignment/calibrate_nulls.py` — expanded null calibration
- `experiments/low_snr_alignment/real_corpus_eval.py` — real-corpus benchmark
- `experiments/low_snr_alignment/engine_v2_owner_test.py` — owner-test tool (decision + perf + guarded export)
- `experiments/low_snr_alignment/local_corpus.example.json` — manifest schema
- `experiments/low_snr_alignment/results/null_calibration_n30.json` — evidence
- `experiments/low_snr_alignment/results/real_corpus_mismatch.json` — evidence (path-free)
- `experiments/low_snr_alignment/results/real_corpus_ra12b.json` — evidence (path-free)
- `experiments/low_snr_alignment/results/synthetic_run_ra12b.json` — evidence
- `docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md` — this report

Modified:
- `docs/RA-1.2A-LOW-SNR-ALIGNMENT.md` — §2 corrections
- `experiments/low_snr_alignment/synthetic_eval.py` — expected-behavior semantics (§13 of task)
- `experiments/low_snr_alignment/README.md` — documents the new tooling
- `.gitignore` — ignores `experiments/low_snr_alignment/local_corpus.json`

Not changed: `auto_sync.py`, `ui_main.py`, `diagnose_offset.py`, version
strings, release metadata. Default GUI behavior untouched. No media, no
local manifest, no test export committed.

## 22. Exact validation results

| check | command | result |
|---|---|---|
| baseline suite (start) | `python -m pytest -q` | 19 passed in 3.65 s |
| full suite (end) | `python -m pytest -q` | **32 passed in 14.08 s** |
| engine tests | `python -m pytest tests/test_alignment_engine_v2.py -q` | 13 passed |
| syntax | `python -m compileall -q auto_sync.py diagnose_offset.py ui_main.py tests experiments` | OK (exit 0) |
| whitespace | `git diff --check` | clean (LF/CRLF notices only, no errors) |
| synthetic benchmark (expected-behavior) | `python experiments/low_snr_alignment/synthetic_eval.py --json …` | 6/6 engine expectations pass, exit 0; baseline observations: 11 correct, 9 wrong_known_baseline, 9 false_confident_known_baseline, 1 below_confidence (all informational) |
| expanded null calibration | `python experiments/low_snr_alignment/calibrate_nulls.py --n 30 --json …` | 0/30 false accepts; §6/§7 tables |
| real-corpus benchmark (29 pos + 10 neg) | `python experiments/low_snr_alignment/real_corpus_eval.py --json …` | 29/29 positives accepted, 28/28 agree with accepted v1, 10/10 mismatches abstain, 0 worker errors |
| 零对话 Engine v2 | `python experiments/low_snr_alignment/engine_v2_owner_test.py` | ACCEPTED +12.4923 s, error 0.0923 s vs GT (§17) |
| path-leak check | `grep Daozh\|舞萌` over committed evidence JSONs | 0 matches |

Benchmark semantics: the synthetic suite exits non-zero **only** on engine
regressions; legacy baseline rows (including known-wrong ones) are recorded
as `wrong_known_baseline` / `false_confident_known_baseline` /
`below_confidence` observations, never failures — machine-actionable for
future CI coverage.

Note on benchmark robustness: single-process benchmark runs of the full
corpus twice died silently ~25–30 cases in (no traceback; each case runs
fine in isolation), so `real_corpus_eval.py` evaluates every case in an
isolated worker subprocess with incremental result writing. The committed
results come from that worker-isolated run; the cause of the native-level
parent deaths (likely a dependency allocation issue under long loops) is
recorded as an open observation, not resolved here.

## 23. Git final state

Committed as one coherent commit on `main` and pushed to `origin/main`
after all checks above passed:

```
docs: RA-1.2B alignment engine v2 evidence gate (non-default path)
```

No release, no tag, no version bump, no default-behavior change.
`experiments/low_snr_alignment/local_corpus.json` (personal paths), all
media, and the test export remain untracked/local; committed evidence
JSONs contain case ids and numbers only.

## 24. Recommendation

**NEEDS_MORE_REAL_DATA**

Justification: the architecture, decision policy, and safety behavior are
working — 0 false accepts on 10 real mismatches and 30 synthetic nulls
where v1.1.x false-accepts 10/10 mismatches, and the real low-SNR failure
is now accepted correctly at +0.09 s error. But the thresholds cannot yet
be responsibly frozen: the CASE A pcen floor (5.6) sits 0.05 above the
highest measured real pcen null and 0.07 below the synthetic taps truth,
onset corroboration headroom is 0.27, and the entire real low-SNR evidence
base is ONE manually ground-truthed recording. RA-1.2C should begin with
owner listening tests on this build (the engine is callable and safe),
while collecting more labeled low-SNR positives to widen the calibration
base before any default-path integration.
