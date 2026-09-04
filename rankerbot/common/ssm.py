"""
Helpers for reading secrets/config from AWS SSM Parameter Store.

Command Lambda and Finalize Lambda both use this to fetch the Discord
Bot Token and Public Key at runtime instead of hardcoding them.
"""


def get_parameter(name: str, with_decryption: bool = True) -> str:
    """Fetch a single SecureString/String parameter from SSM Parameter Store."""
    # TODO: implement using boto3 ssm client
    pass


def get_discord_bot_token() -> str:
    """Convenience wrapper to fetch the Discord bot token from SSM."""
    # TODO: implement
    pass


def get_discord_public_key() -> str:
    """Convenience wrapper to fetch the Discord public key from SSM."""
    # TODO: implement
    pass