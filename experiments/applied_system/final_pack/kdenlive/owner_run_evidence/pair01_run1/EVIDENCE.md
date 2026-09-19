# pair01 run 1 — preserved failure evidence (VOID run)

This directory is a **verbatim, byte-identical archive** of the pair01
owner run that was performed under owner procedure **v1** (both clips
placed at timeline 00:00). The run is void for scoring under
`kdenlive_run_policy.json`; the pair is redone as run `pair01r2` under
procedure `KDENLIVE-PLACEMENT-V2`.

The originals stay untouched in their original (gitignored) locations.
Nothing in `owner_pack/pair01/` was modified, moved, or re-saved after
the run. See `docs/research/applied_system/KDENLIVE_PAIR01_AUDIT.md`
for the full audit.

## Files

| File | Original location (gitignored) | SHA-256 (identical) | Bytes |
|---|---|---|---|
| `pair01.kdenlive` | `owner_pack/pair01/pair01.kdenlive` | `b2b3fb5aa8dea8e7f24f4628bd87d34a28f7ffd3ca846bc68bf3322bd454af8e` | 65361 |
| `pair01_run1.timing_log.jsonl` | `owner_pack/timing_log.jsonl` | `0d712bc35cdecaaf305c3a20e47b8b2cdbc36c323bfd58247f0d0aa636f8c4ee` | 227 |

The timing log copy contains exactly the one record that existed when the
run was voided:

```json
{"elapsed_seconds": 231.171, "end_utc": "2026-09-19T20:59:23Z", "notes": "Cannot move clip to frame -17472", "observation": "OTHER", "pair": "pair01", "schema_version": "KDENLIVE-TIMER-V1", "start_utc": "2026-09-19T20:55:32Z"}
```

## Chain of custody

- Archived (copied, never moved) on 2026-09-20 during the pair01 audit,
  before any comparator was run and before any automated result was
  computed or unsealed.
- The saved project shows both clips still at frame 0 with the move
  refused: profile HD 1080p 60 fps, `playlist0` entry at position 0
  (reference.wav, 150.286 s), `playlist2` entry at position 0
  (recording.wav, 65.413 s).
- Scoring rule: this run is **never scored**. pair01 is scored from
  `owner_pack/pair01r2/pair01r2.kdenlive` only.
