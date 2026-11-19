"""Scénario de présentation : les 4 questions enchaînées sur une seule page.

- Où ? : vue d'ensemble, détail par État et écart au Sudeste (sections partagées
  avec la page carte).
- Quand ? : en attente.
- Quel effet ? et Quelles catégories ? : les pages 3 et 4 complètes, exécutées
  telles quelles dans cette page (toute modification de ces pages s'y retrouve).

Tout suit le filtre global « Jeu de données ».
"""

import runpy
from pathlib import Path

import streamlit as st

from mbds_projet_dataviz.domains.coordonnees import transforms as effect
from mbds_projet_dataviz.domains.livraison import charts as delivery_charts
from mbds_projet_dataviz.domains.livraison import datasets as delivery_data
from mbds_projet_dataviz.domains.livraison import sections as delivery_sections
from mbds_projet_dataviz.domains.livraison import transforms as delivery
from mbds_projet_dataviz.domains.livraison.transforms import format_number
from mbds_projet_dataviz.domains.livraison.transforms import format_value as fmt
from mbds_projet_dataviz.shared.data import missing_data_message
from mbds_projet_dataviz.shared.datasets import load_orders
from mbds_projet_dataviz.shared.filters import selected_dataset
from mbds_projet_dataviz.shared.transforms import filter_dataset

PAGES_DIR = "src/mbds_projet_dataviz/pages"
PAGES_PATH = Path(__file__).parent
# Clés propres au scénario : la page carte garde sa propre sélection d'État.
STATE_KEY = "scenario_state"
MAP_KEY = "scenario_map"


def section(title: str, minutes: str) -> None:
    st.divider()
    st.subheader(title)
    st.caption(f"⏱ {minutes}")


def key_message(text: str) -> None:
    """Le message à dire à l'oral, en une ou deux phrases."""
    st.success(text, icon="💡")


def embed_page(name: str) -> None:
    """Exécute une page détaillée ici, sans la copier."""
    runpy.run_path(str(PAGES_PATH / f"{name}.py"))


dataset = selected_dataset()

delivered = delivery_data.load_delivered_orders()
sellers = delivery_data.load_sellers()
geojson = delivery_data.load_states_geojson()
if delivered is None:
    missing_data_message("orders")
    st.stop()
if sellers is None:
    missing_data_message("sellers")
    st.stop()
if geojson is None:
    st.error("`data/03_primary/brazil_states.geojson` est introuvable.")
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
regions = delivery.region_metrics(delivered)
delivery_sections.overview(
    states, regions, sellers, geojson, "median_days", dataset, MAP_KEY, STATE_KEY
)
delivery_sections.state_detail(
    delivered, states, sellers, geojson, STATE_KEY, with_tables=False
)

intervals = delivery.region_intervals(delivered).set_index("region")
gaps = delivery.region_gaps(delivered)
day_gaps = gaps[gaps["indicator"] == "median_days"]
st.subheader("Écart de délai au Sudeste, brut et à distance égale")
st.plotly_chart(delivery_charts.region_gaps_chart(day_gaps, "jours"), width="stretch")
st.caption(
    "Régression du délai sur la région, sans puis avec la tranche de distance au "
    "vendeur. La barre foncée est l'écart qui reste à distance égale."
)
day_gaps = day_gaps.set_index("region")
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
embed_page("coordonnees")

# 4. Quelles catégories ? ---------------------------------------------------------
section("4. Quelles catégories sont les plus touchées ?", "2 min")
embed_page("treemap")

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
