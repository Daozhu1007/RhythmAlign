"""RA-1.2D1 shared experiment infrastructure.

Runs against UNMODIFIED production main; writes only this directory and the
gitignored repository-root results/ scratch tree. Media is read-only.

Follows the decoding / feature-reuse discipline established by the Astra
study (experiments/alignment_research, branch astra/alignment-research-wip,
commit 8b78eb1): per-source features are extracted once and family curves
rebuilt from them must equal engine curves bit-for-bit (checked in
selftest_equivalence()).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import fft, signal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import alignment_engine_v2 as eng  # noqa: E402
import auto_sync  # noqa: E402
import librosa  # noqa: E402
import imageio_ffmpeg  # noqa: E402
from experiments.low_snr_alignment import semi_synthetic as ss  # noqa: E402
from experiments.low_snr_alignment import semi_synthetic_eval as sse  # noqa: E402

SR, HOP = 22050, 512
BASE = ROOT / "experiments/low_snr_alignment"
OUT = Path(__file__).resolve().parent / "results"
SCRATCH = ROOT / "results/ra12d1_cache"
SOURCES_PATH = BASE / "local_sources.json"
CORPUS_PATH = BASE / "local_corpus.json"
PLAN_PATH = BASE / "semi_synthetic_plan.json"

# Astra clean wrong-song population (results/clean_mismatch_search.json,
# branch astra/alignment-research-wip). All 22 accepted directed pairs.
DEV_COMPONENT_A = sorted({"lingduihua", "yanwulieche", "baixiwang", "drd",
                          "babieta", "fenzhen", "maodunxinli"})


def read(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / name
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(clean(payload), indent=2, ensure_ascii=False,
                              default=float) + "\n", encoding="utf-8")
    tmp.replace(target)


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.integer, np.bool_)):
        return x.item()
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    return x


def digest(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Sources:
    """Decodes media to mono float32 at SR with an on-disk cache."""

    def __init__(self):
        self.mapping = read(SOURCES_PATH)
        self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        SCRATCH.mkdir(parents=True, exist_ok=True)

    def path_of(self, kind: str, sid: str) -> Path:
        return Path(self.mapping[kind][sid])

    def audio_from_path(self, source: Path) -> np.ndarray:
        sha = digest(source)
        cache = SCRATCH / f"{sha}_{SR}.npy"
        if not cache.exists():
            cmd = [self.ffmpeg, "-v", "error", "-i", str(source), "-vn",
                   "-ac", "1", "-ar", str(SR), "-acodec", "pcm_s16le",
                   "-f", "s16le", "-"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  **auto_sync._subprocess_no_window_kwargs())
            if proc.returncode:
                raise RuntimeError(f"decode failed: {source}")
            y = np.frombuffer(proc.stdout, dtype="<i2").astype(np.float32) / 32768
            np.save(cache, y)
        return np.load(cache)

    def audio(self, kind: str, sid: str) -> np.ndarray:
        return self.audio_from_path(self.path_of(kind, sid))


def source_features(y: np.ndarray) -> dict:
    """Per-source representations reused by engine curves AND the verifier."""
    chroma = librosa.feature.chroma_cens(y=y, sr=SR, hop_length=HOP)
    chroma = np.diff(chroma, axis=1, prepend=chroma[:, :1])
    return {
        "chroma": chroma,
        "onset": librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP),
        "pcen_hpss": eng._pcen_hpss_features(y, SR, HOP),
        "pcen": eng._pcen_features(y, SR, HOP),
    }


class FeatureStore:
    """Per-source feature cache (npz under the gitignored scratch tree)."""

    def __init__(self, sources: Sources):
        self.sources = sources
        self.mem: dict[str, dict] = {}

    def get(self, kind: str, sid: str) -> dict:
        key = f"{kind}:{sid}"
        if key in self.mem:
            return self.mem[key]
        y = self.sources.audio(kind, sid)
        path = SCRATCH / f"feat_{digest(self.sources.path_of(kind, sid))[:24]}.npz"
        if not path.exists():
            np.savez_compressed(path, **source_features(y))
        self.mem[key] = dict(np.load(path))
        return self.mem[key]


def families(vf: dict, mf: dict):
    """Engine FamilyResults rebuilt from per-source features (exact reuse)."""
    chroma = eng._correlate_rows(vf["chroma"], mf["chroma"])
    oc = signal.correlate(mf["onset"] - mf["onset"].mean(),
                          vf["onset"] - vf["onset"].mean(),
                          mode="full", method="fft")
    curves = {
        "hybrid": (auto_sync._normalize_correlation(chroma)
                   + 0.2 * auto_sync._normalize_correlation(oc)),
        "onset": signal.correlate(mf["onset"], vf["onset"], mode="full",
                                  method="fft"),
        "pcen_hpss": eng._correlate_rows(vf["pcen_hpss"], mf["pcen_hpss"]),
        "pcen": eng._correlate_rows(vf["pcen"], mf["pcen"]),
    }
    n_video_frames = vf["chroma"].shape[1]
    return [eng.FamilyResult(k, eng.METHOD_FAMILY[k], c, n_video_frames,
                             float(auto_sync._correlation_z_score(c)), 0.0)
            for k, c in curves.items()]


def decide(vf: dict, mf: dict, vdur: float, mdur: float):
    """Frozen Engine v2 decision from cached features."""
    return eng.decide_from_families(families(vf, mf), SR, HOP, None,
                                    vdur, mdur)


def duration(y: np.ndarray) -> float:
    return len(y) / SR


# ---------------------------------------------------------------------------
# semi-synthetic case construction (delegates to RA-1.2C code, exact reuse)
# ---------------------------------------------------------------------------

def semi_case_mix(case: dict, store: FeatureStore = None) -> np.ndarray:
    """Build (or load cached) the audio for one semi-synthetic eval case."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    cache = SCRATCH / f"mix_{case['case_id']}.npy"
    if cache.exists():
        return np.load(cache)
    sources = store.sources if store else Sources()
    if case["kind"] == "positive":
        background = sources.audio("recordings", case["background"])
        track = sources.audio("tracks", case["target"])
        mix, _ = ss.build_positive(background, track, case["offset_s"],
                                   case["gain_db"], case["condition"],
                                   case["seed"])
    elif case["kind"] == "tiled":
        background = sources.audio("recordings", case["background"])
        track = sources.audio("tracks", case["target"])
        mix, _ = ss.build_tiled(background, track, case["tile_s"],
                                case["gain_db"], case["condition"],
                                case["seed"])
    elif case["kind"] == "hard_negative":
        background = sources.audio("recordings", case["background"])
        track = sources.audio("tracks", case["target"])
        mix = np.asarray(background, dtype=np.float32)
    else:
        raise ValueError(case["kind"])
    np.save(cache, mix)
    return mix


def iter_split_cases(split: str):
    yield from sse._iter_split_cases(read(PLAN_PATH), split)


# ---------------------------------------------------------------------------
# real corpus (local_corpus.json, gitignored)
# ---------------------------------------------------------------------------

def real_cases() -> list:
    return read(CORPUS_PATH)["cases"]


def real_case_audio(case: dict, sources: Sources):
    v = sources.audio_from_path(Path(case["video"]))
    m = sources.audio_from_path(Path(case["music"]))
    return v, m


# ---------------------------------------------------------------------------
# clean wrong-song grid
# ---------------------------------------------------------------------------

def track_ids(sources: Sources) -> list:
    return sorted(sources.mapping["tracks"])


def clean_pair_rows(dev_songs, sources: Sources):
    """All directed clean track pairs partitioned by song-identity split."""
    ids = track_ids(sources)
    dev, test = [], []
    for q in ids:
        for r in ids:
            if q == r:
                continue
            row = {"query_track": q, "reference_track": r}
            if q.removeprefix("tr_") in dev_songs and r.removeprefix("tr_") in dev_songs:
                dev.append(row)
            elif (q.removeprefix("tr_") not in dev_songs
                  and r.removeprefix("tr_") not in dev_songs):
                test.append(row)
    return dev, test


# ---------------------------------------------------------------------------
# waveform baselines: normalized cross-correlation and GCC-PHAT
# (same explicit construction as the Astra study's waveform_baselines:
#  22050 -> 7350 Hz analysis rate, per-lag Pearson, 30 s minimum overlap)
# ---------------------------------------------------------------------------

def wave_baselines(v: np.ndarray, m: np.ndarray) -> dict:
    rate = SR // 3
    v = signal.resample_poly(np.asarray(v, dtype=np.float64), 1, 3)
    m = signal.resample_poly(np.asarray(m, dtype=np.float64), 1, 3)
    v -= v.mean()
    m -= m.mean()
    nv, nm = len(v), len(m)
    lags = np.arange(-(nv - 1), nm)
    ms, me = np.maximum(0, lags), np.minimum(nm, lags + nv)
    vs, ve = np.maximum(0, -lags), np.minimum(nv, nm - lags)
    overlap = me - ms
    valid = overlap >= 30 * rate
    if not np.any(valid):
        return {"wave_ncc": {"offset": None}, "gcc_phat": {"offset": None}}
    cm, cv = np.r_[0.0, np.cumsum(m * m)], np.r_[0.0, np.cumsum(v * v)]
    sm, sv = np.r_[0.0, np.cumsum(m)], np.r_[0.0, np.cumsum(v)]
    cross = signal.correlate(m, v, mode="full", method="fft")
    n = np.maximum(overlap, 1)
    em = cm[me] - cm[ms] - (sm[me] - sm[ms]) ** 2 / n
    ev = cv[ve] - cv[vs] - (sv[ve] - sv[vs]) ** 2 / n
    numerator = cross - (sm[me] - sm[ms]) * (sv[ve] - sv[vs]) / n
    denom = np.sqrt(np.maximum(em, 0) * np.maximum(ev, 0))
    valid &= denom > 1e-12
    ncc = np.where(valid, numerator / np.maximum(denom, 1e-12), -np.inf)
    k = int(np.argmax(ncc))
    out = {"wave_ncc": {"offset": float(-lags[k] / rate),
                        "peak": float(ncc[k]), "analysis_sr": rate,
                        "min_overlap_s": 30}}
    nfft = fft.next_fast_len(nm + nv - 1)
    spec = np.fft.rfft(m, nfft) * np.conj(np.fft.rfft(v, nfft))
    cc = np.fft.irfft(spec / np.maximum(np.abs(spec), 1e-12), nfft)
    cc = np.r_[cc[-(nv - 1):], cc[:nm]]
    k = int(np.argmax(np.where(valid, cc, -np.inf)))
    out["gcc_phat"] = {"offset": float(-lags[k] / rate), "peak": float(cc[k]),
                       "analysis_sr": rate, "min_overlap_s": 30}
    return out
