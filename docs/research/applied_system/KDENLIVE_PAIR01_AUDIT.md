# Audit: pair01 negative-frame alignment failure (Kdenlive 26.08.1)

Status: **audit complete, correction applied (procedure v2)**
Date: 2026-09-20 (audit started after the owner stopped the run)
Scope: pair01 failure audit only. No comparator was run, no automated
result was computed or unsealed, no frozen pair identity / input / scoring
rule / comparator semantics changed.

## VERDICT

**KDENLIVE_OWNER_PROCEDURE_BUG** (option B).

The 00:00 initialization in owner procedure v1 created an artificial
left-boundary constraint. Kdenlive's native audio alignment *analyzed*
the pair and requested a move to a negative frame; the request was
refused because the timeline has no space left of frame 0. The same
request, issued from a placement with left headroom, is executable.
Kdenlive's failure to realize the placement is therefore caused by our
procedure's placement choice, not by a defect in Kdenlive's alignment
analysis.

A genuine Kdenlive display defect was found during the audit (the error
message shows a doubled frame number — see "Message number" below), but
it is cosmetic and did not cause the failure.

## What happened (recorded evidence, untouched)

Owner pack built 2026-09-19T19:02:56Z. Owner run recorded by
`owner_timer.py` (KDENLIVE-TIMER-V1):

```json
{"elapsed_seconds": 231.171, "end_utc": "2026-09-19T20:59:23Z", "notes": "Cannot move clip to frame -17472", "observation": "OTHER", "pair": "pair01", "schema_version": "KDENLIVE-TIMER-V1", "start_utc": "2026-09-19T20:55:32Z"}
```

No manual rescue was attempted; the owner saved the project as observed
(`owner_pack/pair01/pair01.kdenlive`) and stopped. The saved project
shows: profile **HD 1080p 60 fps**; `recording.wav` (65.413 s) placed at
frame 0 on one audio track, `reference.wav` (150.286 s) placed at frame
0 on the other; neither clip moved.

## Root cause

### Native chain (Kdenlive 26.08.1, tag `v26.08.1`)

1. `TimelineController::setAudioRef` (`src/timeline2/view/`
   `timelinecontroller.cpp:3869`) stores the recording clip as reference
   and builds its loudness envelope (`AudioEnvelope` +
   `AudioCorrelation`).
2. `TimelineController::alignAudio` (`timelinecontroller.cpp:3901`)
   adds the selected clip's envelope (reference.wav) to the correlator.
3. When correlation finishes, the `gotAudioAlignData` handler computes
   `pos = getClipPosition(m_audioRef) + shift - getClipIn(m_audioRef)`
   (`timelinecontroller.cpp:3887`) and calls
   `TimelineModel::requestClipMove(cid, track, pos, ...)`.
4. `shift` is the cross-correlation argmax of the two per-frame
   envelopes (`AudioCorrelation::getShift`, `src/lib/audio/`
   `audioCorrelation.cpp`; FFT path `fftCorrelation.cpp` — including the
   one-frame output insert in `convolve`, which keeps the index
   arithmetic correct). It is the frame offset at which the aligned
   clip's audio matches the reference clip's audio. In this project the
   alignment math is audio-only and position-independent: the requested
   `pos` is relative to where the clips currently sit.

### The pair01 numbers

With both clips at position 0 and in-point 0, `pos = shift`. The refusal
message prints `pos + shift` (`timelinecontroller.cpp:3891`) — the shift
is counted twice. So the displayed frame **−17472** means the actually
requested target was **pos = −8736 frames = −145.6 s at 60 fps**.

−8736 is inside the geometrically possible range for these two clips
(envelope lengths 9017 and 3925 frames → any alignment target must lie
in [−9016, +3924] frames). The request was therefore a *legal alignment
target* — an alignment of this pair structurally requires moving
reference.wav to the left of the recording whenever the room recording
starts part-way into the reference playback, i.e. a negative timeline
position.

### Why it failed

`requestClipMove` → group move validates each clip's target position
against track availability (`timelinemodel.cpp`, group-move reinsert,
`isAvailableWithExceptions(newIn, ...)`). A clip cannot occupy a
negative interval: the timeline has no region left of frame 0. With both
clips at 00:00 there is no left room, so any negative target is refused
unconditionally and the handler emits
`"Cannot move clip to frame %1."`.

Procedure v1 instructed exactly this placement (「两条都从最左边 00:00
位置开始放」). The 00:00 initialization is what converted the (valid)
negative alignment target into a hard failure — an artificial
left-boundary constraint of our own making.

### Message number (Kdenlive display defect, cosmetic)

The dialog printed `-17472` instead of the requested `-8736` because the
handler formats `(pos + shift)` rather than `pos`
(`timelinecontroller.cpp:3891`). This is a Kdenlive UI bug (the same
handler also prints the position it failed to reach incorrectly for any
nonzero reference in-point). It does not affect placements and does not
change the verdict; owner procedure v2 only asks the owner to record any
such message verbatim.

### Honest uncertainty (does not affect the verdict)

Whether `shift = −8736` is the *true* offset of pair01 or a false peak
of Kdenlive's loudness-envelope correlation cannot be determined without
computing alignments, which is sealed until the owner run completes —
so it is deliberately left undetermined. This is irrelevant to the
verdict: a correct native analysis would also have requested a negative
move for this pair class and been refused identically at 00:00. After
the correction, whatever Kdenlive's native analysis produces — right or
wrong — becomes a measurable placement, which is exactly what the
benchmark is designed to record.

## Why the correction is outcome-independent

The fix is a neutral timeline-placement rule; its value is derived only
from frozen input sizes, not from any observed outcome:

- A Kdenlive envelope-correlation move is bounded by the clip lengths
  themselves: any requested target lies in
  `[−L_child, +L_reference]` frames. This is arithmetic on the inputs,
  not on results.
- Longest frozen pack input = 150.286 s (from
  `kdenlive_owner_pack_manifest.json` byte sizes; frozen format
  48 kHz/16-bit/mono).
- Rule (**KDENLIVE-PLACEMENT-V2**): place both clips at a common left
  headroom **H = smallest whole minute ≥ the longest frozen input** →
  H = 180 s = 00:03:00, identical for all ten pairs.
- Sufficiency proof: for every frozen pair and every possible
  correlation output, `H + shift ≥ 180 s − 150.286 s > 0`, so the move
  is executable; rightward moves always are. The same H would have been
  chosen had the failure occurred on any other pair, or on none.

Relative placements — the only thing scored — are unchanged: both clips
shift by the same H, and `clip_offset_frames` is a pure difference.

## ORIGINAL PAIR01 EVIDENCE PRESERVED

YES.

- `owner_pack/pair01/` (gitignored) was not modified, moved, or re-saved:
  `pair01.kdenlive` (SHA-256 `b2b3fb5a…4af8e`, 65361 bytes) and
  `owner_pack/timing_log.jsonl` (SHA-256 `0d712bc3…c4ee`, 227 bytes)
  remain exactly as the owner left them.
- Committed verbatim copies (byte-identical, hashes recorded):
  `final_pack/kdenlive/owner_run_evidence/pair01_run1/` with an
  `EVIDENCE.md` chain-of-custody note.
- The run is voided for scoring via `kdenlive_run_policy.json`, never
  deleted. pair01 was not re-interpreted in light of any automated
  outcome (none exists; comparators remain sealed).

## AUTOMATED RESULTS STILL SEALED

YES. No comparator (RhythmAlign, GCC-PHAT, NCC, Panako) was run; no
alignment was computed by the audit; no scoring happened. The audit used
only: saved project XML, WAV headers (durations), pack manifest byte
sizes, timing log, and Kdenlive 26.08.1 source inspection.

## CORRECTED OWNER PROCEDURE (v2)

`docs/research/applied_system/OWNER_KDENLIVE_FINAL_INSTRUCTIONS.md`
version **V2** (`KDENLIVE-PLACEMENT-V2`), applied uniformly to all ten
pairs:

1. New blank project; import both WAVs into the Project Bin (unchanged).
2. Move the timeline playhead to `00:03:00:00` (type it into the
   timecode box and press Enter).
3. Drag `recording.wav` to audio track **A1** and `reference.wav` to
   audio track **A2**, each starting at the playhead (clips snap to it),
   i.e. both start at 00:03:00. Nothing else about placement changes.
4. `recording.wav` → Set Audio Reference; `reference.wav` → Align Audio
   to Reference (unchanged native steps).
5. Any error message is recorded verbatim (unchanged rule); v2 notes
   that Kdenlive may display a doubled frame number in this message —
   record it as shown, never reinterpret it.

Versioning: instructions doc carries a V2 header and change record; the
rule is implemented as `KDENLIVE-PLACEMENT-V2` in
`experiments/applied_system/final_kdenlive_prep.py`
(`placement_headroom_seconds`, verified by regression tests, recomputed
and printed by `--verify`).

## PAIR01 RERUN POLICY

- Original run (`pair01`) is **void for scoring** and preserved as
  evidence (`kdenlive_run_policy.json`: `void_runs: ["pair01"]`,
  reason `PROCEDURE_V1_TIMELINE_ZERO_LEFT_BOUNDARY`).
- pair01 is redone exactly once as run **`pair01r2`** under procedure
  v2, in a fresh folder `owner_pack/pair01r2/` whose media are
  hash-verified copies of the frozen pair01 inputs (built by
  `final_kdenlive_prep.py --build-rerun pair01r2`; recorded in
  `kdenlive_owner_pack_rerun_manifest.json`; the original pack manifest
  is untouched). The owner times it with `python owner_timer.py
  pair01r2` and saves `pair01r2.kdenlive` in that folder.
- Scoring: pair01 is scored from `pair01r2.kdenlive` only. The original
  project is excluded from scoring permanently, retained as evidence,
  and was never re-interpreted against any automated outcome.
- Frozen pair identity, inputs, GT, and scoring semantics are unchanged:
  same take, same two files, same offset definition, same scoring.
- Frozen artifacts untouched: `kdenlive_pair_freeze.json`
  (`pair_freeze_sha256 2edd734b…`), `kdenlive_owner_pack_manifest.json`,
  `kdenlive_environment.json`, all pair inputs.

## PAIR02–PAIR10 MAY BEGIN

YES — under procedure v2 (00:03:00 placement). The corrected procedure
is uniform for all pairs; pair01r2 completes the set. The comparator
seal stays in force until all ten scoring runs exist.

## Regression tests

`tests/test_kdenlive_final_prep.py` (extended; synthetic fixtures only,
no media, no comparators):

- headroom rule: value, whole-minute ceiling, ≥ longest input for the
  committed pack manifest; sufficiency bound
  (`H ≥ max input duration ⇒ every possible move target ≥ 0`);
- run-id policy: canonical/rerun id parsing, rerun-manifest + policy
  verification, evidence-dir integrity (hash-identical archive);
- placement regression: the instructions prescribe the 00:03:00
  headroom placement on A1/A2 (the former test asserting 00:00 was the
  encoded v1 bug and was corrected), and stay GT-clean;
- offset invariance: synthetic projects with both clips shifted by a
  common headroom yield the identical `clip_offset_frames`.
