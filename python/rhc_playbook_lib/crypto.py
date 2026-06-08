import logging
import subprocess
from contextlib import contextmanager
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from typing import Generator

from rhc_playbook_lib.constants import TEMPORARY_DIRECTORY_PREFIX

logger = logging.getLogger(__name__)


@contextmanager
def temp_gpg_dir(key: Path) -> Generator[Path, None, None]:
    """Create a temporary directory, import the given GPG key into it, and yield the directory.

    GPG commands can be run against this directory, with the ``--homedir`` flag. On teardown, delete
    the GPG socket in the directory, then delete the directory.
    """
    with TemporaryDirectory(prefix=TEMPORARY_DIRECTORY_PREFIX) as dir:
        subprocess.run(
            ["/usr/bin/gpg", "--homedir", dir, "--import", str(key.absolute())],
            check=True,
            capture_output=True,
        )
        try:
            yield Path(dir)
        finally:
            # `gpgconf --kill` was added in GnuPG 2.1.0-beta2 and `--kill all` exists since 2.1.18.
            #
            # * 2.1.0b1: commit 7c03c8cc65e68f1d77a5a5a497025191fe5df5e9 in GPG's repository.
            # * 2.1.18: https://lists.gnupg.org/pipermail/gnupg-announce/2017q1/000401.html
            #
            # The following RHEL images ship with the following packages:
            #
            # * rhel-server-7.9-update-12-x86_64-kvm.qcow2  gnupg2-2.0.22-5.el7_5.x86_64
            # * rhel-8.6-x86_64-kvm.qcow2                   gnupg2-2.2.20-2.el8.x86_64
            # * rhel-baseos-9.0-update-4-x86_64-kvm.qcow2   gnupg2-2.3.3-2.el9_0.x86_64
            #
            # ...which means this command should work on RHEL 8 and above.
            subprocess.run(
                ["/usr/bin/gpgconf", "--kill", "all"],
                env={"GNUPGHOME": str(dir)},
                check=True,
                capture_output=True,
            )


def verify_gpg_signed_file(file: Path, signature: Path, key: Path) -> CompletedProcess:
    """
    Verify a file that was signed using GPG.

    :param file: A path to the signed file.
    :param signature: A path to the detached signature.
    :param key: Path to the public GPG key on the filesystem to check against.

    :returns: Evaluated GPG command.
    """
    if not file.is_file():
        logger.debug(f"Cannot verify signature of '{file}', file does not exist")
        raise FileNotFoundError(f"File '{file}' not found")

    if not signature.is_file():
        logger.debug(
            f"Cannot verify signature of '{file!s}', signature '{signature!s}' does not exist."
        )
        raise FileNotFoundError(
            f"Signature '{signature!s}' of file '{file!s}' not found."
        )

    with temp_gpg_dir(key) as dir:
        logger.debug(f"Starting GPG verification process for '{file}'.")
        return subprocess.run(
            ["/usr/bin/gpg", "--homedir", dir, "--verify", signature, file],
            check=True,
            capture_output=True,
        )


def sign_file(file: Path, key: Path) -> CompletedProcess:
    """
    Sign a file using GPG.

    :param file: File to be signed.
    :param key: Path to the private GPG key on the filesystem.

    :return: Evaluated GPG command.
    """
    if not file.is_file():
        logger.debug(f"Cannot sign file '{file}', file does not exist.")
        raise FileNotFoundError(f"File '{file}' not found")

    if not key.is_file():
        logger.debug(f"Cannot sign file '{file}', key does not exist.")
        raise FileNotFoundError(f"Key '{key}' not found")

    with temp_gpg_dir(key) as dir:
        logger.debug(f"Starting GPG signing process for '{file}'.")
        return subprocess.run(
            ["/usr/bin/gpg", "--homedir", dir, "--detach-sign", "--armor", file],
            check=True,
            capture_output=True,
        )
