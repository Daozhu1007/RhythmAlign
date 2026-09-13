"""Research-only test: full shakedown pipeline end-to-end on a reduced
engineering set (three cases, 36 s payloads — the engine's 30 s minimum
overlap makes shorter payloads unrepresentative).

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

This exercises machinery only: manifest freezing, single-pass execution,
byte-identical inputs, deterministic scoring, and the reproducibility
re-run. It asserts nothing about alignment METHOD performance beyond the
exact-DSP runners' known placements.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import manifest as manifest_mod  # noqa: E402
from experiments.applied_system import scoring as scoring_mod  # noqa: E402
from experiments.applied_system import shakedown  # noqa: E402
from experiments.applied_system.manifest import (  # noqa: E402
    STRATUM_EXACT_GT, STRATUM_GT_FAILED, STRATUM_NO_MATCH)

PAYLOAD_S = 36.0


def _mini_case_defs():
    return [
        shakedown.CaseDef(case_id="pos_ordinary", condition="ordinary",
                          payload_song="shakedown_song_a",
                          reference_song="shakedown_song_a"),
        shakedown.CaseDef(case_id="wrong_reference",
                          condition="wrong_reference_no_match",
                          payload_song="shakedown_song_a",
                          reference_song="shakedown_song_b",
                          expected_stratum=STRATUM_NO_MATCH),
        shakedown.CaseDef(case_id="gt_truncated",
                          condition="truncated_capture",
                          payload_song="shakedown_song_a",
                          reference_song="shakedown_song_a",
                          truncate_at_capture_s=14.0,
                          expected_stratum=STRATUM_GT_FAILED),
    ]


@pytest.fixture(scope="module")
def mini_run(tmp_path_factory):
    outdir = tmp_path_factory.mktemp("shakedown_mini")
    results = shakedown.run_shakedown(
        outdir, case_defs=_mini_case_defs(), payload_duration_s=PAYLOAD_S,
        stages=("prepare", "run", "score", "reproduce"))
    return outdir, results


def test_manifest_frozen_and_labeled(mini_run):
    outdir, _ = mini_run
    frozen = json.loads((outdir / "manifest.json").read_text(
        encoding="utf-8"))
    assert manifest_mod.verify_frozen(frozen) == []
    body = frozen["body"]
    assert body["shakedown_only"] == "SHAKEDOWN_ONLY"
    assert body["not_paper_evidence"] == "NOT_PAPER_EVIDENCE"
    strata = {c["case_id"]: c["gt_stratum"] for c in body["cases"]}
    assert strata["gt_truncated"] == STRATUM_GT_FAILED
    assert strata["wrong_reference"] == STRATUM_NO_MATCH
    assert strata["pos_ordinary"] == STRATUM_EXACT_GT


def test_gt_failed_case_has_no_inputs_or_runs(mini_run):
    outdir, _ = mini_run
    body = json.loads((outdir / "manifest.json").read_text(
        encoding="utf-8"))["body"]
    case = next(c for c in body["cases"] if c["case_id"] == "gt_truncated")
    assert case["comparator_eligibility"] == []
    assert case["trimmed_input_path"] is None
    assert not list((outdir / "records").glob("*__gt_truncated.json"))


def test_dsp_runners_recover_known_placement(mini_run):
    outdir, _ = mini_run
    for system in ("gcc_phat_argmax_v1", "ncc_argmax_v1"):
        rec = json.loads((outdir / "records" /
                          f"{system}__pos_ordinary.json").read_text(
            encoding="utf-8"))
        assert rec["decision"] == "ACCEPT"
        assert abs(rec["predicted_offset_s"]
                   - (2.5 - 0.05)) <= 2e-3  # GT minus pre-trim margin


def test_scores_and_labels(mini_run):
    outdir, _ = mini_run
    scores = json.loads((outdir / "scores.json").read_text(encoding="utf-8"))
    assert scores["manifest_hash"]
    outcomes = {(r["case_id"], r["system"]): r["outcome"]
                for r in scores["per_case"]}
    for system in ("gcc_phat_argmax_v1", "ncc_argmax_v1"):
        assert outcomes[("pos_ordinary", system)] == "CORRECT_ACCEPT"
        assert outcomes[("wrong_reference", system)] == "WRONG_ACCEPT"
    # RhythmAlign produced a contract-valid outcome on both scoreable cases
    for case_id in ("pos_ordinary", "wrong_reference"):
        assert outcomes[(case_id, "rhythmalign_v1_2_0")] in (
            "CORRECT_ACCEPT", "WRONG_ACCEPT", "SAFE_ABSTAIN")
    # the GT_FAILED case is reported as a protocol failure, never dropped
    assert outcomes[("gt_truncated", None)] == "GT_FAILED"


def test_every_artifact_labeled_shakedown_only(mini_run):
    outdir, _ = mini_run
    for path in list((outdir / "records").glob("*.json")) + \
            [outdir / "manifest.json", outdir / "scores.json",
             outdir / "panako_status.json"]:
        data = json.loads(path.read_text(encoding="utf-8"))
        labeled = (data.get("shakedown_only") == "SHAKEDOWN_ONLY"
                   or data.get("body", {}).get("shakedown_only")
                   == "SHAKEDOWN_ONLY")
        assert labeled, f"{path.name} lacks shakedown labels"


def test_reproducibility_second_run_identical(mini_run):
    outdir, results = mini_run
    check = results["reproduction"]
    assert check["reproduced"] is True, check["differences"]
    assert check["records_compared"] == 6  # 2 scoreable cases x 3 systems
    saved = json.loads((outdir / "reproduction_check.json").read_text(
        encoding="utf-8"))
    assert saved["reproduced"] is True


def test_prepare_is_deterministic_across_runs(tmp_path_factory):
    """Two independent preparations from the same code + seeds must freeze
    byte-identical manifests."""
    out1 = tmp_path_factory.mktemp("prep_a")
    out2 = tmp_path_factory.mktemp("prep_b")
    for out in (out1, out2):
        shakedown.prepare_stage(out, _mini_case_defs(), PAYLOAD_S)
    h1 = json.loads((out1 / "manifest.json").read_text(
        encoding="utf-8"))["manifest_hash"]
    h2 = json.loads((out2 / "manifest.json").read_text(
        encoding="utf-8"))["manifest_hash"]
    assert h1 == h2
