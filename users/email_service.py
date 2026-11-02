import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail


BREVO_EMAIL_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


class TransactionalEmailError(Exception):
    """Erreur rencontrée lors de l'envoi d'un email transactionnel."""


def _send_with_brevo(subject, message, recipient_email, html_message=None):
    if not settings.BREVO_SENDER_EMAIL:
        raise TransactionalEmailError(
            "BREVO_SENDER_EMAIL doit être configurée pour utiliser Brevo."
        )

    payload = {
        "sender": {
            "name": settings.BREVO_SENDER_NAME,
            "email": settings.BREVO_SENDER_EMAIL,
        },
        "to": [{"email": recipient_email}],
        "subject": subject,
    }
    if html_message:
        payload["htmlContent"] = html_message
    else:
        payload["textContent"] = message

    request = Request(
        BREVO_EMAIL_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=settings.BREVO_API_TIMEOUT) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise TransactionalEmailError(
            f"Brevo a refusé l'email (HTTP {exc.code}): {error_body}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise TransactionalEmailError(
            "Impossible de joindre l'API Brevo."
        ) from exc

    if not response_body:
        return None

    try:
        return json.loads(response_body)
    except json.JSONDecodeError:
        return None


def send_transactional_email(
    subject,
    message,
    recipient_email,
    html_message=None,
):
    """Envoie via l'API Brevo, ou via Django lorsque Brevo n'est pas configuré."""
    if settings.BREVO_API_KEY:
        return _send_with_brevo(
            subject=subject,
            message=message,
            recipient_email=recipient_email,
            html_message=html_message,
        )

    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
        html_message=html_message,
    )
