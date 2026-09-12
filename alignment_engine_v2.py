"""Alignment Engine v2 — evidence-based alignment decisions (RA-1.2B).

Default product alignment path since RA-1.2D: the GUI's SyncWorker and
AnalyzeWorker call find_offset_v2() and consume AlignmentDecision
(ACCEPT/ABSTAIN). The legacy auto_sync.find_offset() remains available
for backward-compatible tests, experiment comparisons, and explicitly-called
diagnostic tooling — it is no longer the normal GUI engine.

Design (RA-1.2A §10, corrected in RA-1.2B):

    primary evidence (tonal, pcen_spectral)
        +
    corroborating evidence (onset_temporal)
        +
    contradiction / ambiguity checks (uniqueness, overlap)
        ->
    ACCEPT or ABSTAIN

RA-1.2D1 adds the temporal-support gate: an ACCEPT is only issued if the
deciding family's net signed correlation at the proposed offset is
distributed over the overlap. A brief common content between two different
songs (e.g. a ~1 s shared boundary event) otherwise produces a strong,
multi-family-agreed peak over a large geometric overlap while the evidence
itself lives in one short region (the RA-1.2A/Astra release blocker:
94.6% of the net signed PCEN correlation in one 1 s bin). Cross-family
agreement demonstrates a shared event; only distributed evidence
demonstrates a whole-song alignment:

    geometric overlap (where comparison is possible)
        != distributed temporal support (where matching evidence exists)

This is deliberately NOT majority voting:

- PCEN and PCEN+HPSS share one underlying feature (PCEN of mel bands) and
  count as ONE family ("pcen_spectral"); they can never form "two votes".
- Onset flux and PCEN deltas are both temporal-change evidence and are
  correlated; onset agreement is corroboration of a strong primary, never
  an independent deciding vote.
- The tonal family (chroma CENS deltas) and the pcen_spectral family have
  genuinely different failure modes; agreement between THOSE two is the
  only dual-primary acceptance path.

Offset sign convention (matches auto_sync.mix_and_export):
    offset > 0 : music must be delayed by `offset` seconds (adelay)
    offset < 0 : the first |offset| seconds of music are trimmed (atrim)
"""
from __future__ import annotations

import dataclasses
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import signal

from auto_sync import (
    _align_hybrid,
    _align_onset,
    _correlation_z_score,
    extract_audio,
)
import imageio_ffmpeg
import librosa

# ---------------------------------------------------------------------------
# evidence families
# ---------------------------------------------------------------------------

FAMILY_TONAL = "tonal"
FAMILY_PCEN = "pcen_spectral"
FAMILY_ONSET = "onset_temporal"

METHOD_FAMILY = {
    "hybrid": FAMILY_TONAL,
    "onset": FAMILY_ONSET,
    "pcen_hpss": FAMILY_PCEN,
    "pcen": FAMILY_PCEN,  # diagnostic member of the SAME family as pcen_hpss
}

# Status values
STATUS_ACCEPTED = "accepted"
STATUS_ABSTAINED = "abstained"

# Stable engine identity for logs / diagnostics / supportability reports.
# Deliberately locale-independent (like a version number).
ENGINE_LABEL = "Engine v2 (evidence-gated)"

# Reason codes (machine-actionable)
ACCEPT_DUAL_FAMILY = "ACCEPT_DUAL_FAMILY"
ACCEPT_PRIMARY_WITH_CORROBORATION = "ACCEPT_PRIMARY_WITH_CORROBORATION"
ABSTAIN_NO_CLUSTER_MEETS_FLOORS = "ABSTAIN_NO_CLUSTER_MEETS_FLOORS"
ABSTAIN_PRIMARY_NOT_CORROBORATED = "ABSTAIN_PRIMARY_NOT_CORROBORATED"
ABSTAIN_AMBIGUOUS_CLUSTER = "ABSTAIN_AMBIGUOUS_CLUSTER"
ABSTAIN_INSUFFICIENT_OVERLAP = "ABSTAIN_INSUFFICIENT_OVERLAP"
# RA-1.2D1 temporal-support gate: the deciding evidence for the proposed
# offset is concentrated in a very short segment (one brief common content),
# so it cannot demonstrate a whole-song alignment.
ABSTAIN_CONCENTRATED_EVIDENCE = "ABSTAIN_CONCENTRATED_EVIDENCE"
ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT = "ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT"


# ---------------------------------------------------------------------------
# calibration
# ---------------------------------------------------------------------------
#
# Thresholds below are the RA-1.2B calibrated defaults. Provenance: synthetic
# null realizations + real mismatched-song negatives + real positive pairs,
# documented in docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md. They are deliberately
# conservative: a false ACCEPT (confident wrong export) is worse than a
# false ABSTAIN (recoverable).


@dataclass(frozen=True)
class DecisionPolicy:
    """Thresholds for the alignment decision. All times in seconds."""

    # Candidates within this distance of each other form one cluster.
    cluster_tol_s: float = 0.15
    # CASE E: reject candidates whose music/video overlap is shorter.
    min_overlap_s: float = 30.0
    # Uniqueness (top-1/top-2 independent-peak ratio) for CASE A. The 1.0
    # semantic is deliberate: each primary family must rank this cluster as
    # its own #1 candidate (< 1.0 means a competing peak beats it). The
    # cross-family agreement is the discriminator here, not peak dominance.
    margin_floor_a: float = 1.00
    # Uniqueness for CASE B, where a single family decides — the risky
    # path, so it demands a clearly dominant peak.
    margin_floor_b: float = 1.40
    # CASE A: dual-family acceptance floors. Each floor sits above the
    # highest cluster-Z observed for its family on the RA-1.2B calibration
    # set (30 synthetic null realizations + 10 real mismatched-song
    # negatives): hybrid 4.94, pcen family 5.55. Provenance in
    # docs/RA-1.2B-ALIGNMENT-ENGINE-V2.md. CASE A additionally requires
    # BOTH families to co-rank the cluster, which no mismatch did (0/10).
    tonal_z_floor: float = 5.0
    pcen_z_floor: float = 5.6
    # CASE B: single strong pcen_hpss primary + onset corroboration.
    pcen_primary_z_floor: float = 7.0
    # Onset corroboration floor (onset curve Z at the primary's offset).
    # Real mismatch onset cluster-Z max 2.01; the RA-1.2A real low-SNR
    # pair corroborates at 2.27. Defense in depth only: CASE B's primary
    # gate is pcen_primary_z_floor.
    onset_corroboration_z_floor: float = 2.0
    # CASE D: a competing cluster carrying every deciding family at >= this
    # fraction of the accepted cluster's strength is "materially comparable"
    # and forces an abstain (repeated / structurally ambiguous content).
    ambiguity_z_ratio: float = 0.95
    # How many independent peaks each family nominates as candidates.
    top_candidates_per_family: int = 4
    # ---------------------------------------------------------------------
    # RA-1.2D1 temporal-support gate. The RA-1.2A/Astra audit demonstrated
    # that a ~1 s shared boundary event between two different songs can
    # drive the entire global evidence (94.6% of the net signed PCEN
    # correlation at the accepted offset), so a qualifying cluster is only
    # accepted if the deciding family's net signed correlation, decomposed
    # into 1 s reference-time bins at the proposed offset, is NOT dominated
    # by a single bin. Calibrated on development data only (18 concentrated
    # wrong-song accepts measured 0.48-1.05; 46 true accepts 0.02-0.11;
    # held-out test: 160/160 wrong-song pairs abstain, 55/55 previously
    # accepted positives retained). See
    # docs/RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md.
    bin_width_s: float = 1.0
    max_top_bin_share: float = 0.25


DEFAULT_POLICY = DecisionPolicy()


# ---------------------------------------------------------------------------
# evidence data model
# ---------------------------------------------------------------------------


@dataclass
class CandidateEvidence:
    """One candidate offset nominated by one generator."""

    method: str
    family: str
    offset_s: float
    z: float
    peak_margin: Optional[float]
    usable_overlap_s: float
    runtime_s: float
    top_competing_offsets_s: tuple = ()
    notes: dict = field(default_factory=dict)

    def as_dict(self):
        d = dataclasses.asdict(self)
        d["top_competing_offsets_s"] = list(self.top_competing_offsets_s)
        return d


@dataclass
class FamilyResult:
    """Full curve + diagnostics for one evidence generator."""

    method: str
    family: str
    curve: np.ndarray
    n_video_frames: int
    z: float
    runtime_s: float
    error: Optional[str] = None
    # RA-1.2D1: per-source feature matrix attached by the PCEN generators
    # so the temporal-support gate can reuse the already-computed
    # representation. Synthetic-curve tests (the decide_from_families seam)
    # leave this empty; the gate then reports itself as not applicable.
    features: Optional[tuple] = None


@dataclass
class AlignmentDecision:
    """Outcome of Engine v2. Decision logic is presentation-free; use
    :func:`decision_message` for user-facing text."""

    status: str
    offset: Optional[float]
    reason_code: str
    evidence: dict
    clusters: list
    policy: dict
    runtime_s: float

    @property
    def accepted(self):
        return self.status == STATUS_ACCEPTED

    def as_dict(self):
        return {
            "status": self.status,
            "offset": self.offset,
            "reason_code": self.reason_code,
            "evidence": self.evidence,
            "clusters": self.clusters,
            "policy": self.policy,
            "runtime_s": self.runtime_s,
        }


def decision_message(decision, tr=None):
    """Presentation string for a decision, separate from the decision logic.

    `tr` is an optional translation callable like the one ui_main passes to
    mix_and_export; the default returns the built-in Chinese strings.

    RA-1.2D note: the GUI does NOT use this helper for user-facing text —
    it maps reason codes onto the locale files instead, keeping the
    decision layer presentation-independent. This helper remains a
    diagnostic/experiment convenience (e.g. engine_v2_owner_test.py).
    """
    _ = tr  # reserved for UI i18n; engine itself stays UI-independent
    if decision.status == STATUS_ACCEPTED:
        return f"已确定对齐偏移: {decision.offset:+.3f} s（置信度评估通过）"
    reasons = {
        ABSTAIN_NO_CLUSTER_MEETS_FLOORS: "各证据家族置信度不足，无法可靠确定对齐偏移。",
        ABSTAIN_PRIMARY_NOT_CORROBORATED: "存在较强候选，但缺少佐证证据，无法可靠确定对齐偏移。",
        ABSTAIN_AMBIGUOUS_CLUSTER: "存在多个强度相当的候选偏移，无法唯一确定对齐。",
        ABSTAIN_INSUFFICIENT_OVERLAP: "候选偏移的重叠时长过短，无法可靠确定对齐。",
        ABSTAIN_CONCENTRATED_EVIDENCE: "对齐证据集中在极短的片段，无法证明整曲级别的对齐。",
        ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT: "有效重叠内容不足，无法证明整曲级别的对齐。",
    }
    return reasons.get(decision.reason_code, "无法可靠确定对齐偏移。")


# ---------------------------------------------------------------------------
# correlation / peak helpers (same conventions as auto_sync)
# ---------------------------------------------------------------------------


def _z_at_index(curve, idx):
    """Z of the curve value at `idx` against the whole-curve distribution."""
    std = np.std(curve)
    if std == 0:
        return 0.0
    return float((curve[idx] - np.mean(curve)) / std)


def _independent_peak_indices(curve, min_separation_frames):
    """Peak indices separated by at least `min_separation_frames`, best first."""
    curve = np.asarray(curve)
    if curve.size == 0:
        return np.empty(0, dtype=int)
    idx, _ = signal.find_peaks(curve, distance=max(1, min_separation_frames))
    best = int(np.argmax(curve))
    if best not in set(idx.tolist()):
        idx = np.append(idx, best)
    return idx[np.argsort(curve[idx])[::-1]]


def _margin_outside_cluster(curve, peak_idx, lo, hi):
    """Uniqueness of one cluster: best value inside [lo, hi] divided by the
    best independent peak value outside it."""
    inside = [i for i in peak_idx if lo <= i <= hi]
    outside = [i for i in peak_idx if not (lo <= i <= hi)]
    if not inside:
        return 0.0
    inside_best = float(np.max(curve[inside]))
    if not outside:
        return float("inf") if inside_best > 0 else 0.0
    outside_best = float(np.max(curve[outside]))
    if outside_best <= 0:
        return float("inf") if inside_best > 0 else 0.0
    return inside_best / outside_best


def _usable_overlap_s(offset_s, video_dur_s, music_dur_s):
    """Seconds of audio in which BOTH the recording and the target music are
    present, given the production offset convention."""
    if offset_s >= 0:
        return max(0.0, min(offset_s + music_dur_s, video_dur_s) - offset_s)
    return max(0.0, min(music_dur_s + offset_s, video_dur_s))


def _offset_to_index(offset_s, n_video_frames, hop_length, sr):
    """Nearest correlation-axis index for a production-convention offset."""
    lag = -offset_s * sr / hop_length
    return int(round(lag)) + (n_video_frames - 1)


def _index_to_offset(idx, n_video_frames, hop_length, sr):
    lag = idx - (n_video_frames - 1)
    return -(lag * hop_length) / sr


# ---------------------------------------------------------------------------
# evidence generators (production-worthy only)
# ---------------------------------------------------------------------------


def _tonal_family(y_video, y_music, sr, hop_length):
    """CASE A primary #1: chroma CENS deltas + small onset refinement
    (production hybrid curve — nominates candidates, never accepted alone)."""
    t0 = time.perf_counter()
    _, z, corr = _align_hybrid(y_video, y_music, sr, hop_length)
    return FamilyResult(
        method="hybrid", family=FAMILY_TONAL, curve=np.asarray(corr),
        n_video_frames=1 + len(y_video) // hop_length, z=float(z),
        runtime_s=time.perf_counter() - t0,
    )


def _onset_family(y_video, y_music, sr, hop_length):
    """Corroborating evidence: onset-strength envelope correlation."""
    t0 = time.perf_counter()
    _, _, corr = _align_onset(y_video, y_music, sr, hop_length)
    return FamilyResult(
        method="onset", family=FAMILY_ONSET, curve=np.asarray(corr),
        n_video_frames=1 + len(y_video) // hop_length,
        z=float(_correlation_z_score(np.asarray(corr))),
        runtime_s=time.perf_counter() - t0,
    )


def _pcen_hpss_features(y, sr, hop_length, n_mels=96, fmin=30.0, fmax=4000.0,
                        hpss_kernel=31, positive_only=True):
    """Harmonic-separated PCEN mel delta (RA-1.2A method C'): suppresses
    percussive taps before the PCEN/delta pipeline."""
    S = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=min(2048, 4 * hop_length), hop_length=hop_length,
        n_mels=n_mels, fmin=fmin, fmax=fmax, power=2.0,
    )
    H, _ = librosa.decompose.hpss(S, kernel_size=hpss_kernel)
    P = librosa.pcen(H, sr=sr, hop_length=hop_length)
    return _pcen_delta(P, positive_only)


def _pcen_features(y, sr, hop_length, n_mels=96, fmin=30.0, fmax=4000.0,
                   positive_only=True):
    """Plain PCEN mel delta (diagnostic member of the SAME family as
    pcen_hpss — correlated features, not an independent vote)."""
    S = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=min(2048, 4 * hop_length), hop_length=hop_length,
        n_mels=n_mels, fmin=fmin, fmax=fmax, power=2.0,
    )
    P = librosa.pcen(S, sr=sr, hop_length=hop_length)
    return _pcen_delta(P, positive_only)


def _pcen_delta(P, positive_only):
    D = np.diff(P, axis=1, prepend=P[:, :1])
    if positive_only:
        D = np.maximum(D, 0.0)
    std = np.std(D, axis=1, keepdims=True)
    return (D - np.mean(D, axis=1, keepdims=True)) / (std + 1e-12)


def _correlate_rows(feat_video, feat_music):
    corr = np.zeros(feat_video.shape[1] + feat_music.shape[1] - 1)
    for i in range(feat_video.shape[0]):
        corr += signal.correlate(feat_music[i], feat_video[i], mode="full",
                                 method="fft")
    return corr


def _run_generators(y_video, y_music, sr, hop_length):
    """Run the production evidence generators. A failed generator must not
    crash the engine — it is recorded as a family error."""
    results = []

    def add(name, fn):
        t0 = time.perf_counter()
        try:
            results.append(fn(y_video, y_music, sr, hop_length))
        except Exception as exc:
            results.append(FamilyResult(
                method=name, family=METHOD_FAMILY[name], curve=np.empty(0),
                n_video_frames=0, z=0.0, runtime_s=time.perf_counter() - t0,
                error=f"{type(exc).__name__}: {exc}",
            ))

    add("hybrid", _tonal_family)
    add("onset", _onset_family)

    def pcen_hpss_gen(v, m, s, h):
        t0 = time.perf_counter()
        fv = _pcen_hpss_features(v, s, h)
        fm = _pcen_hpss_features(m, s, h)
        corr = _correlate_rows(fv, fm)
        return FamilyResult(
            method="pcen_hpss", family=FAMILY_PCEN, curve=corr,
            n_video_frames=1 + len(v) // h,
            z=float(_correlation_z_score(corr)),
            runtime_s=time.perf_counter() - t0,
            features=(fv, fm),
        )

    def pcen_gen(v, m, s, h):
        t0 = time.perf_counter()
        fv = _pcen_features(v, s, h)
        fm = _pcen_features(m, s, h)
        corr = _correlate_rows(fv, fm)
        return FamilyResult(
            method="pcen", family=FAMILY_PCEN, curve=corr,
            n_video_frames=1 + len(v) // h,
            z=float(_correlation_z_score(corr)),
            runtime_s=time.perf_counter() - t0,
            features=(fv, fm),
        )

    add("pcen_hpss", pcen_hpss_gen)
    add("pcen", pcen_gen)
    return results


# ---------------------------------------------------------------------------
# clustering
# ---------------------------------------------------------------------------


def _family_candidates(fr, policy, sr, hop_length, video_dur, music_dur):
    """Top-N independent peaks of one family as CandidateEvidence."""
    if fr.error or fr.curve.size == 0:
        return []
    min_sep = max(1, int(1.5 * sr / hop_length))
    peaks = _independent_peak_indices(fr.curve, min_sep)[
        : policy.top_candidates_per_family]
    cands = []
    for idx in peaks:
        offset = _index_to_offset(int(idx), fr.n_video_frames, hop_length, sr)
        others = [i for i in peaks if i != idx]
        margin = None
        if others and fr.curve[others].max() > 0:
            margin = float(fr.curve[idx] / fr.curve[others].max())
        competing = tuple(
            round(_index_to_offset(int(i), fr.n_video_frames, hop_length, sr), 4)
            for i in others)
        cands.append(CandidateEvidence(
            method=fr.method, family=fr.family, offset_s=float(offset),
            z=_z_at_index(fr.curve, int(idx)), peak_margin=margin,
            usable_overlap_s=_usable_overlap_s(offset, video_dur, music_dur),
            runtime_s=fr.runtime_s,
            top_competing_offsets_s=competing,
        ))
    return cands


def _build_clusters(family_results, policy, sr, hop_length, video_dur,
                    music_dur):
    """Group candidate peaks from all families into offset clusters and
    compute per-cluster, per-family evidence.

    Per-family cluster evidence is the strongest member of that family in
    the cluster (pcen_hpss and plain pcen therefore combine, they never
    compete or double-count).
    """
    all_cands = []
    for fr in family_results:
        all_cands.extend(_family_candidates(fr, policy, sr, hop_length,
                                            video_dur, music_dur))
    all_cands.sort(key=lambda c: c.offset_s)

    clusters = []
    for cand in all_cands:
        for cl in clusters:
            if abs(cand.offset_s - cl["offset_s"]) <= policy.cluster_tol_s:
                cl["candidates"].append(cand)
                offs = sorted(c.offset_s for c in cl["candidates"])
                cl["offset_s"] = offs[len(offs) // 2]
                break
        else:
            clusters.append({"offset_s": cand.offset_s,
                             "candidates": [cand]})

    win_frames = max(1, int(round(2 * policy.cluster_tol_s * sr / hop_length)))

    peak_cache = {}
    for cl in clusters:
        by_family = {}
        for fr in family_results:
            fam_members = [c for c in cl["candidates"] if c.family == fr.family]
            if fr.error or fr.curve.size == 0 or not fam_members:
                continue
            if fr.method not in peak_cache:
                min_sep = max(1, int(1.5 * sr / hop_length))
                peak_cache[fr.method] = _independent_peak_indices(fr.curve,
                                                                  min_sep)
            idx = int(np.clip(
                _offset_to_index(cl["offset_s"], fr.n_video_frames,
                                 hop_length, sr),
                0, len(fr.curve) - 1))
            lo, hi = idx - win_frames, idx + win_frames
            # Family evidence for this cluster = the family's own best
            # independent peak INSIDE the cluster window (never the curve
            # value at the cluster representative: sharp real peaks must
            # not be penalized for the representative's exact position).
            inside = [(int(i), _z_at_index(fr.curve, int(i)))
                      for i in peak_cache[fr.method] if lo <= i <= hi]
            if inside:
                best_idx, z_val = max(inside, key=lambda t: t[1])
                best_off = _index_to_offset(best_idx, fr.n_video_frames,
                                            hop_length, sr)
            else:  # no peak of this family in the window: evaluate in place
                z_val = _z_at_index(fr.curve, idx)
                best_off = cl["offset_s"]
            entry = {
                "methods": sorted({c.method for c in fam_members}),
                "z_at_cluster": z_val,
                "margin_at_cluster": _margin_outside_cluster(
                    fr.curve, peak_cache[fr.method], lo, hi),
                "best_member_offset_s": best_off,
            }
            prev = by_family.get(fr.family)
            # Same family, multiple members (pcen_hpss + pcen): ONE vote —
            # keep the strongest member's evidence.
            if prev is None or entry["z_at_cluster"] > prev["z_at_cluster"]:
                by_family[fr.family] = entry
        cl["families"] = by_family
        cl["overlap_s"] = _usable_overlap_s(cl["offset_s"], video_dur,
                                            music_dur)
    return clusters


def _serialize_cluster(cl):
    return {
        "offset_s": round(cl["offset_s"], 4),
        "overlap_s": round(cl["overlap_s"], 2),
        "candidates": [c.as_dict() for c in cl["candidates"]],
        "families": {
            fam: {
                "methods": v["methods"],
                "z_at_cluster": round(v["z_at_cluster"], 3),
                "margin_at_cluster": (
                    None if not np.isfinite(v["margin_at_cluster"])
                    else round(float(v["margin_at_cluster"]), 3)
                ),
                "best_member_offset_s": round(v["best_member_offset_s"], 4),
            }
            for fam, v in cl["families"].items()
        },
    }


# ---------------------------------------------------------------------------
# decision policy
# ---------------------------------------------------------------------------


def _case_a_failed_checks(cl, policy):
    """Return the list of CASE A checks that failed for this cluster."""
    fam = cl["families"]
    tonal = fam.get(FAMILY_TONAL)
    pcen = fam.get(FAMILY_PCEN)
    failed = []
    if tonal is None:
        failed.append("tonal_missing")
    else:
        if tonal["z_at_cluster"] < policy.tonal_z_floor:
            failed.append("tonal_z")
        if tonal["margin_at_cluster"] < policy.margin_floor_a:
            failed.append("tonal_margin")
    if pcen is None:
        failed.append("pcen_missing")
    else:
        if pcen["z_at_cluster"] < policy.pcen_z_floor:
            failed.append("pcen_z")
        if pcen["margin_at_cluster"] < policy.margin_floor_a:
            failed.append("pcen_margin")
    return failed


def _case_b_failed_checks(cl, policy):
    """Return the list of CASE B checks that failed for this cluster."""
    fam = cl["families"]
    pcen = fam.get(FAMILY_PCEN)
    onset = fam.get(FAMILY_ONSET)
    failed = []
    if pcen is None:
        failed.append("pcen_missing")
    else:
        if pcen["z_at_cluster"] < policy.pcen_primary_z_floor:
            failed.append("pcen_z")
        if pcen["margin_at_cluster"] < policy.margin_floor_b:
            failed.append("pcen_margin")
    if onset is None:
        failed.append("onset_missing")
    elif onset["z_at_cluster"] < policy.onset_corroboration_z_floor:
        failed.append("onset_z")
    return failed


def _cluster_score(cl):
    """Ranking score for choosing the 'best' cluster in reports/reasons."""
    zs = [f["z_at_cluster"] for f in cl["families"].values()]
    return max(zs) if zs else 0.0


def _deciding_families(reason_code):
    return ((FAMILY_TONAL, FAMILY_PCEN)
            if reason_code == ACCEPT_DUAL_FAMILY else (FAMILY_PCEN,))


def _comparable_competitor_exists(cl, reason_code, clusters, policy):
    """CASE D: is there another cluster, far enough away, that carries every
    deciding family at >= ambiguity_z_ratio of the accepted cluster's
    strength? Such content is structurally ambiguous -> abstain."""
    deciding = _deciding_families(reason_code)
    for other in clusters:
        if other is cl:
            continue
        if abs(other["offset_s"] - cl["offset_s"]) <= 2 * policy.cluster_tol_s:
            continue
        fam_other = other["families"]
        if any(f not in fam_other for f in deciding):
            continue
        if all(fam_other[f]["z_at_cluster"]
               >= policy.ambiguity_z_ratio
               * cl["families"][f]["z_at_cluster"] for f in deciding):
            return True
    return False


# ---------------------------------------------------------------------------
# RA-1.2D1 temporal-support gate
# ---------------------------------------------------------------------------


def _concentration_profile(feat_video, feat_music, offset_s, sr, hop_length,
                           bin_width_s):
    """Net signed feature correlation at `offset_s`, decomposed into
    consecutive `bin_width_s` reference-time bins.

    Video time = music time + offset (production convention), so music
    frame t pairs with video frame t + shift. Returns (bins, t0_s, shift);
    bins is None when the overlap is empty."""
    shift = int(round(offset_s * sr / hop_length))
    a = max(0, -shift)
    b = min(feat_music.shape[1], feat_video.shape[1] - shift)
    if b - a <= 0:
        return None, None, shift
    prod = np.zeros(b - a, dtype=np.float64)
    for band in range(feat_music.shape[0]):
        prod += feat_music[band, a:b] * feat_video[band, a + shift:b + shift]
    n = max(1, int(round(bin_width_s * sr / hop_length)))
    n_bins = int(np.ceil((b - a) / n))
    bins = np.array([prod[i * n:(i + 1) * n].sum() for i in range(n_bins)])
    return bins, a * hop_length / sr, shift


def _deciding_pcen_method(clusters, offset):
    """The pcen_spectral member that supplied the accepted cluster's family
    evidence (highest member peak z inside the cluster). Plain PCEN and
    PCEN+HPSS are correlated derivatives and count as ONE family; the gate
    verifies the member the decision actually stands on."""
    best_method, best_z = None, None
    for cl in clusters:
        if abs(cl["offset_s"] - offset) > 1.0:
            continue
        for cand in cl["candidates"]:
            if cand["family"] != FAMILY_PCEN:
                continue
            if best_z is None or cand["z"] > best_z:
                best_z, best_method = cand["z"], cand["method"]
    return best_method


def _apply_temporal_support(decision, family_results, policy, sr, hop_length):
    """RA-1.2D1: verify that the deciding evidence for an accepted offset is
    distributed over the overlap rather than concentrated in one brief
    segment. Downgrades the ACCEPT to ABSTAIN when the single strongest
    1 s bin carries more than `max_top_bin_share` of the net signed
    correlation at the accepted offset. Never upgrades a decision."""
    if (decision.status != STATUS_ACCEPTED or decision.offset is None
            or not decision.clusters):
        return decision
    method = _deciding_pcen_method(decision.clusters, decision.offset)
    if method is None:
        return decision
    fr = next((f for f in family_results if f.method == method), None)
    if fr is None or fr.error or fr.features is None:
        # Feature matrices unavailable (decide_from_families seam with
        # synthetic curves): the gate is not applicable, say so explicitly.
        decision.evidence["temporal_support"] = {
            "verified_method": method, "applied": False,
            "note": "features unavailable for this decision path",
        }
        return decision

    feat_video, feat_music = fr.features
    bins, t0, _ = _concentration_profile(
        feat_video, feat_music, decision.offset, sr, hop_length,
        policy.bin_width_s)
    if bins is None or bins.size == 0:
        decision.status = STATUS_ABSTAINED
        decision.offset = None
        decision.reason_code = ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT
        decision.evidence["temporal_support"] = {
            "verified_method": method, "applied": True, "n_bins": 0,
        }
        return decision

    total = float(bins.sum())
    top_i = int(np.argmax(bins))
    top_share = float(bins[top_i] / total) if total > 0 else 1.0
    effective = (float(1.0 / np.sum((bins / total) ** 2)) if total > 0
                 else 0.0)
    summary = {
        "verified_method": method,
        "applied": True,
        "top_bin_share": round(top_share, 4),
        "effective_bins": round(effective, 2),
        "n_bins": int(bins.size),
        "max_top_bin_share": policy.max_top_bin_share,
    }
    if top_share > policy.max_top_bin_share:
        decision.status = STATUS_ABSTAINED
        decision.offset = None
        decision.reason_code = ABSTAIN_CONCENTRATED_EVIDENCE
        summary["peak_bin_start_s"] = (
            None if total <= 0 else round(t0 + top_i * policy.bin_width_s, 3))
        summary["total_signed"] = total
        decision.evidence["temporal_support"] = summary
        return decision
    decision.evidence["temporal_support"] = summary
    return decision


def decide_alignment(y_video, y_music, sr=22050, hop_length=512,
                     policy: Optional[DecisionPolicy] = None,
                     durations_s=None) -> AlignmentDecision:
    """Core Engine v2 decision on loaded audio.

    Returns an AlignmentDecision; "no alignment found" is an ABSTAIN
    decision, never an exception.
    """
    policy = policy or DEFAULT_POLICY
    t0 = time.perf_counter()
    video_dur, music_dur = durations_s or (len(y_video) / sr,
                                           len(y_music) / sr)
    family_results = _run_generators(y_video, y_music, sr, hop_length)
    decision = decide_from_families(family_results, sr, hop_length, policy,
                                    video_dur, music_dur)
    decision = _apply_temporal_support(decision, family_results, policy,
                                       sr, hop_length)
    decision.runtime_s = time.perf_counter() - t0
    return decision


def decide_from_families(family_results, sr, hop_length, policy,
                         video_dur, music_dur) -> AlignmentDecision:
    """Decision over already-computed family curves (test seam; also the
    reason-code layer of decide_alignment)."""
    policy = policy or DEFAULT_POLICY
    t0 = time.perf_counter()
    clusters = _build_clusters(family_results, policy, sr, hop_length,
                               video_dur, music_dur)

    accepted = []  # (reason_code, cluster)
    for cl in clusters:
        if cl["overlap_s"] < policy.min_overlap_s:
            continue  # CASE E: edge-lag guard, hard reject
        if not _case_a_failed_checks(cl, policy):
            accepted.append((ACCEPT_DUAL_FAMILY, cl))
        elif not _case_b_failed_checks(cl, policy):
            accepted.append((ACCEPT_PRIMARY_WITH_CORROBORATION, cl))

    if len(accepted) > 1:
        # Two materially comparable qualifying clusters: content ambiguity.
        reason = ABSTAIN_AMBIGUOUS_CLUSTER
        status, offset = STATUS_ABSTAINED, None
    elif len(accepted) == 1:
        reason, cl = accepted[0]
        if _comparable_competitor_exists(cl, reason, clusters, policy):
            status, offset = STATUS_ABSTAINED, None
            reason = ABSTAIN_AMBIGUOUS_CLUSTER
        else:
            status, offset = STATUS_ACCEPTED, _choose_offset(cl)
    else:
        status, offset = STATUS_ABSTAINED, None
        reason = _abstain_reason(clusters, policy)

    evidence = {
        "video_duration_s": round(video_dur, 3),
        "music_duration_s": round(music_dur, 3),
        "families": {
            fr.method: {
                "family": fr.family,
                "z": round(fr.z, 3),
                "runtime_s": round(fr.runtime_s, 3),
                "error": fr.error,
            }
            for fr in family_results
        },
        "n_clusters": len(clusters),
    }
    return AlignmentDecision(
        status=status, offset=offset, reason_code=reason, evidence=evidence,
        clusters=[_serialize_cluster(cl) for cl in clusters],
        policy=dataclasses.asdict(policy),
        runtime_s=time.perf_counter() - t0,
    )


def _choose_offset(cl):
    """Offset of the most unique deciding member (pcen_hpss preferred)."""
    pcen_members = [c for c in cl["candidates"] if c.method == "pcen_hpss"]
    pool = pcen_members or cl["candidates"]
    return max(pool, key=lambda c: (c.peak_margin if c.peak_margin
                                    is not None else 0.0)).offset_s


def _abstain_reason(clusters, policy):
    """Machine-actionable abstain reason, driven by the strongest cluster."""
    if not clusters:
        return ABSTAIN_NO_CLUSTER_MEETS_FLOORS
    if all(cl["overlap_s"] < policy.min_overlap_s for cl in clusters):
        return ABSTAIN_INSUFFICIENT_OVERLAP
    best = max(clusters, key=_cluster_score)
    if best["overlap_s"] < policy.min_overlap_s:
        return ABSTAIN_INSUFFICIENT_OVERLAP
    a_failed = _case_a_failed_checks(best, policy)
    b_failed = _case_b_failed_checks(best, policy)
    # CASE A nearly holds but uniqueness fails -> ambiguity (CASE D).
    a_without_margin = [c for c in a_failed if c != "pcen_margin"
                        and c != "tonal_margin"]
    if not a_without_margin and a_failed:
        return ABSTAIN_AMBIGUOUS_CLUSTER
    # Strong pcen primary present, corroboration/uniqueness missing.
    pcen = best["families"].get(FAMILY_PCEN)
    if pcen is not None and pcen["z_at_cluster"] >= policy.pcen_primary_z_floor:
        if "pcen_margin" in b_failed:
            return ABSTAIN_AMBIGUOUS_CLUSTER
        if b_failed:
            return ABSTAIN_PRIMARY_NOT_CORROBORATED
    return ABSTAIN_NO_CLUSTER_MEETS_FLOORS


# ---------------------------------------------------------------------------
# file-level entry point (parallel to auto_sync.find_offset)
# ---------------------------------------------------------------------------


def find_offset_v2(video_path, music_path, sr=22050,
                   policy: Optional[DecisionPolicy] = None) -> AlignmentDecision:
    """Engine v2 file entry point. Returns an AlignmentDecision; does NOT
    raise CorrelationLowConfidenceError (abstention is a decision, not an
    exception)."""
    policy = policy or DEFAULT_POLICY
    temp_dir = tempfile.gettempdir()
    temp_audio_path = os.path.abspath(
        os.path.join(temp_dir, f"ra_v2_audio_{uuid.uuid4().hex}.wav"))
    temp_music_path = os.path.abspath(
        os.path.join(temp_dir, f"ra_v2_music_{uuid.uuid4().hex}.wav"))
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        extract_audio(ffmpeg_bin, video_path, temp_audio_path, sr)
        extract_audio(ffmpeg_bin, music_path, temp_music_path, sr)
        y_video, _ = librosa.load(temp_audio_path, sr=None, mono=True)
        y_music, _ = librosa.load(temp_music_path, sr=None, mono=True)
        return decide_alignment(y_video, y_music, sr=sr, policy=policy)
    finally:
        for p in (temp_audio_path, temp_music_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
