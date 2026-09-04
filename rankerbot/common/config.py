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
DYNAMODB_TABLE_NAME = ""

# TODO: Set the GSI name used for guild_id / weekly_credits queries
WEEKLY_CREDITS_GSI_NAME = ""

# TODO: Set number of top users to rank in the weekly finalize job
TOP_N_RANKS = 3

# TODO: Set hardcoded #leaderboard channel ID
LEADERBOARD_CHANNEL_ID = ""

# TODO: Set the test server (guild) ID
GUILD_ID = ""

# TODO: Set the rank role IDs (#1, #2, #3), ordered best to worst
RANK_ROLE_IDS = []
