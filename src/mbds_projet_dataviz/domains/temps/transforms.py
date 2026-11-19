"""Commandes et retards au fil du temps (date d'achat de la commande).

- Volume : toutes les commandes passées sur la période, quel que soit leur statut.
- Retard : part des commandes livrées reçues après la date estimée (même définition
  que la page carte, ``is_late`` du pipeline commun).

Hypothèse testée (reprise de la branche ``2_time_series``, membre 2) : le Black
Friday du 24 novembre 2017 crée le plus grand pic de commandes, et le taux de retard
augmente dans les 4 semaines qui suivent.
"""

import pandas as pd

from mbds_projet_dataviz.domains.livraison.transforms import wilson_interval

BLACK_FRIDAY = pd.Timestamp("2017-11-24")
# Référence « avant » : le mois complet qui précède (octobre 2017).
BASELINE = (pd.Timestamp("2017-10-01"), pd.Timestamp("2017-11-01"))
AFTER_DAYS = 28
# Pas de temps proposés : libellé -> période pandas (semaines du lundi au dimanche).
FREQUENCIES = {"Jour": "D", "Semaine": "W-SUN", "Mois": "M"}
# En dessous, un taux de retard sur une période est trop instable pour être tracé.
MIN_DELIVERED = 30
# Fenêtre affichée par défaut : hors 2016 et fin 2018, presque vides.
DEFAULT_WINDOW = (pd.Timestamp("2017-01-01"), pd.Timestamp("2018-08-31"))
TOP_LATE_WEEKS = 4


def _with_late(orders: pd.DataFrame) -> pd.DataFrame:
    return orders.assign(late=orders["is_late"].astype(float))


def time_series(orders: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """Commandes et taux de retard par période (début de période en ``period``)."""
    table = _with_late(orders)
    period = table["purchase_date"].dt.to_period(FREQUENCIES[frequency]).dt.start_time
    out = (
        table.groupby(period)
        .agg(
            orders=("order_id", "count"),
            delivered=("late", "count"),
            late_rate=("late", "mean"),
        )
        .rename_axis("period")
        .reset_index()
    )
    out["late_rate"] *= 100
    out.loc[out["delivered"] < MIN_DELIVERED, "late_rate"] = float("nan")
    return out


def default_range(orders: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Fenêtre de zoom initiale : la période utile, bornée aux données."""
    first, last = orders["purchase_date"].min(), orders["purchase_date"].max()
    start, end = max(first, DEFAULT_WINDOW[0]), min(last, DEFAULT_WINDOW[1])
    return (start, end) if start < end else (first, last)


def window_late_rate(
    orders: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> dict | None:
    """Taux de retard (IC de Wilson à 95 %) des commandes achetées dans [start, end[."""
    late = _with_late(orders)
    late = late.loc[
        (late["purchase_date"] >= start) & (late["purchase_date"] < end), "late"
    ].dropna()
    if late.empty:
        return None
    rate, low, high = wilson_interval(late.sum(), len(late))
    return {"rate": rate, "low": low, "high": high, "delivered": len(late)}


def black_friday_test(orders: pd.DataFrame) -> dict | None:
    """Les deux parties de l'hypothèse ; ``None`` si Black Friday est hors données."""
    daily = orders.groupby("purchase_date")["order_id"].count().sort_values()
    if BLACK_FRIDAY not in daily.index:
        return None
    after_start = BLACK_FRIDAY + pd.Timedelta(days=1)
    before = window_late_rate(orders, *BASELINE)
    after = window_late_rate(
        orders, after_start, after_start + pd.Timedelta(days=AFTER_DAYS)
    )
    return {
        "peak_day": daily.index[-1],
        "peak_orders": int(daily.iloc[-1]),
        "second_day": daily.index[-2],
        "second_orders": int(daily.iloc[-2]),
        "black_friday_orders": int(daily[BLACK_FRIDAY]),
        "before": before,
        "after": after,
    }


def weekly_points(orders: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par semaine (commandes, taux de retard) et son rôle dans le récit.

    ``highlight`` : « Semaine du pic de commandes », « Semaines les plus en
    retard » (les ``TOP_LATE_WEEKS`` premières) ou vide.
    """
    weeks = time_series(orders, "Semaine").dropna(subset=["late_rate"])
    weeks["highlight"] = ""
    if weeks.empty:
        return weeks
    worst = weeks.nlargest(TOP_LATE_WEEKS, "late_rate").index
    weeks.loc[worst, "highlight"] = "Semaines les plus en retard"
    weeks.loc[weeks["orders"].idxmax(), "highlight"] = "Semaine du pic de commandes"
    return weeks


def same_volume_contrast(orders: pd.DataFrame) -> dict | None:
    """Mois le plus en retard et mois au volume le plus proche, mais moins en retard.

    Sert à montrer que le volume de commandes n'explique pas tout le retard.
    """
    months = time_series(orders, "Mois").dropna(subset=["late_rate"])
    if len(months) < 2:
        return None
    worst = months.loc[months["late_rate"].idxmax()]
    others = months[months["period"] != worst["period"]]
    closest = others.loc[(others["orders"] - worst["orders"]).abs().idxmin()]
    return {"worst": worst, "closest": closest}
