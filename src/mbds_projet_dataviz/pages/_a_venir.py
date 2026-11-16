"""Gabarit commun des pages pas encore codées (à remplacer par chaque membre)."""

import streamlit as st


def page_a_venir(titre: str, membre: str, technique: str, question: str) -> None:
    st.title(titre)
    st.info(
        f"**Page en construction — {membre}.**\n\n"
        f"Technique prévue : **{technique}**.\n\n"
        f"Question : {question}"
    )
    st.markdown(
        "Pour coder cette page, suivre la même structure que la page 3 : "
        "`domains/<domaine>/datasets.py` → `transforms.py` → `charts.py`, puis "
        "remplacer le contenu de ce fichier (question, vue d'ensemble, détail, "
        "réponse, lien vers la page suivante)."
    )
