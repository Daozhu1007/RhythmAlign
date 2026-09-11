# RA-1.2A — Low-SNR Alignment Spike (engineering experiments)

Isolated experiment code for the low-SNR alignment investigation documented in
`docs/RA-1.2A-LOW-SNR-ALIGNMENT.md`. Nothing here is imported by production
code and no production behavior is changed by this directory.

## Contents

| file | purpose |
|---|---|
| `harness.py` | Method library: production hybrid/onset/chroma wrappers, PCEN-delta, PCEN+HPSS, log-mel flux, candidate extraction, peak metrics |
| `run_experiment.py` | Run all methods on a real (video, music) pair, prints markdown table + JSON |
| `synthetic_eval.py` | Self-contained synthetic regression suite with known ground-truth offsets (`--nulls N` runs no-signal null realizations) |
| `pcen_sweep.py` | PCEN hyper-parameter sweep across analysis rate / band-limit / mels / delta polarity |
| `failure_analysis.py` | Deep dive into the real hybrid false peak (top peaks, per-window votes, stereo scan, repeat-structure test) |
| `results/*.json` | Committed evidence from the runs quoted in the report |

## Usage

```bash
# full method comparison on the documented failing sample
python experiments/low_snr_alignment/run_experiment.py --json experiments/low_snr_alignment/results/run_final.json

# synthetic regression + abstention checks
python experiments/low_snr_alignment/synthetic_eval.py --json experiments/low_snr_alignment/results/synthetic_run.json

# null distribution (no shared signal -> every method must lose confidence)
python experiments/low_snr_alignment/synthetic_eval.py --nulls 5

# PCEN configuration sweep
python experiments/low_snr_alignment/pcen_sweep.py

# failure-mode deep dive on the real pair
python experiments/low_snr_alignment/failure_analysis.py
```

Media paths default to the real failing sample
(`D:\Daozh\Videos\舞萌手元\13.2\零对话\`); override with `--video/--music`.
No media is committed here; `failure_analysis.py` caches extracted audio in
`results/rep_y_*.npy` (git-ignored location: repository-root `results/`).

## Offset sign convention

Identical to `auto_sync.mix_and_export`: positive offset delays the music
(`adelay`), negative offset trims the music head (`atrim`). At video time `t`
the music plays at music time `t - offset`.
