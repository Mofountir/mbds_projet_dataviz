# MBDS Projet DataViz

Dashboard Streamlit sur les données e-commerce Olist : [ouvrir l'application](https://mbds-projet-dataviz.onrender.com).

Documentation : [Doc.md](./docs/DOC.md)

## Contribuer

Pré-requis : Docker Desktop installé et démarré, VS Code et l'extension **Dev Containers**.

```bash
git clone https://github.com/Mofountir/mbds_projet_dataviz.git
cd mbds_projet_dataviz
cp .env.example .env
```

Dans `.env`, remplacer `change-me` par le chemin absolu du dossier contenant les CSV : `LOCAL_STORAGE=/chemin/vers/les/csv`.

Ouvrir le dossier dans VS Code → **Dev Containers: Reopen in Container**. 

Tester l'app le terminal du conteneur :

```bash
streamlit run main.py
```

Application locale : [localhost:8501](http://localhost:8501).


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
| [`data/01_raw/`](data/01_raw/) → [`data/02_intermediate/`](data/02_intermediate/) → [`data/03_primary/`](data/03_primary/) | CSV bruts locaux → résultats intermédiaires locaux → données gold connecté à l'app |


Strategie de visualisation : [API Streamlit Charts](https://docs.streamlit.io/develop/api-reference/charts) · [exemples Plotly](https://plotly.com/python/).

## Règles de contribution

1. Créer une branche `<num_issue>_<branch_name>` depuis `main`. Faire les commits et les pushs depuis le terminal du conteneur. Coordonner les modifications de `main.py`, `pages/about.py` et `shared/` avec l'équipe.
2. Avant la PR, lancer `uv run ruff check .` et `uv run ruff format --check .`. Si besoin : `uv run ruff check . --fix` puis `uv run ruff format .`.
3. Ouvrir une PR vers `main` sur github: indiquer les données choisies, les transformations et les visualisations ; attendre la CI et une revue d'un autre membre avant le GO pour merger.

Spécification commune pour l'équipe et les assistants IA : [AGENTS.md](.agents/AGENTS.md).
