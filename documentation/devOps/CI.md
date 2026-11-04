# Intégration continue du backend

Le workflow `.github/workflows/ci.yml` vérifie automatiquement le backend à
chaque push et à chaque Pull Request vers `dev` ou `main`. Il n'effectue aucun
déploiement : le CD sera ajouté séparément lorsque le staging Docker aura été
validé.

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

## Suite prévue

Après validation du runtime Docker sur Render staging, un job de CD dépendra de
la réussite de cette CI. Render ne sera appelé que si la construction et tous
les tests passent.
