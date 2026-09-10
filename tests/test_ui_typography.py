from pathlib import Path


def test_ui_uses_distinct_typography_system():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    css = Path("app/static/css/insightpilot.css").read_text(encoding="utf-8")

    assert "fonts.googleapis.com/css2" in html
    assert "family=Inter" in html
    assert "family=JetBrains+Mono" in html
    assert "family=Sora" in html

    assert '--font-display: "Sora"' in css
    assert '--font-ui: Inter' in css
    assert '--font-mono: "JetBrains Mono"' in css

    assert "font-family: var(--font-display);" in css
    assert "font-family: var(--font-mono);" in css
