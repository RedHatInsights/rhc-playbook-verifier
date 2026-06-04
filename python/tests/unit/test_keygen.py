"""Tests for module `rhc_playbook_lib._keygen`."""

import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest import TestCase

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
