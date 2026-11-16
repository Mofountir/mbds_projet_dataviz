"""Choix et chargement des données du domaine « coordonnées parallèles ».

Étape 1 du pipeline : les CSV bruts Kaggle (data/01_raw, ou le dossier indiqué
par la variable LOCAL_STORAGE) sont lus ici ; la table préparée par
``transforms.py`` est ensuite lue depuis data/03_primary par l'application.
"""

import os
from pathlib import Path

import pandas as pd

KAGGLE_SOURCE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "translation": "product_category_name_translation.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
}

PRIMARY_DIR = Path("data/03_primary/coordonnees")
PRIMARY_ORDERS = PRIMARY_DIR / "orders.parquet"

# Jeux de données proposés dans l'interface : mêmes colonnes, période différente.
# Les mois 2016 et septembre-octobre 2018 contiennent très peu de commandes.
DATASETS = {
    "Olist 2017 (année complète)": ("2017-01-01", "2018-01-01"),
    "Olist 2018 (janvier à août)": ("2018-01-01", "2018-09-01"),
    "Olist — toutes les commandes": (None, None),
}


def raw_dir() -> Path:
    """Dossier des CSV bruts : LOCAL_STORAGE s'il est défini, sinon data/01_raw."""
    local = os.environ.get("LOCAL_STORAGE")
    if local and local != "change-me":
        return Path(local)
    return Path("data/01_raw")


def load_raw(name: str, folder: Path | None = None) -> pd.DataFrame:
    """Lit un CSV brut Olist par son nom court (voir RAW_FILES)."""
    path = (folder or raw_dir()) / RAW_FILES[name]
    return pd.read_csv(path)


def load_orders() -> pd.DataFrame:
    """Table préparée : une ligne par commande livrée et notée."""
    if not PRIMARY_ORDERS.exists():
        raise FileNotFoundError(
            f"{PRIMARY_ORDERS} introuvable. Lancer : "
            "python -m mbds_projet_dataviz.domains.coordonnees.transforms"
        )
    return pd.read_parquet(PRIMARY_ORDERS)
