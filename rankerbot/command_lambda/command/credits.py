"""
/credits @user

GetItem lookup of a user's current weekly_credits. Defaults to the calling
user if no @user is given.
"""

from rankerbot.common import dynamo


def _target_user(interaction: dict) -> tuple[str | None, str | None]:
    """Resolve the optional target user, defaulting to the command caller."""
    options = interaction.get("data", {}).get("options", [])
    selected_user_id = next(
        (option.get("value") for option in options if option.get("name") == "user"),
        None,
    )

    if selected_user_id:
        user = (
            interaction.get("data", {})
            .get("resolved", {})
            .get("users", {})
            .get(selected_user_id, {})
        )
        username = user.get("global_name") or user.get("username") or selected_user_id
        return selected_user_id, username

    caller = interaction.get("member", {}).get("user", {})
    user_id = caller.get("id")
    username = caller.get("global_name") or caller.get("username") or user_id
    return user_id, username


def handle_credits(interaction: dict) -> dict:
    """Handle the /credits slash command interaction."""
    user_id, username = _target_user(interaction)
    if not user_id:
        return {
            "type": 4,
            "data": {"content": "Could not identify that user.", "flags": 64},
        }

    item = dynamo.get_user_credits(user_id) or {}
    weekly_credits = int(item.get("weekly_credits", 0))

    return {
        "type": 4,
        "data": {
            "content": f"💳 **{username}** has **{weekly_credits} weekly credits**."
        },
    }
