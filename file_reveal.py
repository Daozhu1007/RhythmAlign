"""Best-effort "show the exported file in the desktop file manager".

Export success must never depend on shell integration success (CP0-001):
a failed reveal returns False, never raises, and never invalidates the
exported media. Windows behavior (selecting the file in Explorer) is
preserved unchanged.
"""
import os
import shutil
import subprocess
import sys


def _reveal_windows(path):
    # Exit code is meaningless (Explorer usually exits 1 on success);
    # issuing the command is the best observable signal.
    subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    return True


def _reveal_macos(path):
    subprocess.Popen(["open", "-R", path])
    return True


def _reveal_linux(path):
    opener = shutil.which("xdg-open")
    if not opener:
        return False
    # No cross-desktop "select file" standard: open the containing folder.
    subprocess.Popen([opener, os.path.dirname(os.path.abspath(path))])
    return True


def _detect_revealer_name():
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    return "linux"


_REVEALERS = {
    "windows": _reveal_windows,
    "macos": _reveal_macos,
    "linux": _reveal_linux,
}


def _platform_revealer(name=None):
    return _REVEALERS[name or _detect_revealer_name()]


def reveal_in_file_manager(path):
    """Reveal ``path`` in the platform file manager. Returns True when a
    reveal/open command was issued, False otherwise. Never raises."""
    if not path:
        return False
    try:
        return bool(_platform_revealer()(path))
    except Exception:
        return False
