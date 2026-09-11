"""
/accolade @user category

Looks up the category's point value from config.ACCOLADE_CATEGORIES,
validates the category, and atomically adds points to the target user's
weekly_credits and lifetime_credits in DynamoDB.
"""


def handle_accolade(interaction: dict) -> dict:
    """Handle the /accolade slash command interaction."""
    # TODO: extract target user + category from interaction options
    # TODO: validate category against config.ACCOLADE_CATEGORIES
    # TODO: call dynamo.add_credits(...)
    # TODO: build and return the interaction response payload
    pass
