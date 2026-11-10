"""
01_demand_forecast.py
Forecasts weekly demand for every item, tests 3 forecasting methods on the
last 13 weeks of 2017, then uses the best method to forecast Q1 2018.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# ---------- 1. Weekly demand per item (all 10 stores combined) ----------
sales = pd.read_csv("data/raw/train.csv", parse_dates=["date"])
sales = sales[sales["date"] >= "2013-01-07"]                      # first full week
sales["week"] = sales["date"].dt.to_period("W-SUN").dt.start_time  # Monday of each week
weekly = sales.groupby(["item", "week"])["sales"].sum().unstack("item")   # rows = weeks, columns = items
print(f"Weekly demand: {weekly.shape[0]} weeks x {weekly.shape[1]} items")

# ---------- 2. Three forecasting methods ----------
def naive(history, h):
    """Next weeks = last week's demand."""
    return pd.DataFrame([history.iloc[-1]] * h)

def moving_average(history, h, n=8):
    """Next weeks = average of the last 8 weeks."""
    return pd.DataFrame([history.tail(n).mean()] * h)

def seasonal_growth(history, h):
    """Next weeks = same weeks last year x recent growth (last 13 weeks vs same 13 weeks a year earlier)."""
    growth = history.tail(13).sum() / history.iloc[-65:-52].sum()
    last_year = history.iloc[-52:-52 + h]
    return last_year.reset_index(drop=True) * growth

methods = {"Naive (last week)": naive, "8-week moving average": moving_average,
           "Seasonal + growth": seasonal_growth}

# ---------- 3. Backtest: hide the last 13 weeks, forecast them, compare ----------
H = 13
train, test = weekly.iloc[:-H], weekly.iloc[-H:]
results, backtests = [], {}
for name, fn in methods.items():
    fc = fn(train, H)
    fc.index = test.index
    backtests[name] = fc
    wape = (fc - test).abs().sum().sum() / test.sum().sum() * 100   # weighted absolute % error
    bias = (fc - test).sum().sum() / test.sum().sum() * 100          # + means over-forecast
    results.append((name, round(wape, 1), round(bias, 1)))
accuracy = pd.DataFrame(results, columns=["method", "wape_pct", "bias_pct"]).sort_values("wape_pct")
print("\nForecast accuracy on the last 13 weeks of 2017 (lower WAPE = better):")
print(accuracy.to_string(index=False))
best = accuracy.iloc[0]["method"]
print(f"\nBest method: {best}")

# ---------- 4. Forecast Q1 2018 (next 13 weeks) with the best method ----------
future = methods[best](weekly, H)
future.index = pd.date_range(weekly.index[-1] + pd.Timedelta(weeks=1), periods=H, freq="7D")
print(f"Q1 2018 forecast: {future.sum().sum():,.0f} units "
      f"(Q1 2017 actual: {weekly.loc['2017-01-02':'2017-03-27'].sum().sum():,.0f})")

# ---------- 5. Save forecast for the inventory step and for Tableau ----------
rows = []
for item in weekly.columns:
    for wk, val in weekly[item].items():
        rows.append((wk.date(), item, val, None, "Actual"))
    for wk, val in backtests[best][item].items():
        rows.append((wk.date(), item, None, round(val, 1), "Backtest"))
    for wk, val in future[item].items():
        rows.append((wk.date(), item, None, round(val, 1), "Forecast"))
pd.DataFrame(rows, columns=["week_start", "item", "actual_units", "forecast_units", "type"]) \
  .to_csv("data/processed/weekly_forecast.csv", index=False)
accuracy.to_csv("data/processed/forecast_accuracy.csv", index=False)
print("Saved data/processed/weekly_forecast.csv and forecast_accuracy.csv")

# ---------- 6. Charts ----------
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#52514e"
plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#ebeae6", "axes.axisbelow": True,
                     "axes.titlelocation": "left", "axes.titleweight": "bold", "axes.titlesize": 13,
                     "xtick.color": GREY, "ytick.color": GREY})
thousands = mtick.FuncFormatter(lambda x, _: f"{x/1000:,.0f}K")

# Chart 1: total weekly demand, backtest and Q1 2018 forecast
total = weekly.sum(axis=1)
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(total.index, total.values, color=BLUE, linewidth=1.6, label="Actual weekly demand")
ax.plot(backtests[best].index, backtests[best].sum(axis=1), color=ORANGE, linewidth=2,
        linestyle="--", label=f"Backtest: {best}")
ax.plot(future.index, future.sum(axis=1), color=ORANGE, linewidth=2.4, label="Q1 2018 forecast")
ax.axvspan(future.index[0], future.index[-1], color=GREY, alpha=0.07)
ax.yaxis.set_major_formatter(thousands)
ax.set_ylim(0)
ax.set_title("Weekly demand, all stores and items: actual, backtest and Q1 2018 forecast")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig("images/01_demand_forecast.png", dpi=150)

# Chart 2: accuracy by method
fig, ax = plt.subplots(figsize=(8, 3.6))
acc = accuracy.sort_values("wape_pct", ascending=False)
colors = [BLUE if m == best else "#b7b5ad" for m in acc["method"]]
ax.barh(acc["method"], acc["wape_pct"], color=colors, height=0.55)
for y, v in enumerate(acc["wape_pct"]):
    ax.text(v + 0.3, y, f"{v:.1f}%", va="center", fontsize=10, color=GREY)
ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_xlim(0, acc["wape_pct"].max() * 1.2)
ax.grid(axis="y", visible=False)
ax.set_title("Forecast error by method (WAPE, lower is better)")
fig.tight_layout()
fig.savefig("images/02_forecast_accuracy.png", dpi=150)
print("Saved images/01_demand_forecast.png and images/02_forecast_accuracy.png")
