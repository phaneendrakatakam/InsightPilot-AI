from app.prompts.investigation_planning import build_investigation_planning_prompt
from app.prompts.sql_generation import build_sql_generation_prompt


def test_planner_uses_cancellations_without_unsolicited_active_counts():
    prompt = build_investigation_planning_prompt(
        "Why did revenue decline in August compared with July?"
    )

    assert "compare cancellation counts by period" in prompt
    assert "do not add active subscription counts" in prompt.lower()


def test_sql_prompt_locks_cancellation_semantics():
    prompt = build_sql_generation_prompt(
        question="Compare subscription cancellations in August compared with July.",
        schema_prompt_context="TABLE: subscriptions",
    )

    assert "subscription_status = 'CANCELLED'" in prompt
    assert "end_date" in prompt
    assert "Do not add active subscription counts" in prompt


def test_sql_prompt_requires_active_status_when_active_is_explicit():
    prompt = build_sql_generation_prompt(
        question="Compare active subscriptions in August compared with July.",
        schema_prompt_context="TABLE: subscriptions",
    )

    assert "subscription_status = 'ACTIVE'" in prompt
    assert "Do not infer a historical active-state snapshot" in prompt
