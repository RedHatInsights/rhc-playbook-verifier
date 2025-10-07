import os
import pathlib
import subprocess

import pytest


PLAYBOOK_DIRECTORY = pathlib.Path(__file__).parents[2].absolute() / "data" / "playbooks"
UNSIGNED_PLAYBOOK_DIRECTORY = (
    pathlib.Path(__file__).parents[2].absolute() / "data" / "playbooks-unsigned"
)


@pytest.mark.parametrize(
    "filename",
    [
        "insights_remove",
        "document-from-hell",
        "unicode",
        "bugs",
    ],
)
def test_official_playbook(filename: str):
    """Test playbook signed by Red Hat's GPG key.

    In this test, the official playbooks are verified against the GPG key
    the application ships.
    """
    playbook_content: str = (PLAYBOOK_DIRECTORY / f"{filename}.yml").read_text()

    result = subprocess.run(
        [
            "rhc-playbook-verifier",
            "--playbook",
            f"{PLAYBOOK_DIRECTORY / filename}.yml",
            "--debug",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env={**os.environ, "LC_ALL": "C.UTF-8"},
    )

    # The playbooks may and may not include newline as EOF.
    if result.returncode != 0:
        print(result.stderr.strip())
    assert result.stdout.strip() == playbook_content.strip()


def test_playbook_with_invalid_signature_fails():
    """Verify that a playbook with an invalid base64 signature
    fails with a PreconditionError
    """
    result = subprocess.run(
        [
            "rhc-playbook-verifier",
            "--playbook",
            f"{UNSIGNED_PLAYBOOK_DIRECTORY}/invalid-signature.yml",
            "--debug",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env={**os.environ, "LC_ALL": "C.UTF-8"},
    )

    assert result.returncode != 0
    assert "rhc_playbook_lib.PreconditionError" in result.stderr
    assert "not a valid base64 string" in result.stderr
