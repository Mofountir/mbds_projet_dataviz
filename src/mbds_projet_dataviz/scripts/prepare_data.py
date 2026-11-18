from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(name, **kwargs):
    path = RAW / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Download and extract Olist CSVs.")
    return pd.read_csv(path, **kwargs)


def prepare():
    orders = read_csv(
        "olist_orders_dataset.csv",
        parse_dates=[
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    items = read_csv("olist_order_items_dataset.csv")
    products = read_csv("olist_products_dataset.csv")
    reviews = read_csv("olist_order_reviews_dataset.csv")
    translation = read_csv("product_category_name_translation.csv")

    # --- Categories ---
    order_items = items.merge(
        products[["product_id", "product_category_name"]],
        on="product_id", how="left", validate="many_to_one",
    )
    order_items = order_items.merge(
        translation, on="product_category_name", how="left", validate="many_to_one",
    )
    order_items["category"] = (
        order_items["product_category_name_english"]
        .fillna(order_items["product_category_name"])
        .fillna("unknown")
    )

    # --- Revenue per order (avoid duplication) ---
    order_revenue = (
        order_items.groupby("order_id", as_index=False)
        .agg(revenue=("price", "sum"))
    )
    orders = orders.merge(order_revenue, on="order_id", how="left", validate="one_to_one")
    orders["revenue"] = orders["revenue"].fillna(0)

    # --- Review per order ---
    review_per_order = (
        reviews.groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "mean"))
    )
    orders = orders.merge(review_per_order, on="order_id", how="left", validate="one_to_one")

    # --- Late flag ---
    delivered = (
        orders["order_delivered_customer_date"].notna()
        & orders["order_estimated_delivery_date"].notna()
    )
    orders["late"] = np.nan
    orders.loc[delivered, "late"] = (
        orders.loc[delivered, "order_delivered_customer_date"]
        > orders.loc[delivered, "order_estimated_delivery_date"]
    ).astype(float)
    orders["date"] = orders["order_purchase_timestamp"].dt.floor("D")

    # --- Daily metrics ---
    daily = (
        orders.groupby("date")
        .agg(
            orders=("order_id", "nunique"),
            revenue=("revenue", "sum"),
            late_rate=("late", "mean"),
            observed_delivery_orders=("late", "count"),
        )
        .reset_index()
        .sort_values("date")
    )

    # --- Category revenue (top 5 + Other) ---
    order_category = (
        order_items.groupby(["order_id", "category"], as_index=False)
        .agg(category_revenue=("price", "sum"))
    )
    order_category = order_category.merge(
        orders[["order_id", "date"]],
        on="order_id", how="inner", validate="many_to_one",
    )
    top_categories = (
        order_category.groupby("category")["category_revenue"]
        .sum().nlargest(5).index.tolist()
    )
    category_daily = (
        order_category[order_category["category"].isin(top_categories)]
        .groupby(["date", "category"], as_index=False)
        .agg(revenue=("category_revenue", "sum"))
    )

    # "Other" = total revenue - sum(top5)  → le stack somme au total
    top5_daily = (
        category_daily.groupby("date", as_index=False)["revenue"]
        .sum().rename(columns={"revenue": "top5_revenue"})
    )
    other = daily[["date", "revenue"]].merge(top5_daily, on="date", how="left")
    other["top5_revenue"] = other["top5_revenue"].fillna(0)
    other["revenue"] = (other["revenue"] - other["top5_revenue"]).clip(lower=0)
    other = other[["date", "revenue"]]
    other["category"] = "Other"
    category_daily = pd.concat([category_daily, other], ignore_index=True)
    category_daily = category_daily.sort_values(["date", "category"])

    daily.to_csv(OUT / "daily_metrics.csv", index=False)
    category_daily.to_csv(OUT / "daily_category_revenue.csv", index=False)
    print(f"Saved {len(daily):,} daily records.")
    print(f"Date range: {daily['date'].min()} to {daily['date'].max()}")
    print("Top categories:", top_categories)


if __name__ == "__main__":
    prepare()