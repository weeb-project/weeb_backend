# Double authentification TOTP

La double authentification utilise TOTP, compatible avec les applications comme
Google Authenticator, Microsoft Authenticator, 1Password ou Authy.

## Dépendance backend

Installer les dépendances :

```bash
pip install -r requirements.txt
```

La dépendance ajoutée est :

```text
pyotp==2.9.0
```

## Champs utilisateur

```text
totp_secret
is_two_factor_enabled
```

Le serializer utilisateur expose :

```text
is_two_factor_enabled
```

## Initialiser la 2FA

```text
POST /users/2fa/setup/
Authorization: Bearer <access_token>
```

Réponse :

```json
{
  "message": "Configuration 2FA initialisée",
  "secret": "BASE32SECRET",
  "provisioning_uri": "otpauth://totp/Weeb:user@example.com?secret=BASE32SECRET&issuer=Weeb"
}
```

Le frontend doit transformer `provisioning_uri` en QR code.

## Confirmer et activer la 2FA

```text
POST /users/2fa/confirm/
Authorization: Bearer <access_token>
```

Body :

```json
{
  "code": "123456"
}
```

Réponse :

```json
{
  "message": "Double authentification activée",
  "user": {
    "is_two_factor_enabled": true
  }
}
```

## Désactiver la 2FA

```text
POST /users/2fa/disable/
Authorization: Bearer <access_token>
```

Body :

```json
{
  "code": "123456"
}
```

## Login avec 2FA activée

Premier appel inchangé :

```text
POST /users/login/
```

Body :

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

Si la 2FA est activée, le backend ne renvoie pas encore d'access token :

```json
{
  "message": "Code 2FA requis",
  "requires_2fa": true,
  "two_factor_token": "...",
  "user": {
    "is_two_factor_enabled": true
  }
}
```

Le frontend doit ensuite demander le code à 6 chiffres et appeler :

```text
POST /users/2fa/verify-login/
```

Body :

```json
{
  "two_factor_token": "...",
  "code": "123456"
}
```

Si le code est valide, la réponse est la même qu'un login classique :

```json
{
  "message": "Connexion réussie",
  "access": "...",
  "user": {
    "is_two_factor_enabled": true
  }
}
```

Le cookie HttpOnly `refresh_token` est posé à cette étape.

## Erreurs utiles

```text
INVALID_TWO_FACTOR_CODE
TWO_FACTOR_TOKEN_EXPIRED
INVALID_TWO_FACTOR_TOKEN
TWO_FACTOR_ALREADY_ENABLED
TWO_FACTOR_NOT_ENABLED
TWO_FACTOR_SETUP_REQUIRED
```
