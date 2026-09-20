"""NIGHTSHIFT-1 release-identity characterization tests.

These tests pin the *current* version-comparison behavior of
``update_checker.parse_version`` / ``is_newer_version`` for every release
identity strategy under consideration for the Linux beta
(docs/NIGHTSHIFT1-LINUX-BETA-REDTEAM.md §6). They are characterization
tests: they document semantics, including the sharp edges, so that any
future change to the version policy is a deliberate, reviewed decision.

Sharp edges pinned here (report-only; no current user-visible defect
because updates are manifest-driven and prerelease tags never enter
``update.json``):

1. Prerelease/build suffixes are silently discarded, so a beta series
   that shares its version core with the installed build can never
   notify (``v1.2.0-linux-beta.1`` -> ``v1.2.0-linux-beta.2`` looks
   unchanged).
2. A client whose embedded APP_VERSION carries a prerelease suffix
   (e.g. ``1.2.1-beta.1``) would never be notified about the stable
   ``1.2.1`` — equality after suffix-stripping.
3. A fourth numeric component is truncated (``1.2.0.1`` == ``1.2.0``).
"""

import pytest

from update_checker import is_newer_version, parse_version


class TestParseVersionMatrix:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("v1.2.0", (1, 2, 0)),
            ("1.2.0", (1, 2, 0)),
            ("v1.2.0-linux-beta.1", (1, 2, 0)),
            ("v1.2.0-beta.1", (1, 2, 0)),
            ("v1.2.1-beta.1", (1, 2, 1)),
            ("v1.2.1", (1, 2, 1)),
            ("v1.3.0", (1, 3, 0)),
            ("v1.2.0+linux.beta.1", (1, 2, 0)),
            ("1.2", (1, 2, 0)),
            # 4th component silently truncated.
            ("1.2.0.1", (1, 2, 0)),
        ],
    )
    def test_parse_version(self, text, expected):
        assert parse_version(text) == expected


class IsNewerAgainstV120:
    Installed = "1.2.0"


class TestIsNewerAgainstInstalled120:
    @pytest.mark.parametrize(
        ("latest", "expected"),
        [
            # Same-core prereleases of the installed build: no notification.
            ("v1.2.0-linux-beta.1", False),
            ("v1.2.0-linux-beta.2", False),
            ("v1.2.0-beta.1", False),
            ("v1.2.0+linux.beta.1", False),
            # Next-core prereleases and stabiles: notification.
            ("v1.2.1-beta.1", True),
            ("v1.2.1", True),
            ("v1.3.0", True),
            ("v1.10.0", True),
            # Truncated 4th component: no notification.
            ("1.2.0.1", False),
        ],
    )
    def test_is_newer_version(self, latest, expected):
        assert is_newer_version(latest, "1.2.0") is expected

    def test_beta_series_cannot_see_itself(self):
        # Consequence of suffix-stripping: a Linux beta on
        # v1.2.0-linux-beta.1 is never told about v1.2.0-linux-beta.2.
        assert not is_newer_version("v1.2.0-linux-beta.2", "v1.2.0-linux-beta.1")

    def test_prerelease_embedded_version_never_sees_own_stable(self):
        # If APP_VERSION ever carried a prerelease suffix, the matching
        # stable release would not be reported as an update.
        assert not is_newer_version("1.2.1", "1.2.1-beta.1")

    def test_prerelease_suffix_does_not_rank_below_stable(self):
        # SemVer would order 1.2.1-beta.1 < 1.2.1; the numeric parser
        # treats them as equal. Relevant only if a manifest ever points
        # a prerelease at clients already on the matching stable.
        assert not is_newer_version("1.2.1-beta.1", "1.2.1")
