# Documentation Weeb Backend

Cette documentation regroupe les informations nécessaires pour développer,
tester et intégrer l'API Django du projet Weeb.

## Environnements actuels

| Service | Adresse | Source |
| --- | --- | --- |
| Backend de staging | `https://weeb-backend-staging.onrender.com` | Branche `dev` |
| Frontends validé | `https://weeb-kappa.vercel.app`, `https://weeb-guillaume-amselle-andreux.vercel.app`  | Déploiement Vercel |
| Documentation | `https://weeb-project.github.io/weeb_backend/` | Dossier `documentation/` de `dev` |

## Pour commencer

- [Connecter un frontend au backend](backend/FRONTEND_BACKEND.md)
- [Consulter les endpoints](backend/ENDPOINTS.md)
- [Configurer les variables d'environnement](backend/ENVIRONMENT.md)
- [Déployer et tester avec le staging](devOps/FRONTEND_STAGING.md)

## Mise à jour de la documentation

Les pages sont générées automatiquement après chaque modification de la
documentation fusionnée dans `dev`. Il suffit donc de modifier les fichiers
Markdown du dossier `documentation/`, puis de suivre le cycle habituel :

```text
branche de travail → Pull Request vers dev → fusion → publication GitHub Pages
```

Les secrets, rapports locaux et documents de travail non versionnés ne sont pas
publiés sur ce site.
