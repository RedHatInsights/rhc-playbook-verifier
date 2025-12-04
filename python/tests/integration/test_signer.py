"""Tests for the ``rhc-playbook-signer`` executable."""

import os
import textwrap
import subprocess
from contextlib import ExitStack
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from types import TracebackType
from typing import Literal, Optional
from unittest import TestCase


class TestSigner(TestCase):
    """Execute ``rhc-playbook-signer --playbook=...``."""

    def setUp(self) -> None:
        """Create an exit stack."""
        self.stack = ExitStack()
        try:
            self.key_pair = self.stack.enter_context(KeyPair())
        except:
            self.tearDown()
            raise

    def tearDown(self) -> None:
        """Destroy the exit stack."""
        self.stack.close()

    def test_behavior(self) -> None:
        """Sign and verify a revocation list and playbooks."""
        data_dir = Path(__file__).parents[3].absolute() / "data"

        # Sign a revocation list, and write it to disk
        with open(data_dir / "revoked_playbooks.yml") as rev_list_in_fd:
            rev_list = self._sign_rev_list(rev_list_in_fd.read())
        with NamedTemporaryFile(
            mode="xt", prefix="rev-list-", suffix=".yml", delete=False
        ) as rev_list_out_fd:
            rev_list_out_path = Path(rev_list_out_fd.name)
            self.stack.callback(rev_list_out_path.unlink)
            rev_list_out_fd.write(rev_list)

        # Sign playbooks with rhc-playbook-signer, and verify them with rhc-playbook-verifier and
        # the revocation list.
        playbook_paths = (
            # official production playbooks
            data_dir / "playbooks" / "insights_remove.yml",
            # custom playbooks signed by official Red Hat key
            data_dir / "playbooks" / "bugs.yml",
            data_dir / "playbooks" / "document-from-hell.yml",
            # unsigned playbooks
            data_dir / "playbooks-unsigned" / "sample.yml",
        )
        for playbook_path in playbook_paths:
            with self.subTest(playbook_path=playbook_path):
                with open(playbook_path) as playbook_fd:
                    playbook = self._sign_playbook(playbook_fd.read())
                verified_playbook = self._verify_playbook(playbook, rev_list_out_path)
                self.assertEqual(playbook.strip(), verified_playbook.strip())

    def _sign_rev_list(self, rev_list: str) -> str:
        """Sign the given revocation list."""
        proc = subprocess.run(
            [
                "rhc-playbook-signer",
                "--revocation-list",
                "--stdin",
                "--key",
                self.key_pair.privkey_path,
                "--debug",
            ],
            input=rev_list,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "LC_ALL": "C.UTF-8"},
        )

        return proc.stdout

    def _sign_playbook(self, playbook: str) -> str:
        """Sign the given playbook, and return stdout."""
        proc = subprocess.run(
            [
                "rhc-playbook-signer",
                "--stdin",
                "--key",
                self.key_pair.privkey_path,
                "--debug",
            ],
            input=playbook,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "LC_ALL": "C.UTF-8"},
        )

        return proc.stdout

    def _verify_playbook(self, signed_playbook: str, rev_list_path: Path) -> str:
        """Verify the given playbook, and return stdout."""
        proc = subprocess.run(
            [
                "rhc-playbook-verifier",
                "--stdin",
                "--key",
                self.key_pair.pubkey_path,
                "--revocation-list",
                rev_list_path,
                "--debug",
            ],
            input=signed_playbook,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "LC_ALL": "C.UTF-8"},
        )

        self.assertEqual(0, proc.returncode)

        return proc.stdout


class KeyPair:
    """A GPG key pair.

    When instantiated, a random GPG key pair is generated and written to the filesystem. To ensure
    clean-up, use as a context manager::

        with KeyPair() as kp:
            with open(kp.pubkey_path) as pubkey_fd:
                print(pubkey_fd.read())
            with open(kp.privkey_path) as privkey_fd:
                print(privkey_fd.read())
    """

    def __init__(self) -> None:
        """Create a key pair, and write them to the filesystem."""
        gpg_instructions = textwrap.dedent(
            """\
            Key-Type: EDDSA
              Key-Curve: ed25519
            Subkey-Type: ECDH
              Subkey-Curve: cv25519
            Name-Real: Integration test key
            Expire-Date: 0
            %no-protection
            %commit
            """
        )

        with ExitStack() as stack:
            gpg_home: str = stack.enter_context(TemporaryDirectory(prefix="gpg-home-"))

            # Create GPG keys
            instructions_fd = stack.enter_context(
                NamedTemporaryFile(mode="w+t", suffix=".txt")
            )
            instructions_fd.write(gpg_instructions)
            instructions_fd.flush()
            subprocess.run(
                [
                    "/usr/bin/gpg",
                    "--batch",
                    "--generate-key",
                    "--pinentry-mode",
                    "loopback",
                    instructions_fd.name,
                ],
                input=os.devnull,
                capture_output=True,
                check=True,
                text=True,
                env={"GNUPGHOME": gpg_home},
            )

            # Generate keys
            pubkey_proc = subprocess.run(
                ["/usr/bin/gpg", "--export", "--armor"],
                capture_output=True,
                check=True,
                text=True,
                env={"GNUPGHOME": gpg_home},
            )
            privkey_proc = subprocess.run(
                [
                    "/usr/bin/gpg",
                    "--export-secret-keys",
                    "--pinentry-mode",
                    "loopback",
                    "--yes",
                    "--armor",
                ],
                capture_output=True,
                check=True,
                text=True,
                env={"GNUPGHOME": gpg_home},
            )

        # Write keys to filesystem
        with NamedTemporaryFile(
            mode="xt", prefix="public-", suffix=".gpg", delete=False
        ) as pubkey_fd:
            self.pubkey_path = Path(pubkey_fd.name)
            pubkey_fd.write(pubkey_proc.stdout)

        with NamedTemporaryFile(
            mode="xt", prefix="private-", suffix=".gpg", delete=False
        ) as privkey_fd:
            self.privkey_path = Path(privkey_fd.name)
            privkey_fd.write(privkey_proc.stdout)

    # typing.Self available in Python 3.11+
    def __enter__(self) -> "KeyPair":
        """Return self; no effect until exit."""
        return self

    def __exit__(
        self,
        type_: Optional[type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        """Delete public and private keys."""
        self.pubkey_path.unlink()
        self.privkey_path.unlink()
        return False  # Should an exception which occurred be suppressed?
