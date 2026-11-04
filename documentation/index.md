# Documentation Weeb Backend

Cette documentation regroupe les informations nécessaires pour développer,
tester et intégrer l'API Django du projet Weeb.

## Environnements actuels

| Service | Adresse | Branche |
| --- | --- | --- |
| Backend staging | `https://weeb-backend-staging.onrender.com` | Backend `dev` |
| Backend production | `https://weeb-backend-production.onrender.com` | Backend `main` |
| Frontend Sylvain production | `https://weeb-kappa.vercel.app` | Frontend `main` |
| Frontend Guillaume production | `https://weeb-guillaume-amselle-andreux.vercel.app` | Frontend `main` |
| Frontend Gaëlle production | `https://weeb-hazel.vercel.app` | Frontend `main` |
| Frontend Sylvain staging | `https://weeb-git-dev-sylvqinz.vercel.app` | Frontend `dev` |
| Autres frontends staging | URLs Vercel Preview stables à renseigner | Frontend `dev` |
| Documentation | `https://weeb-project.github.io/weeb_backend/` | Documentation de `dev` |

Les domaines principaux Vercel utilisent le backend production. Les Previews
des branches frontend `dev` utilisent le backend staging.

## Pour commencer

- [Connecter un frontend au backend](backend/FRONTEND_BACKEND.md)
- [Consulter les endpoints](backend/ENDPOINTS.md)
- [Configurer les variables d'environnement](backend/ENVIRONMENT.md)
- [Comprendre le staging et la production](devOps/ENVIRONMENTS.md)
- [Déployer et tester avec le staging](devOps/FRONTEND_STAGING.md)
- [Comprendre la conteneurisation Docker](devOps/DOCKER.md)
- [Comprendre l'intégration continue](devOps/CI.md)
- [Comprendre le pipeline Docker et CI/CD](devOps/PIPELINE_CICD.md)

## Mise à jour de la documentation

Les pages sont générées automatiquement après chaque modification de la
documentation fusionnée dans `dev`. Il suffit donc de modifier les fichiers
Markdown du dossier `documentation/`, puis de suivre le cycle habituel :

```text
branche de travail → Pull Request vers dev → fusion → publication GitHub Pages
```

Les secrets, rapports locaux et documents de travail non versionnés ne sont pas
publiés sur ce site.
