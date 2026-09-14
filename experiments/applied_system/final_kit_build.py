"""Final acquisition kit: manifest, playback buffers, digital validation.

Authority: docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md (FROZEN)
+ the frozen source freeze (final_pack/final_source_freeze.json, rule
FINAL-SELECT-V1). This module materializes the ALREADY-FROZEN acquisition
design; it invents nothing scientific:

  24 primary positives (frozen condition allocation):
    final01-final10  ordinary            S01-S10
    final11-final16  low-level/tap       S01-S06 (odd slot LOW_LEVEL,
                                             even slot TAP_DOMINANT; 3+3)
    final17-final20  interference        S07-S10 (interference source plays
                                             from the second playback device)
    final21-final22  partial             S01-S02 (payload starts at
                                             min(90 s, duration-60 s))
    final23-final24  device-variation    S09-S10 (second recording device)
  + repeat01/repeat02: strict repeats of ordinary final01/final02 (S01/S02),
    reported separately from the 24 scored positives.
  Wrong-reference rotation (frozen before identities were filled): take i is
  offered reference slot S(i mod 10)+1; any ACCEPT is WRONG_ACCEPT, refusal
  is SAFE_ABSTAIN. The rotation never offers a take its true source.

Buffers use the UNCHANGED marker protocol
(`marker_protocol.render_marker_buffer`): chirp 0.75 s | guard 1.0 s |
60 s payload | guard 1.0 s | chirp 0.75 s @ 48 kHz mono PCM_16 (63.5 s).

DIGITAL VALIDATION ONLY: decode, hashes, payload placement, marker
generation/detection on clean self-check captures, GT bookkeeping, trim
bookkeeping, leakage check, deterministic rerender, manifest integrity.
NO COMPARATOR (RhythmAlign, GCC-PHAT, Panako, NCC, Kdenlive) MAY SEE FINAL
MATERIAL IN THIS TASK, and none is invoked here.

Generated audio stays under final_pack/ and is gitignored; only this
committed module + manifests/hashes enter Git. Sources are READ-ONLY.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import scipy
import soundfile as sf

from . import marker_protocol as mp
from . import pilot_source_selection as pss
from .runners import common

APPLIED_DIR = Path(__file__).resolve().parent
FINAL_PACK = APPLIED_DIR / "final_pack"
FREEZE_PATH = FINAL_PACK / "final_source_freeze.json"
MANIFEST_PATH = FINAL_PACK / "final_acquisition_manifest.json"
BUFFERS_DIR = FINAL_PACK / "buffers"
REFERENCES_DIR = FINAL_PACK / "local" / "references"
SELFCHECK_DIR = FINAL_PACK / "local" / "selfcheck"

FS = mp.FS
PAYLOAD_S = 60.0
PARTIAL_START_S = 90.0
SELF_CHECK_LEAD_S = 2.5
SELF_CHECK_TAIL_S = 2.0
SELF_CHECK_NOISE_STD = 3e-4      # same floor as the shakedown/pilot ambience

SLOTS = [f"S{i:02d}" for i in range(1, 11)]

SESSIONS = {
    "SESSION_1": {"room": "ROOM_A", "recording_device": "D1",
                  "playback_device": "P1",
                  "takes": ["final01", "final02", "final03", "final04",
                            "final05", "final06", "final07", "final08",
                            "final09", "final10", "repeat01", "repeat02"]},
    "SESSION_2": {"room": "ROOM_A", "recording_device": "D1",
                  "playback_device": "P1",
                  "takes": ["final11", "final12", "final13", "final14",
                            "final15", "final16", "final21", "final22"]},
    "SESSION_3": {"room": "ROOM_B", "recording_device": "D2",
                  "playback_device": "P1",
                  "takes": ["final17", "final18", "final19", "final20",
                            "final23", "final24"]},
}

DEVICES = {
    "D1": "primary recording device (the pilot-validated phone chain)",
    "D2": "second recording device (second phone / tablet / laptop "
          "internal microphone)",
    "P1": "main playback path (PC speakers)",
    "P2": "second playback device for the interference source "
          "(final17-final20 only)",
}

CONDITIONS = {
    # take: (source slot, condition, buffer kind)
    **{f"final{i:02d}": (f"S{i:02d}", "ORDINARY", "ORD")
       for i in range(1, 11)},
    "final11": ("S01", "LOW_LEVEL", "ORD"),
    "final12": ("S02", "TAP_DOMINANT", "ORD"),
    "final13": ("S03", "LOW_LEVEL", "ORD"),
    "final14": ("S04", "TAP_DOMINANT", "ORD"),
    "final15": ("S05", "LOW_LEVEL", "ORD"),
    "final16": ("S06", "TAP_DOMINANT", "ORD"),
    "final17": ("S07", "INTERFERENCE", "ORD"),
    "final18": ("S08", "INTERFERENCE", "ORD"),
    "final19": ("S09", "INTERFERENCE", "ORD"),
    "final20": ("S10", "INTERFERENCE", "ORD"),
    "final21": ("S01", "PARTIAL", "PART"),
    "final22": ("S02", "PARTIAL", "PART"),
    "final23": ("S09", "DEVICE_VARIATION", "ORD"),
    "final24": ("S10", "DEVICE_VARIATION", "ORD"),
    "repeat01": ("S01", "ORDINARY_REPEAT_STRICT_PAIR_OF_FINAL01", "ORD"),
    "repeat02": ("S02", "ORDINARY_REPEAT_STRICT_PAIR_OF_FINAL02", "ORD"),
}

PRIMARY_TAKES = [f"final{i:02d}" for i in range(1, 25)]


def wrong_reference_slot(take: str) -> str:
    """Frozen rotation S(i mod 10)+1 over the PRIMARY take number i=1..24."""
    i = int(take[5:])
    return f"S{(i % 10) + 1:02d}"


def partial_start_s(duration_s: float) -> float:
    """Frozen partial rule: 90 s offset when the song fits, else its last
    60 s. Deterministic for any duration >= 60 s."""
    return min(PARTIAL_START_S, max(0.0, duration_s - PAYLOAD_S))


def buffer_id(slot: str, kind: str) -> str:
    return f"BUF-{slot}" if kind == "ORD" else f"BUF-{slot}-PART"


def pss_decode(path: str):
    y, sr = sf.read(path, dtype="float64", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != FS:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(int(sr), FS)
        y = resample_poly(y, FS // g, int(sr) // g)
    return np.ascontiguousarray(y)


def write_wav_int16(path: Path, y: np.ndarray, fs: int = FS):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.asarray(y, dtype=np.float64), fs,
             subtype="PCM_16")


def self_check_seed(buffer_id: str) -> int:
    return int.from_bytes(
        hashlib.sha256(f"final_kit_selfcheck:{buffer_id}".encode("utf-8"))
        .digest()[:4], "little")


def payload_placement_check(buffer_path: Path, ref_path: Path,
                            buffer_payload_start_sample: int,
                            ref_payload_start_sample: int,
                            payload_len_samples: int) -> dict:
    buf16, _ = sf.read(str(buffer_path), dtype="int16", always_2d=False)
    ref16, _ = sf.read(str(ref_path), dtype="int16", always_2d=False)
    b_lo = buffer_payload_start_sample
    r_lo = ref_payload_start_sample
    identical = bool(np.array_equal(buf16[b_lo:b_lo + payload_len_samples],
                                    ref16[r_lo:r_lo + payload_len_samples]))
    return {"payload_equals_reference_slice": identical,
            "buffer_payload_samples": [int(b_lo),
                                       int(b_lo + payload_len_samples)],
            "reference_payload_samples": [int(r_lo),
                                          int(r_lo + payload_len_samples)]}


def run_self_check(bid: str, buffer_path: Path, spec: mp.BufferSpec,
                   payload_len_samples: int, ref_path: Path,
                   slice_start_s: float, out_dir: Path) -> dict:
    """Deterministic digital capture -> GT -> trim -> leakage on the
    WRITTEN buffer bytes (mirrors the pilot/shakedown prepare stage)."""
    buffer, _ = sf.read(str(buffer_path), dtype="float64", always_2d=False)
    rng = np.random.default_rng(self_check_seed(bid))
    capture = np.concatenate([
        rng.normal(0.0, SELF_CHECK_NOISE_STD,
                   int(round(SELF_CHECK_LEAD_S * FS))),
        buffer,
        rng.normal(0.0, SELF_CHECK_NOISE_STD,
                   int(round(SELF_CHECK_TAIL_S * FS)))])
    capture_path = out_dir / f"selfcheck_capture_{bid}.wav"
    write_wav_int16(capture_path, capture, FS)

    y_cap, _ = sf.read(str(capture_path), dtype="float64", always_2d=False)
    gt = mp.derive_ground_truth(y_cap, spec, FS)
    if gt.status != mp.GT_VALID:
        return {"passed": False, "gt_status": gt.status,
                "fail_reason": gt.fail_reason, "marker_qc": gt.qc_dict()}
    tr = mp.trim_capture(y_cap, gt, spec, FS, trim_start=0)
    if not tr.ok:
        return {"passed": False, "gt_status": gt.status,
                "fail_reason": f"trim failed: {tr.fail_reason}"}
    leak = mp.marker_leakage_check(tr.trimmed, FS)
    placement = payload_placement_check(
        buffer_path, ref_path, int(spec.payload_start_sample),
        int(round(slice_start_s * FS)), payload_len_samples)
    intended_reference_gt_s = tr.gt_offset_s - slice_start_s
    check = {
        "passed": bool(not leak["leakage"]
                       and placement["payload_equals_reference_slice"]),
        "gt_status": gt.status,
        "scale_error": gt.scale_error,
        "mapping_disagreement_s": gt.diagnostics[
            "mapping_disagreement_samples"] / FS,
        "n_marker_candidates": gt.marker_qc["n_marker_candidates"],
        "pre_marker_confidence": gt.marker_qc["pre_marker"]["confidence"],
        "post_marker_confidence": gt.marker_qc["post_marker"]["confidence"],
        "gt_offset_s_payload_in_trimmed": tr.gt_offset_s,
        "intended_reference_gt_s": intended_reference_gt_s,
        "marker_leakage_check": leak,
        "payload_placement": placement,
        "selfcheck_capture_sha256": common.sha256_file(capture_path),
        "marker_qc": gt.qc_dict(),
        "trim": tr.as_dict(),
    }
    return check


def build_allocation(freeze: dict) -> dict:
    """Freeze the 26-take acquisition allocation from the frozen sources."""
    refs = freeze["body"]["references"]
    itf = freeze["body"]["interference"]
    takes = {}
    for take, (slot, condition, kind) in CONDITIONS.items():
        session = next(s for s, cfg in SESSIONS.items() if take in cfg["takes"])
        cfg = SESSIONS[session]
        row = {
            "take": take,
            "primary": take in PRIMARY_TAKES,
            "source_slot": slot,
            "source_identity": refs[slot]["identity"],
            "source_sha256": refs[slot]["sha256"],
            "condition": condition,
            "session": session,
            "room": cfg["room"],
            "recording_device": cfg["recording_device"],
            "playback_device": cfg["playback_device"],
            "playback_buffer": buffer_id(slot, kind),
            "gt_stratum": "EXACT_GT",
            "wrong_reference_slot": (wrong_reference_slot(take)
                                     if take in PRIMARY_TAKES else None),
            "wrong_reference_sha256": (refs[wrong_reference_slot(take)]
                                       ["sha256"]
                                       if take in PRIMARY_TAKES else None),
            "interference_identity": (itf["identity"]
                                      if condition == "INTERFERENCE"
                                      else None),
            "interference_playback_device": ("P2"
                                             if condition == "INTERFERENCE"
                                             else None),
            "destination_dir": "experiments/applied_system/final_pack/incoming/",
            "destination_basename": take,
            "status": "AWAITING_FINAL_RECORDING",
        }
        assert row["wrong_reference_slot"] != row["source_slot"], (
            f"{take}: wrong-reference rotation offered the true source")
        takes[take] = row
    return takes


def build_manifest_body(freeze: dict, environment: dict) -> dict:
    refs = freeze["body"]["references"]
    itf = freeze["body"]["interference"]
    takes = build_allocation(freeze)
    return {
        "final_pack": "FINAL_PACK",
        "status": "AWAITING_FINAL_RECORDING",
        "authority": ("docs/research/applied_system/"
                      "FINAL_BENCHMARK_PROTOCOL.md + final_source_freeze.json"),
        "source_freeze_sha256": freeze["freeze_sha256"],
        "selection_rule_id": freeze["body"]["selection_rule_id"],
        "no_comparator_run": True,
        "performance_blind": True,
        "counts": {
            "primary_positives": 24,
            "strict_repeats": 2,
            "total_physical_recordings": 26,
            "conditions": {
                "ORDINARY": 10, "LOW_LEVEL": 3, "TAP_DOMINANT": 3,
                "INTERFERENCE": 4, "PARTIAL": 2, "DEVICE_VARIATION": 2},
            "sessions": 3, "rooms": 2, "recording_devices": 2,
        },
        "slots": {slot: {
            "identity": refs[slot]["identity"],
            "artist": refs[slot]["artist"],
            "basename": refs[slot]["basename"],
            "path": refs[slot]["path"],
            "sha256": refs[slot]["sha256"],
            "duration_s": refs[slot]["duration_s"],
            "repetitive_flag": refs[slot]["repetitive_flag"],
            "r_long": refs[slot]["r_long"],
        } for slot in SLOTS},
        "interference": {
            "identity": itf["identity"], "artist": itf["artist"],
            "basename": itf["basename"], "path": itf["path"],
            "sha256": itf["sha256"], "duration_s": itf["duration_s"],
            "role": itf["role"],
            "takes": ["final17", "final18", "final19", "final20"],
        },
        "sessions": SESSIONS,
        "devices": DEVICES,
        "rooms": {
            "ROOM_A": "main recording room (the pilot-validated room)",
            "ROOM_B": "second room with different acoustics",
        },
        "gt_contract": {
            "gt_stratum": "EXACT_GT (dual-marker ground truth per take)",
            "marker_threshold": mp.MIN_MARKER_CONFIDENCE,
            "frozen_marker_threshold": 0.163837792269,
            "drift_tolerance_ppm": 128.486056,
            "max_mapping_disagreement_s": mp.MAX_MAPPING_DISAGREEMENT_S,
            "trim_rule": "remove marker/guard holes with 50 ms external "
                         "margins; concatenate; never resample/stretch",
            "reference_gt_bookkeeping": (
                "ORD buffers: reference GT = payload GT (payload starts at "
                "song start). PART buffers: reference GT = payload GT - "
                "slice start. Actual per-take GT is derived from the two "
                "markers at analysis time."),
        },
        "wrong_reference_rule": (
            "take i is offered reference slot S(i mod 10)+1 (frozen before "
            "identities were filled); any ACCEPT is WRONG_ACCEPT, refusal "
            "is SAFE_ABSTAIN; never changed from results"),
        "takes": takes,
        "environment": environment,
    }


def render_buffers(body: dict) -> dict:
    """Render the 12 playback buffers + 10 references + interference copy
    from the hash-verified frozen sources; self-check every buffer."""
    slots = body["slots"]
    decoded = {}
    for slot in SLOTS:
        path = slots[slot]["path"]
        actual = common.sha256_file(path)
        if actual != slots[slot]["sha256"]:
            raise RuntimeError(f"{slot}: source hash changed since freeze")
        decoded[slot] = pss_decode(path)
    itf_path = body["interference"]["path"]
    if common.sha256_file(itf_path) != body["interference"]["sha256"]:
        raise RuntimeError("interference: source hash changed since freeze")

    references = {}
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    for slot in SLOTS:
        ref_path = REFERENCES_DIR / f"REF-{slot}.wav"
        write_wav_int16(ref_path, decoded[slot], FS)
        references[f"REF-{slot}"] = {
            "path": str(ref_path),
            "sha256": common.sha256_file(ref_path),
            "duration_s": round(len(decoded[slot]) / FS, 6),
            "source_sha256": slots[slot]["sha256"],
            "role": "agent-side comparator reference (FULL decoded song); "
                    "gitignored, regenerable from the frozen source",
        }

    BUFFERS_DIR.mkdir(parents=True, exist_ok=True)
    SELFCHECK_DIR.mkdir(parents=True, exist_ok=True)
    buffers = {}
    needed = sorted({row["playback_buffer"]
                     for row in body["takes"].values()})
    for bid in needed:
        slot = bid[4:7]
        kind = "PART" if bid.endswith("-PART") else "ORD"
        payload_len = int(round(PAYLOAD_S * FS))
        if kind == "ORD":
            start_sample = 0
        else:
            # frozen partial rule in exact samples: 90 s offset when the
            # song fits, else its last 60 s
            start_sample = min(int(round(PARTIAL_START_S * FS)),
                               len(decoded[slot]) - payload_len)
            if start_sample < 0:
                raise RuntimeError(f"{bid}: source shorter than payload")
        start_s = start_sample / FS
        payload = decoded[slot][start_sample:start_sample + payload_len]
        if len(payload) != payload_len:
            raise RuntimeError(f"{bid}: source too short for slice")
        spec = mp.buffer_spec(payload_len, FS)
        path = BUFFERS_DIR / f"{bid}.wav"
        write_wav_int16(path, mp.render_marker_buffer(payload, FS), FS)
        check = run_self_check(bid, path, spec, payload_len,
                               REFERENCES_DIR / f"REF-{slot}.wav",
                               start_s, SELFCHECK_DIR)
        if not check["passed"]:
            raise RuntimeError(f"{bid} self-check failed: "
                               f"{json.dumps(check, default=str)}")
        buffers[bid] = {
            "buffer_id": bid,
            "path": str(path),
            "sha256": common.sha256_file(path),
            "bytes": path.stat().st_size,
            "duration_s": round(spec.total_len_samples / FS, 6),
            "source_slot": slot,
            "source_sha256": slots[slot]["sha256"],
            "payload_slice_s": [round(start_s, 6),
                                round(start_s + PAYLOAD_S, 6)],
            "payload_slice_start_sample": int(start_sample),
            "condition_role": (
                "ordinary payload from song start"
                if kind == "ORD" else
                f"partial payload starting at {start_s:.3f} s "
                "(min(90 s, duration-60 s))"),
            "marker_positions": {
                "marker1_start_sample": int(spec.marker1_start_sample),
                "payload_start_sample": int(spec.payload_start_sample),
                "payload_end_sample": int(spec.payload_end_sample),
                "marker2_start_sample": int(spec.marker2_start_sample),
                "total_samples": int(spec.total_len_samples),
            },
            "intended_gt": {
                "payload_gt_s_with_standard_lead":
                    round(SELF_CHECK_LEAD_S - mp.PRE_TRIM_MARGIN_S, 6),
                "reference_gt_s_with_standard_lead":
                    round(SELF_CHECK_LEAD_S - mp.PRE_TRIM_MARGIN_S
                          - start_s, 6),
                "bookkeeping": "reference GT = payload GT - slice start",
            },
            "used_by_takes": sorted(
                take for take, row in body["takes"].items()
                if row["playback_buffer"] == bid),
            "selfcheck": check,
        }
        print(f"  {bid}: slice {start_s:.3f}s+60s "
              f"sha256={buffers[bid]['sha256'][:16]}… self-check OK "
              f"(ref GT {check['intended_reference_gt_s']:+.3f}s)")

    interference_copy = FINAL_PACK / (
        "INTERFERENCE" + Path(body["interference"]["path"]).suffix.lower())
    if Path(body["interference"]["path"]).resolve() != \
            interference_copy.resolve():
        shutil.copyfile(body["interference"]["path"], interference_copy)
    if common.sha256_file(interference_copy) != \
            body["interference"]["sha256"]:
        raise RuntimeError("interference copy hash mismatch")
    interference_asset = {
        "path": str(interference_copy),
        "sha256": body["interference"]["sha256"],
        "source_path": body["interference"]["path"],
        "role": "owner hand-off copy for the second playback device "
                "(final17-final20 only); never a reference",
    }
    print(f"  INTERFERENCE copy: {interference_copy.name}")
    return {"references": references, "buffers": buffers,
            "interference_asset": interference_asset}


def attach_results(body: dict, rendered: dict) -> dict:
    body = json.loads(json.dumps(body, ensure_ascii=False))
    body["references"] = rendered["references"]
    body["buffers"] = {bid: {k: v for k, v in row.items() if k != "selfcheck"}
                       for bid, row in rendered["buffers"].items()}
    body["interference_asset"] = rendered["interference_asset"]
    body["buffer_selfchecks"] = {
        bid: {k: v for k, v in row["selfcheck"].items()
              if k not in ("marker_qc", "trim")}
        for bid, row in rendered["buffers"].items()}
    return body


def validate_kit(freeze: dict, manifest_path: Path) -> dict:
    """Full kit validation (digital only). Re-derives every gate."""
    frozen_manifest = common.load_json(manifest_path)
    body = frozen_manifest["body"]
    failures = []

    def check(ok, msg):
        if not ok:
            failures.append(msg)
        return bool(ok)

    # manifest integrity
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
    check(hashlib.sha256(canon).hexdigest()
          == frozen_manifest["manifest_hash"],
          "manifest_hash mismatch (edited after freeze?)")
    check(body["status"] == "AWAITING_FINAL_RECORDING",
          "manifest status is not AWAITING_FINAL_RECORDING")
    check(body["source_freeze_sha256"] == freeze["freeze_sha256"],
          "manifest does not reference the current source freeze")

    # counts and structure
    takes = body["takes"]
    check(len(takes) == 26, "take count != 26")
    check(sum(1 for t in takes.values() if t["primary"]) == 24,
          "primary positives != 24")
    conds = {}
    for t in takes.values():
        if t["primary"]:
            conds[t["condition"]] = conds.get(t["condition"], 0) + 1
    check(conds == {"ORDINARY": 10, "LOW_LEVEL": 3, "TAP_DOMINANT": 3,
                    "INTERFERENCE": 4, "PARTIAL": 2, "DEVICE_VARIATION": 2},
          f"condition allocation wrong: {conds}")
    check(sum(1 for t in takes.values()
              if t["condition"].startswith("ORDINARY_REPEAT")) == 2,
          "strict repeats != 2")
    check(len(body["slots"]) == 10, "slot count != 10")
    check(len({s["sha256"] for s in body["slots"].values()}) == 10,
          "reference identities are not unique")
    stress = [s["identity"] for s in body["slots"].values()
              if s["repetitive_flag"] == "REPETITIVE_STRESS_SOURCE"]
    check(len(stress) >= 3, "fewer than 3 repetitive references")
    check(body["interference"]["sha256"] not in
          {s["sha256"] for s in body["slots"].values()},
          "interference identity collides with a reference")
    rooms = {t["room"] for t in takes.values()}
    rec_devs = {t["recording_device"] for t in takes.values()}
    sessions = {t["session"] for t in takes.values()}
    check(len(sessions) >= 3, "fewer than 3 sessions")
    check(len(rec_devs) >= 2, "fewer than 2 recording devices")
    check(len(rooms) >= 2, "fewer than 2 rooms")

    # wrong-reference rotation + status
    for take, row in takes.items():
        if not row["primary"]:
            check(row["wrong_reference_slot"] is None,
                  f"{take}: repeat carries a wrong-reference slot")
            continue
        expect = f"S{(int(take[5:]) % 10) + 1:02d}"
        check(row["wrong_reference_slot"] == expect,
              f"{take}: wrong-reference slot != frozen rotation")
        check(row["wrong_reference_slot"] != row["source_slot"],
              f"{take}: wrong reference equals true source")
        check(row["status"] == "AWAITING_FINAL_RECORDING",
              f"{take}: status not AWAITING_FINAL_RECORDING")
        check(row["gt_stratum"] == "EXACT_GT", f"{take}: gt stratum wrong")

    # device-variation must use the other recording device than the
    # ordinary takes of the same slot
    for take in ("final23", "final24"):
        slot = takes[take]["source_slot"]
        ordinary_dev = takes[f"final{int(slot[1:]):02d}"]["recording_device"]
        check(takes[take]["recording_device"] != ordinary_dev,
              f"{take}: device-variation reuses the ordinary device")

    # buffers exist, hash-match, self-checks passed, take links resolve
    for bid, row in body["buffers"].items():
        path = Path(row["path"])
        check(path.exists(), f"{bid}: file missing")
        if path.exists():
            check(common.sha256_file(path) == row["sha256"],
                  f"{bid}: hash mismatch vs manifest")
            check(row["duration_s"] == 63.5, f"{bid}: duration != 63.5 s")
        sc = body["buffer_selfchecks"][bid]
        check(sc["gt_status"] == "GT_VALID", f"{bid}: self-check GT invalid")
        check(sc["n_marker_candidates"] == 2,
              f"{bid}: marker count rule failed")
        check(abs(sc["scale_error"]) <= mp.PROVISIONAL_MAX_CLOCK_SCALE_ERROR,
              f"{bid}: clock scale beyond tolerance")
        check(sc["mapping_disagreement_s"] <= mp.MAX_MAPPING_DISAGREEMENT_S,
              f"{bid}: mapping disagreement beyond gate")
        check(not sc["marker_leakage_check"]["leakage"],
              f"{bid}: marker leakage after simulated trim")
        check(sc["payload_placement"]["payload_equals_reference_slice"],
              f"{bid}: payload != reference slice")
        expected_payload_gt = SELF_CHECK_LEAD_S - mp.PRE_TRIM_MARGIN_S
        check(abs(sc["gt_offset_s_payload_in_trimmed"] - expected_payload_gt)
              < 1e-9, f"{bid}: unexpected payload GT")
        start_s = row["payload_slice_start_sample"] / FS
        check(abs(sc["intended_reference_gt_s"]
                  - (expected_payload_gt - start_s)) < 1e-6,
              f"{bid}: unexpected reference GT")
    for take, row in takes.items():
        check(row["playback_buffer"] in body["buffers"],
              f"{take}: unknown buffer {row['playback_buffer']}")

    # interference asset + references
    itf = body["interference_asset"]
    check(Path(itf["path"]).exists(), "INTERFERENCE asset missing")
    if Path(itf["path"]).exists():
        check(common.sha256_file(itf["path"]) == itf["sha256"],
              "INTERFERENCE asset hash mismatch")
    for ref_id, row in body["references"].items():
        check(Path(row["path"]).exists(), f"{ref_id}: missing")
        if Path(row["path"]).exists():
            check(common.sha256_file(Path(row["path"])) == row["sha256"],
                  f"{ref_id}: hash mismatch")

    # source files still byte-identical to the freeze
    for slot in SLOTS:
        s = body["slots"][slot]
        check(common.sha256_file(s["path"]) == s["sha256"],
              f"{slot}: source hash drifted since freeze")
    check(common.sha256_file(body["interference"]["path"])
          == body["interference"]["sha256"],
          "interference source hash drifted since freeze")

    return {"ok": not failures, "failures": failures,
            "manifest": str(manifest_path),
            "manifest_hash": frozen_manifest["manifest_hash"]}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="build + validate the final acquisition kit (digital "
                    "validation ONLY; no comparator is invoked)")
    ap.add_argument("--skip-render", action="store_true",
                    help="validate only; requires an existing manifest")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args(argv)

    freeze = common.load_json(FREEZE_PATH)
    if freeze.get("body", {}).get("status") != "FINAL_SOURCES_FROZEN":
        raise RuntimeError("source freeze is not FINAL_SOURCES_FROZEN")
    canon = json.dumps(freeze["body"], sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False).encode()
    if hashlib.sha256(canon).hexdigest() != freeze["freeze_sha256"]:
        raise RuntimeError("source freeze hash mismatch")

    environment = {
        "python": sys.version.split()[0], "numpy": np.__version__,
        "scipy": scipy.__version__, "soundfile": sf.__version__,
        "libsndfile": sf.__libsndfile_version__,
    }

    if args.validate_only or args.skip_render:
        result = validate_kit(freeze, MANIFEST_PATH)
        print(json.dumps({k: v for k, v in result.items() if k != "failures"}
                         if result["ok"] else result, indent=1))
        if not result["ok"]:
            raise SystemExit(1)
        print("[final-kit] VALIDATION OK")
        return result

    print("[final-kit] freezing acquisition allocation from the source "
          "freeze …")
    body = build_manifest_body(freeze, environment)
    print("[final-kit] rendering 12 playback buffers + references "
          "(digital self-checks only) …")
    rendered = render_buffers(body)
    body = attach_results(body, rendered)

    frozen = {"manifest_hash": hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest(),
        "body": body}
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(frozen, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"[final-kit] manifest -> {MANIFEST_PATH}")

    result = validate_kit(freeze, MANIFEST_PATH)
    if not result["ok"]:
        print(json.dumps(result["failures"], indent=1))
        raise SystemExit(1)
    print("[final-kit] VALIDATION OK — status AWAITING_FINAL_RECORDING")
    return result


if __name__ == "__main__":
    main()
