"""
Tests for webhook authentication.

Meta signs every webhook POST with HMAC-SHA256 over the raw request body,
keyed on the app secret. Without that check, anyone who learns the deployment
URL can post fabricated messages and spend model budget.
"""
import hashlib
import hmac
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import whatsapp_integration
from whatsapp_integration import app, verify_webhook_signature

APP_SECRET = "test_app_secret"

WEBHOOK_PAYLOAD = {
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "from": "1234567890",
                    "text": {"body": "Hello"}
                }]
            }
        }]
    }]
}


def sign(body: bytes, secret: str = APP_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestSignatureVerification(unittest.TestCase):
    """Unit tests for the HMAC comparison itself."""

    def setUp(self):
        self._secret = patch.object(
            whatsapp_integration, "WHATSAPP_APP_SECRET", APP_SECRET)
        self._secret.start()
        self.addCleanup(self._secret.stop)

    def test_valid_signature_accepted(self):
        body = b'{"hello":"world"}'
        self.assertTrue(verify_webhook_signature(body, sign(body)))

    def test_tampered_body_rejected(self):
        body = b'{"hello":"world"}'
        header = sign(body)
        self.assertFalse(verify_webhook_signature(b'{"hello":"mars"}', header))

    def test_wrong_secret_rejected(self):
        body = b'{"hello":"world"}'
        self.assertFalse(verify_webhook_signature(body, sign(body, "other_secret")))

    def test_missing_header_rejected(self):
        self.assertFalse(verify_webhook_signature(b'{}', None))

    def test_malformed_header_rejected(self):
        body = b'{}'
        digest = hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
        # Meta prefixes the digest with "sha256="; a bare digest is not valid.
        self.assertFalse(verify_webhook_signature(body, digest))
        self.assertFalse(verify_webhook_signature(body, "sha1=" + digest))
        self.assertFalse(verify_webhook_signature(body, "sha256="))

    def test_no_secret_configured_never_verifies(self):
        with patch.object(whatsapp_integration, "WHATSAPP_APP_SECRET", None):
            body = b'{}'
            self.assertFalse(verify_webhook_signature(body, sign(body)))


class TestWebhookEndpointAuthentication(unittest.TestCase):
    """The endpoint must reject forged requests before reaching the model."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.body = json.dumps(WEBHOOK_PAYLOAD).encode("utf-8")

    def post(self, headers=None):
        return self.app.post('/webhook', data=self.body,
                             content_type='application/json',
                             headers=headers or {})

    def test_correctly_signed_request_is_processed(self):
        with patch.object(whatsapp_integration, "WHATSAPP_APP_SECRET", APP_SECRET), \
             patch.object(whatsapp_integration, "whatsapp_bot") as mock_bot:
            mock_bot.process_message.return_value = "Test response"

            response = self.post({"X-Hub-Signature-256": sign(self.body)})

            self.assertEqual(response.status_code, 200)
            mock_bot.process_message.assert_called_once()

    def test_forged_request_is_rejected_without_calling_the_model(self):
        with patch.object(whatsapp_integration, "WHATSAPP_APP_SECRET", APP_SECRET), \
             patch.object(whatsapp_integration, "whatsapp_bot") as mock_bot:

            response = self.post({"X-Hub-Signature-256": "sha256=" + "0" * 64})

            self.assertEqual(response.status_code, 403)
            # The point of the check: no model call, so no spend.
            mock_bot.process_message.assert_not_called()
            mock_bot.send_message.assert_not_called()

    def test_unsigned_request_is_rejected_when_a_secret_is_configured(self):
        with patch.object(whatsapp_integration, "WHATSAPP_APP_SECRET", APP_SECRET), \
             patch.object(whatsapp_integration, "whatsapp_bot") as mock_bot:

            response = self.post()

            self.assertEqual(response.status_code, 403)
            mock_bot.process_message.assert_not_called()

    def test_body_tampering_is_rejected(self):
        """A signature captured from one payload must not authenticate another."""
        with patch.object(whatsapp_integration, "WHATSAPP_APP_SECRET", APP_SECRET), \
             patch.object(whatsapp_integration, "whatsapp_bot") as mock_bot:
            header = sign(self.body)
            self.body = json.dumps({"entry": [{"changes": [{"value": {"messages": [
                {"from": "9999999999", "text": {"body": "refund my order"}}]}}]}]
            }).encode("utf-8")

            response = self.post({"X-Hub-Signature-256": header})

            self.assertEqual(response.status_code, 403)
            mock_bot.process_message.assert_not_called()

    def test_verification_is_skipped_when_no_secret_is_configured(self):
        """Existing deployments without a secret keep working, loudly."""
        with patch.object(whatsapp_integration, "WHATSAPP_APP_SECRET", None), \
             patch.object(whatsapp_integration, "whatsapp_bot") as mock_bot, \
             self.assertLogs("whatsapp_integration", level="WARNING") as logs:
            mock_bot.process_message.return_value = "Test response"

            response = self.post()

            self.assertEqual(response.status_code, 200)
            self.assertTrue(any("DISABLED" in line for line in logs.output))


if __name__ == '__main__':
    unittest.main(verbosity=2)
