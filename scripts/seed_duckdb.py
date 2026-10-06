import pathlib
import duckdb

pathlib.Path("data").mkdir(exist_ok=True)
con = duckdb.connect("data/shop.duckdb")
con.execute("CREATE SCHEMA IF NOT EXISTS analytics")
con.execute("CREATE SCHEMA IF NOT EXISTS internal")

con.execute("""
CREATE OR REPLACE TABLE analytics.customers AS
SELECT i AS customer_id,
       'Customer ' || i AS full_name,
       'user' || i || '@example.com' AS email,
       ['TN','FR','DE','US'][1 + i % 4] AS country,
       DATE '2024-01-01' + CAST(i % 300 AS INTEGER) AS signup_date
FROM range(1, 501) t(i)
""")

con.execute("""
CREATE OR REPLACE TABLE analytics.products AS
SELECT i AS product_id,
       'Product ' || i AS product_name,
       ['books','tech','home','toys'][1 + i % 4] AS category,
       CAST(5 + (i * 7) % 95 AS DECIMAL(10,2)) AS price
FROM range(1, 51) t(i)
""")

con.execute("""
CREATE OR REPLACE TABLE analytics.orders AS
SELECT i AS order_id,
       1 + (i * 37) % 500 AS customer_id,
       DATE '2024-06-01' + CAST(i % 400 AS INTEGER) AS order_date,
       ['completed','completed','completed','cancelled','refunded'][1 + i % 5] AS status
FROM range(1, 5001) t(i)
""")

con.execute("""
CREATE OR REPLACE TABLE analytics.order_items AS
SELECT i AS order_item_id,
       1 + (i * 13) % 5000 AS order_id,
       1 + (i * 17) % 50 AS product_id,
       1 + i % 3 AS quantity
FROM range(1, 12001) t(i)
""")

con.execute("""
CREATE OR REPLACE TABLE internal.audit_log AS
SELECT i AS id, 'secret event ' || i AS event FROM range(1, 11) t(i)
""")
con.close()
print("done")
