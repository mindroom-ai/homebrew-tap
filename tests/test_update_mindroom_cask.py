"""Tests for the MindRoom cask updater."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_PATH = Path(__file__).parents[1] / ".github" / "scripts" / "update_mindroom_cask.py"
WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "update-mindroom-cask.yml"
spec = importlib.util.spec_from_file_location("update_mindroom_cask", SCRIPT_PATH)
assert spec is not None
assert spec.loader is not None
update_mindroom_cask = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_mindroom_cask)


class ReleaseSourceTests(unittest.TestCase):
    def test_release_dispatch_payload_supplies_version_and_asset_url(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as event_file:
            json.dump(
                {
                    "client_payload": {
                        "tag_name": "v2026.6.28",
                        "asset_url": "https://example.com/MindRoom.dmg",
                    }
                },
                event_file,
            )
            event_file.flush()

            with patch.dict(
                os.environ,
                {
                    "GITHUB_EVENT_NAME": "repository_dispatch",
                    "GITHUB_EVENT_PATH": event_file.name,
                },
                clear=False,
            ):
                self.assertEqual(
                    update_mindroom_cask.release_from_dispatch_event(),
                    ("2026.6.28", "https://example.com/MindRoom.dmg"),
                )

    def test_non_dispatch_event_does_not_supply_release(self) -> None:
        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}, clear=False):
            self.assertIsNone(update_mindroom_cask.release_from_dispatch_event())

    def test_update_cask_text_replaces_one_version_and_sha256(self) -> None:
        source = '  version "2026.6.9"\n  sha256 "8294f897f80e0cc7ee65d00478f72c71b64aafb252ee8a24563a24375a7f3646"\n'

        updated = update_mindroom_cask.update_cask_text(
            source,
            version="v2026.6.28",
            sha256="49d6a1262ad9978c06c3374d41828bc096a0992fcac74b5db863361e4ec766b7",
        )

        self.assertEqual(
            updated,
            '  version "2026.6.28"\n  sha256 "49d6a1262ad9978c06c3374d41828bc096a0992fcac74b5db863361e4ec766b7"\n',
        )

    def test_workflow_authenticates_homebrew_github_api_calls(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("HOMEBREW_GITHUB_API_TOKEN: ${{ github.token }}", workflow)


def release(tag_name: str, *asset_names: str) -> dict[str, object]:
    return {
        "tag_name": tag_name,
        "assets": [
            {"name": name, "browser_download_url": f"https://example.com/{tag_name}/{name}"}
            for name in asset_names
        ],
    }


class CaskSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        # Every cask points at its own temp file, so a run that writes the wrong
        # cask never touches the repository's casks.
        self.casks = {}
        for name, (repo, asset_name, _) in update_mindroom_cask.CASKS.items():
            path = Path(self.tmp_dir.name) / f"{name}.rb"
            path.write_text('  version "0"\n  sha256 "' + "0" * 64 + '"\n', encoding="utf-8")
            self.casks[name] = (repo, asset_name, path)
        self.env = patch.dict(os.environ, {"GITHUB_EVENT_NAME": "schedule"}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_main(self, argv: list[str], latest: dict[str, object]) -> list[str]:
        requested_urls: list[str] = []

        def fake_api_json(url: str) -> dict[str, object]:
            requested_urls.append(url)
            return latest

        def fake_download_sha256(url: str) -> str:
            requested_urls.append(url)
            return "a" * 64

        with (
            patch.dict(update_mindroom_cask.CASKS, self.casks),
            patch.object(update_mindroom_cask, "api_json", fake_api_json),
            patch.object(update_mindroom_cask, "download_sha256", fake_download_sha256),
            patch.object(sys, "argv", ["update_mindroom_cask.py", *argv]),
        ):
            update_mindroom_cask.main()
        return requested_urls

    def test_chat_cask_maps_to_chat_repo_asset_and_file(self) -> None:
        self.assertEqual(
            update_mindroom_cask.CASKS["mindroom-chat"],
            (
                "mindroom-ai/mindroom-chat",
                "MindRoom-Chat.dmg",
                update_mindroom_cask.ROOT / "Casks" / "mindroom-chat.rb",
            ),
        )

    def cask_file(self, name: str) -> Path:
        return self.casks[name][2]

    def test_chat_cask_uses_chat_repo_and_asset(self) -> None:
        mindroom_before = self.cask_file("mindroom").read_bytes()

        urls = self.run_main(
            ["--cask", "mindroom-chat"],
            release("v4.12.6-mindroom.268", "MindRoom.dmg", "MindRoom-Chat.dmg"),
        )

        self.assertEqual(
            urls,
            [
                "https://api.github.com/repos/mindroom-ai/mindroom-chat/releases/latest",
                "https://example.com/v4.12.6-mindroom.268/MindRoom-Chat.dmg",
            ],
        )
        self.assertEqual(
            self.cask_file("mindroom-chat").read_text(encoding="utf-8"),
            '  version "4.12.6-mindroom.268"\n  sha256 "' + "a" * 64 + '"\n',
        )
        self.assertEqual(self.cask_file("mindroom").read_bytes(), mindroom_before)

    def test_chat_release_without_dmg_raises(self) -> None:
        before = self.cask_file("mindroom-chat").read_bytes()

        with self.assertRaisesRegex(RuntimeError, "has no MindRoom-Chat.dmg asset"):
            self.run_main(["--cask", "mindroom-chat"], release("v4.12.6-mindroom.269", "MindRoom.dmg"))

        self.assertEqual(self.cask_file("mindroom-chat").read_bytes(), before)

    def test_default_cask_is_mindroom(self) -> None:
        urls = self.run_main([], release("v2026.10.700", "MindRoom.dmg"))

        self.assertEqual(
            urls,
            [
                "https://api.github.com/repos/mindroom-ai/mindroom/releases/latest",
                "https://example.com/v2026.10.700/MindRoom.dmg",
            ],
        )
        self.assertIn('version "2026.10.700"', self.cask_file("mindroom").read_text(encoding="utf-8"))

    def test_chat_cask_file_is_updatable(self) -> None:
        cask_path = update_mindroom_cask.CASKS["mindroom-chat"][2]

        updated = update_mindroom_cask.update_cask_text(
            cask_path.read_text(encoding="utf-8"), version="v4.12.6-mindroom.268", sha256="b" * 64
        )

        self.assertIn('version "4.12.6-mindroom.268"', updated)


if __name__ == "__main__":
    unittest.main()
