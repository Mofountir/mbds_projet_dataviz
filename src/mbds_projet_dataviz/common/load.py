from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed"



def load_daily():
    path = DATA / "daily_metrics.csv"
    if not path.exists():
        raise FileNotFoundError("Processed data missing. Run python scripts/prepare_data.py")
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date")



def load_category_daily():
    path = DATA / "daily_category_revenue.csv"
    if not path.exists():
        raise FileNotFoundError("Category data missing. Run python scripts/prepare_data.py")
    return pd.read_csv(path, parse_dates=["date"])


def select_dataset(df, choice):
    if choice == "Olist 2017":
        return df[df["date"].dt.year == 2017].copy()
    if choice == "Olist 2018 (Jan-Aug)":
        mask = (df["date"] >= "2018-01-01") & (df["date"] < "2018-09-01")
        return df[mask].copy()
    return df.copy()