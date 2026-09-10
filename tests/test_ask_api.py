from fastapi.testclient import TestClient

import app.api.routes.ask as ask_route
from app.main import app

client = TestClient(app)


def test_unrelated_question_is_rejected_before_gemini():
    response = client.post(
        "/api/v1/ask",
        json={"question": "Tell me whether tomorrow will be lucky."},
    )

    assert response.status_code == 422


def test_ask_endpoint_returns_answered_payload(monkeypatch):
    def fake_answer_question(question: str):
        return {
            "status": "answered",
            "question": question,
            "intent": "Count active Pro customers.",
            "selected_tables": ["subscriptions", "customers"],
            "sql": "SELECT COUNT(*) AS active_pro_customers FROM subscriptions WHERE plan_name = 'PRO' AND subscription_status = 'ACTIVE' LIMIT 500",
            "answer": "There are 10 active Pro customers.",
            "observations": ["The query returned 10."],
            "interpretation": "",
            "caveat": "",
            "evidence": {
                "columns": ["active_pro_customers"],
                "rows": [{"active_pro_customers": 10}],
                "row_count": 1,
                "row_limit": 500,
                "execution_time_ms": 1.0,
            },
        }

    monkeypatch.setattr(ask_route, "answer_question", fake_answer_question)

    response = client.post(
        "/api/v1/ask",
        json={"question": "How many active Pro customers do we have?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["selected_tables"] == ["subscriptions", "customers"]
