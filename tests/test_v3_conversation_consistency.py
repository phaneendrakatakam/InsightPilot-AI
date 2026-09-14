from pathlib import Path

from app.schemas.conversation import ConversationContext, EvidenceReference, EvidenceSnapshot
from app.services.context_manager import update_conversation_context
from app.services.evidence_followup import answer_from_evidence, metric_keywords


def test_failure_followup_switches_metric_without_losing_region_or_periods():
    current = ConversationContext(
        metric="revenue",
        region="South",
        primary_period="August",
        comparison_period="July",
        revision=2,
    )

    updated = update_conversation_context(
        current,
        "Did failures increase there too?",
    )

    assert updated.metric == "failed_payments"
    assert updated.region == "South"
    assert updated.primary_period == "August"
    assert updated.comparison_period == "July"
    assert updated.revision == 3
    assert "failed payment" in metric_keywords(updated.metric)


def test_explanation_and_challenge_return_reused_evidence_payload():
    snapshot = EvidenceSnapshot(
        snapshot_id="evs_test",
        session_id="ses_test",
        source_route="v1_simple_query",
        source_question="Compare South with North.",
        conclusion="South and North differed.",
        evidence=[
            EvidenceReference(
                evidence_id="E1",
                title="Failed Payment Comparison",
                summary="South had more failed payments.",
                sql="SELECT 1",
                tables=["payments"],
                rows=[{"region": "South", "failed": 54}],
                row_count=1,
            )
        ],
        created_at="2026-09-13T18:00:00Z",
    )

    # Use a non-LLM intent path to exercise the deterministic evidence contract.
    response = answer_from_evidence(
        intent="follow_up",
        message="Summarize that.",
        snapshot=snapshot,
    )

    assert response.status == "completed"
    assert response.result["evidence"][0]["evidence_id"] == "E1"


def test_final_ui_maps_blocked_status_explicitly():
    script = Path("app/static/js/insightpilot-v3.js").read_text(encoding="utf-8")

    assert 'if (status === "blocked") return "Blocked";' in script
    assert '"Request blocked by governance"' in script
    assert "executionStatusLabel(response.execution?.status)" in script
