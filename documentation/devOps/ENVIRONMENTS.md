# Environnements staging et production

Le projet utilise deux environnements backend complètement séparés. Ils ne
partagent ni service Render, ni base Supabase, ni secrets.

| Environnement | Branche backend | Service Render | Runtime | Base de données |
| --- | --- | --- | --- | --- |
| Staging | `dev` | `weeb-backend-staging` | Docker | Supabase staging |
| Production | `main` | `weeb-backend-production` | Python, migration Docker à venir | Supabase production |

```text
feature/* → dev  → Render staging    → Supabase staging
               validation
            dev → main → Render production → Supabase production
```

## Backend de staging

Le staging sert à tester les changements avant leur mise en production :

```text
https://weeb-backend-staging.onrender.com
```

Une fusion dans `dev` déclenche actuellement son déploiement automatique. Render
construit le `Dockerfile` du dépôt puis démarre le conteneur avec son `CMD`. Les
comptes et les données créés dans cet environnement sont des données de test.

Le health check Render utilise :

```text
/health/
```

Le runtime Docker du staging a été validé le 4 novembre 2026 avec les migrations,
la collecte des fichiers statiques, le démarrage de Gunicorn et les principaux
parcours fonctionnels.

## Backend de production

La production utilise l'adresse suivante :

```text
https://weeb-backend-production.onrender.com
```

Le service est connecté uniquement à `main`. Une fonctionnalité doit être
validée sur le staging avant d'être fusionnée de `dev` vers `main`.

La production utilise encore temporairement le runtime Python natif de Render.
Elle sera migrée vers Docker uniquement après validation du pipeline de
déploiement continu sur le staging.

Les variables `DB_*` du service de production doivent toujours pointer vers le
projet Supabase de production. Elles ne doivent jamais reprendre les
identifiants du staging.

## Choisir le backend depuis un frontend Vite

La variable `VITE_API_URL` détermine le backend appelé par le frontend. Elle est
intégrée aux fichiers JavaScript pendant le build : la modifier ne change pas un
frontend déjà construit. Il faut toujours reconstruire et redéployer le
frontend.

### Développement local

Pour utiliser Django en local, créer un fichier `.env.local` non versionné :

```env
VITE_API_URL=http://localhost:8000
```

### Build connecté au staging

Créer un fichier `.env.staging` :

```env
VITE_API_URL=https://weeb-backend-staging.onrender.com
```

Puis construire avec le mode staging :

```bash
npm run build -- --mode staging
```

Il est également possible d'ajouter un script dédié dans `package.json` :

```json
{
  "scripts": {
    "build:staging": "vite build --mode staging"
  }
}
```

Le build de staging se lance alors avec :

```bash
npm run build:staging
```

### Build connecté à la production

Le fichier `.env.production` doit contenir :

```env
VITE_API_URL=https://weeb-backend-production.onrender.com
```

Le build standard utilise ce fichier :

```bash
npm run build
```

## Configuration avec Vercel

Le projet Vercel utilise les environnements gratuits intégrés. Aucun
environnement personnalisé payant n'est nécessaire :

| Branche frontend | Environnement Vercel | Backend appelé |
| --- | --- | --- |
| `dev` | Preview | Render staging |
| `main` | Production | Render production |

Dans **Settings → Environments**, la branche suivie par Production doit être
`main`. Toutes les autres branches non assignées, dont `dev`, sont alors des
branches Preview.

Dans les variables d'environnement Vercel, créer deux valeurs de type
**Config**. Une URL `VITE_*` est publique et ne doit pas être enregistrée comme
un secret :

```text
Key: VITE_API_URL
Environment: Preview
Value: https://weeb-backend-staging.onrender.com
```

```text
Key: VITE_API_URL
Environment: Production
Value: https://weeb-backend-production.onrender.com
```

Un push sur `dev` crée automatiquement une Preview. Un push sur `main` crée un
déploiement Production. Après une modification de variable, il faut redéployer
l'environnement concerné afin que Vite intègre la nouvelle valeur pendant le
build.

Un même déploiement frontend ne peut pas appeler alternativement staging et
production sans être reconstruit. Pour changer d'environnement, ouvrir l'URL
Vercel Production ou l'URL stable de la Preview associée à `dev`.

## CORS des deux backends

Chaque backend doit autoriser uniquement les origines des frontends qui
l'appellent. Les domaines sont séparés par des virgules, sans espace et sans
slash final.

Sur Render staging, utiliser les URLs stables des Previews associées aux
branches `dev` des trois frontends :

```env
CORS_ALLOWED_ORIGINS=https://preview-dev-front-1.vercel.app,https://preview-dev-front-2.vercel.app,https://preview-dev-front-3.vercel.app
```

Sur Render production, utiliser les domaines principaux associés aux branches
`main` :

```env
CORS_ALLOWED_ORIGINS=https://weeb-kappa.vercel.app,https://front-2.vercel.app,https://front-3.vercel.app
```

Une URL Preview propre à un commit peut changer au déploiement suivant. Pour le
CORS du staging, choisir l'alias stable fourni par Vercel pour la branche `dev`.
Une fois la Preview validée, retirer du CORS staging le domaine principal du
frontend Production : il n'a plus besoin d'appeler le staging.

## Vérifier l'environnement utilisé

Dans les outils de développement du navigateur, ouvrir l'onglet **Network** et
contrôler l'URL des requêtes :

```text
https://weeb-backend-staging.onrender.com/...    # staging
https://weeb-backend-production.onrender.com/... # production
```

Avant de réaliser une action destructive ou de créer des données, toujours
vérifier que le frontend appelle l'environnement attendu.

Le résultat attendu est :

```text
Frontend main → Vercel Production → Render production → Supabase production
Frontend dev  → Vercel Preview    → Render staging    → Supabase staging
```
