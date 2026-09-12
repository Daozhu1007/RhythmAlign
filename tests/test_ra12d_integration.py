"""RA-1.2D product-path integration tests.

Proves product behavior of the Engine v2 default path, media-independent:
SyncWorker / AnalyzeWorker are driven synchronously with a mocked
find_offset_v2 and a mocked mix_and_export (no media, no FFmpeg).
The legacy auto_sync.find_offset() must never be reachable from the
GUI default path.
"""
import json
from pathlib import Path

import pytest

import auto_sync
import alignment_engine_v2 as eng
import ui_main


OFFSET_ZERO_DUIHUA = 12.4923  # RA-1.2B/C real-corpus headline value


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_decision(status, offset=None, reason_code=eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS):
    return eng.AlignmentDecision(
        status=status, offset=offset, reason_code=reason_code,
        evidence={"engine": "test"}, clusters=[], policy={}, runtime_s=0.0,
    )


def accepted(offset, reason_code=eng.ACCEPT_PRIMARY_WITH_CORROBORATION):
    return make_decision(eng.STATUS_ACCEPTED, offset=offset, reason_code=reason_code)


def abstained(reason_code=eng.ABSTAIN_AMBIGUOUS_CLUSTER):
    return make_decision(eng.STATUS_ABSTAINED, offset=None, reason_code=reason_code)


class SignalCapture:
    def __init__(self, signal):
        self.events = []
        signal.connect(lambda *args: self.events.append(args))

    def last(self):
        return self.events[-1] if self.events else None


def make_sync_worker(tmp_path, manual_offset=0.25):
    kwargs = {
        'v_path': str(tmp_path / "input video.mp4"),
        'm_path': str(tmp_path / "music.wav"),
        'save_path': str(tmp_path / "output synced.mp4"),
        'orig_vol': 1.2, 'music_vol': 0.7,
        'manual_offset': manual_offset,
        'use_gpu': False, 'bitrate': '10000k',
        'open_folder': False, 'stream_copy': True,
    }
    worker = ui_main.SyncWorker(kwargs)
    return worker, kwargs


def patch_product_path(monkeypatch, decision, export_recorder=None):
    """Replace the Engine v2 entry point and the export call in ui_main."""
    monkeypatch.setattr(ui_main, "find_offset_v2", lambda v, m: decision)
    calls = []

    def fake_mix_and_export(**kwargs):
        calls.append(kwargs)
        if export_recorder is not None:
            export_recorder.append(kwargs)

    monkeypatch.setattr(ui_main, "mix_and_export", fake_mix_and_export)
    return calls


# ---------------------------------------------------------------------------
# A. accepted decision: SyncWorker uses the v2 offset, exports exactly once
# ---------------------------------------------------------------------------


def test_accepted_decision_exports_once_with_v2_offset(tmp_path, monkeypatch):
    calls = patch_product_path(monkeypatch, accepted(OFFSET_ZERO_DUIHUA))
    worker, kwargs = make_sync_worker(tmp_path)
    finished = SignalCapture(worker.finished_signal)

    worker.run()

    assert len(calls) == 1
    assert calls[0]['offset'] == pytest.approx(OFFSET_ZERO_DUIHUA)
    assert finished.last() == (True, kwargs['save_path'], "")


def test_manual_fine_adjustment_semantics_preserved(tmp_path, monkeypatch):
    """final_offset = automatic offset + manual fine-adjustment is the
    mix_and_export contract; the worker must pass both values through."""
    calls = patch_product_path(monkeypatch, accepted(9.9149,
                                                     eng.ACCEPT_DUAL_FAMILY))
    worker, kwargs = make_sync_worker(tmp_path, manual_offset=-0.12)

    worker.run()

    assert len(calls) == 1
    assert calls[0]['offset'] == pytest.approx(9.9149)
    assert calls[0]['manual_offset'] == pytest.approx(-0.12)
    # volume presets / stream-copy / GPU / bitrate passthrough
    assert calls[0]['vol_original'] == pytest.approx(1.2)
    assert calls[0]['vol_music'] == pytest.approx(0.7)
    assert calls[0]['stream_copy'] is True
    assert calls[0]['use_gpu'] is False
    assert calls[0]['bitrate'] == '10000k'


def i18n_safe(key, *args):
    return ui_main.i18n.tr(key, *args)


def test_accepted_logs_report_engine_and_evidence_path(tmp_path, monkeypatch):
    patch_product_path(monkeypatch, accepted(OFFSET_ZERO_DUIHUA))
    worker, _ = make_sync_worker(tmp_path)
    logs = SignalCapture(worker.log_signal)

    worker.run()

    joined = "\n".join(msg for msg, _ in logs.events)
    assert "Engine v2" in joined
    assert i18n_safe("evidence_path_primary_corroboration") in joined
    assert "+12.4923" in joined  # selected-offset line, locale-independent
    assert "运行报错" not in joined and "Execution error" not in joined


# ---------------------------------------------------------------------------
# B. abstained decision: no export, no output, safe failure report
# ---------------------------------------------------------------------------


def test_abstained_decision_never_exports(tmp_path, monkeypatch):
    calls = patch_product_path(monkeypatch, abstained(
        eng.ABSTAIN_AMBIGUOUS_CLUSTER))
    worker, kwargs = make_sync_worker(tmp_path)
    finished = SignalCapture(worker.finished_signal)
    logs = SignalCapture(worker.log_signal)

    worker.run()

    assert calls == []  # export NEVER started
    ok, path, message = finished.last()
    assert ok is False
    assert path == ""
    assert message  # user-facing safe-stop explanation present
    assert message == ui_main.abstain_user_message(abstained(
        eng.ABSTAIN_AMBIGUOUS_CLUSTER))
    joined = "\n".join(msg for msg, _ in logs.events)
    assert eng.ABSTAIN_AMBIGUOUS_CLUSTER in joined  # machine-readable reason
    assert i18n_safe("log_abstain_no_export") in joined
    assert "运行报错" not in joined and "Execution error" not in joined


def test_abstained_decision_generates_no_output_file(tmp_path, monkeypatch):
    patch_product_path(monkeypatch, abstained(
        eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS))
    worker, kwargs = make_sync_worker(tmp_path)

    worker.run()

    assert not Path(kwargs['save_path']).exists()
    assert not list(Path(tmp_path).glob("*.mp4"))


def test_abstained_progress_reports_safe_stop_not_generic_failure(
        tmp_path, monkeypatch):
    patch_product_path(monkeypatch, abstained())
    worker, _ = make_sync_worker(tmp_path)
    progress = SignalCapture(worker.progress_signal)

    worker.run()

    last_task = progress.last()[0]
    assert last_task == i18n_safe("task_abstained")


# ---------------------------------------------------------------------------
# C/D. AnalyzeWorker accept/abstain
# ---------------------------------------------------------------------------


def test_analyze_worker_accept_reports_offset(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_main, "find_offset_v2",
                        lambda v, m: accepted(OFFSET_ZERO_DUIHUA))
    worker = ui_main.AnalyzeWorker("v.mp4", "m.wav")
    result = SignalCapture(worker.result_signal)

    worker.run()

    ok, offset, reason_code = result.last()
    assert ok is True
    assert offset == pytest.approx(OFFSET_ZERO_DUIHUA)
    assert reason_code == ""


def test_analyze_worker_abstain_shows_no_fake_numeric_offset(
        tmp_path, monkeypatch):
    monkeypatch.setattr(ui_main, "find_offset_v2",
                        lambda v, m: abstained(eng.ABSTAIN_AMBIGUOUS_CLUSTER))
    worker = ui_main.AnalyzeWorker("v.mp4", "m.wav")
    result = SignalCapture(worker.result_signal)

    worker.run()

    ok, offset, reason_code = result.last()
    assert ok is False
    assert reason_code == eng.ABSTAIN_AMBIGUOUS_CLUSTER
    # The UI layer renders an explicit undetermined state, never a number:
    display_text = i18n_safe("analyze_abstained")
    assert "+0.0000" not in display_text and "0.0000" not in display_text
    hint = ui_main.analyze_abstain_hint_text(reason_code)
    assert "+0.0000" not in hint


# ---------------------------------------------------------------------------
# E. no legacy fallback in the default path
# ---------------------------------------------------------------------------


def test_ui_module_no_longer_binds_legacy_find_offset():
    assert not hasattr(ui_main, "find_offset")


def test_gui_default_path_never_calls_legacy_find_offset(tmp_path, monkeypatch):
    def legacy_must_not_run(*args, **kwargs):
        raise AssertionError(
            "legacy auto_sync.find_offset was called by the GUI default path")

    monkeypatch.setattr(auto_sync, "find_offset", legacy_must_not_run)
    monkeypatch.setattr(ui_main, "find_offset", legacy_must_not_run,
                        raising=False)
    calls = patch_product_path(monkeypatch, accepted(OFFSET_ZERO_DUIHUA))
    worker, _ = make_sync_worker(tmp_path)

    worker.run()  # must not raise via legacy_must_not_run

    assert len(calls) == 1


# ---------------------------------------------------------------------------
# F. reason-code handling: stable, categorized, machine-readable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code,locale_key", [
    (eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS, "abstain_reason_insufficient_evidence"),
    (eng.ABSTAIN_PRIMARY_NOT_CORROBORATED, "abstain_reason_insufficient_evidence"),
    (eng.ABSTAIN_AMBIGUOUS_CLUSTER, "abstain_reason_ambiguous"),
    (eng.ABSTAIN_INSUFFICIENT_OVERLAP, "abstain_reason_insufficient_overlap"),
])
def test_every_reason_code_maps_to_a_stable_user_category(
        reason_code, locale_key):
    assert ui_main.ABSTAIN_REASON_KEYS[reason_code] == locale_key
    hint = ui_main.analyze_abstain_hint_text(reason_code)
    assert i18n_safe(locale_key) in hint
    assert reason_code not in hint  # users see categories, logs see codes


def test_ambiguity_and_insufficient_evidence_differ_stably():
    logs_a = _abstain_log_run(eng.ABSTAIN_AMBIGUOUS_CLUSTER)
    logs_b = _abstain_log_run(eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS)
    # deterministic across repeated invocations
    assert _abstain_log_run(eng.ABSTAIN_AMBIGUOUS_CLUSTER) == logs_a
    # distinct user-facing categories
    assert ui_main.analyze_abstain_hint_text(
        eng.ABSTAIN_AMBIGUOUS_CLUSTER) != ui_main.analyze_abstain_hint_text(
        eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS)
    # but the shared safe-stop framing is identical
    assert i18n_safe("log_abstain_no_export") in logs_a
    assert i18n_safe("log_abstain_no_export") in logs_b


def _abstain_log_run(reason_code):
    worker = ui_main.AnalyzeWorker("v.mp4", "m.wav")
    logs = SignalCapture(worker.log_signal)
    worker._on_abstained(abstained(reason_code))
    return tuple(msg for msg, _ in logs.events)


# ---------------------------------------------------------------------------
# G. locale completeness for the new product strings
# ---------------------------------------------------------------------------


def test_locale_files_cover_engine_v2_product_strings():
    en = json.loads(Path("locales/en_US.json").read_text(encoding="utf-8"))
    zh = json.loads(Path("locales/zh_CN.json").read_text(encoding="utf-8"))

    assert set(en) == set(zh)
    required = {
        "log_engine_v2", "log_alignment_accepted", "log_evidence_path",
        "evidence_path_dual_family", "evidence_path_primary_corroboration",
        "log_abstained", "log_abstain_reason", "log_abstain_no_export",
        "task_abstained", "analyze_abstained", "abstain_headline",
        "abstain_safe_stop", "abstain_reason_insufficient_evidence",
        "abstain_reason_ambiguous", "abstain_reason_insufficient_overlap",
        "abstain_suggestion",
    }
    assert required <= set(en)
    # the misleading manual-fallback wording must be gone
    assert "err_low_confidence" not in en
    assert "err_manual_fallback" not in en
    # fine-adjust wording must present the slider as an add-on, not a fallback
    assert "auto alignment" in en["lbl_offset"].lower()
    assert "自动对齐" in zh["lbl_offset"]


def test_analyze_accept_hint_for_accepted_offset_unchanged(tmp_path, monkeypatch):
    """The accepted-path hint semantics (positive => delay) are preserved."""
    monkeypatch.setattr(ui_main, "find_offset_v2",
                        lambda v, m: accepted(2.0))
    worker = ui_main.AnalyzeWorker("v.mp4", "m.wav")
    result = SignalCapture(worker.result_signal)

    worker.run()

    ok, offset, _ = result.last()
    assert ok is True and offset > 0
    assert "delay" in i18n_safe("hint_video_early", abs(offset)).lower() or \
        "延迟" in i18n_safe("hint_video_early", abs(offset))
