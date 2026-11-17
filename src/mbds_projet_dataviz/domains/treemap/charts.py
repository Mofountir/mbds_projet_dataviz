"""Graphiques du tableau de bord : ventes, avis et livraisons."""

import pandas as pd
import plotly.graph_objects as go

from mbds_projet_dataviz.domains.treemap.labels import category_label
from mbds_projet_dataviz.shared.colors import BLUE, RED

PALE = "#edf1f2"
COLOR_METRICS = {
    "Avis négatifs": "bad_rate",
    "Retards": "late_rate",
    "Note moyenne": "review_score",
}
RANKINGS = {
    "Nombre d'avis négatifs": ("bad_orders", "Avis négatifs"),
    "Part d'avis négatifs (%)": ("bad_rate", "Avis négatifs (%)"),
    "Ventes (R$)": ("revenue", "Ventes hors frais de port (R$)"),
}


def _coloraxis(metric: str) -> dict:
    """Bornes fixes ; les valeurs au-dessus du plafond restent visibles au survol."""
    score = metric == "review_score"
    maximum = 5 if score else (30 if metric == "bad_rate" else 20)
    ticks = [1, 2, 3, 4, 5] if score else [0, maximum / 2, maximum]
    return {
        "colorscale": [[0, RED], [0.5, PALE], [1, BLUE]]
        if score
        else [[0, PALE], [0.5, "#e5aa79"], [1, RED]],
        "cmin": 1 if score else 0,
        "cmax": maximum,
        "colorbar": {
            "title": {"text": "Note / 5" if score else "%"},
            "thickness": 10,
            "len": 0.65,
            "outlinewidth": 0,
            "tickvals": ticks,
            "ticktext": [str(t) for t in ticks]
            if score
            else ["0", f"{maximum / 2:g}", f"≥ {maximum}"],
        },
    }


def _layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        font={"family": "sans-serif", "size": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        separators=", ",
        margin={"l": 8, "r": 8, "t": 10, "b": 15},
        hoverlabel={"bgcolor": "#ffffff", "font_color": "#213541"},
    )
    return fig


def overview_treemap(nodes: pd.DataFrame, metric: str) -> go.Figure:
    labels = nodes["label"].copy()
    leaves = nodes["id"].str.startswith("category/")
    labels.loc[leaves] = labels.loc[leaves].map(category_label)
    fig = go.Figure(
        go.Treemap(
            ids=nodes["id"],
            labels=labels,
            parents=nodes["parent"],
            values=nodes["revenue"],
            branchvalues="total",
            marker={
                "colors": nodes[metric],
                "coloraxis": "coloraxis",
                "line": {"width": 2, "color": "white"},
            },
            customdata=nodes[
                ["orders", "review_score", "late_rate", "bad_rate", "revenue_share"]
            ].to_numpy(),
            texttemplate="<b>%{label}</b><br>%{customdata[4]:.1f} % des ventes",
            textfont={"size": 13},
            hovertemplate=(
                "<b>%{label}</b><br>Ventes : %{value:,.0f} R$<br>"
                "%{customdata[0]:,.0f} commandes<br>"
                "Avis négatifs : %{customdata[3]:.1f} %<br>"
                "Livraisons en retard : %{customdata[2]:.1f} %<br>"
                "Note : %{customdata[1]:.2f} / 5<extra></extra>"
            ),
            pathbar={"visible": True, "thickness": 26},
            tiling={"pad": 4},
            root={"color": "#eef2f3"},
        )
    )
    _layout(fig, 510)
    fig.update_layout(
        coloraxis=_coloraxis(metric), margin={"l": 0, "r": 0, "t": 30, "b": 0}
    )
    return fig


def category_bars(
    summary: pd.DataFrame,
    metric: str,
    ranking: str = "bad_orders",
    selected: str | None = None,
) -> go.Figure:
    labels = summary["category"].map(category_label)
    fig = go.Figure(
        go.Bar(
            x=summary[ranking],
            y=labels,
            orientation="h",
            marker={
                "color": summary[metric],
                "coloraxis": "coloraxis",
                "line": {
                    "color": "#183c4b",
                    "width": [2 if c == selected else 0 for c in summary["category"]],
                },
            },
            customdata=summary[
                [
                    "orders",
                    "review_score",
                    "late_rate",
                    "bad_rate",
                    "bad_orders",
                    "revenue",
                ]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>Ventes : %{customdata[5]:,.0f} R$<br>"
                "%{customdata[0]:,.0f} commandes<br>"
                "Avis négatifs : %{customdata[4]:,.0f} (%{customdata[3]:.1f} %)<br>"
                "Livraisons en retard : %{customdata[2]:.1f} %<extra></extra>"
            ),
        )
    )
    _layout(fig, 365)
    axis_title = next(title for column, title in RANKINGS.values() if column == ranking)
    fig.update_layout(
        coloraxis=_coloraxis(metric),
        xaxis_title=axis_title,
        yaxis={"autorange": "reversed", "title": None},
        bargap=0.28,
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#edf0f2",
        rangemode="tozero",
        ticksuffix=" %" if ranking == "bad_rate" else "",
    )
    return fig


def delivery_bars(comparison: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=comparison["bad_rate"],
            y=comparison["late"].map(
                {False: "Livrées à l'heure", True: "Livrées en retard"}
            ),
            orientation="h",
            marker_color=[RED if late else BLUE for late in comparison["late"]],
            text=comparison["bad_rate"],
            texttemplate="%{text:.1f} %",
            textposition="auto",
            customdata=comparison[["bad_orders", "orders"]].to_numpy(),
            hovertemplate="%{y}<br>%{customdata[0]:,.0f} avis négatifs sur %{customdata[1]:,.0f} commandes<extra></extra>",
        )
    )
    _layout(fig, 175)
    fig.update_layout(
        bargap=0.35,
        xaxis={"range": [0, 100], "ticksuffix": " %", "title": None},
        yaxis={"autorange": "reversed"},
    )
    return fig


def sales_reviews(summary: pd.DataFrame, baseline: float, selected: str) -> go.Figure:
    """Une catégorie par point ; le clic transmet sa clé Olist, pas sa position."""
    fig = go.Figure(
        go.Scatter(
            x=summary["revenue"],
            y=summary["bad_rate"],
            mode="markers",
            marker={
                "size": [16 if c == selected else 10 for c in summary["category"]],
                "color": [
                    RED if rate > baseline else BLUE for rate in summary["bad_rate"]
                ],
                "opacity": 0.9,
                "line": {
                    "color": "#19324A",
                    "width": [2 if c == selected else 0 for c in summary["category"]],
                },
            },
            customdata=summary.assign(label=summary["category"].map(category_label))[
                ["category", "label", "orders", "bad_orders", "late_rate"]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>Ventes : %{x:,.0f} R$<br>"
                "Avis négatifs : %{y:.1f} % (%{customdata[3]:,.0f} avis)<br>"
                "%{customdata[2]:,.0f} commandes<br>"
                "Livraisons en retard : %{customdata[4]:.1f} %<extra></extra>"
            ),
            selected={"marker": {"opacity": 1}},
            unselected={"marker": {"opacity": 0.5}},
        )
    )
    fig.add_hline(
        y=baseline,
        line_dash="dot",
        line_color="#647F95",
        annotation_text=f"Moyenne Olist : {baseline:.1f} %".replace(".", ","),
        annotation_position="top right",
        annotation_font_color="#31546B",
    )
    _layout(fig, 510)
    fig.update_layout(clickmode="event+select", dragmode=False, showlegend=False)
    fig.update_xaxes(
        title="Ventes hors livraison (R$)",
        tickformat=",.0f",
        nticks=4,
        rangemode="tozero",
        gridcolor="#E7EEF5",
    )
    fig.update_yaxes(
        title="Commandes avec un avis négatif (%)",
        ticksuffix=" %",
        range=[0, max(float(summary["bad_rate"].max()), baseline, 1) * 1.2],
        gridcolor="#E7EEF5",
    )
    return fig
