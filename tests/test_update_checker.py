import json

import update_checker


def test_version_compare_ignores_v_prefix_and_missing_patch():
    assert update_checker.is_newer_version("v1.1.1", "1.1.0")
    assert update_checker.is_newer_version("1.2", "1.1.9")
    assert not update_checker.is_newer_version("v1.1.0", "1.1.0")
    assert not update_checker.is_newer_version("1.0.9", "1.1.0")


def test_setup_asset_preferred_over_portable_zip():
    assets = [
        {"name": "RhythmAlign-v1.1.1-Portable.zip", "browser_download_url": "zip"},
        {"name": "RhythmAlign_v1.1.1_Setup.exe", "browser_download_url": "exe"},
    ]

    asset = update_checker._find_setup_asset(assets, platform="windows")

    assert asset["name"] == "RhythmAlign_v1.1.1_Setup.exe"


def test_setup_asset_selection_is_windows_only():
    assets = [
        {"name": "RhythmAlign-v1.1.1-Portable.zip", "browser_download_url": "zip"},
        {"name": "RhythmAlign_v1.1.1_Setup.exe", "browser_download_url": "exe"},
    ]

    # CP-2: off-Windows clients never self-install; a Windows setup asset
    # must not be selected for them.
    for platform in ("linux", "macos", "other"):
        assert update_checker._find_setup_asset(assets, platform=platform) is None


def test_current_platform_detection(monkeypatch):
    for platform_name, expected in (
        ("win32", "windows"),
        ("linux", "linux"),
        ("darwin", "macos"),
        ("sunos", "other"),
    ):
        monkeypatch.setattr(update_checker.sys, "platform", platform_name)
        assert update_checker.current_platform() == expected


def test_asset_sha256_reads_github_digest_first():
    asset = {
        "name": "RhythmAlign_v1.1.1_Setup.exe",
        "digest": "sha256:" + "a" * 64,
    }

    assert update_checker._asset_sha256(asset, "") == "a" * 64


def test_asset_sha256_falls_back_to_release_notes_line():
    asset = {"name": "RhythmAlign_v1.1.1_Setup.exe"}
    body = "\n".join(
        [
            "Portable SHA256: " + "b" * 64,
            "RhythmAlign_v1.1.1_Setup.exe SHA256: " + "c" * 64,
        ]
    )

    assert update_checker._asset_sha256(asset, body) == "c" * 64


def test_release_from_manifest_normalizes_version_and_checksum():
    info = update_checker.release_from_manifest(
        {
            "version": "v1.2.3",
            "release_url": "https://example.invalid/release",
            "setup": {
                "name": "Setup.exe",
                "url": "https://example.invalid/Setup.exe",
                "size": 123,
                "sha256": "D" * 64,
            },
        },
        platform="windows",
    )

    assert info.tag_name == "v1.2.3"
    assert info.version == "1.2.3"
    assert info.sha256 == "d" * 64
    assert info.setup_url == "https://example.invalid/Setup.exe"


def test_release_from_manifest_hides_windows_installer_off_windows():
    manifest = {
        "version": "v1.2.3",
        "release_url": "https://example.invalid/release",
        "setup": {
            "name": "RhythmAlign_v1.2.3_Setup.exe",
            "url": "https://example.invalid/RhythmAlign_v1.2.3_Setup.exe",
            "size": 123,
            "sha256": "D" * 64,
        },
    }

    for platform in ("linux", "macos", "other"):
        info = update_checker.release_from_manifest(manifest, platform=platform)

        # No Windows installer may be presented as this platform's update;
        # the UI falls back to opening the releases page.
        assert info.setup_url is None, platform
        assert info.setup_name is None, platform
        assert info.setup_size is None, platform


def test_release_from_manifest_keeps_non_windows_shaped_setup():
    info = update_checker.release_from_manifest(
        {
            "version": "v1.3.0",
            "setup": {
                "name": "RhythmAlign-v1.3.0-linux-x86_64.tar.gz",
                "url": "https://example.invalid/RhythmAlign-v1.3.0-linux-x86_64.tar.gz",
            },
        },
        platform="linux",
    )

    assert info.setup_url == "https://example.invalid/RhythmAlign-v1.3.0-linux-x86_64.tar.gz"


def test_release_from_github_api_selects_no_windows_asset_off_windows():
    data = {
        "tag_name": "v1.2.3",
        "body": "",
        "assets": [
            {
                "name": "RhythmAlign_v1.2.3_Setup.exe",
                "browser_download_url": "https://example.invalid/Setup.exe",
                "size": 123,
            },
            {
                "name": "RhythmAlign-v1.2.3-linux-x86_64.tar.gz",
                "browser_download_url": "https://example.invalid/linux.tar.gz",
                "size": 456,
            },
        ],
    }

    linux_info = update_checker.release_from_github_api(data, platform="linux")
    assert linux_info.setup_url is None

    windows_info = update_checker.release_from_github_api(data, platform="windows")
    assert windows_info.setup_url == "https://example.invalid/Setup.exe"


def test_fetch_latest_release_falls_back_to_local_manifest(monkeypatch, tmp_path):
    def fail_fetch(*args, **kwargs):
        raise OSError("network unavailable")

    manifest = tmp_path / "update.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "1.1.0",
                "tag_name": "v1.1.0",
                "release_url": "https://example.invalid/release",
                "setup": {
                    "name": "Setup.exe",
                    "url": "https://example.invalid/Setup.exe",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(update_checker, "_fetch_json", fail_fetch)

    info = update_checker.fetch_latest_release(local_manifest_path=str(manifest))

    assert info.version == "1.1.0"
    assert info.source == "bundled"
