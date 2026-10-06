# RA-1.2F2 — v1.2.1 RC1 gate

Date: 2026-10-07 (Asia/Shanghai). Disposition: `READY_FOR_V121_OWNER_RC1`.

**Hard stop: waiting for OWNER_RC_PASS on the exact Setup bytes below.**

## CTO and merge provenance

Owner-supplied verdict: **RA-1.2F1_CTO_REVIEW_PASS**. F1 evidence: [RA-1.2F1-EVIDENCE-OWNERSHIP-FIX.md](RA-1.2F1-EVIDENCE-OWNERSHIP-FIX.md).

- Fetched pre-merge main/origin/main: `c92e82763350d70e7d5982de2dcdcb99cebc1e83`.
- Reviewed local/remote hotfix HEAD: `7619b9c5a8290dfee51a67d5caa1c59e6eb24ad7`.
- Implementation: `9d5973e61dd0bba386501d7bf309e7e7fb83c18a`.
- Ancestry: 2 ahead, 0 behind; no baseline drift. Primary checkout returned to clean tracked main; `git merge --ff-only` merged only the reviewed branch.
- Immediate post-merge suite: **96 passed in 37.94 s**; diff check clean.
- Exact version/source/build commit: **`c4b1b1cc2d9adf967feb412d916a40389ce0da22`**, `chore: prepare v1.2.1 release candidate`.
- This report follows in a documentation-only commit. Its final SHA and verified origin/main equality are returned in delivery; obtain the report commit with `git log -1 --format=%H -- docs/RA-1.2F2-V1.2.1-RC.md`.

Direct GitHub connections failed; fetch succeeded through the already-running local proxy using a command-local option. Git configuration and product networking were unchanged.

## Version consistency and scope freeze

Seven changed version files: `app_info.py`, `locales/zh_CN.json`, `locales/en_US.json`, `README.md`, `README_zh.md`, `RhythmAlign.iss`, `bundled_update.json`.

| Surface | Verified value |
|---|---|
| APP_VERSION | 1.2.1 |
| Both GUI titles / About strings | RhythmAlign v1.2.1 / v1.2.1 |
| Installer version / output | 1.2.1 / RhythmAlign_v1.2.1_Setup.exe |
| Bundled offline version / tag | 1.2.1 / v1.2.1 |
| Both README badges and current wording | v1.2.1 |
| **Public update.json** | **1.2.0; byte-identical to pre-merge main** |

Stale-reference classification: A, current version/README surfaces updated; B, historical CP0, RA-1.2D and F1 discussions preserved; C, RA-1.2E release history and historical experiment evidence preserved. Public update.json is the required RC exception. The bundled manifest has no download assets; it describes the installed/offline version.

AST checks confirm unchanged DecisionPolicy, acceptance checks, independent peak nomination, offset choice, ambiguity comparator, concentration calculation and temporal gate. Engine/worker sources match reviewed F1. No threshold tuning, CASE B redesign, UI feature, Linux work or research change. CASE B comparator asymmetry remains out of scope.

## Final source regression

All final tests used repository .venv. Media work ran sequentially **after** all pytest runs. All tracked-file fingerprints stayed unchanged throughout validation and the version commit; artifacts were built from that exact committed source.

| Check | Result |
|---|---|
| Full tests | 96 passed in 33.04s |
| Engine v2 | 13 passed in 10.58s |
| Temporal support | 11 passed in 12.57s |
| Evidence ownership | 16 passed in 1.24s |
| AP, three fresh processes | 3/3 ACCEPT_DUAL_FAMILY, +11.377777777777778 s |
| AP determinism | Complete decisions equal excluding runtime fields |
| AP temporal gate | applied=true; pcen_hpss; share 0.0241 <= 0.25; 140 bins; effective_bins=81.21 |
| Integrated positives, 85 | 55 ACCEPT / 30 ABSTAIN preserved; accepted offset change **0.0 s** |
| Low-SNR 零对话 | +12.49233560090703 s; accepted in established +12.4 +/-0.4 s interval |
| Directed clean wrong songs | 156/156 ABSTAIN |
| DEV concentrated wrong accepts | 18/18 ABSTAIN_CONCENTRATED_EVIDENCE |
| Ordinary mismatches / hard negatives | 10/10 + 10/10 ABSTAIN |
| Tiled/repeated ambiguity | 4/4 ABSTAIN_AMBIGUOUS_CLUSTER |
| Astra blocker | ABSTAIN_CONCENTRATED_EVIDENCE; share 0.9456 |
| AP wrong references | 19/19 ABSTAIN |
| New false ACCEPT in designated negatives | **0** |

Known residual, separate from negatives: `haiditan_ds_1 x tr_hongzhoutian` still **accepted**, ACCEPT_DUAL_FAMILY, **+59.72172335600907 s**, share **0.0613**; same historical offset, unresolved target identity. It was neither repaired nor reinterpreted.

These are reused development/historical regression populations, not fresh independent correctness evidence or a population-wide accuracy estimate. Construction-exact labels, the manual interval and pairing-only evidence retain distinct provenance.

## Real product path

The actual current SyncWorker and revised production find_offset_v2 were exercised. An export-recorder replay checked routing; a separate replay called original mix_and_export with real FFmpeg.

- Correct AP: accepted +11.377777777777778 s; one physical export created a nonempty MP4. First 3 seconds decoded; temporary output removed.
- Deliberate wrong reference: ABSTAIN, zero export calls, no output video.
- Legacy-v1 booby trap: zero calls in both replays. No human listening or GUI alignment interaction is claimed.

## Clean Windows build

Windows x64 build 26200; Python 3.10.11; PyInstaller 6.19.0; Inno Setup 6.7.3; PyQt6 6.10.2; PyQt6-Fluent-Widgets 1.11.1; librosa 0.11.0; imageio-ffmpeg 0.6.0.

The first build compiled but failed actual frozen startup with a QtGui DLL load error. Analysis-00.toc proved that the tool runtime's Poppler PATH entry supplied an incompatible ICU 78 DLL exporting version-suffixed symbols, while Qt imports unversioned Windows ICU symbols. Source Qt used Windows System32 ICU and passed. Failed-build logs/hashes remain ignored locally. The final build excludes tool-native dependency directories from its process-local PATH, retaining repository .venv and normal Windows tools. No repository spec, product code, installed dependency or global environment changed; final artifacts were rebuilt cleanly from the same RC commit and revalidated.

Old build/, dist/, root/test bytecode caches removed first; unrelated research/media and F0 untouched. Unchanged chain: `python -m PyInstaller RhythmAlign.spec --clean --noconfirm`, `ISCC.exe RhythmAlign.iss`, `Compress-Archive`. All succeeded with clean tracked source and unchanged HEAD.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| dist/RhythmAlign_v1.2.1_Setup.exe | 118711694 | `EE925C3BEFB2DF526339B11D8CC9422CC39ECAD71BDA88025DFC76BA58331D5A` |
| dist/RhythmAlign-v1.2.1-Portable.zip | 180789856 | `12AAB8525BD1978218E8C4328689B9FAD245E03C8DD61BF13C7A998BDAA46515` |

## Actual packaged-byte validation

- Shipping RhythmAlign.exe launched independently of project sources; **two** starts each stayed alive 12 seconds, actual title **RhythmAlign v1.2.1**, closed normally via WM_CLOSE, exit 0. Test user config isolated; startup update checks disabled only in that test config.
- Packaged locales title/About and bundled manifest verified at v1.2.1.
- Six actual executable code objects, including engine, ui_main, auto_sync and app_info, match the exact source commit including nested bytecode/constants. Traceback filenames contain no developer absolute paths.
- Actual executable engine/auto_sync bytecode replayed AP with project imports excluded: ACCEPT_DUAL_FAMILY +11.377777777777778 s, pcen_hpss share 0.0241. This uses host .venv dependencies and **is not a fully frozen engine E2E claim**.
- FFmpeg `ffmpeg-win-x86_64-v7.1.exe` present and executable.
- **0** PySide6/shiboken files/modules; no injected probe hook, project test or experiment module. No RC/debug shipping metadata. Existing console=False / CREATE_NO_WINDOW unchanged; no app console window observed during startup.
- Portable ZIP matches bundle byte-for-byte for all **668 files**, with no missing/extra entries.
- Installer installation, GUI alignment interaction and audio listening remain Owner checks; they were not performed here.

## Local Owner package and notes

- `dist/rc/RhythmAlign-v1.2.1-RC1-Setup.exe`: `EE925C3BEFB2DF526339B11D8CC9422CC39ECAD71BDA88025DFC76BA58331D5A` — **byte-identical** to final Setup.
- `dist/rc/RhythmAlign-v1.2.1-RC1-Portable.zip`: `12AAB8525BD1978218E8C4328689B9FAD245E03C8DD61BF13C7A998BDAA46515` — byte-identical to final Portable ZIP.
- `dist/rc/OWNER-TEST-CHECKLIST-v1.2.1-RC1.md`: five short checks (version, AP export/listening, ordinary positive, wrong reference, restart).
- `release_notes_v1.2.1.md`: sanitized concise patch notes with actual hashes; stays local/untracked per RELEASE.md.

## Privacy, preservation and hard stop

Shipping audit passed: no developer/private media paths, hotfix branch names, RC debug constants, raw F0 metadata or precise location/device metadata introduced. No raw F0 JSON, media, local manifests, logs or build outputs staged. All three existing F0 files retain original hashes; cross-platform/linux retains its original HEAD. Local machine evidence and logs stay ignored in results/ra12f2/.

Only the seven version files and this sanitized report accompany the reviewed F1 commits. Public update.json remains **1.2.0**. **No v1.2.1 tag, GitHub Release, public asset upload or publication occurred.** Only main is pushed; final remote HEAD equality is verified in delivery.

**Waiting for OWNER_RC_PASS on the exact local RC1 artifact.**

## Remaining post-Owner-PASS publication sequence

1. Record explicit OWNER_RC_PASS against RC1 Setup hash; recheck source, versions, notes and artifact hashes. Preserve exact tested bytes.
2. Prepare final public v1.2.1 manifest with exact names, URLs, sizes and hashes, retaining v1.2.0 publication ordering.
3. Under the next publication authorization, create/push only v1.2.1 tag and create GitHub Release with exact tested Setup/Portable bytes.
4. Verify uploaded asset hashes before pushing public update.json, so users are never directed at nonexistent assets.
5. Verify release/update path and append publication receipt.

This phase stops for **OWNER_RC_PASS**.
