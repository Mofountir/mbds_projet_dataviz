from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]

df = pd.read_csv(ROOT / "data" / "processed" / "daily_metrics.csv", parse_dates=["date"]).sort_values("date")
df = df[(df["date"] >= "2017-01-01") & (df["date"] < "2018-09-01")].copy()

if df.empty:
    raise ValueError("No observations in the analysis period.")

peak = df.loc[df["orders"].idxmax()]
print("Largest daily order count:")
print(peak[["date", "orders"]].to_string())

black_friday = pd.Timestamp("2017-11-24")
event = df[df["date"] == black_friday]
if event.empty:
    print("Black Friday is missing from the data.")
else:
    print(f"\nBlack Friday orders: {int(event.iloc[0]['orders'])}")

after = df[
    (df["date"] >= black_friday + pd.Timedelta(days=1))
    & (df["date"] <= black_friday + pd.Timedelta(days=28))
]
baseline = df[(df["date"] >= "2017-10-01") & (df["date"] < "2017-11-01")]


def pooled_rate(frame):
    n = frame["observed_delivery_orders"].sum()
    if n == 0:
        return float("nan")
    late = (frame["late_rate"] * frame["observed_delivery_orders"]).sum()
    return late / n


before_rate = pooled_rate(baseline)
after_rate = pooled_rate(after)
print(f"\nOctober baseline: {before_rate:.2%}")
print(f"Following 28 days: {after_rate:.2%}")
print(f"Difference in percentage points: {(after_rate - before_rate) * 100:.2f}")