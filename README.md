# Weeb Backend

API Django du projet Weeb, conteneurisée avec Docker et déployée sur Render.
Elle fournit l'authentification, la gestion des utilisateurs, les articles, les
favoris, la 2FA, l'administration et les emails transactionnels.

## Démarrage rapide

Prérequis : Git et Docker Desktop.

```bash
git clone https://github.com/weeb-project/weeb_backend.git
cd weeb_backend
cp .env.example .env
docker compose up --build
```

Compléter `.env` avec les valeurs locales ou staging fournies par l'équipe. Ne
jamais utiliser ni versionner les secrets de production.

Vérifier le backend :

```bash
curl http://localhost:8000/health/
```

Réponse attendue :

```json
{"status":"ok"}
```

Pour les lancements suivants :

```bash
docker compose up
```

Pour arrêter les conteneurs :

```bash
docker compose down
```

Le [guide de lancement](documentation/GETTING_STARTED.md) explique les logs,
les commandes Django, la reconstruction de l'image et la méthode alternative
sans Docker.

## Environnements

| Environnement | Branche | Backend |
| --- | --- | --- |
| Staging | `dev` | `https://weeb-backend-staging.onrender.com` |
| Production | `main` | `https://weeb-backend-production.onrender.com` |

Le staging et la production utilisent des services Render, des bases Supabase
et des secrets distincts.

## Contribution

Le travail part de `dev` et passe par une branche dédiée :

```bash
git switch dev
git pull --ff-only origin dev
git switch -c feature/nom-de-la-feature
```

Après les modifications :

```bash
git add .
git commit -m "feat: description concise"
git push -u origin feature/nom-de-la-feature
```

Ouvrir ensuite une Pull Request vers `dev`. La fusion vers `main` est réservée
aux versions validées pour la production.

## CI/CD

GitHub Actions construit l'image Docker, vérifie Django et les migrations, puis
exécute les tests sur les Pull Requests. Après une fusion :

```text
dev  → image Docker :staging    → Docker Hub → Render staging
main → image Docker :production → Docker Hub → Render production (à finaliser)
```

Le pipeline staging est opérationnel. L'automatisation du déploiement Docker
de production reste à finaliser et à valider avant sa mise en service.

Les secrets GitHub, Render, Supabase et Brevo ne doivent jamais être ajoutés au
dépôt.

## Documentation

La documentation complète est publiée sur GitHub Pages :

**[Documentation Weeb Backend](https://weeb-project.github.io/weeb_backend/)**

Pages principales :

- [Lancer le projet](documentation/GETTING_STARTED.md)
- [Docker](documentation/devOps/DOCKER.md)
- [Pipeline CI/CD](documentation/devOps/PIPELINE_CICD.md)
- [Variables d'environnement](documentation/backend/ENVIRONMENT.md)
- [Endpoints](documentation/backend/ENDPOINTS.md)
- [Choix d'implémentation](IMPLEMENTATION.md)
