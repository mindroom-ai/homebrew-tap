#!/usr/bin/env python3
"""Update the MindRoom cask from the latest GitHub release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

REPO = "mindroom-ai/mindroom"
ASSET_NAME = "MindRoom.dmg"
ROOT = Path(__file__).resolve().parents[2]
CASK_PATH = ROOT / "Casks" / "mindroom.rb"
VERSION_RE = re.compile(r'^(?P<indent>\s*)version "[^"]+"$')
SHA256_RE = re.compile(r'^(?P<indent>\s*)sha256 "[0-9a-f]{64}"$')


def api_json(url: str) -> dict[str, object]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def latest_release() -> tuple[str, str]:
    release = api_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    tag_name = str(release["tag_name"])
    version = normalize_version(tag_name)
    assets = release.get("assets", [])
    if not isinstance(assets, list):
        raise RuntimeError("Latest release has no assets list")

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if asset.get("name") == ASSET_NAME:
            return version, str(asset["browser_download_url"])

    raise RuntimeError(f"Latest release {tag_name} has no {ASSET_NAME} asset")


def normalize_version(value: str) -> str:
    return value[1:] if value.startswith("v") else value


def release_from_dispatch_event() -> tuple[str, str] | None:
    if os.environ.get("GITHUB_EVENT_NAME") != "repository_dispatch":
        return None

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is required for repository_dispatch")

    with Path(event_path).open(encoding="utf-8") as event_file:
        event = json.load(event_file)

    payload = event.get("client_payload")
    if not isinstance(payload, dict):
        raise RuntimeError("repository_dispatch payload must include client_payload")

    tag_name = payload.get("tag_name")
    asset_url = payload.get("asset_url")
    if not isinstance(tag_name, str) or not tag_name:
        raise RuntimeError("repository_dispatch payload must include tag_name")
    if not isinstance(asset_url, str) or not asset_url:
        raise RuntimeError("repository_dispatch payload must include asset_url")

    return normalize_version(tag_name), asset_url


def download_sha256(url: str) -> str:
    request = Request(url, headers={"User-Agent": "homebrew-tap-cask-updater"})
    digest = hashlib.sha256()
    with tempfile.NamedTemporaryFile() as tmp_file:
        with urlopen(request, timeout=300) as response:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                tmp_file.write(chunk)
    return digest.hexdigest()


def validate_sha256(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
    return value


def validate_version(value: str) -> str:
    value = normalize_version(value)
    if not re.fullmatch(r"\d+(?:\.\d+)*(?:[-,._A-Za-z0-9]+)?", value):
        raise ValueError(f"unsupported cask version: {value}")
    return value


def update_cask_text(text: str, *, version: str, sha256: str) -> str:
    version = validate_version(version)
    sha256 = validate_sha256(sha256)

    version_count = 0
    sha256_count = 0
    lines: list[str] = []
    for source_line in text.splitlines(keepends=True):
        if source_line.endswith("\r\n"):
            newline = "\r\n"
            content = source_line.removesuffix("\r\n")
        elif source_line.endswith("\n"):
            newline = "\n"
            content = source_line.removesuffix("\n")
        else:
            newline = ""
            content = source_line

        if match := VERSION_RE.match(content):
            output_line = f'{match.group("indent")}version "{version}"{newline}'
            version_count += 1
        elif match := SHA256_RE.match(content):
            output_line = f'{match.group("indent")}sha256 "{sha256}"{newline}'
            sha256_count += 1
        else:
            output_line = source_line
        lines.append(output_line)

    if version_count != 1:
        raise ValueError(f"expected exactly one version stanza, found {version_count}")
    if sha256_count != 1:
        raise ValueError(f"expected exactly one sha256 stanza, found {sha256_count}")

    return "".join(lines)


def update_cask_file(path: Path, *, version: str, sha256: str) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = update_cask_text(text, version=version, sha256=sha256)

    if updated == text:
        print(f"mindroom cask already up to date at {version}")
        return False

    path.write_text(updated, encoding="utf-8")
    print(f"updated mindroom cask to {version}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", help="Release version without leading v")
    parser.add_argument("--asset-url", help=f"Download URL for {ASSET_NAME}")
    args = parser.parse_args()

    dispatch_release = release_from_dispatch_event()
    if args.version or args.asset_url:
        if not args.version or not args.asset_url:
            parser.error("--version and --asset-url must be passed together")
        version = normalize_version(args.version)
        asset_url = args.asset_url
    elif dispatch_release:
        version, asset_url = dispatch_release
    else:
        version, asset_url = latest_release()

    sha256 = download_sha256(asset_url)
    update_cask_file(CASK_PATH, version=version, sha256=sha256)
    return 0


if __name__ == "__main__":
    sys.exit(main())
