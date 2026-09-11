"""
/leaderboard

Read-only live view of the current top users this week. Queries the GSI
(guild_id, weekly_credits) — does NOT modify roles or credits.
"""


def handle_leaderboard(interaction: dict) -> dict:
    """Handle the /leaderboard slash command interaction."""
    # TODO: call dynamo.query_top_users_by_weekly_credits(...)
    # TODO: format results as a Discord embed
    # TODO: build and return the interaction response payload
    pass
