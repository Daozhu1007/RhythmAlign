"""DEV comparison and frozen-policy validation. Raw media stays local.

    .venv/Scripts/python experiments/awaken_corroboration/study.py dev
    .venv/Scripts/python experiments/awaken_corroboration/study.py test
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import types

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments/ra12d1_temporal_support"))
import common
from experiments.awaken_corroboration import waveform_probe as wave

BASELINE = "5527647"
OUT = ROOT / "results/awaken"
SR, HOP = common.SR, common.HOP


def baseline_module():
    source = subprocess.check_output(["git", "show", BASELINE + ":alignment_engine_v2.py"], cwd=ROOT)
    module = types.ModuleType("awaken_frozen_v121")
    sys.modules[module.__name__] = module
    exec(compile(source, "frozen_v121.py", "exec"), module.__dict__)
    return module


eng = baseline_module()


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def row(cid, group, v, m, fs=None, gt=None, tolerance=0.15):
    if fs is None:
        fs = eng._run_generators(v, m, SR, HOP)
    d = eng.decide_from_families(fs, SR, HOP, None, len(v) / SR, len(m) / SR)
    d = eng._apply_temporal_support(d, fs, eng.DEFAULT_POLICY, SR, HOP)
    if any(f.error for f in fs):
        raise AssertionError("generator error " + cid)
    proposals = []
    if d.reason_code == eng.ABSTAIN_PRIMARY_NOT_CORROBORATED:
        for cl in d.clusters:
            if cl["overlap_s"] < eng.DEFAULT_POLICY.min_overlap_s:
                continue
            if set(cl["case_b_failed_checks"]) - {"onset_missing", "onset_z"}:
                continue
            offset = cl["families"][eng.FAMILY_PCEN]["supplier_peak_offset_s"]
            # Temporal gate measures the actual owned supplier, before rescue.
            trial = dataclasses.replace(d, status="accepted", offset=offset,
                reason_code="ACCEPT_PRIMARY_WITH_CORROBORATION", evidence=dict(d.evidence))
            trial = eng._apply_temporal_support(trial, fs, eng.DEFAULT_POLICY, SR, HOP)
            temporal = trial.evidence.get("temporal_support", {})
            measurement = wave.measure(v, m, SR, offset)
            proposals.append({"offset": offset, "temporal": temporal,
                              "temporal_ok": trial.accepted and temporal.get("applied", False),
                              "waveform": measurement})
    return {"case_id": cid, "group": group, "gt": gt, "tolerance_s": tolerance,
            "before": {"status": d.status, "offset": d.offset, "reason": d.reason_code},
            "proposals": proposals}


def cached(store, qkind, qid, rkind, rid):
    fs = common.families(store.get(qkind, qid), store.get(rkind, rid))
    for f in fs:
        if f.family == eng.FAMILY_PCEN:
            f.features = (store.get(qkind, qid)[f.method], store.get(rkind, rid)[f.method])
    return fs


def run(split):
    store = common.FeatureStore(common.Sources())
    sources = store.sources
    rows = []
    def add(*args, **kwargs):
        r = row(*args, **kwargs)
        rows.append(r)
        print(r["case_id"], r["before"]["reason"], len(r["proposals"]), flush=True)
        write(split + "_raw.json", {"baseline": BASELINE, "rows": rows})
    plan_split = "calibration" if split == "dev" else "holdout"
    for c in common.iter_split_cases(plan_split):
        v = common.semi_case_mix(c, store)
        m = sources.audio("tracks", c["target"])
        add(c["case_id"], c["kind"] + "_" + c.get("level", ""), v, m,
            gt=c.get("offset_s") if c["kind"] == "positive" else None)
    # Existing real positives are preservation targets, never fresh GT.
    if split == "dev":
        for c in common.real_cases():
            v, m = common.real_case_audio(c, sources)
            add(c["case_id"], c["class"], v, m,
                gt=c.get("expected_offset"), tolerance=c.get("tolerance", 0.15))
        v, _ = librosa.load(OUT / "bundle/recording_22k.wav", sr=None)
        m, _ = librosa.load(OUT / "bundle/song_22k.wav", sr=None)
        add("awaken", "owner_confirmed_positive", v, m, gt=10.9552)
        for tid in sorted(sources.mapping["tracks"]):
            add("awaken_x_" + tid, "wrong_reference", v, sources.audio("tracks", tid))
    dev, test = common.clean_pair_rows(common.DEV_COMPONENT_A, sources)
    for c in dev if split == "dev" else test:
        q, r = c["query_track"], c["reference_track"]
        add(q + "_x_" + r, "clean_wrong_song", sources.audio("tracks", q),
            sources.audio("tracks", r), cached(store, "tracks", q, "tracks", r))
    write(split + "_raw.json", {"baseline": BASELINE, "rows": rows})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("split", choices=["dev", "test"])
    run(p.parse_args().split)
