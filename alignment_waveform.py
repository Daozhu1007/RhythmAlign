"""Candidate-level waveform corroboration for Alignment Engine v2.

GCC-PHAT verifies an already nominated spectral placement. It never
nominates a replacement offset or acts as a stand-alone song matcher.
"""
from __future__ import annotations

import numpy as np
from scipy import fft, signal


def phat_window(video, music, rate, min_overlap_fraction=0.8):
    """Linear GCC-PHAT; a positive lag means video follows reference.

    Search all lags retaining >=80% of the window. Z and dominance
    describe the local curve and are not correctness probabilities.
    """
    v = np.asarray(video, dtype=np.float64)
    m = np.asarray(music, dtype=np.float64)
    if v.size < 2 or m.size < 2:
        return {"available": False, "failure": "empty_audio"}
    v = v - v.mean()
    m = m - m.mean()
    if not np.isfinite(v).all() or not np.isfinite(m).all():
        return {"available": False, "failure": "nonfinite_audio"}
    if np.linalg.norm(v) <= 1e-10 or np.linalg.norm(m) <= 1e-10:
        return {"available": False, "failure": "silent_audio"}
    nfft = fft.next_fast_len(len(v) + len(m) - 1)
    cross = fft.rfft(v, nfft) * np.conj(fft.rfft(m, nfft))
    circular = fft.irfft(cross / np.maximum(np.abs(cross), 1e-12), nfft)
    corr = np.r_[circular[-(len(m) - 1):], circular[:len(v)]]
    lags = np.arange(-(len(m) - 1), len(v))
    overlap = np.minimum(len(v), len(m) + lags) - np.maximum(0, lags)
    valid = overlap >= min(len(v), len(m)) * min_overlap_fraction
    curve, axis = corr[valid], lags[valid]
    if not curve.size:
        return {"available": False, "failure": "empty_search"}
    i = int(np.argmax(curve))
    outside = np.abs(axis - axis[i]) >= round(1.5 * rate)
    second = float(np.max(curve[outside])) if outside.any() else 0.0
    peak = float(curve[i])
    std = float(np.std(curve))
    return {"available": True, "lag_s": float(axis[i] / rate),
            "z": float((peak - curve.mean()) / std) if std else 0.0,
            "margin": peak / max(second, 1e-12), "peak": peak,
            "runner_up": second, "search_min_s": float(axis[0] / rate),
            "search_max_s": float(axis[-1] / rate)}


def measure(video, music, sr, offset, window_s=25.0, windows=4):
    """Four disjoint windows span the actual reference/video intersection.

    At most 25 seconds per window, at least 8 seconds. Downsampling by
    three matches the historical waveform comparator's analysis rate.
    """
    rate = sr / 3
    v = signal.resample_poly(np.asarray(video, dtype=np.float64), 1, 3)
    m = signal.resample_poly(np.asarray(music, dtype=np.float64), 1, 3)
    shift = int(round(offset * rate))
    a, b = max(0, -shift), min(len(m), len(v) - shift)
    width = min(round(window_s * rate), (b - a) // windows)
    if width < round(8.0 * rate):
        return {"available": False, "failure": "short_overlap", "windows": []}
    starts = np.linspace(a, b - width, windows).round().astype(int)
    rows = []
    for start in starts:
        row = phat_window(v[start + shift:start + shift + width],
                          m[start:start + width], rate)
        rows.append({"reference_start_s": float(start / rate),
                     "duration_s": float(width / rate),
                     "offset_s": (float(shift / rate + row["lag_s"])
                                  if row["available"] else None), **row})
    return {"available": all(r["available"] for r in rows), "windows": rows}


def verify_candidate(video, music, sr, offset, policy):
    result = measure(video, music, sr, offset)
    failed = []
    for i, row in enumerate(result["windows"]):
        checks = []
        if not row["available"]:
            checks.append(row["failure"])
        else:
            if abs(row["offset_s"] - offset) > policy.waveform_offset_tol_s:
                checks.append("offset_disagreement")
            if row["z"] < policy.waveform_z_floor:
                checks.append("weak_peak")
            if row["margin"] < policy.waveform_margin_floor:
                checks.append("nonunique_peak")
        row["failed_checks"] = checks
        failed.extend(f"window_{i + 1}:{c}" for c in checks)
    if not result["available"]:
        failed.append(result.get("failure", "unavailable_window"))
    offsets = [r["offset_s"] for r in result["windows"] if r["available"]]
    spread = max(offsets) - min(offsets) if offsets else None
    if spread is not None and spread > policy.waveform_max_spread_s:
        failed.append("inconsistent_windows")
    result.update({"failed_checks": failed, "passed": not failed,
                   "offset_spread_s": spread,
                   "thresholds": {"z_floor": policy.waveform_z_floor,
                                  "margin_floor": policy.waveform_margin_floor,
                                  "offset_tolerance_s": policy.waveform_offset_tol_s,
                                  "max_spread_s": policy.waveform_max_spread_s}})
    return result
