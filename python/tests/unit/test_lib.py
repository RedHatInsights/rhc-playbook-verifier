import pathlib
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import rhc_playbook_lib
from rhc_playbook_lib import GPGValidationError, PreconditionError, _keygen

DATA = pathlib.Path(__file__).parents[3].absolute() / "data"
GPG_KEY = (DATA / "public.gpg").read_bytes()
REVOKED = (DATA / "revoked_playbooks.yml").read_text()
PLAYBOOKS = pathlib.Path(__file__).parents[3].absolute() / "data" / "playbooks"


class TestParsePlaybook(TestCase):
    """The reference verifier used YAML 1.2.

    PyYAML seems to be using YAML 1.1 by default, so we have to ensure we parse it correctly.
    """

    def test_all(self) -> None:
        """Test that all plays loaded if present."""
        raw = "\n".join(
            [
                "---",
                "- name: first dictionary",
                "  key: value",
                "- name: second dictionary",
                "  key: value",
            ]
        )
        expected = [
            {"name": "first dictionary", "key": "value"},
            {"name": "second dictionary", "key": "value"},
        ]
        actual = rhc_playbook_lib.parse_playbook(raw)
        self.assertEqual(actual, expected)

    def test_integers(self) -> None:
        raw = '- {"numbers": [1, 2, 3, 0b1101]}'
        actual = rhc_playbook_lib.parse_playbook(raw)
        expected = [{"numbers": [1, 2, 3, 13]}]
        self.assertEqual(actual, expected)

    def test_floats(self) -> None:
        raw = '- {"numbers": [1.0, 2.0, 3.0]}'
        actual = rhc_playbook_lib.parse_playbook(raw)
        expected = [{"numbers": [1.0, 2.0, 3.0]}]
        self.assertEqual(actual, expected)

    def test_true(self) -> None:
        raw = "- bool: [true, True, TRUE]\n  string: [y, yes, Yes, YES, on, On, ON]"
        expected = [
            {
                "bool": [True, True, True],
                "string": ["y", "yes", "Yes", "YES", "on", "On", "ON"],
            }
        ]
        actual = rhc_playbook_lib.parse_playbook(raw)
        self.assertEqual(actual, expected)


class TestCleanPlaybook(TestCase):
    def test_ok(self) -> None:
        raw = {
            "name": "good playbook",
            "hosts": "localhost",
            "vars": {
                "insights_signature_exclude": "/hosts,/vars/insights_signature/",
                "insights_signature": b"data",
            },
            "tasks": [],
        }
        expected = {
            "name": "good playbook",
            "vars": {"insights_signature_exclude": "/hosts,/vars/insights_signature/"},
            "tasks": [],
        }
        actual: dict = rhc_playbook_lib.clean_play(raw)
        self.assertEqual(actual, expected)

    def test_too_shallow_exclude(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/"}}
        with self.assertRaisesRegex(PreconditionError, "too deep or shallow"):
            rhc_playbook_lib.clean_play(raw)

    def test_too_deep_exclude(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/vars/nested/key"}}
        with self.assertRaisesRegex(PreconditionError, "too deep or shallow"):
            rhc_playbook_lib.clean_play(raw)

    def test_forbidden_exclude(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/name"}}
        with self.assertRaisesRegex(PreconditionError, "cannot be excluded"):
            rhc_playbook_lib.clean_play(raw)

    def test_missing_simple(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/hosts"}}
        with self.assertRaisesRegex(
            PreconditionError, "Variable field '/hosts' is not present in the play."
        ):
            rhc_playbook_lib.clean_play(raw)

    def test_missing_nested(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/vars/insights_signature"}}
        with self.assertRaisesRegex(
            PreconditionError,
            "Variable field '/vars/insights_signature' is not present in the play.",
        ):
            rhc_playbook_lib.clean_play(raw)


class TestCreatePlayDigest(TestCase):
    def test_ok(self) -> None:
        for file in ("insights_remove", "document-from-hell"):
            with self.subTest(file=file):
                raw: bytes = (PLAYBOOKS / f"{file}.serialized.bin").read_bytes()
                actual: bytes = rhc_playbook_lib.create_play_digest(raw)
                expected: bytes = (PLAYBOOKS / f"{file}.digest.bin").read_bytes()
                self.assertEqual(actual, expected)


class TestVerifyPlay(TestCase):
    def test_requires_signature(self) -> None:
        raw = {
            "name": "bad playbook",
            "tasks": [{"name": "a task"}],
        }
        with self.assertRaisesRegex(PreconditionError, "does not contain a signature"):
            rhc_playbook_lib.verify_play(play=raw, gpg_key=b"")

    def test_requires_signature_exclude(self) -> None:
        raw = {
            "name": "bad playbook",
            "vars": {"insights_signature": ""},
            "tasks": [{"name": "a task"}],
        }
        with self.assertRaisesRegex(
            PreconditionError, "does not have the key 'vars/insights_signature_exclude'"
        ):
            rhc_playbook_lib.verify_play(play=raw, gpg_key=b"")


class TestVerifyPlaybook(TestCase):
    def test_ok(self) -> None:
        for file in ("insights_remove", "document-from-hell"):
            with self.subTest(file=file):
                raw: str = (PLAYBOOKS / f"{file}.yml").read_text()
                parsed_play: dict = rhc_playbook_lib.parse_playbook(raw)[0]
                digest: bytes = rhc_playbook_lib.verify_play(
                    parsed_play, gpg_key=GPG_KEY
                )
                expected: bytes = (PLAYBOOKS / f"{file}.digest.bin").read_bytes()
                self.assertEqual(digest, expected)

    def test_no_signature(self) -> None:
        parsed_play = {
            "name": "bad playbook",
            "hosts": "localhost",
            "vars": {
                "insights_signature_exclude": "/hosts,/vars/insights_signature/",
            },
            "tasks": [],
        }
        with self.assertRaisesRegex(PreconditionError, "does not contain a signature"):
            rhc_playbook_lib.verify_play(parsed_play, gpg_key=GPG_KEY)

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
        with self.assertRaisesRegex(PreconditionError, "not a valid base64 string"):
            rhc_playbook_lib.verify_play(parsed_play, gpg_key=GPG_KEY)


class TestGetRevocationDigests(TestCase):
    def test_ok(self) -> None:
        expected = {
            bytes(
                bytearray.fromhex(
                    "8ddc7c9fb264aa24d7b3536ecf00272ca143c2ddb14a499cdefab045f3403e9b"
                )
            ),
            bytes(
                bytearray.fromhex(
                    "40a6e9af448208759bc4ef59b6c678227aae9b3f6291c74a4a8767eefc0a401f"
                )
            ),
        }
        actual: set[bytes] = rhc_playbook_lib.get_revocation_digests(
            playbook=REVOKED, gpg_key=GPG_KEY
        )
        self.assertEqual(actual, expected)

    def test_bad_signature(self) -> None:
        """Test that validation failure raises an exception."""
        with ExitStack() as stack:
            gpg_tmp_dir = stack.enter_context(_keygen._generate_keys())
            export_dir = stack.enter_context(TemporaryDirectory())
            _keygen._export_key_pair(gpg_tmp_dir, export_dir)
            handle = stack.enter_context(
                (Path(export_dir) / "key.public.gpg").open("rb")
            )
            invalid_gpg_key = handle.read()
        with self.assertRaisesRegex(
            GPGValidationError, "Play digest does not match its signature"
        ):
            rhc_playbook_lib.get_revocation_digests(
                playbook=REVOKED, gpg_key=invalid_gpg_key
            )
