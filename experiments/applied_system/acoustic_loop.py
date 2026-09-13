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


def run_acoustic_capture(capture_path: Path, outdir: Path,
                         label: str, payload_duration_s: float = 62.0) -> dict:
    """Full pipeline on one real capture. Deterministic given the file."""
    y, native_sr = sf.read(str(capture_path), dtype="float64",
                           always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
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
        "native_fs": int(native_sr),
        "capture_samples": int(len(y)),
        "capture_sha256": common.sha256_file(capture_path),
    }

    gt = mp.derive_ground_truth(y, spec, fs=native_sr)
    report["ground_truth"] = gt.qc_dict()
    if gt.status != mp.GT_VALID:
        report["verdict"] = "GT_FAILED (machinery/protocol failure — a " \
                            "valid shakedown finding, never rescued)"
        common.save_json(outdir / "acoustic" / f"{label}_report.json", report)
        return report

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
