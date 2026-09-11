"""Deep-dive failure analysis for the 零对话 hybrid -1.997 s false peak.

Localizes which video segments drive the false chroma peak, compares local
per-window offset votes, and checks stereo / band structure.
Run:  python experiments/low_snr_alignment/failure_analysis.py
Outputs: JSON + markdown-friendly text to stdout.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import librosa
from scipy import signal

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from auto_sync import (  # noqa: E402
    _correlate_feature_rows,
    _correlation_z_score,
    _normalize_correlation,
    _align_hybrid,
)

SR = 22050
HOP = 512
CACHE = os.path.join(_HERE, "..", "..", "results", "rep_y_video.npy")
CACHE_M = os.path.join(_HERE, "..", "..", "results", "rep_y_music.npy")

VIDEO = r"D:\Daozh\Videos\舞萌手元\13.2\零对话\零对话.mp4"
MUSIC = r"D:\Daozh\Videos\舞萌手元\13.2\零对话\track.mp3"


def load_audio():
    if os.path.exists(CACHE) and os.path.exists(CACHE_M):
        return np.load(CACHE), np.load(CACHE_M)
    from run_experiment import load_pair
    y_video, y_music = load_pair(VIDEO, MUSIC, SR)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.save(CACHE, y_video)
    np.save(CACHE_M, y_music)
    return y_video, y_music


def chroma_delta(y):
    c = librosa.feature.chroma_cens(y=y, sr=SR, hop_length=HOP)
    return np.diff(c, axis=1, prepend=c[:, :1])


def window_offset_votes(fv, fm, window_s=8.0, hop_s=4.0):
    """For each video window, find the local best lag via per-frame-band
    correlation restricted to that window."""
    win_frames = int(window_s * SR / HOP)
    step_frames = int(hop_s * SR / HOP)
    votes = []
    n_music_frames = fm.shape[1]
    for start in range(0, fv.shape[1] - win_frames, step_frames):
        seg = fv[:, start:start + win_frames]
        seg = (seg - seg.mean(axis=1, keepdims=True)) / (
            np.std(seg, axis=1, keepdims=True) + 1e-12)
        best = None
        corr_curve = np.zeros(fm.shape[1] + win_frames - 1)
        for band in range(seg.shape[0]):
            row = (fm[band] - fm[band].mean()) / (np.std(fm[band]) + 1e-12)
            corr_curve += signal.correlate(row, seg[band], mode="full",
                                           method="fft")
        k = int(np.argmax(corr_curve))
        lag = k - (win_frames - 1)
        offset = -(lag * HOP) / SR
        votes.append({
            "video_t0": round(start * HOP / SR, 2),
            "video_t1": round((start + win_frames) * HOP / SR, 2),
            "best_local_offset": round(offset, 3),
            "local_peak_z": round(_correlation_z_score(corr_curve), 2),
        })
    return votes


def main():
    y_video, y_music = load_audio()
    print(f"video {len(y_video)/SR:.2f}s, music {len(y_music)/SR:.2f}s")

    fv = chroma_delta(y_video)
    fm = chroma_delta(y_music)
    chroma_corr = _correlate_feature_rows(fv, fm)

    onset_video = librosa.onset.onset_strength(y=y_video, sr=SR, hop_length=HOP)
    onset_music = librosa.onset.onset_strength(y=y_music, sr=SR, hop_length=HOP)
    onset_corr = signal.correlate(onset_music - onset_music.mean(),
                                  onset_video - onset_video.mean(),
                                  mode="full", method="fft")

    hybrid_corr = _normalize_correlation(chroma_corr) + 0.2 * _normalize_correlation(
        onset_corr)

    n_video_frames = fv.shape[1]

    def top(corr, n=8):
        from experiments.low_snr_alignment.harness import top_candidates
        return top_candidates(corr, n_video_frames, HOP, SR, n=n)

    out = {
        "chroma_top": top(chroma_corr),
        "hybrid_top": top(hybrid_corr),
        "onset_top": top(onset_corr),
    }

    print("\nTop chroma peaks:")
    for c in out["chroma_top"]:
        print(f"  offset {c['offset_s']:+8.3f}s  corr={c['corr']:.1f}")
    print("Top hybrid peaks:")
    for c in out["hybrid_top"]:
        print(f"  offset {c['offset_s']:+8.3f}s  corr={c['corr']:.2f}")
    print("Top onset peaks:")
    for c in out["onset_top"]:
        print(f"  offset {c['offset_s']:+8.3f}s  corr={c['corr']:.2f}")

    # Where does the TRUE candidate (+12.42) rank in the chroma curve?
    def rank_of(corr, offset, tol_frames=6):
        lag = int(round(-offset * SR / HOP))
        k = lag + (n_video_frames - 1)
        lo, hi = max(0, k - tol_frames), min(len(corr), k + tol_frames + 1)
        window_val = corr[lo:hi].max()
        peaks, _ = signal.find_peaks(corr, distance=int(1.5 * SR / HOP))
        peak_vals = sorted(corr[peaks])[::-1]
        rank = sum(1 for v in peak_vals if v > window_val) + 1
        return rank, len(peaks), float(window_val)

    for off in (-1.9969, +12.4227):
        rank, total, val = rank_of(chroma_corr, off)
        print(f"\nchroma curve at offset {off:+.4f}: local corr={val:.1f}, "
              f"rank {rank}/{total} among independent peaks")
        rank, total, val = rank_of(hybrid_corr, off)
        print(f"hybrid curve at offset {off:+.4f}: local corr={val:.2f}, "
              f"rank {rank}/{total}")

    # Per-window offset votes (which video segments vote for which offset)
    print("\nPer-window best local offset (chroma):")
    votes = window_offset_votes(fv, fm)
    for v in votes:
        print(f"  video {v['video_t0']:6.1f}-{v['video_t1']:6.1f}s -> "
              f"{v['best_local_offset']:+8.3f}s (local z={v['local_peak_z']:.2f})")
    out["window_votes"] = votes

    # stereo check
    import tempfile, uuid, imageio_ffmpeg
    from auto_sync import extract_audio
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = tempfile.gettempdir()
    wavs = []
    try:
        for tag, src in (("v", VIDEO), ("m", MUSIC)):
            w = os.path.join(tmp, f"ra_st_{tag}_{uuid.uuid4().hex}.wav")
            cmd = [ffmpeg, "-y", "-i", src, "-vn", "-acodec", "pcm_s16le",
                   "-ar", str(SR), "-ac", "2", w]
            import subprocess
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            wavs.append(w)
        yv2, _ = librosa.load(wavs[0], sr=SR, mono=False)
        ym2, _ = librosa.load(wavs[1], sr=SR, mono=False)
    finally:
        for w in wavs:
            if os.path.exists(w):
                os.remove(w)
    stereo = {}
    if yv2.ndim == 2:
        for name, idx in (("L", 0), ("R", 1)):
            corr = _correlate_feature_rows(
                chroma_delta(np.ascontiguousarray(yv2[idx])),
                chroma_delta(np.ascontiguousarray(ym2[idx])))
            z = _correlation_z_score(corr)
            lag = int(np.argmax(corr)) - (chroma_delta(yv2[idx]).shape[1] - 1)
            stereo[name] = {"offset": round(-(lag * HOP) / SR, 3), "z": round(float(z), 2)}
        # mid/side
        mid_v = yv2.mean(axis=0); side_v = yv2[0] - yv2[1]
        mid_m = ym2.mean(axis=0); side_m = ym2[0] - ym2[1]
        corr = _correlate_feature_rows(chroma_delta(mid_v), chroma_delta(mid_m))
        lag = int(np.argmax(corr)) - (chroma_delta(mid_v).shape[1] - 1)
        stereo["mid"] = {"offset": round(-(lag * HOP) / SR, 3),
                         "z": round(float(_correlation_z_score(corr)), 2)}
        out["stereo"] = stereo
        print(f"\nStereo chroma alignment: {stereo}")

    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "failure_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nsaved {out_path}")


if __name__ == "__main__":
    main()
