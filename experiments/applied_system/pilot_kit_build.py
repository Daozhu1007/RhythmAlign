"""Fresh-pilot kit build: render playback buffers + references + self-check.

PILOT_ONLY / NOT_PAPER_EVIDENCE. Consumes the FROZEN selection record
(`pilot_source_selection.py` output) and renders the three playback
buffers of FRESH_PILOT_PLAN section 5 with the existing marker protocol
(`marker_protocol.render_marker_buffer`, unchanged):

    chirp 0.75 s | guard 1.0 s | 60 s payload | guard 1.0 s | chirp 0.75 s
    @ 48 kHz mono PCM_16  (63.5 s per buffer)

    BUF-A     payload = song A from 0 s
    BUF-B1    payload = song B from 0 s
    BUF-BMID  payload = song B from 90 s (mid-song placement)

Reference pool (agent-side, gitignored): the FULL decoded songs
(REF-A / REF-B), matching production usage where the reference is the
whole track. GT bookkeeping for BUF-BMID takes is therefore
`gt_offset_s(payload in trimmed input) - 90.0` — recorded here as
`intended_reference_gt_s` in the self-check, to be applied by the
analysis harness. BUF-A / BUF-B1 references coincide with the payload
start, so their reference GT equals the payload GT.

Deterministic: fixed decode (libsndfile), fixed protocol constants, fixed
self-check noise seeds. Every rendered artifact is hashed; sources are
re-hashed and verified against the frozen selection record BEFORE any
rendering (FRESH_PILOT_PLAN section 9 anti-cherry-picking rule).

Digital self-check per buffer (mirrors the shakedown prepare stage):
a deterministic quiet-noise capture (lead 2.5 s + buffer + tail 2.0 s) is
written and re-read from disk, then the full GT/QC/trim/leakage pipeline
must pass on the shipped bytes. This validates the marker/GT machinery on
the actual rendered files; it is NOT an acoustic test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import scipy

from . import marker_protocol as mp
from .runners import common

APPLIED_DIR = Path(__file__).resolve().parent
PILOT_PACK = APPLIED_DIR / "pilot_pack"
DEFAULT_SELECTION = PILOT_PACK / "source_selection.json"

FS = mp.FS
PAYLOAD_S = 60.0
BMID_START_S = 90.0
SELF_CHECK_LEAD_S = 2.5
SELF_CHECK_TAIL_S = 2.0
SELF_CHECK_NOISE_STD = 3e-4      # same floor as the shakedown ambience

BUFFERS = {
    "BUF-A": ("song_a", 0.0),
    "BUF-B1": ("song_b", 0.0),
    "BUF-BMID": ("song_b", BMID_START_S),
}


def write_wav_int16(path: Path, y: np.ndarray, fs: int = FS):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.asarray(y, dtype=np.float64), fs, subtype="PCM_16")


def decode_reference(path: str) -> np.ndarray:
    """Full-track mono float64 at the protocol rate (resampled only if the
    source is not already 48 kHz; both selected sources are)."""
    y, sr = sf.read(path, dtype="float64", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != FS:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(int(sr), FS)
        y = resample_poly(y, FS // g, int(sr) // g)
    return np.ascontiguousarray(y)


def self_check_seed(buffer_id: str) -> int:
    return int.from_bytes(
        hashlib.sha256(f"pilot_kit_selfcheck:{buffer_id}".encode("utf-8"))
        .digest()[:4], "little")


def payload_placement_check(buffer_path: Path, ref_path: Path,
                            buffer_payload_start_sample: int,
                            ref_payload_start_sample: int,
                            payload_len_samples: int) -> dict:
    """Bit-equality proof that the written buffer's payload region equals
    the payload region of the written reference file. Both files went
    through the identical libsndfile float->PCM_16 quantization, so
    identical source floats must give identical int16 bytes."""
    buf16, _ = sf.read(str(buffer_path), dtype="int16", always_2d=False)
    ref16, _ = sf.read(str(ref_path), dtype="int16", always_2d=False)
    b_lo = buffer_payload_start_sample
    b_hi = b_lo + payload_len_samples
    r_lo = ref_payload_start_sample
    r_hi = r_lo + payload_len_samples
    identical = bool(np.array_equal(buf16[b_lo:b_hi], ref16[r_lo:r_hi]))
    return {
        "payload_equals_reference_slice": identical,
        "buffer_payload_samples": [int(b_lo), int(b_hi)],
        "reference_payload_samples": [int(r_lo), int(r_hi)],
    }


def run_self_check(buffer_id: str, buffer_path: Path, spec: mp.BufferSpec,
                   buffer_payload_start_sample: int,
                   ref_payload_start_sample: int, payload_len_samples: int,
                   ref_path: Path, out_dir: Path) -> dict:
    """Deterministic digital capture -> GT -> trim -> leakage on the
    WRITTEN buffer bytes (mirrors shakedown prepare)."""
    buffer, _ = sf.read(str(buffer_path), dtype="float64", always_2d=False)
    rng = np.random.default_rng(self_check_seed(buffer_id))
    parts = [rng.normal(0.0, SELF_CHECK_NOISE_STD,
                        int(round(SELF_CHECK_LEAD_S * FS))),
             buffer,
             rng.normal(0.0, SELF_CHECK_NOISE_STD,
                        int(round(SELF_CHECK_TAIL_S * FS)))]
    capture = np.concatenate(parts)
    capture_path = out_dir / f"selfcheck_capture_{buffer_id}.wav"
    write_wav_int16(capture_path, capture, FS)

    y_cap, _ = sf.read(str(capture_path), dtype="float64", always_2d=False)
    gt = mp.derive_ground_truth(y_cap, spec, FS)
    if gt.status != mp.GT_VALID:
        return {"passed": False, "gt_status": gt.status,
                "fail_reason": gt.fail_reason,
                "marker_qc": gt.qc_dict()}

    tr = mp.trim_capture(y_cap, gt, spec, FS, trim_start=0)
    if not tr.ok:
        return {"passed": False, "gt_status": gt.status,
                "fail_reason": f"trim failed: {tr.fail_reason}"}
    leak = mp.marker_leakage_check(tr.trimmed, FS)
    placement = payload_placement_check(buffer_path, ref_path,
                                        buffer_payload_start_sample,
                                        ref_payload_start_sample,
                                        payload_len_samples)
    intended_reference_gt_s = (tr.gt_offset_s - BMID_START_S
                               if buffer_id == "BUF-BMID"
                               else tr.gt_offset_s)

    check = {
        "passed": bool(not leak["leakage"]
                       and placement["payload_equals_reference_slice"]),
        "gt_status": gt.status,
        "scale_error": gt.scale_error,
        "mapping_disagreement_s": (gt.diagnostics[
            "mapping_disagreement_samples"] / FS),
        "n_marker_candidates": gt.marker_qc["n_marker_candidates"],
        "pre_marker_confidence": gt.marker_qc["pre_marker"]["confidence"],
        "post_marker_confidence": gt.marker_qc["post_marker"]["confidence"],
        "gt_offset_s_payload_in_trimmed": tr.gt_offset_s,
        "intended_reference_gt_s": intended_reference_gt_s,
        "marker_leakage_check": leak,
        "payload_placement": placement,
        "selfcheck_capture_sha256": common.sha256_file(capture_path),
    }
    check["marker_qc"] = gt.qc_dict()
    check["trim"] = tr.as_dict()
    return check


def build_kit(selection_path: Path, buffers_dir: Path, refs_dir: Path,
              selfcheck_dir: Path) -> dict:
    selection = common.load_json(selection_path)
    if selection.get("status") != "SELECTED_FROZEN":
        raise RuntimeError(
            f"{selection_path}: status {selection.get('status')!r} — "
            "selection must be SELECTED_FROZEN before the kit build")

    sources = {}
    for key in ("song_a", "song_b", "interference"):
        row = selection[key]
        actual = common.sha256_file(row["path"])
        if actual != row["sha256"]:
            raise RuntimeError(
                f"{key} source hash changed since selection:\n"
                f"  frozen:  {row['sha256']}\n  actual:  {actual}")
        sources[key] = row

    decoded = {k: decode_reference(v["path"])
               for k, v in (("song_a", sources["song_a"]),
                            ("song_b", sources["song_b"]))}

    refs_dir.mkdir(parents=True, exist_ok=True)
    ref_paths = {}
    for key, song_id in (("song_a", "A"), ("song_b", "B")):
        path = refs_dir / f"REF-{song_id}.wav"
        write_wav_int16(path, decoded[key], FS)
        ref_paths[key] = path

    buffers_dir.mkdir(parents=True, exist_ok=True)
    selfcheck_dir.mkdir(parents=True, exist_ok=True)
    buffers = {}
    for buffer_id, (song_key, start_s) in BUFFERS.items():
        start_sample = int(round(start_s * FS))
        payload_len = int(round(PAYLOAD_S * FS))
        end_sample = start_sample + payload_len
        payload = decoded[song_key][start_sample:end_sample]
        if len(payload) != payload_len:
            raise RuntimeError(
                f"{buffer_id}: source too short for payload "
                f"[{start_s}s, {start_s + PAYLOAD_S}s]")
        buffer = mp.render_marker_buffer(payload, FS)
        spec = mp.buffer_spec(len(payload), FS)

        path = buffers_dir / f"{buffer_id}.wav"
        write_wav_int16(path, buffer, FS)

        # analyze the SHIPPED file bytes, not the in-memory floats
        check = run_self_check(buffer_id, path, spec,
                               int(spec.payload_start_sample),
                               start_sample, payload_len,
                               ref_paths[song_key], selfcheck_dir)
        if not check["passed"]:
            print(f"  SELF-CHECK FAILED for {buffer_id}: {json.dumps(check)}",
                  file=sys.stderr)
            raise RuntimeError(f"{buffer_id} self-check failed")

        buffers[buffer_id] = {
            "path": str(path),
            "sha256": common.sha256_file(path),
            "bytes": path.stat().st_size,
            "duration_s": round(spec.total_len_samples / FS, 6),
            "layout": ("chirp 0.75s | guard 1.0s | payload 60.0s | "
                       "guard 1.0s | chirp 0.75s @ 48 kHz PCM_16 mono"),
            "marker1_start_sample": int(spec.marker1_start_sample),
            "payload_start_sample": int(spec.payload_start_sample),
            "payload_end_sample": int(spec.payload_end_sample),
            "marker2_start_sample": int(spec.marker2_start_sample),
            "total_samples": int(spec.total_len_samples),
            "payload_source": {
                "identity": sources[song_key]["path"],
                "source_sha256": sources[song_key]["sha256"],
                "payload_start_s": start_s,
                "payload_end_s": start_s + PAYLOAD_S,
            },
            "selfcheck": check,
        }
        print(f"  {buffer_id}: {path.name} "
              f"sha256={buffers[buffer_id]['sha256'][:16]}… "
              f"self-check OK (payload GT {check['gt_offset_s_payload_in_trimmed']:+.3f}s"
              + (f", reference GT {check['intended_reference_gt_s']:+.3f}s"
                 if buffer_id == "BUF-BMID" else "") + ")")

    interference_src = sources["interference"]
    interference_copy = PILOT_PACK / (
        "INTERFERENCE" + Path(interference_src["path"]).suffix.lower())
    if Path(interference_src["path"]).resolve() != \
            interference_copy.resolve():
        shutil.copyfile(interference_src["path"], interference_copy)
    interference = {
        "path": str(interference_copy),
        "source_path": interference_src["path"],
        "source_identity": interference_src["sha256"],
        "sha256": common.sha256_file(interference_copy),
        "duration_s": interference_src["duration_s"],
        "role": ("background source for take 8 only; never a reference in "
                 "any pairing"),
    }
    if interference["sha256"] != interference_src["sha256"]:
        raise RuntimeError("interference copy hash mismatch")

    references = {}
    for key, song_id in (("song_a", "A"), ("song_b", "B")):
        references[f"REF-{song_id}"] = {
            "path": str(ref_paths[key]),
            "sha256": common.sha256_file(ref_paths[key]),
            "duration_s": round(len(decoded[key]) / FS, 6),
            "source_sha256": sources[key]["sha256"],
            "role": ("agent-side comparator reference (FULL decoded song); "
                     "gitignored generated media, regenerable from the "
                     "frozen source"),
        }

    return {
        "pilot_pack_only": "PILOT_PACK_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "status": "KIT_READY",
        "authority": "docs/research/applied_system/FRESH_PILOT_PLAN.md",
        "selection_record": str(selection_path),
        "buffers": buffers,
        "references": references,
        "interference": interference,
        "protocol": {
            "module": "experiments.applied_system.marker_protocol",
            "fs": FS,
            "chirp_duration_s": mp.CHIRP_DURATION_S,
            "guard_duration_s": mp.GUARD_DURATION_S,
            "payload_duration_s": PAYLOAD_S,
            "bmid_payload_start_s": BMID_START_S,
            "min_marker_confidence": mp.MIN_MARKER_CONFIDENCE,
            "max_mapping_disagreement_s": mp.MAX_MAPPING_DISAGREEMENT_S,
            "wav_format": "PCM_16 mono (protocol rate)",
            "bmid_gt_bookkeeping": (
                "reference GT = payload GT in trimmed input - "
                f"{BMID_START_S} s (reference pool = full decoded songs)"),
        },
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "soundfile": sf.__version__,
            "libsndfile": sf.__libsndfile_version__,
        },
    }


def update_take_plan(kit: dict, take_plan_path: Path) -> None:
    plan = common.load_json(take_plan_path)
    if plan.get("status") != "AWAITING_KIT_BUILD":
        raise RuntimeError(
            f"{take_plan_path}: status {plan.get('status')!r} — expected "
            "AWAITING_KIT_BUILD (the 12 slots are frozen; never rebuilt)")
    plan["status"] = "KIT_READY"
    plan["status_note"] = (
        "Kit built and digitally validated (see kit_manifest.json and "
        "PILOT_KIT_BUILD.md). The three playback buffers and the "
        "interference copy exist under pilot_pack/. Recording may begin "
        "when the owner starts; slots are unchanged from "
        "FRESH_PILOT_PLAN section 5.")
    def entry(b):
        return {"path": b["path"], "sha256": b["sha256"],
                "duration_s": b["duration_s"]}
    plan["buffer_files"] = {
        "BUF-A": entry(kit["buffers"]["BUF-A"]),
        "BUF-B1": entry(kit["buffers"]["BUF-B1"]),
        "BUF-BMID": entry(kit["buffers"]["BUF-BMID"]),
        "INTERFERENCE": {
            "path": kit["interference"]["path"],
            "sha256": kit["interference"]["sha256"],
            "duration_s": kit["interference"]["duration_s"],
            "source_path": kit["interference"]["source_path"],
            "note": kit["interference"]["role"],
        },
    }
    # preserve the hand-authored key order of take_plan.json (a sorted
    # rewrite would churn the frozen slots' diff for no information)
    with open(take_plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False, sort_keys=False)


def validate_kit(kit_path: Path, take_plan_path: Path) -> dict:
    """Full kit validation (FRESH_PILOT_PLAN kit-build gate): files exist,
    hashes match the manifests, digital GT/QC/trim/leakage self-checks
    passed, every take slot resolves to an existing playback asset, the
    interference asset resolves, and expected GT values are correct."""
    kit = common.load_json(kit_path)
    plan = common.load_json(take_plan_path)
    failures = []

    def check(ok, msg):
        if not ok:
            failures.append(msg)
        return bool(ok)

    check(kit.get("status") == "KIT_READY", "kit status is not KIT_READY")
    check(plan.get("status") == "KIT_READY",
          "take_plan status is not KIT_READY")

    for buffer_id, row in kit["buffers"].items():
        path = Path(row["path"])
        check(path.exists(), f"{buffer_id}: file missing ({path})")
        if path.exists():
            check(common.sha256_file(path) == row["sha256"],
                  f"{buffer_id}: hash mismatch vs kit manifest")
            check(row["duration_s"] == 63.5,
                  f"{buffer_id}: duration {row['duration_s']} != 63.5 s")
            check(path.name.encode("utf-8").decode("utf-8") == path.name,
                  f"{buffer_id}: unicode path round-trip failed")
        sc = row["selfcheck"]
        check(sc["gt_status"] == "GT_VALID",
              f"{buffer_id}: self-check GT not valid")
        check(sc["n_marker_candidates"] == 2,
              f"{buffer_id}: dual-marker count rule failed")
        check(abs(sc["scale_error"])
              <= mp.PROVISIONAL_MAX_CLOCK_SCALE_ERROR,
              f"{buffer_id}: scale error beyond tolerance")
        check(sc["mapping_disagreement_s"] <= mp.MAX_MAPPING_DISAGREEMENT_S,
              f"{buffer_id}: mapping disagreement beyond gate")
        check(not sc["marker_leakage_check"]["leakage"],
              f"{buffer_id}: marker leakage after simulated trim")
        check(sc["payload_placement"]["payload_equals_reference_slice"],
              f"{buffer_id}: payload != reference slice")
        expected_gt = SELF_CHECK_LEAD_S - mp.PRE_TRIM_MARGIN_S
        check(abs(sc["gt_offset_s_payload_in_trimmed"] - expected_gt)
              < 1e-9, f"{buffer_id}: unexpected payload GT")
        expected_ref_gt = (expected_gt - BMID_START_S
                           if buffer_id == "BUF-BMID" else expected_gt)
        check(abs(sc["intended_reference_gt_s"] - expected_ref_gt) < 1e-9,
              f"{buffer_id}: unexpected reference GT")
        # take_plan carries the same identity as the kit manifest
        tp = plan["buffer_files"][buffer_id]
        check(tp["sha256"] == row["sha256"],
              f"{buffer_id}: hash mismatch kit manifest vs take_plan")

    valid_ids = set(kit["buffers"])
    for take in plan["takes"]:
        bid = take["buffer"]
        check(bid in valid_ids, f"{take['take']}: unknown buffer {bid}")
        if bid in valid_ids:
            check(Path(kit["buffers"][bid]["path"]).exists(),
                  f"{take['take']}: buffer {bid} file missing")

    itf = kit["interference"]
    itf_path = Path(itf["path"])
    check(itf_path.exists(), f"INTERFERENCE: file missing ({itf_path})")
    if itf_path.exists():
        check(common.sha256_file(itf_path) == itf["sha256"],
              "INTERFERENCE: hash mismatch")
    check(itf["sha256"] != kit["buffers"]["BUF-A"]["payload_source"]
          ["source_sha256"], "INTERFERENCE must differ from song A source")
    check(itf["sha256"] != kit["buffers"]["BUF-B1"]["payload_source"]
          ["source_sha256"], "INTERFERENCE must differ from song B source")
    check(plan["buffer_files"]["INTERFERENCE"]["sha256"] == itf["sha256"],
          "INTERFERENCE hash mismatch kit manifest vs take_plan")

    for ref_id, row in kit["references"].items():
        check(Path(row["path"]).exists(), f"{ref_id}: file missing")
        if Path(row["path"]).exists():
            check(common.sha256_file(Path(row["path"])) == row["sha256"],
                  f"{ref_id}: hash mismatch")

    return {"ok": not failures, "failures": failures,
            "kit_manifest": str(kit_path), "take_plan": str(take_plan_path)}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="render + validate the fresh-pilot playback kit "
                    "(PILOT_ONLY; source library stays read-only)")
    ap.add_argument("--selection", default=str(DEFAULT_SELECTION))
    ap.add_argument("--skip-take-plan", action="store_true",
                    help="render + validate only; do not update take_plan")
    ap.add_argument("--validate-only", action="store_true",
                    help="re-validate an existing kit (no rendering)")
    args = ap.parse_args(argv)

    if args.validate_only:
        result = validate_kit(PILOT_PACK / "kit_manifest.json",
                              PILOT_PACK / "take_plan.json")
        print(json.dumps(result, indent=1))
        if not result["ok"]:
            raise SystemExit(1)
        print("[kit] VALIDATION OK")
        return result

    print(f"[kit] selection record: {args.selection}")
    kit = build_kit(Path(args.selection),
                    PILOT_PACK / "buffers", PILOT_PACK / "local" / "references",
                    PILOT_PACK / "local" / "selfcheck")
    kit_path = PILOT_PACK / "kit_manifest.json"
    common.save_json(kit_path, kit)
    print(f"[kit] manifest -> {kit_path}")

    if not args.skip_take_plan:
        update_take_plan(kit, PILOT_PACK / "take_plan.json")
        print("[kit] take_plan.json -> KIT_READY")
    return kit


if __name__ == "__main__":
    main()
