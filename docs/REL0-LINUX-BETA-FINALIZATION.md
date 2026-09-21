# REL-0 — Linux Beta Release Finalization

Status: **LINUX_BETA_RC_READY · OWNER_LICENSE_DECISION_REQUIRED · READY_TO_PUBLISH_AFTER_OWNER_APPROVAL**
Branch: `cross-platform/linux` · Final RC source commit: **`86c27b4`** (full SHA below)
Date: 2026-09-21 · Mission: REL-0 (nothing was published; no tags/releases created)

---

## 1. Executive Summary

REL-0 produced the exact final source state from which the Linux beta may
later be published, a freshly built and validated release-candidate
artifact with clean provenance, and the two Owner-facing decisions
(release identity, third-party distribution) prepared for a decision
that this mission deliberately did not make.

- Both proven Nightshift commits were cherry-picked onto
  `cross-platform/linux` with history preserved; the production diff is
  exactly the 7-line desktop-entry escaping fix plus test files.
- Full suites green on both hosts (Windows 122 passed / 3 skipped;
  Linux 125 passed / 0 failed), `git diff --check` clean.
- The desktop-integration fix was independently revalidated at source
  level and again against the actual extracted RC artifact (path
  containing spaces and `&`): no `__APP_DIR__` leakage, literal
  Exec/Path/Icon, `--remove` works.
- A **new** RC artifact was built by the production CI pipeline from the
  exact final commit `86c27b4` (no docs-only delta between branch tip at
  build time and the CI build commit) and validated on Ubuntu 22.04
  (glibc 2.35, in-container), Ubuntu 24.04 (CI runner), and WSL Ubuntu
  24.04 — engine decision bit-identical
  (`accepted / ACCEPT_DUAL_FAMILY / 2.995374149659864`) everywhere.
- A release-facing `THIRD-PARTY-NOTICES.txt` (148 KB, canonical license
  texts) is now shipped inside the Linux artifact.
- Third-party audit found **no P0-style technical blocker**, but
  identified that the GUI stack (PyQt6 = GPL-3-or-commercial, no LGPL;
  PyQt6-Fluent-Widgets = GPLv3 with paid commercial licensing) is
  redistributed inside a PolyForm Noncommercial-licensed application.
  Public binary publication therefore requires an Owner decision first.
  The already-published Windows v1.2.0 binaries bundle the same stack,
  so the finding is not Linux-specific.

## 2. Starting State

| Item | Value |
|---|---|
| Repository | `Daozhu1007/RhythmAlign` |
| Branch at start | `cross-platform/linux` |
| HEAD at start | `a2f5ededd9412fff872205e1fac3ba8375f79526` (matches expected baseline) |
| Working tree | clean (`git fetch --all --prune` first) |
| Nightshift commits verified present | `42821a8` (test: close mutation-review false-confidence gaps), `e276859` (fix: escape sed metacharacters in desktop-entry install paths) |
| Nightshift verdict | `LINUX_BETA_REDTEAM_PASS_WITH_NOTES` / `READY_FOR_OWNER_RELEASE_DECISION` |
| Superseded CP-2 artifact | tar.gz SHA256 `e953eeee…74124a` (185,009,492 bytes, run 35529323382; the `c3096e61…` / 185,014,321-byte value recorded by CP-2/NIGHTSHIFT-1 corresponds to the downloaded artifact ZIP containing it) — **predates the desktop fix; not the RC** |
| Stable release | `v1.2.0` (Windows, `prerelease: false`) untouched throughout |

## 3. Nightshift Commits Integrated

Cherry-picked in parent order, history preserved, zero conflicts:

1. `42821a8` → product branch `68b2d01` — `tests/test_nightshift_hardening.py` (145 lines, test-only)
2. `e276859` → product branch `639d706` — `packaging/linux/install-desktop-integration.sh` escaping fix + `tests/test_desktop_integration.py` (80 lines)

Explicitly **not** cherry-picked (per mission): the macOS probe workflow
(`1c244ab`), release-identity characterization-only commit (`7f66466`),
and evidence/report commits.

Production-code impact of the integration:
`git diff a2f5ede..639d706 --stat` = 1 packaging script (+7/−1 lines)
and 2 new test files. No engine, UI, updater, or Windows packaging file
touched.

## 4. Tests

| Suite | Result |
|---|---|
| Windows host (repo checkout), `pytest tests/ -q` | **122 passed, 3 skipped** (skips = the POSIX-only desktop-entry tests) — includes all Windows-specific pins (updater ranking, `explorer /select,`, AppUserModelID, `CREATE_NO_WINDOW`, GPU policy) |
| Linux (WSL Ubuntu 24.04, Python 3.10 venv, pinned `constraints-linux.txt` stack, **LF checkout via `git archive`**), `pytest tests/ -q` | **125 passed, 0 failed** (= 122 + the 3 POSIX desktop-entry tests) |
| `git diff --check` (authoritative Windows checkout) | clean |
| CP-2 CI suite (this RC build, Ubuntu 22.04 container) | green (run 35561857077) |

Investigation note: the first Linux run from the *Windows working
directory* failed the 3 desktop-entry tests with exit 2 — root cause is
`core.autocrlf=true` + no `.gitattributes` giving the shell script CRLF
line endings in Windows checkouts only (`--install\r` misses the case
branch). Linux CI and the artifact are unaffected (Linux checkout = LF;
verified `git archive` extraction is LF and all 125 tests pass there).
Recorded as a new P3 recommendation in §17; no repo change made in
REL-0 to keep the RC diff bounded.

## 5. Desktop-Integration Fix Revalidation

Independently re-ran the Nightshift reproduction (not via the test
suite) against a staged `RhythmAlign/` directory at
`/tmp/rock & roll/RhythmAlign` (contains spaces **and** `&`):

| Check | Source tree (fixed script) | Extracted RC artifact |
|---|---|---|
| Install succeeds | PASS | PASS |
| No `__APP_DIR__` leakage | PASS | PASS |
| `Exec` = literal path | PASS | PASS |
| `Path` = literal path | PASS | PASS |
| `Icon` = literal path | PASS | PASS |
| `--remove` deletes entry | PASS | PASS |

The artifact column re-ran the same regression against the actual
extracted release candidate (`install-desktop-integration.sh` inside the
tar.gz is the fixed version, verified by content). This fix is the
production change that invalidates the old CP-2 artifact as the RC.

## 6. Release Identity Recommendation

Ground truth (re-verified): stable `v1.2.0` exists (`prerelease: false`,
Windows assets, tag on the Windows-release lineage); the Linux beta
comes from five-plus commits that tag does not contain; clients are
manifest-driven (`update.json` on `main`, `1.2.0` only) and never
consult `/releases/latest` (UI never enables the API fallback);
`parse_version` strips prerelease suffixes.

**Recommendation (not executed, Owner decision):** tag
**`v1.2.0-linux-beta.1`** with `prerelease: true` at the RC source
commit **`86c27b4…`** — the exact commit CI built the artifact from —
attaching `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` + `.sha256` +
`build-env-frozen.txt`. Verified properties:

- tag points at the exact RC source commit (clean provenance, §13);
- prereleases are excluded from `/latest` → Windows clients receive no
  beta signal;
- `update.json` stays `1.2.0`-only → Linux beta is manual-update-only;
- embedded `APP_VERSION` remains `1.2.0` (never a prerelease string —
  the suffix-stripping parser would make such a client blind to a later
  stable `1.2.1`);
- stable Windows `v1.2.0`, its assets, and all existing tags untouched;
- future betas: `v1.2.0-linux-beta.2`, … (manual releases-page checking).

Alternatives evaluated by NIGHTSHIFT-1 (attach to stable v1.2.0 =
REJECT, `v1.2.1-beta.1` = viable-but-misleading, immediate stable
v1.2.1 = out of scope) remain rejected for the same reasons.

## 7. Third-Party Distribution Audit

Method: primary sources only (PyPI package metadata for the exact pinned
versions, upstream vendor licensing pages, the license files inside the
redistributed wheels, the shipped binary's own `--version` output, and
the artifact's actual file inventory). No legal advice is given or
implied; classifications are evidentiary.

Redistributed components (Python packages — exact pinned versions, all
verified present in the artifact and in `build-env-frozen.txt`):

| Component | Version | License | Class |
|---|---|---|---|
| PyQt6 | 6.7.1 | **GPL v3** or Riverbank Commercial (no LGPL) | OWNER_LEGAL_DECISION_REQUIRED |
| PyQt6-Qt6 (Qt) | 6.7.3 | LGPL-3.0 (+ Qt third-party components) | NOTICE_REQUIRED_OR_RECOMMENDED |
| PyQt6-sip | 13.12.0 | BSD-2-Clause | CLEAR |
| PyQt6-Fluent-Widgets | 1.11.1 | **GPLv3** (non-commercial); paid commercial license for business | OWNER_LEGAL_DECISION_REQUIRED |
| PyQt6-Frameless-Window | 0.8.2 | GPLv3 | OWNER_LEGAL_DECISION_REQUIRED |
| Python runtime | 3.10 | PSF-2.0 | CLEAR |
| numpy / scipy / scikit-learn | 1.24.4 / 1.10.1 / 1.7.2 | BSD-3 (bundle OpenBLAS, GCC runtime w/ exception) | CLEAR |
| librosa | 0.11.0 | ISC | CLEAR |
| numba / llvmlite | 0.58.1 / 0.41.1 | BSD-2 (llvmlite bundles LLVM, Apache-2.0 + LLVM exception) | CLEAR |
| soundfile (+libsndfile) | 0.13.1 | BSD-3 (libsndfile LGPL-2.1+; COPYING shipped in `_soundfile_data/`) | NOTICE_REQUIRED_OR_RECOMMENDED |
| soxr | 0.3.7 | LGPL-2.1-or-later | NOTICE_REQUIRED_OR_RECOMMENDED |
| imageio-ffmpeg | 0.6.0 | BSD-2 (wrapper) | CLEAR |
| certifi | 2026.7.22 | MPL-2.0 | NOTICE_REQUIRED_OR_RECOMMENDED |
| requests/urllib3/idna/charset-normalizer, audioread, joblib, pooch, msgpack, lazy-loader, decorator, darkdetect, cffi, pycparser, typing_extensions, cloudpickle, threadpoolctl, setuptools | (frozen) | Apache-2.0 / MIT / BSD-3 / PSF-2.0 | CLEAR |
| FFmpeg binary (bundled) | 7.0.2 static | **GPL-3** (see §9) | NOTICE_REQUIRED (compliance satisfiable; see §8 for the coupled question) |
| OpenSSL (libssl.so.3/libcrypto.so.3) | 3.x (Ubuntu 22.04) | Apache-2.0 | NOTICE_REQUIRED_OR_RECOMMENDED |
| System libraries from build image (GLib, systemd, util-linux libs, Kerberos, X11/xcb, ICU, zlib, libpng, freetype, brotli, zstd, readline, …) | per jammy | mostly LGPL-2.1+/MIT/BSD families; **readline = GPL-3+** | NOTICE_REQUIRED_OR_RECOMMENDED |

Full component table, licenses, upstream references, and canonical
license texts are shipped in `THIRD-PARTY-NOTICES.txt` (§10).

## 8. PyQt6 / QFluentWidgets Licensing Finding

Established from official sources:

- **PyQt6** (Riverbank Computing): *"PyQt is dual licensed on all
  supported platforms under the GNU GPL v3 and the Riverbank Commercial
  License"* and, explicitly, *"Unlike Qt, PyQt is not available under
  the LGPL."* There is no LGPL option.
- **PyQt6-Fluent-Widgets** (qfluentwidgets): *"licensed under GPLv3 for
  non-commercial project"*; *"For commercial use, please purchase a
  commercial license."* The artifact also redistributes
  **PyQt6-Frameless-Window** (GPLv3, same author).
- **RhythmAlign** is licensed under **PolyForm Noncommercial 1.0.0**.

Analysis (factual, no legal certainty claimed): the shipped application
is a *combined work* — RhythmAlign code is compiled into the same
distribution and linked against PyQt6/QFluentWidgets. Distributing that
binary publicly means distributing the GPL-3-licensed components under
GPL-3 terms for the whole, or holding the vendors' commercial licenses.
PolyForm Noncommercial 1.0.0 is a source-available license that
restricts recipients to noncommercial use; it does not function as a
GPL-3 grant for RhythmAlign's own portion, and adding third-party
notices does not change that. The Owner holds copyright in RhythmAlign
and is free to make a distribution-policy decision (commercial
licensing from the vendors; distributing under GPL-3-compatible terms
for the binary; or changing the project license) — but any of those is
an **Owner decision, not a compliance chore**, and this mission did not
execute any of them.

**Compatibility memo verdict: B — Current distribution model requires
Owner/legal review before a new public binary release.**

(A is false — there is an apparent unresolved compatibility question.
C and D each name only one possible remedy; the evidence supports B as
the honest state. If evidence had been ambiguous, B was mandated.)

## 9. FFmpeg Distribution Finding

Exact bundled binary, verified from the artifact itself:
`ffmpeg-linux-x86_64-v7.0.2`, `ffmpeg version 7.0.2-static
https://johnvansickle.com/ffmpeg/`, configuration beginning
`--enable-gpl --enable-version3 --enable-static …` (full flag list
recorded in `THIRD-PARTY-NOTICES.txt` §2). The `--enable-gpl` +
`--enable-version3` combination makes the binary **GPL-3** as a whole
(GPL components such as libx264/libx265 are enabled).

Redistribution obligations and how they are addressed:

- **License text**: GPL-3 text included in `THIRD-PARTY-NOTICES.txt`.
- **Source availability**: official FFmpeg n7.0.2 source
  (ffmpeg.org) plus the builder's published provenance/sources
  (johnvansickle.com/ffmpeg/), plus a written-offer pointer for this
  specific archive. Recorded in the notices file.
- **Codec implications**: the build's external libraries each carry
  their own licenses, documented in the FFmpeg source tree; the notices
  file points there rather than fabricating a per-codec list.
- **Linkage nature**: FFmpeg is executed as a **separate standalone
  program** (subprocess via imageio-ffmpeg), not linked into the
  application — this is the factually relevant distinction versus the
  PyQt6/Qt stack, and it is why FFmpeg is classified as
  NOTICE_REQUIRED (compliance-focused) rather than an owner-decision
  blocker in itself. No replacement of FFmpeg was made or needed.

## 10. Third-Party Notices

Created **`THIRD-PARTY-NOTICES.txt`** (repo root; 148 KB) and added it
to the Linux artifact staging (`packaging/linux/package_artifact.sh`),
so the RC tar.gz ships `LICENSE` (PolyForm NC, project code) alongside
`THIRD-PARTY-NOTICES.txt` (third-party components) — the two are
explicitly distinguished in the file header.

Content, all sourced (nothing fabricated): per-component table (name,
exact version, license, upstream URL); FFmpeg section with the exact
build flags and source references; Qt section (LGPL-3, dynamic linking,
Qt's official third-party-licenses page); build-image system libraries
grouped by license family with the Ubuntu archive/copyright references;
written-offer statement; then 17 canonical license texts (GPL-3, LGPL-3,
LGPL-2.1, Apache-2.0, Apache-2.0 + LLVM-exception, MPL-2.0, PSF-2.0,
BSD-3, BSD-2, MIT, ISC, Zlib, libpng-2.0, FTL, ICU, X11, OpenSSL) taken
verbatim from SPDX/gnu.org/apache.org.

Scope note: the notices file discharges attribution/text obligations
for the components it covers. It does **not** and cannot resolve the
PyQt6/QFluentWidgets combined-work question in §8 — the file says so
and defers to the project's release documentation.

Windows note: `RhythmAlign.spec` was **not** modified, so the Windows
build (released from its own pipeline) does not yet ship the notices
file; adding it to the Windows artifact is recommended for the next
Windows release (see §11/§17).

## 11. Existing Windows Distribution Implication

**The licensing finding in §8 applies to the existing Windows v1.2.0
distribution as well** — the Windows binaries bundle the same
PyQt6/QFluentWidgets/PyQt6-Frameless-Window GPL stack. This is an audit
finding only: no existing GitHub Release, asset, tag, or `update.json`
was altered, deleted, or rewritten in REL-0. The Owner may wish to
weigh the Windows and Linux distributions together when making the §8
decision.

## 12. Final RC Source Commit

| Field | Value |
|---|---|
| Final RC source commit | **`86c27b4`** (full SHA: `86c27b4a372dff5e1262dcd438bfca6fb1490d8b`) |
| Contains | CP-2 packaging work (`a2f5ede` lineage) + `68b2d01` (hardening tests) + `639d706` (desktop fix) + `86c27b4` (notices + draft release notes) |
| Tag target recommended | exactly this commit (§6) |

## 13. Final RC CI Build

| Field | Value |
|---|---|
| Pipeline | `.github/workflows/linux-build.yml` (production Linux CI), push-triggered |
| Run | **35561857077**, conclusion **success** |
| Jobs | "Build & validate (Ubuntu 22.04 container)" ✓ (3m16s) · "Validate on Ubuntu 24.04 runner" ✓ (48s) |
| Build commit | `86c27b4` — **identical to the RC source commit; no docs-only delta** (the commit that completed the source state is the commit CI built; the only later commit on the branch is this REL-0 report itself, which is not part of the product and is documented here) |
| Dependency stack | byte-identical `build-env-frozen.txt` to the CP-2 build (diff = empty) — no drift |
| Old artifact | `e953eeee…` / `c3096e61…` (ZIP) **not reused**, as required |

## 14. Final Artifact

| Field | Value |
|---|---|
| Filename | `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` |
| Size | 185,072,337 bytes |
| SHA256 | `88d300a85d0b9b13eb4f3d9f5350ea5918fc4806012c57bf2334b6af0cf6eae5` (matches the shipped `.sha256` sidecar) |
| CI run | 35561857077 (branch `cross-platform/linux`, commit `86c27b4`) |
| Archive contents | single top-level `RhythmAlign/` with the onedir build, `README-linux.txt`, `RhythmAlign.desktop`, **fixed** `install-desktop-integration.sh`, `LICENSE`, **`THIRD-PARTY-NOTICES.txt`** |
| Clean-room validation | see §15 |

## 15. Runtime Validation

Engine v2 expectation met **bit-identically** in all environments:

| Environment | Result |
|---|---|
| Ubuntu 22.04 container, glibc 2.35 (CI build job, this artifact) | `accepted / ACCEPT_DUAL_FAMILY / 2.995374149659864`, export 48.00→48.02 s, RESULT PASS |
| Ubuntu 24.04 runner (CI validation job, this artifact) | `accepted / ACCEPT_DUAL_FAMILY / 2.995374149659864`, export PASS, no-partial-leftovers PASS |
| WSL Ubuntu 24.04 (independent local full-workflow run of the freshly downloaded artifact) | PASS — deterministic +3.000 s pair, engine value identical, export verified, no `.partial` leftovers |
| Path-regression vs extracted artifact (`rock & roll` path) | PASS (§5) |

Additional checks on the fresh download: SHA256 recomputed vs sidecar;
`build-env-frozen.txt` byte-identical to the CP-2 build; bundled
desktop script verified to be the fixed version by content.

Compatibility smoke scope (per mission §15): the only runtime-relevant
changes since the Nightshift distro marathon are the packaging-script
escape fix, the notices file, and docs — no runtime files changed — so
the Nightshift Debian 12 / Fedora 41 / Ubuntu evidence remains valid;
this mission re-evidenced the glibc 2.35 floor (CI 22.04 container) and
a newer-glibc host (CI 24.04 + local WSL 24.04) on the exact RC build.

## 16. Windows Regression

- Full Windows suite re-run after integration: **122 passed / 3
  skipped** (§4), including every Windows-specific pin.
- Conditional packaged self-check (mission §16): **not triggered** — the
  REL-0 diff contains no shared/Windows-packaging input
  (`RhythmAlign.spec`, `RhythmAlign.iss`, `requirements.txt`,
  `update*.json`, engine/UI/updater/reveal modules all untouched since
  `a2f5ede`; verified via `git diff a2f5ede..86c27b4 --stat`). The only
  production file changed is the Linux-only packaging script; the
  notices file is not in the Windows `datas` set.
- Existing v1.2.0 Windows release, its assets, `update.json`, GPU
  behavior, updater, installer, reveal, and AppUserModelID: preserved by
  construction and pinned by tests.

## 17. Remaining Non-Blocking P3s

Preserved from NIGHTSHIFT-1 (§25 there; not fixed in REL-0 — the
priority was a clean RC):

1. **Output path == input path** silently overwrites the source in place
   (media-layer guard is ~three lines; UI already steers to `*_synced`).
2. **Close-during-export** and the **generic failure InfoBar** — small
   UI-surface improvements (Nightshift's highest-value next fixes).
3. **No FFmpeg timeouts** — a pathological input can hang the export
   thread; desktop exposure is bounded (user closes the app).
4. **Save-dialog extension inconsistency** and **stale GPU toggle visual
   state** — cosmetic.

New P3 recorded by REL-0:

5. **Add `.gitattributes` (e.g. `*.sh text eal=lf`)** — Windows checkouts
   with `core.autocrlf=true` materialize the packaging shell scripts
   with CRLF, breaking them when executed from a Windows checkout
   (reproduced by REL-0 in WSL; Linux CI and shipped artifacts are
   unaffected because they are produced from LF Linux checkouts).
   Trivial fix, but it has no regression test and touches checkout
   behavior for every platform, so it was documented rather than changed
   mid-RC. (Also worth adding `THIRD-PARTY-NOTICES.txt` to the Windows
   artifact `datas` at the same time.)

## 18. Draft Release Notes

`docs/RELEASE-NOTES-DRAFT-v1.2.0-linux-beta.1.md` — complete, **not
published**, with two clearly marked Owner-fill placeholders (SHA256,
source commit) and step-by-step publication instructions. Covers: beta
status, x86_64-only, glibc ≥ 2.35 + example distro families, portable
tar.gz with extraction/launch steps, optional desktop integration,
software-encoding-only / GPU unavailable, CJK font note, manual-update
policy, Windows-users-stay-on-stable note, license + notices pointers.

## 19. Public Release Gate

**READY_TO_PUBLISH_AFTER_OWNER_APPROVAL** — technically, the tagged
commit + artifact + draft notes are ready now. Publication remains
gated on (a) the Owner's §8 distribution decision and (b) the Owner's
release-identity approval (§6). **No publication occurred in REL-0**: no
tag, no release, no asset upload, no `update.json` change.

## 20. Git Evidence

| Item | Value |
|---|---|
| Starting SHA | `a2f5ededd9412fff872205e1fac3ba8375f79526` (== expected baseline) |
| Ending SHA | `86c27b4a372dff5e1262dcd438bfca6fb1490d8b` + this report commit (the report commit's only delta over the RC build commit is this file) |
| Commits created | `68b2d01` (cherry-pick of `42821a8`), `639d706` (cherry-pick of `e276859`), `86c27b4` (notices + draft release notes + packaging staging), plus this report commit |
| Pushed | `a2f5ede..86c27b4` → `origin/cross-platform/linux` (normal push, no force) |
| CI | run 35561857077 green on `86c27b4` |
| Not done (by design) | no merge to `main`, no tag, no release, no research-branch modification, no history rewrite |
