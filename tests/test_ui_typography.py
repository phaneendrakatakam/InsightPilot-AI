from pathlib import Path


def test_ui_uses_distinct_typography_system():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    css = Path("app/static/css/insightpilot-v2.css").read_text(encoding="utf-8")

    assert "fonts.googleapis.com/css2" in html
    assert "family=Manrope" in html
    assert "family=JetBrains+Mono" in html

    assert '--font-body: "Manrope", sans-serif;' in css
    assert '--font-heading: "Manrope", sans-serif;' in css
    assert '--font-mono: "JetBrains Mono", monospace;' in css
