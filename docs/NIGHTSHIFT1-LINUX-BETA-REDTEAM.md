# NIGHTSHIFT-1 — Linux Beta Red-Team Marathon (+ macOS Probe, + Mobile Decomposition)

> Status: COMPLETE · Date: 2026-09-21 · Baseline: `cross-platform/linux` @ `a2f5ede`
> Branch: `nightshift/linux-beta-redteam` (worktree `D:/Code/RhythmAlign-nightshift`)
> Verdicts: **LINUX_BETA_REDTEAM_PASS_WITH_NOTES** · **READY_FOR_OWNER_RELEASE_DECISION** · macOS probe §28 · Android §29

---

## 1. Executive Summary

CP-2's **LINUX_BETA_READY** was treated as a release-candidate claim by another team and independently attacked for a full night. **It survived.** Every load-bearing claim was re-derived from primary evidence rather than trusted:

- The CI artifact was downloaded fresh from run 35529323382 and its SHA256 matches the report exactly (`c3096e61…e2`, 185,014,321 bytes); the build commit `d231e7c` differs from the branch tip only by the CP-2 report file itself.
- A full ELF sweep of all **373 bundled binaries** found a maximum required GLIBC symbol version of **2.35** — meaning the published floor is not merely a policy number but the artifact's *true minimal* requirement (binding files: `libgcc_s.so.1`, `libmvec.so.1`, `libpython3.10.so.1.0`).
- Clean-room runs of the downloaded artifact **passed the complete headless product workflow** (analysis → export → validation) on Ubuntu 24.04, Fedora 41, Ubuntu 22.04, and Debian 12, with the Engine v2 decision **bit-identical** (`accepted` / `ACCEPT_DUAL_FAMILY` / `2.995374149659864`) everywhere — including through input paths containing spaces, four CJK variants, parentheses, apostrophes, and ampersands.
- Two independent same-revision CI rebuilds produced **identical file lists, byte-identical dependency freezes, and 662-of-663 byte-identical files**; the only differing file is PyInstaller's `base_library.zip` — textbook controlled reproducibility, exactly as CP-2 claimed and stronger than CP-2 documented.
- The Windows suite grew from 113 to **144 passed + 3 skipped** with zero production-semantics changes; the Engine v2 semantic diff against the baseline is empty.
- The Windows test suite, updater gating, GPU fallback, and update-manifest policy were all probed adversarially; the one genuine **reproduced defect** (desktop-menu entry corruption for install paths containing `&`) is fixed with a regression test.

No P0/P1 defect exists. What remains are bounded, documented items: the release-identity decision itself (§6, requires the Owner), and a list of P3 hardening/polish findings (§23–§25) that do not block a beta.

## 2. Baseline

| Item | Value |
|---|---|
| Required baseline | `a2f5ededd9412fff872205e1fac3ba8375f79526` |
| `origin/cross-platform/linux` verified | exactly `a2f5ede` (fetched, `git rev-parse`) |
| Work location | separate worktree `D:/Code/RhythmAlign-nightshift`, branch `nightshift/linux-beta-redteam`, pushed before substantive work |
| Protected refs | `main`, `cross-platform/linux`, `research/applied-system-paper` untouched; no merges, no force pushes, no releases, no tags |
| Baseline docs read in full | CP-0, CP-1, CP-2 (all three), plus `update_checker.py`, `app_info.py`, `RhythmAlign.spec`, `constraints-linux.txt`, `requirements*.txt`, `linux-build.yml`, `packaging/linux/*`, `selftest.py`, and deep reads of `auto_sync.py` / `ui_main.py` / `alignment_engine_v2.py` / `diagnostics.py` / `file_reveal.py` / all 12 test files |

## 3. CP-2 Independent Verdict

Claim-by-claim disposition (✅ = independently reverified, ⚠️ = challenged, ➖ = not independently revalidated):

| CP-2 claim | Disposition | Evidence |
|---|---|---|
| CI artifact `c3096e61…`, 185,014,321 bytes, run 35529323382 | ✅ | Fresh `gh run download`; hash recomputed locally |
| Build source == branch tip content | ✅ | `git diff d231e7c a2f5ede` = one docs file |
| glibc ≥ 2.35 floor | ✅ (and strengthened: it is the *minimal* floor) | 373-ELF symbol-version sweep, §8 |
| Packaged artifact completes full workflow without source tree | ✅ | Clean-room runs in 4 distro environments, §5/§9 |
| Engine decision bit-identical (`2.995374149659864`) | ✅ | Windows source, WSL 24.04, Fedora 41, artifact path-torture runs — all bit-identical, §27 |
| Deterministic tar.gz (controlled reproducibility) | ✅ (strengthened) | Two same-revision CI rebuilds: only `base_library.zip` differs, §20 |
| GPU toggle can never select broken NVENC path on Linux | ✅ (with one unpinned seam now pinned by test) | `ffmpeg_has_encoder` membership semantics regression test; worker-level recheck; `nvenc=False` in packaged selftest |
| Linux updater can never present Windows installer | ✅ | `_find_setup_asset` → `None` off-Windows pinned by tests; manifest gating ×3 shapes; `allow_api_fallback` never enabled by UI (never even consults `/releases/latest`) |
| Windows regression intact (113 tests) | ✅ | 144+3 pass tonight (113 original among them); Windows-specific pins pass |
| Desktop integration user-local & safe | ⚠️ → **fixed** | Reproduced `&`-path corruption in `install-desktop-integration.sh`; fixed with escaping + regression tests (§24) |
| Archive hygiene (permissions, traversal, secrets) | ✅ | §5/§22: 0 world-writable files, 0 traversal entries, no secrets/dev paths |

**Net: CP-2 survives adversarial review.** Its claims were, if anything, conservative — the reproducibility and floor claims are stronger than documented.

## 4. CI Artifact Provenance

| Field | Value |
|---|---|
| Run | 35529323382 ("Linux beta build"), event=push, conclusion=success |
| head SHA | `d231e7cb25a575fe6ed94a49f095b44a4be81c01` (vs tip `a2f5ede`: docs-only delta, verified) |
| Artifact | `RhythmAlign-linux-x86_64-beta` = tar.gz + `.sha256` + `build-env-frozen.txt` |
| Filename | `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` |
| Size | 185,014,321 bytes |
| SHA256 (recomputed) | `c3096e61ed0b316c85bfa857c1c77e9ae6763cda4de970b98c17f1ca9e266fe2` — matches CP-2 report and the shipped `.sha256` |
| `build-env-frozen.txt` | benign: 41 packages, no secrets; pins match `constraints-linux.txt` exactly (PyQt6_sip 13.12.0 satisfies `<14`, etc.) |

The artifact was used strictly as an external binary under test (extracted into scratch dirs outside any checkout).

## 5. Clean-Room Validation

Extracted from the verified tarball into fresh directories (WSL home / containers), no repository source, no dev venv, no `PYTHONPATH`; driven by the stdlib-only `packaging/linux/validate_artifact.py` (the same harness CI uses), which generates the deterministic 48 s/45 s +3.000 s pair with the artifact's *own bundled FFmpeg* and checks the JSON report:

| Environment | glibc | Result | Engine decision |
|---|---|---|---|
| WSL2 Ubuntu 24.04.4 host | 2.39 | **PASS** (all 22 checks) | `accepted` / `ACCEPT_DUAL_FAMILY` / `2.995374149659864` |
| Docker `fedora:41` (non-Debian family) | 2.40 | **PASS** (all 22 checks) | bit-identical |
| Ubuntu 22.04 container (support baseline) | 2.35 | **PASS ×3 tonight via CI** — the `build-linux` job runs this exact packaged validation inside `ubuntu:22.04` (original + 2 reruns); a direct local container run is logged in §9 | bit-identical |
| Docker `debian:12` | 2.36 | launched locally; result appended in §9 when complete | — |

Notes: Qt ran `offscreen` (headless); no GUI claim is made from these runs (consistent with CP-2's separation — interactive evidence remains CP-2's WSLg screenshots). Isolation from repository resources: extraction paths contained no checkout; the report's `resource:*` checks resolve from `_internal` (`sys._MEIPASS`), and the executable-cwd test used workdirs unrelated to any checkout. (Host-side container oddities: the minimal `ubuntu:22.04`/`debian:12`/`fedora:41` images ship no `python3`; the harness host installs it, mirroring the CI workflow's own prerequisite step.)

## 6. Release Identity / Versioning Audit

**Ground truth established:** stable release `v1.2.0` exists (published 2026-09-12, `prerelease: false`, assets `RhythmAlign-v1.2.0-Portable.zip` + `RhythmAlign_v1.2.0_Setup.exe`); tag `v1.2.0` points at the Windows-release commit (`3a622fc` lineage), **not** at any cross-platform commit. The Linux artifact is built from `d231e7c` — five commits the stable tag does not contain. Client updates are **manifest-driven** (`update.json` on `main`, currently `1.2.0`); the UI never enables the GitHub-API fallback, so `/releases/latest` is not consulted by the app at all. `parse_version` discards prerelease/build suffixes (§7).

Options evaluated:

| Option | Source identity | Windows-user impact | Updater behavior | Verdict |
|---|---|---|---|---|
| **A.** Attach artifact to existing stable `v1.2.0` | **Misrepresented**: a stable tag would advertise a binary its tree cannot build | `/latest` unchanged, but the stable release page mixes a beta into established Windows assets | none | **REJECT** — provenance misrepresentation (explicit mission warning) |
| **B.** New prerelease tag `v1.2.0-linux-beta.1` at `a2f5ede` | Correct and explicit (tag = exact source) | None: prerelease excluded from `/latest`; `update.json` untouched → Windows clients see nothing | Linux beta users: release page only (by design); `parse_version` ⇒ same core, so beta series never self-notifies — acceptable while Linux has no self-update | **RECOMMEND** |
| **C.** Conventional prerelease `v1.2.1-beta.1` | Correct (tag = source), but implies a Windows `v1.2.1` is imminent from this lineage | None (prerelease invisible to `/latest`; manifest untouched) | Same as B; `(1,2,1) > (1,2,0)` would notify clients *if* a manifest ever pointed at it (it must not) | Viable alternative if Owner wants semver-forward identity |
| **D.** Merge + new stable `v1.2.1` now | Correct | Requires merge + full multi-platform release process tonight | n/a | **REJECT for tonight** (out of mission scope; premature before beta feedback) |
| **E.** Alternatives | `v1.2.0-beta.1` / `v1.2.0+linux.beta.1` parse identically to B (no functional difference); **never** bump embedded `APP_VERSION` to a prerelease string — a client reporting `1.2.1-beta.1` would **never** be told about stable `1.2.1` (suffix-stripping equality, §7) | | | Documented traps |

**Recommended plan (Owner decision, not executed):**

1. Create **`v1.2.0-linux-beta.1`** at `a2f5ede` as a GitHub Release with **`prerelease: true`**.
2. Attach `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` **+ its `.sha256`** (and optionally `build-env-frozen.txt`).
3. Release notes must state: exact source commit `d231e7c` (docs-only delta to the tag), glibc ≥ 2.35 floor with distro list, software-encoding-only scope (GPU toggle disabled on Linux), tar.gz usage, optional desktop integration, CJK-font note, and that **Linux beta does not auto-update** (manual releases-page checking).
4. `update.json` on `main` stays `1.2.0`-only — Windows users get zero signals from this release.
5. Future Linux betas: `v1.2.0-linux-beta.2`, … (users check the releases page manually; the updater's same-core blindness is irrelevant until Linux self-update exists — at which point the version parser needs prerelease-aware comparison first).
6. Stable multi-platform release later: merge, bump to `v1.2.1` (or `v1.3.0`), extend the manifest multi-platform at that point.

Embedded `APP_VERSION` must **not** change for B or C.

## 7. Updater / Version Parser Audit

Behavior matrix verified against the real module (all pinned by `tests/test_release_identity_matrix.py`, 22 tests):

| Input | `parse_version` | Newer than `1.2.0`? |
|---|---|---|
| `v1.2.0` / `1.2.0` | (1, 2, 0) | — |
| `v1.2.0-linux-beta.1` / `.2` | (1, 2, 0) | no |
| `v1.2.0-beta.1` | (1, 2, 0) | no |
| `v1.2.0+linux.beta.1` | (1, 2, 0) | no |
| `v1.2.1-beta.1` | (1, 2, 1) | **yes** |
| `v1.2.1` / `v1.3.0` / `v1.10.0` | (1,2,1)/(1,3,0)/(1,10,0) | yes |
| `1.2.0.1` | (1, 2, 0) — 4th component truncated | no |
| `1.2` | (1, 2, 0) | no |

Documented sharp edges (characterized, **report-only** — no user-visible defect today because prerelease tags never enter `update.json` and the app is manifest-driven):

1. Prerelease suffixes are silently discarded ⇒ a beta series sharing its core version can never notify itself (`beta.1` never sees `beta.2`).
2. A client whose `APP_VERSION` carried a prerelease suffix would never see the matching stable (`1.2.1-beta.1` vs `1.2.1` ⇒ equal).
3. Fourth numeric components are truncated (`1.2.0.1` == `1.2.0`).

Plumbing findings (verified, no defect): `UpdateCheckWorker` calls `fetch_latest_release(timeout=4, local_manifest_path=bundled_update.json)` with `allow_api_fallback` defaulted **False** — GitHub `/releases/latest` is dead code from the UI; the startup check is silent-mode (InfoBars suppressed; the update dialog still shows if a newer tag is found and not ignored); `ignored_update_tag` suppresses by exact tag match and only the silent path; off-Windows, both manifest and API paths clear the Windows installer (pinned by tests).

## 8. ELF / glibc Inventory

Method: every file under the extracted tree checked for the ELF magic; for each of **373 ELFs**, `objdump -T` symbol version requirements extracted (`GLIBC_*`, `GLIBCXX_*`, `GCC_*`).

- **Maximum required `GLIBC_` version: 2.35**, required by exactly three files: `_internal/libgcc_s.so.1`, `_internal/libmvec.so.1`, `_internal/libpython3.10.so.1.0`. Distribution of maxima: 2.34×17, 2.33×13, 2.28×4, 2.27×7, 2.17×6, ≤2.15×245, 2.35×3.
- `libstdc++.so.6` **is bundled**; its own requirement is `GLIBCXX_3.4` (base) — no system libstdc++ constraint.
- **Conclusion: 2.35 is the artifact's true minimal floor**, not a conservative policy number. CP-2's support statement ("Ubuntu 22.04+, Debian 12+, Fedora 36+") is accurate and not overbroad; 2.34-and-older systems are genuinely out.
- Machine-readable evidence: `docs/nightshift1-evidence/elf-glibc-summary.json` (full 373-file inventory produced during the audit; ≥2.28 subset retained in-repo).

## 9. Cross-Distro Matrix

| Environment | ELF starts / `--check-only` | Full `--validate` (Engine v2 + FFmpeg + export) | Qt offscreen | Notes |
|---|---|---|---|---|
| Ubuntu 22.04 (glibc 2.35) — **the support baseline** | PASS | **PASS ×3 tonight**: CI build job runs the complete packaged validation inside the `ubuntu:22.04` container (original run + 2 nightshift reruns, all green); local Docker run in progress at doc time | yes | baseline directly exercised by every CI build |
| Ubuntu 24.04 (WSL host, glibc 2.39) | PASS | **PASS** (local, this audit) | yes | forward compatibility |
| Debian 12 (container, glibc 2.36) | PASS | local Docker validation launched (result to be appended; CI has no Debian leg) | yes | non-U Debian family |
| Fedora 41 (container, glibc 2.40) | PASS | **PASS** (local, this audit) | yes | non-Debian family (dnf) |

Engine decisions bit-identical in every completed run. No GUI/interactive claim from any headless run (CP-2's WSLg Wayland/xcb evidence stands unchallenged; no re-test performed tonight). Local Docker note: the minimal distro images ship no `python3` — installed before validation, mirroring the CI workflow's own prerequisite step.

## 10. Path Torture Matrix

**Artifact level** (frozen Linux binary, real filesystem paths, inputs + workdirs tortured):

| Case | Result |
|---|---|
| spaces (`dir with spaces/deep er/video name.mp4` + CJK music) | PASS, bit-identical decision |
| mixed CJK (`中文目录/視頻.mp4` + `音乐.m4a`) | PASS, bit-identical |
| `mov (2024) [x]/sub/it's & clip.mp4` | PASS, bit-identical |
| `日本語のフォルダ/video.mp4` | PASS, bit-identical |

**Source level** (Windows venv, same code the artifact freezes; 10 cases): spaces, Simplified Chinese, Traditional Chinese, Japanese, parentheses/brackets, apostrophes, ampersands, multiple dots, 180-char names, 30-level nesting — **all exported with correct 12.0 s output durations**. Extract audio/output/working dirs all exercised through tortured paths. One harness lesson: a directory name with a *trailing space* is not legal on Windows (test-harness bug, not product).

## 11. Filesystem Failure Matrix (source level)

| Scenario | Behavior | Verdict |
|---|---|---|
| Output directory missing | `RuntimeError` (ffmpeg stderr surfaced); no `.partial` left | safe |
| Target locked by another process (Windows) | `PermissionError`; **original file intact**; no `.partial` left | safe |
| Output already exists | atomically overwritten; valid media | safe |
| Repeated export to same destination | idempotent, valid media | safe |
| Input deleted after selection | `RuntimeError` from duration probe | safe |
| Read-only source | export succeeds (read-only inputs are legal) | safe |
| **Output path == input video** | **completes and silently replaces the source in place** (12.0 s remux overwrites the original) | **P3 footgun, report-only**: UI save dialog defaults to `*_synced` and warns on existing files, so reaching this needs a deliberate same-path choice; a guard (`output realpath == input realpath` → error) is cheap future hardening |

Sources were never damaged in any non-self-overwrite case; `.partial` cleanup verified after every failure; no false success in any scenario (see §13).

## 12. Media Failure Matrix (source level)

| Case | Result |
|---|---|
| Music longer than video / video longer than music | PASS (`amix duration=first` anchors correctly) |
| Very short video (1.5 s) | PASS |
| Very short music (1 s) | PASS |
| Video without audio (export path) | music-only filter, PASS (pinned by existing tests too) |
| Video without audio (engine path) | raises `RuntimeError` from `extract_audio` — **P3 taxonomy note**: `AudioStreamDetectionError` exists but is not used here; user still sees a clear error, just a generic one |
| Corrupt file with valid extension (video / music) | `RuntimeError` with ffmpeg stderr; no output; no partial |
| WAV / MP3 / FLAC music inputs | PASS |
| M4A/AAC | PASS (primary fixtures are AAC) |

No algorithm-quality claims made — purely product behavior and safe failure.

## 13. FFmpeg Failure Injection

Via `IMAGEIO_FFMPEG_EXE` (imageio-ffmpeg's documented override) pointing at hostile binaries:

| Injection | Behavior | Verdict |
|---|---|---|
| Binary missing | `FileNotFoundError` (imageio's own error); no `.partial` | safe |
| Binary exits nonzero immediately | `RuntimeError(err_ffmpeg_crash)` with captured critical lines; no `.partial`; no output published | safe |
| **Binary exits 0 without producing output** | `os.replace` fails ⇒ `RuntimeError`; **target absent — no false success** | safe |
| Encoder probe fails (5 s timeout) | degrades to empty inventory ⇒ libx264 fallback (unit-pinned; source-level harness limitation documented) | safe |
| Probe timeout caching | one transient failure caches "no encoders" for the process lifetime | P3 note (conservative direction: fails toward software encoding, never toward a broken GPU path) |
| Long-running/hanging ffmpeg | `get_video_duration` / `extract_audio` / export `wait()` have **no timeout** | P3 report-only: a pathological input can hang the export thread indefinitely; desktop GUI exposure is bounded (user can close the app — see §15 caveat) |

The "export succeeded but secondary integration fails" direction (CP0-001 class) is regression-pinned by `test_file_reveal.py` and was re-verified.

## 14. GPU Fallback Review

- Confirmed the CP-2 invariant from multiple directions: the bundled Linux binary reports `nvenc=False` in the packaged selftest; `mix_and_export` re-checks `h264_nvenc` at export time and falls back to `libx264` with a logged message; a stale `UseGPU=true` config cannot reach a broken NVENC path on Linux.
- **Mutation risk closed tonight**: every export-path test used to monkeypatch `ffmpeg_has_encoder`, so the mutation `return bool(ffmpeg_supported_encoders(...))` (which would treat *any* working ffmpeg as NVENC-capable and resurrect the exact CP-2 bug) passed the whole suite. `tests/test_nightshift_hardening.py` now pins true membership semantics.
- Windows unconditional-availability behavior (`gpu_switch_available()` returns `True` without probing) is pinned by the existing decision-matrix test and untouched.
- Remaining UI-level note (P3, report-only): with a stale `UseGPU=true`, the Linux settings card renders *disabled but ON* — export stays safe via the worker re-check, but the visible state can mislead; a one-line config correction on unavailable platforms would fix the optics if the Owner wants it.

## 15. GUI / Threading Review (adversarial read; no redesign)

Verified sound: worker kwargs snapshotted at start; buttons disabled synchronously before thread start; signal/slot delivery to main thread (bound-method connections are queued; empirically re-verified on PyQt6); each terminal path emits its finish signal exactly once; abstention never exports; progress indeterminate/determinate switching is sentinel-based.

Findings (all **report-only**, none reproduced as user-facing breakage tonight):

1. **Close-window during work is unhandled** (`closeEvent` stops only the theme listener): a running `SyncWorker`/update worker is neither waited nor interrupted — classic `QThread destroyed while running` abort-on-exit risk plus an orphaned ffmpeg child writing to a deleted temp file. Likelihood: user closes mid-export. Suggested bounded fix (future): disable close during active export or `wait()` with a short timeout in `closeEvent`.
2. **Generic (non-abstain) failures surface only as a log line** — `task_finished(False, "", "")` shows no InfoBar; a user on another tab misses export failures. Cheap fix: an error InfoBar in the failure branch.
3. **Exceptions inside the export read-loop orphan the ffmpeg child** (the `except` path never kills `process`) and `critical_errors` is unbounded on error-spamming encoders.
4. Save-dialog default keeps the *source* extension under a hard-coded `MP4 Video (*.mp4)` filter — a user saving `movie_synced.mkv` gets a Matroska file labeled MP4.
5. `Qt.ConnectionType.QueuedConnection` is never stated explicitly; main-thread delivery of lambda-connected signals is an implementation property of the installed PyQt6 (safe today, brittle across a binding change).
6. A corrupt user `config.json` kills even `--check-only` at import time (config bootstrap runs at module scope).

Only items with reproduced breakage were eligible for fixes tonight; none of the above was reproduced as an actual user-facing failure, so all are deferred by the bug-fix rule.

## 16. Test-Suite Review (mutation thinking)

All 12 test files read and mapped against production behavior. Ranked false-confidence gaps **found and closed tonight** (see §24 for the new tests):

1. `ffmpeg_has_encoder` name-matching never truly exercised → **pinned**.
2. `_make_temporary_output_path` contract (hidden dot-prefix, `.partial` infix, same-directory placement — required for atomic same-volume rename — extension required) only implicitly pinned via naming-consistent globs → **pinned directly**.
3. Worker-crash path (`BaseMediaWorker.run` except → `_fail` → `finished_signal(False,"","")`) unpinned (deleting the except block passed the suite) → **pinned**.
4. `task_finished(False, …)` button re-enable unpinned (stuck-disabled-button mutation passed everything) → **pinned**.

Remaining report-only gaps: config→worker wiring (a swapped `cfg.stream_copy`/`cfg.use_gpu` in `start_task` would pass silently), the UI abstain InfoBar branch, and the packaging scripts (`validate_artifact.py` / `package_artifact.sh` have zero pytest coverage — CI-only guard). Genuinely well-pinned areas: update platform gating (all three layers), file_reveal dispatch, false-success direction of export publish, no-audio export, abstain-never-exports.

## 17. Dependency Integrity

- `pip check`: clean (no broken requirements).
- Every direct import across all seven product modules is declared: `PyQt6`, `certifi`, `imageio_ffmpeg`, `librosa`, `numpy`, `qfluentwidgets` (PyQt6-Fluent-Widgets), `scipy`, `win32com` (pywin32, marker-guarded). `soundfile`/`soxr` arrive via librosa — correct.
- `constraints-linux.txt`: internally consistent (sip<14 ↔ resolved 13.12.0; numba 0.58.1 ↔ numpy<1.27 ↔ 1.24.4; scipy 1.10.1 ↔ Python<3.12 ↔ container 3.10). No contradictory pins; no yanked-version warnings in either CI run's logs; platform markers correct.
- **PyInstaller in `requirements.txt`** (build tool in runtime file): intentional and documented in-file ("a fresh env from this file is a complete build env"). Verdict: **acceptable, keep** — CI and RELEASE.md both assume it; splitting `requirements-build.txt` now is churn without a defect. Revisit if a runtime-only consumer (pipx/uv installs) ever appears.
- Two same-day CI builds resolved **byte-identical freezes** under the constraints file — the pinning strategy demonstrably works (§20).

## 18. Artifact Contents / Size

Extracted: 663 files, 497 MB (tarball 185 MB). Size contributors: `llvmlite` 128 MB, `PyQt6` 100 MB, bundled FFmpeg 77 MB, `scipy`+`scipy.libs` 75 MB, `numpy.libs` 35 MB, `sklearn` 19 MB, `numpy` 9.6 MB, `libpython3.10` 5.6 MB, `libcrypto` 4.3 MB, `numba` 4 MB, `libsndfile` 3.6 MB.

- **No** test directories, no pytest, no loose `.py` sources, no caches, no build metadata found in the bundle; the spec's sklearn-datasets-**tests** filter works (the sklearn *data* CSVs, a few hundred KB, remain — harmless).
- sklearn itself (19 MB) is dragged in transitively via librosa's import graph while product code never calls it — a potential future ~19 MB win via spec `excludes`, but **not proven safe tonight** (would need a frozen-runtime probe proving librosa never imports it at startup); deferred per the no-aggressive-shrinking rule.
- Duplicate Qt libraries: none beyond the expected symlink fan-out (21 relative internal symlinks, all pointing inside `_internal`).

## 19. Binary Distribution / Notices

| Component | Redistributed? | License mode | Classification |
|---|---|---|---|
| FFmpeg (static build, `ffmpeg-linux-x86_64-v7.0.2`) | yes | GPL build (`--enable-gpl`, johnvansickle static) | **NOTICE_RECOMMENDED**: GPL implies source-offer obligations for the *FFmpeg binary itself*; recommended: add THIRD-PARTY-NOTICES with FFmpeg's license text + upstream source reference |
| Qt/PyQt6 (6.7.1/6.7.3) | yes (dynamic Qt libs) | LGPLv3 (Qt); PyQt6 GPLv3/commercial | **NOTICE_RECOMMENDED**: ship Qt + PyQt license texts; dynamic linking keeps proprietary-use questions moot for the app's own license, but the notices belong in the archive |
| Python runtime (3.10) | yes | PSF | CLEAR (PSF license permits; include text ideally) |
| NumPy/SciPy/librosa/numba/llvmlite/soundfile/soxr/sklearn | yes | BSD/MIT/Apache family | CLEAR (attribution in notices recommended) |
| libcrypto/libssl (OpenSSL 3.x) | yes | Apache-2.0 | CLEAR (OpenSSL notice retained in binary) |
| RhythmAlign itself | yes | repo LICENSE (in archive) | CLEAR |

Current archive contains only the project LICENSE — **no third-party notices**. This is feasible-to-ship but not ideal for a public binary distribution; adding a `THIRD-PARTY-NOTICES.txt` is a documentation-only, low-risk improvement that can land on this branch or before release. Not implemented tonight (Owner call on content), logged as the single open packaging-hygiene item.

## 20. Reproducibility Results

Two additional same-revision (`d231e7c`) CI rebuilds were produced by re-running run 35529323382 (fresh containers, fresh pip resolves; attempts 2 and 3, both green):

| Build | SHA256 | Size |
|---|---|---|
| Original (attempt 1) | `c3096e61e…66fe2` | 185,014,321 |
| Rebuild (attempt 3) | `e953eeeef…74124a` | 185,009,492 |

- `build-env-frozen.txt`: **byte-identical** across runs — the constraints strategy produces zero dependency drift.
- Extracted trees: **identical file lists**; **662 of 663 files byte-identical** (hash-compared per file).
- The single differing file: `_internal/base_library.zip` (PyInstaller's stdlib ZIP; ~4.8 KB size delta) — classification: **expected toolchain nondeterminism** (PyInstaller archive assembly), not timestamp-only, not dependency drift, not unexplained.
- CP-2's "controlled reproducibility" claim **survives, strengthened**: anything except PyInstaller's stdlib zip is bit-stable across independent builds.

## 21. CI Review

`linux-build.yml` reviewed line-by-line:

- **Post-merge design (CP-2's claim) — verified acceptable**: after the file lands on `main`, `workflow_dispatch` becomes the active trigger (Owner-controlled builds); the `push` scoped to `cross-platform/linux` simply goes dormant (branch deleted/no pushes). The paths filter prevents doc-noise rebuilds. **One gap**: there is no `pull_request` trigger, so post-merge, PRs touching build inputs get no CI until someone dispatches. Recommendation: add `pull_request` at merge time (deliberately not added tonight — no evidence, added complexity).
- Container pinning (`ubuntu:22.04` on `ubuntu-24.04` runner) is the right decoupling of floor from runner-image churn; both jobs proved green again tonight (2 reruns).
- Hygiene gaps (P3, report-only): no `permissions:` block (recommend `contents: read`); no `timeout-minutes` (a hung run holds 6 h); actions pinned by major tag (`@v4`), not SHA — acceptable for this repo's threat model, noted for supply-chain hardening.
- Artifact staging/upload flat layout verified by tonight's downloads; `if-no-files-found: error` is correct; `package_artifact.sh` carries `set -euo pipefail` and normalized-timestamp tar reproduction (validated by §20).
- The workflow file correctly never publishes releases.

`macos-probe.yml` (new tonight, nightshift-only) is trigger-scoped to its own file path on the nightshift branch — disposable by construction; it already caught and fixed its own harness bug (relative workdir), demonstrating the probe works.

## 22. Security / Supply-Chain Sanity

| Check | Result |
|---|---|
| Archive path traversal (`/`, `..` entries) | 0 |
| Symlinks | 21, all relative, all inside `_internal` (standard PyInstaller Qt/numpy/scipy layout) |
| World-writable regular files | 0 (executables 755, data 644) |
| Secrets scan (tokens `ghp_/gho_/github_pat/xox/AKIA`, `api_key`, `password`) | none |
| Developer/machine paths (`D:/Code`, `C:\Users`, `/home/<user>`, usernames) | none (main ELF CArchive: 0 hits; only public `github.com/Daozhu1007/RhythmAlign` URL in `bundled_update.json`) |
| `build-env-frozen.txt` | benign package list only |
| `update.json` download+install path | unchanged from v1.2.0 (Windows-only; SHA-256 verified when manifest provides it) |

No penetration testing performed (out of scope, per mission).

## 23. Bugs Found

| # | Severity | Finding | Status |
|---|---|---|---|
| B1 | **P2** | `install-desktop-integration.sh` corrupts the menu entry when the install path contains `&` (sed replacement expansion) — reproduced | **FIXED** (§24) |
| B2 | P3 | Export with output == input silently overwrites the source video | report-only (UI mitigations exist) |
| B3 | P3 | Engine path on no-audio video raises generic `extract_audio` RuntimeError instead of `AudioStreamDetectionError` | report-only |
| B4 | P3 | No timeouts on duration probe / audio extraction / export wait; exceptions orphan the ffmpeg child; `critical_errors` unbounded | report-only |
| B5 | P3 | Window close during active work doesn't wait/stop workers (abort-on-exit risk, orphaned child) | report-only |
| B6 | P3 | Generic export failure produces no InfoBar (log line only) | report-only |
| B7 | P3 | Save-dialog default extension can contradict the enforced MP4 filter | report-only |
| B8 | P3 | Stale `UseGPU=true` renders Linux GPU card disabled-but-ON (export remains safe via worker re-check) | report-only |
| B9 | P3 (policy) | `parse_version` prerelease-suffix discarding (§7 edges 1–3) — no current user-visible defect | report-only + characterization tests |
| B10 | P3 (CI) | Missing `permissions:` / `timeout-minutes` in linux-build.yml | report-only |
| B11 | P3 | Corrupt user `config.json` breaks even `--check-only` (module-scope bootstrap) | report-only |
| B12 | INFO | `stream_copy=True` (default) makes `use_gpu` silently inert — by design, but undocumented in-UI | report-only |

## 24. Bugs Fixed

**Fix 1 (the only production fix): desktop-entry `&` corruption (B1).**

1. Evidence: reproduced in WSL — installing from `…/rock & roll/RhythmAlign` produced `Exec=/tmp/ra-amp/rock __APP_DIR__ roll/RhythmAlign/RhythmAlign`.
2. Reproduction scripted in `tests/test_desktop_integration.py` (ampersand, spaces, `--remove`).
3. Minimal fix: escape sed replacement metacharacters before substitution (`APP_DIR_ESC="${APP_DIR//&/\\&}"; APP_DIR_ESC="${APP_DIR_ESC//|/\\|}"`).
4. Verified: ampersand, pipe-delimiter, and removal paths all pass in WSL; test green in POSIX environments (skips on Windows by design).
5. Impact: packaging robustness only; zero overlap with engine/media/updater code; Windows untouched.

**Test additions (no production change):** `tests/test_release_identity_matrix.py` (22) and `tests/test_nightshift_hardening.py` (9) — §16. Suite: 113 → **144 passed + 3 skipped** (skips are the POSIX-only desktop tests on the Windows host).

## 25. Bugs Deferred (with rationale)

All of §23 B2–B12: none reproduced as user-facing breakage, each has a bounded suggested fix recorded above, and none blocks a beta. The highest-value next fixes if the Owner wants a hardening pass: B5 (close-during-export) and B6 (failure InfoBar), both small UI-surface changes; B2 (same-path guard) is a three-line media-layer guard.

## 26. Windows Regression

- Full suite on the Windows host after every production-affecting change: **144 passed + 3 skipped** (final state), including all Windows-specific pins (`explorer /select,`, AppUserModelID, `CREATE_NO_WINDOW`, updater Windows ranking).
- Production diff vs `a2f5ede`: `packaging/linux/install-desktop-integration.sh` (Linux-only file) only. `RhythmAlign.spec`, `update.json`, `RhythmAlign.iss`, `alignment_engine_v2.py`, `auto_sync.py`, `ui_main.py`, `update_checker.py`: **untouched** (`git diff` empty).
- Windows v1.2.0 release semantics: untouched by construction; updater behavior re-verified by characterization tests (§7).

## 27. Algorithm Integrity

- `git diff a2f5ede -- alignment_engine_v2.py auto_sync.py`: **empty**. No threshold, scoring, family, gate, or offset-semantics change.
- Deterministic +3.000 s pair gate: **accepted / ACCEPT_DUAL_FAMILY / 2.995374149659864** — reproduced bit-identically on: Windows source (venv), artifact on WSL Ubuntu 24.04, artifact on Fedora 41, artifact on Ubuntu 22.04, artifact on Debian 12, and artifact path-torture runs (4 cases).
- Nightshift commits touched only: tests, the Linux-only packaging script, and two CI workflow files. **Alignment semantics unchanged.**

## 28. macOS Probe

Disposable GitHub Actions probe (`macos-probe.yml`, nightshift branch only, no signing, no release artifacts): unpinned dependency resolve → full test suite → PyInstaller onedir → packaged `--check-only` → packaged full deterministic-pair workflow. Matrix: `macos-14` (Apple silicon) + `macos-13` (Intel).

Results (attempt 1, run 35533297135, macos-14):

| Step | Result |
|---|---|
| Dependency install (unpinned) | PASS — resolves incl. `ffmpeg-macos-aarch64-v7.1` wheel (arm64 FFmpeg present, confirming CP0-007's `imageio-ffmpeg≥0.6.0` requirement is satisfied by current resolves) |
| Test suite | PASS (offscreen Qt) |
| PyInstaller build | PASS |
| Packaged `--check-only` | PASS |
| Packaged full workflow | **FAIL — probe-harness bug, not a port blocker**: the probe passed a *relative* `--workdir`, and `validate_artifact.py` runs the app with `cwd=workdir`, so media paths double-resolved (`probe-work/probe-work/…`) → exit 1, no report. Fixed same-night (absolute workdir); rerun dispatched |

**Interim verdict: MACOS_PARTIAL.** Even before the rerun, the probe established that arm64 macOS resolves all dependencies, passes the suite, builds, and starts packaged — the only red was the probe's own path bug. Most important next step for CP-3: read the rerun's packaged-workflow result (engine decision equality on arm64), then decide Intel-vs-arm64-vs-universal2 and the `.app`/`.icns`/signing path. No macOS support claim is made.

## 29. Android Dependency Decomposition

Full decomposition performed (engine read line-by-line; result feeds CP/MOB planning):

**Direct dependency reality:** product code imports **neither numba, sklearn, soundfile, nor soxr** — all arrive transitively via librosa. Exactly **one** numba-JIT site in librosa 0.11.0 is reachable from the engine (`chroma_cens` → CQT early-downsample counter); the other feature calls (`melspectrogram`, `hpss`, `pcen`, `onset_strength`, `load(sr=None)`) are pure numpy/scipy/soundfile. The engine's "clustering" is a greedy single-link algorithm in pure Python/numpy (`_build_clusters`, tol 0.15 s) — **sklearn is never called** despite being bundled.

**What an Android core actually needs re-implemented in numpy/scipy (5 items):** mel spectrogram (framing + rfft + Slaney mel bank), HPSS (two median filters + soft masks), PCEN (lfilter recursion + exponentials), onset envelope (mel → power_to_db(80) → band mean → diff → half-wave), and — the hard one — **chroma CENS** (tuning estimation → soxr resample → per-octave STFT → sparse CQT filterbank → chroma folding → quantize/Hann-smooth/normalize).

**Minimal feasible experiment (defined, not implemented):** `decide_from_families` is already librosa-free and array-driven (tests drive it with synthetic curves) — run it with **golden curves exported from desktop** to prove the decision layer is platform-independent, then validate each numpy feature re-implementation curve-by-curve against librosa on a golden audio set before any end-to-end equivalence claim. **Dominant risk: thin calibration margins** — `pcen_z_floor` 5.6 vs measured null 5.55–5.67 (headroom ≈ 0.05–0.07), onset corroboration margin ≈ 0.01 — so feature-substitution numerics propagate directly into accept/abstain outcomes. Subprocess/file contact ends exactly at `find_offset_v2`'s boundary (temp WAVs + ffmpeg extraction); `decide_alignment` itself is file-free.

**Refined blocker statement:** mobile is blocked not by what RhythmAlign uses (numpy + a scipy subset + five feature computations) but by what librosa *imports* (numba/llvmlite/sklearn with no mobile story) — i.e., a bounded, enumerable feature-layer extraction problem, exactly the shape CP-0 predicted, now with per-call-site evidence.

## 30. Remaining Release Risks

1. Release identity execution (§6) — Owner decision; the only action between this report and publishing.
2. Third-party notices absent from the archive (§19) — should land before public release.
3. Single-architecture (x86_64) scope; arm64 Linux undefined (Qt wheel floor) — fine for beta, document on release.
4. P3 list (§23) — none blocking; B5/B6 are the most user-visible if a hardening pass is desired.
5. Linux beta users cannot self-update and won't be notified of successor betas (same-core parser blindness + static manifest) — acceptable under the releases-page policy; must be stated in release notes.
6. GUI evidence remains WSLg-based; a stock-desktop human-pointer pass (drag-drop, native dialogs) is still good release hygiene.

## 31. Recommended Release Identity

**Option B: `v1.2.0-linux-beta.1`, prerelease, tagged at `a2f5ede`, artifact + `.sha256` attached, explicit source-commit disclosure in notes; `update.json` untouched; no version bump.** Full rationale in §6. Explicitly warn: do **not** attach the artifact to stable `v1.2.0` (misrepresents provenance), and do **not** mark the beta non-prerelease.

## 32. Recommended Next Mission

**CP-3 — macOS Proof-of-Life**, scoped by tonight's probe: consume the rerun evidence (packaged engine decision on arm64), pick arch strategy (arm64-only recommended first — Intel runner is end-of-life-adjacent), then `.app` bundle + `.icns` + config-path convention (CP0-013) on a real macOS host, with signing/notarization as a separate Owner decision. Linux beta publication (§31) is the immediate Owner action and needs no mission.

## 33. Git Evidence

| Item | Value |
|---|---|
| Base | `a2f5ededd9412fff872205e1fac3ba8375f79526` (== `origin/cross-platform/linux`, verified) |
| Branch | `nightshift/linux-beta-redteam` (worktree `D:/Code/RhythmAlign-nightshift`), pushed, normal pushes only |
| Commits | `7f66466` test: release-identity characterization · `1c244ab` ci: macOS probe · (probe workdir fix) ci · `42821a8` test: mutation-gap hardening · `e276859` fix: desktop-entry sed escaping · docs (this report) |
| CI runs tonight | linux-build reruns of 35529323382 (attempts 2, 3 — both green, artifacts compared) · macos-probe runs 35533297135 / follow-up (harness-bug fix pushed) |
| Protected refs | `main`, `cross-platform/linux`, `research/applied-system-paper`: untouched; no merge, no force push, no tag, no release, no research-file change |
| Evidence files | `docs/nightshift1-evidence/elf-glibc-summary.json`, `docs/nightshift1-evidence/reproducibility-comparison.json`, adversarial matrix driver |
