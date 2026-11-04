"""Tests API des articles : accès public, permissions, création et slugs."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from blog.models import Article


User = get_user_model()


class ArticleApiTests(APITestCase):
    password = "SecurePass123!"

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password=self.password,
            is_active=True,
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password=self.password,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password=self.password,
            is_active=True,
            is_staff=True,
        )
        self.article = Article.objects.create(
            author=self.owner,
            title="A public article",
            content="Article content",
            slug="a-public-article",
        )
        self.list_url = reverse("article-list-create")
        self.detail_url = reverse(
            "article-detail",
            kwargs={"slug": self.article.slug},
        )

    def test_article_list_and_detail_are_public_and_hide_author_private_fields(self):
        list_response = self.client.get(self.list_url)
        detail_response = self.client.get(self.detail_url)

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        author = detail_response.data["author"]
        self.assertEqual(author["id"], str(self.owner.public_id))
        self.assertEqual(author["first_name"], self.owner.first_name)
        self.assertNotIn("email", author)
        self.assertNotIn("is_staff", author)
        self.assertNotIn("is_active", author)

    def test_anonymous_user_cannot_create_article(self):
        response = self.client.post(
            self.list_url,
            {"title": "New article", "content": "Content"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Article.objects.filter(title="New article").exists())

    def test_anonymous_user_cannot_update_or_delete_article(self):
        update_response = self.client.patch(
            self.detail_url,
            {"title": "Changed anonymously"},
            format="json",
        )
        delete_response = self.client.delete(self.detail_url)

        self.assertEqual(update_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(delete_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "A public article")

    def test_creation_uses_authenticated_user_and_generates_unique_slug(self):
        self.client.force_authenticate(user=self.owner)
        payload = {
            "title": "My New Article",
            "content": "Article body",
            "author_id": str(self.other_user.public_id),
        }

        first_response = self.client.post(self.list_url, payload, format="json")
        second_response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first_response.data["author"]["id"], str(self.owner.public_id))
        self.assertEqual(first_response.data["slug"], "my-new-article")
        self.assertEqual(second_response.data["slug"], "my-new-article-2")
        self.assertEqual(
            Article.objects.filter(title="My New Article", author=self.owner).count(),
            2,
        )

    def test_only_owner_or_admin_can_update_and_delete_article(self):
        self.client.force_authenticate(user=self.other_user)
        denied_update = self.client.patch(
            self.detail_url,
            {"title": "Changed by another user"},
            format="json",
        )
        denied_delete = self.client.delete(self.detail_url)

        self.assertEqual(denied_update.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(denied_delete.status_code, status.HTTP_403_FORBIDDEN)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "A public article")

        self.client.force_authenticate(user=self.owner)
        owner_update = self.client.patch(
            self.detail_url,
            {"title": "Changed by owner"},
            format="json",
        )
        self.assertEqual(owner_update.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin)
        admin_delete = self.client.delete(self.detail_url)
        self.assertEqual(admin_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())

    def test_admin_can_update_article(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url,
            {"title": "Changed by admin"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Changed by admin")

    def test_owner_can_delete_article(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())
