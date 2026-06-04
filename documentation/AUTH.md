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

## Login et register

`POST /users/login/` et `POST /users/register/` renvoient l'access token dans le JSON
et placent le refresh token dans un cookie sécurisé :

```text
refresh_token
HttpOnly=True
Secure=True
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

En cas d'email déjà utilisé à l'inscription :

```json
{
  "error_code": "EMAIL_ALREADY_EXISTS",
  "message": "Cet email existe déjà"
}
```

La vérification est insensible à la casse : `user@example.com` et
`User@example.com` sont considérés comme le même email. L'API renvoie donc une
erreur `400` contrôlée plutôt qu'une erreur serveur.

## Refresh token

La route existe :

```text
POST /users/token/refresh/
```

Elle utilise actuellement la vue standard SimpleJWT `TokenRefreshView`.
Elle attend donc un refresh token dans le body JSON :

```json
{
  "refresh": "..."
}
```

Point d'attention : le login et le register stockent le refresh token dans un cookie
HttpOnly, qui n'est pas lisible par JavaScript. Si le frontend doit rafraîchir
automatiquement l'access token à partir du cookie, il faudra remplacer cette vue par
une vue custom qui lit `request.COOKIES["refresh_token"]`.

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

Quand le formulaire de contact sera implémenté, son endpoint devra être public :

```text
POST /contact/
```

Il devra donc utiliser :

```python
permission_classes = [AllowAny]
```
