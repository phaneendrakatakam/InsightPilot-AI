from types import SimpleNamespace

import pytest

from app.schemas.conversation import ConversationContext, IntentDecision
from app.services import execution_router
from app.services.evidence_memory import evidence_memory


@pytest.fixture(autouse=True)
def clear_memory():
    evidence_memory.clear()
    yield
    evidence_memory.clear()


def _intent(name: str, uses_prior_context: bool = False):
    return IntentDecision(
        intent=name,
        confidence="high",
        uses_prior_context=uses_prior_context,
        reason="test",
    )


def test_resolved_question_contains_preserved_context():
    context = ConversationContext(
        metric="revenue",
        region="South",
        primary_period="August",
        comparison_period="July",
        revision=2,
    )

    resolved = execution_router.build_resolved_question("Investigate it.", context)

    assert "metric: revenue" in resolved
    assert "compare August with July" in resolved
    assert "region: South" in resolved


@pytest.mark.parametrize(
    ("intent_name", "message", "expected"),
    [
        ("simple_query", "What was August revenue?", "v1_simple_query"),
        ("comparison", "Compare South with North.", "v1_simple_query"),
        ("investigation", "Why did revenue decline?", "v2_investigation"),
        ("drill_down", "Investigate South.", "v2_investigation"),
        ("follow_up", "Did failures increase there too?", "v1_simple_query"),
        ("follow_up", "What happened there?", "v2_investigation"),
        ("challenge", "Are you sure?", "evidence_memory"),
        ("explanation", "Explain this.", "evidence_memory"),
        ("evidence_request", "Show SQL.", "evidence_memory"),
    ],
)
def test_execution_route_selection(intent_name, message, expected):
    assert execution_router.choose_execution_route(_intent(intent_name), message) == expected


def test_simple_query_reuses_v1_pipeline(monkeypatch):
    monkeypatch.setattr(
        execution_router,
        "answer_question",
        lambda question: {
            "status": "answered",
            "answer": "August revenue was 1770795.",
            "question": question,
            "selected_tables": ["payments"],
            "sql": "SELECT 1",
            "evidence": {"rows": [{"value": 1770795}], "row_count": 1},
        },
    )

    result = execution_router.execute_intent(
        "ses_1",
        "What was August revenue?",
        _intent("simple_query"),
        ConversationContext(metric="revenue", primary_period="August"),
    )

    assert result.route == "v1_simple_query"
    assert evidence_memory.latest("ses_1") is not None


def test_investigation_reuses_v2_pipeline(monkeypatch):
    fake_response = SimpleNamespace(
        model_dump=lambda mode=None: {
            "question": "Why did revenue decline?",
            "status": "completed",
            "conclusion": "South was the largest negative contributor.",
            "caveats": [],
            "plan": {"steps": []},
        }
    )
    monkeypatch.setattr(execution_router, "investigate", lambda question: fake_response)

    result = execution_router.execute_intent(
        "ses_1",
        "Why did revenue decline?",
        _intent("investigation"),
        ConversationContext(
            metric="revenue",
            primary_period="August",
            comparison_period="July",
        ),
    )

    assert result.route == "v2_investigation"
    assert evidence_memory.latest("ses_1").conclusion == "South was the largest negative contributor."
