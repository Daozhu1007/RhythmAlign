# RA-1.2A / RA-1.2B — Low-SNR Alignment Spike and Engine v2 (engineering experiments)

Isolated experiment code for the low-SNR alignment investigation documented in
`docs/RA-1.2A-LOW-SNR-ALIGNMENT.md` and the Alignment Engine v2 evidence gate
documented in `docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md`. Nothing here is imported
by production code (`alignment_engine_v2.py` at the repository root is the
Engine v2 module; it is not on the default GUI path) and no production
behavior is changed by this directory.

## Contents

| file | purpose |
|---|---|
| `harness.py` | Method library: production hybrid/onset/chroma wrappers, PCEN-delta, PCEN+HPSS, log-mel flux, candidate extraction, peak metrics |
| `run_experiment.py` | Run all methods on a real (video, music) pair, prints markdown table + JSON |
| `synthetic_eval.py` | Expected-behavior synthetic regression suite: Engine v2 outcomes gate the exit code, legacy-method rows are informational baseline observations (`--nulls N` runs no-signal null realizations) |
| `calibrate_nulls.py` | Expanded synthetic no-signal null calibration: per-family Z/margin distributions + joint family-coincidence risk + engine false-accept check |
| `real_corpus_eval.py` | Run production v1 and Engine v2 over the local real corpus (positives + mismatch negatives); requires `local_corpus.json` |
| `semi_synthetic.py` | RA-1.2C generator library: exact-GT real-noise positives (background + inserted track + documented degradation), tiled ambiguity cases, outcome classification, split/leakage audit |
| `semi_synthetic_plan.json` | Path-free corpus plan: calibration/holdout split (10+10 projects), cases, seeds, hard-negative selection |
| `semi_synthetic_eval.py` | RA-1.2C runner: `build-sources` (id→path mapping, gitignored `local_sources.json`), `select-hard-negatives` (feature-similarity search), `run --split calibration\|holdout` |
| `soak_test.py` | RA-1.2C repeated-invocation harness: `synthetic` / `real-file` / `benchmark-repro` modes, measures RSS/handles/temp leaks per call |
| `memory_scaling.py` | RA-1.2C long-duration memory/runtime scaling measurement (deterministic synthetic fixtures) |
| `local_corpus.example.json` | Schema example for the local corpus manifest |
| `local_corpus.json` | YOUR local manifest with absolute media paths — gitignored, never commit |
| `local_sources.json` | YOUR id→path mapping for the semi-synthetic corpus — gitignored, never commit (regenerate with `semi_synthetic_eval.py build-sources`) |
| `pcen_sweep.py` | PCEN hyper-parameter sweep across analysis rate / band-limit / mels / delta polarity |
| `failure_analysis.py` | Deep dive into the real hybrid false peak (top peaks, per-window votes, stereo scan, repeat-structure test) |
| `results/*.json` | Committed evidence from the runs quoted in the reports |

## Usage

```bash
# full method comparison on the documented failing sample
python experiments/low_snr_alignment/run_experiment.py --json experiments/low_snr_alignment/results/run_final.json

# expected-behavior synthetic suite (engine outcome gates the exit code)
python experiments/low_snr_alignment/synthetic_eval.py --json experiments/low_snr_alignment/results/synthetic_run_ra12b.json

# expanded null calibration (N=30 no-signal realizations)
python experiments/low_snr_alignment/calibrate_nulls.py --n 30 --json experiments/low_snr_alignment/results/null_calibration_n30.json

# real-corpus benchmark (needs your local_corpus.json)
python experiments/low_snr_alignment/real_corpus_eval.py --json experiments/low_snr_alignment/results/real_corpus.json
python experiments/low_snr_alignment/real_corpus_eval.py --only negative --json experiments/low_snr_alignment/results/real_corpus_mismatch.json

# RA-1.2C: semi-synthetic calibration hardening (needs local_corpus.json)
python experiments/low_snr_alignment/semi_synthetic_eval.py build-sources
python experiments/low_snr_alignment/semi_synthetic_eval.py select-hard-negatives
python experiments/low_snr_alignment/semi_synthetic_eval.py run --split calibration
python experiments/low_snr_alignment/semi_synthetic_eval.py run --split holdout

# RA-1.2C: repeated-invocation soak + memory scaling
python experiments/low_snr_alignment/soak_test.py synthetic --n 60
python experiments/low_snr_alignment/soak_test.py real-file --n 25
python experiments/low_snr_alignment/soak_test.py benchmark-repro --n 35
python experiments/low_snr_alignment/memory_scaling.py

# null distribution (no shared signal -> every method must lose confidence)
python experiments/low_snr_alignment/synthetic_eval.py --nulls 5

# PCEN configuration sweep
python experiments/low_snr_alignment/pcen_sweep.py

# failure-mode deep dive on the real pair
python experiments/low_snr_alignment/failure_analysis.py
```

`run_experiment.py`, `pcen_sweep.py` and `failure_analysis.py` default to the
real failing sample's local media paths (see the gitignored
`local_corpus.json` for the recording/track pair; override with
`--video/--music`). No media is committed here; `failure_analysis.py` caches
extracted audio in `results/rep_y_*.npy` (git-ignored location:
repository-root `results/`).

## Corpus manifest

`local_corpus.json` (gitignored) declares real positive pairs and mismatched
negatives with case ids that are safe to commit; see
`local_corpus.example.json` for the schema. Mismatch negatives pair a real
handcam video with a track confirmed to be a different song (different
folder, unrelated title, no filename correspondence) and are expected
ABSTAIN cases.

## Offset sign convention

Identical to `auto_sync.mix_and_export`: positive offset delays the music
(`adelay`), negative offset trims the music head (`atrim`). At video time `t`
the music plays at music time `t - offset`.
