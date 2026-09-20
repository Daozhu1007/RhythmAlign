"""COMPARATOR-INTEGRITY-1: GCC-PHAT FFT-index -> lag unwrap validation.

Synthetic-first audit tests (no final data, no GT). The intended linear
cross-correlation lag convention is derived mathematically and every fixture
is checked against an INDEPENDENT direct linear cross-correlation
(scipy.signal.correlate, direct method — no FFT unwrap involved).

Convention (v1 docstring, v2 docstring, production engine, frozen GT):
lag m means y_rec[n] ~= y_ref[n - m] — the reference begins m samples into
the capture. c[m] = sum_n y_rec[n] y_ref[n-m] has nonzero support
m in [-(Ly-1), Lx-1].

v1 unwrap (preserved verbatim in gcc_phat_runner): k if k < ceil(N/2) else
k - N. Correct only when every negative-lag index N-Ly+1..N-1 lies at or
above ceil(N/2) AND every positive-lag index lies below it — true for equal
lengths, false for unequal lengths whenever next_fast_len(Lx+Ly) is close to
Lx+Ly. v2 (gcc_phat_argmax_v2_lagfix) flips at the geometric boundary
N - Ly + 1 instead.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import fft as scipy_fft
from scipy import signal

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.applied_system.runners import gcc_phat_runner, ncc_runner  # noqa: E402
from experiments.applied_system.runners import gcc_phat_runner_v2_lagfix as v2  # noqa: E402


# --------------------------------------------------------------------------
# Independent reference: direct linear cross-correlation with explicit lag
# axis. Anchor check pins the axis direction by hand.
# --------------------------------------------------------------------------

def direct_xcorr_argmax_lag(y_rec, y_ref):
    """Expected lag from DIRECT linear cross-correlation (no FFT unwrap).

    correlate(rec, ref, 'full')[k] = c[k - (Ly-1)] with the convention
    c[m] = sum_n y_rec[n] y_ref[n-m]; hand-checked with Lx=3, Ly=2, query
    impulse at 1 -> full index 2 -> lag 1.
    """
    lags = np.arange(-(len(y_ref) - 1), len(y_rec))
    c = signal.correlate(y_rec, y_ref, mode="full", method="direct")
    return int(lags[int(np.argmax(c))])


def test_direct_xcorr_lag_axis_anchor():
    y_rec = np.array([0.0, 1.0, 0.0])   # query impulse at q=1
    y_ref = np.array([1.0, 0.0])        # reference impulse at p=0
    assert direct_xcorr_argmax_lag(y_rec, y_ref) == 1 - 0  # m = q - p


# --------------------------------------------------------------------------
# Fixture builders. Both produce signal pairs whose PHAT curve is an EXACT
# delta at the true lag (all nonzero reference content appears in the query
# delayed by exactly m -> cross-spectrum has pure linear phase), so the
# argmax index is exact and any deviation is a MAPPING error, not an
# estimator error.
# --------------------------------------------------------------------------

def impulse_pair(lx, ly, m):
    """Query impulse at q, reference impulse at p, q - p = m."""
    assert -(ly - 1) <= m <= lx - 1
    p = max(0, -m)
    q = p + m
    assert 0 <= p < ly and 0 <= q < lx
    y_ref = np.zeros(ly)
    y_ref[p] = 1.0
    y_rec = np.zeros(lx)
    y_rec[q] = 1.0
    return y_rec, y_ref


def exact_delay_pair(lx, ly, m, seed=20260920):
    """Deterministic broadband pair, exact delayed copy for ANY valid lag.

    m >= 0: reference content sits at [0, ell), query carries it at
    [m, m+ell) — the capture head is pre-reference material.
    m < 0: reference content sits at [t, t+ell) with t = -m, query carries it
    at [0, ell) — the capture starts t samples into the reference content.
    ell is the maximum overlap; every other sample is exactly zero."""
    rng = np.random.default_rng(seed)
    assert -(ly - 1) <= m <= lx - 1
    y_ref = np.zeros(ly)
    y_rec = np.zeros(lx)
    if m >= 0:
        ell = min(ly, lx - m)
        y_ref[:ell] = rng.normal(0.0, 1.0, ell)
        y_rec[m:m + ell] = y_ref[:ell]
    else:
        t = -m
        ell = min(ly - t, lx)
        y_ref[t:t + ell] = rng.normal(0.0, 1.0, ell)
        y_rec[:ell] = y_ref[t:t + ell]
    return y_rec, y_ref


def v1_expected_report(lx, ly, m):
    """What the preserved v1 unwrap reports for true lag m (its documented
    defective behavior for unequal lengths)."""
    n = scipy_fft.next_fast_len(lx + ly)
    j = m % n
    return j if j < (n + 1) // 2 else j - n


# --------------------------------------------------------------------------
# 1. Full unequal-length linear lag support (impulses sweep every region,
#    both boundaries, and both length orderings).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("lx,ly", [(1000, 4000), (4000, 1000), (2000, 2000)])
def test_full_lag_support_impulses(lx, ly):
    lags = sorted({0, 1, -1, lx - 1, -(ly - 1),
                   lx // 3, -(ly // 3), lx - 2, -(ly - 2)})
    for m in lags:
        y_rec, y_ref = impulse_pair(lx, ly, m)
        assert direct_xcorr_argmax_lag(y_rec, y_ref) == m
        off2, nat2 = v2.gcc_phat_offset(y_rec, y_ref)
        assert off2 == m, (lx, ly, m)
        assert nat2["lag_samples"] == m
        if lx == ly:
            off1, _ = gcc_phat_runner.gcc_phat_offset(y_rec, y_ref)
            assert off1 == m  # v1 must stay correct for equal lengths


# --------------------------------------------------------------------------
# 2. The unequal-length mapping bug, demonstrated and corrected.
#    next_fast_len(6000+20000) = 27000, midpoint 13500. Query-shorter:
#    m = -14000 sits at index 13000 < 13500 -> v1 reports +13000 (exactly N
#    samples too large). Query-longer: m = +14000 sits at index 14000 >=
#    13500 -> v1 reports -13000 (exactly N samples too small). v2 returns
#    the true lag in both geometries.
# --------------------------------------------------------------------------

CANONICAL_SHORT = (6000, 20000, -14000)   # query shorter than reference
CANONICAL_LONG = (20000, 6000, 14000)     # query longer than reference


@pytest.mark.parametrize("lx,ly,m", [CANONICAL_SHORT, CANONICAL_LONG])
def test_v1_unequal_length_misread_is_real_and_preserved(lx, ly, m):
    """v1's documented defective behavior, preserved as evidence: the same
    PHAT curve v1 computed is unwrapped through the length-independent
    midpoint, landing exactly one FFT length away from the true lag."""
    y_rec, y_ref = exact_delay_pair(lx, ly, m)
    n = scipy_fft.next_fast_len(lx + ly)
    off1, nat1 = gcc_phat_runner.gcc_phat_offset(y_rec, y_ref)
    assert direct_xcorr_argmax_lag(y_rec, y_ref) == m
    assert nat1["lag_samples"] == off1
    assert off1 == v1_expected_report(lx, ly, m)
    assert off1 != m and abs(off1 - m) == n


@pytest.mark.parametrize("lx,ly,m", [CANONICAL_SHORT, CANONICAL_LONG])
def test_v2_corrects_unequal_length_mapping(lx, ly, m):
    y_rec, y_ref = exact_delay_pair(lx, ly, m)
    off2, nat2 = v2.gcc_phat_offset(y_rec, y_ref)
    n = scipy_fft.next_fast_len(lx + ly)
    assert off2 == m
    assert nat2["argmax_index"] == m % n
    assert nat2["fft_length"] == n
    assert nat2["lagfix_wrap_boundary_index"] == n - ly + 1


def test_v2_benchmark_like_geometry_deep_negative_lag():
    """Small-scale replica of the final-benchmark geometry (short query,
    long reference, argmax deep in the negative-lag region). With this
    scipy's next_fast_len(3450+7515) = 10976, the true lag -6000 sits at
    index 4976, below the 5488 midpoint, so v1 reports +4976 (the misread)
    while v2 reports the true -6000."""
    lx, ly, m = 3450, 7515, -6000
    n = scipy_fft.next_fast_len(lx + ly)
    assert n == 10976 and m % n == 4976 < (n + 1) // 2
    y_rec, y_ref = impulse_pair(lx, ly, m)
    off1, _ = gcc_phat_runner.gcc_phat_offset(y_rec, y_ref)
    off2, _ = v2.gcc_phat_offset(y_rec, y_ref)
    assert off1 == 4976 and off2 == -6000
    assert direct_xcorr_argmax_lag(y_rec, y_ref) == -6000


# --------------------------------------------------------------------------
# 3. Positive and negative known offsets, boundary lags, exact insertion
#    positions, deterministic broadband fixtures (beyond the impulse sweep).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("lx,ly,m", [
    (6000, 20000, 0),        # exact alignment
    (6000, 20000, 2500),     # positive: capture head precedes reference
    (6000, 20000, 5999),     # positive boundary: single-sample overlap
    (20000, 6000, 13999),    # large positive, fully-contained copy
    (20000, 6000, 1),
])
def test_positive_offsets_broadband(lx, ly, m):
    y_rec, y_ref = exact_delay_pair(lx, ly, m)
    assert direct_xcorr_argmax_lag(y_rec, y_ref) == m
    off2, nat2 = v2.gcc_phat_offset(y_rec, y_ref)
    assert off2 == m and nat2["lag_samples"] == m


@pytest.mark.parametrize("lx,ly,t", [
    (6000, 20000, 1),
    (6000, 20000, 14000),    # deep negative: v1 misread region
    (6000, 20000, 19999),    # negative boundary: single-sample overlap
    (20000, 6000, 5999),     # negative boundary on the long-query side
])
def test_negative_offsets_broadband(lx, ly, t):
    y_rec, y_ref = exact_delay_pair(lx, ly, -t)
    assert direct_xcorr_argmax_lag(y_rec, y_ref) == -t
    off2, _ = v2.gcc_phat_offset(y_rec, y_ref)
    assert off2 == -t


def test_shallow_negative_offsets_agree_with_v1():
    """Negative offsets with |m| above-the-midpoint-safe were already correct
    in v1 (the existing sign test's regime); v2 must agree there too."""
    lx, ly = 6000, 20000           # next_fast_len = 27000; v1 misreads only
    for t in (1, 500, 5000):       # m <= ceil(N/2)-1-N = -13500
        y_rec, y_ref = exact_delay_pair(lx, ly, -t)
        off1, _ = gcc_phat_runner.gcc_phat_offset(y_rec, y_ref)
        off2, _ = v2.gcc_phat_offset(y_rec, y_ref)
        assert off1 == off2 == -t


def test_v1_and_v2_agree_wherever_v1_was_correct():
    """For every swept lag of an unequal pair, v2 equals the true lag; v1
    equals it too EXACTLY WHEN the lag is outside the misread region."""
    lx, ly = 3000, 5000            # next_fast_len = 8000, midpoint 4000
    n = scipy_fft.next_fast_len(lx + ly)
    for m in range(-(ly - 1), lx, 37):
        y_rec, y_ref = exact_delay_pair(lx, ly, m, seed=10_000 + m)
        off1, _ = gcc_phat_runner.gcc_phat_offset(y_rec, y_ref)
        off2, _ = v2.gcc_phat_offset(y_rec, y_ref)
        assert off2 == m
        if off1 != m:
            assert off1 == v1_expected_report(lx, ly, m)
            assert abs(off1 - m) == n


def test_noisy_capture_broadband_fixture():
    """Noise-like capture: delayed copy plus deterministic noise keeps the
    PHAT argmax at the true lag under the corrected mapping."""
    rng = np.random.default_rng(7)
    lx, ly, m = 8000, 24000, -20000   # next_fast_len=32000, misread region
    y_rec, y_ref = exact_delay_pair(lx, ly, m)
    y_rec = y_rec + rng.normal(0, 1e-3, lx)
    off2, _ = v2.gcc_phat_offset(y_rec, y_ref)
    assert off2 == m
    off1, _ = gcc_phat_runner.gcc_phat_offset(y_rec, y_ref)
    assert off1 == m + 32000  # v1 defect still visible on this geometry


# --------------------------------------------------------------------------
# 4. Sign convention and semantics preservation.
# --------------------------------------------------------------------------

def test_sign_convention_matches_documentation():
    """+m: reference begins m samples into the capture (delayed reference);
    -t: capture starts t samples into the reference (trimmed reference head).
    Same convention as the production engine and the frozen GT."""
    y_rec, y_ref = exact_delay_pair(620, 500, 120, seed=5)
    off2, _ = v2.gcc_phat_offset(y_rec, y_ref)
    assert off2 == 120
    y_rec, y_ref = exact_delay_pair(380, 500, -120, seed=6)
    off2, _ = v2.gcc_phat_offset(y_rec, y_ref)
    assert off2 == -120


def test_v2_semantics_and_curve_identical_to_v1():
    """v2 changes ONLY the unwrap: same curve, same always-output contract,
    same peak value, same argmax index."""
    y_rec, y_ref = exact_delay_pair(6000, 20000, -14000)
    curve = gcc_phat_runner.gcc_phat_curve(y_rec, y_ref)
    j = int(np.argmax(curve))
    off1, nat1 = gcc_phat_runner.gcc_phat_offset(y_rec, y_ref)
    off2, nat2 = v2.gcc_phat_offset(y_rec, y_ref)
    assert nat2["argmax_index"] == j == (off2 % len(curve))
    assert nat2["gcc_peak_value"] == nat1["gcc_peak_value"]
    assert nat2["gcc_peak_value"] == float(curve[j])
    assert off2 == nat2["argmax_index"] - len(curve)
    assert off1 == nat2["argmax_index"]
    assert v2.SYSTEM_ID == "gcc_phat_argmax_v2_lagfix"
    assert gcc_phat_runner.SYSTEM_ID == "gcc_phat_argmax_v1"


def test_v2_determinism():
    y_rec, y_ref = exact_delay_pair(6000, 20000, -14000)
    a = v2.gcc_phat_offset(y_rec, y_ref)
    b = v2.gcc_phat_offset(y_rec, y_ref)
    assert a[0] == b[0]
    assert {k: v for k, v in a[1].items() if "runtime" not in k} == \
        {k: v for k, v in b[1].items() if "runtime" not in k}


def test_run_case_file_contract(tmp_path):
    """File-based v2 entry keeps the v1 record contract (ALWAYS_OUTPUT, no
    invented threshold, numeric offset in the frozen convention)."""
    import soundfile as sf
    fs = 48_000
    y_rec, y_ref = exact_delay_pair(int(2.0 * fs), int(6.0 * fs),
                                    -int(1.5 * fs), seed=11)
    in_path = tmp_path / "in.wav"
    ref_path = tmp_path / "ref.wav"
    sf.write(str(in_path), y_rec, fs, subtype="PCM_16")
    sf.write(str(ref_path), y_ref, fs, subtype="PCM_16")
    record = v2.run_case({"case_id": "lagfix_file_test"}, in_path,
                         ref_path, fs, _load_audio)
    assert record.decision == "ACCEPT"
    assert record.output_semantics == "ALWAYS_OUTPUT"
    assert record.notes["no_threshold_invented"] is True
    assert record.predicted_offset_s == pytest.approx(-1.5, abs=1e-4)
    assert record.system == "gcc_phat_argmax_v2_lagfix"


def test_ncc_mapping_unaffected_by_gcc_lagfix():
    """The NCC runner maps lags via an explicit full-mode lag axis (no FFT
    unwrap) and must be untouched by the GCC correction.

    Fixture note: with per-lag overlap-energy normalization, a ONE-sample
    overlap of nonzero samples scores exactly +-1.0 and can tie or beat the
    true full-overlap peak (argmax then breaks the tie toward the extreme
    edge). Zeroing the two samples that form the extreme single-sample
    overlaps floors them and exposes the true lag deterministically. See
    NCC_OVERLAP_CONTRACT_AUDIT.md for the final-data consequence."""
    y_rec, y_ref = exact_delay_pair(6000, 20000, -14000)
    y_rec[0] = 0.0            # floors the lag -(Ly-1) single-sample overlap
    # y_ref[0] is already zero (content starts at t=14000), flooring the
    # lag +(Lx-1) single-sample overlap.
    ncc, lags = ncc_runner.ncc_curve(y_rec, y_ref)
    off, nat = ncc_runner.ncc_offset(y_rec, y_ref)
    k = int(np.argmax(ncc))
    assert off == nat["lag_samples"] == int(lags[k]) == -14000
    assert lags[0] == -(len(y_ref) - 1) and lags[-1] == len(y_rec) - 1


def _load_audio(path, fs):
    import soundfile as sf
    y, sr = sf.read(str(path), dtype="float64", always_2d=False)
    assert sr == fs
    return np.ascontiguousarray(y)
