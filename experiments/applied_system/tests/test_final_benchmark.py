"""Frozen final-benchmark integrity tests.

FINAL CONFIRMATORY EVIDENCE GUARDS: these tests assert the population,
separation, freeze, sign, and immutability contracts of the final
benchmark execution. They never execute a comparator and never touch
final media — they verify committed evidence and pure functions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.applied_system import final_benchmark as fb
from experiments.applied_system.scoring import (OUTCOME_CORRECT_ACCEPT,
                                                OUTCOME_SAFE_ABSTAIN,
                                                OUTCOME_WRONG_ACCEPT,
                                                score_pair)
from experiments.applied_system.runners import (gcc_phat_runner,
                                                ncc_runner,
                                                panako_runner,
                                                rhythmalign_runner)

REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "experiments/applied_system/final_pack/results"


@pytest.fixture(scope="module")
def bench_manifest():
    value = json.loads((RESULTS / "final_benchmark_manifest.json")
                       .read_text(encoding="utf-8"))
    assert fb.verify_frozen_artifact(value) == []
    return value["body"]


@pytest.fixture(scope="module")
def bench_scores():
    value = json.loads((RESULTS / "final_benchmark_results.json")
                       .read_text(encoding="utf-8"))
    body = value["body"]
    digest = fb._canonical_bytes and __import__("hashlib").sha256(
        fb._canonical_bytes(body)).hexdigest()
    assert value["benchmark_results_sha256"] == digest
    return body


@pytest.fixture(scope="module")
def raw_records():
    return fb._load_raw_records()


# ---------------------------------------------------------------------------
# exact populations
# ---------------------------------------------------------------------------


def test_exact_population_24_24_2(bench_manifest):
    cases = bench_manifest["cases"]
    pos = [c for c in cases if c["pair_type"] == "POSITIVE"
           and c.get("primary")]
    wrong = [c for c in cases if c["pair_type"] == "WRONG_REFERENCE"]
    reps = [c for c in cases if c.get("reliability_only")]
    assert (len(pos), len(wrong), len(reps)) == (24, 24, 2)
    assert bench_manifest["counts"] == {"primary_positives": 24,
                                        "wrong_reference": 24,
                                        "strict_repeats": 2}


def test_exact_wrong_reference_mapping_frozen_rotation(bench_manifest):
    rotation = {}
    for case in bench_manifest["cases"]:
        if case["pair_type"] != "WRONG_REFERENCE":
            continue
        i = int(case["take"].replace("final", ""))
        rotation[case["take"]] = (i % 10) + 1
        assert case["reference_id"] == f"REF-S{(i % 10) + 1:02d}"
        assert case["source_slot"] != case["reference_id"].replace("REF-", "")
    assert len(rotation) == 24
    assert rotation["final01"] == 2 and rotation["final10"] == 1
    assert rotation["final24"] == 5


def test_strict_repeat_separation(bench_manifest):
    reps = [c for c in bench_manifest["cases"] if c.get("reliability_only")]
    assert sorted(c["take"] for c in reps) == ["repeat01", "repeat02"]
    for case in reps:
        assert case["primary"] is False
        assert case["condition"].startswith("ORDINARY"), case["condition"]
        # no wrong-reference case may exist for a repeat
    wrong_takes = {c["take"] for c in bench_manifest["cases"]
                   if c["pair_type"] == "WRONG_REFERENCE"}
    assert not wrong_takes & {"repeat01", "repeat02"}
    # repeats never enter primary counts in the scored artifact
    scores = json.loads((RESULTS / "final_benchmark_results.json")
                        .read_text(encoding="utf-8"))["body"]
    assert scores["denominators"]["strict_repeats"] == 2
    assert scores["denominators"]["primary_positives"] == 24


def test_kdenlive_valid_scoring_run_set():
    policy = fb._load_json(fb.RUN_POLICY_PATH)
    pair_freeze = fb._load_json(fb.PAIR_FREEZE_PATH)
    assert fb.verify_frozen_artifact(pair_freeze, "pair_freeze_sha256") == []
    pairs = pair_freeze["body"]["pairs"]
    runs = []
    for pid in sorted(pairs):
        rule = policy["rules"].get(pid)
        runs.append(rule["scoring_run"] if rule else pid)
    assert len(runs) == 10 and len(set(runs)) == 10
    assert "pair01r2" in runs and "pair01" not in runs


def test_original_pair01_v1_excluded_from_scoring():
    scores = json.loads(
        (RESULTS / "final_kdenlive_results.json").read_text(encoding="utf-8"))
    body = scores["body"]
    scored_runs = {row["scoring_run"] for row in body["per_pair"]}
    assert "pair01" not in scored_runs and "pair01r2" in scored_runs
    assert body["exclusions"]["pair01_run1"].startswith("void for scoring")
    owner = fb._load_json(fb.OWNER_RUN_FREEZE_PATH)
    assert owner["body"]["void_runs"] == {
        "pair01": "PROCEDURE_V1_TIMELINE_ZERO_LEFT_BOUNDARY"}
    assert "pair01r2" in owner["body"]["valid_scoring_run_set"]


# ---------------------------------------------------------------------------
# comparator / configuration freeze
# ---------------------------------------------------------------------------


def test_comparator_version_and_config_freeze():
    assert fb.SYSTEM_IDS == (
        rhythmalign_runner.SYSTEM_ID,
        gcc_phat_runner.SYSTEM_ID,
        panako_runner.SYSTEM_ID,
        ncc_runner.SYSTEM_ID,
    )
    assert fb.SUBJECT_COMMIT == \
        "3a622fc33af1212178296ad9dad57ce9693eed48"
    assert fb.PANAKO_PINNED_COMMIT == \
        "e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211"
    assert fb.PANAKO_JAR_SHA256 == \
        "77c56eabf93defe64ddddf0fb75478c415dc7b64ddb065b5a34a27f6b9fb2276"
    assert panako_runner.PANAKO_STRATEGY == "OLAF"
    assert fb._production_unchanged() is True


def test_every_record_carries_identical_frozen_input_hashes(
        bench_manifest, raw_records):
    by_case = {c["case_id"]: c for c in bench_manifest["cases"]}
    n = 0
    for record in raw_records:
        case = by_case[record["case_id"]]
        assert record["input_sha256"]["trimmed_input"] == \
            case["trimmed_input_sha256"]
        assert record["input_sha256"]["reference"] == \
            case["reference_sha256"]
        n += 1
    assert n == 200


# ---------------------------------------------------------------------------
# scoring semantics
# ---------------------------------------------------------------------------


def test_scoring_at_50_100_150_ms_boundaries():
    case = {"case_id": "synthetic__positive", "gt_stratum": "EXACT_GT",
            "comparator_eligibility": ["x"], "gt_offset_s": 1.0}
    for tol, outcome in ((0.05, OUTCOME_CORRECT_ACCEPT),
                         (0.10, OUTCOME_CORRECT_ACCEPT),
                         (0.15, OUTCOME_CORRECT_ACCEPT)):
        record = {"system": "x", "case_id": case["case_id"],
                  "decision": "ACCEPT", "predicted_offset_s": 1.0}
        assert score_pair(case, record, tol)["outcome"] == outcome
        # fp guard: exactly-at-tolerance errors never flip from noise
        record["predicted_offset_s"] = 1.0 + tol
        assert score_pair(case, record, tol)["outcome"] == \
            OUTCOME_CORRECT_ACCEPT
        record["predicted_offset_s"] = 1.0 + tol + 1e-9
        assert score_pair(case, record, tol)["outcome"] == OUTCOME_WRONG_ACCEPT
    no_match = {"case_id": "synthetic__wrong", "gt_stratum": "NO_MATCH",
                "comparator_eligibility": ["x"], "gt_offset_s": None}
    record = {"system": "x", "case_id": no_match["case_id"],
              "decision": "ACCEPT", "predicted_offset_s": 0.0}
    assert score_pair(no_match, record)["outcome"] == OUTCOME_WRONG_ACCEPT
    record["decision"] = "ABSTAIN"
    assert score_pair(no_match, record)["outcome"] == OUTCOME_SAFE_ABSTAIN
    record["decision"] = "NO_MATCH"
    assert score_pair(no_match, record)["outcome"] == OUTCOME_SAFE_ABSTAIN


def test_final_tolerance_grid_is_50_100_150():
    assert fb.TOLERANCES == (0.05, 0.1, 0.15)
    assert [fb._tol_key(t) for t in fb.TOLERANCES] == \
        ["0.05", "0.1", "0.15"]


def test_panako_offset_sign_query_minus_match():
    """Offset sign convention (frozen): Query start - Match start, verified
    against the native 13-column output shape transcribed from the pinned
    Panako source."""
    header = ("Index; Total ; Query path;Query start (s);Query stop (s); "
              "Match path;Match id; Match start (s); Match stop (s); "
              "Match score; Time factor (%); Frequency factor(%); "
              "Seconds with match (%)")
    row = ("0 ; 1 ; /tmp/q.wav ; 10.500 ; 61.570 ; /tmp/ref.wav ; 4 ; "
           "4.000 ; 59.120 ; 412 ; 100.000 % ; 100.000 %; 97.41")
    rows = panako_runner.parse_query_output("\n".join([header, row]) + "\n")
    assert rows and rows[0].offset_s() == pytest.approx(10.5 - 4.0)
    assert rows[0].is_valid_match


def test_kdenlive_predicted_offset_is_reference_minus_recording():
    """Sign convention: predicted = (reference.start - recording.start)/fps.
    Positive GT means the reference starts GT seconds into the capture, so
    the reference clip must sit to the RIGHT of the recording clip."""
    parsed = fb.summarize_file if False else None  # guard against drift
    from experiments.applied_system.kdenlive_project_xml import (
        parse_project, project_summary)
    fps = 60
    rec_start, ref_start = 10800, 10800 + 229  # GT 3.8157 s to the right
    xml = f'''<mlt><profile frame_rate_num="{fps}" frame_rate_den="1"/>
      <producer id="p0"><property name="resource">recording.wav</property></producer>
      <producer id="p1"><property name="resource">reference.wav</property></producer>
      <playlist id="pl0"><blank length="10800"/><entry producer="p0" in="0" out="100"/></playlist>
      <playlist id="pl1"><blank length="11029"/><entry producer="p1" in="0" out="100"/></playlist>
      <tractor id="t"><track producer="pl0"/><track producer="pl1"/></tractor>
    </mlt>'''
    summary = project_summary(parse_project(xml.encode()),
                              {"recording": "recording.wav",
                               "reference": "reference.wav"})
    clip_offset = summary["clip_offset_frames"]  # rec - ref = -229
    predicted = -clip_offset / summary["profile_frame_rate"]
    assert predicted == pytest.approx((ref_start - rec_start) / fps)
    assert predicted == pytest.approx(229 / fps)


# ---------------------------------------------------------------------------
# raw-result immutability and aggregation
# ---------------------------------------------------------------------------


def test_raw_assembly_matches_record_files():
    assembly = json.loads((RESULTS / "final_comparator_raw.json")
                          .read_text(encoding="utf-8"))
    assert len(assembly["records"]) == 200
    for entry in assembly["records"]:
        path = REPO / entry["record_file"]
        assert fb._sha256_file(path) == entry["record_sha256"]


def test_freeze_artifact_refuses_modification(tmp_path):
    body = {"a": 1}
    path = tmp_path / "freeze.json"
    fb.freeze_artifact(path, body)
    fb.freeze_artifact(path, {"a": 1})  # identical re-call is a no-op
    with pytest.raises(RuntimeError):
        fb.freeze_artifact(path, {"a": 2})
    tampered = fb._load_json(path)
    tampered["body"]["a"] = 99
    assert fb.verify_frozen_artifact(tampered)


def test_song_bootstrap_uses_source_slots_and_is_deterministic():
    scores = json.loads((RESULTS / "final_benchmark_results.json")
                        .read_text(encoding="utf-8"))["body"]
    boot = scores["song_level_bootstrap"]
    assert boot["unit"] == "source_slot"
    assert boot["replicates"] == fb.BOOTSTRAP_REPLICATES
    assert boot["seed"] == fb.BOOTSTRAP_SEED
    rows = scores["per_case_rows"]
    pos = [r for r in rows if r["pair_type"] == "POSITIVE"
           and not r["reliability_only"]]
    wrong = [r for r in rows if r["pair_type"] == "WRONG_REFERENCE"]
    again = fb._song_bootstrap(pos, wrong)
    assert again == boot  # deterministic from the frozen seed


def test_source_level_table_covers_all_ten_slots(bench_manifest,
                                                 bench_scores):
    slots = {c["source_slot"] for c in bench_manifest["cases"]}
    assert set(bench_scores["source_level_100ms"]) == slots == \
        {f"S{i:02d}" for i in range(1, 11)}
    for slot, tbl in bench_scores["source_level_100ms"].items():
        n_pos = sum(tbl["primary_positives"]
                    .get("rhythmalign_v1_2_0", {}).values())
        n_wrong = sum(tbl["wrong_reference"]
                      .get("rhythmalign_v1_2_0", {}).values())
        expected_pos = sum(1 for c in bench_manifest["cases"]
                           if c["source_slot"] == slot
                           and c["pair_type"] == "POSITIVE"
                           and c.get("primary"))
        expected_wrong = sum(1 for c in bench_manifest["cases"]
                             if c["source_slot"] == slot
                             and c["pair_type"] == "WRONG_REFERENCE")
        assert (n_pos, n_wrong) == (expected_pos, expected_wrong)


# ---------------------------------------------------------------------------
# Kdenlive stratum artifact
# ---------------------------------------------------------------------------


def test_kdenlive_results_internal_consistency():
    doc = json.loads((RESULTS / "final_kdenlive_results.json")
                     .read_text(encoding="utf-8"))
    body = doc["body"]
    import hashlib
    assert doc["kdenlive_results_sha256"] == hashlib.sha256(
        fb._canonical_bytes(body)).hexdigest()
    assert len(body["per_pair"]) == 10
    agg = body["aggregates"]["primary_counts_at_100ms"]
    assert sum(agg.values()) == 10
    assert body["aggregates"]["operator_time"]["timed_runs"] == 9
    assert body["aggregates"]["operator_time"]["untimed_runs"] == \
        ["pair01r2"]
