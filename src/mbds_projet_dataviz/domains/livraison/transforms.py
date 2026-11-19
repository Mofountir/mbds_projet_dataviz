"""Indicateurs de livraison par région, État et ville du client.

Toutes les agrégations partent des commandes livrées (1 ligne par commande), donc
aucune commande n'est comptée deux fois.
"""

from dataclasses import dataclass

import numpy as np
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
REFERENCE_REGION = "Sudeste"
FOCUS_REGIONS = ["Norte", "Nordeste", "Sudeste"]

# Tranches de distance client - vendeur principal (km).
DISTANCE_BINS = [0, 250, 500, 1000, 1500, 2000, 4000]
DISTANCE_LABELS = [
    "< 250 km",
    "250-500 km",
    "500-1 000 km",
    "1 000-1 500 km",
    "1 500-2 000 km",
    "> 2 000 km",
]
# En dessous, une médiane par tranche est trop instable pour être affichée.
MIN_ORDERS_PER_CELL = 30
# Itinéraires affichés sur la carte de détail : au-delà, les arcs se confondent.
MAX_ROUTES = 15
Z_95 = 1.96


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


def clean_city(names: pd.Series) -> pd.Series:
    """Nom de ville saisi librement -> forme commune (« São Paulo / SP » -> sao paulo)."""
    return (
        names.fillna("")
        .str.split(r"/| - |,", regex=True)
        .str[0]
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def routes_to_state(
    orders: pd.DataFrame,
    sellers: pd.DataFrame,
    geojson: dict,
    state: str,
    max_routes: int = MAX_ROUTES,
) -> tuple[pd.DataFrame, int]:
    """Itinéraires ville du vendeur -> clients de l'État, les plus fréquents d'abord.

    Une ligne par ville d'origine (vendeur principal). La destination est le point
    moyen des clients servis depuis cette ville. Les clients géolocalisés hors de
    l'État sont écartés. Renvoie aussi le nombre total de commandes géolocalisées
    de l'État, pour dire quelle part les itinéraires affichés couvrent.
    """
    in_state = orders[orders["customer_state"] == state].dropna(
        subset=["customer_lat", "main_seller_lat"]
    )
    in_state = within_bounds(
        in_state, state_bounds(geojson, state), "customer_lat", "customer_lng"
    )
    cities = sellers.set_index("seller_id")["seller_city"]
    in_state = in_state.assign(
        origin_city=clean_city(in_state["main_seller_id"].map(cities)),
        is_late=in_state["is_late"].astype(float),
    )
    routes = (
        in_state.groupby(["main_seller_state", "origin_city"], observed=True)
        .agg(
            orders=("order_id", "count"),
            origin_lat=("main_seller_lat", "mean"),
            origin_lng=("main_seller_lng", "mean"),
            dest_lat=("customer_lat", "mean"),
            dest_lng=("customer_lng", "mean"),
            distance_km=("distance_km", "median"),
            median_days=("delivery_days", "median"),
            late_rate=("is_late", "mean"),
        )
        .reset_index()
        .rename(columns={"main_seller_state": "origin_state"})
        .sort_values("orders", ascending=False)
        .head(max_routes)
        .reset_index(drop=True)
    )
    routes["late_rate"] *= 100
    routes["origin_city"] = routes["origin_city"].str.title()
    routes["is_local"] = routes["origin_state"] == state
    return routes, len(in_state)


def state_distance_profile(orders: pd.DataFrame, state: str) -> pd.DataFrame:
    """Délai médian (IC à 95 %) par tranche de distance, clients d'un seul État."""
    banded = with_distance_band(orders[orders["customer_state"] == state])
    rows = []
    for band, group in banded.groupby("distance_band", observed=True):
        if len(group) < MIN_ORDERS_PER_CELL:
            continue
        days, low, high = median_interval(group["delivery_days"].to_numpy(float))
        rows.append(
            {
                "distance_band": band,
                "orders": len(group),
                "median_days": days,
                "median_days_low": low,
                "median_days_high": high,
                "late_rate": 100 * group["is_late"].astype(float).mean(),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "distance_band",
            "orders",
            "median_days",
            "median_days_low",
            "median_days_high",
            "late_rate",
        ],
    )


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


def median_interval(values: np.ndarray) -> tuple[float, float, float]:
    """Médiane et intervalle de confiance à 95 % exact (statistiques d'ordre)."""
    values = np.sort(values[~np.isnan(values)])
    n = len(values)
    half_width = Z_95 * np.sqrt(n) / 2
    low = int(max(np.floor(n / 2 - half_width), 0))
    high = int(min(np.ceil(n / 2 + half_width), n - 1))
    return float(np.median(values)), float(values[low]), float(values[high])


def wilson_interval(successes: float, n: int) -> tuple[float, float, float]:
    """Proportion (%) et intervalle de Wilson à 95 %."""
    p = successes / n
    denom = 1 + Z_95**2 / n
    center = (p + Z_95**2 / (2 * n)) / denom
    half = Z_95 * np.sqrt(p * (1 - p) / n + Z_95**2 / (4 * n**2)) / denom
    return 100 * p, 100 * (center - half), 100 * (center + half)


def region_intervals(orders: pd.DataFrame) -> pd.DataFrame:
    """Délai médian et taux de retard par région, avec IC à 95 %."""
    rows = []
    regions = orders["customer_state"].map(STATE_REGION)
    for region in REGION_ORDER:
        group = orders[regions == region]
        if group.empty:
            continue
        days, days_low, days_high = median_interval(
            group["delivery_days"].to_numpy(float)
        )
        late = group["is_late"].astype(float)
        rate, rate_low, rate_high = wilson_interval(late.sum(), late.count())
        rows.append(
            {
                "region": region,
                "orders": len(group),
                "median_days": days,
                "median_days_low": days_low,
                "median_days_high": days_high,
                "late_rate": rate,
                "late_rate_low": rate_low,
                "late_rate_high": rate_high,
            }
        )
    return pd.DataFrame(rows)


def with_distance_band(orders: pd.DataFrame) -> pd.DataFrame:
    """Commandes géolocalisées, avec région et tranche de distance."""
    located = orders.dropna(subset=["distance_km"])
    return located.assign(
        region=located["customer_state"].map(STATE_REGION),
        distance_band=pd.cut(
            located["distance_km"],
            DISTANCE_BINS,
            labels=DISTANCE_LABELS,
            include_lowest=True,
        ),
    )


def delivery_by_distance(orders: pd.DataFrame) -> pd.DataFrame:
    """Délai médian par région et tranche de distance (cellules >= seuil)."""
    banded = with_distance_band(orders)
    out = (
        banded[banded["region"].isin(FOCUS_REGIONS)]
        .groupby(["region", "distance_band"], observed=True)
        .agg(
            orders=("order_id", "count"),
            median_days=("delivery_days", "median"),
        )
        .reset_index()
    )
    return out[out["orders"] >= MIN_ORDERS_PER_CELL].reset_index(drop=True)


def _ols(design: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Coefficients et erreurs types classiques d'une régression linéaire."""
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ coef
    dof = len(y) - design.shape[1]
    sigma2 = residuals @ residuals / dof
    cov = sigma2 * np.linalg.pinv(design.T @ design)
    return coef, np.sqrt(np.diag(cov))


def region_gaps(orders: pd.DataFrame) -> pd.DataFrame:
    """Écart de chaque région au Sudeste, brut puis à distance égale.

    Régression linéaire de l'indicateur sur des indicatrices de région, sans puis
    avec des indicatrices de tranche de distance. La part expliquée par la
    distance est ``1 - écart à distance égale / écart brut``.
    """
    banded = with_distance_band(orders)
    others = [r for r in REGION_ORDER if r != REFERENCE_REGION]
    others = [r for r in others if (banded["region"] == r).any()]
    region_cols = np.column_stack(
        [(banded["region"] == r).to_numpy(float) for r in others]
    )
    intercept = np.ones((len(banded), 1))
    bands = pd.get_dummies(banded["distance_band"], drop_first=True).to_numpy(float)
    raw_design = np.hstack([intercept, region_cols])
    controlled_design = np.hstack([raw_design, bands])

    rows = []
    for indicator, values in [
        ("median_days", banded["delivery_days"].to_numpy(float)),
        ("late_rate", banded["is_late"].astype(float).to_numpy() * 100),
    ]:
        raw, _ = _ols(raw_design, values)
        controlled, se = _ols(controlled_design, values)
        for i, region in enumerate(others, start=1):
            rows.append(
                {
                    "indicator": indicator,
                    "region": region,
                    "orders": int(region_cols[:, i - 1].sum()),
                    "gap_raw": raw[i],
                    "gap_same_distance": controlled[i],
                    "gap_same_distance_low": controlled[i] - Z_95 * se[i],
                    "gap_same_distance_high": controlled[i] + Z_95 * se[i],
                    "share_explained": 100 * (1 - controlled[i] / raw[i]),
                }
            )
    return pd.DataFrame(rows)


def local_vs_distant(orders: pd.DataFrame) -> pd.DataFrame:
    """Délai médian selon que le vendeur principal est dans l'État du client."""
    with_region = orders.assign(
        region=orders["customer_state"].map(STATE_REGION),
        seller=np.where(
            orders["main_seller_state"] == orders["customer_state"],
            "Vendeur du même État",
            "Vendeur d'un autre État",
        ),
    )
    out = (
        with_region.groupby(["region", "seller"], observed=True)
        .agg(orders=("order_id", "count"), median_days=("delivery_days", "median"))
        .reset_index()
    )
    out["region"] = pd.Categorical(out["region"], REGION_ORDER, ordered=True)
    return out.sort_values(["region", "seller"]).reset_index(drop=True)
