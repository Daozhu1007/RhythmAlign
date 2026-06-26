import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from importlib import metadata

from app_info import APP_DISPLAY_VERSION, APP_NAME, GITHUB_HOME_URL


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


def build_diagnostic_report(config, user_config_path, base_dir, recent_logs=None):
    qt_version, pyqt_version = _qt_versions()
    imageio_ffmpeg = _imageio_ffmpeg_path()
    path_ffmpeg = shutil.which("ffmpeg")

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
        "",
        "[System]",
        f"OS: {platform.platform()}",
        f"Machine: {platform.machine()}",
        f"Python: {platform.python_version()}",
        f"Qt: {qt_version}",
        f"PyQt: {pyqt_version}",
        f"PyQt-Fluent-Widgets: {_package_version('PyQt-Fluent-Widgets', 'pyqt-fluent-widgets')}",
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
        f"PATH ffmpeg: {path_ffmpeg or 'not found'}",
        f"PATH ffmpeg version: {_probe_executable(path_ffmpeg)}",
    ]

    recent_logs = recent_logs or {}
    if recent_logs:
        lines.extend(["", "[Recent Logs]"])
        for name, text in recent_logs.items():
            lines.extend([f"--- {name} ---", text.strip() or "(empty)"])

    return "\n".join(lines)
