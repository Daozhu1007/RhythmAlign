"""Research-only tests for the fresh acoustic pilot harness."""
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from experiments.applied_system import pilot_harness as ph
from experiments.applied_system.runners import common


def _plan():
    return {"takes": [
        {"take": "take01", "device": "D1", "buffer": "BUF-A"},
        {"take": "take02", "device": "D1", "buffer": "BUF-BMID"},
    ]}


def test_ingest_maps_mixed_m4a_aac_by_take_number(tmp_path):
    (tmp_path / "take01.m4a").write_bytes(b"one")
    (tmp_path / "take02.aac").write_bytes(b"two")
    found = ph.discover_recordings(tmp_path, _plan())
    assert found["take01"].name == "take01.m4a"
    assert found["take02"].name == "take02.aac"


def test_ingest_prefers_canonical_name_and_preserves_take_mapping(tmp_path):
    (tmp_path / "take01.m4a").write_bytes(b"canonical")
    (tmp_path / "take01_b.aac").write_bytes(b"retake")
    (tmp_path / "take02.aac").write_bytes(b"two")
    found = ph.discover_recordings(tmp_path, _plan())
    assert found["take01"].read_bytes() == b"canonical"


def test_ingest_fails_missing_take_without_remapping(tmp_path):
    (tmp_path / "take01.m4a").write_bytes(b"one")
    with pytest.raises(RuntimeError, match="take02: missing"):
        ph.discover_recordings(tmp_path, _plan())


def test_ffmpeg_metadata_parser_handles_phone_formats():
    stderr = """Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'take01.m4a':
  Stream #0:0: Audio: aac (LC), 48000 Hz, stereo, fltp
"""
    assert ph.parse_ffmpeg_input(stderr) == {
        "container": "mov,mp4,m4a,3gp,3g2,mj2", "codec": "aac"}


def test_measurement_freeze_is_immutable(tmp_path):
    path = tmp_path / "freeze.json"
    first = ph.freeze_artifact(path, {"threshold": 0.16}, "measurement_freeze_hash")
    assert ph.verify_frozen_artifact(first, "measurement_freeze_hash") == []
    assert ph.freeze_artifact(path, {"threshold": 0.16}, "measurement_freeze_hash") == first
    with pytest.raises(RuntimeError, match="different content"):
        ph.freeze_artifact(path, {"threshold": 0.17}, "measurement_freeze_hash")
    tampered = ph._load_json(path)
    tampered["body"]["threshold"] = 0.17
    ph._save_json(path, tampered)
    with pytest.raises(RuntimeError, match="invalid"):
        ph.freeze_artifact(path, {"threshold": 0.16}, "measurement_freeze_hash")


def _take(take_id, device, pre, post, competitor, leak, drift,
          genuine_trajectory=True):
    return {
        "take_id": take_id, "device": device,
        "marker_diagnostics": {
            "diagnostic_gt_status": "GT_VALID",
            "genuine_pre_marker": {"confidence": pre,
                                   "sweep_trajectory": {"corroborated": genuine_trajectory}},
            "genuine_post_marker": {"confidence": post,
                                    "sweep_trajectory": {"corroborated": genuine_trajectory}},
            "take_competing_B": max(competitor, leak),
            "drift_ppm": drift,
            "top_candidate_diagnostics": [
                {"candidate_role": "NON_MARKER",
                 "sweep_trajectory": {"corroborated": False}}],
        },
    }


def test_threshold_formula_and_device_aggregation_are_predeclared():
    takes = [
        _take("take01", "D1", .25, .30, .04, .03, -20),
        _take("take02", "D1", .24, .29, .03, .02, -10),
        _take("take06", "D2", .23, .28, .05, .02, 15),
        _take("take09", "D3", .22, .27, .03, .02, 30),
    ]
    rules = ph.compute_freeze_rules(takes)
    assert rules["marker"]["G"] == .22
    assert rules["marker"]["B"] == .05
    assert rules["marker"]["T_low_3B"] == pytest.approx(.15)
    assert rules["marker"]["T_high_0_8G"] == pytest.approx(.176)
    assert rules["marker"]["frozen_threshold_exact"] == pytest.approx((.15 * .176) ** .5)
    assert rules["marker"]["per_device"]["D2"]["G_over_B"] == pytest.approx(4.6)
    assert rules["drift"]["frozen_tolerance_ppm"] == 111.0


def test_trajectory_gate_turns_off_if_one_genuine_is_noisy():
    takes = [
        _take("take01", "D1", .30, .30, .03, .02, 1),
        _take("take06", "D2", .30, .30, .03, .02, 1,
              genuine_trajectory=False),
        _take("take09", "D3", .30, .30, .03, .02, 1),
    ]
    assert ph.compute_freeze_rules(takes)["trajectory"]["state"] == \
        "TRAJECTORY_GATE_FROZEN_OFF"


def test_wrong_reference_pairing_is_other_song_and_frozen(tmp_path):
    reports = [
        {"take_id": "take01", "buffer": "BUF-A"},
        {"take_id": "take03", "buffer": "BUF-BMID"},
        {"take_id": "take12", "buffer": "BUF-B1"},
    ]
    body = ph.build_wrong_pairings(reports)
    assert [p["wrong_reference"] for p in body["pairings"]] == [
        "REF-B", "REF-A", "REF-A"]
    frozen = ph.freeze_artifact(tmp_path / "wrong.json", body, "pairing_hash")
    assert ph.verify_frozen_artifact(frozen, "pairing_hash") == []


def test_pilot_scoring_preserves_positive_and_wrong_reference_semantics():
    cases = [{
        "case_id": "take01__positive", "take_id": "take01",
        "pair_type": "POSITIVE", "gt_stratum": "EXACT_GT",
        "gt_offset_s": 2.0, "comparator_eligibility": ["sys"],
    }, {
        "case_id": "take01__wrong_ref", "take_id": "take01",
        "pair_type": "WRONG_REFERENCE", "gt_stratum": "NO_MATCH",
        "gt_offset_s": None, "comparator_eligibility": ["sys"],
    }]
    records = [{"case_id": "take01__positive", "system": "sys",
                "decision": common.DECISION_ACCEPT, "predicted_offset_s": 2.05},
               {"case_id": "take01__wrong_ref", "system": "sys",
                "decision": common.DECISION_ACCEPT, "predicted_offset_s": 9.0}]
    scored = ph.score_records({"cases": cases}, records)
    assert scored["summary_by_pair_type"]["POSITIVE"]["sys"] == {"CORRECT_ACCEPT": 1}
    assert scored["summary_by_pair_type"]["WRONG_REFERENCE"]["sys"] == {"WRONG_ACCEPT": 1}


def test_reproducibility_projection_ignores_only_volatile_fields():
    a = {"runtime_s": 1.2, "notes": {"store_dir": "/tmp/a", "value": 4}}
    b = {"runtime_s": 9.9, "notes": {"store_dir": "/tmp/b", "value": 4}}
    assert ph.comparable_record(a) == ph.comparable_record(b)
    b["notes"]["value"] = 5
    assert ph.comparable_record(a) != ph.comparable_record(b)


def test_direct_gt_crosscheck_recovers_known_payload_position(tmp_path):
    fs = 8000
    rng = np.random.default_rng(20260914)
    reference = rng.normal(0, .1, 4 * fs)
    lead = np.zeros(fs // 2)
    trimmed = np.concatenate((lead, reference[:3 * fs]))
    ref_path, in_path = tmp_path / "ref.wav", tmp_path / "input.wav"
    sf.write(ref_path, reference, fs, subtype="PCM_16")
    sf.write(in_path, trimmed, fs, subtype="PCM_16")
    result = ph.direct_gt_crosscheck(in_path, ref_path, 0.0, 0.5,
                                     probe_duration_s=1.0)
    assert result["passed"]
    assert result["direct_payload_offset_s"] == pytest.approx(.5)


def test_final_protocol_generation_and_immutable_write(tmp_path, monkeypatch):
    monkeypatch.setattr(ph, "DEFAULT_OUTDIR", tmp_path)
    (tmp_path / "pilot_measurement_freeze.json").write_text("{}", encoding="utf-8")
    measurement = {"measurement_freeze_hash": "a" * 64, "body": {
        "marker_confidence_threshold": .16,
        "marker_confidence_threshold_documentation_2dp": .16,
        "trajectory_gate_state": "TRAJECTORY_GATE_FROZEN_OFF",
        "drift_tolerance_ppm": 111.0,
        "mapping_disagreement_tolerance_s": .01,
        "comparators": {
            "rhythmalign_v1_2_0": {"production_tag_commit": "b" * 40},
            "panako_fingerprint": {"pinned_commit": "c" * 40,
                                   "environment": {"jar_sha256": "d" * 64}},
        },
    }}
    evaluation = {"verdict": "PILOT_PASS_PROTOCOL_FREEZE_READY",
                  "panako_role": "PLACEMENT_COMPARATOR"}
    exclusions = {"exclusion_hash": "e" * 64}
    correction = {"correction_hash": "f" * 64}
    text = ph.build_final_protocol_markdown(measurement, evaluation, exclusions,
                                            correction)
    assert "FINAL DATA MUST NOT BE USED TO CHANGE THESE RULES" in text
    assert "exactly 24 scored positive takes" in text
    path = tmp_path / "FINAL.md"
    ph.write_text_immutable(path, text)
    ph.write_text_immutable(path, text)
    with pytest.raises(RuntimeError, match="different content"):
        ph.write_text_immutable(path, text + "changed")
