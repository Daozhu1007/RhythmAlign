"""CP-2 GPU-setting safety tests.

The "Use GPU" toggle must never select a path that predictably fails:
exports fall back to software encoding when the bundled FFmpeg binary does
not expose h264_nvenc (Linux beta), while Windows behavior is unchanged.
"""
from pathlib import Path

import pytest

import auto_sync
from ui_main import gpu_switch_should_be_enabled


@pytest.fixture
def ffmpeg_bin():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


@pytest.fixture(autouse=True)
def clear_encoder_cache():
    auto_sync._encoder_inventory_cache.clear()
    yield
    auto_sync._encoder_inventory_cache.clear()


def _run_export(tmp_path, monkeypatch, *, use_gpu, nvenc_available=None):
    """Drive mix_and_export's re-encode path with stubbed probes.

    Returns (commands, logs) captured from the fake FFmpeg run.
    """
    commands = []
    logs = []

    class RecordingPopen:
        def __init__(self, cmd, **kwargs):
            commands.append(cmd)
            Path(cmd[-1]).write_bytes(b"media")
            self.stdout = iter([])
            self.returncode = 0

        def wait(self):
            return 0

    monkeypatch.setattr(auto_sync.subprocess, "Popen", RecordingPopen)
    monkeypatch.setattr(auto_sync.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(auto_sync, "get_video_duration", lambda ffmpeg, path: 1.0)
    monkeypatch.setattr(auto_sync, "_has_audio_stream", lambda ffmpeg, path: False)
    if nvenc_available is not None:
        monkeypatch.setattr(auto_sync, "ffmpeg_has_encoder", lambda ffmpeg, name: nvenc_available)

    auto_sync.mix_and_export(
        video_path="video.mp4", music_path="music.wav", offset=0.0,
        output_path=str(tmp_path / "out.mp4"),
        use_gpu=use_gpu, bitrate="10000k", stream_copy=False,
        tr=lambda key, *args: key, ui_log_callback=logs.append,
    )
    return commands, logs


def test_bundled_binary_reports_libx264(ffmpeg_bin):
    # True on both platform bundles (Windows v7.1 and Linux v7.0.2 static).
    assert "libx264" in auto_sync.ffmpeg_supported_encoders(ffmpeg_bin)


def test_encoder_probe_degrades_to_empty_set_on_missing_binary(tmp_path):
    missing = str(tmp_path / "no-such-ffmpeg")
    assert auto_sync.ffmpeg_supported_encoders(missing) == set()
    assert auto_sync.ffmpeg_has_encoder(missing, "h264_nvenc") is False


def test_encoder_probe_is_cached_per_binary(ffmpeg_bin, monkeypatch):
    calls = []
    real_run = auto_sync.subprocess.run

    def counting_run(*args, **kwargs):
        calls.append(args)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(auto_sync.subprocess, "run", counting_run)

    auto_sync.ffmpeg_supported_encoders(ffmpeg_bin)
    auto_sync.ffmpeg_supported_encoders(ffmpeg_bin)

    assert len(calls) == 1


def test_export_uses_nvenc_when_use_gpu_and_available(tmp_path, monkeypatch):
    commands, _ = _run_export(tmp_path, monkeypatch, use_gpu=True, nvenc_available=True)

    cmd = commands[0]
    assert "h264_nvenc" in cmd
    assert "libx264" not in cmd


def test_export_falls_back_to_software_when_nvenc_missing(tmp_path, monkeypatch):
    commands, logs = _run_export(tmp_path, monkeypatch, use_gpu=True, nvenc_available=False)

    cmd = commands[0]
    assert "libx264" in cmd
    assert "h264_nvenc" not in cmd
    # The user must be told the GPU path was skipped.
    assert "log_gpu_fallback" in logs


def test_export_default_path_never_probes_encoders(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("encoder probe must not run when use_gpu is False")

    monkeypatch.setattr(auto_sync, "ffmpeg_has_encoder", forbidden)

    commands, logs = _run_export(tmp_path, monkeypatch, use_gpu=False)

    assert "libx264" in commands[0]
    assert "log_gpu_fallback" not in logs


def test_gpu_switch_decision_matrix():
    # Windows keeps the v1.2.0 behavior unconditionally.
    assert gpu_switch_should_be_enabled("win32", False) is True
    assert gpu_switch_should_be_enabled("win32", True) is True
    # Other platforms only offer the toggle when NVENC really exists.
    assert gpu_switch_should_be_enabled("linux", False) is False
    assert gpu_switch_should_be_enabled("linux", True) is True
    assert gpu_switch_should_be_enabled("darwin", False) is False


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_setting_interface_gpu_card_follows_availability(qapp, monkeypatch):
    import ui_main

    monkeypatch.setattr(ui_main, "gpu_switch_available", lambda: False)
    settings = ui_main.SettingInterface()
    try:
        assert not settings.gpu_switch.isEnabled()
        assert settings.gpu_switch.contentLabel.text().strip()
    finally:
        settings.deleteLater()

    monkeypatch.setattr(ui_main, "gpu_switch_available", lambda: True)
    settings = ui_main.SettingInterface()
    try:
        assert settings.gpu_switch.isEnabled()
    finally:
        settings.deleteLater()
