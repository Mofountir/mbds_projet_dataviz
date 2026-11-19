# MBDS Projet DataViz

Dashboard Streamlit sur les données e-commerce Olist : [ouvrir l'application](https://mbds-projet-dataviz.onrender.com).

Documentation : [Doc.md](./docs/DOC.md)

## Contribuer

Pré-requis : Git et `uv`. Le développement se fait directement sur la machine,
avec l'éditeur de son choix. Docker sert uniquement au déploiement sur Render.

À faire une fois après le clonage, dans un terminal local :

```bash
git clone https://github.com/Mofountir/mbds_projet_dataviz.git
cd mbds_projet_dataviz
uv sync --locked --dev
uv run --no-sync pre-commit install --hook-type pre-commit --config githooks/pre-commit.yaml
uv run --no-sync pre-commit install --hook-type pre-push --config githooks/pre-push.yaml
```

`uv` prépare Python 3.13 et l'environnement `.venv` avec les versions de `uv.lock`.
L'installation des hooks est propre à chaque clone : chaque membre la fait une
fois. Si ce clone était utilisé dans un conteneur, relancer les deux commandes
`pre-commit install` depuis la machine pour remplacer les anciens chemins.

Lancer l'application :

```bash
uv run streamlit run main.py
```

Application locale : [localhost:8501](http://localhost:8501).

Les données préparées dans `data/03_primary/` suffisent pour lancer l'application.
Les CSV bruts ne sont nécessaires que pour reconstruire les données. Pour cela,
passer leur dossier au script de transformation :

```bash
uv run python -m mbds_projet_dataviz.domains.coordonnees.transforms /chemin/vers/les/csv
```

On peut aussi copier `.env.example` en `.env`, renseigner `LOCAL_STORAGE`, puis
exécuter :

```bash
uv run --env-file .env python -m mbds_projet_dataviz.domains.coordonnees.transforms
```

## Vérifications et déploiement

- Avant chaque commit, les hooks vérifient les fichiers Python modifiés avec Ruff.
- Avant chaque push, ils vérifient le code du projet, le format et les imports.
- Les tests automatisés seront ajoutés plus tard ; `tests/` est réservé à cet effet.
- Après revue et merge d'une PR dans `main`, Render construit l'image et déploie
  automatiquement le nouveau commit. Il n'y a plus de workflow GitHub Actions.

Les hooks sont locaux et peuvent être contournés : ils ne remplacent pas la revue
par un autre membre. Render ne lance pas ces hooks.

Le seul Dockerfile est `docker/Dockerfile.prod`. Il installe les dépendances de
production et copie l'application et ses données préparées. `deploy/render.yaml`
définit la branche `main`, le déploiement à chaque commit et le contrôle de santé.

## Structure du projet

| Emplacement | Ce que tu y mets |
| --- | --- |
| [`notebooks/`](notebooks/) | Essais et exploration ; pas de logique nécessaire à l'application. |
| [`domains/`](src/mbds_projet_dataviz/domains/) → `<domaine>/datasets.py` | Choix et chargement des jeux de données de ton domaine. |
| `<domaine>/transforms.py` | Nettoyage, jointures, calculs et préparation des données. |
| `<domaine>/charts.py` | Fonctions qui construisent les graphiques de ton domaine. |
| [`pages/`](src/mbds_projet_dataviz/pages/) → `<domaine>.py` | Page Streamlit : filtres, graphiques et explication des résultats. |
| `pages/about.py` | Présentation du projet (Story telling) |
| [`shared/`](src/mbds_projet_dataviz/shared/) | Code réutilisé par au moins deux domaines ; sinon, garde-le dans ton domaine. |
| [`main.py`](main.py) | Enregistrement des pages et navigation de l'application. |
| [`githooks/`](githooks/) | Vérifications locales avant commit et push. |
| [`tests/`](tests/) | Dossier réservé aux futurs tests automatisés. |
| [`docker/Dockerfile.prod`](docker/Dockerfile.prod) et [`deploy/render.yaml`](deploy/render.yaml) | Construction et déploiement sur Render. |
| [`data/01_raw/`](data/01_raw/) → [`data/02_intermediate/`](data/02_intermediate/) → [`data/03_primary/`](data/03_primary/) | CSV bruts locaux → résultats intermédiaires locaux → données gold connecté à l'app |


Strategie de visualisation : [API Streamlit Charts](https://docs.streamlit.io/develop/api-reference/charts) · [exemples Plotly](https://plotly.com/python/).

## Règles de contribution

1. Créer une branche `<num_issue>_<branch_name>` depuis `main`. Faire les commits et les pushs depuis son terminal local, avec les hooks installés. Coordonner les modifications de `main.py`, `pages/about.py` et `shared/` avec l'équipe.
2. Avant la PR, lancer `uv run ruff check .` et `uv run ruff format --check .`. Si besoin : `uv run ruff check . --fix` puis `uv run ruff format .`.
3. Vérifier localement les pages modifiées, puis ouvrir une PR vers `main` sur GitHub : indiquer les données choisies, les transformations, les visualisations et les vérifications effectuées. Fusionner après revue d'un autre membre ; Render déploie ensuite automatiquement.

Spécification commune pour l'équipe et les assistants IA : [AGENTS.md](.agents/AGENTS.md).
