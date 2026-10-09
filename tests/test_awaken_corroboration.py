"""Candidate-only rescue, waveform sign/linear lags, and fail-closed safety."""
from __future__ import annotations
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import librosa
import numpy as np
import pytest

import alignment_engine_v2 as eng
from alignment_waveform import phat_window, verify_candidate


@pytest.mark.parametrize("shift",[-137,0,181])
def test_phat_linear_lag_sign_and_unequal_lengths(shift):
    m = np.random.default_rng(12).normal(size=12000)
    v = np.r_[np.zeros(shift),m,np.zeros(90)] if shift>=0 else m[-shift:]
    r = phat_window(v,m,1000)
    assert r["available"]
    assert r["lag_s"] == pytest.approx(shift/1000,abs=0.001)


def audio_pair(offset=5, duration=100, sr=3000):
    rng = np.random.default_rng(345)
    m = rng.normal(0,0.1,int(duration*sr))
    if offset>=0:
        v = np.r_[rng.normal(0,0.001,round(offset*sr)),m]
    else:
        v = m[round(-offset*sr):]
    return v,m,sr


@pytest.mark.parametrize("offset",[-4.3,0,5.2])
def test_disjoint_waveform_windows_verify_both_offset_signs(offset):
    v,m,sr = audio_pair(offset)
    r = verify_candidate(v,m,sr,offset,eng.DEFAULT_POLICY)
    assert r["passed"],r
    assert len(r["windows"])==4
    for a,b in zip(r["windows"],r["windows"][1:]):
        assert a["reference_start_s"]+a["duration_s"]<=b["reference_start_s"]+1/sr


def test_one_unsupported_window_prevents_rescue():
    v,m,sr = audio_pair()
    v[5*sr:30*sr] = np.random.default_rng(981).normal(0,0.1,25*sr)
    r = verify_candidate(v,m,sr,5,eng.DEFAULT_POLICY)
    assert not r["passed"]
    assert r["windows"][0]["failed_checks"]


def test_strong_waveform_at_different_offset_does_not_refine_candidate():
    v,m,sr = audio_pair()
    r = verify_candidate(v,m,sr,5.5,eng.DEFAULT_POLICY)
    assert not r["passed"]
    assert "window_1:offset_disagreement" in r["failed_checks"]


@pytest.mark.parametrize("mode",["silence","nan","short"])
def test_unusable_audio_cannot_corroborate(mode):
    v,m,sr = audio_pair(duration=20 if mode=="short" else 100)
    if mode=="silence":
        v[:] = 0
    if mode=="nan":
        v[15*sr] = np.nan
    r = verify_candidate(v,m,sr,5,eng.DEFAULT_POLICY)
    assert not r["passed"]


def primary_fixture():
    sr,hop,nv=3000,60,6500
    curve=np.tile([-1.0,1.0],6500)
    idx=eng._offset_to_index(5,nv,hop,sr)
    curve[idx]=25
    f=eng.FamilyResult("pcen_hpss",eng.FAMILY_PCEN,curve,nv,25,0,
        features=(np.ones((1,nv)),np.ones((1,5000))))
    fs=[f]
    d=eng.decide_from_families(fs,sr,hop,None,130,100)
    assert d.reason_code==eng.ABSTAIN_PRIMARY_NOT_CORROBORATED
    return d,fs,sr,hop


def test_primary_candidate_requires_real_temporal_features():
    d,fs,sr,hop=primary_fixture()
    fs[0].features=None
    v,m,_=audio_pair(sr=sr)
    out=eng._apply_waveform_corroboration(d,fs,v,m,eng.DEFAULT_POLICY,sr,hop,130,100)
    assert not out.accepted
    c=out.evidence["waveform_corroboration"]["candidates"][0]
    assert "temporal_features_unavailable" in c["failed_checks"]
    assert c["waveform"] is None


def test_candidate_concentration_rejects_even_perfect_waveform(monkeypatch):
    d,fs,sr,hop=primary_fixture()
    fv,fm=fs[0].features
    fv[:,1750:1800]=1000  # music 30 s + candidate 5 s
    monkeypatch.setattr(eng,"verify_candidate",lambda *args: pytest.fail("verifier reached"))
    out=eng._apply_waveform_corroboration(d,fs,None,None,eng.DEFAULT_POLICY,sr,hop,130,100)
    assert not out.accepted
    c=out.evidence["waveform_corroboration"]["candidates"][0]
    assert eng.ABSTAIN_CONCENTRATED_EVIDENCE in c["failed_checks"]


def test_comparable_spectral_competitor_prevents_waveform_rescue(monkeypatch):
    d,fs,sr,hop=primary_fixture()
    curve=np.tile([-1.0,1.0],6500)
    curve[eng._offset_to_index(20,6500,hop,sr)]=24.5
    fs.append(eng.FamilyResult("pcen",eng.FAMILY_PCEN,curve,6500,24.5,0,
        features=(np.ones((1,6500)),np.ones((1,5000)))))
    d=eng.decide_from_families(fs,sr,hop,None,130,100)
    assert d.reason_code==eng.ABSTAIN_PRIMARY_NOT_CORROBORATED
    monkeypatch.setattr(eng,"verify_candidate",lambda *args: pytest.fail("verifier reached"))
    out=eng._apply_waveform_corroboration(d,fs,None,None,eng.DEFAULT_POLICY,sr,hop,130,100)
    assert not out.accepted
    assert all("comparable_pcen_competitor" in c["failed_checks"]
        for c in out.evidence["waveform_corroboration"]["candidates"])


def test_verifier_exception_preserves_abstention(monkeypatch):
    d,fs,sr,hop=primary_fixture()
    def fail(*args):
        raise RuntimeError("a private input path")
    monkeypatch.setattr(eng,"verify_candidate",fail)
    v,m,_=audio_pair(sr=sr)
    out=eng._apply_waveform_corroboration(d,fs,v,m,eng.DEFAULT_POLICY,sr,hop,130,100)
    assert not out.accepted and out.offset is None
    assert "private input" not in json.dumps(out.as_dict())
    assert "waveform_error:RuntimeError" in out.evidence["waveform_corroboration"]["candidates"][0]["failed_checks"]


@pytest.mark.parametrize("reason",[eng.ABSTAIN_AMBIGUOUS_CLUSTER,
    eng.ABSTAIN_CONCENTRATED_EVIDENCE,eng.ABSTAIN_INSUFFICIENT_OVERLAP,
    eng.ABSTAIN_NO_CLUSTER_MEETS_FLOORS])
def test_waveform_never_overrides_other_rejection_reasons(reason,monkeypatch):
    d,fs,sr,hop=primary_fixture()
    d.reason_code=reason
    monkeypatch.setattr(eng,"verify_candidate",lambda *args: pytest.fail("verifier reached"))
    assert eng._apply_waveform_corroboration(d,fs,None,None,eng.DEFAULT_POLICY,sr,hop,130,100) is d
    assert not d.accepted


def test_corroboration_keeps_owned_spectral_offset():
    d,fs,sr,hop=primary_fixture()
    v,m,_=audio_pair(offset=5.009,sr=sr)
    out=eng._apply_waveform_corroboration(d,fs,v,m,eng.DEFAULT_POLICY,sr,hop,130,100)
    assert out.accepted
    assert out.offset==5
    assert out.reason_code==eng.ACCEPT_PRIMARY_WITH_WAVEFORM
    assert out.evidence["temporal_support"]["applied"]


def test_inconsistent_window_lags_fail_even_with_strong_peaks(monkeypatch):
    import alignment_waveform as wave
    monkeypatch.setattr(wave,"measure",lambda *args: {"available":True,"windows":[
        {"available":True,"offset_s":5+x,"lag_s":x,"z":25,"margin":4}
        for x in (-0.04,0.04,-0.04,0.04)]})
    out=wave.verify_candidate(None,None,3000,5,eng.DEFAULT_POLICY)
    assert out["failed_checks"]==["inconsistent_windows"]


def test_real_awaken_positive_and_baseline_abstention():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/"tests/fixtures/awaken_positive.json").read_text())
    supplied=os.environ.get("RHYTHMALIGN_AWAKEN_REPRO_ZIP")
    if supplied:
        with zipfile.ZipFile(supplied) as archive:
            blobs={name:archive.read(name) for name in manifest["audio_sha256"]}
    else:
        bundle=root/"results/awaken/bundle"
        if not all((bundle/name).exists() for name in manifest["audio_sha256"]):
            pytest.skip("Set RHYTHMALIGN_AWAKEN_REPRO_ZIP to the privately supplied fixture")
        blobs={name:(bundle/name).read_bytes() for name in manifest["audio_sha256"]}
    audio={}
    for name,sha in manifest["audio_sha256"].items():
        assert hashlib.sha256(blobs[name]).hexdigest()==sha
        audio[name],sr=librosa.load(io.BytesIO(blobs[name]),sr=None,mono=True)
        assert sr==manifest["sample_rate"]
    v,m=audio["recording_22k.wav"],audio["song_22k.wav"]
    baseline=eng.decide_alignment(v,m,policy=dataclasses.replace(
        eng.DEFAULT_POLICY,waveform_corroboration=False))
    assert baseline.reason_code==manifest["baseline_reason"]
    d=eng.decide_alignment(v,m)
    assert d.accepted and d.reason_code==eng.ACCEPT_PRIMARY_WITH_WAVEFORM
    assert abs(d.offset-manifest["reference_offset_s"])<=manifest["tolerance_s"]
    assert d.evidence["temporal_support"]["applied"]
    assert d.evidence["temporal_support"]["top_bin_share"]<=eng.DEFAULT_POLICY.max_top_bin_share
    assert d.evidence["waveform_corroboration"]["n_verified"]==1
