from __future__ import annotations

from app.core.sql_guard import ValidatedSql
from app.schemas.assistant import EvidenceAnswer, SqlGeneration
from app.schemas.investigation import InvestigationPlan, InvestigationStep
from app.services import investigation_executor


def test_step_question_preserves_parent_period_context():
    step = InvestigationStep(
        step_id="step_2",
        title="Payment failures",
        objective="Compare failed payment attempts.",
        tables=["payments"],
    )

    question = investigation_executor._build_step_question(
        "Why did revenue decline in August compared with July?",
        step,
    )

    assert "August compared with July" in question
    assert "Compare failed payment attempts." in question
    assert "include every compared period" in question


def test_execute_plan_forwards_parent_question_to_each_step(monkeypatch):
    plan = InvestigationPlan(
        question="Why did revenue decline in August compared with July?",
        investigation_goal="Collect comparative evidence.",
        steps=[
            InvestigationStep(
                step_id="step_1",
                title="Revenue",
                objective="Compare successful payment revenue.",
                tables=["payments"],
            ),
            InvestigationStep(
                step_id="step_2",
                title="Refunds",
                objective="Compare refund counts and amounts.",
                tables=["refunds"],
            ),
        ],
    )

    received: list[tuple[str, str | None]] = []

    def fake_execute(step, investigation_question=None):
        received.append((step.step_id, investigation_question))
        step.status = "completed"
        return step

    monkeypatch.setattr(
        investigation_executor,
        "execute_investigation_step",
        fake_execute,
    )

    investigation_executor.execute_investigation_plan(plan)

    assert received == [
        ("step_1", plan.question),
        ("step_2", plan.question),
    ]
