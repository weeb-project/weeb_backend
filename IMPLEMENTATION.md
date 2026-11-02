# Implémentations techniques

Ce document sert de sommaire pour les choix techniques déjà mis en place dans le backend.

## Documentation

- [Modèle utilisateur personnalisé](documentation/backend/USER_MODEL.md)
- [Authentification et autorisations](documentation/backend/AUTH.md)
- [Politique de mots de passe](documentation/backend/PASSWORD_POLICY.md)
- [Reset password par email](documentation/backend/PASSWORD_RESET.md)
- [Articles](documentation/backend/ARTICLES.md)
- [Formulaire de contact](documentation/backend/CONTACT.md)
- [Gestion des secrets avec `.env`](documentation/backend/ENVIRONMENT.md)
- [Connexion avec le frontend local](documentation/backend/FRONTEND_BACKEND.md)

## Résumé rapide

Le backend utilise :

- Django REST Framework avec JWT
- un modèle `CustomUser` basé sur l'email, avec UUID public et unicité email insensible à la casse
- une politique de mots de passe renforcée
- un reset password par email avec token Django
- des articles lisibles publiquement et modifiables par leur auteur
- un auteur public minimal sur les articles pour éviter d'exposer l'email
- un formulaire de contact public
- des refresh tokens stockés en cookie HttpOnly, avec rotation et blacklist SimpleJWT
- du rate limiting sur les routes publiques sensibles
- `python-decouple` pour externaliser les secrets
- `django-cors-headers` pour connecter le frontend local

## À implémenter plus tard

- ajouter des tests métier sur les articles et le formulaire de contact
