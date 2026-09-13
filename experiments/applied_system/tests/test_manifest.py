"""Research-only tests: manifest schema, freeze, tamper detection.
SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import manifest as m  # noqa: E402

SHA = "ab" * 32


def _raw_case(case_id="c1", stratum=m.STRATUM_EXACT_GT, **overrides):
    """Unvalidated case dict (for testing the validator itself)."""
    base = dict(
        case_id=case_id, condition="ordinary",
        source_identity="shakedown_song_a",
        payload_identity="shakedown_song_a", payload_sha256=SHA,
        capture_path=f"captures/{case_id}.wav", capture_sha256=SHA,
        reference_path="media/shakedown_song_a.wav", reference_sha256=SHA,
        gt_stratum=stratum,
        gt_offset_s=(2.45 if stratum == m.STRATUM_EXACT_GT else None),
        expected_label=(m.LABEL_MATCH if stratum == m.STRATUM_EXACT_GT
                        else m.LABEL_NO_MATCH),
        marker_qc={"status": stratum},
        provenance={"seed": 1},
        trimmed_input_path=f"trimmed/{case_id}.wav",
        trimmed_input_sha256=SHA,
        comparator_eligibility=m.default_eligibility(stratum),
    )
    if stratum == m.STRATUM_GT_FAILED:
        base.update(trimmed_input_path=None, trimmed_input_sha256=None,
                    expected_label=None, gt_offset_s=None,
                    comparator_eligibility=[])
    base.update(overrides)
    return base


def _valid_case(case_id="c1", stratum=m.STRATUM_EXACT_GT, **overrides):
    return m.make_case(**_raw_case(case_id, stratum, **overrides))


def test_valid_case_builds_and_validates():
    case = _valid_case()
    assert m.validate_case(case) == []
    body = m.build_manifest([case], {"fs": 48000})
    frozen = m.freeze_manifest(body)
    assert m.verify_frozen(frozen) == []


def test_freeze_is_deterministic():
    body = m.build_manifest([_valid_case(), _valid_case(
        case_id="c2", stratum=m.STRATUM_NO_MATCH)], {"fs": 48000})
    f1 = m.freeze_manifest(body)
    f2 = m.freeze_manifest(m.build_manifest([_valid_case(), _valid_case(
        case_id="c2", stratum=m.STRATUM_NO_MATCH)], {"fs": 48000}))
    assert f1["manifest_hash"] == f2["manifest_hash"]


def test_tampered_body_detected():
    frozen = m.freeze_manifest(m.build_manifest([_valid_case()],
                                                {"fs": 48000}))
    frozen["body"]["cases"][0]["gt_offset_s"] = 99.0
    errors = m.verify_frozen(frozen)
    assert any("manifest_hash mismatch" in e for e in errors)


def test_tampered_hash_detected():
    frozen = m.freeze_manifest(m.build_manifest([_valid_case()],
                                                {"fs": 48000}))
    frozen["manifest_hash"] = "0" * 64
    assert m.verify_frozen(frozen)


def test_gt_failed_case_rules():
    case = _valid_case(stratum=m.STRATUM_GT_FAILED)
    assert m.validate_case(case) == []
    # a GT_FAILED case must not carry eligibility or a trimmed input
    bad = _raw_case(stratum=m.STRATUM_GT_FAILED,
                    comparator_eligibility=["x"])
    assert m.validate_case(bad)
    bad2 = _raw_case(stratum=m.STRATUM_GT_FAILED, expected_label="MATCH")
    assert m.validate_case(bad2)
    bad3 = _raw_case(stratum=m.STRATUM_GT_FAILED,
                     trimmed_input_sha256=SHA)
    assert m.validate_case(bad3)


def test_label_stratum_consistency_enforced():
    bad = _raw_case(expected_label=m.LABEL_NO_MATCH)
    assert m.validate_case(bad)
    bad2 = _raw_case(gt_offset_s=None)
    assert m.validate_case(bad2)
    bad3 = _raw_case(stratum=m.STRATUM_NO_MATCH,
                     expected_label=m.LABEL_MATCH)
    assert m.validate_case(bad3)


def test_duplicate_case_ids_rejected():
    with pytest.raises(ValueError):
        m.build_manifest([_valid_case(), _valid_case()], {"fs": 48000})
