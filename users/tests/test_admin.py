"""Tests des permissions et actions de l'API d'administration des utilisateurs."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AdminUserApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="SecurePass123!",
            is_active=True,
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            email="user@example.com",
            password="SecurePass123!",
            is_active=True,
        )
        self.list_url = reverse("admin_user_list")
        self.detail_url = reverse(
            "admin_user_detail",
            kwargs={"user_id": self.regular_user.public_id},
        )

    def test_admin_user_list_requires_admin_access(self):
        anonymous_response = self.client.get(self.list_url)
        self.client.force_authenticate(user=self.regular_user)
        regular_user_response = self.client.get(self.list_url)
        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.get(self.list_url)

        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(regular_user_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertIn(
            self.regular_user.email,
            [user["email"] for user in admin_response.data],
        )

    def test_admin_can_activate_another_user(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url,
            {"is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_active)

    def test_admin_cannot_disable_or_remove_own_admin_access(self):
        self.client.force_authenticate(user=self.admin)
        own_detail_url = reverse(
            "admin_user_detail",
            kwargs={"user_id": self.admin.public_id},
        )

        disable_response = self.client.patch(
            own_detail_url,
            {"is_active": False},
            format="json",
        )
        remove_admin_response = self.client.patch(
            own_detail_url,
            {"is_staff": False},
            format="json",
        )

        self.assertEqual(disable_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            disable_response.data["error_code"][0],
            "CANNOT_DEACTIVATE_SELF",
        )
        self.assertEqual(remove_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            remove_admin_response.data["error_code"][0],
            "CANNOT_REMOVE_OWN_ADMIN_ACCESS",
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertTrue(self.admin.is_staff)
