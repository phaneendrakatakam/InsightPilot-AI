from __future__ import annotations

from app.core.sql_guard import SqlValidationError, validate_sql
from app.services.gemini_service import (
    GeminiServiceError,
    generate_business_answer,
    generate_sql,
)
from app.services.query_executor import QueryExecutionError, execute_read_query
from app.services.schema_context import build_schema_context


class AssistantQuestionError(ValueError):
    pass


class GeneratedSqlScopeError(SqlValidationError):
    pass


def _ensure_generated_tables_are_in_context(
    generated_tables: list[str],
    selected_tables: list[str],
) -> None:
    unexpected = sorted(set(generated_tables) - set(selected_tables))

    if unexpected:
        raise GeneratedSqlScopeError(
            "Generated SQL referenced table(s) outside the approved question context: "
            + ", ".join(unexpected)
        )


def answer_question(question: str) -> dict:
    schema_context = build_schema_context(question)

    if not schema_context["selected_tables"]:
        raise AssistantQuestionError(
            "The question does not map to the approved V1 business schema. "
            "Please ask about customers, subscriptions, payments/revenue, refunds, "
            "orders, products, or regions."
        )

    generation = generate_sql(
        question=question,
        schema_prompt_context=schema_context["prompt_context"],
    )

    if generation.status == "NEEDS_CLARIFICATION":
        return {
            "status": "needs_clarification",
            "question": question,
            "message": generation.message
            or "More information is required before a safe query can be generated.",
            "intent": generation.intent,
            "selected_tables": schema_context["selected_tables"],
        }

    if not generation.sql.strip():
        raise GeminiServiceError(
            "Gemini marked the request READY but did not provide SQL."
        )

    # First safety validation before execution.
    validated = validate_sql(generation.sql)

    # Stronger than the global allow-list: Gemini may only use tables that were
    # selected for this specific question.
    _ensure_generated_tables_are_in_context(
        generated_tables=validated.tables,
        selected_tables=schema_context["selected_tables"],
    )

    # execute_read_query performs validation again before using the read-only DB.
    result = execute_read_query(validated.executable_sql)

    explanation = generate_business_answer(
        question=question,
        executed_sql=result["sql"],
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
    )

    return {
        "status": "answered",
        "question": question,
        "intent": generation.intent,
        "selected_tables": schema_context["selected_tables"],
        "sql": result["sql"],
        "answer": explanation.answer,
        "observations": explanation.observations,
        "interpretation": explanation.interpretation,
        "caveat": explanation.caveat,
        "evidence": {
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "row_limit": result["row_limit"],
            "execution_time_ms": result["execution_time_ms"],
        },
    }
