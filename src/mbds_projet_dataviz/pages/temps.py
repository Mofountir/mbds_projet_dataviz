import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.append(str(Path(__file__).resolve().parents[2]))

ROOT = Path(__file__).resolve().parents[3]
from mbds_projet_dataviz.common.load.py import load_daily, load_category_daily, select_dataset

st.title("Demand and Delivery Over Time")
st.caption("Member 2 — Focus + context time series (d3.brushX)")

choice = st.session_state.get("dataset_choice", "Olist all orders")
st.sidebar.markdown(f"**Dataset actif :** {choice}")
daily = select_dataset(load_daily(), choice)
category = select_dataset(load_category_daily(), choice)

if daily.empty:
    st.warning("No data for this dataset.")
    st.stop()

# ---------- 1. QUESTION ----------
st.markdown("## 1. Question")
st.markdown(
    "> **Hypothesis:** Black Friday (24 Nov 2017) produces the largest daily order "
    "spike, and late-delivery rates rise in the weeks after it."
)

# ---------- 2. OVERVIEW ----------
st.markdown("## 2. Overview")
st.markdown(
    "The context strip below shows daily orders, revenue, or late rate over the "
    "whole selected dataset. Look for the November 2017 peak."
)

default_start = max(pd.Timestamp("2017-01-01"), daily["date"].min())
default_end = min(pd.Timestamp("2018-08-31"), daily["date"].max())
if default_start > default_end:
    default_start = daily["date"].min()
    default_end = daily["date"].max()

date_range = st.date_input(
    "Analysis period",
    value=(default_start.date(), default_end.date()),
    min_value=daily["date"].min().date(),
    max_value=daily["date"].max().date(),
)
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start and end date.")
    st.stop()

start = pd.Timestamp(date_range[0])
end = pd.Timestamp(date_range[1])
df = daily[(daily["date"] >= start) & (daily["date"] <= end)].copy()
df_cat = category[(category["date"] >= start) & (category["date"] <= end)].copy()

if df.empty:
    st.warning("No observations in the selected period.")
    st.stop()

metric_labels = {
    "Daily orders": "orders",
    "Daily revenue (R$)": "revenue",
    "Late-delivery rate (%)": "late_rate",
}
label = st.selectbox("Measure", list(metric_labels))
metric = metric_labels[label]

plot_df = df.copy()
if metric == "late_rate":
    plot_df["late_rate"] = plot_df["late_rate"] * 100

# ---------- 3. EXPLORATION ----------
st.markdown("## 3. Exploration")
st.markdown(
    "Brush the lower strip to zoom. Hover for tooltips. "
    "For revenue, click legend items to toggle categories."
)

a, b, c = st.columns(3)
a.metric("Orders", f"{int(df['orders'].sum()):,}")
b.metric("Revenue", f"R$ {df['revenue'].sum():,.2f}")
if df["late_rate"].notna().any():
    c.metric("Mean daily late rate", f"{df['late_rate'].mean():.1%}")
else:
    c.metric("Mean daily late rate", "N/A")

chart_daily = plot_df[["date", "orders", "revenue", "late_rate"]].copy()
chart_daily["date"] = chart_daily["date"].dt.strftime("%Y-%m-%d")
daily_records = json.dumps(
    chart_daily.astype(object).where(pd.notna(chart_daily), None).to_dict("records"),
    allow_nan=False,
)

chart_cat = df_cat[["date", "category", "revenue"]].copy()
chart_cat["date"] = chart_cat["date"].dt.strftime("%Y-%m-%d")
category_records = json.dumps(
    chart_cat.astype(object).where(pd.notna(chart_cat), None).to_dict("records"),
    allow_nan=False,
)
categories = sorted(chart_cat["category"].unique().tolist())

html_path = ROOT / "d3" / "timeseries.html"
html = html_path.read_text(encoding="utf-8")
html = html.replace("__DATA__", daily_records)
html = html.replace("__CATEGORY_DATA__", category_records)
html = html.replace("__METRIC__", json.dumps(metric))
html = html.replace("__CATEGORIES__", json.dumps(categories))

components.html(html, height=560, scrolling=False)

# ---------- 4. ANSWER ----------
st.markdown("## 4. Answer")

black_friday = pd.Timestamp("2017-11-24")
analysis = daily[
    (daily["date"] >= "2017-01-01") & (daily["date"] < "2018-09-01")
].copy()

if not analysis.empty:
    peak = analysis.loc[analysis["orders"].idxmax()]
    st.write(
        f"**Peak day in analysis period:** {peak['date'].date()} "
        f"with **{int(peak['orders']):,} orders**."
    )
    if peak["date"] == black_friday:
        st.success("First part **supported**: Black Friday is the largest daily order spike.")
    else:
        st.warning(
            f"First part **rejected**: the peak is {peak['date'].date()}, not Black Friday."
        )

    after = analysis[
        (analysis["date"] >= black_friday + pd.Timedelta(days=1))
        & (analysis["date"] <= black_friday + pd.Timedelta(days=28))
    ]
    baseline = analysis[
        (analysis["date"] >= "2017-10-01") & (analysis["date"] < "2017-11-01")
    ]

    def pooled_rate(frame):
        n = frame["observed_delivery_orders"].sum()
        if n == 0:
            return float("nan")
        late = (frame["late_rate"] * frame["observed_delivery_orders"]).sum()
        return late / n

    before_rate = pooled_rate(baseline)
    after_rate = pooled_rate(after)
    if pd.notna(before_rate) and pd.notna(after_rate):
        diff = (after_rate - before_rate) * 100
        st.write(
            f"**Late-delivery rate** — Oct 2017 baseline: {before_rate:.2%}; "
            f"28 days after BF: {after_rate:.2%} (**{diff:+.1f} pp**)."
        )
        if after_rate > before_rate:
            st.success("Second part **supported**.")
        else:
            st.warning("Second part **rejected**.")
else:
    st.info("Expand the analysis period to include 2017 to test the hypothesis.")

# ---------- 5. LINK ----------
st.markdown("## 5. Link to the next page")
st.markdown(
    "Delays peak in Nov–Dec 2017. **The map page** now asks: "
    "*where* in Brazil do these delays concentrate?"
)
