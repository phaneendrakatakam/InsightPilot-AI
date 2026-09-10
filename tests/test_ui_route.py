from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ui_route_returns_insightpilot_page():
    response = client.get("/ui")
    assert response.status_code == 200
    assert "InsightPilot" in response.text
    assert "Enterprise Data Assistant" in response.text
    assert "/static/js/insightpilot.js" in response.text
    assert "/static/css/insightpilot.css" in response.text
