# Articles

Les articles sont exposés via l'application `blog`.

Routes disponibles :

```text
GET /articles/
POST /articles/
GET /articles/:slug/
PUT /articles/:slug/
PATCH /articles/:slug/
DELETE /articles/:slug/
```

## Lecture

La lecture est publique :

```text
GET /articles/
GET /articles/:slug/
```

Ces routes utilisent `AllowAny` ou une permission custom qui autorise les méthodes
de lecture.

## Écriture

La création demande un utilisateur connecté et actif :

```text
POST /articles/
Authorization: Bearer <access_token>
```

Le backend ignore `author_id` à la création et utilise toujours l'utilisateur connecté
comme auteur.

La modification et la suppression sont réservées au propriétaire de l'article :

```text
PUT /articles/:slug/
PATCH /articles/:slug/
DELETE /articles/:slug/
```

## Slug

Le slug est généré automatiquement à partir du titre dans `blog/serializers.py`.
S'il existe déjà, un suffixe numérique est ajouté :

```text
mon-article
mon-article-2
mon-article-3
```

Le détail d'un article utilise le slug comme identifiant public.
