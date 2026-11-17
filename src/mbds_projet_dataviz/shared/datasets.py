"""Sources Olist, périodes et lectures communes aux pages 3 et 4."""

import os
from pathlib import Path

import pandas as pd
import streamlit as st

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

# Table commune produite par domains.coordonnees.transforms ; chemin conservé
# pour réutiliser les données déjà livrées en production.
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


@st.cache_data
def load_orders() -> pd.DataFrame:
    """Table préparée : une ligne par commande livrée et notée."""
    if not PRIMARY_ORDERS.exists():
        raise FileNotFoundError(
            f"{PRIMARY_ORDERS} introuvable. Lancer : "
            "python -m mbds_projet_dataviz.domains.coordonnees.transforms"
        )
    return pd.read_parquet(PRIMARY_ORDERS)
