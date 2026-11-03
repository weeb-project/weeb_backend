# Documentation MkDocs et GitHub Pages

La documentation technique du backend est construite avec MkDocs et publiée
automatiquement sur GitHub Pages.

## Adresse de la documentation

Une fois GitHub Pages activé, le site est disponible à l'adresse suivante :

```text
https://weeb-project.github.io/weeb_backend/
```

## Organisation des fichiers

Les sources de la documentation sont placées dans le dossier
`documentation/` :

```text
documentation/
├── index.md
├── backend/
├── devOps/
└── updates/
```

Le fichier `mkdocs.yml`, situé à la racine du dépôt, configure notamment :

- le nom et l'adresse du site ;
- le thème Material for MkDocs ;
- la navigation ;
- la recherche ;
- les documents exclus de la publication.

## Installer les dépendances

Depuis la racine du projet, avec l'environnement virtuel Python activé :

```bash
pip install -r requirements-docs.txt
```

Ces dépendances servent uniquement à construire et prévisualiser la
documentation. Elles ne sont pas nécessaires au fonctionnement de Django.

## Prévisualiser la documentation en local

Lancer le serveur de développement MkDocs :

```bash
mkdocs serve
```

La documentation est alors accessible à l'adresse suivante :

```text
http://127.0.0.1:8000
```

MkDocs actualise automatiquement la page lorsqu'un fichier Markdown ou la
configuration est modifié. Ce serveur est réservé au développement local.

## Vérifier la documentation avant de pousser

Exécuter la même compilation stricte que dans GitHub Actions :

```bash
mkdocs build --strict
```

La commande échoue lorsqu'elle détecte une erreur ou un avertissement, par
exemple une page déclarée dans la navigation mais introuvable.

Le site généré est placé dans le dossier `site/`. Ce dossier est ignoré par Git
car GitHub Actions le reconstruit à chaque publication.

## Ajouter une page

1. Créer un fichier Markdown dans le sous-dossier adapté de `documentation/`.
2. Ajouter la page à la section `nav` de `mkdocs.yml`.
3. Lancer `mkdocs build --strict`.
4. Commiter la page et la modification de `mkdocs.yml` sur une branche de
   travail.
5. Ouvrir une Pull Request vers `dev`.

Exemple de déclaration dans `mkdocs.yml` :

```yaml
nav:
  - DevOps:
      - Nouvelle page: devOps/NOUVELLE_PAGE.md
```

Les chemins déclarés dans `nav` sont relatifs au dossier `documentation/`.

## Publication automatique

Le workflow `.github/workflows/documentation.yml` surveille la branche `dev`.
Il est déclenché lorsque les fichiers suivants sont modifiés :

- `documentation/**` ;
- `mkdocs.yml` ;
- `requirements-docs.txt` ;
- le workflow lui-même.

Le cycle de publication est le suivant :

```text
branche de travail
    → Pull Request vers dev
    → fusion dans dev
    → compilation MkDocs
    → déploiement GitHub Pages
```

Le workflow peut aussi être lancé manuellement depuis l'onglet **Actions** de
GitHub avec l'action **Run workflow**.

## Première activation de GitHub Pages

Cette opération ne doit être réalisée qu'une seule fois par un membre disposant
des droits nécessaires sur le dépôt :

1. Ouvrir le dépôt `weeb-project/weeb_backend` sur GitHub.
2. Aller dans **Settings**, puis **Pages**.
3. Dans **Build and deployment**, sélectionner **GitHub Actions** comme source.
4. Fusionner une modification de la documentation dans `dev`, ou lancer le
   workflow manuellement.
5. Vérifier le déploiement dans l'onglet **Actions**.

## Documents non publiés

Les documents locaux suivants sont explicitement exclus de la construction :

```text
documentation/backend/RAPPORT_BACKEND.md
documentation/devOps/TODO_BEFORE_PRODUCTION.md
```

Ils ne doivent pas être ajoutés à Git. Leur exclusion dans `mkdocs.yml` évite
également qu'une compilation locale les ajoute accidentellement au site.

## Diagnostic

Si la publication échoue :

1. ouvrir le workflow **Publish documentation** dans l'onglet **Actions** ;
2. consulter l'étape en erreur ;
3. exécuter `mkdocs build --strict` localement ;
4. vérifier les chemins déclarés dans `nav` ;
5. vérifier que GitHub Pages utilise bien **GitHub Actions** comme source.

Une modification présente uniquement sur une branche de travail n'est pas
publiée. Elle doit d'abord être fusionnée dans `dev`.
