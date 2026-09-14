import unittest
from unittest.mock import Mock, patch

from rankerbot.common import dynamo


class DynamoTests(unittest.TestCase):
    @patch("rankerbot.common.dynamo.get_table")
    def test_query_all_guild_users_paginates(self, get_table):
        table = Mock()
        table.query.side_effect = [
            {"Items": [{"user_id": "1"}], "LastEvaluatedKey": {"user_id": "1"}},
            {"Items": [{"user_id": "2"}]},
        ]
        get_table.return_value = table

        users = dynamo.query_all_guild_users("guild")

        self.assertEqual(users, [{"user_id": "1"}, {"user_id": "2"}])
        self.assertNotIn("ExclusiveStartKey", table.query.call_args_list[0].kwargs)
        self.assertEqual(
            table.query.call_args_list[1].kwargs["ExclusiveStartKey"],
            {"user_id": "1"},
        )

    @patch("rankerbot.common.dynamo.get_table")
    def test_reset_subtracts_snapshot_without_clearing_current_role(self, get_table):
        table = Mock()
        get_table.return_value = table

        result = dynamo.reset_weekly_credits("user", 10, "2026-W38")

        kwargs = table.update_item.call_args.kwargs
        self.assertIn("ADD #weekly_credits :credits", kwargs["UpdateExpression"])
        self.assertEqual(
            kwargs["ExpressionAttributeValues"],
            {":credits": -10, ":week_id": "2026-W38"},
        )
        self.assertNotIn("current_rank_role", str(kwargs))
        self.assertTrue(result)

    @patch("rankerbot.common.dynamo.get_table")
    def test_reset_skips_users_with_no_snapshotted_credits(self, get_table):
        result = dynamo.reset_weekly_credits("user", 0, "2026-W38")
        get_table.assert_not_called()
        self.assertFalse(result)

    @patch("rankerbot.common.dynamo.get_table")
    def test_reset_is_idempotent_for_the_same_week(self, get_table):
        from botocore.exceptions import ClientError

        table = Mock()
        table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}},
            "UpdateItem",
        )
        get_table.return_value = table

        result = dynamo.reset_weekly_credits("user", 10, "2026-W38")

        self.assertFalse(result)

    @patch("rankerbot.common.dynamo.get_table")
    def test_clear_current_rank_role_only_removes_role_tracking(self, get_table):
        table = Mock()
        get_table.return_value = table

        dynamo.clear_current_rank_role("user")

        kwargs = table.update_item.call_args.kwargs
        self.assertEqual(kwargs["UpdateExpression"], "REMOVE #current_rank_role")


if __name__ == "__main__":
    unittest.main()