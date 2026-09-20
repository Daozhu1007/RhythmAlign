"""NIGHTSHIFT-1: desktop-entry install path-torture regression.

Reproduced defect: install-desktop-integration.sh substitutes the install
directory with ``sed "s|__APP_DIR__|$APP_DIR|g"``. In a sed replacement
``&`` means "the whole match", so an install path containing ``&`` (e.g.
".../rock & roll/RhythmAlign") silently produced a corrupted menu entry:

    Exec=/opt/rock __APP_DIR__ roll/RhythmAlign/RhythmAlign

The fix escapes ``&`` and the ``|`` delimiter before substitution. The
script is bash/POSIX, so this test runs only where that is native (Linux
CI; skipped on Windows hosts).
"""

import os
import shutil
import stat
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "packaging", "linux", "install-desktop-integration.sh")
DESKTOP_TEMPLATE = os.path.join(REPO_ROOT, "packaging", "linux", "RhythmAlign.desktop")

posix_only = pytest.mark.skipif(
    os.name != "posix" or shutil.which("bash") is None,
    reason="install-desktop-integration.sh is a bash script (POSIX only)",
)


def _stage_install_tree(tmp_path, install_dir_name):
    app_dir = os.path.join(str(tmp_path), install_dir_name, "RhythmAlign")
    os.makedirs(app_dir)
    shutil.copy(SCRIPT, app_dir)
    shutil.copy(DESKTOP_TEMPLATE, app_dir)
    return app_dir


def _read_installed_desktop(app_dir):
    data_home = os.path.join(app_dir, ".data")
    desktop = os.path.join(data_home, "applications", "rhythmalign.desktop")
    subprocess.run(
        ["bash", os.path.join(app_dir, "install-desktop-integration.sh"), "--install"],
        cwd=app_dir, check=True,
        env=dict(os.environ, XDG_DATA_HOME=data_home),
        stdout=subprocess.DEVNULL,
    )
    with open(desktop, "r", encoding="utf-8") as fh:
        return fh.read()


@posix_only
def test_install_path_with_ampersand_preserved(tmp_path):
    app_dir = _stage_install_tree(tmp_path, "rock & roll")
    content = _read_installed_desktop(app_dir)
    assert "__APP_DIR__" not in content, "placeholder must be fully substituted"
    assert f"Exec={app_dir}/RhythmAlign" in content
    assert f"Icon={app_dir}/assets/logo.png" in content


@posix_only
def test_install_path_with_spaces_preserved(tmp_path):
    app_dir = _stage_install_tree(tmp_path, "my apps dir")
    content = _read_installed_desktop(app_dir)
    assert f"Exec={app_dir}/RhythmAlign" in content


@posix_only
def test_remove_removes_entry(tmp_path):
    app_dir = _stage_install_tree(tmp_path, "plain")
    data_home = os.path.join(str(tmp_path), "plain", ".data")
    desktop = os.path.join(data_home, "applications", "rhythmalign.desktop")
    env = dict(os.environ, XDG_DATA_HOME=data_home)
    subprocess.run(["bash", os.path.join(app_dir, "install-desktop-integration.sh")],
                   cwd=app_dir, check=True, env=env, stdout=subprocess.DEVNULL)
    assert os.path.exists(desktop)
    subprocess.run(["bash", os.path.join(app_dir, "install-desktop-integration.sh"), "--remove"],
                   cwd=app_dir, check=True, env=env, stdout=subprocess.DEVNULL)
    assert not os.path.exists(desktop)
