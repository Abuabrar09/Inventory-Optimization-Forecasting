-- 1. Load all files into database tables
CREATE OR REPLACE TABLE sales AS
SELECT CAST(date AS DATE) AS sale_date, store, item, sales AS units_sold
FROM read_csv_auto('data/raw/train.csv');

CREATE OR REPLACE TABLE items           AS SELECT * FROM read_csv_auto('data/raw/items.csv');
CREATE OR REPLACE TABLE suppliers       AS SELECT * FROM read_csv_auto('data/raw/suppliers.csv');
CREATE OR REPLACE TABLE purchase_orders AS SELECT * FROM read_csv_auto('data/raw/purchase_orders.csv');
CREATE OR REPLACE TABLE inventory       AS SELECT * FROM read_csv_auto('data/raw/inventory_snapshot.csv');

-- 2. How many rows did each table load?
SELECT 'sales' AS table_name, COUNT(*) AS row_count FROM sales
UNION ALL SELECT 'items', COUNT(*) FROM items
UNION ALL SELECT 'suppliers', COUNT(*) FROM suppliers
UNION ALL SELECT 'purchase_orders', COUNT(*) FROM purchase_orders
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory;

-- 3. Sales data quality: is every day there, and are the values sensible?
SELECT
    MIN(sale_date)                AS first_date,
    MAX(sale_date)                AS last_date,
    COUNT(DISTINCT sale_date)     AS days,
    COUNT(DISTINCT store)         AS stores,
    COUNT(DISTINCT item)          AS items,
    COUNT(DISTINCT sale_date) * COUNT(DISTINCT store) * COUNT(DISTINCT item) AS expected_rows,
    COUNT(*)                      AS actual_rows,
    SUM(CASE WHEN units_sold IS NULL THEN 1 ELSE 0 END) AS missing_units,
    SUM(CASE WHEN units_sold < 0     THEN 1 ELSE 0 END) AS negative_units,
    SUM(CASE WHEN units_sold = 0     THEN 1 ELSE 0 END) AS zero_sales_days,
    MAX(units_sold)               AS max_units_one_day
FROM sales;

-- 4. Duplicates: does any store + item + day appear more than once?
SELECT COUNT(*) AS duplicate_keys
FROM (
    SELECT sale_date, store, item
    FROM sales
    GROUP BY sale_date, store, item
    HAVING COUNT(*) > 1
);
