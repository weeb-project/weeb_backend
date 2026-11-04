import json
import re
from unittest.mock import MagicMock, patch

from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from users.email_service import send_transactional_email


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


class PasswordResetFormTests(SimpleTestCase):
    @patch("users.views.PasswordResetTokenGenerator.check_token", return_value=True)
    @patch("users.views.get_password_reset_user", return_value=MagicMock())
    def test_displays_form_for_valid_link(self, get_user, check_token):
        response = self.client.get(
            reverse("password-reset-form"),
            {"uidb64": "encoded-user", "token": "valid-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nouveau mot de passe")
        self.assertContains(response, 'name="password_confirm"')
        self.assertIn("csrftoken", response.cookies)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(response.headers["Referrer-Policy"], "origin")
        self.assertEqual(
            response.headers["X-Robots-Tag"],
            "noindex, nofollow, noarchive",
        )
        self.assertIn(
            "form-action 'self'",
            response.headers["Content-Security-Policy"],
        )

    @patch("users.views.get_password_reset_user", return_value=None)
    def test_displays_error_for_invalid_link(self, get_user):
        response = self.client.get(
            reverse("password-reset-form"),
            {"uidb64": "invalid", "token": "invalid"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lien invalide")

    @patch("users.views.reset_user_password")
    def test_rejects_different_passwords(self, reset_password):
        response = self.client.post(reverse("password-reset-form"), {
            "uidb64": "encoded-user",
            "token": "valid-token",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        })

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Les deux mots de passe ne correspondent pas.",
            status_code=400,
        )
        reset_password.assert_not_called()

    @patch("users.views.reset_user_password", return_value=True)
    def test_resets_password_and_displays_success(self, reset_password):
        response = self.client.post(reverse("password-reset-form"), {
            "uidb64": "encoded-user",
            "token": "valid-token",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mot de passe modifié")
        reset_password.assert_called_once_with(
            "encoded-user",
            "valid-token",
            "StrongPassword123!",
        )

    @patch("users.views.reset_user_password", return_value=True)
    @patch("users.views.PasswordResetTokenGenerator.check_token", return_value=True)
    @patch("users.views.get_password_reset_user", return_value=MagicMock())
    def test_csrf_protected_form_accepts_its_own_token(
        self,
        get_user,
        check_token,
        reset_password,
    ):
        client = Client(enforce_csrf_checks=True)
        response = client.get(
            reverse("password-reset-form"),
            {"uidb64": "encoded-user", "token": "valid-token"},
        )
        html = response.content.decode("utf-8")
        csrf_token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            html,
        ).group(1)

        response = client.post(reverse("password-reset-form"), {
            "csrfmiddlewaretoken": csrf_token,
            "uidb64": "encoded-user",
            "token": "valid-token",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mot de passe modifié")
