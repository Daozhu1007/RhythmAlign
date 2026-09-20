#!/usr/bin/env python3
"""CP-2 packaged-artifact validation harness (standard library only).

Generates a deterministic handcam+music pair with a known +3.0 s offset
using the artifact's own bundled FFmpeg, then drives the packaged
executable's ``--validate`` entry point and checks the JSON report.

Usage:
    python3 validate_artifact.py --app /path/to/RhythmAlign \
        [--workdir DIR] [--keep] [--skip-analysis]

--skip-analysis runs the launch/resource checks only (no media), which is
the fast smoke variant used for cross-environment runner jobs.
"""

import argparse
import array
import glob
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import wave

SR = 22050
MUSIC_DUR = 45.0
VIDEO_DUR = 48.0
TRUE_OFFSET = 3.0
SEED = 20260921


def find_bundled_ffmpeg(app_dir):
    pattern = os.path.join(app_dir, "_internal", "imageio_ffmpeg", "binaries", "ffmpeg-*")
    matches = [p for p in glob.glob(pattern) if not p.endswith((".json", ".txt"))]
    if not matches:
        raise SystemExit(f"error: no bundled FFmpeg found under {pattern}")
    return sorted(matches)[0]


def run_ffmpeg(ffmpeg_bin, args):
    result = subprocess.run(
        [ffmpeg_bin, "-nostdin", "-hide_banner", "-loglevel", "error", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise SystemExit(f"error: ffmpeg {' '.join(args[:2])}... failed:\n{result.stderr[-2000:]}")


def synth_music(rng):
    """Structured music: 120 BPM kicks, C-G-Am-F chord bars, offbeat hats."""
    n = int(MUSIC_DUR * SR)
    mix = [0.0] * n

    for k in range(int(MUSIC_DUR / 0.5)):
        start = int(k * 0.5 * SR)
        dur = int(0.18 * SR)
        for i in range(min(dur, n - start)):
            t = i / SR
            mix[start + i] += 0.9 * math.sin(2 * math.pi * 58 * t) * math.exp(-t * 22)

    chords = [
        (261.63, 329.63, 392.00), (246.94, 293.66, 392.00),
        (220.00, 261.63, 329.63), (174.61, 220.00, 349.23),
    ]
    for b in range(int(MUSIC_DUR / 2.0)):
        f0 = chords[b % 4]
        start = int(b * 2.0 * SR)
        end = min(int(2.0 * SR), n - start)
        for i in range(end):
            t = i / SR
            env = 0.35 * (1 - math.exp(-t * 3)) * math.exp(-t * 0.35)
            tone = sum(math.sin(2 * math.pi * f * t) + 0.3 * math.sin(4 * math.pi * f * t) for f in f0)
            mix[start + i] += env * tone / 3.0

    for k in range(int(MUSIC_DUR / 0.5)):
        start = int((k * 0.5 + 0.25) * SR)
        dur = int(0.05 * SR)
        for i in range(min(dur, n - start)):
            mix[start + i] += 0.25 * (rng.random() * 2 - 1) * math.exp(-i / SR * 60)
    return mix


def write_wav(path, samples):
    frames = array.array("h", (max(-32768, min(32767, int(s * 32767 * 0.8))) for s in samples))
    with wave.open(path, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        fh.writeframes(frames.tobytes())


def generate_media(workdir, ffmpeg_bin):
    rng = random.Random(SEED)
    music = synth_music(rng)

    n_video = int(VIDEO_DUR * SR)
    video_audio = [0.0] * n_video
    drift = 0.0
    offset_n = int(TRUE_OFFSET * SR)
    for i in range(n_video):
        noise = rng.random() * 2 - 1
        drift = 0.98 * drift + 0.02 * noise  # low-frequency ambience
        if i >= offset_n:
            video_audio[i] = music[i - offset_n]
        video_audio[i] += 0.05 * drift + 0.01 * noise

    music_wav = os.path.join(workdir, "music_track.wav")
    video_wav = os.path.join(workdir, "video_audio.wav")
    write_wav(music_wav, music)
    write_wav(video_wav, video_audio)

    music_m4a = os.path.join(workdir, "music_track.m4a")
    video_mp4 = os.path.join(workdir, "handcam_source.mp4")
    run_ffmpeg(ffmpeg_bin, ["-y", "-i", music_wav, "-c:a", "aac", "-b:a", "128k", music_m4a])
    run_ffmpeg(ffmpeg_bin, [
        "-y", "-f", "lavfi", "-i", "color=c=0x202020:s=320x240:r=15",
        "-i", video_wav,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", video_mp4,
    ])
    os.remove(music_wav)
    os.remove(video_wav)
    return video_mp4, music_m4a


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True, help="path to the extracted RhythmAlign executable")
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--skip-analysis", action="store_true")
    args = parser.parse_args()

    app_dir = os.path.dirname(os.path.abspath(args.app))
    executable = os.path.join(app_dir, "RhythmAlign")
    if not os.access(executable, os.X_OK):
        raise SystemExit(f"error: {executable} is missing or not executable")

    workdir = args.workdir or tempfile.mkdtemp(prefix="ra_artifact_validation_")
    os.makedirs(workdir, exist_ok=True)
    json_path = os.path.join(workdir, "selftest_report.json")
    ffmpeg_bin = find_bundled_ffmpeg(app_dir)
    print(f"[validate] bundled FFmpeg: {ffmpeg_bin}")

    cmd = [executable, "--check-only", "--json", json_path]
    if not args.skip_analysis:
        video, music = generate_media(workdir, ffmpeg_bin)
        print(f"[validate] media pair: {video} + {music} (true offset +{TRUE_OFFSET:.1f}s)")
        cmd = [executable, "--validate", video, music, "--json", json_path,
               "--expect-offset", str(TRUE_OFFSET)]

    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    print(f"[validate] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=workdir, env=env, timeout=900,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if not os.path.exists(json_path):
        raise SystemExit(f"error: no report written; exit={result.returncode} stderr:\n{result.stderr[-3000:]}")

    with open(json_path, "r", encoding="utf-8") as fh:
        report = json.load(fh)

    print(f"[validate] mode={report['mode']} frozen={report['frozen']} ok={report['ok']}")
    for name, check in sorted(report["checks"].items()):
        mark = "PASS" if check["ok"] else "FAIL"
        print(f"  [{mark}] {name}: {check['detail']}")
    if report.get("engine"):
        print(f"[validate] engine: {json.dumps(report['engine'])}")
    if report.get("export"):
        print(f"[validate] export: {json.dumps(report['export'])}")

    ok = bool(report["ok"]) and result.returncode == 0
    print(f"[validate] RESULT: {'PASS' if ok else 'FAIL'}")
    if not args.keep and args.workdir is None and ok:
        shutil.rmtree(workdir, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
