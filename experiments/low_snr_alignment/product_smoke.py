"""Product-path end-to-end smoke test (RA-1.2D).

Runs the REAL product worker class (ui_main.SyncWorker) — Alignment
Engine v2 default path, real FFmpeg extraction, real mix_and_export —
against one corpus case at a time. No mocks. This is the same worker the
GUI starts; only the Qt event loop is replaced by a synchronous run()
for deterministic scripted verification.

Expected outcomes (RA-1.2D §12):
  positive case   -> accepted, exactly one export, output file exists
  mismatch case   -> abstained, export NEVER started, no output file

Run from the repository root (requires the gitignored local_corpus.json):

  python experiments/low_snr_alignment/product_smoke.py \
      --case lingduihua_132 [--keep]

--keep preserves the exported file for human listening; default behavior
deletes the temporary output directory afterwards.

Exit code: 0 pass, 1 fail (unexpected outcome), 2 missing manifest/case.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

MANIFEST = os.path.join(_HERE, "local_corpus.json")


def run_case(case_id, out_dir, manual_offset=0.0, keep=False):
    import ui_main

    with open(MANIFEST, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    case = next((c for c in cases if c["case_id"] == case_id), None)
    if case is None:
        print(f"FAIL: case {case_id!r} not in local manifest")
        return 2

    save_path = os.path.join(out_dir, f"{case_id}_product_smoke.mp4")
    kwargs = {
        'v_path': case["video"], 'm_path': case["music"],
        'save_path': save_path,
        'orig_vol': 1.2, 'music_vol': 0.7, 'manual_offset': manual_offset,
        'use_gpu': False, 'bitrate': '10000k',
        'open_folder': False, 'stream_copy': True,
    }

    logs, progress, finished = [], [], []

    worker = ui_main.SyncWorker(kwargs)
    worker.log_signal.connect(lambda msg, state: logs.append((state, msg)))
    worker.progress_signal.connect(
        lambda task, pct, eta: progress.append((task, pct, eta)))
    worker.finished_signal.connect(
        lambda ok, path, abstain: finished.append((ok, path, abstain)))

    print(f"--- product smoke: {case_id} (class={case['class']}) ---")
    t0 = time.perf_counter()
    worker.run()
    wall = time.perf_counter() - t0

    for state, msg in logs:
        print(f"  [{state}] {msg}")
    ok, path, abstain_msg = finished[-1]
    exists = os.path.exists(save_path)
    print(f"  result: ok={ok} output_exists={exists} "
          f"analysis+export wall={wall:.1f}s")
    if abstain_msg:
        print(f"  abstain message:\n    " +
              abstain_msg.replace("\n", "\n    "))

    if case["class"].startswith("positive"):
        export_done = ui_main.i18n.tr("task_done_export")
        passed = (ok is True and exists
                  and any(t == export_done for t, _, _ in progress))
    else:
        passed = (ok is False and not exists and bool(abstain_msg))

    if not keep and os.path.exists(out_dir):
        shutil.rmtree(out_dir, ignore_errors=True)
        print("  temporary output directory removed")
    return 0 if passed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="case_id from local corpus")
    ap.add_argument("--manual-offset", type=float, default=0.0)
    ap.add_argument("--keep", action="store_true",
                    help="keep the exported file instead of deleting it")
    args = ap.parse_args()

    if not os.path.exists(MANIFEST):
        print("local_corpus.json not found (gitignored local manifest).")
        return 2

    out_dir = tempfile.mkdtemp(prefix="ra12d_product_smoke_")
    return run_case(args.case, out_dir, args.manual_offset, args.keep)


if __name__ == "__main__":
    sys.exit(main())
