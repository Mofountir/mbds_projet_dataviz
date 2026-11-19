"""Finitions du dashboard compatibles avec les thèmes natifs clair et sombre.

Les couleurs de fond, de texte et la barre latérale restent gérées par Streamlit.
"""

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
<style>
.st-key-treemap_dashboard h1,
.st-key-coordonnees_dashboard h1 {font-size:2.15rem; letter-spacing:-.04em;}
.st-key-treemap_dashboard h3,
.st-key-coordonnees_dashboard h3 {font-size:1.12rem; letter-spacing:-.025em;}
.st-key-treemap_dashboard [data-testid="stMetricValue"],
.st-key-coordonnees_dashboard [data-testid="stMetricValue"] {font-size:1.75rem;}
.st-key-treemap_dashboard [data-testid="stVerticalBlockBorderWrapper"],
.st-key-coordonnees_dashboard [data-testid="stVerticalBlockBorderWrapper"] {
    border-radius:14px;
}
.dashboard-context {font-size:.8rem; font-weight:600; letter-spacing:.04em; color:inherit;}
.metric-comparison {
    display:inline-block; font-size:.9rem; font-weight:650; line-height:1.5;
    margin:.5rem 0 0; padding:.15rem .5rem; border-radius:6px; color:inherit;
}
.metric-comparison.higher {color:#c84453; background:rgba(200,68,83,.12);}
.metric-comparison.lower {color:#16836b; background:rgba(22,131,107,.12);}
.metric-comparison.neutral {background:rgba(128,128,128,.1);}
.st-key-treemap_kpis [data-testid="stMetric"],
.st-key-treemap_detail_metrics [data-testid="stMetric"],
.st-key-coordonnees_dashboard [data-testid="stMetric"] {
    padding:0; border:0; box-shadow:none; background:transparent;
}
</style>
""",
        unsafe_allow_html=True,
    )
