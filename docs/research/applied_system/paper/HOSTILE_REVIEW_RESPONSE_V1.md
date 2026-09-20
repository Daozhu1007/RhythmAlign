# Hostile Review Response V1

Response memo for the independent hostile review of PAPER-DRAFT-0 (verdict: MAJOR_REVISION_REQUIRED), executed during MANUSCRIPT-REVISION-1 on branch `research/applied-system-paper` from HEAD `8940cc4`. The review's main technical objection — comparator validity — was investigated first as COMPARATOR-INTEGRITY-1 (a frozen-evidence audit, not a rerun of the benchmark), and its findings drive the revisions below.

Provenance note: the review text itself was not committed to the repository. The issue statements below are reconstructed from the revision mandate and the committed comparator-integrity audits; each response cites committed evidence only. Tone is factual by design.

---

## M1 — Comparator validity: GCC-PHAT index-to-lag mapping

**Reviewer issue.** The frozen `gcc_phat_argmax_v1` comparator may map the FFT correlation index to lag incorrectly for unequal-length signals, invalidating the GCC-PHAT arm.

**Disposition.** Bug confirmed. Corrected synthetic-first with an outcome-independent, hash-sealed prediction; zero scored outcome changes. The valid paper comparator is now `gcc_phat_argmax_v2_lagfix`; the original v1 is preserved verbatim as defective-implementation evidence, not silently replaced.

**Change made.** §4.5 documents the defect (midpoint unwrap on a length-dependent support region), its discovery through independent manuscript review, the synthetic-first correction validated on known-offset fixtures before any final case was re-executed, the frozen geometry-only prediction manifest, and the uniform rerun that changed exactly two reported offsets (final21 positive and wrong-reference records) and zero scored outcomes at 0.05/0.1/0.15 s. Every principal GCC result, Table 2, and Table 3 now use the v2 lagfix distributions; the superseded v1 artifact maximum no longer appears as the valid GCC result, and the corrected all-produced maximum is 113.1878 s (median unchanged at 29.3135 s). §4.8 and §8 record the correction as the third preserved outcome-independent correction. Tables and prose are labeled "(v2 lagfix)".

**Evidence.** [GCC_PHAT_LAG_AUDIT.md](../GCC_PHAT_LAG_AUDIT.md); frozen [correction manifest](../../../../experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_correction_manifest.json) (freeze hash verified, prediction made before rerun); [gcc_phat_v2_lagfix_results.json](../../../../experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_results.json); 26 synthetic regression tests written and passing before the rerun; `validate_paper_v1.py` recomputes the v2 distributions and asserts count identity with the sealed reporting artifact.

**New data required?** No. The uniform rerun of the affected comparator arm was executed under the frozen contract as part of COMPARATOR-INTEGRITY-1 (byte-identical inputs, hash-verified); no further execution is needed or performed.

---

## M2 — Comparator validity: NCC contract asymmetry and over-attribution to selectivity

**Reviewer issue.** The NCC comparison does not isolate the value of abstention: NCC searches every nonzero overlap down to one sample, while RhythmAlign requires at least 30 s of usable overlap, so the measured difference conflates estimator and candidate-policy differences.

**Disposition.** Contract asymmetry disclosed; causal claim narrowed; no selective NCC created.

**Change made.** NCC is now labeled an unconstrained full-lag argmax control in §4.5, Table 2, and Table 4. New §6.4 states the required disclosure verbatim: "NCC remains an unconstrained argmax control. Its five wrong positive placements occurred at short edge overlaps that RhythmAlign's frozen candidate policy excludes; therefore the comparison reflects both estimator and candidate-policy differences and does not isolate the causal value of abstention." The five wrong positives' usable overlaps (1.675/1.234/3.589/3.522/4.694 s, approximately 1.2–4.7 s) are reported against the 30 s threshold and the 19 correct positives at 60.414 s or more (Table 7 panel). The abstract and §7 now attribute the measured differences to complete system contracts rather than to selectivity. §4.5 and §8 state that a 30 s-filtered NCC would be a different, unevaluated system; the paper draws no conclusion that such a system would succeed, that NCC is inherently unreliable, or that correlation cannot solve the task. No new NCC variant was built or run.

**Evidence.** [NCC_OVERLAP_CONTRACT_AUDIT.md](../NCC_OVERLAP_CONTRACT_AUDIT.md) (reporting-only audit from stored records); overlaps recomputed by `validate_paper_v1.py` from frozen NCC lag samples and correction-manifest lengths, pinned by `tests/test_comparator_integrity_audit.py`.

**New data required?** No. Scoring NCC at restricted lags on exposed final data would be a new experiment on final data; the frozen protocol reserves such a change for a new protocol and new data.

---

## M3 — Prior-art positioning gaps

**Reviewer issue.** The draft lacked the OLAF primary method reference, complete metadata for the close occurrence-alignment prior art, and the public audio-identification evaluation-framework category; SyncSink positioning was too thin.

**Disposition.** Accepted; all four repaired without new empirical claims.

**Change made.** §2.2 adds R11 (Six, OLAF, ISMIR 2020 Late-Breaking/Demo extended abstract) and R12 (Six, Olaf, JOSS 2023) and states that the evaluated comparator is the OLAF strategy within the pinned Panako implementation, not every configuration. R13 (Ramona and Peeters, DAFx-11, pp. DAFX-429–436) is treated as close prior art that already addresses incorrect annotations, repeated occurrences, and temporal occurrence support; the paper explicitly claims no conceptual novelty for rejecting unsupported occurrences. R14 (Ramona et al., Applied Artificial Intelligence 26(1–2):119–136, 2012) anchors the public evaluation-framework family, and the paper lists its protocol additions relative to that family rather than claiming mismatch evaluation is new. §2.3 acknowledges that SyncSink already combines fingerprint-supported synchronization, match qualification, waveform refinement, and a practical interface, and that the evaluated OLAF CLI is not a direct empirical test of the complete SyncSink pipeline. Both V0 citation TODOs are resolved; zero remain.

**Evidence.** [CITATION_LEDGER_V1.md](CITATION_LEDGER_V1.md) (verification status per record; full DAFx-11 PDF retrieved and passages checked; JOSS, Crossref, Zenodo, and HAL records retrieved); [CITATION_GAPS_V1.md](CITATION_GAPS_V1.md) resolution table.

**New data required?** No.

---

## M4 — Overclaiming: title, terminology, and causal wording

**Reviewer issue.** "Reliable" in the title overstates the evidence; consequence-laden outcome wording (a severity adjective for an unmeasured consequence class), workflow-benefit wording, and phrasing that implies selectivity produced the improvement exceed what the benchmark supports.

**Disposition.** Accepted; title replaced, central claim reframed, terminology cleaned globally.

**Change made.** The title is now "Benchmarking Selective Reference-Audio Alignment on Controlled Acoustic Rerecordings" — no demonstrated-property adjective and no implication of general user-generated-video validation. The central claim (§1, §7, §10, abstract) is now the contract-scoped statement: RhythmAlign produced fewer wrong placements than the evaluated always-output controls while retaining 20/24 correct placements, and the comparison does not isolate a causal effect of abstention. "Wrong placements" replaces consequence-class wording except for descriptive error magnitudes; `SAFE_ABSTAIN` is retained only as a defined scoring label meaning no placement was emitted for a no-match case; the accepted-risk metric is renamed "positive-case accepted error rate" (with the selective-prediction parallel noted once, defined). The automated checker rejects the superseded GCC maximum, consequence-class wording, workflow-benefit wording, and causal selectivity phrasing anywhere in the V1 manuscript set.

**Evidence.** `validate_paper_v1.py` revision gate (wording checks fail closed); CLAIM_LEDGER_V1 core-claim boundaries; abstract audit A01–A10.

**New data required?** No.

---

## m1 — Benchmark realism and acquisition disclosure

**Reviewer issue.** The draft under-disclosed that the corpus is controlled rerecording rather than field sampling, and acquisition asymmetries (interference-take durations, device-assignment wording) were not surfaced.

**Disposition.** Accepted; disclosures added from frozen metadata; nothing invented.

**Change made.** §4.3 now states that the benchmark is controlled acoustic rerecording over a structured 10-identity stress-test pool with dependent repeated conditions and constructed wrong references; that the common 60 s payload represents one duration regime favoring substantial overlap, with RhythmAlign's 30 s minimum-overlap requirement flagged for applicability to shorter clips; that the four interference takes (final17–final20) produced trimmed inputs of approximately 136.9–139.3 s versus approximately 62.9–68.7 s elsewhere (frozen lengths; the acquisition record documents no reason, and none is invented); and that the per-take drift QC assigns final21–final22 to the primary device D1, reconciling the attestation summary's over-inclusive "final17–final24" range — a provenance clarification only, with the device-variation condition remaining final23–final24.

**Evidence.** Frozen per-case lengths in [gcc_phat_v2_lagfix_correction_manifest.json](../../../../experiments/applied_system/final_pack/results/gcc_phat_v2_lagfix_correction_manifest.json); per-take device table in [FINAL_ACQUISITION_QC.md](../FINAL_ACQUISITION_QC.md) Drift QC; attestation summary sentence in the same document; checked by `validate_paper_v1.py`.

**New data required?** No.

---

## m2 — Kdenlive stratum scoping

**Reviewer issue.** The 2/10 Kdenlive result invites an unsupported "RhythmAlign beats Kdenlive" reading.

**Disposition.** Accepted; stratum boundaries and a scoped interpretation added.

**Change made.** §6.7 and Table 5 now state the boundaries: ten selected positives across seven source identities, one owner/operator, one editor version, no wrong-reference arm, and explicitly not a usability comparison. The preferred interpretation — "the native command did not reliably recover placement on this selected technical stratum" — replaces any cross-tool preference claim; the automated checker enforces its presence.

**Evidence.** [final_kdenlive_results.json](../../../../experiments/applied_system/final_pack/results/final_kdenlive_results.json); V2.kdenlive_stratum; [KDENLIVE_PAIR01_AUDIT.md](../KDENLIVE_PAIR01_AUDIT.md).

**New data required?** No.

---

## m3 — Reproducibility overstatement

**Reviewer issue.** Hash-verified provenance was being read as if the exact final corpus were openly available for re-execution, which it is not (commercial media).

**Disposition.** Accepted; reproducibility split into three explicit levels.

**Change made.** §9 now distinguishes (A) result recomputation from committed outputs, manifests, hashes, and scoring/reporting code; (B) system re-execution on the exact final media, which requires authorized access because the media are not openly redistributed; and (C) protocol replication with other authorized or open media. The paper uses "reproducible protocol with restricted exact-media corpus" and states that hashes prove identity, not availability. The automated checker rejects the corpus being called openly available/reproducible.

**Evidence.** V2.authority and raw-assembly hashes; [FINAL_SOURCE_SELECTION.md](../FINAL_SOURCE_SELECTION.md) copyright/access clarification; `validate_paper_v1.py` wording gate.

**New data required?** No.

---

## Cross-cutting statement

No comparator was rerun during this revision except the already-executed, protocol-authorized uniform GCC v2 lagfix rerun performed under COMPARATOR-INTEGRITY-1 before this manuscript work; no threshold, scoring rule, pairing, or frozen artifact was modified; all 200 original raw records, sidecars, and sealed artifacts are hash-verified unchanged since `8940cc4`. The creator feasibility pilot remains NOT_CONDUCTED and no pilot results are reported. Frozen original evidence changed: **NO** (additive versioned artifacts only). Comparators rerun during this revision task: **NO**.
