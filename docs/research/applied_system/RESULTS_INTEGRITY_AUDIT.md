# RESULTS-INTEGRITY-1 — Final-Result Reporting Integrity Audit

Status: **RESULTS_REPORTING_CORRECTED** (reporting-only; frozen evidence
untouched). Executed 2026-09-20 on `research/applied-system-paper`,
starting HEAD `0534ea4`.

This is a post-result REPORTING-integrity audit of the frozen final
benchmark. It is not a new experiment: no comparator was rerun, no raw
output changed, no threshold/pairing/tolerance/scoring rule moved. All
corrections below are deterministic re-derivations from the immutable raw
records, published as a versioned reporting artifact
(`results/final_benchmark_reporting_v2.json`).

## Verdict

**RESULTS_REPORTING_CORRECTED.** Every headline raw count in
`FINAL_BENCHMARK_RESULTS.md` was independently recomputed from the 200
frozen raw records and reconciled exactly. Three paper-facing reporting
defects were found and corrected (an accepted-risk denominator error, an
accepted-vs-correct-accept wording error, and a coverage-terminology
conflation), plus one confusing bootstrap presentation. The scientific
outcome is unchanged: **CLAIM_STILL_SUPPORTED_WITH_SCOPE** (see Claim
audit).

## Immutable evidence checked

- Git preflight: branch `research/applied-system-paper`, HEAD `0534ea4`,
  clean tree (only the known untracked `.zcodeignore`), upstream
  `origin/research/applied-system-paper`.
- `results/final_comparator_raw.json` — SHA-256 verified against its
  sidecar and against the hash table in `FINAL_BENCHMARK_RESULTS.md`
  (`9ae59821…`); all 200 per-record files hash-verified against the
  assembly's per-record `record_sha256` entries.
- `results/final_benchmark_results.json`, `.csv`,
  `results/final_kdenlive_results.json`,
  `results/final_comparator_environment.json` — SHA-256 sidecars all OK.
- Benchmark case manifest freeze hash verified
  (`verify_frozen_artifact`).
- Read in full: `FINAL_BENCHMARK_PROTOCOL.md`,
  `FINAL_BENCHMARK_RESULTS.md`, `HUMAN_LIGHT_STUDY_DESIGN.md`,
  `FINAL_ACQUISITION_QC.md`; aggregation/scoring/plot code
  (`final_benchmark.py`, `scoring.py`).

## Raw-count reconciliation

Recomputed independently from the raw records with the frozen
`scoring.py` contract (100 ms primary). **Exact match with the frozen
artifact at every tolerance, stratum, and system** (asserted by tests):

POSITIVE (24 primary):

| System | CORRECT_ACCEPT | WRONG_ACCEPT | ACCEPT | SAFE_ABSTAIN/NO_MATCH |
|---|---:|---:|---:|---:|
| RhythmAlign v1.2.0 | 20 | 0 | 20 | 4 |
| GCC-PHAT argmax | 10 | 14 | 24 | 0 |
| NCC argmax | 19 | 5 | 24 | 0 |
| Panako OLAF | 2 | 0 | 2 | 22 |

WRONG REFERENCE (24):

| System | WRONG_ACCEPT | refusal/NO_MATCH |
|---|---:|---:|
| RhythmAlign v1.2.0 | 0 | 24 |
| GCC-PHAT argmax | 24 | 0 |
| NCC argmax | 24 | 0 |
| Panako OLAF | 0 | 24 |

## Metric-definition audit

Four explicitly distinct metrics are now defined once and computed for
ALL FOUR systems (previously the frozen artifact computed a single
conflated "positive coverage" number, and only for the two selective
systems):

- **Acceptance coverage** = accepts / positives.
- **Correct-placement yield** = CORRECT_ACCEPT / positives.
- **Accepted risk** = WRONG_ACCEPT / accepts (positives; refusals are not
  in the denominator).
- **Wrong-reference false-accept rate** = wrong-ref WRONG_ACCEPT /
  wrong-ref cases.

## Coverage vs correct-yield correction

The frozen artifact's `positive_coverage_*` fields and the results
document's "Coverage" column reported CORRECT_ACCEPT/positives — correct
**placement yield** — under the name "coverage". For the always-output
baselines this materially misdescribes behavior: GCC-PHAT and NCC never
refuse, so their acceptance coverage is **100% (24/24)**, while their
correct-placement yields are 41.7% and 79.2%. The old column made
always-output baselines look like they "cover" less than they do, and
made the selective/always-output distinction harder to read. Corrected
table (100 ms):

| System | Acceptance coverage | Correct-placement yield | Accepted risk | Wrong-ref false-accept rate |
|---|---|---|---|---|
| RhythmAlign v1.2.0 | 20/24 = 83.3% | 20/24 = 83.3% | 0/20 = 0% | 0/24 = 0% |
| GCC-PHAT argmax | 24/24 = 100% | 10/24 = 41.7% | 14/24 = 58.3% | 24/24 = 100% |
| NCC argmax | 24/24 = 100% | 19/24 = 79.2% | 5/24 = 20.8% | 24/24 = 100% |
| Panako OLAF | 2/24 = 8.3% | 2/24 = 8.3% | 0/2 = 0% | 0/24 = 0% |

For RhythmAlign (and Panako) acceptance coverage and correct-placement
yield coincide numerically here because every accept happened to be
correct. That coincidence is now stated explicitly wherever the two
numbers appear together, and the definitions remain distinct.

## Denominator audit

Confirmed: `FINAL_BENCHMARK_RESULTS.md` reported NCC accepted risk as
**5/19**. NCC accepted 24 positives (19 correct + 5 wrong), so accepted
risk = WRONG_ACCEPT / (CORRECT_ACCEPT + WRONG_ACCEPT) = **5/24 = 20.8%**;
the 19-denominator version inflates the apparent risk by mixing the
refusal-free denominator with an accepts-only numerator. All other
denominators checked: RhythmAlign 0/20, GCC-PHAT 14/24 (58.3%), Panako
0/2 — already consistent. Raw counts unchanged. Paper-facing prose
corrected to 5/24 = 20.8% everywhere.

## Error-distribution wording audit

Confirmed: the sentence "Every accepted placement of every system lies
below 25 ms" is **semantically false**. All-produced-accept error
maxima on positives: GCC-PHAT **184.1 s**, NCC **153.4 s** (the
WRONG_ACCEPT tail; RhythmAlign 15.7 ms and Panako 21.9 ms have no wrong
accepts). What IS true: every **CORRECT_ACCEPT** placement of every
system lies below 25 ms (max 21.9 ms). The frozen
`accepted_positive_abs_error_s` field had the same naming defect — its
content is CORRECT_ACCEPT-conditional. Corrected to:

- "Every CORRECT_ACCEPT placement lies below 25 ms" (with the grid
  invariance it justifies: no accept error falls in (25 ms, 150 ms], so
  the 50/100/150 ms grid changes no outcome anywhere — this conclusion
  survives, now with a correct justification: correct accepts are all
  ≤ 21.9 ms and wrong accepts are all ≥ 0.85 s, so no tolerance on the
  grid can flip any outcome).
- All error tables state their conditioning denominator; the v2 artifact
  reports `correct_accept_conditional_abs_error_s` and
  `all_produced_accept_abs_error_s` as separate named distributions, and
  wrong-reference output magnitudes (GCC-PHAT median 64.2 s / max
  132.7 s; NCC median 104.5 s / max 155.6 s) as their own table.
- The mislabeled figure `final_accepted_offset_errors.png` (titled
  "accepted placements ... below 25 ms", actually plotting
  CORRECT_ACCEPT-only errors) is preserved; two corrected versioned
  figures were added (see Corrections made).

No other ACCEPT vs CORRECT_ACCEPT conflation remains in the results
document.

## Bootstrap audit

Confirmed the mechanism: `false_accepts_wrong_ref_ci95 = [21, 27]` for
GCC-PHAT/NCC is a source-cluster bootstrap interval on a resampled
**count** of wrong accepts. Resampling the 10 source identities with
replacement makes the per-replicate denominator variable (sources
contribute unequal numbers of dependent takes), so the interval's upper
endpoint (27) exceeds the observed fixed denominator n = 24. Internally
legitimate; paper-facing it reads as an impossible binomial CI and is
easy to misinterpret.

Correction (paper-facing): source-cluster bootstrap **RATE** intervals —
numerator / resampled denominator computed inside every replicate, so
every value lies in [0, 1] — with exact raw counts always reported
alongside. For this benchmark's deterministic wrong-reference behavior
the rate intervals are honestly degenerate: RhythmAlign and Panako
[0.0, 0.0], GCC-PHAT and NCC [1.0, 1.0] — under every source resample
the behavior never varies, which is exactly what the raw 0/24 and 24/24
counts show. The frozen count interval is preserved in the frozen
artifact and is no longer quoted in paper-facing text. Positive
correct-placement-yield uncertainty remains a correctly defined
song-level rate bootstrap (v2 recomputation reproduces the frozen
intervals exactly: RhythmAlign [0.60, 1.00], NCC [0.63, 0.95], GCC-PHAT
[0.17, 0.70], Panako [0.00, 0.19]). No interval is presented as a CI on
a fixed n=24 binomial count anywhere.

## Kdenlive audit

No projects rescored. `final_kdenlive_results.json` verified and
consistent with all prose: 10 scoring pairs; 2 CORRECT_ACCEPT (pair02
5.3 ms, pair10 0.1 ms); 8 WRONG_ACCEPT (0.85 s–149.4 s); 0 native
failures; identical counts at 50/100/150 ms; operator time from 9/10
timed runs (median 58.6 s, IQR 45.1–60.7 s, total 551.5 s) with
pair01r2's missing timer record documented and never imputed; original
pair01 V1 void (`PROCEDURE_V1_TIMELINE_ZERO_LEFT_BOUNDARY`) and
preserved as evidence only, never scored. The pair01 V2 placement
correction (00:03:00 headroom) and the XML parser v2 correction are both
described as outcome-independent implementation/procedure corrections
applied uniformly before any scoring, with original failure evidence
preserved verbatim — not hidden methodological changes. The stratum is
never pooled with the automated n=24 axis.

## Strict-repeat audit

Confirmed: plain "outcome agreement" would obscure catastrophic
placement movement. v2 reporting separates **decision-state agreement**
from **placement movement** (`placement_move_s`) and **signed error
change**, with per-comparison interpretation:

- GCC-PHAT repeat02 vs final02: ACCEPT→ACCEPT while the placement moved
  **67.2 s** (correct take → wrong take). Not repeatability.
- NCC repeat02 vs final02: ACCEPT→ACCEPT while the placement moved
  **60.5 s** (wrong take → correct take). Not repeatability.
- GCC-PHAT repeat01 vs final01: ACCEPT→ACCEPT with both placements
  **consistently wrong** (|error| ≈ 61.9 s at both takes) — agreement
  that reflects stable wrongness, not correctness.
- RhythmAlign: agreement with millisecond-scale placement movement
  (repeat01 +7.8 ms, repeat02 +14.0 ms signed error change).
- Panako: refused both repeats of takes it had accepted
  (decision-state instability).

n=2 repeats are reported as observations, never as rates; no
repeatability claim rests on them.

## Claim audit

Candidate core claim: *On fresh, independently timed recordings from
the stress-test domain, selective alignment reduces catastrophic
alignment errors relative to always-output baselines while retaining
useful positive coverage.*

**Verdict: CLAIM_STILL_SUPPORTED_WITH_SCOPE** — no weakening after
terminology correction; the corrected metrics sharpen the claim.

- Catastrophic-error reduction: RhythmAlign wrong-reference false-accept
  rate 0/24 vs 24/24 (GCC-PHAT) and 24/24 (NCC); positive wrong accepts
  0/24 vs 14/24 and 5/24. Total on this benchmark, not marginal.
- Useful positive coverage: correct-placement yield 20/24 = 83.3% (song
  bootstrap CI95 [0.60, 1.00]) with every accept correct (≤ 15.7 ms).
  Under the corrected definitions the claim holds under *either*
  reading — acceptance coverage (83.3%) or correct-placement yield
  (83.3%); they coincide numerically for RhythmAlign here. Paper-facing
  wording should say "correct-placement yield (83.3%; every accept was
  correct, so acceptance coverage coincides at 83.3%)" to preempt the
  conflation.
- Scope conditions unchanged: 10 source identities with dependent takes;
  one domain; one frozen operating point; constructed wrong-reference
  pairs; Panako at shipped thresholds; magnitudes are domain
  measurements. The claim does NOT assert zero future risk,
  calibration, population-level usability, universal superiority,
  algorithmic novelty, generalization beyond the measured domain, that
  Panako is inherently poor, or that always-output systems cannot be
  made selective with an added detector.

## Paper-scope audit

Benchmark completion is separate from paper completeness.
`HUMAN_LIGHT_STUDY_DESIGN.md` defines the recommended minimum paper as
benchmark (Section 6) + essential comparators (Section 8) + the 2-creator
× 4-task feasibility pilot (Section 10), with pillar 3 = "a measured
account of refusal cost ... so that 'safe' is never claimed without 'and
here is what safe costs'", and C-A's wording includes "refusal costs are
quantified and bounded in a creator pilot". The pilot has NOT been run.

Verdict: **BOTH_ROUTES_AVAILABLE** (details and recommendation in
`PAPER_SCOPE_AFTER_FINAL_BENCHMARK.md`). Statements that CANNOT
currently be written because refusal recovery cost is unmeasured: the
C-A pilot clause; pillar 3's "what safe costs" account; the
workflow-level secondary research question; any observed recovery
behavior after ABSTAIN or after wrong-reference discovery; any
statement that creators understand ACCEPT/ABSTAIN without training;
approximate end-to-end task time; and the framing sentence as written
("supported by a small creator feasibility pilot").

## Corrections made

1. `experiments/applied_system/final_reporting_v2.py` — new deterministic
   reporting module (pure; no media access; no reruns).
2. `results/final_benchmark_reporting_v2.json` (+ `.sha256` sidecar) —
   versioned paper-facing artifact citing the immutable raw-result SHA
   (`9ae59821…`) and the original final-results SHA (`4c6c81df…` file
   hash); contains only deterministic reporting corrections and states
   exactly what changed semantically (`corrections_vs_frozen_artifact`).
   Determinism asserted byte-for-byte by tests.
3. Two corrected-label figures, versioned new files:
   `results/figures/final_correct_accept_errors_v2.png` (renames the
   frozen plot to what it actually shows: CORRECT_ACCEPT-conditional
   errors) and `results/figures/final_produced_placement_errors_v2.png`
   (ALL produced placements, log axis, catastrophic WRONG_ACCEPT tail
   visible). The frozen figures are not overwritten.
4. `FINAL_BENCHMARK_RESULTS.md` — minimal paper-facing prose
   corrections: NCC risk 5/19 → 5/24 = 20.8%; "every accepted placement"
   → "every CORRECT_ACCEPT placement" with the all-produced distribution
   stated; "Coverage" column → correct-placement yield with an added
   acceptance-coverage column; bootstrap count interval replaced by rate
   intervals + raw counts; strict-repeat table gains the
   placement-movement reading. No count, verdict, or scope claim
   changed.
5. `experiments/applied_system/tests/test_final_reporting_v2.py` —
   reporting-semantics tests (see Tests).

## Frozen artifacts preserved

YES. `final_comparator_raw.json` and all 200 per-record files,
`final_benchmark_results.json` / `.csv`,
`final_kdenlive_results.json`, `final_comparator_environment.json`,
the benchmark manifest, and the three original figures are
byte-identical to their `0534ea4` state (hash sidecars verified after
all changes; enforced again by tests). The frozen derived artifact's
conflated field names remain exactly as frozen — corrected semantics
live only in the versioned v2 artifact.

## Remaining limitations

- 10 source identities; within-song takes are dependent; bootstrap
  intervals remain descriptive aids.
- One domain; magnitudes do not transfer automatically.
- The refusal-cost pilot is still unrun; no recovery-cost number exists.
- Panako's coverage is contract- and threshold-native (shipped OLAF
  defaults).
- Kdenlive remains a single-operator, 10-pair technical stratum;
  pair01r2 operator time is missing and never imputed.
- The degenerate [0,0]/[1,1] wrong-reference rate intervals are honest
  descriptions of deterministic behavior, not evidence of future
  behavior.

## Recommended next step

Draft the applied-system paper now from
`final_benchmark_reporting_v2.json` + the corrected results document
under the benchmark-only claim set, and decide before submission whether
to run the 2-creator pilot to unlock the original refusal-cost claims
(see `PAPER_SCOPE_AFTER_FINAL_BENCHMARK.md`).
