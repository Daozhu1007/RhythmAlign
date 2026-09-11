"""RA-1.2B owner-test tool: run Alignment Engine v2 on a real pair.

Evaluates production v1.1.x and Engine v2 on one (video, music) pair,
reports the decision with its evidence, measures runtime and peak memory,
and can produce ONE local test export for owner listening tests.

The test export is a local artifact: never commit it.

Run (defaults to the RA-1.2A failing pair):
    python experiments/low_snr_alignment/engine_v2_owner_test.py
    python experiments/low_snr_alignment/engine_v2_owner_test.py --export OUT.mp4
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from alignment_engine_v2 import (  # noqa: E402
    decision_message,
    find_offset_v2,
)
from auto_sync import _align_hybrid  # noqa: E402

DEFAULT_VIDEO = r"D:\Daozh\Videos\舞萌手元\13.2\零对话\零对话.mp4"
DEFAULT_MUSIC = r"D:\Daozh\Videos\舞萌手元\13.2\零对话\track.mp3"
GROUND_TRUTH_S = 12.4
GROUND_TRUTH_TOL_S = 0.4


def _rss_mb():
    """Process RSS in MB via psutil, with a ctypes fallback on Windows."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        if os.name == "nt":
            import ctypes.wintypes as wt

            class PMC(ctypes.Structure):
                _fields_ = [("PageFaultCount", wt.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t)]

            pmc = PMC()
            ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(pmc), ctypes.sizeof(pmc))
            return pmc.WorkingSetSize / (1024 * 1024)
        return float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=DEFAULT_VIDEO)
    ap.add_argument("--music", default=DEFAULT_MUSIC)
    ap.add_argument("--export", default=None,
                    help="write ONE local test export to this path "
                         "(only when the decision is an accept near the "
                         "documented ground truth, unless --force)")
    ap.add_argument("--force", action="store_true",
                    help="export regardless of the decision")
    args = ap.parse_args()

    print(f"video: {args.video}")
    print(f"music: {args.music}")

    # v1.1.x production path (extract + align), for the owner's comparison
    import tempfile
    import uuid
    import imageio_ffmpeg
    import librosa
    from auto_sync import extract_audio

    temp_dir = tempfile.gettempdir()
    tv = os.path.abspath(os.path.join(temp_dir, f"ra_owner_v_{uuid.uuid4().hex}.wav"))
    tm = os.path.abspath(os.path.join(temp_dir, f"ra_owner_m_{uuid.uuid4().hex}.wav"))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    t0 = time.perf_counter()
    extract_audio(ffmpeg, args.video, tv, 22050)
    extract_audio(ffmpeg, args.music, tm, 22050)
    y_video, _ = librosa.load(tv, sr=None, mono=True)
    y_music, _ = librosa.load(tm, sr=None, mono=True)
    prep_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    offset, z, _ = _align_hybrid(y_video, y_music, 22050, 512)
    v1_s = time.perf_counter() - t0
    print(f"\n[v1.1.x production hybrid] offset={offset:+.4f} s Z={z:.3f} "
          f"accepted={z >= 2.0} ({v1_s:.2f} s + {prep_s:.2f} s extract)")

    # Engine v2 with memory measurement
    rss0 = _rss_mb()
    import tracemalloc
    tracemalloc.start()
    t0 = time.perf_counter()
    decision = find_offset_v2(args.video, args.music)
    wall_s = time.perf_counter() - t0
    _cur, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss1 = _rss_mb()

    print(f"\n[Engine v2] {decision.status.upper()} "
          f"offset={decision.offset if decision.offset is None else format(decision.offset, '+.4f')} "
          f"reason={decision.reason_code}")
    print(f"  wall: {wall_s:.2f} s (incl. extraction) | "
          f"engine decision layer: {decision.runtime_s:.2f} s")
    print(f"  peak python memory: {py_peak / (1024 * 1024):.1f} MB | "
          f"RSS {rss0:.0f} -> {rss1:.0f} MB")
    print("  families:")
    for method, info in decision.evidence["families"].items():
        print(f"    {method:10s} z={info['z']:7.3f} "
              f"runtime={info['runtime_s']:6.2f} s error={info['error']}")
    print("  top clusters:")
    for cl in decision.clusters[:3]:
        fams = {f: (v["z_at_cluster"], v["margin_at_cluster"])
                for f, v in cl["families"].items()}
        print(f"    {cl['offset_s']:+9.4f} s overlap={cl['overlap_s']:6.1f} s "
              f"{fams}")
    print(f"\n  message: {decision_message(decision)}")

    accepted_near_gt = (
        decision.status == "accepted" and decision.offset is not None
        and abs(decision.offset - GROUND_TRUTH_S) <= GROUND_TRUTH_TOL_S
    )

    if args.export:
        if accepted_near_gt or args.force:
            from auto_sync import mix_and_export
            mix_and_export(args.video, args.music, decision.offset,
                           args.export, stream_copy=True)
            size_mb = os.path.getsize(args.export) / (1024 * 1024)
            print(f"\ntest export written: {args.export} ({size_mb:.1f} MB)")
        else:
            print("\nno export: decision is not an accept near ground truth "
                  f"({GROUND_TRUTH_S} ± {GROUND_TRUTH_TOL_S} s); use --force "
                  "to override")
    return 0


if __name__ == "__main__":
    sys.exit(main())
