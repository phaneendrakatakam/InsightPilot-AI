from pathlib import Path

from app.schemas.conversation import ConversationContext
from app.services.context_manager import update_conversation_context


def test_failure_analysis_followup_can_switch_metric():
    current = ConversationContext(
        metric="revenue",
        region="South",
        primary_period="August",
        comparison_period="July",
    )

    updated = update_conversation_context(
        current,
        "Did failures increase there too?",
    )

    assert updated.metric == "failed_payments"
    assert updated.region == "South"


def test_causal_challenge_does_not_change_active_metric():
    current = ConversationContext(
        metric="revenue",
        comparison_regions=["South", "North"],
        primary_period="August",
        comparison_period="July",
    )

    updated = update_conversation_context(
        current,
        "Are you sure payment failures caused it?",
    )

    assert updated.metric == "revenue"
    assert updated.comparison_regions == ["South", "North"]
    assert updated.primary_period == "August"
    assert updated.comparison_period == "July"


def test_explain_and_evidence_requests_do_not_mutate_metric():
    current = ConversationContext(
        metric="revenue",
        region="South",
        primary_period="August",
        comparison_period="July",
    )

    explained = update_conversation_context(current, "Explain this result.")
    evidence = update_conversation_context(current, "Show me the evidence behind South.")

    assert explained.metric == "revenue"
    assert evidence.metric == "revenue"


def test_evidence_reasoning_prompt_forbids_dataset_absence_extrapolation():
    prompt = Path("app/prompts/evidence_reasoning.py").read_text(encoding="utf-8")

    assert "Never infer that the overall dataset, database, or schema lacks a field" in prompt
    assert "describe that as an" in prompt
    assert "evidence gap" in prompt
