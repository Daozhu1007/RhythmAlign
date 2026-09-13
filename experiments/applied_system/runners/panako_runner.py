"""Panako fingerprint comparator runner — WSL2 integration.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

THIS IS ENGINEERING SHAKEDOWN-DERIVED MACHINERY.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

Tool provenance: Panako (JorenSix/Panako), 2.1 line, built from the pinned
source commit e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211 with the Gradle
wrapper inside WSL2 Ubuntu 24.04 (the project does not support native
Windows). Windows-host runners invoke it through ``wsl.exe -e bash -c``
with /mnt path translation owned entirely by this wrapper.

Frozen comparator contract (established at integration, BEFORE any pilot
run; full record in docs/research/applied_system/PANAKO_INTEGRATION.md):

  Strategy: OLAF — the pinned source's shipped default (STRATEGY=OLAF in
  resources/defaults/config.properties). The override is passed explicitly
  for self-documentation, not as a change. Every match-acceptance setting
  stays at the shipped default (OLAF_MIN_HITS_UNFILTERED=10,
  OLAF_MIN_HITS_FILTERED=5, OLAF_MIN_SEC_WITH_MATCH=0.2,
  OLAF_MIN_MATCH_DURATION=3 s, OLAF_MIN/MAX_TIME_FACTOR=0.95/1.05, query
  range 2, 16 kHz internal rate, 8 ms fingerprint time blocks): no
  threshold is invented or tuned here.

  Store-per-run: every case gets a fresh LMDB directory inside the WSL
  filesystem (/tmp/panako_runner_store_...), passed per invocation via the
  CLI config-override mechanism (OLAF_LMDB_FOLDER=...). The store contains
  exactly the case's reference and nothing else; stores are discarded after
  the query.

  Native match semantics (verified empirically on shakedown material, and
  consistent with source inspection):
    - ``query`` prints a 13-column ';'-separated table (Locale.US, so
      decimal points are always '.'). Interleaved non-table diagnostic
      lines can appear on stdout and are ignored by the parser.
    - >=1 VALID match row (Match path != 'null' and Match start >= 0)
        -> ACCEPT. The offset comes from the valid row with the highest
        native Match score (fingerprint hit count); all rows are recorded.
    - only the native EMPTY row (or no rows) -> NO_MATCH. Panako prints an
      explicit empty-result row (Match path 'null', Match start -1, Match
      score -1): this is the tool's native refusal, preserved verbatim.
      It is never converted to an argmax placement.
    - store/query subprocess failure or unparseable output -> ERROR.

  Offset convention (production convention: the reference begins this many
  seconds into the query input):
      predicted_offset_s = Query start - Match start          [seconds]
    Source semantics (OlafStrategy): queryStart/refStart are the first
    aligned fingerprint-hit times in query time and reference time, so
    queryTime = refTime + offset, i.e. offset = Query start - Match start.
    EMPIRICAL VERIFICATION REVERSED the FRESH_PILOT_PLAN section 8 proposal
    ("Match start - Query start"), which has the wrong sign; this was
    corrected here BEFORE any pilot run, as that plan requires.

  Hybrid restriction: no post-hoc refinement of Panako output (e.g. with
  GCC-PHAT) is performed here; such a step would be an undeclared hybrid
  system and is forbidden by the study plan.
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .common import (DECISION_ACCEPT, DECISION_ERROR, DECISION_NO_MATCH,
                     SEMANTICS_SELECTIVE_NO_MATCH, RunnerRecord)

SYSTEM_ID = "panako_fingerprint"

STATUS_READY = "READY_INTEGRATED"
STATUS_PENDING = "PENDING_NOT_INSTALLED"
STATUS_BLOCKED = "BLOCKED"

# Pinned upstream source (no release tags exist for the 2.1 line; HEAD at
# integration time). Recorded again in PANAKO_INTEGRATION.md and the
# environment probe.
PANAKO_CLONE_URL = "https://github.com/JorenSix/Panako.git"
PANAKO_PINNED_COMMIT = "e4b0e1dbb55e340bc66c90bac0ceb82b2cf84211"
PANAKO_STRATEGY = "OLAF"

# Jar location INSIDE WSL (bash expands it; override with an absolute
# WSL-side path via the environment variable).
DEFAULT_JAR_WSL = "$HOME/.panako/panako.jar"
ENV_JAR_WSL = "RHYTHMALIGN_PANAKO_JAR"
ENV_WSL_DISTRO = "RHYTHMALIGN_PANAKO_WSL_DISTRO"
ENV_TIMEOUT_S = "RHYTHMALIGN_PANAKO_TIMEOUT_S"
DEFAULT_TIMEOUT_S = 900

OUTPUT_SEMANTICS = SEMANTICS_SELECTIVE_NO_MATCH
OFFSET_CONVENTION = ("predicted_offset_s = Query start - Match start "
                     "(reference begins this many seconds into the input; "
                     "verified empirically on shakedown GT)")


# ---------------------------------------------------------------------------
# WSL plumbing (owned by the wrapper, never by the benchmark)
# ---------------------------------------------------------------------------


def to_wsl_path(path) -> str:
    """Translate a Windows path to its /mnt/... WSL view. POSIX paths that
    already live under /mnt pass through unchanged."""
    p = Path(str(path))
    posix = p.as_posix()
    if posix.startswith("/mnt/") or posix.startswith("/"):
        return posix
    resolved = p.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        raise ValueError(f"cannot translate path to WSL view: {path}")
    rel = resolved.relative_to(resolved.anchor).as_posix()
    return f"/mnt/{drive}/{rel}"


def _sh_quote(s: str) -> str:
    return "'" + str(s).replace("'", "'\\''") + "'"


def _wsl_bash(script: str, timeout_s: float | None = None):
    """Run one bash script inside WSL. Returns a CompletedProcess with
    utf-8-decoded streams (Linux side writes UTF-8)."""
    cmd = ["wsl.exe"]
    distro = os.environ.get(ENV_WSL_DISTRO)
    if distro:
        cmd += ["-d", distro]
    cmd += ["-e", "bash", "-c", script]
    timeout = timeout_s if timeout_s is not None else float(
        os.environ.get(ENV_TIMEOUT_S, DEFAULT_TIMEOUT_S))
    return subprocess.run(cmd, capture_output=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


def _jar_path() -> str:
    return os.environ.get(ENV_JAR_WSL, DEFAULT_JAR_WSL)


JVM_LMDB_FLAG = "--add-opens=java.base/java.nio=ALL-UNNAMED"


def _panako_invocation_prefix(store_dir_wsl: str | None) -> str:
    """`java -jar ...` plus the frozen, shipped-default config overrides.
    OLAF_LMDB_FOLDER redirects the store for THIS invocation only; nothing
    outside the per-run store directory is read or written. The --add-opens
    flag is the pinned build's own documented requirement for LMDB on
    JDK 9+ (build.gradle test task: "needed for lmdb to work correctly").
    The jar path is resolved inside WSL via `eval echo` so the default
    $HOME form expands while quoted override paths with spaces stay safe.
    """
    overrides = [f"STRATEGY={PANAKO_STRATEGY}"]
    if store_dir_wsl is not None:
        overrides.append(f"OLAF_LMDB_FOLDER={store_dir_wsl}")
    return ("jar=$(eval echo " + _sh_quote(_jar_path()) + "); "
            "java " + JVM_LMDB_FLAG + " -jar \"$jar\" "
            + " ".join(overrides))


# ---------------------------------------------------------------------------
# native output parsing (pure functions — unit-tested without WSL)
# ---------------------------------------------------------------------------


@dataclass
class PanakoRow:
    """One native query-output table row, fields kept verbatim."""

    index: int
    total: int
    query_path: str
    query_start_s: float
    query_stop_s: float
    match_path: str | None      # None for the native empty-result row
    match_id: str
    match_start_s: float
    match_stop_s: float
    match_score: float
    time_factor: float
    frequency_factor: float
    seconds_with_match: float
    raw_line: str

    @property
    def is_valid_match(self) -> bool:
        """False for the native empty-result row (Match path 'null', Match
        start -1, Match score -1): Panako's explicit refusal."""
        return (self.match_path is not None
                and self.match_start_s >= 0.0
                and self.match_score >= 0.0)

    def offset_s(self) -> float:
        """Production-convention offset for this row: Query start minus
        Match start (see module docstring for the sign argument)."""
        return self.query_start_s - self.match_start_s

    def as_dict(self) -> dict:
        return {
            "index": self.index, "total": self.total,
            "query_path": self.query_path,
            "query_start_s": self.query_start_s,
            "query_stop_s": self.query_stop_s,
            "match_path": self.match_path, "match_id": self.match_id,
            "match_start_s": self.match_start_s,
            "match_stop_s": self.match_stop_s,
            "match_score": self.match_score,
            "time_factor_percent": self.time_factor,
            "frequency_factor_percent": self.frequency_factor,
            "seconds_with_match_percent": self.seconds_with_match,
            "is_valid_match": self.is_valid_match,
        }


def _parse_float(field: str) -> float:
    """Panako forces Locale.US, so '.' decimals are guaranteed; tolerate a
    comma fallback defensively (never observed)."""
    return float(field.strip().replace(",", "."))


def parse_query_output(stdout: str) -> list:
    """Extract native match rows from `panako query` stdout.

    Tolerates the documented noise on stdout (diagnostic lines such as
    'Matches ... (id) Filtered hits: ...', blank lines, the header). Any
    13-field ';'-separated line whose first two fields are integers is a
    table row; everything else is ignored. Malformed numeric fields raise
    ValueError (callers convert that into an ERROR record).
    """
    rows = []
    for line in stdout.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) != 13:
            continue
        try:
            index, total = int(parts[0]), int(parts[1])
        except ValueError:
            continue  # header or noise
        match_path = None if parts[5] == "null" or parts[5] == "" \
            else parts[5]
        rows.append(PanakoRow(
            index=index, total=total, query_path=parts[2],
            query_start_s=_parse_float(parts[3]),
            query_stop_s=_parse_float(parts[4]),
            match_path=match_path, match_id=parts[6],
            match_start_s=_parse_float(parts[7]),
            match_stop_s=_parse_float(parts[8]),
            match_score=_parse_float(parts[9]),
            time_factor=_parse_float(parts[10].replace("%", "").strip()),
            frequency_factor=_parse_float(parts[11].replace("%", "").strip()),
            seconds_with_match=_parse_float(parts[12]),
            raw_line=line))
    return rows


def normalize_decision(rows: list) -> tuple:
    """Frozen decision mapping: (decision, selected_row, native_info).

    >=1 valid row -> ACCEPT (row with the highest native Match score);
    otherwise NO_MATCH (native refusal: empty row(s) or zero rows).
    """
    valid = [r for r in rows if r.is_valid_match]
    if valid:
        best = max(valid, key=lambda r: (r.match_score,
                                         -abs(r.offset_s())))
        return DECISION_ACCEPT, best, {"n_valid_match_rows": len(valid),
                                       "n_empty_rows": len(rows) - len(valid)}
    return DECISION_NO_MATCH, None, {
        "n_valid_match_rows": 0,
        "n_empty_rows": sum(1 for r in rows if not r.is_valid_match),
        "native_refusal": "no valid match row (native empty-result row "
                          "or no rows)"}


# ---------------------------------------------------------------------------
# availability probing
# ---------------------------------------------------------------------------


def panako_available() -> bool:
    """True only if the WSL route can run Panako: bash reachable, java on
    PATH inside WSL, and the built jar present."""
    ok, _ = panako_environment()
    return ok


def panako_environment() -> tuple:
    """Probe the WSL Panako installation. Returns (ok, info dict with
    java/ffmpeg/jar/version details and the jar's SHA-256)."""
    info = {
        "route": "WSL2 (Ubuntu 24.04)",
        "jar_wsl_path": _jar_path(),
        "clone_url": PANAKO_CLONE_URL,
        "pinned_commit": PANAKO_PINNED_COMMIT,
        "strategy": PANAKO_STRATEGY,
    }
    script = (
        "JAR=$(eval echo " + _sh_quote(_jar_path()) + "); "
        "test -f \"$JAR\" || exit 3; "
        "command -v java >/dev/null || exit 4; "
        "command -v ffmpeg >/dev/null || exit 5; "
        "echo JAR=$JAR; "
        "sha256sum \"$JAR\" | cut -d' ' -f1; "
        "java -version 2>&1 | head -1; "
        "ffmpeg -version 2>&1 | head -1; "
        "java -jar \"$JAR\" --version 2>&1 | tail -2")
    try:
        proc = _wsl_bash(script, timeout_s=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
        return False, info
    if proc.returncode != 0:
        info["error"] = (f"wsl probe exit {proc.returncode}: "
                         f"{(proc.stderr or '').strip()[-300:]}")
        return False, info
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines()
             if ln.strip()]
    for line in lines:
        if line.startswith("JAR="):
            info["jar_resolved_path"] = line[4:]
    if len(lines) >= 4:
        info["jar_sha256"] = lines[1]
        info["java_version_line"] = lines[2]
        info["ffmpeg_version_line"] = lines[3]
        info["panako_version_line"] = " ".join(lines[4:])
    return True, info


# ---------------------------------------------------------------------------
# runner entry (shakedown harness contract)
# ---------------------------------------------------------------------------


def _error_record(case_id: str, message: str, notes: dict) -> RunnerRecord:
    return RunnerRecord(
        system=SYSTEM_ID, case_id=case_id, decision=DECISION_ERROR,
        predicted_offset_s=None,
        native_scores={"error": message},
        runtime_s=0.0, output_semantics=OUTPUT_SEMANTICS, notes=notes)


def _run_store_and_query(wsl_ref: str, wsl_in: str, store_dir: str,
                         cleanup: bool, timeout_s: float) -> tuple:
    """Store the reference into a fresh store, then query the input.
    Returns (returncode, stdout, stderr, store_stdout)."""
    prefix = _panako_invocation_prefix(store_dir)
    store_script = f"{prefix} store {_sh_quote(wsl_ref)}"
    store_proc = _wsl_bash(store_script, timeout_s)
    if store_proc.returncode != 0:
        return store_proc.returncode, store_proc.stdout, store_proc.stderr, \
            store_proc.stdout
    cleanup_suffix = (f"; rc=$?; rm -rf {_sh_quote(store_dir)}; exit $rc"
                      if cleanup else "")
    query_script = (f"{prefix} query {_sh_quote(wsl_in)}{cleanup_suffix}")
    query_proc = _wsl_bash(query_script, timeout_s)
    return query_proc.returncode, query_proc.stdout, query_proc.stderr, \
        store_proc.stdout


def run_case(case: dict, input_path, reference_path, fs: int,
             load_audio=None) -> RunnerRecord:
    """One (reference -> query) comparator case through native Panako.

    Consumes the SAME file bytes every other comparator receives (the
    trimmed 48 kHz WAV); Panako resamples internally via ffmpeg. load_audio
    is accepted for harness-signature compatibility and unused: this
    comparator never touches decoded samples. Store-per-run: the fresh LMDB
    store contains exactly this case's reference.
    """
    case_id = case["case_id"]
    t0 = time.perf_counter()
    timeout_s = float(os.environ.get(ENV_TIMEOUT_S, DEFAULT_TIMEOUT_S))
    store_dir = f"/tmp/panako_runner_store_{os.getpid()}_{uuid.uuid4().hex}"
    try:
        wsl_ref = to_wsl_path(reference_path)
        wsl_in = to_wsl_path(input_path)
    except (ValueError, OSError) as exc:
        return _error_record(case_id,
                             f"path translation failed: "
                             f"{type(exc).__name__}: {exc}", {})
    try:
        rc, out, err, store_out = _run_store_and_query(
            wsl_ref, wsl_in, store_dir, cleanup=True, timeout_s=timeout_s)
    except subprocess.TimeoutExpired as exc:
        return _error_record(
            case_id, f"panako invocation timed out after {timeout_s}s",
            {"stage": "store/query", "timeout_s": timeout_s,
             "stderr_tail": str(exc)[-400:]})
    except OSError as exc:
        return _error_record(case_id,
                             f"wsl invocation failed: "
                             f"{type(exc).__name__}: {exc}", {})
    runtime = time.perf_counter() - t0

    if rc != 0:
        return _error_record(
            case_id, f"panako subprocess exit {rc}",
            {"stderr_tail": (err or "").strip()[-400:],
             "stdout_tail": (out or "").strip()[-200:]})
    try:
        rows = parse_query_output(out or "")
    except ValueError as exc:
        return _error_record(
            case_id, f"native output parse failure: {exc}",
            {"stdout_tail": (out or "").strip()[-400:]})

    decision, best, native_info = normalize_decision(rows)
    native = {**native_info, "match_rows": [r.as_dict() for r in rows]}
    notes = {"offset_convention": OFFSET_CONVENTION,
             "store_dir": store_dir, "strategy": PANAKO_STRATEGY,
             "no_threshold_invented": True,
             "hybrid_refinement": "none (forbidden by study plan)"}
    if decision == DECISION_ACCEPT:
        return RunnerRecord(
            system=SYSTEM_ID, case_id=case_id, decision=DECISION_ACCEPT,
            predicted_offset_s=best.offset_s(), native_scores=native,
            runtime_s=runtime, output_semantics=OUTPUT_SEMANTICS,
            notes={**notes, "selected_row_index": best.index,
                   "selected_match_score": best.match_score})
    return RunnerRecord(
        system=SYSTEM_ID, case_id=case_id, decision=DECISION_NO_MATCH,
        predicted_offset_s=None, native_scores=native, runtime_s=runtime,
        output_semantics=OUTPUT_SEMANTICS, notes=notes)
