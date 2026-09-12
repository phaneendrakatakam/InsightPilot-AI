from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_serves_v2_ui():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "InsightPilot" in response.text
    assert "V2 · Investigation Agent" in response.text
    assert "Multi-step enterprise investigation" in response.text


def test_ui_alias_still_works():
    response = client.get("/ui")

    assert response.status_code == 200
    assert "InsightPilot" in response.text


def test_openapi_reports_v2_release_version():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["version"] == "2.0.0"
