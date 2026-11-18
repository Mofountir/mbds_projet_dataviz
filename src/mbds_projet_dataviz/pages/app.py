import streamlit as st

st.set_page_config(page_title="Olist Analytics", page_icon="📊", layout="wide")

st.title("Olist E-Commerce Analytics")
st.write(
    "Explore sales, delivery performance, customer satisfaction, "
    "geography, and product categories."
)

options = ["Olist all orders", "Olist 2017", "Olist 2018 (Jan-Aug)"]

# On initialise la mémoire si elle n'existe pas encore
if "dataset_choice" not in st.session_state:
    st.session_state["dataset_choice"] = options[0]

# Cette fonction copie le choix du widget dans la mémoire permanente
def update_dataset():
    st.session_state["dataset_choice"] = st.session_state["temp_selector"]

# On affiche le menu avec un index pour qu'il pointe toujours sur le bon choix
idx = options.index(st.session_state["dataset_choice"])
st.sidebar.selectbox(
    "Shared dataset",
    options,
    index=idx,
    key="temp_selector",
    on_change=update_dataset
)

st.markdown("## Project overview")
st.write("This application uses the Brazilian Olist e-commerce dataset.")
st.markdown(
    "- **Time series**: demand and delivery performance\n"
    "- **Map**: geographical patterns\n"
    "- **Parallel coordinates**: order variables\n"
    "- **Treemap**: revenue and reviews by category"
)
st.info(f"Current dataset: {st.session_state['dataset_choice']}")