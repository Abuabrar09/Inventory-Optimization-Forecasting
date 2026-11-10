"""
03_export_for_tableau.py
Combines the outputs into one Excel file with 3 sheets, ready to upload to Tableau Public.
"""
import pandas as pd
from pathlib import Path

Path("tableau").mkdir(exist_ok=True)

plan = pd.read_csv("data/processed/inventory_plan.csv")
items = pd.read_csv("data/raw/items.csv")[["item", "category"]]

fc = pd.read_csv("data/processed/weekly_forecast.csv", parse_dates=["week_start"])
fc["units"] = fc["actual_units"].fillna(fc["forecast_units"])     # one column for the line chart
fc = fc[fc["week_start"] >= "2016-01-01"]                           # last 2 years + forecast is enough to show
fc = fc.merge(items, on="item")[["week_start", "item", "category", "type", "units"]]

accuracy = pd.read_csv("data/processed/forecast_accuracy.csv")

out = "tableau/inventory_dashboard_data.xlsx"
with pd.ExcelWriter(out) as writer:
    plan.to_excel(writer, sheet_name="Inventory_Plan", index=False)
    fc.to_excel(writer, sheet_name="Weekly_Forecast", index=False)
    accuracy.to_excel(writer, sheet_name="Forecast_Accuracy", index=False)
print(f"Saved {out}: Inventory_Plan ({len(plan)} rows), Weekly_Forecast ({len(fc):,} rows), "
      f"Forecast_Accuracy ({len(accuracy)} rows)")
      