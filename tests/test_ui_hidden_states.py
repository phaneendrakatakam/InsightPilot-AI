from pathlib import Path


def test_hidden_attribute_is_not_overridden_by_component_display_rules():
    css_file = Path("app/static/css/insightpilot.css")
    css = css_file.read_text(encoding="utf-8")

    assert "[hidden]" in css
    assert "display: none !important;" in css
