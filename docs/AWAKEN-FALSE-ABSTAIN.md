# Awaken false abstention — investigation and candidate corroboration

Date: 2026-10-09. Target: v1.2.1 / Engine v2.

Disposition: **VALIDATION_PASS_RECOMMEND_REVIEW**. Dedicated branch:
`codex/awaken-corroboration`. Review recommendation: the bounded repair below.
No main merge, release metadata change, installer, tag or publication.

## Reproduction and root cause

Baseline `552764763fc2dabb0e087f541c2e5646b050604d` is the current main source.
Its engine is byte-identical to the `v1.2.1` tag. Before editing production,
the supplied script ran against that engine and returned
`ABSTAIN_PRIMARY_NOT_CORROBORATED`, with no offset. Subsequent comparisons
load that exact original engine from Git in an isolated module.

The bundle supplies decoded mono PCM at 22,050 Hz. Original video, original
MP3, packaged GUI interaction and final exported media are outside this
reproduction. The Owner confirmed song identity. Agreement among algorithms
does not establish sample-exact independent timing ground truth.

| Observation from unchanged production definitions | Measured value |
|---|---:|
| PCEN+HPSS owned candidate | +10.95981859410431 s |
| PCEN+HPSS Z / owned independent-peak margin | 67.124 / 6.876 |
| Plain PCEN candidate / Z | +10.95981859410431 s / 17.463 |
| Hybrid owned candidate / Z | +11.029478458049887 s / 4.663 |
| Onset Z at the PCEN candidate | 1.590810 |
| Maximum onset Z in the nearby sampled tolerance window | 1.874087 |
| Nearby independent onset peak rank | 8 |
| Deciding PCEN+HPSS strongest 1 s signed-bin share | 0.0204 |

Candidate generation uses four independent peaks per method, separated by
1.5 s. The correct PCEN candidates and the correct hybrid peak already
belong to the same 0.15 s cluster and retain unique ownership. PCEN and
PCEN+HPSS aggregate into one family. The cluster has 135 s of overlap.

Case A fails only `tonal_z`: 4.663 is below 5.0. Case B fails
`onset_missing`: its top four nominations are elsewhere. This is partly a
nomination limitation, but adding the nearby rank-8 onset cannot repair the
decision: its Z remains below 2.0. Replays with 4, 8, 16, 64 and all 156
independent onset-peak nominations still abstain. Global peak rankings,
clustering and the later ambiguity comparator do not discard the true PCEN
primary. Temporal verification is not reached by the original abstention;
an explicit diagnostic evaluation of the actual supplier passes it.

**Confirmed root cause:** the existing acceptance paths require either a
qualifying tonal primary or qualifying onset corroboration, and this real
positive has neither despite strong, distributed spectral evidence. The
tonal miss is a score-floor limitation on this input; onset also fails as a
placement witness here. These measurements do not justify globally
recalibrating either score floor. Physical explanations such as taps or
microphone coloration were not independently established.

Independent linear GCC-PHAT at full sample rate gives +10.951565 s. Four
25 s reference excerpts starting at 10, 40, 70 and 100 s, each searched
against the complete recording, give +10.952744, +10.951610, +10.953968 and
+10.950839 s (3.13 ms span). The supplied approximate GCC results are
consistent in placement; their exact numerical margin and 2 ms spread were
not reproduced with these FFT/window definitions. The implementation's
four disjoint anchored windows give +10.956327, +10.953878, +10.950204 and
+10.951429 s. All corroborate the spectral placement within 10 ms.

## Historical constraints and design comparison

The investigation reviewed RA-1.2B, C, D and D1, plus F1 ownership:

- [B](RA-1.2B-ALIGNMENT-ENGINE-V2.md) establishes primary versus
  corroborating roles. Correlated PCEN derivatives supply one family.
- [C](RA-1.2C-CALIBRATION-HARDENING.md) already reports L3/L4 positives
  losing tonal/onset support. Its historical project holdout is reused as
  regression material here, not presented as a fresh confirmatory set.
- [D](RA-1.2D-DEFAULT-INTEGRATION.md) makes abstention a safe stop before
  export. Automatic legacy-v1 fallback stays unreachable.
- [D1](RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md) documents 22 clean wrong-song
  accepts caused by concentrated shared content. Its deciding-member gate
  remains mandatory. Its rejected local *feature* verifier and uncalibrated
  global GCC argmax are not silently promoted into an acceptance rule.
- [F1](RA-1.2F1-EVIDENCE-OWNERSHIP-FIX.md) establishes exact peak ownership;
  this repair neither imports sibling peaks nor widens clustering.

Development comparison used 146 cases: 36 construction-exact positives,
29 historical real pairs, Awaken, 10 ordinary mismatches, 6 hard negatives,
2 tiled ambiguity cases, 20 Awaken wrong references and 42 clean wrong-song
pairs. Six additional shared-event counterexamples were examined before
opening validation. Threshold and design selection never used the later
holdout or acoustic outputs.

| DEV candidate waveform policy | Additional positives | Wrong upgrades |
|---|---:|---:|
| One window, Z >= 5, margin >= 1.2, tolerance 0.15 s | 17 | 0 |
| Four windows, same permissive floors | 17 | 0 |
| **Four windows, Z >= 7, margin >= 1.4, tolerance 0.10 s** | **17** | **0** |
| Four windows, Z >= 9, margin >= 2, tolerance 0.05 s | 17 | 0 |
| Four windows, Z >= 12, margin >= 2, tolerance 0.05 s | 16 | 0 |

Seventeen means 16 exact-insertion cases and Awaken. Local peaks in tested
wrong-song proposals reach only about Z=5 and margin=1.25; the weakest
Awaken window reaches Z=10.017 and margin=2.594. The selected floors leave
development headroom on both sides. More restrictive floors did not provide
observed safety gains; Z=12 loses the motivating real positive. Four windows
were retained as an explicit distribution requirement despite equivalent
coverage in these development data. A 0.05 s maximum inter-window spread
also passed all proposed development upgrades and was frozen before testing.

The four-event stress pair has very strong waveform agreement at its shared
placement but remains spectrally ambiguous. This is direct evidence that
waveform agreement alone is insufficient and that the existing ambiguity
stop is load-bearing.

## Implementation

`alignment_engine_v2.py` adds `ACCEPT_PRIMARY_WITH_WAVEFORM` only after
`ABSTAIN_PRIMARY_NOT_CORROBORATED`, and only for an owned PCEN primary whose
remaining Case B failures are onset checks. Existing accepts and all other
abstention reasons retain their decisions. The candidate must:

1. Retain Case B's Z >= 7 and margin >= 1.4 and minimum geometric overlap.
2. Have no materially comparable PCEN competitor under the existing ratio.
3. Pass D1 using the actual deciding member's feature matrices. Missing
   features prevent rescue.
4. Pass `alignment_waveform.py`: four disjoint 8–25 s windows spread across
   the actual intersection. Each window's **linear** GCC-PHAT searches all
   local lags with at least 80% overlap (up to +/-5 s for a 25 s window).
   Each own argmax must agree with the spectral supplier within 0.10 s,
   have Z >= 7 and peak dominance >= 1.4 against lags separated by 1.5 s.
   The four recovered offsets must span at most 0.05 s.

No whole-song waveform argmax is used as a fallback. Four windows verify
one candidate; they are not independent votes. PCEN variants remain one
family. The accepted offset is the spectral supplier, not a waveform
refinement. Verifier errors, unavailable audio and competing survivors
stop safely. D1 remains in the final acceptance path.

All old `DecisionPolicy` values and the ASTs of generation, nomination,
Case A/B checks, offset selection, ambiguity comparison, concentration and
temporal rejection functions are unchanged. Cluster diagnostics add
read-only local curve observations without using those values as evidence.

## Validation

The selected policy file was frozen before validation. Every actual
production positive call records the unmodified generators' results and
replays the frozen baseline on those same curves. The 380-pair grid reuses
canonical per-source features; all four reconstructed curves were checked
bit-for-bit against production on the archived blocker.

| Population | v1.2.1 accepts | Revised accepts | Wrong accepts |
|---|---:|---:|---:|
| Calibration exact-insertion positives, 36 | 17 | 33 | 0 |
| Historical project holdout exact-insertion positives, 20 | 9 | 17 | 0 |
| Historical real positives, 29 | 29 | 29 | No new offset changes |
| Source-disjoint historical acoustic positives, 26 | 22 | 24 | 0 |
| Awaken, Owner-confirmed identity | 0 | 1 | Timing is a regression estimate |

Historical positive coverage: **55/85 -> 79/85**. All 55 existing accepts
retain their exact offset and reason. Semi-synthetic accepted maximum exact
GT error is **0.016463 s**; holdout maximum **0.016145 s**. The acoustic
accepted maximum marker-GT error is **0.015675 s**. Its two improvements are
`final08__positive` and `final24__positive`. The low-SNR manual-interval case
retains +12.49233560090703 s inside +12.4 +/-0.4 s; its 0.092336 s deviation
from the manual interval center is not pooled with exact-GT errors.

All **484** designated rejection/ambiguity cases abstain:

- 380 directed clean wrong-song pairs, including all 22 archived concentrated
  wrong accepts, the 42 DEV pairs, 156 historical held-out pairs and 182
  cross-split pairs;
- 10 ordinary mismatches, 10 hard negatives and 4 tiled ambiguity cases;
- 20 Awaken wrong references;
- 24 frozen acoustic wrong references;
- 6 one/two/four shared-event constructions and 30 deterministic no-signal
  noise/tap cases (seeds 100–129, noise gain 0.12, tap gain 0.30).

**New confirmed wrong accepts: 0.** Existing accepted offsets are bit-identical.
The room-grid pair `haiditan_ds_1 x tr_hongzhoutian` remains accepted at
+59.72172335600907 s with concentration 0.0613. Its identity remains
unresolved; it is excluded from confirmed-wrong and positive-correctness
counts. The repair does not reinterpret that residual.

Full final suite: **121 passed**. Regression tests cover unequal-length
linear lag signs, both offset signs, missing windows, wrong local lag,
silence, nonfinite and short audio, inter-window inconsistency, verifier
errors, unavailable temporal features, concentrated primary evidence,
comparable competitors, protected rejection reasons and the real fixture.
The actual SyncWorker/file entry on supplied decoded WAVs reaches the export
recorder once for the positive and zero times for a wrong reference; legacy
calls and physical exports are zero. This is source routing evidence,
not packaged GUI or original-video export acceptance.

Three fresh processes on final source all return the identical decision at
+10.95981859410431 s after removing runtime fields. The isolated waveform
verifier costs 0.207–0.228 s across nine sequential measurements on this
fixture; this is verifier overhead, not a packaged end-to-end timing claim.

## Diagnostics, reproduction and evidence ownership

Both workers retain their latest full structured decision. Settings
**Copy diagnostics** includes Sync/Analyze decisions with full-precision
supplier scores and offsets, nominations, Case A/B failures, nondeciding
local curve observations, candidate concentration and waveform window
values/failed checks. Ordinary alignment logs remain compact. A failed new
analysis clears the previous decision instead of showing stale evidence.

The real-positive fixture contract is
`tests/fixtures/awaken_positive.json`; decoded audio stays in the private
bundle. The test automatically uses `results/awaken/bundle`, or reads the
ZIP specified by `RHYTHMALIGN_AWAKEN_REPRO_ZIP`. Both exact PCM hashes are
checked. Without either private fixture, that single test explicitly skips.
It ran and passed locally.

Reproduction commands from the repository root:

```powershell
$env:PYTHONUTF8 = '1'
$env:RHYTHMALIGN_AWAKEN_REPRO_ZIP = '<private reproduction ZIP>'
.venv/Scripts/python.exe experiments/awaken_corroboration/prepare_fixture.py
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe experiments/awaken_corroboration/verify_repro.py
.venv/Scripts/python.exe experiments/awaken_corroboration/study.py dev
.venv/Scripts/python.exe experiments/awaken_corroboration/adversarial.py
.venv/Scripts/python.exe experiments/awaken_corroboration/select_policy.py
.venv/Scripts/python.exe experiments/awaken_corroboration/validate.py positives
.venv/Scripts/python.exe experiments/awaken_corroboration/validate.py negatives
.venv/Scripts/python.exe experiments/awaken_corroboration/validate.py acoustic
.venv/Scripts/python.exe experiments/awaken_corroboration/validate.py adversarial
.venv/Scripts/python.exe experiments/awaken_corroboration/validate.py product
.venv/Scripts/python.exe experiments/awaken_corroboration/acceptance.py
.venv/Scripts/python.exe experiments/awaken_corroboration/summarize.py
```

The study commands need the locally registered historical sources and the
bundle extracted into the ignored directory. The acoustic runner reads the
original frozen manifest from research commit
`59131c79afa4cd956174944bf6025230cf9b4e4f`, verifies every original input/reference
hash and preserves its labels. That branch and its artifacts are unchanged.
Its historical labels are useful timing evidence; this engineering reuse
does not rewrite the earlier paper study or create fresh confirmation.

Committed review evidence:
`experiments/awaken_corroboration/results/validation_summary.json` records
the frozen policy, comparisons, changed case IDs, verified invariants and
hashes of local raw results. Full reproduction, per-case decisions,
fresh-process witnesses and logs remain under ignored `results/awaken`.
No private media, raw audio, personal source paths or source inventories
are included in the PR.

These finite reused populations support a bounded engineering repair and
review recommendation. They do not establish a general wrong-accept rate,
independent corroboration probabilities or safety for every kind of shared
content. Six difficult historical positives and two acoustic positives
still abstain. No policy was retuned after their outcomes were opened.
