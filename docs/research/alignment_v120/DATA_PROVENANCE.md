# DATA PROVENANCE MAP — alignment corpora and case families vs RhythmAlign v1.2.0

Question this document answers:

> Which examples can still be used for future exploratory work, and which
> examples are no longer valid as final confirmation because the method was
> designed after looking at them?

Labels used:

- `DISCOVERY` — exploratory/hypothesis-generation use; fine for future exploratory work.
- `DEVELOPMENT` — influenced design or tuning (Engine v2 thresholds, or the RA-1.2D1 temporal-support safeguard); never confirmatory.
- `HISTORICAL_HOLDOUT` — was held out at some stage, but has since been consumed by development/validation and re-inspected; no longer eligible as fresh confirmation.
- `POTENTIAL_FUTURE_CONFIRMATION` — genuinely unseen, uncontaminated, and eligible to confirm the released method.
- `NOT_ELIGIBLE_FOR_CONFIRMATION` — cannot be used as confirmation at all (superset of the above restrictions).

Conservative rule applied throughout: any real-audio population that was
inspected during development or validation, at any stage, is not eligible as
fresh confirmation. **No clean holdout is manufactured where none exists.**

Corpus context (from the Astra audit, `experiments/alignment_research/results/audit.json`
on `astra/alignment-research-wip`): the source set is **20 projects / 29
recordings**; multiple recordings share projects; tracks/backgrounds are reused
across noise levels and negative pairings; every recording in the RA-1.2C
"historical holdout" had appeared in RA-1.2B development results.

---

## Positives

| Population | N | Ground truth | Status | Reason |
|---|---|---|---|---|
| Exact-GT semi-synthetic positives — calibration split (L1–L4 corruption packages) | 36 | construction-exact offset | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Used for Engine v2 calibration (RA-1.2B/C) and as RA-1.2D1 positive DEV (17 of them entered the 0.25 calibration). |
| Exact-GT semi-synthetic positives — holdout split | 20 | construction-exact offset | `HISTORICAL_HOLDOUT` (spent) → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Held out at RA-1.2C, then used as RA-1.2D1 positive TEST and re-run at RC. Still valid as a regression fixture. |
| Real positive recordings (pairing-evidence) | 29 | pairing evidence; only 零对话 has a manual interval | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Preservation targets; RA-1.2D1 positive DEV; consulted since RA-1.2B. v1–v2 agreement is consistency evidence only. |
| 零对话 (`lingduihua_132`) | 1 | manual estimate +12.4 ± 0.4 s | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | The motivating case of RA-1.2A; consulted at every stage; the deciding-member rule exists specifically to preserve it (its plain-PCEN member is concentrated/anti-correlated at the correct offset). |

## Negatives

| Population | N | Status | Reason |
|---|---|---|---|
| Designed wrong-song negatives (RA-1.2B/C era) | 20 | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | In corpus.json; consulted throughout. |
| RA-1.2B ordinary mismatches | 10 | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | RA-1.2D1 safety family. |
| Feature-similar hard negatives (RA-1.2C) | 10 | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Feature-similar but not worst-case-searched; RA-1.2D1 safety family. |
| Tiled/repeated-structure ambiguity cases | 4 | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Uniqueness-contract cases; RA-1.2D1 safety family. |
| Astra 551 room-grid pairs (29 recordings × 19 other-project references) | 551 (1 accepted) | `DISCOVERY`; accepted pair → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Exploratory adversarial search on already-exposed source identities. The single accepted pair `haiditan_ds_1` × `tr_hongzhoutian` (+59.7217 s) became a RA-1.2D1 TEST row and the documented residual; repeatedly inspected since. |
| Astra 380 directed clean wrong-song pairs — component A (songs: lingduihua, yanwulieche, baixiwang, drd, babieta, fenzhen, maodunxinli) | 42 directed (18 accepted) | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | The 18 known wrong accepts (incl. the blocker) are the DEV data that selected `max_top_bin_share = 0.25` and rejected designs 1–3. |
| Astra 380 directed clean wrong-song pairs — component B (13 remaining tracks) | 156 directed (4 accepted) | `HISTORICAL_HOLDOUT` (spent) → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Never examined during RA-1.2D1 design (true held-out TEST at the time); consumed by D1 validation (156/156 SAFE_ABSTAIN) and re-run at RC. Only 4 known accepts; not a population estimate. |
| Archived blocker pair `tr_lingduihua` → `tr_yanwulieche` (+ reverse) | 2 directed | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Mechanism-identification evidence; minimum regression; reproduced at `20d4816`; the A/B causal test case. |
| RA-1.2D1 DEV wrong accepts (component A accepted set incl. blocker) | 18 | `DEVELOPMENT` → `NOT_ELIGIBLE_FOR_CONFIRMATION` | Threshold-selection data (decider concentration 0.480–1.048). |
| Residual room-grid case `haiditan_ds_1` × `tr_hongzhoutian` | 1 | `NOT_ELIGIBLE_FOR_CONFIRMATION` | Accepted at v1.2.0 with distributed decider evidence (concentration 0.061, peak bin mid-overlap at 88 s); Astra itself declined to treat it as a strict wrong-song proof (possible background music unresolved). Owner judgment open; development-inspected. |

## Synthetic probes (system-independent constructions)

| Population | N | Status | Note |
|---|---|---|---|
| Feature-space nulls | 384 draws | `DISCOVERY` | Reusable for exploratory null work; shared seeds across cells; not independent audio. |
| Audio nulls (Gaussian / Gaussian+taps) | 36 | `DISCOVERY` | Reused deterministic reference; not 36 independent songs. |
| Partial-support cases (1/3/8/20/40 s support) | 5 | `DISCOVERY` | Guard-semantics counterexamples (8 s support accepted). |
| Repetition cases (disjoint repeats; close replicas) | 7 | `DISCOVERY` | Unique-placement contract probes. |
| Decision-seam curve constructions | 3 | `DISCOVERY` | Synthetic curves, not natural audio. |

## Baseline measurements (existing; not rerun during consolidation)

| Population | Status | Content |
|---|---|---|
| N=76 preserved-corpus baselines (Astra, ffa6b07-era) | `DEVELOPMENT` | v1 hybrid 29/47/0; GCC-PHAT argmax 56/56 positives (+20 wrong accepts); NCC 54/22; HPSS argmax 54/22; scalar selectors; frozen v2 26/0/50. |
| RA-1.2D1 baseline runs (`eval_baselines.json`) | `DEVELOPMENT` (consumed validation) | GCC-PHAT 57/57 GT-bearing positives (56/56 semi-synthetic + 零对话 within ±0.4 s manual interval); NCC 54/57; 28 real positives GT-less (`null`); wrong-song argmax peaks 0.004–0.031. |

## What may still be used, and for what

- **Future exploratory work:** all `DISCOVERY` populations, all tooling
  (ASSET_LEDGER rows marked REUSE), and the development corpora as regression
  fixtures (replay of archived decisions, mechanism demonstrations) — provided
  results are labeled as development/exploratory, never as confirmation.
- **Final confirmation:** nothing currently in the repository qualifies.
  Every real-audio population is `DEVELOPMENT` or a spent `HISTORICAL_HOLDOUT`;
  `POTENTIAL_FUTURE_CONFIRMATION` is **empty today**. What would qualify is a
  source-disjoint, blinded acquisition on previously unseen songs/projects with
  independent timing labels, acquired after the freeze of the evaluated method
  (the shape proposed in Astra study §18). Deciding the exact design belongs to
  the next scientific-triage stage, not this consolidation.
