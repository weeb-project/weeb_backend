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

Les réponses publiques exposent l'auteur avec un format minimal :

```json
{
  "author": {
    "id": "4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86",
    "first_name": "John",
    "last_name": "Doe"
  },
  "title": "Mon article",
  "content": "Contenu de l'article",
  "slug": "mon-article",
  "created_at": "2026-06-04T10:00:00Z",
  "updated_at": "2026-06-04T10:00:00Z"
}
```

Pour éviter d'exposer des informations utilisateur sensibles sur des endpoints
publics, l'auteur d'un article ne contient pas `email`, `is_staff` ou `is_active`.

## Écriture

La création demande un utilisateur connecté et actif :

```text
POST /articles/
Authorization: Bearer <access_token>
```

Le backend ignore `author_id` à la création et utilise toujours l'utilisateur connecté
comme auteur.

La modification et la suppression sont réservées au propriétaire de l'article ou
à un admin actif (`is_staff=true`) :

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
