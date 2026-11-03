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

La branche `main` n'est pas utilisée par ce service. Elle alimente séparément le
service `weeb-backend-production`, connecté à la base Supabase de production.
Consulter la page [Environnements staging et production](ENVIRONMENTS.md) avant
de basculer un frontend d'un backend vers l'autre.

## Configuration du frontend

À la racine du projet frontend, créer un fichier `.env.staging` contenant l'URL
du backend Render :

```env
VITE_API_URL=https://weeb-backend-staging.onrender.com
```

Ne pas ajouter `/api`, `/users`, `/articles` ou de `/` final à cette URL.
Construire explicitement le frontend en mode staging :

```bash
npm run build -- --mode staging
```

Les variables `VITE_*` sont publiques et intégrées au frontend pendant ce
build. Il faut donc reconstruire et redéployer le frontend après chaque
modification.

Pour développer avec le backend Django local, créer séparément un fichier
`.env.local` non partagé :

```env
VITE_API_URL=http://localhost:8000
```

Vérifier que `.env.local` est ignoré par Git. Le fichier `.env.staging` peut être
versionné : l'URL publique du backend n'est pas un secret.

Le frontend utilise ainsi le backend local avec `npm run dev`, puis le backend
de staging lors du build réalisé avec `--mode staging`. Pour un déploiement
Vercel, la variable peut aussi être définie directement dans les paramètres du
projet Vercel.

Dans Vercel, configurer `VITE_API_URL` pour l'environnement **Preview** et
utiliser `dev` comme branche frontend de test :

```text
Branche frontend: dev
Environnement Vercel: Preview
VITE_API_URL: https://weeb-backend-staging.onrender.com
```

La branche `main` reste suivie par Vercel Production et utilise le backend
Render production. Aucun environnement Vercel personnalisé n'est nécessaire.

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

Après le déploiement Preview du frontend, transmettre son URL stable de branche
au responsable du backend. Celui-ci doit ajouter cette origine à
`CORS_ALLOWED_ORIGINS` sur le Render staging :

```env
CORS_ALLOWED_ORIGINS=https://preview-dev-front-1.vercel.app,https://preview-dev-front-2.vercel.app,https://preview-dev-front-3.vercel.app
```

Une origine contient uniquement le protocole et le domaine : aucun chemin et
aucun `/` final. Utiliser l'alias stable associé à `dev`, pas une URL propre à
un seul commit.

Le domaine principal tel que `https://weeb-kappa.vercel.app` appartient au
frontend Production. Une fois la Preview validée, il peut être retiré du CORS
staging. Il doit rester autorisé dans le CORS du Render production.

Le backend de staging utilise aussi :

```env
REFRESH_TOKEN_COOKIE_SECURE=True
REFRESH_TOKEN_COOKIE_SAMESITE=None
```

Chaque frontend demande un reset avec l'adresse email uniquement :

```js
await api.post("/users/password-reset/request/", {
  email,
});
```

Le lien reçu ouvre `/users/password-reset/form/` sur le backend Render. Django
sert une page HTML commune et sécurisée pour saisir le nouveau mot de passe. Les
frontends n'ont donc aucune redirection particulière à configurer pour le reset.

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
- Les liens de reset password ouvrent la page HTML commune servie par le backend.
  Les liens de confirmation de changement d'email utilisent encore le frontend
  défini par `FRONTEND_URL`.
