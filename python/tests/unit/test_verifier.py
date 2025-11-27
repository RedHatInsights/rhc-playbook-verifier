import argparse
import pathlib

from unittest import main, mock, TestCase

import rhc_playbook_verifier.app as verifier


PLAYBOOKS = pathlib.Path(__file__).parents[3].absolute() / "data" / "playbooks"


class TestVerifier(TestCase):
    @mock.patch(
        "rhc_playbook_verifier.app.argparse.ArgumentParser.parse_args",
        mock.MagicMock(
            return_value=argparse.Namespace(
                key=None,
                stdin=None,
                playbook=f"{PLAYBOOKS}/document-from-hell.yml",
                revocation_list=None,
            )
        ),
    )
    def test_run_verifier(self) -> None:
        verifier.run()


if __name__ == "__main__":
    main()
