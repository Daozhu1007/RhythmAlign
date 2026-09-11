"""Synthetic regression suite for RA-1.2A.

Fully self-contained: music and "recordings" are synthesized with numpy, so
no media assets are needed and every case has an exact known offset.

Cases cover: strong music, attenuated music, strong transient interference,
repeated structure, and no shared signal (must abstain).

Run:  python experiments/low_snr_alignment/synthetic_eval.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from experiments.low_snr_alignment.harness import (  # noqa: E402
    hybrid_method,
    onset_method,
    pcen_hpss_method,
    pcen_method,
    logmel_flux_method,
    production_reliability,
    default_reliability,
)

SR = 22050
HOP = 512
TOLERANCE_S = 0.15  # ~6 hops; alignment considered correct within this window


# ---------------------------------------------------------------------------
# deterministic synthetic audio
# ---------------------------------------------------------------------------

def make_music(duration_s=64.0, seed=7, loop_s=None):
    """Simple tonal piece: chord pads + bass + kick/snare + arpeggio lead."""
    rng = np.random.default_rng(seed)
    n = int(duration_s * SR)
    t = np.arange(n) / SR
    bpm = 128.0
    beat = 60.0 / bpm

    chords = [
        (261.63, 329.63, 392.00),   # C
        (196.00, 246.94, 392.00),   # G
        (220.00, 261.63, 329.63),   # Am
        (174.61, 220.00, 261.63),   # F
    ]
    y = np.zeros(n)
    bar = beat * 4
    n_bars = int(np.ceil(duration_s / bar))
    for b in range(n_bars):
        chord = chords[b % len(chords)]
        t0 = b * bar
        i0 = int(t0 * SR)
        i1 = min(n, int((t0 + bar) * SR))
        tt = t[i0:i1] - t0
        env = 0.5 * (1 + np.cos(2 * np.pi * tt / bar - np.pi))
        pad = sum(np.sin(2 * np.pi * f * tt) for f in chord)
        y[i0:i1] += 0.22 * pad * env
        # bass on beats 1 and 3
        for beat_i in (0, 2):
            bs = int((t0 + beat_i * beat) * SR)
            be = min(n, bs + int(beat * SR))
            if bs < n:
                tb = t[bs:be] - (t0 + beat_i * beat)
                y[bs:be] += 0.30 * np.sin(2 * np.pi * chord[0] / 2 * tb) * \
                    np.exp(-tb * 3)
    # drums
    kick_t = np.arange(0, duration_s, beat)
    for kt in kick_t:
        i0 = int(kt * SR)
        i1 = min(n, i0 + int(0.12 * SR))
        if i0 < n:
            tk = t[i0:i1] - kt
            y[i0:i1] += 0.55 * np.sin(2 * np.pi * 55 * tk) * np.exp(-tk * 30)
    for st in np.arange(beat / 2, duration_s, beat):
        i0 = int(st * SR)
        i1 = min(n, i0 + int(0.08 * SR))
        if i0 < n:
            ts_ = t[i0:i1] - st
            y[i0:i1] += 0.18 * rng.standard_normal(i1 - i0) * np.exp(-ts_ * 60)
    # arpeggio lead
    step = beat / 2
    for k in range(int(duration_s / step)):
        chord = chords[int((k * step) // bar) % len(chords)]
        f = chord[int(k) % 3] * 2
        i0 = int(k * step * SR)
        i1 = min(n, i0 + int(step * SR))
        tl = t[i0:i1] - k * step
        y[i0:i1] += 0.12 * np.sin(2 * np.pi * f * tl) * np.exp(-tl * 8)

    if loop_s is not None:
        # make structure deliberately repetitive: tile one loop
        loop_n = int(loop_s * SR)
        tile = y[:loop_n]
        reps = int(np.ceil(n / loop_n))
        y = np.tile(tile, reps)[:n]
    peak = np.max(np.abs(y))
    return (y / peak * 0.9).astype(np.float32)


def make_taps(duration_s, rate_hz=8.0, gain=0.15, seed=11):
    """Player tap transients: sharp decaying clicks on a steady grid + jitter."""
    rng = np.random.default_rng(seed)
    n = int(duration_s * SR)
    y = np.zeros(n)
    period = 1.0 / rate_hz
    tt = np.arange(int(0.02 * SR)) / SR
    click = np.exp(-tt * 120) * np.sin(2 * np.pi * 1900 * tt)
    t = 0.5
    while t < duration_s - 0.1:
        i0 = int((t + rng.uniform(-0.01, 0.01)) * SR)
        i1 = min(n, i0 + len(click))
        if i0 >= 0:
            y[i0:i1] += gain * click[: i1 - i0]
        t += period * rng.uniform(0.9, 1.1)
    return y


def make_recording(music, true_offset, music_gain, noise_gain, tap_gain=0.0,
                   seed=3):
    """video(t) = music(t - offset)*gain + noise + taps. Returns video audio."""
    rng = np.random.default_rng(seed)
    n_video = int(92.0 * SR)
    y = music_gain * np.random.default_rng(seed + 1).standard_normal(n_video) * 0  # placeholder
    y = np.zeros(n_video)
    off_i = int(true_offset * SR)
    src = np.zeros(n_video + len(music) + abs(off_i))
    if off_i >= 0:
        # video t plays music (t - offset) -> place music starting at off_i
        src[off_i:off_i + len(music)] = music
    y = src[:n_video] * music_gain
    y += noise_gain * rng.standard_normal(n_video)
    if tap_gain > 0:
        y += make_taps(n_video / SR, gain=tap_gain, seed=seed + 2)
    peak = np.max(np.abs(y)) + 1e-9
    return (y / peak * 0.95).astype(np.float32)


# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------

def build_cases():
    music = make_music()
    looped = make_music(loop_s=8.0)
    cases = [
        ("strong_music", music, dict(true_offset=7.30, music_gain=0.5,
                                     noise_gain=0.004)),
        ("attenuated_music", music, dict(true_offset=21.70, music_gain=0.02,
                                         noise_gain=0.006)),
        ("low_snr_taps", music, dict(true_offset=13.60, music_gain=0.012,
                                     noise_gain=0.008, tap_gain=0.30)),
        ("repeated_structure", looped, dict(true_offset=9.80, music_gain=0.30,
                                            noise_gain=0.004)),
        ("no_shared_signal", music, dict(true_offset=5.10, music_gain=0.0,
                                         noise_gain=0.02, tap_gain=0.30)),
    ]
    return cases


def run_nulls(n_realizations, music):
    """Null distribution: no shared signal, several noise/tap realizations.

    Reports the max-Z and top-peak margin each method reaches on pure
    interference — the empirical floor any accept threshold must clear.
    """
    print(f"\nnull distribution ({n_realizations} realizations, "
          f"no shared signal):")
    methods = {
        "hybrid": hybrid_method,
        "onset": onset_method,
        "pcen": lambda v, m: pcen_method(v, m, SR, HOP, n_mels=96,
                                         fmax=4000.0, positive_only=True),
        "pcen_hpss": pcen_hpss_method,
    }
    stats = {name: {"z": [], "margin": [], "offsets": []}
             for name in methods}
    for i in range(n_realizations):
        video = make_recording(music, true_offset=5.10, music_gain=0.0,
                               noise_gain=0.02, tap_gain=0.30, seed=100 + i)
        for name, fn in methods.items():
            r = fn(video, music)
            stats[name]["z"].append(r["z_score"])
            if r["peak_margin"] is not None:
                stats[name]["margin"].append(r["peak_margin"])
            stats[name]["offsets"].append(r["offset_s"])
    for name, s in stats.items():
        z = np.array(s["z"])
        m = np.array(s["margin"]) if s["margin"] else np.array([0.0])
        print(f"  {name:10s} z: min={z.min():5.2f} max={z.max():5.2f} "
              f"mean={z.mean():5.2f} | margin: min={m.min():.3f} "
              f"max={m.max():.3f}")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--nulls", type=int, default=0,
                    help="also run N no-signal null realizations")
    args = ap.parse_args()

    music = make_music()
    if args.nulls:
        run_nulls(args.nulls, music)
        return 0

    runners = [
        ("hybrid", lambda v, m: hybrid_method(v, m, SR, HOP)),
        ("onset", lambda v, m: onset_method(v, m, SR, HOP)),
        ("pcen", lambda v, m: pcen_method(v, m, SR, HOP, n_mels=96,
                                          fmax=4000.0, positive_only=True)),
        ("pcen_hpss", lambda v, m: pcen_hpss_method(v, m, SR, HOP)),
        ("logmel_flux", lambda v, m: logmel_flux_method(v, m, SR, HOP)),
    ]
    rows = []
    all_ok = True
    for name, music, kwargs in build_cases():
        gt = kwargs["true_offset"]
        video = make_recording(music, **kwargs)
        no_signal = kwargs["music_gain"] == 0.0
        for label, fn in runners:
            r = fn(video, music)
            prod = production_reliability(r)
            r["reliable"] = prod if prod is not None else default_reliability(r)
            err = abs(r["offset_s"] - gt)
            if no_signal:
                ok = not r["reliable"]
                verdict = "abstain-ok" if ok else "FALSE-CONFIDENT"
            else:
                ok = err <= TOLERANCE_S
                verdict = "ok" if ok else "WRONG"
            all_ok &= ok
            rows.append({
                "case": name, "method": label, "ground_truth": gt,
                "offset": r["offset_s"], "z": r["z_score"],
                "ratio": r["independent_peak_ratio"],
                "margin": r["peak_margin"],
                "reliable": r["reliable"], "error": round(err, 4),
                "verdict": verdict, "runtime_s": r["runtime_s"],
            })
            print(f"{name:20s} {label:12s} off={r['offset_s']:+8.3f} "
                  f"gt={gt:+6.2f} z={r['z_score']:5.2f} "
                  f"margin={r['peak_margin']} "
                  f"rel={r['reliable']} -> {verdict}")

    print()
    n_false = sum(1 for r in rows if r["verdict"] == "FALSE-CONFIDENT")
    n_wrong = sum(1 for r in rows if r["verdict"] == "WRONG")
    print(f"summary: {len(rows)} evaluations, {n_wrong} wrong, "
          f"{n_false} false-confident (no-signal)")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
        print(f"saved {args.json}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
