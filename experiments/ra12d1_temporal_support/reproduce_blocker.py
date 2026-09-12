"""RA-1.2D1 Phase 1: reproduce the Astra release blocker on production main.

Runs the unmodified production Engine v2 entry point on the archived
minimum-regression pair:

    query    tr_lingduihua   (track.mp3 of 零对话)
    reference tr_yanwulieche (延误列车.mp3)

Expected (buggy) behavior: ACCEPT at offset ~ +1.462857 s with reason
ACCEPT_PRIMARY_WITH_CORROBORATION and geometric overlap ~ 148.57 s.

Writes experiments/ra12d1_temporal_support/results/blocker_reproduction.json.
Read-only with respect to production code.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import alignment_engine_v2 as eng  # noqa: E402
import librosa  # noqa: E402
import imageio_ffmpeg  # noqa: E402
from auto_sync import extract_audio  # noqa: E402

SR, HOP = 22050, 512
OUT = Path(__file__).resolve().parent / "results"
SOURCES = ROOT / "experiments/low_snr_alignment/local_sources.json"

QUERY, REFERENCE = "tr_lingduihua", "tr_yanwulieche"


def decode(path: Path) -> np.ndarray:
    """Decode to mono float32 at SR the same way the engine does."""
    tmp = OUT / f"_decode_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    extract_audio(imageio_ffmpeg.get_ffmpeg_exe(), str(path), str(tmp), SR)
    y, _ = librosa.load(str(tmp), sr=None, mono=True)
    tmp.unlink(missing_ok=True)
    return y


def per_family_cluster_diagnostics(decision, offset):
    """Diagnostics of the cluster nearest the reported offset."""
    for cl in decision.clusters:
        if offset is not None and abs(cl["offset_s"] - offset) < 1.0:
            return cl
    return None


def main() -> None:
    mapping = json.loads(SOURCES.read_text(encoding="utf-8"))
    video_path = Path(mapping["tracks"][QUERY])
    music_path = Path(mapping["tracks"][REFERENCE])
    t0 = time.perf_counter()
    decision = eng.find_offset_v2(str(video_path), str(music_path))
    wall = time.perf_counter() - t0

    record = {
        "task": "RA-1.2D1 blocker reproduction on unmodified production main",
        "production_head": "20d48169803a0e62e4379f197a51b92f9ac6555b",
        "query": {"id": QUERY, "path_sha256": hashlib.sha256(video_path.read_bytes()).hexdigest()},
        "reference": {"id": REFERENCE, "path_sha256": hashlib.sha256(music_path.read_bytes()).hexdigest()},
        "decision": decision.as_dict(),
        "engine_wall_time_s": round(wall, 3),
        "expected_failure_signature": {
            "status": "accepted",
            "offset_s": 1.4628571428571429,
            "reason_code": "ACCEPT_PRIMARY_WITH_CORROBORATION",
            "overlap_s": 148.57,
        },
    }
    cl = per_family_cluster_diagnostics(decision, decision.offset)
    record["accepted_cluster_diagnostics"] = cl

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "blocker_reproduction.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, default=float) + "\n",
        encoding="utf-8",
    )
    print(f"status={decision.status} offset={decision.offset} reason={decision.reason_code}")
    print(f"wall={wall:.2f}s  families={json.dumps(decision.evidence['families'])}")
    if cl:
        print(f"cluster overlap_s={cl['overlap_s']} families={list(cl['families'])}")


if __name__ == "__main__":
    main()
