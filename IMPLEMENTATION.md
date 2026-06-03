# Implémentations techniques

Ce document sert de sommaire pour les choix techniques déjà mis en place dans le backend.

## Documentation

- [Modèle utilisateur personnalisé](documentation/USER_MODEL.md)
- [Authentification et autorisations](documentation/AUTH.md)
- [Politique de mots de passe](documentation/PASSWORD_POLICY.md)
- [Reset password par email](documentation/PASSWORD_RESET.md)
- [Articles](documentation/ARTICLES.md)
- [Gestion des secrets avec `.env`](documentation/ENVIRONMENT.md)
- [Connexion avec le frontend local](documentation/FRONTEND_BACKEND.md)

## Résumé rapide

Le backend utilise :

- Django REST Framework avec JWT
- un modèle `CustomUser` basé sur l'email
- une politique de mots de passe renforcée
- un reset password par email avec token Django
- des articles lisibles publiquement et modifiables par leur auteur
- `python-decouple` pour externaliser les secrets
- `django-cors-headers` pour connecter le frontend local

## À implémenter plus tard

- formulaire de contact public
