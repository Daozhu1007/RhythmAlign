# Pilot Pack — status and conventions

PILOT_PACK_PREPARED / NOT PAPER EVIDENCE / NO RECORDING HAS BEGUN.

This folder is the owner-facing hand-off point for the fresh acoustic
pilot (`docs/research/applied_system/FRESH_PILOT_PLAN.md`). Everything the
owner physically touches lives here; every analysis step stays agent-side.

## Contents

- `take_plan.json` — machine-readable take plan: the 12 frozen slots
  (device, playback source, buffer, condition), ingest conventions, and
  the device/playback labels used in the owner instructions. Status is
  `AWAITING_KIT_BUILD`: the three playback buffers cannot be rendered
  until the owner hands over the two clean songs and one interference
  track (plan section 12 step 1, next agent round). Slots themselves are
  frozen and will not change.
- `incoming/` — the ONLY folder the owner writes to. Owner drops raw
  recordings here as `takeNN.<any extension>` (retakes: `take01_b.m4a` —
  duplicates are kept, both analyzed, agent classifies). Gitignored;
  contents are personal data and never committed.
- `README.md` — this file (agent-facing).

## Ingest contract (for the future `pilot_harness.py`)

1. Read `incoming/takeNN.*`, match `NN` to `take_plan.json` slots.
2. Decode at native rate via ffmpeg (AAC/M4A expected from phones); never
   resample on ingest (drift must survive).
3. Hash every incoming file; record decode provenance per take.
4. Per-take GT/QC/trim analysis, then the frozen manifest and the
   single-pass comparator sweep (RhythmAlign, GCC-PHAT, NCC, Panako via
   the WSL wrapper — `runners/panako_runner.py`).
5. The owner never renames (beyond the take number), trims, converts, or
   analyzes anything.

Path note: the plan's section 12 sketched `results/pilot/incoming/` as the
drop folder; the pack-local `pilot_pack/incoming/` here is the same
convention moved into the owner's hand-off folder. `pilot_harness.py`
ingests from this folder; analysis outputs still go to `results/pilot/`.

## What is deliberately NOT here yet

- Playback buffer files (BUF-A / BUF-B1 / BUF-BMID) — rendered by the
  agent's kit build from the owner's songs; hashes land in
  `take_plan.json` when they exist.
- `pilot_harness.py` — the next research round implements ingest +
  analysis + freeze-rule computation + comparator sweep.
- Any recording. Do not start the pilot until the kit is built and the
  comparator stack is frozen (Panako contract: DONE, see
  `docs/research/applied_system/PANAKO_INTEGRATION.md`).
