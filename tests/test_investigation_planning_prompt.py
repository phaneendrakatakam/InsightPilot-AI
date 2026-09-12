from __future__ import annotations

from app.prompts.investigation_planning import build_investigation_planning_prompt


def test_investigation_prompt_locks_revenue_semantics():
    prompt = build_investigation_planning_prompt(
        "Why did revenue decline in August compared with July?"
    )

    assert "Revenue means SUM(payments.amount)" in prompt
    assert "Do not use orders to explain generic company revenue" in prompt
    assert "successful payment revenue movement" in prompt
    assert "payment failure movement" in prompt
    assert "refund movement" in prompt
    assert "subscription cancellation/churn movement" in prompt
    assert "regional revenue movement" in prompt
