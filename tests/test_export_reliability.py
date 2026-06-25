import json
import math
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pytest

import auto_sync


def run_ffmpeg(ffmpeg_bin, args):
    result = subprocess.run(
        [ffmpeg_bin, "-nostdin", "-hide_banner", "-loglevel", "error", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def ffmpeg_bin():
    return imageio_ffmpeg.get_ffmpeg_exe()


def test_no_window_kwargs_are_empty_off_windows(monkeypatch):
    monkeypatch.setattr(auto_sync, "_IS_WINDOWS", False)
    monkeypatch.setattr(auto_sync.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    kwargs = auto_sync._subprocess_no_window_kwargs(stdout=subprocess.PIPE)

    assert kwargs == {"stdout": subprocess.PIPE}


def test_no_window_kwargs_are_added_on_windows_without_overwriting(monkeypatch):
    monkeypatch.setattr(auto_sync, "_IS_WINDOWS", True)
    monkeypatch.setattr(auto_sync.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    kwargs = auto_sync._subprocess_no_window_kwargs(stdout=subprocess.PIPE, creationflags=0x00000001)

    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["creationflags"] == 0x08000001


def test_independent_peak_ratio_detects_ambiguous_repeated_peaks():
    correlation = np.array([0.0, 10.0, 0.0, 9.9, 0.0])

    ratio = auto_sync._independent_peak_ratio(correlation, min_separation_frames=2)

    assert ratio < auto_sync._FALLBACK_PEAK_RATIO_THRESHOLD


def test_independent_peak_ratio_accepts_clear_peak():
    correlation = np.array([0.0, 10.0, 0.0, 6.0, 0.0])

    ratio = auto_sync._independent_peak_ratio(correlation, min_separation_frames=2)

    assert ratio > auto_sync._FALLBACK_PEAK_RATIO_THRESHOLD


def test_find_offset_rejects_ambiguous_onset_fallback(monkeypatch):
    ambiguous_correlation = np.zeros(200)
    ambiguous_correlation[70] = 10.0
    ambiguous_correlation[140] = 9.9

    monkeypatch.setattr(auto_sync.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(auto_sync, "extract_audio", lambda *args: None)
    monkeypatch.setattr(auto_sync.librosa, "load", lambda *args, **kwargs: (np.zeros(1024), 22050))
    monkeypatch.setattr(auto_sync, "_align_hybrid", lambda *args: (0.0, 0.5, np.array([0.0])))
    monkeypatch.setattr(
        auto_sync,
        "_align_onset",
        lambda *args: (18.0, 3.0, ambiguous_correlation),
    )

    with pytest.raises(auto_sync.CorrelationLowConfidenceError):
        auto_sync.find_offset("video.mp4", "music.mp3")


def test_extract_audio_passes_no_window_flag_on_windows(monkeypatch):
    monkeypatch.setattr(auto_sync, "_IS_WINDOWS", True)
    monkeypatch.setattr(auto_sync.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    calls = []

    class CompletedProcess:
        returncode = 0
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return CompletedProcess()

    monkeypatch.setattr(auto_sync.subprocess, "run", fake_run)

    auto_sync.extract_audio("ffmpeg", "input.mp4", "output.wav", 22050)

    assert calls[0][1]["creationflags"] == 0x08000000
    assert calls[0][1]["stdout"] == subprocess.PIPE
    assert calls[0][1]["stderr"] == subprocess.PIPE


def test_mix_and_export_popen_passes_no_window_flag_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_sync, "_IS_WINDOWS", True)
    monkeypatch.setattr(auto_sync.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(auto_sync.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(auto_sync, "get_video_duration", lambda ffmpeg, path: 1.0)
    monkeypatch.setattr(auto_sync, "_has_audio_stream", lambda ffmpeg, path: False)
    calls = []

    class SuccessfulPopen:
        def __init__(self, cmd, **kwargs):
            calls.append((cmd, kwargs))
            Path(cmd[-1]).write_bytes(b"media")
            self.stdout = iter([])
            self.returncode = 0

        def wait(self):
            return self.returncode

    monkeypatch.setattr(auto_sync.subprocess, "Popen", SuccessfulPopen)

    output = tmp_path / "synced.mp4"
    auto_sync.mix_and_export("video.mp4", "music.wav", 0.0, str(output), stream_copy=True)

    assert output.read_bytes() == b"media"
    assert calls[0][1]["creationflags"] == 0x08000000
    assert calls[0][1]["stdout"] == subprocess.PIPE
    assert calls[0][1]["stderr"] == subprocess.STDOUT


def create_video(ffmpeg_bin, path, *, with_audio, duration=1.2):
    args = [
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc2=size=160x90:rate=25:duration={duration}",
    ]
    if with_audio:
        args.extend([
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration}",
            "-shortest",
            "-c:a", "aac",
            "-b:a", "96k",
        ])
    else:
        args.append("-an")

    args.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        str(path),
    ])
    run_ffmpeg(ffmpeg_bin, args)


def write_tone_wav(path, *, duration=1.2, tone_start=0.0, tone_duration=0.3, sr=48000):
    sample_count = int(duration * sr)
    samples = np.zeros(sample_count, dtype=np.float32)
    start = int(tone_start * sr)
    end = min(sample_count, start + int(tone_duration * sr))
    t = np.arange(end - start, dtype=np.float32) / sr
    samples[start:end] = 0.8 * np.sin(2 * math.pi * 1000 * t)

    pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm]).ravel()

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sr)
        wav_file.writeframes(stereo.tobytes())


def inspect_media(ffmpeg_bin, path):
    result = subprocess.run(
        [ffmpeg_bin, "-nostdin", "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=30,
    )
    info = result.stdout + result.stderr
    return {
        "has_video": "Video:" in info,
        "has_audio": "Audio:" in info,
        "duration": auto_sync._parse_duration_hms(info),
        "size": Path(path).stat().st_size,
    }


def extract_audio_samples(ffmpeg_bin, media_path, wav_path, sr=48000):
    run_ffmpeg(
        ffmpeg_bin,
        [
            "-y",
            "-i", str(media_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sr),
            "-ac", "1",
            str(wav_path),
        ],
    )
    with wave.open(str(wav_path), "rb") as wav_file:
        frames = wav_file.readframes(wav_file.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def rms_window(samples, sr, start, end):
    window = samples[int(start * sr):int(end * sr)]
    return float(np.sqrt(np.mean(np.square(window)))) if len(window) else 0.0


def partial_outputs_for(path):
    return list(path.parent.glob(f".{path.stem}.*.partial{path.suffix}"))


def test_audio_stream_detection_true_false_and_invalid_input(ffmpeg_bin, tmp_path):
    with_audio = tmp_path / "video with audio.mp4"
    without_audio = tmp_path / "无声 video.mp4"
    corrupted = tmp_path / "corrupted.mp4"

    create_video(ffmpeg_bin, with_audio, with_audio=True)
    create_video(ffmpeg_bin, without_audio, with_audio=False)
    corrupted.write_text("not media", encoding="utf-8")

    assert auto_sync._has_audio_stream(ffmpeg_bin, str(with_audio)) is True
    assert auto_sync._has_audio_stream(ffmpeg_bin, str(without_audio)) is False
    with pytest.raises(auto_sync.AudioStreamDetectionError):
        auto_sync._has_audio_stream(ffmpeg_bin, str(corrupted))


def test_no_audio_export_succeeds_without_original_audio_reference(ffmpeg_bin, tmp_path, monkeypatch):
    video = tmp_path / "源 视频 no audio.mp4"
    music = tmp_path / "替换 music.wav"
    output = tmp_path / "输出 synced 文件.mp4"
    commands = []
    real_popen = subprocess.Popen

    create_video(ffmpeg_bin, video, with_audio=False)
    write_tone_wav(music)

    def recording_popen(cmd, *args, **kwargs):
        commands.append(cmd)
        return real_popen(cmd, *args, **kwargs)

    monkeypatch.setattr(auto_sync.subprocess, "Popen", recording_popen)

    auto_sync.mix_and_export(str(video), str(music), 0.0, str(output), stream_copy=True)

    export_cmd = next(cmd for cmd in commands if "-filter_complex" in cmd)
    filter_graph = export_cmd[export_cmd.index("-filter_complex") + 1]
    assert "[0:a:0]" not in filter_graph
    assert "[1:a:0]" in filter_graph

    media = inspect_media(ffmpeg_bin, output)
    assert media["has_video"] is True
    assert media["has_audio"] is True
    assert media["duration"] > 0
    assert media["size"] > 0


def test_audio_source_export_still_uses_original_audio_mix(ffmpeg_bin, tmp_path, monkeypatch):
    video = tmp_path / "source with audio.mp4"
    music = tmp_path / "music.wav"
    output = tmp_path / "mixed.mp4"
    commands = []
    real_popen = subprocess.Popen

    create_video(ffmpeg_bin, video, with_audio=True)
    write_tone_wav(music)

    def recording_popen(cmd, *args, **kwargs):
        commands.append(cmd)
        return real_popen(cmd, *args, **kwargs)

    monkeypatch.setattr(auto_sync.subprocess, "Popen", recording_popen)

    auto_sync.mix_and_export(str(video), str(music), 0.0, str(output), stream_copy=True)

    export_cmd = next(cmd for cmd in commands if "-filter_complex" in cmd)
    filter_graph = export_cmd[export_cmd.index("-filter_complex") + 1]
    assert "[0:a:0]volume=" in filter_graph
    assert "amix=inputs=2:duration=first" in filter_graph

    media = inspect_media(ffmpeg_bin, output)
    assert media["has_video"] is True
    assert media["has_audio"] is True
    assert media["duration"] > 0
    assert media["size"] > 0


def test_positive_and_negative_offsets_adjust_replacement_music(ffmpeg_bin, tmp_path):
    video = tmp_path / "video no audio.mp4"
    create_video(ffmpeg_bin, video, with_audio=False, duration=1.4)

    positive_music = tmp_path / "positive.wav"
    positive_output = tmp_path / "positive.mp4"
    positive_wav = tmp_path / "positive_out.wav"
    write_tone_wav(positive_music, duration=0.9, tone_start=0.0, tone_duration=0.25)

    auto_sync.mix_and_export(str(video), str(positive_music), 0.30, str(positive_output), stream_copy=True)
    positive_samples = extract_audio_samples(ffmpeg_bin, positive_output, positive_wav)
    assert rms_window(positive_samples, 48000, 0.02, 0.18) < 0.03
    assert rms_window(positive_samples, 48000, 0.34, 0.48) > 0.20

    negative_music = tmp_path / "negative.wav"
    negative_output = tmp_path / "negative.mp4"
    negative_wav = tmp_path / "negative_out.wav"
    write_tone_wav(negative_music, duration=1.0, tone_start=0.35, tone_duration=0.25)

    auto_sync.mix_and_export(str(video), str(negative_music), -0.25, str(negative_output), stream_copy=True)
    negative_samples = extract_audio_samples(ffmpeg_bin, negative_output, negative_wav)
    assert rms_window(negative_samples, 48000, 0.02, 0.07) < 0.03
    assert rms_window(negative_samples, 48000, 0.13, 0.25) > 0.20


def test_failed_export_cleans_partial_and_preserves_existing_destination(ffmpeg_bin, tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    music = tmp_path / "music.wav"
    missing_output = tmp_path / "missing final.mp4"
    existing_output = tmp_path / "existing final.mp4"

    create_video(ffmpeg_bin, video, with_audio=False)
    write_tone_wav(music)
    create_video(ffmpeg_bin, existing_output, with_audio=True)
    existing_bytes = existing_output.read_bytes()

    class FailingPopen:
        def __init__(self, cmd, *args, **kwargs):
            Path(cmd[-1]).write_bytes(b"partial media")
            self.stdout = iter(["forced invalid failure\n"])
            self.returncode = 1

        def wait(self):
            return self.returncode

    monkeypatch.setattr(auto_sync, "get_video_duration", lambda ffmpeg, path: 1.0)
    monkeypatch.setattr(auto_sync, "_has_audio_stream", lambda ffmpeg, path: False)
    monkeypatch.setattr(auto_sync.subprocess, "Popen", FailingPopen)

    with pytest.raises(RuntimeError):
        auto_sync.mix_and_export(str(video), str(music), 0.0, str(missing_output), stream_copy=True)

    assert not missing_output.exists()
    assert partial_outputs_for(missing_output) == []

    with pytest.raises(RuntimeError):
        auto_sync.mix_and_export(str(video), str(music), 0.0, str(existing_output), stream_copy=True)

    assert existing_output.read_bytes() == existing_bytes
    assert partial_outputs_for(existing_output) == []


def test_locale_keys_and_offset_wording_are_consistent():
    en = json.loads(Path("locales/en_US.json").read_text(encoding="utf-8"))
    zh = json.loads(Path("locales/zh_CN.json").read_text(encoding="utf-8"))

    assert set(en) == set(zh)
    assert "delay the replacement music" in en["hint_video_early"].lower()
    assert "trim" in en["hint_music_early"].lower()
    assert "beginning" in en["hint_music_early"].lower()
    assert "starts early" not in en["hint_video_early"].lower()
    assert "starts early" not in en["hint_music_early"].lower()

    assert "延迟" in zh["hint_video_early"]
    assert "替换音乐" in zh["hint_video_early"]
    assert "裁掉" in zh["hint_music_early"]
    assert "开头" in zh["hint_music_early"]
    assert "开始得早" not in zh["hint_video_early"]
    assert "开始得早" not in zh["hint_music_early"]
