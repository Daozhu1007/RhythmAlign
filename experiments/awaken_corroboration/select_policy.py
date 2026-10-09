"""Compare candidate policies on DEV, then write the immutable test contract."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.awaken_corroboration.waveform_probe import passes

OUT = ROOT / "results/awaken"


def main():
    data = json.loads((OUT / "dev_raw.json").read_text())
    assert len(data["rows"]) == 146, len(data["rows"])
    comparisons = []
    for z, margin, tol, n in ((5, 1.2, 0.15, 1), (5, 1.2, 0.15, 4),
                              (7, 1.4, 0.1, 4), (9, 2.0, 0.05, 4),
                              (12, 2.0, 0.05, 4)):
        changes = []
        for row in data["rows"]:
            for q in row["proposals"]:
                w = q["waveform"]
                probe = {**w, "windows": w["windows"][:n]}
                if q["temporal_ok"] and passes(probe, z, margin, tol):
                    if row["gt"] is not None:
                        correct = abs(q["offset"] - row["gt"]) <= row["tolerance_s"]
                    else:
                        correct = "positive" in row["group"]
                    changes.append({"case_id": row["case_id"], "correct": correct})
        comparisons.append({"z": z, "margin": margin, "tolerance_s": tol,
                            "windows": n, "upgrades": changes,
                            "wrong_upgrades": sum(not c["correct"] for c in changes)})
    policy = {"window_s": 25.0, "windows": 4, "min_window_s": 8.0,
              "min_overlap_fraction": 0.8, "z_floor": 7.0, "margin_floor": 1.4,
              "offset_tolerance_s": 0.1, "max_spread_s": 0.05,
              "decimation": 3, "independent_peak_separation_s": 1.5}
    selected = next(c for c in comparisons if c["z"] == 7)
    assert not selected["wrong_upgrades"]
    assert any(c["case_id"] == "awaken" for c in selected["upgrades"])
    adversarial = json.loads((OUT / "adversarial_dev.json").read_text())
    assert len(adversarial["rows"]) == 6
    assert all(r["before"]["status"] == "abstained" and not any(
        q["temporal_ok"] and passes(q["waveform"]) for q in r["proposals"])
        for r in adversarial["rows"])
    for r in data["rows"]:
        for q in r["proposals"]:
            offsets = [w["offset_s"] for w in q["waveform"]["windows"] if w["available"]]
            if q["temporal_ok"] and passes(q["waveform"]):
                assert max(offsets)-min(offsets) <= policy["max_spread_s"]
    result = {"development_population": len(data["rows"]),
              "groups": dict(Counter(r["group"] for r in data["rows"])),
              "dev_input_sha256": hashlib.sha256((OUT / "dev_raw.json").read_bytes()).hexdigest(),
              "adversarial_cases": 6,
              "adversarial_input_sha256": hashlib.sha256((OUT / "adversarial_dev.json").read_bytes()).hexdigest(),
              "comparisons": comparisons, "selected": policy,
              "selection": "Four disjoint windows; stronger point-estimator checks than permissive comparator; 12 Z loses Awaken. No old global floor changes.",
              "validation_status": "NOT_YET_EVALUATED"}
    (OUT / "frozen_policy.json").write_text(json.dumps(result, indent=2) + "\n")
    print([(c["z"],c["margin"],c["windows"],len(c["upgrades"]),c["wrong_upgrades"]) for c in comparisons])


if __name__ == "__main__":
    main()
