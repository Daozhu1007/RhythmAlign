"""Research-only tests: marker protocol (generation, detection, QC, trim,
sign convention). SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE."""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import marker_protocol as mp  # noqa: E402
from experiments.applied_system import synth_payload  # noqa: E402

FS = mp.FS
PAYLOAD_S = 8.0


@pytest.fixture(scope="module")
def song_a():
    return synth_payload.render_song_a(duration_s=PAYLOAD_S)


@pytest.fixture(scope="module")
def spec(song_a):
    return mp.buffer_spec(len(song_a))


def _ambient(cap, lead_s, tail_s, seed=7):
    rng = np.random.default_rng(seed)
    parts = []
    if lead_s:
        parts.append(rng.normal(0, 3e-4, int(round(lead_s * FS))))
    parts.append(cap)
    if tail_s:
        parts.append(rng.normal(0, 3e-4, int(round(tail_s * FS))))
    return np.concatenate(parts) if len(parts) > 1 else parts[0]


def test_render_determinism_and_spec(song_a, spec):
    b1 = mp.render_marker_buffer(song_a)
    b2 = mp.render_marker_buffer(song_a)
    assert b1.tobytes() == b2.tobytes()
    c = int(round(mp.CHIRP_DURATION_S * FS))
    g = int(round(mp.GUARD_DURATION_S * FS))
    assert spec.chirp_len_samples == c and spec.guard_len_samples == g
    assert spec.marker1_start_sample == 0
    assert spec.payload_start_sample == c + g
    assert spec.payload_end_sample == c + g + len(song_a)
    assert spec.marker2_start_sample == c + g + len(song_a) + g
    assert spec.expected_marker_separation_samples == c + g + len(song_a) + g
    assert spec.total_len_samples == 2 * c + 2 * g + len(song_a)
    assert len(b1) == spec.total_len_samples
    # second chirp is a verbatim copy of the first
    assert np.array_equal(b1[:c], b1[spec.marker2_start_sample:
                                     spec.marker2_start_sample + c])


def test_detection_exact_buffer(song_a, spec):
    buf = mp.render_marker_buffer(song_a)
    gt = mp.derive_ground_truth(buf, spec)
    assert gt.status == mp.GT_VALID, gt.fail_reason
    assert gt.payload_start_sample == spec.payload_start_sample
    assert gt.payload_end_sample == spec.payload_end_sample
    assert abs(gt.scale_error) < 1e-9


@pytest.mark.parametrize("degradation,lead_s", [
    ("amplitude_0x35", 2.5), ("noise_10db", 2.5),
    ("lead_silence", 3.0), ("trailing_silence", 0.0), ("clipped", 2.5),
])
def test_detection_under_degradations(song_a, spec, degradation, lead_s):
    buf = mp.render_marker_buffer(song_a)
    rng = np.random.default_rng(11)
    if degradation == "amplitude_0x35":
        cap = _ambient(buf * 0.35, lead_s, 2.0)
    elif degradation == "noise_10db":
        payload_rms = float(np.sqrt(np.mean(song_a ** 2)))
        cap = _ambient(buf + rng.normal(
            0.0, payload_rms * 10 ** (-10 / 20), len(buf)), lead_s, 2.0)
    elif degradation == "lead_silence":
        cap = _ambient(buf, lead_s, 0.0)
    elif degradation == "trailing_silence":
        cap = _ambient(buf, lead_s, 2.0)
    elif degradation == "clipped":
        cap = _ambient(np.clip(buf, -0.4, 0.4), lead_s, 2.0)
    gt = mp.derive_ground_truth(cap, spec)
    assert gt.status == mp.GT_VALID, gt.fail_reason
    truth = int(round(lead_s * FS)) + spec.payload_start_sample
    assert abs(gt.payload_start_sample - truth) <= int(0.5e-3 * FS)


def test_resample_drift_scale_measured_and_corrected(song_a, spec):
    buf = mp.render_marker_buffer(song_a)
    cap = _ambient(buf, 2.5, 2.0)
    drifted = resample_poly(cap, 4001, 4000)  # +250 ppm clock stretch
    gt = mp.derive_ground_truth(drifted, spec)
    assert gt.status == mp.GT_VALID, gt.fail_reason
    assert abs(gt.scale_error - 1 / 4000) < 1e-9
    truth = (int(round(2.5 * FS)) + spec.payload_start_sample) * 4001 / 4000
    assert abs(gt.payload_start_sample - truth) <= int(0.5e-3 * FS)


def test_two_marker_qc_scale_rule(song_a, spec):
    buf = mp.render_marker_buffer(song_a)
    cap = _ambient(buf, 2.5, 2.0)
    drifted = resample_poly(cap, 1001, 1000)  # +1000 ppm: markers still
    # detectable, but the scale QC must refuse
    gt = mp.derive_ground_truth(drifted, spec)
    assert gt.status == mp.GT_FAILED
    assert "clock scale" in gt.fail_reason
    assert gt.marker_qc["n_marker_candidates"] == 2


def test_two_marker_qc_truncation(song_a, spec):
    buf = mp.render_marker_buffer(song_a)
    cap = _ambient(buf, 2.5, 2.0)
    # payload occupies cap seconds 4.25..12.25; cut mid-payload
    truncated = cap[:int(8.0 * FS)]
    gt = mp.derive_ground_truth(truncated, spec)
    assert gt.status == mp.GT_FAILED
    assert gt.marker_qc["n_marker_candidates"] == 1


def test_two_marker_qc_extra_marker(song_a, spec):
    buf = mp.render_marker_buffer(song_a)
    # a third chirp injected between the guards is ambiguous corruption
    corrupted = np.concatenate([buf[:spec.payload_start_sample],
                                mp.chirp_template(),
                                buf[spec.payload_start_sample:]])
    gt = mp.derive_ground_truth(corrupted, spec)
    assert gt.status == mp.GT_FAILED
    assert gt.marker_qc["n_marker_candidates"] == 3


def test_trim_removes_markers_keeps_payload(song_a, spec):
    buf = mp.render_marker_buffer(song_a)
    cap = _ambient(buf, 2.5, 2.0)
    gt = mp.derive_ground_truth(cap, spec)
    tr = mp.trim_capture(cap, gt, spec)
    assert tr.ok
    start = tr.payload_start_in_trimmed
    seg = tr.trimmed[start:start + spec.payload_len_samples]
    assert np.array_equal(seg, song_a)  # payload verbatim at the GT position
    leak = mp.marker_leakage_check(tr.trimmed)
    assert not leak["leakage"], leak
    expected_len = (len(cap)
                    - (tr.holes[0][1] - tr.holes[0][0])
                    - (tr.holes[1][1] - tr.holes[1][0]))
    assert len(tr.trimmed) == expected_len


def test_sign_convention_positive(song_a, spec):
    """GT offset must be relative to the TRIMMED input and positive when the
    reference begins inside it (production convention: music delayed by
    offset seconds)."""
    buf = mp.render_marker_buffer(song_a)
    cap = _ambient(buf, 2.5, 2.0)
    gt = mp.derive_ground_truth(cap, spec)
    tr = mp.trim_capture(cap, gt, spec)
    # independent arithmetic: kept lead ambient = lead - pre-trim margin
    assert tr.gt_offset_s == pytest.approx(2.5 - mp.PRE_TRIM_MARGIN_S,
                                           abs=1e-9)
    assert tr.gt_offset_s > 0


def test_sign_convention_negative(song_a, spec):
    """A benchmark input starting mid-payload must yield a NEGATIVE GT
    (first |offset| seconds of the reference trimmed), exactly the frozen
    v1.2.0 production convention."""
    buf = mp.render_marker_buffer(song_a)
    cap = _ambient(buf, 2.5, 2.0)
    gt = mp.derive_ground_truth(cap, spec)
    cut_s = 2.0
    trim_start = gt.payload_start_sample + int(round(cut_s * FS))
    tr = mp.trim_capture(cap, gt, spec, trim_start=trim_start)
    assert tr.ok
    assert tr.gt_offset_s == pytest.approx(-cut_s, abs=1e-9)
    seg = tr.trimmed[:len(song_a) - int(round(cut_s * FS))]
    assert np.array_equal(seg, song_a[int(round(cut_s * FS)):])
    leak = mp.marker_leakage_check(tr.trimmed)
    assert not leak["leakage"], leak


def test_gt_recomputation_after_trimming(song_a, spec):
    """GT recomputed from trim bookkeeping must equal the reported offset:
    payload_start_in_trimmed = payload_start - trim_start - removed_before."""
    buf = mp.render_marker_buffer(song_a)
    cap = _ambient(buf, 2.5, 2.0)
    gt = mp.derive_ground_truth(cap, spec)
    for trim_start in (0, int(round(1.0 * FS))):
        tr = mp.trim_capture(cap, gt, spec, trim_start=trim_start)
        removed_before = sum(
            max(0, min(hi, gt.payload_start_sample) - max(lo, trim_start))
            for lo, hi in tr.holes)
        expected = (gt.payload_start_sample - trim_start
                    - removed_before) / FS
        assert tr.gt_offset_s == pytest.approx(expected, abs=1e-12)
        assert tr.payload_start_in_trimmed / FS == pytest.approx(
            tr.gt_offset_s, abs=1e-12)


def test_trim_rejects_invalid_gt(spec, song_a):
    buf = mp.render_marker_buffer(song_a)
    bad = mp.GroundTruthResult(status=mp.GT_FAILED, fail_reason="x")
    tr = mp.trim_capture(buf, bad, spec)
    assert not tr.ok
