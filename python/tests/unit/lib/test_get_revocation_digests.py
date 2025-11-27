import pathlib

from unittest import main, mock, TestCase

import rhc_playbook_lib as lib

DATA = pathlib.Path(__file__).parents[4].absolute() / "data"
GPG_KEY = (DATA / "public.gpg").read_bytes()
REVOKED = (DATA / "revoked_playbooks.yml").read_text()


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

        actual: set[bytes] = lib.get_revocation_digests(
            playbook=REVOKED, gpg_key=GPG_KEY
        )

        self.assertEqual(actual, expected)

    @mock.patch(
        "rhc_playbook_lib.crypto.verify_gpg_signed_file",
        return_value=mock.MagicMock(ok=False),
    )
    def test_bad_signature(self, _: mock.MagicMock) -> None:
        """Test that validation failure raises an exception."""
        with self.assertRaisesRegex(
            lib.GPGValidationError,
            "Play digest does not match its signature",
        ):
            lib.get_revocation_digests(playbook=REVOKED, gpg_key=GPG_KEY)


if __name__ == "__main__":
    main()
