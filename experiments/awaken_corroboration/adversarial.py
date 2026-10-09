"""Construct shared-event negatives before opening held-out validation."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.awaken_corroboration.study import eng, row, write, OUT
from experiments.awaken_corroboration.waveform_probe import measure, passes
spec = importlib.util.spec_from_file_location("temporal_fixtures", ROOT / "tests/test_ra12d1_temporal_support.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def build_pair(count, gain):
    # Different complete songs with only shared short hit sequences.
    m = fixtures.make_music(duration_s=120, seed=13)
    v = fixtures.make_other_song(duration_s=130, seed=17)
    event = fixtures._hit_sequence(gain=gain, seed=31)
    for start in np.linspace(12, 102, count):
        mi = int(start * fixtures.SR)
        vi = int((start + 5) * fixtures.SR)
        m[mi:mi+len(event)] += event
        v[vi:vi+len(event)] += event
    return v,m


def main():
    rows = []
    for count in (1, 2, 4):
        for gain in (1, 4):
            v,m = build_pair(count,gain)
            r = row(f"shared_events_{count}_gain_{gain}", "constructed_wrong_song", v, m)
            r["wave_at_shared_offset"] = measure(v,m,fixtures.SR,5)
            rows.append(r)
            print(r["case_id"],r["before"],[(q["temporal_ok"],passes(q["waveform"])) for q in r["proposals"]],flush=True)
            write("adversarial_dev.json", {"rows": rows})


if __name__ == "__main__":
    main()
