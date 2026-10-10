import numpy as np
import librosa
from scipy import signal
import os
import math
import tempfile
import subprocess
import re
import uuid
import imageio_ffmpeg


_IS_WINDOWS = os.name == "nt"


class CorrelationLowConfidenceError(RuntimeError):
    """互相关峰值置信度过低，无法可靠确定偏移量。"""
    def __init__(self, z_score, threshold):
        self.z_score = z_score
        self.threshold = threshold
        super().__init__(f"Correlation peak Z-score {z_score:.2f} below threshold {threshold:.1f}")


class AudioStreamDetectionError(RuntimeError):
    """Raised when FFmpeg cannot reliably determine whether an input has audio."""


def _subprocess_no_window_kwargs(**kwargs):
    """Return subprocess kwargs that hide child console windows on Windows."""
    if _IS_WINDOWS:
        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if create_no_window:
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | create_no_window
    return kwargs


def _parse_duration_hms(stderr_text):
    """Parse HH:MM:SS.ms from FFmpeg stderr or stdout."""
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr_text)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return None


def get_video_duration(ffmpeg_bin, video_path):
    # Primary: fast ffmpeg probe
    cmd = [ffmpeg_bin, "-hide_banner", "-i", video_path]
    process = subprocess.run(
        cmd,
        **_subprocess_no_window_kwargs(
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors='replace',
        )
    )
    duration = _parse_duration_hms(process.stderr)
    if duration is not None:
        return duration

    # Last resort: raise so the caller knows duration is unknown.
    raise RuntimeError(f"Cannot determine duration of: {video_path}")


def extract_audio(ffmpeg_bin, input_path, output_path, sr):
    cmd = [
        ffmpeg_bin, "-y", "-i", input_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", str(sr), "-ac", "1",
        output_path
    ]
    process = subprocess.run(
        cmd,
        **_subprocess_no_window_kwargs(
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors='replace',
        )
    )
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg底层音频提取崩溃: \n{process.stderr}")


# Reliability gate — Z-score thresholds:
#   < 1.0 : random noise, no peak at all
#   1.0–2.0: weak peak, result may be unreliable
#   > 2.0 : clear peak, result is trustworthy
_CONFIDENCE_THRESHOLD = 2.0
_FALLBACK_PEAK_RATIO_THRESHOLD = 1.05
_INDEPENDENT_PEAK_SEPARATION_SECONDS = 1.5
_HYBRID_ONSET_WEIGHT = 0.2


def _correlation_z_score(correlation):
    """Return Z-score of correlation peak. Higher = more reliable peak."""
    std_val = np.std(correlation)
    if std_val == 0:
        return 0.0
    return (np.max(correlation) - np.mean(correlation)) / std_val


def _normalize_correlation(correlation):
    """Normalize a correlation curve to zero mean and unit variance."""
    std_val = np.std(correlation)
    if std_val == 0:
        return np.zeros_like(correlation)
    return (correlation - np.mean(correlation)) / std_val


def _correlate_feature_rows(feat_video, feat_music):
    correlation = np.zeros(feat_video.shape[1] + feat_music.shape[1] - 1)
    for i in range(feat_video.shape[0]):
        correlation += signal.correlate(feat_music[i], feat_video[i], mode='full', method='fft')
    return correlation


def _independent_peak_ratio(correlation, min_separation_frames):
    """Return best-peak / next-independent-peak ratio for ambiguity checks."""
    if len(correlation) == 0:
        return 0.0

    order = np.argsort(correlation)[::-1]
    best_idx = order[0]
    best_val = correlation[best_idx]

    second_val = None
    for idx in order[1:]:
        if abs(idx - best_idx) >= min_separation_frames:
            second_val = correlation[idx]
            break

    if second_val is None:
        return float("inf") if best_val > 0 else 0.0
    if second_val <= 0:
        return float("inf") if best_val > 0 else 0.0
    return best_val / second_val


def _align_chroma(y_video, y_music, sr, hop_length=512):
    """Align using Chroma CENS deltas (pitch-content changes)."""
    feat_video = librosa.feature.chroma_cens(y=y_video, sr=sr, hop_length=hop_length)
    feat_music = librosa.feature.chroma_cens(y=y_music, sr=sr, hop_length=hop_length)

    feat_video = np.diff(feat_video, axis=1, prepend=feat_video[:, :1])
    feat_music = np.diff(feat_music, axis=1, prepend=feat_music[:, :1])

    correlation = _correlate_feature_rows(feat_video, feat_music)
    z_score = _correlation_z_score(correlation)
    lag = np.argmax(correlation) - (feat_video.shape[-1] - 1)
    offset_seconds = (lag * hop_length) / sr
    return -offset_seconds, z_score, correlation


def _align_onset(y_video, y_music, sr, hop_length=512):
    """Fallback: align using onset strength envelopes (rhythmic content, more noise-robust)."""
    onset_video = librosa.onset.onset_strength(y=y_video, sr=sr, hop_length=hop_length)
    onset_music = librosa.onset.onset_strength(y=y_music, sr=sr, hop_length=hop_length)

    correlation = signal.correlate(onset_music, onset_video, mode='full', method='fft')

    z_score = _correlation_z_score(correlation)
    lag = np.argmax(correlation) - (len(onset_video) - 1)
    offset_seconds = (lag * hop_length) / sr
    return -offset_seconds, z_score, correlation


def _align_hybrid(y_video, y_music, sr, hop_length=512):
    """Align with chroma deltas, lightly refined by centered onset evidence."""
    feat_video = librosa.feature.chroma_cens(y=y_video, sr=sr, hop_length=hop_length)
    feat_music = librosa.feature.chroma_cens(y=y_music, sr=sr, hop_length=hop_length)

    feat_video = np.diff(feat_video, axis=1, prepend=feat_video[:, :1])
    feat_music = np.diff(feat_music, axis=1, prepend=feat_music[:, :1])
    chroma_corr = _correlate_feature_rows(feat_video, feat_music)

    onset_video = librosa.onset.onset_strength(y=y_video, sr=sr, hop_length=hop_length)
    onset_music = librosa.onset.onset_strength(y=y_music, sr=sr, hop_length=hop_length)
    onset_corr = signal.correlate(
        onset_music - np.mean(onset_music),
        onset_video - np.mean(onset_video),
        mode='full',
        method='fft',
    )

    if len(chroma_corr) == len(onset_corr):
        correlation = (
            _normalize_correlation(chroma_corr)
            + _HYBRID_ONSET_WEIGHT * _normalize_correlation(onset_corr)
        )
    else:
        correlation = _normalize_correlation(chroma_corr)

    z_score = _correlation_z_score(correlation)
    lag = np.argmax(correlation) - (feat_video.shape[-1] - 1)
    offset_seconds = (lag * hop_length) / sr
    return -offset_seconds, z_score, correlation


def find_offset(video_path, music_path, sr=22050, confidence_threshold=None):
    if confidence_threshold is None:
        confidence_threshold = _CONFIDENCE_THRESHOLD

    temp_dir = tempfile.gettempdir()
    temp_audio_path = os.path.abspath(os.path.join(temp_dir, f"ra_temp_audio_{uuid.uuid4().hex}.wav"))
    temp_music_path = os.path.abspath(os.path.join(temp_dir, f"ra_temp_music_{uuid.uuid4().hex}.wav"))

    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    try:
        extract_audio(ffmpeg_bin, video_path, temp_audio_path, sr)
        extract_audio(ffmpeg_bin, music_path, temp_music_path, sr)

        y_video, _ = librosa.load(temp_audio_path, sr=None, mono=True)
        y_music, _ = librosa.load(temp_music_path, sr=None, mono=True)

        hop_length = 512

        # Strategy 1: pitch-content changes plus a small onset refinement.
        offset, z_score, _ = _align_hybrid(y_video, y_music, sr, hop_length)
        if z_score >= confidence_threshold:
            return offset

        # Strategy 2: onset envelope for percussive/noisy recordings.
        offset, onset_z, onset_corr = _align_onset(y_video, y_music, sr, hop_length)
        min_peak_separation = max(
            1,
            int((_INDEPENDENT_PEAK_SEPARATION_SECONDS * sr) / hop_length),
        )
        onset_peak_ratio = _independent_peak_ratio(onset_corr, min_peak_separation)
        if onset_z >= confidence_threshold and onset_peak_ratio >= _FALLBACK_PEAK_RATIO_THRESHOLD:
            return offset

        # Both failed; report the better Z-score for the UI message.
        best_z = max(z_score, onset_z)
        raise CorrelationLowConfidenceError(best_z, confidence_threshold)

    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass
        if os.path.exists(temp_music_path):
            try:
                os.remove(temp_music_path)
            except Exception:
                pass


def _has_audio_stream(ffmpeg_bin, input_path):
    """Return whether the media file has audio, raising on unreadable inputs."""
    try:
        result = subprocess.run(
            [
                ffmpeg_bin, "-nostdin", "-hide_banner", "-v", "error",
                "-i", input_path,
                "-map", "0:a:0",
                "-frames:a", "1",
                "-f", "null", "-"
            ],
            **_subprocess_no_window_kwargs(
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors='replace', timeout=15,
            )
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioStreamDetectionError(f"Timed out detecting audio stream in: {input_path}") from exc
    except OSError as exc:
        raise AudioStreamDetectionError(f"Unable to run FFmpeg for audio stream detection: {exc}") from exc

    if result.returncode == 0:
        return True

    stderr_text = result.stderr.strip()
    if "matches no streams" in stderr_text.lower():
        return False

    raise AudioStreamDetectionError(
        f"Unable to determine audio stream presence for {input_path}:\n{stderr_text}"
    )


def _make_temporary_output_path(output_path):
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path) or os.curdir
    stem, ext = os.path.splitext(os.path.basename(output_path))
    if not ext:
        raise ValueError("Output path must include a media extension.")
    temp_name = f".{stem}.{uuid.uuid4().hex}.partial{ext}"
    return output_path, os.path.join(output_dir, temp_name)


def _remove_file_if_exists(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# Fixed compatibility gain, followed by whole-file peak protection. Percentages
# are per-source multipliers relative to this baseline, NOT output loudness.
# The 192 kHz scan approximates intersample peaks; -2 dB leaves AAC headroom.
_MIX_PEAK_CEILING_DB = -2.0
_MIX_PEAK_SCAN_RATE = 192000


def _build_mix_filter(has_original, offset, duration, vol_original, vol_music):
    """Return the unprotected mix. Both sources have constant gain throughout.

    With original audio: gains are original/2 and music/2, matching the old
    overlapping section. With no original: music keeps its legacy unity base.
    Pad and trim explicitly so neither EOF changes gain or output duration.
    """
    base = 0.5 if has_original else 1.0
    music = f"aformat=channel_layouts=stereo,volume={vol_music * base:.12g}"
    if offset > 0:
        # Fractional milliseconds are supported; do not truncate small offsets.
        music += f",adelay={offset * 1000:.9f}:all=1"
    elif offset < 0:
        music += f",atrim=start={-offset:.12g},asetpts=PTS-STARTPTS"
    music += ",apad"
    tail = f"atrim=duration={duration:.12g},asetpts=PTS-STARTPTS[mixed]"
    if has_original:
        return (
            f"[0:a:0]volume={vol_original * base:.12g},apad[a0];"
            f"[1:a:0]{music}[a1];"
            f"[a0][a1]amix=inputs=2:duration=first:normalize=0,{tail}"
        )
    return f"[1:a:0]{music},{tail}"


def _measure_mix_peak(ffmpeg_bin, video_path, music_path, mix_filter):
    """Decode the exact mix once, measuring an oversampled peak without files.

    Fail closed if peak evidence is unavailable. No compressor or limiter is
    involved: one attenuation is selected before export for the entire file.
    """
    graph = (mix_filter + f";[mixed]aresample={_MIX_PEAK_SCAN_RATE},"
             "astats=reset=0:measure_perchannel=none:measure_overall=Peak_level[peak]")
    result = subprocess.run(
        [ffmpeg_bin, "-nostdin", "-hide_banner", "-nostats", "-i", video_path,
         "-i", music_path, "-filter_complex", graph, "-map", "[peak]",
         "-vn", "-c:a", "pcm_f32le", "-f", "null", "-"],
        **_subprocess_no_window_kwargs(
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace",
        ),
    )
    if result.returncode:
        raise RuntimeError(f"Audio peak scan failed:\n{result.stderr[-6000:]}")
    values = re.findall(r"Peak level dB:\s*([^\s]+)", result.stderr)
    try:
        peak_db = float(values[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError("Audio peak scan did not return a valid peak.") from exc
    if peak_db != -math.inf and not math.isfinite(peak_db):
        raise RuntimeError("Audio peak scan returned a non-finite peak.")
    return peak_db


def _mix_attenuation(peak_db):
    if peak_db <= _MIX_PEAK_CEILING_DB:
        return 1.0
    return 10 ** ((_MIX_PEAK_CEILING_DB - peak_db) / 20)


def _ffmpeg_progress_percent(line, duration, previous):
    """Machine progress is elapsed MEDIA time in microseconds, never an ETA."""
    match = re.fullmatch(r"out_time_us=(\d+)", line.strip())
    if not match or not math.isfinite(duration) or duration <= 0:
        return None
    # Reject implausibly large/malformed integers without converting huge input.
    if len(match[1]) > 18:
        return None
    seconds = int(match[1]) / 1_000_000
    return max(previous, min(99, int(seconds * 100 / duration)))


def mix_and_export(video_path, music_path, offset, output_path, vol_original=1.0, vol_music=1.0,
                   use_gpu=False, bitrate="10000k", manual_offset=0.0, stream_copy=True,
                   tr=None, ui_log_callback=None, ui_progress_callback=None,
                   ui_stage_callback=None):
    if tr is None:
        tr = lambda k, *args: k

    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    final_offset = offset + manual_offset
    if (not all(math.isfinite(v) for v in (final_offset, vol_original, vol_music))
            or min(vol_original, vol_music) < 0):
        raise ValueError("Offsets and gains must be finite; gains must be nonnegative.")
    output_path, temp_output_path = _make_temporary_output_path(output_path)

    # 使用正则原生提取时长
    total_duration = get_video_duration(ffmpeg_bin, video_path)
    if not math.isfinite(total_duration) or total_duration <= 0:
        raise ValueError("Video duration must be finite and positive.")
    if ui_stage_callback:
        ui_stage_callback(tr("stage_mix_peaks"))
    mix_filter = _build_mix_filter(
        _has_audio_stream(ffmpeg_bin, video_path), final_offset,
        total_duration, vol_original, vol_music,
    )
    peak_db = _measure_mix_peak(ffmpeg_bin, video_path, music_path, mix_filter)
    attenuation = _mix_attenuation(peak_db)
    filter_complex = mix_filter + f";[mixed]volume={attenuation:.12g}[aout]"
    if ui_log_callback:
        attenuation_db = 20 * math.log10(attenuation)
        ui_log_callback(tr("log_mix_gain", attenuation_db))

    cmd = [
        ffmpeg_bin, "-nostdin", "-hide_banner", "-y",
        "-progress", "pipe:1", "-nostats", "-stats_period", "0.2",
        "-fflags", "+genpts",
        "-avoid_negative_ts", "make_zero",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v:0", "-map", "[aout]"
    ]

    if stream_copy:
        cmd.extend(["-c:v", "copy", "-c:a", "aac", "-b:a", "320k"])
        if ui_log_callback:
            ui_log_callback(tr("log_stream_copy"))
    else:
        vcodec = "h264_nvenc" if use_gpu else "libx264"
        cmd.extend(["-c:v", vcodec, "-b:v", bitrate, "-c:a", "aac", "-b:a", "320k"])
        if ui_log_callback:
            ui_log_callback(tr("log_encode_mode", vcodec, bitrate))

    # 剥离源文件私有元数据 (如 iPhone QuickTime atoms)，优化 MP4 结构
    cmd.extend(["-map_metadata", "-1", "-movflags", "+faststart"])
    cmd.extend(["-t", f"{total_duration:.12g}"])
    cmd.append(temp_output_path)

    if ui_log_callback:
        ui_log_callback(tr("log_target_offset", final_offset))

    process = None
    try:
        process = subprocess.Popen(
            cmd,
            **_subprocess_no_window_kwargs(
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors='replace',
            )
        )

        previous_percent = 0
        task_name = tr("task_copy_ing") if stream_copy else tr("task_rendering")
        if ui_progress_callback:
            ui_progress_callback(task_name, 0)
        error_log = []
        critical_errors = []

        for line in process.stdout:
            stripped = line.strip()
            error_log.append(stripped)
            if len(error_log) > 50:
                error_log.pop(0)

            # 捕获含严重错误关键词的行，独立保存用于诊断
            lowline = stripped.lower()
            if any(kw in lowline for kw in ('error', 'failed', 'invalid')):
                critical_errors.append(stripped)

            percent = _ffmpeg_progress_percent(line, total_duration, previous_percent)
            if percent is not None and percent > previous_percent:
                previous_percent = percent
                if ui_progress_callback:
                    ui_progress_callback(task_name, percent)

        process.wait()

        if process.returncode != 0:
            if critical_errors:
                err_msg = "CRITICAL:\n" + "\n".join(critical_errors[-20:])
                err_msg += "\n\n--- tail ---\n" + "\n".join(error_log)
            else:
                err_msg = "\n".join(error_log)
            raise RuntimeError(tr("err_ffmpeg_crash", err_msg))

        if ui_stage_callback:
            ui_stage_callback(tr("stage_finalizing"))
        os.replace(temp_output_path, output_path)
    except Exception:
        if process is not None and getattr(process, "poll", lambda: 0)() is None:
            process.kill()
            process.wait()
        _remove_file_if_exists(temp_output_path)
        raise
    finally:
        if process is not None and hasattr(process.stdout, "close"):
            process.stdout.close()

    if ui_progress_callback:
        ui_progress_callback(tr("task_done_export"), 100)
