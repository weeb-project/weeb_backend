# Authentification et autorisations

Le projet utilise Django REST Framework avec une authentification JWT.

Dans `weeb_backend/settings.py`, toutes les routes API sont protégées par défaut :

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

Cela signifie que, par défaut, une route API demande un utilisateur connecté avec un token JWT valide.

## Routes publiques

Certaines routes doivent rester accessibles sans être connecté.

Dans `users/views.py`, on importe :

```python
from rest_framework.permissions import AllowAny
```

Puis on ajoute :

```python
permission_classes = [AllowAny]
```

sur les vues publiques suivantes :

```text
POST /users/login/
POST /users/logout/
POST /users/register/
POST /users/token/refresh/
POST /users/password-reset/request/
POST /users/password-reset/confirm/
GET /articles/
GET /articles/:slug/
```

Ces routes sont publiques parce qu'un utilisateur non connecté doit pouvoir :

- se connecter
- supprimer le cookie refresh_token lors de la déconnexion
- créer un compte
- demander un nouvel access token à partir d'un refresh token
- demander une réinitialisation de mot de passe
- confirmer une réinitialisation de mot de passe
- lire les articles

## Déconnexion

Le frontend doit appeler :

```text
POST /users/logout/
```

avec les credentials/cookies activés, puis supprimer son access token local.
L'endpoint renvoie un cookie `refresh_token` expiré pour empêcher une reconnexion
automatique via un refresh token encore présent dans le navigateur.

## Login

`POST /users/login/` renvoie l'access token dans le JSON et place le refresh token
dans un cookie sécurisé :

```text
refresh_token
HttpOnly=True
Secure=True en production HTTPS, False en local HTTP
SameSite=Strict
Max-Age=7 jours
```

Le frontend doit stocker l'access token côté application et envoyer :

```text
Authorization: Bearer <access_token>
```

sur les routes protégées.

En cas d'identifiants invalides, le login renvoie une erreur personnalisée :

```json
{
  "error_code": "INVALID_CREDENTIALS",
  "message": "Email ou mot de passe incorrect"
}
```

Si le compte existe mais n'a pas encore été validé par un administrateur :

```json
{
  "error_code": "ACCOUNT_PENDING_APPROVAL",
  "message": "Votre compte est en attente de validation par un administrateur"
}
```

## Register

`POST /users/register/` crée un compte inactif en attente de validation par un
administrateur. Cette route ne renvoie pas de token et ne pose pas de cookie
`refresh_token`.

Réponse succès :

```json
{
  "message": "Compte créé avec succès. Il doit être validé par un administrateur avant connexion.",
  "user": {
    "id": "4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86",
    "email": "newuser@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_staff": false,
    "is_active": false
  }
}
```

En cas d'email déjà utilisé à l'inscription :

```json
{
  "error_code": "EMAIL_ALREADY_EXISTS",
  "message": "Cet email existe déjà"
}
```

## Refresh token

La route existe :

```text
POST /users/token/refresh/
```

Elle lit le refresh token depuis le cookie HttpOnly `refresh_token`.
Le frontend doit appeler cette route avec les credentials/cookies activés, sans
envoyer le refresh token dans le body :

```text
withCredentials: true
```

En cas de succès, la réponse contient un nouvel access token :

```json
{
  "access": "..."
}
```

Si le cookie est absent, invalide ou expiré, la route renvoie une erreur `401`.

## Logique pour les futures routes

La règle générale est :

```text
Privé par défaut.
Public uniquement si la route déclare explicitement AllowAny.
```

Les routes articles suivent déjà cette règle.

```text
GET /articles/
GET /articles/:slug/
```

Les routes d'écriture sont protégées :

```text
POST /articles/
PUT /articles/:slug/
PATCH /articles/:slug/
DELETE /articles/:slug/
```

Le formulaire de contact est public :

```text
POST /contact/
```

Il utilise donc :

```python
permission_classes = [AllowAny]
```
