"""RA-1.2F1 regression replay using the canonical D1 populations/builders.

Local media paths are supplied at runtime or via the gitignored canonical
manifests. Outputs contain neutral case IDs and algorithm evidence only.
Historical result files are read, never overwritten. No export is invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments/ra12d1_temporal_support"))

import alignment_engine_v2 as eng
import common
import validate_full_positives

OUT = ROOT / "results/ra12f1"
HIST = ROOT / "experiments/ra12d1_temporal_support/results"


def write(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n", encoding="utf-8")


def decision_row(d):
    # Do not persist generator exception text, which could contain paths.
    assert all(not f["error"] for f in d.evidence["families"].values())
    return {"status": d.status, "offset": d.offset, "reason": d.reason_code,
            "temporal_support": d.evidence.get("temporal_support")}


def ap(args):
    runs = []
    for i in range(3):
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                               "_ap", "--video", args.video, "--music", args.music],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8", check=True)
        payload = json.loads(proc.stdout)
        runs.append(payload)
        print(f"AP fresh process {i + 1}: {payload['status']} "
              f"{payload['offset']} {payload['reason_code']}", flush=True)
    def stable(d):
        if isinstance(d, dict):
            return {k: stable(v) for k, v in d.items() if k != "runtime_s"}
        if isinstance(d, list):
            return [stable(v) for v in d]
        return d
    canonical = [stable(d) for d in runs]
    deterministic = canonical[0] == canonical[1] == canonical[2]
    for d in runs:
        assert d["status"] == eng.STATUS_ACCEPTED
        assert d["reason_code"] == eng.ACCEPT_DUAL_FAMILY
        assert abs(d["offset"] - 11.377777777777778) <= 0.05
        temporal = d["evidence"]["temporal_support"]
        assert temporal["applied"] and temporal["verified_method"] == "pcen_hpss"
        assert temporal["top_bin_share"] <= eng.DEFAULT_POLICY.max_top_bin_share
        false = min(d["clusters"], key=lambda c: abs(c["representative_offset_s"] - 11.633197278911565))
        assert false["families"][eng.FAMILY_PCEN]["supplier_method"] == "pcen"
        assert "pcen_z" in false["case_b_failed_checks"]
    assert deterministic
    # Use all locally registered reference tracks except the correct song.
    sources = common.Sources()
    wrong = []
    for tid, path in sorted(sources.mapping["tracks"].items()):
        if Path(path).resolve() == Path(args.music).resolve():
            continue
        d = eng.find_offset_v2(args.video, path)
        wrong.append({"case_id": "ap_x_" + tid, **decision_row(d)})
        print(f"AP x {tid}: {d.status} {d.reason_code}", flush=True)
    payload = {"runs": runs, "deterministic": deterministic,
               "canonical_decision_sha256": hashlib.sha256(json.dumps(canonical[0], sort_keys=True).encode()).hexdigest(),
               "wrong_references": wrong,
               "safety_passed": all(r["status"] == "abstained" for r in wrong)}
    write("ap.json", payload)
    assert payload["safety_passed"]


def positives():
    # Run the actual canonical integrated-production script, redirecting
    # only its output destination. Population and audio builders are intact.
    common.OUT = OUT
    validate_full_positives.main()
    baseline = common.read(HIST / "integrated_full_positives.json")["rows"]
    actual = common.read(OUT / "integrated_full_positives.json")
    old = {r["case_id"]: r for r in baseline}
    assert len(old) == len(actual["rows"]) == 85
    changes = []
    for row in actual["rows"]:
        previous = old[row["case_id"]]
        if row["status"] != previous["status"]:
            changes.append({"case_id": row["case_id"], "old": previous["status"], "new": row["status"]})
        elif row["status"] == "accepted" and abs(row["offset"] - previous["offset"]) > 0.15:
            changes.append({"case_id": row["case_id"], "offset_changed": True})
        if row["outcome"] == "WRONG_ACCEPT":
            changes.append({"case_id": row["case_id"], "wrong_accept": True})
    write("positive_comparison.json", {"total": 85,
          "statuses": dict(Counter(r["status"] for r in actual["rows"])),
          "changes": changes,
          "max_accepted_offset_change_s": max(abs(r["offset"] - old[r["case_id"]]["offset"])
             for r in actual["rows"] if r["status"] == old[r["case_id"]]["status"] == "accepted"),
          "low_snr": next(r for r in actual["rows"] if r["case_id"] == "lingduihua_132")})
    assert not changes, changes


def synthetic_before_after():
    import importlib.util
    import types
    spec = importlib.util.spec_from_file_location(
        "ownership_fixtures", ROOT / "tests/test_ra12f1_evidence_ownership.py")
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    baseline = "c92e82763350d70e7d5982de2dcdcb99cebc1e83"
    source = subprocess.check_output(
        ["git", "show", baseline + ":alignment_engine_v2.py"], cwd=ROOT).decode("utf-8")
    old = types.ModuleType("ra12f1_baseline_engine")
    sys.modules[old.__name__] = old
    exec(compile(source, "baseline_alignment_engine_v2.py", "exec"), old.__dict__)
    _, h2, frs = fixtures.structural_pair()
    gap = 66 * fixtures.FRAME
    cases = [("structural", frs, eng.DEFAULT_POLICY, h2),
             ("same_method", [fixtures.family("hybrid", [(10, 10)]),
               fixtures.family("pcen_hpss", [(10, 25), (10 + gap, 5.2), (30, 4)]),
               fixtures.family("onset", [(10 + gap, 3)])],
              eng.DecisionPolicy(cluster_tol_s=0.8), 10 + gap)]
    rows = []
    for name, families, policy, false_offset in cases:
        pair = {}
        for label, module in (("before", old), ("after", eng)):
            d = module.decide_from_families(families, fixtures.SR, fixtures.HOP,
                                           policy, 120, 90)
            cl = min(d.clusters, key=lambda c: abs(c["offset_s"] - false_offset))
            pair[label] = {**decision_row(d),
                           "false_primary": cl["families"][eng.FAMILY_PCEN]}
        assert pair["before"]["reason"] == eng.ABSTAIN_AMBIGUOUS_CLUSTER
        assert pair["after"]["reason"] == eng.ACCEPT_DUAL_FAMILY
        rows.append({"case": name, **pair})
    write("synthetic_before_after.json", {"baseline": baseline, "rows": rows})


def product(args):
    """Exercise the real GUI worker/engine path, replacing only export."""
    import auto_sync
    import ui_main
    assert ui_main.find_offset_v2 is eng.find_offset_v2
    native = ui_main.find_offset_v2
    decisions, exports, legacy_calls = [], [], []

    def observed(v, m):
        d = native(v, m)
        decisions.append(d)
        return d

    def forbidden_legacy(*args, **kwargs):
        legacy_calls.append(True)
        raise AssertionError("legacy fallback reached")

    ui_main.find_offset_v2 = observed
    auto_sync.find_offset = forbidden_legacy
    ui_main.mix_and_export = lambda **kwargs: exports.append(kwargs["offset"])
    target = OUT / "not-exported.mp4"
    rows = []
    sources = common.Sources()
    wrong = next(path for _, path in sorted(sources.mapping["tracks"].items())
                 if Path(path).resolve() != Path(args.music).resolve())
    for name, reference, expected in (("ap_positive", args.music, True),
                                      ("ap_wrong_reference", wrong, False)):
        initial = len(exports)
        kwargs = dict(v_path=args.video, m_path=reference, save_path=str(target),
                      orig_vol=1.0, music_vol=1.0, manual_offset=0.0,
                      use_gpu=False, bitrate="10000k", open_folder=False,
                      stream_copy=True)
        worker = ui_main.SyncWorker(kwargs)
        finished = []
        worker.finished_signal.connect(lambda *event: finished.append(event))
        worker.run()
        assert finished and finished[-1][0] is expected
        assert len(exports) - initial == int(expected)
        assert decisions[-1].accepted is expected
        rows.append({"case_id": name, **decision_row(decisions[-1]),
                     "export_calls_intercepted": len(exports) - initial})
    assert not legacy_calls and not target.exists()
    write("product.json", {"rows": rows, "engine": eng.ENGINE_LABEL,
          "entry_point_is_revised_production": True,
          "legacy_fallback_calls": len(legacy_calls),
          "physical_media_exports": 0})


def summary():
    """Assemble privacy-safe, checked evidence for repository history."""
    import ast
    import re
    baseline = "c92e82763350d70e7d5982de2dcdcb99cebc1e83"
    before = ast.parse(subprocess.check_output(
        ["git", "show", baseline + ":alignment_engine_v2.py"], cwd=ROOT).decode("utf-8"))
    after = ast.parse((ROOT / "alignment_engine_v2.py").read_text(encoding="utf-8"))
    unchanged = ["DecisionPolicy", "_case_a_failed_checks", "_case_b_failed_checks",
                 "_comparable_competitor_exists", "_choose_offset",
                 "_independent_peak_indices", "_concentration_profile",
                 "_apply_temporal_support"]
    for name in unchanged:
        assert ast.dump(next(n for n in before.body if getattr(n, "name", None) == name)) == ast.dump(
            next(n for n in after.body if getattr(n, "name", None) == name)), name
    tests = {}
    for key, expected in (("pytest", 96), ("engine-tests", 13),
                          ("temporal-tests", 11), ("ownership-tests", 16)):
        raw = (ROOT / "results" / f"ra12f1-{key}.log").read_bytes()
        log = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff"))
                         else "utf-8-sig")
        count = int(re.search(r"(\d+) passed", log).group(1))
        assert count == expected and " failed" not in log
        tests[key] = count
    ap_data = common.read(OUT / "ap.json")
    positives_data = common.read(OUT / "positive_comparison.json")
    actual = common.read(OUT / "integrated_full_positives.json")["rows"]
    safety_data = common.read(OUT / "safety.json")
    assert ap_data["deterministic"] and ap_data["safety_passed"]
    assert not positives_data["changes"] and not safety_data["new_false_accepts"]
    assert positives_data["statuses"] == {"accepted": 55, "abstained": 30}

    def stable(data):
        if isinstance(data, dict):
            return {k: stable(v) for k, v in data.items() if k != "runtime_s"}
        if isinstance(data, list):
            return [stable(v) for v in data]
        return data
    first = ap_data["runs"][0]
    payload = {"baseline": baseline, "branch": "hotfix/ra12f1-evidence-ownership",
               "verdict": "READY_FOR_RA12F1_CTO_REVIEW", "unchanged_ast": unchanged,
               "tests": tests,
               "ap": {"runs": [{"status": d["status"], "offset": d["offset"],
                                 "reason": d["reason_code"],
                                 "temporal_support": d["evidence"]["temporal_support"]}
                                for d in ap_data["runs"]],
                      "deterministic": True,
                      "canonical_decision_sha256": ap_data["canonical_decision_sha256"],
                      "clusters": stable(first["clusters"]),
                      "wrong_references": ap_data["wrong_references"]},
               "positives": {**stable(positives_data), "rows": stable(actual),
                  "max_abs_error_exact_gt_semi_synthetic_s": max(abs(r["offset_error"])
                    for r in actual if r["split"] != "real" and r["offset_error"] is not None),
                  "ground_truth_note": "Construction-exact semi-synthetic GT; low-SNR real manual interval; other real rows mostly pairing evidence."},
               "safety": safety_data,
               "synthetic": common.read(OUT / "synthetic_before_after.json"),
               "product": common.read(OUT / "product.json")}
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    assert not re.search(r"[A-Za-z]:[\\/]", encoded), "absolute local path in evidence"
    target = Path(__file__).resolve().parent / "results/regression.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(encoded, encoding="utf-8")
    print(json.dumps({"positive_statuses": positives_data["statuses"],
                      "changes": positives_data["changes"],
                      "max_offset_change": positives_data["max_accepted_offset_change_s"],
                      "low_snr": positives_data["low_snr"],
                      "tests": tests, "safety_counts": safety_data["counts"]}, indent=2))


def safety():
    store = common.FeatureStore(common.Sources())
    sources = store.sources
    rows = []
    equivalence_checked = False

    def cached_pair(case_id, family, q, r, kind="tracks"):
        nonlocal equivalence_checked
        vf, mf = store.get(kind, q), store.get("tracks", r)
        v, m = sources.audio(kind, q), sources.audio("tracks", r)
        frs = common.families(vf, mf)
        for fr in frs:
            if fr.family == eng.FAMILY_PCEN:
                fr.features = (vf[fr.method], mf[fr.method])
        if not equivalence_checked:
            # Canonical cached-feature seam must reproduce production
            # generator curves exactly before being used for this grid.
            import numpy as np
            direct = eng._run_generators(v, m, common.SR, common.HOP)
            for cached, original in zip(frs, direct):
                assert cached.method == original.method
                np.testing.assert_array_equal(cached.curve, original.curve)
                assert cached.n_video_frames == original.n_video_frames
            equivalence_checked = True
        d = eng.decide_from_families(frs, common.SR, common.HOP, None,
                                     common.duration(v), common.duration(m))
        d = eng._apply_temporal_support(d, frs, eng.DEFAULT_POLICY,
                                        common.SR, common.HOP)
        rows.append({"case_id": case_id, "family": family, **decision_row(d)})
        print(f"{family} {case_id}: {d.status} {d.reason_code}", flush=True)

    wrong = common.read(HIST / "eval_wrong_song_test.json")["rows"]
    clean = [r for r in wrong if r["family"] == "heldout_clean_wrong_song"]
    assert len(clean) == 156
    for row in clean:
        q, r = row["query_track"], row["reference_track"]
        cached_pair(q + "_x_" + r, "clean_wrong_song", q, r)
    dev = [r for r in common.read(HIST / "dev_concentration.json")["rows"]
           if r["kind"] == "dev_wrong_song" and r["v2_status"] == "accepted"]
    assert len(dev) == 18
    for row in dev:
        q, r = row["case_id"].removeprefix("devwrong_").split("_x_")
        cached_pair(row["case_id"], "dev_concentrated", q, r)
    cached_pair("blocker_lingduihua_x_yanwulieche", "astra_blocker",
                "tr_lingduihua", "tr_yanwulieche")
    cached_pair("haiditan_ds_1_x_tr_hongzhoutian", "known_unresolved_residual",
                "haiditan_ds_1", "tr_hongzhoutian", "recordings")
    historical_neg = common.read(HIST / "eval_negatives.json")["rows"]
    ids = {r["case_id"] for r in historical_neg}
    assert len(ids) == 24
    for split in ("calibration", "holdout"):
        for c in common.iter_split_cases(split):
            if c["case_id"] not in ids:
                continue
            v = common.semi_case_mix(c, store)
            m = sources.audio("tracks", c["target"])
            d = eng.decide_alignment(v, m)
            rows.append({"case_id": c["case_id"], "family": c["kind"], **decision_row(d)})
            print(f"{c['kind']} {c['case_id']}: {d.status} {d.reason_code}", flush=True)
    for c in common.real_cases():
        if c["case_id"] not in ids:
            continue
        v, m = common.real_case_audio(c, sources)
        d = eng.decide_alignment(v, m)
        rows.append({"case_id": c["case_id"], "family": "ordinary_mismatch", **decision_row(d)})
        print(f"mismatch {c['case_id']}: {d.status} {d.reason_code}", flush=True)
    assert {r["case_id"] for r in rows if r["family"] in
            ("hard_negative", "tiled", "ordinary_mismatch")} == ids
    failures = [r for r in rows if r["status"] != "abstained"
                and r["family"] != "known_unresolved_residual"]
    write("safety.json", {"rows": rows, "new_false_accepts": failures,
          "cached_curves_bit_exact_to_production": equivalence_checked,
          "counts": dict(Counter(r["family"] for r in rows))})
    assert not failures, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("section", choices=["ap", "_ap", "positives", "safety", "synthetic", "product", "summary"])
    parser.add_argument("--video")
    parser.add_argument("--music")
    args = parser.parse_args()
    if args.section == "_ap":
        d = eng.find_offset_v2(args.video, args.music)
        decision_row(d)
        print(json.dumps(d.as_dict(), ensure_ascii=False, allow_nan=False))
    elif args.section == "ap":
        ap(args)
    elif args.section == "positives":
        positives()
    elif args.section == "synthetic":
        synthetic_before_after()
    elif args.section == "product":
        product(args)
    elif args.section == "summary":
        summary()
    else:
        safety()


if __name__ == "__main__":
    main()
