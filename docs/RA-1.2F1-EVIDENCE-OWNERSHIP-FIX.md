# RA-1.2F1 — Peak-level evidence ownership fix

Date: 2026-10-07 (Asia/Shanghai). Scope: production alignment fix and validation;
no merge, version bump, installer, tag, release, or v1.2.1 publication.

Final disposition: `READY_FOR_RA12F1_CTO_REVIEW`.

## Defect and production provenance

F0's conclusion is confirmed by the source and the real AP reproduction. The
generators nominated the correct PCEN+HPSS peak at **+11.377777777777778 s**.
The true hypothesis also owns a tonal peak at +11.331337868480725 s and passes
CASE A. A different hypothesis at +11.633197278911565 s owns onset and weak
plain-PCEN candidates; its own PCEN Z is 5.237893392079429 and margin is
0.9670952503624239, insufficient for CASE B.

Before this fix, `_build_clusters()` treated family membership as permission
to score any sibling method in a +/-13-frame window (about +/-0.301859 s).
Membership tolerance is only 0.15 s. The false hypothesis's plain-PCEN member
therefore authorized a PCEN+HPSS search that imported the true hypothesis's
peak, Z 25.1062244640698 and margin 3.065276573513938. Two labels then qualified,
and `len(accepted) > 1` produced `ABSTAIN_AMBIGUOUS_CLUSTER` before temporal
verification. `_comparable_competitor_exists()` was not the cause and is
unchanged. Its separate CASE B asymmetry remains outside this phase.

This is a v1.2.0 production defect: the starting main engine blob and
`v1.2.0:alignment_engine_v2.py` both equal
`6b82dad1dd1f80fc76d8d87a45ed5527d505ba57`. The AP capture was excluded from
the historical positive corpus. Historical release success did not exercise
it. F0 actually ran on `cross-platform/linux` at
`34078ec82cec2991b88df061746dd2f0f5809615`; its local Markdown incorrectly
called that branch main. This hotfix does not inherit that branch's history.

Threshold tuning was rejected because the true candidate already passed the
floors, margins, overlap and temporal criteria. Changing floors or merging
neighboring labels by widening membership would conceal an attribution bug.
Every `DecisionPolicy` default, peak nomination separation and top-N setting
is unchanged. No song, offset, path or media hash is special-cased in production.

## Corrected evidence topology and exact implementation

Old topology: nominated family member -> sibling method's wider window ->
possibly another hypothesis's independent peak -> inflated family evidence.

Corrected topology: independent method peak -> nominated candidate -> exactly
one hypothesis -> strongest owned method contribution -> one family winner.

Changes in `alignment_engine_v2.py`:

- `CandidateEvidence.peak_index` retains the exact correlation index;
  `peak_id` is the method/index pair, scoped to one analysis. `_family_candidates()`
  attaches it when nominating each peak.
- `_build_clusters()` retains the existing membership/upper-median algorithm.
  Stable offset/method/index sorting makes equal-offset nomination order
  deterministic. Method scoring selects only that cluster's owned candidates,
  using their exact peak Z and offset. There is no wider scoring-window search
  or representative-value fallback.
- `_margin_for_owned_peak()` divides the owned supplier by the strongest
  unowned independent peak from that method, including non-nominated peaks.
  Overlapping windows cannot supply the numerator or hide a competitor.
- Family aggregation follows ownership and retains one strongest contribution.
  Plain PCEN and PCEN+HPSS remain one `pcen_spectral` family.
- `_serialize_cluster()` includes the exact representative, candidate identities,
  winner/supplier method, index, identity, full-precision supplier offset,
  ownership flag, and CASE A/B failed checks. Existing rounded display fields
  remain available. No ordinary UI wording or product log flow changed.
- `_deciding_pcen_method()` uses the family winner from the cluster owning the
  selected offset. This makes temporal verification follow the recorded
  supplier instead of scanning unrelated candidates within one second. Older
  diagnostic/test decisions retain a fallback restricted to the owning cluster.

One nominated method/index pair is assigned once. Family evidence is selected
from that assigned set, so one method peak cannot decisively score two
different hypotheses. The ownership flag is supported by candidate/supplier
identity checks in the new tests; it is not used as an alternative acceptance
threshold. Offset selection, acceptance floors, ambiguity comparator and
temporal concentration calculation are unchanged.

## Synthetic regressions

`tests/test_ra12f1_evidence_ownership.py`: **16 passed**. Coverage includes the
exact F0 topology, same-method leakage, unique peak ownership, independently
supported ambiguity, one PCEN-family vote, all three CASE B safeguard cases,
all generator permutations, moving representatives, membership boundaries
(including exact equality), former scoring-window boundaries, and temporal
verification's actual supplier.

The same-method stress fixture uses only a test policy with 0.8 s membership:
two genuinely independent generator peaks more than 1.5 s apart then fit
within the old +/-1.6 s scoring window while belonging to different clusters.
This tests the peak-level failure without changing production's 0.15 s default
or mocking away independent peak nomination.

The replay harness also loads the exact starting engine in memory for a
before/after comparison. Both structural and same-method cases previously
returned ambiguity after borrowing the strong peak. Afterward the true CASE A
is accepted; the false hypothesis retains its own weak supplier. Same-method
false margin changes from the borrowed **6.25** to its own **0.208**. Genuinely
supported alternatives still return `ABSTAIN_AMBIGUOUS_CLUSTER`.

## Real AP and temporal support

Three unmodified, fresh-process calls to production `find_offset_v2()`:

| Run | Status | Reason | Offset (s) | Deciding temporal share |
|---|---|---|---:|---:|
| 1 | accepted | ACCEPT_DUAL_FAMILY | 11.377777777777778 | 0.0241 |
| 2 | accepted | ACCEPT_DUAL_FAMILY | 11.377777777777778 | 0.0241 |
| 3 | accepted | ACCEPT_DUAL_FAMILY | 11.377777777777778 | 0.0241 |

Complete decision payloads are identical after excluding runtime fields. All
three verify `pcen_hpss`, with `applied=true`, 140 bins and effective bins 81.21;
the unchanged threshold is 0.25. The deciding candidate now reaches and passes
the normal production temporal gate. The before result was the deterministic
F0 `ABSTAIN_AMBIGUOUS_CLUSTER`; it never reached that gate.

The false +11.633197278911565 label now records its owned plain-PCEN supplier
at exactly that offset, Z 5.238 and margin 0.967 in rounded diagnostics.
CASE B fails `pcen_z` and `pcen_margin`. It receives no true PCEN+HPSS peak.

All **19** locally registered wrong-reference tracks for this AP capture
abstain. The correct reference is excluded from the 20-track registry.
An additional actual `SyncWorker` replay asserts that its entry point is the
revised production function, executes the real AP analysis, and receives the
passing temporal decision. Only export is replaced by a recorder; the positive
reaches it once, the real wrong-reference abstention reaches it zero times,
and legacy-v1 calls remain zero. No media is physically exported. Existing
product integration tests also pass. This validates source-level product
behavior; no packaged GUI or installer was built or tested in this phase.

## Historical safety and preservation

`experiments/ra12f1_evidence_ownership/run_regression.py` reuses canonical D1
data, populations and audio builders. Historical artifacts are read without
overwriting them. Positives run the actual `validate_full_positives.main()`
with its output redirected to ignored scratch storage. The clean/dev grid
reuses `common.families()` plus production `decide_from_families()` and
`_apply_temporal_support()` with attached PCEN features. All four cached curves
were checked bit-for-bit against `_run_generators()` for a complete real pair
before the grid; negative/tiled cases run production `decide_alignment()`.

| Population | Result |
|---|---|
| Integrated positives, 85 | 55/55 accepts and 30/30 abstentions preserved; accepted offset change 0.0 s |
| Low-SNR lingduihua_132 | +12.49233560090703 s, ACCEPT_PRIMARY_WITH_CORROBORATION; inside +12.4 +/-0.4 s manual interval |
| Ordinary strong positives | All 28 strong real positives preserve acceptance and offsets |
| DEV concentrated wrong accepts, 18 | 18/18 abstain through ABSTAIN_CONCENTRATED_EVIDENCE |
| Directed clean wrong songs, 156 | 156/156 abstain |
| Ordinary mismatches, 10 | 10/10 abstain |
| Hard negatives, 10 | 10/10 abstain |
| Tiled/repeated cases, 4 | 4/4 abstain with ambiguity |
| Astra tr_lingduihua -> tr_yanwulieche | ABSTAIN_CONCENTRATED_EVIDENCE; share 0.9456 |
| Known room-grid residual | Still accepted at +59.72172335600907 s, ACCEPT_DUAL_FAMILY; share 0.0613 |

The residual offset equals its historical result. Its target identity remains
unresolved; distributed correlation is not proof of correct song identity.
It is reported separately and was neither fixed nor reclassified. No new
false ACCEPT was found in the designated negative populations.

The 56 semi-synthetic positives retain 26 accepts and 30 abstentions; the
maximum accepted construction-exact timing error is 0.013650793650793247 s.
The 29 real positives (28 strong and one low-SNR) all remain accepted. The
low-SNR manual-interval deviation is 0.0923356009070293 s and is reported
separately from construction-exact errors. Its temporal gate passes at share
0.0836. No intentional positive-population abstention converted to ACCEPT.

These are reused development/safety regression populations. Semi-synthetic
timing labels are construction-exact; the low-SNR real case has a manual
+12.4 +/-0.4 s interval; other real positives mostly have pairing evidence.
Regression preservation is not new independent timing ground truth or a
population false-accept-rate estimate. This one AP repair does not establish
universal correctness, and the existing nomination/clustering, CASE B
comparator and residual identity limitations remain.

## Test and static validation

- Full `python -m pytest tests/ -q`: **96 passed in 32.21 s**.
- Focused Engine v2: **13 passed**; temporal support: **11 passed**;
  ownership: **16 passed**. Combined initial focused run: **40 passed**.
- `python -m py_compile` for all three changed/added Python files: passed.
- `git diff --check`: passed. Existing tests were not modified or weakened.

The first full-suite run overlapped AP decoding and its global temporary-file
count assertion observed another process's files (1 failed, 95 passed).
Repeating the unchanged tests after AP file-entry executions ended passed;
the initial log is preserved in ignored local scratch storage. The final
suite also includes the tightened supplier-selection test.

## Privacy, replay and Git provenance

The original primary checkout and all three local F0 artifacts were preserved;
their SHA-256 values remain unchanged. F0 JSON, F0 Markdown and its script were
not staged, copied into public artifacts, or committed. Local media manifests
and audio caches remain gitignored. Committed F1 evidence is assembled from
algorithm decisions and neutral case identifiers, with no absolute media
paths, raw FFmpeg metadata, device details or location/recording metadata.

Sanitized machine evidence: `experiments/ra12f1_evidence_ownership/results/regression.json`.
Full local logs/decisions: ignored `results/ra12f1*`. From the hotfix root,
using the existing Python environment and local gitignored manifests:

```text
python experiments/ra12f1_evidence_ownership/run_regression.py synthetic
python experiments/ra12f1_evidence_ownership/run_regression.py positives
python experiments/ra12f1_evidence_ownership/run_regression.py safety
python experiments/ra12f1_evidence_ownership/run_regression.py ap --video <AP-video> --music <correct-reference>
python experiments/ra12f1_evidence_ownership/run_regression.py product --video <AP-video> --music <correct-reference>
python -m pytest tests/ -q > results/ra12f1-pytest.log
python -m pytest tests/test_alignment_engine_v2.py -q > results/ra12f1-engine-tests.log
python -m pytest tests/test_ra12d1_temporal_support.py -q > results/ra12f1-temporal-tests.log
python -m pytest tests/test_ra12f1_evidence_ownership.py -q > results/ra12f1-ownership-tests.log
python experiments/ra12f1_evidence_ownership/run_regression.py summary
git diff --check
```

Run file-entry media validations separately from pytest's global temporary-file
counter test. No threshold search or recalibration is part of replay.

- Starting fetched `origin/main`: `c92e82763350d70e7d5982de2dcdcb99cebc1e83`.
- Branch: `hotfix/ra12f1-evidence-ownership`.
- Worktree: `D:\Code\RhythmAlign-ra12f1`.
- Final implementation commit SHA (code/tests/replay/sanitized evidence):
  `9d5973e61dd0bba386501d7bf309e7e7fb83c18a`.
- This report is a subsequent documentation-only commit. Its final delivery
  SHA is returned in the delivery response and can be obtained without a
  self-referential hash using
  `git log -1 --format=%H -- docs/RA-1.2F1-EVIDENCE-OWNERSHIP-FIX.md`.
- Only the hotfix branch is pushed; its remote HEAD is checked against local
  HEAD after push. The hotfix worktree is left clean. Main is not merged.
- No version/update/release files change; no installer, tag or release is created.
