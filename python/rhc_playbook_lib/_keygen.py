import argparse
import logging
import os
import pathlib
import re
import subprocess
import sys
import textwrap
import traceback
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Generator

import rhc_playbook_lib as lib
from rhc_playbook_lib.crypto import GPGCommandResult

logger = logging.getLogger(__name__)


TEMPORARY_GPG_HOME_PARENT_DIRECTORY_PREFIX = "rhc-playbook-verifier-gpg-"


def _run_gpg_command(command: list[str], fingerprint: bool = False) -> GPGCommandResult:
    """Run a GPG command in a specific directory.

    :param command: The command to be executed.
    :param fingerprint: Optional flag to get the fingerprint from the output.
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"LC_ALL": "C.UTF-8"},
        text=fingerprint,
    )
    stdout, stderr = process.communicate()

    result = GPGCommandResult(
        ok=process.returncode == 0,
        return_code=process.returncode,
        stdout=stdout.decode("utf-8") if not fingerprint else stdout,
        stderr=stderr.decode("utf-8") if not fingerprint else stderr,
        _command=None,
    )

    if result.ok:
        logger.debug(f"GPG command {command}: ok.")
    else:
        logger.error(f"GPG command {command} returned non-zero code: {result}.")

    return result


@contextmanager
def _generate_keys() -> Generator[str, None, None]:
    """Generate GPG keys into a temporary directory.

    Yield the path to the directory into which keys are generated.
    """
    with TemporaryDirectory(
        prefix=TEMPORARY_GPG_HOME_PARENT_DIRECTORY_PREFIX
    ) as gpg_tmp_dir:
        logger.debug(f"Generating GPG keys into {gpg_tmp_dir}.")
        instructions_file = pathlib.Path(gpg_tmp_dir) / "keygen"
        instructions_file.write_text(
            textwrap.dedent(
                """
                Key-Type: EDDSA
                Key-Curve: ed25519
                Subkey-Type: ECDH
                Subkey-Curve: cv25519
                Name-Real: rhc-playbook-verifier test
                Expire-Date: 0
                %no-protection
                %commit
                """
            ).strip()
        )
        logger.debug(
            f"Keys generation instructions written to a file {instructions_file}."
        )
        _run_gpg_command(
            [
                "/usr/bin/gpg",
                "--batch",
                "--homedir",
                gpg_tmp_dir,
                "--generate-key",
                f"{instructions_file}",
            ]
        )
        yield gpg_tmp_dir


def _export_key_pair(gpg_tmp_dir: str, keys_path: str) -> None:
    """
    Export the generated key pair to the `keys_path` directory.

    :param gpg_tmp_dir: The GPG home directory where the key pair was generated.
    :param keys_path: The directory where the key pair should be exported.
    """
    _run_gpg_command(
        [
            "/usr/bin/gpg",
            "--homedir",
            gpg_tmp_dir,
            "--export",
            "--armor",
            "--yes",
            "--output",
            f"{keys_path}/key.public.gpg",
        ]
    )
    logger.debug(f"GPG public key written to a file {keys_path}/key.public.gpg.")

    _run_gpg_command(
        [
            "/usr/bin/gpg",
            "--homedir",
            gpg_tmp_dir,
            "--export-secret-keys",
            "--armor",
            "--yes",
            "--output",
            f"{keys_path}/key.private.gpg",
        ]
    )
    logger.debug(f"GPG private key written to a file {keys_path}/key.private.gpg.")


def _get_fingerprint(gpg_tmp_dir: str) -> str:
    """
    Get the fingerprint of the generated key pair.

    :param gpg_tmp_dir: The GPG home directory where the key pair was generated.
    """
    result = _run_gpg_command(
        [
            "/usr/bin/gpg",
            "--homedir",
            gpg_tmp_dir,
            "--fingerprint",
            "rhc-playbook-verifier test",
        ],
        fingerprint=True,
    )
    match = re.search(r"^\s+([A-F0-9\s]+)", result.stdout, re.MULTILINE)
    gpg_fingerprint = match.group(1).strip() if match else ""
    return gpg_fingerprint


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Display logs",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        metavar="DIR",
        help="Directory to store the key pair (default: current working directory)",
    )
    args = parser.parse_args()

    # Generate a keypair, export them to args.directory, and get their fingerprint
    with _generate_keys() as gpg_tmp_dir:
        os.makedirs(args.directory, exist_ok=True)
        _export_key_pair(gpg_tmp_dir, str(args.directory))
        gpg_fingerprint = _get_fingerprint(gpg_tmp_dir)

    with open(f"{args.directory}/key.fingerprint.txt", "w") as fingerprint_file:
        fingerprint_file.write(gpg_fingerprint)
        logger.debug(f"GPG fingerprint written to a file {fingerprint_file.name}")


def main() -> None:
    debug: bool = "--debug" in sys.argv
    lib._configure_logging(debug=debug)

    try:
        run()
        print(
            "GPG keys were generated to 'key.public.gpg', 'key.private.gpg', 'key.fingerprint.txt'."
        )
    except Exception as exc:
        logger.critical("Unhandled exception occured, aborting.")
        if debug:
            traceback.print_exc()
        else:
            print(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
