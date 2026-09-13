"""Research-only tests: deterministic scoring contract, including
wrong-reference scoring and GT_FAILED handling.
SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import scoring as s  # noqa: E402
from experiments.applied_system.manifest import (  # noqa: E402
    STRATUM_EXACT_GT, STRATUM_GT_FAILED, STRATUM_NO_MATCH)
from experiments.applied_system.runners.common import (  # noqa: E402
    DECISION_ABSTAIN, DECISION_ACCEPT, DECISION_ERROR, DECISION_NO_MATCH)

SHA = "ab" * 32


def _case(stratum=STRATUM_EXACT_GT, gt_offset_s=2.45, case_id="c1"):
    return {
        "case_id": case_id, "gt_stratum": stratum,
        "gt_offset_s": gt_offset_s,
        "comparator_eligibility": ["rhythmalign_v1_2_0"],
        "trimmed_input_sha256": None if stratum == STRATUM_GT_FAILED else SHA,
    }


def _rec(decision, offset=None, system="sys", case_id="c1"):
    return {"system": system, "case_id": case_id, "decision": decision,
            "predicted_offset_s": offset, "native_scores": {},
            "runtime_s": 0.5, "output_semantics": "ALWAYS_OUTPUT",
            "notes": {}}


def test_positive_within_tolerance():
    out = s.score_pair(_case(), _rec(DECISION_ACCEPT, 2.45 + 0.09))
    assert out["outcome"] == s.OUTCOME_CORRECT_ACCEPT
    assert out["abs_error_s"] == pytest.approx(0.09)


def test_positive_outside_tolerance():
    out = s.score_pair(_case(), _rec(DECISION_ACCEPT, 2.45 + 0.11))
    assert out["outcome"] == s.OUTCOME_WRONG_ACCEPT


def test_tolerance_boundary_inclusive():
    out = s.score_pair(_case(), _rec(DECISION_ACCEPT, 2.45 + 0.100))
    assert out["outcome"] == s.OUTCOME_CORRECT_ACCEPT


def test_positive_abstain_is_safe():
    out = s.score_pair(_case(), _rec(DECISION_ABSTAIN))
    assert out["outcome"] == s.OUTCOME_SAFE_ABSTAIN


def test_no_match_accept_is_wrong_accept():
    out = s.score_pair(_case(stratum=STRATUM_NO_MATCH),
                       _rec(DECISION_ACCEPT, 7.0))
    assert out["outcome"] == s.OUTCOME_WRONG_ACCEPT
    assert out["protocol_failure"] is False


def test_no_match_abstain_is_safe():
    out = s.score_pair(_case(stratum=STRATUM_NO_MATCH),
                       _rec(DECISION_NO_MATCH))
    assert out["outcome"] == s.OUTCOME_SAFE_ABSTAIN


def test_gt_failed_case():
    out = s.score_pair(_case(stratum=STRATUM_GT_FAILED, gt_offset_s=None),
                       None)
    assert out["outcome"] == s.OUTCOME_GT_FAILED
    assert out["protocol_failure"] is True


def test_runner_error_and_missing_record():
    out = s.score_pair(_case(), _rec(DECISION_ERROR))
    assert out["outcome"] == s.OUTCOME_RUNNER_ERROR
    out2 = s.score_pair(_case(), None)
    assert out2["outcome"] == s.OUTCOME_RUNNER_ERROR


def test_score_run_summary_and_protocol_failures():
    manifest = {"cases": [
        {**_case(case_id="pos"), "comparator_eligibility": ["a", "b"]},
        {**_case(stratum=STRATUM_NO_MATCH, case_id="neg"),
         "comparator_eligibility": ["a"]},
        {**_case(stratum=STRATUM_GT_FAILED, gt_offset_s=None,
                 case_id="bad"), "comparator_eligibility": []},
    ]}
    records = [
        _rec(DECISION_ACCEPT, 2.50, system="a", case_id="pos"),
        _rec(DECISION_ABSTAIN, system="b", case_id="pos"),
        _rec(DECISION_ACCEPT, 9.9, system="a", case_id="neg"),
    ]
    scores = s.score_run(manifest, records)
    assert scores["summary"]["a"] == {"CORRECT_ACCEPT": 1,
                                      "WRONG_ACCEPT": 1}
    assert scores["summary"]["b"] == {"SAFE_ABSTAIN": 1}
    # the GT_FAILED case is reported under the PROTOCOL bucket: no system
    assert scores["summary"]["PROTOCOL"] == {"GT_FAILED": 1}
    assert len(scores["protocol_failures"]) == 1
    assert scores["protocol_failures"][0]["case_id"] == "bad"
    # shakedown labels embedded in the artifact
    assert scores["shakedown_only"] == "SHAKEDOWN_ONLY"
    assert scores["not_paper_evidence"] == "NOT_PAPER_EVIDENCE"


def test_comparable_record_strips_runtime():
    r = _rec(DECISION_ACCEPT, 1.0)
    r["native_scores"] = {"runtime_curve_s": 0.1, "lag_samples": 48}
    cmp1 = s.comparable_record(r)
    import copy
    r2 = copy.deepcopy(r)
    r2["runtime_s"] = 9.9
    r2["native_scores"]["runtime_curve_s"] = 9.9
    assert cmp1 == s.comparable_record(r2)
    assert cmp1["native_scores"]["lag_samples"] == 48
