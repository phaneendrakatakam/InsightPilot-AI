from app.schemas.analytics import EvidenceReasoning
from app.services import evidence_followup
from app.services.evidence_memory import EvidenceMemory


def _snapshot():
    memory = EvidenceMemory()
    return memory.remember_v2(
        "ses_1",
        {
            "question": "Why did revenue decline in August compared with July?",
            "status": "completed",
            "conclusion": "South revenue declined while payment failures increased.",
            "caveats": [
                "Payment failures are associated with the decline but direct causality is not proven."
            ],
            "plan": {
                "steps": [
                    {
                        "status": "completed",
                        "title": "Revenue Movement",
                        "evidence_summary": "South revenue fell from 591279 to 444828.",
                        "sql": "SELECT revenue",
                        "tables": ["payments"],
                        "rows": [],
                        "row_count": 2,
                    },
                    {
                        "status": "completed",
                        "title": "Payment Failure Movement",
                        "evidence_summary": "Failed payments increased from 15 to 54.",
                        "sql": "SELECT failures",
                        "tables": ["payments"],
                        "rows": [],
                        "row_count": 2,
                    },
                ]
            },
        },
    )


def test_challenge_uses_grounded_reasoning(monkeypatch):
    snapshot = _snapshot()

    monkeypatch.setattr(
        evidence_followup,
        "generate_evidence_reasoning",
        lambda **kwargs: EvidenceReasoning(
            answer="Failures increased alongside the decline, but causality is not proven.",
            supporting_evidence_ids=["E1", "E2"],
            limitations=["No direct causal linkage is established."],
            causality_statement="Association is observed; causality is not proven.",
            confidence="high",
        ),
    )

    result = evidence_followup.answer_from_evidence(
        "challenge",
        "Are you sure failures caused it?",
        snapshot,
    )

    assert result.status == "completed"
    assert result.result["reasoning_mode"] == "grounded_llm"
    assert result.result["supporting_evidence_ids"] == ["E1", "E2"]
    assert "causality is not proven" in result.result["answer"]


def test_explanation_uses_grounded_reasoning(monkeypatch):
    snapshot = _snapshot()

    monkeypatch.setattr(
        evidence_followup,
        "generate_evidence_reasoning",
        lambda **kwargs: EvidenceReasoning(
            answer="Revenue fell while failures rose in the same period.",
            supporting_evidence_ids=["E1", "E2"],
            limitations=[],
            causality_statement="This is an observed relationship, not proof of causality.",
            confidence="high",
        ),
    )

    result = evidence_followup.answer_from_evidence(
        "explanation",
        "Explain this result.",
        snapshot,
    )

    assert result.result["reasoning_mode"] == "grounded_llm"
    assert result.result["confidence"] == "high"


def test_provider_failure_falls_back_without_fabricating(monkeypatch):
    snapshot = _snapshot()

    def fail(**kwargs):
        raise evidence_followup.GeminiServiceError("provider unavailable")

    monkeypatch.setattr(
        evidence_followup,
        "generate_evidence_reasoning",
        fail,
    )

    result = evidence_followup.answer_from_evidence(
        "challenge",
        "Are you sure failures caused it?",
        snapshot,
    )

    assert result.status == "completed"
    assert result.result["reasoning_mode"] == "deterministic_fallback"
    assert "does not independently prove causality" in result.result["causality_statement"]
