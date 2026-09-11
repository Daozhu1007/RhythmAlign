"""RA-1.2A low-SNR alignment experiment harness.

Isolated engineering experiments only. This module imports production
alignment helpers from auto_sync.py so the "current algorithm" numbers are
faithful, but it never changes production behavior.

Offset sign convention (matches auto_sync.mix_and_export):
    offset > 0 : music is delayed by `offset` seconds (adelay)
    offset < 0 : the first |offset| seconds of music are trimmed (atrim)
    i.e. at video time t the music plays at music time (t - offset).
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
from scipy import signal
import librosa

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from auto_sync import (  # noqa: E402
    _align_chroma,
    _align_hybrid,
    _align_onset,
    _correlation_z_score,
    _independent_peak_ratio,
)

PEAK_SEPARATION_SECONDS = 1.5


# ---------------------------------------------------------------------------
# correlation axis helpers
# ---------------------------------------------------------------------------

def lag_to_offset(lag_frames, hop_length, sr):
    """Convert a raw correlation lag into the production offset convention.

    In every production correlation the *music* feature is in1 and the
    *video* feature is in2, so lag = (music frame aligned with video frame 0).
    Positive offset means the music must be delayed.
    """
    return -(lag_frames * hop_length) / sr


def _frame_count(y, hop_length):
    """librosa frame count for centered features (chroma_cens / onset)."""
    return 1 + len(y) // hop_length


def top_candidates(correlation, n_video_frames, hop_length, sr, n=6,
                   min_separation_frames=None):
    """Top-N distinct candidate offsets from a full correlation curve.

    Returns a list of dicts with raw lag value, offset in seconds and the
    correlation value. The global argmax is always included (find_peaks can
    miss edge maxima), deduplicated by index.
    """
    if min_separation_frames is None:
        min_separation_frames = max(
            1, int(PEAK_SEPARATION_SECONDS * sr / hop_length)
        )

    corr = np.asarray(correlation)
    peak_idx, _ = signal.find_peaks(corr, distance=min_separation_frames)
    best_idx = int(np.argmax(corr))
    if best_idx not in set(peak_idx.tolist()):
        peak_idx = np.append(peak_idx, best_idx)

    order = np.argsort(corr[peak_idx])[::-1][:n]
    candidates = []
    for i in order:
        idx = int(peak_idx[i])
        lag = idx - (n_video_frames - 1)
        candidates.append({
            "offset_s": round(lag_to_offset(lag, hop_length, sr), 4),
            "corr": float(corr[idx]),
        })
    return candidates


def peak_ratio(correlation, hop_length, sr):
    min_sep = max(1, int(PEAK_SEPARATION_SECONDS * sr / hop_length))
    return _independent_peak_ratio(np.asarray(correlation), min_sep)


def _method_result(method, offset, z, correlation, n_video_frames, hop, sr,
                   runtime, extra=None):
    cands = top_candidates(correlation, n_video_frames, hop, sr)
    margin = None
    if len(cands) >= 2 and cands[1]["corr"] > 0:
        margin = round(cands[0]["corr"] / cands[1]["corr"], 3)
    result = {
        "method": method,
        "offset_s": round(float(offset), 4),
        "z_score": round(float(z), 3),
        "independent_peak_ratio": (
            None if not np.isfinite(peak_ratio(correlation, hop, sr))
            else round(float(peak_ratio(correlation, hop, sr)), 3)
        ),
        "peak_margin": margin,
        "top_candidates": cands,
        "runtime_s": round(float(runtime), 2),
        "params": {"sr": sr, "hop_length": hop},
    }
    if extra:
        result.update(extra)
    return result


# ---------------------------------------------------------------------------
# Method A/B: current production algorithms (called unmodified)
# ---------------------------------------------------------------------------

def hybrid_method(y_video, y_music, sr=22050, hop_length=512, top_n=6):
    t0 = time.perf_counter()
    offset, z, corr = _align_hybrid(y_video, y_music, sr, hop_length)
    runtime = time.perf_counter() - t0
    n_video = _frame_count(y_video, hop_length)
    assert len(corr) == (1 + len(y_music) // hop_length) + n_video - 1
    return _method_result(
        "hybrid (production)", offset, z, corr, n_video, hop_length, sr, runtime,
        extra={"top_candidates": top_candidates(corr, n_video, hop_length, sr, top_n)},
    )


def onset_method(y_video, y_music, sr=22050, hop_length=512, top_n=6):
    t0 = time.perf_counter()
    offset, z, corr = _align_onset(y_video, y_music, sr, hop_length)
    runtime = time.perf_counter() - t0
    n_video = _frame_count(y_video, hop_length)
    assert len(corr) == (1 + len(y_music) // hop_length) + n_video - 1
    return _method_result(
        "onset (production)", offset, z, corr, n_video, hop_length, sr, runtime,
        extra={"top_candidates": top_candidates(corr, n_video, hop_length, sr, top_n)},
    )


def chroma_method(y_video, y_music, sr=22050, hop_length=512, top_n=6):
    t0 = time.perf_counter()
    offset, z, corr = _align_chroma(y_video, y_music, sr, hop_length)
    runtime = time.perf_counter() - t0
    n_video = _frame_count(y_video, hop_length)
    return _method_result(
        "chroma (production)", offset, z, corr, n_video, hop_length, sr, runtime,
        extra={"top_candidates": top_candidates(corr, n_video, hop_length, sr, top_n)},
    )


# ---------------------------------------------------------------------------
# Method C: PCEN mel + temporal delta + per-band correlation
# ---------------------------------------------------------------------------

def pcen_delta_features(y, sr, hop_length, n_mels=96, fmin=30.0, fmax=None,
                        n_fft=None, positive_only=True, per_band="zscore",
                        pcen_gain=0.98, pcen_bias=2.0, pcen_power=0.5,
                        pcen_time_constant=0.400):
    """PCEN mel spectrogram followed by a temporal first difference.

    per_band: None | "mean" (subtract row mean) | "zscore" (row mean/std)
    """
    if n_fft is None:
        n_fft = 4 * hop_length if hop_length <= 512 else 2048
    S = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=n_fft, hop_length=hop_length,
        n_mels=n_mels, fmin=fmin, fmax=fmax, power=2.0,
    )
    P = librosa.pcen(
        S, sr=sr, hop_length=hop_length, gain=pcen_gain, bias=pcen_bias,
        power=pcen_power, time_constant=pcen_time_constant,
    )
    D = np.diff(P, axis=1, prepend=P[:, :1])
    if positive_only:
        D = np.maximum(D, 0.0)
    if per_band == "mean":
        D = D - np.mean(D, axis=1, keepdims=True)
    elif per_band == "zscore":
        std = np.std(D, axis=1, keepdims=True)
        D = (D - np.mean(D, axis=1, keepdims=True)) / (std + 1e-12)
    return D


def _correlate_rows(feat_video, feat_music):
    corr = np.zeros(feat_video.shape[1] + feat_music.shape[1] - 1)
    for i in range(feat_video.shape[0]):
        corr += signal.correlate(feat_music[i], feat_video[i], mode="full",
                                 method="fft")
    return corr


def pcen_method(y_video, y_music, sr=22050, hop_length=512, top_n=6, **kwargs):
    t0 = time.perf_counter()
    feat_video = pcen_delta_features(y_video, sr, hop_length, **kwargs)
    feat_music = pcen_delta_features(y_music, sr, hop_length, **kwargs)
    corr = _correlate_rows(feat_video, feat_music)
    z = _correlation_z_score(corr)
    lag = int(np.argmax(corr)) - (feat_video.shape[1] - 1)
    offset = lag_to_offset(lag, hop_length, sr)
    runtime = time.perf_counter() - t0
    return _method_result(
        "pcen_delta", offset, z, corr, feat_video.shape[1], hop_length, sr,
        runtime,
        extra={
            "top_candidates": top_candidates(corr, feat_video.shape[1],
                                             hop_length, sr, top_n),
            "params": {
                "sr": sr, "hop_length": hop_length,
                **{k: v for k, v in sorted(kwargs.items())},
            },
        },
    )


# ---------------------------------------------------------------------------
# Method C': PCEN + HPSS variant (best real-case discriminators in the sweep)
# ---------------------------------------------------------------------------

def pcen_hpss_features(y, sr, hop_length, n_mels=96, fmin=30.0, fmax=4000.0,
                       hpss_kernel=31, positive_only=True, per_band="zscore"):
    """Harmonic-separated PCEN mel delta: suppresses percussive taps before
    the PCEN/delta pipeline (median-filter HPSS on the mel spectrogram)."""
    S = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=min(2048, 4 * hop_length), hop_length=hop_length,
        n_mels=n_mels, fmin=fmin, fmax=fmax, power=2.0,
    )
    H, _ = librosa.decompose.hpss(S, kernel_size=hpss_kernel)
    P = librosa.pcen(H, sr=sr, hop_length=hop_length)
    D = np.diff(P, axis=1, prepend=P[:, :1])
    if positive_only:
        D = np.maximum(D, 0.0)
    if per_band == "mean":
        D = D - np.mean(D, axis=1, keepdims=True)
    elif per_band == "zscore":
        std = np.std(D, axis=1, keepdims=True)
        D = (D - np.mean(D, axis=1, keepdims=True)) / (std + 1e-12)
    return D


def pcen_hpss_method(y_video, y_music, sr=22050, hop_length=512, top_n=6,
                     **kwargs):
    t0 = time.perf_counter()
    feat_video = pcen_hpss_features(y_video, sr, hop_length, **kwargs)
    feat_music = pcen_hpss_features(y_music, sr, hop_length, **kwargs)
    corr = _correlate_rows(feat_video, feat_music)
    z = _correlation_z_score(corr)
    lag = int(np.argmax(corr)) - (feat_video.shape[1] - 1)
    offset = lag_to_offset(lag, hop_length, sr)
    runtime = time.perf_counter() - t0
    return _method_result(
        "pcen_hpss", offset, z, corr, feat_video.shape[1], hop_length, sr,
        runtime,
        extra={
            "top_candidates": top_candidates(corr, feat_video.shape[1],
                                             hop_length, sr, top_n),
            "params": {
                "sr": sr, "hop_length": hop_length,
                **{k: v for k, v in sorted(kwargs.items())},
            },
        },
    )


# ---------------------------------------------------------------------------
# spectral-flux comparison variant (cheap log-mel flux envelope)
# ---------------------------------------------------------------------------

def logmel_flux_method(y_video, y_music, sr=22050, hop_length=512, top_n=6,
                       n_mels=96, fmin=30.0, fmax=None):
    t0 = time.perf_counter()
    kw = dict(n_fft=min(2048, 4 * hop_length), hop_length=hop_length,
              n_mels=n_mels, fmin=fmin, fmax=fmax, power=2.0)

    def flux(y):
        S = librosa.feature.melspectrogram(y=y, sr=sr, **kw)
        Sdb = librosa.power_to_db(S, ref=np.max)
        D = np.diff(Sdb, axis=1, prepend=Sdb[:, :1])
        return np.sum(np.maximum(D, 0.0), axis=0)

    fv, fm = flux(y_video), flux(y_music)
    corr = signal.correlate(fm - np.mean(fm), fv - np.mean(fv), mode="full",
                            method="fft")
    z = _correlation_z_score(corr)
    lag = int(np.argmax(corr)) - (len(fv) - 1)
    offset = lag_to_offset(lag, hop_length, sr)
    runtime = time.perf_counter() - t0
    return _method_result(
        "logmel_flux", offset, z, corr, len(fv), hop_length, sr, runtime,
        extra={"top_candidates": top_candidates(corr, len(fv), hop_length, sr,
                                                top_n)},
    )


# ---------------------------------------------------------------------------
# reliability decisions
# ---------------------------------------------------------------------------

PRODUCTION_CONFIDENCE_THRESHOLD = 2.0
PRODUCTION_FALLBACK_PEAK_RATIO = 1.05


def production_reliability(result):
    """Reproduce the production accept/reject decision per method."""
    z = result["z_score"]
    ratio = result["independent_peak_ratio"]
    ratio = float("inf") if ratio is None else ratio
    if result["method"].startswith("hybrid"):
        return z >= PRODUCTION_CONFIDENCE_THRESHOLD
    if result["method"].startswith("onset"):
        return (z >= PRODUCTION_CONFIDENCE_THRESHOLD
                and ratio >= PRODUCTION_FALLBACK_PEAK_RATIO)
    return None


def default_reliability(result, z_threshold=2.0, ratio_threshold=1.05):
    z = result["z_score"]
    ratio = result["independent_peak_ratio"]
    ratio = float("inf") if ratio is None else ratio
    return z >= z_threshold and ratio >= ratio_threshold


def summarize(results, gt_offset=None, tolerance=0.15):
    """Render a markdown table row set for a list of method results."""
    lines = []
    header = ("| method | offset (s) | Z | peak ratio | reliable | runtime (s) |"
              + (" |err| vs GT (s) |" if gt_offset is not None else ""))
    lines.append(header)
    lines.append("|---|---|---|---|---|---|" +
                 ("---|" if gt_offset is not None else ""))
    for r in results:
        rel = r.get("reliable")
        rel_s = "-" if rel is None else ("yes" if rel else "NO")
        row = (f"| {r['method']} | {r['offset_s']:+.4f} | {r['z_score']:.2f} | "
               f"{r['independent_peak_ratio']} | {rel_s} | {r['runtime_s']:.2f} |")
        if gt_offset is not None:
            row += f" {abs(r['offset_s'] - gt_offset):.3f} |"
        lines.append(row)
    return "\n".join(lines)
