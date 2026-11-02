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
        'email_change_confirm': '10/hour',
        'two_factor_verify': '10/minute',
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

La vérification est insensible à la casse : `user@example.com` et
`User@example.com` sont considérés comme le même email. L'API renvoie donc une
erreur `400` contrôlée plutôt qu'une erreur serveur.

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

La route utilisateur courant est protégée :

```text
GET /users/
Authorization: Bearer <access_token>
```

Le profil de l'utilisateur connecté se modifie sur la même route :

```text
PATCH /users/
Authorization: Bearer <access_token>
```

Changement de nom/prénom :

```json
{
  "first_name": "John",
  "last_name": "Doe"
}
```

Changement d'email :

```json
{
  "email": "new-email@example.com"
}
```

Cette requête ne modifie pas immédiatement `user.email`. Elle envoie un email de
confirmation à l'adresse email actuelle du compte. Cet email contient :

- un lien de confirmation vers le frontend
- un lien de reset password si l'utilisateur n'est pas à l'origine de la demande

Réponse :

```json
{
  "message": "Demande de changement d'email envoyée. Vérifiez votre adresse email actuelle pour confirmer.",
  "email_change_requested": true,
  "pending_email": "new-email@example.com",
  "user": {
    "email": "current-email@example.com"
  }
}
```

Après clic sur le lien reçu, le frontend doit afficher un champ `current_password`
et appeler :

```text
POST /users/email-change/confirm/
```

```json
{
  "token": "...",
  "current_password": "MotDePasseActuel123!"
}
```

Changement de mot de passe :

```json
{
  "current_password": "MotDePasseActuel123!",
  "password": "NouveauMotDePasse123!",
  "password_confirm": "NouveauMotDePasse123!"
}
```

L'email est normalisé en minuscules et vérifié de manière insensible à la casse.
Le mot de passe actuel est obligatoire pour confirmer le changement d'email ou
changer le mot de passe.
Le nouveau mot de passe applique les mêmes règles que l'inscription et le reset
password.

Notifications email envoyées après mise à jour du profil :

- changement de nom/prénom : aucun email envoyé
- demande de changement d'email : email envoyé à l'adresse actuelle avec lien de confirmation et lien de reset password
- confirmation du changement d'email : email envoyé à la nouvelle adresse
- changement de mot de passe : email de sécurité envoyé à l'adresse email du compte avant modification, avec un lien direct de reset password si l'utilisateur n'est pas à l'origine du changement

Ces notifications utilisent la configuration email Django existante
(`EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`, `FRONTEND_URL`, `SUPPORT_EMAIL`,
variables SMTP). Si l'envoi SMTP échoue, la modification du profil reste validée
et l'erreur est loggée côté serveur.
`SUPPORT_EMAIL` vaut `projet.ggs@gmail.com` par défaut et est affiché dans les
emails de sécurité lorsque l'utilisateur n'est pas à l'origine de l'action.
Les emails sont envoyés avec une version texte et une version HTML. Dans la
version HTML, les URLs sont placées derrière des liens lisibles comme
`confirmez le changement d'email` ou `choisissez immédiatement un nouveau mot de
passe`. La version texte garde l'URL complète en fallback.

Erreurs utiles pour le profil :

```text
EMAIL_ALREADY_EXISTS
CURRENT_PASSWORD_REQUIRED
INVALID_CURRENT_PASSWORD
INVALID_EMAIL_CHANGE_TOKEN
EMAIL_CHANGE_TOKEN_EXPIRED
EMAIL_CHANGE_TOKEN_STALE
PASSWORD_FIELDS_REQUIRED
PASSWORD_MISMATCH
WEAK_PASSWORD
```

Les routes d'administration utilisateur sont protégées par `IsAdminUser`.
Elles demandent donc un utilisateur connecté avec `is_staff=true` :

```text
GET /api/admin/users/
GET /api/admin/users/:id/
PATCH /api/admin/users/:id/
Authorization: Bearer <access_token>
```

`PATCH /api/admin/users/:id/` accepte les champs `first_name`, `last_name`,
`is_active` et `is_staff`. Il permet notamment de valider un compte en attente
avec `{"is_active": true}`. Un admin ne peut pas désactiver son propre compte ou
retirer ses propres droits admin via cette route.

Les routes d'écriture sont protégées :

```text
POST /articles/
PUT /articles/:slug/
PATCH /articles/:slug/
DELETE /articles/:slug/
```

Pour `PUT`, `PATCH` et `DELETE`, l'utilisateur doit être le propriétaire de
l'article ou un admin actif (`is_staff=true`).

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
| `POST /users/email-change/confirm/` | `email_change_confirm` | `10/hour` |
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
