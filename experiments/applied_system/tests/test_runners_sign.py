"""Research-only tests: DSP runner sign conventions and semantics
preservation. SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import synth_payload  # noqa: E402
from experiments.applied_system.runners import gcc_phat_runner, ncc_runner  # noqa: E402
from experiments.applied_system.runners.common import (  # noqa: E402
    DECISION_ACCEPT, SEMANTICS_ALWAYS_OUTPUT)

FS = 48_000
PAYLOAD_S = 8.0


@pytest.fixture(scope="module")
def song_a():
    return synth_payload.render_song_a(duration_s=PAYLOAD_S)


@pytest.fixture(scope="module")
def song_b():
    return synth_payload.render_song_b(duration_s=PAYLOAD_S)


def _rec_with(song, lead_s):
    rng = np.random.default_rng(3)
    lead = rng.normal(0, 3e-4, int(round(lead_s * FS)))
    return np.concatenate([lead, song, rng.normal(0, 3e-4, FS)])


@pytest.mark.parametrize("runner", [gcc_phat_runner, ncc_runner])
def test_positive_offset_sign(runner, song_a):
    rec = _rec_with(song_a, 1.5)
    offset, native = runner.ncc_offset(rec, song_a) if runner is ncc_runner \
        else runner.gcc_phat_offset(rec, song_a)
    assert offset == pytest.approx(int(round(1.5 * FS)), abs=FS // 1000)
    assert native["lag_samples"] == offset


@pytest.mark.parametrize("runner", [gcc_phat_runner, ncc_runner])
def test_negative_offset_sign(runner, song_a):
    """Capture starting mid-song must produce a NEGATIVE offset (production
    convention: first |offset| seconds of the reference trimmed)."""
    rec = np.concatenate([song_a[int(round(1.0 * FS)):],
                          np.zeros(FS)])
    offset, _ = (runner.ncc_offset(rec, song_a) if runner is ncc_runner
                 else runner.gcc_phat_offset(rec, song_a))
    assert offset == pytest.approx(-int(round(1.0 * FS)), abs=FS // 1000)


@pytest.mark.parametrize("runner", [gcc_phat_runner, ncc_runner])
def test_determinism(runner, song_a):
    rec = _rec_with(song_a, 0.7)
    fn = runner.ncc_offset if runner is ncc_runner else runner.gcc_phat_offset
    off1, nat1 = fn(rec, song_a)
    off2, nat2 = fn(rec, song_a)
    assert off1 == off2
    assert {k: v for k, v in nat1.items() if "runtime" not in k} == \
        {k: v for k, v in nat2.items() if "runtime" not in k}


def test_wrong_reference_still_always_output(tmp_path, song_a, song_b):
    """No invented refusal: on a wrong-reference pair the argmax baselines
    must still ACCEPT (semantics preserved for scoring to judge)."""
    import soundfile as sf
    in_path = tmp_path / "in_b.wav"
    ref_path = tmp_path / "ref_a.wav"
    sf.write(str(in_path), _rec_with(song_b, 1.25), FS, subtype="PCM_16")
    sf.write(str(ref_path), song_a, FS, subtype="PCM_16")
    case = {"case_id": "wrong_ref_test"}
    for runner in (gcc_phat_runner, ncc_runner):
        record = runner.run_case(case, in_path, ref_path, FS, load_audio)
        assert record.decision == DECISION_ACCEPT
        assert record.output_semantics == SEMANTICS_ALWAYS_OUTPUT
        assert record.notes["no_threshold_invented"] is True


def test_run_case_file_contract(tmp_path, song_a, song_b):
    import soundfile as sf
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    sf.write(str(in_path), _rec_with(song_a, 1.25), FS, subtype="PCM_16")
    sf.write(str(ref_path), song_a, FS, subtype="PCM_16")
    case = {"case_id": "file_test"}

    for runner in (gcc_phat_runner, ncc_runner):
        record = runner.run_case(case, in_path, ref_path, FS, load_audio)
        assert record.decision == DECISION_ACCEPT
        assert record.predicted_offset_s == pytest.approx(1.25, abs=2e-3)
        assert record.case_id == "file_test"


def load_audio(path, fs=FS):
    import soundfile as sf
    y, sr = sf.read(str(path), dtype="float64", always_2d=False)
    assert sr == fs
    return np.ascontiguousarray(y)
