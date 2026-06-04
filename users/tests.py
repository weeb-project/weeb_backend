from django.core import mail
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import CustomTokenObtainPairSerializer, UserRegisterSerializer


class CookieTokenRefreshTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('token_refresh')
        self.user = CustomUser.objects.create_user(
            email='user@example.com',
            password='InitialPass123!',
        )

    def test_refresh_reads_refresh_token_from_cookie(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies['refresh_token'] = str(refresh)

        response = self.client.post(self.url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_without_cookie_returns_401(self):
        response = self.client.post(self.url, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['message'], 'Refresh token manquant.')

    def test_refresh_with_invalid_cookie_returns_401(self):
        self.client.cookies['refresh_token'] = 'invalid-refresh-token'

        response = self.client.post(self.url, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['message'], 'Refresh token invalide ou expiré.')


class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('logout')

    def test_logout_deletes_refresh_token_cookie(self):
        self.client.cookies['refresh_token'] = 'refresh-token-value'

        response = self.client.post(self.url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Déconnexion réussie')
        self.assertIn('refresh_token', response.cookies)
        self.assertEqual(response.cookies['refresh_token'].value, '')
        self.assertEqual(response.cookies['refresh_token']['max-age'], 0)
        self.assertEqual(response.cookies['refresh_token']['path'], '/')
        self.assertEqual(
            response.cookies['refresh_token']['samesite'],
            settings.REFRESH_TOKEN_COOKIE_SAMESITE
        )


class UserRegisterSerializerTests(TestCase):
    def test_duplicate_email_returns_custom_error(self):
        CustomUser.objects.create_user(
            email='user@example.com',
            password='InitialPass123!',
        )
        serializer = UserRegisterSerializer(data={
            'email': 'user@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Jane',
            'last_name': 'Doe',
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['error_code'][0], 'EMAIL_ALREADY_EXISTS')
        self.assertEqual(serializer.errors['message'][0], 'Cet email existe déjà')

    def test_register_normalizes_email_case(self):
        serializer = UserRegisterSerializer(data={
            'email': 'User@Example.COM',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Jane',
            'last_name': 'Doe',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.email, 'user@example.com')

    def test_duplicate_email_with_different_case_returns_custom_error(self):
        CustomUser.objects.create_user(
            email='user@example.com',
            password='InitialPass123!',
        )
        serializer = UserRegisterSerializer(data={
            'email': 'User@Example.COM',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Jane',
            'last_name': 'Doe',
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['error_code'][0], 'EMAIL_ALREADY_EXISTS')
        self.assertEqual(serializer.errors['message'][0], 'Cet email existe déjà')


class LoginSerializerTests(TestCase):
    def test_login_accepts_email_with_different_case(self):
        CustomUser.objects.create_user(
            email='user@example.com',
            password='InitialPass123!',
        )
        serializer = CustomTokenObtainPairSerializer(data={
            'email': 'User@Example.COM',
            'password': 'InitialPass123!',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn('access', serializer.validated_data)

    def test_invalid_credentials_return_custom_error(self):
        serializer = CustomTokenObtainPairSerializer(data={
            'email': 'unknown@example.com',
            'password': 'WrongPass123!',
        })

        with self.assertRaises(AuthenticationFailed) as context:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(context.exception.detail['error_code'], 'INVALID_CREDENTIALS')
        self.assertEqual(context.exception.detail['message'], 'Email ou mot de passe incorrect')


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('login')

    def test_login_accepts_email_with_different_case(self):
        CustomUser.objects.create_user(
            email='user@example.com',
            password='InitialPass123!',
        )

        response = self.client.post(self.url, {
            'email': 'User@Example.COM',
            'password': 'InitialPass123!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'user@example.com')
        self.assertIn('access', response.data)
        self.assertIn('refresh_token', response.cookies)

    def test_login_returns_authenticated_user_data(self):
        user = CustomUser.objects.create_user(
            email='user@example.com',
            password='InitialPass123!',
            first_name='Jane',
            last_name='Doe',
        )

        response = self.client.post(self.url, {
            'email': 'user@example.com',
            'password': 'InitialPass123!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['id'], str(user.public_id))
        self.assertEqual(response.data['user']['email'], 'user@example.com')
        self.assertEqual(response.data['user']['first_name'], 'Jane')
        self.assertEqual(response.data['user']['last_name'], 'Doe')
        self.assertFalse(response.data['user']['is_staff'])
        self.assertTrue(response.data['user']['is_active'])
        self.assertIn('access', response.data)
        self.assertIn('refresh_token', response.cookies)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='Weeb <no-reply@example.com>',
    FRONTEND_URL='https://front.example.com',
)
class PasswordResetEmailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('password-reset-request')

    def test_password_reset_request_sends_email_with_reset_link(self):
        user = CustomUser.objects.create_user(
            email='user@example.com',
            password='InitialPass123!',
        )

        response = self.client.post(self.url, {'email': user.email}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])
        self.assertEqual(mail.outbox[0].from_email, 'Weeb <no-reply@example.com>')
        self.assertIn('Réinitialisation de votre mot de passe', mail.outbox[0].subject)
        self.assertIn('https://front.example.com/reset-password?uidb64=', mail.outbox[0].body)
        self.assertIn('&token=', mail.outbox[0].body)

    def test_password_reset_request_keeps_generic_response_for_unknown_email(self):
        response = self.client.post(
            self.url,
            {'email': 'unknown@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn('Si un compte est associé à cet email', response.data['message'])
