from app.prompts.sql_generation import build_sql_generation_prompt
from app.services.schema_context import build_schema_context


def test_highest_selling_definition_uses_completed_quantity():
    context = build_schema_context("What were the five highest-selling products?")

    prompt = build_sql_generation_prompt(
        "What were the five highest-selling products?",
        context["prompt_context"],
    )

    assert "SUM(orders.quantity)" in prompt
    assert "orders.order_status = 'COMPLETED'" in prompt
    assert "Do not silently replace" in prompt


def test_product_revenue_definition_uses_completed_order_amount():
    context = build_schema_context("Which products generated the most revenue?")

    prompt = build_sql_generation_prompt(
        "Which products generated the most revenue?",
        context["prompt_context"],
    )

    assert "SUM(orders.order_amount)" in prompt
    assert "orders.order_status = 'COMPLETED'" in prompt
