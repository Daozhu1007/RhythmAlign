"""Synthetic regression suite for RA-1.2B (expected-behavior semantics).

Fully self-contained: music and "recordings" are synthesized with numpy, so
no media assets are needed and every case has an exact known offset.

RA-1.2B semantics (replaces the RA-1.2A "all methods must succeed" logic):

- Each case declares the EXPECTED Alignment Engine v2 outcome:
    accept        -> engine must accept within tolerance of ground truth
    abstain       -> engine must abstain (no offset)
    no_wrong_accept -> engine may accept or abstain, but must never accept
                       an offset outside tolerance (content-ambiguous cases)
- Legacy baseline methods (hybrid, onset, pcen, pcen_hpss, logmel_flux) are
  recorded as OBSERVATIONS. A known wrong baseline row is reported as
  "known_baseline_failure" (informational); it never fails the suite.
- The suite fails (exit 1) only on engine_v2_regression rows.

Run:  python experiments/low_snr_alignment/synthetic_eval.py [--json OUT]
      [--nulls N] [--legacy]
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
)
from alignment_engine_v2 import (  # noqa: E402
    decide_alignment,
    STATUS_ACCEPTED,
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


def make_tiled_recording(music, loop_s=8.0, video_dur_s=92.0, music_gain=0.3,
                         noise_gain=0.004, seed=5):
    """A recording that contains the same music loop TILED — every 8 s span
    is identical, so no algorithm can prefer one placement. The expected
    engine outcome is an ambiguity abstain."""
    rng = np.random.default_rng(seed)
    n_video = int(video_dur_s * SR)
    loop = music[: int(loop_s * SR)]
    y = music_gain * np.tile(loop, int(np.ceil(video_dur_s / loop_s)))[:n_video]
    y = y + noise_gain * rng.standard_normal(n_video)
    peak = np.max(np.abs(y)) + 1e-9
    return (y / peak * 0.95).astype(np.float32)


# ---------------------------------------------------------------------------
# cases + expectations
# ---------------------------------------------------------------------------

EXPECT_ACCEPT = "accept"
EXPECT_ABSTAIN = "abstain"
EXPECT_NO_WRONG_ACCEPT = "no_wrong_accept"


def build_cases():
    music = make_music()
    looped = make_music(loop_s=8.0)
    cases = [
        # (name, music, recording kwargs, expectation, note, no_signal)
        ("strong_music", music,
         dict(true_offset=7.30, music_gain=0.5, noise_gain=0.004),
         EXPECT_ACCEPT, "healthy strong recording -> straightforward accept",
         False),
        ("attenuated_music", music,
         dict(true_offset=21.70, music_gain=0.02, noise_gain=0.006),
         EXPECT_ACCEPT, "quiet music, still shared signal -> accept", False),
        ("low_snr_taps", music,
         dict(true_offset=13.60, music_gain=0.012, noise_gain=0.008,
              tap_gain=0.30),
         EXPECT_ACCEPT,
         "RA-1.2A regression: plain pcen and flux pick wrong offsets here; "
         "engine must accept within tolerance", False),
        ("repeated_structure", looped,
         dict(true_offset=9.80, music_gain=0.30, noise_gain=0.004),
         EXPECT_NO_WRONG_ACCEPT,
         "looped music, single span in the recording; accept-correct or "
         "abstain, never a wrong confident offset", False),
        ("repeated_structure_tiled", looped,
         dict(loop_s=8.0),
         EXPECT_ABSTAIN,
         "recording contains the same 8 s loop tiled: evidence is genuinely "
         "non-unique -> must abstain", True),
        ("no_shared_signal", music,
         dict(true_offset=5.10, music_gain=0.0, noise_gain=0.02, tap_gain=0.30),
         EXPECT_ABSTAIN, "no shared signal -> must abstain", True),
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


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def run_suite(run_legacy=True):
    music = make_music()
    rows = []
    engine_failures = 0
    for name, case_music, kwargs, expectation, note, no_signal in build_cases():
        if name == "repeated_structure_tiled":
            video = make_tiled_recording(case_music, **kwargs)
            gt = None
        else:
            video = make_recording(case_music, **kwargs)
            gt = kwargs["true_offset"]

        t0 = time.perf_counter()
        decision = decide_alignment(video, case_music)
        engine_runtime = time.perf_counter() - t0

        accepted = decision.status == STATUS_ACCEPTED
        err = (abs(decision.offset - gt)
               if (accepted and gt is not None) else None)
        if expectation == EXPECT_ACCEPT:
            ok = accepted and err is not None and err <= TOLERANCE_S
        elif expectation == EXPECT_ABSTAIN:
            ok = not accepted
        else:  # no_wrong_accept
            ok = (not accepted) or (err is not None and err <= TOLERANCE_S)
        if not ok:
            engine_failures += 1
        failure_class = None if ok else "engine_v2_regression"

        rows.append({
            "case": name, "kind": "engine_v2",
            "expectation": expectation, "ground_truth": gt,
            "status": decision.status,
            "offset": None if decision.offset is None else round(decision.offset, 4),
            "error": None if err is None else round(err, 4),
            "reason_code": decision.reason_code,
            "families": decision.evidence["families"],
            "verdict": "pass" if ok else "FAIL",
            "failure_class": failure_class,
            "runtime_s": round(engine_runtime, 2),
            "note": note,
        })
        r = rows[-1]
        print(f"{name:26s} ENG {r['status']:9s} "
              f"off={r['offset'] if r['offset'] is None else format(r['offset'], '+8.3f')} "
              f"expect={expectation:14s} -> {r['verdict']} "
              f"({decision.reason_code})")

        if run_legacy:
            runners = [
                ("hybrid", lambda v, m: hybrid_method(v, m, SR, HOP)),
                ("onset", lambda v, m: onset_method(v, m, SR, HOP)),
                ("pcen", lambda v, m: pcen_method(v, m, SR, HOP, n_mels=96,
                                                  fmax=4000.0,
                                                  positive_only=True)),
                ("pcen_hpss", lambda v, m: pcen_hpss_method(v, m, SR, HOP)),
                ("logmel_flux",
                 lambda v, m: logmel_flux_method(v, m, SR, HOP)),
            ]
            for label, fn in runners:
                r = fn(video, case_music)
                if no_signal:
                    # No shared signal exists: "correct/wrong" is
                    # meaningless. A baseline above the production Z gate
                    # is confident garbage; below it, it effectively
                    # abstains.
                    base = ("false_confident_known_baseline"
                            if r["z_score"] >= 2.0 else "below_confidence")
                else:
                    wrong = (gt is not None
                             and abs(r["offset_s"] - gt) > TOLERANCE_S)
                    base = ("wrong_known_baseline" if wrong else "correct")
                rows.append({
                    "case": name, "kind": "baseline", "method": label,
                    "ground_truth": gt,
                    "offset": r["offset_s"], "z": r["z_score"],
                    "margin": r["peak_margin"],
                    "observation": base,
                    "runtime_s": r["runtime_s"],
                })
                print(f"{name:26s} {label:12s} off={r['offset_s']:+8.3f} "
                      f"z={r['z_score']:5.2f} [{base}]")
    return rows, engine_failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--nulls", type=int, default=0,
                    help="also run N no-signal null realizations")
    ap.add_argument("--no-legacy", action="store_true",
                    help="skip informational baseline method rows")
    args = ap.parse_args()

    music = make_music()
    if args.nulls:
        run_nulls(args.nulls, music)
        return 0

    rows, engine_failures = run_suite(run_legacy=not args.no_legacy)

    baseline_wrong = sum(1 for r in rows
                         if r["kind"] == "baseline"
                         and r["observation"].startswith("wrong"))
    baseline_false = sum(1 for r in rows
                         if r["kind"] == "baseline"
                         and r["observation"].startswith("false_confident"))
    n_engine = sum(1 for r in rows if r["kind"] == "engine_v2")
    print()
    print(f"summary: {n_engine} engine expectations, "
          f"{engine_failures} engine_v2_regression | "
          f"baseline observations: {baseline_wrong} wrong, "
          f"{baseline_false} false-confident (informational)")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        print(f"saved {args.json}")
    return 1 if engine_failures else 0


if __name__ == "__main__":
    sys.exit(main())
