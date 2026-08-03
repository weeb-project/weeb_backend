from django.urls import path

from users.views import (
    CookieTokenRefreshView,
    CurrentUserArticleListView,
    CurrentUserFavoriteArticleListView,
    CurrentUserView,
    CustomTokenObtainPairView,
    LogoutView,
    PasswordResetConfirmView,
    RegisterView,
    RequestPasswordResetEmailView,
)

urlpatterns = [
    # Current user
    path('', CurrentUserView.as_view(), name='current_user'),
    path('me/articles/', CurrentUserArticleListView.as_view(), name='current_user_articles'),
    path('me/favorites/', CurrentUserFavoriteArticleListView.as_view(), name='current_user_favorite_articles'),

    # Sign Up
    path('register/', RegisterView.as_view(), name='register'),

    # Sign In
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),

    # Sign Out
    path('logout/', LogoutView.as_view(), name='logout'),

    # Refresh token
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),

    # Password Reset
    path('password-reset/request/', RequestPasswordResetEmailView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
