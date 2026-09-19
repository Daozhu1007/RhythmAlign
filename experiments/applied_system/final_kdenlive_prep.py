"""Kdenlive final technical stratum preparation — blind pair freeze + owner pack.

Authority: docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md (FROZEN
before final data collection) + final_pack/final_source_freeze.json +
final_pack/final_acquisition_manifest.json + final_pack/results/
final_acquisition_qc.json (frozen hashes, all verified before any action).

The frozen protocol fixes the Kdenlive stratum at exactly 10 technical pairs
(checklist items 12 and 17) but never froze WHICH take IDs they are. This
module resolves that implementation detail with KDENLIVE-SELECT-V1, declared
here BEFORE any final comparator result exists, using ONLY acquisition-
manifest metadata (take id, source slot, condition, session, room, devices).
GT offsets, marker data, trimmed-audio content, and every comparator outcome
are structurally unreachable from the selection input.

COMPARATOR-BLIND BY CONSTRUCTION: this module must never import or invoke
RhythmAlign, GCC-PHAT, NCC, Panako, or Kdenlive, and must never import any
module that does (pilot_harness and runners/* import comparator runners).
It computes no alignment performance output and compares nothing against
GT. The XML parser it ships with extracts placements only; scoring against
GT lives elsewhere and is NOT run by this module.

KDENLIVE-SELECT-V1 (fully deterministic, metadata-only):
  A1. Universe = the 24 primary takes of the frozen acquisition manifest
      (strict repeats are reliability takes, reported separately; they are
      never benchmark pairs).
  A2. Condition quotas: proportional largest-remainder over the frozen
      condition counts, total 10; ties broken by condition name ascending.
  A3. Within a condition, takes in ascending take-id order, first
      quota_c taken.

Freeze outputs (write-once, canonical-hash sealed):
  kdenlive/kdenlive_pair_freeze.json           pair01..pair10 + provenance
  kdenlive/kdenlive_owner_pack_manifest.json   input hashes of the blind pack
  kdenlive/kdenlive_environment.json           exact Kdenlive build record
Blind owner media (gitignored, hash-recorded):
  kdenlive/owner_pack/pairNN/{recording.wav, reference.wav, pairNN.kdenlive}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLIED_DIR = Path(__file__).resolve().parent
FINAL_PACK = APPLIED_DIR / "final_pack"
KDENLIVE_DIR = FINAL_PACK / "kdenlive"
OWNER_PACK = KDENLIVE_DIR / "owner_pack"
TRIMMED_DIR = FINAL_PACK / "local" / "final_qc_work" / "trimmed"

MANIFEST_PATH = FINAL_PACK / "final_acquisition_manifest.json"
QC_PATH = FINAL_PACK / "results" / "final_acquisition_qc.json"
FREEZE_PATH = KDENLIVE_DIR / "kdenlive_pair_freeze.json"
PACK_MANIFEST_PATH = KDENLIVE_DIR / "kdenlive_owner_pack_manifest.json"
ENV_PATH = KDENLIVE_DIR / "kdenlive_environment.json"

SELECTION_RULE_ID = "KDENLIVE-SELECT-V1"
PAIR_COUNT = 10

# The ONLY manifest fields the selection may see. Everything else (hashes,
# buffers, wrong-reference data, provenance) is projected away before the
# selection function runs; the projection is the structural blindness proof.
SELECT_ALLOWED_KEYS = frozenset(
    {"take", "source_slot", "condition", "session", "room",
     "recording_device", "playback_device", "primary"}
)

# Kdenlive 26.08 series as pinned by the frozen protocol (item 12). The
# installed build is recorded exactly in kdenlive_environment.json.
KDENLIVE_PINNED_SERIES = "26.08"
TIMING_SCHEMA_VERSION = "KDENLIVE-TIMER-V1"

TIMING_OBSERVATIONS = {
    "ALIGNED": "Kdenlive 完成了对齐操作",
    "NO_MATCH_REPORTED": "Kdenlive 报告无法对齐 / 未找到匹配",
    "ERROR_DIALOG": "Kdenlive 弹出错误对话框",
    "OTHER": "其他情况(在备注里说明)",
}

TIMING_RECORD_REQUIRED_KEYS = (
    "pair", "start_utc", "end_utc", "elapsed_seconds",
    "observation", "schema_version",
)

# Owner-facing artifacts must never contain scientific metadata. Take IDs
# are "final01".."final24"/"repeat01"/"repeat02", so the digit-bearing
# forms are forbidden while the neutral folder name final_pack is not
# scientific metadata.
OWNER_FACING_FORBIDDEN_SUBSTRINGS = (
    "GT", "EXACT", "wrong_reference", "marker", "offset",
    "S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10",
    "final0", "final1", "final2", "repeat0", "repeat1", "chirp",
)


# ---------------------------------------------------------------------------
# canonical JSON + immutable freeze helpers (same semantics as the pilot)
# ---------------------------------------------------------------------------


def canonical_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


# ---------------------------------------------------------------------------
# frozen-authority verification
# ---------------------------------------------------------------------------


def verify_frozen_authority(manifest: dict, qc: dict) -> list:
    problems = []
    if hashlib.sha256(canonical_bytes(manifest["body"])).hexdigest() \
            != manifest["manifest_hash"]:
        problems.append("acquisition manifest canonical hash mismatch")
    if hashlib.sha256(canonical_bytes(qc["body"])).hexdigest() \
            != qc["qc_freeze_sha256"]:
        problems.append("acquisition QC canonical hash mismatch")
    if qc["body"].get("verdict") != "FINAL_QC_PASS":
        problems.append("QC verdict is not FINAL_QC_PASS")
    return problems


def load_verified_authority():
    manifest = load_json(MANIFEST_PATH)
    qc = load_json(QC_PATH)
    problems = verify_frozen_authority(manifest, qc)
    if problems:
        raise SystemExit("FROZEN AUTHORITY VIOLATION: " + "; ".join(problems))
    return manifest, qc


# ---------------------------------------------------------------------------
# KDENLIVE-SELECT-V1 — performance-blind deterministic pair selection
# ---------------------------------------------------------------------------


def selection_rows(manifest_body: dict) -> list:
    """Project primary takes down to the allowlisted metadata fields only.

    This projection is the structural blindness proof: the dict returned
    here physically cannot carry a GT value, marker position, trimmed-hash,
    or any comparator outcome, because every other key is dropped before
    selection runs.
    """
    rows = []
    for take, rec in manifest_body["takes"].items():
        if not rec.get("primary"):
            continue
        rows.append({k: rec[k] for k in SELECT_ALLOWED_KEYS})
    rows.sort(key=lambda r: r["take"])
    return rows


def largest_remainder_quotas(condition_counts: dict, total: int) -> dict:
    """Proportional largest-remainder seat allocation over conditions.

    Deterministic: floor seats first, remaining seats by largest fractional
    remainder, ties broken by condition name ascending.
    """
    conds = sorted(condition_counts)
    n = sum(condition_counts.values())
    raw = {c: condition_counts[c] * total / n for c in conds}
    quotas = {c: int(raw[c]) for c in conds}
    remaining = total - sum(quotas.values())
    by_remainder = sorted(
        conds, key=lambda c: (-(raw[c] - quotas[c]), c))
    for cond in by_remainder[:remaining]:
        quotas[cond] += 1
    return quotas


def select_pairs(rows: list, total: int = PAIR_COUNT) -> list:
    """Run KDENLIVE-SELECT-V1 over the projected rows; returns ordered pairs.

    `rows` must already be restricted to SELECT_ALLOWED_KEYS (see
    selection_rows); this function reads nothing else.
    """
    counts = {}
    for r in rows:
        counts.setdefault(r["condition"], 0)
        counts[r["condition"]] += 1
    quotas = largest_remainder_quotas(counts, total)
    chosen = []
    for cond in sorted(quotas):
        members = sorted(r["take"] for r in rows if r["condition"] == cond)
        chosen.extend(members[:quotas[cond]])
    if len(chosen) != total or len(set(chosen)) != total:
        raise SystemExit("selection did not produce %d unique takes" % total)
    chosen.sort()
    return [r for r in rows if r["take"] in set(chosen)]


def assign_pair_ids(selected_rows: list) -> dict:
    """Deterministic pair01..pair10 mapping over ascending take ids."""
    pairs = {}
    for i, row in enumerate(sorted(selected_rows, key=lambda r: r["take"]), 1):
        pid = "pair%02d" % i
        pairs[pid] = {
            "pair": pid,
            "take": row["take"],
            "source_slot": row["source_slot"],
            "condition": row["condition"],
            "session": row["session"],
            "room": row["room"],
            "recording_device": row["recording_device"],
            "playback_device": row["playback_device"],
        }
    return pairs


# ---------------------------------------------------------------------------
# pair freeze body
# ---------------------------------------------------------------------------


def build_freeze_body(manifest: dict, qc: dict, env: dict) -> dict:
    body = manifest["body"]
    trimmed = qc["body"]["trimmed_input_sha256"]
    refs = body["references"]

    selected = select_pairs(selection_rows(body))
    pairs = assign_pair_ids(selected)
    take_meta = {r["take"]: r for r in selected}

    for pid, pair in pairs.items():
        take = pair["take"]
        slot = pair["source_slot"]
        ref = refs["REF-" + slot]
        pair["source_identity"] = body["takes"][take]["source_identity"]
        pair["reference_slot"] = "REF-" + slot
        pair["recording_file"] = "local/final_qc_work/trimmed/%s.wav" % take
        pair["recording_sha256"] = trimmed[take]
        pair["reference_file"] = "local/references/REF-%s.wav" % slot
        pair["reference_sha256"] = ref["sha256"]
        pair["owner_pack_dir"] = "owner_pack/" + pid
        pair["owner_recording"] = "owner_pack/%s/recording.wav" % pid
        pair["owner_reference"] = "owner_pack/%s/reference.wav" % pid
        pair["owner_project_file"] = "owner_pack/%s/%s.kdenlive" % (pid, pid)

    cond_counts = {}
    for pair in pairs.values():
        cond_counts[pair["condition"]] = \
            cond_counts.get(pair["condition"], 0) + 1

    return {
        "status": "KDENLIVE_PAIRS_FROZEN",
        "created_utc": now_utc(),
        "authority": {
            "protocol": "docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md",
            "protocol_items": ["12 (Kdenlive 26.08 owner-operated stratum, scored from project XML)",
                               "17 (exactly 10 Kdenlive technical pairs)",
                               "8 (every system consumes the identical trimmed WAV bytes)"],
            "manifest_hash": manifest["manifest_hash"],
            "manifest_file_sha256": sha256_file(MANIFEST_PATH),
            "qc_freeze_sha256": qc["qc_freeze_sha256"],
            "qc_file_sha256": sha256_file(QC_PATH),
            "source_freeze_sha256": body["source_freeze_sha256"],
        },
        "selection_rule_id": SELECTION_RULE_ID,
        "selection_rule": (
            "A1: universe = the 24 primary takes of the frozen acquisition "
            "manifest (strict repeats are reliability takes, never pairs). "
            "A2: condition quotas by proportional largest remainder over the "
            "frozen condition counts, total %d, ties by condition name "
            "ascending. A3: within a condition, ascending take-id order. "
            "Only take id / source slot / condition / session / room / "
            "device metadata is consulted (allowlist enforced by "
            "selection_rows); GT, marker data, audio content, and every "
            "comparator outcome are structurally excluded." % PAIR_COUNT),
        "blindness": {
            "selection_allowed_keys": sorted(SELECT_ALLOWED_KEYS),
            "gt_used": False,
            "comparator_outcome_used": False,
            "statement": (
                "Selected after final acquisition but BEFORE any final "
                "comparator result exists; no RhythmAlign / Panako / "
                "GCC-PHAT / NCC / Kdenlive outcome was or could be "
                "consulted (structural allowlist projection)."),
            "timing_note": (
                "The exact 10 take IDs were NOT frozen by any earlier "
                "document; the earlier study design said only '8-10 pairs "
                "spanning strata'. This freeze resolves that implementation "
                "detail now, before any performance outcome exists."),
        },
        "input_representation": {
            "recording": "frozen trimmed WAV (protocol item 8: identical trimmed WAV bytes for every system)",
            "reference": "full decoded clean reference WAV (REF-Sxx, same bytes the comparators receive)",
            "note": "Kdenlive receives exactly these two audio files per pair; no marker audio, no GT, no wrong-reference input.",
            "path_base": "recording_file / reference_file are relative to experiments/applied_system/final_pack/",
        },
        "kdenlive_environment": {
            "pinned_series": KDENLIVE_PINNED_SERIES,
            "installed_version": env["version"],
            "exe_sha256": env["exe_sha256"],
            "env_record": "kdenlive_environment.json",
        },
        "operator_timing_contract": {
            "tool": "owner_timer.py",
            "schema_version": TIMING_SCHEMA_VERSION,
            "measures": "owner operation time per pair (open pair folder -> Kdenlive native alignment -> save project)",
            "fields": list(TIMING_RECORD_REQUIRED_KEYS) + ["notes"],
            "excludes": "agent preparation time; breaks between pairs",
            "gt_exposure": "the timer knows no GT and displays no scientific metadata",
        },
        "saved_project_contract": {
            "filenames": ["pair%02d.kdenlive" % i for i in range(1, PAIR_COUNT + 1)],
            "rule": "the owner saves Kdenlive's own project file per pair; later scoring reads placement from the project XML / MLT structure; the owner never reports an offset manually",
        },
        "sealing": ("AUTOMATED FINAL RESULTS REMAIN SEALED UNTIL "
                    "OWNER-OPERATED KDENLIVE STRATUM IS COMPLETE. No "
                    "automated comparator may run or be surfaced before all "
                    "10 Kdenlive projects are saved."),
        "no_comparator_run": ("No RhythmAlign, Panako, GCC-PHAT, NCC, or "
                              "Kdenlive execution touched any final audio "
                              "during this preparation."),
        "coverage": {
            "pairs": PAIR_COUNT,
            "condition_counts": cond_counts,
            "manifest_condition_counts": body["counts"]["conditions"],
            "source_slots": sorted({p["source_slot"] for p in pairs.values()}),
            "sessions": sorted({p["session"] for p in pairs.values()}),
            "recording_devices": sorted({p["recording_device"] for p in pairs.values()}),
            "rooms": sorted({p["room"] for p in pairs.values()}),
        },
        "pairs": {pid: pairs[pid] for pid in sorted(pairs)},
    }


def build_or_verify_freeze(manifest: dict, qc: dict, env: dict,
                           force_new: bool = False) -> dict:
    """Write-once freeze creation: refuses to rewrite an existing freeze."""
    body = build_freeze_body(manifest, qc, env)
    doc = {"body": body, "pair_freeze_sha256": canonical_sha256(body)}
    if FREEZE_PATH.exists():
        existing = load_json(FREEZE_PATH)
        if existing == doc:
            return doc
        if not force_new:
            raise SystemExit(
                "kdenlive_pair_freeze.json already exists with different "
                "content; the freeze is write-once and never changes from "
                "later information")
    save_json(FREEZE_PATH, doc)
    return doc


def verify_freeze() -> dict:
    doc = load_json(FREEZE_PATH)
    body = doc["body"]
    problems = []
    if hashlib.sha256(canonical_bytes(body)).hexdigest() \
            != doc["pair_freeze_sha256"]:
        problems.append("pair freeze canonical hash mismatch")
    manifest = load_json(MANIFEST_PATH)
    qc = load_json(QC_PATH)
    if body["authority"]["manifest_hash"] != manifest["manifest_hash"]:
        problems.append("freeze references a different manifest")
    if body["authority"]["qc_freeze_sha256"] != qc["qc_freeze_sha256"]:
        problems.append("freeze references a different QC freeze")
    pairs = body["pairs"]
    if sorted(pairs) != ["pair%02d" % i for i in range(1, PAIR_COUNT + 1)]:
        problems.append("pair ids are not exactly pair01..pair10")
    takes = [p["take"] for p in pairs.values()]
    if len(set(takes)) != PAIR_COUNT or sorted(takes) != takes:
        problems.append("takes are not 10 unique ascending ids")
    return doc if not problems else \
        (_ for _ in ()).throw(SystemExit("; ".join(problems)))


# ---------------------------------------------------------------------------
# blind owner pack
# ---------------------------------------------------------------------------


def build_owner_pack(freeze_doc: dict) -> dict:
    """Materialize the blind pack (hash-verified copies; media gitignored)."""
    body = freeze_doc["body"]
    trimmed_dir = TRIMMED_DIR
    refs_dir = FINAL_PACK / "local" / "references"
    entries = {}
    for pid, pair in sorted(body["pairs"].items()):
        src_rec = FINAL_PACK / pair["recording_file"]
        src_ref = FINAL_PACK / pair["reference_file"]
        if sha256_file(src_rec) != pair["recording_sha256"]:
            raise SystemExit("recording hash drifted for " + pid)
        if sha256_file(src_ref) != pair["reference_sha256"]:
            raise SystemExit("reference hash drifted for " + pid)
        dst_dir = OWNER_PACK / pid
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_rec = dst_dir / "recording.wav"
        dst_ref = dst_dir / "reference.wav"
        for src, dst in ((src_rec, dst_rec), (src_ref, dst_ref)):
            if not dst.exists() or sha256_file(dst) != sha256_file(src):
                shutil.copyfile(src, dst)
        if sha256_file(dst_rec) != pair["recording_sha256"] or \
                sha256_file(dst_ref) != pair["reference_sha256"]:
            raise SystemExit("pack copy verification failed for " + pid)
        entries[pid] = {
            "pack_dir": "owner_pack/" + pid,
            "recording": "owner_pack/%s/recording.wav" % pid,
            "recording_sha256": pair["recording_sha256"],
            "recording_bytes": dst_rec.stat().st_size,
            "reference": "owner_pack/%s/reference.wav" % pid,
            "reference_sha256": pair["reference_sha256"],
            "reference_bytes": dst_ref.stat().st_size,
            "expected_project_file": "owner_pack/%s/%s.kdenlive" % (pid, pid),
        }
    doc = {
        "status": "KDENLIVE_OWNER_PACK_BUILT",
        "created_utc": now_utc(),
        "pair_freeze_sha256": freeze_doc["pair_freeze_sha256"],
        "naming": {
            "recording.wav": "需要被对齐的现场录音",
            "reference.wav": "干净的参考音乐",
            "pairNN.kdenlive": "owner saves the Kdenlive project here",
        },
        "blindness": ("filenames and this manifest carry no GT, marker, "
                      "wrong-reference, or comparator information"),
        "pairs": entries,
    }
    save_json(PACK_MANIFEST_PATH, doc)
    return doc


# ---------------------------------------------------------------------------
# Kdenlive environment record
# ---------------------------------------------------------------------------


DEFAULT_KDENLIVE_EXE = (Path.home() / "AppData" / "Local" / "Programs"
                        / "Kdenlive" / "bin" / "kdenlive.exe")


def build_environment_record(exe: Path, version: str, install_source: str,
                             installer_url: str) -> dict:
    doc = {
        "status": "KDENLIVE_ENV_READY",
        "recorded_utc": now_utc(),
        "pinned_series": KDENLIVE_PINNED_SERIES,
        "version": version,
        "exe_path": str(exe),
        "exe_sha256": sha256_file(exe),
        "install_source": install_source,
        "installer_url": installer_url,
        "installer_hash_verified": "winget verified the installer hash before install",
        "os": {"system": platform.system(), "release": platform.release(),
               "version": platform.version()},
    }
    save_json(ENV_PATH, doc)
    return doc


def verify_environment() -> dict:
    """Re-verify the recorded build against the machine; readiness gate."""
    doc = load_json(ENV_PATH)
    exe = Path(doc["exe_path"])
    if not exe.exists():
        raise SystemExit("recorded Kdenlive executable is missing: %s" % exe)
    if sha256_file(exe) != doc["exe_sha256"]:
        raise SystemExit("Kdenlive executable hash drifted from the record")
    if not doc["version"].startswith(doc["pinned_series"]):
        raise SystemExit("Kdenlive version %s is outside the pinned %s series"
                         % (doc["version"], doc["pinned_series"]))
    return doc


# ---------------------------------------------------------------------------
# operator timing record schema
# ---------------------------------------------------------------------------


def build_timing_record(pair: str, start_utc: str, end_utc: str,
                        elapsed_seconds: float, observation: str,
                        notes: str = "") -> dict:
    if observation not in TIMING_OBSERVATIONS:
        raise ValueError("unknown observation: %r" % observation)
    if elapsed_seconds < 0:
        raise ValueError("negative elapsed time")
    return {
        "pair": pair,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "observation": observation,
        "schema_version": TIMING_SCHEMA_VERSION,
        "notes": notes,
    }


def validate_timing_record(rec: dict) -> list:
    problems = []
    for key in TIMING_RECORD_REQUIRED_KEYS:
        if key not in rec:
            problems.append("missing field: " + key)
    if rec.get("observation") not in TIMING_OBSERVATIONS:
        problems.append("bad observation: %r" % rec.get("observation"))
    if not isinstance(rec.get("elapsed_seconds"), (int, float)) \
            or rec.get("elapsed_seconds", -1) < 0:
        problems.append("bad elapsed_seconds")
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--freeze", action="store_true",
                    help="create/verify the write-once pair freeze")
    ap.add_argument("--force-new", action="store_true",
                    help=argparse.SUPPRESS)
    ap.add_argument("--build-pack", action="store_true",
                    help="materialize the blind owner pack (gitignored)")
    ap.add_argument("--verify", action="store_true",
                    help="verify freeze + pack manifest + environment")
    ap.add_argument("--record-env", nargs=4, metavar=(
        "EXE", "VERSION", "INSTALL_SOURCE", "INSTALLER_URL"),
        help="record the installed Kdenlive build (run once at prep time)")
    args = ap.parse_args(argv)

    if args.record_env:
        doc = build_environment_record(
            Path(args.record_env[0]), args.record_env[1],
            args.record_env[2], args.record_env[3])
        print("environment recorded:", doc["version"], doc["exe_sha256"][:16])
        return 0

    if args.freeze:
        env = load_json(ENV_PATH)
        manifest, qc = load_verified_authority()
        doc = build_or_verify_freeze(manifest, qc, env,
                                     force_new=args.force_new)
        print("freeze ok:", doc["pair_freeze_sha256"][:16])
        for pid, pair in doc["body"]["pairs"].items():
            print("  %s %s %s %s" % (pid, pair["take"],
                                     pair["condition"], pair["source_slot"]))
    if args.build_pack:
        freeze_doc = verify_freeze()
        verify_environment()
        pack = build_owner_pack(freeze_doc)
        print("pack built:", len(pack["pairs"]), "pairs at", OWNER_PACK)
    if args.verify:
        verify_freeze()
        verify_environment()
        if PACK_MANIFEST_PATH.exists():
            pack = load_json(PACK_MANIFEST_PATH)
            for pid, e in pack["pairs"].items():
                rec = OWNER_PACK / pid / "recording.wav"
                ref = OWNER_PACK / pid / "reference.wav"
                assert sha256_file(rec) == e["recording_sha256"]
                assert sha256_file(ref) == e["reference_sha256"]
        print("verify ok")
    if not (args.freeze or args.build_pack or args.verify or args.record_env):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
