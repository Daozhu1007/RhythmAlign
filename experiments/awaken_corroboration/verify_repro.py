"""Independently inspect the supplied PCM fixture with frozen v1.2.1."""
from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import librosa
import numpy as np
from experiments.awaken_corroboration.study import eng, OUT, SR, HOP, write
from experiments.awaken_corroboration import waveform_probe as wave


def main():
    v, sr = librosa.load(OUT / "bundle/recording_22k.wav", sr=None)
    m, mr = librosa.load(OUT / "bundle/song_22k.wav", sr=None)
    assert sr == mr == SR
    fs = eng._run_generators(v, m, sr, HOP)
    d = eng.decide_from_families(fs, sr, HOP, None, len(v)/sr, len(m)/sr)
    assert d.reason_code == eng.ABSTAIN_PRIMARY_NOT_CORROBORATED
    strongest = max(d.clusters, key=lambda c: max(f["z_at_cluster"] for f in c["families"].values()))
    offset = strongest["families"][eng.FAMILY_PCEN]["supplier_peak_offset_s"]
    f = next(f for f in fs if f.method == "onset")
    idx = eng._offset_to_index(offset, f.n_video_frames, HOP, sr)
    peaks = eng._independent_peak_indices(f.curve, int(1.5*sr/HOP))
    nearby = [int(p) for p in peaks if abs(eng._index_to_offset(p, f.n_video_frames, HOP, sr)-offset) <= 0.15]
    i0, i1 = max(0, idx-6), min(len(f.curve), idx+7)
    trial = dataclasses.replace(d, status="accepted", offset=offset, evidence=dict(d.evidence))
    eng._apply_temporal_support(trial, fs, eng.DEFAULT_POLICY, sr, HOP)
    topn = {}
    for n in (4, 8, 16, 64, len(peaks)):
        policy = dataclasses.replace(eng.DEFAULT_POLICY, top_candidates_per_family=n)
        check = eng.decide_from_families(fs, sr, HOP, policy, len(v)/sr, len(m)/sr)
        topn[str(n)] = {"status": check.status, "reason": check.reason_code}
    payload = {"audio_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (OUT / "bundle").glob("*.wav")},
               "decision": d.as_dict(),
               "onset": {"z_at_pcen_offset": eng._z_at_index(f.curve, idx),
                         "max_z_within_cluster_tolerance": eng._z_at_index(f.curve, i0+int(np.argmax(f.curve[i0:i1]))),
                         "nearby_independent_peak_ranks": [int(np.where(peaks==p)[0][0])+1 for p in nearby]},
               "candidate_count_ablation": topn,
               "diagnostic_temporal_support": trial.evidence["temporal_support"],
               "gcc_phat_full_rate": wave.phat_window(v,m,sr,30/(len(m)/sr)),
               "gcc_phat_full_recording_windows": [
                   {"reference_start_s": start,
                    **wave.phat_window(v, m[int(start*sr):int((start+25)*sr)], sr, 1.0)}
                   for start in (10, 40, 70, 100)],
               "gcc_phat_distributed": wave.measure(v,m,sr,offset)}
    write("reproduction.json", payload)
    print(payload["onset"])
    print(payload["candidate_count_ablation"])
    print(payload["gcc_phat_full_rate"])
    print(payload["gcc_phat_distributed"])


if __name__ == "__main__":
    main()
