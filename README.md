<p align="center">
  <img src="logo.png" alt="RhythmAlign Logo" width="128" />
</p>

<h1 align="center">RhythmAlign</h1>
<p align="center">
  <strong>Production-grade audio-visual synchronization for rhythm game handcam videos.</strong><br>
  Two-stage feature cascade &bull; reliability-gated alignment &bull; VFR-stable ffmpeg pipeline.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python" />
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/status-stable-brightgreen" alt="Status" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome" />
</p>

<p align="center">
  <img src="screenshot.png" alt="RhythmAlign Main Interface" width="720" />
</p>

---

## What is RhythmAlign?

RhythmAlign solves a hard, real-world problem for rhythm game players and content creators: **automatically aligning a handcam video with a separate high-quality audio track (the "pure" music file)** so that keystrokes, visuals, and audio are perfectly synchronized—even when the video was recorded on a mobile device with noisy onboard microphones, variable frame rate (VFR), or Apple-specific container quirks.

If you play *Arcaea*, *Phigros*, *osu!*, *maimai*, or any other rhythm game and produce handcam content, you know the pain: you record gameplay video on one device and want to replace the scratchy, compressed in-room audio with the studio master. Manually nudging tracks in a video editor is tedious and imprecise. RhythmAlign automates this end-to-end with a **signal-processing pipeline** that is both mathematically rigorous and hardened against real-world media corruption.

---

## Key Features

- **One-click auto-sync** — drop in a video and a music file; get a fully mixed, synced MP4 export in seconds.
- **Two-stage feature cascade** — Chroma CENS (pitch/harmony) as the primary strategy, Onset Strength Envelope (rhythm/transients) as the noise-robust fallback.
- **Reliability gating** — Z-score thresholding on the cross-correlation peak; weak matches are flagged before producing a bad output, protecting users from silent alignment failures.
- **Stream-copy mode** — remux the original video stream untouched (zero quality loss, near-instant export) while replacing only the audio track.
- **Hardware encode fallback** — optional NVIDIA NVENC re-encode when transcoding is necessary, with configurable bitrate ladders.
- **VFR / QuickTime hardening** — force-regenerates PTS (`+genpts`), normalizes negative timestamps (`make_zero`), strips proprietary MOV/QuickTime metadata atoms, and remuxes with `+faststart` for web-optimized playback.
- **Built-in diagnostic toolkit** — the `diagnose_offset.py` script profiles Chroma variance, correlation Z-score, and audio stream metadata so you can debug stubborn file pairs.
- **Dark-themed Fluent Design UI** — powered by PyQt6 + QFluentWidgets, with full bilingual (English / Simplified Chinese) i18n support.

---

## Technical Deep Dive

### Two-Stage Feature Cascade

The core alignment problem is: *given two audio signals with potentially drastic timbral differences (onboard mic vs. studio master), find the time offset that maximizes their musical agreement.*

Naive cross-correlation on raw waveforms fails catastrophically here — the waveforms are structurally different. Instead, RhythmAlign operates in **feature space**:

#### Stage 1 — Chroma CENS (Harmonic Fingerprint)

```
feat = librosa.feature.chroma_cens(y, sr=sr, hop_length=512)
```

**Chroma CENS** (Chroma Energy Normalized Statistics) maps audio to a 12-dimensional pitch-class profile per time frame, then applies temporal smoothing and normalization. This strips away timbre, loudness, and recording artifacts — what remains is a robust *harmonic fingerprint*: which notes are sounding, regardless of *how* they were recorded.

Cross-correlation is computed independently on each of the 12 chroma bands and summed, yielding a single correlation vector whose peak position gives the time offset:

```python
for i in range(12):
    correlation += signal.correlate(feat_music[i], feat_video[i], mode='full', method='fft')
offset = - (argmax(correlation) - (len(feat_video) - 1)) * hop_length / sr
```

This works beautifully for clean, high-quality recordings (e.g., desktop screen capture with system audio). But when the video audio is an external microphone recording in a noisy room — common for mobile/arcade handcams — chroma features can be corrupted by reverberation and ambient noise.

#### Stage 2 — Onset Strength Envelope (Rhythmic Fallback)

When Chroma CENS produces an unreliable result, the pipeline automatically falls back to **onset strength**:

```
onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
```

Onset strength captures *when* notes begin — the transient attacks — rather than *which* notes are playing. This is a 1D signal per track, making it far more robust to noise and timbral distortion. Even a badly clipped phone recording will preserve the rhythmic onset structure of the music.

The same FFT-based cross-correlation is then applied to the onset envelopes. The trade-off is lower precision (onsets are sparser than chroma frames), but dramatically higher noise immunity.

### Reliability Gating — Z-Score Thresholding

A critical failure mode in any auto-alignment tool is **producing a wrong offset without the user knowing**. To prevent this, RhythmAlign applies a statistical reliability gate:

```python
z_score = (max(correlation) - mean(correlation)) / std(correlation)
if z_score < 2.0:  # Default threshold
    raise CorrelationLowConfidenceError(z_score, threshold)
```

This Z-score measures how many standard deviations the correlation peak rises above the noise floor. Empirically:
- **Z < 1.0**: random noise — no discernible peak
- **Z = 1.0–2.0**: weak peak — result may be unreliable; manual verification recommended
- **Z > 2.0**: clear, unambiguous peak — result is trustworthy

When both stages fail the Z-score gate, the tool reports the failure explicitly rather than silently exporting a misaligned video. Users can then use the manual offset slider or provide a cleaner audio source.

### FFmpeg Pipeline — VFR Drift Elimination & Metadata Sanitization

Mobile-recorded videos (especially from iPhones) present two notorious problems:

1. **Variable Frame Rate (VFR)** — the video track has non-uniform frame timestamps. When ffmpeg processes VFR input, audio/video sync can drift over time.
2. **QuickTime Edit-List Atoms** — Apple devices store an edit list in the MOV container that instructs players to apply timeline transformations. ffmpeg may or may not honor this, causing unpredictable A/V offset.

RhythmAlign's export pipeline addresses both aggressively:

```bash
ffmpeg -y \
  -fflags +genpts \            # Force-regenerate presentation timestamps (fixes VFR)
  -avoid_negative_ts make_zero \ # Normalize any negative timestamps to zero
  -i video.mp4 \
  -i music.mp3 \
  -filter_complex "..." \
  -map 0:v:0 -map [aout] \
  -c:v copy \                  # Stream-copy: zero re-encode, zero quality loss
  -c:a aac -b:a 320k \
  -map_metadata -1 \           # Strip all source-file metadata (incl. QuickTime atoms)
  -movflags +faststart \       # Relocate moov atom for streaming-optimized MP4
  output.mp4
```

`-map_metadata -1` is particularly important: it strips proprietary QuickTime metadata (rotation matrices, edit lists, color profiles) that can cause player-dependent behavior. Combined with `+genpts`, the output MP4 has a clean, deterministic timeline that plays identically on every player.

The stream-copy path (`-c:v copy`) preserves the original video bitstream 1:1 — no generational quality loss and near-instant processing (typically under 10 seconds for a 3-minute video). For users who need to transcode (e.g., applying hardware encoding or changing resolution), the re-encode path supports NVIDIA NVENC with configurable bitrate presets.

### Edge Cases Handled

| Scenario | Behavior |
|---|---|
| Video has no audio track | Detected via ffprobe; music track used as sole audio source |
| Offset is negative (music starts before video) | `atrim=start=N` to trim the music track rather than padding with silence |
| ffmpeg fails to parse duration | Falls back to ffprobe JSON probe; raises a clear error if both fail |
| Both alignment stages fail | Raises `CorrelationLowConfidenceError` with actionable guidance in the UI |
| Temporary files left behind on crash | Cleaned in a `finally` block regardless of exit path |

---

## Quick Start

### Prerequisites

- **Windows 10 or 11** (primary target; may work on Linux/macOS with minor adjustments)
- **Python 3.9+** (64-bit recommended)
- **FFmpeg** is bundled automatically via `imageio-ffmpeg` — no manual installation needed

### Installation

```bash
# Clone the repository
git clone https://github.com/Daozhu1007/RhythmAlign.git
cd RhythmAlign

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python ui_main.py
```

### Diagnostic Tool (for debugging difficult file pairs)

```bash
python diagnose_offset.py "path/to/video.mp4" "path/to/music.mp3"
```

The diagnostic script prints:
- Audio stream codec, channels, and sample rate
- RMS energy and peak amplitude (to detect silent/corrupted tracks)
- Chroma CENS feature variance (to detect featureless audio)
- Cross-correlation quality metrics (Z-score, peak-to-mean ratio)
- Actionable troubleshooting recommendations

---

## Usage

### Auto-Sync Tab

1. Select your **video file** (MP4, MKV, MOV, AVI, FLV, WMV, WebM, TS).
2. Select your **pure music file** (MP3, WAV, FLAC, M4A, AAC, OGG, WMA).
3. (Optional) Choose a **volume preset** — *Arcade*, *Mobile*, or *Desktop* — or adjust sliders manually.
4. Click **Full Export** and choose an output path.
5. Done — the exported MP4 has your video stream plus the synced, mixed audio.

### Analyze-Only Tab

If you prefer to do the mixing in your own video editor (DaVinci Resolve, Premiere, etc.), use the Analyze tab. It computes the offset and displays the exact value you should nudge the pure music track by in your timeline.

### Manual Offset

If auto-alignment produces a slightly-off result (e.g., due to extremely noisy source audio), use the **Manual Offset (ms)** slider on the Sync tab to apply a fine-tuning correction. The displayed final offset = algorithmic offset + manual offset.

---

## Configuration

Settings are persisted in `config.json` and configurable in the Settings tab:

| Setting | Default | Description |
|---|---|---|
| Language | 简体中文 | UI language (English / 中文); requires restart |
| Stream Copy | On | Skip video re-encode; near-instant export, zero quality loss |
| GPU Acceleration | Off | Use NVIDIA NVENC when transcoding (only effective with Stream Copy off) |
| Video Bitrate | 10000k | Encoding bitrate: 6000k (sharing), 10000k (recommended), 20000k (archival) |
| Open Folder | On | Open output folder automatically after export |

---

## Project Structure

```
RhythmAlign/
├── ui_main.py              # PyQt6 + QFluentWidgets GUI (Sync, Analyze, About, Settings)
├── auto_sync.py            # Core alignment engine & ffmpeg export pipeline
├── diagnose_offset.py      # CLI diagnostic tool for debugging alignment failures
├── locales/
│   ├── zh_CN.json          # Simplified Chinese translations
│   └── en_US.json          # English translations
├── requirements.txt        # Python dependencies
├── logo.png                # Application icon (Tairitsu duck)
├── logo.ico                # Windows .ico variant
├── github.png              # GitHub branding asset
├── bilibili.png            # Bilibili branding asset
└── config.json             # User settings (auto-generated)
```

---

## Contributing

Contributions are welcome. For significant changes, please open an issue first to discuss your proposal.

Areas where help is especially appreciated:
- **macOS / Linux compatibility** — the core engine is platform-agnostic; GUI testing on non-Windows platforms
- **Additional alignment strategies** — e.g., MFCC-based, DTW-based, or deep-learning approaches as tertiary fallbacks
- **Multilingual UI** — adding new locale files

---

## License & Disclaimer

### Code License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

### Asset Credits

The application icon and branding assets are cropped from the **"Tairitsu Duck" (对立鸭)** emoji sticker series, graciously provided under a free open-source license by:

> **春也Haruya** (Bilibili UID: [3280](https://space.bilibili.com/3280))
>
> Special thanks to the original commissioner for granting open-source usage rights.

**Character & IP Notice:** Tairitsu (对立) and all related character assets, names, and intellectual property are the exclusive property of **lowiro**. RhythmAlign is an independent, non-commercial, open-source community tool. It is not affiliated with, endorsed by, or connected to lowiro in any way.

### ⚠️ Fair Use Notice

- This software is **free and open-source**. If you paid for it, please request a refund.
- For **personal, non-commercial use** only. Do not redistribute for profit or bundle with commercial products.

---

<p align="center">
  <sub>Made with ♪ for the rhythm game community.</sub>
</p>
