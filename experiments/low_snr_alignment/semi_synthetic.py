"""Semi-synthetic real-noise corpus builder (RA-1.2C).

Bridges the gap between simplistic Gaussian synthetic audio and the single
real low-SNR recording: a REAL handcam/arcade recording provides the
background (taps, ambience, adjacent machines, speech, phone-mic coloration,
compression artifacts) and a clean target track from a DIFFERENT project is
inserted at an EXACT known offset under a documented, deterministic acoustic
degradation.

The purpose is NOT to simulate an arcade loudspeaker. It is to expose the
engine to structured real-world interference with exact ground truth, so
thresholds can be calibrated and then verified on a disjoint holdout.

Split discipline (RA-1.2C §5): songs and recordings are partitioned into
CALIBRATION and HOLDOUT at PROJECT level (a project = one song + all its
recordings). A source used to tune thresholds never reappears in the
holdout under another gain/offset variant. See semi_synthetic_plan.json
(path-free) and local_sources.json (gitignored, absolute paths).

Media is READ-ONLY: sources are only ever decoded, never modified. Generated
audio goes to the gitignored repository-root results/ scratch tree and is
never committed.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import wave

import numpy as np
from scipy import signal

SR = 22050

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))

# Evaluation tolerance: ~6 analysis hops (512 / 22050 = 23.2 ms per hop).
# Matches the engine cluster tolerance and the synthetic suite tolerance.
GT_TOLERANCE_S = 0.15


# ---------------------------------------------------------------------------
# deterministic degradation conditions
# ---------------------------------------------------------------------------

def band_limit(y, sr=SR, low_hz=80.0, high_hz=5500.0):
    """4th-order Butterworth band-pass, zero-phase: phone-microphone-like
    band limitation of the inserted track."""
    sos = signal.butter(4, [low_hz, high_hz], btype="band", fs=sr,
                        output="sos")
    return signal.sosfiltfilt(sos, y).astype(np.float32)


def room_reverb(y, sr=SR, seed=0, tail_s=0.25, tau_s=0.08, wet=0.25):
    """Mild room-like reverberation: exponentially decaying noise impulse
    response (energy-normalized), mixed wet at a fixed ratio. Deterministic
    given `seed`."""
    rng = np.random.default_rng(seed)
    n = int(tail_s * sr)
    t = np.arange(n) / sr
    ir = rng.standard_normal(n) * np.exp(-t / tau_s)
    ir[0] += 4.0  # clear dry path
    ir = ir / np.linalg.norm(ir)
    conv = signal.fftconvolve(y, ir)[: len(y)]
    out = y + wet * conv
    return out.astype(np.float32)


def soft_compress(y, knee=2.2):
    """Mild static soft-knee compression: unit-slope tanh curve applied at a
    fixed internal level, then re-normalized to the input RMS. Peak-heavy
    material is squashed; quiet passages are untouched. Deterministic."""
    rms = float(np.sqrt(np.mean(y ** 2))) + 1e-12
    x = y / rms
    out = np.tanh(knee * x) / knee
    return (out / (float(np.sqrt(np.mean(out ** 2))) + 1e-12) * rms).astype(
        np.float32)


# Documented condition packages (applied to the inserted track, in order).
CONDITIONS = {
    "clean": [],
    "bandlimit": ["bandlimit"],
    "bandlimit_reverb": ["bandlimit", "reverb"],
    "brl_comp": ["bandlimit", "reverb", "compress"],
}


def apply_condition(y, condition, seed):
    for step in CONDITIONS[condition]:
        if step == "bandlimit":
            y = band_limit(y)
        elif step == "reverb":
            y = room_reverb(y, seed=seed)
        elif step == "compress":
            y = soft_compress(y)
        else:  # pragma: no cover - plan validation should prevent this
            raise ValueError(f"unknown degradation step: {step}")
    return y


# ---------------------------------------------------------------------------
# case construction
# ---------------------------------------------------------------------------


def _rms(y):
    return float(np.sqrt(np.mean(y ** 2))) + 1e-12


def insert_track(background, degraded, offset_s, gain_db):
    """Place the degraded target track into the background at the exact
    production-convention offset. offset > 0 delays the track; offset < 0
    trims its head. Track gain is set so the degraded track's RMS sits
    `gain_db` dB below the background RMS (before clipping protection)."""
    n = len(background)
    gain = _rms(background) / _rms(degraded) * 10.0 ** (gain_db / 20.0)
    sig = degraded * gain
    out = background.copy()
    off_i = int(round(offset_s * SR))
    if off_i >= 0:
        end = min(n, off_i + len(sig))
        if off_i < n:
            out[off_i:end] += sig[: end - off_i]
    else:
        start_src = min(-off_i, len(sig))
        take = min(n, len(sig) - start_src)
        out[:take] += sig[start_src:start_src + take]
    peak = float(np.max(np.abs(out)))
    if peak > 0.99:  # deterministic clipping protection
        out = out * (0.99 / peak)
    return out.astype(np.float32)


def build_positive(background, track, offset_s, gain_db, condition, seed):
    """background + degraded(track) at exact offset -> low-SNR positive.

    Returns (mix, exact_offset_s). The offset is exact by construction; it
    is never derived from any algorithm prediction."""
    degraded = apply_condition(np.asarray(track, dtype=np.float32),
                               condition, seed)
    return insert_track(np.asarray(background, dtype=np.float32), degraded,
                        offset_s, gain_db), float(offset_s)


def build_tiled(background, track, tile_s, gain_db, condition, seed):
    """Recording contains the SAME tile of the track repeated end-to-end —
    evidence is genuinely non-unique, every tile boundary is an equally
    valid placement. Expected engine outcome: abstain (CASE D semantics);
    accepting exactly one arbitrary tile start would be a policy gap."""
    n = len(background)
    degraded = apply_condition(np.asarray(track[: int(tile_s * SR)],
                                          dtype=np.float32),
                               condition, seed)
    gain = _rms(background) / _rms(degraded) * 10.0 ** (gain_db / 20.0)
    tiled = np.tile(degraded, int(np.ceil(n / max(1, len(degraded)))))[:n]
    out = background + tiled * gain
    peak = float(np.max(np.abs(out)))
    if peak > 0.99:
        out = out * (0.99 / peak)
    return out.astype(np.float32), float(tile_s)


def usable_overlap_s(offset_s, video_dur_s, music_dur_s):
    if offset_s >= 0:
        return max(0.0, min(offset_s + music_dur_s, video_dur_s) - offset_s)
    return max(0.0, min(music_dur_s + offset_s, video_dur_s))


# ---------------------------------------------------------------------------
# outcome classification (task §8 semantics)
# ---------------------------------------------------------------------------

CORRECT_ACCEPT = "CORRECT_ACCEPT"
SAFE_ABSTAIN = "SAFE_ABSTAIN"
WRONG_ACCEPT = "WRONG_ACCEPT"


def classify_positive(decision, gt_offset_s, tolerance_s=GT_TOLERANCE_S):
    """For exact-GT positives: a correct accept is within tolerance; any
    accept outside tolerance is WRONG_ACCEPT (the critical failure);
    abstention is a recoverable miss."""
    if decision.status == "accepted":
        if decision.offset is not None and \
                abs(decision.offset - gt_offset_s) <= tolerance_s:
            return CORRECT_ACCEPT
        return WRONG_ACCEPT
    return SAFE_ABSTAIN


def classify_negative(decision, tile_starts_s=None, tolerance_s=GT_TOLERANCE_S):
    """For negatives: any ACCEPT is WRONG_ACCEPT. For tiled-ambiguity cases,
    an accept that lands on SOME tile start is recorded as TILE_CONSISTENT_ACCEPT
    (semantically ambiguous content, not a wrong offset — but still a policy
    gap the CASE D ambiguity check is supposed to prevent)."""
    if decision.status != "accepted":
        return SAFE_ABSTAIN
    if tile_starts_s:
        if any(abs(decision.offset - t) <= tolerance_s
               for t in tile_starts_s):
            return "TILE_CONSISTENT_ACCEPT"
    return WRONG_ACCEPT


# ---------------------------------------------------------------------------
# deterministic media IO (scratch only; nothing here is committed)
# ---------------------------------------------------------------------------

SCRATCH_DIR = os.path.join(_REPO_ROOT, "results", "semi_synthetic_cache")


def _scratch_path(name):
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    return os.path.join(SCRATCH_DIR, name)


def load_audio_cached(path, source_id, ffmpeg_bin):
    """Decode a source media file to mono float32 @ SR, cached by content
    hash in the gitignored scratch tree. Sources are opened READ-ONLY."""
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read(1 << 20)).hexdigest()[:16]
    cache = _scratch_path(f"{source_id}_{digest}.npy")
    if os.path.exists(cache):
        return np.load(cache)
    tmp_wav = _scratch_path(f"tmp_{source_id}_{digest}.wav")
    cmd = [ffmpeg_bin, "-y", "-i", path, "-vn", "-acodec", "pcm_s16le",
           "-ar", str(SR), "-ac", "1", tmp_wav]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {source_id}: "
                           f"{proc.stderr[-400:]}")
    with wave.open(tmp_wav, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    os.remove(tmp_wav)
    y = (pcm.astype(np.float32) / 32768.0)
    np.save(cache, y)
    return y


def write_wav(path, y, sr=SR):
    pcm = (np.clip(y, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------------------
# split / leakage audit (pure plan logic; no media, no file IO)
# ---------------------------------------------------------------------------


def project_of_recording(rid, projects):
    for pid, spec in projects.items():
        if rid in spec["recordings"]:
            return pid
    return None


def project_of_track(tid, projects):
    for pid, spec in projects.items():
        if spec["track"] == tid:
            return pid
    return None


# Conservative static minimum durations (s) for the overlap guard; the
# runner re-checks with real durations before mixing.
_STATIC_MIN_VIDEO_S = 145.0
_STATIC_MIN_TRACK_S = 119.0


def audit_split(plan, min_overlap_s=45.0):
    """Split integrity: every project in exactly one side; every case's
    sources belong to its declared split; no positive target is the
    background's own song; overlaps clear the guard. Returns violations."""
    split = plan["split"]
    projects = split["projects"]
    problems = []
    cal = set(split["calibration_projects"])
    ho = set(split["holdout_projects"])
    if cal & ho:
        problems.append(f"projects in both splits: {sorted(cal & ho)}")
    if set(projects) != cal | ho:
        problems.append("projects table does not match the split lists")
    seen_recordings = set()
    for pid, spec in projects.items():
        for rid in spec["recordings"]:
            if rid in seen_recordings:
                problems.append(f"recording {rid} in two projects")
            seen_recordings.add(rid)
    for case in plan["positives"]:
        bg_p = project_of_recording(case["background"], projects)
        tg_p = project_of_track(case["target"], projects)
        if bg_p is None or tg_p is None:
            problems.append(f"{case['case_id']}: unknown source id")
            continue
        pure = (bg_p in cal and tg_p in cal) if case["split"] == "calibration" \
            else (bg_p in ho and tg_p in ho)
        if not pure:
            problems.append(f"{case['case_id']}: not split-pure "
                            f"{case['split']}")
        if bg_p == tg_p:
            problems.append(
                f"{case['case_id']}: target is the background's own song")
        ov = usable_overlap_s(case["offset_s"], _STATIC_MIN_VIDEO_S,
                              _STATIC_MIN_TRACK_S)
        if ov < min_overlap_s:
            problems.append(
                f"{case['case_id']}: conservative overlap {ov:.1f}s "
                f"below {min_overlap_s}s guard")
    for case in plan["ambiguity_tiled"]:
        bg_p = project_of_recording(case["background"], projects)
        tg_p = project_of_track(case["target"], projects)
        pure = (bg_p in cal and tg_p in cal) if case["split"] == "calibration" \
            else (bg_p in ho and tg_p in ho)
        if not pure or bg_p == tg_p:
            problems.append(f"{case['case_id']}: split/identity violation")
    for entry in plan.get("hard_negatives_real", {}).get("selected", []):
        rec_p = project_of_recording(entry["recording"], projects)
        trk_p = project_of_track(entry["track"], projects)
        pure = (rec_p in cal and trk_p in cal) if entry["split"] == "calibration" \
            else (rec_p in ho and trk_p in ho)
        if not pure or rec_p == trk_p:
            problems.append(f"{entry['case_id']}: split/identity violation")
    return problems
