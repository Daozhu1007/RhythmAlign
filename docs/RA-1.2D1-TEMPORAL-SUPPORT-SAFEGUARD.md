# RA-1.2D1 — Temporal-Support Safeguard for Alignment Engine v2

Status: **implemented and validated** — production integration of an
additional ACCEPT gate that closes the Astra release blocker.

Verdict line at the end of this document (§19).

---

## 1. Astra blocker summary

The independent Astra scientific audit (branch `astra/alignment-research-wip`,
research commit `8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e`, study document
`docs/research/alignment/ALIGNMENT_RESEARCH_STUDY.md`) found:

- Engine v2 ACCEPTED 22 / 380 directed clean wrong-song pairs (11 unordered
  pairs, 10 distinct songs; 20 × `ACCEPT_PRIMARY_WITH_CORROBORATION`, 2 ×
  `ACCEPT_DUAL_FAMILY`), plus 1 / 551 room-recording × wrong-reference
  accepts (`haiditan_ds_1` × `tr_hongzhoutian`).
- Minimum regression: `tr_lingduihua` → `tr_yanwulieche`, repeatable ACCEPT
  at **+1.462857 s**, geometric overlap **148.57 s**.
- **94.563 %** of the net signed plain-PCEN correlation at the accepted
  offset comes from a single ~1 s reference-time bin (0.99846 s onward);
  70.128 % for PCEN+HPSS. Median 1 s waveform Pearson at the offset ≈
  −0.0055.
- Astra's §12.4 prescribed the fix type: *candidate-level verification of
  temporally distributed matching content before converting ACCEPT into a
  whole-song placement*, with a fresh development/test split. That is what
  RA-1.2D1 implements.

## 2. Exact reproduction (before any change)

On unmodified production main `20d48169803a0e62e4379f197a51b92f9ac6555b`
(`experiments/ra12d1_temporal_support/reproduce_blocker.py`, third
independent run including Astra's two):

| field | value |
|---|---|
| status | `accepted` |
| offset | `+1.462857 s` (exactly the archived value) |
| reason code | `ACCEPT_PRIMARY_WITH_CORROBORATION` (CASE B) |
| family Z | plain PCEN 13.109 · PCEN+HPSS 9.956 · onset 2.012 (floor 2.0) · hybrid 5.419 |
| evidence path | `experiments/ra12d1_temporal_support/results/blocker_reproduction.json` |
| geometric overlap | 148.57 s |
| engine wall time | 10.16 s (media decode included) |

Reproduced; no investigation of the algorithm was needed before building
the safeguard.

## 3. Root cause

Engine v2's decision chain treats cross-family agreement plus a geometric
overlap check as whole-song evidence:

    brief common content
        → strong global correlation peak
        → multiple feature families agree
        → overlap-length check passes (148.57 s ≥ 30 s)
        → ACCEPT of a whole-song offset

The flaw is the final inference. **Cross-family agreement is not
distributed temporal support.** All families are transformations of the
same ~1 s of shared audio; they are independent witnesses of the *event*,
not of the *placement*. The existing overlap check (`_usable_overlap_s`,
CASE E) measures where comparison is *geometrically possible* — a property
of file lengths and the offset — never whether matching *evidence* spans
that interval:

    geometric overlap  ≠  distributed temporal support

No threshold on Z (13.1 observed), margin (2.48 observed) or a third
global family vote can fix this: the evidence is concentrated, not weak or
ambiguous (Astra §12.3 falsified those directions; this work re-confirmed
them on the expanded corpus).

## 4. Verifier designs considered

Explored in `experiments/ra12d1_temporal_support/` (DEV data only):

1. **Segmented local verification (windowed local lag-z / local
   dominance)** — tile the overlap into separated 6–10 s windows; support O
   where the window's own lag distribution prefers O (z ≥ threshold or
   r(O) ≥ margin × window max). **Rejected by measurement**: real music is
   self-similar; within any window, same-song content correlates at many
   lags and structured interference dominates, so even correct accepts of
   low-SNR positives carry near-zero local dominance in most windows
   (DEV: per-config feasible separation **0/432** configurations; true
   positives measured 0–2 supporting windows of ~9). Documented in
   `results/dev_calibration_analysis.json` (superseded v1 design).
2. **Windowed consistency statistics** (mean/median window-z, t-statistic,
   support fractions across windows) — **rejected by measurement**: wrong
   accepts overlapped or exceeded true accepts on every statistic
   (e.g. median window-z mean: wrong 0.60 vs true 0.24).
3. **Stationary (non-delta) PCEN texture features with absolute per-window
   cosine** — probed on real positives: per-window cosine at the true
   offset (0.03–0.07) sits barely above the different-song noise floor
   (±0.03); not thresholdable per window.
4. **Leave-one-region-out stability** (recompute global support without
   each region) — correct in principle but superseded by design 5, which
   measures the same quantity directly and cheaply.
5. **Net-signed-correlation concentration at the proposed offset (CHOSEN)**
   — decompose the engine's own net signed PCEN correlation at O into
   1-second reference-time bins; the single strongest bin's share of the
   net total is the gate statistic. This is Astra's own concentration
   measurement turned into a decision rule (reproduces the archived 94.6 %
   to 0.946).

## 5. Chosen verifier

Given an already-proposed candidate offset O (candidate generation is
unchanged), the deciding evidence is verified as follows:

- **Which feature**: the `pcen_spectral` **member that actually decided
  the cluster** (highest member peak z inside the accepted cluster; plain
  PCEN and PCEN+HPSS are correlated derivatives and count as ONE family —
  RA-1.2B semantics preserved). The accept stands on that member's
  evidence; if it is one brief event, the accept fails the
  distributed-support contract whatever a correlated sibling shows. This
  rule is load-bearing: 零对话's plain-PCEN member anti-correlates at its
  correct offset (tap-dominated), while its decider PCEN+HPSS measures
  0.084 (distributed); conversely, three dev wrong accepts have a
  *spread* HPSS member despite a concentrated PCEN decider — so "any
  member distributed" is unsafe in both directions.
- **Statistic**: decompose `S = Σ_{bands,t} Fm·Fv` at O over the valid
  overlap into 1 s bins; `concentration = max_i S_i / Σ_i S_i`.
- **Gate**: ACCEPT survives only if `concentration ≤ 0.25`
  (`DecisionPolicy.max_top_bin_share`; bin width `bin_width_s = 1.0`).
- **Direction**: the gate can only downgrade ACCEPT → ABSTAIN; it never
  upgrades anything.

Calibration (DEV only — 18 component-A wrong accepts incl. the blocker +
46 dev true accepts = 29 real positives + 17 calibration-split exact-GT
positives):

| group | deciding-member concentration |
|---|---|
| known wrong accepts (n=18) | 0.480 – 1.048 |
| true accepts (n=46) | 0.014 – 0.108 |

Threshold 0.25 keeps ≥ ~2× margin on both sides. DEV outcome with the
final rule: **18/18 wrong accepts rejected, 46/46 true accepts retained**.

## 6. Development / test split

Split by song identity (the Astra wrong-accept graph has two disconnected
components, which makes a clean partition possible):

- **DEV wrong-song**: all directed clean pairs inside component A —
  songs {lingduihua, yanwulieche, baixiwang, drd, babieta, fenzhen,
  maodunxinli} — 42 pairs, of which 18 are known wrong accepts (incl. the
  blocker). All threshold/design decisions used only these.
- **TEST wrong-song (held out)**: all 156 directed pairs among the
  remaining 13 tracks — includes the 4 component-B known wrong accepts
  (bai39 ↔ haiditan, bai39 ↔ chiyaoshuijiao) — plus the archived
  room-grid accept. Never examined during design.
- **Positive DEV**: 29 real positives (preservation targets) +
  calibration-split exact-GT positives.
- **Positive TEST**: holdout-split exact-GT positives (the existing
  RA-1.2C project-level split).

Acknowledged overlap: component-A songs also appear in positive DEV data
(as true positives); no wrong-song TEST pair shares a song with any
wrong-song DEV pair.

## 7. Wrong-song results

| family | n | WRONG_ACCEPT | SAFE_ABSTAIN |
|---|---|---|---|
| DEV wrong accepts (known, incl. blocker) | 18 | 0 | 18 |
| Held-out clean wrong-song pairs (TEST) | 156 | 0 | 156 |
| — of which known component-B Astra accepts | 4 | 0 | 4 (measured concentration 0.672 / 0.836) |
| Archived blocker (production path) | 1 | 0 | 1 (concentration 0.946) |
| RA-1.2B ordinary mismatches | 10 | 0 | 10 |
| RA-1.2C hard negatives (cal+holdout) | 10 | 0 | 10 |
| Tiled ambiguity (cal+holdout) | 4 | 0 | 4 |
| Room-grid archived accept (see §11) | 1 | 1 | 0 |

Sources: `results/eval_wrong_song_test.json`, `results/eval_negatives.json`,
`results/dev_concentration.json`.

## 8. Positive coverage

Frozen v2 baseline (RA-1.2D): 26/56 exact-GT semi-synthetic positives
accepted, 29/29 real positives accepted, 30/56 + 0 abstained. History is
not rewritten: the safeguard's job is to preserve the 55 accepted positives
and change nothing else.

End-to-end with the **integrated production engine** (all 85 cases re-run
through `eng.decide_alignment`; `results/integrated_full_positives.json`):

| group | CORRECT_ACCEPT | SAFE_ABSTAIN | WRONG_ACCEPT |
|---|---|---|---|
| 56 exact-GT semi-synthetic (cal+holdout) | 26 (identical cases to v2) | 30 (identical) | 0 |
| 29 real positives (incl. 零对话 low-SNR) | 29 | 0 | 0 |

- Previously accepted positives retained: **55/55 (100 %)**.
- Previously abstained positives newly accepted: **0** (the gate cannot
  upgrade; by construction and verified).
- Newly introduced false abstains: **0**.
- 零对话 (`lingduihua_132`, low-SNR): retained at **+12.4923 s** against
  its independently established manual estimate **+12.4 ± 0.4 s** —
  deviation from the interval center ≈ 0.0923 s, result inside the
  interval. That manual estimate is not exact GT; the deciding-member
  rule exists precisely to preserve this case.

## 9. Exact-GT results

26 semi-synthetic correct accepts re-measured end-to-end: all within the
0.15 s tolerance; max |offset error| among the exact-GT semi-synthetic
accepts **0.0137 s** (`ss_cal_001`).

Separately, the one manual-GT case, 零对话: accepted at +12.4923 s; its
independently established manual estimate is +12.4 ± 0.4 s, so the
deviation from the interval center is ≈ 0.0923 s and the result lies
inside the interval. The 0.0923 s figure is a deviation from a manual
estimate, **not** an exact-GT error, and is not pooled with the
semi-synthetic metric. (Population split corrected in RA-1.2E; an
earlier revision of this section reported 0.0923 s as a
cross-population "max GT error".)

Accepted offsets are bit-identical to the frozen v2 baseline (the gate
changes decisions, never placements).

## 10. GCC-PHAT comparison (`results/eval_baselines.json`)

- **Coverage**: GCC-PHAT (7 350 Hz analysis rate, per-lag Pearson, 30 s
  minimum overlap; same construction as the Astra study) places
  **57/57** GT-bearing positives within tolerance (median |error|
  0.000 s). Waveform NCC: 54/57. This confirms Astra's observation.
- **Safety**: GCC-PHAT is a point estimator — it has no accept/reject
  machinery. On wrong-song pairs its argmax lands on meaningless
  placements (blocker: +2.96 s; component-B: ±12.28 s / ±30.9 s) with
  near-zero peak values (peak NCC 0.024–0.031). Turning that into a
  decision would require exactly the kind of calibrated distribution
  analysis built here, on data GCC-PHAT has never been calibrated against.
- **Conclusion**: not a replacement for Engine v2 (no decision semantics,
  no low-SNR robustness evidence, no abstention UX); retained as the
  established comparison baseline. Engine v2 + temporal-support gate
  provides both coverage (55 retained accepts) and safety (all
  concentrated wrong-song accepts rejected).

## 11. Counterexample analysis before / after

- Blocker `tr_lingduihua` → `tr_yanwulieche`: before — ACCEPT +1.462857 s
  (CASE B, overlap 148.57 s, concentration **0.946**); after — ABSTAIN
  `ABSTAIN_CONCENTRATED_EVIDENCE`, evidence names the verified member and
  the dominant bin (`results/integrated_validation.json`). Reverse
  direction: same.
- All 22 clean Astra wrong accepts: rejected; measured decider-member
  concentration 0.480–1.048 — every one is a concentrated-evidence
  failure, i.e. the guard's causal target (H).
- **Room-grid archived accept** (`haiditan_ds_1` × `tr_hongzhoutian`,
  +59.72 s, CASE A): **still accepted**. Its decider member (PCEN+HPSS)
  measures concentration **0.061** with 40 effective bins and the peak bin
  at 88 s — mid-overlap, not a boundary event. Astra itself declined to
  treat this pair as a wrong-song proof ("possible unrelated background
  music is unresolved; not needed as a strict no-shared-content proof").
  The verifier's verdict is that the +59.72 s placement carries genuinely
  distributed matching content — plausibly the arcade background really
  contained that song. **Residual risk**: if the owner judges this pair
  wrong regardless, closing it would require evidence beyond the
  concentrated-evidence failure mode (e.g. a content-identity review of
  that recording); it is not addressable by this safeguard without
  sacrificing the 55 retained positives.

## 12. Runtime / memory

- Gate cost (blocker geometry, 149 bins): **1.6–3.2 ms** wall,
  **100.5 KiB** peak Python-side allocation (tracemalloc), against a
  3.3–5.7 s `decide_alignment` — < 0.1 % relative overhead.
- The gate reuses the PCEN features the generators already computed
  (attached to `FamilyResult.features` **by reference**); no re-decode, no
  second feature pass, no new global correlation. The extra allocation is
  the 1-D product array plus bins.
- Full 85-case positive corpus through the integrated engine: 319.6 s
  total (≈ 3.8 s/case), within the RA-1.2D runtime envelope
  (`results/integrated_full_positives.json`).

## 13. Production changes

- `alignment_engine_v2.py`
  - `FamilyResult.features`: optional reference to the generator's
    (video, music) feature matrices.
  - `DecisionPolicy.bin_width_s = 1.0`, `DecisionPolicy.max_top_bin_share
    = 0.25` (calibrated; provenance in comments).
  - New reason codes `ABSTAIN_CONCENTRATED_EVIDENCE`,
    `ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT` + presentation strings.
  - `_concentration_profile`, `_deciding_pcen_method`,
    `_apply_temporal_support`; wired into `decide_alignment` after
    `decide_from_families`. `decide_from_families` itself is unchanged —
    the synthetic-curve test seam keeps its contract, and the gate
    explicitly reports `"applied": false` when feature matrices are
    unavailable instead of silently skipping.
  - PCEN generators attach their already-computed features.
- `ui_main.py`: new reason codes mapped to locale keys (unknown codes
  already fall back safely).
- `locales/en_US.json`, `locales/zh_CN.json`: two new abstain-reason
  strings each.
- Candidate generation, ACCEPT/ABSTAIN product semantics and the
  no-silent-fallback-to-v1 rule are untouched.

## 14. Tests

`tests/test_ra12d1_temporal_support.py` (11 tests; full suite **76
passed**):

- concentrated-evidence wrong-song rejection (real pipeline PCEN features,
  boundary + middle event; media-independent stand-in for the archived
  blocker; asserts the dominant bin lands at the event);
- same fixture passes with `max_top_bin_share = 1.01` (causal mechanism
  proof);
- distributed true-match acceptance end-to-end with support evidence;
- one-local-event-only rejection;
- low-SNR CASE B acceptance retained (spirit of the 零对话 regression);
- insufficient temporal extent → `ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT`;
- decide_from_families seam does not gate (pre-RA-1.2D1 contract);
- legacy hard negatives (no-signal, wrong-song) remain abstained;
- existing CASE A / CASE B policy tests unchanged and green.

## 15. Remaining risks

1. The room-grid pair (§11) — accepted with distributed evidence; owner
   decision required if it must abstain for non-concentration reasons.
2. A different wrong-song mechanism *not* based on concentration (e.g.
   two genuinely similar songs) would not be caught by this gate; the
   156-pair held-out sweep found none, but the corpus is finite.
3. DEV/TEST positive overlap: component-A songs appear in positive DEV
   data; the positive TEST split is disjoint at project level, but the
   wrong-song split (song identity) and the positive split (project) are
   different partitions by necessity of the available data.
4. The gate verifies the deciding PCEN member only; a hypothetical accept
   whose concentrated evidence lived exclusively in the tonal family
   would pass the gate. No such case exists in any corpus measured
   (chroma profiles on the measured accepts are diffuse or negative-sum),
   and CASE A additionally requires tonal+pcen agreement.
5. Semi-synthetic positives are constructions; the 29 real positives are
   pairing-evidence based (only 零对话 has manual-frame GT).

## 16. Exact files changed

Production:
- `alignment_engine_v2.py` (modified)
- `ui_main.py` (modified)
- `locales/en_US.json`, `locales/zh_CN.json` (modified)
- `tests/test_ra12d1_temporal_support.py` (new)
- `docs/RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md` (new)

Research/experiment package (development data only, no production impact):
- `experiments/ra12d1_temporal_support/reproduce_blocker.py`
- `experiments/ra12d1_temporal_support/common.py`
- `experiments/ra12d1_temporal_support/temporal_support.py`
- `experiments/ra12d1_temporal_support/calibrate_dev.py`
- `experiments/ra12d1_temporal_support/evaluate.py`
- `experiments/ra12d1_temporal_support/prepare.py`
- `experiments/ra12d1_temporal_support/validate_integration.py`
- `experiments/ra12d1_temporal_support/validate_full_positives.py`
- `experiments/ra12d1_temporal_support/DESIGN_NOTES.md`
- `experiments/ra12d1_temporal_support/results/*.json` (10 committed
  outputs; scratch caches live under gitignored `/results/ra12d1_cache/`)

## 17. Validation

- Blocker reproduced on unmodified main before any change (§2).
- Feature-reuse equivalence: family curves rebuilt from cached features
  are bit-identical to `find_offset_v2` (`results/equivalence_check.json`).
- DEV: 18/18 wrong accepts rejected, 46/46 true accepts retained.
- Held-out TEST: 156/156 clean wrong-song pairs SAFE_ABSTAIN (incl. the 4
  known component-B accepts), blocker rejected, no new false-accept
  family.
- Safety families unchanged: 10 RA-1.2B mismatches, 10 hard negatives,
  4 tiled — all SAFE_ABSTAIN.
- Full positive corpus through the integrated engine: 55/55 previously
  accepted positives retained, 0 new false abstains; max |offset error|
  among exact-GT semi-synthetic accepts **0.0137 s**; 零对话 (manual GT
  +12.4 ± 0.4 s) retained at +12.4923 s, inside the interval
  (deviation from center ≈ 0.0923 s; not exact GT).
- A/B causal check: blocker accepted at +1.462857 with
  `max_top_bin_share = 1.01`, abstained with 0.25 — identical decisions,
  the gate is the only difference.
- Full pytest suite: 76 passed (65 pre-existing + 11 new).

## 18. Final Git status

Recorded at commit time (see commit message for SHA). Branch `main`;
Astra research branch `astra/alignment-research-wip` remains unmerged at
research commit `8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e` (not pushed).

## 19. Verdict

All acceptance criteria A–H are met: the archived counterexample is
rejected through the production path (A); all 22 known clean Astra
wrong-song counterexamples are rejected (B); 156 held-out wrong-song pairs
show no new false-accept family (C); hard-negative / mismatch / tiled
safety is unchanged (D); real positive coverage is fully preserved
(29/29) (E); exact-GT offsets are unchanged and correct (F); the result is
the opposite of blanket abstention — 55/55 previously accepted positives
remain accepted (G); and the safeguard is the direct, calibrated
measurement of the discovered concentrated-evidence failure mode (H).

READY_FOR_RA12E
