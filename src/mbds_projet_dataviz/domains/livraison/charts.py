"""Figures Plotly du domaine livraison.

Couleurs : une seule rampe bleue séquentielle (clair = faible, foncé = élevé) pour
les valeurs ; orange réservé aux vendeurs sur la carte de détail.
"""

import pandas as pd
import plotly.graph_objects as go

from mbds_projet_dataviz.domains.livraison.transforms import METRICS, format_number

BLUE_RAMP = [
    "#cde2fb",
    "#9ec5f4",
    "#6da7ec",
    "#3987e5",
    "#256abf",
    "#184f95",
    "#0d366b",
]
BLUE_SCALE = [[i / (len(BLUE_RAMP) - 1), c] for i, c in enumerate(BLUE_RAMP)]
SERIES_BLUE = "#2a78d6"
SELLER_ORANGE = "#eb6834"
OUTLINE_GRAY = "#c3c2b7"

STATE_KEY = "properties.sigla"
# Plotly : 1er caractère = séparateur décimal, 2e = séparateur de milliers.
FR_SEPARATORS = ", "


def _value_label(metric_key: str) -> str:
    metric = METRICS[metric_key]
    return f"{metric.label} ({metric.unit})"


def _hover_value(metric_key: str, column: str) -> str:
    """Format d3 pour le hovertemplate, aligné sur le format du tableau."""
    fmt = METRICS[metric_key].fmt
    d3 = ",.0f" if "," in fmt else fmt.strip("{}:")
    return f"%{{{column}:{d3}}} {METRICS[metric_key].unit}"


def state_choropleth(states: pd.DataFrame, geojson: dict, metric_key: str) -> go.Figure:
    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            featureidkey=STATE_KEY,
            locations=states["state"],
            z=states[metric_key],
            customdata=states[["region", "orders"]],
            colorscale=BLUE_SCALE,
            marker_line_color="white",
            marker_line_width=0.8,
            colorbar=dict(title=dict(text=METRICS[metric_key].unit), thickness=12),
            hovertemplate=(
                "<b>%{location}</b> · %{customdata[0]}<br>"
                f"{METRICS[metric_key].label} : "
                + _hover_value(metric_key, "z")
                + "<br>Commandes livrées : %{customdata[1]:,}<extra></extra>"
            ),
        )
    )
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=10, b=0),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        clickmode="event+select",
        separators=FR_SEPARATORS,
    )
    return fig


def region_bars(regions: pd.DataFrame, metric_key: str) -> go.Figure:
    metric = METRICS[metric_key]
    labels = [format_number(v, metric.fmt) for v in regions[metric_key]]
    fig = go.Figure(
        go.Bar(
            x=regions[metric_key],
            y=regions["region"].astype(str),
            orientation="h",
            marker=dict(color=SERIES_BLUE, cornerradius=4),
            text=labels,
            textposition="outside",
            cliponaxis=False,
            customdata=regions[["orders"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{metric.label} : " + _hover_value(metric_key, "x") + "<br>"
                "Commandes livrées : %{customdata[0]:,}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=40, t=10, b=0),
        xaxis=dict(title=_value_label(metric_key), showgrid=True, zeroline=False),
        yaxis=dict(autorange="reversed", title=None),
        bargap=0.35,
        separators=FR_SEPARATORS,
    )
    return fig


def state_detail_map(
    cities: pd.DataFrame,
    sellers: pd.DataFrame,
    geojson: dict,
    state: str,
    metric_key: str,
) -> go.Figure:
    feature = [f for f in geojson["features"] if f["properties"]["sigla"] == state]
    outline = {"type": "FeatureCollection", "features": feature}
    cities = cities.dropna(subset=["lat", "lng"])
    max_orders = max(cities["orders"].max(), 1)

    fig = go.Figure()
    fig.add_trace(
        go.Choropleth(
            geojson=outline,
            featureidkey=STATE_KEY,
            locations=[state],
            z=[0],
            colorscale=[[0, "rgba(195,194,183,0.15)"], [1, "rgba(195,194,183,0.15)"]],
            showscale=False,
            marker_line_color=OUTLINE_GRAY,
            marker_line_width=1,
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scattergeo(
            name="Villes des clients (taille = commandes)",
            lat=cities["lat"],
            lon=cities["lng"],
            text=cities["city"],
            # Tableau numpy : metric_key peut valoir "orders" (colonne en double).
            customdata=cities[["orders", metric_key]].to_numpy(),
            mode="markers",
            marker=dict(
                size=cities["orders"],
                sizemode="area",
                sizeref=2.0 * max_orders / (40.0**2),
                sizemin=3,
                color=cities[metric_key],
                colorscale=BLUE_SCALE,
                colorbar=dict(title=dict(text=METRICS[metric_key].unit), thickness=12),
                line=dict(color="white", width=1),
                opacity=0.9,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>Commandes livrées : %{customdata[0]:,}<br>"
                f"{METRICS[metric_key].label} : "
                + _hover_value(metric_key, "customdata[1]")
                + "<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scattergeo(
            name="Vendeurs",
            lat=sellers["seller_lat"],
            lon=sellers["seller_lng"],
            text=sellers["seller_city"],
            mode="markers",
            marker=dict(
                size=8,
                color=SELLER_ORANGE,
                symbol="diamond",
                line=dict(color="white", width=1),
            ),
            hovertemplate="<b>Vendeur</b> · %{text}<extra></extra>",
        )
    )
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=10, b=0),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        separators=FR_SEPARATORS,
    )
    return fig
