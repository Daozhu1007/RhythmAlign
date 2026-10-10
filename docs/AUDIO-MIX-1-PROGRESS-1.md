# AUDIO-MIX-1 + PROGRESS-1 review

Date: 2026-10-10 (Asia/Shanghai). Verdict: **READY_FOR_OWNER_AUDIO_REVIEW**.
Branch: `codex/ra-audio-progress-1`, isolated worktree
`D:\Code\RhythmAlign-audio-progress-1`. The fetched `origin/main` was exactly
`befa8379e14f150f801c74b7c7a9b470a8e707f4` (released v1.2.2).

## Confirmed causes and implementation

The released graph applies source `volume` filters, then uses `amix` with
implicit `normalize=1` and a two-second dropout transition. During overlap,
each source effectively receives half its configured gain. When the reference
ends, the original recording rises toward its full configured gain. For example,
Mobile 200% / 50% means approximately 1.0x recording / 0.25x reference during
overlap, then 2.0x recording after reference EOF. This is a reproducible gain
change, independent of subjective listening. The default behavior is documented
by [FFmpeg amix](https://ffmpeg.org/ffmpeg-filters.html#amix) and verified against
the actual bundled FFmpeg 7.1 executable's filter help.

Analysis ETA additionally probed both input durations, applied a realtime factor,
then counted down on a one-second UI timer. Export extrapolated wall-clock time
from media percentage. Neither describes the actual remaining computation or
MP4 finalization work. All these estimators, probes, formatting/parsing helpers
and countdown timer state have been removed.

Changed production files:

- `auto_sync.py`: fixed mixing, streaming peak scan, explicit audio duration,
  machine-readable FFmpeg progress, finalization boundary and process cleanup.
- `ui_main.py`: honest stages and terminal states, two-field progress signals,
  fresh progress on restart, disabled input/preset controls during work, clearer
  recording/music gain labels and an explanation of the gain baseline.
- `locales/en_US.json`, `locales/zh_CN.json`: matching stage, gain and progress text.
- `alignment_engine_v2.py`: **only** optional stage notifications in the file
  extraction/loading entry point. All 34 other function/class definitions are
  AST-identical to the released baseline. Features, thresholds, candidate
  ownership, evidence, decision logic and waveform verification are unchanged.

New regression files are `tests/test_audio_mix_progress.py` and
`tests/test_progress_ui.py`. Existing slider, worker, diagnostics and export
tests were adapted to the removed ETA contract. Both existing product-smoke
scripts now consume the two-field progress signal. Reproduction/measurement
tools are under `experiments/audio_progress/`; generated synthetic measurements
are in `experiments/audio_progress/results/synthetic_summary.json`.

## Mixing contract

Let O/M be decoded recording/reference audio after the usual FFmpeg channel
conversion, pO/pM be slider values divided by 100, and A be one fixed attenuation:

```text
Recording audio exists:  output(t) = A * [0.5*pO*O(t) + 0.5*pM*M_aligned(t)]
No recording audio:      output(t) = A * pM*M_aligned(t)
```

Percentages are **per-source gains relative to a fixed compatibility baseline**,
not a measured loudness percentage or normalized mix weight. In a two-track
mix, 100% means 0.5x and 200% means 1.0x before peak protection. A silent original
audio stream still counts as an existing track, as in the released behavior.
Without an original audio stream, music retains its legacy unity baseline.
These distinctions are stated in both languages in the gain tooltip; the
visible explanation also identifies existing music as part of the recording.

`amix` now explicitly uses `normalize=0`, **after halving both gains** for the
two-track case. Both inputs are padded with silence; the mix is trimmed to the
video duration. Original channel negotiation and the released reference stereo
conversion are retained, including mixed mono/stereo inputs. No input EOF or
offset changes the gains. Positive offsets delay the reference, negative
offsets trim its beginning, and manual adjustment still adds to the engine
offset. Fractional positive milliseconds are retained rather than truncated.

Before export, the exact aligned mix is streamed through a 192 kHz resampler
and `astats`, without writing a decoded temporary file. The measured maximum
sets `A = min(1, 10^((-2 - peak_dB)/20))`, with silence giving A=1. Thus high peaks
cause **one whole-export attenuation applied equally to both sources**. There
is no automatic upward gain, compressor, limiter, attack/release, look-ahead
delay or time-varying normalization. Missing/non-finite peak evidence or a scan
failure stops export safely. The -2 dB target leaves AAC encoding headroom.

This is an oversampled peak estimate, not a universal mathematical guarantee
about every decoder or intersample reconstruction. Post-AAC sample peaks and
two independent true-peak estimates were measured in validation. This approach
adds one audio decode/mix pass; it does not re-encode copied video. Short or
fully trimmed references produce silence through video EOF. Existing atomic
partial-file replacement, destination preservation on failure, hidden FFmpeg
console windows, video stream copy, AAC 320k, metadata stripping and faststart
remain in place. Exceptions after process launch now also reap FFmpeg before
removing the partial output.

## Quantitative synthetic results

Independent inputs: 48 kHz float PCM; 8 s recording at 440 Hz, amplitude 0.2;
2 s reference at 880 Hz, amplitude 0.3, delayed 2 s. Output is production AAC.
Source amplitudes are recovered by quadrature projection, not by inspecting
the filter string. Before/during/after windows are 0.5–1.5 / 2.5–3.5 / 6.5–7.5 s.

| Setting | Old original before / during / after | New original before / during / after | Old/new reference during overlap |
|---|---|---|---|
| Arcade 120 / 70 | 0.5998 / 0.5998 / 1.1998 | 0.5998 / 0.5998 / 0.5998 | 0.3499 / 0.3499 |
| Mobile 200 / 50 | 0.9999 / 0.9999 / 1.9997 | 0.9999 / 0.9999 / 0.9998 | 0.2498 / 0.2498 |
| Mobile candidate 200 / 35 | 0.9999 / 0.9999 / 1.9997 | 0.9999 / 0.9999 / 0.9998 | 0.1749 / 0.1749 |
| Mobile candidate 200 / 25 | 0.9999 / 0.9999 / 1.9997 | 0.9999 / 0.9999 / 0.9998 | 0.1249 / 0.1249 |
| Desktop 100 / 90 | 0.4998 / 0.4999 / 0.9998 | 0.4998 / 0.4999 / 0.4998 | 0.4499 / 0.4499 |

At 4.1–4.6 s, immediately after reference EOF, Mobile original gain already
increased to 1.1102 in the old export; the new gain remained 0.9998. Late old
gain is approximately +6.02 dB relative to the overlapping recording. The new
overlap matches the old overlap while the later gain increase disappears.

| Synthetic case | Old sample / 4x true peak dBFS | New sample / 4x true peak dBFS | Old/new decoded samples at or above full scale | Old/new LUFS |
|---|---|---|---|---|
| Mobile 200 / 50, normal tones | -7.950 / -7.944 | -12.401 / -12.396 | 0 / 0 | -12.4 / -15.4 |
| Correlated 0.95-amplitude peaks, 200 / 200 | +5.593 / +5.598 | -1.995 / -1.990 | 285,194 / 0 | +2.4 / -7.1 |

For the strong case, new isolated original gain before/after was
0.418023 / 0.418015; overlap gain relative to the summed source was the same.
FFmpeg's EBU R128 peak estimate was -2.0 dBFS. This proves constant attenuation
on that case instead of pumping. Full-scale counts describe decoded floating
samples that would exceed unity playback range; they do not establish whether
the original recording had already been hard-clipped.

Regression coverage additionally includes silence, both
mono and stereo, mixed mono/stereo in both directions, no original audio,
positive/negative offsets, reference entirely outside the video, original
audio shorter than video, reference EOF, software re-encoding, video bitstream
identity, AAC duration/padding, burst timing, FFmpeg failures, unavailable peaks,
rename failure, callback failure and child-process/partial-file cleanup.
The controlled 200 ms bursts at offsets ±312.5 ms retained onset/end placement
within 25 ms, including the existing AAC priming/mux behavior; no DSP delay was
introduced. Generated output duration remained 8 s within AAC-frame tolerance.

## Real Awaken in Ruins validation

The original MP4, reference MP3 and existing `awakeninruins_PM_synced.mp4` were
read-only inputs. The existing synchronized file was included as a listening
reference; its filename does not prove its sliders or exact generating build.
The task's Owner-reported 200 / 25 acceptance supports considering that
candidate, not claiming independently recovered settings for this file.
No accessible 超熊猫 pair was found in the local handcam library or XiaomiShare
intake, so no result is claimed for it.

Released Engine v2 selected **+10.95981859410431 s**,
`ACCEPT_PRIMARY_WITH_WAVEFORM`. The actual source GUI produced the same accepted
offset in both languages. Stream-copy video hashes matched for all four A/B
exports and both GUI exports; originals and existing synchronized media hashes
were unchanged after validation. Full video+audio decode of every A/B export
completed without FFmpeg errors.

| Media | Integrated LUFS | Sample peak dBFS | 4x reconstructed peak dBFS | Full-scale samples |
|---|---:|---:|---:|---:|
| Original recording | -27.8 | -5.185 | -5.179 | 0 |
| Reference MP3 decoded | -9.5 | +1.330 | +1.358 | 1,781 |
| Released 200 / 50 export | -21.0 | -4.705 | -4.689 | 0 |
| Stable 200 / 50 export | -20.9 | -3.544 | -3.539 | 0 |
| Stable 200 / 35 export | -23.3 | -3.984 | -3.976 | 0 |
| Stable 200 / 25 export | -25.1 | -4.336 | -4.330 | 0 |
| Existing synchronized file | -25.3 | -5.145 | -5.139 | 0 |

No protection attenuation was necessary in these three stable real mixes.
FFmpeg EBU R128 true-peak results agreed with the 4x reconstruction within
0.1 dB. The reference's decoded overshoots reinforce why simply disabling
normalization with unscaled gains is unsafe.

In the representative 15 s music-heavy section, recording and reference
loudness were **-28.6 and -9.0 LUFS**: a 19.6 LU difference before mixing.
At 200 / 50 the reference receives -12.04 dB gain, making its isolated
contribution about -21.0 LUFS versus the recording's -28.6 LUFS. At 35% and
25%, the corresponding reference contributions are about -24.1 and -27.1 LUFS.
These are isolated contribution calculations, not sums of LUFS values or a
subjective judgement of quality. Existing room music remains in the recording
and can interfere with the reference; slider ratios alone cannot remove it.

Decoded stable exports last 163.840 s versus the released export's 163.819 s;
explicit padding adds about one AAC frame to the tail. Video packet count is
9,233 throughout. First video PTS remains 0.008 s; first encoded AAC PTS remains
-0.021333 s (existing priming). Video packet last end remains 163.825722 s in
old/new exports; video and audio DTS are monotonic. No copied video frame or
payload changes. Old/new overlapping audio correlation differed by approximately
0.813 ms, consistent with retaining the fractional part of the positive delay
that the released graph truncated; the alignment engine offset is unchanged.

Measured local export wall times were 6.84 s released, and 11.08 / 7.48 / 7.31 s
stable 50 / 35 / 25. These are single, cache-sensitive runs, not a speed
benchmark. The extra peak pass is a real cost, with a truthful busy stage.

## Progress behavior and GUI acceptance

| Situation | Released behavior | Implemented behavior |
|---|---|---|
| Analyze or Sync analysis | Duration-based ETA and countdown; broad analysis label | Actual extraction, waveform loading, feature/reliability stage; indeterminate animation; no percentage or ETA |
| Peak scan | Absent | “Checking mix peaks” / “检查混合峰值”, indeterminate |
| FFmpeg export | Scraped human stats and extrapolated ETA | `-progress pipe:1` media `out_time_us`; monotonic 0–99%; no prediction |
| Finalization | ETA could reach zero before work ended | Retains the last actual percentage with finalization stage; 100% only after FFmpeg success and atomic replacement |
| Analysis success | 100% with zero ETA | “Analysis Complete” / “分析完成”; no fabricated percentage |
| Error or refusal | Timer/state cleanup depended on progress events | Explicit terminal status, stopped animation, cleared previous percentage, restored inputs/presets/buttons |
| New run | Previous value could survive until worker signal | Immediate reset before starting the worker |

Malformed, negative, N/A, non-finite or implausibly large FFmpeg timestamps are
ignored. Backward media timestamps cannot decrease percentage; oversized valid
timestamps clamp to 99%, and `progress=end` alone cannot claim success. A failed
encoder, scan, callback or atomic rename never reports 100%. The machine
progress protocol is described by [FFmpeg](https://ffmpeg.org/ffmpeg.html#Advanced-options).

The actual `RhythmAlignApp` GUI ran on the Windows desktop at 1050×820 logical
pixels / DPR 2, in zh_CN and en_US, with a task-local config and updater/folder
opening disabled in that validation process. GUI widgets, event loop, QThreads,
alignment and FFmpeg were real; only the save chooser was supplied by the harness.
Each language passed actual Analyze success, Sync export success, insufficient-
overlap refusal and unreadable-media error. Controls restored and animation
stopped in every terminal state. Export events progressed through 99 before
finalization and 100 after success. Source screenshots and structured event
receipts are private under `results/audio-progress/gui/{zh_CN,en_US}/`.
Long stage-label fit and restart behavior are also checked in both languages.

## Automated validation and reproduction

Before production edits: **120 passed, 1 skipped in 35.21 s**. Initial unrestricted
pytest collection exposed a missing `psutil` dependency in the existing soak
script; it was installed only into ignored `results/python-deps`, leaving the
existing Python environment unchanged. The baseline skip was the absent private
Awaken fixture in the new worktree. Its two allowlisted, hash-checked decoded
WAVs were subsequently copied into the ignored worktree fixture directory;
original media and fixtures were preserved.

Final full suite: **182 passed in 63.81 s**, no skips.
`git diff --check` passes. The source GUI produced eight successful acceptance
checks across the two languages. The new tests use independent signal and
transaction oracles, including preservation of previous destinations, child
reaping and actual post-rename existence at the first 100% event.

PowerShell reproduction from the isolated worktree, using installed dependencies:

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = "$PWD\results\python-deps"
$env:APPDATA = "$PWD\results\appdata"
& 'D:\Code\RhythmAlign\.venv\Scripts\python.exe' -m pytest -q -ra
& 'D:\Code\RhythmAlign\.venv\Scripts\python.exe' -m experiments.audio_progress.validate
```

The validation command without media arguments reproduces the synthetic table
and baseline AST/file integrity check. To create local real examples, add
`--video <original.mp4> --music <reference.mp3> --accepted <existing_synced.mp4>`.
GUI reproduction uses `-m experiments.audio_progress.gui_smoke --locale zh_CN`
(or `en_US`) with the video/music arguments. It isolates config before importing
the app and exercises success, refusal and failure; it creates fresh exports
under ignored `results/`.

## Owner listening and pending decisions

All media is local under **`D:\Code\RhythmAlign-audio-progress-1\results\audio-progress`**.
The clickable local guide is `OWNER-LISTENING.md` in that directory. Each file
below is a 15 s, 24-bit WAV derived from actual full exports:

| Section | Video time | Matched loudness | Filenames |
|---|---|---|---|
| Music-heavy | 70.960–85.960 s | -25.4 LUFS for all five | `awaken_music_heavy_{released_200_50,stable_200_50,stable_200_35,stable_200_25,existing_synced}_matched.wav` |
| Reference ending | 139.980–154.980 s | -39.7 LUFS for all five | `awaken_music_end_{released_200_50,stable_200_50,stable_200_35,stable_200_25,existing_synced}_matched.wav` |

Matching uses only a constant attenuation per clip, to the quietest member of
each group, with no compression or time-varying correction. It preserves the
end-transition shape. Raw float WAVs and full exports remain beside the matched
examples. Different sections have different common targets; keep volume fixed
within a comparison group. The ending group is intentionally quiet, so increase
playback volume once for that whole group if necessary.

Listen to stable **50 → 35 → 25** in the music-heavy group at fixed playback
volume. Judge tap audibility, existing room/game music, reference prominence and
phase/echo character. Compare 25 with the existing synchronized reference.
Then compare released/stable 50 in the ending group for a rising recording level.
Confirm any preferred balance on the corresponding full export; global
loudness matching is for balance comparison, not a change to production output.

**Preset proposal, pending Owner listening:** retain Arcade 120 / 70 and Desktop
100 / 90; consider Mobile 200 / 25 first given the Owner's existing satisfactory
result, with 200 / 35 as an intermediate option and 200 / 50 as the compatibility
reference. Replacement contribution is 6.02 dB lower at 25 than 50, and 3.10 dB
lower at 35 than 50. This evidence does not choose the subjective default across
different recordings. All three shipped preset buttons, and initial slider
values 120 / 60, remain numerically unchanged on this branch.

Open product decisions are the final Mobile preset and Owner acceptance of the
mix balance/tail behavior. Cross-recording perceptual generalization and the
inaccessible 超熊猫 example are unverified. Limiter behavior is not claimed
because none was introduced. Source GUI validation satisfies this branch's
requested scope; no installer was published.

No main merge, version bump, tag, Release, production manifest or active
installation change is part of this delivery. `app_info.py`, `config.json`,
`update.json`, `bundled_update.json`, the packaging specification and installer
script remain identical to the baseline under Git's newline normalization.
Copyrighted/private inputs, exports, A/B WAVs and GUI captures are ignored and
excluded from the commit and draft PR.
