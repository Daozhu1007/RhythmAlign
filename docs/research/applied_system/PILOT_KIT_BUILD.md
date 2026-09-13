# Pilot Kit Build — Fresh Acoustic Pilot

Status: **PILOT_KIT_READY** — selection frozen, buffers rendered and
digitally validated, take plan populated, owner instructions final.
PILOT_ONLY / NOT PAPER EVIDENCE / NO RECORDING HAS BEGUN.

- Authority: `FRESH_PILOT_PLAN.md` sections 5–6, 12 step 1 (kit build).
- Selection machinery: `experiments/applied_system/pilot_source_selection.py`
  (frozen record: `experiments/applied_system/pilot_pack/source_selection.json`).
- Kit machinery: `experiments/applied_system/pilot_kit_build.py`
  (kit record: `experiments/applied_system/pilot_pack/kit_manifest.json`).
- Owner hand-off: `experiments/applied_system/pilot_pack/` (buffers +
  interference copy), instructions:
  `OWNER_PILOT_INSTRUCTIONS.md`.
- The owner's media roots were treated as READ-ONLY source libraries
  throughout: listed, hashed, and decoded only. Zero files renamed,
  moved, rewritten, retagged, or deleted (verified: no modification-time
  change under either root on build day). All generated material lives
  under `experiments/applied_system/pilot_pack/` (gitignored media +
  committed manifests/hashes). No copyrighted audio is committed.

## Media roots scanned

- `D:\Daozh\Videos`
- `D:\Daozh\Music`

Recursive scan over the standard audio extensions (.wav/.flac/.mp3/.m4a/
.aac/.ogg/.opus/.wma). The Videos tree does contain standalone audio
files nested deeply inside handcam project folders (e.g.
`Videos\舞萌手元\13.1\steelyou\track.mp3`); no video-container extraction
was needed — the standalone pool was sufficient.

## Candidate-count summary

| Item | Count |
|---|---|
| Audio files found | 40 |
| Unique by SHA-256 | 38 (2 exact duplicate pairs: `分诊`, `海底谭` — both historically excluded anyway) |
| Codecs | 40 × MP3 (48 kHz stereo; analysis decodes to mono) |
| Historically excluded | 33 files |
| Clean pool after screening | 7 candidates |
| Clean-pool duration range | 126.1 – 232.1 s (median 150.076 s) |

The complete 40-file inventory (personal paths) is a LOCAL-ONLY file
(`pilot_pack/local/inventory.json`, gitignored, never committed).

## Historical exclusions

Source-disjointness from all prior RhythmAlign research, enforced by a
provenance-cited exclusion list (`EXCLUSIONS` in
`pilot_source_selection.py`, matched case-insensitively over source
paths; ID3 tags of the surviving pool were additionally verified by hand
against the same identities). Excluded identities, by evidence source:

- **延误列车 / 零对话** — explicit task exclusions; RA-1.2 calibration
  list; Astra blocker case (零对话 video × 延误列车 music); v1.2.0
  release-validation cases; temporal-support blocker reproduction.
- **RA-1.2 calibration corpus** (`RA-1.2C-CALIBRATION-HARDENING.md`):
  零对话, 红Lividi, DROPS, 延误列车, 白妄想/妄想感伤代偿联盟, 共感觉,
  分诊, 萨姆沙, 90decision, QUEEN.
- **RA-1.2 holdout corpus** (same document): DanceRobotDance, 白39/39,
  宙天, 海底谭 (same song identity as ウミユリ海底譚), Let u dive,
  乐意效劳, 吃药睡觉, 巴别塔, 才不是恶魔呢, 矛盾心理.
- **RA-1.2 dev corpus** (`RA-1.2B-ALIGNMENT-ENGINE-V2.md`):
  INTERNETOVERDOSE, on your mark, 右曲, 强风大背头/強風オールバック,
  心跳不止, all Arcaea手元 folders (Chelsea/7mai, Code Oblivion,
  One Step Closer), Override/オーバーライド (both candidate tracks).
- Named identities with no current-pool file (recorded for
  completeness): 猫娘打架, 红枪, 水神1.5, 再见公主.

Ambiguity policy: no guessing from partial names — an identity is
excluded only on a clear match; the seven survivors were additionally
checked by ID3 title/artist against the full list above.

## Song A selection

**SONG A = Bloody Trail** (Hommarju, maimai でらっくす)

- Path: `D:\Daozh\Music\舞萌手元用\Bloody Trail.mp3`
- Duration: 150.076 s; 48 kHz stereo MP3 (320 kbps class); decodes
  cleanly; edge silence 0.25 s lead / 1.23 s trail.
- SHA-256: `0c1bad0c937b57ee49b7189a4d0ca7fd01f4d001859fd0723e9b0dd1165fd077`
- **Why:** pre-declared ordinary-representative rule — among clean-pool
  candidates with structural score strictly below Song B's, the one
  whose duration is closest to the clean-pool median (150.076 s; Bloody
  Trail IS the median track, distance ≈ 0.02 s). Its structural score
  (R_long 0.972, mid-pool; peak recurrence at a short 22 s lag) is
  unremarkable. Selection used source properties ONLY; no RhythmAlign or
  comparator output was computed on any candidate.

## Song B structural selection

**SONG B = スティールユー (Steel You, Omoi)** — file `track.mp3` in the
`steelyou` handcam project folder

- Path: `D:\Daozh\Videos\舞萌手元\13.1\steelyou\track.mp3`
- Duration: 152.842 s; 48 kHz stereo MP3 (256 kbps class); edge silence
  1.61 s lead / 0.17 s trail (within the ≤ 5 s screen).
- SHA-256: `cf92dceb32aac347c7861308e1982be9fa98a6145b992e85dd1e51ff30e1eaf1`
- **Analysis method (pre-declared, RhythmAlign-independent):** mono
  mixdown → STFT (nperseg 4096, hop 1200 = exactly 40 fps, hann) →
  log-compressed magnitude → 12-bin pitch-class profile (65–6000 Hz) →
  per-frame L2 normalization → 0.5 s block means (2 blocks/s) → cosine
  self-similarity. **Ranking criterion R_long** = mean self-similarity
  over all frame-block pairs at lag ≥ 16 s (long-range recurrence mass).
  This is a deterministic pilot-source selection heuristic, NOT a
  universal difficulty metric.
- Clean-pool ranking (R_long): steelyou 0.988 > Divide et impera 0.978
  > さよならプリンセス 0.974 > Scarlet Lance 0.972 ≈ Bloody Trail 0.972
  > ARROW 0.952 > Sage 0.947.
- **Why selected:** highest R_long among BUF-BMID-eligible candidates
  (duration ≥ 150 s so a 90 s + 60 s mid-song payload fits). Its peak
  long-lag recurrence sits at ≈ 50.5 s with near-max similarity, i.e.
  strongly repeated ~50 s-scale sections — qualitatively and
  measurably more long-range self-similar than Song A (0.988 vs 0.972,
  peak lag 50.5 s vs 22 s), satisfying the plan's requirement that song
  B stress placement uniqueness (≥3 near-identical sections family) for
  every comparator including Panako.

## Interference selection

**INTERFERENCE = Divide et impera** (BlackY a.k.a. WAiKURO survive,
maimai でらっくす)

- Path: `D:\Daozh\Music\舞萌手元用\Divide et impera.mp3`
- Duration: 143.188 s; 48 kHz stereo MP3; decodes cleanly.
- SHA-256: `26f0284c9f104f54c2fcca5638c1b1398e924bf64a851f0a0732814393e80904`
- **Why:** pre-declared rule — maximum mean chroma-texture distance to
  {Song A, Song B} among remaining clean candidates (different artist
  and composition from both; not a remix or version of either;
  historically clean). It plays softly from a second device during take
  8 only and is never a reference in any pairing. Honest note: the
  texture-distance metric's absolute spread across this game-music pool
  is small (chosen value 0.013, cosine-distance units); the binding
  requirement — a clearly unrelated, identity-disjoint normal music
  source — is independently satisfied.

## Frozen hashes

Frozen BEFORE buffer rendering and BEFORE any benchmark observation
(`source_selection.json`, status `SELECTED_FROZEN`; replacement is only
permitted before recording for the pre-declared causes — decode failure,
technical impossibility, protocol violation, access problem — documented
at replacement time).

| Role | Identity | Source SHA-256 | Duration |
|---|---|---|---|
| Song A | Bloody Trail | `0c1bad0c…65fd077` | 150.076 s |
| Song B | スティールユー | `cf92dceb…e1eaf1` | 152.842 s |
| Interference | Divide et impera | `26f0284c…93e80904` | 143.188 s |

## Generated buffers

Rendered by `pilot_kit_build.py` with the UNCHANGED marker protocol
(`marker_protocol.render_marker_buffer`): chirp 0.75 s | guard 1.0 s |
60.0 s payload | guard 1.0 s | chirp 0.75 s @ 48 kHz mono PCM_16
(63.5 s, 6,096,044 bytes each; marker1 @ sample 0, payload
[84000, 2964000), marker2 @ 3012000).

| Buffer | Payload | SHA-256 |
|---|---|---|
| `pilot_pack/buffers/BUF-A.wav` | A[0 s → 60 s] | `fe224ed7…970e49b3` |
| `pilot_pack/buffers/BUF-B1.wav` | B[0 s → 60 s] | `91c9740f…23ebfb1d` |
| `pilot_pack/buffers/BUF-BMID.wav` | B[90 s → 150 s] | `f81b84fc…98b979a` |

- Reference pool (agent-side, gitignored `pilot_pack/local/references/`):
  `REF-A.wav` (full decoded A, 150.072 s,
  SHA-256 `3bb5f4aa…dbedc5d`), `REF-B.wav` (full decoded B, 152.842125 s,
  SHA-256 `9b9c7059…8db645b`) — full tracks, matching production usage.
  GT bookkeeping: BUF-A/BUF-B1 reference GT equals the payload GT;
  BUF-BMID reference GT = payload GT − 90.0 s (recorded per buffer in
  the kit manifest, applied by the analysis harness).
- Interference hand-off: local copy `pilot_pack/INTERFERENCE.mp3`
  (gitignored, byte-identical to the frozen source; hash + source path
  recorded in `kit_manifest.json` / `take_plan.json`), so the owner can
  copy it to the second playback device without searching the library.
- Determinism: two independent builds produced byte-identical buffers
  (identical SHA-256; fixed libsndfile decode, fixed protocol constants,
  fixed self-check seeds). Environment: Python 3.10.11, numpy 2.2.6,
  scipy 1.15.3, soundfile 0.13.1 / libsndfile 1.2.2.
- Rendered media is gitignored; only manifests and hashes are committed.

## Validation

`python -m experiments.applied_system.pilot_kit_build --validate-only`
(executes the full gate below; result `ok: true`, zero failures):

- All three playback buffers exist and hash-match both manifests. ✔
- Marker detection succeeds digitally on self-check captures of every
  shipped buffer: exactly 2 candidates, confidences ≈ 1.0. ✔
- Dual-marker QC: scale_error 0.0, mapping disagreement ≈ 0 (≤ 10 ms
  gate). ✔
- Trim bookkeeping: payload GT = +2.450 s on every buffer (lead 2.5 s −
  50 ms trim margin, exactly as designed); BUF-BMID reference GT =
  −87.550 s = 2.450 − 90.0. ✔
- No marker leakage after simulated trim (max residual NCC ≤ 0.026 vs
  0.15 gate). ✔
- Payload placement proven bit-exact: each buffer's payload region is
  byte-identical (int16) to the same region of the written reference. ✔
- `take_plan.json` validates; all 12 slots resolve to existing required
  playback assets; interference asset resolves and is identity-disjoint
  from A and B; Unicode Windows paths round-trip. ✔
- `take_plan.json` status `AWAITING_KIT_BUILD` → `KIT_READY`; the
  scientific 12-take design is unchanged. (Machinery fix: the template
  file used Python-style string concatenation and was not parseable as
  JSON; rewritten as valid JSON with identical content. The future
  harness would have hit the same error at ingest.)
- Owner library mutation: none (read-only scan/decode/copy; zero
  modification-time changes under either root on build day). ✔
- No acoustic recording was performed. ✔

## Pilot readiness

### PILOT KIT VERDICT
PILOT_KIT_READY

- Song A, Song B, interference: selected by pre-declared rules, frozen,
  hashed, and verified unchanged at build time.
- Three playback buffers + interference copy: rendered, deterministic,
  digitally validated.
- Comparator stack (already frozen): RhythmAlign v1.2.0, GCC-PHAT, NCC,
  Panako 2.1 (`PANAKO_INTEGRATION.md`).
- Owner workload: 12 takes, ≈ 1 hour, 3 recommended devices (2 = floor),
  no other people needed — `OWNER_PILOT_INSTRUCTIONS.md`.
- Next round (`pilot_harness.py`): ingest `pilot_pack/incoming/`,
  per-take GT/QC/trim, freeze-rule computation, single-pass comparator
  sweep, PILOT_ONLY reports.
