from pathlib import Path

from app.services.schema_context import select_relevant_tables


def test_product_revenue_question_selects_orders_and_products():
    tables = select_relevant_tables("Which products generated the most revenue?")

    assert "products" in tables
    assert "orders" in tables
    assert "subscriptions" not in tables


def test_ui_has_large_result_pagination_and_scope_state_mapping():
    js = Path("app/static/js/insightpilot.js").read_text(encoding="utf-8")
    css = Path("app/static/css/insightpilot.css").read_text(encoding="utf-8")

    assert "response.status === 422" in js
    assert "renderClarification({ message: detail })" in js
    assert "const pageSize = 25;" in js
    assert "evidencePagination" in js
    assert ".evidence-pagination" in css
