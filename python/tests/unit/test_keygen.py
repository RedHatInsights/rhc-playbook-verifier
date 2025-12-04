import os.path
import shutil
import tempfile

from unittest import main, mock, TestCase

from rhc_playbook_lib import _keygen


class TestKeygen(TestCase):
    __home = ""

    def setUp(self) -> None:
        self.__home = tempfile.mkdtemp()

    def tearDown(self) -> None:
        if self.__home != "":
            shutil.rmtree(self.__home)
            self.__home = ""

    @mock.patch(
        "rhc_playbook_lib._keygen.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_run_valid_gpg_command(self) -> None:
        """A valid GPG command can be executed."""
        # Run the test
        result = _keygen._run_gpg_command(
            ["/usr/bin/gpg", "--batch", "--homedir", self.__home, "--version"],
        )

        # Verify results
        self.assertTrue(result.ok)
        self.assertIn(f"Home: {self.__home}", result.stdout)
        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.return_code)

    @mock.patch(
        "rhc_playbook_lib._keygen.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_run_invalid_gpg_command(self) -> None:
        """An invalid GPG command can be detected."""

        # Run the test
        result = _keygen._run_gpg_command(
            [
                "/usr/bin/gpg",
                "--batch",
                "--homedir",
                self.__home,
                "--invalid-command",
            ],
        )

        # Verify results
        self.assertFalse(result.ok)
        self.assertEqual("", result.stdout)
        self.assertIn("invalid option", result.stderr)
        self.assertEqual(2, result.return_code)

    @mock.patch(
        "rhc_playbook_lib._keygen.TEMPORARY_GPG_HOME_PARENT_DIRECTORY",
        "/tmp/",
    )
    def test_generate_gpg_key_pair(self) -> None:
        """A GPG key pair with a fingerprint can be generated."""

        # Run the test
        gpg_tmp_dir = _keygen._generate_keys()
        _keygen._export_key_pair(gpg_tmp_dir, self.__home)
        fingerprint = _keygen._get_fingerprint(gpg_tmp_dir, self.__home)

        # Verify results
        self.assertTrue(os.path.exists(gpg_tmp_dir))
        self.assertTrue(os.path.exists(gpg_tmp_dir + "/keygen"))
        self.assertTrue(os.path.exists(self.__home + "/key.public.gpg"))
        self.assertTrue(os.path.exists(self.__home + "/key.private.gpg"))
        self.assertTrue(os.path.exists(self.__home + "/key.fingerprint.txt"))
        self.assertEqual(
            fingerprint, open(self.__home + "/key.fingerprint.txt").read().strip()
        )

        shutil.rmtree(gpg_tmp_dir)


if __name__ == "__main__":
    main()
