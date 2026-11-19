"""Page du domaine 3 : coordonnées parallèles — retards de livraison et avis."""

import streamlit as st

from mbds_projet_dataviz.domains.coordonnees import charts, datasets, transforms
from mbds_projet_dataviz.shared.filters import selected_dataset

# Sélections de départ prêtes pour la démo : {nom: {colonne: (min, max)}}.
PRESETS = {
    "aucune": {},
    "notes 1-2": {"review_score": (1, 2)},
    "prix élevés (≥ 175 R$)": {"price": (175, 5000)},
    "frais élevés (≥ 27 R$)": {"freight": (27, 300)},
    "livraison longue (≥ 20 j)": {"delivery_days": (20, 60)},
}
PRICE_STEPS = [0, 10, 30, 50, 100, 175, 300, 1000, 5000]
FREIGHT_STEPS = [0, 5, 10, 15, 20, 27, 50, 100, 300]


st.title("Qu'est-ce qui provoque les mauvais avis ?")

try:
    all_orders = datasets.load_orders()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

dataset = selected_dataset()
orders = transforms.filter_dataset(all_orders, dataset)
numbers = transforms.key_numbers(orders)

# 1. Question ----------------------------------------------------------------
st.markdown(
    "**Hypothèse :** c'est le **retard de livraison**, et non le prix ou les frais "
    "de port, qui explique les avis à **1 ou 2 étoiles**."
)
st.caption(
    f"{dataset} · {numbers['orders']:,} commandes livrées et notées · "
    f"source : [Kaggle — Olist]({datasets.KAGGLE_SOURCE})".replace(",", " ")
)

summary = transforms.category_summary(orders)
by_size = summary.sort_values("orders", ascending=False)["category"].tolist()

# Choix des catégories (sert au surlignage de l'overview et au détail).
n_all = orders["category"].nunique()
categories = st.multiselect(
    f"Catégories à étudier ({len(summary)} disponibles) : surlignées dans la vue "
    "d'ensemble et utilisées pour le détail",
    by_size,
    default=by_size[:4],
)


# 2. Overview ----------------------------------------------------------------
def reading_box(colors: list[tuple[str, str]], line: str, hint: str) -> None:
    """Encadré visible « Comment lire ce graphique » avec la légende des couleurs."""
    with st.container(border=True):
        st.markdown("**Comment lire ce graphique**")
        st.markdown(
            f"- **1 ligne = {line}.** Elle passe par sa valeur sur chaque axe : "
            "**en haut** = grande valeur, **en bas** = petite valeur.\n"
            "- **Couleur de la ligne** = la note :"
        )
        cols = st.columns(len(colors))
        for col, (color, text) in zip(cols, colors):
            col.markdown(
                f"<span style='display:inline-block;width:28px;height:6px;"
                f"background:{color};border-radius:3px;vertical-align:middle'></span>"
                f"&nbsp; {text}",
                unsafe_allow_html=True,
            )
        st.caption(hint)


st.subheader("1. Vue d'ensemble : une ligne par catégorie de produits")
st.markdown(
    "Chaque ligne relie les **valeurs moyennes** d'une catégorie (toutes ses "
    "commandes). **À regarder :** les lignes **rouges** passent-elles plus haut sur "
    "l'axe *Livraison* ou sur l'axe *Prix* ?"
)
reading_box(
    [(color, name) for name, color, _, _ in charts.OVERVIEW_CLASSES],
    "1 catégorie de produits",
    "Passe la souris sur une ligne pour voir la catégorie et ses chiffres, et sur "
    "le titre d'un axe pour lire sa définition. Clique sur une couleur de la "
    "légende du graphique pour n'afficher qu'elle.",
)
only_chosen = st.toggle(
    "Afficher seulement les catégories choisies", value=False, key="only_chosen"
)
shown = summary[summary["category"].isin(categories)] if only_chosen else summary
st.caption(
    f"**{len(shown)} lignes affichées** = {len(shown)} catégories. Sur les {n_all} "
    f"catégories du jeu de données, {len(summary)} ont au moins 30 commandes "
    "(les autres sont trop petites pour une moyenne fiable)."
)
if shown.empty:
    st.info("Choisis au moins une catégorie, ou désactive l'option.")
else:
    st.plotly_chart(
        charts.overview_parcoords(shown, categories),
        use_container_width=True,
    )


def axis_help() -> None:
    """Encadré dépliable : la définition de chaque axe."""
    with st.expander(" Définition de chaque axe"):
        st.markdown(
            "\n".join(
                f"- **{name}** : {text}" for name, text in charts.AXIS_HELP_TEXT.items()
            )
        )


axis_help()
with st.expander(f"Tableau des {len(summary)} catégories (au moins 30 commandes)"):
    st.dataframe(
        summary.rename(
            columns={
                "category": "Catégorie",
                "orders": "Commandes",
                "price": "Prix moyen (R$)",
                "freight": "Frais moyens (R$)",
                "weight_kg": "Poids moyen (kg)",
                "delivery_days": "Livraison moy. (j)",
                "late_rate": "En retard (%)",
                "installments": "Mensualités moy.",
                "review_score": "Note moyenne",
                "bad_rate": "Avis 1-2 (%)",
            }
        ).round(1),
        hide_index=True,
        use_container_width=True,
    )

# 3. Exploration (détail) ----------------------------------------------------
st.subheader("2. Détail : les commandes une par une")
st.markdown(
    "Une ligne = **une commande** des catégories choisies. Utilise les **curseurs** "
    "pour sélectionner une plage sur un axe (*brushing*) : les commandes "
    "sélectionnées restent en couleur, les autres deviennent **très pâles**, et une "
    "**bande jaune** montre la plage choisie sur l'axe."
)
reading_box(
    [(color, name) for name, color, _ in charts.DETAIL_CLASSES]
    + [(charts.SELECTION, "Bande jaune = plage sélectionnée")],
    "1 commande",
    "Passe la souris sur le titre d'un axe pour lire sa définition. Clique sur une "
    "couleur de la légende du graphique pour n'afficher qu'elle.",
)
if not categories:
    st.info("Choisis au moins une catégorie en haut de la page.")
    st.stop()

preset = st.radio("Sélection de départ", list(PRESETS), horizontal=True, key="preset")
start = PRESETS[preset]

c1, c2, c3, c4 = st.columns(4)
review = c1.slider(
    "Note", 1, 5, start.get("review_score", (1, 5)), key=f"review_{preset}"
)
days = c2.slider(
    "Livraison (jours)",
    0,
    60,
    start.get("delivery_days", (0, 60)),
    key=f"days_{preset}",
)
price = c3.select_slider(
    "Prix (R$)", PRICE_STEPS, start.get("price", (0, 5000)), key=f"price_{preset}"
)
freight = c4.select_slider(
    "Frais de port (R$)",
    FREIGHT_STEPS,
    start.get("freight", (0, 300)),
    key=f"freight_{preset}",
)
filters = {}
if review != (1, 5):
    filters["review_score"] = review
if days != (0, 60):
    filters["delivery_days"] = (days[0], 10_000 if days[1] == 60 else days[1])
if price != (0, 5000):
    filters["price"] = (price[0], 1e9 if price[1] == 5000 else price[1])
if freight != (0, 300):
    filters["freight"] = (freight[0], 1e9 if freight[1] == 300 else freight[1])

axis_order = st.multiselect(
    "Ordre des axes (enlève et remets un axe pour le déplacer)",
    list(charts.DETAIL_AXES),
    default=list(charts.DETAIL_AXES),
    format_func=lambda c: charts.DETAIL_AXES[c]["label"],
)
if len(axis_order) < 2:
    st.info("Garde au moins deux axes.")
    st.stop()

detail = transforms.sample_orders(orders, categories, n=2000)
detail_selected = transforms.selection_mask(detail, filters)
st.plotly_chart(
    charts.detail_parcoords(detail, detail_selected, filters, axis_order),
    use_container_width=True,
)
st.caption(
    f"{len(detail):,} commandes affichées (échantillon de 2 000 maximum). "
    "Prix, frais et poids en échelle logarithmique ; retard = jours après la date "
    "promise (négatif = en avance).".replace(",", " ")
)
axis_help()

# Chiffres de la sélection, calculés sur TOUTES les commandes des catégories.
in_categories = orders[orders["category"].isin(categories)]
comparison = transforms.selection_comparison(
    in_categories, transforms.selection_mask(in_categories, filters)
)
if comparison:
    st.markdown(
        f"**Sélection : {comparison['n']:,} commandes**, comparées au reste "
        "des catégories choisies :".replace(",", " ")
    )
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Livraison médiane",
        f"{comparison['days_in']:.1f} j",
        f"{comparison['days_in'] - comparison['days_out']:+.1f} j vs reste",
        delta_color="inverse",
    )
    m2.metric(
        "Commandes en retard",
        f"{comparison['late_in']:.1f} %",
        f"{comparison['late_in'] - comparison['late_out']:+.1f} pts vs reste",
        delta_color="inverse",
    )
    if "review_score" not in filters:  # sinon la valeur est évidente
        m3.metric(
            "Avis 1-2 étoiles",
            f"{comparison['bad_in']:.1f} %",
            f"{comparison['bad_in'] - comparison['bad_out']:+.1f} pts vs reste",
            delta_color="inverse",
        )

# 4. Réponse -----------------------------------------------------------------
st.subheader("3. Réponse")
r1, r2, r3 = st.columns(3)
r1.metric("Avis 1-2 si livré en retard", f"{numbers['bad_rate_late']:.0f} %")
r2.metric("Avis 1-2 si livré à l'heure", f"{numbers['bad_rate_on_time']:.0f} %")
r3.metric("Commandes en retard", f"{numbers['late_rate']:.1f} %")

st.plotly_chart(
    charts.quintile_small_multiples(
        {
            "Délai de livraison": (
                "j",
                transforms.bad_rate_by_quintile(orders, "delivery_days"),
            ),
            "Prix": ("R$", transforms.bad_rate_by_quintile(orders, "price")),
            "Frais de port": ("R$", transforms.bad_rate_by_quintile(orders, "freight")),
        }
    ),
    use_container_width=True,
)

rho = numbers["spearman"]
st.markdown(
    f"""
**Hypothèse confirmée.** Une commande livrée **en retard** reçoit un avis à 1-2
étoiles dans **{numbers["bad_rate_late"]:.0f} %** des cas, contre
**{numbers["bad_rate_on_time"]:.0f} %** à l'heure (note moyenne
{numbers["score_late"]:.1f} contre {numbers["score_on_time"]:.1f}). Les avis 1-2
étoiles ont une livraison médiane de **{numbers["median_days_bad"]:.0f} jours**,
contre {numbers["median_days_good"]:.0f} pour les autres.

Le lien de la note avec le **délai** (corrélation de Spearman
{rho["delivery_days"]:.2f}) est bien plus fort qu'avec le **prix**
({rho["price"]:.2f}) ou les **frais de port** ({rho["freight"]:.2f}).
"""
)
st.info(
    "**Limites.** Corrélation ne veut pas dire causalité : les frais de port élevés "
    "vont souvent avec des envois lointains, donc plus longs. La catégorie d'une "
    "commande est celle de son premier article, et seules les commandes livrées "
    "et notées sont prises en compte."
)

# 5. Lien vers la suite ------------------------------------------------------
st.markdown(
    "➡️ **Et ensuite ?** Les retards abîment les avis : la page suivante montre "
    "**quelles catégories** sont les plus touchées."
)
