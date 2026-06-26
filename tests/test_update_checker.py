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

    asset = update_checker._find_setup_asset(assets)

    assert asset["name"] == "RhythmAlign_v1.1.1_Setup.exe"


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
        }
    )

    assert info.tag_name == "v1.2.3"
    assert info.version == "1.2.3"
    assert info.sha256 == "d" * 64


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
