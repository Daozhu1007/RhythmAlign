<p align="center">
  <a href="README.md"><b>English</b></a> &nbsp;|&nbsp; <a href="README_zh.md">简体中文</a>
</p>

<p align="center">
  <img src="logo.png" width="128" alt="Logo">
</p>

<h1 align="center">RhythmAlign</h1>

<p align="center">
  Automated audio alignment tool for rhythm game handcam videos.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

<p align="center">
  <img src="assets/screenshot_en.png" width="720" alt="Interface">
</p>

---

## Why RhythmAlign?

Synchronizing a handcam recording with a clean audio track in a conventional video editor (Premiere, CapCut, etc.) is tedious. You nudge the waveform back and forth by eye, render, re-check, repeat. When the onboard mic captures heavy keystroke noise and room echo — typical for arcade handcams — the editor's waveform view is nearly useless.

RhythmAlign handles this automatically:

1. Extracts audio from both your video and the reference music file.
2. Finds the best alignment offset using a two-strategy algorithm (Chroma pitch matching, with automatic fallback to Onset rhythm matching when the recording is too noisy).
3. Exports a new MP4 — video stream untouched, audio track replaced with the synced music.

---

## Features

### Audio Alignment

| Strategy | What it does | When it works |
|---|---|---|
| Chroma | Matches harmonic content (pitch classes) between the two tracks | Clean recordings: desktop capture, line-in audio |
| Onset (fallback) | Matches rhythmic attack transients | Noisy recordings: phone mic, arcade ambient noise |

The algorithm tries Chroma first. If the result fails a statistical confidence check, it automatically retries with Onset. Both fail → the UI shows an explicit error instead of exporting a misaligned result.

### Video Export

- **Stream copy (default):** Copies the original video bitstream 1:1. No re-encode, no quality loss. A 3-minute video finishes in seconds.
- **Re-encode (optional):** NVIDIA NVENC with 6000k / 10000k / 20000k bitrate presets. Use this when you need a specific codec or size.

### Mobile Video Robustness

Phone recordings — especially iPhone MOV files — often cause ffmpeg to misbehave:

| Problem | Fix |
|---|---|
| Variable Frame Rate (VFR) causes A/V drift | `-fflags +genpts` regenerates uniform timestamps |
| Negative timestamps break player sync | `-avoid_negative_ts make_zero` |
| QuickTime edit-list metadata causes crashes | `-map_metadata -1` strips all proprietary atoms |
| Moov atom at end of file blocks streaming | `-movflags +faststart` |

### Other

- **Analyze-only mode:** Compute the offset number without exporting. Paste it into any video editor timeline.
- **Manual offset trim:** ±500 ms slider for fine-tuning when the source audio is severely degraded.
- **Built-in diagnostics:** `diagnose_offset.py` prints Chroma variance, correlation Z-score, and audio stream metadata for troubleshooting.
- **Bilingual UI:** English / 简体中文, switchable in Settings.

---

## Quick Start

### Requirements

- Windows 10 / 11
- Python 3.9+ (64-bit)
- FFmpeg is bundled via `imageio-ffmpeg` — no separate install needed

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

### Troubleshoot a difficult file pair

```bash
python diagnose_offset.py "path/to/video.mp4" "path/to/music.mp3"
```

---

## Copyright & Disclaimer

### App Icon

The application icon is cropped from the **"Tairitsu Duck" (对立鸭)** emoji sticker series, created by:

> **春也Haruya** ([Bilibili UID: 3280](https://space.bilibili.com/3280))

Used under a free open-source license granted by the original commissioner. Sincere thanks to both the artist and the commissioner.

### IP Notice

**Tairitsu (对立)** and all related character designs, names, and intellectual property are owned by **lowiro**. RhythmAlign is an independent, non-commercial, open-source community tool. It is not affiliated with or endorsed by lowiro.

### Fair Use

- This software is **free and open-source** (MIT). If you paid for it, request a refund.
- **Personal, non-commercial use only.** Do not redistribute for profit.

---

## License

MIT. See [LICENSE](LICENSE).

---

<p align="center">
  <a href="https://github.com/Daozhu1007/RhythmAlign"><img src="github.png" height="22"></a>
  &nbsp;
  <a href="https://space.bilibili.com/477852567"><img src="bilibili.png" height="22"></a>
</p>
