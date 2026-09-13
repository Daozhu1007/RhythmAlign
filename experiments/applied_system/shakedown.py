"""Benchmark machinery shakedown orchestrator.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Stages (each independent, strictly ordered; run/s_score/reproduce never
edit the frozen manifest):

  prepare   render payloads + captures, derive GT, trim, verify no marker
            leakage, build and FREEZE the manifest
  run       verify frozen manifest + input hashes, execute every eligible
            runner once per eligible case (single pass), save raw records
  score     deterministic scoring of records against the frozen manifest
  reproduce re-run all runners and scoring from the same frozen manifest and
            compare (volatile runtime fields excluded) — shakedown question 9

Engineering case set (tiny, machinery-exercising, NOT a dataset): the nine
cases in :func:`standard_case_definitions` map one-to-one onto the shakedown
spec section 13 minimum.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from . import manifest as manifest_mod
from . import marker_protocol as mp
from . import scoring as scoring_mod
from . import synth_payload
from .manifest import (STRATUM_EXACT_GT, STRATUM_GT_FAILED, STRATUM_NO_MATCH)
from .runners import common
from .runners import gcc_phat_runner, ncc_runner, panako_runner
from .runners import rhythmalign_runner

APPLIED_DIR = Path(__file__).resolve().parent
DEFAULT_OUTDIR = APPLIED_DIR / "results" / "shakedown"

FS = mp.FS

RUNNERS = {
    "rhythmalign_v1_2_0": rhythmalign_runner.run_case,
    "gcc_phat_argmax_v1": gcc_phat_runner.run_case,
    "ncc_argmax_v1": ncc_runner.run_case,
    "panako_fingerprint": panako_runner.run_case,
}


def panako_probe_record() -> dict:
    """Live Panako status probe (written to panako_status.json by run_stage
    and refreshable standalone). The frozen shakedown round shipped with
    STATUS_PENDING; the integration contract now lives in
    docs/research/applied_system/PANAKO_INTEGRATION.md."""
    ok, env = panako_runner.panako_environment()
    return {
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "status": (panako_runner.STATUS_READY if ok
                   else panako_runner.STATUS_PENDING),
        "panako_available": ok,
        "environment": env,
        "comparator_contract":
            "docs/research/applied_system/PANAKO_INTEGRATION.md",
    }


AMBIENT_NOISE_STD = 3e-4  # low room-tone floor for lead/tail ambience


# ---------------------------------------------------------------------------
# engineering case definitions (frozen set for THIS shakedown round)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseDef:
    case_id: str
    condition: str
    payload_song: str
    reference_song: str
    lead_s: float = 2.5
    tail_s: float = 2.0
    amplitude_scale: float | None = None
    noise_snr_db: float | None = None
    clip_level: float | None = None
    drift: tuple | None = None            # (up, down) rational for resample_poly
    truncate_at_capture_s: float | None = None
    trim_start_into_payload_s: float | None = None
    expected_stratum: str = STRATUM_EXACT_GT


def standard_case_definitions() -> list:
    """The nine shakedown cases (spec section 13 minimum, one case each)."""
    return [
        CaseDef(case_id="pos_zero_lead", condition="ordinary_zero_lead_in",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a",
                lead_s=0.0, tail_s=1.5),
        CaseDef(case_id="pos_ordinary", condition="ordinary",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a"),
        CaseDef(case_id="pos_negative_offset",
                condition="capture_start_mid_song_trim_equivalent",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a",
                trim_start_into_payload_s=6.0),
        CaseDef(case_id="pos_noise", condition="added_noise_10db",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a",
                noise_snr_db=10.0),
        CaseDef(case_id="pos_quiet", condition="low_amplitude_0x35",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a",
                amplitude_scale=0.35),
        CaseDef(case_id="pos_clock_drift", condition="clock_drift_250ppm",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a",
                drift=(4001, 4000)),
        CaseDef(case_id="wrong_reference", condition="wrong_reference_no_match",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_b",
                expected_stratum=STRATUM_NO_MATCH),
        CaseDef(case_id="gt_truncated", condition="truncated_capture",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a",
                truncate_at_capture_s=24.0,
                expected_stratum=STRATUM_GT_FAILED),
        CaseDef(case_id="gt_drift_excess",
                condition="clock_drift_1000ppm_excessive",
                payload_song="shakedown_song_a",
                reference_song="shakedown_song_a",
                drift=(1001, 1000),
                expected_stratum=STRATUM_GT_FAILED),
    ]


def noise_seed_for(case_id: str) -> int:
    """Deterministic per-case RNG seed derived from the case id (documented
    in the reproducibility environment record)."""
    return int.from_bytes(
        hashlib.sha256(case_id.encode("utf-8")).digest()[:4], "little")


# ---------------------------------------------------------------------------
# capture construction (digital degradations, deterministic order)
# ---------------------------------------------------------------------------


def build_capture(case: CaseDef, buffer: np.ndarray, spec: mp.BufferSpec,
                  fs: int = FS) -> np.ndarray:
    rng = np.random.default_rng(noise_seed_for(case.case_id))
    parts = []
    if case.lead_s > 0:
        parts.append(rng.normal(0.0, AMBIENT_NOISE_STD,
                                int(round(case.lead_s * fs))))
    parts.append(buffer)
    if case.tail_s > 0:
        parts.append(rng.normal(0.0, AMBIENT_NOISE_STD,
                                int(round(case.tail_s * fs))))
    cap = parts[0] if len(parts) == 1 else np.concatenate(parts)
    # Degradation order is deterministic and documented: clock drift,
    # amplitude, added noise, clipping, truncation.
    if case.drift is not None:
        up, down = case.drift
        cap = resample_poly(cap, up, down)
    if case.amplitude_scale is not None:
        cap = cap * case.amplitude_scale
    if case.noise_snr_db is not None:
        payload_rms = float(np.sqrt(np.mean(
            buffer[spec.payload_start_sample:spec.payload_end_sample] ** 2)))
        noise_std = payload_rms * 10.0 ** (-case.noise_snr_db / 20.0)
        cap = cap + rng.normal(0.0, noise_std, len(cap))
    if case.clip_level is not None:
        cap = np.clip(cap, -case.clip_level, case.clip_level)
    if case.truncate_at_capture_s is not None:
        cap = cap[:int(round(case.truncate_at_capture_s * fs))]
    return cap


# ---------------------------------------------------------------------------
# audio I/O
# ---------------------------------------------------------------------------


def write_wav_int16(path: Path, y: np.ndarray, fs: int = FS):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.asarray(y, dtype=np.float64), fs, subtype="PCM_16")


def load_audio(path, fs: int = FS) -> np.ndarray:
    """Benchmark-input loader for the DSP runners: mono float64 at the
    protocol rate; every system consumes the same file bytes."""
    y, sr = sf.read(str(path), dtype="float64", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != fs:
        raise ValueError(f"{path}: expected fs={fs}, got {sr}")
    return np.ascontiguousarray(y)


# ---------------------------------------------------------------------------
# stage: prepare
# ---------------------------------------------------------------------------


def protocol_constants(payload_duration_s: float) -> dict:
    return {
        "fs": mp.FS,
        "chirp_duration_s": mp.CHIRP_DURATION_S,
        "chirp_freq_hz": [mp.CHIRP_F_LO_HZ, mp.CHIRP_F_HI_HZ],
        "guard_duration_s": mp.GUARD_DURATION_S,
        "pre_trim_margin_s": mp.PRE_TRIM_MARGIN_S,
        "post_trim_margin_s": mp.POST_TRIM_MARGIN_S,
        "min_marker_confidence": mp.MIN_MARKER_CONFIDENCE,
        "marker_rule": "exactly two accepted marker candidates required",
        "provisional_max_clock_scale_error":
            mp.PROVISIONAL_MAX_CLOCK_SCALE_ERROR,
        "max_mapping_disagreement_s": mp.MAX_MAPPING_DISAGREEMENT_S,
        "payload_duration_s": payload_duration_s,
        "wav_format": "PCM_16 mono (protocol rate)",
    }


def prepare_stage(outdir: Path, case_defs: list,
                  payload_duration_s: float = 62.0) -> dict:
    """Render everything, derive GT, trim, verify leakage, freeze manifest."""
    media = outdir / "media"
    songs = {}
    for song_id, generator in synth_payload.SONG_GENERATORS.items():
        if song_id == "shakedown_song_b" and not any(
                c.reference_song == "shakedown_song_b" for c in case_defs):
            # Only render what this shakedown set consumes.
            continue
        y = generator(duration_s=payload_duration_s)
        path = media / f"{song_id}.wav"
        write_wav_int16(path, y, FS)
        songs[song_id] = path
    song_hashes = {sid: common.sha256_file(p) for sid, p in songs.items()}
    song_seeds = {
        "shakedown_song_a": synth_payload.SONG_A_SEED,
        "shakedown_song_b": synth_payload.SONG_B_SEED,
    }

    cases = []
    for case in case_defs:
        payload_y, _ = sf.read(str(songs[case.payload_song]),
                               dtype="float64")
        buffer = mp.render_marker_buffer(payload_y, FS)
        spec = mp.buffer_spec(len(payload_y), FS)
        capture = build_capture(case, buffer, spec, FS)
        capture_path = outdir / "captures" / f"{case.case_id}.wav"
        write_wav_int16(capture_path, capture, FS)

        # Analyze the SHIPPED file (int16-quantized), not the in-memory
        # floats: ground truth must come from the bytes that exist.
        y_cap, _ = sf.read(str(capture_path), dtype="float64")
        gt = mp.derive_ground_truth(y_cap, spec, FS)

        marker_qc = gt.qc_dict()
        provenance = {
            "payload_generator": f"experiments.applied_system."
                                 f"synth_payload.{case.payload_song}",
            "payload_seed": song_seeds[case.payload_song],
            "capture_noise_seed": noise_seed_for(case.case_id),
            "capture_degradations": {
                "lead_s": case.lead_s, "tail_s": case.tail_s,
                "amplitude_scale": case.amplitude_scale,
                "noise_snr_db": case.noise_snr_db,
                "clip_level": case.clip_level,
                "drift_resample_updown": (list(case.drift)
                                          if case.drift else None),
                "truncate_at_capture_s": case.truncate_at_capture_s,
                "trim_start_into_payload_s": case.trim_start_into_payload_s,
            },
            "protocol_module": "experiments.applied_system.marker_protocol",
        }

        if gt.status == mp.GT_FAILED:
            cases.append(manifest_mod.make_case(
                case_id=case.case_id, condition=case.condition,
                source_identity=case.payload_song,
                payload_identity=case.payload_song,
                payload_sha256=song_hashes[case.payload_song],
                capture_path=f"captures/{case.case_id}.wav",
                capture_sha256=common.sha256_file(capture_path),
                reference_path=f"media/{case.reference_song}.wav",
                reference_sha256=song_hashes[case.reference_song],
                gt_stratum=STRATUM_GT_FAILED, gt_offset_s=None,
                expected_label=None, marker_qc=marker_qc,
                provenance=provenance, trimmed_input_path=None,
                trimmed_input_sha256=None,
                comparator_eligibility=[]))
            continue

        trim_start = 0
        if case.trim_start_into_payload_s is not None:
            trim_start = gt.payload_start_sample + int(round(
                case.trim_start_into_payload_s * FS))
        tr = mp.trim_capture(y_cap, gt, spec, FS, trim_start=trim_start)
        if not tr.ok:
            raise RuntimeError(
                f"{case.case_id}: trim failed on valid GT "
                f"({tr.fail_reason}) — machinery bug")
        leak = mp.marker_leakage_check(tr.trimmed, FS)
        if leak["leakage"]:
            raise RuntimeError(
                f"{case.case_id}: marker leakage in trimmed input "
                f"(max_ncc={leak['max_ncc']:.3f}) — machinery bug")
        trimmed_path = outdir / "trimmed" / f"{case.case_id}.wav"
        write_wav_int16(trimmed_path, tr.trimmed, FS)

        marker_qc["trim"] = tr.as_dict()
        marker_qc["marker_leakage_check"] = leak
        provenance["trim"] = tr.as_dict()
        cases.append(manifest_mod.make_case(
            case_id=case.case_id, condition=case.condition,
            source_identity=case.payload_song,
            payload_identity=case.payload_song,
            payload_sha256=song_hashes[case.payload_song],
            capture_path=f"captures/{case.case_id}.wav",
            capture_sha256=common.sha256_file(capture_path),
            reference_path=f"media/{case.reference_song}.wav",
            reference_sha256=song_hashes[case.reference_song],
            gt_stratum=(STRATUM_EXACT_GT
                        if case.expected_stratum == STRATUM_EXACT_GT
                        else case.expected_stratum),
            gt_offset_s=tr.gt_offset_s,
            expected_label=(manifest_mod.LABEL_MATCH
                            if case.expected_stratum == STRATUM_EXACT_GT
                            else manifest_mod.LABEL_NO_MATCH),
            marker_qc=marker_qc, provenance=provenance,
            trimmed_input_path=f"trimmed/{case.case_id}.wav",
            trimmed_input_sha256=common.sha256_file(trimmed_path),
            comparator_eligibility=manifest_mod.default_eligibility(
                case.expected_stratum)))

    body = manifest_mod.build_manifest(
        cases, protocol_constants(payload_duration_s),
        notes={
            "purpose": "benchmark MACHINERY shakedown only",
            "case_set": "shakedown spec section 13 minimum (engineering, "
                        "not a dataset)",
            "offset_convention": ("positive: reference begins gt_offset_s "
                                  "into the trimmed input; negative: capture "
                                  "starts |gt_offset_s| into the reference "
                                  "(frozen v1.2.0 production convention)"),
        })
    frozen = manifest_mod.freeze_manifest(body)
    common.save_json(outdir / "manifest.json", frozen)

    # Playback buffer for the OPTIONAL owner acoustic loop test (spec
    # section 14): the exact digital buffer, rendered as audio.
    if "shakedown_song_a" in songs:
        song_y, _ = sf.read(str(songs["shakedown_song_a"]), dtype="float64")
        write_wav_int16(outdir / "media" / "playback_buffer_song_a.wav",
                        mp.render_marker_buffer(song_y, FS), FS)
    return frozen


# ---------------------------------------------------------------------------
# stage: run
# ---------------------------------------------------------------------------


def resolve_path(base: Path, rel: str) -> Path:
    return base / rel


def run_stage(outdir: Path) -> list:
    """Single-pass execution of every eligible runner on the frozen
    manifest. Never edits the manifest."""
    frozen = common.load_json(outdir / "manifest.json")
    errors = manifest_mod.verify_frozen(frozen)
    if errors:
        raise RuntimeError(f"frozen manifest failed verification: {errors}")
    body = frozen["body"]

    panako_probe = panako_probe_record()
    common.save_json(outdir / "panako_status.json", panako_probe)
    common.save_json(outdir / "environment.json",
                     common.capture_environment())

    records = []
    for case in body["cases"]:
        for system in case["comparator_eligibility"]:
            input_path = resolve_path(outdir, case["trimmed_input_path"])
            reference_path = resolve_path(outdir, case["reference_path"])
            actual_in = common.sha256_file(input_path)
            actual_ref = common.sha256_file(reference_path)
            if actual_in != case["trimmed_input_sha256"] or \
                    actual_ref != case["reference_sha256"]:
                rec = common.RunnerRecord(
                    system=system, case_id=case["case_id"],
                    decision=common.DECISION_ERROR, predicted_offset_s=None,
                    native_scores={"error": "input/reference hash mismatch "
                                            "against frozen manifest"},
                    output_semantics=common.SEMANTICS_UNKNOWN)
            else:
                rec = RUNNERS[system](case, input_path, reference_path, FS,
                                      load_audio)
            rec.input_sha256 = {"trimmed_input": actual_in,
                                "reference": actual_ref}
            common.save_json(
                outdir / "records" / f"{system}__{case['case_id']}.json",
                rec.as_dict())
            records.append(rec.as_dict())
            print(f"  ran {system} on {case['case_id']}: {rec.decision} "
                  f"(runtime {rec.runtime_s:.2f}s)")
    return records


# ---------------------------------------------------------------------------
# stage: score
# ---------------------------------------------------------------------------


def score_stage(outdir: Path, records: list | None = None) -> dict:
    frozen = common.load_json(outdir / "manifest.json")
    errors = manifest_mod.verify_frozen(frozen)
    if errors:
        raise RuntimeError(f"frozen manifest failed verification: {errors}")
    if records is None:
        records = []
        for path in sorted((outdir / "records").glob("*.json")):
            records.append(common.load_json(path))
    scores = scoring_mod.score_run(frozen["body"], records)
    scores["manifest_hash"] = frozen["manifest_hash"]
    common.save_json(outdir / "scores.json", scores)
    return scores


def print_summary(scores: dict):
    print("\n  scoring summary (tolerance "
          f"{scores['tolerance_s']:.3f} s):")
    for system, slot in sorted(scores["summary"].items(),
                               key=lambda kv: str(kv[0])):
        counts = ", ".join(f"{k}={v}" for k, v in sorted(slot.items()))
        print(f"    {system}: {counts}")
    if scores["protocol_failures"]:
        print(f"    protocol failures: {len(scores['protocol_failures'])}")
        for row in scores["protocol_failures"]:
            print(f"      {row['case_id']}: {row['outcome']}")


# ---------------------------------------------------------------------------
# stage: reproduce
# ---------------------------------------------------------------------------


def reproduce_stage(outdir: Path) -> dict:
    """Re-run all runners and scoring from the same frozen manifest and
    compare to the first run, volatile fields excluded."""
    first_records = []
    for path in sorted((outdir / "records").glob("*.json")):
        first_records.append(common.load_json(path))
    rerun = run_stage(outdir)

    first_cmp = {f"{r['system']}__{r['case_id']}":
                 scoring_mod.comparable_record(r) for r in first_records}
    second_cmp = {f"{r['system']}__{r['case_id']}":
                  scoring_mod.comparable_record(r) for r in rerun}
    differences = []
    for key in sorted(set(first_cmp) | set(second_cmp)):
        if key not in second_cmp:
            differences.append(f"{key}: missing in rerun")
        elif key not in first_cmp:
            differences.append(f"{key}: missing in first run")
        elif first_cmp[key] != second_cmp[key]:
            differences.append(f"{key}: record differs beyond runtime fields")

    first_scores = scoring_mod.score_run(
        common.load_json(outdir / "manifest.json")["body"], first_records)
    second_scores = scoring_mod.score_run(
        common.load_json(outdir / "manifest.json")["body"], rerun)
    scores_equal = (first_scores["summary"] == second_scores["summary"]
                    and first_scores["per_case"] == second_scores["per_case"])
    if not scores_equal:
        differences.append("scoring outputs differ between runs")

    check = {
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "warning": common.SHAKEDOWN_WARNING,
        "reproduced": not differences,
        "differences": differences,
        "records_compared": len(first_cmp),
    }
    common.save_json(outdir / "reproduction_check.json", check)
    return check


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run_shakedown(outdir: Path = DEFAULT_OUTDIR,
                  case_defs: list | None = None,
                  payload_duration_s: float = 62.0,
                  stages=("prepare", "run", "score", "reproduce")) -> dict:
    outdir = Path(outdir)
    case_defs = case_defs if case_defs is not None \
        else standard_case_definitions()
    results = {}
    for stage in stages:
        print(f"[shakedown] stage: {stage}")
        if stage == "prepare":
            frozen = prepare_stage(outdir, case_defs, payload_duration_s)
            print(f"  manifest frozen: {frozen['manifest_hash'][:16]}… "
                  f"({len(frozen['body']['cases'])} cases)")
            results["manifest_hash"] = frozen["manifest_hash"]
        elif stage == "run":
            results["records"] = run_stage(outdir)
        elif stage == "score":
            results["scores"] = score_stage(outdir)
            print_summary(results["scores"])
        elif stage == "reproduce":
            results["reproduction"] = reproduce_stage(outdir)
            print(f"  reproduced: {results['reproduction']['reproduced']}")
        else:
            raise ValueError(f"unknown stage: {stage}")
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="applied-system benchmark MACHINERY shakedown "
                    "(SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE)")
    parser.add_argument("--stage", default="all",
                        choices=["all", "prepare", "run", "score",
                                 "reproduce"])
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    args = parser.parse_args(argv)
    stages = {"all": ("prepare", "run", "score", "reproduce")}.get(
        args.stage, (args.stage,))
    run_shakedown(Path(args.outdir), stages=stages)


if __name__ == "__main__":
    main()
