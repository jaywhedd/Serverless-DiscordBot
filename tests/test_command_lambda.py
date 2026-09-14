import base64
import json
import time
import unittest
from unittest.mock import Mock, patch

from nacl.signing import SigningKey

from rankerbot.command_lambda import handler
from rankerbot.command_lambda.verify import is_timestamp_fresh, verify_signature


class SignatureVerificationTests(unittest.TestCase):
    def setUp(self):
        self.signing_key = SigningKey.generate()
        self.public_key = self.signing_key.verify_key.encode().hex()
        self.timestamp = str(int(time.time()))
        self.body = json.dumps({"type": 1}, separators=(",", ":"))
        self.signature = self.signing_key.sign(
            f"{self.timestamp}{self.body}".encode("utf-8")
        ).signature.hex()

    def test_accepts_valid_signature(self):
        self.assertTrue(
            verify_signature(
                self.body, self.signature, self.timestamp, self.public_key
            )
        )

    def test_rejects_modified_body_and_malformed_hex(self):
        self.assertFalse(
            verify_signature(
                self.body + " ", self.signature, self.timestamp, self.public_key
            )
        )
        self.assertFalse(
            verify_signature(self.body, "not-hex", self.timestamp, self.public_key)
        )

    @patch("rankerbot.command_lambda.verify.time.time", return_value=1_000)
    def test_timestamp_freshness_allows_skew_but_rejects_old_requests(self, _):
        self.assertTrue(is_timestamp_fresh("750", 300))
        self.assertTrue(is_timestamp_fresh("1250", 300))
        self.assertFalse(is_timestamp_fresh("699", 300))
        self.assertFalse(is_timestamp_fresh("invalid", 300))


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.signing_key = SigningKey.generate()
        self.public_key = self.signing_key.verify_key.encode().hex()

    def _event(self, payload, *, base64_encoded=False, raw_body=None):
        body = raw_body if raw_body is not None else json.dumps(
            payload, separators=(",", ":")
        )
        timestamp = str(int(time.time()))
        signature = self.signing_key.sign(
            f"{timestamp}{body}".encode("utf-8")
        ).signature.hex()
        event_body = (
            base64.b64encode(body.encode("utf-8")).decode("ascii")
            if base64_encoded
            else body
        )
        return {
            "body": event_body,
            "isBase64Encoded": base64_encoded,
            "headers": {
                "X-Signature-Ed25519": signature,
                "x-signature-timestamp": timestamp,
            },
        }

    @patch("rankerbot.command_lambda.handler.get_discord_public_key")
    def test_ping_handshake_for_plain_and_base64_bodies(self, get_key):
        get_key.return_value = self.public_key
        for encoded in (False, True):
            with self.subTest(base64_encoded=encoded):
                response = handler.lambda_handler(
                    self._event({"type": 1}, base64_encoded=encoded), None
                )
                self.assertEqual(response["statusCode"], 200)
                self.assertEqual(json.loads(response["body"]), {"type": 1})

    @patch("rankerbot.command_lambda.handler.get_discord_public_key")
    def test_missing_signature_is_rejected_without_ssm_lookup(self, get_key):
        response = handler.lambda_handler(
            {"body": "{}", "headers": {}, "isBase64Encoded": False}, None
        )
        self.assertEqual(response["statusCode"], 401)
        get_key.assert_not_called()

    @patch("rankerbot.command_lambda.handler.get_discord_public_key")
    def test_signed_malformed_json_returns_400(self, get_key):
        get_key.return_value = self.public_key
        response = handler.lambda_handler(
            self._event(None, raw_body="not-json"), None
        )
        self.assertEqual(response["statusCode"], 400)

    @patch("rankerbot.command_lambda.handler.get_discord_public_key")
    def test_routes_known_command(self, get_key):
        get_key.return_value = self.public_key
        command_handler = Mock(
            return_value={"type": 4, "data": {"content": "worked"}}
        )
        with patch.dict(handler.COMMAND_HANDLERS, {"credits": command_handler}):
            response = handler.lambda_handler(
                self._event({"type": 2, "data": {"name": "credits"}}), None
            )

        command_handler.assert_called_once()
        self.assertEqual(json.loads(response["body"])["data"]["content"], "worked")

    @patch("rankerbot.command_lambda.handler.get_discord_public_key")
    def test_handler_failure_returns_ephemeral_error(self, get_key):
        get_key.return_value = self.public_key
        command_handler = Mock(side_effect=RuntimeError("database unavailable"))
        with (
            patch.dict(handler.COMMAND_HANDLERS, {"credits": command_handler}),
            patch.object(handler.logger, "exception") as log_exception,
        ):
            response = handler.lambda_handler(
                self._event({"type": 2, "data": {"name": "credits"}}), None
            )

        log_exception.assert_called_once()
        payload = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(payload["data"]["flags"], 64)
        self.assertNotIn("database unavailable", payload["data"]["content"])

    @patch("rankerbot.command_lambda.handler.get_discord_public_key")
    def test_invalid_base64_body_is_rejected(self, get_key):
        response = handler.lambda_handler(
            {
                "body": "%%%",
                "isBase64Encoded": True,
                "headers": {
                    "x-signature-ed25519": "00",
                    "x-signature-timestamp": str(int(time.time())),
                },
            },
            None,
        )
        self.assertEqual(response["statusCode"], 401)
        get_key.assert_not_called()


if __name__ == "__main__":
    unittest.main()