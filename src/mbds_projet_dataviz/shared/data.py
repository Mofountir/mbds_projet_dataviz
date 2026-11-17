import pandas as pd
import streamlit as st

from mbds_projet_dataviz.shared.paths import PRIMARY_DIR

PIPELINE_COMMAND = "uv run python -m mbds_projet_dataviz.shared.pipeline"


@st.cache_data(show_spinner=False)
def load_primary(name: str, columns: list[str] | None = None) -> pd.DataFrame | None:
    """Charge ``data/03_primary/<name>.parquet`` ; ``None`` si le fichier manque."""
    path = PRIMARY_DIR / f"{name}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path, columns=columns)


def missing_data_message(name: str) -> None:
    st.error(
        f"`data/03_primary/{name}.parquet` est introuvable. "
        f"Générer les données préparées avec `{PIPELINE_COMMAND}`."
    )
