-- InsightPilot AI | V1 Day 2 | Load seed data
-- Run from project root:
-- psql -U postgres -d insightpilot_db -f ".\data\sql\load_seed_data.sql"

TRUNCATE TABLE refunds, orders, payments, subscriptions, customers, products, regions
RESTART IDENTITY CASCADE;

\copy regions(region_id, region_code, region_name) FROM 'data/synthetic/regions.csv' WITH (FORMAT csv, HEADER true)
\copy products(product_id, product_code, product_name, category, unit_price, product_status) FROM 'data/synthetic/products.csv' WITH (FORMAT csv, HEADER true)
\copy customers(customer_id, customer_code, customer_name, region_id, signup_date, account_status) FROM 'data/synthetic/customers.csv' WITH (FORMAT csv, HEADER true)
\copy subscriptions(subscription_id, customer_id, plan_name, subscription_status, start_date, end_date, monthly_price) FROM 'data/synthetic/subscriptions.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy payments(payment_id, customer_id, subscription_id, amount, payment_status, payment_date, payment_method) FROM 'data/synthetic/payments.csv' WITH (FORMAT csv, HEADER true)
\copy refunds(refund_id, payment_id, customer_id, refund_amount, refund_reason, refund_date) FROM 'data/synthetic/refunds.csv' WITH (FORMAT csv, HEADER true)
\copy orders(order_id, customer_id, product_id, quantity, order_amount, order_status, order_date) FROM 'data/synthetic/orders.csv' WITH (FORMAT csv, HEADER true)

SELECT setval(pg_get_serial_sequence('regions','region_id'), MAX(region_id), true) FROM regions;
SELECT setval(pg_get_serial_sequence('customers','customer_id'), MAX(customer_id), true) FROM customers;
SELECT setval(pg_get_serial_sequence('subscriptions','subscription_id'), MAX(subscription_id), true) FROM subscriptions;
SELECT setval(pg_get_serial_sequence('payments','payment_id'), MAX(payment_id), true) FROM payments;
SELECT setval(pg_get_serial_sequence('refunds','refund_id'), MAX(refund_id), true) FROM refunds;
SELECT setval(pg_get_serial_sequence('products','product_id'), MAX(product_id), true) FROM products;
SELECT setval(pg_get_serial_sequence('orders','order_id'), MAX(order_id), true) FROM orders;
