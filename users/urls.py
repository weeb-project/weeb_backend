from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import CustomTokenObtainPairView, LogoutView, RegisterView, PasswordResetConfirmView, \
    RequestPasswordResetEmailView

urlpatterns = [
    # Sign Up
    path('register/', RegisterView.as_view(), name='register'),

    # Sign In
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),

    # Sign Out
    path('logout/', LogoutView.as_view(), name='logout'),

    # Refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Password Reset
    path('password-reset/request/', RequestPasswordResetEmailView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
