# Instructions frontend - Articles et favoris

## Champs article

Les réponses de `GET /articles/`, `GET /articles/:slug/`,
`GET /users/me/articles/` et `GET /users/me/favorites/` renvoient maintenant :

```text
favorites_count
is_favorite
```

`is_favorite` vaut `false` pour un visiteur non connecté.

## Ajouter un favori

```text
POST /articles/:slug/favorite/
Authorization: Bearer <access_token>
```

Réponse :

```json
{
  "message": "Article ajouté aux favoris",
  "is_favorite": true,
  "favorites_count": 4
}
```

## Retirer un favori

```text
DELETE /articles/:slug/favorite/
Authorization: Bearer <access_token>
```

Réponse :

```json
{
  "message": "Article retiré des favoris",
  "is_favorite": false,
  "favorites_count": 3
}
```

## Articles du profil

```text
GET /users/me/articles/
Authorization: Bearer <access_token>
```

Utiliser cette route dans le profil pour afficher les articles publiés par
l'utilisateur connecté.

## Favoris du profil

```text
GET /users/me/favorites/
Authorization: Bearer <access_token>
```

Utiliser cette route dans le profil pour afficher les articles favoris de
l'utilisateur connecté.

## Comportement UI recommandé

Afficher un bouton favori sur chaque article.

Si `is_favorite=true`, le bouton doit apparaître actif. Au clic, appeler
`DELETE /articles/:slug/favorite/`.

Si `is_favorite=false`, le bouton doit apparaître inactif. Au clic, appeler
`POST /articles/:slug/favorite/`.

Après la réponse backend, mettre à jour localement `is_favorite` et
`favorites_count` avec les valeurs renvoyées par l'API.

Si l'utilisateur n'est pas connecté, rediriger vers la connexion ou afficher une
invitation à se connecter avant d'appeler les routes favori.
