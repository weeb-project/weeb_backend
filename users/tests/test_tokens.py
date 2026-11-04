"""Tests de rotation des refresh tokens, de déconnexion et de révocation."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()
REFRESH_COOKIE = "refresh_token"


class RefreshAndLogoutApiTests(APITestCase):
    password = "SecurePass123!"

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
            is_active=True,
        )
        self.login_url = reverse("login")
        self.refresh_url = reverse("token_refresh")
        self.logout_url = reverse("logout")

    def login_and_get_refresh_token(self):
        response = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(REFRESH_COOKIE, response.cookies)
        self.assertTrue(response.cookies[REFRESH_COOKIE]["httponly"])
        return response.cookies[REFRESH_COOKIE].value

    def test_refresh_rotates_cookie_and_blacklists_previous_token(self):
        original_refresh = self.login_and_get_refresh_token()
        self.client.cookies[REFRESH_COOKIE] = original_refresh

        response = self.client.post(self.refresh_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn(REFRESH_COOKIE, response.cookies)
        rotated_refresh = response.cookies[REFRESH_COOKIE].value
        self.assertNotEqual(rotated_refresh, original_refresh)

        self.client.cookies[REFRESH_COOKIE] = original_refresh
        replay_response = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(replay_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_without_cookie_is_rejected(self):
        response = self.client.post(self.refresh_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_refresh_token_and_deletes_cookie(self):
        refresh_token = self.login_and_get_refresh_token()
        self.client.cookies[REFRESH_COOKIE] = refresh_token

        logout_response = self.client.post(self.logout_url, {}, format="json")

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(logout_response.cookies[REFRESH_COOKIE]["max-age"], 0)
        self.client.cookies[REFRESH_COOKIE] = refresh_token
        refresh_response = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_cookie_remains_successful_and_deletes_cookie(self):
        response = self.client.post(self.logout_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies[REFRESH_COOKIE]["max-age"], 0)

    def test_refresh_rejects_invalid_cookie_and_expires_it(self):
        self.client.cookies[REFRESH_COOKIE] = "not-a-valid-token"

        response = self.client.post(self.refresh_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.cookies[REFRESH_COOKIE]["max-age"], 0)
