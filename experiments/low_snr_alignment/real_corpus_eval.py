"""RA-1.2B real-corpus benchmark.

Runs production v1.1.x find_offset() and Alignment Engine v2
(find_offset_v2) over the local corpus manifest (positives + mismatch
negatives). Requires experiments/low_snr_alignment/local_corpus.json
(gitignored; see local_corpus.example.json). All committed output is
path-free: only case ids and numbers leave this machine.

Each case runs in an isolated worker subprocess (this script re-invokes
itself with --worker N): a native-level crash in one media file then costs
one case, not the whole benchmark. Results are written incrementally.

Run:  python experiments/low_snr_alignment/real_corpus_eval.py \
          [--json results/real_corpus.json] [--only positive|negative]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

MANIFEST = os.path.join(_HERE, "local_corpus.json")
SR = 22050


def load_cases(only=None, skip=0, limit=None):
    with open(MANIFEST, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    if only:
        cases = [c for c in cases
                 if (c["class"].startswith("positive") if only == "positive"
                     else c["class"] == "negative_mismatch")]
    if limit:
        cases = cases[:limit]
    if skip:
        cases = cases[skip:]
    return cases


def evaluate_case(case, y_video, y_music):
    """Run v1 and v2 on already-extracted audio; return path-free row."""
    from auto_sync import _align_hybrid
    from alignment_engine_v2 import decide_alignment, STATUS_ACCEPTED

    row = {"case_id": case["case_id"], "class": case["class"]}

    # v1.1.x production behavior
    t0 = time.perf_counter()
    try:
        offset, z, _ = _align_hybrid(y_video, y_music, SR, 512)
        row["v1"] = {"accepted": bool(z >= 2.0), "offset": round(offset, 4),
                     "hybrid_z": round(z, 3),
                     "runtime_s": round(time.perf_counter() - t0, 2)}
    except Exception as exc:
        row["v1"] = {"accepted": False,
                     "error": f"{type(exc).__name__}: {exc}"}

    # Engine v2 (full decision + diagnostics)
    decision = decide_alignment(y_video, y_music, sr=SR)
    row["v2"] = {
        "status": decision.status,
        "offset": None if decision.offset is None else round(decision.offset, 4),
        "reason_code": decision.reason_code,
        "families": decision.evidence["families"],
        "clusters": decision.clusters[:6],
        "runtime_s": round(decision.runtime_s, 2),
    }

    # v1-vs-v2 consistency for positives, measured low-SNR class
    if row["v2"]["status"] == STATUS_ACCEPTED and row["v1"].get("accepted"):
        row["v1_v2_agree"] = bool(
            abs(row["v1"]["offset"] - row["v2"]["offset"]) <= 0.15)
    if case["class"].startswith("positive"):
        hz = row["v1"].get("hybrid_z")
        row["measured_class"] = (
            "positive_strong" if (hz is not None and hz >= 8.0)
            else "positive_low_snr_or_failed_v1")
    gt = case.get("expected_offset")
    if gt is not None and row["v2"]["status"] == STATUS_ACCEPTED:
        row["v2_error_vs_gt"] = round(abs(row["v2"]["offset"] - gt), 4)
        row["v2_within_gt_tolerance"] = bool(
            row["v2_error_vs_gt"] <= case.get("tolerance", 0.15))
    return row


def run_worker(case):
    """Extract audio and evaluate one case in THIS process; returns a row."""
    import tempfile
    import uuid
    import imageio_ffmpeg
    import librosa
    from alignment_engine_v2 import extract_audio

    t0 = time.perf_counter()
    temp_dir = tempfile.gettempdir()
    tv = os.path.abspath(os.path.join(
        temp_dir, f"ra_corpus_v_{uuid.uuid4().hex}.wav"))
    tm = os.path.abspath(os.path.join(
        temp_dir, f"ra_corpus_m_{uuid.uuid4().hex}.wav"))
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        extract_audio(ffmpeg_bin, case["video"], tv, SR)
        extract_audio(ffmpeg_bin, case["music"], tm, SR)
        y_video, _ = librosa.load(tv, sr=None, mono=True)
        y_music, _ = librosa.load(tm, sr=None, mono=True)
    finally:
        for p in (tv, tm):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
    row = evaluate_case(case, y_video, y_music)
    row["extract_s"] = round(time.perf_counter() - t0, 2)
    return row


def worker_main(manifest_index):
    cases = load_cases()
    row = run_worker(cases[manifest_index])
    sys.stdout.write("@@ROW@@" + json.dumps(row, ensure_ascii=False) + "\n")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--only", choices=["positive", "negative"], default=None)
    ap.add_argument("--skip", type=int, default=0,
                    help="skip the first N cases of the filtered list")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--worker", type=int, default=None, metavar="N",
                    help="internal: evaluate manifest case N in this "
                         "process and print one @@ROW@@ line")
    args = ap.parse_args()

    if args.worker is not None:
        return worker_main(args.worker)

    cases = load_cases(args.only, args.skip, args.limit)
    # map filtered positions back to manifest indexes for worker isolation
    with open(MANIFEST, encoding="utf-8") as f:
        all_cases = json.load(f)["cases"]
    index_by_id = {c["case_id"]: i for i, c in enumerate(all_cases)}

    rows = []
    if args.json and os.path.exists(args.json):
        try:
            with open(args.json, encoding="utf-8") as f:
                rows = json.load(f)
        except Exception:
            rows = []
    done_ids = {r["case_id"] for r in rows}

    mismatches_accepted = 0
    for n, case in enumerate(cases):
        if case["case_id"] in done_ids:
            print(f"[{n + 1}/{len(cases)}] {case['case_id']}: cached")
            continue
        t0 = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, os.path.abspath(__file__),
             "--worker", str(index_by_id[case["case_id"]])],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            errors="replace", timeout=600)
        wall = time.perf_counter() - t0
        row = None
        for line in proc.stdout.splitlines():
            if line.startswith("@@ROW@@"):
                row = json.loads(line[len("@@ROW@@"):])
        if row is None:
            row = {"case_id": case["case_id"], "class": case["class"],
                   "error": f"worker exit {proc.returncode}",
                   "stderr_tail": proc.stderr[-500:]}
        rows.append(row)
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, ensure_ascii=False)

        v1, v2 = row.get("v1", {}), row.get("v2", {})
        if v1.get("accepted"):
            v1_str = f"acc@{v1['offset']:+.3f} z={v1['hybrid_z']:.2f}"
        else:
            v1_str = v1.get("error", "abstain/err")
        v2_off = v2.get("offset")
        v2_off = "None" if v2_off is None else format(v2_off, "+.3f")
        print(f"[{n + 1}/{len(cases)}] {case['case_id']} "
              f"({case['class']}): v1={v1_str} | v2="
              f"{v2.get('status', 'ERROR')}@{v2_off} "
              f"({v2.get('reason_code', row.get('error', '?'))}) "
              f"[{wall:.1f}s]")

        if case["class"] == "negative_mismatch" \
                and v2.get("status") == "accepted":
            mismatches_accepted += 1

    n_pos = sum(1 for r in rows if r.get("class", "").startswith("positive"))
    n_neg = sum(1 for r in rows if r.get("class") == "negative_mismatch")
    pos_accept = sum(1 for r in rows
                     if r.get("class", "").startswith("positive")
                     and r.get("v2", {}).get("status") == "accepted")
    agree = sum(1 for r in rows if r.get("v1_v2_agree"))
    errors = sum(1 for r in rows if "error" in r and "v2" not in r)
    print(f"\nsummary: {n_pos} positives ({pos_accept} accepted by v2, "
          f"{agree} agree with accepted v1), {n_neg} mismatch negatives "
          f"({mismatches_accepted} FALSE-ACCEPTED by v2), {errors} worker "
          f"errors")
    return 1 if mismatches_accepted else 0


if __name__ == "__main__":
    sys.exit(main())
