"""
Command Lambda entrypoint. Triggered by API Gateway on every Discord
Interaction (slash command, or Discord's initial PING handshake check).

SECURITY: This is a public, internet-accessible endpoint. verify_signature()
and is_timestamp_fresh() MUST both pass before any other code runs -- no
parsing, no DynamoDB calls, nothing -- until the request is proven genuine.
Reject anything that fails verification with a 401, and stop immediately.
"""

from rankerbot.command_lambda.verify import verify_signature, is_timestamp_fresh
from rankerbot.common.ssm import get_discord_public_key
from rankerbot.common.config import MAX_REQUEST_AGE_SECONDS


def lambda_handler(event, context):
    # --- Step 1: Extract raw body + signature headers from the API Gateway event ---
    # TODO: pull event["body"], event["headers"]["x-signature-ed25519"],
    # event["headers"]["x-signature-timestamp"]

    # --- Step 2: Verify BEFORE doing anything else ---
    # TODO:
    # public_key = get_discord_public_key()
    # if not is_timestamp_fresh(timestamp, MAX_REQUEST_AGE_SECONDS):
    #     return {"statusCode": 401, "body": "stale request"}
    # if not verify_signature(raw_body, signature, timestamp, public_key):
    #     return {"statusCode": 401, "body": "invalid signature"}

    # --- Step 3: Handle Discord's PING handshake (interaction type 1) ---
    # TODO: parse raw_body as JSON, if type == 1, return {"type": 1}

    # --- Step 4: Route real slash commands to their handler ---
    # TODO: dispatch to command_lambda/command/accolade.py, leaderboard.py,
    # or credits.py based on the command name in the interaction payload

    pass