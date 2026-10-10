"""Generate measured evidence and private loudness-matched listening examples.

Run as python -m experiments.audio_progress.validate [--video ... --music ...
--accepted ...]. All actual media and detailed provenance stay under results/.
"""
import argparse
import ast
import json
import subprocess
import time
import types
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from scipy.io import wavfile

import alignment_engine_v2 as eng
import auto_sync
from .media_checks import (
    SR, amplitude, decode, ffmpeg, file_hash, loudness, make_pair, packet_timing,
    signal_metrics, tone, video_hash,
)

BASE = "befa8379e14f150f801c74b7c7a9b470a8e707f4"
PRESETS = {"arcade_120_70": (1.2, 0.7), "mobile_200_50": (2, 0.5),
           "mobile_200_35": (2, 0.35), "mobile_200_25": (2, 0.25), "desktop_100_90": (1, 0.9)}


def legacy_module():
    source = subprocess.check_output(["git", "show", f"{BASE}:auto_sync.py"]).decode("utf-8")
    module = types.ModuleType("released_auto_sync")
    exec(compile(source, "released_auto_sync.py", "exec"), module.__dict__)
    return module


def engine_integrity():
    old = ast.parse(subprocess.check_output(["git", "show", f"{BASE}:alignment_engine_v2.py"]).decode("utf-8"))
    new = ast.parse(Path("alignment_engine_v2.py").read_text(encoding="utf-8"))
    old_nodes = {n.name: n for n in old.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    new_nodes = {n.name: n for n in new.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    names = set(old_nodes) - {"find_offset_v2"}
    assert all(ast.dump(old_nodes[n]) == ast.dump(new_nodes[n]) for n in names)
    assert set(old_nodes) == set(new_nodes)
    for filename in ("alignment_waveform.py", "app_info.py", "update.json", "bundled_update.json",
                     "config.json", "RhythmAlign.spec", "RhythmAlign.iss"):
        baseline = subprocess.check_output(["git", "show", f"{BASE}:{filename}"]).decode("utf-8")
        assert baseline.replace("\r\n", "\n") == Path(filename).read_text(encoding="utf-8")
    return {"baseline": BASE, "unchanged_engine_definitions": len(names),
            "algorithm_and_release_files_unchanged": True,
            "entrypoint_change": "optional observational stage callbacks only"}


def synth(root, old):
    video, music = make_pair(root / "inputs")
    rows = []
    for preset, (ov, mv) in PRESETS.items():
        pair = {}
        for variant, exporter in (("released", old.mix_and_export), ("stable", auto_sync.mix_and_export)):
            path = root / f"{preset}_{variant}.mp4"
            exporter(str(video), str(music), 2, str(path), vol_original=ov, vol_music=mv)
            audio = decode(path)
            pair[variant] = {
                "original_gains": [amplitude(audio, 440, a, b) / 0.2
                                   for a, b in ((0.5, 1.5), (2.5, 3.5), (4.1, 4.6), (6.5, 7.5))],
                "music_gain_overlap": amplitude(audio, 880, 2.5, 3.5) / 0.3,
                **signal_metrics(audio), **loudness(path),
            }
        rows.append({"preset": preset, "percentages": [ov * 100, mv * 100], **pair})
    video, music = make_pair(root / "strong_inputs", amplitude=0.95)
    wavfile.write(music, SR, tone(2, 440, 0.95).astype(np.float32))
    strong = {}
    for variant, exporter in (("released", old.mix_and_export), ("stable", auto_sync.mix_and_export)):
        path = root / f"strong_{variant}.mp4"
        exporter(str(video), str(music), 2, str(path), vol_original=2, vol_music=2)
        audio = decode(path)
        strong[variant] = {**signal_metrics(audio), **loudness(path),
                           "original_gain_before": amplitude(audio, 440, 0.5, 1.5) / 0.95,
                           "original_gain_after": amplitude(audio, 440, 6.5, 7.5) / 0.95}
    rows.append({"preset": "correlated_full_peaks_200_200", **strong})
    return rows


def real(root, old, video, music, accepted):
    sources = {"video": video, "reference": music}
    if accepted:
        sources["existing_synced"] = accepted
    hashes = {key: file_hash(path) for key, path in sources.items()}
    stages = []
    decision = eng.find_offset_v2(str(video), str(music), stage_callback=stages.append)
    assert decision.accepted, decision.reason_code
    offset = decision.offset
    rows = {}
    exports = {}
    for variant in ("released_200_50", "stable_200_50", "stable_200_35", "stable_200_25"):
        mv = int(variant.rsplit("_", 1)[1]) / 100
        path = root / f"awaken_{variant}.mp4"
        exporter = old.mix_and_export if variant.startswith("released") else auto_sync.mix_and_export
        events, logs = [], []
        start = time.monotonic()
        kwargs = {"ui_progress_callback": lambda *args: events.append(args),
                  "tr": lambda key, *args: f"{key}: {args}" if args else key,
                  "ui_log_callback": logs.append}
        exporter(str(video), str(music), offset, str(path), vol_original=2, vol_music=mv, **kwargs)
        wall = time.monotonic() - start
        audio = decode(path)
        rows[variant] = {**signal_metrics(audio), **loudness(path), "wall_s": wall,
                         "video_bitstream_equal": video_hash(video) == video_hash(path),
                         "output_sha256": file_hash(path), "progress": events, "logs": logs}
        rows[variant]["video_timing"] = packet_timing(path, "v")
        rows[variant]["audio_timing"] = packet_timing(path, "a")
        # Full decode validates video as well as audio, without touching sources.
        ffmpeg(["-v", "error", "-i", path, "-f", "null", "-"])
        exports[variant] = path
        print(variant, "done", round(wall, 2), "s", flush=True)
    rows["original_recording"] = {**signal_metrics(decode(video)), **loudness(video)}
    rows["original_recording"]["video_timing"] = packet_timing(video, "v")
    rows["original_recording"]["audio_timing"] = packet_timing(video, "a")
    rows["reference_music"] = {**signal_metrics(decode(music)), **loudness(music)}
    if accepted:
        rows["existing_synced"] = {**signal_metrics(decode(accepted)), **loudness(accepted)}
        exports["existing_synced"] = accepted
    # Equal integrated loudness per section, using constant attenuation only.
    # Common target is the quietest example, avoiding any A/B sample amplification.
    music_duration = auto_sync.get_video_duration(imageio_ffmpeg.get_ffmpeg_exe(), str(music))
    sections = {"music_heavy": (offset + 60, 15), "music_end": (offset + music_duration - 6, 15)}
    samples = {}
    for section, (start, length) in sections.items():
        raw = {}
        for variant, path in exports.items():
            clip = root / f"awaken_{section}_{variant}_raw.wav"
            ffmpeg(["-y", "-v", "error", "-i", path, "-ss", start, "-t", length,
                    "-vn", "-c:a", "pcm_f32le", clip])
            raw[variant] = (clip, loudness(clip)["integrated_lufs"])
        target = min(value[1] for value in raw.values()) - 0.1
        section_rows = {}
        for variant, (clip, lufs) in raw.items():
            matched = root / f"awaken_{section}_{variant}_matched.wav"
            ffmpeg(["-y", "-v", "error", "-i", clip, "-af", f"volume={target - lufs:.5f}dB",
                    "-c:a", "pcm_s24le", matched])
            section_rows[variant] = {"path": str(matched.resolve()), "raw_lufs": lufs,
                                     "attenuation_db": target - lufs, **loudness(matched)}
        samples[section] = {"video_start_s": start, "duration_s": length,
                            "target_lufs": target, "examples": section_rows}
    assert hashes == {key: file_hash(path) for key, path in sources.items()}
    assert not list(root.glob(".*.partial*"))
    return {"decision": decision.as_dict(), "analysis_stages": stages, "source_hashes": hashes,
            "source_files_unchanged": True, "measurements": rows, "listening_samples": samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path)
    parser.add_argument("--music", type=Path)
    parser.add_argument("--accepted", type=Path)
    parser.add_argument("--out", type=Path, default=Path("results/audio-progress"))
    args = parser.parse_args()
    root = args.out
    root.mkdir(parents=True, exist_ok=True)
    summary = {"integrity": engine_integrity()}
    old = legacy_module()
    summary["synthetic"] = synth(root, old)
    (root / "synthetic_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.video and args.music:
        summary["real_media"] = real(root, old, args.video, args.music, args.accepted)
    (root / "validation.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Evidence:", root.resolve() / "validation.json", flush=True)


if __name__ == "__main__":
    main()
