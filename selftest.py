"""Packaged-build validation entry point (CP-2).

Invoked from ui_main's entry point before any QApplication is constructed:

    RhythmAlign --check-only
    RhythmAlign --validate VIDEO MUSIC [--json PATH] [--expect-offset SECONDS]

--check-only verifies the packaged runtime (bundled resources, locales,
FFmpeg discovery/execution, imports, diagnostics). --validate additionally
runs the real Engine v2 analysis on the given media pair and performs a
stream-copy export, then validates the produced media. The JSON report is
written to --json PATH when given and printed best-effort to stdout (which
is None for windowed executables launched without a console).
"""

import json
import os
import platform
import sys
import tempfile

import app_info
from alignment_engine_v2 import find_offset_v2

_MODES = ("--check-only", "--validate")
_EXPECT_OFFSET_TOLERANCE_S = 0.1


def _resource_base():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


class _Report:
    def __init__(self):
        self.checks = {}

    def add(self, name, ok, detail=""):
        self.checks[name] = {"ok": bool(ok), "detail": str(detail)}
        return bool(ok)

    @property
    def ok(self):
        return all(check["ok"] for check in self.checks.values())


def _check_resources(report):
    base = _resource_base()
    for rel in ("assets/logo.ico", "assets/logo.png", "config.json", "bundled_update.json"):
        report.add(f"resource:{rel}", os.path.exists(os.path.join(base, rel)), base)

    for locale in ("en_US", "zh_CN"):
        path = os.path.join(base, "locales", f"{locale}.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                texts = json.load(fh)
            ok = bool(texts) and "app_title" in texts
            report.add(f"locale:{locale}", ok, f"{len(texts)} keys")
        except Exception as exc:
            report.add(f"locale:{locale}", False, repr(exc))


def _check_ffmpeg(report):
    try:
        import imageio_ffmpeg

        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        report.add("ffmpeg:discovery", False, repr(exc))
        return None

    if not report.add("ffmpeg:discovery", bool(ffmpeg_bin) and os.path.exists(ffmpeg_bin), ffmpeg_bin or "not found"):
        return None

    executable = os.access(ffmpeg_bin, os.X_OK) if os.name != "nt" else True
    report.add("ffmpeg:executable-bit", executable, ffmpeg_bin)

    version = "unavailable"
    try:
        import subprocess

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        result = subprocess.run(
            [ffmpeg_bin, "-version"],
            capture_output=True, text=True, errors="replace", timeout=10,
            creationflags=creationflags,
        )
        first_line = (result.stdout or "").splitlines()
        version = first_line[0] if first_line else f"returncode {result.returncode}"
        report.add("ffmpeg:executes", result.returncode == 0, version)
    except Exception as exc:
        report.add("ffmpeg:executes", False, repr(exc))

    try:
        from diagnostics import _ffmpeg_encoder_inventory

        encoders = _ffmpeg_encoder_inventory(ffmpeg_bin)
        report.add("ffmpeg:libx264", "libx264" in encoders, ", ".join(encoders))
    except Exception as exc:
        report.add("ffmpeg:libx264", False, repr(exc))

    return ffmpeg_bin


def _check_imports(report, ffmpeg_bin):
    try:
        from alignment_engine_v2 import ENGINE_LABEL

        report.add("import:alignment_engine_v2", bool(ENGINE_LABEL), ENGINE_LABEL)
    except Exception as exc:
        report.add("import:alignment_engine_v2", False, repr(exc))

    try:
        from auto_sync import ffmpeg_has_encoder, mix_and_export

        nvenc = bool(ffmpeg_bin) and ffmpeg_has_encoder(ffmpeg_bin, "h264_nvenc")
        report.add("import:auto_sync", True, f"nvenc={nvenc}")
    except Exception as exc:
        report.add("import:auto_sync", False, repr(exc))

    for module_name, attr in (
        ("update_checker", "current_platform"),
        ("file_reveal", "reveal_in_file_manager"),
        ("diagnostics", "build_diagnostic_report"),
    ):
        try:
            module = __import__(module_name, fromlist=[attr])
            report.add(f"import:{module_name}", hasattr(module, attr), attr)
        except Exception as exc:
            report.add(f"import:{module_name}", False, repr(exc))


def _check_diagnostics(report):
    try:
        from diagnostics import build_diagnostic_report

        stub_config = type("StubConfig", (), {})()
        for name in ("language", "open_folder", "stream_copy", "use_gpu",
                     "bitrate", "check_updates_on_startup", "ignored_update_tag"):
            setattr(stub_config, name, type("Item", (), {"value": None})())
        report_text = build_diagnostic_report(stub_config, "selftest", _resource_base())
        report.add("diagnostics:report", len(report_text.splitlines()) >= 10,
                   f"{len(report_text.splitlines())} lines")
    except Exception as exc:
        report.add("diagnostics:report", False, repr(exc))


def _run_checks():
    report = _Report()
    report.add("runtime:frozen", True, bool(getattr(sys, "frozen", False)))
    report.add("runtime:platform", True,
               f"{sys.platform} {platform.machine()} libc={platform.libc_ver()[1] or 'unknown'}")
    _check_resources(report)
    ffmpeg_bin = _check_ffmpeg(report)
    _check_imports(report, ffmpeg_bin)
    _check_diagnostics(report)
    return report


def _run_validation(report, video_path, music_path, expect_offset=None):
    """Returns a structured (engine, export) info pair for the JSON report."""
    from auto_sync import get_video_duration, mix_and_export

    engine_info = {}
    export_info = {}

    try:
        decision = find_offset_v2(video_path, music_path)
    except Exception as exc:
        report.add("engine:analysis", False, repr(exc))
        return engine_info, export_info

    engine_info = {
        "status": decision.status,
        "reason_code": decision.reason_code,
        "offset": decision.offset,
        "runtime_s": round(decision.runtime_s, 3),
    }
    report.add("engine:analysis", decision.accepted,
               f"status={decision.status} reason={decision.reason_code} "
               f"offset={decision.offset} runtime={decision.runtime_s:.2f}s")
    if not decision.accepted:
        return engine_info, export_info

    if expect_offset is not None:
        delta = abs((decision.offset or 0.0) - expect_offset)
        engine_info["expected_offset"] = expect_offset
        engine_info["offset_delta"] = round(delta, 6)
        report.add("engine:expected-offset", delta <= _EXPECT_OFFSET_TOLERANCE_S,
                   f"expected={expect_offset} got={decision.offset} delta={delta:.4f}")

    out_dir = tempfile.mkdtemp(prefix="ra_selftest_")
    output_path = os.path.join(out_dir, "selftest_synced.mp4")
    try:
        mix_and_export(
            video_path=video_path, music_path=music_path, offset=decision.offset,
            output_path=output_path, stream_copy=True, tr=lambda key, *args: key,
        )
        produced = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        report.add("export:produced", produced, f"{output_path}")

        duration_ok = False
        duration_detail = "export missing"
        if os.path.exists(output_path):
            ffmpeg_bin = find_ffmpeg_bin()
            source_duration = get_video_duration(ffmpeg_bin, video_path)
            export_duration = get_video_duration(ffmpeg_bin, output_path)
            duration_ok = abs(export_duration - source_duration) < 1.0
            duration_detail = f"source={source_duration:.2f}s export={export_duration:.2f}s"
            export_info = {
                "path_size": os.path.getsize(output_path),
                "source_duration_s": round(source_duration, 3),
                "export_duration_s": round(export_duration, 3),
            }
        report.add("export:duration", duration_ok, duration_detail)

        leftovers = [name for name in os.listdir(out_dir) if ".partial" in name]
        report.add("export:no-partial-leftovers", not leftovers, ", ".join(leftovers))
    except Exception as exc:
        report.add("export:produced", False, repr(exc))
    finally:
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            if not os.listdir(out_dir):
                os.rmdir(out_dir)
        except OSError:
            pass
    return engine_info, export_info


def find_ffmpeg_bin():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run(argv):
    """Execute the selftest. Returns (exit_code, report_dict)."""
    mode = argv[0] if argv else "--check-only"
    if mode not in _MODES:
        return 2, {"ok": False, "error": f"unknown mode {mode!r}; expected one of {_MODES}"}

    positional, json_path, expect_offset = [], None, None
    rest = argv[1:]
    while rest:
        arg = rest.pop(0)
        if arg == "--json":
            json_path = rest.pop(0)
        elif arg == "--expect-offset":
            expect_offset = float(rest.pop(0))
        else:
            positional.append(arg)

    if mode == "--validate" and len(positional) != 2:
        return 2, {"ok": False, "error": "--validate requires VIDEO and MUSIC paths"}

    report = _run_checks()
    engine_info, export_info = {}, {}
    if mode == "--validate":
        engine_info, export_info = _run_validation(
            report, positional[0], positional[1], expect_offset)

    result = {
        "app": app_info.APP_NAME,
        "version": app_info.APP_VERSION,
        "mode": mode,
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "checks": report.checks,
        "engine": engine_info,
        "export": export_info,
        "ok": report.ok,
    }

    if json_path:
        try:
            with open(json_path, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
        except Exception as exc:
            result["ok"] = False
            result["json_write_error"] = repr(exc)

    _print_result(result)
    return (0 if result["ok"] else 1), result


def _print_result(result):
    try:
        print(json.dumps(result, indent=2))
    except Exception:
        pass  # windowed executables may have no stdout at all


def main(argv):
    exit_code, _ = run(argv)
    return exit_code
