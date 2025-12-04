from unittest import main, TestCase

import rhc_playbook_lib as lib


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

        actual: dict = lib.clean_play(raw)
        self.assertEqual(actual, expected)

    def test_too_shallow_exclude(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/"}}

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "too deep or shallow",
        ):
            lib.clean_play(raw)

    def test_too_deep_exclude(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/vars/nested/key"}}

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "too deep or shallow",
        ):
            lib.clean_play(raw)

    def test_forbidden_exclude(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/name"}}

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "cannot be excluded",
        ):
            lib.clean_play(raw)

    def test_missing_simple(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/hosts"}}

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "Variable field '/hosts' is not present in the play.",
        ):
            lib.clean_play(raw)

    def test_missing_nested(self) -> None:
        raw = {"vars": {"insights_signature_exclude": "/vars/insights_signature"}}

        with self.assertRaisesRegex(
            lib.PreconditionError,
            "Variable field '/vars/insights_signature' is not present in the play.",
        ):
            lib.clean_play(raw)


if __name__ == "__main__":
    main()
