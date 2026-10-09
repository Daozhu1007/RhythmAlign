"""Generate sanitized review evidence after all validation gates pass."""
from __future__ import annotations
import ast
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.awaken_corroboration.study import eng as old, OUT
import alignment_engine_v2 as eng


def read(name):
    return json.loads((OUT/name).read_text(encoding="utf-8"))


def aggregate(rows):
    return {"n":len(rows),
            "before_accept":sum(r["before"]["status"]=="accepted" for r in rows),
            "after_accept":sum(r["after"]["status"]=="accepted" for r in rows),
            "wrong_accept":sum(r["wrong_accept"] for r in rows),
            "old_accepts_preserved":all(r["old_accept_preserved"] for r in rows),
            "max_exact_gt_abs_error_s":max((abs(r["after"]["offset"]-r["gt"])
                for r in rows if r["gt"] is not None and r["after"]["status"]=="accepted"
                and not r["group"].startswith("positive")),default=None)}


def main():
    files=["validation_positives.json","validation_negatives.json",
           "validation_acoustic.json","validation_adversarial.json"]
    populations={f:read(f)["rows"] for f in files}
    assert [len(populations[f]) for f in files]==[85,424,50,36]
    policy_sha=hashlib.sha256((OUT/"frozen_policy.json").read_bytes()).hexdigest()
    assert all(read(f)["policy_sha256"]==policy_sha for f in files)
    assert all(not r["wrong_accept"] and r["old_accept_preserved"]
               for rows in populations.values() for r in rows)
    p,n,a,x=[populations[f] for f in files]
    assert all(r["after"]["status"]=="abstained" for r in n+x+[r for r in a if r["negative"]])
    native=(ROOT/"alignment_engine_v2.py").read_text(encoding="utf-8")
    source=subprocess.check_output(["git","show","5527647:alignment_engine_v2.py"],cwd=ROOT).decode()
    names=["_run_generators","_family_candidates","_case_a_failed_checks",
           "_case_b_failed_checks","_choose_offset","_comparable_competitor_exists",
           "_concentration_profile","_apply_temporal_support","_independent_peak_indices",
           "_margin_for_owned_peak"]
    def functions(s):
        return {n.name:ast.dump(n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
    one,two=functions(source),functions(native)
    assert all(one[n]==two[n] for n in names)
    assert all(getattr(eng.DEFAULT_POLICY,key)==value for key,value in vars(old.DEFAULT_POLICY).items())
    products=read("validation_product.json")
    acceptance=read("final_acceptance.json")
    assert acceptance["deterministic"] and acceptance["fixture_hashes_preserved"]
    assert len(acceptance["runs"])==3
    match=re.search(r"(\d+) passed in ([\d.]+)s",(OUT/"tests_final.log").read_text())
    assert match and int(match[1])==121
    assert products["rows"][0]["decision"]["status"]=="accepted"
    assert products["rows"][1]["decision"]["status"]=="abstained"
    changed=[{"case_id":r["case_id"],"group":r["group"],"gt":r["gt"],
              "offset_s":r["after"]["offset"],"reason":r["after"]["reason"]}
             for r in p+a if r["before"]["status"]!=r["after"]["status"]]
    aw=products["rows"][0]["decision"]
    frozen=read("frozen_policy.json")
    frozen={**frozen,"comparisons":[
        {**{k:v for k,v in c.items() if k!="upgrades"},
         "positive_upgrades":len(c["upgrades"])} for c in frozen["comparisons"]]}
    summary={"verdict":"VALIDATION_PASS_RECOMMEND_REVIEW",
        "baseline_commit":"552764763fc2dabb0e087f541c2e5646b050604d",
        "baseline_engine_matches_v121_tag":True,
        "policy_sha256":policy_sha,"frozen_policy":frozen,
        "unchanged_functions_ast":names,"old_policy_values_unchanged":vars(old.DEFAULT_POLICY),
        "historical_positives":aggregate(p),
        "semi_calibration":aggregate([r for r in p if r["group"].startswith("calibration")]),
        "semi_holdout":aggregate([r for r in p if r["group"].startswith("holdout")]),
        "real_pairing_positives":aggregate([r for r in p if r["group"].startswith("positive")]),
        "low_snr_manual_interval":{k:next(r for r in p if r["case_id"]=="lingduihua_132")[k]
            for k in ("gt","tolerance_s","before","after")},
        "acoustic_positives":aggregate([r for r in a if not r["negative"]]),
        "negative_groups":dict(Counter(r["group"] for r in n+x+[r for r in a if r["negative"]])),
        "rejection_or_ambiguity_cases":len(n+x+[r for r in a if r["negative"]]),
        "new_confirmed_wrong_accepts":0,"upgrades":changed,
        "final_tests":{"passed":int(match[1]),"wall_s":float(match[2])},
        "awaken_fresh_processes":{"deterministic":True,"runs":3,
            "canonical_decision_sha256":acceptance["canonical_decision_sha256"],
            "verifier_wall_s":[cost for r in acceptance["runs"] for cost in r["verifier_wall_s"]]},
        "awaken":{"status":aw["status"],"offset_s":aw["offset"],"reason":aw["reason_code"],
                  "temporal_support":aw["evidence"]["temporal_support"],
                  "waveform_corroboration":aw["evidence"]["waveform_corroboration"]},
        "product_scope":products["input_scope"],"physical_exports":0,"legacy_calls":0,
        "cache_equivalence":read("cache_equivalence.json"),
        "unresolved_residual":read("unresolved_residual.json")["after"],
        "evidence_classes":["Construction-exact semi-synthetic GT",
            "Historical marker-labelled acoustic GT (reused, not fresh confirmation)",
            "Historical pairing-only real positives except one manual interval",
            "Owner-confirmed Awaken identity; waveform agreement is not independent timing GT"],
        "raw_result_sha256":{f:hashlib.sha256((OUT/f).read_bytes()).hexdigest() for f in files},
        "final_source_sha256":{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
            for f in ("alignment_engine_v2.py","alignment_waveform.py","diagnostics.py","ui_main.py")}}
    dest=ROOT/"experiments/awaken_corroboration/results/validation_summary.json"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({k:summary[k] for k in ("historical_positives","semi_holdout",
        "acoustic_positives","rejection_or_ambiguity_cases","new_confirmed_wrong_accepts")},indent=2))


if __name__=="__main__":
    main()
