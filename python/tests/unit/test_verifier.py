import argparse
import pathlib
import unittest.mock

import rhc_playbook_verifier.app as verifier


PLAYBOOKS = pathlib.Path(__file__).parents[3].absolute() / "data" / "playbooks"


class TestRun:
    @unittest.mock.patch(
        "rhc_playbook_verifier.app.argparse.ArgumentParser.parse_args",
        unittest.mock.MagicMock(
            return_value=argparse.Namespace(
                key=None,
                stdin=None,
                playbook=f"{PLAYBOOKS}/document-from-hell.yml",
                revocation_list=None,
            )
        ),
    )
    def test_ok(self) -> None:
        verifier.run()
