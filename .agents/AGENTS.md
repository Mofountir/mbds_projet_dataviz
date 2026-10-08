# AGENTS.md — spécification du projet

Ces consignes s'appliquent à tout le dépôt, quel que soit l'assistant de code. Le `README.md` explique comment démarrer ; ce fichier décrit le résultat attendu et les règles de réalisation. Suivre la demande de la tâche en cours lorsqu'elle précise un choix encore ouvert ici.

## Objectif

Construire un dashboard Streamlit sur les données e-commerce Olist : une page **About** pour présenter le projet et son fil conducteur, puis une page de reporting interactif par domaine traité par les quatre membres de l'équipe. Chaque domaine choisit ses jeux de données, prépare ses indicateurs et explique ce que montrent ses visualisations. Ne pas inventer de métriques ou de résultats absents des données.

## Responsabilités des fichiers

| Emplacement | Responsabilité |
| --- | --- |
| `src/mbds_projet_dataviz/domains/<domaine>/datasets.py` | Sélectionner et charger les fichiers nécessaires au domaine. |
| `src/mbds_projet_dataviz/domains/<domaine>/transforms.py` | Nettoyer, joindre, agréger et produire les données préparées. |
| `src/mbds_projet_dataviz/domains/<domaine>/charts.py` | Construire les figures et les fonctions de visualisation du domaine. |
| `src/mbds_projet_dataviz/pages/<domaine>.py` | Afficher les filtres, graphiques, indicateurs et commentaires du domaine ; éviter les transformations lourdes dans la page. |
| `src/mbds_projet_dataviz/pages/about.py` | Présenter le sujet, les données, les domaines étudiés et le parcours de lecture. |
| `src/mbds_projet_dataviz/shared/` | Héberger uniquement les fonctions réellement communes à plusieurs domaines. |
| `main.py` | Définir le point d'entrée et enregistrer les pages dans la navigation. |
| `notebooks/` | Explorer et prototyper ; l'application ne doit pas dépendre d'un notebook. |

Créer `__init__.py` dans chaque nouveau sous-package de `domains/`. Utiliser des noms Python en `snake_case` et des imports depuis `mbds_projet_dataviz`. Ne pas déplacer du code métier vers `shared/` simplement pour le rendre accessible à une page.

## Contrat des données

- `data/01_raw/` est un montage local en lecture seule via `LOCAL_STORAGE` : ne pas modifier ni commiter les CSV bruts.
- `data/02_intermediate/` sert aux résultats temporaires locaux ; son contenu n'est pas versionné.
- `data/03_primary/` contient les données préparées nécessaires à l'application publiée. Le conteneur de production copie ce dossier, mais n'a pas accès au montage `data/01_raw/`.
- Garder dans le domaine le code permettant de refaire les transformations à partir des données brutes. Rendre explicites les clés de jointure, le niveau d'agrégation et la définition des indicateurs afin d'éviter les doubles comptes.
- Ne pas commiter `.env`, identifiants, secrets ni chemins personnels. Utiliser des chemins relatifs au projet pour lire les données dans l'application.

## Critères pour une page de domaine

- Expliquer la question traitée, les jeux de données utilisés et la définition des indicateurs.
- Proposer des filtres utiles et des graphiques qui réagissent à ces filtres, avec titres, unités et légendes lisibles.
- Accompagner les graphiques d'une interprétation factuelle et signaler les limites des données quand elles affectent la lecture.
- Charger les données nécessaires à la page depuis `data/03_primary/`, gérer clairement l'absence de données et enregistrer la page dans `main.py`.

## Environnement et livraison

- Travailler avec Python 3.13, `uv` et le Dev Container du dépôt. Les dépendances déclarées sont dans `pyproject.toml` et figées dans `uv.lock` ; mettre à jour les deux si une nouvelle dépendance est indispensable.
- Créer une branche `<num_issue>_<branch_name>` depuis `main`. Garder la PR centrée sur un domaine ; coordonner les changements de `main.py`, `pages/about.py` et `shared/` avec l'équipe.
- Avant la PR, exécuter `uv run ruff check .` et `uv run ruff format --check .`, puis vérifier localement la page concernée. Les hooks dans `githooks/` et la CI contrôlent le lint, le format, les imports et le build Docker.
- Dans la PR, résumer les sources, transformations, indicateurs, visualisations et vérifications effectuées. Fusionner vers `main` après CI réussie et revue d'un autre membre.
- Ne modifier Docker, Dev Container, CI/CD ou Render que si la tâche le demande ou si leur changement est nécessaire à la fonctionnalité.
