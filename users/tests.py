import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from .email_service import send_transactional_email


class TransactionalEmailServiceTests(SimpleTestCase):
    @override_settings(
        BREVO_API_KEY="test-api-key",
        BREVO_SENDER_EMAIL="sender@example.com",
        BREVO_SENDER_NAME="Weeb",
        BREVO_API_TIMEOUT=10,
    )
    @patch("users.email_service.urlopen")
    def test_sends_email_through_brevo_when_api_key_is_configured(self, urlopen):
        response = MagicMock()
        response.read.return_value = b'{"messageId":"test-message-id"}'
        urlopen.return_value.__enter__.return_value = response

        result = send_transactional_email(
            subject="Reset password",
            message="Reset link",
            recipient_email="user@example.com",
            html_message="<p>Reset link</p>",
        )

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request.headers["Api-key"], "test-api-key")
        self.assertEqual(payload["sender"]["email"], "sender@example.com")
        self.assertEqual(payload["to"], [{"email": "user@example.com"}])
        self.assertEqual(result, {"messageId": "test-message-id"})

    @override_settings(
        BREVO_API_KEY="",
        DEFAULT_FROM_EMAIL="Weeb <sender@example.com>",
    )
    @patch("users.email_service.send_mail")
    def test_uses_django_email_backend_without_brevo_key(self, send_mail):
        send_transactional_email(
            subject="Subject",
            message="Message",
            recipient_email="user@example.com",
        )

        send_mail.assert_called_once_with(
            subject="Subject",
            message="Message",
            from_email="Weeb <sender@example.com>",
            recipient_list=["user@example.com"],
            fail_silently=False,
            html_message=None,
        )
