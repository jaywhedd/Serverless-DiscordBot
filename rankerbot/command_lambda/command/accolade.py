"""
/accolade @user category

Looks up the category's point value from config.ACCOLADE_CATEGORIES,
validates that the category has not already been awarded today, and atomically
adds its points to the target user's weekly_credits in DynamoDB.
"""

from datetime import datetime, timezone

from rankerbot.common import dynamo
from rankerbot.common.config import ACCOLADE_CATEGORIES


def _option_values(interaction: dict) -> dict:
    """Return slash-command options keyed by their registered names."""
    return {
        option.get("name"): option.get("value")
        for option in interaction.get("data", {}).get("options", [])
    }


def _resolved_username(interaction: dict, user_id: str) -> str:
    """Get a display-friendly name for a resolved Discord user."""
    user = (
        interaction.get("data", {})
        .get("resolved", {})
        .get("users", {})
        .get(user_id, {})
    )
    return user.get("global_name") or user.get("username") or user_id


def handle_accolade(interaction: dict) -> dict:
    """Handle the /accolade slash command interaction."""
    options = _option_values(interaction)
    user_id = options.get("user")
    category = options.get("category")
    guild_id = interaction.get("guild_id")

    if not user_id or not guild_id or category not in ACCOLADE_CATEGORIES:
        return {
            "type": 4,
            "data": {
                "content": "Please choose a valid user and accolade category.",
                "flags": 64,
            },
        }

    points = ACCOLADE_CATEGORIES[category]
    username = _resolved_username(interaction, user_id)
    date_str = datetime.now(timezone.utc).date().isoformat()

    try:
        dynamo.claim_category_for_today(date_str, category, user_id)
    except dynamo.AccoladeAlreadyClaimedError:
        return {
            "type": 4,
            "data": {
                "content": (
                    f"**{category}** has already been awarded today. "
                    "It will be available again tomorrow."
                ),
                "flags": 64,
            },
        }

    dynamo.add_credits(user_id, username, guild_id, points)
    return {
        "type": 4,
        "data": {
            "content": (
                f"🏅 **{username}** received **{category}** and earned "
                f"**{points} weekly credits**!"
            )
        },
    }
