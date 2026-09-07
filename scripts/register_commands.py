"""
One-off local script to register the bot's slash commands with Discord.

Registers commands against a single test GUILD (not globally), because
guild-scoped commands propagate near-instantly, whereas global commands can
take up to an hour to show up. This is the right choice while testing --
switch to the global commands endpoint later for production.

SECURITY: This script needs your bot token to authenticate with Discord's
REST API. The token is NEVER hardcoded here and NEVER committed. It is read
from the repository-root .env file, an existing environment variable, or an
interactive prompt. The .env file is ignored by Git.

Usage:
    1. Fill in the three values in the repository-root .env file.
    2. Run: python scripts/register_commands.py

Values already present in the process environment take precedence over .env.
If any value is still missing, the script prompts for it interactively (the
token prompt hides input).
"""

import getpass
import os
import sys
from pathlib import Path

import requests

DISCORD_API_BASE = "https://discord.com/api/v10"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# The commands to register. Add more dicts here as new slash commands are
# built (accolade, credits, leaderboard, etc.) -- for now, just the
# hello-world /ping health check.
COMMANDS = [
    {
        "name": "ping",
        "description": "Health check -- replies with pong if the bot is alive.",
        "type": 1,  # CHAT_INPUT (slash command)
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


def register_guild_commands(application_id: str, guild_id: str, bot_token: str) -> None:
    """PUT the full command list to Discord for a single guild. This is a
    bulk overwrite -- it replaces all of the guild's existing commands with
    exactly the list provided, which is Discord's documented way to do it."""
    url = f"{DISCORD_API_BASE}/applications/{application_id}/guilds/{guild_id}/commands"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }

    response = requests.put(url, headers=headers, json=COMMANDS, timeout=10)

    if response.status_code in (200, 201):
        registered = [cmd.get("name") for cmd in response.json()]
        print(f"Success ({response.status_code}). Registered commands: {registered}")
    else:
        # Discord's error bodies don't echo back the token, so safe to print.
        print(f"FAILED ({response.status_code}): {response.text}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    _load_env_file()

    application_id = _get_required("DISCORD_APPLICATION_ID", "Discord Application ID")
    guild_id = _get_required("DISCORD_GUILD_ID", "Discord Test Guild (Server) ID")
    bot_token = _get_required("DISCORD_BOT_TOKEN", "Discord Bot Token", secret=True)

    register_guild_commands(application_id, guild_id, bot_token)


if __name__ == "__main__":
    main()
