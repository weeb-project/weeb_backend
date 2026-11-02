# Politique de mots de passe

La politique de mots de passe est définie dans `weeb_backend/settings.py` avec `AUTH_PASSWORD_VALIDATORS`.

Les validateurs Django standards activés sont :

- `UserAttributeSimilarityValidator` : refuse un mot de passe trop proche des informations de l'utilisateur
- `MinimumLengthValidator` : impose une longueur minimale de 12 caractères
- `CommonPasswordValidator` : refuse les mots de passe trop courants
- `NumericPasswordValidator` : refuse les mots de passe uniquement numériques

Deux validateurs personnalisés ont aussi été ajoutés dans `users/validators.py` :

- `UppercaseValidator` : impose au moins une lettre majuscule
- `SpecialCharacterValidator` : impose au moins un caractère spécial

Ces règles sont appliquées lors de la création de compte et lors du reset password grâce à `validate_password_strength()` dans `users/serializers.py`.

Un mot de passe valide doit donc respecter au minimum :

- 12 caractères
- pas trop proche de l'email, du prénom ou du nom
- pas présent dans la liste des mots de passe courants
- pas uniquement numérique
- au moins une majuscule
- au moins un caractère spécial

Exemple accepté :

```text
SecurePass123!
```
