# ASTRA HANDOFF — RhythmAlign v1.2.0 alignment research

This is the main context document for the next Astra round. It consolidates
what a previous exploration found, what engineering changed in response, and
where the scientific boundary now sits. Repository archaeology is complete:
the full detail lives in `ASSET_LEDGER.md`, `DATA_PROVENANCE.md`,
`FACT_SHEET.md`, and `EXPLORATORY_STUDY_INDEX.md` next to this file, plus the
archived study on `astra/alignment-research-wip`.

## Research target

The alignment system of **RhythmAlign v1.2.0** (tag commit
`3a622fc33af1212178296ad9dad57ce9693eed48`): a selective, single-offset,
audio-to-audio aligner for rhythm-game hand-cam recordings. Engine v2 is the
product default. Four candidate-generator methods in three named families
(tonal hybrid, onset, PCEN spectral with plain-PCEN and PCEN+HPSS members)
nominate offset candidates; clustering plus family floors (CASE A / CASE B),
a 30 s geometric-overlap floor, single-qualifying-cluster and
competitor-ambiguity checks decide ACCEPT; a temporal-support gate verifies
that the deciding PCEN member's evidence is distributed over the overlap
(strongest 1 s bin ≤ 25 % of net signed correlation) before an ACCEPT stands;
otherwise the system ABSTAINS with a localized reason. ABSTAIN is a product
feature: the export path stops, and there is no fallback to the old engine.

## Why a second scientific review is needed

The first Astra study evaluated a **pre-v1.2.0 system** (scientific baseline
`ffa6b07`: Engine v2 implemented but non-default, without the temporal-support
safeguard). It returned `ENGINEERING_ONLY` with `RELEASE_BLOCKER_FOUND`: the
engine could accept a whole-song offset between two different songs when a
brief co-occurring event dominated the correlation evidence. Concretely, an
exhaustive 380-pair directed clean wrong-song search produced 22 accepted
pairs (11 unordered song pairs), and the minimum regression
(`tr_lingduihua` → `tr_yanwulieche`) accepted +1.462857 s where roughly one
second of shared content carried 94.563 % of the net signed plain-PCEN
correlation, with onset corroboration and a 148.57 s geometric-overlap pass.
The study's prescribed fix type — candidate-level verification of temporally
distributed matching content — was then implemented as RA-1.2D1 and shipped in
v1.2.0. The released system is therefore materially different from the one
the first study judged, and no verdict about v1.2.0 exists yet.

## Provenance chain at a glance

1. **Pre-Astra Engine v2 (RA-1.2A/B/C, on `main`).** RA-1.2A (`c036a1c`)
   discovered that the v1.1.x hybrid engine misaligned the quiet 零对话
   recording (−1.997 s against a manual +12.4 ± 0.4 s interval). RA-1.2B
   (`c8bbcd9`) built Engine v2 (multi-evidence gate, non-default,
   `NEEDS_MORE_REAL_DATA`). RA-1.2C (`ffa6b07`) hardened calibration — this
   commit is the Astra study's frozen scientific baseline; Engine v2 still
   non-default there.
2. **Astra exploratory audit (branch `astra/alignment-research-wip`).** Paused
   work preserved at `5b1fcd4` (during the RA-1.2D pre-flight, owner-approved),
   completed at `8b78eb1`. It reconstructed the algorithm from code, replayed
   all 81 preserved decisions, measured baselines and nulls, ran the 551-pair
   room-grid and post-discovery 380-pair clean-grid searches, validated the
   counterexample, and verified its blocker still applied at RA-1.2D
   (`20d4816`) via AST equality. Verdicts: `ENGINEERING_ONLY`,
   `RELEASE_BLOCKER_FOUND` — for the pre-v1.2.0 system.
3. **RA-1.2D1 engineering response (`67c8cbd`).** Reproduced the blocker on
   unmodified `20d4816` (third independent run), measured and rejected four
   alternative verifier designs on DEV data, chose the deciding-member
   1 s-bin concentration gate with `max_top_bin_share = 0.25`, validated on the
   untouched component-B holdout, and preserved all positive coverage.
4. **v1.2.0 freeze (RA-1.2E, tag `3a622fc`).** No algorithm change after D1
   (zero-diff verified at RC); frozen-state regressions re-run (tests, blocker
   abstain, 55/55 positives, 156/156 held-out abstains, 24/24 safety
   negatives, residual unchanged); owner gates passed; tag created; the
   docs-only final release record is `91bc50c` on `main`.

## What changed (RA-1.2D1, `67c8cbd`, frozen into v1.2.0)

The safeguard decomposes the deciding PCEN member's net signed correlation at
the accepted offset into 1-second reference-time bins and rejects (ACCEPT →
ABSTAIN only) when the strongest bin carries more than 25 %
(`max_top_bin_share = 0.25`) of the total, emitting
`ABSTAIN_CONCENTRATED_EVIDENCE` (plus `ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT`
for degenerate extents). The deciding member — not any sibling — is verified,
because plain PCEN and PCEN+HPSS are correlated derivatives and because real
cases exist in both directions (零对话's plain-PCEN member is concentrated at
its correct offset while its PCEN+HPSS decider is distributed at 0.084).
Development was strictly partitioned: 18 component-A wrong accepts (including
the blocker) plus 46 true accepts (29 real positives + 17 calibration-split
exact-GT positives) selected the threshold (wrong-accept decider concentration
0.480–1.048 vs true-accept 0.014–0.108); 156 held-out component-B wrong-song
pairs were never examined during design. Results: blocker and all 22 known
clean wrong accepts rejected; 156/156 held-out pairs SAFE_ABSTAIN; 55/55
previously accepted positives retained with bit-identical offsets (max
exact-GT error 0.0137 s; 零对话 retained at +12.4923 s inside its manual
interval +12.4 ± 0.4 s); gate cost < 0.1 % of decision runtime. These numbers
were re-verified from committed JSONs during this consolidation and re-run at
the release candidate (RA-1.2E §9).

## Existing evidence (strongest facts, with provenance)

Positive side, strictly separated populations:

- 56 exact-GT semi-synthetic positives (digital insertions, L1–L4 corruption
  packages): 26 accepted / 30 abstained / 0 wrong at v1.2.0; max offset error
  0.0137 s among accepts. Development-influenced corpus.
- 29 real positives (pairing evidence, no timing GT except one case): 29/29
  accepted, offsets identical to the pre-gate engine. Development-influenced.
- 零对话: manual interval +12.4 ± 0.4 s; accepted at +12.4923 s (0.0923 s from
  the interval center — a deviation from a manual estimate, not exact GT).
- Owner listening: qualitative per-export verdicts (`OWNER_RC_PASS`,
  `OWNER_RC2_PASS`), not a labeled dataset.

Negative side:

- Pre-D1 engine: 22/380 directed clean wrong-song accepts; 1/551 room-grid
  accepts; repeatable +1.462857 s blocker with 94.563 % one-second plain-PCEN
  concentration. At v1.2.0: all 22 known clean wrong accepts and the blocker
  are rejected; the held-out 156 abstain.
- The single room-grid accept (`haiditan_ds_1` × `tr_hongzhoutian`, +59.72 s)
  **remains accepted** at v1.2.0: its decider evidence is distributed
  (concentration 0.061, peak bin mid-overlap), and Astra itself declined to
  treat the pair as a strict wrong-song proof (possible background music
  unresolved). It is the documented residual risk, not a concentration failure.
- Baselines (existing measurements, never rerun for consolidation): GCC-PHAT
  recovers all GT-bearing positives (56/56 semi-synthetic; 57/57 including the
  manual-GT real case) but has no reject machinery — on wrong-song pairs its
  argmax lands on meaningless placements with tiny peaks. Simple scalar
  selectors (HPSS Z ≥ 7, margin ≥ 1.4) show zero errors on the inherited 76-case
  corpus yet accept 52 and 50 of the 380 clean wrong-song pairs respectively —
  the clearest demonstration that inherited zero-error rows do not transfer.
- No fingerprint (landmark or learned) or DTW baseline was ever fairly
  reproduced.

## Contaminated / non-confirmatory evidence

Per `DATA_PROVENANCE.md`: **no real-audio population in the repository is
eligible as fresh confirmation.** Specifically not confirmatory: the 18
component-A wrong accepts and the blocker pair (they selected the 0.25
threshold and rejected alternative designs); the 46 DEV true accepts; the
36-calibration and 20-holdout exact-GT semi-synthetic splits (the holdout was
consumed as RA-1.2D1 positive TEST and re-run at RC); the 29 real positives
(preservation targets, positive DEV); the 156 held-out wrong-song pairs
(true TEST at design time, consumed by validation and re-run at RC); the 551
room-grid and its residual case; the 20/10/10/4 designed negative families;
the 零对话 manual case (motivating case at every stage). The Astra study's
measurements additionally describe the pre-D1 engine and must never be
reported as v1.2.0 results. `POTENTIAL_FUTURE_CONFIRMATION` is empty today.

## Reusable old assets

From the archived study (branch `astra/alignment-research-wip`,
`8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e`), per `ASSET_LEDGER.md`:

- `docs/research/alignment/LITERATURE_REVIEW.md` — system-independent
  bibliography and novelty-boundary mapping: Duong, Howson & Legallais (2012)
  (fingerprint candidates + GCC-PHAT verification + confidence-based
  acquisition) is the nearest precedent for evidence-plus-refusal; Six & Leman
  (2015) for fingerprint + covariance refinement; Wang (2003), Haitsma & Kalker
  (2002), Chang et al. (2021) for fingerprint baselines; Knapp & Carter (1976)
  for GCC; Ewert et al. (2009), Müller et al. (2021) for chroma/DTW
  synchronization; Chow (1970), El-Yaniv & Wiener (2010), Geifman & El-Yaniv
  (2017), Angelopoulos et al. for reject-option/selective-risk framing; Vio &
  Andreani (2016) for searched-peak significance.
- `EXPERIMENT_PLAN.md` — reusable protocol definitions (GT strata,
  selective-risk reporting, prohibitions on iid bounds for reused sources).
- All experiment tooling: `experiments/alignment_research/` (grids, probes,
  counterexample attribution/ablation, verification) and
  `experiments/low_snr_alignment/` + `experiments/ra12d1_temporal_support/`
  packages, runnable against v1.2.0.
- Reusable-as-data: the null/probe JSONs (synthetic, system-independent), the
  source-exposure audit, and the preserved 81-case corpus as a regression
  fixture only.
- Superseded-but-historical: pre-D1 soak/memory records; the study's
  `RELEASE_BLOCKER_FOUND` recommendation (resolved by RA-1.2D1/1.2E).

## Open scientific questions (to be judged, not answered, next round)

1. Is temporally distributed evidence verification already established prior
   art in comparable audio alignment / fingerprint-verification systems, or
   does v1.2.0's concentration-gated reject rule go beyond Duong-style
   candidate verification?
2. Does v1.2.0's temporal-support mechanism constitute anything scientifically
   beyond an engineering safeguard (e.g., a measured causal feature of
   wrong-song acceptance)?
3. Is the stronger research framing selective/reject-option temporal alignment
   (coverage/risk with abstention) rather than the specific concentration
   statistic?
4. What genuinely unseen confirmatory dataset would be required (scale, label
   types, acquisition protocol) to test generalization of the released system?
5. Which baselines are necessary before any novelty claim — and can any of
   them (fingerprint verifiers, GCC-PHAT with a calibrated reject rule) match
   v1.2.0's coverage/safety on such a dataset?
6. Is the current `0.25` threshold scientifically defensible or merely
   development-calibrated (18 vs 46 DEV cases, one held-out validation)?
7. Can the residual room-grid case (`haiditan_ds_1` × `tr_hongzhoutian`,
   accepted with distributed evidence) reveal a second, non-concentration
   failure mode?

The next round should also weigh the known risks: one manual-GT case total;
semi-synthetic-to-real gap (direct-path construction); song/project reuse
across stages; and the absence of any independent confirmatory corpus.

## Exact next-role instruction

> The next Astra round should perform scientific triage, novelty-boundary
> analysis, and decisive-experiment design. It should not repeat repository
> archaeology that is already consolidated here.
