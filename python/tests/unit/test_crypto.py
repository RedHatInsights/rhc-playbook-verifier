import os.path
import pathlib
import shutil
import subprocess
import sys
import tempfile
import uuid

from unittest import main, mock, TestCase

from rhc_playbook_lib import crypto
from rhc_playbook_lib import _keygen


GPG_OWNER = "rhc-playbook-verifier test"


class TestCrypto(TestCase):
    __home = ""
    __gpg_fingerprint = None

    def tearDown(self) -> None:
        if self.__home != "":
            shutil.rmtree(self.__home, ignore_errors=True)
            self.__home = ""
            self.__gpg_fingerprint = None

    def setUp(self) -> None:
        """Save GPG keys and sign a file with them.

        Populate the given (home) directory with the following files:

        - key.public.gpg
        - key.private.gpg
        - key.fingerprint.txt
        - file.txt
        - file.txt.asc

        It stores the fingerprint of the generated key pair and home directory in attributes.
        """
        self.gpg_path = (
            "/usr/local/bin/gpg" if sys.platform == "darwin" else "/usr/bin/gpg"
        )

        self.__home = tempfile.mkdtemp()
        # Generate the keys and save them
        gpg_tmp_dir = _keygen._generate_keys()
        _keygen._export_key_pair(gpg_tmp_dir, self.__home)

        # Import the public and private keys
        # It is strictly not necessary to import both public and private keys,
        #  the private key should be enough.
        #  However, the Python 2.6 CI image requires that.
        subprocess.run(
            [
                self.gpg_path,
                "--homedir",
                self.__home,
                "--import",
                f"{self.__home}/key.public.gpg",
            ],
            capture_output=True,
            check=True,
            env={"LC_ALL": "C.UTF-8"},
        )
        subprocess.run(
            [
                self.gpg_path,
                "--homedir",
                self.__home,
                "--import",
                f"{self.__home}/key.private.gpg",
            ],
            capture_output=True,
            check=True,
            env={"LC_ALL": "C.UTF-8"},
        )

        # Get the fingerprint of the key
        self.__gpg_fingerprint = _keygen._get_fingerprint(gpg_tmp_dir, self.__home)
        self.assertTrue(os.path.exists(self.__home + "/key.fingerprint.txt"))

        # Create a file and sign it
        file = self.__home + "/file.txt"
        with open(file, "w") as f:
            f.write("a signed message")
        subprocess.run(
            [
                self.gpg_path,
                "--homedir",
                self.__home,
                "--detach-sign",
                "--armor",
                file,
            ],
            capture_output=True,
            check=True,
            env={"LC_ALL": "C.UTF-8"},
        )

        # Ensure the signature has been created
        self.assertTrue(os.path.exists(self.__home + "/file.txt.asc"))

    @mock.patch(
        "rhc_playbook_lib.crypto.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_valid_signature(self) -> None:
        """A detached file signature can be verified."""

        # Run the test
        result = crypto.verify_gpg_signed_file(
            file=pathlib.Path(self.__home) / "file.txt",
            signature=pathlib.Path(self.__home) / "file.txt.asc",
            key=pathlib.Path(self.__home) / "key.public.gpg",
        )

        # Verify results
        self.assertTrue(result.ok)
        self.assertEqual("", result.stdout)
        self.assertIn(f'gpg: Good signature from "{GPG_OWNER}"', result.stderr)

        self.assertIn(
            f"Primary key fingerprint: {self.__gpg_fingerprint}", result.stderr
        )
        self.assertEqual(0, result.return_code)

        assert result._command is not None
        assert result._command._home is not None

        self.assertFalse(pathlib.Path(result._command._home).is_file())

    @mock.patch(
        "rhc_playbook_lib.crypto.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_invalid_signature(self) -> None:
        """A bad detached file signature can be detected."""
        # Change the contents of the file, making the signature incorrect
        with open(self.__home + "/file.txt", "w") as f:
            f.write("an unsigned message")

        # Run the test
        result = crypto.verify_gpg_signed_file(
            file=pathlib.Path(self.__home) / "file.txt",
            signature=pathlib.Path(self.__home) / "file.txt.asc",
            key=pathlib.Path(self.__home) / "key.public.gpg",
        )

        # Verify results
        self.assertFalse(result.ok)
        self.assertEqual("", result.stdout)
        self.assertIn(f'gpg: BAD signature from "{GPG_OWNER}"', result.stderr)
        self.assertNotIn(
            f"Primary key fingerprint: {self.__gpg_fingerprint}", result.stderr
        )
        self.assertEqual(1, result.return_code)

        assert result._command is not None
        assert result._command._home is not None

        self.assertFalse(pathlib.Path(result._command._home).is_file())

    @mock.patch(
        "rhc_playbook_lib.crypto.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    @mock.patch("subprocess.Popen")
    @mock.patch.object(crypto.GPGCommand, "_cleanup", return_value=None)
    def test_invalid_gpg_setup(
        self,
        mock_cleanup: mock.MagicMock,
        mock_popen: mock.MagicMock,
    ) -> None:
        """An invalid GPG setup can be detected."""
        gpg_command = crypto.GPGCommand(command=[], key=pathlib.Path("/dummy/key"))

        # Mock the process
        mock_process = mock.Mock()
        mock_process.communicate.return_value = (b"", b"GPG setup failed")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        # Run the test
        result: crypto.GPGCommandResult = gpg_command.evaluate()

        # Verify results
        self.assertFalse(result.ok)
        self.assertEqual("", result.stdout)
        self.assertIn("GPG setup failed", result.stderr)
        self.assertEqual(1, result.return_code)

    @mock.patch(
        "rhc_playbook_lib.crypto.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_missing_public_key(self) -> None:
        """A missing public key can be detected."""
        # Remove the public key
        os.remove(self.__home + "/key.public.gpg")

        # Run the test
        result: crypto.GPGCommandResult = crypto.verify_gpg_signed_file(
            file=pathlib.Path(self.__home) / "file.txt",
            signature=pathlib.Path(self.__home) / "file.txt.asc",
            key=pathlib.Path(self.__home) / "key.public.gpg",
        )

        # Verify results
        self.assertFalse(result.ok)
        self.assertEqual("", result.stdout)
        self.assertIn(
            f"gpg: can't open '{self.__home}/key.public.gpg': No such file or directory",
            result.stderr,
        )
        self.assertEqual(2, result.return_code)

    @mock.patch(
        "rhc_playbook_lib.crypto.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_invalid_public_key(self) -> None:
        """An invalid public key can be detected."""
        # Change the contents of the public key
        with open(self.__home + "/key.public.gpg", "w") as f:
            f.write("invalid key")

        # Run the test
        result: crypto.GPGCommandResult = crypto.verify_gpg_signed_file(
            file=pathlib.Path(self.__home) / "file.txt",
            signature=pathlib.Path(self.__home) / "file.txt.asc",
            key=pathlib.Path(self.__home) / "key.public.gpg",
        )

        # Verify results
        self.assertFalse(result.ok)
        self.assertEqual("", result.stdout)
        self.assertIn("gpg: no valid OpenPGP data found", result.stderr)
        self.assertEqual(2, result.return_code)

    @mock.patch(
        "rhc_playbook_lib.crypto.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_missing_signed_file(self) -> None:
        """A missing signed file can be detected."""
        temp_dir = tempfile.gettempdir()
        unique_filename = str(uuid.uuid4())
        home = os.path.join(temp_dir, unique_filename)

        # Run the test
        with self.assertRaises(FileNotFoundError):
            crypto.verify_gpg_signed_file(
                file=pathlib.Path(home) / "file.txt",
                signature=pathlib.Path(home) / "file.txt.asc",
                key=pathlib.Path(home) / "key.public.gpg",
            )

        self.assertFalse(os.path.isfile(pathlib.Path(home) / "file.txt"))
        self.assertFalse(os.path.isdir(pathlib.Path(home)))

    @mock.patch(
        "rhc_playbook_lib.crypto.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_missing_signature_file(self) -> None:
        """A missing signature file can be detected."""
        # Remove the signature file
        os.remove(self.__home + "/file.txt.asc")

        # Run the test
        with self.assertRaises(FileNotFoundError):
            crypto.verify_gpg_signed_file(
                file=pathlib.Path(self.__home) / "file.txt",
                signature=pathlib.Path(self.__home) / "file.txt.asc",
                key=pathlib.Path(self.__home) / "key.public.gpg",
            )

        self.assertTrue(os.path.isfile(pathlib.Path(self.__home) / "file.txt"))
        self.assertFalse(os.path.isfile(pathlib.Path(self.__home) / "file.txt.asc"))


if __name__ == "__main__":
    main()
