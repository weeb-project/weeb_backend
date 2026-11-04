"""Tests de demande et de confirmation de réinitialisation du mot de passe."""

from datetime import datetime, timedelta
from unittest.mock import patch

from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase
from urllib.parse import parse_qs, urlsplit


User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetApiTests(APITestCase):
    request_url = reverse("password-reset-request")
    confirm_url = reverse("password-reset-confirm")
    password = "SecurePass123!"

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
            is_active=True,
        )

    def reset_payload(self, **overrides):
        payload = {
            "uidb64": urlsafe_base64_encode(force_bytes(self.user.public_id)),
            "token": PasswordResetTokenGenerator().make_token(self.user),
            "password": "NewSecurePass456!",
        }
        payload.update(overrides)
        return payload

    def test_password_reset_request_returns_same_message_for_known_and_unknown_email(self):
        known_response = self.client.post(
            self.request_url,
            {"email": self.user.email},
            format="json",
        )
        unknown_response = self.client.post(
            self.request_url,
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(known_response.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown_response.status_code, status.HTTP_200_OK)
        self.assertEqual(known_response.data, unknown_response.data)

    def test_password_reset_request_sends_email_with_reset_link(self):
        response = self.client.post(
            self.request_url,
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn("/users/password-reset/form/?uidb64=", mail.outbox[0].body)
        self.assertIn("token=", mail.outbox[0].body)

    def test_password_reset_email_link_completes_password_reset_flow(self):
        request_response = self.client.post(
            self.request_url,
            {"email": self.user.email},
            format="json",
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        reset_link = next(
            line.split()[-1]
            for line in mail.outbox[0].body.splitlines()
            if "/reset-password?" in line
        )
        query = parse_qs(urlsplit(reset_link).query)
        self.assertIn("uidb64", query)
        self.assertIn("token", query)

        new_password = "NewSecurePass456!"
        confirm_response = self.client.post(
            self.confirm_url,
            {
                "uidb64": query["uidb64"][0],
                "token": query["token"][0],
                "password": new_password,
            },
            format="json",
        )

        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        login_url = reverse("login")
        old_password_response = self.client.post(
            login_url,
            {"email": self.user.email, "password": self.password},
            format="json",
        )
        new_password_response = self.client.post(
            login_url,
            {"email": self.user.email, "password": new_password},
            format="json",
        )
        self.assertEqual(
            old_password_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(new_password_response.status_code, status.HTTP_200_OK)

    def test_password_reset_confirm_changes_password_and_invalidates_token(self):
        payload = self.reset_payload()

        response = self.client.post(self.confirm_url, payload, format="json")
        replay_response = self.client.post(self.confirm_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(replay_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(replay_response.data["error_code"], "INVALID_TOKEN")

    def test_password_reset_confirm_rejects_invalid_token(self):
        response = self.client.post(
            self.confirm_url,
            self.reset_payload(token="invalid-token"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "INVALID_TOKEN")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))

    @override_settings(PASSWORD_RESET_TIMEOUT=0)
    def test_password_reset_confirm_rejects_expired_token(self):
        payload = self.reset_payload()
        expired_at = datetime.now() + timedelta(seconds=1)

        with patch.object(PasswordResetTokenGenerator, "_now", return_value=expired_at):
            response = self.client.post(self.confirm_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "INVALID_TOKEN")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))


class PasswordResetTokenUnitTests(TestCase):
    def test_reset_token_is_invalid_after_password_changes(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="SecurePass123!",
            is_active=True,
        )
        generator = PasswordResetTokenGenerator()
        token = generator.make_token(user)

        user.set_password("NewSecurePass456!")
        user.save(update_fields=["password"])

        self.assertFalse(generator.check_token(user, token))
