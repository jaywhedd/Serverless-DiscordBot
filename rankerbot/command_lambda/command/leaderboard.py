"""
/leaderboard

Read-only live view of the current top users this week. Queries the GSI
(guild_id, weekly_credits) — does NOT modify roles or credits.
"""

from rankerbot.common import dynamo
from rankerbot.common.config import TOP_N_RANKS


def handle_leaderboard(interaction: dict) -> dict:
    """Handle the /leaderboard slash command interaction."""
    guild_id = interaction.get("guild_id")
    if not guild_id:
        return {
            "type": 4,
            "data": {"content": "This command can only be used in a server."},
        }

    users = dynamo.query_top_users_by_weekly_credits(guild_id, TOP_N_RANKS)
    users = [user for user in users if int(user.get("weekly_credits", 0)) > 0]

    if not users:
        return {
            "type": 4,
            "data": {"content": "No weekly credits have been awarded yet."},
        }

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for position, user in enumerate(users, start=1):
        marker = medals[position - 1] if position <= len(medals) else f"**{position}.**"
        username = user.get("username") or user.get("user_id", "Unknown user")
        credits = int(user.get("weekly_credits", 0))
        lines.append(f"{marker} **{username}** — {credits} credits")

    return {
        "type": 4,
        "data": {
            "embeds": [
                {
                    "title": "Weekly Credits Leaderboard",
                    "description": "\n".join(lines),
                    "color": 0xF1C40F,
                }
            ]
        },
    }
