"""Structured evidence travels from either worker to Copy diagnostics."""
import json
from types import SimpleNamespace

import alignment_engine_v2 as eng
import diagnostics
import ui_main


def test_worker_retains_abstention_candidates_and_clears_stale_result(monkeypatch):
    decision=eng.AlignmentDecision("abstained",None,
        eng.ABSTAIN_PRIMARY_NOT_CORROBORATED,
        {"families":{"pcen_hpss":{"z":67.124}}},
        [{"representative_offset_s":10.96,"case_a_failed_checks":["tonal_z"],
          "case_b_failed_checks":["onset_missing"]}],{},0)
    worker=ui_main.AnalyzeWorker("unused.wav","unused.wav")
    monkeypatch.setattr(worker,"_run_find_offset",lambda:decision)
    worker.run()
    assert worker.alignment_decision==decision.as_dict()
    def fail():
        raise RuntimeError("decode failure")
    monkeypatch.setattr(worker,"_run_find_offset",fail)
    worker.run()
    assert worker.alignment_decision is None


def test_diagnostic_report_contains_parseable_candidate_evidence(monkeypatch):
    monkeypatch.setattr(diagnostics,"_probe_executable",lambda p:"test")
    decision={"status":"abstained","offset":None,
        "reason_code":eng.ABSTAIN_PRIMARY_NOT_CORROBORATED,
        "clusters":[{"offset_s":10.96,"case_b_failed_checks":["onset_missing"]}]}
    report=diagnostics.build_diagnostic_report(SimpleNamespace(),"test","test",
        alignment_decisions={"Analyze":decision})
    payload=report.split("--- Analyze ---\n")[1]
    assert json.loads(payload)==decision
    assert "[Alignment Decisions]" in report


def test_copy_diagnostics_includes_decisions_from_both_pages(monkeypatch):
    captured={}
    def report(*args,**kwargs):
        captured.update(kwargs)
        return "diagnostic text"
    monkeypatch.setattr(ui_main,"build_diagnostic_report",report)
    monkeypatch.setattr(ui_main.QApplication,"clipboard",lambda:SimpleNamespace(setText=lambda _:None))
    monkeypatch.setattr(ui_main.InfoBar,"success",lambda **kwargs:None)
    sync,analyze={"reason_code":"sync"},{"reason_code":"analyze"}
    window=SimpleNamespace(sync_interface=SimpleNamespace(worker=SimpleNamespace(alignment_decision=sync)),
        analyze_interface=SimpleNamespace(worker=SimpleNamespace(alignment_decision=analyze)),
        _collect_recent_logs=lambda:{})
    ui_main.RhythmAlignApp.copy_diagnostics(window)
    assert captured["alignment_decisions"]=={"Sync":sync,"Analyze":analyze}
