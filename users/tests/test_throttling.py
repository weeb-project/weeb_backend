"""Tests de limitation des tentatives de connexion (throttling HTTP 429)."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class LoginThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="SecurePass123!",
            is_active=True,
        )
        self.login_url = reverse("login")

    def test_login_returns_429_after_configured_scope_limit(self):
        payload = {"email": self.user.email, "password": "WrongPassword123!"}

        with patch(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"anon": "100/hour", "login": "1/minute"},
        ):
            first_response = self.client.post(self.login_url, payload, format="json")
            second_response = self.client.post(self.login_url, payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
