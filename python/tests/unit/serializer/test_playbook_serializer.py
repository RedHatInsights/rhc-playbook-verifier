from unittest import main, TestCase
from rhc_playbook_lib import serialization


class TestPlaybookSerializer(TestCase):
    def test_list(self) -> None:
        source = ["a", "b"]
        result = serialization.Serializer._list(source)
        expected = "['a', 'b']"
        self.assertEqual(result, expected)

    def test_dict_empty(self) -> None:
        source: dict = {}
        result = serialization.Serializer._dict(source)
        expected = "ordereddict()"
        self.assertEqual(result, expected)

    def test_dict_empty_value(self) -> None:
        source = {"a": None}
        result = serialization.Serializer._dict(source)
        expected = "ordereddict([('a', None)])"
        self.assertEqual(result, expected)

    def test_dict_single(self) -> None:
        source = {"a": "a"}
        result = serialization.Serializer._dict(source)
        expected = "ordereddict([('a', 'a')])"
        self.assertEqual(result, expected)

    def test_dict_list(self) -> None:
        source = {"a": ["a1", "a2"]}
        result = serialization.Serializer._dict(source)
        expected = "ordereddict([('a', ['a1', 'a2'])])"
        self.assertEqual(result, expected)

    def test_dict_mixed(self) -> None:
        source = {"a": "a", "b": ["b1", "b2"]}
        result = serialization.Serializer._dict(source)
        expected = "ordereddict([('a', 'a'), ('b', ['b1', 'b2'])])"
        self.assertEqual(result, expected)

    def test_dict_multiple(self) -> None:
        source = {"a": "a", "b": "b"}
        result = serialization.Serializer._dict(source)
        expected = "ordereddict([('a', 'a'), ('b', 'b')])"
        self.assertEqual(result, expected)

    def test_numbers(self) -> None:
        source = {"integer": 37, "float": 17.93233901}
        result = serialization.Serializer._dict(source)
        expected = "ordereddict([('integer', 37), ('float', 17.93233901)])"
        self.assertEqual(result, expected)

    def __test_strings(self, source: str, expected: str) -> None:
        result = serialization.Serializer._str(source)
        self.assertEqual(result, expected)

    def test_strings(self) -> None:
        input = [
            ("no quote", "'no quote'"),
            ("single'quote", '''"single'quote"'''),
            ('double"quote', """'double"quote'"""),
            ("both\"'quotes", r"""'both"\'quotes'"""),
            ("\\backslash", "'\\\\backslash'"),
            ("new\nline", "'new\\nline'"),
            ("tab\tchar", "'tab\\tchar'"),
        ]

        for value in input:
            self.__test_strings(*value)

    def __test_strings_unicode(self, source: str, expected: str) -> None:
        result = serialization.Serializer._str(source)
        self.assertEqual(result, expected)

    def test_strings_unicode(self) -> None:
        input = [
            ("zw​space", "'zw\\u200bspace'"),
            ("zw‌nonjoiner", "'zw\\u200cnonjoiner'"),
            ("👨🏼‍🚀", "'👨🏼\\u200d🚀'"),
        ]

        for value in input:
            self.__test_strings_unicode(*value)


if __name__ == "__main__":
    main()
