import pathlib

from unittest import main, mock, TestCase

import rhc_playbook_lib as lib

DATA = pathlib.Path(__file__).parents[4].absolute() / "data"
GPG_KEY = (DATA / "public.gpg").read_bytes()
PLAYBOOKS = pathlib.Path(__file__).parents[4].absolute() / "data" / "playbooks"


class TestVerifyPlayBook(TestCase):
    @mock.patch(
        "rhc_playbook_lib.crypto.verify_gpg_signed_file",
        return_value=mock.MagicMock(ok=False),
    )
    def test_requires_signature(self, _verify: mock.MagicMock) -> None:
        raw = {"name": "bad playbook", "tasks": [{"name": "a task"}]}

        # lib.verify_play(play=raw, gpg_key=b"")

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "does not contain a signature",
        ):
            lib.verify_play(play=raw, gpg_key=b"")

    @mock.patch(
        "rhc_playbook_lib.crypto.verify_gpg_signed_file",
        return_value=mock.MagicMock(ok=False),
    )
    def test_requires_signature_exclude(self, _verify: mock.MagicMock) -> None:
        raw = {
            "name": "bad playbook",
            "vars": {"insights_signature": ""},
            "tasks": [{"name": "a task"}],
        }

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "does not have the key 'vars/insights_signature_exclude'",
        ):
            lib.verify_play(play=raw, gpg_key=b"")

    def __test_file(self, file: str) -> None:
        raw: str = (PLAYBOOKS / f"{file}.yml").read_text()
        expected: bytes = (PLAYBOOKS / f"{file}.digest.bin").read_bytes()

        parsed_play: dict = lib.parse_playbook(raw)[0]
        digest: bytes = lib.verify_play(parsed_play, gpg_key=GPG_KEY)

        self.assertEqual(digest, expected)

    def test_files(self) -> None:
        files = ["insights_remove", "document-from-hell"]

        for file in files:
            self.__test_file(file)

    def test_no_signature(self) -> None:
        parsed_play = {
            "name": "bad playbook",
            "hosts": "localhost",
            "vars": {
                "insights_signature_exclude": "/hosts,/vars/insights_signature/",
            },
            "tasks": [],
        }

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "does not contain a signature",
        ):
            lib.verify_play(parsed_play, gpg_key=GPG_KEY)

    def test_invalid_signature(self) -> None:
        parsed_play = {
            "name": "bad playbook",
            "hosts": "localhost",
            "vars": {
                "insights_signature_exclude": "/hosts,/vars/insights_signature/",
                "insights_signature": "SIGNATURE",
            },
            "tasks": [],
        }

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "not a valid base64 string",
        ):
            lib.verify_play(parsed_play, gpg_key=GPG_KEY)


if __name__ == "__main__":
    main()
