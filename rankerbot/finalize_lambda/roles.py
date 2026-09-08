"""
Discord rank role management for the weekly Finalize Lambda.

Removes outdated rank roles (tracked via current_rank_role in DynamoDB)
before assigning the new #1/#2/#3 roles based on this week's standings.
"""


def remove_outdated_roles(ranked_users: list) -> None:
    """Remove each user's previously assigned rank role, if any."""
    # TODO: implement using discord_client.remove_role + dynamo.set_current_rank_role
    pass


def assign_rank_roles(ranked_users: list) -> None:
    """Assign the #1/#2/#3 rank roles to this week's top users."""
    # TODO: implement using discord_client.assign_role + dynamo.set_current_rank_role
    pass