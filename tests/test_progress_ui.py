"""PROGRESS-1: truthful stages, restart/terminal states and bilingual controls."""
import inspect

import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

import alignment_engine_v2 as eng
import auto_sync
import ui_main


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("locale", ["zh_CN", "en_US"])
@pytest.mark.parametrize("kind", [ui_main.SyncInterface, ui_main.AnalyzeInterface])
def test_busy_progress_no_eta_and_clean_restart(qapp, monkeypatch, locale, kind):
    monkeypatch.setattr(ui_main, "i18n", ui_main.I18nManager(locale))
    interface = kind(None)
    interface.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    interface.resize(900, 800)
    interface.show()
    qapp.processEvents()
    try:
        interface.update_progress("Export", "100")
        interface.reset_progress(ui_main.i18n.tr("stage_extract_video"))
        assert interface.prog_bar.value() == 0
        assert interface.busy_prog_bar.isStarted()
        assert interface.prog_bar.isHidden()
        for stage in ("stage_extract_music", "stage_load_audio", "stage_alignment"):
            interface.update_progress(ui_main.i18n.tr(stage), ui_main.INDETERMINATE_PROGRESS)
            qapp.processEvents()
            text = interface.prog_lbl.text()
            assert "%" not in text
            assert "ETA" not in text and "剩余" not in text
            assert ui_main.i18n.tr(stage) in text
            assert interface.prog_lbl.width() >= interface.prog_lbl.fontMetrics().horizontalAdvance(text)
        assert not hasattr(interface, "busy_eta_timer")
        interface.update_progress("Export", "67")
        assert not interface.busy_prog_bar.isStarted()
        interface.update_progress("Export", "20")
        assert interface.prog_bar.value() == 67
        for value in ("N/A", "nan", "-1", "101", "", "2.5", "9" * 100, "１２"):
            interface.update_progress("Malformed", value)
            assert interface.prog_bar.value() == 67
            assert "Malformed" not in interface.prog_lbl.text()
    finally:
        interface.close()


@pytest.mark.parametrize("locale", ["zh_CN", "en_US"])
@pytest.mark.parametrize("outcome", ["success", "abstain", "error"])
@pytest.mark.parametrize("kind", [ui_main.SyncInterface, ui_main.AnalyzeInterface])
def test_terminal_restores_controls_and_animation(qapp, monkeypatch, locale, outcome, kind):
    monkeypatch.setattr(ui_main, "i18n", ui_main.I18nManager(locale))
    for name in ("success", "warning", "error"):
        monkeypatch.setattr(ui_main.InfoBar, name, lambda **kw: None)
    interface = kind(None)
    try:
        interface.set_task_running(True)
        interface.reset_progress("Working")
        assert not interface.btn_vid.isEnabled()
        if kind is ui_main.SyncInterface:
            assert not interface.orig_slider.isEnabled()
            interface.task_finished(outcome == "success", "out.mp4",
                                    "safe stop" if outcome == "abstain" else "", False)
            assert interface.btn_start.isEnabled()
            assert interface.orig_slider.isEnabled()
            assert interface.prog_bar.value() == (100 if outcome == "success" else 0)
        else:
            interface.analysis_finished(outcome == "success", 2,
                                        eng.ABSTAIN_AMBIGUOUS_CLUSTER if outcome == "abstain" else "")
            assert interface.btn_analyze.isEnabled()
            assert interface.prog_bar.value() == 0
            if outcome == "abstain":
                assert interface.result_display.text() == ui_main.i18n.tr("analyze_abstained")
        assert interface.btn_vid.isEnabled() and interface.btn_mus.isEnabled()
        assert interface.acceptDrops()
        assert not interface.busy_prog_bar.isStarted()
        assert "ETA" not in interface.prog_lbl.text() and "剩余" not in interface.prog_lbl.text()
    finally:
        interface.close()


def test_eta_code_and_probe_are_removed():
    assert not hasattr(auto_sync, "estimate_analysis_duration")
    assert not hasattr(ui_main, "format_eta")
    assert not hasattr(ui_main, "parse_eta_seconds")
    assert not hasattr(ui_main.BaseMediaWorker, "_estimate_initial_eta")
    assert "eta" not in inspect.getsource(ui_main.BaseMediaWorker).lower()


def test_real_entry_stages_are_observational_and_temporary_files_cleaned(monkeypatch, tmp_path):
    monkeypatch.setattr(eng.tempfile, "gettempdir", lambda: str(tmp_path))
    stages, paths = [], []
    def extract(ffmpeg, source, destination, sr):
        from pathlib import Path
        Path(destination).write_bytes(b"fixture")
        paths.append(destination)
    monkeypatch.setattr(eng, "extract_audio", extract)
    monkeypatch.setattr(eng.librosa, "load", lambda *a, **kw: (np.zeros(100), 22050))
    decision = object()
    monkeypatch.setattr(eng, "decide_alignment", lambda *a, **kw: decision)
    assert eng.find_offset_v2("video", "music", stage_callback=stages.append) is decision
    assert stages == ["stage_extract_video", "stage_extract_music", "stage_load_audio", "stage_alignment"]
    assert not list(tmp_path.iterdir())
    assert eng.find_offset_v2("video", "music") is decision
    assert not list(tmp_path.iterdir())


def test_worker_stages_have_two_fields_and_never_fabricate_analysis_percentage(monkeypatch):
    decision = eng.AlignmentDecision("accepted", 2, eng.ACCEPT_DUAL_FAMILY, {}, [], {}, 0)
    def find(video, music, stage_callback):
        stage_callback("stage_alignment")
        return decision
    monkeypatch.setattr(ui_main, "find_offset_v2", find)
    worker = ui_main.AnalyzeWorker("video", "music")
    events = []
    worker.progress_signal.connect(lambda *args: events.append(args))
    worker.run()
    assert all(len(event) == 2 for event in events)
    assert all(pct in (ui_main.INDETERMINATE_PROGRESS, ui_main.FINISHED_PROGRESS) for _, pct in events)
