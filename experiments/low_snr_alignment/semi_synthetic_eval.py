"""RA-1.2C semi-synthetic + hard-negative evaluation runner.

Subcommands
-----------
build-sources          Map plan source ids to local media paths (from the
                       gitignored local_corpus.json) and write the
                       gitignored local_sources.json. Validates split
                       coverage and disjointness.
select-hard-negatives  Feature-similarity search (chroma cosine, tempo
                       proximity, onset density, PCEN low-band cosine) over
                       the split-respecting candidate tracks; writes the
                       selected wrong-track pairings + metrics into the
                       committed plan (ids/metrics only).
run --split calibration|holdout
                       Build the split's cases (exact-GT positives, tiled
                       ambiguity cases, real hard negatives), run Engine v2,
                       classify outcomes, and write path-free evidence JSON.

All committed output is path-free: case ids and numbers only.
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

import librosa  # noqa: E402

from experiments.low_snr_alignment import semi_synthetic as ss  # noqa: E402
from alignment_engine_v2 import (  # noqa: E402
    decide_alignment,
    FAMILY_ONSET,
    FAMILY_PCEN,
    FAMILY_TONAL,
    STATUS_ACCEPTED,
)

PLAN_PATH = os.path.join(_HERE, "semi_synthetic_plan.json")
CORPUS_PATH = os.path.join(_HERE, "local_corpus.json")
SOURCES_PATH = os.path.join(_HERE, "local_sources.json")
RESULTS_DIR = os.path.join(_REPO_ROOT, "experiments", "low_snr_alignment",
                           "results")

SR = ss.SR

# corpus case id -> plan project id (ids only; no paths in this file)
RECORDING_PROJECT = {
    "lingduihua_132": "lingduihua",
    "lividi_132": "lividi",
    "drops_132": "drops",
    "yanwulieche_132": "yanwulieche",
    "baixiwang_132": "baixiwang",
    "goganjue_niaojia_132": "goganjue",
    "fenzhen_ds_1": "fenzhen",
    "fenzhen_ds_2": "fenzhen",
    "fenzhen_ds_3": "fenzhen",
    "fenzhen_ds_4": "fenzhen",
    "samesha_411": "samesha",
    "decision90": "decision90",
    "queen": "queen",
    "dancerobotdance_133": "drd",
    "bai39_134": "bai39",
    "hongzhoutian_135": "hongzhoutian",
    "haiditan_ds_0": "haiditan",
    "haiditan_ds_1": "haiditan",
    "haiditan_ds_2": "haiditan",
    "haiditan_ds_3": "haiditan",
    "haiditan_ds_4": "haiditan",
    "haiditan_ds_5": "haiditan",
    "letudive": "letudive",
    "leyixiaolao": "leyixiaolao",
    "chiyaoshuijiao": "chiyaoshuijiao",
    "babieta": "babieta",
    "caibushimo": "caibushimo",
    "maodunxinli": "maodunxinli",
    "maodunxinli_niaojia": "maodunxinli",
}


def load_plan():
    with open(PLAN_PATH, encoding="utf-8") as f:
        return json.load(f)


def audit_split(plan):
    """Thin wrapper over the pure audit in semi_synthetic (kept here so the
    CLI keeps one call site)."""
    return ss.audit_split(plan)


# ---------------------------------------------------------------------------
# build-sources
# ---------------------------------------------------------------------------


def cmd_build_sources(_args):
    with open(CORPUS_PATH, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    positives = [c for c in cases if c["class"].startswith("positive")]
    recordings = {}
    tracks = {}
    own_track = {}
    for c in positives:
        rid = c["case_id"]
        pid = RECORDING_PROJECT[rid]
        recordings[rid] = c["video"]
        tid = f"tr_{pid}"
        if tid not in tracks:
            tracks[tid] = c["music"]
        own_track[rid] = tracks[tid]
    sources = {
        "recordings": recordings,
        "tracks": tracks,
        "recording_own_track": own_track,
    }
    with open(SOURCES_PATH, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    plan = load_plan()
    problems = audit_split(plan)
    missing = [rid for pid in plan["split"]["projects"]
               for rid in plan["split"]["projects"][pid]["recordings"]
               if rid not in recordings]
    print(f"local_sources.json written: {len(recordings)} recordings, "
          f"{len(tracks)} tracks")
    print(f"split audit: {len(problems)} problems {problems}")
    print(f"missing recordings: {missing}")
    return 1 if (problems or missing) else 0


def _load_sources():
    with open(SOURCES_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# hard-negative similarity search
# ---------------------------------------------------------------------------


def _tempo_of(y):
    try:
        return float(librosa.feature.tempo(y=y, sr=SR)[0])
    except AttributeError:  # older librosa
        return float(librosa.beat.tempo(y=y, sr=SR)[0])


def source_summary(y):
    """Coarse similarity features used ONLY for negative construction."""
    chroma = librosa.feature.chroma_stft(y=y, sr=SR)
    chroma_vec = chroma.mean(axis=1)
    chroma_vec /= (np.linalg.norm(chroma_vec) + 1e-12)
    onset_rate = float(librosa.onset.onset_strength(y=y, sr=SR).mean())
    S = librosa.feature.melspectrogram(y=y, sr=SR, n_mels=96, fmin=30.0,
                                       fmax=4000.0, power=2.0)
    P = librosa.pcen(S, sr=SR, hop_length=512)
    pcen_vec = P[:32].mean(axis=1)
    pcen_vec /= (np.linalg.norm(pcen_vec) + 1e-12)
    return {
        "chroma": chroma_vec,
        "tempo": _tempo_of(y),
        "onset_rate": onset_rate,
        "pcen_low": pcen_vec,
    }


def cmd_select_hard_negatives(_args):
    import imageio_ffmpeg

    plan = load_plan()
    sources = _load_sources()
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    projects = plan["split"]["projects"]
    cal = set(plan["split"]["calibration_projects"])

    summaries = {}

    def summary_of(kind, sid, path):
        key = f"{kind}:{sid}"
        if key not in summaries:
            y = ss.load_audio_cached(path, sid.replace("_", "-"), ffmpeg_bin)
            summaries[key] = source_summary(y)
        return summaries[key]

    selected = []
    search_log = []
    groups = [("calibration", plan["hard_negatives_real"]["calibration_recordings"]),
              ("holdout", plan["hard_negatives_real"]["holdout_recordings"])]
    for split_name, recs in groups:
        for rid in recs:
            rec_project = _project_of_recording(rid, projects)
            pool = [pid for pid in projects
                    if (pid in cal) == (split_name == "calibration")
                    and pid != rec_project]
            rs = summary_of("rec", rid, sources["recordings"][rid])
            scored = []
            for pid in pool:
                tid = projects[pid]["track"]
                ts = summary_of("trk", tid, sources["tracks"][tid])
                chroma_cos = float(np.dot(rs["chroma"], ts["chroma"]))
                pcen_cos = float(np.dot(rs["pcen_low"], ts["pcen_low"]))
                tempo_diff = abs(rs["tempo"] - ts["tempo"])
                onset_diff = abs(rs["onset_rate"] - ts["onset_rate"])
                scored.append({
                    "track": tid,
                    "chroma_cos": round(chroma_cos, 4),
                    "pcen_low_cos": round(pcen_cos, 4),
                    "tempo_diff_bpm": round(tempo_diff, 2),
                    "onset_rate_diff": round(onset_diff, 4),
                })
            # rank-normalize each metric (higher = more similar), average.
            # tempo_diff and onset_rate_diff rank ascending (smaller=similar).
            for metric, invert in (("chroma_cos", False),
                                   ("pcen_low_cos", False),
                                   ("tempo_diff_bpm", True),
                                   ("onset_rate_diff", True)):
                order = sorted(scored, key=lambda r: r[metric],
                               reverse=not invert)
                for rank, row in enumerate(order):
                    row.setdefault("ranks", {})[metric] = rank
            for row in scored:
                row["mean_rank"] = round(
                    sum(row["ranks"].values()) / len(row["ranks"]), 2)
            scored.sort(key=lambda r: r["mean_rank"])
            best = scored[0]
            case_id = f"rhn_{'cal' if split_name == 'calibration' else 'ho'}_{rid}"
            selected.append({
                "case_id": case_id,
                "split": split_name,
                "recording": rid,
                "track": best["track"],
                "selection": best,
                "runner_candidates": scored[:3],
            })
            search_log.append({"recording": rid, "split": split_name,
                               "ranked": scored})
            print(f"{case_id}: best={best['track']} "
                  f"chroma={best['chroma_cos']} pcen={best['pcen_low_cos']} "
                  f"tempo_diff={best['tempo_diff_bpm']} "
                  f"onset_diff={best['onset_rate_diff']} "
                  f"mean_rank={best['mean_rank']}")

    plan["hard_negatives_real"]["selected"] = selected
    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "hard_negative_search_ra12c.json"),
              "w", encoding="utf-8") as f:
        json.dump({"search": search_log}, f, ensure_ascii=False, indent=2)
    problems = audit_split(plan)
    print(f"plan updated with {len(selected)} hard negatives; "
          f"split audit: {len(problems)} problems {problems}")
    return 1 if problems else 0


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def _cluster_at(decision, offset_s, tol=0.15):
    best = None
    for cl in decision.clusters:
        if abs(cl["offset_s"] - offset_s) <= tol:
            if best is None or cl["offset_s"] - offset_s < \
                    best["offset_s"] - offset_s:
                best = cl
    return best


def _family_null_stats(decision):
    """Path-free per-family evidence for threshold analysis: global curve Z
    + the strongest cluster Z/margin per family."""
    out = {"global_z": {}, "cluster_max_z": {}}
    for method, info in decision.evidence["families"].items():
        out["global_z"][method] = info["z"]
    cluster_max = {}
    for cl in decision.clusters:
        for fam, ev in cl["families"].items():
            z = ev["z_at_cluster"]
            if fam not in cluster_max or z > cluster_max[fam][0]:
                cluster_max[fam] = (z, ev["margin_at_cluster"])
    out["cluster_max_z"] = {
        fam: {"z": round(z, 3), "margin": margin}
        for fam, (z, margin) in cluster_max.items()
    }
    return out


def _evaluate_case(case, y_background, y_target, ffmpeg_bin):
    kind = case["kind"]
    if kind == "positive":
        mix, gt = ss.build_positive(
            y_background, y_target, case["offset_s"], case["gain_db"],
            case["condition"], case["seed"])
        v_dur, m_dur = len(mix) / SR, len(y_target) / SR
        ov = ss.usable_overlap_s(gt, v_dur, m_dur)
        assert ov >= 45.0, f"{case['case_id']}: overlap {ov:.1f}s"
        decision = decide_alignment(mix, y_target, sr=SR)
        outcome = ss.classify_positive(decision, gt, case["tolerance_s"])
        gt_cluster = _cluster_at(decision, gt)
        row = {
            "case_id": case["case_id"],
            "class": "semi_synthetic_positive",
            "level": case["level"],
            "ground_truth_offset_s": gt,
            "status": decision.status,
            "offset": None if decision.offset is None
            else round(decision.offset, 4),
            "error_s": None if decision.offset is None
            else round(abs(decision.offset - gt), 4),
            "reason_code": decision.reason_code,
            "outcome": outcome,
            "gt_cluster_families": None if gt_cluster is None
            else gt_cluster["families"],
            "family_null_stats": _family_null_stats(decision),
            "policy": decision.policy,
            "runtime_s": round(decision.runtime_s, 2),
        }
    elif kind == "tiled":
        mix, tile_s = ss.build_tiled(
            y_background, y_target, case["tile_s"], case["gain_db"],
            case["condition"], case["seed"])
        decision = decide_alignment(mix, y_target, sr=SR)
        tile_starts = list(np.arange(0.0, len(mix) / SR, tile_s))
        outcome = ss.classify_negative(decision, tile_starts_s=tile_starts)
        row = {
            "case_id": case["case_id"],
            "class": "semi_synthetic_tiled_ambiguity",
            "tile_s": tile_s,
            "status": decision.status,
            "offset": None if decision.offset is None
            else round(decision.offset, 4),
            "reason_code": decision.reason_code,
            "outcome": outcome,
            "family_null_stats": _family_null_stats(decision),
            "policy": decision.policy,
            "runtime_s": round(decision.runtime_s, 2),
        }
    elif kind == "hard_negative":
        decision = decide_alignment(y_background, y_target, sr=SR)
        outcome = ss.classify_negative(decision)
        row = {
            "case_id": case["case_id"],
            "class": "real_hard_negative",
            "status": decision.status,
            "offset": None if decision.offset is None
            else round(decision.offset, 4),
            "reason_code": decision.reason_code,
            "outcome": outcome,
            "selection": case.get("selection"),
            "family_null_stats": _family_null_stats(decision),
            "policy": decision.policy,
            "runtime_s": round(decision.runtime_s, 2),
        }
    else:
        raise ValueError(kind)
    return row


def _iter_split_cases(plan, split):
    projects = plan["split"]["projects"]
    levels = plan["levels"]
    for case in plan["positives"]:
        if case["split"] != split:
            continue
        lv = levels[case["level"]]
        yield {"kind": "positive", "case_id": case["case_id"],
               "background": case["background"], "target": case["target"],
               "offset_s": case["offset_s"], "gain_db": lv["gain_db"],
               "condition": lv["condition"], "seed": case["seed"],
               "tolerance_s": plan["tolerance_s"], "level": case["level"]}
    for case in plan["ambiguity_tiled"]:
        if case["split"] != split:
            continue
        yield {"kind": "tiled", "case_id": case["case_id"],
               "background": case["background"], "target": case["target"],
               "tile_s": case["tile_s"], "gain_db": case["gain_db"],
               "condition": case["condition"], "seed": case["seed"]}
    for entry in plan["hard_negatives_real"].get("selected", []):
        if entry["split"] != split:
            continue
        yield {"kind": "hard_negative", "case_id": entry["case_id"],
               "background": entry["recording"], "target": entry["track"],
               "selection": entry.get("selection")}


def cmd_run(args):
    import imageio_ffmpeg

    plan = load_plan()
    problems = audit_split(plan)
    if problems:
        print(f"split audit FAILED: {problems}")
        return 2
    sources = _load_sources()
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    out_path = os.path.join(
        RESULTS_DIR,
        f"semi_synthetic_{args.split}_ra12c.json")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = []
    if os.path.exists(out_path) and not args.fresh:
        with open(out_path, encoding="utf-8") as f:
            rows = json.load(f)
    done = {r["case_id"] for r in rows}

    audio_cache = {}

    def audio_of(kind, sid):
        key = f"{kind}:{sid}"
        if key not in audio_cache:
            path = (sources["recordings"] if kind == "rec"
                    else sources["tracks"])[sid]
            audio_cache[key] = ss.load_audio_cached(
                path, sid.replace("_", "-"), ffmpeg_bin)
        return audio_cache[key]

    cases = list(_iter_split_cases(plan, args.split))
    for i, case in enumerate(cases):
        if case["case_id"] in done:
            print(f"[{i + 1}/{len(cases)}] {case['case_id']}: cached")
            continue
        y_bg = audio_of("rec", case["background"])
        y_tg = audio_of("trk", case["target"])
        t0 = time.perf_counter()
        row = _evaluate_case(case, y_bg, y_tg, ffmpeg_bin)
        rows.append(row)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        off = row["offset"]
        print(f"[{i + 1}/{len(cases)}] {case['case_id']} "
              f"({row['class']}): {row['status']}@"
              f"{'None' if off is None else format(off, '+.3f')} "
              f"-> {row['outcome']} ({row['reason_code']}) "
              f"[{time.perf_counter() - t0:.1f}s]")

    n = len(rows)
    n_ca = sum(1 for r in rows if r.get("outcome") == ss.CORRECT_ACCEPT)
    n_sa = sum(1 for r in rows if r.get("outcome") == ss.SAFE_ABSTAIN)
    n_wa = sum(1 for r in rows if r.get("outcome") == ss.WRONG_ACCEPT)
    n_tc = sum(1 for r in rows
               if r.get("outcome") == "TILE_CONSISTENT_ACCEPT")
    print(f"\nsummary [{args.split}]: {n} cases -> "
          f"{n_ca} CORRECT_ACCEPT, {n_sa} SAFE_ABSTAIN, "
          f"{n_wa} WRONG_ACCEPT, {n_tc} TILE_CONSISTENT_ACCEPT")
    return 1 if n_wa else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build-sources")
    sub.add_parser("select-hard-negatives")
    run_p = sub.add_parser("run")
    run_p.add_argument("--split", choices=["calibration", "holdout"],
                       required=True)
    run_p.add_argument("--fresh", action="store_true",
                       help="ignore cached rows and re-run everything")
    args = ap.parse_args()
    if args.cmd == "build-sources":
        return cmd_build_sources(args)
    if args.cmd == "select-hard-negatives":
        return cmd_select_hard_negatives(args)
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
