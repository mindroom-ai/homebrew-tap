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
WORKFLOWS_PATH = Path(__file__).parents[1] / ".github" / "workflows"
WORKFLOW_PATH = WORKFLOWS_PATH / "update-mindroom-cask.yml"
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

    def test_update_cask_text_replaces_one_version_sha256_url_file_and_app(self) -> None:
        source = (
            '  version "2026.6.9"\n  sha256 "8294f897f80e0cc7ee65d00478f72c71b64aafb252ee8a24563a24375a7f3646"\n'
            '  url "https://example.com/v#{version}/MindRoom.dmg"\n'
            '  app "MindRoom.app", target: "MindRoom Chat.app"\n'
        )

        updated = update_mindroom_cask.update_cask_text(
            source,
            version="v2026.6.28",
            sha256="49d6a1262ad9978c06c3374d41828bc096a0992fcac74b5db863361e4ec766b7",
            asset="MindRoom-Chat.dmg",
            app='app "MindRoom Chat.app"',
        )

        self.assertEqual(
            updated,
            '  version "2026.6.28"\n  sha256 "49d6a1262ad9978c06c3374d41828bc096a0992fcac74b5db863361e4ec766b7"\n'
            '  url "https://example.com/v#{version}/MindRoom-Chat.dmg"\n'
            '  app "MindRoom Chat.app"\n',
        )

    def test_update_cask_text_needs_one_app_stanza(self) -> None:
        source = '  version "0"\n  sha256 "' + "0" * 64 + '"\n  url "https://example.com/MindRoom.dmg"\n'

        with self.assertRaisesRegex(ValueError, "expected exactly one app stanza, found 0"):
            update_mindroom_cask.update_cask_text(
                source, version="1", sha256="a" * 64, asset="MindRoom.dmg", app='app "MindRoom.app"'
            )

    def test_workflow_authenticates_homebrew_github_api_calls(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("HOMEBREW_GITHUB_API_TOKEN: ${{ github.token }}", workflow)

    def test_workflows_trust_their_cask_before_loading_it(self) -> None:
        for cask, name in [("mindroom", "update-mindroom-cask.yml"), ("mindroom-chat", "update-mindroom-chat-cask.yml")]:
            workflow = (WORKFLOWS_PATH / name).read_text(encoding="utf-8")
            trust = workflow.index(f"brew trust --cask mindroom-ai/tap/{cask}\n")
            self.assertLess(workflow.index("brew tap mindroom-ai/tap\n"), trust)
            self.assertLess(trust, workflow.index(f"brew style --cask mindroom-ai/tap/{cask}\n"))


CASK_STUB = '  version "0"\n  sha256 "' + "0" * 64 + '"\n  url "https://example.com/v#{version}/X.dmg"\n  app "X.app"\n'


def release(tag_name: str, *asset_names: str, prerelease: bool = False) -> dict[str, object]:
    return {
        "tag_name": tag_name,
        "draft": False,
        "prerelease": prerelease,
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
        for name, (repo, apps, _) in update_mindroom_cask.CASKS.items():
            path = Path(self.tmp_dir.name) / f"{name}.rb"
            path.write_text(CASK_STUB, encoding="utf-8")
            self.casks[name] = (repo, apps, path)
        self.env = patch.dict(os.environ, {"GITHUB_EVENT_NAME": "schedule"}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_main(self, argv: list[str], releases: list[dict[str, object]]) -> list[str]:
        requested_urls: list[str] = []

        def fake_api_json(url: str) -> object:
            requested_urls.append(url)
            return releases

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

    def cask_file(self, name: str) -> Path:
        return self.casks[name][2]

    def test_chat_cask_uses_chat_repo_and_asset(self) -> None:
        mindroom_before = self.cask_file("mindroom").read_bytes()

        urls = self.run_main(["--cask", "mindroom-chat"], [release("v2026.11.199", "MindRoom.dmg")])

        self.assertEqual(
            urls,
            [
                "https://api.github.com/repos/mindroom-ai/mindroom-chat/releases?per_page=30",
                "https://example.com/v2026.11.199/MindRoom.dmg",
            ],
        )
        self.assertEqual(
            self.cask_file("mindroom-chat").read_text(encoding="utf-8"),
            '  version "2026.11.199"\n  sha256 "' + "a" * 64 + '"\n'
            '  url "https://example.com/v#{version}/MindRoom.dmg"\n'
            '  app "MindRoom.app", target: "MindRoom Chat.app"\n',
        )
        self.assertEqual(self.cask_file("mindroom").read_bytes(), mindroom_before)

    def test_chat_cask_takes_the_renamed_dmg_and_its_app(self) -> None:
        urls = self.run_main(
            ["--cask", "mindroom-chat"],
            [release("v2026.11.500", "MindRoom-Chat.dmg"), release("v2026.11.499", "MindRoom.dmg")],
        )

        self.assertEqual(urls[1], "https://example.com/v2026.11.500/MindRoom-Chat.dmg")
        self.assertEqual(
            self.cask_file("mindroom-chat").read_text(encoding="utf-8"),
            '  version "2026.11.500"\n  sha256 "' + "a" * 64 + '"\n'
            '  url "https://example.com/v#{version}/MindRoom-Chat.dmg"\n'
            '  app "MindRoom Chat.app"\n',
        )

    def test_dispatched_asset_names_the_app(self) -> None:
        for asset, app in [
            ("MindRoom-Chat.dmg", 'app "MindRoom Chat.app"'),
            ("MindRoom.dmg", 'app "MindRoom.app", target: "MindRoom Chat.app"'),
        ]:
            with self.subTest(asset=asset):
                self.run_main(
                    ["--cask", "mindroom-chat", "--version", "v2026.11.500", "--asset-url", f"https://example.com/{asset}"],
                    [],
                )
                text = self.cask_file("mindroom-chat").read_text(encoding="utf-8")
                self.assertIn(f"/{asset}\"\n", text)
                self.assertIn(f"  {app}\n", text)

    def test_unknown_asset_raises(self) -> None:
        before = self.cask_file("mindroom-chat").read_bytes()

        with self.assertRaisesRegex(RuntimeError, "is none of the mindroom-chat cask's assets"):
            self.run_main(["--cask", "mindroom-chat", "--version", "1", "--asset-url", "https://example.com/MindRoom.zip"], [])

        self.assertEqual(self.cask_file("mindroom-chat").read_bytes(), before)

    def test_newest_release_with_dmg_wins(self) -> None:
        urls = self.run_main(
            ["--cask", "mindroom-chat"],
            [
                release("v2026.11.201"),
                release("watch-sdk-1", "MindRoom.dmg", prerelease=True),
                release("v2026.11.200", "MindRoom.zip"),
                release("v2026.11.199", "MindRoom.dmg"),
                release("v2026.11.198", "MindRoom.dmg"),
            ],
        )

        self.assertEqual(urls[1], "https://example.com/v2026.11.199/MindRoom.dmg")
        self.assertIn('version "2026.11.199"', self.cask_file("mindroom-chat").read_text(encoding="utf-8"))

    def test_no_release_with_dmg_raises(self) -> None:
        before = self.cask_file("mindroom-chat").read_bytes()

        with self.assertRaisesRegex(RuntimeError, "None of the last 2 mindroom-ai/mindroom-chat releases has a MindRoom-Chat.dmg or MindRoom.dmg asset"):
            self.run_main(["--cask", "mindroom-chat"], [release("v2026.11.199"), release("v2026.11.198", "MindRoom.zip")])

        self.assertEqual(self.cask_file("mindroom-chat").read_bytes(), before)

    def test_default_cask_is_mindroom(self) -> None:
        urls = self.run_main([], [release("v2026.10.700", "MindRoom.dmg")])

        self.assertEqual(
            urls,
            [
                "https://api.github.com/repos/mindroom-ai/mindroom/releases?per_page=30",
                "https://example.com/v2026.10.700/MindRoom.dmg",
            ],
        )
        self.assertIn('version "2026.10.700"', self.cask_file("mindroom").read_text(encoding="utf-8"))

    def test_cask_files_are_updatable_for_each_asset(self) -> None:
        for name, (_, apps, cask_path) in update_mindroom_cask.CASKS.items():
            for asset, app in apps.items():
                with self.subTest(cask=name, asset=asset):
                    updated = update_mindroom_cask.update_cask_text(
                        cask_path.read_text(encoding="utf-8"), version="v2026.11.199", sha256="b" * 64, asset=asset, app=app
                    )

                    self.assertIn('version "2026.11.199"', updated)
                    self.assertIn(f'/v#{{version}}/{asset}"\n', updated)
                    self.assertIn(f"\n  {app}\n", updated)


if __name__ == "__main__":
    unittest.main()
