"""Graphiques du domaine « coordonnées parallèles » (Plotly, sans WebGL).

Les coordonnées parallèles sont dessinées « à la main » avec des lignes SVG
(``go.Scatter``) pour s'afficher dans tous les navigateurs, même sans WebGL.

Mapping visuel (étape « données → variables visuelles » du pipeline) :
- chaque **axe vertical** = un attribut (prix, frais, poids, délai…) et la
  **position** sur l'axe = sa valeur ;
- chaque **ligne** = un item (une catégorie dans l'overview, une commande dans
  le détail) ;
- la **couleur** de la ligne = la note client (rouge = mauvaise, bleu = bonne).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from mbds_projet_dataviz.shared.colors import BLUE, GRAY, RED

# 3 couleurs nettes pour la note : rouge = mauvaise, gris = moyenne, bleu = bonne.
SELECTION = "#eda100"  # bande jaune = plage sélectionnée (brush)
MUTED = "#b4b2a9"
AXIS = "#898781"
HIGHLIGHT = BLUE

# Overview : classe d'une catégorie selon sa note moyenne.
# (moyenne générale 4,16 ; 7 catégories sous 4,0 et 10 au-dessus de 4,3)
OVERVIEW_CLASSES = [
    ("Mal notée (note moyenne < 4,0)", RED, -np.inf, 4.0),
    ("Dans la moyenne (4,0 à 4,3)", GRAY, 4.0, 4.3),
    ("Bien notée (note moyenne ≥ 4,3)", BLUE, 4.3, np.inf),
]

# Détail : classe d'une commande selon sa note.
DETAIL_CLASSES = [
    ("Note 1 ou 2 (mécontent)", RED, [1, 2]),
    ("Note 3 (moyen)", GRAY, [3]),
    ("Note 4 ou 5 (content)", BLUE, [4, 5]),
]

# Axes de l'overview (une ligne par catégorie, valeurs moyennes).
OVERVIEW_AXES = {
    "orders": {"label": "Commandes", "ticks": [30, 100, 300, 1000, 10000], "log": True},
    "price": {
        "label": "Prix moyen (R$)",
        "ticks": [10, 30, 100, 300, 1000],
        "log": True,
    },
    "freight": {"label": "Frais moyens (R$)", "ticks": [0, 20, 40, 60, 80]},
    "weight_kg": {"label": "Poids moyen (kg)", "ticks": [0.1, 1, 10, 30], "log": True},
    "delivery_days": {"label": "Livraison moy. (j)", "ticks": [5, 10, 15, 20, 25]},
    "late_rate": {"label": "En retard (%)", "ticks": [0, 5, 10, 15, 20, 25]},
    "installments": {"label": "Mensualités moy.", "ticks": [1, 2, 3, 4, 5, 6]},
    "review_score": {"label": "Note moyenne", "ticks": [3, 3.5, 4, 4.5, 5]},
}

# Axes du détail (une ligne par commande).
DETAIL_AXES = {
    "price": {
        "label": "Prix (R$)",
        "ticks": [5, 10, 30, 100, 300, 1000, 5000],
        "log": True,
    },
    "freight": {"label": "Frais (R$)", "ticks": [1, 3, 10, 30, 100, 300], "log": True},
    "weight_kg": {
        "label": "Poids (kg)",
        "ticks": [0.05, 0.3, 1, 3, 10, 50],
        "log": True,
    },
    "delivery_days": {
        "label": "Livraison (j)",
        "ticks": [0, 10, 20, 30, 40, 50, 60],
        "ticktext": ["0", "10", "20", "30", "40", "50", "60+"],
    },
    "delay_days": {
        "label": "Retard (j)",
        "ticks": [-40, -20, 0, 20, 40],
        "ticktext": ["-40", "-20", "0", "+20", "+40"],
    },
    "installments": {
        "label": "Mensualités",
        "ticks": [1, 3, 6, 9, 12],
        "ticktext": ["1", "3", "6", "9", "12+"],
    },
    "review_score": {"label": "Note", "ticks": [1, 2, 3, 4, 5]},
}

# Explication de chaque axe (bulle au survol du titre, et encadré de la page).
AXIS_HELP = {
    "orders": "Nombre de commandes de la catégorie.<br>Haut = catégorie très vendue.",
    "price": "Prix payé pour les articles (en reais, R$).<br>Haut = produits chers.",
    "freight": "Frais de port payés par le client (R$).<br>Haut = livraison chère.",
    "weight_kg": "Poids des produits commandés (kg).<br>Haut = produits lourds.",
    "delivery_days": (
        "Nombre de jours entre l'achat et la livraison.<br>Haut = livraison longue."
    ),
    "late_rate": (
        "Part des commandes livrées APRÈS la date promise par Olist.<br>"
        "Haut = beaucoup de retards."
    ),
    "delay_days": (
        "Jours d'écart avec la date promise.<br>"
        "Négatif = en avance, 0 = le jour prévu, positif = en retard."
    ),
    "installments": (
        "Nombre de fois où le client paie (paiement en plusieurs fois).<br>"
        "1 = paiement en une fois."
    ),
    "review_score": (
        "Note donnée par le client, de 1 (très mécontent) à 5 (très content).<br>"
        "C'est ce qu'on cherche à expliquer."
    ),
}

# Version texte pour l'encadré « Que veut dire chaque axe ? ».
AXIS_HELP_TEXT = {
    "Commandes": "nombre de commandes de la catégorie (haut = très vendue).",
    "Prix moyen / Prix": "prix des articles en reais, R$ (haut = cher).",
    "Frais moyens / Frais": "frais de port payés par le client (haut = livraison chère).",
    "Poids moyen / Poids": "poids des produits en kg (haut = lourd).",
    "Livraison moy. / Livraison": "jours entre l'achat et la livraison (haut = long).",
    "En retard (%)": "part des commandes livrées après la date promise par Olist.",
    "Retard (j)": "jours d'écart avec la date promise : négatif = en avance, "
    "positif = en retard.",
    "Mensualités": "en combien de fois le client paie (1 = paiement en une fois).",
    "Note moyenne / Note": "note du client, de 1 (très mécontent) à 5 (très content). "
    "C'est ce qu'on veut expliquer.",
}


def _scale(values, spec: dict) -> np.ndarray:
    """Position verticale (0 = bas de l'axe, 1 = haut) d'une valeur."""
    ticks = spec["ticks"]
    v = np.clip(np.asarray(values, dtype=float), ticks[0], ticks[-1])
    lo, hi = ticks[0], ticks[-1]
    if spec.get("log"):
        v, lo, hi = np.log10(v), np.log10(lo), np.log10(hi)
    return (v - lo) / (hi - lo)


def _polylines(frame: pd.DataFrame, columns: list[str], specs: dict):
    """Coordonnées x / y de toutes les lignes, séparées par des trous (NaN)."""
    n, k = len(frame), len(columns)
    ys = np.full((n, k + 1), np.nan)
    for j, column in enumerate(columns):
        ys[:, j] = _scale(frame[column], specs[column])
    xs = np.tile(np.append(np.arange(k, dtype=float), np.nan), n)
    return xs, ys.ravel()


def _axes_figure(columns: list[str], specs: dict, height: int) -> go.Figure:
    """Fond du graphique : un axe vertical gradué par attribut."""
    fig = go.Figure()
    for j, column in enumerate(columns):
        spec = specs[column]
        fig.add_shape(
            type="line", x0=j, x1=j, y0=0, y1=1, line={"color": AXIS, "width": 1}
        )
        labels = spec.get("ticktext") or [f"{t:g}" for t in spec["ticks"]]
        for tick, label in zip(_scale(spec["ticks"], spec), labels):
            fig.add_annotation(
                x=j,
                y=tick,
                text=label,
                showarrow=False,
                xanchor="right",
                xshift=-4,
                font={"size": 11, "color": AXIS},
            )
        fig.add_annotation(
            x=j,
            y=1.06,
            text=f"<b>{spec['label']}</b>",
            showarrow=False,
            font={"size": 12},
            hovertext=AXIS_HELP.get(column, ""),
        )
    fig.update_xaxes(visible=False, range=[-0.45, len(columns) - 0.55])
    fig.update_yaxes(visible=False, range=[-0.04, 1.12])
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        hovermode="closest",
    )
    return fig


def overview_class(score: float) -> tuple[str, str]:
    """(nom de la classe, couleur) d'une catégorie selon sa note moyenne."""
    for name, color, low, high in OVERVIEW_CLASSES:
        if low <= score < high:
            return name, color
    return OVERVIEW_CLASSES[-1][0], OVERVIEW_CLASSES[-1][1]


def overview_parcoords(
    summary: pd.DataFrame, highlighted: list[str] | None = None
) -> go.Figure:
    """Overview : une ligne par catégorie ; survol = nom et chiffres.

    Couleur = classe de la note moyenne (rouge / gris / bleu), avec une légende.
    """
    columns = list(OVERVIEW_AXES)
    fig = _axes_figure(columns, OVERVIEW_AXES, 500)
    highlighted = set(highlighted or [])
    classes = summary["review_score"].map(overview_class)
    # Ordre de dessin : gris d'abord, puis rouge et bleu, puis les catégories
    # choisies, pour que les lignes importantes restent au premier plan.
    rank = {GRAY: 0, RED: 1, BLUE: 1}
    order = sorted(
        range(len(summary)),
        key=lambda i: (
            summary["category"].iat[i] in highlighted,
            rank[classes.iat[i][1]],
        ),
    )
    in_legend = set()
    for i in order:
        row = summary.iloc[[i]]
        name, color = classes.iat[i]
        xs, ys = _polylines(row, columns, OVERVIEW_AXES)
        chosen = row["category"].iat[0] in highlighted
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": color, "width": 3.2 if chosen else 1.6},
                opacity=0.4 if color == GRAY and not chosen else 0.95,
                name=name,
                legendgroup=name,
                showlegend=name not in in_legend,
                hovertemplate=(
                    f"<b>{row['category'].iat[0]}</b> ({name.split(' (')[0]})<br>"
                    f"{row['orders'].iat[0]} commandes<br>"
                    f"note moyenne {row['review_score'].iat[0]:.2f}<br>"
                    f"livraison moy. {row['delivery_days'].iat[0]:.1f} j<br>"
                    f"en retard {row['late_rate'].iat[0]:.1f} %<extra></extra>"
                ),
            )
        )
        in_legend.add(name)
    _legend_on_top(fig, [c[0] for c in OVERVIEW_CLASSES])
    return fig


def _legend_on_top(fig: go.Figure, names: list[str]) -> None:
    """Légende horizontale au-dessus du graphique, dans l'ordre rouge, gris, bleu."""
    order = {name: i for i, name in enumerate(names)}
    for trace in fig.data:
        trace.legendrank = order.get(trace.name, len(names)) + 1
    fig.update_layout(
        showlegend=True,
        legend={
            "orientation": "h",
            "x": 0.5,
            "xanchor": "center",
            "y": 1.0,
            "yanchor": "bottom",
            "title": {"text": "Couleur : "},
            "itemclick": "toggleothers",
        },
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
    )


def detail_parcoords(
    orders: pd.DataFrame,
    selected: pd.Series,
    filters: dict[str, tuple[float, float]],
    columns: list[str],
) -> go.Figure:
    """Détail : une ligne par commande. Hors sélection = gris clair."""
    fig = _axes_figure(columns, DETAIL_AXES, 520)
    rest = orders[~selected]
    if len(rest):
        xs, ys = _polylines(rest, columns, DETAIL_AXES)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": MUTED, "width": 0.5},
                opacity=0.12,
                name="Hors sélection (très pâle)",
                hoverinfo="skip",
            )
        )
    inside = orders[selected]
    # Gris d'abord, puis bleu, puis rouge au premier plan (les notes 1-2).
    for name, color, scores in [
        DETAIL_CLASSES[1],
        DETAIL_CLASSES[2],
        DETAIL_CLASSES[0],
    ]:
        group = inside[inside["review_score"].isin(scores)]
        if group.empty:
            continue
        xs, ys = _polylines(group, columns, DETAIL_AXES)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": color, "width": 0.8},
                opacity=0.35 if color == GRAY else 0.6,
                name=name,
                hoverinfo="skip",
            )
        )
    _legend_on_top(fig, [c[0] for c in DETAIL_CLASSES] + ["Hors sélection (très pâle)"])
    # Bandes de sélection (brush) sur les axes filtrés.
    for column, (low, high) in filters.items():
        if column not in columns:
            continue
        j = columns.index(column)
        y0, y1 = _scale([low, high], DETAIL_AXES[column])
        fig.add_shape(
            type="rect",
            x0=j - 0.05,
            x1=j + 0.05,
            y0=y0,
            y1=y1,
            fillcolor=SELECTION,
            opacity=0.3,
            line={"color": SELECTION, "width": 1.5},
        )
    return fig


def quintile_small_multiples(
    quintiles: dict[str, tuple[str, pd.DataFrame]],
) -> go.Figure:
    """Petits multiples : % de notes 1-2 par cinquième de chaque variable.

    ``quintiles`` : {titre: (unité, table de bad_rate_by_quintile)}.
    Le premier panneau (délai de livraison) est mis en avant en bleu.
    """
    titles = list(quintiles)
    fig = make_subplots(
        rows=1, cols=len(titles), shared_yaxes=True, subplot_titles=titles
    )
    for i, title in enumerate(titles, start=1):
        unit, table = quintiles[title]
        ranges = [
            f"{lo:.0f} à {hi:.0f} {unit}" for lo, hi in zip(table["low"], table["high"])
        ]
        fig.add_trace(
            go.Bar(
                x=table["quintile"],
                y=table["bad_rate"],
                marker={"color": HIGHLIGHT if i == 1 else MUTED},
                customdata=np.column_stack([ranges, table["orders"]]),
                hovertemplate=(
                    "%{x} : %{customdata[0]}<br>"
                    "%{y:.1f} % d'avis 1-2 étoiles<br>"
                    "%{customdata[1]} commandes<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1,
            col=i,
        )
    fig.update_yaxes(title_text="% d'avis 1-2 étoiles", row=1, col=1, ticksuffix=" %")
    fig.update_yaxes(gridcolor="#e1e0d9", rangemode="tozero")
    fig.update_xaxes(title_text="du plus petit (Q1) au plus grand (Q5)")
    fig.update_layout(
        bargap=0.25, height=360, margin={"l": 70, "r": 20, "t": 50, "b": 30}
    )
    return fig
