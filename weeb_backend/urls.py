"""
URL configuration for weeb_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import sentry_sdk
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

from users.views import AdminUserDetailView, AdminUserListView


def health_check(request):
    """Confirme que le processus Django est prêt à recevoir des requêtes."""
    return JsonResponse({'status': 'ok'})

def trigger_error(request):
    event_id = sentry_sdk.capture_message(
        "Test Sentry depuis Render staging",
        level="error",
    )
    sentry_sdk.flush(timeout=5)

    return JsonResponse({
        "event_id": str(event_id) if event_id else None,
    })

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('api/admin/users/<uuid:user_id>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('users/', include('users.urls')),
    path('articles/', include('blog.urls')),
    path('contact/', include('contact.urls')),
    path('sentry-debug/', trigger_error),
]
