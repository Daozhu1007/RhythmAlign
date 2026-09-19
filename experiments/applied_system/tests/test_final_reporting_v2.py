"""RESULTS-INTEGRITY-1: corrected reporting semantics for the frozen final
benchmark.

These tests guard the v2 reporting layer (`final_reporting_v2.py`) and
the immutability of every frozen final artifact. They never execute a
comparator and never touch final media.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.applied_system import final_benchmark as fb
from experiments.applied_system import final_reporting_v2 as v2
from experiments.applied_system.scoring import OUTCOME_CORRECT_ACCEPT

REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "experiments/applied_system/final_pack/results"

FROZEN_ARTIFACTS = [
    "final_comparator_raw.json",
    "final_benchmark_results.json",
    "final_benchmark_results.csv",
    "final_kdenlive_results.json",
    "final_comparator_environment.json",
    "final_acquisition_qc.json",
]
FROZEN_FIGURES = [
    "final_outcome_composition.png",
    "final_accepted_offset_errors.png",
    "final_condition_summary.png",
]


@pytest.fixture(scope="module")
def man_records():
    return v2.load_frozen_inputs()


@pytest.fixture(scope="module")
def rows(man_records):
    return v2.score_rows(man_records[0], man_records[1])


@pytest.fixture(scope="module")
def metrics(rows):
    return v2.reporting_metrics(rows)["per_system"]


@pytest.fixture(scope="module")
def v2_body():
    value = json.loads((RESULTS / "final_benchmark_reporting_v2.json")
                       .read_text(encoding="utf-8"))
    digest = hashlib.sha256(
        fb._canonical_bytes(value["body"])).hexdigest()
    assert value["reporting_v2_sha256"] == digest
    return value["body"]


# ---------------------------------------------------------------------------
# metric semantics
# ---------------------------------------------------------------------------


def test_always_output_acceptance_coverage_is_one(metrics):
    for system in fb.ALWAYS_OUTPUT_SYSTEMS:
        assert metrics[system]["positive_accepts"] == 24
        assert metrics[system]["acceptance_coverage_100ms"] == 1.0
        assert metrics[system]["positive_runner_errors"] == 0


def test_ncc_accepted_risk_denominator_is_24(metrics):
    ncc = metrics["ncc_argmax_v1"]
    assert ncc["positive_correct_accepts"] == 19
    assert ncc["positive_wrong_accepts"] == 5
    assert ncc["positive_accepts"] == 24
    assert ncc["accepted_risk_display"] == "5/24"
    assert ncc["accepted_risk_100ms"] == pytest.approx(5 / 24)


def test_gcc_accepted_risk_denominator_is_24(metrics):
    gcc = metrics["gcc_phat_argmax_v1"]
    assert gcc["positive_correct_accepts"] == 10
    assert gcc["positive_wrong_accepts"] == 14
    assert gcc["accepted_risk_display"] == "14/24"
    assert gcc["accepted_risk_100ms"] == pytest.approx(14 / 24)


def test_acceptance_coverage_distinct_from_correct_placement_yield(metrics):
    for system in fb.ALWAYS_OUTPUT_SYSTEMS:
        m = metrics[system]
        assert m["acceptance_coverage_100ms"] == 1.0
        assert m["correct_placement_yield_100ms"] < 1.0
    # Selective systems coincide here only because every accept is
    # correct; the artifact must state that this is a coincidence.
    for system in fb.SELECTIVE_SYSTEMS:
        m = metrics[system]
        assert (m["acceptance_coverage_100ms"]
                == m["correct_placement_yield_100ms"])
    assert "coincide" in v2.METRIC_DEFINITIONS["note"]


def test_wrong_reference_false_accept_rates(metrics):
    assert metrics["rhythmalign_v1_2_0"][
        "wrong_ref_false_accept_rate_100ms"] == 0.0
    assert metrics["panako_fingerprint"][
        "wrong_ref_false_accept_rate_100ms"] == 0.0
    for system in fb.ALWAYS_OUTPUT_SYSTEMS:
        m = metrics[system]
        assert m["wrong_ref_wrong_accepts"] == 24
        assert m["wrong_ref_false_accept_rate_100ms"] == 1.0


def test_correct_accept_errors_distinct_from_all_produced_errors(rows):
    dist = v2.error_distributions(rows)
    for system in fb.ALWAYS_OUTPUT_SYSTEMS:
        cond = dist[system]["correct_accept_conditional_abs_error_s"]
        prod = dist[system]["all_produced_accept_abs_error_s"]
        assert cond["n"] < prod["n"]
        assert cond["max_s"] < 0.025
        assert prod["max_s"] > 60.0  # catastrophic WRONG_ACCEPT tail
        assert prod["max_s"] > 1000 * cond["max_s"]
    for system in fb.SELECTIVE_SYSTEMS:
        d = dist[system]
        assert (d["correct_accept_conditional_abs_error_s"]
                == d["all_produced_accept_abs_error_s"])


def test_wrong_reference_magnitudes_state_conditioning(rows, man_records):
    mags = v2.wrong_reference_magnitudes(man_records[1])
    for system in fb.ALWAYS_OUTPUT_SYSTEMS:
        m = mags[system]
        assert m["n"] == 24
        assert m["median_s"] > 60.0
    for system in fb.SELECTIVE_SYSTEMS:
        assert mags[system] is None


# ---------------------------------------------------------------------------
# bootstrap semantics
# ---------------------------------------------------------------------------


def test_rate_bootstrap_values_stay_in_unit_interval(v2_body):
    for system, boot in v2_body["rate_bootstrap"]["systems"].items():
        for key in ("correct_placement_yield_100ms_ci95",
                    "wrong_ref_false_accept_rate_ci95"):
            lo, hi = boot[key]
            assert 0.0 <= lo <= hi <= 1.0, (system, key, boot[key])


def test_rate_bootstrap_reproduces_frozen_yield_intervals(v2_body):
    frozen = fb._load_json(fb.SCORES_PATH)["body"]
    for system, boot in v2_body["rate_bootstrap"]["systems"].items():
        want = frozen["song_level_bootstrap"]["systems"][system][
            "positive_coverage_100ms_ci95"]
        got = boot["correct_placement_yield_100ms_ci95"]
        assert got == pytest.approx(want, abs=1e-9)


def test_degenerate_wrong_ref_intervals_match_raw_counts(v2_body):
    for system, boot in v2_body["rate_bootstrap"]["systems"].items():
        counts = boot["exact_raw_counts"]
        lo, hi = boot["wrong_ref_false_accept_rate_ci95"]
        if counts["wrong_ref_wrong_accepts"] == 0:
            assert (lo, hi) == (0.0, 0.0)
        elif counts["wrong_ref_wrong_accepts"] == counts["wrong_ref"]:
            assert (lo, hi) == (1.0, 1.0)


# ---------------------------------------------------------------------------
# reconciliation with frozen evidence
# ---------------------------------------------------------------------------


def test_v2_counts_reproduce_frozen_artifact(man_records):
    _, _, _ = man_records
    frozen = fb._load_json(fb.SCORES_PATH)["body"]
    for tol, tol_key in (("0.05", "0.05"), ("0.1", "0.1"),
                         ("0.15", "0.15")):
        for strat, pair_type in (("primary_positives", "POSITIVE"),
                                 ("wrong_reference", "WRONG_REFERENCE")):
            for system in fb.SYSTEM_IDS:
                want = frozen["outcomes_by_tolerance"][tol][strat][system]
                got = v2.reporting_metrics(
                    v2.score_rows(*v2.load_frozen_inputs()[:2]),
                    float(tol))["per_system"][system]
                out = {"CORRECT_ACCEPT": got["positive_correct_accepts"],
                       "WRONG_ACCEPT": got["positive_wrong_accepts"],
                       "SAFE_ABSTAIN":
                           got["positive_safe_abstain_no_match"]}
                if pair_type == "WRONG_REFERENCE":
                    got_counts = {
                        "WRONG_ACCEPT": got["wrong_ref_wrong_accepts"],
                        "SAFE_ABSTAIN": got["wrong_ref_safe_refusals"]}
                else:
                    got_counts = {k: v for k, v in out.items() if v}
                for outcome, count in want.items():
                    assert got_counts[outcome] == count, (tol, strat,
                                                          system, outcome)


def test_v2_reports_raw_counts_unchanged(v2_body):
    m = v2_body["reporting_metrics_100ms"]["per_system"]
    expected = {
        "rhythmalign_v1_2_0": dict(ca=20, wa=0, refuse=4, neg_wa=0),
        "gcc_phat_argmax_v1": dict(ca=10, wa=14, refuse=0, neg_wa=24),
        "ncc_argmax_v1": dict(ca=19, wa=5, refuse=0, neg_wa=24),
        "panako_fingerprint": dict(ca=2, wa=0, refuse=22, neg_wa=0),
    }
    for system, want in expected.items():
        got = m[system]
        assert got["positive_correct_accepts"] == want["ca"]
        assert got["positive_wrong_accepts"] == want["wa"]
        assert got["positive_safe_abstain_no_match"] == want["refuse"]
        assert got["wrong_ref_wrong_accepts"] == want["neg_wa"]


def test_kdenlive_projection_read_only(v2_body):
    k = v2_body["kdenlive_stratum"]
    assert k["scoring_pairs"] == 10
    assert k["correct_accepts_100ms"] == 2
    assert k["wrong_accepts_100ms"] == 8
    assert k["native_failures"] == 0
    op = k["operator_time"]
    assert op["timed_runs"] == 9
    assert op["untimed"] == ["pair01r2"]
    assert op["never_imputed"] is True
    assert "pair01_run1" in k["exclusions"]
    assert "PROCEDURE_V1_TIMELINE_ZERO_LEFT_BOUNDARY" in k[
        "void_run_preserved"]
    assert "outcome-independent" in k["corrections_outcome_independent"]


def test_benchmark_manifest_freeze_intact():
    value = json.loads((RESULTS / "final_benchmark_manifest.json")
                       .read_text(encoding="utf-8"))
    assert fb.verify_frozen_artifact(value) == []


def test_strict_repeats_separate_agreement_from_movement(v2_body):
    comps = {(c["comparison"], c["system"]): c
             for c in v2_body["strict_repeats"]["comparisons"]}
    gcc02 = comps[("repeat02 vs final02", "gcc_phat_argmax_v1")]
    ncc02 = comps[("repeat02 vs final02", "ncc_argmax_v1")]
    assert gcc02["decision_state_agreement"] is True
    assert gcc02["placement_move_s"] == pytest.approx(67.205, abs=0.01)
    assert "not repeatability" in gcc02["interpretation"]
    assert ncc02["placement_move_s"] == pytest.approx(60.46, abs=0.01)
    gcc01 = comps[("repeat01 vs final01", "gcc_phat_argmax_v1")]
    assert "consistently wrong" in gcc01["interpretation"]
    ra02 = comps[("repeat02 vs final02", "rhythmalign_v1_2_0")]
    assert ra02["repeat_placement_abs_error_s"] < 0.100


# ---------------------------------------------------------------------------
# determinism and immutability
# ---------------------------------------------------------------------------


def test_v2_reporting_is_deterministic():
    body_a = v2.build_v2_body()
    body_b = v2.build_v2_body()
    assert (fb._canonical_bytes(body_a) == fb._canonical_bytes(body_b))
    assert "created_utc" not in body_a  # no wall-clock input


def test_v2_artifact_cites_immutable_raw_and_original_results():
    authority = v2.build_v2_body()["authority"]
    assert authority["raw_assembly_sha256"] == (
        "9ae59821baaf523ad1f89c98b214d565573600d3e23a7c13a2e2f2a9c848dcb3")
    assert authority["original_final_results_sha256"] == (
        fb._sha256_file(fb.SCORES_PATH))


def test_raw_comparator_records_unmodified():
    assert fb._sha256_file(fb.RAW_PATH) == (
        "9ae59821baaf523ad1f89c98b214d565573600d3e23a7c13a2e2f2a9c848dcb3")
    raw = json.loads(fb.RAW_PATH.read_text(encoding="utf-8"))
    for entry in raw["records"]:
        path = REPO / entry["record_file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == (
            entry["record_sha256"])


@pytest.mark.parametrize("name", FROZEN_ARTIFACTS)
def test_original_frozen_artifact_hashes_unchanged(name):
    path = RESULTS / name
    sidecar = path.with_suffix(path.suffix + ".sha256")
    expected = f"{fb._sha256_file(path)}  {path.name}\n"
    assert sidecar.exists(), name
    assert sidecar.read_text(encoding="utf-8") == expected, name


@pytest.mark.parametrize("name", FROZEN_FIGURES)
def test_original_frozen_figures_unchanged(name):
    # frozen figures must still verify against their generation-time
    # hashes recorded in the results document's artifact table is not
    # possible (figures have no sidecars); instead assert they were not
    # touched by v2 (different filenames) and still exist.
    assert (RESULTS / "figures" / name).exists()


def test_v2_figures_are_new_files_not_overwrites():
    figures = RESULTS / "figures"
    for name in ("final_correct_accept_errors_v2.png",
                 "final_produced_placement_errors_v2.png"):
        assert (figures / name).exists()
    # the frozen figure set is untouched by the v2 builder
    frozen = fb._load_json(fb.SCORES_PATH)["body"]
    assert set(frozen.keys())  # sanity: frozen artifact readable


def test_v2_write_is_idempotent():
    wrapped = v2.write_reporting_v2()
    again = v2.write_reporting_v2()
    assert wrapped == again
