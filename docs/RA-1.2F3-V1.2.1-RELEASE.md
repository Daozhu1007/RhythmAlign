# RA-1.2F3 — v1.2.1 publication and final verification

Date: 2026-10-07 (Asia/Shanghai). Verdict: **V121_RELEASE_COMPLETE**.

[Stable/latest GitHub Release](https://github.com/Daozhu1007/RhythmAlign/releases/tag/v1.2.1).

## Owner acceptance and immutable bytes

The Owner explicitly granted **OWNER_RC_PASS**, with verdict **PERFECT PASS**,
after manually testing the actual RC1 installer: the GUI displayed RhythmAlign
v1.2.1; the exact 共感 AP pair succeeded; Engine v2 reported **+11.3778 s**;
the reliability gate passed; the final offset remained **+11.3778 s**; real
export succeeded and the output was usable. These are Owner-reported manual
observations supplied with publication authorization, not an independent F3
GUI, listening, or screenshot experiment.

The final Setup and Owner-tested `dist/rc/RhythmAlign-v1.2.1-RC1-Setup.exe`
were rehashed before publication. Both are 118711694 bytes and have SHA-256
`EE925C3BEFB2DF526339B11D8CC9422CC39ECAD71BDA88025DFC76BA58331D5A`.
The final Setup and validated Portable were uploaded directly from `dist/`.
**No rebuild, substitution, or algorithm change occurred after OWNER_RC_PASS.**

## Source and final gate

| Item | Verified value |
|---|---|
| Pre-publication local main = fetched origin/main | `afa5938cc917ba98da508556ec1feca66a334e4c` |
| Exact RC build source | `c4b1b1cc2d9adf967feb412d916a40389ce0da22` |
| Release-manifest commit | `4c6728e4639789643d88eff139fb7d6f91985d92` |
| Lightweight v1.2.1 tag target | `4c6728e4639789643d88eff139fb7d6f91985d92` |
| Release ID | 405158069 |
| GitHub publication time | 2026-10-07 05:31:51 +08:00 (2026-10-06T21:31:51Z) |
| Release title / state | RhythmAlign v1.2.1; draft=false; prerelease=false; stable/latest |

Fetched main matched the authorized baseline exactly. Its only change from
the RC build commit was the F2 Markdown report. There was no product/source
drift. The existing untracked F0 evidence was identified against F2's saved
preservation hashes, preserved unchanged, and excluded locally through
`.git/info/exclude`; it was never staged. The release-note carrier was the
other intentional untracked file. Neither v1.2.1 tag nor Release existed at
phase entry; GitHub returned HTTP 404 for the latter.

The final gate used the repository's existing Python environment, with no
overlapping media experiment:

- `python -m pytest tests/ -q`: **96 passed in 31.53 s**.
- `git diff --check`: passed.
- Static compilation of all seven root Python sources and `RhythmAlign.spec`: passed.
- All RC source-file hashes in the saved F2 inventory matched before publication.
- app_info, both locale titles/About strings, Inno Setup, bundled_update.json,
  and both README badges consistently reported **1.2.1**.
- The engine, worker, UI, diagnostics and updater sources matched reviewed F1.
  No algorithm retuning or new product-code edit occurred in F3.

| Frozen DecisionPolicy value | Value |
|---|---:|
| cluster_tol_s | 0.15 |
| margin_floor_a | 1.00 |
| margin_floor_b | 1.40 |
| tonal_z_floor | 5.0 |
| pcen_z_floor | 5.6 |
| pcen_primary_z_floor | 7.0 |
| onset_corroboration_z_floor | 2.0 |
| ambiguity_z_ratio | 0.95 |
| max_top_bin_share | 0.25 |

## Public assets and mandatory download-back

Exactly two binary assets were uploaded. GitHub reported `state=uploaded`
for both, with the following sizes and matching `sha256:` digest values.
Anonymous public downloads into a newly created temporary directory used
the application's existing `download_file()` and `sha256_file()` functions.
The complete downloaded files matched the expected filenames, sizes and
hashes below.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| [RhythmAlign_v1.2.1_Setup.exe](https://github.com/Daozhu1007/RhythmAlign/releases/download/v1.2.1/RhythmAlign_v1.2.1_Setup.exe) | 118711694 | `EE925C3BEFB2DF526339B11D8CC9422CC39ECAD71BDA88025DFC76BA58331D5A` |
| [RhythmAlign-v1.2.1-Portable.zip](https://github.com/Daozhu1007/RhythmAlign/releases/download/v1.2.1/RhythmAlign-v1.2.1-Portable.zip) | 180789856 | `12AAB8525BD1978218E8C4328689B9FAD245E03C8DD61BF13C7A998BDAA46515` |

Download-back integrity: **PASS**, completed 2026-10-07 05:34:58 +08:00.
No RC-named artifact, log, report, raw JSON or debug archive was uploaded.
GitHub's automatically generated source archives are separate from these
two uploaded assets.

The public Release page was read independently of the upload command and
showed the intended title, tag, commit, Latest status, patch notes, download
table and hashes. The GitHub GFM renderer also confirmed the quote,
headings, table and both hashes. Release body matched the local notes.
The notes accurately describe false ambiguous-alignment abstention caused
by shared independent spectral peaks, unique peak ownership before family
aggregation, unchanged thresholds, and preserved wrong-song/repeated-content
safe-stop behavior. They make no universal correctness claim.

## Publication order and real update path

1. Public raw `main/update.json` was verified at **1.2.0** before publication.
2. Only `update.json` was committed as `chore: publish v1.2.1 release manifest`;
   the existing schema was preserved exactly and parsed by the production
   `release_from_manifest()` function.
3. The new lightweight tag was created at the manifest commit and **only the
   tag** was pushed. Remote main remained at `afa5938...`.
4. The stable/latest Release was created with the exact approved bytes.
5. Both full public download-back checks and Release-page/API checks passed.
   The public main manifest was still **1.2.0** after these checks.
6. Only then was main pushed to `4c6728e...`; fetched origin/main equaled local
   main, verified at 2026-10-07 05:35:25 +08:00.
7. The first immediately subsequent raw fetch observed a stale manifest.
   The same original URL, without a cache-busting query or product-code
   change, then served **1.2.1**. The complete update-path gate passed at
   2026-10-07 05:35:53 +08:00.
8. This documentation-only publication receipt follows afterward. The
   v1.2.1 tag remains at the release-manifest commit.

[Public update.json](https://raw.githubusercontent.com/Daozhu1007/RhythmAlign/main/update.json)
exactly matched the committed manifest: version/tag/release URL, both asset
names and URLs, sizes, and SHA-256 values.

The unmodified production `fetch_latest_release()` fetched that public raw
URL with **no bundled or GitHub API fallback**. Its result was passed to the
existing `is_newer_version()` function:

| Installed -> public version | Result |
|---|---|
| v1.2.0 -> v1.2.1 | **UPDATE AVAILABLE** |
| v1.2.1 -> v1.2.1 | **NO UPDATE** |

Both manifest asset URLs independently resolved anonymously with HTTP 200
and exact Content-Length after main publication. Their URLs and downloaded
hashes matched the manifest, and the downloaded files were rehashed during
the update-path check before cleanup. Latest API still identified this
stable Release.

Direct GitHub Git access initially reset the connection. Subsequent Git,
CLI and anonymous HTTP checks used the already-running local proxy through
command/process-local options. Product networking, Git configuration, and
the operating-system environment were not changed. This confirms the
public update path over the tested connection; it is not a claim that every
network can reach GitHub.

## Preservation, cleanup and final Git receipt

The temporary downloaded verification copies and their directory were
removed after all publication/update gates passed. The temporary
`release_notes_v1.2.1.md` carrier remained untracked throughout and was
removed according to `RELEASE.md`. Its public body remains on GitHub.
Approved artifacts remain under ignored `dist/`; F0/F1 local evidence and
research data were preserved. Raw F0 artifacts, private media manifests,
logs and machine evidence were neither committed nor uploaded. Local F3
verification receipts remain under ignored `results/ra12f3/`.

This receipt is the only file in the final documentation commit. Its final
commit/origin-main SHA is returned explicitly in the final handoff and
saved in the ignored local `results/ra12f3/delivery.json` after push. To avoid
a self-referential commit hash in this file, independently resolve it with:

```text
git log -1 --format=%H -- docs/RA-1.2F3-V1.2.1-RELEASE.md
git rev-parse origin/main
git rev-parse refs/tags/v1.2.1
```

The first two agree at phase completion; the third remains
`4c6728e4639789643d88eff139fb7d6f91985d92`. Final delivery verifies a clean
working tree, unchanged prior tags, retained exact artifact/F0 hashes and
local main = origin/main. No existing tag is moved.

## Known residual

The previously documented room-grid pair `haiditan_ds_1 x tr_hongzhoutian`
remains an unresolved accepted match: historical **+59.72172335600907 s**,
ACCEPT_DUAL_FAMILY, temporal share **0.0613**, unresolved target identity.
F3 did not rerun, repair or reclassify it. F1/F2 historical regression
results remain development/safety evidence; this release does not turn
them into independent population accuracy evidence. No algorithm changes
occurred after F1, and no rebuild occurred after Owner acceptance.
