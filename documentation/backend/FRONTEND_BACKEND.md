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
GET /users/
GET /api/admin/users/
GET /api/admin/users/:id/
PATCH /api/admin/users/:id/
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

## Reset password côté frontend

Le frontend intervient uniquement pour demander l'envoi de l'email :

```js
await api.post("/users/password-reset/request/", {
  email,
});
```

Après la réponse, afficher le message générique renvoyé par le backend. Ne pas
indiquer si l'adresse correspond réellement à un compte.

Le frontend ne doit pas construire de lien, transmettre `frontend_url`, lire
`uidb64` ou `token`, ni afficher le formulaire de nouveau mot de passe. L'email
Brevo contient un lien vers `/users/password-reset/form/`, une page HTML commune
servie directement par Django.

`POST /users/password-reset/confirm/` reste disponible uniquement pour la
compatibilité avec les anciennes implémentations. Il n'est pas nécessaire dans
le nouveau parcours frontend.

`GET /users/` renvoie l'utilisateur connecté. Cette route est protégée et doit
être appelée avec l'access token :

```text
Authorization: Bearer <access_token>
```

Les routes d'administration utilisateur sont réservées aux comptes avec
`is_staff=true`. Elles permettent au frontend admin de lister les comptes,
consulter un utilisateur et modifier ses champs administrables :

```text
GET /api/admin/users/
GET /api/admin/users/:id/
PATCH /api/admin/users/:id/
```

Exemple pour valider un compte en attente :

```json
{
  "is_active": true
}
```

`POST /users/register/` crée un compte en attente de validation administrateur.
Cette route ne connecte pas automatiquement l'utilisateur : elle ne renvoie pas
d'access token et ne pose pas de cookie `refresh_token`. Après inscription, le
frontend doit afficher le message de succès et inviter l'utilisateur à attendre
la validation du compte.

Pour les articles, un utilisateur actif peut modifier ou supprimer ses propres
publications. Un admin actif (`is_staff=true`) peut aussi modifier ou supprimer
une publication dont il n'est pas l'auteur via `PUT /articles/:slug/`,
`PATCH /articles/:slug/` ou `DELETE /articles/:slug/`.

`POST /users/logout/` blackliste le refresh token côté serveur, puis supprime le
cookie HttpOnly `refresh_token`. Le frontend doit aussi appeler cette route avec
les credentials/cookies activés, sinon le navigateur peut ignorer le `Set-Cookie`
qui expire le cookie :

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

Le backend pose aussi un nouveau cookie HttpOnly `refresh_token` et blackliste
l'ancien refresh token. Le nouveau refresh token n'est jamais renvoyé dans le
JSON.

Si le cookie est absent, invalide, expiré ou blacklisté, la route renvoie `401`.

### Renouvellement automatique de l'access token

L'access token a une durée de vie courte. Le frontend doit conserver l'access
token reçu au login et l'ajouter aux routes protégées :

```text
Authorization: Bearer <access_token>
```

Lorsqu'une route protégée renvoie `401`, le frontend doit tenter un refresh,
enregistrer le nouvel access token, puis rejouer la requête initiale. Il ne doit
rediriger vers `/login` que si le refresh échoue lui-même.

La rotation du refresh token impose de ne lancer qu'un seul refresh à la fois.
Si plusieurs requêtes expirent simultanément, le premier refresh remplace le
cookie et blackliste l'ancien token. Des refresh concurrents utilisant l'ancien
token recevraient alors `401` et pourraient provoquer une fausse déconnexion.

Exemple avec une promesse partagée et un intercepteur Axios :

```js
let refreshPromise = null;

function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = api
      .post("/users/token/refresh/")
      .then((response) => {
        setAccessToken(response.data.access);
        return response.data.access;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

api.interceptors.request.use((config) => {
  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const isRefreshRequest = request?.url?.includes("/users/token/refresh/");

    if (error.response?.status === 401 && !request._retry && !isRefreshRequest) {
      request._retry = true;

      try {
        const accessToken = await refreshAccessToken();
        request.headers.Authorization = `Bearer ${accessToken}`;
        return api(request);
      } catch (refreshError) {
        clearAuthentication();
        window.location.assign("/login");
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);
```

`getAccessToken`, `setAccessToken` et `clearAuthentication` représentent ici le
store d'authentification du frontend. Le refresh token reste inaccessible au
JavaScript, car il est stocké dans un cookie HttpOnly.

Le cycle attendu après expiration est :

```text
requête protégée       -> 401
token/refresh/          -> 200
requête initiale rejouée -> 200 ou 201
```

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
