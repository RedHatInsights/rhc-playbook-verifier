import pathlib

from unittest import main, TestCase

import rhc_playbook_lib as lib

PLAYBOOKS = pathlib.Path(__file__).parents[4].absolute() / "data" / "playbooks"


class TestCreatePlayDigest(TestCase):
    def __create_play_digest(self, file: str) -> None:
        raw: bytes = (PLAYBOOKS / f"{file}.serialized.bin").read_bytes()
        expected: bytes = (PLAYBOOKS / f"{file}.digest.bin").read_bytes()

        actual: bytes = lib.create_play_digest(raw)

        self.assertEqual(actual, expected)

    def test_all(self) -> None:
        files = ["insights_remove", "document-from-hell"]

        for file in files:
            self.__create_play_digest(file)


if __name__ == "__main__":
    main()
