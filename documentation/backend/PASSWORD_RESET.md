# Reset password par email

La demande de réinitialisation se fait en deux étapes :

```text
POST /users/password-reset/request/
POST /users/password-reset/confirm/
```

`POST /users/password-reset/request/` reçoit un email :

```json
{
  "email": "utilisateur@example.com"
}
```

Le backend génère un `uidb64` et un token Django, puis envoie un lien vers une
page HTML commune servie directement par Django :

```text
https://backend.example/users/password-reset/form/?uidb64={uidb64}&token={token}
```

Cette page utilise un formulaire protégé par CSRF, applique les mêmes règles de
mot de passe que l'API et ne dépend d'aucun des trois frontends.

La réponse reste toujours générique, même si l'email n'existe pas, pour éviter l'énumération d'utilisateurs.

L'envoi passe par `users/email_service.py`. Sur Render, ce service appelle l'API
HTTPS transactionnelle de Brevo. Sans clé Brevo, il utilise le backend email
Django, notamment le backend console en local.

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

En cas d'échec d'envoi, l'erreur est loggée côté serveur, mais la réponse API
reste générique pour ne pas révéler si l'email existe.

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
BREVO_API_KEY
BREVO_SENDER_EMAIL
BREVO_SENDER_NAME
BREVO_API_TIMEOUT
SUPPORT_EMAIL
FRONTEND_URL
```

Sur Render, `BREVO_API_KEY` active automatiquement l'envoi par l'API HTTPS
Brevo. `BREVO_SENDER_EMAIL` doit correspondre exactement à un expéditeur vérifié
dans Brevo. Le timeout empêche un appel externe de bloquer durablement un worker
Gunicorn.

```env
BREVO_API_KEY=cle-secrete-configuree-uniquement-dans-render
BREVO_SENDER_EMAIL=expediteur-verifie@example.com
BREVO_SENDER_NAME=Weeb
BREVO_API_TIMEOUT=10
```

En local, la clé reste vide et le backend console, utilisé par défaut, affiche le
contenu des emails dans le terminal :

```env
BREVO_API_KEY=
```

Cette même configuration est utilisée pour les notifications de sécurité
envoyées après changement d'email ou de mot de passe depuis le profil utilisateur.
La notification de changement de mot de passe contient un lien direct de reset
password vers `{FRONTEND_URL}/reset-password?uidb64=...&token=...`.
Les emails incluent aussi une version HTML afin d'afficher ce lien derrière un
texte cliquable, tout en gardant l'URL complète dans la version texte fallback.

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

`FRONTEND_URL` reste utilisé par les autres liens de sécurité, notamment la
confirmation de changement d'adresse email. Le lien principal de reset password
est construit avec le domaine du backend qui reçoit la demande.

L'endpoint JSON `POST /users/password-reset/confirm/` reste disponible pour la
compatibilité avec les frontends existants.
