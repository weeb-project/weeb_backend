# Administration

Cette documentation décrit les accès réservés aux administrateurs : l'interface
Django Admin native et les routes API utilisées par le frontend admin.

## Accès admin

L'interface Django Admin demande une connexion via session Django avec un compte
ayant `is_staff=true`.

Les routes API d'administration utilisateur sont protégées par `IsAdminUser`.
Elles demandent un utilisateur connecté avec `is_staff=true`.

Chaque requête vers l'API admin doit être envoyée avec un access token valide :

```text
Authorization: Bearer <access_token>
```

## Deux espaces d'administration

Le projet expose deux espaces admin différents :

```text
/admin/
```

Interface HTML native de Django. Elle sert à administrer les modèles directement
depuis le backend.

```text
/api/admin/users/
```

API JSON utilisée par le frontend admin pour gérer les utilisateurs.

## Django Admin natif

L'interface Django Admin est montée sur :

```text
GET /admin/
```

Elle n'est pas une API JSON. Elle sert des pages HTML générées par Django et
utilise l'authentification de session Django.

Routes principales :

```text
GET /admin/
GET /admin/login/
POST /admin/login/
POST /admin/logout/
GET /admin/password_change/
POST /admin/password_change/
GET /admin/password_change/done/
```

L'accès au Django Admin demande un compte avec `is_staff=true`. Pour tout gérer
sans restriction, le compte doit aussi avoir `is_superuser=true` ou les
permissions Django nécessaires.

Modèles enregistrés dans le Django Admin :

```text
CustomUser
Article
Contact
```

URLs utiles générées par Django Admin :

```text
GET /admin/users/customuser/
GET /admin/users/customuser/add/
GET /admin/users/customuser/:pk/change/

GET /admin/blog/article/
GET /admin/blog/article/add/
GET /admin/blog/article/:pk/change/

GET /admin/contact/contact/
GET /admin/contact/contact/:pk/change/
```

Dans ces URLs Django Admin, `:pk` correspond à la clé primaire interne utilisée
par Django. À ne pas confondre avec l'API `PATCH /api/admin/users/:id/`, où
`:id` correspond à l'UUID public exposé dans le champ JSON `id`.

Un admin peut aussi valider un compte depuis l'interface Django Admin en ouvrant
le `CustomUser` concerné et en cochant `is_active`. Pour le dashboard frontend,
il faut utiliser l'API JSON décrite ci-dessous.

## Administration des articles via API

Il n'existe pas de route `/api/admin/articles/` dédiée. Le frontend admin utilise
les routes articles standards :

```text
PUT /articles/:slug/
PATCH /articles/:slug/
DELETE /articles/:slug/
```

Un admin actif (`is_staff=true`) peut modifier ou supprimer une publication dont
il n'est pas l'auteur. Les utilisateurs non-admin restent limités à leurs propres
publications.

## Routes API admin utilisateur

```text
GET /api/admin/users/
GET /api/admin/users/:id/
PATCH /api/admin/users/:id/
```

Le paramètre `:id` correspond à l'UUID public de l'utilisateur. C'est la valeur
renvoyée par l'API dans le champ `id`, qui pointe côté backend vers
`public_id`.

Exemple :

```json
{
  "id": "4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_staff": false,
  "is_active": false,
  "date_joined": "2026-06-04T10:30:00Z"
}
```

Pour consulter ou modifier cet utilisateur, le frontend admin utilise donc :

```text
GET /api/admin/users/4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86/
PATCH /api/admin/users/4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86/
```

## Lister les utilisateurs

```text
GET /api/admin/users/
```

Cette route renvoie la liste des utilisateurs, triée du plus récent au plus
ancien.

Elle permet notamment au dashboard admin d'afficher les comptes en attente de
validation, c'est-à-dire les utilisateurs avec :

```json
{
  "is_active": false
}
```

## Consulter un utilisateur

```text
GET /api/admin/users/:id/
```

Cette route renvoie les informations d'un utilisateur précis.

Champs renvoyés :

```text
id
email
first_name
last_name
is_staff
is_active
date_joined
```

## Valider un compte

Lors de l'inscription, un compte est créé avec `is_active=false`. L'utilisateur
ne peut donc pas encore se connecter.

Pour valider ce compte, l'admin envoie :

```text
PATCH /api/admin/users/:id/
```

avec :

```json
{
  "is_active": true
}
```

Après cette mise à jour, le compte devient actif et l'utilisateur peut se
connecter avec `POST /users/login/`.

## Modifier un utilisateur

La route admin accepte les champs suivants en modification :

```text
first_name
last_name
is_active
is_staff
```

Exemple :

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_staff": false
}
```

Les champs suivants sont en lecture seule :

```text
id
email
date_joined
```

## Garde-fous

Un admin ne peut pas désactiver son propre compte via cette route.

Si un admin tente de passer son propre compte à `is_active=false`, l'API renvoie
une erreur :

```json
{
  "error_code": "CANNOT_DEACTIVATE_SELF",
  "message": "Vous ne pouvez pas désactiver votre propre compte"
}
```

Un admin ne peut pas non plus retirer ses propres droits admin via cette route.

Si un admin tente de passer son propre compte à `is_staff=false`, l'API renvoie
une erreur :

```json
{
  "error_code": "CANNOT_REMOVE_OWN_ADMIN_ACCESS",
  "message": "Vous ne pouvez pas retirer vos propres droits admin"
}
```

## Codes de réponse utiles

```text
200 OK
```

La lecture ou la mise à jour admin a réussi.

```text
400 Bad Request
```

La requête est invalide, par exemple si un admin tente de désactiver son propre
compte ou de retirer ses propres droits admin.

```text
401 Unauthorized
```

La requête n'a pas d'access token valide.

```text
403 Forbidden
```

L'utilisateur est connecté, mais il n'a pas les droits admin.

```text
404 Not Found
```

Aucun utilisateur ne correspond à l'UUID public fourni dans l'URL.

## Flux de validation d'un compte

1. L'utilisateur remplit le formulaire d'inscription.
2. Le frontend envoie `POST /users/register/`.
3. L'API crée l'utilisateur avec `is_active=false`.
4. Le frontend affiche un message de compte en attente de validation.
5. L'admin liste les utilisateurs avec `GET /api/admin/users/`.
6. L'admin repère le compte inactif.
7. Le frontend admin envoie `PATCH /api/admin/users/:id/` avec `{"is_active": true}`.
8. L'API met à jour l'utilisateur en base de données.
9. L'API répond `200 OK`.
10. Le compte est actif et l'utilisateur peut se connecter.

Le backend ne notifie pas automatiquement l'utilisateur après validation. Si le
frontend veut informer l'utilisateur, il faut prévoir une logique dédiée côté
application.
