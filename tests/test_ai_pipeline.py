import pytest

from app.core.sql_guard import SqlValidationError
from app.prompts.sql_generation import build_sql_generation_prompt
from app.services.assistant import _ensure_generated_tables_are_in_context
from app.services.schema_context import build_schema_context


def test_sql_prompt_contains_only_selected_schema_context():
    context = build_schema_context("Which region generated the most revenue?")

    prompt = build_sql_generation_prompt(
        question="Which region generated the most revenue?",
        schema_prompt_context=context["prompt_context"],
    )

    assert "TABLE: payments" in prompt
    assert "TABLE: customers" in prompt
    assert "TABLE: regions" in prompt
    assert "Never produce INSERT" in prompt


def test_generated_tables_must_stay_inside_question_context():
    _ensure_generated_tables_are_in_context(
        generated_tables=["payments", "customers", "regions"],
        selected_tables=["payments", "customers", "regions"],
    )


def test_generated_table_outside_context_is_blocked():
    with pytest.raises(SqlValidationError):
        _ensure_generated_tables_are_in_context(
            generated_tables=["payments", "refunds"],
            selected_tables=["payments", "customers"],
        )
