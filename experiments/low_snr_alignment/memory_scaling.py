"""RA-1.2C long-duration memory/runtime scaling check.

RA-1.2B measured Engine v2 at ~8.5 s wall / 247 MB peak Python allocation /
RSS 218->265 MB on a ~180 s video and estimated the PCEN/HPSS matrices grow
~3.3x for a 10-minute input. This measures that scaling directly with
deterministic synthetic fixtures (no media needed), without optimizing.

Run:  python experiments/low_snr_alignment/memory_scaling.py \
          [--durations 180 420 720] [--json OUT]
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
import tracemalloc

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np  # noqa: E402
import psutil  # noqa: E402

from experiments.low_snr_alignment.synthetic_eval import (  # noqa: E402
    make_music,
    make_taps,
)
from alignment_engine_v2 import decide_alignment  # noqa: E402

SR = 22050


def long_recording(music, true_offset, music_gain, noise_gain, tap_gain,
                   seed=3):
    """make_recording equivalent for arbitrary durations (deterministic)."""
    rng = np.random.default_rng(seed)
    n_video = int(240.0 * SR)  # recording runs 240 s regardless of track len
    n = n_video
    y = np.zeros(n, dtype=np.float32)
    off_i = int(true_offset * SR)
    end = min(n, off_i + len(music))
    if off_i < n:
        y[off_i:end] += music[: end - off_i] * music_gain
    y += (noise_gain * rng.standard_normal(n)).astype(np.float32)
    if tap_gain > 0:
        y += make_taps(n / SR, gain=tap_gain, seed=seed + 2)
    peak = np.max(np.abs(y)) + 1e-9
    return (y / peak * 0.95).astype(np.float32)


def measure(duration_s):
    music = make_music(duration_s=duration_s)
    recording = long_recording(music, true_offset=duration_s * 0.11,
                               music_gain=0.012, noise_gain=0.008,
                               tap_gain=0.30)
    proc = psutil.Process()
    gc.collect()
    rss_before = proc.memory_info().rss / (1 << 20)
    tracemalloc.start()
    t0 = time.perf_counter()
    d = decide_alignment(recording, music, sr=SR)
    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc.collect()
    rss_after = proc.memory_info().rss / (1 << 20)
    stages = {m: info["runtime_s"]
              for m, info in d.evidence["families"].items()}
    return {
        "duration_s": duration_s,
        "status": d.status,
        "offset": None if d.offset is None else round(d.offset, 3),
        "wall_s": round(wall, 2),
        "generator_runtimes_s": stages,
        "tracemalloc_peak_mb": round(peak / (1 << 20), 1),
        "rss_before_mb": round(rss_before, 1),
        "rss_after_mb": round(rss_after, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--durations", type=float, nargs="+",
                    default=[180.0, 420.0, 720.0])
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    rows = []
    for dur in args.durations:
        print(f"duration {dur:.0f}s ...", flush=True)
        row = measure(dur)
        rows.append(row)
        print(f"  status={row['status']} wall={row['wall_s']}s "
              f"peak={row['tracemalloc_peak_mb']}MB "
              f"rss={row['rss_before_mb']}->{row['rss_after_mb']}MB")
        gc.collect()
    base = rows[0]["duration_s"]
    for row in rows[1:]:
        row["scaling_vs_first"] = {
            "duration_x": round(row["duration_s"] / base, 2),
            "wall_x": round(row["wall_s"] / rows[0]["wall_s"], 2),
            "peak_mb_x": round(
                row["tracemalloc_peak_mb"] / rows[0]["tracemalloc_peak_mb"],
                2),
        }
    out = args.json or os.path.join(_HERE, "results",
                                    "memory_scaling_ra12c.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(json.dumps(rows, indent=2))
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
