"""
Thin wrapper around Discord's REST API (bot token authenticated).

Used by the Finalize Lambda to assign rank roles and post the weekly
leaderboard announcement embed.
"""


def assign_role(guild_id: str, user_id: str, role_id: str) -> None:
    """PUT /guilds/{guild.id}/members/{user.id}/roles/{role.id}"""
    # TODO: implement using requests + bot token from ssm.get_discord_bot_token()
    pass


def remove_role(guild_id: str, user_id: str, role_id: str) -> None:
    """DELETE /guilds/{guild.id}/members/{user.id}/roles/{role.id}"""
    # TODO: implement
    pass


def post_message(channel_id: str, embed: dict) -> None:
    """POST /channels/{channel.id}/messages with an embed payload."""
    # TODO: implement
    pass
