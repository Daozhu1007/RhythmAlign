"""NIGHTSHIFT-1 hardening regression tests.

Closes the four false-confidence gaps identified by the mutation review
(docs/NIGHTSHIFT1-LINUX-BETA-REDTEAM.md §16):

1. ``ffmpeg_has_encoder`` membership semantics were never pinned (every
   export-path test monkeypatches it). The unpinned mutation
   ``return bool(ffmpeg_supported_encoders(...))`` would resurrect the
   exact CP-2 bug: a GPU toggle that selects a predictably-broken NVENC
   path.
2. ``_make_temporary_output_path``'s contract (hidden dot-prefix,
   ``.partial`` infix, same-directory placement — required for atomic
   ``os.replace`` — extension required) was only implicitly pinned via
   glob-based assertions that stay green if creation and cleanup mutate
   consistently.
3. ``BaseMediaWorker.run``'s exception path (worker crash → ``_fail`` →
   ``finished_signal(False, "", "")``) was unpinned; deleting the except
   block passed the entire suite.
4. ``task_finished(False, ...)`` must re-enable the start button and
   surface a failure, not only the success path was pinned.
"""

import pytest

import auto_sync
import ui_main


# ---------------------------------------------------------------------------
# 1. GPU: real name-matching semantics of ffmpeg_has_encoder
# ---------------------------------------------------------------------------


@pytest.fixture
def inventory(monkeypatch):
    names = {"libx264", "libx264rgb"}
    monkeypatch.setattr(auto_sync, "ffmpeg_supported_encoders", lambda _bin: set(names))
    return names


def test_has_encoder_true_only_for_listed_encoder(inventory):
    assert auto_sync.ffmpeg_has_encoder("/bin/ffmpeg", "libx264") is True


def test_has_encoder_false_for_present_but_unlisted_encoder(inventory):
    # A binary that lists libx264 must NOT be treated as NVENC-capable.
    assert auto_sync.ffmpeg_has_encoder("/bin/ffmpeg", "h264_nvenc") is False


def test_has_encoder_false_on_empty_probe_result(monkeypatch):
    monkeypatch.setattr(auto_sync, "ffmpeg_supported_encoders", lambda _bin: set())
    assert auto_sync.ffmpeg_has_encoder("/bin/ffmpeg", "libx264") is False


# ---------------------------------------------------------------------------
# 2. Temp output path contract
# ---------------------------------------------------------------------------


def test_temp_path_is_hidden_partial_sibling(tmp_path):
    target = tmp_path / "movie synced.mp4"
    output_path, temp_path = auto_sync._make_temporary_output_path(str(target))
    assert output_path == str(target)
    name = temp_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    assert name.startswith("."), "temp must be hidden (dot-prefix)"
    assert ".partial" in name, "temp must carry the .partial infix"
    assert name.endswith(".mp4"), "temp must keep the media extension"
    assert temp_path.rsplit("\\", 1)[0].rsplit("/", 1)[0] == str(tmp_path) or \
        temp_path.startswith(str(tmp_path)), "temp must live in the output directory"


def test_temp_path_requires_extension(tmp_path):
    with pytest.raises(ValueError):
        auto_sync._make_temporary_output_path(str(tmp_path / "noext"))


def test_temp_path_names_are_unique(tmp_path):
    _, a = auto_sync._make_temporary_output_path(str(tmp_path / "out.mp4"))
    _, b = auto_sync._make_temporary_output_path(str(tmp_path / "out.mp4"))
    assert a != b


# ---------------------------------------------------------------------------
# 3. Worker crash reports failure, never success
# ---------------------------------------------------------------------------


def test_worker_exception_emits_failure_signal(tmp_path, monkeypatch, qapp=None):
    worker = ui_main.SyncWorker({
        'v_path': str(tmp_path / "in.mp4"),
        'm_path': str(tmp_path / "music.wav"),
        'save_path': str(tmp_path / "out.mp4"),
        'orig_vol': 1.0, 'music_vol': 0.5, 'manual_offset': 0.0,
        'use_gpu': False, 'bitrate': '10000k',
        'open_folder': False, 'stream_copy': True,
    })
    events = []
    worker.finished_signal.connect(lambda *a: events.append(a))

    def boom(v, m):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(ui_main, "find_offset_v2", boom)
    worker.run()  # driven synchronously, mirroring the RA-1.2D test style

    assert events, "finish signal must fire even on worker crash"
    ok, path, abstain = events[-1]
    assert ok is False, "a crashed run must never report success"
    assert path == "" and abstain == "", "crash is not an abstention"


# ---------------------------------------------------------------------------
# 4. task_finished(False) re-enables the start button (offscreen Qt)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _build_sync_interface(qapp, monkeypatch):
    from PyQt6.QtCore import Qt
    monkeypatch.setattr(ui_main, "i18n", ui_main.I18nManager("en_US"))
    interface = ui_main.SyncInterface("Sync", None)
    interface.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    interface.btn_start.setEnabled(False)
    return interface


def test_failure_completion_reenables_start_button(qapp, monkeypatch):
    interface = _build_sync_interface(qapp, monkeypatch)
    interface.task_finished(False, "", "", False)
    qapp.processEvents()
    assert interface.btn_start.isEnabled(), (
        "start button must be re-enabled after a failed task, or the UI "
        "dead-ends until restart")


def test_export_failure_completion_reenables_start_button(qapp, monkeypatch):
    interface = _build_sync_interface(qapp, monkeypatch)
    interface.task_finished(False, "/tmp/exports/x.mp4", "", True)
    qapp.processEvents()
    assert interface.btn_start.isEnabled()
