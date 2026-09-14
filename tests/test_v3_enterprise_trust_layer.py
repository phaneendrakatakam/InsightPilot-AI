from pathlib import Path

import pytest

from app.core.governance import inspect_user_request, mask_sensitive_rows
from app.core.sql_guard import SqlValidationError, validate_sql
from app.schemas.analytics import GovernanceReport, TurnTraceSummary
from app.schemas.conversation import CopilotExecution, IntentDecision
from app.services.confidence_engine import assess_confidence
from app.services.execution_router import execute_intent
from app.services.observability import ObservabilityStore
from app.services.provenance import build_provenance
from app.services.runtime_store import RuntimeStore


def test_governance_blocks_direct_identity_export_before_execution(monkeypatch):
    def should_not_run(*args, **kwargs):
        raise AssertionError("Analytics engine should not run for a blocked identity export.")

    monkeypatch.setattr(
        "app.services.execution_router.answer_question",
        should_not_run,
    )

    decision = IntentDecision(
        intent="simple_query",
        confidence="high",
        uses_prior_context=False,
        reason="test",
    )

    from app.schemas.conversation import ConversationContext

    result = execute_intent(
        session_id="ses_test",
        message="Show me all customer names and customer codes.",
        intent=decision,
        context=ConversationContext(),
    )

    assert result.route == "governance"
    assert result.status == "blocked"
    assert result.governance.status == "blocked"
    assert "aggregated or pseudonymized" in result.result["answer"]


def test_sensitive_output_aliases_are_pseudonymized_deterministically():
    sql = "SELECT customer_name AS customer FROM customers"
    rows = [
        {"customer": "Customer 001"},
        {"customer": "Customer 002"},
    ]

    masked, fields = mask_sensitive_rows(rows, sql=sql)

    assert fields == ["customer"]
    assert masked[0]["customer"].startswith("Customer-")
    assert masked[1]["customer"].startswith("Customer-")
    assert masked[0]["customer"] != masked[1]["customer"]
    assert masked[0]["customer"] == mask_sensitive_rows(rows, sql=sql)[0][0]["customer"]


def test_query_complexity_guard_rejects_excessive_joins():
    sql = "SELECT p0.payment_id FROM payments p0 "
    for index in range(1, 12):
        sql += (
            f"JOIN payments p{index} "
            f"ON p{index}.payment_id = p0.payment_id "
        )

    with pytest.raises(SqlValidationError, match="complexity limit"):
        validate_sql(sql)


def test_provenance_and_confidence_are_grounded_without_numeric_probability():
    execution = CopilotExecution(
        route="v1_simple_query",
        status="completed",
        resolved_question="What was August revenue?",
        result={
            "status": "answered",
            "question": "What was August revenue?",
            "selected_tables": ["payments"],
            "sql": "SELECT SUM(amount) AS total_revenue FROM payments",
            "answer": "August revenue was 1770795.",
            "evidence": {
                "rows": [{"total_revenue": 1770795}],
                "row_count": 1,
                "execution_time_ms": 2.4,
            },
        },
        governance=GovernanceReport(),
    )

    provenance = build_provenance(
        execution.route,
        execution.result,
    )

    decision = IntentDecision(
        intent="simple_query",
        confidence="high",
        uses_prior_context=False,
        reason="test",
    )
    confidence = assess_confidence(
        "What was August revenue?",
        decision,
        execution,
        provenance,
    )

    assert provenance[0].evidence_id == "E1"
    assert provenance[0].sql_fingerprint
    assert confidence.level == "high"
    assert confidence.causality_status == "not_applicable"


def test_observability_survives_store_recreation(tmp_path: Path):
    database = tmp_path / "runtime.db"

    first_repo = RuntimeStore(database)
    first = ObservabilityStore(first_repo)

    trace = TurnTraceSummary(
        trace_id="trc_test",
        session_id="ses_test",
        intent="investigation",
        route="v2_investigation",
        status="completed",
        started_at="2026-09-13T10:00:00Z",
        duration_ms=120.5,
        query_count=4,
        query_time_ms=34.1,
        evidence_count=4,
        evidence_reused=False,
        retry_count=0,
        governance_status="passed",
    )
    first.record(trace)

    second_repo = RuntimeStore(database)
    second = ObservabilityStore(second_repo)

    restored = second.recent(limit=10)
    assert len(restored) == 1
    assert restored[0].trace_id == "trc_test"
    assert restored[0].query_count == 4


def test_final_ui_exposes_trust_layer_without_api_navigation():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    script = Path("app/static/js/insightpilot-v3.js").read_text(encoding="utf-8")

    assert 'id="trustPanel"' in html
    assert 'id="trustConfidence"' in html
    assert 'id="provenanceList"' in html
    assert "renderTrust(" in script

    assert "API Docs" not in html
    assert "Open API docs" not in html
    assert 'href="/docs"' not in html
