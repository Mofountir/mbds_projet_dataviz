"""Tableau de bord des catégories : repérer, comparer, choisir où enquêter."""

import pandas as pd
import streamlit as st

from mbds_projet_dataviz.domains.treemap import charts, datasets, transforms
from mbds_projet_dataviz.domains.treemap.labels import (
    category_label,
    money,
    number,
    rate_comparison,
)
from mbds_projet_dataviz.shared.filters import selected_dataset

PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False}


def select_chart_category(chart_key: str, available: list[str]) -> None:
    """Synchronise le détail avant le rendu des widgets, via la clé du point."""
    event = st.session_state.get(chart_key, {})
    points = event.get("selection", {}).get("points", [])
    if points:
        custom = points[-1].get("customdata", [])
        if custom and custom[0] in available:
            st.session_state["treemap_category"] = custom[0]


def rate_metric(label: str, value: float, reference: float, help_text: str) -> None:
    st.metric(label, f"{number(value, 1)} %", help=help_text)
    text, tone = rate_comparison(value, reference)
    st.markdown(
        f'<div class="metric-comparison {tone}" '
        f'title="Écart en points de pourcentage par rapport à la moyenne Olist">{text}</div>',
        unsafe_allow_html=True,
    )


def export_table(summary: pd.DataFrame) -> pd.DataFrame:
    return (
        summary.assign(category=summary["category"].map(category_label))[
            [
                "category",
                "group",
                "revenue",
                "orders",
                "bad_orders",
                "bad_rate",
                "late_rate",
                "review_score",
            ]
        ]
        .rename(
            columns={
                "category": "Catégorie",
                "group": "Famille",
                "revenue": "Ventes (R$)",
                "orders": "Commandes",
                "bad_orders": "Avis négatifs",
                "bad_rate": "Avis négatifs (%)",
                "late_rate": "Retards (%)",
                "review_score": "Note / 5",
            }
        )
        .round(2)
    )


try:
    all_orders = datasets.load_orders()
except FileNotFoundError:
    st.error("Les données des catégories ne sont pas disponibles.")
    with st.expander("Préparer les données"):
        st.code("python -m mbds_projet_dataviz.domains.coordonnees.transforms")
    st.stop()

dataset = selected_dataset()
period = transforms.prepare_orders(transforms.filter_dataset(all_orders, dataset))
if period.empty:
    st.title("Catégories")
    st.info("Aucune commande sur cette période. Choisissez une autre année.")
    st.stop()
baseline = transforms.key_numbers(period)

with st.container(key="treemap_dashboard"):
    st.title("Où agir pour réduire les mauvais avis ?")

    f1, f2, f3 = st.columns([2, 1.3, 1.5])
    group = f1.selectbox(
        "Famille de produits",
        ["Tous les groupes", *sorted(period["group"].unique())],
        format_func=lambda value: (
            "Toutes les familles" if value == "Tous les groupes" else value
        ),
        key="treemap_group",
    )
    minimum = f2.select_slider(
        "Commandes minimum par catégorie",
        [1, 10, 30, 100, 500],
        value=30,
        key="treemap_min_orders",
        help="Écarte les catégories avec peu de commandes. Ce filtre s'applique à tous les chiffres et graphiques.",
    )
    color = f3.selectbox(
        "Couleur : ventes et classement",
        list(charts.COLOR_METRICS),
        key="treemap_color",
    )
    metric = charts.COLOR_METRICS[color]
    orders = transforms.filter_scope(period, group, minimum)
    if orders.empty:
        st.info(
            "Aucune catégorie avec autant de commandes. Diminuez le minimum ou changez de famille."
        )
        st.stop()
    summary = transforms.summarize(orders, ["group", "category"])
    numbers = transforms.key_numbers(orders)
    options = summary["category"].tolist()
    if st.session_state.get("treemap_category") not in options:
        st.session_state["treemap_category"] = summary.sort_values(
            "bad_orders", ascending=False
        ).iloc[0]["category"]

    st.markdown(
        '<div class="dashboard-context">'
        f"{dataset.replace('Olist ', '').replace('— ', '')} · {len(summary)} catégories · "
        f"{number(numbers['orders'])} commandes affichées</div>",
        unsafe_allow_html=True,
    )
    with st.container(key="treemap_kpis"):
        k1, k2, k3, k4 = st.columns(4)
        with k1, st.container(border=True):
            st.metric(
                "Ventes hors livraison",
                money(numbers["revenue"]),
                help="Somme des prix des articles, en réals brésiliens. Les frais de port sont exclus.",
            )
        with k2, st.container(border=True):
            st.metric(
                "Commandes",
                number(numbers["orders"]),
                help="Commandes livrées avec un avis client, après les filtres.",
            )
        with k3, st.container(border=True):
            rate_metric(
                "Avis négatifs · 1 ou 2 étoiles",
                numbers["bad_rate"],
                baseline["bad_rate"],
                f"{number(numbers['bad_orders'])} avis négatifs. Moyenne Olist : {number(baseline['bad_rate'], 1)} % sur toute la période choisie.",
            )
        with k4, st.container(border=True):
            rate_metric(
                "Livraisons en retard",
                numbers["late_rate"],
                baseline["late_rate"],
                f"Livraison après le jour annoncé. Moyenne Olist : {number(baseline['late_rate'], 1)} % sur toute la période choisie.",
            )

    left, right = st.columns([1.4, 1], gap="large")
    with left, st.container(border=True):
        st.subheader(
            "Répartition des ventes",
            help="Chaque rectangle représente une catégorie. Sa surface correspond aux ventes hors livraison. Cliquez pour zoomer.",
        )
        st.plotly_chart(
            charts.overview_treemap(transforms.hierarchy(orders), metric),
            use_container_width=True,
            config=PLOT_CONFIG,
            key=f"treemap_overview_{dataset}_{group}_{minimum}_{metric}",
        )
    with right, st.container(border=True):
        st.subheader(
            "Ventes et mauvais avis",
            help="Un point représente une catégorie. Cliquez sur un point pour afficher son détail. La ligne indique la moyenne Olist de la période, avant les filtres.",
        )
        chart_key = f"treemap_sales_reviews_{dataset}_{group}_{minimum}"
        st.plotly_chart(
            charts.sales_reviews(
                summary, baseline["bad_rate"], st.session_state["treemap_category"]
            ),
            use_container_width=True,
            config=PLOT_CONFIG,
            key=chart_key,
            on_select=lambda: select_chart_category(chart_key, options),
            selection_mode="points",
        )

    ranking_panel, detail_panel = st.columns([1.2, 1], gap="large")
    with ranking_panel, st.container(border=True):
        st.subheader("Les 10 premières catégories")
        ranking = st.selectbox(
            "Classer par", list(charts.RANKINGS), key="treemap_ranking"
        )
        rank_column = charts.RANKINGS[ranking][0]
        ranked = summary.sort_values(
            [rank_column, "category"], ascending=[False, True]
        ).head(10)
        st.plotly_chart(
            charts.category_bars(
                ranked, metric, rank_column, st.session_state["treemap_category"]
            ),
            use_container_width=True,
            config=PLOT_CONFIG,
            key="treemap_ranking_chart",
        )
    with detail_panel, st.container(border=True):
        st.subheader("Examiner une catégorie")
        category = st.selectbox(
            "Catégorie", options, format_func=category_label, key="treemap_category"
        )
        row = summary.set_index("category").loc[category]
        chosen = orders[orders["category"] == category]
        with st.container(key="treemap_detail_metrics"):
            a, b = st.columns(2)
            with a, st.container(border=True):
                st.metric(
                    "Ventes",
                    money(row["revenue"]),
                    help=f"{number(row['revenue_share'], 1)} % des ventes de la sélection.",
                )
            with b, st.container(border=True):
                rate_metric(
                    "Avis négatifs",
                    row["bad_rate"],
                    baseline["bad_rate"],
                    f"Moyenne Olist : {number(baseline['bad_rate'], 1)} % sur la même période, toutes catégories confondues.",
                )
        st.markdown(
            f"**{number(row['bad_orders'])} avis négatifs** sur {number(row['orders'])} commandes"
        )
        st.markdown("**Avis négatifs selon la livraison**")
        st.plotly_chart(
            charts.delivery_bars(transforms.delivery_comparison(chosen)),
            use_container_width=True,
            config=PLOT_CONFIG,
            key="treemap_delivery",
        )
    with st.expander("Chiffres par catégorie et export"):
        table = export_table(summary)
        st.dataframe(table, hide_index=True, use_container_width=True)
        st.download_button(
            "Télécharger le tableau",
            table.to_csv(index=False).encode("utf-8-sig"),
            file_name="olist_categories.csv",
            mime="text/csv",
        )
    with st.expander("À propos des chiffres"):
        st.markdown(
            f"**Source :** [Olist — commandes 2016–2018]({datasets.KAGGLE_SOURCE}). "
            "Seules les commandes livrées avec un avis sont incluses ; le dernier avis est retenu.\n\n"
            "**Comparaison :** la moyenne Olist porte sur toute la période choisie, "
            "avant les filtres de famille et de nombre de commandes.\n\n"
            "**À garder en tête :** une commande entière est rattachée à la catégorie "
            "de son premier article. Les familles sont des regroupements de présentation. "
            "Un mauvais avis sur une livraison en retard ne prouve pas que le retard en est la cause."
        )
