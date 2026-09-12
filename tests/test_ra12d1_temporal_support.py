"""RA-1.2D1 temporal-support gate tests.

Media-independent regression coverage for the RA-1.2D1 safeguard:

- the Astra release blocker MECHANISM (one brief shared hit sequence, the
  "one local event only" case) is verified on real pipeline PCEN features:
  the gate downgrades the ACCEPT to ABSTAIN_CONCENTRATED_EVIDENCE with the
  dominant bin at the event, and passes the same features when disabled;
- distributed true matches are still accepted end-to-end (CASE A / CASE B
  paths, including a low-SNR recording-style case in the spirit of the
  零对话 regression);
- legacy hard negatives (no-signal and wrong-song recordings) remain
  abstained;
- unit-level coverage of the gate plumbing: distributed features stay
  accepted, single-bin concentration abstains, empty overlap yields
  ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT, missing features skip the gate.

The synthetic fixture is the media-independent stand-in for the archived
real-media blocker tr_lingduihua -> tr_yanwulieche (verified against the
real pair in experiments/ra12d1_temporal_support/).
"""
import dataclasses

import numpy as np
import pytest

import alignment_engine_v2 as eng
from experiments.low_snr_alignment.synthetic_eval import (
    make_music,
    make_recording,
)

SR = 22050


def make_other_song(duration_s=90.0, seed=5):
    """A genuinely DIFFERENT song from make_music: different tempo, key,
    chord set, bass pattern and drum texture. (make_music's seed only
    varies snare noise — two seeds of it are the same song, which the
    engine correctly treats as distributed content at offset 0.)"""
    rng = np.random.default_rng(seed)
    n = int(duration_s * SR)
    t = np.arange(n) / SR
    bpm = 92.0
    beat = 60.0 / bpm
    bar = beat * 4
    chords = [
        (220.00, 261.63, 329.63),   # Am
        (246.94, 293.66, 369.99),   # Bm
        (164.81, 196.00, 246.94),   # Em
        (293.66, 349.23, 440.00),   # D
    ]
    y = np.zeros(n)
    n_bars = int(np.ceil(duration_s / bar))
    for b in range(n_bars):
        chord = chords[(b * 3) % len(chords)]  # non-cyclic progression
        t0 = b * bar
        i0 = int(t0 * SR)
        i1 = min(n, int((t0 + bar) * SR))
        tt = t[i0:i1] - t0
        y[i0:i1] += 0.20 * sum(np.sin(2 * np.pi * f * tt) for f in chord)
        for beat_i in (1, 3):  # off-beat bass (different from make_music)
            bs = int((t0 + beat_i * beat) * SR)
            be = min(n, bs + int(beat * SR))
            if bs < n:
                tb = t[bs:be]
                y[bs:be] += 0.32 * np.sin(
                    2 * np.pi * chord[2] / 4 * (tb - t0 - beat_i * beat))
    # shaker texture instead of kick/snare
    for st in np.arange(0.0, duration_s, beat / 4):
        i0 = int(st * SR)
        i1 = min(n, i0 + int(0.03 * SR))
        if i0 < n:
            y[i0:i1] += 0.10 * rng.standard_normal(i1 - i0) * \
                np.exp(-(t[i0:i1] - st) * 120)
    peak = np.max(np.abs(y))
    return (y / peak * 0.9).astype(np.float32)


def _concentrated_pair(event_video_start_s, seed=61):
    """The Astra blocker mechanism, media-independently: the query video is
    a near-silent recording that contains the reference music ONLY as one
    brief loud hit sequence (brief common content -> strong global peak ->
    multi-family agreement with no distributed support). Returns
    (video, music, expected_offset_s)."""
    music = make_music(duration_s=90.0, seed=7)
    event = _hit_sequence(seed=4)
    music = music.copy()
    m0 = int(30.0 * SR)
    music[m0:m0 + len(event)] += event
    video = make_recording(make_other_song(duration_s=90.0, seed=5),
                           true_offset=0.0, music_gain=0.0,
                           noise_gain=0.0005, tap_gain=0.0, seed=seed)
    i0 = int(event_video_start_s * SR)
    video[i0:i0 + len(event)] += event
    return video, music, event_video_start_s - 30.0


def _hit_sequence(gain=0.9, seed=4):
    """A ~2 s sequence of six loud hits (broadband click + chord stab)."""
    rng = np.random.default_rng(seed)
    chords = [(185.0, 233.1, 277.2), (233.1, 277.2, 349.2)]
    parts = []
    for k in range(6):
        n = int(0.33 * SR)
        tt = np.arange(n) / SR
        seg = 0.8 * rng.standard_normal(n) * np.exp(-tt * 60)
        seg = seg + sum(np.sin(2 * np.pi * f * tt)
                        for f in chords[k % 2]) * np.exp(-tt * 10)
        parts.append(seg)
    y = np.concatenate(parts)
    return y / np.max(np.abs(y)) * gain


def _accept_floors_policy(max_top_bin_share):
    """Evidence floors low enough that the synthetic concentrated candidate
    qualifies (the fixture does not reach the calibrated real-media
    floors); the temporal-support parameter is the A/B knob under test."""
    return eng.DecisionPolicy(
        tonal_z_floor=2.0, pcen_z_floor=2.5, pcen_primary_z_floor=5.0,
        onset_corroboration_z_floor=0.5, margin_floor_b=1.2,
        max_top_bin_share=max_top_bin_share)


@pytest.mark.parametrize("event_start", [2.0, 44.5],
                         ids=["early_event", "middle_event"])
def test_gate_rejects_one_local_event_on_real_pipeline_features(
        event_start):
    """The Astra blocker mechanism, media-independently: the video is
    silent except ONE brief shared hit sequence. The deciding PCEN member's
    net correlation at the proposed offset concentrates in the event bins,
    and the gate must downgrade the ACCEPT to
    ABSTAIN_CONCENTRATED_EVIDENCE with the dominant bin at the event.

    (The accept step itself is the existing CASE A/B floors' contract,
    covered by test_alignment_engine_v2; this test pins the gate's causal
    effect on real pipeline features at the real proposed offset.)
    """
    video, music, expected_offset = _concentrated_pair(event_start)
    fv = eng._pcen_features(video, SR, 512)
    fm = eng._pcen_features(music, SR, 512)
    decision = _accepted_decision(offset=expected_offset)
    family_results = [eng.FamilyResult(
        method="pcen", family=eng.FAMILY_PCEN, curve=np.zeros(1),
        n_video_frames=1, z=12.0, runtime_s=0.0, features=(fv, fm))]
    out = eng._apply_temporal_support(
        decision, family_results, _accept_floors_policy(0.25), SR, 512)
    assert out.status == eng.STATUS_ABSTAINED
    assert out.reason_code == eng.ABSTAIN_CONCENTRATED_EVIDENCE
    assert out.offset is None
    ts = out.evidence["temporal_support"]
    assert ts["applied"] is True
    assert ts["top_bin_share"] > 0.25
    # bins are in reference (music) time; the shared event lives at 30 s
    assert abs(ts["peak_bin_start_s"] - 30.0) <= 1.5


def test_gate_passes_same_fixture_when_disabled():
    """Mechanism proof: with max_top_bin_share=1.01 the SAME concentrated
    fixture passes the gate — the rejection is caused by the
    temporal-support rule, not by the decision plumbing."""
    video, music, expected_offset = _concentrated_pair(44.5)
    fv = eng._pcen_features(video, SR, 512)
    fm = eng._pcen_features(music, SR, 512)
    decision = _accepted_decision(offset=expected_offset)
    family_results = [eng.FamilyResult(
        method="pcen", family=eng.FAMILY_PCEN, curve=np.zeros(1),
        n_video_frames=1, z=12.0, runtime_s=0.0, features=(fv, fm))]
    out = eng._apply_temporal_support(
        decision, family_results, _accept_floors_policy(1.01), SR, 512)
    assert out.status == eng.STATUS_ACCEPTED
    assert abs(out.offset - expected_offset) <= 1e-9


# ---------------------------------------------------------------------------
# distributed true matches are retained
# ---------------------------------------------------------------------------


def test_distributed_case_b_accept_retained_with_support_evidence():
    music = make_music(duration_s=45.0)
    video = make_recording(music, true_offset=5.0, music_gain=0.5,
                           noise_gain=0.004, seed=41)
    d = eng.decide_alignment(video, music)
    assert d.status == eng.STATUS_ACCEPTED, d.reason_code
    assert abs(d.offset - 5.0) <= 0.2
    ts = d.evidence["temporal_support"]
    assert ts["applied"] is True
    assert ts["top_bin_share"] <= 0.25
    assert ts["n_bins"] >= 30


def test_low_snr_recording_accept_retained():
    """Low-SNR true match (the spirit of the 零对话 CASE B regression):
    quiet music under noise and taps must stay accepted."""
    music = make_music(duration_s=60.0)
    video = make_recording(music, true_offset=12.4, music_gain=0.12,
                           noise_gain=0.02, tap_gain=0.3, seed=63)
    d = eng.decide_alignment(video, music)
    assert d.status == eng.STATUS_ACCEPTED, d.reason_code
    assert abs(d.offset - 12.4) <= 0.3
    assert d.evidence["temporal_support"]["applied"] is True


def test_legacy_hard_negatives_still_abstain():
    music = make_music(duration_s=45.0, seed=7)
    impostor = make_other_song(duration_s=45.0, seed=5)
    noise_only = make_recording(music, true_offset=5.0, music_gain=0.0,
                                noise_gain=0.02, tap_gain=0.3, seed=42)
    wrong_song = make_recording(impostor, true_offset=0.0, music_gain=0.5,
                                noise_gain=0.004, seed=43)
    assert eng.decide_alignment(noise_only, music).status == \
        eng.STATUS_ABSTAINED
    assert eng.decide_alignment(wrong_song, music).status == \
        eng.STATUS_ABSTAINED


def test_decide_from_families_seam_does_not_gate():
    """The synthetic-curve seam keeps its pre-RA-1.2D1 contract: no
    temporal-support evidence is attached when no features are present."""
    idx = 500
    tonal = eng.FamilyResult(
        "hybrid", eng.FAMILY_TONAL, _peak_curve(idx), 1000, 5.0, 0.0)
    pcen = eng.FamilyResult(
        "pcen_hpss", eng.FAMILY_PCEN, _peak_curve(idx), 1000, 5.0, 0.0)
    d = eng.decide_from_families([tonal, pcen], 22050, 512, None,
                                 90.0, 90.0)
    assert d.status == eng.STATUS_ACCEPTED
    assert "temporal_support" not in d.evidence


def _peak_curve(idx, n=1000, peak=12.0, width=2, seed=0):
    rng = np.random.default_rng(seed)
    curve = rng.standard_normal(n)
    curve[idx - width:idx + width] += peak
    return curve


# ---------------------------------------------------------------------------
# unit-level gate behaviour on crafted features
# ---------------------------------------------------------------------------


def _accepted_decision(offset):
    cluster = {
        "offset_s": offset,
        "overlap_s": 60.0,
        "candidates": [{
            "method": "pcen", "family": eng.FAMILY_PCEN,
            "offset_s": offset, "z": 12.0, "peak_margin": 2.0,
            "usable_overlap_s": 60.0, "runtime_s": 0.0,
            "top_competing_offsets_s": [], "notes": {},
        }],
        "families": {
            eng.FAMILY_PCEN: {"methods": ["pcen"], "z_at_cluster": 12.0,
                              "margin_at_cluster": 2.0,
                              "best_member_offset_s": offset},
        },
    }
    return eng.AlignmentDecision(
        status=eng.STATUS_ACCEPTED, offset=offset,
        reason_code=eng.ACCEPT_PRIMARY_WITH_CORROBORATION,
        evidence={}, clusters=[cluster], policy={}, runtime_s=0.0)


def _pcen_family_result(fv, fm):
    return eng.FamilyResult(
        method="pcen", family=eng.FAMILY_PCEN,
        curve=np.zeros(4), n_video_frames=4, z=12.0, runtime_s=0.0,
        features=(fv, fm))


def test_unit_gate_distributed_features_stay_accepted():
    rng = np.random.default_rng(5)
    # smooth (strongly autocorrelated) content: net correlation at the
    # true shift is strongly positive, as for real accepted candidates
    fm = np.cumsum(rng.standard_normal((8, 4000)), axis=1)
    fm = (fm - fm.mean(axis=1, keepdims=True)) / (
        fm.std(axis=1, keepdims=True) + 1e-9)
    fv = np.zeros((8, 4000))
    shift = -50
    fv[:, -shift:] = fm[:, :4000 + shift]
    decision = _accepted_decision(offset=shift * 512 / 22050)
    fr = _pcen_family_result(fv, fm)
    out = eng._apply_temporal_support(
        decision, [fr], eng.DEFAULT_POLICY, 22050, 512)
    assert out.status == eng.STATUS_ACCEPTED
    assert out.evidence["temporal_support"]["applied"] is True
    assert out.evidence["temporal_support"]["top_bin_share"] <= 0.25


def test_unit_gate_single_bin_concentration_abstains():
    rng = np.random.default_rng(6)
    fm = rng.standard_normal((8, 400))
    fv = np.zeros((8, 400))
    # support exists at shift -50 for exactly ONE bin worth of frames
    shift = -50
    fv[:, 100 + shift:112 + shift] = fm[:, 100:112] * 10.0
    decision = _accepted_decision(offset=shift * 512 / 22050)
    fr = _pcen_family_result(fv, fm)
    out = eng._apply_temporal_support(
        decision, [fr], eng.DEFAULT_POLICY, 22050, 512)
    assert out.status == eng.STATUS_ABSTAINED
    assert out.reason_code == eng.ABSTAIN_CONCENTRATED_EVIDENCE
    assert out.offset is None
    assert out.evidence["temporal_support"]["top_bin_share"] > 0.25


def test_unit_gate_empty_overlap_abstains_insufficient():
    fm = np.ones((8, 400))
    fv = np.ones((8, 400))
    # offset maps the entire music outside the video -> empty overlap
    decision = _accepted_decision(offset=500.0)
    fr = _pcen_family_result(fv, fm)
    out = eng._apply_temporal_support(
        decision, [fr], eng.DEFAULT_POLICY, 22050, 512)
    assert out.status == eng.STATUS_ABSTAINED
    assert out.reason_code == eng.ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT


def test_unit_gate_skips_when_features_missing():
    decision = _accepted_decision(offset=0.0)
    fr = eng.FamilyResult(method="pcen", family=eng.FAMILY_PCEN,
                          curve=np.zeros(4), n_video_frames=4, z=12.0,
                          runtime_s=0.0, features=None)
    out = eng._apply_temporal_support(
        decision, [fr], eng.DEFAULT_POLICY, 22050, 512)
    assert out.status == eng.STATUS_ACCEPTED
    assert out.evidence["temporal_support"]["applied"] is False
