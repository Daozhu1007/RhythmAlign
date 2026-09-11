# RA-1.2A — Low-SNR Alignment Spike (零对话 handcam failure)

Status: **investigation spike — no production behavior changed.**
Recommendation: **READY_FOR_RA12B**

---

## 1. Git starting state

| item | value |
|---|---|
| Repository | `Daozhu1007/RhythmAlign` (local checkout `D:\Code\RhythmAlign`) |
| Branch | `main` |
| HEAD at task start | `44164d1a7321ec9a8ac2977346c3814c6383d227` (`chore: update v1.1.2 release manifest`) |
| Working tree at start | clean |
| Matches known upstream HEAD | yes — local HEAD == the documented upstream baseline |
| Test suite at start | `python -m pytest -q` → **19 passed** |

Media located (read-only; never modified):

- `D:\Daozh\Videos\舞萌手元\13.2\零对话\零对话.mp4` (450,709,854 bytes)
- `D:\Daozh\Videos\舞萌手元\13.2\零对话\track.mp3` (4,873,226 bytes)

A misaligned export (`零对话_synced.mp4`) from the user's original run is
present in the same folder; it was not used as evidence and not modified.

## 2. Existing algorithm behavior

Production path (`auto_sync.py`):

1. Extract mono audio from video and music at 22 050 Hz (ffmpeg → WAV).
2. `_align_hybrid`: Chroma CENS temporal deltas, per-band full
   cross-correlation, plus `0.2 ×` normalized onset-envelope correlation.
   If peak Z ≥ 2.0 → **accept immediately**.
3. Otherwise `_align_onset`: onset-strength envelope correlation. Accept if
   Z ≥ 2.0 **and** independent-peak ratio ≥ 1.05 (peaks separated ≥ 1.5 s).
4. Otherwise raise `CorrelationLowConfidenceError` (UI abstains).

Offset sign convention (verified against `mix_and_export`): positive offset
delays the music (`adelay`); negative offset trims the music head
(`atrim`). At video time `t` the music plays at music time `t − offset`.
Raw correlation lag maps as `offset = −lag × hop / sr` because every
production correlation places the *music* feature as `in1`.

## 3. Exact reproduction of the 零对话 failure

Command: `python experiments/low_snr_alignment/run_experiment.py` (wraps the
unmodified production functions; identical numbers were also reproduced by a
direct inline call to `auto_sync._align_hybrid` / `_align_onset`).

| method (production, unmodified) | offset | Z | result |
|---|---|---|---|
| `_align_hybrid` | **−1.9969 s** | 5.485 | accepted (Z ≥ 2.0) → exported misaligned video |
| `_align_onset` | +12.4459 s | 2.268 | would be rejected (peak ratio 1.001 < 1.05) |
| `_align_chroma` | −1.9040 s | 5.376 | (diagnostic only) |

Durations: video 179.691 s, music 152.030 s — both match the CTO's
independent measurements exactly.

## 4. Independently established approximate ground truth

**Ground truth: offset ≈ +12.4 s ± 0.4 s.** Evidence chain (no algorithm
under test used):

1. **Track leading silence:** `track.mp3` contains digital silence
   (frame RMS ≈ 1e-4 of full scale or lower) for its first **3.065 s**, then
   an abrupt step to full energy (RMS 0.000 → 0.147 within one 0.25 s
   bucket). Frame-precise anchor.
2. **Video frames — gameplay start:** song-select screen still visible at
   9.0–9.5 s; transition/loading screen at 10.0–10.5 s; empty gameplay field
   (intro, no notes) from 11.5 s to 14.5 s; first tap notes visible
   approaching at 15.0 s; **PERFECT judgment + 連打2 note on screen at
   15.5 s**. So first note hits occur in ≈ (15.0, 15.5] s.
3. **First-hit ↔ music-start correspondence:** under a maimai chart the
   first notes land at/just after music start. First hit ≈ 15.4 s minus
   music start 3.065 s ⇒ offset ≈ **+12.3 s** (±0.4 s covering the frame
   sampling and the first-note-at-music-start assumption).
4. **Song-end discriminator (excludes the −1.997 s peak decisively):**
   gameplay is still active at 149–151 s (連打115) and the final 連打168
   rumble continues through 163–167 s. Under offset −1.997 s the 152.03 s
   track would be exhausted at video 150.0 s, making 17+ more seconds of
   active track-mode play impossible. Under +12.42 s music ends at
   video 164.45 s with the final rumble tail extending ~3 s past it —
   exactly what the frames show.
5. **Competing candidates excluded:** +8.82 s would start the music at
   video 11.9 s (during the empty intro, before any note exists);
   +23.94 s would start it at 27.0 s (after the first observed judgment).

The algorithm-side values +12.4227 s (PCEN) and +12.4459 s (onset) agree
within 24 ms and fall inside the anchor interval.

## 5. Experimental methods

Isolated harness: `experiments/low_snr_alignment/` (nothing imported by
production). Methods evaluated:

- **A. hybrid** — production `_align_hybrid`, unmodified.
- **B. onset** — production `_align_onset`, unmodified.
- (chroma — production `_align_chroma`, diagnostic.)
- **C. pcen_delta** — mel spectrogram → PCEN → temporal first difference
  (positive-only) → per-band z-score normalization → per-band correlation
  summed → lag/Z/independent-peak metrics.
- **C′. pcen_hpss** — C preceded by median-filter HPSS on the mel
  spectrogram, keeping the harmonic component (suppresses percussive taps
  before normalization).
- **logmel_flux** — dB-mel positive-flux envelope correlation (control).

PCEN configuration chosen from a 36-point sweep (`pcen_sweep.py`) over
analysis rate {22 050/512, 11 025/256, 11 025/512}, n_mels {64, 96},
fmax {nyquist, 5500, 4000}, delta polarity {positive, signed}:

- **Final choice:** sr 22 050, hop 512 (23 ms), n_mels 96, fmin 30 Hz,
  **fmax 4000 Hz**, positive-only delta, per-band z-score, PCEN params
  librosa defaults (gain 0.98, bias 2.0, power 0.5, τ 0.4 s); C′ adds HPSS
  kernel 31.
- Rationale: band-limiting to 4 kHz raised the true-peak margin on the real
  pair (1.04 → 1.18) and lowered the no-signal null Z (3.63 → 3.31); signed
  deltas were worse everywhere; analysis-rate changes were negligible, so
  the production rate is kept.

## 6. Results table — real failing pair

| method | offset (s) | Z | peak ratio | top-1/top-2 margin | reliable? | runtime (s) |
|---|---|---|---|---|---|---|
| hybrid (production) | −1.9969 | 5.49 | 1.193 | 1.19 | yes (WRONG) | 1.93 |
| onset (production) | +12.4459 | 2.27 | 1.001 | 1.01 | no | 0.23 |
| chroma (production) | −1.9040 | 5.38 | 1.341 | 1.34 | yes (WRONG) | 1.70 |
| pcen_delta | **+12.4227** | 5.88 | 1.177 | 1.18 | yes | 0.30 |
| pcen_hpss | **+12.4923** | **10.44** | **1.893** | **1.89** | yes | 2.11 |
| logmel_flux | +8.8236 | 4.78 | 1.000 | 1.00 | no | 0.21 |

Ground truth +12.4 ± 0.4 s: pcen_delta error 0.02 s, pcen_hpss error 0.07 s,
onset error 0.05 s; hybrid error 14.4 s. Total budget for all six methods
≈ 6.5 s on a 3-minute video (full pipeline cost stays in the seconds class;
pcen_hpss ≈ chroma cost).

## 7. PCEN experiment results

- The CTO's prototype observation **reproduced**: plain PCEN-delta lands at
  +12.4227 s with Z 5.08–5.88 (CTO reported +12.423 s / Z 5.26) — matching
  within frame resolution.
- The tuned variant (fmax 4000) improves margin 1.04 → 1.18.
- **pcen_hpss is the strongest configuration found:** Z 10.44, peak ratio
  1.89 — the true peak towers over every competitor. Among the *new
  low-SNR candidates* it was the only one that survived the harshest
  synthetic interference case (taps +28 dB above music, near-periodic:
  correct at +13.607 s where plain PCEN chose +24.776 s). The legacy
  hybrid also passed that synthetic case, but hybrid is the incumbent that
  fails the real recording (§6), so pcen_hpss is the successful *new*
  method, not literally the only method overall.
- Caveat carried forward: HPSS *raises* the no-signal null Z
  (3.3–3.9 → up to 4.69 over 5 null realizations), so its accept threshold
  must be calibrated per-family; raw Z alone is not a pass/fail rule for
  any family (see §9, §12).

## 8. Top competing candidate peaks (real pair)

| rank | hybrid | chroma | onset | pcen_hpss |
|---|---|---|---|---|
| 1 | −1.997 | −1.904 | **+12.446** | **+12.492** |
| 2 | +33.878 | +33.901 | +8.824 | +24.009 |
| 3 | −12.144 | −12.051 | +23.940 | +8.150 |

- The onset curve's top two peaks are nearly tied (2770.9 vs 2752.2 → ratio
  1.007) — its correct win is *thin*, which is why its Z is 2.27 and its
  ambiguity gate rejects it today.
- In the chroma curve the true candidate (+12.42) ranks **67 of 152**
  independent peaks — chroma does not merely mis-rank the truth, it is
  blind to it.

## 9. Root cause of the false-confident −1.997 s

1. **The video mix is not music-dominated.** Video RMS is 0.23 — loud
   broadband tap clicks and arcade ambience; the cabinet music is a minor
   contributor (which is exactly why PCEN/HPSS helps: gain-normalized
   band-limited harmonic evidence).
2. **Chroma CENS deltas respond to coincidental tonal patterns.** Per-window
   analysis (8 s windows, 4 s step): individual windows vote for scattered,
   mostly degenerate offsets; the global −2.0 s peak is driven primarily by
   video 80–88 s (local Z 4.78, the strongest window vote of all 43
   windows). We tested and **rejected** the "repeated musical structure"
   explanation: the chroma-delta cosine between the music segments that
   window would connect under the two hypotheses (track 67.6–75.6 s vs
   82–90 s) is −0.06 — no self-similarity. The match is coincidental
   low-dimensional structure (12 quantized pitch classes), not song
   content.
3. **Z measures sharpness inside one feature space, not correctness.** With
   ~7 700 + 5 300-frame correlation axes, the expected max-Z of a *pure
   noise* correlation curve is ≈ 3.5–4 (measured: hybrid 3.44–3.80, pcen
   3.52–3.90, pcen_hpss 3.93–4.69 over 5 synthetic no-signal realizations;
   onset stays ≤ 1.55). A Z of 5.5 is barely above the null ceiling — and
   the production threshold of 2.0 sits far *below* it. **The 2.0 threshold
   guarantees confident garbage on signal-less audio, and Z 5.5 does not
   certify a correct alignment even when the peak is real-looking.**
4. **The onset refinement cannot rescue it:** the hybrid's 0.2 onset weight
   leaves the chroma winner unchanged (top hybrid peaks == top chroma
   peaks), and the production decision path accepts hybrid at Z 5.49
   before the onset fallback ever runs.
5. **Mono downmix is *not* the culprit here:** L/R/mid onset and PCEN
   alignments all place the true lag at/near top-1 (L is cleanest);
   the one channel that disagreed under chroma (R → −12.26) proved to be
   chroma-specific noise. Side-channel evidence is weaker (favors +8.15).

**Product question answered:** "correct alignment" cannot mean "sharp peak
in a feature space". It should mean *converging evidence*: agreement
between evidence families with different failure modes, peak margins above
a per-family *measured null*, and explicit abstention otherwise.

## 10. Proposed Alignment Engine v2 (design only — not integrated)

```
video audio ─┬─ chroma/hybrid generator ──┐
             ├─ onset generator ──────────┤→ candidates → cluster (±0.15 s)
music ───────┴─ pcen / pcen_hpss generator┘        ↓
                                        per-family null-calibrated scoring
                                                   ↓
                              consensus + uniqueness + overlap checks
                                                   ↓
                                        ACCEPT (offset, evidence) / ABSTAIN
```

Policy sketch:

1. **Families, not votes.** `{chroma-hybrid}`, `{onset-flux}`,
   `{pcen (±HPSS)}` are three evidence families. PCEN and PCEN+HPSS count
   as ONE family (shared underlying feature); onset and PCEN are both
   flux-based and correlated — their agreement is supporting, not
   decisive, evidence. Never implement naive "2 votes wins".
2. **Per-family null calibration.** Accept thresholds derived from
   measured null distributions (§12): e.g. pcen accept if
   Z ≥ ~5.5 (null max 3.9) with margin ≥ ~1.5; pcen_hpss if Z ≥ ~6.5
   (null max 4.7); hybrid never accepts alone — it only nominates
   candidates. Thresholds to be finalized on a labeled real corpus in
   RA-1.2B.
3. **Clustering.** Candidates within ±0.15 s (≈6 hops) form a cluster;
   cluster evidence = best per-family evidence among members.
4. **Accept** iff: ≥2 distinct families' top-1 candidates agree in one
   cluster, ≥1 member clears its family's Z floor, no competing cluster
   reaches ≥ ~0.8× the best cluster's evidence, and the music/video
   overlap at that offset is ≥ 30 s (edge-lag guard).
   Single-family acceptance additionally requires exceptional margin
   (≥ 2.5) plus a multi-window consistency check.
5. **Multi-window consistency must be soft, not hard.** Measured on the
   real pair: on 8 s windows *no individual window votes for +12.42*
   (0/43) — the true peak only emerges from whole-signal integration.
   A hard per-window consistency gate would reject the correct answer
   in exactly the low-SNR case we are fixing. Longer/pooled windows only,
   and only as a tie-breaker.
6. **Abstain** → UI message ("无法可靠确定对齐偏移") + manual-offset affordance.
   A wrong confident export is the worst outcome (user trusts it); abstain
   is recoverable.

Worked example on the real failure (primary + corroborating +
contradiction-check model — *not* a two-vote count): clusters
{−1.997: hybrid+chroma}, {+12.45 ± 0.04: pcen (Z 5.88), pcen_hpss
(Z 10.44, margin 1.89), onset (supporting)}. The PCEN-family candidate at
+12.45 is the *primary* evidence: pcen_hpss clears its family null by a
wide margin with strong peak uniqueness. Onset's top-1 agreement is
*corroboration* (onset and PCEN are both temporal-flux evidence and
correlated — their agreement supports but does not by itself decide).
Contradiction checks: the hybrid/chroma cluster at −1.997 is an
unsupported outlier from the one family known to fail on this recording
and leaves the song-end evidence impossible (§4), and no comparable
alternative cluster exists near +12.45 → **accept +12.45, exactly what
the current engine got wrong.**

## 11. Zero-music feasibility analysis

Scenario A — target music present but very quiet (this failure):
pcen_hpss/pcen fusion solves it; this is the RA-1.2B scope.

Scenario B — music absent, player tap/button sounds present:

1. **Interaction-rhythm alignment** (feasible, medium confidence): detect
   tap transients, build the inter-onset-interval pattern, match against
   the music's beat/onset grid (beat-synchronous DTW or IOI histogram
   correlation). Caveat from this spike: dense maimai charts make naive
   event matching non-discriminative — measured onset-event agreement at
   the *correct* offset (+12.42) was 0.473 but 0.473 at the *wrong*
   offset (−1.997) and up to 0.521 at random offsets, because the music
   onset density (median IOI 0.232 s) saturates any ±60 ms tolerance.
   Rhythm alignment must therefore use *pattern* (bar/phrase structure),
   not point matching.
2. **Lightweight visual anchors** (feasible, coarse ±0.3–0.5 s): gameplay
   transition (select→play), first note appearance/hit (first PERFECT
   effect — used successfully as ground-truth evidence in §4), song-end /
   CLEAR transition (also used in §4: final rumble + music-end timing).
   Enough for a "music starts at gameplay start" prior; refine with B.1.
3. **Chart-assisted alignment** (strongest, when available): with
   simai/maidata note timestamps, observed taps/judgments align directly
   to chart times — no music needed; a handful of matched taps (~10–20 s
   of gameplay) yields near-exact offset. Recommended long-term direction
   (RA-1.3+), since charts are commonly available to users.

Scenario C — music absent, no useful interaction audio, screen visible:
visual anchors (B.2) still give a coarse prior; chart assistance (B.3)
still works. Pure audio-to-audio alignment cannot.

**Information-theoretic limit (stated explicitly):** if the target song is
completely absent from the recording and there is no correlated
interaction audio, no visual event tied to song time, no chart/metadata,
and no user anchor, then no algorithm — audio or otherwise — can recover
the absolute offset; the information does not exist in the input. The
product must abstain (or ask for a manual anchor) in that case.

## 12. Regression / synthetic-test results

Fully self-contained synthesized suite (`synthetic_eval.py`, no media
assets; music = seeded chord/bass/drums/arpeggio piece; recordings built at
exact known offsets). Tolerance ±0.15 s; "FALSE-CONFIDENT" = claimed
reliability with no shared signal.

| case | ground truth | hybrid | onset | pcen | pcen_hpss | logmel_flux |
|---|---|---|---|---|---|---|
| strong_music | +7.30 | ok +7.314 | WRONG +7.779 | ok +7.291 | ok +7.291 | WRONG +7.779 |
| attenuated_music (−28 dB) | +21.70 | ok +21.711 | WRONG +21.479 (abstain-grade) | ok +21.711 (Z 14.4) | ok +21.711 | WRONG +21.014 |
| low_snr_taps (taps +28 dB, near-periodic) | +13.60 | ok +13.537 | WRONG +26.285 | WRONG +24.776 | **ok +13.607** | WRONG +30.047 |
| repeated_structure (8 s loop) | +9.80 | ok +9.822 | WRONG +10.751 | ok +9.799 | ok +9.799 | WRONG +10.751 |
| no_shared_signal | (none) | **FALSE-CONFIDENT** (Z 3.90) | abstain-ok (Z 1.42) | abstain-ok (Z 3.31, ratio gate) | **FALSE-CONFIDENT** (Z 5.01) | **FALSE-CONFIDENT** (Z 3.48) |

Notes:
- `onset`'s "WRONG" on strong/attenuated cases reflects my synthetic
  music's perfectly periodic beat grid (unrealistically flat onset
  correlation); on real recordings onset behaves better (it top-1'd the
  real pair). Production pipeline as a whole is correct on the strong case
  because hybrid carries it.
- The `low_snr_taps` synthetic is *harsher* than the real recording
  (taps ~22–28 dB above music, metronomic) — plain PCEN fails it,
  pcen_hpss survives; this drove the C′ selection.
- The `repeated_structure` case is content-ambiguous modulo the 8 s loop;
  "ok" here means "matched the placed offset", and the ambiguity-gate
  discussion in §10 applies.

**Null distribution** (5 no-signal realizations, `--nulls 5`):

| family | Z range | top-1/top-2 margin range |
|---|---|---|
| hybrid | 3.44 – 3.80 | 1.036 – 1.132 |
| onset | 1.44 – 1.55 | 1.000 – 1.003 |
| pcen | 3.52 – 3.90 | 1.020 – 1.114 |
| pcen_hpss | 3.93 – 4.69 | 1.004 – 1.183 |

Signal-side discriminators on the real pair (pcen_hpss Z 10.44 / margin
1.893) sit far above this null, which is the quantitative basis for the
§10 accept rules — and the reason a *fixed global* Z threshold (2.0 today)
is unsound for every family except onset.

Desired behavior confirmed: strong recordings keep aligning (hybrid/pcen
families correct on every synthetic signal case), low-SNR improves
(pcen_hpss solves the case plain PCEN and flux miss), and evidence-free
recordings can be made to abstain *provided* acceptance is family-calibrated
(a bare PCEN integration with the old Z ≥ 2 rule would have been
false-confident).

## 13. Risks and unresolved questions

1. **Single real low-SNR sample.** All real-data conclusions rest on one
   failure case (plus its export). Need more labeled low-SNR handcam
   recordings before locking thresholds.
2. **Null coverage is narrow** (5 synthetic realizations; no real
   "no-signal" recording yet). Real arcade noise may produce different
   null ceilings per family.
3. **pcen_hpss cost** ≈ 2.1 s on a 3-minute pair (comparable to chroma);
   fine for desktop, but HPSS adds memory for the mel matrix on long
   videos (a 10-minute video ≈ 5× — still modest, but worth measuring in
   RA-1.2B).
4. **Threshold portability:** PCEN/HPSS null behavior may shift with
   sample rate, hop, and n_mels; thresholds must be derived from the same
   config as production.
5. **Onset-family weakness:** when onset is the second agreeing family its
   evidence is thin (margin ~1.0 on the real pair). Whether "strong PCEN +
   thin onset agreement" suffices, or a third independent family is
   needed, must be settled with more labeled data.
6. **Repeated-structure charts:** songs with literal loops produce
   content-ambiguous alignments; the uniqueness gate needs a real-corpus
   calibration.
7. **Abstain UX:** product flow for "无法可靠确定" (message wording, manual
   offset slider handoff) is a product decision, not yet designed.
8. Hybrid remains valuable on strong recordings; lowering or bypassing it
   risks regressions on the healthy majority — the engine must add
   evidence, not replace the working path blindly.

## 14. Recommendation

**READY_FOR_RA12B**

Justification: the motivating failure is reproduced, its root cause is
measured (not guessed), ground truth is independently established, and a
candidate generator (pcen_hpss) exists that solves the real case with
Z 10.4 / margin 1.9 while also passing every synthetic signal case — with a
quantified null model to build abstention on. RA-1.2B scope: implement the
candidate-fusion engine with per-family calibrated thresholds, integrate
the abstain UI flow, and calibrate against a small labeled corpus of real
recordings (strong + low-SNR + no-signal). Do NOT simply lower thresholds
or switch the pipeline to PCEN unconditionally — the no-signal false-confidence
data shows exactly how that fails.

## 15. Exact files changed

Added:
- `docs/RA-1.2A-LOW-SNR-ALIGNMENT.md` (this report)
- `experiments/__init__.py`
- `experiments/low_snr_alignment/__init__.py`
- `experiments/low_snr_alignment/README.md`
- `experiments/low_snr_alignment/harness.py`
- `experiments/low_snr_alignment/run_experiment.py`
- `experiments/low_snr_alignment/synthetic_eval.py`
- `experiments/low_snr_alignment/pcen_sweep.py`
- `experiments/low_snr_alignment/failure_analysis.py`
- `experiments/low_snr_alignment/results/` (run_baseline.json,
  run_final.json, synthetic_run.json, failure_analysis.json — small
  evidence JSONs)

Modified:
- `.gitignore` (ignore local experiment scratch dir `results/`)

Not changed: `auto_sync.py`, `diagnose_offset.py`, `ui_main.py`, `tests/`,
release metadata, version strings. No media committed.

## 16. Exact test results

| check | command | result |
|---|---|---|
| baseline suite (before changes) | `python -m pytest -q` | 19 passed in 10.31s |
| suite (after changes) | `python -m pytest -q` | 19 passed in 3.73s |
| syntax | `python -m compileall -q auto_sync.py diagnose_offset.py ui_main.py tests experiments` | OK (exit 0) |
| whitespace | `git diff --check` | clean (LF/CRLF notice only, no errors) |
| synthetic suite | `python experiments/low_snr_alignment/synthetic_eval.py` | 25 evaluations: 4 false-confident rows (hybrid, pcen_hpss, logmel_flux on no-signal; expected pre-calibration), 5 "WRONG" rows detailed in §12, pcen_hpss correct on all 4 signal cases |
| null distribution | `python experiments/low_snr_alignment/synthetic_eval.py --nulls 5` | table in §12 |
| real-pair comparison | `python experiments/low_snr_alignment/run_experiment.py --json …` | table in §6 |
| sweep | `python experiments/low_snr_alignment/pcen_sweep.py` | 36 configs; all reasonable configs recover +12.42 s on the real pair |
| reproduction (Phase 0) | direct `auto_sync._align_hybrid`/`_align_onset` calls | −1.9969 s / Z 5.485 and +12.4459 s / Z 2.268 |

## 17. Final git status

At report time (before commit):

```
On branch main
HEAD: 44164d1a7321ec9a8ac2977346c3814c6383d227
 M .gitignore
?? experiments/
?? docs/RA-1.2A-LOW-SNR-ALIGNMENT.md
```

Committed as a single commit on `main`; **not pushed**; no tag, no release
metadata change, no version bump, no production behavior change.
