"""RA-1.2D1 held-out evaluation of the calibrated temporal-support gate.

Runs AFTER calibrate_dev.py analyze has produced chosen_policy.json.
Everything in this script uses data NEVER examined during design:

  wrong-song TEST : directed clean pairs among the 13 tracks outside DEV
                    component A (156 pairs, includes the 4 known component-B
                    Astra wrong accepts that must flip to SAFE_ABSTAIN),
                    plus the archived room-grid accept
                    haiditan_ds_1 x tr_hongzhoutian.
  positive TEST   : holdout-split exact-GT semi-synthetic positives.
  positive DEV-reported : real positives and calibration-split positives
                    (preservation targets; re-measured end-to-end).
  safety families : RA-1.2B ordinary mismatches, RA-1.2C hard negatives,
                    tiled-ambiguity cases.
  baselines       : GCC-PHAT and waveform NCC point estimates.

Usage: python evaluate.py <section>   section in {wrongsong, positives,
negatives, baselines, all}
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import alignment_engine_v2 as eng
import temporal_support as ts
from common import (DEV_COMPONENT_A, FeatureStore, Sources, clean_pair_rows,
                    decide, duration, iter_split_cases, real_cases,
                    real_case_audio, read, save, semi_case_mix,
                    wave_baselines)

OUT = Path(__file__).resolve().parent / "results"
ROOM_CASE = ("haiditan_ds_1", "tr_hongzhoutian")
BLOCKER = ("tr_lingduihua", "tr_yanwulieche")
TOL_S = 0.15


def load_policy():
    chosen = read(OUT / "chosen_policy.json")
    return ts.SupportPolicy(**chosen["support_policy"]), chosen


def gated(vf, mf, vdur, mdur, policy, methods=None):
    decision = decide(vf, mf, vdur, mdur)
    d, reports = ts.gate_decision(decision, vf, mf, vdur, mdur, policy,
                                  methods=methods)
    return decision, d, reports


def case_outcome_negative(final_status, final_offset):
    return "SAFE_ABSTAIN" if final_status != "accepted" else "WRONG_ACCEPT"


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------


def section_wrongsong(policy, chosen) -> None:
    store = FeatureStore(Sources())
    sources = store.sources
    _dev, test = clean_pair_rows(DEV_COMPONENT_A, sources)
    rows = []
    known_accepts = set()
    for q, r in [("tr_bai39", "tr_haiditan"), ("tr_haiditan", "tr_bai39"),
                 ("tr_bai39", "tr_chiyaoshuijiao"),
                 ("tr_chiyaoshuijiao", "tr_bai39")]:
        known_accepts.add((q, r))
    for row in test:
        q, r = row["query_track"], row["reference_track"]
        vf, mf = store.get("tracks", q), store.get("tracks", r)
        vdur, mdur = duration(sources.audio("tracks", q)), duration(sources.audio("tracks", r))
        decision, final, reports = gated(vf, mf, vdur, mdur, policy)
        outcome = case_outcome_negative(final["status"], final["offset"])
        rows.append({
            "query_track": q, "reference_track": r,
            "family": "heldout_clean_wrong_song",
            "known_astra_accept": (q, r) in known_accepts,
            "v2_status": decision.status, "v2_offset": decision.offset,
            "v2_reason": decision.reason_code,
            "final_status": final["status"], "final_offset": final["offset"],
            "final_reason": final["reason_code"], "outcome": outcome,
            "support": reports[0].as_dict() if reports else None,
        })
        print(f"{q} -> {r}: v2={decision.status} final={final['status']} "
              f"{outcome}", flush=True)
    # archived room-grid accept (recordings x wrong track)
    rid, tid = ROOM_CASE
    vf = store.get("recordings", rid)
    mf = store.get("tracks", tid)
    vdur = duration(sources.audio("recordings", rid))
    mdur = duration(sources.audio("tracks", tid))
    decision, final, reports = gated(vf, mf, vdur, mdur, policy)
    outcome = case_outcome_negative(final["status"], final["offset"])
    rows.append({
        "query_track": rid, "reference_track": tid,
        "family": "room_grid_archived_accept",
        "known_astra_accept": True,
        "v2_status": decision.status, "v2_offset": decision.offset,
        "v2_reason": decision.reason_code,
        "final_status": final["status"], "final_offset": final["offset"],
        "final_reason": final["reason_code"], "outcome": outcome,
        "support": reports[0].as_dict() if reports else None,
        "note": "Astra judged this pair's background content unresolved; "
                "it is reported separately from the 22 clean pairs.",
    })
    # blocker must abstain
    q, r = BLOCKER
    vf, mf = store.get("tracks", q), store.get("tracks", r)
    vdur = duration(sources.audio("tracks", q))
    mdur = duration(sources.audio("tracks", r))
    decision, final, reports = gated(vf, mf, vdur, mdur, policy)
    rows.append({
        "query_track": q, "reference_track": r,
        "family": "archived_blocker", "known_astra_accept": True,
        "v2_status": decision.status, "v2_offset": decision.offset,
        "v2_reason": decision.reason_code,
        "final_status": final["status"], "final_offset": final["offset"],
        "final_reason": final["reason_code"],
        "outcome": case_outcome_negative(final["status"], final["offset"]),
        "support": reports[0].as_dict() if reports else None,
    })
    save("eval_wrong_song_test.json", {
        "policy": dataclasses.asdict(policy), "chosen": chosen,
        "rows": rows,
    })
    _summary(rows)


def _summary(rows):
    from collections import Counter
    by = {}
    for r in rows:
        fam = r["family"]
        by.setdefault(fam, Counter())[r["outcome"]] += 1
    print(json.dumps({k: dict(v) for k, v in by.items()}, indent=2))


def _positive_rows(store, split):
    sources = store.sources
    mix_cache = {}

    def mix_feats(y, key):
        from common import source_features
        if key not in mix_cache:
            mix_cache[key] = source_features(y)
        return mix_cache[key]

    if split == "real":
        for case in real_cases():
            if case["class"] == "negative_mismatch":
                continue
            v, m = real_case_audio(case, sources)
            mf_key = None
            for sid, p in sources.mapping["tracks"].items():
                if str(p) == str(case["music"]):
                    mf_key = sid
                    break
            mf = store.get("tracks", mf_key)
            yield ({"case_id": case["case_id"], "family": "real_" + case["class"],
                    "gt_offset": case.get("expected_offset"),
                    "tolerance": case.get("tolerance", 0.4),
                    "audio": (v, m)},
                   mix_feats(v, "real:" + case["case_id"]), mf,
                   duration(v), duration(m))
        return
    for c in iter_split_cases(split):
        if c["kind"] != "positive":
            continue
        mix = semi_case_mix(c, store)
        m = store.sources.audio("tracks", c["target"])
        mf = store.get("tracks", c["target"])
        yield ({"case_id": c["case_id"], "family": f"semi_positive_{split}_{c['level']}",
                "gt_offset": c["offset_s"], "tolerance": TOL_S,
                "audio": (mix, m)},
               mix_feats(mix, "mix:" + c["case_id"]), mf,
               duration(mix), duration(m))


def classify_positive(final, gt, tol):
    if final["status"] == "accepted":
        if final["offset"] is not None and abs(final["offset"] - gt) <= tol:
            return "CORRECT_ACCEPT"
        return "WRONG_ACCEPT"
    return "SAFE_ABSTAIN"


def section_positives(policy, chosen) -> None:
    store = FeatureStore(Sources())
    rows = []
    for split in ("calibration", "holdout", "real"):
        for meta, vf, mf, vdur, mdur in _positive_rows(store, split):
            decision, final, reports = gated(vf, mf, vdur, mdur, policy)
            gt, tol = meta["gt_offset"], meta["tolerance"]
            outcome = (classify_positive(final, gt, tol) if gt is not None
                       else ("CORRECT_ACCEPT" if final["status"] == "accepted"
                             else "SAFE_ABSTAIN"))
            rows.append({**{k: meta[k] for k in
                            ("case_id", "family", "gt_offset", "tolerance")},
                         "v2_status": decision.status,
                         "v2_offset": decision.offset,
                         "v2_reason": decision.reason_code,
                         "final_status": final["status"],
                         "final_offset": final["offset"],
                         "final_reason": final["reason_code"],
                         "outcome": outcome,
                         "offset_error": (None if final["offset"] is None
                                          or gt is None
                                          else final["offset"] - gt),
                         "support": reports[0].as_dict() if reports else None,
                         })
            print(f"{meta['case_id']:34s} v2={decision.status:9s} "
                  f"final={final['status']:9s} {outcome}", flush=True)
    save("eval_positives.json", {
        "policy": dataclasses.asdict(policy), "chosen": chosen,
        "rows": rows})
    _summary(rows)


def section_negatives(policy, chosen) -> None:
    store = FeatureStore(Sources())
    rows = []
    for c in iter_split_cases("calibration"):
        if c["kind"] == "positive":
            continue
        rows.append((c, "calibration"))
    for c in iter_split_cases("holdout"):
        if c["kind"] == "positive":
            continue
        rows.append((c, "holdout"))
    out = []
    for c, split in rows:
        mix = semi_case_mix(c, store)
        from common import source_features
        vf = source_features(mix)
        mf = store.get("tracks", c["target"])
        decision, final, reports = gated(vf, mf, duration(mix),
                                         duration(store.sources.audio(
                                             "tracks", c["target"])), policy)
        out.append({"case_id": c["case_id"], "family": f"{c['kind']}_{split}",
                    "v2_status": decision.status, "v2_offset": decision.offset,
                    "final_status": final["status"],
                    "final_offset": final["offset"],
                    "final_reason": final["reason_code"],
                    "outcome": case_outcome_negative(final["status"],
                                                     final["offset"])})
        print(f"{c['case_id']:34s} {c['kind']:14s} final={final['status']}",
              flush=True)
    for case in real_cases():
        if case["class"] != "negative_mismatch":
            continue
        v, m = real_case_audio(case, store.sources)
        from common import source_features
        vf = source_features(v)
        mf_key = next(sid for sid, p in store.sources.mapping["tracks"].items()
                      if str(p) == str(case["music"]))
        mf = store.get("tracks", mf_key)
        decision, final, reports = gated(vf, mf, duration(v), duration(m),
                                         policy)
        out.append({"case_id": case["case_id"], "family": "ra12b_mismatch",
                    "v2_status": decision.status, "v2_offset": decision.offset,
                    "final_status": final["status"],
                    "final_offset": final["offset"],
                    "final_reason": final["reason_code"],
                    "outcome": case_outcome_negative(final["status"],
                                                     final["offset"])})
        print(f"{case['case_id']:34s} ra12b_mismatch  final={final['status']}",
              flush=True)
    save("eval_negatives.json", {"policy": dataclasses.asdict(policy),
                                 "rows": out})
    _summary(out)


def section_baselines(policy, chosen) -> None:
    store = FeatureStore(Sources())
    sources = store.sources
    rows = []
    # positives: offsets + coverage at tolerance
    for split in ("calibration", "holdout", "real"):
        for meta, vf, mf, vdur, mdur in _positive_rows(store, split):
            v, m = meta.pop("audio") if "audio" in meta else (None, None)
            base = wave_baselines(v, m)
            gt, tol = meta["gt_offset"], meta["tolerance"]
            row = {**{k: meta[k] for k in ("case_id", "family")},
                   "gt_offset": gt, "tolerance": tol}
            for name in ("wave_ncc", "gcc_phat"):
                off = base[name]["offset"]
                row[name] = {
                    "offset": off,
                    "within_tol": (None if off is None or gt is None
                                   else abs(off - gt) <= tol),
                    "abs_error": (None if off is None or gt is None
                                  else abs(off - gt)),
                    "peak": base[name].get("peak"),
                }
            rows.append(row)
            print(f"baseline {meta['case_id']:32s} "
                  f"gcc={row['gcc_phat']['offset']}", flush=True)
    # wrong-song population: where do waveform argmaxes point
    _dev, test = clean_pair_rows(DEV_COMPONENT_A, sources)
    for q, r in [BLOCKER] + [
            ("tr_bai39", "tr_haiditan"), ("tr_haiditan", "tr_bai39"),
            ("tr_bai39", "tr_chiyaoshuijiao"),
            ("tr_chiyaoshuijiao", "tr_bai39"),
            (ROOM_CASE[0], ROOM_CASE[1])]:
        pass
    wrong_pairs = [("tr_lingduihua", "tr_yanwulieche"),
                   ("tr_bai39", "tr_haiditan"), ("tr_haiditan", "tr_bai39"),
                   ("tr_bai39", "tr_chiyaoshuijiao"),
                   ("tr_chiyaoshuijiao", "tr_bai39")]
    for q, r in wrong_pairs:
        v = sources.audio("tracks", q)
        m = sources.audio("tracks", r)
        base = wave_baselines(v, m)
        rows.append({"case_id": f"{q}_x_{r}", "family": "wrong_song",
                     "gt_offset": None, "tolerance": None,
                     "wave_ncc": {"offset": base["wave_ncc"]["offset"],
                                  "peak": base["wave_ncc"]["peak"]},
                     "gcc_phat": {"offset": base["gcc_phat"]["offset"],
                                  "peak": base["gcc_phat"]["peak"]}})
        print(f"baseline wrong {q} x {r}", flush=True)
    save("eval_baselines.json", {"rows": rows})
    ok = sum(1 for r in rows if r["family"] != "wrong_song"
             and r["gcc_phat"]["within_tol"])
    tot = sum(1 for r in rows if r["family"] != "wrong_song")
    print(f"GCC-PHAT within tolerance: {ok}/{tot}", flush=True)


def main() -> None:
    policy, chosen = load_policy()
    section = sys.argv[1] if len(sys.argv) > 1 else "all"
    if section in ("wrongsong", "all"):
        section_wrongsong(policy, chosen)
    if section in ("positives", "all"):
        section_positives(policy, chosen)
    if section in ("negatives", "all"):
        section_negatives(policy, chosen)
    if section in ("baselines", "all"):
        section_baselines(policy, chosen)


if __name__ == "__main__":
    main()
