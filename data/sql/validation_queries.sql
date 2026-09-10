-- InsightPilot AI | V1 Day 2 | Validation

SELECT 'regions' table_name, COUNT(*) row_count FROM regions
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'refunds', COUNT(*) FROM refunds
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
ORDER BY table_name;

SELECT DATE_TRUNC('month', payment_date)::date AS month,
       ROUND(SUM(amount),2) AS successful_revenue
FROM payments
WHERE payment_status='SUCCESS'
GROUP BY 1 ORDER BY 1;

SELECT DATE_TRUNC('month', payment_date)::date AS month,
       COUNT(*) AS attempts,
       COUNT(*) FILTER (WHERE payment_status='FAILED') AS failed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE payment_status='FAILED') / NULLIF(COUNT(*),0), 2) AS failure_rate_pct
FROM payments
GROUP BY 1 ORDER BY 1;

SELECT r.region_name,
       DATE_TRUNC('month', p.payment_date)::date AS month,
       ROUND(SUM(p.amount),2) AS successful_revenue
FROM payments p
JOIN customers c ON c.customer_id=p.customer_id
JOIN regions r ON r.region_id=c.region_id
WHERE p.payment_status='SUCCESS'
  AND p.payment_date >= DATE '2026-07-01'
  AND p.payment_date < DATE '2026-09-01'
GROUP BY r.region_name, DATE_TRUNC('month', p.payment_date)
ORDER BY r.region_name, month;

SELECT DATE_TRUNC('month', refund_date)::date AS month,
       COUNT(*) AS refund_count,
       ROUND(SUM(refund_amount),2) AS refund_amount
FROM refunds
WHERE refund_date >= DATE '2026-07-01'
  AND refund_date < DATE '2026-09-01'
GROUP BY 1 ORDER BY 1;

SELECT DATE_TRUNC('month', end_date)::date AS month,
       plan_name,
       COUNT(*) AS cancellations
FROM subscriptions
WHERE subscription_status='CANCELLED'
  AND end_date >= DATE '2026-07-01'
  AND end_date < DATE '2026-09-01'
GROUP BY 1, plan_name
ORDER BY 1, plan_name;

SELECT r.region_name, s.plan_name, COUNT(*) AS august_cancellations
FROM subscriptions s
JOIN customers c ON c.customer_id=s.customer_id
JOIN regions r ON r.region_id=c.region_id
WHERE s.subscription_status='CANCELLED'
  AND s.end_date >= DATE '2026-08-01'
  AND s.end_date < DATE '2026-09-01'
GROUP BY r.region_name, s.plan_name
ORDER BY august_cancellations DESC, r.region_name, s.plan_name;
