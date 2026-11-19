#!/usr/bin/env python3
"""Update a MindRoom cask from the newest GitHub release that carries its DMG."""

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

ROOT = Path(__file__).resolve().parents[2]
# Cask name: (GitHub repository, {release asset: the cask's app stanza for it}, cask file). The
# updater writes the url's file name and the app stanza from the asset the release carries.
CASKS: dict[str, tuple[str, dict[str, str], Path]] = {
    "mindroom": ("mindroom-ai/mindroom", {"MindRoom.dmg": 'app "MindRoom.app"'}, ROOT / "Casks" / "mindroom.rb"),
    "mindroom-chat": (
        "mindroom-ai/mindroom-chat",
        {
            "MindRoom-Chat.dmg": 'app "MindRoom Chat.app"',
            # Releases from before the rename: MindRoom.app, which the menu bar app installs as too.
            "MindRoom.dmg": 'app "MindRoom.app", target: "MindRoom Chat.app"',
        },
        ROOT / "Casks" / "mindroom-chat.rb",
    ),
}
VERSION_RE = re.compile(r'^(?P<indent>\s*)version "[^"]+"$')
SHA256_RE = re.compile(r'^(?P<indent>\s*)sha256 "[0-9a-f]{64}"$')
URL_RE = re.compile(r'^(?P<head>\s*url "[^"]*/)[^"/]+"$')
APP_RE = re.compile(r'^(?P<indent>\s*)app "[^"]+"(?:, target: "[^"]+")?$')


def api_json(url: str) -> object:
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


def newest_release_with_asset(repo: str, asset_names: dict[str, str]) -> tuple[str, str]:
    # A release gets its DMG from a macOS build that finishes after the release is published, and
    # never gets one when that build fails, so the newest release can lack it. The casks' livecheck
    # picks the same release, or `brew audit --online` fails on the version.
    releases = api_json(f"https://api.github.com/repos/{repo}/releases?per_page=30")
    if not isinstance(releases, list):
        raise RuntimeError(f"{repo} releases response is not a list")

    for release in releases:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        assets = release.get("assets", [])
        if not isinstance(assets, list):
            continue
        for asset in assets:
            if isinstance(asset, dict) and asset.get("name") in asset_names:
                version = normalize_version(str(release["tag_name"]))
                return version, str(asset["browser_download_url"])

    raise RuntimeError(f"None of the last {len(releases)} {repo} releases has a {' or '.join(asset_names)} asset")


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


def update_cask_text(text: str, *, version: str, sha256: str, asset: str, app: str) -> str:
    version = validate_version(version)
    sha256 = validate_sha256(sha256)
    # The stanzas this rewrites, each of which the cask must have exactly once.
    stanzas = {
        "version": (VERSION_RE, lambda match: f'{match["indent"]}version "{version}"'),
        "sha256": (SHA256_RE, lambda match: f'{match["indent"]}sha256 "{sha256}"'),
        "url": (URL_RE, lambda match: f'{match["head"]}{asset}"'),
        "app": (APP_RE, lambda match: f'{match["indent"]}{app}'),
    }
    counts = dict.fromkeys(stanzas, 0)
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

        for name, (pattern, render) in stanzas.items():
            if match := pattern.match(content):
                source_line = render(match) + newline
                counts[name] += 1
                break
        lines.append(source_line)

    for name, count in counts.items():
        if count != 1:
            raise ValueError(f"expected exactly one {name} stanza, found {count}")

    return "".join(lines)


def update_cask_file(path: Path, *, version: str, sha256: str, asset: str, app: str) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = update_cask_text(text, version=version, sha256=sha256, asset=asset, app=app)

    if updated == text:
        print(f"{path.stem} cask already up to date at {version}")
        return False

    path.write_text(updated, encoding="utf-8")
    print(f"updated {path.stem} cask to {version}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cask", choices=sorted(CASKS), default="mindroom", help="Cask to update")
    parser.add_argument("--version", help="Release version without leading v")
    parser.add_argument("--asset-url", help="Download URL for the cask's release asset")
    args = parser.parse_args()
    repo, apps, cask_path = CASKS[args.cask]

    dispatch_release = release_from_dispatch_event()
    if args.version or args.asset_url:
        if not args.version or not args.asset_url:
            parser.error("--version and --asset-url must be passed together")
        version = normalize_version(args.version)
        asset_url = args.asset_url
    elif dispatch_release:
        version, asset_url = dispatch_release
    else:
        version, asset_url = newest_release_with_asset(repo, apps)

    asset = asset_url.rsplit("/", 1)[-1]
    if asset not in apps:
        raise RuntimeError(f"{asset_url} is none of the {args.cask} cask's assets ({', '.join(apps)})")
    sha256 = download_sha256(asset_url)
    update_cask_file(cask_path, version=version, sha256=sha256, asset=asset, app=apps[asset])
    return 0


if __name__ == "__main__":
    sys.exit(main())
