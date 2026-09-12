"""RA-1.2C calibration-hardening tests.

Media-independent invariants added by RA-1.2C:
- calibration/holdout split identity isolation (no same-source leakage);
- exact-GT outcome classification semantics;
- threshold boundary behavior at the frozen policy floors;
- policy serialization / deterministic decisions;
- degradation determinism and exact placement of the semi-synthetic
  generator;
- repeated-call temp-file cleanup in the file entry point.

No user media and no absolute local paths are required.
"""
import os
import tempfile
import wave

import numpy as np

import alignment_engine_v2 as eng
from experiments.low_snr_alignment import semi_synthetic as ss

SR = 22050
HOP = 512
N_VIDEO_FRAMES = 600
CURVE_LEN = 1000


# ---------------------------------------------------------------------------
# plan helpers (same curve-building approach as the RA-1.2B tests)
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLAN_PATH = os.path.join(_HERE, "..", "experiments", "low_snr_alignment",
                          "semi_synthetic_plan.json")


def load_plan():
    import json
    with open(_PLAN_PATH, encoding="utf-8") as f:
        return json.load(f)


def make_curve(peaks, noise=1.0, seed=0, n=1000):
    rng = np.random.default_rng(seed)
    curve = noise * rng.standard_normal(n)
    x = np.arange(n)
    for idx, height, width in peaks:
        curve = curve + height * np.exp(-0.5 * ((x - idx) / width) ** 2)
    return curve


def idx_of_offset(offset_s, n_video_frames=N_VIDEO_FRAMES):
    return int(round(-offset_s * SR / HOP)) + (n_video_frames - 1)


def height_for_z(target_z, seed, idx, noise=1.0, n=CURVE_LEN,
                 win_frames=13):
    """Peak height that makes the best Z inside the cluster window
    (idx +/- win_frames, ~ cluster_tol 0.15 s) equal `target_z` on the
    deterministic stream. Z is normalized by the whole-curve std and the
    engine scores the window's best peak, so solve max-window-Z by
    bisection (monotonic in the height)."""
    def realized(h):
        curve = make_curve([(idx, h, 3.0)], noise=noise, seed=seed, n=n)
        lo = max(0, idx - win_frames)
        hi = min(n, idx + win_frames + 1)
        return max(eng._z_at_index(curve, i) for i in range(lo, hi))

    lo, hi = 0.0, max(8.0, 4.0 * target_z)
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if realized(mid) < target_z:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def family_result(method, curve):
    return eng.FamilyResult(
        method=method, family=eng.METHOD_FAMILY[method], curve=curve,
        n_video_frames=N_VIDEO_FRAMES,
        z=eng._z_at_index(curve, int(np.argmax(curve))), runtime_s=0.0,
    )


def flat_family(method, seed=1):
    return family_result(method, make_curve([], seed=seed))


def decide(families, policy=None, durations=(92.0, 64.0)):
    return eng.decide_from_families(families, SR, HOP, policy,
                                    durations[0], durations[1])


# ---------------------------------------------------------------------------
# split identity isolation / leakage
# ---------------------------------------------------------------------------


def test_plan_split_is_disjoint_and_leak_free():
    problems = ss.audit_split(load_plan())
    assert problems == []


def test_split_covers_every_project_exactly_once():
    plan = load_plan()
    split = plan["split"]
    assert len(split["calibration_projects"]) == 10
    assert len(split["holdout_projects"]) == 10
    assert not (set(split["calibration_projects"])
                & set(split["holdout_projects"]))
    n_recordings = sum(len(spec["recordings"])
                       for spec in split["projects"].values())
    assert n_recordings == 29  # matches the RA-1.2B real corpus


def test_semi_synthetic_offsets_vary_and_clear_overlap_guard():
    plan = load_plan()
    offsets = [c["offset_s"] for c in plan["positives"]]
    assert any(abs(o) < 1.0 for o in offsets), "near-zero offset missing"
    assert any(o < -2.0 for o in offsets), "negative offset missing"
    assert len(set(offsets)) >= 20, "offsets not varied enough"
    assert all(ss.usable_overlap_s(o, 145.0, 119.0) >= 45.0
               for o in offsets)


# ---------------------------------------------------------------------------
# exact-GT outcome classification
# ---------------------------------------------------------------------------


def _decision_like(status, offset):
    from types import SimpleNamespace
    return SimpleNamespace(status=status, offset=offset)


def test_classify_positive_semantics():
    assert ss.classify_positive(
        _decision_like("accepted", 12.45), 12.4, 0.15) == ss.CORRECT_ACCEPT
    assert ss.classify_positive(
        _decision_like("accepted", 13.0), 12.4, 0.15) == ss.WRONG_ACCEPT
    assert ss.classify_positive(
        _decision_like("abstained", None), 12.4, 0.15) == ss.SAFE_ABSTAIN


def test_classify_negative_semantics():
    assert ss.classify_negative(
        _decision_like("abstained", None)) == ss.SAFE_ABSTAIN
    assert ss.classify_negative(
        _decision_like("accepted", 5.0)) == ss.WRONG_ACCEPT
    # tiled ambiguity: accept on SOME tile start is a policy gap, not a
    # wrong offset
    assert ss.classify_negative(
        _decision_like("accepted", 19.2), tile_starts_s=[0.0, 9.6, 19.2],
    ) == "TILE_CONSISTENT_ACCEPT"
    assert ss.classify_negative(
        _decision_like("accepted", 12.3), tile_starts_s=[0.0, 9.6, 19.2],
    ) == ss.WRONG_ACCEPT


# ---------------------------------------------------------------------------
# threshold boundary behavior (frozen policy floors)
# ---------------------------------------------------------------------------


def test_case_a_tonal_floor_is_binding_boundary():
    # pcen evidence strong at the cluster; tonal cluster Z just below vs
    # above the 5.0 floor decides CASE A. Heights are solved so the
    # realized cluster Z is 4.8 vs 5.2 on the deterministic stream. The
    # onset curve has low noise and keeps its only peak far from the
    # cluster, so CASE B cannot fire.
    idx = idx_of_offset(7.3)
    far = idx_of_offset(-9.0)
    pcen = family_result("pcen_hpss",
                         make_curve([(idx, 12.0, 3.0)], seed=41))
    onset = family_result(
        "onset", make_curve([(far, 3.0, 3.0)], noise=0.2, seed=42))
    below = family_result(
        "hybrid", make_curve([(idx, height_for_z(4.8, 43, idx), 3.0)],
                             seed=43))
    d = decide([below, onset, pcen])
    assert d.status == eng.STATUS_ABSTAINED
    above = family_result(
        "hybrid", make_curve([(idx, height_for_z(5.2, 43, idx), 3.0)],
                             seed=43))
    d2 = decide([above, onset, pcen])
    assert d2.status == eng.STATUS_ACCEPTED
    assert d2.reason_code == eng.ACCEPT_DUAL_FAMILY


def test_case_a_pcen_floor_is_binding_boundary():
    # Same bracketing method against the pcen_z_floor 5.6 (realized 5.4 vs
    # 5.8).
    idx = idx_of_offset(7.3)
    far = idx_of_offset(-9.0)
    tonal = family_result("hybrid",
                          make_curve([(idx, 12.0, 3.0)], seed=45))
    onset = family_result(
        "onset", make_curve([(far, 3.0, 3.0)], noise=0.2, seed=46))
    below = family_result(
        "pcen_hpss", make_curve([(idx, height_for_z(5.4, 47, idx), 3.0)],
                                seed=47))
    d = decide([tonal, onset, below])
    assert d.status == eng.STATUS_ABSTAINED
    above = family_result(
        "pcen_hpss", make_curve([(idx, height_for_z(5.8, 47, idx), 3.0)],
                                seed=47))
    d2 = decide([tonal, onset, above])
    assert d2.status == eng.STATUS_ACCEPTED


def test_case_b_requires_uniqueness_margin():
    # pcen Z above the 7.0 primary floor and onset corroborating, but the
    # competing peak is nearly as strong (margin < 1.4): no CASE B accept.
    idx = idx_of_offset(7.3)
    other = idx_of_offset(-6.0)
    pcen = family_result(
        "pcen_hpss",
        make_curve([(idx, 10.0, 3.0), (other, 9.0, 3.0)], seed=49))
    onset = family_result("onset", make_curve([(idx, 3.0, 3.0)], seed=50))
    d = decide([flat_family("hybrid", seed=51), onset, pcen])
    assert d.status == eng.STATUS_ABSTAINED
    assert d.reason_code == eng.ABSTAIN_AMBIGUOUS_CLUSTER


def test_frozen_policy_defaults_unchanged():
    p = eng.DEFAULT_POLICY
    assert (p.tonal_z_floor, p.pcen_z_floor, p.pcen_primary_z_floor,
            p.onset_corroboration_z_floor, p.margin_floor_a,
            p.margin_floor_b) == (5.0, 5.6, 7.0, 2.0, 1.00, 1.40)


# ---------------------------------------------------------------------------
# policy serialization / deterministic decisions
# ---------------------------------------------------------------------------


def test_decision_is_deterministic_and_serializes_policy():
    idx = idx_of_offset(7.3)

    def families_once():
        return [
            family_result("hybrid",
                          make_curve([(idx, 12.0, 3.0)], seed=52)),
            flat_family("onset", seed=53),
            family_result("pcen_hpss",
                          make_curve([(idx, 12.0, 3.0)], seed=54)),
            family_result("pcen", make_curve([(idx, 11.0, 3.0)], seed=55)),
        ]

    d1 = decide(families_once())
    d2 = decide(families_once())
    a, b = d1.as_dict(), d2.as_dict()
    a.pop("runtime_s"), b.pop("runtime_s")
    assert a == b
    assert d1.policy == eng.dataclasses.asdict(eng.DEFAULT_POLICY)


# ---------------------------------------------------------------------------
# degradation determinism / exact placement
# ---------------------------------------------------------------------------


def _tiny_bg_and_track():
    rng = np.random.default_rng(7)
    # quiet background: no clipping protection kicks in, so placement is
    # exactly the background plus the gained track
    bg = (0.05 * rng.standard_normal(int(20.0 * SR))).astype(np.float32)
    t = np.arange(int(10.0 * SR)) / SR
    track = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return bg, track


def test_reverb_is_deterministic_and_seed_sensitive():
    y = np.random.default_rng(3).standard_normal(SR).astype(np.float32)
    a = ss.room_reverb(y, seed=11)
    b = ss.room_reverb(y, seed=11)
    c = ss.room_reverb(y, seed=12)
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, c)


def test_build_positive_places_track_at_exact_offset():
    bg, track = _tiny_bg_and_track()
    offset = 3.0
    mix, gt = ss.build_positive(bg, track, offset, gain_db=-10.0,
                                condition="clean", seed=0)
    assert gt == offset
    off_i = int(round(offset * SR))
    gain = (ss._rms(bg) / ss._rms(track)) * 10.0 ** (-10.0 / 20.0)
    # before the offset the mix is the background alone; at the offset the
    # track contribution begins exactly
    np.testing.assert_allclose(mix[:off_i], bg[:off_i], rtol=0, atol=1e-6)
    expected_start = bg[off_i] + track[0] * gain
    assert abs(mix[off_i] - expected_start) < 1e-6


def test_build_positive_never_clips_even_loud_inputs():
    rng = np.random.default_rng(9)
    loud_bg = (0.6 * rng.standard_normal(int(10.0 * SR))).astype(np.float32)
    _, track = _tiny_bg_and_track()
    mix, _ = ss.build_positive(loud_bg, track, 2.0, gain_db=0.0,
                               condition="clean", seed=0)
    assert float(np.max(np.abs(mix))) <= 0.99 + 1e-6


def test_negative_offset_trims_track_head():
    bg, track = _tiny_bg_and_track()
    offset = -2.0
    mix, gt = ss.build_positive(bg, track, offset, gain_db=-10.0,
                                condition="clean", seed=0)
    assert gt == offset
    trim = int(round(-offset * SR))
    gain = (ss._rms(bg) / ss._rms(track)) * 10.0 ** (-10.0 / 20.0)
    assert abs(mix[0] - (bg[0] + track[trim] * gain)) < 1e-5


def test_usable_overlap_matches_production_convention():
    # positive offset: shared audio is the music tail inside the video
    assert ss.usable_overlap_s(10.0, 100.0, 60.0) == 60.0
    assert ss.usable_overlap_s(50.0, 100.0, 60.0) == 50.0
    # negative offset trims the music head
    assert ss.usable_overlap_s(-10.0, 100.0, 60.0) == 50.0


# ---------------------------------------------------------------------------
# repeated-call cleanup invariants (file entry point)
# ---------------------------------------------------------------------------


def _write_wav(path, y, sr=SR):
    pcm = (np.clip(y, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def test_find_offset_v2_leaves_no_temp_files():
    import glob

    from experiments.low_snr_alignment.synthetic_eval import (
        make_music,
        make_recording,
    )
    music = make_music(duration_s=40.0)
    strong = make_recording(music, true_offset=5.0, music_gain=0.5,
                            noise_gain=0.004, seed=61)
    tmp = tempfile.mkdtemp(prefix="ra12c_")
    wav_m = os.path.join(tmp, "music.wav")
    wav_v = os.path.join(tmp, "video.wav")
    _write_wav(wav_m, music)
    _write_wav(wav_v, strong)
    try:
        before = len(glob.glob(os.path.join(
            tempfile.gettempdir(), "ra_v2_*")))
        d = eng.find_offset_v2(wav_v, wav_m)
        assert d.status == eng.STATUS_ACCEPTED
        after = len(glob.glob(os.path.join(
            tempfile.gettempdir(), "ra_v2_*")))
        assert after == before
    finally:
        for name in (wav_m, wav_v):
            os.remove(name)
        os.rmdir(tmp)
