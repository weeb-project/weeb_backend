# Modèle utilisateur personnalisé

Le projet utilise un modèle utilisateur personnalisé dans l'application `users`.

L'application est déclarée dans `weeb_backend/settings.py` :

```python
INSTALLED_APPS = [
    ...
    'users.apps.UsersConfig'
]
```

Le modèle actif est défini avec :

```python
AUTH_USER_MODEL = 'users.CustomUser'
```

Cette directive indique à Django d'utiliser `users.CustomUser` partout où le framework ou les applications tierces manipulent un utilisateur.

## Choix du modèle

Le modèle `CustomUser` est défini dans `users/models.py` et hérite de `AbstractUser`.

Le champ `username` hérité de Django est supprimé :

```python
username = None
```

L'email devient l'identifiant principal :

```python
email = models.EmailField(_('adresse email'), unique=True, blank=False)
USERNAME_FIELD = 'email'
REQUIRED_FIELDS = []
```

Les emails sont normalisés en minuscules à la création et à la validation des
formulaires API. Une contrainte de base de données empêche aussi les doublons
insensibles à la casse :

```python
models.UniqueConstraint(
    Lower('email'),
    name='unique_customuser_email_ci',
)
```

Ainsi, `user@example.com` et `USER@example.com` sont considérés comme le même
email.

Le modèle expose aussi un identifiant public non prédictible :

```python
public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
```

L'API renvoie ce UUID dans le champ `id` des réponses utilisateur. La clé primaire
interne Django reste un entier afin de ne pas casser les relations SQL existantes.

Conséquences :

- les utilisateurs se connectent avec leur email
- l'email est obligatoire et unique, sans distinction de casse
- la commande `createsuperuser` demande l'email au lieu d'un username
- le modèle reste compatible avec les champs standards de Django comme `first_name`, `last_name`, `is_active`, `is_staff`, `is_superuser` et `date_joined`

## CustomUserManager

Comme le champ `username` est supprimé, le manager utilisateur par défaut de Django ne suffit plus.

Le projet définit donc `CustomUserManager`, basé sur `BaseUserManager`, avec deux méthodes :

- `create_user(email, password, **extra_fields)` : crée un utilisateur standard
- `create_superuser(email, password, **extra_fields)` : crée un administrateur avec `is_staff=True`, `is_superuser=True` et `is_active=True`

Le manager normalise l'email avec `normalize_email().lower()`, vérifie que l'email et le mot de passe sont fournis, puis hache le mot de passe avec `set_password()`.

Les serializers API appliquent la même normalisation et vérifient les doublons
avec `email__iexact`, afin que `user@example.com` et `User@example.com` soient
considérés comme le même compte.

Le modèle lie ce manager avec :

```python
objects = CustomUserManager()
```

## Administration Django

Le modèle est enregistré dans `users/admin.py` :

```python
from django.contrib import admin
from .models import CustomUser

admin.site.register(CustomUser)
```

Cela permet de gérer les utilisateurs personnalisés depuis `/admin/`.
