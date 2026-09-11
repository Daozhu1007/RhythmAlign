"""PCEN hyper-parameter sweep for RA-1.2A.

Scores candidate PCEN configurations against:
  - the real failing pair (want: top-1 = +12.42 s with a wide margin)
  - a synthetic no-signal pair (want: LOW null Z, i.e. abstain)
  - a synthetic low-SNR tap pair (want: correct top-1)
  - a synthetic strong pair (want: correct top-1, no regression)

Run:  python experiments/low_snr_alignment/pcen_sweep.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import librosa

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from experiments.low_snr_alignment.harness import (  # noqa: E402
    pcen_delta_features,
    _correlate_rows,
    _correlation_z_score,
    top_candidates,
)
from experiments.low_snr_alignment.synthetic_eval import (  # noqa: E402
    make_music,
    make_recording,
)

CACHE_V = os.path.join(_REPO_ROOT, "results", "rep_y_video.npy")
CACHE_M = os.path.join(_REPO_ROOT, "results", "rep_y_music.npy")
REAL_OFFSET = 12.4227  # independently established ground truth (see report)


def robust_z(corr):
    med = np.median(corr)
    mad = np.median(np.abs(corr - med)) + 1e-12
    return (np.max(corr) - med) / (1.4826 * mad)


def evaluate(yv, ym, sr, hop, expect, n_mels, fmax, positive_only, zmode):
    kw = dict(n_mels=n_mels, fmax=fmax, positive_only=positive_only)
    fv = pcen_delta_features(yv, sr, hop, **kw)
    fm = pcen_delta_features(ym, sr, hop, **kw)
    corr = _correlate_rows(fv, fm)
    z = _correlation_z_score(corr)
    rz = robust_z(corr)
    tops = top_candidates(corr, fv.shape[1], hop, sr, n=3)
    best = tops[0]["offset_s"]
    margin = (tops[0]["corr"] / (tops[1]["corr"] + 1e-12)
              if len(tops) > 1 else float("inf"))
    err = abs(best - expect) if expect is not None else float("nan")
    return {
        "best": best, "err": err, "z": round(float(z), 2),
        "robust_z": round(float(rz), 2), "margin": round(float(margin), 3),
        "top2": [t["offset_s"] for t in tops],
    }


def main():
    yv = np.load(CACHE_V)
    ym = np.load(CACHE_M)

    music = make_music()
    video_null = make_recording(music, true_offset=5.10, music_gain=0.0,
                                noise_gain=0.02, tap_gain=0.30)
    video_low = make_recording(music, true_offset=13.60, music_gain=0.012,
                               noise_gain=0.008, tap_gain=0.30)
    video_strong = make_recording(music, true_offset=7.30, music_gain=0.5,
                                  noise_gain=0.004)

    # resampled copies for the 11025 configs
    yv11 = librosa.resample(yv, orig_sr=22050, target_sr=11025)
    ym11 = librosa.resample(ym, orig_sr=22050, target_sr=11025)
    v_null11 = librosa.resample(video_null, orig_sr=22050, target_sr=11025)
    v_low11 = librosa.resample(video_low, orig_sr=22050, target_sr=11025)
    v_strong11 = librosa.resample(video_strong, orig_sr=22050, target_sr=11025)
    music11 = librosa.resample(music, orig_sr=22050, target_sr=11025)

    configs = []
    for sr, hop, yv_, ym_, vn, vl, vs in (
        (22050, 512, yv, ym, video_null, video_low, video_strong),
        (11025, 256, yv11, ym11, v_null11, v_low11, v_strong11),
        (11025, 512, yv11, ym11, v_null11, v_low11, v_strong11),
    ):
        for n_mels in (64, 96):
            for fmax in (None, 4000, 5500):
                for positive_only in (True, False):
                    configs.append((sr, hop, yv_, ym_, vn, vl, vs,
                                    n_mels, fmax, positive_only))

    rows = []
    for (sr, hop, yv_, ym_, vn, vl, vs, n_mels, fmax, pos) in configs:
        t0 = time.perf_counter()
        real = evaluate(yv_, ym_, sr, hop, REAL_OFFSET, n_mels, fmax, pos, "z")
        null = evaluate(vn, music if sr == 22050 else music11, sr, hop,
                        None, n_mels, fmax, pos, "z")
        low = evaluate(vl, music if sr == 22050 else music11, sr, hop,
                       13.60, n_mels, fmax, pos, "z")
        strong = evaluate(vs, music if sr == 22050 else music11, sr, hop,
                          7.30, n_mels, fmax, pos, "z")
        runtime = time.perf_counter() - t0
        rows.append({
            "sr": sr, "hop": hop, "n_mels": n_mels,
            "fmax": fmax or "nyquist", "pos_only": pos,
            "real_err": round(real["err"], 3), "real_z": real["z"],
            "real_margin": real["margin"], "real_best": real["best"],
            "null_z": null["z"], "low_err": round(low["err"], 3),
            "low_z": low["z"], "strong_err": round(strong["err"], 3),
            "strong_z": strong["z"], "runtime_s": round(runtime, 1),
        })

    rows.sort(key=lambda r: (r["real_err"], -r["real_margin"]))
    hdr = (f"{'sr':>5} {'hop':>3} {'mels':>4} {'fmax':>7} {'pos':>5} | "
           f"{'real_err':>8} {'real_z':>6} {'margin':>6} | "
           f"{'null_z':>6} | {'low_err':>7} {'low_z':>5} | "
           f"{'str_err':>7} {'str_z':>5} | {'rt':>5}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['sr']:>5} {r['hop']:>3} {r['n_mels']:>4} {r['fmax']:>7} "
              f"{str(r['pos_only']):>5} | {r['real_err']:>8.3f} "
              f"{r['real_z']:>6.2f} {r['real_margin']:>6.3f} | "
              f"{r['null_z']:>6.2f} | {r['low_err']:>7.3f} {r['low_z']:>5.2f} | "
              f"{r['strong_err']:>7.3f} {r['strong_z']:>5.2f} | "
              f"{r['runtime_s']:>5.1f}")


if __name__ == "__main__":
    main()
