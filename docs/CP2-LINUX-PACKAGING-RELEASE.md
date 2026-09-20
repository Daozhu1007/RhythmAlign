# CP-2 — Linux Packaging & Release Engineering (RhythmAlign v1.2.0)

> Status: CP-2 COMPLETE · Date: 2026-09-21 · Verdict: **LINUX_BETA_READY**
> Branch: `cross-platform/linux` (2b100c1 + 581b86f on f89ba72, clean base verified)
> Companion evidence (local, gitignored): `results/cp2/` — CI logs, screenshots, sha256, build env freeze.

---

## 1. Executive Summary

RhythmAlign now has a **reproducible Linux x86_64 beta build pipeline** that produces a **user-consumable artifact** from a clean source checkout: pinned build environment → production PyInstaller onedir → deterministic `tar.gz` with checksum → headless runtime validation of the packaged build → GUI verification.

The core acceptance question is answered **YES**: CI can produce a Linux x86_64 beta artifact against an explicitly defined baseline (**glibc ≥ 2.35**), and the packaged artifact completes the full product workflow — Engine v2 analysis on real media, export, and output validation — without the source tree, with the engine decision **bit-identical** to the CP-1 reference (`accepted`, offset `2.995374149659864`, `ACCEPT_DUAL_FAMILY`).

Two product-safety gaps that would have produced broken Linux beta experiences were closed with small, tested, Windows-preserving changes: the "Use GPU" toggle can no longer select a predictably-broken NVENC path on Linux, and the Linux updater can never present a Windows installer as the update.

Public release remains a separate Owner decision (§27 of the mission); nothing was published.

## 2. Starting State

| Item | Value |
|---|---|
| Branch / HEAD at start | `cross-platform/linux` @ `f89ba7293d9fd4d9faae251ac325075a148aab47` (verified, clean, synced) |
| Prior phases | CP-0 `READY_FOR_DESKTOP_PORT` · CP-1 `LINUX_PROOF_CONFIRMED` · CP-1.1 94/94 both platforms |
| CI at start | none (no `.github/` directory existed) |
| Windows state | v1.2.0 released; release process Windows-host-only per `RELEASE.md` |
| Ending HEAD | `581b86f` (see §22 Git) |

## 3. Supported Linux Baseline

**Policy statement: the Linux x86_64 beta is built against glibc ≥ 2.35.**

| Item | Decision | Evidence |
|---|---|---|
| Build environment | `ubuntu:22.04` container pinned on a `ubuntu-24.04` runner | Runner-label lifecycle is decoupled from the build: `ubuntu-latest` migrates to 26.04 by 2026-11-19 and the bare `ubuntu-22.04` label is on a deprecation path, so the workflow does **not** trust runner images; the Docker Hub `ubuntu:22.04` image is upstream-supported until April 2027 |
| glibc floor | **2.35** | The build host is the binding constraint (classic manylinux practice: every runtime wheel floor verified ≤ 2.34 — PyQt6-Qt6 6.7.3 `manylinux_2_28`, numpy/scipy/numba/soxr `manylinux_2_17`, soundfile `manylinux_2_28`, PyInstaller/imageio-ffmpeg `manylinux2014`; even the newer PyQt6-Qt6 6.11.2 x86_64 is `manylinux_2_34`) |
| Distributions covered | Ubuntu 22.04+, Debian 12+, Fedora 36+, Linux Mint 21+, equivalents by libc | Ubuntu 20.04-class (glibc 2.31) is **out**: its standard support ended 2025-04, and a 2.31 floor would force building inside an EOL container for a shrinking population |
| Architecture | x86_64 only (beta) | arm64 is a future decision (PyQt6-Qt6 aarch64 wheels have a higher glibc floor, CP-0 §12) |
| Python | **3.10** (distro python3.10 in the container) | Matches the released Windows v1.2.0 stack (3.10.11); `scipy==1.10.1` requires Python < 3.12; avoids deadsnakes PPA maintenance in CI |
| PyQt6/Qt | 6.7.1 / 6.7.3 | Parity with the released Windows v1.2.0 build; newer Qt 6.11 (CP-1's unpinned resolve) works but was not needed |
| imageio-ffmpeg | 0.6.0 (`ffmpeg-linux-x86_64-v7.0.2` static, libx264) | The exact CP-1-proven Linux binary; Windows release builds keep their own 0.5.1/7.1 environment |
| GitHub Actions runners | available (24.04) | Container approach survives runner-image churn |
| Containerized building | **chosen** | See above; also makes local "which Ubuntu is the runner" irrelevant |

Not selected: Ubuntu 24.04 build host (would set a glibc 2.39 floor — "too new to casually define as the release floor" per CP-1), Alma/Rockley 8-class 2.28 floor (maximum breadth, but EOL-adjacent base and no product demand yet).

## 4. Dependency Reproducibility Strategy

**Chosen strategy: `requirements.txt` remains runtime minimums; a new root `constraints-linux.txt` pins the release-critical and engine-affecting stack for Linux release builds.** Install pattern:

```
pip install -r requirements.txt -r requirements-dev.txt -c constraints-linux.txt
```

Rationale (per mission §8 — stabilize release-critical tools, don't pin every transitive):

- **Pinned exactly**: the scientific stack that touches engine behavior (numpy 1.24.4, scipy 1.10.1, librosa 0.11.0, numba 0.58.1, llvmlite 0.41.1, soundfile 0.13.1, soxr 0.3.7) — the same generation the released Windows v1.2.0 shipped; the bundled-FFmpeg provider (imageio-ffmpeg 0.6.0); the Qt stack (PyQt6 6.7.1, PyQt6-Qt6 6.7.3, PyQt6-sip<14, PyQt6-Fluent-Widgets 1.11.1); the build tool (PyInstaller 6.22.3); pytest<9 to keep CI from jumping majors.
- **Left floating**: pure-transitive helpers (pooch, joblib, cffi, …) and certifi (CA data only) — no material effect on the artifact.
- Evidence recorded per CI run: `build-env-frozen.txt` (`pip freeze`) is uploaded next to the artifact.
- Two CI builds of the same revision now receive the same material build stack; CP-1's "fresh Linux installs resolved significantly newer dependencies" risk is closed for release builds.
- Windows release builds are **unchanged** (RELEASE.md process; constraints file is Linux-build-specific).

New finding fixed en route: **PyInstaller was an undeclared build dependency** (requirements.txt never named it — same defect class as CP0-002/pywin32). It is now declared (`PyInstaller>=6.18`) so a fresh env from `requirements.txt` is a complete build env.

## 5. Production Build Architecture

```
clean checkout
  → ubuntu:22.04 container (CI) or pinned py3.10 venv (local)
  → pip install -r requirements.txt -r requirements-dev.txt -c constraints-linux.txt
  → pytest tests/ -q                       (offscreen Qt)
  → pyinstaller RhythmAlign.spec --clean --noconfirm
  → packaging/linux/package_artifact.sh    (staging + deterministic tar.gz + sha256)
  → packaging/linux/validate_artifact.py   (drives the extracted artifact end-to-end)
  → upload workflow artifact (tar.gz + .sha256 + build-env-frozen.txt)
```

Single production spec, platform-aware (§6). No Linux-specific spec fork exists.

## 6. PyInstaller Configuration

`RhythmAlign.spec` was audited and made minimally platform-aware:

- **`upx` is now `_IS_WINDOWS_BUILD`** (`sys.platform == "win32"`): Windows keeps UPX exactly as the release process expects; Linux builds skip UPX unconditionally so the artifact never depends on whether the build host has an `upx` binary. This is the only functional spec change.
- Verified unchanged on Linux: datas (assets/locales/config.json/bundled_update.json/certifi/metadata), `console=False` (windowed ELF), onedir `_internal` layout, Qt plugin collection (wayland/**xcb**/offscreen plugins all collected), FFmpeg auto-bundling via imageio-ffmpeg, dev/test-data exclusion (`pytest`, `_PySide6`; sklearn datasets/tests filter).
- Windows impact: explicitly verified — full Windows rebuild with the modified spec succeeds and the packaged `RhythmAlign.exe --check-only` passes (§18).
- Cosmetic Linux build note: PyInstaller logs `Ignoring icon; supported only on Windows and macOS` — expected; the ELF gets its icon from `assets/logo.png` at the desktop-integration layer.

The Linux executable launches from the packaged artifact with no source tree (proven in validation below: extraction into a scratch dir, GUI + headless runs).

## 7. Artifact Format Decision

**Primary (only) beta artifact: portable `tar.gz` of the PyInstaller onedir build.**

- `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` — naming follows mission §20 with an explicit `beta` marker outside the embedded product version (`APP_VERSION` remains 1.2.0; no false stable labeling).
- Contents: one top-level `RhythmAlign/` directory (ELF + `_internal/`) plus `README-linux.txt`, `RhythmAlign.desktop`, `install-desktop-integration.sh`, `LICENSE`.
- **Why tar.gz**: zero extra tooling, fully scriptable in CI, reliable, trivial to explain ("download, extract, run"), preserves executable bits, and matches the Windows portable-ZIP philosophy. AppImage was evaluated and deferred: it adds tooling (appimagetool/runtime), FUSE/`--appimage-extract` caveats, and another moving part for marginal benefit over an already-portable archive — not justified for a first beta (mission §11 default bias honored).
- deb/Flatpak: conceptually reviewed, not implemented — no evidence of necessity for the beta.
- Reproducibility hygiene: staging timestamps normalized, `tar --sort=name --owner=0 --group=0 --numeric-owner`, `gzip -n`; checksum recorded as `.sha256`. (PyInstaller output is not bit-reproducible; "reproducible" here means the pinned-stack/build-path property per §4.)

## 8. Desktop Integration

Bounded, **user-local, optional**:

- `RhythmAlign.desktop` template (absolute `Exec`/`Path`/`Icon` via `__APP_DIR__` placeholder; `Categories=AudioVideo;AudioVideoEditing;Audio`; `StartupWMClass=RhythmAlign`; icon = existing `assets/logo.png`, no new branding).
- `install-desktop-integration.sh [--install|--remove]`: writes only `$XDG_DATA_HOME`/`~/.local/share/applications/rhythmalign.desktop`; nothing system-wide; the app itself never writes these paths during normal launch. Shipped inside the archive.

## 9. Wayland / X11 Assessment

| Backend | Evidence | Notes |
|---|---|---|
| **Wayland** | Packaged artifact launched and rendered on real WSLg Wayland (desktop screenshot `results/cp2/gui/win_desktop_wayland.png`; process alive, only benign Mesa/EGL software-rendering warnings on stderr) | Works out of the box; Qt wayland plugin bundled |
| **X11/xcb** | Packaged artifact launched and rendered via xcb/XWayland after installing the xcb runtime libs (desktop screenshot `results/cp2/gui/win_desktop_xcb.png`) | The xcb plugin **is bundled**; it requires **distro-provided** runtime libs, not bundled ones: `libxkbcommon-x11-0`, `libxcb-cursor0` (pulls `libxcb-util1`), `libxcb-icccm4`, `libxcb-image0`, `libxcb-keysyms1`, `libxcb-render-util0`, `libxcb-xkb1` |

- On normal desktop distributions these xcb libraries are preinstalled; on **minimal** systems (containers, bare WSL) the missing-lib failure mode is a clear Qt error naming `libxcb-cursor0` (documented in `README-linux.txt` with the exact package names). A missing optional xcb lib on a minimal container does not fail Linux support — Wayland and offscreen work without them.
- No arbitrary system libraries are bundled; Qt loads system xcb libs by design (licensing/runtime-clean).
- CI verifies headless (offscreen) on the build baseline; interactive verification was performed on WSLg (this section).

## 10. CJK Font Policy

**Policy: rely on normal desktop distro fonts; document the requirement; no font bundling.**

- The beta's Chinese UI renders correctly wherever a CJK system font exists (standard on desktop distros; verified visually on WSLg, screenshots §9).
- Minimal systems without CJK fonts see tofu exactly as CP-1 observed; `README-linux.txt` documents `fonts-noto-cjk` as the fix. Bundling an application font was rejected for scope/legal simplicity (mission §15).

## 11. GPU Setting Policy

Current product setting `Use GPU → h264_nvenc` on a bundled Linux FFmpeg without NVENC was a guaranteed-failure path. Smallest safe behavior implemented (media layer + UI shell only; no encoder framework):

1. **Capability detection** (`auto_sync.ffmpeg_supported_encoders` / `ffmpeg_has_encoder`): one bounded (5 s) `-encoders` subprocess per binary, cached; any failure degrades to "not supported".
2. **Runtime fallback** (`mix_and_export`): `use_gpu=True` without `h264_nvenc` → software `libx264` + explicit log line (`log_gpu_fallback`, en/zh). Software encoding always works; a broken-GPU-path export can no longer happen.
3. **UI gating** (`ui_main.gpu_switch_should_be_enabled` / `gpu_switch_available`): off-Windows, the settings card is disabled with an explanatory description (`set_gpu_desc_unavailable`) when the bundled binary lacks NVENC; **Windows returns `True` unconditionally without probing** — v1.2.0 Windows behavior byte-preserved (bundled Windows binary carries nvenc/amf/qsv, verified by the packaged Windows selftest: `nvenc=True`).

Regression tests: 8 new GPU-policy tests (probe parsing, degradation, caching, nvenc selection, fallback + log, default path never probes, decision matrix, settings-card wiring).

## 12. Updater Policy

**Chosen: Option A — Linux checks for updates and opens GitHub Releases; no self-install.**

- `update_checker.current_platform()` ("windows"/"linux"/"macos"/"other").
- `_find_setup_asset(assets, platform)`: Windows ranking byte-unchanged; any other platform returns `None` — a Windows `.exe`/`.msi` can never be selected for Linux.
- `release_from_manifest(..., platform)`: the shipped manifest's Windows-shaped `setup` object is cleared for non-Windows clients, so the existing UI contract ("no installer → **Open releases page**" button) takes over. The same gating covers the bundled offline manifest.
- Net behavior: Linux beta never selects Windows assets, never presents a Windows installer as a Linux update, never executes a Windows installer (nothing is ever downloaded).
- **Windows updater untouched**: same ranking, same manifest contract, same install launch (all paths resolve `platform == "windows"` exactly as before). `update.json` was not modified — automated Linux update is explicitly deferred (mission §18 fallback), to be revisited with the multi-platform manifest at release time.

Tests: 5 new/extended update tests (platform detection, Windows-only selection, manifest gating ×3 shapes incl. a hypothetical Linux archive asset, API fallback per platform).

## 13. Release Manifest Changes

None. `update.json` and the Windows release-manifest contract are untouched (§12). The forward-compatible multi-platform manifest model (platform/arch/type/url/size/sha256) remains a release-time design task, now simpler because the client-side platform gating already exists and is tested.

## 14. GitHub Actions

`.github/workflows/linux-build.yml` (branch `cross-platform/linux`):

- **Triggers**: `workflow_dispatch` (long-term, active once the file reaches `main` at release time) and scoped `push` on `cross-platform/linux` with a paths filter (docs-only pushes don't rebuild). Not automatic-release; nothing publishes.
- **Job `build-linux`** — `runs-on: ubuntu-24.04` + `container: ubuntu:22.04`:
  apt build prerequisites (git, python3.10 venv, Qt offscreen runtime libs) → checkout → pinned venv (`constraints-linux.txt`) → `pip freeze` recorded → **full test suite** → `pyinstaller RhythmAlign.spec` → `package_artifact.sh` → **packaged-artifact validation** (extract → `--check-only`/`--validate` full workflow on generated deterministic media) → upload `RhythmAlign-linux-x86_64-beta` (tar.gz + sha256 + build-env-frozen.txt).
- **Job `validate-24-04`** — `needs: build-linux`, plain `ubuntu-24.04` runner: downloads the artifact, extracts, reruns full packaged validation on a **newer environment** (glibc-forward compatibility evidence).
- Deliberately simple: two jobs, no matrix, no release publishing.

## 15. Build Evidence

| Build | Environment | Result | Artifact / SHA256 |
|---|---|---|---|
| Local production build | WSL2 Ubuntu 24.04 host, **pinned** py3.10 venv (constraints stack; uv-provisioned CPython 3.10) | **SUCCESS** (tests → build → package) | `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` · `b038d97a…c1ce0b` |
| CI build (run **35529323382**, job `build-linux`) | `ubuntu:22.04` container on `ubuntu-24.04` runner — **the release baseline**; PyInstaller logs `with-glibc2.35`, Python 3.10.12 | **SUCCESS** (3m37s: tests → build → package → packaged validation) | artifact `RhythmAlign-linux-x86_64-beta`: `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz`, **185,014,321 bytes**, SHA256 `c3096e61ed0b316c85bfa857c1c77e9ae6763cda4de970b98c17f1ca9e266fe2` (verified after download) + `build-env-frozen.txt` |

The CI artifact is the beta deliverable shape: download → extract → `cd RhythmAlign && ./RhythmAlign` (see `README-linux.txt` inside the archive).

Build warnings (local, ~40): benign — guarded Windows ctypes imports; xcb-plugin deps not present in the minimal WSL userspace (§9 explains the runtime story); `libtbb`/`libatomic` from non-product extras. Windows side: spec change rebuilt cleanly. CI iterations fixed two container-only issues (binutils for PyInstaller's `objdump`; flat artifact staging for upload) — final run fully green.

## 16. Packaged Runtime Validation

Mechanism: new product entry points `RhythmAlign --check-only` / `RhythmAlign --validate VIDEO MUSIC [--json PATH] [--expect-offset S]` (`selftest.py`), driven by the stdlib-only harness `packaging/linux/validate_artifact.py`, which generates the **CP-1 deterministic media pair** (48 s handcam video + 45 s music, true offset +3.000 s) using the artifact's own bundled FFmpeg, then runs the packaged executable and checks the JSON report.

Packaged results — **three independent builds, all PASS, all engine decisions bit-identical**:

| Validated build | Where | Engine v2 decision |
|---|---|---|
| Local pinned-stack build | Ubuntu 24.04 WSL host (offscreen) | `accepted` / `ACCEPT_DUAL_FAMILY` / `2.995374149659864` |
| **CI build** (22.04 container job) | same container (offscreen) | `accepted` / `ACCEPT_DUAL_FAMILY` / `2.995374149659864` |
| **CI build** (24.04 runner job) | newer environment (offscreen) | `accepted` / `ACCEPT_DUAL_FAMILY` / `2.995374149659864` |
| **CI build** (downloaded artifact) | Ubuntu 24.04 WSL host (offscreen) | `accepted` / `ACCEPT_DUAL_FAMILY` / `2.995374149659864` |

Detailed check list from the CI-artifact run on WSL 24.04 (`results/cp2/`):

| Check | Result |
|---|---|
| Archive extracts; ELF executable bit preserved | PASS |
| `--check-only`: frozen runtime, `_MEIPASS`, all resources (assets/config/bundled_update), locales en_US+zh_CN (174 keys each) | PASS |
| Bundled FFmpeg discovered + executes (`ffmpeg-linux-x86_64-v7.0.2`), libx264 present | PASS |
| Imports in frozen runtime: Engine v2, auto_sync (nvenc=False — correct for Linux bundle), update_checker, file_reveal, diagnostics | PASS |
| Diagnostics report builds in frozen runtime (39 lines) | PASS |
| **Engine v2 analysis on real media** | **PASS — `accepted`, `ACCEPT_DUAL_FAMILY`, offset `2.995374149659864` (Δ4.6 ms vs true; bit-identical to CP-1 Windows/Linux reference)** |
| Export (stream copy + AAC) from packaged runtime | PASS — output produced, duration 48.02 s vs source 48.00 s |
| Export hygiene: no `.partial` leftovers; temp cleaned | PASS |
| No source checkout required at any point | PASS (extracted into scratch dir) |

## 17. Cross-environment Compatibility

| Built on | Ran on | Result |
|---|---|---|
| glibc 2.35 baseline (22.04 container, CI run 35529323382) | Ubuntu 22.04 container (CI job 1) | PASS (headless full workflow) |
| glibc 2.35 baseline (22.04 container, CI) | **Ubuntu 24.04 runner** (CI job 2, glibc 2.39) | PASS (headless full workflow) |
| glibc 2.35 baseline (CI artifact, downloaded) | Ubuntu 24.04 WSL host (glibc 2.39) | PASS (headless full workflow, checksum verified) |
| pinned stack local build (24.04 host) | Ubuntu 24.04 WSLg — **Wayland**, interactive | PASS (rendered, `win_desktop_wayland.png`) |
| pinned stack local build (24.04 host) | Ubuntu 24.04 WSLg — **X11/xcb**, interactive | PASS (rendered after xcb libs, `win_desktop_xcb.png`) |
| **CI artifact** | Ubuntu 24.04 WSLg — **X11/xcb**, interactive | PASS (rendered, `win_desktop_ci_xcb.png`) |

Headless vs GUI evidence is distinguished exactly as the mission requires: CI proves headless runtime on the baseline and a newer env; WSLg proves both Qt display backends interactively, including with the CI-built artifact itself. No claim of universal Linux support is made — the claim is the §3 policy.

## 18. Windows Regression

- Full Windows test suite after all changes: **113 passed** (94 pre-existing + 19 new; includes the existing Windows-specific pins — `explorer /select,` reveal, AppUserModelID logic, `CREATE_NO_WINDOW` choke points).
- Full Windows PyInstaller rebuild with the modified spec: **SUCCESS**; packaged `RhythmAlign.exe --check-only` passes with `frozen=true`, Windows FFmpeg 7.1, **`nvenc=True`** (GPU toggle untouched on Windows).
- Inno Setup script, `RELEASE.md` process, `update.json`, Windows updater behavior, `bundled_update.json`: untouched (verified by diff scope: no changes to `RhythmAlign.iss`, `update.json`; updater changes are platform-gated and Windows paths are byte-identical, pinned by tests).

## 19. Remaining Linux Release Gaps

1. **Public release logistics** — Owner-authorized GitHub Release, release notes, README install section for Linux, and (optionally) the multi-platform update manifest enabling Linux self-update.
2. **Ubuntu 20.04-class support** — permanently out of the stated floor; revisit only if demand appears (would need an older build base and Qt wheel audit).
3. **AppImage / deb / Flatpak** — deferred; tar.gz satisfies the beta; reconsider per user feedback.
4. **Linux hardware encoding** — bundled FFmpeg is software-only; GPU toggle correctly disabled on Linux. Capability-based encoder selection (CP0-003) or an alternate FFmpeg bundle is future work.
5. **Human-pointer GUI pass on a stock desktop distro** (drag-drop, native dialogs) — automated equivalents proven on WSLg; a real-desktop pass remains good release hygiene.

## 20. Beta Release Recommendation

**READY_FOR_OWNER_BETA_RELEASE_DECISION.** The pipeline, artifact, validation, and documentation exist and are reproducible; the artifact itself is user-consumable (download → extract → `./RhythmAlign`). Publishing remains the Owner's call; recommended publication shape: GitHub Release (pre-release flag) with `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` + `.sha256`, Linux section in README, and release notes documenting the glibc ≥ 2.35 floor, software-encoding scope, and minimal-system notes (§9/§10).

## 21. Final Verdict

**LINUX_BETA_READY**

- Reproducible build path exists (pinned container + constraints, §4/§5).
- Supported baseline defined and testable (glibc ≥ 2.35, §3).
- CI produces a user-consumable artifact (§14/§15).
- The packaged artifact passes runtime validation, including the full Engine v2 workflow, bit-identical to the CP-1 reference (§16).
- No major user-facing Linux blocker remains (§19 items are bounded, non-blocking for a beta).

## 22. Git

| Item | Value |
|---|---|
| Starting HEAD | `f89ba7293d9fd4d9faae251ac325075a148aab47` |
| Commits | `2b100c1` `feat: prepare Linux beta packaging`; `581b86f`/`2c499f6`/`9ea4306`/`d231e7c` CI fixes + trigger; docs commit (final) |
| CI run | `35529323382` — green (`ubuntu-22.04` container build + `ubuntu-24.04` validation) |
| Pushed branch | `origin/cross-platform/linux` |
| `main` | untouched (no merge, no PR) |
| Research assets | untouched; no build outputs tracked; no private data tracked |
