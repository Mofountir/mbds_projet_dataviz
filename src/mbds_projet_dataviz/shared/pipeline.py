"""Pipeline commun : CSV bruts Olist -> tables préparées dans data/03_primary.

Lancer depuis la racine du projet (dans le conteneur, data/01_raw est monté) :

    uv run python -m mbds_projet_dataviz.shared.pipeline [--raw-dir CHEMIN]

Tables produites :

- ``orders.parquet`` : 1 ligne par commande (clé ``order_id``).
- ``order_items.parquet`` : 1 ligne par article (clé ``order_id`` + ``order_item_id``).
- ``sellers.parquet`` : 1 ligne par vendeur (clé ``seller_id``).

Définitions :

- ``delivery_days`` : jours entre l'achat et la livraison au client (commandes
  livrées uniquement).
- ``is_late`` : date de livraison client postérieure à la date estimée, comparée au
  jour près (une livraison le jour estimé est à l'heure) ; vide si la commande
  n'a pas été livrée.
- ``review_score`` : note de l'avis le plus récent de la commande.
- ``items_value`` / ``freight_value`` : somme des prix et des frais de port des
  articles de la commande.
- ``main_category`` : catégorie de l'article le plus cher de la commande.
- ``customer_lat`` / ``customer_lng`` : moyenne des points de géolocalisation du
  préfixe de code postal (même règle pour les vendeurs).
- ``distance_km`` : distance à vol d'oiseau entre le client et le vendeur principal
  (vide si l'un des deux n'est pas géolocalisé).
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mbds_projet_dataviz.shared.paths import PRIMARY_DIR, RAW_DIR

UNKNOWN_CATEGORY = "unknown"
BRAZIL_LAT = (-34.0, 5.5)
BRAZIL_LNG = (-74.0, -34.0)
EARTH_RADIUS_KM = 6371.0

RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "categories": "product_category_name_translation.csv",
}

ZIP_DTYPE = {
    "customer_zip_code_prefix": "string",
    "seller_zip_code_prefix": "string",
    "geolocation_zip_code_prefix": "string",
}


def read_raw(raw_dir: Path) -> dict[str, pd.DataFrame]:
    missing = [name for name in RAW_FILES.values() if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Fichiers absents de {raw_dir} : {', '.join(missing)}")
    return {
        key: pd.read_csv(raw_dir / name, dtype=ZIP_DTYPE, encoding="utf-8-sig")
        for key, name in RAW_FILES.items()
    }


def haversine_km(
    lat1: pd.Series, lng1: pd.Series, lat2: pd.Series, lng2: pd.Series
) -> pd.Series:
    """Distance à vol d'oiseau (km) entre deux points."""
    lat1, lng1, lat2, lng2 = (np.radians(s) for s in (lat1, lng1, lat2, lng2))
    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def zip_centroids(geolocation: pd.DataFrame) -> pd.DataFrame:
    """Un point (lat, lng moyens) par préfixe de code postal.

    Les points hors de l'emprise du Brésil (erreurs de saisie) sont écartés.
    """
    in_brazil = geolocation["geolocation_lat"].between(*BRAZIL_LAT) & geolocation[
        "geolocation_lng"
    ].between(*BRAZIL_LNG)
    return (
        geolocation[in_brazil]
        .groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean"))
        .rename(columns={"geolocation_zip_code_prefix": "zip_prefix"})
    )


def build_products(products: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    out = products.merge(categories, on="product_category_name", how="left")
    # Catégories sans traduction : on garde le nom portugais.
    out["category"] = (
        out["product_category_name_english"]
        .fillna(out["product_category_name"])
        .fillna(UNKNOWN_CATEGORY)
    )
    return out[["product_id", "category", "product_weight_g"]]


def build_sellers(sellers: pd.DataFrame, centroids: pd.DataFrame) -> pd.DataFrame:
    out = sellers.merge(
        centroids, left_on="seller_zip_code_prefix", right_on="zip_prefix", how="left"
    )
    return out.rename(
        columns={
            "seller_zip_code_prefix": "seller_zip_prefix",
            "lat": "seller_lat",
            "lng": "seller_lng",
        }
    )[
        [
            "seller_id",
            "seller_zip_prefix",
            "seller_city",
            "seller_state",
            "seller_lat",
            "seller_lng",
        ]
    ]


def build_items(
    items: pd.DataFrame, products: pd.DataFrame, sellers: pd.DataFrame
) -> pd.DataFrame:
    out = items.merge(products, on="product_id", how="left").merge(
        sellers[["seller_id", "seller_state"]], on="seller_id", how="left"
    )
    out["category"] = out["category"].fillna(UNKNOWN_CATEGORY)
    return out[
        [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "seller_state",
            "category",
            "price",
            "freight_value",
            "product_weight_g",
        ]
    ]


def order_items_summary(items: pd.DataFrame) -> pd.DataFrame:
    totals = items.groupby("order_id").agg(
        n_items=("order_item_id", "count"),
        n_sellers=("seller_id", "nunique"),
        items_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
    )
    # Article le plus cher : porte la catégorie et le vendeur principaux.
    main = (
        items.sort_values(["order_id", "price"], ascending=[True, False])
        .drop_duplicates("order_id")
        .set_index("order_id")[["category", "seller_id"]]
        .rename(columns={"category": "main_category", "seller_id": "main_seller_id"})
    )
    return totals.join(main).reset_index()


def order_payments_summary(payments: pd.DataFrame) -> pd.DataFrame:
    totals = payments.groupby("order_id").agg(
        payment_value=("payment_value", "sum"),
        payment_installments=("payment_installments", "max"),
    )
    main = (
        payments.sort_values(["order_id", "payment_value"], ascending=[True, False])
        .drop_duplicates("order_id")
        .set_index("order_id")[["payment_type"]]
    )
    return totals.join(main).reset_index()


def latest_review(reviews: pd.DataFrame) -> pd.DataFrame:
    reviews = reviews.assign(
        review_answer_timestamp=pd.to_datetime(reviews["review_answer_timestamp"])
    )
    return (
        reviews.sort_values("review_answer_timestamp")
        .drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
        .reset_index(drop=True)
    )


def build_orders(
    raw: dict[str, pd.DataFrame],
    items: pd.DataFrame,
    sellers: pd.DataFrame,
    centroids: pd.DataFrame,
) -> pd.DataFrame:
    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    orders = raw["orders"].copy()
    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col])

    customers = (
        raw["customers"]
        .merge(
            centroids,
            left_on="customer_zip_code_prefix",
            right_on="zip_prefix",
            how="left",
        )
        .rename(
            columns={
                "customer_zip_code_prefix": "customer_zip_prefix",
                "lat": "customer_lat",
                "lng": "customer_lng",
            }
        )
        .drop(columns="zip_prefix")
    )

    out = (
        orders.merge(customers, on="customer_id", how="left", validate="1:1")
        .merge(order_items_summary(items), on="order_id", how="left", validate="1:1")
        .merge(
            order_payments_summary(raw["payments"]),
            on="order_id",
            how="left",
            validate="1:1",
        )
        .merge(latest_review(raw["reviews"]), on="order_id", how="left", validate="1:1")
        .merge(
            sellers[["seller_id", "seller_state", "seller_lat", "seller_lng"]].rename(
                columns={
                    "seller_id": "main_seller_id",
                    "seller_state": "main_seller_state",
                    "seller_lat": "main_seller_lat",
                    "seller_lng": "main_seller_lng",
                }
            ),
            on="main_seller_id",
            how="left",
        )
    )

    delivered = out["order_delivered_customer_date"]
    out["delivery_days"] = (
        delivered - out["order_purchase_timestamp"]
    ).dt.total_seconds() / 86_400
    out["is_late"] = (
        delivered.dt.normalize() > out["order_estimated_delivery_date"].dt.normalize()
    ).astype("boolean")
    out.loc[delivered.isna(), "is_late"] = pd.NA
    out["purchase_date"] = out["order_purchase_timestamp"].dt.normalize()
    out["distance_km"] = haversine_km(
        out["customer_lat"],
        out["customer_lng"],
        out["main_seller_lat"],
        out["main_seller_lng"],
    )

    return out.drop(columns="customer_id")


def run(raw_dir: Path = RAW_DIR, out_dir: Path = PRIMARY_DIR) -> dict[str, int]:
    raw = read_raw(raw_dir)
    centroids = zip_centroids(raw["geolocation"])
    products = build_products(raw["products"], raw["categories"])
    sellers = build_sellers(raw["sellers"], centroids)
    items = build_items(raw["items"], products, sellers)
    orders = build_orders(raw, items, sellers, centroids)

    out_dir.mkdir(parents=True, exist_ok=True)
    tables = {"orders": orders, "order_items": items, "sellers": sellers}
    for name, table in tables.items():
        table.to_parquet(out_dir / f"{name}.parquet", index=False, compression="zstd")
    return {name: len(table) for name, table in tables.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=PRIMARY_DIR)
    args = parser.parse_args()
    for name, n_rows in run(args.raw_dir, args.out_dir).items():
        print(f"{name}: {n_rows:,} lignes")


if __name__ == "__main__":
    main()
