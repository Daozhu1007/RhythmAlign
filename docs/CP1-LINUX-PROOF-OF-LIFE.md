# CP-1 — Linux Proof-of-Life (RhythmAlign v1.2.0)

> Status: CP-1 COMPLETE · Date: 2026-09-21 · Verdict: **LINUX_PROOF_CONFIRMED**
> Branch: `cross-platform/linux` (based on `c92e827`, clean base verified before any change)
> Companion evidence (local, gitignored): `results/cp1/` — probe JSONs, decision evidence, GUI screenshots, scripts.

---

## 1. Executive Summary

RhythmAlign's essential product workflow — launch, select video/music, Engine v2 analysis, alignment decision, export, validation, post-export behavior — **runs on real Linux with only three bounded compatibility fixes and zero algorithm change**.

The headline result: Engine v2's decision on the CP-1 real-media pair is **bit-identical across Windows and Linux** (`accepted`, offset `2.995374149659864` s, `ACCEPT_DUAL_FAMILY`), and the same is true inside the packaged Linux PyInstaller runtime. Linux PyInstaller build viability is established: the existing spec pattern builds unmodified and the packaged app completes a real Engine v2 analysis with bundled FFmpeg.

What failed before the fixes (all fixed or recorded):

1. **CP0-001** — the unguarded `explorer /select,` call raised in the export-success slot on Linux (`PermissionError: [Errno 13] Permission denied: 'explorer'`). Fixed by a centralized, tested platform abstraction; export success is now decoupled from shell integration.
2. **Dependency declaration bug (new finding, beyond CP-0's list)** — `requirements.txt` names `PyQt-Fluent-Widgets`, which is the **PyQt5** build of qfluentwidgets ("A fluent design widgets library based on PyQt5" per its own metadata). A fresh install on *any* platform gets the wrong Qt binding; on Linux this aborted the UI stack at startup (SIGABRT, PyQt5+PyQt6 mixed). Fixed: requirements now declare `PyQt6-Fluent-Widgets` — the package Windows dev machines actually use.
3. **CP0-002** — `pywin32` was used but undeclared. Fixed with a Windows-only environment marker.

Diagnostics gained the CP0-009 fields (kernel, libc, Qt platform plugin, FFmpeg H.264/HEVC encoder inventory), and the `use_gpu → h264_nvenc` coupling (CP0-003) is confirmed on Linux as evidence for a future capability-based phase.

---

## 2. Baseline

| Item | Value |
|---|---|
| Product state | v1.2.0 released baseline, zero source drift from tag |
| Starting HEAD | `c92e82763350d70e7d5982de2dcdcb99cebc1e83` |
| Working tree | Clean |
| Windows test suite (pre-change) | `80 passed in 46.57 s` (matches CP-0's record) |
| Linux test suite (pre-change) | **Abort (core dumped)** in `test_ra12e_slider_ui.py` — wrong qfluentwidgets binding (see §6); excluding the two qfluentwidgets-driven UI test files: **76 passed in 34.65 s** |

Pre-change versions (Windows audit machine): Python 3.10.11, numpy 1.24.4, scipy 1.10.1, librosa 0.11.0, imageio-ffmpeg 0.5.1 (FFmpeg 7.1), PyQt6 6.7.1, PyQt6-Fluent-Widgets 1.11.1, PyInstaller 6.18.0.

## 3. Git State

| Item | Value |
|---|---|
| Branch at start | `cross-platform/linux` at `c92e827` (verified per mission §2) |
| Branch publication | Pushed to `origin/cross-platform/linux` before substantive changes |
| Work location | All CP-1 changes made in the Windows checkout; all Linux execution ran against the same tree from WSL2 (`/mnt/d/Code/RhythmAlign`) |
| Ending state | See §21/owner return |
| `research/applied-system-paper` | Untouched (no research branch commits used) |
| `experiments/applied_system/` | Untouched |

## 4. Linux Environment

| Item | Value |
|---|---|
| Distro | Ubuntu 24.04.4 LTS (WSL2) |
| Kernel | 6.6.87.2-microsoft-standard-WSL2 |
| Architecture | x86_64 |
| glibc | 2.39 (build-host floor note for CP-2) |
| Python | 3.12.3 (`pip` 26.2.1, venv at `~/venvs/ra-cp1`) |
| Qt / PyQt6 | Qt 6.11.2 / PyQt6 6.11.0 |
| PyQt6-Fluent-Widgets | 1.11.3 (+ PyQt6-Frameless-Window 0.8.2) |
| PyInstaller | 6.22.3 |
| imageio-ffmpeg | 0.6.0 → bundled `ffmpeg-linux-x86_64-v7.0.2` (static) |
| NumPy / SciPy | 2.5.3 / 1.18.1 |
| librosa | 1.0.0 (numba 0.67.0 / llvmlite 0.49.0, soundfile 0.14.0, soxr 1.1.0) |
| Display backend | **WSLg — Wayland** (`QGuiApplication.platformName()` = `wayland`); `xvfb`-style offscreen (`QT_QPA_PLATFORM=offscreen`) used for test-suite runs |
| GPU | NVIDIA GeForce RTX 4060 Laptop (visible via WSL `nvidia-smi`) |
| Environment split | Core/media + GUI tests + GUI proof + PyInstaller: Linux (WSL2). Windows regression suite: Windows host. |

Note: Linux resolved newer dependency versions than the Windows dev machine (numpy 2.x, librosa 1.0.0, imageio-ffmpeg 0.6.0, Qt 6.11) because `requirements.txt` floors are open (`>=`). Cross-platform behavior was nevertheless identical (§11), which strengthens portability evidence. The Windows→0.6.0 imageio-ffmpeg bump is CP0-007 territory (macOS arm64), not changed here.

## 5. Pre-fix Failure Reproduction

Mission §7 checklist against the unmodified tree (evidence: `results/cp1/prefix_probe.json`):

| # | Check | Result on stock code |
|---|---|---|
| 1 | Product imports (`auto_sync`, `alignment_engine_v2`, `diagnostics`, `update_checker`) | PASS |
| 2 | `ui_main` import | PASS (module scope) |
| 3 | Configuration directory init | PASS — `~/.config/RhythmAlign/config.json` (XDG-correct, verified by write/read) |
| 4 | Assets | PASS — 6 files, `logo.ico` + `logo.png` present |
| 5 | Locales | PASS — `en_US.json`, `zh_CN.json` parse, keys present |
| 6 | FFmpeg discovery | PASS — static `ffmpeg-linux-x86_64-v7.0.2`, mode `755`, executes |
| 7 | Diagnostics generation | PASS (35-line report) |
| 8 | Engine v2 import + execution | PASS — `accepted`, offset `2.9954` (true: 3.0), `ACCEPT_DUAL_FAMILY`, 2.8 s |
| 9 | Media extraction | PASS — 2.1 MB WAV via pcm_s16le |
| 10 | Export (stream copy + AAC mix) | PASS — valid 48.02 s MP4, h264 + aac |
| 11 | Post-export reveal | **FAIL — `PermissionError: [Errno 13] Permission denied: 'explorer'`** raised by the unguarded call (`ui_main.py:921`); on stock Linux it would escape `task_finished`, suppress the success InfoBar, and print a traceback after every successful export. Confirms CP0-001 exactly as predicted. |
| 12 | GUI startup | **FAIL — SIGABRT (-6)**, "QWidget: Must construct a QApplication before a QWidget": qfluentwidgets resolved to the PyQt5 build (§6 root cause), mixing PyQt5+PyQt6 in one process |

## 6. CP-0 Issues Addressed

| CP-0 item | Action in CP-1 |
|---|---|
| **CP0-001** (unguarded `explorer`, P2) | **Fixed** — new `file_reveal.py` abstraction; wired into `SyncInterface.task_finished`; reveal failure logged, never raised (§7) |
| **CP0-002** (undeclared `pywin32`, P3) | **Fixed** — `pywin32>=306; sys_platform == "win32"` declared in `requirements.txt` |
| **CP0-009** (diagnostics gaps, P3) | **Fixed (additive)** — kernel, libc, Qt platform plugin, FFmpeg H.264/HEVC encoder inventory added (§16) |
| **New: fluent-widgets binding** | **Fixed** — `requirements.txt` now names `PyQt6-Fluent-Widgets` (CP-0 §12 marked the Linux cell "S" via upstream claims; the *declared* package name was the PyQt5 build — the dependency declaration itself was the defect) |
| CP0-003 (`use_gpu` → `h264_nvenc`) | Evidence only (§10), fix deferred per mission |
| CP0-006/007/004/005/008/013 | Untouched — not required for CP-1 (§9 of the mission); deferred to CP-2/CP-3 |

## 7. Code Changes

Zero semantic diff in `alignment_engine_v2.py` and `auto_sync.py` (verified: `git diff` on both files is empty; §14 of the mission). Complete change set:

| File | Change |
|---|---|
| `file_reveal.py` (new) | Platform reveal abstraction: `explorer /select,` (Windows, unchanged), `open -R` (macOS), `xdg-open <folder>` (other). Returns `True`/`False`, never raises. Dispatch table with injectable platform name for tests. |
| `ui_main.py` | +1 import; success slot now calls `reveal_in_file_manager(path)` and logs `log_reveal_failed` on failure. Windows `explorer /select,` behavior preserved verbatim inside the abstraction. No other UI change. |
| `locales/en_US.json`, `zh_CN.json` | +1 key: `log_reveal_failed` ("File manager could not be opened (export completed): {0}" / "无法打开文件管理器（导出已完成）: {0}") |
| `requirements.txt` | `PyQt-Fluent-Widgets>=1.3` → `PyQt6-Fluent-Widgets>=1.3`; `pywin32>=306; sys_platform == "win32"` added |
| `diagnostics.py` | Additive: `_qt_platform_name`, `_libc_label`, `_ffmpeg_encoder_inventory` + Kernel/Libc/Qt-platform-plugin/encoder lines |
| `tests/test_file_reveal.py` (new) | 10 tests: per-platform reveal commands, no-xdg-open → False, never-raises contract, empty path, dispatch, host detection, and two `task_finished` integration tests (offscreen Qt): export success survives reveal failure; reveal skipped when `open_folder` off |
| `tests/test_diagnostics.py` (new) | 4 tests: new report fields present; Qt-platform-name degrades headless; encoder probe degrades on missing binary; real bundled binary exposes `libx264` |

Design principle (mission §8.1): **export success ≠ shell integration success**. The media output is the primary operation; revealing it is best-effort and centralized.

## 8. FFmpeg Runtime Evidence

Binary returned by `imageio_ffmpeg.get_ffmpeg_exe()` on Linux (evidence: `results/cp1/ffmpeg_evidence.json`):

| Property | Value |
|---|---|
| Path | `…/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2` (per-platform wheel binary; also bundled at `_internal/imageio_ffmpeg/binaries/` in the PyInstaller output) |
| Source / package | imageio-ffmpeg 0.6.0 manylinux wheel; upstream static GPL build (`johnvansickle.com`) |
| Version | ffmpeg 7.0.2-static |
| Executable permission | `755` — executes normally (returncode 0 on `-version`) |
| Size | ~78 MB static binary |

Functionality verified with the real media pair (all PASS): input probing (Duration parse), audio extraction (`pcm_s16le` WAV), audio-stream detection, AAC encode (product exports), **libx264 encode** (explicit re-encode probe), stream copy (`-c:v copy`, the product default), muxing (`+faststart`, `+genpts`), metadata stripping (`-map_metadata -1`; the mov muxer itself always writes container brands — identical on Windows), final MP4 output.

## 9. Encoder Inventory

`ffmpeg -encoders` on the bundled Linux binary:

| Encoder | Present |
|---|---|
| `libx264` | **YES** (also `libx264rgb`) |
| `h264_nvenc` | no |
| `h264_vaapi` | no |
| `h264_qsv` | no |
| `h264_amf` / `h264_videotoolbox` | no |
| Other hardware | `h264_v4l2m2m`, `hevc_v4l2m2m` only (embedded-oriented; not relevant to desktop GPUs) |

Contrast with the Windows binary (CP-0): carries `h264_nvenc`, `h264_amf`, `h264_qsv` alongside `libx264`. **The bundled Linux binary is effectively software-only** — relevant context for CP-2's artifact decisions and any future GPU promise.

## 10. Engine v2 Linux Execution

- `alignment_engine_v2.find_offset_v2` executes on Linux with stock code (pre-fix AND post-fix).
- Decision (§11 table): bit-identical to Windows — same status, reason code, and offset float.
- Frozen-runtime decision also bit-identical (§15).
- Semantic protection: `git diff alignment_engine_v2.py auto_sync.py` = empty. No thresholds, scoring, evidence-family, offset semantics, or decision-rule code was touched in CP-1.

## 11. Real Media Test

Pair: deterministic synthetic handcam+BGM pair generated for CP-1 (`results/cp1/gen_media.py`, scratch): 45 s structured music (120 BPM kicks, chord progression, hats → `music_track.m4a`), and a 48 s 640×360 H.264 video whose audio embeds the music with a **known true offset of +3.000 s** plus a 3 s ambience head and a low noise floor. Real MP4/AAC media encoded with the product's own FFmpeg; input SHA-256s recorded and verified unchanged after the run. Repository-owned research material was not used.

| Record | Linux (WSL2) | Windows (baseline) |
|---|---|---|
| Video / music duration | 48.0 s / 45.0 s | 48.0 s / 45.0 s |
| Engine v2 decision | `accepted` | `accepted` |
| Reason code | `ACCEPT_DUAL_FAMILY` | `ACCEPT_DUAL_FAMILY` |
| Estimated offset | **2.995374149659864 s** | **2.995374149659864 s** |
| Error vs true offset | 4.6 ms | 4.6 ms |
| Export settings | stream copy, `use_gpu=false`, 10000k, orig 1.2 / music 0.6, manual 0.0 | identical |
| FFmpeg binary | linux-x86_64 v7.0.2 static | win-x86_64 v7.1 |
| Output | `handcam_synced.mp4`, 48.02 s, h264+aac | `handcam_synced.mp4`, 48.02 s, h264+aac |
| Export return | success (no exception; `.partial` renamed onto output) | success |
| Comparison | **Bit-identical decision — no floating-point variation at all** | — |

Evidence: `results/cp1/evidence_decision_linux.json`, `evidence_decision_win32.json`, `real_media_proof_{linux,win32}.json`.

## 12. Export Validation

Not relying on FFmpeg's return code (`mix_and_export` raises on nonzero anyway). Verified on the Linux export (evidence: `real_media_proof_linux.json`):

- output exists, size > 0 (5.6 MB)
- FFmpeg reopens the file; video stream (h264 High, yuv420p) and audio stream (AAC LC, 44.1 kHz stereo) present
- container is MP4; duration 48.02 s vs source 48.0 s (reasonable)
- **no `.partial` file remains** — the sibling-temp + `os.replace` publish succeeded on Linux (POSIX atomic rename)
- sources unchanged (SHA-256 match before/after for video and music)
- temp files cleaned: output directory contains exactly the exported file

## 13. GUI Validation

**Interactive-equivalent GUI proof on the real WSLg display (Wayland)** — not a headless claim. Driver: `results/cp1/gui_proof.py`; screenshots: `results/cp1/gui/*.png`.

- `RhythmAlignApp` constructs, shows, and renders on the **wayland** platform plugin (2100×1440 HiDPI): navigation, all four pages (Sync/Analyze/About/Settings), text, `logo.ico` window icon, dark **and** light themes render correctly. CJK text renders correctly once a CJK system font is present (the minimal WSL Ubuntu initially had none — tofu boxes; installing `Noto Sans CJK SC` into the user font dir resolved it. Environment gap, not a product defect; fonts-noto-cjk is standard on desktop distros).
- Locales load (`en_US`, `zh_CN` both parse and render).
- **Full product workflow driven through the real UI objects**: file inputs set → `btn_start` clicked → production `SyncWorker` QThread runs analysis on the real pair → log shows decision `+2.9954 s` → stream-copy export → success log `处理成功！保存至: handcam_gui_synced.mp4` → progress UI reached 100% → result state displayed → export file exists (5.6 MB).
- **Post-export reveal behaved per the new contract on Linux**: `xdg-open` could not open a file manager (none installed in WSLg) → failure was logged (`无法打开文件管理器（导出已完成）: …`), the success InfoBar still fired, the start button re-enabled, and the application remained alive and usable (page switches verified after export). `GUI_INTERACTIVE_VALIDATION_PENDING` is **not** applicable: startup, rendering, navigation, and the complete workflow were exercised; not mechanized by a human pointer were drag-and-drop and native file-dialog interaction (file-dialog *stubbing* was used to choose the save path — the dialog-open path itself is Qt cross-platform per CP-0).

## 14. PyInstaller Build Probe

| Item | Value |
|---|---|
| Build command | `pyinstaller results/cp1/probe_spec.spec --noconfirm --clean --workpath ~/ra_build --distpath ~/ra_dist` (probe-only spec copy with absolute paths + an env-gated runtime hook; **product `RhythmAlign.spec` unchanged**, nothing committed) |
| Python / PyInstaller | 3.12.3 / 6.22.3 |
| Result | **SUCCESS** (onedir build in ~50 s) |
| Artifact | onedir: `RhythmAlign/RhythmAlign` ELF + `_internal/` |
| Bundled FFmpeg | `_internal/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2` — present and executable |
| Qt plugins | wayland/xcb/offscreen plugins collected; app started on the **wayland** plugin |
| Important warnings | 43, all benign: (a) `user32/shell32/ole32 required via ctypes not found` — the guarded Windows-only imports; (b) `libxkbcommon-x11/libxcb-*` unresolvable as dependencies of the **xcb** plugins — not installed in the minimal WSL userspace; irrelevant to the wayland backend that was actually used, and a distro-package concern for CP-2's supported-baseline decision |

## 15. Packaged Runtime Probe

Env-gated runtime hook (probe spec only) executed inside the frozen Linux build (`results/cp1/frozen_probe.json`):

| Check | Result |
|---|---|
| Executable starts, `sys.frozen`, `_MEIPASS` | PASS |
| Bundled resources | assets/, logo.ico, config.json present |
| Locales load | en_US + zh_CN present and parse |
| FFmpeg from packaged runtime | found in `_internal`, executes (7.0.2-static) |
| Diagnostics run in frozen runtime | PASS (39 lines incl. encoder inventory) |
| Engine v2 imports + executes on the real pair | **PASS — `accepted`, offset `2.995374149659864`, `ACCEPT_DUAL_FAMILY` (bit-identical)** |
| Normal startup (no probe env) | Alive after 12 s, empty stderr (no Qt plugin failure), clean SIGTERM exit |

## 16. Diagnostics Changes

Additive, platform-neutral, and safe (mission §12 requirements met: never crashes startup, graceful degradation, one bounded `-encoders` subprocess with 5 s timeout, no external tools):

- `[System]`: `Kernel:`, `Libc:` (glibc version via `platform.libc_ver()`), `Qt platform plugin:` (live `QGuiApplication.platformName()`, or "application not created" headless)
- `[FFmpeg]`: `imageio-ffmpeg H.264/HEVC encoders:` — filtered `-encoders` inventory (`libx264*`, `h264_*`, `hevc_*`); on this Linux env it reports `libx264, libx264rgb, h264_v4l2m2m, hevc_v4l2m2m`
- Fluent-widgets version line now probes `PyQt6-Fluent-Widgets` (the dist name requirements actually installs)

## 17. Windows Regression Assessment

- Full Windows suite after changes: **94 passed** (80 pre-existing + 14 new).
- `explorer /select,` reveal preserved verbatim (pinned by `test_windows_reveal_selects_file_in_explorer`); the only change is that a reveal failure can no longer escape the success slot.
- `AppUserModelID` logic, shortcut resolution, `CREATE_NO_WINDOW` choke points: untouched (diff is confined to the import block + `task_finished`).
- Inno Setup script, updater, `update.json`, release manifest, `RhythmAlign.spec`: untouched.
- Windows host used for all Windows test runs; Linux for all Linux runs (preferred split per mission §21).

## 18. Automated Tests

| Suite | Pre-change | Post-change |
|---|---|---|
| Windows host | 80 passed (46.6 s) | **94 passed** (33.0 s) |
| Linux (WSL2, offscreen Qt) | abort in UI tests (wrong binding); 76 passed excluding them | **94 passed** (35.5 s) |

New tests (14): platform reveal ×10 (incl. two `task_finished` integration tests), diagnostics ×4. Existing Windows-oriented tests continue to pass unchanged. Tests avoid requiring a graphical desktop (offscreen Qt / mocks only).

## 19. Remaining Linux Gaps

1. **Release engineering (CP-2)** — build-host/distro-baseline policy (glibc 2.39 build floor observed here; PyInstaller cannot cross-compile), artifact format (tar.gz/AppImage), desktop entry + PNG icon, updater assets for Linux (CP0-004/005).
2. **xcb plugin system libraries** — on minimal installs the xcb backend needs distro packages (`libxkbcommon-x11`, `libxcb-*`); wayland worked here. Belongs in CP-2's supported-baseline decision.
3. **CJK font availability on minimal distros** — UI text needs a CJK system font (e.g. `fonts-noto-cjk`); consider documenting or bundling a font fallback at CP-2.
4. **GPU acceleration on Linux** — bundled binary has no desktop hardware encoders; `use_gpu=true` would fail with "Encoder not found" even with an NVIDIA GPU present. Capability-based encoder selection (CP0-003) is the future fix; CP-1 acceptance path correctly uses `use_gpu=false`.
5. **Native interactive GUI pass on a real desktop session** — this proof automated the real app on WSLg/Wayland; a human-pointer pass (drag-drop, native dialogs) on a stock desktop distro remains good hygiene before release.

## 20. CP-2 Entry Criteria

All mission §24 mandatory criteria are met, and all three preferred criteria (interactive GUI workflow, packaged executable launch, packaged real workflow) are evidenced. CP-2 may begin.

## 21. Final Verdict

**LINUX_PROOF_CONFIRMED** — the essential RhythmAlign workflow runs on real Linux with bounded compatibility fixes; no architectural blocker remains.

Recommended next phase: **CP-2 — Linux Packaging & Release Engineering**.
