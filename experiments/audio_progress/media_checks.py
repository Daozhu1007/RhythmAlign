"""Independent signal/codec measurements shared by regression and local review."""
import hashlib
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

SR = 48000


def ffmpeg(args, binary=False):
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-hide_banner", *map(str, args)],
        capture_output=True, timeout=180,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-6000:])
    return result if binary else result.stderr.decode("utf-8", errors="replace")


def tone(duration, frequency, amplitude, channels=2):
    t = np.arange(round(duration * SR)) / SR
    values = amplitude * np.sin(2 * np.pi * frequency * t)
    return values if channels == 1 else np.column_stack((values, values * 0.8))


def make_pair(root, channels=2, original=True, amplitude=0.2, music_amplitude=0.3):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    video, music = root / "recording.mkv", root / "music.wav"
    wavfile.write(music, SR, tone(2, 880, music_amplitude, channels).astype(np.float32))
    args = ["-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=96x64:r=25:d=8"]
    if original:
        recording = root / "recording.wav"
        wavfile.write(recording, SR, tone(8, 440, amplitude, channels).astype(np.float32))
        args += ["-i", recording, "-c:a", "pcm_f32le"]
    args += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", video]
    ffmpeg(args)
    return video, music


def decode(path, start=None, duration=None):
    args = ["-v", "error", "-i", path]
    if start is not None:
        args += ["-ss", start]
    if duration is not None:
        args += ["-t", duration]
    args += ["-vn", "-ac", "2", "-ar", SR, "-c:a", "pcm_f32le", "-f", "f32le", "-"]
    return np.frombuffer(ffmpeg(args, binary=True).stdout, dtype="<f4").reshape(-1, 2)


def amplitude(samples, frequency, start, end, channel=0):
    values = samples[round(start * SR):round(end * SR), channel].astype(float)
    t = np.arange(len(values)) / SR
    # Quadrature projection tolerates codec priming, unlike a phase-only oracle.
    return float(2 * abs(np.mean(values * np.exp(-2j * np.pi * frequency * t))))


def signal_metrics(samples):
    values = samples.astype(float)
    peak = float(np.max(np.abs(values))) if values.size else 0.0
    true_peak = float(np.max(np.abs(resample_poly(values, 4, 1, axis=0)))) if values.size else 0.0
    rms = float(np.sqrt(np.mean(values ** 2))) if values.size else 0.0
    return {
        "duration_s": len(values) / SR,
        "sample_peak": peak,
        "sample_peak_dbfs": float(20 * np.log10(peak)) if peak else None,
        "true_peak_4x": true_peak,
        "true_peak_4x_dbfs": float(20 * np.log10(true_peak)) if true_peak else None,
        "samples_at_or_above_full_scale": int(np.count_nonzero(np.abs(values) >= 1)),
        "rms_dbfs": float(20 * np.log10(rms)) if rms else None,
    }


def loudness(path):
    text = ffmpeg(["-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    integrated = re.findall(r"I:\s*(-?[\d.]+) LUFS", text)
    peaks = re.findall(r"Peak:\s*(-?[\d.]+) dBFS", text)
    return {"integrated_lufs": float(integrated[-1]) if integrated else None,
            "ffmpeg_true_peak_dbfs": float(peaks[-1]) if peaks else None}


def video_hash(path):
    text = ffmpeg(["-v", "error", "-i", path, "-map", "0:v:0", "-c:v", "copy",
                   "-f", "hash", "-hash", "sha256", "-"], binary=True).stdout
    return text.decode().strip()


def packet_timing(path, stream):
    result = ffmpeg(["-v", "error", "-i", path, "-map", f"0:{stream}:0", "-c", "copy",
                     "-f", "framehash", "-"], binary=True).stdout.decode()
    tb = re.search(r"#tb 0: (\d+)/(\d+)", result)
    scale = int(tb[1]) / int(tb[2])
    rows = [line.split(",") for line in result.splitlines() if line and not line.startswith("#")]
    pts = [int(row[2]) * scale for row in rows]
    dts = [int(row[1]) * scale for row in rows]
    return {"first_pts_s": pts[0], "first_dts_s": dts[0],
            "last_end_s": pts[-1] + int(rows[-1][3]) * scale,
            "packet_count": len(rows), "dts_monotonic": dts == sorted(dts)}


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
