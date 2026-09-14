"""
Shared DynamoDB access helpers for the `Credits` table.

Used by both the Command Lambda (accolade/leaderboard/credits commands)
and the Finalize Lambda (weekly ranking + reset).
"""
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from rankerbot.common.config import *

# Cached across warm Lambda invocations to avoid recreating the resource
# on every single call.
_table = None
_daily_table = None


class AccoladeAlreadyClaimedError(Exception):
    """Raised when an accolade category has already been awarded today."""


def get_table():
    """Return a boto3 DynamoDB Table resource for the Credits table."""
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(DYNAMODB_TABLE_NAME)
    return _table


def get_daily_accolades_table():
    """Return a boto3 DynamoDB Table resource for the DailyAccolades table."""
    global _daily_table
    if _daily_table is None:
        _daily_table = boto3.resource("dynamodb").Table(DAILY_ACCOLADES_TABLE_NAME)
    return _daily_table


def get_user_credits(user_id: str) -> dict:
    """GetItem for a single user's current weekly credits. Used by /credits."""
    table = get_table()
    response = table.get_item(Key={"user_id": user_id})
    return response.get("Item")  # If the user has no record, this returns None.


def add_credits(user_id: str, username: str, guild_id: str, points: int) -> None:
    """Atomically increment a user's weekly credits for an accolade award."""
    table = get_table()
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=(
            "SET #username = :username, #guild_id = :guild_id "
            "ADD #weekly_credits :points"
        ),
        ExpressionAttributeNames={
            "#username": "username",
            "#guild_id": "guild_id",
            "#weekly_credits": "weekly_credits",
        },
        ExpressionAttributeValues={
            ":username": username,
            ":guild_id": guild_id,
            ":points": points,
        },
    )


def is_category_claimed_today(date_str: str, category: str) -> bool:
    """Check the DailyAccolades table for a date_category key (e.g.
    "2026-09-04#MVP"). Returns True if that category has already been
    awarded to someone today, False otherwise. Used by /accolade before
    allowing a new award for that category."""
    table = get_daily_accolades_table()
    response = table.get_item(
        Key={"date_category": f"{date_str}#{category}"},
        ConsistentRead=True,
    )
    return "Item" in response


def claim_category_for_today(date_str: str, category: str, user_id: str) -> None:
    """Write a new item to the DailyAccolades table claiming `category` for
    `user_id` on `date_str`. Use a conditional PutItem (attribute_not_exists
    on the partition key) so two simultaneous /accolade calls for the same
    category on the same day can't both succeed — this is the race-condition
    guard, similar in spirit to the atomic UpdateItem used in add_credits."""
    table = get_daily_accolades_table()
    date_category = f"{date_str}#{category}"

    try:
        table.put_item(
            Item={
                "date_category": date_category,
                "awarded_to_user_id": user_id,
            },
            ConditionExpression="attribute_not_exists(#date_category)",
            ExpressionAttributeNames={"#date_category": "date_category"},
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            raise AccoladeAlreadyClaimedError(
                f"{category} has already been awarded on {date_str}."
            ) from error
        raise


def query_top_users_by_weekly_credits(guild_id: str, limit: int) -> list:
    """Query the GSI (guild_id, weekly_credits) for the top N users this week.
    Used by /leaderboard and the Finalize Lambda. Must use Query, not Scan."""
    if limit <= 0:
        return []

    table = get_table()
    response = table.query(
        IndexName=WEEKLY_CREDITS_GSI_NAME,
        KeyConditionExpression=Key("guild_id").eq(guild_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return response.get("Items", [])


def query_all_guild_users(guild_id: str) -> list:
    """Return every guild user from the credits GSI, handling pagination."""
    table = get_table()
    query_args = {
        "IndexName": WEEKLY_CREDITS_GSI_NAME,
        "KeyConditionExpression": Key("guild_id").eq(guild_id),
        "ScanIndexForward": False,
    }
    users = []

    while True:
        response = table.query(**query_args)
        users.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return users
        query_args["ExclusiveStartKey"] = last_key


def reset_weekly_credits(user_id: str, credits_to_reset: int, week_id: str) -> bool:
    """Subtract a week's snapshot once while preserving newly awarded points."""
    if credits_to_reset <= 0:
        return False

    table = get_table()
    try:
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=(
                "SET #last_reset_week = :week_id "
                "ADD #weekly_credits :credits"
            ),
            ConditionExpression=(
                "attribute_not_exists(#last_reset_week) "
                "OR #last_reset_week <> :week_id"
            ),
            ExpressionAttributeNames={
                "#weekly_credits": "weekly_credits",
                "#last_reset_week": "last_reset_week",
            },
            ExpressionAttributeValues={
                ":credits": -credits_to_reset,
                ":week_id": week_id,
            },
        )
        return True
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            return False
        raise


def set_current_rank_role(user_id: str, role_id: str) -> None:
    """Update the current_rank_role attribute so the Finalize Lambda can remove
    outdated rank roles before assigning new ones next week."""
    table = get_table()
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET #current_rank_role = :role_id",
        ExpressionAttributeNames={"#current_rank_role": "current_rank_role"},
        ExpressionAttributeValues={":role_id": role_id},
    )


def clear_current_rank_role(user_id: str) -> None:
    """Clear tracked role state after Discord confirms the old role removal."""
    get_table().update_item(
        Key={"user_id": user_id},
        UpdateExpression="REMOVE #current_rank_role",
        ExpressionAttributeNames={"#current_rank_role": "current_rank_role"},
    )


def get_or_create_finalization(
    guild_id: str,
    week_id: str,
    users: list,
    ranked_users: list,
) -> dict:
    """Create an immutable weekly standings snapshot, or return an existing one."""
    table = get_table()
    key = {"user_id": f"FINALIZATION#{guild_id}#{week_id}"}
    item = {
        **key,
        "record_type": "weekly_finalization",
        "finalization_guild_id": guild_id,
        "week_id": week_id,
        "status": "prepared",
        "users": users,
        "ranked_users": ranked_users,
    }
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(#user_id)",
            ExpressionAttributeNames={"#user_id": "user_id"},
        )
        return item
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code != "ConditionalCheckFailedException":
            raise
        return table.get_item(Key=key, ConsistentRead=True)["Item"]


def set_finalization_status(guild_id: str, week_id: str, status: str) -> None:
    """Advance the checkpoint used to safely resume a retried weekly job."""
    get_table().update_item(
        Key={"user_id": f"FINALIZATION#{guild_id}#{week_id}"},
        UpdateExpression="SET #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": status},
    )
