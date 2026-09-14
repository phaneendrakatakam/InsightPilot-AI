import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.session_store import session_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_ephemeral_sessions():
    session_store.clear()
    yield
    session_store.clear()


def _create_session() -> str:
    response = client.post("/api/v3/sessions", json={})
    assert response.status_code == 201
    return response.json()["session_id"]


def test_create_v3_session():
    response = client.post("/api/v3/sessions", json={})

    assert response.status_code == 201
    body = response.json()
    assert body["session_id"].startswith("ses_")
    assert body["title"] == "New Investigation"
    assert body["messages"] == []
    assert body["context"]["revision"] == 0


def test_first_message_builds_business_context():
    session_id = _create_session()

    response = client.post(
        f"/api/v3/sessions/{session_id}/messages",
        json={"message": "Why did revenue decline in August compared with July?"},
    )

    assert response.status_code == 200
    context = response.json()["context"]
    assert context["metric"] == "revenue"
    assert context["primary_period"] == "August"
    assert context["comparison_period"] == "July"
    assert context["revision"] == 1


def test_follow_up_preserves_prior_context_and_adds_region():
    session_id = _create_session()

    client.post(
        f"/api/v3/sessions/{session_id}/messages",
        json={"message": "Why did revenue decline in August compared with July?"},
    )
    follow_up = client.post(
        f"/api/v3/sessions/{session_id}/messages",
        json={"message": "Investigate South."},
    )

    assert follow_up.status_code == 200
    context = follow_up.json()["context"]
    assert context["metric"] == "revenue"
    assert context["primary_period"] == "August"
    assert context["comparison_period"] == "July"
    assert context["region"] == "South"
    assert context["revision"] == 2


def test_follow_up_can_change_region_without_losing_metric_or_periods():
    session_id = _create_session()

    client.post(
        f"/api/v3/sessions/{session_id}/messages",
        json={"message": "Compare revenue in August with July for South."},
    )
    response = client.post(
        f"/api/v3/sessions/{session_id}/messages",
        json={"message": "Now compare North."},
    )

    context = response.json()["context"]
    assert context["metric"] == "revenue"
    assert context["primary_period"] == "August"
    assert context["comparison_period"] == "July"
    assert context["region"] == "North"


def test_context_reset_keeps_message_history():
    session_id = _create_session()

    client.post(
        f"/api/v3/sessions/{session_id}/messages",
        json={"message": "Why did revenue decline in August compared with July?"},
    )
    response = client.post(f"/api/v3/sessions/{session_id}/context/reset")

    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) == 1
    assert body["context"]["metric"] is None
    assert body["context"]["primary_period"] is None
    assert body["context"]["comparison_period"] is None
    assert body["context"]["revision"] == 0


def test_unknown_session_returns_404():
    response = client.get("/api/v3/sessions/ses_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation session not found."
