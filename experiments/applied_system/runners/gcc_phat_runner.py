"""GCC-PHAT argmax runner — canonical always-output DSP baseline.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

Semantics (frozen for this round): GENERALIZED CROSS-CORRELATION with phase
transform, linear (zero-padded) correlation, argmax lag. ALWAYS_OUTPUT: no
native refusal, and NO confidence threshold is invented here (shakedown
spec section 11). Offset convention: lag m means the reference begins m
seconds into the capture, identical to the production engine convention.
"""
from __future__ import annotations

import time

import numpy as np
from scipy import fft as scipy_fft

from .common import (DECISION_ACCEPT, DECISION_ERROR, SEMANTICS_ALWAYS_OUTPUT,
                     RunnerRecord)

SYSTEM_ID = "gcc_phat_argmax_v1"


def gcc_phat_curve(y_rec: np.ndarray, y_ref: np.ndarray) -> np.ndarray:
    """PHAT-weighted cross-correlation, linear via zero padding.

    Returns the inverse FFT of the phase-normalized cross-spectrum
    (cross-spectrum divided by its magnitude). Circular index k unwraps to
    signed lag m such that y_rec[n] ~= y_ref[n - m]; the reference thus
    begins m samples into the capture.
    """
    n_total = scipy_fft.next_fast_len(len(y_rec) + len(y_ref))
    spec_rec = scipy_fft.rfft(y_rec, n_total)
    spec_ref = scipy_fft.rfft(y_ref, n_total)
    cross = spec_rec * np.conj(spec_ref)
    denom = np.abs(cross)
    eps = max(float(denom.max()), 1e-30) * 1e-12
    phase = cross / np.maximum(denom, eps)
    return scipy_fft.irfft(phase, n_total)


def curve_argmax_offset_samples(curve: np.ndarray) -> int:
    """Unwrap circular FFT correlation index to signed lag in samples."""
    n = len(curve)
    k = int(np.argmax(curve))
    return k if k < (n + 1) // 2 else k - n


def gcc_phat_offset(y_rec: np.ndarray, y_ref: np.ndarray):
    """Returns (offset_samples:int, native:dict)."""
    t0 = time.perf_counter()
    curve = gcc_phat_curve(y_rec, y_ref)
    k = curve_argmax_offset_samples(curve)
    native = {
        "gcc_peak_value": float(curve[k if k >= 0 else len(curve) + k]),
        "lag_samples": int(k),
        "implementation": SYSTEM_ID,
        "runtime_curve_s": time.perf_counter() - t0,
    }
    return int(k), native


def run_case(case: dict, input_path, reference_path, fs: int,
             load_audio) -> RunnerRecord:
    """File-based entry used by the shakedown harness. load_audio(path, fs)
    must return float64 mono."""
    try:
        t0 = time.perf_counter()
        y_in = load_audio(input_path, fs)
        y_ref = load_audio(reference_path, fs)
        offset_samples, native = gcc_phat_offset(y_in, y_ref)
        runtime = time.perf_counter() - t0
        return RunnerRecord(
            system=SYSTEM_ID, case_id=case["case_id"],
            decision=DECISION_ACCEPT, predicted_offset_s=offset_samples / fs,
            native_scores=native, runtime_s=runtime,
            output_semantics=SEMANTICS_ALWAYS_OUTPUT,
            notes={"always_output": True, "no_threshold_invented": True})
    except Exception as exc:  # noqa: BLE001 — runner errors must be recorded
        return RunnerRecord(
            system=SYSTEM_ID, case_id=case["case_id"],
            decision=DECISION_ERROR, predicted_offset_s=None,
            native_scores={"error": f"{type(exc).__name__}: {exc}"},
            runtime_s=0.0, output_semantics=SEMANTICS_ALWAYS_OUTPUT,
            notes={})
