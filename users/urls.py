from django.urls import path

from users.views import (
    CookieTokenRefreshView,
    CurrentUserArticleListView,
    CurrentUserFavoriteArticleListView,
    CurrentUserView,
    CustomTokenObtainPairView,
    EmailChangeConfirmView,
    LogoutView,
    PasswordResetConfirmView,
    RegisterView,
    RequestPasswordResetEmailView,
    TwoFactorConfirmView,
    TwoFactorDisableView,
    TwoFactorLoginVerifyView,
    TwoFactorSetupView,
)

urlpatterns = [
    # Current user
    path('', CurrentUserView.as_view(), name='current_user'),
    path('me/articles/', CurrentUserArticleListView.as_view(), name='current_user_articles'),
    path('me/favorites/', CurrentUserFavoriteArticleListView.as_view(), name='current_user_favorite_articles'),
    path('email-change/confirm/', EmailChangeConfirmView.as_view(), name='email_change_confirm'),

    # Sign Up
    path('register/', RegisterView.as_view(), name='register'),

    # Sign In
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),

    # Sign Out
    path('logout/', LogoutView.as_view(), name='logout'),

    # Refresh token
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),

    # Two-factor authentication
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='two_factor_setup'),
    path('2fa/confirm/', TwoFactorConfirmView.as_view(), name='two_factor_confirm'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='two_factor_disable'),
    path('2fa/verify-login/', TwoFactorLoginVerifyView.as_view(), name='two_factor_verify_login'),

    # Password Reset
    path('password-reset/request/', RequestPasswordResetEmailView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
