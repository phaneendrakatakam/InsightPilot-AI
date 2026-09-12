from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ui_route_returns_insightpilot_v2_page():
    response = client.get("/ui")

    assert response.status_code == 200
    assert "InsightPilot" in response.text
    assert "V2 · Investigation Agent" in response.text
    assert "Multi-step enterprise investigation" in response.text
    assert "Investigation trail" in response.text
