from unittest import TestCase

import yaml
from rhc_playbook_lib.serialization import CustomYamlDumper, Serializer


class TestPlaybookSerializer(TestCase):
    def test_list(self) -> None:
        source = ["a", "b"]
        result = Serializer._list(source)
        expected = "['a', 'b']"
        self.assertEqual(result, expected)

    def test_dict_empty(self) -> None:
        source: dict = {}
        result = Serializer._dict(source)
        expected = "ordereddict()"
        self.assertEqual(result, expected)

    def test_dict_empty_value(self) -> None:
        source = {"a": None}
        result = Serializer._dict(source)
        expected = "ordereddict([('a', None)])"
        self.assertEqual(result, expected)

    def test_dict_single(self) -> None:
        source = {"a": "a"}
        result = Serializer._dict(source)
        expected = "ordereddict([('a', 'a')])"
        self.assertEqual(result, expected)

    def test_dict_list(self) -> None:
        source = {"a": ["a1", "a2"]}
        result = Serializer._dict(source)
        expected = "ordereddict([('a', ['a1', 'a2'])])"
        self.assertEqual(result, expected)

    def test_dict_mixed(self) -> None:
        source = {"a": "a", "b": ["b1", "b2"]}
        result = Serializer._dict(source)
        expected = "ordereddict([('a', 'a'), ('b', ['b1', 'b2'])])"
        self.assertEqual(result, expected)

    def test_dict_multiple(self) -> None:
        source = {"a": "a", "b": "b"}
        result = Serializer._dict(source)
        expected = "ordereddict([('a', 'a'), ('b', 'b')])"
        self.assertEqual(result, expected)

    def test_numbers(self) -> None:
        source = {"integer": 37, "float": 17.93233901}
        result = Serializer._dict(source)
        expected = "ordereddict([('integer', 37), ('float', 17.93233901)])"
        self.assertEqual(result, expected)

    def test_strings(self) -> None:
        for source, expected in (
            ("no quote", "'no quote'"),
            ("single'quote", '''"single'quote"'''),
            ('double"quote', """'double"quote'"""),
            ("both\"'quotes", r"""'both"\'quotes'"""),
            ("\\backslash", "'\\\\backslash'"),
            ("new\nline", "'new\\nline'"),
            ("tab\tchar", "'tab\\tchar'"),
        ):
            with self.subTest(source):
                result = Serializer._str(source)
                self.assertEqual(result, expected)

    def test_strings_unicode(self) -> None:
        # https://docs.astral.sh/ruff/rules/invalid-character-zero-width-space/
        for desc, source, expected in (
            ("zero-width space", "zw​space", "'zw\\u200bspace'"),  # noqa:PLE2515
            ("zero-width non-joiner", "zw‌nonjoiner", "'zw\\u200cnonjoiner'"),
            ("zero-width joiner", "👨🏼‍🚀", "'👨🏼\\u200d🚀'"),
        ):
            with self.subTest(desc):
                result = Serializer._str(source)
                self.assertEqual(result, expected)


class TestYamlDumper(TestCase):
    def test_represent_none(self) -> None:
        """Test that None is represented as an empty string in YAML."""
        yaml.Dumper.add_representer(type(None), CustomYamlDumper.represent_none)
        source = {"key": None}
        result: str = yaml.dump(source, Dumper=CustomYamlDumper)
        expected: str = "key:\n"
        self.assertEqual(result, expected)
