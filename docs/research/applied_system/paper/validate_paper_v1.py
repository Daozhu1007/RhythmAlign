"""Read-only paper/evidence checks for PAPER-DRAFT-1; --write-tables writes only PAPER_TABLES_V1.md.

No comparator imports, audio access, aggregation reruns, or frozen-file writes.
Values below project existing sealed summaries (reporting v2, the immutable
final-results artifact, and the corrected gcc_phat_v2_lagfix results) into
manuscript displays, and enforce the revision-1 gate: corrected GCC comparator,
NCC overlap-contract disclosure, no causal-abstention claim, no "catastrophic"
outcome class, no workflow-safety claim, resolved citation TODOs, public
evaluation-framework prior art, scoped reproducibility, and untouched frozen
evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACK = ROOT / "experiments/applied_system/final_pack"
RESULTS = PACK / "results"
BASE = "8940cc4"  # revision-1 starting HEAD; frozen evidence must be untouched since
SR = 48000
SYSTEMS = {
    "rhythmalign_v1_2_0": "RhythmAlign v1.2.0",
    "gcc_phat_argmax_v2_lagfix": "GCC-PHAT argmax (v2 lagfix)",
    "ncc_argmax_v1": "NCC argmax (unconstrained)",
    "panako_fingerprint": "Panako OLAF",
}
CONDITIONS = ["ORDINARY", "LOW_LEVEL", "TAP_DOMINANT", "INTERFERENCE",
              "PARTIAL", "DEVICE_VARIATION"]
TITLE = "Benchmarking Selective Reference-Audio Alignment on Controlled Acoustic Rerecordings"
NCC_CONTRACT_SENTENCE = (
    "NCC remains an unconstrained argmax control. Its five wrong positive "
    "placements occurred at short edge overlaps that RhythmAlign's frozen "
    "candidate policy excludes; therefore the comparison reflects both "
    "estimator and candidate-policy differences and does not isolate the "
    "causal value of abstention."
)
# Overlap geometry recomputed from frozen NCC lag_samples + manifest lengths
# (pinned by tests/test_comparator_integrity_audit.py and the NCC audit).
NCC_WRONG_OVERLAPS = {"final02": 1.675, "final18": 1.234, "final19": 3.589,
                      "final20": 3.522, "final23": 4.694}
MIN_CORRECT_OVERLAP_S = 60.414


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


V2 = read_json(RESULTS / "final_benchmark_reporting_v2.json")["body"]
FROZEN = read_json(RESULTS / "final_benchmark_results.json")["body"]
MANIFEST = read_json(RESULTS / "final_benchmark_manifest.json")["body"]
KDENLIVE = read_json(RESULTS / "final_kdenlive_results.json")["body"]
GCCV2 = read_json(RESULTS / "gcc_phat_v2_lagfix_results.json")
GCCMAN = read_json(RESULTS / "gcc_phat_v2_lagfix_correction_manifest.json")["body"]
METRICS = V2["reporting_metrics_100ms"]["per_system"]
GCC_METRICS = METRICS["gcc_phat_argmax_v1"]  # scored counts identical under v2 lagfix (asserted)


def table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(map(str, row)) + " |" for row in rows),
    ])


def fraction(n, d):
    percent = f"{100 * n / d:.1f}".removesuffix(".0")
    return f"{n}/{d} ({percent}%)"


def iqr_max(values):
    vals = sorted(values)
    q = statistics.quantiles(vals, n=4, method="inclusive")
    return {"n": len(vals), "median_s": statistics.median(vals),
            "iqr25_s": q[0], "iqr75_s": q[2], "max_s": vals[-1]}


def gcc_v2_positive_cases():
    return [c for c in GCCV2["per_case"]
            if c["pair_type"] == "POSITIVE" and c["case_id"].startswith("final")]


def gcc_v2_distributions():
    cases = gcc_v2_positive_cases()
    produced = [c["abs_errors"]["0.10"] for c in cases]
    correct = [c["abs_errors"]["0.10"] for c in cases
               if c["outcomes"]["0.10"] == "CORRECT_ACCEPT"]
    wrong_refs = [abs(c["v2_predicted_offset_s"]) for c in GCCV2["per_case"]
                  if c["pair_type"] == "WRONG_REFERENCE"]
    return iqr_max(produced), iqr_max(correct), iqr_max(wrong_refs)


def main_table():
    metrics = dict(METRICS)
    metrics["gcc_phat_argmax_v2_lagfix"] = GCC_METRICS
    rows = []
    for key, name in SYSTEMS.items():
        m = metrics[key]
        rows.append([name,
                     fraction(m["positive_accepts"], m["positive_denominator"]),
                     fraction(m["positive_correct_accepts"], m["positive_denominator"]),
                     fraction(m["positive_wrong_accepts"], m["positive_accepts"]),
                     fraction(m["wrong_ref_wrong_accepts"], m["wrong_ref_denominator"])])
    return table(["System", "Acceptance coverage", "Correct-placement yield",
                  "Positive-case accepted error rate", "Wrong-ref false accept"], rows)


def paired_tables():
    disc = FROZEN["discordant_counts_vs_rhythmalign"]
    key_map = {"gcc_phat_argmax_v1": "gcc_phat_argmax_v2_lagfix",
               "ncc_argmax_v1": "ncc_argmax_v1", "panako_fingerprint": "panako_fingerprint"}
    pos_rows, neg_rows = [], []
    for frozen_key, key in key_map.items():
        p = disc[frozen_key]["positives_100ms"]
        only = p[f"{frozen_key}_only"]
        pos_rows.append([SYSTEMS[key], p["both_correct_accept"], only,
                         p["rhythmalign_only"], p["neither"]])
        w = disc[frozen_key]["wrong_reference_100ms"]
        neg_rows.append([SYSTEMS[key], w["both_safe"], w[f"{frozen_key}_wrong_accept_only"],
                         w["rhythmalign_wrong_accept_only"], w["both_wrong_accept"]])
    pos = table(["Comparator", "Both correct", "Comparator-only correct",
                 "RhythmAlign-only correct", "Neither"], pos_rows)
    neg = table(["Comparator", "Both refused/no-match", "Comparator wrong-accept only",
                 "RhythmAlign wrong-accept only", "Both wrong accepts"], neg_rows)
    return pos, neg


def render_tables():
    cases = MANIFEST["cases"]
    positives = [c for c in cases if c["pair_type"] == "POSITIVE" and c["primary"]]
    rows = []
    for condition in CONDITIONS:
        group = [c for c in positives if c["condition"] == condition]
        rows.append([condition, len(group), ", ".join(sorted({c["source_slot"] for c in group})),
                     "Primary EXACT_GT"])
    rows.extend([
        ["Primary positives total", len(positives), "10 source identities", "Dependent within source"],
        ["Constructed wrong references", MANIFEST["counts"]["wrong_reference"],
         "Same primary recordings", "NO_MATCH; directed, frozen take-index rotation"],
        ["Strict repeats", MANIFEST["counts"]["strict_repeats"], "S01, S02", "Separate from primary counts"],
        ["Kdenlive positive pairs", V2["kdenlive_stratum"]["scoring_pairs"],
         "Selected primary takes", "Separate technical stratum; no negative arm"],
    ])
    composition = table(["Component", "n", "Sources / inputs", "Role"], rows)
    produced, correct, wrong_refs = gcc_v2_distributions()
    errors = []
    for key, name in SYSTEMS.items():
        entries = []
        if key == "gcc_phat_argmax_v2_lagfix":
            entries = [(correct, "CORRECT_ACCEPT only", 1000, "ms", 2),
                       (produced, "All produced positive placements", 1, "s", 4)]
        else:
            dist = V2["error_distributions_positives"][key]
            entries = [(dist["correct_accept_conditional_abs_error_s"], "CORRECT_ACCEPT only", 1000, "ms", 2),
                       (dist["all_produced_accept_abs_error_s"], "All produced positive placements", 1, "s", 4)]
        for d, label, scale, unit, precision in entries:
            fmt = lambda x: f"{scale * x:.{precision}f}"
            errors.append([name, label, d["n"], unit, fmt(d["median_s"]),
                           f"{fmt(d['iqr25_s'])}–{fmt(d['iqr75_s'])}", fmt(d["max_s"])])
    error_table = table(["System", "Conditioning", "n", "Unit", "Median absolute error",
                         "IQR", "Maximum"], errors)
    condition_rows = []
    for condition in CONDITIONS:
        counts = FROZEN["condition_level_100ms"][condition]
        n = sum(counts["rhythmalign_v1_2_0"].values())
        triple = lambda c: "/".join(str(c.get(k, 0)) for k in
                                    ["CORRECT_ACCEPT", "WRONG_ACCEPT", "SAFE_ABSTAIN"])
        condition_rows.append([condition, n, triple(counts["rhythmalign_v1_2_0"]),
                               triple(counts["gcc_phat_argmax_v1"]), triple(counts["ncc_argmax_v1"]),
                               triple(counts["panako_fingerprint"])])
    condition_table = table(["Condition", "n", "RhythmAlign v1.2.0", "GCC-PHAT argmax (v2 lagfix)",
                             "NCC argmax (unconstrained)", "Panako OLAF"], condition_rows)
    source_rows = []
    for slot, counts in FROZEN["source_level_100ms"].items():
        pos = counts["primary_positives"]
        triple = lambda c: "/".join(str(c.get(k, 0)) for k in
                                    ["CORRECT_ACCEPT", "WRONG_ACCEPT", "SAFE_ABSTAIN"])
        source_rows.append([slot, sum(pos["rhythmalign_v1_2_0"].values()),
                            triple(pos["rhythmalign_v1_2_0"]), triple(pos["gcc_phat_argmax_v1"]),
                            triple(pos["ncc_argmax_v1"]), triple(pos["panako_fingerprint"])])
    source_table = table(["Source", "Primary n", "RhythmAlign v1.2.0", "GCC-PHAT argmax (v2 lagfix)",
                          "NCC argmax (unconstrained)", "Panako OLAF"], source_rows)
    k = V2["kdenlive_stratum"]
    t = k["operator_time"]
    ksummary = table(["Quantity", "Observed value", "Denominator / scope"], [
        ["CORRECT_ACCEPT", k["correct_accepts_100ms"], f"{k['scoring_pairs']} valid positive pairs"],
        ["WRONG_ACCEPT", k["wrong_accepts_100ms"], "10 valid positive pairs"],
        ["Native failures", k["native_failures"], "10 valid positive pairs"],
        ["Timed runs", t["timed_runs"], "10 valid runs; pair01r2 missing, never imputed"],
        ["Operator-time median", f"{t['median_s']:.1f} s", "9 timed runs"],
        ["Operator-time IQR", f"{t['iqr25_s']:.1f}–{t['iqr75_s']:.1f} s", "9 timed runs"],
        ["Operator-time total", f"{t['total_s']:.1f} s", "9 timed runs"],
    ])
    krows = []
    for r in KDENLIVE["per_pair"]:
        elapsed = r["operator_elapsed_seconds"]
        krows.append([r["canonical_pair"], r["scoring_run"], r["take"], r["condition"],
                      r["outcome_by_tolerance_s"]["0.1"], f"{r['abs_error_s']:.6f}",
                      "Missing" if elapsed is None else f"{elapsed:.3f}"])
    ktable = table(["Pair", "Scoring run", "Take", "Condition", "Outcome at 100 ms",
                    "Absolute error (s)", "Operator time (s)"], krows)
    repeat_rows = []
    names = dict(SYSTEMS)
    names["gcc_phat_argmax_v1"] = "GCC-PHAT argmax (v2 lagfix)"
    for c in V2["strict_repeats"]["comparisons"]:
        move = c.get("placement_move_s")
        delta = c.get("signed_error_difference_s")
        orig = c.get("original_placement_abs_error_s")
        rep = c.get("repeat_placement_abs_error_s")
        repeat_rows.append([c["comparison"], names[c["system"]],
                            f"{c['original_decision']} → {c['repeat_decision']}",
                            "Yes" if c["decision_state_agreement"] else "No",
                            "—" if move is None else f"{move:.4f}",
                            "—" if delta is None else f"{1000 * delta:+.2f}",
                            "—" if orig is None else f"{orig:.6f}",
                            "—" if rep is None else f"{rep:.6f}"])
    repeat_table = table(["Comparison", "System", "Native states", "State agreement",
                          "Absolute output movement (s)", "Signed error change (ms)",
                          "Original absolute error (s)", "Repeat absolute error (s)"], repeat_rows)
    paired_pos, paired_neg = paired_tables()
    return f"""# Paper Tables V1

STATUS: TECHNICAL-CORE TABLES V1 — revised after comparator-integrity review; sealed benchmark evidence; creator pilot NOT_CONDUCTED.

Numeric authority: [reporting v2](../../../../experiments/applied_system/final_pack/results/final_benchmark_reporting_v2.json) (V2) for all systems, plus the corrected [gcc_phat_v2_lagfix_results.json](../../../../experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_results.json) (G2) and its frozen correction manifest for the valid GCC comparator. Composition uses the frozen benchmark/acquisition manifests; condition, source, and paired panels use only raw counts in the immutable original final-results artifact (F), never its obsolete coverage fields. Kdenlive per-pair detail uses its frozen result artifact (K). All tables are projections of stored evidence, not new performance analyses. Fractions retain exact denominators; displayed decimals are rounded.

## Table 1 — Benchmark composition

{composition}

Acquisition: 3 sessions, 2 rooms, 2 recording devices; 26/26 captures GT_VALID (24 primary + 2 repeats). Sources are the independence unit; primary takes and reused wrong-reference recordings are dependent. Exactly 3 source identities were preflagged for repetitive structure. The four interference takes (final17–final20) produced trimmed inputs of approximately 136.9–139.3 s versus approximately 62.9–68.7 s for the other primary takes (frozen lengths in the correction manifest; reason not documented in the acquisition record). Per-take drift QC assigns final21–final22 to D1 (SESSION_2, ROOM_A); only final17–final20 and final23–final24 used D2. Optional authentic-handcam, version-mismatch, external-domain, and creator-pilot evidence is not included. Source: frozen manifests, FINAL_SOURCE_SELECTION.md, FINAL_ACQUISITION_QC.md, gcc_phat_v2_lagfix_correction_manifest.json.

## Table 2 — Main system results

100 ms primary correctness tolerance. First three metrics: primary positives only. Last metric: constructed wrong references only. Kdenlive has a separate denominator (Table 5). GCC-PHAT = corrected `gcc_phat_argmax_v2_lagfix` (original v1 evidence preserved as defective-implementation evidence; scored counts identical). NCC = unconstrained full-lag argmax (no minimum-overlap requirement). RhythmAlign minimum usable overlap = 30 s.

{main_table()}

Acceptance coverage = accepts / positives; correct-placement yield = correct accepts / positives; positive-case accepted error rate = wrong positive accepts / all positive accepts. Acceptance coverage and correct-placement yield coincide for RhythmAlign and Panako here only because their observed positive accepts were all correct. GCC-PHAT and NCC always output. Source: V2.body.reporting_metrics_100ms.per_system with GCC counts asserted equal to G2 per-case recomputation. Counts are unchanged at 50/100/150 ms (V2.body.counts_by_tolerance; G2.summary_outcome_counts_by_tolerance).

## Table 3 — Placement error

Positive placements only. The conditioning and unit columns are essential: successful-case errors in milliseconds and all-produced errors in seconds describe different distributions. Refusals produce no offset and are not assigned zero error. GCC-PHAT rows are recomputed from the corrected v2 lagfix records (G2 per-case; the frozen inclusive-quartile method reproduces the stored V2 distributions for the lag-identical records).

{error_table}

Every CORRECT_ACCEPT placement was below 25 ms. This does not describe every accepted placement. In particular, the all-produced NCC median remains small while its maximum reveals a large wrong-placement tail. Wrong-reference outputs have no true timing target and are excluded from these error distributions. Source: V2.body.error_distributions_positives; G2 per-case records for GCC-PHAT.

## Table 4 — Condition-level raw counts

Each system cell is **CORRECT_ACCEPT / WRONG_ACCEPT / refusal**, as three counts, not a fraction. Refusal means native ABSTAIN for RhythmAlign and NO_MATCH for Panako. No subgroup inference.

{condition_table}

Source: F.body.condition_level_100ms. Row totals equal n for every system and sum to the Table 2 numerator counts.

**Source-level companion panel.** The same count convention applies; these are the ten independence units, not ten further observations.

{source_table}

Source: F.body.source_level_100ms. On wrong references, each source has the same denominator as its primary n: RhythmAlign and Panako refuse every case; GCC-PHAT and NCC accept every case. The four RhythmAlign positive refusals are final08/final18 (S08) and final20/final24 (S10). S08, S09, and S10 were preflagged repetitive; concentration on S08/S10 is descriptive, not causal.

## Table 5 — Kdenlive technical stratum

Kdenlive 26.08.1; one owner/operator; 10 selected positives across 7 source identities; one editor version; positive-only (no wrong-reference arm); not a usability comparison. The scoped reading: the native command did not reliably recover placement on this selected technical stratum.

{ksummary}

{ktable}

Source: V2.body.kdenlive_stratum for summaries; K.body.per_pair for individual errors/times. Counts are identical at 50/100/150 ms. Original pair01 V1 is void evidence only; pair01r2 is its scored replacement under the uniform 180 s headroom procedure. Original failure evidence and the outcome-independent XML correction remain preserved. Pair01r2 timing is missing, not zero, and the void run's time is not substituted. Correct pair02/pair10 errors round to 5.3/0.1 ms; eight wrong errors range from approximately 0.85 to 149.4 s.

## Table 6 — Strict-repeat observations

Only two repeat takes, excluded from primary counts. Absolute output movement is |offset_repeat − offset_original|. Signed error change is (offset_repeat − GT_repeat) − (offset_original − GT_original). Different recording starts change GT; raw movement alone is not repeatability. Dashes mean values not supplied in V2 for Panako's refusal comparisons: the originals were accepted, but no repeat placement or paired timing change exists. The GCC rows' underlying records (final01, final02, repeat01, repeat02) are lag-identical under the v2 lagfix correction, so this table holds unchanged for the valid comparator (asserted by the paper checker).

{repeat_table}

Source: V2.body.strict_repeats.comparisons. RhythmAlign's +7.8/+14.0 ms figures are changes in signed error, not raw output movement. GCC-PHAT repeat01 is consistently wrong. On repeat02, GCC-PHAT changes correct → wrong and NCC wrong → correct despite ACCEPT → ACCEPT in both cases; their raw movements are approximately 67.2 and 60.5 s. Panako refuses both repeats after accepting their originals. These are observations, not reliability rates.

## Table 7 — Paired outcomes versus RhythmAlign (primary positives, 100 ms)

Frozen per-case discordance counts (F.body.discordant_counts_vs_rhythmalign), reported to prevent reading 20/24 versus 19/24 as broad dominance. Dependent within-source observations; no significance test is performed.

{paired_pos}

Wrong-reference pairing over the same 24 constructed pairs:

{paired_neg}

**NCC overlap contract panel.** The five NCC wrong positives occur at usable overlaps of {", ".join(f"{v:.3f} s ({k})" for k, v in NCC_WRONG_OVERLAPS.items())} — approximately 1.2–4.7 s — all below RhythmAlign's 30 s minimum-overlap threshold, while all 19 NCC correct positives sit at {MIN_CORRECT_OVERLAP_S:.3f} s or more; the 30 s line falls in the empty middle. RhythmAlign's edge-lag guard alone excludes all five placements. Source: NCC_OVERLAP_CONTRACT_AUDIT.md; recomputed by the paper checker from frozen NCC lag_samples and correction-manifest lengths (pinned by tests/test_comparator_integrity_audit.py).
"""


def abstract_expected():
    ra, gcc, ncc, pan = (GCC_METRICS if k.startswith("gcc") else METRICS[k]
                         for k in SYSTEMS)
    n = ra["positive_denominator"]
    sources = len({c["source_slot"] for c in MANIFEST["cases"]})
    kd = V2["kdenlive_stratum"]
    return [
        "Replacing degraded captured audio in user-generated video with a clean reference requires both accurate timing and a decision about whether a proposed placement is supported.",
        "We benchmark frozen RhythmAlign v1.2.0, a selective reference-audio alignment system, on controlled acoustic rerecordings under rhythm-game handcam-style stress-test conditions.",
        f"A performance-blind source-selection and dual-marker timing protocol produced {n} dependent positive takes from {sources} source identities and {ra['wrong_ref_denominator']} constructed wrong-reference pairs; no thresholds were tuned on final data.",
        f"At a {1000 * V2['reporting_metrics_100ms']['tolerance_s']:.0f} ms correctness tolerance, RhythmAlign achieved {ra['positive_correct_accepts']}/{n} correct-placement yield with four abstentions, {ra['positive_wrong_accepts']} wrong positive accepts, and {ra['wrong_ref_wrong_accepts']}/{ra['wrong_ref_denominator']} wrong-reference false accepts.",
        f"The always-output correlation controls accepted every case: corrected GCC-PHAT (`gcc_phat_argmax_v2_lagfix`) produced {gcc['positive_correct_accepts']}/{n} correct positive placements and {gcc['positive_wrong_accepts']} wrong, and normalized cross-correlation produced {ncc['positive_correct_accepts']}/{n} correct and {ncc['positive_wrong_accepts']} wrong; each accepted all {gcc['wrong_ref_wrong_accepts']} wrong references.",
        f"The five NCC wrong positives occurred at 1.2–{max(NCC_WRONG_OVERLAPS.values()):.1f} s edge overlaps that RhythmAlign's frozen 30 s minimum-overlap candidate policy excludes, so this comparison reflects complete system contracts, not the causal effect of abstention.",
        f"Panako under native shipped OLAF settings achieved {pan['positive_correct_accepts']}/{n} correct-placement yield with {pan['wrong_ref_wrong_accepts']}/{pan['wrong_ref_denominator']} wrong-reference false accepts.",
        f"A separate single-operator Kdenlive technical stratum recovered {kd['correct_accepts_100ms']}/{kd['scoring_pairs']} placements.",
        "These observations concern one domain, one frozen operating point, and controlled rather than field-sampled rerecordings; they are not calibrated future risk or creator workflow benefit.",
        "The evaluated systems differed primarily in unsupported-placement behavior, and the cost of recovering from refusal remains unmeasured.",
    ]


def v1_files():
    return {name: (HERE / name).read_text(encoding="utf-8") for name in [
        "PAPER_DRAFT_V1.md", "PAPER_TABLES_V1.md", "CLAIM_LEDGER_V1.md",
        "CITATION_LEDGER_V1.md", "CITATION_GAPS_V1.md", "HOSTILE_REVIEW_RESPONSE_V1.md"]}


def validate():
    files = v1_files()
    draft, tables, ledger = files["PAPER_DRAFT_V1.md"], files["PAPER_TABLES_V1.md"], files["CLAIM_LEDGER_V1.md"]
    assert tables == render_tables(), "Paper table drift from sealed summaries"
    # Main table in the prose has alignment colons; cell content must match.
    normalize = lambda s: re.sub(r"(?m)^\|[-: |]+\|$", "", s).strip()
    actual = draft.split("| System | Acceptance coverage", 1)[1].split("\n\n", 1)[0]
    assert normalize("| System | Acceptance coverage" + actual) == normalize(main_table())

    # --- GCC v2 comparator integrity (revision gate) ---
    cases = gcc_v2_positive_cases()
    produced, correct, wrong_refs = gcc_v2_distributions()
    assert len(cases) == 24
    assert produced["n"] == 24 and correct["n"] == GCC_METRICS["positive_correct_accepts"]
    assert wrong_refs["n"] == 24
    assert abs(produced["max_s"] - 113.1878125) < 1e-6, produced["max_s"]
    assert abs(produced["median_s"] - 29.31346875) < 1e-9
    stored_gcc = V2["error_distributions_positives"]["gcc_phat_argmax_v1"]
    assert correct == stored_gcc["correct_accept_conditional_abs_error_s"]  # unchanged by the fix
    stored_wr = V2["wrong_reference_output_magnitudes_abs_s"]["gcc_phat_argmax_v1"]
    assert abs(wrong_refs["median_s"] - stored_wr["median_s"]) < 1e-9 and wrong_refs["max_s"] == stored_wr["max_s"]
    assert sorted(c["case_id"] for c in GCCV2["per_case"] if c["lag_changed_by_correction"]) == \
        ["final21__positive", "final21__wrong_ref"]
    assert GCCV2["comparison_vs_frozen_v1"]["outcome_changes_any_tolerance"] == []
    assert all(c["input_hashes_match_manifest"] for c in GCCV2["per_case"])
    for tol in GCCV2["summary_outcome_counts_by_tolerance"].values():
        assert tol["CORRECT_ACCEPT"] == GCC_METRICS["positive_correct_accepts"]
    # GCC repeat records are lag-identical under v2 (Table 6 note).
    unchanged = {c["case_id"] for c in GCCV2["per_case"] if not c["lag_changed_by_correction"]}
    assert {"final01__positive", "final02__positive", "repeat01__positive",
            "repeat02__positive"} <= unchanged

    # --- Abstract audit ---
    abstract = draft.split("## Abstract\n", 1)[1].split("\n## 1.", 1)[0].strip()
    assert abstract == " ".join(abstract_expected()), "Abstract needs a fresh complete claim audit"
    abstract_words = len(abstract.split())
    assert 180 <= abstract_words <= 250, abstract_words
    for index in range(1, 11):
        assert f"A{index:02d}" in ledger, "Missing abstract sentence audit"

    # --- Frozen-evidence internal consistency ---
    for m in METRICS.values():
        assert m["positive_accepts"] == m["positive_correct_accepts"] + m["positive_wrong_accepts"]
        assert m["accepted_risk_100ms"] == m["positive_wrong_accepts"] / m["positive_accepts"]
    for key in SYSTEMS:
        frozen_key = "gcc_phat_argmax_v1" if key.startswith("gcc") else key
        for panel in [FROZEN["condition_level_100ms"], FROZEN["source_level_100ms"]]:
            counts = [r.get("primary_positives", r)[frozen_key] for r in panel.values()]
            for outcome, field in [("CORRECT_ACCEPT", "positive_correct_accepts"),
                                   ("WRONG_ACCEPT", "positive_wrong_accepts"),
                                   ("SAFE_ABSTAIN", "positive_safe_abstain_no_match")]:
                assert sum(c.get(outcome, 0) for c in counts) == METRICS[frozen_key][field]
    by_tolerance = V2["counts_by_tolerance"]
    assert by_tolerance["0.05"] == by_tolerance["0.1"] == by_tolerance["0.15"]

    # --- Paired outcomes (Table 7) ---
    disc = FROZEN["discordant_counts_vs_rhythmalign"]
    ra_ncc = disc["ncc_argmax_v1"]["positives_100ms"]
    assert (ra_ncc["both_correct_accept"], ra_ncc["ncc_argmax_v1_only"],
            ra_ncc["rhythmalign_only"], ra_ncc["neither"]) == (17, 2, 3, 2)
    gcc_p = disc["gcc_phat_argmax_v1"]["positives_100ms"]
    assert (gcc_p["both_correct_accept"], gcc_p["gcc_phat_argmax_v1_only"],
            gcc_p["rhythmalign_only"], gcc_p["neither"]) == (10, 0, 10, 4)
    for entry in disc.values():
        assert sum(entry["positives_100ms"][k] for k in
                   ["both_correct_accept"] + [k2 for k2 in entry["positives_100ms"]
                                              if k2.endswith("_only")] + ["neither"]) == 24
    for phrase in ["17 positives both placed correctly", "10 both, 10 RhythmAlign-only",
                   "2 both, 18 RhythmAlign-only"]:
        assert phrase in draft, phrase
    assert "no significance test is performed" in draft

    # --- NCC overlap-contract recomputation and disclosure (revision gate) ---
    geom = {c["case_id"]: c for c in GCCMAN["geometry_only_prediction"]["per_case"]}
    overlaps = {}
    for case_id, wrong_s in NCC_WRONG_OVERLAPS.items():
        rec = read_json(RESULTS / "final_comparator_raw_records" / f"ncc_argmax_v1__{case_id}__positive.json")
        lag = rec["native_scores"]["lag_samples"]
        g = geom[f"{case_id}__positive"]
        overlap = (g["query_samples"] - lag) / SR if lag >= 0 else (g["reference_samples"] + lag) / SR
        assert abs(overlap - wrong_s) < 0.001, (case_id, overlap)
        overlaps[case_id] = overlap
    correct_overlaps = []
    for row in FROZEN["per_case_rows"]:
        if row["system"] == "ncc_argmax_v1" and row["pair_type"] == "POSITIVE" \
                and not row["reliability_only"] and row["outcome_at_0.1"] == "CORRECT_ACCEPT":
            g = geom[row["case_id"]]
            rec = read_json(RESULTS / "final_comparator_raw_records" / f"ncc_argmax_v1__{row['case_id']}.json")
            lag = rec["native_scores"]["lag_samples"]
            correct_overlaps.append((g["query_samples"] - lag) / SR if lag >= 0
                                    else (g["reference_samples"] + lag) / SR)
    assert len(correct_overlaps) == 19 and min(correct_overlaps) >= MIN_CORRECT_OVERLAP_S - 0.001
    assert max(overlaps.values()) < 30.0 < min(correct_overlaps)
    assert NCC_CONTRACT_SENTENCE in draft, "Required NCC comparator-contract sentence missing"
    for case_id, value in NCC_WRONG_OVERLAPS.items():
        assert f"{value:.3f} s ({case_id})" in tables or f"{value:.3f}" in tables
    assert "1.2–4.7 s" in draft and "60.414 s" in draft and "30 s" in draft

    # --- Numeric prose guards ---
    assert f"{produced['max_s']:.4f} s" in draft and f"{produced['median_s']:.4f} s" in draft
    assert "0.22 ms" in draft and "3.8 ms" in draft and "7.9 ms" in draft and "15.1 ms" in draft
    for key, label in [("ncc_argmax_v1", "NCC")]:
        d = V2["error_distributions_positives"][key]["all_produced_accept_abs_error_s"]
        assert f"{d['max_s']:.4f} s" in draft and f"{d['median_s']:.4f} s" in draft
    assert "64.2303 s" in draft and "132.7303 s" in draft
    assert "104.4808 s" in draft and "155.5800 s" in draft
    for c in V2["strict_repeats"]["comparisons"]:
        if c["system"] == "rhythmalign_v1_2_0":
            assert f"{c['placement_move_s']:.4f} s" in draft
            assert f"{1000 * c['signed_error_difference_s']:+.1f} ms" in draft
        if c["comparison"].startswith("repeat02") and c["system"] != "panako_fingerprint":
            assert f"{c['placement_move_s']:.4f} s" in draft
    for boot in V2["rate_bootstrap"]["systems"].values():
        lo, hi = boot["correct_placement_yield_100ms_ci95"]
        assert f"[{lo:.2f}, {hi:.2f}]" in draft
    assert "136.9–139.3 s" in draft and "62.9–68.7 s" in draft  # interference duration disclosure
    assert "final21–final22 to the primary device D1" in draft  # D1/D2 provenance clarification
    assert "did not reliably recover placement on this selected technical stratum" in draft
    assert "not a usability comparison" in draft

    # --- Revision-1 forbidden/required wording gate ---
    combined = "\n".join(files.values())
    assert f"# {TITLE}" in draft
    assert not re.search(r"\bReliable\b", draft)
    assert not re.search(r"\b(reliable|robust|superior|safer)\b", abstract, flags=re.I)
    assert "gcc_phat_argmax_v2_lagfix" in draft
    assert "GCC-PHAT argmax (v2 lagfix)" in tables and "(v2 lagfix)" in draft
    assert "preserved verbatim as defective-implementation evidence" in draft
    assert "184.1055" not in combined  # superseded v1 artifact maximum must not appear
    assert "[CITATION TODO" not in combined  # C1/C2 resolved
    assert "Public Audio Identification Evaluation Framework" in draft  # evaluation-framework prior art
    assert "reproducible protocol with restricted exact-media corpus" in draft
    assert "Hashes prove identity, not availability" in draft
    assert "openly reproducible" not in combined
    assert not re.search(r"\bcatastrophic\b", combined, flags=re.I)
    no_labels = re.sub(r"SAFE_ABSTAIN", "", combined)
    assert not re.search(r"\bsafety\b|\bsafe\b", no_labels, flags=re.I)
    assert not re.search(r"(selectivity|abstention|refusal)\s+(caused|is the key)", combined, flags=re.I)
    assert not re.search(r"selective alignment reduced", combined, flags=re.I)
    assert not re.search(r"pilot (results|participants|creators)\s+(show|reported|were)", combined, flags=re.I)
    assert "pilot exists but was not conducted" in draft and "NOT_CONDUCTED" in files["CLAIM_LEDGER_V1.md"]
    assert "Positive-case accepted error rate" in draft and "Accepted risk" not in draft.split("## References")[0].split("## Abstract")[1]

    # --- Citation structure ---
    used = set(re.findall(r"R\d+", draft.split("## References", 1)[0]))
    defined = set(re.findall(r"\*\*(R\d+)\.", draft))
    assert used == defined == {f"R{i}" for i in range(1, 15)}
    for path in HERE.glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not re.match(r"https?://", target):
                assert (path.parent / target.split("#", 1)[0]).exists(), (path.name, target)

    # --- Frozen evidence untouched ---
    sidecars = list(RESULTS.rglob("*.sha256"))
    for sidecar in sidecars:
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        original = sidecar.with_suffix("")
        assert hashlib.sha256(original.read_bytes()).hexdigest() == expected, str(original)
    raw = read_json(RESULTS / "final_comparator_raw.json")
    for r in raw["records"]:
        assert hashlib.sha256((ROOT / r["record_file"]).read_bytes()).hexdigest() == r["record_sha256"]
    diff = subprocess.check_output(["git", "diff", "--name-only", BASE, "--"], cwd=ROOT, text=True)
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    changed = {p for p in diff.splitlines() if p} | {ln[3:].strip() for ln in status.splitlines() if ln.startswith("??")}
    outside = {p for p in changed if not p.startswith("docs/research/applied_system/paper/") and p != ".zcodeignore"}
    assert not outside, outside
    body = draft.split("## Abstract", 1)[1].split("## References", 1)[0]
    print(f"PASS: seven tables (incl. paired outcomes + GCC v2 distributions), source/condition counts, "
          f"complete 10-sentence abstract audit ({abstract_words} words), NCC overlap-contract recomputation, "
          f"numerical prose guards, revision-1 wording gate, citation IDs R1–R14, links, {len(sidecars)} SHA-256 "
          f"sidecars, {len(raw['records'])} raw record hashes, and documentation-only diff vs {BASE}.")
    print(f"Approximate manuscript word count (Abstract through Conclusion, tables included, references excluded): {len(body.split())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-tables", action="store_true")
    args = parser.parse_args()
    if args.write_tables:
        (HERE / "PAPER_TABLES_V1.md").write_text(render_tables(), encoding="utf-8", newline="\n")
        print("Wrote PAPER_TABLES_V1.md from sealed summaries only.")
    else:
        validate()
