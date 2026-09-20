# Citation Gaps V0

STATUS: 2 explicit citation TODOs; technical-core draft, not submission-ready.

Scope: complete references needed for statements already in this manuscript. No new literature survey, benchmark arm, or empirical claim is authorized by this list. No bibliography entry was invented to fill a gap.

## Missing references / metadata

| ID | Missing work / information | Why needed | Suggested bounded search query/topic | Manuscript location |
|---|---|---|---|---|
| C1 | OLAF-specific primary method reference; verified authors, title, year, venue, and relationship to the OLAF strategy in pinned Panako | The measured strategy is OLAF. The existing Panako 2.0 demo citation is valid family context but does not identify OLAF's method provenance | `Joren Six OLAF acoustic fingerprinting original paper Panako OLAF strategy e4b0e1db` | §2.2 TODO; comparator provenance in §4.5 |
| C2 | Ramona and Peeters, Automatic Alignment of Audio Occurrences (2011): full author names, proceedings metadata, pages if available, and exact support for the occurrence-support discussion | The committed repo-wide audit identifies this close precedent but its bibliography is incomplete; do not guess metadata or import unchecked detailed mechanisms | `Ramona Peeters Automatic Alignment of Audio Occurrences DAFx 2011`; begin with [the paper already named in the committed audit](https://www.dafx.de/paper-archive/2011/Papers/94_e.pdf) | §2.2 TODO |

Both placeholders use `[CITATION TODO: ...]` in the manuscript. C2's work is known from the committed audit; the gap is complete metadata and passage verification, not permission to assert method novelty pending a search.

## Citation provenance register

The primary committed literature source is [LITERATURE_REVIEW.md at 8b78eb1](https://github.com/Daozhu1007/RhythmAlign/blob/8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e/docs/research/alignment/LITERATURE_REVIEW.md), inspected directly from Git history. The local [repo-wide paper audit](../../repo_wide/PAPER_OPPORTUNITY_AUDIT.md), Source record and nearest-systems discussion, supplies the editor documentation and occurrence-alignment lead. The notes' historical statements that final comparators were unmeasured are historical context, not current benchmark status.

| Paper ID | Committed metadata source | Targeted verification on 2026-09-20 | Permitted use / unresolved issue |
|---|---|---|---|
| R1 Knapp & Carter (1976) | Archived literature review, Established audio representations and matching baselines | DOI resolver could not be fetched by the browser tool | Existing complete author/title/journal/year/volume/pages/DOI retained; recheck primary landing page before submission; no invented substitute metadata |
| R2 Lewis (1995) | Same section | [Author treatment](https://scribblethink.org/Work/nvisionInterface/nip.html) retrieved | Classical normalization background; frozen audio runner uses overlap-energy normalization, not an assertion of an exact locally mean-subtracted implementation |
| R3 Ewert et al. (2009) | Same section | Listed institution PDF returned HTTP 403 | Complete metadata retained from committed notes; recheck primary copy/access before submission |
| R4 Six & Leman (2015) | Archived review, Closest work; repo-wide audit | [Institutional record](https://biblio.ugent.be/publication/6873558) and [author manuscript](https://0110.be/files/attachments/434/2015.synchronized-recording.pdf) retrieved | Author/year/journal/volume/pages confirmed; established fingerprint-based synchronization and refinement, not a measured arm in this final benchmark |
| R5 Wang (2003) | Archived review, Established audio representations | Listed Columbia-hosted PDF could not be fetched | Author/title/year/ISMIR retained from committed notes; no page numbers guessed; recheck a primary proceedings copy before submission |
| R6 Six (2021) | Same section | [ISMIR archive PDF](https://archives.ismir.net/ismir2021/latebreaking/000039.pdf) retrieved | Correctly labeled late-breaking/demo, not main-track paper; not used as the OLAF-specific reference |
| R7 El-Yaniv & Wiener (2010) | Archived review, Peak confidence, fusion and abstention | [JMLR record](https://jmlr.org/papers/v11/el-yaniv10a.html) retrieved | Metadata and coverage/risk framing confirmed; no classification theorem transferred to RhythmAlign |
| R8 Kdenlive manual | Repo-wide audit, Source record | [Official 26.08 manual](https://docs.kdenlive.org/en/cutting_and_assembling/right_click_menu.html) retrieved | Confirms native audio-reference operation; documentation citation, distinct from frozen executable 26.08.1 and its preserved audit |
| R9 Wang et al. (2017) | Archived review, PCEN and HPSS | [Author publication page](https://getreuer.info/papers/wang2017trainable/index.html) retrieved | Authors/title/ICASSP/year/pages confirmed; PCEN is an established ingredient, not evidence for this benchmark's gate calibration |
| R10 FitzGerald (2010) | Same section | [DAFx proceedings PDF](https://dafx.de/paper-archive/2010/DAFx10/DerryFitzGerald_DAFx10_P15.pdf) retrieved | Median-filter HPSS precedent; implementation placement in a mel-power pipeline remains RhythmAlign's known-ingredient choice |

The two metadata/method-reference TODOs are separate from three retrieval rechecks (R1, R3, R5). An unsuccessful fetch does not erase metadata already committed, and this draft does not claim that those three primary documents were newly verified. No broad search was performed: live checks were restricted to references already named in the research history.

## Excluded citation-driven claims

The draft makes no unsupported “first” claim, no statement that prior evaluations generally omit mismatches, no claim that repeated structure universally causes refusal, and no assertion that creator recovery is inexpensive. It does not cite classification guarantees as a risk certificate. No newly found method is silently promoted to an evaluated comparator. Final bibliographic formatting and the two TODOs remain work for manuscript review before submission.
