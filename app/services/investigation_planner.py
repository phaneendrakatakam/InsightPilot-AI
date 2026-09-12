from __future__ import annotations

from app.core.schema_catalog import SCHEMA_CATALOG
from app.schemas.investigation import InvestigationPlan
from app.services.gemini_service import generate_investigation_plan


class InvestigationPlannerError(RuntimeError):
    pass


def create_investigation_plan(question: str) -> InvestigationPlan:
    question = question.strip()

    if not question:
        raise InvestigationPlannerError(
            "Investigation question cannot be empty."
        )

    plan = generate_investigation_plan(question)

    if not 2 <= len(plan.steps) <= 6:
        raise InvestigationPlannerError(
            "Investigation plans must contain between 2 and 6 steps."
        )

    seen_step_ids: set[str] = set()

    for step in plan.steps:
        if step.step_id in seen_step_ids:
            raise InvestigationPlannerError(
                f"Duplicate investigation step id: {step.step_id}"
            )

        seen_step_ids.add(step.step_id)

        invalid_tables = [
            table
            for table in step.tables
            if table not in SCHEMA_CATALOG
        ]

        if invalid_tables:
            raise InvestigationPlannerError(
                "Investigation plan referenced unapproved tables: "
                + ", ".join(invalid_tables)
            )

        step.tables = list(dict.fromkeys(step.tables))
        step.status = "planned"
        step.sql = None
        step.row_count = None
        step.rows = []
        step.evidence_summary = None
        step.error = None

    plan.question = question
    return plan
