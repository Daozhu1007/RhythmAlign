"""Frozen benchmark manifest for the applied-system MACHINERY SHAKEDOWN.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

The manifest is built once (GT -> trim -> hashes), frozen under a canonical
SHA-256 hash, and must never be silently edited afterwards: any run records
and verifies ``manifest_hash``. Validation re-derives the hash from the body
and enforces the schema and stratum/label consistency rules. Manifest
content is fully deterministic (no wall-clock fields), so re-running
preparation from the same code and seeds reproduces the manifest byte for
byte — regeneration that changes the hash is a determinism FAILURE, not a
new manifest.

All media paths are stored POSIX-relative to the manifest's base directory.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

MANIFEST_SCHEMA_VERSION = "1"

STRATUM_EXACT_GT = "EXACT_GT"
STRATUM_NO_MATCH = "NO_MATCH"
STRATUM_GT_FAILED = "GT_FAILED"

LABEL_MATCH = "MATCH"
LABEL_NO_MATCH = "NO_MATCH"

REQUIRED_CASE_KEYS = (
    "case_id", "shakedown_only", "not_paper_evidence", "condition",
    "source_identity", "payload_identity", "payload_sha256",
    "capture_path", "capture_sha256",
    "trimmed_input_path", "trimmed_input_sha256",
    "reference_path", "reference_sha256",
    "gt_stratum", "gt_offset_s", "expected_label",
    "marker_qc", "provenance", "comparator_eligibility",
)


def canonical_json_bytes(obj) -> bytes:
    """Stable serialization used for hashing (sorted keys, tight separators,
    UTF-8, preserved non-ASCII)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def make_case(case_id: str, condition: str, source_identity: str,
              payload_identity: str, payload_sha256: str,
              capture_path: str, capture_sha256: str,
              reference_path: str, reference_sha256: str,
              gt_stratum: str, gt_offset_s: Optional[float],
              expected_label: Optional[str], marker_qc: dict,
              provenance: dict, trimmed_input_path: Optional[str],
              trimmed_input_sha256: Optional[str],
              comparator_eligibility: list) -> dict:
    case = {
        "case_id": case_id,
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "condition": condition,
        "source_identity": source_identity,
        "payload_identity": payload_identity,
        "payload_sha256": payload_sha256,
        "capture_path": capture_path,
        "capture_sha256": capture_sha256,
        "trimmed_input_path": trimmed_input_path,
        "trimmed_input_sha256": trimmed_input_sha256,
        "reference_path": reference_path,
        "reference_sha256": reference_sha256,
        "gt_stratum": gt_stratum,
        "gt_offset_s": gt_offset_s,
        "expected_label": expected_label,
        "marker_qc": marker_qc,
        "provenance": provenance,
        "comparator_eligibility": comparator_eligibility,
    }
    errors = validate_case(case)
    if errors:
        raise ValueError(f"invalid case {case_id}: {errors}")
    return case


def default_eligibility(gt_stratum: str) -> list:
    if gt_stratum == STRATUM_GT_FAILED:
        return []
    return ["rhythmalign_v1_2_0", "gcc_phat_argmax_v1", "ncc_argmax_v1"]


def validate_case(case: dict) -> list:
    errors = []
    for key in REQUIRED_CASE_KEYS:
        if key not in case:
            errors.append(f"missing key: {key}")
    if errors:
        return errors
    if case["shakedown_only"] != "SHAKEDOWN_ONLY":
        errors.append("case is not flagged SHAKEDOWN_ONLY")
    if case["not_paper_evidence"] != "NOT_PAPER_EVIDENCE":
        errors.append("case is not flagged NOT_PAPER_EVIDENCE")
    if case["gt_stratum"] not in (STRATUM_EXACT_GT, STRATUM_NO_MATCH,
                                  STRATUM_GT_FAILED):
        errors.append(f"unknown gt_stratum: {case['gt_stratum']}")

    def _is_sha256(x):
        return isinstance(x, str) and len(x) == 64 and \
            all(c in "0123456789abcdef" for c in x)

    for key in ("payload_sha256", "capture_sha256", "reference_sha256"):
        if not _is_sha256(case[key]):
            errors.append(f"{key} is not a sha256 hex digest")

    def _is_rel_posix(p):
        return p is None or (isinstance(p, str) and not p.startswith("/")
                             and ":" not in p and "\\" not in p)

    for key in ("capture_path", "trimmed_input_path", "reference_path"):
        if not _is_rel_posix(case[key]):
            errors.append(f"{key} must be a POSIX-relative path")

    if case["gt_stratum"] == STRATUM_GT_FAILED:
        if case["comparator_eligibility"]:
            errors.append("GT_FAILED case must have empty "
                          "comparator_eligibility")
        if case["trimmed_input_path"] is not None or \
                case["trimmed_input_sha256"] is not None:
            errors.append("GT_FAILED case must not ship a trimmed input")
        if case["expected_label"] is not None:
            errors.append("GT_FAILED case must not carry an expected label")
    else:
        if not _is_sha256(case["trimmed_input_sha256"] or ""):
            errors.append("scoreable case requires trimmed_input_sha256")
        if case["expected_label"] not in (LABEL_MATCH, LABEL_NO_MATCH):
            errors.append(f"bad expected_label: {case['expected_label']}")
        if case["expected_label"] != (
                LABEL_MATCH if case["gt_stratum"] == STRATUM_EXACT_GT
                else LABEL_NO_MATCH):
            errors.append("expected_label inconsistent with gt_stratum")
        if case["gt_stratum"] == STRATUM_EXACT_GT and \
                not isinstance(case["gt_offset_s"], (int, float)):
            errors.append("EXACT_GT case requires numeric gt_offset_s")
    return errors


def build_manifest(cases: list, protocol_constants: dict,
                   notes: Optional[dict] = None) -> dict:
    """Assemble the manifest BODY from validated cases. Deterministic."""
    body = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "warning": ("THIS IS ENGINEERING SHAKEDOWN DATA. "
                    "IT MUST NOT BE USED AS FINAL PAPER EVIDENCE."),
        "protocol_constants": protocol_constants,
        "cases": sorted(cases, key=lambda c: c["case_id"]),
        "notes": notes or {},
    }
    seen = set()
    for case in body["cases"]:
        if case["case_id"] in seen:
            raise ValueError(f"duplicate case_id: {case['case_id']}")
        seen.add(case["case_id"])
        errors = validate_case(case)
        if errors:
            raise ValueError(f"invalid case {case['case_id']}: {errors}")
    return body


def freeze_manifest(body: dict) -> dict:
    """Attach the canonical SHA-256 of the body. The hash covers every
    content byte of the body; runs verify it before executing."""
    manifest_hash = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return {"manifest_hash": manifest_hash, "body": body}


def verify_frozen(frozen: dict) -> list:
    errors = []
    body = frozen.get("body")
    declared = frozen.get("manifest_hash")
    if not isinstance(body, dict) or not isinstance(declared, str):
        return ["malformed frozen manifest"]
    recomputed = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    if recomputed != declared:
        errors.append(f"manifest_hash mismatch: declared {declared}, "
                      f"recomputed {recomputed} (manifest was edited after "
                      f"freeze)")
    if body.get("shakedown_only") != "SHAKEDOWN_ONLY":
        errors.append("manifest is not flagged SHAKEDOWN_ONLY")
    for case in body.get("cases", []):
        for err in validate_case(case):
            errors.append(f"{case.get('case_id')}: {err}")
    return errors
