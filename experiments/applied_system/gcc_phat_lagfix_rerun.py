"""COMPARATOR-INTEGRITY-1: outcome-independent GCC-PHAT lagfix rerun.

Uniform re-execution of the corrected ``gcc_phat_argmax_v2_lagfix``
implementation on exactly the frozen GCC-eligible final cases (24 positive +
24 wrong-reference + 2 strict repeats), using byte-identical frozen inputs
(hash-verified per record) and the byte-identical PHAT curve of v1 (imported,
not reimplemented). Only the FFT-index -> lag unwrap differs.

Subcommands:
  freeze-manifest  Write the correction manifest (write-once). Contains the
                   exact correction and a geometry-only prediction of which
                   frozen v1 records the corrected unwrap can change,
                   derived BEFORE any v2 execution from frozen v1
                   ``lag_samples`` plus frozen file lengths only — no
                   ground truth, no scoring outcomes, no v2 output.
  rerun            Execute v2 uniformly on all GCC-eligible cases; verify
                   per-record input/reference hashes against the frozen
                   benchmark manifest; verify the recomputed argmax index
                   matches the geometry prediction; write versioned records
                   + raw assembly + hash sidecars. Never touches v1 paths.
  score            Score the v2 records with the frozen scoring contract at
                   50/100/150 ms and write the versioned results artifact
                   with an explicit v1-vs-v2 comparison.

Frozen evidence is never modified: the original ``final_comparator_raw.json``,
its 200 per-record files, ``final_benchmark_results.json``, and
``final_benchmark_reporting_v2.json`` are read-only here.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.applied_system import scoring  # noqa: E402
from experiments.applied_system.final_benchmark import (  # noqa: E402
    FINAL_MARK, _canonical_bytes, _sha256_file, _utc_now,
    verify_frozen_artifact, write_hash_sidecar)
from experiments.applied_system.runners import common  # noqa: E402
from experiments.applied_system.runners import gcc_phat_runner  # noqa: E402
from experiments.applied_system.runners import gcc_phat_runner_v2_lagfix as v2  # noqa: E402
from scipy import fft as scipy_fft  # noqa: E402

BENCH_MANIFEST = (ROOT / "experiments/applied_system/final_pack/results/"
                  "final_benchmark_manifest.json")
V1_RAW = (ROOT / "experiments/applied_system/final_pack/results/"
          "final_comparator_raw.json")
V1_RESULTS = (ROOT / "experiments/applied_system/final_pack/results/"
              "final_benchmark_results.json")
V1_REPORTING = (ROOT / "experiments/applied_system/final_pack/results/"
                "final_benchmark_reporting_v2.json")
V1_RECORDS_DIR = (ROOT / "experiments/applied_system/final_pack/results/"
                  "final_comparator_raw_records")

RESULTS_DIR = ROOT / "experiments/applied_system/final_pack/results"
V2_MANIFEST = RESULTS_DIR / "gcc_phat_v2_lagfix_correction_manifest.json"
V2_RAW = RESULTS_DIR / "gcc_phat_v2_lagfix_raw.json"
V2_RESULTS = RESULTS_DIR / "gcc_phat_v2_lagfix_results.json"
V2_RECORDS_DIR = RESULTS_DIR / "gcc_phat_v2_lagfix_records"

REQUIRED_BRANCH = "research/applied-system-paper"
AUDIT_HEAD = "0f37cbc"

FROZEN_BASELINES = {
    "final_comparator_raw.json":
        "9ae59821baaf523ad1f89c98b214d565573600d3e23a7c13a2e2f2a9c848dcb3",
    "final_benchmark_results.json":
        "4c6c81dfc8289905286560e8ca2ede71f72c478d6c0fd5c04f68e98061ad6fc2",
    "final_benchmark_reporting_v2.json":
        "b46b9357dca0de9f50d879d9b6dd1952fb7eb21a29581ab8f559b7c7ec5d9acc",
}

OLD_MAPPING = ("lag(j) = j if j < ceil(N/2) else j - N   "
               "(length-independent midpoint unwrap)")
NEW_MAPPING = ("lag(j) = j - N if j >= N - Ly + 1 else j   "
               "(linear-correlation support geometry; Lx = query length, "
               "Ly = reference length, N = fft_length = next_fast_len(Lx+Ly))")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, timeout=30).stdout.strip()


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_canonical_bytes(value).decode("utf-8") + "\n")


def require_branch_head() -> None:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != REQUIRED_BRANCH:
        raise SystemExit(f"refusing to run on branch {branch!r}")
    head = _git("rev-parse", "--short", "HEAD")
    print(f"branch={branch} head={head}")


def verify_frozen_baselines() -> None:
    for name, expected in FROZEN_BASELINES.items():
        got = _sha256_file(RESULTS_DIR / name)
        if got != expected:
            raise SystemExit(f"frozen artifact changed before audit: "
                             f"{name}: {got}")
    errors = verify_frozen_artifact(_load_json(BENCH_MANIFEST))
    if errors:
        raise SystemExit(f"benchmark manifest invalid: {errors}")
    print("frozen baselines verified (3 artifacts + benchmark manifest)")


def case_lengths(case: dict) -> tuple[int, int]:
    """(Lx, Ly) in samples, read from the frozen input/reference WAVs."""
    import soundfile as sf
    lx = sf.info(str(ROOT / case["trimmed_input_path"])).frames
    ly = sf.info(str(ROOT / case["reference_path"])).frames
    fs_in = sf.info(str(ROOT / case["trimmed_input_path"])).samplerate
    fs_ref = sf.info(str(ROOT / case["reference_path"])).samplerate
    if fs_in != 48000 or fs_ref != 48000:
        raise SystemExit(f"{case['case_id']}: unexpected sample rate")
    return lx, ly


def classify(lx: int, ly: int, reported_lag: int) -> dict:
    """Geometry-only reconstruction of the v1 argmax index and region from a
    frozen v1 reported lag plus the two file lengths."""
    n = scipy_fft.next_fast_len(lx + ly)
    mid = (n + 1) // 2
    j = reported_lag if reported_lag >= 0 else reported_lag + n
    if j <= lx - 1:
        region = "positive_support"
    elif j <= n - ly:
        region = "zero_overlap"
    elif j < mid:
        region = "negative_below_midpoint"   # v1 misreads: reports +j
    else:
        region = "negative_at_or_above_midpoint"
    v2_lag = j - n if j >= n - ly + 1 else j
    return {"n_total": n, "midpoint": mid, "wrap_boundary": n - ly + 1,
            "argmax_index": j, "region": region,
            "v1_reported_lag_samples": reported_lag,
            "v2_predicted_lag_samples": v2_lag,
            "v2_changes_lag": v2_lag != reported_lag}


def load_frozen_v1_lags() -> dict:
    """case_id -> native lag_samples from the sealed v1 raw records."""
    v1 = _load_json(V1_RAW)
    got = _sha256_file(V1_RAW)
    expected = FROZEN_BASELINES["final_comparator_raw.json"]
    if got != expected:
        raise SystemExit(f"v1 raw assembly hash mismatch: {got}")
    out = {}
    for entry in v1["records"]:
        rec = _load_json(ROOT / entry["record_file"])
        if _sha256_file(ROOT / entry["record_file"]) != entry["record_sha256"]:
            raise SystemExit(f"v1 record hash mismatch: {entry['record_file']}")
        if rec["system"] != gcc_phat_runner.SYSTEM_ID:
            continue
        out[rec["case_id"]] = int(rec["native_scores"]["lag_samples"])
    return out


def build_prediction() -> list:
    v1_lags = load_frozen_v1_lags()
    frozen = _load_json(BENCH_MANIFEST)
    rows = []
    for case in frozen["body"]["cases"]:
        cid = case["case_id"]
        if gcc_phat_runner.SYSTEM_ID not in case["comparator_eligibility"]:
            continue
        lx, ly = case_lengths(case)
        info = classify(lx, ly, v1_lags[cid])
        rows.append({
            "case_id": cid,
            "pair_type": case["pair_type"],
            "query_samples": lx,
            "reference_samples": ly,
            **info,
            "predicted_offset_unchanged": not info["v2_changes_lag"],
        })
    return rows


def cmd_freeze_manifest() -> None:
    require_branch_head()
    verify_frozen_baselines()
    if V2_MANIFEST.exists():
        raise SystemExit("correction manifest already exists (write-once)")
    prediction = build_prediction()
    changed = [r["case_id"] for r in prediction if r["v2_changes_lag"]]
    zero_region = [r["case_id"] for r in prediction
                   if r["region"] == "zero_overlap"]
    body = {
        "audit_id": "COMPARATOR-INTEGRITY-1",
        "created_utc": _utc_now(),
        "git_head_short": _git("rev-parse", "--short", "HEAD"),
        "verdict": "GCC_LAG_MAPPING_BUG_CONFIRMED",
        "system_v1": gcc_phat_runner.SYSTEM_ID,
        "system_v2": v2.SYSTEM_ID,
        "root_cause": (
            "gcc_phat_runner.curve_argmax_offset_samples unwraps the "
            "zero-padded FFT correlation at the length-independent midpoint "
            "ceil(N/2). Linear-correlation lag support depends on BOTH "
            "lengths: negative lags occupy indices N-Ly+1..N-1. When the "
            "query is shorter than the reference (N close to Lx+Ly), part of "
            "the negative-lag support lies below the midpoint and v1 reports "
            "it as a positive lag larger by exactly N samples; when the "
            "query is longer, part of the positive support is reported "
            "negative by N. Equal lengths are unaffected."),
        "old_mapping": OLD_MAPPING,
        "corrected_mapping": NEW_MAPPING,
        "curve_identity": (
            "v2 imports gcc_phat_curve from v1 verbatim; the PHAT curve, "
            "FFT length, and argmax index are bit-identical. Only the "
            "index->lag unwrap differs."),
        "affected_geometry": (
            "any pair with next_fast_len(Lx+Ly) < 2*Ly (query shorter than "
            "reference, misread negative lags) or next_fast_len(Lx+Ly) < "
            "2*Lx (query longer, misread positive lags); equal lengths "
            "never affected"),
        "sign_convention": (
            "lag m means y_rec[n] ~= y_ref[n - m]; the reference begins m "
            "samples into the capture; identical to the production engine "
            "and the frozen ground truth (gt = payload_start_in_trimmed - "
            "slice_start)"),
        "synthetic_validation": {
            "test_module": ("experiments/applied_system/tests/"
                            "test_gcc_phat_lagfix.py"),
            "independent_reference": ("direct linear cross-correlation "
                                      "(scipy.signal.correlate, direct "
                                      "method) with explicit lag axis"),
            "fixture_families": [
                "impulse pairs over {query shorter, equal, query longer} x "
                "{zero, positive, negative, both single-sample boundary} "
                "lags",
                "exact delayed-copy broadband pairs (pure linear phase -> "
                "exact PHAT delta) at deep negative and large positive "
                "lags in both misread regions",
                "noise-added delayed copy (deterministic seed)",
                "full lag sweep (stride 37) over an unequal pair, v1 "
                "correct iff outside the misread region",
                "sign-convention, determinism, file-contract, and "
                "NCC-unaffected checks",
            ],
            "result": "26 passed (run before any final-case re-execution)",
        },
        "implementation_hashes": {
            "gcc_phat_runner_v1_sha256":
                _sha256_file(ROOT / "experiments/applied_system/runners/"
                             "gcc_phat_runner.py"),
            "gcc_phat_runner_v2_lagfix_sha256":
                _sha256_file(ROOT / "experiments/applied_system/runners/"
                             "gcc_phat_runner_v2_lagfix.py"),
        },
        "outcome_independence": (
            "The correction is fixed by linear-correlation lag geometry "
            "alone and was validated on synthetic fixtures BEFORE any final "
            "case was re-executed. The prediction below was derived only "
            "from frozen v1 native lag_samples and frozen file lengths — "
            "no ground truth, no scoring outcome, no RhythmAlign/NCC/"
            "Panako/Kdenlive output, and no v2 execution entered it."),
        "geometry_only_prediction": {
            "method": (
                "reconstruct each v1 argmax index from its frozen reported "
                "lag and the frozen file lengths, classify the index "
                "against the support regions, apply the corrected unwrap"),
            "records_total": len(prediction),
            "records_with_changed_lag": sorted(changed),
            "records_with_changed_lag_count": len(changed),
            "zero_overlap_argmax_records": sorted(zero_region),
            "per_case": prediction,
        },
        "rerun_contract": {
            "cases": "every benchmark case eligible for gcc_phat_argmax_v1 "
                     "(24 positive + 24 wrong-reference + 2 repeats)",
            "inputs": "hash-verified trimmed inputs and references, loaded "
                      "identically to the frozen run (float64, mean of "
                      "channels, native 48 kHz)",
            "semantics": "ALWAYS_OUTPUT argmax; no threshold, no refusal, "
                         "no no-match detector",
            "scoring": "frozen scoring.py contract; 100 ms primary, "
                       "50/150 ms sensitivity; no new threshold",
            "outputs": {
                "records_dir": str(V2_RECORDS_DIR.relative_to(ROOT)),
                "raw_assembly": str(V2_RAW.relative_to(ROOT)),
                "scored_results": str(V2_RESULTS.relative_to(ROOT)),
            },
            "v1_evidence": "preserved verbatim; nothing under "
                           "final_comparator_raw_records/ or any frozen "
                           "artifact is modified",
        },
        "frozen_baselines_sha256": FROZEN_BASELINES,
    }
    _save_json(V2_MANIFEST, {"body": body})
    value = _load_json(V2_MANIFEST)
    value["freeze_hash"] = hashlib.sha256(
        _canonical_bytes(value["body"])).hexdigest()
    _save_json(V2_MANIFEST, value)
    write_hash_sidecar(V2_MANIFEST)
    print(f"frozen correction manifest: {V2_MANIFEST.name}")
    print(f"  records: {len(prediction)}; changed-lag prediction: {changed}")


def _load_audio_same_rate(path: Path, fs: int):
    import numpy as np
    import soundfile as sf
    y, sr = sf.read(str(path), dtype="float64", always_2d=False)
    if sr != fs:
        raise ValueError(f"{path}: sample rate {sr} != frozen input rate {fs}")
    if y.ndim > 1:
        y = y.mean(axis=1)
    return np.ascontiguousarray(y)


def cmd_rerun() -> None:
    require_branch_head()
    verify_frozen_baselines()
    if V2_RAW.exists() or V2_RECORDS_DIR.exists():
        raise SystemExit("v2 rerun artifacts already exist (single-pass)")
    manifest_value = _load_json(V2_MANIFEST)
    errors = verify_frozen_artifact(manifest_value)
    if errors:
        raise SystemExit(f"correction manifest invalid: {errors}")
    prediction = {r["case_id"]: r
                  for r in manifest_value["body"]["geometry_only_prediction"]
                  ["per_case"]}

    frozen = _load_json(BENCH_MANIFEST)
    records = []
    for case in frozen["body"]["cases"]:
        if gcc_phat_runner.SYSTEM_ID not in case["comparator_eligibility"]:
            continue
        cid = case["case_id"]
        input_path = ROOT / case["trimmed_input_path"]
        reference_path = ROOT / case["reference_path"]
        actual_input = _sha256_file(input_path)
        actual_ref = _sha256_file(reference_path)
        if (actual_input != case["trimmed_input_sha256"]
                or actual_ref != case["reference_sha256"]):
            raise SystemExit(f"{cid}: input/reference hash mismatch against "
                             "frozen manifest — refusing to rerun")
        import soundfile as sf
        fs = int(sf.info(str(input_path)).samplerate)
        record = v2.run_case(case, input_path, reference_path, fs,
                             _load_audio_same_rate)
        value = record.as_dict()
        value.pop("shakedown_only", None)
        value.pop("not_paper_evidence", None)
        value.pop("warning", None)
        value["final_confirmatory_evidence"] = FINAL_MARK
        value["input_sha256"] = {"trimmed_input": actual_input,
                                 "reference": actual_ref}
        # integrity link: the recomputed curve must match the geometry
        # prediction made before any v2 execution.
        pred = prediction[cid]
        if record.decision != "ACCEPT" or value["native_scores"].get("error"):
            raise SystemExit(f"{cid}: v2 runner error")
        if value["native_scores"]["argmax_index"] != pred["argmax_index"]:
            raise SystemExit(f"{cid}: argmax index {value['native_scores']['argmax_index']} "
                             f"!= pre-registered prediction {pred['argmax_index']}")
        if value["native_scores"]["lag_samples"] != \
                pred["v2_predicted_lag_samples"]:
            raise SystemExit(f"{cid}: v2 lag differs from prediction")
        path = V2_RECORDS_DIR / f"{v2.SYSTEM_ID}__{cid}.json"
        _save_json(path, value)
        write_hash_sidecar(path)
        records.append(value)
        print(f"  {cid}: lag {value['native_scores']['lag_samples']}"
              f" ({'CHANGED' if pred['v2_changes_lag'] else 'unchanged'})")

    expected = sorted(prediction)
    if sorted(r["case_id"] for r in records) != expected:
        raise SystemExit("v2 rerun case set differs from the frozen "
                         "GCC-eligible case set")

    index = {
        "status": "GCC_PHAT_V2_LAGFIX_RAW",
        "final_confirmatory_evidence": FINAL_MARK,
        "not_pilot_not_development": True,
        "audit_id": "COMPARATOR-INTEGRITY-1",
        "correction_manifest_freeze_sha256":
            manifest_value["freeze_hash"],
        "manifest_freeze_sha256": frozen["freeze_hash"],
        "supersedes": ("the lag mapping of gcc_phat_argmax_v1 only; v1 raw "
                       "evidence (final_comparator_raw.json and its 200 "
                       "records) is preserved verbatim and remains the "
                       "defective-implementation record"),
        "single_pass": ("each (system, case) ran exactly once; existing "
                        "records are never regenerated"),
        "records": [{"record_file": str(
                        V2_RECORDS_DIR.relative_to(ROOT) /
                        f"{v2.SYSTEM_ID}__{r['case_id']}.json"),
                     "record_sha256": _sha256_file(
                        V2_RECORDS_DIR /
                        f"{v2.SYSTEM_ID}__{r['case_id']}.json")}
                    for r in sorted(records, key=lambda r: r["case_id"])],
    }
    _save_json(V2_RAW, index)
    write_hash_sidecar(V2_RAW)
    print(f"wrote {V2_RAW.name} with {len(records)} records")


def cmd_score() -> None:
    require_branch_head()
    verify_frozen_baselines()
    manifest_value = _load_json(V2_MANIFEST)
    errors = verify_frozen_artifact(manifest_value)
    if errors:
        raise SystemExit(f"correction manifest invalid: {errors}")
    raw = _load_json(V2_RAW)
    got = _sha256_file(V2_RAW)
    if got != _read_sidecar_digest(V2_RAW):
        raise SystemExit("v2 raw assembly hash sidecar mismatch")
    records = [_load_json(ROOT / entry["record_file"])
               for entry in raw["records"]]
    for entry in raw["records"]:
        p = ROOT / entry["record_file"]
        if _sha256_file(p) != entry["record_sha256"]:
            raise SystemExit(f"v2 record hash mismatch: {p.name}")

    frozen = _load_json(BENCH_MANIFEST)
    body = frozen["body"]
    by_case = {c["case_id"]: c for c in body["cases"]}
    v1_lags = load_frozen_v1_lags()

    tolerances = (0.05, 0.10, 0.15)
    per_case = []
    for rec in sorted(records, key=lambda r: r["case_id"]):
        cid = rec["case_id"]
        case = by_case[cid]
        row = {"case_id": cid, "pair_type": case["pair_type"],
               "source_slot": case["source_slot"],
               "gt_offset_s": case["gt_offset_s"],
               "input_hashes_match_manifest": (
                   rec["input_sha256"]["trimmed_input"]
                   == case["trimmed_input_sha256"]
                   and rec["input_sha256"]["reference"]
                   == case["reference_sha256"]),
               "v1_lag_samples": v1_lags[cid],
               "v2_lag_samples": rec["native_scores"]["lag_samples"],
               "lag_changed_by_correction": (
                   v1_lags[cid] != rec["native_scores"]["lag_samples"]),
               "v1_predicted_offset_s": v1_lags[cid] / 48000,
               "v2_predicted_offset_s": rec["predicted_offset_s"],
               "outcomes": {}, "abs_errors": {}}
        for tol in tolerances:
            scored = scoring.score_pair(case, rec, tol)
            row["outcomes"][f"{tol:.2f}"] = scored["outcome"]
            row["abs_errors"][f"{tol:.2f}"] = scored["abs_error_s"]
        per_case.append(row)

    summary = {}
    for tol in tolerances:
        key = f"{tol:.2f}"
        counts = {}
        for row in per_case:
            counts[row["outcomes"][key]] = \
                counts.get(row["outcomes"][key], 0) + 1
        summary[key] = counts

    v1_comparison = {
        "changed_lag_records": sorted(row["case_id"] for row in per_case
                                      if row["lag_changed_by_correction"]),
        "outcome_changes_any_tolerance": sorted(
            row["case_id"] for row in per_case
            if _v1_outcome(row["case_id"], 0.10)
            != row["outcomes"]["0.10"]),
        "note": ("v1 outcomes recomputed with the frozen scoring contract "
                 "from the sealed v1 raw records; the corrected unwrap "
                 "changes only reported lag magnitudes, never the "
                 "argmax index or decision"),
    }
    results = {
        "status": "GCC_PHAT_V2_LAGFIX_RESULTS",
        "final_confirmatory_evidence": FINAL_MARK,
        "not_pilot_not_development": True,
        "system": v2.SYSTEM_ID,
        "correction_manifest_freeze_sha256": manifest_value["freeze_hash"],
        "raw_assembly_sha256": got,
        "tolerances_s": list(tolerances),
        "scoring": "frozen experiments/applied_system/scoring.py contract; "
                   "no new threshold; ALWAYS_OUTPUT semantics preserved",
        "summary_outcome_counts_by_tolerance": summary,
        "per_case": per_case,
        "comparison_vs_frozen_v1": v1_comparison,
    }
    _save_json(V2_RESULTS, results)
    write_hash_sidecar(V2_RESULTS)
    print(f"wrote {V2_RESULTS.name}")
    for key, counts in summary.items():
        print(f"  tolerance {key}: {counts}")
    print(f"  changed-lag records: {v1_comparison['changed_lag_records']}")
    print(f"  outcome changes at 100 ms: "
          f"{v1_comparison['outcome_changes_any_tolerance']}")


def _read_sidecar_digest(path: Path) -> str:
    return path.with_suffix(path.suffix + ".sha256").read_text(
        encoding="utf-8").split()[0]


def _v1_outcome(case_id: str, tol: float) -> str:
    """Recompute the frozen v1 outcome from the sealed v1 record."""
    frozen = _load_json(BENCH_MANIFEST)
    case = next(c for c in frozen["body"]["cases"]
                if c["case_id"] == case_id)
    rec = _load_json(V1_RECORDS_DIR
                     / f"{gcc_phat_runner.SYSTEM_ID}__{case_id}.json")
    if _sha256_file(V1_RECORDS_DIR
                    / f"{gcc_phat_runner.SYSTEM_ID}__{case_id}.json") \
            != rec_sha(case_id):
        raise SystemExit("v1 record hash mismatch in outcome recomputation")
    return scoring.score_pair(case, rec, tol)["outcome"]


def rec_sha(case_id: str) -> str:
    raw = _load_json(V1_RAW)
    entry = next(e for e in raw["records"]
                 if e["record_file"].endswith(
                     f"{gcc_phat_runner.SYSTEM_ID}__{case_id}.json"))
    return entry["record_sha256"]


if __name__ == "__main__":
    cmds = {"freeze-manifest": cmd_freeze_manifest, "rerun": cmd_rerun,
            "score": cmd_score}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        raise SystemExit(f"usage: {sys.argv[0]} "
                         f"{{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
