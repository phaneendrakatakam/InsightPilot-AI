from app.services.visualization_engine import build_charts


def test_time_series_rows_become_line_chart():
    result = {
        "plan": {
            "steps": [
                {
                    "status": "completed",
                    "title": "Successful Payment Revenue Movement",
                    "rows": [
                        {"payment_month": "2026-07", "total_revenue": "591279.00"},
                        {"payment_month": "2026-08", "total_revenue": "444828.00"},
                    ],
                }
            ]
        }
    }

    charts = build_charts("v2_investigation", result)

    assert len(charts) == 1
    chart = charts[0]
    assert chart.chart_type == "line"
    assert chart.labels == ["Jul 2026", "Aug 2026"]
    assert chart.series[0].key == "total_revenue"
    assert chart.series[0].values == [591279.0, 444828.0]
    assert chart.evidence_id == "E1"


def test_categorical_rows_become_bar_chart():
    result = {
        "evidence": {
            "rows": [
                {"region_name": "North", "total_revenue": "493803.00"},
                {"region_name": "South", "total_revenue": "444828.00"},
                {"region_name": "East", "total_revenue": "386343.00"},
            ]
        }
    }

    charts = build_charts("v1_simple_query", result)

    assert len(charts) == 1
    assert charts[0].chart_type == "bar"
    assert charts[0].labels == ["North", "South", "East"]


def test_single_row_does_not_create_meaningless_chart():
    result = {
        "evidence": {
            "rows": [
                {"total_revenue": "1770795.00"}
            ]
        }
    }

    charts = build_charts("v1_simple_query", result)

    assert charts == []
