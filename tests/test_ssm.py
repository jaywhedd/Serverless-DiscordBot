import unittest
from unittest.mock import Mock, patch

from rankerbot.common import ssm


class SsmTests(unittest.TestCase):
    def setUp(self):
        ssm._parameter_cache.clear()

    def tearDown(self):
        ssm._parameter_cache.clear()

    @patch("rankerbot.common.ssm._get_client")
    def test_parameter_values_are_cached_across_calls(self, get_client):
        client = Mock()
        client.get_parameter.return_value = {"Parameter": {"Value": "public-key"}}
        get_client.return_value = client

        first = ssm.get_parameter("/key", with_decryption=False)
        second = ssm.get_parameter("/key", with_decryption=False)

        self.assertEqual(first, "public-key")
        self.assertEqual(second, "public-key")
        client.get_parameter.assert_called_once_with(
            Name="/key", WithDecryption=False
        )

    @patch("rankerbot.common.ssm._get_client")
    def test_decryption_setting_uses_a_separate_cache_entry(self, get_client):
        client = Mock()
        client.get_parameter.side_effect = [
            {"Parameter": {"Value": "plain"}},
            {"Parameter": {"Value": "decrypted"}},
        ]
        get_client.return_value = client

        self.assertEqual(ssm.get_parameter("/key", False), "plain")
        self.assertEqual(ssm.get_parameter("/key", True), "decrypted")
        self.assertEqual(client.get_parameter.call_count, 2)


if __name__ == "__main__":
    unittest.main()