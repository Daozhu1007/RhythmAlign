# RA-1.2D1 design notes — architectural diagnosis and verifier design

Working notes for the temporal-support safeguard. The final report is
`docs/RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md`; this file records the
diagnosis and the design decisions with their provenance.

## 1. The blocker, reproduced

On unmodified production main (`20d48169803a0e62e4379f197a51b92f9ac6555b`),
`eng.find_offset_v2(tr_lingduihua, tr_yanwulieche)` returns:

- `status = accepted`, `offset = +1.462857 s`
- `reason_code = ACCEPT_PRIMARY_WITH_CORROBORATION` (CASE B)
- family Z: plain PCEN 13.109, PCEN+HPSS 9.956, onset 2.012 (floor 2.0),
  hybrid 5.419
- geometric overlap at the accepted offset: **148.57 s**

Identical to the archived Astra counterexample
(`experiments/alignment_research/results/counterexample_validation.json`,
branch `astra/alignment-research-wip`, commit `8b78eb1`), including the
file-entry repeatability (Astra ran it twice; this reproduction is a third
independent run on a clean checkout of main).

Astra's decomposition at that lag: **94.563 %** of the net signed plain-PCEN
correlation comes from a single ~1 s reference bin (starting 0.99846 s);
70.128 % for HPSS. Median 1 s waveform Pearson at the accepted lag is
≈ −0.0055 (max |r| 0.0923). The two tracks are different songs; the shared
content is a brief boundary event, not a whole-song alignment.

## 2. Root cause — the missing concept

Engine v2's evidence chain is:

    brief common content
        → strong global correlation peak (high Z, high margin)
        → multiple feature families agree at that lag
        → overlap-length check passes (148.57 s ≥ 30 s)
        → ACCEPT of a whole-song offset

Every step is sound *except the inference*. The families are not independent
witnesses of "the whole reference occurs here"; they are different
transformations of the **same ~1 s of shared audio**. Cross-family agreement
demonstrates that the brief event is really shared. It does not demonstrate
that matching content is **distributed across the reported overlap**.

The existing check that looks closest — `_usable_overlap_s` (CASE E,
`min_overlap_s = 30`) — measures the *geometric* overlap between the two
signals after applying the offset: where both signals could in principle be
compared. It never measures whether the *matching evidence* actually spans
that interval. Under the current policy:

    geometric overlap (where comparison is possible)
        ≠ distributed temporal support (where matching evidence exists)

The 148.57 s number is a property of file lengths and the offset; the actual
support lives in ~1 s of it. Nothing in the decision inspects the temporal
distribution of the evidence.

## 3. Why this is not a threshold-tuning problem

- Raising Z floors does not help: the blocker's PCEN Z is 13.1, far above
  any floor that real low-SNR positives could pass (RA-1.2A/B calibration
  sits at 5.0–7.0).
- Raising margin floors does not help: margins are 1.83–2.48, comfortably
  above CASE B's 1.4; the competing peaks are other coincidences, not the
  true alignment (there is no true alignment).
- Requiring one more global family vote does not help: the same 1 s event
  produces correlated evidence in every derivative of the same feature
  (Astra and RA-1.2B already established that PCEN/PCEN+HPSS must count as
  ONE family for exactly this reason; the same argument defeats "add a
  third global score").
- The existing CASE D (comparable competing cluster) misses it because the
  evidence is *concentrated*, not *ambiguous*: one dominant explanation,
  supported almost everywhere by nothing.

The missing check is a different *kind* of evidence: the temporal
distribution of the support for the proposed offset.

## 4. Verifier design space (explored)

Given candidate offset O (candidate generation is unchanged), inspect
whether local evidence independently supports O in multiple separated
temporal regions of the valid overlap.

### Design A — segmented local verification (REJECTED BY MEASUREMENT)

Tile the musically valid overlap into separated windows; per window,
compute the window's own lag distribution r_w(s) and count a window as
supporting O when it locally prefers O (z ≥ threshold, or r_w(O) ≥
margin × window max). **Measured on DEV (18 wrong accepts vs 46 true
accepts, `results/dev_calibration_analysis.json`): 0/432 parameter
configurations separate the groups.** Real music is self-similar: within
any window, same-song content correlates at many lags and structured
interference (a loud background song, arcade taps) dominates, so even
correct accepts of low-SNR positives carry near-zero local dominance in
most windows (true positives measured 0–2 supporting windows of ~9).
Consistency statistics over window-z profiles (mean/median/t-statistic/
support fractions) overlap as well. Stationary (non-delta) PCEN features
with per-window cosine: true-positive windows measure 0.03–0.07 against a
±0.03 different-song noise floor — not thresholdable. Superseded artifacts
of this design stage were trimmed from `results/` (the analysis summary is
kept as the falsification record).

### Design B — net-signed-correlation concentration (CHOSEN)

Decompose the engine's own net signed PCEN correlation at O,

    S = sum_{bands, t in valid overlap} Fm[band, t] * Fv[band, t+shift(O)],

into consecutive 1-second reference-time bins; the gate statistic is the
share of the net total carried by the single strongest bin. This is
Astra's own concentration measurement (§12.2 of the study) turned into a
decision rule — the archived blocker reproduces to 0.946 vs their 94.563%.
It asks the question at the right granularity: not "where does local
evidence peak" but "how much of the total evidence does one place supply".

- DEV wrong accepts: 0.480–1.048 (all concentrated).
- DEV true accepts: 0.014–0.108 (all distributed).
- Threshold 0.25, ≥ ~2× margin both sides.
- Verified feature = the pcen_spectral member that DECIDED the cluster
  (highest member z inside the accepted cluster). Load-bearing rule: 零对话's
  plain-PCEN member anti-correlates at its correct offset while its
  decider PCEN+HPSS measures 0.084 (must retain); conversely three dev
  wrong accepts have spread HPSS members despite concentrated PCEN
  deciders (must reject) — "any member distributed" fails in both
  directions.

### Design C — leave-one-region-out stability (superseded)

Recompute global support without each region; a distributed match survives
every single-region removal, the blocker collapses. Measures the same
quantity as Design B at higher cost; kept as an idea, not implemented in
the gate.

### Rejected directions (per task constraints and Astra §12.4)

- cropping first/last N seconds (the diagnostic that *localized* the
  blocker, not a principled fix — the shared event need not be at an edge),
- raising global Z / margin thresholds (see §3),
- requiring one additional global score (family semantics: correlated
  derivatives are not independent votes),
- replacing candidate generation with GCC-PHAT (kept as a comparison
  baseline instead).

## 5. Family semantics preserved

The gate verifies the `pcen_spectral` **member that decided the cluster**
(highest member peak z inside the accepted cluster). Plain PCEN and
PCEN+HPSS are correlated derivatives of one representation and count as
ONE family — RA-1.2B semantics; windows/bins of one member are temporal
samples of one representation, never independent family votes. The accept
stands on the decider's evidence; if that evidence is one brief event, the
accept fails the distributed-support contract whatever a correlated
sibling shows. The tonal family's chroma representation is recorded as an
observation only; onset stays a corroboration-only signal, exactly as in
RA-1.2B.

## 6. Development / test discipline

- DEV wrong-song: the 42 directed clean pairs inside component A of the
  Astra wrong-accept graph (songs: lingduihua, yanwulieche, baixiwang, drd,
  babieta, fenzhen, maodunxinli) — contains 18 of the 22 known wrong
  accepts including the blocker. All threshold decisions use only these.
- TEST wrong-song (held out, by song identity): all 156 directed pairs
  among the remaining 13 tracks — includes the 4 component-B wrong accepts
  (bai39 ↔ haiditan, bai39 ↔ chiyaoshuijiao) which double as required
  rejections, plus the archived room-grid accept
  (haiditan_ds_1 × tr_hongzhoutian, reported separately: Astra judged its
  background content unresolved).
- Positive DEV: 29 real positives (preservation targets) + calibration-split
  exact-GT positives.
- Positive TEST: holdout-split exact-GT positives (accepted ones must stay
  accepted; abstained ones are unchanged by construction — the gate can
  only downgrade accepts).

Known overlap acknowledged: component-A songs also appear in positive DEV
data, and positive TEST songs (holdout projects) are disjoint from positive
CALIBRATION songs by the existing RA-1.2C project split. No wrong-song pair
in TEST shares a song with any wrong-song pair in DEV.

## 7. Integration sketch (production, only if criteria pass)

- The gate runs inside `decide_alignment` on the PCEN features the
  generators already computed (attached by reference to
  `FamilyResult.features`); no re-decode, no second feature pass, no new
  global correlation. Measured overhead: 1.6–3.2 ms and ~100 KiB per
  accepted-candidate check.
- Accepted decisions are re-checked; a failed gate downgrades to ABSTAIN
  with a new reason code (`ABSTAIN_CONCENTRATED_EVIDENCE` /
  `ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT`) plus concentration diagnostics
  in `evidence["temporal_support"]`. Nothing can upgrade an ABSTAIN.
- New `DecisionPolicy` fields (`bin_width_s = 1.0`,
  `max_top_bin_share = 0.25`) carry the calibrated values; defaults keep
  behavior deterministic.
- `decide_from_families` (the synthetic-curve test seam) is unchanged;
  when feature matrices are absent the gate reports `"applied": false`
  instead of silently skipping.
