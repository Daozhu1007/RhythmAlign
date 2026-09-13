"""Waveform normalized cross-correlation argmax runner — always-output DSP
baseline.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

Semantics (frozen for this round): sample-level normalized cross-correlation
with PER-LAG overlap-energy normalization (so partial overlaps — negative
offsets, truncated captures — are handled honestly instead of being
silently favored), argmax lag. ALWAYS_OUTPUT: no native refusal and NO
confidence threshold invented in this round. Offset convention identical to
the production engine: positive lag = reference begins lag seconds into the
capture.
"""
from __future__ import annotations

import time

import numpy as np
from scipy import signal

from .common import (DECISION_ACCEPT, DECISION_ERROR, SEMANTICS_ALWAYS_OUTPUT,
                     RunnerRecord)

SYSTEM_ID = "ncc_argmax_v1"


def ncc_curve(y_rec: np.ndarray, y_ref: np.ndarray):
    """Full normalized cross-correlation with per-lag overlap normalization.

    ncc[m] = sum_i y_rec[m+i]*y_ref[i] / (||overlap_rec|| * ||overlap_ref||)
    for all integer lags m (including negative), computed via FFT.
    Returns (ncc_values, lags) with lags from -(len(ref)-1) to len(rec)-1.
    """
    n_r, n_t = len(y_rec), len(y_ref)
    corr = signal.fftconvolve(y_rec, y_ref[::-1], mode="full")
    lags = np.arange(-(n_t - 1), n_r)
    rec_pad = np.concatenate(([0.0], np.cumsum(y_rec * y_rec)))
    ref_pad = np.concatenate(([0.0], np.cumsum(y_ref * y_ref)))
    lo_r = np.clip(np.maximum(lags, 0), 0, n_r)
    hi_r = np.clip(np.minimum(lags + n_t, n_r), 0, n_r)
    lo_t = np.clip(np.maximum(-lags, 0), 0, n_t)
    hi_t = np.clip(np.minimum(n_r - lags, n_t), 0, n_t)
    e_rec = rec_pad[hi_r] - rec_pad[lo_r]
    e_ref = ref_pad[hi_t] - ref_pad[lo_t]
    e_prod = e_rec * e_ref
    # Relative floor: near-silent windows must yield zero correlation, not
    # FFT-roundoff dust divided by a tiny denominator (the detector hit
    # exactly this pathology; the runner uses the same normalization).
    floor = (max(float(np.max(e_rec)), 1e-30)
             * max(float(np.max(e_ref)), 1e-30) * 1e-12)
    ncc = np.where(e_prod > floor,
                   corr / np.sqrt(np.maximum(e_prod, 1e-30)),
                   0.0)
    return ncc, lags


def ncc_offset(y_rec: np.ndarray, y_ref: np.ndarray):
    """Returns (offset_samples:int, native:dict)."""
    t0 = time.perf_counter()
    ncc, lags = ncc_curve(y_rec, y_ref)
    k = int(np.argmax(ncc))
    native = {
        "ncc_peak_value": float(ncc[k]),
        "lag_samples": int(lags[k]),
        "implementation": SYSTEM_ID,
        "runtime_curve_s": time.perf_counter() - t0,
    }
    return int(lags[k]), native


def run_case(case: dict, input_path, reference_path, fs: int,
             load_audio) -> RunnerRecord:
    try:
        t0 = time.perf_counter()
        y_in = load_audio(input_path, fs)
        y_ref = load_audio(reference_path, fs)
        offset_samples, native = ncc_offset(y_in, y_ref)
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
