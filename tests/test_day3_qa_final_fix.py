from pathlib import Path

from app.services.schema_context import select_relevant_tables


def test_product_revenue_uses_only_product_order_domain():
    tables = select_relevant_tables("Which products generated the most revenue?")

    assert "products" in tables
    assert "orders" in tables
    assert "payments" not in tables
    assert "refunds" not in tables
    assert "subscriptions" not in tables


def test_final_ui_qa_helpers_are_present():
    js = Path("app/static/js/insightpilot.js").read_text(encoding="utf-8")
    css = Path("app/static/css/insightpilot.css").read_text(encoding="utf-8")

    assert "function isScopeRejection" in js
    assert "applyEvidencePagination(25);" in js
    assert "qa-pagination" in js
    assert ".qa-pagination" in css


def test_product_revenue_interpretation_is_strictly_grounded():
    prompt = Path("app/prompts/answer_generation.py").read_text(encoding="utf-8")

    assert "PRODUCT-RANKING INTERPRETATION RULES" in prompt
    assert "higher demand" in prompt
    assert "higher customer spending" in prompt
