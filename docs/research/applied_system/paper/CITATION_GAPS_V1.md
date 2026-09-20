# Citation Gaps V1

STATUS: **ZERO UNRESOLVED CITATION TODOs.** Supersedes CITATION_GAPS_V0 (kept as revision history). Full per-reference records now live in [CITATION_LEDGER_V1.md](CITATION_LEDGER_V1.md).

## Resolution summary

| V0 gap | Resolution in V1 | Evidence |
|---|---|---|
| C1 — OLAF-specific primary method reference | **RESOLVED.** R11 (Six, ISMIR 2020 Late-Breaking/Demo extended abstract) identifies the evaluated strategy's method provenance; R12 (Six, JOSS 2023) documents the portable system. The manuscript states explicitly that the evaluated comparator is the OLAF strategy within the pinned Panako implementation, not every OLAF/Panako configuration. | Venue string verified from the author's repository bibliography; JOSS record fully retrieved (DOI 10.21105/joss.05459). The archives.ismir.net 2020 LBD index blocks automated retrieval (HTTP 403), so R11 claims no article/page numbers. |
| C2 — Ramona & Peeters complete metadata and passage check | **RESOLVED.** R13 with full metadata (DAFx-11, Paris, Sept 19–23 2011, pp. DAFX-429–436) and passage verification: incorrect-annotation detection, repetition discard, and temporal occurrence support are all confirmed present in the retrieved PDF. The manuscript positions it as close prior art and claims no conceptual novelty for rejecting unsupported occurrences. | Full proceedings PDF retrieved and read on 2026-09-20. |

## Newly added category (hostile review)

| Addition | Reference | Why required |
|---|---|---|
| Public audio-identification evaluation frameworks | R14 — Ramona et al., "A Public Audio Identification Evaluation Framework for Broadcast Monitoring," *Applied Artificial Intelligence* 26(1–2), 119–136, 2012, DOI 10.1080/08839514.2012.629840 | The hostile review identified public evaluation frameworks as a materially missing prior-art category. The manuscript now discusses this family and states what the present protocol adds (controlled acoustic rerecording acquisition, system-independent timing markers, reference-placement task contract, explicit frozen system outputs, applied editor comparator) without claiming mismatch evaluation itself is new. Crossref + HAL verified. |

## Retrieval rechecks closed (were open in V0)

- **R1 Knapp–Carter:** Crossref DOI record verified in full (journal, vol. 24(4), pp. 320–327, 1976); DOI resolves to IEEE document 1162830. Closed.
- **R3 Ewert–Müller–Grosche:** Crossref DOI record verified (ICASSP 2009, pp. 1869–1872, DOI 10.1109/ICASSP.2009.4959972); the institution-hosted PDF remains HTTP 403 but is no longer needed for metadata. Closed.
- **R5 Wang:** Zenodo ISMIR-archives record retrieved (DOI 10.5281/zenodo.1416340, venue string, Baltimore, Oct 27–30, 2003). Pages 7–13 carry disclosed secondary provenance (author-maintained Olaf repository bibliography, consistent with the committed literature notes). Closed with provenance note.

## Remaining honesty caveats (not gaps)

- R11's ISMIR-archives listing is bot-blocked; its venue string is verified from the author's own committed bibliography, and no page or article numbers are claimed. This is a retrieval limitation, honestly recorded, not an unresolved reference.
- No newly found method is silently promoted to an evaluated comparator; R11–R14 support positioning and provenance statements only.
