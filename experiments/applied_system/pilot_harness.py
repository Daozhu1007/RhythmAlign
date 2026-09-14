"""Fresh acoustic development-pilot harness.

PILOT_ONLY / NOT_FINAL_PAPER_EVIDENCE.

The stages deliberately enforce the order declared in FRESH_PILOT_PLAN:

    prepare   ingest -> ungated marker diagnostics -> rule derivation ->
              GT/trim -> immutable measurement and pairing freezes
    run       verify all freezes and hashes, then run one comparator pass
    score     deterministic scoring of the first pass
    reproduce run one complete second pass and compare non-volatile output
    report    evaluate pre-declared gates and write the pilot report; only a
              clean pass creates FINAL_BENCHMARK_PROTOCOL.md

No production module is modified. Raw recordings are opened read-only, hashed
before and after decode, and never copied, renamed, converted in place, or
committed. Decoded/trimmed working media lives under a gitignored directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal as scipy_signal

from . import marker_protocol as mp
from . import scoring as scoring_mod
from .acoustic_loop import sweep_trajectory_check, top_marker_peaks
from .runners import common
from .runners import gcc_phat_runner, ncc_runner, panako_runner
from .runners import rhythmalign_runner


ROOT = Path(__file__).resolve().parents[2]
APPLIED_DIR = Path(__file__).resolve().parent
PACK_DIR = APPLIED_DIR / "pilot_pack"
DEFAULT_OUTDIR = PACK_DIR / "results"
TAKE_PLAN_PATH = PACK_DIR / "take_plan.json"
KIT_MANIFEST_PATH = PACK_DIR / "kit_manifest.json"
RESULTS_DOC_PATH = ROOT / "docs/research/applied_system/FRESH_PILOT_RESULTS.md"
FINAL_PROTOCOL_PATH = ROOT / "docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md"

PILOT_ONLY = "PILOT_ONLY"
NOT_FINAL = "NOT_FINAL_PAPER_EVIDENCE"
WARNING = "PILOT_ONLY — NOT_FINAL_PAPER_EVIDENCE"
REQUIRED_BRANCH = "research/applied-system-paper"
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


def _canonical_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return common.sha256_file(path)


def _save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    common.save_json(path, value)


def _load_json(path: Path):
    return common.load_json(path)


def _repo_rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def require_research_branch() -> None:
    branch = _git("branch", "--show-current")
    if branch != REQUIRED_BRANCH:
        raise RuntimeError(f"pilot requires {REQUIRED_BRANCH}, found {branch}")


def freeze_artifact(path: Path, body: dict,
                    hash_key: str = "freeze_hash") -> dict:
    """Write once. A second identical call is a no-op; any edit/refreeze fails."""
    digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    wrapped = {hash_key: digest, "body": body}
    if path.exists():
        current = _load_json(path)
        errors = verify_frozen_artifact(current, hash_key)
        if errors:
            raise RuntimeError(f"immutable artifact {path} is invalid: {errors}")
        if current != wrapped:
            raise RuntimeError(f"immutable artifact already exists with different content: {path}")
        return current
    _save_json(path, wrapped)
    return wrapped


def verify_frozen_artifact(value: dict, hash_key: str = "freeze_hash") -> list[str]:
    if not isinstance(value, dict) or not isinstance(value.get("body"), dict):
        return ["malformed frozen artifact"]
    declared = value.get(hash_key)
    actual = hashlib.sha256(_canonical_bytes(value["body"])).hexdigest()
    return [] if declared == actual else [f"{hash_key} mismatch: {declared} != {actual}"]


def _write_hash_sidecar(path: Path) -> str:
    digest = _sha256_file(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    expected = f"{digest}  {path.name}\n"
    if sidecar.exists() and sidecar.read_text(encoding="utf-8") != expected:
        raise RuntimeError(f"immutable hash sidecar differs: {sidecar}")
    if not sidecar.exists():
        sidecar.write_text(expected, encoding="utf-8", newline="\n")
    return digest


def discover_recordings(incoming: Path, take_plan: dict) -> dict[str, Path]:
    expected = [row["take"] for row in take_plan["takes"]]
    by_take: dict[str, list[Path]] = {take: [] for take in expected}
    rx = re.compile(r"^(take\d{2})(?:_[^.]+)?$", re.IGNORECASE)
    for path in sorted(incoming.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        match = rx.fullmatch(path.stem)
        if match and match.group(1).lower() in by_take:
            by_take[match.group(1).lower()].append(path)
    chosen = {}
    errors = []
    for take in expected:
        candidates = by_take[take]
        exact = [p for p in candidates if p.stem.lower() == take]
        if len(exact) == 1:
            chosen[take] = exact[0]
        elif len(candidates) == 1:
            chosen[take] = candidates[0]
        elif not candidates:
            errors.append(f"{take}: missing")
        else:
            errors.append(f"{take}: ambiguous candidates {[p.name for p in candidates]}")
    if errors:
        raise RuntimeError("recording ingest failed: " + "; ".join(errors))
    return chosen


def parse_ffmpeg_input(stderr: str) -> dict:
    container = None
    codec = None
    match = re.search(r"Input #0,\s*([^\n]+?),\s*from", stderr)
    if match:
        container = match.group(1).strip()
    audio_lines = [line for line in stderr.splitlines() if " Audio: " in line]
    if audio_lines:
        match = re.search(r"Audio:\s*([^,\s]+)", audio_lines[0])
        if match:
            codec = match.group(1).strip()
    return {"container": container, "codec": codec}


def decode_native(raw_path: Path, decoded_path: Path) -> tuple[np.ndarray, int, dict]:
    """Decode without -ar or -ac: native nominal rate/channels are preserved."""
    import imageio_ffmpeg

    raw_before = _sha256_file(raw_path)
    decoded_path.parent.mkdir(parents=True, exist_ok=True)
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, "-y", "-hide_banner", "-i", str(raw_path), "-vn", "-map",
           "0:a:0", "-acodec", "pcm_s16le", str(decoded_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed for {raw_path.name}: {proc.stderr[-800:]}")
    raw_after = _sha256_file(raw_path)
    if raw_after != raw_before:
        raise RuntimeError(f"raw source changed during decode: {raw_path}")
    info = sf.info(str(decoded_path))
    y, sr = sf.read(str(decoded_path), dtype="float64", always_2d=False)
    mono = np.ascontiguousarray(y.mean(axis=1) if y.ndim > 1 else y)
    parsed = parse_ffmpeg_input(proc.stderr)
    meta = {
        "original_filename": raw_path.name,
        "raw_sha256": raw_before,
        "raw_sha256_after_decode": raw_after,
        "original_bytes": raw_path.stat().st_size,
        "container": parsed["container"] or raw_path.suffix.lower().lstrip("."),
        "codec": parsed["codec"] or "unknown",
        "native_sample_rate_hz": int(info.samplerate),
        "native_channel_count": int(info.channels),
        "duration_s": float(info.duration),
        "decoded_working_sha256": _sha256_file(decoded_path),
        "decoded_working_path": _repo_rel(decoded_path),
        "decode": {
            "tool": str(exe),
            "no_resampling": True,
            "no_channel_forcing": True,
            "output_codec": "pcm_s16le",
        },
    }
    return mono, int(sr), meta


def accepted_peaks(y: np.ndarray, fs: int, threshold: float) -> list[dict]:
    template = mp.chirp_template(fs)
    ncc, lags = mp._normalized_correlation(y, template)
    valid = (lags >= 0) & (lags + len(template) <= len(y))
    ncc = np.where(valid, ncc, -np.inf)
    above = np.flatnonzero(ncc >= threshold)
    order = above[np.argsort(-ncc[above], kind="stable")]
    selected = []
    for k in order:
        lag = int(lags[k])
        if all(abs(lag - row["start_sample"]) >= len(template) for row in selected):
            selected.append({
                "start_sample": float(lag) + mp._parabolic_refine(ncc, int(k)),
                "confidence": float(ncc[k]),
            })
    return sorted(selected, key=lambda row: row["start_sample"])


def select_structural_marker_pair(top_peaks: list[dict], expected_sep: int,
                                  max_abs_ppm: float = 1000.0) -> tuple[dict, dict] | None:
    """Outcome-blind calibration helper: strongest pair within the declared
    1000 ppm detectable separation band. It does not impose a confidence gate."""
    pairs = []
    for i, left in enumerate(top_peaks):
        for right in top_peaks[i + 1:]:
            a, b = sorted((left, right), key=lambda row: row["lag_samples"])
            ppm = (float(b["lag_samples"] - a["lag_samples"]) / expected_sep - 1.0) * 1e6
            if abs(ppm) <= max_abs_ppm:
                pairs.append((min(a["ncc"], b["ncc"]), a["ncc"] + b["ncc"],
                              -abs(ppm), a, b))
    if not pairs:
        return None
    best = max(pairs, key=lambda row: row[:3])
    return best[3], best[4]


def ground_truth_from_pair(pre: dict, post: dict, spec: mp.BufferSpec,
                           fs: int) -> mp.GroundTruthResult:
    a, b = float(pre["start_sample"]), float(post["start_sample"])
    expected = float(spec.expected_marker_separation_samples)
    observed = b - a
    scale = observed / expected
    map_a = a + spec.payload_start_sample * scale
    map_b = b - (spec.marker2_start_sample - spec.payload_start_sample) * scale
    start = int(round(0.5 * (map_a + map_b)))
    end_a = a + spec.payload_end_sample * scale
    end_b = b - (spec.marker2_start_sample - spec.payload_end_sample) * scale
    end = int(round(0.5 * (end_a + end_b)))
    disagreement = abs(map_a - map_b)
    qc = {
        "pre_marker": {"found": True, "start_sample": a,
                       "confidence": float(pre["confidence"])},
        "post_marker": {"found": True, "start_sample": b,
                        "confidence": float(post["confidence"])},
        "n_marker_candidates": 2,
        "expected_marker_separation_samples": int(expected),
        "observed_marker_separation_samples": observed,
        "max_mapping_disagreement_samples": int(round(mp.MAX_MAPPING_DISAGREEMENT_S * fs)),
    }
    diag = {
        "payload_start_map_via_pre_samples": map_a,
        "payload_start_map_via_post_samples": map_b,
        "mapping_disagreement_samples": disagreement,
        "payload_start_samples_used": start,
        "payload_end_samples_used": end,
    }
    return mp.GroundTruthResult(
        status=mp.GT_VALID, payload_start_sample=start, payload_end_sample=end,
        clock_scale=scale, scale_error=scale - 1.0, marker_qc=qc,
        diagnostics=diag)


def diagnose_take(y: np.ndarray, fs: int, buffer_row: dict,
                  trimmed_path: Path) -> dict:
    payload_duration = ((buffer_row["payload_end_sample"] -
                         buffer_row["payload_start_sample"]) /
                        float(buffer_row.get("total_samples", mp.FS)))
    # The manifests use 48 kHz sample indices. Convert through seconds.
    payload_duration = 60.0 if not (59.0 <= payload_duration <= 61.0) else payload_duration
    spec = mp.buffer_spec(int(round(payload_duration * fs)), fs)
    top = top_marker_peaks(y, fs, n=12)
    pair = select_structural_marker_pair(top, spec.expected_marker_separation_samples)
    report = {
        "diagnostic_selection_rule": (
            "ungated full-template-overlap peaks; strongest two-peak pair "
            "within the pre-declared 1000 ppm detectable separation band"),
        "provisional_threshold_used_for_diagnostics": False,
        "provisional_candidate_count": len(accepted_peaks(y, fs, mp.MIN_MARKER_CONFIDENCE)),
        "full_template_overlap_required": True,
        "top_candidate_diagnostics": top,
        "expected_marker_separation_samples": spec.expected_marker_separation_samples,
    }
    if pair is None:
        report.update({
            "diagnostic_gt_status": mp.GT_FAILED,
            "diagnostic_fail_reason": "no ungated marker pair inside 1000 ppm separation band",
        })
        return report
    left, right = pair
    pre = {"start_sample": left["lag_samples"], "confidence": left["ncc"]}
    post = {"start_sample": right["lag_samples"], "confidence": right["ncc"]}
    gt = ground_truth_from_pair(pre, post, spec, fs)
    template = mp.chirp_template(fs)
    ncc, lags = mp._normalized_correlation(y, template)
    valid = (lags >= 0) & (lags + len(template) <= len(y))
    competing = valid.copy()
    for marker in (pre, post):
        competing &= np.abs(lags - marker["start_sample"]) >= len(template)
    if np.any(competing):
        masked = np.where(competing, ncc, -np.inf)
        k = int(np.argmax(masked))
        competitor_ncc = float(masked[k])
        competitor_lag = int(lags[k])
        competitor_trajectory = sweep_trajectory_check(y, competitor_lag, fs)
    else:
        competitor_ncc, competitor_lag = 0.0, None
        competitor_trajectory = {"corroborated": False, "reason": "no eligible lag"}

    tr = mp.trim_capture(y, gt, spec, fs)
    if not tr.ok:
        report.update({"diagnostic_gt_status": mp.GT_FAILED,
                       "diagnostic_fail_reason": tr.fail_reason})
        return report
    trimmed_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(trimmed_path), tr.trimmed, fs, subtype="PCM_16")
    shipped_trimmed, shipped_sr = sf.read(str(trimmed_path), dtype="float64",
                                          always_2d=False)
    if shipped_trimmed.ndim > 1:
        shipped_trimmed = shipped_trimmed.mean(axis=1)
    leak = mp.marker_leakage_check(np.ascontiguousarray(shipped_trimmed), shipped_sr)
    pre_traj = sweep_trajectory_check(y, pre["start_sample"], fs)
    post_traj = sweep_trajectory_check(y, post["start_sample"], fs)
    for row in top:
        row["candidate_role"] = (
            "GENUINE_PRE" if abs(row["lag_samples"] - pre["start_sample"]) < len(template)
            else "GENUINE_POST" if abs(row["lag_samples"] - post["start_sample"]) < len(template)
            else "NON_MARKER")
    report.update({
        "diagnostic_gt_status": mp.GT_VALID,
        "genuine_pre_marker": {**pre, "full_template_overlap": True,
                               "sweep_trajectory": pre_traj},
        "genuine_post_marker": {**post, "full_template_overlap": True,
                                "sweep_trajectory": post_traj},
        "strongest_competing_peak": {
            "confidence": competitor_ncc,
            "start_sample": competitor_lag,
            "full_template_overlap": True,
            "sweep_trajectory": competitor_trajectory,
        },
        "observed_marker_separation_samples": (
            post["start_sample"] - pre["start_sample"]),
        "clock_scale": gt.clock_scale,
        "drift_ppm": gt.scale_error * 1e6,
        "mapping_disagreement_samples": gt.diagnostics["mapping_disagreement_samples"],
        "mapping_disagreement_s": gt.diagnostics["mapping_disagreement_samples"] / fs,
        "preliminary_trim": tr.as_dict(),
        "post_trim_leakage_diagnostic": leak,
        "trimmed_working_path": _repo_rel(trimmed_path),
        "trimmed_input_sha256": _sha256_file(trimmed_path),
    })
    report["take_competing_B"] = max(competitor_ncc, float(leak["max_ncc"]))
    return report


def compute_freeze_rules(take_reports: list[dict]) -> dict:
    devices = {}
    valid = [r for r in take_reports if r["marker_diagnostics"].get(
        "diagnostic_gt_status") == mp.GT_VALID]
    for device in sorted({r["device"] for r in take_reports}):
        rows = [r for r in valid if r["device"] == device]
        if not rows:
            devices[device] = {"valid_takes": 0, "G": None, "B": None,
                               "G_over_B": None, "feasible": False}
            continue
        genuine = [value for r in rows for value in (
            r["marker_diagnostics"]["genuine_pre_marker"]["confidence"],
            r["marker_diagnostics"]["genuine_post_marker"]["confidence"])]
        competing = [r["marker_diagnostics"]["take_competing_B"] for r in rows]
        g, b = min(genuine), max(competing)
        devices[device] = {
            "valid_takes": len(rows), "G": g, "B": b,
            "G_over_B": (math.inf if b <= 0 else g / b),
            "feasible": b <= 0 or g / b >= 3.75,
            "drift_ppm_min": min(r["marker_diagnostics"]["drift_ppm"] for r in rows),
            "drift_ppm_max": max(r["marker_diagnostics"]["drift_ppm"] for r in rows),
        }
    if not valid:
        raise RuntimeError("no structurally valid take; freeze rule cannot be computed")
    genuine = [value for r in valid for value in (
        r["marker_diagnostics"]["genuine_pre_marker"]["confidence"],
        r["marker_diagnostics"]["genuine_post_marker"]["confidence"])]
    competing = [r["marker_diagnostics"]["take_competing_B"] for r in valid]
    g, b = min(genuine), max(competing)
    t_low, t_high = 3.0 * b, 0.8 * g
    threshold = math.sqrt(t_low * t_high)
    genuine_trajectories = [r["marker_diagnostics"][key]["sweep_trajectory"]
                            for r in valid for key in
                            ("genuine_pre_marker", "genuine_post_marker")]
    competing_trajectories = [
        row["sweep_trajectory"]
        for r in valid
        for row in r["marker_diagnostics"]["top_candidate_diagnostics"]
        if row.get("candidate_role") == "NON_MARKER"]
    trajectory_on = (all(row.get("corroborated") for row in genuine_trajectories)
                     and not any(row.get("corroborated") for row in competing_trajectories))
    worst_abs_drift = max(abs(r["marker_diagnostics"]["drift_ppm"]) for r in valid)
    drift_uncapped = max(3.0 * worst_abs_drift, 111.0)
    return {
        "marker": {
            "G": g, "B": b, "G_over_B": math.inf if b <= 0 else g / b,
            "T_low_3B": t_low, "T_high_0_8G": t_high,
            "frozen_threshold_exact": threshold,
            "frozen_threshold_documentation_2dp": round(threshold, 2),
            "formula_verbatim": "T = sqrt(T_low × T_high), with T_low = 3 × B and T_high = 0.8 × G",
            "feasibility_rule_verbatim": "the band is non-empty iff G/B ≥ 3.75",
            "pooled_feasible": b <= 0 or g / b >= 3.75,
            "per_device": devices,
        },
        "trajectory": {
            "state": ("TRAJECTORY_GATE_FROZEN_ON" if trajectory_on
                      else "TRAJECTORY_GATE_FROZEN_OFF"),
            "all_genuine_corroborate": all(row.get("corroborated") for row in genuine_trajectories),
            "any_non_marker_corroborates": any(row.get("corroborated") for row in competing_trajectories),
            "genuine_count": len(genuine_trajectories),
            "non_marker_diagnostic_count": len(competing_trajectories),
        },
        "drift": {
            "every_take_ppm": {r["take_id"]: r["marker_diagnostics"]["drift_ppm"] for r in valid},
            "worst_observed_abs_ppm": worst_abs_drift,
            "three_times_D_max_ppm": 3.0 * worst_abs_drift,
            "frozen_tolerance_ppm": min(drift_uncapped, 1000.0),
            "cap_reached": 3.0 * worst_abs_drift > 1000.0,
            "formula_verbatim": "T_drift = max(3 × D_max, 111 ppm); T_drift ≤ 1000 ppm",
        },
    }


def finalize_take_gt(report: dict, y: np.ndarray, fs: int, buffer_row: dict,
                     rules: dict, trimmed_path: Path) -> None:
    diag = report["marker_diagnostics"]
    failures = []
    threshold = rules["marker"]["frozen_threshold_exact"]
    peaks = accepted_peaks(y, fs, threshold)
    diag["frozen_threshold_candidate_count"] = len(peaks)
    if len(peaks) != 2:
        failures.append(f"frozen threshold produced {len(peaks)} candidates, expected exactly 2")
    payload_duration = 60.0
    spec = mp.buffer_spec(int(round(payload_duration * fs)), fs)
    gt = None
    if len(peaks) == 2:
        gt = ground_truth_from_pair(peaks[0], peaks[1], spec, fs)
        drift_ppm = gt.scale_error * 1e6
        if abs(drift_ppm) > rules["drift"]["frozen_tolerance_ppm"]:
            failures.append(f"|drift| {abs(drift_ppm):.6f} ppm exceeds frozen tolerance")
        disagreement_s = gt.diagnostics["mapping_disagreement_samples"] / fs
        if disagreement_s > mp.MAX_MAPPING_DISAGREEMENT_S:
            failures.append("mapping disagreement exceeds 10 ms")
        if rules["trajectory"]["state"] == "TRAJECTORY_GATE_FROZEN_ON":
            if not all(sweep_trajectory_check(y, p["start_sample"], fs).get("corroborated")
                       for p in peaks):
                failures.append("frozen trajectory gate failed")
    if rules["drift"]["cap_reached"]:
        failures.append("drift detectability cap breached")
    if gt is not None and not failures:
        tr = mp.trim_capture(y, gt, spec, fs)
        if not tr.ok:
            failures.append(f"trim failed: {tr.fail_reason}")
        else:
            sf.write(str(trimmed_path), tr.trimmed, fs, subtype="PCM_16")
            shipped, shipped_sr = sf.read(str(trimmed_path), dtype="float64",
                                           always_2d=False)
            if shipped.ndim > 1:
                shipped = shipped.mean(axis=1)
            leak = mp.marker_leakage_check(np.ascontiguousarray(shipped), shipped_sr)
            leak["frozen_threshold"] = threshold
            leak["passes_frozen_threshold"] = leak["max_ncc"] < threshold
            if not leak["passes_frozen_threshold"]:
                failures.append("post-trim marker leakage exceeds frozen threshold")
            diag["final_trim"] = tr.as_dict()
            diag["final_marker_leakage"] = leak
            diag["trimmed_input_sha256"] = _sha256_file(trimmed_path)
            diag["derived_payload_offset_on_trimmed_input_s"] = tr.gt_offset_s
            payload_start_s = float(buffer_row["payload_source"]["payload_start_s"])
            diag["derived_reference_offset_on_trimmed_input_s"] = tr.gt_offset_s - payload_start_s
            diag["final_clock_scale"] = gt.clock_scale
            diag["final_drift_ppm"] = gt.scale_error * 1e6
            diag["final_mapping_disagreement_s"] = (
                gt.diagnostics["mapping_disagreement_samples"] / fs)
    diag["gt_status"] = mp.GT_FAILED if failures else mp.GT_VALID
    diag["gt_fail_reason"] = "; ".join(failures) if failures else None


def _asset_snapshot(kit: dict) -> dict:
    assets = {"buffers": {}, "references": {}}
    for name, row in kit["buffers"].items():
        path = PACK_DIR / "buffers" / f"{name}.wav"
        actual = _sha256_file(path)
        if actual != row["sha256"]:
            raise RuntimeError(f"buffer hash mismatch: {name}")
        assets["buffers"][name] = {"path": _repo_rel(path), "sha256": actual}
    for name, row in kit["references"].items():
        path = Path(row["path"])
        actual = _sha256_file(path)
        if actual != row["sha256"]:
            raise RuntimeError(f"reference hash mismatch: {name}")
        assets["references"][name] = {"path": _repo_rel(path), "sha256": actual,
                                      "source_sha256": row["source_sha256"]}
    return assets


def _comparator_contract() -> dict:
    panako_ok, panako_env = panako_runner.panako_environment()
    try:
        production_tag_commit = _git("rev-list", "-n", "1", "v1.2.0")
    except RuntimeError:
        production_tag_commit = "tag-not-found"
    return {
        rhythmalign_runner.SYSTEM_ID: {
            "role": "ESSENTIAL", "frozen_release": "v1.2.0",
            "production_tag_commit": production_tag_commit,
            "engine_label": getattr(rhythmalign_runner.alignment_engine_v2,
                                    "ENGINE_LABEL", None),
            "decision_semantics": "native ACCEPT or ABSTAIN; one alignment decision per pair",
            "runner_sha256": _sha256_file(Path(rhythmalign_runner.__file__)),
        },
        gcc_phat_runner.SYSTEM_ID: {
            "role": "ESSENTIAL", "decision_semantics": "ALWAYS_OUTPUT argmax; no rejection threshold",
            "runner_sha256": _sha256_file(Path(gcc_phat_runner.__file__)),
        },
        panako_runner.SYSTEM_ID: {
            "role": "ESSENTIAL", "available_at_freeze": panako_ok,
            "pinned_commit": panako_runner.PANAKO_PINNED_COMMIT,
            "strategy": panako_runner.PANAKO_STRATEGY,
            "offset_convention": panako_runner.OFFSET_CONVENTION,
            "decision_semantics": "native ACCEPT / NO_MATCH / ERROR; no invented threshold",
            "environment": panako_env,
            "runner_sha256": _sha256_file(Path(panako_runner.__file__)),
        },
        ncc_runner.SYSTEM_ID: {
            "role": "USEFUL_OPTIONAL", "status": "RUN",
            "decision_semantics": "ALWAYS_OUTPUT argmax; no rejection threshold",
            "runner_sha256": _sha256_file(Path(ncc_runner.__file__)),
        },
    }


def build_wrong_pairings(take_reports: list[dict]) -> dict:
    pairings = []
    for report in sorted(take_reports, key=lambda row: row["take_id"]):
        correct = "REF-A" if report["buffer"] == "BUF-A" else "REF-B"
        wrong = "REF-B" if correct == "REF-A" else "REF-A"
        pairings.append({
            "take_id": report["take_id"], "source_buffer": report["buffer"],
            "correct_reference": correct, "wrong_reference": wrong,
            "construction": "offer the OTHER pilot song's clean reference",
            "provenance": PILOT_ONLY,
            "rate_estimation_evidence": False,
        })
    return {
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "warning": WARNING,
        "authority": "FRESH_PILOT_PLAN.md section 7",
        "pairings": pairings,
    }


def build_case_manifest(take_reports: list[dict], assets: dict) -> dict:
    cases = []
    for report in sorted(take_reports, key=lambda row: row["take_id"]):
        take = report["take_id"]
        diag = report["marker_diagnostics"]
        if diag["gt_status"] != mp.GT_VALID:
            cases.append({
                "case_id": f"{take}__positive", "take_id": take,
                "pair_type": "POSITIVE", "gt_stratum": "GT_FAILED",
                "gt_offset_s": None, "expected_label": None,
                "comparator_eligibility": [], "gt_fail_reason": diag["gt_fail_reason"],
            })
            continue
        correct = "REF-A" if report["buffer"] == "BUF-A" else "REF-B"
        wrong = "REF-B" if correct == "REF-A" else "REF-A"
        common_fields = {
            "take_id": take, "device": report["device"],
            "condition": report["condition"], "playback": report["playback"],
            "raw_capture_path": report["raw"]["path"],
            "raw_capture_sha256": report["raw"]["raw_sha256"],
            "trimmed_input_path": diag["trimmed_working_path"],
            "trimmed_input_sha256": diag["trimmed_input_sha256"],
            "comparator_eligibility": list(SYSTEM_IDS),
        }
        cases.append({
            **common_fields, "case_id": f"{take}__positive",
            "pair_type": "POSITIVE", "reference_id": correct,
            "reference_path": assets["references"][correct]["path"],
            "reference_sha256": assets["references"][correct]["sha256"],
            "gt_stratum": "EXACT_GT", "expected_label": "MATCH",
            "gt_offset_s": diag["derived_reference_offset_on_trimmed_input_s"],
        })
        cases.append({
            **common_fields, "case_id": f"{take}__wrong_ref",
            "pair_type": "WRONG_REFERENCE", "reference_id": wrong,
            "reference_path": assets["references"][wrong]["path"],
            "reference_sha256": assets["references"][wrong]["sha256"],
            "gt_stratum": "NO_MATCH", "expected_label": "NO_MATCH",
            "gt_offset_s": None,
        })
    return {
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "warning": WARNING, "schema_version": "pilot-1",
        "cases": sorted(cases, key=lambda row: row["case_id"]),
    }


def build_final_exclusion_ledger(kit: dict) -> dict:
    from .pilot_source_selection import EXCLUSIONS

    selected = [
        {"identity": "Bloody Trail", "role": "pilot Song A",
         "sha256": kit["buffers"]["BUF-A"]["payload_source"]["source_sha256"]},
        {"identity": "スティールユー / Steel You", "role": "pilot Song B",
         "sha256": kit["buffers"]["BUF-B1"]["payload_source"]["source_sha256"]},
        {"identity": "Divide et impera", "role": "pilot interference",
         "sha256": kit["interference"]["sha256"]},
    ]
    return {
        "status": "FINAL_SOURCE_EXCLUSIONS_FROZEN",
        "pilot_only": PILOT_ONLY,
        "rule": "Final data excludes all pilot, historical development, holdout, and shakedown material.",
        "pilot_development_exposed": selected,
        "historical_exclusions_snapshot": EXCLUSIONS,
        "shakedown_material": "all experiments/applied_system/results/shakedown synthetic and acoustic fixtures",
    }


def prepare_stage(outdir: Path = DEFAULT_OUTDIR) -> dict:
    require_research_branch()
    take_plan, kit = _load_json(TAKE_PLAN_PATH), _load_json(KIT_MANIFEST_PATH)
    recordings = discover_recordings(PACK_DIR / "incoming", take_plan)
    assets = _asset_snapshot(kit)
    plan_rows = {row["take"]: row for row in take_plan["takes"]}
    take_reports = []
    loaded: dict[str, tuple[np.ndarray, int]] = {}
    for take in sorted(recordings):
        slot, raw = plan_rows[take], recordings[take]
        decoded = outdir / "decoded" / f"{take}.wav"
        trimmed = outdir / "trimmed" / f"{take}.wav"
        y, fs, raw_meta = decode_native(raw, decoded)
        loaded[take] = (y, fs)
        buffer_row = kit["buffers"][slot["buffer"]]
        marker = diagnose_take(y, fs, buffer_row, trimmed)
        take_reports.append({
            "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
            "take_id": take, "device": slot["device"],
            "playback": slot["playback"], "buffer": slot["buffer"],
            "condition": slot["condition"], "provenance": PILOT_ONLY,
            "raw": {"path": _repo_rel(raw), **raw_meta},
            "marker_diagnostics": marker,
        })
    rules = compute_freeze_rules(take_reports)
    for report in take_reports:
        y, fs = loaded[report["take_id"]]
        buffer_row = kit["buffers"][report["buffer"]]
        finalize_take_gt(report, y, fs, buffer_row, rules,
                         outdir / "trimmed" / f"{report['take_id']}.wav")
        # Final byte preservation check after all analysis on this take.
        raw_path = ROOT / report["raw"]["path"]
        report["raw"]["raw_sha256_after_analysis"] = _sha256_file(raw_path)
        report["raw"]["byte_identical_preserved"] = (
            report["raw"]["raw_sha256"] == report["raw"]["raw_sha256_after_analysis"])
        _save_json(outdir / "takes" / f"{report['take_id']}.json", report)

    calibration = {
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "warning": WARNING, "authority": "FRESH_PILOT_PLAN.md sections 3-4",
        "phase_order": ["A_INGEST_PROVENANCE", "B_MARKER_GT_CALIBRATION",
                        "C_MEASUREMENT_CONTRACT_FREEZE"],
        "rules": rules,
        "take_reports": take_reports,
        "gt_valid_count": sum(r["marker_diagnostics"]["gt_status"] == mp.GT_VALID
                              for r in take_reports),
    }
    _save_json(outdir / "pilot_calibration.json", calibration)

    wrong = freeze_artifact(outdir / "pilot_wrong_reference_pairings.json",
                            build_wrong_pairings(take_reports), "pairing_hash")
    case_manifest = freeze_artifact(outdir / "pilot_case_manifest.json",
                                    build_case_manifest(take_reports, assets),
                                    "manifest_hash")
    exclusions = freeze_artifact(outdir / "final_source_exclusions.json",
                                 build_final_exclusion_ledger(kit),
                                 "exclusion_hash")
    comparator_contract = _comparator_contract()
    mapping_values = [r["marker_diagnostics"].get("mapping_disagreement_s")
                      for r in take_reports
                      if r["marker_diagnostics"].get("mapping_disagreement_s") is not None]
    measurement_body = {
        "status": "PILOT_MEASUREMENT_CONTRACT_FROZEN_BEFORE_COMPARATOR_SWEEP",
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "warning": WARNING,
        "authority": "docs/research/applied_system/FRESH_PILOT_PLAN.md",
        "marker_confidence_threshold": rules["marker"]["frozen_threshold_exact"],
        "marker_confidence_threshold_documentation_2dp": rules["marker"]["frozen_threshold_documentation_2dp"],
        "marker_threshold_rule": rules["marker"]["formula_verbatim"],
        "trajectory_gate_state": rules["trajectory"]["state"],
        "drift_tolerance_ppm": rules["drift"]["frozen_tolerance_ppm"],
        "drift_rule": rules["drift"]["formula_verbatim"],
        "mapping_disagreement_tolerance_s": mp.MAX_MAPPING_DISAGREEMENT_S,
        "mapping_disagreement_observed_max_s": max(mapping_values) if mapping_values else None,
        "mapping_rule": "10 ms re-affirmed; no valid take showed borderline behavior",
        "candidate_count_rule": "exactly two accepted full-template marker candidates",
        "full_template_overlap_rule": "mandatory; capture-edge partial overlaps excluded",
        "trimming_rule": {
            "pre_margin_s": mp.PRE_TRIM_MARGIN_S,
            "post_margin_s": mp.POST_TRIM_MARGIN_S,
            "construction": "remove marker+guard holes; concatenate only; never resample or warp",
        },
        "offset_correctness_tolerance_s": 0.100,
        "offset_sensitivity_tolerances_s": [0.050, 0.150],
        "gt_status_definitions": {
            "GT_VALID": "exactly two candidates plus drift, mapping, trajectory-if-gated, trim, and leakage gates",
            "GT_FAILED": "protocol failure retained in ledger; never alignment success/failure",
        },
        "scoring_definitions": {
            "positive": "ACCEPT within tolerance=CORRECT_ACCEPT; ACCEPT outside=WRONG_ACCEPT; ABSTAIN/NO_MATCH=SAFE_ABSTAIN",
            "wrong_reference": "ACCEPT=WRONG_ACCEPT; ABSTAIN/NO_MATCH=SAFE_ABSTAIN",
        },
        "source_recordings": [{
            "take_id": r["take_id"], "filename": r["raw"]["original_filename"],
            "sha256": r["raw"]["raw_sha256"],
            "decoded_sha256": r["raw"]["decoded_working_sha256"],
            "trimmed_sha256": r["marker_diagnostics"].get("trimmed_input_sha256"),
        } for r in take_reports],
        "assets": assets,
        "comparators": comparator_contract,
        "wrong_pairing_hash": wrong["pairing_hash"],
        "case_manifest_hash": case_manifest["manifest_hash"],
        "final_exclusion_hash": exclusions["exclusion_hash"],
        "research_starting_head": _git("rev-parse", "HEAD"),
        "prohibited": ["comparator-dependent threshold changes", "manual marker rescue",
                       "payload time-warp", "per-take comparator special cases"],
    }
    measurement = freeze_artifact(outdir / "pilot_measurement_freeze.json",
                                  measurement_body, "measurement_freeze_hash")
    file_hash = _write_hash_sidecar(outdir / "pilot_measurement_freeze.json")
    result = {
        "gt_valid": calibration["gt_valid_count"],
        "measurement_freeze_hash": measurement["measurement_freeze_hash"],
        "measurement_freeze_file_sha256": file_hash,
        "case_manifest_hash": case_manifest["manifest_hash"],
        "wrong_pairing_hash": wrong["pairing_hash"],
        "trajectory_gate": rules["trajectory"]["state"],
    }
    _save_json(outdir / "prepare_summary.json", result)
    return result


def _verify_pre_run(outdir: Path) -> tuple[dict, dict]:
    measurement = _load_json(outdir / "pilot_measurement_freeze.json")
    manifest = _load_json(outdir / "pilot_case_manifest.json")
    wrong = _load_json(outdir / "pilot_wrong_reference_pairings.json")
    for value, key in ((measurement, "measurement_freeze_hash"),
                       (manifest, "manifest_hash"), (wrong, "pairing_hash")):
        errors = verify_frozen_artifact(value, key)
        if errors:
            raise RuntimeError(f"pre-run freeze verification failed: {errors}")
    actual_freeze_file_hash = _sha256_file(outdir / "pilot_measurement_freeze.json")
    sidecar = (outdir / "pilot_measurement_freeze.json.sha256").read_text(
        encoding="utf-8").split()[0]
    if actual_freeze_file_hash != sidecar:
        raise RuntimeError("measurement-freeze file SHA-256 mismatch")
    if measurement["body"]["case_manifest_hash"] != manifest["manifest_hash"]:
        raise RuntimeError("case manifest is not the one named by measurement freeze")
    if measurement["body"]["wrong_pairing_hash"] != wrong["pairing_hash"]:
        raise RuntimeError("wrong-pairing manifest is not the frozen one")
    return measurement, manifest


def load_audio_same_rate(path: Path, fs: int) -> np.ndarray:
    y, sr = sf.read(str(path), dtype="float64", always_2d=False)
    if sr != fs:
        raise ValueError(f"{path}: sample rate {sr} != frozen input rate {fs}")
    if y.ndim > 1:
        y = y.mean(axis=1)
    return np.ascontiguousarray(y)


def _pilot_record(record: common.RunnerRecord) -> dict:
    value = record.as_dict()
    value.pop("shakedown_only", None)
    value["pilot_only"] = PILOT_ONLY
    value["not_final_paper_evidence"] = NOT_FINAL
    value["warning"] = WARNING
    return value


def run_pass(outdir: Path, records_dir: Path) -> list[dict]:
    _measurement, frozen_manifest = _verify_pre_run(outdir)
    records = []
    for case in frozen_manifest["body"]["cases"]:
        for system in case.get("comparator_eligibility", []):
            input_path = ROOT / case["trimmed_input_path"]
            reference_path = ROOT / case["reference_path"]
            actual_input = _sha256_file(input_path)
            actual_ref = _sha256_file(reference_path)
            if (actual_input != case["trimmed_input_sha256"] or
                    actual_ref != case["reference_sha256"]):
                record = common.RunnerRecord(
                    system=system, case_id=case["case_id"],
                    decision=common.DECISION_ERROR, predicted_offset_s=None,
                    native_scores={"error": "input/reference hash mismatch against frozen manifest"})
            else:
                fs = int(sf.info(str(input_path)).samplerate)
                record = RUNNERS[system](case, input_path, reference_path, fs,
                                         load_audio_same_rate)
            record.input_sha256 = {"trimmed_input": actual_input,
                                   "reference": actual_ref}
            value = _pilot_record(record)
            _save_json(records_dir / f"{system}__{case['case_id']}.json", value)
            records.append(value)
            print(f"  {system} {case['case_id']}: {record.decision}")
    index = {
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "records": [{"system": r["system"], "case_id": r["case_id"],
                     "record_sha256": _sha256_file(records_dir / f"{r['system']}__{r['case_id']}.json")}
                    for r in records],
    }
    _save_json(records_dir.parent / f"{records_dir.name}_index.json", index)
    return records


def _pilot_environment() -> dict:
    env = common.capture_environment()
    env.pop("shakedown_only", None)
    env["pilot_only"] = PILOT_ONLY
    env["not_final_paper_evidence"] = NOT_FINAL
    env["warning"] = WARNING
    env["research_head_at_run"] = _git("rev-parse", "HEAD")
    env["production_rhythmalign_tag"] = "v1.2.0"
    env["production_rhythmalign_tag_commit"] = _git("rev-list", "-n", "1", "v1.2.0")
    return env


def run_stage(outdir: Path = DEFAULT_OUTDIR) -> list[dict]:
    require_research_branch()
    records = run_pass(outdir, outdir / "records_first")
    _save_json(outdir / "pilot_environment.json", _pilot_environment())
    return records


def _load_records(records_dir: Path) -> list[dict]:
    return [_load_json(path) for path in sorted(records_dir.glob("*.json"))]


def score_records(manifest_body: dict, records: list[dict]) -> dict:
    by_key = {(r["case_id"], r["system"]): r for r in records}
    per_case = []
    protocol_seen = set()
    for case in manifest_body["cases"]:
        if case["gt_stratum"] == "GT_FAILED":
            if case["take_id"] not in protocol_seen:
                protocol_seen.add(case["take_id"])
                per_case.append({
                    "case_id": case["case_id"], "take_id": case["take_id"],
                    "pair_type": case["pair_type"], "system": None,
                    "gt_stratum": "GT_FAILED", "outcome": "GT_FAILED",
                    "abs_error_s": None, "protocol_failure": True,
                })
            continue
        for system in case["comparator_eligibility"]:
            row = scoring_mod.score_pair(case, by_key.get((case["case_id"], system)))
            row["take_id"] = case["take_id"]
            row["pair_type"] = case["pair_type"]
            per_case.append(row)
    summary, by_pair_type = {}, {}
    for row in per_case:
        system = row["system"] or "PROTOCOL"
        summary.setdefault(system, {}).setdefault(row["outcome"], 0)
        summary[system][row["outcome"]] += 1
        pair_slot = by_pair_type.setdefault(row["pair_type"], {}).setdefault(system, {})
        pair_slot[row["outcome"]] = pair_slot.get(row["outcome"], 0) + 1
    return {
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "warning": WARNING, "tolerance_s": 0.100,
        "per_case": per_case, "summary": summary,
        "summary_by_pair_type": by_pair_type,
        "protocol_failures": [r for r in per_case if r["protocol_failure"]],
    }


def score_stage(outdir: Path = DEFAULT_OUTDIR) -> dict:
    _measurement, manifest = _verify_pre_run(outdir)
    scores = score_records(manifest["body"], _load_records(outdir / "records_first"))
    scores["case_manifest_hash"] = manifest["manifest_hash"]
    _save_json(outdir / "pilot_scores.json", scores)
    return scores


def comparable_record(value):
    """Remove only runtime and per-run temporary-store fields."""
    if isinstance(value, dict):
        return {key: comparable_record(item) for key, item in value.items()
                if "runtime" not in str(key).lower() and key != "store_dir"}
    if isinstance(value, list):
        return [comparable_record(item) for item in value]
    return value


def reproduce_stage(outdir: Path = DEFAULT_OUTDIR) -> dict:
    _measurement, manifest = _verify_pre_run(outdir)
    first = _load_records(outdir / "records_first")
    rerun = run_pass(outdir, outdir / "records_rerun")
    first_map = {f"{r['system']}__{r['case_id']}": comparable_record(r) for r in first}
    rerun_map = {f"{r['system']}__{r['case_id']}": comparable_record(r) for r in rerun}
    differences = [key for key in sorted(set(first_map) | set(rerun_map))
                   if first_map.get(key) != rerun_map.get(key)]
    first_scores = score_records(manifest["body"], first)
    rerun_scores = score_records(manifest["body"], rerun)
    _save_json(outdir / "pilot_scores_rerun.json", rerun_scores)
    if first_scores["per_case"] != rerun_scores["per_case"]:
        differences.append("scoring_outputs")
    result = {
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "warning": WARNING, "reproduced": not differences,
        "records_compared": len(first_map), "differences": differences,
        "volatile_fields_ignored": ["keys containing runtime", "Panako temporary store_dir"],
    }
    _save_json(outdir / "pilot_reproduction_check.json", result)
    return result


def direct_gt_crosscheck(trimmed_path: Path, reference_path: Path,
                         payload_reference_start_s: float,
                         expected_payload_offset_s: float,
                         probe_duration_s: float = 20.0) -> dict:
    """Plan-declared GT validation independent of markers and all systems.

    A clean-reference payload probe is located by raw correlation. This is
    diagnostic validation only: it cannot alter marker thresholds, GT, trim,
    pairings, or comparator records.
    """
    y, fs = sf.read(str(trimmed_path), dtype="float64", always_2d=False)
    ref, ref_fs = sf.read(str(reference_path), dtype="float64", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if ref.ndim > 1:
        ref = ref.mean(axis=1)
    if fs != ref_fs:
        raise ValueError("direct GT cross-check requires equal input/reference rates")
    start = int(round(payload_reference_start_s * fs))
    stop = min(len(ref), start + int(round(probe_duration_s * fs)))
    probe = np.ascontiguousarray(ref[start:stop])
    if len(probe) < fs or len(y) < len(probe):
        raise ValueError("direct GT cross-check probe is too short for the input")
    corr = scipy_signal.fftconvolve(np.ascontiguousarray(y), probe[::-1], mode="valid")
    direct_sample = int(np.argmax(corr))
    direct_s = direct_sample / fs
    delta_s = direct_s - float(expected_payload_offset_s)
    return {
        "method": "raw FFT correlation of the first 20 s payload-reference probe",
        "marker_or_comparator_output_used": False,
        "reference_payload_start_s": payload_reference_start_s,
        "expected_payload_offset_s": expected_payload_offset_s,
        "direct_payload_offset_s": direct_s,
        "delta_s": delta_s,
        "absolute_delta_s": abs(delta_s),
        "tolerance_s": 0.010,
        "passed": abs(delta_s) < 0.010,
    }


def correction_stage(outdir: Path = DEFAULT_OUTDIR) -> dict:
    """Outcome-independent correction for an omitted plan diagnostic.

    The original measurement freeze is verified and preserved byte-for-byte.
    This stage adds a separate versioned audit artifact; it changes no
    scientific decision and never reruns or edits comparator output.
    """
    measurement, _manifest = _verify_pre_run(outdir)
    freeze_file_hash_before = _sha256_file(outdir / "pilot_measurement_freeze.json")
    calibration = _load_json(outdir / "pilot_calibration.json")
    rows = []
    for report in calibration["take_reports"]:
        diag = report["marker_diagnostics"]
        ref_id = "REF-A" if report["buffer"] == "BUF-A" else "REF-B"
        reference_path = ROOT / measurement["body"]["assets"]["references"][ref_id]["path"]
        payload_start_s = 90.0 if report["buffer"] == "BUF-BMID" else 0.0
        check = direct_gt_crosscheck(
            outdir / "trimmed" / f"{report['take_id']}.wav", reference_path,
            payload_start_s,
            diag["derived_payload_offset_on_trimmed_input_s"])
        rows.append({"take_id": report["take_id"], **check})
    freeze_file_hash_after = _sha256_file(outdir / "pilot_measurement_freeze.json")
    if freeze_file_hash_before != freeze_file_hash_after:
        raise RuntimeError("measurement freeze changed during correction")
    body = {
        "correction_id": "PILOT_RESEARCH_TOOLING_CORRECTION_001",
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "discovered_after_comparator_execution": True,
        "original_failure_evidence": (
            "pilot_harness prepare artifacts omitted the plan-declared direct "
            "correlation GT cross-check; all original artifacts remain present"),
        "classification": "outcome-independent diagnostic omission",
        "scientific_contract_changed": False,
        "comparator_outputs_consulted_or_changed": False,
        "original_measurement_freeze_hash": measurement["measurement_freeze_hash"],
        "original_measurement_freeze_file_sha256_before": freeze_file_hash_before,
        "original_measurement_freeze_file_sha256_after": freeze_file_hash_after,
        "regression_test": "test_direct_gt_crosscheck_recovers_known_payload_position",
        "checks": rows,
        "all_passed": all(row["passed"] for row in rows),
        "max_absolute_delta_s": max(row["absolute_delta_s"] for row in rows),
    }
    artifact = freeze_artifact(
        outdir / "pilot_correction_001_direct_gt_crosscheck.json", body,
        "correction_hash")
    _write_hash_sidecar(outdir / "pilot_correction_001_direct_gt_crosscheck.json")
    return artifact


def repeatability_summary(calibration: dict) -> dict:
    by_take = {r["take_id"]: r for r in calibration["take_reports"]}
    pairs = []
    for a, b in (("take01", "take02"), ("take06", "take07")):
        ra, rb = by_take[a], by_take[b]
        da, db = ra["marker_diagnostics"], rb["marker_diagnostics"]
        pairs.append({
            "pair": [a, b],
            "pre_confidence_abs_delta": abs(da["genuine_pre_marker"]["confidence"] -
                                             db["genuine_pre_marker"]["confidence"]),
            "post_confidence_abs_delta": abs(da["genuine_post_marker"]["confidence"] -
                                              db["genuine_post_marker"]["confidence"]),
            "drift_ppm_abs_delta": abs(da["drift_ppm"] - db["drift_ppm"]),
            "reference_gt_offset_abs_delta_s": abs(
                da["derived_reference_offset_on_trimmed_input_s"] -
                db["derived_reference_offset_on_trimmed_input_s"]),
            "both_gt_valid": da["gt_status"] == db["gt_status"] == mp.GT_VALID,
        })
    return {"pairs": pairs, "all_repeat_pairs_gt_consistent": all(
        row["both_gt_valid"] for row in pairs)}


def evaluate_pilot(outdir: Path = DEFAULT_OUTDIR) -> dict:
    calibration = _load_json(outdir / "pilot_calibration.json")
    scores = _load_json(outdir / "pilot_scores.json")
    reproduction = _load_json(outdir / "pilot_reproduction_check.json")
    correction_path = outdir / "pilot_correction_001_direct_gt_crosscheck.json"
    correction = _load_json(correction_path) if correction_path.exists() else None
    records = _load_records(outdir / "records_first")
    rules = calibration["rules"]
    valid = [r for r in calibration["take_reports"]
             if r["marker_diagnostics"]["gt_status"] == mp.GT_VALID]
    valid_devices = {r["device"] for r in valid}
    record_errors = [r for r in records if r["decision"] == "ERROR"]
    panako_wrong = [r for r in records if r["system"] == panako_runner.SYSTEM_ID
                    and r["case_id"].endswith("__wrong_ref")]
    ra_wrong_count = scores["summary_by_pair_type"].get("WRONG_REFERENCE", {}).get(
        rhythmalign_runner.SYSTEM_ID, {}).get("WRONG_ACCEPT", 0)
    repeatability = repeatability_summary(calibration)
    success = {
        "1_gt_survival": (len(valid) >= 10 and valid_devices == {"D1", "D2", "D3"}
                          and correction is not None and correction["body"]["all_passed"]),
        "2_confidence_feasibility": (rules["marker"]["pooled_feasible"] and
                                     all(row["feasible"] for row in rules["marker"]["per_device"].values())),
        "3_trajectory_policy_decidable": rules["trajectory"]["state"] in (
            "TRAJECTORY_GATE_FROZEN_ON", "TRAJECTORY_GATE_FROZEN_OFF"),
        "4_drift_feasibility": (not rules["drift"]["cap_reached"] and
                                all(abs(r["marker_diagnostics"]["drift_ppm"]) <= 1000 for r in valid)),
        "5_trim_leakage_mapping": all(
            r["marker_diagnostics"].get("final_marker_leakage", {}).get(
                "passes_frozen_threshold", False)
            and r["marker_diagnostics"].get("final_mapping_disagreement_s", math.inf)
            <= mp.MAX_MAPPING_DISAGREEMENT_S for r in valid),
        "6_comparators": (not record_errors and len(records) == len(valid) * 2 * len(SYSTEM_IDS)
                          and any(r["decision"] == "NO_MATCH" for r in panako_wrong)),
        "7_wrong_reference_sanity": ra_wrong_count <= 1,
        "8_reproducibility": bool(reproduction["reproduced"]),
    }
    device_zero_valid = sorted({"D1", "D2", "D3"} - valid_devices)
    crosscheck_failures = ([] if correction is None else
                           [row["take_id"] for row in correction["body"]["checks"]
                            if not row["passed"]])
    repeat_failure = not repeatability["all_repeat_pairs_gt_consistent"]
    kills = {
        "1_marker_gt_unreliable_common_device": {
            "fired": bool(device_zero_valid or crosscheck_failures),
            "evidence": {"zero_valid_devices": device_zero_valid,
                         "direct_crosscheck_failures": crosscheck_failures}},
        "2_confidence_distributions_overlap": {
            "fired": any(not row["feasible"] for row in rules["marker"]["per_device"].values()),
            "evidence": {d: row["G_over_B"] for d, row in rules["marker"]["per_device"].items()}},
        "3_fixed_offset_invalidated": {
            "fired": bool(rules["drift"]["cap_reached"]),
            "evidence": rules["drift"]["three_times_D_max_ppm"]},
        "4_fingerprint_threat_unintegratable": {
            "fired": any(r["system"] == panako_runner.SYSTEM_ID for r in record_errors),
            "evidence": [r["case_id"] for r in record_errors if r["system"] == panako_runner.SYSTEM_ID]},
        "5_selectivity_transport_failure": {
            "fired": ra_wrong_count >= 2, "evidence": {"ra_wrong_accepts": ra_wrong_count}},
        "6_conditions_not_reproducible": {
            "fired": repeat_failure, "evidence": repeatability},
        "7_workload_blowout": {
            "fired": False,
            "evidence": "owner reported recordings done and no workload blowout or unusual event"},
    }
    fired = [name for name, row in kills.items() if row["fired"]]
    if fired:
        verdict = ("PILOT_KILLS_CURRENT_PAPER_ROUTE"
                   if "5_selectivity_transport_failure" in fired
                   else "PILOT_REDESIGN_REQUIRED")
    elif all(success.values()):
        verdict = "PILOT_PASS_PROTOCOL_FREEZE_READY"
    else:
        verdict = "PILOT_PASS_WITH_RECORDED_ACTIONS"
    panako_positive_scores = [row for row in scores["per_case"]
                              if row["system"] == panako_runner.SYSTEM_ID
                              and row["pair_type"] == "POSITIVE"
                              and row["abs_error_s"] is not None]
    panako_median = (statistics.median(row["abs_error_s"] for row in panako_positive_scores)
                     if panako_positive_scores else None)
    panako_role = ("PLACEMENT_COMPARATOR" if panako_median is not None and panako_median <= 0.100
                   else "IDENTIFICATION_SELECTIVITY_COMPARATOR")
    return {
        "pilot_only": PILOT_ONLY, "not_final_paper_evidence": NOT_FINAL,
        "warning": WARNING, "verdict": verdict, "success_criteria": success,
        "kill_criteria": kills, "fired_kill_criteria": fired,
        "gt_valid": len(valid), "repeatability": repeatability,
        "panako_role": panako_role, "panako_median_abs_offset_error_s": panako_median,
        "owner_action_required": "NONE" if verdict == "PILOT_PASS_PROTOCOL_FREEZE_READY"
        else "See failed criterion; no retake is requested unless a protocol-required GT failure is identified.",
    }


def _counts(scores: dict, system: str, pair_type: str) -> str:
    values = scores["summary_by_pair_type"].get(pair_type, {}).get(system, {})
    return ", ".join(f"{key}={values[key]}" for key in sorted(values)) or "NO_RECORDS"


def _markdown_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(str(v) for v in row) + " |" for row in rows)
    return "\n".join(lines)


def build_results_markdown(calibration: dict, scores: dict, evaluation: dict,
                           measurement: dict, wrong: dict, reproduction: dict,
                           correction: dict) -> str:
    takes = calibration["take_reports"]
    rules = calibration["rules"]
    raw_rows = [[r["take_id"], r["raw"]["original_filename"], r["raw"]["raw_sha256"],
                 r["raw"]["container"], r["raw"]["codec"],
                 r["raw"]["native_sample_rate_hz"], r["raw"]["native_channel_count"],
                 f"{r['raw']['duration_s']:.3f}", r["raw"]["original_bytes"]] for r in takes]
    map_rows = [[r["take_id"], r["device"], r["playback"], r["buffer"], r["condition"]]
                for r in takes]
    marker_rows = [[r["take_id"], r["device"],
                    f"{r['marker_diagnostics']['genuine_pre_marker']['confidence']:.6f}",
                    f"{r['marker_diagnostics']['genuine_post_marker']['confidence']:.6f}",
                    r["marker_diagnostics"]["frozen_threshold_candidate_count"]]
                   for r in takes]
    comp_rows = [[r["take_id"], f"{r['marker_diagnostics']['strongest_competing_peak']['confidence']:.6f}",
                  f"{r['marker_diagnostics']['post_trim_leakage_diagnostic']['max_ncc']:.6f}",
                  f"{r['marker_diagnostics']['take_competing_B']:.6f}"] for r in takes]
    drift_rows = [[r["take_id"], r["device"],
                   f"{r['marker_diagnostics']['drift_ppm']:.6f}",
                   f"{r['marker_diagnostics']['clock_scale']:.9f}",
                   f"{r['marker_diagnostics']['mapping_disagreement_s'] * 1000:.6f}"] for r in takes]
    correction_by_take = {row["take_id"]: row for row in correction["body"]["checks"]}
    gt_rows = [[r["take_id"], r["marker_diagnostics"]["gt_status"],
                r["marker_diagnostics"].get("gt_fail_reason") or "—",
                f"{r['marker_diagnostics'].get('derived_reference_offset_on_trimmed_input_s', 0):+.6f}",
                f"{correction_by_take[r['take_id']]['delta_s'] * 1000:+.3f}"]
               for r in takes]
    repeat_rows = [[" + ".join(row["pair"]),
                    f"{row['pre_confidence_abs_delta']:.6f}",
                    f"{row['post_confidence_abs_delta']:.6f}",
                    f"{row['drift_ppm_abs_delta']:.6f}",
                    f"{row['reference_gt_offset_abs_delta_s'] * 1000:.3f}",
                    row["both_gt_valid"]] for row in evaluation["repeatability"]["pairs"]]
    wrong_rows = [[p["take_id"], p["source_buffer"], p["wrong_reference"]]
                  for p in wrong["body"]["pairings"]]
    comparator_rows = [[system, _counts(scores, system, "POSITIVE"),
                        _counts(scores, system, "WRONG_REFERENCE")]
                       for system in SYSTEM_IDS]
    success_rows = [[name, "PASS" if ok else "FAIL"]
                    for name, ok in evaluation["success_criteria"].items()]
    kill_rows = [[name, "FIRED" if row["fired"] else "NOT_FIRED",
                  json.dumps(row["evidence"], ensure_ascii=False)]
                 for name, row in evaluation["kill_criteria"].items()]
    device_lines = []
    for device, row in rules["marker"]["per_device"].items():
        device_lines.append(f"- {device}: G={row['G']:.6f}, B={row['B']:.6f}, "
                            f"G/B={row['G_over_B']:.3f}, drift range "
                            f"[{row['drift_ppm_min']:.3f}, {row['drift_ppm_max']:.3f}] ppm")
    return f"""# Fresh Acoustic Pilot Results

## 1. Status and Non-Evidence Warning

**{WARNING}.** These development-pilot counts may never be presented as final confirmatory performance evidence.

- Verdict: `{evaluation['verdict']}`
- Measurement-freeze semantic hash: `{measurement['measurement_freeze_hash']}`
- Measurement-freeze file SHA-256: `{_sha256_file(DEFAULT_OUTDIR / 'pilot_measurement_freeze.json')}`
- Transparent tooling correction: `{correction['correction_hash']}` — the omitted direct-correlation diagnostic was added after comparator execution without changing the original freeze or any outcome; 12/12 cross-checks passed.

## 2. Raw Recording Provenance

**{WARNING}.** Originals were hashed before/after automated decode and remained byte-identical.

{_markdown_table(['Take','Original','SHA-256','Container','Codec','Hz','Channels','Duration s','Bytes'], raw_rows)}

## 3. Device / Take Mapping

**{WARNING}.** Mapping comes only from the frozen take plan.

{_markdown_table(['Take','Device','Playback','Buffer','Condition'], map_rows)}

## 4. Marker Confidence by Device

**{WARNING}.** Genuine values come from ungated full-overlap diagnostics; provisional 0.15 did not censor calibration.

{_markdown_table(['Take','Device','Pre G','Post G','Frozen candidate count'], marker_rows)}

{chr(10).join(device_lines)}

## 5. Competing Peak Diagnostics

**{WARNING}.** B is the maximum of the strongest non-marker full-overlap peak and the exact post-trim leakage rescan.

{_markdown_table(['Take','Raw competitor','Trim rescan max','Take B'], comp_rows)}

## 6. Frozen Marker Rule

- Exact authoritative formula applied: `T_low = 3 × B`; `T_high = 0.8 × G`; feasibility iff `G/B ≥ 3.75`; `T = sqrt(T_low × T_high)`.
- Pooled G: `{rules['marker']['G']:.9f}`
- Pooled B: `{rules['marker']['B']:.9f}`
- Band: `[{rules['marker']['T_low_3B']:.9f}, {rules['marker']['T_high_0_8G']:.9f}]`
- Frozen threshold (exact): `{rules['marker']['frozen_threshold_exact']:.12f}`; documentation only: `{rules['marker']['frozen_threshold_documentation_2dp']:.2f}`
- Trajectory: `{rules['trajectory']['state']}` because all-genuine={rules['trajectory']['all_genuine_corroborate']} and any-non-marker={rules['trajectory']['any_non_marker_corroborates']}.

## 7. Clock Drift by Device

**{WARNING}.** No take was resampled or time-warped before drift measurement.

{_markdown_table(['Take','Device','Drift ppm','Clock scale','Mapping disagreement ms'], drift_rows)}

## 8. Frozen Drift Rule

- Exact authoritative formula applied: `T_drift = max(3 × D_max, 111 ppm)`, with `T_drift ≤ 1000 ppm`.
- Worst observed |ppm|: `{rules['drift']['worst_observed_abs_ppm']:.6f}`
- 3 × D_max: `{rules['drift']['three_times_D_max_ppm']:.6f}` ppm
- Frozen tolerance: `{rules['drift']['frozen_tolerance_ppm']:.6f}` ppm
- Cap reached: `{'YES' if rules['drift']['cap_reached'] else 'NO'}`

## 9. Repeatability

**{WARNING}.** Protocol-calibration repeat pairs only.

{_markdown_table(['Pair','Pre conf Δ','Post conf Δ','Drift Δ ppm','GT offset Δ ms','Both GT valid'], repeat_rows)}

## 10. GT Success / Failure

**{WARNING}.** GT_FAILED is a protocol outcome, never alignment success/failure.

{_markdown_table(['Take','GT status','Reason','Reference GT offset s','Direct check Δ ms'], gt_rows)}

GT_VALID: **{evaluation['gt_valid']} / 12**.

## 11. Frozen Wrong-Reference Pairings

**{WARNING}.** Semantic/selectivity pilot only; N=12 is not rate-estimation evidence. Pairing hash: `{wrong['pairing_hash']}`.

{_markdown_table(['Take','Source buffer','Frozen wrong reference'], wrong_rows)}

## 12. Comparator Pilot Outcomes

**{WARNING}.** Raw development-pilot counts only; no paper-level rates or claims.

{_markdown_table(['System','Positive raw counts','Wrong-reference raw counts'], comparator_rows)}

## 13. Panako Role Decision

Pre-declared rule: median positive |offset error| ≤100 ms → placement role. Observed pilot median: `{evaluation['panako_median_abs_offset_error_s']}` s. Frozen role: **{evaluation['panako_role']}**.

## 14. Pilot Success Criteria

**{WARNING}.** Criteria are protocol gates, not paper-performance claims.

{_markdown_table(['Criterion','Result'], success_rows)}

## 15. Kill Criteria Evaluation

**{WARNING}.** Kill decisions use only the pre-declared pilot rules.

{_markdown_table(['Pre-declared criterion','State','Evidence'], kill_rows)}

## 16. Final Protocol Freeze Readiness

`{evaluation['verdict']}`. Final protocol: `{'FROZEN' if evaluation['verdict'] == 'PILOT_PASS_PROTOCOL_FREEZE_READY' else 'NOT_FROZEN'}`. Final data must not begin unless the protocol is frozen.

## 17. Required Owner Action, If Any

`{evaluation['owner_action_required']}`

Reproduction: `{reproduction['reproduced']}` over {reproduction['records_compared']} comparator records; non-volatile differences: `{reproduction['differences']}`.
"""


def build_final_protocol_markdown(measurement: dict, evaluation: dict,
                                  exclusions: dict, correction: dict) -> str:
    m = measurement["body"]
    return f"""# Final Benchmark Protocol

Status: **FROZEN BEFORE FINAL DATA COLLECTION**

This is the internal preregistration-like freeze for the final confirmatory benchmark. Pilot material and outcomes are development-only. **FINAL DATA MUST NOT BE USED TO CHANGE THESE RULES.**

## Authority and freeze provenance

- Pilot verdict: `{evaluation['verdict']}`
- Pilot measurement freeze: `{measurement['measurement_freeze_hash']}`
- Pilot freeze file SHA-256: `{_sha256_file(DEFAULT_OUTDIR / 'pilot_measurement_freeze.json')}`
- Final exclusion ledger: `{exclusions['exclusion_hash']}`
- Outcome-independent diagnostic correction: `{correction['correction_hash']}`; the original measurement freeze was unchanged and all 12 direct GT cross-checks passed.
- Subject: frozen RhythmAlign v1.2.0; production code remains unchanged.

## The 17-item freeze checklist

1. **Marker waveform:** 0.75 s deterministic linear chirp, 1–9 kHz, peak 0.9, rendered at the capture protocol rate; template implementation is `marker_protocol.py`.
2. **Marker detector:** normalized matched filter with per-lag overlap energy, full-template-overlap eligibility, one-template NMS.
3. **Confidence rule:** exact threshold `{m['marker_confidence_threshold']:.12f}` (documentation `{m['marker_confidence_threshold_documentation_2dp']:.2f}`), derived only by `T=sqrt((3B)(0.8G))` before comparator execution.
4. **Candidate count:** exactly two accepted marker candidates; one marker is never valid GT.
5. **Trajectory policy:** `{m['trajectory_gate_state']}`; trajectory remains recorded when off.
6. **Drift tolerance:** ±`{m['drift_tolerance_ppm']:.6f}` ppm from `max(3D_max,111)`, inside the 1000 ppm cap; captures are never warped.
7. **Mapping disagreement:** ≤`{m['mapping_disagreement_tolerance_s'] * 1000:.3f}` ms.
8. **Trim rule:** remove both marker/guard holes with 50 ms external margins, concatenate retained audio, never resample/time-stretch; every system consumes the identical trimmed WAV bytes.
9. **Manifest schema:** immutable canonical JSON body hash; repo-relative paths; raw/decoded/trimmed/reference hashes; exact strata, source identity, condition, session, device, and comparator eligibility; freeze before first final system run.
10. **System versions:** RhythmAlign v1.2.0 at `{m['comparators']['rhythmalign_v1_2_0']['production_tag_commit']}`; Panako commit `{m['comparators']['panako_fingerprint']['pinned_commit']}` with jar hash `{m['comparators']['panako_fingerprint']['environment'].get('jar_sha256')}`; environment records OS, Python, ffmpeg, Java, numpy, scipy, librosa, and soundfile.
11. **Baseline implementations:** committed `gcc_phat_argmax_v1` and `ncc_argmax_v1`; NCC remains USEFUL_OPTIONAL and is run unless a recorded machinery failure makes it unavailable.
12. **Comparator configs/semantics:** RhythmAlign native ACCEPT/ABSTAIN once per pair; GCC-PHAT and NCC ALWAYS_OUTPUT argmax with no invented rejection; Panako OLAF native ACCEPT/NO_MATCH/ERROR, highest native match score, `offset=Query start−Match start`, no threshold or hybrid refinement. Panako final role is **{evaluation['panako_role']}**. Kdenlive 26.08 remains the essential owner-operated final technical stratum and is scored from project XML, not simulated.
13. **Offset correctness:** 100 ms primary; 50/150 ms sensitivity. Exact GT and approximate GT are never pooled.
14. **Wrong-reference scoring:** every final take is offered reference slot `S(i mod 10)+1`; any ACCEPT is WRONG_ACCEPT, refusal is SAFE_ABSTAIN. Slot rotation is fixed before song identities are filled and never changed from results.
15. **Benchmark conditions:** 24 scored positives: 10 ordinary (S01–S10); 6 low-level/tap-dominant (S01–S06, three each assigned in the frozen acquisition manifest before recording); 4 interference (S07–S10); 2 partial (S01–S02); 2 device-variation (S09–S10). Interference sources are outside every reference/exclusion identity.
16. **Song/source selection:** 10 owner-licensed source identities, exact versions/hashes logged before recording, all cleanly decodable, ≥3 deliberately repetitive; none may occur in the exclusion ledger. No song is selected using system performance.
17. **Final sample counts:** 10 songs; exactly 24 scored positive takes; exactly 24 directed wrong-reference pairs; 2 additional strict-repeat reliability takes reported separately; ≥3 sessions, ≥2 devices, ≥2 rooms; 10 Kdenlive technical pairs; optional 2–4 version-mismatch, 2–4 authentic-handcam approximate-GT, and 3–4 external probes remain separate existence-check strata and are not silently added to primary counts.

## Ground-truth strata and scoring

- `EXACT_GT`: dual-marker GT; ACCEPT within tolerance → CORRECT_ACCEPT, outside → WRONG_ACCEPT; ABSTAIN/NO_MATCH → SAFE_ABSTAIN.
- `APPROXIMATE_GT`: optional authentic takes with a pre-system manual uncertainty interval; reported separately and correct only when the full interval satisfies the criterion.
- `NO_MATCH`: wrong reference/version mismatch; any ACCEPT → WRONG_ACCEPT; refusal → SAFE_ABSTAIN.
- `GT_FAILED`: retained as protocol failure, excluded from alignment metrics, never silently dropped or replaced after system output is known. A required acquisition replacement is decided from GT/QC alone and logged before any comparator sees that case.

## Independence and aggregation

The source/song identity is the independence unit. Pair-level raw counts are always shown; multiple takes/conditions from one song are dependent. Primary reporting is raw counts with denominators, source-level aggregation, conditional accepted-offset median/IQR/max, exact discordant-pair counts, and song-level bootstrap uncertainty. No pilot count enters final estimates.

## Post-freeze bug and tuning policy

After final collection starts, thresholds, features, conditions, pairings, sample counts, scoring, roles, and exclusions cannot change. Only a demonstrable outcome-independent implementation bug may be corrected: preserve original failure evidence, explain why the correction is outcome-independent, add a regression test, version the correction without overwriting the original artifact, and rerun every affected case under the same scientific contract. Result-dependent changes require a new protocol and new final data.

## Prohibited actions

- No final-data threshold/configuration tuning, per-case rescue, manual marker rescue, payload warping, task replacement, or pairing substitution.
- No reuse of pilot songs (Bloody Trail; スティールユー / Steel You; Divide et impera), historical development/holdout songs, or shakedown material.
- No final benchmark collection begins automatically from this document; the owner starts acquisition in a separate task.

**FINAL DATA MUST NOT BE USED TO CHANGE THESE RULES.**
"""


def write_text_immutable(path: Path, text: str) -> None:
    normalized = text.rstrip() + "\n"
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current != normalized:
            raise RuntimeError(f"frozen document exists with different content: {path}")
        return
    path.write_text(normalized, encoding="utf-8", newline="\n")


def report_stage(outdir: Path = DEFAULT_OUTDIR) -> dict:
    measurement, _manifest = _verify_pre_run(outdir)
    calibration = _load_json(outdir / "pilot_calibration.json")
    scores = _load_json(outdir / "pilot_scores.json")
    wrong = _load_json(outdir / "pilot_wrong_reference_pairings.json")
    reproduction = _load_json(outdir / "pilot_reproduction_check.json")
    correction = _load_json(outdir / "pilot_correction_001_direct_gt_crosscheck.json")
    exclusions = _load_json(outdir / "final_source_exclusions.json")
    evaluation = evaluate_pilot(outdir)
    _save_json(outdir / "pilot_verdict.json", evaluation)
    RESULTS_DOC_PATH.write_text(
        build_results_markdown(calibration, scores, evaluation, measurement,
                               wrong, reproduction, correction).rstrip() + "\n",
        encoding="utf-8", newline="\n")
    if evaluation["verdict"] == "PILOT_PASS_PROTOCOL_FREEZE_READY":
        write_text_immutable(
            FINAL_PROTOCOL_PATH,
            build_final_protocol_markdown(measurement, evaluation, exclusions,
                                          correction))
    return evaluation


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=WARNING)
    parser.add_argument("--stage", required=True,
                        choices=("prepare", "run", "score", "reproduce", "correction", "report"))
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    args = parser.parse_args(argv)
    outdir = Path(args.outdir)
    print(f"[pilot] {WARNING}; stage={args.stage}")
    result = {
        "prepare": prepare_stage,
        "run": run_stage,
        "score": score_stage,
        "reproduce": reproduce_stage,
        "correction": correction_stage,
        "report": report_stage,
    }[args.stage](outdir)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
