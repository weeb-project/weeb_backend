from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

from contact.serializers import ContactMessageSerializer


class ContactFormView(CreateAPIView):
    """Vue publique pour créer un message de contact via POST."""
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "contact"
