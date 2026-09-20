import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from importlib import metadata

from app_info import APP_DISPLAY_VERSION, APP_NAME, GITHUB_HOME_URL


def _alignment_engine_label():
    try:
        from alignment_engine_v2 import ENGINE_LABEL

        return ENGINE_LABEL
    except Exception:
        return "unknown"


def _package_version(*names):
    for name in names:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return "unknown"


def _config_value(config, name):
    item = getattr(config, name, None)
    return getattr(item, "value", None)


def _probe_executable(path):
    if not path:
        return "not found"
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        result = subprocess.run(
            [path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=creationflags,
        )
        first_line = (result.stdout or result.stderr or "").splitlines()
        return first_line[0] if first_line else path
    except Exception as exc:
        return f"{path} ({type(exc).__name__}: {exc})"


def _imageio_ffmpeg_path():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _qt_versions():
    try:
        from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR

        return QT_VERSION_STR, PYQT_VERSION_STR
    except Exception:
        return "unknown", "unknown"


def _qt_platform_name():
    """Name of the Qt platform plugin in use (e.g. windows/xcb/wayland/
    offscreen) — the single most useful field when a Qt port fails to
    start. Reports gracefully when no application exists (headless use)."""
    try:
        from PyQt6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is None:
            return "application not created"
        return app.platformName()
    except Exception as exc:
        return f"unknown ({type(exc).__name__})"


def _libc_label():
    try:
        name, version = platform.libc_ver()
        label = f"{name} {version}".strip()
        return label or "unknown"
    except Exception:
        return "unknown"


_ENCODER_PROBE_TIMEOUT_S = 5


def _ffmpeg_encoder_inventory(path):
    """Relevant H.264/HEVC encoder names an FFmpeg binary reports.

    One ``-encoders`` call with a timeout; any failure degrades to an
    empty list so diagnostics can never crash or hang startup.
    """
    if not path:
        return []
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        result = subprocess.run(
            [path, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=_ENCODER_PROBE_TIMEOUT_S,
            creationflags=creationflags,
        )
    except Exception:
        return []
    names = []
    for line in (result.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and (
            parts[1] == "libx264" or parts[1].startswith(("h264_", "hevc_"))
        ):
            names.append(parts[1])
    return names


def build_diagnostic_report(config, user_config_path, base_dir, recent_logs=None):
    qt_version, pyqt_version = _qt_versions()
    imageio_ffmpeg = _imageio_ffmpeg_path()
    path_ffmpeg = shutil.which("ffmpeg")
    encoders = _ffmpeg_encoder_inventory(imageio_ffmpeg)

    lines = [
        f"{APP_NAME} Diagnostics",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Version: {APP_DISPLAY_VERSION}",
        f"GitHub: {GITHUB_HOME_URL}",
        "",
        "[Runtime]",
        f"Frozen: {bool(getattr(sys, 'frozen', False))}",
        f"Executable: {sys.executable}",
        f"Base dir: {base_dir}",
        f"Working dir: {os.getcwd()}",
        f"User config: {user_config_path}",
        f"Alignment engine: {_alignment_engine_label()}",
        "",
        "[System]",
        f"OS: {platform.platform()}",
        f"Kernel: {platform.release()}",
        f"Machine: {platform.machine()}",
        f"Libc: {_libc_label()}",
        f"Python: {platform.python_version()}",
        f"Qt: {qt_version}",
        f"Qt platform plugin: {_qt_platform_name()}",
        f"PyQt: {pyqt_version}",
        f"Fluent Widgets: {_package_version('PyQt6-Fluent-Widgets', 'PyQt-Fluent-Widgets')}",
        "",
        "[Settings]",
        f"Language: {_config_value(config, 'language')}",
        f"OpenFolder: {_config_value(config, 'open_folder')}",
        f"StreamCopy: {_config_value(config, 'stream_copy')}",
        f"UseGPU: {_config_value(config, 'use_gpu')}",
        f"Bitrate: {_config_value(config, 'bitrate')}",
        f"CheckUpdatesOnStartup: {_config_value(config, 'check_updates_on_startup')}",
        f"IgnoredUpdateTag: {_config_value(config, 'ignored_update_tag')}",
        "",
        "[FFmpeg]",
        f"imageio-ffmpeg path: {imageio_ffmpeg or 'not found'}",
        f"imageio-ffmpeg version: {_probe_executable(imageio_ffmpeg)}",
        f"imageio-ffmpeg H.264/HEVC encoders: {', '.join(encoders) if encoders else 'none detected'}",
        f"PATH ffmpeg: {path_ffmpeg or 'not found'}",
        f"PATH ffmpeg version: {_probe_executable(path_ffmpeg)}",
    ]

    recent_logs = recent_logs or {}
    if recent_logs:
        lines.extend(["", "[Recent Logs]"])
        for name, text in recent_logs.items():
            lines.extend([f"--- {name} ---", text.strip() or "(empty)"])

    return "\n".join(lines)
