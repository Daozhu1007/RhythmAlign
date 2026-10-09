"""Run the frozen repair against historical and source-disjoint populations.

Reads all historical labels/media without changing their original artifacts.
All results are neutral case IDs and numerical evidence under results/awaken.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.awaken_corroboration.study import eng as old, common, OUT, SR, HOP, cached, write
import alignment_engine_v2 as eng
import librosa
import numpy as np

FROZEN_RESEARCH = "59131c79afa4cd956174944bf6025230cf9b4e4f"


def contract():
    p = json.loads((OUT / "frozen_policy.json").read_text())["selected"]
    for key, actual in (("z_floor", eng.DEFAULT_POLICY.waveform_z_floor),
                        ("margin_floor", eng.DEFAULT_POLICY.waveform_margin_floor),
                        ("offset_tolerance_s", eng.DEFAULT_POLICY.waveform_offset_tol_s),
                        ("max_spread_s", eng.DEFAULT_POLICY.waveform_max_spread_s)):
        assert p[key] == actual
    return hashlib.sha256((OUT / "frozen_policy.json").read_bytes()).hexdigest()


def decision_summary(d):
    return {"status": d.status, "offset": d.offset, "reason": d.reason_code,
            "temporal_support": d.evidence.get("temporal_support"),
            "waveform_corroboration": d.evidence.get("waveform_corroboration")}


def compare(cid, group, v, m, fs=None, gt=None, tolerance=0.15, negative=False):
    t0 = time.perf_counter()
    if fs is None:
        # Observe the real production pipeline; never substitute generators.
        captured = []
        native = eng._run_generators
        def observed(*args):
            result = native(*args)
            captured.extend(result)
            return result
        eng._run_generators = observed
        try:
            after = eng.decide_alignment(v, m, sr=SR)
        finally:
            eng._run_generators = native
        fs = captured
    else:
        after = eng.decide_from_families(fs, SR, HOP, None, len(v)/SR, len(m)/SR)
        after = eng._apply_waveform_corroboration(after, fs, v, m, eng.DEFAULT_POLICY,
            SR, HOP, len(v)/SR, len(m)/SR)
        after = eng._apply_temporal_support(after, fs, eng.DEFAULT_POLICY, SR, HOP)
    assert not any(f.error for f in fs), cid
    before = old.decide_from_families(fs, SR, HOP, None, len(v)/SR, len(m)/SR)
    before = old._apply_temporal_support(before, fs, old.DEFAULT_POLICY, SR, HOP)
    wrong = after.accepted and (negative or (gt is not None and abs(after.offset-gt)>tolerance))
    preserved = (not before.accepted or (after.accepted and after.offset == before.offset
                                        and after.reason_code == before.reason_code))
    result = {"case_id": cid, "group": group, "gt": gt, "tolerance_s": tolerance,
              "negative": negative, "before": decision_summary(before),
              "after": decision_summary(after), "wrong_accept": bool(wrong),
              "old_accept_preserved": preserved, "runtime_s": time.perf_counter()-t0}
    print(cid, before.reason_code, "->", after.reason_code, "wrong", wrong, flush=True)
    assert not wrong, result
    assert preserved, result
    return result


def historical_positives():
    store = common.FeatureStore(common.Sources())
    rows = []
    for split in ("calibration", "holdout"):
        for c in common.iter_split_cases(split):
            if c["kind"] != "positive":
                continue
            v, m = common.semi_case_mix(c, store), store.sources.audio("tracks", c["target"])
            rows.append(compare(c["case_id"], split+"_"+c["level"], v, m, gt=c["offset_s"]))
            write("validation_positives.json", {"rows": rows, "policy_sha256": contract()})
    for c in common.real_cases():
        if c["class"] == "negative_mismatch":
            continue
        v, m = common.real_case_audio(c, store.sources)
        rows.append(compare(c["case_id"], c["class"], v, m,
            gt=c.get("expected_offset"), tolerance=c.get("tolerance", 0.15)))
        write("validation_positives.json", {"rows": rows, "policy_sha256": contract()})
    assert len(rows) == 85


def negatives():
    store = common.FeatureStore(common.Sources())
    sources = store.sources
    rows = []
    def add(*args, **kwargs):
        rows.append(compare(*args, **kwargs, negative=True))
        write("validation_negatives.json", {"rows": rows, "policy_sha256": contract()})
    # All 380 directed pairs, including the old DEV/TEST populations and
    # cross-split pairs. No policy tuning is permitted after opening these.
    for q in sorted(sources.mapping["tracks"]):
        for r in sorted(sources.mapping["tracks"]):
            if q != r:
                add(q+"_x_"+r, "clean_wrong_song", sources.audio("tracks",q),
                    sources.audio("tracks",r), cached(store,"tracks",q,"tracks",r))
    for c in common.real_cases():
        if c["class"] == "negative_mismatch":
            v, m = common.real_case_audio(c,sources)
            add(c["case_id"],"real_mismatch",v,m)
    for split in ("calibration","holdout"):
        for c in common.iter_split_cases(split):
            if c["kind"] != "positive":
                add(c["case_id"],c["kind"],common.semi_case_mix(c,store),
                    sources.audio("tracks",c["target"]))
    v, _ = librosa.load(OUT/"bundle/recording_22k.wav",sr=None)
    for tid in sorted(sources.mapping["tracks"]):
        add("awaken_x_"+tid,"awaken_wrong_reference",v,sources.audio("tracks",tid))
    # Cached-vs-production curve equivalence on a complete real pair.
    q,r = "tr_lingduihua","tr_yanwulieche"
    expected = eng._run_generators(sources.audio("tracks",q),sources.audio("tracks",r),SR,HOP)
    actual = cached(store,"tracks",q,"tracks",r)
    assert all(np.array_equal(a.curve,b.curve) for a,b in zip(actual,expected))
    write("cache_equivalence.json", {"all_four_curves_bit_equal": True})


def acoustic():
    # A historically used, source-disjoint acoustic set. Reuse its frozen
    # labels, but do not relabel it as fresh confirmatory product evidence.
    raw = subprocess.check_output(["git","show",FROZEN_RESEARCH+
        ":experiments/applied_system/final_pack/results/final_benchmark_manifest.json"],cwd=ROOT)
    manifest = json.loads(raw)
    rows = []
    for c in manifest["body"]["cases"]:
        paths = [(ROOT/c["trimmed_input_path"],c["trimmed_input_sha256"]),
                 (ROOT/c["reference_path"],c["reference_sha256"])]
        for path, sha in paths:
            assert hashlib.sha256(path.read_bytes()).hexdigest()==sha, c["case_id"]
        v = common.Sources().audio_from_path(paths[0][0])
        m = common.Sources().audio_from_path(paths[1][0])
        rows.append(compare(c["case_id"],"acoustic_"+c["condition"],v,m,
            gt=c["gt_offset_s"],negative=c["pair_type"]=="WRONG_REFERENCE"))
        write("validation_acoustic.json", {"rows": rows,"policy_sha256":contract(),
            "historical_manifest_git_commit":FROZEN_RESEARCH,
            "historical_manifest_sha256":hashlib.sha256(raw).hexdigest()})
    assert len(rows)==50


def adversarial():
    from experiments.awaken_corroboration.adversarial import build_pair
    from experiments.low_snr_alignment.synthetic_eval import make_music,make_recording
    rows=[]
    for count in (1,2,4):
        for gain in (1,4):
            v,m=build_pair(count,gain)
            rows.append(compare(f"shared_events_{count}_gain_{gain}","shared_events",v,m,negative=True))
    music=make_music()
    for seed in range(100,130):
        v=make_recording(music,true_offset=0,music_gain=0,
            noise_gain=0.12,tap_gain=0.3,seed=seed)
        rows.append(compare(f"null_{seed}","no_shared_signal",v,music,negative=True))
    write("validation_adversarial.json",{"rows":rows,"policy_sha256":contract()})


def product():
    import auto_sync
    import ui_main
    sources=common.Sources()
    v=str(OUT/"bundle/recording_22k.wav")
    m=str(OUT/"bundle/song_22k.wav")
    exports=[]
    def forbidden(*args,**kwargs):
        raise AssertionError("legacy fallback reached")
    auto_sync.find_offset=forbidden
    ui_main.mix_and_export=lambda **kwargs:exports.append(kwargs["offset"])
    rows=[]
    assert ui_main.find_offset_v2 is eng.find_offset_v2
    for cid,reference,expect in (("awaken_positive",m,True),
        ("awaken_wrong_reference",str(sources.path_of("tracks","tr_bai39")),False)):
        count=len(exports)
        w=ui_main.SyncWorker(dict(v_path=v,m_path=reference,
            save_path=str(OUT/"not_exported.mp4"),orig_vol=1,music_vol=1,
            manual_offset=0,use_gpu=False,bitrate="10000k",open_folder=False,
            stream_copy=True))
        finished=[]
        w.finished_signal.connect(lambda *event:finished.append(event))
        w.run()
        assert finished and finished[-1][0]==expect,finished
        assert len(exports)-count==int(expect)
        rows.append({"case_id":cid,"decision":w.alignment_decision,
                     "intercepted_export_calls":len(exports)-count})
    write("validation_product.json",{"rows":rows,"policy_sha256":contract(),
        "input_scope":"decoded WAV fixture through real file entry/SyncWorker; original MP4 not supplied",
        "legacy_calls":0,"physical_exports":0})
    store=common.FeatureStore(sources)
    v,m=sources.audio("recordings","haiditan_ds_1"),sources.audio("tracks","tr_hongzhoutian")
    residual=compare("unresolved_room_grid","unresolved_identity",v,m)
    assert residual["before"]["status"]==residual["after"]["status"]=="accepted"
    write("unresolved_residual.json",residual)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("population",choices=["positives","negatives","acoustic","adversarial","product"])
    args = p.parse_args()
    contract()
    {"positives":historical_positives,"negatives":negatives,"acoustic":acoustic,
     "adversarial":adversarial,"product":product}[args.population]()
