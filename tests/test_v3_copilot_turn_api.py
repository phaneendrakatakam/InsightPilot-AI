import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import execution_router
from app.services.evidence_memory import evidence_memory
from app.services.session_store import session_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    session_store.clear()
    evidence_memory.clear()
    yield
    session_store.clear()
    evidence_memory.clear()


def test_copilot_turn_executes_and_stores_assistant_message(monkeypatch):
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

    session_id = client.post("/api/v3/sessions", json={}).json()["session_id"]
    response = client.post(
        f"/api/v3/sessions/{session_id}/turns",
        json={"message": "What was August revenue?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution"]["route"] == "v1_simple_query"
    assert "1770795" in body["assistant_message"]["content"]

    stored = client.get(f"/api/v3/sessions/{session_id}").json()
    assert [item["role"] for item in stored["messages"]] == ["user", "assistant"]


def test_evidence_request_uses_previous_turn_without_new_query(monkeypatch):
    calls = {"count": 0}

    def fake_answer(question):
        calls["count"] += 1
        return {
            "status": "answered",
            "answer": "August revenue was 1770795.",
            "question": question,
            "selected_tables": ["payments"],
            "sql": "SELECT SUM(amount) FROM payments",
            "evidence": {"rows": [{"value": 1770795}], "row_count": 1},
        }

    monkeypatch.setattr(execution_router, "answer_question", fake_answer)

    session_id = client.post("/api/v3/sessions", json={}).json()["session_id"]

    first = client.post(
        f"/api/v3/sessions/{session_id}/turns",
        json={"message": "What was August revenue?"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v3/sessions/{session_id}/turns",
        json={"message": "Show me the SQL behind that."},
    )
    assert second.status_code == 200
    assert second.json()["execution"]["route"] == "evidence_memory"
    assert calls["count"] == 1
