"""Tests API du formulaire de contact : validation, enregistrement et throttling."""

from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from contact.models import Contact


class ContactApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("contact_form")
        self.payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "subject": "Question",
            "message": "I would like more information.",
        }

    def test_valid_contact_submission_is_saved(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Contact.objects.count(), 1)
        contact = Contact.objects.get()
        self.assertEqual(contact.first_name, self.payload["first_name"])
        self.assertEqual(contact.last_name, self.payload["last_name"])
        self.assertEqual(contact.email, self.payload["email"])
        self.assertEqual(contact.subject, self.payload["subject"])
        self.assertEqual(contact.message, self.payload["message"])

    def test_contact_submission_rejects_missing_required_fields(self):
        for field in self.payload:
            with self.subTest(field=field):
                payload = self.payload.copy()
                del payload[field]

                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

    def test_contact_submission_rejects_invalid_email_and_blank_message(self):
        for field, value in (("email", "not-an-email"), ("message", "")):
            with self.subTest(field=field):
                payload = self.payload.copy()
                payload[field] = value

                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

    def test_contact_submission_accepts_maximum_length_for_name_and_subject(self):
        for field in ("first_name", "last_name", "subject"):
            with self.subTest(field=field):
                payload = self.payload.copy()
                payload[field] = "x" * 255

                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data[field], payload[field])

    def test_contact_submission_rejects_name_and_subject_over_maximum_length(self):
        for field in ("first_name", "last_name", "subject"):
            with self.subTest(field=field):
                payload = self.payload.copy()
                payload[field] = "x" * 256

                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

    def test_contact_submission_rejects_blank_email(self):
        payload = self.payload.copy()
        payload["email"] = ""

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_contact_endpoint_returns_429_after_configured_scope_limit(self):
        with patch(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"anon": "100/hour", "contact": "1/hour"},
        ):
            first_response = self.client.post(self.url, self.payload, format="json")
            second_response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(Contact.objects.count(), 1)
