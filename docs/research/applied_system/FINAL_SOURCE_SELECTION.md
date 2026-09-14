# Final Source Selection

## Status

`FINAL_SOURCES_FROZEN` + `FINAL_ACQUISITION_KIT_READY`. The final source
pool is sufficient, S01–S10 plus a separate interference identity are
frozen, the 26-take acquisition manifest is frozen
(`AWAITING_FINAL_RECORDING`), and every playback buffer passed digital
validation. Final recording has NOT begun; it starts only when the owner
starts it in a separate task.

**NO COMPARATOR WAS RUN DURING FINAL SOURCE SELECTION.** No RhythmAlign,
GCC-PHAT, Panako, NCC, or Kdenlive execution touched any final candidate,
buffer, reference, or future final case. Selection used source properties
only (decode integrity, duration, edge silence, chroma recurrence
structure, chroma texture, identity provenance). The frozen protocol was
not changed in any way.

- Source freeze: `experiments/applied_system/final_pack/final_source_freeze.json`
  (file SHA-256 `6a6a38515b1f801eab3bc1dffe23306c77e14720e930edf6aaf9d185749aae30`,
  canonical body hash identical to the embedded `freeze_sha256`)
- Acquisition manifest:
  `experiments/applied_system/final_pack/final_acquisition_manifest.json`
  (file SHA-256 `bba8096cc3b3b85d47931b5d49f00c3834260f68f2313bc373b0be7c801d1f7d`,
  canonical `manifest_hash`
  `7e1c1d54e3c50576d68aa8b8c983c1ee7fb921d4ad2486c48b638ad3790b906a`)
- Authority: `FINAL_BENCHMARK_PROTOCOL.md` (FROZEN before final data
  collection); ledger snapshot
  `ab7572e352421e433b3ed6aff009fdc437d3c57bca73e257c626fcaef5385b9e`

## Fresh candidate intake

The owner-supplied read-only folder
`D:\Daozh\Music\RhythmAlign_FinalCandidates_Fresh` contained exactly 13
audio files (filesystem reality, matching the owner's count). All 13 were
hashed, probed, ID3-tag-read, and fully decoded; nothing in the folder was
renamed, moved, retagged, or modified in any way. 11 of the 13 files are
clean final-eligible identities; 2 are excluded identities in fresh
enclosures (see the exclusion audit). The full inventory with private
paths is LOCAL ONLY (`final_pack/local/final_audit.json`, gitignored).

## Complete exclusion audit

The committed ledger (31 historical identities in
`pilot_source_selection.EXCLUSIONS` + 3 pilot identities: Bloody Trail,
スティールユー / Steel You, Divide et impera) was applied unchanged over
path, filename, ID3 title/artist/album, and exact SHA-256.

This audit additionally resolved **translated/aliased identities** that
earlier name-based passes could not see, using the owner's own
repository-verifiable evidence (result-screen thumbnails in the video
project folders, ID3 tags, `*_synced.mp4` outputs, and the RA-1.2 corpus
lists). Four findings, three of which retire identities that the
2026-09-14 audit had classified FINAL_ELIGIBLE:

| Fresh/pool identity | Excluded as | Evidence |
|---|---|---|
| `スティールユー.mp3` (fresh folder) | `PERMANENTLY_EXCLUDED_PILOT` | byte-identical to the frozen pilot Song B source |
| `ゼロトーキング.mp3` (fresh folder) | `PERMANENTLY_EXCLUDED_HISTORICAL` (零对话) | byte-identical (same size + SHA-256) to the RA-1.2A failure-case file `Videos\舞萌手元\13.2\零对话\track.mp3`; its ID3 (TIT2 ゼロトーキング / TPE1 はるまきごはん) is identical too; 零对话 is the owner's Chinese name of the same song |
| Scarlet Lance (declared survivor) | `PERMANENTLY_EXCLUDED_HISTORICAL` (红枪) | `已发\红枪\红枪.jpg` result screen displays "Scarlet Lance"; folder holds 红枪_synced.mp4; 红枪 is a ledger identity |
| Sage (declared survivor) | `PERMANENTLY_EXCLUDED_HISTORICAL` (production use) | `不太想发的\Sage\` holds Sage_synced.mp4 + Sage_synced_2.mp4 — production RhythmAlign outputs (the RA-1.2B corpus-pair confirmation convention) |
| さよならプリンセス (declared survivor) | `PERMANENTLY_EXCLUDED_HISTORICAL` (再见公主) | `已发\再见公主\再见公主.jpg` result screen displays さよならプリンセス; folder holds 再见公主_synced.mp4 ×2; 再见公主 is a ledger identity |

A full sweep of every video-project folder (result-screen thumbnails,
read-only) mapped all remaining folders to songs — 13.1/animal=アニマル,
13.1/忒拉忒拉=てらてら, 13.1/转生苹果=転生林檎, 13.1/三小只=ホシシズク,
不太想发的/墓守=躯樹の墓守, 不太想发的/红世终孤独=World's end loneliness,
13.1/爱包=愛包ダンスホール, 13.1/甜食控=シュガーホリック,
不太想发的/彗星=彗星ハネムーン, 不太想发的/Maxi=Maxi,
13.1/帝国华击团=檄！帝国華撃団(改), 13.2/cpfc=コスモポップファンクラブ,
已发/FF=FLUFFY FLASH. None of those folders contains any RhythmAlign
output, so none of their songs is excluded by them; every `*_synced.mp4`
in the media library belongs to an already-excluded identity except the
Sage discovery recorded above. ARROW (`已发\ARROW\`) contains only the raw
video — no synced output, no corpus entry — and stays eligible.

Classification of the 13 fresh files + 4 declared survivors:

| Class | Count | Identities |
|---|---:|---|
| `PERMANENTLY_EXCLUDED_HISTORICAL` | 2 (fresh) + 3 (survivors invalidated) | ゼロトーキング (=零对话); Scarlet Lance (=红枪); Sage (production); さよならプリンセス (=再见公主) |
| `PERMANENTLY_EXCLUDED_PILOT` | 1 | スティールユー |
| `DUPLICATE` | 0 | none (hashes unique within the folder and against all 40 prior files) |
| `TECHNICALLY_UNSUITABLE` | 0 | all 13 decoded cleanly, ≥60 s, edge silence ≤5 s |
| `IDENTITY_REVIEW_NEEDED` | 0 | every alias question was resolved with owner-produced evidence; none left uncertain |
| `FINAL_ELIGIBLE` | 12 | 11 fresh + ARROW |

## Eligible pool

12 independent eligible identities (11 from the fresh folder + the
verified survivor ARROW; its hash is unchanged and its R_long recompute
matches the 2026-09-14 value exactly, an independent determinism check).
All are 48 kHz stereo MP3, cleanly decodable, durations 83.3–232.1 s.
Requirement: 10 references + 1 interference = 11 ≤ 12. SUFFICIENT, with
exactly one spare identity (ビビデバ) left unused by the deterministic rule.

## Performance-blind selection rule

`FINAL-SELECT-V1`, declared in `final_source_selection.py` BEFORE the
structural analysis was run, applied mechanically, reproducible:

- E1–E4 screening: exclusion ledger (incl. aliases/hashes), duplicate
  collapse by SHA-256, full decode + duration ≥60 s + edge silence ≤5 s,
  IDENTITY_REVIEW_NEEDED for unresolved identity (none remained).
- R1: the 3 highest-R_long eligible identities become references, flagged
  `REPETITIVE_STRESS_SOURCE` (rank-based; no tuned threshold; satisfies the
  frozen "≥3 deliberately repetitive" requirement).
- R2: the remaining 7 reference slots fill in ascending SHA-256 order.
- R3: S01–S10 = the 10 references sorted by ascending SHA-256 (slot order
  independent of structure).
- R4: interference = the eligible non-reference identity with the maximum
  mean chroma-texture cosine distance to the 10 references (generalization
  of the frozen pilot interference rule; tie: ascending SHA-256).
- No personal preference, popularity, or predicted/observed system
  performance enters any step. R_long is a deterministic selection
  heuristic, NOT a universal difficulty metric.

## S01–S10

| Slot | Identity | Artist | Duration s | R_long | Flag | SHA-256 (prefix) |
|---|---|---|---:|---:|---|---|
| S01 | World's end loneliness | 打打だいず | 150.286 | 0.95940 | ORDINARY | `087fce52c70b885c…` |
| S02 | 転生林檎 | ピノキオピー | 148.138 | 0.97467 | ORDINARY | `1347b77c7b789165…` |
| S03 | 7 Wonders | 削除 | 153.214 | 0.97535 | ORDINARY | `25548ff816d53f5f…` |
| S04 | Fragrance | Tsukasa(Arte Refact) | 83.333 | 0.97438 | ORDINARY | `32413fa39a235535…` |
| S05 | ホシシズク | 森羅万象 | 159.560 | 0.96920 | ORDINARY | `3723944c36e38774…` |
| S06 | ARROW | niki feat.Lily | 232.083 | 0.95204 | ORDINARY | `3e61a90722f1a979…` |
| S07 | 躯樹の墓守 | 隣の庭は青い(庭師+Aoi) | 137.062 | 0.96266 | ORDINARY | `49c26864446ce0fa…` |
| S08 | Cryptarithm | 削除 | 152.229 | 0.98968 | REPETITIVE_STRESS_SOURCE | `5888dc3ef9e3fa32…` |
| S09 | アニマル | DECO*27 | 153.885 | 0.98511 | REPETITIVE_STRESS_SOURCE | `7e7df8adb965dedd…` |
| S10 | Straight into the lights | Cosmograph | 153.333 | 0.98607 | REPETITIVE_STRESS_SOURCE | `bc7f4d08d9fc7bda…` |

Full hashes, paths, codec details, and structural descriptors are in the
freeze JSON. After the freeze these identities may never be swapped
because of alignment results.

## Repetitive stress sources

Cryptarithm, アニマル, Straight into the lights — exactly the three
highest-R_long identities in the eligible pool (0.98968 / 0.98511 /
0.98607). Long-lag recurrence peaks: Cryptarithm ≈22 s, アニマル ≈98.5 s,
Straight into the lights ≈96 s. This is a source-only structural
descriptor for placement-uniqueness stress, not a difficulty claim.

## Interference source

**てらてら** (和田たけあき), file `てらてら.mp3`, SHA-256
`b8c41c719b537906…` (full hash in the freeze). Won R4 by maximum mean
chroma-texture distance to the 10 references among the remaining
candidates; not S01–S10, not historical, not pilot-exposed, not a
version/remix of any reference, cleanly decodable. It plays softly from a
second playback device during final17–final20 only and is never a
reference in any pairing.

## Source freeze hash

- Path: `experiments/applied_system/final_pack/final_source_freeze.json`
- File SHA-256: `6a6a38515b1f801eab3bc1dffe23306c77e14720e930edf6aaf9d185749aae30`
- Embedded canonical `freeze_sha256`: identical (verified at kit-build
  time; the kit build refuses to run against a drifted freeze).
- Rule identifier recorded inside: `FINAL-SELECT-V1`.

## Condition allocation

Exactly the frozen protocol counts, bound to slots at freeze time:

- final01–final10: ORDINARY, S01–S10
- final11–final16: S01–S06 with LOW_LEVEL = S01/S03/S05 (final11/13/15)
  and TAP_DOMINANT = S02/S04/S06 (final12/14/16) — alternating slot
  parity, frozen deterministically before recording
- final17–final20: INTERFERENCE, S07–S10 (interference source from the
  second playback device)
- final21–final22: PARTIAL, S01–S02 (payload starts at
  min(90 s, duration−60 s): S01 at 90.000 s, S02 at 88.138 s)
- final23–final24: DEVICE_VARIATION, S09–S10 on the second recording
  device (D2), in the second room

## Wrong-reference freeze

The frozen rotation S(i mod 10)+1 over primary take number i=1..24 was
filled mechanically: final01→S02, final02→S03, … final10→S01, and so on
through final24→S05. Verified: no take is offered its own source slot;
the rotation was fixed before song identities were filled and is never
changed from results. Any ACCEPT against the offered wrong reference is
WRONG_ACCEPT; refusal is SAFE_ABSTAIN.

## Strict repeats

repeat01 = strict repeat of ordinary final01 (S01, BUF-S01);
repeat02 = strict repeat of ordinary final02 (S02, BUF-S02). Both are
recorded in SESSION_1 immediately after their originals, reported
separately from the 24 scored positives, and carry no wrong-reference
slot.

## Sessions / rooms / devices

Exactly 3 owner-friendly sessions (no participants; everything done
alone; minimal setup switching):

| Session | Room | Recording device | Playback | Takes |
|---|---|---|---|---|
| SESSION_1 | ROOM_A (pilot room) | D1 (primary phone) | P1 (PC speakers) | final01–final10, repeat01, repeat02 |
| SESSION_2 | ROOM_A | D1 | P1 | final11–final16, final21, final22 |
| SESSION_3 | ROOM_B (second room) | D2 (second device) | P1 (+ P2 for interference) | final17–final20, final23, final24 |

3 sessions ≥ 3 ✔; 2 recording devices (D1, D2) ≥ 2 ✔; 2 rooms ≥ 2 ✔.

## Playback kit

12 buffers required by the 26 instructions, rendered with the UNCHANGED
marker protocol (chirp 0.75 s | guard 1.0 s | 60 s payload | guard 1.0 s |
chirp 0.75 s, 48 kHz mono PCM_16, 63.5 s each):

- BUF-S01 … BUF-S10 (payload = source [0 s, 60 s))
- BUF-S01-PART (payload [90.000 s, 150.000 s)), BUF-S02-PART (payload
  [88.138 s, 148.138 s))
- `final_pack/INTERFERENCE.mp3` — owner hand-off copy, byte-identical to
  the frozen てらてら source

Per buffer the manifest records: buffer ID, source slot, payload slice,
source hash, output hash, marker positions, exact intended GT (ordinary:
reference GT = payload GT ≈ +2.45 s at the standard lead; partial:
payload GT − slice start, −87.550 s / −85.688 s), duration, and condition
role. Digital validation per buffer: deterministic quiet-noise self-check
capture → exactly 2 marker candidates → dual-marker GT → trim bookkeeping
→ zero marker leakage → payload region bit-identical to the reference
slice. A full rebuild reproduced all 12 buffer hashes and the manifest
hash byte-identically (deterministic rerender). All generated audio stays
gitignored under `final_pack/` (buffers/, local/, INTERFERENCE.*);
references (`final_pack/local/references/REF-Sxx.wav`, full decoded
sources) are agent-side and gitignored.

## Acquisition manifest

`experiments/applied_system/final_pack/final_acquisition_manifest.json`
— canonical JSON with embedded `manifest_hash`
`7e1c1d54e3c50576d68aa8b8c983c1ee7fb921d4ad2486c48b638ad3790b906a`,
status `AWAITING_FINAL_RECORDING`. Contains final01…final24 + repeat01 +
repeat02 with source slot, condition, session, room, recording device,
playback device, playback buffer, GT stratum (EXACT_GT), wrong-reference
slot + hash, interference identity (final17–final20), destination
filename, and source/reference hashes; plus the frozen slot/interference
identities, GT contract (threshold 0.163837792269, drift ±128.486056 ppm,
10 ms mapping gate, trim rule), and environment. Once frozen it is never
changed from result information.

## Copyright/access clarification

No copyrighted audio is committed. The source songs, the interference
track, the rendered buffers, the references, and all future raw recordings
stay in the owner's local library / gitignored `final_pack/` paths. Git
receives only identities, hashes, manifests, provenance, instructions,
validation metadata, code, and tests. All owner media roots were treated
as READ-ONLY: listed, hashed, decoded, and thumbnail-read only; zero
renames, moves, retags, re-encodes, or deletions.

## Contamination boundary

- No final candidate, buffer, reference, or future final case was ever
  shown to RhythmAlign, GCC-PHAT, Panako, NCC, or Kdenlive in this task.
- The fresh folder's two excluded files (スティールユー, ゼロトーキング)
  never entered the pool; the three invalidated survivors were removed
  BEFORE selection, on identity evidence only.
- The remaining fresh candidates are the owner's own handcam-project
  songs whose videos exist but were never processed by any
  RhythmAlign-family tool (verified by the synced-output sweep).
- Pilot identities remain permanently excluded; the historical ledger is
  preserved unchanged plus documented application extensions.

## Owner burden

3 sessions ≈ 10 min setup + 26 takes × ≈2.5 min ≈ **1.5 hours total**
(30–35 + 20–25 + 20–25 min plus breaks). Only the owner's own devices;
no other people; sessions may be on different days. The owner never needs
to understand S-slots, GT, markers, ppm, statistics, or wrong-reference
logic — `OWNER_FINAL_RECORDING_INSTRUCTIONS.md` is plain Chinese tables.

## Acquisition readiness

`FINAL_ACQUISITION_KIT_READY` — sources frozen, allocation frozen,
manifest frozen, buffers rendered + digitally validated, owner
instructions final. Nothing has been recorded. Final collection begins
only when the owner starts SESSION_1.
