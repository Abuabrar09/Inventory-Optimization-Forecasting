"""
02_inventory_policy.py
Turns the Q1 2018 demand forecast into an inventory policy for all 500 store-items:
safety stock, reorder point, order recommendation, and the cost of the current stock.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

SERVICE_Z = 1.65          # 95% service level: stock covers demand 95% of the time
HOLDING_RATE = 0.25       # assumption: holding stock costs 25% of its value per year
ORDER_CYCLE_DAYS = 28     # assumption: each store-item is reordered about every 4 weeks
EXCESS_DAYS = 90          # more than 90 days of supply counts as excess

# ---------- 1. Load data ----------
sales = pd.read_csv("data/raw/train.csv", parse_dates=["date"])
items = pd.read_csv("data/raw/items.csv")
suppliers = pd.read_csv("data/raw/suppliers.csv")
pos = pd.read_csv("data/raw/purchase_orders.csv", parse_dates=["order_date", "received_date"])
inv = pd.read_csv("data/raw/inventory_snapshot.csv")
fc = pd.read_csv("data/processed/weekly_forecast.csv")

# ---------- 2. Demand per store-item ----------
recent = sales[sales["date"] >= "2017-10-03"]                       # last 90 days
stats = recent.groupby(["store", "item"])["sales"].agg(recent_daily="mean", daily_std="std").reset_index()
stats["store_share"] = stats["recent_daily"] / stats.groupby("item")["recent_daily"].transform("sum")

q1 = fc[fc["type"] == "Forecast"].groupby("item")["forecast_units"].sum() / 91   # daily, all stores
stats["forecast_daily"] = stats["item"].map(q1) * stats["store_share"]

flat = sales[sales["date"].dt.year == 2017].groupby(["store", "item"])["sales"].mean()
stats["flat_daily"] = stats.set_index(["store", "item"]).index.map(flat)          # 2017 average, no seasonality

# ---------- 3. Actual lead time per supplier (from purchase orders) ----------
pos = pos.dropna(subset=["received_date"])
pos["lead_days"] = (pos["received_date"] - pos["order_date"]).dt.days
lt = pos.groupby("supplier_id")["lead_days"].agg(lt_mean="mean", lt_std="std").reset_index()

plan = (stats.merge(items, on="item").merge(lt, on="supplier_id")
             .merge(inv[["store", "item", "on_hand_units", "on_order_units"]], on=["store", "item"]))

# ---------- 4. Safety stock and reorder point ----------
# Safety stock covers both demand swings and late deliveries:
#   SS  = Z x sqrt( lead_time x demand_std^2 + daily_demand^2 x lead_time_std^2 )
#   ROP = daily_demand x lead_time + SS
d, sd, L, sL = plan["forecast_daily"], plan["daily_std"], plan["lt_mean"], plan["lt_std"]
plan["safety_stock"] = np.ceil(SERVICE_Z * np.sqrt(L * sd**2 + d**2 * sL**2))
plan["reorder_point"] = np.ceil(d * L + plan["safety_stock"])
flat_ss = SERVICE_Z * np.sqrt(L * sd**2 + plan["flat_daily"]**2 * sL**2)
plan["flat_reorder_point"] = np.ceil(plan["flat_daily"] * L + flat_ss)

# ---------- 5. Recommendation for each store-item ----------
plan["inventory_position"] = plan["on_hand_units"] + plan["on_order_units"]
plan["days_of_supply"] = plan["on_hand_units"] / d
order_up_to = plan["reorder_point"] + d * ORDER_CYCLE_DAYS
plan["action"] = np.select(
    [plan["inventory_position"] <= plan["reorder_point"], plan["days_of_supply"] > EXCESS_DAYS],
    ["Order now", "Excess: pause orders"], default="OK")
plan["order_qty"] = np.where(plan["action"] == "Order now",
                             np.ceil(order_up_to - plan["inventory_position"]), 0)

# ---------- 6. Cost: current stock vs right-sized stock ----------
plan["stock_value"] = plan["on_hand_units"] * plan["unit_cost"]
plan["target_avg_units"] = plan["safety_stock"] + d * ORDER_CYCLE_DAYS / 2   # safety stock + half an order cycle
plan["target_value"] = plan["target_avg_units"] * plan["unit_cost"]
plan["holding_cost_year"] = plan["stock_value"] * HOLDING_RATE
plan["excess_value"] = np.where(plan["days_of_supply"] > EXCESS_DAYS,
                                (plan["on_hand_units"] - d * EXCESS_DAYS) * plan["unit_cost"], 0)

print("Actions for Q1 2018 (store-items):")
print(plan["action"].value_counts().to_string())
print(f"\nOrders to place now: {int((plan['action'] == 'Order now').sum())} store-items, "
      f"{plan['order_qty'].sum():,.0f} units, ${(plan['order_qty'] * plan['unit_cost']).sum():,.0f}")
print(f"Safety stock: {plan['safety_stock'].sum():,.0f} units, ${(plan['safety_stock'] * plan['unit_cost']).sum():,.0f}")
cur, tgt = plan["stock_value"].sum(), plan["target_value"].sum()
print(f"\nCurrent stock value:      ${cur:,.0f}  (holding cost ${cur * HOLDING_RATE:,.0f}/year)")
print(f"Right-sized stock value:  ${tgt:,.0f}  (holding cost ${tgt * HOLDING_RATE:,.0f}/year)")
print(f"Cash that could be freed: ${cur - tgt:,.0f}  -> saves ${(cur - tgt) * HOLDING_RATE:,.0f}/year")
diff = (plan["flat_reorder_point"].sum() / plan["reorder_point"].sum() - 1) * 100
print(f"\nA flat 2017-average reorder point would be {diff:+.1f}% vs the seasonal forecast for Q1")

# ---------- 7. Save for Tableau ----------
cols = ["store", "item", "item_name", "category", "supplier_id", "unit_cost", "forecast_daily", "daily_std",
        "lt_mean", "lt_std", "safety_stock", "reorder_point", "on_hand_units", "on_order_units",
        "inventory_position", "days_of_supply", "action", "order_qty", "stock_value", "target_value",
        "holding_cost_year", "excess_value"]
plan[cols].round(2).to_csv("data/processed/inventory_plan.csv", index=False)
print("\nSaved data/processed/inventory_plan.csv")

# ---------- 8. Charts ----------
BLUE, ORANGE, RED, GREY = "#2a78d6", "#eb6834", "#d03b3b", "#52514e"
plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#ebeae6", "axes.axisbelow": True,
                     "axes.titlelocation": "left", "axes.titleweight": "bold", "axes.titlesize": 13,
                     "xtick.color": GREY, "ytick.color": GREY})
millions = mtick.FuncFormatter(lambda x, _: f"${x/1e6:,.1f}M")

# Chart 3: days of supply per item, coloured by status
item_view = plan.groupby("item").agg(days=("days_of_supply", "mean"), lead=("lt_mean", "mean")).sort_values("days")
status_color = [ORANGE if r.days > EXCESS_DAYS else RED if r.days < r.lead else BLUE for r in item_view.itertuples()]
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(item_view.index.astype(str), item_view["days"], color=status_color, width=0.75)
ax.axhline(EXCESS_DAYS, color=GREY, linestyle="--", linewidth=1)
ax.text(0, EXCESS_DAYS + 5, "90 days: excess above this line", fontsize=9, color=GREY)
ax.set_xlabel("Item (sorted by days of supply)", color=GREY)
ax.set_ylabel("Days of supply on hand", color=GREY)
ax.tick_params(axis="x", labelsize=7)
ax.grid(axis="x", visible=False)
ax.set_title("Days of supply by item: red will run out before restock, orange is excess")
fig.tight_layout()
fig.savefig("images/03_days_of_supply.png", dpi=150)

# Chart 4: current vs right-sized stock value
fig, ax = plt.subplots(figsize=(8, 4.2))
bars = ax.bar(["Current stock", "Right-sized stock"], [cur, tgt], color=[ORANGE, BLUE], width=0.5)
for b, v in zip(bars, [cur, tgt]):
    ax.text(b.get_x() + b.get_width() / 2, v, f"\\${v/1e6:,.1f}M", ha="center", va="bottom", fontsize=11, color=GREY)
ax.yaxis.set_major_formatter(millions)
ax.set_ylim(0, cur * 1.18)
ax.grid(axis="x", visible=False)
ax.set_title(f"Right-sizing frees \\${(cur - tgt)/1e6:,.1f}M and saves \\${(cur - tgt) * HOLDING_RATE/1e6:,.2f}M a year")
fig.tight_layout()
fig.savefig("images/04_current_vs_target_stock.png", dpi=150)
print("Saved images/03_days_of_supply.png and images/04_current_vs_target_stock.png")
