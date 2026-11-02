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
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=Weeb <adresse-gmail-du-projet@gmail.com>
SUPPORT_EMAIL=projet.ggs@gmail.com
```

`SUPPORT_EMAIL` est affiché dans les emails de sécurité lorsque l'utilisateur
n'est pas à l'origine d'un changement sensible du profil. Par défaut, l'adresse
utilisée est `projet.ggs@gmail.com`.
