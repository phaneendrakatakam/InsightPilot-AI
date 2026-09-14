from pathlib import Path


def test_ui_loads_v3_script():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")

    assert "/static/js/insightpilot-v3.js" in html
    assert "/static/js/insightpilot-v2.js" not in html


def test_v3_ui_uses_server_backed_sessions_and_evidence():
    script = Path("app/static/js/insightpilot-v3.js").read_text(
        encoding="utf-8"
    )

    assert "/api/v3/sessions" in script
    assert "/turns" in script
    assert "/evidence" in script
    assert "refreshSessions()" in script
    assert "loadSession(session.session_id)" in script
    assert "state.sessionId" in script
