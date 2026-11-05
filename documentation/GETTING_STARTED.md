# Lancer le projet

Docker est la méthode recommandée pour installer et lancer le backend Weeb de
manière reproductible. Il n'est pas nécessaire d'installer Python, Django ou
les dépendances du projet directement sur la machine.

## Prérequis

- Git ;
- Docker Desktop, démarré ;
- les valeurs de configuration locales ou staging transmises par l'équipe.

Les identifiants et secrets de production ne doivent jamais être utilisés pour
le développement local.

## Préparer la configuration

Depuis la racine du dépôt, créer le fichier local `.env` :

```bash
cp .env.example .env
```

Compléter les variables avec les valeurs locales ou Supabase staging. Le fichier
`.env` est ignoré par Git et ne doit jamais être ajouté à un commit.

## Premier lancement

Construire l'image et démarrer le backend :

```bash
docker compose up --build
```

Cette commande :

1. construit l'image depuis le `Dockerfile` ;
2. installe les dépendances de `requirements.txt` dans l'image ;
3. applique les migrations Django ;
4. collecte les fichiers statiques ;
5. démarre Gunicorn sur le port `8000`.

Le backend est ensuite disponible sur :

```text
http://localhost:8000
```

## Vérifier le lancement

Dans un second terminal :

```bash
docker compose ps
curl http://localhost:8000/health/
```

Le service `backend` doit être `Up` et `healthy`. La réponse attendue est :

```json
{"status":"ok"}
```

Consulter les logs si nécessaire :

```bash
docker compose logs -f backend
```

## Lancements suivants

Lorsque l'image est déjà à jour :

```bash
docker compose up
```

Reconstruire l'image après une modification du code embarqué, du `Dockerfile`
ou de `requirements.txt` :

```bash
docker compose up --build
```

Pour lancer le backend en arrière-plan :

```bash
docker compose up -d
```

## Commandes utiles

```bash
docker compose ps
docker compose logs --tail=100 backend
docker compose logs -f backend
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations
docker compose down
```

Les tests automatisés sont exécutés par GitHub Actions avec une base PostgreSQL
temporaire. Ne pas lancer la suite complète contre la base Supabase staging du
fichier `.env`.

## Développement sans Docker

Un environnement virtuel Python reste utilisable pour le dépannage ou un besoin
de développement spécifique :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Sous Windows, utiliser la commande d'activation adaptée au terminal. Cette
méthode est une alternative : le lancement Docker doit être privilégié pour
obtenir le même environnement sur toutes les machines.

Pour comprendre la construction de l'image, Compose et le déploiement Render,
consulter le [guide Docker détaillé](devOps/DOCKER.md).
