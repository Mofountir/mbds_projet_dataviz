"""Page d'accueil : le projet, les utilisateurs, le pipeline et le parcours."""

import streamlit as st

KAGGLE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

st.title("Olist : retards de livraison et satisfaction des clients")
st.markdown(
    f"""
Olist est une place de marché brésilienne : de petits vendeurs y vendent leurs
produits et Olist organise la livraison. Les données ([Kaggle]({KAGGLE})) contiennent
environ **100 000 commandes réelles** (2016 à 2018) dans **9 tables** reliées :
commandes, articles, paiements, avis, clients, vendeurs, produits, géolocalisation
et traduction des catégories.

Les données sont **multivariées** : quantitatives (prix, frais, délai), ordinales
(note de 1 à 5), catégorielles (état, catégorie, paiement), temporelles (dates) et
géographiques (états, coordonnées).
"""
)

st.subheader("Le fil de l'histoire")
st.markdown(
    """
| Page | Question | Technique |
|---|---|---|
| **1. Où ?** | Où les livraisons sont-elles lentes ? | Carte choroplèthe |
| **2. Quand ?** | Quand les retards apparaissent-ils ? | Série temporelle |
| **3. Quel effet ?** | Les retards font-ils baisser les notes ? | Coordonnées parallèles |
| **4. Quelles catégories ?** | Quelles catégories sont touchées ? | Treemap |

Chaque page suit la même structure : **question → vue d'ensemble → détail →
réponse → lien vers la page suivante**. Le menu de gauche permet aussi de
**changer de jeu de données** (2017, 2018, toutes les commandes).
"""
)

st.subheader("Utilisateurs visés et leurs tâches")
st.markdown(
    """
**Utilisateurs principaux :** les analystes d'Olist (responsables de catégories,
logistique, service client). Ils connaissent le métier, pas la programmation.
**Utilisateurs secondaires :** les vendeurs, qui se comparent à leur région et à
leur catégorie.

| Besoin | Tâche dans l'outil | Page |
|---|---|---|
| Savoir où sont les problèmes | Comparer les états, zoomer sur un état | 1 |
| Comprendre les tendances | Trouver les pics, zoomer sur une période | 2 |
| Trouver ce qui provoque les mauvais avis | Filtrer par délai, prix, frais et voir les notes | 3 |
| Savoir quelles catégories comptent | Classer les catégories, zoomer d'un groupe à une catégorie | 4 |
"""
)

st.subheader("Pipeline de visualisation")
st.graphviz_chart(
    """
digraph {
  rankdir=LR; node [shape=box, style="rounded", fontname="Helvetica", fontsize=11];
  raw [label="Kaggle\\n9 CSV bruts\\n(data/01_raw)", shape=cylinder];
  s1 [label="Script 1\\ndatasets.py\\nlecture des CSV"];
  s2 [label="Script 2\\ntransforms.py\\nnettoyage, jointures,\\ncalculs"];
  prim [label="Données traitées\\n(data/03_primary)", shape=cylinder];
  s3 [label="Script 3\\nfiltre du jeu de données,\\nagrégations"];
  map [label="charts.py\\nmapping données →\\nvariables visuelles"];
  page [label="Page Streamlit\\nvue + interactions"];
  raw -> s1 -> s2 -> prim -> s3 -> map -> page;
  page -> s3 [style=dashed, label=" filtres,\\n sélection"];
}
"""
)
st.caption(
    "Chaque page suit cette chaîne : lecture des données brutes, préparation, "
    "puis mapping visuel. Les interactions de l'utilisateur reviennent sur les "
    "étapes de filtrage et la vue est redessinée."
)
