"""Optional acoustic loop test — owner-operated, NO participants.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Purpose: exercise the marker protocol against ONE or TWO real
playback->capture round trips performed by the repository owner (see
OWNER_SHAKEDOWN_INSTRUCTIONS.md). This is purely a machinery check: does the
marker GT survive real speakers, a real room, and a real recording device?

The owner plays the rendered playback buffer (results/shakedown/media/
playback_buffer_song_a.wav) through any loudspeaker, records it with any
device, and drops the recording into results/shakedown/acoustic/. This
script then runs the SAME detection -> GT -> QC -> trim pipeline used for
the digital cases, at the recording's own native rate, and writes an
acoustic_loop_report.json. It never contacts anyone and never starts
recruitment.

Usage:
    python -m experiments.applied_system.acoustic_loop \
        --capture path/to/recording.wav [--label take1]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from . import manifest as manifest_mod
from . import marker_protocol as mp
from . import synth_payload
from .runners import common

APPLIED_DIR = Path(__file__).resolve().parent
DEFAULT_OUTDIR = APPLIED_DIR / "results" / "shakedown"


def _load_capture(capture_path: Path, outdir: Path, label: str):
    """Load a capture at its NATIVE rate. soundfile (libsndfile) handles
    WAV; compressed phone recordings (m4a/AAC etc.) are decoded via the
    bundled ffmpeg with NO sample-rate or channel forcing — resampling
    would destroy the clock-drift signal the two-marker QC measures.
    Returns (y_mono, native_sr, decode_info_dict)."""
    import tempfile

    try:
        y, sr = sf.read(str(capture_path), dtype="float64", always_2d=False)
        return (np.ascontiguousarray(y.mean(axis=1) if y.ndim > 1 else y),
                int(sr),
                {"decoded_via_ffmpeg": False})
    except Exception as exc:
        decode_error = f"{type(exc).__name__}: {exc}"
    import imageio_ffmpeg
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    decoded_path = outdir / "acoustic" / f"{label}_decoded.wav"
    decoded_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_bin, "-y", "-i", str(capture_path),
           "-vn", "-acodec", "pcm_s16le", str(decoded_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg decode of {capture_path.name} failed: "
            f"{proc.stderr[-800:]}")
    y, sr = sf.read(str(decoded_path), dtype="float64", always_2d=False)
    return (np.ascontiguousarray(y.mean(axis=1) if y.ndim > 1 else y),
            int(sr),
            {"decoded_via_ffmpeg": True,
             "decode_error_of_soundfile": decode_error,
             "decoded_wav": f"acoustic/{decoded_path.name}",
             "decoded_wav_sha256": common.sha256_file(decoded_path),
             "decode_command": cmd})


def sweep_trajectory_check(y: np.ndarray, start_sample: float, fs: int) -> dict:
    """Independent, physics-based corroboration for one detected marker:
    does the audio at start_sample contain a RISING ~1->9 kHz linear sweep
    matching the known template's time-frequency structure? Unlike the
    matched filter (sample-level phase correlation, sensitive to reverberation
    and codec artifacts) this checks the sweep's coarse frequency trajectory
    and is reported for every marker as diagnostic evidence. It does NOT
    gate GT; the reported confidence gate and two-marker QC remain the
    decision rules."""
    from scipy.signal import stft

    lo, hi = mp.CHIRP_F_LO_HZ, mp.CHIRP_F_HI_HZ
    a = max(0, int(start_sample - 0.03 * fs))
    b = min(len(y), int(start_sample + mp.CHIRP_DURATION_S * fs + 0.05 * fs))
    seg = y[a:b]
    if len(seg) < 2048:
        return {"corroborated": False, "reason": "segment too short"}
    f, t, Z = stft(seg, fs, nperseg=1024, noverlap=768)
    band = (f >= lo - 300) & (f <= hi + 300)
    mag = np.abs(Z[band])
    freqs = f[band]
    frame_energy = mag.sum(axis=0)
    if frame_energy.max() <= 0:
        return {"corroborated": False, "reason": "no energy in chirp band"}
    keep = frame_energy > 0.1 * frame_energy.max()
    if keep.sum() < 5:
        return {"corroborated": False, "reason": "insufficient frames"}
    dom = freqs[np.argmax(mag[:, keep], axis=0)]
    tt = t[keep]
    slope, _intercept = np.polyfit(tt, dom, 1)
    pred = slope * tt
    ss_res = float(np.sum((dom - pred - np.mean(dom) + np.mean(dom)) ** 2))
    ss_tot = float(np.sum((dom - np.mean(dom)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    template_slope = (hi - lo) / mp.CHIRP_DURATION_S
    ratio = float(slope / template_slope)
    # PROVISIONAL diagnostic thresholds (machinery, non-gating): on
    # reverberant/AAC audio the dominant-bin trajectory carries bin-
    # quantization noise, so r^2 tops out around 0.84 for a visually clean
    # monotone ramp (first real capture, 2026-09-14); slope ratio is the
    # discriminating statistic. Re-visit only from multi-device pilot data.
    corroborated = bool(slope > 0 and 0.80 <= ratio <= 1.20 and r2 >= 0.75)
    return {"corroborated": corroborated,
            "slope_hz_per_s": float(slope),
            "template_slope_hz_per_s": float(template_slope),
            "slope_ratio": ratio,
            "r_squared": float(r2),
            "n_frames": int(keep.sum())}


def top_marker_peaks(y: np.ndarray, fs: int, n: int = 5) -> list:
    """Strongest full-overlap matched-filter peaks regardless of the
    confidence gate (diagnostic evidence trail; also records what a failed
    gate rejected)."""
    template = mp.chirp_template(fs)
    ncc, lags = mp._normalized_correlation(y, template)
    if len(ncc) == 0:
        return []
    valid = (lags >= 0) & (lags + len(template) <= len(y))
    ncc = np.where(valid, ncc, -np.inf)
    order = np.argsort(-ncc, kind="stable")
    taken = []
    peaks = []
    for k in order:
        if len(peaks) >= n or not np.isfinite(ncc[k]):
            break
        lag = lags[k]
        if all(abs(lag - t0) >= len(template) for t0 in taken):
            taken.append(float(lag))
            peaks.append({
                "lag_samples": int(lag),
                "time_s": float(lag) / fs,
                "ncc": float(ncc[k]),
                "above_gate": bool(ncc[k] >= mp.MIN_MARKER_CONFIDENCE),
                "sweep_trajectory": sweep_trajectory_check(y, float(lag), fs),
            })
    return peaks


def run_acoustic_capture(capture_path: Path, outdir: Path,
                         label: str, payload_duration_s: float = 62.0) -> dict:
    """Full pipeline on one real capture. Deterministic given the file."""
    y, native_sr, decode_info = _load_capture(capture_path, outdir, label)
    y = np.ascontiguousarray(y)

    # Analyze at the capture's own clock: marker detection and the QC scale
    # statistic operate on native samples (a device recording at a nominal
    # 48 kHz that actually runs at 47990 Hz must still be measurable).
    song = synth_payload.render_song_a(duration_s=payload_duration_s)
    spec = mp.buffer_spec(len(song), fs=native_sr)
    report = {
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "warning": common.SHAKEDOWN_WARNING,
        "label": label,
        "capture_file": str(capture_path),
        "capture_sha256": common.sha256_file(capture_path),
        "native_fs": int(native_sr),
        "capture_samples": int(len(y)),
        "capture_duration_s": len(y) / native_sr,
        **decode_info,
    }

    report["top_marker_peaks_diagnostic"] = {
        "min_marker_confidence_used": mp.MIN_MARKER_CONFIDENCE,
        "peaks": top_marker_peaks(y, native_sr),
    }
    gt = mp.derive_ground_truth(y, spec, fs=native_sr)
    report["ground_truth"] = gt.qc_dict()
    if gt.status != mp.GT_VALID:
        report["verdict"] = "GT_FAILED (machinery/protocol failure — a " \
                            "valid shakedown finding, never rescued)"
        common.save_json(outdir / "acoustic" / f"{label}_report.json", report)
        return report

    for key, det in (("pre_marker_sweep_trajectory",
                      gt.marker_qc["pre_marker"]),
                     ("post_marker_sweep_trajectory",
                      gt.marker_qc["post_marker"])):
        report[key] = sweep_trajectory_check(y, det["start_sample"],
                                             native_sr)

    tr = mp.trim_capture(y, gt, spec, fs=native_sr)
    leak = mp.marker_leakage_check(tr.trimmed, fs=native_sr)
    report["trim"] = tr.as_dict()
    report["marker_leakage_check"] = leak
    trimmed_path = outdir / "acoustic" / f"{label}_trimmed.wav"
    mp_fs = native_sr
    sf.write(str(trimmed_path), tr.trimmed, mp_fs, subtype="PCM_16")
    report["trimmed_sha256"] = common.sha256_file(trimmed_path)
    report["gt_offset_s_relative_to_trimmed_input"] = tr.gt_offset_s

    # Round-trip placement check WITHOUT any alignment system: correlate the
    # trimmed input's opening payload against the known clean song to see
    # whether the machinery's GT matches a naive direct measurement.
    from scipy import signal as sps
    probe_len = min(len(song), int(20 * native_sr))
    probe = song[:probe_len]
    corr = sps.fftconvolve(tr.trimmed, probe[::-1], mode="valid")
    direct_start = int(np.argmax(corr))
    report["direct_correlation_payload_start_in_trimmed"] = direct_start
    report["direct_vs_marker_gt_delta_s"] = (
        direct_start / native_sr - tr.gt_offset_s)
    report["verdict"] = (
        "GT_OK" if abs(report["direct_vs_marker_gt_delta_s"]) < 0.010
        else "GT_DIRECT_DISAGREEMENT (investigate before any pilot)")

    common.save_json(outdir / "acoustic" / f"{label}_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="owner-operated acoustic loop test "
                    "(SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE)")
    parser.add_argument("--capture", required=True,
                        help="path to the owner's recording of the playback "
                             "buffer")
    parser.add_argument("--label", default="take1")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    args = parser.parse_args(argv)
    report = run_acoustic_capture(Path(args.capture), Path(args.outdir),
                                  args.label)
    print(f"verdict: {report['verdict']}")
    print(f"report: {Path(args.outdir) / 'acoustic' / (args.label + '_report.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
