"""Jeux de données du domaine livraison.

- ``orders.parquet`` (pipeline commun) : commandes livrées, état et ville du client,
  dates, délai, retard, note et vendeur principal.
- ``sellers.parquet`` (pipeline commun) : localisation des vendeurs.
- ``brazil_states.geojson`` : contours des 27 États, issu de
  ``codeforamerica/click_that_hood`` (coordonnées arrondies à 3 décimales).
"""

import json

import pandas as pd
import streamlit as st

from mbds_projet_dataviz.shared.data import load_primary
from mbds_projet_dataviz.shared.paths import PRIMARY_DIR

GEOJSON_PATH = PRIMARY_DIR / "brazil_states.geojson"

ORDER_COLUMNS = [
    "order_id",
    "order_status",
    "purchase_date",
    "customer_state",
    "customer_city",
    "customer_lat",
    "customer_lng",
    "main_seller_state",
    "items_value",
    "delivery_days",
    "is_late",
    "review_score",
]


def load_delivered_orders() -> pd.DataFrame | None:
    orders = load_primary("orders", ORDER_COLUMNS)
    if orders is None:
        return None
    delivered = orders[
        (orders["order_status"] == "delivered") & orders["delivery_days"].notna()
    ]
    return delivered.drop(columns="order_status")


def load_sellers() -> pd.DataFrame | None:
    return load_primary("sellers")


@st.cache_data(show_spinner=False)
def load_states_geojson() -> dict | None:
    if not GEOJSON_PATH.exists():
        return None
    return json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
