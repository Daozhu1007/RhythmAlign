"""RA-1.2B expanded synthetic-null calibration.

RA-1.2A calibrated against N=5 no-signal realizations — useful evidence, not
sufficient threshold calibration. This script runs a materially broader
synthetic null population and records per-family DISTRIBUTIONS (not just
maxima), plus the joint family-coincidence risk that CASE A (dual-family
agreement) depends on, plus any Engine v2 false-accept.

Run:  python experiments/low_snr_alignment/calibrate_nulls.py --n 30 \
          --json results/null_calibration.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from experiments.low_snr_alignment.synthetic_eval import (  # noqa: E402
    make_music,
    make_recording,
    SR,
)
import alignment_engine_v2 as eng  # noqa: E402


def family_stats(fr, sr=SR, hop=512):
    """Per-family null metrics for one realization."""
    if fr.error or fr.curve.size == 0:
        return {"method": fr.method, "error": fr.error}
    min_sep = max(1, int(1.5 * sr / hop))
    peaks = eng._independent_peak_indices(fr.curve, min_sep)
    margin = None
    if len(peaks) >= 2 and fr.curve[peaks[1]] > 0:
        margin = float(fr.curve[peaks[0]] / fr.curve[peaks[1]])
    top1 = eng._index_to_offset(int(peaks[0]), fr.n_video_frames, hop, sr)
    return {
        "method": fr.method,
        "z": fr.z,
        "top1_offset_s": round(top1, 4),
        "margin": margin,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    music = make_music()
    per_family = {m: {"z": [], "margin": [], "top1": []}
                  for m in ("hybrid", "onset", "pcen", "pcen_hpss")}
    engine_accepts = []
    joint_top1_coincidences = 0
    tol = eng.DEFAULT_POLICY.cluster_tol_s

    for i in range(args.n):
        video = make_recording(music, true_offset=5.10, music_gain=0.0,
                               noise_gain=0.02, tap_gain=0.30, seed=100 + i)
        fams = eng._run_generators(video, music, SR, 512)
        stats = [family_stats(f) for f in fams]
        for s in stats:
            if s.get("error") or "z" not in s:
                continue
            per_family[s["method"]]["z"].append(s["z"])
            if s["margin"] is not None:
                per_family[s["method"]]["margin"].append(s["margin"])
            per_family[s["method"]]["top1"].append(s["top1_offset_s"])

        hybrid_top1 = next((s["top1_offset_s"] for s in stats
                            if s["method"] == "hybrid" and "top1_offset_s" in s),
                           None)
        pcen_top1 = next((s["top1_offset_s"] for s in stats
                          if s["method"] == "pcen_hpss"
                          and "top1_offset_s" in s), None)
        if hybrid_top1 is not None and pcen_top1 is not None \
                and abs(hybrid_top1 - pcen_top1) <= tol:
            joint_top1_coincidences += 1

        decision = eng.decide_alignment(video, music)
        if decision.accepted:
            engine_accepts.append({
                "realization": i,
                "offset": decision.offset,
                "reason_code": decision.reason_code,
                "families": decision.evidence["families"],
            })
        print(f"null {i:3d}: "
              + " ".join(f"{s['method']}={s.get('z', 0):5.2f}" for s in stats)
              + f" -> {decision.status} ({decision.reason_code})")

    summary = {}
    for m, d in per_family.items():
        z = np.array(d["z"])
        mg = np.array(d["margin"]) if d["margin"] else np.array([np.nan])
        summary[m] = {
            "z": {"min": float(z.min()), "mean": float(z.mean()),
                  "q95": float(np.quantile(z, 0.95)),
                  "q99": float(np.quantile(z, 0.99)), "max": float(z.max())},
            "margin": {"min": float(np.nanmin(mg)),
                       "mean": float(np.nanmean(mg)),
                       "q95": float(np.nanquantile(mg, 0.95)),
                       "max": float(np.nanmax(mg))},
        }
        print(f"{m:10s} z q95={summary[m]['z']['q95']:5.2f} "
              f"max={summary[m]['z']['max']:5.2f} | "
              f"margin max={summary[m]['margin']['max']:.3f}")

    print(f"\njoint tonal#1/pcen_hpss#1 coincidences (|delta| <= {tol}s): "
          f"{joint_top1_coincidences}/{args.n}")
    print(f"engine false accepts: {len(engine_accepts)}/{args.n}")

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        payload = {
            "n_realizations": args.n,
            "config": {"sr": SR, "hop": 512, "video_s": 92.0, "music_s": 64.0,
                       "noise_gain": 0.02, "tap_gain": 0.30},
            "per_family": {m: {"z": d["z"], "margin": d["margin"]}
                           for m, d in per_family.items()},
            "summary": summary,
            "joint_top1_coincidences": joint_top1_coincidences,
            "engine_false_accepts": engine_accepts,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"saved {args.json}")
    return 1 if engine_accepts else 0


if __name__ == "__main__":
    sys.exit(main())
