"""Tests for the MindRoom cask updater."""

from __future__ import annotations

import importlib.util
import json
import os
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


if __name__ == "__main__":
    unittest.main()
