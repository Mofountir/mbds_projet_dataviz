"""Filtre global « Jeu de données », commun à toutes les pages.

Le sélecteur est affiché une seule fois, dans ``main.py``, avant la page courante :
sa valeur est donc conservée quand on change de page. Les pages ne créent pas leur
propre sélecteur, elles lisent la valeur avec ``selected_dataset()``.
"""

import streamlit as st

from mbds_projet_dataviz.shared.datasets import DATASETS

DATASET_KEY = "dataset"
DEFAULT_DATASET = "Olist — toutes les commandes"


def dataset_selector() -> str:
    """Affiche le sélecteur dans la barre latérale (à appeler une fois, dans main.py)."""
    names = list(DATASETS)
    return st.sidebar.selectbox(
        "Jeu de données",
        names,
        index=names.index(DEFAULT_DATASET),
        key=DATASET_KEY,
    )


def selected_dataset() -> str:
    """Jeu de données choisi (valeur par défaut si la page est lancée seule)."""
    return st.session_state.get(DATASET_KEY, DEFAULT_DATASET)
