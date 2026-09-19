"""Kdenlive final-stratum preparation tests.

Research-only: verifies the blind pair freeze (determinism, blindness,
coverage), the timing-record schema, the synthetic-fixture XML extractor,
and that the owner-facing preparation stays GT/comparator/copyright clean.
No final Kdenlive project is read (none exists yet), and no comparator is
invoked anywhere.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest

from experiments.applied_system import final_kdenlive_prep as prep
from experiments.applied_system import kdenlive_project_xml as kpx

REPO = Path(__file__).resolve().parents[1]
KDENLIVE_DIR = REPO / "experiments" / "applied_system" / "final_pack" / "kdenlive"
FREEZE_PATH = KDENLIVE_DIR / "kdenlive_pair_freeze.json"
PACK_MANIFEST_PATH = KDENLIVE_DIR / "kdenlive_owner_pack_manifest.json"
MANIFEST_PATH = (REPO / "experiments" / "applied_system" / "final_pack"
                 / "final_acquisition_manifest.json")
QC_PATH = (REPO / "experiments" / "applied_system" / "final_pack" / "results"
           / "final_acquisition_qc.json")
INSTRUCTIONS_PATH = (REPO / "docs" / "research" / "applied_system"
                     / "OWNER_KDENLIVE_FINAL_INSTRUCTIONS.md")


@pytest.fixture(scope="module")
def freeze():
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def qc():
    return json.loads(QC_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# selection rule — determinism, quotas, blindness
# ---------------------------------------------------------------------------


def test_largest_remainder_quotas_mirror_frozen_shape():
    counts = {"ORDINARY": 10, "LOW_LEVEL": 3, "TAP_DOMINANT": 3,
              "INTERFERENCE": 4, "PARTIAL": 2, "DEVICE_VARIATION": 2}
    quotas = prep.largest_remainder_quotas(counts, 10)
    assert quotas == {"ORDINARY": 4, "INTERFERENCE": 2, "LOW_LEVEL": 1,
                      "TAP_DOMINANT": 1, "PARTIAL": 1, "DEVICE_VARIATION": 1}
    assert sum(quotas.values()) == 10


def test_largest_remainder_tie_breaks_by_name():
    assert prep.largest_remainder_quotas({"YB": 1, "YA": 1}, 1) == \
        {"YB": 0, "YA": 1}


def test_pair_id_mapping_is_ascending_and_deterministic():
    rows = [{"take": "final03", "source_slot": "S03", "condition": "C1",
             "session": "S", "room": "R", "recording_device": "D",
             "playback_device": "P", "primary": True},
            {"take": "final01", "source_slot": "S01", "condition": "C2",
             "session": "S", "room": "R", "recording_device": "D",
             "playback_device": "P", "primary": True}]
    pairs = prep.assign_pair_ids(prep.select_pairs(rows, 2))
    assert [pairs["pair%02d" % i]["take"] for i in (1, 2)] == \
        ["final01", "final03"]


def test_selection_reproduces_the_committed_freeze(freeze, manifest):
    body = manifest["body"]
    selected = prep.select_pairs(prep.selection_rows(body))
    pairs = prep.assign_pair_ids(selected)
    # the committed freeze enriches each pair with hash/provenance fields;
    # the selection-produced base fields must be identical
    frozen_base = {
        pid: {k: v for k, v in pair.items() if k in pairs[pid]}
        for pid, pair in freeze["body"]["pairs"].items()}
    assert pairs == frozen_base


def test_selection_ignores_every_non_allowlisted_field(freeze, manifest):
    """Structural blindness proof: garbage every non-allowlisted field."""
    body = json.loads(json.dumps(manifest["body"]))
    for rec in body["takes"].values():
        for key in list(rec):
            if key not in prep.SELECT_ALLOWED_KEYS:
                rec[key] = "OUTCOME_GARBAGE" if isinstance(rec[key], str) \
                    else 123987
    selected = prep.select_pairs(prep.selection_rows(body))
    takes = sorted(p["take"] for p in selected)
    frozen_takes = sorted(p["take"] for p in freeze["body"]["pairs"].values())
    assert takes == frozen_takes


def test_selection_rows_only_carry_allowlisted_keys(manifest):
    rows = prep.selection_rows(manifest["body"])
    assert rows and all(set(r) <= prep.SELECT_ALLOWED_KEYS for r in rows)
    assert all(r["primary"] for r in rows)
    assert len({r["take"] for r in rows}) == 24


# ---------------------------------------------------------------------------
# committed freeze — seal, shape, coverage, input hashes
# ---------------------------------------------------------------------------


def test_freeze_canonical_hash_is_sealed(freeze):
    body = freeze["body"]
    assert prep.canonical_sha256(body) == freeze["pair_freeze_sha256"]


def test_freeze_has_exactly_pair01_to_pair10(freeze):
    pairs = freeze["body"]["pairs"]
    assert sorted(pairs) == ["pair%02d" % i for i in range(1, 11)]
    takes = [p["take"] for p in pairs.values()]
    assert len(set(takes)) == 10
    assert takes == sorted(takes)


def test_freeze_selection_rule_and_authority_hashes(freeze):
    body = freeze["body"]
    assert body["selection_rule_id"] == "KDENLIVE-SELECT-V1"
    assert body["authority"]["manifest_hash"] == \
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["manifest_hash"]
    assert body["authority"]["qc_freeze_sha256"] == \
        json.loads(QC_PATH.read_text(encoding="utf-8"))["qc_freeze_sha256"]
    assert body["kdenlive_environment"]["installed_version"].startswith("26.08")


def test_freeze_covers_every_benchmark_condition(freeze, manifest):
    pairs = freeze["body"]["pairs"]
    frozen_conditions = set(p["condition"] for p in pairs.values())
    all_conditions = set(manifest["body"]["counts"]["conditions"])
    assert frozen_conditions == all_conditions
    counts = {}
    for p in pairs.values():
        counts[p["condition"]] = counts.get(p["condition"], 0) + 1
    assert counts == freeze["body"]["coverage"]["condition_counts"]
    assert len({p["session"] for p in pairs.values()}) >= 3
    assert len({p["recording_device"] for p in pairs.values()}) >= 2
    assert len({p["room"] for p in pairs.values()}) >= 2


def test_freeze_input_hashes_match_the_frozen_sources(freeze, qc, manifest):
    trimmed = qc["body"]["trimmed_input_sha256"]
    refs = manifest["body"]["references"]
    for pair in freeze["body"]["pairs"].values():
        assert pair["recording_sha256"] == trimmed[pair["take"]]
        assert pair["reference_sha256"] == \
            refs["REF-" + pair["source_slot"]]["sha256"]
        assert pair["reference_slot"] == "REF-" + pair["source_slot"]


def test_freeze_carries_no_outcome_fields(freeze):
    forbidden = {"gt", "gt_offset", "offset_s", "marker", "wrong_reference",
                 "comparator", "alignment_result"}
    for pair in freeze["body"]["pairs"].values():
        assert not (set(pair) & forbidden)
        assert not (set(freeze["body"]) & forbidden)


def test_project_filenames_are_deterministic(freeze):
    for i in range(1, 11):
        pid = "pair%02d" % i
        pair = freeze["body"]["pairs"][pid]
        assert pair["owner_project_file"] == \
            "owner_pack/%s/%s.kdenlive" % (pid, pid)


# ---------------------------------------------------------------------------
# owner pack manifest + owner-facing blindness
# ---------------------------------------------------------------------------


def test_pack_manifest_matches_freeze(freeze):
    pack = json.loads(PACK_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert pack["pair_freeze_sha256"] == freeze["pair_freeze_sha256"]
    assert sorted(pack["pairs"]) == sorted(freeze["body"]["pairs"])
    for pid, entry in pack["pairs"].items():
        pair = freeze["body"]["pairs"][pid]
        assert entry["recording_sha256"] == pair["recording_sha256"]
        assert entry["reference_sha256"] == pair["reference_sha256"]
        assert entry["expected_project_file"] == pair["owner_project_file"]


def test_pack_media_on_disk_matches_manifest():
    pack = json.loads(PACK_MANIFEST_PATH.read_text(encoding="utf-8"))
    base = KDENLIVE_DIR
    for pid, entry in pack["pairs"].items():
        rec = base / entry["recording"]
        ref = base / entry["reference"]
        if not rec.parent.exists():
            pytest.skip("owner pack not materialized in this checkout")
        assert prep.sha256_file(rec) == entry["recording_sha256"]
        assert prep.sha256_file(ref) == entry["reference_sha256"]


def test_owner_instructions_carry_no_scientific_metadata():
    text = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    low = text.lower()
    for token in prep.OWNER_FACING_FORBIDDEN_SUBSTRINGS:
        assert token.lower() not in low, "owner instructions leak %r" % token


def test_owner_instructions_prescribe_two_distinct_audio_tracks():
    """The two pure-WAV inputs must be prescribed onto two distinct AUDIO
    timeline tracks (A1 and A2), both starting at the neutral 00:03:00
    headroom (KDENLIVE-PLACEMENT-V2, pair01 audit 2026-09-20) — never on
    video tracks, and never at the v1 00:00 placement that blocks negative
    alignment moves at the timeline origin."""
    text = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    placement = [line for line in text.splitlines() if "拖到" in line]
    assert placement, "no timeline placement step found"
    placed = "\n".join(placement)
    assert "recording.wav" in placed and "reference.wav" in placed, \
        "placement step must cover both inputs"
    assert "音频轨道" in placed, "inputs must be placed on audio tracks"
    assert re.search(r"A1", placed) and re.search(r"A2", placed), \
        "recording.wav -> A1 and reference.wav -> A2 required"
    assert placed.index("A1") < placed.index("A2"), \
        "the two clips must sit on distinct audio tracks"
    assert "00:03:00" in placed, \
        "both clips must start at the 00:03:00 headroom (KDENLIVE-PLACEMENT-V2)"
    assert "最左边 00:00" not in text, \
        "the v1 00:00 placement must not come back (pair01 audit)"
    for no, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bV[12]\b", line):
            # the only tolerated V1/V2 mentions are procedure version
            # labels; a video-track prescription would name tracks or
            # dragging in the same line
            assert not re.search(r"轨道|拖到|视频", line), \
                "owner instructions prescribe video tracks at line %d" % no


def test_timer_console_labels_carry_no_scientific_metadata():
    for label in prep.TIMING_OBSERVATIONS.values():
        for token in prep.OWNER_FACING_FORBIDDEN_SUBSTRINGS:
            assert token.lower() not in label.lower()


def test_owner_pack_file_naming_is_neutral():
    pack = json.loads(PACK_MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in pack["pairs"].values():
        assert Path(entry["recording"]).name == "recording.wav"
        assert Path(entry["reference"]).name == "reference.wav"
        assert Path(entry["expected_project_file"]).name == \
            Path(entry["expected_project_file"]).stem + ".kdenlive"


# ---------------------------------------------------------------------------
# timing record schema
# ---------------------------------------------------------------------------


def test_timing_record_schema_accepts_valid_record():
    rec = prep.build_timing_record(
        "pair01", "2026-09-20T00:00:00Z", "2026-09-20T00:04:30Z",
        270.0, "ALIGNED", "")
    assert prep.validate_timing_record(rec) == []
    assert rec["schema_version"] == "KDENLIVE-TIMER-V1"


@pytest.mark.parametrize("mutation", [
    {"observation": "MAGIC"}, {"elapsed_seconds": -1.0},
])
def test_timing_record_schema_rejects_bad_records(mutation):
    kwargs = dict(pair="pair01", start_utc="2026-09-20T00:00:00Z",
                  end_utc="2026-09-20T00:04:30Z", elapsed_seconds=270.0,
                  observation="ALIGNED")
    kwargs.update(mutation)
    with pytest.raises(ValueError):
        prep.build_timing_record(**kwargs)


def test_timing_record_schema_reports_missing_fields():
    assert "missing field: observation" in prep.validate_timing_record(
        {"pair": "pair01", "elapsed_seconds": 1.0})


# ---------------------------------------------------------------------------
# owner timer pair-ID validation (canonical zero-padded IDs must be accepted)
# ---------------------------------------------------------------------------

TIMER_PATH = KDENLIVE_DIR / "owner_timer.py"


@pytest.fixture(scope="module")
def timer():
    spec = importlib.util.spec_from_file_location(
        "owner_timer_under_test", TIMER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_timer_accepts_every_canonical_pair_id(timer):
    for i in range(1, prep.PAIR_COUNT + 1):
        assert timer.valid_pair("pair%02d" % i) == "pair%02d" % i


def test_timer_accepts_unpadded_aliases_and_returns_canonical(timer):
    for i in range(1, prep.PAIR_COUNT + 1):
        assert timer.valid_pair("pair%d" % i) == "pair%02d" % i


def test_timer_alias_and_canonical_agree(timer):
    for i in range(1, prep.PAIR_COUNT + 1):
        assert timer.valid_pair("pair%d" % i) == \
            timer.valid_pair("pair%02d" % i)


@pytest.mark.parametrize("bad", [
    "pair00", "pair0", "pair11", "pair001", "pair", "pair01x",
    "pair-1", "pair 01", "pair1.5", "", "abc", "pairten", "10x",
])
def test_timer_rejects_out_of_range_and_malformed_ids(timer, bad):
    with pytest.raises(SystemExit):
        timer.valid_pair(bad)


def test_timer_accepts_documented_invocation_forms(timer):
    assert timer.valid_pair("pair01") == "pair01"
    assert timer.valid_pair(" pair07 ") == "pair07"
    assert timer.valid_pair("PAIR10") == "pair10"


# ---------------------------------------------------------------------------
# synthetic-fixture XML extraction (no final project is ever touched)
# ---------------------------------------------------------------------------


FPS30 = ('<profile description="HD 1080p 30 fps" width="1920" height="1080"'
         ' progressive="1" sample_aspect_num="1" sample_aspect_den="1"'
         ' display_aspect_num="16" display_aspect_den="9"'
         ' frame_rate_num="30" frame_rate_den="1" colorspace="709"/>')

SYNTHETIC_PROJECT = f'''<mlt LC_NUMERIC="C" version="7.30.0" title="Kdenlive">
  {FPS30}
  <producer id="producer0" in="00:00:00.000" out="00:00:20.000">
    <property name="mlt_service">avformat-novalidate</property>
    <property name="resource">C:\\somewhere\\pair01\\recording.wav</property>
    <property name="kdenlive:clipname">recording.wav</property>
  </producer>
  <producer id="producer1" in="00:00:00.000" out="00:01:00.000">
    <property name="mlt_service">avformat-novalidate</property>
    <property name="resource">C:\\somewhere\\pair01\\reference.wav</property>
    <property name="kdenlive:clipname">reference.wav</property>
  </producer>
  <playlist id="main_bin">
    <entry producer="producer0" in="0" out="600"/>
    <entry producer="producer1" in="0" out="1800"/>
  </playlist>
  <playlist id="playlist0">
    <blank length="90"/>
    <entry producer="producer0" in="0" out="2879"/>
  </playlist>
  <playlist id="playlist1">
    <entry producer="producer1" in="00:00:01.000" out="00:00:10.000"/>
  </playlist>
  <tractor id="tractor0" title="Kdenlive Sequence" global_feed="1">
    <track producer="background"/>
    <track producer="playlist0"/>
    <track producer="playlist1"/>
  </tractor>
</mlt>
'''


def _expected():
    return {"recording": "recording.wav", "reference": "reference.wav"}


def test_synthetic_xml_positions_and_offset():
    parsed = kpx.parse_project(SYNTHETIC_PROJECT.encode("utf-8"))
    assert parsed["frame_rate"] == pytest.approx(30.0)
    placed = {p["resource"]: p for p in kpx.placements(parsed)}
    # bin entries must not count as placements
    assert len(placed) == 2
    rec = placed["C:\\somewhere\\pair01\\recording.wav"]
    ref = placed["C:\\somewhere\\pair01\\reference.wav"]
    assert rec["start_frame"] == 90
    assert rec["end_frame"] == 90 + 2880
    assert ref["start_frame"] == 0
    # timecode in="00:00:01.000" at 30 fps
    assert ref["in_frame"] == 30
    summary = kpx.project_summary(parsed, _expected())
    assert summary["state"] == "OK"
    assert summary["clip_offset_frames"] == 90


def test_synthetic_xml_doc_properties_recovered():
    project = SYNTHETIC_PROJECT.replace(
        "</producer>",
        "<property name=\"kdenlive:docproperties.version\">1.2</property>"
        "</producer>", 1)
    parsed = kpx.parse_project(project.encode("utf-8"))
    assert parsed["doc_properties"]["kdenlive:docproperties.version"] == "1.2"


def test_synthetic_xml_missing_clip_state():
    parsed = kpx.parse_project(SYNTHETIC_PROJECT.encode("utf-8"))
    summary = kpx.project_summary(
        parsed, {"recording": "recording.wav", "reference": "absent.wav"})
    assert summary["state"] == "INCOMPLETE"
    assert summary["failures"][0]["state"] == "MISSING_EXPECTED_CLIP"


def test_synthetic_xml_bin_only_clip_is_not_placed():
    project = SYNTHETIC_PROJECT.replace(
        '  <playlist id="playlist1">\n'
        '    <entry producer="producer1" in="00:00:01.000"'
        ' out="00:00:10.000"/>\n  </playlist>\n', '')
    parsed = kpx.parse_project(project.encode("utf-8"))
    summary = kpx.project_summary(parsed, _expected())
    states = {f["role"]: f["state"] for f in summary["failures"]}
    assert states["reference"] == "NOT_PLACED_ON_TIMELINE"


# ---------------------------------------------------------------------------
# post-freeze correction v2 (pair01 audit 2026-09-20): neutral placement
# headroom, run-id/rerun policy, preserved pair01 run-1 evidence
# ---------------------------------------------------------------------------

EVIDENCE_DIR = KDENLIVE_DIR / "owner_run_evidence" / "pair01_run1"
RERUN_MANIFEST_PATH = KDENLIVE_DIR / "kdenlive_owner_pack_rerun_manifest.json"
RUN_POLICY_PATH = KDENLIVE_DIR / "kdenlive_run_policy.json"


def test_run_ids_canonical_and_rerun_forms():
    assert prep.parse_run_id("pair01") == "pair01"
    assert prep.parse_run_id(" pair7 ") == "pair07"
    assert prep.parse_run_id("PAIR10") == "pair10"
    assert prep.parse_run_id("pair01r2") == "pair01r2"
    assert prep.parse_run_id("Pair01R2") == "pair01r2"
    assert prep.parse_run_id("pair10r9") == "pair10r9"
    assert prep.canonical_pair_of("pair01r2") == "pair01"
    assert prep.canonical_pair_of("pair07") == "pair07"


@pytest.mark.parametrize("bad", [
    "pair00", "pair11", "pair001", "pair", "pair01x", "pair-1", "",
    "pair01r1", "pair01r10", "pair01rx", "pair01r", "pair01rr2",
    "pair1.5", "pairten",
])
def test_run_ids_reject_malformed_and_r1(bad):
    with pytest.raises(ValueError):
        prep.parse_run_id(bad)


def test_timer_accepts_rerun_id_and_canonicalizes(timer):
    assert timer.valid_pair("pair01r2") == "pair01r2"
    assert timer.valid_pair(" pair01R2 ") == "pair01r2"
    assert timer.valid_pair("pair01") == "pair01"
    with pytest.raises(SystemExit):
        timer.valid_pair("pair01r1")


@pytest.mark.parametrize("num_bytes,expected", [
    (14427492, 180),  # longest frozen reference: 150.286 s -> 3 min
    (5760000, 60),    # exactly 60 s
    (5769600, 120),   # 60.1 s rounds up to the next whole minute
    (48000, 60),      # floor of one minute
])
def test_headroom_rule_is_whole_minute_over_longest_input(num_bytes, expected):
    assert prep.placement_headroom_seconds(num_bytes) == expected


def test_headroom_covers_every_frozen_pair_from_manifest_sizes_only():
    pack = json.loads(PACK_MANIFEST_PATH.read_text(encoding="utf-8"))
    headroom = prep.pack_headroom_seconds(pack)
    assert headroom == 180  # KDENLIVE-PLACEMENT-V2, uniform for all 10 pairs
    longest = max(max(e["recording_bytes"], e["reference_bytes"])
                  for e in pack["pairs"].values())
    assert prep.wav_seconds(longest) <= headroom


def test_headroom_absorbs_any_alignment_move_kdenlive_can_request():
    """Kdenlive's align handler moves a clip placed at headroom H to
    H + shift, where the correlation shift is bounded by the clip lengths
    themselves ([-L_child, +L_main] frames). Verify that bound in frames so
    every possible request stays non-negative for every frozen pair — no
    observed outcome involved."""
    fps = 60  # the profile the owner's project actually used
    pack = json.loads(PACK_MANIFEST_PATH.read_text(encoding="utf-8"))
    h_frames = prep.pack_headroom_seconds(pack) * fps
    for entry in pack["pairs"].values():
        for num_bytes in (entry["recording_bytes"], entry["reference_bytes"]):
            length_frames = int(prep.wav_seconds(num_bytes) * fps) + 1
            assert h_frames - length_frames >= 0, entry["pack_dir"]


def test_run_policy_and_rerun_manifest_are_consistent():
    policy = json.loads(RUN_POLICY_PATH.read_text(encoding="utf-8"))
    assert policy["status"] == "KDENLIVE_RUN_POLICY_V2"
    assert policy["procedure"] == prep.PLACEMENT_VERSION
    pack = json.loads(PACK_MANIFEST_PATH.read_text(encoding="utf-8"))
    for pair, rule in policy["rules"].items():
        assert pair in pack["pairs"]
        assert prep.canonical_pair_of(rule["scoring_run"]) == pair
        assert rule["scoring_run"] not in rule["void_runs"]
        assert (KDENLIVE_DIR / rule["evidence_dir"]).is_dir()
    reruns = json.loads(RERUN_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(reruns["reruns"]) == \
        {r["scoring_run"] for r in policy["rules"].values()}
    for run_id, entry in reruns["reruns"].items():
        frozen = pack["pairs"][entry["canonical_pair"]]
        assert entry["recording_sha256"] == frozen["recording_sha256"]
        assert entry["reference_sha256"] == frozen["reference_sha256"]
        assert entry["expected_project_file"] == \
            "owner_pack/%s/%s.kdenlive" % (run_id, run_id)
        assert entry["procedure"] == prep.PLACEMENT_VERSION


def test_prep_verify_rerun_and_policy_passes():
    if not (KDENLIVE_DIR / "owner_pack" / "pair01").exists():
        pytest.skip("owner pack not materialized in this checkout")
    prep.verify_rerun_and_policy()


def test_pair01_run1_evidence_is_hash_identical():
    expected_hashes = {
        "pair01.kdenlive":
            "b2b3fb5aa8dea8e7f24f4628bd87d34a28f7ffd3ca846bc68bf3322bd454af8e",
        "pair01_run1.timing_log.jsonl":
            "0d712bc35cdecaaf305c3a20e47b8b2cdbc36c323bfd58247f0d0aa636f8c4ee",
    }
    for name, digest in expected_hashes.items():
        copy = EVIDENCE_DIR / name
        assert copy.is_file(), name
        assert prep.sha256_file(copy) == digest, name
    originals = {
        "pair01.kdenlive":
            KDENLIVE_DIR / "owner_pack" / "pair01" / "pair01.kdenlive",
        "pair01_run1.timing_log.jsonl":
            KDENLIVE_DIR / "owner_pack" / "timing_log.jsonl",
    }
    if not originals["pair01.kdenlive"].parent.exists():
        pytest.skip("owner pack not materialized in this checkout")
    for name, original in originals.items():
        assert prep.sha256_file(original) == expected_hashes[name], name


def test_pair01_run1_timing_record_is_the_observed_failure():
    line = (EVIDENCE_DIR / "pair01_run1.timing_log.jsonl") \
        .read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["pair"] == "pair01"
    assert rec["observation"] == "OTHER"
    assert rec["notes"] == "Cannot move clip to frame -17472"
    assert rec["schema_version"] == "KDENLIVE-TIMER-V1"
    assert rec["start_utc"] == "2026-09-19T20:55:32Z"
    assert rec["end_utc"] == "2026-09-19T20:59:23Z"


FPS60 = ('<profile description="HD 1080p 60 fps" width="1920" height="1080"'
         ' progressive="1" sample_aspect_num="1" sample_aspect_den="1"'
         ' display_aspect_num="16" display_aspect_den="9"'
         ' frame_rate_num="60" frame_rate_den="1" colorspace="709"/>')


def _headroom_project(blank_frames):
    blank = '<blank length="%d"/>' % blank_frames if blank_frames else ""
    return f'''<mlt LC_NUMERIC="C" version="7.30.0" title="Kdenlive">
  {FPS60}
  <producer id="producer0" in="00:00:00.000" out="00:01:05.400">
    <property name="mlt_service">avformat-novalidate</property>
    <property name="resource">C:\\somewhere\\recording.wav</property>
  </producer>
  <producer id="producer1" in="00:00:00.000" out="00:02:30.267">
    <property name="mlt_service">avformat-novalidate</property>
    <property name="resource">C:\\somewhere\\reference.wav</property>
  </producer>
  <playlist id="main_bin">
    <entry producer="producer0" in="0" out="3924"/>
    <entry producer="producer1" in="0" out="9016"/>
  </playlist>
  <playlist id="playlist0">
    {blank}
    <entry producer="producer0" in="0" out="3924"/>
  </playlist>
  <playlist id="playlist1">
    {blank}
    <entry producer="producer1" in="0" out="9016"/>
  </playlist>
  <tractor id="tractor0" title="Kdenlive Sequence" global_feed="1">
    <track producer="background"/>
    <track producer="playlist0"/>
    <track producer="playlist1"/>
  </tractor>
</mlt>
'''


def test_clip_offset_is_invariant_under_common_headroom_shift():
    """Procedure v2 shifts both clips by the same headroom; the scored
    quantity (clip_offset_frames) must not move."""
    base = kpx.project_summary(
        kpx.parse_project(_headroom_project(0).encode("utf-8")), _expected())
    shifted = kpx.project_summary(
        kpx.parse_project(_headroom_project(5400).encode("utf-8")),
        _expected())
    assert base["state"] == "OK" and shifted["state"] == "OK"
    assert base["clip_offset_frames"] == shifted["clip_offset_frames"]
    assert shifted["roles"]["recording"]["start_frame"] == \
        base["roles"]["recording"]["start_frame"] + 5400
    assert shifted["roles"]["reference"]["start_frame"] == \
        base["roles"]["reference"]["start_frame"] + 5400


# ---------------------------------------------------------------------------
# comparator hygiene + no copyrighted media tracked
# ---------------------------------------------------------------------------


FORBIDDEN_IMPORT_TOKENS = ("pilot_harness", "runners", "rhythmalign",
                           "panako", "gcc_phat", "ncc", "alignment_engine",
                           "auto_sync", "numpy", "scipy", "soundfile",
                           "librosa", "subprocess")


def _imported_modules(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("module_path", [
    REPO / "experiments" / "applied_system" / "final_kdenlive_prep.py",
    REPO / "experiments" / "applied_system" / "kdenlive_project_xml.py",
    KDENLIVE_DIR / "owner_timer.py",
])
def test_preparation_modules_import_no_comparators_or_dsp(module_path):
    for name in _imported_modules(module_path):
        root = name.split(".")[0].lower()
        assert not any(tok in root for tok in FORBIDDEN_IMPORT_TOKENS), \
            "%s imports %s" % (module_path.name, name)


def test_no_copyrighted_media_is_tracked():
    out = subprocess.run(
        ["git", "ls-files", "experiments/applied_system/final_pack/kdenlive"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    assert out, "kdenlive preparation files must be committed"
    allowed = {".py", ".json", ".md"}
    for path in out:
        assert Path(path).suffix in allowed, "tracked media: %s" % path


def test_owner_pack_directory_is_gitignored():
    probe = "experiments/applied_system/final_pack/kdenlive/owner_pack/x.wav"
    out = subprocess.run(["git", "check-ignore", probe], cwd=REPO,
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == probe
