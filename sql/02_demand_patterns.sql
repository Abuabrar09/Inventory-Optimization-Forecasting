-- 1. Weekly demand per store and item (the level we will forecast at)
CREATE OR REPLACE TABLE weekly_demand AS
SELECT
    DATE_TRUNC('week', sale_date) AS week_start,
    store,
    item,
    SUM(units_sold)               AS units
FROM sales
WHERE sale_date >= DATE '2013-01-07'
GROUP BY DATE_TRUNC('week', sale_date), store, item;

-- 2. Check the weekly table
SELECT
    COUNT(DISTINCT week_start) AS weeks,
    MIN(week_start)            AS first_week,
    MAX(week_start)            AS last_week,
    COUNT(*)                   AS row_count
FROM weekly_demand;

-- 3. Is demand growing year over year?
WITH yearly AS (
    SELECT YEAR(sale_date) AS year, SUM(units_sold) AS units
    FROM sales
    GROUP BY YEAR(sale_date)
)
SELECT
    year,
    units,
    ROUND((units - LAG(units) OVER (ORDER BY year)) * 100.0
          / LAG(units) OVER (ORDER BY year), 1) AS growth_pct
FROM yearly
ORDER BY year;

-- 4. Seasonality: which months sell more or less than average? (100 = average month)
WITH monthly AS (
    SELECT MONTH(sale_date) AS month_num, MONTHNAME(sale_date) AS month, AVG(units_sold) AS avg_units
    FROM sales
    GROUP BY MONTH(sale_date), MONTHNAME(sale_date)
)
SELECT
    month,
    ROUND(avg_units, 1)                                   AS avg_daily_units,
    ROUND(avg_units / AVG(avg_units) OVER () * 100, 0)    AS seasonality_index
FROM monthly
ORDER BY month_num;

-- 5. Weekday pattern (100 = average day)
WITH weekday AS (
    SELECT ISODOW(sale_date) AS day_num, DAYNAME(sale_date) AS weekday, AVG(units_sold) AS avg_units
    FROM sales
    GROUP BY ISODOW(sale_date), DAYNAME(sale_date)
)
SELECT
    weekday,
    ROUND(avg_units, 1)                                   AS avg_daily_units,
    ROUND(avg_units / AVG(avg_units) OVER () * 100, 0)    AS weekday_index
FROM weekday
ORDER BY day_num;

-- 6. Fastest and slowest moving items in 2017
SELECT *
FROM (
    SELECT
        s.item,
        i.category,
        SUM(s.units_sold)                                             AS units_2017,
        ROUND(SUM(s.units_sold) * 100.0 / SUM(SUM(s.units_sold)) OVER (), 2) AS share_pct,
        RANK() OVER (ORDER BY SUM(s.units_sold) DESC)                 AS sales_rank
    FROM sales s
    JOIN items i ON s.item = i.item
    WHERE YEAR(s.sale_date) = 2017
    GROUP BY s.item, i.category
)
WHERE sales_rank <= 5 OR sales_rank >= 46
ORDER BY sales_rank;
