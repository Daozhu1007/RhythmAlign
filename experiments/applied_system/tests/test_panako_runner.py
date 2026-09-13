"""Research-only tests: Panako runner parser, frozen decision mapping,
offset sign convention, no-match normalization, error handling, and WSL
path translation. SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

The parser/normalization/path tests are pure and run everywhere. The
subprocess-level tests monkeypatch the WSL invocation, so no WSL or
Panako installation is required. The single end-to-end test is skipped
unless a runnable Panako is actually installed in WSL.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system.runners import panako_runner as pr  # noqa: E402
from experiments.applied_system.runners.common import (  # noqa: E402
    DECISION_ACCEPT, DECISION_ERROR, DECISION_NO_MATCH,
    SEMANTICS_SELECTIVE_NO_MATCH)

# Native output shapes transcribed from the pinned Panako source
# (Panako.printQueryResult / printQueryResultHeader, Locale.US decimals,
# ' ; ' separators) and from real captured runs (see
# docs/research/applied_system/PANAKO_INTEGRATION.md).

HEADER = ("Index; Total ; Query path;Query start (s);Query stop (s); "
          "Match path;Match id; Match start (s); Match stop (s); "
          "Match score; Time factor (%); Frequency factor(%); "
          "Seconds with match (%)")


def _match_row(query_start="3.120", match_start="0.670", score="412",
               index="0", total="1", query_path="/tmp/q.wav",
               match_path="/tmp/ref.wav", seconds="97.41"):
    return (f"{index} ; {total} ; {query_path} ; {query_start} ; 61.570 ; "
            f"{match_path} ; 4 ; {match_start} ; 59.120 ; {score} ; "
            f"100.000 % ; 100.000 %; {seconds}")


EMPTY_ROW = ("0 ; 1 ; /tmp/q.wav ; 0.000 ; 0.000 ; null ; null ; -1.000 ; "
             "-1.000 ; -1 ; -1.000 % ; -1.000 %; 0.00")

DIAGNOSTIC = ("Matches 4 (id) Filtered hits: 412 (#) query start 3.12 (s) , "
              "query stop 61.57 (s)")


def _full_stdout(*rows):
    return "\n".join([HEADER, *rows]) + "\n"


# ---------------------------------------------------------------------------
# parser correctness
# ---------------------------------------------------------------------------


def test_parses_header_and_valid_row():
    rows = pr.parse_query_output(_full_stdout(_match_row()))
    assert len(rows) == 1
    r = rows[0]
    assert r.index == 0 and r.total == 1
    assert r.query_path == "/tmp/q.wav"
    assert r.query_start_s == pytest.approx(3.120)
    assert r.query_stop_s == pytest.approx(61.570)
    assert r.match_path == "/tmp/ref.wav"
    assert r.match_id == "4"
    assert r.match_start_s == pytest.approx(0.670)
    assert r.match_stop_s == pytest.approx(59.120)
    assert r.match_score == pytest.approx(412.0)
    assert r.time_factor == pytest.approx(100.0)
    assert r.frequency_factor == pytest.approx(100.0)
    assert r.seconds_with_match == pytest.approx(97.41)
    assert r.is_valid_match is True


def test_parses_empty_result_row_as_invalid():
    rows = pr.parse_query_output(_full_stdout(EMPTY_ROW))
    assert len(rows) == 1
    assert rows[0].is_valid_match is False
    assert rows[0].match_path is None
    assert rows[0].match_start_s == pytest.approx(-1.0)


def test_ignores_diagnostic_lines_and_header():
    stdout = DIAGNOSTIC + "\n" + _full_stdout(_match_row()) + DIAGNOSTIC \
        + "\n"
    rows = pr.parse_query_output(stdout)
    assert len(rows) == 1
    assert rows[0].is_valid_match


def test_no_rows_on_header_only_output():
    assert pr.parse_query_output(HEADER + "\n") == []


def test_malformed_row_skipped_not_fatal():
    # 12 fields (missing last column): not a table row -> ignored.
    malformed = "0 ; 1 ; /tmp/q.wav ; 1.0 ; 2.0 ; /tmp/ref.wav ; 4 ; 0.5 ; " \
                "1.5 ; 42 ; 100.000 % ; 100.000 %"
    rows = pr.parse_query_output(_full_stdout(malformed, _match_row()))
    assert len(rows) == 1
    assert rows[0].is_valid_match


def test_non_numeric_first_field_skipped():
    junk = "x ; y ; a ; b ; c ; d ; e ; f ; g ; h ; i ; j ; k"
    assert pr.parse_query_output(_full_stdout(junk, _match_row()))


# ---------------------------------------------------------------------------
# frozen decision mapping + offset sign convention
# ---------------------------------------------------------------------------


def test_accept_offset_is_query_start_minus_match_start():
    """GT semantics: reference begins `offset` seconds into the query. A
    fingerprint hit at query time t aligns with reference time t-offset,
    so the row must satisfy offset = query_start - match_start."""
    rows = pr.parse_query_output(_full_stdout(_match_row(query_start="3.120",
                                                         match_start="0.670")))
    decision, best, info = pr.normalize_decision(rows)
    assert decision == DECISION_ACCEPT
    assert best.offset_s() == pytest.approx(3.120 - 0.670)
    assert info["n_valid_match_rows"] == 1


def test_accept_selects_highest_native_score_row():
    rows = pr.parse_query_output(_full_stdout(
        _match_row(index="0", query_start="5.000", match_start="2.500",
                   score="37"),
        _match_row(index="1", query_start="5.000", match_start="1.000",
                   score="913")))
    decision, best, info = pr.normalize_decision(rows)
    assert decision == DECISION_ACCEPT
    assert best.index == 1
    assert best.offset_s() == pytest.approx(4.0)
    assert info["n_valid_match_rows"] == 2


def test_no_match_on_native_empty_row_only():
    decision, best, info = pr.normalize_decision(
        pr.parse_query_output(_full_stdout(EMPTY_ROW)))
    assert decision == DECISION_NO_MATCH
    assert best is None
    assert info["n_valid_match_rows"] == 0


def test_no_match_on_zero_rows():
    decision, best, _ = pr.normalize_decision(pr.parse_query_output(HEADER))
    assert decision == DECISION_NO_MATCH
    assert best is None


def test_negative_score_row_is_not_a_match():
    """A row with non-negative start but negative score is not a valid
    match (defensive: never observed natively)."""
    weird = ("0 ; 1 ; /tmp/q.wav ; 1.000 ; 2.000 ; /tmp/ref.wav ; 4 ; "
             "0.500 ; 1.500 ; -1 ; 100.000 % ; 100.000 %; 90.00")
    decision, _, _ = pr.normalize_decision(
        pr.parse_query_output(_full_stdout(weird)))
    assert decision == DECISION_NO_MATCH


# ---------------------------------------------------------------------------
# run_case subprocess plumbing (mocked WSL — no Panako required)
# ---------------------------------------------------------------------------


class _FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _patch_wsl(monkeypatch, scripts):
    """Queue scripted responses by stage: 'store' then 'query'."""
    calls = []

    def fake_bash(script, timeout_s=None):
        calls.append(script)
        stage = "store" if " store " in script else "query"
        payload = scripts[stage]
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(pr, "_wsl_bash", fake_bash)
    return calls


def test_run_case_accept(tmp_path, monkeypatch):
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    in_path.write_bytes(b"x")
    ref_path.write_bytes(b"x")
    scripts = {"store": _FakeProc(0, "stored\n", ""),
               "query": _FakeProc(0, _full_stdout(_match_row(
                   query_start="3.120", match_start="0.670")), "")}
    calls = _patch_wsl(monkeypatch, scripts)
    rec = pr.run_case({"case_id": "c1"}, in_path, ref_path, 48000, None)
    assert rec.decision == DECISION_ACCEPT
    assert rec.predicted_offset_s == pytest.approx(2.450)
    assert rec.output_semantics == SEMANTICS_SELECTIVE_NO_MATCH
    assert rec.runtime_s > 0
    assert rec.notes["no_threshold_invented"] is True
    assert rec.notes["hybrid_refinement"].startswith("none")
    assert rec.native_scores["n_valid_match_rows"] == 1
    assert len(rec.native_scores["match_rows"]) == 1
    assert len(calls) == 2
    # per-run store: fresh LMDB dir passed as a CLI config override
    assert any("OLAF_LMDB_FOLDER=/tmp/panako_runner_store_" in c
               for c in calls)
    assert any("STRATEGY=OLAF" in c for c in calls)
    # query stage removes the store
    assert "rm -rf" in calls[1]


def test_run_case_no_match(tmp_path, monkeypatch):
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    scripts = {"store": _FakeProc(0, "", ""),
               "query": _FakeProc(0, _full_stdout(EMPTY_ROW), "")}
    _patch_wsl(monkeypatch, scripts)
    rec = pr.run_case({"case_id": "c2"}, in_path, ref_path, 48000, None)
    assert rec.decision == DECISION_NO_MATCH
    assert rec.predicted_offset_s is None
    assert rec.native_scores["n_empty_rows"] == 1


def test_run_case_store_failure_is_error(tmp_path, monkeypatch):
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    scripts = {"store": _FakeProc(1, "", "java: command not found"),
               "query": _FakeProc(0, "", "")}
    _patch_wsl(monkeypatch, scripts)
    rec = pr.run_case({"case_id": "c3"}, in_path, ref_path, 48000, None)
    assert rec.decision == DECISION_ERROR
    assert "exit 1" in rec.native_scores["error"]
    assert "java: command not found" in rec.notes["stderr_tail"]


def test_run_case_query_failure_is_error(tmp_path, monkeypatch):
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    scripts = {"store": _FakeProc(0, "", ""),
               "query": _FakeProc(2, "", "LMDB error")}
    _patch_wsl(monkeypatch, scripts)
    rec = pr.run_case({"case_id": "c4"}, in_path, ref_path, 48000, None)
    assert rec.decision == DECISION_ERROR
    assert "LMDB error" in rec.notes["stderr_tail"]


def test_run_case_timeout_is_error(tmp_path, monkeypatch):
    import subprocess as sp
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    scripts = {"store": _FakeProc(0, "", ""),
               "query": sp.TimeoutExpired(cmd="panako", timeout=1)}
    _patch_wsl(monkeypatch, scripts)
    rec = pr.run_case({"case_id": "c5"}, in_path, ref_path, 48000, None)
    assert rec.decision == DECISION_ERROR
    assert "timed out" in rec.native_scores["error"]


def test_run_case_garbage_output_is_error(tmp_path, monkeypatch):
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    scripts = {"store": _FakeProc(0, "", ""),
               "query": _FakeProc(0, "complete garbage, no table", "")}
    _patch_wsl(monkeypatch, scripts)
    rec = pr.run_case({"case_id": "c6"}, in_path, ref_path, 48000, None)
    # Header-less garbage parses as zero rows -> native-looking no rows.
    # Zero rows is the native no-match shape; only MALFORMED ROWS (integer
    # index fields with broken numerics) are parse errors.
    assert rec.decision == DECISION_NO_MATCH


def test_run_case_broken_numeric_row_is_error(tmp_path, monkeypatch):
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    broken = "0 ; 1 ; /q ; not_a_number ; 2.0 ; /r ; 4 ; 0.5 ; 1.5 ; 42 ; " \
             "100.0 % ; 100.0 %; 90.0"
    scripts = {"store": _FakeProc(0, "", ""),
               "query": _FakeProc(0, _full_stdout(broken), "")}
    _patch_wsl(monkeypatch, scripts)
    rec = pr.run_case({"case_id": "c7"}, in_path, ref_path, 48000, None)
    assert rec.decision == DECISION_ERROR
    assert "parse failure" in rec.native_scores["error"]


# ---------------------------------------------------------------------------
# path translation
# ---------------------------------------------------------------------------


def test_windows_path_translation():
    assert pr.to_wsl_path("D:\\Code\\RhythmAlign\\a.wav") == \
        "/mnt/d/Code/RhythmAlign/a.wav"
    assert pr.to_wsl_path("c:\\x\\y z\\a b.wav") == "/mnt/c/x/y z/a b.wav"


def test_posix_path_passthrough():
    assert pr.to_wsl_path("/mnt/d/Code/R/a.wav") == "/mnt/d/Code/R/a.wav"
    assert pr.to_wsl_path("/tmp/q.wav") == "/tmp/q.wav"


def test_quote_escaping():
    assert pr._sh_quote("a'b.wav") == "'a'\\''b.wav'"


# ---------------------------------------------------------------------------
# end-to-end (only when Panako is actually installed in WSL)
# ---------------------------------------------------------------------------


def test_end_to_end_known_offset():
    if not pr.panako_available():
        pytest.skip("Panako not installed in WSL on this machine")
    import numpy as np
    import soundfile as sf
    from experiments.applied_system import synth_payload
    fs = 48_000
    song = synth_payload.render_song_a(duration_s=25.0)
    lead = np.random.default_rng(7).normal(0, 3e-4, int(1.25 * fs))
    rec = np.concatenate([lead, song])
    with pytest.MonkeyPatch.context() as mp_ctx:
        tmp = Path(__file__).parent / "_panako_e2e_tmp"
        tmp.mkdir(exist_ok=True)
        in_path = tmp / "e2e_in.wav"
        ref_path = tmp / "e2e_ref.wav"
        sf.write(str(in_path), rec, fs, subtype="PCM_16")
        sf.write(str(ref_path), song, fs, subtype="PCM_16")
        record = pr.run_case({"case_id": "e2e"}, in_path, ref_path, fs,
                             None)
        for p in (in_path, ref_path):
            p.unlink(missing_ok=True)
        tmp.rmdir()
    assert record.decision == DECISION_ACCEPT
    assert record.predicted_offset_s == pytest.approx(1.25, abs=0.2)
