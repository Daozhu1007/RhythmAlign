"""RA-1.2B Alignment Engine v2 tests.

Media-independent: policy tests run on synthetic correlation curves through
the decide_from_families() seam; end-to-end tests use small deterministic
synthetic audio. No user media is required.
"""
import wave

import numpy as np
import pytest

import auto_sync
import alignment_engine_v2 as eng
from experiments.low_snr_alignment.synthetic_eval import (
    make_music,
    make_recording,
)

SR = 22050
HOP = 512
N_VIDEO_FRAMES = 600
CURVE_LEN = 1000


# ---------------------------------------------------------------------------
# curve construction helpers
# ---------------------------------------------------------------------------


def make_curve(peaks, noise=1.0, seed=0, n=CURVE_LEN):
    """Noise curve + gaussian peaks [(index, height, width_frames)]."""
    rng = np.random.default_rng(seed)
    curve = noise * rng.standard_normal(n)
    x = np.arange(n)
    for idx, height, width in peaks:
        curve = curve + height * np.exp(-0.5 * ((x - idx) / width) ** 2)
    return curve


def idx_of_offset(offset_s, n_video_frames=N_VIDEO_FRAMES):
    return int(round(-offset_s * SR / HOP)) + (n_video_frames - 1)


def offset_of(idx, n_video_frames=N_VIDEO_FRAMES):
    return -((idx - (n_video_frames - 1)) * HOP) / SR


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
# policy tests (CASE A-E, family bookkeeping)
# ---------------------------------------------------------------------------


def test_case_a_dual_family_agreement_accepts():
    idx = idx_of_offset(7.3)
    tonal = family_result("hybrid", make_curve([(idx, 12.0, 3.0)], seed=2))
    pcen = family_result("pcen_hpss", make_curve([(idx, 12.0, 3.0)], seed=3))
    onset = flat_family("onset")
    d = decide([tonal, pcen, onset])
    assert d.status == eng.STATUS_ACCEPTED
    assert d.reason_code == eng.ACCEPT_DUAL_FAMILY
    assert d.offset is not None and abs(d.offset - 7.3) <= 0.15


def test_case_c_no_evidence_abstains():
    d = decide([flat_family(m, seed=i) for i, m in
                enumerate(("hybrid", "onset", "pcen_hpss", "pcen"))])
    assert d.status == eng.STATUS_ABSTAINED
    assert d.offset is None
    assert d.reason_code == eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS


def test_case_c_misleading_high_z_single_family_abstains():
    # One family produces a sharp, high-Z peak; nothing corroborates it.
    idx = idx_of_offset(7.3)
    tonal = family_result("hybrid", make_curve([(idx, 14.0, 3.0)], seed=4))
    d = decide([tonal, flat_family("onset", seed=5),
                flat_family("pcen_hpss", seed=6), flat_family("pcen", seed=7)])
    assert d.status == eng.STATUS_ABSTAINED
    assert d.offset is None


def test_pcen_and_pcen_hpss_are_one_vote_not_two():
    # pcen_hpss + plain pcen agree on a strong wrong candidate, but they are
    # the SAME family: without tonal agreement (CASE A) or onset
    # corroboration (CASE B) this must never be accepted.
    idx = idx_of_offset(7.3)
    hpss = family_result("pcen_hpss", make_curve([(idx, 14.0, 3.0)], seed=8))
    plain = family_result("pcen", make_curve([(idx, 12.0, 3.0)], seed=9))
    d = decide([flat_family("hybrid", seed=10), flat_family("onset", seed=11),
                hpss, plain])
    assert d.status == eng.STATUS_ABSTAINED
    assert d.reason_code == eng.ABSTAIN_PRIMARY_NOT_CORROBORATED


def test_case_b_strong_primary_with_onset_corroboration_accepts():
    idx = idx_of_offset(7.3)
    pcen = family_result("pcen_hpss",
                         make_curve([(idx, 15.0, 3.0), (idx_of_offset(-6.0),
                                                        1.5, 3.0)], seed=12))
    onset = family_result("onset", make_curve([(idx, 3.5, 3.0)], seed=13))
    tonal = family_result("hybrid",
                          make_curve([(idx_of_offset(-6.0), 12.0, 3.0)],
                                     seed=14))
    d = decide([tonal, onset, pcen])
    assert d.status == eng.STATUS_ACCEPTED
    assert d.reason_code == eng.ACCEPT_PRIMARY_WITH_CORROBORATION
    assert d.offset is not None and abs(d.offset - 7.3) <= 0.15


def test_case_b_strong_primary_without_onset_abstains():
    idx = idx_of_offset(7.3)
    pcen = family_result("pcen_hpss", make_curve([(idx, 15.0, 3.0)], seed=15))
    tonal = family_result("hybrid",
                          make_curve([(idx_of_offset(-6.0), 12.0, 3.0)],
                                     seed=16))
    d = decide([tonal, flat_family("onset", seed=17), pcen])
    assert d.status == eng.STATUS_ABSTAINED
    assert d.reason_code == eng.ABSTAIN_PRIMARY_NOT_CORROBORATED


def test_case_d_comparable_competing_cluster_abstains():
    # Two clusters both carrying both primary families at comparable
    # strength: content ambiguity -> abstain.
    idx1 = idx_of_offset(7.3)
    idx2 = idx_of_offset(12.0)
    tonal = family_result(
        "hybrid", make_curve([(idx1, 12.0, 3.0), (idx2, 11.8, 3.0)], seed=18))
    pcen = family_result(
        "pcen_hpss", make_curve([(idx1, 12.0, 3.0), (idx2, 11.8, 3.0)],
                                seed=19))
    d = decide([tonal, flat_family("onset", seed=20), pcen])
    assert d.status == eng.STATUS_ABSTAINED
    assert d.reason_code == eng.ABSTAIN_AMBIGUOUS_CLUSTER


def test_case_e_insufficient_overlap_abstains():
    # Strong dual-family peak whose overlap (20 s) is below the 30 s floor.
    idx = idx_of_offset(12.0)
    tonal = family_result("hybrid", make_curve([(idx, 12.0, 3.0)], seed=21))
    pcen = family_result("pcen_hpss", make_curve([(idx, 12.0, 3.0)], seed=22))
    d = decide([tonal, flat_family("onset", seed=23), pcen],
               durations=(92.0, 20.0))
    assert d.status == eng.STATUS_ABSTAINED
    assert d.reason_code == eng.ABSTAIN_INSUFFICIENT_OVERLAP


# ---------------------------------------------------------------------------
# decision object plumbing
# ---------------------------------------------------------------------------


def test_decision_serializes_and_reports_message():
    idx = idx_of_offset(7.3)
    tonal = family_result("hybrid", make_curve([(idx, 12.0, 3.0)], seed=24))
    pcen = family_result("pcen_hpss", make_curve([(idx, 12.0, 3.0)], seed=25))
    d = decide([tonal, flat_family("onset", seed=26), pcen])
    payload = d.as_dict()
    assert payload["status"] == eng.STATUS_ACCEPTED
    assert set(payload) == {"status", "offset", "reason_code", "evidence",
                            "clusters", "policy", "runtime_s"}
    assert "已确定对齐偏移" in eng.decision_message(d)

    d_abstain = decide([flat_family(m, seed=i) for i, m in
                        enumerate(("hybrid", "onset", "pcen_hpss", "pcen"))])
    assert eng.decision_message(d_abstain)
    # presentation layer is separable: message strings never feed decisions
    assert d_abstain.reason_code == eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS


def test_default_v1_path_unchanged():
    # Engine v2 must not have altered the v1.1.x default alignment path.
    assert auto_sync._CONFIDENCE_THRESHOLD == 2.0
    assert callable(auto_sync.find_offset)


# ---------------------------------------------------------------------------
# end-to-end audio tests (deterministic synthetic media)
# ---------------------------------------------------------------------------


def test_end_to_end_strong_signal_accepts_true_offset():
    music = make_music(duration_s=40.0)
    video = make_recording(music, true_offset=6.4, music_gain=0.5,
                           noise_gain=0.004, seed=31)
    d = eng.decide_alignment(video, music)
    assert d.status == eng.STATUS_ACCEPTED
    assert abs(d.offset - 6.4) <= 0.2


def test_end_to_end_no_signal_abstains():
    music = make_music(duration_s=40.0)
    video = make_recording(music, true_offset=5.1, music_gain=0.0,
                           noise_gain=0.02, tap_gain=0.30, seed=32)
    d = eng.decide_alignment(video, music)
    assert d.status == eng.STATUS_ABSTAINED


def _write_wav(path, y, sr=SR):
    pcm = (np.clip(y, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def test_find_offset_v2_file_path_accepts_and_abstains(tmp_path):
    # 45 s music at offset +5.0 keeps the usable overlap (~40 s) safely
    # above the 30 s CASE E floor (30 s media would sit exactly on it).
    music = make_music(duration_s=45.0)
    strong = make_recording(music, true_offset=5.0, music_gain=0.5,
                            noise_gain=0.004, seed=41)
    noise_only = make_recording(music, true_offset=5.0, music_gain=0.0,
                                noise_gain=0.02, tap_gain=0.3, seed=42)
    wav_m = tmp_path / "music.wav"
    wav_v = tmp_path / "video.wav"
    wav_n = tmp_path / "noise.wav"
    _write_wav(wav_m, music)
    _write_wav(wav_v, strong)
    _write_wav(wav_n, noise_only)

    d = eng.find_offset_v2(str(wav_v), str(wav_m))
    assert d.status == eng.STATUS_ACCEPTED, d.reason_code
    assert abs(d.offset - 5.0) <= 0.2

    d2 = eng.find_offset_v2(str(wav_n), str(wav_m))
    assert d2.status == eng.STATUS_ABSTAINED
