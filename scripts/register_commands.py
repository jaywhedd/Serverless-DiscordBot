"""
One-off local script to register the bot's slash commands with Discord.

Registers commands against a single test guild by default. Pass
``--scope global`` for production registration across every server where the
application is installed.

SECURITY: This script needs your bot token to authenticate with Discord's
REST API. The token is NEVER hardcoded here and NEVER committed. It is read
from the repository-root .env file, an existing environment variable, or an
interactive prompt. The .env file is ignored by Git.

Usage:
    1. Fill in the three values in the repository-root .env file.
    2. Run: python scripts/register_commands.py
       Production: python scripts/register_commands.py --scope global

Values already present in the process environment take precedence over .env.
If any value is still missing, the script prompts for it interactively (the
token prompt hides input).
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

import requests

DISCORD_API_BASE = "https://discord.com/api/v10"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rankerbot.common.config import ACCOLADE_CATEGORIES

# The guild-scoped commands exposed by the Command Lambda.
COMMANDS = [
    {
        "name": "accolade",
        "description": "Award today's available accolade to a user.",
        "type": 1,
        "options": [
            {
                "name": "user",
                "description": "The user receiving the accolade.",
                "type": 6,  # USER
                "required": True,
            },
            {
                "name": "category",
                "description": "The accolade category to award.",
                "type": 3,  # STRING
                "required": True,
                "choices": [
                    {"name": category, "value": category}
                    for category in ACCOLADE_CATEGORIES
                ],
            },
        ],
    },
    {
        "name": "credits",
        "description": "Show a user's current weekly credits.",
        "type": 1,
        "options": [
            {
                "name": "user",
                "description": "The user to check; defaults to you.",
                "type": 6,  # USER
                "required": False,
            }
        ],
    },
    {
        "name": "leaderboard",
        "description": "Show the current weekly credits leaderboard.",
        "type": 1,
    },
]


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Load simple KEY=VALUE entries without overriding existing variables.

    This intentionally avoids adding another dependency for a small local
    administration script. Blank lines and comments are ignored; matching
    single or double quotes around values are removed.
    """
    if not path.is_file():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            print(
                f"WARNING: Ignoring malformed .env line {line_number}.",
                file=sys.stderr,
            )
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _get_required(env_var: str, prompt: str, secret: bool = False) -> str:
    """Read a required value from the environment, falling back to an
    interactive prompt so nothing needs to be hardcoded or committed."""
    value = os.environ.get(env_var)
    if value:
        return value.strip()

    if secret:
        value = getpass.getpass(f"{prompt}: ")
    else:
        value = input(f"{prompt}: ")

    value = value.strip()
    if not value:
        print(f"ERROR: {env_var} is required.", file=sys.stderr)
        sys.exit(1)
    return value


def register_commands(
    application_id: str,
    bot_token: str,
    scope: str = "guild",
    guild_id: str | None = None,
) -> None:
    """Bulk overwrite Discord commands for a guild or for the application."""
    if scope == "guild":
        if not guild_id:
            raise ValueError("guild_id is required for guild command registration")
        url = (
            f"{DISCORD_API_BASE}/applications/{application_id}"
            f"/guilds/{guild_id}/commands"
        )
    elif scope == "global":
        url = f"{DISCORD_API_BASE}/applications/{application_id}/commands"
    else:
        raise ValueError(f"Unsupported command scope: {scope}")

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.put(url, headers=headers, json=COMMANDS, timeout=10)
    except requests.RequestException as error:
        print(f"FAILED to contact Discord: {error}", file=sys.stderr)
        sys.exit(1)

    if response.status_code in (200, 201):
        registered = [cmd.get("name") for cmd in response.json()]
        print(f"Success ({response.status_code}). Registered commands: {registered}")
    else:
        # Discord's error bodies don't echo back the token, so safe to print.
        print(f"FAILED ({response.status_code}): {response.text}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register RankerBot slash commands.")
    parser.add_argument(
        "--scope",
        choices=("guild", "global"),
        default="guild",
        help="Register immediately in one guild (default) or globally for production.",
    )
    args = parser.parse_args()

    _load_env_file()

    application_id = _get_required("DISCORD_APPLICATION_ID", "Discord Application ID")
    bot_token = _get_required("DISCORD_BOT_TOKEN", "Discord Bot Token", secret=True)
    guild_id = None
    if args.scope == "guild":
        guild_id = _get_required("DISCORD_GUILD_ID", "Discord Test Guild (Server) ID")

    register_commands(application_id, bot_token, args.scope, guild_id)


if __name__ == "__main__":
    main()
