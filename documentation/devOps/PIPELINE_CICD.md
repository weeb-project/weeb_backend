# Pipeline Docker, CI et CD

Cette page décrit le cycle complet du backend Weeb, depuis une modification du
code jusqu'à son exécution sur Render. Elle précise le rôle de GitHub Actions,
Docker, Docker Hub, Render et Supabase.

## Vue d'ensemble

```text
Développeur
    │
    │ push d'une branche et Pull Request
    ▼
GitHub
    │
    ▼
GitHub Actions
    ├── démarre un PostgreSQL temporaire
    ├── construit une image avec le Dockerfile
    ├── vérifie la configuration Django
    ├── vérifie les migrations
    └── exécute les tests dans l'image
            │
            ├── échec ──> arrêt du pipeline, aucune publication
            │
            └── succès après fusion dans dev ou main
                         │
                         ▼
                    Docker Hub
                    projetggs/weeb-backend
                         │
                         ├── tag immuable : <sha>
                         ├── dev  : staging
                         └── main : production
                                  │
                                  ▼
                       Deploy Hook Render
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
          Render staging                    Render production
          image validée                     image validée
                 │                                 │
                 ▼                                 ▼
          Supabase staging                  Supabase production
```

Le frontend n'est pas inclus dans cette image. Vercel construit séparément les
frontends et leur variable `VITE_API_URL` détermine le backend appelé.

## Responsabilité de chaque composant

| Composant | Responsabilité |
| --- | --- |
| GitHub | Héberger le code, les Pull Requests et les secrets du pipeline |
| GitHub Actions | Construire, contrôler, tester, publier et déclencher le déploiement |
| Docker | Fournir un environnement d'exécution reproductible pour Django |
| Docker Hub | Conserver les images testées et leurs versions |
| Render | Télécharger et exécuter une image avec les variables de l'environnement |
| Supabase | Fournir une base PostgreSQL distincte pour staging et production |
| Vercel | Construire et héberger les frontends indépendamment du backend |

## Ce que fait GitHub Actions

Le workflow est défini dans `.github/workflows/ci.yml`.

### Déclenchement

- chaque push construit et teste l'image ;
- chaque Pull Request vers `dev` ou `main` construit et teste l'image ;
- une Pull Request ne publie jamais d'image et ne déclenche jamais Render ;
- un push sur `dev` peut publier l'image de staging ;
- un push sur `main` peut publier l'image de production.

### Base de tests isolée

GitHub Actions démarre `postgres:16-alpine` avec des identifiants temporaires.
Cette base est créée uniquement pour le job et supprimée à sa fin. Elle ne se
connecte jamais aux projets Supabase.

PostgreSQL temporaire n'utilise pas TLS :

```env
DB_SSLMODE=disable
```

Supabase conserve au contraire :

```env
DB_SSLMODE=require
```

### Construction et contrôles

Le workflow construit une seule image locale :

```text
weeb-backend-ci:<sha>
```

Il remplace temporairement le `CMD` de cette image pour exécuter :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
```

Si une commande échoue, le job s'arrête et l'image n'est pas publiée.

### Publication après les tests

Après un push réussi sur `dev`, l'image testée reçoit les tags suivants :

```text
projetggs/weeb-backend:<sha>
projetggs/weeb-backend:staging
```

Après un push réussi sur `main` :

```text
projetggs/weeb-backend:<sha>
projetggs/weeb-backend:production
```

La CI ne reconstruit pas l'image avant sa publication. Les différents tags
pointent donc vers le même digest Docker et le même contenu.

## Rôle de Docker Hub

Le dépôt public utilisé est :

```text
docker.io/projetggs/weeb-backend
```

Docker Hub sert de registre entre GitHub Actions et Render :

- le SHA fournit une version immuable et traçable ;
- `staging` désigne la dernière image validée depuis `dev` ;
- `production` désigne la dernière image validée depuis `main` ;
- une ancienne image peut être redéployée pour effectuer un rollback.

L'image ne contient aucun `.env`. Les secrets sont injectés uniquement au
moment de son exécution par Render.

## Ce que fait Render

Render staging est un service basé sur l'image :

```text
docker.io/projetggs/weeb-backend:staging
```

Render ne reconstruit plus le dépôt et n'installe plus Python. Il télécharge
l'image publiée par la CI, lui fournit les variables d'environnement staging et
exécute son `CMD` :

```text
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn weeb_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

Le health check du service utilise :

```text
/health/
```

La production conserve ses propres variables, ses propres secrets et sa base
Supabase. Une image ne contient donc pas la configuration d'un environnement :
le même artefact peut être exécuté avec une configuration différente.

## Déclenchement du déploiement

Un service Render basé sur une image ne détecte pas automatiquement qu'un tag
Docker Hub a changé. Après la publication, GitHub Actions doit appeler le Deploy
Hook secret du service correspondant.

Le CD staging attendu est :

```text
Fusion dans dev
    ↓
CI et tests réussis
    ↓
publication de <sha> et staging
    ↓
appel du Deploy Hook staging
    ↓
Render télécharge la dernière valeur du tag staging
    ↓
migrations, collectstatic et Gunicorn
    ↓
contrôle de https://weeb-backend-staging.onrender.com/health/
```

Le workflow appelle le hook immédiatement après les deux publications. À ce
moment, les tags SHA et `staging` partagent le même digest et désignent donc la
même image validée.

Le même principe est appliqué à `main` avec un hook et une URL de production
distincts.

## Variables et secrets du pipeline

| Nom | Type GitHub | Utilisation |
| --- | --- | --- |
| `DOCKERHUB_USERNAME` | Variable | Namespace du dépôt Docker Hub |
| `DOCKERHUB_TOKEN` | Secret | Authentification en écriture sur Docker Hub |
| `RENDER_STAGING_DEPLOY_HOOK` | Secret | Déclenchement du staging après publication |
| `RENDER_PRODUCTION_DEPLOY_HOOK` | Secret | Déclenchement de la production depuis `main` |

Les identifiants Supabase, Brevo et la `SECRET_KEY` Django ne sont pas utilisés
pour construire l'image. Ils restent uniquement dans les variables des services
Render.

## Comportement selon l'événement

| Événement | Construire | Tester | Publier | Déployer |
| --- | --- | --- | --- | --- |
| Push sur une branche de travail | Oui | Oui | Non | Non |
| Pull Request vers `dev` | Oui | Oui | Non | Non |
| Push/fusion dans `dev` | Oui | Oui | `staging` + SHA | Staging |
| Pull Request vers `main` | Oui | Oui | Non | Non |
| Push/fusion dans `main` | Oui | Oui | `production` + SHA | Production |

## Échecs et sécurité

- un échec de build, de migration ou de test bloque la publication ;
- le hook Render n'est appelé qu'après la publication réussie ;
- les secrets GitHub ne sont jamais présents dans l'image ;
- `.dockerignore` exclut les `.env`, caches, journaux et fichiers locaux ;
- staging et production n'utilisent jamais la même base Supabase ;
- les Pull Requests ne disposent d'aucune étape de publication ;
- les logs ne doivent jamais afficher un token ou une URL de Deploy Hook.

## Rollback

Chaque image reste accessible par son SHA. Pour revenir à une version validée :

1. identifier le SHA d'un ancien déploiement fonctionnel ;
2. vérifier que le tag existe encore dans Docker Hub ;
3. demander à Render de déployer `projetggs/weeb-backend:<sha>` ;
4. vérifier `/health/` et les parcours critiques ;
5. documenter la raison du rollback.

## État de mise en œuvre

| Élément | État |
| --- | --- |
| Docker local | Validé |
| Tests dans l'image Docker | Validé |
| CI GitHub Actions | Validée |
| Publication Docker Hub staging + SHA | Validée |
| Render staging basé sur l'image Docker Hub | Validé |
| Déclenchement automatique Render après publication | Validé sur staging et production |
| Contrôle de santé automatique après déploiement | À mettre en place |
| Image et CD de production | Validés |

