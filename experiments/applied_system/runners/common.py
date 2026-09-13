"""Common runner infrastructure: output contract, hashing, environment.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Output contract (shakedown question 7/11): every system result is normalized
into a RunnerRecord while PRESERVING native decision semantics:

    decision in {ACCEPT, ABSTAIN, NO_MATCH, ERROR}
      RhythmAlign ABSTAIN stays ABSTAIN (SELECTIVE_NO_MATCH semantics).
      A fingerprint tool's native no-match stays NO_MATCH.
      GCC-PHAT / NCC argmax are ACCEPT (ALWAYS_OUTPUT semantics); no
      confidence threshold is invented for baselines in this round.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]

DECISION_ACCEPT = "ACCEPT"
DECISION_ABSTAIN = "ABSTAIN"
DECISION_NO_MATCH = "NO_MATCH"
DECISION_ERROR = "ERROR"

SEMANTICS_ALWAYS_OUTPUT = "ALWAYS_OUTPUT"
SEMANTICS_SELECTIVE_NO_MATCH = "SELECTIVE_NO_MATCH"
SEMANTICS_UNKNOWN = "UNKNOWN_NOT_APPLICABLE"

SHAKEDOWN_WARNING = ("THIS IS ENGINEERING SHAKEDOWN DATA. "
                     "IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array_f64(arr) -> str:
    """Hash of an in-memory float64 array (test convenience; the benchmark
    itself always hashes files)."""
    return hashlib.sha256(
        np.ascontiguousarray(arr, dtype=np.float64).tobytes()).hexdigest()


@dataclass
class RunnerRecord:
    """One system result for one case, in the common output contract."""

    system: str
    case_id: str
    decision: str                     # ACCEPT | ABSTAIN | NO_MATCH | ERROR
    predicted_offset_s: float | None
    native_scores: dict = field(default_factory=dict)
    runtime_s: float = 0.0
    input_sha256: dict = field(default_factory=dict)   # name -> sha256
    output_semantics: str = SEMANTICS_UNKNOWN
    notes: dict = field(default_factory=dict)

    def as_dict(self):
        return {
            "shakedown_only": "SHAKEDOWN_ONLY",
            "not_paper_evidence": "NOT_PAPER_EVIDENCE",
            "system": self.system,
            "case_id": self.case_id,
            "decision": self.decision,
            "predicted_offset_s": (None if self.predicted_offset_s is None
                                   else float(self.predicted_offset_s)),
            "native_scores": self.native_scores,
            "runtime_s": float(self.runtime_s),
            "input_sha256": self.input_sha256,
            "output_semantics": self.output_semantics,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            system=d["system"], case_id=d["case_id"],
            decision=d["decision"],
            predicted_offset_s=d.get("predicted_offset_s"),
            native_scores=d.get("native_scores", {}),
            runtime_s=d.get("runtime_s", 0.0),
            input_sha256=d.get("input_sha256", {}),
            output_semantics=d.get("output_semantics",
                                   SEMANTICS_UNKNOWN),
            notes=d.get("notes", {}))


def save_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=str(ROOT),
                              capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:
        return None


def capture_environment() -> dict:
    """Reproducibility metadata (shakedown question 9 / section 15)."""
    import numpy
    import scipy

    env = {
        "shakedown_only": "SHAKEDOWN_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "warning": SHAKEDOWN_WARNING,
        "os": platform.platform(),
        "python_version": sys.version.replace("\n", " "),
        "numpy_version": numpy.__version__,
        "scipy_version": scipy.__version__,
        "git_research_commit": _git("rev-parse", "HEAD"),
        "git_describe": _git("describe", "--tags", "--always"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": None,
        "ffmpeg": None,
        "rhythmalign_engine": None,
        "comparators": {
            "gcc_phat": "research implementation v1 (FFT PHAT, argmax, no "
                        "invented thresholds)",
            "ncc": "research implementation v1 (overlap-normalized waveform "
                   "NCC, argmax, no invented thresholds)",
            "panako": "PENDING_NOT_INSTALLED (build-from-source only; "
                      "see runners/panako_runner.py)",
        },
        "random_seeds": {
            "shakedown_song_a": 20260913,
            "shakedown_song_b": 20260914,
            "capture_noise": "derived deterministically from case_id (see "
                             "shakedown.case_definitions)",
        },
    }
    try:
        status = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                                capture_output=True, text=True,
                                timeout=30).stdout.strip()
        env["git_dirty"] = bool(status)
    except Exception:
        pass
    try:
        import librosa
        env["librosa_version"] = librosa.__version__
    except Exception:
        env["librosa_version"] = None
    try:
        import soundfile
        env["soundfile_version"] = soundfile.__version__
    except Exception:
        env["soundfile_version"] = None
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        ver = subprocess.run([exe, "-version"], capture_output=True, text=True,
                             timeout=60).stdout.splitlines()
        env["ffmpeg"] = {"path": exe, "version_line": ver[0] if ver else None}
    except Exception as exc:
        env["ffmpeg"] = {"error": str(exc)}
    try:
        sys.path.insert(0, str(ROOT))
        import alignment_engine_v2
        env["rhythmalign_engine"] = {
            "engine_label": alignment_engine_v2.ENGINE_LABEL,
            "frozen_release": "v1.2.0",
            "module": "alignment_engine_v2.py (unmodified, read-only import)",
        }
    except Exception as exc:
        env["rhythmalign_engine"] = {"error": str(exc)}
    return env
