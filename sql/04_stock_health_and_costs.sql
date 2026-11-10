-- 1. Stock health for every store + item at 31 Dec 2017
--    Demand rate = average daily sales over the last 90 days
CREATE OR REPLACE TABLE inventory_status AS
WITH demand AS (
    SELECT store, item, AVG(units_sold) AS avg_daily_units
    FROM sales
    WHERE sale_date >= DATE '2017-10-03'
    GROUP BY store, item
)
SELECT
    inv.store,
    inv.item,
    i.category,
    a.abc_class,
    i.unit_cost,
    sp.promised_lead_time_days               AS lead_time_days,
    inv.on_hand_units,
    inv.on_order_units,
    d.avg_daily_units,
    inv.on_hand_units / d.avg_daily_units    AS days_of_supply,
    inv.on_hand_units * i.unit_cost          AS stock_value,
    CASE
        WHEN inv.on_hand_units / d.avg_daily_units < sp.promised_lead_time_days THEN 'Stockout risk'
        WHEN inv.on_hand_units / d.avg_daily_units > 90                         THEN 'Excess'
        ELSE 'Healthy'
    END                                      AS stock_status
FROM inventory inv
JOIN demand    d  ON inv.store = d.store AND inv.item = d.item
JOIN items     i  ON inv.item = i.item
JOIN suppliers sp ON i.supplier_id = sp.supplier_id
JOIN abc       a  ON inv.item = a.item;

-- 2. Summary: how much stock is healthy, excess or at risk?
SELECT
    stock_status,
    COUNT(*)                                                         AS store_items,
    COUNT(DISTINCT item)                                             AS items,
    ROUND(SUM(stock_value), 0)                                       AS stock_value,
    ROUND(SUM(stock_value) * 100.0 / SUM(SUM(stock_value)) OVER (), 1) AS value_share_pct,
    ROUND(AVG(days_of_supply), 0)                                    AS avg_days_of_supply
FROM inventory_status
GROUP BY stock_status
ORDER BY stock_value DESC;

-- 3. Holding cost (assumption: 25% of stock value per year for storage, capital, insurance and shrinkage)
SELECT
    ROUND(SUM(stock_value), 0)        AS total_stock_value,
    ROUND(SUM(stock_value) * 0.25, 0) AS annual_holding_cost,
    ROUND(SUM(CASE WHEN days_of_supply > 90
                   THEN (on_hand_units - 90 * avg_daily_units) * unit_cost ELSE 0 END), 0) AS excess_stock_value,
    ROUND(SUM(CASE WHEN days_of_supply > 90
                   THEN (on_hand_units - 90 * avg_daily_units) * unit_cost ELSE 0 END) * 0.25, 0) AS excess_holding_cost_per_year
FROM inventory_status;

-- 4. Excess inventory: which items are overstocked?
SELECT
    item, category, abc_class,
    COUNT(*)                       AS stores,
    ROUND(AVG(days_of_supply), 0)  AS avg_days_of_supply,
    ROUND(SUM(stock_value), 0)     AS stock_value
FROM inventory_status
WHERE stock_status = 'Excess'
GROUP BY item, category, abc_class
ORDER BY stock_value DESC;

-- 5. Stockout risk: stock will run out before a new delivery can arrive
SELECT
    item, category, abc_class,
    COUNT(*)                       AS stores,
    ROUND(AVG(days_of_supply), 1)  AS avg_days_of_supply,
    MAX(lead_time_days)            AS lead_time_days
FROM inventory_status
WHERE stock_status = 'Stockout risk'
GROUP BY item, category, abc_class
ORDER BY abc_class, avg_days_of_supply;

-- 6. Slow-moving items: lowest inventory turnover (times stock sells through per year)
SELECT
    a.item, a.category, a.abc_class,
    ROUND(a.annual_value / SUM(st.stock_value), 1)        AS turns_per_year,
    ROUND(365 / (a.annual_value / SUM(st.stock_value)), 0) AS days_to_sell_through
FROM abc a
JOIN inventory_status st ON a.item = st.item
GROUP BY a.item, a.category, a.abc_class, a.annual_value
ORDER BY turns_per_year
LIMIT 10;