# Panako Comparator Integration

Status: **INTEGRATED — comparator contract frozen before any pilot run.**
SHAKEDOWN_ONLY validation / NOT PAPER EVIDENCE / NO PILOT RECORDING DONE.

This document is the reproducibility record and frozen comparator contract
for the Panako fingerprint comparator (the study's strongest technical
threat arm; `HUMAN_LIGHT_STUDY_DESIGN.md`, `FRESH_PILOT_PLAN.md` section
8). It supersedes the PENDING status recorded in the shakedown round
(`BENCHMARK_SHAKEDOWN.md`; the frozen shakedown manifest and records are
untouched in git history — manifest hash `0c59568f…60091f9` unchanged).

- Runner: `experiments/applied_system/runners/panako_runner.py`
- Validation run: `experiments/applied_system/panako_shakedown_check.py`
- Raw validation artifacts:
  `experiments/applied_system/results/shakedown/panako_integration/`
- Live status probe:
  `experiments/applied_system/results/shakedown/panako_status.json`
  (now `READY_INTEGRATED`)

## Environment

| Item | Value |
|---|---|
| Route | WSL2 (preference order 1 of the plan; Docker not needed) |
| WSL distro | Ubuntu 24.04.4 LTS, kernel 6.6.87-microsoft-standard-WSL2 |
| Java | OpenJDK 17.0.20 (openjdk-17-jdk-headless, apt) |
| ffmpeg | 6.1.1-3ubuntu5 (apt) — Panako's PIPE decoder subprocess |
| Panako version | 2.1 line (no release tags exist upstream) |
| Pinned source commit | `e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211` (HEAD at integration, 2024-05-31) |
| Clone URL | `https://github.com/JorenSix/Panako.git` |
| panako.jar SHA-256 | `77c56eabf93defe64ddddf0fb75478c415dc7b64ddb065b5a34a27f6b9fb2276` |
| Jar path (WSL) | `/home/daozh/.panako/panako.jar` (`$HOME/.panako/panako.jar`; override: env `RHYTHMALIGN_PANAKO_JAR`) |
| Strategy | OLAF — the pinned source's shipped default (`STRATEGY=OLAF` in `resources/defaults/config.properties`), passed explicitly for self-documentation |
| Match acceptance settings | ALL shipped defaults: `OLAF_MIN_HITS_UNFILTERED=10`, `OLAF_MIN_HITS_FILTERED=5`, `OLAF_MIN_SEC_WITH_MATCH=0.2`, `OLAF_MIN_MATCH_DURATION=3` s, `OLAF_MIN/MAX_TIME_FACTOR=0.95/1.05`, `OLAF_QUERY_RANGE=2`, 16 kHz internal rate, 8 ms fingerprint time blocks |
| WSL env note | apt was switched to the TUNA mirror (`/etc/apt/sources.list.d/ubuntu.sources`, backup `ubuntu.sources.orig`) after the default archive trickled at ~12 KB/s; no other WSL-global change |

The jar is built inside WSL and lives in the WSL filesystem; it is never
committed (hash recorded instead). Windows-host runners never run Java
directly — every Panako invocation goes through the wrapper in
`panako_runner.py` (`wsl.exe -e bash -c …`), which owns all path
translation (`D:\…` → `/mnt/d/…`).

## Installation

Reproducible from scratch (as executed for this integration):

```bash
# inside WSL Ubuntu 24.04 (root ok via `wsl.exe -u root`):
apt-get update && apt-get install -y openjdk-17-jdk-headless ffmpeg
# as the normal WSL user:
git clone https://github.com/JorenSix/Panako.git ~/panako-src
cd ~/panako-src
git checkout e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211
./gradlew shadowJar install        # BUILD produces build/libs/panako-2.1-all.jar
cp build/libs/panako-2.1-all.jar ~/.panako/panako.jar   # see note
sha256sum ~/.panako/panako.jar     # record in this document
java -jar ~/.panako/panako.jar --version   # must print "Version: 2.1 …"
```

Note: the upstream `install` Gradle task prints the install message but at
this pinned commit does not actually place the jar (only a `log/` dir
appears); the explicit `cp` above performs the intended install. The
`config.properties` is auto-written next to the jar on first run — the
runner never edits it (per-run store isolation uses CLI overrides, below).

Required JVM flag: `--add-opens=java.base/java.nio=ALL-UNNAMED` — the
pinned build's own documented requirement for LMDB on JDK 9+ (build.gradle
test task: "needed for lmdb to work correctly"). Without it LMDB's
`ByteBufferProxy` fails `setAccessible` on JDK 17 and the store silently
ends up empty.

## Native Semantics

Established from source inspection of the pinned commit AND verified
empirically on shakedown material.

- Subcommands used: `store <file>` (add reference to the store) and
  `query <file>` (match one query file against the store). The 2.1
  README's `query` naming is correct at this commit; there is no `match`
  subcommand.
- `query` prints to stdout a 13-column table, `;`-separated, values
  formatted with `Locale.US` (decimal points guaranteed):

  `Index; Total ; Query path;Query start (s);Query stop (s); Match path;Match id; Match start (s); Match stop (s); Match score; Time factor (%); Frequency factor(%); Seconds with match (%)`

  - Times are seconds on the fingerprint-block grid (8 ms at OLAF
    defaults); Query start/stop are in QUERY time, Match start/stop in
    REFERENCE time.
  - `Match score` = number of aligned matching fingerprints (native
    confidence analog).
  - `Time factor (%)` ≈ replay speed ratio (1.000 % printed for a
    same-speed match — column header says %, value is a ratio).
  - `Seconds with match (%)` is a 0..1 fraction printed with the %
    header (0.98 observed on a near-fully-matching take) — another
    native header/value mismatch, recorded verbatim, never corrected.
- Diagnostic lines (e.g. `Matches <id> (id) Filtered hits: <n> (#) …`)
  are interleaved on stdout; the parser ignores everything that is not a
  13-field row with two leading integer fields.
- A query can yield MULTIPLE valid rows (multiple stored references or
  multiple segments); results are printed best-score-first.
- One query file per invocation is used by the runner (single-query
  semantics; no multi-file batching).

## Offset Convention

**Frozen (verified empirically BEFORE any pilot run):**

```
predicted_offset_s = Query start − Match start
```

(production convention: the reference begins this many seconds into the
query input). Source semantics: `queryStart`/`refStart` are the first
aligned fingerprint-hit times in query/reference time, so
`queryTime = refTime + offset`.

**This REVERSES the FRESH_PILOT_PLAN section 8 proposal**
(`Match start − Query start`), which has the wrong sign. The plan
required exactly this empirical verification before pilot use; the
correction is frozen here and in `panako_runner.py`. Empirical proof on
shakedown GT: `pos_ordinary` (reference begins +2.45 s into the input)
→ row Query start 2.696, Match start 0.240 → +2.456 s (error +6.0 ms);
`pos_negative_offset` (GT −6.0) → −6.000 s (error 0.0 ms). Under the
plan's proposed sign both would be negated and rejected.

Decision row selection (frozen): among valid rows take the highest native
`Match score` (ties → offset closest to 0); all rows are recorded
verbatim in `native_scores.match_rows`.

## No-Match Semantics

Panako does not stay silent on a failed query: it prints an explicit
EMPTY-RESULT row (source: `QueryResult.emptyQueryResult` → printed via
the same table): `Match path` = `null`, `Match start (s)` = −1.000,
`Match score` = −1, query times 0.000. The runner's frozen mapping:

- ≥1 VALID match row (Match path not null, Match start ≥ 0, score ≥ 0)
  → `ACCEPT`
- only empty row(s), or zero rows → `NO_MATCH` (native refusal preserved
  verbatim; never forced to an argmax placement)
- store/query subprocess failure or unparseable output → `ERROR`
  (stderr tail recorded)

Acceptance of a match is entirely Panako's own native behavior — the
shipped hit-count / duration / seconds-with-match / time-factor gates
above. No threshold is invented, added, or bypassed anywhere in the
runner. No hybrid refinement (e.g. GCC-PHAT polishing of Panako offsets)
is performed or permitted here — that would be an undeclared hybrid
system (FRESH_PILOT_PLAN section 8, explicitly forbidden).

Store-per-run: every case runs against a fresh LMDB store directory
inside WSL (`/tmp/panako_runner_store_<pid>_<uuid>`), passed per
invocation via Panako's own CLI config-override mechanism
(`OLAF_LMDB_FOLDER=…`), containing exactly the case's reference and
nothing else; the directory is removed after the query. Nothing outside
the store path is read or written; the shipped `~/.panako` config is
never edited.

## Shakedown Validation

(`python -m experiments.applied_system.panako_shakedown_check`; raw
records in `results/shakedown/panako_integration/`; frozen manifest
hash `0c59568f…60091f9`; SHAKEDOWN_ONLY, machinery validation only.)

| Case | GT (s) | Decision | Offset (s) | Error (ms) |
|---|---|---|---|---|
| pos_zero_lead | 0.000 | ACCEPT | +0.000 | 0.0 |
| pos_ordinary | +2.450 | ACCEPT | +2.456 | +6.0 |
| pos_negative_offset | −6.000 | ACCEPT | −6.000 | 0.0 |
| pos_noise (10 dB SNR) | +2.450 | ACCEPT | +2.456 | +6.0 |
| pos_quiet (×0.35) | +2.450 | ACCEPT | +2.456 | +6.0 |
| pos_clock_drift (+250 ppm) | +2.4514 | ACCEPT | +2.456 | +4.6 |
| wrong_reference (song B vs store A) | — | **NO_MATCH** | — | — |

- Store determinism (store once, query twice): rows byte-identical. ✔
- Repeatability (fresh store per run, pos_ordinary twice): offsets
  identical to 0.0 ms. ✔
- Runtime ≈ 1.8–2.4 s per case (store + query, single core).
- These outcomes validate the COMPARATOR CONTRACT. They say nothing
  about scientific performance: synthetic fixtures, digital degradations,
  one reference per store.

## Comparator Role

Pre-declared rule (FRESH_PILOT_PLAN section 8): median |offset error| over
the positives vs the 100 ms editorial tolerance.

- Measured median |offset error| on the 6 shakedown positives:
  **5.3 ms** ≤ 100 ms → rule outcome **PLACEMENT_COMPARATOR**.
- Classification: **A. PLACEMENT_COMPARATOR** — on this validation
  material Panako's native placement is precise enough for direct timing
  comparison at the benchmark tolerance (6 ms worst case on an 8 ms
  fingerprint grid), AND its native selectivity correctly refused the
  wrong reference. Both roles are available; the study therefore gets the
  placement comparison it hoped for, with the identification/selectivity
  behavior additionally recorded (it is the strongest-threat arm either
  way).
- Scope caveats, recorded honestly: this classification rests on
  SHAKEDOWN_ONLY synthetic material. The pilot re-freezes the role on the
  12 real acoustic takes with the same pre-declared rule before the final
  benchmark; if real-chain precision degrades beyond 100 ms median, the
  role scopes down to IDENTIFICATION/SELECTIVITY exactly as planned
  (either role keeps Panako ESSENTIAL).

## Limitations

- 8 ms fingerprint-block time grid: offsets quantize coarsely relative to
  waveform methods (observed +6 ms systematic bias from first-hit edge
  effects on the fixtures) — recorded natively, never "corrected".
- Match requires ≥3 s of aligned content (native `MIN_MATCH_DURATION`);
  shorter queries can never match by design.
- OLAF rejects replay-speed factors outside 0.95–1.05 (native); drift
  beyond ±50000 ppm is out of its contract (benchmark drift budget is
  ±1000 ppm — comfortably inside).
- Fingerprint matching makes occurrence claims; on repeated-structure
  music (pilot song B) it may legitimately match an earlier/later
  repetition — this is native behavior to be OBSERVED in the pilot, not
  patched.
- WSL dependency: the wrapper requires `wsl.exe` and the WSL default
  user's `~/.panako/panako.jar`; on machines without WSL the runner
  records ERROR (and `panako_available()` is False — tests skip e2e).
- `_sh_quote`-escaped paths are safe for spaces/quotes; a literal
  semicolon in a filename would corrupt the table format (controlled
  inputs only; noted, not defended against).
- java.util.logging INFO lines (ffmpeg probe, store stats) go to stderr;
  the parser reads stdout only, so this is invisible to the contract.

## Reproduction

For an agent reproducing this on the same machine:

1. Environment check (no side effects):
   `python -c "from experiments.applied_system.runners import panako_runner as p; print(p.panako_environment())"`
2. Full validation run (~1 min, WSL+Panako required):
   `python -m experiments.applied_system.panako_shakedown_check`
3. Unit/contract tests (no WSL required except one e2e test that
   self-skips):
   `python -m pytest experiments/applied_system/tests/test_panako_runner.py`
4. Runtime knobs (env vars, all optional): `RHYTHMALIGN_PANAKO_JAR`
   (WSL-side jar path), `RHYTHMALIGN_PANAKO_WSL_DISTRO` (distro name),
   `RHYTHMALIGN_PANAKO_TIMEOUT_S` (per-invocation timeout, default 900).
5. The owner never operates Panako; the runner owns wsl.exe, path
   translation, store lifecycle, and parsing end-to-end.

## Pilot Readiness

- Comparator stack: RhythmAlign v1.2.0 (frozen), GCC-PHAT argmax, NCC
  argmax, Panako 2.1 (WSL2, pinned, contract above) — **all four
  integrated and executable on identical trimmed bytes.**
- Panako status for the pilot: ESSENTIAL, role pre-classified
  PLACEMENT_COMPARATOR (to be re-frozen on pilot data with the same
  rule). Decision mapping, offset convention, row selection, no-match
  semantics, and store-per-run determinism are frozen BEFORE any pilot
  recording — as the plan requires.
- Pilot pack: `experiments/applied_system/pilot_pack/` prepared —
  `take_plan.json` (12 frozen slots + ingest conventions, status
  `AWAITING_KIT_BUILD`), `incoming/` owner drop folder (gitignored),
  `README.md` (agent-facing conventions). Playback buffers cannot exist
  until the kit build receives the owner's two songs + interference
  track (`FRESH_PILOT_PLAN.md` section 12 step 1 — next agent round).
- Owner instructions: `OWNER_PILOT_INSTRUCTIONS.md` (plain-language,
  no DSP terminology; ~1 hour total).
