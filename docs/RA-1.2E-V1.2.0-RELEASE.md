# RA-1.2E — v1.2.0 Release Candidate Preparation + Human Release Gate

Status: **RC1 built and validated; owner returned `OWNER_RC_PASS`;
RC2 built (final UI polish only, §14); owner returned `OWNER_RC2_PASS`
(§15); FINAL RELEASE AUTHORIZED — release actions in progress (§16).**

Owner test status: **RC1 = `OWNER_RC_PASS`**, **RC2 =
`OWNER_RC2_PASS`** (received before final release authorization;
nothing below is fabricated).

---

## 1. Baseline audit (before any change)

| item | value |
|---|---|
| Branch | `main` |
| HEAD at task start | `67c8cbd406a51659bb1f7c3d2059898ec4ee17b6` (`fix: RA-1.2D1 temporal-support gate …`) |
| `origin/main` | identical to HEAD (verified after `git fetch`) |
| Working tree | clean |
| Baseline suite | `python -m pytest tests/ -q` → **76 passed** in 26.27 s |
| Astra research branch | `astra/alignment-research-wip` @ research commit `8b78eb1`, local-only, **unmerged, untouched** |

Known deviation recorded: a bare `python -m pytest -q` from the repo
root additionally collects `experiments/low_snr_alignment/soak_test.py`
(matches `*_test.py`), which imports `psutil` — an undeclared,
experiments-only dependency — and errors at collection. The file
contains no `test_*` functions. The canonical suite command for this
repository is `python -m pytest tests/ -q`; nothing was changed about
this during RA-1.2E.

Inspected per task list: `app_info.py`, `update.json`,
`bundled_update.json`, `update_checker.py`, `RhythmAlign.spec`,
`RhythmAlign.iss`, `README.md`, `README_zh.md`, `ui_main.py`,
`alignment_engine_v2.py` (untouched this phase), both RA-1.2D/1.2D1
reports, `RELEASE.md`, and the v1.1.2 tag / release conventions
(`git tag -l`, `gh release view v1.1.2`, `release/` local archives).

## 2. Algorithm freeze

No alignment-algorithm change was made or attempted in RA-1.2E:
Engine v2 thresholds, `max_top_bin_share = 0.25`, bin width 1.0 s,
candidate generation, ACCEPT/ABSTAIN policy, and the room-grid residual
are all untouched. `alignment_engine_v2.py` has a **zero-line diff**
this phase (verified via `git diff 67c8cbd..2d0a922 --stat`).

## 3. Documentation / evidence corrections (pre-release)

### 3.1 RA-1.2D report (`docs/RA-1.2D-DEFAULT-INTEGRATION.md`)

- §19 previously claimed `auto_sync.py — unchanged`, contradicting
  §10 of the same report. Corrected: RA-1.2D changed exactly one thing
  in `auto_sync.py`, the analysis-ETA realtime factor **45 → 75**;
  legacy decision logic untouched.
- §19 previously claimed `RhythmAlign.spec — unchanged`,
  contradicting §16. Corrected: RA-1.2D added `'PySide6'` to the
  spec's `excludes` (environment-drift fix). `app_info.py` really was
  unchanged; the sentence now says so separately.
- §17 previously said the engine *code* was "byte-identical" to the
  RA-1.2C soak-verified state. Corrected: decision policy / thresholds
  / decision logic unchanged; the file itself had three comment/label
  edits (module docstring, `ENGINE_LABEL`, one function docstring).
- §21 wording adjusted the same way ("byte-unchanged" → unchanged
  decision logic). Commit history was not rewritten; corrections are
  marked as RA-1.2E wording fixes in place.

### 3.2 RA-1.2D1 report + result JSON GT populations

The number **0.0923 s** is `|12.4923356 − 12.4|` for 零对话
(`lingduihua_132`), whose ground truth is an independently established
**manual estimate, +12.4 ± 0.4 s** — it is not exact GT and was
wrongly reported as the cross-population "max GT error".

Corrected in `docs/RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md` (§8, §9,
§17), separating the metrics:

1. **Exact semi-synthetic GT** (26 accepted cases): max |offset error|
   = **0.0137 s** (`ss_cal_001`), all within the 0.15 s tolerance.
2. **零对话 manual GT**: accepted at **+12.4923 s**; deviation from the
   interval center ≈ **0.0923 s**; result lies **inside** +12.4 ± 0.4 s.

`experiments/ra12d1_temporal_support/results/integrated_full_positives.json`
summary was corrected deterministically from its own raw rows (rows
byte-identical, verified by hash before/after): the single mixed scalar
`max_abs_offset_error` was replaced by
`max_abs_offset_error_exact_gt_semi_synthetic` = 0.013650793650793247,
an explicit `manual_gt_cases` entry for `lingduihua_132`, and a
`gt_population_note` recording the pre-RA-1.2E mixed value and why it
was separated. The committed RA-1.2D1 evidence files were **restored
byte-identical from git** after the RC regression re-runs (below).

## 4. Version bump 1.1.2 → 1.2.0

Audited propagation (per `RELEASE.md` checklist), all updated:

| location | change |
|---|---|
| `app_info.py` | `APP_VERSION = "1.2.0"` (drives GUI display + update check; no hardcoded version in `ui_main.py` or `RhythmAlign.spec`) |
| `locales/zh_CN.json` | `app_title` = "RhythmAlign v1.2.0", `about_ver` = "v1.2.0" |
| `locales/en_US.json` | same two keys |
| `README.md` | badge `version-v1.2.0-blue` |
| `README_zh.md` | badge `version-v1.2.0-blue` |
| `RhythmAlign.iss` | `#define MyAppVersion "1.2.0"`, `OutputBaseFilename=RhythmAlign_v1.2.0_Setup` |
| `bundled_update.json` | offline fallback manifest → 1.2.0 (bundled inside the app; not public) |

Deliberately **NOT** changed yet:

| location | reason |
|---|---|
| `update.json` (live manifest) | served from raw `main`; must keep pointing at the existing v1.1.2 assets until the real v1.2.0 release is published (task §6: never point users at nonexistent assets). Finalized only in the post-PASS release actions. |
| git tag / GitHub Release | hard-stopped until `OWNER_RC_PASS`. |

## 5. User-facing story (READMEs)

`README.md` and `README_zh.md` were rewritten for the v1.2.0 story in
user language: multi-evidence alignment (melodic movement, rhythmic
onsets, noise-robust spectral texture), cross-checked candidates,
temporal-distribution check against brief-event matches, and
"refuses to guess" safe-stop behavior; manual ±500 ms slider described
as fine adjustment on top of a successful automatic alignment. The
claims prohibited by the task (perfect alignment, universal
low-volume recovery, zero false positives, verified accuracy over all
29 recordings, no-audio alignment, in-product recovery of every
abstention) appear nowhere. The v1-engine "How Alignment Works"
description (chroma CENS delta + onset blend + Z-score gate) was
replaced accordingly; project layout now lists
`alignment_engine_v2.py` as the default engine.

## 6. Release notes

`release_notes_v1.2.0.md` drafted per `RELEASE.md` (quote intro, core
features, `v1.2.0 重大更新 | Major Changes` with 🚀/🐛 sections,
upgrade/compatibility notes, downloads, installation, known issues,
technical appendix without Z-score internals, license, signature).
Covers: Engine v2, the 零对话 low-SNR improvement, evidence-gated
ACCEPT/ABSTAIN behavior, temporal-support safeguard, Analyze-page
abstention display, manual fine-adjust wording correction, PySide6
packaging exclusion (framed as build-reliability only), and
compatibility/upgrade notes. SHA-256 section filled with the real
artifact hashes. Per `RELEASE.md` 善后 rules the file stays
**untracked** (local carrier for `gh release create -F`); its reviewed
content is preserved verbatim in Appendix A of this document.

## 7. Clean release build (RC1)

Environment: Windows 11 x64 (10.0.26200), Python 3.10.11 (`.venv`),
PyInstaller 6.19.0, Inno Setup 6.7.3, PyQt6 6.10.2,
PyQt6-Fluent-Widgets 1.11.1, librosa 0.11.0, imageio-ffmpeg 0.6.0.

Steps (after deleting `build/`, `dist/`, all `__pycache__/`, on clean
tree at commit `2d0a922`):

```bash
python -m PyInstaller RhythmAlign.spec --clean --noconfirm   # ~106 s, success
"D:\Program Files\Inno Setup 6\ISCC.exe" RhythmAlign.iss     # ~131 s, success
powershell -Command "Compress-Archive -Path 'dist\RhythmAlign\*' -DestinationPath 'dist\RhythmAlign-v1.2.0-Portable.zip' -Force"
```

The RA-1.2D PySide6 exclusion remains valid: the dev environment still
has PySide6 installed, the build succeeded with it excluded, and the
bundle contains **0** PySide6/shiboken files (verified below).

Artifacts (nothing uploaded):

| file | size (bytes) | SHA-256 |
|---|---|---|
| `dist/RhythmAlign_v1.2.0_Setup.exe` | 118,717,743 | `CE34DDCB4BDDA1A19243A4384615576825C90856226BC605181E923A0954EA8E` |
| `dist/RhythmAlign-v1.2.0-Portable.zip` | 176,290,844 | `BFB5456BAC064AFB1E6BCC3BA248BB533DEBF70B65B3BBD10647A979E31E0C64` |

## 8. Frozen-build technical smoke — PASS

- Bundle verified: `locales/{zh_CN,en_US}.json` present and containing
  "RhythmAlign v1.2.0"; `assets/` (icon, screenshots);
  `bundled_update.json` at 1.2.0; FFmpeg binary
  `_internal/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe`;
  `alignment_engine_v2` present in the PyInstaller module graph
  (Analysis toc) with zero warnings for it; PySide6 appears only in the
  spec excludes list and **0** PySide6 files exist anywhere in the
  bundle.
- Launch/stay-alive smoke: `RhythmAlign.exe` started from the frozen
  bundle, stayed alive 12 s (225 MB working set — full Qt +
  qfluentwidgets + Engine v2 + librosa import chain), closed
  gracefully via `CloseMainWindow()` (no force-kill needed).
- Console-window suppression on Windows subprocesses is unchanged
  (`CREATE_NO_WINDOW` in `auto_sync.py`, single choke point); no
  subprocess-related code changed this phase.

## 9. RC alignment regression (frozen code, no retuning)

All checks executed on the RC code state (commit `2d0a922`); raw RC
outputs archived under gitignored `results/ra12e_rc/`, and the
committed RA-1.2D1 evidence JSONs were restored byte-identical after
the re-runs.

| check | expectation | result |
|---|---|---|
| `python -m pytest tests/ -q` | 76 passed | **76 passed** in 26.46 s (incl. all 11 temporal-support tests) |
| Astra blocker `tr_lingduihua` → `tr_yanwulieche` (production `find_offset_v2`) | `ABSTAIN_CONCENTRATED_EVIDENCE` | **abstained**, `ABSTAIN_CONCENTRATED_EVIDENCE`, 6.05 s (was ACCEPT +1.462857 s pre-RA-1.2D1) |
| 零对话 (`lingduihua_132`) | ACCEPT ≈ +12.4923 s | **+12.4923 s** (temporal support 0.0836 ≤ 0.25) |
| Full positive corpus (85 cases through integrated engine) | 55/55 accepts preserved | **55/55 accepted set and offsets identical** to committed baseline; 30/30 abstains identical; semi-synthetic max |error| 0.0137 s |
| 18 DEV known Astra wrong accepts (incl. blocker), production path | all rejected | **18/18** `ABSTAIN_CONCENTRATED_EVIDENCE` |
| 156 held-out clean wrong-song pairs (incl. 4 known component-B accepts) | all abstain | **156/156** SAFE_ABSTAIN; blocker SAFE_ABSTAIN |
| RA-1.2B mismatches (10) + hard negatives (10) + tiled (4) | all abstain | **24/24** SAFE_ABSTAIN |
| Known residual room-grid case (`haiditan_ds_1` × `tr_hongzhoutian`) | documented residual, unchanged | still accepted (unchanged from RA-1.2D1 §11; not a regression, not retuned) |

## 10. Product-path ACCEPT/ABSTAIN smokes (real SyncWorker)

Via `experiments/low_snr_alignment/product_smoke.py` (real worker, real
FFmpeg extraction, real `mix_and_export`, no mocks) and the new
`experiments/low_snr_alignment/blocker_product_smoke.py`:

| case | expectation | result |
|---|---|---|
| `lingduihua_132` (零对话) | ACCEPT, export exactly once | **PASS** — accepted +12.4923 s, output created, temp dir removed (11.2 s) |
| `lividi_132` (normal strong) | ACCEPT, export exactly once | **PASS** — +9.9149 s (CASE A), output created (9.9 s) |
| `mm_queen_x_lingduihua` (ordinary wrong track) | ABSTAIN, no export | **PASS** — `ABSTAIN_NO_CLUSTER_MEETS_FLOORS`, no output, localized safe-stop message (6.5 s) |
| Astra blocker (`tr_lingduihua` video × `tr_yanwulieche` music) | ABSTAIN, no export, no v1 fallback | **PASS** — `ABSTAIN_CONCENTRATED_EVIDENCE`, 0 export-progress entries, `auto_sync.find_offset` booby-trap never triggered, correct user message (6.2 s) |

All temporary outputs were removed after each smoke.

## 11. Owner test package (local only, unpublished)

- `D:\Code\RhythmAlign\dist\rc\RhythmAlign-v1.2.0-RC1-Setup.exe`
  — byte-identical copy of `RhythmAlign_v1.2.0_Setup.exe`
  (SHA-256 equal to §7), so the owner tests exactly the shipping bytes.
- `D:\Code\RhythmAlign\dist\rc\RhythmAlign-v1.2.0-RC1-portable\`
  — folder copy of the frozen bundle.
- `D:\Code\RhythmAlign\dist\rc\OWNER-TEST-CHECKLIST-v1.2.0-RC1.md`
  — 10-point manual checklist (launch, version display, strong-song
  alignment, 零对话, deliberate wrong-track abstention, zh/en UI,
  manual ±500 ms fine-adjust, real export playback, restart/settings).

`dist/` is gitignored; nothing was uploaded anywhere.

## 12. Hard stop — human release gate

This phase ends here by instruction. Until the owner returns
`OWNER_RC_PASS`:

- no `v1.2.0` tag, no GitHub Release, no asset upload,
- no public manifest change (`update.json` still serves v1.1.2),
- no further algorithm work (frozen).

After PASS, the remaining RA-1.2E actions are: final pre-release audit
(tree clean, tests, hash equality with owner-tested artifacts, version
consistency, manifest URLs/hashes, no RC/debug naming leakage, no
personal paths, Astra branch unmerged), tag + push, GitHub Release with
the exact assets and reviewed notes, publish finalized `update.json`
(v1.2.0 URLs/hashes; upgrade comparison `1.1.2 → 1.2.0` verified via
`update_checker.is_newer_version`), verify the release page, and append
the post-PASS section here.

## 13. Final Git state (RC phase)

- `2d0a922` — `chore: bump version to v1.2.0 and prepare release
  (RA-1.2E RC1)` (version bump, READMEs, bundled_update, report
  corrections, JSON GT separation; `update.json` untouched).
- RA-1.2E report + `experiments/low_snr_alignment/
  blocker_product_smoke.py` committed in the docs commit accompanying
  this file. No tag, no release, nothing published.
- Astra branch `astra/alignment-research-wip` remains local-only and
  unmerged.

---

## Appendix A — reviewed release notes (verbatim carrier copy)

The file `release_notes_v1.2.0.md` stays local and untracked per
RELEASE.md 善后 rules; its reviewed content is preserved verbatim below.

````markdown
> 音游手元音频自动对齐工具 | Auto Audio-Video Sync for Rhythm Game Hand-Cams

---

## 核心特性 | Core Features

- 多证据融合自动对齐：综合旋律走向、节奏起振、抗噪声谱纹理等多种独立证据交叉验证，而不是信任任何单一特征。
- 证据门控安全停止：证据不足、模糊或仅靠短暂片段支撑时，明确说明原因并停止，不导出错误视频。
- 默认视频流直拷，只重建音轨，保留原画质；可选 NVIDIA NVENC 重编码。
- 纯分析模式、可复制诊断报告、内置检查更新（含 SHA256 校验）。
- 简体中文 / English 双语界面，浅色/深色主题，可跟随 Windows 系统主题。

---

## v1.2.0 重大更新 | Major Changes

### 🚀 优化与重构

- **对齐引擎全面升级为 Engine v2**：多证据融合 + 证据门控决策。在安静手元、强噪声、重复谱面段落等困难录音下，自动对齐显著更稳。
- **安静录音实测改善**：此前旧引擎无法自动对齐的安静手元录音（如「零对话」）现在可以正确自动对齐，并通过实听验证。
- **新增 ACCEPT/ABSTAIN 安全机制**：只有当多种独立证据一致指向同一偏移时才采纳结果；证据不可靠时，对齐页与纯分析页会明确显示「无法可靠确定」，不导出、不编造数字、也不回退到旧引擎。
- **新增时间支撑校验**：拒绝仅由一小段音频（一声敲击、一个音效）支撑的短暂匹配，防止「错歌被对齐」的假阳性结果。
- **手动偏移语义修正**：±500 ms 滑块明确定位为「成功自动对齐之后的毫秒级微调」（叠加在自动结果之上），不再被宣传为自动对齐失败后的完整手动方案。

### 🐛 问题修复

- 修复困难录音下「自信地给出错误偏移并导出」的风险：这类情况现在会安全停止，并给出具体原因（证据不足 / 偏移模糊 / 证据过于集中 / 有效重叠过短）。
- 分析进度预估按 Engine v2 实测耗时重新校准，减少预计剩余时间的高估。
- 打包健壮性：构建时排除开发环境中误装的 PySide6，避免 PyInstaller 因双 Qt 绑定而构建失败（对最终用户无影响，仅提升构建可重复性）。

---

## 升级与兼容性 | Compatibility & Upgrade Notes

- 从 v1.1.x 可直接覆盖安装或解压，设置与工作流程保持不变。
- **行为变化**：以前「总会给出一个偏移」的素材，现在可能显示「无法可靠确定」并安全停止。这是有意的保护行为，不是故障；请确认所选音乐确为视频中实际播放的曲目后重试。
- 自动对齐成功后的使用体验与之前一致；手动滑块仍然是微调工具。
- 纯分析模式在证据不足时显示「无法可靠确定」，不再输出任何可能误导的数字。

---

## 下载 | Downloads

| 类型 | 文件名 |
|---|---|
| 安装版 (推荐) | `RhythmAlign_v1.2.0_Setup.exe` |
| 便携版 | `RhythmAlign-v1.2.0-Portable.zip` |

---

## 安装说明 | Installation

**Windows 10/11 x64**:
- **Setup 版**: 双击安装程序，按向导完成安装。自动创建桌面与开始菜单快捷方式。
- **Portable 版**: 解压 ZIP 到任意目录，直接运行 `RhythmAlign.exe`。

首次启动时如需 Microsoft Visual C++ Redistributable，请从 [微软官方](https://aka.ms/vs/17/release/vc_redist.x64.exe) 下载安装。

---

## SHA256

- `RhythmAlign_v1.2.0_Setup.exe`
  `CE34DDCB4BDDA1A19243A4384615576825C90856226BC605181E923A0954EA8E`
- `RhythmAlign-v1.2.0-Portable.zip`
  `BFB5456BAC064AFB1E6BCC3BA248BB533DEBF70B65B3BBD10647A979E31E0C64`

---

## 已知限制 | Known Issues

- 仅支持 Windows x64 平台。
- GPU 加速仅支持 NVIDIA 显卡 (NVENC)。
- 当视频内录音频与参考音乐差异过大时，自动对齐会拒绝猜测（安全停止）；请优先确认音源版本一致。
- 暂无应用内的完整手动放置偏移手段（±500 ms 滑块仅是微调）；确需手动时可在其他剪辑软件中完成。

---

## 技术附录 | Technical Notes（开发者向）

- Engine v2：四类证据家族（tonal/chroma、onset、PCEN 谱、PCEN+HPSS）分别生成候选偏移，聚类交叉验证后决策；产品语义为「全有或全无」——要么可信采纳，要么安全放弃。
- 时间支撑校验：对决定性 PCEN 证据在候选偏移处按 1 s 分箱，最大箱占比超过阈值即判定为「集中证据」并放弃（`ABSTAIN_CONCENTRATED_EVIDENCE`），阻断短暂共同内容导致的整曲错位。
- 安全回归规模：22/22 已知错歌假阳性全部拒绝；156/156 留出错歌对全部安全停止；55/55 此前采纳的正样本全部保留。
- 研究过程与校准细节见仓库 `docs/RA-1.2A` – `docs/RA-1.2D1` 系列报告。

---

## 许可 | License

本软件基于 PolyForm Noncommercial 1.0.0 许可协议，仅供个人非商业使用。详见 [LICENSE](https://github.com/Daozhu1007/RhythmAlign/blob/main/LICENSE)。

---

## 14. RC2 — final UI polish only (post `OWNER_RC_PASS`)

Scope guard honored: after the owner returned `OWNER_RC_PASS` for RC1,
exactly one fix was allowed — the Sync-page slider label/unit layout.
`alignment_engine_v2.py`, `auto_sync.py`, export/update/packaging logic,
version 1.2.0, and `release_notes_v1.2.0.md` are **zero-diff** against
the RC1 state (`2d0a922` + report commit); the RC2 commit `ed1a869`
touches only `ui_main.py`, `locales/{zh_CN,en_US}.json`, and tests
(verified via `git show ed1a869 --stat` and an empty
`git diff 2d0a922..ed1a869` over the algorithm/update/packaging files).

### 14.1 Change (commit `ed1a869`)

- `lbl_offset` shortened: zh_CN `手动微调 (ms，叠加在自动对齐之上)` →
  `手动微调`; en_US `Manual fine-adjust (ms, added on top of auto
  alignment)` → `Manual fine-adjust`. The long label measured 408 px
  (en) / 284 px (zh) rendered vs 114 px for the other rows, pushing the
  third slider start far right.
- `create_slider_row(..., unit="%")`: the unit is now an explicit
  parameter; the text-dependent heuristic (`'%' if 'ms' not in name`)
  is removed. The offset row passes `unit=" ms"`, so live text is
  e.g. `手动微调: 0 ms` / `Manual fine-adjust: 0 ms` and volume rows
  keep `…%`.
- Labels use a fixed `SLIDER_LABEL_WIDTH = 180` px (fits the widest
  state `Manual fine-adjust: -500 ms` = 173 px in both locales), so all
  three sliders start at the same x in zh_CN and en_US (verified 244 px
  for both languages in a real widget layout).
- Offset slider unchanged: range −500..500, default 0, semantics
  (`/1000.0` seconds) untouched; presets untouched.
- Tests: new `tests/test_ra12e_slider_ui.py` (4 tests: short/unit-free
  labels in both locales, explicit `unit` parameter, shared slider
  start x + offset range + live unit text); the RA-1.2D locale-wording
  assertion was updated to pin the new exact labels.

### 14.2 Verification and RC2 build

- `python -m pytest tests/ -q` → **80 passed** (76 baseline + 4 new),
  23.8 s. One pre-existing assertion failed against the shortened label
  (`test_locale_files_cover_engine_v2_product_strings` required
  "auto alignment" inside `lbl_offset`) and was updated as above — the
  intent (fine-adjust presented as an add-on, never a fallback) is kept
  by pinning the exact new labels.
- `python -m compileall -q` on product modules + tests: clean.
- `git diff --check`: clean. Clean tree at build time
  (`ed1a869`, only untracked `release_notes_v1.2.0.md`).
- Rebuild per §7 (PyInstaller 6.19.0 `--clean --noconfirm`, 94 s;
  Inno Setup 6.7.3, 126 s; Compress-Archive). RC1 owner artifacts in
  `dist/rc/` were preserved.

### 14.3 RC2 owner-test package (local only, unpublished)

- `D:\Code\RhythmAlign\dist\rc\RhythmAlign-v1.2.0-RC2-Setup.exe`
  — 118,717,233 bytes, SHA-256
  `025323C60D133318BD21F5EE132A617A406DF9F8164BE51198DC3C4F46CC8774`
  (byte-identical to the Inno output `dist/RhythmAlign_v1.2.0_Setup.exe`).
- `D:\Code\RhythmAlign\dist\rc\RhythmAlign-v1.2.0-RC2-portable\`
  — folder copy of the frozen bundle.
- `dist/RhythmAlign-v1.2.0-Portable.zip` — 176,289,985 bytes, SHA-256
  `CFCED7CC67B5A5423C9A5E225D28BB93B673C282089145D85E645C4376EB3579`
  (same content as the RC2 portable folder).

Bundle re-verified: both locales carry `RhythmAlign v1.2.0` and the
short `lbl_offset`; 0 PySide6/shiboken files; FFmpeg
`ffmpeg-win-x86_64-v7.1.exe` present; `alignment_engine_v2` in the
PyInstaller Analysis toc. Frozen launch smoke (RC2 portable): alive
after 12 s at 232 MB working set, closed gracefully via
`CloseMainWindow()`. No research/corpus evaluation was re-run (per
instruction; algorithm code is zero-diff).

### 14.4 Hard stop (unchanged)

No tag, no GitHub Release, no asset upload, `update.json` still serves
v1.1.2. RC2 awaits the owner's go-ahead; the §12 post-PASS release
actions apply unchanged, with RC2 hashes as the asset reference.

---

## 15. OWNER_RC2_PASS — final release authorization

`OWNER_RC2_PASS` received from the product owner: the owner manually
tested the packaged RC2 (`dist/rc/RhythmAlign-v1.2.0-RC2-Setup.exe`,
SHA-256 `025323C60D133318BD21F5EE132A617A406DF9F8164BE51198DC3C4F46CC8774`)
after the final slider-layout polish and explicitly approved it for
release. No further product/UI/algorithm/packaging/release-note feature
changes are permitted unless a final-audit blocker is found; no
additional testing is claimed beyond this authorization.

RA-1.2E may resume for FINAL RELEASE; the §12 post-PASS actions are
executed in §16 with the owner-approved RC2 artifacts as the reference
bytes.

---

*Limitime — September 2026*
````
