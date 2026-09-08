"""
Weekly leaderboard announcement for the Finalize Lambda.

Builds a Discord embed summarizing final weekly standings and posts it
to the hardcoded #leaderboard channel, tagging the top users.
"""


def build_announcement_embed(ranked_users: list) -> dict:
    """Format final weekly standings as a Discord embed payload."""
    # TODO: implement
    pass


def post_announcement(embed: dict) -> None:
    """Post the announcement embed to the #leaderboard channel."""
    # TODO: implement using discord_client.post_message + config.LEADERBOARD_CHANNEL_ID
    pass