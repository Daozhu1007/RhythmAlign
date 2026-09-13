"""Marker playback-buffer protocol for the applied-system benchmark
MACHINERY SHAKEDOWN: deterministic buffer generation, marker detection that
is fully independent of RhythmAlign, two-marker ground-truth derivation with
an explicit QC rule, and marker/guard-free trimming.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Protocol structure (one rendered buffer, one playback):

    chirp1 | guard | music payload | guard | chirp2

Both chirps are required. chirp1 alone is NOT sufficient for a valid GT
claim (shakedown question 1/2.1): chirp2 is an independent quality-control
signal for capture completeness, sample-clock drift, unexpected
resampling/time-stretch, marker mis-detection, and dropped/duplicated
sections. If the two markers imply inconsistent timing beyond the frozen
provisional tolerance, the capture is classified GT_FAILED and is never
rescued manually.

Offset convention (matches frozen RhythmAlign v1.2.0 production semantics,
see alignment_engine_v2 module docstring):

    GT offset > 0 : the reference begins GT seconds into the benchmark input
                    (music must be delayed by GT on export).
    GT offset < 0 : the capture starts GT seconds INTO the reference
                    (the first |GT| seconds of the reference are trimmed).

GT offset is always reported relative to the TRIMMED benchmark input, i.e.
relative to the exact audio every system consumes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import signal

# ---------------------------------------------------------------------------
# frozen shakedown protocol constants (machinery engineering choices; to be
# re-examined and frozen properly from pilot-device data before the final
# study — see BENCHMARK_SHAKEDOWN.md "provisional tolerance" section)
# ---------------------------------------------------------------------------

FS = 48_000
CHIRP_DURATION_S = 0.75
CHIRP_F_LO_HZ = 1000.0
CHIRP_F_HI_HZ = 9000.0
CHIRP_PEAK_AMPLITUDE = 0.9
GUARD_DURATION_S = 1.0

# Trim margins around detected marker extents, independent of the guard
# length so that a localization slip can never leave audible chirp residue.
PRE_TRIM_MARGIN_S = 0.05
POST_TRIM_MARGIN_S = 0.05

# Marker detector acceptance (deterministic; no manual override). Exactly
# two occurrences are required by the two-marker QC (see find_marker_peaks).
MIN_MARKER_CONFIDENCE = 0.50     # normalized matched-filter peak

# Two-marker QC: provisional clock-scale tolerance for the SHAKEDOWN only.
# Consumer DAC/ADC chains drift tens to a few hundred ppm; 500 ppm covers
# plausible hardware while still catching resampling-scale and dropped-chunk
# faults. PROVISIONAL: must be re-frozen from real device pilots before the
# final study (see module docstring / BENCHMARK_SHAKEDOWN.md).
PROVISIONAL_MAX_CLOCK_SCALE_ERROR = 5e-4

# Two markers must agree on the payload mapping within this window.
MAX_MAPPING_DISAGREEMENT_S = 0.010

GT_VALID = "GT_VALID"
GT_FAILED = "GT_FAILED"


# ---------------------------------------------------------------------------
# buffer generation
# ---------------------------------------------------------------------------


def chirp_template(fs: int = FS) -> np.ndarray:
    """Deterministic linear chirp with a sinusoidal (equal-power) envelope.

    Pure function of fs: no RNG, no wall clock. The matched-filter detector
    anchors the reported position at the chirp's FIRST sample.
    """
    n = int(round(CHIRP_DURATION_S * fs))
    t = np.arange(n) / fs
    phase = (2 * np.pi
             * (CHIRP_F_LO_HZ * t
                + 0.5 * (CHIRP_F_HI_HZ - CHIRP_F_LO_HZ) * t ** 2 / CHIRP_DURATION_S))
    env = np.sin(np.pi * t / CHIRP_DURATION_S)
    return CHIRP_PEAK_AMPLITUDE * env * np.sin(phase)


@dataclass(frozen=True)
class BufferSpec:
    """Exact sample layout of the rendered playback buffer. Every index is
    exact by construction and stored in metadata."""

    fs: int
    payload_len_samples: int
    chirp_len_samples: int
    guard_len_samples: int
    marker1_start_sample: int          # 0 by construction
    payload_start_sample: int
    payload_end_sample: int            # exclusive
    marker2_start_sample: int
    expected_marker_separation_samples: int  # marker1 start -> marker2 start
    total_len_samples: int
    chirp_sha256: str


def buffer_spec(payload_len_samples: int, fs: int = FS) -> BufferSpec:
    import hashlib

    c = int(round(CHIRP_DURATION_S * fs))
    g = int(round(GUARD_DURATION_S * fs))
    p = int(payload_len_samples)
    chirp_hash = hashlib.sha256(
        np.ascontiguousarray(chirp_template(fs), dtype=np.float64).tobytes()
    ).hexdigest()
    return BufferSpec(
        fs=fs, payload_len_samples=p, chirp_len_samples=c, guard_len_samples=g,
        marker1_start_sample=0, payload_start_sample=c + g,
        payload_end_sample=c + g + p, marker2_start_sample=c + g + p + g,
        expected_marker_separation_samples=c + g + p + g,
        total_len_samples=c + g + p + g + c, chirp_sha256=chirp_hash,
    )


def render_marker_buffer(payload: np.ndarray, fs: int = FS) -> np.ndarray:
    """chirp1 | guard | payload | guard | chirp2, one float64 buffer."""
    spec = buffer_spec(len(payload), fs)
    out = np.zeros(spec.total_len_samples)
    chirp = chirp_template(fs)
    out[:spec.chirp_len_samples] = chirp
    out[spec.payload_start_sample:spec.payload_end_sample] = payload
    out[spec.marker2_start_sample:spec.marker2_start_sample + spec.chirp_len_samples] = chirp
    return out


# ---------------------------------------------------------------------------
# marker detection (independent of RhythmAlign and of every comparator)
# ---------------------------------------------------------------------------


@dataclass
class MarkerDetection:
    found: bool
    start_sample: Optional[float] = None   # float: parabolically refined
    confidence: float = 0.0                # normalized peak in [-1, 1]

    def as_dict(self):
        return {
            "found": bool(self.found),
            "start_sample": None if self.start_sample is None else float(self.start_sample),
            "confidence": float(self.confidence),
        }


@dataclass
class MarkerPeak:
    """One accepted marker occurrence (post non-maximum suppression)."""
    start_sample: float
    confidence: float

    def as_dict(self):
        return {"start_sample": float(self.start_sample),
                "confidence": float(self.confidence)}


def _normalized_correlation(rec: np.ndarray, template: np.ndarray):
    """Full normalized cross-correlation with per-lag overlap-energy
    normalization. Returns (ncc, lags) with lag m meaning:
    rec[m + i] ~= template[i]  ->  template starts at sample m.

    Windows whose overlap energy is negligible relative to the loudest
    window are forced to 0: an absolute energy floor would amplify FFT
    roundoff dust in near-silent regions into huge spurious "correlations"
    (observed as normalized peaks of value ~100 in digital-silence guards).
    The relative floor is amplitude-invariant.
    """
    n_r, n_t = len(rec), len(template)
    corr = signal.fftconvolve(rec, template[::-1], mode="full")  # len n_r+n_t-1
    # lag m = k - (n_t - 1), m in [-(n_t-1), n_r-1]
    lags = np.arange(-(n_t - 1), n_r)
    rec_pad = np.concatenate(([0.0], np.cumsum(rec * rec)))
    tpl_pad = np.concatenate(([0.0], np.cumsum(template * template)))
    # rec overlap: [max(0, m), min(n_r, m + n_t))
    lo_r = np.clip(np.maximum(lags, 0), 0, n_r)
    hi_r = np.clip(np.minimum(lags + n_t, n_r), 0, n_r)
    # template overlap: [max(0, -m), min(n_t, n_r - m))
    lo_t = np.clip(np.maximum(-lags, 0), 0, n_t)
    hi_t = np.clip(np.minimum(n_r - lags, n_t), 0, n_t)
    e_rec = rec_pad[hi_r] - rec_pad[lo_r]
    e_tpl = tpl_pad[hi_t] - tpl_pad[lo_t]
    e_prod = e_rec * e_tpl
    floor = (max(float(np.max(e_rec)), 1e-30)
             * max(float(np.max(e_tpl)), 1e-30) * 1e-12)
    ncc = np.where(e_prod > floor,
                   corr / np.sqrt(np.maximum(e_prod, 1e-30)),
                   0.0)
    return ncc, lags


def _parabolic_refine(values, idx):
    """Sub-sample peak offset from three samples around idx; 0.0 if at edge."""
    if idx <= 0 or idx >= len(values) - 1:
        return 0.0
    a, b, c = float(values[idx - 1]), float(values[idx]), float(values[idx + 1])
    denom = (a - 2 * b + c)
    if denom == 0:
        return 0.0
    delta = 0.5 * (a - c) / denom
    if not (-1.0 <= delta <= 1.0):
        return 0.0
    return float(delta)


def find_marker_peaks(rec: np.ndarray, template: np.ndarray,
                      fs: int = FS) -> list:
    """All accepted marker occurrences: normalized matched filter, then
    greedy non-maximum suppression with one-template-length separation.

    A peak is accepted only above MIN_MARKER_CONFIDENCE. The protocol buffer
    legitimately contains exactly TWO occurrences (pre and post chirp); the
    two-marker QC in derive_ground_truth therefore requires exactly two
    candidates — 0/1 means a missing or truncated marker, >=3 means
    ambiguous or corrupted detection. Deterministic; no manual override.
    """
    ncc, lags = _normalized_correlation(rec, template)
    if len(ncc) == 0:
        return []
    above = np.nonzero(ncc >= MIN_MARKER_CONFIDENCE)[0]
    order = above[np.argsort(-ncc[above], kind="stable")]
    sep = len(template)
    accepted = []
    for k in order:
        lag = lags[k]
        if all(abs(lag - a.start_sample) >= sep for a in accepted):
            accepted.append(MarkerPeak(
                start_sample=float(lag) + _parabolic_refine(ncc, k),
                confidence=float(ncc[k])))
    return sorted(accepted, key=lambda a: a.start_sample)


def detect_markers(capture: np.ndarray, fs: int = FS):
    """Detect both protocol markers in a capture.

    Returns (pre, post, n_candidates, third_party_max_ncc). pre/post are
    marked found=False unless exactly two candidates exist. third_party_max
    is the strongest normalized correlation outside one template length of
    either accepted marker (a third accepted candidate would already have
    failed the count rule).
    """
    template = chirp_template(fs)
    peaks = find_marker_peaks(capture, template, fs)
    if len(peaks) != 2:
        empty = MarkerDetection(found=False)
        return empty, empty, len(peaks), None
    pre = MarkerDetection(found=True, start_sample=peaks[0].start_sample,
                          confidence=peaks[0].confidence)
    post = MarkerDetection(found=True, start_sample=peaks[1].start_sample,
                           confidence=peaks[1].confidence)
    ncc, lags = _normalized_correlation(capture, template)
    window = len(template)
    third = 0.0
    for peak in peaks:
        near = np.abs(lags - peak.start_sample) < window
        third = max(third, float(np.max(ncc[~near])) if np.any(~near) else 0.0)
    return pre, post, len(peaks), third


# ---------------------------------------------------------------------------
# ground-truth derivation with two-marker QC
# ---------------------------------------------------------------------------


@dataclass
class GroundTruthResult:
    status: str                                  # GT_VALID | GT_FAILED
    fail_reason: Optional[str] = None
    payload_start_sample: Optional[int] = None   # capture timeline
    payload_end_sample: Optional[int] = None     # capture timeline (exclusive)
    clock_scale: Optional[float] = None          # observed/expected separation
    scale_error: Optional[float] = None          # clock_scale - 1
    marker_qc: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)

    def qc_dict(self):
        """Flat QC record for the manifest (no nested duplication)."""
        return {
            **self.marker_qc,
            "status": self.status,
            "fail_reason": self.fail_reason,
            "clock_scale": self.clock_scale,
            "scale_error": self.scale_error,
            "diagnostics": self.diagnostics,
        }


def derive_ground_truth(capture: np.ndarray, spec: BufferSpec,
                        fs: int = FS) -> GroundTruthResult:
    """Derive payload timing ground truth from a captured marker buffer.

    Deterministic failure conditions (GT_FAILED, no manual override):
      - the capture does not contain exactly two accepted marker candidates
        (missing/truncated marker, or ambiguous/extra occurrences);
      - observed marker separation implies a clock scale outside the
        provisional tolerance;
      - the two markers disagree on the payload mapping beyond the
        disagreement window.
    No compensation of the payload is ever performed; RhythmAlign is a
    fixed-offset aligner, so excessive drift invalidates the case instead of
    being warped away.
    """
    pre, post, n_candidates, third_party_max = detect_markers(capture, fs)
    qc = {
        "pre_marker": pre.as_dict(),
        "post_marker": post.as_dict(),
        "n_marker_candidates": int(n_candidates),
        "third_party_max_ncc": (None if third_party_max is None
                                else float(third_party_max)),
        "expected_marker_separation_samples": int(spec.expected_marker_separation_samples),
        "observed_marker_separation_samples": None,
        "provisional_max_clock_scale_error": PROVISIONAL_MAX_CLOCK_SCALE_ERROR,
        "max_mapping_disagreement_samples": int(round(MAX_MAPPING_DISAGREEMENT_S * fs)),
    }

    def failed(reason):
        return GroundTruthResult(status=GT_FAILED, fail_reason=reason,
                                 marker_qc=qc)

    if n_candidates != 2:
        return failed(
            f"expected exactly 2 marker candidates, found {n_candidates} "
            f"(missing/truncated marker or ambiguous detection)")
    if not pre.found or not post.found:  # defensive; covered by count rule
        return failed("marker detection incomplete")

    a = float(pre.start_sample)
    b = float(post.start_sample)
    obs_sep = b - a
    exp_sep = float(spec.expected_marker_separation_samples)
    if obs_sep <= 0:
        return failed("post-marker detected before pre-marker")
    qc["observed_marker_separation_samples"] = float(obs_sep)

    scale = obs_sep / exp_sep
    scale_error = scale - 1.0
    if abs(scale_error) > PROVISIONAL_MAX_CLOCK_SCALE_ERROR:
        return failed(
            f"clock scale error {scale_error:.6f} exceeds provisional "
            f"tolerance {PROVISIONAL_MAX_CLOCK_SCALE_ERROR:.6f}")

    # Payload mapping anchored at each marker; drift-corrected linear map.
    map_a = a + (spec.payload_start_sample - spec.marker1_start_sample) * scale
    map_b = b - (spec.marker2_start_sample - spec.payload_start_sample) * scale
    disagreement = abs(map_a - map_b)
    if disagreement > qc["max_mapping_disagreement_samples"]:
        return failed(
            f"two-marker payload mapping disagreement {disagreement:.1f} "
            f"samples exceeds tolerance")

    start = int(round(0.5 * (map_a + map_b)))
    end_map_a = a + (spec.payload_end_sample - spec.marker1_start_sample) * scale
    end_map_b = b - (spec.marker2_start_sample - spec.payload_end_sample) * scale
    end = int(round(0.5 * (end_map_a + end_map_b)))

    diag = {
        "payload_start_map_via_pre_samples": float(map_a),
        "payload_start_map_via_post_samples": float(map_b),
        "mapping_disagreement_samples": float(disagreement),
        "payload_start_samples_used": int(start),
        "payload_end_samples_used": int(end),
        "single_marker_payload_start_via_pre_only_samples":
            float(a + (spec.payload_start_sample - spec.marker1_start_sample)),
        "single_marker_payload_start_via_post_only_samples":
            float(b - (spec.marker2_start_sample - spec.payload_start_sample)),
    }
    return GroundTruthResult(
        status=GT_VALID, payload_start_sample=start, payload_end_sample=end,
        clock_scale=scale, scale_error=scale_error, marker_qc=qc,
        diagnostics=diag)


# ---------------------------------------------------------------------------
# trimming: marker buffer -> benchmark input (identical bytes for all systems)
# ---------------------------------------------------------------------------


@dataclass
class TrimResult:
    ok: bool
    fail_reason: Optional[str] = None
    trimmed: Optional[np.ndarray] = None
    trim_start_sample: Optional[int] = None   # capture timeline, inclusive
    trim_end_sample: Optional[int] = None     # capture timeline, exclusive
    holes: list = field(default_factory=list)  # [(start, end)] capture timeline
    payload_start_in_trimmed: Optional[int] = None  # may be negative
    gt_offset_s: Optional[float] = None       # relative to the TRIMMED input

    def as_dict(self):
        return {
            "ok": self.ok,
            "fail_reason": self.fail_reason,
            "trim_start_sample": self.trim_start_sample,
            "trim_end_sample": self.trim_end_sample,
            "holes": [list(h) for h in self.holes],
            "payload_start_in_trimmed": self.payload_start_in_trimmed,
            "gt_offset_s": self.gt_offset_s,
        }


def trim_capture(capture: np.ndarray, gt: GroundTruthResult, spec: BufferSpec,
                 fs: int = FS, trim_start: int = 0,
                 trim_end: Optional[int] = None) -> TrimResult:
    """Deterministically remove marker/guard material and produce the
    benchmark input.

    The output is the capture with these holes removed (concatenation, never
    time-stretched):
        [pre_chirp_start - PRE_TRIM_MARGIN, payload_start)
        [payload_end, post_chirp_end + POST_TRIM_MARGIN)
    clipped to the trim window [trim_start, trim_end). Audio outside the
    holes inside the window is kept (lead/tail ambience survives).

    trim_start may lie INSIDE the payload (negative/trim-equivalent offset
    case): the benchmark input then begins mid-music and GT is negative,
    exactly matching the production offset convention.

    GT offset of the reference relative to the TRIMMED input is
    payload_start_in_trimmed / fs, with the sign convention documented at
    module level.
    """
    if gt.status != GT_VALID:
        return TrimResult(ok=False,
                          fail_reason=f"GT not valid ({gt.status}: "
                                      f"{gt.fail_reason})")
    if trim_end is None:
        trim_end = len(capture)
    if not (0 <= trim_start < trim_end <= len(capture)):
        return TrimResult(ok=False, fail_reason="invalid trim window")

    pre_lo = int(round(gt.payload_start_sample
                       - (spec.payload_start_sample - spec.marker1_start_sample)
                       - PRE_TRIM_MARGIN_S * fs))
    hole1 = (max(trim_start, pre_lo), min(trim_end, gt.payload_start_sample))
    post_hi = int(round(gt.payload_end_sample
                        + (spec.marker2_start_sample - spec.payload_end_sample)
                        + spec.chirp_len_samples
                        + POST_TRIM_MARGIN_S * fs))
    hole2 = (max(trim_start, gt.payload_end_sample),
             min(trim_end, post_hi))

    active_holes = sorted(h for h in (hole1, hole2) if h[1] > h[0])

    kept_segments = []
    cursor = trim_start
    for lo, hi in active_holes:
        if lo > cursor:
            kept_segments.append(capture[cursor:lo])
        cursor = max(cursor, hi)
    if cursor < trim_end:
        kept_segments.append(capture[cursor:trim_end])

    # Payload position in the output: capture-relative payload start, minus
    # the trim window start, minus every sample removed strictly before the
    # payload start. This single formula covers positive offsets (ambient
    # lead kept, marker hole removed) and negative offsets (trim window
    # begins inside the payload, no hole precedes the payload start).
    removed_before_payload = 0
    for lo, hi in active_holes:
        overlap_lo = max(lo, trim_start)
        removed_before_payload += max(0, min(hi, gt.payload_start_sample)
                                      - overlap_lo)
    payload_start_in_trimmed = gt.payload_start_sample - trim_start \
        - removed_before_payload

    trimmed = np.concatenate(kept_segments) if kept_segments \
        else np.zeros(0)
    return TrimResult(
        ok=True, trimmed=trimmed, trim_start_sample=trim_start,
        trim_end_sample=trim_end,
        holes=[h for h in (hole1, hole2) if h[1] > h[0]],
        payload_start_in_trimmed=int(payload_start_in_trimmed),
        gt_offset_s=payload_start_in_trimmed / fs)


def marker_leakage_check(trimmed: np.ndarray, fs: int = FS) -> dict:
    """Mechanical leakage verification: re-run the detector on the final
    benchmark input. Any accepted detection is a protocol failure."""
    template = chirp_template(fs)
    ncc, lags = _normalized_correlation(trimmed, template)
    if len(ncc) == 0:
        return {"leakage": False, "max_ncc": 0.0,
                "threshold": MIN_MARKER_CONFIDENCE}
    k = int(np.argmax(ncc))
    peak = float(ncc[k])
    return {
        "leakage": bool(peak >= MIN_MARKER_CONFIDENCE),
        "max_ncc": peak,
        "max_ncc_lag_samples": int(lags[k]),
        "threshold": MIN_MARKER_CONFIDENCE,
    }
