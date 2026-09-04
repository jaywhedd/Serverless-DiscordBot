"""
Shared configuration and constants for RankerBot Lambdas.

Loads non-secret configuration (table name, region, category point values,
etc.). Secrets (bot token, public key) are NOT stored here — see ssm.py.
"""

#These are the points allocated for accolades, for command /accolade must be typed the same(case sensitive)
ACCOLADE_CATEGORIES = {
     "MVP": 10,
     "Play of the game": 8,
     "Most Kills": 5,
     "Best save of the day": 5,
     "Team Player": 3,
     "Best in moral support": 3,
 }

# TODO: Set DynamoDB table name (Credits)
DYNAMODB_TABLE_NAME = "Credits"

# TODO: Set the GSI name used for guild_id / weekly_credits queries
WEEKLY_CREDITS_GSI_NAME = "guild_id-weekly_credits-index"

# Second table: tracks which category has already been claimed each day,
# so each accolade category can only be given to one person per day.
# Partition key: date_category (e.g. "2026-09-04#MVP")
# Attribute: awarded_to_user_id
DAILY_ACCOLADES_TABLE_NAME = "DailyAccolades"

# TODO: Set number of top users to rank in the weekly finalize job
TOP_N_RANKS = 3

# Maximum age (in seconds) a Discord interaction request's timestamp may be
# before we reject it as stale, to guard against replay attacks. Discord
# signs every request with the current time; this is a defense-in-depth
# check alongside signature verification (see verify.is_timestamp_fresh).
MAX_REQUEST_AGE_SECONDS = 10

# SSM Parameter Store *paths* (not secret values -- safe to commit) used by
# common/ssm.py to fetch the actual Discord public key / bot token at
# runtime. The real values live only in SSM, never in this repo.
DISCORD_PUBLIC_KEY_PARAM = "/rankerbot/discord_public_key"
DISCORD_BOT_TOKEN_PARAM = "/rankerbot/discord_bot_token"

# TODO: Set hardcoded #leaderboard channel ID
LEADERBOARD_CHANNEL_ID = ""

# TODO: Set the test server (guild) ID
GUILD_ID = ""

# TODO: Set the rank role IDs (#1, #2, #3), ordered best to worst
RANK_ROLE_IDS = []
