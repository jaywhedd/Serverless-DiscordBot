"""
Weekly leaderboard announcement for the Finalize Lambda.

Builds a Discord embed summarizing final weekly standings and posts it
to the hardcoded #leaderboard channel, tagging the top users.
"""

from rankerbot.common import discord_client
from rankerbot.common.config import LEADERBOARD_CHANNEL_ID


def build_announcement_embed(ranked_users: list) -> dict:
    """Format final weekly standings as a Discord embed payload."""
    medals = ["🥇", "🥈", "🥉"]
    if ranked_users:
        lines = []
        for position, user in enumerate(ranked_users):
            username = user.get("username") or user.get("user_id", "Unknown user")
            credits = int(user.get("weekly_credits", 0))
            lines.append(f"{medals[position]} **{username}** — {credits} credits")
        description = "\n".join(lines)
    else:
        description = "No weekly credits were awarded this week."

    return {
        "title": "🏆 Final Weekly Leaderboard",
        "description": description,
        "color": 0xF1C40F,
        "footer": {"text": "Rank roles remain until the next weekly leaderboard."},
    }


def post_announcement(embed: dict, week_id: str) -> dict:
    """Post the announcement embed to the #leaderboard channel."""
    return discord_client.post_message(
        LEADERBOARD_CHANNEL_ID,
        embed,
        nonce=f"rankerbot-weekly-{week_id}",
    )