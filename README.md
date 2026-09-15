# Serverless-DiscordBot (RankerBot)

A serverless Discord bot on AWS where users award each other daily accolades that build weekly credit totals. Each accolade category can be awarded to **one user per day**. A weekly scheduled job finalizes the leaderboard, automatically assigns rank roles (**#1, #2, #3**) through the Discord API, and resets weekly credits.

Built with **Python, AWS Lambda, API Gateway, DynamoDB, and EventBridge**, and designed to run entirely within the **AWS free tier**.

---

## Features

- **Daily accolades** - award your teammates a curated set of categories, each worth a fixed number of weekly credits.
- **One award per category per day** - an atomic, race-guarded claim in DynamoDB guarantees a category can't be handed out twice on the same day.
- **Live weekly leaderboard** - view the current top users with `/leaderboard` at any time.
- **Automatic weekly finalization** - a scheduled job posts the winner announcement and assigns/removes the `#1`, `#2`, and `#3` rank roles.
- **Idempotent weekly reset** - standings are snapshotted and credits are reset exactly once per week, so retried runs never double-pay or double-post.
- **Secure by default** - every command is cryptographically verified (Ed25519) and replay-protected before any logic runs.

---

## Slash Commands

| Command | Description |
| --- | --- |
| `/accolade @user <category>` | Award an accolade category to a user, adding its points to their weekly credits. |
| `/credits @user` | Show a user's current weekly credits (defaults to the caller). |
| `/leaderboard` | Show the current weekly credits leaderboard (read-only). |

### Accolade categories and point values

Categories are defined (case-sensitive) in `rankerbot/common/config.py`:

| Category | Weekly credits |
| --- | --- |
| MVP | 10 |
| Play of the game | 8 |
| Most Kills | 5 |
| Best save of the day | 5 |
| Team Player | 3 |
| Best in moral support | 3 |

---

## How it works

### Daily flow (`/accolade`)

1. A member runs `/accolade @user <category>`.
2. API Gateway invokes the **Command Lambda**.
3. The Lambda verifies the request's Ed25519 signature and timestamp freshness **before** touching anything else.
4. It checks the `DailyAccolades` table to confirm that category hasn't been awarded today, then atomically claims it (a conditional write prevents race conditions).
5. It atomically increments the target user's `weekly_credits` in the `Credits` table and confirms the award in the channel.

### Weekly flow (automated)

An EventBridge `cron` rule triggers the **Finalize Lambda** each week:

1. It queries all guild users from the `Credits` table and snapshots the standings for the week.
2. It removes every previously-assigned rank role and assigns `#1`, `#2`, `#3` to the top users via the Discord REST API.
3. It posts the final leaderboard embed to the leaderboard channel.
4. It subtracts the snapshot from each user's credits (preserving anything newly awarded mid-run) and marks the week complete.

The job advances through a recorded status (`prepared → roles_updated → announced → completed`). If a run fails partway and is retried, it resumes from the saved checkpoint instead of repeating side effects, this is what makes the weekly reset safe and idempotent.

---

## Architecture & project layout

```
Serverless-DiscordBot/
├─ rankerbot/
│  ├─ __init__.py
│  ├─ command_lambda/          # Command Lambda (API Gateway → Discord interaction handler)
│  │  ├─ handler.py            #   entrypoint: signature check, PING handshake, command routing
│  │  ├─ verify.py             #   Ed25519 signature + timestamp freshness verification
│  │  └─ command/
│  │     ├─ accolade.py        #   /accolade
│  │     ├─ credits.py         #   /credits
│  │     └─ leaderboard.py     #   /leaderboard
│  ├─ finalize_lambda/         # Finalize Lambda (EventBridge weekly cron)
│  │  ├─ handler.py            #   entrypoint: snapshot, resume, orchestrate weekly reset
│  │  ├─ announcement.py       #   builds/posts the winner embed
│  │  └─ roles.py              #   removes/assigns rank roles
│  └─ common/
│     ├─ config.py             #   constants, accolade categories, param paths
│     ├─ discord_client.py     #   Discord REST API wrapper (bot token auth, 429 retries)
│     ├─ dynamo.py             #   DynamoDB access (Credits + DailyAccolades)
│     └─ ssm.py                #   secrets fetched from SSM Parameter Store
├─ scripts/
│  └─ register_commands.py     # one-off slash-command registration helper
├─ tests/                      # pytest test suite for all modules/behaviours
├─ requirements.txt
├─ LICENSE                     # MIT
└─ README.md
```

(Directories like `package/`, `zip_check/`, and `*.zip` are Lambda deployment/build artifacts — see [Deployment](#deployment). They are gitignored.)

### Diagram

```
            ┌──────────────┐  interactions   ┌────────────────────┐
  Discord ─▶│ API Gateway  │────────────────▶│ Command Lambda     │
            └──────────────┘                 └─────────┬──────────┘
                                                       │ verify + route commands
                                                       ▼
EventBridge ──(weekly cron)──▶ ┌────────────────┐  ┌────────────┐
                               │ Finalize Lambda│─▶│ DynamoDB   │  Credits + DailyAccolades
                               └───────┬────────┘  └────────────┘
                                       │ rank roles & announcement
                                       ▼
                              Discord REST API        ▲
                                                       │
                                     SSM Parameter Store┘ (public key, bot token)
```

---

## AWS resources

### DynamoDB - `Credits` table

Primary storage for weekly credits, rank-role tracking, and weekly snapshots.

- **Partition key:** `user_id` (String)
- **Attributes:** `username`, `guild_id`, `weekly_credits` (Number), `current_rank_role`, `last_reset_week`
- **Weekly snapshot rows:** `user_id` = `FINALIZATION#{guild_id}#{week_id}` with `status`, `users`, and `ranked_users` - the immutable record the weekly job resumes from.
- **GSI:** `guild_id-weekly_credits-index` - powers `/leaderboard` and the weekly top-N queries.

### DynamoDB - `DailyAccolades` table

Ensures each category can only be awarded once per day.

- **Partition key:** `date_category` (String) - e.g. `2026-09-04#MVP`
- **Attributes:** `awarded_to_user_id`

### SSM Parameter Store (secrets - never in code or git)

| Parameter | Type | Used by |
| --- | --- | --- |
| `/rankerbot/discord_public_key` | String | Command Lambda (signature verification) |
| `/rankerbot/discord_bot_token` | SecureString | Finalize Lambda + Discord REST authentication |

### Compute & orchestration

- **API Gateway** - public HTTPS endpoint fronting the Command Lambda (hosts the Discord interaction webhook).
- **Lambda - Command** - `rankerbot.command_lambda.handler.lambda_handler`.
- **Lambda - Finalize** - `rankerbot.finalize_lambda.handler.lambda_handler`.
- **EventBridge** - weekly `cron` rule that triggers the Finalize Lambda.
- **IAM** - each Lambda gets a role granting the minimum access required (DynamoDB, SSM).

---

## Configuration

Non-secret settings live in `rankerbot/common/config.py`. Remember to set the values that currently carry `# TODO` markers for a fresh deployment:

| Constant | Default / example | Purpose |
| --- | --- | --- |
| `ACCOLADE_CATEGORIES` | MVP 10, Play of the game 8, Most Kills 5, Best save of the day 5, Team Player 3, Best in moral support 3 | Accolade names → point values |
| `DYNAMODB_TABLE_NAME` | `Credits` | Credits table name |
| `WEEKLY_CREDITS_GSI_NAME` | `guild_id-weekly_credits-index` | Leaderboard GSI name |
| `DAILY_ACCOLADES_TABLE_NAME` | `DailyAccolades` | Daily-accolade table name |
| `TOP_N_RANKS` | `3` | How many users are ranked each week |
| `MAX_REQUEST_AGE_SECONDS` | `300` | Max request age accepted (replay guard) |
| `DISCORD_PUBLIC_KEY_PARAM` | `/rankerbot/discord_public_key` | SSM path for the public key |
| `DISCORD_BOT_TOKEN_PARAM` | `/rankerbot/discord_bot_token` | SSM path for the bot token |
| `LEADERBOARD_CHANNEL_ID` | *TODO* | Channel where weekly announcements are posted |
| `GUILD_ID` | *TODO* | The target Discord server (guild) |
| `RANK_ROLE_IDS` | *TODO* | `#1`, `#2`, `#3` role IDs (best → worst) |

---

## Local development

### Prerequisites

- Python 3.11+ (PyNaCl wheels available for common platforms)
- AWS credentials configured locally (for running the Lambda modules against DynamoDB/SSM)

### 1. Set up a virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # PowerShell
pip install -r requirements.txt
```

`requirements.txt` contains `boto3`, `PyNaCl`, and `requests`.

### 2. Configure local secrets (`.env`)

Create a `.env` in the repository root (already gitignored) with the values used by the command-registration script:

```
DISCORD_APPLICATION_ID=<your app id>
DISCORD_BOT_TOKEN=<your bot token>
DISCORD_GUILD_ID=<your test guild id>
```

### 3. Run the tests

The suite lives in `tests/` and is run with pytest:

```powershell
.\.venv\Scripts\python -m pytest
```

### 4. Register the slash commands

Register the commands against a single test guild:

```powershell
.\.venv\Scripts\python scripts/register_commands.py
```

Or against every server (production scope):

```powershell
.\.venv\Scripts\python scripts/register_commands.py --scope global
```

The script reads the values from `.env` or existing environment variables and prompts for anything still missing (the bot token prompt hides input).

---

## Deployment

> There is no CloudFormation/SAM template in this repo, so deployment is a practical zip-to-Lambda workflow. Configuration, IAM, and resource wiring are done in the AWS Console/CLI.

1. **Install runtime dependencies into the bundle folder:**
   ```powershell
   pip install -r requirements.txt --target package
   ```
2. **Assemble the deployment zip** so the `rankerbot` package and dependencies sit together at the archive root:
   ```powershell
   Compress-Archive -Path package/*, rankerbot -DestinationPath rankerbot_deployment.zip
   ```
   (Keep `package/`, `zip_check/`, and `rankerbot_deployment.zip` out of git — they're already listed in `.gitignore`.)
3. **Create the two Lambda functions** and upload the zip:
   - Command: handler `rankerbot.command_lambda.handler.lambda_handler`
   - Finalize: handler `rankerbot.finalize_lambda.handler.lambda_handler`
4. **Create the DynamoDB tables** (`Credits` + `DailyAccolades` per the schemas above, including the `guild_id-weekly_credits-index` GSI) and the **SSM parameters** (public key, bot token).
5. **Wire up triggers:**
   - Add an **API Gateway** HTTP trigger to the Command Lambda and point the bot's **Interactions Endpoint URL** at it.
   - Add an **EventBridge** rule (e.g. weekly `cron` expression) targeting the Finalize Lambda.
6. **Assign IAM roles** allowing each function to reach DynamoDB and SSM as needed.
7. **Register the slash commands** (see [Local development](#4-register-the-slash-commands)) and confirm the bot responds.

---

## Security notes

- **Ed25519 signature verification** — every interaction body is verified against the Discord public key before it is parsed or touches any resource. Requests that fail return `401` immediately.
- **Replay protection** - the request timestamp must be within `MAX_REQUEST_AGE_SECONDS` (300s) of the current time.
- **Secrets are never committed** - the bot token and public key live in SSM Parameter Store (fetched at runtime); local copies go in the gitignored `.env`.
- **Discord REST calls** are authenticated with the bot token and handle rate limits with bounded 429 retries.

---

## License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 Jason.

---

#### WeThinkCode_ Verfication
WTC-GFQRQG4H