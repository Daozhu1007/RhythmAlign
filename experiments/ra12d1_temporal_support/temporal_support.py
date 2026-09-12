"""Temporal-support verification of a proposed alignment offset (RA-1.2D1).

Root cause addressed
--------------------
Engine v2 decides ACCEPT from global correlation evidence: a strong peak,
agreed by multiple feature families, plus a *geometric* overlap-length
check. A brief common content (e.g. a ~1 s shared boundary event between
two different songs) produces exactly that signature while supporting only
a tiny fraction of the overlap:

    cross-family agreement != distributed temporal support

Verifier concept (Astra's own measurement, turned into a gate)
--------------------------------------------------------------
Given the already-proposed candidate offset O (candidate generation is NOT
replaced), decompose the deciding feature's net signed correlation at O,

    S = sum_{bands, t in valid overlap} Fm[band, t] * Fv[band, t+shift(O)],

into consecutive 1-second reference-time bins and measure the share of the
net total carried by the single strongest bin:

    concentration = max_i S_i / sum_i S_i

The Astra study measured concentration = 94.6% for the archived blocker
(reproduced here to 0.946); dev true matches measure 0.02-0.11. One brief
region supplying (nearly) all the net evidence is exactly the discovered
failure mode; a whole-song alignment distributes evidence along the
overlap.

Why per-window local-preference statistics are NOT used: real music is
self-similar. Within an 8 s window, same-song content correlates
positively at many lags and unrelated loud content interferes, so "does
this window locally prefer O" is unreliable even for true matches —
measured on DEV, per-window dominance/z statistics do not separate true
from wrong. The bin decomposition asks the question at the right
granularity: not "where does local evidence peak" but "how much of the
total evidence does one place supply".

Which feature is verified: the pcen_spectral FAMILY member that actually
supplied the cluster's deciding evidence (highest member z inside the
accepted cluster; plain pcen and pcen_hpss are correlated derivatives and
count as ONE family — RA-1.2B semantics). The accept stands on that
member's evidence; if that evidence is one brief event, the accept fails
the distributed-support contract, whatever a correlated sibling shows.

Diagnostics reported with every gate run: top_bin_share, effective_bins
(inverse participation ratio), active_bins, n_bins, peak_bin_start_s,
top_k_share. The gate can only downgrade an ACCEPT to ABSTAIN.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupportPolicy:
    # Bin width for the net-correlation decomposition (seconds).
    bin_s: float = 1.0
    # Maximum share of the net signed correlation the single strongest bin
    # may carry for the offset to count as distributed. Calibrated on DEV
    # only: dev wrong accepts measure 0.48-1.05, dev true accepts
    # 0.02-0.11; 0.25 keeps >= ~2x margin on both sides.
    max_top_share: float = 0.25


DEFAULT_SUPPORT_POLICY = SupportPolicy()

ABSTAIN_CONCENTRATED_EVIDENCE = "ABSTAIN_CONCENTRATED_EVIDENCE"
ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT = "ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT"

FAIL_CONC = "evidence_concentrated"
FAIL_SHORT = "insufficient_temporal_extent"


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def valid_overlap_slice(feat_video: np.ndarray, feat_music: np.ndarray,
                        offset_s: float, sr: int, hop: int):
    """Music-time frame bounds [a, b) where both signals are present for
    the production offset convention (video_time = music_time + O),
    clamped to the actual feature matrices."""
    shift = int(round(offset_s * sr / hop))
    a = max(0, -shift)
    b = min(feat_music.shape[1], feat_video.shape[1] - shift)
    if b - a <= 0:
        return None, shift
    return (a, b), shift


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------


@dataclass
class SupportReport:
    family: str
    method: str
    offset_s: float
    overlap_s: float
    n_bins: int
    active_bins: int
    effective_bins: float
    top_bin_share: Optional[float]
    top_k_share: dict
    peak_bin_start_s: Optional[float]
    total_signed: Optional[float]
    fail_reasons: list = field(default_factory=list)
    passed: Optional[bool] = None

    def as_dict(self):
        return dataclasses.asdict(self)


def concentration_profile(feat_video: np.ndarray, feat_music: np.ndarray,
                          offset_s: float, sr: int = 22050, hop: int = 512,
                          bin_s: float = 1.0):
    """Decompose the net signed correlation at `offset_s` into `bin_s`
    reference-time bins. Returns (bins, t0_s, shift)."""
    (a, b), shift = valid_overlap_slice(feat_video, feat_music, offset_s,
                                        sr, hop)
    if (a, b) is None:
        return None, None, shift
    prod = np.zeros(b - a, dtype=np.float64)
    for band in range(feat_music.shape[0]):
        prod += feat_music[band, a:b] * feat_video[band, a + shift:b + shift]
    n = max(1, int(round(bin_s * sr / hop)))
    n_bins = int(np.ceil((b - a) / n))
    bins = np.array([prod[i * n:(i + 1) * n].sum() for i in range(n_bins)])
    return bins, a * hop / sr, shift


# ---------------------------------------------------------------------------
# the verifier
# ---------------------------------------------------------------------------


def verify_offset(feat_video: np.ndarray, feat_music: np.ndarray,
                  offset_s: float, video_dur_s: float, music_dur_s: float,
                  method: str, family: str, sr: int = 22050, hop: int = 512,
                  policy: SupportPolicy = None) -> SupportReport:
    """Evaluate the temporal distribution of support for `offset_s` under
    one feature representation. Never raises; degenerate geometry yields a
    failing report (the caller abstains)."""
    policy = policy or DEFAULT_SUPPORT_POLICY
    bins, t0, _shift = concentration_profile(
        feat_video, feat_music, offset_s, sr, hop, policy.bin_s)
    overlap_s = float(bins.size) * policy.bin_s if bins is not None else 0.0
    if bins is None or bins.size == 0:
        return SupportReport(
            family=family, method=method, offset_s=offset_s,
            overlap_s=overlap_s, n_bins=0, active_bins=0, effective_bins=0.0,
            top_bin_share=None, top_k_share={}, peak_bin_start_s=None,
            total_signed=None, fail_reasons=[FAIL_SHORT], passed=False)

    total = float(bins.sum())
    scale = float(np.mean(np.abs(bins)))
    active = int(np.sum(np.abs(bins) > 0.10 * scale))
    effective = (float(1.0 / np.sum((bins / total) ** 2))
                 if total > 0 else 0.0)

    def report(top_share, peak_s, reasons):
        order = np.argsort(bins)[::-1]
        top_k = {str(k): float(bins[order[:k]].sum() / total)
                 for k in (1, 2, 3, 5, 8)
                 if total > 0 and k <= bins.size}
        return SupportReport(
            family=family, method=method, offset_s=offset_s,
            overlap_s=overlap_s, n_bins=int(bins.size), active_bins=active,
            effective_bins=effective, top_bin_share=top_share,
            top_k_share=top_k, peak_bin_start_s=peak_s,
            total_signed=total, fail_reasons=reasons,
            passed=not reasons)

    if total <= 0:
        # No net positive evidence for the offset at all: there is no
        # distributed support to point at -> concentrated by definition.
        return report(1.0, None, [FAIL_CONC])

    top_i = int(np.argmax(bins))
    top_share = float(bins[top_i] / total)
    reasons = [FAIL_CONC] if top_share > policy.max_top_share else []
    return report(top_share, t0 + top_i * policy.bin_s, reasons)


def deciding_pcen_method(decision) -> Optional[str]:
    """The pcen_spectral member that supplied the accepted cluster's
    family evidence (highest member peak z inside the cluster)."""
    if decision.offset is None:
        return None
    best_cl, best_z, best_method = None, None, None
    for cl in decision.clusters:
        if abs(cl["offset_s"] - decision.offset) > 1.0:
            continue
        for cand in cl["candidates"]:
            if cand["family"] != "pcen_spectral":
                continue
            if best_z is None or cand["z"] > best_z:
                best_z, best_method = cand["z"], cand["method"]
    return best_method


# ---------------------------------------------------------------------------
# engine-level gate (wrap an AlignmentDecision)
# ---------------------------------------------------------------------------


def gate_decision(decision, feat_video: dict, feat_music: dict,
                  video_dur_s: float, music_dur_s: float,
                  policy: SupportPolicy = None,
                  methods: Optional[list] = None) -> tuple:
    """Apply the temporal-support gate to an Engine v2 decision.

    Only ACCEPTED decisions are affected: the gate can downgrade an accept
    to ABSTAIN, never upgrade anything. By default the verified feature is
    the pcen_spectral member that decided the cluster
    (`deciding_pcen_method`); pass `methods` explicitly to override.
    Returns (decision_like_dict, reports).
    """
    policy = policy or DEFAULT_SUPPORT_POLICY
    d = {
        "status": decision.status,
        "offset": decision.offset,
        "reason_code": decision.reason_code,
        "evidence": dict(decision.evidence),
        "clusters": decision.clusters,
        "policy": decision.policy,
        "runtime_s": decision.runtime_s,
    }
    if decision.status != "accepted" or decision.offset is None:
        return d, []

    if methods is None:
        methods = [deciding_pcen_method(decision) or "pcen"]
    family_of = {"pcen": "pcen_spectral", "pcen_hpss": "pcen_spectral"}
    reports = []
    for method in methods:
        reports.append(verify_offset(
            feat_video[method], feat_music[method], decision.offset,
            video_dur_s, music_dur_s, method,
            family=family_of.get(method, method), policy=policy))

    d["evidence"] = dict(d["evidence"])
    if all(r.passed for r in reports):
        d["evidence"]["temporal_support"] = {
            "verified_method": reports[0].method,
            "top_bin_share": round(reports[0].top_bin_share, 4),
            "effective_bins": round(reports[0].effective_bins, 2),
            "active_bins": reports[0].active_bins,
            "n_bins": reports[0].n_bins,
        }
        return d, reports

    d["status"] = "abstained"
    d["offset"] = None
    kinds = {fr for r in reports for fr in r.fail_reasons}
    d["reason_code"] = (ABSTAIN_CONCENTRATED_EVIDENCE
                        if FAIL_CONC in kinds else
                        ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT)
    d["evidence"]["temporal_support"] = {
        "verified_method": reports[0].method,
        "reports": [r.as_dict() for r in reports],
    }
    return d, reports
