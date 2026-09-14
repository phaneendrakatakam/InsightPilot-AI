from pathlib import Path


def test_v3_ui_uses_manrope_and_readable_monospace_for_evidence():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    css = Path("app/static/css/insightpilot-v3.css").read_text(
        encoding="utf-8"
    )

    assert "fonts.googleapis.com/css2" in html
    assert "family=Manrope" in html
    assert 'font-family: "Manrope"' in css
    assert "ui-monospace" in css
