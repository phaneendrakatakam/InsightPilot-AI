from __future__ import annotations

import pytest

from app.schemas.investigation import InvestigationPlan, InvestigationStep
from app.services import investigation_planner
from app.services.investigation_planner import InvestigationPlannerError


def _plan(*steps: InvestigationStep) -> InvestigationPlan:
    return InvestigationPlan(
        question="model-rephrased question",
        investigation_goal="Identify the strongest evidence-backed drivers.",
        steps=list(steps),
    )


def test_create_investigation_plan_normalizes_execution_fields(monkeypatch):
    generated = _plan(
        InvestigationStep(
            step_id="step_1",
            title="Revenue movement",
            objective="Compare July and August successful payment revenue.",
            tables=["payments", "payments"],
            status="completed",
            sql="SELECT 1",
            row_count=1,
            rows=[{"value": 1}],
            evidence_summary="Premature evidence",
            error="Premature error",
        ),
        InvestigationStep(
            step_id="step_2",
            title="Refund movement",
            objective="Compare July and August refunds.",
            tables=["refunds", "payments"],
        ),
    )

    monkeypatch.setattr(
        investigation_planner,
        "generate_investigation_plan",
        lambda question: generated,
    )

    question = "Why did revenue decline in August compared with July?"
    result = investigation_planner.create_investigation_plan(question)

    assert result.question == question
    assert len(result.steps) == 2

    first = result.steps[0]
    assert first.tables == ["payments"]
    assert first.status == "planned"
    assert first.sql is None
    assert first.row_count is None
    assert first.rows == []
    assert first.evidence_summary is None
    assert first.error is None


def test_create_investigation_plan_rejects_empty_question():
    with pytest.raises(InvestigationPlannerError, match="cannot be empty"):
        investigation_planner.create_investigation_plan("   ")


def test_create_investigation_plan_rejects_duplicate_step_ids(monkeypatch):
    generated = _plan(
        InvestigationStep(
            step_id="step_1",
            title="Revenue",
            objective="Compare revenue.",
            tables=["payments"],
        ),
        InvestigationStep(
            step_id="step_1",
            title="Refunds",
            objective="Compare refunds.",
            tables=["refunds"],
        ),
    )

    monkeypatch.setattr(
        investigation_planner,
        "generate_investigation_plan",
        lambda question: generated,
    )

    with pytest.raises(InvestigationPlannerError, match="Duplicate"):
        investigation_planner.create_investigation_plan(
            "Why did revenue decline?"
        )


def test_create_investigation_plan_rejects_unapproved_tables(monkeypatch):
    generated = _plan(
        InvestigationStep(
            step_id="step_1",
            title="Revenue",
            objective="Compare revenue.",
            tables=["payments"],
        ),
        InvestigationStep(
            step_id="step_2",
            title="Mystery source",
            objective="Inspect an unsupported source.",
            tables=["warehouse_events"],
        ),
    )

    monkeypatch.setattr(
        investigation_planner,
        "generate_investigation_plan",
        lambda question: generated,
    )

    with pytest.raises(InvestigationPlannerError, match="unapproved tables"):
        investigation_planner.create_investigation_plan(
            "Why did revenue decline?"
        )


def test_create_investigation_plan_requires_two_to_six_steps(monkeypatch):
    generated = _plan(
        InvestigationStep(
            step_id="step_1",
            title="Revenue",
            objective="Compare revenue.",
            tables=["payments"],
        ),
    )

    monkeypatch.setattr(
        investigation_planner,
        "generate_investigation_plan",
        lambda question: generated,
    )

    with pytest.raises(InvestigationPlannerError, match="between 2 and 6"):
        investigation_planner.create_investigation_plan(
            "Why did revenue decline?"
        )
