# Maintenir une activité sur Supabase

Le workflow `.github/workflows/supabase-keepalive.yml` exécute `SELECT 1` sur
les bases de staging et de production toutes les six heures, via deux connexions
PostgreSQL chiffrées et deux jobs indépendants. Il ne lit aucune donnée métier
et ne modifie aucune table. Il fonctionne indépendamment du serveur Django et
ne nécessite pas de nouvelle route publique.

Supabase peut mettre en pause les projets gratuits ayant une activité trop
faible sur sept jours. Quelques requêtes quotidiennes peuvent réduire ce risque,
mais ce mécanisme ne garantit pas l'absence de pause. Seul un forfait payant
exclut la pause pour inactivité :
[documentation Supabase](https://supabase.com/docs/guides/platform/free-project-pausing).

## Activation

1. Dans le dépôt GitHub, ouvrir **Settings → Secrets and variables → Actions**.
2. Ajouter les secrets de dépôt suivants avec les paramètres PostgreSQL des deux
   projets Supabase :

   | Staging | Production |
   | --- | --- |
   | `STAGING_DB_NAME` | `PROD_DB_NAME` |
   | `STAGING_DB_USER` | `PROD_DB_USER` |
   | `STAGING_DB_PASSWORD` | `PROD_DB_PASSWORD` |
   | `STAGING_DB_HOST` | `PROD_DB_HOST` |
   | `STAGING_DB_PORT` | `PROD_DB_PORT` |

   Ne pas utiliser une clé API Supabase à la place du mot de passe PostgreSQL.
   Pour les runners GitHub hébergés, utiliser de préférence les paramètres du
   **Session pooler** fournis dans **Connect** sur Supabase, compatibles IPv4
   (reprendre exactement l'hôte, l'utilisateur et le port affichés). Le nom de
   base est normalement `postgres` et le port du Session pooler est `5432`.
3. Intégrer le workflow dans la **branche par défaut du dépôt** : les tâches
   planifiées GitHub ne démarrent que depuis cette branche.
4. Dans **Actions → Supabase keepalive → Run workflow**, lancer une première
   exécution et vérifier le succès des jobs **Keepalive Supabase staging** et
   **Keepalive Supabase production**.

Les secrets sont transmis uniquement à l'étape de connexion. Un échec de
connexion ou une configuration manquante fait échouer uniquement le job de
l'environnement concerné ; consulter les exécutions et activer les
notifications GitHub Actions en cas d'échec.

## Limites

- Si le projet est déjà en pause, le réactiver depuis le dashboard Supabase
  avant de lancer le workflow. La requête ne réactive pas un projet en pause.
- GitHub peut retarder les exécutions planifiées. Sur un dépôt public, les
  workflows planifiés sont désactivés après 60 jours sans activité sur le dépôt.
  Il faut alors les réactiver depuis l'onglet Actions. Voir la
  [documentation GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows).
- Les restrictions réseau Supabase doivent autoriser la connexion du runner.
- Le workflow n'est actif qu'après son intégration sur GitHub et la configuration
  des secrets ; sa présence en local ne suffit pas.
