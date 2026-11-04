# Intégration continue du backend

Le workflow `.github/workflows/ci.yml` vérifie automatiquement le backend à
chaque push et à chaque Pull Request vers `dev` ou `main`. Il publie les images
validées après une fusion dans `dev` ou `main`. Après la publication du staging,
il appelle le Deploy Hook Render afin de télécharger la nouvelle image.

## Enchaînement

```text
Push ou Pull Request
        ↓
PostgreSQL temporaire
        ↓
Construction de l'image Docker
        ↓
Vérification de Django
        ↓
Vérification des migrations
        ↓
Tests Django dans l'image
```

Une étape en échec arrête le job et rend la CI rouge. Le futur déploiement
dépendra de ce résultat afin qu'une version invalide ne puisse pas être mise en
ligne.

Après la réussite de tous les contrôles, un push sur `dev` ou `main` publie
exactement l'image testée dans le dépôt Docker Hub
`projetggs/weeb-backend`. Une Pull Request ne publie jamais d'image.

## Base PostgreSQL temporaire

GitHub Actions démarre `postgres:16-alpine` uniquement pendant le workflow. La
base `weeb_ci` ne contient que les données créées par les migrations et les
tests. Elle est détruite automatiquement à la fin du job et n'utilise ni la base
Supabase staging ni la base de production.

Le service PostgreSQL de la CI n'utilise pas TLS. Django reçoit donc :

```env
DB_SSLMODE=disable
```

Les connexions Supabase conservent `require`, qui est la valeur par défaut dans
`settings.py`. Aucune modification des variables Render n'est nécessaire.

## Tests exécutés dans Docker

La CI construit une seule image à partir du `Dockerfile`, puis remplace sa
commande de démarrage pour exécuter successivement :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
```

Le `CMD` qui lance les migrations, `collectstatic` et Gunicorn reste réservé au
démarrage normal du backend. Les tests ne sont jamais exécutés au démarrage de
Render.

Cette organisation vérifie que le code et les tests fonctionnent dans le même
environnement Python que celui destiné au déploiement.

## Déclenchement

- chaque push déclenche la CI, quelle que soit la branche ;
- chaque Pull Request vers `dev` ou `main` déclenche également la CI ;
- deux exécutions concurrentes sur la même branche sont évitées : la plus
  ancienne est annulée lorsqu'un nouveau commit est poussé.

## Secrets

La CI n'utilise aucun secret de staging ou de production. Les identifiants
PostgreSQL définis dans le workflow sont temporaires et limités au runner GitHub.
La valeur `SECRET_KEY` utilisée pendant les tests n'est pas une clé de
production.

La publication dans Docker Hub utilise uniquement :

```text
DOCKERHUB_USERNAME   Variable GitHub contenant le namespace Docker Hub
DOCKERHUB_TOKEN      Secret GitHub disposant de la permission Repo Read & Write
```

Le token n'est jamais ajouté à l'image ou affiché dans les logs.

Le CD staging utilise également :

```text
RENDER_STAGING_DEPLOY_HOOK   Secret GitHub contenant l'URL privée du hook Render
```

Ce secret n'est appelé qu'après la publication réussie des tags du staging.

## Images publiées

La même image qui a passé les tests reçoit deux tags : un tag immuable avec le
SHA complet du commit et un tag correspondant à l'environnement.

```text
Push sur dev  → projetggs/weeb-backend:<sha>
             → projetggs/weeb-backend:staging

Push sur main → projetggs/weeb-backend:<sha>
             → projetggs/weeb-backend:production
```

Le tag par SHA permet d'identifier précisément une version et de revenir à une
image antérieure. Les tags `staging` et `production` indiquent la dernière image
validée pour chaque environnement.

## Déploiement du staging

Render staging utilise l'image `:staging`. Après sa publication, la CI appelle
le Deploy Hook avec une requête POST. Render exécute alors l'équivalent de
`Deploy latest reference` et télécharge la nouvelle valeur du tag `staging`.

Cette étape est configurée et doit être validée lors du prochain push fusionné
dans `dev`. Le contrôle automatique de `/health/` après le déploiement reste à
ajouter.

Voir [Pipeline Docker, CI et CD](PIPELINE_CICD.md) pour l'enchaînement complet.
