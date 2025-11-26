"""Tests for the ``rhc-playbook-verifier`` executable."""

import os
import subprocess
from pathlib import Path
from typing import ClassVar
from unittest import TestCase


class PlaybookTestCase(TestCase):
    """Execute ``rhc-playbook-verifier --playbook=...``."""

    data_dir: ClassVar[Path]

    @classmethod
    def setUpClass(cls) -> None:
        """Set class variables."""
        cls.data_dir = Path(__file__).parents[3].absolute() / "data"

    def test_valid_playbooks(self) -> None:
        """Consume valid playbooks."""
        playbook_files = (
            "bugs.yml",
            "document-from-hell.yml",
            "insights_remove.yml",
            "unicode.yml",
        )
        playbook_paths = (
            self.data_dir / "playbooks" / playbook_file
            for playbook_file in playbook_files
        )
        for playbook_path in playbook_paths:
            with self.subTest(playbook_path=playbook_path):
                result = self._verify_playbook(playbook_path)
                self.assertEqual(result.returncode, 0, result.stderr.strip())
                playbook_content: str = playbook_path.read_text()
                self.assertEqual(result.stdout.strip(), playbook_content.strip())

    def test_invalid_playbooks(self) -> None:
        """Consume invalid playbooks."""
        playbook_files = ("invalid-signature.yml",)
        playbook_paths = tuple(
            self.data_dir / "playbooks-unsigned" / playbook_file
            for playbook_file in playbook_files
        )
        for playbook_path in playbook_paths:
            with self.subTest(playbook_path=playbook_paths):
                result = self._verify_playbook(playbook_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("rhc_playbook_lib.PreconditionError", result.stderr)
                self.assertIn("not a valid base64 string", result.stderr)

    @staticmethod
    def _verify_playbook(playbook_path: Path) -> subprocess.CompletedProcess:
        """Call rhc-playbook-verifier; do not assert on return code."""
        return subprocess.run(
            [
                "rhc-playbook-verifier",
                "--playbook",
                str(playbook_path),
                "--debug",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C.UTF-8"},
        )
