from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_serves_v3_copilot_ui():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "InsightPilot AI" in response.text
    assert "Ask anything about your data." in response.text
    assert "V3" in response.text
    assert "/static/css/insightpilot-v3.css" in response.text
    assert "/static/js/insightpilot-v3.js" in response.text


def test_ui_alias_and_v3_assets_work():
    ui_response = client.get("/ui")
    css_response = client.get("/static/css/insightpilot-v3.css")
    js_response = client.get("/static/js/insightpilot-v3.js")

    assert ui_response.status_code == 200
    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert "InsightPilot" in ui_response.text


def test_openapi_reports_v3_development_version():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["version"] == "3.0.0-dev"
    assert response.json()["info"]["description"] == "InsightPilot AI — Enterprise Data Copilot"
