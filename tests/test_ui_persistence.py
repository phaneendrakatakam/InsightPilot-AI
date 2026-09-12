from pathlib import Path


def test_ui_loads_v2_script():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")

    script = "/static/js/insightpilot-v2.js"

    assert script in html


def test_v2_ui_persists_latest_report_and_history():
    script = Path("app/static/js/insightpilot-v2.js").read_text(
        encoding="utf-8"
    )

    assert "window.localStorage" in script
    assert "insightpilot:v2:latest" in script
    assert "insightpilot:v2:history" in script
    assert "restoreLatest()" in script
    assert "MAX_HISTORY = 10" in script
    assert "newInvestigationButton" in script
