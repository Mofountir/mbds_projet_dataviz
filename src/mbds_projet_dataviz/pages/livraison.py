import pandas as pd
import streamlit as st

from mbds_projet_dataviz.domains.livraison import charts, datasets, transforms
from mbds_projet_dataviz.domains.livraison.transforms import METRICS, format_number
from mbds_projet_dataviz.domains.livraison.transforms import format_value as fmt
from mbds_projet_dataviz.shared.data import missing_data_message

STATE_KEY = "livraison_state"
MAP_KEY = "livraison_map"
# Avant 2017 et après août 2018, trop peu de commandes pour comparer les États.
DEFAULT_PERIOD = (pd.Timestamp("2017-01-01"), pd.Timestamp("2018-08-01"))


def select_state_from_map() -> None:
    points = st.session_state[MAP_KEY].selection.points
    if points and points[0].get("location"):
        st.session_state[STATE_KEY] = points[0]["location"]


st.title("Livraison : délais et retards selon la région")
st.markdown(
    "**Question.** Les clients du Nord et du Nordeste attendent-ils plus longtemps "
    "et subissent-ils plus de retards que ceux du Sudeste, parce que la majorité des "
    "vendeurs se trouve dans l'État de São Paulo ?"
)

orders = datasets.load_delivered_orders()
sellers = datasets.load_sellers()
geojson = datasets.load_states_geojson()
if orders is None:
    missing_data_message("orders")
    st.stop()
if sellers is None:
    missing_data_message("sellers")
    st.stop()
if geojson is None:
    st.error("`data/03_primary/brazil_states.geojson` est introuvable.")
    st.stop()

with st.expander("Données et définitions"):
    st.markdown(
        """
- **Source** : commandes Olist au statut *delivered* avec une date de livraison
  (tables `orders`, `customers`, `order_items`, `order_reviews`, `sellers`,
  `geolocation` jointes par le pipeline commun, 1 ligne par commande).
- **Délai de livraison** : jours entre l'achat et la réception par le client ;
  on affiche la médiane, moins sensible aux colis bloqués plusieurs mois.
- **Retard** : livraison reçue un jour postérieur à la date estimée annoncée au
  client (une livraison le jour estimé est à l'heure).
- **Note moyenne** : moyenne de l'avis le plus récent de chaque commande (1 à 5).
- **Chiffre d'affaires** : somme du prix des articles, frais de port exclus.
- **Vendeur du même État** : le vendeur de l'article le plus cher de la commande
  est inscrit dans l'État du client.
- **Localisation** : l'État et la ville sont ceux du client ; les points de la carte
  de détail sont la moyenne des coordonnées des codes postaux de la ville.
"""
    )

months = pd.date_range(
    orders["purchase_date"].min().to_period("M").to_timestamp(),
    orders["purchase_date"].max(),
    freq="MS",
)
filter_period, filter_metric = st.columns([3, 2])
with filter_period:
    start, end = st.select_slider(
        "Période d'achat",
        options=list(months),
        value=DEFAULT_PERIOD,
        format_func=lambda m: m.strftime("%m/%Y"),
    )
with filter_metric:
    metric_key = st.selectbox(
        "Indicateur",
        options=list(METRICS),
        format_func=lambda k: METRICS[k].label,
    )

period_orders = transforms.filter_period(orders, start, end)
if period_orders.empty:
    st.warning("Aucune commande livrée sur cette période.")
    st.stop()

states = transforms.state_metrics(period_orders)
regions = transforms.region_metrics(period_orders)
national = transforms.overall_metrics(period_orders)

kpi = st.columns(4)
kpi[0].metric("Commandes livrées", fmt("orders", national["orders"]))
kpi[1].metric("Délai médian", fmt("median_days", national["median_days"]))
kpi[2].metric("Livraisons en retard", fmt("late_rate", national["late_rate"]))
kpi[3].metric("Note moyenne", fmt("mean_review", national["mean_review"]))

st.subheader("Vue d'ensemble : les 27 États")
st.caption(
    f"{METRICS[metric_key].label} par État du client, du {start:%m/%Y} au "
    f"{end:%m/%Y}. Plus la couleur est foncée, plus la valeur est élevée. "
    "Cliquer sur un État pour afficher le détail par ville plus bas."
)
map_col, region_col = st.columns([3, 2])
with map_col:
    st.plotly_chart(
        charts.state_choropleth(states, geojson, metric_key),
        key=MAP_KEY,
        on_select=select_state_from_map,
        selection_mode="points",
        width="stretch",
    )
with region_col:
    st.markdown(f"**{METRICS[metric_key].label} par région**")
    st.plotly_chart(charts.region_bars(regions, metric_key), width="stretch")
    seller_share = transforms.seller_share_by_state(sellers)
    st.caption(
        f"{seller_share.get('SP', 0):.0f} % des {format_number(len(sellers))} "
        "vendeurs sont inscrits dans l'État de São Paulo (tous vendeurs, sans "
        "filtre de période)."
    )

with st.expander("Tableau par État"):
    table = states.sort_values(metric_key, ascending=False)[
        ["state", "region", *METRICS]
    ]
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "state": "État",
            "region": "Région",
            **{
                k: st.column_config.NumberColumn(
                    f"{m.label} ({m.unit})",
                    format="%.1f" if m.fmt == "{:.1f}" else None,
                )
                for k, m in METRICS.items()
            },
        },
    )

st.subheader("Détail : villes et vendeurs d'un État")
state_codes = sorted(states["state"])
if st.session_state.get(STATE_KEY) not in state_codes:
    st.session_state[STATE_KEY] = "SP" if "SP" in state_codes else state_codes[0]
state = st.selectbox(
    "État",
    options=state_codes,
    key=STATE_KEY,
    format_func=lambda s: f"{s} · {transforms.STATE_REGION.get(s, '')}",
)
cities = transforms.city_metrics(period_orders, state)
state_sellers = transforms.sellers_in_state(sellers, state)
state_row = states.set_index("state").loc[state]
st.caption(
    f"{state} : {fmt('orders', state_row['orders'])}, délai médian "
    f"{fmt('median_days', state_row['median_days'])}, "
    f"{fmt('late_rate', state_row['late_rate'])} de retards, "
    f"{fmt('local_seller_rate', state_row['local_seller_rate'])} des commandes "
    "servies par un vendeur du même État, "
    f"{format_number(len(state_sellers))} vendeurs inscrits. Taille des bulles = commandes, couleur = indicateur choisi."
)
bounds = transforms.state_bounds(geojson, state)
map_cities = transforms.within_bounds(cities, bounds, "lat", "lng")
map_sellers = transforms.within_bounds(
    state_sellers, bounds, "seller_lat", "seller_lng"
)
detail_map, detail_table = st.columns([3, 2])
with detail_map:
    st.plotly_chart(
        charts.state_detail_map(map_cities, map_sellers, geojson, state, metric_key),
        width="stretch",
    )
    hidden_cities = len(cities) - len(map_cities)
    hidden_sellers = len(state_sellers) - len(map_sellers)
    if hidden_cities or hidden_sellers:
        st.caption(
            f"Non affichés sur la carte : {hidden_cities} villes et {hidden_sellers} "
            "vendeurs dont le code postal est géolocalisé hors de l'État ou absent "
            "de la table de géolocalisation."
        )
with detail_table:
    st.markdown("**Villes avec le plus de commandes**")
    st.dataframe(
        cities.head(15)[["city", "orders", "median_days", "late_rate", "mean_review"]],
        hide_index=True,
        width="stretch",
        column_config={
            "city": "Ville",
            "orders": "Commandes",
            "median_days": st.column_config.NumberColumn(
                "Délai médian (j)", format="%.1f"
            ),
            "late_rate": st.column_config.NumberColumn("Retard (%)", format="%.1f"),
            "mean_review": st.column_config.NumberColumn("Note", format="%.2f"),
        },
    )

st.subheader("Réponse")
by_region = regions.set_index(regions["region"].astype(str))
compared = [r for r in ("Norte", "Nordeste", "Sudeste") if r in by_region.index]
if len(compared) < 3:
    st.info("La période choisie ne contient pas les trois régions à comparer.")
else:
    north, northeast, southeast = (by_region.loc[r] for r in compared)
    slower = all(
        r["median_days"] > southeast["median_days"] for r in (north, northeast)
    )
    later = all(r["late_rate"] > southeast["late_rate"] for r in (north, northeast))
    if slower and later:
        verdict = "**Hypothèse confirmée** sur cette période"
    elif slower or later:
        verdict = "**Hypothèse partiellement confirmée** sur cette période"
    else:
        verdict = "**Hypothèse rejetée** sur cette période"
    st.markdown(
        f"{verdict} : délai médian de {fmt('median_days', north['median_days'])} "
        f"dans le Norte et {fmt('median_days', northeast['median_days'])} dans le "
        f"Nordeste, contre {fmt('median_days', southeast['median_days'])} dans le "
        f"Sudeste ; taux de retard de {fmt('late_rate', north['late_rate'])}, "
        f"{fmt('late_rate', northeast['late_rate'])} et "
        f"{fmt('late_rate', southeast['late_rate'])}. Seules "
        f"{fmt('local_seller_rate', north['local_seller_rate'])} des commandes du "
        f"Norte et {fmt('local_seller_rate', northeast['local_seller_rate'])} de "
        "celles du Nordeste sont servies par un vendeur du même État, contre "
        f"{fmt('local_seller_rate', southeast['local_seller_rate'])} dans le Sudeste."
    )

st.markdown(
    "**Limites.** Les États du Norte comptent peu de commandes : leurs valeurs "
    "varient fortement d'un mois à l'autre. La date estimée est fixée par Olist et peut "
    "déjà intégrer la distance : un délai long n'implique donc pas forcément un "
    "retard. Le lien avec la localisation des vendeurs est une corrélation, pas "
    "une preuve de cause."
)
