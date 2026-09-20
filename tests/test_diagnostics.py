"""CP-1 — cross-platform diagnostics additions (CP0-009) regression tests.

Pins that the diagnostic report carries the fields needed for Linux issue
triage (kernel, libc, Qt platform plugin, FFmpeg H.264/HEVC encoder
inventory), that probing degrades gracefully, and that report generation
works without a QApplication or a live GUI.
"""
import diagnostics


def test_report_contains_platform_fields(tmp_path):
    report = diagnostics.build_diagnostic_report(None, str(tmp_path / "config.json"), str(tmp_path))
    assert "Kernel:" in report
    assert "Libc:" in report
    assert "Qt platform plugin:" in report
    assert "H.264/HEVC encoders:" in report


def test_qt_platform_name_without_application():
    # No QApplication exists in this process: must degrade, never raise.
    value = diagnostics._qt_platform_name()
    assert isinstance(value, str) and value


def test_encoder_inventory_handles_missing_binary():
    assert diagnostics._ffmpeg_encoder_inventory(None) == []
    assert diagnostics._ffmpeg_encoder_inventory("/nonexistent/ffmpeg-binary") == []


def test_encoder_inventory_of_real_bundled_binary():
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pytest.skip("imageio-ffmpeg not available")
    names = diagnostics._ffmpeg_encoder_inventory(path)
    assert names, "bundled FFmpeg must expose at least one H.264/HEVC encoder"
    assert "libx264" in names
    for name in names:
        assert name == "libx264" or name.startswith(("h264_", "hevc_"))
