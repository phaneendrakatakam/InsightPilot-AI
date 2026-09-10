from app.services.schema_context import select_relevant_tables


def test_pro_does_not_match_products():
    tables = select_relevant_tables("What were the five highest-selling products?")

    assert "products" in tables
    assert "orders" in tables
    assert "subscriptions" not in tables


def test_pro_still_matches_real_pro_subscription_question():
    tables = select_relevant_tables("How many active Pro customers do we have?")

    assert "subscriptions" in tables
    assert "customers" in tables
