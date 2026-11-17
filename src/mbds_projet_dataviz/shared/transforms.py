"""Filtrage commun des commandes Olist."""

import pandas as pd

from mbds_projet_dataviz.shared.datasets import DATASETS


def filter_dataset(orders: pd.DataFrame, name: str) -> pd.DataFrame:
    """Garde la période du jeu de données choisi (voir DATASETS)."""
    start, end = DATASETS[name]
    mask = pd.Series(True, index=orders.index)
    if start:
        mask &= orders["purchase_date"] >= start
    if end:
        mask &= orders["purchase_date"] < end
    return orders[mask]
