# Kdenlive Final Preparation

## Status

`KDENLIVE_OWNER_RUN_READY` — the blind owner-operated Kdenlive final
technical stratum is fully prepared and frozen. The owner may start the 10
pairs at any time. **No final Kdenlive project has been scored, and no
final performance result of any system exists.**

**AUTOMATED FINAL RESULTS REMAIN SEALED UNTIL OWNER-OPERATED KDENLIVE
STRATUM IS COMPLETE.** No RhythmAlign, Panako, GCC-PHAT, or NCC execution
was started or surfaced in this preparation, and none may run before all
10 owner-saved Kdenlive projects exist.

## Frozen authority

- `docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md`
  (FROZEN before final data collection), items 12 and 17: Kdenlive 26.08
  is the essential owner-operated final technical stratum; exactly 10
  technical pairs; resulting placement scored from the saved Kdenlive
  project XML, never simulated.
- Protocol item 8 (trim rule): every system consumes the identical trimmed
  WAV bytes — Kdenlive included.
- Frozen artifacts verified at preparation time (canonical hashes
  recomputed and matched):
  - `final_acquisition_manifest.json` — canonical `manifest_hash`
    `7e1c1d54e3c50576d68aa8b8c983c1ee7fb921d4ad2486c48b638ad3790b906a`
  - `results/final_acquisition_qc.json` — canonical `qc_freeze_sha256`
    `962455b6b2962b06b5e9b7019bef71f4be686e17abb7162932c347c8b261ae9d`
    (verdict `FINAL_QC_PASS`, 26/26 GT_VALID)
  - `final_source_freeze.json` — canonical `freeze_sha256`
    `0a81c47339a7d9d565c26a46866065fa6b5ce41aa8deeca95874e2d6e2ecb029`
- Local audio verified byte-identical before pack build: 26/26 trimmed
  WAVs match the QC freeze `trimmed_input_sha256`; 10/10 `REF-Sxx.wav`
  match the manifest references.

## Whether exact pair IDs were previously frozen

**NO.** A full sweep of all committed history (`git grep` over every
revision for `kdenlive_pair`, `pair01`, `pair02`, `technical pair`) found
only the frozen checklist count "10 Kdenlive technical pairs"; the earlier
study design (HUMAN_LIGHT_STUDY_DESIGN.md, Layer B) says only "8–10
benchmark pairs spanning strata". No document ever fixed which take IDs.

## Performance-blind pair selection rule

Because the exact IDs were never frozen, the gap was resolved by
**KDENLIVE-SELECT-V1**, declared in
`experiments/applied_system/final_kdenlive_prep.py` and executed **after
final acquisition and final QC, but before any final comparator result
exists** (no RhythmAlign/Panako/GCC-PHAT/NCC/Kdenlive outcome existed or
could exist at freeze time). The rule is fully deterministic and
metadata-only:

- **A1 — universe:** the 24 primary takes of the frozen acquisition
  manifest. Strict repeats are reliability takes reported separately and
  are never benchmark pairs.
- **A2 — condition quotas:** proportional largest-remainder allocation of
  the 10 pairs over the frozen condition counts, ties broken by condition
  name ascending. Computed quotas: ORDINARY 4, INTERFERENCE 2, LOW_LEVEL 1,
  TAP_DOMINANT 1, PARTIAL 1, DEVICE_VARIATION 1.
- **A3 — within-condition order:** ascending take ID, first quota taken.
- **Blindness enforcement (structural, not procedural):** the selection
  function receives takes only through `selection_rows()`, which projects
  each manifest record down to `SELECT_ALLOWED_KEYS` = {take, source_slot,
  condition, session, room, recording_device, playback_device, primary}.
  GT offsets, marker data, audio content, trimmed hashes, wrong-reference
  data, and every comparator outcome are physically absent from the
  selection input. A regression test re-runs the selection with all other
  manifest fields replaced by garbage and asserts an identical result.

This honors the original design intent ("benchmark pairs spanning strata")
by guaranteeing every benchmark condition is represented, proportionally
to the frozen acquisition design, rather than 10 ordinary takes.

## Selected 10 pairs

Pair freeze: `experiments/applied_system/final_pack/kdenlive/kdenlive_pair_freeze.json`
(canonical `pair_freeze_sha256`
`2edd734b53e06d47e4774605d398b0f02521437d668f151fcabd69f0cccdbc0f`,
write-once; the file refuses rewrite on content drift).

| Pair | Take | Condition | Slot | Session | Room | Device | Reference |
|---|---|---|---|---|---|---|---|
| pair01 | final01 | ORDINARY | S01 | SESSION_1 | ROOM_A | D1 | REF-S01 |
| pair02 | final02 | ORDINARY | S02 | SESSION_1 | ROOM_A | D1 | REF-S02 |
| pair03 | final03 | ORDINARY | S03 | SESSION_1 | ROOM_A | D1 | REF-S03 |
| pair04 | final04 | ORDINARY | S04 | SESSION_1 | ROOM_A | D1 | REF-S04 |
| pair05 | final11 | LOW_LEVEL | S01 | SESSION_2 | ROOM_A | D1 | REF-S01 |
| pair06 | final12 | TAP_DOMINANT | S02 | SESSION_2 | ROOM_A | D1 | REF-S02 |
| pair07 | final17 | INTERFERENCE | S07 | SESSION_3 | ROOM_B | D2 | REF-S07 |
| pair08 | final18 | INTERFERENCE | S08 | SESSION_3 | ROOM_B | D2 | REF-S08 |
| pair09 | final21 | PARTIAL | S01 | SESSION_2 | ROOM_A | D1 | REF-S01 |
| pair10 | final23 | DEVICE_VARIATION | S09 | SESSION_3 | ROOM_B | D2 | REF-S09 |

Each pair is the take's frozen trimmed WAV plus the correct clean full
reference (`REF-<slot>`); hashes for both are embedded in the freeze.
The freeze was created and hashed before any Kdenlive project exists and
cannot change from later results.

## Kdenlive version

- Pinned series (protocol item 12): **26.08**.
- Installed for the owner on this machine: **Kdenlive 26.08.1** (first
  maintenance release of the 26.08 series), via winget
  `KDE.Kdenlive@26.08.1`, installer
  `https://download.kde.org/stable/kdenlive/26.08/windows/kdenlive-26.08.1.exe`
  (installer hash verified by winget before install).
- Executable: `C:\Users\Daozh\AppData\Local\Programs\Kdenlive\bin\kdenlive.exe`,
  `kdenlive --version` → `kdenlive 26.08.1`, exe SHA-256
  `4ba2e9c5dc181e429bde94f7206c02f536e4ef633a9145625d4ec9c180350dee`.
- Recorded in `kdenlive/kdenlive_environment.json` and re-verifiable with
  `python -m experiments.applied_system.final_kdenlive_prep --verify`.

## Input representation

Per protocol item 8 the Kdenlive stratum consumes the identical frozen
trimmed WAV bytes the automated systems receive:

- recording input = `local/final_qc_work/trimmed/<take>.wav` (hash in the
  QC freeze `trimmed_input_sha256`);
- reference input = `local/references/REF-<slot>.wav` (full decoded clean
  source, hash in the acquisition manifest).

No marker audio exists in the trimmed files (frozen trim with 50 ms
margins, leakage-checked); no wrong-reference audio is offered in this
stratum; the owner receives hash-verified copies named only
`recording.wav` / `reference.wav` (pack manifest:
`kdenlive/kdenlive_owner_pack_manifest.json`, committed, hashes only —
the media itself is gitignored).

## Blindness controls

- The owner-facing pack uses neutral names (`pair01`…`pair10`,
  `recording.wav`, `reference.wav`, `pairNN.kdenlive`); no S-slot, take,
  condition, GT, marker, or wrong-reference token appears in any owner
  path, filename, instruction text, or timer output (enforced by test).
- The pair freeze, pack manifest, and environment record contain placement
  contract and hashes only — no GT offsets, no marker positions, no
  comparator outputs. (Wrong-reference slots deliberately are NOT carried
  into this stratum at all.)
- The timing helper knows no GT and cannot display one.
- The saved-project contract makes the machine-readable project the only
  result artifact; the owner never reports or inspects an offset.
- Sealing rule (also embedded in the pair freeze): automated final results
  stay sealed until all 10 owner Kdenlive projects are saved.

## Operator timing method

`kdenlive/owner_timer.py` (`KDENLIVE-TIMER-V1`), run by the owner per pair:

- start timestamp (UTC) when the owner launches the command for that pair;
- end timestamp when the owner returns and presses Enter after saving the
  project;
- elapsed seconds, the observed native Kdenlive behavior (`ALIGNED` /
  `NO_MATCH_REPORTED` / `ERROR_DIALOG` / `OTHER` + note), appended as one
  JSON line to `owner_pack/timing_log.jsonl`;
- the timer warns (without blocking) if `pairNN/pairNN.kdenlive` is
  missing; duplicate pairs are refused;
- measures owner operation only — agent preparation time is never inside a
  timed window, and breaks between pairs are excluded by construction
  (the timer runs only within one pair).

## Saved project as the authoritative result

The owner saves each pair's Kdenlive project as `pairNN.kdenlive` inside
the pair's folder (deterministic filenames pair01…pair10, fixed in the
freeze before any project exists). No manual offset reporting exists. The
placement will later be read from the project XML / MLT structure.

## XML extraction design

`experiments/applied_system/kdenlive_project_xml.py` (committed; tested
only on synthetic fixtures — no final project has been touched):

- parses the MLT document: profile/frame rate, producers and resources,
  `kdenlive:docproperties.*`, playlists with blank/entry arithmetic, and
  the main tractor's track list;
- timeline placements = entries on tractor-listed playlists only (the
  project bin is itself a playlist and is excluded), each with absolute
  start/end frames;
- per-project summary for later scoring: recording/reference placements,
  `clip_offset_frames` (pure placement difference — no GT comparison
  exists in this module), and representable native-failure states
  (`MISSING_EXPECTED_CLIP`, `NOT_PLACED_ON_TIMELINE`, `INCOMPLETE`);
- regression tests cover position arithmetic, timecode-valued entries,
  bin-only clips, and missing-clip states.

## Owner workload

10 pairs × ~3–5 min ≈ 30–50 minutes total, following the one-page
instructions. The owner needs only: open folder → Kdenlive native
alignment → save project → press Enter.

## Readiness

- `KDENLIVE_ENV_READY`: Kdenlive 26.08.1 installed and hash-recorded.
- Pair freeze sealed before any result exists: `2edd734b53e06d47…`.
- Blind pack built and hash-verified (10 pairs).
- Owner instructions published (Chinese, one page).
- XML parser ready on synthetic fixtures; final scoring machinery is
  deliberately NOT run.

**Do not run any automated comparator until all 10 `pairNN.kdenlive`
projects and the timing log exist.**
