import unittest
from unittest.mock import Mock, call, patch

import requests

from rankerbot.common import discord_client


class DiscordClientTests(unittest.TestCase):
    @patch("rankerbot.common.discord_client.get_discord_bot_token", return_value="token")
    @patch.object(discord_client._session, "request")
    def test_assign_and_remove_role_use_expected_endpoints(self, request, _):
        response = Mock(status_code=204)
        request.return_value = response

        discord_client.assign_role("guild", "user", "role")
        discord_client.remove_role("guild", "user", "role")

        self.assertEqual(
            request.call_args_list,
            [
                call(
                    "PUT",
                    "https://discord.com/api/v10/guilds/guild/members/user/roles/role",
                    headers={"Authorization": "Bot token"},
                    timeout=discord_client.REQUEST_TIMEOUT,
                ),
                call(
                    "DELETE",
                    "https://discord.com/api/v10/guilds/guild/members/user/roles/role",
                    headers={"Authorization": "Bot token"},
                    timeout=discord_client.REQUEST_TIMEOUT,
                ),
            ],
        )
        self.assertEqual(response.raise_for_status.call_count, 2)

    @patch("rankerbot.common.discord_client.get_discord_bot_token", return_value="token")
    @patch.object(discord_client._session, "request")
    def test_post_message_uses_nonce_and_disables_mentions(self, request, _):
        response = Mock(status_code=200)
        response.json.return_value = {"id": "message-id"}
        request.return_value = response

        result = discord_client.post_message("channel", {"title": "Winners"}, "week")

        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["nonce"], "week")
        self.assertTrue(payload["enforce_nonce"])
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        self.assertEqual(result, {"id": "message-id"})

    @patch("rankerbot.common.discord_client.time.sleep")
    @patch("rankerbot.common.discord_client.get_discord_bot_token", return_value="token")
    @patch.object(discord_client._session, "request")
    def test_retries_rate_limit_using_discord_retry_after(self, request, _, sleep):
        limited = Mock(status_code=429)
        limited.json.return_value = {"retry_after": 0.25}
        success = Mock(status_code=204)
        request.side_effect = [limited, success]

        discord_client.assign_role("guild", "user", "role")

        sleep.assert_called_once_with(0.25)
        self.assertEqual(request.call_count, 2)
        success.raise_for_status.assert_called_once()

    @patch("rankerbot.common.discord_client.get_discord_bot_token", return_value="token")
    @patch.object(discord_client._session, "request")
    def test_http_errors_are_raised(self, request, _):
        response = Mock(status_code=403)
        response.raise_for_status.side_effect = requests.HTTPError("forbidden")
        request.return_value = response

        with self.assertRaises(requests.HTTPError):
            discord_client.assign_role("guild", "user", "role")


if __name__ == "__main__":
    unittest.main()