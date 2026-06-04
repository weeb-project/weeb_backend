# Connexion avec le frontend local

Le backend autorise les appels depuis un frontend local via `django-cors-headers`.

La dépendance est ajoutée dans `requirements.txt` :

```text
django-cors-headers
```

Dans `weeb_backend/settings.py`, l'application et le middleware sont activés :

```python
INSTALLED_APPS = [
    ...
    'corsheaders',
    ...
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    ...
]
```

Les origines locales autorisées par défaut sont :

```text
http://localhost:3000
http://127.0.0.1:3000
http://localhost:5173
http://127.0.0.1:5173
```

Elles peuvent être remplacées dans `.env` avec :

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`CORS_ALLOW_CREDENTIALS = True` est activé pour permettre au navigateur d'accepter les cookies définis par le backend, notamment le cookie `refresh_token`.

Dans le repo frontend, une variable d'environnement doit pointer vers l'API backend locale :

```env
VITE_API_URL=http://localhost:8000
```

Utiliser le même host logique partout en local. Par exemple, si le frontend appelle
`localhost:8000`, éviter d'appeler ensuite `127.0.0.1:8000`, car le cookie
`refresh_token` peut ne pas être renvoyé.

Les routes backend utilisées par le frontend sont :

```text
POST /users/register/
POST /users/login/
POST /users/logout/
POST /users/token/refresh/
POST /users/password-reset/request/
POST /users/password-reset/confirm/
GET /articles/
GET /articles/:slug/
POST /articles/
PUT /articles/:slug/
PATCH /articles/:slug/
DELETE /articles/:slug/
POST /contact/
```

`POST /users/register/` crée un compte en attente de validation administrateur.
Cette route ne connecte pas automatiquement l'utilisateur : elle ne renvoie pas
d'access token et ne pose pas de cookie `refresh_token`. Après inscription, le
frontend doit afficher le message de succès et inviter l'utilisateur à attendre
la validation du compte.

`POST /users/logout/` supprime le cookie HttpOnly `refresh_token`. Le frontend
doit aussi appeler cette route avec les credentials/cookies activés, sinon le
navigateur peut ignorer le `Set-Cookie` qui expire le cookie :

```js
withCredentials: true
```

`POST /users/token/refresh/` lit le refresh token depuis le cookie HttpOnly
`refresh_token`. Le frontend doit appeler cette route avec les credentials/cookies
activés, sans body obligatoire :

```text
withCredentials: true
```

En cas de succès, le backend renvoie :

```json
{
  "access": "..."
}
```

Si le cookie est absent, invalide ou expiré, la route renvoie `401`.

## Rôle du frontend

Le frontend gère l'accès aux pages visibles par l'utilisateur.

Si un utilisateur n'est pas connecté, il doit uniquement pouvoir accéder aux pages :

```text
/
/contact
/login
/signup
/blog
/blog/:id
```

Toutes les autres pages doivent rediriger vers :

```text
/login
```

Le frontend contrôle la navigation, mais la vraie sécurité doit toujours être assurée côté backend.
