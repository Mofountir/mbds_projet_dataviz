"""Nettoyage, jointures et indicateurs du domaine « coordonnées parallèles ».

Pipeline (étapes 2 et 3) :

1. ``build_orders`` part des CSV bruts et produit une table **une ligne par
   commande livrée et notée** (data/03_primary/coordonnees/orders.parquet).
2. Les fonctions ``category_summary``, ``sample_orders``, ``key_numbers`` et
   ``bad_rate_by_quintile`` agrègent cette table pour les graphiques.

Reconstruire la table préparée depuis la racine du dépôt :

    python -m mbds_projet_dataviz.domains.coordonnees.transforms [dossier_csv]
"""

import sys
from pathlib import Path

import pandas as pd

from mbds_projet_dataviz.domains.coordonnees import datasets
from mbds_projet_dataviz.shared.transforms import filter_dataset as filter_dataset

# Colonnes numériques comparées sur les axes des coordonnées parallèles.
NUMERIC_COLUMNS = [
    "price",
    "freight",
    "weight_kg",
    "delivery_days",
    "delay_days",
    "installments",
    "review_score",
]


def build_orders(folder: Path | None = None) -> pd.DataFrame:
    """Table commande par commande à partir des CSV bruts.

    Choix (pour éviter les doubles comptes) :
    - commandes au statut ``delivered`` avec une date de livraison connue ;
    - prix et frais = **somme** des articles de la commande ;
    - catégorie = catégorie du **premier** article (environ 10 % des commandes ont
      plusieurs articles, le plus souvent du même produit) ;
    - avis : si une commande a plusieurs avis, on garde le **plus récent** ;
    - mensualités = maximum des paiements de la commande ;
    - en retard = jour de livraison **après** le jour estimé par Olist.
    """
    load = lambda name: datasets.load_raw(name, folder)  # noqa: E731

    orders = load("orders")
    for col in [
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        orders[col] = pd.to_datetime(orders[col])
    orders = orders[
        (orders["order_status"] == "delivered")
        & orders["order_delivered_customer_date"].notna()
    ].copy()

    purchased = orders["order_purchase_timestamp"]
    delivered = orders["order_delivered_customer_date"]
    estimated = orders["order_estimated_delivery_date"]
    orders["delivery_days"] = (delivered - purchased).dt.total_seconds() / 86400
    orders["delay_days"] = (delivered.dt.normalize() - estimated.dt.normalize()).dt.days
    orders["late"] = orders["delay_days"] > 0

    items = load("items")
    products = load("products").merge(
        load("translation"), on="product_category_name", how="left"
    )
    products["category"] = (
        products["product_category_name_english"]
        .fillna(products["product_category_name"])
        .fillna("unknown")
    )
    items = items.merge(
        products[["product_id", "category", "product_weight_g"]],
        on="product_id",
        how="left",
    )
    items_per_order = (
        items.sort_values(["order_id", "order_item_id"])
        .groupby("order_id")
        .agg(
            price=("price", "sum"),
            freight=("freight_value", "sum"),
            weight_g=("product_weight_g", "sum"),
            n_items=("order_item_id", "count"),
            category=("category", "first"),
        )
        .reset_index()
    )

    installments = (
        load("payments")
        .groupby("order_id")["payment_installments"]
        .max()
        .rename("installments")
        .reset_index()
    )

    reviews = (
        load("reviews")
        .sort_values("review_answer_timestamp")
        .drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
    )

    customers = load("customers")[["customer_id", "customer_state"]]

    table = (
        orders.merge(items_per_order, on="order_id")
        .merge(installments, on="order_id", how="left")
        .merge(reviews, on="order_id")
        .merge(customers, on="customer_id", how="left")
    )
    table["weight_kg"] = table["weight_g"] / 1000
    table["installments"] = table["installments"].fillna(1).clip(lower=1)
    table = table.rename(columns={"order_purchase_timestamp": "purchase_date"})

    columns = [
        "purchase_date",
        "customer_state",
        "category",
        "n_items",
        *NUMERIC_COLUMNS,
        "late",
    ]
    return table[columns].reset_index(drop=True)


def category_summary(orders: pd.DataFrame, min_orders: int = 30) -> pd.DataFrame:
    """Overview : une ligne par catégorie (moyennes), catégories assez fournies."""
    summary = (
        orders.groupby("category")
        .agg(
            orders=("price", "count"),
            price=("price", "mean"),
            freight=("freight", "mean"),
            weight_kg=("weight_kg", "mean"),
            delivery_days=("delivery_days", "mean"),
            late_rate=("late", "mean"),
            installments=("installments", "mean"),
            review_score=("review_score", "mean"),
            bad_rate=("review_score", lambda s: (s <= 2).mean()),
        )
        .reset_index()
    )
    summary["late_rate"] *= 100
    summary["bad_rate"] *= 100
    return (
        summary[summary["orders"] >= min_orders]
        .sort_values("review_score")
        .reset_index(drop=True)
    )


def sample_orders(
    orders: pd.DataFrame, categories: list[str], n: int = 5000, seed: int = 42
) -> pd.DataFrame:
    """Détail : commandes des catégories choisies (échantillon pour rester fluide)."""
    subset = orders[orders["category"].isin(categories)]
    if len(subset) > n:
        subset = subset.sample(n, random_state=seed)
    return subset


def key_numbers(orders: pd.DataFrame) -> dict:
    """Chiffres clés pour répondre à l'hypothèse."""
    bad = orders["review_score"] <= 2
    late = orders["late"]
    spearman = (
        orders[["delivery_days", "price", "freight", "weight_kg", "review_score"]]
        .corr(method="spearman")["review_score"]
        .drop("review_score")
    )
    return {
        "orders": len(orders),
        "late_rate": late.mean() * 100,
        "bad_rate": bad.mean() * 100,
        "bad_rate_late": bad[late].mean() * 100,
        "bad_rate_on_time": bad[~late].mean() * 100,
        "score_late": orders.loc[late, "review_score"].mean(),
        "score_on_time": orders.loc[~late, "review_score"].mean(),
        "median_days_bad": orders.loc[bad, "delivery_days"].median(),
        "median_days_good": orders.loc[~bad, "delivery_days"].median(),
        "spearman": spearman,
    }


def bad_rate_by_quintile(orders: pd.DataFrame, column: str) -> pd.DataFrame:
    """Part des notes 1-2 dans chaque cinquième (quintile) d'une variable."""
    quintile = pd.qcut(orders[column], 5, labels=False, duplicates="drop")
    grouped = orders.groupby(quintile)
    result = pd.DataFrame(
        {
            "low": grouped[column].min(),
            "high": grouped[column].max(),
            "bad_rate": grouped["review_score"].apply(lambda s: (s <= 2).mean() * 100),
            "orders": grouped.size(),
        }
    ).reset_index(names="quintile")
    result["quintile"] = "Q" + (result["quintile"] + 1).astype(str)
    return result


def selection_mask(
    orders: pd.DataFrame, filters: dict[str, tuple[float, float]]
) -> pd.Series:
    """Brush : vrai pour les commandes dont chaque valeur est dans sa plage."""
    mask = pd.Series(True, index=orders.index)
    for column, (low, high) in filters.items():
        mask &= orders[column].between(low, high)
    return mask


def selection_comparison(orders: pd.DataFrame, selected: pd.Series) -> dict | None:
    """Compare les commandes sélectionnées avec le reste."""
    if selected.all() or not selected.any():
        return None
    inside, outside = orders[selected], orders[~selected]
    return {
        "n": int(selected.sum()),
        "days_in": inside["delivery_days"].median(),
        "days_out": outside["delivery_days"].median(),
        "late_in": inside["late"].mean() * 100,
        "late_out": outside["late"].mean() * 100,
        "bad_in": (inside["review_score"] <= 2).mean() * 100,
        "bad_out": (outside["review_score"] <= 2).mean() * 100,
    }


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    table = build_orders(folder)
    datasets.PRIMARY_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(datasets.PRIMARY_ORDERS, index=False)
    print(f"{len(table)} commandes écrites dans {datasets.PRIMARY_ORDERS}")


if __name__ == "__main__":
    main()
