"""
Discord rank role management for the weekly Finalize Lambda.

Removes outdated rank roles (tracked via current_rank_role in DynamoDB)
before assigning the new #1/#2/#3 roles based on this week's standings.
"""

from rankerbot.common import discord_client, dynamo
from rankerbot.common.config import GUILD_ID, RANK_ROLE_IDS


def remove_outdated_roles(users: list) -> None:
    """Remove each user's previously assigned rank role, if any."""
    for user in users:
        user_id = user.get("user_id")
        role_id = user.get("current_rank_role")
        if not user_id or not role_id:
            continue

        discord_client.remove_role(GUILD_ID, user_id, role_id)
        dynamo.clear_current_rank_role(user_id)


def assign_rank_roles(ranked_users: list) -> None:
    """Assign the #1/#2/#3 rank roles to this week's top users."""
    for user, role_id in zip(ranked_users, RANK_ROLE_IDS):
        user_id = user.get("user_id")
        if not user_id:
            continue

        discord_client.assign_role(GUILD_ID, user_id, role_id)
        dynamo.set_current_rank_role(user_id, role_id)