"""COMPARATOR-INTEGRITY-1: evidence-integrity tests for the GCC lagfix
audit and the NCC overlap-contract audit.

Hermetic: reads only committed artifacts (frozen benchmark manifest, sealed
v1 raw evidence and records, versioned v2 lagfix artifacts, correction
manifest) — no audio, no comparators, no reruns.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import scoring  # noqa: E402
from experiments.applied_system.final_benchmark import (  # noqa: E402
    _canonical_bytes, verify_frozen_artifact)

RESULTS = ROOT / "experiments/applied_system/final_pack/results"
V1_RAW = RESULTS / "final_comparator_raw.json"
V1_RECORDS = RESULTS / "final_comparator_raw_records"
V2_MANIFEST = RESULTS / "gcc_phat_v2_lagfix_correction_manifest.json"
V2_RAW = RESULTS / "gcc_phat_v2_lagfix_raw.json"
V2_RECORDS = RESULTS / "gcc_phat_v2_lagfix_records"
V2_RESULTS = RESULTS / "gcc_phat_v2_lagfix_results.json"
BENCH_MANIFEST = RESULTS / "final_benchmark_manifest.json"

V1_SYSTEM = "gcc_phat_argmax_v1"
V2_SYSTEM = "gcc_phat_argmax_v2_lagfix"

FROZEN_BASELINES = {
    "final_comparator_raw.json":
        "9ae59821baaf523ad1f89c98b214d565573600d3e23a7c13a2e2f2a9c848dcb3",
    "final_benchmark_results.json":
        "4c6c81dfc8289905286560e8ca2ede71f72c478d6c0fd5c04f68e98061ad6fc2",
    "final_benchmark_reporting_v2.json":
        "b46b9357dca0de9f50d879d9b6dd1952fb7eb21a29581ab8f559b7c7ec5d9acc",
}


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sidecar_digest(path: Path) -> str:
    return path.with_suffix(path.suffix + ".sha256").read_text(
        encoding="utf-8").split()[0]


@pytest.fixture(scope="module")
def bench():
    return load(BENCH_MANIFEST)


@pytest.fixture(scope="module")
def cases(bench):
    return {c["case_id"]: c for c in bench["body"]["cases"]}


@pytest.fixture(scope="module")
def v2_manifest_value():
    value = load(V2_MANIFEST)
    errors = verify_frozen_artifact(value)
    assert errors == []
    assert sha_file(V2_MANIFEST) == sidecar_digest(V2_MANIFEST)
    return value


@pytest.fixture(scope="module")
def v2_raw():
    assert sha_file(V2_RAW) == sidecar_digest(V2_RAW)
    return load(V2_RAW)


@pytest.fixture(scope="module")
def v2_results():
    assert sha_file(V2_RESULTS) == sidecar_digest(V2_RESULTS)
    return load(V2_RESULTS)


# --------------------------------------------------------------------------
# Frozen evidence preservation (no changes to ANY frozen artifact).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name,digest", sorted(FROZEN_BASELINES.items()))
def test_frozen_baselines_byte_identical(name, digest):
    assert sha_file(RESULTS / name) == digest
    assert sidecar_digest(RESULTS / name) == digest


def test_all_200_v1_records_still_match_sealed_assembly():
    raw = load(V1_RAW)
    assert len(raw["records"]) == 200
    for entry in raw["records"]:
        path = ROOT / entry["record_file"]
        assert sha_file(path) == entry["record_sha256"], path.name


def test_v2_evidence_covers_only_the_gcc_system(v2_raw, v2_manifest_value):
    assert v2_raw["status"] == "GCC_PHAT_V2_LAGFIX_RAW"
    assert v2_raw["correction_manifest_freeze_sha256"] == \
        v2_manifest_value["freeze_hash"]
    assert len(v2_raw["records"]) == 50
    for entry in v2_raw["records"]:
        assert V2_SYSTEM in Path(entry["record_file"]).name
        rec = load(ROOT / entry["record_file"])
        assert rec["system"] == V2_SYSTEM
        assert sha_file(ROOT / entry["record_file"]) == \
            entry["record_sha256"]
    expected_dir = "gcc_phat_v2_lagfix_records"
    for entry in v2_raw["records"]:
        path = Path(entry["record_file"])
        assert path.parts[-2] == expected_dir
        assert path.name == f"{V2_SYSTEM}__{path.stem.split('__', 1)[1]}.json"


# --------------------------------------------------------------------------
# Rerun contract: exact frozen input hashes, uniform case set, prediction
# integrity, frozen scoring semantics.
# --------------------------------------------------------------------------

def test_v2_case_set_is_exactly_the_frozen_gcc_eligible_set(cases):
    raw = load(V2_RAW)
    expected = sorted(cid for cid, c in cases.items()
                      if V1_SYSTEM in c["comparator_eligibility"])
    got = sorted(entry["record_file"].split("__", 1)[1][:-5]
                 for entry in raw["records"])
    assert got == expected
    assert len(expected) == 50


def test_v2_records_used_exact_frozen_input_hashes(cases):
    for entry in load(V2_RAW)["records"]:
        rec = load(ROOT / entry["record_file"])
        case = cases[rec["case_id"]]
        assert rec["input_sha256"]["trimmed_input"] == \
            case["trimmed_input_sha256"]
        assert rec["input_sha256"]["reference"] == case["reference_sha256"]


def test_v2_correction_manifest_prediction_was_confirmed_by_the_rerun(
        v2_manifest_value):
    prediction = {r["case_id"]: r for r in
                  v2_manifest_value["body"]["geometry_only_prediction"]
                  ["per_case"]}
    assert len(prediction) == 50
    changed = sorted(cid for cid, r in prediction.items()
                     if r["v2_changes_lag"])
    assert changed == ["final21__positive", "final21__wrong_ref"]
    for entry in load(V2_RAW)["records"]:
        rec = load(ROOT / entry["record_file"])
        pred = prediction[rec["case_id"]]
        ns = rec["native_scores"]
        assert ns["argmax_index"] == pred["argmax_index"]
        assert ns["lag_samples"] == pred["v2_predicted_lag_samples"]
        assert ns["fft_length"] == pred["n_total"]
        # v1 evidence untouched and consistent with the reconstruction
        v1 = load(V1_RECORDS / f"{V1_SYSTEM}__{rec['case_id']}.json")
        assert v1["native_scores"]["lag_samples"] == \
            pred["v1_reported_lag_samples"]
        if not pred["v2_changes_lag"]:
            assert ns["lag_samples"] == v1["native_scores"]["lag_samples"]


def test_v2_scored_results_match_frozen_scoring_contract(cases, v2_results):
    assert v2_results["status"] == "GCC_PHAT_V2_LAGFIX_RESULTS"
    assert v2_results["summary_outcome_counts_by_tolerance"] == {
        "0.05": {"WRONG_ACCEPT": 40, "CORRECT_ACCEPT": 10},
        "0.10": {"WRONG_ACCEPT": 40, "CORRECT_ACCEPT": 10},
        "0.15": {"WRONG_ACCEPT": 40, "CORRECT_ACCEPT": 10},
    }
    # independent re-scoring of every v2 record with the frozen contract
    by_id = {r["case_id"]: r for r in v2_results["per_case"]}
    raw = {load(ROOT / e["record_file"])["case_id"]:
           load(ROOT / e["record_file"]) for e in load(V2_RAW)["records"]}
    for cid, rec in raw.items():
        for tol in (0.05, 0.10, 0.15):
            scored = scoring.score_pair(cases[cid], rec, tol)
            assert by_id[cid]["outcomes"][f"{tol:.2f}"] == scored["outcome"]
            assert by_id[cid]["abs_errors"][f"{tol:.2f}"] == \
                scored["abs_error_s"]


def test_v2_changes_no_outcome_vs_frozen_v1(v2_results, cases):
    """The corrected mapping changes only reported lag magnitudes; every
    outcome at every grid tolerance is identical to the sealed v1 outcome."""
    assert v2_results["comparison_vs_frozen_v1"][
        "outcome_changes_any_tolerance"] == []
    assert v2_results["comparison_vs_frozen_v1"]["changed_lag_records"] == \
        ["final21__positive", "final21__wrong_ref"]
    v1_by_id = {}
    for entry in load(V1_RAW)["records"]:
        rec = load(ROOT / entry["record_file"])
        if rec["system"] == V1_SYSTEM:
            v1_by_id[rec["case_id"]] = rec
    assert len(v1_by_id) == 50
    for entry in load(V2_RAW)["records"]:
        v2rec = load(ROOT / entry["record_file"])
        cid = v2rec["case_id"]
        for tol in (0.05, 0.10, 0.15):
            v1o = scoring.score_pair(cases[cid], v1_by_id[cid], tol)
            v2o = scoring.score_pair(cases[cid], v2rec, tol)
            assert v1o["outcome"] == v2o["outcome"], (cid, tol)
        if cid not in ("final21__positive", "final21__wrong_ref"):
            assert v2rec["native_scores"]["lag_samples"] == \
                v1_by_id[cid]["native_scores"]["lag_samples"]


def test_v2_still_always_output_with_no_invented_threshold():
    for entry in load(V2_RAW)["records"]:
        rec = load(ROOT / entry["record_file"])
        assert rec["decision"] == "ACCEPT"
        assert rec["output_semantics"] == "ALWAYS_OUTPUT"
        assert rec["notes"]["no_threshold_invented"] is True
        assert rec["notes"]["always_output"] is True


# --------------------------------------------------------------------------
# NCC overlap-contract audit reproducibility (no NCC rerun).
# --------------------------------------------------------------------------

RA_MIN_OVERLAP_S = 30.0
NCC_WRONG_POSITIVE_OVERLAPS_S = {
    "final02__positive": 1.675,
    "final18__positive": 1.234,
    "final19__positive": 3.589,
    "final20__positive": 3.522,
    "final23__positive": 4.694,
}


def _usable_overlap_s(offset_s, lx_s, ly_s):
    """Production formula (alignment_engine_v2._usable_overlap_s)."""
    if offset_s >= 0:
        return max(0.0, min(offset_s + ly_s, lx_s) - offset_s)
    return max(0.0, min(ly_s + offset_s, lx_s))


def test_rhythmalign_frozen_minimum_overlap_is_30s():
    sys.path.insert(0, str(ROOT))
    import alignment_engine_v2
    policy = alignment_engine_v2.DecisionPolicy()
    assert policy.min_overlap_s == RA_MIN_OVERLAP_S


def test_ncc_curve_searches_down_to_single_sample_overlaps():
    """Contract fact: NCC's lag axis is the full [-(Ly-1), Lx-1] range with
    per-lag normalization and no duration guard (silence floor only)."""
    from experiments.applied_system.runners import ncc_runner
    import numpy as np
    y_ref = np.zeros(50)
    y_ref[10:] = 1.0
    y_rec = np.zeros(30)
    y_rec[0] = 1.0
    ncc, lags = ncc_runner.ncc_curve(y_rec, y_ref)
    assert lags[0] == -(50 - 1) and lags[-1] == 30 - 1
    # 1-sample overlap at lag -(Ly-1): y_rec[0]*y_ref[49] = 0*0 -> floored;
    # shift to nonzero content: a 1-sample overlap of nonzero samples is a
    # legal candidate scoring exactly +-1.
    y_ref2 = np.zeros(50)
    y_ref2[49] = 2.0
    y_rec2 = np.zeros(30)
    y_rec2[29] = 3.0
    ncc2, lags2 = ncc_runner.ncc_curve(y_rec2, y_ref2)
    k = int(np.argmax(np.abs(ncc2)))
    assert int(lags2[k]) == 29 - 49  # single-sample-overlap lag is the max


def test_ncc_wrong_positive_overlaps_reproduce_from_committed_artifacts(
        v2_manifest_value, cases):
    prediction = {r["case_id"]: r for r in
                  v2_manifest_value["body"]["geometry_only_prediction"]
                  ["per_case"]}
    ncc_outcomes = {}
    for entry in load(V1_RAW)["records"]:
        rec = load(ROOT / entry["record_file"])
        if rec["system"] == "ncc_argmax_v1":
            ncc_outcomes[rec["case_id"]] = rec
    wrong = {}
    correct_min = None
    for cid, rec in ncc_outcomes.items():
        if "__positive" not in cid:
            continue
        p = prediction[cid]
        lx = p["query_samples"] / 48000.0
        ly = p["reference_samples"] / 48000.0
        lag = rec["native_scores"]["lag_samples"] / 48000.0
        ov = _usable_overlap_s(lag, lx, ly)
        outcome = scoring.score_pair(cases[cid], rec, 0.10)["outcome"]
        if outcome == "WRONG_ACCEPT":
            wrong[cid] = round(ov, 3)
        elif outcome == "CORRECT_ACCEPT":
            correct_min = ov if correct_min is None else min(correct_min, ov)
    assert wrong == NCC_WRONG_POSITIVE_OVERLAPS_S
    assert all(ov < RA_MIN_OVERLAP_S for ov in wrong.values())
    assert correct_min >= 60.0   # no correct case anywhere near short
    assert len(wrong) == 5
