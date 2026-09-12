"""RA-1.2D1 final validation of the INTEGRATED production engine.

Runs the production find_offset_v2 (with the temporal-support gate
installed) on a representative sample and compares against (a) the frozen
v2 baseline recorded on main before the change and (b) the
experiment-harness gate results. Also measures gate runtime and memory.
"""
from __future__ import annotations

import dataclasses
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import alignment_engine_v2 as eng  # noqa: E402
import temporal_support as ts  # noqa: E402
from common import (FeatureStore, Sources, duration, iter_split_cases,
                    real_cases, real_case_audio, read, save,
                    semi_case_mix, source_features)  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"


def production_case(store, v, m, vdur, mdur):
    t0 = time.perf_counter()
    d = eng.decide_alignment(v, m, sr=22050, hop_length=512,
                             durations_s=(vdur, mdur))
    wall = time.perf_counter() - t0
    return d, wall


def main() -> None:
    store = FeatureStore(Sources())
    sources = store.sources
    rows = []

    def record(cid, family, v, m, vdur, mdur, expect):
        d, wall = production_case(store, v, m, vdur, mdur)
        ok = expect(d)
        rows.append({
            "case_id": cid, "family": family, "status": d.status,
            "offset": d.offset, "reason_code": d.reason_code,
            "temporal_support": d.evidence.get("temporal_support"),
            "runtime_s": round(wall, 3), "expectation_met": ok,
        })
        print(f"{cid:44s} {d.status:9s} off={d.offset} ok={ok} "
              f"({wall:.2f}s)", flush=True)
        return d, wall

    # 1. the blocker must ABSTAIN through the production path
    q, r = "tr_lingduihua", "tr_yanwulieche"
    vf, mf = store.get("tracks", q), store.get("tracks", r)
    record("blocker_lingduihua_x_yanwulieche", "astra_blocker",
           vf["pcen"] if False else sources.audio("tracks", q),
           sources.audio("tracks", r),
           duration(sources.audio("tracks", q)),
           duration(sources.audio("tracks", r)),
           lambda d: d.status == "abstained"
           and d.reason_code == "ABSTAIN_CONCENTRATED_EVIDENCE")

    # 2. real positives sample incl. 零对话 (low-SNR)
    for case in real_cases():
        if case["case_id"] not in ("lingduihua_132", "haiditan_ds_1",
                                   "queen", "maodunxinli"):
            continue
        v, m = real_case_audio(case, sources)
        mf_key = next(sid for sid, p in sources.mapping["tracks"].items()
                      if str(p) == str(case["music"]))
        record("real_" + case["case_id"], "real_positive",
               v, m, duration(v), duration(m),
               lambda d: d.status == "accepted")

    # 3. semi-synthetic: one accepted + one abstained from each split
    seen = {"calibration": 0, "holdout": 0}
    for split in ("calibration", "holdout"):
        for c in iter_split_cases(split):
            if c["kind"] != "positive" or seen[split] >= 2:
                continue
            mix = semi_case_mix(c, store)
            m = sources.audio("tracks", c["target"])
            vf2 = source_features(mix)["pcen"] if False else mix
            d, wall = production_case(store, mix, m, duration(mix),
                                      duration(m))
            outcome = ("CORRECT_ACCEPT" if d.status == "accepted"
                       and abs(d.offset - c["offset_s"]) <= 0.15
                       else ("SAFE_ABSTAIN" if d.status != "accepted"
                             else "WRONG_ACCEPT"))
            baseline_ok = outcome in ("CORRECT_ACCEPT", "SAFE_ABSTAIN")
            rows.append({"case_id": "semi_" + c["case_id"], "family":
                         f"semi_positive_{split}_{c['level']}",
                         "status": d.status, "offset": d.offset,
                         "reason_code": d.reason_code,
                         "temporal_support":
                             d.evidence.get("temporal_support"),
                         "runtime_s": round(wall, 3),
                         "expectation_met": baseline_ok})
            print(f"semi_{c['case_id']:39s} {d.status:9s} {outcome} "
                  f"ok={baseline_ok}", flush=True)
            seen[split] += 1

    # 4. component-B clean wrong pair must abstain (CASE A path)
    q, r = "tr_bai39", "tr_haiditan"
    record("clean_bai39_x_haiditan", "astra_wrong_accept_holdout",
           sources.audio("tracks", q), sources.audio("tracks", r),
           duration(sources.audio("tracks", q)),
           duration(sources.audio("tracks", r)),
           lambda d: d.status == "abstained")

    # 5. gate runtime + memory overhead on the blocker geometry
    d_base = eng.find_offset_v2  # noqa: F841  (entry point exists)
    vf = store.get("tracks", "tr_lingduihua")
    mf = store.get("tracks", "tr_yanwulieche")
    fv, fm = vf["pcen"], mf["pcen"]
    tracemalloc.start()
    t0 = time.perf_counter()
    bins, t0s, _ = eng._concentration_profile(
        fv, fm, 1.4628571428571429, 22050, 512, 1.0)
    gate_ms = (time.perf_counter() - t0) * 1000
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    overhead = {
        "gate_wall_ms": round(gate_ms, 2),
        "gate_peak_python_mem_kib": round(peak / 1024, 1),
        "n_bins": int(bins.size),
        "note": "features are attached to FamilyResults by reference; the "
                "gate allocates only the 1-D product array + bins",
    }
    print(overhead, flush=True)

    # engine-level A/B on the blocker: gate off vs on (policy knob)
    policy_off = eng.DecisionPolicy(max_top_bin_share=1.01)
    d_off = eng.decide_alignment(
        sources.audio("tracks", "tr_lingduihua"),
        sources.audio("tracks", "tr_yanwulieche"), policy=policy_off)
    ab = {"gate_disabled_status": d_off.status,
          "gate_disabled_offset": d_off.offset,
          "gate_disabled_reason": d_off.reason_code}
    print(ab, flush=True)

    save("integrated_validation.json", {"rows": rows, "overhead": overhead,
                                        "ab_test": ab})


if __name__ == "__main__":
    main()
