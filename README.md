<p align="center">
  <img src="logo.png" alt="RhythmAlign Logo" width="140" />
</p>

<h1 align="center">RhythmAlign</h1>

<p align="center">
  <strong>Auto-align your rhythm game handcam to the studio master — in one click.</strong><br>
  Two-stage Chroma/Onset cascade &bull; Z-score reliability gate &bull; VFR-hardened ffmpeg export.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs" />
</p>

<p align="center">
  <img src="assets/screenshot_en.png" alt="RhythmAlign Interface" width="720" />
</p>

<p align="center">
  <a href="README_zh.md">简体中文说明</a> &nbsp;|&nbsp; <b>English Readme</b>
</p>

---

## ⚠️ Disclaimer

This software is **free and open-source** — distributed under the MIT License for personal, non-commercial use. If you paid for a copy, request a refund immediately.

RhythmAlign is an independent community tool. It is **not affiliated with, endorsed by, or connected to lowiro** in any capacity. All references to rhythm game titles are for compatibility description only.

---

## What Problem Does This Solve?

You record a handcam — phone on a tripod, onboard mic picking up keystroke clatter and room reverb. Separately, you have the studio master: pristine, uncompressed, perfectly mixed.

Now you need to **replace the scratchy in-camera audio with the studio track**, and the two recordings must line up to within tens of milliseconds. Manually nudging an audio clip in a video editor takes minutes per video and is never quite right.

RhythmAlign does this **automatically, in seconds, with a confidence score**. It cross-correlates the two audio signals in musical-feature space, finds the sub-second offset, and remuxes the final MP4 — with the original video stream untouched.

If you play *Arcaea*, *Phigros*, *osu!*, *maimai*, *CHUNITHM*, or any other rhythm game and produce handcam content, this is your tool.

---

## ✨ Features

- **One-click export** — select video + pure music, pick an output path, done. The exported MP4 has your video stream synced to the mixed audio track.
- **Stream-copy fast path** — video bitstream is copied 1:1 with zero re-encode. A 3-minute video exports in under 10 seconds at full original quality.
- **Hardware encode fallback** — when transcoding is necessary, optional NVIDIA NVENC acceleration with 6000k / 10000k / 20000k bitrate presets.
- **Volume presets** — one-tap *Arcade*, *Mobile*, or *Desktop* gain profiles tuned for common recording setups. Adjustable sliders if you need finer control.
- **Analyze-only mode** — compute the offset without exporting. Paste the value directly into DaVinci Resolve, Premiere, or any timeline editor.
- **Manual offset trim** — ±500 ms fine-tuning slider for edge cases where source audio is severely degraded.
- **Built-in diagnostic toolkit** — `diagnose_offset.py` profiles Chroma variance, cross-correlation Z-score, and audio stream metadata to debug stubborn file pairs.
- **Full bilingual UI** — English / 简体中文, persisted language preference, JSON-based i18n with zero framework overhead.

---

## 🔬 Architecture — The Two-Stage Feature Cascade

The core alignment problem, stated precisely: *given two audio signals with drastically different timbre, loudness, and noise profiles, find the time offset that maximizes their musical agreement.*

Naive waveform cross-correlation fails here — the two signals are structurally different. RhythmAlign operates in **musical-feature space**, where timbre and recording artifacts are abstracted away.

### Stage 1 — Chroma CENS (Harmonic Fingerprint)

```python
feat_video = librosa.feature.chroma_cens(y=y_video, sr=sr, hop_length=512)
feat_music = librosa.feature.chroma_cens(y=y_music, sr=sr, hop_length=512)
```

**Chroma CENS** (Chroma Energy Normalized Statistics) reduces audio to a 12-dimensional pitch-class vector per time frame, then applies temporal smoothing and L¹ normalization. The result is a **timbre-invariant harmonic fingerprint**: it captures which notes are sounding regardless of whether they were recorded through a studio condenser or a phone mic pressed against a table.

Cross-correlation runs independently on each chroma band and sums into a single confidence curve:

```python
correlation = np.zeros(feat_video.shape[1] + feat_music.shape[1] - 1)
for i in range(12):
    correlation += signal.correlate(feat_music[i], feat_video[i], mode='full', method='fft')
lag = np.argmax(correlation) - (feat_video.shape[-1] - 1)
offset = -(lag * hop_length) / sr
```

This strategy excels with clean system-audio captures (desktop screen recording, line-in from a capture card). It struggles when room acoustics and ambient noise corrupt the harmonic profile — typical of mobile-recorded arcade handcams.

### Stage 2 — Onset Strength Envelope (Rhythmic Fallback)

When Stage 1 returns a weak correlation peak, the pipeline automatically falls through to **onset strength**:

```python
onset_video = librosa.onset.onset_strength(y=y_video, sr=sr, hop_length=512)
onset_music = librosa.onset.onset_strength(y=y_music, sr=sr, hop_length=512)
correlation = signal.correlate(onset_music, onset_video, mode='full', method='fft')
```

Onset strength is a **1D signal** per track capturing note attack transients — *when* notes begin rather than *which* notes they are. This makes it dramatically more robust to noise and distortion. Even a heavily clipped phone recording preserves the rhythmic attack structure of the underlying music.

The trade-off: onset frames are orders of magnitude sparser than chroma frames, so alignment precision is coarser. But as a fallback, it turns unwatchable noise into a usable result.

---

## 🛡️ Reliability Gating — No Silent Misalignments

The most dangerous failure mode of any auto-alignment tool is **producing a wrong offset without the user knowing**. RhythmAlign applies a statistical confidence gate to every correlation result:

```python
z_score = (np.max(correlation) - np.mean(correlation)) / np.std(correlation)
_CONFIDENCE_THRESHOLD = 2.0  # empirically calibrated
```

The Z-score measures how many standard deviations the correlation peak rises above the noise floor:

| Z-score | Interpretation | Action |
|---|---|---|
| **< 1.0** | Random noise — no discernible peak | Both stages fail; error surfaced to UI |
| **1.0 – 2.0** | Weak peak — possibly unreliable | Fallback to Stage 2; if both fail, error surfaced |
| **> 2.0** | Clear, unambiguous peak | Result accepted; export proceeds |

When both stages fail the Z-score gate, the tool raises `CorrelationLowConfidenceError` with the actual Z-score and the threshold. The UI displays explicit guidance — use the manual offset slider, or try a cleaner audio source. Crucially, **it never silently exports a misaligned video**.

---

## 🎬 The FFmpeg Pipeline — VFR Drift & QuickTime Sanitization

Mobile-recorded videos present two structural problems that break naive ffmpeg pipelines:

1. **Variable Frame Rate (VFR)** — frame timestamps are non-uniform. ffmpeg can't maintain A/V sync over VFR input without explicit flagging.
2. **QuickTime Edit-List Atoms** — Apple MOV containers embed an edit list that instructs players to apply non-trivial timeline transforms (rotation, trimming, track reordering). ffmpeg may or may not honor these — behavior varies by build and platform.

RhythmAlign's export command addresses both aggressively:

```bash
ffmpeg -y \
  -fflags +genpts \
  -avoid_negative_ts make_zero \
  -i video.mp4 \
  -i music.mp3 \
  -filter_complex "[0:a:0]volume=${vol_orig}[a0];[1:a:0]${music_filter}[a1];[a0][a1]amix=inputs=2:duration=first[aout]" \
  -map 0:v:0 -map "[aout]" \
  -c:v copy \
  -c:a aac -b:a 320k \
  -map_metadata -1 \
  -movflags +faststart \
  output.mp4
```

Each flag carries specific intent:

| Flag | Purpose |
|---|---|
| `-fflags +genpts` | Force-regenerate presentation timestamps from decode order — eliminates VFR drift |
| `-avoid_negative_ts make_zero` | Normalize any negative timestamps to zero — prevents player-dependent A/V offset |
| `-c:v copy` | Stream-copy video 1:1 — zero generational quality loss, sub-10-second export for typical videos |
| `-map_metadata -1` | Strip all source-file metadata — removes QuickTime edit lists, rotation matrices, color profiles |
| `-movflags +faststart` | Relocate moov atom to file header — enables streaming playback before full download |

The pipeline also handles several edge cases at the Python layer:

- **Video has no audio track**: detected via `ffprobe -select_streams a`; music track used as sole audio source, skipping the amix filter.
- **Negative offset** (music starts before video): uses `atrim=start=N` to trim the music track rather than padding with digital silence.
- **Duration parsing failure**: falls back from `ffmpeg -i` regex to `ffprobe -show_entries format=duration` JSON probe; raises a clear `RuntimeError` if both fail.
- **Temporary WAV files**: always cleaned in a `finally` block regardless of how the function exits.

---

## 🚀 Quick Start

### Prerequisites

- **Windows 10 or 11** (primary target; macOS/Linux untested but the engine is platform-agnostic)
- **Python 3.9+** (64-bit)
- **FFmpeg** is bundled automatically via `imageio-ffmpeg` — no separate installation needed

### Install

```bash
git clone https://github.com/Daozhu1007/RhythmAlign.git
cd RhythmAlign
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python ui_main.py
```

### Debug a Stubborn File Pair

```bash
python diagnose_offset.py "D:\videos\handcam.mp4" "D:\music\track.mp3"
```

Output includes: audio codec + sample rate, RMS/peak energy (catches silent tracks), Chroma feature variance (catches featureless audio), cross-correlation Z-score and peak-to-mean ratio, and specific troubleshooting advice per metric.

---

## 📖 Usage

### Auto-Sync Tab

1. Browse for your **video** (MP4 / MKV / MOV / AVI / FLV / WMV / WebM / TS).
2. Browse for your **pure music** (MP3 / WAV / FLAC / M4A / AAC / OGG / WMA).
3. Tap a volume preset — *Arcade* (loud keystrokes), *Mobile* (quiet room), or *Desktop* (system audio) — or adjust sliders manually.
4. Click **Full Export**, choose an output path.
5. Done. The output MP4 has your untouched video stream plus the synchronized mixed audio.

### Analyze-Only Tab

Use this when you want the offset number but not a rendered export — for example, if you do your own mixing in DaVinci Resolve or Premiere.

The result card displays the offset as `+0.1234 s` or `-0.5678 s` with an explicit instruction: which direction to nudge the music track on your timeline.

---

## ⚙️ Configuration

All settings persist to `config.json`. Configure them in the Settings tab:

| Setting | Default | Effect |
|---|---|---|
| **Language** | 简体中文 | English / 中文 UI; restart required |
| **Stream Copy** | On | Skip video re-encode; near-instant export, zero quality loss |
| **GPU Acceleration** | Off | NVIDIA NVENC encode (only active when Stream Copy is off) |
| **Bitrate** | 10000k | 6000k (sharing) / 10000k (recommended) / 20000k (archival) |
| **Open Folder** | On | Auto-open output directory after export |

---

## 📁 Project Structure

```
RhythmAlign/
├── ui_main.py              # PyQt6 + QFluentWidgets GUI (4 tabs: Sync, Analyze, About, Settings)
├── auto_sync.py            # Alignment engine + ffmpeg export pipeline
├── diagnose_offset.py      # CLI diagnostic: Chroma variance, Z-score, stream metadata
├── locales/
│   ├── zh_CN.json          # 简体中文 strings
│   └── en_US.json          # English strings
├── requirements.txt        # Python dependencies (no moviepy)
├── logo.png                # App icon — Tairitsu duck
├── logo.ico                # Windows .ico variant
└── config.json             # Persisted user settings (auto-generated)
```

---

## 🤝 Contributing

PRs are welcome. For non-trivial changes, open an issue first.

High-impact contribution areas:
- **macOS / Linux validation** — the core engine imports no Windows-specific modules; the GUI is the blocker
- **Additional alignment strategies** — MFCC, DTW, or learned embeddings as tertiary fallbacks for extreme noise
- **New locale files** — the i18n system requires zero code changes; just add `locales/ja_JP.json`

---

## 📜 License & Credits

### Code

MIT License. See [LICENSE](LICENSE).

### App Icon & Branding — Tairitsu Duck (对立鸭)

The application icon and related visual assets are cropped from the **"Tairitsu Duck"** emoji sticker series. These assets are used under a free open-source license, graciously granted by:

> **春也Haruya** ([Bilibili UID: 3280](https://space.bilibili.com/3280)) — illustrator and original creator of the sticker series.
>
> Special thanks to the commissioner who negotiated open-source usage rights.

### Character & Intellectual Property

**Tairitsu (对立)** and all related character designs, names, and intellectual property are the exclusive property of **lowiro**. RhythmAlign is an independent, non-commercial, open-source community utility. It is not endorsed by, affiliated with, or otherwise connected to lowiro.

### Fair Use

- This tool is **free software**. If you paid for a copy, demand a refund.
- **Personal, non-commercial use only.** Do not redistribute for profit or bundle with commercial products.

---

## 💬 Community

<p align="center">
  <a href="https://github.com/Daozhu1007/RhythmAlign"><img src="github.png" height="24" /></a>
  &nbsp;&nbsp;
  <a href="https://space.bilibili.com/477852567"><img src="bilibili.png" height="24" /></a>
</p>

<p align="center">
  <sub>Built for the rhythm game community. Pull requests and bug reports welcome.</sub>
</p>
