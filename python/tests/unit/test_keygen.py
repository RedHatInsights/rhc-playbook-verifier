"""Tests for module `rhc_playbook_lib._keygen`."""

import tempfile
from contextlib import ExitStack
from unittest import TestCase
from pathlib import Path

from rhc_playbook_lib import _keygen


class TestCallGPG(TestCase):
    """Test subprocess calls to ``/usr/bin/gpg``."""

    def setUp(self) -> None:
        """Create a temporary home directory."""
        self.stack = ExitStack()
        try:
            self.home = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        except:
            self.tearDown()
            raise

    def tearDown(self) -> None:
        """Clean up."""
        self.stack.close()

    def test_run_gpg_command_success(self) -> None:
        """Call ``_keygen._run_gpg_command()`` with a valid command."""
        result = _keygen._run_gpg_command(
            ["/usr/bin/gpg", "--batch", "--homedir", str(self.home), "--version"],
        )
        self.assertTrue(result.ok)
        self.assertIn("gpg (GnuPG)", result.stdout)
        self.assertIn(f"Home: {self.home}", result.stdout)
        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.return_code)

    def test_run_gpg_command_failure(self) -> None:
        """Call ``_keygen._run_gpg_command()`` with an invalid command."""
        result = _keygen._run_gpg_command(
            ["/usr/bin/gpg", "--batch", "--homedir", str(self.home), "--invalid-flag"],
        )
        self.assertFalse(result.ok)
        self.assertEqual("", result.stdout)
        self.assertIn("gpg: invalid option", result.stderr)
        self.assertEqual(2, result.return_code)

    def test_export_key_pair(self) -> None:
        """Call ``_keygen._export_key_pair()``."""
        with _keygen._generate_keys() as gpg_tmp_dir:
            _keygen._export_key_pair(gpg_tmp_dir, str(self.home))
        self.assertTrue((self.home / "key.public.gpg").is_file())
        self.assertTrue((self.home / "key.private.gpg").is_file())

    def test_get_fingerprint(self) -> None:
        """Call ``_keygen._get_fingerprint()``."""
        with _keygen._generate_keys() as gpg_tmp_dir:
            fingerprint = _keygen._get_fingerprint(gpg_tmp_dir)
        self.assertTrue(bool(fingerprint))
