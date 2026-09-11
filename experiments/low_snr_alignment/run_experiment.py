"""Run the RA-1.2A method comparison on a real (video, music) pair.

Usage:
    python experiments/low_snr_alignment/run_experiment.py \
        [--video PATH] [--music PATH] [--sr 22050] [--hop 512] [--json OUT]

Defaults point at the real failing sample documented in
docs/RA-1.2A-LOW-SNR-ALIGNMENT.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np  # noqa: E402

from experiments.low_snr_alignment.harness import (  # noqa: E402
    chroma_method,
    hybrid_method,
    logmel_flux_method,
    onset_method,
    pcen_hpss_method,
    pcen_method,
    production_reliability,
    default_reliability,
    summarize,
)

DEFAULT_VIDEO = r"D:\Daozh\Videos\舞萌手元\13.2\零对话\零对话.mp4"
DEFAULT_MUSIC = r"D:\Daozh\Videos\舞萌手元\13.2\零对话\track.mp3"


def load_pair(video_path, music_path, sr):
    import librosa
    import imageio_ffmpeg
    from auto_sync import extract_audio
    import tempfile
    import uuid

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = tempfile.gettempdir()
    paths = {}
    try:
        for tag, src in (("v", video_path), ("m", music_path)):
            wav = os.path.join(tmp, f"ra_exp_{tag}_{uuid.uuid4().hex}.wav")
            extract_audio(ffmpeg, src, wav, sr)
            paths[tag] = wav
        y_video, _ = librosa.load(paths["v"], sr=None, mono=True)
        y_music, _ = librosa.load(paths["m"], sr=None, mono=True)
    finally:
        for p in paths.values():
            if os.path.exists(p):
                os.remove(p)
    return y_video, y_music


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=DEFAULT_VIDEO)
    ap.add_argument("--music", default=DEFAULT_MUSIC)
    ap.add_argument("--sr", type=int, default=22050)
    ap.add_argument("--hop", type=int, default=512)
    ap.add_argument("--json", default=None, help="write results JSON here")
    args = ap.parse_args()

    print(f"video: {args.video}")
    print(f"music: {args.music}")
    y_video, y_music = load_pair(args.video, args.music, args.sr)
    print(f"video audio: {len(y_video)/args.sr:.3f}s   "
          f"music: {len(y_music)/args.sr:.3f}s\n")

    runners = [
        lambda: hybrid_method(y_video, y_music, args.sr, args.hop),
        lambda: onset_method(y_video, y_music, args.sr, args.hop),
        lambda: chroma_method(y_video, y_music, args.sr, args.hop),
        lambda: pcen_method(y_video, y_music, args.sr, args.hop,
                            n_mels=96, fmax=4000.0, positive_only=True),
        lambda: pcen_hpss_method(y_video, y_music, args.sr, args.hop),
        lambda: logmel_flux_method(y_video, y_music, args.sr, args.hop),
    ]
    results = []
    for run in runners:
        r = run()
        prod = production_reliability(r)
        r["production_reliable"] = prod
        r["reliable"] = prod if prod is not None else default_reliability(r)
        results.append(r)
        print(f"[{r['method']}] offset={r['offset_s']:+.4f}s  "
              f"z={r['z_score']:.2f}  ratio={r['independent_peak_ratio']}  "
              f"({r['runtime_s']:.2f}s)")

    print()
    print(summarize(results))

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nresults written to {args.json}")


if __name__ == "__main__":
    main()
