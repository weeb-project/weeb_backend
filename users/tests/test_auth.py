"""Tests d'inscription, de connexion et d'accès JWT à l'API utilisateur."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


User = get_user_model()


class RegistrationTests(APITestCase):
    registration_url = reverse("register")
    password = "SecurePass123!"

    def registration_payload(self, **overrides):
        payload = {
            "email": "newuser@example.com",
            "password": self.password,
            "password_confirm": self.password,
            "first_name": "John",
            "last_name": "Doe",
        }
        payload.update(overrides)
        return payload

    def test_registration_creates_inactive_user_without_auth_tokens(self):
        response = self.client.post(
            self.registration_url,
            self.registration_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(response.data["user"]["email"], user.email)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh_token", response.cookies)

    def test_registration_rejects_email_already_registered_with_different_case(self):
        User.objects.create_user(
            email="existing@example.com",
            password=self.password,
            is_active=True,
        )

        response = self.client.post(
            self.registration_url,
            self.registration_payload(email="EXISTING@example.com"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"][0], "EMAIL_ALREADY_EXISTS")
        self.assertEqual(User.objects.filter(email__iexact="existing@example.com").count(), 1)


class LoginTests(APITestCase):
    login_url = reverse("login")
    password = "SecurePass123!"

    @override_settings(
        REFRESH_TOKEN_COOKIE_SECURE=True,
        REFRESH_TOKEN_COOKIE_SAMESITE="Strict",
    )
    def test_login_succeeds_for_active_user(self):
        user = User.objects.create_user(
            email="active@example.com",
            password=self.password,
            is_active=True,
        )

        response = self.client.post(
            self.login_url,
            {"email": user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["email"], user.email)
        access_token = AccessToken(response.data["access"])
        self.assertEqual(access_token["user_id"], str(user.public_id))
        self.assertIn("refresh_token", response.cookies)
        refresh_cookie = response.cookies["refresh_token"]
        self.assertTrue(refresh_cookie["httponly"])
        self.assertTrue(refresh_cookie["secure"])
        self.assertEqual(refresh_cookie["samesite"], "Strict")
        self.assertEqual(refresh_cookie["max-age"], 7 * 24 * 60 * 60)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        profile_response = self.client.get(reverse("current_user"))
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["email"], user.email)

    def test_login_rejects_account_waiting_for_approval(self):
        User.objects.create_user(
            email="pending@example.com",
            password=self.password,
            is_active=False,
        )

        response = self.client.post(
            self.login_url,
            {"email": "pending@example.com", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error_code"], "ACCOUNT_PENDING_APPROVAL")

    def test_login_rejects_invalid_credentials(self):
        User.objects.create_user(
            email="active@example.com",
            password=self.password,
            is_active=True,
        )

        response = self.client.post(
            self.login_url,
            {"email": "active@example.com", "password": "WrongPassword123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error_code"], "INVALID_CREDENTIALS")


class CurrentUserAuthenticationTests(APITestCase):
    current_user_url = reverse("current_user")

    def setUp(self):
        self.user = User.objects.create_user(
            email="active@example.com",
            password="SecurePass123!",
            is_active=True,
        )

    def test_current_user_endpoint_rejects_anonymous_requests(self):
        response = self.client.get(self.current_user_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_user_endpoint_accepts_valid_jwt(self):
        access_token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get(self.current_user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)


class RegistrationApprovalLoginFlowTests(APITestCase):
    password = "SecurePass123!"

    def test_user_can_register_get_approved_and_login(self):
        registration_response = self.client.post(
            reverse("register"),
            {
                "email": "newuser@example.com",
                "password": self.password,
                "password_confirm": self.password,
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )
        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.is_active)

        pending_login_response = self.client.post(
            reverse("login"),
            {"email": user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(
            pending_login_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            pending_login_response.data["error_code"],
            "ACCOUNT_PENDING_APPROVAL",
        )

        admin = User.objects.create_user(
            email="admin@example.com",
            password=self.password,
            is_active=True,
            is_staff=True,
        )
        self.client.force_authenticate(user=admin)
        approval_response = self.client.patch(
            reverse("admin_user_detail", kwargs={"user_id": user.public_id}),
            {"is_active": True},
            format="json",
        )
        self.assertEqual(approval_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=None)
        login_response = self.client.post(
            reverse("login"),
            {"email": user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        self.assertIn("refresh_token", login_response.cookies)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        profile_response = self.client.get(reverse("current_user"))
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["email"], user.email)
