from __future__ import annotations

from app.core.sql_guard import ValidatedSql
from app.schemas.assistant import EvidenceAnswer, SqlGeneration
from app.schemas.investigation import InvestigationPlan, InvestigationStep
from app.services import investigation_executor
from app.services.schema_context import build_schema_context_for_tables


def test_build_schema_context_for_tables_preserves_safe_planner_scope():
    context = build_schema_context_for_tables(
        question="Compare regional revenue.",
        table_names=["regions", "customers", "payments", "payments"],
    )

    assert context["selected_tables"] == ["regions", "customers", "payments"]
    assert "TABLE: regions" in context["prompt_context"]
    assert "TABLE: customers" in context["prompt_context"]
    assert "TABLE: payments" in context["prompt_context"]


def test_execute_investigation_step_completes_with_grounded_evidence(monkeypatch):
    step = InvestigationStep(
        step_id="step_1",
        title="Revenue movement",
        objective="Compare successful payment revenue between July and August.",
        tables=["payments"],
    )

    monkeypatch.setattr(
        investigation_executor,
        "generate_sql",
        lambda **kwargs: SqlGeneration(
            status="READY",
            intent="Compare revenue",
            sql="SELECT 1 AS revenue",
            message="",
        ),
    )

    monkeypatch.setattr(
        investigation_executor,
        "validate_sql",
        lambda sql: ValidatedSql(
            original_sql=sql,
            normalized_sql=sql,
            executable_sql=sql,
            tables=["payments"],
            row_limit=500,
        ),
    )

    monkeypatch.setattr(
        investigation_executor,
        "execute_read_query",
        lambda sql: {
            "status": "success",
            "sql": sql,
            "tables": ["payments"],
            "columns": ["month", "revenue"],
            "rows": [
                {"month": "July", "revenue": 1902744},
                {"month": "August", "revenue": 1770795},
            ],
            "row_count": 2,
            "row_limit": 500,
            "execution_time_ms": 1.2,
        },
    )

    monkeypatch.setattr(
        investigation_executor,
        "generate_business_answer",
        lambda **kwargs: EvidenceAnswer(
            answer="Successful payment revenue decreased from July to August.",
            observations=[],
            interpretation="",
            caveat="",
        ),
    )

    result = investigation_executor.execute_investigation_step(step)

    assert result.status == "completed"
    assert result.row_count == 2
    assert result.tables == ["payments"]
    assert result.evidence_summary.startswith("Successful payment revenue")
    assert result.error is None


def test_execute_investigation_step_blocks_when_model_needs_clarification(monkeypatch):
    step = InvestigationStep(
        step_id="step_1",
        title="Unclear evidence",
        objective="Investigate an unclear metric.",
        tables=["payments"],
    )

    monkeypatch.setattr(
        investigation_executor,
        "generate_sql",
        lambda **kwargs: SqlGeneration(
            status="NEEDS_CLARIFICATION",
            intent="Unclear metric",
            sql="",
            message="The metric needs clarification.",
        ),
    )

    result = investigation_executor.execute_investigation_step(step)

    assert result.status == "blocked"
    assert result.sql is None
    assert result.error == "The metric needs clarification."


def test_execute_investigation_step_fails_when_sql_escapes_step_scope(monkeypatch):
    step = InvestigationStep(
        step_id="step_1",
        title="Revenue",
        objective="Compare revenue.",
        tables=["payments"],
    )

    monkeypatch.setattr(
        investigation_executor,
        "generate_sql",
        lambda **kwargs: SqlGeneration(
            status="READY",
            intent="Compare revenue",
            sql="SELECT * FROM refunds",
            message="",
        ),
    )

    monkeypatch.setattr(
        investigation_executor,
        "validate_sql",
        lambda sql: ValidatedSql(
            original_sql=sql,
            normalized_sql=sql,
            executable_sql=sql,
            tables=["refunds"],
            row_limit=500,
        ),
    )

    result = investigation_executor.execute_investigation_step(step)

    assert result.status == "failed"
    assert "outside the approved investigation step context" in result.error


def test_execute_investigation_plan_continues_after_failed_step(monkeypatch):
    plan = InvestigationPlan(
        question="Why did revenue decline?",
        investigation_goal="Find evidence-backed drivers.",
        steps=[
            InvestigationStep(
                step_id="step_1",
                title="Revenue",
                objective="Compare revenue.",
                tables=["payments"],
            ),
            InvestigationStep(
                step_id="step_2",
                title="Refunds",
                objective="Compare refunds.",
                tables=["refunds"],
            ),
        ],
    )

    calls: list[str] = []

    def fake_execute(step, investigation_question=None):
        calls.append(step.step_id)
        if step.step_id == "step_1":
            step.status = "failed"
            step.error = "simulated failure"
        else:
            step.status = "completed"
            step.row_count = 1
            step.evidence_summary = "Refund evidence collected."
        return step

    monkeypatch.setattr(
        investigation_executor,
        "execute_investigation_step",
        fake_execute,
    )

    result = investigation_executor.execute_investigation_plan(plan)

    assert calls == ["step_1", "step_2"]
    assert result.steps[0].status == "failed"
    assert result.steps[1].status == "completed"
