from unittest import main, TestCase

import rhc_playbook_lib as lib


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

        actual = lib.parse_playbook(raw)

        self.assertEqual(actual, expected)

    def test_integers(self) -> None:
        raw = '- {"numbers": [1, 2, 3, 0b1101]}'
        actual = lib.parse_playbook(raw)
        expected = [{"numbers": [1, 2, 3, 13]}]
        self.assertEqual(actual, expected)

    def test_floats(self) -> None:
        raw = '- {"numbers": [1.0, 2.0, 3.0]}'
        actual = lib.parse_playbook(raw)
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

        actual = lib.parse_playbook(raw)

        self.assertEqual(actual, expected)


if __name__ == "__main__":
    main()
