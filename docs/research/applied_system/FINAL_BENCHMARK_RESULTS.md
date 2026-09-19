# Final Benchmark Results

Status: **FINAL_BENCHMARK_COMPLETE** — the one confirmatory run of the
frozen protocol, executed 2026-09-20 on branch
`research/applied-system-paper` (starting HEAD `68a3ae2`).

Everything in this document is **FINAL CONFIRMATORY EVIDENCE**. Pilot
(`FRESH_PILOT_RESULTS.md`), shakedown (`BENCHMARK_SHAKEDOWN.md`), and all
historical development numbers are development evidence only and appear
nowhere in the counts below. FINAL DATA WAS NOT USED TO CHANGE THE FROZEN
PROTOCOL: no threshold, pairing, population, scoring rule, system
configuration, or exclusion was altered after acquisition; the only
post-freeze corrections are the two outcome-independent, evidence-
preserved items documented under "Post-freeze corrections".

## Final status

- Automated benchmark: 24/24 primary positives evaluated; 24/24
  wrong-reference pairs evaluated; 2/2 strict repeats evaluated
  separately; 200/200 system records produced; 0 runner errors.
- Kdenlive owner-operated technical stratum: 10/10 valid scoring runs
  scored from saved project XML.
- Verdict: **CLAIM_SUPPORTED_WITH_SCOPE** (see Claim audit).

## Frozen protocol confirmation

Authority chain, all verified at execution time by canonical-hash
recomputation: `FINAL_BENCHMARK_PROTOCOL.md` (frozen before collection) →
`final_source_freeze.json` → `final_acquisition_manifest.json`
(`7e1c1d54…`) → `results/final_acquisition_qc.json` (`962455b6…`,
`FINAL_QC_PASS`, 26/26 GT_VALID) → `kdenlive/kdenlive_pair_freeze.json`
(`2edd734b…`, KDENLIVE-SELECT-V1) → `kdenlive_run_policy.json`
(`KDENLIVE_RUN_POLICY_V2`, procedure `KDENLIVE-PLACEMENT-V2`, headroom
180 s) → pre-scoring owner-run freeze (`b7a557f4…`) → benchmark case
manifest (`459e9ba5…`, frozen before the first automated run). Frozen
scoring machinery: `experiments/applied_system/scoring.py` (unchanged)
and the committed frozen runners; production subject verified unchanged
since tag `v1.2.0` (`3a622fc3…`) — `git diff` from the tag touches only
`experiments/`, `docs/`, `tests/`, and `.gitattributes`.

The automated benchmark was executed only after the owner Kdenlive run
was verified complete (10/10 saved projects + timing log) and the
pre-scoring owner-run evidence freeze existed — the seal held.

## Final data provenance

26 raw owner recordings (final01–final24, repeat01–repeat02), 3 sessions,
2 rooms (ROOM_A/ROOM_B), 2 recording devices (D1/D2), owner-attested
condition execution; 26/26 GT_VALID under the frozen marker contract;
trimmed inputs hash-identical to the QC freeze; every system consumed
byte-identical trimmed WAVs and reference WAVs (hash-verified per record
at run time). No copyrighted media is committed.

## Systems and versions

| System | Frozen identity | Native semantics |
|---|---|---|
| RhythmAlign | v1.2.0, commit `3a622fc3…` | ACCEPT / ABSTAIN |
| GCC-PHAT | `gcc_phat_argmax_v1` | ALWAYS_OUTPUT |
| NCC | `ncc_argmax_v1` | ALWAYS_OUTPUT |
| Panako | OLAF, source `e4b0e1db…`, jar `77c56eab…` (verified at run) | ACCEPT / NO_MATCH / ERROR |
| Kdenlive | 26.08.1, exe `4ba2e9c5…` (verified at prep) | owner-operated native alignment, placement read from project XML |

Full environment: `results/final_comparator_environment.json`.

## Primary positive results (24 EXACT_GT positives, 100 ms)

| System | CORRECT_ACCEPT | WRONG_ACCEPT | SAFE_ABSTAIN/NO_MATCH | Coverage |
|---|---:|---:|---:|---:|
| RhythmAlign v1.2.0 | **20** | 0 | 4 (abstain) | 83.3% |
| NCC argmax | 19 | 5 | 0 (never refuses) | 79.2% |
| GCC-PHAT argmax | 10 | 14 | 0 (never refuses) | 41.7% |
| Panako OLAF | 2 | 0 | 22 (no match) | 8.3% |

RhythmAlign's 4 abstentions are final08 (ORDINARY), final18
(INTERFERENCE), final20 (INTERFERENCE), final24 (DEVICE_VARIATION) — all
four on the two deliberately repetitive sources S08 Cryptarithm and S10
Straight into the lights. Refusal, not confident error, is where its
coverage ends.

## Wrong-reference results (24 NO_MATCH pairs, frozen rotation S(i mod 10)+1)

| System | WRONG_ACCEPT | SAFE_ABSTAIN/NO_MATCH |
|---|---:|---:|
| RhythmAlign v1.2.0 | **0** | 24 |
| Panako OLAF | 0 | 24 |
| GCC-PHAT argmax | 24 | 0 |
| NCC argmax | 24 | 0 |

The always-output baselines produced a catastrophic wrong placement on
**every** wrong-song pair — the headline failure mode of the frozen
semantics: an argmax must output something, and with a wrong reference it
outputs confident nonsense. Output magnitudes: GCC-PHAT median |offset|
64.2 s (IQR 43.1–74.2, max 132.7); NCC median 104.5 s (IQR 62.8–149.2,
max 155.6). These are the baselines' native semantics, not
implementation bugs.

## Risk / coverage results

- Selective-risk position of RhythmAlign: 20/24 coverage with 0 wrong
  accepts anywhere (positives and wrong-references). Every refused case
  is a safe refusal; every accepted case is correct at 100 ms.
- Panako is equally safe (0 false accepts) but its coverage on this task
  contract collapses to 2/24 — fingerprint occurrence matching does not
  deliver whole-song placement offsets for degraded 60 s room queries at
  its shipped thresholds. It does NOT dominate RhythmAlign.
- Accepted-positive risk (wrong accepts among accepts): RhythmAlign 0/20,
  GCC-PHAT 14/24, NCC 5/19, Panako 0/2 (denominators differ by refusal
  behavior; shown raw, not as rates).

## Condition-level results (positives, raw counts; denominators in parentheses)

| Condition (n) | RhythmAlign | NCC | GCC-PHAT | Panako |
|---|---|---|---|---|
| ORDINARY (10) | 9 CA, 1 AB | 9 CA, 1 WA | 5 CA, 5 WA | 2 CA, 8 NM |
| LOW_LEVEL (3) | 3 CA | 3 CA | 2 CA, 1 WA | 3 NM |
| TAP_DOMINANT (3) | 3 CA | 3 CA | 2 CA, 1 WA | 3 NM |
| INTERFERENCE (4) | 2 CA, 2 AB | 1 CA, 3 WA | 4 WA | 4 NM |
| PARTIAL (2) | 2 CA | 2 CA | 1 CA, 1 WA | 2 NM |
| DEVICE_VARIATION (2) | 1 CA, 1 AB | 1 CA, 1 WA | 2 WA | 2 NM |

CA = CORRECT_ACCEPT, WA = WRONG_ACCEPT, AB = abstain, NM = no match.
Denominators are small; no subgroup inference is drawn.

## Offset-error results (accepted positives, 100 ms)

| System | n | median | IQR | max |
|---|---:|---:|---|---:|
| GCC-PHAT (correct cases) | 10 | 0.22 ms | 0.20–0.30 ms | 3.8 ms |
| NCC (correct cases) | 19 | 3.8 ms | 3.7–3.9 ms | 3.9 ms |
| RhythmAlign | 20 | 7.9 ms | 5.5–10.6 ms | 15.7 ms |
| Panako (correct cases) | 2 | 15.1 ms | 11.7–18.5 ms | 21.9 ms |

Every accepted placement of every system lies below 25 ms — the 50/100/
150 ms tolerance grid changes **no** outcome anywhere in the benchmark.
Separation between systems is decided entirely by *what they refuse*,
not by placement precision.

Kdenlive stratum (separate, n=10): 2 produced placements correct
(5.3 ms, 0.1 ms); 8 wrong placements with errors 0.85 s to 149.4 s
(median 2.97 s, IQR 1.12–69.7 s, max 149.4 s across produced placements).

## Source-level aggregation

The source identity is the independence unit; the 24 takes are 10 songs
and are NOT independent observations. Per-source RhythmAlign outcome
(CORRECT_ACCEPT counts out of that song's primary takes):

S01 3/3, S02 3/3, S03 2/2, S04 2/2, S05 2/2, S06 2/2, S07 2/2,
**S08 0/2 (both abstained)**, S09 3/3, **S10 1/3 (two abstained)**.
RhythmAlign refused every wrong-reference pair from every source.
Song-level bootstrap (resampling the 10 source identities, 10,000
replicates, seed 20260920; descriptive only): RhythmAlign coverage
CI95 [0.60, 1.00]; NCC [0.63, 0.95]; GCC-PHAT [0.17, 0.70]; Panako
[0.00, 0.19]. Wrong-reference false accepts: RhythmAlign and Panako
[0, 0]; GCC-PHAT and NCC [21, 27]. No claim of n=24 independent songs
is made anywhere.

## Strict-repeat reliability (reported separately; never in primary counts)

| Comparison | System | Outcome agreement | Signed error change vs GT |
|---|---|---|---:|
| repeat01 vs final01 | RhythmAlign | yes | +7.8 ms |
| repeat01 vs final01 | NCC | yes | +2.7 ms |
| repeat01 vs final01 | GCC-PHAT | yes | −0.04 ms |
| repeat01 vs final01 | Panako | **no** (accept → no match) | — |
| repeat02 vs final02 | RhythmAlign | yes | +14.0 ms |
| repeat02 vs final02 | NCC | yes (both ACCEPT) | **−60.33 s** |
| repeat02 vs final02 | GCC-PHAT | yes (both ACCEPT) | **−67.07 s** |
| repeat02 vs final02 | Panako | **no** (accept → no match) | — |

The repeats expose a second, independent instability of the
always-output baselines: on two near-identical recordings of the same
song their placements differ by about a minute. "Outcome agreement"
(here, ACCEPT = ACCEPT) hides that both outputs can be wrong; the signed
error change is the honest statistic. RhythmAlign moved 8–14 ms between
originals and repeats. Panako refused the repeats of the very takes it
had accepted.

## Kdenlive technical stratum (separate; never pooled with the n=24)

- 10 valid scoring pairs (pair01 scored via `pair01r2` under
  `KDENLIVE-PLACEMENT-V2`; original pair01 V1 void —
  `PROCEDURE_V1_TIMELINE_ZERO_LEFT_BOUNDARY` — and preserved as evidence
  only).
- Correct placements at 100 ms: **2/10** (pair02: 5.3 ms; pair10:
  0.1 ms). Wrong placements: 8/10. Native failures: 0.
- Sensitivity: identical counts at 50/100/150 ms (the two correct
  placements are ≤5.3 ms; the eight wrong ones are ≥0.85 s).
- Operator time (9/10 timed; pair01r2 saved without a timer record — gap
  documented with owner approval, never imputed): median 58.6 s, IQR
  45.1–60.7 s, total 551.5 s.
- The pair01r2 placement (−145.60 s) is exactly the move Kdenlive
  requested and was refused during the void V1 run (−8736 frames at
  60 fps), confirming the pair01 audit: the V2 headroom made the move
  executable and revealed that the native envelope-correlation analysis
  itself selected a false peak for that pair. Recorded as observed.
- Explicit caveats: single operator (the owner); not a population-level
  usability study; the V2 correction was outcome-independent and applied
  uniformly before any scoring.

## Operator time

Automated systems are agent-run and report per-record wall-clock in the
raw records (secondary). The human-facing Kdenlive numbers above are the
operator-time result.

## Result robustness at 50/100/150 ms

Primary counts are identical at all three tolerances for every system
and stratum: all accepted errors (automated) are < 25 ms and all
Kdenlive errors are either ≤ 5.3 ms or ≥ 0.85 s. The benchmark's
separation is refusal behavior, not tolerance sensitivity.

## Claim audit

Candidate core claim: *On fresh independently timed recordings from the
stress-test domain, selective alignment reduces catastrophic alignment
errors relative to always-output baselines while retaining useful
positive coverage.*

**Verdict: CLAIM_SUPPORTED_WITH_SCOPE.**

- Catastrophic-error reduction: RhythmAlign 0/24 wrong-reference false
  accepts vs 24/24 (GCC-PHAT) and 24/24 (NCC); and 0/24 wrong accepts on
  positives vs 14/24 (GCC-PHAT) and 5/24 (NCC). Total, not marginal.
- Useful coverage retained: 20/24 (83.3%), bootstrap CI95 [0.60, 1.00],
  all correct placements ≤ 15.7 ms.
- Kill criteria: comparator dominance — not fired (Panako ties safety at
  2/24 coverage; no system reaches RA coverage with ≤ its wrong accepts);
  safety collapse — not fired (0 ≥ 3 threshold); coverage collapse — not
  fired (83.3% ≥ ~50%); GT infeasibility — not fired (26/26); editor
  parity — not fired (Kdenlive 2/10); framing failure — not fired.
- Scope conditions attached: 10 source identities with dependent takes;
  one stress-test domain; one frozen operating point (no threshold
  sweeps); constructed wrong-reference pairs (not a measured creator
  error rate); Panako evaluated under its native shipped thresholds on
  an occurrence-matching contract; magnitudes are domain measurements.

## Limitations

- 10 songs; all within-song counts are dependent; bootstrap intervals
  are descriptive aids, not evidence of equivalence or difference.
- Single domain (rhythm-game handcam-style capture); magnitudes do not
  transfer automatically.
- RhythmAlign's refusals are silent coverage loss: 4/24 positives
  produced no placement, concentrated on repetitive sources — the
  recovery cost of an abstention is not measured by this benchmark
  (the creator pilot is a separate, not-yet-run stratum).
- Kdenlive: one operator, 10 pairs, one editor; pair01r2 operator time
  unrecorded (owner-approved gap, reported as missing, never imputed).
- Panako's near-zero coverage is contract- and threshold-native (shipped
  OLAF defaults, no hybrid refinement allowed); other fingerprint
  configurations were not explored by design.

## What the final evidence does NOT show

- That always-output baselines are unusable in practice — only that
  under frozen always-output semantics their errors are catastrophic and
  frequent on this benchmark; adding an external no-match detector to a
  baseline would be a *different, untuned-here system*.
- Population-level creator effort, preference, or usability claims.
- That RhythmAlign's ABSTAIN is calibrated: 0 wrong accepts on this
  benchmark does not certify future accepts.
- Anything about thresholds other than the frozen 50/100/150 ms grid.
- Kdenlive population behavior (single operator).

## Paper implications

The primary claim (C-A) can now be written from final evidence: a
risk-coverage comparison in which the selective system dominates the
safety axis outright and holds high coverage; the benchmark protocol
(C-B) is validated end-to-end including the no-match stratum that does
the decisive work; the Kdenlive stratum answers "why not just use the
editor's native sync" with a measured 2/10 and observed failure modes
(including a documented native-analysis false peak); the strict repeats
add an instability finding for argmax baselines that survives even
outcome-agreement summaries. The claim must be written with the scope
conditions above; the refusal-cost pilot remains open before any
"and here is what safe costs" statement.

## Reproducibility

Single-pass execution; per-record raw JSON files with SHA-256 sidecars;
aggregates deterministic from raw records; every stage verifies the
previous stage's hashes before running. Re-running `run` after
completion refuses to regenerate records; `score` recomputes byte-
identical artifacts from the frozen raw assembly.

## Artifact hashes (SHA-256)

| Artifact | SHA-256 |
|---|---|
| `results/final_benchmark_manifest.json` | `68ebe06b2e713cc6a9464d96464bb4f18b89f7942f643c47637cf6c58a7a52d1` |
| `results/final_comparator_raw.json` | `9ae59821baaf523ad1f89c98b214d565573600d3e23a7c13a2e2f2a9c848dcb3` |
| `results/final_benchmark_results.json` | `4c6c81dfc8289905286560e8ca2ede71f72c478d6c0fd5c04f68e98061ad6fc2` |
| `results/final_benchmark_results.csv` | `5869356537bf3900120ed8237bf8f37421d56cdf40e1d5fd87ba279286124384` |
| `results/final_kdenlive_results.json` | `f04724a034d48ddb2d497d59ae3bd9dd4132a652878485cff090f6f177f965b2` (body `d72f75fc…`) |
| `results/final_comparator_environment.json` | `c92d6457fca39b0cbdbac8437ffe7fcd3967b60f907ddee64b8c8d25df248e92` |
| `kdenlive/kdenlive_owner_run_freeze.json` | `b7a557f47661ed0e5a2bf017365a2f55ef033bb1f4a0d16b644735e64b84a3c3` |
| `results/evidence_kdenlive_parser_v1_native_failure.json` | `1f8c241ecc5ace2315749a06605d6ff75511651af875adb502931a9d57d44bcf` |

Figures (aggregate views; tables above are the authority):
`results/figures/final_outcome_composition.png`,
`results/figures/final_accepted_offset_errors.png`,
`results/figures/final_condition_summary.png`.

## Post-freeze corrections (both outcome-independent, evidence preserved)

1. **pair01 V1 → pair01r2** (audited before this run;
   `KDENLIVE_PAIR01_AUDIT.md`, `kdenlive_run_policy.json`): owner
   procedure V1's 00:00 placement created an artificial left boundary;
   V2 places both clips at 00:03:00 headroom (derived from frozen input
   sizes only). Original run preserved verbatim and never scored.
2. **Kdenlive XML parser v2** (this run, before any Kdenlive result
   existed): the committed extraction module assumed the first
   `<tractor>` element lists the timeline playlists and resolved clip
   resources only from `<producer>` elements; real Kdenlive 26.08
   documents nest one tractor per timeline track and store clips as
   `<chain>` elements, so the module reported NATIVE_FAILURE for all ten
   projects. The correction reads document structure only (reachability
   of playlists from tractors; chain resources) — no GT, marker,
   comparator, or placement information feeds it — and affects all ten
   projects identically. The invalid all-NATIVE_FAILURE output is
   preserved verbatim (`evidence_kdenlive_parser_v1_native_failure.json`)
   and regression tests cover the nested/chain structure. Placement
   arithmetic (the scored quantity) is unchanged.
3. **Owner timing decision** (this run): pair01r2 was saved without a
   timer record; the owner approved proceeding with the gap documented
   rather than re-running for a timing number. Operator-time statistics
   cover the 9 timed valid runs.
