# Endpoints

## Authentification et utilisateurs

```text
GET    /users/
POST   /users/register/
POST   /users/login/
POST   /users/logout/
POST   /users/token/refresh/
POST   /users/password-reset/request/
POST   /users/password-reset/confirm/
```

## Articles

```text
GET    /articles/
POST   /articles/
GET    /articles/<slug:slug>/
PUT    /articles/<slug:slug>/
PATCH  /articles/<slug:slug>/
DELETE /articles/<slug:slug>/
```

## Contact

```text
POST   /contact/
```

## API admin

```text
GET    /api/admin/users/
GET    /api/admin/users/<uuid:user_id>/
PATCH  /api/admin/users/<uuid:user_id>/
```

## Django admin

```text
GET    /admin/
```
