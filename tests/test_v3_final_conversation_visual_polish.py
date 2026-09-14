from app.schemas.analytics import ConfidenceAssessment
from app.schemas.conversation import (
    ConversationContext,
    EvidenceReference,
    EvidenceSnapshot,
)
from app.services.context_manager import update_conversation_context
from app.services.evidence_followup import answer_from_evidence
from app.services.visualization_engine import build_charts


def test_evidence_request_does_not_mutate_comparison_context():
    current = ConversationContext(
        metric="revenue",
        comparison_regions=["South", "North"],
        primary_period="August",
        comparison_period="July",
        drilldown_dimension="region",
    )

    updated = update_conversation_context(
        current,
        "Show me the evidence behind South.",
    )

    assert updated.metric == "revenue"
    assert updated.region is None
    assert updated.comparison_regions == ["South", "North"]
    assert updated.primary_period == "August"
    assert updated.comparison_period == "July"
    assert updated.drilldown_dimension == "region"


def test_evidence_request_inherits_source_confidence():
    snapshot = EvidenceSnapshot(
        snapshot_id="evs_test",
        session_id="ses_test",
        source_route="v1_simple_query",
        source_question="Compare South with North.",
        conclusion="North overtook South in August.",
        evidence=[
            EvidenceReference(
                evidence_id="E1",
                title="Revenue comparison",
                summary="Comparison evidence.",
                rows=[],
                row_count=4,
            )
        ],
        confidence=ConfidenceAssessment(
            level="high",
            rationale="Direct executed evidence.",
            evidence_ids=["E1"],
            limitations=[],
            causality_status="not_applicable",
            causality_note="No causal claim.",
        ),
        created_at="2026-09-14T00:00:00Z",
    )

    execution = answer_from_evidence(
        intent="evidence_request",
        message="Show me the evidence behind South.",
        snapshot=snapshot,
    )

    assert execution.result["confidence"] == "high"


def test_comparison_chart_uses_unique_composite_labels():
    result = {
        "status": "answered",
        "evidence": {
            "rows": [
                {
                    "region_name": "North",
                    "month_label": "July 2026",
                    "total_revenue": 504300,
                },
                {
                    "region_name": "North",
                    "month_label": "August 2026",
                    "total_revenue": 493803,
                },
                {
                    "region_name": "South",
                    "month_label": "July 2026",
                    "total_revenue": 591279,
                },
                {
                    "region_name": "South",
                    "month_label": "August 2026",
                    "total_revenue": 444828,
                },
            ]
        },
    }

    charts = build_charts("v1_simple_query", result)

    assert len(charts) == 1
    assert charts[0].title == "Revenue Comparison"
    assert charts[0].labels == [
        "North · July 2026",
        "North · August 2026",
        "South · July 2026",
        "South · August 2026",
    ]
    assert len(set(charts[0].labels)) == 4
