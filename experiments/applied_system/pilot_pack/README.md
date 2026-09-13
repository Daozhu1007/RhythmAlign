# Pilot Pack — status and conventions

KIT_READY / NOT PAPER EVIDENCE / NO RECORDING HAS BEGUN.

This folder is the owner-facing hand-off point for the fresh acoustic
pilot (`docs/research/applied_system/FRESH_PILOT_PLAN.md`). Everything the
owner physically touches lives here; every analysis step stays agent-side.
Kit-build record: `docs/research/applied_system/PILOT_KIT_BUILD.md`.

## Contents

- `take_plan.json` — machine-readable take plan: the 12 frozen slots
  (device, playback source, buffer, condition), ingest conventions, and
  the device/playback labels used in the owner instructions. Status is
  `KIT_READY`: the three playback buffers are rendered, hashed, and
  digitally validated; slots are unchanged from plan section 5.
- `buffers/BUF-A.wav`, `buffers/BUF-B1.wav`, `buffers/BUF-BMID.wav` —
  the rendered playback buffers (63.5 s each, chirp | guard | 60 s music
  payload | guard | chirp @ 48 kHz PCM_16 mono). Gitignored generated
  media; regenerable from the frozen selection via
  `python -m experiments.applied_system.pilot_kit_build`. Hashes live in
  `kit_manifest.json` and `take_plan.json`.
- `INTERFERENCE.mp3` — local copy of the owner-library interference
  source for take 8 (gitignored; hash + source path recorded in
  `kit_manifest.json` / `take_plan.json`). Never a reference in any
  pairing.
- `source_selection.json` — the FROZEN source-selection record: scan
  aggregates, historical exclusions with provenance, the clean-pool
  structural table, and the pre-declared rules that picked song A
  (ordinary), song B (structurally difficult), and the interference
  track. Selection is frozen before any benchmark observation
  (plan section 9 anti-cherry-picking rule).
- `kit_manifest.json` — the kit-build record: buffer hashes, exact
  layouts, marker/payload positions, payload provenance, and the
  deterministic digital self-check results (GT/QC/trim/leakage).
- `incoming/` — the ONLY folder the owner writes to. Owner drops raw
  recordings here as `takeNN.<any extension>` (retakes: `take01_b.m4a` —
  duplicates are kept, both analyzed, agent classifies). Gitignored;
  contents are personal data and never committed.
- `local/` — gitignored agent scratch: full media inventory (personal
  paths, never committed), decoded full-song references (REF-A/REF-B,
  the comparator reference pool), and self-check captures.
- `README.md` — this file (agent-facing).

## Ingest contract (for the future `pilot_harness.py`)

1. Read `incoming/takeNN.*`, match `NN` to `take_plan.json` slots.
2. Decode at native rate via ffmpeg (AAC/M4A expected from phones); never
   resample on ingest (drift must survive).
3. Hash every incoming file; record decode provenance per take.
4. Per-take GT/QC/trim analysis against the buffer layouts in
   `kit_manifest.json`; BUF-BMID takes report reference GT as
   `payload GT − 90.0 s` (the reference pool is the FULL decoded songs,
   `local/references/`).
5. Then the frozen manifest and the single-pass comparator sweep
   (RhythmAlign, GCC-PHAT, NCC, Panako via the WSL wrapper —
   `runners/panako_runner.py`).
6. The owner never renames (beyond the take number), trims, converts, or
   analyzes anything.

## What is deliberately NOT here yet

- `pilot_harness.py` — the next research round implements ingest +
  analysis + freeze-rule computation + comparator sweep.
- Any recording. Do not start the pilot before the owner begins; the
  comparator stack is frozen (Panako contract:
  `docs/research/applied_system/PANAKO_INTEGRATION.md`).
