"""Research-only regression tests for defects exposed by the first REAL
acoustic round trip (2026-09-14, owner phone m4a capture).

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

Covers:
  1. m4a/AAC capture decode path (libsndfile cannot read AAC; the bundled
     ffmpeg must decode at the NATIVE rate — resampling would destroy the
     clock-drift measurement).
  2. Full-template-overlap restriction (capture-edge partial overlaps
     produced phantom 0.32-confidence "markers" from ~2 ms of content).
  3. The real-device confidence regime: true markers on reverberant/AAC
     audio score ~0.22-0.28 while non-marker content stays <= 0.05, so the
     gate constant must accept that regime (provisional 0.15).
"""
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import marker_protocol as mp  # noqa: E402
from experiments.applied_system import synth_payload  # noqa: E402

FS = mp.FS


@pytest.fixture(scope="module")
def song_a():
    return synth_payload.render_song_a(duration_s=4.0)


def test_min_marker_confidence_covers_real_device_regime():
    """The gate must accept the confidence measured for genuine markers on
    the first real capture (0.226 / 0.243) — the synthetic-era 0.50 gate
    rejected both real markers. This test pins the regression: if the
    constant is raised again without a multi-device pilot re-derivation,
    real-device captures silently fail."""
    assert mp.MIN_MARKER_CONFIDENCE <= 0.22


def test_full_template_overlap_required(song_a):
    """A loud non-marker burst near the capture END must not produce a
    phantom marker from a tiny template overlap (observed: ncc 0.32 from
    ~2 ms of content on the real capture)."""
    buf = mp.render_marker_buffer(song_a)
    rng = np.random.default_rng(42)
    cap = np.concatenate([buf, rng.normal(0.35, 1.0, int(0.5 * FS))])
    peaks = mp.find_marker_peaks(cap, mp.chirp_template(FS), FS)
    # only the two genuine markers, no phantom at the noisy tail
    assert len(peaks) == 2, [(p.start_sample, p.confidence) for p in peaks]


def test_partially_captured_chirp_fails(song_a):
    """A capture ending mid-chirp2 must report ONE candidate (the
    incomplete second chirp is not a marker), never accept the partial
    overlap as a detection."""
    buf = mp.render_marker_buffer(song_a)
    cut = int(0.5 * FS)  # stop halfway through the final chirp
    cap = buf[:len(buf) - cut]
    peaks = mp.find_marker_peaks(cap, mp.chirp_template(FS), FS)
    assert len(peaks) == 1
    gt = mp.derive_ground_truth(cap, mp.buffer_spec(len(song_a)), FS)
    assert gt.status == mp.GT_FAILED


def test_chirp_before_capture_start_fails(song_a):
    """A capture that starts mid-chirp1 (negative-lag partial overlap) must
    not detect the truncated first chirp."""
    buf = mp.render_marker_buffer(song_a)
    cap = buf[int(0.4 * FS):]  # capture begins 100 ms into chirp1
    peaks = mp.find_marker_peaks(cap, mp.chirp_template(FS), FS)
    assert len(peaks) == 1  # only chirp2


def test_m4a_decode_native_rate(tmp_path, song_a):
    """End-to-end: an AAC (m4a) capture must be decoded via the bundled
    ffmpeg at its native rate and yield valid GT — regression for the
    LibsndfileError 'Format not recognised' failure on the real owner
    recording."""
    import subprocess
    import imageio_ffmpeg
    from experiments.applied_system.acoustic_loop import _load_capture

    wav_path = tmp_path / "buffer.wav"
    sf.write(str(wav_path), mp.render_marker_buffer(song_a), FS,
             subtype="PCM_16")
    m4a_path = tmp_path / "capture.m4a"
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(wav_path),
           "-c:a", "aac", "-b:a", "96k", str(m4a_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]

    y, native_sr, info = _load_capture(m4a_path, tmp_path, "m4a_test")
    assert info["decoded_via_ffmpeg"] is True
    assert native_sr == FS  # native rate preserved (no resampling)
    gt = mp.derive_ground_truth(y, mp.buffer_spec(len(song_a), fs=native_sr),
                                fs=native_sr)
    assert gt.status == mp.GT_VALID, gt.fail_reason
    assert gt.payload_start_sample == mp.buffer_spec(
        len(song_a), fs=native_sr).payload_start_sample


def test_sweep_trajectory_corroborates_clean_chirp(song_a):
    """The trajectory diagnostic must corroborate a genuine (synthetic)
    chirp and reject a random burst of the same energy."""
    from experiments.applied_system.acoustic_loop import \
        sweep_trajectory_check
    buf = mp.render_marker_buffer(song_a)
    ok = sweep_trajectory_check(buf, 0.0, FS)
    assert ok["corroborated"], ok
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 0.3, int(1.0 * FS))
    bad = sweep_trajectory_check(noise, 0.1 * FS, FS)
    assert not bad["corroborated"], bad
