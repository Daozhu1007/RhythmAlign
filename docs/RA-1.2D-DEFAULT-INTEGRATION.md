# RA-1.2D — Alignment Engine v2 Default-Path Integration + Abstention UX

Status: **integration complete; Engine v2 is the product default path.**

Recommendation: **READY_FOR_RA12E**

---

## 1. Git baseline

| item | value |
|---|---|
| Branch | `main` |
| HEAD at task start | `ffa6b07a591dbdb54ae8350f3d27dce3ed74c847` (`docs: RA-1.2C calibration hardening + repeated-invocation stability (non-default path)`) |
| Upstream relation | `origin/main`, 0 ahead / 0 behind |
| Working tree at start | contained the paused Astra research study (4 untracked files) |
| Baseline suite | `python -m pytest -q` → **48 passed in 14.71 s** |
| Baseline engine state | Engine v2 exists, non-default; GUI default path v1.1.x (`auto_sync.find_offset()`) |

**Paused Astra work preservation (pre-flight, owner-approved).** The
working tree was not clean at dispatch: a separate, still-incomplete
Astra alignment research study had left 4 untracked files
(`docs/research/alignment/EXPERIMENT_PLAN.md`,
`experiments/alignment_research/study.py`,
`experiments/alignment_research/results/audit.json`,
`experiments/alignment_research/results/corpus.json`). Per the owner's
explicit choice they were preserved **verbatim** (read-only hygiene scan
first: no secrets, no personal absolute paths, no embedded media) on a
local-only branch, then removed from the `main` working tree:

- branch `astra/alignment-research-wip` (parent = `ffa6b07`)
- WIP commit: `5b1fcd472a94470872dc1f837a7f473c0edd5282`
- **not pushed** (local durability only, per owner instruction)

RA-1.2D code shares no path, commit, or conclusion with that study; the
Astra branch is not merged, cherry-picked, or referenced by any product
change below, and no unfinished Astra finding is inferred anywhere.

## 2. Owner listening PASS (RA-1.2C gate closure)

Recorded as a dated addendum (§24) plus a targeted §3 note in
`docs/RA-1.2C-CALIBRATION-HARDENING.md`; the RA-1.2C text itself was not
rewritten and commit `ffa6b07` was not amended.

- File tested: `零对话_engine_v2_test.mp4` (RA-1.2B owner-test artifact)
- Engine v2 offset: **+12.4923 s**
- Owner verdict: **PASS** — no observable alignment problem
- The verdict does **not** make the ±0.4 s manual ground-truth interval
  more precise; it remains one recording deep.

Also fixed the report cross-reference typo: the header now points to the
recommendation at **§23** (it previously said §24).

## 3. Exact product-path change

One choke point served both GUI workers:
`BaseMediaWorker._run_find_offset()` called `auto_sync.find_offset()`.

It now calls `alignment_engine_v2.find_offset_v2()` and returns an
`AlignmentDecision`; `BaseMediaWorker.run()` dispatches on the decision:

```python
decision = self._run_find_offset()      # find_offset_v2(...)
if decision.accepted:
    log "auto alignment completed" + "evidence path: …"
    self._on_offset_found(decision.offset)     # ACCEPT: continue
else:
    self._on_abstained(decision)               # ABSTAIN: safe stop
```

- `SyncWorker` and `AnalyzeWorker` both inherit this; there is no other
  automatic alignment path in the product.
- The legacy `from auto_sync import find_offset, CorrelationLowConfidenceError`
  bindings were **removed from `ui_main.py`**; the legacy engine remains
  in `auto_sync.py` for backward-compatible tests, experiment
  comparisons, and explicitly-called diagnostic tooling
  (`diagnose_offset.py`, `experiments/low_snr_alignment/*`).
- `alignment_engine_v2.py` header updated: it is now the default product
  path; a stable, locale-independent `ENGINE_LABEL` constant
  (`"Engine v2 (evidence-gated)"`) was added for logs/diagnostics.

## 4. Why no legacy fallback exists

A "v2 abstains → call v1" chain would reintroduce exactly the failure
the RA-1.2B/C evidence work removed: v1's Z ≥ 2.0 gate accepts all ten
deliberate wrong-song mismatches and has no ambiguity or overlap
guards. An abstention means the evidence does not establish *any*
offset; the only product-safe behavior is to stop before export.
Test `test_gui_default_path_never_calls_legacy_find_offset` proves the
default path cannot reach the legacy function (both namespaces are
booby-trapped), and `test_ui_module_no_longer_binds_legacy_find_offset`
proves `ui_main` no longer even binds it.

## 5. ACCEPT UX

Sync page, for an accepted decision (unchanged product semantics, now
fed by Engine v2):

- `decision.offset` becomes the automatic base offset; the existing
  manual fine-adjust slider adds on top:
  `final_offset = automatic_offset + manual_adjustment`
- volume presets, stream-copy / GPU / bitrate behavior unchanged
- export runs exactly once through the existing `mix_and_export` path
- logs: engine identity, `自动对齐完成：选定偏移 …（可靠性校验通过）`,
  `证据路径: 双家族证据一致 | 主证据 + 佐证通过` — compact, no Z-score
  internals, no raw correlation arrays
- Analyze page displays `decision.offset` and reports success normally

## 6. ABSTAIN UX

A product-safety behavior, never a crash and never an export:

- **no export, no v1 fallback, no invented offset** — the worker stops
  before `mix_and_export` and no output file is created
- log lines: `无法可靠地确定对齐偏移。`, `原因代码: {machine-readable
  reason_code}`, `已安全停止：未开始导出，未生成输出文件。`
- Sync page: persistent, user-dismissable warning banner
  (`InfoBar.warning`, `duration=-1`) with the full explanation; the
  progress row shows `已安全停止（未导出）`; the Sync button is
  re-enabled immediately
- Analyze page: result card shows `无法可靠确定` (**no numeric
  placeholder** such as `+0.0000 s`), hint shows the reason category
- reason codes map to three user-facing categories (exact codes are
  preserved in logs/diagnostics):

| reason_code | user-facing category |
|---|---|
| `ABSTAIN_NO_CLUSTER_MEETS_FLOORS` | insufficient evidence (+ checklist suggestion) |
| `ABSTAIN_PRIMARY_NOT_CORROBORATED` | insufficient evidence (+ checklist suggestion) |
| `ABSTAIN_AMBIGUOUS_CLUSTER` | several similarly plausible offsets |
| `ABSTAIN_INSUFFICIENT_OVERLAP` | usable overlap too short |

Messages only claim what the reason code establishes; the suggestion
line ("verify the music file is the song actually playing…") is phrased
as a possible cause, not a finding. A generic `运行报错/Execution
error` is never emitted for an abstention (covered by tests).

## 7. Manual fine-adjustment semantics

The old failure wording advertised the ±500 ms slider as a complete
fallback for a failed automatic alignment — misleading when the true
offset is e.g. +12 s. Corrected:

- `err_low_confidence` / `err_manual_fallback` strings **removed** from
  both locales; no code path emits them anymore
- the slider label now states its real semantics:
  `手动微调 (ms，叠加在自动对齐之上)` /
  `Manual fine-adjust (ms, added on top of auto alignment)`
- a full manual-base-offset control (timeline editor / forced legacy
  button) was deliberately **not** implemented; it is documented as a
  future product option in §18 (remaining risks / future work)

## 8. Localization changes

Both `locales/zh_CN.json` and `locales/en_US.json` (key sets kept
identical; the existing parity test still passes):

- added: `log_engine_v2`, `log_alignment_accepted`, `log_evidence_path`,
  `evidence_path_dual_family`, `evidence_path_primary_corroboration`,
  `log_abstained`, `log_abstain_reason`, `log_abstain_no_export`,
  `task_abstained`, `analyze_abstained`, `abstain_headline`,
  `abstain_safe_stop`, `abstain_reason_insufficient_evidence`,
  `abstain_reason_ambiguous`, `abstain_reason_insufficient_overlap`,
  `abstain_suggestion`
- reworded: `lbl_offset` (fine-adjust semantics), `log_extract`
  (multi-family evidence features, was "Chroma")
- removed: `err_low_confidence`, `err_manual_fallback`

Architecture choice for `alignment_engine_v2.decision_message()`:
**option A** — it keeps its built-in Chinese strings as a diagnostic /
experiment helper (`engine_v2_owner_test.py`) and is **not** used by the
GUI, which maps reason codes onto locale files instead. The decision
layer stays presentation-independent; this is documented in the
function's docstring. No Chinese strings were added to the engine or
core UI flow.

## 9. Analyze-page behavior

- ACCEPT → shows the selected offset (unchanged format/hints)
- ABSTAIN → shows the explicit `无法可靠确定` state with the
  reason-category hint; never `+0.0000 s` or any other number that
  could be mistaken for a result
- hard failure (corrupt media, FFmpeg error) → unchanged `分析失败`
  state, clearly distinct from abstention

## 10. ETA / progress decision

**Numeric ETA kept, recalibrated from measured Engine v2 behavior.**
Measured full product-path analysis (FFmpeg extraction + multi-family
evidence + decision) on this machine: **3.3–6.7 s** for 273–332 s media
pairs (零对话 332 s → 6.7 s). The legacy estimator
(`2 s + total_media/45`) predicted 8.1–9.4 s — a +39 %…+142 %
overestimate. `_ANALYSIS_ESTIMATE_REALTIME_FACTOR` was recalibrated
**45 → 75** in `auto_sync.py` (deliberately biased toward a slight
overestimate; nothing else in the estimator changed, floor/cap
untouched). Rendering/export ETA behavior is untouched. The UI keeps its
indeterminate bar + `预计剩余` countdown; no fake precision was added.

## 11. Worker / thread architecture

Unchanged threading model, deliberately: `SyncWorker` / `AnalyzeWorker`
remain `QThread`s running the template method off the GUI thread, so the
slower Engine v2 analysis cannot freeze the UI. The only structural
changes are the decision dispatch in `run()` and the two new safe-stop
signal payloads (`finished_signal(bool, str, str)`,
`result_signal(bool, float, str)`). Button re-enable is the first
statement of both completion handlers, so the UI recovers on ACCEPT,
ABSTAIN, and hard failure alike.

## 12. Tests added

`tests/test_ra12d_integration.py` — 17 tests, media-independent (mocked
`find_offset_v2` + mocked `mix_and_export`, workers driven
synchronously):

- **A. accepted decision:** SyncWorker exports exactly once with the v2
  offset; `final = auto + manual` semantics, volume presets,
  stream-copy/GPU/bitrate all passed through unchanged
- **B. abstained decision:** `mix_and_export` never called, no output
  file exists, safe-failure payload carries a non-empty user message,
  progress row reports the safe stop (not generic failure)
- **C. AnalyzeWorker accepted:** emits the offset
- **D. AnalyzeWorker abstained:** emits `(False, 0.0, reason_code)` —
  no displayable fake numeric result; display layer renders the
  undetermined state
- **E. no legacy fallback:** `ui_main` has no `find_offset` binding;
  with both `auto_sync.find_offset` and `ui_main.find_offset`
  booby-trapped to raise, the accepted flow still completes through v2
- **F. reason-code handling:** all four codes map to stable user
  categories; ambiguity vs insufficient-evidence produce different,
  deterministic messages; logs carry the exact machine-readable codes;
  no `运行报错/Execution error` line on the abstain path
- **G. legacy suite:** the 48 pre-existing tests (including all
  `auto_sync` legacy unit tests) still pass — full suite now **65
  passed**

Locale coverage of all new product strings is also asserted.

## 13. Real-corpus regression

Re-ran the established benchmark
(`real_corpus_eval.py --json …/real_corpus_ra12d_default.json`) with the
**integrated** product path after the UI/worker changes:

- **29/29 real positives accepted** by Engine v2; **28 agree with the
  accepted v1 result** (零对话 remains the only v1-rejected/v2-accepted
  case); **0 worker errors**
- **零对话 (`lingduihua_132`): accepted @ +12.4923 s** through
  `ACCEPT_PRIMARY_WITH_CORROBORATION` (CASE B) — identical to RA-1.2C
- every positive offset is **identical to the RA-1.2C run** (e.g.
  lividi +9.9149, drops +10.2864, hongzhoutian +32.7169,
  bai39 +10.8437)
- **10/10 ordinary mismatch negatives abstained**
  (`ABSTAIN_NO_CLUSTER_MEETS_FLOORS`) — while v1 accepted all ten
  (Z 3.4–5.96), unchanged as expected

The integration layer did not alter a single engine decision or offset.

## 14. Hard-negative / holdout regression

Frozen-policy safety regressions re-run fresh (`--fresh`, integrated
code), outputs copied to `*_ra12d_default.json`, RA-1.2C evidence files
restored byte-identical from git afterwards:

| split | RA-1.2D result | RA-1.2C reference |
|---|---|---|
| Calibration (44: 36 semi-synthetic + 4 tiled + 6 hard negatives) | **17 CA / 27 SA / 0 WA** | 17 CA / 27 SA / 0 WA |
| Holdout (26: 20 semi-synthetic + 2 tiled + 4 hard negatives) | **9 CA / 17 SA / 0 WA** | 9 CA / 17 SA / 0 WA |
| Real hard negatives (10, v1 false-accepts all) | **10/10 abstain** | 10/10 abstain |
| Tiled-ambiguity cases (6) | **6/6 abstain** (`ABSTAIN_AMBIGUOUS_CLUSTER`) | all abstain |

**0 wrong accepts anywhere.** Calibration policy unchanged —
`git diff` on `alignment_engine_v2.py` touches only the module
docstring, `ENGINE_LABEL`, and a docstring.

## 15. End-to-end product smoke tests

Run via `experiments/low_snr_alignment/product_smoke.py` (real
`ui_main.SyncWorker`, real FFmpeg extraction, real `mix_and_export`, no
mocks; temporary outputs removed afterwards):

**A. 零对话 (`lingduihua_132`, low-SNR positive) — PASS.** Default
product path selected Engine v2; accepted @ **+12.4923 s** (evidence
path: 主证据 + 佐证通过 / CASE B); reached the normal export path
(stream-copy); output file verified on disk. Logs, in order: engine
identity → extraction → accepted+offset → evidence path → raw/final
offset → render → export complete. Total wall 11.8 s.

**B. Ordinary strong recording (`lividi_132`) — PASS.** Accepted @
+9.9149 s (evidence path: 双家族证据一致 / CASE A); exported normally;
output verified. Total wall 10.5 s.

**C. Deliberate mismatch (`mm_queen_x_lingduihua`) — PASS.** Product
path **abstained** (`ABSTAIN_NO_CLUSTER_MEETS_FLOORS`); export was NOT
started; no output file existed. The worker emitted the full localized
safe-stop message (headline → safe-stop reason → insufficient-evidence
category → checklist suggestion), and no generic execution error
appeared. Total wall 7.0 s.

## 16. Packaging smoke test

- The spec already bundles everything Engine v2 needs: it analyzes
  `ui_main.py`, which imports `alignment_engine_v2` → `auto_sync`,
  `librosa`, `scipy`, `imageio_ffmpeg`; PyInstaller followed all of them
  with **no hiddenimports additions required** — verified below, so the
  spec needed no dependency changes for the new import.
- **One spec fix was required (environment drift, explained):** the dev
  Python now has PySide6 6.11.1 installed alongside PyQt6, and
  PyInstaller 6.18 aborts builds that collect two Qt bindings. Per
  PyInstaller's own guidance, `'PySide6'` was added to the spec's
  `excludes` (3-line diff with comment); the app is PyQt6-only, so the
  shipped bundle is unaffected.
- Rebuild `python -m PyInstaller RhythmAlign.spec --noconfirm` →
  **success**. Verified in the bundle: `alignment_engine_v2` present in
  the module graph (xref; zero missing-module warnings for it), `librosa`,
  `scipy`, `scipy.libs`, `imageio_ffmpeg` (incl. the FFmpeg binary),
  `locales/{zh_CN,en_US}.json`, and `assets/` all present under
  `dist/RhythmAlign/_internal/`.
- **Frozen launch smoke:** `dist/RhythmAlign/RhythmAlign.exe` started,
  stayed alive (full Qt + qfluentwidgets + Engine v2 + librosa import
  chain intact inside the frozen app), then was closed. No installer
  was published; `dist/` and `build/` are gitignored.

## 17. Performance observations

- Engine v2 full product-path analysis measured at **3.3–6.7 s** for
  representative ~2.5–5.5-minute media pairs (extraction + all four
  evidence families + decision); consistent with RA-1.2B/C's ~8–9 s
  observation on a colder/loaded machine. Acceptable for interactive
  use; no optimization work performed (none needed).
- Analysis stays off the GUI thread (unchanged `QThread` template
  method), so the slower engine cannot freeze the UI; progress state
  transitions (indeterminate → export % → done / safe-stop) and button
  re-enables are covered by the integration tests and were exercised in
  the product smokes.
- No memory/perf regression is expected: the engine code is
  byte-identical to the RA-1.2C soak/memory-verified state
  (60 synthetic + 25 real-file repeated invocations, flat RSS).

## 18. Remaining risks

- **No new numeric ground truth.** The owner listening PASS confirms
  perceptual correctness of the +12.4923 s case only; ground-truth
  coverage remains one recording deep (unchanged from RA-1.2C).
- **Abstention dead-ends for the user.** A user whose legitimate pair
  abstains has no in-product recovery path (no manual base-offset
  control, no force-export). This is the intended RA-1.2D safety
  posture; a manual-base-offset control is the natural future product
  option and should be specified as such (not added ad hoc).
- **Persistent banner is dismiss-only.** The abstain InfoBar stays until
  dismissed; it never blocks other pages.
- **`decision_message()` bilingual surface.** The diagnostic helper
  still contains built-in Chinese strings (option A). Harmless while it
  is GUI-unused; revisit if it ever becomes user-facing.
- **Threading model verified by construction.** The smoke tests drive
  `worker.run()` synchronously for determinism; the GUI's QThread
  offloading is architecturally unchanged from the shipped v1.1.x
  behavior. An interactive owner launch of the packaged build remains
  the definitive responsiveness check.

## 19. Exact files changed

- `ui_main.py` — Engine v2 default path, decision dispatch, abstention
  UX, signal payload changes, reason-code → locale-key maps
- `alignment_engine_v2.py` — header/default-path note, `ENGINE_LABEL`,
  `decision_message()` docstring note (GUI-unused); **no policy,
  threshold, or decision-logic change**
- `auto_sync.py` — **unchanged** (legacy engine intact for
  tests/experiments/diagnostics)
- `diagnostics.py` — `Alignment engine:` line in the `[Runtime]` report
- `locales/zh_CN.json`, `locales/en_US.json` — §8
- `docs/RA-1.2C-CALIBRATION-HARDENING.md` — §2 addendum + typo fix
- `docs/RA-1.2D-DEFAULT-INTEGRATION.md` — this report
- `tests/test_ra12d_integration.py` — new (17 tests)
- `experiments/low_snr_alignment/product_smoke.py` — new product-path
  smoke harness (manifest-driven, no media committed)
- `RhythmAlign.spec`, `app_info.py` — **unchanged** (no version bump,
  no tag, no release)

## 20. Exact validation results

| check | result |
|---|---|
| `python -m pytest -q` (baseline, pre-change) | **48 passed** in 14.71 s |
| `python -m pytest -q` (final, post-change incl. ETA recalibration) | **65 passed** in 16.61 s |
| `python -m compileall -q auto_sync.py alignment_engine_v2.py diagnose_offset.py ui_main.py tests experiments` | OK |
| `git diff --check` | clean |
| Established Engine v2 synthetic regression | `test_alignment_engine_v2` + `test_ra12c_calibration` suites all green (inside the 65) |
| Real corpus regression (integrated) | 29/29 ACCEPT (零对话 +12.4923, CASE B), 10/10 mismatch ABSTAIN, 0 errors, offsets identical to RA-1.2C |
| Hard-negative / holdout safety regression (fresh) | calibration 17 CA / 27 SA / 0 WA; holdout 9 CA / 17 SA / 0 WA; 10/10 hard negatives and 6/6 tiled-ambiguity abstain |
| SyncWorker integration tests | pass (accept/abstain/no-fallback/semantics) |
| AnalyzeWorker integration tests | pass (accept / abstain-no-fake-numeric) |
| Real end-to-end ACCEPT smoke | 零对话 + lividi: exported, outputs verified, then removed |
| Real end-to-end ABSTAIN smoke | mismatch: no export, no output, correct safe-stop UX |
| PyInstaller package smoke | build success, bundle verified, frozen exe launched alive and closed |
| Path-leak scrub | 0 personal absolute paths in diff and new files |
| Astra isolation | WIP branch untouched; no Astra files in this commit; no Astra conclusions referenced |

## 21. Final Git state

- One coherent commit on `main` (parent `ffa6b07`), pushed to
  `origin/main` after every check above passed.
- Files staged **explicitly by path**: `ui_main.py`,
  `alignment_engine_v2.py`, `auto_sync.py`, `diagnostics.py`,
  `locales/zh_CN.json`, `locales/en_US.json`, `RhythmAlign.spec`,
  `docs/RA-1.2C-CALIBRATION-HARDENING.md`,
  `docs/RA-1.2D-DEFAULT-INTEGRATION.md`,
  `tests/test_ra12d_integration.py`,
  `experiments/low_snr_alignment/product_smoke.py`, and the three
  path-free RA-1.2D evidence JSONs
  (`real_corpus_ra12d_default.json`,
  `semi_synthetic_calibration_ra12d_default.json`,
  `semi_synthetic_holdout_ra12d_default.json`).
- Paused Astra study: preserved verbatim on local-only
  `astra/alignment-research-wip` (`5b1fcd4`), **not** merged, pushed,
  or referenced; `main` contains no Astra paths.
- GUI default path = Engine v2; no silent legacy fallback; engine
  thresholds/policy byte-unchanged.
- No user media, no personal absolute paths, no gitignored-local
  manifests, and no build artifacts (`build/`, `dist/` ignored)
  committed. No version bump, no tag, no GitHub Release.

## 22. Recommendation

**READY_FOR_RA12E**

Meaning: Engine v2 is successfully integrated as the default product
path, the abstention UX stops unsafe exports correctly, regressions and
real-media smokes pass with engine decisions byte-stable against
RA-1.2C, packaging is verified, and the repository is ready for the
v1.2.0 release-candidate phase (final version bump, README/release
notes, installer/portable build, upgrade manifest, tag, GitHub
Release).
