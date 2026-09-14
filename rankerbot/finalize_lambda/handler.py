"""
Finalize Lambda entrypoint.

Triggered weekly by EventBridge (cron). Queries DynamoDB for the top N
users by weekly_credits, assigns/updates Discord rank roles, posts the
weekly announcement embed to #leaderboard, then resets weekly credits to zero.
"""

from datetime import datetime, timezone

from rankerbot.common import dynamo
from rankerbot.common.config import (
    GUILD_ID,
    LEADERBOARD_CHANNEL_ID,
    RANK_ROLE_IDS,
    TOP_N_RANKS,
)
from rankerbot.finalize_lambda import announcement, roles


STATUS_ORDER = {
    "prepared": 0,
    "roles_updated": 1,
    "announced": 2,
    "completed": 3,
}


def _event_time(event: dict) -> datetime:
    """Use EventBridge's stable event time so retries keep the same week ID."""
    event_time = event.get("time") if isinstance(event, dict) else None
    if event_time:
        try:
            return datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc)


def _week_id(event: dict) -> str:
    year, week, _ = _event_time(event).isocalendar()
    return f"{year}-W{week:02d}"


def _ranked_users(users: list) -> list:
    eligible = [user for user in users if int(user.get("weekly_credits", 0)) > 0]
    eligible.sort(
        key=lambda user: (
            -int(user.get("weekly_credits", 0)),
            str(user.get("user_id", "")),
        )
    )
    return eligible[:TOP_N_RANKS]


def lambda_handler(event: dict, context) -> dict:
    """EventBridge scheduled rule entrypoint for the weekly finalize job."""
    if not GUILD_ID:
        raise ValueError("GUILD_ID must be configured before weekly finalization")
    if not LEADERBOARD_CHANNEL_ID:
        raise ValueError(
            "LEADERBOARD_CHANNEL_ID must be configured before weekly finalization"
        )
    if len(RANK_ROLE_IDS) < TOP_N_RANKS:
        raise ValueError("RANK_ROLE_IDS must contain one role for every ranked place")

    week_id = _week_id(event)
    current_users = dynamo.query_all_guild_users(GUILD_ID)
    snapshot = dynamo.get_or_create_finalization(
        GUILD_ID,
        week_id,
        current_users,
        _ranked_users(current_users),
    )
    users = snapshot.get("users", [])
    ranked_users = snapshot.get("ranked_users", [])
    status = snapshot.get("status", "prepared")

    if STATUS_ORDER.get(status, -1) < STATUS_ORDER["roles_updated"]:
        roles.remove_outdated_roles(users)
        roles.assign_rank_roles(ranked_users)
        dynamo.set_finalization_status(GUILD_ID, week_id, "roles_updated")
        status = "roles_updated"

    if STATUS_ORDER[status] < STATUS_ORDER["announced"]:
        embed = announcement.build_announcement_embed(ranked_users)
        announcement.post_announcement(embed, week_id)
        dynamo.set_finalization_status(GUILD_ID, week_id, "announced")
        status = "announced"

    if STATUS_ORDER[status] < STATUS_ORDER["completed"]:
        for user in users:
            user_id = user.get("user_id")
            if user_id:
                dynamo.reset_weekly_credits(
                    user_id,
                    int(user.get("weekly_credits", 0)),
                    week_id,
                )
        dynamo.set_finalization_status(GUILD_ID, week_id, "completed")

    return {
        "status": "completed",
        "week_id": week_id,
        "participant_count": len(users),
        "ranked_user_ids": [user.get("user_id") for user in ranked_users],
    }
