"""Panako comparator-contract validation on SHAKEDOWN_ONLY material.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING VALIDATION DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE, AS A DATASET, OR AS ANY
PERFORMANCE CLAIM about Panako or any other system.

Purpose (integration task, BEFORE any pilot recording): verify on the
existing frozen shakedown cases, which carry exact marker-derived GT, that

  1. the runner's decision mapping behaves (match / native no-match /
     degraded positives);
  2. the offset sign convention is what the source inspection predicts
     (predicted_offset_s = Query start - Match start);
  3. offset magnitude and repeatability are measured RAW (no tuning, no
     re-runs beyond the explicit determinism/repeatability checks below);
  4. store determinism: one stored reference, two queries -> identical
     non-volatile output (FRESH_PILOT_PLAN section 8 requirement).

All outcomes are reported raw. The pre-declared role rule (FRESH_PILOT_PLAN
section 8) is APPLIED as written — median |offset error| over the eligible
EXACT_GT positives vs the 100 ms editorial tolerance — but the result is a
SHAKEDOWN_ONLY role scoping, never a performance finding; the pilot
re-freezes the role on pilot data with the same rule.

Usage:
    python -m experiments.applied_system.panako_shakedown_check
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

from .runners import panako_runner
from .runners.common import (DECISION_ACCEPT, DECISION_ERROR,
                             DECISION_NO_MATCH, load_json, save_json,
                             sha256_file)
from .shakedown import DEFAULT_OUTDIR, FS

OUT_SUBDIR = "panako_integration"
REPORT_ORDER = [
    "pos_zero_lead", "pos_ordinary", "pos_negative_offset", "pos_noise",
    "pos_quiet", "pos_clock_drift", "wrong_reference",
]


def _resolve(base: Path, rel: str | None) -> Path | None:
    return None if rel is None else base / rel


def store_determinism_check(manifest_body: dict, outdir: Path) -> dict:
    """Store song A once; query pos_ordinary twice; require identical
    non-volatile output rows (the runner's own parse, verbatim)."""
    case = next(c for c in manifest_body["cases"]
                if c["case_id"] == "pos_ordinary")
    wsl_in = panako_runner.to_wsl_path(outdir / case["trimmed_input_path"])
    store_dir = "/tmp/panako_determinism_store"
    prefix = panako_runner._panako_invocation_prefix(store_dir)
    wsl_ref = panako_runner.to_wsl_path(outdir / case["reference_path"])
    run = lambda: panako_runner._wsl_bash(
        f"{prefix} query {panako_runner._sh_quote(wsl_in)}")
    store_proc = panako_runner._wsl_bash(
        f"{prefix} store {panako_runner._sh_quote(wsl_ref)}")
    if store_proc.returncode != 0:
        return {"ok": False,
                "error": f"store failed: {store_proc.stderr.strip()[-300:]}"}
    q1, q2 = run(), run()
    panako_runner._wsl_bash(f"rm -rf {panako_runner._sh_quote(store_dir)}")
    rows1 = [r.as_dict() for r in panako_runner.parse_query_output(q1.stdout)]
    rows2 = [r.as_dict() for r in panako_runner.parse_query_output(q2.stdout)]
    return {"ok": rows1 == rows2 and q1.returncode == q2.returncode == 0,
            "n_rows_run1": len(rows1), "n_rows_run2": len(rows2),
            "rows_identical": rows1 == rows2,
            "rows_run1": rows1, "rows_run2": rows2}


def main() -> int:
    outdir = DEFAULT_OUTDIR
    out = outdir / OUT_SUBDIR
    out.mkdir(parents=True, exist_ok=True)

    print("[panako-check] probing WSL Panako environment…")
    ok, env = panako_runner.panako_environment()
    env["shakedown_only"] = "SHAKEDOWN_ONLY"
    env["not_paper_evidence"] = "NOT_PAPER_EVIDENCE"
    save_json(out / "panako_environment.json", env)
    if not ok:
        print(f"[panako-check] Panako environment NOT available: "
              f"{env.get('error')}")
        save_json(out / "summary.json", {
            "status": panako_runner.STATUS_BLOCKED,
            "shakedown_only": "SHAKEDOWN_ONLY",
            "not_paper_evidence": "NOT_PAPER_EVIDENCE",
            "environment": env})
        return 2
    for key in ("jar_sha256", "java_version_line", "ffmpeg_version_line",
                "panako_version_line", "jar_resolved_path"):
        print(f"  {key}: {env.get(key)}")

    frozen = load_json(outdir / "manifest.json")
    body = frozen["body"]
    cases = {c["case_id"]: c for c in body["cases"]}

    records = {}
    for case_id in REPORT_ORDER:
        case = cases[case_id]
        input_path = _resolve(outdir, case.get("trimmed_input_path"))
        reference_path = _resolve(outdir, case["reference_path"])
        if input_path is None or not input_path.exists():
            print(f"[panako-check] {case_id}: trimmed input missing, skipped")
            continue
        hash_ok = (
            sha256_file(input_path) == case["trimmed_input_sha256"]
            and sha256_file(reference_path) == case["reference_sha256"])
        if not hash_ok:
            print(f"[panako-check] {case_id}: HASH MISMATCH vs frozen "
                  "manifest — skipped (never run on altered bytes)")
            continue
        t0 = time.perf_counter()
        rec = panako_runner.run_case(case, input_path, reference_path, FS)
        wall = time.perf_counter() - t0
        records[case_id] = rec
        save_json(out / f"record__{case_id}.json", rec.as_dict())
        extra = ""
        if rec.decision == DECISION_ACCEPT:
            err = rec.predicted_offset_s - case["gt_offset_s"]
            extra = (f" offset={rec.predicted_offset_s:+.3f}s "
                     f"gt={case['gt_offset_s']:+.3f}s err={err * 1000:+.1f}ms")
        print(f"  {case_id}: {rec.decision}{extra} "
              f"(runtime {rec.runtime_s:.1f}s, wall {wall:.1f}s)")

    if "pos_ordinary" in records:
        print("[panako-check] store determinism (store once, query twice)…")
        det = store_determinism_check(body, outdir)
        save_json(out / "store_determinism.json", {
            "shakedown_only": "SHAKEDOWN_ONLY",
            "not_paper_evidence": "NOT_PAPER_EVIDENCE", **det})
        print(f"  identical: {det['ok']}")

        print("[panako-check] repeatability: fresh-store rerun of "
              "pos_ordinary…")
        case = cases["pos_ordinary"]
        rec2 = panako_runner.run_case(
            case, outdir / case["trimmed_input_path"],
            outdir / case["reference_path"], FS)
        save_json(out / "record__pos_ordinary_rerun.json", rec2.as_dict())
        r1, r2 = records["pos_ordinary"], rec2
        if r1.decision == DECISION_ACCEPT and r2.decision == DECISION_ACCEPT:
            delta = abs(r1.predicted_offset_s - r2.predicted_offset_s)
            print(f"  offsets: {r1.predicted_offset_s:+.4f} vs "
                  f"{r2.predicted_offset_s:+.4f} (|delta| {delta * 1000:.1f} ms)")
        else:
            print(f"  decisions: {r1.decision} / {r2.decision}")

    pos_errors_ms = []
    for case_id, rec in records.items():
        if rec.decision == DECISION_ACCEPT:
            gt = cases[case_id]["gt_offset_s"]
            pos_errors_ms.append(
                (case_id, abs(rec.predicted_offset_s - gt) * 1000.0))

    median_abs_err_ms = (statistics.median(e for _, e in pos_errors_ms)
                         if pos_errors_ms else None)
    role_rule = {
        "rule_source": "FRESH_PILOT_PLAN section 8 (pre-declared)",
        "tolerance_ms": 100.0,
        "median_abs_offset_error_ms": median_abs_err_ms,
        "abs_errors_ms": pos_errors_ms,
        "shakedown_only": True,
    }
    if median_abs_err_ms is not None:
        role_rule["rule_outcome"] = (
            "PLACEMENT_COMPARATOR"
            if median_abs_err_ms <= 100.0
            else "IDENTIFICATION_SELECTIVITY_COMPARATOR")

    summary = {
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "warning": "comparator-contract validation only; NOT performance "
                   "evidence; no tuning performed",
        "status": panako_runner.STATUS_READY,
        "manifest_hash": frozen["manifest_hash"],
        "environment": env,
        "decisions": {cid: {"decision": r.decision,
                            "predicted_offset_s": r.predicted_offset_s,
                            "runtime_s": r.runtime_s,
                            "n_valid_match_rows":
                                r.native_scores.get("n_valid_match_rows"),
                            "n_empty_rows":
                                r.native_scores.get("n_empty_rows")}
                      for cid, r in records.items()},
        "role_rule": role_rule,
    }
    save_json(out / "summary.json", summary)
    print(f"[panako-check] artifacts in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
