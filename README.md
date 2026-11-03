# Workflow Git

## Branches principales
- `main` → production 
- `dev` → intégration des nouvelles fonctionnalités


## Développement d’une feature

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

### Préparation de l'environnement Python
Sur Mac :

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

### Lancement

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

Les choix d'implémentation déjà réalisés sont résumés dans [IMPLEMENTATION.md](IMPLEMENTATION.md).

Pour configurer la tâche planifiée qui maintient une activité PostgreSQL sur
Supabase, voir [SUPABASE_KEEPALIVE.md](documentation/devOps/SUPABASE_KEEPALIVE.md).
