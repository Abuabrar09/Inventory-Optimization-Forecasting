"""
00_build_assumptions.py
-----------------------
The Kaggle "Store Item Demand Forecasting Challenge" data (train.csv) contains
real-looking daily sales for 10 stores x 50 items (2013-2017), but nothing about
costs, suppliers or stock levels. An inventory analysis needs those, so this
script builds them as clearly labelled ASSUMPTIONS, based on the real sales.

Input:
    data/raw/train.csv          (download from Kaggle)
Output (data/raw/):
    items.csv                   category, unit cost, unit price, supplier per item
    suppliers.csv               promised lead time and lead-time variability
    purchase_orders.csv         2017 purchase orders with order and received dates
    inventory_snapshot.csv      stock on hand and on order at 31 Dec 2017
"""

import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

sales = pd.read_csv(RAW / "train.csv", parse_dates=["date"])
items_list = sorted(sales["item"].unique())
stores_list = sorted(sales["store"].unique())
print(f"Read train.csv: {len(sales):,} rows, {len(stores_list)} stores, {len(items_list)} items, "
      f"{sales.date.min().date()} to {sales.date.max().date()}")

# ---------------------------------------------------------------- suppliers (assumption)
suppliers = pd.DataFrame([
    ("SUP-01", "Lone Star Foods",        5, 1.0),
    ("SUP-02", "Gulf Coast Beverages",   4, 0.8),
    ("SUP-03", "Prairie Pantry Co",      9, 2.0),
    ("SUP-04", "Harbor Household",      12, 3.5),
    ("SUP-05", "Sunvale Personal Care", 10, 2.5),
    ("SUP-06", "Overseas Imports Ltd",  21, 6.0),
], columns=["supplier_id", "supplier_name", "promised_lead_time_days", "lead_time_std_days"])

# ---------------------------------------------------------------- items (assumption)
categories = {   # category: (supplier, unit cost range)
    "Grocery":       ("SUP-01", (1.5, 6)),
    "Beverages":     ("SUP-02", (2, 8)),
    "Pantry":        ("SUP-03", (2, 10)),
    "Household":     ("SUP-04", (4, 25)),
    "Personal Care": ("SUP-05", (3, 15)),
    "Imported":      ("SUP-06", (10, 45)),
}
cat_names = list(categories)
item_rows = []
for i, item in enumerate(items_list):
    cat = cat_names[i % len(cat_names)]
    sup, (cmin, cmax) = categories[cat]
    cost = round(rng.uniform(cmin, cmax), 2)
    price = round(cost * rng.uniform(1.30, 1.70), 2)
    item_rows.append((item, f"Item {item:02d}", cat, sup, cost, price))
items = pd.DataFrame(item_rows, columns=["item", "item_name", "category", "supplier_id", "unit_cost", "unit_price"])

# ---------------------------------------------------------------- purchase orders for 2017 (assumption)
s17 = sales[sales.date.dt.year == 2017].sort_values("date")
dates17 = pd.date_range("2017-01-01", "2017-12-31")
sup = suppliers.set_index("supplier_id")
po_rows, n = [], 1
for (store, item), g in s17.groupby(["store", "item"]):
    it = items.loc[items.item == item].iloc[0]
    lt_mean, lt_std = sup.loc[it.supplier_id, "promised_lead_time_days"], sup.loc[it.supplier_id, "lead_time_std_days"]
    daily = g.set_index("date")["sales"].reindex(dates17, fill_value=0).values
    day = int(rng.integers(0, 7))
    while day < len(dates17) - 3:
        cover = int(rng.integers(14, 29))
        qty = max(int(daily[day:day + cover].sum() * rng.uniform(0.95, 1.12)), 1)
        lt = max(1, int(round(rng.normal(lt_mean + 0.2 * lt_std, lt_std))))   # suppliers run a bit late
        received = dates17[day] + pd.Timedelta(days=lt)
        po_rows.append((f"PO-{n:06d}", store, item, it.supplier_id, dates17[day].date(), int(lt_mean),
                        received.date() if received <= dates17[-1] else None, qty, it.unit_cost))
        n += 1
        day += cover
purchase_orders = pd.DataFrame(po_rows, columns=["po_id", "store", "item", "supplier_id", "order_date",
                                                 "promised_lead_time_days", "received_date", "quantity", "unit_cost"])

# ---------------------------------------------------------------- inventory snapshot at 31 Dec 2017 (assumption)
# Most items carry 2-6 weeks of stock. Some were over-bought (excess); some are running short.
avg90 = sales[sales.date > sales.date.max() - pd.Timedelta(days=90)].groupby(["store", "item"])["sales"].mean()
order = list(rng.permutation(items_list))
excess_items, short_items = set(order[:8]), set(order[8:14])
snap = []
for (store, item), ad in avg90.items():
    if item in excess_items:
        days_cover = rng.uniform(120, 300)
    elif item in short_items:
        days_cover = rng.uniform(2, 7)
    else:
        days_cover = rng.uniform(14, 45)
    on_hand = int(ad * days_cover)
    on_order = 0 if item in excess_items else int(ad * rng.uniform(0, 12))
    snap.append((store, item, on_hand, on_order, "2017-12-31"))
inventory = pd.DataFrame(snap, columns=["store", "item", "on_hand_units", "on_order_units", "snapshot_date"])

items.to_csv(RAW / "items.csv", index=False)
suppliers.to_csv(RAW / "suppliers.csv", index=False)
purchase_orders.to_csv(RAW / "purchase_orders.csv", index=False)
inventory.to_csv(RAW / "inventory_snapshot.csv", index=False)
print(f"Saved items.csv ({len(items)}), suppliers.csv ({len(suppliers)}), "
      f"purchase_orders.csv ({len(purchase_orders):,}), inventory_snapshot.csv ({len(inventory)})")
