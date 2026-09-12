"""RA-1.2D1 DEV calibration for the temporal-support verifier (v2 design).

Measures the net-signed-correlation concentration profile (top-1s-bin
share of the engine's own PCEN correlation at the accepted offset) for
every accepted DEV case:

  wrong side : 18 known wrong accepts among directed clean pairs inside
               DEV component A (incl. the archived blocker).
  true side  : the 46 dev true accepts (29 real positives + 17
               calibration-split exact-GT semi-synthetic positives).

DEV data only — the held-out TEST set is never looked at here.

Usage: python calibrate_dev.py compute
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import temporal_support as ts
from common import (DEV_COMPONENT_A, FeatureStore, Sources, clean_pair_rows,
                    decide, duration, iter_split_cases, real_cases,
                    real_case_audio, save, semi_case_mix, source_features)


def collect_cases(store: FeatureStore):
    sources = store.sources
    dev, _test = clean_pair_rows(DEV_COMPONENT_A, sources)
    for row in dev:
        q, r = row["query_track"], row["reference_track"]
        vf, mf = store.get("tracks", q), store.get("tracks", r)
        yield ({"case_id": f"devwrong_{q}_x_{r}", "kind": "dev_wrong_song"},
               vf, mf, duration(sources.audio("tracks", q)),
               duration(sources.audio("tracks", r)), None)
    mix_cache: dict = {}

    def mix_feats(y, key):
        if key not in mix_cache:
            mix_cache[key] = source_features(y)
        return mix_cache[key]

    for case in real_cases():
        if case["class"] == "negative_mismatch":
            continue
        v, m = real_case_audio(case, sources)
        mf_key = next(sid for sid, p in sources.mapping["tracks"].items()
                      if str(p) == str(case["music"]))
        yield ({"case_id": "real_" + case["class"] + "_" + case["case_id"],
                "kind": "real_positive"},
               mix_feats(v, "real:" + case["case_id"]),
               store.get("tracks", mf_key), duration(v), duration(m),
               case.get("expected_offset"))
    for c in iter_split_cases("calibration"):
        if c["kind"] != "positive":
            continue
        mix = semi_case_mix(c, store)
        m = sources.audio("tracks", c["target"])
        yield ({"case_id": "semical_" + c["case_id"],
                "kind": "semi_positive", "level": c["level"]},
               mix_feats(mix, "mix:" + c["case_id"]),
               store.get("tracks", c["target"]), duration(mix), duration(m),
               c["offset_s"])


def main() -> None:
    store = FeatureStore(Sources())
    rows = []
    for meta, vf, mf, vdur, mdur, gt in collect_cases(store):
        t0 = time.perf_counter()
        decision = decide(vf, mf, vdur, mdur)
        row = {**meta, "v2_status": decision.status,
               "v2_offset": decision.offset, "gt_offset": gt,
               "methods": {}}
        if decision.status == "accepted":
            for method in ("pcen", "pcen_hpss", "chroma"):
                rep = ts.verify_offset(
                    vf[method], mf[method], decision.offset, vdur, mdur,
                    method, method, policy=ts.DEFAULT_SUPPORT_POLICY)
                row["methods"][method] = {
                    "top_bin_share": rep.top_bin_share,
                    "effective_bins": rep.effective_bins,
                    "active_bins": rep.active_bins,
                    "n_bins": rep.n_bins,
                    "peak_bin_start_s": rep.peak_bin_start_s,
                    "overlap_s": rep.overlap_s,
                    "top_k_share": rep.top_k_share,
                }
        rows.append(row)
        m = row["methods"].get("pcen", {})
        print(f"{row['case_id']:44s} {decision.status:9s} "
              f"share={m.get('top_bin_share')} eff={m.get('effective_bins')} "
              f"act={m.get('active_bins')}/{m.get('n_bins')} "
              f"{time.perf_counter()-t0:4.1f}s", flush=True)
    save("dev_concentration.json", {"rows": rows,
                                    "policy": {"bin_s": 1.0}})

    # separation summary
    acc = [r for r in rows if r["v2_status"] == "accepted"]
    wrong = sorted((r["methods"]["pcen"]["top_bin_share"] for r in acc
                    if r["kind"] == "dev_wrong_song"))
    true_ = sorted((r["methods"]["pcen"]["top_bin_share"] for r in acc
                    if r["kind"] != "dev_wrong_song"))
    act_w = sorted((r["methods"]["pcen"]["active_bins"] for r in acc
                    if r["kind"] == "dev_wrong_song"))
    act_t = sorted((r["methods"]["pcen"]["active_bins"] for r in acc
                    if r["kind"] != "dev_wrong_song"))
    eff_w = sorted((round(r["methods"]["pcen"]["effective_bins"], 1) for r in acc
                    if r["kind"] == "dev_wrong_song"))
    eff_t = sorted((round(r["methods"]["pcen"]["effective_bins"], 1) for r in acc
                    if r["kind"] != "dev_wrong_song"))
    print("pcen top_bin_share  wrong:", [round(x, 3) for x in wrong], flush=True)
    print("pcen top_bin_share  true :", [round(x, 3) for x in true_], flush=True)
    print("pcen active_bins    wrong:", act_w, flush=True)
    print("pcen active_bins    true :", act_t, flush=True)
    print("pcen effective_bins wrong:", eff_w, flush=True)
    print("pcen effective_bins true :", eff_t, flush=True)


if __name__ == "__main__":
    main()
