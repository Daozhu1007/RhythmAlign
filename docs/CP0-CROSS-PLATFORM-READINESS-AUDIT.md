# CP-0 — Cross-platform Readiness Audit (RhythmAlign v1.2.0)

> Status: AUDIT COMPLETE · Date: 2026-09-20 · Scope: evidence-only audit, no code changes
> Primary deliverable of the CP-0 mission. Production source untouched.

---

## 1. Executive Summary

The strategic assumptions given to CP-0 are **confirmed against the repository**, with corrections in the details:

* The alignment core (`alignment_engine_v2.py`) is already OS-independent at the Python level. Its decision core (`decide_alignment`) operates purely on in-memory NumPy arrays; the only platform-relevant behavior lives in the *file entry point* (`find_offset_v2`), which delegates to the media layer (`tempfile`, `subprocess`, `imageio_ffmpeg`). No algorithm change is needed for any platform.
* The media pipeline is subprocess-driven FFmpeg via `imageio-ffmpeg`. This is portable across Windows/Linux/macOS (imageio-ffmpeg ships per-platform static binaries) and is the single hardest blocker on mobile — iOS forbids subprocess execution outright.
* The desktop UI has exactly **one unguarded Windows-only call** (`explorer /select,` at `ui_main.py:921`). Everything else Windows-specific (AppUserModelID, shortcut resolution via `win32com`, `CREATE_NO_WINDOW`) is already guarded by `os.name == "nt"` checks and degrades safely.
* Linux and macOS are code-side small ports; the real work is **release engineering** (PyInstaller cannot cross-compile — each platform needs its own build host — plus macOS signing/notarization and an `imageio-ffmpeg>=0.6.0` bump for Apple Silicon).
* Android and iOS are blocked by **known, enumerable dependencies**, not by the architecture: librosa hard-depends on `numba`/`llvmlite` and `scikit-learn` (no mobile platform support), PyQt6 has no mobile deployment path (`pyqtdeploy` does not support Qt6; PySide6 does), and iOS additionally forbids FFmpeg-as-subprocess (FFmpegKit retired 2025).

Primary verdict: **READY_FOR_DESKTOP_PORT** (see §22).

---

## 2. Baseline

| Item | Value |
|---|---|
| Branch | `main` |
| Starting HEAD | `91bc50c0a117b38176ec93b44b9e0d1b8aaf749d` (matches the hash expected at CP-0 commissioning) |
| Working tree at start | Clean except two pre-existing untracked items: `.zcodeignore`, `experiments/applied_system/` (not audited, not modified) |
| Released state | Tag `v1.2.0` → `3a622fc` ("chore: publish v1.2.0 release manifest"); `main` is exactly **1 commit ahead** of `v1.2.0` and that commit is docs-only (`91bc50c`, release record). Zero source drift between `main` and the released v1.2.0. |
| Python (audit machine) | 3.10.11 (Windows x64) |
| Key installed deps | numpy 1.24.4, scipy 1.10.1, librosa 0.11.0, numba 0.58.1 / llvmlite 0.41.1, soundfile 0.13.1, soxr 0.3.7, imageio-ffmpeg 0.5.1 (FFmpeg win-x86_64 v7.1), PyQt6 6.7.1 / PyQt6-Qt6 6.7.3, pyqt6-fluent-widgets 1.11.1, PyInstaller 6.18.0, pywin32 3.11 (installed but **not declared**, see CP0-002) |
| Tests before audit | `python -m pytest tests/ -q` → **80 passed** in 26.59 s |

---

## 3. Current Architecture

Repository-grounded call graph of the shipping product path:

```text
ui_main.py  (PyQt6 + PyQt-Fluent-Widgets, FluentWindow)
  │  QThread workers: SyncWorker / AnalyzeWorker / UpdateCheckWorker / UpdateDownloadWorker
  ▼
BaseMediaWorker (ui_main.py:470)          UpdateChecker (update_checker.py, urllib)
  │  _run_find_offset()
  ▼
alignment_engine_v2.find_offset_v2  (Engine v2, default since RA-1.2D)
  │  ├─ auto_sync.extract_audio          ← media layer (subprocess + imageio-ffmpeg)
  │  ├─ librosa.load                     ← media layer (soundfile/soxr)
  │  └─ decide_alignment                 ← PURE NUMPY/SCIPY/LIBROSA DECISION CORE
  │        ├─ _align_hybrid / _align_onset      (auto_sync.py, librosa)
  │        ├─ PCEN/HPSS feature generators      (librosa)
  │        └─ clustering + evidence gates + temporal-support gate
  ▼
auto_sync.mix_and_export  (subprocess.Popen → imageio-ffmpeg binary → FFmpeg)
```

Supporting layers: `diagnostics.py` (report → clipboard), `update_checker.py` (manifest fetch from `main/update.json`, bundled fallback `bundled_update.json`), config (`config.json` default → per-user copy), packaging (`RhythmAlign.spec` + `RhythmAlign.iss`), release process (`RELEASE.md`, Windows-only tooling).

---

## 4. Platform Assumption Inventory

Full-repository sweep (source, spec, installer, manifests, docs — `build/`, `dist/`, `results/`, `experiments/` excluded). Complete list of every platform-sensitive construct found:

| # | Location | Construct | Guarded? | Effect |
|---|---|---|---|---|
| A1 | `auto_sync.py:13` | `_IS_WINDOWS = os.name == "nt"` | yes | sole platform flag of the media layer |
| A2 | `auto_sync.py:28-34` | `subprocess.CREATE_NO_WINDOW` | yes (`_IS_WINDOWS`) | hides child consoles on Windows; no-op elsewhere |
| A3 | `diagnostics.py:39` | `creationflags = CREATE_NO_WINDOW if os.name=="nt" else 0` | yes | same, choke point #2 |
| A4 | `ui_main.py:24-31` | `APPDATA` vs `XDG_CONFIG_HOME`/`~/.config` | yes | per-user config location already dual-path |
| A5 | `ui_main.py:49-68` | `windows_shortcut_candidates` (APPDATA/PROGRAMDATA/USERPROFILE/PUBLIC, `.lnk`) | yes (`os.name != "nt"` → `[]`) | Windows-only, safe no-op elsewhere |
| A6 | `ui_main.py:71-77` | `from win32com.client import Dispatch` | yes (try/except → `""`) | **hidden pywin32 dependency** (CP0-002) |
| A7 | `ui_main.py:99-112` | `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID` | yes | Windows taskbar identity |
| A8 | `ui_main.py:921` | `subprocess.Popen(['explorer', '/select,', path])` | **NO** | **the only unguarded Windows call** (CP0-001) |
| A9 | `ui_main.py:10-13` | `sys._MEIPASS` | PyInstaller flag | not OS-specific; works on all PyInstaller targets |
| A10 | `ui_main.py:244-247` | `QFont("Consolas")` + Monospace style hint | soft | graceful font substitution off-Windows |
| A11 | `ui_main.py:238, RhythmAlign.spec:63, RhythmAlign.iss` | `logo.ico` | soft | Qt reads `.ico` on all desktop OS; `.png` fallback exists; `.icns` absent (macOS bundle work, CP0-006) |
| A12 | `auto_sync.py:370` | `vcodec = "h264_nvenc" if use_gpu else "libx264"` | no | "Use GPU" is NVIDIA-coupled (CP0-003) |
| A13 | `update_checker.py:87-97` | asset ranking `.exe`/`.msi`/`.zip` only | no | updater is Windows-artifact-only (CP0-004) |
| A14 | `update_checker.py:236` | fallback name `*_Setup.exe` | no | cosmetic but Windows-shaped |
| A15 | `ui_main.py:1697-1699` | `_launch_installer` Popen of downloaded artifact | no | Windows installer semantics (CP0-005) |
| A16 | `diagnose_offset.py:73` | `ffprobe.exe if os.name == "nt" else "ffprobe"` | yes | already correct (and ffprobe is *not* shipped by imageio-ffmpeg — graceful `shutil.which` fallback) |
| A17 | `RhythmAlign.iss` | Inno Setup script, `AppUserModelID`, `{autopf}` | Windows build only | Windows-only installer by design |
| A18 | `RELEASE.md` | PyInstaller → Inno → PowerShell ZIP → `gh release` | Windows host | release process is Windows-host-only |
| A19 | `subprocess` usage | `auto_sync.py` (5 sites), `diagnostics.py`, `ui_main.py:921,1699`, `diagnose_offset.py` | n/a | desktop-port fine; mobile blocker (CP0-010) |

Nothing else platform-specific exists: no `sys.platform` checks, no `platform.system()` branches in product code, no endianness assumptions, no registry/wmi use beyond A6/A7, no hard-coded `C:\` paths in product code.

---

## 5. Alignment Core Audit

Files: `alignment_engine_v2.py` (901 lines), decision-relevant helpers in `auto_sync.py`.

**Verdict: PORTABLE as computation; the file entry point is a thin media-layer consumer.**

* NumPy usage (`np.correlate`-style FFT correlation, peaks, z-scores, binning): OS-independent, CPU-endianness-neutral on all supported targets.
* SciPy usage: `signal.find_peaks`, `signal.correlate(method="fft")` — portable.
* librosa usage: `load`, `feature.chroma_cens`, `onset.onset_strength`, `feature.melspectrogram`, `decompose.hpss`, `pcen` — portable on desktop; **hard dependency chain is the mobile blocker**: librosa 0.11.0 declares `numba>=0.51.0`, `scikit-learn>=1.1.0`, `soundfile`, `soxr`, `pooch` (verified via package metadata). numba→llvmlite has no Android/iOS support at all (§12).
* Threading/multiprocessing: none in the engine; workers are Qt `QThread`s in the UI layer. No native extensions beyond the standard scientific wheels.
* Filesystem contact inside the engine: `find_offset_v2` writes two temp WAVs via `tempfile.gettempdir()` + `uuid` names and removes them in `finally` (`alignment_engine_v2.py:877-901`) — cross-platform safe. The decision core `decide_alignment` (line 762) never touches the filesystem.
* `decide_from_families` (line 783) is a documented test seam that already accepts precomputed family curves — i.e., **the seam for a mobile adapter already exists in the code**.

Answer to the §9 question "can Engine v2 be made completely OS-unaware without changing its algorithm": **YES — it effectively already is.** The only OS-coupled step is audio extraction, which is invoked from `auto_sync.extract_audio`, a separate module. No threshold, no signal logic, no decision code contains any platform reference.

Classification summary: everything in the core is *portable* (desktop) / *mobile concern* only via librosa's dependency chain.

---

## 6. Media / FFmpeg Audit

File: `auto_sync.py`.

**Binary discovery.** `imageio_ffmpeg.get_ffmpeg_exe()` resolves in order: `IMAGEIO_FFMPEG_EXE` env → bundled per-platform binary → conda ffmpeg → system PATH (verified from installed package source). The shipped binary is platform-named (`ffmpeg-win-x86_64-v7.1.exe` observed in the v1.2.0 frozen build, recorded in `docs/RA-1.2E-V1.2.0-RELEASE.md`). imageio-ffmpeg 0.5.1 publishes wheels for win32/win_amd64, manylinux2010 x86_64, manylinux2014 aarch64, and macOS x86_64 **only**; macOS arm64 first appears in 0.6.0 (verified on PyPI) → CP0-007.

**Operations and their portability:**

| Operation | Site | Platform assessment |
|---|---|---|
| Duration probe | `get_video_duration` — parses `Duration:` from `ffmpeg -i` stderr | FFmpeg-level, platform-independent; no ffprobe dependency in the product path |
| Audio extraction | `extract_audio` → `pcm_s16le` WAV in temp dir | platform-independent |
| Audio-stream detection | `_has_audio_stream` → `-f null -` decode of 1 frame | platform-independent |
| Export, stream copy (default) | `-c:v copy -c:a aac -b:a 320k` + `amix`/`adelay`/`atrim` filters | encoder-independent — this is why the default product path is already hardware-neutral |
| Export, re-encode | `h264_nvenc` if `use_gpu` else `libx264` (`auto_sync.py:370`) | **NVIDIA-only coupling** — see below |
| Mux hygiene | `-map_metadata -1`, `-movflags +faststart`, `-fflags +genpts`, `-avoid_negative_ts make_zero` | platform-independent |
| Temp output + atomic publish | `.{stem}.{uuid}.partial{ext}` sibling file, then `os.replace` (`auto_sync.py:309-316, 432`) | atomic rename is valid on POSIX too; temp file lands in the *output* directory (correct for same-filesystem rename on all OS) |
| Subprocess handling | `subprocess.run`/`Popen` + `_subprocess_no_window_kwargs` | desktop-port fine; **mobile: Android restricted (W^X: exec only from `jniLibs` native lib dir), iOS forbidden** |

**GPU coupling (explicit examination requested).** The `UseGPU` setting (`ui_main.py:197`, default **false**) maps to exactly one encoder choice: `h264_nvenc`. This is *incorrectly coupled to NVIDIA hardware*, confirmed at both ends:

1. Code: no AMF/QSV/VideoToolbox/VAAPI path exists anywhere (`auto_sync.py:370` is the only encoder selection).
2. Binary: the bundled imageio-ffmpeg v7.1 Windows binary **already contains** `h264_amf` (AMD) and `h264_qsv` (Intel) alongside `h264_nvenc`, `hevc_nvenc`, `av1_nvenc`, `libx264`, `aac` (verified by enumerating `-encoders` on the installed binary). So on Windows, "use GPU" could serve AMD/Intel owners with the shipped binary today; on Linux/macOS the bundled binary's hardware-encoder inventory is UNVERIFIED and must be probed before promising anything.

The README/RELEASE.md wording "GPU 加速仅支持 NVIDIA 显卡 (NVENC)" is therefore accurate today but is a self-imposed limitation, not a binary limitation. Not fixed in CP-0 per mission boundary; recorded as CP0-003.

---

## 7. Desktop UI Audit

Files: `ui_main.py`, dependency `pyqt6-fluent-widgets` 1.11.1 + `pyqt6-frameless-window`.

**Will fail (exactly one site):**

* `ui_main.py:921` — `subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])`. `open_folder` defaults to **true** (`config.json`), so on Linux/macOS every *successful export* raises `FileNotFoundError` in the completion slot: the traceback is printed, the success InfoBar is never shown, and the app stays usable. Export itself is already complete — this is a post-success UX break, not a data break. → CP0-001 (P2).

**Will work but degrade / not feel native:**

* `Consolas` log font → Qt monospace substitution (A10). P3 polish.
* `SystemThemeListener` (verified from installed qfluentwidgets source): `win32` → `darkdetect.listener`; other platforms poll `darkdetect.theme()` every 1–2 s. macOS/Windows auto-theme works; Linux coverage depends on desktop environment (darkdetect reads gsettings where available) — "works, may not feel native".
* Fluent design: `qfluentwidgets` upstream declares Win32/Linux/macOS support; frameless window (`pyqt6-frameless-window`) supports all three; Mica material is Windows-11-only (graceful). The app's own rounded-corner/stacked-background QSS (`ui_main.py:1478-1498`) is plain Qt — portable.
* `logo.ico` window icon: Qt decodes ICO on all desktop platforms; `.png` fallback exists (`load_app_icon`). Native `.icns` matters only for macOS bundling (§9).
* Drag & drop, `QFileDialog`, `QDesktopServices.openUrl`, clipboard (`QApplication.clipboard`): Qt cross-platform — no issues.
* DPI: manual `devicePixelRatioF` pixmap scaling (`ui_main.py:229-234`), no Windows-only DPI APIs — portable.
* Threading: `QThread` workers + signals; `closeEvent` terminates the theme listener. No Windows-specific threading behavior.

**Windows-only but correctly guarded** (no action needed for a port): AUMID via `ctypes.windll` (A7), shortcut resolution via `win32com` (A5/A6 — falls back to empty), `CREATE_NO_WINDOW` (A2/A3).

**Mobile UX note:** minimum window size 1024×550, hover-driven navigation, desktop file dialogs — the widget set is desktop-shaped. A touch UI would be new work regardless of the Qt binding (§15).

---

## 8. Filesystem / Configuration Audit

| Path | Mechanism | Windows | Linux | macOS |
|---|---|---|---|---|
| User config | `_user_config_path` (`ui_main.py:24-31`): `%APPDATA%\RhythmAlign\config.json` vs `$XDG_CONFIG_HOME`/`~/.config/RhythmAlign/config.json` | native | native (XDG-correct) | **works but non-native** — macOS convention is `~/Library/Application Support` (CP0-013); Qt's `QStandardPaths.AppConfigLocation` would give all three natively (recommended later, *not* implemented per mission) |
| Bundled resources | `sys._MEIPASS` (frozen) / source dir (dev) — `resource_path` (`ui_main.py:10-21`) | OK | OK | OK (PyInstaller-managed) |
| Analysis temp WAVs | `tempfile.gettempdir()` + cleanup in `finally` (`alignment_engine_v2.py:883-901`, `auto_sync.py:229-231`) | OK | OK | OK |
| Update downloads | `%TEMP%\RhythmAlign\updates\` via `tempfile.gettempdir()` (`update_checker.py:235-240`) | OK | OK | OK |
| Export temp+rename | sibling `.{uuid}.partial` + `os.replace` | OK | OK | OK |
| FFmpeg binary | inside frozen `_internal/imageio_ffmpeg/binaries/` | OK | OK | OK |

No `QStandardPaths` usage exists today; no path hardcoding beyond Windows env vars (guarded). Environment-variable sweep hits (`APPDATA`, `PROGRAMDATA`, `USERPROFILE`, `PUBLIC`) are confined to the guarded Windows shortcut code (A5).

---

## 9. Packaging Audit

Current chain (Windows, works, documented in `RELEASE.md`): `pyinstaller RhythmAlign.spec` (onedir EXE+COLLECT, excludes pytest/PySide6, bundles `assets/`, `locales/`, `config.json`, `bundled_update.json`, imageio-ffmpeg metadata, certifi data) → `RhythmAlign.iss` (Inno Setup, per-user/per-machine, shortcuts with AppUserModelID, VC++ redist note) + portable ZIP.

**Hard constraint for every new desktop platform: PyInstaller does not cross-compile.** A Linux build must run on Linux; a macOS build must run on macOS (official PyInstaller documentation). This alone dictates CI runners or dedicated build hosts — it is the *dominant* cost of CP-2/CP-4, larger than any code change.

### Linux
* Likely spec changes: none structurally required — the same onedir spec pattern works; `icon='assets/logo.ico'` should gain a `.png`/`.svg` variant for Linux launchers (CP0-006). Executable bit and `chmod +x` are handled by PyInstaller on Linux.
* FFmpeg: imageio-ffmpeg manylinux x86_64 + aarch64 wheels bundle a static binary automatically; no extra provisioning.
* glibc floor: the build host's glibc becomes the minimum supported distro — build on the oldest supported base (classic manylinux practice). UNVERIFIED which glibc the bundled FFmpeg binaries themselves require (statically linked per upstream; verify at CP-1).
* Distribution format: `.tar.gz` of the onedir folder is the zero-extra-tooling artifact; AppImage / `.deb` / Flatpak are *conceptual* options only (CP-0 does not select one; a plain archive + README is sufficient for a proof-of-life and reasonable for a first release; AppImage would replicate the "no-install" portable experience that Windows users get today).

### macOS
* Build blockers: **none fundamental** — PyInstaller supports macOS (x86_64 + arm64). Required spec work: add a `BUNDLE` block (`.app`), `.icns` icon (`logo.icns` must be produced; only `.ico`/`.png` exist today), optionally `target_arch` for universal2 (currently `None` → native-only per build).
* Distribution work (not blockers): code signing identity (`codesign_identity=None` today), notarization, `.dmg` staging.
* Dependency bump: imageio-ffmpeg **0.6.0** required for an arm64 FFmpeg wheel (0.5.1 is Intel-only) → CP0-007. All other deps publish macosx_arm64 wheels (numpy 1.24+, scipy, llvmlite, PyQt6-Qt6 — verified on PyPI).
* Intel + Apple Silicon: two native builds (or one universal2 build with a universal2 Python) — decision belongs to CP-3.

---

## 10. Update-System Audit

Files: `update_checker.py`, `ui_main.py` (workers + dialogs), `update.json` (live manifest, served from repo `main`), `bundled_update.json` (offline fallback, version-note only).

**How Windows-specific is the updater?** The transport, versioning, and integrity machinery is fully portable: urllib fetch with UA + no-cache, three-tier fallback (remote manifest → optional GitHub API → bundled JSON), `parse_version`/`is_newer_version` numeric compare, `.part` download + `os.replace`, SHA-256 verification (accepts GitHub `digest: sha256:…` or release-notes regex), ThreadPool manifest race with timeout.

Windows is embedded in exactly three places:

1. **Asset selection** `_find_setup_asset` (`update_checker.py:78-100`): ranks only `.exe` (setup), `.msi`, `.exe`, `.zip` (non-portable). A Linux `.tar.gz`/`.AppImage` or macOS `.dmg` asset scores `None` → `setup_url=None` → the UI already has a defined no-installer path ("open releases page" button, `ui_main.py:1608-1612`). **Graceful, but no self-update for other platforms.** → CP0-004.
2. **Fallback filename** `..._Setup.exe` (`update_checker.py:236`) — cosmetic.
3. **Install launch** `_launch_installer` Popen of the downloaded file + app quit (`ui_main.py:1697-1708`) — meaningful only for Windows installer semantics (`.exe`/`.msi`); on other platforms the equivalent actions differ (untar, mount dmg, apt install) and belong to the platform packaging story.

**Manifest shape today:** single `setup` object (name/url/size/sha256) + an informational `portable` section that the client ignores. A future multi-platform manifest needs, conceptually, a list of artifacts each tagged with `platform` (win/linux/mac/android/ios), `architecture` (x86_64/arm64/universal2), `artifact_type` (setup/portable/archive/dmg/appimage), `url`, `size`, `sha256`, plus client-side platform detection (`sys.platform` + `platform.machine()` mapping). **Schema deliberately not designed here** per mission scope.

---

## 11. Diagnostics Audit

`diagnostics.py` correctly reports: frozen state, executable/base/working dirs, user-config path, alignment-engine label, `platform.platform()` + `platform.machine()` (OS + arch), Python/Qt/PyQt versions, PyQt-Fluent-Widgets version, all seven product settings, and FFmpeg (imageio-ffmpeg path + `-version` first line, PATH ffmpeg presence + version).

Gaps that would hurt cross-platform bug triage:

* **No hardware-encoder inventory** — nothing probes `-encoders` for nvenc/amf/qsv/videotoolbox/vaapi, so "UseGPU didn't work" reports are undiagnosable today even on Windows.
* No Linux distribution/libc detail beyond `platform.platform()` (usually adequate; a distro field would be better).
* No GPU/driver identification.
* No Qt platform plugin name (`QGuiApplication.platformName`) — the single most useful field when a Qt port fails to start.
* PATH-ffmpeg probing exists — good (it would mask a broken bundled binary on all OSes equally; consider reporting *which* binary the product actually used for the last export).

→ CP0-009 (P3, but cheap and high-leverage before CP-1 starts producing Linux users).

---

## 12. Dependency Portability Matrix

Legend: **S** = Supported (official artifacts exist) · **L** = Likely supported (evidence, not fully verified) · **U** = Unsupported · **C** = Requires custom build · **?** = Unknown/requires experiment. Claims without a cited verification are marked UNVERIFIED in the notes.

| Dependency (version in use) | Win x86_64 | Linux x86_64 | Linux arm64 | macOS x86_64 | macOS arm64 | Android arm64 | iOS arm64 |
|---|---|---|---|---|---|---|---|
| Python 3.10+ (3.10.11) | S | S | S | S | S | L (official Android Tier-3 from 3.13, PEP 738; 3.10 via Chaquopy) | C (PEP 730 toolchain; no plain CPython) |
| NumPy (1.24.4) | S | S | S | S | S | L (no official PyPI Android wheels — verified NONE; Chaquopy-hosted builds exist — UNVERIFIED current status) | C |
| SciPy (1.10.1) | S | S | S | S | S | L (same as NumPy; Chaquopy — UNVERIFIED) | C |
| **librosa (0.11.0)** | S | S | S | S | S | **U** | **U** |
| — via numba/llvmlite | S | S | S | S | S | **U** (no support, no binaries) | **U** |
| — via scikit-learn | S | S | S | S | S | U | U |
| soundfile / libsndfile (0.13.1) | S | S | S | S | S | C | C |
| soxr (0.3.7) | S | S | S | S | S | C | C |
| imageio-ffmpeg (0.5.1) | S | S | S | S | **S only ≥0.6.0** (0.5.1 = Intel-only — verified PyPI) | C (binary packaging via jniLibs; exec restrictions apply) | U as package (subprocess model forbidden) |
| FFmpeg (bundled binary) | S (v7.1 verified) | S | S | S | S (≥0.6.0) | C (link or package as executable; W^X rules) | C (must link as library; FFmpegKit retired 2025 — forks only) |
| PyQt6 (6.7.1) / Qt (6.7.3) | S | S | S (manylinux_2_39 aarch64 wheels exist — verified 6.11.2; high glibc floor) | S | S (macosx_11_0_arm64 — verified) | **U** (no wheels; no deployment tooling; `pyqtdeploy` lacks Qt6) | **U** |
| PyQt-Fluent-Widgets (1.11.1) | S | S (upstream-declared) | L | S | L | U | U |
| pyqt6-frameless-window (0.8.1) | S | S | L | S | L | U | U |
| PyInstaller (6.18.0) | S | S | S | S | S | U (use p4a/Chaquopy/PySide-deploy instead) | U |
| certifi | S | S | S | S | S | S (pure python) | S |
| pywin32 (3.11, **undeclared**) | S (undeclared → silent absence possible) | U (graceful) | U | U | U | U | U |

Notes: desktop cells are supported by PyPI wheel inventory verified during this audit (numpy/scipy/llvmlite/PyQt6-Qt6/imageio-ffmpeg) or upstream statements (PyQt-Fluent-Widgets: Win32/Linux/macOS). Mobile cells: PyPI began accepting mobile platform tags in 2025 (PEP 738/730), but numpy/scipy currently publish **no** Android/iOS wheels (verified against latest release inventories), and numba/llvmlite/scikit-learn provide none at all — that, not librosa's pure-Python code, is the mobile blocker. PySide6 (not a current dependency) does publish Android wheels and gained iOS deployment with Qt ≥ 6.12 — relevant only as a *future* mobile-Qt route (§15/§16).

---

## 13. Linux Assessment

**Scope: SMALL (code) / MEDIUM (as a product release).** The initial hypothesis "SMALL/MEDIUM" is confirmed.

Evidence:
* Code: zero Linux-breaking constructs found. The one failure is CP0-001 (`explorer`), a one-line guarded rewrite. Config paths already XDG-correct. `CREATE_NO_WINDOW` correctly no-ops.
* Runtime: all deps ship manylinux x86_64 wheels; imageio-ffmpeg ships the FFmpeg binary; librosa chain installs cleanly.
* The actual work is productization: a Linux build host (no cross-compilation), glibc-floor decision, launcher icon/desktop-entry, distribution format choice, updater asset support (CP0-004/005), and a real-machine verification of the fluent-widget rendering (darkdetect polling path) — none of it architectural.

**Biggest blocker: none in code — the binding constraint is release engineering (a Linux build environment + choosing the distribution artifact).** Recommended gating experiment for CP-1: `find_offset_v2` + `mix_and_export` end-to-end on a real Linux box.

## 14. macOS Assessment

**Scope: MEDIUM.** Hypothesis "SMALL/MEDIUM" confirmed at the MEDIUM end, entirely due to packaging/distribution.

Evidence:
* Code: identical story to Linux (CP0-001 is the only break). Theme listener uses darkdetect with a proper macOS path.
* Dependencies: every runtime dep publishes macosx_arm64 wheels **except** the pinned-resolved imageio-ffmpeg 0.5.1 → bump to 0.6.0 (CP0-007). Intel wheels all exist.
* Packaging: `.app` BUNDLE + `.icns` are spec additions; signing/notarization require an Apple Developer account and build-host time. These are distribution work, **not build blockers** — CP-0 explicitly distinguishes them per the mission.
* Non-native-but-working: config path (`~/.config`) — CP0-013.

**Biggest blocker: notarization/signing logistics + Apple-Silicon build (imageio-ffmpeg bump).** First product decision for CP-3: Intel-only vs arm64-only vs universal2.

## 15. Android Assessment

**Scope: RESEARCH-leaning-LARGE** (hypothesis "LARGE/RESEARCH" confirmed). Feasibility-only conclusions:

1. **Python runtime: feasible.** CPython is Tier-3 on Android from 3.13 (PEP 738); Chaquopy provides embedded CPython for app integration. The engine's Python-level code would run; the *dependencies* are the problem.
2. **Scientific stack: blocked as-is.** librosa requires numba→llvmlite and scikit-learn — neither has Android support or binaries (numba/llvmlite: no Android platform support at all). NumPy/SciPy have no official PyPI Android wheels (verified); Chaquopy historically hosts its own numpy/scipy builds (UNVERIFIED current coverage/versions).
   * Consequence: an Android engine proof (MOB-1) must either extract the librosa feature computations actually used (melspectrogram/HPSS/PCEN, chroma CENS, onset strength) into a numpy/scipy-only path — algorithmically identical but a re-implementation that would need its own equivalence validation against v1.2.0 golden outputs — or wait for/verify Chaquopy coverage of numba (unrealistic). This is the single largest unknown of the mobile track.
3. **Qt bindings: PyQt6 is a dead end on Android.** No wheels, no deployment tooling (`pyqtdeploy` does not support Qt6). PySide6 has official Android wheels + `pyside6-deploy` (Nuitka-based, APK/AAB). PyQt-Fluent-Widgets additionally exists in a PySide6 flavor (upstream supports PySide6 branches), which *softens* a future binding migration — but CP-0 explicitly does **not** recommend migrating for its own sake; desktop v1.2.x stays PyQt6.
4. **FFmpeg: plausible but custom.** Android can exec packaged binaries under W^X restrictions (must live in the APK's native lib dir, executable extracted/exec'd per NDK rules); the subprocess-based `mix_and_export` could survive nearly unchanged with a repackaged FFmpeg. Storage needs SAF/permissions work for user media I/O.
5. **Architecture split** (`core → desktop adapter → PyQt6` / `core → mobile adapter → Android client`): **plausible and already half-present.** The engine's decision core is array-in/array-out; the media layer is a separate module; the UI already communicates with the engine only through `find_offset_v2`/`mix_and_export` and reason codes. The missing piece for the split is *not* the engine — it is (a) a librosa-free feature layer and (b) a media-adapter interface over extraction/mux.

**Biggest unknown/blocker: librosa's numba/scikit-learn dependency chain** (with FFmpeg-subprocess packaging as the second).

## 16. iOS Assessment

**Scope: RESEARCH. Desired outcome reached: `IOS_REQUIRES_SEPARATE_FEASIBILITY_PHASE`.**

Everything from §15 applies *plus* iOS-specific hard problems:

* **Subprocess execution is forbidden** by Apple's platform rules — `subprocess.Popen(ffmpeg)` can never run as written. FFmpeg must be linked as a library; the standard tooling for that (FFmpegKit) was retired in January 2025 (binaries removed from registries April 2025; forks such as FFmpegKit.Next exist). The whole export path needs a library-shaped redesign, not a port.
* Embedded Python (PEP 730, Tier 3 since 3.13) and the scientific stack face the same numba/librosa blocker with even less community tooling than Android.
* Qt route: PySide6 iOS deployment exists only from Qt ≥ 6.12 (very recent, Nuitka static-compilation approach) — immature; PyQt6 has none.
* App Store: signing, LGPL/GPL static-linking licensing constraints on FFmpeg, background-audio and file-access policies — each its own work item.

**Biggest unknown/blocker: the subprocess ban making the entire FFmpeg pipeline architecture invalid on iOS.**

---

## 17. Portability Issue Inventory

Severity: P0 prevents execution · P1 prevents normal product workflow · P2 packaging/release/quality · P3 polish. Confidence: HIGH = verified in repo/on machine; MED = verified + reasonable inference; LOW = UNVERIFIED.

| ID | File:Location | Layer | Current behavior | Affected platforms | Sev | Type | Why it matters | Suggested future direction | Conf |
|---|---|---|---|---|---|---|---|---|---|
| CP0-001 | `ui_main.py:921` (`SyncInterface.task_finished`) | UI/FILESYSTEM | Unguarded `Popen(['explorer', '/select,', path])` after every successful export (`open_folder` default true) | Linux, macOS | **P2** (P1 for those products' normal flow) | CODE | Success feedback breaks on every export off-Windows; traceback noise in support | Platform-aware reveal: `xdg-open <dir>` / `open -R <path>` (or `QDesktopServices.openUrl` on the folder); guard behind `os.name` | HIGH |
| CP0-002 | `ui_main.py:73` + `requirements.txt` | DEPENDENCY | `win32com` used for shortcut resolution; `pywin32` installed locally but absent from requirements | All (dev envs), frozen builds from clean env | P3 | DEPENDENCY | Silent feature loss (AUMID not set) and non-reproducible dev setups | Declare `pywin32; sys_platform == "win32"` or drop the import behind a hard guard | HIGH |
| CP0-003 | `auto_sync.py:370` (`mix_and_export`) | MEDIA | `use_gpu` ⇒ `h264_nvenc` only; bundled binary also carries `h264_amf`, `h264_qsv` (verified) | Windows (AMD/Intel users), future Linux/macOS | P3 | MEDIA | "Use GPU" is mislabeled as generic hardware acceleration; NVIDIA-only by code, not by capability | Future: encoder auto-detect/selection from `-encoders` probe; rename setting semantics. **Not fixed in CP-0** | HIGH (Windows binary); LOW (Linux/mac binary inventory) |
| CP0-004 | `update_checker.py:78-100` (`_find_setup_asset`) | UPDATE | Ranks only `.exe`/`.msi`/non-portable-`.zip`; other-platform assets invisible | Linux, macOS (future) | **P1** (for future platform self-update) | UPDATE | No self-update path can ever trigger off-Windows; users fall back to the releases page | Manifest-driven per-platform artifact selection (§10); keep GitHub-API fallback platform-aware | HIGH |
| CP0-005 | `update.json` schema + `ui_main.py:1697` (`_launch_installer`) | UPDATE/PACKAGING | Single Windows `setup` object; installer launch = run `.exe` | Linux, macOS (future) | P2 | UPDATE | Manifest cannot express multi-platform releases; install semantics differ per OS | Multi-artifact manifest concept (platform/arch/type/url/size/sha256) — design deferred | HIGH |
| CP0-006 | `RhythmAlign.spec` (no `BUNDLE`; `icon='assets/logo.ico'`), asset set (`.ico`/`.png` only) | PACKAGING | Windows onedir + Inno is the only packaging story | macOS (build), Linux (launcher polish) | P2 | PACKAGING | No `.app` bundle/`.icns` for macOS; Linux desktop entry needs PNG/SVG icon | Per-OS spec variants or one spec with `platform` branches; produce `logo.icns` at CP-3 | HIGH |
| CP0-007 | `requirements.txt:4` (`imageio-ffmpeg>=0.4`) | DEPENDENCY | Current resolve (0.5.1) ships no macOS-arm64 FFmpeg wheel; 0.6.0 does (verified) | macOS arm64 | P2 | DEPENDENCY | Apple Silicon build impossible on 0.5.1 | Bump pin to `>=0.6.0` at CP-3 (verify 0.6.0 behavior on Win/Linux first) | HIGH |
| CP0-008 | `ui_main.py:244` (`log_text_font`) | UI | `Consolas` + monospace style hint | Linux, macOS | P3 | UI | Non-native fallback font | Optional: platform font table or `QFontDatabase.systemFont(QFontDatabase.FixedFont)` | HIGH |
| CP0-009 | `diagnostics.py` | DIAGNOSTICS | No FFmpeg encoder inventory, no Qt platform plugin, no distro/libc detail, no GPU info | All (esp. future ports) | P3 | CODE | Cross-platform bug reports undiagnosable (esp. GPU/encoder issues) | Add `-encoders` probe (filtered), `QGuiApplication.platformName`, distro line at CP-1 | HIGH |
| CP0-010 | `auto_sync.py` (all subprocess sites) | MEDIA/MOBILE | FFmpeg driven via `subprocess` | Android (restricted), iOS (forbidden) | **P0-for-mobile**, N/A desktop | MOBILE | The entire media layer is subprocess-shaped | Mobile adapter: Android = packaged binary exec; iOS = linked library (FFmpegKit-fork). Desktop unaffected | HIGH |
| CP0-011 | `requirements.txt:2` → librosa → numba/llvmlite/scikit-learn | DEPENDENCY/MOBILE | librosa's hard deps have no Android/iOS support or binaries | Android, iOS | **P0-for-mobile** | MOBILE/DEPENDENCY | Engine as-shipped cannot be built for mobile | MOB track: numpy/scipy-only feature layer with golden-output equivalence vs v1.2.0 | HIGH |
| CP0-012 | PyQt6 binding choice (`requirements.txt:5`) | UI/MOBILE | PyQt6 has no mobile wheels or deployment tooling (`pyqtdeploy` lacks Qt6); PySide6 does (Android mature, iOS Qt≥6.12) | Android, iOS | P1-for-mobile | MOBILE | Desktop binding cannot ship on mobile | Decision deferred to MOB-0; PyQt-Fluent-Widgets' PySide6 flavor lowers future migration cost. **No migration now** | HIGH |
| CP0-013 | `ui_main.py:24-31` | FILESYSTEM | macOS config at `~/.config` (works, non-native) | macOS | P3 | FILESYSTEM | Not where macOS users/tools expect | Adopt `QStandardPaths` when touching config next | HIGH |
| CP0-014 | `RhythmAlign.iss`, `RELEASE.md` | DISTRIBUTION | Windows-only installer + Windows-host-only release process; PyInstaller cannot cross-compile | Linux, macOS | P2 | DISTRIBUTION | Each new platform needs its own build host/CI pipeline | CP-2/CP-4 define per-OS build pipelines (GitHub runners are natural) | HIGH |
| CP0-015 | `ui_main.py:1415` (min 1024×550), fluent desktop widgets | UI/MOBILE | Desktop-shaped UI (hover nav, dialogs, min size) | Android, iOS | P3 | MOBILE | Touch/mobile UX is new design work regardless of binding | Mobile client UX design in MOB track | HIGH |

Positive findings (no issue IDs): guarded `CREATE_NO_WINDOW` single choke points; XDG-aware config; atomic temp+rename export; engine/decision presentation-independence (reason codes → locale keys); `diagnose_offset.py` already ffprobe-platform-correct.

---

## 18. Platform Readiness Matrix

| Layer | Windows | Linux | macOS | Android | iOS |
|---|---|---|---|---|---|
| Alignment engine | READY | READY | READY | FEASIBILITY_REQUIRED | FEASIBILITY_REQUIRED |
| FFmpeg extraction | READY | READY | MINOR_WORK (arm64 wheel bump) | FEASIBILITY_REQUIRED | BLOCKED (subprocess ban) |
| Export | READY | READY | MINOR_WORK | FEASIBILITY_REQUIRED | BLOCKED |
| UI | READY | MINOR_WORK (CP0-001, theme polling verify) | MINOR_WORK (CP0-001, font/icon niceties) | SIGNIFICANT_WORK | SIGNIFICANT_WORK |
| Filesystem | READY | READY | MINOR_WORK (config path convention) | SIGNIFICANT_WORK (SAF/storage) | SIGNIFICANT_WORK |
| Packaging | READY | SIGNIFICANT_WORK (build host, artifact choice — no code blockers) | SIGNIFICANT_WORK (bundle/sign/notarize) | FEASIBILITY_REQUIRED | FEASIBILITY_REQUIRED |
| Updater | READY | SIGNIFICANT_WORK (asset selection + manifest) | SIGNIFICANT_WORK | FEASIBILITY_REQUIRED | FEASIBILITY_REQUIRED |
| Distribution | READY | SIGNIFICANT_WORK | SIGNIFICANT_WORK (signing/notarization) | BLOCKED_BY_KNOWN_DEPENDENCY | BLOCKED_BY_KNOWN_DEPENDENCY |

Justifications for non-obvious cells: engine READY on mobile-adjacent columns refers to algorithm portability; the column-level mobile blockers live in the rows below it (librosa chain → §15/§16, CP0-010/011). Linux "SIGNIFICANT_WORK" in packaging/updater/distribution reflects *engineering scope without architectural risk*, per §13. macOS UI/Filesystem MINOR_WORK items are polish, not correctness.

---

## 19. Architectural Coupling Map

Platform leakage map (leak points in **bold**):

```text
UI (ui_main.py — PyQt6 + fluent widgets)
 │   **explorer Popen (CP0-001)** · win32com/AUMID (guarded) · Consolas (soft)
 │   **updater artifact ranking/installer launch (Windows-shaped, CP0-004/005)**
 ▼
workers/controllers (QThread; platform-clean)
 ▼
alignment engine (alignment_engine_v2.py)
 │   PURE decision core: numpy/scipy + librosa features — NO OS references
 │   find_offset_v2: tempfile + calls media layer   ← the only OS-adjacent seam,
 │                                                      and it is delegated, not owned
 ▼
media extraction/export (auto_sync.py)
 │   **subprocess + imageio-ffmpeg binary (desktop-port fine; mobile blocker)**
 │   **h264_nvenc coupling (CP0-003)** — the only hardware-specific string in the product
 ▼
FFmpeg (per-platform binary via imageio-ffmpeg wheels)
```

Findings:

1. **Layer discipline is already good.** Platform knowledge is confined to the UI shell, the updater's artifact model, and the media layer. The engine contains zero platform constructs.
2. **Engine v2 can be made completely OS-unaware — it already is**, with one caveat: `alignment_engine_v2` imports `imageio_ffmpeg` and `auto_sync.extract_audio` inside its *file entry point* (`find_offset_v2`, lines 877-901). What prevents a formally pure engine is therefore nothing but entry-point placement: moving the "load two files → decide" convenience behind the media adapter seam (which `decide_alignment`/`decide_from_families` already form) leaves the algorithm untouched. No threshold or signal change required — verified by inspection, and the existing test suite (80/80) pins the semantics.
3. The Windows-isms in `auto_sync.py` are a single guarded flag (`_IS_WINDOWS`) affecting only console-window suppression — the correct pattern to extend to future media-adapter branches.

## 20. Recommended Cross-platform Architecture Boundaries

(Conceptual — nothing implemented in CP-0.)

* **Boundary 1 — Engine/mediator:** keep `decide_alignment` array-in/array-out as the *only* engine contract; the file-level `find_offset_v2` becomes the desktop adapter's convenience, not the engine's.
* **Boundary 2 — Media adapter:** extraction/muxing behind an interface (current implementation = subprocess+imageio-ffmpeg). Desktop platforms all satisfy it unchanged; a future Android adapter re-uses the same FFmpeg command surface; an iOS adapter would replace the mechanism (library), keeping the command semantics.
* **Boundary 3 — Feature provider (mobile-only):** the librosa feature calls (`chroma_cens`, `onset_strength`, `melspectrogram`, `hpss`, `pcen`) isolated behind one seam so a numpy/scipy-only mobile implementation can be equivalence-tested against v1.2.0 golden outputs. On desktop this seam is pass-through; zero behavior change.
* **Boundary 4 — Presentation:** reason codes → locale keys (already implemented) stays the only engine→UI channel.
* **Platform shell per OS:** guarded shell modules (AUMID, reveal-in-explorer/open, updater artifacts, packaging spec) — mirroring the existing `_IS_WINDOWS` pattern rather than sprinkling new checks.

None of these boundaries requires touching v1.2.0 alignment behavior; 1–2 are pure re-plumbing, 3 is additive.

## 21. Recommended Phase Sequence

The working hypothesis is confirmed with one re-ordering rationale: macOS proof-of-life is *cheaper* than macOS release (bundling/signing), so proof-of-life phases should both precede packaging phases to fail fast on runtime issues.

```text
CP-1  Linux Proof-of-Life      (run engine+export on real Linux; fix CP0-001/002; probe bundled-binary encoder inventory; CP0-009 diagnostics additions)
CP-2  Linux Packaging/Release  (build host/CI, artifact format decision, updater assets CP0-004/005)
CP-3  macOS Proof-of-Life      (imageio-ffmpeg ≥0.6.0 bump CP0-007, arm64/Intel decision)
CP-4  macOS Packaging/Release  (.app/.icns BUNDLE, signing/notarization, .dmg)

MOB-0 Android Feasibility      (Chaquopy numpy/scipy coverage verification; FFmpeg-on-Android exec spike; PySide6-flavored UI spike)
MOB-1 Android Engine Proof     (librosa-free feature layer, golden-equivalence vs v1.2.0)
...

iOS                            (separate feasibility phase after Android reality is known; subprocess-free FFmpeg design is the gate)
```

Rationale for keeping desktop-first: every mobile blocker (CP0-010/011/012) is independent of desktop port work, while CP-1..CP-4 reuse one codebase with zero architectural change.

---

## 22. Final Verdict

### Primary verdict: **READY_FOR_DESKTOP_PORT**

Linux/macOS can proceed without major architectural restructuring. Evidence: the engine core contains no platform constructs (§5, §19); exactly one unguarded Windows-only UI call exists repo-wide (CP0-001, one-line class of fix); all desktop dependency rows in §12 are Supported (with one macOS-arm64 pin bump, CP0-007); the remaining desktop work is packaging/updater engineering (§9, §10), not architecture.

```text
ANDROID:
BLOCKED_BY_KNOWN_DEPENDENCY
  (librosa → numba/llvmlite/scikit-learn have no Android support — CP0-011;
   FFmpeg subprocess packaging restricted — CP0-010; PyQt6 has no Android
   deployment path — CP0-012. All three are known, enumerable, and each has
   a credible route: numpy/scipy feature layer, jniLibs-packaged FFmpeg,
   PySide6. Feasible after MOB-0 verifies the routes.)

IOS:
SEPARATE_FEASIBILITY_REQUIRED
  (superset of Android's blockers PLUS: subprocess execution forbidden —
   the FFmpeg pipeline architecture itself is invalid on iOS; FFmpegKit
   retired 2025; PySide6 iOS only from Qt ≥6.12; App Store licensing.
   IOS_REQUIRES_SEPARATE_FEASIBILITY_PHASE.)
```

Desktop and mobile verdicts are deliberately not merged: the desktop verdict rests on verified repository evidence; both mobile verdicts rest on verified *dependency absence*, which mobile phases exist to route around without touching the stabilized v1.2.0 alignment behavior.
