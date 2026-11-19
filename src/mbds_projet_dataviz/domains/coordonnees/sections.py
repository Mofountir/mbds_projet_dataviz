"""Section « 3. Quel effet ? » du scénario : version courte (2 minutes) de la page 3.

Un seul graphique de coordonnées parallèles avec 3 étapes à cliquer, puis la
preuve en barres et le message à retenir. La page 3 garde la version complète
(vue d'ensemble par catégorie, curseurs, ordre des axes).
"""

import pandas as pd
import streamlit as st

from mbds_projet_dataviz.domains.coordonnees import charts, transforms
from mbds_projet_dataviz.domains.treemap.labels import number

PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False}

# Axes gardés pour l'oral : ceux qui comptent pour la question.
AXES = ["price", "freight", "delivery_days", "delay_days", "review_score"]

# Les 3 étapes de la démonstration : {nom: (filtre, phrase à dire)}.
STEPS = {
    "① Toutes les commandes": (
        {},
        "Chaque ligne est une commande. Rouge = 1 ou 2 étoiles, bleu = 4 ou 5. "
        "Regardez l'axe **Livraison** : les lignes rouges montent plus haut.",
    ),
    "② Seulement les avis 1-2 ★": (
        {"review_score": (1, 2)},
        "On ne garde que les clients mécontents : leurs lignes passent **haut sur "
        "Livraison et Retard**, mais **partout sur Prix**.",
    ),
    "③ Seulement les prix élevés": (
        {"price": (175, 1e9)},
        "Contre-épreuve : les produits chers (≥ 175 R$) ont **à peine plus** "
        "d'avis 1-2 ★ que les autres. Le prix n'explique pas la note.",
    ),
}


def _card(column, label: str, value: str, note: str) -> None:
    with column, st.container(border=True):
        st.metric(label, value)
        st.caption(note)


def scenario(orders: pd.DataFrame, key: str = "scenario_effect") -> str:
    """Affiche la section et renvoie le message à retenir."""
    numbers = transforms.key_numbers(orders)

    st.markdown(
        "**Question :** pourquoi des clients mettent-ils 1 ou 2 étoiles ? "
        "**Hypothèse :** à cause du **retard de livraison**, pas du prix."
    )

    # 1. Les chiffres qui répondent ------------------------------------------
    c1, c2, c3 = st.columns(3)
    _card(
        c1,
        "Avis 1-2 ★ si livré en retard",
        f"{number(numbers['bad_rate_late'], 0)} %",
        f"contre {number(numbers['bad_rate_on_time'], 0)} % à l'heure",
    )
    _card(
        c2,
        "Délai médian des avis 1-2 ★",
        f"{number(numbers['median_days_bad'], 0)} jours",
        f"contre {number(numbers['median_days_good'], 0)} jours pour les autres",
    )
    _card(
        c3,
        "Lien avec la note (Spearman)",
        f"délai {number(numbers['spearman']['delivery_days'], 2)}",
        f"prix {number(numbers['spearman']['price'], 2)} · frais "
        f"{number(numbers['spearman']['freight'], 2)}",
    )

    # 2. Le graphique en 3 étapes --------------------------------------------
    st.markdown("**Coordonnées parallèles : cliquez les 3 étapes dans l'ordre**")
    step = (
        st.segmented_control(
            "Étape",
            list(STEPS),
            default=list(STEPS)[0],
            key=f"{key}_step",
            label_visibility="collapsed",
        )
        or list(STEPS)[0]
    )
    filters, sentence = STEPS[step]
    sample = orders.sample(min(len(orders), 1200), random_state=42)
    st.plotly_chart(
        charts.detail_parcoords(
            sample,
            transforms.selection_mask(sample, filters),
            filters,
            AXES,
            opacity=0.55 if not filters else 1.0,
        ),
        width="stretch",
        config=PLOT_CONFIG,
        key=f"{key}_chart_{step}",
    )
    selected = transforms.selection_mask(orders, filters)
    comparison = transforms.selection_comparison(orders, selected)
    if comparison:
        details = (
            f"{number(comparison['n'])} commandes · délai médian "
            f"{number(comparison['days_in'], 0)} j (reste : "
            f"{number(comparison['days_out'], 0)} j) · en retard "
            f"{number(comparison['late_in'], 0)} % (reste : "
            f"{number(comparison['late_out'], 0)} %)"
        )
        if "review_score" not in filters:
            details += (
                f" · avis 1-2 ★ {number(comparison['bad_in'], 0)} % (reste : "
                f"{number(comparison['bad_out'], 0)} %)"
            )
        st.info(f"{sentence}\n\n{details}")
    else:
        st.info(sentence)
    st.caption(
        "1 200 commandes tirées au hasard pour le dessin ; les chiffres portent sur "
        "toutes les commandes. Survolez une ligne colorée pour voir la commande."
    )

    # 3. La preuve -------------------------------------------------------------
    st.markdown(
        "**La preuve : part d'avis 1-2 ★ quand le délai, le prix ou les frais augmentent**"
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
        key=f"{key}_quintiles",
    )

    return (
        f"**Hypothèse confirmée.** Livrée en retard, une commande reçoit 1 ou 2 "
        f"étoiles dans **{number(numbers['bad_rate_late'], 0)} %** des cas, contre "
        f"**{number(numbers['bad_rate_on_time'], 0)} %** à l'heure. Les mauvais avis "
        "montent avec le **délai**, presque pas avec le **prix**. Attention : c'est "
        "une corrélation, pas une preuve de cause."
    )
