"""AUDIO-MIX-1: independent gain, EOF, peak, timing and transaction oracles."""
import math
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pytest
from scipy.io import wavfile

import auto_sync
from experiments.audio_progress.media_checks import (
    SR, amplitude, decode, ffmpeg, make_pair, signal_metrics, tone, video_hash,
)


@pytest.mark.parametrize("channels", [1, 2])
@pytest.mark.parametrize("offset", [-0.5, 0, 2])
@pytest.mark.parametrize("original", [True, False])
def test_source_gain_eof_duration_and_video_integrity(tmp_path, channels, offset, original):
    video, music = make_pair(tmp_path, channels=channels, original=original)
    output = tmp_path / "mixed.mp4"
    progress = []
    auto_sync.mix_and_export(str(video), str(music), offset, str(output),
                             vol_original=2, vol_music=0.5,
                             ui_progress_callback=lambda task, pct: progress.append(pct))
    samples = decode(output)
    mapping = 1 / math.sqrt(2) if channels == 1 else 1
    if original:
        # Original gain must not climb when the short reference ends.
        for start, end in ((0.3, 0.8), (2.5, 3.0), (6.0, 7.0)):
            assert amplitude(samples, 440, start, end) / (0.2 * mapping) == pytest.approx(1, abs=0.025)
    begin = max(0, offset) + 0.25
    music_gain = 0.25 if original else 0.5
    assert amplitude(samples, 880, begin, begin + 0.5) / (0.3 * mapping) == pytest.approx(music_gain, abs=0.025)
    if offset > 0:
        assert amplitude(samples, 880, 0.5, 1.5) < 0.002
    assert amplitude(samples, 880, 6, 7) < 0.002
    assert 7.98 <= len(samples) / SR <= 8.05  # AAC frame padding / existing mux priming
    assert video_hash(video) == video_hash(output)
    assert progress == sorted(set(progress))
    assert progress[0] == 0 and progress[-1] == 100
    assert max(progress[:-1]) <= 99
    assert not list(tmp_path.glob(".*.partial*"))


def test_overlap_compatibility_and_old_end_gain_jump(tmp_path):
    video, music = make_pair(tmp_path)
    new = tmp_path / "new.mp4"
    auto_sync.mix_and_export(str(video), str(music), 2, str(new), vol_original=2, vol_music=0.5)
    legacy = ("[0:a]volume=2[a0];[1:a]volume=0.5,adelay=2000:all=1[a1];"
              "[a0][a1]amix=inputs=2:duration=first[out]")
    old = tmp_path / "old.wav"
    ffmpeg(["-y", "-v", "error", "-i", video, "-i", music, "-filter_complex", legacy,
            "-map", "[out]", "-c:a", "pcm_f32le", old])
    before, after = decode(old), decode(new)
    assert amplitude(before, 440, 2.5, 3.5) == pytest.approx(amplitude(after, 440, 2.5, 3.5), abs=0.003)
    assert amplitude(before, 880, 2.5, 3.5) == pytest.approx(amplitude(after, 880, 2.5, 3.5), abs=0.003)
    assert amplitude(before, 440, 6.5, 7.5) / 0.2 == pytest.approx(2, abs=0.005)
    assert amplitude(after, 440, 6.5, 7.5) / 0.2 == pytest.approx(1, abs=0.025)


@pytest.mark.parametrize("original_channels,music_channels", [(1, 2), (2, 1)])
def test_mixed_channel_layouts_preserve_released_overlap_balance(tmp_path, original_channels, music_channels):
    video, music = make_pair(tmp_path, channels=original_channels)
    wavfile.write(music, SR, tone(2, 880, 0.3, music_channels).astype(np.float32))
    new, old = tmp_path / "new.mp4", tmp_path / "old.wav"
    auto_sync.mix_and_export(str(video), str(music), 0, str(new), vol_original=2, vol_music=0.5)
    legacy = ("[0:a]volume=2[a0];[1:a]aformat=channel_layouts=stereo,volume=0.5[a1];"
              "[a0][a1]amix=inputs=2:duration=first[out]")
    ffmpeg(["-y", "-v", "error", "-i", video, "-i", music, "-filter_complex", legacy,
            "-map", "[out]", "-c:a", "pcm_f32le", old])
    before, after = decode(old), decode(new)
    for channel in (0, 1):
        for frequency in (440, 880):
            assert amplitude(before, frequency, 0.5, 1.5, channel) == pytest.approx(
                amplitude(after, frequency, 0.5, 1.5, channel), abs=0.003)
        assert amplitude(after, 440, 6, 7, channel) == pytest.approx(
            amplitude(after, 440, 0.5, 1.5, channel), abs=0.003)


def test_strong_correlated_peaks_use_constant_protection_without_clipping(tmp_path):
    video, music = make_pair(tmp_path, amplitude=0.95)
    wavfile.write(music, SR, tone(2, 440, 0.95).astype(np.float32))
    output = tmp_path / "protected.mp4"
    auto_sync.mix_and_export(str(video), str(music), 2, str(output), vol_original=2, vol_music=2)
    samples = decode(output)
    stats = signal_metrics(samples)
    assert stats["samples_at_or_above_full_scale"] == 0
    assert stats["true_peak_4x"] < 0.9  # -2 dB scan ceiling + bounded AAC overshoot
    gains = [amplitude(samples, 440, a, b) / 0.95 for a, b in ((0.5, 1.5), (6, 7))]
    assert gains[0] == pytest.approx(gains[1], abs=0.01)
    assert gains[0] == pytest.approx(10 ** (-2 / 20) / 1.9, abs=0.02)
    assert amplitude(samples, 440, 2.5, 3.5) / 1.9 == pytest.approx(gains[0], abs=0.01)


@pytest.mark.parametrize("original,offset", [(True, 0), (False, 0), (False, -5), (False, 10)])
def test_silence_and_reference_outside_video_still_finalize(tmp_path, original, offset):
    video, music = make_pair(tmp_path, original=original, amplitude=0, music_amplitude=0)
    output = tmp_path / "silence.mp4"
    auto_sync.mix_and_export(str(video), str(music), offset, str(output))
    samples = decode(output)
    assert np.max(np.abs(samples)) < 1e-7
    assert 7.98 <= len(samples) / SR <= 8.05


def test_software_reencode_still_decodes(tmp_path):
    video, music = make_pair(tmp_path)
    output = tmp_path / "reencoded.mp4"
    auto_sync.mix_and_export(str(video), str(music), 0, str(output), stream_copy=False, bitrate="6000k")
    assert len(decode(output)) >= 8 * SR


@pytest.mark.parametrize("line", ["out_time_us=N/A", "out_time_us=-20", "out_time_us=nan",
                                "out_time_us=1.2", "time=00:00:05.0", "progress=end",
                                "out_time_us=" + "9" * 100, "out_time_us=∞"])
def test_malformed_progress_does_not_change_previous_value(line):
    assert auto_sync._ffmpeg_progress_percent(line, 10, 40) is None


def test_progress_monotonic_bounded_and_unknown_duration():
    assert auto_sync._ffmpeg_progress_percent("out_time_us=2000000", 10, 40) == 40
    assert auto_sync._ffmpeg_progress_percent("out_time_us=999999999", 10, 40) == 99
    for duration in (0, -1, math.nan, math.inf):
        assert auto_sync._ffmpeg_progress_percent("out_time_us=2000000", duration, 0) is None


@pytest.mark.parametrize("failure", ["encode", "rename", "scan"])
def test_failure_never_reports_100_and_preserves_destination(tmp_path, monkeypatch, failure):
    output = tmp_path / "existing.mp4"
    output.write_bytes(b"previous accepted output")
    progress = []
    monkeypatch.setattr(auto_sync, "get_video_duration", lambda *args: 10)
    monkeypatch.setattr(auto_sync, "_has_audio_stream", lambda *args: True)
    monkeypatch.setattr(auto_sync, "_measure_mix_peak", lambda *args: -10)

    class FakeProcess:
        def __init__(self, cmd, **kwargs):
            Path(cmd[-1]).write_bytes(b"partial")
            self.stdout = iter(["out_time_us=8000000\n", "out_time_us=5000000\n", "out_time_us=N/A\n",
                                "out_time_us=99999999\n", "progress=end\n"])
            self.returncode = 1 if failure == "encode" else 0

        def wait(self):
            return self.returncode

    monkeypatch.setattr(auto_sync.subprocess, "Popen", FakeProcess)
    def fail(*args):
        raise OSError("forced failure")
    if failure == "scan":
        monkeypatch.setattr(auto_sync, "_measure_mix_peak", fail)
    if failure == "rename":
        monkeypatch.setattr(auto_sync.os, "replace", fail)
    with pytest.raises((RuntimeError, OSError)):
        auto_sync.mix_and_export("v", "m", 0, str(output), ui_progress_callback=lambda t, p: progress.append(p))
    assert 100 not in progress
    assert progress == sorted(set(progress))
    assert output.read_bytes() == b"previous accepted output"
    assert not list(tmp_path.glob(".*.partial*"))


@pytest.mark.parametrize("peak_text", ["", "Peak level dB: nan", "Peak level dB: inf", "Peak level dB: invalid"])
def test_unknown_peak_fails_closed(monkeypatch, peak_text):
    from types import SimpleNamespace
    monkeypatch.setattr(auto_sync.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stderr=peak_text))
    with pytest.raises(RuntimeError):
        auto_sync._measure_mix_peak("ffmpeg", "v", "m", "graph")


def test_success_progress_is_after_atomic_finalization(tmp_path, monkeypatch):
    video, music = make_pair(tmp_path)
    output = tmp_path / "final.mp4"
    events = []
    def progress(task, pct):
        events.append((pct, output.exists()))
    auto_sync.mix_and_export(str(video), str(music), 0, str(output), ui_progress_callback=progress)
    assert events[-1] == (100, True)
    assert all(pct < 100 for pct, exists in events[:-1])


def test_original_audio_eof_does_not_end_replacement_or_raise_its_gain(tmp_path):
    video, music = make_pair(tmp_path)
    short_audio = tmp_path / "short.wav"
    wavfile.write(short_audio, SR, tone(2, 440, 0.2).astype(np.float32))
    short_video = tmp_path / "short_original.mkv"
    ffmpeg(["-y", "-v", "error", "-i", video, "-i", short_audio,
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "pcm_f32le", short_video])
    wavfile.write(music, SR, tone(4, 880, 0.3).astype(np.float32))
    output = tmp_path / "short_original.mp4"
    auto_sync.mix_and_export(str(short_video), str(music), 0, str(output), vol_original=2, vol_music=0.5)
    samples = decode(output)
    for a, b in ((0.5, 1.5), (2.5, 3.5)):
        assert amplitude(samples, 880, a, b) / 0.3 == pytest.approx(0.25, abs=0.025)
    assert np.max(np.abs(samples[6 * SR:7 * SR])) < 1e-7
    assert 7.98 <= len(samples) / SR <= 8.05


@pytest.mark.parametrize("offset", [0.3125, -0.3125])
def test_impulse_burst_timing_has_no_limiter_or_scan_delay(tmp_path, offset):
    video, music = make_pair(tmp_path, original=False)
    values = tone(2, 880, 0.4)
    values[:int(0.7 * SR)] = 0
    values[int(0.9 * SR):] = 0
    wavfile.write(music, SR, values.astype(np.float32))
    output = tmp_path / "timing.mp4"
    auto_sync.mix_and_export(str(video), str(music), offset, str(output))
    samples = decode(output)
    envelope = np.sqrt(np.mean(samples.reshape(-1, 2) ** 2, axis=1))
    active = np.flatnonzero(envelope > 0.08)
    # Source MP4 export path already has AAC priming/mux padding; no extra DSP delay.
    assert abs(active[0] / SR - (0.7 + offset)) < 0.025
    assert abs(active[-1] / SR - (0.9 + offset)) < 0.025


def test_callback_failure_reaps_ffmpeg_and_removes_partial(tmp_path, monkeypatch):
    video, music = make_pair(tmp_path)
    output = tmp_path / "interrupted.mp4"
    processes = []
    real_popen = auto_sync.subprocess.Popen
    def record(cmd, **kwargs):
        process = real_popen(cmd, **kwargs)
        if "-progress" in cmd:
            processes.append(process)
        return process
    monkeypatch.setattr(auto_sync.subprocess, "Popen", record)
    def fail(task, pct):
        raise RuntimeError("controlled callback failure")
    with pytest.raises(RuntimeError, match="controlled callback"):
        auto_sync.mix_and_export(str(video), str(music), 0, str(output), ui_progress_callback=fail)
    assert processes and all(process.poll() is not None for process in processes)
    assert all(process.stdout.closed for process in processes)
    assert not output.exists() and not list(tmp_path.glob(".*.partial*"))
