import unittest

from relaylab.jsonutil import AgentProtocolError, extract_json_object


class JsonUtilTests(unittest.TestCase):
    def test_parses_plain_object(self) -> None:
        self.assertEqual(extract_json_object('{"ok": true}'), {"ok": True})

    def test_parses_json_fence(self) -> None:
        self.assertEqual(
            extract_json_object('''```json
{"ok": true}
```'''),
            {"ok": True},
        )

    def test_rejects_non_object(self) -> None:
        with self.assertRaises(AgentProtocolError):
            extract_json_object('["nope"]')


if __name__ == "__main__":
    unittest.main()
