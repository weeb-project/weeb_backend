# Connecter un frontend au backend de staging

Le backend commun de staging est disponible à cette adresse :

```text
https://weeb-backend-staging.onrender.com
```

## Fonctionnement du staging

Le service `weeb-backend-staging` sur Render est connecté à la branche `dev` du dépôt backend. Render redéploie automatiquement le backend après chaque nouveau commit fusionné dans `dev`.

Le cycle de travail du backend est donc :

```text
branche de travail → Pull Request vers dev → fusion dans dev → déploiement Render
```

Une modification présente uniquement sur une branche de travail n'est pas encore
disponible sur le staging. Après une fusion, vérifier le statut du déploiement
dans Render avant de tester la fonctionnalité depuis un frontend.

La branche `main` n'est pas utilisée par ce service de staging. Elle servira au
backend de production lorsque celui-ci sera créé.

## Configuration du frontend

À la racine du projet frontend, créer un fichier `.env.production` contenant
l'URL du backend Render :

```env
VITE_API_URL=https://weeb-backend-staging.onrender.com
```

Ne pas ajouter `/api`, `/users`, `/articles` ou de `/` final à cette URL.
Vite charge automatiquement `.env.production` lors de `npm run build`. Les
variables `VITE_*` sont publiques et intégrées au frontend pendant ce build. Il
faut donc reconstruire et redéployer le frontend après chaque modification.

Pour développer avec le backend Django local, créer séparément un fichier
`.env.local` non partagé :

```env
VITE_API_URL=http://localhost:8000
```

Vérifier que `.env.local` est ignoré par Git. Le fichier `.env.production` peut
être versionné : l'URL publique du backend n'est pas un secret.

Le frontend utilise ainsi le backend local avec `npm run dev`, puis le backend
Render lors du build destiné à GitHub Pages ou Vercel.

Avec Axios, utiliser une instance commune qui transmet les cookies :

```js
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
});

export default api;
```

Tous les appels API doivent utiliser cette instance, particulièrement :

```text
POST /users/login/
POST /users/logout/
POST /users/token/refresh/
```

Avec `fetch`, ajouter cette option à chaque appel concerné :

```js
fetch(url, {
  credentials: "include",
});
```

## Autorisation du frontend dans Render

Après le déploiement du frontend, transmettre son URL publique au responsable du
backend. Celui-ci doit ajouter son origine à `CORS_ALLOWED_ORIGINS` dans Render :

```env
CORS_ALLOWED_ORIGINS=https://weeb-kappa.vercel.app,https://front-2.vercel.app,https://front-3.vercel.app
```

Une origine contient uniquement le protocole et le domaine : aucun chemin et
aucun `/` final. Le premier frontend validé utilise actuellement
`https://weeb-kappa.vercel.app`.

Le backend de staging utilise aussi :

```env
REFRESH_TOKEN_COOKIE_SECURE=True
REFRESH_TOKEN_COOKIE_SAMESITE=None
```

## Vérifications après déploiement

1. Ouvrir `https://weeb-backend-staging.onrender.com/health/` et vérifier la
   réponse `{"status": "ok"}`.
2. Ouvrir le frontend et vérifier le chargement de la liste des articles.
3. Tester la connexion avec un compte de staging.
4. Vérifier l'accès au profil et aux autres routes protégées.
5. Attendre l'expiration de l'access token puis vérifier son renouvellement.
6. Tester la déconnexion.

Dans les outils de développement du navigateur, les requêtes doivent partir vers
`https://weeb-backend-staging.onrender.com`. Une erreur CORS signifie généralement
que l'origine exacte du frontend manque dans la variable Render.

## Particularités actuelles du staging

- Le service Render Free se met en veille après une période d'inactivité. La
  première requête peut donc être lente.
- Les emails transactionnels sont envoyés avec l'API HTTPS Brevo. Les secrets
  Brevo restent uniquement dans les variables d'environnement Render.
- Les liens de reset password et de confirmation d'email ouvrent actuellement le
  frontend défini par `FRONTEND_URL`. La sélection du frontend demandeur sera
  ajoutée séparément avec une liste d'URL autorisées.
