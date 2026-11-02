# Reset password par email

La demande de réinitialisation se fait en deux étapes :

```text
POST /users/password-reset/request/
POST /users/password-reset/confirm/
```

`POST /users/password-reset/request/` reçoit un email, génère un `uidb64` et un token Django, puis envoie un lien au frontend :

```text
{FRONTEND_URL}/reset-password?uidb64={uidb64}&token={token}
```

La réponse reste toujours générique, même si l'email n'existe pas, pour éviter l'énumération d'utilisateurs.

L'envoi est fait dans `users/views.py` avec `django.core.mail.send_mail`.

Le token est généré avec `django.contrib.auth.tokens.PasswordResetTokenGenerator`. Il dépend notamment de l'état courant de l'utilisateur et devient invalide après changement du mot de passe.

Sa durée de validité est configurée explicitement dans `weeb_backend/settings.py` :

```python
PASSWORD_RESET_TIMEOUT = 60 * 60 * 2
```

Les liens de reset expirent donc au bout de 2 heures.

Le contenu envoyé contient :

- un sujet de réinitialisation
- un court message explicatif
- le lien de reset contenant `uidb64` et `token`
- une phrase indiquant d'ignorer l'email si la demande ne vient pas de l'utilisateur

En cas d'échec SMTP, l'erreur est loggée côté serveur, mais la réponse API reste générique pour ne pas révéler si l'email existe.

## Rate limiting

Les endpoints de reset password sont publics, mais protégés par les throttles DRF :

```text
POST /users/password-reset/request/  -> 5/hour
POST /users/password-reset/confirm/  -> 10/hour
```

Scopes utilisés dans `users/views.py` :

```python
throttle_scope = "password_reset_request"
throttle_scope = "password_reset_confirm"
```

Quand la limite est dépassée, l'API renvoie :

```http
429 Too Many Requests
```

Cette protection limite le spam d'emails de réinitialisation et les tentatives répétées sur les tokens de reset.

## Configuration email

La configuration d'envoi est dans `weeb_backend/settings.py` via les variables :

```text
EMAIL_BACKEND
EMAIL_HOST
EMAIL_PORT
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
EMAIL_USE_TLS
EMAIL_USE_SSL
DEFAULT_FROM_EMAIL
SUPPORT_EMAIL
FRONTEND_URL
```

Par défaut en local, `EMAIL_BACKEND` utilise `django.core.mail.backends.console.EmailBackend`.
Cette même configuration email est aussi utilisée pour les notifications de sécurité
envoyées après changement d'email ou de mot de passe depuis le profil utilisateur.
La notification de changement de mot de passe contient un lien direct de reset
password vers `{FRONTEND_URL}/reset-password?uidb64=...&token=...`.
Les emails incluent aussi une version HTML afin d'afficher ce lien derrière un
texte cliquable, tout en gardant l'URL complète dans la version texte fallback.

Pour envoyer de vrais emails via Gmail SMTP, les variables attendues dans `.env` sont :

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=adresse-gmail-du-projet@gmail.com
EMAIL_HOST_PASSWORD=mot-de-passe-application-google
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=Weeb <adresse-gmail-du-projet@gmail.com>
SUPPORT_EMAIL=projet.ggs@gmail.com
```

`EMAIL_HOST_PASSWORD` doit être un mot de passe d'application Google, pas le mot de passe normal du compte Gmail.

Ces valeurs ne doivent jamais être commit dans Git. Elles restent uniquement dans le fichier `.env` local ou dans les variables d'environnement de production.

## Test SMTP

Pour tester l'envoi SMTP depuis Django :

```bash
python3 manage.py shell
```

Puis :

```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    "Test SMTP Weeb",
    "Si tu reçois ce mail, Gmail SMTP fonctionne.",
    settings.DEFAULT_FROM_EMAIL,
    ["adresse-de-test@example.com"],
    fail_silently=False,
)
```

Si la commande retourne `1`, l'email a été accepté par le serveur SMTP.

Sur macOS, si Python retourne une erreur de certificat SSL, il faut utiliser les certificats du virtualenv :

```bash
source .venv/bin/activate
python3 -m pip install --upgrade certifi
export SSL_CERT_FILE=$(python3 -m certifi)
```

## URL frontend

`FRONTEND_URL` doit pointer vers l'application frontend qui affiche le formulaire de nouveau mot de passe.

En local, avec un frontend lancé séparément :

```env
FRONTEND_URL=http://localhost:3000
```

ou, pour Vite :

```env
FRONTEND_URL=http://localhost:5173
```

Le frontend doit avoir une route `/reset-password` qui lit les paramètres `uidb64` et `token`, puis appelle :

```text
POST /users/password-reset/confirm/
```

avec :

```json
{
  "uidb64": "...",
  "token": "...",
  "password": "NouveauMotDePasse123!"
}
```

En production, `FRONTEND_URL` devra être remplacé par l'URL publique du frontend.
