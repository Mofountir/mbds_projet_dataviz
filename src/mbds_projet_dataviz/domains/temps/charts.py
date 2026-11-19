"""Figures Plotly du domaine temps.

Mêmes couleurs que la page carte : bleu pour les séries, orange réservé à la
semaine du pic de commandes. Deux mesures d'échelles différentes (commandes, taux
de retard) sont tracées dans deux panneaux superposés qui partagent l'axe du temps,
jamais sur un double axe.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from mbds_projet_dataviz.domains.livraison.charts import (
    FR_SEPARATORS,
    SELLER_ORANGE,
    SERIES_BLUE,
)
from mbds_projet_dataviz.domains.livraison.transforms import format_number
from mbds_projet_dataviz.domains.temps.transforms import BLACK_FRIDAY

DARK_BLUE = "#184f95"
MUTED_GRAY = "#b4b2a9"
EVENT_GRAY = "#898781"
HIGHLIGHT_COLORS = {
    "Semaine du pic de commandes": SELLER_ORANGE,
    "Semaines les plus en retard": SERIES_BLUE,
}
# Format de date du survol selon le pas de temps.
HOVER_DATE = {
    "Jour": "%d/%m/%Y",
    "Semaine": "semaine du %d/%m/%Y",
    "Mois": "%m/%Y",
}


def timeline(
    series: pd.DataFrame,
    frequency: str,
    visible: tuple[pd.Timestamp, pd.Timestamp],
) -> go.Figure:
    """Focus + contexte : commandes et taux de retard, curseur de zoom en bas."""
    date = HOVER_DATE[frequency]
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.5, 0.5],
        subplot_titles=("Commandes passées", "Taux de livraisons en retard (%)"),
    )
    fig.update_annotations(font_size=13)
    fig.add_trace(
        go.Scatter(
            x=series["period"],
            y=series["orders"],
            mode="lines",
            line=dict(color=SERIES_BLUE, width=2),
            hovertemplate=f"%{{x|{date}}}<br>%{{y:,}} commandes<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=series["period"],
            y=series["late_rate"],
            mode="lines",
            line=dict(color=SERIES_BLUE, width=2),
            customdata=series[["delivered"]],
            hovertemplate=(
                f"%{{x|{date}}}<br>%{{y:.1f}} % en retard"
                "<br>%{customdata[0]:,} commandes livrées<extra></extra>"
            ),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    if series["period"].min() <= BLACK_FRIDAY <= series["period"].max():
        for row in (1, 2):
            fig.add_vline(
                x=BLACK_FRIDAY,
                line=dict(color=EVENT_GRAY, width=1, dash="dot"),
                row=row,
                col=1,
            )
        fig.add_annotation(
            x=BLACK_FRIDAY,
            y=1,
            xref="x",
            yref="y domain",
            text="Black Friday",
            showarrow=False,
            xanchor="left",
            xshift=4,
            yanchor="top",
            font=dict(size=11, color=EVENT_GRAY),
        )
    fig.update_xaxes(range=list(visible), tickformat="%m/%Y", showgrid=False)
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.08), row=2, col=1)
    fig.update_yaxes(rangemode="tozero", gridcolor="#e1e0d9", zeroline=False)
    fig.update_yaxes(ticksuffix=" %", row=2, col=1)
    fig.update_layout(
        height=560,
        margin=dict(l=0, r=10, t=30, b=0),
        hovermode="x unified",
        separators=FR_SEPARATORS,
    )
    return fig


def volume_vs_late(weeks: pd.DataFrame) -> go.Figure:
    """Une semaine par point : commandes (x) et taux de retard (y)."""
    fig = go.Figure()
    base = weeks[weeks["highlight"] == ""]
    fig.add_trace(
        go.Scatter(
            name="Autres semaines",
            x=base["orders"],
            y=base["late_rate"],
            mode="markers",
            marker=dict(size=8, color=MUTED_GRAY, line=dict(color="white", width=1)),
            customdata=base[["period"]],
            hovertemplate=(
                "Semaine du %{customdata[0]|%d/%m/%Y}<br>%{x:,} commandes"
                "<br>%{y:.1f} % en retard<extra></extra>"
            ),
        )
    )
    for name, color in HIGHLIGHT_COLORS.items():
        points = weeks[weeks["highlight"] == name]
        if points.empty:
            continue
        fig.add_trace(
            go.Scatter(
                name=name,
                x=points["orders"],
                y=points["late_rate"],
                mode="markers+text",
                marker=dict(size=11, color=color, line=dict(color="white", width=2)),
                text=points["period"].dt.strftime("%d/%m/%y"),
                textposition="middle left",
                textfont=dict(size=11),
                customdata=points[["period"]],
                hovertemplate=(
                    f"<b>{name}</b><br>Semaine du %{{customdata[0]|%d/%m/%Y}}"
                    "<br>%{x:,} commandes<br>%{y:.1f} % en retard<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        height=420,
        margin=dict(l=0, r=10, t=10, b=0),
        xaxis=dict(title="Commandes passées dans la semaine", rangemode="tozero"),
        yaxis=dict(
            title="Taux de livraisons en retard",
            ticksuffix=" %",
            rangemode="tozero",
            gridcolor="#e1e0d9",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        separators=FR_SEPARATORS,
    )
    return fig


def before_after_chart(before: dict, after: dict) -> go.Figure:
    """Taux de retard avant / après Black Friday, IC à 95 % en barres d'erreur."""
    rates = [before["rate"], after["rate"]]
    # Valeur dans le libellé : un texte au bout de la barre chevaucherait l'IC.
    labels = [
        f"{name} · {format_number(rate, '{:.1f}')} %"
        for name, rate in zip(
            ["Octobre 2017 (référence)", "28 jours après Black Friday"], rates
        )
    ]
    fig = go.Figure(
        go.Bar(
            x=rates,
            y=labels,
            orientation="h",
            marker=dict(color=[MUTED_GRAY, SERIES_BLUE], cornerradius=4),
            error_x=dict(
                type="data",
                array=[before["high"] - before["rate"], after["high"] - after["rate"]],
                arrayminus=[
                    before["rate"] - before["low"],
                    after["rate"] - after["low"],
                ],
                color=DARK_BLUE,
                thickness=1.5,
                width=5,
            ),
            customdata=[
                [before["low"], before["high"], before["delivered"]],
                [after["low"], after["high"], after["delivered"]],
            ],
            hovertemplate=(
                "<b>%{y}</b><br>%{x:.1f} % en retard"
                "<br>IC 95 % : %{customdata[0]:.1f} - %{customdata[1]:.1f} %"
                "<br>%{customdata[2]:,} commandes livrées<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=200,
        margin=dict(l=0, r=10, t=10, b=0),
        xaxis=dict(title=None, ticksuffix=" %", rangemode="tozero"),
        yaxis=dict(autorange="reversed", title=None),
        bargap=0.4,
        separators=FR_SEPARATORS,
    )
    return fig
