"""Frozen FINAL benchmark execution — the one confirmatory run.

FINAL CONFIRMATORY EVIDENCE (pilot/shakedown machinery is development-only).

Authority: docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md (frozen
before final data collection). This module only ASSEMBLES frozen inputs and
RUNS frozen systems; it never tunes, rescues, retakes, or reinterprets.

Stages (run in this order, each verifying the previous one):

  1. build_kdenlive_owner_run_freeze()  — write-once owner-run evidence
     summary proving the ten saved Kdenlive projects existed BEFORE any
     performance scoring (protocol section 3 of the execution task).
  2. score_kdenlive()                    — placement scoring of the ten
     valid scoring runs from saved project XML (never from owner reports).
  3. build_benchmark_manifest()          — frozen automated-case manifest:
     24 EXACT_GT positives, 24 NO_MATCH wrong-reference pairs under the
     frozen rotation S(i mod 10)+1, 2 strict repeats kept separate.
  4. run_comparators()                   — single pass of the four frozen
     systems over the frozen manifest, raw records preserved immutably.
  5. score_comparators()                 — scoring at 50/100/150 ms,
     selective-risk metrics, condition/source aggregation, song-level
     bootstrap, exact discordant counts, strict-repeat reliability.

FINAL DATA MUST NOT BE USED TO CHANGE THE FROZEN PROTOCOL.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

if __package__:
    from .kdenlive_project_xml import summarize_file
    from .runners import common
    from .runners import gcc_phat_runner, ncc_runner, panako_runner
    from .runners import rhythmalign_runner
    from .scoring import (OUTCOME_CORRECT_ACCEPT, OUTCOME_GT_FAILED,
                          OUTCOME_RUNNER_ERROR, OUTCOME_SAFE_ABSTAIN,
                          OUTCOME_WRONG_ACCEPT, TOLERANCE_S_PRIMARY,
                          TOLERANCE_SENSITIVITIES_S, score_pair)
else:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.applied_system.kdenlive_project_xml import summarize_file
    from experiments.applied_system.runners import common
    from experiments.applied_system.runners import (gcc_phat_runner,
                                                    ncc_runner,
                                                    panako_runner,
                                                    rhythmalign_runner)
    from experiments.applied_system.scoring import (
        OUTCOME_CORRECT_ACCEPT, OUTCOME_GT_FAILED, OUTCOME_RUNNER_ERROR,
        OUTCOME_SAFE_ABSTAIN, OUTCOME_WRONG_ACCEPT, TOLERANCE_S_PRIMARY,
        TOLERANCE_SENSITIVITIES_S, score_pair)

# 50/100/150 ms; 100 ms is the frozen primary, 50/150 the frozen
# sensitivities. Canonical JSON keys via %g: "0.05", "0.1", "0.15".
TOLERANCES = (0.050, TOLERANCE_S_PRIMARY, 0.150)


def _tol_key(tol: float) -> str:
    return f"{tol:g}"

ROOT = Path(__file__).resolve().parents[2]
APPLIED_DIR = Path(__file__).resolve().parent
PACK_DIR = APPLIED_DIR / "final_pack"
KDENLIVE_DIR = PACK_DIR / "kdenlive"
OWNER_PACK = KDENLIVE_DIR / "owner_pack"
RESULTS_DIR = PACK_DIR / "results"
LOCAL_DIR = PACK_DIR / "local"
TRIMMED_DIR = LOCAL_DIR / "final_qc_work" / "trimmed"
REFERENCES_DIR = LOCAL_DIR / "references"

MANIFEST_PATH = PACK_DIR / "final_acquisition_manifest.json"
QC_PATH = RESULTS_DIR / "final_acquisition_qc.json"
BENCH_MANIFEST_PATH = RESULTS_DIR / "final_benchmark_manifest.json"
RAW_RECORDS_DIR = RESULTS_DIR / "final_comparator_raw_records"
RAW_PATH = RESULTS_DIR / "final_comparator_raw.json"
SCORES_PATH = RESULTS_DIR / "final_benchmark_results.json"
SCORES_CSV_PATH = RESULTS_DIR / "final_benchmark_results.csv"
KDENLIVE_RESULTS_PATH = RESULTS_DIR / "final_kdenlive_results.json"
ENV_PATH = RESULTS_DIR / "final_comparator_environment.json"

OWNER_RUN_FREEZE_PATH = KDENLIVE_DIR / "kdenlive_owner_run_freeze.json"
PAIR_FREEZE_PATH = KDENLIVE_DIR / "kdenlive_pair_freeze.json"
RUN_POLICY_PATH = KDENLIVE_DIR / "kdenlive_run_policy.json"
KDENV_PATH = KDENLIVE_DIR / "kdenlive_environment.json"
PACK_MANIFEST_PATH = KDENLIVE_DIR / "kdenlive_owner_pack_manifest.json"
RERUN_MANIFEST_PATH = KDENLIVE_DIR / "kdenlive_owner_pack_rerun_manifest.json"
TIMING_LOG_PATH = OWNER_PACK / "timing_log.jsonl"
PAIR01_EVIDENCE_DIR = KDENLIVE_DIR / "owner_run_evidence" / "pair01_run1"

PROCEDURE_V2 = "KDENLIVE-PLACEMENT-V2"
REQUIRED_BRANCH = "research/applied-system-paper"
SUBJECT_COMMIT = "3a622fc33af1212178296ad9dad57ce9693eed48"
PANAKO_PINNED_COMMIT = panako_runner.PANAKO_PINNED_COMMIT
PANAKO_JAR_SHA256 = "77c56eabf93defe64ddddf0fb75478c415dc7b64ddb065b5a34a27f6b9fb2276"
BOOTSTRAP_REPLICATES = 10000
BOOTSTRAP_SEED = 20260920

FINAL_MARK = "FINAL_CONFIRMATORY_EVIDENCE"

SYSTEM_IDS = (
    rhythmalign_runner.SYSTEM_ID,
    gcc_phat_runner.SYSTEM_ID,
    panako_runner.SYSTEM_ID,
    ncc_runner.SYSTEM_ID,
)
RUNNERS = {
    rhythmalign_runner.SYSTEM_ID: rhythmalign_runner.run_case,
    gcc_phat_runner.SYSTEM_ID: gcc_phat_runner.run_case,
    panako_runner.SYSTEM_ID: panako_runner.run_case,
    ncc_runner.SYSTEM_ID: ncc_runner.run_case,
}
ALWAYS_OUTPUT_SYSTEMS = (gcc_phat_runner.SYSTEM_ID, ncc_runner.SYSTEM_ID)
SELECTIVE_SYSTEMS = (rhythmalign_runner.SYSTEM_ID, panako_runner.SYSTEM_ID)


# ---------------------------------------------------------------------------
# small shared helpers (canonical JSON, hashing, write-once freezes)
# ---------------------------------------------------------------------------


def _canonical_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_canonical_bytes(value).decode("utf-8") + "\n")


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=str(ROOT),
                              capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:
        return ""


def require_research_branch() -> None:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != REQUIRED_BRANCH:
        raise SystemExit(f"refusing to run on branch {branch!r}; "
                         f"final evidence requires {REQUIRED_BRANCH!r}")


def verify_frozen_artifact(value: dict, hash_key: str = "freeze_hash") -> list:
    if not isinstance(value, dict) or not isinstance(value.get("body"), dict):
        return ["malformed frozen artifact"]
    declared = value.get(hash_key)
    actual = hashlib.sha256(_canonical_bytes(value["body"])).hexdigest()
    return ([] if declared == actual
            else [f"{hash_key} mismatch: {declared} != {actual}"])


def freeze_artifact(path: Path, body: dict, hash_key: str = "freeze_hash"):
    """Write once. A second identical call is a no-op; any edit fails."""
    digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    wrapped = {hash_key: digest, "body": body}
    if path.exists():
        current = _load_json(path)
        errors = verify_frozen_artifact(current, hash_key)
        if errors:
            raise RuntimeError(f"immutable artifact {path} is invalid: {errors}")
        if current != wrapped:
            raise RuntimeError("immutable artifact already exists with "
                               f"different content: {path}")
        return current
    _save_json(path, wrapped)
    return wrapped


def write_hash_sidecar(path: Path) -> str:
    digest = _sha256_file(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    expected = f"{digest}  {path.name}\n"
    if sidecar.exists():
        if sidecar.read_text(encoding="utf-8") != expected:
            raise RuntimeError(f"immutable hash sidecar differs: {sidecar}")
    else:
        sidecar.write_text(expected, encoding="utf-8", newline="\n")
    return digest


def _final_labels(extra: dict | None = None) -> dict:
    labels = {"final_confirmatory_evidence": FINAL_MARK,
              "not_pilot_not_development": True}
    if extra:
        labels.update(extra)
    return labels


# ---------------------------------------------------------------------------
# frozen-input loading and verification
# ---------------------------------------------------------------------------


def load_verified_authority() -> tuple:
    """Load the frozen acquisition manifest + QC, verifying their embedded
    canonical hashes against recomputation."""
    manifest = _load_json(MANIFEST_PATH)
    body = manifest["body"]
    declared = manifest["manifest_hash"]
    actual = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    if declared != actual:
        raise SystemExit("acquisition manifest hash mismatch")
    qc = _load_json(QC_PATH)
    qc_body = qc["body"]
    declared_qc = qc["qc_freeze_sha256"]
    actual_qc = hashlib.sha256(_canonical_bytes(qc_body)).hexdigest()
    if declared_qc != actual_qc:
        raise SystemExit("acquisition QC freeze hash mismatch")
    if qc_body.get("verdict") != "FINAL_QC_PASS":
        raise SystemExit(f"QC verdict is {qc_body.get('verdict')!r}; "
                         "refusing to run comparators")
    return manifest, qc


def qc_take_index(qc_body: dict) -> dict:
    return {row["take"]: row for row in qc_body["raw_recordings"]}


# ---------------------------------------------------------------------------
# stage 1 — pre-scoring owner-run evidence freeze (execution task section 3)
# ---------------------------------------------------------------------------


def _timing_records() -> tuple:
    records = [json.loads(line) for line in
               TIMING_LOG_PATH.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    return records, _sha256_file(TIMING_LOG_PATH)


def build_kdenlive_owner_run_freeze() -> dict:
    """Write-once evidence that the ten scoring projects existed before any
    performance scoring. Contains NO scored correctness."""
    require_research_branch()
    pair_freeze = _load_json(PAIR_FREEZE_PATH)
    errors = verify_frozen_artifact(pair_freeze, "pair_freeze_sha256")
    if errors:
        raise SystemExit(f"pair freeze invalid: {errors}")
    policy = _load_json(RUN_POLICY_PATH)
    kdenv = _load_json(KDENV_PATH)
    pack_manifest = _load_json(PACK_MANIFEST_PATH)
    rerun_manifest = _load_json(RERUN_MANIFEST_PATH)
    pairs = pair_freeze["body"]["pairs"]

    scoring_runs = {}
    void_runs = {}
    for pid in sorted(pairs):
        rule = policy["rules"].get(pid)
        if rule:
            scoring_runs[pid] = rule["scoring_run"]
            void_runs.update({rid: rule["void_reason"]
                              for rid in rule["void_runs"]})
        else:
            scoring_runs[pid] = pid

    # pack media still match the frozen pack + rerun manifests
    for pid, entry in pack_manifest["pairs"].items():
        for role, key, want in (
                ("recording", "recording", entry["recording_sha256"]),
                ("reference", "reference", entry["reference_sha256"])):
            got = _sha256_file(OWNER_PACK / pid / f"{role}.wav")
            if got != want:
                raise SystemExit(f"pack media drift: {pid}/{role}")
    for rid, entry in rerun_manifest["reruns"].items():
        for role, want in (("recording", entry["recording_sha256"]),
                           ("reference", entry["reference_sha256"])):
            got = _sha256_file(OWNER_PACK / rid / f"{role}.wav")
            if got != want:
                raise SystemExit(f"rerun media drift: {rid}/{role}")

    timing_records, timing_log_sha256 = _timing_records()
    timing_by_pair = {r["pair"]: r for r in timing_records}

    projects = {}
    for pid in sorted(pairs):
        run_id = scoring_runs[pid]
        path = OWNER_PACK / run_id / f"{run_id}.kdenlive"
        if not path.exists():
            raise SystemExit(f"scoring project missing: {path}")
        projects[pid] = {
            "canonical_pair": pid,
            "take": pairs[pid]["take"],
            "condition": pairs[pid]["condition"],
            "source_slot": pairs[pid]["source_slot"],
            "scoring_run": run_id,
            "project_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "project_sha256": _sha256_file(path),
            "project_bytes": path.stat().st_size,
            "operator_elapsed_seconds": (
                timing_by_pair[run_id]["elapsed_seconds"]
                if run_id in timing_by_pair else None),
            "operator_time_status": (
                "TIMED" if run_id in timing_by_pair else
                "NOT_TIMED_OWNER_APPROVED_GAP"),
            "native_owner_observation": (
                timing_by_pair[run_id]["observation"]
                if run_id in timing_by_pair else None),
        }
    untimed = [p["scoring_run"] for p in projects.values()
               if p["operator_time_status"] != "TIMED"]

    evidence_files = {}
    for path in sorted(PAIR01_EVIDENCE_DIR.iterdir()):
        if path.is_file():
            evidence_files[path.name] = {
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }

    body = {
        "status": "KDENLIVE_OWNER_RUN_FROZEN_PRE_SCORING",
        "created_utc": _utc_now(),
        "final_confirmatory_evidence": FINAL_MARK,
        "authority": {
            "protocol": "docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md",
            "pair01_audit": "docs/research/applied_system/KDENLIVE_PAIR01_AUDIT.md",
            "procedure": PROCEDURE_V2,
            "placement_headroom_seconds": policy["placement_headroom_seconds"],
        },
        "frozen_hashes": {
            "pair_freeze_sha256": pair_freeze["pair_freeze_sha256"],
            "run_policy_sha256": _sha256_file(RUN_POLICY_PATH),
            "kdenlive_environment_sha256": _sha256_file(KDENV_PATH),
            "owner_pack_manifest_sha256": _sha256_file(PACK_MANIFEST_PATH),
            "rerun_manifest_sha256": _sha256_file(RERUN_MANIFEST_PATH),
            "kdenlive_version": kdenv["version"],
            "kdenlive_exe_sha256": kdenv["exe_sha256"],
            "timing_log_sha256": timing_log_sha256,
        },
        "valid_scoring_run_set": sorted(
            {p["scoring_run"] for p in projects.values()}),
        "void_runs": void_runs,
        "projects": projects,
        "timing_log_records": timing_records,
        "timing_gap_note": (
            "pair01r2 was saved without a timer record (project save "
            "06:29Z postdates the last log write 06:18Z); the owner "
            "approved proceeding with the gap documented on 2026-09-20; "
            "operator-time statistics cover the 9 timed valid runs and "
            "never impute or fabricate the missing value"
            if untimed else "all scoring runs timed"),
        "pair01_v1_void_evidence": {
            "evidence_dir": str(PAIR01_EVIDENCE_DIR.relative_to(ROOT)).replace("\\", "/"),
            "void_reason": void_runs.get("pair01"),
            "files": evidence_files,
            "never_scored": True,
        },
        "no_scores_in_this_freeze": ("this artifact proves existence before "
                                     "scoring and contains no placement, "
                                     "offset, or correctness value"),
    }
    return freeze_artifact(OWNER_RUN_FREEZE_PATH, body,
                           "owner_run_freeze_sha256")


# ---------------------------------------------------------------------------
# stage 2 — Kdenlive placement scoring from saved project XML (section 4)
# ---------------------------------------------------------------------------


def _require_owner_run_freeze() -> dict:
    if not OWNER_RUN_FREEZE_PATH.exists():
        raise SystemExit("owner-run freeze missing; run stage 1 first")
    freeze = _load_json(OWNER_RUN_FREEZE_PATH)
    errors = verify_frozen_artifact(freeze, "owner_run_freeze_sha256")
    if errors:
        raise SystemExit(f"owner-run freeze invalid: {errors}")
    return freeze


def _median_iqr_max(values: list) -> dict:
    if not values:
        return {"n": 0, "median_s": None, "iqr25_s": None, "iqr75_s": None,
                "max_s": None}
    arr = np.sort(np.asarray(values, dtype=float))
    q25, med, q75 = np.percentile(arr, [25, 50, 75])
    return {"n": int(arr.size), "median_s": float(med),
            "iqr25_s": float(q25), "iqr75_s": float(q75),
            "max_s": float(arr[-1])}


def score_kdenlive() -> dict:
    """Score the ten valid scoring runs from project XML against frozen GT.

    Offset semantics (frozen family convention): predicted_offset_s is where
    the reference's content-start sits on the trimmed-capture timebase, so
    predicted = (reference.start_frame − recording.start_frame) / fps. The
    common 180 s V2 headroom cancels in this difference (proven invariance).
    """
    require_research_branch()
    owner_freeze = _require_owner_run_freeze()
    _manifest, qc = load_verified_authority()
    qc_index = qc_take_index(qc["body"])
    pair_freeze = _load_json(PAIR_FREEZE_PATH)["body"]["pairs"]
    policy = _load_json(RUN_POLICY_PATH)

    per_pair = []
    for pid in sorted(pair_freeze):
        proj = owner_freeze["body"]["projects"][pid]
        run_id = proj["scoring_run"]
        path = ROOT / proj["project_path"]
        # the file scored must be byte-identical to the pre-scoring freeze
        if _sha256_file(path) != proj["project_sha256"]:
            raise SystemExit(f"project changed after pre-scoring freeze: {path}")
        expected = {"recording": "recording.wav", "reference": "reference.wav"}
        summary = summarize_file(path, expected)
        take = pair_freeze[pid]["take"]
        gt = qc_index[take]["derived_reference_offset_on_trimmed_input_s"]
        row = {
            "canonical_pair": pid,
            "scoring_run": run_id,
            "take": take,
            "condition": proj["condition"],
            "source_slot": proj["source_slot"],
            "profile_frame_rate": summary["profile_frame_rate"],
            "state": summary["state"],
            "failures": summary["failures"],
            "placements": summary["placements"],
            "clip_offset_frames": summary["clip_offset_frames"],
            "gt_offset_s": gt,
            "predicted_offset_s": None,
            "abs_error_s": None,
            "outcome_by_tolerance_s": {},
            "operator_elapsed_seconds": proj["operator_elapsed_seconds"],
            "operator_time_status": proj["operator_time_status"],
            "native_owner_observation": proj["native_owner_observation"],
        }
        if summary["state"] != "OK" or summary["clip_offset_frames"] is None:
            row["outcome_by_tolerance_s"] = {
                _tol_key(t): "NATIVE_FAILURE" for t in TOLERANCES}
        else:
            predicted = (-summary["clip_offset_frames"]
                         / summary["profile_frame_rate"])
            row["predicted_offset_s"] = predicted
            err = abs(predicted - gt)
            row["abs_error_s"] = err
            for tol in TOLERANCES:
                row["outcome_by_tolerance_s"][_tol_key(tol)] = (
                    OUTCOME_CORRECT_ACCEPT
                    if err <= tol + 1e-12 else OUTCOME_WRONG_ACCEPT)
        per_pair.append(row)

    def _bucket(tol_key: str) -> dict:
        counts = {"CORRECT_ACCEPT": 0, "WRONG_ACCEPT": 0, "NATIVE_FAILURE": 0}
        for row in per_pair:
            counts[row["outcome_by_tolerance_s"][tol_key]] += 1
        return counts

    produced_errors = [row["abs_error_s"] for row in per_pair
                       if row["abs_error_s"] is not None]
    correct_errors = [row["abs_error_s"] for row in per_pair
                      if row["outcome_by_tolerance_s"].get(_tol_key(0.1))
                      == OUTCOME_CORRECT_ACCEPT]
    timed = [row["operator_elapsed_seconds"] for row in per_pair
             if row["operator_time_status"] == "TIMED"]
    agg = {
        "tolerances_s": [_tol_key(t) for t in TOLERANCES],
        "primary_counts_at_100ms": _bucket(_tol_key(0.1)),
        "counts_at_50ms": _bucket(_tol_key(0.05)),
        "counts_at_150ms": _bucket(_tol_key(0.15)),
        "produced_placement_abs_error_s": _median_iqr_max(produced_errors),
        "correct_accept_conditional_abs_error_s": _median_iqr_max(correct_errors),
        "operator_time": {
            "timed_runs": len(timed),
            "untimed_runs": [row["scoring_run"] for row in per_pair
                             if row["operator_time_status"] != "TIMED"],
            "median_s": float(np.median(timed)) if timed else None,
            "iqr25_s": float(np.percentile(timed, 25)) if timed else None,
            "iqr75_s": float(np.percentile(timed, 75)) if timed else None,
            "total_s": float(np.sum(timed)) if timed else None,
            "note": ("9/10 valid scoring runs timed; pair01r2 saved without "
                     "a timer record; owner approved proceeding with the "
                     "gap documented; void pair01 V1 run never enters stats"),
        },
    }
    body = {
        "status": "FINAL_KDENLIVE_STRATUM_SCORED",
        "created_utc": _utc_now(),
        **_final_labels(),
        "authority": {
            "owner_run_freeze_sha256": owner_freeze["owner_run_freeze_sha256"],
            "run_policy_status": policy["status"],
            "procedure": PROCEDURE_V2,
            "pair_freeze_sha256": _load_json(PAIR_FREEZE_PATH)["pair_freeze_sha256"],
            "qc_freeze_sha256": _load_json(QC_PATH)["qc_freeze_sha256"],
        },
        "scoring_semantics": {
            "predicted_offset_s": ("(reference.start_frame − "
                                   "recording.start_frame) / fps; headroom-"
                                   "invariant placement difference"),
            "gt_offset_s": ("QC derived_reference_offset_on_trimmed_input_s "
                            "of the pair's take"),
            "native_failure_states": ["MISSING_EXPECTED_CLIP",
                                      "NOT_PLACED_ON_TIMELINE", "INCOMPLETE"],
        },
        "valid_scoring_pairs": len(per_pair),
        "per_pair": per_pair,
        "aggregates": agg,
        "exclusions": {
            "pair01_run1": ("void for scoring "
                            "(PROCEDURE_V1_TIMELINE_ZERO_LEFT_BOUNDARY); "
                            "evidence-only; never in any count"),
        },
    }
    _save_json(KDENLIVE_RESULTS_PATH, {"kdenlive_results_sha256": None,
                                       "body": body})
    # canonical self-hash: hash of the body with the wrapper's hash nulled
    wrapped = _load_json(KDENLIVE_RESULTS_PATH)
    wrapped["kdenlive_results_sha256"] = hashlib.sha256(
        _canonical_bytes(wrapped["body"])).hexdigest()
    _save_json(KDENLIVE_RESULTS_PATH, wrapped)
    write_hash_sidecar(KDENLIVE_RESULTS_PATH)
    print(f"kdenlive scored: {agg['primary_counts_at_100ms']}")
    return wrapped


# ---------------------------------------------------------------------------
# stage 3 — frozen automated-case manifest (execution task section 6)
# ---------------------------------------------------------------------------


def _repo_rel(path: Path) -> str:
    return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


def build_benchmark_manifest() -> dict:
    require_research_branch()
    manifest, qc = load_verified_authority()
    body = manifest["body"]
    qc_index = qc_take_index(qc["body"])
    slots = body["slots"]
    ref_paths = {}
    for ref_id, entry in body["references"].items():
        p = Path(entry["path"])
        if not p.exists():
            p = ROOT / "experiments/applied_system/final_pack/local/references" / f"{ref_id}.wav"
        if not p.exists():
            raise SystemExit(f"reference missing: {ref_id}")
        got = _sha256_file(p)
        if got != entry["sha256"]:
            raise SystemExit(f"reference hash drift: {ref_id}")
        ref_paths[ref_id] = (_repo_rel(p), entry["sha256"])

    cases = []
    for take in sorted(body["takes"]):
        row = body["takes"][take]
        qc_row = qc_index[take]
        if qc_row["gt_status"] != "GT_VALID":
            raise SystemExit(f"{take}: GT not valid under frozen QC; the "
                             "execution gate requires 26/26 GT_VALID")
        trimmed_rel = _repo_rel(TRIMMED_DIR / f"{take}.wav")
        got = _sha256_file(ROOT / trimmed_rel)
        if got != qc_row["trimmed_input_sha256"]:
            raise SystemExit(f"trimmed input hash drift: {take}")
        shared = {
            "take": take,
            "condition": row["condition"],
            "source_slot": row["source_slot"],
            "session": row["session"],
            "room": row["room"],
            "recording_device": row["recording_device"],
            "playback_device": row["playback_device"],
            "primary": bool(row["primary"]),
            "trimmed_input_path": trimmed_rel,
            "trimmed_input_sha256": qc_row["trimmed_input_sha256"],
            "comparator_eligibility": list(SYSTEM_IDS),
        }
        if row["primary"]:
            correct_slot = row["source_slot"]
            cases.append({
                **shared, "case_id": f"{take}__positive",
                "pair_type": "POSITIVE", "gt_stratum": "EXACT_GT",
                "reference_id": f"REF-{correct_slot}",
                "gt_offset_s":
                    qc_row["derived_reference_offset_on_trimmed_input_s"],
                "expected_label": "MATCH",
            })
            # frozen wrong-reference rotation S(i mod 10)+1 over take number
            i = int(re.fullmatch(r"final(\d{2})", take).group(1))
            expect_slot = f"S{(i % 10) + 1:02d}"
            if row["wrong_reference_slot"] != expect_slot:
                raise SystemExit(f"{take}: wrong-reference slot "
                                 f"{row['wrong_reference_slot']} violates the "
                                 f"frozen rotation {expect_slot}")
            wrong_id = f"REF-{row['wrong_reference_slot']}"
            # the take's frozen wrong_reference_sha256 is the SOURCE
            # identity hash; tie it to the reference WAV via its recorded
            # source_sha256 (the WAV hash itself was verified above)
            if body["references"][wrong_id].get("source_sha256") != \
                    row["wrong_reference_sha256"]:
                raise SystemExit(f"{take}: wrong-reference source identity "
                                 "does not match the frozen reference WAV")
            cases.append({
                **shared, "case_id": f"{take}__wrong_ref",
                "pair_type": "WRONG_REFERENCE", "gt_stratum": "NO_MATCH",
                "reference_id": wrong_id,
                "gt_offset_s": None, "expected_label": "NO_MATCH",
            })
        else:
            cases.append({
                **shared, "case_id": f"{take}__positive",
                "pair_type": "POSITIVE", "gt_stratum": "EXACT_GT",
                "reference_id": f"REF-{row['source_slot']}",
                "gt_offset_s":
                    qc_row["derived_reference_offset_on_trimmed_input_s"],
                "expected_label": "MATCH",
                "reliability_only": True,
                "note": ("strict repeat; reported separately from primary "
                         "counts; carries no wrong-reference case"),
            })
    for case in cases:
        case["reference_path"], case["reference_sha256"] = \
            ref_paths[case["reference_id"]]

    n_pos = sum(1 for c in cases if c["pair_type"] == "POSITIVE"
                and c.get("primary"))
    n_wrong = sum(1 for c in cases if c["pair_type"] == "WRONG_REFERENCE")
    n_rep = sum(1 for c in cases if c.get("reliability_only"))
    if (n_pos, n_wrong, n_rep) != (24, 24, 2):
        raise SystemExit(f"population mismatch: pos={n_pos} wrong={n_wrong} "
                         f"repeats={n_rep}")

    freeze_body = {
        "status": "FINAL_BENCHMARK_MANIFEST_FROZEN",
        "created_utc": _utc_now(),
        **_final_labels(),
        "authority": {
            "acquisition_manifest_hash": manifest["manifest_hash"],
            "qc_freeze_sha256": _load_json(QC_PATH)["qc_freeze_sha256"],
            "wrong_reference_rule": body["wrong_reference_rule"],
            "subject": {
                "rhythmalign": {"release": "v1.2.0", "commit": SUBJECT_COMMIT},
                "gcc_phat": gcc_phat_runner.SYSTEM_ID,
                "ncc": ncc_runner.SYSTEM_ID,
                "panako": {"commit": PANAKO_PINNED_COMMIT,
                           "jar_sha256": PANAKO_JAR_SHA256,
                           "strategy": panako_runner.PANAKO_STRATEGY},
            },
        },
        "counts": {"primary_positives": n_pos, "wrong_reference": n_wrong,
                   "strict_repeats": n_rep},
        "cases": sorted(cases, key=lambda c: c["case_id"]),
    }
    return freeze_artifact(BENCH_MANIFEST_PATH, freeze_body)


# ---------------------------------------------------------------------------
# stage 4 — single-pass comparator execution (sections 5-11)
# ---------------------------------------------------------------------------


def _record_path(system: str, case_id: str) -> Path:
    return RAW_RECORDS_DIR / f"{system}__{case_id}.json"


def _finalize_record(record: common.RunnerRecord, input_sha: str,
                     ref_sha: str) -> dict:
    value = record.as_dict()
    value.pop("shakedown_only", None)
    value.pop("not_paper_evidence", None)
    value.pop("warning", None)
    value["final_confirmatory_evidence"] = FINAL_MARK
    value["input_sha256"] = {"trimmed_input": input_sha, "reference": ref_sha}
    return value


def run_comparators(resume_if_interrupted: bool = True) -> list:
    """Single pass over the frozen manifest. A case already holding an
    immutable first-pass record is never re-run (crash-recovery keeps the
    first-pass result; results are never regenerated)."""
    require_research_branch()
    frozen = _load_json(BENCH_MANIFEST_PATH)
    errors = verify_frozen_artifact(frozen)
    if errors:
        raise SystemExit(f"benchmark manifest invalid: {errors}")
    if RAW_PATH.exists() and not resume_if_interrupted:
        raise SystemExit("raw assembly already exists; single-pass benchmark "
                         "refuses a second run")
    import soundfile as sf
    records = []
    expected_pairs = [(system, case["case_id"])
                      for case in frozen["body"]["cases"]
                      for system in case["comparator_eligibility"]]
    for case in frozen["body"]["cases"]:
        input_path = ROOT / case["trimmed_input_path"]
        reference_path = ROOT / case["reference_path"]
        actual_input = _sha256_file(input_path)
        actual_ref = _sha256_file(reference_path)
        for system in case["comparator_eligibility"]:
            path = _record_path(system, case["case_id"])
            if path.exists():
                records.append(_load_json(path))
                continue
            if (actual_input != case["trimmed_input_sha256"]
                    or actual_ref != case["reference_sha256"]):
                record = common.RunnerRecord(
                    system=system, case_id=case["case_id"],
                    decision=common.DECISION_ERROR, predicted_offset_s=None,
                    native_scores={"error": "input/reference hash mismatch "
                                            "against frozen manifest"})
                value = _finalize_record(record, actual_input, actual_ref)
            else:
                fs = int(sf.info(str(input_path)).samplerate)
                record = RUNNERS[system](case, input_path, reference_path,
                                         fs, _load_audio_same_rate)
                value = _finalize_record(record, actual_input, actual_ref)
            _save_json(path, value)
            write_hash_sidecar(path)
            records.append(value)
            print(f"  {system} {case['case_id']}: {record.decision}")
    have = {(r["system"], r["case_id"]) for r in records}
    missing = [pair for pair in expected_pairs if pair not in have]
    if missing:
        raise SystemExit(f"records missing after pass: {missing[:5]}…")
    _save_raw_assembly(frozen)
    if not ENV_PATH.exists():
        _save_json(ENV_PATH, _final_environment())
        write_hash_sidecar(ENV_PATH)
    return records


def _load_audio_same_rate(path: Path, fs: int) -> np.ndarray:
    import soundfile as sf
    y, sr = sf.read(str(path), dtype="float64", always_2d=False)
    if sr != fs:
        raise ValueError(f"{path}: sample rate {sr} != frozen input rate {fs}")
    if y.ndim > 1:
        y = y.mean(axis=1)
    return np.ascontiguousarray(y)


def _save_raw_assembly(frozen: dict) -> None:
    """final_comparator_raw.json — immutable raw-first assembly. Each
    per-record file keeps its own hash; the assembly is deterministic from
    the record files (no timestamps) and, once written, never changes."""
    index = {
        "status": "FINAL_COMPARATOR_RAW",
        **_final_labels(),
        "manifest_freeze_sha256": frozen["freeze_hash"],
        "single_pass": ("each (system, case) ran exactly once; existing "
                        "first-pass records are never regenerated"),
        "records": [],
    }
    for path in sorted(RAW_RECORDS_DIR.glob("*.json")):
        index["records"].append({
            "record_file": _repo_rel(path),
            "record_sha256": _sha256_file(path),
        })
    if RAW_PATH.exists():
        current = _load_json(RAW_PATH)
        if current != index:
            raise RuntimeError("raw assembly already exists with different "
                               f"content: {RAW_PATH}")
    else:
        _save_json(RAW_PATH, index)
        write_hash_sidecar(RAW_PATH)


def _final_environment() -> dict:
    env = common.capture_environment()
    env.pop("shakedown_only", None)
    env.pop("not_paper_evidence", None)
    env.pop("warning", None)
    env.update(_final_labels())
    env["research_head_at_run"] = _git("rev-parse", "HEAD")
    env["production_subject"] = {
        "release": "v1.2.0",
        "tag_commit": SUBJECT_COMMIT,
        "head_matches_tag_production_files": _production_unchanged(),
    }
    env["panako_pinned_jar_sha256"] = PANAKO_JAR_SHA256
    return env


def _production_unchanged() -> bool:
    changed = _git("diff", "--name-only", f"{SUBJECT_COMMIT}..HEAD")
    production = [line for line in changed.splitlines()
                  if line and not re.match(
                      r"^(experiments|docs|tests|archive|\.zcode)/", line)]
    return production == [] or production == [".gitattributes"]


# ---------------------------------------------------------------------------
# stage 5 — scoring and aggregation (sections 12-18)
# ---------------------------------------------------------------------------


def _load_raw_records() -> list:
    if not RAW_PATH.exists():
        raise SystemExit("raw assembly missing; run stage 4 first")
    assembly = _load_json(RAW_PATH)
    expected = {rec["record_file"]: rec["record_sha256"]
                for rec in assembly["records"]}
    records = []
    for rel, want in sorted(expected.items()):
        path = ROOT / rel
        got = _sha256_file(path)
        if got != want:
            raise SystemExit(f"raw record mutated after freeze: {rel}")
        records.append(_load_json(path))
    return records


def score_comparators() -> dict:
    require_research_branch()
    frozen = _load_json(BENCH_MANIFEST_PATH)
    errors = verify_frozen_artifact(frozen)
    if errors:
        raise SystemExit(f"benchmark manifest invalid: {errors}")
    cases = {c["case_id"]: c for c in frozen["body"]["cases"]}
    records = _load_raw_records()
    by_key = {(r["system"], r["case_id"]): r for r in records}

    tol_keys = [_tol_key(t) for t in TOLERANCES]
    rows = []
    for case_id in sorted(cases):
        case = cases[case_id]
        for system in case["comparator_eligibility"]:
            record = by_key.get((system, case_id))
            base_row = {
                "case_id": case_id, "system": system,
                "pair_type": case["pair_type"],
                "condition": case["condition"],
                "source_slot": case["source_slot"],
                "take": case["take"],
                "reliability_only": bool(case.get("reliability_only")),
                "decision": (record or {}).get("decision"),
                "predicted_offset_s": (record or {}).get("predicted_offset_s"),
                "gt_offset_s": case["gt_offset_s"],
            }
            for tol in TOLERANCES:
                key = _tol_key(tol)
                scored = score_pair(case, record, tol)
                base_row[f"outcome_at_{key}"] = scored["outcome"]
                base_row[f"abs_error_s_at_{key}"] = scored["abs_error_s"]
            rows.append(base_row)

    def _subset(pair_type: str | None, primary: bool | None = None):
        out = []
        for row in rows:
            if pair_type is not None and row["pair_type"] != pair_type:
                continue
            if primary is not None and row["reliability_only"] != (not primary):
                continue
            out.append(row)
        return out

    primary_pos = _subset("POSITIVE", primary=True)
    wrong = _subset("WRONG_REFERENCE")
    repeats = _subset("POSITIVE", primary=False)

    def _counts(subset: list, outcome_key: str) -> dict:
        per_system = {}
        for system in SYSTEM_IDS:
            counts = {}
            for row in subset:
                if row["system"] != system:
                    continue
                o = row[outcome_key]
                counts[o] = counts.get(o, 0) + 1
            per_system[system] = {k: counts.get(k, 0) for k in sorted(counts)}
        return per_system

    outcomes = {tol: {
        "primary_positives": _counts(primary_pos, f"outcome_at_{tol}"),
        "wrong_reference": _counts(wrong, f"outcome_at_{tol}"),
    } for tol in tol_keys}

    def _accepted_errors(subset: list, system: str, tol: str) -> list:
        vals = []
        for row in subset:
            if (row["system"] == system
                    and row[f"outcome_at_{tol}"] == OUTCOME_CORRECT_ACCEPT):
                vals.append(row[f"abs_error_s_at_{tol}"])
        return vals

    def _produced_errors(subset: list, system: str) -> list:
        return [abs(row["predicted_offset_s"] - row["gt_offset_s"])
                for row in subset
                if row["system"] == system
                and row["decision"] == "ACCEPT"
                and row["predicted_offset_s"] is not None
                and row["gt_offset_s"] is not None]

    error_stats = {}
    for system in SYSTEM_IDS:
        error_stats[system] = {
            "accepted_positive_abs_error_s": {
                tol: _median_iqr_max(_accepted_errors(primary_pos, system, tol))
                for tol in tol_keys},
            "produced_acceptance_abs_error_s_100ms":
                _median_iqr_max(_produced_errors(primary_pos, system)),
        }

    # selective-risk metrics (section 13)
    selective = {}
    for system in SELECTIVE_SYSTEMS:
        pos = {tol: _counts(primary_pos, f"outcome_at_{tol}")[system]
               for tol in tol_keys}
        neg = {tol: _counts(wrong, f"outcome_at_{tol}")[system]
               for tol in tol_keys}
        ca = pos["0.1"].get(OUTCOME_CORRECT_ACCEPT, 0)
        n_pos = sum(pos["0.1"].values())
        selective[system] = {
            "positive_denominator": n_pos,
            "positive_coverage_correct_accepts_100ms": ca,
            "positive_coverage_fraction_100ms": (ca / n_pos) if n_pos else None,
            "positive_wrong_accepts_100ms": pos["0.1"].get(OUTCOME_WRONG_ACCEPT, 0),
            "positive_abstain_no_match_100ms":
                pos["0.1"].get(OUTCOME_SAFE_ABSTAIN, 0),
            "positive_runner_errors_100ms":
                pos["0.1"].get(OUTCOME_RUNNER_ERROR, 0),
            "wrong_ref_false_accepts_100ms":
                neg["0.1"].get(OUTCOME_WRONG_ACCEPT, 0),
            "wrong_ref_safe_refusals_100ms":
                neg["0.1"].get(OUTCOME_SAFE_ABSTAIN, 0),
            "wrong_ref_denominator": sum(neg["0.1"].values()),
        }

    # always-output metrics (section 13)
    always = {}
    for system in ALWAYS_OUTPUT_SYSTEMS:
        pos100 = _counts(primary_pos, "outcome_at_0.1")[system]
        neg100 = _counts(wrong, "outcome_at_0.1")[system]
        errs = _produced_errors(primary_pos, system)
        wrong_errs = [abs(row["predicted_offset_s"])
                      for row in wrong
                      if row["system"] == system
                      and row["decision"] == "ACCEPT"
                      and row["predicted_offset_s"] is not None]
        always[system] = {
            "positive_correct_100ms": pos100.get(OUTCOME_CORRECT_ACCEPT, 0),
            "positive_wrong_100ms": pos100.get(OUTCOME_WRONG_ACCEPT, 0),
            "positive_denominator": sum(pos100.values()),
            "wrong_reference_outputs_100ms": sum(neg100.values()),
            "wrong_reference_all_accept_semantics":
                "ALWAYS_OUTPUT: every wrong-reference output is a "
                "WRONG_ACCEPT under frozen scoring (native baseline "
                "semantics, not an implementation bug)",
            "wrong_reference_catastrophic_wrong_accepts":
                neg100.get(OUTCOME_WRONG_ACCEPT, 0),
            "positive_error_abs_s": _median_iqr_max(errs),
            "wrong_reference_output_magnitude_abs_s":
                _median_iqr_max(wrong_errs),
        }

    # condition-level (section 14)
    conditions = sorted({row["condition"] for row in primary_pos})
    condition_table = {cond: _counts(
        [r for r in primary_pos if r["condition"] == cond], "outcome_at_0.1")
        for cond in conditions}

    # source-level aggregation (section 15) — slot is the independence unit
    slots = sorted({row["source_slot"] for row in primary_pos})
    source_table = {}
    for slot in slots:
        source_table[slot] = {
            "primary_positives": _counts(
                [r for r in primary_pos if r["source_slot"] == slot],
                "outcome_at_0.1"),
            "wrong_reference": _counts(
                [r for r in wrong if r["source_slot"] == slot],
                "outcome_at_0.1"),
        }

    # song-level bootstrap (section 15/18): resample source slots
    bootstrap = _song_bootstrap(primary_pos, wrong)

    # exact discordant counts (section 18): RA vs each baseline
    discordant = _discordant_counts(primary_pos, wrong,
                                    rhythmalign_runner.SYSTEM_ID)

    # strict repeats (section 16)
    strict_repeats = _strict_repeat_report(repeats, cases, by_key)

    body = {
        "status": "FINAL_BENCHMARK_SCORED",
        "created_utc": _utc_now(),
        **_final_labels(),
        "authority": {
            "manifest_freeze_sha256": frozen["freeze_hash"],
            "raw_assembly_sha256": _sha256_file(RAW_PATH),
            "kdenlive_results_sha256":
                _load_json(KDENLIVE_RESULTS_PATH)["kdenlive_results_sha256"]
                if KDENLIVE_RESULTS_PATH.exists() else None,
            "qc_freeze_sha256": _load_json(QC_PATH)["qc_freeze_sha256"],
            "scoring_module": "experiments/applied_system/scoring.py "
                              "(frozen contract, unchanged)",
        },
        "denominators": {
            "primary_positives": len(primary_pos) // len(SYSTEM_IDS),
            "wrong_reference": len(wrong) // len(SYSTEM_IDS),
            "strict_repeats": len(repeats) // len(SYSTEM_IDS),
        },
        "outcomes_by_tolerance": outcomes,
        "error_statistics": error_stats,
        "selective_risk_metrics": selective,
        "always_output_metrics": always,
        "condition_level_100ms": condition_table,
        "source_level_100ms": source_table,
        "song_level_bootstrap": bootstrap,
        "discordant_counts_vs_rhythmalign": discordant,
        "strict_repeats": strict_repeats,
        "per_case_rows": rows,
    }
    _save_json(SCORES_PATH, {"benchmark_results_sha256": None, "body": body})
    wrapped = _load_json(SCORES_PATH)
    wrapped["benchmark_results_sha256"] = hashlib.sha256(
        _canonical_bytes(wrapped["body"])).hexdigest()
    _save_json(SCORES_PATH, wrapped)
    write_hash_sidecar(SCORES_PATH)
    _write_scores_csv(rows)
    return wrapped


def _write_scores_csv(rows: list) -> None:
    cols = ["case_id", "system", "pair_type", "condition", "source_slot",
            "take", "reliability_only", "decision", "predicted_offset_s",
            "gt_offset_s", "outcome_at_0.05", "outcome_at_0.1",
            "outcome_at_0.15", "abs_error_s_at_0.1"]
    with open(SCORES_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for row in sorted(rows, key=lambda r: (r["case_id"], r["system"])):
            writer.writerow([row.get(c) for c in cols])
    write_hash_sidecar(SCORES_CSV_PATH)


def _song_bootstrap(primary_pos: list, wrong: list) -> dict:
    """Song-level bootstrap: the source slot is the independence unit.
    Takes of one song are never treated as independent observations."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    slots = sorted({row["source_slot"] for row in primary_pos})
    pos_by_slot = {s: [r for r in primary_pos if r["source_slot"] == s]
                   for s in slots}
    neg_by_slot = {s: [r for r in wrong if r["source_slot"] == s]
                   for s in slots}
    systems = SYSTEM_IDS
    out = {"unit": "source_slot", "replicates": BOOTSTRAP_REPLICATES,
           "seed": BOOTSTRAP_SEED, "note": "descriptive aids only; wide "
           "intervals at 10 source identities; never evidence of "
           "equivalence or difference", "systems": {}}
    stats = {sys_: {"cov": [], "wa_pos": [], "fa_neg": [], "refuse_neg": []}
             for sys_ in systems}
    for _ in range(BOOTSTRAP_REPLICATES):
        pick = rng.choice(len(slots), size=len(slots), replace=True)
        for sys_ in systems:
            cov_n = cov_k = wa = fa = refuse = 0
            for idx in pick:
                s = slots[idx]
                for row in pos_by_slot[s]:
                    if row["system"] != sys_:
                        continue
                    cov_n += 1
                    cov_k += row["outcome_at_0.1"] == OUTCOME_CORRECT_ACCEPT
                    wa += row["outcome_at_0.1"] == OUTCOME_WRONG_ACCEPT
                for row in neg_by_slot[s]:
                    if row["system"] != sys_:
                        continue
                    o = row["outcome_at_0.1"]
                    fa += o == OUTCOME_WRONG_ACCEPT
                    refuse += o == OUTCOME_SAFE_ABSTAIN
            stats[sys_]["cov"].append(cov_k / cov_n if cov_n else np.nan)
            stats[sys_]["wa_pos"].append(wa)
            stats[sys_]["fa_neg"].append(fa)
            stats[sys_]["refuse_neg"].append(refuse)
    for sys_ in systems:
        cov = np.asarray(stats[sys_]["cov"], dtype=float)
        out["systems"][sys_] = {
            "positive_coverage_100ms_point": None,
            "positive_coverage_100ms_ci95": [float(np.nanpercentile(cov, 2.5)),
                                             float(np.nanpercentile(cov, 97.5))],
            "wrong_accepts_positives_ci95": [
                float(np.percentile(stats[sys_]["wa_pos"], 2.5)),
                float(np.percentile(stats[sys_]["wa_pos"], 97.5))],
            "false_accepts_wrong_ref_ci95": [
                float(np.percentile(stats[sys_]["fa_neg"], 2.5)),
                float(np.percentile(stats[sys_]["fa_neg"], 97.5))],
            "safe_refusals_wrong_ref_ci95": [
                float(np.percentile(stats[sys_]["refuse_neg"], 2.5)),
                float(np.percentile(stats[sys_]["refuse_neg"], 97.5))],
        }
    for sys_ in systems:
        subset = [r for r in primary_pos if r["system"] == sys_]
        k = sum(r["outcome_at_0.1"] == OUTCOME_CORRECT_ACCEPT
                for r in subset)
        out["systems"][sys_]["positive_coverage_100ms_point"] = k / len(subset)
    return out


def _discordant_counts(primary_pos: list, wrong: list, ra_id: str) -> dict:
    """Exact paired counts against each baseline, positives and negatives."""
    out = {}
    for system in SYSTEM_IDS:
        if system == ra_id:
            continue
        pos_pairs = {}
        neg_pairs = {}
        for row in primary_pos:
            pos_pairs.setdefault(row["case_id"], {})[row["system"]] = row
        for row in wrong:
            neg_pairs.setdefault(row["case_id"], {})[row["system"]] = row
        p_both = p_ra_only = p_base_only = p_neither = 0
        for case_id in sorted(pos_pairs):
            ra_ok = (pos_pairs[case_id][ra_id]["outcome_at_0.1"]
                     == OUTCOME_CORRECT_ACCEPT)
            base_ok = (pos_pairs[case_id][system]["outcome_at_0.1"]
                       == OUTCOME_CORRECT_ACCEPT)
            if ra_ok and base_ok:
                p_both += 1
            elif ra_ok:
                p_ra_only += 1
            elif base_ok:
                p_base_only += 1
            else:
                p_neither += 1
        n_both = n_ra_only = n_base_only = n_neither = 0
        for case_id in sorted(neg_pairs):
            ra_wa = (neg_pairs[case_id][ra_id]["outcome_at_0.1"]
                     == OUTCOME_WRONG_ACCEPT)
            base_wa = (neg_pairs[case_id][system]["outcome_at_0.1"]
                       == OUTCOME_WRONG_ACCEPT)
            if ra_wa and base_wa:
                n_both += 1
            elif ra_wa:
                n_ra_only += 1
            elif base_wa:
                n_base_only += 1
            else:
                n_neither += 1
        out[system] = {
            "positives_100ms": {
                "both_correct_accept": p_both,
                "rhythmalign_only": p_ra_only,
                f"{system}_only": p_base_only,
                "neither": p_neither,
            },
            "wrong_reference_100ms": {
                "both_wrong_accept": n_both,
                "rhythmalign_wrong_accept_only": n_ra_only,
                f"{system}_wrong_accept_only": n_base_only,
                "both_safe": n_neither,
            },
        }
    return out


def _strict_repeat_report(repeat_rows: list, cases: dict, by_key: dict) -> dict:
    pairs = [("repeat01", "final01"), ("repeat02", "final02")]
    out = {"note": ("reliability evidence only; never enters primary "
                    "counts; each repeat compared only with its paired "
                    "ordinary case"),
           "comparisons": []}
    for repeat, original in pairs:
        for system in SYSTEM_IDS:
            rep = by_key.get((system, f"{repeat}__positive"))
            orig = by_key.get((system, f"{original}__positive"))
            rep_gt = cases[f"{repeat}__positive"]["gt_offset_s"]
            orig_gt = cases[f"{original}__positive"]["gt_offset_s"]
            entry = {"repeat": repeat, "original": original,
                     "system": system,
                     "repeat_decision": (rep or {}).get("decision"),
                     "original_decision": (orig or {}).get("decision"),
                     "repeat_gt_offset_s": rep_gt,
                     "original_gt_offset_s": orig_gt,
                     "gt_offset_difference_s": rep_gt - orig_gt,
                     "outcome_agreement": (
                         (rep or {}).get("decision")
                         == (orig or {}).get("decision"))}
            if (rep and orig
                    and rep.get("decision") == "ACCEPT"
                    and orig.get("decision") == "ACCEPT"
                    and rep.get("predicted_offset_s") is not None
                    and orig.get("predicted_offset_s") is not None):
                entry["offset_difference_s"] = (
                    rep["predicted_offset_s"] - orig["predicted_offset_s"])
                # signed error change relative to the two takes' true
                # offsets: how much the system's placement error moved
                # between the ordinary take and its strict repeat
                entry["signed_error_difference_s"] = (
                    (rep["predicted_offset_s"] - rep_gt)
                    - (orig["predicted_offset_s"] - orig_gt))
            out["comparisons"].append(entry)
    return out


# ---------------------------------------------------------------------------
# optional plots (execution task section 23) — tables remain the authority
# ---------------------------------------------------------------------------


FIGURES_DIR = RESULTS_DIR / "figures"


def build_plots() -> list:
    """Three aggregate figures. Raw counts annotated; no axis truncation;
    the Kdenlive stratum is never mixed into automated-system axes (its
    placement errors span minutes, not milliseconds)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frozen = _load_json(SCORES_PATH)["body"]
    outcomes = frozen["outcomes_by_tolerance"]["0.1"]
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    written = []

    label = {"rhythmalign_v1_2_0": "RhythmAlign v1.2.0",
             "gcc_phat_argmax_v1": "GCC-PHAT argmax",
             "ncc_argmax_v1": "NCC argmax",
             "panako_fingerprint": "Panako OLAF"}
    order = ["rhythmalign_v1_2_0", "ncc_argmax_v1", "gcc_phat_argmax_v1",
             "panako_fingerprint"]

    # 1 — outcome composition at 100 ms
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    pos_cats = [("CORRECT_ACCEPT", "#2a7f2a"), ("WRONG_ACCEPT", "#b2182b"),
                ("SAFE_ABSTAIN", "#6baed6"), ("RUNNER_ERROR", "#999999")]
    neg_cats = [("WRONG_ACCEPT", "#b2182b"), ("SAFE_ABSTAIN", "#6baed6"),
                ("RUNNER_ERROR", "#999999")]
    for ax, cats, table, title in (
            (axes[0], pos_cats, outcomes["primary_positives"],
             "Primary positives (n=24)"),
            (axes[1], neg_cats, outcomes["wrong_reference"],
             "Wrong-reference pairs (n=24)")):
        left = [0] * len(order)
        y = list(range(len(order)))[::-1]
        for outcome, color in cats:
            vals = [table[s].get(outcome, 0) for s in order]
            ax.barh(y, vals, left=left, color=color,
                    label=outcome.replace("_", " ").title())
            for yi, v, l in zip(y, vals, left):
                if v:
                    ax.text(l + v / 2, yi, str(v), ha="center", va="center",
                            color="white", fontsize=9)
            left = [a + b for a, b in zip(left, vals)]
        ax.set_title(title, fontsize=10)
        ax.set_xlim(0, 24)
        ax.set_xticks([0, 6, 12, 18, 24])
    axes[0].set_yticks(y, [label[s] for s in order], fontsize=9)
    axes[1].legend(fontsize=7, loc="lower right")
    fig.suptitle("Frozen final benchmark outcomes at the 100 ms tolerance",
                 fontsize=11)
    fig.tight_layout()
    path = FIGURES_DIR / "final_outcome_composition.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)

    # 2 — accepted-positive absolute errors (all systems < 25 ms)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for yi, s in enumerate(order[::-1]):
        errs = sorted(
            row["abs_error_s_at_0.1"] for row in frozen["per_case_rows"]
            if row["system"] == s and row["pair_type"] == "POSITIVE"
            and not row["reliability_only"]
            and row["outcome_at_0.1"] == OUTCOME_CORRECT_ACCEPT
            and row["abs_error_s_at_0.1"] is not None)
        ax.scatter(errs, [yi] * len(errs), s=28, alpha=0.75)
        ax.axvline(0.05, color="#888", lw=0.6, linestyle=":")
    ax.axvline(0.05, color="#888", lw=0.6, linestyle=":")
    ax.set_yticks(range(len(order)), [label[order[::-1][i]]
                                      for i in range(len(order))], fontsize=9)
    ax.set_xlabel("Accepted-positive |offset error| (s) — every accepted "
                  "placement of every system lies below 25 ms")
    ax.set_title("Accepted-positive offset errors at 100 ms "
                 "(dots = cases; dashed line = 50 ms)", fontsize=10)
    fig.tight_layout()
    path = FIGURES_DIR / "final_accepted_offset_errors.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)

    # 3 — condition-level correct-accept counts (raw, small denominators)
    conds = sorted(frozen["condition_level_100ms"])
    width = 0.2
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for i, s in enumerate(order):
        vals = [frozen["condition_level_100ms"][c][s]
                .get("CORRECT_ACCEPT", 0) for c in conds]
        ax.bar([j + (i - 1.5) * width for j in range(len(conds))], vals,
               width=width, label=label[s])
    denoms = {"ORDINARY": 10, "LOW_LEVEL": 3, "TAP_DOMINANT": 3,
              "INTERFERENCE": 4, "PARTIAL": 2, "DEVICE_VARIATION": 2}
    ax.set_xticks(range(len(conds)),
                  [f"{c}\nn={denoms[c]}" for c in conds], fontsize=8)
    ax.set_ylabel("CORRECT_ACCEPT count")
    ax.set_title("Correct accepts by condition (small denominators; "
                 "raw counts only)", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = FIGURES_DIR / "final_condition_summary.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)
    return written


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    stages = {
        "kdenlive-freeze": build_kdenlive_owner_run_freeze,
        "kdenlive-score": score_kdenlive,
        "manifest": build_benchmark_manifest,
        "run": run_comparators,
        "score": score_comparators,
        "plots": build_plots,
    }
    if not args or args[0] not in stages:
        print("usage: python -m experiments.applied_system.final_benchmark "
              + "|".join(stages))
        return 2
    result = stages[args[0]]()
    if isinstance(result, dict) and "freeze_hash" in result:
        print("freeze ok:", result["freeze_hash"][:16])
    elif isinstance(result, dict) and "owner_run_freeze_sha256" in result:
        print("owner-run freeze ok:", result["owner_run_freeze_sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
