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

Variables email utiles pour le reset password :

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=Weeb <no-reply@example.com>
FRONTEND_URL=http://localhost:3000
REFRESH_TOKEN_COOKIE_SECURE=False
REFRESH_TOKEN_COOKIE_SAMESITE=Strict
```

En local, si `EMAIL_BACKEND` n'est pas défini, Django utilise le backend console et affiche l'email dans le terminal.

En local HTTP, `REFRESH_TOKEN_COOKIE_SECURE` doit rester à `False` pour que le
navigateur renvoie le cookie `refresh_token` lors de `POST /users/token/refresh/`.
En production HTTPS, le passer à `True`.

### Certificats SSL sur macOS

Sur certains Mac, l'envoi d'emails SMTP peut échouer avec :

```text
ssl.SSLCertVerificationError: certificate verify failed
```

Dans ce cas, activer l'environnement virtuel puis indiquer à Python le bundle de certificats fourni par `certifi` :

```bash
source .venv/bin/activate
python3 -m pip install --upgrade certifi
export SSL_CERT_FILE=$(python3 -m certifi)
```

Cette variable est utile uniquement pour la session de terminal courante. Elle permet à Python de vérifier correctement le certificat TLS du serveur SMTP.


### Lancement

```bash
python3 manage.py migrate
python3 manage.py runserver
```

Serveur dispo sur :

```text
http://127.0.0.1:8000/
```

## Documentation technique

Les choix d'implémentation déjà réalisés sont résumés dans [IMPLEMENTATION.md](IMPLEMENTATION.md).
