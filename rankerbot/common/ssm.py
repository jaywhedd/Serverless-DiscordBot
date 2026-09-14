"""
Helpers for reading secrets/config from AWS SSM Parameter Store.

Command Lambda and Finalize Lambda both use this to fetch the Discord
Bot Token and Public Key at runtime instead of hardcoding them.
"""

import boto3

from rankerbot.common.config import DISCORD_BOT_TOKEN_PARAM, DISCORD_PUBLIC_KEY_PARAM

_ssm_client = None
_parameter_cache = {}


def _get_client():
    """Lazily create (and cache) the boto3 SSM client across warm Lambda invocations."""
    global _ssm_client
    if _ssm_client is None:
        _ssm_client = boto3.client("ssm")
    return _ssm_client


def get_parameter(name: str, with_decryption: bool = True) -> str:
    """Fetch and cache a SecureString/String parameter across warm invocations."""
    cache_key = (name, with_decryption)
    if cache_key in _parameter_cache:
        return _parameter_cache[cache_key]

    response = _get_client().get_parameter(Name=name, WithDecryption=with_decryption)
    value = response["Parameter"]["Value"]
    _parameter_cache[cache_key] = value
    return value


def get_discord_bot_token() -> str:
    """Convenience wrapper to fetch the Discord bot token from SSM."""
    return get_parameter(DISCORD_BOT_TOKEN_PARAM, with_decryption=True)


def get_discord_public_key() -> str:
    """Convenience wrapper to fetch the Discord public key from SSM."""
    return get_parameter(DISCORD_PUBLIC_KEY_PARAM, with_decryption=False)