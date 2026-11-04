# Implémentations techniques

Ce document résume les choix techniques actuellement mis en place dans le
backend Weeb. Les procédures détaillées se trouvent dans la documentation
MkDocs publiée sur
[GitHub Pages](https://weeb-project.github.io/weeb_backend/).

## Documentation

### Backend

- [Modèle utilisateur personnalisé](documentation/backend/USER_MODEL.md)
- [Authentification et autorisations](documentation/backend/AUTH.md)
- [Administration](documentation/backend/ADMIN.md)
- [Authentification à deux facteurs](documentation/backend/TWO_FACTOR_AUTH.md)
- [Endpoints API](documentation/backend/ENDPOINTS.md)
- [Politique de mots de passe](documentation/backend/PASSWORD_POLICY.md)
- [Réinitialisation du mot de passe](documentation/backend/PASSWORD_RESET.md)
- [Articles](documentation/backend/ARTICLES.md)
- [Formulaire de contact](documentation/backend/CONTACT.md)
- [Variables d'environnement](documentation/backend/ENVIRONMENT.md)
- [Intégration avec les frontends](documentation/backend/FRONTEND_BACKEND.md)

### DevOps

- [Environnements staging et production](documentation/devOps/ENVIRONMENTS.md)
- [Connexion d'un frontend au staging](documentation/devOps/FRONTEND_STAGING.md)
- [Docker](documentation/devOps/DOCKER.md)
- [Intégration continue](documentation/devOps/CI.md)
- [Pipeline Docker, CI et CD](documentation/devOps/PIPELINE_CICD.md)
- [Documentation MkDocs et GitHub Pages](documentation/devOps/MKDOCS.md)
- [Keepalive Supabase](documentation/devOps/SUPABASE_KEEPALIVE.md)

## Backend et sécurité

Le backend utilise :

- Django et Django REST Framework ;
- PostgreSQL hébergé sur Supabase ;
- un modèle `CustomUser` basé sur l'email, avec UUID public et unicité de
  l'email insensible à la casse ;
- JWT avec rotation et blacklist des refresh tokens ;
- un refresh token stocké dans un cookie `HttpOnly`, `Secure` et
  `SameSite=None` sur les environnements en ligne ;
- une politique de mots de passe renforcée ;
- une authentification à deux facteurs avec TOTP ;
- du rate limiting sur les routes publiques sensibles ;
- des permissions distinctes pour les utilisateurs, auteurs et
  administrateurs ;
- `python-decouple` pour externaliser la configuration et les secrets ;
- `django-cors-headers` avec une liste d'origines propre à chaque
  environnement.

Les articles sont lisibles publiquement et modifiables par leur auteur ou par
un administrateur actif. Les réponses publiques exposent un auteur minimal afin
de ne pas révéler son adresse email. Le backend gère également les favoris, le
profil utilisateur, l'administration des comptes et le formulaire de contact.

## Emails et réinitialisation du mot de passe

Les emails transactionnels sont envoyés avec l'API HTTPS Brevo. Les clés Brevo
restent dans les variables d'environnement Render et ne sont pas versionnées.
Cette intégration remplace l'envoi SMTP, dont le port n'est pas utilisable avec
l'offre gratuite retenue pour le backend.

Le backend génère le lien de réinitialisation et sert un formulaire HTML Django
commun à tous les frontends. Le formulaire est protégé par CSRF et utilise les
tokens de réinitialisation Django. Cette solution évite de choisir un frontend
particulier au moment de générer l'email.

## Environnements déployés

Deux environnements backend indépendants sont disponibles :

| Environnement | Branche | Backend | Base de données |
| --- | --- | --- | --- |
| Staging | `dev` | `https://weeb-backend-staging.onrender.com` | Supabase staging |
| Production | `main` | `https://weeb-backend-production.onrender.com` | Supabase production |

Les deux projets Supabase utilisent des identifiants séparés. Les connexions
depuis les services qui nécessitent IPv4 utilisent le **Session Pooler**.

Les frontends sont déployés avec Vercel. Les déploiements Production utilisent
le backend de production et les Preview Deployments des branches de
développement utilisent le backend de staging. La variable `VITE_API_URL` est
injectée au moment du build Vite.

## Disponibilité et keepalive

La route publique `GET /health/` retourne `{"status": "ok"}`. Elle permet à
Render, Docker, au futur pipeline de déploiement et aux outils de monitoring de
vérifier que Gunicorn et Django répondent, sans utiliser une route métier
protégée. Ce contrôle léger ne vérifie pas directement la disponibilité de
PostgreSQL.

Un workflow GitHub Actions exécute périodiquement une requête PostgreSQL en
lecture seule sur les bases Supabase de staging et de production. Les deux jobs
utilisent des secrets GitHub distincts et ne lisent ni ne modifient les données
métier.

## Documentation publiée

La documentation est construite avec MkDocs Material et publiée avec GitHub
Pages. Elle est versionnée dans `documentation/` et sa navigation est définie
dans `mkdocs.yml`.

## Docker

La conteneurisation locale du backend est validée avec :

- un `Dockerfile` minimal basé sur `python:3.13-slim` ;
- un `.dockerignore` excluant les secrets et fichiers locaux ;
- un `compose.yaml` chargeant le `.env` local ;
- l'application automatique des migrations ;
- la collecte des fichiers statiques ;
- Gunicorn comme serveur applicatif ;
- un healthcheck Docker utilisant `/health/`.

L'image se construit et le conteneur atteint l'état `healthy` localement. GitHub
Actions publie l'image validée dans `projetggs/weeb-backend` et Render staging
utilise désormais le tag `staging` de ce registre. Les migrations, la collecte
des fichiers statiques, Gunicorn, `/health/` et les principaux parcours
fonctionnels ont été validés. La production utilise encore le runtime Python et
sera migrée séparément.

## Vérifications déjà réalisées

Les parcours suivants ont été vérifiés manuellement sur le staging :

- inscription et attente de validation administrateur ;
- connexion, déconnexion et renouvellement automatique du token ;
- modification du profil, de l'email et du mot de passe ;
- authentification à deux facteurs ;
- création, modification et suppression des articles ;
- favoris ;
- formulaire de contact ;
- administration des utilisateurs ;
- réinitialisation du mot de passe avec Brevo ;
- permissions utilisateur, auteur et administrateur.

## Intégration continue

Le workflow `.github/workflows/ci.yml` construit l'image Docker et exécute dans
cette image les contrôles Django, la vérification des migrations et les tests.
Une base PostgreSQL temporaire est créée par GitHub Actions puis détruite à la
fin du job. Les tests ne se connectent jamais à Supabase.

La CI est déclenchée à chaque push et sur les Pull Requests vers `dev` ou
`main`. Elle a été validée sur GitHub avec succès pour les événements `push` et
`pull_request` avant la fusion dans `dev`. Le runtime Docker du staging est
maintenant validé ; le déploiement continu reste à conditionner à la réussite de
la CI. Après les tests, les pushes sur `dev` et `main` publient la même image
dans `projetggs/weeb-backend`, avec un tag par SHA et un tag d'environnement.
Après la publication du staging, le workflow appelle son Deploy Hook Render.
Cette dernière étape doit être validée sur le prochain push dans `dev`.

## Travaux restants

Les prochaines étapes sont réalisées dans cet ordre :

1. compléter les tests automatisés Django et ajouter la mesure de couverture ;
2. mettre en place le CD staging, conditionné par la réussite de la CI, avec un
   contrôle de santé après le déploiement ;
3. reproduire et valider le runtime Docker et le CD sur la production ;
4. mettre en place le monitoring séparé du staging et de la production, avec
   collecte des erreurs, contrôle d'uptime et alertes ;
5. documenter les indicateurs de qualité, l'utilisation des ressources et
   l'impact énergétique de l'architecture.
