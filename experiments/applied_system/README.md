# Applied-System Benchmark Machinery — SHAKEDOWN_ONLY

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Research-only benchmark infrastructure for the human-light applied-system
study (`docs/research/applied_system/HUMAN_LIGHT_STUDY_DESIGN.md`, Layer A).
Everything here exists to answer one question: **can the proposed benchmark
machinery produce trustworthy, reproducible measurements?** Nothing in this
directory may be counted in the final paper benchmark, and nothing here may
alter frozen RhythmAlign v1.2.0 production behavior (production modules are
imported read-only).

## Layout

| Path | Purpose |
|---|---|
| `marker_protocol.py` | Deterministic playback-buffer generation (chirp → guard → payload → guard → chirp), marker detection independent of every system, two-marker GT derivation with QC rule, marker-free trimming, mechanical leakage check |
| `synth_payload.py` | Deterministic synthetic music-like payloads (two source-disjoint "songs", fixed seeds) — machinery fixtures, not a dataset |
| `manifest.py` | Machine-readable manifest schema, deterministic build, freeze + tamper verification |
| `scoring.py` | Deterministic scoring contract (CORRECT_ACCEPT / WRONG_ACCEPT / SAFE_ABSTAIN / GT_FAILED / RUNNER_ERROR) |
| `shakedown.py` | Orchestrator: prepare → run → score → reproduce |
| `acoustic_loop.py` | Optional owner-operated acoustic loop test (no participants) |
| `runners/` | Common record contract + frozen RhythmAlign v1.2.0, GCC-PHAT, NCC runners; Panako feasibility + integration plan |
| `tests/` | Research-only tests (also collected by the repository root pytest run) |
| `results/shakedown/` | Frozen manifest, raw records, scores, environment, reproduction check (JSON committed; all audio gitignored and deterministically regenerable) |

## Conventions

- **Offset sign convention** (identical to frozen production semantics,
  `alignment_engine_v2`): positive GT offset = the reference begins that
  many seconds into the benchmark input; negative = the capture starts
  |offset| seconds into the reference (first |offset| s of the reference
  trimmed). GT is always reported relative to the TRIMMED input.
- **Marker protocol**: 0.75 s linear chirp (1→9 kHz, 48 kHz), 1.0 s guards,
  50 ms trim margins. Both chirps are mandatory: exactly two accepted
  matched-filter candidates required; separation implies a clock-scale QC
  statistic (provisional shakedown tolerance ±500 ppm); mapping disagreement
  > 10 ms fails GT. Any failure classifies the case GT_FAILED — no manual
  rescue, no payload warping (RhythmAlign is a fixed-offset aligner; clock
  drift is scientifically relevant).
- **Leakage**: chirps and guards are removed before any system sees audio;
  every trimmed input is re-scanned mechanically (`marker_leakage_check`)
  and every runner records the SHA-256 of the exact files it consumed.
- **Comparator semantics preserved**: RhythmAlign ABSTAIN stays ABSTAIN
  (SELECTIVE_NO_MATCH); GCC-PHAT / NCC argmax are ALWAYS_OUTPUT with no
  invented thresholds; Panako would keep its native no-match (PENDING).
- **Scoring tolerance**: 100 ms primary (editorial-task criterion);
  50/150 ms sensitivities are derivable from per-case `abs_error_s`;
  nothing is tuned in this round.

## Running

```bash
# full shakedown (prepare, run, score, reproduce)
.venv/Scripts/python.exe -m experiments.applied_system.shakedown --stage all

# individual stages
.venv/Scripts/python.exe -m experiments.applied_system.shakedown --stage prepare

# optional owner acoustic loop (see OWNER_SHAKEDOWN_INSTRUCTIONS.md)
.venv/Scripts/python.exe -m experiments.applied_system.acoustic_loop \
    --capture results/shakedown/acoustic/take1.wav --label take1
```

The manifest is fully deterministic (no wall-clock fields): re-running
`prepare` from the same code and seeds reproduces the frozen manifest byte
for byte; a changed manifest hash is a determinism failure, not a new
manifest. The `reproduce` stage re-runs every runner from the same frozen
manifest and verifies records and scoring are identical beyond volatile
runtime fields.

## Status

Shakedown verdict and findings:
`docs/research/applied_system/BENCHMARK_SHAKEDOWN.md` — verdict
`SHAKEDOWN_PASS_WITH_FIXES` (Panako PENDING; all required machinery gates
passed).
