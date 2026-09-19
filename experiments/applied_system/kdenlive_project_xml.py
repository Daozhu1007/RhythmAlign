"""Kdenlive project XML (MLT) placement extractor — preparation tooling.

Reads a saved Kdenlive project (.kdenlive, an MLT XML document) and
recovers, WITHOUT scoring anything:

- the profile (frame rate etc.) needed to interpret frame positions;
- every producer's resource (the imported media files) and Kdenlive
  document properties;
- every timeline playlist with blank/entry children and each clip's
  absolute start/end frame on its track;
- the placement summary used later by scoring: where the recording clip
  and the reference clip sit on the timeline, the frame offset between
  them, and a native-failure state when representable (expected clip
  missing from the project, or present in the bin but never placed).

This module is deliberately scoring-free: it never loads GT, never
compares a placement to GT, and never imports any comparator. Final
.kdenlive projects must not be touched until the owner has saved all
ten; development uses only synthetic fixtures (see
tests/test_kdenlive_final_prep.py).

MLT notes: playlist children are <blank length="N"/> and <entry
producer="P" in="A" out="B"/>; a clip's timeline position is the sum of
all preceding children's durations on that track. `in`/`out` may be
frame integers or "HH:MM:SS.mmm" timecodes (interpreted with the
document profile's frame rate).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import PurePath


def _profile_fps(profile) -> float:
    num = float(profile.get("frame_rate_num", "0") or 0)
    den = float(profile.get("frame_rate_den", "0") or 0)
    if num <= 0 or den <= 0:
        raise ValueError("profile lacks a usable frame rate")
    return num / den


def parse_mlt_time(value, fps: float) -> int:
    """MLT time value -> frames (int frames pass through; timecodes convert)."""
    text = str(value).strip()
    try:
        return int(text)
    except ValueError:
        pass
    if ":" not in text:
        raise ValueError("unrecognized MLT time value: %r" % value)
    parts = text.split(":")
    if len(parts) != 3:
        raise ValueError("unrecognized MLT timecode: %r" % value)
    hours, minutes, seconds = parts
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return int(round(total_seconds * fps))


def _properties(element) -> dict:
    return {p.get("name"): (p.text or "")
            for p in element.findall("property")}


def parse_project(xml_bytes: bytes) -> dict:
    """Parse one .kdenlive document into a plain data dictionary."""
    root = ET.fromstring(xml_bytes)
    profile = root.find("profile")
    if profile is None:
        raise ValueError("not a Kdenlive/MLT project: no <profile>")
    fps = _profile_fps(profile)

    producers = {}
    doc_properties = {}
    for producer in root.iter("producer"):
        pid = producer.get("id")
        props = _properties(producer)
        for key, value in props.items():
            if key.startswith("kdenlive:docproperties."):
                doc_properties[key] = value
        producers[pid] = {
            "id": pid,
            "resource": props.get("resource", ""),
            "mlt_service": props.get("mlt_service", ""),
            "kdenlive_clipname": props.get("kdenlive:clipname", ""),
        }

    playlists = []
    for playlist in root.iter("playlist"):
        entries = []
        position = 0
        for child in playlist:
            if child.tag == "blank":
                length = parse_mlt_time(child.get("length", "0"), fps)
                entries.append({
                    "kind": "blank", "length_frames": length,
                    "position_start_frames": position,
                    "position_end_frames": position + length,
                })
                position += length
            elif child.tag == "entry":
                producer_id = child.get("producer", "")
                in_f = parse_mlt_time(child.get("in", "0"), fps)
                out_f = parse_mlt_time(child.get("out", "0"), fps)
                length = out_f - in_f + 1
                entries.append({
                    "kind": "entry", "producer": producer_id,
                    "in_frame": in_f, "out_frame": out_f,
                    "duration_frames": length,
                    "position_start_frames": position,
                    "position_end_frames": position + length,
                    "resource": producers.get(producer_id, {}).get("resource", ""),
                })
                position += length
        playlists.append({
            "id": playlist.get("id", ""),
            "entries": entries,
        })

    tractor = root.find("tractor")
    tracks = []
    if tractor is not None:
        tracks = [t.get("producer", "") for t in tractor.findall("track")]

    return {
        "root_attributes": dict(root.attrib),
        "profile": dict(profile.attrib),
        "frame_rate": fps,
        "producers": producers,
        "doc_properties": doc_properties,
        "playlists": playlists,
        "tractor_tracks": tracks,
    }


def placements(parsed: dict) -> list:
    """Timeline clip placements with absolute track positions.

    Only playlists that the main tractor lists as tracks are the timeline;
    Kdenlive's project bin is itself a playlist (its entries are bin
    references, not placements) and is excluded here.
    """
    track_ids = set(parsed["tractor_tracks"])
    out = []
    for playlist in parsed["playlists"]:
        if playlist["id"] not in track_ids:
            continue
        for entry in playlist["entries"]:
            if entry["kind"] != "entry":
                continue
            out.append({
                "producer": entry["producer"],
                "resource": entry["resource"],
                "playlist": playlist["id"],
                "in_frame": entry["in_frame"],
                "out_frame": entry["out_frame"],
                "start_frame": entry["position_start_frames"],
                "end_frame": entry["position_end_frames"],
            })
    return out


def _basename(resource: str) -> str:
    return PurePath(resource.replace("\\", "/")).name.lower()


def project_summary(parsed: dict, expected_resources: dict) -> dict:
    """Placement summary for scoring; also the representable failure state.

    `expected_resources` maps a role name ("recording", "reference") to the
    expected media file basename. Failure is represented as
    MISSING_EXPECTED_CLIP (file absent from the project) or
    NOT_PLACED_ON_TIMELINE (imported but never put on a track). No GT
    comparison happens here.
    """
    placed = placements(parsed)
    bin_names = {_basename(p["resource"])
                 for p in parsed["producers"].values()}
    bin_names |= {_basename(e["resource"])
                  for pl in parsed["playlists"]
                  if pl["id"] not in set(parsed["tractor_tracks"])
                  for e in pl["entries"] if e["kind"] == "entry"}
    roles = {}
    missing = []
    for role, expected in expected_resources.items():
        want = _basename(expected)
        hits = [p for p in placed if _basename(p["resource"]) == want]
        if not hits:
            missing.append({
                "role": role,
                "expected": want,
                "state": "NOT_PLACED_ON_TIMELINE" if want in bin_names
                else "MISSING_EXPECTED_CLIP",
            })
            continue
        hit = sorted(hits, key=lambda p: p["start_frame"])[0]
        roles[role] = hit
    summary = {
        "profile_frame_rate": parsed["frame_rate"],
        "root_attributes": parsed["root_attributes"],
        "doc_properties": parsed["doc_properties"],
        "placements": placed,
        "roles": roles,
        "failures": missing,
        "state": "OK" if not missing else "INCOMPLETE",
        "clip_offset_frames": (
            roles["recording"]["start_frame"] - roles["reference"]["start_frame"]
            if "recording" in roles and "reference" in roles else None),
    }
    return summary


def summarize_file(path, expected_resources: dict) -> dict:
    with open(path, "rb") as f:
        return project_summary(parse_project(f.read()), expected_resources)
