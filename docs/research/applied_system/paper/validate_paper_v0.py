"""Read-only paper/evidence checks; --write-tables writes only PAPER_TABLES_V0.md.

No comparator imports, audio access, aggregation reruns, or frozen-file writes.
Values below project existing sealed summaries into manuscript displays.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACK = ROOT / "experiments/applied_system/final_pack"
RESULTS = PACK / "results"
BASE = "9605c21127d14d72922593a7990571d48a461bb2"
SYSTEMS = {
    "rhythmalign_v1_2_0": "RhythmAlign v1.2.0",
    "gcc_phat_argmax_v1": "GCC-PHAT argmax",
    "ncc_argmax_v1": "NCC argmax",
    "panako_fingerprint": "Panako OLAF",
}
CONDITIONS = ["ORDINARY", "LOW_LEVEL", "TAP_DOMINANT", "INTERFERENCE",
              "PARTIAL", "DEVICE_VARIATION"]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


V2 = read_json(RESULTS / "final_benchmark_reporting_v2.json")["body"]
FROZEN = read_json(RESULTS / "final_benchmark_results.json")["body"]
MANIFEST = read_json(RESULTS / "final_benchmark_manifest.json")["body"]
KDENLIVE = read_json(RESULTS / "final_kdenlive_results.json")["body"]
METRICS = V2["reporting_metrics_100ms"]["per_system"]


def table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(map(str, row)) + " |" for row in rows),
    ])


def fraction(n, d):
    percent = f"{100 * n / d:.1f}".removesuffix(".0")
    return f"{n}/{d} ({percent}%)"


def main_table():
    rows = []
    for key, name in SYSTEMS.items():
        m = METRICS[key]
        rows.append([name,
                     fraction(m["positive_accepts"], m["positive_denominator"]),
                     fraction(m["positive_correct_accepts"], m["positive_denominator"]),
                     fraction(m["positive_wrong_accepts"], m["positive_accepts"]),
                     fraction(m["wrong_ref_wrong_accepts"], m["wrong_ref_denominator"])])
    return table(["System", "Acceptance coverage", "Correct-placement yield",
                  "Accepted risk", "Wrong-ref false accept"], rows)


def outcome_triple(counts):
    return "/".join(str(counts.get(k, 0)) for k in
                    ["CORRECT_ACCEPT", "WRONG_ACCEPT", "SAFE_ABSTAIN"])


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
    errors = []
    for key, name in SYSTEMS.items():
        dist = V2["error_distributions_positives"][key]
        for kind, label, scale, unit, precision in [
            ("correct_accept_conditional_abs_error_s", "CORRECT_ACCEPT only", 1000, "ms", 2),
            ("all_produced_accept_abs_error_s", "All produced positive placements", 1, "s", 4),
        ]:
            d = dist[kind]
            fmt = lambda x: f"{scale * x:.{precision}f}"
            errors.append([name, label, d["n"], unit, fmt(d["median_s"]),
                           f"{fmt(d['iqr25_s'])}–{fmt(d['iqr75_s'])}", fmt(d["max_s"])])
    error_table = table(["System", "Conditioning", "n", "Unit", "Median absolute error",
                         "IQR", "Maximum"], errors)
    condition_rows = []
    for condition in CONDITIONS:
        counts = FROZEN["condition_level_100ms"][condition]
        n = sum(counts["rhythmalign_v1_2_0"].values())
        condition_rows.append([condition, n, *(outcome_triple(counts[s]) for s in SYSTEMS)])
    condition_table = table(["Condition", "n", *SYSTEMS.values()], condition_rows)
    source_rows = []
    for slot, counts in FROZEN["source_level_100ms"].items():
        pos = counts["primary_positives"]
        source_rows.append([slot, sum(pos["rhythmalign_v1_2_0"].values()),
                            *(outcome_triple(pos[s]) for s in SYSTEMS)])
    source_table = table(["Source", "Primary n", *SYSTEMS.values()], source_rows)
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
    for c in V2["strict_repeats"]["comparisons"]:
        move = c.get("placement_move_s")
        delta = c.get("signed_error_difference_s")
        orig = c.get("original_placement_abs_error_s")
        rep = c.get("repeat_placement_abs_error_s")
        repeat_rows.append([c["comparison"], SYSTEMS[c["system"]],
                            f"{c['original_decision']} → {c['repeat_decision']}",
                            "Yes" if c["decision_state_agreement"] else "No",
                            "—" if move is None else f"{move:.4f}",
                            "—" if delta is None else f"{1000 * delta:+.2f}",
                            "—" if orig is None else f"{orig:.6f}",
                            "—" if rep is None else f"{rep:.6f}"])
    repeat_table = table(["Comparison", "System", "Native states", "State agreement",
                          "Absolute output movement (s)", "Signed error change (ms)",
                          "Original absolute error (s)", "Repeat absolute error (s)"], repeat_rows)
    return f"""# Paper Tables V0

STATUS: TECHNICAL-CORE TABLES — sealed benchmark evidence; creator pilot NOT_CONDUCTED.

Numeric authority: [reporting v2](../../../../experiments/applied_system/final_pack/results/final_benchmark_reporting_v2.json) (V2). Composition uses the frozen benchmark/acquisition manifests; condition and source panels use only raw counts in the immutable original final-results artifact (F), never its obsolete coverage fields. Kdenlive per-pair detail uses its frozen result artifact (K). All tables are projections of stored evidence, not new performance analyses. Fractions retain exact denominators; displayed decimals are rounded.

## Table 1 — Benchmark composition

{composition}

Acquisition: 3 sessions, 2 rooms, 2 recording devices; 26/26 captures GT_VALID (24 primary + 2 repeats). Sources are the independence unit; primary takes and reused wrong-reference recordings are dependent. Exactly 3 source identities were preflagged for repetitive structure. Optional authentic-handcam, version-mismatch, external-domain, and creator-pilot evidence is not included. The Kdenlive pairs reuse selected primary takes and are not additional recordings. Source: frozen manifests, FINAL_SOURCE_SELECTION.md, FINAL_ACQUISITION_QC.md.

## Table 2 — Main system results

100 ms primary correctness tolerance. First three metrics: primary positives only. Last metric: constructed wrong references only. Kdenlive has a separate denominator (Table 5).

{main_table()}

Acceptance coverage = accepts / positives; correct-placement yield = correct accepts / positives; accepted risk = wrong positive accepts / all positive accepts. Acceptance coverage and correct-placement yield coincide for RhythmAlign and Panako here only because their observed positive accepts were all correct. GCC-PHAT and NCC always output. Source: V2.body.reporting_metrics_100ms.per_system. Counts are unchanged at 50/100/150 ms (V2.body.counts_by_tolerance).

## Table 3 — Placement error

Positive placements only. The conditioning and unit columns are essential: successful-case errors in milliseconds and all-produced errors in seconds describe different distributions. Refusals produce no offset and are not assigned zero error.

{error_table}

Every CORRECT_ACCEPT placement was below 25 ms. This does not describe every accepted placement. In particular, the all-produced NCC median remains small while its maximum reveals a large-error tail. Wrong-reference outputs have no true timing target and are excluded from these error distributions. Source: V2.body.error_distributions_positives.

## Table 4 — Condition-level raw counts

Each system cell is **CORRECT_ACCEPT / WRONG_ACCEPT / refusal**, as three counts, not a fraction. Refusal means native ABSTAIN for RhythmAlign and NO_MATCH for Panako. No subgroup inference.

{condition_table}

Source: F.body.condition_level_100ms. Row totals equal n for every system and sum to the Table 2 numerator counts.

**Source-level companion panel.** The same count convention applies; these are the ten independence units, not ten further observations.

{source_table}

Source: F.body.source_level_100ms. On wrong references, each source has the same denominator as its primary n: RhythmAlign and Panako refuse every case; GCC-PHAT and NCC accept every case. The four RhythmAlign positive refusals are final08/final18 (S08) and final20/final24 (S10). S08, S09, and S10 were preflagged repetitive; concentration on S08/S10 is descriptive, not causal.

## Table 5 — Kdenlive technical stratum

Kdenlive 26.08.1; one operator; separate positive-pair axis; no HCI or wrong-reference inference.

{ksummary}

{ktable}

Source: V2.body.kdenlive_stratum for summaries; K.body.per_pair for individual errors/times. Counts are identical at 50/100/150 ms. Original pair01 V1 is void evidence only; pair01r2 is its scored replacement under the uniform 180 s headroom procedure. Original failure evidence and the outcome-independent XML correction remain preserved. Pair01r2 timing is missing, not zero, and the void run's time is not substituted. Correct pair02/pair10 errors round to 5.3/0.1 ms; eight wrong errors range from approximately 0.85 to 149.4 s.

## Table 6 — Strict-repeat observations

Only two repeat takes, excluded from primary counts. Absolute output movement is |offset_repeat − offset_original|. Signed error change is (offset_repeat − GT_repeat) − (offset_original − GT_original). Different recording starts change GT; raw movement alone is not repeatability. Dashes mean values not supplied in V2 for Panako's refusal comparisons: the originals were accepted, but no repeat placement or paired timing change exists.

{repeat_table}

Source: V2.body.strict_repeats.comparisons. RhythmAlign's +7.8/+14.0 ms figures are changes in signed error, not raw output movement. GCC-PHAT repeat01 is consistently wrong. On repeat02, GCC-PHAT changes correct → wrong and NCC wrong → correct despite ACCEPT → ACCEPT in both cases; their raw movements are approximately 67.2 and 60.5 s. Panako refuses both repeats after accepting their originals. These are observations, not reliability rates.
"""


def abstract_expected():
    ra, gcc, ncc, pan = (METRICS[k] for k in SYSTEMS)
    n = ra["positive_denominator"]
    sources = len({c["source_slot"] for c in MANIFEST["cases"]})
    return [
        "Replacing degraded captured audio in user-generated video with a clean reference requires both accurate timing and a decision about whether a proposed placement is supported.",
        "An always-output estimator can return a precise-looking offset even when the reference is wrong.",
        "We evaluate frozen RhythmAlign v1.2.0 as a selective alignment system for this task, using rhythm-game handcam-style acoustic recording as the stress-test domain.",
        f"A performance-blind source selection and dual-marker timing protocol produced {n} dependent positive takes from {sources} source identities and {ra['wrong_ref_denominator']} constructed wrong-reference pairs; no thresholds were tuned on final data.",
        f"At a {1000 * V2['reporting_metrics_100ms']['tolerance_s']:.0f} ms correctness tolerance, RhythmAlign achieved {ra['positive_accepts']}/{n} acceptance coverage and {ra['positive_correct_accepts']}/{n} correct-placement yield (both {100 * ra['correct_placement_yield_100ms']:.1f}%), with accepted risk {ra['accepted_risk_display']} and wrong-reference false accepts {ra['wrong_ref_wrong_accepts']}/{ra['wrong_ref_denominator']}.",
        f"Always-output GCC-PHAT and normalized cross-correlation accepted all positives, with correct-placement yields of {gcc['positive_correct_accepts']}/{n} and {ncc['positive_correct_accepts']}/{n}, respectively, and each accepted all {gcc['wrong_ref_wrong_accepts']} wrong references.",
        f"Panako under its native shipped settings achieved {pan['positive_correct_accepts']}/{n} correct-placement yield with {pan['wrong_ref_wrong_accepts']}/{pan['wrong_ref_denominator']} wrong-reference false accepts.",
        f"In a separate, single-operator Kdenlive technical stratum, {V2['kdenlive_stratum']['correct_accepts_100ms']}/{V2['kdenlive_stratum']['scoring_pairs']} placements were correct.",
        "These observations concern one domain and one frozen operating point, not calibrated future risk or creator workflow benefit.",
        "The measured distinction was the systems' behavior on unsupported placements, rather than the precision of their successful matches; the cost of recovering from refusal remains unmeasured.",
    ]


def validate():
    draft = (HERE / "PAPER_DRAFT_V0.md").read_text(encoding="utf-8")
    tables = (HERE / "PAPER_TABLES_V0.md").read_text(encoding="utf-8")
    ledger = (HERE / "CLAIM_LEDGER_V0.md").read_text(encoding="utf-8")
    gaps = (HERE / "CITATION_GAPS_V0.md").read_text(encoding="utf-8")
    assert tables == render_tables(), "Paper table drift from sealed summaries"
    # Main table in the prose has alignment colons; cell content must match.
    normalize = lambda s: re.sub(r"(?m)^\|[-: |]+\|$", "", s).strip()
    actual = draft.split("| System | Acceptance coverage", 1)[1].split("\n\n", 1)[0]
    assert normalize("| System | Acceptance coverage" + actual) == normalize(main_table())
    abstract = draft.split("## Abstract\n", 1)[1].split("\n## 1.", 1)[0].strip()
    assert abstract == " ".join(abstract_expected()), "Abstract needs a fresh complete claim audit"
    abstract_words = len(abstract.split())
    assert 180 <= abstract_words <= 250, abstract_words
    for index in range(1, 11):
        assert f"A{index:02d}" in ledger, "Missing abstract sentence audit"
    for m in METRICS.values():
        assert m["positive_accepts"] == m["positive_correct_accepts"] + m["positive_wrong_accepts"]
        assert m["acceptance_coverage_100ms"] == m["positive_accepts"] / m["positive_denominator"]
        assert m["accepted_risk_100ms"] == m["positive_wrong_accepts"] / m["positive_accepts"]
    for key in SYSTEMS:
        for panel in [FROZEN["condition_level_100ms"], FROZEN["source_level_100ms"]]:
            counts = [r.get("primary_positives", r)[key] for r in panel.values()]
            for outcome, field in [("CORRECT_ACCEPT", "positive_correct_accepts"),
                                   ("WRONG_ACCEPT", "positive_wrong_accepts"),
                                   ("SAFE_ABSTAIN", "positive_safe_abstain_no_match")]:
                assert sum(c.get(outcome, 0) for c in counts) == METRICS[key][field]
    by_tolerance = V2["counts_by_tolerance"]
    assert by_tolerance["0.05"] == by_tolerance["0.1"] == by_tolerance["0.15"]
    assert all(d["correct_accept_conditional_abs_error_s"]["max_s"] < .025
               for d in V2["error_distributions_positives"].values())
    assert all(METRICS[k]["positive_accepts"] == 24 and METRICS[k]["wrong_ref_wrong_accepts"] == 24
               for k in ["gcc_phat_argmax_v1", "ncc_argmax_v1"])
    # Check rounded narrative values against their exact stored quantities.
    for key, label in [("gcc_phat_argmax_v1", "GCC-PHAT"), ("ncc_argmax_v1", "NCC")]:
        d = V2["error_distributions_positives"][key]["all_produced_accept_abs_error_s"]
        assert f"{d['max_s']:.4f} s" in draft, label
        assert f"{d['median_s']:.4f} s" in draft, label
    for c in V2["strict_repeats"]["comparisons"]:
        if c["system"] == "rhythmalign_v1_2_0":
            assert f"{c['placement_move_s']:.4f} s" in draft
            assert f"{1000 * c['signed_error_difference_s']:+.1f} ms" in draft
        if c["comparison"].startswith("repeat02") and c["system"] in ["gcc_phat_argmax_v1", "ncc_argmax_v1"]:
            assert f"{c['placement_move_s']:.4f} s" in draft
    for boot in V2["rate_bootstrap"]["systems"].values():
        lo, hi = boot["correct_placement_yield_100ms_ci95"]
        assert f"[{lo:.2f}, {hi:.2f}]" in draft
    for forbidden in [r"5\s*/\s*19", r"Every accepted placement.*below 25",
                       r"all accepted placements.*<\s*25", r"positive_coverage_fraction"]:
        assert not re.search(forbidden, draft + tables, flags=re.I)
    assert not re.search(r"\b(robust|reliable|superior|safer)\b", abstract, flags=re.I)
    assert "pilot exists but was not conducted" in draft
    assert "Zero observed wrong accepts does not certify future risk" in draft
    assert draft.startswith("STATUS: TECHNICAL-CORE DRAFT — BENCHMARK COMPLETE; CREATOR FEASIBILITY PILOT NOT CONDUCTED.")
    todos = re.findall(r"\[CITATION TODO: (C\d+) —", draft)
    assert todos == ["C1", "C2"]
    assert all(f"| {c} |" in gaps for c in todos)
    used = set(re.findall(r"R\d+", draft.split("## References", 1)[0]))
    defined = set(re.findall(r"\*\*(R\d+)\.", draft))
    assert used == defined == {f"R{i}" for i in range(1, 11)}
    for path in HERE.glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not re.match(r"https?://", target):
                assert (path.parent / target.split("#", 1)[0]).exists(), (path.name, target)
    sidecars = list(RESULTS.rglob("*.sha256"))
    for sidecar in sidecars:
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        original = sidecar.with_suffix("")
        assert hashlib.sha256(original.read_bytes()).hexdigest() == expected, str(original)
    raw = read_json(RESULTS / "final_comparator_raw.json")
    for r in raw["records"]:
        assert hashlib.sha256((ROOT / r["record_file"]).read_bytes()).hexdigest() == r["record_sha256"]
    diff = subprocess.check_output(["git", "diff", "--name-only", BASE, "--"], cwd=ROOT, text=True)
    assert all(p.startswith("docs/research/applied_system/paper/") for p in diff.splitlines()), diff
    body = draft.split("## Abstract", 1)[1].split("## References", 1)[0]
    print(f"PASS: six tables, source/condition counts, complete 10-sentence abstract audit ({abstract_words} words), numerical prose guards, citation IDs, links, {len(sidecars)} SHA-256 sidecars, {len(raw['records'])} raw record hashes, and documentation-only diff.")
    print(f"Approximate manuscript word count (Abstract through Conclusion, tables included, references excluded): {len(body.split())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-tables", action="store_true")
    args = parser.parse_args()
    if args.write_tables:
        (HERE / "PAPER_TABLES_V0.md").write_text(render_tables(), encoding="utf-8", newline="\n")
        print("Wrote PAPER_TABLES_V0.md from sealed summaries only.")
    else:
        validate()
