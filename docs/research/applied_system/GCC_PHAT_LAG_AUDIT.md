# GCC-PHAT Lag Mapping Audit (COMPARATOR-INTEGRITY-1)

Status: **GCC_LAG_MAPPING_BUG_CONFIRMED — outcome-independent correction
executed uniformly; original v1 evidence preserved verbatim.**
Executed 2026-09-20 on `research/applied-system-paper`, starting HEAD
`0f37cbc`. Prompted by an independent hostile manuscript review; audited
synthetic-first, per the frozen protocol's post-freeze bug policy.

- Correction manifest (frozen BEFORE any final-case re-execution):
  `experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_correction_manifest.json`
  (`freeze_hash` verified; per-case geometry-only prediction included).
- Corrected implementation: `experiments/applied_system/runners/gcc_phat_runner_v2_lagfix.py`
  (`gcc_phat_argmax_v2_lagfix`).
- Versioned artifacts: `gcc_phat_v2_lagfix_raw.json` (+ sidecar, 50 records
  with per-record SHA-256 sidecars) and `gcc_phat_v2_lagfix_results.json`
  (+ sidecar).
- Regression tests: `experiments/applied_system/tests/test_gcc_phat_lagfix.py`
  (26 synthetic tests; written and passing BEFORE the final rerun).

## 1. The hostile-review concern, restated

The review suggested that `gcc_phat_argmax_v1` "may map FFT correlation
index to lag incorrectly for unequal-length signals." This audit
(1) derives the intended linear cross-correlation lag convention
mathematically, (2) tests the runner on synthetic fixtures before looking
at any final outcome, (3) decides the verdict from that mathematics alone,
and only then (4) re-executes the comparator uniformly under the frozen
contract.

## 2. Mathematical lag convention (independent of any implementation)

Let the query/capture be `y_rec` with `Lx` samples and the reference
`y_ref` with `Ly` samples, both at 48 kHz. The frozen ground truth and both
runner versions share one convention:

```
lag m  <=>  y_rec[n] ~= y_ref[n - m]
```

i.e. the reference begins `m` samples into the capture; a positive offset
delays the reference, a negative offset trims its beginning. (The frozen GT
is `payload_start_in_trimmed - slice_start` on this same convention, which
is why RhythmAlign's millisecond-correct positives confirm it.)

The linear cross-correlation in this convention is

```
c[m] = sum_n y_rec[n] * y_ref[n - m],      m in [-(Ly-1), Lx-1]
```

(nonempty overlap exactly on that interval). Computing it by FFT requires
zero-padding both signals to `N = next_fast_len(Lx + Ly) >= Lx + Ly`; the
circular correlation array `C = IFFT(R * conj(F))` then satisfies

```
C[j] = c(j)        for j in [0, Lx-1]         (positive lags)
C[j] = 0           for j in [Lx, N-Ly]        (zero-overlap region)
C[j] = c(j - N)    for j in [N-Ly+1, N-1]     (negative lags)
```

because `y_ref`'s zero padding kills every wrapped term. **The exact
unwrap is therefore `lag(j) = j - N if j >= N - Ly + 1 else j`** — a
boundary that depends on BOTH signal lengths.

## 3. Root cause and exact old mapping

`gcc_phat_runner.curve_argmax_offset_samples` (v1, preserved verbatim)
unwraps at the length-independent midpoint:

```
v1:  lag(j) = j       if j < ceil(N/2)
     lag(j) = j - N   otherwise
```

This is correct only when the entire negative-lag support
`[N-Ly+1, N-1]` lies at or above `ceil(N/2)` (and the positive support
below it) — essentially `N >= 2*Ly`, which holds for equal lengths but
fails for unequal lengths whenever `next_fast_len(Lx+Ly)` is close to
`Lx+Ly`:

- **Query shorter than reference** (`Lx < Ly`, the final benchmark's
  geometry): negative lags `m` with index `j = N + m < ceil(N/2)` are
  reported as the POSITIVE lag `j = m + N` — exactly one FFT length too
  large. In the final data this region is a physically meaningful band
  (reported offsets of roughly [query length, N/2] seconds correspond to
  true placements starting deep inside the reference).
- **Query longer than reference** (`Lx > Ly`): the mirror defect — large
  positive lags reported negative by exactly `N`.

The PHAT curve, FFT length, and argmax index are all correct in v1; only
the final index→lag mapping is wrong. The estimator and the mapping must
not be conflated: v1's positive-stratum errors are dominated by genuine
spurious PHAT peaks (see §7), and the mapping defect touched only records
whose argmax landed in the misread band.

## 4. Synthetic validation (performed FIRST; no final data involved)

`tests/test_gcc_phat_lagfix.py` — 26 tests, all passing before the rerun:

- **Independent reference:** every fixture's expected lag is derived from
  a DIRECT linear cross-correlation (`scipy.signal.correlate`, direct
  method) with an explicit lag axis, itself hand-anchored on a 3×2
  impulse example. No FFT unwrap is involved in the expectation.
- **Exact-delta fixtures:** impulse pairs and exact delayed-copy
  broadband pairs (pure linear phase ⇒ the PHAT curve is an exact delta
  at the true lag), so any deviation is provably a MAPPING error, not an
  estimator error.
- **Coverage:** full unequal-length lag support over {query shorter,
  equal, query longer} × {0, ±1, both single-sample boundaries
  (`Lx-1`, `-(Ly-1)`), interior lags}; the two canonical misread
  geometries (e.g. `Lx=6000, Ly=20000, m=-14000`: v1 reports `+13000`,
  exactly `N=27000` too large; `Lx=20000, Ly=6000, m=+14000`: v1 reports
  `-13000`); a small-scale replica of the final benchmark geometry
  (short query, long reference, argmax deep in the misread band); a
  noise-added deterministic capture; a stride-37 full-lag sweep where v1
  is asserted correct exactly when the lag lies outside the misread
  region; sign-convention, determinism, file-contract, and
  v1-behavior-preservation checks (v1 still returns its documented
  misread on the canonical fixtures — preserved as evidence, not
  "fixed" in place).
- Existing v1 behavior elsewhere: equal-length fixtures keep `v1 == v2`;
  shallow negative offsets (the regime of the pre-existing sign test,
  which could not see this bug because `|-1 s| < N/2`) keep
  `v1 == v2`.

## 5. Exact corrected mapping (v2 `gcc_phat_argmax_v2_lagfix`)

```
v2:  lag(j) = j - N   if j >= N - Ly + 1
     lag(j) = j       otherwise
```

- Derived solely from the support geometry in §2; validated only on the
  synthetic fixtures in §4 before the rerun.
- `v2` imports `gcc_phat_curve` from `v1` verbatim — the curve, FFT
  length, and argmax index are bit-identical; only the unwrap differs.
  `native_scores` additionally records `argmax_index`, `fft_length`, and
  `lagfix_wrap_boundary_index` for auditability.
- The zero-overlap region `[Lx, N-Ly]` maps to `+j` under both rules; no
  frozen argmax landed there (see §6), so the choice is immaterial to
  this evidence and is documented for completeness.
- ALWAYS_OUTPUT semantics unchanged: no refusal, no threshold, no
  no-match detector.

## 6. Geometry-only prediction, frozen before the rerun

The correction manifest — frozen and hash-sealed BEFORE any v2 execution
— reconstructs each of the 50 frozen v1 argmax indices from the frozen
records' `lag_samples` plus the frozen file lengths (hash-verified
trimmed inputs and references) alone, classifies each index against the
support regions, and applies the corrected unwrap on paper:

| Region (actual frozen file lengths) | Records |
|---|---:|
| positive support `[0, Lx-1]` (mapping identical) | 14 |
| negative at/above midpoint (mapping identical) | 34 |
| **negative below midpoint (v1 misread)** | **2** |
| zero-overlap region (argmax on numerical dust) | 0 |

Predicted changed records: **`final21__positive` and
`final21__wrong_ref` only.** This prediction was derived from frozen v1
raw outputs and frozen input geometry — **no ground truth, no scoring
outcome, and no RhythmAlign/NCC/Panako/Kdenlive output entered the
correction, the fixtures, the manifest, or the prediction.**

The rerun then verified, per record, that the recomputed v2 argmax index
equals the pre-registered prediction (all 50 matched; any mismatch would
have aborted before writing).

## 7. Uniform GCC-only re-execution (frozen contract)

All 50 GCC-eligible cases (24 primary positives, 24 directed
wrong-reference pairs, 2 strict repeats) were re-executed with
`gcc_phat_argmax_v2_lagfix` on the byte-identical frozen trimmed inputs
and references (SHA-256 verified against the frozen benchmark manifest at
execution, recorded per record), loaded identically to the frozen run
(float64, mean of channels, native 48 kHz), same environment
(numpy 2.2.6 / scipy 1.15.3 / Python 3.10.11 as the frozen run).

**Reported-lag changes (exactly the two predicted records):**

| Record | v1 (misread) | v2 (corrected) | GT | v1 → v2 outcome @100 ms |
|---|---:|---:|---:|---|
| `final21__positive` | +97.6494 s | **−118.350625 s** | −86.4561 s | WRONG_ACCEPT → WRONG_ACCEPT |
| `final21__wrong_ref` | +90.3092 s | **−123.5308125 s** | (no true placement) | WRONG_ACCEPT → WRONG_ACCEPT |

All 48 other records report lag-identical offsets. The corrected
`final21__positive` placement is a spurious peak (31.9 s from GT) — the
mapping fix corrects the reported lag, it does not rescue the case.

**Scored results (frozen scoring contract, identical at 50/100/150 ms):**

| Stratum | v1 (frozen) | v2 lagfix | Outcome changes |
|---|---|---|---|
| Primary positives | 10 CORRECT_ACCEPT / 14 WRONG_ACCEPT | 10 / 14 | none |
| Wrong references | 24/24 WRONG_ACCEPT | 24/24 WRONG_ACCEPT | none |
| Strict repeats | both WRONG_ACCEPT | both WRONG_ACCEPT | none |

Distribution-level effects of the correction (for future paper use):

- All-produced positive absolute error (n=24): median unchanged at
  29.3135 s; maximum improves from 184.1055 s (the misread artifact) to
  113.1878 s.
- CORRECT_ACCEPT-conditional errors: unchanged (n=10, median 0.219 ms,
  max 3.771 ms).
- Wrong-reference |offset| magnitudes (n=24): median unchanged at
  64.2303 s, max unchanged at 132.7303 s; `final21__wrong_ref`'s
  magnitude becomes 123.5308 s.
- Strict repeats: repeat01 and repeat02 remain wrong placements
  (−58.6443 s / −64.2271 s) — the v1 "consistently wrong" repeat story
  is unchanged.

## 8. Why the correction is outcome-independent

1. The corrected mapping is a theorem about zero-padded FFT
   cross-correlation (§2) — it does not reference the data.
2. The v2 implementation was validated exclusively on synthetic fixtures
   before any final case was re-executed (§4).
3. The set of affected records was predicted from frozen v1 native
   outputs and frozen file lengths and hash-sealed in the correction
   manifest BEFORE the rerun (§6); the rerun merely confirmed the
   prediction.
4. No threshold, pairing, tolerance, scoring rule, or other system moved;
   no comparator other than GCC was re-executed; no final-case GT
   influenced anything (the GT column in §7 is shown only to interpret
   already-scored outcomes, exactly as the frozen scoring contract does).

This follows the protocol's post-freeze bug policy: demonstrable
implementation bug → preserve original evidence → outcome-independent
explanation → regression test → versioned correction → uniform rerun of
every affected case under the same scientific contract. (The affected
set here is all 50 GCC cases, because the runner is a single uniform
implementation; the correction changes only the two records above.)

## 9. Evidence preservation

- `final_comparator_raw.json` and all 200 per-record v1 files: untouched,
  byte-identical (hash-verified by the rerun script on every invocation
  and by test; v1 = defective-implementation evidence, retained as the
  frozen comparator of record for the sealed benchmark).
- `final_benchmark_results.json`, `final_benchmark_reporting_v2.json`:
  byte-identical (SHA-256 pinned in the correction manifest and re-verified
  before and after the rerun).
- No non-GCC record was re-executed or modified. RhythmAlign, NCC,
  Panako, and Kdenlive evidence is exactly as sealed.
- All new artifacts are additive and versioned: correction manifest,
  `gcc_phat_v2_lagfix_records/` (50 records + sidecars),
  `gcc_phat_v2_lagfix_raw.json` + sidecar,
  `gcc_phat_v2_lagfix_results.json` + sidecar.

## 10. Versioning plan

- `gcc_phat_argmax_v1` (`experiments/applied_system/runners/gcc_phat_runner.py`)
  remains in the repository unchanged, including its docstring and its
  defective unwrap, with regression tests pinning the defective behavior
  on the canonical unequal-length fixtures.
- `gcc_phat_argmax_v2_lagfix` is the lag-valid implementation. The
  manuscript may treat v2 as the valid GCC comparator and v1 as preserved
  defective-implementation evidence; outcome counts are identical under
  both (§7), so the sealed benchmark's comparator conclusions do not
  change — only two reported offset magnitudes and the all-produced error
  maximum do.

## 11. Note on QC trim bookkeeping (no bearing on this audit)

The committed QC take records' `trim_end_sample` values exceed the
delivered trimmed WAV frame counts by a constant 172,800 samples (3.6 s)
on every take. Ground-truth labels were verified against the DELIVERED
files by the frozen direct-correlation crosscheck (all 26 within 10 ms),
every system consumed hash-identical delivered files, and this audit's
lengths (and the frozen manifest's) are read from the delivered files.
Recorded here so future geometry work uses actual file frames, not the QC
trim bookkeeping.

## 12. Clarifying addendum (second review, 2026-09-20): PHAT weighting and the zero-overlap region

Purely clarifying; sections 1–11 above are preserved verbatim and no recorded
value, hash, prediction, or outcome changes. The second independent review
flagged that the zero-overlap statements above could be over-read, so this
addendum states the boundary explicitly:

- §2's identity `C[j] = 0` on `[Lx, N-Ly]` is a statement about the ORDINARY
  linear cross-correlation, where it holds algebraically because `y_ref`'s
  zero padding kills every wrapped term. The evaluated curve is the
  PHAT-weighted spectral correlation, and PHAT weighting does not preserve
  those zeros exactly: values of the weighted curve in the zero-overlap index
  region are not mathematically guaranteed to be zero, and they are not
  claimed to be numerical roundoff.
- This audit makes no claim — general or empirical — about PHAT-weighted
  values outside the physical overlap support, and the final benchmark does
  not validate any theorem about them.
- The facts this evidence relies on are narrower and sufficient: (a) the
  physically meaningful linear-lag support is determined by the two signal
  lengths; (b) the v2 unwrap follows that physical support geometry, while
  the v1 midpoint unwrap was invalid for unequal lengths; and (c) none of the
  50 stored final argmax indices fell in the physical zero-overlap index
  region (§6: 0 records there), so the weighted curve's behavior in that
  region and the unwrap choice there are immaterial to every recorded and
  scored v2 outcome.
