"""CP-1 — platform-safe post-export reveal (CP0-001 fix) regression tests.

Pins the contract that export success is independent of shell integration
success: reveal_in_file_manager issues the per-platform reveal command,
returns False instead of raising on failure, and never touches the export
outcome. No real file manager is launched and no graphical desktop is
required.
"""
import os

import pytest

import file_reveal


@pytest.fixture
def popen_calls(monkeypatch):
    calls = []

    def fake_popen(args, *f_args, **kwargs):
        calls.append(list(args))
        return object()

    monkeypatch.setattr(file_reveal.subprocess, "Popen", fake_popen)
    return calls


def test_windows_reveal_selects_file_in_explorer(popen_calls):
    assert file_reveal._reveal_windows("exports/out.mp4") is True
    assert popen_calls == [["explorer", "/select,", os.path.normpath("exports/out.mp4")]]


def test_macos_reveal_reveals_file_in_finder(popen_calls):
    assert file_reveal._platform_revealer("macos")("/tmp/out.mp4") is True
    assert popen_calls == [["open", "-R", "/tmp/out.mp4"]]


def test_linux_reveal_opens_containing_folder(popen_calls, monkeypatch):
    monkeypatch.setattr(file_reveal.shutil, "which", lambda name: "/usr/bin/xdg-open")
    target = "/tmp/exports/out.mp4"
    assert file_reveal._reveal_linux(target) is True
    assert popen_calls == [["/usr/bin/xdg-open", os.path.dirname(os.path.abspath(target))]]


def test_linux_reveal_false_without_xdg_open(monkeypatch):
    monkeypatch.setattr(file_reveal.shutil, "which", lambda name: None)
    assert file_reveal._reveal_linux("/tmp/out.mp4") is False


def test_reveal_never_raises_when_command_missing(popen_calls, monkeypatch):
    def boom(args, *f_args, **kwargs):
        raise FileNotFoundError(args)

    monkeypatch.setattr(file_reveal.subprocess, "Popen", boom)
    assert file_reveal.reveal_in_file_manager("/tmp/out.mp4") is False


def test_reveal_empty_path_is_false():
    assert file_reveal.reveal_in_file_manager("") is False
    assert file_reveal.reveal_in_file_manager(None) is False


def test_platform_dispatch(popen_calls, monkeypatch):
    monkeypatch.setattr(file_reveal.shutil, "which", lambda name: "/usr/bin/xdg-open")
    target = "/tmp/out.mp4"
    assert file_reveal._platform_revealer("linux")(target) is True
    assert popen_calls == [["/usr/bin/xdg-open", os.path.dirname(os.path.abspath(target))]]

    assert file_reveal._platform_revealer("windows")("C:\\tmp\\out.mp4") is True
    assert popen_calls[-1][:2] == ["explorer", "/select,"]


def test_revealer_detection_matches_host():
    expected = "windows" if os.name == "nt" else ("macos" if file_reveal.sys.platform == "darwin" else "linux")
    assert file_reveal._detect_revealer_name() == expected


# --- ui_main integration: export success is independent of reveal success ---

@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _build_sync_interface(qapp, monkeypatch):
    import ui_main
    from PyQt6.QtCore import Qt
    monkeypatch.setattr(ui_main, "i18n", ui_main.I18nManager("en_US"))
    interface = ui_main.SyncInterface("Sync", None)
    interface.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    return interface


def test_export_success_survives_reveal_failure(qapp, monkeypatch):
    import ui_main
    interface = _build_sync_interface(qapp, monkeypatch)
    calls = []

    def failing_reveal(path):
        calls.append(path)
        return False

    monkeypatch.setattr(ui_main, "reveal_in_file_manager", failing_reveal)
    interface.task_finished(True, "/tmp/exports/out_synced.mp4", None, True)
    qapp.processEvents()
    assert calls == ["/tmp/exports/out_synced.mp4"]
    assert interface.btn_start.isEnabled(), "start button must be re-enabled after export"


def test_reveal_skipped_when_open_folder_disabled(qapp, monkeypatch):
    import ui_main
    interface = _build_sync_interface(qapp, monkeypatch)
    calls = []
    monkeypatch.setattr(ui_main, "reveal_in_file_manager", lambda path: calls.append(path) or True)
    interface.task_finished(True, "/tmp/exports/out_synced.mp4", None, False)
    qapp.processEvents()
    assert calls == []
