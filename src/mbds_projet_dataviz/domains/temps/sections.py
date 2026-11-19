"""Sections de page du domaine temps, partagées par la page « Quand ? » et le scénario.

Les fonctions reçoivent les commandes déjà filtrées par le jeu de données global.
Les clés de widgets sont passées en paramètre pour éviter les conflits entre pages.
"""

import pandas as pd
import streamlit as st

from mbds_projet_dataviz.domains.livraison.transforms import format_number
from mbds_projet_dataviz.domains.temps import charts, transforms

MONTHS_FR = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def month_name(date: pd.Timestamp) -> str:
    return f"{MONTHS_FR[date.month - 1]} {date.year}"


def rate(value: float) -> str:
    return f"{format_number(value, '{:.1f}')} %"


def overview(orders: pd.DataFrame, dataset: str, frequency_key: str) -> None:
    """Série temporelle focus + contexte : commandes et taux de retard."""
    st.subheader("Vue d'ensemble : commandes et retards au fil du temps")
    frequency = st.segmented_control(
        "Pas de temps",
        options=list(transforms.FREQUENCIES),
        default="Semaine",
        key=frequency_key,
    )
    frequency = frequency or "Semaine"
    series = transforms.time_series(orders, frequency)
    st.plotly_chart(
        charts.timeline(series, frequency, transforms.default_range(orders)),
        width="stretch",
    )
    st.caption(
        f"{dataset} · date d'achat de la commande. Faire glisser les poignées du "
        "bandeau du bas pour zoomer sur une période ; les deux panneaux suivent. "
        f"Taux de retard masqué quand moins de {transforms.MIN_DELIVERED} commandes "
        "livrées sur la période."
    )


def detail(orders: pd.DataFrame) -> None:
    """Black Friday avant / après, puis volume de la semaine contre retard."""
    test = transforms.black_friday_test(orders)
    st.subheader("Détail : Black Friday, puis le volume explique-t-il les retards ?")
    bf_col, volume_col = st.columns([2, 3])
    with bf_col:
        st.markdown("**Black Friday 2017 : avant / après**")
        if test is None or test["before"] is None or test["after"] is None:
            st.info("Black Friday 2017 n'est pas dans ce jeu de données.")
        else:
            peak, second = st.columns(2)
            peak.metric(
                "Commandes le 24/11/2017",
                format_number(test["black_friday_orders"]),
            )
            second.metric(
                "2e jour le plus chargé",
                format_number(test["second_orders"]),
                help=f"Le {test['second_day']:%d/%m/%Y}.",
            )
            st.plotly_chart(
                charts.before_after_chart(test["before"], test["after"]),
                width="stretch",
            )
            st.caption(
                "Taux de retard des commandes achetées en octobre 2017 et dans les "
                f"{transforms.AFTER_DAYS} jours après Black Friday. Barres : IC à "
                "95 % (Wilson)."
            )
    with volume_col:
        st.markdown("**Une semaine par point : commandes et retards**")
        st.plotly_chart(
            charts.volume_vs_late(transforms.weekly_points(orders)), width="stretch"
        )
        st.caption(
            "Si le volume suffisait à expliquer les retards, les points monteraient "
            "régulièrement de gauche à droite. Semaines de moins de "
            f"{transforms.MIN_DELIVERED} commandes livrées masquées."
        )


def answer(orders: pd.DataFrame) -> tuple[str, list[str]] | None:
    """Verdict et paragraphes de réponse ; ``None`` si Black Friday est hors données."""
    test = transforms.black_friday_test(orders)
    if test is None or test["before"] is None or test["after"] is None:
        return None
    before, after = test["before"], test["after"]
    is_peak = test["peak_day"] == transforms.BLACK_FRIDAY
    rises = after["low"] > before["high"]

    if is_peak:
        ratio = test["black_friday_orders"] / test["second_orders"]
        part_one = (
            "**1. Le pic de commandes est bien Black Friday.** Le 24/11/2017 compte "
            f"{format_number(test['black_friday_orders'])} commandes, "
            f"{format_number(ratio, '{:.1f}')} fois plus que le deuxième jour le plus "
            f"chargé ({test['second_day']:%d/%m/%Y})."
        )
    else:
        part_one = (
            f"**1. Le pic de commandes n'est pas Black Friday** mais le "
            f"{test['peak_day']:%d/%m/%Y} ({format_number(test['peak_orders'])} "
            "commandes)."
        )
    if rises:
        part_one += (
            f" **Les retards suivent** : {rate(after['rate'])} de livraisons en retard "
            f"dans les {transforms.AFTER_DAYS} jours suivants, contre "
            f"{rate(before['rate'])} en octobre 2017 (intervalles de confiance "
            "disjoints)."
        )
    else:
        part_one += (
            f" En revanche, le taux de retard des {transforms.AFTER_DAYS} jours "
            f"suivants ({rate(after['rate'])}) n'est pas nettement supérieur à celui "
            f"d'octobre 2017 ({rate(before['rate'])})."
        )

    paragraphs = [part_one]
    contrast = transforms.same_volume_contrast(orders)
    if contrast is not None:
        worst, closest = contrast["worst"], contrast["closest"]
        if worst["period"].month != transforms.BLACK_FRIDAY.month or (
            worst["period"].year != transforms.BLACK_FRIDAY.year
        ):
            paragraphs.append(
                "**2. Mais ce n'est pas la pire période.** Le mois le plus en retard "
                f"est {month_name(worst['period'])} ({rate(worst['late_rate'])}), "
                f"avec {format_number(worst['orders'])} commandes ; "
                f"{month_name(closest['period'])} en a presque autant "
                f"({format_number(closest['orders'])}) pour seulement "
                f"{rate(closest['late_rate'])} de retards. Le volume n'explique donc "
                "qu'une partie des retards : une autre cause (transporteurs, "
                "logistique) joue aussi."
            )

    if is_peak and rises:
        verdict = "Hypothèse confirmée"
    elif is_peak or rises:
        verdict = "Hypothèse confirmée en partie"
    else:
        verdict = "Hypothèse rejetée"
    return verdict, paragraphs
