"""Deterministic synthetic "music-like" payload generators for the applied
system benchmark MACHINERY SHAKEDOWN.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Purpose: provide two source-disjoint, byte-reproducible audio payloads so the
marker/trim/scoring machinery can be exercised without legal, provenance, or
reproducibility problems. These are NOT the final-study songs, NOT a dataset,
and carry no scientific meaning. The generators exist because every shakedown
hash (payload, capture, trimmed input) must be reproducible from code alone.

The two songs are deliberately compositionally distant (key, tempo, chord
vocabulary, timbre, drum pattern, RNG seed) so the wrong-reference case is a
genuine mismatch for tonal evidence families. No parameter here was tuned on
any evaluation data; these are machinery fixtures.
"""
from __future__ import annotations

import numpy as np

FS = 48_000

SONG_A_SEED = 20260913
SONG_B_SEED = 20260914

# Semitone ratio and a couple of helper pitches (MIDI numbers).
_SEMITONE = 2.0 ** (1.0 / 12.0)


def _midi_to_hz(m):
    return 440.0 * _SEMITONE ** (m - 69)


def _note(freq, dur_s, harmonics, rng, level):
    """One plucked/struck tone: harmonic stack with exponential decay and a
    touch of inharmonic detune. Deterministic given rng."""
    n = int(round(dur_s * FS))
    t = np.arange(n) / FS
    out = np.zeros(n)
    for k, amp in enumerate(harmonics, start=1):
        detune = 1.0 + rng.normal(0.0, 0.0004)
        out += amp * np.sin(2 * np.pi * freq * k * detune * t)
    env = np.exp(-t / (dur_s * 0.35))
    attack = np.minimum(t / 0.008, 1.0)
    return level * out * env * attack


def _kick(dur_s=0.28):
    t = np.arange(int(round(dur_s * FS))) / FS
    f = 105.0 * np.exp(-t / 0.045) + 42.0
    phase = 2 * np.pi * np.cumsum(f) / FS
    return 0.9 * np.sin(phase) * np.exp(-t / 0.09)


def _hat(rng, dur_s=0.07):
    n = int(round(dur_s * FS))
    return rng.normal(0.0, 1.0, n) * np.exp(-np.arange(n) / (FS * 0.018))


def _render_song(seed, bpm, chord_roots, chord_type, melody_scale, lead_timbre,
                 duration_s):
    """Render one deterministic music-like payload.

    chord_roots: MIDI root notes, one per 2-second chord slot, looped.
    chord_type: "minor" or "major" triad above each root.
    melody_scale: MIDI pitch classes allowed for the seeded melody walk.
    lead_timbre: harmonic amplitude list for melody notes.
    """
    rng = np.random.default_rng(seed)
    total_n = int(round(duration_s * FS))
    out = np.zeros(total_n)
    beat = 60.0 / bpm
    chord_len = 2.0  # seconds per chord slot
    n_slots = int(np.ceil(duration_s / chord_len))

    third = 3 if chord_type == "minor" else 4
    for slot in range(n_slots):
        root = chord_roots[slot % len(chord_roots)]
        t0 = int(round(slot * chord_len * FS))
        # Chord pad: root/triad, sustained, soft.
        for iv in (0, third, 7):
            note = _note(_midi_to_hz(root + iv), chord_len * 0.98,
                         (1.0, 0.45, 0.22, 0.12), rng, 0.10)
            end = min(t0 + len(note), total_n)
            out[t0:end] += note[: end - t0]
        # Bass: root one octave down, re-struck every bar (2 beats).
        for b in range(int(round(chord_len / beat)) // 2 + 1):
            bt0 = t0 + int(round(2 * b * beat * FS))
            note = _note(_midi_to_hz(root - 12), beat * 1.8,
                         (1.0, 0.7, 0.35, 0.2, 0.1), rng, 0.22)
            end = min(bt0 + len(note), total_n)
            if bt0 < total_n:
                out[bt0:end] += note[: end - bt0]

    # Melody: seeded random walk over the scale, eighth notes.
    step = int(round(beat / 2 * FS))
    pitch = melody_scale[0] + 12
    pos = 0
    while pos < total_n:
        dur_notes = rng.choice([1, 1, 1, 2], p=[0.5, 0.25, 0.15, 0.1])
        dur_n = step * dur_notes
        if rng.random() < 0.12:
            pitch = melody_scale[int(rng.integers(len(melody_scale)))] + 12
        else:
            pitch += int(rng.choice([-2, -1, 0, 1, 2]))
        if pitch not in [p + 12 for p in melody_scale] and pitch not in melody_scale:
            pitch = melody_scale[int(rng.integers(len(melody_scale)))] + 12
        note = _note(_midi_to_hz(pitch), dur_n / FS * 0.95, lead_timbre,
                     rng, 0.16)
        end = min(pos + len(note), total_n)
        out[pos:end] += note[: end - pos]
        pos += dur_n

    # Percussion: kick on every beat, hats on the off-beat eighths.
    beat_n = int(round(beat * FS))
    eighth_n = int(round(beat / 2 * FS))
    k = _kick()
    for b0 in range(0, total_n - len(k), beat_n):
        out[b0:b0 + len(k)] += 0.85 * k
    for e0 in range(eighth_n, total_n, 2 * eighth_n):
        h = _hat(rng)
        end = min(e0 + len(h), total_n)
        out[e0:end] += 0.08 * h[: end - e0]

    # Quiet noise floor so "digital silence" never appears inside the song.
    out += rng.normal(0.0, 3e-4, total_n)

    peak = float(np.max(np.abs(out)))
    if peak <= 0:
        raise RuntimeError("degenerate synthetic payload")
    return out * (0.8 / peak)


def render_song_a(duration_s=62.0):
    """Song A: A minor, 120 BPM, minor triads, sine-dominant lead."""
    # Am | F | C | G  (roots A2 F2 C3 G2)
    return _render_song(
        seed=SONG_A_SEED, bpm=120.0,
        chord_roots=[45, 41, 48, 43], chord_type="minor",
        melody_scale=[57, 60, 62, 64, 67, 69, 72],  # A minor pentatonic-ish
        lead_timbre=(1.0, 0.3, 0.15, 0.08),
        duration_s=duration_s,
    )


def render_song_b(duration_s=62.0):
    """Song B: D minor, 96 BPM, major/minor mix, brighter saw-like lead."""
    # Dm | Bb | F | A  (roots D2 Bb1 F2 A1)
    return _render_song(
        seed=SONG_B_SEED, bpm=96.0,
        chord_roots=[38, 34, 41, 33], chord_type="minor",
        melody_scale=[50, 53, 55, 57, 60, 62, 65],  # D minor pentatonic-ish
        lead_timbre=(1.0, 0.6, 0.45, 0.3, 0.2, 0.12),
        duration_s=duration_s,
    )


SONG_GENERATORS = {
    "shakedown_song_a": render_song_a,
    "shakedown_song_b": render_song_b,
}
