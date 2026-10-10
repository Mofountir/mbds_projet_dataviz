"""Indicateurs de livraison par région, État et ville du client.

Toutes les agrégations partent des commandes livrées (1 ligne par commande), donc
aucune commande n'est comptée deux fois.
"""

from dataclasses import dataclass

import pandas as pd

# Grandes régions de l'IBGE.
STATE_REGION = {
    "AC": "Norte",
    "AM": "Norte",
    "AP": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}
REGION_ORDER = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]


@dataclass(frozen=True)
class Metric:
    label: str
    unit: str
    fmt: str


METRICS = {
    "median_days": Metric("Délai médian de livraison", "jours", "{:.1f}"),
    "late_rate": Metric("Taux de livraisons en retard", "%", "{:.1f}"),
    "mean_review": Metric("Note moyenne des avis", "/ 5", "{:.2f}"),
    "orders": Metric("Commandes livrées", "commandes", "{:,.0f}"),
    "revenue": Metric("Chiffre d'affaires (hors port)", "R$", "{:,.0f}"),
    "local_seller_rate": Metric(
        "Part des commandes servies par un vendeur du même État", "%", "{:.1f}"
    ),
}


def format_number(value: float, fmt: str = "{:,.0f}") -> str:
    """Nombre au format français : espace fine pour les milliers, virgule décimale."""
    return fmt.format(value).replace(",", "\u202f").replace(".", ",")


def format_value(metric_key: str, value: float) -> str:
    metric = METRICS[metric_key]
    return f"{format_number(value, metric.fmt)} {metric.unit}"


def filter_period(
    orders: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    """Commandes achetées entre le 1er jour de ``start`` et le dernier de ``end``."""
    end_exclusive = end + pd.offsets.MonthBegin(1)
    mask = (orders["purchase_date"] >= start) & (
        orders["purchase_date"] < end_exclusive
    )
    return orders[mask]


def _aggregate(orders: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    out = (
        orders.assign(
            is_late=orders["is_late"].astype(float),
            is_local=(orders["main_seller_state"] == orders["customer_state"]).astype(
                float
            ),
        )
        .groupby(by, observed=True)
        .agg(
            orders=("order_id", "count"),
            revenue=("items_value", "sum"),
            median_days=("delivery_days", "median"),
            late_rate=("is_late", "mean"),
            mean_review=("review_score", "mean"),
            local_seller_rate=("is_local", "mean"),
        )
        .reset_index()
    )
    out["late_rate"] *= 100
    out["local_seller_rate"] *= 100
    return out


def state_metrics(orders: pd.DataFrame) -> pd.DataFrame:
    out = _aggregate(orders, "customer_state").rename(
        columns={"customer_state": "state"}
    )
    out["region"] = out["state"].map(STATE_REGION)
    return out


def region_metrics(orders: pd.DataFrame) -> pd.DataFrame:
    with_region = orders.assign(region=orders["customer_state"].map(STATE_REGION))
    out = _aggregate(with_region, "region")
    out["region"] = pd.Categorical(out["region"], REGION_ORDER, ordered=True)
    return out.sort_values("region").reset_index(drop=True)


def overall_metrics(orders: pd.DataFrame) -> pd.Series:
    return _aggregate(orders.assign(scope="Brésil"), "scope").iloc[0]


def city_metrics(orders: pd.DataFrame, state: str) -> pd.DataFrame:
    in_state = orders[orders["customer_state"] == state]
    out = _aggregate(in_state, "customer_city")
    coords = (
        in_state.groupby("customer_city", observed=True)[
            ["customer_lat", "customer_lng"]
        ]
        .mean()
        .rename(columns={"customer_lat": "lat", "customer_lng": "lng"})
    )
    out = out.join(coords, on="customer_city").rename(columns={"customer_city": "city"})
    return out.sort_values("orders", ascending=False).reset_index(drop=True)


def sellers_in_state(sellers: pd.DataFrame, state: str) -> pd.DataFrame:
    return sellers[
        (sellers["seller_state"] == state) & sellers["seller_lat"].notna()
    ].reset_index(drop=True)


def state_bounds(geojson: dict, state: str) -> tuple[float, float, float, float]:
    """Emprise (lat min, lat max, lng min, lng max) d'un État du GeoJSON."""
    feature = next(f for f in geojson["features"] if f["properties"]["sigla"] == state)

    def points(coords):
        if isinstance(coords[0], (int, float)):
            yield coords
        else:
            for c in coords:
                yield from points(c)

    lngs, lats = zip(*points(feature["geometry"]["coordinates"]))
    return min(lats), max(lats), min(lngs), max(lngs)


def within_bounds(
    table: pd.DataFrame,
    bounds: tuple[float, float, float, float],
    lat: str,
    lng: str,
) -> pd.DataFrame:
    """Écarte les points dont le code postal est géolocalisé hors de l'État."""
    lat_min, lat_max, lng_min, lng_max = bounds
    mask = table[lat].between(lat_min, lat_max) & table[lng].between(lng_min, lng_max)
    return table[mask]


def seller_share_by_state(sellers: pd.DataFrame) -> pd.Series:
    """Part (%) des vendeurs inscrits dans chaque État."""
    return sellers["seller_state"].value_counts(normalize=True).mul(100)
