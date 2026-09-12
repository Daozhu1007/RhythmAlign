"""RA-1.2D1 warm-up: decode sources, extract per-source features, and verify
that family curves rebuilt from cached features reproduce the production
find_offset_v2 decision exactly on the archived blocker pair.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

from common import (FeatureStore, SCRATCH, Sources, decide, digest, duration,
                    families, read, save)
import alignment_engine_v2 as eng  # noqa: E402

BLOCKER = ("tr_lingduihua", "tr_yanwulieche")


def main() -> None:
    sources = Sources()
    store = FeatureStore(sources)
    kinds = ["tracks", "recordings"]
    t0 = time.perf_counter()
    done = 0
    for kind in kinds:
        for sid in sources.mapping[kind]:
            t1 = time.perf_counter()
            f = store.get(kind, sid)
            print(f"features {kind}:{sid} frames={f['chroma'].shape[1]} "
                  f"({time.perf_counter() - t1:.1f}s)", flush=True)
            done += 1
    print(f"extracted {done} sources in {time.perf_counter() - t0:.0f}s",
          flush=True)

    # equivalence check on the blocker
    q, r = BLOCKER
    vf, mf = store.get("tracks", q), store.get("tracks", r)
    vdur, mdur = duration(sources.audio("tracks", q)), duration(sources.audio("tracks", r))
    d_cached = decide(vf, mf, vdur, mdur)
    d_prod = eng.find_offset_v2(str(sources.path_of("tracks", q)),
                                str(sources.path_of("tracks", r)))
    fs = families(vf, mf)
    eq = {
        "cached_status": d_cached.status,
        "cached_offset": d_cached.offset,
        "cached_reason": d_cached.reason_code,
        "production_status": d_prod.status,
        "production_offset": d_prod.offset,
        "production_reason": d_prod.reason_code,
        "offset_equal": (d_cached.offset == d_prod.offset),
        "status_equal": d_cached.status == d_prod.status,
        "runtime_cached_s": d_cached.runtime_s,
    }
    # also verify against the committed research reproduction
    repro = read(Path(__file__).resolve().parent / "results/blocker_reproduction.json")
    eq["reproduction_offset_equal"] = (d_cached.offset == repro["decision"]["offset"])
    save("equivalence_check.json", eq)
    print(eq, flush=True)
    if not (eq["offset_equal"] and eq["status_equal"] and eq["reproduction_offset_equal"]):
        print("EQUIVALENCE FAILED", flush=True)
        sys.exit(2)
    print("EQUIVALENCE OK", flush=True)


if __name__ == "__main__":
    main()
