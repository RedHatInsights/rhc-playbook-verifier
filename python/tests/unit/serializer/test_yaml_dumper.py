import yaml

from unittest import main, TestCase
from rhc_playbook_lib import serialization


class TestYamlDumper(TestCase):
    def test_represent_none(self) -> None:
        """Test that None is represented as an empty string in YAML."""
        yaml.Dumper.add_representer(
            type(None), serialization.CustomYamlDumper.represent_none
        )

        actual: str = yaml.dump({"key": None}, Dumper=serialization.CustomYamlDumper)
        expected: str = "key:\n"

        self.assertEqual(actual, expected)


if __name__ == "__main__":
    main()
