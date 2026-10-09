"""Fresh-process Awaken determinism, diagnostic observations, and media QA."""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import alignment_engine_v2 as eng
from alignment_waveform import verify_candidate
import librosa
from experiments.awaken_corroboration.study import OUT,write


def child():
    v,sr=librosa.load(OUT/"bundle/recording_22k.wav",sr=None)
    m,mr=librosa.load(OUT/"bundle/song_22k.wav",sr=None)
    assert sr==mr==22050
    d=eng.decide_alignment(v,m)
    assert d.accepted and d.reason_code==eng.ACCEPT_PRIMARY_WITH_WAVEFORM
    cl=next(c for c in d.clusters if any(p["offset_s"]==d.offset for p in c["candidates"]))
    assert cl["case_a_failed_checks"]==["tonal_z"]
    assert cl["case_b_failed_checks"]==["onset_missing"]
    assert cl["curve_observations"]["onset"]["local_max_z"]<eng.DEFAULT_POLICY.onset_corroboration_z_floor
    assert not cl["curve_observations"]["onset"]["decision_evidence"]
    costs=[]
    for _ in range(3):
        t0=time.perf_counter()
        r=verify_candidate(v,m,sr,d.offset,eng.DEFAULT_POLICY)
        costs.append(time.perf_counter()-t0)
        assert r["passed"]
    print(json.dumps({"decision":d.as_dict(),"verifier_wall_s":costs},allow_nan=False))


def stable(data):
    if isinstance(data,dict):
        return {k:stable(v) for k,v in data.items() if k!="runtime_s"}
    if isinstance(data,list):
        return [stable(v) for v in data]
    return data


def main():
    runs=[]
    for _ in range(3):
        raw=subprocess.check_output([sys.executable,str(Path(__file__).resolve()),"--child"],cwd=ROOT)
        runs.append(json.loads(raw))
    decisions=[stable(r["decision"]) for r in runs]
    assert decisions[0]==decisions[1]==decisions[2]
    # Check both audio fixture files still match their public contract.
    fixture=json.loads((ROOT/"tests/fixtures/awaken_positive.json").read_text())
    assert all(hashlib.sha256((OUT/"bundle"/n).read_bytes()).hexdigest()==h
               for n,h in fixture["audio_sha256"].items())
    write("final_acceptance.json",{"runs":runs,"deterministic":True,
        "fixture_hashes_preserved":True,
        "canonical_decision_sha256":hashlib.sha256(json.dumps(decisions[0],sort_keys=True).encode()).hexdigest()})
    print("3/3 deterministic ACCEPT_PRIMARY_WITH_WAVEFORM",[r["decision"]["offset"] for r in runs])
    print("Verifier wall seconds",[r["verifier_wall_s"] for r in runs])


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    child() if p.parse_args().child else main()
