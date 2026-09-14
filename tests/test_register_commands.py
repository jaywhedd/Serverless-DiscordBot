import unittest
from unittest.mock import Mock, patch

from rankerbot.command_lambda.handler import COMMAND_HANDLERS
from scripts import register_commands


class RegisterCommandsTests(unittest.TestCase):
    def test_command_definitions_match_runtime_handlers(self):
        names = {command["name"] for command in register_commands.COMMANDS}
        self.assertEqual(names, set(COMMAND_HANDLERS))

    @patch("scripts.register_commands.requests.put")
    def test_guild_scope_uses_guild_bulk_overwrite_endpoint(self, put):
        put.return_value = Mock(status_code=200)
        put.return_value.json.return_value = register_commands.COMMANDS

        register_commands.register_commands("app", "token", "guild", "guild-id")

        self.assertEqual(
            put.call_args.args[0],
            "https://discord.com/api/v10/applications/app/guilds/guild-id/commands",
        )

    @patch("scripts.register_commands.requests.put")
    def test_global_scope_uses_global_bulk_overwrite_endpoint(self, put):
        put.return_value = Mock(status_code=200)
        put.return_value.json.return_value = register_commands.COMMANDS

        register_commands.register_commands("app", "token", "global")

        self.assertEqual(
            put.call_args.args[0],
            "https://discord.com/api/v10/applications/app/commands",
        )

    def test_guild_scope_requires_guild_id(self):
        with self.assertRaises(ValueError):
            register_commands.register_commands("app", "token", "guild")


if __name__ == "__main__":
    unittest.main()