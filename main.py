"""Point d'entrée Streamlit : enregistrement des pages et navigation.

Fichier partagé. Le menu (barre de gauche) affiche les pages dans l'ordre de
l'histoire. Chaque membre code sa page dans ``src/mbds_projet_dataviz/pages/`` :
le fichier existe déjà, il suffit de remplacer son contenu.
"""

import streamlit as st

PAGES_DIR = "src/mbds_projet_dataviz/pages"

PAGES = {
    "Présentation": [
        st.Page(
            f"{PAGES_DIR}/about.py", title="Accueil", url_path="accueil", default=True
        ),
    ],
    "L'histoire en 4 étapes": [
        # Membre 1 : carte du Brésil
        st.Page(
            f"{PAGES_DIR}/carte.py", title="1. Où ? Carte des retards", url_path="carte"
        ),
        # Membre 2 : série temporelle
        st.Page(
            f"{PAGES_DIR}/temps.py", title="2. Quand ? Évolution", url_path="temps"
        ),
        # Membre 3 : coordonnées parallèles
        st.Page(
            f"{PAGES_DIR}/coordonnees.py",
            title="3. Quel effet ? Retards et avis",
            url_path="coordonnees",
        ),
        # Membre 4 : treemap
        st.Page(
            f"{PAGES_DIR}/treemap.py",
            title="4. Quelles catégories ?",
            url_path="treemap",
        ),
    ],
}


def main():
    st.set_page_config(page_title="Olist DataViz", layout="wide")
    st.navigation(PAGES).run()


if __name__ == "__main__":
    main()
