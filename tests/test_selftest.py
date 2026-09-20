"""CP-2 packaged-runtime selftest (--check-only / --validate) tests.

The selftest is the validation entry point CI drives inside the packaged
Linux artifact; these tests pin its behavior in the dev tree on both
platforms (resources, locales, bundled FFmpeg, engine gating, export).
"""
import json
import math
import subprocess
from pathlib import Path
from types import SimpleNamespace

import imageio_ffmpeg
import pytest

import selftest


@pytest.fixture
def ffmpeg_bin():
    return imageio_ffmpeg.get_ffmpeg_exe()


def _decision(status="accepted", reason="ACCEPT_DUAL_FAMILY", offset=0.05, accepted=True):
    return SimpleNamespace(
        status=status, reason_code=reason, offset=offset,
        runtime_s=0.01, accepted=accepted, evidence={},
    )


def _create_video(ffmpeg_bin, path, duration=1.2):
    subprocess.run(
        [ffmpeg_bin, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc2=size=160x90:rate=25:duration={duration}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
         "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", str(path)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
    )


def _create_music(ffmpeg_bin, path, duration=1.2, sr=22050):
    frames = bytearray()
    for i in range(int(duration * sr)):
        value = int(0.6 * 32767 * math.sin(2 * math.pi * 660 * i / sr))
        frames += value.to_bytes(2, "little", signed=True)
    import wave

    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sr)
        fh.writeframes(bytes(frames))


def test_check_only_passes_in_dev_tree():
    exit_code, report = selftest.run(["--check-only"])

    assert exit_code == 0, json.dumps(report, indent=2)
    assert report["ok"] is True
    assert report["checks"]["locale:en_US"]["ok"]
    assert report["checks"]["locale:zh_CN"]["ok"]
    assert report["checks"]["ffmpeg:executes"]["ok"]
    assert report["checks"]["ffmpeg:libx264"]["ok"]
    assert report["checks"]["import:alignment_engine_v2"]["ok"]
    assert report["checks"]["diagnostics:report"]["ok"]


def test_run_rejects_unknown_mode():
    exit_code, report = selftest.run(["--nonsense"])

    assert exit_code == 2
    assert report["ok"] is False


def test_validate_requires_two_media_paths():
    exit_code, report = selftest.run(["--validate", "only-one-path"])

    assert exit_code == 2
    assert report["ok"] is False


def test_validate_full_pipeline_with_stubbed_engine(ffmpeg_bin, tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    music = tmp_path / "music.wav"
    _create_video(ffmpeg_bin, video)
    _create_music(ffmpeg_bin, music)

    monkeypatch.setattr(selftest, "find_offset_v2", lambda v, m: _decision(offset=0.02))
    json_path = tmp_path / "report.json"

    exit_code, report = selftest.run(
        ["--validate", str(video), str(music), "--json", str(json_path)])

    assert exit_code == 0, json.dumps(report, indent=2)
    assert report["engine"]["status"] == "accepted"
    assert report["engine"]["reason_code"] == "ACCEPT_DUAL_FAMILY"
    assert report["export"]["export_duration_s"] == pytest.approx(1.2, abs=1.0)
    assert json_path.exists()
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["ok"] is True


def test_validate_reports_abstain_as_failure(ffmpeg_bin, tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    music = tmp_path / "music.wav"
    _create_video(ffmpeg_bin, video)
    _create_music(ffmpeg_bin, music)

    monkeypatch.setattr(
        selftest, "find_offset_v2",
        lambda v, m: _decision(status="abstained", reason="ABSTAIN_AMBIGUOUS_CLUSTER",
                               offset=None, accepted=False))

    exit_code, report = selftest.run(["--validate", str(video), str(music)])

    assert exit_code == 1
    assert report["ok"] is False
    assert report["checks"]["engine:analysis"]["ok"] is False


def test_validate_expect_offset_gate_fails_on_mismatch(ffmpeg_bin, tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    music = tmp_path / "music.wav"
    _create_video(ffmpeg_bin, video)
    _create_music(ffmpeg_bin, music)

    monkeypatch.setattr(selftest, "find_offset_v2", lambda v, m: _decision(offset=0.02))

    exit_code, report = selftest.run(
        ["--validate", str(video), str(music), "--expect-offset", "3.0"])

    assert exit_code == 1
    assert report["checks"]["engine:expected-offset"]["ok"] is False
