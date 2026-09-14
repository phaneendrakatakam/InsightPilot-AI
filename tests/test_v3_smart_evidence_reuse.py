import pytest

from app.schemas.conversation import ConversationContext, IntentDecision
from app.services import execution_router
from app.services.evidence_memory import evidence_memory


@pytest.fixture(autouse=True)
def clear_memory():
    evidence_memory.clear()
    yield
    evidence_memory.clear()


def _intent(name: str):
    return IntentDecision(
        intent=name,
        confidence="high",
        uses_prior_context=True,
        reason="test",
    )


def _seed_investigation():
    evidence_memory.remember_v2(
        "ses_1",
        {
            "question": "Investigate South.",
            "status": "completed",
            "conclusion": "South revenue declined.",
            "caveats": ["Association does not prove causality."],
            "plan": {
                "steps": [
                    {
                        "status": "completed",
                        "title": "Successful Payment Revenue Movement",
                        "evidence_summary": "Revenue fell from 591279 to 444828.",
                        "sql": "SELECT revenue",
                        "tables": ["payments"],
                        "rows": [],
                        "row_count": 2,
                    },
                    {
                        "status": "completed",
                        "title": "Payment Failure Movement",
                        "evidence_summary": "Failed payments increased from 15 to 54.",
                        "sql": "SELECT failures",
                        "tables": ["payments"],
                        "rows": [],
                        "row_count": 2,
                    },
                ]
            },
        },
    )


def test_follow_up_reuses_matching_evidence_without_new_query(monkeypatch):
    _seed_investigation()

    def should_not_run(_):
        raise AssertionError("A new V1 query should not run when evidence already answers the follow-up.")

    monkeypatch.setattr(execution_router, "answer_question", should_not_run)

    result = execution_router.execute_intent(
        "ses_1",
        "Did failures increase there too?",
        _intent("follow_up"),
        ConversationContext(metric="failed_payments", region="South", revision=3),
    )

    assert result.route == "evidence_memory"
    assert result.status == "completed"
    assert result.result["reused_evidence"] is True
    assert "15 to 54" in result.result["answer"]


def test_follow_up_falls_back_to_query_when_evidence_does_not_match(monkeypatch):
    _seed_investigation()

    monkeypatch.setattr(
        execution_router,
        "answer_question",
        lambda question: {
            "status": "answered",
            "answer": "Order evidence.",
            "question": question,
            "selected_tables": ["orders"],
            "sql": "SELECT 1",
            "evidence": {"rows": [], "row_count": 0},
        },
    )

    result = execution_router.execute_intent(
        "ses_1",
        "What about orders?",
        _intent("follow_up"),
        ConversationContext(metric="orders", region="South", revision=3),
    )

    assert result.route == "v1_simple_query"
    assert result.status == "completed"
