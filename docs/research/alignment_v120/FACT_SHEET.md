# FACT SHEET — RhythmAlign v1.2.0 alignment system

Deliberately concise, factual, and provenance-labeled, for a senior research
review. Companion documents: `ASSET_LEDGER.md` (asset classification),
`DATA_PROVENANCE.md` (corpus contamination map), `EXPLORATORY_STUDY_INDEX.md`
(pre-v1.2.0 Astra study), `ASTRA_HANDOFF.md` (next-stage context).

## Frozen subject

- Release: **v1.2.0**; tag commit **`3a622fc33af1212178296ad9dad57ce9693eed48`**
  (lightweight tag on `main`; `main` HEAD `91bc50c0a117b38176ec93b44b9e0d1b8aaf749d`
  is a post-tag docs-only release-record commit).
- Default alignment engine: **Engine v2** (`alignment_engine_v2.py`), invoked by
  the product worker (`auto_sync.py`) with no policy overrides; ABSTAIN stops the
  export path; there is no silent fallback to the v1.1.x engine.
- Frozen decision policy (CASE A: tonal Z ≥ 5.0 and PCEN-family Z ≥ 5.6, both
  margins ≥ 1.0; CASE B: PCEN-family Z ≥ 7.0, PCEN margin ≥ 1.4, nominated onset
  corroboration Z ≥ 2.0; competitor ambiguity ratio 0.95; geometric overlap
  ≥ 30 s; single qualifying cluster required).
- Temporal-support rule (RA-1.2D1): the deciding PCEN-spectral member's net
  signed correlation at the accepted offset is decomposed into 1 s reference-time
  bins; ACCEPT survives only if the strongest bin's share ≤ **`max_top_bin_share`
  = 0.25** (`bin_width_s = 1.0`). Direction: ACCEPT → ABSTAIN only; never upgrades.
- Product semantics: whole-song placement or safe stop. Reason codes include
  `ACCEPT_DUAL_FAMILY`, `ACCEPT_PRIMARY_WITH_CORROBORATION`,
  `ABSTAIN_CONCENTRATED_EVIDENCE`, `ABSTAIN_INSUFFICIENT_TEMPORAL_SUPPORT`,
  `ABSTAIN_NO_CLUSTER_MEETS_FLOORS`, `ABSTAIN_AMBIGUOUS_CLUSTER`; UI shows
  localized abstention reasons; manual ±500 ms slider is post-accept fine-tuning.

## Current algorithm components (factual)

1. Candidate generators: four methods, three named families — tonal (chroma CENS
   first-difference correlation + 0.2× centered onset blend, the v1 hybrid),
   onset temporal (raw onset-envelope correlation), PCEN spectral (plain PCEN
   and PCEN+HPSS mel-power correlation; counted as ONE family).
2. Each method nominates its top-4 independent peaks (~1.5 s separation);
   candidates clustered greedily within 0.15 s of an evolving median
   representative; per-family scoring searches ±0.30 s of the representative.
3. Decision: family floors (CASE A / CASE B above) + minimum geometric overlap
   + single-qualifying-cluster + competitor-strength ambiguity check.
4. Ambiguity rejection: abstains if a separated competitor reaches ≥ 95 % of the
   deciding families' Z.
5. Temporal-support verification (post-decision gate): verifies the deciding
   PCEN member's evidence is time-distributed (§ above); explicit
   `applied: false` reporting when feature matrices are unavailable (no silent skip).
6. Output: one constant offset; no tempo/drift estimation; offset source may
   differ from the scoring member (HPSS-preferred candidate selection).

## Existing positive evidence (populations strictly separated)

| Population | N | Ground truth | Influenced design? | Accept | Abstain | Wrong accept | Offset error |
|---|---|---|---|---|---|---|---|
| Exact-GT semi-synthetic positives (L1–L4 corruption packages; 36 cal + 20 holdout) | 56 | construction-exact | YES (v2 calibration; D1 positive DEV/TEST) | 26 | 30 | 0 | max 0.0137 s among accepts |
| Real positives (pairing evidence) | 29 | pairing only; no timing GT except 零对话 | YES (preservation targets; D1 positive DEV) | 29 | 0 | 0 | n/a (no real GT) |
| 零对话 (`lingduihua_132`) | 1 | manual estimate +12.4 ± 0.4 s | YES (motivating case) | 1 | 0 | 0 | +12.4923 s; 0.0923 s from interval center (inside interval; NOT exact-GT error) |
| v1/v2 agreement (RA-1.2B/C/D) | 29 real + semi-synthetic | none (consistency) | YES | — | — | — | n/a — regression-consistency evidence only, not correctness |
| Owner listening | RC1/RC2 products + motivating export | qualitative, per-export | n/a | — | — | — | n/a — `OWNER_RC_PASS`, `OWNER_RC2_PASS` recorded in RA-1.2E |

All positive rows measured on the D1 engine state = the state v1.2.0 froze
(`integrated_full_positives.json`; re-run at RC per RA-1.2E §9: 55/55 accepts
with identical offsets).

## Existing negative evidence (populations strictly separated)

| Population | N | Outcome at v1.2.0 | Status |
|---|---|---|---|
| Designed wrong-song negatives (RA-1.2B/C) | 20 | all abstain (historical); safety family 24/24 incl. rows below | development |
| RA-1.2B ordinary mismatches | 10 | SAFE_ABSTAIN | development |
| Feature-similar hard negatives | 10 | SAFE_ABSTAIN | development |
| Tiled/repeated-structure ambiguity | 4 | SAFE_ABSTAIN | development |
| Astra clean wrong-song search (pre-D1, ffa6b07-era engine) | 380 directed, 22 accepted (11 unordered pairs) | discovery event; all 22 rejected post-D1 (decider concentration 0.480–1.048) | exploratory discovery; component A (42 directed, 18 accepted) = development; component B (156 directed, 4 accepted) = historical holdout, spent |
| Astra blocker `tr_lingduihua` → `tr_yanwulieche` | 1 (+reverse) | pre-D1 ACCEPT +1.462857 s (PCEN Z 13.109, margin 2.483; plain-PCEN top-1 s-bin share 0.9456); post-D1 ABSTAIN `ABSTAIN_CONCENTRATED_EVIDENCE`; product-path smoke ABSTAIN, no export | development (mechanism + regression) |
| RA-1.2D1 held-out wrong-song TEST | 156 directed | 156/156 SAFE_ABSTAIN (incl. 4 known component-B accepts) | historical holdout (spent; re-run at RC) |
| Astra room-grid search | 551, 1 accepted | accepted pair retained at v1.2.0 | exploratory discovery; accepted pair = development-inspected residual |

## Known baseline evidence (existing measurements; none rerun here)

- v1.1.x hybrid (N=76 preserved corpus, ffa6b07-era): 29 CA / 47 WA / 0 SA.
- GCC-PHAT: argmax on N=76 → 56/56 exact-insertion positives (+20 wrong accepts,
  no reject rule). RA-1.2D1 runs: 57/57 **GT-bearing** positives within tolerance
  (median |err| 0.000 s), i.e. 56/56 semi-synthetic + 零对话 within ±0.4 s manual
  interval (0.0886 s from center); wrong-song argmax lands on meaningless
  placements with peaks 0.004–0.031. No calibrated reject option exists.
- Waveform Pearson NCC: N=76 → 54 CA / 22 WA; GT-bearing 54/57; fails the
  零对话 manual anchor (−120.56 s).
- PCEN/HPSS argmax and scalar selectors (N=76): plain PCEN 45/31; HPSS-PCEN
  54/22; HPSS Z ≥ 7 → 52/0/24; HPSS margin ≥ 1.4 → 50/0/26; both → 50/0/26.
  These zero-error rows do NOT transfer: on the 380 clean wrong-song grid the
  same selectors accept 52 / 50 / 36 respectively.
- No fingerprint (landmark/learned) or DTW baseline was ever fairly reproduced.

## Known unresolved risks (status checked at v1.2.0)

1. **Residual room-grid accept** — `haiditan_ds_1` × `tr_hongzhoutian` remains
   ACCEPTED at v1.2.0 (decider PCEN+HPSS concentration 0.061, peak bin
   mid-overlap at 88 s). Not a concentration failure; owner judgment pending;
   not addressable by this safeguard.
2. **Small independent real-GT population** — exactly one manual-GT case
   (零对话, interval only). All other real positives are pairing-evidence.
3. **Semi-synthetic-to-real gap** — positives are digital insertions with
   confounded noise/processing packages; direct waveform relationship favors
   waveform baselines; no clock drift, no independent mic/room path.
4. **Threshold provenance** — `0.25` was calibrated on 18 component-A DEV wrong
   accepts vs 46 DEV true accepts (separation 0.480–1.048 vs 0.014–0.108),
   validated once on the 156-pair component-B holdout. No population calibration.
5. **Song/project reuse across stages** — component-A songs also appear in
   positive DEV; the wrong-song split (by song) and positive split (by project)
   are different partitions of overlapping source material.
6. **No truly unseen confirmatory corpus exists** — every real-audio population
   has been inspected during development or validation (see DATA_PROVENANCE).
7. **Prior art** — fingerprint + GCC-PHAT verification with confidence-based
   refusal is established (Duong et al. 2012; Six & Leman 2015); whether
   *temporally distributed support verification* specifically is established
   prior art is an open question for the next stage.

## What has NOT been demonstrated

- No claim of zero (or any bounded rate of) false accepts in general; 22/380 is
  an existence result on a pre-v1.2.0 engine, not a prevalence estimate.
- No independent GT for the 29 real positives (one manual interval only).
- No proof that `0.25` is universally calibrated; it is development-calibrated.
- No proof of novelty; no fair fingerprint/DTW baseline comparison exists.
- No demonstration of generalization beyond rhythm-game hand-cam audio.
- No calibrated probability/confidence; no selective-risk guarantee.
- No paper-worthiness verdict — explicitly deferred to the next Astra triage
  stage; this consolidation makes none.
