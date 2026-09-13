"""Deterministic scoring contract for the applied-system MACHINERY SHAKEDOWN.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Contract (shakedown spec section 12), pure and deterministic:

  Exact-GT positive pair:
      ACCEPT within tolerance  -> CORRECT_ACCEPT
      ACCEPT outside tolerance -> WRONG_ACCEPT
      ABSTAIN / NO_MATCH       -> SAFE_ABSTAIN
  Wrong-reference / no-match pair:
      any placement ACCEPT     -> WRONG_ACCEPT
      ABSTAIN / NO_MATCH       -> SAFE_ABSTAIN
  Invalid marker/GT:
      GT_FAILED — excluded from alignment metrics, reported as a
      benchmark-protocol failure, never silently dropped.
  Runner failure:
      RUNNER_ERROR — also a protocol failure (records exist but the system
      errored); never silently dropped.

Tolerance: 100 ms primary (editorial-task criterion from the study design;
NOT a perceptual threshold). 50/150 ms sensitivities are derivable from the
per-case absolute errors reported here; the shakedown does not tune anything.
"""
from __future__ import annotations

from .manifest import (STRATUM_EXACT_GT, STRATUM_GT_FAILED, STRATUM_NO_MATCH)
from .runners.common import (DECISION_ABSTAIN, DECISION_ACCEPT,
                             DECISION_ERROR, DECISION_NO_MATCH,
                             SHAKEDOWN_WARNING)

TOLERANCE_S_PRIMARY = 0.100
TOLERANCE_SENSITIVITIES_S = (0.050, 0.150)

OUTCOME_CORRECT_ACCEPT = "CORRECT_ACCEPT"
OUTCOME_WRONG_ACCEPT = "WRONG_ACCEPT"
OUTCOME_SAFE_ABSTAIN = "SAFE_ABSTAIN"
OUTCOME_GT_FAILED = "GT_FAILED"
OUTCOME_RUNNER_ERROR = "RUNNER_ERROR"

VOLATILE_RECORD_KEYS = ("runtime_s",)
# fp guard only (1 ps): floating-point subtraction noise at the tolerance
# boundary must not flip an outcome; the editorial tolerance is unchanged.
TOLERANCE_FP_GUARD_S = 1e-12


def score_pair(case: dict, record: dict | None,
               tolerance_s: float = TOLERANCE_S_PRIMARY) -> dict:
    """Score one (case, system record) pair. Pure function of its inputs."""
    base = {
        "case_id": case["case_id"],
        "gt_stratum": case["gt_stratum"],
        "tolerance_s": tolerance_s,
    }
    if case["gt_stratum"] == STRATUM_GT_FAILED:
        return {**base, "system": (record or {}).get("system"),
                "outcome": OUTCOME_GT_FAILED, "abs_error_s": None,
                "protocol_failure": True}
    if record is None:
        return {**base, "system": None, "outcome": OUTCOME_RUNNER_ERROR,
                "abs_error_s": None, "protocol_failure": True,
                "notes": "no record produced for an eligible case"}
    decision = record.get("decision")
    if decision == DECISION_ERROR:
        return {**base, "system": record.get("system"),
                "outcome": OUTCOME_RUNNER_ERROR, "abs_error_s": None,
                "protocol_failure": True}
    if decision in (DECISION_ABSTAIN, DECISION_NO_MATCH):
        return {**base, "system": record.get("system"),
                "outcome": OUTCOME_SAFE_ABSTAIN, "abs_error_s": None,
                "protocol_failure": False}
    if decision == DECISION_ACCEPT:
        offset = record.get("predicted_offset_s")
        if case["gt_stratum"] == STRATUM_NO_MATCH:
            return {**base, "system": record.get("system"),
                    "outcome": OUTCOME_WRONG_ACCEPT, "abs_error_s": None,
                    "protocol_failure": False,
                    "notes": "placement accepted on a no-match pair"}
        if not isinstance(offset, (int, float)):
            return {**base, "system": record.get("system"),
                    "outcome": OUTCOME_RUNNER_ERROR, "abs_error_s": None,
                    "protocol_failure": True,
                    "notes": "ACCEPT without a numeric offset"}
        gt = float(case["gt_offset_s"])
        err = abs(float(offset) - gt)
        return {**base, "system": record.get("system"),
                "outcome": (OUTCOME_CORRECT_ACCEPT
                            if err <= tolerance_s + TOLERANCE_FP_GUARD_S
                            else OUTCOME_WRONG_ACCEPT),
                "abs_error_s": err, "protocol_failure": False}
    return {**base, "system": record.get("system"),
            "outcome": OUTCOME_RUNNER_ERROR, "abs_error_s": None,
            "protocol_failure": True,
            "notes": f"unknown decision value: {decision!r}"}


def score_run(manifest_body: dict, records: list,
              tolerance_s: float = TOLERANCE_S_PRIMARY) -> dict:
    """Score every eligible (case, system) combination. Cases without a
    record for an eligible system produce RUNNER_ERROR (protocol failure),
    never a silent drop. GT_FAILED cases (empty eligibility) are always
    reported as protocol-failure rows — never silently dropped."""
    by_key = {(r.get("case_id"), r.get("system")): r for r in records}
    per_case = []
    for case in sorted(manifest_body["cases"], key=lambda c: c["case_id"]):
        if not case["comparator_eligibility"]:
            if case["gt_stratum"] == STRATUM_GT_FAILED:
                per_case.append(score_pair(case, None, tolerance_s))
            continue
        for system in case["comparator_eligibility"]:
            per_case.append(score_pair(case, by_key.get((case["case_id"],
                                                         system)),
                                       tolerance_s))
    summary = {}
    for row in per_case:
        # Rows without a system (GT_FAILED protocol rows) are bucketed
        # under "PROTOCOL"; JSON objects require string keys.
        slot = summary.setdefault(row["system"] or "PROTOCOL", {})
        slot[row["outcome"]] = slot.get(row["outcome"], 0) + 1
    protocol_failures = [row for row in per_case if row["protocol_failure"]]
    return {
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "warning": SHAKEDOWN_WARNING,
        "tolerance_s": tolerance_s,
        "tolerance_note": ("100 ms primary editorial-task tolerance; "
                           "50/150 ms sensitivity derivable from per-case "
                           "abs_error_s; no threshold tuned in this round"),
        "per_case": per_case,
        "summary": summary,
        "protocol_failures": protocol_failures,
        "alignment_metrics_note": ("GT_FAILED and RUNNER_ERROR outcomes are "
                                   "excluded from alignment performance "
                                   "metrics and reported as benchmark-"
                                   "protocol failures"),
    }


def comparable_record(record: dict) -> dict:
    """Record projection used for reproducibility comparison: volatile
    timing fields removed at every nesting level, everything else preserved
    byte-exactly. Runner records embed raw native outputs (e.g. the frozen
    engine's full decision dict) that may carry their own internal timings.
    """
    def strip(obj):
        if isinstance(obj, dict):
            return {k: strip(v) for k, v in obj.items()
                    if "runtime" not in str(k)}
        if isinstance(obj, list):
            return [strip(v) for v in obj]
        return obj
    return strip(record)
