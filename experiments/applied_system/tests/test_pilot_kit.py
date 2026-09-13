"""Research-only tests: fresh-pilot source selection + kit build machinery.

PILOT_ONLY / NOT_PAPER_EVIDENCE. All tests run on synthetic audio or
synthetic candidate records — the owner's media library is never touched.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import marker_protocol as mp  # noqa: E402
from experiments.applied_system import pilot_kit_build as kb  # noqa: E402
from experiments.applied_system import pilot_source_selection as pss  # noqa: E402

FS = mp.FS


def _candidate(sha, path="/x/a.mp3", duration=180.0, r_long=0.9,
               lead=0.0, trail=0.0, texture=None):
    c = pss.Candidate(path=path, sha256=sha, size_bytes=1000)
    c.duration_s = duration
    c.sample_rate = FS
    c.channels = 1
    c.leading_silence_s = lead
    c.trailing_silence_s = trail
    c.r_long = r_long
    c.texture = texture if texture is not None else np.array([1.0, 0.0])
    return c


# ---------------------------------------------------------------------------
# exclusion matching + duplicate collapse
# ---------------------------------------------------------------------------


def test_exclusion_matching():
    assert pss.match_exclusions(pss.Candidate(
        path="D:\\m\\延误列车.mp3", sha256="a", size_bytes=1)) == \
        ["延误列车 (yanwulieche)"]
    assert "零对话 (lingduihua)" in pss.match_exclusions(pss.Candidate(
        path="D:\\v\\零对话\\track.mp3", sha256="a", size_bytes=1))
    assert "QUEEN" in pss.match_exclusions(pss.Candidate(
        path="D:\\v\\已发\\QUEEN\\QUEEN.mp3", sha256="a", size_bytes=1))
    arcaea = pss.match_exclusions(pss.Candidate(
        path="D:\\m\\Arcaea手元用\\x.mp3", sha256="a", size_bytes=1))
    assert any("Arcaea" in h for h in arcaea)
    assert pss.match_exclusions(pss.Candidate(
        path="D:\\m\\Bloody Trail.mp3", sha256="a", size_bytes=1)) == []
    # every exclusion identity must carry its patterns + provenance
    for exc in pss.EXCLUSIONS:
        assert exc["patterns"] and exc["provenance"]


def test_collapse_duplicates():
    cands = [
        pss.Candidate(path="D:\\m\\same.mp3", sha256="h1", size_bytes=1),
        pss.Candidate(path="D:\\v\\same.mp3", sha256="h1", size_bytes=1),
        pss.Candidate(path="D:\\m\\other.mp3", sha256="h2", size_bytes=1),
    ]
    pss.collapse_duplicates(cands)
    dups = {c.path: c.is_duplicate_of for c in cands if c.is_duplicate_of}
    assert dups == {"D:\\v\\same.mp3": "D:\\m\\same.mp3"}


# ---------------------------------------------------------------------------
# screening + structural metric
# ---------------------------------------------------------------------------


def test_edge_silence():
    y = np.zeros(4 * FS)
    y[int(1.5 * FS):int(2.5 * FS)] = 0.5
    lead, trail = pss.edge_silence(y, FS)
    assert abs(lead - 1.5) < 1e-9
    assert abs(trail - (1.5 - 1 / FS)) < 0.01
    assert pss.edge_silence(np.zeros(1000), FS) == (1000 / FS, 1000 / FS)


def _tone_chirp_repeats(duration_s=30.0):
    """Tone pattern that repeats every ~8 s (high long-lag recurrence)."""
    t = np.arange(int(duration_s * FS)) / FS
    seg = (np.sin(2 * np.pi * 220 * t[:int(8 * FS)])
           + 0.5 * np.sin(2 * np.pi * 330 * t[:int(8 * FS)]))
    reps = int(np.ceil(duration_s / 8.0))
    return np.tile(seg, reps)


def test_structural_scores_rank_repetition_above_noise():
    rng = np.random.default_rng(11)
    noise = rng.normal(0, 0.1, int(30 * FS))
    rep = _tone_chirp_repeats()
    r_rep = pss.structural_scores(rep, FS)["r_long"]
    r_noise = pss.structural_scores(noise, FS)["r_long"]
    assert r_rep > r_noise


def test_structural_scores_deterministic():
    rep = _tone_chirp_repeats(duration_s=20.0)
    a = pss.structural_scores(rep, FS)
    b = pss.structural_scores(rep, FS)
    assert a["r_long"] == b["r_long"]
    assert a["peak_lag_s"] == b["peak_lag_s"]


# ---------------------------------------------------------------------------
# pre-declared selection rules (synthetic pool)
# ---------------------------------------------------------------------------


def _synthetic_pool():
    tex = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0]),
           "c": np.array([0.7, 0.7]), "d": np.array([0.9, 0.1]),
           "e": np.array([0.2, 0.8])}
    return [
        _candidate("1" * 64, "D:\\m\\aaa.mp3", duration=200.0, r_long=0.90,
                   texture=tex["a"]),
        _candidate("2" * 64, "D:\\m\\bbb.mp3", duration=160.0, r_long=0.99,
                   texture=tex["b"]),
        _candidate("3" * 64, "D:\\m\\ccc.mp3", duration=170.0, r_long=0.95,
                   texture=tex["c"]),
        _candidate("4" * 64, "D:\\m\\ddd.mp3", duration=120.0, r_long=0.80,
                   texture=tex["d"]),
        _candidate("5" * 64, "D:\\m\\eee.mp3", duration=140.0, r_long=0.85,
                   texture=tex["e"]),
    ]


def test_selection_rules():
    sel = pss.select_sources(_synthetic_pool())
    # B: highest R_long among duration>=150 (aaa 0.90, bbb 0.99, ccc 0.95)
    assert sel["song_b"].path == "D:\\m\\bbb.mp3"
    # median duration of pool: 170 s -> among {aaa(200,0.90), ccc(170,0.95),
    # ddd(120,0.80), eee(140,0.85)}: ccc is closest to 170
    assert sel["song_a"].path == "D:\\m\\ccc.mp3"
    # interference: max mean texture distance to a's texture [0,1] (B) and
    # ccc's [0.7071,0.7071] (A): aaa 0.646 > ddd 0.596 > eee 0.247
    assert sel["interference"].path == "D:\\m\\aaa.mp3"


def test_selection_requires_b_longer_than_a_structurally():
    # aaa has the highest R_long overall; B must still be B-eligible &
    # chosen first; A must come from below-B candidates only.
    pool = _synthetic_pool()
    sel = pss.select_sources(pool)
    assert sel["song_a"].r_long < sel["song_b"].r_long


# ---------------------------------------------------------------------------
# kit build: deterministic self-check on a SHORT synthetic buffer
# ---------------------------------------------------------------------------


def test_run_self_check_roundtrip(tmp_path):
    payload = _tone_chirp_repeats(duration_s=6.0)
    buffer = mp.render_marker_buffer(payload, FS)
    spec = mp.buffer_spec(len(payload), FS)
    buf_path = tmp_path / "BUF-T.wav"
    ref_path = tmp_path / "REF-T.wav"
    kb.write_wav_int16(buf_path, buffer, FS)
    kb.write_wav_int16(ref_path, payload, FS)
    check = kb.run_self_check("BUF-T", buf_path, spec,
                              int(spec.payload_start_sample), 0,
                              len(payload), ref_path, tmp_path)
    assert check["passed"]
    assert check["gt_status"] == "GT_VALID"
    assert check["n_marker_candidates"] == 2
    assert abs(check["gt_offset_s_payload_in_trimmed"]
               - (kb.SELF_CHECK_LEAD_S - mp.PRE_TRIM_MARGIN_S)) < 1e-9
    assert check["payload_placement"]["payload_equals_reference_slice"]
    assert not check["marker_leakage_check"]["leakage"]


def test_self_check_seed_deterministic():
    assert kb.self_check_seed("BUF-A") == kb.self_check_seed("BUF-A")
    assert kb.self_check_seed("BUF-A") != kb.self_check_seed("BUF-B1")
