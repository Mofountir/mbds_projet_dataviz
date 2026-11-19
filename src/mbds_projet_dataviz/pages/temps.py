"""Page du domaine 2 : série temporelle — quand les retards apparaissent-ils ?

Hypothèse et approche focus + contexte reprises de la branche ``2_time_series``
(membre 2), reconstruites sur le pipeline commun et le filtre global.
"""

import streamlit as st

from mbds_projet_dataviz.domains.temps import datasets, sections
from mbds_projet_dataviz.shared.data import missing_data_message
from mbds_projet_dataviz.shared.filters import selected_dataset
from mbds_projet_dataviz.shared.transforms import filter_dataset

st.title("Temps : quand les retards apparaissent-ils ?")
st.markdown(
    "**Question.** Le Black Friday du 24 novembre 2017 crée-t-il le plus grand pic "
    "de commandes, et les livraisons en retard augmentent-elles dans les semaines "
    "qui suivent ?"
)

orders = datasets.load_orders()
if orders is None:
    missing_data_message("orders")
    st.stop()
dataset = selected_dataset()
orders = filter_dataset(orders, dataset)
if orders.empty:
    st.warning("Aucune commande dans ce jeu de données.")
    st.stop()

with st.expander("Données et définitions"):
    st.markdown(
        """
- **Source** : table `orders` du pipeline commun (1 ligne par commande), datée par
  le jour d'achat.
- **Commandes** : toutes les commandes passées, quel que soit leur statut.
- **Retard** : commande livrée un jour postérieur à la date estimée annoncée au
  client (même définition que la page carte) ; calculé sur les commandes livrées.
- **Avant / après Black Friday** : commandes achetées en octobre 2017, puis du
  25 novembre au 22 décembre 2017 (28 jours) ; intervalle de confiance de Wilson
  à 95 %.
"""
    )

sections.overview(orders, dataset, "temps_frequency")
sections.detail(orders)

st.subheader("Réponse")
result = sections.answer(orders)
if result is None:
    st.info(
        "Black Friday 2017 n'est pas dans ce jeu de données : choisir 2017 ou "
        "toutes les commandes dans la barre latérale."
    )
else:
    verdict, paragraphs = result
    st.markdown(f"#### {verdict} ({dataset})")
    for paragraph in paragraphs:
        st.markdown(paragraph)

st.markdown(
    "**Limites.** La date est celle de l'achat : un retard est rattaché au jour de "
    "la commande, pas au jour de livraison. Les données ne disent pas pourquoi un "
    "colis est en retard (transporteur, météo, grève) : la série montre quand, pas "
    "la cause."
)
st.markdown(
    "➡️ **Et ensuite ?** On sait où et quand les retards se produisent : la page "
    "suivante montre **quel effet** ils ont sur les avis des clients."
)
