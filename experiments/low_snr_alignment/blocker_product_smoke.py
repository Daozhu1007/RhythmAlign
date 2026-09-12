"""Product-path end-to-end smoke for the Astra blocker pair (RA-1.2E).

Companion to product_smoke.py: drives the REAL ui_main.SyncWorker on the
Astra release-blocker pair (tr_lingduihua video x tr_yanwulieche music)
from the gitignored local_sources.json manifest. Expected behavior since
RA-1.2D1: the worker must ABSTAIN with ABSTAIN_CONCENTRATED_EVIDENCE,
never start an export, never create an output file, and never fall back
to the legacy v1 engine (auto_sync.find_offset is booby-trapped).

Run from the repository root:

  python experiments/low_snr_alignment/blocker_product_smoke.py [--keep]

Exit code: 0 pass, 1 fail, 2 missing manifest/pair.
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

SOURCES = os.path.join(_HERE, "local_sources.json")
QUERY, REFERENCE = "tr_lingduihua", "tr_yanwulieche"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(SOURCES):
        print("local_sources.json not found (gitignored local manifest).")
        return 2
    tracks = json.loads(open(SOURCES, encoding="utf-8").read())["tracks"]
    if QUERY not in tracks or REFERENCE not in tracks:
        print(f"pair {QUERY} x {REFERENCE} not in local manifest")
        return 2

    import auto_sync
    import ui_main

    # No silent v1 fallback: the legacy entry point must never be reached.
    def _boom(*_a, **_k):
        raise AssertionError("legacy v1 find_offset was called")
    auto_sync.find_offset = _boom
    if hasattr(ui_main, "find_offset"):
        ui_main.find_offset = _boom

    out_dir = tempfile.mkdtemp(prefix="ra12e_blocker_smoke_")
    save_path = os.path.join(out_dir, "blocker_product_smoke.mp4")
    kwargs = {
        "v_path": tracks[QUERY], "m_path": tracks[REFERENCE],
        "save_path": save_path,
        "orig_vol": 1.2, "music_vol": 0.7, "manual_offset": 0.0,
        "use_gpu": False, "bitrate": "10000k",
        "open_folder": False, "stream_copy": True,
    }

    logs, progress, finished = [], [], []
    worker = ui_main.SyncWorker(kwargs)
    worker.log_signal.connect(lambda msg, state: logs.append((state, msg)))
    worker.progress_signal.connect(
        lambda task, pct, eta: progress.append((task, pct, eta)))
    worker.finished_signal.connect(
        lambda ok, path, abstain: finished.append((ok, path, abstain)))

    t0 = time.perf_counter()
    worker.run()
    wall = time.perf_counter() - t0

    for state, msg in logs:
        print(f"  [{state}] {msg}")
    ok, path, abstain_msg = finished[-1]
    exists = os.path.exists(save_path)
    export_progress = [t for t, _, _ in progress
                       if t == ui_main.i18n.tr("task_done_export")]
    reason_ok = any("ABSTAIN_CONCENTRATED_EVIDENCE" in m for _, m in logs)
    passed = (ok is False and not exists and bool(abstain_msg)
              and not export_progress and reason_ok
              and len(finished) == 1)
    print(f"  result: ok={ok} output_exists={exists} "
          f"export_progress_entries={len(export_progress)} "
          f"finished_signals={len(finished)} "
          f"concentrated_evidence_in_logs={reason_ok} "
          f"wall={wall:.1f}s")
    if abstain_msg:
        print("  abstain message:\n    " +
              abstain_msg.replace("\n", "\n    "))

    if not args.keep and os.path.exists(out_dir):
        shutil.rmtree(out_dir, ignore_errors=True)
        print("  temporary output directory removed")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
