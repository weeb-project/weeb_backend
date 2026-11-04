"""Tests unitaires des validateurs de mot de passe et serializers utilisateur."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from rest_framework import serializers

from users.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TwoFactorCodeSerializer,
    UserRegisterSerializer,
    normalize_email,
    validate_password_strength,
)
from users.validators import SpecialCharacterValidator, UppercaseValidator


class PasswordValidatorTests(TestCase):
    def test_uppercase_validator_rejects_password_without_uppercase(self):
        with self.assertRaises(DjangoValidationError) as raised:
            UppercaseValidator().validate("securepass123!")

        self.assertEqual(raised.exception.code, "password_no_upper")

    def test_uppercase_validator_accepts_password_with_uppercase(self):
        self.assertIsNone(UppercaseValidator().validate("Securepass123!"))

    def test_special_character_validator_rejects_alphanumeric_password(self):
        with self.assertRaises(DjangoValidationError) as raised:
            SpecialCharacterValidator().validate("SecurePass123")

        self.assertEqual(raised.exception.code, "password_no_special")

    def test_special_character_validator_accepts_password_with_symbol(self):
        self.assertIsNone(SpecialCharacterValidator().validate("SecurePass123!"))

    def test_password_strength_rejects_weak_password_with_api_error_code(self):
        with self.assertRaises(serializers.ValidationError) as raised:
            validate_password_strength("weak")

        self.assertEqual(str(raised.exception.detail["error_code"]), "WEAK_PASSWORD")
        self.assertTrue(raised.exception.detail["details"])

    def test_password_strength_accepts_password_matching_configured_rules(self):
        self.assertIsNone(validate_password_strength("SecurePass123!"))


class EmailNormalizationTests(TestCase):
    def test_normalize_email_lowercases_local_and_domain_parts(self):
        self.assertEqual(
            normalize_email("First.Last@EXAMPLE.COM"),
            "first.last@example.com",
        )

    def test_registration_serializer_normalizes_email_before_saving(self):
        serializer = UserRegisterSerializer(
            data={
                "email": "New.User@EXAMPLE.COM",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "first_name": "New",
                "last_name": "User",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.email, "new.user@example.com")
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("SecurePass123!"))
        self.assertNotIn("password", serializer.data)
        self.assertNotIn("password_confirm", serializer.data)


class UserSerializerValidationTests(TestCase):
    def test_registration_requires_email_password_and_confirmation(self):
        serializer = UserRegisterSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            set(serializer.errors),
            {"email", "password", "password_confirm"},
        )

    def test_registration_rejects_invalid_email_format(self):
        serializer = UserRegisterSerializer(
            data={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_registration_rejects_mismatched_password_confirmation(self):
        serializer = UserRegisterSerializer(
            data={
                "email": "new@example.com",
                "password": "SecurePass123!",
                "password_confirm": "DifferentPass456!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors["error_code"][0]), "PASSWORD_MISMATCH")

    def test_registration_rejects_weak_password(self):
        serializer = UserRegisterSerializer(
            data={
                "email": "new@example.com",
                "password": "weak",
                "password_confirm": "weak",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors["error_code"][0]), "WEAK_PASSWORD")

    def test_password_reset_request_requires_valid_email_and_normalizes_it(self):
        missing_email = PasswordResetRequestSerializer(data={})
        invalid_email = PasswordResetRequestSerializer(data={"email": "invalid"})
        valid_email = PasswordResetRequestSerializer(
            data={"email": "User@EXAMPLE.COM"}
        )

        self.assertFalse(missing_email.is_valid())
        self.assertIn("email", missing_email.errors)
        self.assertFalse(invalid_email.is_valid())
        self.assertIn("email", invalid_email.errors)
        self.assertTrue(valid_email.is_valid(), valid_email.errors)
        self.assertEqual(
            valid_email.validated_data["email"],
            "user@example.com",
        )

    def test_password_reset_confirm_requires_all_fields(self):
        serializer = PasswordResetConfirmSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"uidb64", "token", "password"})

    def test_password_reset_confirm_rejects_weak_password(self):
        serializer = PasswordResetConfirmSerializer(
            data={
                "uidb64": "encoded-user-id",
                "token": "reset-token",
                "password": "weak",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            str(serializer.errors["password"]["error_code"]),
            "WEAK_PASSWORD",
        )

    def test_password_reset_confirm_does_not_expose_password_in_output(self):
        serializer = PasswordResetConfirmSerializer(
            data={
                "uidb64": "encoded-user-id",
                "token": "reset-token",
                "password": "SecurePass123!",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("password", serializer.data)

    def test_two_factor_code_serializer_requires_six_digits(self):
        for value in ("12345", "1234567", "12a456"):
            with self.subTest(value=value):
                serializer = TwoFactorCodeSerializer(data={"code": value})
                self.assertFalse(serializer.is_valid())
                self.assertIn("code", serializer.errors)

        valid_serializer = TwoFactorCodeSerializer(data={"code": "012345"})
        self.assertTrue(valid_serializer.is_valid(), valid_serializer.errors)
