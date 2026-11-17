"""Page 3 : coordonnées parallèles — le retard explique-t-il les mauvais avis ?"""

import streamlit as st

from mbds_projet_dataviz.domains.coordonnees import charts, datasets, transforms
from mbds_projet_dataviz.domains.treemap.labels import category_label, number

PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False}

# Sélections de départ prêtes pour la démo : {nom: {colonne: (min, max)}}.
PRESETS = {
    "Aucune": {},
    "Avis 1-2 ★": {"review_score": (1, 2)},
    "Prix élevés": {"price": (175, 5000)},
    "Frais élevés": {"freight": (27, 300)},
    "Livraison longue": {"delivery_days": (20, 60)},
}
PRICE_STEPS = [0, 10, 30, 50, 100, 175, 300, 1000, 5000]
FREIGHT_STEPS = [0, 5, 10, 15, 20, 27, 50, 100, 300]


def comparison_line(text: str) -> None:
    st.markdown(f'<div class="metric-comparison">{text}</div>', unsafe_allow_html=True)


def card_metric(label: str, value: str, help_text: str, note: str = "") -> None:
    with st.container(border=True):
        st.metric(label, value, help=help_text)
        if note:
            comparison_line(note)


try:
    all_orders = datasets.load_orders()
except FileNotFoundError:
    st.error("Les données des commandes ne sont pas disponibles.")
    with st.expander("Préparer les données"):
        st.code("python -m mbds_projet_dataviz.domains.coordonnees.transforms")
    st.stop()

dataset = st.sidebar.selectbox(
    "Jeu de données", list(datasets.DATASETS), index=2, key="dataset"
)
orders = transforms.filter_dataset(all_orders, dataset)
numbers = transforms.key_numbers(orders)
summary = transforms.category_summary(orders)
by_size = summary.sort_values("orders", ascending=False)["category"].tolist()

with st.container(key="coordonnees_dashboard"):
    st.title("Qu'est-ce qui provoque les mauvais avis ?")
    st.markdown(
        "**Hypothèse :** c'est le **retard de livraison**, et non le prix ou les "
        "frais de port, qui explique les avis à 1 ou 2 étoiles."
    )
    st.markdown(
        '<div class="dashboard-context">'
        f"{dataset.replace('Olist ', '').replace('— ', '')} · "
        f"{len(summary)} catégories · {number(numbers['orders'])} commandes "
        "livrées et notées</div>",
        unsafe_allow_html=True,
    )

    # Chiffres clés ----------------------------------------------------------
    with st.container(key="coordonnees_kpis"):
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            card_metric(
                "Avis négatifs · livré en retard",
                f"{number(numbers['bad_rate_late'], 1)} %",
                "Part des commandes livrées après la date promise qui reçoivent "
                "1 ou 2 étoiles.",
            )
        with k2:
            card_metric(
                "Avis négatifs · livré à l'heure",
                f"{number(numbers['bad_rate_on_time'], 1)} %",
                "Part des commandes livrées à temps qui reçoivent 1 ou 2 étoiles.",
            )
        with k3:
            card_metric(
                "Livraisons en retard",
                f"{number(numbers['late_rate'], 1)} %",
                "Livraison après le jour annoncé par Olist.",
            )
        with k4:
            card_metric(
                "Délai médian · avis négatifs",
                f"{number(numbers['median_days_bad'], 0)} jours",
                "Médiane : la moitié des commandes est en dessous, l'autre moitié "
                "au-dessus.",
                f"contre {number(numbers['median_days_good'], 0)} jours pour les "
                "autres avis",
            )

    # 1. Vue d'ensemble ------------------------------------------------------
    with st.container(border=True):
        st.subheader(
            "1. Vue d'ensemble : une ligne par catégorie",
            help=(
                "Chaque ligne relie les valeurs moyennes d'une catégorie (toutes "
                "ses commandes) : en haut = grande valeur, en bas = petite. "
                "Couleur = note moyenne. Survolez une ligne pour voir la catégorie, "
                "et le titre d'un axe pour sa définition."
            ),
        )
        st.markdown(
            "Les catégories **rouges** (mal notées) passent-elles plus haut sur "
            "l'axe *Livraison* ou sur l'axe *Prix* ?"
        )
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        categories = c1.multiselect(
            "Catégories mises en avant (et détaillées plus bas)",
            by_size,
            default=by_size[:4],
            format_func=category_label,
            key="coordonnees_categories",
        )
        only_chosen = c2.toggle(
            "Seulement celles-ci", value=False, key="coordonnees_only_chosen"
        )
        shown = (
            summary[summary["category"].isin(categories)] if only_chosen else summary
        )
        if shown.empty:
            st.info("Choisissez au moins une catégorie.")
        else:
            st.plotly_chart(
                charts.overview_parcoords(shown, categories),
                width="stretch",
                config=PLOT_CONFIG,
                key="coordonnees_overview",
            )

    # 2. Détail --------------------------------------------------------------
    with st.container(border=True):
        st.subheader(
            "2. Détail : les commandes une par une",
            help=(
                "Une ligne = une commande des catégories choisies (2 000 au "
                "maximum, tirées au hasard). Réglez une plage sur un axe "
                "(brushing) : les commandes dans la plage restent en couleur, "
                "les autres pâlissent, une bande jaune marque la plage. "
                "Survolez une ligne colorée pour voir le détail de la commande."
            ),
        )
        if not categories:
            st.info("Choisissez au moins une catégorie dans la vue d'ensemble.")
            st.stop()

        preset = (
            st.segmented_control(
                "Sélection rapide",
                list(PRESETS),
                default="Aucune",
                key="coordonnees_preset",
            )
            or "Aucune"
        )
        start = PRESETS[preset]
        s1, s2, s3, s4 = st.columns(4)
        review = s1.slider(
            "Note", 1, 5, start.get("review_score", (1, 5)), key=f"review_{preset}"
        )
        days = s2.slider(
            "Livraison (jours)",
            0,
            60,
            start.get("delivery_days", (0, 60)),
            key=f"days_{preset}",
        )
        price = s3.select_slider(
            "Prix (R$)",
            PRICE_STEPS,
            start.get("price", (0, 5000)),
            key=f"price_{preset}",
        )
        freight = s4.select_slider(
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

        with st.expander("Ordre des axes"):
            axis_order = st.multiselect(
                "Enlevez puis remettez un axe pour le déplacer à la fin",
                list(charts.DETAIL_AXES),
                default=list(charts.DETAIL_AXES),
                format_func=lambda c: charts.DETAIL_AXES[c]["label"],
                key="coordonnees_axes",
            )
        if len(axis_order) < 2:
            st.info("Gardez au moins deux axes.")
            st.stop()

        detail = transforms.sample_orders(orders, categories, n=2000)
        st.plotly_chart(
            charts.detail_parcoords(
                detail, transforms.selection_mask(detail, filters), filters, axis_order
            ),
            width="stretch",
            config=PLOT_CONFIG,
            key="coordonnees_detail",
        )

        # Chiffres de la sélection, sur TOUTES les commandes des catégories.
        in_categories = orders[orders["category"].isin(categories)]
        comparison = transforms.selection_comparison(
            in_categories, transforms.selection_mask(in_categories, filters)
        )
        if comparison:
            st.markdown(
                f"**Sélection : {number(comparison['n'])} commandes**, comparées "
                "au reste des catégories choisies"
            )
            m1, m2, m3 = st.columns(3)
            with m1:
                card_metric(
                    "Délai médian",
                    f"{number(comparison['days_in'], 1)} jours",
                    "Délai de livraison médian des commandes sélectionnées.",
                    f"contre {number(comparison['days_out'], 1)} jours pour le reste",
                )
            with m2:
                card_metric(
                    "Livraisons en retard",
                    f"{number(comparison['late_in'], 1)} %",
                    "Part des commandes sélectionnées livrées après la date promise.",
                    f"contre {number(comparison['late_out'], 1)} % pour le reste",
                )
            if "review_score" not in filters:  # sinon la valeur est évidente
                with m3:
                    card_metric(
                        "Avis négatifs",
                        f"{number(comparison['bad_in'], 1)} %",
                        "Part des commandes sélectionnées notées 1 ou 2 étoiles.",
                        f"contre {number(comparison['bad_out'], 1)} % pour le reste",
                    )
        else:
            st.caption("Réglez un curseur pour comparer une sélection au reste.")

    # 3. Réponse -------------------------------------------------------------
    with st.container(border=True):
        st.subheader(
            "3. Réponse : le délai compte, le prix beaucoup moins",
            help=(
                "Les commandes sont rangées puis coupées en 5 groupes égaux "
                "(quintiles), du plus petit (Q1) au plus grand (Q5). Chaque barre "
                "donne la part d'avis 1-2 étoiles du groupe."
            ),
        )
        st.plotly_chart(
            charts.quintile_small_multiples(
                {
                    "Délai de livraison": (
                        "j",
                        transforms.bad_rate_by_quintile(orders, "delivery_days"),
                    ),
                    "Prix": ("R$", transforms.bad_rate_by_quintile(orders, "price")),
                    "Frais de port": (
                        "R$",
                        transforms.bad_rate_by_quintile(orders, "freight"),
                    ),
                }
            ),
            width="stretch",
            config=PLOT_CONFIG,
            key="coordonnees_quintiles",
        )
        rho = numbers["spearman"]
        st.markdown(
            f"**Hypothèse confirmée.** Livrée en retard, une commande reçoit un avis "
            f"négatif dans **{number(numbers['bad_rate_late'], 0)} %** des cas, "
            f"contre **{number(numbers['bad_rate_on_time'], 0)} %** à l'heure. "
            "Le lien de la note avec le **délai** (corrélation de Spearman "
            f"{number(rho['delivery_days'], 2)}) est bien plus fort qu'avec le "
            f"**prix** ({number(rho['price'], 2)}) ou les **frais de port** "
            f"({number(rho['freight'], 2)})."
        )

    with st.expander("Définition de chaque axe"):
        st.markdown(
            "\n".join(
                f"- **{name}** : {text}" for name, text in charts.AXIS_HELP_TEXT.items()
            )
        )
    with st.expander("Chiffres par catégorie"):
        st.dataframe(
            summary.assign(category=summary["category"].map(category_label))
            .rename(
                columns={
                    "category": "Catégorie",
                    "orders": "Commandes",
                    "price": "Prix moyen (R$)",
                    "freight": "Frais moyens (R$)",
                    "weight_kg": "Poids moyen (kg)",
                    "delivery_days": "Livraison moy. (j)",
                    "late_rate": "Retards (%)",
                    "installments": "Mensualités moy.",
                    "review_score": "Note / 5",
                    "bad_rate": "Avis négatifs (%)",
                }
            )
            .round(1),
            hide_index=True,
            width="stretch",
        )
    with st.expander("À propos des chiffres"):
        st.markdown(
            f"**Source :** [Olist — commandes 2016–2018]({datasets.KAGGLE_SOURCE}). "
            "Seules les commandes livrées avec un avis sont incluses ; le dernier "
            "avis est retenu. Une commande est rattachée à la catégorie de son "
            "premier article ; les catégories de moins de 30 commandes sont "
            "écartées de la vue d'ensemble.\n\n"
            "**À garder en tête :** corrélation n'est pas causalité. Les frais de "
            "port élevés vont souvent avec des envois lointains, donc plus longs."
        )

    st.markdown(
        "➡️ **Et ensuite ?** Les retards abîment les avis : la page suivante montre "
        "**quelles catégories** sont les plus touchées."
    )
