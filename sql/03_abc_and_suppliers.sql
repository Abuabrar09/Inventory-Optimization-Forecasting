-- 1. ABC analysis: rank items by annual consumption value (units sold x unit cost)
--    A = top 80% of value, B = next 15%, C = last 5%
CREATE OR REPLACE TABLE abc AS
WITH item_value AS (
    SELECT
        s.item,
        i.category,
        SUM(s.units_sold)               AS units_2017,
        SUM(s.units_sold) * i.unit_cost AS annual_value
    FROM sales s
    JOIN items i ON s.item = i.item
    WHERE YEAR(s.sale_date) = 2017
    GROUP BY s.item, i.category, i.unit_cost
),
ranked AS (
    SELECT
        *,
        SUM(annual_value) OVER (ORDER BY annual_value DESC) * 100.0
            / SUM(annual_value) OVER () AS cumulative_pct
    FROM item_value
)
SELECT
    *,
    CASE WHEN cumulative_pct <= 80 THEN 'A'
         WHEN cumulative_pct <= 95 THEN 'B'
         ELSE 'C' END AS abc_class
FROM ranked;

-- 2. ABC summary: how much value sits in each class?
SELECT
    abc_class,
    COUNT(*)                                                       AS items,
    ROUND(SUM(annual_value), 0)                                    AS annual_value,
    ROUND(SUM(annual_value) * 100.0 / SUM(SUM(annual_value)) OVER (), 1) AS value_share_pct
FROM abc
GROUP BY abc_class
ORDER BY abc_class;

-- 3. Supplier performance: promised vs actual lead time
SELECT
    sp.supplier_name,
    sp.promised_lead_time_days                                         AS promised_days,
    COUNT(*)                                                           AS orders,
    ROUND(AVG(DATEDIFF('day', po.order_date, po.received_date)), 1)    AS actual_avg_days,
    ROUND(STDDEV(DATEDIFF('day', po.order_date, po.received_date)), 1) AS variability_days,
    MAX(DATEDIFF('day', po.order_date, po.received_date))              AS worst_case_days,
    ROUND(AVG(CASE WHEN DATEDIFF('day', po.order_date, po.received_date)
                        > po.promised_lead_time_days THEN 1 ELSE 0 END) * 100, 1) AS late_pct
FROM purchase_orders po
JOIN suppliers sp ON po.supplier_id = sp.supplier_id
WHERE po.received_date IS NOT NULL
GROUP BY sp.supplier_name, sp.promised_lead_time_days
ORDER BY actual_avg_days DESC;
