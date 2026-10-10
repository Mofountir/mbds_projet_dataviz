"""Figures Plotly du domaine livraison.

Couleurs : une seule rampe bleue séquentielle (clair = faible, foncé = élevé) pour
les valeurs ; orange réservé aux vendeurs sur la carte de détail.
"""

import pandas as pd
import plotly.graph_objects as go

from mbds_projet_dataviz.domains.livraison.transforms import (
    DISTANCE_LABELS,
    FOCUS_REGIONS,
    METRICS,
    format_number,
)

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
LIGHT_BLUE = "#9ec5f4"
# Couleurs catégorielles validées (ordre fixe) pour les régions comparées.
REGION_COLORS = dict(zip(FOCUS_REGIONS, ["#2a78d6", "#eb6834", "#1baf7a"]))

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


def region_intervals_chart(intervals: pd.DataFrame, metric_key: str) -> go.Figure:
    """Valeur par région (point) et intervalle de confiance à 95 % (barre)."""
    metric = METRICS[metric_key]
    value = intervals[metric_key]
    low = intervals[f"{metric_key}_low"]
    high = intervals[f"{metric_key}_high"]
    fig = go.Figure(
        go.Scatter(
            x=value,
            y=intervals["region"],
            mode="markers+text",
            marker=dict(size=10, color=SERIES_BLUE),
            error_x=dict(
                type="data",
                array=high - value,
                arrayminus=value - low,
                color=SERIES_BLUE,
                thickness=2,
                width=6,
            ),
            text=[format_number(v, metric.fmt) for v in value],
            textposition="top center",
            customdata=pd.concat([low, high, intervals["orders"]], axis=1).to_numpy(),
            hovertemplate=(
                f"<b>%{{y}}</b><br>{metric.label} : "
                + _hover_value(metric_key, "x")
                + "<br>IC 95 % : %{customdata[0]:.1f} - %{customdata[1]:.1f}"
                + "<br>Commandes : %{customdata[2]:,}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=280,
        margin=dict(l=0, r=10, t=10, b=0),
        xaxis=dict(title=_value_label(metric_key), zeroline=False),
        yaxis=dict(autorange="reversed", title=None),
        separators=FR_SEPARATORS,
    )
    return fig


def delivery_by_distance_chart(cells: pd.DataFrame) -> go.Figure:
    """Délai médian par tranche de distance : une ligne par région comparée."""
    fig = go.Figure()
    for region in FOCUS_REGIONS:
        line = cells[cells["region"] == region]
        if line.empty:
            continue
        color = REGION_COLORS[region]
        fig.add_trace(
            go.Scatter(
                name=region,
                x=line["distance_band"].astype(str),
                y=line["median_days"],
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=8, color=color, line=dict(color="white", width=2)),
                customdata=line[["orders"]],
                hovertemplate=(
                    f"<b>{region}</b> · %{{x}}<br>Délai médian : %{{y:.1f}} jours"
                    "<br>Commandes : %{customdata[0]:,}<extra></extra>"
                ),
            )
        )
        last = line.iloc[-1]
        fig.add_annotation(
            x=str(last["distance_band"]),
            y=last["median_days"],
            text=region,
            showarrow=False,
            xanchor="left",
            xshift=10,
            font=dict(size=12),
        )
    fig.update_layout(
        height=380,
        margin=dict(l=0, r=80, t=10, b=0),
        xaxis=dict(
            title="Distance client - vendeur principal",
            categoryorder="array",
            categoryarray=DISTANCE_LABELS,
        ),
        yaxis=dict(title="Délai médian de livraison (jours)", rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        hovermode="closest",
        separators=FR_SEPARATORS,
    )
    return fig


def region_gaps_chart(gaps: pd.DataFrame, unit: str) -> go.Figure:
    """Écart au Sudeste : brut, puis à distance égale (IC à 95 % au survol)."""
    regions = gaps["region"]
    fig = go.Figure(
        [
            go.Bar(
                name="Écart brut",
                y=regions,
                x=gaps["gap_raw"],
                orientation="h",
                marker=dict(color=LIGHT_BLUE, cornerradius=4),
                text=[format_number(v, "{:+.1f}") for v in gaps["gap_raw"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Écart brut : %{x:+.1f} "
                + unit
                + "<extra></extra>",
            ),
            go.Bar(
                name="Écart à distance égale",
                y=regions,
                x=gaps["gap_same_distance"],
                orientation="h",
                marker=dict(color=SERIES_BLUE, cornerradius=4),
                customdata=gaps[
                    ["gap_same_distance_low", "gap_same_distance_high"]
                ].to_numpy(),
                text=[format_number(v, "{:+.1f}") for v in gaps["gap_same_distance"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Écart à distance égale : %{x:+.1f} "
                + unit
                + "<br>IC 95 % : %{customdata[0]:+.1f} à %{customdata[1]:+.1f}"
                + "<extra></extra>",
            ),
        ]
    )
    fig.update_layout(
        barmode="group",
        bargap=0.3,
        bargroupgap=0.1,
        height=320,
        margin=dict(l=0, r=50, t=10, b=0),
        xaxis=dict(title=f"Écart au Sudeste ({unit})", zeroline=True),
        yaxis=dict(autorange="reversed", title=None),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        separators=FR_SEPARATORS,
    )
    return fig
