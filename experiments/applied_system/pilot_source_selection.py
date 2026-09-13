"""Fresh-pilot source selection: deterministic, structure-blind where required.

PILOT_ONLY / NOT_PAPER_EVIDENCE. No recording, no RhythmAlign involvement:
selection is based on SOURCE PROPERTIES ONLY (decode integrity, duration,
edge silence, chroma recurrence structure). The benchmark systems are never
run on candidates, and selection must never be revised after buffer
rendering because of comparator outcomes (FRESH_PILOT_PLAN section 9
anti-cherry-picking rule).

Media roots are READ-ONLY owner libraries: this module only lists, hashes,
and decodes. It never writes, moves, renames, retags, or re-encodes a
source file. All generated material goes to the pilot pack (committed
selection record + a local-only full inventory).

Pre-declared selection rules (frozen BEFORE analysis was run; do not edit
after the selection record exists):

  Screen (eligibility):
    - decodable by libsndfile, native sample rate read cleanly;
    - duration >= 60.0 s (the buffer payload length);
    - leading AND trailing silence <= 5.0 s each (|sample| > 1e-3, -60 dBFS);
    - exact duplicates collapsed by SHA-256 (canonical path kept);
    - historical-exposure exclusion (list below, repo-evidenced).

  Song B (structural-difficulty role): eligible if duration >= 150.0 s
    (BUF-BMID places the payload 90 s in: 90 + 60 must fit). Song B is the
    candidate with the HIGHEST long-lag chroma recurrence R_long.

  Song A (ordinary representative role): among remaining candidates with
    R_long strictly below Song B's, the one whose duration is closest to
    the MEDIAN duration of the full clean pool (tie: ascending SHA-256).
    Duration-ordinariness is deliberately structure-blind apart from the
    B-feasibility clause, which guarantees the plan requirement that song B
    be measurably more repetitive than song A.

  Interference (take 8 background source): among remaining candidates, the
    maximum mean chroma-texture distance to {A, B} (tie: ascending
    SHA-256). It is never a reference; it is never optimized against any
    comparator.

  Structural metric (deterministic; a selection heuristic, NOT a universal
  difficulty measure): mono mixdown @ 48 kHz -> STFT (nperseg 4096,
  hop 1200 -> exactly 40 frames/s, hann) -> magnitude -> log1p(100*|X|) ->
  12-bin pitch-class profile over 65-6000 Hz -> L2-normalize per frame ->
  mean over 20-frame blocks (exactly 2 blocks/s, re-normalized) ->
  cosine self-similarity S. R_long = mean of off-diagonal S over pairs
  with |i-j| >= 32 blocks (16 s). Context only: R_short over 16 <= |i-j|
  < 32 blocks (8-16 s) and peak long-lag mean similarity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[2]
APPLIED_DIR = Path(__file__).resolve().parent
PILOT_PACK = APPLIED_DIR / "pilot_pack"

AUDIO_EXTENSIONS = (".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg",
                    ".opus", ".wma")

ANALYSIS_FS = 48_000
STFT_NPERSEG = 4096
STFT_HOP = 1200                      # 48 kHz / 1200 -> exactly 40 fps
CHROMA_F_LO_HZ = 65.0
CHROMA_F_HI_HZ = 6000.0
BLOCK_FRAMES = 20                    # 40 fps / 20 -> exactly 2 blocks/s
LONG_LAG_BLOCKS = 32                 # 16 s at 2 blocks/s
SHORT_LAG_BLOCKS = 16                # 8 s

PAYLOAD_DURATION_S = 60.0
BMID_START_S = 90.0
B_MIN_DURATION_S = BMID_START_S + PAYLOAD_DURATION_S   # 150.0 s
MAX_EDGE_SILENCE_S = 5.0
SILENCE_AMPLITUDE = 1e-3             # -60 dBFS

# ---------------------------------------------------------------------------
# historical-exposure exclusions (source-disjointness from prior RhythmAlign
# research). Each identity cites its repository evidence. Matching is
# substring/casefold over the full source path. Named identities without a
# current-pool match are kept in the record for completeness.
# ---------------------------------------------------------------------------

EXCLUSIONS = [
    {"identity": "延误列车 (yanwulieche)",
     "patterns": ["延误列车"],
     "provenance": [
         "task directive (this pilot round)",
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list",
         "experiments/ra12d1_temporal_support/reproduce_blocker.py "
         "(tr_yanwulieche reference)",
         "docs/RA-1.2E-V1.2.0-RELEASE.md Astra blocker case",
     ]},
    {"identity": "零对话 (lingduihua)",
     "patterns": ["零对话"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list",
         "docs/RA-1.2E-V1.2.0-RELEASE.md release validation cases",
         "Astra exploratory research (tr_lingduihua video)",
     ]},
    {"identity": "红Lividi",
     "patterns": ["红lividi"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list"]},
    {"identity": "DROPS",
     "patterns": ["drops"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list"]},
    {"identity": "白妄想 / 妄想感伤代偿联盟",
     "patterns": ["白妄想", "妄想感伤代偿联盟"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list"]},
    {"identity": "共感觉",
     "patterns": ["共感觉"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list",
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus note"]},
    {"identity": "分诊",
     "patterns": ["分诊"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list"]},
    {"identity": "萨姆沙",
     "patterns": ["萨姆沙"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list"]},
    {"identity": "90decision",
     "patterns": ["90decision"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list"]},
    {"identity": "QUEEN",
     "patterns": ["queen"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md calibration list"]},
    {"identity": "DanceRobotDance",
     "patterns": ["dancerobotdance"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "白39 / 39",
     "patterns": ["白39", "39.mp3"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "宙天",
     "patterns": ["宙天"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "海底谭 / ウミユリ海底譚 (same song identity)",
     "patterns": ["海底谭", "ウミユリ海底譚"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list (海底谭)",
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus (海底谭 已发)"]},
    {"identity": "Let u dive",
     "patterns": ["let u dive"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "乐意效劳",
     "patterns": ["乐意效劳"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "吃药睡觉",
     "patterns": ["吃药睡觉"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "巴别塔",
     "patterns": ["巴别塔"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "才不是恶魔呢",
     "patterns": ["才不是恶魔呢"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "矛盾心理",
     "patterns": ["矛盾心理"],
     "provenance": [
         "docs/RA-1.2C-CALIBRATION-HARDENING.md holdout list"]},
    {"identity": "INTERNETOVERDOSE",
     "patterns": ["internetoverdose"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "on your mark",
     "patterns": ["on your mark"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "右曲",
     "patterns": ["右曲"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "强风大背头 / 強風オールバック",
     "patterns": ["强风大背头", "強風オールバック"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "心跳不止",
     "patterns": ["心跳不止"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "Arcaea手元 folders (Chelsea/7mai, Code Oblivion, "
                 "One Step Closer)",
     "patterns": ["arcaea"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list "
         "('all Arcaea手元 folders')"]},
    {"identity": "Override / オーバーライド (both candidate tracks)",
     "patterns": ["override", "オーバーライド"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md 已发/Override note"]},
    {"identity": "猫娘打架 (no current-pool file)",
     "patterns": ["猫娘打架"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "红枪 (no current-pool file)",
     "patterns": ["红枪"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "水神1.5 (no current-pool file)",
     "patterns": ["水神"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
    {"identity": "再见公主 (no current-pool file)",
     "patterns": ["再见公主"],
     "provenance": [
         "docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md dev corpus list"]},
]


@dataclass
class Candidate:
    path: str                 # absolute Windows path
    sha256: str
    size_bytes: int
    duration_s: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    bit_rate_bps: int = 0
    leading_silence_s: float = -1.0
    trailing_silence_s: float = -1.0
    r_long: float = 0.0
    r_short: float = 0.0
    peak_lag_s: float = 0.0
    excluded_by: list = field(default_factory=list)
    is_duplicate_of: str = ""     # canonical path this file duplicates
    texture: np.ndarray = None    # mean chroma profile (interference rule)

    def as_row(self):
        return {"path": self.path, "sha256": self.sha256,
                "duration_s": round(self.duration_s, 3),
                "sample_rate": self.sample_rate, "channels": self.channels,
                "bit_rate_bps": self.bit_rate_bps,
                "leading_silence_s": round(self.leading_silence_s, 3),
                "trailing_silence_s": round(self.trailing_silence_s, 3),
                "r_long": round(self.r_long, 5),
                "r_short": round(self.r_short, 5),
                "peak_lag_s": round(self.peak_lag_s, 2),
                "excluded_by": self.excluded_by}


# ---------------------------------------------------------------------------
# scanning (READ-ONLY over the owner library)
# ---------------------------------------------------------------------------


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_roots(roots) -> list:
    """List + hash every audio file under the roots. No writes anywhere."""
    cands = []
    for root in roots:
        root = Path(root)
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
                cands.append(Candidate(
                    path=str(p).replace("/", "\\"),
                    sha256=sha256_file(p), size_bytes=p.stat().st_size))
    return cands


def collapse_duplicates(cands: list) -> list:
    """Keep the lexicographically first path per SHA-256; mark the rest."""
    by_hash = {}
    for c in sorted(cands, key=lambda c: (c.path, c.sha256)):
        if c.sha256 in by_hash:
            c.is_duplicate_of = by_hash[c.sha256].path
        else:
            by_hash[c.sha256] = c
    return cands


def match_exclusions(c: Candidate) -> list:
    folded = c.path.casefold()
    hits = []
    for exc in EXCLUSIONS:
        if any(pat in folded for pat in exc["patterns"]):
            hits.append(exc["identity"])
    return hits


# ---------------------------------------------------------------------------
# audio screening + structural analysis (all read-only)
# ---------------------------------------------------------------------------


def probe_candidate(c: Candidate):
    info = sf.info(c.path)
    c.duration_s = info.duration
    c.sample_rate = int(info.samplerate)
    c.channels = int(info.channels)
    # average bytes/s over duration approximates the encoded bitrate for
    # CBR/VBR mp3 well enough for screening records (not a codec readout).
    c.bit_rate_bps = int(round(c.size_bytes * 8.0 / max(c.duration_s, 1e-9)))


def decode_mono(path: str) -> tuple:
    y, sr = sf.read(path, dtype="float64", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    return np.ascontiguousarray(y), int(sr)


def edge_silence(y: np.ndarray, fs: int,
                 amp: float = SILENCE_AMPLITUDE) -> tuple:
    above = np.flatnonzero(np.abs(y) > amp)
    if len(above) == 0:
        return len(y) / fs, len(y) / fs
    return above[0] / fs, (len(y) - 1 - above[-1]) / fs


def chroma_blocks(y: np.ndarray, fs: int):
    """Deterministic chroma-block features (see module docstring)."""
    if fs != ANALYSIS_FS:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(int(fs), ANALYSIS_FS)
        y = resample_poly(y, ANALYSIS_FS // g, int(fs) // g)
    f, _, Z = signal.stft(y, fs=ANALYSIS_FS, window="hann",
                          nperseg=STFT_NPERSEG, noverlap=STFT_NPERSEG
                          - STFT_HOP, padded=False, boundary=None)
    mag = np.abs(Z)
    with np.errstate(divide="ignore"):
        feat = np.log1p(100.0 * mag)
    bin_hz = np.fft.rfftfreq(STFT_NPERSEG, 1.0 / ANALYSIS_FS)
    band = (bin_hz >= CHROMA_F_LO_HZ) & (bin_hz <= CHROMA_F_HI_HZ)
    with np.errstate(divide="ignore", invalid="ignore"):
        pc = np.mod(np.rint(12.0 * np.log2(bin_hz / 440.0)).astype(int), 12)
    chroma = np.zeros((12, feat.shape[1]))
    for k in range(12):
        rows = band & (pc == k)
        if rows.any():
            chroma[k] = feat[rows].sum(axis=0)
    nrm = np.linalg.norm(chroma, axis=0, keepdims=True)
    chroma = np.where(nrm > 0, chroma / np.maximum(nrm, 1e-30), 0.0)
    n_blocks = chroma.shape[1] // BLOCK_FRAMES
    if n_blocks == 0:
        raise ValueError("track too short for chroma-block analysis")
    blocks = chroma[:, :n_blocks * BLOCK_FRAMES].reshape(
        12, n_blocks, BLOCK_FRAMES).mean(axis=2)
    nrm = np.linalg.norm(blocks, axis=0, keepdims=True)
    blocks = np.where(nrm > 0, blocks / np.maximum(nrm, 1e-30), 0.0)
    return blocks


def structural_scores(y: np.ndarray, fs: int) -> dict:
    blocks = chroma_blocks(y, fs)
    sim = blocks.T @ blocks
    m = sim.shape[0]
    i, j = np.triu_indices(m, k=0)
    lag = np.abs(i - j)
    long_mask = lag >= LONG_LAG_BLOCKS
    short_mask = (lag >= SHORT_LAG_BLOCKS) & (lag < LONG_LAG_BLOCKS)
    r_long = float(sim[i[long_mask], j[long_mask]].mean())
    r_short = (float(sim[i[short_mask], j[short_mask]].mean())
               if short_mask.any() else 0.0)
    # per-lag mean similarity (both diagonal directions), long lags only
    lag_ids = np.unique(lag[long_mask])
    lag_mean = {int(t): float(sim[i[lag == t], j[lag == t]].mean())
                for t in lag_ids}
    peak = max(lag_mean, key=lambda t: lag_mean[t])
    return {"r_long": r_long, "r_short": r_short,
            "peak_lag_s": peak / 2.0,           # blocks -> s at 2 blocks/s
            "peak_lag_similarity": lag_mean[peak],
            "texture": (lambda v: (v / max(float(np.linalg.norm(v)), 1e-30)))(
                blocks.mean(axis=1))}


def texture_distance(tex_x, tex_ab: list) -> float:
    return float(np.mean([1.0 - float(np.dot(tex_x, t)) for t in tex_ab]))


# ---------------------------------------------------------------------------
# pre-declared selection
# ---------------------------------------------------------------------------


def analyze_candidate(c: Candidate):
    """Fill screening + structural fields (decode happens once)."""
    probe_candidate(c)
    y, fs = decode_mono(c.path)
    lead, trail = edge_silence(y, fs)
    c.leading_silence_s = lead
    c.trailing_silence_s = trail
    scores = structural_scores(y, fs)
    c.r_long = scores["r_long"]
    c.r_short = scores["r_short"]
    c.peak_lag_s = scores["peak_lag_s"]
    c.texture = scores["texture"]


def select_sources(cands: list) -> dict:
    """Apply the pre-declared rules to ANALYZED candidates (see module
    docstring). Deterministic incl. tie-breaks (ascending SHA-256)."""
    pool = [c for c in cands if not c.excluded_by and not c.is_duplicate_of
            and c.duration_s >= PAYLOAD_DURATION_S
            and c.leading_silence_s <= MAX_EDGE_SILENCE_S
            and c.trailing_silence_s <= MAX_EDGE_SILENCE_S]
    pool.sort(key=lambda c: c.sha256)
    if len(pool) < 3:
        raise RuntimeError(f"clean pool too small after screening: {len(pool)}")

    b_eligible = [c for c in pool if c.duration_s >= B_MIN_DURATION_S]
    if not b_eligible:
        raise RuntimeError("no candidate long enough for BUF-BMID")
    best_r = max(c.r_long for c in b_eligible)
    song_b = min((c for c in b_eligible if c.r_long == best_r),
                 key=lambda c: c.sha256)

    median_d = float(np.median([c.duration_s for c in pool]))
    a_pool = [c for c in pool
              if c is not song_b and c.r_long < song_b.r_long]
    if not a_pool:
        raise RuntimeError("no candidate with R_long below song B for song A")
    song_a = min(a_pool, key=lambda c: (abs(c.duration_s - median_d),
                                        c.sha256))

    tex_ab = [song_a.texture, song_b.texture]
    i_pool = [c for c in pool if c is not song_a and c is not song_b]
    dists = {c.sha256: texture_distance(c.texture, tex_ab) for c in i_pool}
    best_d = max(dists.values())
    interference = min((c for c in i_pool if dists[c.sha256] == best_d),
                       key=lambda c: c.sha256)

    return {"pool": pool, "median_duration_s": median_d,
            "song_a": song_a, "song_b": song_b,
            "interference": interference}


# ---------------------------------------------------------------------------
# record emission
# ---------------------------------------------------------------------------


def selection_record(sel: dict, scan_summary: dict, roots) -> dict:
    def identity_row(c: Candidate, role_note: str) -> dict:
        return {**c.as_row(), "role_note": role_note}

    pool = sel["pool"]
    a, b, i = sel["song_a"], sel["song_b"], sel["interference"]
    matched_exclusions = []
    seen = set()
    for c in scan_summary["candidates"]:
        for ident in c.excluded_by:
            if ident.startswith("UNDECODABLE:"):
                continue      # screening failures are not historical IDs
            if ident not in seen:
                seen.add(ident)
                exc = next(e for e in EXCLUSIONS if e["identity"] == ident)
                matched_exclusions.append(
                    {"identity": ident,
                     "pool_files_matched": sorted(
                         Path(c.path).name for c in scan_summary["candidates"]
                         if ident in c.excluded_by),
                     "provenance": exc["provenance"]})

    return {
        "pilot_pack_only": "PILOT_PACK_ONLY",
        "not_paper_evidence": "NOT_PAPER_EVIDENCE",
        "status": "SELECTED_FROZEN",
        "frozen_note": (
            "Selection is FROZEN before buffer rendering. Sources may only "
            "be replaced before recording for the reasons pre-declared in "
            "FRESH_PILOT_PLAN section 9 (undecodable / technically "
            "impossible / protocol violation / access problem), documented "
            "BEFORE any benchmark outcome is observed. Never replaced "
            "because a comparator performs well or badly."),
        "privacy_note": (
            "Clean-pool and exclusion rows carry basenames + hashes only; "
            "full local paths are recorded for the three SELECTED sources "
            "(needed to re-run the kit build on this machine) and in the "
            "LOCAL-ONLY inventory. The full media listing is never "
            "committed."),
        "media_roots_scanned": [str(r) for r in roots],
        "scan_summary": scan_summary["aggregate"],
        "historical_exclusions": matched_exclusions,
        "clean_pool": [{**c.as_row(), "path": None,
                        "basename": Path(c.path).name} for c in pool],
        "selection_rules": {
            "screening": (
                f"decodable; duration >= {PAYLOAD_DURATION_S} s; leading and "
                f"trailing silence <= {MAX_EDGE_SILENCE_S} s at "
                f"-60 dBFS; duplicates collapsed by SHA-256; historical "
                f"exclusions applied"),
            "song_b": (
                f"highest R_long among candidates with duration >= "
                f"{B_MIN_DURATION_S} s (BUF-BMID needs {BMID_START_S} s "
                f"+ {PAYLOAD_DURATION_S} s)"),
            "song_a": (
                "closest duration to the clean-pool median among candidates "
                "with R_long strictly below song B (structure-blind "
                "ordinariness; B-feasibility clause guarantees song B is "
                "measurably more repetitive than song A)"),
            "interference": (
                "maximum mean chroma-texture distance to {song A, song B} "
                "among remaining candidates"),
            "structural_metric": (
                "R_long = mean cosine similarity of 2 Hz chroma blocks at "
                f"lags >= {LONG_LAG_BLOCKS // 2} s (see module docstring). "
                "A deterministic selection heuristic, NOT a universal "
                "difficulty measure."),
            "tie_break": "ascending SHA-256",
        },
        "clean_pool_median_duration_s": round(sel["median_duration_s"], 3),
        "song_a": identity_row(a, (
            f"ordinary representative: duration closest to clean-pool "
            f"median ({sel['median_duration_s']:.1f} s); R_long "
            f"{a.r_long:.3f} < song B {b.r_long:.3f}; clean decode, edge "
            f"silence {a.leading_silence_s:.2f}s/"
            f"{a.trailing_silence_s:.2f}s")),
        "song_b": identity_row(b, (
            f"structurally difficult: highest R_long "
            f"({b.r_long:.3f}) among {B_MIN_DURATION_S}-eligible "
            f"candidates; peak long-lag recurrence at "
            f"{b.peak_lag_s:.1f} s (similarity "
            f"{b.r_long:.3f}); edge silence "
            f"{b.leading_silence_s:.2f}s/{b.trailing_silence_s:.2f}s")),
        "interference": identity_row(i, (
            f"maximum chroma-texture distance to song A and song B among "
            f"remaining candidates ({texture_distance(i.texture, [a.texture, b.texture]):.3f}); "
            f"never a reference in any pairing")),
    }


def local_inventory_record(cands: list, roots) -> dict:
    """FULL local inventory (personal paths) — LOCAL ONLY, never committed."""
    return {
        "local_only": "NEVER_COMMIT_PERSONAL_MEDIA_INVENTORY",
        "media_roots": [str(r) for r in roots],
        "candidates": [c.as_row() for c in cands],
        "duplicates": [{"duplicate_path": c.path, "canonical_path":
                        c.is_duplicate_of}
                       for c in cands if c.is_duplicate_of],
    }


def aggregate_summary(cands: list) -> dict:
    from collections import Counter
    ext = Counter(Path(c.path).suffix.lower() for c in cands)
    dup = [c for c in cands if c.is_duplicate_of]
    probed = [c for c in cands if c.duration_s > 0]
    return {
        "files_found": len(cands),
        "unique_by_sha256": len({c.sha256 for c in cands}),
        "exact_duplicate_files": len(dup),
        "probed_files": len(probed),
        "extensions": dict(ext),
        "duration_range_s": [round(min(c.duration_s for c in probed), 1),
                             round(max(c.duration_s for c in probed), 1)]
        if probed else [],
        "excluded_historical": len({c.path for c in cands
                                    if c.excluded_by}),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="fresh-pilot source selection (PILOT_ONLY; owner media "
                    "roots are READ-ONLY)")
    ap.add_argument("--roots", nargs="+", required=True,
                    help="owner media roots to scan (read-only)")
    ap.add_argument("--out", default=str(PILOT_PACK / "source_selection.json"))
    ap.add_argument("--local-dir", default=str(PILOT_PACK / "local"))
    args = ap.parse_args(argv)

    roots = [Path(r) for r in args.roots]
    print(f"[selection] scanning {len(roots)} roots (read-only) …")
    cands = collapse_duplicates(scan_roots(roots))
    for c in cands:
        c.excluded_by = match_exclusions(c)
    print(f"[selection] {len(cands)} files, "
          f"{len({c.sha256 for c in cands})} unique, "
          f"{sum(1 for c in cands if c.excluded_by)} historically excluded")

    analyzed = 0
    for c in cands:
        if c.excluded_by or c.is_duplicate_of:
            continue
        try:
            analyze_candidate(c)
            analyzed += 1
            print(f"  analyzed {Path(c.path).name}: {c.duration_s:.1f}s "
                  f"R_long={c.r_long:.3f}")
        except Exception as exc:   # decode/analysis failure = screening out
            c.excluded_by = [f"UNDECODABLE: {type(exc).__name__}: {exc}"]
            print(f"  FAILED {Path(c.path).name}: {exc}")
    print(f"[selection] analyzed {analyzed} clean candidates")

    sel = select_sources(cands)

    record = selection_record(
        sel, {"candidates": cands, "aggregate": aggregate_summary(cands)},
        roots)
    out = Path(args.out)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[selection] frozen selection record -> {out}")

    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "inventory.json").write_text(
        json.dumps(local_inventory_record(cands, roots),
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[selection] LOCAL-ONLY full inventory -> "
          f"{local_dir / 'inventory.json'} (never committed)")

    for role in ("song_a", "song_b", "interference"):
        c = sel[role]
        print(f"  {role.upper()}: {Path(c.path).name} "
              f"({c.duration_s:.1f}s, R_long={c.r_long:.3f})")
    return record


if __name__ == "__main__":
    main()
