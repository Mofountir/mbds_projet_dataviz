"""Sections de page du domaine livraison, partagées par la page carte et le scénario.

Chaque fonction affiche un bloc complet (titre, graphiques, légendes) à partir des
commandes déjà filtrées par le jeu de données. Les clés de widgets sont passées en
paramètre pour que deux pages puissent afficher le même bloc sans conflit.
"""

from functools import partial

import pandas as pd
import streamlit as st

from mbds_projet_dataviz.domains.livraison import charts, transforms
from mbds_projet_dataviz.domains.livraison.transforms import METRICS, format_number
from mbds_projet_dataviz.domains.livraison.transforms import format_value as fmt


def _select_state(map_key: str, state_key: str) -> None:
    """Clic sur un État de la carte -> État affiché dans le détail."""
    points = st.session_state[map_key].selection.points
    if points and points[0].get("location"):
        st.session_state[state_key] = points[0]["location"]


def overview(
    states: pd.DataFrame,
    regions: pd.DataFrame,
    sellers: pd.DataFrame,
    geojson: dict,
    metric_key: str,
    dataset: str,
    map_key: str,
    state_key: str,
) -> None:
    """Carte des 27 États (cliquable) et barres par région."""
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
            key=map_key,
            on_select=partial(_select_state, map_key, state_key),
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


def state_detail(
    orders: pd.DataFrame,
    states: pd.DataFrame,
    sellers: pd.DataFrame,
    geojson: dict,
    state_key: str,
    with_tables: bool = True,
) -> None:
    """Itinéraires vendeur -> clients d'un État et délai selon la distance."""
    st.subheader("Détail : d'où viennent les colis livrés dans un État ?")
    st.markdown(
        "Chaque arc relie la ville des vendeurs aux clients qu'ils servent dans l'État "
        "choisi. On voit ainsi la distance réellement parcourue et le délai sur chaque "
        "itinéraire, puis, à droite, si les commandes venues de loin arrivent plus tard."
    )
    state_codes = sorted(states["state"])
    if st.session_state.get(state_key) not in state_codes:
        st.session_state[state_key] = "SP" if "SP" in state_codes else state_codes[0]
    state = st.selectbox(
        "État du client",
        options=state_codes,
        key=state_key,
        format_func=lambda s: f"{s} · {transforms.STATE_REGION.get(s, '')}",
    )
    state_row = states.set_index("state").loc[state]
    routes, located_orders = transforms.routes_to_state(orders, sellers, geojson, state)
    profile = transforms.state_distance_profile(orders, state)
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
        st.markdown(
            f"**Les {len(routes)} itinéraires les plus fréquents vers {state}**"
        )
        if routes.empty:
            st.info(
                "Aucune commande géolocalisée pour cet État dans ce jeu de données."
            )
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
                "Trop peu de commandes par tranche de distance pour cet État dans ce "
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

    if not with_tables:
        return
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
                    "late_rate": st.column_config.NumberColumn(
                        "Retard (%)", format="%.1f"
                    ),
                },
            )
        with cities_table:
            st.markdown("**Villes des clients**")
            cities = transforms.city_metrics(orders, state)
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
                    "late_rate": st.column_config.NumberColumn(
                        "Retard (%)", format="%.1f"
                    ),
                },
            )
