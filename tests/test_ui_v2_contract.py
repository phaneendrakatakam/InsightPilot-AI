from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ui_is_v3_conversational_analytics_workspace():
    response = client.get("/")

    assert response.status_code == 200
    html = response.text

    assert "InsightPilot AI" in html
    assert "Ask anything about your data." in html
    assert "Key findings" in html
    assert "Evidence" in html
    assert "/static/js/insightpilot-v3.js" in html


def test_v3_frontend_calls_session_turns_endpoint():
    script = Path("app/static/js/insightpilot-v3.js").read_text(
        encoding="utf-8"
    )

    assert 'api("/api/v3/sessions"' in script
    assert "/turns" in script
    assert "ensureSession()" in script
    assert "sendTurn(" in script


def test_v3_frontend_renders_kpis_charts_context_and_evidence():
    script = Path("app/static/js/insightpilot-v3.js").read_text(
        encoding="utf-8"
    )

    assert "renderKpis(" in script
    assert "renderChart(" in script
    assert "renderContext(" in script
    assert "renderEvidence(" in script
    assert "renderSuggestedFollowups(" in script
