"""GCC-PHAT argmax runner, lagfix version 2 — corrected FFT-index unwrap.

COMPARATOR-INTEGRITY-1 correction of ``gcc_phat_argmax_v1``. The v1 module is
preserved verbatim as defective-implementation evidence; this module changes
ONLY the circular-index-to-lag unwrapping, derived from linear-correlation
lag geometry and validated on synthetic fixtures (see
``docs/research/applied_system/GCC_PHAT_LAG_AUDIT.md`` and
``tests/test_gcc_phat_lagfix.py``).

Offset convention (identical to v1 and to the production engine, and to the
frozen ground truth): lag m means ``y_rec[n] ~= y_ref[n - m]`` — the reference
begins m samples into the capture; a positive offset delays the reference, a
negative offset trims its beginning. ALWAYS_OUTPUT semantics are unchanged:
no native refusal, no invented confidence threshold.
"""
from __future__ import annotations

import time

import numpy as np

from .common import (DECISION_ACCEPT, DECISION_ERROR,
                     SEMANTICS_ALWAYS_OUTPUT, RunnerRecord)
from .gcc_phat_runner import gcc_phat_curve  # byte-identical PHAT curve

SYSTEM_ID = "gcc_phat_argmax_v2_lagfix"


def curve_argmax_offset_samples_lagfix(curve: np.ndarray,
                                       n_ref_samples: int) -> int:
    """Unwrap circular FFT correlation index to signed lag, lagfix rule.

    The curve was computed with both signals zero-padded to n >= Lx + Ly
    samples (Lx = query, Ly = reference), so its linear cross-correlation
    c[m] = sum_n y_rec[n] * y_ref[n - m] occupies exactly:

        indices [0, Lx-1]        -> lags [0, Lx-1]           (positive)
        indices [Lx, N-Ly]       -> zero-overlap region (c = 0)
        indices [N-Ly+1, N-1]    -> lags [-(Ly-1), -1]       (negative)

    The exact unwrap therefore flips at index N - Ly + 1, which depends on
    BOTH signal lengths — not at the length-independent midpoint ceil(N/2)
    used by v1. v1 is correct only when N >= 2*Ly (e.g. equal lengths);
    when the query is shorter than the reference, negative lags in
    [-(Ly-1), ceil(N/2)-1-N] sit below the midpoint and v1 reports them as
    positive lags larger by exactly N (the FFT length).
    """
    n = len(curve)
    j = int(np.argmax(curve))
    return j - n if j >= n - n_ref_samples + 1 else j


def gcc_phat_offset(y_rec: np.ndarray, y_ref: np.ndarray):
    """Returns (offset_samples:int, native:dict). Same curve as v1; only the
    index->lag unwrap differs (see curve_argmax_offset_samples_lagfix)."""
    t0 = time.perf_counter()
    curve = gcc_phat_curve(y_rec, y_ref)
    j = int(np.argmax(curve))
    k = curve_argmax_offset_samples_lagfix(curve, len(y_ref))
    native = {
        "gcc_peak_value": float(curve[j]),
        "argmax_index": int(j),
        "fft_length": int(len(curve)),
        "lagfix_wrap_boundary_index": int(len(curve) - len(y_ref) + 1),
        "lag_samples": int(k),
        "implementation": SYSTEM_ID,
        "runtime_curve_s": time.perf_counter() - t0,
    }
    return int(k), native


def run_case(case: dict, input_path, reference_path, fs: int,
             load_audio) -> RunnerRecord:
    """File-based entry with the same record contract as v1."""
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
            notes={"always_output": True, "no_threshold_invented": True,
                   "lagfix": "v2 corrected FFT-index unwrap; curve identical "
                             "to gcc_phat_argmax_v1"})
    except Exception as exc:  # noqa: BLE001 — runner errors must be recorded
        return RunnerRecord(
            system=SYSTEM_ID, case_id=case["case_id"],
            decision=DECISION_ERROR, predicted_offset_s=None,
            native_scores={"error": f"{type(exc).__name__}: {exc}"},
            runtime_s=0.0, output_semantics=SEMANTICS_ALWAYS_OUTPUT,
            notes={})
