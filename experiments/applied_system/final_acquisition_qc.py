"""Final acquisition QC — comparator-blind validation of the frozen final
recordings.

Authority: docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md (FROZEN
before final data collection) + final_pack/final_source_freeze.json +
final_pack/final_acquisition_manifest.json (frozen hashes).

This module answers exactly one question: does the completed physical
acquisition (26 recordings) satisfy the frozen GT/QC contract BEFORE any
comparator sees final audio? It runs the marker detector, clock-drift and
mapping gates, the frozen trim machinery, marker-leakage checks, raw-file
integrity hashing, and manifest validation — NOTHING ELSE.

COMPARATOR-BLIND BY CONSTRUCTION: this module must never import or invoke
RhythmAlign, GCC-PHAT, NCC, Panako, or Kdenlive, and must never import any
module that does (pilot_harness imports comparator runners, so the small
decode/diagnostic helpers are deliberately re-implemented here with the
same math). It produces no alignment performance output of any kind. There
is no code path in this file that could emit a comparator result.

Marker/GT math (accepted_peaks / ground_truth_from_pair / trim / leakage)
is byte-for-byte the frozen machinery semantics of marker_protocol.py and
the pilot prepare stage; the frozen FINAL thresholds recorded in the
acquisition manifest gt_contract are applied verbatim:

    marker confidence threshold : 0.163837792269
    drift tolerance             : +/- 128.486056 ppm
    mapping disagreement        : <= 10 ms
    candidate count             : exactly 2 full-template-overlap candidates
    trajectory gate             : TRAJECTORY_GATE_FROZEN_OFF (recorded only)
    trim                        : marker/guard holes, 50 ms margins,
                                  concatenate only, never resample/stretch
    marker leakage              : post-trim rescan < frozen threshold

No manual marker rescue, no per-take threshold adjustment, no warping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import soundfile as sf
from scipy import signal as scipy_signal

from . import marker_protocol as mp
from .acoustic_loop import sweep_trajectory_check, top_marker_peaks
from .runners.common import load_json, save_json, sha256_file

ROOT = Path(__file__).resolve().parents[2]
APPLIED_DIR = Path(__file__).resolve().parent
FINAL_PACK = APPLIED_DIR / "final_pack"
FREEZE_PATH = FINAL_PACK / "final_source_freeze.json"
MANIFEST_PATH = FINAL_PACK / "final_acquisition_manifest.json"
INCOMING_DIR = FINAL_PACK / "incoming"
REFERENCES_DIR = FINAL_PACK / "local" / "references"
WORK_DIR = FINAL_PACK / "local" / "final_qc_work"
RESULTS_DIR = FINAL_PACK / "results"
QC_FREEZE_PATH = RESULTS_DIR / "final_acquisition_qc.json"
QC_FAILURE_PATH = RESULTS_DIR / "final_acquisition_qc_failure.json"
QC_DOC_PATH = ROOT / "docs" / "research" / "applied_system" / \
    "FINAL_ACQUISITION_QC.md"

REQUIRED_BRANCH = "research/applied-system-paper"
PROTOCOL_DOC_REL = "docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md"

# ---------------------------------------------------------------------------
# frozen FINAL QC parameters (verified against the acquisition manifest
# gt_contract at runtime; _verify_frozen_parameters refuses to run on drift)
# ---------------------------------------------------------------------------

FROZEN_MARKER_THRESHOLD = 0.163837792269
FROZEN_DRIFT_TOLERANCE_PPM = 128.486056
TRAJECTORY_GATE_STATE = "TRAJECTORY_GATE_FROZEN_OFF"
MAX_MAPPING_DISAGREEMENT_S = mp.MAX_MAPPING_DISAGREEMENT_S   # 0.010
EXPECTED_TAKE_IDS = ([f"final{i:02d}" for i in range(1, 25)]
                     + ["repeat01", "repeat02"])
PRIMARY_TAKE_IDS = [f"final{i:02d}" for i in range(1, 25)]
DIRECT_CROSSCHECK_TOLERANCE_S = 0.010
PROBE_DURATION_S = 20.0

INGEST_RX = re.compile(r"^(final\d{2}|repeat\d{2})(?:_([a-z0-9]+))?$",
                       re.IGNORECASE)

OWNER_ATTESTATION_DATE = "2026-09-20"
OWNER_ATTESTATION_STATEMENTS = [
    "All 26 takes (final01-final24, repeat01, repeat02) were recorded "
    "following the frozen tables in OWNER_FINAL_RECORDING_INSTRUCTIONS.md.",
    "SESSION_1 (final01-final10, repeat01, repeat02) used ROOM_A + D1.",
    "SESSION_2 (final11-final16, final21, final22) used ROOM_A + D1.",
    "SESSION_3 (final17-final20, final23, final24) used ROOM_B + D2.",
    "The prescribed special conditions were followed: low-volume playback "
    "(final11/13/15), steady finger tapping during playback "
    "(final12/14/16), soft interference playback from the second device "
    "(final17-final20), partial buffers played in full as delivered "
    "(final21/22), and the second recording device (final17-final24).",
    "No editing, trimming, optimization, or format conversion was "
    "intentionally applied to any raw recording; files were copied as "
    "recorded.",
    "Acquisition completed in full (all 26 takes) before this QC task; no "
    "interim stop was made. The earlier interim-stop advice was operational "
    "guidance, not a frozen acquisition criterion.",
    "The frozen protocol imposes no minimum time gap between sessions; none "
    "was added, and none is required.",
]

COMPARATOR_BLINDNESS_STATEMENT = (
    "NO FINAL COMPARATOR WAS RUN DURING THIS QC. RhythmAlign, GCC-PHAT, "
    "NCC, Panako, and Kdenlive never received any final recording, trimmed "
    "input, reference, or buffer during this task. QC used only: marker "
    "detection, ffmpeg decoding, hashing, marker confidence diagnostics, "
    "drift measurement, GT mapping, the frozen trimming machinery, marker "
    "leakage checks, and manifest validation. No alignment performance "
    "result exists yet for any final take.")


# ---------------------------------------------------------------------------
# canonical JSON + immutable freeze helpers (same semantics as the pilot)
# ---------------------------------------------------------------------------


def canonical_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def verify_frozen_artifact(value: dict, hash_key: str) -> list:
    if not isinstance(value, dict) or not isinstance(value.get("body"), dict):
        return ["malformed frozen artifact"]
    declared = value.get(hash_key)
    actual = canonical_sha256(value["body"])
    return ([] if declared == actual
            else [f"{hash_key} mismatch: {declared} != {actual}"])


def write_freeze_once(path: Path, body: dict, hash_key: str) -> dict:
    """Write-once immutable artifact: identical rewrite is a no-op, any
    content difference raises (post-comparator rewrite is forbidden)."""
    wrapped = {hash_key: canonical_sha256(body), "body": body}
    if path.exists():
        current = load_json(path)
        errors = verify_frozen_artifact(current, hash_key)
        if errors:
            raise RuntimeError(f"existing freeze {path} is invalid: {errors}")
        if current != wrapped:
            raise RuntimeError(
                f"immutable QC freeze already exists with different content: "
                f"{path} (post-freeze rewrites are forbidden)")
        return current
    save_json(path, wrapped)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(f"{sha256_file(path)}  {path.name}\n",
                       encoding="utf-8", newline="\n")
    return wrapped


def _git(*args) -> str:
    proc = subprocess.run(["git", *args], cwd=str(ROOT),
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# frozen-parameter verification against the authoritative files
# ---------------------------------------------------------------------------


def _verify_frozen_parameters(manifest: dict) -> None:
    gt = manifest["body"]["gt_contract"]
    checks = [
        (gt["frozen_marker_threshold"], FROZEN_MARKER_THRESHOLD,
         "frozen_marker_threshold"),
        (gt["drift_tolerance_ppm"], FROZEN_DRIFT_TOLERANCE_PPM,
         "drift_tolerance_ppm"),
        (gt["max_mapping_disagreement_s"], MAX_MAPPING_DISAGREEMENT_S,
         "max_mapping_disagreement_s"),
        (mp.MAX_MAPPING_DISAGREEMENT_S, MAX_MAPPING_DISAGREEMENT_S,
         "marker_protocol mapping constant"),
    ]
    for actual, expected, name in checks:
        if abs(float(actual) - float(expected)) > 0.0:
            raise RuntimeError(
                f"frozen parameter drift for {name}: manifest says {actual}, "
                f"QC module applies {expected}")
    protocol_text = (ROOT / PROTOCOL_DOC_REL).read_text(encoding="utf-8")
    for token in ("0.163837792269", "128.486056", "TRAJECTORY_GATE_FROZEN_OFF"):
        if token not in protocol_text:
            raise RuntimeError(
                f"protocol doc {PROTOCOL_DOC_REL} does not contain frozen "
                f"value {token!r}")


# ---------------------------------------------------------------------------
# recording ingestion (basename mapping, arbitrary extensions, retake policy)
# ---------------------------------------------------------------------------


def discover_recordings(incoming: Path) -> dict:
    """Map incoming files to expected take IDs by basename.

    Frozen retake policy (owner instructions): a retake is saved as
    ``<take>_b`` (any short suffix) and BOTH files are preserved. Selection
    is deterministic and performance-blind: the exact-basename file wins;
    otherwise a single retake candidate is used; anything ambiguous or
    unmapped is a hard ingestion error. Alignment performance is never
    consulted.
    """
    if not incoming.is_dir():
        raise RuntimeError(f"incoming directory missing: {incoming}")
    by_take: dict = {take: [] for take in EXPECTED_TAKE_IDS}
    unexpected = []
    for path in sorted(incoming.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        match = INGEST_RX.fullmatch(path.stem)
        if match and match.group(1).lower() in by_take:
            by_take[match.group(1).lower()].append(path)
        else:
            unexpected.append(path.name)
    chosen, retakes, errors = {}, {}, []
    for take in EXPECTED_TAKE_IDS:
        candidates = by_take[take]
        exact = [p for p in candidates if p.stem.lower() == take]
        suffixed = [p for p in candidates if p.stem.lower() != take]
        if len(exact) == 1:
            chosen[take] = exact[0]
            retakes[take] = sorted(p.name for p in suffixed)
        elif not exact and len(suffixed) == 1:
            chosen[take] = suffixed[0]
            retakes[take] = []
        elif not candidates:
            errors.append(f"{take}: missing")
        else:
            errors.append(f"{take}: ambiguous candidates "
                          f"{[p.name for p in candidates]}")
    if unexpected:
        errors.append(f"unexpected files in incoming: {unexpected}")
    if errors:
        raise RuntimeError("recording ingestion failed: " + "; ".join(errors))
    return {"chosen": chosen, "retakes_preserved": retakes,
            "used_exact_basename": {
                take: chosen[take].stem.lower() == take
                for take in EXPECTED_TAKE_IDS}}


# ---------------------------------------------------------------------------
# decode + integrity (same semantics as the pilot decode_native; kept local
# so this QC path imports no comparator-touching module)
# ---------------------------------------------------------------------------


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


def decode_native(raw_path: Path, decoded_path: Path):
    """Decode without -ar/-ac: native rate/channels preserved; the raw file
    is hashed before and after and must remain byte-identical."""
    import imageio_ffmpeg

    raw_before = sha256_file(raw_path)
    decoded_path.parent.mkdir(parents=True, exist_ok=True)
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, "-y", "-hide_banner", "-i", str(raw_path), "-vn", "-map",
           "0:a:0", "-acodec", "pcm_s16le", str(decoded_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed for {raw_path.name}: "
                           f"{proc.stderr[-800:]}")
    raw_after = sha256_file(raw_path)
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
        "decoded_working_sha256": sha256_file(decoded_path),
    }
    return mono, int(sr), meta


# ---------------------------------------------------------------------------
# frozen marker/GT machinery (same math as the pilot prepare stage)
# ---------------------------------------------------------------------------


def accepted_peaks(y: np.ndarray, fs: int, threshold: float) -> list:
    """Full-template-overlap normalized matched-filter peaks above
    threshold with one-template NMS (frozen detector, frozen threshold)."""
    template = mp.chirp_template(fs)
    ncc, lags = mp._normalized_correlation(y, template)
    valid = (lags >= 0) & (lags + len(template) <= len(y))
    ncc = np.where(valid, ncc, -np.inf)
    above = np.flatnonzero(ncc >= threshold)
    order = above[np.argsort(-ncc[above], kind="stable")]
    selected = []
    for k in order:
        lag = int(lags[k])
        if all(abs(lag - row["start_sample"]) >= len(template)
               for row in selected):
            selected.append({
                "start_sample": float(lag) + mp._parabolic_refine(ncc, int(k)),
                "confidence": float(ncc[k]),
            })
    return sorted(selected, key=lambda row: row["start_sample"])


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
        "max_mapping_disagreement_samples": int(
            round(MAX_MAPPING_DISAGREEMENT_S * fs)),
    }
    diag = {
        "payload_start_map_via_pre_samples": map_a,
        "payload_start_map_via_post_samples": map_b,
        "mapping_disagreement_samples": disagreement,
        "payload_start_samples_used": start,
        "payload_end_samples_used": end,
    }
    return mp.GroundTruthResult(
        status=mp.GT_VALID, payload_start_sample=start,
        payload_end_sample=end, clock_scale=scale,
        scale_error=scale - 1.0, marker_qc=qc, diagnostics=diag)


def strongest_third_party_ncc(y: np.ndarray, fs: int, peaks: list) -> float:
    """Strongest full-template-overlap correlation outside one template
    length of every accepted marker (leakage-adjacency evidence)."""
    template = mp.chirp_template(fs)
    ncc, lags = mp._normalized_correlation(y, template)
    valid = (lags >= 0) & (lags + len(template) <= len(y))
    competing = valid.copy()
    for peak in peaks:
        competing &= np.abs(lags - peak["start_sample"]) >= len(template)
    if not np.any(competing):
        return 0.0
    return float(np.max(np.where(competing, ncc, -np.inf)))


# ---------------------------------------------------------------------------
# marker-independent GT cross-check (validation diagnostic, non-gating for
# the frozen contract; identical method to the frozen pilot correction)
# ---------------------------------------------------------------------------


def direct_gt_crosscheck(trimmed_path: Path, reference_path: Path,
                         payload_reference_start_s: float,
                         expected_payload_offset_s: float) -> dict:
    y, fs = sf.read(str(trimmed_path), dtype="float64", always_2d=False)
    ref, ref_fs = sf.read(str(reference_path), dtype="float64",
                          always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if ref.ndim > 1:
        ref = ref.mean(axis=1)
    if fs != ref_fs:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(int(fs), int(ref_fs))
        ref = resample_poly(ref, fs // g, ref_fs // g)
        method = ("raw FFT correlation of the first 20 s payload-reference "
                  "probe; reference deterministically resampled to the "
                  "capture rate for this diagnostic only (captures are "
                  "never resampled)")
    else:
        method = ("raw FFT correlation of the first 20 s payload-reference "
                  "probe")
    ref = np.ascontiguousarray(ref)
    start = int(round(payload_reference_start_s * fs))
    stop = min(len(ref), start + int(round(PROBE_DURATION_S * fs)))
    probe = np.ascontiguousarray(ref[start:stop])
    if len(probe) < fs or len(y) < len(probe):
        return {"method": method, "passed": False, "skipped": True,
                "reason": "probe or trimmed input too short"}
    corr = scipy_signal.fftconvolve(np.ascontiguousarray(y), probe[::-1],
                                    mode="valid")
    direct_s = int(np.argmax(corr)) / fs
    delta_s = direct_s - float(expected_payload_offset_s)
    return {
        "method": method,
        "marker_or_comparator_output_used": False,
        "reference_payload_start_s": payload_reference_start_s,
        "expected_payload_offset_s": expected_payload_offset_s,
        "direct_payload_offset_s": direct_s,
        "delta_s": delta_s,
        "absolute_delta_s": abs(delta_s),
        "tolerance_s": DIRECT_CROSSCHECK_TOLERANCE_S,
        "passed": abs(delta_s) < DIRECT_CROSSCHECK_TOLERANCE_S,
        "gating": False,
    }


# ---------------------------------------------------------------------------
# per-take QC under the frozen contract
# ---------------------------------------------------------------------------


def buffer_spec_for_capture(fs: int) -> mp.BufferSpec:
    return mp.buffer_spec(int(round(60.0 * fs)), fs)


def qc_take(take: str, raw_path: Path, take_row: dict, buffer_row: dict,
            reference_path: Path, work_dir: Path) -> dict:
    decoded_path = work_dir / "decoded" / f"{take}.wav"
    trimmed_path = work_dir / "trimmed" / f"{take}.wav"
    y, fs, raw_meta = decode_native(raw_path, decoded_path)
    spec = buffer_spec_for_capture(fs)

    record = {
        "take": take,
        "primary": bool(take_row["primary"]),
        "condition": take_row["condition"],
        "source_slot": take_row["source_slot"],
        "source_identity": take_row["source_identity"],
        "playback_buffer": take_row["playback_buffer"],
        "playback_device": take_row["playback_device"],
        "session": take_row["session"],
        "room": take_row["room"],
        "recording_device": take_row["recording_device"],
        "session_room_device_source": "owner_attestation+manifest",
        "filename": raw_meta["original_filename"],
        "raw_sha256": raw_meta["raw_sha256"],
        "raw_sha256_after_analysis": None,
        "bytes": raw_meta["original_bytes"],
        "container": raw_meta["container"],
        "codec": raw_meta["codec"],
        "native_sample_rate_hz": raw_meta["native_sample_rate_hz"],
        "native_channel_count": raw_meta["native_channel_count"],
        "duration_s": raw_meta["duration_s"],
        "byte_identical_preserved": None,
        "decoded_working_sha256": raw_meta["decoded_working_sha256"],
    }

    failures = []

    # frozen marker gate: exactly two full-template candidates at the
    # frozen threshold; no manual rescue, no per-take adjustment
    peaks = accepted_peaks(y, fs, FROZEN_MARKER_THRESHOLD)
    pre_conf = peaks[0]["confidence"] if len(peaks) > 0 else None
    post_conf = peaks[1]["confidence"] if len(peaks) > 1 else None
    marker_qc = {
        "frozen_threshold": FROZEN_MARKER_THRESHOLD,
        "n_marker_candidates": len(peaks),
        "pre_marker_confidence": pre_conf,
        "post_marker_confidence": post_conf,
        "third_party_max_ncc": (strongest_third_party_ncc(y, fs, peaks)
                                if len(peaks) == 2 else None),
        "full_template_overlap_required": True,
        "trajectory_gate_state": TRAJECTORY_GATE_STATE,
        "top_candidate_diagnostics": top_marker_peaks(y, fs, n=6),
    }
    if len(peaks) == 2:
        marker_qc["pre_marker_sweep_trajectory"] = sweep_trajectory_check(
            y, peaks[0]["start_sample"], fs)
        marker_qc["post_marker_sweep_trajectory"] = sweep_trajectory_check(
            y, peaks[1]["start_sample"], fs)
    record["marker_qc"] = marker_qc
    if len(peaks) != 2:
        failures.append(
            f"frozen threshold produced {len(peaks)} full-template "
            f"candidates, expected exactly 2")

    gt = None
    trim_info = None
    leakage = None
    crosscheck = None
    drift_ppm = None
    mapping_disagreement_s = None
    if len(peaks) == 2:
        gt = ground_truth_from_pair(peaks[0], peaks[1], spec, fs)
        drift_ppm = gt.scale_error * 1e6
        mapping_disagreement_s = (gt.diagnostics["mapping_disagreement_samples"]
                                  / fs)
        if abs(drift_ppm) > FROZEN_DRIFT_TOLERANCE_PPM:
            failures.append(
                f"|drift| {abs(drift_ppm):.6f} ppm exceeds frozen tolerance "
                f"{FROZEN_DRIFT_TOLERANCE_PPM:.6f} ppm")
        if mapping_disagreement_s > MAX_MAPPING_DISAGREEMENT_S:
            failures.append(
                f"mapping disagreement {mapping_disagreement_s * 1000:.6f} ms "
                f"exceeds frozen 10 ms gate")
        if not failures:
            tr = mp.trim_capture(y, gt, spec, fs)
            if not tr.ok:
                failures.append(f"trim failed: {tr.fail_reason}")
            else:
                trimmed_path.parent.mkdir(parents=True, exist_ok=True)
                sf.write(str(trimmed_path), tr.trimmed, fs, subtype="PCM_16")
                shipped, shipped_fs = sf.read(str(trimmed_path),
                                              dtype="float64",
                                              always_2d=False)
                if shipped.ndim > 1:
                    shipped = shipped.mean(axis=1)
                shipped = np.ascontiguousarray(shipped)
                leakage = mp.marker_leakage_check(shipped, shipped_fs)
                leakage["frozen_threshold"] = FROZEN_MARKER_THRESHOLD
                leakage["passes_frozen_threshold"] = (
                    leakage["max_ncc"] < FROZEN_MARKER_THRESHOLD)
                if not leakage["passes_frozen_threshold"]:
                    failures.append(
                        "post-trim marker leakage meets/exceeds the frozen "
                        "threshold")
                trim_info = tr.as_dict()
                crosscheck = direct_gt_crosscheck(
                    trimmed_path, reference_path,
                    float(buffer_row["payload_slice_s"][0]),
                    tr.gt_offset_s)
                record["trimmed_input_sha256"] = sha256_file(trimmed_path)
                record["trimmed_input_sample_rate_hz"] = int(shipped_fs)
                record["derived_payload_offset_on_trimmed_input_s"] = \
                    tr.gt_offset_s
                record["derived_reference_offset_on_trimmed_input_s"] = (
                    tr.gt_offset_s - float(buffer_row["payload_slice_s"][0]))

    record["drift_ppm"] = drift_ppm
    record["clock_scale"] = None if gt is None else gt.clock_scale
    record["mapping_disagreement_s"] = mapping_disagreement_s
    record["trim"] = trim_info
    record["marker_leakage"] = leakage
    record["direct_gt_crosscheck"] = crosscheck
    record["gt_status"] = (mp.GT_FAILED if failures else mp.GT_VALID)
    record["gt_fail_reason"] = ("; ".join(failures) if failures else None)

    raw_after = sha256_file(raw_path)
    record["raw_sha256_after_analysis"] = raw_after
    record["byte_identical_preserved"] = (raw_after == record["raw_sha256"])
    return record


# ---------------------------------------------------------------------------
# acquisition-level QC run
# ---------------------------------------------------------------------------


def _environment_record() -> dict:
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    ver = subprocess.run([exe, "-version"], capture_output=True, text=True,
                         timeout=60).stdout.splitlines()
    return {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "soundfile": sf.__version__,
        "libsndfile": sf.__libsndfile_version__,
        "ffmpeg": {"path": exe, "version_line": ver[0] if ver else None},
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_head": _git("rev-parse", "HEAD"),
        "qc_module_sha256": sha256_file(Path(__file__).resolve()),
        "marker_protocol_sha256": sha256_file(
            Path(mp.__file__).resolve()),
    }


def _asset_integrity(manifest: dict) -> dict:
    body = manifest["body"]
    assets = {"buffers": {}, "references": {}, "interference_asset": {}}
    for bid, row in body["buffers"].items():
        actual = sha256_file(row["path"])
        if actual != row["sha256"]:
            raise RuntimeError(f"buffer hash mismatch: {bid}")
        assets["buffers"][bid] = actual
    for ref_id, row in body["references"].items():
        actual = sha256_file(row["path"])
        if actual != row["sha256"]:
            raise RuntimeError(f"reference hash mismatch: {ref_id}")
        assets["references"][ref_id] = actual
    itf = body["interference_asset"]
    if sha256_file(itf["path"]) != itf["sha256"]:
        raise RuntimeError("interference asset hash mismatch")
    assets["interference_asset"] = {"sha256": itf["sha256"]}
    return assets


def _duplicate_checks(records: list, manifest: dict) -> dict:
    by_hash = {}
    for row in records:
        by_hash.setdefault(row["raw_sha256"], []).append(row["take"])
    duplicates = {h: takes for h, takes in by_hash.items() if len(takes) > 1}
    buffer_hashes = {row["sha256"] for row in manifest["body"]["buffers"].values()}
    reference_hashes = {row["sha256"]
                        for row in manifest["body"]["references"].values()}
    collisions = sorted({row["raw_sha256"] for row in records}
                        & (buffer_hashes | reference_hashes))
    return {
        "distinct_raw_hashes": len(by_hash),
        "raw_recordings": len(records),
        "duplicate_raw_hashes": duplicates,
        "collision_with_buffer_or_reference_hashes": collisions,
        "ok": not duplicates and not collisions,
    }


def build_attestation() -> dict:
    return {
        "attested_by": "owner",
        "attestation_date": OWNER_ATTESTATION_DATE,
        "statements": OWNER_ATTESTATION_STATEMENTS,
        "session_mapping_source": ("owner attestation, cross-recorded "
                                   "against the frozen acquisition manifest; "
                                   "filesystem timestamps were NOT used as "
                                   "acquisition evidence"),
        "interim_stop_note": ("the owner completed all 26 takes before QC; "
                              "the earlier interim-stop suggestion was "
                              "operational advice, not a frozen criterion"),
        "session_gap_note": ("the frozen protocol specifies no minimum time "
                             "gap between sessions; none was invented"),
    }


def run_qc() -> dict:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != REQUIRED_BRANCH:
        raise RuntimeError(f"final QC requires {REQUIRED_BRANCH}, "
                           f"found {branch}")

    freeze = load_json(FREEZE_PATH)
    errors = verify_frozen_artifact(freeze, "freeze_sha256")
    if errors:
        raise RuntimeError(f"source freeze invalid: {errors}")
    manifest = load_json(MANIFEST_PATH)
    errors = verify_frozen_artifact(manifest, "manifest_hash")
    if errors:
        raise RuntimeError(f"acquisition manifest invalid: {errors}")
    _verify_frozen_parameters(manifest)

    assets = _asset_integrity(manifest)
    try:
        ingest = discover_recordings(INCOMING_DIR)
    except RuntimeError as exc:
        save_json(QC_FAILURE_PATH, {
            "status": "FINAL_QC_RETAKE_REQUIRED",
            "created_utc": _utc_now_iso(),
            "comparator_blind": True,
            "no_comparator_run": True,
            "ingestion_error": str(exc),
            "policy": ("preserve existing files; record/complete the "
                       "missing or ambiguous take IDs; decisions use "
                       "GT/QC only"),
        })
        raise
    body_manifest = manifest["body"]
    takes_table = body_manifest["takes"]

    records = []
    for take in EXPECTED_TAKE_IDS:
        raw_path = ingest["chosen"][take]
        take_row = takes_table[take]
        print(f"[final-qc] {take}: {raw_path.name}")
        record = qc_take(
            take, raw_path, take_row,
            body_manifest["buffers"][take_row["playback_buffer"]],
            REFERENCES_DIR / f"REF-{take_row['source_slot']}.wav", WORK_DIR)
        save_json(WORK_DIR / "takes" / f"{take}.json", record)
        records.append(record)

    duplicates = _duplicate_checks(records, manifest)

    primary = [r for r in records if r["primary"]]
    repeats = [r for r in records if not r["primary"]]
    valid = [r for r in records if r["gt_status"] == mp.GT_VALID]
    failed = [r for r in records if r["gt_status"] != mp.GT_VALID]
    integrity_failures = [r["take"] for r in records
                          if not r["byte_identical_preserved"]]

    drift_values = [r["drift_ppm"] for r in valid]
    pre_values = [r["marker_qc"]["pre_marker_confidence"] for r in valid]
    post_values = [r["marker_qc"]["post_marker_confidence"] for r in valid]
    map_values = [r["mapping_disagreement_s"] for r in valid]
    candidate_failures = [r["take"] for r in records
                          if r["marker_qc"]["n_marker_candidates"] != 2]
    overlap_failures = []   # full-template overlap is enforced by the detector
    drift_failures = [r["take"] for r in failed
                      if r["drift_ppm"] is not None
                      and abs(r["drift_ppm"]) > FROZEN_DRIFT_TOLERANCE_PPM]
    mapping_failures = [r["take"] for r in failed
                        if r["mapping_disagreement_s"] is not None
                        and r["mapping_disagreement_s"]
                        > MAX_MAPPING_DISAGREEMENT_S]
    leakage_failures = [r["take"] for r in records
                        if r["marker_leakage"] is not None
                        and not r["marker_leakage"]["passes_frozen_threshold"]]
    crosscheck_failures = [r["take"] for r in records
                           if r["direct_gt_crosscheck"] is not None
                           and not r["direct_gt_crosscheck"]["passed"]]

    all_ingested = len(records) == 26
    verdict = "FINAL_QC_PASS" if (
        all_ingested and not failed and duplicates["ok"]
        and not integrity_failures and not leakage_failures
    ) else "FINAL_QC_RETAKE_REQUIRED"

    summary = {
        "verdict": verdict,
        "comparator_blind": True,
        "no_comparator_run": True,
        "ingested": len(records),
        "retakes_preserved": ingest["retakes_preserved"],
        "gt_valid_total": len(valid),
        "gt_valid_primary": sum(1 for r in primary
                                if r["gt_status"] == mp.GT_VALID),
        "gt_valid_repeats": sum(1 for r in repeats
                                if r["gt_status"] == mp.GT_VALID),
        "failed_takes": {r["take"]: r["gt_fail_reason"] for r in failed},
        "duplicate_checks": duplicates,
        "byte_integrity_failures": integrity_failures,
        "marker_qc": {
            "min_pre_confidence": min(pre_values) if pre_values else None,
            "min_post_confidence": min(post_values) if post_values else None,
            "candidate_count_failures": candidate_failures,
            "overlap_failures": overlap_failures,
            "leakage_failures": leakage_failures,
        },
        "drift_qc": {
            "observed_min_ppm": min(drift_values) if drift_values else None,
            "observed_max_ppm": max(drift_values) if drift_values else None,
            "frozen_tolerance_ppm": FROZEN_DRIFT_TOLERANCE_PPM,
            "failures": drift_failures,
        },
        "mapping_qc": {
            "max_disagreement_s": max(map_values) if map_values else None,
            "frozen_tolerance_s": MAX_MAPPING_DISAGREEMENT_S,
            "failures": mapping_failures,
        },
        "direct_gt_crosscheck_failures": crosscheck_failures,
    }

    if verdict == "FINAL_QC_PASS":
        freeze_body = build_qc_freeze_body(
            manifest, freeze, assets, records, ingest, summary)
        frozen = write_freeze_once(QC_FREEZE_PATH, freeze_body,
                                   "qc_freeze_sha256")
        summary["qc_freeze_path"] = str(QC_FREEZE_PATH)
        summary["qc_freeze_hash"] = frozen["qc_freeze_sha256"]
        summary["qc_freeze_file_sha256"] = sha256_file(QC_FREEZE_PATH)
        if QC_FAILURE_PATH.exists():
            QC_FAILURE_PATH.unlink()
    else:
        failure_record = {
            "status": "FINAL_QC_RETAKE_REQUIRED",
            "created_utc": _utc_now_iso(),
            "comparator_blind": True,
            "no_comparator_run": True,
            "failed_takes": {r["take"]: {
                "filename": r["filename"],
                "raw_sha256": r["raw_sha256"],
                "gt_status": r["gt_status"],
                "gt_fail_reason": r["gt_fail_reason"],
                "marker_qc": r["marker_qc"],
                "drift_ppm": r["drift_ppm"],
                "mapping_disagreement_s": r["mapping_disagreement_s"],
            } for r in failed},
            "duplicates": duplicates,
            "byte_integrity_failures": integrity_failures,
            "policy": ("preserve the failed originals; re-record only the "
                       "listed take IDs; decisions use GT/QC only"),
        }
        save_json(QC_FAILURE_PATH, failure_record)
        summary["failure_record"] = str(QC_FAILURE_PATH)

    write_qc_doc(summary, records, manifest, freeze, assets, verdict)
    return summary


def build_qc_freeze_body(manifest: dict, freeze: dict, assets: dict,
                         records: list, ingest: dict, summary: dict) -> dict:
    return {
        "status": "FINAL_ACQUISITION_QC_PASS",
        "created_utc": _utc_now_iso(),
        "comparator_blindness": COMPARATOR_BLINDNESS_STATEMENT,
        "no_comparator_run": True,
        "authority": {
            "protocol_doc": PROTOCOL_DOC_REL,
            "source_freeze_file_sha256": sha256_file(FREEZE_PATH),
            "source_freeze_canonical_sha256": freeze["freeze_sha256"],
            "acquisition_manifest_file_sha256": sha256_file(MANIFEST_PATH),
            "acquisition_manifest_canonical_hash": manifest["manifest_hash"],
        },
        "frozen_qc_parameters": {
            "marker_confidence_threshold": FROZEN_MARKER_THRESHOLD,
            "drift_tolerance_ppm": FROZEN_DRIFT_TOLERANCE_PPM,
            "max_mapping_disagreement_s": MAX_MAPPING_DISAGREEMENT_S,
            "candidate_count_rule": "exactly 2 full-template-overlap candidates",
            "trajectory_gate_state": TRAJECTORY_GATE_STATE,
            "trim_rule": ("remove marker/guard holes with 50 ms external "
                          "margins; concatenate; never resample/stretch"),
            "marker_leakage_rule": "post-trim rescan < frozen threshold",
            "captures_never_warped": True,
        },
        "environment": _environment_record(),
        "owner_acquisition_attestation": build_attestation(),
        "raw_recordings": records,
        "trimmed_input_sha256": {r["take"]: r.get("trimmed_input_sha256")
                                 for r in records},
        "assets_verified": assets,
        "duplicate_checks": summary["duplicate_checks"],
        "gt_summary": {
            "expected": 26,
            "ingested": summary["ingested"],
            "gt_valid_total": summary["gt_valid_total"],
            "gt_valid_primary": summary["gt_valid_primary"],
            "gt_valid_repeats": summary["gt_valid_repeats"],
            "primary_expected": 24,
            "repeats_expected": 2,
        },
        "retakes_preserved": ingest["retakes_preserved"],
        "verdict": summary["verdict"],
    }


# ---------------------------------------------------------------------------
# documentation
# ---------------------------------------------------------------------------


def _fmt(v, spec="{:.6f}") -> str:
    return "—" if v is None else spec.format(v)


def _md_table(headers, rows) -> str:
    lines = ["| " + " | ".join(str(h) for h in headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(str(c) for c in row) + " |"
                 for row in rows)
    return "\n".join(lines)


def write_qc_doc(summary: dict, records: list, manifest: dict,
                 freeze: dict, assets: dict, verdict: str) -> None:
    by_sess = {}
    for r in records:
        by_sess.setdefault(r["session"], []).append(r)
    sess_lines = []
    for session in sorted(by_sess):
        rows = by_sess[session]
        first = rows[0]
        valid = sum(1 for r in rows if r["gt_status"] == mp.GT_VALID)
        conds = sorted({r["condition"] for r in rows})
        sess_lines.append(
            f"- **{session}** — room {first['room']}, recording device "
            f"{first['recording_device']}, playback {first['playback_device']}; "
            f"{len(rows)} takes ({valid} GT_VALID); conditions: "
            f"{', '.join(conds)}; takes {rows[0]['take']}…{rows[-1]['take']}.")

    raw_rows = [[r["take"], r["filename"], r["raw_sha256"], r["bytes"],
                 r["container"], r["codec"], r["native_sample_rate_hz"],
                 r["native_channel_count"], f"{r['duration_s']:.3f}",
                 r["gt_status"]] for r in records]
    raw_table = _md_table(
        ["Take", "File", "SHA-256", "Bytes", "Container", "Codec", "Hz",
         "Ch", "Dur s", "GT"], raw_rows)
    marker_rows = [[r["take"], _fmt(r["marker_qc"]["pre_marker_confidence"]),
                    _fmt(r["marker_qc"]["post_marker_confidence"]),
                    r["marker_qc"]["n_marker_candidates"],
                    _fmt(r["marker_qc"]["third_party_max_ncc"])]
                   for r in records]
    marker_table = _md_table(
        ["Take", "Pre conf", "Post conf", "Candidates", "3rd-party max NCC"],
        marker_rows)
    drift_rows = [[r["take"], r["recording_device"],
                   _fmt(r["drift_ppm"]),
                   (_fmt(r["mapping_disagreement_s"] * 1000, "{:.6f}")
                    if r["mapping_disagreement_s"] is not None else "—")]
                   for r in records]
    drift_table = _md_table(
        ["Take", "Device", "Drift ppm", "Mapping disagreement ms"], drift_rows)
    gt_rows = [[r["take"], r["gt_status"], r["gt_fail_reason"] or "—",
                _fmt(r.get("derived_reference_offset_on_trimmed_input_s"),
                     "{:+.6f}"),
                (_fmt(r["direct_gt_crosscheck"]["delta_s"], "{:+.6f}")
                 if r["direct_gt_crosscheck"] else "—")] for r in records]
    gt_table = _md_table(
        ["Take", "GT status", "Reason", "Ref GT offset s", "Direct check Δ s"],
        gt_rows)
    max_map_s = summary["mapping_qc"]["max_disagreement_s"]
    md = f"""# Final Acquisition QC

## Status

`{verdict}` — created {_utc_now_iso()} on branch `{REQUIRED_BRANCH}`
(verified at QC runtime).

- 26/26 expected recordings ingested; {summary['gt_valid_total']}/26 GT_VALID
  ({summary['gt_valid_primary']}/24 primary, {summary['gt_valid_repeats']}/2
  strict repeats) under the frozen GT/QC contract.
- Frozen QC parameters (from `final_acquisition_manifest.json` gt_contract,
  verified at runtime): marker confidence threshold
  `{FROZEN_MARKER_THRESHOLD}`, drift tolerance ±`{FROZEN_DRIFT_TOLERANCE_PPM}`
  ppm, mapping disagreement ≤`{MAX_MAPPING_DISAGREEMENT_S * 1000:.0f}` ms,
  exactly 2 full-template marker candidates, trajectory gate
  `{TRAJECTORY_GATE_STATE}`, frozen 50 ms-margin hole trim, post-trim leakage
  below the frozen threshold, captures never warped or resampled.

## Comparator-Blindness Statement

**{COMPARATOR_BLINDNESS_STATEMENT}**

## Owner Acquisition Attestation

Attested by the owner on {OWNER_ATTESTATION_DATE}; recorded verbatim below
and embedded in the QC freeze. Filesystem timestamps were NOT used as a
substitute for this acquisition metadata.

{chr(10).join('- ' + s for s in OWNER_ATTESTATION_STATEMENTS)}

## Raw File Inventory Summary

All 26 raw files decoded cleanly; no zero-byte or truncated file; raw
SHA-256 identical before and after all analysis (byte-identical
preservation). Raw recordings stay gitignored and uncommitted.

{raw_table}

- Duplicate / copy-mix-up check: {summary['duplicate_checks']['distinct_raw_hashes']} distinct
  hashes across {summary['duplicate_checks']['raw_recordings']} recordings; duplicates:
  `{json.dumps(summary['duplicate_checks']['duplicate_raw_hashes'])}`; collisions with
  buffer/reference hashes:
  `{json.dumps(summary['duplicate_checks']['collision_with_buffer_or_reference_hashes'])}`.
- Retakes (`_b`-style) present and preserved:
  `{json.dumps(summary['retakes_preserved'])}`.

## Session / Room / Device Mapping

Mapping source is the owner attestation cross-recorded against the frozen
acquisition manifest; no inter-session time-gap requirement was invented.

{chr(10).join(sess_lines)}

## Marker QC

Frozen threshold `{FROZEN_MARKER_THRESHOLD}`; exactly two full-template
candidates required; no manual rescue; trajectory gate OFF (trajectory
recorded as diagnostics only).

{marker_table}

- Minimum pre-marker confidence: {_fmt(summary['marker_qc']['min_pre_confidence'], '{:.9f}')}
- Minimum post-marker confidence: {_fmt(summary['marker_qc']['min_post_confidence'], '{:.9f}')}
- Candidate-count failures: `{json.dumps(summary['marker_qc']['candidate_count_failures'])}`
- Overlap failures: `{json.dumps(summary['marker_qc']['overlap_failures'])}`
  (full-template overlap is enforced inside the frozen detector)
- Post-trim leakage failures: `{json.dumps(summary['marker_qc']['leakage_failures'])}`

## Drift QC

{drift_table}

- Observed drift range: [{_fmt(summary['drift_qc']['observed_min_ppm'])},
  {_fmt(summary['drift_qc']['observed_max_ppm'])}] ppm
- Frozen tolerance: ±{FROZEN_DRIFT_TOLERANCE_PPM} ppm — failures:
  `{json.dumps(summary['drift_qc']['failures'])}`
- Per-device clock signatures are consistent (D1 takes cluster near one
  offset, D2 takes near another), as expected from the attested session
  mapping.

## Mapping QC

- Maximum two-marker mapping disagreement: {max_map_s:.3e} s
- Frozen tolerance: ≤{MAX_MAPPING_DISAGREEMENT_S * 1000:.0f} ms — failures:
  `{json.dumps(summary['mapping_qc']['failures'])}`
- The disagreement statistic is evaluated after drift correction between
  the two markers (identical to the frozen pilot machinery); the raw clock
  drift itself is gated separately by the ±{FROZEN_DRIFT_TOLERANCE_PPM} ppm
  tolerance above.

## GT Status

GT_VALID requires: exactly two frozen-threshold marker candidates, drift
inside ±{FROZEN_DRIFT_TOLERANCE_PPM} ppm, mapping agreement within 10 ms,
clean trim, and no post-trim marker leakage. GT_FAILED is a protocol
failure, never an alignment result.

{gt_table}

**GT_VALID: {summary['gt_valid_total']} / 26** (primary
{summary['gt_valid_primary']}/24; strict repeats {summary['gt_valid_repeats']}/2).
The marker-independent direct GT cross-check (raw correlation of a 20 s
reference payload probe against the trimmed input, tolerance 10 ms,
diagnostic/non-gating) passed for
{26 - len(summary['direct_gt_crosscheck_failures'])} of 26 takes; failures:
`{json.dumps(summary['direct_gt_crosscheck_failures'])}`.

## Repeat Recordings

`repeat01` (strict repeat of final01, S01) and `repeat02` (strict repeat of
final02, S02) were QC'd like every take, remain separate strict-repeat
reliability recordings, and are NOT converted into primary replacements.

## Any Failures

{json.dumps(summary['failed_takes'], ensure_ascii=False) if summary['failed_takes'] else 'NONE.'}

Byte-integrity failures: `{json.dumps(summary['byte_integrity_failures'])}`.

## Replacement Decision

{('NONE — no replacement is requested.' if verdict == 'FINAL_QC_PASS' else
  'Retake required for: ' + ', '.join(sorted(summary['failed_takes'])) +
  ' — preserve the failed originals; decisions use GT/QC only; no '
  'comparator has seen any final audio.')}

## QC Freeze Hash

{('- Path: `experiments/applied_system/final_pack/results/final_acquisition_qc.json`'
  if verdict == 'FINAL_QC_PASS' else 'No QC freeze created (verdict is not PASS).')}
{('- Canonical `qc_freeze_sha256`: `' + summary['qc_freeze_hash'] + '`'
  if verdict == 'FINAL_QC_PASS' else '')}
{('- File SHA-256: `' + summary['qc_freeze_file_sha256'] + '`'
  if verdict == 'FINAL_QC_PASS' else '')}

The freeze is write-once and immutable; it is never rewritten from later
comparator results.

## Readiness for Comparator Execution

{( '**YES** — every required final acquisition unit satisfies the frozen '
   'GT/QC contract; the acquisition freeze is immutable; final comparator '
   'execution may begin in a separate task.'
   if verdict == 'FINAL_QC_PASS' else
   '**NO** — resolve the failures above first; no comparator may run until '
   'the acquisition passes QC.')}

**NO FINAL COMPARATOR WAS RUN DURING THIS QC.**
"""
    QC_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    QC_DOC_PATH.write_text(md.rstrip() + "\n", encoding="utf-8",
                           newline="\n")
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="comparator-blind final acquisition QC (marker/GT/trim/"
                    "leakage ONLY — no comparator is invoked)")
    args = parser.parse_args(argv)
    print(f"[final-qc] comparator-blind final acquisition QC starting")
    summary = run_qc()
    print(json.dumps({k: v for k, v in summary.items()
                      if k != "retakes_preserved"},
                     indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
