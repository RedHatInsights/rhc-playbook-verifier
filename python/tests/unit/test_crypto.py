"""Unit tests for module ``rhc_playbook_lib.crypto``."""

import subprocess
from contextlib import ExitStack
from pathlib import Path
from subprocess import CalledProcessError
from tempfile import TemporaryDirectory
from unittest import TestCase

from rhc_playbook_lib import _keygen, crypto

GPG_OWNER = "rhc-playbook-verifier test"


def _initialize_gpg_environment(home: Path) -> str:
    """Save GPG keys and sign a file with them.

    Populate the given (home) directory with the following files:

    - key.public.gpg
    - key.private.gpg
    - file.txt
    - file.txt.asc

    Return the fingerprint of the generated key pair.
    """
    # Generate the keys and save them
    with _keygen._generate_keys() as gpg_tmp_dir:
        _keygen._export_key_pair(gpg_tmp_dir, str(home))
        gpg_fingerprint = _keygen._get_fingerprint(gpg_tmp_dir)

    # Import the public and private keys
    # It is strictly not necessary to import both public and private keys,
    #  the private key should be enough.
    #  However, the Python 2.6 CI image requires that.
    for basename in ("key.public.gpg", "key.private.gpg"):
        subprocess.run(
            ["/usr/bin/gpg", "--homedir", home, "--import", home / basename],
            capture_output=True,
            check=True,
            env={"LC_ALL": "C.UTF-8"},
        )

    # Create a file and sign it
    file_txt = home / "file.txt"
    with file_txt.open("w") as f:
        f.write("a signed message")
    subprocess.run(
        ["/usr/bin/gpg", "--homedir", home, "--detach-sign", "--armor", file_txt],
        capture_output=True,
        check=True,
        env={"LC_ALL": "C.UTF-8"},
    )

    # Ensure the signature has been created
    assert (home / "file.txt.asc").is_file()

    return gpg_fingerprint


class CryptoTestCase(TestCase):
    """Test cases for module ``rhc_playbook_lib.crypto``."""

    def setUp(self) -> None:
        """Create a temporary home directory."""
        self.stack = ExitStack()
        try:
            self.home = Path(self.stack.enter_context(TemporaryDirectory()))
        except:
            self.tearDown()
            raise

    def tearDown(self) -> None:
        """Clean up."""
        self.stack.close()

    def test_valid_signature(self) -> None:
        """A detached file signature can be verified."""
        gpg_fingerprint = _initialize_gpg_environment(self.home)
        result = crypto.verify_gpg_signed_file(
            file=self.home / "file.txt",
            signature=self.home / "file.txt.asc",
            key=self.home / "key.public.gpg",
        )
        self.assertEqual(result.stdout.decode(), "")
        self.assertIn(f'gpg: Good signature from "{GPG_OWNER}"', result.stderr.decode())
        self.assertIn(
            f"Primary key fingerprint: {gpg_fingerprint}", result.stderr.decode()
        )
        self.assertEqual(result.returncode, 0)

    def test_invalid_signature(self) -> None:
        """A bad detached file signature can be detected."""
        gpg_fingerprint = _initialize_gpg_environment(self.home)

        # Change the contents of the file, making the signature incorrect
        with (self.home / "file.txt").open("w") as f:
            f.write("an unsigned message")

        with self.assertRaises(CalledProcessError) as cm:
            crypto.verify_gpg_signed_file(
                file=self.home / "file.txt",
                signature=self.home / "file.txt.asc",
                key=self.home / "key.public.gpg",
            )

        # Verify results
        self.assertEqual("", cm.exception.stdout.decode())
        self.assertIn(
            f'gpg: BAD signature from "{GPG_OWNER}"', cm.exception.stderr.decode()
        )
        self.assertNotIn(
            f"Primary key fingerprint: {gpg_fingerprint}", cm.exception.stderr.decode()
        )

    def test_missing_public_key(self) -> None:
        """A missing public key can be detected."""
        _initialize_gpg_environment(self.home)
        (self.home / "key.public.gpg").unlink()  # remove public key
        with self.assertRaises(CalledProcessError) as cm:
            crypto.verify_gpg_signed_file(
                file=self.home / "file.txt",
                signature=self.home / "file.txt.asc",
                key=self.home / "key.public.gpg",
            )
        self.assertEqual("", cm.exception.stdout.decode())
        self.assertIn(
            f"gpg: can't open '{self.home}/key.public.gpg': No such file or directory",
            cm.exception.stderr.decode(),
        )

    def test_invalid_public_key(self) -> None:
        """An invalid public key can be detected."""
        _initialize_gpg_environment(self.home)
        with (self.home / "key.public.gpg").open("w") as f:
            f.write("invalid key")  # change public key
        with self.assertRaises(CalledProcessError) as cm:
            crypto.verify_gpg_signed_file(
                file=self.home / "file.txt",
                signature=self.home / "file.txt.asc",
                key=self.home / "key.public.gpg",
            )
        self.assertEqual("", cm.exception.stdout.decode())
        self.assertIn("gpg: no valid OpenPGP data found", cm.exception.stderr.decode())

    def test_missing_signed_file(self) -> None:
        """A missing signed file can be detected."""
        with self.assertRaises(FileNotFoundError) as cm:
            crypto.verify_gpg_signed_file(
                file=self.home / "file.txt",
                signature=self.home / "file.txt.asc",
                key=self.home / "key.public.gpg",
            )
        self.assertIn("file.txt", str(cm.exception))
        self.assertFalse((self.home / "file.txt").is_file())

    def test_missing_signature_file(self) -> None:
        """A missing signature file can be detected."""
        _initialize_gpg_environment(self.home)
        (self.home / "file.txt.asc").unlink()  # remove signature file
        with self.assertRaises(FileNotFoundError) as cm:
            crypto.verify_gpg_signed_file(
                file=self.home / "file.txt",
                signature=self.home / "file.txt.asc",
                key=self.home / "key.public.gpg",
            )
        self.assertIn("file.txt.asc", str(cm.exception))
        self.assertTrue((self.home / "file.txt").is_file())
        self.assertFalse((self.home / "file.txt.asc").is_file())
