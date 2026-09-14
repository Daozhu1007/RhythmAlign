"""Final benchmark source selection: audit, classify, freeze.

Authority: docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md (FROZEN
before final data collection). This module performs the performance-blind
source audit for the final acquisition kit. Selection uses SOURCE PROPERTIES
ONLY (decode integrity, duration, edge silence, chroma recurrence structure,
chroma texture). NO COMPARATOR (RhythmAlign, GCC-PHAT, Panako, NCC,
Kdenlive) IS EVER RUN HERE, and the rule is never revised from benchmark
outcomes.

Read-only inputs:
  - the owner's fresh-candidate folder (positional --root, may repeat);
  - the four previously declared FINAL_ELIGIBLE survivors (hash-verified
    against the committed FINAL_SOURCE_GAP.md record);
  - the frozen exclusion ledger (EXCLUSIONS in pilot_source_selection.py)
    plus documented ledger extensions produced by THIS audit.

Outputs:
  - experiments/applied_system/final_pack/final_source_freeze.json
    (canonical, hash-stamped, COMMITTED: identities, hashes, structural
    scores, selection rule, provenance; selected sources carry full local
    paths so the kit build can re-run on this machine — the same practice
    as the pilot freeze);
  - experiments/applied_system/final_pack/local/final_audit.json
    (LOCAL ONLY, gitignored: complete file inventory with private paths).

Selection rule FINAL-SELECT-V1 (declared here BEFORE the analysis was run;
do not edit after the freeze record exists):

  Screening (per unique identity):
    E1. exclusion: any frozen-ledger identity match over path, filename,
        ID3 title/artist/album (case-insensitive substring), any exact
        SHA-256 match with a historically known file, or any of the
        documented alias resolutions below (Chinese/Japanese/English
        translation equivalents and production-use evidence; no weak
        substring matches);
    E2. duplicates collapsed by SHA-256;
    E3. decodable (libsndfile full decode), duration >= 60 s (buffer
        payload length), leading AND trailing silence <= 5 s at -60 dBFS;
    E4. identity uncertain after E1-E3 -> IDENTITY_REVIEW_NEEDED and NOT
        selectable.

  Selection (over the eligible pool, deterministic incl. tie-breaks):
    R1. the 3 eligible identities with the highest R_long (tie: ascending
        SHA-256) are selected as references and marked
        REPETITIVE_STRESS_SOURCE (satisfies the frozen ">=3 deliberately
        repetitive" requirement; rank-based, no tuned threshold);
    R2. the remaining 7 reference slots are filled in ascending SHA-256
        order;
    R3. S01-S10 = the 10 selected references sorted by ascending SHA-256
        (slot numbering independent of structure/performance);
    R4. INTERFERENCE = the eligible non-reference identity with the
        maximum mean chroma-texture cosine distance to the 10 selected
        references (generalizes the frozen pilot interference rule; tie:
        ascending SHA-256). It is never a reference in any pairing.
    R5. If the pool has exactly 11 identities, R2 leaves zero candidates
        and R4 has exactly one candidate; the rule stays deterministic.

  Structural metric: the established source-only long-lag chroma
  recurrence R_long (pilot machinery, unchanged). It is a deterministic
  selection heuristic, NOT a universal difficulty metric.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
import scipy
import soundfile as sf

from . import pilot_source_selection as pss
from .runners import common

ROOT = Path(__file__).resolve().parents[2]
APPLIED_DIR = Path(__file__).resolve().parent
FINAL_PACK = APPLIED_DIR / "final_pack"

PAYLOAD_DURATION_S = pss.PAYLOAD_DURATION_S          # 60.0 s
MAX_EDGE_SILENCE_S = pss.MAX_EDGE_SILENCE_S          # 5.0 s
MIN_DURATION_S = PAYLOAD_DURATION_S

# ---------------------------------------------------------------------------
# frozen exclusion ledger provenance
# ---------------------------------------------------------------------------

LEDGER_SHA256 = "ab7572e352421e433b3ed6aff009fdc437d3c57bca73e257c626fcaef5385b9e"

# The committed ledger (pilot_source_selection.EXCLUSIONS + the three pilot
# identities) is applied unchanged. The rows below are extensions of its
# APPLICATION discovered by this audit (translation aliases and production-use
# evidence), each with repository-verifiable evidence. They are recorded in
# the freeze; they do not amend any frozen protocol rule.

PILOT_EXCLUSIONS = [
    {"identity": "Bloody Trail (Hommarju)",
     "patterns": ["bloody trail"],
     "evidence": "fresh acoustic pilot Song A "
                 "(experiments/applied_system/pilot_pack/source_selection.json)"},
    {"identity": "スティールユー / Steel You (Omoi)",
     "patterns": ["スティールユー", "steel you"],
     "evidence": "fresh acoustic pilot Song B "
                 "(experiments/applied_system/pilot_pack/source_selection.json)"},
    {"identity": "Divide et impera (BlackY a.k.a. WAiKURO survive)",
     "patterns": ["divide et impera"],
     "evidence": "fresh acoustic pilot interference source "
                 "(experiments/applied_system/pilot_pack/source_selection.json)"},
]

LEDGER_EXTENSIONS = [
    {"candidate_identity": "さよならプリンセス (Sayonara Princess)",
     "excluded_identity": "再见公主",
     "classification": "PERMANENTLY_EXCLUDED_HISTORICAL",
     "evidence": [
         "D:\\Daozh\\Videos\\舞萌手元\\已发\\再见公主\\再见公主.jpg is the "
         "owner's maimai DX CN result screen and displays the song title "
         "さよならプリンセス (MASTER, SSS+) — 再见公主 is the owner's "
         "Chinese name for the same song",
         "the same folder holds 再见公主_synced.mp4 + _synced_1.mp4 "
         "(production RhythmAlign outputs; the RA-1.2B corpus-pair "
         "confirmation convention)",
         "再见公主 is a named identity in the frozen exclusion ledger "
         "(RA-1.2B dev corpus discovery)",
     ]},
    {"candidate_identity": "Scarlet Lance (MASAKI (ZUNATA))",
     "excluded_identity": "红枪",
     "classification": "PERMANENTLY_EXCLUDED_HISTORICAL",
     "evidence": [
         "D:\\Daozh\\Videos\\舞萌手元\\已发\\红枪\\红枪.jpg is the owner's "
         "maimai DX CN result screen and displays the song title Scarlet "
         "Lance (EXPERT, SSS+) — 红枪 is the owner's Chinese name for the "
         "same song",
         "the same folder holds 红枪_synced.mp4 (production RhythmAlign "
         "output)",
         "红枪 is a named identity in the frozen exclusion ledger "
         "(RA-1.2B dev corpus discovery)",
     ]},
    {"candidate_identity": "Sage (かめりあ (Camellia))",
     "excluded_identity": "Sage (production use)",
     "classification": "PERMANENTLY_EXCLUDED_HISTORICAL",
     "evidence": [
         "D:\\Daozh\\Videos\\舞萌手元\\不太想发的\\Sage\\ holds Sage_synced."
         "mp4 + Sage_synced_2.mp4 — outputs produced by production "
         "RhythmAlign (the RA-1.2B corpus-pair confirmation convention), "
         "i.e. the song was alignment-processed before the final freeze",
     ]},
]

# Alias rows that only re-label a file ALREADY excluded by the committed
# ledger (kept for the audit record; no new exclusion power).
ALIAS_NOTES = [
    {"candidate_identity": "ゼロトーキング (はるまきごはん)",
     "excluded_identity": "零对话",
     "classification": "PERMANENTLY_EXCLUDED_HISTORICAL",
     "evidence": [
         "the historical RA-1.2A failure-case file "
         "D:\\Daozh\\Videos\\舞萌手元\\13.2\\零对话\\track.mp3 (RA-1.2B dev "
         "corpus lingduihua_132; ledger identity 零对话) carries ID3 TIT2 "
         "ゼロトーキング / TPE1 はるまきごはん / TALB niconico＆ボーカロイド, "
         "identical to the fresh candidate's tags",
         "the same historical folder holds 零对话_synced_after.mp4 "
         "(production RhythmAlign output)",
     ]},
    {"candidate_identity": "スティールユー (Omoi)",
     "excluded_identity": "pilot Song B",
     "classification": "PERMANENTLY_EXCLUDED_PILOT",
     "evidence": [
         "the fresh file's ID3 tags and identity equal the frozen pilot "
         "source (pilot_pack/source_selection.json song_b)",
     ]},
]

# Video-folder alias map established by this audit from the owner's own
# result-screen thumbnails (documentation of the contamination boundary;
# none of these folders carries any RhythmAlign output, so none of these
# identities is excluded).
VIDEO_ALIAS_MAP_NOTES = (
    "Result-screen thumbnails (read-only) mapped every video-project folder "
    "to its song: 13.1/animal=アニマル, 13.1/忒拉忒拉=てらてら, 13.1/转生苹果="
    "転生林檎, 13.1/三小只=ホシシズク, 不太想发的/墓守=躯樹の墓守, 不太想发的/"
    "红世终孤独=World's end loneliness, 13.1/爱包=愛包ダンスホール, 13.1/甜食控"
    "=シュガーホリック, 不太想发的/彗星=彗星ハネムーン, 不太想发的/Maxi=Maxi, "
    "13.1/帝国华击团=檄！帝国華撃団(改), 13.2/cpfc=コスモポップファンクラブ, "
    "已发/FF=FLUFFY FLASH. Only steelyou (pilot), 零对话 (ledger), Sage "
    "(production), 再见公主 (ledger), 红枪 (ledger) carry RhythmAlign exposure."
)

# ---------------------------------------------------------------------------
# previously declared FINAL_ELIGIBLE survivors (FINAL_SOURCE_GAP.md,
# hash-verified here before they may re-enter the pool)
# ---------------------------------------------------------------------------

SURVIVORS = [
    {"identity": "ARROW",
     "path": r"D:\Daozh\Music\舞萌手元用\ARROW.mp3",
     "sha256": "3e61a90722f1a979a92f294c7256566bc796130deeabb35524f265caa4fe0ee6"},
]

# Survivors of the 2026-09-14 audit that THIS audit's alias review excludes.
SURVIVORS_INVALIDATED = [
    {"identity": "Scarlet Lance", "reason": "ledger alias of 红枪"},
    {"identity": "Sage", "reason": "production RhythmAlign outputs (Sage_synced*.mp4)"},
    {"identity": "さよならプリンセス", "reason": "ledger alias of 再见公主"},
]

# ---------------------------------------------------------------------------
# ID3 metadata (minimal deterministic reader; no external dependency)
# ---------------------------------------------------------------------------


def _id3_decode_text(raw: bytes, enc: int) -> str:
    try:
        if enc == 0:
            return raw.decode("latin-1")
        if enc == 1:
            return raw.decode("utf-16")
        if enc == 2:
            return raw.decode("utf-16-be")
        if enc == 3:
            return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    return raw.decode("latin-1", "replace")


def read_id3(path) -> dict:
    """ID3v2.3/2.4 TIT2/TPE1/TALB (+v1 fallback). Read-only; {} if absent."""
    tags = {}
    try:
        with open(path, "rb") as f:
            head = f.read(10)
            if head[:3] == b"ID3":
                ver = head[3]
                size = ((head[6] & 0x7F) << 21) | ((head[7] & 0x7F) << 14) \
                    | ((head[8] & 0x7F) << 7) | (head[9] & 0x7F)
                body = f.read(size)
                i = 0
                while i + 10 <= len(body):
                    fid = body[i:i + 4]
                    if not fid.strip(b"\x00"):
                        break
                    if ver == 4:
                        fsz = ((body[i + 4] & 0x7F) << 21) \
                            | ((body[i + 5] & 0x7F) << 14) \
                            | ((body[i + 6] & 0x7F) << 7) \
                            | (body[i + 7] & 0x7F)
                    else:
                        fsz = struct.unpack(">I", body[i + 4:i + 8])[0]
                    if fsz <= 0 or i + 10 + fsz > len(body):
                        break
                    data = body[i + 10:i + 10 + fsz]
                    if fid[:1] == b"T" and data:
                        tags[fid.decode("latin-1")] = _id3_decode_text(
                            data[1:], data[0]).strip("\x00")
                    i += 10 + fsz
            else:
                f.seek(-128, 2)
                tail = f.read(128)
                if tail[:3] == b"TAG":
                    tags["TIT2"] = tail[3:33].decode(
                        "latin-1", "replace").strip("\x00 ")
                    tags["TPE1"] = tail[33:63].decode(
                        "latin-1", "replace").strip("\x00 ")
    except OSError:
        pass
    return {k: v for k, v in tags.items() if v}


# ---------------------------------------------------------------------------
# audit machinery
# ---------------------------------------------------------------------------


def scan_root_files(root: Path) -> list:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in pss.AUDIO_EXTENSIONS:
            files.append(p)
    return files


def known_hash_index() -> dict:
    """sha256 -> identity label for every historically known file.

    Sources: the LOCAL pilot inventory when present (full coverage of the
    two pilot media roots) plus the hashes recorded in committed research
    documents (pilot frozen sources, declared survivors). Read-only.
    """
    index = {}
    inv_path = APPLIED_DIR / "pilot_pack" / "local" / "inventory.json"
    if inv_path.exists():
        inv = common.load_json(inv_path)
        for row in inv["candidates"]:
            folded = str(row.get("path", "")).casefold()
            ident = "PRIOR_FILE (unexcluded clean-pool path)"
            for exc in pss.EXCLUSIONS:
                if any(pat in folded for pat in exc["patterns"]):
                    ident = exc["identity"]
                    break
            index[row["sha256"]] = ident
    sel_path = APPLIED_DIR / "pilot_pack" / "source_selection.json"
    if sel_path.exists():
        sel = common.load_json(sel_path)
        for key in ("song_a", "song_b", "interference"):
            row = sel[key]
            index[row["sha256"]] = {
                "song_a": "Bloody Trail (Hommarju)",
                "song_b": "スティールユー / Steel You (Omoi)",
                "interference": "Divide et impera (BlackY a.k.a. WAiKURO "
                                "survive)"}[key]
    for s in SURVIVORS:
        index[s["sha256"]] = s["identity"]
    return index


def ledger_patterns() -> list:
    pats = []
    for exc in pss.EXCLUSIONS:
        pats.append((exc["identity"], exc["patterns"]))
    for exc in PILOT_EXCLUSIONS:
        pats.append((exc["identity"], exc["patterns"]))
    return pats


def match_ledger(text_fields: list) -> list:
    folded = [t.casefold() for t in text_fields if t]
    hits = []
    for identity, patterns in ledger_patterns():
        if any(pat in t for t in folded for pat in patterns):
            hits.append(identity)
    return hits


def classify_fresh_file(path: Path, known_hashes: dict) -> dict:
    """Audit one file: hash, probe, decode screen, ID3, classification."""
    row = {
        "path": str(path),
        "basename": path.name,
        "sha256": pss.sha256_file(path),
        "size_bytes": path.stat().st_size,
        "classification": None,
        "evidence": [],
    }
    known = known_hashes.get(row["sha256"])
    if known is not None:
        row["classification"] = (
            "DUPLICATE" if known == "PRIOR_FILE (unexcluded clean-pool path)"
            else "PERMANENTLY_EXCLUDED_HISTORICAL")
        row["evidence"].append(
            f"exact SHA-256 match with a historically known file ({known})")
        if row["classification"] == "DUPLICATE":
            row["excluded_identity"] = known
        return row

    tags = read_id3(path)
    row["id3_title"] = tags.get("TIT2")
    row["id3_artist"] = tags.get("TPE1")
    row["id3_album"] = tags.get("TALB")

    hits = match_ledger([path.name, str(path), tags.get("TIT2"),
                         tags.get("TPE1"), tags.get("TALB")])
    if hits:
        row["classification"] = (
            "PERMANENTLY_EXCLUDED_PILOT"
            if any("pilot" in h.lower() or "Steel You" in h
                   for h in hits) else "PERMANENTLY_EXCLUDED_HISTORICAL")
        row["excluded_identity"] = hits[0]
        row["evidence"].append(
            "frozen-ledger identity match over path/filename/ID3: "
            + "; ".join(sorted(set(hits))))
        return row

    # technical screen on the untouched file
    try:
        info = sf.info(str(path))
        row["container"] = str(info.format)
        row["codec"] = str(info.subtype)
        row["sample_rate"] = int(info.samplerate)
        row["channels"] = int(info.channels)
        row["duration_s"] = round(float(info.duration), 3)
        y, fs = pss.decode_mono(str(path))
    except Exception as exc:                       # decode/analysis failure
        row["classification"] = "TECHNICALLY_UNSUITABLE"
        row["evidence"].append(f"decode failed: {type(exc).__name__}: {exc}")
        return row
    lead, trail = pss.edge_silence(y, fs)
    row["leading_silence_s"] = round(lead, 3)
    row["trailing_silence_s"] = round(trail, 3)
    reasons = []
    if row["duration_s"] < MIN_DURATION_S:
        reasons.append(f"duration {row['duration_s']} s < {MIN_DURATION_S} s")
    if lead > MAX_EDGE_SILENCE_S:
        reasons.append(f"leading silence {lead:.2f} s > {MAX_EDGE_SILENCE_S} s")
    if trail > MAX_EDGE_SILENCE_S:
        reasons.append(f"trailing silence {trail:.2f} s > {MAX_EDGE_SILENCE_S} s")
    if reasons:
        row["classification"] = "TECHNICALLY_UNSUITABLE"
        row["evidence"].append("; ".join(reasons))
        return row

    row["classification"] = "FINAL_ELIGIBLE"
    return row


# ---------------------------------------------------------------------------
# FINAL-SELECT-V1 (declared before analysis; see module docstring)
# ---------------------------------------------------------------------------

SELECTION_RULE_ID = "FINAL-SELECT-V1"


def select_final_sources(pool: list) -> dict:
    """pool: analyzed FINAL_ELIGIBLE rows, each with sha256 + structural.
    Deterministic; performance-blind; ties broken by ascending SHA-256."""
    if len(pool) < 11:
        return {"ok": False, "pool_size": len(pool),
                "missing": 11 - len(pool)}
    by_hash = sorted(pool, key=lambda r: r["sha256"])
    stress = sorted(pool, key=lambda r: (-r["r_long"], r["sha256"]))[:3]
    stress_hashes = {r["sha256"] for r in stress}
    rest = [r for r in by_hash if r["sha256"] not in stress_hashes]
    refs = sorted(stress + rest[:7], key=lambda r: r["sha256"])
    assert len(refs) == 10
    candidates = [r for r in by_hash if r["sha256"] not in
                  {q["sha256"] for q in refs}]
    tex = [r["texture"] for r in refs]
    dists = {r["sha256"]: float(np.mean(
        [1.0 - float(np.dot(r["texture"], t)) for t in tex]))
        for r in candidates}
    if candidates:
        best = max(dists.values())
        interference = min((r for r in candidates
                            if dists[r["sha256"]] == best),
                           key=lambda r: r["sha256"])
    else:
        interference = None
    slots = {}
    for i, r in enumerate(refs, start=1):
        slots[f"S{i:02d}"] = r["sha256"]
    return {"ok": True, "pool_size": len(pool),
            "references": refs, "slots": slots,
            "stress": stress, "interference": interference,
            "interference_texture_distance": dists,
            "unused": [r for r in candidates
                       if interference is None
                       or r["sha256"] != interference["sha256"]]}


# ---------------------------------------------------------------------------
# record emission
# ---------------------------------------------------------------------------


def canonical_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def survivor_rows() -> list:
    rows = []
    for s in SURVIVORS:
        p = Path(s["path"])
        ok = p.exists() and pss.sha256_file(p) == s["sha256"]
        try:
            info = sf.info(str(p))
            tech = {"sample_rate": int(info.samplerate),
                    "channels": int(info.channels),
                    "duration_s": round(float(info.duration), 3)}
        except Exception:
            tech = None
        rows.append({"identity": s["identity"], "path": s["path"],
                     "sha256": s["sha256"], "present": p.exists(),
                     "hash_unchanged": bool(ok), "technical": tech})
    return rows


def eligible_row_from_survivor(s: dict) -> dict:
    """Build a pool row for a hash-verified declared survivor (task rule:
    verified survivors re-enter the combined eligible pool)."""
    p = Path(s["path"])
    tags = read_id3(p)
    row = {
        "path": str(p), "basename": p.name,
        "sha256": s["sha256"], "size_bytes": p.stat().st_size,
        "classification": "FINAL_ELIGIBLE",
        "evidence": ["previously declared FINAL_ELIGIBLE "
                     "(FINAL_SOURCE_GAP.md); hash unchanged; no ledger or "
                     "alias match in this audit"],
        "id3_title": tags.get("TIT2"), "id3_artist": tags.get("TPE1"),
        "id3_album": tags.get("TALB"),
    }
    info = sf.info(str(p))
    row["container"] = str(info.format)
    row["codec"] = str(info.subtype)
    row["sample_rate"] = int(info.samplerate)
    row["channels"] = int(info.channels)
    row["duration_s"] = round(float(info.duration), 3)
    y, fs = pss.decode_mono(str(p))
    lead, trail = pss.edge_silence(y, fs)
    row["leading_silence_s"] = round(lead, 3)
    row["trailing_silence_s"] = round(trail, 3)
    assert row["duration_s"] >= MIN_DURATION_S, "survivor below duration gate"
    assert lead <= MAX_EDGE_SILENCE_S and trail <= MAX_EDGE_SILENCE_S
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="final source audit + freeze (performance-blind; NO "
                    "comparator is run)")
    ap.add_argument("--roots", nargs="+", required=True,
                    help="fresh-candidate folders (read-only)")
    ap.add_argument("--out", default=str(FINAL_PACK / "final_source_freeze.json"))
    ap.add_argument("--local-dir", default=str(FINAL_PACK / "local"))
    args = ap.parse_args(argv)

    roots = [Path(r) for r in args.roots]
    known_hashes = known_hash_index()
    print(f"[final-selection] scanning {len(roots)} fresh root(s) (read-only)")
    rows = []
    seen_paths = set()
    for root in roots:
        for p in scan_root_files(root):
            if str(p) in seen_paths:
                continue
            seen_paths.add(str(p))
            print(f"  auditing {p.name} …")
            rows.append(classify_fresh_file(p, known_hashes))

    # duplicate collapse within the fresh folder itself
    by_hash = {}
    for r in rows:
        if r["sha256"] in by_hash:
            r["classification"] = "DUPLICATE"
            r["evidence"].append(
                f"exact duplicate of {by_hash[r['sha256']]['basename']}")
        else:
            by_hash[r["sha256"]] = r

    print("[final-selection] verifying previously declared survivors")
    survivors = survivor_rows()
    # verified survivors re-enter the combined eligible pool (their ledger
    # and alias status is re-checked below together with the fresh rows)
    for s in survivors:
        if not (s["present"] and s["hash_unchanged"]):
            raise RuntimeError(
                f"declared survivor {s['identity']} is missing or its hash "
                "changed — it cannot re-enter the pool")
        row = eligible_row_from_survivor(s)
        hits = match_ledger([row["basename"], row["path"], row["id3_title"],
                             row["id3_artist"], row["id3_album"]])
        if hits:
            row["classification"] = "PERMANENTLY_EXCLUDED_HISTORICAL"
            row["evidence"].append(
                "frozen-ledger identity match: " + "; ".join(sorted(set(hits))))
        rows.append(row)

    eligible = [r for r in rows if r["classification"] == "FINAL_ELIGIBLE"]
    eligible.sort(key=lambda r: r["sha256"])
    print(f"[final-selection] eligible pool: {len(eligible)} identities")

    # structural analysis of the eligible pool only (source-only; no
    # comparator involvement)
    for r in eligible:
        y, fs = pss.decode_mono(r["path"])
        scores = pss.structural_scores(y, fs)
        r["r_long"] = round(scores["r_long"], 5)
        r["r_short"] = round(scores["r_short"], 5)
        r["peak_lag_s"] = round(scores["peak_lag_s"], 2)
        r["texture"] = scores["texture"]
        print(f"  {r['basename']}: R_long={r['r_long']} "
              f"peak_lag={r['peak_lag_s']}s")

    sel = select_final_sources(eligible)
    if not sel["ok"]:
        record = {
            "status": "FINAL_SOURCE_POOL_INSUFFICIENT",
            "eligible_pool": [{k: v for k, v in r.items()
                               if k != "texture"} for r in eligible],
            "pool_size": sel["pool_size"], "missing": sel["missing"],
        }
    else:
        refs = sel["references"]
        slot_rows = {}
        for i, r in enumerate(refs, start=1):
            slot = f"S{i:02d}"
            slot_rows[slot] = {
                "slot": slot,
                "identity": r["id3_title"] or r["basename"],
                "artist": r.get("id3_artist"),
                "basename": r["basename"],
                "path": r["path"],
                "sha256": r["sha256"],
                "duration_s": r["duration_s"],
                "codec": r["codec"],
                "sample_rate": r["sample_rate"],
                "channels": r["channels"],
                "r_long": r["r_long"],
                "r_short": r["r_short"],
                "peak_lag_s": r["peak_lag_s"],
                "repetitive_flag": (
                    "REPETITIVE_STRESS_SOURCE"
                    if r in sel["stress"] else "ORDINARY"),
            }
        itf = sel["interference"]
        interference_row = None
        if itf is not None:
            interference_row = {
                "identity": itf["id3_title"] or itf["basename"],
                "artist": itf.get("id3_artist"),
                "basename": itf["basename"],
                "path": itf["path"],
                "sha256": itf["sha256"],
                "duration_s": itf["duration_s"],
                "codec": itf["codec"],
                "sample_rate": itf["sample_rate"],
                "channels": itf["channels"],
                "role": "acoustic interference during final17-final20 only; "
                        "never a reference in any pairing",
            }
        durations = [r["duration_s"] for r in refs]
        record = {
            "status": "FINAL_SOURCES_FROZEN",
            "final_pack": "FINAL_PACK",
            "authority": "docs/research/applied_system/FINAL_BENCHMARK_PROTOCOL.md",
            "no_comparator_run": True,
            "performance_blind": True,
            "selection_rule_id": SELECTION_RULE_ID,
            "exclusion_ledger": {
                "ledger_sha256": LEDGER_SHA256,
                "machinery": "pilot_source_selection.EXCLUSIONS (applied "
                             "unchanged) + pilot identities",
                "extensions_by_this_audit": LEDGER_EXTENSIONS,
                "alias_notes": ALIAS_NOTES,
                "video_alias_map": VIDEO_ALIAS_MAP_NOTES,
            },
            "survivor_reverification": survivors,
            "survivors_invalidated": SURVIVORS_INVALIDATED,
            "fresh_scan": {
                "roots": [str(r) for r in roots],
                "files_audited": len(rows),
                "class_counts": {
                    c: sum(1 for r in rows if r["classification"] == c)
                    for c in sorted({r["classification"] for r in rows})},
                "rows": [{k: v for k, v in r.items() if k != "texture"}
                         for r in rows],
            },
            "eligible_pool": [{k: v for k, v in r.items()
                               if k != "texture"} for r in eligible],
            "selection_rule": {
                "id": SELECTION_RULE_ID,
                "screening": (
                    f"E1 frozen exclusion ledger (path/filename/ID3/alias/"
                    f"hash); E2 duplicates collapsed by SHA-256; E3 full "
                    f"decode, duration >= {MIN_DURATION_S} s, edge silence "
                    f"<= {MAX_EDGE_SILENCE_S} s at -60 dBFS; E4 uncertain "
                    f"identity -> IDENTITY_REVIEW_NEEDED (not selectable)"),
                "R1": "3 highest-R_long eligible identities selected as "
                      "references and marked REPETITIVE_STRESS_SOURCE "
                      "(tie: ascending SHA-256)",
                "R2": "remaining 7 reference slots filled in ascending "
                      "SHA-256 order",
                "R3": "S01-S10 = the 10 selected references sorted by "
                      "ascending SHA-256",
                "R4": "interference = maximum mean chroma-texture cosine "
                      "distance to the 10 references among remaining "
                      "eligible identities (tie: ascending SHA-256)",
                "R5": "pool of exactly 11 leaves no free choice; rule "
                      "stays deterministic",
                "structural_metric": "R_long = mean cosine similarity of "
                                     "2 Hz chroma blocks at lags >= 16 s "
                                     "(pilot machinery, unchanged); a "
                                     "deterministic selection heuristic, "
                                     "NOT a universal difficulty metric",
                "tie_break": "ascending SHA-256",
            },
            "references": slot_rows,
            "interference": interference_row,
            "repetitive_stress_sources": [
                slot_rows[f"S{i:02d}"]["identity"] for i in range(1, 11)
                if slot_rows[f"S{i:02d}"]["repetitive_flag"]
                == "REPETITIVE_STRESS_SOURCE"],
            "diversity": {
                "duration_range_s": [round(min(durations), 3),
                                     round(max(durations), 3)],
                "r_long_range": [min(r["r_long"] for r in refs),
                                 max(r["r_long"] for r in refs)],
                "unique_artists": len({(r.get("artist") or "")
                                       for r in slot_rows.values()}),
            },
            "unused_eligible": [r["basename"] for r in sel["unused"]],
            "environment": {
                "python": sys.version.split()[0],
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "soundfile": sf.__version__,
                "libsndfile": sf.__libsndfile_version__,
            },
        }

    body = json.loads(canonical_bytes(record).decode("utf-8"))
    frozen = {"freeze_sha256": hashlib.sha256(
        canonical_bytes(body)).hexdigest(), "body": body}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(frozen, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"[final-selection] freeze record -> {out}")

    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "final_audit.json").write_text(
        json.dumps({"local_only": "NEVER_COMMIT_PERSONAL_MEDIA_INVENTORY",
                    "rows": rows, "survivors": survivors},
                   ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    print(f"[final-selection] LOCAL-ONLY audit -> "
          f"{local_dir / 'final_audit.json'} (never committed)")

    if record["status"] != "FINAL_SOURCES_FROZEN":
        print(f"[final-selection] {record['status']}: "
              f"{record['pool_size']} eligible, "
              f"{record['missing']} more needed")
        return record
    for slot in sorted(record["references"]):
        r = record["references"][slot]
        print(f"  {slot}: {r['identity']} [{r['repetitive_flag']}] "
              f"R_long={r['r_long']}")
    print(f"  INTERFERENCE: {record['interference']['identity']}")
    return record


if __name__ == "__main__":
    main()
