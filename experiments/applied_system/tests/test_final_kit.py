"""Research-only tests: final source selection + final acquisition kit.

All tests run on synthetic audio or synthetic candidate records — the
owner's media library and the frozen final-pack media are never touched.
NO comparator is invoked anywhere in this module.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system import final_kit_build as fkb  # noqa: E402
from experiments.applied_system import final_source_selection as fss  # noqa: E402
from experiments.applied_system import marker_protocol as mp  # noqa: E402

FS = mp.FS


# ---------------------------------------------------------------------------
# frozen allocation structure (protocol item 15 / 17)
# ---------------------------------------------------------------------------


def test_condition_allocation_counts():
    primary = {t: c for t, (s, c, k) in fkb.CONDITIONS.items()
               if t in fkb.PRIMARY_TAKES}
    counts = {}
    for c in primary.values():
        counts[c] = counts.get(c, 0) + 1
    assert counts == {"ORDINARY": 10, "LOW_LEVEL": 3, "TAP_DOMINANT": 3,
                      "INTERFERENCE": 4, "PARTIAL": 2,
                      "DEVICE_VARIATION": 2}
    assert len(fkb.PRIMARY_TAKES) == 24
    assert len(fkb.CONDITIONS) == 26
    # low/tap split binds to slots S01-S06, three each
    low = {t for t, c in primary.items() if c == "LOW_LEVEL"}
    tap = {t for t, c in primary.items() if c == "TAP_DOMINANT"}
    assert {fkb.CONDITIONS[t][0] for t in low} == {"S01", "S03", "S05"}
    assert {fkb.CONDITIONS[t][0] for t in tap} == {"S02", "S04", "S06"}
    # interference takes bind to S07-S10; partial to S01-S02;
    # device-variation to S09-S10
    assert {fkb.CONDITIONS[f"final{i:02d}"][0] for i in range(17, 21)} == \
        {"S07", "S08", "S09", "S10"}
    assert {fkb.CONDITIONS[t][0] for t in ("final21", "final22")} == \
        {"S01", "S02"}
    assert {fkb.CONDITIONS[t][0] for t in ("final23", "final24")} == \
        {"S09", "S10"}
    # strict repeats pair with ordinary final01/final02
    assert fkb.CONDITIONS["repeat01"][:2] == ("S01",
                                              "ORDINARY_REPEAT_STRICT_PAIR"
                                              "_OF_FINAL01")
    assert fkb.CONDITIONS["repeat02"][0] == "S02"


def test_wrong_reference_rotation():
    for i in range(1, 25):
        take = f"final{i:02d}"
        assert fkb.wrong_reference_slot(take) == f"S{(i % 10) + 1:02d}"
        assert fkb.wrong_reference_slot(take) != fkb.CONDITIONS[take][0], \
            "rotation must never offer a take its true source"


def test_partial_start_rule():
    assert fkb.partial_start_s(200.0) == 90.0
    assert fkb.partial_start_s(150.0) == 90.0
    assert abs(fkb.partial_start_s(148.138) - 88.138) < 1e-9
    assert abs(fkb.partial_start_s(83.333) - 23.333) < 1e-9
    assert fkb.partial_start_s(60.0) == 0.0


def test_session_room_device_design():
    all_takes = [t for cfg in fkb.SESSIONS.values() for t in cfg["takes"]]
    assert sorted(all_takes) == sorted(fkb.CONDITIONS)
    assert len(fkb.SESSIONS) == 3
    rooms = {cfg["room"] for cfg in fkb.SESSIONS.values()}
    devs = {cfg["recording_device"] for cfg in fkb.SESSIONS.values()}
    assert len(rooms) == 2 and len(devs) == 2
    # device-variation takes must sit in the session using the OTHER device
    assert fkb.SESSIONS["SESSION_3"]["recording_device"] == "D2"
    assert fkb.SESSIONS["SESSION_1"]["recording_device"] == "D1"
    for take in ("final23", "final24"):
        session = next(s for s, cfg in fkb.SESSIONS.items()
                       if take in cfg["takes"])
        assert fkb.SESSIONS[session]["recording_device"] == "D2"


# ---------------------------------------------------------------------------
# FINAL-SELECT-V1 selection rule (synthetic pool)
# ---------------------------------------------------------------------------


def _pool_row(sha, r_long, texture):
    return {"sha256": sha, "r_long": r_long, "texture": texture,
            "basename": f"{sha}.mp3", "id3_title": sha, "duration_s": 120.0}


def test_selection_rule_final_select_v1():
    pool = []
    tex_pool = np.eye(6)
    for i in range(12):
        pool.append(_pool_row(sha=f"h{i:02d}",
                              r_long=0.90 + i * 0.001,
                              texture=tex_pool[i % 6]))
    # h09-h11 have the highest R_long (0.909-0.911)
    sel = fss.select_final_sources(pool)
    assert sel["ok"] and sel["pool_size"] == 12
    stress = {r["sha256"] for r in sel["stress"]}
    assert stress == {"h09", "h10", "h11"}
    refs = {r["sha256"] for r in sel["references"]}
    assert len(refs) == 10 and stress <= refs
    # remaining slots filled by ascending SHA-256 among the rest
    assert refs == stress | {f"h{i:02d}" for i in range(7)}
    # candidates are the two non-references h07, h08: one wins interference,
    # the other stays unused
    assert ({r["sha256"] for r in sel["unused"]}
            | {sel["interference"]["sha256"]}) == {"h07", "h08"}
    # slot numbering = ascending SHA-256 of the 10 refs
    ordered = sorted(refs)
    assert [sel["slots"][f"S{i:02d}"] for i in range(1, 11)] == ordered


def test_selection_rule_interference_texture_choice():
    # two remaining candidates; the one most distant from all reference
    # textures must win
    pool = []
    for i in range(11):  # h00..h10 share one texture, ascending R_long
        pool.append(_pool_row(sha=f"h{i:02d}", r_long=0.9 + i * 0.001,
                              texture=np.array([1.0, 0.0])))
    # two non-reference candidates: h11 is orthogonal to every reference,
    # h12 matches them
    pool.append(_pool_row(sha="h11", r_long=0.80,
                          texture=np.array([0.0, 1.0])))
    pool.append(_pool_row(sha="h12", r_long=0.79,
                          texture=np.array([1.0, 0.0])))
    sel = fss.select_final_sources(pool)
    assert sel["ok"]
    refs = {r["sha256"] for r in sel["references"]}
    assert "h11" not in refs and "h12" not in refs
    assert sel["interference"]["sha256"] == "h11"
    # non-reference candidates are h07 (loses the R_long cut), h11, h12
    assert {r["sha256"] for r in sel["unused"]} == {"h07", "h12"}


def test_selection_rule_insufficient_pool():
    pool = [_pool_row(sha=f"h{i:02d}", r_long=0.9, texture=np.array([1.0]))
            for i in range(10)]
    sel = fss.select_final_sources(pool)
    assert not sel["ok"] and sel["missing"] == 1


# ---------------------------------------------------------------------------
# buffer machinery on synthetic audio (digital validation only)
# ---------------------------------------------------------------------------


def _write_source(tmp_path, duration_s, seed=7):
    rng = np.random.default_rng(seed)
    y = 0.2 * rng.standard_t(8.0, int(round(duration_s * FS)))
    path = tmp_path / "src.wav"
    fkb.write_wav_int16(path, y, FS)
    return str(path)


def test_buffer_render_and_gt_bookkeeping(tmp_path):
    src = _write_source(tmp_path, 120.0)
    decoded = fkb.pss_decode(src)
    payload_len = int(round(fkb.PAYLOAD_S * FS))
    for start_sample in (0, int(round(30.0 * FS))):
        payload = decoded[start_sample:start_sample + payload_len]
        spec = mp.buffer_spec(len(payload), FS)
        buf_path = tmp_path / f"buf_{start_sample}.wav"
        fkb.write_wav_int16(buf_path, mp.render_marker_buffer(payload, FS),
                            FS)
        ref_path = tmp_path / f"ref_{start_sample}.wav"
        fkb.write_wav_int16(ref_path, decoded, FS)
        check = fkb.run_self_check(
            f"t{start_sample}", buf_path, spec, payload_len, ref_path,
            start_sample / FS, tmp_path)
        assert check["passed"]
        assert check["gt_status"] == "GT_VALID"
        assert check["n_marker_candidates"] == 2
        assert not check["marker_leakage_check"]["leakage"]
        assert check["payload_placement"]["payload_equals_reference_slice"]
        expected_payload_gt = fkb.SELF_CHECK_LEAD_S - mp.PRE_TRIM_MARGIN_S
        assert abs(check["gt_offset_s_payload_in_trimmed"]
                   - expected_payload_gt) < 1e-9
        assert abs(check["intended_reference_gt_s"]
                   - (expected_payload_gt - start_sample / FS)) < 1e-6


def test_marker_positions_match_protocol(tmp_path):
    src = _write_source(tmp_path, 70.0)
    decoded = fkb.pss_decode(src)
    payload_len = int(round(fkb.PAYLOAD_S * FS))
    spec = mp.buffer_spec(payload_len, FS)
    buf = mp.render_marker_buffer(decoded[:payload_len], FS)
    assert spec.total_len_samples == len(buf)
    assert spec.marker1_start_sample == 0
    assert spec.payload_start_sample == spec.chirp_len_samples \
        + spec.guard_len_samples
    assert spec.marker2_start_sample == spec.payload_end_sample \
        + spec.guard_len_samples
    # deterministic rerender
    buf2 = mp.render_marker_buffer(decoded[:payload_len], FS)
    assert np.array_equal(buf, buf2)


# ---------------------------------------------------------------------------
# committed artifact integrity (when present on this machine)
# ---------------------------------------------------------------------------


def _load_frozen(path):
    if not path.exists():
        pytest.skip(f"{path.name} not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_freeze_record_integrity():
    frozen = _load_frozen(fkb.FREEZE_PATH)
    body = frozen["body"]
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
    assert hashlib.sha256(canon).hexdigest() == frozen["freeze_sha256"]
    assert body["status"] == "FINAL_SOURCES_FROZEN"
    assert body["no_comparator_run"] is True
    assert len(body["references"]) == 10
    assert len(body["eligible_pool"]) >= 11
    stress = [r for r in body["references"].values()
              if r["repetitive_flag"] == "REPETITIVE_STRESS_SOURCE"]
    assert len(stress) >= 3
    assert body["interference"]["sha256"] not in \
        {r["sha256"] for r in body["references"].values()}


def test_manifest_integrity_and_counts():
    if not fkb.MANIFEST_PATH.exists():
        pytest.skip("final_acquisition_manifest.json not present")
    frozen = _load_frozen(fkb.MANIFEST_PATH)
    body = frozen["body"]
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
    assert hashlib.sha256(canon).hexdigest() == frozen["manifest_hash"]
    result = fkb.validate_kit(_load_frozen(fkb.FREEZE_PATH),
                              fkb.MANIFEST_PATH)
    assert result["ok"], result["failures"]
