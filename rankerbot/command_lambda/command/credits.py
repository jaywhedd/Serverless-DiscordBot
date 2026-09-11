"""
/credits @user

GetItem lookup of a user's weekly_credits and lifetime_credits. Defaults
to the calling user if no @user is given.
"""


def handle_credits(interaction: dict) -> dict:
    """Handle the /credits slash command interaction."""
    # TODO: extract target user from interaction options (default to caller)
    # TODO: call dynamo.get_user_credits(...)
    # TODO: build and return the interaction response payload
    pass
