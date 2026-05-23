import numpy as np
import librosa
from scipy import signal
import os
import time
import tempfile
import subprocess
import re
import uuid
import json
import imageio_ffmpeg


class CorrelationLowConfidenceError(RuntimeError):
    """互相关峰值置信度过低，无法可靠确定偏移量。"""
    def __init__(self, z_score, threshold):
        self.z_score = z_score
        self.threshold = threshold
        super().__init__(f"Correlation peak Z-score {z_score:.2f} below threshold {threshold:.1f}")


def _parse_duration_hms(stderr_text):
    """Parse HH:MM:SS.ms from ffmpeg/ffprobe stderr or stdout."""
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr_text)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return None


def get_video_duration(ffmpeg_bin, video_path):
    # Primary: fast ffmpeg probe
    cmd = [ffmpeg_bin, "-i", video_path]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace')
    duration = _parse_duration_hms(process.stderr)
    if duration is not None:
        return duration

    # Fallback: ffprobe for container formats where ffmpeg -i can't parse Duration
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        process = subprocess.run(
            [ffprobe_bin, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace', timeout=30
        )
        val = process.stdout.strip()
        if val:
            return float(val)
    except Exception:
        pass

    # Last resort: raise so the caller knows duration is unknown
    raise RuntimeError(f"Cannot determine duration of: {video_path}")


def extract_audio(ffmpeg_bin, input_path, output_path, sr):
    cmd = [
        ffmpeg_bin, "-y", "-i", input_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", str(sr), "-ac", "1",
        output_path
    ]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace')
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg底层音频提取崩溃: \n{process.stderr}")


# Reliability gate — Z-score thresholds:
#   < 1.0 : random noise, no peak at all
#   1.0–2.0: weak peak, result may be unreliable
#   > 2.0 : clear peak, result is trustworthy
_CONFIDENCE_THRESHOLD = 2.0


def _correlation_z_score(correlation):
    """Return Z-score of correlation peak. Higher = more reliable peak."""
    std_val = np.std(correlation)
    if std_val == 0:
        return 0.0
    return (np.max(correlation) - np.mean(correlation)) / std_val


def _align_chroma(y_video, y_music, sr, hop_length=512):
    """Align using Chroma CENS features (pitch content)."""
    feat_video = librosa.feature.chroma_cens(y=y_video, sr=sr, hop_length=hop_length)
    feat_music = librosa.feature.chroma_cens(y=y_music, sr=sr, hop_length=hop_length)

    correlation = np.zeros(feat_video.shape[1] + feat_music.shape[1] - 1)
    for i in range(12):
        correlation += signal.correlate(feat_music[i], feat_video[i], mode='full', method='fft')

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

        # Strategy 1: Chroma CENS (pitch/harmony — best for clean, high-quality audio)
        offset, z_score, _ = _align_chroma(y_video, y_music, sr, hop_length)
        if z_score >= confidence_threshold:
            return offset

        # Strategy 2: Onset envelope (rhythm/transients — robust to noisy recordings)
        offset, onset_z, _ = _align_onset(y_video, y_music, sr, hop_length)
        if onset_z >= confidence_threshold:
            return offset

        # Both failed — report the better of the two Z-scores
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


def _has_audio_stream(ffprobe_bin, input_path):
    """Return True if the media file has at least one audio stream."""
    try:
        result = subprocess.run(
            [ffprobe_bin, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "a", input_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors='replace', timeout=15
        )
        info = json.loads(result.stdout)
        return len(info.get("streams", [])) > 0
    except Exception:
        return True  # assume audio exists if probe fails


def mix_and_export(video_path, music_path, offset, output_path, vol_original=1.0, vol_music=1.0,
                   use_gpu=False, bitrate="10000k", manual_offset=0.0, stream_copy=True,
                   tr=None, ui_log_callback=None, ui_progress_callback=None):
    if tr is None:
        tr = lambda k, *args: k

    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    final_offset = offset + manual_offset

    # 使用正则原生提取时长
    total_duration = get_video_duration(ffmpeg_bin, video_path)

    if abs(final_offset) < 0.001:
        music_filter = f"aformat=channel_layouts=stereo,volume={vol_music}"
    elif final_offset > 0:
        delay_ms = int(final_offset * 1000)
        music_filter = f"aformat=channel_layouts=stereo,volume={vol_music},adelay={delay_ms}|{delay_ms}"
    else:
        abs_delay = abs(final_offset)
        music_filter = f"aformat=channel_layouts=stereo,volume={vol_music},atrim=start={abs_delay},asetpts=PTS-STARTPTS"

    # 探测视频音轨：无声视频时仅使用音乐轨
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    if _has_audio_stream(ffprobe_bin, video_path):
        filter_complex = f"[0:a:0]volume={vol_original}[a0];[1:a:0]{music_filter}[a1];[a0][a1]amix=inputs=2:duration=first[aout]"
    else:
        filter_complex = f"[1:a:0]{music_filter}[aout]"

    cmd = [
        ffmpeg_bin, "-y",
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
    cmd.append(output_path)

    if ui_log_callback:
        ui_log_callback(tr("log_target_offset", final_offset))

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')

    start_time_real = time.time()
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

        time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
        if time_match and ui_progress_callback:
            h, m, s = time_match.groups()
            current_sec = int(h) * 3600 + int(m) * 60 + float(s)
            percent = min(int((current_sec / total_duration) * 100), 99)

            elapsed = time.time() - start_time_real
            eta_str = tr("status_calc")
            if percent > 0:
                eta_sec = (elapsed / (percent / 100.0)) - elapsed
                eta_m, eta_s = divmod(int(eta_sec), 60)
                eta_str = f"{eta_m:02d}:{eta_s:02d}"

            task_name = tr("task_copy_ing") if stream_copy else tr("task_rendering")
            ui_progress_callback(task_name, percent, eta_str)

    process.wait()

    if process.returncode != 0:
        if critical_errors:
            err_msg = "CRITICAL:\n" + "\n".join(critical_errors[-20:])
            err_msg += "\n\n--- tail ---\n" + "\n".join(error_log)
        else:
            err_msg = "\n".join(error_log)
        raise RuntimeError(tr("err_ffmpeg_crash", err_msg))

    if ui_progress_callback:
        ui_progress_callback(tr("task_done_export"), 100, "00:00")