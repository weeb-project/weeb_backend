# Monitoring et alertes

Le monitoring du projet Weeb combine plusieurs outils complémentaires. Aucun
outil unique ne couvre à la fois les erreurs applicatives, les échecs de
déploiement, la disponibilité HTTP et l'état des bases PostgreSQL.

## Couverture retenue

| Outil | Élément surveillé | Environnements |
| --- | --- | --- |
| Sentry | Exceptions Django, contexte applicatif et disponibilité HTTP | Staging et production |
| Render | Échecs de build et de déploiement | Staging et production |
| Route `/health/` | Disponibilité de Django et Gunicorn | Staging et production |
| GitHub Actions | Exécution des tests et état du pipeline CI/CD | `dev` et `main` |
| Keepalive Supabase | Connexion PostgreSQL en lecture seule | Staging et production |

## Sentry

Deux projets Sentry indépendants sont utilisés afin de ne pas mélanger les
erreurs de test avec les incidents réels :

- un projet pour le backend de staging ;
- un projet pour le backend de production.

Chaque membre utilise son compte Sentry personnel pour accéder aux projets :
aucun mot de passe de compte n'est partagé ou versionné. Les alertes du monitor
de production sont envoyées à l'adresse commune `projet.ggs@gmail.com`.

Chaque service Render possède sa propre configuration :

```env
SENTRY_DSN=<DSN du projet correspondant>
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=0.1
```

La production utilise `SENTRY_ENVIRONMENT=production` et peut conserver un
taux plus faible, par exemple `0.05`, afin de limiter le volume de transactions
collectées. Le DSN est configuré dans Render et n'est pas écrit dans le dépôt.

L'initialisation Django est effectuée uniquement lorsqu'un DSN est présent :

```python
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
```

`send_default_pii=False` limite l'envoi automatique de données personnelles.
La capture automatique des erreurs a été validée sur les deux environnements.
La route volontairement fautive utilisée pendant cette validation doit rester
temporaire et être supprimée immédiatement après le test.

## Notifications Render

Les notifications de service Render sont configurées sur les échecs. Elles
signalent un build ou un déploiement qui ne termine pas correctement, mais ne
remplacent pas Sentry : un service peut être démarré tout en rencontrant des
exceptions lors du traitement d'une requête.

## Contrôle de disponibilité

La route publique suivante constitue la sonde de disponibilité :

```text
GET /health/
```

Elle doit répondre avec le statut HTTP `200` et le contenu :

```json
{"status": "ok"}
```

Cette route confirme que le processus Django/Gunicorn répond. Elle ne garantit
pas à elle seule que Supabase ou les services externes sont disponibles.

### Monitor Sentry de production

Un monitor HTTP Sentry contrôle directement la route de santé de production :

```text
https://weeb-backend-production.onrender.com/health/
```

Il attend une réponse HTTP `200` et envoie une alerte à
`projet.ggs@gmail.com` si le contrôle échoue. Ce monitor complète la capture
des exceptions Django : il peut signaler une indisponibilité même lorsqu'aucune
requête utilisateur ne produit d'événement applicatif.

Sur une offre Render gratuite, une sonde périodique peut empêcher la mise en
veille du service. Le monitor est donc limité à la production ; aucun monitor
HTTP permanent n'est activé sur le staging. Ce choix évite les alertes de test,
limite les requêtes inutiles et réduit la consommation de ressources.

## Réaction à un incident

1. confirmer l'indisponibilité avec `/health/` ;
2. consulter l'état du dernier déploiement et les logs Render ;
3. consulter l'exception et son environnement dans Sentry ;
4. vérifier la CI et le SHA de l'image Docker actuellement déployée ;
5. vérifier Supabase si l'erreur concerne PostgreSQL ;
6. si nécessaire, redéployer un tag Docker SHA précédemment validé ;
7. vérifier de nouveau `/health/` et les parcours critiques.

## Limites connues

- le monitor Sentry vérifie une route HTTP, mais ne teste pas tous les parcours
  métier ni toutes les dépendances ;
- `/health/` ne teste volontairement pas toutes les dépendances ;
- les offres gratuites limitent la rétention, la fréquence des contrôles et les
  fonctions avancées d'alerte ;
- le monitoring doit rester proportionné au projet afin de ne pas générer plus
  de trafic et de consommation que nécessaire.
