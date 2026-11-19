"""Jeu de données du domaine temps.

``orders.parquet`` (pipeline commun) : une ligne par commande, toutes les commandes
passées (quel que soit leur statut) avec leur date d'achat et, pour les commandes
livrées, l'indicateur de retard.
"""

import pandas as pd

from mbds_projet_dataviz.shared.data import load_primary

ORDER_COLUMNS = ["order_id", "purchase_date", "is_late"]


def load_orders() -> pd.DataFrame | None:
    return load_primary("orders", ORDER_COLUMNS)
