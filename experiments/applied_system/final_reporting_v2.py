"""Versioned paper-facing reporting for the frozen final benchmark (v2).

RESULTS-INTEGRITY-1 reporting-only correction layer.

This module derives NOTHING new from media and reruns NOTHING. It re-reads
the immutable raw comparator records and the frozen benchmark manifest,
rescores them with the unchanged frozen scoring contract
(`experiments/applied_system/scoring.py`), and republishes the same raw
counts under four explicitly distinct metric definitions:

  A. acceptance coverage          = accepts / positive cases
  B. correct-placement yield      = CORRECT_ACCEPT / positive cases
  C. accepted risk                = WRONG_ACCEPT / accepts (positives)
  D. wrong-reference false-accept rate = wrong-ref WRONG_ACCEPT / wrong-ref cases

Why v2 exists (all corrections are reporting-level; no system output,
threshold, pairing, tolerance, or raw count changes):

  1. The frozen artifact's `positive_coverage_*` fields conflate acceptance
     coverage with correct-placement yield. For the always-output baselines
     (GCC-PHAT, NCC) those are radically different: acceptance coverage is
     24/24 = 100% (they never refuse), while correct-placement yield is
     41.7% / 79.2%. The frozen fields were only computed for the two
     selective systems, where the two definitions coincide whenever every
     accept happens to be correct (true here for both, a numerical
     coincidence that must not blur the definitions).
  2. The frozen `accepted_positive_abs_error_s` field is conditional on
     CORRECT_ACCEPT despite its name. v2 names both distributions
     explicitly: `correct_accept_conditional_abs_error_s` and
     `all_produced_accept_abs_error_s` (the latter includes the
     catastrophic WRONG_ACCEPT placements of the always-output baselines).
  3. The frozen `false_accepts_wrong_ref_ci95` is a source-cluster
     bootstrap interval on a resampled COUNT whose denominator varies
     between replicates (source identities contribute unequal numbers of
     dependent takes), so its upper endpoint [27] exceeds the observed
     n=24. That interval is mathematically legitimate internally but is
     not a CI on a fixed n=24 binomial count and is confusing in
     paper-facing text. v2 reports source-cluster bootstrap RATE intervals
     (numerator / resampled denominator inside every replicate), which
     stay in [0, 1] by construction; for this benchmark's deterministic
     wrong-reference behavior they are honestly degenerate ([0, 0] or
     [1, 1]). Exact raw counts are always reported alongside.
  4. Strict-repeat reporting separates decision-state agreement from
     placement movement: for the always-output baselines an
     ACCEPT->ACCEPT "agreement" can hide a ~60 s placement jump (or two
     consistently wrong placements), so agreement alone is never
     repeatability evidence.

Deterministic: the body contains no timestamp and no environment data;
re-running the builder on the same frozen inputs reproduces byte-identical
canonical JSON (asserted by tests). Outputs are versioned NEW files — the
frozen `final_benchmark_results.json` / `.csv`, the raw assembly, and the
original figures are never modified or overwritten.
"""
from __future__ import annotations

import hashlib
import statistics

import numpy as np

from .final_benchmark import (
    ALWAYS_OUTPUT_SYSTEMS,
    BENCH_MANIFEST_PATH,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    FINAL_MARK,
    KDENLIVE_RESULTS_PATH,
    RAW_PATH,
    RESULTS_DIR,
    SCORES_PATH,
    SELECTIVE_SYSTEMS,
    SYSTEM_IDS,
    TOLERANCES,
    _canonical_bytes,
    _load_json,
    _load_raw_records,
    _save_json,
    _sha256_file,
    verify_frozen_artifact,
    write_hash_sidecar,
)
from .scoring import (OUTCOME_CORRECT_ACCEPT, OUTCOME_RUNNER_ERROR,
                      OUTCOME_SAFE_ABSTAIN, OUTCOME_WRONG_ACCEPT,
                      score_pair)

REPORTING_V2_PATH = RESULTS_DIR / "final_benchmark_reporting_v2.json"

METRIC_DEFINITIONS = {
    "acceptance_coverage":
        "accepted placements (CORRECT_ACCEPT + WRONG_ACCEPT) / primary "
        "positive cases; for an ALWAYS_OUTPUT system this is 1.0 by "
        "construction whenever no runner error occurred",
    "correct_placement_yield":
        "CORRECT_ACCEPT / primary positive cases; distinct from acceptance "
        "coverage for any system that accepts wrong placements or refuses",
    "accepted_risk":
        "WRONG_ACCEPT / (CORRECT_ACCEPT + WRONG_ACCEPT) on primary "
        "positives, i.e. among ACCEPTED placements only; refusals are not "
        "in the denominator",
    "wrong_reference_false_accept_rate":
        "wrong-reference WRONG_ACCEPT / wrong-reference cases",
    "wrong_reference_safe_refusal_rate":
        "wrong-reference refusals (SAFE_ABSTAIN/NO_MATCH) / wrong-reference"
        " cases",
    "note":
        "acceptance coverage and correct-placement yield coincide "
        "numerically for RhythmAlign and Panako in this benchmark because "
        "every accept they made was correct; that coincidence does not "
        "merge the definitions",
}

CORRECTIONS_VS_FROZEN = [
    {
        "frozen_field": "selective_risk_metrics.*."
                        "positive_coverage_correct_accepts_100ms / "
                        "positive_coverage_fraction_100ms",
        "problem": "labelled 'coverage' but counts CORRECT_ACCEPTs, i.e. "
                   "correct-placement yield; computed only for the two "
                   "selective systems",
        "v2_replacement": "per_system.*.correct_placement_yield_100ms plus "
                          "the distinct acceptance_coverage_100ms for ALL "
                          "four systems",
    },
    {
        "frozen_field": "error_statistics.*.accepted_positive_abs_error_s",
        "problem": "named 'accepted' but conditioned on CORRECT_ACCEPT only",
        "v2_replacement": "correct_accept_conditional_abs_error_s; the "
                          "companion all_produced_accept_abs_error_s makes "
                          "the catastrophic WRONG_ACCEPT tail visible",
    },
    {
        "frozen_field": "song_level_bootstrap.systems.*."
                        "false_accepts_wrong_ref_ci95 ([21, 27] for GCC/NCC)",
        "problem": "source-cluster bootstrap interval on a resampled COUNT "
                   "with a variable per-replicate denominator; not a CI on "
                   "the observed fixed n=24, and easy to misread that way",
        "v2_replacement": "wrong_ref_false_accept_rate_ci95: rate "
                          "bootstrap, numerator / resampled denominator "
                          "inside every replicate, always within [0, 1]; "
                          "degenerate [1, 1] / [0, 0] here because the "
                          "wrong-reference behavior is deterministic in "
                          "every source resample; exact raw counts are "
                          "reported alongside and remain the primary fact",
    },
    {
        "frozen_field": "strict_repeats.comparisons.*.outcome_agreement",
        "problem": "decision equality alone can present two consistently "
                   "wrong placements, or placements ~60 s apart, as "
                   "'agreement'",
        "v2_replacement": "decision_state_agreement reported jointly with "
                          "placement_move_s and signed_error_difference_s; "
                          "repeatability claims require both",
    },
]


def load_frozen_inputs() -> tuple:
    """Verify and return (manifest_body, records, raw_sha256)."""
    frozen = _load_json(BENCH_MANIFEST_PATH)
    errors = verify_frozen_artifact(frozen)
    if errors:
        raise SystemExit(f"benchmark manifest invalid: {errors}")
    records = _load_raw_records()
    return frozen["body"], records, _sha256_file(RAW_PATH)


def score_rows(manifest_body: dict, records: list) -> list:
    """One row per eligible (case, system), scored at every frozen
    tolerance with the unchanged scoring contract. `outcome` /
    `abs_error_s` are the 100 ms primary view; `outcome_by_tolerance`
    carries the 50/100/150 ms grid."""
    by_key = {(r["system"], r["case_id"]): r for r in records}
    rows = []
    for case in sorted(manifest_body["cases"], key=lambda c: c["case_id"]):
        for system in case["comparator_eligibility"]:
            record = by_key.get((system, case["case_id"]))
            scored = {tol_key: score_pair(case, record, tol)
                      for tol_key, tol in
                      ((f"{tol:g}", tol) for tol in TOLERANCES)}
            primary = scored[f"{0.100:g}"]
            rows.append({
                "case_id": case["case_id"],
                "system": system,
                "pair_type": case["pair_type"],
                "condition": case["condition"],
                "source_slot": case["source_slot"],
                "reliability_only": bool(case.get("reliability_only")),
                "decision": (record or {}).get("decision"),
                "predicted_offset_s": (record or {}).get("predicted_offset_s"),
                "gt_offset_s": case["gt_offset_s"],
                "outcome": primary["outcome"],
                "abs_error_s": primary["abs_error_s"],
                "outcome_by_tolerance":
                    {k: v["outcome"] for k, v in scored.items()},
                "abs_error_by_tolerance":
                    {k: v["abs_error_s"] for k, v in scored.items()},
            })
    return rows


def _subset(rows: list, pair_type: str, primary: bool = True) -> list:
    return [r for r in rows
            if r["pair_type"] == pair_type
            and r["reliability_only"] == (not primary)]


def _iqr_max(values: list) -> dict | None:
    vals = sorted(values)
    if not vals:
        return None
    med = statistics.median(vals)
    if len(vals) > 1:
        q = statistics.quantiles(vals, n=4, method="inclusive")
        iqr = [q[0], q[2]]
    else:
        iqr = [vals[0], vals[0]]
    return {"n": len(vals), "median_s": med, "iqr25_s": iqr[0],
            "iqr75_s": iqr[1], "max_s": vals[-1]}


def reporting_metrics(rows: list, tolerance_s: float = 0.100) -> dict:
    """Raw counts plus the four distinct metric definitions per system,
    at the requested frozen tolerance."""
    tol_key = f"{tolerance_s:g}"
    pos = _subset(rows, "POSITIVE")
    neg = _subset(rows, "WRONG_REFERENCE")

    def outcome(row):
        return row["outcome_by_tolerance"][tol_key]

    per_system = {}
    for system in SYSTEM_IDS:
        p = [r for r in pos if r["system"] == system]
        n = [r for r in neg if r["system"] == system]
        ca = sum(outcome(r) == OUTCOME_CORRECT_ACCEPT for r in p)
        wa = sum(outcome(r) == OUTCOME_WRONG_ACCEPT for r in p)
        accepts = ca + wa
        refusals = sum(outcome(r) == OUTCOME_SAFE_ABSTAIN for r in p)
        runner_errors = sum(outcome(r) == OUTCOME_RUNNER_ERROR
                            for r in p)
        neg_wa = sum(outcome(r) == OUTCOME_WRONG_ACCEPT for r in n)
        neg_ref = sum(outcome(r) == OUTCOME_SAFE_ABSTAIN for r in n)
        per_system[system] = {
            "output_semantics": (
                "ALWAYS_OUTPUT" if system in ALWAYS_OUTPUT_SYSTEMS
                else "SELECTIVE (native ACCEPT/refuse)"),
            "positive_denominator": len(p),
            "positive_correct_accepts": ca,
            "positive_wrong_accepts": wa,
            "positive_accepts": accepts,
            "positive_safe_abstain_no_match": refusals,
            "positive_runner_errors": runner_errors,
            "wrong_ref_denominator": len(n),
            "wrong_ref_wrong_accepts": neg_wa,
            "wrong_ref_safe_refusals": neg_ref,
            "acceptance_coverage_100ms": accepts / len(p) if p else None,
            "correct_placement_yield_100ms": ca / len(p) if p else None,
            "accepted_risk_100ms": (wa / accepts) if accepts else None,
            "accepted_risk_display": f"{wa}/{accepts}",
            "wrong_ref_false_accept_rate_100ms":
                neg_wa / len(n) if n else None,
            "wrong_ref_safe_refusal_rate_100ms":
                neg_ref / len(n) if n else None,
        }
    return {"tolerance_s": tolerance_s, "per_system": per_system}


def error_distributions(rows: list) -> dict:
    """CORRECT_ACCEPT-conditional vs all-produced-accept errors, positives."""
    pos = _subset(rows, "POSITIVE")
    out = {}
    for system in SYSTEM_IDS:
        sub = [r for r in pos if r["system"] == system]
        ca_errs = [r["abs_error_s"] for r in sub
                   if r["outcome"] == OUTCOME_CORRECT_ACCEPT
                   and r["abs_error_s"] is not None]
        prod_errs = [abs(r["predicted_offset_s"] - r["gt_offset_s"])
                     for r in sub
                     if r["decision"] == "ACCEPT"
                     and r["predicted_offset_s"] is not None
                     and r["gt_offset_s"] is not None]
        out[system] = {
            "correct_accept_conditional_abs_error_s": _iqr_max(ca_errs),
            "all_produced_accept_abs_error_s": _iqr_max(prod_errs),
            "conditioning_note":
                "the two distributions are radically different for "
                "ALWAYS_OUTPUT systems: the conditional view hides the "
                "catastrophic WRONG_ACCEPT tail, so every table must state "
                "its conditioning denominator",
        }
    return out


def wrong_reference_magnitudes(records: list) -> dict:
    """|offset| of every produced wrong-reference placement (ALWAYS_OUTPUT
    baselines output confident nonsense; selective systems refuse)."""
    out = {}
    for system in SYSTEM_IDS:
        mags = [abs(r["predicted_offset_s"]) for r in records
                if r["system"] == system
                and r["case_id"].endswith("__wrong_ref")
                and r["decision"] == "ACCEPT"
                and r["predicted_offset_s"] is not None]
        out[system] = _iqr_max(mags)
    return out


def rate_bootstrap(rows: list) -> dict:
    """Source-cluster bootstrap RATE intervals.

    The source slot is the independence unit; resamples draw source slots
    with replacement and compute numerator / resampled denominator inside
    every replicate, so every value lies in [0, 1]. Because source
    identities contribute unequal numbers of dependent takes, resampled
    COUNT intervals (as in the frozen artifact) have a variable denominator
    and are not reported here.
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    pos = _subset(rows, "POSITIVE")
    neg = _subset(rows, "WRONG_REFERENCE")
    slots = sorted({r["source_slot"] for r in pos})
    stats = {s: {"yield": [], "fa_rate": []} for s in SYSTEM_IDS}
    for _ in range(BOOTSTRAP_REPLICATES):
        pick = rng.choice(len(slots), size=len(slots), replace=True)
        for system in SYSTEM_IDS:
            y_num = y_den = f_num = f_den = 0
            for idx in pick:
                slot = slots[idx]
                for r in pos:
                    if r["system"] == system and r["source_slot"] == slot:
                        y_den += 1
                        y_num += r["outcome"] == OUTCOME_CORRECT_ACCEPT
                for r in neg:
                    if r["system"] == system and r["source_slot"] == slot:
                        f_den += 1
                        f_num += r["outcome"] == OUTCOME_WRONG_ACCEPT
            stats[system]["yield"].append(
                y_num / y_den if y_den else np.nan)
            stats[system]["fa_rate"].append(
                f_num / f_den if f_den else np.nan)
    out = {"unit": "source_slot", "replicates": BOOTSTRAP_REPLICATES,
           "seed": BOOTSTRAP_SEED,
           "method": "source-cluster bootstrap RATE: numerator / resampled "
                     "denominator inside every replicate; every value in "
                     "[0, 1]; descriptive aids at 10 source identities, "
                     "never evidence of equivalence or difference",
           "degeneracy_note":
               "wrong-reference behavior is deterministic in every "
               "resample of this benchmark, so these intervals are "
               "honestly degenerate ([0, 0] or [1, 1]); the exact raw "
               "counts remain the primary reported fact",
           "systems": {}}
    for system in SYSTEM_IDS:
        y = np.asarray(stats[system]["yield"], dtype=float)
        f = np.asarray(stats[system]["fa_rate"], dtype=float)
        sub_pos = [r for r in pos if r["system"] == system]
        sub_neg = [r for r in neg if r["system"] == system]
        ca = sum(r["outcome"] == OUTCOME_CORRECT_ACCEPT for r in sub_pos)
        fa = sum(r["outcome"] == OUTCOME_WRONG_ACCEPT for r in sub_neg)
        out["systems"][system] = {
            "correct_placement_yield_100ms_point": ca / len(sub_pos),
            "correct_placement_yield_100ms_ci95":
                [float(np.nanpercentile(y, 2.5)),
                 float(np.nanpercentile(y, 97.5))],
            "wrong_ref_false_accept_rate_point": fa / len(sub_neg),
            "wrong_ref_false_accept_rate_ci95":
                [float(np.nanpercentile(f, 2.5)),
                 float(np.nanpercentile(f, 97.5))],
            "exact_raw_counts": {
                "positives": len(sub_pos), "correct_accepts": ca,
                "wrong_ref": len(sub_neg), "wrong_ref_wrong_accepts": fa,
            },
        }
    return out


def strict_repeat_reporting(records: list, manifest_body: dict) -> dict:
    """Decision-state agreement and placement movement as separate metrics.

    ACCEPT->ACCEPT is not repeatability evidence when the placement moves
    by tens of seconds, or when both placements are wrong; n=2 repeats are
    never overstated.
    """
    by_key = {(r["system"], r["case_id"]): r for r in records}
    cases = {c["case_id"]: c for c in manifest_body["cases"]}
    comparisons = []
    for repeat, original in (("repeat01", "final01"),
                             ("repeat02", "final02")):
        for system in SYSTEM_IDS:
            rep = by_key.get((system, f"{repeat}__positive"))
            orig = by_key.get((system, f"{original}__positive"))
            rep_gt = cases[f"{repeat}__positive"]["gt_offset_s"]
            orig_gt = cases[f"{original}__positive"]["gt_offset_s"]
            entry = {
                "comparison": f"{repeat} vs {original}",
                "system": system,
                "original_decision": (orig or {}).get("decision"),
                "repeat_decision": (rep or {}).get("decision"),
                "decision_state_agreement":
                    (orig or {}).get("decision") == (rep or {}).get("decision"),
            }
            if (rep and orig
                    and rep.get("decision") == "ACCEPT"
                    and orig.get("decision") == "ACCEPT"
                    and rep.get("predicted_offset_s") is not None
                    and orig.get("predicted_offset_s") is not None):
                rep_err = rep["predicted_offset_s"] - rep_gt
                orig_err = orig["predicted_offset_s"] - orig_gt
                orig_abs, rep_abs = abs(orig_err), abs(rep_err)
                entry["placement_move_s"] = abs(
                    rep["predicted_offset_s"] - orig["predicted_offset_s"])
                entry["signed_error_difference_s"] = rep_err - orig_err
                entry["original_placement_abs_error_s"] = orig_abs
                entry["repeat_placement_abs_error_s"] = rep_abs
                if orig_abs <= 0.100 and rep_abs <= 0.100:
                    interp = ("decision states and placements agree; both "
                              "takes correct at 100 ms")
                elif orig_abs > 0.100 and rep_abs > 0.100:
                    interp = ("decision states agree but placements are "
                              "consistently wrong at both takes; decision "
                              "agreement is not correctness")
                else:
                    interp = ("decision states agree while one take is "
                              "placed correctly and the other "
                              "catastrophically wrong; decision agreement "
                              "alone is not repeatability evidence")
                if entry["placement_move_s"] > 1.0:
                    interp += (f" (placement moved "
                               f"{entry['placement_move_s']:.1f} s between "
                               "near-identical takes)")
                entry["interpretation"] = interp
            elif entry["decision_state_agreement"] is False:
                entry["interpretation"] = (
                    "the system refused the repeat of a take it had "
                    "accepted (or the reverse); decision-state instability")
            comparisons.append(entry)
    return {
        "note": ("reliability evidence only, never in primary counts; n=2 "
                 "repeats are not overstated: decision-state agreement and "
                 "placement movement are separate metrics"),
        "comparisons": comparisons,
    }


def kdenlive_projection() -> dict:
    """Existing frozen Kdenlive results, projected with explicit
    denominators. Nothing is rescored; no automated-system pooling."""
    body = _load_json(KDENLIVE_RESULTS_PATH)["body"]
    agg = body["aggregates"]
    counts = agg["primary_counts_at_100ms"]
    return {
        "source_artifact": "results/final_kdenlive_results.json (frozen, "
                           "hash-sidecarred; read-only here)",
        "scoring_pairs": body["valid_scoring_pairs"],
        "correct_accepts_100ms": counts["CORRECT_ACCEPT"],
        "wrong_accepts_100ms": counts["WRONG_ACCEPT"],
        "native_failures": counts["NATIVE_FAILURE"],
        "correct_placement_yield_100ms":
            counts["CORRECT_ACCEPT"] / body["valid_scoring_pairs"],
        "operator_time": {
            "timed_runs": agg["operator_time"]["timed_runs"],
            "of_valid_runs": body["valid_scoring_pairs"],
            "untimed": agg["operator_time"]["untimed_runs"],
            "never_imputed": True,
            "median_s": agg["operator_time"]["median_s"],
            "iqr25_s": agg["operator_time"]["iqr25_s"],
            "iqr75_s": agg["operator_time"]["iqr75_s"],
            "total_s": agg["operator_time"]["total_s"],
        },
        "void_run_preserved": body["exclusions"]["pair01_run1"],
        "exclusions": body["exclusions"],
        "corrections_outcome_independent": (
            "pair01 V2 placement (00:03:00 headroom) and the XML parser v2 "
            "are documented, evidence-preserving, outcome-independent "
            "implementation/procedure corrections applied uniformly before "
            "any scoring; original failure evidence preserved verbatim"),
    }


def build_v2_body() -> dict:
    manifest_body, records, raw_sha = load_frozen_inputs()
    rows = score_rows(manifest_body, records)
    original_scores_sha = _sha256_file(SCORES_PATH)
    return {
        "status": "FINAL_BENCHMARK_REPORTING_V2",
        "final_confirmatory_evidence": FINAL_MARK,
        "not_pilot_not_development": True,
        "purpose": ("deterministic reporting-level corrections only; no "
                    "system output, threshold, pairing, tolerance, or raw "
                    "count is changed; the frozen raw assembly and the "
                    "original final results remain the immutable "
                    "authority"),
        "authority": {
            "raw_assembly_sha256": raw_sha,
            "raw_assembly_path": "results/final_comparator_raw.json",
            "original_final_results_sha256": original_scores_sha,
            "original_final_results_path":
                "results/final_benchmark_results.json",
            "manifest_freeze_sha256": _load_json(BENCH_MANIFEST_PATH)[
                "freeze_hash"],
            "scoring_module": ("experiments/applied_system/scoring.py "
                               "(frozen contract, unchanged)"),
        },
        "metric_definitions": METRIC_DEFINITIONS,
        "corrections_vs_frozen_artifact": CORRECTIONS_VS_FROZEN,
        "reporting_metrics_100ms": reporting_metrics(rows, 0.100),
        "counts_by_tolerance": {
            f"{tol:g}": reporting_metrics(rows, tol)["per_system"]
            for tol in TOLERANCES
        },
        "error_distributions_positives": error_distributions(rows),
        "wrong_reference_output_magnitudes_abs_s":
            wrong_reference_magnitudes(records),
        "rate_bootstrap": rate_bootstrap(rows),
        "strict_repeats": strict_repeat_reporting(records, manifest_body),
        "kdenlive_stratum": kdenlive_projection(),
    }


def write_reporting_v2() -> dict:
    """Build, write (once), and sidecar the v2 artifact.

    Deterministic: the body contains no timestamp, so re-running on the
    same frozen inputs reproduces byte-identical canonical JSON.
    """
    body = build_v2_body()
    digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    wrapped = {"reporting_v2_sha256": digest, "body": body}
    if REPORTING_V2_PATH.exists():
        current = _load_json(REPORTING_V2_PATH)
        if current != wrapped:
            raise RuntimeError(
                "v2 reporting artifact already exists with different "
                f"content: {REPORTING_V2_PATH}")
        return current
    _save_json(REPORTING_V2_PATH, wrapped)
    write_hash_sidecar(REPORTING_V2_PATH)
    return wrapped


# ---------------------------------------------------------------------------
# versioned figures (new files; the frozen figures are never overwritten)
# ---------------------------------------------------------------------------


def build_v2_figures() -> list:
    """Two corrected-label figures. Figure 1 renames the frozen
    'accepted placements below 25 ms' plot to what it actually shows
    (CORRECT_ACCEPT-conditional errors). Figure 2 makes the catastrophic
    WRONG_ACCEPT tail of produced placements visible on a log axis."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    body = write_reporting_v2()["body"]
    rows = score_rows(*load_frozen_inputs()[:2])
    pos = _subset(rows, "POSITIVE")

    label = {"rhythmalign_v1_2_0": "RhythmAlign v1.2.0",
             "gcc_phat_argmax_v1": "GCC-PHAT argmax",
             "ncc_argmax_v1": "NCC argmax",
             "panako_fingerprint": "Panako OLAF"}
    order = ["rhythmalign_v1_2_0", "ncc_argmax_v1", "gcc_phat_argmax_v1",
             "panako_fingerprint"]
    written = []

    # 1 — CORRECT_ACCEPT-conditional placement errors (honest label)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for yi, s in enumerate(order[::-1]):
        errs = sorted(r["abs_error_s"] for r in pos
                      if r["system"] == s
                      and r["outcome"] == OUTCOME_CORRECT_ACCEPT
                      and r["abs_error_s"] is not None)
        ax.scatter([e * 1000 for e in errs], [yi] * len(errs),
                   s=28, alpha=0.75)
    ax.axvline(50, color="#888", lw=0.6, linestyle=":")
    ax.set_yticks(range(len(order)),
                  [label[order[::-1][i]] for i in range(len(order))],
                  fontsize=9)
    ax.set_xlabel("CORRECT_ACCEPT |offset error| (ms) — conditioning: "
                  "correct accepts only; WRONG_ACCEPT placements are "
                  "excluded from this panel and shown in "
                  "final_produced_placement_errors_v2.png")
    ax.set_title("Correct-accept placement errors at 100 ms "
                 "(dots = cases; dashed line = 50 ms)", fontsize=10)
    fig.tight_layout()
    path = RESULTS_DIR / "figures" / "final_correct_accept_errors_v2.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)

    # 2 — ALL produced placements on a log axis (catastrophic tail visible)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for yi, s in enumerate(order[::-1]):
        sub = [r for r in pos if r["system"] == s
               and r["decision"] == "ACCEPT"
               and r["predicted_offset_s"] is not None]
        errs = [abs(r["predicted_offset_s"] - r["gt_offset_s"]) * 1000
                for r in sub]
        ca = [r["abs_error_s"] * 1000 for r in sub
              if r["outcome"] == OUTCOME_CORRECT_ACCEPT]
        wa = [e for e in errs if e > 100.0]
        ax.scatter(ca, [yi] * len(ca), s=28, alpha=0.75, color="#2a7f2a",
                   label="CORRECT_ACCEPT" if yi == len(order) - 1 else None)
        ax.scatter(wa, [yi] * len(wa), s=28, alpha=0.75, color="#b2182b",
                   marker="x", label="WRONG_ACCEPT (produced)"
                   if yi == len(order) - 1 else None)
    ax.set_xscale("log")
    ax.set_yticks(range(len(order)),
                  [label[order[::-1][i]] for i in range(len(order))],
                  fontsize=9)
    ax.set_xlabel("ALL produced placements |offset error| (ms, log scale) "
                  "— conditioning: every ACCEPT, correct or wrong")
    ax.set_title("Produced placement errors at 100 ms: correct accepts vs "
                 "catastrophic wrong accepts", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    path = (RESULTS_DIR / "figures"
            / "final_produced_placement_errors_v2.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)
    return written
