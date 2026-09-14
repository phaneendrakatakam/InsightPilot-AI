from __future__ import annotations

from app.core.sql_guard import SqlValidationError, validate_sql
from app.schemas.analytics import GovernanceReport
from app.schemas.investigation import InvestigationPlan, InvestigationStep
from app.services.gemini_service import (
    GeminiServiceError,
    generate_business_answer,
    generate_sql,
)
from app.services.query_executor import QueryExecutionError, execute_read_query
from app.services.schema_context import (
    build_schema_context,
    build_schema_context_for_tables,
)


class InvestigationExecutionError(RuntimeError):
    pass


class InvestigationStepScopeError(SqlValidationError):
    pass


def _ensure_step_tables_are_in_context(
    generated_tables: list[str],
    selected_tables: list[str],
) -> None:
    unexpected = sorted(set(generated_tables) - set(selected_tables))
    if unexpected:
        raise InvestigationStepScopeError(
            "Generated SQL referenced table(s) outside the approved investigation "
            "step context: " + ", ".join(unexpected)
        )


def _build_step_question(
    investigation_question: str | None,
    step: InvestigationStep,
) -> str:
    if not investigation_question:
        return step.objective

    return f"""
PARENT INVESTIGATION:
{investigation_question}

CURRENT EVIDENCE STEP:
{step.objective}

Generate SQL only for this evidence step.

IMPORTANT:
- Preserve the explicit comparison periods/time ranges from the parent investigation.
- If this step is comparative, include every compared period in the SQL.
- Collect observable evidence only; do not try to prove causality in the SQL.
- Follow the locked business definitions in the SQL-generation instructions.
""".strip()


def _context_for_step(
    step: InvestigationStep,
    generation_question: str,
) -> dict:
    if step.tables:
        return build_schema_context_for_tables(
            question=generation_question,
            table_names=step.tables,
        )
    return build_schema_context(generation_question)


def execute_investigation_step(
    step: InvestigationStep,
    investigation_question: str | None = None,
) -> InvestigationStep:
    step.status = "running"
    step.sql = None
    step.row_count = None
    step.rows = []
    step.evidence_summary = None
    step.execution_time_ms = None
    step.governance = None
    step.error = None

    try:
        generation_question = _build_step_question(
            investigation_question=investigation_question,
            step=step,
        )

        schema_context = _context_for_step(
            step=step,
            generation_question=generation_question,
        )

        if not schema_context["selected_tables"]:
            step.status = "blocked"
            step.error = (
                "No approved schema context was available for this investigation step."
            )
            return step

        generation = generate_sql(
            question=generation_question,
            schema_prompt_context=schema_context["prompt_context"],
        )

        if generation.status == "NEEDS_CLARIFICATION":
            step.status = "blocked"
            step.error = (
                generation.message
                or "This investigation step needs clarification before SQL can be generated."
            )
            return step

        if not generation.sql.strip():
            raise GeminiServiceError(
                "Gemini marked the investigation step READY but did not provide SQL."
            )

        validated = validate_sql(generation.sql)

        _ensure_step_tables_are_in_context(
            generated_tables=validated.tables,
            selected_tables=schema_context["selected_tables"],
        )

        result = execute_read_query(validated.executable_sql)

        evidence_question = (
            generation_question
            + "\n\nSummarize only the executed evidence for the current step."
        )

        explanation = generate_business_answer(
            question=evidence_question,
            executed_sql=result["sql"],
            columns=result["columns"],
            rows=result["rows"],
            row_count=result["row_count"],
        )

        step.status = "completed"
        step.sql = result["sql"]
        step.tables = result["tables"]
        step.row_count = result["row_count"]
        step.rows = result["rows"]
        step.evidence_summary = explanation.answer
        step.execution_time_ms = result["execution_time_ms"]
        step.governance = GovernanceReport.model_validate(result.get("governance") or {})
        step.error = None
        return step

    except (
        GeminiServiceError,
        SqlValidationError,
        QueryExecutionError,
        ValueError,
    ) as exc:
        step.status = "failed"
        step.error = str(exc)
        return step


def execute_investigation_plan(plan: InvestigationPlan) -> InvestigationPlan:
    for step in plan.steps:
        execute_investigation_step(
            step,
            investigation_question=plan.question,
        )
    return plan
