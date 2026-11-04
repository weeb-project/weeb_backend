# Weeb Backend

Backend Django de l'application Weeb, exécutable localement avec Docker et
déployé sur Render à partir des images validées par la CI.

## Démarrage rapide avec Docker

Prérequis : Docker Desktop doit être installé et démarré.

Depuis la racine du dépôt :

```bash
cp .env.example .env
docker compose up --build
```

Renseigner dans `.env` les valeurs locales ou staging transmises par l'équipe.
Ne jamais y placer les secrets de production.

Vérifier ensuite le backend :

```bash
curl http://localhost:8000/health/
```

Réponse attendue :

```json
{"status":"ok"}
```

Le backend est alors disponible sur `http://localhost:8000`. Pour les
lancements suivants, si l'image est toujours à jour :

```bash
docker compose up
```

Pour arrêter le projet :

```bash
docker compose down
```

Voir le [guide Docker complet](documentation/devOps/DOCKER.md) pour les logs,
les commandes Django et la reconstruction de l'image.

## Workflow Git

### Branches principales
- `main` → production 
- `dev` → intégration des nouvelles fonctionnalités


### Développement d’une feature

→ Se placer sur la branche `dev` et la mettre à jour :

- git checkout dev
- git pull

→ Créer une nouvelle branche :

- git checkout -b feature/nom-de-la-feature
- Développement de la fonctionnalité et commit des changements

→ Push la branche :
- git push origin feature/nom-de-la-feature

→ Ouvrir une Pull Request :
- Source : feature/nom-de-la-feature
- Target : dev
- Après review et validation → merge dans `dev`
- Suppression de la branche feature
- Close issue

## Lancement du projet

### Méthode recommandée : Docker

Docker est la méthode principale pour lancer le backend. Elle installe les
dépendances dans l'image et exécute automatiquement les migrations, la collecte
des fichiers statiques et Gunicorn.

Créer d'abord le fichier local de configuration :

```bash
cp .env.example .env
```

Renseigner les valeurs de développement ou de staging fournies par l'équipe,
sans utiliser les secrets de production, puis construire et démarrer le
backend :

```bash
docker compose up --build
```

Pour les lancements suivants, tant que le `Dockerfile`, les dépendances et le
code embarqué dans l'image n'ont pas changé :

```bash
docker compose up
```

Le backend est disponible sur `http://localhost:8000`. Vérification rapide :

```bash
docker compose ps
curl http://localhost:8000/health/
```

Commandes courantes :

```bash
docker compose up -d
docker compose logs -f backend
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations
docker compose down
```

Après une modification du code, de `requirements.txt` ou du `Dockerfile`,
reconstruire l'image avec `docker compose up --build`.

Le guide complet se trouve dans
[documentation/devOps/DOCKER.md](documentation/devOps/DOCKER.md).

### Méthode alternative : environnement Python local

Cette méthode reste disponible pour le développement ou le dépannage sans
Docker.

Sur macOS :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Sur Windows PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Sur Windows CMD :

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Créer le .env

Créer un fichier `.env` à la racine du projet à partir du template :

```bash
cp .env.example .env
```

Puis remplir les variables avec les valeurs disponibles sur le drive ou fournies par l'équipe.

Variables email utiles pour le reset password et les notifications de sécurité
du profil :

```env
SUPPORT_EMAIL=projet.ggs@gmail.com
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
REFRESH_TOKEN_COOKIE_SECURE=False
REFRESH_TOKEN_COOKIE_SAMESITE=Strict
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=Weeb
BREVO_API_TIMEOUT=10
```

En local, Django utilise le backend console et affiche les emails dans le
terminal. Sur Render, la présence de `BREVO_API_KEY` active l'envoi réel via
l'API HTTPS Brevo. Les valeurs secrètes restent exclusivement dans les variables
d'environnement Render.
`SUPPORT_EMAIL` est l'adresse affichée dans les emails de sécurité quand
l'utilisateur n'est pas à l'origine d'une modification sensible du profil.

En local HTTP, `REFRESH_TOKEN_COOKIE_SECURE` doit rester à `False` pour que le
navigateur renvoie le cookie `refresh_token` lors de `POST /users/token/refresh/`.
En production HTTPS, le passer à `True`.

### Lancement sans Docker

Sur macOS, depuis la racine du projet :

```bash
python manage.py migrate
python manage.py runserver
```


Sur Windows :

```bash
python manage.py migrate
python manage.py runserver
```

Serveur dispo sur :

```text
http://127.0.0.1:8000/
```

## Documentation technique

La documentation complète du backend est publiée sur GitHub Pages :

**[Consulter la documentation Weeb Backend](https://weeb-project.github.io/weeb_backend/)**

Elle est mise à jour automatiquement après chaque modification de la
documentation fusionnée dans `dev`.

Les choix d'implémentation déjà réalisés sont résumés dans [IMPLEMENTATION.md](IMPLEMENTATION.md).

Pour configurer la tâche planifiée qui maintient une activité PostgreSQL sur
Supabase, voir [SUPABASE_KEEPALIVE.md](documentation/devOps/SUPABASE_KEEPALIVE.md).
