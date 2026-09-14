from app.services.kpi_engine import build_kpis


def test_builds_revenue_comparison_kpi_from_investigation_rows():
    result = {
        "plan": {
            "steps": [
                {
                    "status": "completed",
                    "rows": [
                        {"payment_month": "2026-07", "total_revenue": "591279.00"},
                        {"payment_month": "2026-08", "total_revenue": "444828.00"},
                    ],
                }
            ]
        }
    }

    cards = build_kpis("v2_investigation", result)

    assert len(cards) == 1
    card = cards[0]
    assert card.label == "Revenue"
    assert card.previous_value == 591279.0
    assert card.value == 444828.0
    assert card.direction == "down"
    assert card.percent_change == -24.77
    assert card.evidence_id == "E1"


def test_builds_failed_payment_count_and_amount_kpis():
    result = {
        "plan": {
            "steps": [
                {
                    "status": "completed",
                    "rows": [
                        {
                            "payment_month": "2026-07",
                            "failed_payment_count": 15,
                            "failed_payment_amount": "41985.00",
                        },
                        {
                            "payment_month": "2026-08",
                            "failed_payment_count": 54,
                            "failed_payment_amount": "163446.00",
                        },
                    ],
                }
            ]
        }
    }

    cards = build_kpis("v2_investigation", result)
    by_key = {card.key: card for card in cards}

    assert by_key["failed_payment_count"].percent_change == 260.0
    assert by_key["failed_payment_amount"].direction == "up"


def test_single_row_v1_result_builds_simple_kpi():
    result = {
        "evidence": {
            "rows": [
                {"total_revenue": "1770795.00"}
            ]
        }
    }

    cards = build_kpis("v1_simple_query", result)

    assert len(cards) == 1
    assert cards[0].label == "Revenue"
    assert cards[0].value == 1770795.0
    assert cards[0].previous_value is None
