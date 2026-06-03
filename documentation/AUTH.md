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
POST /users/register/
POST /users/password-reset/request/
POST /users/password-reset/confirm/
```

Ces routes sont publiques parce qu'un utilisateur non connecté doit pouvoir :

- se connecter
- créer un compte
- demander une réinitialisation de mot de passe
- confirmer une réinitialisation de mot de passe

## Logique pour les futures routes

La règle générale est :

```text
Privé par défaut.
Public uniquement si la route déclare explicitement AllowAny.
```

Quand le blog/articles sera implémenté, les routes de lecture devront être publiques :

```text
GET /articles/
GET /articles/:slug/
```

Les routes d'écriture devront rester protégées :

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
