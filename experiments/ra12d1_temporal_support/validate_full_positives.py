"""RA-1.2D1: full positive corpus through the INTEGRATED production path.

Runs eng.decide_alignment (with the temporal-support gate installed) on all
56 exact-GT semi-synthetic positives and all 29 real positives, and
compares against the frozen v2 baseline (26/56 + 29/29 accepted).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import alignment_engine_v2 as eng  # noqa: E402
from common import (FeatureStore, Sources, duration, iter_split_cases,
                    real_cases, real_case_audio, save, semi_case_mix)  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"
TOL = 0.15


def main() -> None:
    store = FeatureStore(Sources())
    sources = store.sources
    rows = []
    t_start = time.perf_counter()
    for split in ("calibration", "holdout"):
        for c in iter_split_cases(split):
            if c["kind"] != "positive":
                continue
            mix = semi_case_mix(c, store)
            m = sources.audio("tracks", c["target"])
            t0 = time.perf_counter()
            d = eng.decide_alignment(mix, m, durations_s=(duration(mix),
                                                          duration(m)))
            if d.status == "accepted":
                outcome = ("CORRECT_ACCEPT"
                           if abs(d.offset - c["offset_s"]) <= TOL
                           else "WRONG_ACCEPT")
                err = d.offset - c["offset_s"]
            else:
                outcome, err = "SAFE_ABSTAIN", None
            rows.append({"case_id": c["case_id"], "split": split,
                         "level": c["level"], "gt": c["offset_s"],
                         "status": d.status, "offset": d.offset,
                         "reason": d.reason_code, "outcome": outcome,
                         "offset_error": err,
                         "temporal_support": d.evidence.get("temporal_support"),
                         "runtime_s": round(time.perf_counter() - t0, 2)})
            print(f"semi {split[:4]} {c['case_id']}: {outcome}", flush=True)
    for case in real_cases():
        if case["class"] == "negative_mismatch":
            continue
        v, m = real_case_audio(case, sources)
        t0 = time.perf_counter()
        d = eng.decide_alignment(v, m, durations_s=(duration(v), duration(m)))
        if d.status == "accepted":
            gt, tol = case.get("expected_offset"), case.get("tolerance", 0.4)
            if gt is None:
                outcome = "CORRECT_ACCEPT (pairing evidence only)"
                err = None
            else:
                ok = abs(d.offset - gt) <= tol
                outcome = "CORRECT_ACCEPT" if ok else "WRONG_ACCEPT"
                err = d.offset - gt
        else:
            outcome, err = "SAFE_ABSTAIN", None
        rows.append({"case_id": case["case_id"], "split": "real",
                     "level": case["class"], "gt": case.get("expected_offset"),
                     "status": d.status, "offset": d.offset,
                     "reason": d.reason_code, "outcome": outcome,
                     "offset_error": err,
                     "temporal_support": d.evidence.get("temporal_support"),
                     "runtime_s": round(time.perf_counter() - t0, 2)})
        print(f"real {case['case_id']}: {outcome}", flush=True)

    from collections import Counter
    summary = {
        "total_seconds": round(time.perf_counter() - t_start, 1),
        "outcomes": dict(Counter(r["outcome"].split(" ")[0] for r in rows)),
        "by_split": {s: dict(Counter(r["outcome"].split(" ")[0]
                                     for r in rows if r["split"] == s))
                     for s in ("calibration", "holdout", "real")},
        "max_abs_offset_error": max((abs(r["offset_error"]) for r in rows
                                     if r["offset_error"] is not None),
                                    default=None),
    }
    print(json.dumps(summary, indent=1), flush=True)
    save("integrated_full_positives.json", {"summary": summary,
                                            "rows": rows})


if __name__ == "__main__":
    main()
