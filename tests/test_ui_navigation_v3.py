from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_final_ui_has_no_visible_api_docs_navigation():
    response = client.get("/")

    assert response.status_code == 200
    html = response.text

    assert "API Docs" not in html
    assert "Open API docs" not in html
    assert 'href="/docs"' not in html


def test_investigations_navigation_has_functional_drawer():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    script = Path("app/static/js/insightpilot-v3.js").read_text(encoding="utf-8")

    assert 'id="investigationsDrawer"' in html
    assert 'id="investigationsDrawerList"' in html
    assert "openInvestigationsDrawer" in script
    assert "refreshInvestigationsDrawer" in script
    assert 'els.investigationsNav.addEventListener("click", openInvestigationsDrawer)' in script
    assert "/api/v3/sessions?limit=100" in script
