"""
Thin wrapper around Discord's REST API (bot token authenticated).

Used by the Finalize Lambda to assign rank roles and post the weekly
leaderboard announcement embed.
"""
import time

import requests

from rankerbot.common.ssm import get_discord_bot_token

DISCORD_API_BASE = "https://discord.com/api/v10"
REQUEST_TIMEOUT = (3.05, 10)
MAX_RATE_LIMIT_RETRIES = 2
_session = requests.Session()


def _request(method: str, path: str, **kwargs) -> requests.Response:
    """Send an authenticated Discord API request with bounded 429 retries."""
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = f"Bot {get_discord_bot_token()}"
    url = f"{DISCORD_API_BASE}{path}"

    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        response = _session.request(
            method,
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        if response.status_code != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
            response.raise_for_status()
            return response

        try:
            retry_after = float(response.json().get("retry_after", 1))
        except (TypeError, ValueError, requests.JSONDecodeError):
            retry_after = 1
        time.sleep(max(retry_after, 0))

    raise RuntimeError("Discord request retry loop exited unexpectedly")

def assign_role(guild_id: str, user_id: str, role_id: str) -> None:
    """PUT /guilds/{guild.id}/members/{user.id}/roles/{role.id}"""
    _request("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")


def remove_role(guild_id: str, user_id: str, role_id: str) -> None:
    """DELETE /guilds/{guild.id}/members/{user.id}/roles/{role.id}"""
    _request("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")


def post_message(channel_id: str, embed: dict, nonce: str | None = None) -> dict:
    """Post an embed, optionally deduplicating retries with a Discord nonce."""
    payload = {
        "embeds": [embed],
        "allowed_mentions": {"parse": []},
    }
    if nonce:
        payload.update({"nonce": nonce, "enforce_nonce": True})

    response = _request("POST", f"/channels/{channel_id}/messages", json=payload)
    return response.json()
