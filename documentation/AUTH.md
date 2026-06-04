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
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'login': '5/minute',
        'register': '5/hour',
        'token_refresh': '30/minute',
        'password_reset_request': '5/hour',
        'password_reset_confirm': '10/hour',
        'contact': '5/hour',
    },
}
```

Cela signifie que, par défaut, une route API demande un utilisateur connecté avec un token JWT valide.

SimpleJWT est configuré pour révoquer les refresh tokens côté serveur :

```python
INSTALLED_APPS = [
    # ...
    'rest_framework_simplejwt.token_blacklist',
]

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    # ...
}
```

Après activation de `token_blacklist`, appliquer les migrations :

```bash
python3 manage.py migrate
```

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
- révoquer puis supprimer le cookie refresh_token lors de la déconnexion
- créer un compte
- demander un nouvel access token à partir d'un refresh token
- demander une réinitialisation de mot de passe
- confirmer une réinitialisation de mot de passe
- lire les articles

Les réponses publiques des articles gardent un auteur minimal : `id`,
`first_name` et `last_name`. Elles ne renvoient pas `email`, `is_staff` ou
`is_active`.

## Déconnexion

Le frontend doit appeler :

```text
POST /users/logout/
```

avec les credentials/cookies activés, puis supprimer son access token local.
L'endpoint blackliste le refresh token présent dans le cookie, puis renvoie un
cookie `refresh_token` expiré pour empêcher une reconnexion automatique.

Si le cookie est absent, invalide, expiré ou déjà blacklisté, la déconnexion
reste idempotente : l'endpoint répond `200` et supprime quand même le cookie.

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

L'email est normalisé en minuscules et l'unicité est vérifiée de manière
insensible à la casse. `user@example.com` et `USER@example.com` ne peuvent donc
pas créer deux comptes différents.

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

Avec `ROTATE_REFRESH_TOKENS=True`, la route pose aussi un nouveau cookie
HttpOnly `refresh_token` et blackliste l'ancien refresh token. Le nouveau
refresh token n'est pas renvoyé dans le JSON.

Si le cookie est absent, invalide, expiré ou blacklisté, la route renvoie une
erreur `401`. Quand un cookie invalide est présenté, l'endpoint renvoie aussi un
cookie `refresh_token` expiré.

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

## Rate limiting des routes publiques sensibles

Les routes publiques sensibles utilisent les throttles DRF pour limiter les abus :

```python
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
throttle_scope = "nom_du_scope"
```

`AnonRateThrottle` applique une limite générale aux requêtes anonymes.
`ScopedRateThrottle` applique une limite spécifique à chaque endpoint sensible.

Limites configurées :

| Route | Scope | Limite |
|-------|-------|--------|
| `POST /users/login/` | `login` | `5/minute` |
| `POST /users/register/` | `register` | `5/hour` |
| `POST /users/token/refresh/` | `token_refresh` | `30/minute` |
| `POST /users/password-reset/request/` | `password_reset_request` | `5/hour` |
| `POST /users/password-reset/confirm/` | `password_reset_confirm` | `10/hour` |
| `POST /contact/` | `contact` | `5/hour` |

Quand une limite est dépassée, DRF renvoie :

```http
429 Too Many Requests
```

Objectif :

- limiter les tentatives de brute force sur le login
- limiter la création massive de comptes
- limiter le spam d'emails de reset password
- limiter les abus sur le renouvellement de token
- limiter le spam du formulaire de contact
