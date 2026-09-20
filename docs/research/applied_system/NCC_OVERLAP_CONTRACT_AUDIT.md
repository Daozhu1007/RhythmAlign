# NCC Overlap Contract Audit (COMPARATOR-INTEGRITY-1)

Status: **CONTRACT_OBSERVATION_CONFIRMED — reporting-only; no NCC
experiment was rerun, modified, or tuned.** Executed 2026-09-20 on
`research/applied-system-paper`, starting HEAD `0f37cbc`, from existing
stored records and frozen code only.

## 1. Scope and prohibitions honored

This audit creates no new NCC experiment. `ncc_argmax_v1` code, its 50
frozen records, thresholds, and semantics are untouched. Nothing here
tunes or proposes a tuned NCC variant on exposed final data, and nothing
claims that adding a 30 s minimum-overlap threshold to NCC would recover
the correct offsets on the cases below — that would be a different,
unevaluated system (the frozen protocol reserves such a change for a new
protocol and new data).

## 2. Exact minimum-overlap behavior of the two systems

**NCC (`ncc_argmax_v1`, `experiments/applied_system/runners/ncc_runner.py`).**
The curve covers EVERY lag with a nonzero-overlap possibility:
`lags = [-(Ly-1), Lx-1]` (full-mode convolution + explicit lag axis).
Normalization is per-lag overlap energy,
`ncc[m] = sum rec[m+i]*ref[i] / (||overlap_rec|| * ||overlap_ref||)`.
There is **no minimum-overlap requirement of any kind** — a 1-sample
overlap is a legal argmax candidate. The only guard is a relative energy
floor (`max(e_rec) * max(e_ref) * 1e-12`) that zeroes near-silent windows;
it is a silence guard, not a duration guard. Two structural consequences,
both verified on synthetic fixtures in
`tests/test_gcc_phat_lagfix.py`:

- A single nonzero sample overlapping a single nonzero sample scores
  exactly ±1.0 — a Cauchy-Schwarz-maximal tie available at the extreme
  edges of the lag axis.
- At final-data lengths the floor suppresses literal one-sample dust, but
  SECOND-scale overlaps remain live candidates; per-lag normalization
  makes a short overlap with locally consistent content competitive with
  the true full-overlap peak.

**RhythmAlign v1.2.0 (frozen `alignment_engine_v2.py`).** The decision
policy enforces a frozen minimum-overlap requirement:
`DecisionPolicy.min_overlap_s = 30.0` — candidates whose
`usable_overlap_s` (music/video overlap on the production offset
convention) is below 30 s are hard-rejected (CASE E edge-lag guard), and
the system abstains (`ABSTAIN_INSUFFICIENT_OVERLAP`) when the best
cluster is below it. The 30 s line is necessary but not sufficient for
acceptance (feature strength, uniqueness, corroboration, and temporal
support gates also apply), so RhythmAlign's candidate policy excludes
entire regions of the lag axis that NCC scores.

## 3. Overlap duration of every NCC positive WRONG_ACCEPT

Usable overlap at each accepted placement, computed from the frozen
`ncc_argmax_v1` records (`lag_samples`) and the frozen trimmed-input /
reference lengths (actual file frames, as pinned in
`gcc_phat_v2_lagfix_correction_manifest.json`; see the QC bookkeeping
note in `GCC_PHAT_LAG_AUDIT.md` §11):

| Case | NCC placement | Usable overlap | Below RA's 30 s? |
|---|---:|---:|---|
| final02 | +63.312 s | 1.675 s | yes |
| final18 | −150.995 s | 1.234 s | yes |
| final19 | −150.296 s | 3.589 s | yes |
| final20 | −149.811 s | 3.522 s | yes |
| final23 | +59.823 s | 4.694 s | yes |

**All five NCC wrong positives occur below RhythmAlign's frozen
30 s minimum-overlap threshold.** They are edge placements: the argmax
landed where the query and reference barely touch.

**No NCC CORRECT_ACCEPT case has similarly short overlap.** All 19
correct primary placements (and both correct repeats) sit at 60.414 s of
usable overlap or more (the physical maximum for a ~65 s query inside a
longer reference). The separation is complete and wide: every wrong
positive ≤ 4.694 s, every correct positive ≥ 60.414 s, and the frozen
30 s policy line falls in the empty middle. (For contrast, GCC-PHAT's
wrong positives sit mostly at 60+ s overlaps — genuine spurious peaks
with abundant overlapping evidence — plus one sub-30 s placement and the
misread `final21` record corrected in `GCC_PHAT_LAG_AUDIT.md`; the NCC
short-overlap mechanism is distinct.)

## 4. Does the manuscript over-attribute the difference to "selectivity"?

The PAPER-DRAFT-0 language is careful *not* to claim a causal
refusal-alone mechanism (claim ledger L05/L29: "The measured separation
concerns unsupported placements"; §7: no gate-level causality; §4.5:
always-output semantics described natively). Nothing in the draft is
false.

However, the draft is silent on the candidate-policy difference that this
audit makes visible: RhythmAlign never scores, and could never accept,
the short-overlap placements where NCC's five wrong positives live. A
reader could reasonably infer that the NCC-vs-RhythmAlign difference on
positives (5 wrong accepts vs 0) measures the value of *refusal* alone;
it does not — RhythmAlign's 30 s edge-lag guard alone excludes all five
placements regardless of any other gate. The revision should say so
explicitly, e.g.:

> "NCC remains an unconstrained argmax control. Its five wrong positive
> placements occurred at short edge overlaps that RhythmAlign's frozen
> candidate policy excludes; therefore the comparison reflects both
> estimator and candidate-policy differences and does not isolate the
> causal value of abstention."

Equally important, the converse is not claimed either: because NCC's
score at the true lag on those five takes is unknown (scoring it would
be a new experiment on exposed final data), nothing can be said about
whether a 30 s-thresholded NCC would recover the correct offsets, produce
different refusals, or change its wrong-reference behavior.

## 5. Reproducibility

Every number in §3 is recomputable from committed artifacts: per-case
`lag_samples` from `final_comparator_raw_records/ncc_argmax_v1__*.json`
(hash-verified against `final_comparator_raw.json`), per-case
`query_samples` / `reference_samples` from the correction manifest
(read from the frozen WAVs at manifest-freeze time), and the production
`_usable_overlap_s` formula. `tests/test_comparator_integrity_audit.py`
pins the recomputation.
