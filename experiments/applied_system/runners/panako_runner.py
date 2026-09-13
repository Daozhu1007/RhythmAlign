"""Panako fingerprint comparator — feasibility assessment and PENDING stub.

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE.

Feasibility probe (2026-09-13, shakedown round):

  - Panako (JorenSix/Panako, latest changelog 2.1, May 2022) publishes NO
    prebuilt artifacts: GitHub Releases is empty and no Maven artifact is
    offered.
  - Installation requires building from source via the Gradle wrapper
    (``./gradlew shadowJar`` then ``gradle install`` -> ``~/.panako/panako.jar``),
    a JDK 11+ toolchain, and ffmpeg on PATH.
  - Windows is NOT supported natively; the project documents WSL or Docker
    as the supported routes.

Decision (shakedown spec section 10: integrate only if reasonably available
without large environment/setup work): the build-from-source + WSL/Docker
requirement is exactly the kind of environment/setup burden the shakedown was
told not to sink time into. Status is therefore PENDING with the integration
plan below; this does NOT block the shakedown verdict (spec section 18
explicitly allows PASS_WITH_FIXES for pending Panako integration).

Integration plan (for the pilot round, not this shakedown):

  1. Environment: WSL2 (Ubuntu 24.04) with openjdk-17-jdk and ffmpeg; OR
     Docker via the project's own Dockerfile. Windows-host runners would
     call the WSL/Docker binary through a wrapper command; the wrapper, not
     the benchmark, owns that translation.
  2. Build: clone the repo at a pinned commit, record the commit hash and
     `java -version` output in the reproducibility environment record,
     build once, and keep the resulting panako.jar inside the experiment's
     gitignored tool cache (never committed; hash recorded instead).
  3. Reference ingestion: `panako store <reference.wav>` once per reference
     into a dedicated fingerprint store directory per run; store path
     recorded in the manifest provenance.
  4. Query: `panako match <trimmed_input.wav>` per case; parse its native
     text/JSON match records (query time, reference time, score).
  5. Semantics: fingerprint matches are OCCURRENCE claims, not whole-song
     placement offsets (study design section 8 warning). The runner records
     native match records verbatim; the decision mapping for the benchmark
     contract is: >=1 reported match -> ACCEPT with predicted offset derived
     from the (query->reference) time mapping; zero matches -> NO_MATCH
     (native refusal, never forced to argmax). This mapping must be frozen
     in writing BEFORE the first pilot run and must not be revisited after
     seeing results.
  6. Reproducibility: fingerprint stores must be rebuilt deterministically
     per run (fresh store dir), and one stored query repeated twice to
     verify store determinism before trusting outputs.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .common import RunnerRecord

SYSTEM_ID = "panako_fingerprint"
STATUS_PENDING = "PENDING_NOT_INSTALLED"


def panako_available() -> bool:
    """True only if a runnable panako binary is reachable (PATH or the
    conventional ~/.panako/panako.jar install location)."""
    if shutil.which("panako"):
        return True
    jar = Path.home() / ".panako" / "panako.jar"
    if jar.exists() and shutil.which("java"):
        return True
    return False


def run_case(*args, **kwargs) -> RunnerRecord:
    """Not available in this shakedown round — integration is PENDING.

    Raises with the reason; the shakedown harness catches this and records
    the PENDING status instead of fabricating results.
    """
    raise NotImplementedError(
        "Panako comparator is PENDING for this shakedown round: no prebuilt "
        "artifact exists and native Windows is unsupported (requires WSL or "
        "Docker build). See runners/panako_runner.py module docstring for "
        "the frozen integration plan.")
