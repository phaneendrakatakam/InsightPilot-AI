from app.schemas.conversation import ConversationContext
from app.services.context_manager import update_conversation_context
from app.services.execution_router import build_resolved_question
from app.services.intent_router import classify_intent


def test_compare_two_regions_is_preserved_in_context():
    previous = ConversationContext(
        metric="revenue",
        primary_period="August",
        comparison_period="July",
        revision=2,
    )

    resolved = update_conversation_context(previous, "Compare South with North.")
    decision = classify_intent("Compare South with North.", previous, resolved)

    assert decision.intent == "comparison"
    assert resolved.region is None
    assert resolved.comparison_regions == ["South", "North"]

    question = build_resolved_question("Compare South with North.", resolved)
    assert "comparison regions: South vs North" in question
    assert "compare August with July" in question


def test_compare_it_with_north_uses_existing_south_context():
    previous = ConversationContext(
        metric="revenue",
        region="South",
        primary_period="August",
        comparison_period="July",
        revision=3,
    )

    resolved = update_conversation_context(previous, "Compare it with North.")

    assert resolved.region is None
    assert resolved.comparison_regions == ["South", "North"]


def test_break_south_down_by_plan_sets_drilldown_dimension():
    previous = ConversationContext(
        metric="revenue",
        primary_period="August",
        comparison_period="July",
        revision=2,
    )

    resolved = update_conversation_context(previous, "Break South down by plan.")
    decision = classify_intent("Break South down by plan.", previous, resolved)

    assert decision.intent == "drill_down"
    assert resolved.region == "South"
    assert resolved.comparison_regions == []
    assert resolved.drilldown_dimension == "subscription_plan"

    question = build_resolved_question("Break South down by plan.", resolved)
    assert "region: South" in question
    assert "break down by: subscription plan" in question


def test_what_changed_most_reuses_comparison_context():
    previous = ConversationContext(
        metric="revenue",
        comparison_regions=["South", "North"],
        primary_period="August",
        comparison_period="July",
        revision=4,
    )

    resolved = update_conversation_context(previous, "What changed most?")
    decision = classify_intent("What changed most?", previous, resolved)

    assert decision.intent == "follow_up"
    assert decision.uses_prior_context is True
    assert resolved.comparison_regions == ["South", "North"]
