# Gestion des secrets avec `.env`

Les secrets et les paramètres dépendants de l'environnement sont externalisés avec `python-decouple`.

Dans `weeb_backend/settings.py`, les valeurs sensibles sont lues avec :

```python
from decouple import Csv, config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
```

La configuration PostgreSQL est également chargée depuis l'environnement :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
```

Le fichier `.env` contient les vraies valeurs locales et ne doit jamais être commit.

Le fichier `.gitignore` ignore déjà :

```text
.env
.envrc
```

Un fichier `.env.example` est fourni pour documenter les variables attendues sans exposer de secrets. Pour installer le projet, chaque développeur doit copier ce template :

```bash
cp .env.example .env
```

puis remplir ses propres valeurs locales.

Variables principales :

```env
SECRET_KEY=
DEBUG=True
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=5432
FRONTEND_URL=http://localhost:5173
REFRESH_TOKEN_COOKIE_SECURE=False
REFRESH_TOKEN_COOKIE_SAMESITE=Strict
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SUPPORT_EMAIL=projet.ggs@gmail.com
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=Weeb
BREVO_API_TIMEOUT=10
```

En local, laisser `BREVO_API_KEY` vide suffit pour utiliser automatiquement le
backend console et afficher les emails dans le terminal sans envoyer de
véritable message. Sur Render, les quatre variables
Brevo sont configurées dans l'environnement du service. La clé réelle ne doit
jamais être enregistrée dans `.env.example`, la documentation ou Git.

`SUPPORT_EMAIL` est affiché dans les emails de sécurité lorsque l'utilisateur
n'est pas à l'origine d'un changement sensible du profil. Par défaut, l'adresse
utilisée est `projet.ggs@gmail.com`.
