"""Page du domaine 1 : carte du Brésil — délais et retards de livraison par région."""

import streamlit as st

from mbds_projet_dataviz.domains.livraison import charts, datasets, transforms
from mbds_projet_dataviz.domains.livraison.transforms import METRICS, format_number
from mbds_projet_dataviz.domains.livraison.transforms import format_value as fmt
from mbds_projet_dataviz.shared.data import missing_data_message
from mbds_projet_dataviz.shared.filters import selected_dataset
from mbds_projet_dataviz.shared.transforms import filter_dataset

STATE_KEY = "livraison_state"
MAP_KEY = "livraison_map"


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
- **Itinéraire** : ville du vendeur principal -> clients d'un État ; la distance
  est à vol d'oiseau entre le code postal du vendeur et celui du client.
- **Retard** : livraison reçue un jour postérieur à la date estimée annoncée au
  client (une livraison le jour estimé est à l'heure).
- **Note moyenne** : moyenne de l'avis le plus récent de chaque commande (1 à 5).
- **Chiffre d'affaires** : somme du prix des articles, frais de port exclus.
- **Vendeur du même État** : le vendeur de l'article le plus cher de la commande
  est inscrit dans l'État du client.
- **Localisation** : l'État et la ville sont ceux du client ; les coordonnées sont
  la moyenne des points de géolocalisation du préfixe de code postal.
"""
    )

dataset = selected_dataset()
metric_key = st.selectbox(
    "Indicateur",
    options=list(METRICS),
    format_func=lambda k: METRICS[k].label,
)

period_orders = filter_dataset(orders, dataset)
if period_orders.empty:
    st.warning("Aucune commande livrée dans ce jeu de données.")
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
    f"{METRICS[metric_key].label} par État du client · {dataset}. Plus la "
    "couleur est foncée, plus la valeur est élevée. "
    "Cliquer sur un État pour afficher ses itinéraires de livraison plus bas."
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
        "filtre de jeu de données)."
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

st.subheader("Détail : d'où viennent les colis livrés dans un État ?")
st.markdown(
    "Chaque arc relie la ville des vendeurs aux clients qu'ils servent dans l'État "
    "choisi. On voit ainsi la distance réellement parcourue et le délai sur chaque "
    "itinéraire, puis, à droite, si les commandes venues de loin arrivent plus tard."
)
state_codes = sorted(states["state"])
if st.session_state.get(STATE_KEY) not in state_codes:
    st.session_state[STATE_KEY] = "SP" if "SP" in state_codes else state_codes[0]
state = st.selectbox(
    "État du client",
    options=state_codes,
    key=STATE_KEY,
    format_func=lambda s: f"{s} · {transforms.STATE_REGION.get(s, '')}",
)
state_row = states.set_index("state").loc[state]
routes, located_orders = transforms.routes_to_state(
    period_orders, sellers, geojson, state
)
profile = transforms.state_distance_profile(period_orders, state)
covered = routes["orders"].sum() / located_orders * 100 if located_orders else 0
st.caption(
    f"{state} : {fmt('orders', state_row['orders'])}, délai médian "
    f"{fmt('median_days', state_row['median_days'])}, "
    f"{fmt('late_rate', state_row['late_rate'])} de retards, "
    f"{fmt('local_seller_rate', state_row['local_seller_rate'])} des commandes "
    "servies par un vendeur du même État."
)
route_col, profile_col = st.columns([3, 2])
with route_col:
    st.markdown(f"**Les {len(routes)} itinéraires les plus fréquents vers {state}**")
    if routes.empty:
        st.info("Aucune commande géolocalisée pour cet État dans ce jeu de données.")
    else:
        st.plotly_chart(
            charts.route_map(
                routes, geojson, state, transforms.state_bounds(geojson, state)
            ),
            width="stretch",
        )
        st.caption(
            "Losange orange : ville des vendeurs (vendeur de l'article le plus cher). "
            "Point : position moyenne des clients servis depuis cette ville. "
            "Épaisseur = nombre de commandes, couleur = délai médian (échelle fixe de "
            f"{charts.ROUTE_DAYS_RANGE[0]:.0f} à {charts.ROUTE_DAYS_RANGE[1]:.0f} "
            f"jours, comparable d'un État à l'autre). Ces itinéraires couvrent "
            f"{format_number(covered, '{:.0f}')} % des commandes géolocalisées de "
            "l'État."
        )
with profile_col:
    st.markdown(f"**Délai selon la distance, clients de {state}**")
    if len(profile) == 1:
        only = profile.iloc[0]
        st.info(
            "Toutes les commandes suffisamment nombreuses viennent de la même "
            f"tranche ({only['distance_band']}, "
            f"{fmt('median_days', only['median_days'])} de délai médian) : aucun "
            "vendeur proche à qui comparer. C'est précisément la situation décrite "
            "par l'hypothèse."
        )
    elif profile.empty:
        st.info(
            "Trop peu de commandes par tranche de distance pour cet État sur la "
            f"jeu de données (minimum {transforms.MIN_ORDERS_PER_CELL} par tranche)."
        )
    else:
        st.plotly_chart(charts.state_distance_chart(profile), width="stretch")
        st.caption(
            "Médiane par tranche de distance à vol d'oiseau, barres : IC à 95 %. "
            "Comparaison dans un seul État : si la courbe monte, la distance "
            "allonge le délai pour des clients d'une même région. Tranches de "
            f"moins de {transforms.MIN_ORDERS_PER_CELL} commandes masquées."
        )

with st.expander("Tableaux : itinéraires et villes des clients"):
    routes_table, cities_table = st.columns(2)
    with routes_table:
        st.markdown("**Itinéraires**")
        st.dataframe(
            routes.assign(
                origin=routes["origin_city"] + " (" + routes["origin_state"] + ")"
            )[["origin", "orders", "distance_km", "median_days", "late_rate"]],
            hide_index=True,
            width="stretch",
            column_config={
                "origin": "Ville du vendeur",
                "orders": "Commandes",
                "distance_km": st.column_config.NumberColumn(
                    "Distance (km)", format="%.0f"
                ),
                "median_days": st.column_config.NumberColumn(
                    "Délai médian (j)", format="%.1f"
                ),
                "late_rate": st.column_config.NumberColumn("Retard (%)", format="%.1f"),
            },
        )
    with cities_table:
        st.markdown("**Villes des clients**")
        cities = transforms.city_metrics(period_orders, state)
        st.dataframe(
            cities.head(15)[["city", "orders", "median_days", "late_rate"]],
            hide_index=True,
            width="stretch",
            column_config={
                "city": "Ville",
                "orders": "Commandes",
                "median_days": st.column_config.NumberColumn(
                    "Délai médian (j)", format="%.1f"
                ),
                "late_rate": st.column_config.NumberColumn("Retard (%)", format="%.1f"),
            },
        )


st.subheader("Robustesse : écart réel, et part due à la distance")
st.markdown(
    "Deux questions distinctes : l'écart entre régions est-il statistiquement "
    "solide, et s'explique-t-il par la distance aux vendeurs ?"
)
intervals = transforms.region_intervals(period_orders)
ci_days, ci_late = st.columns(2)
with ci_days:
    st.markdown("**Délai médian par région, IC à 95 %**")
    st.plotly_chart(
        charts.region_intervals_chart(intervals, "median_days"), width="stretch"
    )
with ci_late:
    st.markdown("**Taux de retard par région, IC à 95 %**")
    st.plotly_chart(
        charts.region_intervals_chart(intervals, "late_rate"), width="stretch"
    )
st.caption(
    "Barres : intervalle de confiance à 95 % (exact pour la médiane, Wilson pour "
    "le taux). Deux régions dont les intervalles ne se chevauchent pas diffèrent "
    "nettement."
)

st.markdown("**À distance égale, le Norte et le Nordeste restent-ils plus lents ?**")
st.plotly_chart(
    charts.delivery_by_distance_chart(transforms.delivery_by_distance(period_orders)),
    width="stretch",
)
st.caption(
    "Distance à vol d'oiseau entre le client et le vendeur de l'article le plus "
    f"cher. Tranches de moins de {transforms.MIN_ORDERS_PER_CELL} commandes "
    "masquées. Si les lignes se superposaient, la distance suffirait à expliquer "
    "l'écart."
)

gaps = transforms.region_gaps(period_orders)
days_gaps = gaps[gaps["indicator"] == "median_days"]
late_gaps = gaps[gaps["indicator"] == "late_rate"]
gap_days_col, gap_late_col = st.columns(2)
with gap_days_col:
    st.markdown("**Écart de délai au Sudeste, brut et à distance égale**")
    st.plotly_chart(charts.region_gaps_chart(days_gaps, "jours"), width="stretch")
with gap_late_col:
    st.markdown("**Écart de taux de retard au Sudeste, brut et à distance égale**")
    st.plotly_chart(charts.region_gaps_chart(late_gaps, "points"), width="stretch")
st.caption(
    "Régression linéaire du délai (ou du retard) sur la région, sans puis avec la "
    "tranche de distance. Écarts en moyenne de jours (ou en points de %), IC à 95 % "
    "de l'écart à distance égale au survol et dans la réponse ci-dessous."
)

with st.expander("Vendeur du même État ou d'un autre État"):
    local = transforms.local_vs_distant(period_orders)
    st.dataframe(
        local,
        hide_index=True,
        width="stretch",
        column_config={
            "region": "Région",
            "seller": "Vendeur principal",
            "orders": "Commandes",
            "median_days": st.column_config.NumberColumn(
                "Délai médian (j)", format="%.1f"
            ),
        },
    )
    st.caption(
        "Les effectifs « même État » sont faibles hors Sudeste et Sul : à lire "
        "comme "
        "un indice, pas comme une mesure précise."
    )

st.subheader("Réponse")
by_region = intervals.set_index("region")
days_by_region = days_gaps.set_index("region")
late_by_region = late_gaps.set_index("region")
local_by_region = local.set_index(["region", "seller"])
compared = ["Norte", "Nordeste"]
if not all(r in by_region.index and r in days_by_region.index for r in compared) or (
    transforms.REFERENCE_REGION not in by_region.index
):
    st.info("Le jeu de données choisi ne contient pas les trois régions à comparer.")
else:
    ref = by_region.loc[transforms.REFERENCE_REGION]
    rows = {r: by_region.loc[r] for r in compared}
    slower = all(
        row["median_days_low"] > ref["median_days_high"] for row in rows.values()
    )
    later = {r: row["late_rate_low"] > ref["late_rate_high"] for r, row in rows.items()}
    shares = {r: days_by_region.loc[r, "share_explained"] for r in compared}

    if slower:
        part_one = (
            "**1. L'écart de délai est réel.** Délai médian de "
            f"{fmt('median_days', rows['Norte']['median_days'])} dans le Norte et "
            f"{fmt('median_days', rows['Nordeste']['median_days'])} dans le "
            f"Nordeste, contre {fmt('median_days', ref['median_days'])} dans le "
            "Sudeste, avec des intervalles de confiance disjoints."
        )
    else:
        part_one = (
            "**1. L'écart de délai n'est pas établi** sur ce jeu de données : les "
            "intervalles de confiance se chevauchent."
        )
    late_text = [
        f"{r} : {fmt('late_rate', rows[r]['late_rate'])} "
        + ("(plus que le Sudeste)" if later[r] else "(pas nettement plus)")
        for r in compared
    ]
    part_one += (
        f" Taux de retard — {' ; '.join(late_text)}, contre "
        f"{fmt('late_rate', ref['late_rate'])} dans le Sudeste."
    )

    def share_level(share: float) -> str:
        if share >= 70:
            return "l'essentiel"
        if share >= 30:
            return "une partie"
        return "une faible part"

    def residual_gap(region: str) -> str:
        gap = days_by_region.loc[region]
        low = format_number(gap["gap_same_distance_low"], "{:.1f}")
        high = format_number(gap["gap_same_distance_high"], "{:.1f}")
        value = format_number(gap["gap_same_distance"], "{:+.1f}")
        return f"{region} : {value} jours (IC {low} à {high})"

    residual = [residual_gap(r) for r in compared]
    part_two = (
        "**2. La distance aux vendeurs en explique "
        f"{share_level(min(shares.values()))}.** Elle explique "
        f"{shares['Norte']:.0f} % de l'écart de délai du Norte et "
        f"{shares['Nordeste']:.0f} % de celui du Nordeste. À distance égale, il "
        f"reste un écart au Sudeste ({' ; '.join(residual)}) : une autre cause "
        "(logistique locale, dernier kilomètre, transporteurs) joue aussi."
    )
    late_persist = [
        r for r in compared if late_by_region.loc[r, "gap_same_distance_low"] > 0
    ]
    late_vanish = [r for r in compared if r not in late_persist]
    if late_vanish:
        part_two += (
            f" L'excès de retards disparaît à distance égale pour "
            f"{' et '.join('le ' + r for r in late_vanish)} : la date estimée tient déjà compte de la "
            "distance."
        )
    if late_persist:
        persist = " et ".join("le " + r for r in late_persist)
        part_two += f" Il persiste pour {persist}, à distance égale."
    key_local = ("Nordeste", "Vendeur du même État")
    key_distant = ("Nordeste", "Vendeur d'un autre État")
    if key_local in local_by_region.index and key_distant in local_by_region.index:
        near, far = local_by_region.loc[key_local], local_by_region.loc[key_distant]
        part_two += (
            " Indice concordant : dans le Nordeste, les commandes servies par un "
            f"vendeur local arrivent en {fmt('median_days', near['median_days'])}, "
            f"contre {fmt('median_days', far['median_days'])} sinon "
            f"({format_number(near['orders'])} commandes locales seulement)."
        )

    if slower and min(shares.values()) >= 70:
        verdict = "Hypothèse confirmée"
    elif slower and min(shares.values()) >= 30:
        verdict = "Hypothèse confirmée en partie"
    elif slower:
        verdict = "Écart confirmé, mais explication par les vendeurs rejetée"
    else:
        verdict = "Hypothèse rejetée"
    st.markdown(f"#### {verdict} ({dataset})")
    st.markdown(part_one)
    st.markdown(part_two)

st.markdown(
    "**Limites.** Données observationnelles : les vendeurs choisissent où "
    "s'installer et les clients chez qui acheter, donc l'analyse montre une "
    "association, pas une preuve de cause. La distance est à vol d'oiseau et ne "
    "connaît ni le transporteur ni l'itinéraire. Le Norte compte peu de commandes "
    "et aucun vendeur local dans les données."
)

st.markdown(
    "➡️ **Et ensuite ?** Les délais dépendent de l'endroit : la page suivante "
    "montre **quand** ils s'allongent, au fil des mois et des pics de commandes."
)
