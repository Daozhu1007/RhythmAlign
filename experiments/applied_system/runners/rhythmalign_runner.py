"""RhythmAlign runner — frozen v1.2.0 production alignment decision.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

Frozen-subject rules (study design section 5, shakedown spec section 2.3):

  - The subject is the UNMODIFIED production RhythmAlign v1.2.0 engine.
  - The runner calls the production file entry point
    ``alignment_engine_v2.find_offset_v2(input, reference)`` exactly as the
    GUI's SyncWorker/AnalyzeWorker do; no research-side thresholds,
    features, or policy overrides are permitted.
  - Analyze Only and Full Export consume the SAME v1.2.0 alignment decision,
    so the frozen decision is scored ONCE; workflow differences are not two
    benchmark arms.
  - Native semantics preserved: engine "accepted" -> ACCEPT (with the
    engine's offset), engine "abstained" -> ABSTAIN (never coerced into an
    always-output answer).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import alignment_engine_v2  # noqa: E402  (unmodified production import)

from .common import (DECISION_ABSTAIN, DECISION_ACCEPT, DECISION_ERROR,
                     SEMANTICS_SELECTIVE_NO_MATCH, RunnerRecord)

SYSTEM_ID = "rhythmalign_v1_2_0"


def run_case(case: dict, input_path, reference_path, fs: int = 22050,
             load_audio=None) -> RunnerRecord:
    """Run the frozen v1.2.0 decision on one case.

    fs/load_audio are accepted for runner-interface uniformity but unused:
    the production entry point performs its own ffmpeg extraction at its own
    frozen rate (22050 Hz mono), which is part of the frozen subject.
    """
    try:
        decision = alignment_engine_v2.find_offset_v2(str(input_path),
                                                      str(reference_path))
        raw = decision.as_dict()
        # Keep the record bounded: clusters carry the full curve metadata.
        raw_clusters = raw.pop("clusters", [])
        accepted = decision.accepted
        return RunnerRecord(
            system=SYSTEM_ID, case_id=case["case_id"],
            decision=DECISION_ACCEPT if accepted else DECISION_ABSTAIN,
            predicted_offset_s=(float(decision.offset) if accepted else None),
            native_scores={
                "engine_label": alignment_engine_v2.ENGINE_LABEL,
                "status": decision.status,
                "reason_code": decision.reason_code,
            },
            runtime_s=float(decision.runtime_s),
            output_semantics=SEMANTICS_SELECTIVE_NO_MATCH,
            notes={"raw_decision": raw,
                   "n_clusters": len(raw_clusters),
                   "frozen_release": "v1.2.0"})
    except Exception as exc:  # noqa: BLE001 — runner errors must be recorded
        return RunnerRecord(
            system=SYSTEM_ID, case_id=case["case_id"],
            decision=DECISION_ERROR, predicted_offset_s=None,
            native_scores={"error": f"{type(exc).__name__}: {exc}"},
            runtime_s=0.0, output_semantics=SEMANTICS_SELECTIVE_NO_MATCH,
            notes={})
