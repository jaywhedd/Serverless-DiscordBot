"""
Command Lambda entrypoint. Triggered by API Gateway on every Discord
Interaction (slash command, or Discord's initial PING handshake check).

SECURITY: This is a public, internet-accessible endpoint. verify_signature()
and is_timestamp_fresh() MUST both pass before any other code runs -- no
parsing, no DynamoDB calls, nothing -- until the request is proven genuine.
Reject anything that fails verification with a 401, and stop immediately.
"""

import json

from rankerbot.command_lambda.verify import verify_signature, is_timestamp_fresh
from rankerbot.common.ssm import get_discord_public_key
from rankerbot.common.config import MAX_REQUEST_AGE_SECONDS


def _get_header(headers: dict, name: str) -> str:
    """API Gateway header casing isn't guaranteed, so look up case-insensitively."""
    if not headers:
        return ""
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value
    return ""


def lambda_handler(event, context):
    # --- Step 1: Extract raw body + signature headers from the API Gateway event ---
    raw_body = event.get("body") or ""
    headers = event.get("headers") or {}
    signature = _get_header(headers, "x-signature-ed25519")
    timestamp = _get_header(headers, "x-signature-timestamp")

    # --- Step 2: Verify BEFORE doing anything else ---
    # No parsing, no dispatch, nothing else runs until both checks below pass.
    if not is_timestamp_fresh(timestamp, MAX_REQUEST_AGE_SECONDS):
        return {"statusCode": 401, "body": "stale request"}

    public_key = get_discord_public_key()
    if not verify_signature(raw_body, signature, timestamp, public_key):
        return {"statusCode": 401, "body": "invalid signature"}

    # --- Step 3: Handle Discord's PING handshake (interaction type 1) ---
    interaction = json.loads(raw_body)
    if interaction.get("type") == 1:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"type": 1}),
        }

    # --- Step 4: Route real slash commands to their handler ---
    # TODO: dispatch to command_lambda/command/accolade.py, leaderboard.py,
    # or credits.py based on the command name in the interaction payload.
    # For now, a minimal "hello world" /ping command proves the full round
    # trip (Discord <-> API Gateway <-> Lambda <-> signature verification)
    # works before any real command logic is wired in.
    if interaction.get("type") == 2:
        command_name = interaction.get("data", {}).get("name")
        if command_name == "ping":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"type": 4, "data": {"content": "pong! \U0001f3d3"}}
                ),
            }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {"type": 4, "data": {"content": "Unknown command."}}
        ),
    }
