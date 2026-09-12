from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ui_is_v2_investigation_workspace():
    response = client.get("/ui")

    assert response.status_code == 200
    html = response.text

    assert "V2 · Investigation Agent" in html
    assert "Investigation trail" in html
    assert "Recent investigations" in html
    assert "/static/js/insightpilot-v2.js" in html


def test_v2_frontend_calls_v2_endpoint_and_persists_history():
    script = Path("app/static/js/insightpilot-v2.js").read_text(encoding="utf-8")

    assert 'const API_ENDPOINT = "/api/v2/investigate"' in script
    assert "window.localStorage" in script
    assert "insightpilot:v2:latest" in script
    assert "insightpilot:v2:history" in script
    assert "MAX_HISTORY = 10" in script


def test_v2_frontend_has_refresh_restore_and_history_reopen():
    script = Path("app/static/js/insightpilot-v2.js").read_text(encoding="utf-8")

    assert "restoreLatest()" in script
    assert "renderReport(payload, { restored: true })" in script
    assert "clearHistoryButton" in script
    assert "newInvestigationButton" in script
