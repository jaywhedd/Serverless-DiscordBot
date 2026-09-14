import unittest
from unittest.mock import call, patch

from rankerbot.finalize_lambda import announcement, handler, roles


class AnnouncementTests(unittest.TestCase):
    def test_builds_ranked_embed_and_handles_empty_week(self):
        embed = announcement.build_announcement_embed(
            [{"user_id": "1", "username": "Alice", "weekly_credits": 10}]
        )
        self.assertIn("🥇 **Alice** — 10 credits", embed["description"])
        self.assertIn("remain until the next", embed["footer"]["text"])

        empty = announcement.build_announcement_embed([])
        self.assertIn("No weekly credits", empty["description"])


class RoleTests(unittest.TestCase):
    @patch("rankerbot.finalize_lambda.roles.dynamo")
    @patch("rankerbot.finalize_lambda.roles.discord_client")
    def test_removes_every_old_role_and_tracks_new_roles(self, discord, dynamo):
        users = [
            {"user_id": "old", "current_rank_role": "old-role"},
            {"user_id": "never-ranked"},
        ]
        ranked = [{"user_id": "first"}, {"user_id": "second"}]

        roles.remove_outdated_roles(users)
        roles.assign_rank_roles(ranked)

        discord.remove_role.assert_called_once_with(roles.GUILD_ID, "old", "old-role")
        dynamo.clear_current_rank_role.assert_called_once_with("old")
        self.assertEqual(discord.assign_role.call_count, 2)
        self.assertEqual(dynamo.set_current_rank_role.call_count, 2)


class FinalizeHandlerTests(unittest.TestCase):
    def setUp(self):
        self.users = [
            {
                "user_id": "old-winner",
                "username": "Old",
                "weekly_credits": 1,
                "current_rank_role": "last-week-first",
            },
            {"user_id": "winner", "username": "Winner", "weekly_credits": 20},
            {"user_id": "runner-up", "username": "Second", "weekly_credits": 10},
            {"user_id": "zero", "username": "Zero", "weekly_credits": 0},
        ]
        self.event = {"time": "2026-09-14T00:00:00Z"}

    @patch("rankerbot.finalize_lambda.handler.announcement")
    @patch("rankerbot.finalize_lambda.handler.roles")
    @patch("rankerbot.finalize_lambda.handler.dynamo")
    def test_roles_then_announcement_then_reset_and_roles_remain(self, dynamo, role_ops, announce):
        ranked = [self.users[1], self.users[2], self.users[0]]
        dynamo.query_all_guild_users.return_value = self.users
        dynamo.get_or_create_finalization.return_value = {
            "status": "prepared",
            "users": self.users,
            "ranked_users": ranked,
        }
        announce.build_announcement_embed.return_value = {"title": "Weekly"}
        operations = []
        role_ops.remove_outdated_roles.side_effect = lambda _: operations.append("remove")
        role_ops.assign_rank_roles.side_effect = lambda _: operations.append("assign")
        announce.post_announcement.side_effect = lambda *_: operations.append("announce")
        dynamo.reset_weekly_credits.side_effect = lambda user_id, credits, week: operations.append(
            f"reset:{user_id}:{credits}:{week}"
        )

        result = handler.lambda_handler(self.event, None)

        self.assertEqual(operations[:3], ["remove", "assign", "announce"])
        self.assertEqual(
            operations[3:],
            [
                "reset:old-winner:1:2026-W38",
                "reset:winner:20:2026-W38",
                "reset:runner-up:10:2026-W38",
                "reset:zero:0:2026-W38",
            ],
        )
        self.assertEqual(
            dynamo.set_finalization_status.call_args_list,
            [
                call(handler.GUILD_ID, "2026-W38", "roles_updated"),
                call(handler.GUILD_ID, "2026-W38", "announced"),
                call(handler.GUILD_ID, "2026-W38", "completed"),
            ],
        )
        self.assertEqual(result["ranked_user_ids"], ["winner", "runner-up", "old-winner"])
        dynamo.clear_current_rank_role.assert_not_called()

    @patch("rankerbot.finalize_lambda.handler.announcement")
    @patch("rankerbot.finalize_lambda.handler.roles")
    @patch("rankerbot.finalize_lambda.handler.dynamo")
    def test_announcement_failure_does_not_reset_credits(self, dynamo, role_ops, announce):
        dynamo.query_all_guild_users.return_value = self.users
        dynamo.get_or_create_finalization.return_value = {
            "status": "roles_updated",
            "users": self.users,
            "ranked_users": self.users[:1],
        }
        announce.build_announcement_embed.return_value = {"title": "Weekly"}
        announce.post_announcement.side_effect = RuntimeError("Discord unavailable")

        with self.assertRaises(RuntimeError):
            handler.lambda_handler(self.event, None)

        role_ops.remove_outdated_roles.assert_not_called()
        dynamo.reset_weekly_credits.assert_not_called()

    @patch("rankerbot.finalize_lambda.handler.announcement")
    @patch("rankerbot.finalize_lambda.handler.roles")
    @patch("rankerbot.finalize_lambda.handler.dynamo")
    def test_completed_retry_does_not_repeat_side_effects(self, dynamo, role_ops, announce):
        dynamo.query_all_guild_users.return_value = []
        dynamo.get_or_create_finalization.return_value = {
            "status": "completed",
            "users": self.users,
            "ranked_users": self.users[:1],
        }

        handler.lambda_handler(self.event, None)

        role_ops.remove_outdated_roles.assert_not_called()
        role_ops.assign_rank_roles.assert_not_called()
        announce.post_announcement.assert_not_called()
        dynamo.reset_weekly_credits.assert_not_called()


if __name__ == "__main__":
    unittest.main()