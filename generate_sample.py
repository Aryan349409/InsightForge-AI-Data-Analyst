"""Generate a realistic, deliberately messy retail sales dataset for demos/evaluation."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 1500
dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
products = {"Laptop": 55000, "Phone": 28000, "Headphones": 3500, "Tablet": 22000, "Monitor": 14000, "Keyboard": 1800}
regions = ["North", "South", "East", "West"]
channels = ["Online", "Retail", "Partner"]

prod = rng.choice(list(products), n, p=[.12, .25, .25, .12, .14, .12])
qty = rng.integers(1, 6, n)
base = np.array([products[p] for p in prod])
d = rng.choice(dates, n)
season = 1 + 0.25 * np.isin(pd.DatetimeIndex(d).month, [10, 11, 12])
price = (base * rng.normal(1, .05, n) * season).round(2)
disc = rng.choice([0, 5, 10, 15, 20], n, p=[.4, .2, .2, .1, .1])
revenue = (price * qty * (1 - disc / 100)).round(2)

df = pd.DataFrame({
    "order_id": np.arange(1001, 1001 + n), "order_date": pd.to_datetime(d),
    "product": prod, "region": rng.choice(regions, n, p=[.3, .25, .25, .2]),
    "channel": rng.choice(channels, n, p=[.5, .35, .15]),
    "quantity": qty, "unit_price": price, "discount_pct": disc, "revenue": revenue,
    "customer_age": rng.integers(18, 70, n).astype(float),
    "returned": rng.choice(["Yes", "No"], n, p=[.07, .93]),
})
df = df.sort_values("order_date").reset_index(drop=True)

# --- inject realistic mess ---
df.loc[rng.choice(n, 60, replace=False), "customer_age"] = np.nan
df.loc[rng.choice(n, 40, replace=False), "region"] = np.nan
df.loc[rng.choice(n, 25, replace=False), "region"] = df["region"].str.lower()
df.loc[rng.choice(n, 8, replace=False), "revenue"] *= 12            # outliers
df.loc[rng.choice(n, 20, replace=False), "product"] = df["product"] + " "   # trailing spaces
df = pd.concat([df, df.sample(18, random_state=1)], ignore_index=True)       # duplicates
df["order_date"] = df["order_date"].dt.strftime("%d-%m-%Y")
df.to_csv("sample_data/sales.csv", index=False)
print("Wrote sample_data/sales.csv", df.shape)
