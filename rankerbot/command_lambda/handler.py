"""
Command Lambda entrypoint. Triggered by API Gateway on every Discord
Interaction (slash command, or Discord's initial PING handshake check).

SECURITY: This is a public, internet-accessible endpoint. verify_signature()
and is_timestamp_fresh() MUST both pass before any other code runs -- no
parsing, no DynamoDB calls, nothing -- until the request is proven genuine.
Reject anything that fails verification with a 401, and stop immediately.
"""

import base64
import binascii
import json
import logging

from rankerbot.command_lambda.verify import verify_signature, is_timestamp_fresh
from rankerbot.command_lambda.command.accolade import handle_accolade
from rankerbot.command_lambda.command.credits import handle_credits
from rankerbot.command_lambda.command.leaderboard import handle_leaderboard
from rankerbot.common.ssm import get_discord_public_key
from rankerbot.common.config import MAX_REQUEST_AGE_SECONDS


logger = logging.getLogger(__name__)


COMMAND_HANDLERS = {
    "accolade": handle_accolade,
    "credits": handle_credits,
    "leaderboard": handle_leaderboard,
}


def _get_header(headers: dict, name: str) -> str:
    """API Gateway header casing isn't guaranteed, so look up case-insensitively."""
    if not headers:
        return ""
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value
    return ""


def _interaction_response(payload: dict) -> dict:
    """Wrap a Discord interaction payload for API Gateway."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _raw_request_body(event: dict) -> str | None:
    """Return the exact UTF-8 request body supplied by API Gateway."""
    body = event.get("body")
    if not isinstance(body, str) or not body:
        return None

    if not event.get("isBase64Encoded"):
        return body

    try:
        return base64.b64decode(body, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None


def lambda_handler(event, context):
    # --- Step 1: Extract raw body + signature headers from API Gateway ---
    raw_body = _raw_request_body(event)
    headers = event.get("headers") or {}
    signature = _get_header(headers, "x-signature-ed25519")
    timestamp = _get_header(headers, "x-signature-timestamp")

    # --- Step 2: Verify BEFORE doing anything else ---
    # No parsing, no dispatch, nothing else runs until both checks below pass.
    if not raw_body or not signature:
        return {"statusCode": 401, "body": "invalid signature"}

    if not is_timestamp_fresh(timestamp, MAX_REQUEST_AGE_SECONDS):
        return {"statusCode": 401, "body": "stale request"}

    public_key = get_discord_public_key()
    if not verify_signature(raw_body, signature, timestamp, public_key):
        return {"statusCode": 401, "body": "invalid signature"}

    # --- Step 3: Handle Discord's PING handshake (interaction type 1) ---
    try:
        interaction = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return {"statusCode": 400, "body": "invalid JSON"}

    if not isinstance(interaction, dict):
        return {"statusCode": 400, "body": "invalid interaction"}

    if interaction.get("type") == 1:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"type": 1}),
        }

    # --- Step 4: Route real slash commands to their handler ---
    if interaction.get("type") == 2:
        command_name = interaction.get("data", {}).get("name")
        command_handler = COMMAND_HANDLERS.get(command_name)
        if command_handler:
            try:
                return _interaction_response(command_handler(interaction))
            except Exception:
                logger.exception("Failed to handle Discord command %r", command_name)
                return _interaction_response(
                    {
                        "type": 4,
                        "data": {
                            "content": "Something went wrong while processing that command.",
                            "flags": 64,
                        },
                    }
                )

    return _interaction_response(
        {"type": 4, "data": {"content": "Unknown command."}}
    )
