import hashlib
import json
import os
import re
import ssl
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from dataclasses import dataclass
from typing import Optional

from app_info import APP_NAME, APP_VERSION, GITHUB_LATEST_RELEASE_API, UPDATE_MANIFEST_URLS


USER_AGENT = f"{APP_NAME}/{APP_VERSION}"
SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    version: str
    html_url: str
    setup_name: Optional[str]
    setup_url: Optional[str]
    setup_size: Optional[int]
    sha256: Optional[str]
    body: str
    source: str = ""


class UpdateCheckError(RuntimeError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


def parse_version(version):
    text = str(version).strip().lstrip("vV")
    core = text.split("+", 1)[0].split("-", 1)[0]
    parts = []
    for item in core.split("."):
        match = re.match(r"\d+", item)
        parts.append(int(match.group(0)) if match else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(latest, current):
    return parse_version(latest) > parse_version(current)


def _request(url, accept="application/json"):
    headers = {
        "User-Agent": USER_AGENT,
        "Cache-Control": "no-cache",
    }
    if accept:
        headers["Accept"] = accept

    return urllib.request.Request(
        url,
        headers=headers,
    )


def _ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _find_setup_asset(assets):
    ranked = []
    for asset in assets or []:
        name = asset.get("name") or ""
        lower = name.lower()
        if not asset.get("browser_download_url"):
            continue

        score = None
        if lower.endswith(".exe") and "setup" in lower:
            score = 0
        elif lower.endswith(".msi"):
            score = 1
        elif lower.endswith(".exe"):
            score = 2
        elif lower.endswith(".zip") and "portable" not in lower:
            score = 3

        if score is not None:
            ranked.append((score, name.lower(), asset))

    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked[0][2] if ranked else None


def _asset_sha256(asset, body):
    if not asset:
        return None

    digest = (asset.get("digest") or "").strip()
    if digest.lower().startswith("sha256:"):
        return digest.split(":", 1)[1].strip().lower()

    name = asset.get("name") or ""
    for line in (body or "").splitlines():
        if name and name in line:
            match = SHA256_RE.search(line)
            if match:
                return match.group(0).lower()

    return None


def _fetch_json(url, timeout):
    with urllib.request.urlopen(_request(url), timeout=timeout, context=_ssl_context()) as response:
        return json.loads(response.read().decode("utf-8"))


def release_from_manifest(data, source=""):
    version = (data.get("version") or data.get("tag_name") or "0.0.0").strip().lstrip("vV")
    tag_name = data.get("tag_name") or f"v{version}"
    setup = data.get("setup") or {}

    return ReleaseInfo(
        tag_name=tag_name,
        version=version,
        html_url=data.get("release_url") or "",
        setup_name=setup.get("name"),
        setup_url=setup.get("url"),
        setup_size=setup.get("size"),
        sha256=(setup.get("sha256") or "").lower() or None,
        body=data.get("notes") or "",
        source=source,
    )


def release_from_github_api(data, source="github-api"):

    tag_name = data.get("tag_name") or data.get("name") or ""
    version = tag_name.strip().lstrip("vV") or "0.0.0"
    body = data.get("body") or ""
    setup_asset = _find_setup_asset(data.get("assets"))

    return ReleaseInfo(
        tag_name=tag_name,
        version=version,
        html_url=data.get("html_url") or "",
        setup_name=setup_asset.get("name") if setup_asset else None,
        setup_url=setup_asset.get("browser_download_url") if setup_asset else None,
        setup_size=setup_asset.get("size") if setup_asset else None,
        sha256=_asset_sha256(setup_asset, body),
        body=body,
        source=source,
    )


def _describe_error(error):
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, urllib.error.URLError):
        return str(error.reason)
    return str(error) or type(error).__name__


def _load_local_manifest(local_manifest_path):
    if not local_manifest_path or not os.path.exists(local_manifest_path):
        return None
    with open(local_manifest_path, "r", encoding="utf-8") as fh:
        return release_from_manifest(json.load(fh), source="bundled")


def _fetch_remote_manifest(timeout):
    executor = ThreadPoolExecutor(max_workers=len(UPDATE_MANIFEST_URLS))
    futures = {
        executor.submit(_fetch_json, url, timeout): url
        for url in UPDATE_MANIFEST_URLS
    }
    errors = []

    try:
        for future in as_completed(futures, timeout=timeout):
            url = futures[future]
            try:
                return release_from_manifest(future.result(), source=url)
            except Exception as exc:
                errors.append(f"manifest {_describe_error(exc)}")
    except FuturesTimeoutError:
        errors.append("manifest timeout")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    raise UpdateCheckError(errors)


def fetch_latest_release(timeout=6, local_manifest_path=None, allow_api_fallback=False):
    errors = []

    try:
        return _fetch_remote_manifest(timeout)
    except UpdateCheckError as exc:
        errors.extend(exc.errors)

    if allow_api_fallback:
        try:
            return release_from_github_api(_fetch_json(GITHUB_LATEST_RELEASE_API, timeout))
        except Exception as exc:
            errors.append(f"api {_describe_error(exc)}")

    bundled = _load_local_manifest(local_manifest_path)
    if bundled:
        return bundled

    raise UpdateCheckError(errors)


def format_size(size):
    if not size:
        return "--"
    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def default_download_path(release):
    name = release.setup_name or f"{APP_NAME}_{release.tag_name or release.version}_Setup.exe"
    safe_name = re.sub(r'[<>:"/\\|?*]+', "_", name)
    target_dir = os.path.join(tempfile.gettempdir(), APP_NAME, "updates")
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, safe_name)


def download_file(url, target_path, progress_callback=None, timeout=60):
    part_path = f"{target_path}.part"
    try:
        with urllib.request.urlopen(
            _request(url, accept="application/octet-stream"),
            timeout=timeout,
            context=_ssl_context(),
        ) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(part_path, "wb") as fh:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(min(99, int(downloaded * 100 / total)))
        os.replace(part_path, target_path)
        if progress_callback:
            progress_callback(100)
        return target_path
    except Exception:
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        finally:
            raise


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()
