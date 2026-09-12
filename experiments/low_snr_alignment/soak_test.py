"""RA-1.2C repeated-invocation / soak harness.

RA-1.2B observed the single-process real-corpus benchmark dying silently
after ~25-30 cases (twice), and worked around it with worker isolation.
Worker isolation hides whether a persistent desktop process calling Engine
v2 repeatedly is safe. This harness investigates explicitly.

Modes
-----
synthetic       N repeated decide_alignment() calls in THIS process on
                small deterministic synthetic audio (fast; alternates
                accept / no-signal inputs so both decision paths run).
real-file       N repeated find_offset_v2() calls on ONE real (video,
                music) pair — the full production path including ffmpeg
                extraction and WAV IO every call.
benchmark-repro Reproduces the original dying benchmark: in-process
                sequential loop over the local real corpus (extract audio,
                v1 hybrid, Engine v2 per case), incremental result writing
                so per-case RSS/handle history survives a hard native crash.

Measured per call: process RSS, OS handle count, per-call wall time; sampled:
tracemalloc peak, leaked ra_* temp files in the system temp dir. The JSON
report records the full history; growth is summarized as a per-call slope.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
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
    make_recording,
)

RESULTS_DIR = os.path.join(_HERE, "results")
SR = 22050
TEMP_PATTERNS = ["ra_v2_*", "ra_corpus_*", "tmp*"]


def _proc():
    return psutil.Process()


def _handles(proc):
    try:
        return proc.num_handles()  # Windows
    except AttributeError:
        try:
            return proc.num_fds()  # unix
        except Exception:
            return None


def _leaked_temp_files():
    root = tempfile.gettempdir()
    hits = []
    for pat in ("ra_v2_*", "ra_corpus_*", "ra_soak_*"):
        hits.extend(glob.glob(os.path.join(root, pat)))
    return len(hits)


def sample_state(samples, label, extra=None):
    proc = _proc()
    entry = {
        "label": label,
        "rss_mb": round(proc.memory_info().rss / (1 << 20), 1),
        "handles": _handles(proc),
        "leaked_temp_files": _leaked_temp_files(),
    }
    if extra:
        entry.update(extra)
    samples.append(entry)
    return entry


def growth_slope(values):
    n = len(values)
    if n < 3 or any(v is None for v in values):
        return None
    x = np.arange(n, dtype=float)
    return round(float(np.polyfit(x, np.asarray(values, dtype=float), 1)[0]),
                 3)


def report(samples):
    rss = [s["rss_mb"] for s in samples]
    handles = [s["handles"] for s in samples]
    temps = [s["leaked_temp_files"] for s in samples]
    return {
        "rss_start_mb": rss[0],
        "rss_end_mb": rss[-1],
        "rss_max_mb": max(rss),
        "rss_slope_mb_per_call": growth_slope(rss),
        "handles_start": handles[0],
        "handles_end": handles[-1],
        "handles_slope_per_call": growth_slope(handles),
        "leaked_temp_files_end": temps[-1],
    }


def run_synthetic(n_calls, sample_every=5):
    """Same-process repeated decide_alignment on deterministic synthetic
    audio, alternating accepting and no-signal inputs."""
    import gc

    from alignment_engine_v2 import decide_alignment

    music = make_music(duration_s=40.0)
    accept_rec = make_recording(music, true_offset=6.4, music_gain=0.5,
                                noise_gain=0.004, seed=901)
    noise_rec = make_recording(music, true_offset=5.1, music_gain=0.0,
                               noise_gain=0.02, tap_gain=0.30, seed=902)
    samples = []
    calls = []
    sample_state(samples, "start")
    for i in range(n_calls):
        rec = accept_rec if i % 2 == 0 else noise_rec
        t0 = time.perf_counter()
        d = decide_alignment(rec, music, sr=SR)
        rt = time.perf_counter() - t0
        calls.append({"i": i, "status": d.status, "runtime_s": round(rt, 3)})
        if i % sample_every == 0 or i == n_calls - 1:
            st = sample_state(samples, f"after_call_{i}")
            print(f"call {i + 1}/{n_calls}: {d.status} {rt:.2f}s "
                  f"rss={st['rss_mb']}MB handles={st['handles']} "
                  f"temp_leaks={st['leaked_temp_files']}", flush=True)
        if i in (10, n_calls // 2):
            tracemalloc.start()
            d = decide_alignment(rec, music, sr=SR)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            samples[-1]["tracemalloc_peak_mb"] = round(peak / (1 << 20), 1)
        gc.collect()
    return {"mode": "synthetic", "n_calls": n_calls, "samples": samples,
            "calls": calls, "summary": report(samples)}


def run_real_file(n_calls, sample_every=1):
    """Repeated find_offset_v2 on one real pair: production file path
    including ffmpeg extraction each call."""
    from alignment_engine_v2 import find_offset_v2

    with open(os.path.join(_HERE, "local_sources.json"),
              encoding="utf-8") as f:
        sources = json.load(f)
    video = sources["recordings"]["lingduihua_132"]
    music_path = sources["recording_own_track"]["lingduihua_132"]
    samples = []
    calls = []
    sample_state(samples, "start")
    for i in range(n_calls):
        t0 = time.perf_counter()
        d = find_offset_v2(video, music_path, sr=SR)
        rt = time.perf_counter() - t0
        calls.append({"i": i, "status": d.status,
                      "offset": d.offset, "runtime_s": round(rt, 3)})
        st = sample_state(samples, f"after_call_{i}")
        print(f"call {i + 1}/{n_calls}: {d.status}@{d.offset} {rt:.2f}s "
              f"rss={st['rss_mb']}MB handles={st['handles']} "
              f"temp_leaks={st['leaked_temp_files']}", flush=True)
    return {"mode": "real-file", "n_calls": n_calls, "samples": samples,
            "calls": calls, "summary": report(samples)}


def run_benchmark_repro(limit, sample_every=1):
    """The original single-process benchmark loop (RA-1.2B §22 note):
    extract audio, run v1 hybrid + Engine v2 for corpus cases, all in THIS
    process. Results are written incrementally so a hard native crash still
    leaves per-case evidence."""
    from auto_sync import _align_hybrid, extract_audio
    from alignment_engine_v2 import decide_alignment
    import imageio_ffmpeg
    import librosa

    with open(os.path.join(_HERE, "local_corpus.json"),
              encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    cases = cases[:limit]
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    proc = _proc()
    samples = []
    calls = []
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "soak_benchmark_repro_ra12c.json")

    def flush():
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"mode": "benchmark-repro", "calls": calls,
                       "samples": samples, "summary": report(samples)
                       if samples else None},
                      f, ensure_ascii=False, indent=2)

    sample_state(samples, "start")
    for i, case in enumerate(cases):
        t0 = time.perf_counter()
        tv = os.path.abspath(os.path.join(
            tempfile.gettempdir(), f"ra_repro_v_{i}.wav"))
        tm = os.path.abspath(os.path.join(
            tempfile.gettempdir(), f"ra_repro_m_{i}.wav"))
        try:
            extract_audio(ffmpeg_bin, case["video"], tv, SR)
            extract_audio(ffmpeg_bin, case["music"], tm, SR)
            y_video, _ = librosa.load(tv, sr=None, mono=True)
            y_music, _ = librosa.load(tm, sr=None, mono=True)
        finally:
            for p in (tv, tm):
                if os.path.exists(p):
                    os.remove(p)
        v1_offset, v1_z, _ = _align_hybrid(y_video, y_music, SR, 512)
        d = decide_alignment(y_video, y_music, sr=SR)
        rt = time.perf_counter() - t0
        calls.append({"i": i, "case_id": case["case_id"],
                      "v1_offset": round(v1_offset, 4),
                      "v1_z": round(v1_z, 3), "v2_status": d.status,
                      "runtime_s": round(rt, 2)})
        st = sample_state(samples, f"after_case_{i}",
                          extra={"case_id": case["case_id"]})
        print(f"case {i + 1}/{len(cases)} {case['case_id']}: {rt:.1f}s "
              f"rss={st['rss_mb']}MB handles={st['handles']} "
              f"temp_leaks={st['leaked_temp_files']}", flush=True)
        flush()
    return {"mode": "benchmark-repro", "n_calls": len(calls),
            "samples": samples, "calls": calls, "summary": report(samples)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["synthetic", "real-file",
                                     "benchmark-repro"])
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--sample-every", type=int, default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    sample_every = args.sample_every
    if args.mode == "synthetic":
        result = run_synthetic(args.n, sample_every or 5)
    elif args.mode == "real-file":
        result = run_real_file(args.n, sample_every or 1)
    else:
        result = run_benchmark_repro(args.n, sample_every or 1)
    out = args.json or os.path.join(
        RESULTS_DIR, f"soak_{args.mode.replace('-', '')}_ra12c.json")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("summary:", json.dumps(result["summary"], indent=2))
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
