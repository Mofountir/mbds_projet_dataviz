# MBDS Projet DataViz

Application Streamlit de visualisation du jeu de données Olist.

## Démarrer en développement

1. Installer Docker Desktop et l'extension VS Code « Dev Containers ».
2. Copier `.env.example` vers `.env`, puis remplacer `LOCAL_STORAGE` par le chemin absolu du dossier local contenant les CSV.
3. Ouvrir le dépôt dans VS Code et choisir « Dev Containers: Reopen in Container ».
4. Dans le terminal du Dev Container, lancer `streamlit run main.py`.

Le dossier de CSV est monté en lecture seule dans `/app/data/01_raw`. Les données brutes ne sont pas versionnées.

## Contribuer

Effectuer les commits et les pushs depuis le terminal du Dev Container. Les hooks `pre-commit` et `pre-push` y sont installés automatiquement au démarrage. Le premier vérifie les fichiers Python modifiés avec Ruff. Le second vérifie le projet entier et ses imports.

Pour corriger un échec Ruff :

```bash
uv run ruff check . --fix
uv run ruff format .
```

Pour réinstaller les hooks dans un clone existant :

```bash
uv run pre-commit install --hook-type pre-commit --config githooks/pre-commit.yaml
uv run pre-commit install --hook-type pre-push --config githooks/pre-push.yaml
```

Les pull requests vers `main` déclenchent la CI. Une CI réussie sur `main` déclenche le déploiement Render. Les données préparées destinées à l'application publiée sont placées dans `data/03_primary`.
