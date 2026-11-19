"""Scénario de présentation : les 4 questions en une page, à dérouler en 10 minutes.

Version allégée des pages détaillées : un graphique et un message par question.
Les calculs et les graphiques viennent des domaines (mêmes chiffres que les pages
complètes) et suivent le filtre global « Jeu de données ».
"""

import pandas as pd
import streamlit as st

from mbds_projet_dataviz.domains.coordonnees import charts as effect_charts
from mbds_projet_dataviz.domains.coordonnees import transforms as effect
from mbds_projet_dataviz.domains.livraison import charts as delivery_charts
from mbds_projet_dataviz.domains.livraison import datasets as delivery_data
from mbds_projet_dataviz.domains.livraison import transforms as delivery
from mbds_projet_dataviz.domains.livraison.transforms import format_number
from mbds_projet_dataviz.domains.livraison.transforms import format_value as fmt
from mbds_projet_dataviz.domains.treemap import charts as category_charts
from mbds_projet_dataviz.domains.treemap import transforms as categories
from mbds_projet_dataviz.domains.treemap.labels import category_label
from mbds_projet_dataviz.shared.data import missing_data_message
from mbds_projet_dataviz.shared.datasets import load_orders
from mbds_projet_dataviz.shared.filters import selected_dataset
from mbds_projet_dataviz.shared.transforms import filter_dataset

PAGES_DIR = "src/mbds_projet_dataviz/pages"
# Même seuil que la page 4 par défaut : moins de commandes = taux instables.
MIN_CATEGORY_ORDERS = 30
TOP_CATEGORIES = 3
# Écart de taux de retard (points) au-delà duquel la livraison est mise en cause.
LATE_GAP_POINTS = 2


def section(title: str, minutes: str) -> None:
    st.divider()
    st.subheader(title)
    st.caption(f"⏱ {minutes}")


def key_message(text: str) -> None:
    """Le message à dire à l'oral, en une ou deux phrases."""
    st.success(text, icon="💡")


def spread(table: pd.DataFrame) -> float:
    """Écart (points de %) d'avis 1-2 entre le 1er et le dernier cinquième."""
    return table["bad_rate"].iloc[-1] - table["bad_rate"].iloc[0]


dataset = selected_dataset()

delivered = delivery_data.load_delivered_orders()
geojson = delivery_data.load_states_geojson()
if delivered is None:
    missing_data_message("orders")
    st.stop()
try:
    reviewed = load_orders()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

delivered = filter_dataset(delivered, dataset)
reviewed = filter_dataset(reviewed, dataset)
if delivered.empty or reviewed.empty:
    st.warning("Aucune commande dans ce jeu de données.")
    st.stop()

# Introduction -----------------------------------------------------------------
st.title("Olist : pourquoi des clients mécontents ?")
st.markdown(
    "Olist relie de petits vendeurs, surtout installés autour de São Paulo, à des "
    "clients dans tout le Brésil. **Notre fil rouge : le retard de livraison.** "
    "Où se produit-il, quand, quel effet a-t-il sur les avis, et quelles "
    "catégories en souffrent le plus ?"
)
st.caption(f"⏱ 30 s · {dataset}")
national = delivery.overall_metrics(delivered)
numbers = effect.key_numbers(reviewed)
kpi = st.columns(4)
kpi[0].metric("Commandes livrées", format_number(national["orders"]))
kpi[1].metric("Délai médian", fmt("median_days", national["median_days"]))
kpi[2].metric("Livraisons en retard", fmt("late_rate", national["late_rate"]))
kpi[3].metric(
    "Avis à 1 ou 2 étoiles", f"{format_number(numbers['bad_rate'], '{:.1f}')} %"
)

# 1. Où ? -------------------------------------------------------------------------
section("1. Où les livraisons sont-elles lentes ?", "3 min")
states = delivery.state_metrics(delivered)
map_col, distance_col = st.columns([1, 1])
with map_col:
    st.markdown("**Délai médian par État du client**")
    if geojson is None:
        st.error("`data/03_primary/brazil_states.geojson` est introuvable.")
    else:
        st.plotly_chart(
            delivery_charts.state_choropleth(states, geojson, "median_days"),
            width="stretch",
        )
with distance_col:
    st.markdown("**À distance égale du vendeur, l'écart se réduit**")
    st.plotly_chart(
        delivery_charts.delivery_by_distance_chart(
            delivery.delivery_by_distance(delivered)
        ),
        width="stretch",
    )
    st.caption("Délai médian par tranche de distance client - vendeur.")

intervals = delivery.region_intervals(delivered).set_index("region")
gaps = delivery.region_gaps(delivered)
day_gaps = gaps[gaps["indicator"] == "median_days"].set_index("region")
compared = ["Norte", "Nordeste"]
reference = delivery.REFERENCE_REGION
if all(r in intervals.index and r in day_gaps.index for r in compared) and (
    reference in intervals.index
):
    days = {r: fmt("median_days", intervals.loc[r, "median_days"]) for r in compared}
    shares = {r: day_gaps.loc[r, "share_explained"] for r in compared}
    key_message(
        f"Un client du Norte attend **{days['Norte']}**, un client du Nordeste "
        f"**{days['Nordeste']}**, contre "
        f"**{fmt('median_days', intervals.loc[reference, 'median_days'])}** dans "
        "le Sudeste, où sont la plupart des vendeurs. La distance explique environ "
        f"**{shares['Norte']:.0f} %** (Norte) et **{shares['Nordeste']:.0f} %** "
        "(Nordeste) de cet écart : le reste vient d'ailleurs (transporteurs, "
        "dernier kilomètre)."
    )
else:
    st.info("Ce jeu de données ne contient pas les trois régions à comparer.")

# 2. Quand ? ----------------------------------------------------------------------
section("2. Quand les retards apparaissent-ils ?", "2 min")
st.info(
    "**Section en attente.** Série temporelle des commandes et des retards "
    "(pic du Black Friday 2017). Contenu à intégrer depuis la page 2 ou à "
    "construire ici.",
    icon="🚧",
)

# 3. Quel effet ? -----------------------------------------------------------------
section("3. Les retards font-ils baisser les notes ?", "2 min")
late_col, on_time_col, _ = st.columns([1, 1, 2])
late_col.metric(
    "Avis 1-2 si livré en retard",
    f"{format_number(numbers['bad_rate_late'], '{:.0f}')} %",
)
on_time_col.metric(
    "Avis 1-2 si livré à l'heure",
    f"{format_number(numbers['bad_rate_on_time'], '{:.0f}')} %",
)
quintiles = {
    "Délai de livraison": ("j", effect.bad_rate_by_quintile(reviewed, "delivery_days")),
    "Prix": ("R$", effect.bad_rate_by_quintile(reviewed, "price")),
    "Frais de port": ("R$", effect.bad_rate_by_quintile(reviewed, "freight")),
}
st.plotly_chart(effect_charts.quintile_small_multiples(quintiles), width="stretch")
st.caption(
    "Part d'avis à 1 ou 2 étoiles dans chaque cinquième des commandes, du plus "
    "petit (Q1) au plus grand (Q5)."
)
spreads = {name: spread(table) for name, (_, table) in quintiles.items()}
key_message(
    f"Livrée en retard, une commande reçoit un avis 1-2 dans "
    f"**{format_number(numbers['bad_rate_late'], '{:.0f}')} %** des cas, contre "
    f"**{format_number(numbers['bad_rate_on_time'], '{:.0f}')} %** à l'heure. Des "
    "commandes les plus rapides aux plus lentes, la part d'avis négatifs varie de "
    f"**{format_number(spreads['Délai de livraison'], '{:+.0f}')} points**, contre "
    f"{format_number(spreads['Prix'], '{:+.0f}')} pour le prix et "
    f"{format_number(spreads['Frais de port'], '{:+.0f}')} pour les frais de port : "
    "c'est le délai qui pèse, pas le prix."
)

# 4. Quelles catégories ? ---------------------------------------------------------
section("4. Quelles catégories sont les plus touchées ?", "2 min")
prepared = categories.filter_scope(
    categories.prepare_orders(reviewed), "Tous les groupes", MIN_CATEGORY_ORDERS
)
st.markdown(
    "**Ventes par famille et catégorie** · taille = ventes, couleur = part d'avis "
    "négatifs"
)
st.plotly_chart(
    category_charts.overview_treemap(categories.hierarchy(prepared), "bad_rate"),
    width="stretch",
)
baseline = categories.key_numbers(prepared)
summary = categories.summarize(prepared, ["group", "category"])
top = categories.priorities(summary, baseline["bad_rate"]).head(TOP_CATEGORIES)
if not top.empty:
    names = [
        f"**{category_label(row.category)}** "
        f"({format_number(row.bad_orders)} avis négatifs, "
        f"{format_number(row.late_rate, '{:.0f}')} % de retards)"
        for row in top.itertuples()
    ]
    late_gap = (top["late_rate"] * top["orders"]).sum() / top["orders"].sum() - (
        baseline["late_rate"]
    )
    if late_gap > LATE_GAP_POINTS:
        cause = (
            "Elles sont aussi plus souvent livrées en retard que la moyenne : la "
            "livraison est un levier direct."
        )
    else:
        cause = (
            "Leur taux de retard est proche de la moyenne "
            f"({format_number(baseline['late_rate'], '{:.0f}')} %) : la livraison "
            "n'explique pas tout, le produit lui-même est à examiner."
        )
    key_message(
        "Au-dessus de la moyenne Olist "
        f"({format_number(baseline['bad_rate'], '{:.1f}')} % d'avis négatifs), les "
        f"catégories qui en comptent le plus : {', '.join(names)}. {cause}"
    )

# Conclusion ----------------------------------------------------------------------
section("Ce qu'il faut retenir", "30 s")
st.markdown(
    """
1. **Où** : le Norte et le Nordeste attendent environ deux fois plus longtemps
   que le Sudeste ; l'éloignement des vendeurs en explique à peu près la moitié.
2. **Effet** : le retard, bien plus que le prix ou les frais de port, fait chuter
   la note.
3. **Catégories** : quelques catégories concentrent les avis négatifs ; ce sont
   les premières à examiner.

**Recommandation** : rapprocher l'offre des clients du Nord et du Nordeste
(vendeurs ou stocks locaux) pour réduire les retards, et examiner en priorité les
catégories ci-dessus.
"""
)
st.markdown("**Pour aller plus loin, les pages détaillées :**")
links = st.columns(4)
links[0].page_link(f"{PAGES_DIR}/carte.py", label="1. Où ?", icon="🗺️")
links[1].page_link(f"{PAGES_DIR}/temps.py", label="2. Quand ?", icon="📈")
links[2].page_link(f"{PAGES_DIR}/coordonnees.py", label="3. Quel effet ?", icon="⭐")
links[3].page_link(f"{PAGES_DIR}/treemap.py", label="4. Catégories", icon="🧩")
