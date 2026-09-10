"""Approved business schema catalog for InsightPilot AI V1.

This is deliberately explicit rather than generated from PostgreSQL system catalogs.
Only fields listed here are eligible to be exposed to later LLM prompts.
"""

SCHEMA_CATALOG = {
    "regions": {
        "description": "Business region reference data used for geographic analysis.",
        "business_terms": [
            "region", "regions", "north", "south", "east", "west",
            "geography", "geographic", "location", "area",
        ],
        "columns": {
            "region_id": "Unique region identifier.",
            "region_code": "Short business code for the region.",
            "region_name": "Human-readable region name.",
        },
    },
    "customers": {
        "description": "Customer identity, region, signup date, and account status.",
        "business_terms": [
            "customer", "customers", "account", "accounts",
            "signup", "signed up", "active customer", "inactive customer",
            "top customer", "highest customer",
        ],
        "columns": {
            "customer_id": "Unique customer identifier.",
            "customer_code": "Business-facing customer code.",
            "customer_name": "Synthetic customer display name.",
            "region_id": "Region associated with the customer.",
            "signup_date": "Date the customer signed up.",
            "account_status": "Current account state: ACTIVE, INACTIVE, SUSPENDED, or CLOSED.",
        },
    },
    "subscriptions": {
        "description": "Customer subscription plan, state, lifecycle dates, and monthly pricing.",
        "business_terms": [
            "subscription", "subscriptions", "plan", "plans", "basic", "pro",
            "enterprise", "free", "active subscription", "cancelled",
            "cancellation", "cancellations", "expired", "past due", "churn",
        ],
        "columns": {
            "subscription_id": "Unique subscription identifier.",
            "customer_id": "Customer that owns the subscription.",
            "plan_name": "Subscription tier: FREE, BASIC, PRO, or ENTERPRISE.",
            "subscription_status": "ACTIVE, CANCELLED, EXPIRED, or PAST_DUE.",
            "start_date": "Subscription start date.",
            "end_date": "Subscription end/cancellation date when applicable.",
            "monthly_price": "Monthly subscription price.",
        },
    },
    "payments": {
        "description": "Subscription payment attempts, amounts, statuses, dates, and payment methods.",
        "business_terms": [
            "payment", "payments", "revenue", "sales revenue", "income",
            "failed payment", "failed payments", "payment failure",
            "successful payment", "success payment", "pending payment",
            "card", "upi", "net banking", "wallet",
        ],
        "columns": {
            "payment_id": "Unique payment identifier.",
            "customer_id": "Customer associated with the payment.",
            "subscription_id": "Subscription associated with the payment when applicable.",
            "amount": "Payment amount.",
            "payment_status": "SUCCESS, FAILED, or PENDING.",
            "payment_date": "Timestamp of the payment attempt.",
            "payment_method": "CARD, UPI, NET_BANKING, or WALLET.",
        },
    },
    "refunds": {
        "description": "Refund amounts, reasons, and dates linked to payments and customers.",
        "business_terms": [
            "refund", "refunds", "refunded", "refund amount",
            "refund reason", "billing correction", "duplicate charge",
        ],
        "columns": {
            "refund_id": "Unique refund identifier.",
            "payment_id": "Payment that the refund relates to.",
            "customer_id": "Customer associated with the refund.",
            "refund_amount": "Amount refunded.",
            "refund_reason": "Reason for the refund.",
            "refund_date": "Timestamp of the refund.",
        },
    },
    "products": {
        "description": "Commercial product catalogue and pricing attributes.",
        "business_terms": [
            "product", "products", "catalogue", "catalog", "category",
            "unit price", "add-on", "addon", "service",
        ],
        "columns": {
            "product_id": "Unique product identifier.",
            "product_code": "Business-facing product code.",
            "product_name": "Product name.",
            "category": "Commercial category such as ADD_ON or SERVICE.",
            "unit_price": "Unit selling price.",
            "product_status": "ACTIVE or INACTIVE.",
        },
    },
    "orders": {
        "description": "Customer product purchases, quantities, amounts, statuses, and order dates.",
        "business_terms": [
            "order", "orders", "purchase", "purchases", "selling",
            "highest-selling", "highest selling", "best-selling", "best selling",
            "quantity", "order amount", "completed order", "cancelled order",
        ],
        "columns": {
            "order_id": "Unique order identifier.",
            "customer_id": "Customer that placed the order.",
            "product_id": "Product purchased in the order.",
            "quantity": "Number of product units purchased.",
            "order_amount": "Total order amount.",
            "order_status": "COMPLETED, CANCELLED, PENDING, or REFUNDED.",
            "order_date": "Timestamp of the order.",
        },
    },
}


RELATIONSHIPS = [
    {
        "left_table": "customers",
        "left_column": "region_id",
        "right_table": "regions",
        "right_column": "region_id",
        "meaning": "Each customer belongs to a region.",
    },
    {
        "left_table": "subscriptions",
        "left_column": "customer_id",
        "right_table": "customers",
        "right_column": "customer_id",
        "meaning": "Subscriptions belong to customers.",
    },
    {
        "left_table": "payments",
        "left_column": "customer_id",
        "right_table": "customers",
        "right_column": "customer_id",
        "meaning": "Payments belong to customers.",
    },
    {
        "left_table": "payments",
        "left_column": "subscription_id",
        "right_table": "subscriptions",
        "right_column": "subscription_id",
        "meaning": "Payments can be linked to subscriptions.",
    },
    {
        "left_table": "refunds",
        "left_column": "payment_id",
        "right_table": "payments",
        "right_column": "payment_id",
        "meaning": "Refunds are linked to payments.",
    },
    {
        "left_table": "refunds",
        "left_column": "customer_id",
        "right_table": "customers",
        "right_column": "customer_id",
        "meaning": "Refunds belong to customers.",
    },
    {
        "left_table": "orders",
        "left_column": "customer_id",
        "right_table": "customers",
        "right_column": "customer_id",
        "meaning": "Orders belong to customers.",
    },
    {
        "left_table": "orders",
        "left_column": "product_id",
        "right_table": "products",
        "right_column": "product_id",
        "meaning": "Orders reference purchased products.",
    },
]
