# Dockeriser le backend Django

Le backend utilise une image Docker indépendante de l'environnement. Pour la
première validation, Compose charge le fichier local `.env`, qui doit pointer
uniquement vers Supabase staging. La production ne doit pas être utilisée
pendant le développement ou les premiers tests Docker.

## Fichiers Docker

```text
Dockerfile       Construction de l'image Django et Gunicorn
.dockerignore    Fichiers exclus du contexte de construction
compose.yaml     Exécution locale avec les variables de .env
```

Le conteneur exécute au démarrage :

1. les migrations Django sur la base configurée ;
2. la collecte des fichiers statiques ;
3. Gunicorn sur le port fourni.

## Vérifier les variables locales

Si le fichier `.env` n'existe pas encore, le créer à partir du modèle :

```bash
cp .env.example .env
```

Renseigner uniquement les variables locales et du Supabase staging :

```env
DEBUG=False
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

Compléter les autres variables avec la configuration staging existante. Le
fichier `.env` est ignoré par Git et par Docker : Compose le lit au démarrage
sans le copier dans l'image.

Ne jamais placer les identifiants Supabase production dans ce fichier.

## Lancement recommandé

Docker est désormais la méthode recommandée pour lancer le backend. Il n'est
pas nécessaire d'activer `.venv`, d'exécuter `pip install` ou de lancer
`manage.py runserver` sur la machine hôte.

Au premier lancement, ou après une modification du code, du `Dockerfile` ou de
`requirements.txt` :

```bash
docker compose up --build
```

Cette commande construit l'image puis démarre le backend. Pour séparer les deux
opérations :

```bash
docker compose build
docker compose up
```

Pour les lancements suivants, lorsque l'image est déjà à jour :

```bash
docker compose up
```

Le backend conteneurisé est accessible sur :

```text
http://localhost:8000
```

Vérifier son état :

```bash
docker compose ps
curl http://localhost:8000/health/
```

Le service `backend` doit être `Up` et `healthy`, et `/health/` doit répondre
avec un statut HTTP 200 et `{"status":"ok"}`.

Pour exécuter le service en arrière-plan et consulter ses logs :

```bash
docker compose up -d
docker compose logs -f backend
```

Pour afficher uniquement les dernières lignes :

```bash
docker compose logs --tail=100 backend
```

## Exécuter les commandes Django

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations
```

Ne pas lancer `manage.py test` avec ce fichier Compose : il utilise le `.env`
local et se connecterait à Supabase staging. Les tests automatisés disposent
d'une base PostgreSQL temporaire dans GitHub Actions.

## Arrêter les conteneurs

```bash
docker compose down
```

L'environnement virtuel éventuellement actif dans le terminal n'est pas utilisé
par ces commandes : Python, Django et Gunicorn s'exécutent dans le conteneur.

Le projet n'utilise pas de base PostgreSQL locale dans Compose. Le Supabase
staging configuré dans `.env` sert uniquement au développement manuel, jamais
aux tests automatisés.

## Utilisation dans la CI

La CI construit la même image depuis le `Dockerfile`, puis exécute les contrôles
et les tests Django dans cette image. Elle utilise un PostgreSQL temporaire et
ne se connecte jamais aux bases Supabase pour lancer les tests.

Le fichier `compose.yaml` reste destiné au développement local. Aucun fichier
`compose.test.yaml` n'est nécessaire : PostgreSQL est déclaré comme service dans
GitHub Actions et la commande du conteneur est remplacée par
`python manage.py test` pendant le workflow.

Voir [Intégration continue du backend](CI.md) pour le détail du pipeline.

## Déploiement Docker sur Render staging

Le service `weeb-backend-staging` utilise le runtime Docker depuis le 4 novembre
2026. La migration a été réalisée ainsi :

1. construire et tester l'image localement ;
2. fusionner la branche Docker dans `dev` ;
3. ouvrir les paramètres du service `weeb-backend-staging` ;
4. conserver le dépôt, la branche `dev`, les variables staging et `/health/` ;
5. changer le runtime de Python vers Docker ;
6. sélectionner le `Dockerfile` situé à la racine ;
7. déployer puis tester tous les parcours du staging.

Render utilise alors le `CMD` du Dockerfile. Les anciennes commandes Build et
Start du runtime Python ne sont plus utilisées.

La validation a confirmé :

- l'application des migrations Django ;
- la collecte de 157 fichiers statiques dans `/app/staticfiles` ;
- le démarrage de Gunicorn sur le port fourni par Render ;
- une réponse HTTP 200 sur `/health/` ;
- le fonctionnement des principaux parcours depuis le frontend staging.

La production reste temporairement en runtime Python. Elle passera à Docker
après l'ajout de la couverture et la mise en place du CD staging conditionné par
la CI.

## Registre Docker Hub

Les images validées par la CI sont publiées dans :

```text
projetggs/weeb-backend
```

La CI ne reconstruit pas une nouvelle image pour la publication. Elle ajoute des
tags à l'image qui vient de passer les contrôles Django et les tests, puis la
publie :

```text
dev  → <sha> et staging
main → <sha> et production
```

Render staging utilise maintenant l'image
`docker.io/projetggs/weeb-backend:staging`. Il ne reconstruit donc plus le
Dockerfile : il télécharge l'artefact produit et testé par GitHub Actions.

Après la publication, GitHub Actions appelle automatiquement le Deploy Hook du
staging. Render exécute alors `Deploy latest reference` et télécharge la nouvelle
valeur du tag `staging`. Cette étape doit encore être validée lors du prochain
push fusionné dans `dev`.

Voir [Pipeline Docker, CI et CD](PIPELINE_CICD.md).

## Sécurité

- Ne jamais ajouter `.env` à Git ou à l'image.
- Ne jamais placer un mot de passe dans `ARG` ou `ENV` du Dockerfile.
- Injecter les secrets avec Compose ou les variables Render.
- Vérifier les logs et le contenu de l'image avant tout déploiement.
- Ne jamais tester Docker avec Supabase production.
