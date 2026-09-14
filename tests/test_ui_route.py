from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ui_route_returns_insightpilot_v3_page():
    response = client.get("/ui")

    assert response.status_code == 200
    assert "InsightPilot AI" in response.text
    assert "Ask anything about your data." in response.text
    assert "Investigation Details" in response.text
    assert "Helpful Prompts" in response.text
    assert "/static/js/insightpilot-v3.js" in response.text
