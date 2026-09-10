from app.services.schema_context import build_schema_context, select_relevant_tables


def test_revenue_question_selects_payments():
    tables = select_relevant_tables("What was total revenue last month?")
    assert "payments" in tables


def test_failed_payments_question_selects_payments():
    tables = select_relevant_tables("Show customers with failed payments.")
    assert "payments" in tables
    assert "customers" in tables


def test_region_revenue_question_selects_joinable_context():
    context = build_schema_context("Which region generated the most revenue?")

    assert "payments" in context["selected_tables"]
    assert "regions" in context["selected_tables"]
    assert "customers" in context["selected_tables"]

    relationship_pairs = {
        (item["left_table"], item["right_table"])
        for item in context["relationships"]
    }

    assert ("payments", "customers") in relationship_pairs
    assert ("customers", "regions") in relationship_pairs


def test_highest_selling_products_selects_orders_and_products():
    tables = select_relevant_tables("What were the five highest-selling products?")
    assert "products" in tables
    assert "orders" in tables


def test_active_pro_customers_selects_subscription_and_customer_context():
    tables = select_relevant_tables("How many active Pro customers do we have?")
    assert "subscriptions" in tables
    assert "customers" in tables


def test_unknown_question_returns_no_schema():
    context = build_schema_context("Tell me whether tomorrow will be lucky.")

    assert context["selected_tables"] == []
    assert "NO APPROVED SCHEMA CONTEXT MATCHED" in context["prompt_context"]


def test_context_contains_only_selected_tables():
    context = build_schema_context("Show customers with failed payments.", max_tables=2)

    assert set(context["tables"].keys()) == set(context["selected_tables"])
    assert len(context["selected_tables"]) <= 2
