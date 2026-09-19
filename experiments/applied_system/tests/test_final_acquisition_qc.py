"""Research-only tests: comparator-blind final acquisition QC.

Everything runs on synthetic audio and temporary directories; the owner's
raw recordings, the frozen final-pack media, and the QC freeze artifacts
are never touched. NO comparator is invoked anywhere in this module, and
the QC module under test must not even import one.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import final_acquisition_qc as fqc  # noqa: E402
from experiments.applied_system import marker_protocol as mp  # noqa: E402

FS = mp.FS

FORBIDDEN_IMPORT_TOKENS = (
    "rhythmalign_runner", "gcc_phat_runner", "ncc_runner",
    "panako_runner", "pilot_harness", "alignment_engine",
    "import scoring",
)


# ---------------------------------------------------------------------------
# frozen parameters (protocol + acquisition manifest are authoritative)
# ---------------------------------------------------------------------------


def test_frozen_qc_parameters_match_manifest():
    manifest = json.loads(
        (ROOT / "experiments/applied_system/final_pack/"
         "final_acquisition_manifest.json").read_text(encoding="utf-8"))
    gt = manifest["body"]["gt_contract"]
    assert gt["frozen_marker_threshold"] == fqc.FROZEN_MARKER_THRESHOLD
    assert gt["frozen_marker_threshold"] == 0.163837792269
    assert gt["drift_tolerance_ppm"] == fqc.FROZEN_DRIFT_TOLERANCE_PPM
    assert gt["drift_tolerance_ppm"] == 128.486056
    assert gt["max_mapping_disagreement_s"] == fqc.MAX_MAPPING_DISAGREEMENT_S
    assert fqc.MAX_MAPPING_DISAGREEMENT_S == mp.MAX_MAPPING_DISAGREEMENT_S
    assert fqc.TRAJECTORY_GATE_STATE == "TRAJECTORY_GATE_FROZEN_OFF"


def test_expected_take_ids_match_manifest_and_counts():
    manifest = json.loads(
        (ROOT / "experiments/applied_system/final_pack/"
         "final_acquisition_manifest.json").read_text(encoding="utf-8"))
    takes = manifest["body"]["takes"]
    assert sorted(fqc.EXPECTED_TAKE_IDS) == sorted(takes)
    assert len(fqc.EXPECTED_TAKE_IDS) == 26
    assert len(fqc.PRIMARY_TAKE_IDS) == 24
    assert sum(1 for t in fqc.EXPECTED_TAKE_IDS
               if t.startswith("repeat")) == 2


def test_protocol_doc_contains_frozen_values():
    text = (ROOT / "docs/research/applied_system/"
            "FINAL_BENCHMARK_PROTOCOL.md").read_text(encoding="utf-8")
    for token in ("0.163837792269", "128.486056", "TRAJECTORY_GATE_FROZEN_OFF",
                  "10.000", "two accepted marker candidates"):
        assert token in text


# ---------------------------------------------------------------------------
# ingestion: basename mapping, arbitrary extensions, frozen retake policy
# ---------------------------------------------------------------------------


def _touch(path: Path, payload: bytes = b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _populate_all(tmp_path: Path, naming=None):
    naming = naming or (lambda take: f"{take}.m4a")
    for take in fqc.EXPECTED_TAKE_IDS:
        _touch(tmp_path / naming(take))


def test_ingestion_maps_arbitrary_extensions(tmp_path):
    for take in fqc.EXPECTED_TAKE_IDS:
        _touch(tmp_path / f"{take}.m4a")
    (tmp_path / "final02.m4a").rename(tmp_path / "final02.wav")
    (tmp_path / "final03.m4a").rename(tmp_path / "final03.FLAC")
    (tmp_path / "repeat01.m4a").rename(tmp_path / "repeat01.mp3")
    ingest = fqc.discover_recordings(tmp_path)
    assert ingest["chosen"]["final01"].name == "final01.m4a"
    assert ingest["chosen"]["final02"].name == "final02.wav"
    assert ingest["chosen"]["final03"].name == "final03.FLAC"
    assert ingest["chosen"]["repeat01"].name == "repeat01.mp3"
    assert len(ingest["chosen"]) == 26


def test_ingestion_prefers_exact_and_preserves_retakes(tmp_path):
    _populate_all(tmp_path)
    _touch(tmp_path / "final04_b.m4a")
    (tmp_path / "repeat02.m4a").rename(tmp_path / "repeat02.mp3")
    _touch(tmp_path / "repeat02_c.mp3")
    ingest = fqc.discover_recordings(tmp_path)
    assert ingest["chosen"]["final04"].name == "final04.m4a"
    assert ingest["retakes_preserved"]["final04"] == ["final04_b.m4a"]
    assert ingest["chosen"]["repeat02"].name == "repeat02.mp3"
    assert ingest["retakes_preserved"]["repeat02"] == ["repeat02_c.mp3"]


def test_ingestion_uses_single_retake_when_no_exact(tmp_path):
    for take in fqc.EXPECTED_TAKE_IDS:
        _touch(tmp_path / f"{take}.m4a")
    (tmp_path / "final05.m4a").unlink()
    _touch(tmp_path / "final05_b.m4a")
    ingest = fqc.discover_recordings(tmp_path)
    assert ingest["chosen"]["final05"].name == "final05_b.m4a"


def test_ingestion_rejects_missing_ambiguous_and_unexpected(tmp_path):
    _populate_all(tmp_path)
    (tmp_path / "final07.m4a").unlink()
    # ambiguous = two retakes and no exact-basename file
    (tmp_path / "final08.m4a").unlink()
    _touch(tmp_path / "final08_a.m4a")
    _touch(tmp_path / "final08_b.m4a")
    _touch(tmp_path / "stray_recording.m4a")
    with pytest.raises(RuntimeError) as exc:
        fqc.discover_recordings(tmp_path)
    msg = str(exc.value)
    assert "final07: missing" in msg
    assert "final08" in msg and "ambiguous" in msg
    assert "stray_recording.m4a" in msg


# ---------------------------------------------------------------------------
# per-take QC on synthetic captures (frozen gates; deterministic)
# ---------------------------------------------------------------------------


def _deterministic_payload(seconds: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.ascontiguousarray(
        rng.normal(0.0, 0.08, int(round(seconds * FS))))


def _synthetic_buffer():
    payload = _deterministic_payload(60.0, seed=11)
    spec = mp.buffer_spec(len(payload), FS)
    buffer = mp.render_marker_buffer(payload, FS)
    return payload, spec, buffer


def _write_capture(path: Path, buffer: np.ndarray, lead_s=2.5, tail_s=2.0,
                   end_cut_s=0.0, seed=7):
    """Deterministic quiet-lead + buffer + quiet-tail capture. end_cut_s
    removes material from the absolute end (used to truncate the post
    marker)."""
    rng = np.random.default_rng(seed)
    capture = np.concatenate([
        rng.normal(0.0, 3e-4, int(round(lead_s * FS))),
        buffer,
        rng.normal(0.0, 3e-4, int(round(tail_s * FS)))])
    if end_cut_s > 0:
        capture = capture[:-int(round(end_cut_s * FS))]
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), capture, FS, subtype="PCM_16")


def _take_row(slot="S01", condition="ORDINARY", primary=True):
    return {
        "primary": primary, "condition": condition, "source_slot": slot,
        "source_identity": "synthetic", "playback_buffer": f"BUF-{slot}",
        "playback_device": "P1", "session": "SESSION_1", "room": "ROOM_A",
        "recording_device": "D1",
    }


def _buffer_row(payload_slice_s=(0.0, 60.0)):
    return {"payload_slice_s": list(payload_slice_s)}


def test_qc_take_gt_valid_on_synthetic_selfcheck_capture(tmp_path):
    payload, _spec, buffer = _synthetic_buffer()
    raw = tmp_path / "incoming" / "final01.wav"
    _write_capture(raw, buffer)
    ref_path = tmp_path / "REF-S01.wav"
    sf.write(str(ref_path), payload, FS, subtype="PCM_16")

    record = fqc.qc_take("final01", raw, _take_row(), _buffer_row(),
                         ref_path, tmp_path / "work")
    assert record["gt_status"] == "GT_VALID"
    assert record["gt_fail_reason"] is None
    assert record["marker_qc"]["n_marker_candidates"] == 2
    assert record["marker_qc"]["pre_marker_confidence"] \
        >= fqc.FROZEN_MARKER_THRESHOLD
    assert record["marker_qc"]["post_marker_confidence"] \
        >= fqc.FROZEN_MARKER_THRESHOLD
    assert abs(record["drift_ppm"]) <= fqc.FROZEN_DRIFT_TOLERANCE_PPM
    assert record["mapping_disagreement_s"] <= 0.010
    assert record["marker_leakage"]["passes_frozen_threshold"]
    assert record["byte_identical_preserved"]
    # standard lead: payload GT on trimmed input = 2.5 s lead - 50 ms margin
    assert abs(record["derived_payload_offset_on_trimmed_input_s"]
               - 2.45) < 1e-6
    assert record["direct_gt_crosscheck"]["passed"]
    assert record["direct_gt_crosscheck"]["gating"] is False
    assert record["trimmed_input_sha256"]
    assert record["raw_sha256"] == record["raw_sha256_after_analysis"]


def test_qc_take_gt_failed_when_post_marker_truncated(tmp_path):
    payload, _spec, buffer = _synthetic_buffer()
    raw = tmp_path / "incoming" / "final02.wav"
    # end inside the second chirp: 2.5 lead + 63.5 buffer + 2.0 tail,
    # cutting 2.3 s from the end leaves the post marker 0.3 s short
    _write_capture(raw, buffer, end_cut_s=2.3)
    ref_path = tmp_path / "REF-S01.wav"
    sf.write(str(ref_path), payload, FS, subtype="PCM_16")

    record = fqc.qc_take("final02", raw, _take_row(), _buffer_row(),
                         ref_path, tmp_path / "work")
    assert record["gt_status"] == "GT_FAILED"
    assert "expected exactly 2" in record["gt_fail_reason"]
    assert record["marker_qc"]["n_marker_candidates"] < 2
    assert record.get("trimmed_input_sha256") is None
    assert not (tmp_path / "work" / "trimmed" / "final02.wav").exists()


def test_qc_rejects_rescue_attempts_by_construction():
    """The QC function exposes no threshold/override argument to loosen."""
    import inspect
    sig = inspect.signature(fqc.qc_take)
    assert "threshold" not in sig.parameters
    assert not any("rescue" in name or "override" in name
                   for name in dir(fqc))


def test_partial_buffer_reference_offset_bookkeeping(tmp_path):
    payload, _spec, buffer = _synthetic_buffer()
    raw = tmp_path / "incoming" / "final21.wav"
    _write_capture(raw, buffer)
    # full-song reference whose payload slice starts at 90 s
    ref_signal = np.concatenate(
        [np.zeros(int(round(90.0 * FS))), payload])
    ref_path = tmp_path / "REF-S01.wav"
    sf.write(str(ref_path), ref_signal, FS, subtype="PCM_16")

    slice_start = 90.0
    record = fqc.qc_take(
        "final21", raw, _take_row(condition="PARTIAL"),
        _buffer_row(payload_slice_s=(slice_start, slice_start + 60.0)),
        ref_path, tmp_path / "work")
    assert record["gt_status"] == "GT_VALID"
    # reference GT = payload GT - slice start (negative offset convention)
    assert abs(record["derived_reference_offset_on_trimmed_input_s"]
               - (2.45 - slice_start)) < 1e-6
    assert record["direct_gt_crosscheck"]["passed"]


# ---------------------------------------------------------------------------
# freeze serialization, canonicalization, immutability
# ---------------------------------------------------------------------------


def test_canonical_serialization_is_stable():
    body = {"b": 1, "a": ["x", {"z": 2, "y": 3}], "u": "ä"}
    once = fqc.canonical_sha256(body)
    assert once == fqc.canonical_sha256(body)
    assert once == hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()


def test_freeze_write_once_and_immutability(tmp_path):
    path = tmp_path / "freeze.json"
    body = {"status": "FINAL_ACQUISITION_QC_PASS", "n": 26}
    frozen = fqc.write_freeze_once(path, body, "qc_freeze_sha256")
    assert frozen["qc_freeze_sha256"] == fqc.canonical_sha256(body)
    sidecar = path.with_suffix(".json.sha256")
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8").split()[0] == \
        fqc.sha256_file(path)
    assert fqc.verify_frozen_artifact(fqc.load_json(path),
                                      "qc_freeze_sha256") == []
    # identical rewrite is a no-op
    again = fqc.write_freeze_once(path, body, "qc_freeze_sha256")
    assert again == frozen
    # any content difference is refused (post-comparator rewrite forbidden)
    with pytest.raises(RuntimeError, match="different content"):
        fqc.write_freeze_once(path, {**body, "n": 27}, "qc_freeze_sha256")
    # a tampered freeze is detected
    tampered = fqc.load_json(path)
    tampered["body"]["n"] = 99
    errors = fqc.verify_frozen_artifact(tampered, "qc_freeze_sha256")
    assert errors and "mismatch" in errors[0]


def test_attestation_content():
    att = fqc.build_attestation()
    joined = " ".join(att["statements"])
    for required in ("26 takes", "ROOM_A + D1", "ROOM_B + D2",
                     "No editing, trimming, optimization",
                     "no minimum time gap"):
        assert required in joined
    assert att["session_mapping_source"].startswith("owner attestation")


def test_comparator_blind_execution_path():
    """No import statement in the QC module may reference a comparator or
    any module that runs one, and importing the module must not load one."""
    source = Path(fqc.__file__).read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines()
                    if re.match(r"^\s*(import|from)\s+", line)]
    assert import_lines, "no import lines found"
    for line in import_lines:
        for token in FORBIDDEN_IMPORT_TOKENS:
            assert token not in line, f"forbidden import: {line!r}"
    probe = (
        "import sys, json\n"
        "import experiments.applied_system.final_acquisition_qc\n"
        "tokens = " + json.dumps(list(FORBIDDEN_IMPORT_TOKENS)) + "\n"
        "offenders = sorted({k for k in sys.modules for t in tokens"
        " if t in k})\n"
        "assert not offenders, offenders\n"
        "print('comparator-blind OK')\n")
    proc = subprocess.run([sys.executable, "-c", probe], cwd=str(ROOT),
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    assert "comparator-blind OK" in proc.stdout
