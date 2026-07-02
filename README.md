<p align="center">
  <a href="README.md"><b>English</b></a> &nbsp;|&nbsp; <a href="README_zh.md">简体中文</a>
</p>

<p align="center">
  <img src="assets/logo.png" width="128" alt="RhythmAlign logo">
</p>

<h1 align="center">RhythmAlign</h1>

<p align="center">
  Automatic audio alignment for rhythm game handcam videos.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.1.2-blue" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-lightgrey" alt="License">
</p>

<p align="center">
  <img src="assets/screenshot_en.png" width="720" alt="RhythmAlign interface">
</p>

---

## Overview

RhythmAlign is built for one painful editing task: replacing noisy handcam audio with a clean music track while keeping the timing locked to the original video.

Instead of dragging waveforms by eye, you select:

1. the handcam video,
2. the clean reference music,
3. an output path.

RhythmAlign extracts both audio tracks, estimates the offset in musical-feature space, and exports a new MP4. By default it stream-copies the video track, so the image quality is preserved and only the audio is rebuilt.

## Download

For regular use, download the latest Windows build from [GitHub Releases](https://github.com/Daozhu1007/RhythmAlign/releases).

- **Setup installer:** recommended for normal installation, Start menu shortcuts, and stable Windows taskbar identity.
- **Portable ZIP:** unzip anywhere and run `RhythmAlign.exe` directly.

This README describes the current app. Per-version change logs are kept in the Release Notes so the front page stays readable.

## Current Highlights

- Light/dark UI with optional Windows theme following.
- Drag-and-drop video and audio import on both sync and analysis pages.
- Hybrid Chroma CENS delta + onset alignment for noisy handcam recordings and repeated rhythm-game chart sections.
- Video stream copy by default, preserving image quality while rebuilding audio.
- Analyze-only mode, diagnostic reports, and built-in update checks for easier troubleshooting.

## How Alignment Works

Raw waveform correlation is fragile. A phone microphone, arcade cabinet speakers, hand taps, compression, clipping, and background noise can make the recorded waveform look nothing like the clean music file.

RhythmAlign works on musical features instead:

1. **Decode to analysis audio**

   FFmpeg extracts both inputs to mono PCM at the analysis sample rate.

2. **Track pitch-class movement**

   `librosa.feature.chroma_cens` maps audio into 12 pitch-class bands. RhythmAlign then uses frame-to-frame chroma deltas, so the correlation follows musical changes rather than static repeated texture.

3. **Blend a small rhythmic cue**

   Onset strength is normalized and blended lightly into the chroma-delta curve. It helps with noisy handcam recordings without letting repeated drum patterns dominate the decision.

4. **Score confidence**

   The selected peak must pass a Z-score gate. If the engine falls back to onset-only matching, the best peak must also beat the next independent candidate by a minimum ratio.

5. **Export safely**

   FFmpeg delays or trims the replacement music, mixes it with the original audio if requested, and writes a new MP4.

Positive offset means the replacement music is delayed. Negative offset means the beginning of the replacement music is trimmed.

## Features

**Alignment**

- Hybrid Chroma CENS delta + onset alignment engine
- Z-score confidence gate
- Independent peak-ratio check for repeated rhythm patterns
- Analyze-only mode for checking the offset without exporting
- Manual offset slider for final sub-frame taste adjustments

**Export**

- Default video stream copy: no video re-encode, no quality loss
- Optional re-encode mode with NVIDIA NVENC support
- AAC audio output at 320 kbps
- Handles videos with no original audio track
- Cleans problematic metadata and timestamps for more reliable MP4 playback

**Workflow**

- One-screen sync workbench
- Drag-and-drop video/audio import
- Quick volume presets for arcade, mobile, and desktop recordings
- Bilingual UI: English and Simplified Chinese
- Light/dark theme support with optional Windows theme following
- Startup/manual update checks through the Settings page, with one-click installer download and SHA256 verification
- Copyable diagnostic report for troubleshooting packaged builds and difficult file pairs
- CLI diagnostic tool for difficult file pairs

## Run from Source

Packaged builds do not require Python. Use these steps when you want to run the source checkout directly or work on the project.

Requirements:

- Windows 10/11
- Python 3.9+ 64-bit
- Dependencies from `requirements.txt`
- FFmpeg is provided through `imageio-ffmpeg`

```powershell
git clone https://github.com/Daozhu1007/RhythmAlign.git
cd RhythmAlign
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python ui_main.py
```

Run the test suite:

```powershell
python -m pytest -q
```

## Usage

### Auto Sync

1. Select a video file: MP4, MKV, MOV, AVI, FLV, WMV, WebM, or TS.
2. Select a reference audio file: MP3, WAV, FLAC, M4A, AAC, OGG, or WMA.
3. Choose a volume preset or adjust volumes manually.
4. Optionally set a manual offset in milliseconds.
5. Click **Full Export** and choose the output path.

For best results, use the exact same music source as the one heard in the video. Different rips, edits, previews, or platform downloads can have intros, fades, mastering differences, or tiny cuts that no fixed-offset aligner can fully correct.

### Analyze Only

Use **Analyze Only** when you want the offset without exporting. This is useful when you plan to do the final edit in another video editor.

Example result:

```text
+0.1234 s
```

That means delaying the replacement music by `0.1234` seconds.

### Diagnose Difficult Pairs

```powershell
python diagnose_offset.py "video.mp4" "music.mp3"
```

The diagnostic output includes audio duration, RMS/peak levels, Chroma variance, Z-score, independent peak ratio, and the calculated offset.

## Reliability Notes

RhythmAlign v1.1.2 is much more robust against repeated beat patterns, but it is still a fixed-offset aligner. It can still struggle when:

- the reference music is not the same version as the video audio,
- the video was cut in the middle,
- the video has speed changes or long-term audio drift,
- hand taps or cabinet noise overpower the music,
- the song has extremely repetitive harmony and rhythm,
- the clean track has a different intro, fade, or silence padding.

For these cases, use `diagnose_offset.py`, Analyze Only mode, or a manual offset check before final export.

## Project Layout

```text
RhythmAlign/
├── ui_main.py              # PyQt GUI
├── auto_sync.py            # Alignment engine and FFmpeg export pipeline
├── diagnose_offset.py      # CLI diagnostic tool
├── tests/                  # Export and alignment reliability tests
├── assets/                 # App icon and screenshots
├── locales/                # English and Chinese UI strings
├── requirements.txt
├── RhythmAlign.spec        # PyInstaller build config
└── RhythmAlign.iss         # Inno Setup installer script
```

## Build Notes

The repository includes packaging files for PyInstaller and Inno Setup. The maintainer release flow, including installer and portable ZIP creation, is documented in [RELEASE.md](RELEASE.md).

## Copyright and Disclaimer

The app icon is cropped from the "Tairitsu Duck" emoji sticker series, created by Haruya ([Bilibili UID: 3280](https://space.bilibili.com/3280)) and used under a free open-source permission granted by the original commissioner.

Tairitsu and related character IP belong to lowiro. RhythmAlign is an independent, non-commercial community tool and is not affiliated with or endorsed by lowiro.

## License

RhythmAlign is released under the [PolyForm Noncommercial License 1.0.0](LICENSE).

Personal, non-commercial use is free. Commercial use, paid editing services, monetized studio use, and redistribution for profit are prohibited unless separately licensed by the author.

<p align="center">
  <a href="https://github.com/Daozhu1007/RhythmAlign"><img src="assets/github.png" height="22" alt="GitHub"></a>
  &nbsp;
  <a href="https://space.bilibili.com/477852567"><img src="assets/bilibili.png" height="22" alt="Bilibili"></a>
</p>
